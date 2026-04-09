"""
Core base classes for the Palace Framework.

This module defines the fundamental abstractions that all agents, tasks,
and results must implement. These base classes establish the contracts
and interfaces that enable the multi-agent orchestration system.

Classes:
    - AgentBase: Abstract base class for all specialized agents
    - TaskBase: Abstract base class for tasks
    - ResultBase: Abstract base class for execution results
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from palace.context import SessionContext
    from palace.memory import MemoryStore
    from palace.models.schemas import AgentCapability

# Generic types for results
T = TypeVar("T")
R = TypeVar("R")


class TaskStatus(str, Enum):
    """Status of a task in the execution pipeline."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"
    DELEGATED = "delegated"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Priority levels for task scheduling."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ResultStatus(str, Enum):
    """Status of an execution result."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    REQUIRES_FEEDBACK = "requires_feedback"
    DELEGATED = "delegated"


@dataclass
class TaskBase(ABC):
    """
    Abstract base class for all tasks in the framework.

    A task represents a unit of work that can be executed by an agent.
    Tasks contain the prompt/instruction, context references, and metadata
    needed for execution.

    Attributes:
        task_id: Unique identifier for the task
        prompt: The main instruction or question for the agent
        project_id: Identifier of the project context
        session_id: Identifier of the conversation session
        status: Current status of the task
        priority: Priority level for task scheduling
        created_at: Timestamp when the task was created
        updated_at: Timestamp when the task was last updated
        parent_task_id: Optional ID of parent task (for subtasks)
        assigned_agent: Name of the agent assigned to this task
        metadata: Additional metadata for the task
    """

    task_id: str
    prompt: str
    project_id: str
    session_id: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    parent_task_id: str | None = None
    assigned_agent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def update_status(self, new_status: TaskStatus) -> None:
        """Update the task status and timestamp."""
        self.status = new_status
        self.updated_at = datetime.utcnow()

    def assign_to(self, agent_name: str) -> None:
        """Assign the task to a specific agent."""
        self.assigned_agent = agent_name
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the task to a dictionary."""
        return {
            "task_id": self.task_id,
            "prompt": self.prompt,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "parent_task_id": self.parent_task_id,
            "assigned_agent": self.assigned_agent,
            "metadata": self.metadata,
        }


@dataclass
class ResultBase(ABC, Generic[T]):
    """
    Abstract base class for execution results.

    A result contains the output of an agent's execution, along with
    status, metadata, and optional sub-results from delegated tasks.

    Attributes:
        result_id: Unique identifier for this result
        task_id: ID of the task that produced this result
        agent_name: Name of the agent that produced this result
        status: Status of the result
        output: The main output content
        artifacts: List of generated artifacts (files, code, etc.)
        metadata: Additional metadata
        created_at: Timestamp when the result was created
        sub_results: List of results from delegated subtasks
        errors: List of errors encountered during execution
        suggestions: Optional suggestions for improvement
    """

    result_id: str
    task_id: str
    agent_name: str
    status: ResultStatus
    output: T
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    sub_results: list["ResultBase[Any]"] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def is_success(self) -> bool:
        """Check if the result represents a successful execution."""
        return self.status in (ResultStatus.SUCCESS, ResultStatus.PARTIAL_SUCCESS)

    def has_artifacts(self) -> bool:
        """Check if the result contains any artifacts."""
        return len(self.artifacts) > 0

    def add_sub_result(self, result: "ResultBase[Any]") -> None:
        """Add a sub-result from a delegated task."""
        self.sub_results.append(result)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the result to a dictionary."""
        return {
            "result_id": self.result_id,
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "status": self.status.value,
            "output": self.output,
            "artifacts": self.artifacts,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "sub_results": [r.to_dict() for r in self.sub_results],
            "errors": self.errors,
            "suggestions": self.suggestions,
        }


class AgentBase(ABC):
    """
    Abstract base class for all specialized agents.

    All agents in the Palace framework must inherit from this class and
    implement its abstract methods. The base class provides common
    functionality for tool management, context handling, and result creation.

    Attributes:
        name: Unique name identifier for the agent
        model: The LLM model to use (e.g., 'qwen3-coder-next')
        capabilities: List of capabilities this agent possesses
        system_prompt: The system prompt that defines agent behavior
        description: Human-readable description of the agent's purpose
        tools: List of tools available to this agent
    """

    name: str
    model: str
    capabilities: list["AgentCapability"]
    system_prompt: str
    description: str
    tools: list[str] = []

    @abstractmethod
    async def execute(
        self,
        task: TaskBase,
        context: "SessionContext",
        memory: "MemoryStore",
    ) -> ResultBase[Any]:
        """
        Execute a task and return the result.

        This is the main entry point for agent execution. Implementations
        should:
        1. Retrieve relevant context from memory
        2. Call the LLM with the appropriate prompt
        3. Process the response and create artifacts
        4. Return a ResultBase with the output

        Args:
            task: The task to execute
            context: The session context with project information
            memory: The memory store for context retrieval

        Returns:
            A ResultBase containing the execution output
        """
        pass

    @abstractmethod
    async def can_handle(self, task: TaskBase) -> bool:
        """
        Determine if this agent can handle the given task.

        This method should analyze the task prompt and determine if
        the agent has the necessary capabilities to handle it.

        Args:
            task: The task to evaluate

        Returns:
            True if the agent can handle the task, False otherwise
        """
        pass

    def get_tools(self) -> list[str]:
        """Return the list of tools available to this agent."""
        return self.tools

    def get_capabilities(self) -> list["AgentCapability"]:
        """Return the list of capabilities this agent has."""
        return self.capabilities

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', model='{self.model}')>"


class ToolBase(ABC):
    """
    Abstract base class for tools that agents can use.

    Tools are reusable components that provide specific functionality
    like file operations, shell commands, or API calls.

    Attributes:
        name: Unique name for the tool
        description: Human-readable description of what the tool does
        parameters_schema: JSON schema for the tool's parameters
    """

    name: str
    description: str
    parameters_schema: dict[str, Any]

    @abstractmethod
    async def execute(self, **params: Any) -> Any:
        """
        Execute the tool with the given parameters.

        Args:
            **params: Tool-specific parameters

        Returns:
            The result of the tool execution
        """
        pass

    @abstractmethod
    def validate_params(self, **params: Any) -> bool:
        """
        Validate the parameters against the schema.

        Args:
            **params: Parameters to validate

        Returns:
            True if parameters are valid, False otherwise
        """
        pass
