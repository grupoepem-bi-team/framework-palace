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

# Core abstractions - exposed at package level
from palace.core.base import AgentBase, ResultBase, TaskBase

# Framework entry point
from palace.core.framework import PalaceFramework
from palace.core.orchestrator import Orchestrator
from palace.core.types import (
    AgentCapability,
    ProjectContext,
    SessionContext,
    TaskStatus,
)

# Agent registry
from palace.agents import (
    BackendAgent,
    DBAAgent,
    DesignerAgent,
    DevOpsAgent,
    FrontendAgent,
    InfraAgent,
    QAAgent,
    ReviewerAgent,
    get_agent,
    list_agents,
)

# Context management
from palace.context import ContextManager, ProjectContextManager

# Memory management
from palace.memory import MemoryStore, MemoryType, VectorStore

# Public API
__all__ = [
    # Version info
    "__version__",
    "__author__",
    # Core
    "PalaceFramework",
    "Orchestrator",
    "AgentBase",
    "TaskBase",
    "ResultBase",
    # Types
    "AgentCapability",
    "TaskStatus",
    "ProjectContext",
    "SessionContext",
    # Agents
    "BackendAgent",
    "FrontendAgent",
    "DevOpsAgent",
    "InfraAgent",
    "DBAAgent",
    "QAAgent",
    "DesignerAgent",
    "ReviewerAgent",
    "get_agent",
    "list_agents",
    # Memory
    "MemoryStore",
    "VectorStore",
    "MemoryType",
    # Context
    "ContextManager",
    "ProjectContextManager",
]
