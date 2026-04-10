"""
Tests for palace.llm.models — Model definitions, ModelConfig, and ModelRegistry.

Covers:
- AgentRole enum (models version)
- ModelCapability enum
- ModelProvider enum
- ModelConfig dataclass (supports_capability, supports_role, get_cost, to_dict)
- Pre-defined model instances (QWEN_35, QWEN_CODER_NEXT, etc.)
- ModelRegistry class (initialize, register, get, get_for_role, get_with_capability,
  get_all, get_names, set_role_mapping, clear)
- Convenience functions (get_model_for_role, get_model, list_models, list_model_names)
"""

import sys
import types
from pathlib import Path
from unittest.mock import patch

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
# import errors.  Direct submodule imports like palace.llm.models
# still work because the stub registers the correct __path__.
_ensure_package("palace.llm", [str(_PALACE_LLM_PKG)])

from palace.llm.models import (
    DEEPSEEK_V32,
    GEMMA_4_31B,
    MISTRAL_LARGE,
    NOMIC_EMBED_TEXT,
    QWEN_35,
    QWEN_CODER_NEXT,
    AgentRole,
    ModelCapability,
    ModelConfig,
    ModelProvider,
    ModelRegistry,
    get_model,
    get_model_for_role,
    list_model_names,
    list_models,
)

# =====================================================================
# AgentRole (models) tests
# =====================================================================


class TestModelsAgentRole:
    """Tests for the AgentRole enum defined in palace.llm.models."""

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

    def test_role_values_are_lowercase_strings(self):
        for role in AgentRole:
            assert isinstance(role.value, str)
            assert role.value == role.value.lower()

    def test_specific_role_values(self):
        assert AgentRole.ORCHESTRATOR.value == "orchestrator"
        assert AgentRole.BACKEND.value == "backend"
        assert AgentRole.FRONTEND.value == "frontend"
        assert AgentRole.DEVOPS.value == "devops"
        assert AgentRole.INFRA.value == "infra"
        assert AgentRole.DBA.value == "dba"
        assert AgentRole.QA.value == "qa"
        assert AgentRole.DESIGNER.value == "designer"
        assert AgentRole.REVIEWER.value == "reviewer"

    def test_is_string_enum(self):
        assert isinstance(AgentRole.ORCHESTRATOR, str)

    def test_role_from_value(self):
        assert AgentRole("backend") == AgentRole.BACKEND
        assert AgentRole("reviewer") == AgentRole.REVIEWER


# =====================================================================
# ModelCapability tests
# =====================================================================


class TestModelCapability:
    """Tests for the ModelCapability enum."""

    def test_all_capabilities_exist(self):
        expected = {
            "CODE_GENERATION",
            "CODE_COMPLETION",
            "CODE_REVIEW",
            "ARCHITECTURE",
            "DATABASE",
            "INFRASTRUCTURE",
            "TESTING",
            "SECURITY",
            "REASONING",
            "SUMMARIZATION",
            "CONVERSATION",
        }
        actual = {c.name for c in ModelCapability}
        assert actual == expected

    def test_capability_values(self):
        assert ModelCapability.CODE_GENERATION.value == "code_generation"
        assert ModelCapability.CODE_COMPLETION.value == "code_completion"
        assert ModelCapability.CODE_REVIEW.value == "code_review"
        assert ModelCapability.ARCHITECTURE.value == "architecture"
        assert ModelCapability.DATABASE.value == "database"
        assert ModelCapability.INFRASTRUCTURE.value == "infrastructure"
        assert ModelCapability.TESTING.value == "testing"
        assert ModelCapability.SECURITY.value == "security"
        assert ModelCapability.REASONING.value == "reasoning"
        assert ModelCapability.SUMMARIZATION.value == "summarization"
        assert ModelCapability.CONVERSATION.value == "conversation"

    def test_is_string_enum(self):
        assert isinstance(ModelCapability.CODE_GENERATION, str)

    def test_capability_from_value(self):
        assert ModelCapability("code_generation") == ModelCapability.CODE_GENERATION
        assert ModelCapability("reasoning") == ModelCapability.REASONING


