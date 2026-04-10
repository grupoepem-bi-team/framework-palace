"""
Tests for palace.agents.base — AgentBase and related types.

Covers:
- AgentRole enum
- AgentState enum
- TaskPriority enum
- TaskStatus enum
- AgentCapabilities dataclass
- Task dataclass
- AgentResult dataclass
- AgentInfo dataclass
- AgentBase abstract class (via concrete subclass)
"""

import sys
import types
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: ensure the palace package stubs exist before importing submodules
# ---------------------------------------------------------------------------
_SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src"
_PALACE_PKG = _SRC_ROOT / "palace"
_PALACE_CORE_PKG = _PALACE_PKG / "core"


def _ensure_package(module_name: str, paths: list) -> types.ModuleType:
    if module_name in sys.modules:
        return sys.modules[module_name]
    mod = types.ModuleType(module_name)
    mod.__path__ = paths
    mod.__package__ = module_name
    sys.modules[module_name] = mod
    return mod


_ensure_package("palace", [str(_PALACE_PKG)])
_ensure_package("palace.core", [str(_PALACE_CORE_PKG)])

# Now import the module under test
from palace.agents.base import (
    AgentBase,
    AgentCapabilities,
    AgentInfo,
    AgentResult,
    AgentRole,
    AgentState,
    Task,
    TaskPriority,
    TaskStatus,
)

# =====================================================================
# Concrete subclass for testing AgentBase (abstract class)
# =====================================================================


class ConcreteAgent(AgentBase):
    """A minimal concrete subclass of AgentBase for testing."""

    async def run(self, task, context, memory):
        return AgentResult(
            success=True,
            content=f"Handled task: {task.description}",
            agent_name=self.name,
            model_used=self.model,
        )

    def can_handle(self, task):
        # Simple logic: handle tasks that mention this agent's role
        return self.role.value in task.description.lower()

    def _build_system_prompt(self):
        return f"You are a {self.role.value} agent named {self.name}."

    def _get_description(self):
        return f"ConcreteAgent({self.name}, role={self.role.value})"


# =====================================================================
# AgentRole tests
# =====================================================================


class TestAgentRole:
    """Tests for the AgentRole enum."""

    def test_all_nine_roles_exist(self):
        expected = {
            "ORCHESTRATOR",
            "BACKEND",
            "FRONTEND",
            "DEVOPS",
            "INFRA",
            "DBA",
            "QA",
            "DESIGNER",
            "REVIEWER",
        }
        actual = {r.name for r in AgentRole}
        assert actual == expected

    def test_role_values_are_lowercase_strings(self):
        for role in AgentRole:
            assert isinstance(role.value, str)
            assert role.value == role.value.lower()

    def test_specific_role_values(self):
        assert AgentRole.ORCHESTRATOR.value == "orchestrator"
        assert AgentRole.BACKEND.value == "backend"
        assert AgentRole.FRONTEND.value == "frontend"
        assert AgentRole.DEVOPS.value == "devops"
        assert AgentRole.INFRA.value == "infra"
        assert AgentRole.DBA.value == "dba"
        assert AgentRole.QA.value == "qa"
        assert AgentRole.DESIGNER.value == "designer"
        assert AgentRole.REVIEWER.value == "reviewer"

    def test_role_from_value(self):
        assert AgentRole("backend") == AgentRole.BACKEND
        assert AgentRole("qa") == AgentRole.QA

    def test_is_string_enum(self):
        assert isinstance(AgentRole.ORCHESTRATOR, str)


# =====================================================================
# AgentState tests
# =====================================================================


class TestAgentState:
    """Tests for the AgentState enum."""

    def test_all_states_exist(self):
        expected = {"IDLE", "BUSY", "ERROR", "INITIALIZING"}
        actual = {s.name for s in AgentState}
        assert actual == expected

    def test_state_values(self):
        assert AgentState.IDLE.value == "idle"
        assert AgentState.BUSY.value == "busy"
        assert AgentState.ERROR.value == "error"
        assert AgentState.INITIALIZING.value == "initializing"

    def test_is_string_enum(self):
        assert isinstance(AgentState.IDLE, str)

    def test_state_from_value(self):
        assert AgentState("busy") == AgentState.BUSY
        assert AgentState("error") == AgentState.ERROR


