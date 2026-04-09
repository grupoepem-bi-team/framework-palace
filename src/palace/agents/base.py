"""
Palace Framework - Agent Base Module

This module provides the base class for all agents in the Palace framework.
All specialized agents (Orchestrator, Backend, Frontend, etc.) inherit from
AgentBase and implement their specific behaviors.

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                        AgentBase                             │
    │  ┌─────────────────────────────────────────────────────┐   │
    │  │                  Core Properties                      │   │
    │  │  - name, role, model, capabilities                   │   │
    │  │  - system_prompt, tools                               │   │
    │  └─────────────────────────────────────────────────────┘   │
    │  ┌─────────────────────────────────────────────────────┐   │
    │  │                  Core Methods                         │   │
    │  │  - run(task, context, memory) → Result               │   │
    │  │  - can_handle(task) → bool                           │   │
    │  │  - get_context(memory, project) → str                │   │
    │  │  - build_prompt(task, context) → str                 │   │
    │  │  - parse_response(response) → Result                │   │
    │  └─────────────────────────────────────────────────────┘   │
    │  ┌─────────────────────────────────────────────────────┐   │
    │  │                  LLM Integration                      │   │
    │  │  - llm_client: LLMClient                            │   │
    │  │  - invoke_llm(prompt) → str                         │   │
    │  │  - stream_llm(prompt) → AsyncIterator               │   │
    │  └─────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────┘
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, List, Optional

import structlog

if TYPE_CHECKING:
    from palace.context import ProjectContext, SessionContext
    from palace.llm import LLMClient
    from palace.memory import MemoryStore

logger = structlog.get_logger()


# =============================================================================
# Enums and Types
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


class AgentState(str, Enum):
    """Possible states for an agent."""

    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    INITIALIZING = "initializing"


class TaskPriority(str, Enum):
    """Priority levels for tasks."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REVIEW = "review"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class AgentCapabilities:
    """Capabilities of an agent."""

    code_generation: bool = False
    code_review: bool = False
    testing: bool = False
    documentation: bool = False
    deployment: bool = False
    database: bool = False
    infrastructure: bool = False
    planning: bool = False
    orchestration: bool = False
    design: bool = False

    def to_list(self) -> List[str]:
        """Convert capabilities to list of strings."""
        capabilities = []
        if self.code_generation:
            capabilities.append("code_generation")
        if self.code_review:
            capabilities.append("code_review")
        if self.testing:
            capabilities.append("testing")
        if self.documentation:
            capabilities.append("documentation")
        if self.deployment:
            capabilities.append("deployment")
        if self.database:
            capabilities.append("database")
        if self.infrastructure:
            capabilities.append("infrastructure")
        if self.planning:
            capabilities.append("planning")
        if self.orchestration:
            capabilities.append("orchestration")
        if self.design:
            capabilities.append("design")
        return capabilities


@dataclass
class Task:
    """A task to be executed by an agent."""

    task_id: str
    description: str
    project_id: str
    session_id: Optional[str] = None
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    parent_task_id: Optional[str] = None
    assigned_agent: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "priority": self.priority.value,
            "status": self.status.value,
            "context": self.context,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "parent_task_id": self.parent_task_id,
            "assigned_agent": self.assigned_agent,
        }


@dataclass
class AgentResult:
    """Result of an agent execution."""

    success: bool
    content: str
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)
    tokens_used: int = 0
    execution_time_ms: int = 0
    model_used: str = ""
    agent_name: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "content": self.content,
            "artifacts": self.artifacts,
            "metadata": self.metadata,
            "errors": self.errors,
            "suggestions": self.suggestions,
            "next_actions": self.next_actions,
            "tokens_used": self.tokens_used,
            "execution_time_ms": self.execution_time_ms,
            "model_used": self.model_used,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AgentInfo:
    """Information about an agent."""

    name: str
    role: AgentRole
    model: str
    description: str
    capabilities: AgentCapabilities
    tools: List[str] = field(default_factory=list)
    system_prompt: str = ""
    state: AgentState = AgentState.IDLE

    def to_dict(self) -> Dict[str, Any]:
        """Convert agent info to dictionary."""
        return {
            "name": self.name,
            "role": self.role.value,
            "model": self.model,
            "description": self.description,
            "capabilities": self.capabilities.to_list(),
            "tools": self.tools,
            "system_prompt": self.system_prompt[:200] + "..." if len(self.system_prompt) > 200 else self.system_prompt,
            "state": self.state.value,
        }