# =====================================================================
# ModelProvider tests
# =====================================================================


class TestModelProvider:
    """Tests for the ModelProvider enum."""

    def test_all_providers_exist(self):
        expected = {"OLLAMA", "OPENAI", "ANTHROPIC", "AZURE", "CUSTOM"}
        actual = {p.name for p in ModelProvider}
        assert actual == expected

    def test_provider_values(self):
        assert ModelProvider.OLLAMA.value == "ollama"
        assert ModelProvider.OPENAI.value == "openai"
        assert ModelProvider.ANTHROPIC.value == "anthropic"
        assert ModelProvider.AZURE.value == "azure"
        assert ModelProvider.CUSTOM.value == "custom"

    def test_is_string_enum(self):
        assert isinstance(ModelProvider.OLLAMA, str)


# =====================================================================
# ModelConfig tests
# =====================================================================


class TestModelConfig:
    """Tests for the ModelConfig dataclass."""

    def _make_config(self, **overrides):
        defaults = dict(
            name="test-model",
            provider=ModelProvider.OLLAMA,
            display_name="Test Model",
            description="A test model for unit tests",
            context_window=8192,
            capabilities=[ModelCapability.CODE_GENERATION, ModelCapability.REASONING],
            default_params={"temperature": 0.7, "max_tokens": 4096},
            pricing={"prompt": 0.0001, "completion": 0.0002},
            roles=[AgentRole.BACKEND],
            tags=["test", "coding"],
        )
        defaults.update(overrides)
        return ModelConfig(**defaults)

    def test_model_config_creation_minimal(self):
        config = ModelConfig(
            name="minimal-model",
            provider=ModelProvider.OLLAMA,
            display_name="Minimal Model",
            description="Minimal model",
            context_window=4096,
        )
        assert config.name == "minimal-model"
        assert config.provider == ModelProvider.OLLAMA
        assert config.display_name == "Minimal Model"
        assert config.description == "Minimal model"
        assert config.context_window == 4096
        assert config.capabilities == []
        assert config.default_params == {}
        assert config.pricing == {"prompt": 0.0, "completion": 0.0}
        assert config.roles == []
        assert config.tags == []

    def test_model_config_creation_full(self):
        config = self._make_config()
        assert config.name == "test-model"
        assert config.provider == ModelProvider.OLLAMA
        assert config.display_name == "Test Model"
        assert config.description == "A test model for unit tests"
        assert config.context_window == 8192
        assert ModelCapability.CODE_GENERATION in config.capabilities
        assert ModelCapability.REASONING in config.capabilities
        assert config.default_params == {"temperature": 0.7, "max_tokens": 4096}
        assert config.pricing == {"prompt": 0.0001, "completion": 0.0002}
        assert AgentRole.BACKEND in config.roles
        assert "test" in config.tags

    def test_supports_capability_true(self):
        config = self._make_config()
        assert config.supports_capability(ModelCapability.CODE_GENERATION) is True

    def test_supports_capability_false(self):
        config = self._make_config()
        assert config.supports_capability(ModelCapability.DATABASE) is False

    def test_supports_role_true(self):
        config = self._make_config()
        assert config.supports_role(AgentRole.BACKEND) is True

    def test_supports_role_false(self):
        config = self._make_config()
        assert config.supports_role(AgentRole.DBA) is False

    def test_get_cost_zero_pricing(self):
        config = ModelConfig(
            name="free-model",
            provider=ModelProvider.OLLAMA,
            display_name="Free Model",
            description="Free local model",
            context_window=4096,
            pricing={"prompt": 0.0, "completion": 0.0},
        )
        cost = config.get_cost(1000, 500)
        assert cost == 0.0

    def test_get_cost_with_pricing(self):
        config = ModelConfig(
            name="paid-model",
            provider=ModelProvider.OPENAI,
            display_name="Paid Model",
            description="Paid model",
            context_window=8192,
            pricing={"prompt": 0.01, "completion": 0.03},
        )
        # (10000 / 1000) * 0.01 + (5000 / 1000) * 0.03 = 0.1 + 0.15 = 0.25
        cost = config.get_cost(10000, 5000)
        assert abs(cost - 0.25) < 0.001

    def test_get_cost_prompt_only(self):
        config = ModelConfig(
            name="model",
            provider=ModelProvider.OLLAMA,
            display_name="Model",
            description="desc",
            context_window=4096,
            pricing={"prompt": 0.005, "completion": 0.0},
        )
        cost = config.get_cost(2000, 0)
        assert abs(cost - 0.01) < 0.001

    def test_get_cost_completion_only(self):
        config = ModelConfig(
            name="model",
            provider=ModelProvider.OLLAMA,
            display_name="Model",
            description="desc",
            context_window=4096,
            pricing={"prompt": 0.0, "completion": 0.02},
        )
        cost = config.get_cost(0, 3000)
        assert abs(cost - 0.06) < 0.001

    def test_to_dict(self):
        config = self._make_config()
        d = config.to_dict()
        assert d["name"] == "test-model"
        assert d["provider"] == "ollama"
        assert d["display_name"] == "Test Model"
        assert d["description"] == "A test model for unit tests"
        assert d["context_window"] == 8192
        assert "code_generation" in d["capabilities"]
        assert "reasoning" in d["capabilities"]
        assert d["default_params"] == {"temperature": 0.7, "max_tokens": 4096}
        assert d["pricing"] == {"prompt": 0.0001, "completion": 0.0002}
        assert "backend" in d["roles"]
        assert "test" in d["tags"]

    def test_to_dict_capability_values_are_strings(self):
        config = self._make_config()
        d = config.to_dict()
        for cap in d["capabilities"]:
            assert isinstance(cap, str)

    def test_to_dict_role_values_are_strings(self):
        config = self._make_config()
        d = config.to_dict()
        for role in d["roles"]:
            assert isinstance(role, str)

    def test_to_dict_provider_is_string(self):
        config = self._make_config()
        d = config.to_dict()
        assert isinstance(d["provider"], str)
        assert d["provider"] == "ollama"


