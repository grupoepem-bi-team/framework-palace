"""
Palace Framework - Tests for Core Exceptions

This module tests all custom exceptions in the palace.core.exceptions module,
verifying:
- Exception hierarchy (all inherit from PalaceError)
- String representation formats
- raise_for_condition helper function
- to_dict() serialization
- Specialized exception extra attributes
"""

import pytest

from palace.core.exceptions import (
    AgentCapabilityError,
    AgentError,
    AgentExecutionError,
    AgentNotFoundError,
    AgentTimeoutError,
    APIError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    ContextError,
    ContextRetrievalError,
    EmbeddingError,
    InvalidConfigError,
    MemoryRetrievalError,
    MemoryStoreError,
    MissingConfigError,
    ModelError,
    ModelNotAvailableError,
    ModelResponseError,
    OrchestratorError,
    PalaceError,
    PalaceMemoryError,
    PipelineError,
    PipelineExecutionError,
    PipelineNotFoundError,
    ProjectNotFoundError,
    RateLimitError,
    SessionNotFoundError,
    TaskExecutionError,
    TaskRoutingError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolTimeoutError,
    WorkflowError,
    raise_for_condition,
)

# ============================================================================
# Hierarchy Tests — All exceptions inherit from PalaceError
# ============================================================================


class TestExceptionHierarchy:
    """Verify that every custom exception inherits from PalaceError."""

    # --- Configuration Errors ---

    def test_configuration_error_inherits_palace_error(self):
        assert issubclass(ConfigurationError, PalaceError)

    def test_missing_config_error_inherits_configuration_error(self):
        assert issubclass(MissingConfigError, ConfigurationError)

    def test_missing_config_error_inherits_palace_error(self):
        assert issubclass(MissingConfigError, PalaceError)

    def test_invalid_config_error_inherits_configuration_error(self):
        assert issubclass(InvalidConfigError, ConfigurationError)

    def test_invalid_config_error_inherits_palace_error(self):
        assert issubclass(InvalidConfigError, PalaceError)

    # --- Agent Errors ---

    def test_agent_error_inherits_palace_error(self):
        assert issubclass(AgentError, PalaceError)

    def test_agent_not_found_error_inherits_agent_error(self):
        assert issubclass(AgentNotFoundError, AgentError)

    def test_agent_not_found_error_inherits_palace_error(self):
        assert issubclass(AgentNotFoundError, PalaceError)

    def test_agent_execution_error_inherits_agent_error(self):
        assert issubclass(AgentExecutionError, AgentError)

    def test_agent_timeout_error_inherits_agent_error(self):
        assert issubclass(AgentTimeoutError, AgentError)

    def test_agent_capability_error_inherits_agent_error(self):
        assert issubclass(AgentCapabilityError, AgentError)

    # --- Orchestrator Errors ---

    def test_orchestrator_error_inherits_palace_error(self):
        assert issubclass(OrchestratorError, PalaceError)

    def test_task_routing_error_inherits_orchestrator_error(self):
        assert issubclass(TaskRoutingError, OrchestratorError)

    def test_task_routing_error_inherits_palace_error(self):
        assert issubclass(TaskRoutingError, PalaceError)

    def test_task_execution_error_inherits_orchestrator_error(self):
        assert issubclass(TaskExecutionError, OrchestratorError)

    def test_workflow_error_inherits_orchestrator_error(self):
        assert issubclass(WorkflowError, OrchestratorError)

    # --- Memory Errors ---

    def test_memory_error_inherits_palace_error(self):
        assert issubclass(PalaceMemoryError, PalaceError)

    def test_memory_store_error_inherits_memory_error(self):
        assert issubclass(MemoryStoreError, PalaceMemoryError)

    def test_memory_store_error_inherits_palace_error(self):
        assert issubclass(MemoryStoreError, PalaceError)

    def test_memory_retrieval_error_inherits_memory_error(self):
        assert issubclass(MemoryRetrievalError, PalaceMemoryError)

    def test_embedding_error_inherits_memory_error(self):
        assert issubclass(EmbeddingError, PalaceMemoryError)

    # --- Context Errors ---

    def test_context_error_inherits_palace_error(self):
        assert issubclass(ContextError, PalaceError)

    def test_project_not_found_error_inherits_context_error(self):
        assert issubclass(ProjectNotFoundError, ContextError)

    def test_project_not_found_error_inherits_palace_error(self):
        assert issubclass(ProjectNotFoundError, PalaceError)

    def test_session_not_found_error_inherits_context_error(self):
        assert issubclass(SessionNotFoundError, ContextError)

    def test_context_retrieval_error_inherits_context_error(self):
        assert issubclass(ContextRetrievalError, ContextError)

    # --- Tool Errors ---

    def test_tool_error_inherits_palace_error(self):
        assert issubclass(ToolError, PalaceError)

    def test_tool_not_found_error_inherits_tool_error(self):
        assert issubclass(ToolNotFoundError, ToolError)

    def test_tool_not_found_error_inherits_palace_error(self):
        assert issubclass(ToolNotFoundError, PalaceError)

    def test_tool_execution_error_inherits_tool_error(self):
        assert issubclass(ToolExecutionError, ToolError)

    def test_tool_timeout_error_inherits_tool_error(self):
        assert issubclass(ToolTimeoutError, ToolError)

    # --- API Errors ---

    def test_api_error_inherits_palace_error(self):
        assert issubclass(APIError, PalaceError)

    def test_authentication_error_inherits_api_error(self):
        assert issubclass(AuthenticationError, APIError)

    def test_authentication_error_inherits_palace_error(self):
        assert issubclass(AuthenticationError, PalaceError)

    def test_authorization_error_inherits_api_error(self):
        assert issubclass(AuthorizationError, APIError)

    def test_rate_limit_error_inherits_api_error(self):
        assert issubclass(RateLimitError, APIError)

    # --- Pipeline Errors ---

    def test_pipeline_error_inherits_palace_error(self):
        assert issubclass(PipelineError, PalaceError)

    def test_pipeline_not_found_error_inherits_pipeline_error(self):
        assert issubclass(PipelineNotFoundError, PipelineError)

    def test_pipeline_not_found_error_inherits_palace_error(self):
        assert issubclass(PipelineNotFoundError, PalaceError)

    def test_pipeline_execution_error_inherits_pipeline_error(self):
        assert issubclass(PipelineExecutionError, PipelineError)

    # --- Model Errors ---

    def test_model_error_inherits_palace_error(self):
        assert issubclass(ModelError, PalaceError)

    def test_model_not_available_error_inherits_model_error(self):
        assert issubclass(ModelNotAvailableError, ModelError)

    def test_model_not_available_error_inherits_palace_error(self):
        assert issubclass(ModelNotAvailableError, PalaceError)

    def test_model_response_error_inherits_model_error(self):
        assert issubclass(ModelResponseError, ModelError)

    # --- All exceptions are also Python Exceptions ---

    def test_palace_error_inherits_exception(self):
        assert issubclass(PalaceError, Exception)


