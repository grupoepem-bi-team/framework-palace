"""
Tests for palace.llm.router — LLMRouter, RoleMapper, ModelRegistry, and related types.

Covers:
- RoutingStrategy enum
- ModelCapabilities dataclass
- ModelCost dataclass
- ModelConfig dataclass
- RoleMapper class
- ModelRegistry class
- LLMRouter class
"""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: register stub package modules so that broken __init__.py files
# do not cascade import errors.
# ---------------------------------------------------------------------------
_SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
_PALACE_PKG = _SRC_ROOT / "palace"
_PALACE_CORE_PKG = _PALACE_PKG / "core"
_PALACE_LLM_PKG = _PALACE_PKG / "llm"


def _ensure_package(module_name: str, paths: list) -> types.ModuleType:
    if module_name in sys.modules:
        return sys.modules[module_name]
    mod = types.ModuleType(module_name)
    mod.__path__ = paths
    mod.__package__ = module_name
    sys.modules[module_name] = mod
    return mod


_ensure_package("palace", [str(_PALACE_PKG)])
_ensure_package("palace.core", [str(_PALACE_CORE_PKG)])

# Stub palace.llm to prevent the broken __init__.py (which imports
# the non-existent LLMMessage from palace.llm.base) from cascading
# import errors.  We still want direct submodule imports like
# palace.llm.router to work, so we register the stub *before* any
# import that touches palace.llm.
_ensure_package("palace.llm", [str(_PALACE_LLM_PKG)])

# Ensure the exceptions module has the classes the router needs.
# If the real module is importable, this is a no-op; otherwise inject stubs.
try:
    from palace.core.exceptions import ConfigurationError, ModelNotAvailableError
except ImportError:

    class ConfigurationError(Exception):
        """Stub for testing."""

    class ModelNotAvailableError(Exception):
        """Stub for testing."""

        def __init__(self, model=None, available_models=None, message=None):
            self.model = model
            self.available_models = available_models or []
            msg = message or f"Model '{model}' is not available"
            super().__init__(msg)

    # Inject into the core package namespace so the router can find them
    _core = sys.modules.get("palace.core")
    if _core is not None:
        _core.ConfigurationError = ConfigurationError
        _core.ModelNotAvailableError = ModelNotAvailableError

# Now safe to import the module under test
from palace.llm.router import (
    AgentRole,
    LLMRouter,
    ModelCapabilities,
    ModelConfig,
    ModelCost,
    ModelRegistry,
    RoleMapper,
    RoutingStrategy,
    TaskComplexity,
    TaskType,
)

# =====================================================================
# RoutingStrategy tests
# =====================================================================


class TestRoutingStrategy:
    """Tests for the RoutingStrategy enum."""

    def test_all_strategies_exist(self):
        expected = {
            "ROLE_BASED",
            "TASK_BASED",
            "COST_OPTIMIZED",
            "QUALITY_FIRST",
            "BALANCED",
            "ROUND_ROBIN",
        }
        actual = {s.name for s in RoutingStrategy}
        assert actual == expected

    def test_strategy_values(self):
        assert RoutingStrategy.ROLE_BASED.value == "role_based"
        assert RoutingStrategy.TASK_BASED.value == "task_based"
        assert RoutingStrategy.COST_OPTIMIZED.value == "cost_optimized"
        assert RoutingStrategy.QUALITY_FIRST.value == "quality_first"
        assert RoutingStrategy.BALANCED.value == "balanced"
        assert RoutingStrategy.ROUND_ROBIN.value == "round_robin"

    def test_is_string_enum(self):
        assert isinstance(RoutingStrategy.ROLE_BASED, str)

    def test_strategy_from_value(self):
        assert RoutingStrategy("role_based") == RoutingStrategy.ROLE_BASED
        assert RoutingStrategy("balanced") == RoutingStrategy.BALANCED


# =====================================================================
# AgentRole (router) tests
# =====================================================================


class TestRouterAgentRole:
    """Tests for the AgentRole enum defined in the router module."""

    def test_all_nine_roles_exist(self):
        expected = {
            "ORCHESTRATOR",
            "BACKEND",
            "FRONTEND",
            "DEVOPS",
            "INFRA",
            "DBA",
            "QA",
            "DESIGNER",
            "REVIEWER",
        }
        actual = {r.name for r in AgentRole}
        assert actual == expected

    def test_role_values(self):
        assert AgentRole.ORCHESTRATOR.value == "orchestrator"
        assert AgentRole.BACKEND.value == "backend"
        assert AgentRole.FRONTEND.value == "frontend"
        assert AgentRole.DEVOPS.value == "devops"
        assert AgentRole.INFRA.value == "infra"
        assert AgentRole.DBA.value == "dba"
        assert AgentRole.QA.value == "qa"
        assert AgentRole.DESIGNER.value == "designer"
        assert AgentRole.REVIEWER.value == "reviewer"


# =====================================================================
# TaskType (router) tests
# =====================================================================


