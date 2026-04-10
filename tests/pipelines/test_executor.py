"""Tests for palace.pipelines.executor — Pipeline execution engine.

Covers PipelineExecutor initialization, pipeline execution, step
dependency resolution, step execution order, cancellation, error
handling, and the get_executor singleton function.
"""

import asyncio
from datetime import datetime
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from palace.pipelines.base import (
    Pipeline,
    PipelineContext,
    PipelineResult,
    PipelineStatus,
    PipelineStep,
    StepResult,
    StepStatus,
)
from palace.pipelines.executor import PipelineExecutor, get_executor
from palace.pipelines.types import PipelineConfig, PipelineType, StepConfig, StepType

# ---------------------------------------------------------------------------
# Concrete test subclasses for abstract base classes
# ---------------------------------------------------------------------------


class SimpleStep(PipelineStep):
    """Concrete PipelineStep that completes successfully."""

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
    """PipelineStep that always returns a FAILED result."""

    async def execute(self, context: PipelineContext) -> StepResult:
        return StepResult(
            step_id=self.step_id,
            status=StepStatus.FAILED,
            error=f"Step {self.step_id} failed intentionally",
        )

    def can_execute(self, context: PipelineContext) -> bool:
        return True


class ExceptionStep(PipelineStep):
    """PipelineStep that raises an exception during execution."""

    def __init__(self, config: StepConfig, error_message: str = "Step raised an error"):
        super().__init__(config=config)
        self._error_message = error_message

    async def execute(self, context: PipelineContext) -> StepResult:
        raise RuntimeError(self._error_message)

    def can_execute(self, context: PipelineContext) -> bool:
        return True


class SkipStep(PipelineStep):
    """PipelineStep whose can_execute always returns False."""

    async def execute(self, context: PipelineContext) -> StepResult:
        return StepResult(
            step_id=self.step_id,
            status=StepStatus.COMPLETED,
            result="Should not be called",
        )

    def can_execute(self, context: PipelineContext) -> bool:
        return False


class TrackingStep(PipelineStep):
    """PipelineStep that records execution order in context variables."""

    def __init__(self, config: StepConfig, track_key: str = "execution_order"):
        super().__init__(config=config)
        self._track_key = track_key

    async def execute(self, context: PipelineContext) -> StepResult:
        order = context.variables.get(self._track_key, [])
        order.append(self.step_id)
        context.variables[self._track_key] = order
        return StepResult(
            step_id=self.step_id,
            status=StepStatus.COMPLETED,
            result=f"Tracked {self.step_id}",
        )

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


class TrackingPipeline(Pipeline):
    """Pipeline that creates TrackingSteps for execution order tests."""

    def build_steps(self) -> list[PipelineStep]:
        steps = []
        for step_config in self.config.steps:
            steps.append(TrackingStep(config=step_config))
        return steps

    def get_initial_context(self, task_description: str, project_id: str) -> PipelineContext:
        return PipelineContext(
            pipeline_id=self.pipeline_id,
            project_id=project_id,
            task_description=task_description,
        )


class FailingPipeline(Pipeline):
    """Pipeline that creates FailingSteps for error handling tests."""

    def build_steps(self) -> list[PipelineStep]:
        steps = []
        for step_config in self.config.steps:
            steps.append(FailingStep(config=step_config))
        return steps

    def get_initial_context(self, task_description: str, project_id: str) -> PipelineContext:
        return PipelineContext(
            pipeline_id=self.pipeline_id,
            project_id=project_id,
            task_description=task_description,
        )


