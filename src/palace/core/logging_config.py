"""
Configuración de logging estructurado para el Palace Framework.

Este módulo configura logging estructurado JSON para producción y
logging legible para humanos en desarrollo. Proporciona utilidades
para gestión de contexto, IDs de correlación y logging de rendimiento.
"""

import logging
import sys
import time
import uuid
from contextlib import contextmanager
from enum import Enum
from typing import Any, Dict, Optional

import structlog
from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    """Enumeration of available log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggingConfig(BaseModel):
    """Configuration model for structured logging."""

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(
        default="json",
        description='"json" for production, "console" for development',
    )
    include_timestamp: bool = Field(default=True, description="Include timestamp in logs")
    include_caller: bool = Field(default=False, description="Include caller info in logs")
    include_process: bool = Field(default=False, description="Include process info in logs")
    correlation_id_header: str = Field(
        default="X-Correlation-ID",
        description="Header for correlation ID",
    )
    output_file: Optional[str] = Field(
        default=None,
        description="Optional file to write logs to",
    )
    max_file_size_mb: float = Field(default=10.0, description="Max log file size in MB")
    backup_count: int = Field(default=5, description="Number of backup log files to keep")


def configure_logging(config: Optional[LoggingConfig] = None) -> None:
    """Main logging configuration function.

    Configures structlog with the appropriate processors based on the
    provided configuration. If no configuration is provided, a default
    LoggingConfig is used.

    Args:
        config: Optional LoggingConfig instance. If None, defaults are used.
    """
    if config is None:
        config = LoggingConfig()

    # Build the shared processors list
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
    ]

    if config.include_timestamp:
        shared_processors.append(structlog.processors.TimeStamper(fmt="iso"))

    shared_processors.extend(
        [
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ]
    )

    if config.include_caller:
        shared_processors.append(structlog.stdlib.add_log_level)

    if config.include_process:
        shared_processors.append(structlog.processors.ProcessRenderer())

    # Determine the renderer based on format
    if config.format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure the renderer for the standard library formatter
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    # Configure standard library logging
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicate logs
    root_logger.handlers.clear()

    # Set up stream handler (stdout)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # Set up file handler if output_file is specified
    if config.output_file:
        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler(
            config.output_file,
            maxBytes=int(config.max_file_size_mb * 1024 * 1024),
            backupCount=config.backup_count,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str = "palace") -> structlog.stdlib.BoundLogger:
    """Get a structured logger bound with the given name.

    Args:
        name: The name to bind to the logger. Defaults to "palace".

    Returns:
        A structlog BoundLogger instance.
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Bind key-value pairs to the logging context.

    Args:
        **kwargs: Key-value pairs to bind to the context.
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    """Unbind keys from the logging context.

    Args:
        *keys: Keys to unbind from the context.
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """Clear all context variables."""
    structlog.contextvars.clear_contextvars()


def get_context() -> Dict[str, Any]:
    """Return the current context variables.

    Returns:
        Dictionary of current context variables.
    """
    return structlog.contextvars.get_contextvars()


def new_correlation_id() -> str:
    """Generate a new correlation ID.

    Returns:
        A new UUID-based correlation ID string.
    """
    return str(uuid.uuid4())


def set_correlation_id(corr_id: Optional[str] = None) -> str:
    """Set the correlation ID in the logging context.

    If no ID provided, generates a new one.

    Args:
        corr_id: Optional correlation ID string. If None, a new one is generated.

    Returns:
        The correlation ID that was set.
    """
    cid = corr_id or new_correlation_id()
    bind_context(correlation_id=cid)
    return cid


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context.

    Returns:
        The current correlation ID, or None if not set.
    """
    ctx = get_context()
    return ctx.get("correlation_id")


@contextmanager
def log_performance(operation: str, **kwargs: Any):
    """Context manager to log operation performance.

    Usage:
        with log_performance("agent_execution", agent="backend"):
            result = await agent.run(task, context, memory)

    Args:
        operation: Name of the operation being measured.
        **kwargs: Additional key-value pairs to include in log entries.
    """
    logger = get_logger("palace.performance")
    start_time = time.time()
    logger.info("operation_started", operation=operation, **kwargs)
    try:
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "operation_completed",
            operation=operation,
            duration_ms=round(duration_ms, 2),
            **kwargs,
        )