# ============================================================================
# PalaceError Base Tests
# ============================================================================


class TestPalaceError:
    """Tests for the base PalaceError class."""

    def test_message_only(self):
        err = PalaceError("something went wrong")
        assert err.message == "something went wrong"
        assert err.code == "PalaceError"
        assert err.details == {}

    def test_message_and_code(self):
        err = PalaceError("something went wrong", code="CUSTOM_CODE")
        assert err.code == "CUSTOM_CODE"

    def test_message_and_details(self):
        err = PalaceError("something went wrong", details={"key": "value"})
        assert err.details == {"key": "value"}

    def test_message_code_and_details(self):
        err = PalaceError(
            "something went wrong",
            code="ERR_001",
            details={"field": "username", "reason": "too short"},
        )
        assert err.message == "something went wrong"
        assert err.code == "ERR_001"
        assert err.details == {"field": "username", "reason": "too short"}

    def test_str_without_details(self):
        err = PalaceError("something went wrong", code="PALACE_ERR")
        assert str(err) == "[PALACE_ERR] something went wrong"

    def test_str_with_details(self):
        err = PalaceError("something went wrong", code="PALACE_ERR", details={"key": "val"})
        assert "[PALACE_ERR]" in str(err)
        assert "something went wrong" in str(err)
        assert "Details:" in str(err)
        assert "'key': 'val'" in str(err)

    def test_str_default_code(self):
        err = PalaceError("default code test")
        assert str(err) == "[PalaceError] default code test"

    def test_to_dict_basic(self):
        err = PalaceError("test error", code="TEST_CODE", details={"foo": "bar"})
        result = err.to_dict()
        assert result == {
            "error": "TEST_CODE",
            "message": "test error",
            "details": {"foo": "bar"},
        }

    def test_to_dict_with_empty_details(self):
        err = PalaceError("test error")
        result = err.to_dict()
        assert result == {
            "error": "PalaceError",
            "message": "test error",
            "details": {},
        }

    def test_can_be_caught_as_exception(self):
        with pytest.raises(PalaceError) as exc_info:
            raise PalaceError("caught!")
        assert "caught!" in str(exc_info.value)

    def test_can_be_caught_with_catch_all(self):
        with pytest.raises(Exception) as exc_info:
            raise PalaceError("caught as Exception!")
        assert isinstance(exc_info.value, PalaceError)