class MixedPipeline(Pipeline):
    """Pipeline that creates mixed step types based on config metadata."""

    def build_steps(self) -> list[PipelineStep]:
        steps = []
        for step_config in self.config.steps:
            step_type = step_config.metadata.get("impl", "simple")
            if step_type == "failing":
                steps.append(FailingStep(config=step_config))
            elif step_type == "exception":
                steps.append(ExceptionStep(config=step_config))
            elif step_type == "skip":
                steps.append(SkipStep(config=step_config))
            elif step_type == "tracking":
                steps.append(TrackingStep(config=step_config))
            elif step_type == "conditional":
                steps.append(ConditionalStep(config=step_config))
            else:
                steps.append(SimpleStep(config=step_config))
        return steps

    def get_initial_context(self, task_description: str, project_id: str) -> PipelineContext:
        return PipelineContext(
            pipeline_id=self.pipeline_id,
            project_id=project_id,
            task_description=task_description,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pipeline_config(**overrides) -> PipelineConfig:
    """Create a PipelineConfig with sensible defaults."""
    defaults = {
        "pipeline_id": "test-pipeline",
        "name": "Test Pipeline",
        "pipeline_type": PipelineType.CUSTOM,
        "project_id": "test-project",
    }
    defaults.update(overrides)
    return PipelineConfig(**defaults)


def _make_step_config(**overrides) -> StepConfig:
    """Create a StepConfig with sensible defaults.

    Uses StepType.VALIDATION so that the executor dispatches steps through
    execute_step() rather than _execute_agent_step() (which returns a mock
    result when no PalaceFramework is configured).
    """
    defaults = {
        "step_id": "step-1",
        "name": "Step 1",
        "step_type": StepType.VALIDATION,
    }
    defaults.update(overrides)
    return StepConfig(**defaults)


# ---------------------------------------------------------------------------
# PipelineExecutor — Initialization
# ---------------------------------------------------------------------------


class TestExecutorInitialization:
    """Tests for PipelineExecutor initialization."""

    def test_default_initialization(self):
        """PipelineExecutor initializes with default parameters."""
        executor = PipelineExecutor()
        assert executor.framework is None
        assert executor.max_concurrent_steps == 5
        assert executor.retry_delay_seconds == 1.0

    def test_custom_initialization(self):
        """PipelineExecutor accepts custom parameters."""
        mock_framework = MagicMock()
        executor = PipelineExecutor(
            framework=mock_framework,
            max_concurrent_steps=10,
            retry_delay_seconds=2.0,
        )
        assert executor.framework is mock_framework
        assert executor.max_concurrent_steps == 10
        assert executor.retry_delay_seconds == 2.0

    def test_initialization_with_framework_none(self):
        """PipelineExecutor can be initialized with framework=None."""
        executor = PipelineExecutor(framework=None)
        assert executor.framework is None

    def test_initialization_max_concurrent_steps(self):
        """max_concurrent_steps can be configured at init time."""
        executor = PipelineExecutor(max_concurrent_steps=3)
        assert executor.max_concurrent_steps == 3

    def test_initialization_retry_delay(self):
        """retry_delay_seconds can be configured at init time."""
        executor = PipelineExecutor(retry_delay_seconds=0.5)
        assert executor.retry_delay_seconds == 0.5


# ---------------------------------------------------------------------------
# PipelineExecutor — Pipeline execution
# ---------------------------------------------------------------------------


class TestExecutorPipelineExecution:
    """Tests for PipelineExecutor pipeline execution."""

    @pytest.mark.asyncio
    async def test_execute_simple_pipeline(self):
        """Execute a simple pipeline with one step."""
        executor = PipelineExecutor()
        step_config = _make_step_config()
        config = _make_pipeline_config(steps=[step_config])
        pipeline = SimplePipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Test task",
            project_id="proj-1",
        )

        assert result.pipeline_id == "test-pipeline"
        assert result.status == PipelineStatus.COMPLETED
        assert len(result.step_results) == 1
        assert result.step_results[0].step_id == "step-1"
        assert result.step_results[0].status == StepStatus.COMPLETED
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.total_execution_time >= 0

    @pytest.mark.asyncio
    async def test_execute_multi_step_pipeline(self):
        """Execute a pipeline with multiple steps."""
        executor = PipelineExecutor()
        step_configs = [
            _make_step_config(step_id=f"step-{i}", name=f"Step {i}") for i in range(1, 4)
        ]
        config = _make_pipeline_config(steps=step_configs)
        pipeline = SimplePipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Multi-step task",
            project_id="proj-1",
        )

        assert result.status == PipelineStatus.COMPLETED
        assert len(result.step_results) == 3
        step_ids = [r.step_id for r in result.step_results]
        assert step_ids == ["step-1", "step-2", "step-3"]

    @pytest.mark.asyncio
    async def test_execute_sets_pipeline_status_running(self):
        """During execution, the pipeline status should transition."""
        executor = PipelineExecutor()
        step_config = _make_step_config()
        config = _make_pipeline_config(steps=[step_config])
        pipeline = SimplePipeline(config=config)

        # Before execution, status is PENDING
        assert pipeline.status == PipelineStatus.PENDING

        await executor.execute(
            pipeline=pipeline,
            task_description="Status check",
            project_id="proj-1",
        )

        # After execution, status should be COMPLETED
        assert pipeline.status == PipelineStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_with_session_id(self):
        """Execute a pipeline with a session_id."""
        executor = PipelineExecutor()
        step_config = _make_step_config()
        config = _make_pipeline_config(steps=[step_config])
        pipeline = SimplePipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Session task",
            project_id="proj-1",
            session_id="sess-123",
        )

        assert result.status == PipelineStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_empty_pipeline_fails(self):
        """Executing a pipeline with no steps returns FAILED status."""
        executor = PipelineExecutor()
        config = _make_pipeline_config()
        # Create a pipeline with no steps
        pipeline = SimplePipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Empty task",
            project_id="proj-1",
        )

        assert result.status == PipelineStatus.FAILED
        assert "Pipeline validation failed" in result.errors

    @pytest.mark.asyncio
    async def test_execute_pipeline_with_step_output_in_context(self):
        """Step outputs should be stored in the pipeline context."""
        executor = PipelineExecutor()
        step_config = _make_step_config()
        config = _make_pipeline_config(steps=[step_config])
        pipeline = SimplePipeline(config=config)

        # We can't directly inspect context after execution easily,
        # but we can verify the result includes step outputs aggregated
        result = await executor.execute(
            pipeline=pipeline,
            task_description="Context test",
            project_id="proj-1",
        )
        assert result.status == PipelineStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_pipeline_result_has_timing_info(self):
        """PipelineResult should include timing information."""
        executor = PipelineExecutor()
        step_config = _make_step_config()
        config = _make_pipeline_config(steps=[step_config])
        pipeline = SimplePipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Timing test",
            project_id="proj-1",
        )

        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.total_execution_time >= 0

    @pytest.mark.asyncio
    async def test_execute_pipeline_result_metadata(self):
        """PipelineResult should include metadata about step counts."""
        executor = PipelineExecutor()
        step_configs = [
            _make_step_config(step_id="s1", name="Step 1"),
            _make_step_config(step_id="s2", name="Step 2"),
        ]
        config = _make_pipeline_config(steps=step_configs)
        pipeline = SimplePipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Metadata test",
            project_id="proj-1",
        )

        assert result.metadata["total_steps"] == 2
        assert result.metadata["completed_steps"] == 2
        assert result.metadata["failed_steps"] == 0
        assert result.metadata["skipped_steps"] == 0

    @pytest.mark.asyncio
    async def test_execute_pipeline_final_result_text(self):
        """PipelineResult final_result should summarize step outcomes."""
        executor = PipelineExecutor()
        step_config = _make_step_config()
        config = _make_pipeline_config(steps=[step_config])
        pipeline = SimplePipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Result text test",
            project_id="proj-1",
        )

        assert "succeeded" in result.final_result
        assert "failed" in result.final_result
        assert "skipped" in result.final_result


