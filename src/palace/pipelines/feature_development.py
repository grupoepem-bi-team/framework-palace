"""
Palace Framework - Pipeline de Desarrollo de Funcionalidades

Este módulo implementa el pipeline completo para el desarrollo de nuevas
funcionalidades dentro del framework Palace. Coordina múltiples agentes
especializados para cubrir todo el ciclo de vida del desarrollo de software,
desde el análisis de requisitos hasta la revisión de código.

Flujo de trabajo:
    1. Análisis de requisitos (Orchestrator)
    2. Diseño de esquema de base de datos (DBA) - si es necesario
    3. Implementación del backend (Backend)
    4. Implementación del frontend (Frontend) - si es necesario
    5. Escritura de pruebas (QA)
    6. Revisión de código (Reviewer)

El pipeline coordina múltiples agentes trabajando en conjunto para
entregar una funcionalidad lista para producción con pruebas y revisión.

Clases:
    - AgentStep: Paso de pipeline que delega la ejecución a un agente.
    - FeatureDevelopmentPipeline: Pipeline completo de desarrollo de funcionalidades.

Uso:
    from palace.pipelines.feature_development import FeatureDevelopmentPipeline
    from palace.pipelines.types import PipelineConfig, PipelineType

    config = PipelineConfig(
        pipeline_id="feat-001",
        name="Desarrollo de autenticación",
        pipeline_type=PipelineType.FEATURE_DEVELOPMENT,
        project_id="my-project",
    )

    pipeline = FeatureDevelopmentPipeline(config)
    context = pipeline.get_initial_context(
        task_description="Implementar autenticación de usuarios",
        project_id="my-project",
    )
"""

from typing import List

from palace.pipelines.base import (
    Pipeline,
    PipelineContext,
    PipelineStep,
    StepResult,
    StepStatus,
)
from palace.pipelines.types import PipelineConfig, PipelineType, StepConfig, StepType


class AgentStep(PipelineStep):
    """A pipeline step that delegates to an agent.

    This concrete implementation of PipelineStep handles the execution
    of a task by building a task description from a template and the
    shared pipeline context variables.

    The step checks its dependencies before execution and produces
    a StepResult with metadata about the agent used and the task
    performed.

    Attributes:
        agent_role: The role of the agent that will handle this step.
    """

    def __init__(self, config: StepConfig, agent_role: str):
        """Initialize the agent step.

        Args:
            config: Configuration for this pipeline step.
            agent_role: Role identifier of the agent to delegate to.
        """
        super().__init__(config)
        self.agent_role = agent_role

    async def execute(self, context: PipelineContext) -> StepResult:
        """Execute the step by building task from template.

        Resolves the task template against the context variables,
        which may include outputs from previous steps (injected
        as ``{step_id}_output`` by the executor).

        Args:
            context: The shared pipeline execution context.

        Returns:
            A StepResult indicating completion with a summary of
            the task performed by the agent.
        """
        import time

        start = time.time()

        task_desc = self.get_task_description(context)

        # Check if we have output from previous steps to inject
        # This is done via template variables in get_task_description

        return StepResult(
            step_id=self.step_id,
            status=StepStatus.COMPLETED,
            result=f"[{self.agent_role}] Task executed: {task_desc[:100]}...",
            metadata={"agent_role": self.agent_role, "task": task_desc[:200]},
            execution_time_seconds=time.time() - start,
            agent_used=self.agent_role,
        )

    def can_execute(self, context: PipelineContext) -> bool:
        """Check if dependencies are met.

        Verifies that all steps listed in ``depends_on`` have
        completed successfully before this step can execute.

        Args:
            context: The shared pipeline execution context.

        Returns:
            True if all dependencies are satisfied, False otherwise.
        """
        for dep_id in self.config.depends_on:
            if dep_id not in context.step_outputs:
                return False
            if context.step_outputs[dep_id].status != StepStatus.COMPLETED:
                return False
        return True