# ============================================================================
# Configuration Error Tests
# ============================================================================


class TestConfigurationErrors:
    """Tests for ConfigurationError and its subclasses."""

    def test_configuration_error_basic(self):
        err = ConfigurationError("bad config", code="CONFIG_ERR")
        assert isinstance(err, PalaceError)
        assert err.message == "bad config"
        assert err.code == "CONFIG_ERR"

    def test_missing_config_error_default_message(self):
        err = MissingConfigError("DATABASE_URL")
        assert "DATABASE_URL" in str(err)
        assert err.config_key == "DATABASE_URL"
        assert err.details["config_key"] == "DATABASE_URL"
        assert err.code == "MISSING_CONFIG"

    def test_missing_config_error_custom_message(self):
        err = MissingConfigError("API_KEY", message="API key is required for production")
        assert err.message == "API key is required for production"
        assert err.config_key == "API_KEY"

    def test_missing_config_error_with_details(self):
        err = MissingConfigError("SECRET_KEY", details={"env_var": "PALACE_SECRET_KEY"})
        assert err.details["config_key"] == "SECRET_KEY"
        assert err.details["env_var"] == "PALACE_SECRET_KEY"

    def test_invalid_config_error(self):
        err = InvalidConfigError("port", "abc", "must be an integer")
        assert err.config_key == "port"
        assert err.value == "abc"
        assert err.reason == "must be an integer"
        assert "port" in str(err)
        assert "must be an integer" in str(err)
        assert err.code == "INVALID_CONFIG"
        assert err.details["config_key"] == "port"
        assert err.details["reason"] == "must be an integer"

    def test_invalid_config_error_with_details(self):
        err = InvalidConfigError(
            "timeout",
            -1,
            "must be positive",
            details={"min_value": 1},
        )
        assert err.details["min_value"] == 1
        assert err.details["config_key"] == "timeout"
        assert err.details["reason"] == "must be positive"

    def test_catch_missing_as_configuration(self):
        """MissingConfigError should be catchable as ConfigurationError."""
        with pytest.raises(ConfigurationError):
            raise MissingConfigError("MISSING_KEY")

    def test_catch_invalid_as_configuration(self):
        """InvalidConfigError should be catchable as ConfigurationError."""
        with pytest.raises(ConfigurationError):
            raise InvalidConfigError("key", "bad_value", "bad reason")


# ============================================================================
# Agent Error Tests
# ============================================================================


class TestAgentErrors:
    """Tests for AgentError and its subclasses."""

    def test_agent_error_basic(self):
        err = AgentError("backend", "agent failed", code="AGENT_ERR")
        assert err.agent_name == "backend"
        assert err.message == "agent failed"
        assert err.code == "AGENT_ERR"
        assert err.details["agent_name"] == "backend"

    def test_agent_error_default_code(self):
        err = AgentError("backend", "agent failed")
        assert err.code == "AgentError"

    def test_agent_not_found_error(self):
        err = AgentNotFoundError("frontend", available_agents=["backend", "devops"])
        assert err.agent_name == "frontend"
        assert err.code == "AGENT_NOT_FOUND"
        assert err.details["available_agents"] == ["backend", "devops"]
        assert "frontend" in str(err)
        assert "backend" in str(err)

    def test_agent_not_found_error_no_available(self):
        err = AgentNotFoundError("unknown_agent")
        assert err.agent_name == "unknown_agent"
        assert err.details["available_agents"] == []
        assert "none" in str(err)

    def test_agent_execution_error(self):
        err = AgentExecutionError("backend", "task-123", "out of memory")
        assert err.agent_name == "backend"
        assert err.task_id == "task-123"
        assert err.details["reason"] == "out of memory"
        assert err.code == "AGENT_EXECUTION_ERROR"
        assert err.details["task_id"] == "task-123"
        assert "task-123" in str(err)

    def test_agent_timeout_error(self):
        err = AgentTimeoutError("backend", "task-456", 30.0)
        assert err.agent_name == "backend"
        assert err.task_id == "task-456"
        assert err.timeout_seconds == 30.0
        assert err.code == "AGENT_TIMEOUT"
        assert err.details["timeout_seconds"] == 30.0
        assert "30" in str(err)

    def test_agent_capability_error(self):
        err = AgentCapabilityError(
            "backend",
            "frontend_development",
            ["backend_development", "database_administration"],
        )
        assert err.agent_name == "backend"
        assert err.required_capability == "frontend_development"
        assert err.available_capabilities == ["backend_development", "database_administration"]
        assert err.code == "AGENT_CAPABILITY_ERROR"
        assert "frontend_development" in str(err)
        assert "backend_development" in str(err)

    def test_agent_capability_error_no_capabilities(self):
        err = AgentCapabilityError("backend", "testing", [])
        assert err.available_capabilities == []
        assert "none" in str(err)

    def test_catch_agent_not_found_as_agent_error(self):
        with pytest.raises(AgentError):
            raise AgentNotFoundError("missing_agent")

    def test_catch_agent_execution_as_palace_error(self):
        with pytest.raises(PalaceError):
            raise AgentExecutionError("backend", "task-1", "crashed")


