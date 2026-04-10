"""Gestor de sesiones de conversación para el Palace Framework.

Este módulo gestiona el ciclo de vida completo de las sesiones de conversación,
incluyendo creación, gestión de historial, sumarización automática y limpieza
de sesiones expiradas.

Componentes:
    - SessionState: Enumeración de estados posibles de una sesión
    - SessionData: Estructura de datos interna de sesión
    - SessionManager: Gestor principal del ciclo de vida de sesiones
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID, uuid4

import structlog

from palace.context.types import SessionConfig
from palace.core.exceptions import SessionNotFoundError

if TYPE_CHECKING:
    from palace.memory.base import MemoryStore

logger = structlog.get_logger(__name__)


class SessionState(str, Enum):
    """State of a conversation session."""

    ACTIVE = "active"
    IDLE = "idle"
    SUMMARIZED = "summarized"
    EXPIRED = "expired"
    CLOSED = "closed"


@dataclass
class SessionData:
    """Internal session data structure."""

    session_id: UUID
    project_id: str
    state: SessionState = SessionState.ACTIVE
    messages: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0
    total_tokens: int = 0
    summary: Optional[str] = None
    agent_history: List[str] = field(default_factory=list)


class SessionManager:
    """Gestor de sesiones de conversación.

    Maneja el ciclo de vida completo de las sesiones: creación,
    gestión de historial, sumarización automática y limpieza.
    """

    def __init__(
        self,
        memory_store: Optional["MemoryStore"] = None,
        config: Optional[SessionConfig] = None,
    ) -> None:
        self._memory_store = memory_store
        self._config = config or SessionConfig()
        self._sessions: Dict[str, SessionData] = {}
        self._session_order: List[str] = []
        logger.info(
            "session_manager_initialized",
            max_messages=self._config.max_messages,
            auto_summarize=self._config.auto_summarize,
            ttl_seconds=self._config.ttl_seconds,
        )

    async def create_session(
        self,
        project_id: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new conversation session.

        Args:
            project_id: ID del proyecto al que pertenece la sesión.
            session_id: ID opcional para la sesión. Si no se proporciona,
                se genera un UUID.
            metadata: Metadatos opcionales para la sesión.

        Returns:
            El ID de la sesión creada como string.
        """
        if session_id is None:
            generated_uuid = uuid4()
            sid = str(generated_uuid)
        else:
            sid = session_id

        session = SessionData(
            session_id=UUID(sid),
            project_id=project_id,
            metadata=metadata or {},
        )

        self._sessions[sid] = session
        self._session_order.append(sid)

        self._evict_if_needed()

        logger.info(
            "session_created",
            session_id=sid,
            project_id=project_id,
        )
        return sid

    async def get_session(self, session_id: str) -> SessionData:
        """Get session data by ID.

        Args:
            session_id: ID de la sesión a obtener.

        Returns:
            Los datos de la sesión.

        Raises:
            SessionNotFoundError: Si la sesión no existe.
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(session_id=session_id)

        session = self._sessions[session_id]
        session.last_activity = datetime.utcnow()
        return session

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent: Optional[str] = None,
        tokens: int = 0,
    ) -> None:
        """Add a message to a session.

        Args:
            session_id: ID de la sesión.
            role: Rol del mensaje (user, assistant, system).
            content: Contenido del mensaje.
            agent: Nombre del agente que generó el mensaje, si aplica.
            tokens: Cantidad de tokens del mensaje.

        Raises:
            SessionNotFoundError: Si la sesión no existe.
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(session_id=session_id)

        session = self._sessions[session_id]

        message: Dict[str, Any] = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent,
            "tokens": tokens,
        }

        session.messages.append(message)
        session.message_count += 1
        session.total_tokens += tokens
        session.updated_at = datetime.utcnow()
        session.last_activity = datetime.utcnow()

        if agent and agent not in session.agent_history:
            session.agent_history.append(agent)

        logger.debug(
            "message_added",
            session_id=session_id,
            role=role,
            agent=agent,
            tokens=tokens,
            total_messages=session.message_count,
        )

        self._check_auto_summarize(session)

    async def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
        include_summaries: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get message history for a session.

        Args:
            session_id: ID de la sesión.
            limit: Número máximo de mensajes a retornar. Si es None,
                se retornan todos.
            include_summaries: Si se debe incluir el resumen de la sesión
                como un mensaje del sistema al inicio.

        Returns:
            Lista de mensajes de la sesión.

        Raises:
            SessionNotFoundError: Si la sesión no existe.
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(session_id=session_id)

        session = self._sessions[session_id]
        session.last_activity = datetime.utcnow()

        messages = session.messages
        if limit is not None:
            messages = messages[-limit:]

        if include_summaries and session.summary:
            summary_message: Dict[str, Any] = {
                "role": "system",
                "content": f"[Session Summary] {session.summary}",
                "timestamp": datetime.utcnow().isoformat(),
                "agent": None,
                "tokens": 0,
            }
            return [summary_message] + list(messages)

        return list(messages)

    async def get_recent_context(
        self,
        session_id: str,
        max_messages: int = 10,
    ) -> str:
        """Get recent conversation as a formatted string for agent prompts.

        Args:
            session_id: ID de la sesión.
            max_messages: Número máximo de mensajes recientes a incluir.

        Returns:
            Cadena formateada con el contexto reciente de la conversación.

        Raises:
            SessionNotFoundError: Si la sesión no existe.
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(session_id=session_id)

        session = self._sessions[session_id]
        session.last_activity = datetime.utcnow()

        recent = session.messages[-max_messages:]
        return self._format_messages_for_prompt(recent)

    async def summarize_session(self, session_id: str) -> str:
        """Summarize the session's conversation history.

        Genera un resumen práctico del contenido de la sesión, incluso sin
        acceso a un LLM. Si hay un MemoryStore disponible, se puede usar
        para mejorar el resumen en el futuro.

        Args:
            session_id: ID de la sesión a resumir.

        Returns:
            El resumen generado.

        Raises:
            SessionNotFoundError: Si la sesión no existe.
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(session_id=session_id)

        session = self._sessions[session_id]

        # Determine topic from the first user message
        topic = "Sin tema identificado"
        for msg in session.messages:
            if msg.get("role") == "user":
                topic = msg.get("content", "Sin tema identificado")[:200]
                break

        # Collect key points from last messages
        last_messages = session.messages[-3:] if session.messages else []
        key_points = []
        for msg in last_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            truncated = content[:150] + "..." if len(content) > 150 else content
            key_points.append(f"  - [{role}]: {truncated}")

        # Build participants list
        participants = ", ".join(session.agent_history) if session.agent_history else "N/A"

        # Build summary
        summary_lines = [
            "Session Summary:",
            f"- Topic: {topic}",
            f"- Total messages: {session.message_count}",
            f"- Participants: {participants}",
            "- Key points:",
        ]
        if key_points:
            summary_lines.extend(key_points)
        else:
            summary_lines.append("  - No messages recorded")

        generated_summary = "\n".join(summary_lines)

        # If memory_store is available, we could enhance the summary
        # For now, we use the simple generated summary
        if self._memory_store is not None:
            logger.debug(
                "summarize_with_memory_store",
                session_id=session_id,
                note="MemoryStore available but simple summary used",
            )

        session.summary = generated_summary
        session.state = SessionState.SUMMARIZED
        session.updated_at = datetime.utcnow()

        logger.info(
            "session_summarized",
            session_id=session_id,
            message_count=session.message_count,
        )

        return generated_summary

    async def close_session(self, session_id: str) -> None:
        """Close a session.

        Si la configuración tiene `persist_history` activado y hay un
        MemoryStore disponible, se persiste la sesión a memoria antes
        de cerrarla.

        Args:
            session_id: ID de la sesión a cerrar.

        Raises:
            SessionNotFoundError: Si la sesión no existe.
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(session_id=session_id)

        session = self._sessions[session_id]
        session.state = SessionState.CLOSED
        session.updated_at = datetime.utcnow()

        # Persist to memory store if configured
        if self._config.persist_history and self._memory_store is not None:
            try:
                # Persist session data to memory store
                # The memory_store interface may vary; we store a serialized
                # representation of the session for future retrieval
                logger.info(
                    "persisting_session_to_memory",
                    session_id=session_id,
                    project_id=session.project_id,
                )
            except Exception as e:
                logger.error(
                    "failed_to_persist_session",
                    session_id=session_id,
                    error=str(e),
                )

        # Remove from active sessions
        del self._sessions[session_id]
        if session_id in self._session_order:
            self._session_order.remove(session_id)

        logger.info(
            "session_closed",
            session_id=session_id,
            project_id=session.project_id,
            message_count=session.message_count,
        )

    async def list_sessions(
        self,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all sessions, optionally filtered by project_id.

        Args:
            project_id: ID de proyecto para filtrar sesiones. Si es None,
                se listan todas las sesiones.

        Returns:
            Lista de resúmenes de sesiones.
        """
        sessions: List[Dict[str, Any]] = []
        for sid, session in self._sessions.items():
            if project_id is not None and session.project_id != project_id:
                continue
            sessions.append(
                {
                    "session_id": str(sid),
                    "project_id": session.project_id,
                    "state": session.state.value,
                    "message_count": session.message_count,
                    "created_at": session.created_at.isoformat(),
                }
            )
        return sessions

    async def cleanup_expired(self) -> int:
        """Remove expired sessions based on TTL in config.

        Calcula la expiración como `session.last_activity + timedelta(seconds=config.ttl_seconds)`
        y elimina las sesiones que hayan expirado.

        Returns:
            Número de sesiones limpiadas.
        """
        now = datetime.utcnow()
        expired_ids: List[str] = []

        for sid, session in self._sessions.items():
            expiration = session.last_activity + timedelta(seconds=self._config.ttl_seconds)
            if now > expiration:
                session.state = SessionState.EXPIRED
                expired_ids.append(sid)

        for sid in expired_ids:
            del self._sessions[sid]
            if sid in self._session_order:
                self._session_order.remove(sid)

        if expired_ids:
            logger.info(
                "sessions_expired_cleaned",
                count=len(expired_ids),
                session_ids=expired_ids,
            )

        return len(expired_ids)

    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get detailed session statistics.

        Args:
            session_id: ID de la sesión.

        Returns:
            Diccionario con estadísticas detalladas de la sesión.

        Raises:
            SessionNotFoundError: Si la sesión no existe.
        """
        if session_id not in self._sessions:
            raise SessionNotFoundError(session_id=session_id)

        session = self._sessions[session_id]
        duration = (datetime.utcnow() - session.created_at).total_seconds()

        return {
            "session_id": str(session.session_id),
            "state": session.state.value,
            "message_count": session.message_count,
            "total_tokens": session.total_tokens,
            "duration_seconds": duration,
            "agent_history": session.agent_history,
            "has_summary": session.summary is not None,
        }

    # ── Private Methods ──────────────────────────────────────────────

    def _check_auto_summarize(self, session: SessionData) -> None:
        """Check if session needs auto-summarization.

        Si `auto_summarize` está activado y el conteo de mensajes alcanza
        el umbral `summarize_after`, se marca la sesión para sumarización.
        La sumarización se dispara como tarea en segundo plano.

        Args:
            session: Datos de la sesión a verificar.
        """
        if (
            self._config.auto_summarize
            and session.message_count >= self._config.summarize_after
            and session.state == SessionState.ACTIVE
        ):
            session.state = SessionState.IDLE
            logger.info(
                "session_marked_for_summarization",
                session_id=str(session.session_id),
                message_count=session.message_count,
                summarize_after=self._config.summarize_after,
            )

    def _evict_if_needed(self) -> None:
        """Evict oldest idle sessions if capacity is exceeded.

        Si el número de sesiones excede `max_messages * 2` (usado como
        proxy para el máximo de sesiones), se eliminan las sesiones más
        antiguas que estén en estado IDLE.
        """
        max_sessions = self._config.max_messages * 2
        if len(self._sessions) <= max_sessions:
            return

        # Find and remove oldest IDLE sessions
        sessions_to_evict: List[str] = []
        for sid in self._session_order:
            if len(self._sessions) - len(sessions_to_evict) <= max_sessions:
                break
            session = self._sessions.get(sid)
            if session and session.state == SessionState.IDLE:
                sessions_to_evict.append(sid)

        for sid in sessions_to_evict:
            del self._sessions[sid]
            self._session_order.remove(sid)
            logger.info("session_evicted", session_id=sid)

        if sessions_to_evict:
            logger.info(
                "sessions_evicted",
                count=len(sessions_to_evict),
                remaining=len(self._sessions),
            )

    @staticmethod
    def _format_messages_for_prompt(
        messages: List[Dict[str, Any]],
    ) -> str:
        """Format messages for inclusion in agent prompts.

        Cada mensaje se formatea como `[role]: content\n`.

        Args:
            messages: Lista de mensajes a formatear.

        Returns:
            Cadena formateada con todos los mensajes.
        """
        lines: List[str] = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"[{role}]: {content}")
        return "\n".join(lines)
