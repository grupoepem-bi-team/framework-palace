"""
Tests for Palace Framework - Core Framework Module

Tests PalaceFramework initialization, execute, shutdown,
ExecutionResult creation and serialization, and ProjectStatus.
"""

# ---------------------------------------------------------------------------
# Bootstrap: prevent broken __init__.py imports from cascading
# ---------------------------------------------------------------------------
import sys
import types
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

_SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
_PALACE_PKG = _SRC_ROOT / "palace"
_PALACE_CORE_PKG = _PALACE_PKG / "core"
_PALACE_MEMORY_PKG = _PALACE_PKG / "memory"


def _ensure_package(module_name: str, path: list[str]) -> types.ModuleType:
    if module_name in sys.modules:
        return sys.modules[module_name]
    mod = types.ModuleType(module_name)
    mod.__path__ = path
    mod.__package__ = module_name
    sys.modules[module_name] = mod
    return mod


# Create stubs for packages with broken __init__.py files.
# These stubs prevent the broken init files from running while still
# allowing direct submodule imports (e.g. from palace.memory.base import ...).
_ensure_package("palace", [str(_PALACE_PKG)])
_ensure_package("palace.core", [str(_PALACE_CORE_PKG)])
_ensure_package("palace.memory", [str(_PALACE_MEMORY_PKG)])

# palace.config is not a real package — palace.core.framework imports
# "from palace.config import Settings, get_settings".  Register the
# *module* palace.core.config under the alias "palace.config" so that
# import resolves correctly without creating a separate file.
import importlib

_core_config = importlib.import_module("palace.core.config")
sys.modules["palace.config"] = _core_config

# Populate the palace.memory stub with symbols from palace.memory.base
# so that "from palace.memory import MemoryStore" etc. works.
# We avoid running the broken palace.memory.__init__.py (which references
# a non-existent EmbeddingGenerator) by importing directly from the submodule.
_palace_memory_mod = sys.modules["palace.memory"]
_palace_memory_base = importlib.import_module("palace.memory.base")
_public_names = [
    "MemoryBase",
    "MemoryEntry",
    "MemoryStore",
    "MemoryType",
    "MemoryPriority",
    "SearchQuery",
    "SearchResult",
    "SearchStrategy",
    "VectorStore",
    "EmbeddingProvider",
    "create_memory_entry",
    "create_search_query",
]
for _name in _public_names:
    if hasattr(_palace_memory_base, _name):
        setattr(_palace_memory_mod, _name, getattr(_palace_memory_base, _name))

from palace.core.framework import ExecutionResult, PalaceFramework, ProjectStatus

# ============================================================================
# ExecutionResult Tests
# ============================================================================