# ============================================================================
# Orchestrator Error Tests
# ============================================================================


class TestOrchestratorErrors:
    """Tests for OrchestratorError and its subclasses."""

    def test_orchestrator_error_basic(self):
        err = OrchestratorError("orchestration failed")
        assert isinstance(err, PalaceError)
        assert err.message == "orchestration failed"

    def test_task_routing_error(self):
        err = TaskRoutingError(
            "Implement user login endpoint",
            "no agent with required capabilities",
            candidate_agents=["backend", "frontend"],
        )
        assert err.task_description == "Implement user login endpoint"
        assert err.reason == "no agent with required capabilities"
        assert err.details["candidate_agents"] == ["backend", "frontend"]
        assert err.code == "TASK_ROUTING_ERROR"
        assert err.details["reason"] == "no agent with required capabilities"
        assert err.details["candidate_agents"] == ["backend", "frontend"]

    def test_task_routing_error_truncates_description(self):
        long_desc = "A" * 100
        err = TaskRoutingError(long_desc, "no match")
        # The message truncates the task description to 50 chars
        assert long_desc[:50] in str(err)

    def test_task_execution_error(self):
        err = TaskExecutionError("task-789", "validation", "schema mismatch")
        assert err.task_id == "task-789"
        assert err.stage == "validation"
        assert err.reason == "schema mismatch"
        assert err.code == "TASK_EXECUTION_ERROR"
        assert "task-789" in str(err)
        assert "validation" in str(err)
        assert err.details["task_id"] == "task-789"
        assert err.details["stage"] == "validation"
        assert err.details["reason"] == "schema mismatch"

    def test_workflow_error(self):
        err = WorkflowError("deploy-pipeline", 3, "connection refused")
        assert err.workflow_name == "deploy-pipeline"
        assert err.step == 3
        assert err.reason == "connection refused"
        assert err.code == "WORKFLOW_ERROR"
        assert "deploy-pipeline" in str(err)
        assert err.details["workflow_name"] == "deploy-pipeline"
        assert err.details["step"] == 3

    def test_catch_routing_as_orchestrator(self):
        with pytest.raises(OrchestratorError):
            raise TaskRoutingError("test task", "no agents")

    def test_catch_workflow_as_palace_error(self):
        with pytest.raises(PalaceError):
            raise WorkflowError("wf", 1, "failed")


# ============================================================================
# Memory Error Tests
# ============================================================================


class TestMemoryErrors:
    """Tests for PalaceMemoryError and its subclasses."""

    def test_memory_error_basic(self):
        err = PalaceMemoryError("memory subsystem error")
        assert isinstance(err, PalaceError)
        assert err.message == "memory subsystem error"

    def test_memory_store_error_with_memory_type(self):
        err = MemoryStoreError(
            "insert",
            "disk full",
            memory_type="semantic",
        )
        assert err.operation == "insert"
        assert err.reason == "disk full"
        assert err.memory_type == "semantic"
        assert err.code == "MEMORY_STORE_ERROR"
        assert err.details["operation"] == "insert"
        assert err.details["reason"] == "disk full"
        assert err.details["memory_type"] == "semantic"

    def test_memory_store_error_without_memory_type(self):
        err = MemoryStoreError("delete", "corrupted index")
        assert err.memory_type is None
        assert "memory_type" not in err.details
        assert "corrupted index" in str(err)

    def test_memory_retrieval_error(self):
        err = MemoryRetrievalError("SELECT * FROM memories WHERE id = 1", "connection timeout")
        assert err.query == "SELECT * FROM memories WHERE id = 1"
        assert err.reason == "connection timeout"
        assert err.code == "MEMORY_RETRIEVAL_ERROR"
        assert err.details["query"] == "SELECT * FROM memories WHERE id = 1"

    def test_memory_retrieval_error_truncates_query(self):
        long_query = "Q" * 100
        err = MemoryRetrievalError(long_query, "timeout")
        # The message truncates the query to 50 chars
        assert long_query[:50] in str(err)

    def test_embedding_error(self):
        err = EmbeddingError(5000, "text-embedding-ada-002", "model overloaded")
        assert err.text_length == 5000
        assert err.model == "text-embedding-ada-002"
        assert err.reason == "model overloaded"
        assert err.code == "EMBEDDING_ERROR"
        assert err.details["text_length"] == 5000
        assert err.details["model"] == "text-embedding-ada-002"
        assert err.details["reason"] == "model overloaded"

    def test_catch_store_as_memory_error(self):
        with pytest.raises(PalaceMemoryError):
            raise MemoryStoreError("read", "IO error")

    def test_catch_retrieval_as_palace_error(self):
        with pytest.raises(PalaceError):
            raise MemoryRetrievalError("query", "not found")