# =====================================================================
# TaskPriority tests
# =====================================================================


class TestTaskPriority:
    """Tests for the TaskPriority enum."""

    def test_all_priorities_exist(self):
        expected = {"LOW", "NORMAL", "HIGH", "CRITICAL"}
        actual = {p.name for p in TaskPriority}
        assert actual == expected

    def test_priority_values(self):
        assert TaskPriority.LOW.value == "low"
        assert TaskPriority.NORMAL.value == "normal"
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.CRITICAL.value == "critical"

    def test_is_string_enum(self):
        assert isinstance(TaskPriority.NORMAL, str)

    def test_priority_from_value(self):
        assert TaskPriority("high") == TaskPriority.HIGH


# =====================================================================
# TaskStatus tests
# =====================================================================


class TestTaskStatus:
    """Tests for the TaskStatus enum."""

    def test_all_statuses_exist(self):
        expected = {"PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "REVIEW"}
        actual = {s.name for s in TaskStatus}
        assert actual == expected

    def test_status_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"
        assert TaskStatus.REVIEW.value == "review"

    def test_is_string_enum(self):
        assert isinstance(TaskStatus.COMPLETED, str)

    def test_status_from_value(self):
        assert TaskStatus("completed") == TaskStatus.COMPLETED


# =====================================================================
# AgentCapabilities tests
# =====================================================================


class TestAgentCapabilities:
    """Tests for the AgentCapabilities dataclass."""

    def test_default_capabilities_all_false(self):
        caps = AgentCapabilities()
        assert caps.code_generation is False
        assert caps.code_review is False
        assert caps.testing is False
        assert caps.documentation is False
        assert caps.deployment is False
        assert caps.database is False
        assert caps.infrastructure is False
        assert caps.planning is False
        assert caps.orchestration is False
        assert caps.design is False

    def test_capabilities_with_values(self):
        caps = AgentCapabilities(
            code_generation=True,
            code_review=True,
            testing=True,
        )
        assert caps.code_generation is True
        assert caps.code_review is True
        assert caps.testing is True
        assert caps.deployment is False  # default

    def test_to_list_empty(self):
        caps = AgentCapabilities()
        assert caps.to_list() == []

    def test_to_list_single_capability(self):
        caps = AgentCapabilities(code_generation=True)
        result = caps.to_list()
        assert result == ["code_generation"]

    def test_to_list_multiple_capabilities(self):
        caps = AgentCapabilities(
            code_generation=True,
            code_review=True,
            database=True,
            orchestration=True,
        )
        result = caps.to_list()
        assert "code_generation" in result
        assert "code_review" in result
        assert "database" in result
        assert "orchestration" in result
        assert len(result) == 4

    def test_to_list_all_capabilities(self):
        caps = AgentCapabilities(
            code_generation=True,
            code_review=True,
            testing=True,
            documentation=True,
            deployment=True,
            database=True,
            infrastructure=True,
            planning=True,
            orchestration=True,
            design=True,
        )
        result = caps.to_list()
        assert len(result) == 10

    def test_to_list_preserves_order(self):
        caps = AgentCapabilities(
            design=True,
            code_generation=True,
        )
        result = caps.to_list()
        # code_generation comes before design in the dataclass definition
        assert result.index("code_generation") < result.index("design")


# =====================================================================
# Task tests
# =====================================================================


class TestTask:
    """Tests for the Task dataclass."""

    def test_task_creation_minimal(self):
        task = Task(
            task_id="task-001",
            description="Implement login endpoint",
            project_id="project-1",
        )
        assert task.task_id == "task-001"
        assert task.description == "Implement login endpoint"
        assert task.project_id == "project-1"
        assert task.session_id is None
        assert task.priority == TaskPriority.NORMAL
        assert task.status == TaskStatus.PENDING
        assert task.context == {}
        assert task.metadata == {}
        assert task.parent_task_id is None
        assert task.assigned_agent is None

    def test_task_creation_full(self):
        now = datetime.utcnow()
        task = Task(
            task_id="task-002",
            description="Create database migration",
            project_id="project-2",
            session_id="session-abc",
            priority=TaskPriority.HIGH,
            status=TaskStatus.RUNNING,
            context={"files": {"app.py": "content"}},
            metadata={"source": "cli"},
            created_at=now,
            parent_task_id="task-001",
            assigned_agent="backend",
        )
        assert task.task_id == "task-002"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.RUNNING
        assert task.session_id == "session-abc"
        assert task.parent_task_id == "task-001"
        assert task.assigned_agent == "backend"

    def test_task_to_dict(self):
        task = Task(
            task_id="task-003",
            description="Write tests",
            project_id="proj-1",
            session_id="sess-1",
            priority=TaskPriority.CRITICAL,
            status=TaskStatus.PENDING,
        )
        result = task.to_dict()
        assert result["task_id"] == "task-003"
        assert result["description"] == "Write tests"
        assert result["project_id"] == "proj-1"
        assert result["session_id"] == "sess-1"
        assert result["priority"] == "critical"
        assert result["status"] == "pending"
        assert result["context"] == {}
        assert result["metadata"] == {}
        assert isinstance(result["created_at"], str)  # ISO format string
        assert result["parent_task_id"] is None
        assert result["assigned_agent"] is None

    def test_task_to_dict_with_nested_context(self):
        task = Task(
            task_id="task-004",
            description="Review code",
            project_id="proj-1",
            context={"files": {"main.py": "print('hello')"}},
            metadata={"priority_reason": "security"},
        )
        result = task.to_dict()
        assert result["context"]["files"] == {"main.py": "print('hello')"}
        assert result["metadata"]["priority_reason"] == "security"


# =====================================================================
# AgentResult tests
# =====================================================================


class TestAgentResult:
    """Tests for the AgentResult dataclass."""

    def test_result_creation_success(self):
        result = AgentResult(
            success=True,
            content="Task completed successfully",
        )
        assert result.success is True
        assert result.content == "Task completed successfully"
        assert result.artifacts == []
        assert result.metadata == {}
        assert result.errors == []
        assert result.suggestions == []
        assert result.next_actions == []
        assert result.tokens_used == 0
        assert result.execution_time_ms == 0
        assert result.model_used == ""
        assert result.agent_name == ""

    def test_result_creation_failure(self):
        result = AgentResult(
            success=False,
            content="",
            errors=["Database connection failed", "Timeout exceeded"],
        )
        assert result.success is False
        assert result.errors == ["Database connection failed", "Timeout exceeded"]

    def test_result_creation_full(self):
        now = datetime.utcnow()
        result = AgentResult(
            success=True,
            content="Implemented endpoint",
            artifacts=[{"type": "code", "path": "app.py", "content": "..."}],
            metadata={"tokens_used": 500},
            suggestions=["Add error handling"],
            next_actions=["Run tests"],
            tokens_used=500,
            execution_time_ms=1500,
            model_used="qwen3-coder-next",
            agent_name="backend",
            timestamp=now,
        )
        assert result.tokens_used == 500
        assert result.execution_time_ms == 1500
        assert result.model_used == "qwen3-coder-next"
        assert result.agent_name == "backend"
        assert len(result.artifacts) == 1
        assert result.suggestions == ["Add error handling"]
        assert result.next_actions == ["Run tests"]

    def test_result_to_dict(self):
        result = AgentResult(
            success=True,
            content="Done",
            tokens_used=100,
            execution_time_ms=200,
            model_used="test-model",
            agent_name="test-agent",
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["content"] == "Done"
        assert d["tokens_used"] == 100
        assert d["execution_time_ms"] == 200
        assert d["model_used"] == "test-model"
        assert d["agent_name"] == "test-agent"
        assert isinstance(d["timestamp"], str)

    def test_result_to_dict_includes_all_fields(self):
        result = AgentResult(
            success=False,
            content="Error",
            artifacts=[{"type": "log"}],
            metadata={"key": "value"},
            errors=["err1"],
            suggestions=["fix1"],
            next_actions=["retry"],
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["artifacts"] == [{"type": "log"}]
        assert d["metadata"] == {"key": "value"}
        assert d["errors"] == ["err1"]
        assert d["suggestions"] == ["fix1"]
        assert d["next_actions"] == ["retry"]


# =====================================================================
# AgentInfo tests
# =====================================================================


class TestAgentInfo:
    """Tests for the AgentInfo dataclass."""

    def test_info_creation(self):
        caps = AgentCapabilities(code_generation=True, code_review=True)
        info = AgentInfo(
            name="backend-agent",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            description="Backend development agent",
            capabilities=caps,
        )
        assert info.name == "backend-agent"
        assert info.role == AgentRole.BACKEND
        assert info.model == "qwen3-coder-next"
        assert info.description == "Backend development agent"
        assert info.capabilities == caps
        assert info.tools == []
        assert info.system_prompt == ""
        assert info.state == AgentState.IDLE

    def test_info_creation_with_all_fields(self):
        caps = AgentCapabilities(orchestration=True, planning=True)
        info = AgentInfo(
            name="orchestrator",
            role=AgentRole.ORCHESTRATOR,
            model="qwen3.5",
            description="Central coordinator",
            capabilities=caps,
            tools=["task_analyzer", "agent_router"],
            system_prompt="You are the orchestrator...",
            state=AgentState.BUSY,
        )
        assert info.tools == ["task_analyzer", "agent_router"]
        assert info.system_prompt == "You are the orchestrator..."
        assert info.state == AgentState.BUSY

    def test_info_to_dict(self):
        caps = AgentCapabilities(code_generation=True)
        info = AgentInfo(
            name="dba-agent",
            role=AgentRole.DBA,
            model="deepseek-v3.2",
            description="Database admin agent",
            capabilities=caps,
            tools=["sql_linter"],
            system_prompt="You are a DBA expert.",
        )
        d = info.to_dict()
        assert d["name"] == "dba-agent"
        assert d["role"] == "dba"
        assert d["model"] == "deepseek-v3.2"
        assert d["description"] == "Database admin agent"
        assert d["capabilities"] == ["code_generation"]
        assert d["tools"] == ["sql_linter"]
        assert d["state"] == "idle"

    def test_info_to_dict_truncates_long_system_prompt(self):
        long_prompt = "x" * 300
        info = AgentInfo(
            name="test",
            role=AgentRole.BACKEND,
            model="model",
            description="desc",
            capabilities=AgentCapabilities(),
            system_prompt=long_prompt,
        )
        d = info.to_dict()
        assert d["system_prompt"].endswith("...")
        assert len(d["system_prompt"]) <= 203  # 200 + "..."

    def test_info_to_dict_short_system_prompt_preserved(self):
        short_prompt = "Short prompt"
        info = AgentInfo(
            name="test",
            role=AgentRole.BACKEND,
            model="model",
            description="desc",
            capabilities=AgentCapabilities(),
            system_prompt=short_prompt,
        )
        d = info.to_dict()
        assert d["system_prompt"] == short_prompt


# =====================================================================
# AgentBase tests
# =====================================================================


class TestAgentBase:
    """Tests for AgentBase through the ConcreteAgent subclass."""

    def _create_mock_llm_client(self):
        """Create a mock LLM client for tests."""
        client = MagicMock()
        response = MagicMock()
        response.content = "Mock LLM response"
        response.model = "test-model"
        response.tokens_total = 100
        response.latency_seconds = 0.5
        client.invoke = AsyncMock(return_value=response)
        return client

    def test_concrete_agent_initialization(self):
        client = self._create_mock_llm_client()
        caps = AgentCapabilities(code_generation=True)
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
            capabilities=caps,
            tools=["linter", "formatter"],
        )

        assert agent.name == "backend-1"
        assert agent.role == AgentRole.BACKEND
        assert agent.model == "qwen3-coder-next"
        assert agent.llm_client is client
        assert agent.capabilities == caps
        assert agent.tools == ["linter", "formatter"]
        assert agent.state == AgentState.IDLE

    def test_default_capabilities_and_tools(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="frontend-1",
            role=AgentRole.FRONTEND,
            model="qwen3-coder-next",
            llm_client=client,
        )

        assert isinstance(agent.capabilities, AgentCapabilities)
        assert agent.capabilities.to_list() == []
        assert agent.tools == []

    def test_build_system_prompt(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="reviewer-1",
            role=AgentRole.REVIEWER,
            model="mistral-large",
            llm_client=client,
        )
        prompt = agent._build_system_prompt()
        assert "reviewer" in prompt
        assert "reviewer-1" in prompt

    def test_get_output_format(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )
        output_format = agent._get_output_format()
        assert isinstance(output_format, str)
        assert len(output_format) > 0

    def test_build_prompt_basic(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )
        task = Task(
            task_id="t-001",
            description="Implement user registration endpoint",
            project_id="proj-1",
        )
        prompt = agent.build_prompt(task)
        assert "Implement user registration endpoint" in prompt
        assert "## Task" in prompt

    def test_build_prompt_with_context(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )
        task = Task(
            task_id="t-002",
            description="Refactor auth module",
            project_id="proj-1",
        )
        context_str = "Previous conversation about authentication patterns"
        prompt = agent.build_prompt(task, context_str=context_str)
        assert "## Context" in prompt
        assert "Previous conversation about authentication patterns" in prompt

    def test_build_prompt_with_additional_instructions(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )
        task = Task(
            task_id="t-003",
            description="Write unit tests",
            project_id="proj-1",
        )
        prompt = agent.build_prompt(task, additional_instructions="Use pytest framework")
        assert "## Instructions" in prompt
        assert "Use pytest framework" in prompt

    def test_build_prompt_with_task_context_files(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )
        task = Task(
            task_id="t-004",
            description="Fix the bug in login",
            project_id="proj-1",
            context={"files": {"auth.py": "def login(): pass"}},
        )
        prompt = agent.build_prompt(task)
        assert "## Relevant Files" in prompt
        assert "auth.py" in prompt
        assert "def login(): pass" in prompt

    def test_build_prompt_with_task_context_requirements(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )
        task = Task(
            task_id="t-005",
            description="Create REST API",
            project_id="proj-1",
            context={"requirements": "Must follow OpenAPI 3.0 spec"},
        )
        prompt = agent.build_prompt(task)
        assert "## Requirements" in prompt
        assert "Must follow OpenAPI 3.0 spec" in prompt

    def test_build_prompt_full(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )
        task = Task(
            task_id="t-006",
            description="Implement CRUD operations",
            project_id="proj-1",
            context={
                "files": {"models.py": "class User: pass"},
                "requirements": "RESTful API standards",
            },
        )
        prompt = agent.build_prompt(
            task,
            context_str="Previous: Set up database schema",
            additional_instructions="Use async/await pattern",
        )
        assert "## Task" in prompt
        assert "## Context" in prompt
        assert "## Relevant Files" in prompt
        assert "## Requirements" in prompt
        assert "## Instructions" in prompt

    @pytest.mark.asyncio
    async def test_can_handle_positive(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )
        task = Task(
            task_id="t-010",
            description="Implement backend API for users",
            project_id="proj-1",
        )
        assert agent.can_handle(task) is True

    @pytest.mark.asyncio
    async def test_can_handle_negative(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )
        task = Task(
            task_id="t-011",
            description="Design UI mockups for dashboard",
            project_id="proj-1",
        )
        assert agent.can_handle(task) is False

    @pytest.mark.asyncio
    async def test_run_returns_result(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )
        task = Task(
            task_id="t-012",
            description="Create backend endpoint",
            project_id="proj-1",
        )
        mock_context = MagicMock()
        mock_memory = MagicMock()

        result = await agent.run(task, mock_context, mock_memory)

        assert result.success is True
        assert "Create backend endpoint" in result.content
        assert result.agent_name == "backend-1"
        assert result.model_used == "qwen3-coder-next"

    @pytest.mark.asyncio
    async def test_invoke_llm(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )

        response = await agent.invoke_llm("Write a function")

        client.invoke.assert_called_once()
        call_kwargs = client.invoke.call_args
        assert (
            call_kwargs.kwargs.get("prompt") == "Write a function"
            or call_kwargs[1].get("prompt") == "Write a function"
        )
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_invoke_llm_with_custom_system_prompt(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )

        custom_prompt = "Custom system prompt override"
        response = await agent.invoke_llm(
            "Write a function",
            system_prompt=custom_prompt,
        )

        client.invoke.assert_called_once()
        call_kwargs = client.invoke.call_args
        # The system prompt should be passed to invoke
        kw = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]
        assert kw.get("system_prompt") == custom_prompt

    @pytest.mark.asyncio
    async def test_invoke_llm_with_temperature_override(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )

        await agent.invoke_llm("test prompt", temperature=0.5, max_tokens=2048)

        client.invoke.assert_called_once()
        call_kwargs = client.invoke.call_args
        kw = call_kwargs.kwargs if call_kwargs.kwargs else call_kwargs[1]
        assert kw.get("temperature") == 0.5
        assert kw.get("max_tokens") == 2048

    @pytest.mark.asyncio
    async def test_get_context_returns_string(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )

        mock_memory = AsyncMock()
        mock_memory.retrieve_context = AsyncMock(
            return_value=[
                {"content": "Relevant context 1", "source": "doc1"},
                {"content": "Relevant context 2", "source": "doc2"},
            ]
        )

        task = Task(
            task_id="t-020",
            description="Implement feature",
            project_id="proj-1",
        )

        context = await agent.get_context(task, mock_memory)
        assert isinstance(context, str)
        assert "Relevant context 1" in context
        assert "Relevant context 2" in context

    @pytest.mark.asyncio
    async def test_get_context_empty_result(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )

        mock_memory = AsyncMock()
        mock_memory.retrieve_context = AsyncMock(return_value=[])

        task = Task(
            task_id="t-021",
            description="Implement feature",
            project_id="proj-1",
        )

        context = await agent.get_context(task, mock_memory)
        assert context == ""

    @pytest.mark.asyncio
    async def test_get_context_handles_exception(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )

        mock_memory = AsyncMock()
        mock_memory.retrieve_context = AsyncMock(side_effect=Exception("Memory error"))

        task = Task(
            task_id="t-022",
            description="Implement feature",
            project_id="proj-1",
        )

        context = await agent.get_context(task, mock_memory)
        assert context == ""

    def test_state_transitions(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )

        # Initially IDLE
        assert agent.state == AgentState.IDLE

        # Transition to BUSY
        agent.state = AgentState.BUSY
        assert agent.state == AgentState.BUSY

        # Transition to ERROR
        agent.state = AgentState.ERROR
        assert agent.state == AgentState.ERROR

        # Back to IDLE
        agent.state = AgentState.IDLE
        assert agent.state == AgentState.IDLE

    def test_multiple_agents_independent_state(self):
        client = self._create_mock_llm_client()
        agent1 = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )
        agent2 = ConcreteAgent(
            name="frontend-1",
            role=AgentRole.FRONTEND,
            model="qwen3-coder-next",
            llm_client=client,
        )

        assert agent1.state == AgentState.IDLE
        assert agent2.state == AgentState.IDLE

        agent1.state = AgentState.BUSY
        assert agent1.state == AgentState.BUSY
        assert agent2.state == AgentState.IDLE

    def test_system_prompt_stored_on_init(self):
        client = self._create_mock_llm_client()
        agent = ConcreteAgent(
            name="dba-1",
            role=AgentRole.DBA,
            model="deepseek-v3.2",
            llm_client=client,
        )
        # _build_system_prompt is called during __init__
        assert agent._system_prompt == agent._build_system_prompt()
        assert "dba" in agent._system_prompt
        assert "dba-1" in agent._system_prompt

    @pytest.mark.asyncio
    async def test_stream_llm_yields_chunks(self):
        client = self._create_mock_llm_client()

        async def mock_stream(*args, **kwargs):
            chunks = ["chunk1", "chunk2", "chunk3"]
            for chunk in chunks:
                yield chunk

        client.stream = mock_stream

        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )

        collected = []
        async for chunk in agent.stream_llm("Write code"):
            collected.append(chunk)

        assert collected == ["chunk1", "chunk2", "chunk3"]

    @pytest.mark.asyncio
    async def test_stream_llm_uses_system_prompt(self):
        client = self._create_mock_llm_client()

        stream_called_with = {}

        async def mock_stream(*args, **kwargs):
            stream_called_with.update(kwargs)
            yield "response"

        client.stream = mock_stream

        agent = ConcreteAgent(
            name="backend-1",
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            llm_client=client,
        )

        custom_prompt = "Custom system prompt for streaming"
        async for _ in agent.stream_llm("prompt", system_prompt=custom_prompt):
            pass

        assert stream_called_with.get("system_prompt") == custom_prompt
