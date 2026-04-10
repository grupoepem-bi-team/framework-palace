"""
Palace Framework - Intelligent Multi-Agent Software Development System

A sophisticated multi-agent framework for software development with:
- Central orchestrator for task routing and coordination
- Specialized agents (backend, frontend, devops, infra, dba, qa, designer, reviewer)
- Vector memory for semantic context retrieval
- Project-scoped context management
- FastAPI-based REST API
- Command-line interface
- Zep integration ready

Architecture Layers:
    - core: Base abstractions, interfaces, and shared types
    - agents: Specialized agent implementations
    - memory: Vector store and episodic memory management
    - context: Project context and session management
    - api: FastAPI REST endpoints
    - cli: Command-line interface
    - pipelines: Workflow definitions and execution
    - tools: Shared tools and utilities
    - models: Pydantic models and schemas

Usage:
    from palace import PalaceFramework

    framework = PalaceFramework()
    result = await framework.execute("Create a REST endpoint for user management")

Author: Palace Framework Team
Version: 0.1.0
"""

__version__ = "0.1.0"
__author__ = "Palace Framework Team"

# Core types - always safe to import (no side effects)
# Core exceptions - always safe to import
from palace.core.exceptions import PalaceError
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

# Core types - dataclasses
from palace.core.types import ModelConfig as TypesModelConfig

# Public API
__all__ = [
    # Version info
    "__version__",
    "__author__",
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
    # Exceptions
    "PalaceError",
]