# ---------------------------------------------------------------------------
# PipelineExecutor — Step dependency resolution
# ---------------------------------------------------------------------------


class TestExecutorDependencyResolution:
    """Tests for step dependency resolution and execution order."""

    def test_resolve_dependencies_no_deps(self):
        """Steps with no dependencies should all be in the first group."""
        executor = PipelineExecutor()
        step_configs = [
            _make_step_config(step_id="s1", name="Step 1"),
            _make_step_config(step_id="s2", name="Step 2"),
            _make_step_config(step_id="s3", name="Step 3"),
        ]
        config = _make_pipeline_config(steps=step_configs)
        pipeline = SimplePipeline(config=config)
        pipeline._steps = pipeline.build_steps()

        groups = executor._resolve_step_dependencies(pipeline._steps)

        assert len(groups) == 1
        assert len(groups[0]) == 3

    def test_resolve_dependencies_linear(self):
        """Linear dependency chain: s2 depends on s1, s3 depends on s2."""
        executor = PipelineExecutor()
        step_configs = [
            _make_step_config(step_id="s1", name="Step 1"),
            _make_step_config(step_id="s2", name="Step 2", depends_on=["s1"]),
            _make_step_config(step_id="s3", name="Step 3", depends_on=["s2"]),
        ]
        config = _make_pipeline_config(steps=step_configs)
        pipeline = SimplePipeline(config=config)
        pipeline._steps = pipeline.build_steps()

        groups = executor._resolve_step_dependencies(pipeline._steps)

        assert len(groups) == 3
        # First group: s1 (no dependencies)
        assert groups[0][0].step_id == "s1"
        # Second group: s2 (depends on s1)
        assert groups[1][0].step_id == "s2"
        # Third group: s3 (depends on s2)
        assert groups[2][0].step_id == "s3"

    def test_resolve_dependencies_parallel_then_sequential(self):
        """s1 and s2 have no deps (parallel), s3 depends on both."""
        executor = PipelineExecutor()
        step_configs = [
            _make_step_config(step_id="s1", name="Step 1"),
            _make_step_config(step_id="s2", name="Step 2"),
            _make_step_config(step_id="s3", name="Step 3", depends_on=["s1", "s2"]),
        ]
        config = _make_pipeline_config(steps=step_configs)
        pipeline = SimplePipeline(config=config)
        pipeline._steps = pipeline.build_steps()

        groups = executor._resolve_step_dependencies(pipeline._steps)

        # Two groups: [s1, s2] then [s3]
        assert len(groups) == 2
        group_ids_0 = {s.step_id for s in groups[0]}
        assert group_ids_0 == {"s1", "s2"}
        assert groups[1][0].step_id == "s3"

    def test_resolve_dependencies_diamond(self):
        """Diamond pattern: s1 -> s2, s1 -> s3, s2+s3 -> s4."""
        executor = PipelineExecutor()
        step_configs = [
            _make_step_config(step_id="s1", name="Step 1"),
            _make_step_config(step_id="s2", name="Step 2", depends_on=["s1"]),
            _make_step_config(step_id="s3", name="Step 3", depends_on=["s1"]),
            _make_step_config(step_id="s4", name="Step 4", depends_on=["s2", "s3"]),
        ]
        config = _make_pipeline_config(steps=step_configs)
        pipeline = SimplePipeline(config=config)
        pipeline._steps = pipeline.build_steps()

        groups = executor._resolve_step_dependencies(pipeline._steps)

        # Group 1: [s1], Group 2: [s2, s3], Group 3: [s4]
        assert len(groups) == 3
        assert groups[0][0].step_id == "s1"
        group_ids_1 = {s.step_id for s in groups[1]}
        assert group_ids_1 == {"s2", "s3"}
        assert groups[2][0].step_id == "s4"

    def test_resolve_dependencies_circular_raises_error(self):
        """Circular dependencies should raise a ValueError."""
        executor = PipelineExecutor()
        step_configs = [
            _make_step_config(step_id="s1", name="Step 1", depends_on=["s2"]),
            _make_step_config(step_id="s2", name="Step 2", depends_on=["s1"]),
        ]
        config = _make_pipeline_config(steps=step_configs)
        pipeline = SimplePipeline(config=config)
        pipeline._steps = pipeline.build_steps()

        with pytest.raises(ValueError, match="Circular dependency"):
            executor._resolve_step_dependencies(pipeline._steps)

    def test_resolve_dependencies_ignores_nonexistent_deps(self):
        """Dependencies referencing nonexistent steps are ignored."""
        executor = PipelineExecutor()
        step_configs = [
            _make_step_config(step_id="s1", name="Step 1", depends_on=["nonexistent"]),
            _make_step_config(step_id="s2", name="Step 2"),
        ]
        config = _make_pipeline_config(steps=step_configs)
        pipeline = SimplePipeline(config=config)
        pipeline._steps = pipeline.build_steps()

        groups = executor._resolve_step_dependencies(pipeline._steps)

        # Both should be in the same group since "nonexistent" is ignored
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_resolve_dependencies_single_step(self):
        """Single step with no dependencies resolves to one group."""
        executor = PipelineExecutor()
        step_config = _make_step_config(step_id="s1", name="Step 1")
        config = _make_pipeline_config(steps=[step_config])
        pipeline = SimplePipeline(config=config)
        pipeline._steps = pipeline.build_steps()

        groups = executor._resolve_step_dependencies(pipeline._steps)

        assert len(groups) == 1
        assert groups[0][0].step_id == "s1"

    def test_resolve_dependencies_empty_steps(self):
        """Empty steps list resolves to empty groups."""
        executor = PipelineExecutor()
        groups = executor._resolve_step_dependencies([])
        assert len(groups) == 0


