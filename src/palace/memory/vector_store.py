"""
Palace Framework - Vector Store Module

This module provides vector storage implementations for semantic search
and context retrieval. It supports multiple backends:

- ChromaDB: Local development and testing
- Zep: Production-ready memory with persistence
- InMemory: Simple in-memory storage for tests

The vector store is used by:
- Memory system for episodic and semantic memory
- Context manager for project-specific context retrieval
- Agents for retrieving relevant code patterns and ADRs
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

import structlog

from palace.core.exceptions import MemoryError, MemoryStoreError
from palace.core.types import MemoryEntry, MemoryType

if TYPE_CHECKING:
    from palace.core.config import Settings

logger = structlog.get_logger()


class VectorStoreType(str, Enum):
    """Supported vector store backends."""

    CHROMA = "chroma"
    """ChromaDB - Local vector store for development."""

    ZEP = "zep"
    """Zep - Production-ready memory store."""

    MEMORY = "memory"
    """In-memory store for testing."""

    PINECONE = "pinecone"
    """Pinecone - Cloud vector database (future)."""

    WEAVIATE = "weaviate"
    """Weaviate - Open source vector database (future)."""


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""

    model: str = "nomic-embed-text"
    """Model to use for generating embeddings."""

    dimension: int = 768
    """Dimension of the embedding vectors."""

    batch_size: int = 100
    """Batch size for embedding generation."""

    cache_embeddings: bool = True
    """Whether to cache generated embeddings."""

    normalize: bool = True
    """Whether to normalize embeddings."""


@dataclass
class SearchQuery:
    """A search query for the vector store."""

    query: str
    """The text query to search for."""

    top_k: int = 5
    """Number of results to return."""

    filters: Dict[str, Any] = field(default_factory=dict)
    """Metadata filters to apply."""

    min_score: float = 0.0
    """Minimum similarity score (0-1)."""

    project_id: Optional[str] = None
    """Project ID to scope the search."""

    memory_types: List[MemoryType] = field(default_factory=list)
    """Types of memory to search."""

    include_content: bool = True
    """Whether to include content in results."""

    include_metadata: bool = True
    """Whether to include metadata in results."""


@dataclass
class SearchResult:
    """A single search result from the vector store."""

    entry_id: str
    """ID of the matching entry."""

    content: str
    """Content of the matching entry."""

    score: float
    """Similarity score (0-1)."""

    memory_type: MemoryType
    """Type of memory."""

    project_id: str
    """Project ID."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""

    embedding: Optional[List[float]] = None
    """The embedding vector (if requested)."""

    created_at: Optional[datetime] = None
    """Creation timestamp."""

    distance: Optional[float] = None
    """Distance metric (if available)."""


@dataclass
class VectorStoreConfig:
    """Configuration for the vector store."""

    store_type: VectorStoreType = VectorStoreType.CHROMA
    """Type of vector store backend."""

    collection_name: str = "palace_memory"
    """Name of the collection to use."""

    embedding_config: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    """Embedding configuration."""

    persist_directory: Optional[str] = None
    """Directory for persistent storage (ChromaDB)."""

    host: str = "localhost"
    """Host for remote stores."""

    port: int = 8000
    """Port for remote stores."""

    api_key: Optional[str] = None
    """API key for authentication."""

    timeout: int = 30
    """Request timeout in seconds."""

    max_retries: int = 3
    """Maximum number of retries."""

    metadata_fields: List[str] = field(
        default_factory=lambda: [
            "project_id",
            "memory_type",
            "source",
            "created_at",
        ]
    )
    """Fields to include in metadata for filtering."""