# ============================================================================
# Context Error Tests
# ============================================================================


class TestContextErrors:
    """Tests for ContextError and its subclasses."""

    def test_context_error_basic(self):
        err = ContextError("context subsystem error")
        assert isinstance(err, PalaceError)
        assert err.message == "context subsystem error"

    def test_project_not_found_error(self):
        err = ProjectNotFoundError("proj-123")
        assert err.project_id == "proj-123"
        assert err.code == "PROJECT_NOT_FOUND"
        assert "proj-123" in str(err)
        assert err.details["project_id"] == "proj-123"

    def test_session_not_found_error_without_project(self):
        err = SessionNotFoundError("sess-456")
        assert err.session_id == "sess-456"
        assert err.project_id is None
        assert err.code == "SESSION_NOT_FOUND"
        assert "sess-456" in str(err)
        assert err.details["session_id"] == "sess-456"

    def test_session_not_found_error_with_project(self):
        err = SessionNotFoundError("sess-456", project_id="proj-789")
        assert err.session_id == "sess-456"
        assert err.project_id == "proj-789"
        assert "proj-789" in str(err)
        assert err.details["project_id"] == "proj-789"

    def test_context_retrieval_error(self):
        err = ContextRetrievalError("semantic", "vector store unavailable")
        assert err.context_type == "semantic"
        assert err.reason == "vector store unavailable"
        assert err.code == "CONTEXT_RETRIEVAL_ERROR"
        assert err.details["context_type"] == "semantic"
        assert err.details["reason"] == "vector store unavailable"

    def test_catch_project_not_found_as_context_error(self):
        with pytest.raises(ContextError):
            raise ProjectNotFoundError("proj-404")

    def test_catch_session_not_found_as_palace_error(self):
        with pytest.raises(PalaceError):
            raise SessionNotFoundError("sess-404")


# ============================================================================
# Tool Error Tests
# ============================================================================


class TestToolErrors:
    """Tests for ToolError and its subclasses."""

    def test_tool_error_basic(self):
        err = ToolError("git", "git operation failed", code="TOOL_ERR")
        assert err.tool_name == "git"
        assert err.message == "git operation failed"
        assert err.code == "TOOL_ERR"
        assert err.details["tool_name"] == "git"

    def test_tool_not_found_error(self):
        err = ToolNotFoundError("docker", available_tools=["git", "pytest"])
        assert err.tool_name == "docker"
        assert err.code == "TOOL_NOT_FOUND"
        assert err.details["available_tools"] == ["git", "pytest"]
        assert "docker" in str(err)
        assert "git" in str(err)

    def test_tool_not_found_error_no_available(self):
        err = ToolNotFoundError("unknown_tool")
        assert err.details["available_tools"] == []
        assert "none" in str(err)

    def test_tool_execution_error(self):
        err = ToolExecutionError("pytest", "test suite crashed", exit_code=1)
        assert err.tool_name == "pytest"
        assert err.reason == "test suite crashed"
        assert err.exit_code == 1
        assert err.code == "TOOL_EXECUTION_ERROR"
        assert err.details["reason"] == "test suite crashed"
        assert err.details["exit_code"] == 1

    def test_tool_execution_error_without_exit_code(self):
        err = ToolExecutionError("git", "merge conflict")
        assert err.exit_code is None
        assert "exit_code" not in err.details

    def test_tool_timeout_error(self):
        err = ToolTimeoutError("docker", 60.0)
        assert err.tool_name == "docker"
        assert err.timeout_seconds == 60.0
        assert err.code == "TOOL_TIMEOUT"
        assert err.details["timeout_seconds"] == 60.0
        assert "60" in str(err)

    def test_catch_tool_not_found_as_tool_error(self):
        with pytest.raises(ToolError):
            raise ToolNotFoundError("missing_tool")

    def test_catch_tool_execution_as_palace_error(self):
        with pytest.raises(PalaceError):
            raise ToolExecutionError("tool", "crashed")


# ============================================================================
# API Error Tests
# ============================================================================


