"""
Palace Framework - LLM Models Module

This module defines the available LLM models, their capabilities, and role-to-model
mappings. It provides a centralized configuration for model selection.

Model Categories:
    - Orchestrator Models: For routing and coordination (qwen3.5)
    - Development Models: For code generation (qwen3-coder-next)
    - Analysis Models: For code review and architecture (mistral-large)
    - Specialized Models: For specific tasks (deepseek-v3.2 for DBA, gemma4:31b for QA)

Usage:
    from palace.llm.models import ModelRegistry, get_model_for_role

    # Get model for a specific role
    model = get_model_for_role(AgentRole.BACKEND)

    # Get model by name
    model = ModelRegistry.get("qwen3-coder-next")
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentRole(str, Enum):
    """
    Agent roles that can be assigned to LLM models.

    Each role represents a specialized function in the software development
    lifecycle. Roles are mapped to specific models optimized for that function.
    """

    # Coordination roles
    ORCHESTRATOR = "orchestrator"
    """Central coordinator for routing and task management."""

    # Development roles
    BACKEND = "backend"
    """Backend development: APIs, services, business logic."""

    FRONTEND = "frontend"
    """Frontend development: UI components, client-side logic."""

    DEVOPS = "devops"
    """DevOps: CI/CD, deployment, automation."""

    INFRA = "infra"
    """Infrastructure: Terraform, Kubernetes, cloud resources."""

    DBA = "dba"
    """Database administration: SQL, migrations, optimization."""

    QA = "qa"
    """Quality assurance: testing, coverage, linting."""

    DESIGNER = "designer"
    """UI/UX design: interface design, accessibility."""

    REVIEWER = "reviewer"
    """Code review: architecture, best practices, security."""


class ModelCapability(str, Enum):
    """
    Capabilities that a model can have.

    Capabilities are used to match models to task requirements.
    """

    # Code capabilities
    CODE_GENERATION = "code_generation"
    """Can generate code from natural language."""

    CODE_COMPLETION = "code_completion"
    """Can complete partial code."""

    CODE_REVIEW = "code_review"
    """Can review and critique code."""

    # Analysis capabilities
    ARCHITECTURE = "architecture"
    """Can design and analyze software architecture."""

    DATABASE = "database"
    """Can design and optimize database schemas."""

    INFRASTRUCTURE = "infrastructure"
    """Can design and manage infrastructure."""

    # Quality capabilities
    TESTING = "testing"
    """Can generate and analyze tests."""

    SECURITY = "security"
    """Can analyze security vulnerabilities."""

    # Communication capabilities
    REASONING = "reasoning"
    """Can perform complex reasoning and planning."""

    SUMMARIZATION = "summarization"
    """Can summarize text and code."""

    CONVERSATION = "conversation"
    """Can maintain multi-turn conversations."""


class ModelProvider(str, Enum):
    """
    LLM providers supported by the framework.

    The framework is designed to be provider-agnostic, allowing
    easy integration of new providers.
    """

    OLLAMA = "ollama"
    """Ollama local/cloud inference."""

    OPENAI = "openai"
    """OpenAI API."""

    ANTHROPIC = "anthropic"
    """Anthropic Claude API."""

    AZURE = "azure"
    """Azure OpenAI API."""

    CUSTOM = "custom"
    """Custom endpoint."""


@dataclass
class ModelConfig:
    """
    Configuration for a specific LLM model.

    Contains all the information needed to use a model, including
    its capabilities, pricing, and generation parameters.

    Attributes:
        name: Unique identifier for the model
        provider: Provider that serves this model
        display_name: Human-readable name
        description: Brief description of the model
        context_window: Maximum context length in tokens
        capabilities: List of model capabilities
        default_params: Default generation parameters
        pricing: Cost per 1K tokens (prompt, completion)
        roles: Roles this model is suitable for
        tags: Additional tags for filtering
    """

    name: str
    provider: ModelProvider
    display_name: str
    description: str
    context_window: int
    capabilities: List[ModelCapability] = field(default_factory=list)
    default_params: Dict[str, Any] = field(default_factory=dict)
    pricing: Dict[str, float] = field(default_factory=lambda: {"prompt": 0.0, "completion": 0.0})
    roles: List[AgentRole] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def supports_capability(self, capability: ModelCapability) -> bool:
        """Check if model has a specific capability."""
        return capability in self.capabilities

    def supports_role(self, role: AgentRole) -> bool:
        """Check if model is suitable for a role."""
        return role in self.roles

    def get_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate cost for a generation.

        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Total cost in USD
        """
        prompt_cost = (prompt_tokens / 1000) * self.pricing.get("prompt", 0.0)
        completion_cost = (completion_tokens / 1000) * self.pricing.get("completion", 0.0)
        return prompt_cost + completion_cost

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "provider": self.provider.value,
            "display_name": self.display_name,
            "description": self.description,
            "context_window": self.context_window,
            "capabilities": [c.value for c in self.capabilities],
            "default_params": self.default_params,
            "pricing": self.pricing,
            "roles": [r.value for r in self.roles],
            "tags": self.tags,
        }


