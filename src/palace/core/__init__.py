"""
Palace Core Module

This module contains the fundamental abstractions, types, and components
that form the foundation of the Palace framework. It defines the contracts
that all agents, memory systems, and pipelines must adhere to.

Components:
    - base: Abstract base classes for agents, tasks, and results
    - framework: Main framework entry point
    - orchestrator: Central coordinator for agent task routing
    - config: Configuration management and settings
    - exceptions: Custom exception hierarchy
    - types: Core type definitions and enums
    - costs: Cost tracking and budget management
    - resilience: Retry, circuit breaker, and fallback patterns
    - memory_quality: Memory quality assessment and cleanup
    - logging_config: Structured logging configuration
"""

# Base abstractions
from palace.core.base import (
    AgentBase,
    ResultBase,
    TaskBase,
    ToolBase,
)

# Configuration
from palace.core.config import (
    APIConfig,
    CLIConfig,
    DatabaseConfig,
    LoggingConfig,
    MemoryConfig,
    ModelConfig,
    OllamaConfig,
    ProjectsConfig,
    SecurityConfig,
    Settings,
    get_settings,
)

# Cost tracking
from palace.core.costs import CostBudget, CostTier, CostTracker, ModelPricing, UsageRecord

# Exceptions
from palace.core.exceptions import (
    AgentExecutionError,
    AgentNotFoundError,
    APIError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    ContextError,
    ContextRetrievalError,
    EmbeddingError,
    InvalidConfigError,
    MemoryRetrievalError,
    MemoryStoreError,
    MissingConfigError,
    ModelError,
    ModelNotAvailableError,
    ModelResponseError,
    OrchestratorError,
    PalaceError,
    PalaceMemoryError,
    PipelineError,
    PipelineExecutionError,
    PipelineNotFoundError,
    ProjectNotFoundError,
    RateLimitError,
    SessionNotFoundError,
    TaskExecutionError,
    TaskRoutingError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolTimeoutError,
    WorkflowError,
)

# Framework entry point
from palace.core.framework import ExecutionResult, PalaceFramework, ProjectStatus
from palace.core.logging_config import (
    LoggingConfig as LoggingConfigModule,
)

# Logging configuration
from palace.core.logging_config import (
    LogLevel,
    bind_context,
    clear_context,
    configure_logging,
    get_context,
    get_correlation_id,
    get_logger,
    log_performance,
    new_correlation_id,
    set_correlation_id,
    unbind_context,
)

# Memory quality
from palace.core.memory_quality import (
    CleanupPolicy,
    MemoryCleanupTask,
    MemoryQualityChecker,
    QualityScore,
)

# Resilience patterns
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

# Types and enums
from palace.core.types import (
    AgentCapability,
    AgentConfig,
    AgentResult,
    AgentRole,
    MemoryEntry,
    MemoryType,
    Message,
    MessageType,
    ProjectConfig,
    ProjectContext,
    SessionContext,
    TaskDefinition,
    TaskPriority,
    TaskResult,
    TaskStatus,
)
from palace.core.types import (
    ModelConfig as TypesModelConfig,
)

__all__ = [
    # Base classes
    "AgentBase",
    "TaskBase",
    "ResultBase",
    "ToolBase",
    # Framework
    "PalaceFramework",
    "ExecutionResult",
    "ProjectStatus",
    # Configuration
    "Settings",
    "get_settings",
    "OllamaConfig",
    "ModelConfig",
    "MemoryConfig",
    "APIConfig",
    "CLIConfig",
    "LoggingConfig",
    "DatabaseConfig",
    "ProjectsConfig",
    "SecurityConfig",
    # Exceptions
    "PalaceError",
    "ConfigurationError",
    "MissingConfigError",
    "InvalidConfigError",
    "AgentNotFoundError",
    "AgentExecutionError",
    "OrchestratorError",
    "TaskExecutionError",
    "TaskRoutingError",
    "WorkflowError",
    "PalaceMemoryError",
    "MemoryStoreError",
    "MemoryRetrievalError",
    "EmbeddingError",
    "ContextError",
    "ProjectNotFoundError",
    "SessionNotFoundError",
    "ContextRetrievalError",
    "ToolError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "ToolTimeoutError",
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitError",
    "PipelineError",
    "PipelineNotFoundError",
    "PipelineExecutionError",
    "ModelError",
    "ModelNotAvailableError",
    "ModelResponseError",
    # Types
    "AgentCapability",
    "AgentRole",
    "AgentConfig",
    "AgentResult",
    "MemoryType",
    "MessageType",
    "Message",
    "MemoryEntry",
    "ProjectConfig",
    "ProjectContext",
    "SessionContext",
    "TaskDefinition",
    "TaskPriority",
    "TaskStatus",
    "TaskResult",
    "ModelConfig",
    # Cost tracking
    "CostTracker",
    "CostTier",
    "ModelPricing",
    "UsageRecord",
    "CostBudget",
    # Resilience
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitOpenError",
    "CircuitState",
    "ModelFallback",
    "RetryConfig",
    "RetryWithBackoff",
    "retry",
    # Memory quality
    "QualityScore",
    "CleanupPolicy",
    "MemoryQualityChecker",
    "MemoryCleanupTask",
    # Logging
    "LogLevel",
    "configure_logging",
    "get_logger",
    "bind_context",
    "unbind_context",
    "clear_context",
    "get_context",
    "new_correlation_id",
    "set_correlation_id",
    "get_correlation_id",
    "log_performance",
]