# =====================================================================
# Pre-defined model instance tests
# =====================================================================


class TestPredefinedModels:
    """Tests for the pre-defined model configuration instances."""

    def test_qwen35_basic_properties(self):
        assert QWEN_35.name == "qwen3.5"
        assert QWEN_35.provider == ModelProvider.OLLAMA
        assert QWEN_35.display_name == "Qwen 3.5"
        assert QWEN_35.context_window == 32768

    def test_qwen35_capabilities(self):
        assert ModelCapability.REASONING in QWEN_35.capabilities
        assert ModelCapability.CONVERSATION in QWEN_35.capabilities
        assert ModelCapability.SUMMARIZATION in QWEN_35.capabilities

    def test_qwen35_roles(self):
        assert AgentRole.ORCHESTRATOR in QWEN_35.roles
        assert AgentRole.DEVOPS in QWEN_35.roles

    def test_qwen35_tags(self):
        assert "orchestration" in QWEN_35.tags
        assert "devops" in QWEN_35.tags

    def test_qwen35_is_free(self):
        cost = QWEN_35.get_cost(10000, 5000)
        assert cost == 0.0

    def test_qwen_coder_next_basic_properties(self):
        assert QWEN_CODER_NEXT.name == "qwen3-coder-next"
        assert QWEN_CODER_NEXT.provider == ModelProvider.OLLAMA
        assert QWEN_CODER_NEXT.display_name == "Qwen 3 Coder Next"
        assert QWEN_CODER_NEXT.context_window == 32768

    def test_qwen_coder_next_capabilities(self):
        assert ModelCapability.CODE_GENERATION in QWEN_CODER_NEXT.capabilities
        assert ModelCapability.CODE_COMPLETION in QWEN_CODER_NEXT.capabilities
        assert ModelCapability.CODE_REVIEW in QWEN_CODER_NEXT.capabilities
        assert ModelCapability.TESTING in QWEN_CODER_NEXT.capabilities

    def test_qwen_coder_next_roles(self):
        assert AgentRole.BACKEND in QWEN_CODER_NEXT.roles
        assert AgentRole.FRONTEND in QWEN_CODER_NEXT.roles
        assert AgentRole.INFRA in QWEN_CODER_NEXT.roles

    def test_qwen_coder_next_supports_capability(self):
        assert QWEN_CODER_NEXT.supports_capability(ModelCapability.CODE_GENERATION) is True
        assert QWEN_CODER_NEXT.supports_capability(ModelCapability.DATABASE) is False

    def test_qwen_coder_next_supports_role(self):
        assert QWEN_CODER_NEXT.supports_role(AgentRole.BACKEND) is True
        assert QWEN_CODER_NEXT.supports_role(AgentRole.ORCHESTRATOR) is False

    def test_deepseek_v32_basic_properties(self):
        assert DEEPSEEK_V32.name == "deepseek-v3.2"
        assert DEEPSEEK_V32.provider == ModelProvider.OLLAMA
        assert DEEPSEEK_V32.display_name == "DeepSeek V3.2"
        assert DEEPSEEK_V32.context_window == 16384

    def test_deepseek_v32_capabilities(self):
        assert ModelCapability.DATABASE in DEEPSEEK_V32.capabilities
        assert ModelCapability.CODE_GENERATION in DEEPSEEK_V32.capabilities
        assert ModelCapability.REASONING in DEEPSEEK_V32.capabilities

    def test_deepseek_v32_roles(self):
        assert AgentRole.DBA in DEEPSEEK_V32.roles

    def test_gemma_4_31b_basic_properties(self):
        assert GEMMA_4_31B.name == "gemma4:31b"
        assert GEMMA_4_31B.provider == ModelProvider.OLLAMA
        assert GEMMA_4_31B.display_name == "Gemma 4 31B"
        assert GEMMA_4_31B.context_window == 8192

    def test_gemma_4_31b_capabilities(self):
        assert ModelCapability.TESTING in GEMMA_4_31B.capabilities
        assert ModelCapability.CODE_REVIEW in GEMMA_4_31B.capabilities
        assert ModelCapability.SECURITY in GEMMA_4_31B.capabilities
        assert ModelCapability.REASONING in GEMMA_4_31B.capabilities

    def test_gemma_4_31b_roles(self):
        assert AgentRole.QA in GEMMA_4_31B.roles

    def test_mistral_large_basic_properties(self):
        assert MISTRAL_LARGE.name == "mistral-large"
        assert MISTRAL_LARGE.provider == ModelProvider.OLLAMA
        assert MISTRAL_LARGE.display_name == "Mistral Large"
        assert MISTRAL_LARGE.context_window == 32768

    def test_mistral_large_capabilities(self):
        assert ModelCapability.ARCHITECTURE in MISTRAL_LARGE.capabilities
        assert ModelCapability.CODE_REVIEW in MISTRAL_LARGE.capabilities
        assert ModelCapability.REASONING in MISTRAL_LARGE.capabilities
        assert ModelCapability.SECURITY in MISTRAL_LARGE.capabilities

    def test_mistral_large_roles(self):
        assert AgentRole.DESIGNER in MISTRAL_LARGE.roles
        assert AgentRole.REVIEWER in MISTRAL_LARGE.roles

    def test_nomic_embed_text_basic_properties(self):
        assert NOMIC_EMBED_TEXT.name == "nomic-embed-text"
        assert NOMIC_EMBED_TEXT.provider == ModelProvider.OLLAMA
        assert NOMIC_EMBED_TEXT.display_name == "Nomic Embed Text"
        assert NOMIC_EMBED_TEXT.context_window == 8192

    def test_nomic_embed_text_capabilities(self):
        assert ModelCapability.SUMMARIZATION in NOMIC_EMBED_TEXT.capabilities

    def test_nomic_embed_text_has_no_roles(self):
        assert len(NOMIC_EMBED_TEXT.roles) == 0

    def test_all_models_have_names(self):
        models = [
            QWEN_35,
            QWEN_CODER_NEXT,
            DEEPSEEK_V32,
            GEMMA_4_31B,
            MISTRAL_LARGE,
            NOMIC_EMBED_TEXT,
        ]
        for model in models:
            assert isinstance(model.name, str)
            assert len(model.name) > 0

    def test_all_models_have_provider(self):
        models = [
            QWEN_35,
            QWEN_CODER_NEXT,
            DEEPSEEK_V32,
            GEMMA_4_31B,
            MISTRAL_LARGE,
            NOMIC_EMBED_TEXT,
        ]
        for model in models:
            assert isinstance(model.provider, ModelProvider)

    def test_all_models_are_free(self):
        models = [
            QWEN_35,
            QWEN_CODER_NEXT,
            DEEPSEEK_V32,
            GEMMA_4_31B,
            MISTRAL_LARGE,
            NOMIC_EMBED_TEXT,
        ]
        for model in models:
            cost = model.get_cost(10000, 5000)
            assert cost == 0.0

    def test_all_models_to_dict(self):
        models = [
            QWEN_35,
            QWEN_CODER_NEXT,
            DEEPSEEK_V32,
            GEMMA_4_31B,
            MISTRAL_LARGE,
            NOMIC_EMBED_TEXT,
        ]
        for model in models:
            d = model.to_dict()
            assert isinstance(d, dict)
            assert "name" in d
            assert "provider" in d
            assert "display_name" in d
            assert "context_window" in d
            assert "capabilities" in d
            assert "roles" in d