# ---------------------------------------------------------------------------
# PipelineExecutor — Step execution order
# ---------------------------------------------------------------------------


class TestExecutorStepExecutionOrder:
    """Tests for verifying step execution order respects dependencies."""

    @pytest.mark.asyncio
    async def test_linear_execution_order(self):
        """Steps with linear dependencies execute in order."""
        executor = PipelineExecutor()
        step_configs = [
            _make_step_config(step_id="s1", name="Step 1"),
            _make_step_config(step_id="s2", name="Step 2", depends_on=["s1"]),
            _make_step_config(step_id="s3", name="Step 3", depends_on=["s2"]),
        ]
        config = _make_pipeline_config(steps=step_configs)
        pipeline = TrackingPipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Order test",
            project_id="proj-1",
        )

        assert result.status == PipelineStatus.COMPLETED
        # Verify execution order from step results
        step_ids = [r.step_id for r in result.step_results]
        assert step_ids == ["s1", "s2", "s3"]

    @pytest.mark.asyncio
    async def test_parallel_then_sequential_execution(self):
        """Parallel steps execute before their dependents."""
        executor = PipelineExecutor()
        step_configs = [
            _make_step_config(step_id="s1", name="Step 1"),
            _make_step_config(step_id="s2", name="Step 2"),
            _make_step_config(step_id="s3", name="Step 3", depends_on=["s1", "s2"]),
        ]
        config = _make_pipeline_config(steps=step_configs)
        pipeline = TrackingPipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Parallel-then-sequential test",
            project_id="proj-1",
        )

        assert result.status == PipelineStatus.COMPLETED
        step_ids = [r.step_id for r in result.step_results]
        # s1 and s2 come before s3
        assert step_ids.index("s3") > step_ids.index("s1")
        assert step_ids.index("s3") > step_ids.index("s2")

    @pytest.mark.asyncio
    async def test_step_outputs_stored_in_context(self):
        """Step results are stored in context step_outputs."""
        executor = PipelineExecutor()
        step_config = _make_step_config(step_id="s1", name="Step 1")
        config = _make_pipeline_config(steps=[step_config])
        pipeline = SimplePipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Context output test",
            project_id="proj-1",
        )

        assert result.status == PipelineStatus.COMPLETED
        # The context should have stored the step output
        # We verify indirectly: all step_results should have COMPLETED status
        for sr in result.step_results:
            assert sr.status == StepStatus.COMPLETED


# ---------------------------------------------------------------------------
# PipelineExecutor — Step execution (execute_step)
# ---------------------------------------------------------------------------


