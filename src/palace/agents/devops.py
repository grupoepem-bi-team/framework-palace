"""
Agente DevOps - Palace Framework

Este agente se especializa en:
- Configuración y gestión de pipelines CI/CD
- Automatización de despliegues
- Infraestructura como código (básico)
- Monitoreo y observabilidad
- Gestión de entornos
- Containerización (Docker, Kubernetes)

Modelo asignado: qwen3.5
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List

import structlog

from palace.agents.base import AgentBase, AgentResult, AgentRole, AgentState, Task
from palace.core.types import AgentCapability
from palace.memory.base import MemoryType, SearchQuery

if TYPE_CHECKING:
    from palace.context import SessionContext
    from palace.llm import LLMClient
    from palace.memory import MemoryStore

logger = structlog.get_logger()


# =============================================================================
# Keywords para detección de tareas DevOps
# =============================================================================

DEVOPS_KEYWORDS = [
    "pipeline",
    "ci/cd",
    "ci",
    "cd",
    "deploy",
    "deployment",
    "docker",
    "kubernetes",
    "k8s",
    "helm",
    "container",
    "jenkins",
    "github actions",
    "gitlab ci",
    "terraform",
    "ansible",
    "infraestructura",
    "infrastructure",
    "monitoreo",
    "monitoring",
    "observabilidad",
    "rollback",
    "entorno",
    "environment",
    "staging",
    "producción",
    "production",
    "dockerfile",
    "docker-compose",
    "manifest",
    "prometheus",
    "grafana",
    "cloudformation",
    "argocd",
    "flux",
    "devops",
    "sre",
    "site reliability",
    "containers",
    "containerización",
    "despliegue",
    "despliegues",
    "ci pipeline",
    "cd pipeline",
    "build pipeline",
    "release",
    "artifact",
    "registry",
    "vault",
    "secrets",
]


# =============================================================================
# Data Classes & Enums
# =============================================================================


class DevOpsTaskType(str, Enum):
    """Tipos de tareas que puede manejar el agente DevOps."""

    PIPELINE_CREATE = "pipeline_create"
    """Crear un nuevo pipeline CI/CD."""

    PIPELINE_UPDATE = "pipeline_update"
    """Actualizar un pipeline existente."""

    DEPLOY = "deploy"
    """Ejecutar un despliegue."""

    ROLLBACK = "rollback"
    """Revertir un despliegue."""

    ENVIRONMENT_SETUP = "environment_setup"
    """Configurar un entorno (dev, staging, prod)."""

    DOCKERFILE_CREATE = "dockerfile_create"
    """Crear Dockerfile para una aplicación."""

    KUBERNETES_MANIFEST = "kubernetes_manifest"
    """Crear manifiestos de Kubernetes."""

    MONITORING_SETUP = "monitoring_setup"
    """Configurar monitoreo y alertas."""

    SECRETS_MANAGEMENT = "secrets_management"
    """Gestionar secrets y variables de entorno."""

    INFRA_VALIDATION = "infra_validation"
    """Validar configuración de infraestructura."""


@dataclass
class DevOpsCapabilities:
    """Capacidades específicas del agente DevOps."""

    ci_cd_tools: List[str] = field(
        default_factory=lambda: [
            "github_actions",
            "gitlab_ci",
            "jenkins",
            "azure_devops",
            "circleci",
            "travis_ci",
        ]
    )
    """Herramientas CI/CD soportadas."""

    container_tools: List[str] = field(
        default_factory=lambda: [
            "docker",
            "docker_compose",
            "kubernetes",
            "helm",
            "kustomize",
        ]
    )
    """Herramientas de contenedores soportadas."""

    cloud_providers: List[str] = field(
        default_factory=lambda: [
            "aws",
            "azure",
            "gcp",
            "digitalocean",
            "heroku",
        ]
    )
    """Proveedores de nube soportados."""

    infrastructure_tools: List[str] = field(
        default_factory=lambda: [
            "terraform",
            "ansible",
            "cloudformation",
        ]
    )
    """Herramientas de infraestructura soportadas."""

    monitoring_tools: List[str] = field(
        default_factory=lambda: [
            "prometheus",
            "grafana",
            "datadog",
            "newrelic",
            "cloudwatch",
        ]
    )
    """Herramientas de monitoreo soportadas."""


class DevOpsAgent(AgentBase):
    """
    Agente especializado en DevOps y CI/CD.

    Este agente maneja todas las tareas relacionadas con:
    - Pipelines de integración continua
    - Despliegue continuo
    - Containerización
    - Orquestación de contenedores
    - Monitoreo y observabilidad
    - Gestión de entornos

    Modelo: qwen3.5
    Capacidades: DEVOPS, INFRASTRUCTURE_AS_CODE

    Ejemplo de uso:
        agent = DevOpsAgent(llm_client=client)
        result = await agent.run(task, context, memory)
    """

    name: str = "devops"
    model: str = "qwen3.5"
    role: AgentRole = AgentRole.DEVOPS

    capabilities: List[AgentCapability] = [
        AgentCapability.DEVOPS,
        AgentCapability.INFRASTRUCTURE_AS_CODE,
        AgentCapability.DOCUMENTATION,
    ]

    system_prompt: str = """Eres un ingeniero DevOps senior especializado en automatización, CI/CD y infraestructura.