# =============================================================================
# Available Models
# =============================================================================

# Orchestrator and DevOps models
QWEN_35 = ModelConfig(
    name="qwen3.5:cloud",
    provider=ModelProvider.OLLAMA,
    display_name="Qwen 3.5 Cloud",
    description="Versatile model for orchestration and DevOps tasks (Ollama Cloud)",
    context_window=32768,
    capabilities=[
        ModelCapability.REASONING,
        ModelCapability.CONVERSATION,
        ModelCapability.SUMMARIZATION,
    ],
    default_params={
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 4096,
    },
    pricing={"prompt": 0.0, "completion": 0.0},  # Ollama is typically free/local
    roles=[AgentRole.ORCHESTRATOR, AgentRole.DEVOPS],
    tags=["orchestration", "devops", "reasoning"],
)

# Development models
QWEN_CODER_NEXT = ModelConfig(
    name="qwen3-coder-next:cloud",
    provider=ModelProvider.OLLAMA,
    display_name="Qwen 3 Coder Next Cloud",
    description="Advanced code generation model for development tasks (Ollama Cloud)",
    context_window=32768,
    capabilities=[
        ModelCapability.CODE_GENERATION,
        ModelCapability.CODE_COMPLETION,
        ModelCapability.CODE_REVIEW,
        ModelCapability.TESTING,
    ],
    default_params={
        "temperature": 0.3,
        "top_p": 0.95,
        "max_tokens": 8192,
    },
    pricing={"prompt": 0.0, "completion": 0.0},
    roles=[AgentRole.BACKEND, AgentRole.FRONTEND, AgentRole.INFRA],
    tags=["code", "development", "generation"],
)

# Database specialist
DEEPSEEK_V32 = ModelConfig(
    name="deepseek-v3.2:cloud",
    provider=ModelProvider.OLLAMA,
    display_name="DeepSeek V3.2 Cloud",
    description="Specialized model for database design and SQL (Ollama Cloud)",
    context_window=16384,
    capabilities=[
        ModelCapability.DATABASE,
        ModelCapability.CODE_GENERATION,
        ModelCapability.REASONING,
    ],
    default_params={
        "temperature": 0.2,
        "top_p": 0.95,
        "max_tokens": 4096,
    },
    pricing={"prompt": 0.0, "completion": 0.0},
    roles=[AgentRole.DBA],
    tags=["database", "sql", "optimization"],
)

# QA and Testing
GEMMA_4_31B = ModelConfig(
    name="gemma4:31b-cloud",
    provider=ModelProvider.OLLAMA,
    display_name="Gemma 4 31B Cloud",
    description="Large model for quality assurance and testing (Ollama Cloud)",
    context_window=8192,
    capabilities=[
        ModelCapability.TESTING,
        ModelCapability.CODE_REVIEW,
        ModelCapability.SECURITY,
        ModelCapability.REASONING,
    ],
    default_params={
        "temperature": 0.4,
        "top_p": 0.9,
        "max_tokens": 4096,
    },
    pricing={"prompt": 0.0, "completion": 0.0},
    roles=[AgentRole.QA],
    tags=["testing", "quality", "security"],
)

# Architecture and Review
MISTRAL_LARGE = ModelConfig(
    name="mistral-large-3:675b-cloud",
    provider=ModelProvider.OLLAMA,
    display_name="Mistral Large 3 675B Cloud",
    description="Large model for architecture design and code review (Ollama Cloud)",
    context_window=32768,
    capabilities=[
        ModelCapability.ARCHITECTURE,
        ModelCapability.CODE_REVIEW,
        ModelCapability.REASONING,
        ModelCapability.SECURITY,
    ],
    default_params={
        "temperature": 0.5,
        "top_p": 0.9,
        "max_tokens": 4096,
    },
    pricing={"prompt": 0.0, "completion": 0.0},
    roles=[AgentRole.DESIGNER, AgentRole.REVIEWER],
    tags=["architecture", "review", "design"],
)

# Embedding model
NOMIC_EMBED_TEXT = ModelConfig(
    name="nomic-embed-text",
    provider=ModelProvider.OLLAMA,
    display_name="Nomic Embed Text",
    description="Embedding model for semantic search and retrieval",
    context_window=8192,
    capabilities=[
        ModelCapability.SUMMARIZATION,
    ],
    default_params={
        "max_tokens": 8192,
    },
    pricing={"prompt": 0.0, "completion": 0.0},
    roles=[],
    tags=["embedding", "retrieval", "search"],
)


# =============================================================================
# Model Registry
# =============================================================================


