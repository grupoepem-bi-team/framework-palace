"""
Palace Framework - Pipeline de Migración de Base de Datos

Este módulo implementa el pipeline completo para la migración de bases de datos
dentro del framework Palace. Coordina múltiples agentes especializados para
cubrir todo el ciclo de vida de una migración, desde el análisis del esquema
actual hasta la verificación de integridad de datos post-migración.

Flujo de trabajo:
    1. Análisis de esquema (DBA)
    2. Diseño de migración (DBA)
    3. Revisión de migración (Reviewer)
    4. Ejecución de migración (DBA)
    5. Verificación de migración (QA)

El pipeline coordina múltiples agentes trabajando en conjunto para
entregar una migración segura con revisión y verificación de integridad.

Clases:
    - DatabaseMigrationPipeline: Pipeline completo de migración de base de datos.

Uso:
    from palace.pipelines.database_migration import DatabaseMigrationPipeline
    from palace.pipelines.types import PipelineConfig, PipelineType

    config = PipelineConfig(
        pipeline_id="mig-001",
        name="Migración de esquema de usuarios",
        pipeline_type=PipelineType.DATABASE_MIGRATION,
        project_id="my-project",
    )

    pipeline = DatabaseMigrationPipeline(config)
    context = pipeline.get_initial_context(
        task_description="Agregar columna de fecha de nacimiento a tabla usuarios",
        project_id="my-project",
    )
"""

from typing import List

import structlog

from palace.pipelines.base import Pipeline, PipelineContext, PipelineStep
from palace.pipelines.feature_development import AgentStep
from palace.pipelines.types import PipelineConfig, PipelineType, StepConfig, StepType


class DatabaseMigrationPipeline(Pipeline):
    """Pipeline for database migration workflow.

    Implements the database migration workflow:
    1. Analyze Schema (DBA)
    2. Design Migration (DBA)
    3. Review Migration (Reviewer)
    4. Execute Migration (DBA)
    5. Verify Migration (QA)

    The pipeline coordinates multiple agents working together to
    deliver a safe migration with review and data integrity verification.

    Each step uses template variables to reference outputs from
    previous steps (e.g., ``{analyze_schema_output}``, ``{design_migration_output}``).
    The executor is responsible for injecting these variables into
    the context after each step completes.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize the database migration pipeline.

        Overrides the pipeline type to DATABASE_MIGRATION regardless
        of the type specified in the configuration.

        Args:
            config: Pipeline configuration containing all settings.
        """
        config.pipeline_type = PipelineType.DATABASE_MIGRATION
        super().__init__(config)

    def build_steps(self) -> List[PipelineStep]:
        """Build the pipeline steps for database migration.

        Creates the five-step workflow that covers the full database
        migration lifecycle:

        - **analyze_schema**: DBA analyzes the current database schema
          and plans the migration approach.
        - **design_migration**: DBA designs the migration script based
          on the schema analysis output.
        - **review_migration**: Reviewer examines the migration script
          for safety and correctness before execution.
        - **execute_migration**: DBA executes the reviewed migration
          script against the database.
        - **verify_migration**: QA verifies the migration was successful
          and that data integrity is maintained.

        Template variables such as ``{analyze_schema_output}``,
        ``{design_migration_output}``, ``{review_migration_output}``,
        and ``{execute_migration_output}`` are resolved at runtime
        from the pipeline context. The executor injects each step's
        output into ``context.variables`` as ``{step_id}_output``
        upon completion.

        Returns:
            A list of AgentStep instances representing the full workflow.
        """
        steps: List[PipelineStep] = []

        # Step 1: Analyze current database schema
        analyze_schema_config = StepConfig(
            step_id="analyze_schema",
            name="Analyze Schema",
            step_type=StepType.AGENT_TASK,
            agent_role="dba",
            task_template=(
                "Analyze the current database schema and plan migration for: {task_description}"
            ),
            depends_on=[],
        )
        steps.append(AgentStep(config=analyze_schema_config, agent_role="dba"))

        # Step 2: Design the migration script
        design_migration_config = StepConfig(
            step_id="design_migration",
            name="Design Migration",
            step_type=StepType.AGENT_TASK,
            agent_role="dba",
            task_template=(
                "Design the database migration script for: "
                "{task_description}. Current schema analysis: {analyze_schema_output}"
            ),
            depends_on=["analyze_schema"],
        )
        steps.append(AgentStep(config=design_migration_config, agent_role="dba"))

        # Step 3: Review the migration script
        review_migration_config = StepConfig(
            step_id="review_migration",
            name="Review Migration",
            step_type=StepType.AGENT_TASK,
            agent_role="reviewer",
            task_template=(
                "Review the migration script for safety and correctness: "
                "{task_description}. Migration design: {design_migration_output}"
            ),
            depends_on=["design_migration"],
        )
        steps.append(AgentStep(config=review_migration_config, agent_role="reviewer"))

        # Step 4: Execute the migration
        execute_migration_config = StepConfig(
            step_id="execute_migration",
            name="Execute Migration",
            step_type=StepType.AGENT_TASK,
            agent_role="dba",
            task_template=(
                "Execute the database migration: "
                "{task_description}. Reviewed migration: {review_migration_output}"
            ),
            depends_on=["review_migration"],
        )
        steps.append(AgentStep(config=execute_migration_config, agent_role="dba"))

        # Step 5: Verify the migration
        verify_migration_config = StepConfig(
            step_id="verify_migration",
            name="Verify Migration",
            step_type=StepType.AGENT_TASK,
            agent_role="qa",
            task_template=(
                "Verify the migration was successful and data integrity is maintained: "
                "{task_description}. Migration results: {execute_migration_output}"
            ),
            depends_on=["execute_migration"],
        )
        steps.append(AgentStep(config=verify_migration_config, agent_role="qa"))

        self._steps = steps
        return steps

    def get_initial_context(self, task_description: str, project_id: str) -> PipelineContext:
        """Create the initial pipeline context for database migration.

        Sets up the shared context with the task description as both
        a top-level field and a variable, so it can be referenced in
        step templates via ``{task_description}``.

        Args:
            task_description: Description of the database migration to perform.
            project_id: Identifier of the project this migration belongs to.

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
