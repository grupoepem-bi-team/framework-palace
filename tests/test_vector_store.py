"""
Tests for Palace Framework - Vector Store Module

Tests VectorStoreType, EmbeddingConfig, SearchQuery, SearchResult,
VectorStoreConfig, VectorStoreBase (abstract), and InMemoryVectorStore
(concrete implementation).
"""

# ---------------------------------------------------------------------------
# Bootstrap: prevent broken __init__.py imports from cascading
# ---------------------------------------------------------------------------
import math
import sys
import types
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

_SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
_PALACE_PKG = _SRC_ROOT / "palace"
_PALACE_CORE_PKG = _PALACE_PKG / "core"
_PALACE_MEMORY_PKG = _PALACE_PKG / "memory"


def _ensure_package(module_name: str, path: list[str]) -> types.ModuleType:
    if module_name in sys.modules:
        return sys.modules[module_name]
    mod = types.ModuleType(module_name)
    mod.__path__ = path
    mod.__package__ = module_name
    sys.modules[module_name] = mod
    return mod


# Create stubs for packages with broken __init__.py files.
# These stubs prevent the broken init files from running while still
# allowing direct submodule imports (e.g. from palace.memory.base import ...).
_ensure_package("palace", [str(_PALACE_PKG)])
_ensure_package("palace.core", [str(_PALACE_CORE_PKG)])
_ensure_package("palace.memory", [str(_PALACE_MEMORY_PKG)])

# palace.config is not a real package — some modules import
# "from palace.config import Settings, get_settings".  Register the
# *module* palace.core.config under the alias "palace.config" so that
# import resolves correctly without creating a separate file.
import importlib

_core_config = importlib.import_module("palace.core.config")
sys.modules["palace.config"] = _core_config

# Populate the palace.memory stub with symbols from palace.memory.base
# so that "from palace.memory import MemoryStore" etc. works.
# We avoid running the broken palace.memory.__init__.py (which references
# a non-existent EmbeddingGenerator) by importing directly from the submodule.
_palace_memory_mod = sys.modules["palace.memory"]
_palace_memory_base = importlib.import_module("palace.memory.base")
_public_names = [
    "MemoryBase",
    "MemoryEntry",
    "MemoryStore",
    "MemoryType",
    "MemoryPriority",
    "SearchQuery",
    "SearchResult",
    "SearchStrategy",
    "VectorStore",
    "EmbeddingProvider",
    "create_memory_entry",
    "create_search_query",
]
for _name in _public_names:
    if hasattr(_palace_memory_base, _name):
        setattr(_palace_memory_mod, _name, getattr(_palace_memory_base, _name))

from palace.memory.vector_store import (
    EmbeddingConfig,
    InMemoryVectorStore,
    SearchQuery,
    SearchResult,
    VectorStoreBase,
    VectorStoreConfig,
    VectorStoreType,
)

# ============================================================================
# VectorStoreType Enum Tests
# ============================================================================


class TestVectorStoreType:
    """Tests for VectorStoreType enum."""

    def test_chroma_value(self):
        assert VectorStoreType.CHROMA.value == "chroma"

    def test_zep_value(self):
        assert VectorStoreType.ZEP.value == "zep"

    def test_memory_value(self):
        assert VectorStoreType.MEMORY.value == "memory"

    def test_pinecone_value(self):
        assert VectorStoreType.PINECONE.value == "pinecone"

    def test_weaviate_value(self):
        assert VectorStoreType.WEAVIATE.value == "weaviate"

    def test_all_values_distinct(self):
        values = [vst.value for vst in VectorStoreType]
        assert len(values) == len(set(values))

    def test_total_members(self):
        assert len(VectorStoreType) == 5

    def test_construct_from_value(self):
        assert VectorStoreType("chroma") == VectorStoreType.CHROMA
        assert VectorStoreType("zep") == VectorStoreType.ZEP
        assert VectorStoreType("memory") == VectorStoreType.MEMORY

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            VectorStoreType("unknown_db")

    def test_is_str_enum(self):
        assert isinstance(VectorStoreType.CHROMA, str)
        assert VectorStoreType.CHROMA == "chroma"