class TestRouterTaskType:
    """Tests for the TaskType enum defined in the router module."""

    def test_all_task_types_exist(self):
        expected = {
            "CODE_GENERATION",
            "CODE_REVIEW",
            "ARCHITECTURE",
            "DATABASE",
            "TESTING",
            "DOCUMENTATION",
            "DEPLOYMENT",
            "PLANNING",
            "ANALYSIS",
        }
        actual = {t.name for t in TaskType}
        assert actual == expected

    def test_task_type_values(self):
        assert TaskType.CODE_GENERATION.value == "code_generation"
        assert TaskType.CODE_REVIEW.value == "code_review"
        assert TaskType.ARCHITECTURE.value == "architecture"
        assert TaskType.DATABASE.value == "database"
        assert TaskType.TESTING.value == "testing"
        assert TaskType.DOCUMENTATION.value == "documentation"
        assert TaskType.DEPLOYMENT.value == "deployment"
        assert TaskType.PLANNING.value == "planning"
        assert TaskType.ANALYSIS.value == "analysis"


# =====================================================================
# TaskComplexity (router) tests
# =====================================================================


class TestRouterTaskComplexity:
    """Tests for the TaskComplexity enum defined in the router module."""

    def test_all_complexity_levels_exist(self):
        expected = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        actual = {c.name for c in TaskComplexity}
        assert actual == expected

    def test_complexity_values(self):
        assert TaskComplexity.LOW.value == "low"
        assert TaskComplexity.MEDIUM.value == "medium"
        assert TaskComplexity.HIGH.value == "high"
        assert TaskComplexity.CRITICAL.value == "critical"


# =====================================================================
# ModelCapabilities tests
# =====================================================================


class TestModelCapabilities:
    """Tests for the ModelCapabilities dataclass."""

    def test_default_capabilities(self):
        caps = ModelCapabilities()
        assert caps.code_generation == 0.0
        assert caps.code_review == 0.0
        assert caps.reasoning == 0.0
        assert caps.creativity == 0.0
        assert caps.speed == 0.0
        assert caps.context_window == 4096
        assert caps.supports_streaming is False
        assert caps.supports_tools is False
        assert caps.supports_vision is False
        assert caps.supports_json is False

    def test_capabilities_with_values(self):
        caps = ModelCapabilities(
            code_generation=0.95,
            code_review=0.90,
            reasoning=0.85,
            creativity=0.70,
            speed=0.80,
            context_window=32768,
            supports_streaming=True,
            supports_tools=True,
            supports_json=True,
        )
        assert caps.code_generation == 0.95
        assert caps.code_review == 0.90
        assert caps.reasoning == 0.85
        assert caps.creativity == 0.70
        assert caps.speed == 0.80
        assert caps.context_window == 32768
        assert caps.supports_streaming is True
        assert caps.supports_tools is True
        assert caps.supports_json is True
        assert caps.supports_vision is False  # default

    def test_get_score_code_generation(self):
        caps = ModelCapabilities(code_generation=0.95)
        assert caps.get_score(TaskType.CODE_GENERATION) == 0.95

    def test_get_score_code_review(self):
        caps = ModelCapabilities(code_review=0.88)
        assert caps.get_score(TaskType.CODE_REVIEW) == 0.88

    def test_get_score_architecture_maps_to_reasoning(self):
        caps = ModelCapabilities(reasoning=0.92)
        assert caps.get_score(TaskType.ARCHITECTURE) == 0.92

    def test_get_score_database_maps_to_code_generation(self):
        caps = ModelCapabilities(code_generation=0.85)
        assert caps.get_score(TaskType.DATABASE) == 0.85

    def test_get_score_testing_maps_to_code_generation(self):
        caps = ModelCapabilities(code_generation=0.80)
        assert caps.get_score(TaskType.TESTING) == 0.80

    def test_get_score_documentation_maps_to_creativity(self):
        caps = ModelCapabilities(creativity=0.75)
        assert caps.get_score(TaskType.DOCUMENTATION) == 0.75

    def test_get_score_deployment_maps_to_reasoning(self):
        caps = ModelCapabilities(reasoning=0.70)
        assert caps.get_score(TaskType.DEPLOYMENT) == 0.70

    def test_get_score_planning_maps_to_reasoning(self):
        caps = ModelCapabilities(reasoning=0.90)
        assert caps.get_score(TaskType.PLANNING) == 0.90

    def test_get_score_analysis_maps_to_reasoning(self):
        caps = ModelCapabilities(reasoning=0.88)
        assert caps.get_score(TaskType.ANALYSIS) == 0.88

    def test_get_score_returns_zero_for_zero_capabilities(self):
        caps = ModelCapabilities()
        assert caps.get_score(TaskType.CODE_GENERATION) == 0.0

    def test_to_dict(self):
        caps = ModelCapabilities(
            code_generation=0.95,
            code_review=0.90,
            reasoning=0.85,
            creativity=0.70,
            speed=0.80,
            context_window=32768,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=False,
            supports_json=True,
        )
        d = caps.to_dict()
        assert d["code_generation"] == 0.95
        assert d["code_review"] == 0.90
        assert d["reasoning"] == 0.85
        assert d["creativity"] == 0.70
        assert d["speed"] == 0.80
        assert d["context_window"] == 32768
        assert d["supports_streaming"] is True
        assert d["supports_tools"] is True
        assert d["supports_vision"] is False
        assert d["supports_json"] is True

    def test_to_dict_default_values(self):
        caps = ModelCapabilities()
        d = caps.to_dict()
        assert d["code_generation"] == 0.0
        assert d["context_window"] == 4096
        assert d["supports_streaming"] is False


