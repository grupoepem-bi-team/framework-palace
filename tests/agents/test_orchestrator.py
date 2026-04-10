"""
Tests for palace.agents.orchestrator — OrchestratorAgent and related types.

Covers:
- TaskType enum
- TaskComplexity enum
- TaskAnalysis dataclass
- TaskPlan dataclass
- OrchestratorAgent (initialization, registration, analysis, routing, status)
"""

import json
import sys
import types
from datetime import datetime
from enum import Enum
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Bootstrap: register stub package modules so that broken __init__.py files
# do not cascade import errors.
# ---------------------------------------------------------------------------
_SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src"
_PALACE_PKG = _SRC_ROOT / "palace"
_PALACE_CORE_PKG = _PALACE_PKG / "core"
_PALACE_LLM_PKG = _PALACE_PKG / "llm"


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

# Stub palace.llm to prevent the broken __init__.py (which imports
# the non-existent LLMMessage) from cascading import errors.  We
# still want direct submodule imports like palace.llm.models to work,
# so we register the stub *before* any import that touches palace.llm.
_llm_stub = _ensure_package("palace.llm", [str(_PALACE_LLM_PKG)])

# The orchestrator imports `from palace.llm import LLMClient`; expose it
# as a MagicMock so the import succeeds at module level.  (Tests mock the
# client on each instance anyway.)
_llm_stub.LLMClient = MagicMock

# ---------------------------------------------------------------------------
# Before importing orchestrator, we need to ensure that certain names
# exist in palace.agents.base that the orchestrator imports but may not
# be defined there (AgentContext, AgentStatus). We inject stubs.
# ---------------------------------------------------------------------------
import palace.agents.base as _base  # noqa: E402

if not hasattr(_base, "AgentContext"):

    class _StubAgentContext:
        """Minimal stub matching what OrchestratorAgent expects."""

        def __init__(
            self,
            project_id: str = "test-project",
            session_id: str = "test-session",
            memory_context=None,
            additional_context=None,
        ):
            self.project_id = project_id
            self.session_id = session_id
            self.memory_context = memory_context or []
            self.additional_context = additional_context or {}

        def to_dict(self):
            return {
                "project_id": self.project_id,
                "session_id": self.session_id,
            }

    _base.AgentContext = _StubAgentContext

if not hasattr(_base, "AgentStatus"):

    class _StubAgentStatus(str, Enum):
        IDLE = "idle"
        BUSY = "busy"
        ERROR = "error"
        INITIALIZING = "initializing"

    _base.AgentStatus = _StubAgentStatus

# Now safe to import orchestrator components
from palace.agents.base import (  # noqa: E402
    AgentCapabilities,
    AgentResult,
    AgentRole,
    AgentState,
    Task,
)
from palace.agents.orchestrator import (  # noqa: E402
    OrchestratorAgent,
    TaskAnalysis,
    TaskComplexity,
    TaskPlan,
    TaskType,
)
from palace.llm.models import AgentRole as ModelsAgentRole  # noqa: E402

# =====================================================================
# Concrete subclass for testing OrchestratorAgent (abstract methods)
# =====================================================================


class ConcreteOrchestrator(OrchestratorAgent):
    """Concrete subclass of OrchestratorAgent that implements the
    abstract methods inherited from AgentBase (_build_system_prompt,
    _get_description, can_handle)."""

    def _build_system_prompt(self) -> str:
        return "You are the Orchestrator, the central coordinator."

    def _get_description(self) -> str:
        return f"ConcreteOrchestrator({self.name}, role={self.role.value})"

    def can_handle(self, task) -> bool:
        return True


# =====================================================================
# TaskType tests
# =====================================================================


class TestTaskType:
    """Tests for the TaskType enum."""

    def test_all_task_types_exist(self):
        expected = {
            "CODE_GENERATION",
            "CODE_REVIEW",
            "DATABASE",
            "INFRASTRUCTURE",
            "DEPLOYMENT",
            "TESTING",
            "DOCUMENTATION",
            "DESIGN",
            "ANALYSIS",
            "PLANNING",
            "UNKNOWN",
        }
        actual = {t.name for t in TaskType}
        assert actual == expected

    def test_task_type_values(self):
        assert TaskType.CODE_GENERATION.value == "code_generation"
        assert TaskType.CODE_REVIEW.value == "code_review"
        assert TaskType.DATABASE.value == "database"
        assert TaskType.INFRASTRUCTURE.value == "infrastructure"
        assert TaskType.DEPLOYMENT.value == "deployment"
        assert TaskType.TESTING.value == "testing"
        assert TaskType.DOCUMENTATION.value == "documentation"
        assert TaskType.DESIGN.value == "design"
        assert TaskType.ANALYSIS.value == "analysis"
        assert TaskType.PLANNING.value == "planning"
        assert TaskType.UNKNOWN.value == "unknown"

    def test_task_type_from_value(self):
        assert TaskType("code_generation") == TaskType.CODE_GENERATION
        assert TaskType("database") == TaskType.DATABASE
        assert TaskType("unknown") == TaskType.UNKNOWN

    def test_is_string_enum(self):
        assert isinstance(TaskType.CODE_GENERATION, str)

    def test_task_type_count(self):
        assert len(TaskType) == 11


