"""
Palace Framework - Shared Pytest Fixtures and Mock Helpers

This module provides reusable fixtures for the entire test suite,
including mock settings, memory stores, LLM clients, and sample
context paths.

NOTE: The palace and palace.core __init__.py files contain broken
imports that reference symbols not yet implemented. To avoid ImportErrors
cascading through the test suite, we pre-register minimal package stubs
in sys.modules before importing any palace submodules. This prevents the
broken __init__.py files from being executed while still allowing direct
submodule imports (e.g. from palace.core.config import Settings).
"""

import asyncio
import importlib
import importlib.util
import sys
import types
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Bootstrap: Register stub package modules so that importing
# palace.core.config / palace.core.types / palace.core.exceptions
# works without triggering the broken palace/__init__.py or
# palace/core/__init__.py (which import non-existent symbols).
# ---------------------------------------------------------------------------
_SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
_PALACE_PKG = _SRC_ROOT / "palace"
_PALACE_CORE_PKG = _PALACE_PKG / "core"


def _ensure_package(module_name: str, path: list[str]) -> types.ModuleType:
    """Return an existing module or create & register a minimal stub package."""
    if module_name in sys.modules:
        return sys.modules[module_name]
    mod = types.ModuleType(module_name)
    mod.__path__ = path
    mod.__package__ = module_name
    sys.modules[module_name] = mod
    return mod


_ensure_package("palace", [str(_PALACE_PKG)])
_ensure_package("palace.core", [str(_PALACE_CORE_PKG)])

# Now safe to import submodules directly — the package stubs prevent
# the broken __init__.py from running.
from palace.core.config import (  # noqa: E402
    APIConfig,
    CLIConfig,
    DatabaseConfig,
    LoggingConfig,
    MemoryConfig,
    OllamaConfig,
    ProjectsConfig,
    SecurityConfig,
    Settings,
)
from palace.core.config import (
    ModelConfig as ConfigModelConfig,
)
from palace.core.types import (  # noqa: E402
    AgentCapability,
    AgentResult,
    AgentRole,
    MemoryEntry,
    MemoryType,
    Message,
    MessageType,
    ProjectConfig,
    ProjectContext,
    SessionContext,
    TaskDefinition,
    TaskPriority,
    TaskStatus,
)

# ============================================================================
# Event Loop Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Ensure an asyncio event loop is available for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Settings Fixtures
# ============================================================================


@pytest.fixture
def mock_ollama_config() -> OllamaConfig:
    """OllamaConfig with test-friendly defaults."""
    return OllamaConfig(
        base_url="http://localhost:11434",
        api_key=None,
        timeout=30,
        max_retries=1,
    )


@pytest.fixture
def mock_model_config() -> ConfigModelConfig:
    """ModelConfig with test-friendly defaults."""
    return ConfigModelConfig(
        orchestrator="test-model",
        devops="test-model",
        backend="test-model",
        frontend="test-model",
        infra="test-model",
        dba="test-model",
        qa="test-model",
        designer="test-model",
        reviewer="test-model",
        embedding="test-embedding-model",
    )


@pytest.fixture
def mock_memory_config() -> MemoryConfig:
    """MemoryConfig with test-friendly defaults."""
    return MemoryConfig(
        store_type="sqlite",
        local_memory_path=":memory:",
        collection_name="test_palace_memory",
        embedding_dimension=128,
        chunk_size=500,
        chunk_overlap=50,
    )


@pytest.fixture
def mock_settings(
    mock_ollama_config,
    mock_model_config,
    mock_memory_config,
) -> Settings:
    """Settings fixture with test defaults.

    Provides a fully configured Settings instance suitable for
    unit and integration tests without hitting real services.
    """
    return Settings(
        environment="test",
        ollama=mock_ollama_config,
        model=mock_model_config,
        memory=mock_memory_config,
        database=DatabaseConfig(
            database_url="sqlite+aiosqlite:///./data/test_palace.db",
            database_echo=False,
        ),
        api=APIConfig(
            host="127.0.0.1",
            port=8001,
            debug=True,
            cors_origins=["http://localhost:3000"],
        ),
        cli=CLIConfig(
            default_project="test-project",
            output_format="text",
            verbose=True,
        ),
        logging=LoggingConfig(
            level="DEBUG",
            format="text",
        ),
        projects=ProjectsConfig(
            base_path="./test_projects",
            max_projects=10,
            auto_create=False,
        ),
        security=SecurityConfig(
            secret_key="test-secret-key-for-testing-only",
            require_authentication=False,
        ),
    )