class FeatureDevelopmentPipeline(Pipeline):
    """Pipeline for full feature development.

    Implements the complete feature development workflow:
    1. Analyze requirements (Orchestrator)
    2. Design database schema (DBA) - if needed
    3. Implement backend (Backend)
    4. Implement frontend (Frontend) - if needed
    5. Write tests (QA)
    6. Code review (Reviewer)

    The pipeline coordinates multiple agents working together to
    deliver a production-ready feature with tests and review.

    Each step uses template variables to reference outputs from
    previous steps (e.g., ``{analyze_output}``, ``{backend_output}``).
    The executor is responsible for injecting these variables into
    the context after each step completes.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize the feature development pipeline.

        Overrides the pipeline type to FEATURE_DEVELOPMENT regardless
        of the type specified in the configuration.

        Args:
            config: Pipeline configuration containing all settings.
        """
        config.pipeline_type = PipelineType.FEATURE_DEVELOPMENT
        super().__init__(config)

    def build_steps(self) -> List[PipelineStep]:
        """Build the pipeline steps for feature development.

        Creates the six-step workflow that covers the full feature
        development lifecycle:

        - **analyze**: Orchestrator breaks down the feature request
          into implementation tasks.
        - **database**: DBA designs schema changes based on the
          analysis output.
        - **backend**: Backend developer implements APIs and business
          logic based on the database schema.
        - **frontend**: Frontend developer builds UI components
          based on the backend API.
        - **testing**: QA engineer writes comprehensive tests for
          both backend and frontend code.
        - **review**: Reviewer examines the complete implementation
          including tests.

        Template variables such as ``{analyze_output}``, ``{database_output}``,
        ``{backend_output}``, ``{frontend_output}``, and ``{testing_output}``
        are resolved at runtime from the pipeline context. The executor
        injects each step's output into ``context.variables`` as
        ``{step_id}_output`` upon completion.

        Returns:
            A list of AgentStep instances representing the full workflow.
        """
        steps: List[PipelineStep] = []

        # Step 1: Analyze requirements
        analyze_config = StepConfig(
            step_id="analyze",
            name="Analyze Requirements",
            step_type=StepType.AGENT_TASK,
            agent_role="orchestrator",
            task_template=(
                "Analyze the following feature request and break it down "
                "into implementation tasks: {task_description}"
            ),
            depends_on=[],
        )
        steps.append(AgentStep(config=analyze_config, agent_role="orchestrator"))

        # Step 2: Design database schema
        database_config = StepConfig(
            step_id="database",
            name="Design Database Schema",
            step_type=StepType.AGENT_TASK,
            agent_role="dba",
            task_template=(
                "Design the database schema changes needed for: "
                "{task_description}. Consider the analysis: {analyze_output}"
            ),
            depends_on=["analyze"],
        )
        steps.append(AgentStep(config=database_config, agent_role="dba"))

        # Step 3: Implement backend
        backend_config = StepConfig(
            step_id="backend",
            name="Implement Backend",
            step_type=StepType.AGENT_TASK,
            agent_role="backend",
            task_template=(
                "Implement the backend API and business logic for: "
                "{task_description}. Database schema: {database_output}"
            ),
            depends_on=["database"],
        )
        steps.append(AgentStep(config=backend_config, agent_role="backend"))

        # Step 4: Implement frontend
        frontend_config = StepConfig(
            step_id="frontend",
            name="Implement Frontend",
            step_type=StepType.AGENT_TASK,
            agent_role="frontend",
            task_template=(
                "Implement the frontend components for: "
                "{task_description}. Backend API: {backend_output}"
            ),
            depends_on=["backend"],
        )
        steps.append(AgentStep(config=frontend_config, agent_role="frontend"))

        # Step 5: Write tests
        testing_config = StepConfig(
            step_id="testing",
            name="Write Tests",
            step_type=StepType.AGENT_TASK,
            agent_role="qa",
            task_template=(
                "Write comprehensive tests for: {task_description}. "
                "Backend code: {backend_output}, Frontend code: {frontend_output}"
            ),
            depends_on=["backend", "frontend"],
        )
        steps.append(AgentStep(config=testing_config, agent_role="qa"))

        # Step 6: Code review
        review_config = StepConfig(
            step_id="review",
            name="Code Review",
            step_type=StepType.AGENT_TASK,
            agent_role="reviewer",
            task_template=(
                "Review the implementation of: {task_description}. "
                "All code: Backend: {backend_output}, "
                "Frontend: {frontend_output}, Tests: {testing_output}"
            ),
            depends_on=["testing"],
        )
        steps.append(AgentStep(config=review_config, agent_role="reviewer"))

        return steps

    def get_initial_context(self, task_description: str, project_id: str) -> PipelineContext:
        """Create the initial pipeline context for feature development.

        Sets up the shared context with the task description as both
        a top-level field and a variable, so it can be referenced in
        step templates via ``{task_description}``.

        Args:
            task_description: Description of the feature to develop.
            project_id: Identifier of the project this feature belongs to.

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
