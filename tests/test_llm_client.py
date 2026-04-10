"""
Tests for palace.llm.client — LLM client configuration and data classes.

Covers:
- InvocationStatus enum
- InvocationResult dataclass (creation, content property, to_dict)
- LLMClientConfig dataclass (default values, get_provider_config)
- LLMClient basic creation tests (with full mocking)

Note: The palace.llm.client module has broken upstream imports (ProviderConfig,
ModelInfo do not exist in palace.llm.base). We inject stubs before importing
so that the module can load successfully.
"""

import sys
import types
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
# import errors.  Direct submodule imports like palace.llm.base and
# palace.llm.client still work because the stub registers __path__.
_ensure_package("palace.llm", [str(_PALACE_LLM_PKG)])

# ---------------------------------------------------------------------------
# Inject missing names into palace.llm.base before palace.llm.client
# tries to import them.  The client module imports ProviderConfig and
# ModelInfo from palace.llm.base, but they are not defined there.
# ---------------------------------------------------------------------------
import palace.llm.base as _llm_base  # noqa: E402

if not hasattr(_llm_base, "ProviderConfig"):

    class _StubProviderConfig:
        """Minimal stub for ProviderConfig."""

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    _llm_base.ProviderConfig = _StubProviderConfig

if not hasattr(_llm_base, "ModelInfo"):

    class _StubModelInfo:
        """Minimal stub for ModelInfo."""

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    _llm_base.ModelInfo = _StubModelInfo

# ---------------------------------------------------------------------------
# palace.llm.client also imports CostTracker & PricingConfig from
# palace.llm.costs — provide stubs if the real module is unavailable.
# ---------------------------------------------------------------------------
try:
    from palace.llm.costs import CostTracker, PricingConfig  # noqa: F401
except ImportError:

    class _StubCostTracker:
        pass

    class _StubPricingConfig:
        pass

    _costs_mod = types.ModuleType("palace.llm.costs")
    _costs_mod.CostTracker = _StubCostTracker
    _costs_mod.PricingConfig = _StubPricingConfig
    _costs_mod.__path__ = [str(_PALACE_LLM_PKG / "costs")]
    _costs_mod.__package__ = "palace.llm.costs"
    sys.modules["palace.llm.costs"] = _costs_mod

# Stub ModelRole if missing from the router module
try:
    from palace.llm.router import ModelRole  # noqa: F401
except ImportError:
    import palace.llm.router as _router_mod

    if not hasattr(_router_mod, "ModelRole"):
        _router_mod.ModelRole = type("ModelRole", (), {})

# Finally, mock get_settings so the client module can load
_mock_settings = MagicMock()
if "palace.core.config" not in sys.modules:
    _config_mod = types.ModuleType("palace.core.config")
    _config_mod.get_settings = MagicMock(return_value=_mock_settings)
    _config_mod.__package__ = "palace.core"
    sys.modules["palace.core.config"] = _config_mod
else:
    sys.modules["palace.core.config"].get_settings = MagicMock(return_value=_mock_settings)

# ---------------------------------------------------------------------------
# Now safe to import the module under test
# ---------------------------------------------------------------------------
from palace.llm.base import LLMResponse  # noqa: E402
from palace.llm.client import (  # noqa: E402
    InvocationResult,
    InvocationStatus,
    LLMClient,
    LLMClientConfig,
)

# =====================================================================
# Helpers
# =====================================================================


def _make_llm_response(
    content="Test response content",
    model="test-model",
    provider="ollama",
):
    """Create a minimal LLMResponse for testing.

    LLMResponse is a Pydantic BaseModel that requires request_id,
    model, and provider fields. The provider must be a valid
    LLMProviderType enum value.
    """
    from palace.llm.base import LLMProviderType

    return LLMResponse(
        request_id="test-request-id",
        content=content,
        model=model,
        provider=LLMProviderType(provider),
    )


# =====================================================================
# InvocationStatus tests
# =====================================================================


class TestInvocationStatus:
    """Tests for the InvocationStatus enum."""

    def test_all_statuses_exist(self):
        expected = {"SUCCESS", "FAILED", "RETRY", "TIMEOUT", "CACHED", "RATE_LIMITED"}
        actual = {s.name for s in InvocationStatus}
        assert actual == expected

    def test_status_values(self):
        assert InvocationStatus.SUCCESS.value == "success"
        assert InvocationStatus.FAILED.value == "failed"
        assert InvocationStatus.RETRY.value == "retry"
        assert InvocationStatus.TIMEOUT.value == "timeout"
        assert InvocationStatus.CACHED.value == "cached"
        assert InvocationStatus.RATE_LIMITED.value == "rate_limited"

    def test_is_string_enum(self):
        assert isinstance(InvocationStatus.SUCCESS, str)

    def test_status_from_value(self):
        assert InvocationStatus("success") == InvocationStatus.SUCCESS
        assert InvocationStatus("failed") == InvocationStatus.FAILED
        assert InvocationStatus("timeout") == InvocationStatus.TIMEOUT

    def test_status_count(self):
        assert len(InvocationStatus) == 6