class VectorStoreBase(ABC):
    """
    Abstract base class for vector store implementations.

    All vector stores must implement this interface to be compatible
    with the Palace memory system.

    The vector store is responsible for:
    - Storing text entries with their embeddings
    - Retrieving similar entries by text or embedding query
    - Filtering by metadata (project_id, memory_type, etc.)
    - Managing collections/namespaces
    """

    def __init__(self, config: VectorStoreConfig):
        """
        Initialize the vector store.

        Args:
            config: Configuration for the vector store
        """
        self.config = config
        self._collection_name = config.collection_name
        self._initialized = False
        logger.info(
            "vector_store_initializing",
            store_type=config.store_type.value,
            collection=config.collection_name,
        )

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the vector store connection.

        This method must be called before any other operations.
        It sets up the connection to the backend and creates
        necessary collections/indexes.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close the vector store connection.

        Clean up resources and close connections.
        """
        pass

    @abstractmethod
    async def add(
        self,
        content: str,
        metadata: Dict[str, Any],
        embedding: Optional[List[float]] = None,
        entry_id: Optional[str] = None,
    ) -> str:
        """
        Add a single entry to the vector store.

        Args:
            content: The text content to store
            metadata: Metadata to associate with the entry
            embedding: Pre-computed embedding (optional)
            entry_id: Custom entry ID (optional)

        Returns:
            The ID of the added entry
        """
        pass

    @abstractmethod
    async def add_batch(
        self,
        entries: List[Tuple[str, Dict[str, Any]]],
        embeddings: Optional[List[List[float]]] = None,
    ) -> List[str]:
        """
        Add multiple entries to the vector store.

        Args:
            entries: List of (content, metadata) tuples
            embeddings: Pre-computed embeddings (optional)

        Returns:
            List of entry IDs
        """
        pass

    @abstractmethod
    async def get(self, entry_id: str) -> Optional[SearchResult]:
        """
        Retrieve a single entry by ID.

        Args:
            entry_id: The entry ID to retrieve

        Returns:
            SearchResult if found, None otherwise
        """
        pass

    @abstractmethod
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search for similar entries.

        Args:
            query: The search query

        Returns:
            List of search results
        """
        pass

    @abstractmethod
    async def search_by_embedding(
        self,
        embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Search using an embedding vector directly.

        Args:
            embedding: The embedding vector to search with
            top_k: Number of results to return
            filters: Metadata filters to apply

        Returns:
            List of search results
        """
        pass

    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        """
        Delete an entry by ID.

        Args:
            entry_id: The entry ID to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def delete_batch(self, entry_ids: List[str]) -> int:
        """
        Delete multiple entries by ID.

        Args:
            entry_ids: List of entry IDs to delete

        Returns:
            Number of entries deleted
        """
        pass

    @abstractmethod
    async def delete_by_filter(self, filters: Dict[str, Any]) -> int:
        """
        Delete entries matching a filter.

        Args:
            filters: Metadata filters to match

        Returns:
            Number of entries deleted
        """
        pass

    @abstractmethod
    async def update(
        self,
        entry_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> bool:
        """
        Update an existing entry.

        Args:
            entry_id: The entry ID to update
            content: New content (optional)
            metadata: New metadata (optional, merged with existing)
            embedding: New embedding (optional)

        Returns:
            True if updated, False if not found
        """
        pass

    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entries in the store.

        Args:
            filters: Metadata filters to apply

        Returns:
            Number of matching entries
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """
        Clear all entries from the store.

        Warning: This operation is irreversible.
        """
        pass

    # -------------------------------------------------------------------------
    # Helper Methods (Concrete implementations)
    # -------------------------------------------------------------------------

    def _validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize metadata.

        Args:
            metadata: Raw metadata dictionary

        Returns:
            Validated metadata dictionary
        """
        validated = {}
        for field_name in self.config.metadata_fields:
            if field_name in metadata:
                validated[field_name] = metadata[field_name]

        # Ensure required fields
        if "project_id" not in validated:
            validated["project_id"] = "default"
        if "memory_type" not in validated:
            validated["memory_type"] = MemoryType.EPISODIC.value
        if "created_at" not in validated:
            validated["created_at"] = datetime.utcnow().isoformat()

        return validated

    def _generate_id(self) -> str:
        """Generate a unique entry ID."""
        return str(uuid4())


class InMemoryVectorStore(VectorStoreBase):
    """
    Simple in-memory vector store for testing.

    This implementation stores all data in memory and uses
    basic cosine similarity for search. It is NOT suitable for
    production use but is useful for testing and development.
    """

    def __init__(self, config: VectorStoreConfig):
        """Initialize the in-memory vector store."""
        super().__init__(config)
        self._entries: Dict[str, Tuple[str, List[float], Dict[str, Any]]] = {}
        self._embedder: Optional[EmbedderBase] = None

    async def initialize(self) -> None:
        """Initialize the store (no-op for in-memory)."""
        self._initialized = True
        logger.info("in_memory_store_initialized")

    async def close(self) -> None:
        """Close the store (no-op for in-memory)."""
        self._entries.clear()
        self._initialized = False
        logger.info("in_memory_store_closed")

    async def add(
        self,
        content: str,
        metadata: Dict[str, Any],
        embedding: Optional[List[float]] = None,
        entry_id: Optional[str] = None,
    ) -> str:
        """Add an entry to the store."""
        if not self._initialized:
            raise MemoryStoreError("store_not_initialized", "Store not initialized")

        entry_id = entry_id or self._generate_id()
        validated_metadata = self._validate_metadata(metadata)

        if embedding is None and self._embedder:
            embedding = await self._embedder.embed(content)

        if embedding is None:
            raise MemoryStoreError("embedding_required", "Embedding is required")

        self._entries[entry_id] = (content, embedding, validated_metadata)
        logger.debug("entry_added", entry_id=entry_id)
        return entry_id

    async def add_batch(
        self,
        entries: List[Tuple[str, Dict[str, Any]]],
        embeddings: Optional[List[List[float]]] = None,
    ) -> List[str]:
        """Add multiple entries."""
        entry_ids = []
        for i, (content, metadata) in enumerate(entries):
            embedding = embeddings[i] if embeddings else None
            entry_id = await self.add(content, metadata, embedding)
            entry_ids.append(entry_id)
        return entry_ids

    async def get(self, entry_id: str) -> Optional[SearchResult]:
        """Get an entry by ID."""
        if entry_id not in self._entries:
            return None

        content, embedding, metadata = self._entries[entry_id]
        return SearchResult(
            entry_id=entry_id,
            content=content,
            score=1.0,
            memory_type=MemoryType(metadata.get("memory_type", MemoryType.EPISODIC.value)),
            project_id=metadata.get("project_id", "default"),
            metadata=metadata,
            embedding=embedding,
        )

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search for similar entries."""
        if not self._initialized:
            raise MemoryStoreError("store_not_initialized", "Store not initialized")

        if not self._embedder:
            return []

        query_embedding = await self._embedder.embed(query.query)
        return await self.search_by_embedding(query_embedding, query.top_k, query.filters)

    async def search_by_embedding(
        self,
        embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search by embedding vector."""
        if not self._initialized:
            raise MemoryStoreError("store_not_initialized", "Store not initialized")

        results = []
        filters = filters or {}

        for entry_id, (content, entry_embedding, metadata) in self._entries.items():
            # Apply filters
            if not self._matches_filters(metadata, filters):
                continue

            # Calculate similarity
            score = self._cosine_similarity(embedding, entry_embedding)

            results.append(
                SearchResult(
                    entry_id=entry_id,
                    content=content,
                    score=score,
                    memory_type=MemoryType(metadata.get("memory_type", MemoryType.EPISODIC.value)),
                    project_id=metadata.get("project_id", "default"),
                    metadata=metadata,
                    embedding=entry_embedding,
                )
            )

        # Sort by score and return top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    async def delete(self, entry_id: str) -> bool:
        """Delete an entry."""
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False

    async def delete_batch(self, entry_ids: List[str]) -> int:
        """Delete multiple entries."""
        count = 0
        for entry_id in entry_ids:
            if await self.delete(entry_id):
                count += 1
        return count

    async def delete_by_filter(self, filters: Dict[str, Any]) -> int:
        """Delete entries matching filter."""
        to_delete = []
        for entry_id, (_, _, metadata) in self._entries.items():
            if self._matches_filters(metadata, filters):
                to_delete.append(entry_id)

        for entry_id in to_delete:
            del self._entries[entry_id]

        return len(to_delete)

    async def update(
        self,
        entry_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> bool:
        """Update an entry."""
        if entry_id not in self._entries:
            return False

        old_content, old_embedding, old_metadata = self._entries[entry_id]

        new_content = content if content is not None else old_content
        new_metadata = {**old_metadata, **(metadata or {})}
        new_embedding = embedding or old_embedding

        if embedding is None and content is not None and self._embedder:
            new_embedding = await self._embedder.embed(new_content)

        self._entries[entry_id] = (new_content, new_embedding, new_metadata)
        return True

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entries."""
        if not filters:
            return len(self._entries)

        count = 0
        for _, _, metadata in self._entries.values():
            if self._matches_filters(metadata, filters):
                count += 1
        return count

    async def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
        logger.info("in_memory_store_cleared")

    def set_embedder(self, embedder: "EmbedderBase") -> None:
        """Set the embedder for this store."""
        self._embedder = embedder

    def _matches_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if metadata matches all filters."""
        for key, value in filters.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math

        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = math.sqrt(sum(x * x for x in a))
        magnitude_b = math.sqrt(sum(x * x for x in b))

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)


class ChromaVectorStore(VectorStoreBase):
    """
    ChromaDB-based vector store implementation.

    ChromaDB is a local vector database that's perfect for:
    - Development and testing
    - Small to medium deployments
    - Offline applications

    For production with persistence and scalability,
    consider using ZepVectorStore instead.
    """

    def __init__(self, config: VectorStoreConfig):
        """Initialize ChromaDB vector store."""
        super().__init__(config)
        self._client = None
        self._collection = None
        self._embedder: Optional[EmbedderBase] = None

    async def initialize(self) -> None:
        """Initialize ChromaDB client and collection."""
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            # Create client
            if self.config.persist_directory:
                settings = ChromaSettings(
                    persist_directory=self.config.persist_directory,
                    anonymized_telemetry=False,
                )
                self._client = chromadb.Client(settings)
            else:
                self._client = chromadb.Client()

            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )

            self._initialized = True
            logger.info(
                "chroma_store_initialized",
                collection=self._collection_name,
                persist_directory=self.config.persist_directory,
            )

        except ImportError:
            raise MemoryStoreError(
                "chroma_not_installed",
                "ChromaDB is not installed. Install it with: pip install chromadb",
            )
        except Exception as e:
            raise MemoryStoreError("initialization_failed", str(e), {"error": str(e)})

    async def close(self) -> None:
        """Close ChromaDB client."""
        if self._client:
            # ChromaDB doesn't have a close method, but we can clear references
            self._client = None
            self._collection = None
        self._initialized = False
        logger.info("chroma_store_closed")

    async def add(
        self,
        content: str,
        metadata: Dict[str, Any],
        embedding: Optional[List[float]] = None,
        entry_id: Optional[str] = None,
    ) -> str:
        """Add an entry to ChromaDB."""
        if not self._initialized:
            raise MemoryStoreError("store_not_initialized", "Store not initialized")

        entry_id = entry_id or self._generate_id()
        validated_metadata = self._validate_metadata(metadata)

        # Convert metadata values to strings for ChromaDB
        str_metadata = {k: str(v) for k, v in validated_metadata.items()}

        if embedding is None and self._embedder:
            embedding = await self._embedder.embed(content)

        try:
            if embedding:
                self._collection.add(
                    ids=[entry_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[str_metadata],
                )
            else:
                self._collection.add(
                    ids=[entry_id],
                    documents=[content],
                    metadatas=[str_metadata],
                )

            logger.debug("chroma_entry_added", entry_id=entry_id)
            return entry_id

        except Exception as e:
            raise MemoryStoreError("add_failed", str(e), {"entry_id": entry_id})

    async def add_batch(
        self,
        entries: List[Tuple[str, Dict[str, Any]]],
        embeddings: Optional[List[List[float]]] = None,
    ) -> List[str]:
        """Add multiple entries to ChromaDB."""
        if not self._initialized:
            raise MemoryStoreError("store_not_initialized", "Store not initialized")

        ids = [self._generate_id() for _ in entries]
        documents = [e[0] for e in entries]
        metadatas = [self._validate_metadata(e[1]) for e in entries]

        # Convert metadata to strings
        str_metadatas = [{k: str(v) for k, v in m.items()} for m in metadatas]

        try:
            if embeddings:
                self._collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=str_metadatas,
                )
            else:
                self._collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=str_metadatas,
                )

            logger.debug("chroma_batch_added", count=len(ids))
            return ids

        except Exception as e:
            raise MemoryStoreError("batch_add_failed", str(e))

    async def get(self, entry_id: str) -> Optional[SearchResult]:
        """Get an entry by ID from ChromaDB."""
        if not self._initialized:
            raise MemoryStoreError("store_not_initialized", "Store not initialized")

        try:
            result = self._collection.get(
                ids=[entry_id], include=["documents", "metadatas", "embeddings"]
            )

            if not result["ids"]:
                return None

            content = result["documents"][0]
            metadata = result["metadatas"][0]
            embedding = result["embeddings"][0] if result.get("embeddings") else None

            return SearchResult(
                entry_id=entry_id,
                content=content,
                score=1.0,
                memory_type=MemoryType(metadata.get("memory_type", MemoryType.EPISODIC.value)),
                project_id=metadata.get("project_id", "default"),
                metadata=metadata,
                embedding=embedding,
            )

        except Exception as e:
            logger.error("chroma_get_failed", entry_id=entry_id, error=str(e))
            return None

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search ChromaDB for similar entries."""
        if not self._initialized:
            raise MemoryStoreError("store_not_initialized", "Store not initialized")

        try:
            # Build where clause from filters
            where = None
            if query.filters:
                where = self._build_where_clause(query.filters)
            elif query.project_id:
                where = {"project_id": query.project_id}

            # Add memory type filter
            if query.memory_types:
                where = where or {}
                where["memory_type"] = {"$in": [mt.value for mt in query.memory_types]}

            # Search
            results = self._collection.query(
                query_texts=[query.query] if not self._embedder else None,
                n_results=query.top_k,
                where=where,
                include=["documents", "metadatas", "distances", "embeddings"],
            )

            # Convert to SearchResults
            search_results = []
            for i, doc_id in enumerate(results["ids"][0]):
                # Convert distance to similarity score (1 - distance for cosine)
                distance = results["distances"][0][i] if results.get("distances") else 0.0
                score = 1.0 - distance

                # Filter by minimum score
                if score < query.min_score:
                    continue

                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}

                search_results.append(
                    SearchResult(
                        entry_id=doc_id,
                        content=results["documents"][0][i] if results.get("documents") else "",
                        score=score,
                        memory_type=MemoryType(
                            metadata.get("memory_type", MemoryType.EPISODIC.value)
                        ),
                        project_id=metadata.get("project_id", "default"),
                        metadata=metadata,
                        embedding=results["embeddings"][0][i]
                        if results.get("embeddings")
                        else None,
                        distance=distance,
                    )
                )

            return search_results

        except Exception as e:
            logger.error("chroma_search_failed", error=str(e))
            raise MemoryStoreError("search_failed", str(e))

    async def search_by_embedding(
        self,
        embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search ChromaDB by embedding vector."""
        if not self._initialized:
            raise MemoryStoreError("store_not_initialized", "Store not initialized")

        try:
            where = self._build_where_clause(filters) if filters else None

            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances", "embeddings"],
            )

            search_results = []
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results.get("distances") else 0.0
                score = 1.0 - distance
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}

                search_results.append(
                    SearchResult(
                        entry_id=doc_id,
                        content=results["documents"][0][i] if results.get("documents") else "",
                        score=score,
                        memory_type=MemoryType(
                            metadata.get("memory_type", MemoryType.EPISODIC.value)
                        ),
                        project_id=metadata.get("project_id", "default"),
                        metadata=metadata,
                        embedding=results["embeddings"][0][i]
                        if results.get("embeddings")
                        else None,
                        distance=distance,
                    )
                )

            return search_results

        except Exception as e:
            logger.error("chroma_embedding_search_failed", error=str(e))
            raise MemoryStoreError("embedding_search_failed", str(e))

    async def delete(self, entry_id: str) -> bool:
        """Delete an entry from ChromaDB."""
        if not self._initialized:
            raise MemoryStoreError("store_not_initialized", "Store not initialized")

        try:
            self._collection.delete(ids=[entry_id])
            logger.debug("chroma_entry_deleted", entry_id=entry_id)
            return True
        except Exception as e:
            logger.error("chroma_delete_failed", entry_id=entry_id, error=str(e))
            return False

    async def delete_batch(self, entry_ids: List[str]) -> int:
        """Delete multiple entries from ChromaDB."""
        if not self._initialized:
            raise MemoryStoreError("store_not_initialized", "Store not initialized")

        try:
            self._collection.delete(ids=entry_ids)
            logger.debug("chroma_batch_deleted", count=len(entry_ids))
            return len(entry_ids)
        except Exception as e:
            logger.error("chroma_batch_delete_failed", error=str(e))
            return 0

    async def delete_by_filter(self, filters: Dict[str, Any]) -> int:
        """Delete entries matching filter from ChromaDB."""
        if not self._initialized:
            raise MemoryStoreError("store_not_initialized", "Store not initialized")

        try:
            where = self._build_where_clause(filters)
            # Get all matching IDs first
            results = self._collection.get(where=where)
            count = len(results["ids"])

            if count > 0:
                self._collection.delete(ids=results["ids"])

            logger.debug("chroma_filter_deleted", count=count)
            return count
        except Exception as e:
            logger.error("chroma_filter_delete_failed", error=str(e))
            return 0

    async def update(
        self,
        entry_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> bool:
        """Update an entry in ChromaDB."""
        if not self._initialized:
            raise MemoryStoreError("store_not_initialized", "Store not initialized")

        try:
            # ChromaDB doesn't have update, so we need to delete and re-add
            existing = await self.get(entry_id)
            if not existing:
                return False

            new_content = content if content is not None else existing.content
            new_metadata = {**existing.metadata, **(metadata or {})}
            new_embedding = embedding or existing.embedding

            await self.delete(entry_id)
            await self.add(new_content, new_metadata, new_embedding, entry_id)

            return True
        except Exception as e:
            logger.error("chroma_update_failed", entry_id=entry_id, error=str(e))
            return False

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entries in ChromaDB."""
        if not self._initialized:
            raise MemoryStoreError("store_not_initialized", "Store not initialized")

        try:
            if filters:
                where = self._build_where_clause(filters)
                results = self._collection.get(where=where)
                return len(results["ids"])
            else:
                return self._collection.count()
        except Exception as e:
            logger.error("chroma_count_failed", error=str(e))
            return 0

    async def clear(self) -> None:
        """Clear all entries from ChromaDB."""
        if not self._initialized:
            raise MemoryStoreError("store_not_initialized", "Store not initialized")

        try:
            # Delete the collection and recreate it
            self._client.delete_collection(self._collection_name)
            self._collection = self._client.create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("chroma_store_cleared")
        except Exception as e:
            raise MemoryStoreError("clear_failed", str(e))

    def set_embedder(self, embedder: "EmbedderBase") -> None:
        """Set the embedder for this store."""
        self._embedder = embedder

    def _build_where_clause(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Build ChromaDB where clause from filters."""
        where = {}
        for key, value in filters.items():
            if isinstance(value, list):
                where[key] = {"$in": [str(v) for v in value]}
            else:
                where[key] = str(value)
        return where


class ZepVectorStore(VectorStoreBase):
    """
    Zep-based vector store implementation.

    Zep is a production-ready memory store that provides:
    - Long-term memory persistence
    - Fast vector search
    - Session management
    - Automatic summarization

    This is the recommended backend for production deployments.
    """

    def __init__(self, config: VectorStoreConfig):
        """Initialize Zep vector store."""
        super().__init__(config)
        self._client = None
        self._embedder: Optional[EmbedderBase] = None

    async def initialize(self) -> None:
        """Initialize Zep client."""
        try:
            # Zep client initialization
            # Note: zep-python package needs to be installed
            from zep_cloud import ZepClient

            self._client = ZepClient(
                base_url=f"{self.config.host}:{self.config.port}",
                api_key=self.config.api_key,
            )

            self._initialized = True
            logger.info(
                "zep_store_initialized",
                host=self.config.host,
                port=self.config.port,
            )

        except ImportError:
            raise MemoryStoreError(
                "zep_not_installed",
                "Zep client is not installed. Install it with: pip install zep-python",
            )
        except Exception as e:
            raise MemoryStoreError("initialization_failed", str(e), {"error": str(e)})

    async def close(self) -> None:
        """Close Zep client."""
        if self._client:
            await self._client.close()
        self._initialized = False
        logger.info("zep_store_closed")

    async def add(
        self,
        content: str,
        metadata: Dict[str, Any],
        embedding: Optional[List[float]] = None,
        entry_id: Optional[str] = None,
    ) -> str:
        """Add an entry to Zep."""
        if not self._initialized:
            raise MemoryStoreError("store_not_initialized", "Store not initialized")

        # TODO: Implement Zep-specific add logic
        raise NotImplementedError("Zep implementation pending")

    async def add_batch(
        self,
        entries: List[Tuple[str, Dict[str, Any]]],
        embeddings: Optional[List[List[float]]] = None,
    ) -> List[str]:
        """Add multiple entries to Zep."""
        # TODO: Implement Zep-specific batch add logic
        raise NotImplementedError("Zep implementation pending")

    async def get(self, entry_id: str) -> Optional[SearchResult]:
        """Get an entry from Zep."""
        # TODO: Implement Zep-specific get logic
        raise NotImplementedError("Zep implementation pending")

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search Zep for similar entries."""
        # TODO: Implement Zep-specific search logic
        raise NotImplementedError("Zep implementation pending")

    async def search_by_embedding(
        self,
        embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search Zep by embedding."""
        # TODO: Implement Zep-specific embedding search
        raise NotImplementedError("Zep implementation pending")

    async def delete(self, entry_id: str) -> bool:
        """Delete an entry from Zep."""
        # TODO: Implement Zep-specific delete logic
        raise NotImplementedError("Zep implementation pending")

    async def delete_batch(self, entry_ids: List[str]) -> int:
        """Delete multiple entries from Zep."""
        # TODO: Implement Zep-specific batch delete
        raise NotImplementedError("Zep implementation pending")

    async def delete_by_filter(self, filters: Dict[str, Any]) -> int:
        """Delete entries matching filter from Zep."""
        # TODO: Implement Zep-specific filter delete
        raise NotImplementedError("Zep implementation pending")

    async def update(
        self,
        entry_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> bool:
        """Update an entry in Zep."""
        # TODO: Implement Zep-specific update logic
        raise NotImplementedError("Zep implementation pending")

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entries in Zep."""
        # TODO: Implement Zep-specific count logic
        raise NotImplementedError("Zep implementation pending")

    async def clear(self) -> None:
        """Clear all entries from Zep."""
        # TODO: Implement Zep-specific clear logic
        raise NotImplementedError("Zep implementation pending")


class EmbedderBase(ABC):
    """
    Abstract base class for embedding generation.

    Embedders convert text to vector representations that can be
    stored and searched in vector stores.
    """

    def __init__(self, config: EmbeddingConfig):
        """Initialize the embedder."""
        self.config = config

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            The embedding vector
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: The texts to embed

        Returns:
            List of embedding vectors
        """
        pass


class OllamaEmbedder(EmbedderBase):
    """
    Ollama-based embedding generation.

    Uses Ollama's embedding API with models like nomic-embed-text.
    """

    def __init__(self, config: EmbeddingConfig, base_url: str = "http://localhost:11434"):
        """Initialize Ollama embedder."""
        super().__init__(config)
        self._base_url = base_url
        self._client = None

    async def initialize(self) -> None:
        """Initialize Ollama client."""
        import httpx

        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=60.0)
        logger.info("ollama_embedder_initialized", model=self.config.model)

    async def close(self) -> None:
        """Close Ollama client."""
        if self._client:
            await self._client.aclose()

    async def embed(self, text: str) -> List[float]:
        """Generate embedding using Ollama."""
        if not self._client:
            await self.initialize()

        try:
            response = await self._client.post(
                "/api/embeddings",
                json={"model": self.config.model, "prompt": text},
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]
        except Exception as e:
            logger.error("ollama_embed_failed", error=str(e))
            raise MemoryError("embedding_generation_failed", str(e))

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embedding = await self.embed(text)
            embeddings.append(embedding)
        return embeddings


def create_vector_store(
    config: VectorStoreConfig,
    settings: Optional["Settings"] = None,
) -> VectorStoreBase:
    """
    Factory function to create a vector store instance.

    Args:
        config: Vector store configuration
        settings: Optional application settings

    Returns:
        Vector store instance

    Raises:
        MemoryStoreError: If store type is not supported
    """
    store_map = {
        VectorStoreType.MEMORY: InMemoryVectorStore,
        VectorStoreType.CHROMA: ChromaVectorStore,
        VectorStoreType.ZEP: ZepVectorStore,
    }

    if config.store_type not in store_map:
        raise MemoryStoreError(
            "unsupported_store_type",
            f"Unsupported store type: {config.store_type}",
            {"supported_types": [t.value for t in store_map.keys()]},
        )

    store_class = store_map[config.store_type]
    return store_class(config)


__all__ = [
    "VectorStoreType",
    "EmbeddingConfig",
    "SearchQuery",
    "SearchResult",
    "VectorStoreConfig",
    "VectorStoreBase",
    "InMemoryVectorStore",
    "ChromaVectorStore",
    "ZepVectorStore",
    "EmbedderBase",
    "OllamaEmbedder",
    "create_vector_store",
]
