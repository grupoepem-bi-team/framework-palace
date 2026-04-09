"""
Palace Framework - Custom Exceptions

This module defines all custom exceptions used throughout the framework.
Exceptions are organized hierarchically for easy catching and handling.

Hierarchy:
    PalaceError (base)
    ├── ConfigurationError
    │   ├── MissingConfigError
    │   └── InvalidConfigError
    ├── AgentError
    │   ├── AgentNotFoundError
    │   ├── AgentExecutionError
    │   ├── AgentTimeoutError
    │   └── AgentCapabilityError
    ├── OrchestratorError
    │   ├── TaskRoutingError
    │   ├── TaskExecutionError
    │   └── WorkflowError
    ├── MemoryError
    │   ├── MemoryStoreError
    │   ├── MemoryRetrievalError
    │   └── EmbeddingError
    ├── ContextError
    │   ├── ProjectNotFoundError
    │   ├── SessionNotFoundError
    │   └── ContextRetrievalError
    ├── ToolError
    │   ├── ToolNotFoundError
    │   ├── ToolExecutionError
    │   └── ToolTimeoutError
    ├── APIError
    │   ├── AuthenticationError
    │   ├── AuthorizationError
    │   └── RateLimitError
    └── PipelineError
        ├── PipelineNotFoundError
        └── PipelineExecutionError
"""

from typing import Any, Optional


