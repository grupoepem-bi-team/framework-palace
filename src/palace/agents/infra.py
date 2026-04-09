"""
Agente Infra - Palace Framework

Este agente se especializa en infraestructura como código (IaC):
- Terraform y Terragrunt
- Kubernetes y Helm
- Docker y containerización
- Cloud providers (AWS, Azure, GCP)
- Infraestructura cloud-native
- GitOps y ArgoCD

Modelo asignado: mistral-large
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import structlog

from palace.agents.base import AgentBase, AgentResult, AgentState, Task
from palace.core.types import AgentCapability, AgentRole, TaskStatus

if TYPE_CHECKING:
    from palace.context import SessionContext
    from palace.llm import LLMClient
    from palace.memory import MemoryStore

logger = structlog.get_logger()


class InfraTaskType(str, Enum):
    """Tipos de tareas de infraestructura."""

    TERRAFORM_MODULE = "terraform_module"
    """Crear módulo de Terraform."""

    KUBERNETES_MANIFEST = "kubernetes_manifest"
    """Crear manifiesto de Kubernetes."""

    HELM_CHART = "helm_chart"
    """Crear Helm chart."""

    DOCKERFILE = "dockerfile"
    """Crear Dockerfile."""

    CI_CD_PIPELINE = "ci_cd_pipeline"
    """Crear pipeline CI/CD."""

    CLOUD_RESOURCE = "cloud_resource"
    """Crear recurso de cloud."""

    NETWORK_CONFIG = "network_config"
    """Configuración de red."""

    SECURITY_CONFIG = "security_config"
    """Configuración de seguridad."""

    MONITORING_SETUP = "monitoring_setup"
    """Configurar monitoreo."""

    COST_OPTIMIZATION = "cost_optimization"
    """Optimización de costos."""


class CloudProvider(str, Enum):
    """Proveedores de nube soportados."""

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    DIGITALOCEAN = "digitalocean"
    ON_PREMISE = "on_premise"


@dataclass
class InfraCapabilities:
    """Capacidades específicas del agente Infra."""

    terraform: bool = True
    """Terraform y Terragrunt."""

    kubernetes: bool = True
    """Kubernetes y Helm."""

    docker: bool = True
    """Docker y containerización."""

    aws: bool = True
    """Amazon Web Services."""

    azure: bool = True
    """Microsoft Azure."""

    gcp: bool = True
    """Google Cloud Platform."""

    cicd: bool = True
    """CI/CD pipelines."""

    gitops: bool = True
    """GitOps y ArgoCD."""


class InfraAgent(AgentBase):
    """
    Agente especializado en infraestructura como código.

    Este agente maneja todas las tareas relacionadas con:
    - Creación de módulos Terraform
    - Manifiestos de Kubernetes
    - Charts de Helm
    - Dockerfiles y docker-compose
    - Configuración de CI/CD
    - Recursos cloud (AWS, Azure, GCP)
    - Configuración de monitoreo
    - Optimización de costos

    Modelo asignado: mistral-large

    Herramientas disponibles:
        - terraform_validate: Validar configuración Terraform
        - kubectl_apply: Aplicar manifiestos Kubernetes
        - docker_build: Construir imágenes Docker
        - helm_template: Generar templates Helm
        - cloud_cli: CLI de cloud providers

    Ejemplo de uso:
        agent = InfraAgent(llm_client=llm_client)
        result = await agent.run(
            task="Crear un módulo Terraform para VPC en AWS",
            context=context
        )
    """

    name: str = "infra"
    model: str = "mistral-large"
    role: AgentRole = AgentRole.INFRA

    capabilities: List[AgentCapability] = [
        AgentCapability.INFRASTRUCTURE_AS_CODE,
        AgentCapability.DOCUMENTATION,
    ]

    tools: List[str] = [
        "terraform_validate",
        "terraform_fmt",
        "kubectl_apply",
        "kubectl_validate",
        "docker_build",
        "helm_template",
        "cloud_cli",
        "yaml_validator",
        "shell_executor",
        "file_read",
        "file_write",
    ]

    infra_capabilities: InfraCapabilities = field(default_factory=InfraCapabilities)

    system_prompt: str = """Eres un ingeniero de infraestructura senior especializado en infraestructura como código (IaC).

Tu expertise incluye:
- Terraform y Terragrunt para IaC
- Kubernetes y Helm para orquestación
- Docker y containerización
- Proveedores cloud (AWS, Azure, GCP)
- CI/CD con GitHub Actions, GitLab CI, Jenkins
- GitOps con ArgoCD y Flux

