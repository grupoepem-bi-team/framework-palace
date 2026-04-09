"""
Palace Framework - LLM Router

This module provides intelligent routing for LLM model selection based on
agent roles, task requirements, and cost optimization strategies.

The router supports:
- Role-based model selection (coder, dba, architect, etc.)
- Task-based model selection (complexity, type)
- Cost-aware routing (balance quality vs. cost)
- Fallback strategies when preferred model is unavailable
- Multi-provider support

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                      LLMRouter                              │
    │  ┌─────────────────────────────────────────────────────┐   │
    │  │                 ModelRegistry                        │   │
    │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │   │
    │  │  │ qwen3.5  │ │ qwen3-   │ │deepseek  │ │ mistral │ │   │
    │  │  │          │ │ coder    │ │  -v3.2   │ │ -large  │ │   │
    │  │  └──────────┘ └──────────┘ └──────────┘ └─────────┘ │   │
    │  └─────────────────────────────────────────────────────┘   │
    │                           │                                 │
    │  ┌─────────────────────────────────────────────────────┐   │
    │  │                 RoleMapper                           │   │
    │  │  orchestrator → qwen3.5                              │   │
    │  │  backend      → qwen3-coder-next                     │   │
    │  │  dba          → deepseek-v3.2                        │   │
    │  │  reviewer     → mistral-large                        │   │
    │  └─────────────────────────────────────────────────────┘   │
    │                           │                                 │
    │  ┌─────────────────────────────────────────────────────┐   │
    │  │                 CostOptimizer                        │   │
    │  │  - Token counting                                    │   │
    │  │  - Cost estimation                                   │   │
    │  │  - Budget tracking                                   │   │
    │  └─────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────┘

Usage:
    from palace.llm import LLMRouter, LLMClient

    # Create router
    router = LLMRouter(settings=settings)

    # Route by role
    model = router.route_by_role("backend")

    # Route by task
    model = router.route_by_task(task_description="Create a REST API endpoint")

    # Get model for specific provider
    model_config = router.get_model("qwen3-coder-next")
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

import structlog

from palace.core.exceptions import ConfigurationError, ModelNotAvailableError

if TYPE_CHECKING:
    from palace.core.config import Settings
    from palace.llm.base import LLMModel, LLMProvider
    from palace.llm.costs import CostTracker

logger = structlog.get_logger()


# =============================================================================
# Enums and Types
# =============================================================================


class AgentRole(str, Enum):
    """
    Agent roles in the Palace framework.

    Each role has an associated optimal model for its tasks.
    """

    ORCHESTRATOR = "orchestrator"
    BACKEND = "backend"
    FRONTEND = "frontend"
    DEVOPS = "devops"
    INFRA = "infra"
    DBA = "dba"
    QA = "qa"
    DESIGNER = "designer"
    REVIEWER = "reviewer"


class TaskComplexity(str, Enum):
    """Task complexity levels for model selection."""

    LOW = "low"
    """Simple tasks: quick responses, simple queries."""

    MEDIUM = "medium"
    """Standard tasks: code generation, analysis."""

    HIGH = "high"
    """Complex tasks: architecture decisions, multi-step reasoning."""

    CRITICAL = "critical"
    """Critical tasks: security reviews, production deployments."""


class TaskType(str, Enum):
    """Types of tasks for model selection."""

    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    ARCHITECTURE = "architecture"
    DATABASE = "database"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DEPLOYMENT = "deployment"
    PLANNING = "planning"
    ANALYSIS = "analysis"


class RoutingStrategy(str, Enum):
    """Strategies for model routing."""

    ROLE_BASED = "role_based"
    """Route based on agent role."""

    TASK_BASED = "task_based"
    """Route based on task type and complexity."""

    COST_OPTIMIZED = "cost_optimized"
    """Route to minimize cost while meeting quality thresholds."""

    QUALITY_FIRST = "quality_first"
    """Always use the highest quality model available."""

    BALANCED = "balanced"
    """Balance between cost and quality."""

    ROUND_ROBIN = "round_robin"
    """Distribute load across available models."""


# =============================================================================
# Model Configuration
# =============================================================================


@dataclass
class ModelCapabilities:
    """
    Capabilities of an LLM model.

    Describes what tasks a model is good at, enabling
    intelligent routing decisions.
    """

    code_generation: float = 0.0
    """Code generation quality score (0-1)."""

    code_review: float = 0.0
    """Code review and analysis quality score (0-1)."""

    reasoning: float = 0.0
    """Logical reasoning capability score (0-1)."""

    creativity: float = 0.0
    """Creative output quality score (0-1)."""

    speed: float = 0.0
    """Response speed score (0-1)."""

    context_window: int = 4096
    """Maximum context window size."""

    supports_streaming: bool = False
    """Whether the model supports streaming responses."""

    supports_tools: bool = False
    """Whether the model supports function/tool calling."""

    supports_vision: bool = False
    """Whether the model supports image inputs."""

    supports_json: bool = False
    """Whether the model supports JSON mode."""

    def get_score(self, task_type: TaskType) -> float:
        """
        Get the capability score for a specific task type.

        Args:
            task_type: The type of task

        Returns:
            Capability score for the task type
        """
        scores = {
            TaskType.CODE_GENERATION: self.code_generation,
            TaskType.CODE_REVIEW: self.code_review,
            TaskType.ARCHITECTURE: self.reasoning,
            TaskType.DATABASE: self.code_generation,
            TaskType.TESTING: self.code_generation,
            TaskType.DOCUMENTATION: self.creativity,
            TaskType.DEPLOYMENT: self.reasoning,
            TaskType.PLANNING: self.reasoning,
            TaskType.ANALYSIS: self.reasoning,
        }
        return scores.get(task_type, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert capabilities to dictionary."""
        return {
            "code_generation": self.code_generation,
            "code_review": self.code_review,
            "reasoning": self.reasoning,
            "creativity": self.creativity,
            "speed": self.speed,
            "context_window": self.context_window,
            "supports_streaming": self.supports_streaming,
            "supports_tools": self.supports_tools,
            "supports_vision": self.supports_vision,
            "supports_json": self.supports_json,
        }


