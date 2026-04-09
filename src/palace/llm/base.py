"""
Palace Framework - LLM Base Module

This module defines the base classes and interfaces for the LLM system.
It provides abstractions for:

- LLM Providers (Ollama, OpenAI, Anthropic, etc.)
- Model definitions and capabilities
- Request/Response handling
- Cost tracking interfaces
- Streaming support

The design follows the Strategy pattern to allow easy swapping of providers
while maintaining a consistent interface for the rest of the framework.

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │                      LLMClient                            │
    │  ┌─────────────────────────────────────────────────┐    │
    │  │                  LLMRouter                        │    │
    │  │  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │    │
    │  │  │ RoleMapping │  │ ModelConfig │  │CostTracker│ │    │
    │  │  └─────────────┘  └─────────────┘  └──────────┘ │    │
    │  └─────────────────────────────────────────────────┘    │
    │                       │                                  │
    │  ┌────────────────────┼────────────────────────────┐    │
    │  │                    ▼                             │    │
    │  │               LLMProvider (Interface)           │    │
    │  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │    │
    │  │  │ Ollama   │  │ OpenAI   │  │  Anthropic   │  │    │
    │  │  │ Provider │  │ Provider │  │  Provider    │  │    │
    │  │  └──────────┘  └──────────┘  └──────────────┘  │    │
    │  └─────────────────────────────────────────────────┘    │
    └─────────────────────────────────────────────────────────┘

Usage:
    from palace.llm import LLMClient, LLMConfig

    # Create client with configuration
    config = LLMConfig(
        provider="ollama",
        base_url="https://ollama-cloud.example.com",
        api_key="your-api-key"
    )
    client = LLMClient(config)

    # Invoke with role-based model selection
    response = await client.invoke(
        prompt="Write a REST endpoint for user management",
        role=LLMRole.BACKEND
    )

    # Or invoke with specific model
    response = await client.invoke(
        prompt="Optimize this SQL query",
        model="deepseek-v3.2"
    )
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
)
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# =============================================================================
# Type Variables
# =============================================================================

T = TypeVar("T")
"""Generic type variable for responses."""


# =============================================================================
# Enums
# =============================================================================


class LLMRole(str, Enum):
    """
    Roles that map to specific LLM models.

    Each role represents a different type of task or expertise
    and is associated with a specific model optimized for that role.
    """

    ORCHESTRATOR = "orchestrator"
    """Orchestration and coordination tasks - uses qwen3.5"""

    BACKEND = "backend"
    """Backend development tasks - uses qwen3-coder-next"""

    FRONTEND = "frontend"
    """Frontend development tasks - uses qwen3-coder-next"""

    DEVOPS = "devops"
    """DevOps and CI/CD tasks - uses qwen3.5"""

    INFRA = "infra"
    """Infrastructure as code tasks - uses qwen3-coder-next"""

    DBA = "dba"
    """Database administration tasks - uses deepseek-v3.2"""

    QA = "qa"
    """Quality assurance and testing - uses gemma4:31b"""

    DESIGNER = "designer"
    """UI/UX design tasks - uses mistral-large"""

    REVIEWER = "reviewer"
    """Code review and architecture - uses mistral-large"""

    EMBEDDING = "embedding"
    """Embedding generation - uses nomic-embed-text"""


class LLMProviderType(str, Enum):
    """
    Supported LLM providers.

    Each provider has its own implementation but shares
    the same interface for consistency.
    """

    OLLAMA = "ollama"
    """Ollama Cloud or local Ollama instance"""

    OPENAI = "openai"
    """OpenAI API (GPT models)"""

    ANTHROPIC = "anthropic"
    """Anthropic API (Claude models)"""

    AZURE = "azure"
    """Azure OpenAI Service"""

    CUSTOM = "custom"
    """Custom provider for extensions"""


class MessageRole(str, Enum):
    """Roles in a conversation."""

    SYSTEM = "system"
    """System message (instructions, context)"""

    USER = "user"
    """User message (input, questions)"""

    ASSISTANT = "assistant"
    """Assistant message (responses)"""

    TOOL = "tool"
    """Tool execution result"""


class FinishReason(str, Enum):
    """Reason for completion of generation."""

    STOP = "stop"
    """Normal completion"""

    LENGTH = "length"
    """Max tokens reached"""

    TOOL_CALL = "tool_call"
    """Tool call requested"""

    CONTENT_FILTER = "content_filter"
    """Content filter triggered"""

    ERROR = "error"
    """Error during generation"""


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ModelCapabilities:
    """
    Capabilities and features of an LLM model.

    Used to determine if a model supports specific features
    like streaming, function calling, vision, etc.
    """

    supports_streaming: bool = True
    """Whether the model supports streaming responses."""

    supports_function_calling: bool = True
    """Whether the model supports function/tool calling."""

    supports_vision: bool = False
    """Whether the model supports image inputs."""

    supports_json_mode: bool = True
    """Whether the model supports JSON output mode."""

    supports_system_prompt: bool = True
    """Whether the model supports system prompts."""

    max_context_tokens: int = 4096
    """Maximum context window size in tokens."""

    max_output_tokens: int = 4096
    """Maximum output tokens in a single response."""

    supports_temperature: bool = True
    """Whether the model supports temperature parameter."""

    supports_top_p: bool = True
    """Whether the model supports top_p parameter."""


@dataclass
class ModelInfo:
    """
    Information about an LLM model.

    Contains metadata about the model including its name,
    capabilities, costs, and default parameters.
    """

    name: str
    """Model identifier (e.g., 'qwen3-coder-next')"""

    display_name: str
    """Human-readable name (e.g., 'Qwen3 Coder Next')"""

    provider: LLMProviderType
    """Provider that offers this model."""

    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    """Model capabilities and features."""

    default_temperature: float = 0.7
    """Default temperature for this model."""

    default_max_tokens: int = 4096
    """Default maximum tokens for generation."""

    input_cost_per_1k_tokens: float = 0.0
    """Cost per 1,000 input tokens (in USD)."""

    output_cost_per_1k_tokens: float = 0.0
    """Cost per 1,000 output tokens (in USD)."""

    tags: List[str] = field(default_factory=list)
    """Tags for categorization (e.g., 'coding', 'reasoning')."""

    description: str = ""
    """Description of the model's strengths and use cases."""

    context_window: int = 4096
    """Maximum context window size."""

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate the cost for a generation.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        input_cost = (input_tokens / 1000) * self.input_cost_per_1k_tokens
        output_cost = (output_tokens / 1000) * self.output_cost_per_1k_tokens
        return input_cost + output_cost

    def supports_role(self, role: LLMRole) -> bool:
        """
        Check if this model is suitable for a given role.

        Args:
            role: The role to check

        Returns:
            True if the model supports the role
        """
        # Map roles to tags
        role_tags = {
            LLMRole.ORCHESTRATOR: ["reasoning", "orchestration"],
            LLMRole.BACKEND: ["coding", "backend"],
            LLMRole.FRONTEND: ["coding", "frontend"],
            LLMRole.DEVOPS: ["reasoning", "devops"],
            LLMRole.INFRA: ["coding", "infrastructure"],
            LLMRole.DBA: ["reasoning", "database", "sql"],
            LLMRole.QA: ["reasoning", "testing", "quality"],
            LLMRole.DESIGNER: ["reasoning", "design", "ui"],
            LLMRole.REVIEWER: ["reasoning", "review", "analysis"],
            LLMRole.EMBEDDING: ["embedding"],
        }

        required_tags = role_tags.get(role, [])
        return any(tag in self.tags for tag in required_tags)