# =====================================================================
# ModelCost tests
# =====================================================================


class TestModelCost:
    """Tests for the ModelCost dataclass."""

    def test_default_cost(self):
        cost = ModelCost()
        assert cost.input_cost_per_1k == 0.0
        assert cost.output_cost_per_1k == 0.0
        assert cost.currency == "USD"

    def test_cost_with_values(self):
        cost = ModelCost(
            input_cost_per_1k=0.0001,
            output_cost_per_1k=0.0002,
            currency="EUR",
        )
        assert cost.input_cost_per_1k == 0.0001
        assert cost.output_cost_per_1k == 0.0002
        assert cost.currency == "EUR"

    def test_calculate_cost_basic(self):
        cost = ModelCost(input_cost_per_1k=0.1, output_cost_per_1k=0.2)
        # 1000 input tokens * $0.1/1K + 1000 output tokens * $0.2/1K = $0.1 + $0.2 = $0.3
        total = cost.calculate_cost(1000, 1000)
        assert abs(total - 0.3) < 0.001

    def test_calculate_cost_zero_tokens(self):
        cost = ModelCost(input_cost_per_1k=0.1, output_cost_per_1k=0.2)
        total = cost.calculate_cost(0, 0)
        assert total == 0.0

    def test_calculate_cost_asymmetric_tokens(self):
        cost = ModelCost(input_cost_per_1k=0.0001, output_cost_per_1k=0.0003)
        # 5000 input * $0.0001/1K + 2000 output * $0.0003/1K
        total = cost.calculate_cost(5000, 2000)
        expected = (5000 / 1000) * 0.0001 + (2000 / 1000) * 0.0003
        assert abs(total - expected) < 0.0001

    def test_calculate_cost_free_model(self):
        cost = ModelCost()  # default costs are 0.0
        total = cost.calculate_cost(100000, 50000)
        assert total == 0.0

    def test_to_dict(self):
        cost = ModelCost(
            input_cost_per_1k=0.00015,
            output_cost_per_1k=0.0003,
            currency="USD",
        )
        d = cost.to_dict()
        assert d["input_cost_per_1k"] == 0.00015
        assert d["output_cost_per_1k"] == 0.0003
        assert d["currency"] == "USD"


# =====================================================================
# ModelConfig tests
# =====================================================================


class TestModelConfig:
    """Tests for the ModelConfig dataclass."""

    def _make_config(self, **overrides):
        defaults = dict(
            name="test-model",
            provider="ollama",
            display_name="Test Model",
            capabilities=ModelCapabilities(code_generation=0.85),
            cost=ModelCost(input_cost_per_1k=0.0001, output_cost_per_1k=0.0002),
            max_tokens=4096,
            temperature=0.7,
            top_p=0.9,
            context_window=8192,
            available=True,
            tags=["test"],
            fallback_model="fallback-model",
            metadata={"version": "1.0"},
        )
        defaults.update(overrides)
        return ModelConfig(**defaults)

    def test_model_config_creation(self):
        config = self._make_config()
        assert config.name == "test-model"
        assert config.provider == "ollama"
        assert config.display_name == "Test Model"
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.top_p == 0.9
        assert config.context_window == 8192
        assert config.available is True
        assert config.tags == ["test"]
        assert config.fallback_model == "fallback-model"
        assert config.metadata == {"version": "1.0"}

    def test_model_config_default_values(self):
        config = ModelConfig(
            name="minimal",
            provider="test",
            display_name="Minimal Model",
        )
        assert isinstance(config.capabilities, ModelCapabilities)
        assert isinstance(config.cost, ModelCost)
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.top_p == 0.9
        assert config.context_window == 8192
        assert config.available is True
        assert config.tags == []
        assert config.fallback_model is None
        assert config.metadata == {}

    def test_is_available_true(self):
        config = self._make_config(available=True)
        assert config.is_available() is True

    def test_is_available_false(self):
        config = self._make_config(available=False)
        assert config.is_available() is False

    def test_get_effective_context_window(self):
        config = self._make_config(context_window=32768, max_tokens=8192)
        # Effective context = context_window - max_tokens
        assert config.get_effective_context_window() == 32768 - 8192

    def test_get_effective_context_window_small_model(self):
        config = self._make_config(context_window=4096, max_tokens=1024)
        assert config.get_effective_context_window() == 3072

    def test_to_dict(self):
        config = self._make_config()
        d = config.to_dict()
        assert d["name"] == "test-model"
        assert d["provider"] == "ollama"
        assert d["display_name"] == "Test Model"
        assert d["max_tokens"] == 4096
        assert d["temperature"] == 0.7
        assert d["top_p"] == 0.9
        assert d["context_window"] == 8192
        assert d["available"] is True
        assert d["tags"] == ["test"]
        assert d["fallback_model"] == "fallback-model"
        assert d["metadata"] == {"version": "1.0"}
        # Check nested dicts
        assert "capabilities" in d
        assert isinstance(d["capabilities"], dict)
        assert "cost" in d
        assert isinstance(d["cost"], dict)

    def test_to_dict_includes_capabilities_and_cost(self):
        config = self._make_config()
        d = config.to_dict()
        assert d["capabilities"]["code_generation"] == 0.85
        assert d["cost"]["input_cost_per_1k"] == 0.0001


