"""Patrones de resiliencia para el Palace Framework.

Este módulo implementa lógica de reintentos, disyuntores de circuito
y mecanismos de fallback para llamadas a LLM y otros servicios externos,
proporcionando tolerancia a fallos y recuperación automática.

Parte del Módulo 11 - Refinement.
"""

import asyncio
import random
from collections.abc import Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar

import structlog

T = TypeVar("T")

logger = structlog.get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    """Circuit is closed, requests flow normally."""

    OPEN = "open"
    """Circuit is open, requests are rejected."""

    HALF_OPEN = "half_open"
    """Circuit is testing if service is back."""


@dataclass
class RetryConfig:
    """Configuration for retry with backoff strategy."""

    max_retries: int = 3
    """Maximum number of retry attempts."""

    base_delay_seconds: float = 1.0
    """Base delay in seconds before the first retry."""

    max_delay_seconds: float = 60.0
    """Maximum delay in seconds between retries."""

    exponential_base: float = 2.0
    """Base for exponential backoff calculation."""

    jitter: bool = True
    """Add random jitter to delay to prevent thundering herd."""

    retryable_exceptions: List[type] = field(default_factory=lambda: [Exception])
    """List of exception types that should trigger a retry."""


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5
    """Number of failures before opening the circuit."""

    recovery_timeout_seconds: float = 30.0
    """Time to wait before trying half-open state."""

    success_threshold: int = 3
    """Number of successes in half-open to close the circuit."""

    half_open_max_calls: int = 1
    """Max calls allowed in half-open state."""


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is open."""

    def __init__(self, circuit_name: str):
        self.circuit_name = circuit_name
        super().__init__(f"Circuit breaker '{circuit_name}' is open")


class RetryWithBackoff:
    """Retry with exponential backoff and jitter.

    Implements a configurable retry strategy with exponential
    backoff and optional jitter to prevent thundering herd.
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """Initialize the retry strategy.

        Args:
            config: Retry configuration. Uses defaults if not provided.
        """
        self._config = config or RetryConfig()

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate the delay for a given attempt.

        Args:
            attempt: The current attempt number (0-based).

        Returns:
            The delay in seconds.
        """
        delay = self._config.base_delay_seconds * (self._config.exponential_base**attempt)
        if self._config.jitter:
            delay += random.uniform(0, self._config.base_delay_seconds)
        return min(delay, self._config.max_delay_seconds)

    def _is_retryable(self, exception: Exception) -> bool:
        """Check if an exception is retryable.

        Args:
            exception: The exception to check.

        Returns:
            True if the exception should trigger a retry.
        """
        return isinstance(exception, tuple(self._config.retryable_exceptions))

    async def execute(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """Execute the async function with retry logic.

        On exception, checks if it's retryable. If retryable and retries
        remaining, waits with backoff and retries. If not retryable or
        max retries exceeded, raises the exception.

        Args:
            func: The async function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            The result of the function call.

        Raises:
            Exception: The last exception if all retries are exhausted
                or the exception is not retryable.
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self._config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                last_exception = exc

                if not self._is_retryable(exc):
                    logger.warning(
                        "Non-retryable exception encountered",
                        attempt=attempt,
                        exception_type=type(exc).__name__,
                        exception_message=str(exc),
                    )
                    raise

                if attempt >= self._config.max_retries:
                    logger.error(
                        "Max retries exceeded",
                        max_retries=self._config.max_retries,
                        exception_type=type(exc).__name__,
                        exception_message=str(exc),
                    )
                    raise

                delay = self._calculate_delay(attempt)
                logger.warning(
                    "Retrying after exception",
                    attempt=attempt + 1,
                    max_retries=self._config.max_retries,
                    delay_seconds=round(delay, 3),
                    exception_type=type(exc).__name__,
                    exception_message=str(exc),
                )
                await asyncio.sleep(delay)

        # This should not be reached, but just in case
        if last_exception is not None:
            raise last_exception
        raise RuntimeError("Retry loop exited without a result or exception")