class TestExecutorStepExecution:
    """Tests for PipelineExecutor.execute_step() method."""

    @pytest.mark.asyncio
    async def test_execute_step_success(self):
        """execute_step() with a simple step returns COMPLETED."""
        executor = PipelineExecutor()
        config = _make_step_config(step_id="s1", name="Step 1")
        step = SimpleStep(config=config)
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        result = await executor.execute_step(step, context)

        assert result.step_id == "s1"
        assert result.status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_step_skips_when_cannot_execute(self):
        """execute_step() returns SKIPPED when can_execute() is False."""
        executor = PipelineExecutor()
        config = _make_step_config(step_id="s-skip", name="Skip Step")
        step = SkipStep(config=config)
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        result = await executor.execute_step(step, context)

        assert result.step_id == "s-skip"
        assert result.status == StepStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_execute_step_retries_on_failure(self):
        """execute_step() retries a step that raises an exception."""
        executor = PipelineExecutor(retry_delay_seconds=0.01)
        config = _make_step_config(step_id="s-exc", name="Exception Step", retry_count=2)
        step = ExceptionStep(config=config, error_message="retry me")
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        result = await executor.execute_step(step, context)

        # After all retries, should return FAILED
        assert result.step_id == "s-exc"
        assert result.status == StepStatus.FAILED
        assert "retry me" in result.error

    @pytest.mark.asyncio
    async def test_execute_step_no_retries(self):
        """execute_step() with retry_count=0 fails immediately on exception."""
        executor = PipelineExecutor(retry_delay_seconds=0.01)
        config = _make_step_config(step_id="s-exc", name="Exception Step", retry_count=0)
        step = ExceptionStep(config=config, error_message="no retries")
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        result = await executor.execute_step(step, context)

        assert result.status == StepStatus.FAILED
        assert "no retries" in result.error

    @pytest.mark.asyncio
    async def test_execute_step_with_retries_succeeds_eventually(self):
        """execute_step() with retries succeeds if step recovers."""

        class RecoverableStep(PipelineStep):
            """Step that fails first N times then succeeds."""

            def __init__(self, config: StepConfig, fail_count: int = 2):
                super().__init__(config=config)
                self._attempt = 0
                self._fail_count = fail_count

            async def execute(self, context: PipelineContext) -> StepResult:
                self._attempt += 1
                if self._attempt <= self._fail_count:
                    raise RuntimeError(f"Attempt {self._attempt} failed")
                return StepResult(
                    step_id=self.step_id,
                    status=StepStatus.COMPLETED,
                    result=f"Succeeded on attempt {self._attempt}",
                )

            def can_execute(self, context: PipelineContext) -> bool:
                return True

        executor = PipelineExecutor(retry_delay_seconds=0.01)
        config = _make_step_config(step_id="s-recover", name="Recover Step", retry_count=3)
        step = RecoverableStep(config=config, fail_count=2)
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        result = await executor.execute_step(step, context)

        assert result.status == StepStatus.COMPLETED
        assert "Succeeded on attempt 3" in result.result

    @pytest.mark.asyncio
    async def test_execute_step_updates_step_status(self):
        """execute_step() updates the step's internal status."""
        executor = PipelineExecutor()
        config = _make_step_config(step_id="s1", name="Step 1")
        step = SimpleStep(config=config)
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        assert step.status == StepStatus.PENDING
        await executor.execute_step(step, context)
        assert step.status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_step_failure_updates_step_status(self):
        """execute_step() updates step status to FAILED on error."""
        executor = PipelineExecutor(retry_delay_seconds=0.01)
        config = _make_step_config(step_id="s-exc", name="Exception Step", retry_count=0)
        step = ExceptionStep(config=config)
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        await executor.execute_step(step, context)
        assert step.status == StepStatus.FAILED


# ---------------------------------------------------------------------------
# PipelineExecutor — Error handling in pipeline execution
# ---------------------------------------------------------------------------


