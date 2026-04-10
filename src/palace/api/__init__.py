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

Components:
    - main: FastAPI application instance, endpoints, and request/response models
"""

from palace.api.main import (
    AgentInfoResponse,
    ErrorResponse,
    HealthResponse,
    MemoryEntryRequest,
    MemoryQueryRequest,
    MemoryResponse,
    ProjectCreateRequest,
    ProjectResponse,
    SessionCreateRequest,
    SessionResponse,
    TaskCreateRequest,
    TaskResponse,
    app,
    get_framework,
)

# API version
__version__ = "1.0.0"

# Public API
__all__ = [
    # App
    "app",
    "get_framework",
    # Request models
    "ProjectCreateRequest",
    "TaskCreateRequest",
    "SessionCreateRequest",
    "MemoryQueryRequest",
    "MemoryEntryRequest",
    # Response models
    "ProjectResponse",
    "TaskResponse",
    "SessionResponse",
    "MemoryResponse",
    "AgentInfoResponse",
    "HealthResponse",
    "ErrorResponse",
]
