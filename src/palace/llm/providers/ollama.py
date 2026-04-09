"""
Ollama Provider Implementation for Palace Framework.

This module provides the Ollama Cloud provider implementation for the LLM router.
It supports multiple models, streaming, cost tracking, and robust error handling.

Features:
- Multiple model support via Ollama Cloud API
- Streaming and non-streaming responses
- Automatic retry with exponential backoff
- Request/response logging
- Token usage tracking
- Connection pooling
- Timeout handling
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    AsyncIterator,
    Callable,
    Dict,
    List,
    Optional,
    Union,
)

import httpx
import structlog

from palace.llm.base import (
    LLMCapability,
    LLMProvider,
    LLMProviderConfig,
    LLMResponse,
    LLMUsage,
)

if TYPE_CHECKING:
    from palace.llm.models import ModelDefinition

logger = structlog.get_logger()


class OllamaModelStatus(str, Enum):
    """Status of an Ollama model."""

    AVAILABLE = "available"
    LOADING = "loading"
    ERROR = "error"
    NOT_FOUND = "not_found"


@dataclass
class OllamaConfig(LLMProviderConfig):
    """Configuration for Ollama provider."""

    base_url: str = "http://localhost:11434"
    """Base URL for Ollama API."""

    api_key: Optional[str] = None
    """API key for authentication (if required)."""

    timeout: int = 300
    """Request timeout in seconds."""

    max_retries: int = 3
    """Maximum number of retries for failed requests."""

    retry_delay: float = 1.0
    """Initial delay between retries (exponential backoff)."""

    max_connections: int = 10
    """Maximum number of concurrent connections."""

    default_model: str = "qwen3.5"
    """Default model to use when not specified."""

    default_options: Dict[str, Any] = field(
        default_factory=lambda: {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "num_ctx": 4096,
            "num_predict": 4096,
        }
    )
    """Default options for model generation."""


@dataclass
class OllamaModelInfo:
    """Information about an available Ollama model."""

    name: str
    """Model name."""

    size: Optional[int] = None
    """Model size in bytes."""

    digest: Optional[str] = None
    """Model digest/hash."""

    modified_at: Optional[datetime] = None
    """Last modification time."""

    details: Dict[str, Any] = field(default_factory=dict)
    """Additional model details."""

    capabilities: List[LLMCapability] = field(default_factory=list)
    """Model capabilities."""


@dataclass
class OllamaRequest:
    """Request to send to Ollama API."""

    model: str
    """Model to use."""

    prompt: str
    """Prompt to send."""

    system: Optional[str] = None
    """System prompt."""

    context: Optional[List[int]] = None
    """Context for conversation."""

    stream: bool = False
    """Whether to stream the response."""

    raw: bool = False
    """Whether to return raw response."""

    options: Dict[str, Any] = field(default_factory=dict)
    """Model options."""

    format: Optional[str] = None
    """Output format (json, etc.)."""


class OllamaError(Exception):
    """Base exception for Ollama errors."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or "OLLAMA_ERROR"
        self.details = details or {}


class OllamaConnectionError(OllamaError):
    """Error connecting to Ollama."""

    pass


class OllamaTimeoutError(OllamaError):
    """Error when request times out."""

    pass


class OllamaModelError(OllamaError):
    """Error related to model operations."""

    pass


class OllamaRateLimitError(OllamaError):
    """Error when rate limit is exceeded."""

    pass


