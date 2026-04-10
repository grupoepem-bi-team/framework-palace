"""
Palace Framework - Pipeline de Revisión de Código

Este módulo implementa el pipeline completo para la revisión de código
dentro del framework Palace. Coordina múltiples agentes especializados
para cubrir todo el ciclo de revisión, desde el análisis inicial hasta
la generación del reporte final con mejoras sugeridas.

Flujo de trabajo:
    1. Análisis de código (Reviewer)
    2. Revisión de seguridad (Reviewer)
    3. Sugerencia de mejoras (Reviewer)
    4. Reporte final (Orchestrator)

El pipeline coordina múltiples agentes trabajando en conjunto para
entregar una revisión completa con hallazgos de seguridad y mejoras
concretas.

Clases:
    - CodeReviewPipeline: Pipeline completo de revisión de código.

Uso:
    from palace.pipelines.code_review import CodeReviewPipeline
    from palace.pipelines.types import PipelineConfig, PipelineType

    config = PipelineConfig(
        pipeline_id="review-001",
        name="Revisión de código de autenticación",
        pipeline_type=PipelineType.CODE_REVIEW,
        project_id="my-project",
    )

    pipeline = CodeReviewPipeline(config)
    context = pipeline.get_initial_context(
        task_description="Revisar el módulo de autenticación",
        project_id="my-project",
    )
"""

from typing import List

import structlog

from palace.pipelines.base import Pipeline, PipelineContext, PipelineStep
from palace.pipelines.feature_development import AgentStep
from palace.pipelines.types import PipelineConfig, PipelineType, StepConfig, StepType


class CodeReviewPipeline(Pipeline):
    """Pipeline for code review workflow.

    Implements the code review workflow:
    1. Analyze code (Reviewer)
    2. Security review (Reviewer)
    3. Suggest improvements (Reviewer)
    4. Final report (Orchestrator)

    The pipeline coordinates multiple review passes to deliver a
    comprehensive code review with security findings and concrete
    improvement suggestions.

    Each step uses template variables to reference outputs from
    previous steps (e.g., ``{analyze_code_output}``,
    ``{security_review_output}``). The executor is responsible for
    injecting these variables into the context after each step
    completes.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize the code review pipeline.

        Overrides the pipeline type to CODE_REVIEW regardless
        of the type specified in the configuration.

        Args:
            config: Pipeline configuration containing all settings.
        """
        config.pipeline_type = PipelineType.CODE_REVIEW
        super().__init__(config)

    def build_steps(self) -> List[PipelineStep]:
        """Build the pipeline steps for code review.

        Creates the four-step workflow that covers the full code
        review lifecycle:

        - **analyze_code**: Reviewer analyzes the code for potential
          issues, security vulnerabilities, and best practice violations.
        - **security_review**: Reviewer performs a focused security
          review based on the initial code analysis findings.
        - **suggest_improvements**: Reviewer suggests concrete
          improvements based on the code analysis and security findings.
        - **final_report**: Orchestrator compiles a final review
          report incorporating all analysis, security findings,
          and improvement suggestions.

        Template variables such as ``{analyze_code_output}`` and
        ``{security_review_output}`` are resolved at runtime from
        the pipeline context. The executor injects each step's output
        into ``context.variables`` as ``{step_id}_output`` upon
        completion.

        Returns:
            A list of AgentStep instances representing the full workflow.
        """
        steps: List[PipelineStep] = []

        # Step 1: Analyze code
        analyze_code_config = StepConfig(
            step_id="analyze_code",
            name="Analyze Code",
            step_type=StepType.AGENT_TASK,
            agent_role="reviewer",
            task_template=(
                "Analyze the following code for potential issues, "
                "security vulnerabilities, and best practice violations: "
                "{task_description}"
            ),
            depends_on=[],
        )
        steps.append(AgentStep(config=analyze_code_config, agent_role="reviewer"))

        # Step 2: Security review
        security_review_config = StepConfig(
            step_id="security_review",
            name="Security Review",
            step_type=StepType.AGENT_TASK,
            agent_role="reviewer",
            task_template=(
                "Perform a security review of: {task_description}. "
                "Consider the code analysis: {analyze_code_output}"
            ),
            depends_on=["analyze_code"],
        )
        steps.append(AgentStep(config=security_review_config, agent_role="reviewer"))

        # Step 3: Suggest improvements
        suggest_improvements_config = StepConfig(
            step_id="suggest_improvements",
            name="Suggest Improvements",
            step_type=StepType.AGENT_TASK,
            agent_role="reviewer",
            task_template=(
                "Suggest concrete improvements for: {task_description}. "
                "Analysis: {analyze_code_output}. "
                "Security findings: {security_review_output}"
            ),
            depends_on=["security_review"],
        )
        steps.append(AgentStep(config=suggest_improvements_config, agent_role="reviewer"))

        # Step 4: Final report
        final_report_config = StepConfig(
            step_id="final_report",
            name="Final Report",
            step_type=StepType.AGENT_TASK,
            agent_role="orchestrator",
            task_template=(
                "Compile a final review report for: {task_description}. "
                "Analysis: {analyze_code_output}. "
                "Security: {security_review_output}. "
                "Improvements: {suggest_improvements_output}"
            ),
            depends_on=["suggest_improvements"],
        )
        steps.append(AgentStep(config=final_report_config, agent_role="orchestrator"))

        self._steps = steps
        return steps

    def get_initial_context(self, task_description: str, project_id: str) -> PipelineContext:
        """Create the initial pipeline context for code review.

        Sets up the shared context with the task description as both
        a top-level field and a variable, so it can be referenced in
        step templates via ``{task_description}``.

        Args:
            task_description: Description of the code to review.
            project_id: Identifier of the project this review belongs to.

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