# =====================================================================
# InvocationResult tests
# =====================================================================


class TestInvocationResult:
    """Tests for the InvocationResult dataclass."""

    def _make_result(self, **overrides):
        defaults = dict(
            response=_make_llm_response(),
            status=InvocationStatus.SUCCESS,
            model="test-model",
            provider="ollama",
            role="backend",
            tokens_prompt=50,
            tokens_completion=100,
            tokens_total=150,
            cost=0.003,
            latency_seconds=1.5,
            timestamp=datetime.utcnow(),
        )
        defaults.update(overrides)
        return InvocationResult(**defaults)

    def test_creation_minimal(self):
        result = self._make_result()
        assert result.status == InvocationStatus.SUCCESS
        assert result.model == "test-model"
        assert result.provider == "ollama"
        assert result.role == "backend"
        assert result.tokens_prompt == 50
        assert result.tokens_completion == 100
        assert result.tokens_total == 150
        assert result.cost == 0.003
        assert result.latency_seconds == 1.5
        assert result.retry_count == 0  # default
        assert result.cached is False  # default
        assert result.metadata == {}  # default

    def test_creation_full(self):
        response = _make_llm_response(content="Full response", model="gpt-4")
        now = datetime.utcnow()
        result = InvocationResult(
            response=response,
            status=InvocationStatus.SUCCESS,
            model="gpt-4",
            provider="openai",
            role="reviewer",
            tokens_prompt=200,
            tokens_completion=500,
            tokens_total=700,
            cost=0.05,
            latency_seconds=3.2,
            timestamp=now,
            retry_count=2,
            cached=True,
            metadata={"source": "cache", "cache_key": "abc123"},
        )
        assert result.model == "gpt-4"
        assert result.provider == "openai"
        assert result.role == "reviewer"
        assert result.tokens_prompt == 200
        assert result.tokens_completion == 500
        assert result.tokens_total == 700
        assert result.cost == 0.05
        assert result.latency_seconds == 3.2
        assert result.timestamp == now
        assert result.retry_count == 2
        assert result.cached is True
        assert result.metadata["source"] == "cache"

    def test_content_property_returns_response_content(self):
        response = _make_llm_response(content="Hello from LLM!")
        result = self._make_result(response=response)
        assert result.content == "Hello from LLM!"

    def test_content_property_various_responses(self):
        for content in ["", "Short", "A" * 1000, "Multi\nline\nresponse"]:
            response = _make_llm_response(content=content)
            result = self._make_result(response=response)
            assert result.content == content

    def test_to_dict(self):
        now = datetime(2024, 6, 15, 12, 30, 45)
        result = InvocationResult(
            response=_make_llm_response(),
            status=InvocationStatus.SUCCESS,
            model="qwen3.5",
            provider="ollama",
            role="orchestrator",
            tokens_prompt=100,
            tokens_completion=200,
            tokens_total=300,
            cost=0.01,
            latency_seconds=2.5,
            timestamp=now,
            retry_count=0,
            cached=False,
        )
        d = result.to_dict()
        assert d["status"] == "success"
        assert d["model"] == "qwen3.5"
        assert d["provider"] == "ollama"
        assert d["role"] == "orchestrator"
        assert d["tokens_prompt"] == 100
        assert d["tokens_completion"] == 200
        assert d["tokens_total"] == 300
        assert d["cost"] == 0.01
        assert d["latency_seconds"] == 2.5
        assert isinstance(d["timestamp"], str)  # ISO format string
        assert d["retry_count"] == 0
        assert d["cached"] is False

    def test_to_dict_with_retry(self):
        result = self._make_result(
            status=InvocationStatus.RETRY,
            retry_count=3,
        )
        d = result.to_dict()
        assert d["status"] == "retry"
        assert d["retry_count"] == 3

    def test_to_dict_cached(self):
        result = self._make_result(
            status=InvocationStatus.CACHED,
            cached=True,
        )
        d = result.to_dict()
        assert d["status"] == "cached"
        assert d["cached"] is True

    def test_to_dict_failed(self):
        result = self._make_result(status=InvocationStatus.FAILED)
        d = result.to_dict()
        assert d["status"] == "failed"

    def test_to_dict_timeout(self):
        result = self._make_result(status=InvocationStatus.TIMEOUT)
        d = result.to_dict()
        assert d["status"] == "timeout"

    def test_to_dict_rate_limited(self):
        result = self._make_result(status=InvocationStatus.RATE_LIMITED)
        d = result.to_dict()
        assert d["status"] == "rate_limited"

    def test_role_can_be_none(self):
        result = self._make_result(role=None)
        assert result.role is None
        d = result.to_dict()
        assert d["role"] is None

    def test_metadata_default_empty(self):
        result = self._make_result()
        assert result.metadata == {}

    def test_metadata_custom(self):
        result = self._make_result(
            metadata={"latency_breakdown": {"llm": 1.0, "network": 0.5}},
        )
        assert "latency_breakdown" in result.metadata
        assert result.metadata["latency_breakdown"]["llm"] == 1.0

    def test_to_dict_timestamp_is_iso_format(self):
        now = datetime(2024, 6, 15, 12, 30, 45)
        result = self._make_result(timestamp=now)
        d = result.to_dict()
        assert "2024-06-15" in d["timestamp"]
        assert "12:30:45" in d["timestamp"]

    def test_to_dict_contains_all_keys(self):
        result = self._make_result()
        d = result.to_dict()
        expected_keys = {
            "status",
            "model",
            "provider",
            "role",
            "tokens_prompt",
            "tokens_completion",
            "tokens_total",
            "cost",
            "latency_seconds",
            "timestamp",
            "retry_count",
            "cached",
        }
        assert expected_keys.issubset(set(d.keys()))

    def test_all_statuses_in_to_dict(self):
        for status in InvocationStatus:
            result = self._make_result(status=status)
            d = result.to_dict()
            assert d["status"] == status.value