# ============================================================================
# EmbeddingConfig Tests
# ============================================================================


class TestEmbeddingConfig:
    """Tests for EmbeddingConfig dataclass."""

    def test_default_values(self):
        config = EmbeddingConfig()
        assert config.model == "nomic-embed-text"
        assert config.dimension == 768
        assert config.batch_size == 100
        assert config.cache_embeddings is True
        assert config.normalize is True

    def test_custom_values(self):
        config = EmbeddingConfig(
            model="text-embedding-ada-002",
            dimension=1536,
            batch_size=50,
            cache_embeddings=False,
            normalize=False,
        )
        assert config.model == "text-embedding-ada-002"
        assert config.dimension == 1536
        assert config.batch_size == 50
        assert config.cache_embeddings is False
        assert config.normalize is False

    def test_partial_custom_values(self):
        config = EmbeddingConfig(dimension=512)
        assert config.dimension == 512
        assert config.model == "nomic-embed-text"
        assert config.batch_size == 100


# ============================================================================
# SearchQuery (vector_store) Tests
# ============================================================================


class TestVectorStoreSearchQuery:
    """Tests for SearchQuery from the vector_store module."""

    def test_creation_with_required_fields(self):
        query = SearchQuery(query="find similar items")
        assert query.query == "find similar items"
        assert query.top_k == 5
        assert query.filters == {}
        assert query.min_score == 0.0
        assert query.project_id is None
        assert query.memory_types == []
        assert query.include_content is True
        assert query.include_metadata is True

    def test_creation_with_all_fields(self):
        from palace.memory.base import MemoryType

        query = SearchQuery(
            query="search query",
            top_k=10,
            filters={"source": "agent"},
            min_score=0.5,
            project_id="proj-1",
            memory_types=[MemoryType.SEMANTIC],
            include_content=False,
            include_metadata=False,
        )
        assert query.query == "search query"
        assert query.top_k == 10
        assert query.filters == {"source": "agent"}
        assert query.min_score == 0.5
        assert query.project_id == "proj-1"
        assert query.memory_types == [MemoryType.SEMANTIC]
        assert query.include_content is False
        assert query.include_metadata is False

    def test_default_filters_is_empty_dict(self):
        query = SearchQuery(query="test")
        assert query.filters == {}


# ============================================================================
# SearchResult (vector_store) Tests
# ============================================================================


class TestVectorStoreSearchResult:
    """Tests for SearchResult from the vector_store module."""

    def test_creation_with_required_fields(self):
        from palace.memory.base import MemoryType

        result = SearchResult(
            entry_id="entry-1",
            content="Test content",
            score=0.95,
            memory_type=MemoryType.SEMANTIC,
            project_id="proj-1",
        )
        assert result.entry_id == "entry-1"
        assert result.content == "Test content"
        assert result.score == 0.95
        assert result.memory_type == MemoryType.SEMANTIC
        assert result.project_id == "proj-1"
        assert result.metadata == {}
        assert result.embedding is None
        assert result.created_at is None
        assert result.distance is None

    def test_creation_with_all_fields(self):
        from palace.memory.base import MemoryType

        now = datetime.utcnow()
        result = SearchResult(
            entry_id="entry-2",
            content="Full content",
            score=0.88,
            memory_type=MemoryType.EPISODIC,
            project_id="proj-2",
            metadata={"source": "test"},
            embedding=[0.1, 0.2, 0.3],
            created_at=now,
            distance=0.12,
        )
        assert result.entry_id == "entry-2"
        assert result.content == "Full content"
        assert result.score == 0.88
        assert result.memory_type == MemoryType.EPISODIC
        assert result.project_id == "proj-2"
        assert result.metadata == {"source": "test"}
        assert result.embedding == [0.1, 0.2, 0.3]
        assert result.created_at == now
        assert result.distance == 0.12

    def test_metadata_defaults_to_empty_dict(self):
        from palace.memory.base import MemoryType

        result = SearchResult(
            entry_id="e1",
            content="c",
            score=0.5,
            memory_type=MemoryType.PROJECT,
            project_id="p1",
        )
        assert result.metadata == {}

    def test_metadata_are_independent_between_instances(self):
        from palace.memory.base import MemoryType

        r1 = SearchResult(
            entry_id="e1",
            content="c1",
            score=0.5,
            memory_type=MemoryType.EPISODIC,
            project_id="p1",
        )
        r2 = SearchResult(
            entry_id="e2",
            content="c2",
            score=0.6,
            memory_type=MemoryType.EPISODIC,
            project_id="p1",
        )
        r1.metadata["key"] = "value"
        assert "key" not in r2.metadata