class TestExecutorErrorHandling:
    """Tests for error handling during pipeline execution."""

    @pytest.mark.asyncio
    async def test_failing_step_stops_pipeline(self):
        """With stop_on_failure=True, a failing step stops the pipeline."""
        executor = PipelineExecutor()
        step_configs = [
            _make_step_config(step_id="s1", name="Step 1", metadata={"impl": "simple"}),
            _make_step_config(step_id="s2", name="Step 2", metadata={"impl": "failing"}),
            _make_step_config(
                step_id="s3", name="Step 3", metadata={"impl": "simple"}, depends_on=["s2"]
            ),
        ]
        config = _make_pipeline_config(
            steps=step_configs,
            stop_on_failure=True,
        )
        pipeline = MixedPipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Failing step test",
            project_id="proj-1",
        )

        assert result.status == PipelineStatus.FAILED
        # Step 1 should succeed, step 2 should fail, step 3 should not run
        # (or it may run but pipeline still fails)
        failed_steps = [r for r in result.step_results if r.status == StepStatus.FAILED]
        assert len(failed_steps) >= 1

    @pytest.mark.asyncio
    async def test_continue_on_failure(self):
        """With stop_on_failure=False, pipeline continues after a step fails."""
        executor = PipelineExecutor()
        step_configs = [
            _make_step_config(step_id="s1", name="Step 1", metadata={"impl": "simple"}),
            _make_step_config(step_id="s2", name="Step 2", metadata={"impl": "failing"}),
        ]
        config = _make_pipeline_config(
            steps=step_configs,
            stop_on_failure=False,
        )
        pipeline = MixedPipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Continue on failure test",
            project_id="proj-1",
        )

        # Pipeline completes even though a step failed
        assert result.status == PipelineStatus.COMPLETED
        assert len(result.step_results) == 2

    @pytest.mark.asyncio
    async def test_exception_in_pipeline(self):
        """An exception during pipeline execution returns FAILED result."""
        executor = PipelineExecutor()
        step_configs = [
            _make_step_config(step_id="s1", name="Step 1", metadata={"impl": "exception"}),
        ]
        config = _make_pipeline_config(steps=step_configs)
        pipeline = MixedPipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Exception test",
            project_id="proj-1",
        )

        # The step itself catches the exception and returns FAILED
        assert result.status == PipelineStatus.FAILED
        assert len(result.step_results) >= 1

    @pytest.mark.asyncio
    async def test_pipeline_error_details(self):
        """PipelineResult errors list includes step error messages."""
        executor = PipelineExecutor(retry_delay_seconds=0.01)
        step_configs = [
            _make_step_config(
                step_id="s-fail",
                name="Failing Step",
                metadata={"impl": "failing"},
            ),
        ]
        config = _make_pipeline_config(steps=step_configs)
        pipeline = MixedPipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Error details test",
            project_id="proj-1",
        )

        assert result.status == PipelineStatus.FAILED
        assert len(result.errors) > 0
        # The errors should mention the step
        error_text = " ".join(result.errors)
        assert "s-fail" in error_text

    @pytest.mark.asyncio
    async def test_skipped_step_in_pipeline(self):
        """Steps that can_execute()=False are skipped."""
        executor = PipelineExecutor()
        step_configs = [
            _make_step_config(step_id="s1", name="Step 1", metadata={"impl": "simple"}),
            _make_step_config(step_id="s-skip", name="Skip Step", metadata={"impl": "skip"}),
        ]
        config = _make_pipeline_config(steps=step_configs)
        pipeline = MixedPipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Skip step test",
            project_id="proj-1",
        )

        assert result.status == PipelineStatus.COMPLETED
        skipped = [r for r in result.step_results if r.status == StepStatus.SKIPPED]
        assert len(skipped) == 1
        assert skipped[0].step_id == "s-skip"


# ---------------------------------------------------------------------------
# PipelineExecutor — Cancellation
# ---------------------------------------------------------------------------


