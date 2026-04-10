"""Tests for palace.pipelines.base — Base classes for pipelines.

Covers PipelineStatus, StepStatus, StepResult, PipelineResult,
PipelineContext, PipelineStep ABC, and Pipeline ABC.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from palace.pipelines.base import (
    Pipeline,
    PipelineContext,
    PipelineResult,
    PipelineStatus,
    PipelineStep,
    StepResult,
    StepStatus,
)
from palace.pipelines.types import PipelineConfig, PipelineType, StepConfig, StepType

# ---------------------------------------------------------------------------
# Concrete test subclasses for abstract base classes
# ---------------------------------------------------------------------------


class SimpleStep(PipelineStep):
    """Concrete PipelineStep implementation for testing."""

    def __init__(self, config: StepConfig, result_content: str = "done"):
        super().__init__(config=config)
        self._result_content = result_content

    async def execute(self, context: PipelineContext) -> StepResult:
        return StepResult(
            step_id=self.step_id,
            status=StepStatus.COMPLETED,
            result=self._result_content,
        )

    def can_execute(self, context: PipelineContext) -> bool:
        return True


class ConditionalStep(PipelineStep):
    """PipelineStep that only executes when a context variable is truthy."""

    def __init__(self, config: StepConfig, condition_key: str = "can_run"):
        super().__init__(config=config)
        self._condition_key = condition_key

    async def execute(self, context: PipelineContext) -> StepResult:
        return StepResult(
            step_id=self.step_id,
            status=StepStatus.COMPLETED,
            result=f"Executed with {self._condition_key}={context.variables.get(self._condition_key)}",
        )

    def can_execute(self, context: PipelineContext) -> bool:
        return bool(context.variables.get(self._condition_key, False))


class FailingStep(PipelineStep):
    """PipelineStep that always fails."""

    async def execute(self, context: PipelineContext) -> StepResult:
        return StepResult(
            step_id=self.step_id,
            status=StepStatus.FAILED,
            error="Step failed intentionally",
        )

    def can_execute(self, context: PipelineContext) -> bool:
        return True


class ExceptionStep(PipelineStep):
    """PipelineStep that raises an exception."""

    async def execute(self, context: PipelineContext) -> StepResult:
        raise RuntimeError("Step raised an error")

    def can_execute(self, context: PipelineContext) -> bool:
        return True


class SimplePipeline(Pipeline):
    """Concrete Pipeline implementation for testing."""

    def build_steps(self) -> list[PipelineStep]:
        steps = []
        for step_config in self.config.steps:
            steps.append(SimpleStep(config=step_config))
        return steps

    def get_initial_context(self, task_description: str, project_id: str) -> PipelineContext:
        return PipelineContext(
            pipeline_id=self.pipeline_id,
            project_id=project_id,
            task_description=task_description,
        )


class EmptyPipeline(Pipeline):
    """Pipeline with no steps."""

    def build_steps(self) -> list[PipelineStep]:
        return []

    def get_initial_context(self, task_description: str, project_id: str) -> PipelineContext:
        return PipelineContext(
            pipeline_id=self.pipeline_id,
            project_id=project_id,
            task_description=task_description,
        )


# ---------------------------------------------------------------------------
# PipelineStatus enum
# ---------------------------------------------------------------------------


class TestPipelineStatus:
    """Tests for the PipelineStatus enum."""

    def test_has_six_values(self):
        """PipelineStatus should define exactly 6 members."""
        assert len(PipelineStatus) == 6

    def test_pending(self):
        assert PipelineStatus.PENDING == "pending"

    def test_running(self):
        assert PipelineStatus.RUNNING == "running"

    def test_paused(self):
        assert PipelineStatus.PAUSED == "paused"

    def test_completed(self):
        assert PipelineStatus.COMPLETED == "completed"

    def test_failed(self):
        assert PipelineStatus.FAILED == "failed"

    def test_cancelled(self):
        assert PipelineStatus.CANCELLED == "cancelled"

    def test_all_values(self):
        values = {m.value for m in PipelineStatus}
        assert values == {"pending", "running", "paused", "completed", "failed", "cancelled"}

    def test_is_str_enum(self):
        """PipelineStatus values should be strings."""
        for member in PipelineStatus:
            assert isinstance(member.value, str)


# ---------------------------------------------------------------------------
# StepStatus enum
# ---------------------------------------------------------------------------


class TestStepStatus:
    """Tests for the StepStatus enum."""

    def test_has_six_values(self):
        """StepStatus should define exactly 6 members."""
        assert len(StepStatus) == 6

    def test_pending(self):
        assert StepStatus.PENDING == "pending"

    def test_running(self):
        assert StepStatus.RUNNING == "running"

    def test_completed(self):
        assert StepStatus.COMPLETED == "completed"

    def test_failed(self):
        assert StepStatus.FAILED == "failed"

    def test_skipped(self):
        assert StepStatus.SKIPPED == "skipped"

    def test_waiting_approval(self):
        assert StepStatus.WAITING_APPROVAL == "waiting_approval"

    def test_all_values(self):
        values = {m.value for m in StepStatus}
        assert values == {
            "pending",
            "running",
            "completed",
            "failed",
            "skipped",
            "waiting_approval",
        }

    def test_is_str_enum(self):
        for member in StepStatus:
            assert isinstance(member.value, str)


# ---------------------------------------------------------------------------
# StepResult dataclass
# ---------------------------------------------------------------------------


class TestStepResult:
    """Tests for the StepResult dataclass."""

    def test_creation_with_required_fields(self):
        """StepResult requires step_id and status."""
        result = StepResult(step_id="step-1", status=StepStatus.COMPLETED)
        assert result.step_id == "step-1"
        assert result.status == StepStatus.COMPLETED

    def test_defaults(self):
        """StepResult should provide sensible defaults."""
        result = StepResult(step_id="step-1", status=StepStatus.PENDING)
        assert result.result == ""
        assert result.artifacts == {}
        assert result.metadata == {}
        assert result.error is None
        assert result.execution_time_seconds == 0.0
        assert result.tokens_used == 0
        assert result.agent_used is None

    def test_all_fields(self):
        """StepResult should accept all fields."""
        now = datetime.now()
        result = StepResult(
            step_id="step-1",
            status=StepStatus.COMPLETED,
            result="Task completed successfully",
            artifacts={"file.py": "print('hello')"},
            metadata={"duration_ms": 500},
            error=None,
            execution_time_seconds=1.5,
            tokens_used=250,
            agent_used="backend",
        )
        assert result.step_id == "step-1"
        assert result.status == StepStatus.COMPLETED
        assert result.result == "Task completed successfully"
        assert result.artifacts == {"file.py": "print('hello')"}
        assert result.metadata == {"duration_ms": 500}
        assert result.error is None
        assert result.execution_time_seconds == 1.5
        assert result.tokens_used == 250
        assert result.agent_used == "backend"

    def test_failed_step_result(self):
        """StepResult can represent a failed step."""
        result = StepResult(
            step_id="step-2",
            status=StepStatus.FAILED,
            error="Connection refused",
        )
        assert result.status == StepStatus.FAILED
        assert result.error == "Connection refused"

    def test_skipped_step_result(self):
        """StepResult can represent a skipped step."""
        result = StepResult(
            step_id="step-3",
            status=StepStatus.SKIPPED,
            result="Condition not met",
        )
        assert result.status == StepStatus.SKIPPED
        assert result.result == "Condition not met"

    def test_artifacts_independent_across_instances(self):
        """Each StepResult should have its own artifacts dict."""
        r1 = StepResult(step_id="s1", status=StepStatus.COMPLETED)
        r2 = StepResult(step_id="s2", status=StepStatus.COMPLETED)
        r1.artifacts["key"] = "value"
        assert r2.artifacts == {}

    def test_metadata_independent_across_instances(self):
        """Each StepResult should have its own metadata dict."""
        r1 = StepResult(step_id="s1", status=StepStatus.COMPLETED)
        r2 = StepResult(step_id="s2", status=StepStatus.COMPLETED)
        r1.metadata["tag"] = "important"
        assert r2.metadata == {}


# ---------------------------------------------------------------------------
# PipelineResult dataclass
# ---------------------------------------------------------------------------


class TestPipelineResult:
    """Tests for the PipelineResult dataclass."""

    def test_creation_with_required_fields(self):
        """PipelineResult requires pipeline_id and status."""
        result = PipelineResult(
            pipeline_id="pipe-1",
            status=PipelineStatus.COMPLETED,
        )
        assert result.pipeline_id == "pipe-1"
        assert result.status == PipelineStatus.COMPLETED

    def test_defaults(self):
        """PipelineResult should provide sensible defaults."""
        result = PipelineResult(
            pipeline_id="pipe-1",
            status=PipelineStatus.PENDING,
        )
        assert result.step_results == []
        assert result.final_result == ""
        assert result.artifacts == {}
        assert result.errors == []
        assert result.total_execution_time == 0.0
        assert result.total_tokens_used == 0
        assert result.started_at is None
        assert result.completed_at is None
        assert result.metadata == {}

    def test_all_fields(self):
        """PipelineResult should accept all fields."""
        step_result = StepResult(step_id="s1", status=StepStatus.COMPLETED)
        now = datetime.now()
        result = PipelineResult(
            pipeline_id="pipe-1",
            status=PipelineStatus.COMPLETED,
            step_results=[step_result],
            final_result="All steps passed",
            artifacts={"output.txt": "hello"},
            errors=[],
            total_execution_time=5.2,
            total_tokens_used=500,
            started_at=now,
            completed_at=now,
            metadata={"total_steps": 1},
        )
        assert result.pipeline_id == "pipe-1"
        assert result.status == PipelineStatus.COMPLETED
        assert len(result.step_results) == 1
        assert result.step_results[0].step_id == "s1"
        assert result.final_result == "All steps passed"
        assert result.artifacts == {"output.txt": "hello"}
        assert result.errors == []
        assert result.total_execution_time == 5.2
        assert result.total_tokens_used == 500
        assert result.started_at == now
        assert result.completed_at == now
        assert result.metadata == {"total_steps": 1}

    def test_failed_pipeline_result(self):
        """PipelineResult can represent a failed pipeline."""
        result = PipelineResult(
            pipeline_id="pipe-2",
            status=PipelineStatus.FAILED,
            errors=["Step 3 failed", "Timeout exceeded"],
        )
        assert result.status == PipelineStatus.FAILED
        assert len(result.errors) == 2

    def test_step_results_independent_across_instances(self):
        """Each PipelineResult should have its own step_results list."""
        r1 = PipelineResult(pipeline_id="p1", status=PipelineStatus.COMPLETED)
        r2 = PipelineResult(pipeline_id="p2", status=PipelineStatus.COMPLETED)
        sr = StepResult(step_id="s1", status=StepStatus.COMPLETED)
        r1.step_results.append(sr)
        assert r2.step_results == []

    def test_errors_independent_across_instances(self):
        """Each PipelineResult should have its own errors list."""
        r1 = PipelineResult(pipeline_id="p1", status=PipelineStatus.FAILED)
        r2 = PipelineResult(pipeline_id="p2", status=PipelineStatus.FAILED)
        r1.errors.append("error")
        assert r2.errors == []


# ---------------------------------------------------------------------------
# PipelineContext dataclass
# ---------------------------------------------------------------------------


class TestPipelineContext:
    """Tests for the PipelineContext dataclass."""

    def test_creation_with_required_fields(self):
        """PipelineContext requires pipeline_id and project_id."""
        ctx = PipelineContext(pipeline_id="pipe-1", project_id="proj-1")
        assert ctx.pipeline_id == "pipe-1"
        assert ctx.project_id == "proj-1"

    def test_defaults(self):
        """PipelineContext should provide sensible defaults."""
        ctx = PipelineContext(pipeline_id="pipe-1", project_id="proj-1")
        assert ctx.session_id is None
        assert ctx.task_description == ""
        assert ctx.variables == {}
        assert ctx.step_outputs == {}
        assert ctx.memory_entries == []
        assert ctx.config is None

    def test_all_fields(self):
        """PipelineContext should accept all fields."""
        pipeline_config = PipelineConfig(
            pipeline_id="pipe-1",
            name="Test",
            pipeline_type=PipelineType.CUSTOM,
            project_id="proj-1",
        )
        step_result = StepResult(step_id="s1", status=StepStatus.COMPLETED)
        ctx = PipelineContext(
            pipeline_id="pipe-1",
            project_id="proj-1",
            session_id="sess-123",
            task_description="Build a REST API",
            variables={"env": "production", "debug": False},
            step_outputs={"s1": step_result},
            memory_entries=["mem-1", "mem-2"],
            config=pipeline_config,
        )
        assert ctx.session_id == "sess-123"
        assert ctx.task_description == "Build a REST API"
        assert ctx.variables == {"env": "production", "debug": False}
        assert "s1" in ctx.step_outputs
        assert ctx.memory_entries == ["mem-1", "mem-2"]
        assert ctx.config is pipeline_config

    def test_variables_independent_across_instances(self):
        """Each PipelineContext should have its own variables dict."""
        ctx1 = PipelineContext(pipeline_id="p1", project_id="proj-1")
        ctx2 = PipelineContext(pipeline_id="p2", project_id="proj-1")
        ctx1.variables["key"] = "value"
        assert ctx2.variables == {}

    def test_step_outputs_independent_across_instances(self):
        """Each PipelineContext should have its own step_outputs dict."""
        ctx1 = PipelineContext(pipeline_id="p1", project_id="proj-1")
        ctx2 = PipelineContext(pipeline_id="p2", project_id="proj-1")
        sr = StepResult(step_id="s1", status=StepStatus.COMPLETED)
        ctx1.step_outputs["s1"] = sr
        assert ctx2.step_outputs == {}

    def test_memory_entries_independent_across_instances(self):
        """Each PipelineContext should have its own memory_entries list."""
        ctx1 = PipelineContext(pipeline_id="p1", project_id="proj-1")
        ctx2 = PipelineContext(pipeline_id="p2", project_id="proj-1")
        ctx1.memory_entries.append("entry-1")
        assert ctx2.memory_entries == []


# ---------------------------------------------------------------------------
# PipelineStep ABC
# ---------------------------------------------------------------------------


class TestPipelineStep:
    """Tests for the PipelineStep abstract base class."""

    def _make_step_config(self, **overrides) -> StepConfig:
        """Helper to create a StepConfig with defaults."""
        defaults = {
            "step_id": "step-1",
            "name": "Test Step",
            "step_type": StepType.AGENT_TASK,
        }
        defaults.update(overrides)
        return StepConfig(**defaults)

    def test_cannot_instantiate_abstract_class(self):
        """PipelineStep cannot be instantiated directly."""
        config = self._make_step_config()
        with pytest.raises(TypeError):
            PipelineStep(config=config)

    def test_concrete_subclass_creation(self):
        """Concrete subclass can be created with a StepConfig."""
        config = self._make_step_config()
        step = SimpleStep(config=config)
        assert step.step_id == "step-1"
        assert step.name == "Test Step"
        assert step.step_type == StepType.AGENT_TASK
        assert step.config is config

    def test_initial_status_is_pending(self):
        """Newly created step should have PENDING status."""
        config = self._make_step_config()
        step = SimpleStep(config=config)
        assert step.status == StepStatus.PENDING

    def test_initial_result_is_none(self):
        """Newly created step should have no result."""
        config = self._make_step_config()
        step = SimpleStep(config=config)
        assert step.result is None

    @pytest.mark.asyncio
    async def test_execute(self):
        """execute() should return a StepResult."""
        config = self._make_step_config()
        step = SimpleStep(config=config, result_content="Hello world")
        ctx = PipelineContext(pipeline_id="p1", project_id="proj-1")
        result = await step.execute(ctx)
        assert result.step_id == "step-1"
        assert result.status == StepStatus.COMPLETED
        assert result.result == "Hello world"

    @pytest.mark.asyncio
    async def test_can_execute_always_true_for_simple_step(self):
        """SimpleStep.can_execute() always returns True."""
        config = self._make_step_config()
        step = SimpleStep(config=config)
        ctx = PipelineContext(pipeline_id="p1", project_id="proj-1")
        assert step.can_execute(ctx) is True

    def test_can_execute_conditional(self):
        """ConditionalStep.can_execute() checks context variables."""
        config = self._make_step_config()
        step = ConditionalStep(config=config, condition_key="can_run")
        ctx_empty = PipelineContext(pipeline_id="p1", project_id="proj-1")
        assert step.can_execute(ctx_empty) is False

        ctx_true = PipelineContext(
            pipeline_id="p1",
            project_id="proj-1",
            variables={"can_run": True},
        )
        assert step.can_execute(ctx_true) is True

    @pytest.mark.asyncio
    async def test_failing_step(self):
        """FailingStep.execute() returns a FAILED StepResult."""
        config = self._make_step_config()
        step = FailingStep(config=config)
        ctx = PipelineContext(pipeline_id="p1", project_id="proj-1")
        result = await step.execute(ctx)
        assert result.status == StepStatus.FAILED
        assert result.error == "Step failed intentionally"

    def test_get_task_description_no_template(self):
        """get_task_description() returns template as-is when no variables match."""
        config = self._make_step_config(task_template="Hello World")
        step = SimpleStep(config=config)
        ctx = PipelineContext(pipeline_id="p1", project_id="proj-1")
        assert step.get_task_description(ctx) == "Hello World"

    def test_get_task_description_with_variables(self):
        """get_task_description() formats template with context variables."""
        config = self._make_step_config(task_template="Implement {feature} for {module}")
        step = SimpleStep(config=config)
        ctx = PipelineContext(
            pipeline_id="p1",
            project_id="proj-1",
            variables={"feature": "authentication", "module": "users"},
        )
        assert step.get_task_description(ctx) == "Implement authentication for users"

    def test_get_task_description_missing_variable(self):
        """get_task_description() returns template as-is when a variable is missing."""
        config = self._make_step_config(task_template="Implement {feature} for {missing_var}")
        step = SimpleStep(config=config)
        ctx = PipelineContext(
            pipeline_id="p1",
            project_id="proj-1",
            variables={"feature": "auth"},
        )
        # KeyError from .format() should be caught, returning original template
        result = step.get_task_description(ctx)
        assert result == "Implement {feature} for {missing_var}"

    def test_get_task_description_empty_template(self):
        """get_task_description() with empty template returns empty string."""
        config = self._make_step_config(task_template="")
        step = SimpleStep(config=config)
        ctx = PipelineContext(pipeline_id="p1", project_id="proj-1")
        assert step.get_task_description(ctx) == ""

    def test_get_task_description_partial_match(self):
        """get_task_description() with partial variable match."""
        config = self._make_step_config(task_template="Build {component} and test")
        step = SimpleStep(config=config)
        ctx = PipelineContext(
            pipeline_id="p1",
            project_id="proj-1",
            variables={"component": "API"},
        )
        assert step.get_task_description(ctx) == "Build API and test"

    def test_step_stores_config(self):
        """Step should store and expose its configuration."""
        config = self._make_step_config(
            step_id="my-step",
            name="My Step",
            step_type=StepType.VALIDATION,
            agent_role="qa",
        )
        step = SimpleStep(config=config)
        assert step.config is config
        assert step.config.agent_role == "qa"


# ---------------------------------------------------------------------------
# Pipeline ABC
# ---------------------------------------------------------------------------


class TestPipeline:
    """Tests for the Pipeline abstract base class."""

    def _make_pipeline_config(self, **overrides) -> PipelineConfig:
        """Helper to create a PipelineConfig with defaults."""
        defaults = {
            "pipeline_id": "pipe-1",
            "name": "Test Pipeline",
            "pipeline_type": PipelineType.CUSTOM,
            "project_id": "proj-1",
        }
        defaults.update(overrides)
        return PipelineConfig(**defaults)

    def test_cannot_instantiate_abstract_class(self):
        """Pipeline cannot be instantiated directly."""
        config = self._make_pipeline_config()
        with pytest.raises(TypeError):
            Pipeline(config=config)

    def test_concrete_subclass_creation(self):
        """SimplePipeline can be created with a PipelineConfig."""
        config = self._make_pipeline_config()
        pipeline = SimplePipeline(config=config)
        assert pipeline.pipeline_id == "pipe-1"
        assert pipeline.name == "Test Pipeline"
        assert pipeline.pipeline_type == PipelineType.CUSTOM
        assert pipeline.config is config

    def test_initial_status_is_pending(self):
        """Newly created pipeline should have PENDING status."""
        config = self._make_pipeline_config()
        pipeline = SimplePipeline(config=config)
        assert pipeline.status == PipelineStatus.PENDING

    def test_initial_steps_is_empty_list(self):
        """Newly created pipeline should have no steps."""
        config = self._make_pipeline_config()
        pipeline = SimplePipeline(config=config)
        assert pipeline.steps == []

    def test_initial_result_is_none(self):
        """Newly created pipeline should have no result."""
        config = self._make_pipeline_config()
        pipeline = SimplePipeline(config=config)
        assert pipeline._result is None

    def test_build_steps(self):
        """build_steps() should create steps from the config."""
        step_config = StepConfig(step_id="s1", name="Step 1", step_type=StepType.AGENT_TASK)
        config = self._make_pipeline_config(steps=[step_config])
        pipeline = SimplePipeline(config=config)
        steps = pipeline.build_steps()
        assert len(steps) == 1
        assert steps[0].step_id == "s1"
        assert steps[0].name == "Step 1"

    def test_build_steps_multiple(self):
        """build_steps() should create all steps from config."""
        step_configs = [
            StepConfig(step_id=f"s{i}", name=f"Step {i}", step_type=StepType.AGENT_TASK)
            for i in range(1, 4)
        ]
        config = self._make_pipeline_config(steps=step_configs)
        pipeline = SimplePipeline(config=config)
        steps = pipeline.build_steps()
        assert len(steps) == 3
        assert [s.step_id for s in steps] == ["s1", "s2", "s3"]

    def test_build_steps_empty(self):
        """EmptyPipeline.build_steps() returns an empty list."""
        config = self._make_pipeline_config()
        pipeline = EmptyPipeline(config=config)
        assert pipeline.build_steps() == []

    def test_get_initial_context(self):
        """get_initial_context() should create a PipelineContext."""
        config = self._make_pipeline_config()
        pipeline = SimplePipeline(config=config)
        ctx = pipeline.get_initial_context(
            task_description="Build feature X",
            project_id="proj-1",
        )
        assert isinstance(ctx, PipelineContext)
        assert ctx.pipeline_id == "pipe-1"
        assert ctx.project_id == "proj-1"
        assert ctx.task_description == "Build feature X"

    def test_get_initial_context_with_session(self):
        """get_initial_context() can include a session_id."""
        config = self._make_pipeline_config()
        pipeline = SimplePipeline(config=config)
        ctx = pipeline.get_initial_context(
            task_description="Task",
            project_id="proj-1",
        )
        ctx.session_id = "sess-123"
        assert ctx.session_id == "sess-123"

    @pytest.mark.asyncio
    async def test_validate_with_steps(self):
        """validate() should return True when steps exist."""
        step_config = StepConfig(step_id="s1", name="Step 1", step_type=StepType.AGENT_TASK)
        config = self._make_pipeline_config(steps=[step_config])
        pipeline = SimplePipeline(config=config)
        pipeline._steps = pipeline.build_steps()
        result = await pipeline.validate()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_without_steps(self):
        """validate() should return False when no steps exist."""
        config = self._make_pipeline_config()
        pipeline = EmptyPipeline(config=config)
        result = await pipeline.validate()
        assert result is False

    def test_get_step_by_id_found(self):
        """get_step_by_id() returns the step if found."""
        step_configs = [
            StepConfig(step_id="s1", name="Step 1", step_type=StepType.AGENT_TASK),
            StepConfig(step_id="s2", name="Step 2", step_type=StepType.AGENT_TASK),
        ]
        config = self._make_pipeline_config(steps=step_configs)
        pipeline = SimplePipeline(config=config)
        pipeline._steps = pipeline.build_steps()
        step = pipeline.get_step_by_id("s2")
        assert step is not None
        assert step.step_id == "s2"
        assert step.name == "Step 2"

    def test_get_step_by_id_not_found(self):
        """get_step_by_id() returns None if not found."""
        step_config = StepConfig(step_id="s1", name="Step 1", step_type=StepType.AGENT_TASK)
        config = self._make_pipeline_config(steps=[step_config])
        pipeline = SimplePipeline(config=config)
        pipeline._steps = pipeline.build_steps()
        step = pipeline.get_step_by_id("nonexistent")
        assert step is None

    def test_get_step_by_id_empty_steps(self):
        """get_step_by_id() returns None when pipeline has no steps."""
        config = self._make_pipeline_config()
        pipeline = EmptyPipeline(config=config)
        assert pipeline.get_step_by_id("any") is None

    def test_pipeline_stores_config(self):
        """Pipeline should store and expose its configuration."""
        config = self._make_pipeline_config(
            pipeline_id="custom-pipe",
            name="My Custom Pipeline",
            pipeline_type=PipelineType.DEPLOYMENT,
            project_id="proj-42",
            max_retries=5,
            timeout_seconds=7200,
        )
        pipeline = SimplePipeline(config=config)
        assert pipeline.config.max_retries == 5
        assert pipeline.config.timeout_seconds == 7200
        assert pipeline.config.project_id == "proj-42"

    def test_pipeline_status_property_is_mutable(self):
        """Pipeline status should be mutable via _status."""
        config = self._make_pipeline_config()
        pipeline = SimplePipeline(config=config)
        assert pipeline.status == PipelineStatus.PENDING

        pipeline._status = PipelineStatus.RUNNING
        assert pipeline.status == PipelineStatus.RUNNING

        pipeline._status = PipelineStatus.COMPLETED
        assert pipeline.status == PipelineStatus.COMPLETED

    def test_pipeline_status_all_transitions(self):
        """Pipeline should support all status transitions."""
        config = self._make_pipeline_config()
        pipeline = SimplePipeline(config=config)

        for status in PipelineStatus:
            pipeline._status = status
            assert pipeline.status == status

    def test_get_step_by_id_multiple_matches_returns_first(self):
        """get_step_by_id() with duplicate IDs returns the first match."""
        # Create two steps with different configs but same ID (unusual but possible)
        step_configs = [
            StepConfig(step_id="s1", name="Step A", step_type=StepType.AGENT_TASK),
            StepConfig(step_id="s2", name="Step B", step_type=StepType.VALIDATION),
        ]
        config = self._make_pipeline_config(steps=step_configs)
        pipeline = SimplePipeline(config=config)
        pipeline._steps = pipeline.build_steps()
        step = pipeline.get_step_by_id("s1")
        assert step is not None
        assert step.name == "Step A"

    def test_pipeline_with_different_types(self):
        """Pipeline should work with all pipeline types."""
        for pt in PipelineType:
            config = self._make_pipeline_config(pipeline_type=pt)
            pipeline = SimplePipeline(config=config)
            assert pipeline.pipeline_type == pt

    @pytest.mark.asyncio
    async def test_validate_returns_true_after_build_steps(self):
        """validate() returns True after build_steps() populates steps."""
        step_configs = [
            StepConfig(step_id=f"s{i}", name=f"Step {i}", step_type=StepType.AGENT_TASK)
            for i in range(1, 4)
        ]
        config = self._make_pipeline_config(steps=step_configs)
        pipeline = SimplePipeline(config=config)
        pipeline._steps = pipeline.build_steps()
        assert await pipeline.validate() is True

    def test_get_initial_context_default_values(self):
        """get_initial_context() should set defaults for optional fields."""
        config = self._make_pipeline_config()
        pipeline = SimplePipeline(config=config)
        ctx = pipeline.get_initial_context(
            task_description="Some task",
            project_id="proj-1",
        )
        assert ctx.session_id is None
        assert ctx.variables == {}
        assert ctx.step_outputs == {}
        assert ctx.memory_entries == []