# =====================================================================
# InvocationResult edge cases
# =====================================================================


class TestInvocationResultEdgeCases:
    """Edge case tests for InvocationResult."""

    def _make_result(self, **overrides):
        defaults = dict(
            response=_make_llm_response(),
            status=InvocationStatus.SUCCESS,
            model="test-model",
            provider="ollama",
            role="backend",
            tokens_prompt=50,
            tokens_completion=100,
            tokens_total=150,
            cost=0.003,
            latency_seconds=1.5,
            timestamp=datetime.utcnow(),
        )
        defaults.update(overrides)
        return InvocationResult(**defaults)

    def test_zero_tokens(self):
        result = self._make_result(tokens_prompt=0, tokens_completion=0, tokens_total=0)
        assert result.tokens_prompt == 0
        assert result.tokens_completion == 0
        assert result.tokens_total == 0

    def test_zero_cost(self):
        result = self._make_result(cost=0.0)
        assert result.cost == 0.0

    def test_large_token_counts(self):
        result = self._make_result(
            tokens_prompt=50000,
            tokens_completion=25000,
            tokens_total=75000,
        )
        assert result.tokens_total == 75000

    def test_very_fast_latency(self):
        result = self._make_result(latency_seconds=0.001)
        assert result.latency_seconds == 0.001

    def test_very_slow_latency(self):
        result = self._make_result(latency_seconds=300.0)
        assert result.latency_seconds == 300.0


# =====================================================================
# LLMClientConfig tests
# =====================================================================