Tu rol es:
- Diseñar y mantener pipelines CI/CD eficientes
- Automatizar despliegues de manera segura y confiable
- Configurar entornos de desarrollo, staging y producción
- Implementar mejores prácticas de DevOps

Herramientas que dominas:
- CI/CD: GitHub Actions, GitLab CI, Jenkins, Azure DevOps
- Contenedores: Docker, Kubernetes, Helm
- Cloud: AWS, Azure, GCP
- IaC: Terraform, Ansible, CloudFormation
- Monitoreo: Prometheus, Grafana, DataDog

Principios que sigues:
1. Automatización sobre procesos manuales
2. Infraestructura como código
3. Despliegues seguros con rollback fácil
4. Monitoreo proactivo
5. Seguridad integrada en el pipeline

Siempre proporciona:
- Código completo y funcional
- Documentación clara
- Consideraciones de seguridad
- Plan de rollback cuando aplique
"""

    description: str = (
        "Agente especializado en DevOps para pipelines CI/CD, "
        "automatización de despliegues y gestión de infraestructura."
    )

    tools: List[str] = [
        "shell_executor",
        "file_writer",
        "git_operations",
        "docker_client",
        "kubernetes_client",
        "yaml_parser",
        "env_validator",
    ]

    # Capacidades específicas del agente
    devops_capabilities: DevOpsCapabilities = field(default_factory=DevOpsCapabilities)

    # =========================================================================
    # Inicialización
    # =========================================================================

    def __init__(
        self,
        llm_client: "LLMClient",
        capabilities: DevOpsCapabilities | None = None,
        tools: List[str] | None = None,
    ):
        """
        Inicializa el agente DevOps.

        Args:
            llm_client: Cliente LLM para invocar modelos
            capabilities: Capacidades específicas de DevOps (opcional)
            tools: Herramientas disponibles (opcional)
        """
        super().__init__(
            name=self.name,
            role=self.role,
            model=self.model,
            llm_client=llm_client,
            tools=tools or self.tools,
        )
        self.devops_capabilities = capabilities or DevOpsCapabilities()

    # =========================================================================
    # Métodos abstractos de AgentBase
    # =========================================================================

    def _build_system_prompt(self) -> str:
        """
        Construye el prompt del sistema para el agente DevOps.

        Returns:
            Prompt del sistema como cadena
        """
        return self.system_prompt

    def _get_description(self) -> str:
        """
        Obtiene la descripción del agente DevOps.

        Returns:
            Descripción del agente como cadena
        """
        return self.description

    async def run(
        self,
        task: Task,
        context: "SessionContext",
        memory: "MemoryStore",
    ) -> AgentResult:
        """
        Ejecuta una tarea DevOps.

        Flujo de ejecución:
        1. Recuperar contexto relevante de memoria
        2. Analizar la tarea y determinar el tipo DevOps
        3. Construir prompt con contexto específico
        4. Invocar LLM para generar solución
        5. Procesar respuesta y generar artefactos
        6. Guardar aprendizaje en memoria
        7. Retornar resultado

        Args:
            task: Tarea a ejecutar
            context: Contexto de sesión con información del proyecto
            memory: Almacén de memoria para contexto adicional

        Returns:
            AgentResult con el resultado de la ejecución
        """
        self.state = AgentState.BUSY
        start_time = datetime.utcnow()

        logger.info(
            "devops_task_started",
            task_preview=task.description[:100] if task.description else "",
            agent=self.name,
        )

        try:
            # Paso 1: Recuperar contexto relevante de memoria
            relevant_memory = await self._retrieve_relevant_context(
                task=task,
                memory=memory,
            )

            # Paso 2: Construir prompt con contexto
            prompt = self._build_task_prompt(
                task=task,
                context=context,
                memory_context=relevant_memory,
            )

            # Paso 3: Invocar LLM con temperatura baja para configuraciones precisas
            response = await self.invoke_llm(
                prompt=prompt,
                temperature=0.15,  # Temperatura baja para YAML/configs precisas
            )

            # Paso 4: Procesar respuesta y generar artefactos
            result = self._process_response(response, task)

            # Paso 5: Guardar aprendizaje en memoria si es relevante
            await self._store_learning(
                task=task,
                result=result,
                memory=memory,
            )

            # Actualizar estado
            self.state = AgentState.IDLE

            logger.info(
                "devops_task_completed",
                success=result.success,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent=self.name,
            )

            return result

        except Exception as e:
            self.state = AgentState.ERROR
            logger.exception(
                "devops_task_failed",
                error=str(e),
                agent=self.name,
            )

            return AgentResult(
                success=False,
                content="",
                errors=[f"DevOps task failed: {str(e)}"],
                metadata={"task": task.description, "agent": self.name},
            )

    def can_handle(self, task: Task) -> bool:
        """
        Determina si este agente puede manejar la tarea.

        Analiza la descripción para detectar tareas relacionadas con:
        - CI/CD pipelines
        - Dockerfile y containers
        - Kubernetes y orquestación
        - Despliegues
        - Infraestructura
        - Monitoreo y observabilidad

        Args:
            task: Tarea a evaluar

        Returns:
            True si puede manejar la tarea, False en caso contrario
        """
        if not task.description:
            return False

        description_lower = task.description.lower()

        # Verificar palabras clave de DevOps
        keyword_matches = sum(1 for keyword in DEVOPS_KEYWORDS if keyword in description_lower)

        # Si hay al menos 2 coincidencias de keywords, probablemente es tarea DevOps
        if keyword_matches >= 2:
            return True

        # Verificar patrones específicos de DevOps
        devops_patterns = [
            r"\.yml\b",
            r"\.yaml\b",
            r"\bDockerfile\b",
            r"\bkubectl\b",
            r"\bdocker\s+(build|run|compose|push|pull)\b",
            r"\bterraform\s+(init|plan|apply|destroy)\b",
            r"\bansible-playbook\b",
            r"\bhelm\s+(install|upgrade|rollback)\b",
            r"\bgithub\.com/.*\.github/workflows\b",
            r"\bgitlab\.com/.*\.gitlab-ci\b",
        ]
        for pattern in devops_patterns:
            if re.search(pattern, description_lower, re.IGNORECASE):
                return True

        # Si solo hay 1 coincidencia, verificar que sea un indicador fuerte
        if keyword_matches == 1:
            strong_indicators = [
                "pipeline",
                "ci/cd",
                "docker",
                "kubernetes",
                "k8s",
                "terraform",
                "ansible",
                "jenkins",
                "github actions",
                "gitlab ci",
                "dockerfile",
                "helm",
                "prometheus",
                "grafana",
                "devops",
                "deploy",
                "deployment",
                "rollback",
                "containerización",
                "despliegue",
            ]
            for indicator in strong_indicators:
                if indicator in description_lower:
                    return True

        return False

    # =========================================================================
    # Métodos auxiliares
    # =========================================================================

    async def _retrieve_relevant_context(
        self,
        task: Task,
        memory: "MemoryStore",
    ) -> str:
        """
        Recupera contexto relevante de la memoria vectorial.

        Busca información relacionada con:
        - Pipelines CI/CD existentes
        - Configuraciones Docker y Kubernetes
        - Templates de infraestructura
        - Convenciones de despliegue del proyecto

        Args:
            task: Tarea actual
            memory: Almacén de memoria

        Returns:
            Contexto relevante como cadena
        """
        try:
            search_query = SearchQuery(
                query=task.description,
                project_id=task.project_id if hasattr(task, "project_id") else None,
                memory_types=[MemoryType.SEMANTIC, MemoryType.PROCEDURAL],
                filters={
                    "type": [
                        "pipeline_config",
                        "docker_config",
                        "kubernetes_config",
                        "infrastructure_config",
                        "deployment_pattern",
                        "monitoring_config",
                        "error",
                        "solution",
                        "pattern",
                    ]
                },
                top_k=5,
            )

            results = await memory.search(search_query)

            if not results:
                return ""

            context_parts = []
            for result in results:
                entry = result.entry
                entry_type = entry.metadata.get("type", entry.memory_type.value)
                context_parts.append(f"- [{entry_type}] {entry.content}")

            return "\n".join(context_parts)

        except Exception as e:
            logger.warning(
                "devops_context_retrieval_failed",
                error=str(e),
                agent=self.name,
            )
            return ""

    def _build_task_prompt(
        self,
        task: Task,
        context: "SessionContext",
        memory_context: str,
    ) -> str:
        """
        Construye el prompt completo para la tarea DevOps.

        Combina:
        - Contexto del proyecto (stack, infraestructura actual)
        - Contexto de memoria relevante
        - Herramienta CI/CD específica si se detecta
        - La tarea específica
        - Instrucciones de formato

        Args:
            task: Tarea a ejecutar
            context: Contexto de sesión
            memory_context: Contexto recuperado de memoria

        Returns:
            Prompt completo para el LLM
        """
        prompt_parts = []

        # Contexto del proyecto
        if hasattr(context, "project_context") and context.project_context:
            project = context.project_context
            if hasattr(project, "config"):
                prompt_parts.append("## Contexto del Proyecto")
                if hasattr(project.config, "name"):
                    prompt_parts.append(f"- Proyecto: {project.config.name}")
                if hasattr(project.config, "stack"):
                    prompt_parts.append(f"- Stack: {project.config.stack}")

        # Contexto de memoria
        if memory_context:
            prompt_parts.append("\n## Contexto Relevante (de memoria)")
            prompt_parts.append(memory_context)

        # Herramienta CI/CD específica si se detecta en la descripción
        description_lower = task.description.lower() if task.description else ""
        for tool in self.devops_capabilities.ci_cd_tools:
            tool_name = tool.replace("_", " ")
            if tool_name in description_lower or tool in description_lower:
                ci_cd_prompt = self._get_ci_cd_prompt(tool)
                if ci_cd_prompt:
                    prompt_parts.append(f"\n## Instrucciones específicas de {tool_name.title()}")
                    prompt_parts.append(ci_cd_prompt)
                break

        # Herramienta de contenedores específica si se detecta
        for tool in self.devops_capabilities.container_tools:
            tool_name = tool.replace("_", " ")
            if tool_name in description_lower or tool in description_lower:
                container_prompt = self._get_container_prompt(tool)
                if container_prompt:
                    prompt_parts.append(f"\n## Instrucciones específicas de {tool_name.title()}")
                    prompt_parts.append(container_prompt)
                break

        # Tarea
        prompt_parts.append("\n## Tarea")
        prompt_parts.append(task.description)

        # Metadata de la tarea
        if hasattr(task, "metadata") and task.metadata:
            prompt_parts.append("\n## Información Adicional")
            for key, value in task.metadata.items():
                prompt_parts.append(f"- {key}: {value}")

        # Instrucciones de formato
        prompt_parts.append("\n## Instrucciones de Formato")
        prompt_parts.append(
            "Proporciona tu respuesta con el siguiente formato:\n"
            "1. **Enfoque**: Explica tu razonamiento y decisiones de diseño\n"
            "2. **Configuración**: Código YAML/Dockerfile/HCL completo y funcional\n"
            "3. **Archivos**: Lista de archivos a crear/modificar con sus rutas\n"
            "4. **Comandos**: Comandos necesarios para aplicar la configuración\n"
            "5. **Seguridad**: Consideraciones de seguridad y mejores prácticas\n"
            "6. **Rollback**: Plan de rollback si aplica"
        )

        return "\n".join(prompt_parts)

    def _process_response(
        self,
        response: str,
        task: Task,
    ) -> AgentResult:
        """
        Procesa la respuesta del LLM y genera el resultado.

        Extrae artefactos de la respuesta (YAML, Dockerfile, HCL, bash, etc.)
        y los organiza en el resultado.

        Args:
            response: Respuesta del LLM
            task: Tarea original

        Returns:
            AgentResult con el resultado procesado
        """
        # Extraer bloques de código YAML
        yaml_blocks = self._extract_code_blocks(response, "yaml")
        yml_blocks = self._extract_code_blocks(response, "yml")

        # Extraer bloques de Dockerfile
        dockerfile_blocks = self._extract_code_blocks(response, "dockerfile")

        # Extraer bloques de HCL (Terraform)
        hcl_blocks = self._extract_code_blocks(response, "hcl")
        terraform_blocks = self._extract_code_blocks(response, "terraform")

        # Extraer bloques de bash/shell
        bash_blocks = self._extract_code_blocks(response, "bash")
        shell_blocks = self._extract_code_blocks(response, "shell")

        # Extraer bloques JSON
        json_blocks = self._extract_code_blocks(response, "json")

        # Extraer bloques Python (scripts de automatización)
        python_blocks = self._extract_code_blocks(response, "python")

        # Determinar tipo de resultado basado en la tarea
        task_type = self._analyze_task_type_sync(task.description)

        # Construir metadata del resultado
        metadata = {
            "agent": self.name,
            "model": self.model,
            "task_type": task_type,
            "yaml_artifacts": len(yaml_blocks) + len(yml_blocks),
            "dockerfile_artifacts": len(dockerfile_blocks),
            "iac_artifacts": len(hcl_blocks) + len(terraform_blocks),
        }

        # Construir lista de artefactos
        artifacts = []

        # Agregar artefactos YAML
        for i, block in enumerate(yaml_blocks + yml_blocks):
            artifacts.append(
                {
                    "type": "config",
                    "language": "yaml",
                    "content": block,
                    "index": i + 1,
                }
            )

        # Agregar artefactos Dockerfile
        for i, block in enumerate(dockerfile_blocks):
            artifacts.append(
                {
                    "type": "config",
                    "language": "dockerfile",
                    "content": block,
                    "index": i + 1,
                }
            )

        # Agregar artefactos de IaC
        for i, block in enumerate(hcl_blocks + terraform_blocks):
            artifacts.append(
                {
                    "type": "infrastructure",
                    "language": "hcl",
                    "content": block,
                    "index": i + 1,
                }
            )

        # Agregar artefactos de shell/bash
        for i, block in enumerate(bash_blocks + shell_blocks):
            artifacts.append(
                {
                    "type": "command",
                    "language": "bash",
                    "content": block,
                    "index": i + 1,
                }
            )

        # Agregar artefactos JSON
        for i, block in enumerate(json_blocks):
            artifacts.append(
                {
                    "type": "config",
                    "language": "json",
                    "content": block,
                    "index": i + 1,
                }
            )

        # Agregar artefactos Python
        for i, block in enumerate(python_blocks):
            artifacts.append(
                {
                    "type": "script",
                    "language": "python",
                    "content": block,
                    "index": i + 1,
                }
            )

        # Extraer recomendaciones de la respuesta
        suggestions = self._extract_suggestions(response)

        # Extraer acciones siguientes
        next_actions = self._extract_next_actions(response)

        return AgentResult(
            success=True,
            content=response,
            artifacts=artifacts,
            metadata=metadata,
            suggestions=suggestions,
            next_actions=next_actions,
            agent_name=self.name,
            model_used=self.model,
        )

    def _extract_code_blocks(
        self,
        text: str,
        language: str,
    ) -> List[str]:
        """
        Extrae bloques de código de un lenguaje específico.

        Args:
            text: Texto del que extraer bloques
            language: Lenguaje de programación (yaml, dockerfile, hcl, bash, etc.)

        Returns:
            Lista de bloques de código encontrados
        """
        pattern = rf"```{language}\s*\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        return [match.strip() for match in matches if match.strip()]

    def _extract_suggestions(self, response: str) -> List[str]:
        """
        Extrae sugerencias y recomendaciones de la respuesta.

        Args:
            response: Respuesta del LLM

        Returns:
            Lista de sugerencias encontradas
        """
        suggestions = []

        # Buscar secciones de recomendaciones
        patterns = [
            r"(?:Recomendaci[oó]n|Sugerencia|Recommendation|Suggestion):\s*(.+?)(?:\n|$)",
            r"(?:⚠️|💡|📋)\s*(.+?)(?:\n|$)",
            r"^\s*[-*]\s+\*{0,2}(?:Recomendaci[oó]n|Sugerencia)\*{0,2}:\s*(.+?)$",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.MULTILINE | re.IGNORECASE)
            suggestions.extend(match.strip() for match in matches if match.strip())

        return suggestions[:5]  # Limitar a 5 sugerencias

    def _extract_next_actions(self, response: str) -> List[str]:
        """
        Extrae acciones siguientes de la respuesta.

        Args:
            response: Respuesta del LLM

        Returns:
            Lista de acciones siguientes
        """
        next_actions = []

        # Buscar comandos de acción
        patterns = [
            r"(?:Ejecutar|Run|Apply|Deploy):\s*`([^`]+)`",
            r"(?:kubectl|docker|terraform|ansible|helm)\s+[\w\-]+\s+[\w\-./]+",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            next_actions.extend(match.strip() for match in matches if match.strip())

        return next_actions[:5]  # Limitar a 5 acciones

    def _analyze_task_type_sync(self, description: str) -> str:
        """
        Analiza la descripción para determinar el tipo de tarea DevOps (síncrono).

        Args:
            description: Descripción de la tarea

        Returns:
            Tipo de tarea DevOps identificada como cadena
        """
        if not description:
            return DevOpsTaskType.INFRA_VALIDATION.value

        description_lower = description.lower()

        if any(
            kw in description_lower for kw in ["crear pipeline", "nuevo pipeline", "ci/cd nuevo"]
        ):
            return DevOpsTaskType.PIPELINE_CREATE.value

        if any(
            kw in description_lower
            for kw in ["actualizar pipeline", "modificar pipeline", "cambiar pipeline"]
        ):
            return DevOpsTaskType.PIPELINE_UPDATE.value

        if any(kw in description_lower for kw in ["desplegar", "deploy", "deployment"]):
            return DevOpsTaskType.DEPLOY.value

        if any(
            kw in description_lower for kw in ["rollback", "revertir despliegue", "deshacer deploy"]
        ):
            return DevOpsTaskType.ROLLBACK.value

        if any(
            kw in description_lower
            for kw in ["configurar entorno", "ambiente", "environment setup"]
        ):
            return DevOpsTaskType.ENVIRONMENT_SETUP.value

        if any(kw in description_lower for kw in ["dockerfile", "docker file"]):
            return DevOpsTaskType.DOCKERFILE_CREATE.value

        if any(kw in description_lower for kw in ["kubernetes", "k8s", "manifest", "helm chart"]):
            return DevOpsTaskType.KUBERNETES_MANIFEST.value

        if any(kw in description_lower for kw in ["monitoreo", "monitoring", "alertas", "alerts"]):
            return DevOpsTaskType.MONITORING_SETUP.value

        if any(
            kw in description_lower
            for kw in ["secrets", "variables de entorno", "env vars", "vault"]
        ):
            return DevOpsTaskType.SECRETS_MANAGEMENT.value

        return DevOpsTaskType.INFRA_VALIDATION.value

    async def _store_learning(
        self,
        task: Task,
        result: AgentResult,
        memory: "MemoryStore",
    ) -> None:
        """
        Almacena aprendizaje de la tarea en memoria.

        Solo almacena información útil y evita duplicados.

        Args:
            task: Tarea ejecutada
            result: Resultado de la ejecución
            memory: Almacén de memoria
        """
        if not result.success or not result.content:
            return

        try:
            # Determinar tipo de memoria
            memory_type = self._infer_memory_type(task.description)

            # Crear metadata para la memoria
            metadata = {
                "agent": self.name,
                "model": self.model,
                "task_type": self._analyze_task_type_sync(task.description),
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Almacenar en memoria como conocimiento
            _ = await memory.store_knowledge(
                project_id=task.project_id if hasattr(task, "project_id") else "",
                title=f"DevOps: {task.description[:80]}",
                content=result.content[:1000],  # Limitar tamaño
                tags=[memory_type, self._analyze_task_type_sync(task.description)],
                metadata=metadata,
            )

            logger.debug(
                "devops_learning_stored",
                memory_type=memory_type,
                agent=self.name,
            )

        except Exception as e:
            logger.warning(
                "devops_learning_store_failed",
                error=str(e),
                agent=self.name,
            )

    def _infer_memory_type(self, description: str) -> str:
        """
        Infiere el tipo de memoria basado en la descripción de la tarea.

        Args:
            description: Descripción de la tarea

        Returns:
            Tipo de memoria apropiado
        """
        description_lower = description.lower()

        if any(kw in description_lower for kw in ["error", "fallo", "falló", "failed", "bug"]):
            return "errors"
        elif any(
            kw in description_lower
            for kw in ["solución", "solution", "resolver", "fix", "arreglar"]
        ):
            return "solutions"
        elif any(kw in description_lower for kw in ["config", "configuración", "setup", "ajuste"]):
            return "configs"
        elif any(
            kw in description_lower
            for kw in ["patrón", "pattern", "mejor práctica", "best practice", "arquitectura"]
        ):
            return "patterns"
        elif any(kw in description_lower for kw in ["pipeline", "ci/cd", "deploy", "deployment"]):
            return "pipelines"
        elif any(
            kw in description_lower for kw in ["docker", "kubernetes", "k8s", "container", "helm"]
        ):
            return "containers"
        elif any(
            kw in description_lower
            for kw in ["terraform", "ansible", "cloudformation", "infraestructura"]
        ):
            return "infrastructure"
        else:
            return "patterns"  # Default para DevOps

    # =========================================================================
    # Prompts específicos por herramienta
    # =========================================================================

    def _get_ci_cd_prompt(self, tool: str) -> str:
        """
        Genera un prompt específico para una herramienta CI/CD.

        Args:
            tool: Nombre de la herramienta CI/CD

        Returns:
            Prompt específico para la herramienta
        """
        prompts = {
            "github_actions": (
                "Usa GitHub Actions con la siguiente estructura:\n"
                "- Archivo YAML en .github/workflows/\n"
                "- Usa actions/checkout@v4 y actions/setup-* \n"
                "- Configura triggers on: push/pull_request\n"
                "- Usa jobs con steps claros\n"
                "- Implementa caching para dependencias\n"
                "- Configura artifacts para build outputs"
            ),
            "gitlab_ci": (
                "Usa GitLab CI con la siguiente estructura:\n"
                "- Archivo .gitlab-ci.yml en la raíz\n"
                "- Define stages: build, test, deploy\n"
                "- Usa variables y artifacts\n"
                "- Configura environments para despliegues\n"
                "- Usa only/except o rules para controlar ejecución"
            ),
            "jenkins": (
                "Usa Jenkins con la siguiente estructura:\n"
                "- Jenkinsfile con pipeline declarativo\n"
                "- Define agent, stages, steps\n"
                "- Usa credentials() para secrets\n"
                "- Implementa post-actions para notificaciones\n"
                "- Configura parameters si es necesario"
            ),
            "azure_devops": (
                "Usa Azure DevOps Pipelines con la siguiente estructura:\n"
                "- Archivo YAML azure-pipelines.yml\n"
                "- Define stages, jobs, steps\n"
                "- Usa UseDotNet, NuGetCommand tasks\n"
                "- Configura variables y variable groups\n"
                "- Implementa environments con approvals"
            ),
        }
        return prompts.get(tool, "")

    def _get_container_prompt(self, tool: str) -> str:
        """
        Genera un prompt específico para una herramienta de contenedores.

        Args:
            tool: Nombre de la herramienta de contenedores

        Returns:
            Prompt específico para la herramienta
        """
        prompts = {
            "docker": (
                "Usa Docker con las siguientes mejores prácticas:\n"
                "- Usa imágenes base oficiales y livianas (alpine, slim)\n"
                "- Implementa multi-stage builds\n"
                "- Minimiza capas y usa .dockerignore\n"
                "- No ejecites como root (USER directive)\n"
                "- Configura HEALTHCHECK\n"
                "- Ordena instrucciones de menos a más cambiantes"
            ),
            "docker_compose": (
                "Usa Docker Compose con la siguiente estructura:\n"
                "- Archivo docker-compose.yml versión 3.8+\n"
                "- Define servicios con build o image\n"
                "- Configura networks y volumes\n"
                "- Usa environment y env_file\n"
                "- Implementa healthchecks\n"
                "- Configura depends_on con condition"
            ),
            "kubernetes": (
                "Usa Kubernetes con las siguientes mejores prácticas:\n"
                "- Define Deployment con replicas y strategy\n"
                "- Configura resources requests y limits\n"
                "- Implementa livenessProbe y readinessProbe\n"
                "- Usa ConfigMaps y Secrets\n"
                "- Configura Service y Ingress\n"
                "- Implementa HorizontalPodAutoscaler si aplica"
            ),
            "helm": (
                "Usa Helm con la siguiente estructura:\n"
                "- Crea un Chart con Chart.yaml y values.yaml\n"
                "- Organiza templates en templates/\n"
                "- Usa _helpers.tpl para funciones comunes\n"
                "- Parametriza todo en values.yaml\n"
                "- Implementa notes.txt para instrucciones post-install\n"
                "- Configura hooks si es necesario"
            ),
        }
        return prompts.get(tool, "")

    # =========================================================================
    # Métodos de utilidad
    # =========================================================================

    def get_tools(self) -> List[str]:
        """Retorna las herramientas disponibles para este agente."""
        return self.tools

    def get_capabilities(self) -> List[AgentCapability]:
        """Retorna las capacidades de este agente."""
        return self.capabilities

    def get_supported_tools(self) -> DevOpsCapabilities:
        """Retorna la configuración de herramientas soportadas."""
        return self.devops_capabilities

    def __repr__(self) -> str:
        return f"<DevOpsAgent(name='{self.name}', model='{self.model}')>"
