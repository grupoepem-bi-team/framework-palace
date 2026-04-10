"""
Palace Framework - Core Types and Enums

This module defines all core types, enums, and data structures
used throughout the framework. These types provide the foundation
for type-safe communication between components.

Architecture:
    - TaskStatus: Lifecycle states for tasks
    - AgentCapability: Skills and competencies of agents
    - MemoryType: Types of memory storage
    - ProjectContext: Project-level configuration and state
    - SessionContext: Conversation-level context
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """
    Lifecycle states for tasks in the framework.

    Flow:
        PENDING -> RUNNING -> (COMPLETED | FAILED | CANCELLED)
                          └──> REVIEW -> (COMPLETED | FAILED)
    """

    PENDING = "pending"
    """Task is queued but not yet started."""

    RUNNING = "running"
    """Task is currently being executed by an agent."""

    COMPLETED = "completed"
    """Task finished successfully."""

    FAILED = "failed"
    """Task execution failed with an error."""

    CANCELLED = "cancelled"
    """Task was cancelled before completion."""

    REVIEW = "review"
    """Task output is under review (by ReviewerAgent or QA)."""

    WAITING = "waiting"
    """Task is waiting for user input or external dependency."""

    DELEGATED = "delegated"
    """Task was delegated to another agent."""


class AgentCapability(str, Enum):
    """
    Skills and competencies that agents can have.

    Each agent declares its capabilities, and the orchestrator
    uses these to route tasks to the most appropriate agent.
    """

    # Development capabilities
    BACKEND_DEVELOPMENT = "backend_development"
    """API development, database integration, business logic."""

    FRONTEND_DEVELOPMENT = "frontend_development"
    """UI components, client-side logic, styling."""

    FULLSTACK_DEVELOPMENT = "fullstack_development"
    """End-to-end feature implementation."""

    # Infrastructure capabilities
    INFRASTRUCTURE_AS_CODE = "infrastructure_as_code"
    """Terraform, Kubernetes, Docker, Cloud SDK."""

    DEVOPS = "devops"
    """CI/CD pipelines, deployment automation."""

    DATABASE_ADMINISTRATION = "database_administration"
    """Schema design, migrations, query optimization."""

    # Quality capabilities
    CODE_REVIEW = "code_review"
    """Code quality, security, best practices review."""

    TESTING = "testing"
    """Unit tests, integration tests, E2E tests."""

    QUALITY_ASSURANCE = "quality_assurance"
    """Quality metrics, coverage analysis, linting."""

    # Design capabilities
    UI_UX_DESIGN = "ui_ux_design"
    """User interface design, accessibility, design systems."""

    ARCHITECTURE = "architecture"
    """System architecture, design patterns, ADRs."""

    # Coordination capabilities
    ORCHESTRATION = "orchestration"
    """Task routing, planning, coordination."""

    PLANNING = "planning"
    """Task decomposition, estimation, scheduling."""

    DOCUMENTATION = "documentation"
    """Technical writing, API docs, README."""


class MemoryType(str, Enum):
    """
    Types of memory storage in the framework.

    Each type serves a different purpose and has different
    retention and retrieval characteristics.
    """

    EPISODIC = "episodic"
    """Conversation history, task results (short-term)."""

    SEMANTIC = "semantic"
    """Knowledge, ADRs, patterns (long-term)."""

    PROCEDURAL = "procedural"
    """Scripts, tools, reusable procedures."""

    PROJECT = "project"
    """Project-specific context and configuration."""


class MessageType(str, Enum):
    """Types of messages in the conversation flow."""

    USER = "user"
    """Message from the user."""

    ASSISTANT = "assistant"
    """Message from an agent."""

    SYSTEM = "system"
    """System message (prompts, instructions)."""

    TOOL = "tool"
    """Tool execution result."""


class TaskPriority(int, Enum):
    """Priority levels for task scheduling."""

    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class AgentRole(str, Enum):
    """
    Roles that agents can play in the system.

    Each role maps to a specialized agent implementation.
    """

    ORCHESTRATOR = "orchestrator"
    BACKEND = "backend"
    FRONTEND = "frontend"
    DEVOPS = "devops"
    INFRA = "infra"
    DBA = "dba"
    QA = "qa"
    DESIGNER = "designer"
    REVIEWER = "reviewer"


# ============================================================================
# Pydantic Models
# ============================================================================


class ProjectConfig(BaseModel):
    """
    Configuration for a specific project.

    This is stored in memory and used to provide context
    to agents when working on project-specific tasks.
    """

    project_id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Human-readable project name")
    description: Optional[str] = Field(default=None, description="Project description")

    # Technology stack
    backend_framework: Optional[str] = Field(default=None, description="e.g., fastapi, django")
    frontend_framework: Optional[str] = Field(default=None, description="e.g., react, vue")
    database: Optional[str] = Field(default=None, description="e.g., postgresql, mysql")
    deployment: Optional[str] = Field(default=None, description="e.g., kubernetes, docker")

    # Paths
    root_path: str = Field(default=".", description="Project root directory")
    source_path: str = Field(default="src", description="Source code directory")
    tests_path: str = Field(default="tests", description="Tests directory")

    # Coding standards
    code_style: str = Field(default="pep8", description="Code style guide")
    test_framework: Optional[str] = Field(default=None, description="e.g., pytest, jest")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class ProjectContext(BaseModel):
    """
    Runtime context for a project.

    Combines configuration with runtime state like:
    - Current session
    - Active decisions
    - Loaded patterns
    """

    config: ProjectConfig

    # Architecture Decision Records
    adrs: List[Dict[str, Any]] = Field(default_factory=list, description="ADR references")

    # Design patterns in use
    patterns: List[str] = Field(default_factory=list, description="Identified patterns")

    # Current session reference
    active_session_id: Optional[UUID] = Field(default=None)

    # Cached context for quick access
    cached_files: Dict[str, str] = Field(
        default_factory=dict, description="Key files content cache (relative_path -> content)"
    )

    # Project-specific instructions
    instructions: List[str] = Field(
        default_factory=list, description="Project-specific instructions for agents"
    )

    def touch(self) -> None:
        """Update the last modified timestamp."""
        self.config.updated_at = datetime.utcnow()


class SessionContext(BaseModel):
    """
    Context for a single conversation session.

    A session represents one or more interactions with the framework
    focused on a specific task or set of related tasks.
    """

    session_id: UUID = Field(default_factory=uuid4)
    project_id: UUID = Field(..., description="Associated project")

    # Conversation history
    messages: List[Dict[str, Any]] = Field(
        default_factory=list, description="Conversation messages"
    )

    # Task tracking
    active_tasks: List[UUID] = Field(default_factory=list, description="Currently active task IDs")
    completed_tasks: List[UUID] = Field(default_factory=list, description="Completed task IDs")

    # Current agent context
    current_agent: Optional[str] = Field(default=None, description="Currently active agent role")
    agent_history: List[str] = Field(
        default_factory=list, description="Sequence of agents involved"
    )

    # Retrieved context (from memory)
    retrieved_context: List[Dict[str, Any]] = Field(
        default_factory=list, description="Context retrieved from vector memory"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class TaskDefinition(BaseModel):
    """
    Definition of a task to be executed.

    Tasks are the unit of work in the framework. They can be:
    - Direct tasks (single agent)
    - Multi-step tasks (decomposed by orchestrator)
    """

    task_id: UUID = Field(default_factory=uuid4)

    # Task identification
    title: str = Field(..., description="Short task title")
    description: str = Field(..., description="Detailed task description")

    # Routing
    required_capabilities: Set[AgentCapability] = Field(
        default_factory=set, description="Required capabilities to execute"
    )
    suggested_agent: Optional[AgentRole] = Field(
        default=None, description="Suggested agent for routing"
    )

    # Priority and status
    priority: TaskPriority = Field(default=TaskPriority.NORMAL)
    status: TaskStatus = Field(default=TaskStatus.PENDING)

    # Context
    project_id: UUID = Field(..., description="Associated project")
    session_id: UUID = Field(..., description="Associated session")
    parent_task_id: Optional[UUID] = Field(
        default=None, description="Parent task if this is a subtask"
    )

    # Dependencies
    depends_on: List[UUID] = Field(
        default_factory=list, description="Task IDs that must complete first"
    )

    # Input/Output
    input_context: Dict[str, Any] = Field(
        default_factory=dict, description="Input data and context"
    )
    output: Optional[Dict[str, Any]] = Field(
        default=None, description="Task output after completion"
    )

    # Error handling
    error: Optional[str] = Field(default=None)
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    class Config:
        use_enum_values = True


class AgentResult(BaseModel):
    """
    Result from an agent execution.

    Contains the output, metadata, and any follow-up actions
    required after agent execution.
    """

    success: bool = Field(..., description="Whether execution succeeded")

    # Output
    content: str = Field(default="", description="Main output content")
    structured_output: Optional[Dict[str, Any]] = Field(
        default=None, description="Structured output (e.g., code, configs)"
    )

    # Generated artifacts
    files_created: List[str] = Field(default_factory=list, description="Files created by this task")
    files_modified: List[str] = Field(
        default_factory=list, description="Files modified by this task"
    )

    # Follow-up
    next_actions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Suggested follow-up actions"
    )
    delegate_to: Optional[AgentRole] = Field(
        default=None, description="Agent to delegate to (if needed)"
    )

    # Context to persist
    context_updates: Dict[str, Any] = Field(
        default_factory=dict, description="Updates to project context"
    )
    memory_entries: List[Dict[str, Any]] = Field(
        default_factory=list, description="Entries to add to memory"
    )

    # Metadata
    agent: AgentRole = Field(..., description="Agent that produced this result")
    model_used: str = Field(..., description="LLM model used")
    tokens_used: int = Field(default=0, description="Total tokens consumed")
    execution_time_ms: int = Field(default=0, description="Execution time in milliseconds")

    # Error info
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_details: Optional[Dict[str, Any]] = Field(default=None)

    class Config:
        use_enum_values = True


class Message(BaseModel):
    """
    A message in the conversation.

    Messages are the atomic unit of conversation history
    and are stored in both episodic and semantic memory.
    """

    message_id: UUID = Field(default_factory=uuid4)
    session_id: UUID = Field(..., description="Associated session")

    # Content
    role: MessageType = Field(..., description="Message role")
    content: str = Field(..., description="Message content")

    # Metadata
    agent: Optional[AgentRole] = Field(default=None, description="Agent role if role=assistant")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Token tracking
    tokens: int = Field(default=0, description="Tokens in this message")

    # Embedding reference (for vector memory)
    embedding_id: Optional[str] = Field(default=None, description="Reference to stored embedding")

    class Config:
        use_enum_values = True


class MemoryEntry(BaseModel):
    """
    An entry in the vector memory store.

    Memory entries can be:
    - Conversations (episodic)
    - Knowledge (semantic)
    - Procedures (procedural)
    - Project config (project)
    """

    entry_id: UUID = Field(default_factory=uuid4)

    # Classification
    memory_type: MemoryType = Field(..., description="Type of memory")
    project_id: UUID = Field(..., description="Associated project")

    # Content
    content: str = Field(..., description="Text content")
    embedding: Optional[List[float]] = Field(default=None, description="Vector embedding")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Source tracking
    source: str = Field(
        default="unknown", description="Source of this memory (agent, user, system)"
    )
    source_id: Optional[UUID] = Field(
        default=None, description="ID of source object (message, task, etc.)"
    )

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(
        default=None, description="Expiration time for short-term memory"
    )

    # Access tracking
    access_count: int = Field(default=0, description="Times this entry was retrieved")
    last_accessed: Optional[datetime] = Field(default=None)

    class Config:
        use_enum_values = True


# ============================================================================
# Dataclasses for internal use
# ============================================================================


@dataclass
class ModelConfig:
    """Configuration for a specific LLM model."""

    name: str
    provider: str = "ollama"
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9

    # Capability mapping
    capabilities: List[AgentCapability] = field(default_factory=list)

    # Cost tracking
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
    """Main output content."""

    artifacts: Dict[str, Any] = field(default_factory=dict)
    """Generated artifacts."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""

    errors: List[str] = field(default_factory=list)
    """Error messages if any."""

    agent_results: List[AgentResult] = field(default_factory=list)
    """Results from individual agents involved."""

    execution_time_ms: int = 0
    """Execution time in milliseconds."""

    tokens_used: int = 0
    """Total tokens consumed."""

    model_used: str = ""
    """Primary LLM model used."""


# ============================================================================
# Type Aliases
# ============================================================================

# For clarity in function signatures
TaskId = UUID
ProjectId = UUID
SessionId = UUID
MessageId = UUID
EntryId = UUID