# =====================================================================
# RoleMapper tests
# =====================================================================


class TestRoleMapper:
    """Tests for the RoleMapper class."""

    def test_default_role_mapping_has_all_roles(self):
        mapper = RoleMapper()
        for role in AgentRole:
            model = mapper.get_model(role)
            assert model is not None, f"No model for role {role}"
            assert isinstance(model, str)

    def test_default_role_mapping_values(self):
        mapper = RoleMapper()
        assert mapper.get_model(AgentRole.ORCHESTRATOR) == "qwen3.5"
        assert mapper.get_model(AgentRole.BACKEND) == "qwen3-coder-next"
        assert mapper.get_model(AgentRole.FRONTEND) == "qwen3-coder-next"
        assert mapper.get_model(AgentRole.DEVOPS) == "qwen3.5"
        assert mapper.get_model(AgentRole.INFRA) == "qwen3-coder-next"
        assert mapper.get_model(AgentRole.DBA) == "deepseek-v3.2"
        assert mapper.get_model(AgentRole.QA) == "gemma4:31b"
        assert mapper.get_model(AgentRole.DESIGNER) == "mistral-large"
        assert mapper.get_model(AgentRole.REVIEWER) == "mistral-large"

    def test_custom_mapping_overrides_default(self):
        custom = {AgentRole.BACKEND: "custom-backend-model"}
        mapper = RoleMapper(custom_mapping=custom)
        assert mapper.get_model(AgentRole.BACKEND) == "custom-backend-model"
        # Other roles still use defaults
        assert mapper.get_model(AgentRole.ORCHESTRATOR) == "qwen3.5"

    def test_get_fallback_models(self):
        mapper = RoleMapper()
        fallbacks = mapper.get_fallback_models(AgentRole.ORCHESTRATOR)
        assert isinstance(fallbacks, list)
        assert len(fallbacks) > 0
        # Default fallbacks for orchestrator
        assert "qwen3-coder-next" in fallbacks

    def test_get_fallback_models_all_roles(self):
        mapper = RoleMapper()
        for role in AgentRole:
            fallbacks = mapper.get_fallback_models(role)
            assert isinstance(fallbacks, list)

    def test_set_model(self):
        mapper = RoleMapper()
        mapper.set_model(AgentRole.BACKEND, "new-backend-model")
        assert mapper.get_model(AgentRole.BACKEND) == "new-backend-model"

    def test_set_model_does_not_affect_other_roles(self):
        mapper = RoleMapper()
        original = mapper.get_model(AgentRole.ORCHESTRATOR)
        mapper.set_model(AgentRole.BACKEND, "new-backend-model")
        assert mapper.get_model(AgentRole.ORCHESTRATOR) == original

    def test_get_all_mappings(self):
        mapper = RoleMapper()
        mappings = mapper.get_all_mappings()
        assert isinstance(mappings, dict)
        assert len(mappings) == len(AgentRole)
        for role in AgentRole:
            assert role in mappings

    def test_get_model_unknown_role_returns_orchestrator_default(self):
        """When a role is not in the mapping, get_model should fall back to ORCHESTRATOR."""
        mapper = RoleMapper()
        # All default roles have mappings; the implementation uses ORCHESTRATOR as default.
        assert mapper.get_model(AgentRole.ORCHESTRATOR) == "qwen3.5"


# =====================================================================
# ModelRegistry tests
# =====================================================================


def _make_model_config(name="test-model", provider="ollama", available=True, **kwargs):
    """Helper to create a ModelConfig for testing."""
    caps = kwargs.pop("capabilities", ModelCapabilities(code_generation=0.85))
    cost = kwargs.pop("cost", ModelCost())
    return ModelConfig(
        name=name,
        provider=provider,
        display_name=kwargs.pop("display_name", f"Display {name}"),
        capabilities=caps,
        cost=cost,
        available=available,
        **kwargs,
    )