# =====================================================================
# TaskComplexity tests
# =====================================================================


class TestTaskComplexity:
    """Tests for the TaskComplexity enum."""

    def test_all_complexity_levels_exist(self):
        expected = {"SIMPLE", "MODERATE", "COMPLEX", "CRITICAL"}
        actual = {c.name for c in TaskComplexity}
        assert actual == expected

    def test_complexity_values(self):
        assert TaskComplexity.SIMPLE.value == "simple"
        assert TaskComplexity.MODERATE.value == "moderate"
        assert TaskComplexity.COMPLEX.value == "complex"
        assert TaskComplexity.CRITICAL.value == "critical"

    def test_is_string_enum(self):
        assert isinstance(TaskComplexity.SIMPLE, str)

    def test_complexity_from_value(self):
        assert TaskComplexity("simple") == TaskComplexity.SIMPLE
        assert TaskComplexity("complex") == TaskComplexity.COMPLEX


# =====================================================================
# TaskAnalysis tests
# =====================================================================


class TestTaskAnalysis:
    """Tests for the TaskAnalysis dataclass."""

    def test_task_analysis_creation_minimal(self):
        analysis = TaskAnalysis(
            task_type=TaskType.CODE_GENERATION,
            complexity=TaskComplexity.MODERATE,
            required_agents=[ModelsAgentRole.BACKEND],
            suggested_workflow="Generate backend code",
            estimated_steps=2,
        )
        assert analysis.task_type == TaskType.CODE_GENERATION
        assert analysis.complexity == TaskComplexity.MODERATE
        assert analysis.required_agents == [ModelsAgentRole.BACKEND]
        assert analysis.suggested_workflow == "Generate backend code"
        assert analysis.estimated_steps == 2
        assert analysis.dependencies == []
        assert analysis.risks == []
        assert analysis.metadata == {}

    def test_task_analysis_creation_full(self):
        analysis = TaskAnalysis(
            task_type=TaskType.CODE_GENERATION,
            complexity=TaskComplexity.COMPLEX,
            required_agents=[ModelsAgentRole.BACKEND, ModelsAgentRole.DBA],
            suggested_workflow="Backend + DBA sequential",
            estimated_steps=3,
            dependencies=["database_schema"],
            risks=["schema_mismatch"],
            metadata={"raw_response": {"key": "value"}},
        )
        assert len(analysis.required_agents) == 2
        assert analysis.dependencies == ["database_schema"]
        assert analysis.risks == ["schema_mismatch"]
        assert analysis.metadata == {"raw_response": {"key": "value"}}

    def test_task_analysis_with_different_types(self):
        for task_type in [
            TaskType.CODE_REVIEW,
            TaskType.DATABASE,
            TaskType.INFRASTRUCTURE,
            TaskType.TESTING,
            TaskType.PLANNING,
        ]:
            analysis = TaskAnalysis(
                task_type=task_type,
                complexity=TaskComplexity.SIMPLE,
                required_agents=[],
                suggested_workflow="",
                estimated_steps=1,
            )
            assert analysis.task_type == task_type


# =====================================================================
# TaskPlan tests
# =====================================================================