@dataclass
class ModelCost:
    """
    Cost configuration for an LLM model.

    Tracks input and output token costs for budget management.
    """

    input_cost_per_1k: float = 0.0
    """Cost per 1K input tokens in USD."""

    output_cost_per_1k: float = 0.0
    """Cost per 1K output tokens in USD."""

    currency: str = "USD"
    """Currency for cost calculation."""

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate total cost for a request.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Total cost in the specified currency
        """
        input_cost = (input_tokens / 1000) * self.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.output_cost_per_1k
        return input_cost + output_cost

    def to_dict(self) -> Dict[str, Any]:
        """Convert cost to dictionary."""
        return {
            "input_cost_per_1k": self.input_cost_per_1k,
            "output_cost_per_1k": self.output_cost_per_1k,
            "currency": self.currency,
        }


@dataclass
class ModelConfig:
    """
    Configuration for a single LLM model.

    Contains all information needed to use and route to a model.
    """

    name: str
    """Unique model identifier (e.g., 'qwen3-coder-next')."""

    provider: str
    """Provider name (e.g., 'ollama', 'openai')."""

    display_name: str
    """Human-readable model name."""

    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    """Model capabilities for routing."""

    cost: ModelCost = field(default_factory=ModelCost)
    """Cost configuration."""

    max_tokens: int = 4096
    """Maximum output tokens."""

    temperature: float = 0.7
    """Default temperature for generation."""

    top_p: float = 0.9
    """Default top-p for generation."""

    context_window: int = 8192
    """Maximum context window."""

    available: bool = True
    """Whether the model is currently available."""

    tags: List[str] = field(default_factory=list)
    """Tags for categorization (e.g., 'coding', 'fast')."""

    fallback_model: Optional[str] = None
    """Fallback model if this one is unavailable."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional model metadata."""

    def is_available(self) -> bool:
        """Check if model is available for use."""
        return self.available

    def get_effective_context_window(self) -> int:
        """Get the effective context window (max_tokens subtracted)."""
        return self.context_window - self.max_tokens

    def to_dict(self) -> Dict[str, Any]:
        """Convert model config to dictionary."""
        return {
            "name": self.name,
            "provider": self.provider,
            "display_name": self.display_name,
            "capabilities": self.capabilities.to_dict(),
            "cost": self.cost.to_dict(),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "context_window": self.context_window,
            "available": self.available,
            "tags": self.tags,
            "fallback_model": self.fallback_model,
            "metadata": self.metadata,
        }


# =============================================================================
# Role Mapping
# =============================================================================


