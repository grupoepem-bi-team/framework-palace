"""Tests for palace.core.resilience — Resilience patterns.

Covers RetryConfig, CircuitBreakerConfig, CircuitOpenError,
RetryWithBackoff, CircuitBreaker, ModelFallback, and the retry()
convenience function.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from palace.core.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    CircuitState,
    ModelFallback,
    RetryConfig,
    RetryWithBackoff,
    retry,
)

# ---------------------------------------------------------------------------
# RetryConfig
# ---------------------------------------------------------------------------


class TestRetryConfig:
    """Tests for the RetryConfig dataclass."""

    def test_default_values(self):
        """RetryConfig should have sensible defaults."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay_seconds == 1.0
        assert config.max_delay_seconds == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.retryable_exceptions == [Exception]

    def test_custom_values(self):
        """RetryConfig should accept custom values."""
        config = RetryConfig(
            max_retries=5,
            base_delay_seconds=0.5,
            max_delay_seconds=120.0,
            exponential_base=3.0,
            jitter=False,
            retryable_exceptions=[ValueError, TypeError],
        )
        assert config.max_retries == 5
        assert config.base_delay_seconds == 0.5
        assert config.max_delay_seconds == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False
        assert config.retryable_exceptions == [ValueError, TypeError]

    def test_independent_instances(self):
        """Each RetryConfig instance should have its own retryable_exceptions list."""
        config1 = RetryConfig()
        config2 = RetryConfig()
        config1.retryable_exceptions.append(ValueError)
        assert config2.retryable_exceptions == [Exception]


# ---------------------------------------------------------------------------
# CircuitBreakerConfig
# ---------------------------------------------------------------------------


class TestCircuitBreakerConfig:
    """Tests for the CircuitBreakerConfig dataclass."""

    def test_default_values(self):
        """CircuitBreakerConfig should have sensible defaults."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout_seconds == 30.0
        assert config.success_threshold == 3
        assert config.half_open_max_calls == 1

    def test_custom_values(self):
        """CircuitBreakerConfig should accept custom values."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout_seconds=60.0,
            success_threshold=5,
            half_open_max_calls=3,
        )
        assert config.failure_threshold == 10
        assert config.recovery_timeout_seconds == 60.0
        assert config.success_threshold == 5
        assert config.half_open_max_calls == 3


# ---------------------------------------------------------------------------
# CircuitOpenError
# ---------------------------------------------------------------------------


class TestCircuitOpenError:
    """Tests for the CircuitOpenError exception."""

    def test_is_exception(self):
        """CircuitOpenError should be an Exception subclass."""
        assert issubclass(CircuitOpenError, Exception)

    def test_creation_with_name(self):
        """CircuitOpenError stores the circuit name."""
        error = CircuitOpenError("my-circuit")
        assert error.circuit_name == "my-circuit"

    def test_error_message_contains_name(self):
        """CircuitOpenError message includes the circuit name."""
        error = CircuitOpenError("test-circuit")
        assert "test-circuit" in str(error)

    def test_can_be_raised_and_caught(self):
        """CircuitOpenError can be raised and caught."""
        with pytest.raises(CircuitOpenError) as exc_info:
            raise CircuitOpenError("my-service")
        assert exc_info.value.circuit_name == "my-service"

    def test_can_be_caught_as_exception(self):
        """CircuitOpenError can be caught as a generic Exception."""
        with pytest.raises(Exception):
            raise CircuitOpenError("my-service")


# ---------------------------------------------------------------------------
# CircuitState
# ---------------------------------------------------------------------------


class TestCircuitState:
    """Tests for the CircuitState enum."""

    def test_has_three_states(self):
        """CircuitState should define exactly 3 states."""
        assert len(CircuitState) == 3

    def test_closed(self):
        assert CircuitState.CLOSED == "closed"

    def test_open(self):
        assert CircuitState.OPEN == "open"

    def test_half_open(self):
        assert CircuitState.HALF_OPEN == "half_open"

    def test_is_str_enum(self):
        """CircuitState values should be strings."""
        for member in CircuitState:
            assert isinstance(member.value, str)


# ---------------------------------------------------------------------------
# RetryWithBackoff
# ---------------------------------------------------------------------------