class TestModelRegistry:
    """Tests for the ModelRegistry class."""

    def test_register_model(self):
        registry = ModelRegistry()
        config = _make_model_config(name="model-a")
        registry.register(config)
        assert registry.get("model-a") is config

    def test_register_multiple_models(self):
        registry = ModelRegistry()
        config_a = _make_model_config(name="model-a")
        config_b = _make_model_config(name="model-b")
        registry.register(config_a)
        registry.register(config_b)
        assert registry.get("model-a") is config_a
        assert registry.get("model-b") is config_b

    def test_unregister_model(self):
        registry = ModelRegistry()
        config = _make_model_config(name="model-a")
        registry.register(config)
        result = registry.unregister("model-a")
        assert result is True
        assert registry.get("model-a") is None

    def test_unregister_nonexistent_model(self):
        registry = ModelRegistry()
        result = registry.unregister("nonexistent")
        assert result is False

    def test_get_model(self):
        registry = ModelRegistry()
        config = _make_model_config(name="model-a")
        registry.register(config)
        retrieved = registry.get("model-a")
        assert retrieved is config
        assert retrieved.name == "model-a"

    def test_get_nonexistent_model_returns_none(self):
        registry = ModelRegistry()
        result = registry.get("nonexistent")
        assert result is None

    def test_get_by_provider(self):
        registry = ModelRegistry()
        config_a = _make_model_config(name="model-a", provider="ollama")
        config_b = _make_model_config(name="model-b", provider="openai")
        config_c = _make_model_config(name="model-c", provider="ollama")
        registry.register(config_a)
        registry.register(config_b)
        registry.register(config_c)

        ollama_models = registry.get_by_provider("ollama")
        assert len(ollama_models) == 2
        openai_models = registry.get_by_provider("openai")
        assert len(openai_models) == 1

    def test_get_by_provider_empty(self):
        registry = ModelRegistry()
        result = registry.get_by_provider("anthropic")
        assert result == []

    def test_get_available_models(self):
        registry = ModelRegistry()
        config_a = _make_model_config(name="model-a", available=True)
        config_b = _make_model_config(name="model-b", available=False)
        config_c = _make_model_config(name="model-c", available=True)
        registry.register(config_a)
        registry.register(config_b)
        registry.register(config_c)

        available = registry.get_available_models()
        assert len(available) == 2
        names = [m.name for m in available]
        assert "model-a" in names
        assert "model-c" in names
        assert "model-b" not in names

    def test_get_models_by_capability(self):
        registry = ModelRegistry()
        # High code generation score
        config_a = _make_model_config(
            name="model-a",
            capabilities=ModelCapabilities(code_generation=0.95),
        )
        # Low code generation score
        config_b = _make_model_config(
            name="model-b",
            capabilities=ModelCapabilities(code_generation=0.3),
        )
        registry.register(config_a)
        registry.register(config_b)

        # With min_score=0.5, only model-a should qualify
        capable = registry.get_models_by_capability(TaskType.CODE_GENERATION, min_score=0.5)
        assert len(capable) == 1
        assert capable[0].name == "model-a"

    def test_get_models_by_capability_default_min_score(self):
        registry = ModelRegistry()
        config = _make_model_config(
            name="model-a",
            capabilities=ModelCapabilities(code_generation=0.6),
        )
        registry.register(config)
        # Default min_score is 0.5
        capable = registry.get_models_by_capability(TaskType.CODE_GENERATION)
        assert len(capable) == 1

    def test_get_models_by_capability_excludes_unavailable(self):
        registry = ModelRegistry()
        config_a = _make_model_config(
            name="model-a",
            available=True,
            capabilities=ModelCapabilities(code_generation=0.95),
        )
        config_b = _make_model_config(
            name="model-b",
            available=False,
            capabilities=ModelCapabilities(code_generation=0.95),
        )
        registry.register(config_a)
        registry.register(config_b)

        capable = registry.get_models_by_capability(TaskType.CODE_GENERATION, min_score=0.5)
        assert len(capable) == 1
        assert capable[0].name == "model-a"

    def test_update_availability(self):
        registry = ModelRegistry()
        config = _make_model_config(name="model-a", available=True)
        registry.register(config)

        assert config.available is True
        registry.update_availability("model-a", available=False)
        assert config.available is False

        registry.update_availability("model-a", available=True)
        assert config.available is True

    def test_update_availability_nonexistent_model(self):
        registry = ModelRegistry()
        # Should not raise, just do nothing
        registry.update_availability("nonexistent", available=False)

    def test_get_all_models(self):
        registry = ModelRegistry()
        config_a = _make_model_config(name="model-a")
        config_b = _make_model_config(name="model-b")
        registry.register(config_a)
        registry.register(config_b)

        all_models = registry.get_all_models()
        assert isinstance(all_models, dict)
        assert len(all_models) == 2
        assert "model-a" in all_models
        assert "model-b" in all_models

    def test_list_models(self):
        registry = ModelRegistry()
        config_a = _make_model_config(name="model-a")
        config_b = _make_model_config(name="model-b")
        registry.register(config_a)
        registry.register(config_b)

        names = registry.list_models()
        assert isinstance(names, list)
        assert set(names) == {"model-a", "model-b"}

    def test_clear(self):
        registry = ModelRegistry()
        config = _make_model_config(name="model-a")
        registry.register(config)

        assert len(registry.list_models()) == 1
        registry.clear()
        assert len(registry.list_models()) == 0
        assert registry.get("model-a") is None

    def test_register_overwrites_existing(self):
        registry = ModelRegistry()
        config_v1 = _make_model_config(name="model-a", display_name="Version 1")
        config_v2 = _make_model_config(name="model-a", display_name="Version 2")
        registry.register(config_v1)
        registry.register(config_v2)

        retrieved = registry.get("model-a")
        assert retrieved.display_name == "Version 2"


# =====================================================================
# LLMRouter tests
# =====================================================================