# =============================================================================
# Agent Base Class
# =============================================================================


class AgentBase(ABC):
    """
    Base class for all agents in the Palace framework.

    This abstract class defines the interface and common functionality
    that all specialized agents must implement. Each agent has:
    - A specific role and model assignment
    - Custom system prompts
    - Tools and capabilities
    - Context retrieval and prompt building
    - LLM invocation through the router

    Agents are responsible for:
    - Receiving tasks from the orchestrator
    - Retrieving relevant context from memory
    - Building prompts with context and instructions
    - Invoking the LLM through the router
    - Parsing responses and creating results

    Example:
        ```python
        class BackendAgent(AgentBase):
            def __init__(self, llm_client: LLMClient):
                super().__init__(
                    name="backend",
                    role=AgentRole.BACKEND,
                    model="qwen3-coder-next",
                    llm_client=llm_client,
                )

            async def run(self, task: Task, context: SessionContext, memory: MemoryStore) -> AgentResult:
                # Build prompt
                prompt = self.build_prompt(task, context)

                # Invoke LLM
                response = await self.invoke_llm(prompt)

                # Parse result
                return self.parse_response(response)
        ```
    """

    def __init__(
        self,
        name: str,
        role: AgentRole,
        model: str,
        llm_client: "LLMClient",
        capabilities: Optional[AgentCapabilities] = None,
        tools: Optional[List[str]] = None,
    ):
        """
        Initialize the agent.

        Args:
            name: Unique name for this agent
            role: Agent role
            model: LLM model to use
            llm_client: LLM client for invoking models
            capabilities: Agent capabilities
            tools: List of available tools
        """
        self.name = name
        self.role = role
        self.model = model
        self.llm_client = llm_client
        self.capabilities = capabilities or AgentCapabilities()
        self.tools = tools or []
        self.state = AgentState.IDLE
        self._system_prompt = self._build_system_prompt()

        logger.info(
            "agent_initialized",
            name=name,
            role=role.value,
            model=model,
            capabilities=self.capabilities.to_list(),
        )

    # -------------------------------------------------------------------------
    # Abstract Methods (must be implemented by subclasses)
    # -------------------------------------------------------------------------

    @abstractmethod
    async def run(
        self,
        task: Task,
        context: "SessionContext",
        memory: "MemoryStore",
    ) -> AgentResult:
        """
        Execute a task and return the result.

        This is the main entry point for agent execution. Subclasses
        must implement this method to define their specific behavior.

        Args:
            task: The task to execute
            context: Session context with project information
            memory: Memory store for context retrieval

        Returns:
            AgentResult with the execution result
        """
        pass

    @abstractmethod
    def can_handle(self, task: Task) -> bool:
        """
        Determine if this agent can handle the given task.

        Args:
            task: The task to evaluate

        Returns:
            True if this agent can handle the task
        """
        pass

    @abstractmethod
    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for this agent.

        Returns:
            System prompt string
        """
        pass

    # -------------------------------------------------------------------------
    # Core Methods
    # -------------------------------------------------------------------------

    async def invoke_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Invoke the LLM with a prompt.

        Args:
            prompt: The prompt to send
            system_prompt: Optional system prompt override
            temperature: Optional temperature override
            max_tokens: Optional max tokens override

        Returns:
            LLM response content
        """
        if system_prompt is None:
            system_prompt = self._system_prompt

        logger.debug(
            "agent_invoking_llm",
            agent=self.name,
            model=self.model,
            prompt_length=len(prompt),
        )

        result = await self.llm_client.invoke(
            prompt=prompt,
            role=self.role.value,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        logger.info(
            "agent_llm_response",
            agent=self.name,
            model=result.model,
            tokens=result.tokens_total,
            latency_ms=result.latency_seconds * 1000,
        )

        return result.content

    async def stream_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Stream response from the LLM.

        Args:
            prompt: The prompt to send
            system_prompt: Optional system prompt override
            temperature: Optional temperature override
            max_tokens: Optional max tokens override

        Yields:
            Chunks of the response
        """
        if system_prompt is None:
            system_prompt = self._system_prompt

        logger.debug(
            "agent_streaming_llm",
            agent=self.name,
            model=self.model,
        )

        async for chunk in self.llm_client.stream(
            prompt=prompt,
            role=self.role.value,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield chunk

    async def get_context(
        self,
        task: Task,
        memory: "MemoryStore",
        max_contexts: int = 5,
    ) -> str:
        """
        Retrieve relevant context from memory for a task.

        Args:
            task: The task to get context for
            memory: Memory store
            max_contexts: Maximum number of context items

        Returns:
            Formatted context string
        """
        try:
            # Search for relevant context
            contexts = await memory.retrieve_context(
                project_id=task.project_id,
                query=task.description,
                top_k=max_contexts,
            )

            if not contexts:
                return ""

            # Format context
            formatted_contexts = []
            for i, ctx in enumerate(contexts, 1):
                content = ctx.get("content", "")
                source = ctx.get("source", "unknown")
                formatted_contexts.append(f"[{i}] ({source}): {content}")

            return "\n\n".join(formatted_contexts)

        except Exception as e:
            logger.warning(
                "agent_context_retrieval_failed",
                agent=self.name,
                task_id=task.task_id,
                error=str(e),
            )
            return ""

    def build_prompt(
        self,
        task: Task,
        context_str: str = "",
        additional_instructions: str = "",
    ) -> str:
        """
        Build the complete prompt for the LLM.

        Args:
            task: The task to execute
            context_str: Retrieved context from memory
            additional_instructions: Additional instructions

        Returns:
            Complete prompt string
        """
        prompt_parts = []

        # Task description
        prompt_parts.append(f"## Task\n{task.description}\n")

        # Context if available
        if context_str:
            prompt_parts.append(f"## Context\n{context_str}\n")

        # Task context (project-specific)
        if task.context:
            if "files" in task.context:
                prompt_parts.append("## Relevant Files")
                for file_path, content in task.context["files"].items():
                    prompt_parts.append(f"### {file_path}\n```\n{content}\n```\n")

            if "requirements" in task.context:
                prompt_parts.append(f"## Requirements\n{task.context['requirements']}\n")

        # Additional instructions
        if additional_instructions:
            prompt_parts.append(f"## Instructions\n{additional_instructions}\n")

        # Output format
        prompt_parts.append(self._get_output_format())

        return "\n".join(prompt_parts)

    def _get_output_format(self) -> str:
        """
        Get the expected output format for this agent.

        Returns:
            Output format instructions
        """
        return """## Output Format
Provide your response in the following format:

1. **Analysis**: Brief analysis of the task
2. **Implementation**: Detailed implementation (code, configuration, etc.)
3. **Files**: List of files to create/modify
4. **Tests**: Test cases to verify the implementation
5. **Notes**: Any important notes or considerations"""

    def parse_response(self, response: str) -> AgentResult:
        """
        Parse the LLM response into a structured result.

        Args:
            response: Raw response from LLM

        Returns:
            Structured AgentResult
        """
        # Default implementation - subclasses can override
        return AgentResult(
            success=True,
            content=response,
            agent_name=self.name,
            model_used=self.model,
        )

    def get_info(self) -> AgentInfo:
        """
        Get information about this agent.

        Returns:
            AgentInfo with agent details
        """
        return AgentInfo(
            name=self.name,
            role=self.role,
            model=self.model,
            description=self._get_description(),
            capabilities=self.capabilities,
            tools=self.tools,
            system_prompt=self._system_prompt,
            state=self.state,
        )

    @abstractmethod
    def _get_description(self) -> str:
        """
        Get a description of this agent.

        Returns:
            Agent description string
        """
        pass

    # -------------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------------

    def set_state(self, state: AgentState) -> None:
        """
        Set the agent state.

        Args:
            state: New state
        """
        self.state = state
        logger.debug("agent_state_changed", agent=self.name, state=state.value)

    def is_busy(self) -> bool:
        """Check if agent is busy."""
        return self.state == AgentState.BUSY

    def is_available(self) -> bool:
        """Check if agent is available for tasks."""
        return self.state == AgentState.IDLE

    # -------------------------------------------------------------------------
    # Special Methods
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', role='{self.role.value}', model='{self.model}')>"

    def __str__(self) -> str:
        return f"{self.name} ({self.role.value})"

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AgentBase):
            return False
        return self.name == other.name
```
Respondo con la implementación completa del archivo `base.py` para los agentes del framework Palace.