class TestTaskPlan:
    """Tests for the TaskPlan dataclass."""

    def test_task_plan_creation_minimal(self):
        plan = TaskPlan(
            plan_id="plan-001",
            description="Implement user management",
            steps=[],
            assigned_agents={},
            estimated_time=30,
        )
        assert plan.plan_id == "plan-001"
        assert plan.description == "Implement user management"
        assert plan.steps == []
        assert plan.assigned_agents == {}
        assert plan.estimated_time == 30
        assert plan.priority == 5  # default
        assert plan.status == "pending"  # default

    def test_task_plan_creation_with_steps(self):
        steps = [
            {
                "step": 1,
                "agent": ModelsAgentRole.BACKEND,
                "task": "Create API endpoint",
                "dependencies": [],
            },
            {
                "step": 2,
                "agent": ModelsAgentRole.DBA,
                "task": "Create database schema",
                "dependencies": ["step-1"],
            },
        ]
        assigned = {"backend": ModelsAgentRole.BACKEND, "dba": ModelsAgentRole.DBA}
        plan = TaskPlan(
            plan_id="plan-002",
            description="Full user management system",
            steps=steps,
            assigned_agents=assigned,
            estimated_time=60,
            priority=10,
            status="in_progress",
        )
        assert len(plan.steps) == 2
        assert plan.assigned_agents == assigned
        assert plan.priority == 10
        assert plan.status == "in_progress"

    def test_task_plan_default_values(self):
        plan = TaskPlan(
            plan_id="plan-003",
            description="Simple task",
            steps=[],
            assigned_agents={},
            estimated_time=15,
        )
        assert plan.priority == 5
        assert plan.status == "pending"
        assert isinstance(plan.created_at, datetime)


# =====================================================================
# OrchestratorAgent tests
# =====================================================================


def _create_mock_llm_response(content="Mock LLM response", model="qwen3.5"):
    """Create a mock LLM response object."""
    response = MagicMock()
    response.content = content
    response.model = model
    response.tokens_total = 150
    response.latency_seconds = 0.5
    return response


def _create_mock_llm_client():
    """Create a fully mocked LLM client."""
    client = MagicMock()
    response = _create_mock_llm_response()
    client.invoke = AsyncMock(return_value=response)
    client.stream = AsyncMock()
    return client


def _create_mock_context_manager():
    """Create a mocked context manager."""
    cm = MagicMock()
    cm.get_context = MagicMock(return_value={"project_id": "test-project"})
    return cm


def _create_mock_memory_store():
    """Create a mocked memory store."""
    ms = MagicMock()
    ms.retrieve_context = AsyncMock(
        return_value=[
            {"content": "Previous context about the project", "source": "memory"},
        ]
    )
    ms.store_context = AsyncMock()
    return ms


def _create_mock_agent(role, name=None):
    """Create a mocked agent with a specific role."""
    agent = MagicMock()
    agent.role = role
    agent.name = name or f"{role.value}-agent"
    agent.run = AsyncMock(
        return_value=AgentResult(
            success=True,
            content=f"Result from {role.value} agent",
            agent_name=name or f"{role.value}-agent",
            model_used="test-model",
        )
    )
    return agent


def _make_analysis_json_response(
    task_type="code_generation",
    complexity="simple",
    required_agents=None,
    risks=None,
    steps=None,
):
    """Build a JSON string that mimics an LLM analysis response."""
    if required_agents is None:
        required_agents = ["backend"]
    if risks is None:
        risks = []
    if steps is None:
        steps = [
            {
                "step": 1,
                "agent": "backend",
                "task": "Implement the feature",
                "context": "",
                "dependencies": [],
                "estimated_time_minutes": 15,
            }
        ]
    data = {
        "analysis": {
            "task_type": task_type,
            "complexity": complexity,
            "required_agents": required_agents,
            "risks": risks,
        },
        "plan": {
            "description": f"Plan for {task_type} task",
            "steps": steps,
            "total_estimated_time": 15 * len(steps),
        },
    }
    return json.dumps(data)


def _make_analysis_markdown_json_response(
    task_type="code_generation",
    complexity="simple",
    required_agents=None,
):
    """Build a markdown-wrapped JSON response (as LLM often outputs)."""
    json_str = _make_analysis_json_response(task_type, complexity, required_agents)
    return f"Here is the analysis:\n\n```json\n{json_str}\n```"


class TestOrchestratorAgentInit:
    """Tests for OrchestratorAgent initialization."""

    def test_initialization(self):
        client = _create_mock_llm_client()
        cm = _create_mock_context_manager()
        ms = _create_mock_memory_store()

        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=cm,
            memory_store=ms,
        )

        assert orchestrator.name == "orchestrator"
        assert orchestrator.role == ModelsAgentRole.ORCHESTRATOR
        assert orchestrator._llm_client is client
        assert orchestrator._context_manager is cm
        assert orchestrator._memory_store is ms

    def test_initial_state_is_idle(self):
        client = _create_mock_llm_client()
        cm = _create_mock_context_manager()
        ms = _create_mock_memory_store()

        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=cm,
            memory_store=ms,
        )

        assert orchestrator.get_status() is not None
        # The status value should indicate idle
        assert orchestrator._status.value in ("idle", "IDLE", "busy", "BUSY")