class PalaceError(Exception):
    """
    Base exception for all Palace framework errors.

    All custom exceptions in the framework should inherit from this class
    to allow for broad exception catching when needed.

    Attributes:
        message: Human-readable error description
        code: Machine-readable error code for programmatic handling
        details: Optional dictionary with additional error context
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"[{self.code}] {self.message} - Details: {self.details}"
        return f"[{self.code}] {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(PalaceError):
    """Base exception for configuration-related errors."""

    pass


class MissingConfigError(ConfigurationError):
    """Raised when a required configuration is missing."""

    def __init__(
        self,
        config_key: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.config_key = config_key
        message = message or f"Missing required configuration: {config_key}"
        details = details or {}
        details["config_key"] = config_key
        super().__init__(message, code="MISSING_CONFIG", details=details)


class InvalidConfigError(ConfigurationError):
    """Raised when a configuration value is invalid."""

    def __init__(
        self,
        config_key: str,
        value: Any,
        reason: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.config_key = config_key
        self.value = value
        self.reason = reason
        message = f"Invalid configuration for '{config_key}': {reason}"
        details = details or {}
        details.update({"config_key": config_key, "value": str(value), "reason": reason})
        super().__init__(message, code="INVALID_CONFIG", details=details)


# =============================================================================
# Agent Errors
# =============================================================================


class AgentError(PalaceError):
    """Base exception for agent-related errors."""

    def __init__(
        self,
        agent_name: str,
        message: str,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.agent_name = agent_name
        details = details or {}
        details["agent_name"] = agent_name
        super().__init__(message, code=code, details=details)


class AgentNotFoundError(AgentError):
    """Raised when a requested agent is not registered."""

    def __init__(self, agent_name: str, available_agents: Optional[list[str]] = None) -> None:
        available_agents = available_agents or []
        message = f"Agent '{agent_name}' not found. Available agents: {', '.join(available_agents) or 'none'}"
        details = {"available_agents": available_agents}
        super().__init__(agent_name, message, code="AGENT_NOT_FOUND", details=details)


class AgentExecutionError(AgentError):
    """Raised when an agent fails to execute a task."""

    def __init__(
        self,
        agent_name: str,
        task_id: str,
        reason: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.task_id = task_id
        message = f"Agent '{agent_name}' failed to execute task '{task_id}': {reason}"
        details = details or {}
        details.update({"task_id": task_id, "reason": reason})
        super().__init__(agent_name, message, code="AGENT_EXECUTION_ERROR", details=details)


class AgentTimeoutError(AgentError):
    """Raised when an agent execution times out."""

    def __init__(
        self,
        agent_name: str,
        task_id: str,
        timeout_seconds: float,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.task_id = task_id
        self.timeout_seconds = timeout_seconds
        message = f"Agent '{agent_name}' timed out after {timeout_seconds}s on task '{task_id}'"
        details = details or {}
        details.update({"task_id": task_id, "timeout_seconds": timeout_seconds})
        super().__init__(agent_name, message, code="AGENT_TIMEOUT", details=details)


class AgentCapabilityError(AgentError):
    """Raised when an agent doesn't have the required capability."""

    def __init__(
        self,
        agent_name: str,
        required_capability: str,
        available_capabilities: list[str],
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.required_capability = required_capability
        self.available_capabilities = available_capabilities
        message = (
            f"Agent '{agent_name}' lacks capability '{required_capability}'. "
            f"Available: {', '.join(available_capabilities) or 'none'}"
        )
        details = details or {}
        details.update(
            {
                "required_capability": required_capability,
                "available_capabilities": available_capabilities,
            }
        )
        super().__init__(agent_name, message, code="AGENT_CAPABILITY_ERROR", details=details)


# =============================================================================
# Orchestrator Errors
# =============================================================================


class OrchestratorError(PalaceError):
    """Base exception for orchestrator-related errors."""

    pass


class TaskRoutingError(OrchestratorError):
    """Raised when the orchestrator cannot route a task to any agent."""

    def __init__(
        self,
        task_description: str,
        reason: str,
        candidate_agents: Optional[list[str]] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.task_description = task_description
        self.reason = reason
        candidate_agents = candidate_agents or []
        message = f"Cannot route task '{task_description[:50]}...': {reason}"
        details = details or {}
        details.update({"reason": reason, "candidate_agents": candidate_agents})
        super().__init__(message, code="TASK_ROUTING_ERROR", details=details)


class TaskExecutionError(OrchestratorError):
    """Raised when task execution fails at the orchestrator level."""

    def __init__(
        self,
        task_id: str,
        stage: str,
        reason: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.task_id = task_id
        self.stage = stage
        self.reason = reason
        message = f"Task '{task_id}' failed at stage '{stage}': {reason}"
        details = details or {}
        details.update({"task_id": task_id, "stage": stage, "reason": reason})
        super().__init__(message, code="TASK_EXECUTION_ERROR", details=details)


class WorkflowError(OrchestratorError):
    """Raised when a workflow execution fails."""

    def __init__(
        self,
        workflow_name: str,
        step: int,
        reason: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.workflow_name = workflow_name
        self.step = step
        self.reason = reason
        message = f"Workflow '{workflow_name}' failed at step {step}: {reason}"
        details = details or {}
        details.update({"workflow_name": workflow_name, "step": step, "reason": reason})
        super().__init__(message, code="WORKFLOW_ERROR", details=details)


# =============================================================================
# Memory Errors
# =============================================================================


class MemoryError(PalaceError):
    """Base exception for memory-related errors."""

    pass


class MemoryStoreError(MemoryError):
    """Raised when storing data in memory fails."""

    def __init__(
        self,
        operation: str,
        reason: str,
        memory_type: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.operation = operation
        self.reason = reason
        self.memory_type = memory_type
        message = f"Memory store error during '{operation}': {reason}"
        details = details or {}
        details.update({"operation": operation, "reason": reason})
        if memory_type:
            details["memory_type"] = memory_type
        super().__init__(message, code="MEMORY_STORE_ERROR", details=details)


class MemoryRetrievalError(MemoryError):
    """Raised when retrieving data from memory fails."""

    def __init__(
        self,
        query: str,
        reason: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.query = query
        self.reason = reason
        message = f"Memory retrieval failed for query '{query[:50]}...': {reason}"
        details = details or {}
        details.update({"query": query, "reason": reason})
        super().__init__(message, code="MEMORY_RETRIEVAL_ERROR", details=details)


class EmbeddingError(MemoryError):
    """Raised when embedding generation fails."""

    def __init__(
        self,
        text_length: int,
        model: str,
        reason: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.text_length = text_length
        self.model = model
        self.reason = reason
        message = f"Embedding generation failed with model '{model}': {reason}"
        details = details or {}
        details.update({"text_length": text_length, "model": model, "reason": reason})
        super().__init__(message, code="EMBEDDING_ERROR", details=details)


# =============================================================================
# Context Errors
# =============================================================================


class ContextError(PalaceError):
    """Base exception for context-related errors."""

    pass


class ProjectNotFoundError(ContextError):
    """Raised when a project is not found."""

    def __init__(
        self,
        project_id: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.project_id = project_id
        message = f"Project '{project_id}' not found"
        details = details or {}
        details["project_id"] = project_id
        super().__init__(message, code="PROJECT_NOT_FOUND", details=details)


class SessionNotFoundError(ContextError):
    """Raised when a session is not found."""

    def __init__(
        self,
        session_id: str,
        project_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.session_id = session_id
        self.project_id = project_id
        message = f"Session '{session_id}' not found"
        details = details or {}
        details["session_id"] = session_id
        if project_id:
            details["project_id"] = project_id
            message = f"Session '{session_id}' not found in project '{project_id}'"
        super().__init__(message, code="SESSION_NOT_FOUND", details=details)


class ContextRetrievalError(ContextError):
    """Raised when context retrieval fails."""

    def __init__(
        self,
        context_type: str,
        reason: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.context_type = context_type
        self.reason = reason
        message = f"Failed to retrieve {context_type} context: {reason}"
        details = details or {}
        details.update({"context_type": context_type, "reason": reason})
        super().__init__(message, code="CONTEXT_RETRIEVAL_ERROR", details=details)


# =============================================================================
# Tool Errors
# =============================================================================


class ToolError(PalaceError):
    """Base exception for tool-related errors."""

    def __init__(
        self,
        tool_name: str,
        message: str,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.tool_name = tool_name
        details = details or {}
        details["tool_name"] = tool_name
        super().__init__(message, code=code, details=details)


class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not registered."""

    def __init__(
        self,
        tool_name: str,
        available_tools: Optional[list[str]] = None,
    ) -> None:
        available_tools = available_tools or []
        message = f"Tool '{tool_name}' not found. Available: {', '.join(available_tools) or 'none'}"
        details = {"available_tools": available_tools}
        super().__init__(tool_name, message, code="TOOL_NOT_FOUND", details=details)


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""

    def __init__(
        self,
        tool_name: str,
        reason: str,
        exit_code: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.reason = reason
        self.exit_code = exit_code
        message = f"Tool '{tool_name}' execution failed: {reason}"
        details = details or {}
        details.update({"reason": reason})
        if exit_code is not None:
            details["exit_code"] = exit_code
        super().__init__(tool_name, message, code="TOOL_EXECUTION_ERROR", details=details)


class ToolTimeoutError(ToolError):
    """Raised when tool execution times out."""

    def __init__(
        self,
        tool_name: str,
        timeout_seconds: float,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        message = f"Tool '{tool_name}' timed out after {timeout_seconds}s"
        details = details or {}
        details["timeout_seconds"] = timeout_seconds
        super().__init__(tool_name, message, code="TOOL_TIMEOUT", details=details)


# =============================================================================
# API Errors
# =============================================================================


class APIError(PalaceError):
    """Base exception for API-related errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.status_code = status_code
        details = details or {}
        details["status_code"] = status_code
        super().__init__(message, code=code, details=details)


class AuthenticationError(APIError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, status_code=401, code="AUTHENTICATION_ERROR", details=details)


class AuthorizationError(APIError):
    """Raised when authorization fails."""

    def __init__(
        self,
        resource: str,
        action: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.resource = resource
        self.action = action
        message = f"Not authorized to {action} on {resource}"
        details = details or {}
        details.update({"resource": resource, "action": action})
        super().__init__(message, status_code=403, code="AUTHORIZATION_ERROR", details=details)


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        retry_after: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.retry_after = retry_after
        message = "Rate limit exceeded"
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after
            message = f"Rate limit exceeded. Retry after {retry_after} seconds"
        super().__init__(message, status_code=429, code="RATE_LIMIT_ERROR", details=details)


# =============================================================================
# Pipeline Errors
# =============================================================================


class PipelineError(PalaceError):
    """Base exception for pipeline-related errors."""

    pass


class PipelineNotFoundError(PipelineError):
    """Raised when a requested pipeline is not found."""

    def __init__(
        self,
        pipeline_name: str,
        available_pipelines: Optional[list[str]] = None,
    ) -> None:
        self.pipeline_name = pipeline_name
        available_pipelines = available_pipelines or []
        message = (
            f"Pipeline '{pipeline_name}' not found. "
            f"Available: {', '.join(available_pipelines) or 'none'}"
        )
        details = {"available_pipelines": available_pipelines}
        super().__init__(message, code="PIPELINE_NOT_FOUND", details=details)


class PipelineExecutionError(PipelineError):
    """Raised when pipeline execution fails."""

    def __init__(
        self,
        pipeline_name: str,
        step: str,
        reason: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.pipeline_name = pipeline_name
        self.step = step
        self.reason = reason
        message = f"Pipeline '{pipeline_name}' failed at step '{step}': {reason}"
        details = details or {}
        details.update({"pipeline_name": pipeline_name, "step": step, "reason": reason})
        super().__init__(message, code="PIPELINE_EXECUTION_ERROR", details=details)


# =============================================================================
# Model Errors
# =============================================================================


class ModelError(PalaceError):
    """Base exception for LLM model-related errors."""

    def __init__(
        self,
        model: str,
        message: str,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.model = model
        details = details or {}
        details["model"] = model
        super().__init__(message, code=code, details=details)


class ModelNotAvailableError(ModelError):
    """Raised when a requested model is not available."""

    def __init__(
        self,
        model: str,
        available_models: Optional[list[str]] = None,
    ) -> None:
        available_models = available_models or []
        message = (
            f"Model '{model}' is not available. "
            f"Available models: {', '.join(available_models) or 'none'}"
        )
        details = {"available_models": available_models}
        super().__init__(model, message, code="MODEL_NOT_AVAILABLE", details=details)


class ModelResponseError(ModelError):
    """Raised when model response is invalid or cannot be parsed."""

    def __init__(
        self,
        model: str,
        reason: str,
        raw_response: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.reason = reason
        self.raw_response = raw_response
        message = f"Invalid response from model '{model}': {reason}"
        details = details or {}
        details["reason"] = reason
        if raw_response:
            details["raw_response"] = raw_response[:500]  # Truncate for safety
        super().__init__(model, message, code="MODEL_RESPONSE_ERROR", details=details)


# =============================================================================
# Helper Functions
# =============================================================================


def raise_for_condition(condition: bool, exception: PalaceError) -> None:
    """
    Raise the given exception if condition is True.

    This is a utility function for cleaner exception handling.

    Args:
        condition: Boolean condition to check
        exception: Exception to raise if condition is True

    Raises:
        PalaceError: The provided exception if condition is True
    """
    if condition:
        raise exception
