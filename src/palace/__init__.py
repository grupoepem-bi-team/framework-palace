"""
Palace Framework - Intelligent Multi-Agent Software Development System

A sophisticated multi-agent framework for software development with:
- Central orchestrator for task routing and coordination
- Specialized agents (backend, frontend, devops, infra, dba, qa, designer, reviewer)
- Vector memory for semantic context retrieval
- Project-scoped context management
- FastAPI-based REST API
- Command-line interface

Architecture Layers:
    - models: Domain types and Pydantic schemas (single source of truth)
    - core: Base abstractions, exceptions, and shared types
    - agents: Specialized agent implementations
    - memory: Vector store and episodic memory management
    - context: Project context and session management
    - api: FastAPI REST endpoints
    - cli: Command-line interface
    - pipelines: Workflow definitions and execution
    - tools: Shared tools and utilities
    - llm: LLM client, router, and provider integration

Usage:
    from palace import PalaceFramework

    framework = PalaceFramework()
    result = await framework.execute("Create a REST endpoint for user management")

Author: Palace Framework Team
Version: 0.1.0
"""

__version__ = "0.1.0"
__author__ = "Palace Framework Team"

# =============================================================================
# Domain Types (Single Source of Truth - models/domain_types.py)
# =============================================================================
# =============================================================================
# Core Exceptions
# =============================================================================
from palace.core.exceptions import PalaceError

# =============================================================================
# Public API
# =============================================================================
from palace.core.framework import PalaceFramework

# =============================================================================
# Dataclasses (core/types.py for backward compatibility)
# =============================================================================
from palace.core.types import (
    AgentConfig,
    AgentResult,
    MemoryEntry,
    Message,
    ModelConfig,
    ProjectConfig,
    ProjectContext,
    SessionContext,
    TaskDefinition,
    TaskResult,
)
from palace.models.domain_types import (
    AgentCapability,
    AgentRole,
    MemoryType,
    MessageType,
    ProjectStatus,
    SessionStatus,
    TaskPriority,
    TaskStatus,
)

__all__ = [
    # Version info
    "__version__",
    "__author__",
    # Framework entry point
    "PalaceFramework",
    # Domain Types (re-exported)
    "AgentRole",
    "TaskStatus",
    "TaskPriority",
    "MemoryType",
    "MessageType",
    "AgentCapability",
    "ProjectStatus",
    "SessionStatus",
    # Dataclasses
    "AgentConfig",
    "AgentResult",
    "ModelConfig",
    "MemoryEntry",
    "Message",
    "ProjectConfig",
    "ProjectContext",
    "SessionContext",
    "TaskDefinition",
    "TaskResult",
    # Exceptions
    "PalaceError",
]