class TestOrchestratorAgentRegistration:
    """Tests for agent registration, unregistration, and listing."""

    def test_register_agent(self):
        client = _create_mock_llm_client()
        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )

        backend_agent = _create_mock_agent(ModelsAgentRole.BACKEND, "backend-1")
        orchestrator.register_agent(backend_agent)

        assert ModelsAgentRole.BACKEND in orchestrator._agent_registry
        assert orchestrator._agent_registry[ModelsAgentRole.BACKEND] is backend_agent

    def test_register_multiple_agents(self):
        client = _create_mock_llm_client()
        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )

        backend = _create_mock_agent(ModelsAgentRole.BACKEND, "backend-1")
        frontend = _create_mock_agent(ModelsAgentRole.FRONTEND, "frontend-1")
        dba = _create_mock_agent(ModelsAgentRole.DBA, "dba-1")

        orchestrator.register_agent(backend)
        orchestrator.register_agent(frontend)
        orchestrator.register_agent(dba)

        agents = orchestrator.get_registered_agents()
        assert len(agents) == 3
        assert ModelsAgentRole.BACKEND in agents
        assert ModelsAgentRole.FRONTEND in agents
        assert ModelsAgentRole.DBA in agents

    def test_unregister_agent(self):
        client = _create_mock_llm_client()
        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )

        backend = _create_mock_agent(ModelsAgentRole.BACKEND, "backend-1")
        orchestrator.register_agent(backend)
        assert ModelsAgentRole.BACKEND in orchestrator.get_registered_agents()

        result = orchestrator.unregister_agent(ModelsAgentRole.BACKEND)
        assert result is True
        assert ModelsAgentRole.BACKEND not in orchestrator.get_registered_agents()

    def test_unregister_nonexistent_agent(self):
        client = _create_mock_llm_client()
        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )

        result = orchestrator.unregister_agent(ModelsAgentRole.QA)
        assert result is False

    def test_register_agent_overwrites(self):
        client = _create_mock_llm_client()
        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )

        agent1 = _create_mock_agent(ModelsAgentRole.BACKEND, "backend-v1")
        agent2 = _create_mock_agent(ModelsAgentRole.BACKEND, "backend-v2")

        orchestrator.register_agent(agent1)
        orchestrator.register_agent(agent2)

        assert orchestrator._agent_registry[ModelsAgentRole.BACKEND] is agent2
        assert orchestrator.get_registered_agents() == [ModelsAgentRole.BACKEND]

    def test_get_registered_agents_empty(self):
        client = _create_mock_llm_client()
        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )

        assert orchestrator.get_registered_agents() == []