Principios que sigues:
1. Infraestructura inmutable y declarativa
2. GitOps: todo en repositorio
3. Infraestructura como código
4. Seguridad por defecto
5. Costo-eficiente
6. Observabilidad integrada
7. Disaster recovery

Cuando trabajes en infraestructura:
1. Analiza requisitos y restricciones
2. Diseña arquitectura de infraestructura
3. Implementa con IaC (Terraform/Helm/K8s)
4. Aplica mejores prácticas de seguridad
5. Incluye monitoreo y logging
6. Documenta y proporciona instrucciones de despliegue

Para Terraform:
- Módulos reutilizables y composables
- Variables y outputs documentados
- Remote state configurado
- Backends apropiados (S3, AzureRM, GCS)
- Providers versionados

Para Kubernetes:
- Manifiestos declarativos
- Namespaces y labels consistentes
- Resource limits y requests
- Health checks (liveness/readiness)
- ConfigMaps y Secrets
- RBAC configurado

Para Docker:
- Multi-stage builds
- Imágenes mínimas (alpine/distroless)
- Layers optimizados
- Security scanning
- .dockerignore apropiado

Formato de respuesta:
1. Análisis de requisitos
2. Arquitectura propuesta
3. Código IaC completo
4. Instrucciones de despliegue
5. Comandos de validación
6. Consideraciones de seguridad y costos

