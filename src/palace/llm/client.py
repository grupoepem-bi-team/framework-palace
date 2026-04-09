"""
Palace Framework - LLM Client Module

This module provides the main LLM client for interacting with language models
through a unified interface. It supports:

- Multiple LLM providers (Ollama, OpenAI, Anthropic, etc.)
- Model routing based on agent roles
- Cost tracking and management
- Retry logic with exponential backoff
- Streaming responses
- Token counting and management

Usage:
    from palace.llm import LLMClient

    # Create client
    client = LLMClient()

    # Invoke a model
    response = await client.invoke(
        prompt="Write a REST endpoint for user management",
        role="backend"
    )

    # Stream response
    async for chunk in client.stream(prompt="...", role="backend"):
        print(chunk, end="")

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │                      LLMClient                           │
    │  ┌─────────────────────────────────────────────────┐    │
    │  │                    Router                        │    │
    │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐          │    │
    │  │  │ Backend │ │  DBA    │ │   QA    │  ...     │    │
    │  │  │ qwen3   │ │deepseek │ │ gemma4  │          │    │
    │  │  └─────────┘ └─────────┘ └─────────┘          │    │
    │  └─────────────────────────────────────────────────┘    │
    │                      ↓                                   │
    │  ┌─────────────────────────────────────────────────┐    │
    │  │                Provider Factory                  │    │
    │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐        │    │
    │  │  │  Ollama  │ │  OpenAI  │ │Anthropic │        │    │
    │  │  │ Provider │ │ Provider │ │ Provider │        │    │
    │  │  └──────────┘ └──────────┘ └──────────┘        │    │
    │  └─────────────────────────────────────────────────┘    │
    └─────────────────────────────────────────────────────────┘
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Union,
    runtime_checkable,
)

import structlog

from palace.core.config import get_settings
from palace.llm.base import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    Message,
    MessageRole,
    ModelInfo,
    ProviderConfig,
)
from palace.llm.costs import CostTracker, PricingConfig
from palace.llm.router import LLMRouter, ModelRole

logger = structlog.get_logger()


# =============================================================================
# Client Configuration
# =============================================================================


@dataclass
class LLMClientConfig:
    """
    Configuration for the LLM client.

    Attributes:
        default_provider: Default provider to use
        default_model: Default model to use
        max_retries: Maximum number of retries on failure
        retry_delay: Base delay between retries (exponential backoff)
        timeout: Request timeout in seconds
        max_tokens_default: Default max tokens for generation
        temperature_default: Default temperature
        enable_cost_tracking: Whether to track costs
        enable_caching: Whether to cache responses
        cache_ttl: Cache time-to-live in seconds
    """

    default_provider: str = "ollama"
    default_model: str = "qwen3-coder-next"
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 300.0
    max_tokens_default: int = 4096
    temperature_default: float = 0.7
    enable_cost_tracking: bool = True
    enable_caching: bool = False
    cache_ttl: int = 3600

    # Provider-specific configurations
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)

    # Role to model mappings (overrides router defaults)
    role_mappings: Dict[str, str] = field(default_factory=dict)

    def get_provider_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """Get configuration for a specific provider."""
        return self.providers.get(provider_name)


class InvocationStatus(str, Enum):
    """Status of an LLM invocation."""

    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"
    TIMEOUT = "timeout"
    CACHED = "cached"
    RATE_LIMITED = "rate_limited"


@dataclass
class InvocationResult:
    """
    Result of an LLM invocation.

    Contains the response along with metadata about the invocation.
    """

    response: LLMResponse
    status: InvocationStatus
    model: str
    provider: str
    role: Optional[str]
    tokens_prompt: int
    tokens_completion: int
    tokens_total: int
    cost: float
    latency_seconds: float
    timestamp: datetime
    retry_count: int = 0
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def content(self) -> str:
        """Get the response content."""
        return self.response.content

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "model": self.model,
            "provider": self.provider,
            "role": self.role,
            "tokens_prompt": self.tokens_prompt,
            "tokens_completion": self.tokens_completion,
            "tokens_total": self.tokens_total,
            "cost": self.cost,
            "latency_seconds": self.latency_seconds,
            "timestamp": self.timestamp.isoformat(),
            "retry_count": self.retry_count,
            "cached": self.cached,
        }


# =============================================================================
# LLM Client
# =============================================================================


class LLMClient:
    """
    Main client for interacting with LLM providers.

    This client provides a unified interface for:
    - Invoking LLM models with automatic routing
    - Managing multiple providers
    - Tracking costs and usage
    - Handling retries and timeouts
    - Streaming responses

    The client is designed to be:
    - Provider-agnostic: Easy to add new providers
    - Production-ready: With proper error handling and retry logic
    - Observable: With comprehensive logging and metrics
    - Cost-aware: With built-in cost tracking

    Example:
        ```python
        # Create client
        client = LLMClient()
        await client.initialize()

        # Simple invocation
        result = await client.invoke(
            prompt="Write a REST endpoint",
            role="backend"
        )

        # With messages (conversation)
        result = await client.invoke(
            messages=[
                {"role": "system", "content": "You are a backend developer."},
                {"role": "user", "content": "Write a REST endpoint"},
            ],
            role="backend"
        )

        # Streaming
        async for chunk in client.stream(prompt="...", role="backend"):
            print(chunk, end="")

        # Cleanup
        await client.shutdown()
        ```
    """

    def __init__(
        self,
        config: Optional[LLMClientConfig] = None,
        settings: Optional[Any] = None,
    ):
        """
        Initialize the LLM client.

        Args:
            config: Client configuration (uses defaults if not provided)
            settings: Framework settings (loads from environment if not provided)
        """
        self._config = config or LLMClientConfig()
        self._settings = settings or get_settings()

        # Core components
        self._router: Optional[LLMRouter] = None
        self._providers: Dict[str, LLMProvider] = {}
        self._cost_tracker: Optional[CostTracker] = None

        # Response cache (if enabled)
        self._cache: Dict[str, tuple[LLMResponse, float]] = {}

        # Initialization state
        self._initialized = False

        # Statistics
        self._stats = {
            "total_invocations": 0,
            "successful_invocations": 0,
            "failed_invocations": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "total_latency": 0.0,
        }

        logger.info(
            "llm_client_created",
            default_provider=self._config.default_provider,
            default_model=self._config.default_model,
            cost_tracking=self._config.enable_cost_tracking,
        )

    async def initialize(self) -> None:
        """
        Initialize the client and load providers.

        This method must be called before any invocations.
        It sets up:
        - The model router
        - Available providers
        - Cost tracking (if enabled)
        """
        if self._initialized:
            return

        logger.info("initializing_llm_client")

        # Initialize router
        self._router = LLMRouter(
            default_provider=self._config.default_provider,
            role_mappings=self._config.role_mappings,
        )

        # Load default provider (Ollama)
        await self._load_provider("ollama")

        # Initialize cost tracker
        if self._config.enable_cost_tracking:
            self._cost_tracker = CostTracker()

        self._initialized = True
        logger.info("llm_client_initialized")

    async def _load_provider(self, provider_name: str) -> None:
        """
        Load and initialize a provider.

        Args:
            provider_name: Name of the provider to load
        """
        if provider_name in self._providers:
            return

        # Get provider configuration
        provider_config = self._config.get_provider_config(provider_name)

        # Create provider based on name
        if provider_name == "ollama":
            from palace.llm.providers.ollama import OllamaProvider

            config = provider_config or ProviderConfig(
                name="ollama",
                base_url=self._settings.ollama.base_url,
                api_key=self._settings.ollama.api_key,
                timeout=self._settings.ollama.timeout,
            )
            provider = OllamaProvider(config)

        else:
            raise ValueError(f"Unknown provider: {provider_name}")

        # Initialize provider
        await provider.initialize()
        self._providers[provider_name] = provider

        # Register models with router
        for model in provider.list_models():
            self._router.register_model(model)

        logger.info(
            "provider_loaded",
            provider=provider_name,
            models_count=len(provider.list_models()),
        )

    async def shutdown(self) -> None:
        """
        Shutdown the client and cleanup resources.

        Closes all provider connections and flushes pending data.
        """
        if not self._initialized:
            return

        logger.info("shutting_down_llm_client")

        # Close all providers
        for name, provider in self._providers.items():
            try:
                await provider.close()
            except Exception as e:
                logger.error(
                    "provider_close_error",
                    provider=name,
                    error=str(e),
                )

        self._providers.clear()
        self._cache.clear()
        self._initialized = False

        logger.info("llm_client_shutdown_complete")

    # -------------------------------------------------------------------------
    # Core Invocation Methods
    # -------------------------------------------------------------------------

    async def invoke(
        self,
        prompt: Optional[str] = None,
        messages: Optional[List[Union[Message, Dict[str, str]]]] = None,
        *,
        role: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> InvocationResult:
        """
        Invoke an LLM model with automatic routing.

        Args:
            prompt: Simple text prompt (mutually exclusive with messages)
            messages: Conversation messages (mutually exclusive with prompt)
            role: Agent role for model routing (backend, frontend, dba, etc.)
            model: Specific model to use (overrides role routing)
            provider: Specific provider to use (overrides default)
            system_prompt: System prompt to prepend
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
            tools: Tools available to the model
            metadata: Additional metadata for the request

        Returns:
            InvocationResult with response and metadata

        Raises:
            ValueError: If both prompt and messages are provided
            RuntimeError: If client is not initialized
        """
        if not self._initialized:
            await self.initialize()

        # Validate inputs
        if prompt is not None and messages is not None:
            raise ValueError("Cannot specify both prompt and messages")

        if prompt is None and messages is None:
            raise ValueError("Must specify either prompt or messages")

        start_time = time.time()

        # Determine model and provider
        if model is None:
            if role is not None:
                model = self._router.get_model_for_role(role)
            else:
                model = self._config.default_model

        if provider is None:
            provider = self._router.get_provider_for_model(model)

        # Ensure provider is loaded
        if provider not in self._providers:
            await self._load_provider(provider)

        llm_provider = self._providers[provider]

        # Build messages
        final_messages: List[Message] = []

        if system_prompt:
            final_messages.append(Message(role=MessageRole.SYSTEM, content=system_prompt))

        if prompt:
            final_messages.append(Message(role=MessageRole.USER, content=prompt))
        elif messages:
            for msg in messages:
                if isinstance(msg, dict):
                    final_messages.append(
                        Message(
                            role=MessageRole(msg["role"]),
                            content=msg["content"],
                        )
                    )
                else:
                    final_messages.append(msg)

        # Build request
        request = LLMRequest(
            messages=final_messages,
            model=model,
            temperature=temperature or self._config.temperature_default,
            max_tokens=max_tokens or self._config.max_tokens_default,
            stop=stop or [],
            tools=tools or [],
            metadata=metadata or {},
        )

        # Check cache
        cache_key = self._get_cache_key(request)
        if self._config.enable_caching and cache_key in self._cache:
            cached_response, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._config.cache_ttl:
                return self._create_result(
                    response=cached_response,
                    status=InvocationStatus.CACHED,
                    model=model,
                    provider=provider,
                    role=role,
                    latency=0.0,
                    cached=True,
                )

        # Invoke with retry
        response, retry_count = await self._invoke_with_retry(
            provider=llm_provider,
            request=request,
            model=model,
        )

        latency = time.time() - start_time

        # Track costs
        cost = 0.0
        if self._cost_tracker:
            cost = self._cost_tracker.track_usage(
                model=model,
                provider=provider,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
            )

        # Cache response
        if self._config.enable_caching:
            self._cache[cache_key] = (response, time.time())

        # Update stats
        self._update_stats(response, cost, latency)

        return self._create_result(
            response=response,
            status=InvocationStatus.SUCCESS,
            model=model,
            provider=provider,
            role=role,
            latency=latency,
            retry_count=retry_count,
            cost=cost,
        )

    async def _invoke_with_retry(
        self,
        provider: LLMProvider,
        request: LLMRequest,
        model: str,
    ) -> tuple[LLMResponse, int]:
        """
        Invoke with exponential backoff retry.

        Args:
            provider: Provider to use
            request: Request to send
            model: Model name

        Returns:
            Tuple of (response, retry_count)
        """
        last_error: Optional[Exception] = None
        retry_count = 0

        for attempt in range(self._config.max_retries):
            try:
                response = await asyncio.wait_for(
                    provider.invoke(request),
                    timeout=self._config.timeout,
                )
                return response, retry_count

            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Request timed out after {self._config.timeout}s")
                logger.warning(
                    "llm_timeout",
                    model=model,
                    attempt=attempt + 1,
                    max_retries=self._config.max_retries,
                )

            except Exception as e:
                last_error = e
                logger.error(
                    "llm_error",
                    model=model,
                    error=str(e),
                    attempt=attempt + 1,
                )

            # Exponential backoff
            if attempt < self._config.max_retries - 1:
                delay = self._config.retry_delay * (2**attempt)
                await asyncio.sleep(delay)
                retry_count += 1

        # All retries exhausted
        raise last_error or RuntimeError("Unknown error during invocation")

    async def stream(
        self,
        prompt: Optional[str] = None,
        messages: Optional[List[Union[Message, Dict[str, str]]]] = None,
        *,
        role: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[str]:
        """
        Stream response from an LLM model.

        Args:
            Same as invoke()

        Yields:
            Chunks of the response content
        """
        if not self._initialized:
            await self.initialize()

        # Determine model and provider
        if model is None:
            if role is not None:
                model = self._router.get_model_for_role(role)
            else:
                model = self._config.default_model

        if provider is None:
            provider = self._router.get_provider_for_model(model)

        # Ensure provider is loaded
        if provider not in self._providers:
            await self._load_provider(provider)

        llm_provider = self._providers[provider]

        # Build messages
        final_messages: List[Message] = []

        if system_prompt:
            final_messages.append(Message(role=MessageRole.SYSTEM, content=system_prompt))

        if prompt:
            final_messages.append(Message(role=MessageRole.USER, content=prompt))
        elif messages:
            for msg in messages:
                if isinstance(msg, dict):
                    final_messages.append(
                        Message(
                            role=MessageRole(msg["role"]),
                            content=msg["content"],
                        )
                    )
                else:
                    final_messages.append(msg)

        # Build request
        request = LLMRequest(
            messages=final_messages,
            model=model,
            temperature=temperature or self._config.temperature_default,
            max_tokens=max_tokens or self._config.max_tokens_default,
            stop=stop or [],
            tools=[],
            metadata=metadata or {},
            stream=True,
        )

        # Stream from provider
        async for chunk in llm_provider.stream(request):
            yield chunk

    # -------------------------------------------------------------------------
    # Role-based Convenience Methods
    # -------------------------------------------------------------------------

    async def invoke_as_backend(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> InvocationResult:
        """Invoke with backend developer role."""
        return await self.invoke(
            prompt=prompt,
            role="backend",
            system_prompt=system_prompt or self._get_backend_system_prompt(),
            **kwargs,
        )

    async def invoke_as_frontend(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> InvocationResult:
        """Invoke with frontend developer role."""
        return await self.invoke(
            prompt=prompt,
            role="frontend",
            system_prompt=system_prompt or self._get_frontend_system_prompt(),
            **kwargs,
        )

    async def invoke_as_dba(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> InvocationResult:
        """Invoke with DBA role."""
        return await self.invoke(
            prompt=prompt,
            role="dba",
            system_prompt=system_prompt or self._get_dba_system_prompt(),
            **kwargs,
        )

    async def invoke_as_qa(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> InvocationResult:
        """Invoke with QA role."""
        return await self.invoke(
            prompt=prompt,
            role="qa",
            system_prompt=system_prompt or self._get_qa_system_prompt(),
            **kwargs,
        )

    async def invoke_as_reviewer(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> InvocationResult:
        """Invoke with reviewer role."""
        return await self.invoke(
            prompt=prompt,
            role="reviewer",
            system_prompt=system_prompt or self._get_reviewer_system_prompt(),
            **kwargs,
        )

    async def invoke_as_devops(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> InvocationResult:
        """Invoke with DevOps role."""
        return await self.invoke(
            prompt=prompt,
            role="devops",
            system_prompt=system_prompt or self._get_devops_system_prompt(),
            **kwargs,
        )

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _get_cache_key(self, request: LLMRequest) -> str:
        """Generate cache key for a request."""
        import hashlib
        import json

        content = json.dumps(
            {
                "model": request.model,
                "messages": [
                    {"role": m.role.value, "content": m.content} for m in request.messages
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            },
            sort_keys=True,
        )

        return hashlib.sha256(content.encode()).hexdigest()

    def _create_result(
        self,
        response: LLMResponse,
        status: InvocationStatus,
        model: str,
        provider: str,
        role: Optional[str],
        latency: float,
        retry_count: int = 0,
        cost: float = 0.0,
        cached: bool = False,
    ) -> InvocationResult:
        """Create an invocation result."""
        return InvocationResult(
            response=response,
            status=status,
            model=model,
            provider=provider,
            role=role,
            tokens_prompt=response.prompt_tokens,
            tokens_completion=response.completion_tokens,
            tokens_total=response.total_tokens,
            cost=cost,
            latency_seconds=latency,
            timestamp=datetime.utcnow(),
            retry_count=retry_count,
            cached=cached,
        )

    def _update_stats(
        self,
        response: LLMResponse,
        cost: float,
        latency: float,
    ) -> None:
        """Update invocation statistics."""
        self._stats["total_invocations"] += 1
        self._stats["successful_invocations"] += 1
        self._stats["total_tokens"] += response.total_tokens
        self._stats["total_cost"] += cost
        self._stats["total_latency"] += latency

    def get_stats(self) -> Dict[str, Any]:
        """Get invocation statistics."""
        stats = self._stats.copy()
        if stats["total_invocations"] > 0:
            stats["average_latency"] = stats["total_latency"] / stats["total_invocations"]
            stats["success_rate"] = stats["successful_invocations"] / stats["total_invocations"]
        return stats

    def get_cost_report(self) -> Optional[Dict[str, Any]]:
        """Get cost tracking report."""
        if self._cost_tracker:
            return self._cost_tracker.get_report()
        return None

    # -------------------------------------------------------------------------
    # System Prompts
    # -------------------------------------------------------------------------

    def _get_backend_system_prompt(self) -> str:
        """Get system prompt for backend role."""
        return """You are an expert backend developer specializing in Python and FastAPI.

