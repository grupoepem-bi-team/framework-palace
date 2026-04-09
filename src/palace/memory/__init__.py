"""
Palace Framework - Memory Module

This module provides the memory layer for the Palace framework, enabling:
- Vector-based semantic memory for context retrieval
- Episodic memory for conversation history
- Project-scoped memory isolation
- Integration with Zep for production deployments

Components:
    - MemoryStore: Main interface for memory operations
    - VectorStore: Vector database integration (Zep/Chroma/SQLite)
    - MemoryManager: High-level memory management
    - EmbeddingGenerator: Text embedding generation

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │                     MemoryManager                        │
    │  ┌─────────────────────────────────────────────────┐    │
    │  │              MemoryStore (Interface)             │    │
    │  └─────────────────────────────────────────────────┘    │
    │                      │                                   │
    │  ┌────────────┬──────┴──────┬────────────────────┐     │
    │  │            │             │                     │     │
    │  ▼            ▼             ▼                     ▼     │
    │ Zep      ChromaDB    SQLite Store         Redis Store   │
    │ Store    (Vector)    (Local Dev)          (Cache)        │
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

# Memory type enumeration
from palace.core.types import MemoryType
from palace.memory.base import (
    EmbeddingGenerator,
    MemoryBase,
    MemoryEntry,
    MemoryQuery,
    MemoryResult,
    MemoryStore,
)
from palace.memory.manager import MemoryManager, get_memory_manager
from palace.memory.vector_store import (
    ChromaStore,
    InMemoryVectorStore,
    SQLiteVectorStore,
    VectorStore,
)
from palace.memory.zep_store import ZepMemoryStore

__all__ = [
    # Base classes
    "MemoryBase",
    "MemoryStore",
    "MemoryManager",
    # Vector stores
    "VectorStore",
    "InMemoryVectorStore",
    "SQLiteVectorStore",
    "ChromaStore",
    "ZepMemoryStore",
    # Embeddings
    "EmbeddingGenerator",
    # Data structures
    "MemoryEntry",
    "MemoryQuery",
    "MemoryResult",
    "MemoryType",
    # Factory functions
    "get_memory_manager",
]