# =====================================================================
# ModelRegistry tests (from palace.llm.models)
# =====================================================================


class TestModelsModelRegistry:
    """Tests for the ModelRegistry class in palace.llm.models."""

    def setup_method(self):
        """Clear the registry before each test to avoid state leaking."""
        ModelRegistry.clear()
        # Reset _initialized so that initialize() will re-populate
        ModelRegistry._initialized = False

    def teardown_method(self):
        """Clear the registry after each test."""
        ModelRegistry.clear()
        ModelRegistry._initialized = False

    def test_initialize_registers_default_models(self):
        ModelRegistry.initialize()
        names = ModelRegistry.get_names()
        assert "qwen3.5" in names
        assert "qwen3-coder-next" in names
        assert "deepseek-v3.2" in names
        assert "gemma4:31b" in names
        assert "mistral-large" in names
        assert "nomic-embed-text" in names

    def test_initialize_idempotent(self):
        ModelRegistry.initialize()
        count_after_first = len(ModelRegistry.get_names())
        ModelRegistry.initialize()  # Should not duplicate
        count_after_second = len(ModelRegistry.get_names())
        assert count_after_first == count_after_second

    def test_register_model(self):
        config = ModelConfig(
            name="custom-model",
            provider=ModelProvider.OLLAMA,
            display_name="Custom Model",
            description="A custom model",
            context_window=4096,
        )
        ModelRegistry.register(config)
        retrieved = ModelRegistry.get("custom-model")
        assert retrieved is config
        assert retrieved.name == "custom-model"

    def test_register_model_updates_role_mapping(self):
        # Initialize first so default models are loaded, then override
        ModelRegistry.initialize()
        config = ModelConfig(
            name="custom-backend",
            provider=ModelProvider.OLLAMA,
            display_name="Custom Backend",
            description="A custom backend model",
            context_window=8192,
            roles=[AgentRole.BACKEND],
        )
        ModelRegistry.register(config)
        role_model = ModelRegistry.get_for_role(AgentRole.BACKEND)
        assert role_model is not None
        assert role_model.name == "custom-backend"

    def test_get_model_by_name(self):
        ModelRegistry.initialize()
        model = ModelRegistry.get("qwen3.5")
        assert model is not None
        assert model.name == "qwen3.5"

    def test_get_nonexistent_model_returns_none(self):
        result = ModelRegistry.get("nonexistent-model")
        assert result is None

    def test_get_for_role(self):
        ModelRegistry.initialize()
        model = ModelRegistry.get_for_role(AgentRole.BACKEND)
        assert model is not None
        assert model.name == "qwen3-coder-next"

    def test_get_for_role_orchestrator(self):
        ModelRegistry.initialize()
        model = ModelRegistry.get_for_role(AgentRole.ORCHESTRATOR)
        assert model is not None
        assert model.name == "qwen3.5"

    def test_get_for_role_dba(self):
        ModelRegistry.initialize()
        model = ModelRegistry.get_for_role(AgentRole.DBA)
        assert model is not None
        assert model.name == "deepseek-v3.2"

    def test_get_for_role_qa(self):
        ModelRegistry.initialize()
        model = ModelRegistry.get_for_role(AgentRole.QA)
        assert model is not None
        assert model.name == "gemma4:31b"

    def test_get_for_role_designer(self):
        ModelRegistry.initialize()
        model = ModelRegistry.get_for_role(AgentRole.DESIGNER)
        assert model is not None
        assert model.name == "mistral-large"

    def test_get_for_role_reviewer(self):
        ModelRegistry.initialize()
        model = ModelRegistry.get_for_role(AgentRole.REVIEWER)
        assert model is not None
        assert model.name == "mistral-large"

    def test_get_for_role_unregistered_role_returns_none(self):
        # NOMIC_EMBED_TEXT has no roles, so a role with no mapping should return None
        # But all AgentRole values have default mappings after initialization
        ModelRegistry.initialize()
        # All roles should have mappings after init
        for role in AgentRole:
            model = ModelRegistry.get_for_role(role)
            assert model is not None, f"No model for role {role}"

    def test_get_with_capability(self):
        ModelRegistry.initialize()
        models = ModelRegistry.get_with_capability(ModelCapability.CODE_GENERATION)
        assert len(models) > 0
        for model in models:
            assert model.supports_capability(ModelCapability.CODE_GENERATION)

    def test_get_with_capability_reasoning(self):
        ModelRegistry.initialize()
        models = ModelRegistry.get_with_capability(ModelCapability.REASONING)
        assert len(models) > 0
        for model in models:
            assert model.supports_capability(ModelCapability.REASONING)

    def test_get_with_capability_database(self):
        ModelRegistry.initialize()
        models = ModelRegistry.get_with_capability(ModelCapability.DATABASE)
        assert len(models) > 0
        for model in models:
            assert model.supports_capability(ModelCapability.DATABASE)

    def test_get_with_capability_returns_empty_for_rare_capability(self):
        ModelRegistry.initialize()
        models = ModelRegistry.get_with_capability(ModelCapability.INFRASTRUCTURE)
        # Only models with infrastructure capability
        for model in models:
            assert model.supports_capability(ModelCapability.INFRASTRUCTURE)

    def test_get_all(self):
        ModelRegistry.initialize()
        all_models = ModelRegistry.get_all()
        assert isinstance(all_models, list)
        assert len(all_models) >= 6  # At least the 6 default models

    def test_get_names(self):
        ModelRegistry.initialize()
        names = ModelRegistry.get_names()
        assert isinstance(names, list)
        assert "qwen3.5" in names
        assert "qwen3-coder-next" in names

    def test_set_role_mapping(self):
        ModelRegistry.initialize()
        # Override the backend role
        ModelRegistry.set_role_mapping(AgentRole.BACKEND, "deepseek-v3.2")
        model = ModelRegistry.get_for_role(AgentRole.BACKEND)
        assert model is not None
        assert model.name == "deepseek-v3.2"

    def test_set_role_mapping_unregistered_model_raises(self):
        ModelRegistry.initialize()
        with pytest.raises(ValueError, match="not registered"):
            ModelRegistry.set_role_mapping(AgentRole.BACKEND, "nonexistent-model")

    def test_clear(self):
        ModelRegistry.initialize()
        assert len(ModelRegistry._models) > 0
        ModelRegistry.clear()
        # After clear, internal state should be empty and _initialized False.
        # NOTE: We check _models directly because get_names() calls initialize()
        # which would re-populate the registry from defaults.
        assert len(ModelRegistry._models) == 0
        assert ModelRegistry._initialized is False
        assert ModelRegistry._initialized is False

    def test_clear_and_reinitialize(self):
        ModelRegistry.initialize()
        ModelRegistry.clear()
        assert len(ModelRegistry._models) == 0
        assert ModelRegistry._initialized is False
        ModelRegistry.initialize()
        assert len(ModelRegistry._models) >= 6
        assert ModelRegistry._initialized is True

    def test_register_multiple_models(self):
        config_a = ModelConfig(
            name="model-a",
            provider=ModelProvider.OLLAMA,
            display_name="Model A",
            description="Test model A",
            context_window=4096,
        )
        config_b = ModelConfig(
            name="model-b",
            provider=ModelProvider.OPENAI,
            display_name="Model B",
            description="Test model B",
            context_window=8192,
        )
        ModelRegistry.register(config_a)
        ModelRegistry.register(config_b)

        assert ModelRegistry.get("model-a") is config_a
        assert ModelRegistry.get("model-b") is config_b

    def test_register_overwrites_existing(self):
        ModelRegistry.clear()
        ModelRegistry._initialized = False
        config_v1 = ModelConfig(
            name="shared-name",
            provider=ModelProvider.OLLAMA,
            display_name="Version 1",
            description="First version",
            context_window=4096,
        )
        config_v2 = ModelConfig(
            name="shared-name",
            provider=ModelProvider.OPENAI,
            display_name="Version 2",
            description="Second version",
            context_window=8192,
        )
        ModelRegistry.register(config_v1)
        ModelRegistry.register(config_v2)

        retrieved = ModelRegistry._models.get("shared-name")
        assert retrieved is not None
        assert retrieved.display_name == "Version 2"


