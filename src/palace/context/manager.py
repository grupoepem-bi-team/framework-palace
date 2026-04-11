"""
Gestor de Contexto - Palace Framework

Este módulo se encarga de gestionar el contexto de proyectos y sesiones:
- Contexto por proyecto (tecnologías, decisiones arquitectónicas, reglas)
- Contexto por sesión (conversación activa, historial)
- Recuperación de contexto desde memoria vectorial (RAG)
- Aislamiento de contexto entre proyectos
- Caché de contexto para acceso rápido

Arquitectura:
    - ContextManager: Gestor principal de contexto
    - ProjectContextManager: Gestor específico por proyecto
    - SessionContextManager: Gestor de sesiones activas
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

import structlog

from palace.core.exceptions import ContextRetrievalError, ProjectNotFoundError, SessionNotFoundError
from palace.core.types import MemoryType, ProjectConfig, ProjectContext, SessionContext

if TYPE_CHECKING:
    from palace.memory.base import MemoryStore

logger = structlog.get_logger()


@dataclass
class CachedContext:
    """
    Contexto en caché para acceso rápido.

    Mantiene copias en memoria de los contextos más utilizados
    para evitar consultas repetidas a la base de datos o memoria vectorial.
    """

    project_context: Optional[ProjectContext] = None
    """Contexto del proyecto."""

    session_contexts: Dict[str, SessionContext] = field(default_factory=dict)
    """Contextos de sesión indexados por session_id."""

    key_files: Dict[str, str] = field(default_factory=dict)
    """Archivos clave del proyecto (path -> content)."""

    decisions: List[Dict[str, Any]] = field(default_factory=list)
    """Decisiones arquitectónicas cacheadas."""

    patterns: List[Dict[str, Any]] = field(default_factory=list)
    """Patrones de diseño cacheados."""

    last_updated: datetime = field(default_factory=datetime.utcnow)
    """Timestamp de última actualización."""

    ttl_seconds: int = 3600
    """Tiempo de vida del caché en segundos."""

    def is_valid(self) -> bool:
        """
        Verifica si el caché sigue siendo válido.

        Returns:
            True si el caché no ha expirado
        """
        elapsed = (datetime.utcnow() - self.last_updated).total_seconds()
        return elapsed < self.ttl_seconds

    def invalidate(self) -> None:
        """Invalida el caché."""
        self.project_context = None
        self.session_contexts.clear()
        self.key_files.clear()
        self.decisions.clear()
        self.patterns.clear()
        self.last_updated = datetime.utcnow()


class ContextManager:
    """
    Gestor principal de contexto del framework.

    Este componente es responsable de:
    - Gestionar el contexto de cada proyecto
    - Mantener sesiones activas
    - Recuperar contexto relevante desde la memoria
    - Aislar contextos entre proyectos
    - Proporcionar acceso rápido a través de caché

    El contexto se organiza en tres niveles:
    1. Proyecto: Configuración global, stack tecnológico, decisiones
    2. Sesión: Conversación activa, historial de mensajes
    3. Memoria: Contexto recuperado (ADRs, código, documentación)

    Ejemplo de uso:
        manager = ContextManager(memory_store, settings)
        await manager.initialize()

        # Obtener contexto de proyecto
        context = await manager.get_project_context("my-project")

        # Crear nueva sesión
        session = await manager.create_session("my-project")

        # Recuperar contexto relevante
        relevant_context = await manager.retrieve_context(
            project_id="my-project",
            query="endpoint REST para usuarios"
        )
    """

    def __init__(
        self,
        memory_store: "MemoryStore",
        settings: Any = None,
        cache_ttl: int = 3600,
        max_cached_projects: int = 10,
    ):
        """
        Inicializa el gestor de contexto.

        Args:
            memory_store: Almacén de memoria vectorial
            settings: Configuración del framework
            cache_ttl: Tiempo de vida del caché en segundos
            max_cached_projects: Máximo número de proyectos en caché
        """
        self._memory_store = memory_store
        self._settings = settings
        self._cache_ttl = cache_ttl
        self._max_cached_projects = max_cached_projects

        # Caché de proyectos
        self._project_cache: Dict[str, CachedContext] = {}

        # Registro de gestores por proyecto
        self._project_managers: Dict[str, "ProjectContextManager"] = {}

        # Proyecto activo por defecto
        self._active_project: Optional[str] = None

        # Inicializado
        self._initialized = False

        logger.info(
            "context_manager_created",
            cache_ttl=cache_ttl,
            max_cached_projects=max_cached_projects,
        )

    async def initialize(self) -> None:
        """
        Inicializa el gestor de contexto.

        Carga proyectos existentes y prepara el caché.
        """
        if self._initialized:
            return

        logger.info("initializing_context_manager")

        # Cargar proyectos existentes desde memoria
        await self._load_existing_projects()

        self._initialized = True
        logger.info("context_manager_initialized")

    async def _load_existing_projects(self) -> None:
        """
        Carga proyectos existentes desde la memoria.

        Busca el registro de proyectos almacenado en memoria y
        reconstruye los gestores de contexto para cada proyecto encontrado.
        Los proyectos se cargan de forma diferida (lazy) cuando se acceden
        por primera vez, pero este método pre-carga los proyectos conocidos.
        """
        try:
            # Buscar el registro global de proyectos usando un project_id especial
            registry_entries = await self._memory_store.search(
                project_id="__system__",
                query="project registry",
                memory_type=MemoryType.PROJECT,
                top_k=50,
            )

            if not registry_entries:
                logger.info("no_existing_projects_found")
                return

            # Extraer los project_ids del registro
            loaded_count = 0
            for result in registry_entries:
                metadata = result.entry.metadata
                if metadata.get("type") != "project_registry":
                    continue

                registered_ids = metadata.get("project_ids", [])
                for project_id in registered_ids:
                    try:
                        loaded = await self._load_project_from_memory(project_id)
                        if loaded:
                            loaded_count += 1
                    except Exception as e:
                        logger.warning(
                            "failed_to_preload_project",
                            project_id=project_id,
                            error=str(e),
                        )

            logger.info(
                "existing_projects_loaded",
                loaded_count=loaded_count,
            )

        except Exception as e:
            logger.warning(
                "failed_to_load_existing_projects",
                error=str(e),
            )

    # -------------------------------------------------------------------------
    # Gestión de Proyectos
    # -------------------------------------------------------------------------

    async def create_project(
        self,
        project_id: str,
        name: str,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> ProjectContext:
        """
        Crea un nuevo proyecto con su contexto.

        Args:
            project_id: ID único del proyecto
            name: Nombre del proyecto
            description: Descripción opcional
            config: Configuración inicial

        Returns:
            Contexto del proyecto creado

        Raises:
            ValidationError: Si el proyecto ya existe
        """
        logger.info(
            "creating_project",
            project_id=project_id,
            name=name,
        )

        # Crear configuración del proyecto
        project_config = ProjectConfig(
            project_id=uuid4(),
            name=name,
            description=description,
            **config or {},
        )

        # Crear contexto del proyecto
        project_context = ProjectContext(config=project_config)

        # Crear gestor específico
        manager = ProjectContextManager(
            project_id=project_id,
            project_context=project_context,
            memory_store=self._memory_store,
        )
        await manager.initialize()

        # Registrar en caché
        self._project_managers[project_id] = manager
        self._project_cache[project_id] = CachedContext(
            project_context=project_context,
            last_updated=datetime.utcnow(),
            ttl_seconds=self._cache_ttl,
        )

        # Persistir en memoria
        await self._memory_store.store(
            project_id=project_id,
            content=project_context.model_dump_json(),
            memory_type=MemoryType.PROJECT,
            metadata={"type": "project_config"},
        )

        logger.info(
            "project_created",
            project_id=project_id,
            name=name,
        )

        return project_context

    async def get_project_context(
        self,
        project_id: str,
        use_cache: bool = True,
    ) -> ProjectContext:
        """
        Obtiene el contexto de un proyecto.

        Args:
            project_id: ID del proyecto
            use_cache: Si debe usar el caché

        Returns:
            Contexto del proyecto

        Raises:
            ProjectNotFoundError: Si el proyecto no existe
        """
        # Verificar caché
        if use_cache and project_id in self._project_cache:
            cached = self._project_cache[project_id]
            if cached.is_valid() and cached.project_context:
                return cached.project_context

        # Verificar si existe el gestor
        if project_id not in self._project_managers:
            # Intentar cargar desde memoria
            loaded = await self._load_project_from_memory(project_id)
            if not loaded:
                raise ProjectNotFoundError(
                    project_id=project_id,
                    details={"available_projects": list(self._project_managers.keys())},
                )

        # Obtener del gestor
        manager = self._project_managers[project_id]
        context = await manager.get_context()

        # Actualizar caché
        if project_id not in self._project_cache:
            self._project_cache[project_id] = CachedContext(
                ttl_seconds=self._cache_ttl,
            )

        self._project_cache[project_id].project_context = context
        self._project_cache[project_id].last_updated = datetime.utcnow()

        return context

    async def _load_project_from_memory(self, project_id: str) -> bool:
        """
        Carga un proyecto desde la memoria.

        Busca la configuración del proyecto en el almacén de memoria,
        la reconstruye como un ProjectContext y registra el gestor
        correspondiente para que esté disponible para consultas futuras.

        Args:
            project_id: ID del proyecto a cargar

        Returns:
            True si se cargó exitosamente
        """
        try:
            # Evitar recarga si ya existe
            if project_id in self._project_managers:
                return True

            # Buscar configuración del proyecto en memoria
            entries = await self._memory_store.search(
                project_id=project_id,
                query="project configuration",
                memory_type=MemoryType.PROJECT,
                top_k=5,
            )

            if not entries:
                logger.debug(
                    "project_not_found_in_memory",
                    project_id=project_id,
                )
                return False

            # Buscar la entrada de configuración principal
            config_entry = None
            for result in entries:
                metadata = result.entry.metadata
                if metadata.get("type") == "project_config":
                    config_entry = result
                    break

            # Si no hay entrada etiquetada, usar la primera
            if config_entry is None:
                config_entry = entries[0]

            # Reconstruir ProjectContext desde el contenido almacenado
            import json

            content = config_entry.entry.content
            try:
                config_data = json.loads(content) if isinstance(content, str) else content
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    "invalid_project_config_json",
                    project_id=project_id,
                )
                config_data = {}

            # Reconstruir ProjectConfig y ProjectContext
            if "config" in config_data:
                config_dict = config_data["config"]
                project_config = ProjectConfig(**config_dict)
            elif "name" in config_data or "project_id" in config_data:
                project_config = ProjectConfig(**config_data)
            else:
                # Crear configuración mínima con los datos disponibles
                project_config = ProjectConfig(
                    name=config_data.get("name", project_id),
                    description=config_data.get("description"),
                    backend_framework=config_data.get("backend_framework"),
                    frontend_framework=config_data.get("frontend_framework"),
                    database=config_data.get("database"),
                    deployment=config_data.get("deployment"),
                )

            project_context = ProjectContext(config=project_config)

            # Reconstruir ADRs si existen en los datos
            if "adrs" in config_data:
                project_context.adrs = config_data["adrs"]
            if "patterns" in config_data:
                project_context.patterns = config_data["patterns"]
            if "instructions" in config_data:
                project_context.instructions = config_data["instructions"]

            # Crear gestor específico del proyecto
            manager = ProjectContextManager(
                project_id=project_id,
                project_context=project_context,
                memory_store=self._memory_store,
            )
            await manager.initialize()

            # Registrar en caché y gestores
            self._project_managers[project_id] = manager
            self._project_cache[project_id] = CachedContext(
                project_context=project_context,
                last_updated=datetime.utcnow(),
                ttl_seconds=self._cache_ttl,
            )

            logger.info(
                "project_loaded_from_memory",
                project_id=project_id,
                project_name=project_config.name,
            )

            return True

        except Exception as e:
            logger.error(
                "failed_to_load_project",
                project_id=project_id,
                error=str(e),
            )
            return False

    async def update_project_context(
        self,
        project_id: str,
        updates: Dict[str, Any],
    ) -> ProjectContext:
        """
        Actualiza el contexto de un proyecto.

        Args:
            project_id: ID del proyecto
            updates: Campos a actualizar

        Returns:
            Contexto actualizado

        Raises:
            ProjectNotFoundError: Si el proyecto no existe
        """
        # Obtener contexto actual
        context = await self.get_project_context(project_id)

        # Aplicar actualizaciones campo por campo
        config = context.config
        updatable_config_fields = {
            "name",
            "description",
            "backend_framework",
            "frontend_framework",
            "database",
            "deployment",
            "root_path",
            "source_path",
            "tests_path",
            "code_style",
            "test_framework",
        }
        for field_name, value in updates.items():
            if field_name in updatable_config_fields and hasattr(config, field_name):
                setattr(config, field_name, value)
            elif field_name == "adrs":
                context.adrs = value if isinstance(value, list) else [value]
            elif field_name == "patterns":
                context.patterns = value if isinstance(value, list) else [value]
            elif field_name == "instructions":
                context.instructions = value if isinstance(value, list) else [value]
            elif field_name == "cached_files" and isinstance(value, dict):
                context.cached_files.update(value)
            elif field_name == "active_session_id":
                context.active_session_id = value
            else:
                # Almacenar como metadato genérico en instructions
                logger.debug(
                    "unknown_update_field_stored_as_instruction",
                    field=field_name,
                    project_id=project_id,
                )
                context.instructions.append(f"{field_name}: {value}")

        # Actualizar timestamp
        context.touch()

        # Invalidar caché
        if project_id in self._project_cache:
            self._project_cache[project_id].invalidate()

        # Persistir en memoria
        await self._memory_store.store(
            project_id=project_id,
            content=context.model_dump_json(),
            memory_type=MemoryType.PROJECT,
            metadata={"type": "project_config", "action": "update"},
        )

        logger.info(
            "project_context_updated",
            project_id=project_id,
            updated_fields=list(updates.keys()),
        )

        return context

    async def delete_project(self, project_id: str) -> None:
        """
        Elimina un proyecto y todo su contexto.

        Args:
            project_id: ID del proyecto a eliminar

        Raises:
            ProjectNotFoundError: Si el proyecto no existe
        """
        # Verificar existencia
        if project_id not in self._project_managers:
            raise ProjectNotFoundError(project_id=project_id)

        # Eliminar de memoria
        await self._memory_store.delete_by_project(project_id)

        # Eliminar de caché y gestores
        if project_id in self._project_cache:
            del self._project_cache[project_id]

        if project_id in self._project_managers:
            await self._project_managers[project_id].shutdown()
            del self._project_managers[project_id]

        # Si era el proyecto activo, desactivar
        if self._active_project == project_id:
            self._active_project = None

        logger.info(
            "project_deleted",
            project_id=project_id,
        )

    def list_projects(self) -> List[str]:
        """
        Lista todos los proyectos registrados.

        Returns:
            Lista de IDs de proyectos
        """
        return list(self._project_managers.keys())

    def set_active_project(self, project_id: str) -> None:
        """
        Establece el proyecto activo.

        Args:
            project_id: ID del proyecto

        Raises:
            ProjectNotFoundError: Si el proyecto no existe
        """
        if project_id not in self._project_managers:
            raise ProjectNotFoundError(project_id=project_id)

        self._active_project = project_id
        logger.info("active_project_set", project_id=project_id)

    def get_active_project(self) -> Optional[str]:
        """
        Obtiene el proyecto activo.

        Returns:
            ID del proyecto activo o None
        """
        return self._active_project

    # -------------------------------------------------------------------------
    # Gestión de Sesiones
    # -------------------------------------------------------------------------

    async def create_session(
        self,
        project_id: str,
        session_id: Optional[str] = None,
    ) -> SessionContext:
        """
        Crea una nueva sesión para un proyecto.

        Args:
            project_id: ID del proyecto
            session_id: ID opcional de sesión

        Returns:
            Contexto de la sesión creada

        Raises:
            ProjectNotFoundError: Si el proyecto no existe
        """
        # Verificar que el proyecto existe
        if project_id not in self._project_managers:
            raise ProjectNotFoundError(project_id=project_id)

        # Crear sesión
        manager = self._project_managers[project_id]
        session = await manager.create_session(session_id)

        # Actualizar caché
        if project_id in self._project_cache:
            self._project_cache[project_id].session_contexts[str(session.session_id)] = session

        logger.info(
            "session_created",
            project_id=project_id,
            session_id=str(session.session_id),
        )

        return session

    async def get_session(
        self,
        project_id: str,
        session_id: str,
    ) -> SessionContext:
        """
        Obtiene el contexto de una sesión.

        Args:
            project_id: ID del proyecto
            session_id: ID de la sesión

        Returns:
            Contexto de la sesión

        Raises:
            ProjectNotFoundError: Si el proyecto no existe
            SessionNotFoundError: Si la sesión no existe
        """
        # Verificar caché
        if project_id in self._project_cache:
            cached = self._project_cache[project_id]
            if session_id in cached.session_contexts:
                return cached.session_contexts[session_id]

        # Obtener del gestor
        if project_id not in self._project_managers:
            raise ProjectNotFoundError(project_id=project_id)

        manager = self._project_managers[project_id]
        session = await manager.get_session(session_id)

        # Actualizar caché
        if project_id in self._project_cache:
            self._project_cache[project_id].session_contexts[session_id] = session

        return session

    async def add_message_to_session(
        self,
        project_id: str,
        session_id: str,
        role: str,
        content: str,
        agent: Optional[str] = None,
    ) -> None:
        """
        Añade un mensaje a una sesión.

        Args:
            project_id: ID del proyecto
            session_id: ID de la sesión
            role: Rol del mensaje (user, assistant, system)
            content: Contenido del mensaje
            agent: Nombre del agente (si role=assistant)

        Raises:
            SessionNotFoundError: Si la sesión no existe
        """
        manager = self._project_managers.get(project_id)
        if not manager:
            raise ProjectNotFoundError(project_id=project_id)

        await manager.add_message(
            session_id=session_id,
            role=role,
            content=content,
            agent=agent,
        )

        # Invalidar caché de sesión
        if project_id in self._project_cache:
            if session_id in self._project_cache[project_id].session_contexts:
                del self._project_cache[project_id].session_contexts[session_id]

    async def get_session_history(
        self,
        project_id: str,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de mensajes de una sesión.

        Args:
            project_id: ID del proyecto
            session_id: ID de la sesión
            limit: Límite opcional de mensajes

        Returns:
            Lista de mensajes
        """
        manager = self._project_managers.get(project_id)
        if not manager:
            raise ProjectNotFoundError(project_id=project_id)

        return await manager.get_history(session_id, limit)

    # -------------------------------------------------------------------------
    # Recuperación de Contexto (RAG)
    # -------------------------------------------------------------------------

    async def retrieve_context(
        self,
        project_id: str,
        query: str,
        top_k: int = 5,
        memory_types: Optional[List[MemoryType]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Recupera contexto relevante desde la memoria vectorial.

        Utiliza RAG (Retrieval-Augmented Generation) para encontrar
        contexto relevante basado en similitud semántica.

        Args:
            project_id: ID del proyecto
            query: Consulta para búsqueda semántica
            top_k: Número máximo de resultados
            memory_types: Tipos de memoria a buscar

        Returns:
            Lista de contextos relevantes

        Raises:
            ContextRetrievalError: Si la recuperación falla
        """
        try:
            # Preparar tipos de memoria
            types = memory_types or [
                MemoryType.SEMANTIC,  # ADRs, documentación
                MemoryType.EPISODIC,  # Conversaciones previas
                MemoryType.PROCEDURAL,  # Patrones de código
            ]

            # Realizar búsqueda en memoria
            results = []
            for mem_type in types:
                entries = await self._memory_store.search(
                    project_id=project_id,
                    query=query,
                    memory_type=mem_type,
                    top_k=top_k,
                )
                results.extend(entries)

            # Ordenar por relevancia y limitar
            results = sorted(results, key=lambda x: x.score, reverse=True)
            results = results[:top_k]

            logger.debug(
                "context_retrieved",
                project_id=project_id,
                query=query[:50],
                results_count=len(results),
            )

            return results

        except Exception as e:
            logger.error(
                "context_retrieval_failed",
                project_id=project_id,
                query=query[:50],
                error=str(e),
            )
            raise ContextRetrievalError(
                context_type="memory",
                reason=str(e),
            )

    async def store_context(
        self,
        project_id: str,
        content: str,
        memory_type: MemoryType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Almacena contexto en la memoria.

        Args:
            project_id: ID del proyecto
            content: Contenido a almacenar
            memory_type: Tipo de memoria
            metadata: Metadatos adicionales

        Returns:
            ID de la entrada almacenada
        """
        entry_id = await self._memory_store.store(
            project_id=project_id,
            content=content,
            memory_type=memory_type,
            metadata=metadata or {},
        )

        logger.debug(
            "context_stored",
            project_id=project_id,
            entry_id=entry_id,
            memory_type=memory_type.value,
        )

        return entry_id

    async def store_decision(
        self,
        project_id: str,
        decision: Dict[str, Any],
    ) -> str:
        """
        Almacena una decisión arquitectónica (ADR).

        Args:
            project_id: ID del proyecto
            decision: Diccionario con la decisión

        Returns:
            ID de la entrada almacenada
        """
        # Formatear ADR
        adr_content = f"""
# Architecture Decision Record

## Title
{decision.get("title", "Untitled Decision")}

## Status
{decision.get("status", "Proposed")}

## Context
{decision.get("context", "")}

## Decision
{decision.get("decision", "")}

## Consequences
{decision.get("consequences", "")}

## Date
{decision.get("date", datetime.utcnow().isoformat())}
"""

        entry_id = await self.store_context(
            project_id=project_id,
            content=adr_content,
            memory_type=MemoryType.SEMANTIC,
            metadata={
                "type": "adr",
                "title": decision.get("title", ""),
            },
        )

        # Invalidar caché
        if project_id in self._project_cache:
            self._project_cache[project_id].decisions.append(decision)

        return entry_id

    async def store_pattern(
        self,
        project_id: str,
        pattern: Dict[str, Any],
    ) -> str:
        """
        Almacena un patrón de código o diseño.

        Args:
            project_id: ID del proyecto
            pattern: Diccionario con el patrón

        Returns:
            ID de la entrada almacenada
        """
        entry_id = await self.store_context(
            project_id=project_id,
            content=pattern.get("content", ""),
            memory_type=MemoryType.PROCEDURAL,
            metadata={
                "type": "pattern",
                "name": pattern.get("name", ""),
                "language": pattern.get("language", ""),
            },
        )

        # Invalidar caché
        if project_id in self._project_cache:
            self._project_cache[project_id].patterns.append(pattern)

        return entry_id

    # -------------------------------------------------------------------------
    # Gestión de Caché
    # -------------------------------------------------------------------------

    def invalidate_cache(self, project_id: Optional[str] = None) -> None:
        """
        Invalida el caché de contexto.

        Args:
            project_id: ID del proyecto específico, o None para todos
        """
        if project_id:
            if project_id in self._project_cache:
                self._project_cache[project_id].invalidate()
                logger.debug("cache_invalidated", project_id=project_id)
        else:
            for cache in self._project_cache.values():
                cache.invalidate()
            logger.debug("all_cache_invalidated")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del caché.

        Returns:
            Diccionario con estadísticas
        """
        stats = {
            "cached_projects": len(self._project_cache),
            "projects": {},
        }

        for project_id, cache in self._project_cache.items():
            stats["projects"][project_id] = {
                "has_context": cache.project_context is not None,
                "sessions_cached": len(cache.session_contexts),
                "decisions_cached": len(cache.decisions),
                "patterns_cached": len(cache.patterns),
                "is_valid": cache.is_valid(),
                "last_updated": cache.last_updated.isoformat() if cache.last_updated else None,
            }

        return stats

    # -------------------------------------------------------------------------
    # Ciclo de Vida
    # -------------------------------------------------------------------------

    async def get_project_status(self, project_id: str) -> dict:
        """
        Get basic status information for a project.

        Args:
            project_id: ID of the project

        Returns:
            Dictionary with project status information

        Raises:
            ProjectNotFoundError: If the project does not exist
        """
        if project_id not in self._project_managers:
            raise ProjectNotFoundError(project_id=project_id)

        cached = self._project_cache.get(project_id)
        return {
            "project_id": project_id,
            "status": "active",
            "active_tasks": 0,
            "last_activity": cached.last_updated.isoformat() if cached else None,
            "context_summary": None,
        }

    async def shutdown(self) -> None:
        """
        Cierra el gestor de contexto de forma ordenada.

        Persiste contextos pendientes y libera recursos.
        """
        logger.info("shutting_down_context_manager")

        # Persistir contextos de todos los proyectos
        for project_id, manager in self._project_managers.items():
            try:
                await manager.shutdown()
            except Exception as e:
                logger.error(
                    "failed_to_shutdown_project_manager",
                    project_id=project_id,
                    error=str(e),
                )

        # Limpiar caché
        self._project_cache.clear()
        self._project_managers.clear()

        self._initialized = False
        logger.info("context_manager_shutdown_complete")


class ProjectContextManager:
    """
    Gestor de contexto específico para un proyecto.

    Se encarga de gestionar el contexto de un proyecto individual,
    incluyendo sus sesiones y configuración.

    Attributes:
        project_id: ID del proyecto
        project_context: Contexto del proyecto
        sessions: Diccionario de sesiones activas
    """

    def __init__(
        self,
        project_id: str,
        project_context: ProjectContext,
        memory_store: "MemoryStore",
    ):
        """
        Inicializa el gestor de contexto del proyecto.

        Args:
            project_id: ID del proyecto
            project_context: Contexto inicial del proyecto
            memory_store: Almacén de memoria
        """
        self.project_id = project_id
        self._project_context = project_context
        self._memory_store = memory_store
        self._sessions: Dict[str, SessionContext] = {}
        self._active_session: Optional[str] = None

    async def initialize(self) -> None:
        """Inicializa el gestor del proyecto."""
        logger.debug(
            "project_manager_initialized",
            project_id=self.project_id,
        )

    async def get_context(self) -> ProjectContext:
        """
        Obtiene el contexto actual del proyecto.

        Returns:
            Contexto del proyecto
        """
        return self._project_context

    async def create_session(
        self,
        session_id: Optional[str] = None,
    ) -> SessionContext:
        """
        Crea una nueva sesión.

        Args:
            session_id: ID opcional de la sesión

        Returns:
            Contexto de la sesión creada
        """
        session = SessionContext(
            session_id=uuid4() if not session_id else UUID(session_id),
            project_id=self._project_context.config.project_id,
        )

        self._sessions[str(session.session_id)] = session
        self._active_session = str(session.session_id)

        return session

    async def get_session(self, session_id: str) -> SessionContext:
        """
        Obtiene una sesión existente.

        Args:
            session_id: ID de la sesión

        Returns:
            Contexto de la sesión

        Raises:
            SessionNotFoundError: Si la sesión no existe
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(
                session_id=session_id,
                project_id=self.project_id,
            )

        return self._sessions[session_id]

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent: Optional[str] = None,
    ) -> None:
        """
        Añade un mensaje a una sesión.

        Args:
            session_id: ID de la sesión
            role: Rol del mensaje
            content: Contenido
            agent: Nombre del agente (opcional)
        """
        session = await self.get_session(session_id)

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if agent:
            message["agent"] = agent

        session.messages.append(message)
        session.updated_at = datetime.utcnow()

    async def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de una sesión.

        Args:
            session_id: ID de la sesión
            limit: Límite opcional de mensajes

        Returns:
            Lista de mensajes
        """
        session = await self.get_session(session_id)
        messages = session.messages

        if limit:
            messages = messages[-limit:]

        return messages

    async def shutdown(self) -> None:
        """Cierra el gestor del proyecto."""
        logger.debug(
            "project_manager_shutdown",
            project_id=self.project_id,
        )


# Exportar clases principales
__all__ = [
    "ContextManager",
    "ProjectContextManager",
    "CachedContext",
]