# ============================================================================
# VectorStoreConfig Tests
# ============================================================================


class TestVectorStoreConfig:
    """Tests for VectorStoreConfig dataclass."""

    def test_default_values(self):
        config = VectorStoreConfig()
        assert config.store_type == VectorStoreType.CHROMA
        assert config.collection_name == "palace_memory"
        assert isinstance(config.embedding_config, EmbeddingConfig)
        assert config.persist_directory is None
        assert config.host == "localhost"
        assert config.port == 8000
        assert config.api_key is None
        assert config.timeout == 30
        assert config.max_retries == 3
        assert "project_id" in config.metadata_fields
        assert "memory_type" in config.metadata_fields

    def test_custom_values(self):
        embed_config = EmbeddingConfig(dimension=1536)
        config = VectorStoreConfig(
            store_type=VectorStoreType.MEMORY,
            collection_name="test_collection",
            embedding_config=embed_config,
            persist_directory="/tmp/vectors",
            host="127.0.0.1",
            port=9000,
            api_key="secret-key",
            timeout=60,
            max_retries=5,
        )
        assert config.store_type == VectorStoreType.MEMORY
        assert config.collection_name == "test_collection"
        assert config.embedding_config.dimension == 1536
        assert config.persist_directory == "/tmp/vectors"
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.api_key == "secret-key"
        assert config.timeout == 60
        assert config.max_retries == 5

    def test_default_metadata_fields(self):
        config = VectorStoreConfig()
        expected_fields = ["project_id", "memory_type", "source", "created_at"]
        for field in expected_fields:
            assert field in config.metadata_fields

    def test_custom_metadata_fields(self):
        config = VectorStoreConfig(metadata_fields=["project_id", "custom_field"])
        assert config.metadata_fields == ["project_id", "custom_field"]


# ============================================================================
# VectorStoreBase Abstract Class Tests
# ============================================================================