Your expertise includes:
- REST API design and implementation
- Database modeling with SQLAlchemy
- Business logic and domain modeling
- Testing with pytest
- Clean architecture and SOLID principles

Provide production-ready code with:
- Proper type hints
- Error handling
- Logging
- Tests
- Documentation"""

    def _get_frontend_system_prompt(self) -> str:
        """Get system prompt for frontend role."""
        return """You are an expert frontend developer specializing in React and TypeScript.

Your expertise includes:
- React components and hooks
- State management
- TypeScript
- CSS and Tailwind
- Testing with Jest and React Testing Library

Provide production-ready code with:
- Proper TypeScript types
- Accessibility (a11y)
- Performance optimization
- Tests
- Documentation"""

    def _get_dba_system_prompt(self) -> str:
        """Get system prompt for DBA role."""
        return """You are an expert database administrator specializing in PostgreSQL.

Your expertise includes:
- Database design and modeling
- SQL optimization and query tuning
- Migrations and schema management
- Index design
- Performance monitoring

Provide production-ready solutions with:
- Optimized queries
- Proper indexing
- Migration scripts
- Documentation"""

    def _get_qa_system_prompt(self) -> str:
        """Get system prompt for QA role."""
        return """You are an expert QA engineer specializing in software testing.

Your expertise includes:
- Unit testing and integration testing
- E2E testing with Cypress/Playwright
- Test strategy and planning
- Quality metrics and coverage
- Automation frameworks