class OllamaProvider(LLMProvider):
    """
    Ollama Cloud provider implementation.

    This provider supports Ollama Cloud API for inference with multiple models.
    It handles connection management, retries, streaming, and cost tracking.

    Example:
        >>> config = OllamaConfig(base_url="https://ollama.example.com")
        >>> provider = OllamaProvider(config)
        >>> await provider.initialize()
        >>> response = await provider.invoke("Hello, world!", model="qwen3.5")
        >>> print(response.content)

    Attributes:
        config: Ollama configuration
        client: HTTPX async client
        models: Available models cache
        usage_tracker: Usage tracking callback
    """

    def __init__(self, config: OllamaConfig):
        """
        Initialize the Ollama provider.

        Args:
            config: Ollama configuration
        """
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._models_cache: Dict[str, OllamaModelInfo] = {}
        self._usage_callback: Optional[Callable[[LLMUsage], None]] = None
        self._initialized = False
        self._request_count = 0
        self._total_tokens = 0

    async def initialize(self) -> None:
        """
        Initialize the Ollama provider.

        Creates the HTTP client and validates the connection.
        """
        if self._initialized:
            return

        # Create async client with connection pooling
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=httpx.Timeout(self.config.timeout),
            limits=httpx.Limits(max_connections=self.config.max_connections),
            headers=self._build_headers(),
        )

        # Validate connection
        try:
            await self._validate_connection()
            await self._refresh_models_cache()
        except Exception as e:
            logger.warning(
                "ollama_connection_warning",
                error=str(e),
                base_url=self.config.base_url,
            )
            # Don't fail initialization, allow lazy connection

        self._initialized = True
        logger.info(
            "ollama_provider_initialized",
            base_url=self.config.base_url,
            default_model=self.config.default_model,
        )

    async def shutdown(self) -> None:
        """Shutdown the provider and release resources."""
        if self._client:
            await self._client.aclose()
            self._client = None

        self._initialized = False
        logger.info("ollama_provider_shutdown")

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    async def _validate_connection(self) -> None:
        """Validate connection to Ollama server."""
        if not self._client:
            raise OllamaConnectionError("Client not initialized")

        try:
            response = await self._client.get("/api/tags", timeout=10.0)
            response.raise_for_status()
            logger.debug("ollama_connection_validated")
        except httpx.TimeoutException:
            raise OllamaTimeoutError(
                "Connection timeout",
                code="CONNECTION_TIMEOUT",
                details={"timeout": 10},
            )
        except httpx.HTTPStatusError as e:
            raise OllamaConnectionError(
                f"HTTP error: {e.response.status_code}",
                code="HTTP_ERROR",
                details={"status_code": e.response.status_code},
            )
        except httpx.RequestError as e:
            raise OllamaConnectionError(
                f"Connection failed: {str(e)}",
                code="CONNECTION_FAILED",
                details={"error": str(e)},
            )

    async def _refresh_models_cache(self) -> None:
        """Refresh the cache of available models."""
        if not self._client:
            return

        try:
            response = await self._client.get("/api/tags")
            response.raise_for_status()
            data = response.json()

            self._models_cache.clear()
            for model_data in data.get("models", []):
                model_info = self._parse_model_info(model_data)
                self._models_cache[model_info.name] = model_info

            logger.debug(
                "ollama_models_cached",
                count=len(self._models_cache),
            )
        except Exception as e:
            logger.warning("ollama_models_cache_failed", error=str(e))

    def _parse_model_info(self, data: Dict[str, Any]) -> OllamaModelInfo:
        """Parse model information from API response."""
        name = data.get("name", "unknown")

        # Parse capabilities based on model name/type
        capabilities = self._infer_capabilities(name)

        return OllamaModelInfo(
            name=name,
            size=data.get("size"),
            digest=data.get("digest"),
            modified_at=self._parse_datetime(data.get("modified_at")),
            details=data.get("details", {}),
            capabilities=capabilities,
        )

    def _infer_capabilities(self, model_name: str) -> List[LLMCapability]:
        """Infer capabilities from model name."""
        capabilities = [LLMCapability.COMPLETION]

        model_lower = model_name.lower()

        if "coder" in model_lower or "code" in model_lower:
            capabilities.append(LLMCapability.CODE_GENERATION)
            capabilities.append(LLMCapability.CODE_COMPLETION)

        if "embed" in model_lower:
            capabilities.append(LLMCapability.EMBEDDING)

        if "chat" in model_lower or "instruct" in model_lower:
            capabilities.append(LLMCapability.CHAT)

        # Most models support these
        capabilities.append(LLMCapability.INSTRUCTION_FOLLOWING)

        return capabilities

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """Parse datetime from string."""
        if not value:
            return None
        try:
            # ISO format
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    async def invoke(
        self,
        prompt: str,
        model: Optional[str] = None,
        *,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Invoke the LLM with a prompt.

        Args:
            prompt: The prompt to send
            model: Model to use (defaults to config.default_model)
            system_prompt: System prompt to prepend
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stop_sequences: Stop sequences
            **kwargs: Additional model-specific options

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            OllamaError: If invocation fails
        """
        if not self._initialized:
            await self.initialize()

        model = model or self.config.default_model
        request = self._build_request(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences,
            **kwargs,
        )

        # Execute with retry
        response = await self._execute_with_retry(request)

        # Track usage
        if self._usage_callback:
            self._usage_callback(response.usage)

        self._request_count += 1
        self._total_tokens += response.usage.total_tokens

        return response

    async def invoke_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        *,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """
        Invoke the LLM with streaming response.

        Args:
            prompt: The prompt to send
            model: Model to use
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            stop_sequences: Stop sequences
            **kwargs: Additional options

        Yields:
            Chunks of generated content

        Raises:
            OllamaError: If invocation fails
        """
        if not self._initialized:
            await self.initialize()

        model = model or self.config.default_model
        request = self._build_request(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences,
            stream=True,
            **kwargs,
        )

        async for chunk in self._execute_stream(request):
            yield chunk

    def _build_request(
        self,
        prompt: str,
        model: str,
        *,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> OllamaRequest:
        """Build an Ollama request from parameters."""
        options = dict(self.config.default_options)

        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if stop_sequences:
            options["stop"] = stop_sequences

        # Add any additional kwargs
        options.update(kwargs.get("options", {}))

        return OllamaRequest(
            model=model,
            prompt=prompt,
            system=system_prompt,
            stream=stream,
            options=options,
            format=kwargs.get("format"),
        )

    async def _execute_with_retry(
        self,
        request: OllamaRequest,
    ) -> LLMResponse:
        """Execute request with exponential backoff retry."""
        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries):
            try:
                return await self._execute_request(request)
            except OllamaRateLimitError as e:
                # Rate limit - wait longer
                wait_time = float(
                    e.details.get("retry_after", self.config.retry_delay * (2**attempt))
                )
                logger.warning(
                    "ollama_rate_limit",
                    attempt=attempt + 1,
                    max_retries=self.config.max_retries,
                    wait_time=wait_time,
                )
                await asyncio.sleep(wait_time)
                last_error = e
            except OllamaTimeoutError as e:
                # Timeout - retry with exponential backoff
                wait_time = self.config.retry_delay * (2**attempt)
                logger.warning(
                    "ollama_timeout",
                    attempt=attempt + 1,
                    max_retries=self.config.max_retries,
                    wait_time=wait_time,
                )
                await asyncio.sleep(wait_time)
                last_error = e
            except OllamaConnectionError as e:
                # Connection error - retry
                wait_time = self.config.retry_delay * (2**attempt)
                logger.warning(
                    "ollama_connection_error",
                    attempt=attempt + 1,
                    max_retries=self.config.max_retries,
                    error=str(e),
                )
                await asyncio.sleep(wait_time)
                last_error = e
            except OllamaError as e:
                # Other errors - don't retry
                raise e

        # All retries exhausted
        raise last_error or OllamaError("Max retries exceeded")

    async def _execute_request(
        self,
        request: OllamaRequest,
    ) -> LLMResponse:
        """Execute a single request to Ollama API."""
        if not self._client:
            raise OllamaConnectionError("Client not initialized")

        url = "/api/generate" if not request.context else "/api/chat"
        payload = self._build_payload(request)

        start_time = time.time()

        try:
            response = await self._client.post(
                url,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        except httpx.TimeoutException as e:
            raise OllamaTimeoutError(
                f"Request timed out: {str(e)}",
                code="TIMEOUT",
                details={"timeout": self.config.timeout},
            )
        except httpx.HTTPStatusError as e:
            await self._handle_http_error(e)
        except httpx.RequestError as e:
            raise OllamaConnectionError(
                f"Request failed: {str(e)}",
                code="REQUEST_ERROR",
                details={"error": str(e)},
            )
        except json.JSONDecodeError as e:
            raise OllamaError(
                f"Invalid JSON response: {str(e)}",
                code="JSON_ERROR",
                details={"error": str(e)},
            )

        elapsed_time = time.time() - start_time

        return self._parse_response(data, request, elapsed_time)

    async def _execute_stream(
        self,
        request: OllamaRequest,
    ) -> AsyncGenerator[str, None]:
        """Execute a streaming request."""
        if not self._client:
            raise OllamaConnectionError("Client not initialized")

        url = "/api/generate"
        payload = self._build_payload(request)

        try:
            async with self._client.stream(
                "POST",
                url,
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                    except json.JSONDecodeError:
                        continue

        except httpx.TimeoutException:
            raise OllamaTimeoutError("Streaming request timed out")
        except httpx.HTTPStatusError as e:
            await self._handle_http_error(e)
        except httpx.RequestError as e:
            raise OllamaConnectionError(f"Streaming request failed: {str(e)}")

    def _build_payload(self, request: OllamaRequest) -> Dict[str, Any]:
        """Build API request payload."""
        payload: Dict[str, Any] = {
            "model": request.model,
            "prompt": request.prompt,
            "stream": request.stream,
        }

        if request.system:
            payload["system"] = request.system

        if request.context:
            payload["context"] = request.context

        if request.options:
            payload["options"] = request.options

        if request.format:
            payload["format"] = request.format

        if request.raw:
            payload["raw"] = request.raw

        return payload

    def _parse_response(
        self,
        data: Dict[str, Any],
        request: OllamaRequest,
        elapsed_time: float,
    ) -> LLMResponse:
        """Parse API response into LLMResponse."""
        content = data.get("response", "")

        # Parse token usage
        prompt_eval_count = data.get("prompt_eval_count", 0)
        eval_count = data.get("eval_count", 0)

        usage = LLMUsage(
            prompt_tokens=prompt_eval_count,
            completion_tokens=eval_count,
            total_tokens=prompt_eval_count + eval_count,
            model=request.model,
            elapsed_seconds=elapsed_time,
        )

        # Parse metadata
        metadata: Dict[str, Any] = {
            "model": request.model,
            "created_at": data.get("created_at"),
            "done": data.get("done", True),
            "context": data.get("context"),
        }

        # Extract finish reason
        finish_reason = None
        if data.get("done"):
            finish_reason = "stop"
        elif data.get("stopped"):
            finish_reason = data.get("stop_reason", "stop")

        return LLMResponse(
            content=content,
            model=request.model,
            usage=usage,
            finish_reason=finish_reason,
            metadata=metadata,
        )

    async def _handle_http_error(
        self,
        error: httpx.HTTPStatusError,
    ) -> None:
        """Handle HTTP error responses."""
        status_code = error.response.status_code

        try:
            error_data = error.response.json()
            error_message = error_data.get("error", str(error))
        except Exception:
            error_message = str(error)
            error_data = {}

        if status_code == 429:
            # Rate limit
            retry_after = error.response.headers.get("Retry-After")
            raise OllamaRateLimitError(
                error_message,
                code="RATE_LIMIT",
                details={"retry_after": int(retry_after) if retry_after else 60},
            )
        elif status_code == 404:
            # Model not found
            raise OllamaModelError(
                f"Model not found: {error_message}",
                code="MODEL_NOT_FOUND",
                details=error_data,
            )
        elif status_code >= 500:
            # Server error
            raise OllamaError(
                f"Server error: {error_message}",
                code="SERVER_ERROR",
                details={"status_code": status_code, **error_data},
            )
        else:
            # Client error
            raise OllamaError(
                f"HTTP error {status_code}: {error_message}",
                code="HTTP_ERROR",
                details={"status_code": status_code, **error_data},
            )

    async def list_models(self) -> List[OllamaModelInfo]:
        """
        List available models.

        Returns:
            List of available model information
        """
        await self._refresh_models_cache()
        return list(self._models_cache.values())

    async def get_model_info(
        self,
        model: str,
    ) -> Optional[OllamaModelInfo]:
        """
        Get information about a specific model.

        Args:
            model: Model name

        Returns:
            Model information or None if not found
        """
        if model not in self._models_cache:
            await self._refresh_models_cache()

        return self._models_cache.get(model)

    async def check_model_availability(
        self,
        model: str,
    ) -> OllamaModelStatus:
        """
        Check if a model is available.

        Args:
            model: Model name

        Returns:
            Model availability status
        """
        info = await self.get_model_info(model)
        if info:
            return OllamaModelStatus.AVAILABLE

        # Try to pull model info
        try:
            if not self._client:
                return OllamaModelStatus.NOT_FOUND

            response = await self._client.post(
                "/api/show",
                json={"name": model},
            )

            if response.status_code == 200:
                return OllamaModelStatus.AVAILABLE
            elif response.status_code == 404:
                return OllamaModelStatus.NOT_FOUND
            else:
                return OllamaModelStatus.ERROR

        except Exception:
            return OllamaModelStatus.ERROR

    async def pull_model(
        self,
        model: str,
        *,
        stream: bool = False,
    ) -> bool:
        """
        Pull a model from Ollama registry.

        Args:
            model: Model name
            stream: Whether to stream progress

        Returns:
            True if successful

        Raises:
            OllamaModelError: If pull fails
        """
        if not self._client:
            raise OllamaConnectionError("Client not initialized")

        try:
            if stream:
                # Stream the pull progress
                async with self._client.stream(
                    "POST",
                    "/api/pull",
                    json={"name": model, "stream": True},
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            logger.debug("ollama_pull_progress", line=line)
            else:
                response = await self._client.post(
                    "/api/pull",
                    json={"name": model, "stream": False},
                )
                response.raise_for_status()

            # Refresh cache after pull
            await self._refresh_models_cache()
            return True

        except httpx.HTTPStatusError as e:
            await self._handle_http_error(e)
            return False
        except httpx.RequestError as e:
            raise OllamaConnectionError(f"Failed to pull model: {str(e)}")

    def set_usage_callback(
        self,
        callback: Optional[Callable[[LLMUsage], None]],
    ) -> None:
        """
        Set callback for usage tracking.

        Args:
            callback: Callback function or None to disable
        """
        self._usage_callback = callback

    def get_stats(self) -> Dict[str, Any]:
        """
        Get provider statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "provider": "ollama",
            "base_url": self.config.base_url,
            "initialized": self._initialized,
            "request_count": self._request_count,
            "total_tokens": self._total_tokens,
            "models_cached": len(self._models_cache),
            "default_model": self.config.default_model,
        }

    @property
    def name(self) -> str:
        """Provider name."""
        return "ollama"

    @property
    def capabilities(self) -> List[LLMCapability]:
        """Provider capabilities."""
        return [
            LLMCapability.COMPLETION,
            LLMCapability.CHAT,
            LLMCapability.STREAMING,
            LLMCapability.EMBEDDING,
        ]

    def supports_model(self, model: str) -> bool:
        """
        Check if provider supports a model.

        Args:
            model: Model name

        Returns:
            True if model is supported
        """
        return True  # Ollama supports dynamic model loading

    async def health_check(self) -> bool:
        """
        Check provider health.

        Returns:
            True if healthy
        """
        try:
            await self._validate_connection()
            return True
        except Exception:
            return False