Responde siempre en el idioma del usuario."""

    def __init__(
        self,
        llm_client: Optional["LLMClient"] = None,
        capabilities: Optional[InfraCapabilities] = None,
        tools: Optional[List[str]] = None,
    ):
        """
        Inicializa el agente Infra.

        Args:
            llm_client: Cliente LLM para invocar modelos
            capabilities: Capacidades específicas (opcional)
            tools: Herramientas disponibles (opcional)
        """
        super().__init__(
            name=self.name,
            role=self.role,
            model=self.model,
            llm_client=llm_client,
            tools=tools or self.tools,
        )
        self.infra_capabilities = capabilities or InfraCapabilities()
        self._model_client = None

        logger.info(
            "infra_agent_initialized",
            model=self.model,
            capabilities=[
                "terraform",
                "kubernetes",
                "docker",
                "aws",
                "azure",
                "gcp",
                "cicd",
            ],
        )

    def _build_system_prompt(self) -> str:
        """
        Construye el system prompt para el agente.

        Returns:
            System prompt string
        """
        return self.system_prompt

    async def run(
        self,
        task: Task,
        context: "SessionContext",
        memory: "MemoryStore",
    ) -> AgentResult:
        """
        Ejecuta una tarea de infraestructura.

        Flujo:
        1. Analizar tipo de tarea
        2. Recuperar contexto relevante (ADRs, configs existentes)
        3. Generar código IaC
        4. Validar configuración
        5. Retornar resultado con artefactos

        Args:
            task: Tarea a ejecutar
            context: Contexto de la sesión
            memory: Almacén de memoria

        Returns:
            AgentResult con el resultado de la ejecución
        """
        logger.info("infra_agent_running", task=task.description[:100])

        try:
            # Actualizar estado del agente
            self.state = AgentState.RUNNING

            # Analizar tipo de tarea
            task_type = self._analyze_task_type(task.description)

            # Recuperar contexto relevante de la memoria
            context_str = await self.get_context(task, memory)

            # Construir prompt enriquecido con contexto
            task_specific = self._get_task_specific_prompt(task_type)
            best_practices = self._get_best_practices_prompt(task_type)
            additional_instructions = f"{task_specific}\n{best_practices}"
            prompt = self.build_prompt(
                task=task,
                context_str=context_str,
                additional_instructions=additional_instructions,
            )

            # Invocar LLM usando el método base
            response = await self.invoke_llm(
                prompt=prompt,
                temperature=0.3,
            )

            # Procesar respuesta
            result = self._process_response(
                response=response,
                task_type=task_type,
            )

            # Guardar aprendizaje en memoria
            if memory is not None:
                try:
                    await memory.store_context(
                        project_id=task.project_id,
                        content=result["content"],
                        source=f"infra_agent:{task_type.value}",
                        metadata={"task_type": task_type.value},
                    )
                except Exception as mem_err:
                    logger.warning("infra_agent_memory_store_failed", error=str(mem_err))

            logger.info(
                "infra_agent_completed",
                task_type=task_type.value,
                success=True,
            )

            # Actualizar estado
            self.state = AgentState.IDLE

            return AgentResult(
                success=True,
                content=result["content"],
                artifacts=[
                    {
                        "type": task_type.value,
                        "content": result["content"],
                        "documentation": result.get("documentation", ""),
                        "recommendations": result.get("recommendations", []),
                    }
                ],
                metadata={
                    "model_used": self.model,
                    "task_type": task_type.value,
                    "agent": self.name,
                },
                suggestions=result.get("recommendations", []),
                model_used=self.model,
                agent_name=self.name,
            )

        except Exception as e:
            logger.error("infra_agent_failed", error=str(e))
            self.state = AgentState.IDLE
            return AgentResult(
                success=False,
                content="",
                errors=[str(e)],
                metadata={"task_type": "unknown"},
                model_used=self.model,
                agent_name=self.name,
            )

    def can_handle(self, task: Task) -> bool:
        """
        Determina si este agente puede manejar la tarea.

        Analiza el prompt para detectar tareas relacionadas con:
        - Terraform, Kubernetes, Docker
        - Cloud providers (AWS, Azure, GCP)
        - CI/CD pipelines
        - Infraestructura como código
        - Arquitectura y escalabilidad

        Args:
            task: Tarea a evaluar

        Returns:
            True si puede manejar la tarea
        """
        infra_keywords = [
            "terraform",
            "kubernetes",
            "k8s",
            "helm",
            "docker",
            "container",
            "aws",
            "azure",
            "gcp",
            "cloud",
            "infrastructure",
            "infraestructura",
            "arquitectura",
            "architecture",
            "ansible",
            "networking",
            "security",
            "scalability",
            "microservices",
            "i-a-c",
            "iac",
            "pipeline",
            "ci-cd",
            "ci/cd",
            "deployment",
            "despliegue",
            "argocd",
            "gitops",
            "vpc",
            "subnet",
            "load balancer",
            "security group",
            "eks",
            "aks",
            "gke",
            "terraform module",
            "terraform plan",
            "terraform apply",
            "serverless",
            "lambda",
            "ec2",
            "s3",
            "rds",
            "network",
            "firewall",
            "iam",
            "monitoring",
            "prometheus",
            "grafana",
        ]

        task_lower = task.description.lower()
        return any(keyword in task_lower for keyword in infra_keywords)

    def _analyze_task_type(self, task: str) -> "InfraTaskType":
        """
        Analiza la tarea para determinar su tipo.

        Args:
            task: Descripción de la tarea

        Returns:
            InfraTaskType identificado
        """
        task_lower = task.lower()

        # Terraform
        if any(kw in task_lower for kw in ["terraform", "tf", "hcl", "terragrunt"]):
            return InfraTaskType.TERRAFORM_MODULE

        # Kubernetes
        if any(
            kw in task_lower
            for kw in ["kubernetes", "k8s", "kubectl", "manifest", "deployment", "service", "pod"]
        ):
            return InfraTaskType.KUBERNETES_MANIFEST

        # Helm
        if any(kw in task_lower for kw in ["helm", "chart", "release"]):
            return InfraTaskType.HELM_CHART

        # Docker
        if any(kw in task_lower for kw in ["docker", "dockerfile", "docker-compose", "container"]):
            return InfraTaskType.DOCKERFILE

        # CI/CD
        if any(
            kw in task_lower
            for kw in ["pipeline", "ci-cd", "ci/cd", "github actions", "gitlab ci", "jenkins"]
        ):
            return InfraTaskType.CI_CD_PIPELINE

        # Cloud resources
        if any(
            kw in task_lower
            for kw in ["vpc", "subnet", "ec2", "s3", "rds", "lambda", "vm", "storage"]
        ):
            return InfraTaskType.CLOUD_RESOURCE

        # Network
        if any(
            kw in task_lower
            for kw in ["network", "vpc", "subnet", "route", "firewall", "security group"]
        ):
            return InfraTaskType.NETWORK_CONFIG

        # Security
        if any(
            kw in task_lower for kw in ["security", "iam", "policy", "rbac", "encryption", "secret"]
        ):
            return InfraTaskType.SECURITY_CONFIG

        # Monitoring
        if any(
            kw in task_lower
            for kw in ["monitoring", "prometheus", "grafana", "logging", "observability"]
        ):
            return InfraTaskType.MONITORING_SETUP

        # Cost
        if any(kw in task_lower for kw in ["cost", "optimization", "budget", "savings"]):
            return InfraTaskType.COST_OPTIMIZATION

        return InfraTaskType.TERRAFORM_MODULE

    def _build_prompt(
        self,
        task: str,
        task_type: InfraTaskType,
        context: "SessionContext",
        project_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Construye el prompt enriquecido para el LLM.

        Args:
            task: Descripción de la tarea
            task_type: Tipo de tarea
            context: Contexto de la sesión
            project_context: Contexto del proyecto

        Returns:
            Prompt completo
        """
        sections = []

        # Encabezado
        sections.append(f"# Tarea de Infraestructura: {task_type.value}")
        sections.append(f"\n## Descripción\n{task}\n")

        # Contexto del proyecto
        if project_context:
            sections.append("## Contexto del Proyecto")
            if "cloud_provider" in project_context:
                sections.append(f"- Cloud Provider: {project_context['cloud_provider']}")
            if "existing_infra" in project_context:
                sections.append(f"- Infraestructura existente: {project_context['existing_infra']}")
            if "requirements" in project_context:
                sections.append(f"- Requisitos: {project_context['requirements']}")
            sections.append("")

        # Tipo específico de prompt
        sections.append(self._get_task_specific_prompt(task_type))

        # Mejores prácticas
        sections.append("\n## Mejores Prácticas")
        sections.append(self._get_best_practices_prompt(task_type))

        return "\n".join(sections)

    def _get_task_specific_prompt(self, task_type: InfraTaskType) -> str:
        """
        Obtiene el prompt específico para el tipo de tarea.

        Args:
            task_type: Tipo de tarea

        Returns:
            Prompt específico
        """
        prompts = {
            InfraTaskType.TERRAFORM_MODULE: """
## Requisitos para Terraform
- Estructura de módulo estándar:
  - main.tf: Recursos principales
  - variables.tf: Variables de entrada
  - outputs.tf: Valores de salida
  - versions.tf: Versiones de providers
  - README.md: Documentación del módulo

- Incluir:
  - Descripción de cada variable
  - Valores por defecto apropiados
  - Validaciones de variables
  - Outputs documentados
  - Ejemplos de uso
""",
            InfraTaskType.KUBERNETES_MANIFEST: """
## Requisitos para Kubernetes
- Manifiestos declarativos en YAML
- Labels estándar (app, version, component, environment)
- Resource limits y requests definidos
- Probes de liveness y readiness
- ConfigMaps para configuración
- Secrets para datos sensibles
- NetworkPolicies si es necesario
- Namespace apropiado
""",
            InfraTaskType.HELM_CHART: """
## Requisitos para Helm Chart
- Estructura de chart estándar:
  - Chart.yaml: Metadatos del chart
  - values.yaml: Valores configurables
  - templates/: Manifiestos template
  - templates/helpers.tpl: Funciones helper
  - README.md: Documentación

- Incluir:
  - Values con defaults sensatos
  - Notas de instalación
  - Dependencias si aplica
""",
            InfraTaskType.DOCKERFILE: """
## Requisitos para Dockerfile
- Multi-stage build si es necesario
- Imagen base mínima (alpine/distroless)
- .dockerignore apropiado
- Labels estándar
- Health check
- Usuario no-root
- Layers optimizados
""",
            InfraTaskType.CI_CD_PIPELINE: """
## Requisitos para Pipeline CI/CD
- Stages claros (lint, test, build, deploy)
- Caché de dependencias
- Secrets management
- Ambientes (dev, staging, prod)
- Rollback automático
- Notificaciones
- Artifacts versioning
""",
        }

        return prompts.get(task_type, "")

    def _get_best_practices_prompt(self, task_type: InfraTaskType) -> str:
        """
        Obtiene las mejores prácticas para el tipo de tarea.

        Args:
            task_type: Tipo de tarea

        Returns:
            Mejores prácticas
        """
        return """
### Generales
- Nombres descriptivos y consistentes
- Documentación inline
- Modular y reutilizable
- Versionamiento
- Tags y labels apropiados
- Seguridad por defecto
- Costo-eficiente

### Entregables
1. Código IaC completo y funcional
2. Comandos de validación
3. Instrucciones de despliegue
4. Documentación
5. Diagrama de arquitectura (si aplica)
"""

    def _process_response(
        self,
        response: str,
        task_type: InfraTaskType,
    ) -> Dict[str, Any]:
        """
        Procesa la respuesta del LLM.

        Args:
            response: Respuesta del modelo
            task_type: Tipo de tarea

        Returns:
            Diccionario con contenido procesado
        """
        # TODO: Implementar parsing más sofisticado
        # Por ahora retornamos la respuesta como está
        return {
            "content": response,
            "files": [],
            "commands": [],
            "documentation": response,
            "recommendations": [],
        }

    def get_tools(self) -> List[str]:
        """Retorna las herramientas disponibles."""
        return self.tools

    def get_capabilities(self) -> List[AgentCapability]:
        """Retorna las capacidades del agente."""
        return self.capabilities

    def __repr__(self) -> str:
        return f"<InfraAgent(name='{self.name}', model='{self.model}')>"