# ============================================================================
# Memory Store Mock Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def mock_memory_store():
    """Async mock of MemoryStore that returns sensible defaults.

    Provides pre-configured AsyncMock methods for store, search,
    retrieve, count, and other common memory operations.
    """
    store = MagicMock()

    # Async methods
    store.initialize = AsyncMock()
    store.close = AsyncMock()

    store.store = AsyncMock(return_value="test-entry-id-1234")
    store.search = AsyncMock(
        return_value=[
            {
                "entry_id": "test-entry-id-1234",
                "content": "Test memory content",
                "memory_type": "semantic",
                "metadata": {"source": "test"},
                "score": 0.95,
            }
        ]
    )
    store.retrieve = AsyncMock(
        return_value={
            "entry_id": "test-entry-id-1234",
            "content": "Test memory content",
            "memory_type": "semantic",
            "metadata": {"source": "test"},
        }
    )
    store.count = AsyncMock(return_value=42)
    store.delete = AsyncMock(return_value=True)
    store.clear = AsyncMock()

    # Property mocks
    store._initialized = True
    store._settings = None
    store._store_type = "sqlite"

    return store


# ============================================================================
# LLM Client Mock Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def mock_llm_client():
    """Async mock of LLM client that returns sample responses.

    Provides pre-configured AsyncMock methods for generate,
    chat, stream, and other common LLM operations.
    """
    client = MagicMock()

    # Sample response data
    sample_response = MagicMock()
    sample_response.content = "This is a test LLM response."
    sample_response.request_id = "test-request-id"
    sample_response.model = "test-model"
    sample_response.provider = "test-provider"
    sample_response.tokens_used = 100
    sample_response.finish_reason = "stop"
    sample_response.success = True
    sample_response.error = None

    # Async methods
    client.initialize = AsyncMock()
    client.close = AsyncMock()
    client.generate = AsyncMock(return_value=sample_response)
    client.chat = AsyncMock(return_value=sample_response)
    client.stream = AsyncMock()

    # Make stream return an async generator
    async def _mock_stream_generator(*args, **kwargs):
        chunks = [
            MagicMock(content="chunk1", finish_reason=None),
            MagicMock(content="chunk2", finish_reason=None),
            MagicMock(content="chunk3", finish_reason="stop"),
        ]
        for chunk in chunks:
            yield chunk

    client.stream.side_effect = _mock_stream_generator

    # Cost tracking
    client.total_cost = 0.0
    client.total_tokens = 0

    return client


# ============================================================================
# Sample Context Path Fixtures
# ============================================================================


@pytest.fixture
def sample_context_path(tmp_path):
    """Create a fake /ai_context/ directory with standard context files.

    Creates the following structure under tmp_path:
        ai_context/
        +-- architecture.md
        +-- stack.md
        +-- conventions.md
        +-- decisions.md
        +-- constraints.md
    """
    context_dir = tmp_path / "ai_context"
    context_dir.mkdir()

    # Create sample context files with realistic content
    context_files = {
        "architecture.md": (
            "# Architecture\n\n"
            "## Overview\n"
            "This project follows a clean architecture pattern.\n\n"
            "## Layers\n"
            "- Domain Layer: Core business logic\n"
            "- Application Layer: Use cases and services\n"
            "- Infrastructure Layer: External integrations\n"
            "- Presentation Layer: API endpoints\n"
        ),
        "stack.md": (
            "# Technology Stack\n\n"
            "## Backend\n"
            "- Python 3.11+\n"
            "- FastAPI\n"
            "- SQLAlchemy\n"
            "- Pydantic\n\n"
            "## Frontend\n"
            "- React\n"
            "- TypeScript\n\n"
            "## Infrastructure\n"
            "- Docker\n"
            "- Kubernetes\n"
        ),
        "conventions.md": (
            "# Coding Conventions\n\n"
            "## General\n"
            "- Use type hints for all function signatures\n"
            "- Write docstrings for all public modules and functions\n"
            "- Follow PEP 8 style guide\n\n"
            "## Testing\n"
            "- Use pytest for all tests\n"
            "- Maintain 80% code coverage\n"
            "- Write integration tests for API endpoints\n"
        ),
        "decisions.md": (
            "# Architecture Decision Records\n\n"
            "## ADR-001: Use FastAPI for REST API\n"
            "- Status: Accepted\n"
            "- Context: Need a modern async Python web framework\n"
            "- Decision: Use FastAPI with Pydantic models\n\n"
            "## ADR-002: Use SQLAlchemy 2.0+ async\n"
            "- Status: Accepted\n"
            "- Context: Need async database access\n"
            "- Decision: Use SQLAlchemy with async sessions\n"
        ),
        "constraints.md": (
            "# Project Constraints\n\n"
            "## Performance\n"
            "- API response time < 200ms for 95th percentile\n"
            "- Support at least 100 concurrent users\n\n"
            "## Security\n"
            "- All endpoints must require authentication in production\n"
            "- Use OAuth 2.0 with JWT tokens\n"
            "- Encrypt all sensitive data at rest\n"
        ),
    }

    for filename, content in context_files.items():
        filepath = context_dir / filename
        filepath.write_text(content, encoding="utf-8")

    return context_dir


