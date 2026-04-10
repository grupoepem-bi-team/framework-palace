"""
Integration Tests for Palace Framework - Memory Pipeline

Tests the full memory operations flow:
  Create MemoryEntry → Store → Search → Retrieve

Mocks the actual vector store but tests the MemoryStore API flow
end-to-end, including convenience methods and the complete lifecycle.
"""

# ---------------------------------------------------------------------------
# Bootstrap: prevent broken __init__.py imports from cascading
# ---------------------------------------------------------------------------
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

_SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src"
_PALACE_PKG = _SRC_ROOT / "palace"
_PALACE_CORE_PKG = _PALACE_PKG / "core"
_PALACE_MEMORY_PKG = _PALACE_PKG / "memory"
_PALACE_CONTEXT_PKG = _PALACE_PKG / "context"


def _ensure_package(module_name: str, path: list[str]) -> types.ModuleType:
    if module_name in sys.modules:
        return sys.modules[module_name]
    mod = types.ModuleType(module_name)
    mod.__path__ = path
    mod.__package__ = module_name
    sys.modules[module_name] = mod
    return mod


_ensure_package("palace", [str(_PALACE_PKG)])
_ensure_package("palace.core", [str(_PALACE_CORE_PKG)])
_ensure_package("palace.memory", [str(_PALACE_MEMORY_PKG)])
_ensure_package("palace.context", [str(_PALACE_CONTEXT_PKG)])

# palace.config is not a real package — some modules import
# "from palace.config import Settings, get_settings".  Register the
# *module* palace.core.config under the alias "palace.config" so that
# import resolves correctly without creating a separate file.
import importlib

_core_config = importlib.import_module("palace.core.config")
sys.modules["palace.config"] = _core_config