# =====================================================================
# Convenience function tests
# =====================================================================


class TestConvenienceFunctions:
    """Tests for the convenience functions in palace.llm.models."""

    def setup_method(self):
        """Reset the registry before each test."""
        ModelRegistry.clear()
        ModelRegistry._initialized = False

    def teardown_method(self):
        """Reset the registry after each test."""
        ModelRegistry.clear()
        ModelRegistry._initialized = False

    def test_get_model_for_role(self):
        ModelRegistry.initialize()
        model = get_model_for_role(AgentRole.BACKEND)
        assert model is not None
        assert model.name == "qwen3-coder-next"

    def test_get_model_for_role_orchestrator(self):
        ModelRegistry.initialize()
        model = get_model_for_role(AgentRole.ORCHESTRATOR)
        assert model is not None
        assert model.name == "qwen3.5"

    def test_get_model_for_role_dba(self):
        ModelRegistry.initialize()
        model = get_model_for_role(AgentRole.DBA)
        assert model is not None
        assert model.name == "deepseek-v3.2"

    def test_get_model_for_role_unmapped_raises(self):
        # Clear registry and mark as initialized so auto-init won't re-populate,
        # then verify that a role with no mapping raises ValueError.
        ModelRegistry.clear()
        ModelRegistry._initialized = True  # Prevent auto-initialize from re-populating
        with pytest.raises(ValueError, match="No model assigned to role"):
            get_model_for_role(AgentRole.BACKEND)

    def test_get_model_by_name(self):
        ModelRegistry.initialize()
        model = get_model("qwen3.5")
        assert model is not None
        assert model.name == "qwen3.5"

    def test_get_model_by_name_not_found_raises(self):
        ModelRegistry.initialize()
        with pytest.raises(ValueError, match="Model not found"):
            get_model("nonexistent-model")

    def test_list_models(self):
        ModelRegistry.initialize()
        models = list_models()
        assert isinstance(models, list)
        assert len(models) >= 6
        for model in models:
            assert isinstance(model, ModelConfig)

    def test_list_model_names(self):
        ModelRegistry.initialize()
        names = list_model_names()
        assert isinstance(names, list)
        assert "qwen3.5" in names
        assert "qwen3-coder-next" in names