class TestAPIErrors:
    """Tests for APIError and its subclasses."""

    def test_api_error_basic(self):
        err = APIError("internal server error", status_code=500)
        assert err.status_code == 500
        assert err.details["status_code"] == 500
        assert err.code == "APIError"

    def test_api_error_custom_code(self):
        err = APIError("bad gateway", status_code=502, code="BAD_GATEWAY")
        assert err.code == "BAD_GATEWAY"

    def test_authentication_error(self):
        err = AuthenticationError()
        assert err.message == "Authentication failed"
        assert err.status_code == 401
        assert err.code == "AUTHENTICATION_ERROR"
        assert err.details["status_code"] == 401

    def test_authentication_error_custom_message(self):
        err = AuthenticationError("Invalid API key")
        assert err.message == "Invalid API key"

    def test_authorization_error(self):
        err = AuthorizationError("projects", "delete")
        assert err.resource == "projects"
        assert err.action == "delete"
        assert err.status_code == 403
        assert err.code == "AUTHORIZATION_ERROR"
        assert "projects" in str(err)
        assert "delete" in str(err)
        assert err.details["resource"] == "projects"
        assert err.details["action"] == "delete"

    def test_rate_limit_error_without_retry(self):
        err = RateLimitError()
        assert err.retry_after is None
        assert err.status_code == 429
        assert err.code == "RATE_LIMIT_ERROR"
        assert err.message == "Rate limit exceeded"

    def test_rate_limit_error_with_retry(self):
        err = RateLimitError(retry_after=60)
        assert err.retry_after == 60
        assert "60" in str(err)
        assert err.details["retry_after"] == 60

    def test_catch_authentication_as_api_error(self):
        with pytest.raises(APIError):
            raise AuthenticationError()

    def test_catch_authorization_as_palace_error(self):
        with pytest.raises(PalaceError):
            raise AuthorizationError("resource", "action")


# ============================================================================
# Pipeline Error Tests
# ============================================================================


class TestPipelineErrors:
    """Tests for PipelineError and its subclasses."""

    def test_pipeline_error_basic(self):
        err = PipelineError("pipeline error")
        assert isinstance(err, PalaceError)
        assert err.message == "pipeline error"

    def test_pipeline_not_found_error(self):
        err = PipelineNotFoundError("deploy-pipeline", available_pipelines=["test-pipeline"])
        assert err.pipeline_name == "deploy-pipeline"
        assert err.code == "PIPELINE_NOT_FOUND"
        assert err.details["available_pipelines"] == ["test-pipeline"]
        assert "deploy-pipeline" in str(err)
        assert "test-pipeline" in str(err)

    def test_pipeline_not_found_error_no_available(self):
        err = PipelineNotFoundError("missing-pipeline")
        assert err.details["available_pipelines"] == []
        assert "none" in str(err)

    def test_pipeline_execution_error(self):
        err = PipelineExecutionError("ci-pipeline", "build", "compilation failed")
        assert err.pipeline_name == "ci-pipeline"
        assert err.step == "build"
        assert err.reason == "compilation failed"
        assert err.code == "PIPELINE_EXECUTION_ERROR"
        assert err.details["pipeline_name"] == "ci-pipeline"
        assert err.details["step"] == "build"
        assert err.details["reason"] == "compilation failed"

    def test_catch_pipeline_not_found_as_pipeline_error(self):
        with pytest.raises(PipelineError):
            raise PipelineNotFoundError("missing")

    def test_catch_pipeline_execution_as_palace_error(self):
        with pytest.raises(PalaceError):
            raise PipelineExecutionError("pipe", "step1", "err")


# ============================================================================
# Model Error Tests
# ============================================================================


class TestModelErrors:
    """Tests for ModelError and its subclasses."""

    def test_model_error_basic(self):
        err = ModelError("gpt-4", "model error", code="MODEL_ERR")
        assert err.model == "gpt-4"
        assert err.message == "model error"
        assert err.code == "MODEL_ERR"
        assert err.details["model"] == "gpt-4"

    def test_model_not_available_error(self):
        err = ModelNotAvailableError("gpt-5", available_models=["gpt-4", "gpt-3.5"])
        assert err.model == "gpt-5"
        assert err.code == "MODEL_NOT_AVAILABLE"
        assert err.details["available_models"] == ["gpt-4", "gpt-3.5"]
        assert "gpt-5" in str(err)
        assert "gpt-4" in str(err)

    def test_model_not_available_error_no_models(self):
        err = ModelNotAvailableError("unknown-model")
        assert err.details["available_models"] == []
        assert "none" in str(err)

    def test_model_response_error(self):
        err = ModelResponseError("gpt-4", "invalid JSON", raw_response='{"broken')
        assert err.model == "gpt-4"
        assert err.reason == "invalid JSON"
        assert err.raw_response == '{"broken'
        assert err.code == "MODEL_RESPONSE_ERROR"
        assert err.details["reason"] == "invalid JSON"
        assert err.details["raw_response"] == '{"broken'

    def test_model_response_error_no_raw_response(self):
        err = ModelResponseError("gpt-4", "timeout")
        assert err.raw_response is None
        assert "raw_response" not in err.details

    def test_model_response_error_truncates_long_raw_response(self):
        long_response = "X" * 1000
        err = ModelResponseError("gpt-4", "too long", raw_response=long_response)
        # raw_response is truncated to 500 chars in details
        assert len(err.details["raw_response"]) == 500

    def test_catch_model_not_available_as_model_error(self):
        with pytest.raises(ModelError):
            raise ModelNotAvailableError("model-x")

    def test_catch_model_response_as_palace_error(self):
        with pytest.raises(PalaceError):
            raise ModelResponseError("model-y", "bad response")