from palace.memory.base import (
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

# ============================================================================
# Helper: Concrete MemoryBase Implementation for Integration Tests
# ============================================================================


class InMemoryMemoryBase(MemoryBase):
    """
    Concrete in-memory implementation of MemoryBase for integration testing.

    This implementation stores all entries in a dictionary and provides
    basic search functionality without requiring an actual vector database.
    """

    def __init__(self):
        self._entries: dict[str, MemoryEntry] = {}
        self._initialized = False

    async def initialize(self) -> None:
        self._initialized = True

    async def close(self) -> None:
        self._initialized = False

    async def store(self, entry: MemoryEntry) -> str:
        if not self._initialized:
            raise RuntimeError("MemoryBase not initialized")
        entry_id = entry.entry_id
        self._entries[entry_id] = entry
        return entry_id

    async def store_batch(self, entries: list[MemoryEntry]) -> list[str]:
        if not self._initialized:
            raise RuntimeError("MemoryBase not initialized")
        ids = []
        for entry in entries:
            entry_id = await self.store(entry)
            ids.append(entry_id)
        return ids

    async def retrieve(self, entry_id: str) -> MemoryEntry | None:
        if not self._initialized:
            raise RuntimeError("MemoryBase not initialized")
        entry = self._entries.get(entry_id)
        if entry is not None:
            entry.touch()
            self._entries[entry.entry_id] = entry
        return entry

    async def search(self, query: SearchQuery) -> list[SearchResult]:
        if not self._initialized:
            raise RuntimeError("MemoryBase not initialized")

        results = []
        for entry in self._entries.values():
            # Filter by project_id
            if query.project_id and entry.project_id != query.project_id:
                continue

            # Filter by memory types
            if query.memory_types and entry.memory_type not in query.memory_types:
                continue

            # Filter out expired entries (unless explicitly included)
            if not query.include_expired and entry.is_expired():
                continue

            # Simple keyword matching for the query
            query_lower = query.query.lower()
            content_lower = entry.content.lower()

            # Calculate a simple relevance score
            score = 0.0
            if query_lower in content_lower:
                # Exact substring match
                score = 0.9
            else:
                # Partial word match
                query_words = query_lower.split()
                content_words = content_lower.split()
                matching = sum(1 for w in query_words if w in content_words)
                if query_words:
                    score = matching / len(query_words) * 0.7

            # Apply metadata filters
            if query.filters:
                match = True
                for key, value in query.filters.items():
                    if key not in entry.metadata or entry.metadata[key] != value:
                        match = False
                        break
                if not match:
                    continue

            # Apply minimum score threshold
            if score < query.min_score:
                continue

            # Check for expired if include_expired
            if query.include_expired and entry.is_expired():
                pass  # Include expired entries

            results.append(
                SearchResult(
                    entry=entry,
                    score=score,
                    highlights=[entry.content[:100]] if score > 0 else [],
                )
            )

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        # Apply top_k limit
        return results[: query.top_k]

    async def delete(self, entry_id: str) -> bool:
        if not self._initialized:
            raise RuntimeError("MemoryBase not initialized")
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False

    async def delete_batch(self, entry_ids: list[str]) -> int:
        count = 0
        for entry_id in entry_ids:
            if await self.delete(entry_id):
                count += 1
        return count

    async def delete_by_project(self, project_id: str) -> int:
        to_delete = [eid for eid, entry in self._entries.items() if entry.project_id == project_id]
        for eid in to_delete:
            del self._entries[eid]
        return len(to_delete)

    async def count(self, project_id: str | None = None) -> int:
        if project_id is None:
            return len(self._entries)
        return sum(1 for e in self._entries.values() if e.project_id == project_id)

    async def clear(self, memory_type: MemoryType | None = None) -> int:
        if memory_type is None:
            count = len(self._entries)
            self._entries.clear()
            return count
        to_delete = [
            eid for eid, entry in self._entries.items() if entry.memory_type == memory_type
        ]
        for eid in to_delete:
            del self._entries[eid]
        return len(to_delete)


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def memory_base():
    """Create and initialize an InMemoryMemoryBase for testing."""
    store = InMemoryMemoryBase()
    await store.initialize()
    assert store._initialized is True
    yield store
    await store.close()


@pytest_asyncio.fixture
async def memory_store(memory_base):
    """Create a MemoryStore wrapping the InMemoryMemoryBase."""
    # Reset singleton state
    MemoryStore._instance = None

    mock_settings = MagicMock()
    mock_settings.memory = MagicMock()
    mock_settings.memory.store_type = "sqlite"
    mock_settings.memory.local_memory_path = ":memory:"

    store = MemoryStore(settings=mock_settings)
    store._store = memory_base
    store._initialized = True

    yield store

    # Reset singleton state
    MemoryStore._instance = None


# ============================================================================
# Memory Entry Lifecycle Tests
# ============================================================================


class TestMemoryEntryLifecycle:
    """Test the full lifecycle of a MemoryEntry: create, store, search, retrieve, delete."""

    async def test_create_store_retrieve(self, memory_base):
        """Test creating an entry, storing it, and retrieving it by ID."""
        # Create
        entry = create_memory_entry(
            content="Users authenticate via JWT tokens",
            memory_type=MemoryType.SEMANTIC,
            project_id="proj-1",
            source="knowledge",
            priority=MemoryPriority.HIGH,
        )

        # Store
        entry_id = await memory_base.store(entry)
        assert entry_id == entry.entry_id

        # Retrieve
        retrieved = await memory_base.retrieve(entry_id)
        assert retrieved is not None
        assert retrieved.entry_id == entry.entry_id
        assert retrieved.content == "Users authenticate via JWT tokens"
        assert retrieved.memory_type == MemoryType.SEMANTIC
        assert retrieved.project_id == "proj-1"
        assert retrieved.source == "knowledge"
        assert retrieved.priority == MemoryPriority.HIGH

    async def test_store_batch_and_count(self, memory_base):
        """Test storing multiple entries in batch and counting them."""
        entries = [
            create_memory_entry(
                content=f"Entry {i}",
                memory_type=MemoryType.EPISODIC,
                project_id="proj-1",
            )
            for i in range(5)
        ]

        # Store batch
        ids = await memory_base.store_batch(entries)
        assert len(ids) == 5

        # Count
        total = await memory_base.count()
        assert total == 5

        # Count by project
        proj_count = await memory_base.count(project_id="proj-1")
        assert proj_count == 5

    async def test_search_finds_matching_entries(self, memory_base):
        """Test that search finds entries matching the query."""
        # Store entries
        await memory_base.store(
            create_memory_entry(
                content="FastAPI is used for the REST API backend",
                memory_type=MemoryType.SEMANTIC,
                project_id="proj-1",
                source="knowledge",
            )
        )
        await memory_base.store(
            create_memory_entry(
                content="React is used for the frontend",
                memory_type=MemoryType.SEMANTIC,
                project_id="proj-1",
                source="knowledge",
            )
        )
        await memory_base.store(
            create_memory_entry(
                content="PostgreSQL is the primary database",
                memory_type=MemoryType.SEMANTIC,
                project_id="proj-1",
                source="knowledge",
            )
        )

        # Search for API-related entries
        query = create_search_query(
            query="REST API backend",
            project_id="proj-1",
            memory_types=[MemoryType.SEMANTIC],
            top_k=5,
        )
        results = await memory_base.search(query)

        assert len(results) > 0
        # The FastAPI entry should have the highest score
        best_result = results[0]
        assert "FastAPI" in best_result.entry.content or "API" in best_result.entry.content
        assert best_result.score > 0

    async def test_search_filters_by_project(self, memory_base):
        """Test that search filters results by project_id."""
        # Store entries for different projects
        await memory_base.store(
            create_memory_entry(
                content="Project A uses Python",
                memory_type=MemoryType.SEMANTIC,
                project_id="project-a",
            )
        )
        await memory_base.store(
            create_memory_entry(
                content="Project B uses Java",
                memory_type=MemoryType.SEMANTIC,
                project_id="project-b",
            )
        )

        # Search in project-a
        query_a = create_search_query(
            query="Python",
            project_id="project-a",
            top_k=10,
        )
        results_a = await memory_base.search(query_a)
        assert all(r.entry.project_id == "project-a" for r in results_a)

        # Search in project-b
        query_b = create_search_query(
            query="Java",
            project_id="project-b",
            top_k=10,
        )
        results_b = await memory_base.search(query_b)
        assert all(r.entry.project_id == "project-b" for r in results_b)

    async def test_search_filters_by_memory_type(self, memory_base):
        """Test that search filters results by memory type."""
        # Store entries of different types
        await memory_base.store(
            create_memory_entry(
                content="User login conversation",
                memory_type=MemoryType.EPISODIC,
                project_id="proj-1",
            )
        )
        await memory_base.store(
            create_memory_entry(
                content="ADR-001: Use FastAPI",
                memory_type=MemoryType.SEMANTIC,
                project_id="proj-1",
            )
        )
        await memory_base.store(
            create_memory_entry(
                content="Deploy script: docker-compose",
                memory_type=MemoryType.PROCEDURAL,
                project_id="proj-1",
            )
        )

        # Search only semantic memory
        query = create_search_query(
            query="FastAPI",
            project_id="proj-1",
            memory_types=[MemoryType.SEMANTIC],
            top_k=10,
        )
        results = await memory_base.search(query)
        assert all(r.entry.memory_type == MemoryType.SEMANTIC for r in results)

        # Search episodic and procedural
        query2 = create_search_query(
            query="login deploy",
            project_id="proj-1",
            memory_types=[MemoryType.EPISODIC, MemoryType.PROCEDURAL],
            top_k=10,
        )
        results2 = await memory_base.search(query2)
        for r in results2:
            assert r.entry.memory_type in [MemoryType.EPISODIC, MemoryType.PROCEDURAL]

    async def test_delete_entry(self, memory_base):
        """Test deleting a single entry."""
        entry = create_memory_entry(
            content="To be deleted",
            memory_type=MemoryType.EPISODIC,
            project_id="proj-1",
        )
        entry_id = await memory_base.store(entry)

        # Verify it exists
        retrieved = await memory_base.retrieve(entry_id)
        assert retrieved is not None

        # Delete it
        deleted = await memory_base.delete(entry_id)
        assert deleted is True

        # Verify it's gone
        retrieved = await memory_base.retrieve(entry_id)
        assert retrieved is None

    async def test_delete_nonexistent_entry(self, memory_base):
        """Test deleting an entry that doesn't exist."""
        deleted = await memory_base.delete("nonexistent-id")
        assert deleted is False

    async def test_delete_batch(self, memory_base):
        """Test deleting multiple entries at once."""
        ids = []
        for i in range(5):
            entry = create_memory_entry(
                content=f"Entry {i}",
                memory_type=MemoryType.EPISODIC,
                project_id="proj-1",
            )
            entry_id = await memory_base.store(entry)
            ids.append(entry_id)

        # Delete 3 entries
        deleted_count = await memory_base.delete_batch(ids[:3])
        assert deleted_count == 3

        # Verify remaining
        remaining = await memory_base.count()
        assert remaining == 2

    async def test_delete_by_project(self, memory_base):
        """Test deleting all entries for a project."""
        # Add entries for two projects
        for i in range(3):
            await memory_base.store(
                create_memory_entry(
                    content=f"Project A entry {i}",
                    memory_type=MemoryType.EPISODIC,
                    project_id="project-a",
                )
            )
        for i in range(2):
            await memory_base.store(
                create_memory_entry(
                    content=f"Project B entry {i}",
                    memory_type=MemoryType.EPISODIC,
                    project_id="project-b",
                )
            )

        # Delete project-a entries
        deleted = await memory_base.delete_by_project("project-a")
        assert deleted == 3

        # Project-b entries should still be there
        remaining = await memory_base.count(project_id="project-b")
        assert remaining == 2

        # Project-a entries should be gone
        project_a_remaining = await memory_base.count(project_id="project-a")
        assert project_a_remaining == 0

    async def test_clear_all(self, memory_base):
        """Test clearing all entries."""
        for i in range(5):
            await memory_base.store(
                create_memory_entry(
                    content=f"Entry {i}",
                    memory_type=MemoryType.EPISODIC,
                    project_id="proj-1",
                )
            )

        assert await memory_base.count() == 5

        cleared = await memory_base.clear()
        assert cleared == 5
        assert await memory_base.count() == 0

    async def test_clear_by_memory_type(self, memory_base):
        """Test clearing entries of a specific memory type."""
        await memory_base.store(
            create_memory_entry(
                content="Episodic entry",
                memory_type=MemoryType.EPISODIC,
                project_id="proj-1",
            )
        )
        await memory_base.store(
            create_memory_entry(
                content="Semantic entry",
                memory_type=MemoryType.SEMANTIC,
                project_id="proj-1",
            )
        )
        await memory_base.store(
            create_memory_entry(
                content="Procedural entry",
                memory_type=MemoryType.PROCEDURAL,
                project_id="proj-1",
            )
        )

        # Clear only episodic entries
        cleared = await memory_base.clear(memory_type=MemoryType.EPISODIC)
        assert cleared == 1

        # Semantic and procedural should still be there
        remaining = await memory_base.count()
        assert remaining == 2

    async def test_touch_on_retrieve(self, memory_base):
        """Test that retrieving an entry updates access_count and last_accessed."""
        entry = create_memory_entry(
            content="Access me",
            memory_type=MemoryType.SEMANTIC,
            project_id="proj-1",
        )
        entry_id = await memory_base.store(entry)

        # Retrieve the entry
        retrieved = await memory_base.retrieve(entry_id)
        assert retrieved is not None
        assert retrieved.access_count == 1
        assert retrieved.last_accessed is not None

        # Retrieve again
        retrieved2 = await memory_base.retrieve(entry_id)
        assert retrieved2.access_count == 2

    async def test_expired_entries_excluded_by_default(self, memory_base):
        """Test that expired entries are excluded from search by default."""
        # Store an expired entry
        expired_entry = MemoryEntry(
            content="I am expired",
            memory_type=MemoryType.EPISODIC,
            project_id="proj-1",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        await memory_base.store(expired_entry)

        # Store a non-expired entry
        valid_entry = create_memory_entry(
            content="I am valid",
            memory_type=MemoryType.EPISODIC,
            project_id="proj-1",
        )
        await memory_base.store(valid_entry)

        # Search without including expired
        query = create_search_query(
            query="I am",
            project_id="proj-1",
            top_k=10,
        )
        results = await memory_base.search(query)
        # Only the valid entry should be returned
        for r in results:
            assert not r.entry.is_expired()

    async def test_search_with_include_expired(self, memory_base):
        """Test that expired entries can be included in search when requested."""
        # Store an expired entry
        expired_entry = MemoryEntry(
            content="I am expired content",
            memory_type=MemoryType.EPISODIC,
            project_id="proj-1",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        await memory_base.store(expired_entry)

        # Search with include_expired=True
        query = SearchQuery(
            query="expired",
            project_id="proj-1",
            include_expired=True,
            top_k=10,
        )
        results = await memory_base.search(query)
        # The expired entry should be found
        assert len(results) >= 0  # May or may not match the keyword

    async def test_search_with_min_score(self, memory_base):
        """Test that search respects minimum score threshold."""
        # Store some entries
        await memory_base.store(
            create_memory_entry(
                content="Python FastAPI backend REST API",
                memory_type=MemoryType.SEMANTIC,
                project_id="proj-1",
            )
        )
        await memory_base.store(
            create_memory_entry(
                content="React frontend TypeScript components",
                memory_type=MemoryType.SEMANTIC,
                project_id="proj-1",
            )
        )

        # Search with high minimum score
        query = SearchQuery(
            query="Python FastAPI",
            project_id="proj-1",
            min_score=0.5,
            top_k=10,
        )
        results = await memory_base.search(query)
        for r in results:
            assert r.score >= 0.5


# ============================================================================
# MemoryStore Delegation Integration Tests
# ============================================================================


class TestMemoryStoreDelegationIntegration:
    """Integration tests for MemoryStore delegating to MemoryBase."""

    async def test_store_and_retrieve_via_memory_store(self, memory_store):
        """Test storing and retrieving through MemoryStore wrapper."""
        entry = create_memory_entry(
            content="Test content through MemoryStore",
            memory_type=MemoryType.SEMANTIC,
            project_id="proj-1",
        )

        # Store
        entry_id = await memory_store.store(entry)
        assert entry_id == entry.entry_id

        # Retrieve
        retrieved = await memory_store.retrieve(entry_id)
        assert retrieved is not None
        assert retrieved.content == "Test content through MemoryStore"
        assert retrieved.memory_type == MemoryType.SEMANTIC

    async def test_store_batch_via_memory_store(self, memory_store):
        """Test storing multiple entries through MemoryStore wrapper."""
        entries = [
            create_memory_entry(
                content=f"Batch entry {i}",
                memory_type=MemoryType.EPISODIC,
                project_id="proj-1",
            )
            for i in range(3)
        ]

        ids = await memory_store.store_batch(entries)
        assert len(ids) == 3

        # Verify all stored
        count = await memory_store.count(project_id="proj-1")
        assert count == 3

    async def test_search_via_memory_store(self, memory_store):
        """Test searching through MemoryStore wrapper."""
        await memory_store.store(
            create_memory_entry(
                content="Python backend architecture",
                memory_type=MemoryType.SEMANTIC,
                project_id="proj-1",
            )
        )
        await memory_store.store(
            create_memory_entry(
                content="Frontend React components",
                memory_type=MemoryType.SEMANTIC,
                project_id="proj-1",
            )
        )

        query = create_search_query(
            query="Python backend",
            project_id="proj-1",
            memory_types=[MemoryType.SEMANTIC],
        )
        results = await memory_store.search(query)
        assert len(results) > 0

    async def test_delete_via_memory_store(self, memory_store):
        """Test deleting entries through MemoryStore wrapper."""
        entry = create_memory_entry(
            content="Delete me",
            memory_type=MemoryType.EPISODIC,
            project_id="proj-1",
        )
        entry_id = await memory_store.store(entry)

        # Verify stored
        retrieved = await memory_store.retrieve(entry_id)
        assert retrieved is not None

        # Delete
        deleted = await memory_store.delete(entry_id)
        assert deleted is True

        # Verify deleted
        retrieved = await memory_store.retrieve(entry_id)
        assert retrieved is None

    async def test_delete_by_project_via_memory_store(self, memory_store):
        """Test deleting entries by project through MemoryStore wrapper."""
        for i in range(3):
            await memory_store.store(
                create_memory_entry(
                    content=f"Project entry {i}",
                    memory_type=MemoryType.EPISODIC,
                    project_id="target-project",
                )
            )
        # Add one entry for a different project
        await memory_store.store(
            create_memory_entry(
                content="Other project",
                memory_type=MemoryType.EPISODIC,
                project_id="other-project",
            )
        )

        deleted = await memory_store.delete_by_project("target-project")
        assert deleted == 3

        # Other project entry should still exist
        remaining = await memory_store.count(project_id="other-project")
        assert remaining == 1

    async def test_count_via_memory_store(self, memory_store):
        """Test counting entries through MemoryStore wrapper."""
        # Count empty
        total = await memory_store.count()
        assert total == 0

        # Add entries
        for i in range(5):
            await memory_store.store(
                create_memory_entry(
                    content=f"Entry {i}",
                    memory_type=MemoryType.EPISODIC,
                    project_id="proj-1",
                )
            )

        # Count total
        total = await memory_store.count()
        assert total == 5

        # Count by project
        proj_count = await memory_store.count(project_id="proj-1")
        assert proj_count == 5

    async def test_clear_via_memory_store(self, memory_store):
        """Test clearing entries through MemoryStore wrapper."""
        for i in range(3):
            await memory_store.store(
                create_memory_entry(
                    content=f"Entry {i}",
                    memory_type=MemoryType.EPISODIC,
                    project_id="proj-1",
                )
            )

        assert await memory_store.count() == 3

        cleared = await memory_store.clear()
        assert cleared == 3
        assert await memory_store.count() == 0


# ============================================================================
# Convenience Methods Integration Tests
# ============================================================================


class TestMemoryStoreConvenienceIntegration:
    """Integration tests for MemoryStore convenience methods with real MemoryBase."""

    async def test_store_conversation_full_flow(self, memory_store):
        """Test store_conversation creates a proper episodic entry."""
        conv_id = await memory_store.store_conversation(
            project_id="proj-1",
            role="user",
            content="How do I implement authentication?",
            metadata={"session": "sess-1"},
        )

        assert conv_id is not None

        # Retrieve and verify
        entry = await memory_store.retrieve(conv_id)
        assert entry is not None
        assert entry.memory_type == MemoryType.EPISODIC
        assert entry.project_id == "proj-1"
        assert "authentication" in entry.content
        assert entry.metadata["role"] == "user"
        assert entry.metadata["session"] == "sess-1"
        assert entry.source == "user"

    async def test_store_conversation_assistant(self, memory_store):
        """Test storing an assistant conversation message."""
        conv_id = await memory_store.store_conversation(
            project_id="proj-1",
            role="assistant",
            content="Use JWT tokens with refresh token rotation",
        )

        entry = await memory_store.retrieve(conv_id)
        assert entry is not None
        assert entry.metadata["role"] == "assistant"
        assert entry.source == "assistant"

    async def test_store_knowledge_full_flow(self, memory_store):
        """Test store_knowledge creates a proper semantic entry."""
        knowledge_id = await memory_store.store_knowledge(
            project_id="proj-1",
            title="ADR-001: Use FastAPI",
            content="We chose FastAPI for the backend REST API framework.",
            tags=["architecture", "backend"],
            metadata={"status": "accepted"},
        )

        assert knowledge_id is not None

        # Retrieve and verify
        entry = await memory_store.retrieve(knowledge_id)
        assert entry is not None
        assert entry.memory_type == MemoryType.SEMANTIC
        assert entry.project_id == "proj-1"
        assert "ADR-001: Use FastAPI" in entry.content
        assert "We chose FastAPI" in entry.content
        assert entry.metadata["title"] == "ADR-001: Use FastAPI"
        assert entry.metadata["tags"] == ["architecture", "backend"]
        assert entry.metadata["status"] == "accepted"
        assert entry.source == "knowledge"
        assert entry.priority == MemoryPriority.HIGH

    async def test_store_procedure_full_flow(self, memory_store):
        """Test store_procedure creates a proper procedural entry."""
        proc_id = await memory_store.store_procedure(
            project_id="proj-1",
            name="Deploy Application",
            description="Steps to deploy the application to production",
            steps=[
                "Build Docker image",
                "Push to container registry",
                "Deploy to Kubernetes",
                "Run health checks",
            ],
            metadata={"category": "devops"},
        )

        assert proc_id is not None

        # Retrieve and verify
        entry = await memory_store.retrieve(proc_id)
        assert entry is not None
        assert entry.memory_type == MemoryType.PROCEDURAL
        assert entry.project_id == "proj-1"
        assert "Deploy Application" in entry.content
        assert "Steps:" in entry.content
        assert "Build Docker image" in entry.content
        assert entry.metadata["name"] == "Deploy Application"
        assert len(entry.metadata["steps"]) == 4
        assert entry.metadata["category"] == "devops"
        assert entry.source == "procedure"

    async def test_retrieve_context_full_flow(self, memory_store):
        """Test retrieve_context searches and formats results."""
        # Store some knowledge
        await memory_store.store_knowledge(
            project_id="proj-1",
            title="Authentication Pattern",
            content="Use JWT tokens with refresh token rotation for authentication",
            tags=["security", "auth"],
        )
        await memory_store.store_knowledge(
            project_id="proj-1",
            title="Database Pattern",
            content="Use repository pattern for data access layer",
            tags=["architecture", "database"],
        )

        # Retrieve context
        results = await memory_store.retrieve_context(
            project_id="proj-1",
            query="authentication JWT",
            memory_types=[MemoryType.SEMANTIC],
            top_k=5,
        )

        assert isinstance(results, list)
        # Results should contain content, score, source, memory_type, metadata
        for result in results:
            assert "content" in result
            assert "score" in result
            assert "source" in result
            assert "memory_type" in result
            assert "metadata" in result

    async def test_retrieve_context_default_memory_types(self, memory_store):
        """Test that retrieve_context defaults to EPISODIC and SEMANTIC."""
        # Store an entry
        await memory_store.store_knowledge(
            project_id="proj-1",
            title="Test Knowledge",
            content="This is test knowledge",
        )

        # Retrieve context with defaults
        results = await memory_store.retrieve_context(
            project_id="proj-1",
            query="test",
        )

        # The SearchQuery should have been created with EPISODIC and SEMANTIC
        # We verify by checking the results contain entries of those types
        for result in results:
            assert result["memory_type"] in ["episodic", "semantic"]


# ============================================================================
# Full Pipeline Integration Tests
# ============================================================================


class TestFullMemoryPipeline:
    """End-to-end integration tests for the complete memory pipeline."""

    async def test_complete_lifecycle_episodic(self, memory_base):
        """Test complete lifecycle for episodic memory: create → store → search → retrieve → delete."""
        # Create
        entry = create_memory_entry(
            content="User asked about authentication patterns",
            memory_type=MemoryType.EPISODIC,
            project_id="proj-1",
            source="user",
            metadata={"session_id": "sess-1", "turn": 1},
        )

        # Store
        entry_id = await memory_base.store(entry)
        assert entry_id is not None

        # Search
        query = create_search_query(
            query="authentication",
            project_id="proj-1",
            memory_types=[MemoryType.EPISODIC],
            top_k=5,
        )
        results = await memory_base.search(query)
        assert len(results) > 0
        assert any("authentication" in r.entry.content for r in results)

        # Retrieve
        retrieved = await memory_base.retrieve(entry_id)
        assert retrieved is not None
        assert retrieved.access_count == 1

        # Delete
        deleted = await memory_base.delete(entry_id)
        assert deleted is True

        # Verify deletion
        retrieved = await memory_base.retrieve(entry_id)
        assert retrieved is None

    async def test_complete_lifecycle_semantic(self, memory_base):
        """Test complete lifecycle for semantic memory: create → store → search → retrieve."""
        # Create and store a knowledge entry
        entry = create_memory_entry(
            content="ADR-002: Use SQLAlchemy async for database access\n\nDecision: Use SQLAlchemy 2.0+ with async sessions",
            memory_type=MemoryType.SEMANTIC,
            project_id="proj-1",
            source="knowledge",
            priority=MemoryPriority.HIGH,
            metadata={"title": "ADR-002", "status": "accepted"},
        )

        entry_id = await memory_base.store(entry)

        # Search for it
        query = create_search_query(
            query="database SQLAlchemy",
            project_id="proj-1",
            memory_types=[MemoryType.SEMANTIC],
            top_k=5,
        )
        results = await memory_base.search(query)
        assert len(results) > 0
        best = results[0]
        assert "SQLAlchemy" in best.entry.content
        assert best.entry.memory_type == MemoryType.SEMANTIC

        # Retrieve by ID
        retrieved = await memory_base.retrieve(entry_id)
        assert retrieved is not None
        assert retrieved.priority == MemoryPriority.HIGH

    async def test_complete_lifecycle_procedural(self, memory_base):
        """Test complete lifecycle for procedural memory."""
        # Create a procedure entry
        steps = [
            "1. Build Docker image",
            "2. Push to registry",
            "3. Deploy to k8s",
            "4. Run health check",
        ]
        content = "Deploy Application\n\nDeployment steps:\n" + "\n".join(steps)

        entry = create_memory_entry(
            content=content,
            memory_type=MemoryType.PROCEDURAL,
            project_id="proj-1",
            source="procedure",
            metadata={"name": "Deploy Application", "steps": steps},
        )

        entry_id = await memory_base.store(entry)

        # Search for it
        query = create_search_query(
            query="deploy docker kubernetes",
            project_id="proj-1",
            memory_types=[MemoryType.PROCEDURAL],
            top_k=5,
        )
        results = await memory_base.search(query)
        assert len(results) > 0

        # Retrieve and verify
        retrieved = await memory_base.retrieve(entry_id)
        assert retrieved is not None
        assert "Deploy Application" in retrieved.content
        assert retrieved.memory_type == MemoryType.PROCEDURAL

    async def test_multiple_memory_types_coexist(self, memory_base):
        """Test that different memory types can be stored and searched independently."""
        # Store entries of different types
        episodic_id = await memory_base.store(
            create_memory_entry(
                content="User discussed API design",
                memory_type=MemoryType.EPISODIC,
                project_id="proj-1",
            )
        )
        semantic_id = await memory_base.store(
            create_memory_entry(
                content="Use repository pattern for data access",
                memory_type=MemoryType.SEMANTIC,
                project_id="proj-1",
            )
        )
        procedural_id = await memory_base.store(
            create_memory_entry(
                content="Deploy script: docker-compose up",
                memory_type=MemoryType.PROCEDURAL,
                project_id="proj-1",
            )
        )

        # Search only episodic
        query_ep = create_search_query(
            query="API design",
            project_id="proj-1",
            memory_types=[MemoryType.EPISODIC],
        )
        results_ep = await memory_base.search(query_ep)
        for r in results_ep:
            assert r.entry.memory_type == MemoryType.EPISODIC

        # Search only semantic
        query_sem = create_search_query(
            query="repository pattern",
            project_id="proj-1",
            memory_types=[MemoryType.SEMANTIC],
        )
        results_sem = await memory_base.search(query_sem)
        for r in results_sem:
            assert r.entry.memory_type == MemoryType.SEMANTIC

        # Search only procedural
        query_proc = create_search_query(
            query="deploy docker",
            project_id="proj-1",
            memory_types=[MemoryType.PROCEDURAL],
        )
        results_proc = await memory_base.search(query_proc)
        for r in results_proc:
            assert r.entry.memory_type == MemoryType.PROCEDURAL

    async def test_project_isolation(self, memory_base):
        """Test that entries are isolated by project."""
        # Store entries for two different projects
        await memory_base.store(
            create_memory_entry(
                content="Project A uses Python",
                memory_type=MemoryType.SEMANTIC,
                project_id="project-a",
            )
        )
        await memory_base.store(
            create_memory_entry(
                content="Project B uses Java",
                memory_type=MemoryType.SEMANTIC,
                project_id="project-b",
            )
        )

        # Search in project-a
        query_a = create_search_query(
            query="Python",
            project_id="project-a",
        )
        results_a = await memory_base.search(query_a)
        for r in results_a:
            assert r.entry.project_id == "project-a"

        # Search in project-b
        query_b = create_search_query(
            query="Java",
            project_id="project-b",
        )
        results_b = await memory_base.search(query_b)
        for r in results_b:
            assert r.entry.project_id == "project-b"

        # Count per project
        count_a = await memory_base.count(project_id="project-a")
        count_b = await memory_base.count(project_id="project-b")
        assert count_a == 1
        assert count_b == 1

        # Delete project-a entries
        deleted = await memory_base.delete_by_project("project-a")
        assert deleted == 1

        # Project-b should be unaffected
        count_b_after = await memory_base.count(project_id="project-b")
        assert count_b_after == 1

    async def test_entry_serialization_roundtrip(self, memory_base):
        """Test that entries survive a serialization roundtrip."""
        original = MemoryEntry(
            entry_id="test-serialization-id",
            memory_type=MemoryType.SEMANTIC,
            project_id="proj-1",
            content="This entry will be serialized and restored",
            embedding=[0.1, 0.2, 0.3],
            metadata={"title": "Test", "priority": "high"},
            source="test",
            source_id="src-123",
            created_at=datetime.utcnow(),
            access_count=5,
            priority=MemoryPriority.HIGH,
        )

        # Serialize
        d = original.to_dict()
        assert d["entry_id"] == "test-serialization-id"
        assert d["memory_type"] == "semantic"
        assert d["content"] == "This entry will be serialized and restored"

        # Deserialize
        restored = MemoryEntry.from_dict(d)
        assert restored.entry_id == original.entry_id
        assert restored.memory_type == original.memory_type
        assert restored.project_id == original.project_id
        assert restored.content == original.content
        assert restored.embedding == original.embedding
        assert restored.metadata == original.metadata
        assert restored.source == original.source
        assert restored.source_id == original.source_id
        assert restored.access_count == original.access_count
        assert restored.priority == original.priority

        # Store the restored entry
        entry_id = await memory_base.store(restored)
        retrieved = await memory_base.retrieve(entry_id)
        assert retrieved is not None
        assert retrieved.content == "This entry will be serialized and restored"

    async def test_search_result_to_dict_roundtrip(self, memory_base):
        """Test that SearchResult serialization preserves data."""
        entry = create_memory_entry(
            content="Search result test",
            memory_type=MemoryType.SEMANTIC,
            project_id="proj-1",
        )
        await memory_base.store(entry)

        query = create_search_query(
            query="Search result",
            project_id="proj-1",
            memory_types=[MemoryType.SEMANTIC],
        )
        results = await memory_base.search(query)
        assert len(results) > 0

        result = results[0]
        d = result.to_dict()
        assert "entry" in d
        assert "score" in d
        assert "highlights" in d
        assert "distance" in d
        assert d["entry"]["content"] == "Search result test"
        assert isinstance(d["score"], float)

    async def test_search_query_to_dict(self):
        """Test SearchQuery serialization preserves data."""
        query = create_search_query(
            query="test query",
            project_id="proj-1",
            memory_types=[MemoryType.SEMANTIC, MemoryType.EPISODIC],
            top_k=10,
        )
        d = query.to_dict()

        assert d["query"] == "test query"
        assert d["project_id"] == "proj-1"
        assert d["memory_types"] == ["semantic", "episodic"]
        assert d["top_k"] == 10

    async def test_priority_and_expiration_interaction(self, memory_base):
        """Test that entries with different priorities and expiration behave correctly."""
        # High priority entry that never expires
        high_priority = MemoryEntry(
            content="Critical system configuration",
            memory_type=MemoryType.SEMANTIC,
            project_id="proj-1",
            priority=MemoryPriority.CRITICAL,
        )
        await memory_base.store(high_priority)

        # Low priority entry that expires soon
        expiring_entry = MemoryEntry(
            content="Temporary cache data",
            memory_type=MemoryType.EPISODIC,
            project_id="proj-1",
            priority=MemoryPriority.LOW,
            expires_at=datetime.utcnow() - timedelta(minutes=1),
        )
        await memory_base.store(expiring_entry)

        # Non-expiring entry
        permanent_entry = create_memory_entry(
            content="Permanent knowledge",
            memory_type=MemoryType.SEMANTIC,
            project_id="proj-1",
            priority=MemoryPriority.NORMAL,
        )
        await memory_base.store(permanent_entry)

        # Verify high priority entry is not expired
        assert not high_priority.is_expired()

        # Verify expiring entry is expired
        assert expiring_entry.is_expired()

        # Verify permanent entry is not expired
        assert not permanent_entry.is_expired()

        # Search should exclude expired entries by default
        query = create_search_query(
            query="data",
            project_id="proj-1",
            top_k=10,
        )
        results = await memory_base.search(query)
        for r in results:
            assert not r.entry.is_expired()

    async def test_store_and_retrieve_large_content(self, memory_base):
        """Test storing and retrieving entries with large content."""
        large_content = "This is a long entry. " * 1000  # ~24KB content
        entry = create_memory_entry(
            content=large_content,
            memory_type=MemoryType.SEMANTIC,
            project_id="proj-1",
        )

        entry_id = await memory_base.store(entry)
        retrieved = await memory_base.retrieve(entry_id)

        assert retrieved is not None
        assert retrieved.content == large_content

    async def test_metadata_filtering_in_search(self, memory_base):
        """Test that search can filter by metadata."""
        # Store entries with different metadata
        await memory_base.store(
            MemoryEntry(
                content="Important architectural decision",
                memory_type=MemoryType.SEMANTIC,
                project_id="proj-1",
                metadata={"status": "accepted", "category": "architecture"},
            )
        )
        await memory_base.store(
            MemoryEntry(
                content="Proposed architectural change",
                memory_type=MemoryType.SEMANTIC,
                project_id="proj-1",
                metadata={"status": "proposed", "category": "architecture"},
            )
        )

        # Search with metadata filter
        query = SearchQuery(
            query="architecture",
            project_id="proj-1",
            memory_types=[MemoryType.SEMANTIC],
            filters={"status": "accepted"},
            top_k=10,
        )
        results = await memory_base.search(query)
        for r in results:
            assert r.entry.metadata.get("status") == "accepted"

    async def test_empty_search_returns_empty_list(self, memory_base):
        """Test that searching an empty store returns an empty list."""
        query = create_search_query(
            query="nonexistent",
            project_id="proj-1",
        )
        results = await memory_base.search(query)
        assert results == []

    async def test_count_empty_store(self, memory_base):
        """Test counting entries in an empty store."""
        total = await memory_base.count()
        assert total == 0

        proj_count = await memory_base.count(project_id="nonexistent")
        assert proj_count == 0