def _make_mock_settings():
    """Create a mock Settings object with the minimal interface the router needs."""
    settings = MagicMock()
    # The router reads model config from settings, but we'll let _initialize_models
    # use its internal defaults. Provide enough to avoid AttributeError.
    settings.model = MagicMock()
    settings.model.orchestrator = "qwen3.5"
    settings.model.backend = "qwen3-coder-next"
    settings.model.frontend = "qwen3-coder-next"
    settings.model.devops = "qwen3.5"
    settings.model.infra = "qwen3-coder-next"
    settings.model.dba = "deepseek-v3.2"
    settings.model.qa = "gemma4:31b"
    settings.model.designer = "mistral-large"
    settings.model.reviewer = "mistral-large"
    settings.model.embedding = "nomic-embed-text"
    return settings


class TestLLMRouterInit:
    """Tests for LLMRouter initialization."""

    def test_init_default_strategy(self):
        settings = _make_mock_settings()
        router = LLMRouter(settings=settings)
        assert router._strategy == RoutingStrategy.ROLE_BASED

    def test_init_custom_strategy(self):
        settings = _make_mock_settings()
        router = LLMRouter(settings=settings, strategy=RoutingStrategy.TASK_BASED)
        assert router._strategy == RoutingStrategy.TASK_BASED

    def test_init_registers_models(self):
        settings = _make_mock_settings()
        router = LLMRouter(settings=settings)
        models = router.get_all_models()
        assert len(models) > 0

    def test_init_with_cost_tracker(self):
        settings = _make_mock_settings()
        cost_tracker = MagicMock()
        router = LLMRouter(settings=settings, cost_tracker=cost_tracker)
        assert router._cost_tracker is cost_tracker


class TestLLMRouterRouteByRole:
    """Tests for LLMRouter.route_by_role method."""

    def _create_router(self):
        settings = _make_mock_settings()
        return LLMRouter(settings=settings)

    def test_route_orchestrator_role(self):
        router = self._create_router()
        model = router.route_by_role(AgentRole.ORCHESTRATOR)
        assert model is not None
        assert isinstance(model, ModelConfig)
        assert model.name == "qwen3.5"

    def test_route_backend_role(self):
        router = self._create_router()
        model = router.route_by_role(AgentRole.BACKEND)
        assert model is not None
        assert model.name == "qwen3-coder-next"

    def test_route_dba_role(self):
        router = self._create_router()
        model = router.route_by_role(AgentRole.DBA)
        assert model is not None
        assert model.name == "deepseek-v3.2"

    def test_route_qa_role(self):
        router = self._create_router()
        model = router.route_by_role(AgentRole.QA)
        assert model is not None
        assert model.name == "gemma4:31b"

    def test_route_reviewer_role(self):
        router = self._create_router()
        model = router.route_by_role(AgentRole.REVIEWER)
        assert model is not None
        assert model.name == "mistral-large"

    def test_route_by_string_role(self):
        router = self._create_router()
        model = router.route_by_role("backend")
        assert model is not None
        assert model.name == "qwen3-coder-next"

    def test_route_invalid_string_role_raises_error(self):
        router = self._create_router()
        with pytest.raises(Exception):
            # ConfigurationError for invalid role string
            router.route_by_role("nonexistent_role")

    def test_route_role_with_fallback(self):
        router = self._create_router()
        # Make primary model unavailable
        router.update_model_availability("qwen3.5", available=False)

        # Should fall back to a fallback model
        model = router.route_by_role(AgentRole.ORCHESTRATOR, fallback=True)
        assert model is not None
        assert model.is_available()

    def test_route_role_no_fallback_primary_unavailable(self):
        router = self._create_router()
        router.update_model_availability("qwen3.5", available=False)
        # With fallback=False, this should raise since primary is unavailable
        with pytest.raises(Exception):
            router.route_by_role(AgentRole.ORCHESTRATOR, fallback=False)

    def test_route_all_roles_return_available_models(self):
        router = self._create_router()
        for role in AgentRole:
            model = router.route_by_role(role)
            assert model is not None
            assert isinstance(model, ModelConfig)
            assert model.is_available()


class TestLLMRouterRouteByTask:
    """Tests for LLMRouter.route_by_task method."""

    def _create_router(self):
        settings = _make_mock_settings()
        return LLMRouter(settings=settings)

    def test_route_code_generation_task(self):
        router = self._create_router()
        model = router.route_by_task(TaskType.CODE_GENERATION)
        assert model is not None
        assert model.capabilities.get_score(TaskType.CODE_GENERATION) >= 0.5

    def test_route_code_review_task(self):
        router = self._create_router()
        model = router.route_by_task(TaskType.CODE_REVIEW)
        assert model is not None
        assert model.capabilities.get_score(TaskType.CODE_REVIEW) >= 0.5

    def test_route_database_task(self):
        router = self._create_router()
        model = router.route_by_task(TaskType.DATABASE)
        assert model is not None

    def test_route_architecture_task(self):
        router = self._create_router()
        model = router.route_by_task(TaskType.ARCHITECTURE)
        assert model is not None
        assert model.capabilities.reasoning >= 0.5

    def test_route_with_high_complexity(self):
        router = self._create_router()
        model = router.route_by_task(TaskType.CODE_GENERATION, complexity=TaskComplexity.HIGH)
        assert model is not None

    def test_route_with_critical_complexity(self):
        router = self._create_router()
        model = router.route_by_task(TaskType.CODE_REVIEW, complexity=TaskComplexity.CRITICAL)
        assert model is not None

    def test_route_with_low_complexity_prefers_speed(self):
        router = self._create_router()
        model = router.route_by_task(TaskType.CODE_GENERATION, complexity=TaskComplexity.LOW)
        assert model is not None

    def test_route_by_string_task_type(self):
        router = self._create_router()
        model = router.route_by_task("code_generation")
        assert model is not None

    def test_route_unknown_string_defaults_to_code_generation(self):
        router = self._create_router()
        # Unknown string task type should default to CODE_GENERATION
        model = router.route_by_task("unknown_task_type")
        assert model is not None

    def test_route_with_min_capability_threshold(self):
        router = self._create_router()
        model = router.route_by_task(TaskType.CODE_GENERATION, min_capability=0.9)
        assert model is not None
        assert model.capabilities.get_score(TaskType.CODE_GENERATION) >= 0.9

    def test_route_no_capable_models_raises_error(self):
        router = self._create_router()
        # Extremely high min_score that no model can meet
        with pytest.raises(Exception):
            router.route_by_task(TaskType.CODE_GENERATION, min_capability=0.99)