class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures.

    Implements the circuit breaker pattern to prevent repeated
    calls to failing services, allowing them time to recover.
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """Initialize the circuit breaker.

        Args:
            name: A descriptive name for this circuit breaker.
            config: Circuit breaker configuration. Uses defaults if not provided.
        """
        self._name = name
        self._config = config or CircuitBreakerConfig()
        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls: int = 0

    async def call(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """Execute the function with circuit breaker protection.

        If CLOSED: calls the function, resets failure count on success,
        increments on failure.
        If OPEN: raises CircuitOpenError if recovery timeout hasn't passed,
        otherwise transitions to HALF_OPEN and tries the call.
        If HALF_OPEN: allows limited calls, increments success count on
        success (closing circuit if threshold met), re-opens on failure.

        Args:
            func: The async function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            The result of the function call.

        Raises:
            CircuitOpenError: If the circuit is open and recovery
                timeout has not passed.
        """
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(
                    "Circuit breaker transitioning to half-open",
                    circuit_name=self._name,
                )
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self._success_count = 0
            else:
                logger.warning(
                    "Circuit breaker is open, rejecting call",
                    circuit_name=self._name,
                )
                raise CircuitOpenError(self._name)

        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self._config.half_open_max_calls:
                logger.warning(
                    "Circuit breaker half-open call limit reached, rejecting call",
                    circuit_name=self._name,
                    half_open_calls=self._half_open_calls,
                    max_calls=self._config.half_open_max_calls,
                )
                raise CircuitOpenError(self._name)
            self._half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt a reset.

        Returns:
            True if the recovery timeout has passed since the last failure.
        """
        if self._last_failure_time is None:
            return True
        timeout = timedelta(seconds=self._config.recovery_timeout_seconds)
        return datetime.now() >= self._last_failure_time + timeout

    def _on_success(self) -> None:
        """Handle a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            logger.info(
                "Circuit breaker half-open call succeeded",
                circuit_name=self._name,
                success_count=self._success_count,
                success_threshold=self._config.success_threshold,
            )
            if self._success_count >= self._config.success_threshold:
                logger.info(
                    "Circuit breaker closing after successful recovery",
                    circuit_name=self._name,
                )
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                self._half_open_calls = 0
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def _on_failure(self) -> None:
        """Handle a failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._state == CircuitState.HALF_OPEN:
            logger.warning(
                "Circuit breaker re-opening after half-open failure",
                circuit_name=self._name,
            )
            self._state = CircuitState.OPEN
            self._half_open_calls = 0
            self._success_count = 0
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self._config.failure_threshold:
                logger.warning(
                    "Circuit breaker opening due to failure threshold",
                    circuit_name=self._name,
                    failure_count=self._failure_count,
                    failure_threshold=self._config.failure_threshold,
                )
                self._state = CircuitState.OPEN

    def is_available(self) -> bool:
        """Check if the circuit allows calls.

        CLOSED → True, OPEN → check recovery timeout, HALF_OPEN → True
        (if under call limit).

        Returns:
            True if the circuit breaker allows calls.
        """
        if self._state == CircuitState.CLOSED:
            return True
        elif self._state == CircuitState.OPEN:
            return self._should_attempt_reset()
        elif self._state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self._config.half_open_max_calls
        return False

    def get_state(self) -> CircuitState:
        """Return the current circuit state.

        Returns:
            The current CircuitState.
        """
        return self._state

    def get_stats(self) -> Dict[str, Any]:
        """Return circuit statistics.

        Returns:
            A dictionary containing state, failure_count, success_count,
            and last_failure_time.
        """
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": (
                self._last_failure_time.isoformat() if self._last_failure_time else None
            ),
        }

    def reset(self) -> None:
        """Reset the circuit to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0
        logger.info(
            "Circuit breaker reset to closed",
            circuit_name=self._name,
        )

    def force_open(self) -> None:
        """Force the circuit to OPEN state."""
        self._state = CircuitState.OPEN
        self._last_failure_time = datetime.now()
        logger.warning(
            "Circuit breaker forced open",
            circuit_name=self._name,
        )

    def force_close(self) -> None:
        """Force the circuit to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        logger.info(
            "Circuit breaker forced closed",
            circuit_name=self._name,
        )


class ModelFallback:
    """Fallback strategy for LLM models.

    When the primary model is unavailable, falls back to
    alternative models in priority order.
    """

    def __init__(self, primary_model: str, fallback_models: Optional[List[str]] = None):
        """Initialize the model fallback strategy.

        Args:
            primary_model: The primary model to use.
            fallback_models: List of fallback models in priority order.
        """
        self._primary_model = primary_model
        self._fallback_models: List[str] = list(fallback_models or [])

    def get_model(self, excluded: Optional[List[str]] = None) -> str:
        """Get the best available model.

        Tries primary first, then fallbacks in order. Skips any models
        in the excluded list. If all models are excluded, returns primary
        anyway.

        Args:
            excluded: List of model names to exclude.

        Returns:
            The name of the best available model.
        """
        excluded_set = set(excluded or [])

        if self._primary_model not in excluded_set:
            return self._primary_model

        for model in self._fallback_models:
            if model not in excluded_set:
                return model

        logger.warning(
            "All models excluded, returning primary",
            primary_model=self._primary_model,
            excluded=excluded,
        )
        return self._primary_model

    def add_fallback(self, model: str, position: int = -1) -> None:
        """Add a fallback model at the given position.

        Args:
            model: The model name to add.
            position: The position in the fallback list. -1 appends.
        """
        if position == -1:
            self._fallback_models.append(model)
        else:
            self._fallback_models.insert(position, model)
        logger.info(
            "Added fallback model",
            model=model,
            position=position,
            fallback_chain=self._fallback_models,
        )

    def remove_fallback(self, model: str) -> None:
        """Remove a fallback model.

        Args:
            model: The model name to remove.
        """
        if model in self._fallback_models:
            self._fallback_models.remove(model)
            logger.info(
                "Removed fallback model",
                model=model,
                fallback_chain=self._fallback_models,
            )
        else:
            logger.warning(
                "Attempted to remove non-existent fallback model",
                model=model,
                fallback_chain=self._fallback_models,
            )

    def get_model_chain(self) -> List[str]:
        """Return the full model chain.

        Returns:
            A list containing the primary model followed by all fallbacks.
        """
        return [self._primary_model] + list(self._fallback_models)


# Global retry instance
_default_retry = RetryWithBackoff()


async def retry(func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
    """Convenience function for retrying async calls.

    Uses the default RetryWithBackoff instance.

    Args:
        func: The async function to execute with retries.
        *args: Positional arguments for the function.
        **kwargs: Keyword arguments for the function.

    Returns:
        The result of the function call.
    """
    return await _default_retry.execute(func, *args, **kwargs)
