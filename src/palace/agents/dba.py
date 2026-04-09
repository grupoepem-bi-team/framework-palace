"""
Agente DBA (Database Administrator) - Palace Framework

Este agente se especializa en diseño, optimización y administración de bases de datos, incluyendo:
- Diseño de esquemas y modelado de datos
- Optimización de consultas y índices
- Migraciones y versionado de esquemas
- Seguridad y permisos de bases de datos
- Resolución de problemas de rendimiento
- Configuración de replicación y alta disponibilidad

Modelo asignado: deepseek-v3.2
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import structlog

from palace.agents.base import AgentBase, AgentResult, AgentState, Task
from palace.core.types import AgentCapability, AgentRole, TaskStatus

if TYPE_CHECKING:
    from palace.context import SessionContext
    from palace.llm import LLMClient
    from palace.memory import MemoryStore

logger = structlog.get_logger()


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class DBACapabilities:
    """Capacidades específicas del agente DBA."""

    databases: List[str] = field(
        default_factory=lambda: [
            "postgresql",
            "mysql",
            "mariadb",
            "sqlite",
            "mongodb",
            "redis",
            "elasticsearch",
            "cassandra",
            "cockroachdb",
        ]
    )
    """Bases de datos soportadas."""

    orms: List[str] = field(
        default_factory=lambda: [
            "sqlalchemy",
            "django_orm",
            "prisma",
            "sequelize",
            "typeorm",
            "mongoose",
        ]
    )
    """ORMs y ODMs soportados."""

    migration_tools: List[str] = field(
        default_factory=lambda: [
            "alembic",
            "flyway",
            "liquibase",
            "django_migrations",
            "prisma_migrate",
            "knex",
        ]
    )
    """Herramientas de migración soportadas."""

    task_types: List[str] = field(
        default_factory=lambda: [
            "schema_design",
            "query_optimization",
            "index_optimization",
            "migration_creation",
            "performance_tuning",
            "backup_recovery",
            "security_hardening",
            "replication_setup",
            "monitoring_setup",
            "data_modeling",
        ]
    )
    """Tipos de tareas que puede manejar."""


@dataclass
class SchemaDesign:
    """Resultado de diseño de esquema."""

    tables: List[Dict[str, Any]] = field(default_factory=list)
    """Definición de tablas."""

    indexes: List[Dict[str, Any]] = field(default_factory=list)
    """Índices propuestos."""

    constraints: List[Dict[str, Any]] = field(default_factory=list)
    """Constraints definidos."""

    relationships: List[Dict[str, Any]] = field(default_factory=list)
    """Relaciones entre tablas."""

    sql_ddl: str = ""
    """Script DDL completo."""


@dataclass
class QueryOptimization:
    """Resultado de optimización de consulta."""

    original_query: str = ""
    """Consulta original."""

    optimized_query: str = ""
    """Consulta optimizada."""

    explanation: str = ""
    """Explicación de la optimización."""

    indexes_needed: List[str] = field(default_factory=list)
    """Índices necesarios."""

    estimated_improvement: str = ""
    """Mejora estimada."""


@dataclass
class MigrationScript:
    """Script de migración generado."""

    up_script: str = ""
    """Script para aplicar la migración."""

    down_script: str = ""
    """Script para revertir la migración."""

    description: str = ""
    """Descripción de la migración."""

    version: str = ""
    """Versión de la migración."""

    is_idempotent: bool = False
    """Si la migración es idempotente."""


# =============================================================================
# Palabras clave para detección de tareas
# =============================================================================

DBA_KEYWORDS = [
    # Esquemas y tablas
    "schema",
    "esquema",
    "tabla",
    "table",
    "modelo",
    "model",
    "entidad",
    "entity",
    "relación",
    "relation",
    "foreign key",
    "primary key",
    "constraint",
    "índice",
    "index",
    # Consultas
    "query",
    "consulta",
    "sql",
    "select",
    "join",
    "subquery",
    "optimizar",
    "optimize",
    "explain",
    "analyze",
    "plan de ejecución",
    # Migraciones
    "migración",
    "migration",
    "alembic",
    "flyway",
    "migrate",
    "rollback",
    "versionado",
    "schema version",
    # Bases de datos específicas
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "sqlite",
    "elasticsearch",
    "cassandra",
    "cockroachdb",
    "mariadb",
    # Operaciones DBA
    "backup",
    "restore",
    "replicación",
    "replication",
    "partición",
    "partition",
    "sharding",
    "cluster",
    "rendimiento",
    "performance",
    "tuning",
    "connection pool",
    "índice",
    "index",
    "btree",
    "hash index",
    "gin",
    "gist",
    # Seguridad
    "permisos",
    "permissions",
    "roles",
    "grant",
    "revoke",
    "encriptación",
    "encryption",
    "audit",
    "auditoría",
    # ORMs
    "orm",
    "sqlalchemy",
    "prisma",
    "sequelize",
    "mongoose",
    "odm",
    "django orm",
]


# =============================================================================
# DBA Agent
# =============================================================================


class DBAAgent(AgentBase):
    """
    Agente especializado en administración y diseño de bases de datos.

    Este agente maneja todas las tareas relacionadas con:
    - Diseño de esquemas de bases de datos
    - Optimización de consultas SQL/NoSQL
    - Creación y gestión de migraciones
    - Configuración de índices y particiones
    - Seguridad y control de acceso
    - Monitoreo y resolución de problemas de rendimiento
    - Configuración de replicación y alta disponibilidad

    Modelo: deepseek-v3.2 (especializado en razonamiento y optimización)
    Capacidades: DATABASE_ADMINISTRATION, INFRASTRUCTURE_AS_CODE

    Ejemplo de uso:
        agent = DBAAgent(llm_client=client)
        result = await agent.run(task, context, memory)
    """

    name: str = "dba"
    role: AgentRole = AgentRole.DBA
    model: str = "deepseek-v3.2"
    description: str = (
        "Agente especializado en administración de bases de datos. "
        "Diseña esquemas optimizados, crea migraciones, optimiza consultas, "
        "configura seguridad y resuelve problemas de rendimiento."
    )

    capabilities: List[AgentCapability] = [
        AgentCapability.DATABASE_ADMINISTRATION,
        AgentCapability.INFRASTRUCTURE_AS_CODE,
    ]

    tools: List[str] = [
        "shell",
        "file_read",
        "file_write",
        "sql_client",
        "migration_tool",
        "explain_analyzer",
        "monitoring_tool",
    ]

    # Capacidades específicas del agente
    dba_capabilities: DBACapabilities = field(default_factory=DBACapabilities)

    system_prompt: str = """Eres un administrador de bases de datos senior especializado en diseño, optimización y gestión de bases de datos.

