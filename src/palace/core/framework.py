"""
Palace Framework - Main Entry Point

This module defines the main PalaceFramework class that serves as the primary
interface for the multi-agent software development framework.
"""

from typing import Optional

from palace.config import Settings, get_settings
from palace.context import ContextManager
from palace.core.orchestrator import Orchestrator
from palace.memory import MemoryStore


class PalaceFramework:
    """
    Main entry point for the Palace multi-agent framework.

    This class coordinates all framework components and provides a unified
    interface for executing tasks through the agent orchestration system.

    Attributes:
        settings: Framework configuration settings
        orchestrator: Central task orchestrator
        memory: Vector memory store for context retrieval
        context: Project and session context manager

    Example:
        >>> framework = PalaceFramework()
        >>> result = await framework.execute(
        ...     project_id="my-project",
        ...     task="Create a REST endpoint for user management"
        ... )
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        memory_store: Optional[MemoryStore] = None,
    ) -> None:
        """
        Initialize the Palace framework.

        Args:
            settings: Optional custom settings. If not provided, uses
                environment variables and default configuration.
            memory_store: Optional custom memory store. If not provided,
                creates a default memory store based on settings.
        """
        self.settings = settings or get_settings()
        self._memory_store = memory_store
        self._orchestrator: Optional[Orchestrator] = None
        self._context_manager: Optional[ContextManager] = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize all framework components.

        This method must be called before executing any tasks.
        It sets up the memory store, context manager, and orchestrator.
        """
        if self._initialized:
            return

        # Initialize memory store
        if self._memory_store is None:
            self._memory_store = MemoryStore.create(self.settings)
        await self._memory_store.initialize()

        # Initialize context manager
        self._context_manager = ContextManager(
            memory_store=self._memory_store,
            settings=self.settings,
        )
        await self._context_manager.initialize()

        # Initialize orchestrator
        self._orchestrator = Orchestrator(
            memory_store=self._memory_store,
            context_manager=self._context_manager,
            settings=self.settings,
        )
        await self._orchestrator.initialize()

        self._initialized = True

    async def execute(
        self,
        task: str,
        project_id: str,
        session_id: Optional[str] = None,
        agent_hint: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> "ExecutionResult":
        """
        Execute a task through the framework.

        The orchestrator will analyze the task, route it to the appropriate
        agent(s), and return the result.

        Args:
            task: The task description or prompt
            project_id: Project identifier for context isolation
            session_id: Optional session identifier for conversation continuity
            agent_hint: Optional hint for which agent to use
            context: Additional context data for the task

        Returns:
            ExecutionResult containing the task result and metadata

        Raises:
            FrameworkNotInitializedError: If framework was not initialized
            TaskExecutionError: If task execution fails
        """
        if not self._initialized:
            await self.initialize()

        return await self._orchestrator.execute_task(
            task=task,
            project_id=project_id,
            session_id=session_id,
            agent_hint=agent_hint,
            context=context,
        )

    async def get_project_status(self, project_id: str) -> "ProjectStatus":
        """
        Get the current status of a project.

        Args:
            project_id: Project identifier

        Returns:
            ProjectStatus with project state information
        """
        if not self._initialized:
            await self.initialize()

        return await self._context_manager.get_project_status(project_id)

    async def list_agents(self) -> list[str]:
        """
        List all available agents in the framework.

        Returns:
            List of agent names
        """
        if not self._initialized:
            await self.initialize()

        return self._orchestrator.list_agents()

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the framework.

        Closes all resources, connections, and cleanup tasks.
        """
        if self._orchestrator:
            await self._orchestrator.shutdown()
        if self._context_manager:
            await self._context_manager.shutdown()
        if self._memory_store:
            await self._memory_store.close()

        self._initialized = False


class ExecutionResult:
    """
    Result of a task execution.

    Attributes:
        task_id: Unique identifier for the executed task
        status: Execution status (success, failed, pending)
        result: The actual result content
        agent_used: Name of the agent that executed the task
        execution_time: Time taken to execute in seconds
        metadata: Additional execution metadata
    """

    def __init__(
        self,
        task_id: str,
        status: str,
        result: str,
        agent_used: str,
        execution_time: float,
        metadata: Optional[dict] = None,
    ) -> None:
        self.task_id = task_id
        self.status = status
        self.result = result
        self.agent_used = agent_used
        self.execution_time = execution_time
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        """Convert result to dictionary representation."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "result": self.result,
            "agent_used": self.agent_used,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
        }


class ProjectStatus:
    """
    Status information for a project.

    Attributes:
        project_id: Project identifier
        status: Current project status
        active_tasks: Number of active tasks
        last_activity: Timestamp of last activity
        context_summary: Summary of project context
    """

    def __init__(
        self,
        project_id: str,
        status: str,
        active_tasks: int,
        last_activity: str,
        context_summary: Optional[str] = None,
    ) -> None:
        self.project_id = project_id
        self.status = status
        self.active_tasks = active_tasks
        self.last_activity = last_activity
        self.context_summary = context_summary

    def to_dict(self) -> dict:
        """Convert status to dictionary representation."""
        return {
            "project_id": self.project_id,
            "status": self.status,
            "active_tasks": self.active_tasks,
            "last_activity": self.last_activity,
            "context_summary": self.context_summary,
        }