# ============================================================================
# raise_for_condition Tests
# ============================================================================


class TestRaiseForCondition:
    """Tests for the raise_for_condition helper function."""

    def test_raises_when_condition_true(self):
        with pytest.raises(PalaceError) as exc_info:
            raise_for_condition(True, PalaceError("condition triggered"))
        assert "condition triggered" in str(exc_info.value)

    def test_does_not_raise_when_condition_false(self):
        # Should not raise any exception
        raise_for_condition(False, PalaceError("should not be raised"))

    def test_raises_with_specialized_exception(self):
        with pytest.raises(AgentNotFoundError) as exc_info:
            raise_for_condition(True, AgentNotFoundError("missing_agent"))
        assert exc_info.value.agent_name == "missing_agent"

    def test_does_not_raise_with_false_condition(self):
        # Verify that no exception is raised for falsy conditions
        raise_for_condition(False, PalaceError("never raised"))
        raise_for_condition(0, PalaceError("never raised"))
        raise_for_condition(None, PalaceError("never raised"))
        raise_for_condition("", PalaceError("never raised"))
        raise_for_condition([], PalaceError("never raised"))

    def test_raises_with_truthy_conditions(self):
        with pytest.raises(PalaceError):
            raise_for_condition(1, PalaceError("truthy"))

        with pytest.raises(PalaceError):
            raise_for_condition("non-empty", PalaceError("truthy"))

        with pytest.raises(PalaceError):
            raise_for_condition([1], PalaceError("truthy"))

    def test_raises_with_complex_condition(self):
        agent_name = "unknown"
        available = ["backend", "frontend"]
        with pytest.raises(AgentNotFoundError):
            raise_for_condition(
                agent_name not in available,
                AgentNotFoundError(agent_name, available_agents=available),
            )

    def test_does_not_raise_with_none_value(self):
        value = None
        raise_for_condition(value is not None, PalaceError("should not raise"))

    def test_raises_with_none_check(self):
        value = None
        with pytest.raises(PalaceError):
            raise_for_condition(value is None, PalaceError("value is None"))

    def test_raises_with_configuration_error(self):
        with pytest.raises(MissingConfigError):
            raise_for_condition(
                True,
                MissingConfigError("MISSING_KEY"),
            )

    def test_raises_with_memory_error(self):
        with pytest.raises(MemoryStoreError):
            raise_for_condition(
                True,
                MemoryStoreError("write", "disk full"),
            )

    def test_chaining_raise_for_condition(self):
        """Multiple conditions can be checked in sequence."""
        raise_for_condition(False, PalaceError("first"))
        raise_for_condition(False, PalaceError("second"))

        with pytest.raises(PalaceError) as exc_info:
            raise_for_condition(True, PalaceError("third"))
        assert "third" in str(exc_info.value)


# ============================================================================
# String Representation Tests
# ============================================================================