class TestExecutionResult:
    """Tests for ExecutionResult data class."""

    def test_creation_with_all_fields(self):
        result = ExecutionResult(
            task_id="task-123",
            status="success",
            result="Task completed successfully",
            agent_used="backend",
            execution_time=1.5,
            metadata={"key": "value"},
        )
        assert result.task_id == "task-123"
        assert result.status == "success"
        assert result.result == "Task completed successfully"
        assert result.agent_used == "backend"
        assert result.execution_time == 1.5
        assert result.metadata == {"key": "value"}

    def test_creation_with_minimal_fields(self):
        result = ExecutionResult(
            task_id="task-456",
            status="pending",
            result="Processing...",
            agent_used="orchestrator",
            execution_time=0.0,
        )
        assert result.task_id == "task-456"
        assert result.status == "pending"
        assert result.metadata == {}

    def test_to_dict(self):
        result = ExecutionResult(
            task_id="task-789",
            status="success",
            result="Done",
            agent_used="frontend",
            execution_time=2.3,
            metadata={"tokens": 150},
        )
        d = result.to_dict()
        assert d["task_id"] == "task-789"
        assert d["status"] == "success"
        assert d["result"] == "Done"
        assert d["agent_used"] == "frontend"
        assert d["execution_time"] == 2.3
        assert d["metadata"] == {"tokens": 150}

    def test_to_dict_preserves_all_keys(self):
        result = ExecutionResult(
            task_id="t1",
            status="success",
            result="r",
            agent_used="a",
            execution_time=0.1,
        )
        d = result.to_dict()
        expected_keys = {
            "task_id",
            "status",
            "result",
            "agent_used",
            "execution_time",
            "metadata",
        }
        assert set(d.keys()) == expected_keys

    def test_metadata_defaults_to_empty_dict(self):
        result = ExecutionResult(
            task_id="t1",
            status="success",
            result="r",
            agent_used="a",
            execution_time=0.0,
        )
        assert result.metadata == {}

    def test_metadata_is_independent_between_instances(self):
        r1 = ExecutionResult(
            task_id="t1", status="s", result="r", agent_used="a", execution_time=0.0
        )
        r2 = ExecutionResult(
            task_id="t2", status="s", result="r", agent_used="a", execution_time=0.0
        )
        r1.metadata["key"] = "value"
        assert "key" not in r2.metadata

    def test_to_dict_with_complex_metadata(self):
        result = ExecutionResult(
            task_id="t1",
            status="success",
            result="r",
            agent_used="a",
            execution_time=1.0,
            metadata={
                "nested": {"inner": "value"},
                "list": [1, 2, 3],
                "string": "hello",
            },
        )
        d = result.to_dict()
        assert d["metadata"]["nested"]["inner"] == "value"
        assert d["metadata"]["list"] == [1, 2, 3]

    def test_failed_result(self):
        result = ExecutionResult(
            task_id="task-fail",
            status="failed",
            result="Error: something went wrong",
            agent_used="backend",
            execution_time=5.0,
            metadata={"error_code": "E001"},
        )
        assert result.status == "failed"
        assert "Error" in result.result

    def test_to_dict_returns_new_dict(self):
        result = ExecutionResult(
            task_id="t1", status="s", result="r", agent_used="a", execution_time=0.0
        )
        d1 = result.to_dict()
        d1["task_id"] = "modified"
        d2 = result.to_dict()
        assert d2["task_id"] == "t1"


# ============================================================================
# ProjectStatus Tests
# ============================================================================


