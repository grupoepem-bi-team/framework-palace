"""
Palace Framework - Core Types (Re-exported from models/domain_types)

This module re-exports domain types from models/domain_types.py.
The actual definitions are in models/domain_types.py (single source of truth).

This module maintains backward compatibility by re-exporting types.
All new code should import directly from palace.models.domain_types.

Imports:
    - AgentRole, TaskStatus, TaskPriority, MemoryType
    - AgentCapability, MessageType, ProjectStatus, SessionStatus
    - Dataclasses: ModelConfig, AgentConfig, TaskResult
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

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

# Re-exported domain types
__all__ = [
    "AgentRole",
    "TaskStatus",
    "TaskPriority",
    "MemoryType",
    "MessageType",
    "AgentCapability",
    "ProjectStatus",
    "SessionStatus",
    "ModelConfig",
    "AgentConfig",
    "TaskResult",
    "ProjectConfig",
    "ProjectContext",
    "SessionContext",
    "TaskDefinition",
    "Message",
    "MemoryEntry",
]


@dataclass
class ModelConfig:
    """Configuration for a specific LLM model."""

    name: str
    provider: str = "ollama"
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    capabilities: List[AgentCapability] = field(default_factory=list)
    cost_per_1k_tokens: float = 0.0


@dataclass
class AgentConfig:
    """Configuration for a specific agent."""

    role: AgentRole
    model: str
    system_prompt: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    max_iterations: int = 10
    timeout_seconds: int = 300


@dataclass
class TaskResult:
    """Result of a task execution through the orchestrator."""

    task_id: str
    status: TaskStatus
    content: str = ""
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    agent_results: List[Any] = field(default_factory=list)
    execution_time_ms: int = 0
    tokens_used: int = 0
    model_used: str = ""


class ProjectConfig(BaseModel):
    """Configuration for a specific project."""

    project_id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Human-readable project name")
    description: Optional[str] = Field(default=None, description="Project description")
    backend_framework: Optional[str] = Field(default=None, description="e.g., fastapi, django")
    frontend_framework: Optional[str] = Field(default=None, description="e.g., react, vue")
    database: Optional[str] = Field(default=None, description="e.g., postgresql, mysql")
    deployment: Optional[str] = Field(default=None, description="e.g., kubernetes, docker")
    root_path: str = Field(default=".", description="Project root directory")
    source_path: str = Field(default="src", description="Source code directory")
    tests_path: str = Field(default="tests", description="Tests directory")
    code_style: str = Field(default="pep8", description="Code style guide")
    test_framework: Optional[str] = Field(default=None, description="e.g., pytest, jest")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectContext(BaseModel):
    """Runtime context for a project."""

    config: ProjectConfig
    adrs: List[Dict[str, Any]] = Field(default_factory=list, description="ADR references")
    patterns: List[str] = Field(default_factory=list, description="Identified patterns")
    active_session_id: Optional[UUID] = Field(default=None)
    cached_files: Dict[str, str] = Field(
        default_factory=dict, description="Key files content cache"
    )
    instructions: List[str] = Field(default_factory=list, description="Project instructions")

    def touch(self) -> None:
        """Update the last modified timestamp."""
        self.config.updated_at = datetime.utcnow()


class SessionContext(BaseModel):
    """Context for a single conversation session."""

    session_id: UUID = Field(default_factory=uuid4)
    project_id: UUID = Field(..., description="Associated project")
    messages: List[Dict[str, Any]] = Field(
        default_factory=list, description="Conversation messages"
    )
    active_tasks: List[UUID] = Field(default_factory=list, description="Active task IDs")
    completed_tasks: List[UUID] = Field(default_factory=list, description="Completed task IDs")
    current_agent: Optional[str] = Field(default=None, description="Currently active agent")
    agent_history: List[str] = Field(default_factory=list, description="Sequence of agents")
    retrieved_context: List[Dict[str, Any]] = Field(
        default_factory=list, description="Retrieved context"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TaskDefinition(BaseModel):
    """Definition of a task to be executed."""

    task_id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., description="Short task title")
    description: str = Field(..., description="Detailed task description")
    required_capabilities: Set[AgentCapability] = Field(default_factory=set)
    suggested_agent: Optional[AgentRole] = Field(default=None)
    priority: TaskPriority = Field(default=TaskPriority.NORMAL)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    project_id: UUID = Field(..., description="Associated project")
    session_id: UUID = Field(..., description="Associated session")
    parent_task_id: Optional[UUID] = Field(default=None)
    depends_on: List[UUID] = Field(default_factory=list)
    input_context: Dict[str, Any] = Field(default_factory=dict)
    output: Optional[Dict[str, Any]] = Field(default=None)
    error: Optional[str] = Field(default=None)
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)


class AgentResult(BaseModel):
    """Result from an agent execution."""

    success: bool = Field(..., description="Whether execution succeeded")
    content: str = Field(default="", description="Main output content")
    structured_output: Optional[Dict[str, Any]] = Field(default=None)
    files_created: List[str] = Field(default_factory=list)
    files_modified: List[str] = Field(default_factory=list)
    next_actions: List[Dict[str, Any]] = Field(default_factory=list)
    delegate_to: Optional[AgentRole] = Field(default=None)
    context_updates: Dict[str, Any] = Field(default_factory=dict)
    memory_entries: List[Dict[str, Any]] = Field(default_factory=list)
    agent: AgentRole = Field(..., description="Agent that produced this result")
    model_used: str = Field(..., description="LLM model used")
    tokens_used: int = Field(default=0)
    execution_time_ms: int = Field(default=0)
    error: Optional[str] = Field(default=None)
    error_details: Optional[Dict[str, Any]] = Field(default=None)


class Message(BaseModel):
    """A message in the conversation."""

    message_id: UUID = Field(default_factory=uuid4)
    session_id: UUID = Field(..., description="Associated session")
    role: MessageType = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    agent: Optional[AgentRole] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tokens: int = Field(default=0)


class MemoryEntry(BaseModel):
    """An entry in the vector memory store."""

    entry_id: UUID = Field(default_factory=uuid4)
    memory_type: MemoryType = Field(..., description="Type of memory")
    project_id: UUID = Field(..., description="Associated project")
    content: str = Field(..., description="Text content")
    embedding: Optional[List[float]] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: str = Field(default="unknown")
    source_id: Optional[UUID] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None)
    access_count: int = Field(default=0)
    last_accessed: Optional[datetime] = Field(default=None)
