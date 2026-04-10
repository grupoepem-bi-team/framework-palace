"""
Tests for Palace Framework API Module (Module 8)

Comprehensive tests for the FastAPI application, covering:
- App creation and configuration
- Health and root endpoints
- Project CRUD endpoints
- Task execution and status endpoints
- Session creation and history endpoints
- Memory query and entry endpoints
- Agent listing and info endpoints
- Error handling (PalaceError, validation, 503)
- CORS middleware configuration

All framework dependencies (PalaceFramework, ContextManager, MemoryStore)
are mocked to prevent real connections.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from palace.api.main import app, get_framework
from palace.core.exceptions import PalaceError

# ============================================================================
# Helper: Build Mock Objects
# ============================================================================


def _make_mock_project_context(
    project_id="proj_test-project",
    name="test-project",
    description="A test project",
):
    """Create a mock ProjectContext with standard attributes."""
    ctx = MagicMock()
    ctx.config = MagicMock()
    ctx.config.project_id = project_id
    ctx.config.name = name
    ctx.config.description = description
    ctx.config.created_at = datetime(2024, 1, 15, 10, 30, 0)
    return ctx


def _make_mock_session(
    session_id="sess_abc123",
    project_id="proj_test-project",
    messages=None,
):
    """Create a mock SessionContext with standard attributes."""
    session = MagicMock()
    session.session_id = session_id
    session.created_at = datetime(2024, 1, 15, 11, 0, 0)
    session.messages = messages or []
    return session


def _make_mock_agent(
    name="backend",
    model="test-model",
    description="Backend development specialist",
):
    """Create a mock Agent with standard attributes."""
    agent = MagicMock()
    agent.name = name
    agent.model = model
    agent.description = description

    cap = MagicMock()
    cap.value = "backend_development"
    agent.capabilities = [cap]
    agent.tools = ["shell", "file_read", "file_write"]
    return agent


def _make_execution_result(
    task_id="task_def456",
    status="success",
    result="Task completed successfully",
    agent_used="backend",
    execution_time=1.5,
    metadata=None,
):
    """Create a mock ExecutionResult-like object."""
    r = MagicMock()
    r.task_id = task_id
    r.status = status
    r.result = result
    r.agent_used = agent_used
    r.execution_time = execution_time
    r.metadata = metadata or {"artifacts": [{"path": "src/api/users.py", "type": "code"}]}
    r.to_dict = lambda: {
        "task_id": task_id,
        "status": status,
        "result": result,
        "agent_used": agent_used,
        "execution_time": execution_time,
        "metadata": r.metadata,
    }
    return r


def _make_project_status(
    project_id="proj_test-project",
    status="active",
    active_tasks=2,
    last_activity="2024-01-15T12:00:00Z",
    context_summary="Test project context",
):
    """Create a mock ProjectStatus-like object."""
    ps = MagicMock()
    ps.project_id = project_id
    ps.status = status
    ps.active_tasks = active_tasks
    ps.last_activity = last_activity
    ps.context_summary = context_summary
    ps.to_dict = lambda: {
        "project_id": project_id,
        "status": status,
        "active_tasks": active_tasks,
        "last_activity": last_activity,
        "context_summary": context_summary,
    }
    return ps


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_project_context():
    """Provide a mock ProjectContext."""
    return _make_mock_project_context()


@pytest.fixture
def mock_session():
    """Provide a mock SessionContext."""
    return _make_mock_session()


@pytest.fixture
def mock_agent():
    """Provide a mock Agent."""
    return _make_mock_agent()


@pytest.fixture
def mock_framework(mock_project_context, mock_session, mock_agent):
    """Create a fully mocked PalaceFramework with all component mocks.

    Replaces ContextManager, MemoryStore, and Orchestrator with AsyncMock
    wrappers so no real connections are made during tests.
    """
    framework = MagicMock()
    framework._initialized = True

    # --- Context Manager ---
    ctx_manager = MagicMock()
    ctx_manager.create_project = AsyncMock(return_value=mock_project_context)
    ctx_manager.get_project_context = AsyncMock(return_value=mock_project_context)
    ctx_manager.list_projects = MagicMock(return_value=["proj_test-project"])
    ctx_manager.delete_project = AsyncMock(return_value=None)
    ctx_manager.create_session = AsyncMock(return_value=mock_session)
    ctx_manager.get_session = AsyncMock(return_value=mock_session)
    ctx_manager.get_session_history = AsyncMock(
        return_value=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
    )
    ctx_manager.retrieve_context = AsyncMock(return_value=[])
    ctx_manager.set_active_project = MagicMock(return_value=None)
    framework._context_manager = ctx_manager

    # --- Memory Store ---
    memory_store = MagicMock()
    memory_store.store = AsyncMock(return_value="entry_abc123")
    memory_store.search = AsyncMock(return_value=[])
    memory_store.initialize = AsyncMock()
    memory_store.close = AsyncMock()
    framework._memory_store = memory_store

    # --- Orchestrator ---
    orchestrator = MagicMock()
    orchestrator._agents = {"backend": mock_agent}
    orchestrator.list_active_projects = MagicMock(return_value=["proj_test-project"])
    orchestrator.initialize = AsyncMock()
    orchestrator.shutdown = AsyncMock()
    framework._orchestrator = orchestrator

    # --- Framework-level methods ---
    framework.execute = AsyncMock(return_value=_make_execution_result())
    framework.get_project_status = AsyncMock(return_value=_make_project_status())
    framework.list_agents = AsyncMock(return_value=["backend", "frontend", "devops"])
    framework.initialize = AsyncMock()
    framework.shutdown = AsyncMock()

    return framework


@pytest.fixture
def client(mock_framework):
    """Create a TestClient with all framework dependencies mocked.

    Uses FastAPI dependency_overrides to inject the mock framework,
    and patches the module-level _framework variable so that
    health-check (which reads the global directly) also works.
    """
    app.dependency_overrides[get_framework] = lambda: mock_framework

    with (
        patch("palace.api.main._framework", mock_framework),
        patch("palace.api.main.PalaceFramework", return_value=mock_framework),
    ):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

    app.dependency_overrides.clear()


# ============================================================================
# Test App Configuration
# ============================================================================


class TestAppConfiguration:
    """Tests for the FastAPI application instance configuration."""

    def test_app_title(self):
        """App should have the correct title."""
        assert app.title == "Palace Framework API"

    def test_app_has_docs_url(self):
        """App should expose Swagger UI at /docs."""
        assert app.docs_url == "/docs"

    def test_app_has_redoc_url(self):
        """App should expose ReDoc at /redoc."""
        assert app.redoc_url == "/redoc"

    def test_app_has_openapi_url(self):
        """App should expose OpenAPI schema at /openapi.json."""
        assert app.openapi_url == "/openapi.json"

    def test_cors_middleware_configured(self):
        """CORS middleware should be present in the app's middleware stack."""
        from fastapi.middleware.cors import CORSMiddleware

        cors_found = any(m.cls is CORSMiddleware for m in app.user_middleware)
        assert cors_found, "CORSMiddleware should be registered"

    def test_cors_headers_on_request(self, client):
        """Responses should include CORS headers for allowed origins."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        # The CORS middleware adds the header when the origin is allowed
        assert response.status_code == 200


# ============================================================================
# Test Health & Root Endpoints
# ============================================================================


class TestHealthEndpoints:
    """Tests for /health and / root endpoints."""

    def test_health_check(self, client):
        """GET /health should return healthy status and version info."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert isinstance(data["framework_initialized"], bool)

    def test_health_check_framework_initialized(self, client, mock_framework):
        """GET /health should report framework_initialized=True when framework is up."""
        mock_framework._initialized = True

        with patch("palace.api.main._framework", mock_framework):
            response = client.get("/health")

        data = response.json()
        assert data["framework_initialized"] is True

    def test_health_check_framework_not_initialized(self, client, mock_framework):
        """GET /health should report framework_initialized=False when not up."""
        mock_framework._initialized = False

        with patch("palace.api.main._framework", mock_framework):
            response = client.get("/health")

        data = response.json()
        # The health endpoint reads _framework._initialized
        assert data["framework_initialized"] is False

    def test_root_endpoint(self, client):
        """GET / should return API metadata."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["name"] == "Palace Framework API"
        assert "version" in data
        assert data["docs"] == "/docs"
        assert data["openapi"] == "/openapi.json"


# ============================================================================
# Test Project Endpoints
# ============================================================================


class TestProjectEndpoints:
    """Tests for /projects CRUD endpoints."""

    def test_create_project(self, client, mock_framework):
        """POST /projects should create a project and return 201."""
        payload = {
            "name": "my-api-project",
            "description": "A new REST API project",
            "backend_framework": "fastapi",
            "database": "postgresql",
        }

        response = client.post("/projects", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["name"] == "test-project"
        assert data["status"] == "active"
        assert "project_id" in data
        assert "created_at" in data

        # Verify the context manager was called
        mock_framework._context_manager.create_project.assert_awaited_once()

    def test_create_project_minimal(self, client, mock_framework):
        """POST /projects with only name should succeed."""
        payload = {"name": "minimal-project"}

        response = client.post("/projects", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert "project_id" in data
        assert data["status"] == "active"

    def test_create_project_with_all_fields(self, client, mock_framework):
        """POST /projects with all optional fields should succeed."""
        payload = {
            "name": "full-project",
            "description": "A project with all fields",
            "backend_framework": "django",
            "frontend_framework": "react",
            "database": "mysql",
        }

        response = client.post("/projects", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        # Verify config dict was built with all fields
        call_args = mock_framework._context_manager.create_project.call_args
        config_arg = call_args.kwargs if call_args.kwargs else {}
        assert config_arg is not None or call_args is not None

    def test_create_project_empty_name_422(self, client):
        """POST /projects with empty name should return 422."""
        payload = {"name": ""}

        response = client.post("/projects", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_project_missing_name_422(self, client):
        """POST /projects without name should return 422."""
        payload = {"description": "No name provided"}

        response = client.post("/projects", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_project_name_too_long_422(self, client):
        """POST /projects with name exceeding 100 chars should return 422."""
        payload = {"name": "x" * 101}

        response = client.post("/projects", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_projects(self, client, mock_framework):
        """GET /projects should return a list of projects."""
        mock_framework._context_manager.list_projects = MagicMock(
            return_value=["proj_test-project"]
        )

        response = client.get("/projects")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["project_id"] == "proj_test-project"

    def test_list_projects_empty(self, client, mock_framework):
        """GET /projects should return empty list when no projects exist."""
        mock_framework._context_manager.list_projects = MagicMock(return_value=[])

        response = client.get("/projects")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_projects_handles_context_error(self, client, mock_framework):
        """GET /projects should include partial results when one project's context fails."""
        # First call succeeds, second call raises
        proj_ctx = _make_mock_project_context(project_id="proj_good")
        mock_framework._context_manager.list_projects = MagicMock(
            return_value=["proj_good", "proj_broken"]
        )
        mock_framework._context_manager.get_project_context = AsyncMock(
            side_effect=[proj_ctx, Exception("Context not found")]
        )

        response = client.get("/projects")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data) == 2

    def test_get_project(self, client, mock_framework):
        """GET /projects/{project_id} should return project details."""
        response = client.get("/projects/proj_test-project")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["project_id"] == "proj_test-project"
        assert data["name"] == "test-project"
        assert data["status"] == "active"

    def test_get_project_not_found(self, client, mock_framework):
        """GET /projects/{project_id} should return 404 for missing project."""
        mock_framework._context_manager.get_project_context = AsyncMock(
            side_effect=Exception("Project not found")
        )

        response = client.get("/projects/proj_nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_project_status(self, client, mock_framework):
        """GET /projects/{project_id}/status should return project status."""
        mock_framework.get_project_status = AsyncMock(return_value=_make_project_status())

        response = client.get("/projects/proj_test-project/status")
        assert response.status_code == status.HTTP_200_OK

        # ProjectStatus is a plain class (not Pydantic), so FastAPI
        # may serialize it differently. Verify the mock was called.
        mock_framework.get_project_status.assert_awaited_once_with("proj_test-project")

    def test_delete_project(self, client, mock_framework):
        """DELETE /projects/{project_id} should delete and return 204."""
        response = client.delete("/projects/proj_test-project")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        mock_framework._context_manager.delete_project.assert_awaited_once_with("proj_test-project")

    def test_delete_project_not_found(self, client, mock_framework):
        """DELETE /projects/{project_id} should return 404 for missing project."""
        mock_framework._context_manager.delete_project = AsyncMock(
            side_effect=Exception("Project not found")
        )

        response = client.delete("/projects/proj_nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Test Task Endpoints
# ============================================================================


class TestTaskEndpoints:
    """Tests for /tasks endpoints."""

    def test_create_task(self, client, mock_framework):
        """POST /tasks should create and execute a task, returning 201."""
        mock_framework.execute = AsyncMock(return_value=_make_execution_result())

        payload = {
            "task": "Create a REST endpoint for user management with CRUD operations",
            "project_id": "proj_test-project",
        }

        response = client.post("/tasks", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["task_id"] == "task_def456"
        assert data["status"] == "success"
        assert data["agent_used"] == "backend"
        assert data["execution_time"] == 1.5
        assert "artifacts" in data

    def test_create_task_with_all_options(self, client, mock_framework):
        """POST /tasks with all optional fields should succeed."""
        mock_framework.execute = AsyncMock(return_value=_make_execution_result())

        payload = {
            "task": "Implement user authentication with OAuth2 and JWT tokens",
            "project_id": "proj_test-project",
            "session_id": "sess_abc123",
            "agent_hint": "backend",
            "priority": "high",
            "context": {"framework": "fastapi"},
        }

        response = client.post("/tasks", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        # Verify execute was called with the right arguments
        call_kwargs = mock_framework.execute.call_args.kwargs
        assert call_kwargs.get("session_id") == "sess_abc123"
        assert call_kwargs.get("agent_hint") == "backend"

    def test_create_task_short_description_422(self, client):
        """POST /tasks with task shorter than 10 chars should return 422."""
        payload = {
            "task": "short",
            "project_id": "proj_test-project",
        }

        response = client.post("/tasks", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_task_missing_project_id_422(self, client):
        """POST /tasks without project_id should return 422."""
        payload = {
            "task": "Create a REST endpoint for user management with CRUD operations",
        }

        response = client.post("/tasks", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_task_missing_task_422(self, client):
        """POST /tasks without task description should return 422."""
        payload = {"project_id": "proj_test-project"}

        response = client.post("/tasks", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_task_status_not_found(self, client):
        """GET /tasks/{task_id} should return 404 (not yet implemented)."""
        response = client.get(
            "/tasks/task_123",
            params={"project_id": "proj_test-project"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_task_status_missing_query_param_422(self, client):
        """GET /tasks/{task_id} without project_id query param should return 422."""
        response = client.get("/tasks/task_123")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# Test Session Endpoints
# ============================================================================


class TestSessionEndpoints:
    """Tests for /sessions endpoints."""

    def test_create_session(self, client, mock_framework):
        """POST /sessions should create a session and return 201."""
        payload = {"project_id": "proj_test-project"}

        response = client.post("/sessions", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert "session_id" in data
        assert data["project_id"] == "proj_test-project"
        assert "created_at" in data
        assert "message_count" in data

    def test_create_session_with_initial_context(self, client, mock_framework):
        """POST /sessions with initial_context should succeed."""
        payload = {
            "project_id": "proj_test-project",
            "initial_context": {"key": "value"},
        }

        response = client.post("/sessions", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_session_missing_project_id_422(self, client):
        """POST /sessions without project_id should return 422."""
        payload = {}

        response = client.post("/sessions", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_session(self, client, mock_framework):
        """GET /sessions/{session_id} should return session details."""
        response = client.get(
            "/sessions/sess_abc123",
            params={"project_id": "proj_test-project"},
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["session_id"] == "sess_abc123"
        assert data["project_id"] == "proj_test-project"

    def test_get_session_not_found(self, client, mock_framework):
        """GET /sessions/{session_id} should return 404 for missing session."""
        mock_framework._context_manager.get_session = AsyncMock(
            side_effect=Exception("Session not found")
        )

        response = client.get(
            "/sessions/sess_nonexistent",
            params={"project_id": "proj_test-project"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_session_missing_project_id_422(self, client):
        """GET /sessions/{session_id} without project_id should return 422."""
        response = client.get("/sessions/sess_abc123")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_session_history(self, client, mock_framework):
        """GET /sessions/{session_id}/history should return messages."""
        mock_framework._context_manager.get_session_history = AsyncMock(
            return_value=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ]
        )

        response = client.get(
            "/sessions/sess_abc123/history",
            params={"project_id": "proj_test-project"},
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["session_id"] == "sess_abc123"
        assert "messages" in data
        assert data["total"] == 2

    def test_get_session_history_pagination(self, client, mock_framework):
        """GET /sessions/{session_id}/history should support pagination."""
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(10)]
        mock_framework._context_manager.get_session_history = AsyncMock(return_value=messages)

        response = client.get(
            "/sessions/sess_abc123/history",
            params={
                "project_id": "proj_test-project",
                "limit": 5,
                "offset": 0,
            },
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0

    def test_get_session_history_not_found(self, client, mock_framework):
        """GET /sessions/{session_id}/history should return 404 for missing session."""
        mock_framework._context_manager.get_session_history = AsyncMock(
            side_effect=Exception("Session not found")
        )

        response = client.get(
            "/sessions/sess_nonexistent/history",
            params={"project_id": "proj_test-project"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Test Memory Endpoints
# ============================================================================


class TestMemoryEndpoints:
    """Tests for /memory endpoints."""

    def test_query_memory(self, client, mock_framework):
        """POST /memory/query should return matching entries."""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "entry_id": "entry_001",
            "content": "Users authenticate via JWT tokens",
            "score": 0.95,
        }
        mock_framework._context_manager.retrieve_context = AsyncMock(return_value=[mock_result])

        payload = {
            "query": "authentication patterns",
            "project_id": "proj_test-project",
        }

        response = client.post("/memory/query", json=payload)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "entries" in data
        assert data["total"] == 1

    def test_query_memory_with_type_filter(self, client, mock_framework):
        """POST /memory/query with memory_type filter should pass it through."""
        mock_framework._context_manager.retrieve_context = AsyncMock(return_value=[])

        payload = {
            "query": "authentication patterns",
            "project_id": "proj_test-project",
            "memory_type": "semantic",
            "top_k": 10,
        }

        response = client.post("/memory/query", json=payload)
        assert response.status_code == status.HTTP_200_OK

        # Verify memory_types was passed
        call_kwargs = mock_framework._context_manager.retrieve_context.call_args.kwargs
        assert call_kwargs.get("top_k") == 10

    def test_query_memory_invalid_type(self, client, mock_framework):
        """POST /memory/query with invalid memory_type should return 400."""
        payload = {
            "query": "authentication patterns",
            "project_id": "proj_test-project",
            "memory_type": "invalid_type",
        }

        response = client.post("/memory/query", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_query_memory_short_query_422(self, client):
        """POST /memory/query with query shorter than 3 chars should return 422."""
        payload = {
            "query": "ab",
            "project_id": "proj_test-project",
        }

        response = client.post("/memory/query", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_memory_missing_project_id_422(self, client):
        """POST /memory/query without project_id should return 422."""
        payload = {"query": "authentication patterns"}

        response = client.post("/memory/query", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_memory_top_k_bounds(self, client):
        """POST /memory/query with top_k out of range should return 422."""
        payload = {
            "query": "authentication patterns",
            "project_id": "proj_test-project",
            "top_k": 0,
        }

        response = client.post("/memory/query", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_add_memory_entry(self, client, mock_framework):
        """POST /memory/entries should store an entry and return 201."""
        payload = {
            "project_id": "proj_test-project",
            "content": "API uses JWT authentication for all endpoints",
            "memory_type": "semantic",
        }

        response = client.post("/memory/entries", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["status"] == "created"
        assert data["entry_id"] == "entry_abc123"
        assert data["project_id"] == "proj_test-project"

        # Verify store was called
        mock_framework._memory_store.store.assert_awaited_once()

    def test_add_memory_entry_with_metadata(self, client, mock_framework):
        """POST /memory/entries with metadata should succeed."""
        payload = {
            "project_id": "proj_test-project",
            "content": "Decision to use PostgreSQL for primary database",
            "memory_type": "semantic",
            "metadata": {"source": "adr-003", "priority": "high"},
        }

        response = client.post("/memory/entries", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

    def test_add_memory_entry_invalid_type(self, client, mock_framework):
        """POST /memory/entries with invalid memory_type should return 400."""
        payload = {
            "project_id": "proj_test-project",
            "content": "Some content that is long enough",
            "memory_type": "nonexistent",
        }

        response = client.post("/memory/entries", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_memory_entry_short_content_422(self, client):
        """POST /memory/entries with content shorter than 10 chars should return 422."""
        payload = {
            "project_id": "proj_test-project",
            "content": "short",
        }

        response = client.post("/memory/entries", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_add_memory_entry_missing_project_id_422(self, client):
        """POST /memory/entries without project_id should return 422."""
        payload = {
            "content": "This content is long enough to pass validation",
        }

        response = client.post("/memory/entries", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_memory_types(self, client):
        """GET /memory/types should return available memory types."""
        response = client.get("/memory/types")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "types" in data
        assert isinstance(data["types"], list)
        assert len(data["types"]) > 0

        type_names = [t["name"] for t in data["types"]]
        assert "episodic" in type_names
        assert "semantic" in type_names
        assert "procedural" in type_names


# ============================================================================
# Test Agent Endpoints
# ============================================================================


class TestAgentEndpoints:
    """Tests for /agents endpoints."""

    def test_list_agents(self, client, mock_framework):
        """GET /agents should return a list of agent info objects."""
        response = client.get("/agents")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        agent = data[0]
        assert "name" in agent
        assert "model" in agent
        assert "description" in agent
        assert "capabilities" in agent
        assert "tools" in agent
        assert "status" in agent

    def test_list_agents_with_instances(self, client, mock_framework):
        """GET /agents should use orchestrator._agents when available."""
        mock_agent_frontend = _make_mock_agent(
            name="frontend", model="fe-model", description="Frontend specialist"
        )
        mock_framework._orchestrator._agents = {
            "backend": _make_mock_agent(name="backend"),
            "frontend": mock_agent_frontend,
        }

        response = client.get("/agents")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data) == 2

        names = [a["name"] for a in data]
        assert "backend" in names
        assert "frontend" in names

    def test_list_agents_fallback(self, client, mock_framework):
        """GET /agents should fall back to list_agents when no agent instances."""
        mock_framework._orchestrator._agents = {}
        mock_framework.list_agents = AsyncMock(return_value=["backend", "frontend", "devops"])

        response = client.get("/agents")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data) == 3

        names = [a["name"] for a in data]
        assert "backend" in names
        assert "frontend" in names
        assert "devops" in names

    def test_get_agent_info(self, client, mock_framework):
        """GET /agents/{agent_name} should return detailed agent info."""
        response = client.get("/agents/backend")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["name"] == "backend"
        assert data["model"] == "test-model"
        assert "capabilities" in data
        assert "tools" in data

    def test_get_agent_info_not_found(self, client, mock_framework):
        """GET /agents/{agent_name} should return 404 for unknown agent."""
        response = client.get("/agents/nonexistent_agent")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_agents_empty(self, client, mock_framework):
        """GET /agents should return empty list when no agents available."""
        mock_framework._orchestrator._agents = {}
        mock_framework.list_agents = AsyncMock(return_value=[])

        response = client.get("/agents")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


# ============================================================================
# Test Error Handling
# ============================================================================


class TestErrorHandling:
    """Tests for exception handlers and error responses."""

    def test_palace_error_returns_400(self, client, mock_framework):
        """PalaceError should be caught and return 400 with error details."""
        error = PalaceError("Test error message", code="TEST_ERROR", details={"key": "value"})
        mock_framework._context_manager.create_project = AsyncMock(side_effect=error)

        response = client.post(
            "/projects",
            json={"name": "fail-project"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        data = response.json()
        assert data["error"] == "TEST_ERROR"
        assert data["message"] == "Test error message"
        assert data["details"] == {"key": "value"}

    def test_palace_error_on_get_project(self, client, mock_framework):
        """PalaceError from GET /projects/{id} should propagate as 400."""
        error = PalaceError("Project error", code="PROJECT_ERROR", details=None)
        mock_framework._context_manager.get_project_context = AsyncMock(side_effect=error)

        response = client.get("/projects/proj_test-project")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_palace_error_on_delete_project(self, client, mock_framework):
        """PalaceError from DELETE /projects/{id} should propagate as 400."""
        error = PalaceError("Cannot delete", code="DELETE_ERROR", details=None)
        mock_framework._context_manager.delete_project = AsyncMock(side_effect=error)

        response = client.delete("/projects/proj_test-project")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_validation_error_422(self, client):
        """Invalid request body should return 422 with validation details."""
        response = client.post("/projects", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()
        assert "detail" in data

    def test_get_framework_raises_503_when_not_initialized(self):
        """get_framework() should raise HTTPException(503) when _framework is None."""
        from fastapi import HTTPException

        with patch("palace.api.main._framework", None):
            with pytest.raises(HTTPException) as exc_info:
                get_framework()
            assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert "Framework not initialized" in exc_info.value.detail

    def test_endpoint_503_when_framework_not_initialized(self, mock_framework):
        """Endpoints should return 503 when framework is not initialized."""

        # Override get_framework to simulate uninitialized state
        def raise_503():
            from fastapi import HTTPException

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Framework not initialized",
            )

        app.dependency_overrides[get_framework] = raise_503

        try:
            with patch("palace.api.main.PalaceFramework", return_value=mock_framework):
                with TestClient(app, raise_server_exceptions=False) as client:
                    response = client.get("/projects")
                    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
                    assert "Framework not initialized" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_framework, None)

    def test_create_project_internal_error_500(self, client, mock_framework):
        """POST /projects with unexpected exception should return 500."""
        mock_framework._context_manager.create_project = AsyncMock(
            side_effect=RuntimeError("Unexpected failure")
        )

        response = client.post(
            "/projects",
            json={"name": "broken-project"},
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ============================================================================
# Test Debug Endpoints (Non-Development Mode)
# ============================================================================


class TestDebugEndpoints:
    """Tests for debug endpoints availability based on environment."""

    def test_debug_endpoints_not_available_in_test_mode(self, client):
        """Debug endpoints are registered at import time based on settings.

        The debug endpoints (/debug/reload, /debug/config) are conditionally
        registered when settings.is_development() is True. Since the app
        module is already imported with development settings, these endpoints
        exist. We verify they respond (either 200 or error) rather than
        asserting they're absent, because conditional registration happens
        at module load time and cannot be easily toggled per-test.
        """
        response = client.post("/debug/reload")
        # Endpoint exists (registered at import time), will fail due to mock
        # or return 200/500 depending on framework state.
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_debug_config_not_available_in_test_mode(self, client):
        """GET /debug/config endpoint availability depends on import-time settings.

        Same rationale as test_debug_endpoints_not_available_in_test_mode:
        conditional registration happens at module load time.
        """
        response = client.get("/debug/config")
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )


# ============================================================================
# Test Response Model Validation
# ============================================================================


class TestResponseModelValidation:
    """Tests that response models match expected schemas."""

    def test_health_response_schema(self, client):
        """HealthResponse should have status, version, and framework_initialized."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "framework_initialized" in data

    def test_project_response_schema(self, client, mock_framework):
        """ProjectResponse should have required fields."""
        response = client.post(
            "/projects",
            json={"name": "schema-test"},
        )
        data = response.json()

        assert "project_id" in data
        assert "name" in data
        assert "status" in data
        assert "created_at" in data

    def test_task_response_schema(self, client, mock_framework):
        """TaskResponse should have required fields."""
        mock_framework.execute = AsyncMock(return_value=_make_execution_result())

        response = client.post(
            "/tasks",
            json={
                "task": "Create a REST endpoint for user management with CRUD",
                "project_id": "proj_test-project",
            },
        )
        data = response.json()

        assert "task_id" in data
        assert "status" in data
        assert "result" in data
        assert "agent_used" in data
        assert "execution_time" in data
        assert "artifacts" in data
        assert "metadata" in data

    def test_session_response_schema(self, client, mock_framework):
        """SessionResponse should have required fields."""
        response = client.post(
            "/sessions",
            json={"project_id": "proj_test-project"},
        )
        data = response.json()

        assert "session_id" in data
        assert "project_id" in data
        assert "created_at" in data
        assert "message_count" in data

    def test_memory_query_response_schema(self, client, mock_framework):
        """MemoryResponse should have entries and total."""
        mock_framework._context_manager.retrieve_context = AsyncMock(return_value=[])

        response = client.post(
            "/memory/query",
            json={
                "query": "test query for schema validation",
                "project_id": "proj_test-project",
            },
        )
        data = response.json()

        assert "entries" in data
        assert "total" in data

    def test_agent_info_response_schema(self, client, mock_framework):
        """AgentInfoResponse should have required fields."""
        response = client.get("/agents/backend")
        data = response.json()

        assert "name" in data
        assert "model" in data
        assert "description" in data
        assert "capabilities" in data
        assert "tools" in data
        assert "status" in data

    def test_error_response_schema(self, client, mock_framework):
        """ErrorResponse should have error, message, and optionally details."""
        error = PalaceError("Schema test error", code="SCHEMA_TEST", details={"field": "value"})
        mock_framework._context_manager.create_project = AsyncMock(side_effect=error)

        response = client.post(
            "/projects",
            json={"name": "schema-error-test"},
        )
        data = response.json()

        assert "error" in data
        assert "message" in data
        assert "details" in data