@dataclass
class TokenUsage:
    """
    Token usage information for a generation.

    Tracks input, output, and total tokens for cost calculation
    and monitoring.
    """

    input_tokens: int = 0
    """Number of input (prompt) tokens."""

    output_tokens: int = 0
    """Number of output (completion) tokens."""

    total_tokens: int = 0
    """Total tokens (input + output)."""

    cached_tokens: int = 0
    """Number of tokens served from cache."""

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """Add two TokenUsage instances."""
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cached_tokens=self.cached_tokens + other.cached_tokens,
        )

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cached_tokens": self.cached_tokens,
        }


# =============================================================================
# Pydantic Models
# =============================================================================


class LLMConfig(BaseModel):
    """
    Configuration for the LLM client.

    This configuration is used to initialize the LLM client
    and can be customized for different providers and use cases.
    """

    # Provider configuration
    provider: LLMProviderType = Field(
        default=LLMProviderType.OLLAMA,
        description="LLM provider to use",
    )
    base_url: Optional[str] = Field(
        default=None,
        description="Base URL for the provider API",
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for authentication",
    )

    # Model defaults
    default_model: Optional[str] = Field(
        default=None,
        description="Default model to use if not specified",
    )
    default_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Default temperature for generation",
    )
    default_max_tokens: int = Field(
        default=4096,
        ge=1,
        le=128000,
        description="Default maximum tokens for generation",
    )

    # Timeouts and retries
    timeout: int = Field(
        default=300,
        ge=1,
        description="Request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retries",
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.0,
        le=30.0,
        description="Delay between retries in seconds",
    )

    # Role-to-model mapping
    role_model_mapping: Dict[str, str] = Field(
        default_factory=lambda: {
            LLMRole.ORCHESTRATOR.value: "qwen3.5",
            LLMRole.BACKEND.value: "qwen3-coder-next",
            LLMRole.FRONTEND.value: "qwen3-coder-next",
            LLMRole.DEVOPS.value: "qwen3.5",
            LLMRole.INFRA.value: "qwen3-coder-next",
            LLMRole.DBA.value: "deepseek-v3.2",
            LLMRole.QA.value: "gemma4:31b",
            LLMRole.DESIGNER.value: "mistral-large",
            LLMRole.REVIEWER.value: "mistral-large",
            LLMRole.EMBEDDING.value: "nomic-embed-text",
        },
        description="Mapping of roles to model names",
    )

    # Cost tracking
    track_costs: bool = Field(
        default=True,
        description="Whether to track token costs",
    )
    cost_limit: Optional[float] = Field(
        default=None,
        description="Maximum cost limit per request (in USD)",
    )

    # Caching
    enable_caching: bool = Field(
        default=False,
        description="Whether to enable response caching",
    )
    cache_ttl: int = Field(
        default=3600,
        description="Cache time-to-live in seconds",
    )

    # Additional options
    options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provider-specific options",
    )

    class Config:
        use_enum_values = True