Tu expertise incluye:

1. Diseño de esquemas:
   - Normalización (1NF, 2NF, 3NF, BCNF)
   - Denormalización estratégica para rendimiento
   - Modelado relacional y NoSQL
   - Diseño de esquemas para escalabilidad

2. Optimización de consultas:
   - Análisis de planes de ejecución (EXPLAIN ANALYZE)
   - Creación de índices apropiados (B-tree, hash, GIN, GiST)
   - Optimización de JOINs y subqueries
   - Uso de particiones y table spaces

3. Migraciones y versionado:
   - Creación de migraciones rollback-safe
   - Versionado de esquemas con Alembic, Flyway, Liquibase
   - Migraciones zero-downtime
   - Scripts de migración idempotentes

4. Seguridad:
   - Principio de menor privilegio
   - Encriptación en reposo y en tránsito
   - Auditoría y logging
   - Protección contra SQL injection

5. Rendimiento:
   - Monitorización de métricas (throughput, latency, error rates)
   - Tuning de configuración del motor de base de datos
   - Connection pooling y gestión de conexiones
   - Caching estratégico

6. Alta disponibilidad:
   - Configuración de replicación (master-slave, multi-master)
   - Failover automático
   - Backups y recovery procedures
   - Disaster recovery planning

Bases de datos que manejas:
- PostgreSQL (avanzado: extensions, partitioning, FDW)
- MySQL/MariaDB (optimización InnoDB, replicación)
- MongoDB (aggregations, sharding, índices compuestos)
- Redis (estructuras de datos, persistence, clustering)
- SQLite (embedded, aplicaciones móviles)
- Elasticsearch (full-text search, aggregations)