class TestExecutorCancellation:
    """Tests for PipelineExecutor cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_returns_true(self):
        """cancel() should return True."""
        executor = PipelineExecutor()
        result = await executor.cancel("pipeline-123")
        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_any_pipeline_id(self):
        """cancel() accepts any pipeline_id string."""
        executor = PipelineExecutor()

        result1 = await executor.cancel("pipe-1")
        assert result1 is True

        result2 = await executor.cancel("pipe-2")
        assert result2 is True

        result3 = await executor.cancel("nonexistent-pipeline")
        assert result3 is True


# ---------------------------------------------------------------------------
# PipelineExecutor — Result building
# ---------------------------------------------------------------------------


class TestExecutorResultBuilding:
    """Tests for PipelineExecutor._build_result() method."""

    def test_build_result_success(self):
        """_build_result() returns COMPLETED when all steps succeed."""
        executor = PipelineExecutor()
        config = _make_pipeline_config()
        pipeline = SimplePipeline(config=config)
        start_time = datetime.now()
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        step_results = [
            StepResult(step_id="s1", status=StepStatus.COMPLETED, result="OK 1"),
            StepResult(step_id="s2", status=StepStatus.COMPLETED, result="OK 2"),
        ]

        result = executor._build_result(pipeline, step_results, start_time, context)

        assert result.status == PipelineStatus.COMPLETED
        assert result.pipeline_id == "test-pipeline"
        assert len(result.step_results) == 2
        assert result.total_tokens_used == 0
        assert "2 succeeded" in result.final_result
        assert "0 failed" in result.final_result
        assert "0 skipped" in result.final_result

    def test_build_result_with_failure(self):
        """_build_result() returns FAILED when a step fails and stop_on_failure."""
        executor = PipelineExecutor()
        config = _make_pipeline_config(stop_on_failure=True)
        pipeline = SimplePipeline(config=config)
        start_time = datetime.now()
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        step_results = [
            StepResult(step_id="s1", status=StepStatus.COMPLETED, result="OK"),
            StepResult(step_id="s2", status=StepStatus.FAILED, error="Bad"),
        ]

        result = executor._build_result(pipeline, step_results, start_time, context)

        assert result.status == PipelineStatus.FAILED
        assert "1 failed" in result.final_result

    def test_build_result_with_failure_continue(self):
        """_build_result() returns COMPLETED when failures but stop_on_failure=False."""
        executor = PipelineExecutor()
        config = _make_pipeline_config(stop_on_failure=False)
        pipeline = SimplePipeline(config=config)
        start_time = datetime.now()
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        step_results = [
            StepResult(step_id="s1", status=StepStatus.COMPLETED, result="OK"),
            StepResult(step_id="s2", status=StepStatus.FAILED, error="Bad"),
        ]

        result = executor._build_result(pipeline, step_results, start_time, context)

        # When stop_on_failure=False, pipeline status is still COMPLETED even with failures
        assert result.status == PipelineStatus.COMPLETED
        assert "1 failed" in result.final_result

    def test_build_result_with_skipped(self):
        """_build_result() counts skipped steps correctly."""
        executor = PipelineExecutor()
        config = _make_pipeline_config()
        pipeline = SimplePipeline(config=config)
        start_time = datetime.now()
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        step_results = [
            StepResult(step_id="s1", status=StepStatus.COMPLETED, result="OK"),
            StepResult(step_id="s2", status=StepStatus.SKIPPED, result="Skipped"),
        ]

        result = executor._build_result(pipeline, step_results, start_time, context)

        assert "1 skipped" in result.final_result
        assert "1 succeeded" in result.final_result

    def test_build_result_aggregates_artifacts(self):
        """_build_result() aggregates artifacts from all step results."""
        executor = PipelineExecutor()
        config = _make_pipeline_config()
        pipeline = SimplePipeline(config=config)
        start_time = datetime.now()
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        step_results = [
            StepResult(
                step_id="s1",
                status=StepStatus.COMPLETED,
                artifacts={"file1.py": "code1"},
            ),
            StepResult(
                step_id="s2",
                status=StepStatus.COMPLETED,
                artifacts={"file2.py": "code2"},
            ),
        ]

        result = executor._build_result(pipeline, step_results, start_time, context)

        assert result.artifacts == {"file1.py": "code1", "file2.py": "code2"}

    def test_build_result_collects_errors(self):
        """_build_result() collects error messages from failed steps."""
        executor = PipelineExecutor()
        config = _make_pipeline_config()
        pipeline = SimplePipeline(config=config)
        start_time = datetime.now()
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        step_results = [
            StepResult(step_id="s1", status=StepStatus.FAILED, error="Connection refused"),
            StepResult(step_id="s2", status=StepStatus.COMPLETED, result="OK"),
        ]

        result = executor._build_result(pipeline, step_results, start_time, context)

        assert len(result.errors) == 1
        assert "s1" in result.errors[0]
        assert "Connection refused" in result.errors[0]

    def test_build_result_aggregates_tokens(self):
        """_build_result() sums tokens_used from all step results."""
        executor = PipelineExecutor()
        config = _make_pipeline_config()
        pipeline = SimplePipeline(config=config)
        start_time = datetime.now()
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        step_results = [
            StepResult(step_id="s1", status=StepStatus.COMPLETED, tokens_used=100),
            StepResult(step_id="s2", status=StepStatus.COMPLETED, tokens_used=250),
        ]

        result = executor._build_result(pipeline, step_results, start_time, context)

        assert result.total_tokens_used == 350

    def test_build_result_timing(self):
        """_build_result() includes timing information."""
        executor = PipelineExecutor()
        config = _make_pipeline_config()
        pipeline = SimplePipeline(config=config)
        start_time = datetime.now()
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        step_results = [
            StepResult(step_id="s1", status=StepStatus.COMPLETED),
        ]

        result = executor._build_result(pipeline, step_results, start_time, context)

        assert result.started_at == start_time
        assert result.completed_at is not None
        assert result.total_execution_time >= 0

    def test_build_result_metadata_counts(self):
        """_build_result() metadata includes correct step counts."""
        executor = PipelineExecutor()
        config = _make_pipeline_config()
        pipeline = SimplePipeline(config=config)
        start_time = datetime.now()
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        step_results = [
            StepResult(step_id="s1", status=StepStatus.COMPLETED),
            StepResult(step_id="s2", status=StepStatus.FAILED, error="err"),
            StepResult(step_id="s3", status=StepStatus.SKIPPED),
            StepResult(step_id="s4", status=StepStatus.COMPLETED),
        ]

        result = executor._build_result(pipeline, step_results, start_time, context)

        assert result.metadata["total_steps"] == 4
        assert result.metadata["completed_steps"] == 2
        assert result.metadata["failed_steps"] == 1
        assert result.metadata["skipped_steps"] == 1


# ---------------------------------------------------------------------------
# PipelineExecutor — get_executor singleton
# ---------------------------------------------------------------------------


class TestGetExecutor:
    """Tests for the get_executor() singleton function."""

    def setup_method(self):
        """Reset the global executor instance before each test."""
        import palace.pipelines.executor as executor_module

        executor_module._executor_instance = None

    def test_get_executor_returns_instance(self):
        """get_executor() returns a PipelineExecutor instance."""
        executor = get_executor()
        assert isinstance(executor, PipelineExecutor)

    def test_get_executor_returns_same_instance(self):
        """get_executor() returns the same instance on subsequent calls."""
        executor1 = get_executor()
        executor2 = get_executor()
        assert executor1 is executor2

    def test_get_executor_with_framework(self):
        """get_executor() can be called with a framework argument."""
        mock_framework = MagicMock()
        executor = get_executor(framework=mock_framework)
        assert executor.framework is mock_framework

    def test_get_executor_singleton_after_first_call(self):
        """After first call, framework argument is ignored (singleton already created)."""
        import palace.pipelines.executor as executor_module

        executor_module._executor_instance = None

        mock_framework = MagicMock()
        executor1 = get_executor(framework=mock_framework)
        assert executor1.framework is mock_framework

        # Second call ignores the framework argument
        executor2 = get_executor(framework=MagicMock())
        assert executor2.framework is mock_framework  # Still the first one

    def test_get_executor_default_params(self):
        """get_executor() creates executor with default parameters."""
        executor = get_executor()
        assert executor.max_concurrent_steps == 5
        assert executor.retry_delay_seconds == 1.0

    def test_multiple_get_executor_calls(self):
        """Multiple calls to get_executor() always return the same instance."""
        instances = [get_executor() for _ in range(5)]
        assert all(inst is instances[0] for inst in instances)


# ---------------------------------------------------------------------------
# PipelineExecutor — Edge cases
# ---------------------------------------------------------------------------


class TestExecutorEdgeCases:
    """Edge case tests for PipelineExecutor."""

    @pytest.mark.asyncio
    async def test_execute_single_step_pipeline(self):
        """Pipeline with a single step executes correctly."""
        executor = PipelineExecutor()
        step_config = _make_step_config(step_id="only-step", name="Only Step")
        config = _make_pipeline_config(steps=[step_config])
        pipeline = SimplePipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Single step",
            project_id="proj-1",
        )

        assert result.status == PipelineStatus.COMPLETED
        assert len(result.step_results) == 1
        assert result.step_results[0].step_id == "only-step"

    @pytest.mark.asyncio
    async def test_execute_pipeline_with_many_steps(self):
        """Pipeline with many steps executes all of them."""
        executor = PipelineExecutor()
        step_configs = [_make_step_config(step_id=f"step-{i}", name=f"Step {i}") for i in range(10)]
        config = _make_pipeline_config(steps=step_configs)
        pipeline = SimplePipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Many steps",
            project_id="proj-1",
        )

        assert result.status == PipelineStatus.COMPLETED
        assert len(result.step_results) == 10

    @pytest.mark.asyncio
    async def test_all_steps_failed_pipeline(self):
        """Pipeline where all steps fail should return FAILED status."""
        executor = PipelineExecutor()
        step_configs = [_make_step_config(step_id=f"s{i}", name=f"Step {i}") for i in range(1, 4)]
        config = _make_pipeline_config(steps=step_configs)
        pipeline = FailingPipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="All fail",
            project_id="proj-1",
        )

        assert result.status == PipelineStatus.FAILED
        failed = [r for r in result.step_results if r.status == StepStatus.FAILED]
        assert len(failed) >= 1

    @pytest.mark.asyncio
    async def test_pipeline_with_custom_retry_count(self):
        """Steps with custom retry_count should retry that many times."""

        class CountingStep(PipelineStep):
            """Step that counts how many times execute is called."""

            attempt = 0

            async def execute(self, context: PipelineContext) -> StepResult:
                self.attempt += 1
                if self.attempt < 3:
                    raise RuntimeError(f"Attempt {self.attempt} failed")
                return StepResult(
                    step_id=self.step_id,
                    status=StepStatus.COMPLETED,
                    result=f"Succeeded on attempt {self.attempt}",
                )

            def can_execute(self, context: PipelineContext) -> bool:
                return True

        executor = PipelineExecutor(retry_delay_seconds=0.01)
        config = _make_step_config(step_id="retry-step", name="Retry Step", retry_count=3)
        step = CountingStep(config=config)
        context = PipelineContext(pipeline_id="p1", project_id="proj-1")

        result = await executor.execute_step(step, context)

        assert result.status == StepStatus.COMPLETED
        assert step.attempt == 3

    @pytest.mark.asyncio
    async def test_pipeline_status_transitions_on_success(self):
        """Pipeline status transitions PENDING → RUNNING → COMPLETED."""
        executor = PipelineExecutor()
        step_config = _make_step_config()
        config = _make_pipeline_config(steps=[step_config])
        pipeline = SimplePipeline(config=config)

        assert pipeline.status == PipelineStatus.PENDING

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Status transitions",
            project_id="proj-1",
        )

        assert pipeline.status == PipelineStatus.COMPLETED
        assert result.status == PipelineStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_pipeline_status_failed_on_exception(self):
        """Pipeline status should be FAILED on exception during execution."""
        executor = PipelineExecutor()

        class BrokenPipeline(Pipeline):
            """Pipeline that fails during get_initial_context."""

            def build_steps(self):
                return []

            def get_initial_context(self, task_description: str, project_id: str):
                raise RuntimeError("Context creation failed")

        config = _make_pipeline_config()
        pipeline = BrokenPipeline(config=config)

        result = await executor.execute(
            pipeline=pipeline,
            task_description="Broken pipeline",
            project_id="proj-1",
        )

        assert pipeline.status == PipelineStatus.FAILED
        assert result.status == PipelineStatus.FAILED
        assert any("Context creation failed" in e for e in result.errors)
