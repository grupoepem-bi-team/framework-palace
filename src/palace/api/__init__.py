"""
Palace Framework - REST API Module

This module provides the FastAPI-based REST API for the Palace framework.
It exposes endpoints for:

- Project management (create, list, get, delete)
- Task execution (submit tasks, check status, get results)
- Agent interaction (list agents, get agent info)
- Memory management (store, retrieve, search)
- Session management (create sessions, get history)
- WebSocket streaming for real-time updates

Architecture:
    - routers: API route definitions
    - dependencies: Dependency injection for FastAPI
    - middleware: Request/response processing
    - models: API request/response models
    - exceptions: API-specific exceptions
    - auth: Authentication and authorization
"""

from palace.api.app import create_app, get_app
from palace.api.dependencies import get_context_manager, get_memory_store, get_orchestrator
from palace.api.models import (
    AgentInfoResponse,
    ErrorResponse,
    HealthResponse,
    MemoryEntryRequest,
    MemoryEntryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    ProjectCreateRequest,
    ProjectResponse,
    TaskCreateRequest,
    TaskResponse,
    TaskStatusResponse,
)

# API version
__version__ = "1.0.0"

# Public API
__all__ = [
    # App factory
    "create_app",
    "get_app",
    # Dependencies
    "get_orchestrator",
    "get_memory_store",
    "get_context_manager",
    # Request models
    "ProjectCreateRequest",
    "TaskCreateRequest",
    "MemoryEntryRequest",
    "MemorySearchRequest",
    # Response models
    "ProjectResponse",
    "TaskResponse",
    "TaskStatusResponse",
    "AgentInfoResponse",
    "MemoryEntryResponse",
    "MemorySearchResponse",
    "HealthResponse",
    "ErrorResponse",
]