class TestLLMRouterRouteByCost:
    """Tests for LLMRouter.route_by_cost method."""

    def _create_router(self):
        settings = _make_mock_settings()
        return LLMRouter(settings=settings)

    def test_route_by_cost_with_budget(self):
        router = self._create_router()
        model = router.route_by_cost(
            TaskType.CODE_GENERATION,
            max_cost_per_1k=1.0,  # generous budget
        )
        assert model is not None

    def test_route_by_cost_string_task_type(self):
        router = self._create_router()
        model = router.route_by_cost(
            "code_generation",
            max_cost_per_1k=1.0,
        )
        assert model is not None

    def test_route_by_cost_very_low_budget_raises(self):
        router = self._create_router()
        # Very low budget that no model can satisfy with min_capability
        with pytest.raises(Exception):
            router.route_by_cost(
                TaskType.CODE_GENERATION,
                max_cost_per_1k=0.00001,
                min_capability=0.8,
            )


class TestLLMRouterRoute:
    """Tests for the main LLMRouter.route method."""

    def _create_router(self):
        settings = _make_mock_settings()
        return LLMRouter(settings=settings)

    def test_route_role_based(self):
        router = self._create_router()
        model = router.route(role=AgentRole.BACKEND, strategy=RoutingStrategy.ROLE_BASED)
        assert model is not None
        assert isinstance(model, ModelConfig)

    def test_route_task_based(self):
        router = self._create_router()
        model = router.route(
            task_type=TaskType.CODE_GENERATION,
            strategy=RoutingStrategy.TASK_BASED,
        )
        assert model is not None

    def test_route_cost_optimized(self):
        router = self._create_router()
        model = router.route(
            task_type=TaskType.CODE_GENERATION,
            max_cost=1.0,
            strategy=RoutingStrategy.COST_OPTIMIZED,
        )
        assert model is not None

    def test_route_quality_first(self):
        router = self._create_router()
        model = router.route(strategy=RoutingStrategy.QUALITY_FIRST)
        assert model is not None
        # Quality first should return the highest quality model
        assert model.is_available()

    def test_route_balanced(self):
        router = self._create_router()
        model = router.route(
            task_type=TaskType.CODE_GENERATION,
            strategy=RoutingStrategy.BALANCED,
        )
        assert model is not None

    def test_route_role_based_requires_role(self):
        router = self._create_router()
        with pytest.raises(Exception):
            router.route(strategy=RoutingStrategy.ROLE_BASED)

    def test_route_task_based_requires_task_type(self):
        router = self._create_router()
        with pytest.raises(Exception):
            router.route(strategy=RoutingStrategy.TASK_BASED)

    def test_route_cost_optimized_requires_task_and_cost(self):
        router = self._create_router()
        with pytest.raises(Exception):
            router.route(strategy=RoutingStrategy.COST_OPTIMIZED)

    def test_route_default_strategy_is_role_based(self):
        router = self._create_router()
        # With no strategy, it defaults to role-based
        model = router.route(role=AgentRole.BACKEND)
        assert model is not None


class TestLLMRouterModelManagement:
    """Tests for LLMRouter model management methods."""

    def _create_router(self):
        settings = _make_mock_settings()
        return LLMRouter(settings=settings)

    def test_get_model(self):
        router = self._create_router()
        model = router.get_model("qwen3.5")
        assert model is not None
        assert model.name == "qwen3.5"

    def test_get_model_not_found_raises(self):
        router = self._create_router()
        with pytest.raises(Exception):
            router.get_model("nonexistent-model")

    def test_get_all_models(self):
        router = self._create_router()
        models = router.get_all_models()
        assert isinstance(models, dict)
        assert len(models) > 0

    def test_get_available_models(self):
        router = self._create_router()
        available = router.get_available_models()
        assert isinstance(available, list)
        assert len(available) > 0
        for model in available:
            assert model.is_available()

    def test_update_model_availability(self):
        router = self._create_router()
        # Make a model unavailable
        router.update_model_availability("qwen3.5", available=False)
        model = router.get_model("qwen3.5")
        assert model.available is False

        # Make it available again
        router.update_model_availability("qwen3.5", available=True)
        model = router.get_model("qwen3.5")
        assert model.available is True

    def test_set_role_model(self):
        router = self._create_router()
        router.set_role_model(AgentRole.BACKEND, "deepseek-v3.2")

        model = router.route_by_role(AgentRole.BACKEND)
        assert model.name == "deepseek-v3.2"

    def test_set_role_model_by_string(self):
        router = self._create_router()
        router.set_role_model("backend", "qwen3.5")

        model = router.route_by_role(AgentRole.BACKEND)
        assert model.name == "qwen3.5"

    def test_set_role_model_nonexistent_model_raises(self):
        router = self._create_router()
        with pytest.raises(Exception):
            router.set_role_model(AgentRole.BACKEND, "nonexistent-model")


