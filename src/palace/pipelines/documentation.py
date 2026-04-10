"""
Palace Framework - Pipeline de Generación de Documentación

Este módulo implementa el pipeline completo para la generación de
documentación dentro del framework Palace. Coordina múltiples agentes
especializados para cubrir todo el ciclo de vida de la documentación,
desde el análisis del código hasta la revisión final de los documentos.

Flujo de trabajo:
    1. Análisis del código (Reviewer)
    2. Generación de documentación de API (Backend)
    3. Generación de documentación de usuario (Designer)
    4. Revisión y mejora de la documentación (Reviewer)

El pipeline coordina múltiples agentes trabajando en conjunto para
entregar documentación completa y de calidad para el proyecto.

Clases:
    - DocumentationPipeline: Pipeline completo de generación de documentación.

Uso:
    from palace.pipelines.documentation import DocumentationPipeline
    from palace.pipelines.types import PipelineConfig, PipelineType

    config = PipelineConfig(
        pipeline_id="docs-001",
        name="Generación de documentación",
        pipeline_type=PipelineType.DOCUMENTATION,
        project_id="my-project",
    )

    pipeline = DocumentationPipeline(config)
    context = pipeline.get_initial_context(
        task_description="Documentar la API de autenticación",
        project_id="my-project",
    )
"""

from typing import List

import structlog

from palace.pipelines.base import Pipeline, PipelineContext, PipelineStep
from palace.pipelines.feature_development import AgentStep
from palace.pipelines.types import PipelineConfig, PipelineType, StepConfig, StepType


class DocumentationPipeline(Pipeline):
    """Pipeline for documentation generation.

    Implements the complete documentation generation workflow:
    1. Analyze codebase (Reviewer)
    2. Generate API docs (Backend)
    3. Generate user docs (Designer)
    4. Review docs (Reviewer)

    The pipeline coordinates multiple agents working together to
    deliver comprehensive documentation covering both API reference
    and user-facing guides.

    Each step uses template variables to reference outputs from
    previous steps (e.g., ``{analyze_codebase_output}``,
    ``{generate_api_docs_output}``, ``{generate_user_docs_output}``).
    The executor is responsible for injecting these variables into
    the context after each step completes.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize the documentation pipeline.

        Overrides the pipeline type to DOCUMENTATION regardless
        of the type specified in the configuration.

        Args:
            config: Pipeline configuration containing all settings.
        """
        config.pipeline_type = PipelineType.DOCUMENTATION
        super().__init__(config)

    def build_steps(self) -> List[PipelineStep]:
        """Build the pipeline steps for documentation generation.

        Creates the four-step workflow that covers the full
        documentation generation lifecycle:

        - **analyze_codebase**: Reviewer analyzes the codebase and
          identifies areas that need documentation.
        - **generate_api_docs**: Backend developer generates API
          documentation based on the analysis output.
        - **generate_user_docs**: Designer generates user-facing
          documentation based on the API docs.
        - **review_docs**: Reviewer reviews and improves both the
          API docs and user docs for quality and completeness.

        Template variables such as ``{analyze_codebase_output}``,
        ``{generate_api_docs_output}``, and ``{generate_user_docs_output}``
        are resolved at runtime from the pipeline context. The executor
        injects each step's output into ``context.variables`` as
        ``{step_id}_output`` upon completion.

        Returns:
            A list of AgentStep instances representing the full workflow.
        """
        steps: List[PipelineStep] = []

        # Step 1: Analyze codebase
        analyze_codebase_config = StepConfig(
            step_id="analyze_codebase",
            name="Analyze Codebase",
            step_type=StepType.AGENT_TASK,
            agent_role="reviewer",
            task_template=(
                "Analyze the codebase and identify areas that need "
                "documentation: {task_description}"
            ),
            depends_on=[],
        )
        steps.append(AgentStep(config=analyze_codebase_config, agent_role="reviewer"))

        # Step 2: Generate API docs
        generate_api_docs_config = StepConfig(
            step_id="generate_api_docs",
            name="Generate API Documentation",
            step_type=StepType.AGENT_TASK,
            agent_role="backend",
            task_template=(
                "Generate API documentation for: {task_description}. "
                "Analysis: {analyze_codebase_output}"
            ),
            depends_on=["analyze_codebase"],
        )
        steps.append(AgentStep(config=generate_api_docs_config, agent_role="backend"))

        # Step 3: Generate user docs
        generate_user_docs_config = StepConfig(
            step_id="generate_user_docs",
            name="Generate User Documentation",
            step_type=StepType.AGENT_TASK,
            agent_role="designer",
            task_template=(
                "Generate user-facing documentation for: "
                "{task_description}. API docs: {generate_api_docs_output}"
            ),
            depends_on=["generate_api_docs"],
        )
        steps.append(AgentStep(config=generate_user_docs_config, agent_role="designer"))

        # Step 4: Review docs
        review_docs_config = StepConfig(
            step_id="review_docs",
            name="Review Documentation",
            step_type=StepType.AGENT_TASK,
            agent_role="reviewer",
            task_template=(
                "Review and improve the documentation for: "
                "{task_description}. API docs: {generate_api_docs_output}. "
                "User docs: {generate_user_docs_output}"
            ),
            depends_on=["generate_user_docs"],
        )
        steps.append(AgentStep(config=review_docs_config, agent_role="reviewer"))

        self._steps = steps
        return steps

    def get_initial_context(self, task_description: str, project_id: str) -> PipelineContext:
        """Create the initial pipeline context for documentation generation.

        Sets up the shared context with the task description as both
        a top-level field and a variable, so it can be referenced in
        step templates via ``{task_description}``.

        Args:
            task_description: Description of the documentation to generate.
            project_id: Identifier of the project to document.

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