class TestOrchestratorParseAnalysis:
    """Tests for _parse_analysis_response method."""

    def _create_orchestrator(self):
        client = _create_mock_llm_client()
        return ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )

    def test_parse_valid_json_response(self):
        orchestrator = self._create_orchestrator()
        response = _make_analysis_json_response(
            task_type="code_generation",
            complexity="simple",
            required_agents=["backend"],
        )
        analysis = orchestrator._parse_analysis_response(response)

        assert analysis.task_type == TaskType.CODE_GENERATION
        assert analysis.complexity == TaskComplexity.SIMPLE
        assert ModelsAgentRole.BACKEND in analysis.required_agents

    def test_parse_markdown_wrapped_json(self):
        orchestrator = self._create_orchestrator()
        response = _make_analysis_markdown_json_response(
            task_type="database",
            complexity="moderate",
            required_agents=["dba"],
        )
        analysis = orchestrator._parse_analysis_response(response)

        assert analysis.task_type == TaskType.DATABASE
        assert analysis.complexity == TaskComplexity.MODERATE

    def test_parse_response_with_risks(self):
        orchestrator = self._create_orchestrator()
        response = _make_analysis_json_response(
            task_type="code_generation",
            complexity="complex",
            required_agents=["backend", "frontend"],
            risks=["performance_bottleneck", "api_versioning"],
        )
        analysis = orchestrator._parse_analysis_response(response)

        assert "performance_bottleneck" in analysis.risks
        assert "api_versioning" in analysis.risks

    def test_parse_response_unknown_task_type_defaults_to_unknown(self):
        orchestrator = self._create_orchestrator()
        response = _make_analysis_json_response(
            task_type="nonexistent_type",
            complexity="simple",
            required_agents=["backend"],
        )
        analysis = orchestrator._parse_analysis_response(response)

        assert analysis.task_type == TaskType.UNKNOWN

    def test_parse_response_unknown_complexity_defaults_to_moderate(self):
        orchestrator = self._create_orchestrator()
        response = _make_analysis_json_response(
            task_type="code_generation",
            complexity="super_complex",
            required_agents=["backend"],
        )
        analysis = orchestrator._parse_analysis_response(response)

        assert analysis.complexity == TaskComplexity.MODERATE

    def test_parse_empty_required_agents_infers_from_task_type(self):
        orchestrator = self._create_orchestrator()
        response = _make_analysis_json_response(
            task_type="code_generation",
            complexity="simple",
            required_agents=[],
        )
        analysis = orchestrator._parse_analysis_response(response)

        # When no agents specified, should infer from task type
        assert len(analysis.required_agents) > 0

    def test_parse_invalid_json_falls_back_gracefully(self):
        orchestrator = self._create_orchestrator()
        # Non-JSON response - should still produce an analysis
        response = "This is not JSON at all, just plain text."

        analysis = orchestrator._parse_analysis_response(response)

        # Should default to UNKNOWN task type and MODERATE complexity
        assert analysis.task_type == TaskType.UNKNOWN
        assert analysis.complexity == TaskComplexity.MODERATE

    def test_parse_response_with_all_task_types(self):
        orchestrator = self._create_orchestrator()
        task_type_mapping = {
            "code_generation": TaskType.CODE_GENERATION,
            "code_review": TaskType.CODE_REVIEW,
            "database": TaskType.DATABASE,
            "infrastructure": TaskType.INFRASTRUCTURE,
            "deployment": TaskType.DEPLOYMENT,
            "testing": TaskType.TESTING,
            "documentation": TaskType.DOCUMENTATION,
            "design": TaskType.DESIGN,
            "analysis": TaskType.ANALYSIS,
            "planning": TaskType.PLANNING,
            "unknown": TaskType.UNKNOWN,
        }
        for type_str, expected_type in task_type_mapping.items():
            response = _make_analysis_json_response(
                task_type=type_str,
                complexity="moderate",
                required_agents=["backend"],
            )
            analysis = orchestrator._parse_analysis_response(response)
            assert analysis.task_type == expected_type, f"Failed for {type_str}"

    def test_parse_response_with_all_complexity_levels(self):
        orchestrator = self._create_orchestrator()
        complexity_mapping = {
            "simple": TaskComplexity.SIMPLE,
            "moderate": TaskComplexity.MODERATE,
            "complex": TaskComplexity.COMPLEX,
            "critical": TaskComplexity.CRITICAL,
        }
        for level_str, expected_complexity in complexity_mapping.items():
            response = _make_analysis_json_response(
                task_type="code_generation",
                complexity=level_str,
                required_agents=["backend"],
            )
            analysis = orchestrator._parse_analysis_response(response)
            assert analysis.complexity == expected_complexity, f"Failed for {level_str}"