Principios de diseño que sigues:
1. ACID compliance cuando es necesario
2. Consistency vs Availability tradeoffs según requirements
3. Escalabilidad horizontal y vertical
4. Maintainability y documentación
5. Observabilidad y monitorización

Cuando generes código SQL o scripts:
- Incluye comentarios explicando decisiones de diseño
- Considera el volumen de datos esperado
- Optimiza para patrones de acceso comunes
- Incluye índices apropiados para queries frecuentes
- Considera security implications

Cuando diseñes esquemas:
- Define constraints (PK, FK, UNIQUE, CHECK)
- Especifica tipos de datos apropiados
- Considera futuros cambios (extension points)
- Documenta relaciones y business logic
- Incluye ejemplos de queries comunes

Formato de respuesta:
1. Explica tu enfoque y reasoning
2. Proporciona código SQL/NoSQL completo
3. Incluye migraciones si son necesarias
4. Sugiere índices y optimizaciones
5. Menciona consideraciones de seguridad
6. Proporciona comandos para implementación

Responde siempre en el idioma del usuario."""

    def __init__(
        self,
        llm_client: "LLMClient",
        capabilities: Optional[DBACapabilities] = None,
        tools: Optional[List[str]] = None,
    ):
        """
        Inicializa el agente DBA.

        Args:
            llm_client: Cliente LLM para invocar modelos
            capabilities: Capacidades específicas del DBA (opcional)
            tools: Herramientas disponibles (opcional)
        """
        super().__init__(
            name=self.name,
            role=self.role,
            model=self.model,
            llm_client=llm_client,
            tools=tools or self.tools,
        )
        self.dba_capabilities = capabilities or DBACapabilities()

    # =========================================================================
    # Métodos abstractos de AgentBase
    # =========================================================================

    def _build_system_prompt(self) -> str:
        """
        Construye el prompt del sistema para el agente DBA.

        Returns:
            Prompt del sistema como cadena
        """
        return self.system_prompt

    async def run(
        self,
        task: Task,
        context: "SessionContext",
        memory: "MemoryStore",
    ) -> AgentResult:
        """
        Ejecuta una tarea de administración de bases de datos.

        Flujo de ejecución:
        1. Recuperar contexto relevante de memoria
        2. Analizar la tarea y determinar tipo
        3. Generar solución (esquema, consultas, migraciones)
        4. Validar con mejores prácticas
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
            "dba_task_started",
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

            # Paso 3: Invocar LLM con temperatura baja para precisión
            response = await self.invoke_llm(
                prompt=prompt,
                temperature=0.1,  # Baja temperatura para respuestas precisas
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
                "dba_task_completed",
                success=result.success,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent=self.name,
            )

            return result

        except Exception as e:
            self.state = AgentState.ERROR
            logger.exception(
                "dba_task_failed",
                error=str(e),
                agent=self.name,
            )

            return AgentResult(
                success=False,
                content="",
                error=f"DBA task failed: {str(e)}",
                metadata={"task": task.description, "agent": self.name},
            )

    def can_handle(self, task: Task) -> bool:
        """
        Determina si este agente puede manejar la tarea.

        Evalúa si la tarea está relacionada con:
        - Diseño y administración de bases de datos
        - Optimización de consultas SQL/NoSQL
        - Creación de migraciones
        - Configuración de índices y particiones
        - Seguridad de bases de datos
        - Resolución de problemas de rendimiento de DB

        Args:
            task: Tarea a evaluar

        Returns:
            True si el agente puede manejar la tarea
        """
        if not task.description:
            return False

        description_lower = task.description.lower()

        # Verificar palabras clave de DBA
        keyword_matches = sum(1 for keyword in DBA_KEYWORDS if keyword in description_lower)

        # Si hay al menos 2 coincidencias de keywords, probablemente es tarea de DBA
        if keyword_matches >= 2:
            return True

        # Verificar patrones SQL
        sql_patterns = [
            r"\bSELECT\b.*\bFROM\b",
            r"\bCREATE\s+TABLE\b",
            r"\bALTER\s+TABLE\b",
            r"\bDROP\s+TABLE\b",
            r"\bINSERT\s+INTO\b",
            r"\bUPDATE\b.*\bSET\b",
            r"\bDELETE\s+FROM\b",
            r"\bCREATE\s+INDEX\b",
            r"\bJOIN\b",
        ]
        for pattern in sql_patterns:
            if re.search(pattern, description_lower, re.IGNORECASE):
                return True

        # Si solo hay 1 coincidencia, verificar que no sea ambigua
        if keyword_matches == 1:
            # Palabras que por sí solas indican fuertemente tarea de DBA
            strong_indicators = [
                "sql",
                "migration",
                "migración",
                "schema",
                "esquema",
                "alembic",
                "flyway",
                "postgresql",
                "mongodb",
                "mysql",
                "database",
                "base de datos",
                "dba",
                "orm",
                "query",
                "consulta",
                "índice",
                "index",
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
        - Esquemas de bases de datos existentes
        - Patrones de consultas previos
        - Migraciones anteriores
        - Problemas y soluciones de rendimiento

        Args:
            task: Tarea actual
            memory: Almacén de memoria

        Returns:
            Contexto relevante como cadena
        """
        try:
            # Buscar en memoria por tipos relevantes
            results = await memory.search(
                query=task.description,
                filters={
                    "type": [
                        "database_schema",
                        "query_pattern",
                        "migration",
                        "optimization",
                        "error",
                        "solution",
                    ]
                },
                limit=5,
            )

            if not results:
                return ""

            # Formatear contexto recuperado
            context_parts = []
            for result in results:
                context_parts.append(
                    f"- [{result.get('type', 'unknown')}] {result.get('content', '')}"
                )

            return "\n".join(context_parts)

        except Exception as e:
            logger.warning(
                "dba_context_retrieval_failed",
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
            "1. **Enfoque**: Explica tu razonamiento\n"
            "2. **Código**: SQL/NoSQL/migraciones completos\n"
            "3. **Índices**: Índices sugeridos\n"
            "4. **Seguridad**: Consideraciones de seguridad\n"
            "5. **Implementación**: Comandos para ejecutar"
        )

        return "\n".join(prompt_parts)

    def _process_response(
        self,
        response: str,
        task: Task,
    ) -> AgentResult:
        """
        Procesa la respuesta del LLM y genera el resultado.

        Extrae artefactos de la respuesta (SQL, migraciones, etc.)
        y los organiza en el resultado.

        Args:
            response: Respuesta del LLM
            task: Tarea original

        Returns:
            AgentResult con el resultado procesado
        """
        # Extraer bloques de código SQL
        sql_blocks = self._extract_code_blocks(response, "sql")

        # Extraer bloques de código Python (para migraciones Alembic)
        python_blocks = self._extract_code_blocks(response, "python")

        # Determinar tipo de resultado basado en la tarea
        task_type = self._infer_task_type(task.description)

        # Construir metadata del resultado
        metadata = {
            "agent": self.name,
            "model": self.model,
            "task_type": task_type,
            "sql_artifacts": len(sql_blocks),
            "python_artifacts": len(python_blocks),
        }

        # Agregar artefactos al metadata
        if sql_blocks:
            metadata["sql_code"] = sql_blocks
        if python_blocks:
            metadata["python_code"] = python_blocks

        return AgentResult(
            success=True,
            content=response,
            metadata=metadata,
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
            language: Lenguaje de programación (sql, python, etc.)

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
            "schema_design": ["schema", "esquema", "tabla", "table", "modelo", "model"],
            "query_optimization": [
                "optimizar",
                "optimize",
                "query",
                "consulta",
                "explain",
                "lento",
            ],
            "migration": ["migración", "migration", "alembic", "flyway", "migrate"],
            "index_optimization": ["índice", "index", "btree", "gin", "gist"],
            "security": ["seguridad", "security", "permisos", "permissions", "roles"],
            "performance": ["rendimiento", "performance", "tuning", "lento", "slow"],
            "replication": ["replicación", "replication", "cluster", "failover"],
            "backup": ["backup", "copia", "restore", "recovery"],
        }

        for task_type, keywords in type_patterns.items():
            if any(kw in description_lower for kw in keywords):
                return task_type

        return "general_dba"

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

            # Almacenar en memoria
            await memory.add(
                text=result.content[:1000],  # Limitar tamaño
                metadata=metadata,
                memory_type=memory_type,
            )

            logger.debug(
                "dba_learning_stored",
                memory_type=memory_type,
                agent=self.name,
            )

        except Exception as e:
            logger.warning(
                "dba_learning_store_failed",
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

        if any(kw in description_lower for kw in ["error", "fallo", "falló", "failed"]):
            return "errors"
        elif any(kw in description_lower for kw in ["solución", "solution", "resolver", "fix"]):
            return "solutions"
        elif any(kw in description_lower for kw in ["config", "configuración", "setup"]):
            return "configs"
        elif any(
            kw in description_lower
            for kw in ["patrón", "pattern", "mejor práctica", "best practice"]
        ):
            return "patterns"
        elif any(
            kw in description_lower for kw in ["anti-patrón", "antipattern", "evitar", "no hacer"]
        ):
            return "anti-patterns"
        else:
            return "patterns"  # Default para DBA

    # =========================================================================
    # Métodos de utilidad para generación de prompts específicos
    # =========================================================================

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
- Implementa índices GIN/GiST para búsquedas avanzadas
- Usa partitioning para tablas grandes
- Considera extensiones (pg_trgm, hstore, postgis)
- Usa CTEs para consultas complejas
- Implementa Row Level Security (RLS) si es necesario
- Considera Logical Replication para casos específicos
""",
            "mysql": """
MySQL/MariaDB específicos:
- Optimiza InnoDB buffer pool size
- Usa índices compuestos para queries frecuentes
- Implementa partitioning para tablas grandes
- Configura replication filters si es necesario
- Usa EXPLAIN para análisis de queries
- Considera MariaDB para features avanzados (ColumnStore)
""",
            "mongodb": """
MongoDB específicos:
- Diseña schemas con embeddings vs references
- Usa aggregation pipeline para queries complejas
- Implementa índices compuestos y de texto
- Considera sharding para colecciones grandes
- Usa Change Streams para real-time
- Implementa TTL indexes para datos temporales
""",
            "redis": """
Redis específicos:
- Usa para caché y sessions con TTL apropiado
- Implementa pub/sub para eventos en tiempo real
- Usa sorted sets para rankings y leaderboards
- Considera Redis Cluster para alta disponibilidad
- Implementa Lua scripts para operaciones atómicas
- Usa Redis Streams para message queuing
""",
            "sqlite": """
SQLite específicos:
- Ideal para aplicaciones embebidas y móviles
- Usa WAL mode para mejor concurrencia
- Implementa PRAGMAs para optimización
- Considera migrar a PostgreSQL para producción a escala
- Usa FTS5 para búsquedas de texto completo
- Implementa transactions para operaciones batch
""",
            "elasticsearch": """
Elasticsearch específicos:
- Diseña mappings con tipos apropiados
- Usa aggregations para análisis
- Implementa analyzers personalizados
- Considera index lifecycle management (ILM)
- Usa aliases para zero-downtime reindexing
- Implementa sharding strategy apropiada
""",
        }
        return database_prompts.get(database.lower(), "")

    def get_orm_prompt(self, orm: str) -> str:
        """
        Genera un prompt específico para un ORM.

        Args:
            orm: Nombre del ORM

        Returns:
            Prompt específico del ORM
        """
        orm_prompts = {
            "sqlalchemy": """
SQLAlchemy específicos:
- Usa declarative base para modelos
- Implementa relationships con lazy loading apropiado
- Usa Alembic para migraciones
- Implementa sessions con context managers
- Usa hybrid properties para lógica de negocio
- Considera async SQLAlchemy para alta concurrencia
""",
            "django_orm": """
Django ORM específicos:
- Define modelos con fields apropiados
- Usa migrations para control de esquema
- Implementa related_name para relaciones inversas
- Usa select_related/prefetch_related para optimizar queries
- Considera django-extensions para funcionalidades adicionales
- Usa database routers para multi-database
""",
            "prisma": """
Prisma específicos:
- Define schema.prisma con modelos y relaciones
- Usa Prisma Migrate para migraciones
- Implementa Prisma Client para queries tipadas
- Usa transactions para operaciones atómicas
- Considera Prisma Studio para visualización de datos
- Implementa middleware para logging
""",
        }
        return orm_prompts.get(orm.lower(), "")


# Exportar clase principal
__all__ = ["DBAAgent", "DBACapabilities", "SchemaDesign", "QueryOptimization", "MigrationScript"]