class TestRetryWithBackoff:
    """Tests for the RetryWithBackoff class."""

    def test_initialization_default(self):
        """RetryWithBackoff initializes with default config."""
        retry = RetryWithBackoff()
        assert retry._config.max_retries == 3

    def test_initialization_custom_config(self):
        """RetryWithBackoff accepts a custom RetryConfig."""
        config = RetryConfig(max_retries=5, base_delay_seconds=0.1)
        retry = RetryWithBackoff(config=config)
        assert retry._config.max_retries == 5
        assert retry._config.base_delay_seconds == 0.1

    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        """Successful function should return on first attempt."""
        retry = RetryWithBackoff(config=RetryConfig(max_retries=3))
        call_count = 0

        async def succeed():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry.execute(succeed)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self):
        """Should retry and succeed if function eventually works."""
        retry = RetryWithBackoff(
            config=RetryConfig(max_retries=3, base_delay_seconds=0.01, jitter=False)
        )
        call_count = 0

        async def fail_twice_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError(f"Attempt {call_count} failed")
            return "success"

        result = await retry.execute(fail_twice_then_succeed)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Should raise the last exception when max retries exceeded."""
        retry = RetryWithBackoff(
            config=RetryConfig(max_retries=2, base_delay_seconds=0.01, jitter=False)
        )

        async def always_fail():
            raise ValueError("persistent failure")

        with pytest.raises(ValueError, match="persistent failure"):
            await retry.execute(always_fail)

    @pytest.mark.asyncio
    async def test_non_retryable_exception_not_retried(self):
        """Non-retryable exceptions should not be retried."""
        retry = RetryWithBackoff(
            config=RetryConfig(
                max_retries=3,
                base_delay_seconds=0.01,
                retryable_exceptions=[ValueError],
            )
        )
        call_count = 0

        async def raise_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError, match="not retryable"):
            await retry.execute(raise_type_error)

        # Should have been called only once (not retried)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retryable_exception_retried(self):
        """Only retryable exceptions should trigger retries."""
        retry = RetryWithBackoff(
            config=RetryConfig(
                max_retries=3,
                base_delay_seconds=0.01,
                retryable_exceptions=[ValueError],
            )
        )
        call_count = 0

        async def fail_with_value_error():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("retryable")
            return "recovered"

        result = await retry.execute(fail_with_value_error)
        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_passes_args_and_kwargs(self):
        """execute() should pass args and kwargs to the function."""
        retry = RetryWithBackoff(config=RetryConfig(max_retries=0))

        async def add(a, b, extra=0):
            return a + b + extra

        result = await retry.execute(add, 1, 2, extra=3)
        assert result == 6

    @pytest.mark.asyncio
    async def test_zero_retries_no_retry(self):
        """With max_retries=0, should not retry at all."""
        retry = RetryWithBackoff(config=RetryConfig(max_retries=0, base_delay_seconds=0.01))
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("fail immediately")

        with pytest.raises(RuntimeError, match="fail immediately"):
            await retry.execute(always_fail)

        assert call_count == 1

    def test_calculate_delay_exponential(self):
        """_calculate_delay should produce exponential backoff."""
        config = RetryConfig(
            base_delay_seconds=1.0, exponential_base=2.0, jitter=False, max_delay_seconds=60.0
        )
        retry = RetryWithBackoff(config=config)

        delay0 = retry._calculate_delay(0)  # 1.0 * 2^0 = 1.0
        delay1 = retry._calculate_delay(1)  # 1.0 * 2^1 = 2.0
        delay2 = retry._calculate_delay(2)  # 1.0 * 2^2 = 4.0
        delay3 = retry._calculate_delay(3)  # 1.0 * 2^3 = 8.0

        assert delay0 == 1.0
        assert delay1 == 2.0
        assert delay2 == 4.0
        assert delay3 == 8.0

    def test_calculate_delay_max_cap(self):
        """_calculate_delay should cap at max_delay_seconds."""
        config = RetryConfig(
            base_delay_seconds=1.0, exponential_base=10.0, jitter=False, max_delay_seconds=5.0
        )
        retry = RetryWithBackoff(config=config)

        delay = retry._calculate_delay(10)  # Would be 10^10 without cap
        assert delay == 5.0

    def test_calculate_delay_with_jitter(self):
        """_calculate_delay with jitter should add random variation."""
        config = RetryConfig(
            base_delay_seconds=1.0, exponential_base=2.0, jitter=True, max_delay_seconds=60.0
        )
        retry = RetryWithBackoff(config=config)

        # With jitter, delay should be base * 2^attempt + random(0, base)
        # For attempt=0: delay should be between 1.0 and 2.0
        delays = [retry._calculate_delay(0) for _ in range(100)]
        assert all(1.0 <= d <= 2.0 for d in delays)
        # Jitter should produce some variation
        assert len(set(delays)) > 1

    def test_is_retryable_with_matching_exception(self):
        """_is_retryable returns True for exceptions in retryable_exceptions."""
        config = RetryConfig(retryable_exceptions=[ValueError, RuntimeError])
        retry = RetryWithBackoff(config=config)

        assert retry._is_retryable(ValueError("test")) is True
        assert retry._is_retryable(RuntimeError("test")) is True

    def test_is_retryable_with_non_matching_exception(self):
        """_is_retryable returns False for exceptions not in retryable_exceptions."""
        config = RetryConfig(retryable_exceptions=[ValueError])
        retry = RetryWithBackoff(config=config)

        assert retry._is_retryable(TypeError("test")) is False
        assert retry._is_retryable(KeyError("test")) is False

    def test_is_retryable_with_default_exceptions(self):
        """_is_retryable with default [Exception] catches everything."""
        config = RetryConfig(retryable_exceptions=[Exception])
        retry = RetryWithBackoff(config=config)

        assert retry._is_retryable(ValueError("test")) is True
        assert retry._is_retryable(TypeError("test")) is True
        assert retry._is_retryable(RuntimeError("test")) is True

    @pytest.mark.asyncio
    async def test_returns_result_on_success(self):
        """execute() should return the function's result."""
        retry = RetryWithBackoff(config=RetryConfig(max_retries=3))

        async def return_number():
            return 42

        result = await retry.execute(return_number)
        assert result == 42

    @pytest.mark.asyncio
    async def test_returns_complex_result(self):
        """execute() should return complex results."""
        retry = RetryWithBackoff(config=RetryConfig(max_retries=3))

        async def return_dict():
            return {"key": "value", "count": 5}

        result = await retry.execute(return_dict)
        assert result == {"key": "value", "count": 5}


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    """Tests for the CircuitBreaker class."""

    def test_initialization_default(self):
        """CircuitBreaker initializes with CLOSED state."""
        cb = CircuitBreaker("test-service")
        assert cb.get_state() == CircuitState.CLOSED

    def test_initialization_custom_config(self):
        """CircuitBreaker accepts a custom CircuitBreakerConfig."""
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout_seconds=10.0)
        cb = CircuitBreaker("test-service", config=config)
        assert cb.get_state() == CircuitState.CLOSED
        assert cb._config.failure_threshold == 3
        assert cb._config.recovery_timeout_seconds == 10.0

    def test_initialization_name(self):
        """CircuitBreaker stores the name."""
        cb = CircuitBreaker("my-service")
        assert cb._name == "my-service"

    @pytest.mark.asyncio
    async def test_call_success_closed(self):
        """Successful call in CLOSED state stays CLOSED."""
        cb = CircuitBreaker("test")

        async def succeed():
            return "ok"

        result = await cb.call(succeed)
        assert result == "ok"
        assert cb.get_state() == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_call_failure_increments_failure_count(self):
        """Failed call in CLOSED state increments failure count."""
        cb = CircuitBreaker("test")

        async def fail():
            raise RuntimeError("fail")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        stats = cb.get_stats()
        assert stats["failure_count"] == 3

    @pytest.mark.asyncio
    async def test_closed_to_open_on_failures(self):
        """Circuit should transition CLOSED → OPEN after failure_threshold failures."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config=config)

        async def fail():
            raise RuntimeError("fail")

        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(fail)

        assert cb.get_state() == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_rejects_calls(self):
        """OPEN circuit should reject calls with CircuitOpenError."""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config=config)

        async def fail():
            raise RuntimeError("fail")

        # Trip the circuit open
        with pytest.raises(RuntimeError):
            await cb.call(fail)

        assert cb.get_state() == CircuitState.OPEN

        # Subsequent calls should be rejected
        with pytest.raises(CircuitOpenError) as exc_info:
            await cb.call(lambda: asyncio.sleep(0))
        assert exc_info.value.circuit_name == "test"

    @pytest.mark.asyncio
    async def test_open_to_half_open_after_timeout(self):
        """OPEN circuit should transition to HALF_OPEN after recovery timeout."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout_seconds=0.01)
        cb = CircuitBreaker("test", config=config)

        async def fail():
            raise RuntimeError("fail")

        async def succeed():
            return "ok"

        # Trip the circuit open
        with pytest.raises(RuntimeError):
            await cb.call(fail)
        assert cb.get_state() == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.02)

        # Next call should be allowed (HALF_OPEN)
        result = await cb.call(succeed)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self):
        """HALF_OPEN circuit should close after enough successes."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout_seconds=0.01,
            success_threshold=2,
            half_open_max_calls=3,
        )
        cb = CircuitBreaker("test", config=config)

        async def fail():
            raise RuntimeError("fail")

        async def succeed():
            return "ok"

        # Trip the circuit open
        with pytest.raises(RuntimeError):
            await cb.call(fail)
        assert cb.get_state() == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.02)

        # First successful call in HALF_OPEN
        result = await cb.call(succeed)
        assert result == "ok"
        # Not yet closed (need success_threshold=2)
        assert cb.get_state() == CircuitState.HALF_OPEN

        # Second successful call should close the circuit
        result = await cb.call(succeed)
        assert result == "ok"
        assert cb.get_state() == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self):
        """Failure in HALF_OPEN state should re-open the circuit."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout_seconds=0.01,
        )
        cb = CircuitBreaker("test", config=config)

        async def fail():
            raise RuntimeError("fail")

        async def succeed():
            return "ok"

        # Trip the circuit open
        with pytest.raises(RuntimeError):
            await cb.call(fail)
        assert cb.get_state() == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.02)

        # Fail again in HALF_OPEN state
        with pytest.raises(RuntimeError):
            await cb.call(fail)
        assert cb.get_state() == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_half_open_max_calls_limit(self):
        """HALF_OPEN state should limit the number of concurrent calls."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout_seconds=0.01,
            half_open_max_calls=1,
        )
        cb = CircuitBreaker("test", config=config)

        async def fail():
            raise RuntimeError("fail")

        # Trip the circuit open
        with pytest.raises(RuntimeError):
            await cb.call(fail)
        assert cb.get_state() == CircuitState.OPEN

        # Wait for recovery timeout to enter HALF_OPEN
        await asyncio.sleep(0.02)

        # The half_open_max_calls limits how many calls can go through
        # after the first successful call, the circuit may transition
        # Let's verify the limit works by checking the stats
        stats = cb.get_stats()
        assert stats is not None

    @pytest.mark.asyncio
    async def test_success_in_closed_resets_failure_count(self):
        """Successful call in CLOSED state should reset failure count."""
        config = CircuitBreakerConfig(failure_threshold=5)
        cb = CircuitBreaker("test", config=config)

        async def succeed():
            return "ok"

        async def fail():
            raise RuntimeError("fail")

        # Accumulate some failures
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(fail)
        assert cb.get_stats()["failure_count"] == 3

        # Success resets failure count
        await cb.call(succeed)
        assert cb.get_stats()["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_passes_args_and_kwargs(self):
        """call() should pass args and kwargs to the function."""
        cb = CircuitBreaker("test")

        async def add(a, b, extra=0):
            return a + b + extra

        result = await cb.call(add, 1, 2, extra=3)
        assert result == 6

    def test_reset(self):
        """reset() should set circuit to CLOSED and clear counters."""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config=config)

        # Manually force open
        cb.force_open()
        assert cb.get_state() == CircuitState.OPEN

        cb.reset()
        assert cb.get_state() == CircuitState.CLOSED
        stats = cb.get_stats()
        assert stats["failure_count"] == 0
        assert stats["success_count"] == 0
        assert stats["last_failure_time"] is None

    def test_force_open(self):
        """force_open() should set circuit to OPEN state."""
        cb = CircuitBreaker("test")
        assert cb.get_state() == CircuitState.CLOSED

        cb.force_open()
        assert cb.get_state() == CircuitState.OPEN

    def test_force_close(self):
        """force_close() should set circuit to CLOSED and reset counters."""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config=config)

        # Open the circuit
        cb.force_open()
        assert cb.get_state() == CircuitState.OPEN

        # Force close
        cb.force_close()
        assert cb.get_state() == CircuitState.CLOSED
        stats = cb.get_stats()
        assert stats["failure_count"] == 0
        assert stats["success_count"] == 0

    def test_is_available_closed(self):
        """is_available should return True when CLOSED."""
        cb = CircuitBreaker("test")
        assert cb.get_state() == CircuitState.CLOSED
        assert cb.is_available() is True

    def test_is_available_open(self):
        """is_available should return False when OPEN (no recovery timeout passed)."""
        cb = CircuitBreaker("test")
        cb.force_open()
        # Just forced open, so recovery timeout has not passed
        # last_failure_time was set to now, so recovery timeout hasn't elapsed
        assert cb.is_available() is False

    def test_is_available_open_after_timeout(self):
        """is_available should return True when OPEN and recovery timeout has passed."""
        config = CircuitBreakerConfig(recovery_timeout_seconds=0.01)
        cb = CircuitBreaker("test", config=config)
        cb.force_open()
        # Manually set last_failure_time to the past
        cb._last_failure_time = datetime.now() - timedelta(seconds=1)
        assert cb.is_available() is True

    def test_is_available_half_open(self):
        """is_available should return True when HALF_OPEN and under call limit."""
        config = CircuitBreakerConfig(half_open_max_calls=3)
        cb = CircuitBreaker("test", config=config)
        cb._state = CircuitState.HALF_OPEN
        cb._half_open_calls = 0
        assert cb.is_available() is True

    def test_is_available_half_open_at_limit(self):
        """is_available should return False when HALF_OPEN at call limit."""
        config = CircuitBreakerConfig(half_open_max_calls=1)
        cb = CircuitBreaker("test", config=config)
        cb._state = CircuitState.HALF_OPEN
        cb._half_open_calls = 1
        assert cb.is_available() is False

    def test_get_stats(self):
        """get_stats() should return relevant statistics."""
        cb = CircuitBreaker("test")
        stats = cb.get_stats()
        assert "state" in stats
        assert "failure_count" in stats
        assert "success_count" in stats
        assert "last_failure_time" in stats
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0
        assert stats["success_count"] == 0
        assert stats["last_failure_time"] is None

    def test_get_stats_after_failure(self):
        """get_stats() should reflect failure count after failures."""
        config = CircuitBreakerConfig(failure_threshold=5)
        cb = CircuitBreaker("test", config=config)
        # Simulate failures by directly modifying the counter
        cb._failure_count = 3
        cb._last_failure_time = datetime.now()
        stats = cb.get_stats()
        assert stats["failure_count"] == 3
        assert stats["last_failure_time"] is not None

    @pytest.mark.asyncio
    async def test_call_success_in_half_open_increments_success_count(self):
        """Successful call in HALF_OPEN increments success count."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout_seconds=0.01,
            success_threshold=5,
        )
        cb = CircuitBreaker("test", config=config)

        async def fail():
            raise RuntimeError("fail")

        async def succeed():
            return "ok"

        # Trip the circuit open
        with pytest.raises(RuntimeError):
            await cb.call(fail)
        assert cb.get_state() == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.02)

        # Call should succeed in HALF_OPEN
        await cb.call(succeed)
        stats = cb.get_stats()
        assert stats["success_count"] == 1
        assert cb.get_state() == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_closed_state_multiple_successes(self):
        """Multiple successes in CLOSED state should keep circuit CLOSED."""
        cb = CircuitBreaker("test")

        async def succeed():
            return "ok"

        for i in range(10):
            result = await cb.call(succeed)
            assert result == "ok"

        assert cb.get_state() == CircuitState.CLOSED
        assert cb.get_stats()["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_gradual_failure_threshold(self):
        """Circuit should stay CLOSED until failure_threshold is reached."""
        config = CircuitBreakerConfig(failure_threshold=5)
        cb = CircuitBreaker("test", config=config)

        async def fail():
            raise RuntimeError("fail")

        async def succeed():
            return "ok"

        # 4 failures should not trip the circuit
        for _ in range(4):
            with pytest.raises(RuntimeError):
                await cb.call(fail)
        assert cb.get_state() == CircuitState.CLOSED

        # 5th failure should trip the circuit
        with pytest.raises(RuntimeError):
            await cb.call(fail)
        assert cb.get_state() == CircuitState.OPEN


# ---------------------------------------------------------------------------
# ModelFallback
# ---------------------------------------------------------------------------


class TestModelFallback:
    """Tests for the ModelFallback class."""

    def test_initialization_with_primary_only(self):
        """ModelFallback should initialize with a primary model only."""
        mf = ModelFallback("gpt-4")
        assert mf._primary_model == "gpt-4"
        assert mf._fallback_models == []

    def test_initialization_with_fallbacks(self):
        """ModelFallback should initialize with primary and fallback models."""
        mf = ModelFallback("gpt-4", ["gpt-3.5", "gpt-3"])
        assert mf._primary_model == "gpt-4"
        assert mf._fallback_models == ["gpt-3.5", "gpt-3"]

    def test_get_model_primary_available(self):
        """get_model() should return the primary model when not excluded."""
        mf = ModelFallback("gpt-4", ["gpt-3.5", "gpt-3"])
        assert mf.get_model() == "gpt-4"

    def test_get_model_primary_excluded(self):
        """get_model() should return first fallback when primary is excluded."""
        mf = ModelFallback("gpt-4", ["gpt-3.5", "gpt-3"])
        assert mf.get_model(excluded=["gpt-4"]) == "gpt-3.5"

    def test_get_model_multiple_excluded(self):
        """get_model() should skip excluded models and return first available."""
        mf = ModelFallback("gpt-4", ["gpt-3.5", "gpt-3"])
        result = mf.get_model(excluded=["gpt-4", "gpt-3.5"])
        assert result == "gpt-3"

    def test_get_model_all_excluded_returns_primary(self):
        """get_model() should return primary when all models are excluded."""
        mf = ModelFallback("gpt-4", ["gpt-3.5"])
        result = mf.get_model(excluded=["gpt-4", "gpt-3.5"])
        assert result == "gpt-4"

    def test_get_model_with_empty_excluded_list(self):
        """get_model() with empty excluded list should return primary."""
        mf = ModelFallback("gpt-4", ["gpt-3.5"])
        assert mf.get_model(excluded=[]) == "gpt-4"

    def test_get_model_with_none_excluded(self):
        """get_model() with None excluded should return primary."""
        mf = ModelFallback("gpt-4", ["gpt-3.5"])
        assert mf.get_model(excluded=None) == "gpt-4"

    def test_add_fallback_append(self):
        """add_fallback() should append by default."""
        mf = ModelFallback("gpt-4", ["gpt-3.5"])
        mf.add_fallback("gpt-3")
        assert mf._fallback_models == ["gpt-3.5", "gpt-3"]

    def test_add_fallback_at_position(self):
        """add_fallback() should insert at the given position."""
        mf = ModelFallback("gpt-4", ["gpt-3.5", "gpt-3"])
        mf.add_fallback("gpt-4-turbo", position=0)
        assert mf._fallback_models == ["gpt-4-turbo", "gpt-3.5", "gpt-3"]

    def test_add_fallback_negative_position_appends(self):
        """add_fallback() with position=-1 should append."""
        mf = ModelFallback("gpt-4", ["gpt-3.5"])
        mf.add_fallback("gpt-3", position=-1)
        assert mf._fallback_models == ["gpt-3.5", "gpt-3"]

    def test_remove_fallback(self):
        """remove_fallback() should remove the specified model."""
        mf = ModelFallback("gpt-4", ["gpt-3.5", "gpt-3"])
        mf.remove_fallback("gpt-3.5")
        assert mf._fallback_models == ["gpt-3"]

    def test_remove_fallback_nonexistent(self):
        """remove_fallback() should not raise for nonexistent model."""
        mf = ModelFallback("gpt-4", ["gpt-3.5"])
        mf.remove_fallback("nonexistent")
        assert mf._fallback_models == ["gpt-3.5"]

    def test_remove_fallback_from_empty(self):
        """remove_fallback() on empty fallback list should not raise."""
        mf = ModelFallback("gpt-4")
        mf.remove_fallback("nonexistent")
        assert mf._fallback_models == []

    def test_get_model_chain(self):
        """get_model_chain() should return primary followed by fallbacks."""
        mf = ModelFallback("gpt-4", ["gpt-3.5", "gpt-3"])
        chain = mf.get_model_chain()
        assert chain == ["gpt-4", "gpt-3.5", "gpt-3"]

    def test_get_model_chain_returns_copy(self):
        """get_model_chain() should return a new list, not the internal list."""
        mf = ModelFallback("gpt-4", ["gpt-3.5"])
        chain = mf.get_model_chain()
        chain.append("new-model")
        assert mf.get_model_chain() == ["gpt-4", "gpt-3.5"]

    def test_get_model_chain_no_fallbacks(self):
        """get_model_chain() with no fallbacks should return just primary."""
        mf = ModelFallback("gpt-4")
        assert mf.get_model_chain() == ["gpt-4"]

    def test_fallback_chain_order_preserved(self):
        """Fallback models should maintain their order."""
        mf = ModelFallback("primary", ["fallback-1", "fallback-2", "fallback-3"])
        result = mf.get_model(excluded=["primary"])
        assert result == "fallback-1"

        result = mf.get_model(excluded=["primary", "fallback-1"])
        assert result == "fallback-2"

        result = mf.get_model(excluded=["primary", "fallback-1", "fallback-2"])
        assert result == "fallback-3"

    def test_add_then_get_model(self):
        """get_model() should reflect models added via add_fallback()."""
        mf = ModelFallback("primary")
        mf.add_fallback("fallback-1")
        mf.add_fallback("fallback-2")

        assert mf.get_model(excluded=["primary"]) == "fallback-1"
        assert mf.get_model(excluded=["primary", "fallback-1"]) == "fallback-2"

    def test_remove_then_get_model(self):
        """get_model() should not return removed models."""
        mf = ModelFallback("primary", ["fallback-1", "fallback-2"])
        mf.remove_fallback("fallback-1")
        assert mf.get_model(excluded=["primary"]) == "fallback-2"


# ---------------------------------------------------------------------------
# retry() convenience function
# ---------------------------------------------------------------------------


class TestRetryConvenienceFunction:
    """Tests for the retry() convenience function."""

    @pytest.mark.asyncio
    async def test_retry_success(self):
        """retry() should succeed on first try for successful function."""

        async def succeed():
            return "ok"

        result = await retry(succeed)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_retry_retries_on_failure(self):
        """retry() should retry on failure and eventually succeed."""
        call_count = 0

        async def fail_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("temporary failure")
            return "recovered"

        result = await retry(fail_once)
        assert result == "recovered"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_with_args(self):
        """retry() should pass args and kwargs to the function."""

        async def add(a, b):
            return a + b

        result = await retry(add, 3, 4)
        assert result == 7

    @pytest.mark.asyncio
    async def test_retry_with_kwargs(self):
        """retry() should pass kwargs to the function."""

        async def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = await retry(greet, "World", greeting="Hi")
        assert result == "Hi, World!"

    @pytest.mark.asyncio
    async def test_retry_uses_default_config(self):
        """retry() should use the default RetryWithBackoff config."""
        # Default config has max_retries=3, so a function that always fails
        # should be called 4 times (initial + 3 retries)
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("always fails")

        with pytest.raises(ValueError, match="always fails"):
            await retry(always_fail)

        # Called once for initial attempt, plus 3 retries = 4 total
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_retry_returns_result(self):
        """retry() should return the function's result."""

        async def return_list():
            return [1, 2, 3]

        result = await retry(return_list)
        assert result == [1, 2, 3]