class RoleMapper:
    """
    Maps agent roles to optimal models.

    This class provides the default mapping between agent roles
    and their preferred models, with support for custom configurations
    and fallback strategies.
    """

    # Default role to model mapping
    DEFAULT_ROLE_MAPPING: Dict[AgentRole, str] = {
        AgentRole.ORCHESTRATOR: "qwen3.5",
        AgentRole.BACKEND: "qwen3-coder-next",
        AgentRole.FRONTEND: "qwen3-coder-next",
        AgentRole.DEVOPS: "qwen3.5",
        AgentRole.INFRA: "qwen3-coder-next",
        AgentRole.DBA: "deepseek-v3.2",
        AgentRole.QA: "gemma4:31b",
        AgentRole.DESIGNER: "mistral-large",
        AgentRole.REVIEWER: "mistral-large",
    }

    # Alternative models for each role (fallback)
    FALLBACK_ROLE_MAPPING: Dict[AgentRole, List[str]] = {
        AgentRole.ORCHESTRATOR: ["qwen3-coder-next", "mistral-large"],
        AgentRole.BACKEND: ["qwen3.5", "deepseek-v3.2"],
        AgentRole.FRONTEND: ["qwen3.5", "deepseek-v3.2"],
        AgentRole.DEVOPS: ["qwen3-coder-next", "mistral-large"],
        AgentRole.INFRA: ["qwen3.5", "deepseek-v3.2"],
        AgentRole.DBA: ["qwen3-coder-next", "mistral-large"],
        AgentRole.QA: ["qwen3-coder-next", "mistral-large"],
        AgentRole.DESIGNER: ["qwen3.5", "qwen3-coder-next"],
        AgentRole.REVIEWER: ["qwen3.5", "deepseek-v3.2"],
    }

    def __init__(self, custom_mapping: Optional[Dict[AgentRole, str]] = None):
        """
        Initialize the role mapper.

        Args:
            custom_mapping: Optional custom role to model mapping
        """
        self._mapping = {**self.DEFAULT_ROLE_MAPPING}
        if custom_mapping:
            self._mapping.update(custom_mapping)

    def get_model(self, role: AgentRole) -> str:
        """
        Get the primary model for a role.

        Args:
            role: The agent role

        Returns:
            Model name for the role
        """
        return self._mapping.get(role, self._mapping[AgentRole.ORCHESTRATOR])

    def get_fallback_models(self, role: AgentRole) -> List[str]:
        """
        Get fallback models for a role.

        Args:
            role: The agent role

        Returns:
            List of fallback model names
        """
        return self.FALLBACK_ROLE_MAPPING.get(role, [])

    def set_model(self, role: AgentRole, model: str) -> None:
        """
        Set the model for a role.

        Args:
            role: The agent role
            model: The model name to use
        """
        self._mapping[role] = model
        logger.info("role_model_updated", role=role.value, model=model)

    def get_all_mappings(self) -> Dict[AgentRole, str]:
        """
        Get all role to model mappings.

        Returns:
            Dictionary of all mappings
        """
        return dict(self._mapping)


# =============================================================================
# Model Registry
# =============================================================================


