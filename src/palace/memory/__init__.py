"""
Palace Framework - Memory Module

This module provides the memory layer for the Palace framework, enabling:
- Vector-based semantic memory for context retrieval
- Episodic memory for conversation history
- Project-scoped memory isolation
- Integration with Zep for production deployments

Components:
    - MemoryStore: Main interface for memory operations
    - VectorStoreBase: Abstract base for vector store backends
    - InMemoryVectorStore: In-memory vector store for testing
    - ChromaVectorStore: ChromaDB-backed vector store
    - ZepVectorStore: Zep-backed vector store for production
    - EmbeddingProvider: Text embedding generation

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │                     MemoryStore                         │
    │  ┌─────────────────────────────────────────────────┐    │
    │  │              MemoryBase (Interface)             │    │
    │  └─────────────────────────────────────────────────┘    │
    │                      │                                   │
    │  ┌────────────┬──────┴──────┬────────────────────┐     │
    │  │            │             │                     │     │
    │  ▼            ▼             ▼                     ▼     │
    │ ZepVector   ChromaDB     InMemory              SQLite  │
    │ Store      (Vector)     (Testing)              (Local) │
    └─────────────────────────────────────────────────────────┘

Memory Types:
    - EPISODIC: Conversation history, task results (short-term)
    - SEMANTIC: Knowledge, ADRs, patterns (long-term)
    - PROCEDURAL: Scripts, tools, reusable procedures
    - PROJECT: Project-specific context and configuration

Usage:
    from palace.memory import MemoryStore, MemoryType

    # Create memory store
    memory = MemoryStore.create(settings)

    # Store a memory entry
    await memory.store(
        project_id="my-project",
        memory_type=MemoryType.SEMANTIC,
        content="API uses REST architecture",
        metadata={"type": "architecture"}
    )

    # Retrieve relevant context
    results = await memory.retrieve(
        project_id="my-project",
        query="What architecture does the API use?",
        top_k=5
    )
"""

# Memory types and data structures from base
from palace.memory.base import (
    EmbeddingProvider,
    MemoryBase,
    MemoryEntry,
    MemoryPriority,
    MemoryStore,
    MemoryType,
    SearchQuery,
    SearchResult,
    SearchStrategy,
    VectorStore,
    create_memory_entry,
    create_search_query,
)

# Vector store implementations
from palace.memory.vector_store import (
    ChromaVectorStore,
    EmbedderBase,
    EmbeddingConfig,
    InMemoryVectorStore,
    OllamaEmbedder,
    VectorStoreBase,
    VectorStoreConfig,
    VectorStoreType,
    ZepVectorStore,
)

__all__ = [
    # Base classes
    "MemoryBase",
    "MemoryStore",
    # Memory types
    "MemoryType",
    "MemoryPriority",
    "SearchStrategy",
    # Data structures
    "MemoryEntry",
    "SearchQuery",
    "SearchResult",
    # Factory functions
    "create_memory_entry",
    "create_search_query",
    # Vector stores
    "VectorStore",
    "VectorStoreBase",
    "VectorStoreConfig",
    "VectorStoreType",
    "InMemoryVectorStore",
    "ChromaVectorStore",
    "ZepVectorStore",
    # Embeddings
    "EmbeddingProvider",
    "EmbeddingConfig",
    "EmbedderBase",
    "OllamaEmbedder",
]