class TestInferAgentsFromTaskType:
    """Tests for _infer_agents_from_task_type method."""

    def _create_orchestrator(self):
        client = _create_mock_llm_client()
        return ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )

    def test_code_generation_infers_backend_and_frontend(self):
        orchestrator = self._create_orchestrator()
        agents = orchestrator._infer_agents_from_task_type(TaskType.CODE_GENERATION)
        assert ModelsAgentRole.BACKEND in agents
        assert ModelsAgentRole.FRONTEND in agents

    def test_code_review_infers_reviewer(self):
        orchestrator = self._create_orchestrator()
        agents = orchestrator._infer_agents_from_task_type(TaskType.CODE_REVIEW)
        assert ModelsAgentRole.REVIEWER in agents

    def test_database_infers_dba(self):
        orchestrator = self._create_orchestrator()
        agents = orchestrator._infer_agents_from_task_type(TaskType.DATABASE)
        assert ModelsAgentRole.DBA in agents

    def test_infrastructure_infers_infra(self):
        orchestrator = self._create_orchestrator()
        agents = orchestrator._infer_agents_from_task_type(TaskType.INFRASTRUCTURE)
        assert ModelsAgentRole.INFRA in agents

    def test_deployment_infers_devops(self):
        orchestrator = self._create_orchestrator()
        agents = orchestrator._infer_agents_from_task_type(TaskType.DEPLOYMENT)
        assert ModelsAgentRole.DEVOPS in agents

    def test_testing_infers_qa(self):
        orchestrator = self._create_orchestrator()
        agents = orchestrator._infer_agents_from_task_type(TaskType.TESTING)
        assert ModelsAgentRole.QA in agents

    def test_documentation_infers_backend(self):
        orchestrator = self._create_orchestrator()
        agents = orchestrator._infer_agents_from_task_type(TaskType.DOCUMENTATION)
        assert ModelsAgentRole.BACKEND in agents

    def test_design_infers_designer(self):
        orchestrator = self._create_orchestrator()
        agents = orchestrator._infer_agents_from_task_type(TaskType.DESIGN)
        assert ModelsAgentRole.DESIGNER in agents

    def test_analysis_infers_reviewer(self):
        orchestrator = self._create_orchestrator()
        agents = orchestrator._infer_agents_from_task_type(TaskType.ANALYSIS)
        assert ModelsAgentRole.REVIEWER in agents

    def test_planning_infers_orchestrator(self):
        orchestrator = self._create_orchestrator()
        agents = orchestrator._infer_agents_from_task_type(TaskType.PLANNING)
        assert ModelsAgentRole.ORCHESTRATOR in agents

    def test_unknown_defaults_to_backend(self):
        orchestrator = self._create_orchestrator()
        agents = orchestrator._infer_agents_from_task_type(TaskType.UNKNOWN)
        assert ModelsAgentRole.BACKEND in agents

    def test_all_task_types_return_non_empty_list(self):
        orchestrator = self._create_orchestrator()
        for task_type in TaskType:
            agents = orchestrator._infer_agents_from_task_type(task_type)
            assert len(agents) > 0, f"No agents inferred for {task_type}"


class TestConsolidateResults:
    """Tests for _consolidate_results method."""

    def _create_orchestrator(self):
        client = _create_mock_llm_client()
        return ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )

    def test_consolidate_empty_results(self):
        orchestrator = self._create_orchestrator()
        result = orchestrator._consolidate_results([])
        assert "No se obtuvieron resultados" in result or "No results" in result.lower()

    def test_consolidate_single_successful_result(self):
        orchestrator = self._create_orchestrator()
        results = [
            AgentResult(
                success=True,
                content="Implemented the endpoint successfully.",
            )
        ]
        consolidated = orchestrator._consolidate_results(results)
        assert "Implemented the endpoint successfully." in consolidated
        assert "✓" in consolidated

    def test_consolidate_single_failed_result(self):
        orchestrator = self._create_orchestrator()
        results = [
            AgentResult(
                success=False,
                content="Failed to connect to database.",
            )
        ]
        consolidated = orchestrator._consolidate_results(results)
        assert "✗" in consolidated

    def test_consolidate_multiple_results(self):
        orchestrator = self._create_orchestrator()
        results = [
            AgentResult(
                success=True,
                content="Backend endpoint created.",
            ),
            AgentResult(
                success=True,
                content="Database schema designed.",
            ),
            AgentResult(
                success=False,
                content="Test coverage insufficient.",
            ),
        ]
        consolidated = orchestrator._consolidate_results(results)
        assert "Backend endpoint created." in consolidated
        assert "Database schema designed." in consolidated
        assert "✓" in consolidated
        assert "✗" in consolidated

    def test_consolidate_result_long_content_is_truncated(self):
        orchestrator = self._create_orchestrator()
        long_content = "A" * 1000
        results = [
            AgentResult(success=True, content=long_content),
        ]
        consolidated = orchestrator._consolidate_results(results)
        # Content should be present (first 500 chars)
        assert "AAAAA" in consolidated


class TestOrchestratorAgentStatus:
    """Tests for get_status and __repr__."""

    def test_get_status_returns_initial_status(self):
        client = _create_mock_llm_client()
        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )
        status = orchestrator.get_status()
        assert status is not None

    def test_repr(self):
        client = _create_mock_llm_client()
        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )
        repr_str = repr(orchestrator)
        assert "OrchestratorAgent" in repr_str
        assert "status" in repr_str.lower() or "idle" in repr_str.lower()