class TestVectorStoreBaseAbstract:
    """Tests for VectorStoreBase abstract class."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            VectorStoreBase(VectorStoreConfig())

    def test_abstract_methods_exist(self):
        abstract_methods = {
            "initialize",
            "close",
            "add",
            "add_batch",
            "get",
            "search",
            "search_by_embedding",
            "delete",
            "delete_batch",
            "delete_by_filter",
            "update",
            "count",
            "clear",
        }
        actual_abstract = VectorStoreBase.__abstractmethods__
        assert actual_abstract == abstract_methods

    def test_concrete_subclass_can_be_instantiated(self):
        class ConcreteStore(VectorStoreBase):
            async def initialize(self):
                pass

            async def close(self):
                pass

            async def add(self, content, metadata, embedding=None, entry_id=None):
                return "id"

            async def add_batch(self, entries, embeddings=None):
                return []

            async def get(self, entry_id):
                return None

            async def search(self, query):
                return []

            async def search_by_embedding(self, embedding, top_k=5, filters=None):
                return []

            async def delete(self, entry_id):
                return True

            async def delete_batch(self, entry_ids):
                return len(entry_ids)

            async def delete_by_filter(self, filters):
                return 0

            async def update(self, entry_id, content=None, metadata=None, embedding=None):
                return True

            async def count(self, filters=None):
                return 0

            async def clear(self):
                pass

        store = ConcreteStore(VectorStoreConfig())
        assert store is not None
        assert store.config.collection_name == "palace_memory"


# ============================================================================
# InMemoryVectorStore Tests
# ============================================================================


class TestInMemoryVectorStoreInit:
    """Tests for InMemoryVectorStore initialization."""

    def test_init_with_config(self):
        config = VectorStoreConfig(
            store_type=VectorStoreType.MEMORY,
            collection_name="test_collection",
        )
        store = InMemoryVectorStore(config)
        assert store.config is config
        assert store._initialized is False
        assert store._entries == {}

    async def test_initialize_sets_flag(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        assert store._initialized is False
        await store.initialize()
        assert store._initialized is True

    async def test_close_clears_entries_and_resets_flag(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        await store.initialize()
        # Add some entries
        await store.add("test content", {"project_id": "p1"}, embedding=[0.1, 0.2])
        assert len(store._entries) > 0

        await store.close()
        assert store._entries == {}
        assert store._initialized is False


class TestInMemoryVectorStoreAdd:
    """Tests for InMemoryVectorStore.add()."""

    @pytest_asyncio.fixture
    async def store(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        await store.initialize()
        yield store
        await store.close()

    async def test_add_with_embedding(self, store):
        entry_id = await store.add(
            "Hello world",
            {"project_id": "proj-1", "memory_type": "episodic"},
            embedding=[0.1, 0.2, 0.3],
        )
        assert entry_id is not None
        assert len(entry_id) > 0

    async def test_add_returns_unique_ids(self, store):
        id1 = await store.add("content 1", {"project_id": "p1"}, embedding=[0.1])
        id2 = await store.add("content 2", {"project_id": "p2"}, embedding=[0.2])
        assert id1 != id2

    async def test_add_with_custom_id(self, store):
        entry_id = await store.add(
            "Custom ID content",
            {"project_id": "p1"},
            embedding=[0.5],
            entry_id="my-custom-id",
        )
        assert entry_id == "my-custom-id"

    async def test_add_with_embedder(self, store):
        """When no embedding is provided but an embedder is set, it should use the embedder."""
        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]
        store.set_embedder(mock_embedder)

        entry_id = await store.add("content with embedder", {"project_id": "p1"})
        assert entry_id is not None
        mock_embedder.embed.assert_called_once_with("content with embedder")

    async def test_add_without_embedding_raises(self, store):
        """When no embedding and no embedder, should raise MemoryStoreError."""
        from palace.core.exceptions import MemoryStoreError

        with pytest.raises(MemoryStoreError):
            await store.add("no embedding", {"project_id": "p1"})

    async def test_add_not_initialized_raises(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        # Not initialized
        from palace.core.exceptions import MemoryStoreError

        with pytest.raises(MemoryStoreError):
            await store.add("test", {"project_id": "p1"}, embedding=[0.1])


class TestInMemoryVectorStoreAddBatch:
    """Tests for InMemoryVectorStore.add_batch()."""

    @pytest_asyncio.fixture
    async def store(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        await store.initialize()
        yield store
        await store.close()

    async def test_add_batch_with_embeddings(self, store):
        entries = [
            ("content 1", {"project_id": "p1"}),
            ("content 2", {"project_id": "p2"}),
            ("content 3", {"project_id": "p3"}),
        ]
        embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

        ids = await store.add_batch(entries, embeddings=embeddings)
        assert len(ids) == 3
        assert all(isinstance(id_, str) for id_ in ids)

    async def test_add_batch_with_embedder(self, store):
        mock_embedder = AsyncMock()
        mock_embedder.embed.side_effect = lambda text: [0.1] * 10
        store.set_embedder(mock_embedder)

        entries = [
            ("content 1", {"project_id": "p1"}),
            ("content 2", {"project_id": "p2"}),
        ]
        ids = await store.add_batch(entries)
        assert len(ids) == 2

    async def test_add_batch_empty_list(self, store):
        ids = await store.add_batch([])
        assert ids == []


class TestInMemoryVectorStoreGet:
    """Tests for InMemoryVectorStore.get()."""

    @pytest_asyncio.fixture
    async def store(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        await store.initialize()
        yield store
        await store.close()

    async def test_get_existing_entry(self, store):
        from palace.memory.base import MemoryType

        entry_id = await store.add(
            "Retrieve me",
            {"project_id": "p1", "memory_type": MemoryType.SEMANTIC.value},
            embedding=[0.1, 0.2],
        )
        result = await store.get(entry_id)
        assert result is not None
        assert result.entry_id == entry_id
        assert result.content == "Retrieve me"
        assert result.score == 1.0
        assert result.project_id == "p1"

    async def test_get_nonexistent_entry(self, store):
        result = await store.get("nonexistent-id")
        assert result is None


class TestInMemoryVectorStoreSearch:
    """Tests for InMemoryVectorStore.search() and search_by_embedding()."""

    @pytest_asyncio.fixture
    async def store(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        await store.initialize()
        # Set up mock embedder
        mock_embedder = AsyncMock()
        mock_embedder.embed.side_effect = lambda text: [0.1] * 10
        store.set_embedder(mock_embedder)
        yield store
        await store.close()

    async def test_search_returns_results(self, store):
        await store.add("Python programming", {"project_id": "p1"}, embedding=[0.9, 0.8, 0.7])
        await store.add("JavaScript development", {"project_id": "p1"}, embedding=[0.1, 0.2, 0.3])

        query = SearchQuery(query="programming", top_k=5)
        results = await store.search(query)
        assert isinstance(results, list)

    async def test_search_by_embedding_returns_results(self, store):
        await store.add("Vector search content", {"project_id": "p1"}, embedding=[1.0, 0.0, 0.0])
        await store.add("Another content", {"project_id": "p1"}, embedding=[0.0, 1.0, 0.0])

        results = await store.search_by_embedding([0.9, 0.1, 0.0], top_k=2)
        assert len(results) <= 2
        # Results should be sorted by score (descending)
        if len(results) > 1:
            assert results[0].score >= results[1].score

    async def test_search_by_embedding_with_filters(self, store):
        from palace.memory.base import MemoryType

        await store.add(
            "Semantic content",
            {"project_id": "proj-a", "memory_type": MemoryType.SEMANTIC.value},
            embedding=[0.5, 0.5],
        )
        await store.add(
            "Episodic content",
            {"project_id": "proj-b", "memory_type": MemoryType.EPISODIC.value},
            embedding=[0.5, 0.5],
        )

        results = await store.search_by_embedding(
            [0.5, 0.5],
            top_k=5,
            filters={"project_id": "proj-a"},
        )
        assert len(results) == 1
        assert results[0].project_id == "proj-a"

    async def test_search_by_embedding_respects_top_k(self, store):
        # Add 5 entries
        for i in range(5):
            await store.add(
                f"Content {i}",
                {"project_id": "p1", "index": str(i)},
                embedding=[0.1 * i, 0.2 * i],
            )

        results = await store.search_by_embedding([0.1, 0.2], top_k=3)
        assert len(results) <= 3

    async def test_search_not_initialized_raises(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        # Not initialized
        from palace.core.exceptions import MemoryStoreError

        with pytest.raises(MemoryStoreError):
            await store.search(SearchQuery(query="test"))

    async def test_search_by_embedding_not_initialized_raises(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        from palace.core.exceptions import MemoryStoreError

        with pytest.raises(MemoryStoreError):
            await store.search_by_embedding([0.1, 0.2])

    async def test_search_without_embedder_returns_empty(self, store):
        """Search requires an embedder to generate query embedding."""
        store_no_embedder = InMemoryVectorStore(
            VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        )
        await store_no_embedder.initialize()
        # Add with explicit embedding
        await store_no_embedder.add("content", {"project_id": "p1"}, embedding=[0.5])
        # But search without embedder should return empty
        results = await store_no_embedder.search(SearchQuery(query="test"))
        assert results == []
        await store_no_embedder.close()


class TestInMemoryVectorStoreDelete:
    """Tests for InMemoryVectorStore delete operations."""

    @pytest_asyncio.fixture
    async def store(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        await store.initialize()
        yield store
        await store.close()

    async def test_delete_existing_entry(self, store):
        entry_id = await store.add("Delete me", {"project_id": "p1"}, embedding=[0.1])
        result = await store.delete(entry_id)
        assert result is True
        # Verify it's actually gone
        assert await store.get(entry_id) is None

    async def test_delete_nonexistent_entry(self, store):
        result = await store.delete("nonexistent-id")
        assert result is False

    async def test_delete_batch(self, store):
        id1 = await store.add("Entry 1", {"project_id": "p1"}, embedding=[0.1])
        id2 = await store.add("Entry 2", {"project_id": "p1"}, embedding=[0.2])
        id3 = await store.add("Entry 3", {"project_id": "p1"}, embedding=[0.3])

        count = await store.delete_batch([id1, id3])
        assert count == 2
        # Verify they're gone
        assert await store.get(id1) is None
        assert await store.get(id3) is None
        # id2 should still exist
        assert await store.get(id2) is not None

    async def test_delete_batch_with_nonexistent_ids(self, store):
        id1 = await store.add("Entry", {"project_id": "p1"}, embedding=[0.1])
        count = await store.delete_batch([id1, "nonexistent-id"])
        assert count == 1

    async def test_delete_by_filter(self, store):
        from palace.memory.base import MemoryType

        await store.add(
            "Semantic entry",
            {"project_id": "proj-a", "memory_type": MemoryType.SEMANTIC.value},
            embedding=[0.1],
        )
        await store.add(
            "Episodic entry",
            {"project_id": "proj-b", "memory_type": MemoryType.EPISODIC.value},
            embedding=[0.2],
        )

        deleted = await store.delete_by_filter({"project_id": "proj-a"})
        assert deleted == 1


class TestInMemoryVectorStoreUpdate:
    """Tests for InMemoryVectorStore.update()."""

    @pytest_asyncio.fixture
    async def store(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        await store.initialize()
        yield store
        await store.close()

    async def test_update_content(self, store):
        from palace.memory.base import MemoryType

        entry_id = await store.add(
            "Original content",
            {"project_id": "p1", "memory_type": MemoryType.EPISODIC.value},
            embedding=[0.1, 0.2],
        )

        result = await store.update(entry_id, content="Updated content")
        assert result is True

        entry = await store.get(entry_id)
        assert entry.content == "Updated content"

    async def test_update_metadata_merges(self, store):
        from palace.memory.base import MemoryType

        entry_id = await store.add(
            "Content",
            {"project_id": "p1", "memory_type": MemoryType.EPISODIC.value, "key1": "val1"},
            embedding=[0.1],
        )

        result = await store.update(entry_id, metadata={"key2": "val2"})
        assert result is True

        entry = await store.get(entry_id)
        # Original metadata should be preserved
        assert entry.metadata["key1"] == "val1"
        # New metadata should be added
        assert entry.metadata["key2"] == "val2"

    async def test_update_embedding(self, store):
        entry_id = await store.add("Content", {"project_id": "p1"}, embedding=[0.1])
        new_embedding = [0.9, 0.8, 0.7]

        result = await store.update(entry_id, embedding=new_embedding)
        assert result is True

        entry = await store.get(entry_id)
        assert entry.embedding == new_embedding

    async def test_update_nonexistent_entry(self, store):
        result = await store.update("nonexistent-id", content="New content")
        assert result is False

    async def test_update_with_embedder(self, store):
        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = [0.5, 0.5, 0.5]
        store.set_embedder(mock_embedder)

        entry_id = await store.add("Original", {"project_id": "p1"}, embedding=[0.1])
        result = await store.update(entry_id, content="Updated")
        assert result is True
        mock_embedder.embed.assert_called_with("Updated")


class TestInMemoryVectorStoreCount:
    """Tests for InMemoryVectorStore.count()."""

    @pytest_asyncio.fixture
    async def store(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        await store.initialize()
        yield store
        await store.close()

    async def test_count_empty_store(self, store):
        count = await store.count()
        assert count == 0

    async def test_count_with_entries(self, store):
        await store.add("Entry 1", {"project_id": "p1"}, embedding=[0.1])
        await store.add("Entry 2", {"project_id": "p1"}, embedding=[0.2])
        await store.add("Entry 3", {"project_id": "p2"}, embedding=[0.3])

        count = await store.count()
        assert count == 3

    async def test_count_with_filters(self, store):
        from palace.memory.base import MemoryType

        await store.add(
            "Semantic 1",
            {"project_id": "proj-a", "memory_type": MemoryType.SEMANTIC.value},
            embedding=[0.1],
        )
        await store.add(
            "Episodic 1",
            {"project_id": "proj-b", "memory_type": MemoryType.EPISODIC.value},
            embedding=[0.2],
        )
        await store.add(
            "Semantic 2",
            {"project_id": "proj-a", "memory_type": MemoryType.SEMANTIC.value},
            embedding=[0.3],
        )

        count_all = await store.count()
        assert count_all == 3

        count_proj_a = await store.count(filters={"project_id": "proj-a"})
        assert count_proj_a == 2

        count_semantic = await store.count(filters={"memory_type": MemoryType.SEMANTIC.value})
        assert count_semantic == 2


class TestInMemoryVectorStoreClear:
    """Tests for InMemoryVectorStore.clear()."""

    @pytest_asyncio.fixture
    async def store(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        await store.initialize()
        yield store
        await store.close()

    async def test_clear_removes_all_entries(self, store):
        await store.add("Entry 1", {"project_id": "p1"}, embedding=[0.1])
        await store.add("Entry 2", {"project_id": "p2"}, embedding=[0.2])

        assert await store.count() == 2

        await store.clear()
        assert await store.count() == 0
        assert store._entries == {}


class TestInMemoryVectorStoreCosineSimilarity:
    """Tests for InMemoryVectorStore._cosine_similarity()."""

    @pytest_asyncio.fixture
    async def store(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        await store.initialize()
        yield store
        await store.close()

    def test_identical_vectors(self, store):
        similarity = store._cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0])
        assert abs(similarity - 1.0) < 1e-6

    def test_opposite_vectors(self, store):
        similarity = store._cosine_similarity([1.0, 0.0], [-1.0, 0.0])
        assert abs(similarity - (-1.0)) < 1e-6

    def test_orthogonal_vectors(self, store):
        similarity = store._cosine_similarity([1.0, 0.0], [0.0, 1.0])
        assert abs(similarity) < 1e-6

    def test_zero_vector_returns_zero(self, store):
        similarity = store._cosine_similarity([0.0, 0.0], [1.0, 1.0])
        assert similarity == 0.0

    def test_similarity_is_symmetric(self, store):
        a = [0.5, 0.5, 0.5]
        b = [0.7, 0.3, 0.1]
        sim_ab = store._cosine_similarity(a, b)
        sim_ba = store._cosine_similarity(b, a)
        assert abs(sim_ab - sim_ba) < 1e-6


class TestInMemoryVectorStoreMatchesFilters:
    """Tests for InMemoryVectorStore._matches_filters()."""

    @pytest_asyncio.fixture
    async def store(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        await store.initialize()
        yield store
        await store.close()

    def test_matches_single_filter(self, store):
        metadata = {"project_id": "proj-1", "memory_type": "episodic"}
        assert store._matches_filters(metadata, {"project_id": "proj-1"}) is True
        assert store._matches_filters(metadata, {"project_id": "proj-2"}) is False

    def test_matches_multiple_filters(self, store):
        metadata = {"project_id": "proj-1", "memory_type": "episodic"}
        assert (
            store._matches_filters(metadata, {"project_id": "proj-1", "memory_type": "episodic"})
            is True
        )
        assert (
            store._matches_filters(metadata, {"project_id": "proj-1", "memory_type": "semantic"})
            is False
        )

    def test_matches_empty_filter(self, store):
        metadata = {"project_id": "proj-1"}
        assert store._matches_filters(metadata, {}) is True

    def test_matches_missing_key_in_metadata(self, store):
        metadata = {"project_id": "proj-1"}
        assert store._matches_filters(metadata, {"missing_key": "value"}) is False


class TestInMemoryVectorStoreSetEmbedder:
    """Tests for InMemoryVectorStore.set_embedder()."""

    async def test_set_embedder(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        await store.initialize()

        mock_embedder = MagicMock()
        store.set_embedder(mock_embedder)
        assert store._embedder is mock_embedder

        await store.close()


class TestInMemoryVectorStoreValidateMetadata:
    """Tests for VectorStoreBase._validate_metadata()."""

    @pytest_asyncio.fixture
    async def store(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        await store.initialize()
        yield store
        await store.close()

    def test_validate_metadata_adds_defaults(self, store):
        metadata = {"project_id": "my-project"}
        validated = store._validate_metadata(metadata)
        assert validated["project_id"] == "my-project"
        assert "memory_type" in validated
        assert "created_at" in validated

    def test_validate_metadata_preserves_existing(self, store):
        from palace.memory.base import MemoryType

        metadata = {
            "project_id": "proj-1",
            "memory_type": MemoryType.SEMANTIC.value,
            "created_at": "2024-01-01T00:00:00",
        }
        validated = store._validate_metadata(metadata)
        assert validated["project_id"] == "proj-1"
        assert validated["memory_type"] == MemoryType.SEMANTIC.value

    def test_validate_metadata_empty_dict_gets_defaults(self, store):
        validated = store._validate_metadata({})
        assert "project_id" in validated
        assert validated["project_id"] == "default"
        assert "memory_type" in validated
        assert "created_at" in validated


class TestInMemoryVectorStoreGenerateId:
    """Tests for VectorStoreBase._generate_id()."""

    @pytest_asyncio.fixture
    async def store(self):
        config = VectorStoreConfig(store_type=VectorStoreType.MEMORY)
        store = InMemoryVectorStore(config)
        await store.initialize()
        yield store
        await store.close()

    def test_generate_id_returns_string(self, store):
        id1 = store._generate_id()
        assert isinstance(id1, str)

    def test_generate_id_returns_unique_ids(self, store):
        ids = [store._generate_id() for _ in range(100)]
        assert len(set(ids)) == 100


class TestInMemoryVectorStoreEndToEnd:
    """End-to-end tests for InMemoryVectorStore operations."""

    @pytest_asyncio.fixture
    async def store(self):
        config = VectorStoreConfig(
            store_type=VectorStoreType.MEMORY,
            collection_name="test_e2e",
        )
        store = InMemoryVectorStore(config)
        await store.initialize()
        yield store
        await store.close()

    async def test_full_lifecycle(self, store):
        """Test add → get → search → update → delete lifecycle."""
        # Add
        entry_id = await store.add(
            "Initial content",
            {"project_id": "lifecycle", "source": "test"},
            embedding=[0.5, 0.5],
        )
        assert entry_id is not None

        # Get
        entry = await store.get(entry_id)
        assert entry is not None
        assert entry.content == "Initial content"

        # Update
        await store.update(entry_id, content="Updated content")
        entry = await store.get(entry_id)
        assert entry.content == "Updated content"

        # Delete
        deleted = await store.delete(entry_id)
        assert deleted is True
        assert await store.get(entry_id) is None

    async def test_search_returns_relevant_results(self, store):
        """Test that search returns results sorted by similarity."""
        # Add entries with known embeddings
        await store.add(
            "Python web framework",
            {"project_id": "p1"},
            embedding=[1.0, 0.0, 0.0],
        )
        await store.add(
            "JavaScript frontend library",
            {"project_id": "p1"},
            embedding=[0.0, 1.0, 0.0],
        )
        await store.add(
            "Python data science",
            {"project_id": "p1"},
            embedding=[0.9, 0.1, 0.0],
        )

        # Search with a vector close to the first entry
        results = await store.search_by_embedding([0.95, 0.05, 0.0], top_k=2)
        assert len(results) <= 2
        # The most similar should be entry about Python web framework or Python data science
        if len(results) >= 1:
            assert results[0].content in ("Python web framework", "Python data science")

    async def test_batch_operations(self, store):
        """Test add_batch and delete_batch."""
        entries = [
            ("Content A", {"project_id": "batch", "index": "1"}),
            ("Content B", {"project_id": "batch", "index": "2"}),
            ("Content C", {"project_id": "batch", "index": "3"}),
        ]
        embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

        ids = await store.add_batch(entries, embeddings=embeddings)
        assert len(ids) == 3
        assert await store.count() == 3

        # Delete batch
        deleted = await store.delete_batch(ids[:2])
        assert deleted == 2
        assert await store.count() == 1