Provide comprehensive testing with:
- Test coverage
- Edge cases
- Error scenarios
- Documentation"""

    def _get_reviewer_system_prompt(self) -> str:
        """Get system prompt for reviewer role."""
        return """You are an expert code reviewer specializing in Python and web development.

Your expertise includes:
- Code quality and best practices
- Security vulnerabilities
- Performance issues
- Architectural patterns
- Maintainability

Provide constructive feedback with:
- Specific issues
- Severity levels
- Suggested fixes
- Best practice references"""

    def _get_devops_system_prompt(self) -> str:
        """Get system prompt for DevOps role."""
        return """You are an expert DevOps engineer specializing in CI/CD and infrastructure.

Your expertise includes:
- GitHub Actions and GitLab CI
- Docker and Kubernetes
- Terraform and IaC
- Monitoring and observability
- Security best practices

Provide production-ready configurations with:
- Proper error handling
- Rollback strategies
- Security considerations
- Documentation"""

    # -------------------------------------------------------------------------
    # Context Manager Support
    # -------------------------------------------------------------------------

    async def __aenter__(self) -> "LLMClient":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.shutdown()


# =============================================================================
# Factory Function
# =============================================================================


def create_llm_client(
    config: Optional[LLMClientConfig] = None,
    settings: Optional[Any] = None,
) -> LLMClient:
    """
    Factory function to create an LLM client.

    Args:
        config: Client configuration
        settings: Framework settings

    Returns:
        Configured LLM client (not yet initialized)
    """
    return LLMClient(config=config, settings=settings)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "LLMClient",
    "LLMClientConfig",
    "InvocationResult",
    "InvocationStatus",
    "create_llm_client",
]