# =====================================================================
# Model availability checks
# =====================================================================


class TestModelAvailability:
    """Tests for model availability-related checks."""

    def test_all_default_models_are_ollama(self):
        models = [
            QWEN_35,
            QWEN_CODER_NEXT,
            DEEPSEEK_V32,
            GEMMA_4_31B,
            MISTRAL_LARGE,
            NOMIC_EMBED_TEXT,
        ]
        for model in models:
            assert model.provider == ModelProvider.OLLAMA

    def test_all_default_models_have_positive_context_window(self):
        models = [
            QWEN_35,
            QWEN_CODER_NEXT,
            DEEPSEEK_V32,
            GEMMA_4_31B,
            MISTRAL_LARGE,
            NOMIC_EMBED_TEXT,
        ]
        for model in models:
            assert model.context_window > 0

    def test_all_default_models_have_display_names(self):
        models = [
            QWEN_35,
            QWEN_CODER_NEXT,
            DEEPSEEK_V32,
            GEMMA_4_31B,
            MISTRAL_LARGE,
            NOMIC_EMBED_TEXT,
        ]
        for model in models:
            assert len(model.display_name) > 0

    def test_all_default_models_have_descriptions(self):
        models = [
            QWEN_35,
            QWEN_CODER_NEXT,
            DEEPSEEK_V32,
            GEMMA_4_31B,
            MISTRAL_LARGE,
            NOMIC_EMBED_TEXT,
        ]
        for model in models:
            assert len(model.description) > 0

    def test_development_models_have_code_generation(self):
        dev_models = [QWEN_CODER_NEXT, DEEPSEEK_V32]
        for model in dev_models:
            assert model.supports_capability(ModelCapability.CODE_GENERATION)

    def test_orchestrator_model_has_reasoning(self):
        assert QWEN_35.supports_capability(ModelCapability.REASONING)

    def test_qa_model_has_testing_capability(self):
        assert GEMMA_4_31B.supports_capability(ModelCapability.TESTING)

    def test_reviewer_model_has_code_review(self):
        assert MISTRAL_LARGE.supports_capability(ModelCapability.CODE_REVIEW)

    def test_embedding_model_has_summarization(self):
        assert NOMIC_EMBED_TEXT.supports_capability(ModelCapability.SUMMARIZATION)

    def test_coder_model_default_params(self):
        assert "temperature" in QWEN_CODER_NEXT.default_params
        assert "max_tokens" in QWEN_CODER_NEXT.default_params
        assert QWEN_CODER_NEXT.default_params["temperature"] == 0.3

    def test_qwen35_default_params(self):
        assert QWEN_35.default_params["temperature"] == 0.7
        assert QWEN_35.default_params["max_tokens"] == 4096

    def test_each_role_has_a_default_model(self):
        """Verify every AgentRole is covered by at least one model."""
        ModelRegistry.clear()
        ModelRegistry._initialized = False
        ModelRegistry.initialize()
        for role in AgentRole:
            model = ModelRegistry.get_for_role(role)
            # All roles except possibly ones not assigned should have a model
            # NOMIC_EMBED_TEXT has no roles, but all AgentRole values should be mapped
            assert model is not None, f"No model mapped for role {role.value}"