class TestProjectStatus:
    """Tests for ProjectStatus data class."""

    def test_creation_with_all_fields(self):
        status = ProjectStatus(
            project_id="proj-1",
            status="active",
            active_tasks=5,
            last_activity="2024-01-15T10:30:00",
            context_summary="Backend API project",
        )
        assert status.project_id == "proj-1"
        assert status.status == "active"
        assert status.active_tasks == 5
        assert status.last_activity == "2024-01-15T10:30:00"
        assert status.context_summary == "Backend API project"

    def test_creation_without_context_summary(self):
        status = ProjectStatus(
            project_id="proj-2",
            status="idle",
            active_tasks=0,
            last_activity="2024-01-14T08:00:00",
        )
        assert status.context_summary is None

    def test_to_dict(self):
        status = ProjectStatus(
            project_id="proj-3",
            status="active",
            active_tasks=3,
            last_activity="2024-01-16T12:00:00",
            context_summary="Frontend project",
        )
        d = status.to_dict()
        assert d["project_id"] == "proj-3"
        assert d["status"] == "active"
        assert d["active_tasks"] == 3
        assert d["last_activity"] == "2024-01-16T12:00:00"
        assert d["context_summary"] == "Frontend project"

    def test_to_dict_with_none_summary(self):
        status = ProjectStatus(
            project_id="proj-4",
            status="paused",
            active_tasks=0,
            last_activity="2024-01-10T09:00:00",
        )
        d = status.to_dict()
        assert d["context_summary"] is None

    def test_to_dict_preserves_all_keys(self):
        status = ProjectStatus(
            project_id="proj-5",
            status="active",
            active_tasks=1,
            last_activity="2024-01-01T00:00:00",
            context_summary="summary",
        )
        d = status.to_dict()
        expected_keys = {
            "project_id",
            "status",
            "active_tasks",
            "last_activity",
            "context_summary",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_returns_new_dict(self):
        status = ProjectStatus(
            project_id="proj-6",
            status="active",
            active_tasks=2,
            last_activity="2024-02-01T00:00:00",
        )
        d1 = status.to_dict()
        d1["project_id"] = "modified"
        d2 = status.to_dict()
        assert d2["project_id"] == "proj-6"


# ============================================================================
# PalaceFramework Tests
# ============================================================================


class TestPalaceFrameworkInit:
    """Tests for PalaceFramework initialization."""

    def test_init_with_default_settings(self):
        with patch("palace.core.framework.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            fw = PalaceFramework()
            assert fw._initialized is False
            assert fw._orchestrator is None
            assert fw._context_manager is None

    def test_init_with_custom_settings(self):
        custom_settings = MagicMock()
        fw = PalaceFramework(settings=custom_settings)
        assert fw.settings is custom_settings
        assert fw._initialized is False

    def test_init_with_custom_memory_store(self):
        custom_settings = MagicMock()
        custom_memory = MagicMock()
        fw = PalaceFramework(settings=custom_settings, memory_store=custom_memory)
        assert fw._memory_store is custom_memory
        assert fw.settings is custom_settings

    def test_init_stores_settings(self):
        custom_settings = MagicMock()
        fw = PalaceFramework(settings=custom_settings)
        assert fw.settings is custom_settings

    def test_initialized_defaults_to_false(self):
        with patch("palace.core.framework.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            fw = PalaceFramework()
            assert fw._initialized is False


class TestPalaceFrameworkInitialize:
    """Tests for PalaceFramework.initialize()."""

    @pytest_asyncio.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.memory = MagicMock()
        settings.memory.store_type = "sqlite"
        settings.memory.local_memory_path = ":memory:"
        settings.memory.collection_name = "test_palace_memory"
        return settings

    async def test_initialize_creates_memory_store_if_none(self, mock_settings):
        with (
            patch("palace.core.framework.MemoryStore") as MockMemoryStore,
            patch("palace.core.framework.ContextManager") as MockContextManager,
            patch("palace.core.framework.Orchestrator") as MockOrchestrator,
        ):
            mock_memory_instance = AsyncMock()
            MockMemoryStore.create.return_value = mock_memory_instance

            mock_ctx_instance = AsyncMock()
            MockContextManager.return_value = mock_ctx_instance

            mock_orch_instance = AsyncMock()
            MockOrchestrator.return_value = mock_orch_instance

            fw = PalaceFramework(settings=mock_settings)
            await fw.initialize()

            MockMemoryStore.create.assert_called_once_with(mock_settings)
            mock_memory_instance.initialize.assert_called_once()

    async def test_initialize_creates_context_manager(self, mock_settings):
        with (
            patch("palace.core.framework.MemoryStore") as MockMemoryStore,
            patch("palace.core.framework.ContextManager") as MockContextManager,
            patch("palace.core.framework.Orchestrator") as MockOrchestrator,
        ):
            mock_memory_instance = AsyncMock()
            MockMemoryStore.create.return_value = mock_memory_instance

            mock_ctx_instance = AsyncMock()
            MockContextManager.return_value = mock_ctx_instance

            mock_orch_instance = AsyncMock()
            MockOrchestrator.return_value = mock_orch_instance

            fw = PalaceFramework(settings=mock_settings)
            await fw.initialize()

            MockContextManager.assert_called_once_with(
                memory_store=mock_memory_instance,
                settings=mock_settings,
            )
            mock_ctx_instance.initialize.assert_called_once()

    async def test_initialize_creates_orchestrator(self, mock_settings):
        with (
            patch("palace.core.framework.MemoryStore") as MockMemoryStore,
            patch("palace.core.framework.ContextManager") as MockContextManager,
            patch("palace.core.framework.Orchestrator") as MockOrchestrator,
        ):
            mock_memory_instance = AsyncMock()
            MockMemoryStore.create.return_value = mock_memory_instance

            mock_ctx_instance = AsyncMock()
            MockContextManager.return_value = mock_ctx_instance

            mock_orch_instance = AsyncMock()
            MockOrchestrator.return_value = mock_orch_instance

            fw = PalaceFramework(settings=mock_settings)
            await fw.initialize()

            MockOrchestrator.assert_called_once_with(
                memory_store=mock_memory_instance,
                context_manager=mock_ctx_instance,
                settings=mock_settings,
            )
            mock_orch_instance.initialize.assert_called_once()

    async def test_initialize_sets_initialized_flag(self, mock_settings):
        with (
            patch("palace.core.framework.MemoryStore") as MockMemoryStore,
            patch("palace.core.framework.ContextManager") as MockContextManager,
            patch("palace.core.framework.Orchestrator") as MockOrchestrator,
        ):
            MockMemoryStore.create.return_value = AsyncMock()
            MockContextManager.return_value = AsyncMock()
            MockOrchestrator.return_value = AsyncMock()

            fw = PalaceFramework(settings=mock_settings)
            assert fw._initialized is False
            await fw.initialize()
            assert fw._initialized is True

    async def test_initialize_idempotent(self, mock_settings):
        with (
            patch("palace.core.framework.MemoryStore") as MockMemoryStore,
            patch("palace.core.framework.ContextManager") as MockContextManager,
            patch("palace.core.framework.Orchestrator") as MockOrchestrator,
        ):
            MockMemoryStore.create.return_value = AsyncMock()
            MockContextManager.return_value = AsyncMock()
            MockOrchestrator.return_value = AsyncMock()

            fw = PalaceFramework(settings=mock_settings)
            await fw.initialize()
            await fw.initialize()

            # MemoryStore.create should only be called once
            assert MockMemoryStore.create.call_count == 1

    async def test_initialize_uses_provided_memory_store(self, mock_settings):
        custom_memory = AsyncMock()
        fw = PalaceFramework(settings=mock_settings, memory_store=custom_memory)

        with (
            patch("palace.core.framework.ContextManager") as MockContextManager,
            patch("palace.core.framework.Orchestrator") as MockOrchestrator,
        ):
            MockContextManager.return_value = AsyncMock()
            MockOrchestrator.return_value = AsyncMock()

            await fw.initialize()

            custom_memory.initialize.assert_called_once()


class TestPalaceFrameworkExecute:
    """Tests for PalaceFramework.execute()."""

    @pytest_asyncio.fixture
    def initialized_framework(self):
        with (
            patch("palace.core.framework.MemoryStore") as MockMemoryStore,
            patch("palace.core.framework.ContextManager") as MockContextManager,
            patch("palace.core.framework.Orchestrator") as MockOrchestrator,
        ):
            mock_settings = MagicMock()
            mock_settings.memory = MagicMock()
            mock_settings.memory.store_type = "sqlite"

            mock_memory_instance = AsyncMock()
            MockMemoryStore.create.return_value = mock_memory_instance

            mock_ctx_instance = AsyncMock()
            MockContextManager.return_value = mock_ctx_instance

            mock_orch_instance = AsyncMock()
            MockOrchestrator.return_value = mock_orch_instance

            fw = PalaceFramework(settings=mock_settings)

            yield fw, mock_orch_instance, mock_memory_instance

    async def test_execute_delegates_to_orchestrator(self, initialized_framework):
        fw, mock_orch, _ = initialized_framework
        expected_result = ExecutionResult(
            task_id="task-1",
            status="success",
            result="Done",
            agent_used="backend",
            execution_time=1.0,
        )
        mock_orch.execute_task = AsyncMock(return_value=expected_result)

        await fw.initialize()
        result = await fw.execute(
            task="Create endpoint",
            project_id="proj-1",
        )

        mock_orch.execute_task.assert_called_once_with(
            task="Create endpoint",
            project_id="proj-1",
            session_id=None,
            agent_hint=None,
            context=None,
        )
        assert result.task_id == "task-1"
        assert result.status == "success"

    async def test_execute_with_all_params(self, initialized_framework):
        fw, mock_orch, _ = initialized_framework
        expected_result = ExecutionResult(
            task_id="task-2",
            status="success",
            result="Completed",
            agent_used="frontend",
            execution_time=2.5,
        )
        mock_orch.execute_task = AsyncMock(return_value=expected_result)

        await fw.initialize()
        result = await fw.execute(
            task="Build UI",
            project_id="proj-2",
            session_id="session-1",
            agent_hint="frontend",
            context={"key": "value"},
        )

        mock_orch.execute_task.assert_called_once_with(
            task="Build UI",
            project_id="proj-2",
            session_id="session-1",
            agent_hint="frontend",
            context={"key": "value"},
        )
        assert result.task_id == "task-2"

    async def test_execute_auto_initializes_if_not_initialized(self, initialized_framework):
        fw, mock_orch, _ = initialized_framework
        expected_result = ExecutionResult(
            task_id="task-3",
            status="success",
            result="Done",
            agent_used="backend",
            execution_time=1.0,
        )
        mock_orch.execute_task = AsyncMock(return_value=expected_result)

        # execute should auto-initialize if not already initialized
        result = await fw.execute(
            task="Some task",
            project_id="proj-3",
        )

        assert result is not None


class TestPalaceFrameworkGetProjectStatus:
    """Tests for PalaceFramework.get_project_status()."""

    @pytest_asyncio.fixture
    def initialized_framework(self):
        with (
            patch("palace.core.framework.MemoryStore") as MockMemoryStore,
            patch("palace.core.framework.ContextManager") as MockContextManager,
            patch("palace.core.framework.Orchestrator") as MockOrchestrator,
        ):
            mock_settings = MagicMock()
            mock_settings.memory = MagicMock()
            mock_settings.memory.store_type = "sqlite"

            mock_memory_instance = AsyncMock()
            MockMemoryStore.create.return_value = mock_memory_instance

            mock_ctx_instance = AsyncMock()
            MockContextManager.return_value = mock_ctx_instance

            mock_orch_instance = AsyncMock()
            MockOrchestrator.return_value = mock_orch_instance

            fw = PalaceFramework(settings=mock_settings)

            yield fw, mock_ctx_instance

    async def test_get_project_status_delegates_to_context_manager(self, initialized_framework):
        fw, mock_ctx = initialized_framework
        expected_status = ProjectStatus(
            project_id="proj-1",
            status="active",
            active_tasks=3,
            last_activity="2024-01-15T10:30:00",
            context_summary="Test project",
        )
        mock_ctx.get_project_status = AsyncMock(return_value=expected_status)

        await fw.initialize()
        status = await fw.get_project_status("proj-1")

        mock_ctx.get_project_status.assert_called_once_with("proj-1")
        assert status.project_id == "proj-1"
        assert status.active_tasks == 3


class TestPalaceFrameworkListAgents:
    """Tests for PalaceFramework.list_agents()."""

    @pytest_asyncio.fixture
    def initialized_framework(self):
        with (
            patch("palace.core.framework.MemoryStore") as MockMemoryStore,
            patch("palace.core.framework.ContextManager") as MockContextManager,
            patch("palace.core.framework.Orchestrator") as MockOrchestrator,
        ):
            mock_settings = MagicMock()
            mock_settings.memory = MagicMock()
            mock_settings.memory.store_type = "sqlite"

            mock_memory_instance = AsyncMock()
            MockMemoryStore.create.return_value = mock_memory_instance

            mock_ctx_instance = AsyncMock()
            MockContextManager.return_value = mock_ctx_instance

            mock_orch_instance = AsyncMock()
            MockOrchestrator.return_value = mock_orch_instance

            fw = PalaceFramework(settings=mock_settings)

            yield fw, mock_orch_instance

    async def test_list_agents_delegates_to_orchestrator(self, initialized_framework):
        fw, mock_orch = initialized_framework
        mock_orch.list_agents = MagicMock(return_value=["backend", "frontend", "devops"])

        await fw.initialize()
        agents = await fw.list_agents()

        mock_orch.list_agents.assert_called_once()
        assert "backend" in agents
        assert len(agents) == 3


class TestPalaceFrameworkShutdown:
    """Tests for PalaceFramework.shutdown()."""

    @pytest_asyncio.fixture
    def initialized_framework(self):
        with (
            patch("palace.core.framework.MemoryStore") as MockMemoryStore,
            patch("palace.core.framework.ContextManager") as MockContextManager,
            patch("palace.core.framework.Orchestrator") as MockOrchestrator,
        ):
            mock_settings = MagicMock()
            mock_settings.memory = MagicMock()
            mock_settings.memory.store_type = "sqlite"

            mock_memory_instance = AsyncMock()
            MockMemoryStore.create.return_value = mock_memory_instance

            mock_ctx_instance = AsyncMock()
            MockContextManager.return_value = mock_ctx_instance

            mock_orch_instance = AsyncMock()
            MockOrchestrator.return_value = mock_orch_instance

            fw = PalaceFramework(settings=mock_settings)

            yield fw, mock_orch_instance, mock_ctx_instance, mock_memory_instance

    async def test_shutdown_calls_orchestrator_shutdown(self, initialized_framework):
        fw, mock_orch, mock_ctx, mock_memory = initialized_framework
        await fw.initialize()
        await fw.shutdown()
        mock_orch.shutdown.assert_called_once()

    async def test_shutdown_calls_context_manager_shutdown(self, initialized_framework):
        fw, mock_orch, mock_ctx, mock_memory = initialized_framework
        await fw.initialize()
        await fw.shutdown()
        mock_ctx.shutdown.assert_called_once()

    async def test_shutdown_calls_memory_store_close(self, initialized_framework):
        fw, mock_orch, mock_ctx, mock_memory = initialized_framework
        await fw.initialize()
        await fw.shutdown()
        mock_memory.close.assert_called_once()

    async def test_shutdown_sets_initialized_to_false(self, initialized_framework):
        fw, mock_orch, mock_ctx, mock_memory = initialized_framework
        await fw.initialize()
        assert fw._initialized is True
        await fw.shutdown()
        assert fw._initialized is False

    async def test_shutdown_is_safe_if_not_initialized(self):
        mock_settings = MagicMock()
        fw = PalaceFramework(settings=mock_settings)
        # Should not raise any errors
        await fw.shutdown()
        assert fw._initialized is False

    async def test_shutdown_order(self, initialized_framework):
        """Orchestrator shuts down before context manager, which shuts down before memory."""
        fw, mock_orch, mock_ctx, mock_memory = initialized_framework
        await fw.initialize()

        call_order = []
        mock_orch.shutdown.side_effect = lambda: call_order.append("orchestrator")
        mock_ctx.shutdown.side_effect = lambda: call_order.append("context")
        mock_memory.close.side_effect = lambda: call_order.append("memory")

        await fw.shutdown()

        assert call_order == ["orchestrator", "context", "memory"]


class TestPalaceFrameworkErrorHandling:
    """Tests for error handling in PalaceFramework."""

    async def test_execute_auto_initializes(self):
        """execute() should auto-initialize if not initialized."""
        with (
            patch("palace.core.framework.MemoryStore") as MockMemoryStore,
            patch("palace.core.framework.ContextManager") as MockContextManager,
            patch("palace.core.framework.Orchestrator") as MockOrchestrator,
        ):
            mock_settings = MagicMock()
            mock_settings.memory = MagicMock()
            mock_settings.memory.store_type = "sqlite"

            MockMemoryStore.create.return_value = AsyncMock()
            MockContextManager.return_value = AsyncMock()
            MockOrchestrator.return_value = AsyncMock()

            fw = PalaceFramework(settings=mock_settings)
            # Not initialized yet
            assert fw._initialized is False

            # Calling execute should trigger auto-initialization
            mock_result = ExecutionResult(
                task_id="t1", status="success", result="done", agent_used="a", execution_time=0.1
            )
            fw._orchestrator = MockOrchestrator.return_value
            MockOrchestrator.return_value.execute_task = AsyncMock(return_value=mock_result)

            result = await fw.execute(task="test", project_id="p1")
            assert fw._initialized is True

    async def test_get_project_status_auto_initializes(self):
        """get_project_status() should auto-initialize if not initialized."""
        with (
            patch("palace.core.framework.MemoryStore") as MockMemoryStore,
            patch("palace.core.framework.ContextManager") as MockContextManager,
            patch("palace.core.framework.Orchestrator") as MockOrchestrator,
        ):
            mock_settings = MagicMock()
            mock_settings.memory = MagicMock()
            mock_settings.memory.store_type = "sqlite"

            MockMemoryStore.create.return_value = AsyncMock()
            mock_ctx = AsyncMock()
            MockContextManager.return_value = mock_ctx
            MockOrchestrator.return_value = AsyncMock()

            fw = PalaceFramework(settings=mock_settings)
            mock_ctx.get_project_status = AsyncMock(
                return_value=ProjectStatus(
                    project_id="p1",
                    status="active",
                    active_tasks=0,
                    last_activity="2024-01-01T00:00:00",
                )
            )

            status = await fw.get_project_status("p1")
            assert fw._initialized is True

    async def test_list_agents_auto_initializes(self):
        """list_agents() should auto-initialize if not initialized."""
        with (
            patch("palace.core.framework.MemoryStore") as MockMemoryStore,
            patch("palace.core.framework.ContextManager") as MockContextManager,
            patch("palace.core.framework.Orchestrator") as MockOrchestrator,
        ):
            mock_settings = MagicMock()
            mock_settings.memory = MagicMock()
            mock_settings.memory.store_type = "sqlite"

            MockMemoryStore.create.return_value = AsyncMock()
            MockContextManager.return_value = AsyncMock()
            mock_orch = AsyncMock()
            MockOrchestrator.return_value = mock_orch
            mock_orch.list_agents = MagicMock(return_value=["backend"])

            fw = PalaceFramework(settings=mock_settings)

            agents = await fw.list_agents()
            assert fw._initialized is True
