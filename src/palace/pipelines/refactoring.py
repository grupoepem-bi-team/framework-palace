"""
Palace Framework - Pipeline de Refactorización de Código

Este módulo implementa el pipeline completo para la refactorización
de código dentro del framework Palace. Coordina múltiples agentes
especializados para cubrir todo el ciclo de vida de la refactorización,
desde el análisis del código existente hasta la revisión final.

Flujo de trabajo:
    1. Análisis de código (Reviewer)
    2. Planificación de refactorización (Orchestrator)
    3. Implementación de refactorización (Backend)
    4. Pruebas de refactorización (QA)
    5. Revisión final (Reviewer)

El pipeline coordina múltiples agentes trabajando en conjunto para
entregar código refactorizado que preserve el comportamiento original,
con pruebas que validen la integridad y una revisión final de calidad.

Clases:
    - RefactoringPipeline: Pipeline completo de refactorización de código.

Uso:
    from palace.pipelines.refactoring import RefactoringPipeline
    from palace.pipelines.types import PipelineConfig, PipelineType

    config = PipelineConfig(
        pipeline_id="refactor-001",
        name="Refactorización de módulo de pagos",
        pipeline_type=PipelineType.REFACTORING,
        project_id="my-project",
    )

    pipeline = RefactoringPipeline(config)
    context = pipeline.get_initial_context(
        task_description="Refactorizar el módulo de procesamiento de pagos",
        project_id="my-project",
    )
"""

from typing import List

import structlog

from palace.pipelines.base import Pipeline, PipelineContext, PipelineStep
from palace.pipelines.feature_development import AgentStep
from palace.pipelines.types import PipelineConfig, PipelineType, StepConfig, StepType


class RefactoringPipeline(Pipeline):
    """Pipeline for code refactoring workflow.

    Implements the complete code refactoring workflow:
    1. Analyze code (Reviewer)
    2. Plan refactoring (Orchestrator)
    3. Implement refactoring (Backend)
    4. Test refactoring (QA)
    5. Final review (Reviewer)

    The pipeline coordinates multiple agents working together to
    deliver refactored code that preserves the original behavior,
    with comprehensive testing and a final quality review.

    Each step uses template variables to reference outputs from
    previous steps (e.g., ``{analyze_code_output}``,
    ``{plan_refactoring_output}``). The executor is responsible
    for injecting these variables into the context after each
    step completes.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize the refactoring pipeline.

        Overrides the pipeline type to REFACTORING regardless
        of the type specified in the configuration.

        Args:
            config: Pipeline configuration containing all settings.
        """
        config.pipeline_type = PipelineType.REFACTORING
        super().__init__(config)

    def build_steps(self) -> List[PipelineStep]:
        """Build the pipeline steps for code refactoring.

        Creates the five-step workflow that covers the full code
        refactoring lifecycle:

        - **analyze_code**: Reviewer analyzes the existing code to
          identify code smells, duplications, and improvement
          opportunities.
        - **plan_refactoring**: Orchestrator creates a structured
          refactoring plan based on the code analysis, prioritizing
          changes and defining safe transformation steps.
        - **implement_refactoring**: Backend developer implements
          the refactoring changes according to the plan, ensuring
          incremental and safe modifications.
        - **test_refactoring**: QA engineer tests the refactored code
          to ensure that the original behavior is preserved and no
          regressions are introduced.
        - **final_review**: Reviewer performs a final quality review
          of the refactored code, including the test results, to
          confirm that the refactoring goals were achieved.

        Template variables such as ``{analyze_code_output}``,
        ``{plan_refactoring_output}``, ``{implement_refactoring_output}``,
        and ``{test_refactoring_output}`` are resolved at runtime from
        the pipeline context. The executor injects each step's output
        into ``context.variables`` as ``{step_id}_output`` upon
        completion.

        Returns:
            A list of AgentStep instances representing the full workflow.
        """
        steps: List[PipelineStep] = []

        # Step 1: Analyze code
        analyze_config = StepConfig(
            step_id="analyze_code",
            name="Analyze Code",
            step_type=StepType.AGENT_TASK,
            agent_role="reviewer",
            task_template=(
                "Analyze the code that needs refactoring: "
                "{task_description}. Identify code smells, duplications, "
                "and improvement opportunities."
            ),
            depends_on=[],
        )
        steps.append(AgentStep(config=analyze_config, agent_role="reviewer"))

        # Step 2: Plan refactoring
        plan_config = StepConfig(
            step_id="plan_refactoring",
            name="Plan Refactoring",
            step_type=StepType.AGENT_TASK,
            agent_role="orchestrator",
            task_template=(
                "Create a refactoring plan for: "
                "{task_description}. Code analysis: {analyze_code_output}"
            ),
            depends_on=["analyze_code"],
        )
        steps.append(AgentStep(config=plan_config, agent_role="orchestrator"))

        # Step 3: Implement refactoring
        implement_config = StepConfig(
            step_id="implement_refactoring",
            name="Implement Refactoring",
            step_type=StepType.AGENT_TASK,
            agent_role="backend",
            task_template=(
                "Implement the refactoring for: "
                "{task_description}. Refactoring plan: {plan_refactoring_output}"
            ),
            depends_on=["plan_refactoring"],
        )
        steps.append(AgentStep(config=implement_config, agent_role="backend"))

        # Step 4: Test refactoring
        test_config = StepConfig(
            step_id="test_refactoring",
            name="Test Refactoring",
            step_type=StepType.AGENT_TASK,
            agent_role="qa",
            task_template=(
                "Test the refactored code to ensure behavior is preserved: "
                "{task_description}. Refactored code: {implement_refactoring_output}"
            ),
            depends_on=["implement_refactoring"],
        )
        steps.append(AgentStep(config=test_config, agent_role="qa"))

        # Step 5: Final review
        review_config = StepConfig(
            step_id="final_review",
            name="Final Review",
            step_type=StepType.AGENT_TASK,
            agent_role="reviewer",
            task_template=(
                "Final review of the refactoring: "
                "{task_description}. Test results: {test_refactoring_output}"
            ),
            depends_on=["test_refactoring"],
        )
        steps.append(AgentStep(config=review_config, agent_role="reviewer"))

        self._steps = steps
        return steps

    def get_initial_context(self, task_description: str, project_id: str) -> PipelineContext:
        """Create the initial pipeline context for code refactoring.

        Sets up the shared context with the task description as both
        a top-level field and a variable, so it can be referenced in
        step templates via ``{task_description}``.

        Args:
            task_description: Description of the code to refactor.
            project_id: Identifier of the project this refactoring belongs to.

        Returns:
            A PipelineContext ready for pipeline execution.
        """
        return PipelineContext(
            pipeline_id=self.pipeline_id,
            project_id=project_id,
            task_description=task_description,
            variables={"task_description": task_description},
            config=self.config,
        )
