"""
Palace Framework - Ejecutor de Pipelines

Este módulo implementa el ejecutor de pipelines, responsable de gestionar
la ejecución de flujos de trabajo complejos que involucran múltiples pasos
y agentes. El ejecutor maneja la resolución de dependencias entre pasos,
la ejecución paralela y secuencial, la lógica de reintentos, y la
recolección de resultados.

Componentes principales:
    - PipelineExecutor: Clase principal que gestiona la ejecución de pipelines
    - get_executor: Función para obtener la instancia global del ejecutor

Arquitectura:
    ┌─────────────────────────────────────────────────────────┐
    │                   PipelineExecutor                       │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │  _resolve_step_dependencies()                      │  │
    │  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐               │  │
    │  │  │ G1  │ │ G2  │ │ G3  │ │ G4  │               │  │
    │  │  └─────┘ └─────┘ └─────┘ └─────┘               │  │
    │  └───────────────────────────────────────────────────┘  │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │  _execute_steps()                                  │  │
    │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │  │
    │  │  │  Agent   │  │ Parallel │  │Condicion │       │  │
    │  │  └──────────┘  └──────────┘  └──────────┘       │  │
    │  └───────────────────────────────────────────────────┘  │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │  _build_result()                                   │  │
    │  │  Collect artifacts, errors, tokens, time           │  │
    │  └───────────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────────┘
"""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

import structlog

from palace.pipelines.base import (
    Pipeline,
    PipelineContext,
    PipelineResult,
    PipelineStatus,
    PipelineStep,
    StepResult,
    StepStatus,
)
from palace.pipelines.types import PipelineConfig, StepType

if TYPE_CHECKING:
    from palace.core.framework import PalaceFramework