class ModelRegistry:
    """
    Registry for available LLM models.

    Maintains a catalog of all available models, their configurations,
    capabilities, and availability status.
    """

    def __init__(self):
        """Initialize the model registry."""
        self._models: Dict[str, ModelConfig] = {}
        self._providers: Dict[str, str] = {}  # model -> provider
        self._availability_cache: Dict[str, bool] = {}

    def register(self, model: ModelConfig) -> None:
        """
        Register a model configuration.

        Args:
            model: Model configuration to register
        """
        self._models[model.name] = model
        self._providers[model.name] = model.provider
        self._availability_cache[model.name] = model.available

        logger.info(
            "model_registered",
            model=model.name,
            provider=model.provider,
            capabilities=model.capabilities.to_dict(),
        )

    def unregister(self, model_name: str) -> bool:
        """
        Unregister a model.

        Args:
            model_name: Name of the model to unregister

        Returns:
            True if model was unregistered, False if not found
        """
        if model_name in self._models:
            del self._models[model_name]
            del self._providers[model_name]
            del self._availability_cache[model_name]
            logger.info("model_unregistered", model=model_name)
            return True
        return False

    def get(self, model_name: str) -> Optional[ModelConfig]:
        """
        Get a model configuration by name.

        Args:
            model_name: Name of the model

        Returns:
            Model configuration or None if not found
        """
        return self._models.get(model_name)

    def get_by_provider(self, provider: str) -> List[ModelConfig]:
        """
        Get all models for a provider.

        Args:
            provider: Provider name

        Returns:
            List of model configurations
        """
        return [m for m in self._models.values() if m.provider == provider]

    def get_available_models(self) -> List[ModelConfig]:
        """
        Get all available models.

        Returns:
            List of available model configurations
        """
        return [m for m in self._models.values() if m.is_available()]

    def get_models_by_capability(
        self,
        task_type: TaskType,
        min_score: float = 0.5,
    ) -> List[ModelConfig]:
        """
        Get models capable of handling a task type.

        Args:
            task_type: The type of task
            min_score: Minimum capability score (0-1)

        Returns:
            List of capable model configurations
        """
        capable = []
        for model in self._models.values():
            if model.is_available() and model.capabilities.get_score(task_type) >= min_score:
                capable.append(model)
        return capable

    def update_availability(self, model_name: str, available: bool) -> None:
        """
        Update model availability status.

        Args:
            model_name: Name of the model
            available: Whether the model is available
        """
        if model_name in self._models:
            self._models[model_name].available = available
            self._availability_cache[model_name] = available
            logger.info("model_availability_updated", model=model_name, available=available)

    def get_all_models(self) -> Dict[str, ModelConfig]:
        """
        Get all registered models.

        Returns:
            Dictionary of all model configurations
        """
        return dict(self._models)

    def list_models(self) -> List[str]:
        """
        List all registered model names.

        Returns:
            List of model names
        """
        return list(self._models.keys())

    def clear(self) -> None:
        """Clear all registered models."""
        self._models.clear()
        self._providers.clear()
        self._availability_cache.clear()
        logger.info("model_registry_cleared")


# =============================================================================
# LLM Router
# =============================================================================


