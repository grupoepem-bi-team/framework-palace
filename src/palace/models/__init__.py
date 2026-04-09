"""
Palace Framework - Models Module

This module defines all Pydantic models and schemas used throughout the Palace framework.
These models provide validation, serialization, and documentation for:

- API request/response models
- Database schemas
- Internal data structures
- Configuration models

All models use Pydantic v2 for validation and serialization.

Components:
    - AgentModels: Agent-related models (AgentInfo, AgentStatus, etc.)
    - TaskModels: Task-related models (TaskCreate, TaskResult, etc.)
    - ProjectModels: Project-related models (ProjectCreate, ProjectConfig, etc.)
    - MemoryModels: Memory-related models (MemoryEntry, MemoryQuery, etc.)
    - SessionModels: Session-related models (SessionCreate, SessionInfo, etc.)
    - PipelineModels: Pipeline-related models (PipelineConfig, PipelineStep, etc.)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# =============================================================================
# Enums
# =============================================================================


class AgentRole(str, Enum):
    """Roles that agents can play in the system."""

    ORCHESTRATOR = "orchestrator"
    BACKEND = "backend"
    FRONTEND = "frontend"
    DEVOPS = "devops"
    INFRA = "infra"
    DBA = "dba"
    QA = "qa"
    DESIGNER = "designer"
    REVIEWER = "reviewer"


class TaskStatus(str, Enum):
    """Status of a task in the execution pipeline."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REVIEW = "review"
    WAITING = "waiting"
    DELEGATED = "delegated"


class TaskPriority(int, Enum):
    """Priority levels for task scheduling."""

    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class MemoryType(str, Enum):
    """Types of memory storage."""

    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    PROJECT = "project"


