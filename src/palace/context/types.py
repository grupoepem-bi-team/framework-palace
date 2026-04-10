"""
Módulo de Tipos de Contexto - Palace Framework

Este módulo define los tipos de datos utilizados exclusivamente por el módulo
de gestión de contexto. Complementa los tipos core definidos en
`palace.core.types`.

Componentes:
    - ContextType: Enumeración de tipos de contexto disponibles
    - ContextEntry: Entrada individual de contexto con metadatos
    - RetrievedContext: Resultado de una búsqueda de contexto
    - SessionConfig: Configuración de sesión
    - ProjectConfig: Configuración de proyecto específica para contexto
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ContextType(str, Enum):
    """
    Types of context available in the framework.

    Each type represents a different category of information
    that can be loaded, stored, or retrieved during context management.
    """

    ARCHITECTURE = "architecture"
    """Architecture documentation and design overviews."""

    STACK = "stack"
    """Technology stack information (languages, frameworks, tools)."""

    CONVENTIONS = "conventions"
    """Code conventions, style guides, and naming standards."""

    DECISIONS = "decisions"
    """Architecture Decision Records (ADRs)."""

    CONSTRAINTS = "constraints"
    """Project constraints, limitations, and non-negotiables."""

    PATTERN = "pattern"
    """Code and design patterns in use or recommended."""

    ANTI_PATTERN = "anti_pattern"
    """Anti-patterns to avoid in the project."""

    CONFIG = "config"
    """Project configuration files and settings."""

    SESSION = "session"
    """Session-specific context (conversation state, active tasks)."""

    MEMORY = "memory"
    """Context retrieved from the memory store (RAG)."""

    TASK = "task"
    """Task-specific context and requirements."""


class ContextEntry(BaseModel):
    """
    A single context entry with metadata and content.

    Represents one piece of contextual information that can be
    loaded from files, memory, or generated dynamically. Each
    entry is classified by type and tracked with relevance
    scores for retrieval.
    """

    entry_id: UUID = Field(default_factory=uuid4, description="Unique identifier for this entry")
    context_type: ContextType = Field(..., description="Classification of the context entry")
    source: str = Field(..., description="Source file or origin of the entry")
    title: str = Field(..., description="Human-readable title for the entry")
    content: str = Field(..., description="The actual content text")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata key-value pairs"
    )
    relevance_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Relevance score for retrieval (0.0 - 1.0)"
    )
    token_count: int = Field(default=0, ge=0, description="Approximate token count for the content")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this entry was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this entry was last updated"
    )

    class Config:
        use_enum_values = True


class RetrievedContext(BaseModel):
    """
    Result of a context retrieval operation.

    Contains the entries that matched the query, along with
    metadata about the retrieval process such as token counts,
    sources consulted, and timing information.
    """

    query: str = Field(..., description="Original query used for retrieval")
    entries: List[ContextEntry] = Field(
        default_factory=list, description="Retrieved context entries sorted by relevance"
    )
    total_tokens: int = Field(
        default=0, ge=0, description="Total tokens across all retrieved entries"
    )
    truncated: bool = Field(
        default=False, description="Whether context was truncated due to token limits"
    )
    sources: List[str] = Field(
        default_factory=list, description="List of source files consulted during retrieval"
    )
    memory_hits: int = Field(default=0, ge=0, description="Number of hits from the memory store")
    retrieval_time_ms: int = Field(
        default=0, ge=0, description="Time taken for retrieval in milliseconds"
    )

    class Config:
        use_enum_values = True


class SessionConfig(BaseModel):
    """
    Configuration for a conversation session.

    Controls how sessions are managed including message limits,
    context window sizing, auto-summarization behavior, and
    persistence settings.
    """

    max_messages: int = Field(
        default=100, ge=1, description="Maximum number of messages per session"
    )
    context_window_tokens: int = Field(
        default=8000, ge=1, description="Token limit for the context window"
    )
    auto_summarize: bool = Field(default=True, description="Whether to auto-summarize old messages")
    summarize_after: int = Field(default=50, ge=1, description="Summarize after this many messages")
    persist_history: bool = Field(
        default=True, description="Whether to persist session history to memory"
    )
    ttl_seconds: int = Field(default=7200, ge=0, description="Session time-to-live in seconds")

    class Config:
        use_enum_values = True


class ProjectConfig(BaseModel):
    """
    Context-specific project configuration.

    This is a context-module-specific version of ProjectConfig that
    focuses on the project's context loading capabilities, including
    paths to context directories, loaded conventions, decisions, and
    constraints. It differs from `palace.core.types.ProjectConfig`
    which handles general project metadata.
    """

    project_id: str = Field(..., description="Unique identifier for the project")
    name: str = Field(..., description="Human-readable project name")
    description: Optional[str] = Field(default=None, description="Project description")
    root_path: Path = Field(..., description="Project root directory")
    context_path: Path = Field(..., description="Path to the /ai_context/ directory")
    stack: Dict[str, str] = Field(
        default_factory=dict,
        description="Technology stack mapping (e.g., {'backend': 'fastapi', 'frontend': 'react'})",
    )
    conventions: List[str] = Field(
        default_factory=list, description="Code conventions loaded from context"
    )
    decisions: List[str] = Field(default_factory=list, description="ADR titles loaded from context")
    constraints: List[str] = Field(
        default_factory=list, description="Constraints loaded from context"
    )
    last_loaded: Optional[datetime] = Field(
        default=None, description="When the context was last loaded"
    )
    auto_reload: bool = Field(
        default=False, description="Whether to auto-reload context on file changes"
    )
    watch_interval_seconds: int = Field(
        default=60, ge=1, description="Interval in seconds for watching context file changes"
    )

    class Config:
        use_enum_values = True