class TestLLMClientConfig:
    """Tests for the LLMClientConfig dataclass."""

    def test_default_values(self):
        config = LLMClientConfig()
        assert config.default_provider == "ollama"
        assert config.default_model == "qwen3-coder-next"
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.timeout == 300.0
        assert config.max_tokens_default == 4096
        assert config.temperature_default == 0.7
        assert config.enable_cost_tracking is True
        assert config.enable_caching is False
        assert config.cache_ttl == 3600
        assert config.providers == {}
        assert config.role_mappings == {}

    def test_custom_values(self):
        config = LLMClientConfig(
            default_provider="openai",
            default_model="gpt-4",
            max_retries=5,
            retry_delay=2.0,
            timeout=60.0,
            max_tokens_default=2048,
            temperature_default=0.3,
            enable_cost_tracking=False,
            enable_caching=True,
            cache_ttl=7200,
        )
        assert config.default_provider == "openai"
        assert config.default_model == "gpt-4"
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.timeout == 60.0
        assert config.max_tokens_default == 2048
        assert config.temperature_default == 0.3
        assert config.enable_cost_tracking is False
        assert config.enable_caching is True
        assert config.cache_ttl == 7200

    def test_get_provider_config_empty(self):
        config = LLMClientConfig()
        result = config.get_provider_config("ollama")
        assert result is None

    def test_get_provider_config_with_providers(self):
        mock_provider_config = MagicMock()
        config = LLMClientConfig(
            providers={"ollama": mock_provider_config},
        )
        result = config.get_provider_config("ollama")
        assert result is mock_provider_config

    def test_get_provider_config_nonexistent(self):
        mock_provider_config = MagicMock()
        config = LLMClientConfig(
            providers={"ollama": mock_provider_config},
        )
        result = config.get_provider_config("openai")
        assert result is None

    def test_role_mappings_default_empty(self):
        config = LLMClientConfig()
        assert config.role_mappings == {}

    def test_role_mappings_custom(self):
        config = LLMClientConfig(
            role_mappings={"backend": "qwen3-coder-next", "dba": "deepseek-v3.2"},
        )
        assert config.role_mappings["backend"] == "qwen3-coder-next"
        assert config.role_mappings["dba"] == "deepseek-v3.2"

    def test_providers_default_empty_dict(self):
        config = LLMClientConfig()
        assert isinstance(config.providers, dict)
        assert len(config.providers) == 0

    def test_with_multiple_providers(self):
        ollama_config = MagicMock(name="ollama_config")
        openai_config = MagicMock(name="openai_config")
        config = LLMClientConfig(
            providers={"ollama": ollama_config, "openai": openai_config},
        )
        assert config.get_provider_config("ollama") is ollama_config
        assert config.get_provider_config("openai") is openai_config
        assert config.get_provider_config("anthropic") is None

    def test_max_retries_zero(self):
        config = LLMClientConfig(max_retries=0)
        assert config.max_retries == 0

    def test_timeout_very_small(self):
        config = LLMClientConfig(timeout=0.1)
        assert config.timeout == 0.1

    def test_temperature_range(self):
        """Verify temperatures can be set across the valid range."""
        for temp in [0.0, 0.1, 0.5, 0.7, 1.0, 1.5, 2.0]:
            config = LLMClientConfig(temperature_default=temp)
            assert config.temperature_default == temp

    def test_max_tokens_variations(self):
        for tokens in [256, 1024, 2048, 4096, 8192, 16384, 32768]:
            config = LLMClientConfig(max_tokens_default=tokens)
            assert config.max_tokens_default == tokens


# =====================================================================
# LLMClient basic tests (creation only, no async provider calls)
# =====================================================================


class TestLLMClientCreation:
    """Tests for LLMClient initialization (no async, no provider calls)."""

    def test_client_creation_default_config(self):
        with patch("palace.llm.client.get_settings", return_value=_mock_settings):
            client = LLMClient()
            assert client._config.default_provider == "ollama"
            assert client._config.default_model == "qwen3-coder-next"
            assert client._initialized is False

    def test_client_creation_custom_config(self):
        config = LLMClientConfig(
            default_provider="openai",
            default_model="gpt-4",
            max_retries=5,
            timeout=60.0,
        )
        with patch("palace.llm.client.get_settings", return_value=_mock_settings):
            client = LLMClient(config=config)
            assert client._config.default_provider == "openai"
            assert client._config.default_model == "gpt-4"
            assert client._config.max_retries == 5
            assert client._config.timeout == 60.0

    def test_client_initial_state(self):
        with patch("palace.llm.client.get_settings", return_value=_mock_settings):
            client = LLMClient()
            assert client._initialized is False
            assert client._router is None
            assert client._providers == {}
            assert client._cache == {}

    def test_client_stats_initial(self):
        with patch("palace.llm.client.get_settings", return_value=_mock_settings):
            client = LLMClient()
            assert client._stats["total_invocations"] == 0
            assert client._stats["successful_invocations"] == 0
            assert client._stats["failed_invocations"] == 0
            assert client._stats["total_tokens"] == 0
            assert client._stats["total_cost"] == 0.0
            assert client._stats["total_latency"] == 0.0

    def test_client_with_settings_override(self):
        custom_settings = MagicMock()
        with patch("palace.llm.client.get_settings", return_value=_mock_settings):
            client = LLMClient(settings=custom_settings)
            assert client._settings is custom_settings

    def test_client_config_preserved(self):
        config = LLMClientConfig(
            enable_cost_tracking=False,
            enable_caching=True,
            cache_ttl=1800,
        )
        with patch("palace.llm.client.get_settings", return_value=_mock_settings):
            client = LLMClient(config=config)
            assert client._config.enable_cost_tracking is False
            assert client._config.enable_caching is True
            assert client._config.cache_ttl == 1800

    def test_client_cache_initially_empty(self):
        with patch("palace.llm.client.get_settings", return_value=_mock_settings):
            client = LLMClient()
            assert isinstance(client._cache, dict)
            assert len(client._cache) == 0