class ProjectStatus(str, Enum):
    """Status of a project."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    PAUSED = "paused"
    DELETED = "deleted"


class SessionStatus(str, Enum):
    """Status of a conversation session."""

    ACTIVE = "active"
    CLOSED = "closed"
    EXPIRED = "expired"


# =============================================================================
# Agent Models
# =============================================================================


class AgentInfo(BaseModel):
    """Information about an agent."""

    name: str = Field(..., description="Agent name", min_length=1, max_length=50)
    role: AgentRole = Field(..., description="Agent role")
    model: str = Field(..., description="LLM model used")
    description: str = Field(..., description="Agent description")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    tools: List[str] = Field(default_factory=list, description="Available tools")
    status: str = Field(default="idle", description="Current status")
    max_tokens: int = Field(default=4096, description="Maximum tokens per request")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature")

    class Config:
        use_enum_values = True


class AgentStatusResponse(BaseModel):
    """Response model for agent status."""

    name: str
    role: AgentRole
    status: str
    current_task_id: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_activity: Optional[datetime] = None
    uptime_seconds: float = 0.0

    class Config:
        use_enum_values = True


# =============================================================================
# Task Models
# =============================================================================


class TaskCreateRequest(BaseModel):
    """Request to create and execute a task."""

    task: str = Field(..., description="Task description", min_length=10, max_length=10000)
    project_id: str = Field(..., description="Project identifier", min_length=1)
    session_id: Optional[str] = Field(None, description="Session identifier")
    agent_hint: Optional[AgentRole] = Field(None, description="Optional hint for agent routing")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        use_enum_values = True

    @field_validator("task")
    @classmethod
    def validate_task(cls, v: str) -> str:
        """Validate task description."""
        if not v.strip():
            raise ValueError("Task description cannot be empty")
        return v.strip()


class TaskResponse(BaseModel):
    """Response for task operations."""

    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Task status")
    result: Optional[str] = Field(None, description="Task result content")
    agent_used: Optional[AgentRole] = Field(None, description="Agent that executed the task")
    execution_time_seconds: float = Field(..., description="Execution time in seconds")
    tokens_used: int = Field(default=0, description="Total tokens consumed")
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, description="Generated artifacts")
    errors: List[str] = Field(default_factory=list, description="Errors encountered")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        use_enum_values = True


class TaskStatusResponse(BaseModel):
    """Response for task status queries."""

    task_id: str
    status: TaskStatus
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Progress percentage")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    agent: Optional[AgentRole] = None
    sub_tasks: List[str] = Field(default_factory=list, description="Sub-task IDs")

    class Config:
        use_enum_values = True


class TaskListResponse(BaseModel):
    """Response for listing tasks."""

    tasks: List[TaskStatusResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# =============================================================================
# Project Models
# =============================================================================


class ProjectCreateRequest(BaseModel):
    """Request to create a new project."""

    name: str = Field(..., description="Project name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Project description", max_length=1000)

    # Technology stack (optional)
    backend_framework: Optional[str] = Field(None, description="Backend framework")
    frontend_framework: Optional[str] = Field(None, description="Frontend framework")
    database: Optional[str] = Field(None, description="Database technology")
    deployment: Optional[str] = Field(None, description="Deployment platform")

    # Configuration
    code_style: str = Field(default="pep8", description="Code style guide")
    test_framework: Optional[str] = Field(None, description="Testing framework")

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Project tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "my-api-project",
                "description": "A new REST API project",
                "backend_framework": "fastapi",
                "database": "postgresql",
                "code_style": "pep8",
                "test_framework": "pytest",
                "tags": ["api", "backend"],
            }
        }


class ProjectResponse(BaseModel):
    """Response for project operations."""

    project_id: str = Field(..., description="Unique project identifier")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    status: ProjectStatus = Field(..., description="Project status")

    # Technology stack
    backend_framework: Optional[str] = None
    frontend_framework: Optional[str] = None
    database: Optional[str] = None
    deployment: Optional[str] = None

    # Statistics
    total_tasks: int = Field(default=0, description="Total tasks executed")
    active_sessions: int = Field(default=0, description="Active sessions")

    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        use_enum_values = True


class ProjectStatusResponse(BaseModel):
    """Detailed project status response."""

    project_id: str
    name: str
    status: ProjectStatus
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    active_sessions: int
    last_activity: datetime
    context_summary: Optional[str] = None

    class Config:
        use_enum_values = True


class ProjectListResponse(BaseModel):
    """Response for listing projects."""

    projects: List[ProjectResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# =============================================================================
# Session Models
# =============================================================================


class SessionCreateRequest(BaseModel):
    """Request to create a new session."""

    project_id: str = Field(..., description="Project identifier")
    initial_context: Optional[Dict[str, Any]] = Field(None, description="Initial session context")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Session metadata")


class SessionResponse(BaseModel):
    """Response for session operations."""

    session_id: str = Field(..., description="Session identifier")
    project_id: str = Field(..., description="Associated project")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE, description="Session status")
    message_count: int = Field(default=0, description="Number of messages")
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class MessageCreateRequest(BaseModel):
    """Request to add a message to a session."""

    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content", min_length=1, max_length=50000)
    agent: Optional[AgentRole] = Field(None, description="Agent role if role=assistant")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate message role."""
        valid_roles = ["user", "assistant", "system", "tool"]
        if v not in valid_roles:
            raise ValueError(f"Invalid role: {v}. Must be one of {valid_roles}")
        return v


class MessageResponse(BaseModel):
    """Response for a single message."""

    message_id: str
    session_id: str
    role: str
    content: str
    agent: Optional[AgentRole] = None
    tokens: int = Field(default=0, description="Tokens in message")
    created_at: datetime

    class Config:
        use_enum_values = True


class SessionHistoryResponse(BaseModel):
    """Response for session history."""

    session_id: str
    messages: List[MessageResponse]
    total_messages: int
    has_more: bool


# =============================================================================
# Memory Models
# =============================================================================


class MemoryEntryRequest(BaseModel):
    """Request to add a memory entry."""

    project_id: str = Field(..., description="Project identifier")
    content: str = Field(..., description="Content to store", min_length=10, max_length=100000)
    memory_type: MemoryType = Field(default=MemoryType.SEMANTIC, description="Memory type")
    source: str = Field(default="user", description="Source of the memory")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    priority: int = Field(default=5, ge=1, le=20, description="Entry priority")

    class Config:
        use_enum_values = True