class TestExceptionStringRepresentation:
    """Comprehensive tests for __str__ across all exception types."""

    def test_palace_error_str_format(self):
        err = PalaceError("base error", code="BASE")
        s = str(err)
        assert s == "[BASE] base error"

    def test_palace_error_str_with_details(self):
        err = PalaceError("base error", code="BASE", details={"k1": "v1"})
        s = str(err)
        assert s.startswith("[BASE]")
        assert "base error" in s
        assert "Details:" in s

    def test_missing_config_str(self):
        s = str(MissingConfigError("API_KEY"))
        assert "[MISSING_CONFIG]" in s
        assert "API_KEY" in s

    def test_invalid_config_str(self):
        s = str(InvalidConfigError("port", "abc", "must be integer"))
        assert "[INVALID_CONFIG]" in s
        assert "port" in s

    def test_agent_not_found_str(self):
        s = str(AgentNotFoundError("devops", available_agents=["backend"]))
        assert "[AGENT_NOT_FOUND]" in s
        assert "devops" in s
        assert "backend" in s

    def test_agent_timeout_str(self):
        s = str(AgentTimeoutError("backend", "t-1", 60.0))
        assert "[AGENT_TIMEOUT]" in s
        assert "60" in s

    def test_rate_limit_str_with_retry(self):
        s = str(RateLimitError(retry_after=120))
        assert "[RATE_LIMIT_ERROR]" in s
        assert "120" in s

    def test_authorization_str(self):
        s = str(AuthorizationError("files", "read"))
        assert "[AUTHORIZATION_ERROR]" in s
        assert "files" in s
        assert "read" in s

    def test_pipeline_not_found_str(self):
        s = str(PipelineNotFoundError("ci", available_pipelines=["cd"]))
        assert "[PIPELINE_NOT_FOUND]" in s
        assert "ci" in s
        assert "cd" in s

    def test_model_not_available_str(self):
        s = str(ModelNotAvailableError("gpt-5", available_models=["gpt-4"]))
        assert "[MODEL_NOT_AVAILABLE]" in s
        assert "gpt-5" in s

    def test_embedding_error_str(self):
        s = str(EmbeddingError(1000, "text-embedding-ada-002", "timeout"))
        assert "[EMBEDDING_ERROR]" in s
        assert "text-embedding-ada-002" in s


# ============================================================================
# to_dict Tests
# ============================================================================


class TestToDict:
    """Tests for the to_dict() method across exception types."""

    def test_palace_error_to_dict(self):
        err = PalaceError("test", code="TEST", details={"a": 1})
        d = err.to_dict()
        assert d == {"error": "TEST", "message": "test", "details": {"a": 1}}

    def test_missing_config_to_dict(self):
        err = MissingConfigError("DB_URL")
        d = err.to_dict()
        assert d["error"] == "MISSING_CONFIG"
        assert d["details"]["config_key"] == "DB_URL"

    def test_agent_execution_to_dict(self):
        err = AgentExecutionError("backend", "t-1", "OOM")
        d = err.to_dict()
        assert d["error"] == "AGENT_EXECUTION_ERROR"
        assert d["details"]["agent_name"] == "backend"
        assert d["details"]["task_id"] == "t-1"

    def test_rate_limit_to_dict(self):
        err = RateLimitError(retry_after=30)
        d = err.to_dict()
        assert d["error"] == "RATE_LIMIT_ERROR"
        assert d["details"]["retry_after"] == 30
        assert d["details"]["status_code"] == 429

    def test_authorization_to_dict(self):
        err = AuthorizationError("documents", "write")
        d = err.to_dict()
        assert d["error"] == "AUTHORIZATION_ERROR"
        assert d["details"]["resource"] == "documents"
        assert d["details"]["action"] == "write"

    def test_workflow_to_dict(self):
        err = WorkflowError("deploy", 2, "connection refused")
        d = err.to_dict()
        assert d["error"] == "WORKFLOW_ERROR"
        assert d["details"]["workflow_name"] == "deploy"
        assert d["details"]["step"] == 2
        assert d["details"]["reason"] == "connection refused"

    def test_model_response_to_dict(self):
        err = ModelResponseError("gpt-4", "bad JSON", raw_response="bad{")
        d = err.to_dict()
        assert d["error"] == "MODEL_RESPONSE_ERROR"
        assert d["details"]["model"] == "gpt-4"
        assert d["details"]["reason"] == "bad JSON"
        assert d["details"]["raw_response"] == "bad{"

    def test_to_dict_preserves_all_keys(self):
        """to_dict should always have error, message, and details keys."""
        test_cases = [
            (PalaceError, lambda: PalaceError("msg", code="X")),
            (ConfigurationError, lambda: ConfigurationError("msg", code="X")),
            (AgentError, lambda: AgentError("agent1", "msg", code="X")),
            (OrchestratorError, lambda: OrchestratorError("msg", code="X")),
            (PalaceMemoryError, lambda: PalaceMemoryError("msg", code="X")),
            (ContextError, lambda: ContextError("msg", code="X")),
            (ToolError, lambda: ToolError("tool1", "msg", code="X")),
            (APIError, lambda: APIError("msg", status_code=500, code="X")),
            (PipelineError, lambda: PipelineError("msg", code="X")),
            (ModelError, lambda: ModelError("model1", "msg", code="X")),
        ]
        for ExcClass, factory in test_cases:
            err = factory()
            d = err.to_dict()
            assert "error" in d, f"{ExcClass.__name__} to_dict missing 'error'"
            assert "message" in d, f"{ExcClass.__name__} to_dict missing 'message'"
            assert "details" in d, f"{ExcClass.__name__} to_dict missing 'details'"
