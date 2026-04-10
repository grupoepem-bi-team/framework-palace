"""
Palace Framework - Memory Base Module

This module defines the base classes and interfaces for the memory system
in the Palace framework. The memory system supports multiple types of storage:

- Episodic Memory: Conversation history and task results (short-term)
- Semantic Memory: Knowledge, ADRs, patterns (long-term)
- Procedural Memory: Scripts, tools, reusable procedures
- Project Memory: Project-specific context and configuration

The memory system is designed to be pluggable, supporting:
- Local SQLite storage (development)
- ChromaDB (production local)
- Zep Cloud (production distributed)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from palace.core.config import Settings

logger = __import__("structlog").get_logger()


# =============================================================================
# Enums and Types
# =============================================================================


class MemoryType(str, Enum):
    """
    Types of memory storage in the Palace framework.

    Each type serves a different purpose and has different
    retention and retrieval characteristics.
    """

    EPISODIC = "episodic"
    """Conversation history, task results (short-term, high-recency)."""

    SEMANTIC = "semantic"
    """Knowledge, ADRs, patterns (long-term, knowledge-graph)."""

    PROCEDURAL = "procedural"
    """Scripts, tools, reusable procedures (skill-based)."""

    PROJECT = "project"
    """Project-specific context and configuration (scoped)."""


class MemoryPriority(int, Enum):
    """Priority levels for memory entries."""

    LOW = 1
    """Low priority, can be evicted first."""

    NORMAL = 5
    """Normal priority, standard retention."""

    HIGH = 10
    """High priority, preferentially retained."""

    CRITICAL = 20
    """Critical priority, never evicted."""


class SearchStrategy(str, Enum):
    """Search strategies for memory retrieval."""

    SIMILARITY = "similarity"
    """Semantic similarity search using embeddings."""

    KEYWORD = "keyword"
    """Keyword-based search."""

    HYBRID = "hybrid"
    """Combination of similarity and keyword search."""

    TEMPORAL = "temporal"
    """Time-based search (most recent)."""


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class MemoryEntry:
    """
    A single entry in the memory store.

    Memory entries are the fundamental unit of storage in the Palace
    memory system. Each entry can be one of several types and contains
    content, metadata, and embedding information.

    Attributes:
        entry_id: Unique identifier for this entry
        memory_type: Type of memory (episodic, semantic, etc.)
        project_id: Project this entry belongs to
        content: The actual content (text)
        embedding: Vector embedding of the content
        metadata: Additional metadata (tags, source, etc.)
        source: Where this entry came from (agent, user, system)
        source_id: ID of the source object (message, task, etc.)
        created_at: When this entry was created
        expires_at: When this entry expires (optional)
        access_count: How many times this entry was retrieved
        last_accessed: When this entry was last accessed
        priority: Priority for eviction decisions
    """

    entry_id: str = field(default_factory=lambda: str(uuid4()))
    memory_type: MemoryType = MemoryType.EPISODIC
    project_id: str = ""
    content: str = ""
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    source_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    priority: MemoryPriority = MemoryPriority.NORMAL

    def touch(self) -> None:
        """Update access timestamp and increment count."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary for serialization."""
        return {
            "entry_id": self.entry_id,
            "memory_type": self.memory_type.value,
            "project_id": self.project_id,
            "content": self.content,
            "embedding": self.embedding,
            "metadata": self.metadata,
            "source": self.source,
            "source_id": self.source_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "priority": self.priority.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Create entry from dictionary."""
        return cls(
            entry_id=data.get("entry_id", str(uuid4())),
            memory_type=MemoryType(data.get("memory_type", "episodic")),
            project_id=data.get("project_id", ""),
            content=data.get("content", ""),
            embedding=data.get("embedding"),
            metadata=data.get("metadata", {}),
            source=data.get("source", "unknown"),
            source_id=data.get("source_id"),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.utcnow(),
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"])
            if data.get("last_accessed")
            else None,
            priority=MemoryPriority(data.get("priority", 5)),
        )


@dataclass
class SearchResult:
    """
    Result from a memory search operation.

    Attributes:
        entry: The memory entry that matched
        score: Similarity/relevance score (0-1)
        highlights: Highlighted snippets from the content
        distance: Vector distance (for similarity search)
    """

    entry: MemoryEntry
    score: float = 0.0
    highlights: List[str] = field(default_factory=list)
    distance: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "entry": self.entry.to_dict(),
            "score": self.score,
            "highlights": self.highlights,
            "distance": self.distance,
        }


@dataclass
class SearchQuery:
    """
    Query for searching memory.

    Attributes:
        query: Text query string
        project_id: Optional project scope
        memory_types: Types of memory to search
        filters: Additional metadata filters
        top_k: Maximum number of results
        min_score: Minimum similarity score
        strategy: Search strategy to use
        include_expired: Whether to include expired entries
    """

    query: str
    project_id: Optional[str] = None
    memory_types: List[MemoryType] = field(default_factory=lambda: [MemoryType.EPISODIC])
    filters: Dict[str, Any] = field(default_factory=dict)
    top_k: int = 5
    min_score: float = 0.0
    strategy: SearchStrategy = SearchStrategy.SIMILARITY
    include_expired: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert query to dictionary."""
        return {
            "query": self.query,
            "project_id": self.project_id,
            "memory_types": [mt.value for mt in self.memory_types],
            "filters": self.filters,
            "top_k": self.top_k,
            "min_score": self.min_score,
            "strategy": self.strategy.value,
            "include_expired": self.include_expired,
        }


# =============================================================================
# Base Classes
# =============================================================================


class MemoryBase(ABC):
    """
    Abstract base class for memory stores.

    All memory implementations must inherit from this class and implement
    the required methods for storing, retrieving, and searching memory entries.

    The memory system supports:
    - Multiple memory types (episodic, semantic, procedural, project)
    - Vector embeddings for semantic search
    - Metadata-based filtering
    - Expiration and eviction policies
    - Project-scoped isolation
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the memory store.

        This method must be called before any other operations.
        It sets up the storage backend, creates indexes, and prepares
        the memory store for use.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close the memory store and release resources.

        This method should be called when the memory store is no longer
        needed. It flushes any pending writes and closes connections.
        """
        pass

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> str:
        """
        Store a memory entry.

        Args:
            entry: The memory entry to store

        Returns:
            The unique ID of the stored entry

        Raises:
            MemoryStoreError: If storage fails
        """
        pass

    @abstractmethod
    async def store_batch(self, entries: List[MemoryEntry]) -> List[str]:
        """
        Store multiple memory entries in a batch.

        Args:
            entries: List of memory entries to store

        Returns:
            List of unique IDs of the stored entries
        """
        pass

    @abstractmethod
    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """
        Retrieve a memory entry by ID.

        Args:
            entry_id: The unique ID of the entry

        Returns:
            The memory entry, or None if not found
        """
        pass

    @abstractmethod
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search for memory entries matching a query.

        Args:
            query: The search query

        Returns:
            List of search results, ordered by relevance
        """
        pass

    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        """
        Delete a memory entry.

        Args:
            entry_id: The unique ID of the entry to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def delete_batch(self, entry_ids: List[str]) -> int:
        """
        Delete multiple memory entries.

        Args:
            entry_ids: List of entry IDs to delete

        Returns:
            Number of entries deleted
        """
        pass

    @abstractmethod
    async def delete_by_project(self, project_id: str) -> int:
        """
        Delete all entries for a project.

        Args:
            project_id: The project ID

        Returns:
            Number of entries deleted
        """
        pass

    @abstractmethod
    async def count(self, project_id: Optional[str] = None) -> int:
        """
        Count memory entries.

        Args:
            project_id: Optional project scope

        Returns:
            Number of entries
        """
        pass

    @abstractmethod
    async def clear(self, memory_type: Optional[MemoryType] = None) -> int:
        """
        Clear memory entries.

        Args:
            memory_type: Optional type to clear (clears all if None)

        Returns:
            Number of entries cleared
        """
        pass


class VectorStore(ABC):
    """
    Abstract base class for vector storage.

    Vector stores handle the embedding generation and similarity search
    for memory entries. They can be backed by different backends:
    - ChromaDB (local)
    - Zep Cloud (distributed)
    - Pinecone (cloud)
    - Weaviate (self-hosted)
    """

    @abstractmethod
    async def create_collection(
        self,
        name: str,
        dimension: int = 1536,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Create a collection for storing vectors.

        Args:
            name: Collection name
            dimension: Vector dimension
            metadata: Collection metadata
        """
        pass

    @abstractmethod
    async def delete_collection(self, name: str) -> bool:
        """
        Delete a collection.

        Args:
            name: Collection name

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def add_vectors(
        self,
        collection: str,
        ids: List[str],
        vectors: List[List[float]],
        metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Add vectors to a collection.

        Args:
            collection: Collection name
            ids: Vector IDs
            vectors: Vector embeddings
            metadata: Optional metadata for each vector
        """
        pass

    @abstractmethod
    async def search_similar(
        self,
        collection: str,
        query_vector: List[float],
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            collection: Collection name
            query_vector: Query vector embedding
            top_k: Maximum number of results
            filter: Optional metadata filter

        Returns:
            List of results with IDs, distances, and metadata
        """
        pass

    @abstractmethod
    async def delete_vectors(
        self,
        collection: str,
        ids: List[str],
    ) -> int:
        """
        Delete vectors from a collection.

        Args:
            collection: Collection name
            ids: Vector IDs to delete

        Returns:
            Number of vectors deleted
        """
        pass

    @abstractmethod
    async def get_vector(
        self,
        collection: str,
        id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a vector by ID.

        Args:
            collection: Collection name
            id: Vector ID

        Returns:
            Vector data with embedding and metadata, or None
        """
        pass


class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.

    Embedding providers generate vector embeddings from text.
    They can use local models or remote APIs.
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Get the dimension of embeddings."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the name of the embedding model."""
        pass

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Vector embedding
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector embeddings
        """
        pass


# =============================================================================
# Memory Store Factory
# =============================================================================


class MemoryStore:
    """
    Factory and manager for memory stores.

    This class provides a unified interface for creating and managing
    different memory store backends. It supports:
    - SQLite (local development)
    - ChromaDB (local production)
    - Zep (cloud distributed)

    The factory pattern allows easy switching between backends
    through configuration.
    """

    _instance: Optional["MemoryStore"] = None
    _store: Optional[MemoryBase] = None
    _vector_store: Optional[VectorStore] = None
    _embedding_provider: Optional[EmbeddingProvider] = None

    def __init__(
        self,
        settings: Optional["Settings"] = None,
        store_type: Optional[str] = None,
    ):
        """
        Initialize the memory store factory.

        Args:
            settings: Framework settings
            store_type: Override store type
        """
        self._settings = settings
        self._store_type = store_type
        self._initialized = False

    @classmethod
    def create(cls, settings: "Settings") -> "MemoryStore":
        """
        Create a memory store instance from settings.

        Args:
            settings: Framework settings

        Returns:
            Configured MemoryStore instance
        """
        if cls._instance is None:
            cls._instance = cls(settings)
        return cls._instance

    async def initialize(self) -> None:
        """
        Initialize the memory store.

        This creates the underlying storage backend based on
        the configured store type.
        """
        if self._initialized:
            return

        store_type = self._store_type or (
            self._settings.memory.store_type if self._settings else "sqlite"
        )

        if store_type == "sqlite":
            from palace.memory.stores import SQLiteMemoryStore

            path = self._settings.memory.local_memory_path if self._settings else "./data/memory.db"
            self._store = SQLiteMemoryStore(path)

        elif store_type == "chroma":
            from palace.memory.stores import ChromaMemoryStore

            collection = (
                self._settings.memory.collection_name if self._settings else "palace_memory"
            )
            self._store = ChromaMemoryStore(collection)

        elif store_type == "zep":
            from palace.memory.stores import ZepMemoryStore

            api_url = (
                self._settings.memory.zep_api_url if self._settings else "http://localhost:8000"
            )
            api_key = self._settings.memory.zep_api_key if self._settings else None
            self._store = ZepMemoryStore(api_url, api_key)

        else:
            raise ValueError(f"Unknown memory store type: {store_type}")

        await self._store.initialize()
        self._initialized = True

    async def close(self) -> None:
        """Close the memory store."""
        if self._store:
            await self._store.close()
        self._initialized = False

    def _require_store(self) -> MemoryBase:
        """Get the underlying memory store, raising if not initialized.

        This replaces the former ``store`` property to avoid a naming
        conflict with the ``async def store()`` delegation method.
        """
        if not self._initialized or self._store is None:
            raise RuntimeError("Memory store not initialized. Call initialize() first.")
        return self._store

    @property
    def vector_store(self) -> VectorStore:
        """Get the vector store."""
        if not self._initialized or self._vector_store is None:
            raise RuntimeError("Memory store not initialized. Call initialize() first.")
        return self._vector_store

    @property
    def embedding_provider(self) -> EmbeddingProvider:
        """Get the embedding provider."""
        if not self._initialized or self._embedding_provider is None:
            raise RuntimeError("Memory store not initialized. Call initialize() first.")
        return self._embedding_provider

    # Delegate methods to underlying store

    async def store(
        self,
        entry: Optional[MemoryEntry] = None,
        *,
        project_id: Optional[str] = None,
        content: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        source_id: Optional[str] = None,
        priority: Optional[MemoryPriority] = None,
    ) -> str:
        """Store a memory entry.

        Accepts either a MemoryEntry object or keyword arguments.
        If a MemoryEntry is provided, it is used directly.
        If keyword arguments are provided, a MemoryEntry is constructed.

        Args:
            entry: Optional MemoryEntry object
            project_id: Project this entry belongs to
            content: The actual content (text)
            memory_type: Type of memory
            metadata: Additional metadata
            source: Where this entry came from
            source_id: ID of the source object
            priority: Priority for eviction decisions

        Returns:
            The unique ID of the stored entry
        """
        if entry is not None:
            return await self._require_store().store(entry)

        # Construct MemoryEntry from keyword arguments
        memory_entry = MemoryEntry(
            project_id=project_id or "",
            content=content or "",
            memory_type=memory_type or MemoryType.EPISODIC,
            metadata=metadata or {},
            source=source or "unknown",
            source_id=source_id,
            priority=priority or MemoryPriority.NORMAL,
        )
        return await self._require_store().store(memory_entry)

    async def store_batch(self, entries: List[MemoryEntry]) -> List[str]:
        """Store multiple entries."""
        return await self._require_store().store_batch(entries)

    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve an entry by ID."""
        return await self._require_store().retrieve(entry_id)

    async def search(
        self,
        query: Optional[SearchQuery] = None,
        *,
        project_id: Optional[str] = None,
        query_text: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        memory_types: Optional[List[MemoryType]] = None,
        top_k: int = 5,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
        strategy: SearchStrategy = SearchStrategy.SIMILARITY,
        include_expired: bool = False,
    ) -> List[SearchResult]:
        """Search for entries.

        Accepts either a SearchQuery object or keyword arguments.
        If a SearchQuery is provided, it is used directly.
        If keyword arguments are provided, a SearchQuery is constructed.

        Args:
            query: Optional SearchQuery object
            project_id: Optional project scope
            query_text: Text query string (used if query is not a SearchQuery)
            memory_type: Single memory type to search (converted to list)
            memory_types: List of memory types to search
            top_k: Maximum number of results
            min_score: Minimum similarity score
            filters: Additional metadata filters
            strategy: Search strategy to use
            include_expired: Whether to include expired entries

        Returns:
            List of search results
        """
        if query is not None:
            search_query = query
        else:
            # Handle query_text or fall back to empty string
            text = query_text or ""

            # Handle memory_type (singular) -> memory_types (plural)
            types = memory_types or []
            if memory_type is not None and memory_type not in types:
                types = [memory_type] + types if not types else types

            search_query = SearchQuery(
                query=text,
                project_id=project_id,
                memory_types=types if types else [MemoryType.EPISODIC],
                filters=filters or {},
                top_k=top_k,
                min_score=min_score,
                strategy=strategy,
                include_expired=include_expired,
            )

        return await self._require_store().search(search_query)

    async def delete(self, entry_id: str) -> bool:
        """Delete an entry."""
        return await self._require_store().delete(entry_id)

    async def delete_batch(self, entry_ids: List[str]) -> int:
        """Delete multiple entries."""
        return await self._require_store().delete_batch(entry_ids)

    async def delete_by_project(self, project_id: str) -> int:
        """Delete all entries for a project."""
        return await self._require_store().delete_by_project(project_id)

    async def count(self, project_id: Optional[str] = None) -> int:
        """Count entries."""
        return await self._require_store().count(project_id)

    async def clear(self, memory_type: Optional[MemoryType] = None) -> int:
        """Clear entries."""
        return await self._require_store().clear(memory_type)

    # Convenience methods

    async def store_conversation(
        self,
        project_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a conversation message.

        Args:
            project_id: Project ID
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Additional metadata

        Returns:
            Entry ID
        """
        entry = MemoryEntry(
            memory_type=MemoryType.EPISODIC,
            project_id=project_id,
            content=content,
            metadata={"role": role, **(metadata or {})},
            source=role,
        )
        return await self.store(entry)

    async def store_knowledge(
        self,
        project_id: str,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store knowledge (ADR, pattern, documentation).

        Args:
            project_id: Project ID
            title: Knowledge title
            content: Knowledge content
            tags: Optional tags
            metadata: Additional metadata

        Returns:
            Entry ID
        """
        entry = MemoryEntry(
            memory_type=MemoryType.SEMANTIC,
            project_id=project_id,
            content=f"{title}\n\n{content}",
            metadata={"title": title, "tags": tags or [], **(metadata or {})},
            source="knowledge",
            priority=MemoryPriority.HIGH,
        )
        return await self.store(entry)

    async def store_procedure(
        self,
        project_id: str,
        name: str,
        description: str,
        steps: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a procedure/script.

        Args:
            project_id: Project ID
            name: Procedure name
            description: Procedure description
            steps: List of steps
            metadata: Additional metadata

        Returns:
            Entry ID
        """
        content = f"{name}\n\n{description}\n\nSteps:\n" + "\n".join(
            f"{i + 1}. {step}" for i, step in enumerate(steps)
        )
        entry = MemoryEntry(
            memory_type=MemoryType.PROCEDURAL,
            project_id=project_id,
            content=content,
            metadata={"name": name, "steps": steps, **(metadata or {})},
            source="procedure",
        )
        return await self.store(entry)

    async def retrieve_context(
        self,
        project_id: str,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context for a query.

        This is a convenience method that combines embedding generation
        and search to retrieve the most relevant context.

        Args:
            project_id: Project ID
            query: Search query
            memory_types: Types of memory to search
            top_k: Maximum results

        Returns:
            List of relevant context entries
        """
        memory_types = memory_types or [
            MemoryType.EPISODIC,
            MemoryType.SEMANTIC,
        ]

        search_query = SearchQuery(
            query=query,
            project_id=project_id,
            memory_types=memory_types,
            top_k=top_k,
        )

        results = await self.search(search_query)

        return [
            {
                "content": result.entry.content,
                "score": result.score,
                "source": result.entry.source,
                "memory_type": result.entry.memory_type.value,
                "metadata": result.entry.metadata,
            }
            for result in results
        ]


# =============================================================================
# Convenience Functions
# =============================================================================


def create_memory_entry(
    content: str,
    memory_type: MemoryType = MemoryType.EPISODIC,
    project_id: str = "",
    source: str = "unknown",
    metadata: Optional[Dict[str, Any]] = None,
    priority: MemoryPriority = MemoryPriority.NORMAL,
) -> MemoryEntry:
    """
    Create a new memory entry with defaults.

    Args:
        content: Entry content
        memory_type: Type of memory
        project_id: Project ID
        source: Entry source
        metadata: Additional metadata
        priority: Entry priority

    Returns:
        New MemoryEntry instance
    """
    return MemoryEntry(
        memory_type=memory_type,
        project_id=project_id,
        content=content,
        source=source,
        metadata=metadata or {},
        priority=priority,
    )


def create_search_query(
    query: str,
    project_id: Optional[str] = None,
    memory_types: Optional[List[MemoryType]] = None,
    top_k: int = 5,
) -> SearchQuery:
    """
    Create a search query with defaults.

    Args:
        query: Search query string
        project_id: Optional project scope
        memory_types: Types of memory to search
        top_k: Maximum results

    Returns:
        New SearchQuery instance
    """
    return SearchQuery(
        query=query,
        project_id=project_id,
        memory_types=memory_types or [MemoryType.EPISODIC],
        top_k=top_k,
    )