class MemoryEntryResponse(BaseModel):
    """Response for a memory entry."""

    entry_id: str
    project_id: str
    memory_type: MemoryType
    content: str
    source: str
    created_at: datetime
    access_count: int
    metadata: Dict[str, Any]

    class Config:
        use_enum_values = True


class MemorySearchRequest(BaseModel):
    """Request to search memory."""

    query: str = Field(..., description="Search query", min_length=3, max_length=1000)
    project_id: str = Field(..., description="Project identifier")
    memory_types: Optional[List[MemoryType]] = Field(None, description="Memory types to search")
    top_k: int = Field(default=5, ge=1, le=100, description="Number of results")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score")
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")

    class Config:
        use_enum_values = True


class MemorySearchResult(BaseModel):
    """A single search result."""

    entry_id: str
    content: str
    score: float
    memory_type: MemoryType
    source: str
    metadata: Dict[str, Any]
    highlights: List[str] = Field(default_factory=list, description="Highlighted snippets")

    class Config:
        use_enum_values = True


class MemorySearchResponse(BaseModel):
    """Response for memory search."""

    results: List[MemorySearchResult]
    total: int
    query: str
    execution_time_ms: float


# =============================================================================
# Pipeline Models
# =============================================================================


class PipelineStepConfig(BaseModel):
    """Configuration for a single pipeline step."""

    name: str = Field(..., description="Step name")
    agent: AgentRole = Field(..., description="Agent to use for this step")
    description: Optional[str] = Field(None, description="Step description")
    input_key: str = Field(default="input", description="Input key from previous step")
    output_key: str = Field(default="output", description="Output key for next step")
    depends_on: List[str] = Field(default_factory=list, description="Step dependencies")
    condition: Optional[str] = Field(None, description="Condition to execute this step")
    timeout_seconds: int = Field(default=300, description="Step timeout")
    retry_count: int = Field(default=3, ge=0, le=10, description="Retry attempts")
    on_failure: str = Field(default="stop", description="Action on failure: stop, skip, retry")

    class Config:
        use_enum_values = True


class PipelineCreateRequest(BaseModel):
    """Request to create a pipeline."""

    name: str = Field(..., description="Pipeline name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Pipeline description")
    project_id: str = Field(..., description="Project identifier")
    steps: List[PipelineStepConfig] = Field(..., min_length=1, description="Pipeline steps")
    parallel_execution: bool = Field(default=False, description="Allow parallel step execution")
    max_concurrent_steps: int = Field(default=3, ge=1, le=10, description="Max concurrent steps")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Pipeline metadata")


class PipelineResponse(BaseModel):
    """Response for pipeline operations."""

    pipeline_id: str
    name: str
    description: Optional[str]
    project_id: str
    steps: List[PipelineStepConfig]
    status: str
    created_at: datetime
    updated_at: datetime


class PipelineExecutionRequest(BaseModel):
    """Request to execute a pipeline."""

    pipeline_id: str = Field(..., description="Pipeline identifier")
    initial_input: Dict[str, Any] = Field(default_factory=dict, description="Initial input data")
    context: Optional[Dict[str, Any]] = Field(None, description="Execution context")
    wait_for_completion: bool = Field(default=True, description="Wait for pipeline completion")


class PipelineExecutionResponse(BaseModel):
    """Response for pipeline execution."""

    execution_id: str
    pipeline_id: str
    status: str
    current_step: Optional[str]
    completed_steps: List[str]
    failed_steps: List[str]
    output: Optional[Dict[str, Any]]
    started_at: datetime
    completed_at: Optional[datetime]
    execution_time_seconds: float


# =============================================================================
# Context Models
# =============================================================================


class ContextQueryRequest(BaseModel):
    """Request to query context."""

    project_id: str = Field(..., description="Project identifier")
    query: str = Field(..., description="Context query", min_length=3)
    memory_types: Optional[List[MemoryType]] = Field(None, description="Memory types to include")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results")
    include_adrs: bool = Field(default=True, description="Include ADRs")
    include_patterns: bool = Field(default=True, description="Include code patterns")
    include_history: bool = Field(default=False, description="Include conversation history")

    class Config:
        use_enum_values = True