class LLMRouter:
    """
    Intelligent router for LLM model selection.

    This class provides sophisticated routing capabilities for selecting
    the optimal LLM model based on various strategies:

    1. Role-based routing: Select model based on agent role
    2. Task-based routing: Select model based on task type and complexity
    3. Cost-optimized routing: Balance quality vs. cost
    4. Custom routing: Use custom routing functions

    The router maintains a registry of available models and their
    capabilities, enabling intelligent decision-making.

    Features:
        - Multiple routing strategies
        - Fallback model support
        - Cost tracking integration
        - Availability checking
        - Custom routing rules

    Example:
        >>> from palace.llm import LLMRouter
        >>> from palace.core.config import get_settings
        >>>
        >>> # Create router
        >>> settings = get_settings()
        >>> router = LLMRouter(settings)
        >>>
        >>> # Route by role
        >>> model = router.route_by_role("backend")
        >>> print(model.name)  # 'qwen3-coder-next'
        >>>
        >>> # Route by task
        >>> model = router.route_by_task(
        ...     task_type="code_generation",
        ...     complexity="high"
        ... )
        >>>
        >>> # Get model configuration
        >>> config = router.get_model("qwen3-coder-next")
    """

    def __init__(
        self,
        settings: "Settings",
        cost_tracker: Optional["CostTracker"] = None,
        strategy: RoutingStrategy = RoutingStrategy.ROLE_BASED,
    ):
        """
        Initialize the LLM router.

        Args:
            settings: Framework settings containing model configurations
            cost_tracker: Optional cost tracker for budget management
            strategy: Default routing strategy
        """
        self._settings = settings
        self._cost_tracker = cost_tracker
        self._strategy = strategy

        # Initialize components
        self._registry = ModelRegistry()
        self._role_mapper = RoleMapper()

        # Custom routing rules
        self._custom_rules: Dict[str, Callable] = {}

        # Initialize models from settings
        self._initialize_models()

        logger.info(
            "llm_router_initialized",
            strategy=strategy.value,
            models_count=len(self._registry.list_models()),
        )

    def _initialize_models(self) -> None:
        """Initialize models from settings."""
        # Define available models with their configurations
        models = [
            # Qwen models
            ModelConfig(
                name="qwen3.5",
                provider="ollama",
                display_name="Qwen 3.5",
                capabilities=ModelCapabilities(
                    code_generation=0.85,
                    code_review=0.80,
                    reasoning=0.90,
                    creativity=0.75,
                    speed=0.85,
                    context_window=32768,
                    supports_streaming=True,
                    supports_tools=True,
                    supports_json=True,
                ),
                cost=ModelCost(
                    input_cost_per_1k=0.0001,
                    output_cost_per_1k=0.0002,
                ),
                max_tokens=8192,
                temperature=0.7,
                context_window=32768,
                tags=["orchestration", "planning", "general"],
                fallback_model="qwen3-coder-next",
            ),
            ModelConfig(
                name="qwen3-coder-next",
                provider="ollama",
                display_name="Qwen 3 Coder Next",
                capabilities=ModelCapabilities(
                    code_generation=0.95,
                    code_review=0.90,
                    reasoning=0.85,
                    creativity=0.70,
                    speed=0.80,
                    context_window=32768,
                    supports_streaming=True,
                    supports_tools=True,
                    supports_json=True,
                ),
                cost=ModelCost(
                    input_cost_per_1k=0.00015,
                    output_cost_per_1k=0.0003,
                ),
                max_tokens=8192,
                temperature=0.7,
                context_window=32768,
                tags=["coding", "backend", "frontend"],
                fallback_model="qwen3.5",
            ),
            ModelConfig(
                name="deepseek-v3.2",
                provider="ollama",
                display_name="DeepSeek V3.2",
                capabilities=ModelCapabilities(
                    code_generation=0.90,
                    code_review=0.85,
                    reasoning=0.92,
                    creativity=0.65,
                    speed=0.75,
                    context_window=65536,
                    supports_streaming=True,
                    supports_tools=True,
                    supports_json=True,
                ),
                cost=ModelCost(
                    input_cost_per_1k=0.0002,
                    output_cost_per_1k=0.0004,
                ),
                max_tokens=16384,
                temperature=0.7,
                context_window=65536,
                tags=["database", "sql", "reasoning"],
                fallback_model="qwen3-coder-next",
            ),
            ModelConfig(
                name="gemma4:31b",
                provider="ollama",
                display_name="Gemma 4 31B",
                capabilities=ModelCapabilities(
                    code_generation=0.80,
                    code_review=0.88,
                    reasoning=0.82,
                    creativity=0.70,
                    speed=0.85,
                    context_window=32768,
                    supports_streaming=True,
                    supports_tools=True,
                    supports_json=True,
                ),
                cost=ModelCost(
                    input_cost_per_1k=0.0001,
                    output_cost_per_1k=0.0002,
                ),
                max_tokens=8192,
                temperature=0.7,
                context_window=32768,
                tags=["qa", "testing", "review"],
                fallback_model="qwen3-coder-next",
            ),
            ModelConfig(
                name="mistral-large",
                provider="ollama",
                display_name="Mistral Large",
                capabilities=ModelCapabilities(
                    code_generation=0.82,
                    code_review=0.92,
                    reasoning=0.95,
                    creativity=0.88,
                    speed=0.70,
                    context_window=32768,
                    supports_streaming=True,
                    supports_tools=True,
                    supports_json=True,
                ),
                cost=ModelCost(
                    input_cost_per_1k=0.00025,
                    output_cost_per_1k=0.0005,
                ),
                max_tokens=8192,
                temperature=0.7,
                context_window=32768,
                tags=["architecture", "review", "design"],
                fallback_model="qwen3.5",
            ),
        ]

        # Register all models
        for model in models:
            self._registry.register(model)

        logger.info("models_initialized", count=len(models))

    # -------------------------------------------------------------------------
    # Routing Methods
    # -------------------------------------------------------------------------

    def route_by_role(
        self,
        role: Union[AgentRole, str],
        fallback: bool = True,
    ) -> ModelConfig:
        """
        Route to the optimal model for an agent role.

        Args:
            role: The agent role (e.g., 'backend', 'dba')
            fallback: Whether to use fallback if primary unavailable

        Returns:
            Model configuration for the role

        Raises:
            ModelNotAvailableError: If no model is available for the role
        """
        # Normalize role
        if isinstance(role, str):
            try:
                role = AgentRole(role.lower())
            except ValueError:
                raise ConfigurationError(
                    f"Invalid role: {role}. Valid roles: {[r.value for r in AgentRole]}"
                )

        # Get primary model
        model_name = self._role_mapper.get_model(role)
        model = self._registry.get(model_name)

        # Check availability
        if model and model.is_available():
            logger.debug(
                "routed_by_role",
                role=role.value,
                model=model.name,
                strategy="primary",
            )
            return model

        # Try fallback models
        if fallback:
            for fallback_name in self._role_mapper.get_fallback_models(role):
                fallback_model = self._registry.get(fallback_name)
                if fallback_model and fallback_model.is_available():
                    logger.warning(
                        "using_fallback_model",
                        role=role.value,
                        primary=model_name,
                        fallback=fallback_name,
                    )
                    return fallback_model

        # No model available
        raise ModelNotAvailableError(
            model=model_name,
            available_models=[m.name for m in self._registry.get_available_models()],
        )

    def route_by_task(
        self,
        task_type: Union[TaskType, str],
        complexity: TaskComplexity = TaskComplexity.MEDIUM,
        min_capability: float = 0.7,
    ) -> ModelConfig:
        """
        Route to the optimal model for a task type.

        Selects the best model based on task requirements and
        model capabilities.

        Args:
            task_type: Type of task
            complexity: Task complexity level
            min_capability: Minimum capability score required

        Returns:
            Model configuration for the task

        Raises:
            ModelNotAvailableError: If no suitable model is found
        """
        # Normalize task type
        if isinstance(task_type, str):
            try:
                task_type = TaskType(task_type.lower())
            except ValueError:
                # Default to code_generation for unknown types
                task_type = TaskType.CODE_GENERATION

        # Get capable models
        capable_models = self._registry.get_models_by_capability(
            task_type=task_type,
            min_score=min_capability,
        )

        if not capable_models:
            raise ModelNotAvailableError(
                model=f"any_capable_for_{task_type.value}",
                available_models=self._registry.list_models(),
            )

        # Sort by capability score
        def score_model(model: ModelConfig) -> float:
            """Calculate model score based on task and complexity."""
            capability_score = model.capabilities.get_score(task_type)

            # Adjust for complexity
            if complexity == TaskComplexity.CRITICAL:
                # For critical tasks, prioritize reasoning and code_review
                capability_score = (
                    0.4 * capability_score
                    + 0.3 * model.capabilities.reasoning
                    + 0.3 * model.capabilities.code_review
                )
            elif complexity == TaskComplexity.HIGH:
                capability_score = 0.6 * capability_score + 0.4 * model.capabilities.reasoning

            # Consider speed for low complexity
            if complexity == TaskComplexity.LOW:
                capability_score = 0.6 * capability_score + 0.4 * model.capabilities.speed

            return capability_score

        # Sort and get best model
        capable_models.sort(key=score_model, reverse=True)
        best_model = capable_models[0]

        logger.debug(
            "routed_by_task",
            task_type=task_type.value,
            complexity=complexity.value,
            model=best_model.name,
            score=score_model(best_model),
        )

        return best_model

    def route_by_cost(
        self,
        task_type: Union[TaskType, str],
        max_cost_per_1k: float,
        min_capability: float = 0.5,
    ) -> ModelConfig:
        """
        Route to a model within cost constraints.

        Selects the best model that meets both capability and cost requirements.

        Args:
            task_type: Type of task
            max_cost_per_1k: Maximum acceptable cost per 1K tokens
            min_capability: Minimum capability score required

        Returns:
            Model configuration within budget

        Raises:
            ModelNotAvailableError: If no model meets constraints
        """
        # Normalize task type
        if isinstance(task_type, str):
            try:
                task_type = TaskType(task_type.lower())
            except ValueError:
                task_type = TaskType.CODE_GENERATION

        # Get capable models within budget
        candidate_models = []

        for model in self._registry.get_models_by_capability(
            task_type=task_type,
            min_score=min_capability,
        ):
            # Calculate average cost (input + output)
            avg_cost = (model.cost.input_cost_per_1k + model.cost.output_cost_per_1k) / 2

            if avg_cost <= max_cost_per_1k:
                candidate_models.append((model, avg_cost))

        if not candidate_models:
            raise ModelNotAvailableError(
                model=f"any_within_budget_{max_cost_per_1k}",
                available_models=self._registry.list_models(),
            )

        # Sort by capability score, then by cost
        candidate_models.sort(
            key=lambda x: (
                -x[0].capabilities.get_score(task_type),
                x[1],
            )
        )

        best_model = candidate_models[0][0]

        logger.debug(
            "routed_by_cost",
            task_type=task_type.value,
            model=best_model.name,
            max_cost=max_cost_per_1k,
            actual_cost=candidate_models[0][1],
        )

        return best_model

    def route(
        self,
        role: Optional[Union[AgentRole, str]] = None,
        task_type: Optional[Union[TaskType, str]] = None,
        complexity: Optional[TaskComplexity] = None,
        max_cost: Optional[float] = None,
        strategy: Optional[RoutingStrategy] = None,
    ) -> ModelConfig:
        """
        Route to optimal model using the specified strategy.

        This is the main routing method that delegates to specific
        routing methods based on the strategy.

        Args:
            role: Agent role for role-based routing
            task_type: Task type for task-based routing
            complexity: Task complexity
            max_cost: Maximum cost per 1K tokens for cost-based routing
            strategy: Override routing strategy

        Returns:
            Model configuration

        Raises:
            ModelNotAvailableError: If no suitable model is found
            ConfigurationError: If routing parameters are invalid
        """
        # Use provided strategy or default
        routing_strategy = strategy or self._strategy

        # Route based on strategy
        if routing_strategy == RoutingStrategy.ROLE_BASED:
            if role is None:
                raise ConfigurationError("Role is required for role-based routing")
            return self.route_by_role(role)

        elif routing_strategy == RoutingStrategy.TASK_BASED:
            if task_type is None:
                raise ConfigurationError("Task type is required for task-based routing")
            return self.route_by_task(
                task_type=task_type,
                complexity=complexity or TaskComplexity.MEDIUM,
            )

        elif routing_strategy == RoutingStrategy.COST_OPTIMIZED:
            if task_type is None or max_cost is None:
                raise ConfigurationError(
                    "Task type and max_cost are required for cost-optimized routing"
                )
            return self.route_by_cost(
                task_type=task_type,
                max_cost_per_1k=max_cost,
            )

        elif routing_strategy == RoutingStrategy.QUALITY_FIRST:
            # Always use the highest quality model
            models = self._registry.get_available_models()
            if not models:
                raise ModelNotAvailableError(
                    model="any",
                    available_models=[],
                )

            # Sort by overall capability
            def quality_score(m: ModelConfig) -> float:
                return (
                    m.capabilities.code_generation
                    + m.capabilities.code_review
                    + m.capabilities.reasoning
                ) / 3

            models.sort(key=quality_score, reverse=True)
            return models[0]

        elif routing_strategy == RoutingStrategy.BALANCED:
            # Balance between quality and cost
            if task_type is None:
                task_type = TaskType.CODE_GENERATION
            models = self._registry.get_models_by_capability(task_type)
            if not models:
                raise ModelNotAvailableError(
                    model="any",
                    available_models=self._registry.list_models(),
                )

            # Score models by quality / cost ratio
            def balanced_score(m: ModelConfig) -> float:
                quality = m.capabilities.get_score(task_type)
                cost = (m.cost.input_cost_per_1k + m.cost.output_cost_per_1k) / 2
                # Avoid division by zero
                if cost == 0:
                    return quality * 100
                return quality / cost

            models.sort(key=balanced_score, reverse=True)
            return models[0]

        else:
            # Default to role-based routing
            if role is None:
                role = AgentRole.ORCHESTRATOR
            return self.route_by_role(role)

    # -------------------------------------------------------------------------
    # Model Management
    # -------------------------------------------------------------------------

    def get_model(self, model_name: str) -> ModelConfig:
        """
        Get a model configuration by name.

        Args:
            model_name: Name of the model

        Returns:
            Model configuration

        Raises:
            ModelNotAvailableError: If model is not found
        """
        model = self._registry.get(model_name)
        if model is None:
            raise ModelNotAvailableError(
                model=model_name,
                available_models=self._registry.list_models(),
            )
        return model

    def get_all_models(self) -> Dict[str, ModelConfig]:
        """
        Get all registered models.

        Returns:
            Dictionary of all model configurations
        """
        return self._registry.get_all_models()

    def get_available_models(self) -> List[ModelConfig]:
        """
        Get all available models.

        Returns:
            List of available model configurations
        """
        return self._registry.get_available_models()

    def update_model_availability(
        self,
        model_name: str,
        available: bool,
    ) -> None:
        """
        Update model availability status.

        Args:
            model_name: Name of the model
            available: Whether the model is available
        """
        self._registry.update_availability(model_name, available)

    def set_role_model(
        self,
        role: Union[AgentRole, str],
        model_name: str,
    ) -> None:
        """
        Set the model for a specific role.

        Args:
            role: The agent role
            model_name: The model name to use
        """
        if isinstance(role, str):
            role = AgentRole(role.lower())

        # Verify model exists
        if not self._registry.get(model_name):
            raise ModelNotAvailableError(
                model=model_name,
                available_models=self._registry.list_models(),
            )

        self._role_mapper.set_model(role, model_name)

    # -------------------------------------------------------------------------
    # Custom Routing
    # -------------------------------------------------------------------------

    def register_custom_rule(
        self,
        name: str,
        rule: Callable[["LLMRouter", Dict[str, Any]], ModelConfig],
    ) -> None:
        """
        Register a custom routing rule.

        Custom rules allow for specialized routing logic beyond
        the built-in strategies.

        Args:
            name: Rule name
            rule: Callable that takes router and context, returns ModelConfig
        """
        self._custom_rules[name] = rule
        logger.info("custom_routing_rule_registered", name=name)

    def route_custom(
        self,
        rule_name: str,
        context: Dict[str, Any],
    ) -> ModelConfig:
        """
        Route using a custom rule.

        Args:
            rule_name: Name of the custom rule
            context: Routing context

        Returns:
            Model configuration

        Raises:
            ConfigurationError: If rule is not found
        """
        if rule_name not in self._custom_rules:
            raise ConfigurationError(f"Custom rule '{rule_name}' not found")

        return self._custom_rules[rule_name](self, context)

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get routing statistics.

        Returns:
            Dictionary with routing statistics
        """
        models = self._registry.get_all_models()
        available = [m for m in models.values() if m.is_available()]

        return {
            "total_models": len(models),
            "available_models": len(available),
            "role_mappings": self._role_mapper.get_all_mappings(),
            "models_by_provider": {
                provider: len([m for m in models.values() if m.provider == provider])
                for provider in set(m.provider for m in models.values())
            },
            "custom_rules": list(self._custom_rules.keys()),
            "default_strategy": self._strategy.value,
        }

    def estimate_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Estimate cost for a request.

        Args:
            model_name: Name of the model
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        model = self.get_model(model_name)
        return model.cost.calculate_cost(input_tokens, output_tokens)

    def get_model_for_task(
        self,
        task_description: str,
        role: Optional[AgentRole] = None,
    ) -> ModelConfig:
        """
        Get the best model for a task description.

        Analyzes the task description to determine the optimal model.

        Args:
            task_description: Description of the task
            role: Optional agent role hint

        Returns:
            Model configuration
        """
        # Keywords for task type detection
        task_keywords = {
            TaskType.CODE_GENERATION: [
                "create",
                "implement",
                "write",
                "build",
                "develop",
                "code",
                "function",
                "class",
                "api",
                "endpoint",
            ],
            TaskType.CODE_REVIEW: [
                "review",
                "analyze",
                "check",
                "audit",
                "refactor",
                "improve",
                "optimize",
                "debug",
            ],
            TaskType.ARCHITECTURE: [
                "design",
                "architecture",
                "structure",
                "pattern",
                "system",
                "component",
                "module",
            ],
            TaskType.DATABASE: [
                "database",
                "sql",
                "query",
                "migration",
                "schema",
                "table",
                "index",
                "optimize",
            ],
            TaskType.TESTING: [
                "test",
                "testing",
                "unit test",
                "integration",
                "coverage",
                "mock",
                "fixture",
            ],
            TaskType.DOCUMENTATION: [
                "document",
                "documentation",
                "readme",
                "comment",
                "explain",
                "describe",
            ],
            TaskType.DEPLOYMENT: [
                "deploy",
                "deployment",
                "ci/cd",
                "pipeline",
                "docker",
                "kubernetes",
                "release",
            ],
            TaskType.PLANNING: [
                "plan",
                "planning",
                "strategy",
                "roadmap",
                "schedule",
                "timeline",
            ],
        }

        # Detect task type from description
        description_lower = task_description.lower()
        detected_type = TaskType.CODE_GENERATION  # Default

        for task_type, keywords in task_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                detected_type = task_type
                break

        # Detect complexity
        complexity = TaskComplexity.MEDIUM
        if any(
            word in description_lower
            for word in ["critical", "security", "production", "important"]
        ):
            complexity = TaskComplexity.CRITICAL
        elif any(
            word in description_lower for word in ["complex", "advanced", "scalable", "enterprise"]
        ):
            complexity = TaskComplexity.HIGH
        elif any(word in description_lower for word in ["simple", "quick", "basic", "small"]):
            complexity = TaskComplexity.LOW

        # Route based on detected type or role
        if role:
            return self.route_by_role(role)
        return self.route_by_task(detected_type, complexity)