class TestLLMRouterCustomRouting:
    """Tests for custom routing rules."""

    def _create_router(self):
        settings = _make_mock_settings()
        return LLMRouter(settings=settings)

    def test_register_custom_rule(self):
        router = self._create_router()

        def my_rule(router_instance, context):
            # Always return the cheapest available model
            models = router_instance.get_available_models()
            return min(models, key=lambda m: m.cost.input_cost_per_1k)

        router.register_custom_rule("cheapest", my_rule)
        assert "cheapest" in router._custom_rules

    def test_route_custom(self):
        router = self._create_router()

        def cheapest_rule(router_instance, context):
            models = router_instance.get_available_models()
            return min(models, key=lambda m: m.cost.input_cost_per_1k)

        router.register_custom_rule("cheapest", cheapest_rule)
        model = router.route_custom("cheapest", {"task": "test"})
        assert model is not None
        assert isinstance(model, ModelConfig)

    def test_route_custom_not_found_raises(self):
        router = self._create_router()
        with pytest.raises(Exception):
            router.route_custom("nonexistent_rule", {})


class TestLLMRouterRoutingStats:
    """Tests for get_routing_stats and estimate_cost."""

    def _create_router(self):
        settings = _make_mock_settings()
        return LLMRouter(settings=settings)

    def test_get_routing_stats(self):
        router = self._create_router()
        stats = router.get_routing_stats()
        assert isinstance(stats, dict)
        assert "total_models" in stats
        assert "available_models" in stats
        assert "role_mappings" in stats
        assert "default_strategy" in stats
        assert stats["total_models"] > 0
        assert stats["available_models"] > 0

    def test_get_routing_stats_includes_custom_rules(self):
        router = self._create_router()

        def my_rule(router_instance, context):
            return router_instance.get_available_models()[0]

        router.register_custom_rule("test_rule", my_rule)
        stats = router.get_routing_stats()
        assert "test_rule" in stats["custom_rules"]

    def test_estimate_cost(self):
        router = self._create_router()
        cost = router.estimate_cost("qwen3.5", input_tokens=1000, output_tokens=500)
        assert isinstance(cost, float)
        assert cost >= 0

    def test_estimate_cost_known_model(self):
        router = self._create_router()
        # qwen3.5: input_cost_per_1k=0.0001, output_cost_per_1k=0.0002
        cost = router.estimate_cost("qwen3.5", input_tokens=10000, output_tokens=5000)
        expected = (10000 / 1000) * 0.0001 + (5000 / 1000) * 0.0002
        assert abs(cost - expected) < 0.0001

    def test_estimate_cost_unknown_model_raises(self):
        router = self._create_router()
        with pytest.raises(Exception):
            router.estimate_cost("nonexistent-model", input_tokens=100, output_tokens=50)


class TestLLMRouterGetModelForTask:
    """Tests for get_model_for_task method."""

    def _create_router(self):
        settings = _make_mock_settings()
        return LLMRouter(settings=settings)

    def test_code_generation_keywords(self):
        router = self._create_router()
        model = router.get_model_for_task("Create a REST API endpoint")
        assert model is not None

    def test_database_keywords(self):
        router = self._create_router()
        model = router.get_model_for_task("Design a database schema for users")
        assert model is not None

    def test_testing_keywords(self):
        router = self._create_router()
        model = router.get_model_for_task("Write unit tests for the login module")
        assert model is not None

    def test_review_keywords(self):
        router = self._create_router()
        model = router.get_model_for_task("Review the code changes in PR #42")
        assert model is not None

    def test_deployment_keywords(self):
        router = self._create_router()
        model = router.get_model_for_task("Deploy to production environment")
        assert model is not None

    def test_architecture_keywords(self):
        router = self._create_router()
        model = router.get_model_for_task("Design the system architecture for microservices")
        assert model is not None

    def test_with_role_hint(self):
        router = self._create_router()
        model = router.get_model_for_task("Write some code", role=AgentRole.BACKEND)
        assert model is not None
        # When role is provided, it should use role-based routing
        assert model.name == "qwen3-coder-next"

    def test_critical_keywords(self):
        router = self._create_router()
        model = router.get_model_for_task("Critical security review for production")
        assert model is not None

    def test_simple_keywords(self):
        router = self._create_router()
        model = router.get_model_for_task("Simple quick fix for typo")
        assert model is not None
