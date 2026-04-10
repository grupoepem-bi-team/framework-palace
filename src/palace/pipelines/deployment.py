"""
Palace Framework - Pipeline de Despliegue

Este módulo implementa el pipeline completo para el despliegue
de aplicaciones dentro del framework Palace. Coordina múltiples agentes
especializados para cubrir todo el ciclo de vida del despliegue,
desde las verificaciones previas hasta la configuración de monitoreo.

Flujo de trabajo:
    1. Verificación pre-despliegue (DevOps)
    2. Construcción y pruebas (DevOps)
    3. Despliegue de la aplicación (DevOps)
    4. Verificación post-despliegue (QA)
    5. Configuración de monitoreo (DevOps)

El pipeline coordina múltiples agentes trabajando en conjunto para
entregar un despliegue seguro, verificado y monitoreado.

Clases:
    - DeploymentPipeline: Pipeline completo de despliegue de aplicaciones.

Uso:
    from palace.pipelines.deployment import DeploymentPipeline
    from palace.pipelines.types import PipelineConfig, PipelineType

    config = PipelineConfig(
        pipeline_id="deploy-001",
        name="Despliegue de aplicación",
        pipeline_type=PipelineType.DEPLOYMENT,
        project_id="my-project",
    )

    pipeline = DeploymentPipeline(config)
    context = pipeline.get_initial_context(
        task_description="Desplegar servicio de autenticación a producción",
        project_id="my-project",
    )
"""

from typing import List

import structlog

from palace.pipelines.base import Pipeline, PipelineContext, PipelineStep
from palace.pipelines.feature_development import AgentStep
from palace.pipelines.types import PipelineConfig, PipelineType, StepConfig, StepType


class DeploymentPipeline(Pipeline):
    """Pipeline for deployment workflow.

    Implements the complete deployment workflow:
    1. Pre-deploy check (DevOps)
    2. Build and test (DevOps)
    3. Deploy application (DevOps)
    4. Post-deploy verification (QA)
    5. Monitor setup (DevOps)

    The pipeline coordinates multiple agents working together to
    deliver a safe, verified, and monitored deployment.

    Each step uses template variables to reference outputs from
    previous steps (e.g., ``{pre_deploy_check_output}``,
    ``{build_and_test_output}``). The executor is responsible for
    injecting these variables into the context after each step completes.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize the deployment pipeline.

        Overrides the pipeline type to DEPLOYMENT regardless
        of the type specified in the configuration.

        Args:
            config: Pipeline configuration containing all settings.
        """
        config.pipeline_type = PipelineType.DEPLOYMENT
        super().__init__(config)

    def build_steps(self) -> List[PipelineStep]:
        """Build the pipeline steps for deployment.

        Creates the five-step workflow that covers the full deployment
        lifecycle:

        - **pre_deploy_check**: DevOps performs pre-deployment checks
          including configurations, environment variables, and dependencies.
        - **build_and_test**: DevOps builds and runs tests based on the
          pre-deployment check results.
        - **deploy**: DevOps deploys the application using the build results.
        - **post_deploy_verify**: QA verifies the deployment was successful
          using the deployment information.
        - **monitor**: DevOps sets up monitoring and alerts based on the
          verified deployment.

        Template variables such as ``{pre_deploy_check_output}``,
        ``{build_and_test_output}``, ``{deploy_output}``, and
        ``{post_deploy_verify_output}`` are resolved at runtime from
        the pipeline context. The executor injects each step's output
        into ``context.variables`` as ``{step_id}_output`` upon completion.

        Returns:
            A list of AgentStep instances representing the full workflow.
        """
        steps: List[PipelineStep] = []

        # Step 1: Pre-deploy check
        pre_deploy_check_config = StepConfig(
            step_id="pre_deploy_check",
            name="Pre-Deploy Check",
            step_type=StepType.AGENT_TASK,
            agent_role="devops",
            task_template=(
                "Perform pre-deployment checks for: {task_description}. "
                "Verify configurations, environment variables, and dependencies."
            ),
            depends_on=[],
        )
        steps.append(AgentStep(config=pre_deploy_check_config, agent_role="devops"))

        # Step 2: Build and test
        build_and_test_config = StepConfig(
            step_id="build_and_test",
            name="Build and Test",
            step_type=StepType.AGENT_TASK,
            agent_role="devops",
            task_template=(
                "Build and run tests for deployment of: {task_description}. "
                "Pre-deploy check results: {pre_deploy_check_output}"
            ),
            depends_on=["pre_deploy_check"],
        )
        steps.append(AgentStep(config=build_and_test_config, agent_role="devops"))

        # Step 3: Deploy
        deploy_config = StepConfig(
            step_id="deploy",
            name="Deploy",
            step_type=StepType.AGENT_TASK,
            agent_role="devops",
            task_template=(
                "Deploy the application: {task_description}. Build results: {build_and_test_output}"
            ),
            depends_on=["build_and_test"],
        )
        steps.append(AgentStep(config=deploy_config, agent_role="devops"))

        # Step 4: Post-deploy verification
        post_deploy_verify_config = StepConfig(
            step_id="post_deploy_verify",
            name="Post-Deploy Verification",
            step_type=StepType.AGENT_TASK,
            agent_role="qa",
            task_template=(
                "Verify the deployment was successful for: {task_description}. "
                "Deployment info: {deploy_output}"
            ),
            depends_on=["deploy"],
        )
        steps.append(AgentStep(config=post_deploy_verify_config, agent_role="qa"))

        # Step 5: Monitor
        monitor_config = StepConfig(
            step_id="monitor",
            name="Monitor",
            step_type=StepType.AGENT_TASK,
            agent_role="devops",
            task_template=(
                "Set up monitoring and alerts for: {task_description}. "
                "Deployment verified: {post_deploy_verify_output}"
            ),
            depends_on=["post_deploy_verify"],
        )
        steps.append(AgentStep(config=monitor_config, agent_role="devops"))

        self._steps = steps
        return steps

    def get_initial_context(self, task_description: str, project_id: str) -> PipelineContext:
        """Create the initial pipeline context for deployment.

        Sets up the shared context with the task description as both
        a top-level field and a variable, so it can be referenced in
        step templates via ``{task_description}``.

        Args:
            task_description: Description of the deployment task.
            project_id: Identifier of the project being deployed.

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