class ContextResponse(BaseModel):
    """Response for context query."""

    project_id: str
    query: str
    results: List[Dict[str, Any]]
    adrs: List[Dict[str, Any]]
    patterns: List[Dict[str, Any]]
    total_entries: int
    execution_time_ms: float


class DecisionRecordRequest(BaseModel):
    """Request to create an Architecture Decision Record."""

    project_id: str = Field(..., description="Project identifier")
    title: str = Field(..., description="ADR title", min_length=5, max_length=200)
    context: str = Field(..., description="Context and problem statement")
    decision: str = Field(..., description="The decision made")
    consequences: str = Field(..., description="Consequences of the decision")
    status: str = Field(default="proposed", description="ADR status")
    tags: List[str] = Field(default_factory=list, description="ADR tags")


class DecisionRecordResponse(BaseModel):
    """Response for an ADR."""

    adr_id: str
    project_id: str
    title: str
    context: str
    decision: str
    consequences: str
    status: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Health and Status Models
# =============================================================================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    framework_initialized: bool = Field(..., description="Framework initialization status")
    uptime_seconds: float = Field(default=0.0, description="Service uptime")
    components: Dict[str, str] = Field(default_factory=dict, description="Component statuses")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")


class ValidationErrorResponse(BaseModel):
    """Validation error response."""

    error: str = Field(default="VALIDATION_ERROR", description="Error code")
    message: str = Field(..., description="Error message")
    errors: List[Dict[str, Any]] = Field(..., description="Validation errors")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Statistics Models
# =============================================================================


class AgentStatistics(BaseModel):
    """Statistics for a single agent."""

    agent_name: str
    tasks_completed: int
    tasks_failed: int
    average_execution_time: float
    total_tokens_used: int
    success_rate: float


class ProjectStatistics(BaseModel):
    """Statistics for a project."""

    project_id: str
    project_name: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    active_sessions: int
    memory_entries: int
    adrs_count: int
    last_activity: datetime


class FrameworkStatistics(BaseModel):
    """Overall framework statistics."""

    total_projects: int
    total_tasks: int
    total_sessions: int
    total_memory_entries: int
    agents: List[AgentStatistics]
    uptime_seconds: float
    version: str


# =============================================================================
# Configuration Models
# =============================================================================


class ModelAssignment(BaseModel):
    """Model assignment for an agent role."""

    role: AgentRole
    model: str
    max_tokens: int = Field(default=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    class Config:
        use_enum_values = True


class FrameworkConfigResponse(BaseModel):
    """Framework configuration response."""

    version: str
    environment: str
    models: List[ModelAssignment]
    memory_type: str
    api_host: str
    api_port: int
    log_level: str


# =============================================================================
# Export all models
# =============================================================================

__all__ = [
    # Enums
    "AgentRole",
    "TaskStatus",
    "TaskPriority",
    "MemoryType",
    "ProjectStatus",
    "SessionStatus",
    # Agent models
    "AgentInfo",
    "AgentStatusResponse",
    # Task models
    "TaskCreateRequest",
    "TaskResponse",
    "TaskStatusResponse",
    "TaskListResponse",
    # Project models
    "ProjectCreateRequest",
    "ProjectResponse",
    "ProjectStatusResponse",
    "ProjectListResponse",
    # Session models
    "SessionCreateRequest",
    "SessionResponse",
    "MessageCreateRequest",
    "MessageResponse",
    "SessionHistoryResponse",
    # Memory models
    "MemoryEntryRequest",
    "MemoryEntryResponse",
    "MemorySearchRequest",
    "MemorySearchResult",
    "MemorySearchResponse",
    # Pipeline models
    "PipelineStepConfig",
    "PipelineCreateRequest",
    "PipelineResponse",
    "PipelineExecutionRequest",
    "PipelineExecutionResponse",
    # Context models
    "ContextQueryRequest",
    "ContextResponse",
    "DecisionRecordRequest",
    "DecisionRecordResponse",
    # Health and error models
    "HealthResponse",
    "ErrorResponse",
    "ValidationErrorResponse",
    # Statistics models
    "AgentStatistics",
    "ProjectStatistics",
    "FrameworkStatistics",
    # Configuration models
    "ModelAssignment",
    "FrameworkConfigResponse",
]