class TestOrchestratorAnalyzeTask:
    """Tests for the _analyze_task method with mocked LLM."""

    @pytest.mark.asyncio
    async def test_analyze_task_simple_code_generation(self):
        client = _create_mock_llm_client()
        # Set up the mock LLM response for analysis
        analysis_json = _make_analysis_json_response(
            task_type="code_generation",
            complexity="simple",
            required_agents=["backend"],
        )
        client.invoke = AsyncMock(return_value=_create_mock_llm_response(content=analysis_json))

        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )

        analysis = await orchestrator._analyze_task(
            task="Create a REST API endpoint",
            project_context={"project_id": "proj-1"},
            memory_context=[],
        )

        assert analysis.task_type == TaskType.CODE_GENERATION
        assert analysis.complexity == TaskComplexity.SIMPLE

    @pytest.mark.asyncio
    async def test_analyze_task_complex_database(self):
        client = _create_mock_llm_client()
        analysis_json = _make_analysis_json_response(
            task_type="database",
            complexity="complex",
            required_agents=["dba", "backend"],
            risks=["data_integrity"],
        )
        client.invoke = AsyncMock(return_value=_create_mock_llm_response(content=analysis_json))

        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )

        analysis = await orchestrator._analyze_task(
            task="Design a complex database schema",
            project_context={"project_id": "proj-1"},
            memory_context=[{"content": "Previous schema design"}],
        )

        assert analysis.task_type == TaskType.DATABASE
        assert analysis.complexity == TaskComplexity.COMPLEX

    @pytest.mark.asyncio
    async def test_analyze_task_critical_deployment(self):
        client = _create_mock_llm_client()
        analysis_json = _make_analysis_json_response(
            task_type="deployment",
            complexity="critical",
            required_agents=["devops"],
            risks=["production_failure"],
        )
        client.invoke = AsyncMock(return_value=_create_mock_llm_response(content=analysis_json))

        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )

        analysis = await orchestrator._analyze_task(
            task="Deploy to production",
            project_context={"project_id": "proj-1"},
            memory_context=[],
        )

        assert analysis.task_type == TaskType.DEPLOYMENT
        assert analysis.complexity == TaskComplexity.CRITICAL


class TestOrchestratorRetrieveContext:
    """Tests for the _retrieve_context method."""

    @pytest.mark.asyncio
    async def test_retrieve_context_success(self):
        client = _create_mock_llm_client()
        ms = _create_mock_memory_store()
        ms.retrieve_context = AsyncMock(
            return_value=[
                {"content": "Project context item 1", "source": "docs"},
                {"content": "Project context item 2", "source": "code"},
            ]
        )

        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=ms,
        )

        context = await orchestrator._retrieve_context(
            project_id="proj-1",
            query="implement feature",
        )

        assert len(context) == 2
        ms.retrieve_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_context_empty(self):
        client = _create_mock_llm_client()
        ms = _create_mock_memory_store()
        ms.retrieve_context = AsyncMock(return_value=[])

        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=ms,
        )

        context = await orchestrator._retrieve_context(
            project_id="proj-1",
            query="implement feature",
        )

        assert context == []

    @pytest.mark.asyncio
    async def test_retrieve_context_handles_error(self):
        client = _create_mock_llm_client()
        ms = _create_mock_memory_store()
        ms.retrieve_context = AsyncMock(side_effect=Exception("Memory store error"))

        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=ms,
        )

        context = await orchestrator._retrieve_context(
            project_id="proj-1",
            query="implement feature",
        )

        # Should return empty list on error
        assert context == []


class TestOrchestratorInferSteps:
    """Tests for _infer_steps_from_agents method."""

    def test_infer_steps_single_agent(self):
        client = _create_mock_llm_client()
        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )

        steps = orchestrator._infer_steps_from_agents(
            agents=[ModelsAgentRole.BACKEND],
            task="Create API endpoint",
        )

        assert len(steps) == 1
        assert steps[0]["agent"] == ModelsAgentRole.BACKEND
        assert steps[0]["step"] == 1

    def test_infer_steps_multiple_agents(self):
        client = _create_mock_llm_client()
        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )

        agents = [ModelsAgentRole.BACKEND, ModelsAgentRole.DBA, ModelsAgentRole.QA]
        steps = orchestrator._infer_steps_from_agents(
            agents=agents,
            task="Build user management system",
        )

        assert len(steps) == 3
        assert steps[0]["agent"] == ModelsAgentRole.BACKEND
        assert steps[1]["agent"] == ModelsAgentRole.DBA
        assert steps[2]["agent"] == ModelsAgentRole.QA

    def test_infer_steps_dependencies(self):
        client = _create_mock_llm_client()
        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )

        steps = orchestrator._infer_steps_from_agents(
            agents=[ModelsAgentRole.BACKEND, ModelsAgentRole.FRONTEND],
            task="Build feature",
        )

        # First step has no dependencies
        assert steps[0]["dependencies"] == []
        # Second step depends on the first
        assert len(steps[1]["dependencies"]) > 0

    def test_infer_steps_first_step_is_critical(self):
        client = _create_mock_llm_client()
        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=_create_mock_memory_store(),
        )

        steps = orchestrator._infer_steps_from_agents(
            agents=[ModelsAgentRole.BACKEND, ModelsAgentRole.QA],
            task="Build and test feature",
        )

        assert steps[0]["critical"] is True
        assert steps[1]["critical"] is False  # Only the first step is critical