# ============================================================================
# Sample Model / Type Instance Fixtures
# ============================================================================


@pytest.fixture
def sample_project_config() -> ProjectConfig:
    """ProjectConfig with test defaults."""
    return ProjectConfig(
        name="test-project",
        description="A test project for the Palace Framework",
        backend_framework="fastapi",
        frontend_framework="react",
        database="postgresql",
        deployment="docker",
        root_path="/tmp/test-project",
        source_path="src",
        tests_path="tests",
        code_style="pep8",
        test_framework="pytest",
    )


@pytest.fixture
def sample_project_context(sample_project_config) -> ProjectContext:
    """ProjectContext with test defaults."""
    return ProjectContext(
        config=sample_project_config,
        adrs=[{"id": "ADR-001", "title": "Use FastAPI", "status": "accepted"}],
        patterns=["repository", "factory", "observer"],
        instructions=["Follow PEP 8", "Write tests first"],
    )


@pytest.fixture
def sample_session_context(sample_project_config) -> SessionContext:
    """SessionContext with test defaults."""
    return SessionContext(
        project_id=sample_project_config.project_id,
        current_agent="orchestrator",
        agent_history=["orchestrator", "backend"],
    )


@pytest.fixture
def sample_task_definition(sample_project_config, sample_session_context) -> TaskDefinition:
    """TaskDefinition with test defaults."""
    return TaskDefinition(
        title="Implement user login endpoint",
        description="Create a POST /api/v1/auth/login endpoint that validates credentials",
        required_capabilities={AgentCapability.BACKEND_DEVELOPMENT},
        suggested_agent=AgentRole.BACKEND,
        priority=TaskPriority.HIGH,
        project_id=sample_project_config.project_id,
        session_id=sample_session_context.session_id,
    )


@pytest.fixture
def sample_agent_result() -> AgentResult:
    """AgentResult with test defaults."""
    return AgentResult(
        success=True,
        content="Successfully implemented the login endpoint",
        agent=AgentRole.BACKEND,
        model_used="test-model",
        tokens_used=250,
        execution_time_ms=1500,
    )


@pytest.fixture
def sample_message(sample_session_context) -> Message:
    """Message with test defaults."""
    return Message(
        session_id=sample_session_context.session_id,
        role=MessageType.USER,
        content="Please implement a user login endpoint",
    )


@pytest.fixture
def sample_memory_entry(sample_project_config) -> MemoryEntry:
    """MemoryEntry with test defaults."""
    return MemoryEntry(
        memory_type=MemoryType.SEMANTIC,
        project_id=sample_project_config.project_id,
        content="Users authenticate via JWT tokens",
        source="backend_agent",
    )


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def freeze_time():
    """Fixture to freeze datetime.utcnow for deterministic tests.

    Usage:
        with freeze_time(datetime(2024, 1, 1, 12, 0, 0)):
            # time is frozen in this block
            pass
    """
    from contextlib import contextmanager
    from unittest.mock import patch

    @contextmanager
    def _freeze_time(frozen_dt: datetime):
        with patch("palace.core.types.datetime") as mock_dt:
            mock_dt.utcnow.return_value = frozen_dt
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            yield frozen_dt

    return _freeze_time
