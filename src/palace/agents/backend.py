"""
Agente Backend - Palace Framework

Este agente se especializa en desarrollo backend, incluyendo:
- APIs REST y GraphQL
- Lógica de negocio
- Integración con bases de datos
- Microservicios
- Autenticación y autorización
- Testing backend
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

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
# Data Classes
# =============================================================================


@dataclass
class BackendCapabilities:
    """Capacidades específicas del agente Backend."""

    frameworks: list[str] = field(
        default_factory=lambda: [
            "fastapi",
            "django",
            "flask",
            "sqlalchemy",
            "pydantic",
            "alembic",
        ]
    )

    databases: list[str] = field(
        default_factory=lambda: [
            "postgresql",
            "mysql",
            "sqlite",
            "mongodb",
            "redis",
        ]
    )

    patterns: list[str] = field(
        default_factory=lambda: [
            "repository",
            "service_layer",
            "dependency_injection",
            "unit_of_work",
            "cqrs",
            "event_sourcing",
        ]
    )


# =============================================================================
# Palabras clave para detección de tareas
# =============================================================================

BACKEND_KEYWORDS = [
    # APIs y endpoints
    "api",
    "endpoint",
    "rest",
    "graphql",
    "route",
    "ruta",
    "controller",
    "controlador",
    "view",
    "vista",
    "serializer",
    "serializador",
    # Frameworks backend
    "fastapi",
    "django",
    "flask",
    "starlette",
    "express",
    "spring",
    "rails",
    # Lógica de negocio
    "lógica de negocio",
    "business logic",
    "servicio",
    "service",
    "use case",
    "caso de uso",
    "domain",
    "dominio",
    "application layer",
    "capa de aplicación",
    # Modelos y datos
    "modelo",
    "model",
    "schema",
    "esquema",
    "pydantic",
    "serializer",
    "dto",
    "vo",
    "value object",
    "entity",
    "entidad",
    "repository",
    "repositorio",
    # Autenticación y autorización
    "autenticación",
    "authentication",
    "autorización",
    "authorization",
    "jwt",
    "oauth",
    "token",
    "login",
    "logout",
    "session",
    "sesión",
    "middleware",
    "permisos",
    "permissions",
    "rbac",
    # Bases de datos (desde perspectiva backend)
    "sqlalchemy",
    "orm",
    "migration",
    "migración",
    "alembic",
    "crud",
    "database",
    "base de datos",
    "query",
    "consulta",
    # Microservicios
    "microservicio",
    "microservice",
    "distributed",
    "distribuido",
    "grpc",
    "rpc",
    "message queue",
    "cola de mensajes",
    "event",
    "evento",
    # Testing backend
    "pytest",
    "unit test",
    "test unitario",
    "integration test",
    "test de integración",
    "mock",
    "fixture",
    # Patrones y arquitectura
    "dependency injection",
    "inyección de dependencias",
    "clean architecture",
    "arquitectura limpia",
    "hexagonal",
    "cqrs",
    "event sourcing",
    "solid",
    # DevOps relacionado con backend
    "docker",
    "container",
    "contenedor",
    "env",
    "environment variable",
    "configuración",
    "configuration",
    # Seguridad backend
    "cors",
    "csrf",
    "rate limit",
    "throttle",
    "encryption",
    "encriptación",
    "hash",
    "password",
    "contraseña",
]


# =============================================================================
# Backend Agent
# =============================================================================


class BackendAgent(AgentBase):
    """
    Agente especializado en desarrollo backend.

    Este agente maneja tareas relacionadas con:
    - Creación de APIs REST y GraphQL
    - Implementación de lógica de negocio
    - Diseño e implementación de modelos de datos
    - Integración con bases de datos
    - Autenticación y autorización
    - Testing de endpoints y servicios
    - Optimización de queries
    - Documentación de APIs

    Modelo asignado: qwen3-coder-next

    Herramientas disponibles:
        - shell: Ejecución de comandos
        - file_read: Lectura de archivos
        - file_write: Escritura de archivos
        - linter: Análisis de código (ruff, mypy)
        - test_runner: Ejecución de tests (pytest)
        - git: Operaciones de git
    """

    name: str = "backend"
    role: AgentRole = AgentRole.BACKEND
    model: str = "qwen3-coder-next"
    description: str = (
        "Agente especializado en desarrollo backend con FastAPI, Django, Flask. "
        "Crea APIs REST/GraphQL, implementa lógica de negocio, diseña modelos de datos, "
        "y asegura mejores prácticas de código."
    )

    capabilities: list[AgentCapability] = [
        AgentCapability.BACKEND_DEVELOPMENT,
        AgentCapability.FULLSTACK_DEVELOPMENT,
        AgentCapability.TESTING,
        AgentCapability.DOCUMENTATION,
    ]

    tools: list[str] = [
        "shell",
        "file_read",
        "file_write",
        "linter",
        "test_runner",
        "git",
        "http_client",
    ]

    # Capacidades específicas del agente
    backend_capabilities: BackendCapabilities = field(default_factory=BackendCapabilities)

    system_prompt: str = """Eres un experto desarrollador backend especializado en Python.