class TestOrchestratorStoreResult:
    """Tests for _store_result method."""

    @pytest.mark.asyncio
    async def test_store_result_success(self):
        client = _create_mock_llm_client()
        ms = _create_mock_memory_store()

        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=ms,
        )

        result = AgentResult(
            success=True,
            content="Task completed",
        )

        await orchestrator._store_result(
            project_id="proj-1",
            session_id="sess-1",
            result=result,
            delegated_to="backend",
        )

        ms.store_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_result_with_step(self):
        client = _create_mock_llm_client()
        ms = _create_mock_memory_store()

        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=ms,
        )

        result = AgentResult(
            success=True,
            content="Step completed",
        )

        await orchestrator._store_result(
            project_id="proj-1",
            session_id="sess-1",
            result=result,
            delegated_to="frontend",
            step=2,
        )

        ms.store_context.assert_called_once()
        call_kwargs = ms.store_context.call_args.kwargs
        assert call_kwargs.get("metadata", {}).get("step") == 2

    @pytest.mark.asyncio
    async def test_store_result_handles_error(self):
        client = _create_mock_llm_client()
        ms = _create_mock_memory_store()
        ms.store_context = AsyncMock(side_effect=Exception("Storage error"))

        orchestrator = ConcreteOrchestrator(
            llm_client=client,
            context_manager=_create_mock_context_manager(),
            memory_store=ms,
        )

        result = AgentResult(
            success=True,
            content="Task completed",
        )

        # Should not raise, just log warning
        await orchestrator._store_result(
            project_id="proj-1",
            session_id="sess-1",
            result=result,
            delegated_to="backend",
        )


class TestOrchestratorAgentSystemPrompt:
    """Tests for the SYSTEM_PROMPT class attribute."""

    def test_system_prompt_exists(self):
        assert hasattr(OrchestratorAgent, "SYSTEM_PROMPT")
        assert isinstance(OrchestratorAgent.SYSTEM_PROMPT, str)

    def test_system_prompt_mentions_orchestrator(self):
        assert "Orchestrator" in OrchestratorAgent.SYSTEM_PROMPT

    def test_system_prompt_mentions_agents(self):
        prompt = OrchestratorAgent.SYSTEM_PROMPT
        # Should mention some agent roles
        assert "Backend" in prompt or "backend" in prompt.lower()
        assert "Frontend" in prompt or "frontend" in prompt.lower()

    def test_system_prompt_mentions_json_format(self):
        assert "json" in OrchestratorAgent.SYSTEM_PROMPT.lower()

    def test_analysis_prompt_template_exists(self):
        assert hasattr(OrchestratorAgent, "ANALYSIS_PROMPT_TEMPLATE")
        assert isinstance(OrchestratorAgent.ANALYSIS_PROMPT_TEMPLATE, str)
        assert "{task}" in OrchestratorAgent.ANALYSIS_PROMPT_TEMPLATE

    def test_delegation_prompt_template_exists(self):
        assert hasattr(OrchestratorAgent, "DELEGATION_PROMPT_TEMPLATE")
        assert isinstance(OrchestratorAgent.DELEGATION_PROMPT_TEMPLATE, str)
        assert "{subtask}" in OrchestratorAgent.DELEGATION_PROMPT_TEMPLATE


class TestOrchestratorClassAttributes:
    """Tests for OrchestratorAgent class-level attributes."""

    def test_name_attribute(self):
        assert OrchestratorAgent.name == "orchestrator"

    def test_role_attribute(self):
        assert OrchestratorAgent.role == ModelsAgentRole.ORCHESTRATOR

    def test_description_attribute(self):
        assert isinstance(OrchestratorAgent.description, str)
        assert len(OrchestratorAgent.description) > 0
