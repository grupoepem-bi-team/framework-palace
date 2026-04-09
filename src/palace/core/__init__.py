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
"""

# Base abstractions
from palace.core.base import (
    AgentBase,
    MemoryBase,
    ResultBase,
    TaskBase,
    ToolBase,
)

# Configuration
from palace.core.config import (
    AgentConfig,
    Config,
    MemoryConfig,
    ModelConfig,
    get_settings,
    load_config,
)

# Exceptions
from palace.core.exceptions import (
    AgentExecutionError,
    AgentNotFoundError,
    ConfigurationError,
    MemoryError,
    MemoryStoreError,
    OrchestratorError,
    PalaceError,
    PipelineError,
    TaskExecutionError,
    ValidationError,
)

# Framework entry point
from palace.core.framework import PalaceFramework

# Orchestrator
from palace.core.orchestrator import Orchestrator

# Types and enums
from palace.core.types import (
    AgentCapability,
    AgentInfo,
    AgentState,
    AgentStatus,
    MemoryEntry,
    MemoryType,
    ProjectContext,
    SessionContext,
    TaskPriority,
    TaskResult,
    TaskStatus,
    ToolInfo,
)

__all__ = [
    # Base classes
    "AgentBase",
    "TaskBase",
    "ResultBase",
    "MemoryBase",
    "ToolBase",
    # Framework
    "PalaceFramework",
    # Orchestrator
    "Orchestrator",
    # Configuration
    "Config",
    "AgentConfig",
    "ModelConfig",
    "MemoryConfig",
    "load_config",
    "get_settings",
    # Exceptions
    "PalaceError",
    "ConfigurationError",
    "AgentNotFoundError",
    "AgentExecutionError",
    "TaskExecutionError",
    "PipelineError",
    "MemoryError",
    "MemoryStoreError",
    "OrchestratorError",
    "ValidationError",
    # Types
    "AgentCapability",
    "AgentInfo",
    "AgentState",
    "AgentStatus",
    "TaskPriority",
    "TaskStatus",
    "TaskResult",
    "MemoryType",
    "MemoryEntry",
    "ProjectContext",
    "SessionContext",
    "ToolInfo",
]