class ModelRegistry:
    """
    Registry for all available LLM models.

    Provides a centralized registry for model configurations,
    allowing lookup by name, role, or capability.

    Example:
        # Get model by name
        model = ModelRegistry.get("qwen3-coder-next")

        # Get model for a role
        model = ModelRegistry.get_for_role(AgentRole.BACKEND)

        # Get all models with a capability
        models = ModelRegistry.get_with_capability(ModelCapability.CODE_GENERATION)
    """

    _models: Dict[str, ModelConfig] = {}
    _role_mapping: Dict[AgentRole, str] = {}
    _initialized: bool = False

    @classmethod
    def initialize(cls) -> None:
        """Initialize the registry with default models."""
        if cls._initialized:
            return

        # Register all models
        default_models = [
            QWEN_35,
            QWEN_CODER_NEXT,
            DEEPSEEK_V32,
            GEMMA_4_31B,
            MISTRAL_LARGE,
            NOMIC_EMBED_TEXT,
        ]

        for model in default_models:
            cls.register(model)

        cls._initialized = True

    @classmethod
    def register(cls, model: ModelConfig) -> None:
        """
        Register a model configuration.

        Args:
            model: Model configuration to register
        """
        cls._models[model.name] = model

        # Update role mapping
        for role in model.roles:
            cls._role_mapping[role] = model.name

    @classmethod
    def get(cls, name: str) -> Optional[ModelConfig]:
        """
        Get a model by name.

        Args:
            name: Model name

        Returns:
            Model configuration or None if not found
        """
        cls.initialize()
        return cls._models.get(name)

    @classmethod
    def get_for_role(cls, role: AgentRole) -> Optional[ModelConfig]:
        """
        Get the model assigned to a role.

        Args:
            role: Agent role

        Returns:
            Model configuration or None if not found
        """
        cls.initialize()
        model_name = cls._role_mapping.get(role)
        if model_name:
            return cls._models.get(model_name)
        return None

    @classmethod
    def get_with_capability(cls, capability: ModelCapability) -> List[ModelConfig]:
        """
        Get all models with a specific capability.

        Args:
            capability: Capability to search for

        Returns:
            List of matching model configurations
        """
        cls.initialize()
        return [model for model in cls._models.values() if model.supports_capability(capability)]

    @classmethod
    def get_all(cls) -> List[ModelConfig]:
        """
        Get all registered models.

        Returns:
            List of all model configurations
        """
        cls.initialize()
        return list(cls._models.values())

    @classmethod
    def get_names(cls) -> List[str]:
        """
        Get all registered model names.

        Returns:
            List of model names
        """
        cls.initialize()
        return list(cls._models.keys())

    @classmethod
    def set_role_mapping(cls, role: AgentRole, model_name: str) -> None:
        """
        Override the default role-to-model mapping.

        Args:
            role: Agent role
            model_name: Model name to assign
        """
        cls.initialize()
        if model_name not in cls._models:
            raise ValueError(f"Model '{model_name}' is not registered")
        cls._role_mapping[role] = model_name

    @classmethod
    def clear(cls) -> None:
        """Clear all registered models."""
        cls._models.clear()
        cls._role_mapping.clear()
        cls._initialized = False


# =============================================================================
# Convenience Functions
# =============================================================================


def get_model_for_role(role: AgentRole) -> ModelConfig:
    """
    Get the model assigned to a role.

    Args:
        role: Agent role

    Returns:
        Model configuration

    Raises:
        ValueError: If no model is assigned to the role
    """
    model = ModelRegistry.get_for_role(role)
    if model is None:
        raise ValueError(f"No model assigned to role: {role}")
    return model


def get_model(name: str) -> ModelConfig:
    """
    Get a model by name.

    Args:
        name: Model name

    Returns:
        Model configuration

    Raises:
        ValueError: If model is not found
    """
    model = ModelRegistry.get(name)
    if model is None:
        raise ValueError(f"Model not found: {name}")
    return model


def list_models() -> List[ModelConfig]:
    """
    List all registered models.

    Returns:
        List of model configurations
    """
    return ModelRegistry.get_all()


def list_model_names() -> List[str]:
    """
    List all registered model names.

    Returns:
        List of model names
    """
    return ModelRegistry.get_names()


# Initialize on module load
ModelRegistry.initialize()


__all__ = [
    # Enums
    "AgentRole",
    "ModelCapability",
    "ModelProvider",
    # Config
    "ModelConfig",
    # Registry
    "ModelRegistry",
    # Convenience functions
    "get_model_for_role",
    "get_model",
    "list_models",
    "list_model_names",
    # Pre-defined models
    "QWEN_35",
    "QWEN_CODER_NEXT",
    "DEEPSEEK_V32",
    "GEMMA_4_31B",
    "MISTRAL_LARGE",
    "NOMIC_EMBED_TEXT",
]
