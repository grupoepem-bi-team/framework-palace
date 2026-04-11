framework-palace/src/palace/models/__init__.py
```
"""Palace Framework - Models Module

This module defines all Pydantic models and schemas used throughout the Palace framework.
These models provide validation, serialization, and documentation for:

- API request/response models
- Database schemas
- Internal data structures
- Configuration models

All models use Pydantic v2 for validation and serialization.

Components:
    - Domain Types: Shared enums and protocols (imported from domain_types)
    - Request Models: API request schemas
    - Response Models: API response schemas
    - Configuration Models: Internal configuration structures

Domain Types (Imported from domain_types):
    - AgentRole, TaskStatus, TaskPriority, MemoryType
    - AgentCapability, ProjectStatus, SessionStatus, MessageType
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# Import Domain Types from domain_types.py (Single Source of Truth)
# =============================================================================

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

# Re-export for convenience
__all__ = [
    # Domain Types (re-exported)
    "AgentRole",
    "TaskStatus",
    "TaskPriority",
    "MemoryType",
    "MessageType",
    "AgentCapability",
    "ProjectStatus",
    "SessionStatus",
    # Request Models
    "TaskCreateRequest",
    "TaskResponse",
    "TaskStatusResponse",
    "TaskListResponse",
    "ProjectCreateRequest",
    "ProjectResponse",
    "ProjectStatusResponse",
    "ProjectListResponse",
    "SessionCreateRequest",
    "SessionResponse",
    "SessionHistoryResponse",
    "MessageCreateRequest",
    "MessageResponse",
    "MemoryEntryRequest",
    "MemoryEntryResponse",
    "MemorySearchRequest",
    "MemorySearchResult",
    "MemorySearchResponse",
    "PipelineStepConfig",
    "PipelineCreateRequest",
    "PipelineResponse",
    "PipelineExecutionRequest",
    "PipelineExecutionResponse",
    "ContextQueryRequest",
    "ContextResponse",
    "DecisionRecordRequest",
    "DecisionRecordResponse",
    # Response Models
    "HealthResponse",
    "ErrorResponse",
    "ValidationErrorResponse",
    "AgentInfo",
    "AgentStatusResponse",
    # Statistics Models
    "AgentStatistics",
    "ProjectStatistics",
    "FrameworkStatistics",
    "ModelAssignment",
    "FrameworkConfigResponse",
]


# =============================================================================
# Agent Models
# =============================================================================


class AgentInfo(BaseModel):
    """Information about an agent."""

    name: str = Field(..., description="Agent name")
    role: AgentRole = Field(..., description="Agent role")
    model: str = Field(..., description="Model used by the agent")
    status: str = Field(default="available", description="Agent status")
    capabilities: List[AgentCapability] = Field(
        default_factory=list,
        description="Agent capabilities",
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Agent configuration",
    )


class AgentStatusResponse(BaseModel):
    """Response model for agent status."""

    name: str
    role: AgentRole
    status: str
    model: str
    available: bool
    uptime_seconds: Optional[float] = None


# =============================================================================
# Task Models
# =============================================================================


class TaskCreateRequest(BaseModel):
    """Request model for creating a task."""

    project_id: str = Field(..., min_length=1, description="Project identifier")
    task: str = Field(..., min_length=1, description="Task description")
    session_id: Optional[str] = Field(None, description="Session identifier")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context",
    )

    @field_validator("task")
    @classmethod
    def validate_task(cls, v: str) -> str:
        if not v or len(v.strip()) < 5:
            raise ValueError("Task description must be at least 5 characters")
        return v.strip()


class TaskResponse(BaseModel):
    """Response model for a single task."""

    task_id: str
    project_id: str
    task: str
    status: TaskStatus
    result: Optional[str] = None
    agent: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    execution_time_ms: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskStatusResponse(BaseModel):
    """Response model for task status."""

    task_id: str
    status: TaskStatus
    progress: Optional[float] = None
    message: Optional[str] = None


class TaskListResponse(BaseModel):
    """Response model for task list."""

    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Project Models
# =============================================================================


class ProjectCreateRequest(BaseModel):
    """Request model for creating a project."""

    project_id: str = Field(..., min_length=1, description="Project identifier")
    name: Optional[str] = Field(None, description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    context_dir: Optional[str] = Field(None, description="Context directory path")
    model: Optional[str] = Field(None, description="Default model for project")


class ProjectResponse(BaseModel):
    """Response model for a project."""

    project_id: str
    name: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    status: ProjectStatus
    context_dir: Optional[str] = None


class ProjectStatusResponse(BaseModel):
    """Response model for project status."""

    project_id: str
    status: ProjectStatus
    active_sessions: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int


class ProjectListResponse(BaseModel):
    """Response model for project list."""

    projects: List[ProjectResponse]
    total: int


# =============================================================================
# Session Models
# =============================================================================


class SessionCreateRequest(BaseModel):
    """Request model for creating a session."""

    project_id: str = Field(..., min_length=1)
    session_id: Optional[str] = Field(None, description="Session ID (auto-generated if not provided)")


class SessionResponse(BaseModel):
    """Response model for a session."""

    project_id: str
    session_id: str
    status: SessionStatus
    created_at: datetime
    last_activity: Optional[datetime] = None


class SessionHistoryResponse(BaseModel):
    """Response model for session history."""

    project_id: str
    session_id: str
    messages: List[Dict[str, Any]]
    total_messages: int


# =============================================================================
# Message Models
# =============================================================================


class MessageCreateRequest(BaseModel):
    """Request model for creating a message."""

    project_id: str
    session_id: str
    role: AgentRole
    content: str = Field(..., min_length=1)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or len(v.strip()) < 1:
            raise ValueError("Content cannot be empty")
        return v


class MessageResponse(BaseModel):
    """Response model for a message."""

    id: str
    project_id: str
    session_id: str
    role: AgentRole
    content: str
    created_at: datetime


class SessionHistoryResponse(BaseModel):
    """Response model for session history."""

    project_id: str
    session_id: str
    messages: List[MessageResponse]
    total_messages: int


# =============================================================================
# Memory Models
# =============================================================================


class MemoryEntryRequest(BaseModel):
    """Request model for storing a memory entry."""

    project_id: str
    session_id: Optional[str] = None
    memory_type: MemoryType
    content: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None


class MemoryEntryResponse(BaseModel):
    """Response model for a memory entry."""

    id: str
    project_id: str
    session_id: Optional[str]
    memory_type: MemoryType
    content: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class MemorySearchRequest(BaseModel):
    """Request model for searching memory."""

    project_id: str
    query: str = Field(..., min_length=1)
    memory_type: Optional[MemoryType] = None
    limit: int = Field(default=10, ge=1, le=100)
    min_score: float = Field(default=0.5, ge=0.0, le=1.0)


class MemorySearchResult(BaseModel):
    """Response model for a memory search result."""

    entry_id: str
    project_id: str
    content: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


class MemorySearchResponse(BaseModel):
    """Response model for memory search."""

    results: List[MemorySearchResult]
    total: int


# =============================================================================
# Pipeline Models
# =============================================================================


class PipelineStepConfig(BaseModel):
    """Configuration for a pipeline step."""

    agent: AgentRole
    model: Optional[str] = None
    description: Optional[str] = None
    requires: List[str] = Field(default_factory=list)
    triggers: List[str] = Field(default_factory=list)


class PipelineCreateRequest(BaseModel):
    """Request model for creating a pipeline."""

    project_id: str
    name: str
    description: Optional[str] = None
    steps: List[PipelineStepConfig]


class PipelineResponse(BaseModel):
    """Response model for a pipeline."""

    id: str
    project_id: str
    name: str
    description: Optional[str]
    steps: List[PipelineStepConfig]
    created_at: datetime
    updated_at: datetime


class PipelineExecutionRequest(BaseModel):
    """Request model for executing a pipeline."""

    project_id: str
    pipeline_id: str
    parameters: Optional[Dict[str, Any]] = None


class PipelineExecutionResponse(BaseModel):
    """Response model for pipeline execution."""

    execution_id: str
    status: str
    results: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]


# =============================================================================
# Context Models
# =============================================================================


class ContextQueryRequest(BaseModel):
    """Request model for context query."""

    project_id: str
    query: str
    session_id: Optional[str] = None


class ContextResponse(BaseModel):
    """Response model for context query."""

    project_id: str
    context: Dict[str, Any]
    sources: List[str]


class DecisionRecordRequest(BaseModel):
    """Request model for decision record."""

    project_id: str
    title: str
    content: str
    status: str = "proposed"


class DecisionRecordResponse(BaseModel):
    """Response model for decision record."""

    id: str
    project_id: str
    title: str
    content: str
    status: str
    created_at: datetime


# =============================================================================
# Health & Error Models
# =============================================================================


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    version: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str
    message: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ValidationErrorResponse(BaseModel):
    """Response model for validation errors."""

    error: str
    message: str
    errors: List[Dict[str, Any]]


# =============================================================================
# Statistics Models
# =============================================================================


class AgentStatistics(BaseModel):
    """Statistics for an agent."""

    agent: str
    tasks_completed: int
    tasks_failed: int
    average_execution_time_ms: float


class ProjectStatistics(BaseModel):
    """Statistics for a project."""

    project_id: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    average_execution_time_ms: float


class FrameworkStatistics(BaseModel):
    """Statistics for the entire framework."""

    total_projects: int
    active_sessions: int
    total_agents: int
    memory_entries: int


# =============================================================================
# Configuration Models
# =============================================================================


class ModelAssignment(BaseModel):
    """Model assignment for an agent type."""

    agent_type: str
    model: str


class FrameworkConfigResponse(BaseModel):
    """Response model for framework configuration."""

    app_name: str
    app_version: str
    environment: str
    models: Dict[str, ModelAssignment]
    memory_store: str
    api_host: str
    api_port: int