Tu expertise incluye:
- FastAPI, Django, Flask y otros frameworks web
- SQLAlchemy, Alembic para bases de datos
- Autenticación (JWT, OAuth2, API Keys)
- APIs REST y GraphQL
- Testing con pytest
- Limpieza de código y mejores prácticas (SOLID, Clean Architecture)

Cuando implementes código backend:
1. Sigue las convenciones del proyecto existente
2. Usa type hints en todas las funciones
3. Implementa manejo de errores robusto
4. Añade logging apropiado
5. Incluye tests unitarios y de integración
6. Documenta endpoints con docstrings y OpenAPI

Formato de respuesta:
- Explica brevemente tu enfoque
- Proporciona el código completo
- Indica archivos a crear/modificar
- Sugiere tests a implementar
- Menciona consideraciones de seguridad si aplica"""

    # =========================================================================
    # Inicialización
    # =========================================================================

    def __init__(
        self,
        llm_client: "LLMClient",
        capabilities: BackendCapabilities | None = None,
        tools: list[str] | None = None,
    ):
        """
        Inicializa el agente Backend.

        Args:
            llm_client: Cliente LLM para invocar modelos
            capabilities: Capacidades específicas del Backend (opcional)
            tools: Herramientas disponibles (opcional)
        """
        super().__init__(
            name=self.name,
            role=self.role,
            model=self.model,
            llm_client=llm_client,
            tools=tools or self.tools,
        )
        self.backend_capabilities = capabilities or BackendCapabilities()

    # =========================================================================
    # Métodos abstractos de AgentBase
    # =========================================================================

    def _build_system_prompt(self) -> str:
        """
        Construye el prompt del sistema para el agente Backend.

        Returns:
            Prompt del sistema como cadena
        """
        return self.system_prompt

    def _get_description(self) -> str:
        """
        Obtiene la descripción del agente Backend.

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
        Ejecuta una tarea de desarrollo backend.

        Flujo de ejecución:
        1. Recuperar contexto relevante de memoria
        2. Analizar la tarea y determinar enfoque
        3. Generar código/implementación
        4. Validar con linter si aplica
        5. Retornar resultado con artefactos

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
            "backend_task_started",
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

            # Paso 3: Invocar LLM con temperatura moderada para creatividad controlada
            response = await self.invoke_llm(
                prompt=prompt,
                temperature=0.2,  # Temperatura moderada para código preciso pero flexible
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
                "backend_task_completed",
                success=result.success,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent=self.name,
            )

            return result

        except Exception as e:
            self.state = AgentState.ERROR
            logger.exception(
                "backend_task_failed",
                error=str(e),
                agent=self.name,
            )

            return AgentResult(
                success=False,
                content="",
                errors=[f"Backend task failed: {str(e)}"],
                metadata={"task": task.description, "agent": self.name},
            )

    def can_handle(self, task: Task) -> bool:
        """
        Determina si este agente puede manejar la tarea.

        Evalúa si la tarea está relacionada con:
        - Desarrollo backend
        - APIs REST/GraphQL
        - Lógica de negocio
        - Bases de datos (desde perspectiva backend)
        - Autenticación/autorización
        - Microservicios
        - Testing backend

        Args:
            task: Tarea a evaluar

        Returns:
            True si el agente puede manejar la tarea
        """
        if not task.description:
            return False

        description_lower = task.description.lower()

        # Verificar palabras clave de Backend
        keyword_matches = sum(1 for keyword in BACKEND_KEYWORDS if keyword in description_lower)

        # Si hay al menos 2 coincidencias de keywords, probablemente es tarea de Backend
        if keyword_matches >= 2:
            return True

        # Verificar patrones de API/endpoint
        api_patterns = [
            r"\bGET\s+/",
            r"\bPOST\s+/",
            r"\bPUT\s+/",
            r"\bPATCH\s+/",
            r"\bDELETE\s+/",
            r"\b/api/",
            r"\bendpoint\b",
            r"\broute\b",
        ]
        for pattern in api_patterns:
            if re.search(pattern, description_lower, re.IGNORECASE):
                return True

        # Si solo hay 1 coincidencia, verificar que no sea ambigua
        if keyword_matches == 1:
            # Palabras que por sí solas indican fuertemente tarea de Backend
            strong_indicators = [
                "api",
                "endpoint",
                "rest",
                "graphql",
                "fastapi",
                "django",
                "flask",
                "pydantic",
                "jwt",
                "oauth",
                "middleware",
                "crud",
                "microservicio",
                "microservice",
                "repository",
                "repositorio",
                "service layer",
                "capa de servicio",
                "serializer",
                "serializador",
                "controller",
                "controlador",
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
        - Patrones de API existentes
        - Modelos de datos y schemas
        - Configuración de autenticación
        - Convenciones del proyecto

        Args:
            task: Tarea actual
            memory: Almacén de memoria

        Returns:
            Contexto relevante como cadena
        """
        try:
            # Construir consulta de búsqueda con SearchQuery
            search_query = SearchQuery(
                query=task.description,
                project_id=task.project_id if hasattr(task, "project_id") else None,
                memory_types=[MemoryType.SEMANTIC, MemoryType.PROCEDURAL],
                filters={
                    "type": [
                        "api_pattern",
                        "model_schema",
                        "auth_config",
                        "project_convention",
                        "error",
                        "solution",
                        "pattern",
                    ]
                },
                top_k=5,
            )

            # Buscar en memoria por tipos relevantes
            results = await memory.search(search_query)

            if not results:
                return ""

            # Formatear contexto recuperado
            # SearchResult tiene: entry (MemoryEntry), score, highlights, distance
            # MemoryEntry tiene: content, metadata, source, memory_type, etc.
            context_parts = []
            for result in results:
                entry = result.entry
                entry_type = entry.metadata.get("type", entry.memory_type.value)
                context_parts.append(f"- [{entry_type}] {entry.content}")

            return "\n".join(context_parts)

        except Exception as e:
            logger.warning(
                "backend_context_retrieval_failed",
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
        Construye el prompt completo para la tarea.

        Combina:
        - Contexto del proyecto (stack, convenciones)
        - Contexto de memoria relevante
        - Framework específico si se detecta
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
                prompt_parts.append(f"## Contexto del Proyecto")
                if hasattr(project.config, "name"):
                    prompt_parts.append(f"- Proyecto: {project.config.name}")
                if hasattr(project.config, "stack"):
                    prompt_parts.append(f"- Stack: {project.config.stack}")

        # Contexto de memoria
        if memory_context:
            prompt_parts.append(f"\n## Contexto Relevante (de memoria)")
            prompt_parts.append(memory_context)

        # Framework específico si se detecta en la descripción
        description_lower = task.description.lower() if task.description else ""
        for framework in self.backend_capabilities.frameworks:
            if framework in description_lower:
                framework_prompt = self.get_framework_prompt(framework)
                if framework_prompt:
                    prompt_parts.append(f"\n## Instrucciones específicas de {framework.title()}")
                    prompt_parts.append(framework_prompt)
                break

        # Base de datos específica si se detecta en la descripción
        for database in self.backend_capabilities.databases:
            if database in description_lower:
                database_prompt = self.get_database_prompt(database)
                if database_prompt:
                    prompt_parts.append(f"\n## Instrucciones específicas de {database.title()}")
                    prompt_parts.append(database_prompt)
                break

        # Tarea
        prompt_parts.append(f"\n## Tarea")
        prompt_parts.append(task.description)

        # Metadata de la tarea
        if hasattr(task, "metadata") and task.metadata:
            prompt_parts.append(f"\n## Información Adicional")
            for key, value in task.metadata.items():
                prompt_parts.append(f"- {key}: {value}")

        # Instrucciones de formato
        prompt_parts.append(f"\n## Instrucciones de Formato")
        prompt_parts.append(
            "Proporciona tu respuesta con el siguiente formato:\n"
            "1. **Enfoque**: Explica tu razonamiento y decisiones de diseño\n"
            "2. **Código**: Implementación completa con type hints\n"
            "3. **Archivos**: Lista de archivos a crear/modificar\n"
            "4. **Tests**: Tests unitarios y de integración sugeridos\n"
            "5. **Seguridad**: Consideraciones de seguridad si aplica"
        )

        return "\n".join(prompt_parts)

    def _process_response(
        self,
        response: str,
        task: Task,
    ) -> AgentResult:
        """
        Procesa la respuesta del LLM y genera el resultado.

        Extrae artefactos de la respuesta (código Python, SQL, configs, etc.)
        y los organiza en el resultado.

        Args:
            response: Respuesta del LLM
            task: Tarea original

        Returns:
            AgentResult con el resultado procesado
        """
        # Extraer bloques de código Python
        python_blocks = self._extract_code_blocks(response, "python")

        # Extraer bloques de código SQL
        sql_blocks = self._extract_code_blocks(response, "sql")

        # Extraer bloques de configuración (YAML, TOML, JSON, etc.)
        yaml_blocks = self._extract_code_blocks(response, "yaml")
        toml_blocks = self._extract_code_blocks(response, "toml")
        json_blocks = self._extract_code_blocks(response, "json")

        # Extraer bloques de bash/shell
        bash_blocks = self._extract_code_blocks(response, "bash")
        shell_blocks = self._extract_code_blocks(response, "shell")

        # Determinar tipo de resultado basado en la tarea
        task_type = self._infer_task_type(task.description)

        # Construir metadata del resultado
        metadata = {
            "agent": self.name,
            "model": self.model,
            "task_type": task_type,
            "python_artifacts": len(python_blocks),
            "sql_artifacts": len(sql_blocks),
        }

        # Construir lista de artefactos
        artifacts = []

        # Agregar artefactos de código Python
        for i, block in enumerate(python_blocks):
            artifacts.append(
                {
                    "type": "code",
                    "language": "python",
                    "content": block,
                    "index": i + 1,
                }
            )

        # Agregar artefactos de código SQL
        for i, block in enumerate(sql_blocks):
            artifacts.append(
                {
                    "type": "code",
                    "language": "sql",
                    "content": block,
                    "index": i + 1,
                }
            )

        # Agregar artefactos de configuración
        for blocks, lang in [
            (yaml_blocks, "yaml"),
            (toml_blocks, "toml"),
            (json_blocks, "json"),
        ]:
            for i, block in enumerate(blocks):
                artifacts.append(
                    {
                        "type": "config",
                        "language": lang,
                        "content": block,
                        "index": i + 1,
                    }
                )

        # Agregar artefactos de shell
        for blocks, lang in [
            (bash_blocks, "bash"),
            (shell_blocks, "shell"),
        ]:
            for i, block in enumerate(blocks):
                artifacts.append(
                    {
                        "type": "command",
                        "language": lang,
                        "content": block,
                        "index": i + 1,
                    }
                )

        # Agregar artefactos al metadata (serializar listas como JSON)
        if python_blocks:
            metadata["python_code"] = "[see artifacts]"
        if sql_blocks:
            metadata["sql_code"] = "[see artifacts]"

        return AgentResult(
            success=True,
            content=response,
            artifacts=artifacts,
            metadata=metadata,
        )

    def _extract_code_blocks(
        self,
        text: str,
        language: str,
    ) -> list[str]:
        """
        Extrae bloques de código de un lenguaje específico.

        Args:
            text: Texto del que extraer bloques
            language: Lenguaje de programación (python, sql, yaml, etc.)

        Returns:
            Lista de bloques de código encontrados
        """
        pattern = rf"```{language}\s*\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        return [match.strip() for match in matches]

    def _infer_task_type(self, description: str) -> str:
        """
        Infiere el tipo de tarea basado en la descripción.

        Args:
            description: Descripción de la tarea

        Returns:
            Tipo de tarea inferido
        """
        description_lower = description.lower()

        type_patterns = {
            "api_creation": [
                "api",
                "endpoint",
                "rest",
                "graphql",
                "ruta",
                "route",
                "controller",
                "controlador",
                "view",
                "vista",
            ],
            "model_design": [
                "modelo",
                "model",
                "schema",
                "esquema",
                "pydantic",
                "dto",
                "entity",
                "entidad",
            ],
            "auth_implementation": [
                "autenticación",
                "authentication",
                "autorización",
                "authorization",
                "jwt",
                "oauth",
                "login",
                "session",
                "sesión",
                "password",
                "contraseña",
            ],
            "business_logic": [
                "lógica de negocio",
                "business logic",
                "servicio",
                "service",
                "use case",
                "caso de uso",
                "domain",
                "dominio",
            ],
            "database_integration": [
                "sqlalchemy",
                "orm",
                "migration",
                "migración",
                "alembic",
                "crud",
                "repository",
                "repositorio",
            ],
            "microservice": [
                "microservicio",
                "microservice",
                "grpc",
                "rpc",
                "message queue",
                "cola de mensajes",
                "event driven",
            ],
            "testing": [
                "pytest",
                "unit test",
                "test unitario",
                "integration test",
                "test de integración",
                "mock",
                "fixture",
            ],
            "security": [
                "cors",
                "csrf",
                "rate limit",
                "throttle",
                "encryption",
                "encriptación",
                "hash",
                "security",
                "seguridad",
            ],
        }

        for task_type, keywords in type_patterns.items():
            if any(kw in description_lower for kw in keywords):
                return task_type

        return "general_backend"

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
                "task_type": self._infer_task_type(task.description),
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Almacenar en memoria como conocimiento
            _ = await memory.store_knowledge(
                project_id=task.project_id if hasattr(task, "project_id") else "",
                title=f"Backend: {task.description[:80]}",
                content=result.content[:1000],  # Limitar tamaño
                tags=[memory_type, self._infer_task_type(task.description)],
                metadata=metadata,
            )

            logger.debug(
                "backend_learning_stored",
                memory_type=memory_type,
                agent=self.name,
            )

        except Exception as e:
            logger.warning(
                "backend_learning_store_failed",
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
        elif any(
            kw in description_lower
            for kw in ["anti-patrón", "antipattern", "evitar", "no hacer", "mal práctica"]
        ):
            return "anti-patterns"
        else:
            return "patterns"  # Default para Backend

    def get_framework_prompt(self, framework: str) -> str:
        """
        Genera un prompt específico para un framework.

        Args:
            framework: Nombre del framework (fastapi, django, etc.)

        Returns:
            Prompt específico del framework
        """
        framework_prompts = {
            "fastapi": """
                FastAPI específicos:
                - Usa Pydantic para schemas de request/response
                - Implementa dependency injection para servicios
                - Usa BackgroundTasks para operaciones asíncronas
                - Añale middleware para CORS, autenticación, etc.
                - Documenta con OpenAPI automáticamente
            """,
            "django": """
                Django específicos:
                - Usa Django ORM para modelos
                - Implementa views con Class-Based Views
                - Usa serializers de Django REST Framework
                - Configura middlewares apropiadamente
                - Implementa permissions personalizados
            """,
            "flask": """
                Flask específicos:
                - Usa Flask-RESTful para APIs
                - Implementa blueprints para modularidad
                - Usa Flask-SQLAlchemy para bases de datos
                - Configura error handlers
                - Usa Flask-Marshmallow para serialización
            """,
        }
        return framework_prompts.get(framework.lower(), "")

    def get_database_prompt(self, database: str) -> str:
        """
        Genera un prompt específico para una base de datos.

        Args:
            database: Nombre de la base de datos

        Returns:
            Prompt específico de la base de datos
        """
        database_prompts = {
            "postgresql": """
                PostgreSQL específicos:
                - Usa JSONB para datos semi-estructurados
                - Implementa índices apropiados
                - Usa transacciones para operaciones críticas
                - Considera connection pooling
            """,
            "mongodb": """
                MongoDB específicos:
                - Diseña schemas con embeddings vs references
                - Usa aggregation pipeline para queries complejas
                - Implementa índices compuestos
                - Considera sharding para colecciones grandes
            """,
            "redis": """
                Redis específicos:
                - Usa para caché y sessions
                - Implementa pub/sub para tiempo real
                - Usa sorted sets para rankings
                - Configura TTL apropiado
            """,
        }
        return database_prompts.get(database.lower(), "")


# Exportar clase principal
__all__ = ["BackendAgent"]