class PipelineExecutor:
    """Ejecutor de pipelines.

    Gestiona la ejecución de pipelines, incluyendo la resolución de
    dependencias entre pasos, manejo de errores y recolección de resultados.
    """

    def __init__(
        self,
        framework: Optional["PalaceFramework"] = None,
        max_concurrent_steps: int = 5,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self.framework = framework
        self.max_concurrent_steps = max_concurrent_steps
        self.retry_delay_seconds = retry_delay_seconds
        self._logger = structlog.get_logger()

    async def execute(
        self,
        pipeline: Pipeline,
        task_description: str,
        project_id: str,
        session_id: Optional[str] = None,
    ) -> PipelineResult:
        """Main execution method.

        Executes a pipeline by initializing context, building steps,
        validating, and running all steps in dependency order.

        Args:
            pipeline: The pipeline to execute.
            task_description: Description of the task to accomplish.
            project_id: Project identifier for context isolation.
            session_id: Optional session identifier for continuity.

        Returns:
            PipelineResult with execution results and metadata.
        """
        start_time = datetime.now()
        self._logger.info(
            "pipeline_execution_started",
            pipeline_id=pipeline.pipeline_id,
            project_id=project_id,
        )

        try:
            # 1. Initialize pipeline context
            context = pipeline.get_initial_context(
                task_description=task_description,
                project_id=project_id,
            )
            if session_id:
                context.session_id = session_id

            # 2. Build steps
            pipeline._steps = pipeline.build_steps()
            self._logger.info(
                "pipeline_steps_built",
                pipeline_id=pipeline.pipeline_id,
                step_count=len(pipeline._steps),
            )

            # 3. Validate pipeline
            if not await pipeline.validate():
                pipeline._status = PipelineStatus.FAILED
                return PipelineResult(
                    pipeline_id=pipeline.pipeline_id,
                    status=PipelineStatus.FAILED,
                    errors=["Pipeline validation failed"],
                    started_at=start_time,
                    completed_at=datetime.now(),
                )

            # 4. Set pipeline status to RUNNING
            pipeline._status = PipelineStatus.RUNNING

            # 5. Record start time (already captured above)

            # 6. Execute steps in order (respecting dependencies)
            step_results = await self._execute_steps(
                steps=pipeline._steps,
                context=context,
                pipeline=pipeline,
            )

            # 7. Collect all step results (done within _execute_steps)

            # 8. Set final status
            result = self._build_result(
                pipeline=pipeline,
                step_results=step_results,
                start_time=start_time,
                context=context,
            )
            pipeline._status = result.status

            self._logger.info(
                "pipeline_execution_completed",
                pipeline_id=pipeline.pipeline_id,
                status=result.status,
                total_execution_time=result.total_execution_time,
            )

            return result

        except Exception as e:
            self._logger.error(
                "pipeline_execution_failed",
                pipeline_id=pipeline.pipeline_id,
                error=str(e),
                exc_info=True,
            )
            pipeline._status = PipelineStatus.FAILED
            return PipelineResult(
                pipeline_id=pipeline.pipeline_id,
                status=PipelineStatus.FAILED,
                errors=[str(e)],
                started_at=start_time,
                completed_at=datetime.now(),
            )

    async def execute_step(self, step: PipelineStep, context: PipelineContext) -> StepResult:
        """Execute a single pipeline step.

        Checks if the step can execute, runs it with retry logic,
        and returns the result.

        Args:
            step: The pipeline step to execute.
            context: The current pipeline context.

        Returns:
            StepResult with the step execution outcome.
        """
        # Check if step can execute
        if not step.can_execute(context):
            self._logger.info(
                "step_skipped",
                step_id=step.step_id,
                reason="Condition not met",
            )
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.SKIPPED,
                result=f"Step {step.step_id} skipped: condition not met",
            )

        # Set step status to RUNNING
        step._status = StepStatus.RUNNING

        retry_count = step.config.retry_count
        last_error: Optional[str] = None

        for attempt in range(retry_count + 1):
            try:
                self._logger.info(
                    "step_execution_started",
                    step_id=step.step_id,
                    attempt=attempt + 1,
                    max_retries=retry_count,
                )
                result = await step.execute(context)
                step._status = result.status
                step._result = result
                self._logger.info(
                    "step_execution_completed",
                    step_id=step.step_id,
                    status=result.status,
                )
                return result
            except Exception as e:
                last_error = str(e)
                self._logger.warning(
                    "step_execution_failed",
                    step_id=step.step_id,
                    attempt=attempt + 1,
                    max_retries=retry_count,
                    error=last_error,
                )
                if attempt < retry_count:
                    await asyncio.sleep(self.retry_delay_seconds)

        # All retries exhausted
        step._status = StepStatus.FAILED
        self._logger.error(
            "step_failed_all_retries",
            step_id=step.step_id,
            error=last_error,
        )
        return StepResult(
            step_id=step.step_id,
            status=StepStatus.FAILED,
            error=last_error,
        )

    async def cancel(self, pipeline_id: str) -> bool:
        """Cancel a running pipeline.

        Currently logs the cancellation request. Full cancellation
        support is not yet implemented.

        Args:
            pipeline_id: Identifier of the pipeline to cancel.

        Returns:
            True indicating the cancellation request was received.
        """
        self._logger.info(
            "pipeline_cancellation_requested",
            pipeline_id=pipeline_id,
            note="Cancellation is not fully implemented yet",
        )
        return True

    async def _execute_steps(
        self,
        steps: List[PipelineStep],
        context: PipelineContext,
        pipeline: Pipeline,
    ) -> List[StepResult]:
        """Execute steps respecting dependencies and step types.

        Groups steps by their dependency level and executes them
        in topological order. Handles PARALLEL, CONDITIONAL, and
        AGENT_TASK step types specially.

        Args:
            steps: List of pipeline steps to execute.
            context: The current pipeline context.
            pipeline: The parent pipeline (for configuration).

        Returns:
            List of all StepResult objects from executed steps.
        """
        all_results: List[StepResult] = []
        step_groups = self._resolve_step_dependencies(steps)

        stop_on_failure = pipeline.config.stop_on_failure

        for group_index, group in enumerate(step_groups):
            self._logger.info(
                "executing_step_group",
                pipeline_id=pipeline.pipeline_id,
                group_index=group_index,
                group_size=len(group),
            )

            # Execute steps within a group, potentially in parallel
            # but respecting max_concurrent_steps
            group_results = await self._execute_step_group(
                group=group,
                context=context,
                stop_on_failure=stop_on_failure,
                pipeline=pipeline,
            )
            all_results.extend(group_results)

            # Check for failures if stop_on_failure is enabled
            if stop_on_failure:
                failed_results = [r for r in group_results if r.status == StepStatus.FAILED]
                if failed_results:
                    self._logger.warning(
                        "stopping_pipeline_on_failure",
                        pipeline_id=pipeline.pipeline_id,
                        failed_steps=[r.step_id for r in failed_results],
                    )
                    break

        return all_results

    async def _execute_step_group(
        self,
        group: List[PipelineStep],
        context: PipelineContext,
        stop_on_failure: bool,
        pipeline: Pipeline,
    ) -> List[StepResult]:
        """Execute a group of steps that can run in parallel.

        Respects the max_concurrent_steps limit and handles
        different step types appropriately.

        Args:
            group: List of steps that can run concurrently.
            context: The current pipeline context.
            stop_on_failure: Whether to stop on step failure.
            pipeline: The parent pipeline.

        Returns:
            List of StepResult objects for this group.
        """
        results: List[StepResult] = []

        # Process steps in batches respecting max_concurrent_steps
        for i in range(0, len(group), self.max_concurrent_steps):
            batch = group[i : i + self.max_concurrent_steps]
            batch_results = await asyncio.gather(
                *[self._execute_single_step(step, context, pipeline) for step in batch]
            )

            for step, result in zip(batch, batch_results):
                # Store step output in context
                context.step_outputs[step.step_id] = result
                results.append(result)

                # If stop_on_failure, don't continue the batch
                if stop_on_failure and result.status == StepStatus.FAILED:
                    break

            # If stop_on_failure, don't continue to next batch
            if stop_on_failure and any(r.status == StepStatus.FAILED for r in results):
                break

        return results

    async def _execute_single_step(
        self,
        step: PipelineStep,
        context: PipelineContext,
        pipeline: Pipeline,
    ) -> StepResult:
        """Execute a single step, dispatching based on step type.

        Args:
            step: The step to execute.
            context: The current pipeline context.
            pipeline: The parent pipeline.

        Returns:
            StepResult from the step execution.
        """
        step_type = step.step_type

        # Handle PARALLEL steps: execute sub-steps concurrently
        if step_type == StepType.PARALLEL:
            return await self._execute_parallel_step(step, context, pipeline)

        # Handle CONDITIONAL steps: evaluate the condition
        if step_type == StepType.CONDITIONAL:
            return await self._execute_conditional_step(step, context, pipeline)

        # Handle AGENT_TASK steps: execute via the framework's orchestrator
        if step_type == StepType.AGENT_TASK:
            return await self._execute_agent_step(step, context)

        # Default: execute step normally
        return await self.execute_step(step, context)

    async def _execute_parallel_step(
        self,
        step: PipelineStep,
        context: PipelineContext,
        pipeline: Pipeline,
    ) -> StepResult:
        """Execute a PARALLEL step by running its sub-steps concurrently.

        Args:
            step: The parallel step containing sub-steps.
            context: The current pipeline context.
            pipeline: The parent pipeline.

        Returns:
            StepResult aggregating all sub-step results.
        """
        sub_configs = step.config.parallel_steps
        if not sub_configs:
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.COMPLETED,
                result="Parallel step had no sub-steps",
            )

        # Build sub-steps from their configs
        sub_steps: List[PipelineStep] = []
        for sub_config in sub_configs:
            # Create a minimal PipelineStep wrapper for each sub-config
            sub_step = _ParallelSubStep(sub_config)
            sub_steps.append(sub_step)

        self._logger.info(
            "parallel_step_executing",
            step_id=step.step_id,
            sub_step_count=len(sub_steps),
        )

        # Execute all sub-steps concurrently
        sub_results = await asyncio.gather(
            *[self._execute_single_step(s, context, pipeline) for s in sub_steps],
            return_exceptions=True,
        )

        # Process results
        step_results: List[StepResult] = []
        all_artifacts: Dict[str, Any] = {}
        total_tokens = 0
        has_failure = False
        errors: List[str] = []

        for i, sub_result in enumerate(sub_results):
            if isinstance(sub_result, Exception):
                has_failure = True
                errors.append(f"Sub-step {i} failed: {sub_result}")
                step_results.append(
                    StepResult(
                        step_id=sub_steps[i].step_id,
                        status=StepStatus.FAILED,
                        error=str(sub_result),
                    )
                )
            else:
                result = cast(StepResult, sub_result)
                step_results.append(result)
                all_artifacts.update(result.artifacts)
                total_tokens += result.tokens_used
                if result.status == StepStatus.FAILED:
                    has_failure = True
                    if result.error:
                        errors.append(result.error)

        # Store sub-step outputs in context
        for sr in step_results:
            context.step_outputs[sr.step_id] = sr

        overall_status = StepStatus.FAILED if has_failure else StepStatus.COMPLETED

        return StepResult(
            step_id=step.step_id,
            status=overall_status,
            result=f"Parallel step completed with {len(step_results)} sub-steps",
            artifacts=all_artifacts,
            tokens_used=total_tokens,
            error="; ".join(errors) if errors else None,
        )

    async def _execute_conditional_step(
        self,
        step: PipelineStep,
        context: PipelineContext,
        pipeline: Pipeline,
    ) -> StepResult:
        """Execute a CONDITIONAL step by evaluating its condition.

        Args:
            step: The conditional step to evaluate.
            context: The current pipeline context.
            pipeline: The parent pipeline.

        Returns:
            StepResult based on condition evaluation.
        """
        condition = step.config.condition
        if condition is None:
            self._logger.warning(
                "conditional_step_no_condition",
                step_id=step.step_id,
            )
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.SKIPPED,
                result="Conditional step has no condition defined",
            )

        # Evaluate the condition against context variables
        try:
            condition_met = eval(condition, {"__builtins__": {}}, context.variables)
        except Exception as e:
            self._logger.warning(
                "conditional_evaluation_failed",
                step_id=step.step_id,
                condition=condition,
                error=str(e),
            )
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.SKIPPED,
                result=f"Condition evaluation failed: {e}",
                error=str(e),
            )

        if not condition_met:
            self._logger.info(
                "conditional_step_skipped",
                step_id=step.step_id,
                condition=condition,
            )
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.SKIPPED,
                result=f"Condition not met: {condition}",
            )

        # Condition met, execute the step
        self._logger.info(
            "conditional_step_executing",
            step_id=step.step_id,
            condition=condition,
        )
        return await self.execute_step(step, context)

    async def _execute_agent_step(
        self,
        step: PipelineStep,
        context: PipelineContext,
    ) -> StepResult:
        """Execute a step that requires an agent.

        If the framework is available, delegates execution to the
        framework's orchestrator. Otherwise, returns a mock result
        indicating no framework is configured.

        Args:
            step: The agent task step to execute.
            context: The current pipeline context.

        Returns:
            StepResult with the agent's output or a mock result.
        """
        task_description = step.get_task_description(context)
        agent_role = step.config.agent_role

        if self.framework is not None:
            self._logger.info(
                "agent_step_executing_via_framework",
                step_id=step.step_id,
                agent_role=agent_role,
            )
            try:
                execution_result = await self.framework.execute(
                    task=task_description,
                    project_id=context.project_id,
                    session_id=context.session_id,
                    agent_hint=agent_role,
                    context=context.variables,
                )

                status = (
                    StepStatus.COMPLETED
                    if execution_result.status == "success"
                    else StepStatus.FAILED
                )

                return StepResult(
                    step_id=step.step_id,
                    status=status,
                    result=execution_result.result,
                    agent_used=execution_result.agent_used,
                    execution_time_seconds=execution_result.execution_time,
                    tokens_used=execution_result.metadata.get("tokens_used", 0),
                    artifacts=execution_result.metadata.get("artifacts", {}),
                    metadata=execution_result.metadata,
                )
            except Exception as e:
                self._logger.error(
                    "agent_step_execution_failed",
                    step_id=step.step_id,
                    agent_role=agent_role,
                    error=str(e),
                )
                return StepResult(
                    step_id=step.step_id,
                    status=StepStatus.FAILED,
                    error=f"Agent execution failed: {e}",
                )

        # No framework available — return a mock result
        self._logger.warning(
            "agent_step_no_framework",
            step_id=step.step_id,
            note="No PalaceFramework configured; returning mock result",
        )
        return StepResult(
            step_id=step.step_id,
            status=StepStatus.COMPLETED,
            result=f"[Mock] Agent task '{task_description}' (no framework available)",
            agent_used=agent_role or "mock",
            metadata={"mock": True, "note": "No PalaceFramework instance configured"},
        )

    def _resolve_step_dependencies(self, steps: List[PipelineStep]) -> List[List[PipelineStep]]:
        """Topologically sort steps by their dependencies.

        Groups steps that can run in parallel (same dependency level)
        and returns them as a list of groups. Steps with no
        dependencies go first, followed by steps that depend on
        completed steps.

        Detects circular dependencies and raises an error.

        Args:
            steps: List of pipeline steps to sort.

        Returns:
            List of groups, where each group contains steps that
            can be executed in parallel.

        Raises:
            ValueError: If a circular dependency is detected.
        """
        # Build a map of step_id -> step
        step_map: Dict[str, PipelineStep] = {s.step_id: s for s in steps}

        # Build dependency graph: step_id -> set of dependency step_ids
        dep_graph: Dict[str, set[str]] = {}
        for step in steps:
            deps = set(step.config.depends_on)
            # Only include dependencies that reference actual steps
            deps = {d for d in deps if d in step_map}
            dep_graph[step.step_id] = deps

        # Kahn's algorithm for topological sort with level grouping
        result_groups: List[List[PipelineStep]] = []
        remaining_deps = {sid: set(deps) for sid, deps in dep_graph.items()}
        completed_ids: set[str] = set()

        while remaining_deps:
            # Find all steps with no remaining dependencies
            ready_ids = {sid for sid, deps in remaining_deps.items() if not deps}

            if not ready_ids:
                # No steps are ready but we still have remaining steps
                # This indicates a circular dependency
                remaining_ids = list(remaining_deps.keys())
                raise ValueError(f"Circular dependency detected among steps: {remaining_ids}")

            # Group ready steps together
            ready_steps = [step_map[sid] for sid in sorted(ready_ids)]
            result_groups.append(ready_steps)

            # Mark them as completed and update remaining dependencies
            for sid in ready_ids:
                completed_ids.add(sid)
                del remaining_deps[sid]

            for sid, deps in remaining_deps.items():
                remaining_deps[sid] = deps - completed_ids

        self._logger.info(
            "step_dependencies_resolved",
            total_steps=len(steps),
            num_groups=len(result_groups),
            group_sizes=[len(g) for g in result_groups],
        )

        return result_groups

    def _build_result(
        self,
        pipeline: Pipeline,
        step_results: List[StepResult],
        start_time: datetime,
        context: PipelineContext,
    ) -> PipelineResult:
        """Build the final PipelineResult from all step results.

        Calculates total execution time, sums tokens used, determines
        final status, and collects all artifacts and errors.

        Args:
            pipeline: The pipeline that was executed.
            step_results: Results from all executed steps.
            start_time: When execution started.
            context: The final pipeline context.

        Returns:
            PipelineResult with aggregated execution information.
        """
        end_time = datetime.now()
        total_execution_time = (end_time - start_time).total_seconds()

        # Sum total tokens used
        total_tokens_used = sum(r.tokens_used for r in step_results)

        # Collect all artifacts from step results
        all_artifacts: Dict[str, Any] = {}
        for r in step_results:
            all_artifacts.update(r.artifacts)

        # Collect all errors from failed steps
        errors: List[str] = []
        for r in step_results:
            if r.error:
                errors.append(f"Step {r.step_id}: {r.error}")

        # Determine final status
        has_failure = any(r.status == StepStatus.FAILED for r in step_results)
        stop_on_failure = pipeline.config.stop_on_failure

        if has_failure and stop_on_failure:
            final_status = PipelineStatus.FAILED
        elif has_failure:
            # Some steps failed but we continued
            final_status = PipelineStatus.COMPLETED
        else:
            final_status = PipelineStatus.COMPLETED

        # Build final result text
        completed_steps = sum(1 for r in step_results if r.status == StepStatus.COMPLETED)
        failed_steps = sum(1 for r in step_results if r.status == StepStatus.FAILED)
        skipped_steps = sum(1 for r in step_results if r.status == StepStatus.SKIPPED)

        final_result = (
            f"Pipeline completed: {completed_steps} succeeded, "
            f"{failed_steps} failed, {skipped_steps} skipped"
        )

        return PipelineResult(
            pipeline_id=pipeline.pipeline_id,
            status=final_status,
            step_results=step_results,
            final_result=final_result,
            artifacts=all_artifacts,
            errors=errors,
            total_execution_time=total_execution_time,
            total_tokens_used=total_tokens_used,
            started_at=start_time,
            completed_at=end_time,
            metadata={
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "skipped_steps": skipped_steps,
                "total_steps": len(step_results),
            },
        )


class _ParallelSubStep(PipelineStep):
    """Internal wrapper for executing sub-steps within a PARALLEL step."""

    def __init__(self, config) -> None:
        super().__init__(config=config)

    async def execute(self, context: PipelineContext) -> StepResult:
        """Execute the sub-step by delegating based on step type."""
        return StepResult(
            step_id=self.step_id,
            status=StepStatus.COMPLETED,
            result=f"Sub-step {self.step_id} executed",
        )

    def can_execute(self, context: PipelineContext) -> bool:
        """Sub-steps within a parallel group are always executable."""
        return True


_executor_instance: Optional[PipelineExecutor] = None


def get_executor(
    framework: Optional["PalaceFramework"] = None,
) -> PipelineExecutor:
    """Get or create the global pipeline executor instance.

    Args:
        framework: Optional PalaceFramework reference for agent execution.
            Only used when creating a new instance.

    Returns:
        The global PipelineExecutor instance.
    """
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = PipelineExecutor(framework=framework)
    return _executor_instance