class Message(BaseModel):
    """
    A message in a conversation.

    Messages are the basic unit of communication with LLMs,
    containing a role and content.
    """

    role: MessageRole = Field(
        ...,
        description="Role of the message sender",
    )
    content: str = Field(
        ...,
        description="Content of the message",
    )
    name: Optional[str] = Field(
        default=None,
        description="Name of the sender (for tool messages)",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    class Config:
        use_enum_values = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        result = {"role": self.role, "content": self.content}
        if self.name:
            result["name"] = self.name
        return result


class ToolDefinition(BaseModel):
    """
    Definition of a tool/function that can be called by the LLM.

    Tools allow LLMs to perform actions by calling external functions.
    """

    name: str = Field(
        ...,
        description="Name of the tool",
    )
    description: str = Field(
        ...,
        description="Description of what the tool does",
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON schema for tool parameters",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolCall(BaseModel):
    """
    A tool call requested by the LLM.

    When the LLM decides to use a tool, it returns a tool call
    with the name and arguments.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the tool call",
    )
    name: str = Field(
        ...,
        description="Name of the tool to call",
    )
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments to pass to the tool",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": self.arguments,
            },
        }


class LLMRequest(BaseModel):
    """
    A request to the LLM.

    Contains all the information needed to make a generation request,
    including messages, tools, and parameters.
    """

    # Identification
    request_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this request",
    )

    # Messages
    messages: List[Message] = Field(
        default_factory=list,
        description="Conversation messages",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="System prompt to prepend",
    )

    # Model selection
    model: Optional[str] = Field(
        default=None,
        description="Specific model to use",
    )
    role: Optional[LLMRole] = Field(
        default=None,
        description="Role for model selection (alternative to model)",
    )

    # Generation parameters
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum tokens to generate",
    )
    top_p: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Top-p sampling parameter",
    )
    stop: Optional[List[str]] = Field(
        default=None,
        description="Stop sequences",
    )

    # Tools
    tools: Optional[List[ToolDefinition]] = Field(
        default=None,
        description="Tools available to the LLM",
    )
    tool_choice: Optional[str] = Field(
        default=None,
        description="How to choose tools ('auto', 'none', or specific)",
    )

    # Response format
    response_format: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Desired response format",
    )

    # Streaming
    stream: bool = Field(
        default=False,
        description="Whether to stream the response",
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for tracking",
    )

    class Config:
        use_enum_values = True

    def get_model_for_role(self, config: LLMConfig) -> str:
        """
        Get the model name for a role.

        Args:
            config: LLM configuration with role mapping

        Returns:
            Model name for the role
        """
        if self.model:
            return self.model

        if self.role:
            return config.role_model_mapping.get(
                self.role.value,
                config.default_model or "qwen3.5",
            )

        return config.default_model or "qwen3.5"


class LLMResponse(BaseModel):
    """
    A response from the LLM.

    Contains the generated content, tool calls, and metadata
    about the generation.
    """

    # Identification
    request_id: str = Field(
        ...,
        description="ID of the request this responds to",
    )
    response_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this response",
    )

    # Content
    content: str = Field(
        default="",
        description="Generated content",
    )
    tool_calls: List[ToolCall] = Field(
        default_factory=list,
        description="Tool calls requested by the LLM",
    )

    # Model info
    model: str = Field(
        ...,
        description="Model used for generation",
    )
    provider: LLMProviderType = Field(
        ...,
        description="Provider that generated this response",
    )

    # Token usage
    usage: TokenUsage = Field(
        default_factory=TokenUsage,
        description="Token usage information",
    )

    # Generation metadata
    finish_reason: FinishReason = Field(
        default=FinishReason.STOP,
        description="Reason for completion",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of generation",
    )

    # Cost
    cost: float = Field(
        default=0.0,
        description="Cost of this generation in USD",
    )

    # Latency
    latency_ms: int = Field(
        default=0,
        description="Generation latency in milliseconds",
    )

    # Additional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional response metadata",
    )

    class Config:
        use_enum_values = True

    @property
    def is_empty(self) -> bool:
        """Check if the response is empty."""
        return not self.content and not self.tool_calls

    @property
    def has_tool_calls(self) -> bool:
        """Check if the response has tool calls."""
        return len(self.tool_calls) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "response_id": self.response_id,
            "content": self.content,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "model": self.model,
            "provider": self.provider,
            "usage": self.usage.to_dict(),
            "finish_reason": self.finish_reason,
            "cost": self.cost,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
        }


class StreamChunk(BaseModel):
    """
    A chunk of a streaming response.

    When streaming is enabled, the response is returned as
    a sequence of chunks.
    """

    request_id: str = Field(
        ...,
        description="ID of the request",
    )
    chunk_id: int = Field(
        default=0,
        description="Sequence number of this chunk",
    )
    content: str = Field(
        default="",
        description="Content delta for this chunk",
    )
    tool_calls: List[ToolCall] = Field(
        default_factory=list,
        description="Tool call deltas",
    )
    finish_reason: Optional[FinishReason] = Field(
        default=None,
        description="Finish reason if this is the last chunk",
    )
    usage: Optional[TokenUsage] = Field(
        default=None,
        description="Token usage (only in last chunk)",
    )

    class Config:
        use_enum_values = True


# =============================================================================
# Abstract Base Classes
# =============================================================================


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM providers (Ollama, OpenAI, Anthropic, etc.) must implement
    this interface to be compatible with the LLM client.

    This design allows for easy swapping of providers while maintaining
    a consistent interface for the rest of the framework.
    """

    provider_type: LLMProviderType
    """The type of this provider."""

    @abstractmethod
    def __init__(self, config: LLMConfig):
        """
        Initialize the provider with configuration.

        Args:
            config: LLM configuration
        """
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the provider connection.

        This method should be called before any other operations.
        It validates configuration, sets up connections, and
        prepares the provider for use.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close the provider connection.

        Clean up resources and close any open connections.
        """
        pass

    @abstractmethod
    async def invoke(self, request: LLMRequest) -> LLMResponse:
        """
        Invoke the LLM with a request.

        This is the main method for generating responses.
        It takes a request and returns a response.

        Args:
            request: The LLM request

        Returns:
            LLM response with generated content

        Raises:
            LLMError: If generation fails
        """
        pass

    @abstractmethod
    async def invoke_stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        """
        Invoke the LLM with streaming.

        Returns chunks of the response as they are generated.

        Args:
            request: The LLM request (stream=True)

        Yields:
            StreamChunk objects

        Raises:
            LLMError: If generation fails
        """
        pass

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            LLMError: If embedding fails
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """
        List available models from this provider.

        Returns:
            List of available models with their information
        """
        pass

    @abstractmethod
    async def get_model_info(self, model: str) -> Optional[ModelInfo]:
        """
        Get information about a specific model.

        Args:
            model: Model name

        Returns:
            Model information or None if not found
        """
        pass

    @abstractmethod
    async def count_tokens(self, text: str, model: str) -> int:
        """
        Count the number of tokens in a text.

        Args:
            text: Text to count tokens for
            model: Model to use for tokenization

        Returns:
            Number of tokens
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and responsive.

        Returns:
            True if healthy, False otherwise
        """
        pass


class CostTracker(ABC):
    """
    Abstract base class for cost tracking.

    Cost trackers monitor token usage and calculate costs
    for LLM operations.
    """

    @abstractmethod
    def track_request(
        self,
        request_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ) -> None:
        """
        Track a request's cost.

        Args:
            request_id: Unique request identifier
            model: Model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost: Cost in USD
        """
        pass

    @abstractmethod
    def get_total_cost(self, model: Optional[str] = None) -> float:
        """
        Get total cost.

        Args:
            model: Optional model to filter by

        Returns:
            Total cost in USD
        """
        pass

    @abstractmethod
    def get_total_tokens(self, model: Optional[str] = None, direction: Optional[str] = None) -> int:
        """
        Get total tokens used.

        Args:
            model: Optional model to filter by
            direction: Optional direction to filter by ('input' or 'output')

        Returns:
            Total tokens
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics.

        Returns:
            Dictionary with usage statistics
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset all tracking data."""
        pass


class CacheProvider(ABC):
    """
    Abstract base class for response caching.

    Cache providers store and retrieve LLM responses to
    avoid redundant API calls for identical requests.
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[LLMResponse]:
        """
        Get a cached response.

        Args:
            key: Cache key

        Returns:
            Cached response or None
        """
        pass

    @abstractmethod
    async def set(self, key: str, response: LLMResponse, ttl: int) -> None:
        """
        Cache a response.

        Args:
            key: Cache key
            response: Response to cache
            ttl: Time-to-live in seconds
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a cached response.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cached responses."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        pass


# =============================================================================
# Exceptions
# =============================================================================


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or "LLM_ERROR"
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


class ProviderError(LLMError):
    """Error from LLM provider."""

    def __init__(
        self,
        message: str,
        provider: LLMProviderType,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code="PROVIDER_ERROR", details=details)
        self.provider = provider


class ModelNotFoundError(LLMError):
    """Model not found error."""

    def __init__(self, model: str, provider: LLMProviderType):
        super().__init__(
            f"Model '{model}' not found for provider '{provider.value}'",
            code="MODEL_NOT_FOUND",
        )
        self.model = model
        self.provider = provider


class RateLimitError(LLMError):
    """Rate limit exceeded error."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
    ):
        super().__init__(message, code="RATE_LIMIT")
        self.retry_after = retry_after


class TokenLimitError(LLMError):
    """Token limit exceeded error."""

    def __init__(
        self,
        message: str = "Token limit exceeded",
        tokens: Optional[int] = None,
        limit: Optional[int] = None,
    ):
        super().__init__(message, code="TOKEN_LIMIT")
        self.tokens = tokens
        self.limit = limit


class CostLimitError(LLMError):
    """Cost limit exceeded error."""

    def __init__(
        self,
        message: str = "Cost limit exceeded",
        cost: Optional[float] = None,
        limit: Optional[float] = None,
    ):
        super().__init__(message, code="COST_LIMIT")
        self.cost = cost
        self.limit = limit


class TimeoutError(LLMError):
    """Request timeout error."""

    def __init__(self, message: str = "Request timed out", timeout: Optional[int] = None):
        super().__init__(message, code="TIMEOUT")
        self.timeout = timeout


class ContentFilterError(LLMError):
    """Content filter triggered error."""

    def __init__(self, message: str = "Content filter triggered"):
        super().__init__(message, code="CONTENT_FILTER")


# =============================================================================
# Callbacks and Hooks
# =============================================================================


BeforeRequestCallback = Callable[[LLMRequest], LLMRequest]
"""Callback called before a request is sent. Can modify the request."""

AfterResponseCallback = Callable[[LLMRequest, LLMResponse], LLMResponse]
"""Callback called after a response is received. Can modify the response."""

OnErrorCallback = Callable[[LLMRequest, Exception], None]
"""Callback called when an error occurs."""

OnStreamChunkCallback = Callable[[StreamChunk], None]
"""Callback called for each chunk in a streaming response."""
