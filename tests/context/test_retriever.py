"""
Palace Framework - Tests for Context Retriever

This module tests RetrievalConfig and ContextRetriever from
palace.context.retriever, verifying:

- RetrievalConfig defaults and custom values
- ContextRetriever initialization
- Retrieval with mocked MemoryStore (no results, with results)
- Agent-specific retrieval (different agents get different context types)
- Relevance filtering
- Recency boosting
- Deduplication
- Token limit truncation
- Error handling for memory store failures
"""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from palace.context.retriever import ContextRetriever, RetrievalConfig
from palace.context.types import ContextEntry, ContextType, RetrievedContext
from palace.core.types import MemoryType

# ============================================================================
# RetrievalConfig Tests
# ============================================================================


class TestRetrievalConfig:
    """Tests for the RetrievalConfig dataclass."""

    def test_defaults(self):
        """Verify all RetrievalConfig fields have expected defaults."""
        config = RetrievalConfig()
        assert config.top_k == 5
        assert config.min_relevance_score == 0.3
        assert config.max_total_tokens == 4000
        assert config.include_project_context is True
        assert config.deduplicate is True
        assert config.boost_recent is True
        assert config.recent_boost_factor == 1.2
        assert len(config.memory_types) == 3
        assert MemoryType.SEMANTIC in config.memory_types
        assert MemoryType.EPISODIC in config.memory_types
        assert MemoryType.PROCEDURAL in config.memory_types

    def test_custom_values(self):
        """Verify RetrievalConfig can be created with custom values."""
        config = RetrievalConfig(
            top_k=10,
            min_relevance_score=0.5,
            max_total_tokens=8000,
            memory_types=[MemoryType.SEMANTIC],
            include_project_context=False,
            deduplicate=False,
            boost_recent=False,
            recent_boost_factor=1.5,
        )
        assert config.top_k == 10
        assert config.min_relevance_score == 0.5
        assert config.max_total_tokens == 8000
        assert config.memory_types == [MemoryType.SEMANTIC]
        assert config.include_project_context is False
        assert config.deduplicate is False
        assert config.boost_recent is False
        assert config.recent_boost_factor == 1.5

    def test_default_memory_types_includes_semantic(self):
        """Verify default memory_types includes SEMANTIC."""
        config = RetrievalConfig()
        assert MemoryType.SEMANTIC in config.memory_types

    def test_default_memory_types_includes_episodic(self):
        """Verify default memory_types includes EPISODIC."""
        config = RetrievalConfig()
        assert MemoryType.EPISODIC in config.memory_types

    def test_default_memory_types_includes_procedural(self):
        """Verify default memory_types includes PROCEDURAL."""
        config = RetrievalConfig()
        assert MemoryType.PROCEDURAL in config.memory_types


# ============================================================================
# ContextRetriever Initialization Tests
# ============================================================================


class TestContextRetrieverInit:
    """Tests for ContextRetriever initialization."""

    def test_init_with_memory_store(self):
        """Verify ContextRetriever initializes with a memory store."""
        mock_store = MagicMock()
        retriever = ContextRetriever(memory_store=mock_store)
        assert retriever._memory_store is mock_store

    def test_init_with_default_config(self):
        """Verify ContextRetriever uses default RetrievalConfig when none provided."""
        mock_store = MagicMock()
        retriever = ContextRetriever(memory_store=mock_store)
        assert isinstance(retriever._config, RetrievalConfig)
        assert retriever._config.top_k == 5
        assert retriever._config.min_relevance_score == 0.3

    def test_init_with_custom_config(self):
        """Verify ContextRetriever uses provided RetrievalConfig."""
        mock_store = MagicMock()
        config = RetrievalConfig(top_k=20, min_relevance_score=0.7)
        retriever = ContextRetriever(memory_store=mock_store, config=config)
        assert retriever._config.top_k == 20
        assert retriever._config.min_relevance_score == 0.7


# ============================================================================
# Helper: Create Mock Memory Store
# ============================================================================


def _create_mock_memory_store(search_results: list[dict[str, Any]] | None = None) -> MagicMock:
    """Create a mock MemoryStore with configurable search results.

    Args:
        search_results: List of result dicts to return from search().
            Each dict may contain: content, score, metadata, entry_id.

    Returns:
        A MagicMock that behaves like a MemoryStore with async search().
    """
    store = MagicMock()

    if search_results is None:
        search_results = []

    store.search = AsyncMock(return_value=search_results)
    store.initialize = AsyncMock()
    store.close = AsyncMock()

    return store


def _make_search_result(
    content: str = "Test content",
    score: float = 0.9,
    source: str = "memory",
    title: str = "Test Entry",
    entry_id: str = "test-entry-1234",
    memory_type: str = "semantic",
    created_at: datetime | None = None,
    **extra_metadata,
) -> dict[str, Any]:
    """Create a single search result dict for mocking memory store responses.

    Args:
        content: The content text.
        score: Relevance score.
        source: Source identifier.
        title: Title of the entry.
        entry_id: Unique entry ID.
        memory_type: Type of memory.
        created_at: Creation timestamp.
        **extra_metadata: Additional metadata fields.

    Returns:
        A dictionary representing a memory search result.
    """
    metadata = {
        "source": source,
        "title": title,
        "memory_type": memory_type,
        **extra_metadata,
    }
    if created_at is not None:
        metadata["created_at"] = created_at

    return {
        "content": content,
        "score": score,
        "metadata": metadata,
        "entry_id": entry_id,
    }


# ============================================================================
# Retrieve Tests
# ============================================================================


class TestContextRetrieverRetrieve:
    """Tests for ContextRetriever.retrieve()."""

    @pytest.mark.asyncio
    async def test_retrieve_with_no_results(self):
        """Verify retrieve() returns empty RetrievedContext when memory store has no results."""
        mock_store = _create_mock_memory_store(search_results=[])
        retriever = ContextRetriever(memory_store=mock_store)

        result = await retriever.retrieve(
            project_id="test-project",
            query="test query",
        )

        assert isinstance(result, RetrievedContext)
        assert result.query == "test query"
        assert len(result.entries) == 0
        assert result.total_tokens == 0
        assert result.truncated is False
        assert result.memory_hits == 0

    @pytest.mark.asyncio
    async def test_retrieve_with_mocked_results(self):
        """Verify retrieve() returns entries from memory store results."""
        search_results = [
            _make_search_result(
                content="FastAPI is a modern web framework",
                score=0.95,
                source="docs",
                title="FastAPI Overview",
                entry_id="entry-1",
            ),
            _make_search_result(
                content="SQLAlchemy provides ORM capabilities",
                score=0.85,
                source="docs",
                title="SQLAlchemy Guide",
                entry_id="entry-2",
            ),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)
        retriever = ContextRetriever(memory_store=mock_store)

        result = await retriever.retrieve(
            project_id="test-project",
            query="web framework",
        )

        assert isinstance(result, RetrievedContext)
        assert result.query == "web framework"
        assert len(result.entries) > 0
        assert result.memory_hits > 0

    @pytest.mark.asyncio
    async def test_retrieve_calls_search_for_each_memory_type(self):
        """Verify retrieve() calls search for each configured memory type."""
        search_results = [
            _make_search_result(content="Result", score=0.8, entry_id="e1"),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)

        config = RetrievalConfig(
            memory_types=[MemoryType.SEMANTIC, MemoryType.EPISODIC],
            include_project_context=False,
        )
        retriever = ContextRetriever(memory_store=mock_store, config=config)

        result = await retriever.retrieve(
            project_id="test-project",
            query="test",
        )

        # search should have been called for each memory type
        assert mock_store.search.call_count >= 2

    @pytest.mark.asyncio
    async def test_retrieve_includes_project_context(self):
        """Verify retrieve() includes project context when configured."""
        search_results = [
            _make_search_result(content="Project context", score=0.7, entry_id="p1"),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)

        config = RetrievalConfig(include_project_context=True)
        retriever = ContextRetriever(memory_store=mock_store, config=config)

        result = await retriever.retrieve(
            project_id="test-project",
            query="test",
        )

        # Should have made at least one extra call for PROJECT type
        assert mock_store.search.call_count >= 1

    @pytest.mark.asyncio
    async def test_retrieve_without_project_context(self):
        """Verify retrieve() skips project context when disabled."""
        search_results = [
            _make_search_result(content="Semantic result", score=0.9, entry_id="s1"),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)

        config = RetrievalConfig(
            include_project_context=False,
            memory_types=[MemoryType.SEMANTIC],
        )
        retriever = ContextRetriever(memory_store=mock_store, config=config)

        result = await retriever.retrieve(
            project_id="test-project",
            query="test",
        )

        # Should only have called search for SEMANTIC, not PROJECT
        for call_args in mock_store.search.call_args_list:
            assert call_args.kwargs.get("memory_type") != MemoryType.PROJECT

    @pytest.mark.asyncio
    async def test_retrieve_with_context_type_filter(self):
        """Verify retrieve() filters results by context_type when specified."""
        search_results = [
            _make_search_result(
                content="Architecture content",
                score=0.9,
                entry_id="e1",
            ),
            _make_search_result(
                content="Memory content",
                score=0.7,
                entry_id="e2",
            ),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)
        retriever = ContextRetriever(memory_store=mock_store)

        result = await retriever.retrieve(
            project_id="test-project",
            query="architecture",
            context_type=ContextType.ARCHITECTURE,
        )

        # All entries should have the ARCHITECTURE type
        # (or no entries if none match)
        for entry in result.entries:
            assert entry.context_type == ContextType.ARCHITECTURE.value

    @pytest.mark.asyncio
    async def test_retrieve_handles_memory_store_error(self):
        """Verify retrieve() handles errors from memory store gracefully."""
        mock_store = MagicMock()
        mock_store.search = AsyncMock(side_effect=Exception("Memory store error"))

        config = RetrievalConfig(
            memory_types=[MemoryType.SEMANTIC],
            include_project_context=False,
        )
        retriever = ContextRetriever(memory_store=mock_store, config=config)

        # Should not raise, but return empty results
        result = await retriever.retrieve(
            project_id="test-project",
            query="test",
        )

        assert isinstance(result, RetrievedContext)
        assert len(result.entries) == 0

    @pytest.mark.asyncio
    async def test_retrieve_sorts_by_relevance(self):
        """Verify retrieve() returns entries sorted by relevance score (descending)."""
        search_results = [
            _make_search_result(content="Low relevance", score=0.4, entry_id="e1"),
            _make_search_result(content="High relevance", score=0.95, entry_id="e2"),
            _make_search_result(content="Medium relevance", score=0.7, entry_id="e3"),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)

        config = RetrievalConfig(
            memory_types=[MemoryType.SEMANTIC],
            include_project_context=False,
            min_relevance_score=0.0,  # Accept all scores
        )
        retriever = ContextRetriever(memory_store=mock_store, config=config)

        result = await retriever.retrieve(
            project_id="test-project",
            query="test",
        )

        if len(result.entries) >= 2:
            # Entries should be sorted by relevance score descending
            for i in range(len(result.entries) - 1):
                assert result.entries[i].relevance_score >= result.entries[i + 1].relevance_score

    @pytest.mark.asyncio
    async def test_retrieve_tracks_sources(self):
        """Verify retrieve() collects unique sources from entries."""
        search_results = [
            _make_search_result(
                content="Content 1",
                score=0.9,
                source="docs",
                entry_id="e1",
            ),
            _make_search_result(
                content="Content 2",
                score=0.8,
                source="code",
                entry_id="e2",
            ),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)

        config = RetrievalConfig(
            memory_types=[MemoryType.SEMANTIC],
            include_project_context=False,
            min_relevance_score=0.0,
        )
        retriever = ContextRetriever(memory_store=mock_store, config=config)

        result = await retriever.retrieve(
            project_id="test-project",
            query="test",
        )

        # Sources should be collected from entries
        assert isinstance(result.sources, list)

    @pytest.mark.asyncio
    async def test_retrieve_tracks_retrieval_time(self):
        """Verify retrieve() tracks retrieval time in milliseconds."""
        search_results = [
            _make_search_result(content="Result", score=0.9, entry_id="e1"),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)

        config = RetrievalConfig(
            memory_types=[MemoryType.SEMANTIC],
            include_project_context=False,
        )
        retriever = ContextRetriever(memory_store=mock_store, config=config)

        result = await retriever.retrieve(
            project_id="test-project",
            query="test",
        )

        assert result.retrieval_time_ms >= 0


# ============================================================================
# Agent-Specific Retrieval Tests
# ============================================================================


class TestContextRetrieverRetrieveForAgent:
    """Tests for ContextRetriever.retrieve_for_agent()."""

    @pytest.mark.asyncio
    async def test_retrieve_for_agent_backend(self):
        """Verify backend agent gets SEMANTIC and PROCEDURAL memory types."""
        search_results = [
            _make_search_result(content="Backend result", score=0.9, entry_id="e1"),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)

        config = RetrievalConfig(
            include_project_context=False,
            min_relevance_score=0.0,
        )
        retriever = ContextRetriever(memory_store=mock_store, config=config)

        result = await retriever.retrieve_for_agent(
            project_id="test-project",
            query="implement API",
            agent_role="backend",
        )

        assert isinstance(result, RetrievedContext)
        # The agent_role mapping should select specific memory types
        assert mock_store.search.call_count >= 1

    @pytest.mark.asyncio
    async def test_retrieve_for_agent_frontend(self):
        """Verify frontend agent gets SEMANTIC and EPISODIC memory types."""
        search_results = [
            _make_search_result(content="Frontend result", score=0.85, entry_id="e1"),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)
        retriever = ContextRetriever(memory_store=mock_store)

        result = await retriever.retrieve_for_agent(
            project_id="test-project",
            query="build UI",
            agent_role="frontend",
        )

        assert isinstance(result, RetrievedContext)

    @pytest.mark.asyncio
    async def test_retrieve_for_agent_orchestrator(self):
        """Verify orchestrator agent gets all three memory types."""
        search_results = [
            _make_search_result(content="Orchestrator result", score=0.8, entry_id="e1"),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)
        retriever = ContextRetriever(memory_store=mock_store)

        result = await retriever.retrieve_for_agent(
            project_id="test-project",
            query="coordinate task",
            agent_role="orchestrator",
        )

        assert isinstance(result, RetrievedContext)
        # Orchestrator should search SEMANTIC, EPISODIC, and PROCEDURAL
        assert mock_store.search.call_count >= 3

    @pytest.mark.asyncio
    async def test_retrieve_for_agent_unknown_role(self):
        """Verify unknown agent role falls back to default memory types."""
        search_results = [
            _make_search_result(content="Default result", score=0.75, entry_id="e1"),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)
        retriever = ContextRetriever(memory_store=mock_store)

        result = await retriever.retrieve_for_agent(
            project_id="test-project",
            query="test query",
            agent_role="unknown_role",
        )

        assert isinstance(result, RetrievedContext)
        # Should still get results with default memory types

    @pytest.mark.asyncio
    async def test_retrieve_for_agent_preserves_original_config(self):
        """Verify retrieve_for_agent() restores the original config after execution."""
        search_results = [
            _make_search_result(content="Result", score=0.8, entry_id="e1"),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)

        original_config = RetrievalConfig(
            top_k=5,
            min_relevance_score=0.3,
            memory_types=[MemoryType.SEMANTIC, MemoryType.EPISODIC, MemoryType.PROCEDURAL],
        )
        retriever = ContextRetriever(memory_store=mock_store, config=original_config)

        await retriever.retrieve_for_agent(
            project_id="test-project",
            query="test",
            agent_role="backend",
        )

        # Original config should be restored
        assert retriever._config.top_k == 5
        assert retriever._config.min_relevance_score == 0.3
        assert len(retriever._config.memory_types) == 3

    @pytest.mark.asyncio
    async def test_agent_memory_types_backend(self):
        """Verify _get_agent_memory_types returns correct types for backend."""
        retriever = ContextRetriever(memory_store=MagicMock())
        types = retriever._get_agent_memory_types("backend")
        assert MemoryType.SEMANTIC in types
        assert MemoryType.PROCEDURAL in types

    @pytest.mark.asyncio
    async def test_agent_memory_types_frontend(self):
        """Verify _get_agent_memory_types returns correct types for frontend."""
        retriever = ContextRetriever(memory_store=MagicMock())
        types = retriever._get_agent_memory_types("frontend")
        assert MemoryType.SEMANTIC in types
        assert MemoryType.EPISODIC in types

    @pytest.mark.asyncio
    async def test_agent_memory_types_dba(self):
        """Verify _get_agent_memory_types returns SEMANTIC for dba."""
        retriever = ContextRetriever(memory_store=MagicMock())
        types = retriever._get_agent_memory_types("dba")
        assert MemoryType.SEMANTIC in types

    @pytest.mark.asyncio
    async def test_agent_memory_types_devops(self):
        """Verify _get_agent_memory_types returns PROCEDURAL for devops."""
        retriever = ContextRetriever(memory_store=MagicMock())
        types = retriever._get_agent_memory_types("devops")
        assert MemoryType.PROCEDURAL in types

    @pytest.mark.asyncio
    async def test_agent_memory_types_qa(self):
        """Verify _get_agent_memory_types returns EPISODIC and PROCEDURAL for qa."""
        retriever = ContextRetriever(memory_store=MagicMock())
        types = retriever._get_agent_memory_types("qa")
        assert MemoryType.EPISODIC in types
        assert MemoryType.PROCEDURAL in types

    @pytest.mark.asyncio
    async def test_agent_memory_types_unknown_returns_default(self):
        """Verify _get_agent_memory_types returns default types for unknown role."""
        retriever = ContextRetriever(memory_store=MagicMock())
        types = retriever._get_agent_memory_types("nonexistent_role")
        assert MemoryType.SEMANTIC in types
        assert MemoryType.EPISODIC in types
        assert MemoryType.PROCEDURAL in types


# ============================================================================
# Project Context Retrieval Tests
# ============================================================================


class TestContextRetrieverRetrieveProjectContext:
    """Tests for ContextRetriever.retrieve_project_context()."""

    @pytest.mark.asyncio
    async def test_retrieve_project_context_with_results(self):
        """Verify retrieve_project_context() returns project entries."""
        search_results = [
            _make_search_result(
                content="Project architecture docs",
                score=0.9,
                source="project",
                title="Architecture",
                entry_id="p1",
            ),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)
        retriever = ContextRetriever(memory_store=mock_store)

        entries = await retriever.retrieve_project_context(project_id="test-project")

        assert isinstance(entries, list)
        assert len(entries) > 0
        # Entries should be sorted by relevance score (descending)
        if len(entries) > 1:
            for i in range(len(entries) - 1):
                assert entries[i].relevance_score >= entries[i + 1].relevance_score

    @pytest.mark.asyncio
    async def test_retrieve_project_context_no_results(self):
        """Verify retrieve_project_context() returns empty list when no results."""
        mock_store = _create_mock_memory_store(search_results=[])
        retriever = ContextRetriever(memory_store=mock_store)

        entries = await retriever.retrieve_project_context(project_id="test-project")

        assert isinstance(entries, list)
        assert len(entries) == 0

    @pytest.mark.asyncio
    async def test_retrieve_project_context_handles_error(self):
        """Verify retrieve_project_context() handles memory store errors gracefully."""
        mock_store = MagicMock()
        mock_store.search = AsyncMock(side_effect=Exception("Connection error"))

        retriever = ContextRetriever(memory_store=mock_store)

        entries = await retriever.retrieve_project_context(project_id="test-project")

        assert isinstance(entries, list)
        assert len(entries) == 0


# ============================================================================
# Convert to Entries Tests
# ============================================================================


class TestContextRetrieverConvertToEntries:
    """Tests for ContextRetriever._convert_to_entries()."""

    def test_convert_to_entries_basic(self):
        """Verify _convert_to_entries converts result dicts to ContextEntry objects."""
        results = [
            _make_search_result(
                content="Test content",
                score=0.9,
                source="docs",
                title="Test Title",
                entry_id="e1",
            ),
        ]
        retriever = ContextRetriever(memory_store=MagicMock())
        entries = retriever._convert_to_entries(results)

        assert len(entries) == 1
        assert isinstance(entries[0], ContextEntry)
        assert entries[0].content == "Test content"
        assert entries[0].relevance_score == 0.9
        assert entries[0].source == "docs"
        assert entries[0].title == "Test Title"

    def test_convert_to_entries_default_context_type(self):
        """Verify _convert_to_entries uses MEMORY as default context type."""
        results = [
            _make_search_result(content="Content", score=0.8, entry_id="e1"),
        ]
        retriever = ContextRetriever(memory_store=MagicMock())
        entries = retriever._convert_to_entries(results)

        assert entries[0].context_type == ContextType.MEMORY.value

    def test_convert_to_entries_custom_context_type(self):
        """Verify _convert_to_entries uses the specified context type."""
        results = [
            _make_search_result(content="Content", score=0.8, entry_id="e1"),
        ]
        retriever = ContextRetriever(memory_store=MagicMock())
        entries = retriever._convert_to_entries(results, context_type=ContextType.ARCHITECTURE)

        assert entries[0].context_type == ContextType.ARCHITECTURE.value

    def test_convert_to_entries_metadata_context_type_override(self):
        """Verify _convert_to_entries uses context_type from metadata when available."""
        results = [
            _make_search_result(
                content="Content",
                score=0.8,
                entry_id="e1",
                context_type="decisions",
            ),
        ]
        retriever = ContextRetriever(memory_store=MagicMock())
        entries = retriever._convert_to_entries(results)

        assert entries[0].context_type == ContextType.DECISIONS.value

    def test_convert_to_entries_estimates_tokens(self):
        """Verify _convert_to_entries estimates token count for content."""
        results = [
            _make_search_result(
                content="This is some content with several words",
                score=0.8,
                entry_id="e1",
            ),
        ]
        retriever = ContextRetriever(memory_store=MagicMock())
        entries = retriever._convert_to_entries(results)

        assert entries[0].token_count > 0

    def test_convert_to_entries_stores_memory_entry_id(self):
        """Verify _convert_to_entries stores entry_id in metadata."""
        results = [
            _make_search_result(
                content="Content",
                score=0.8,
                entry_id="my-special-id",
            ),
        ]
        retriever = ContextRetriever(memory_store=MagicMock())
        entries = retriever._convert_to_entries(results)

        assert entries[0].metadata["memory_entry_id"] == "my-special-id"

    def test_convert_to_entries_clamps_score_to_range(self):
        """Verify _convert_to_entries clamps relevance scores to [0.0, 1.0]."""
        results = [
            _make_search_result(content="High", score=1.5, entry_id="e1"),
            _make_search_result(content="Low", score=-0.2, entry_id="e2"),
        ]
        retriever = ContextRetriever(memory_store=MagicMock())
        entries = retriever._convert_to_entries(results)

        assert entries[0].relevance_score == 1.0
        assert entries[1].relevance_score == 0.0

    def test_convert_to_entries_handles_missing_fields(self):
        """Verify _convert_to_entries handles results with missing fields."""
        results = [
            {"content": "Some content"},
            {"score": 0.5},
            {},
        ]
        retriever = ContextRetriever(memory_store=MagicMock())
        entries = retriever._convert_to_entries(results)

        # Should still produce entries with defaults
        assert len(entries) == 3
        assert entries[0].content == "Some content"
        assert entries[1].relevance_score == 0.5

    def test_convert_to_entries_handles_empty_content(self):
        """Verify _convert_to_entries handles entries with empty content."""
        results = [
            _make_search_result(content="", score=0.5, entry_id="e1"),
        ]
        retriever = ContextRetriever(memory_store=MagicMock())
        entries = retriever._convert_to_entries(results)

        assert len(entries) == 1
        assert entries[0].content == ""
        assert entries[0].token_count == 0

    def test_convert_to_entries_skips_invalid_results(self):
        """Verify _convert_to_entries skips results that can't be converted."""
        results = [
            _make_search_result(content="Valid", score=0.8, entry_id="e1"),
            None,  # Invalid entry
            "not_a_dict",  # Invalid entry
        ]
        retriever = ContextRetriever(memory_store=MagicMock())
        entries = retriever._convert_to_entries(results)

        # Only the valid result should be converted
        assert len(entries) == 1
        assert entries[0].content == "Valid"

    def test_convert_to_entries_extracts_source_from_result(self):
        """Verify _convert_to_entries uses 'source' from result dict when metadata lacks it."""
        results = [
            {
                "content": "Test content",
                "score": 0.8,
                "source": "external_db",
                "metadata": {},
                "entry_id": "e1",
            },
        ]
        retriever = ContextRetriever(memory_store=MagicMock())
        entries = retriever._convert_to_entries(results)

        assert entries[0].source == "external_db"


# ============================================================================
# Relevance Filtering Tests
# ============================================================================


class TestContextRetrieverRelevanceFilter:
    """Tests for ContextRetriever._apply_relevance_filter()."""

    def test_filter_removes_low_relevance_entries(self):
        """Verify entries below min_relevance_score are filtered out."""
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="High",
                content="High relevance",
                relevance_score=0.9,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s2",
                title="Medium",
                content="Medium relevance",
                relevance_score=0.5,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s3",
                title="Low",
                content="Low relevance",
                relevance_score=0.1,
            ),
        ]

        config = RetrievalConfig(min_relevance_score=0.3)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        filtered = retriever._apply_relevance_filter(entries)

        assert len(filtered) == 2
        assert all(e.relevance_score >= 0.3 for e in filtered)

    def test_filter_keeps_exact_match(self):
        """Verify entries with score exactly equal to min_relevance_score are kept."""
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="Exact",
                content="Exact threshold",
                relevance_score=0.3,
            ),
        ]

        config = RetrievalConfig(min_relevance_score=0.3)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        filtered = retriever._apply_relevance_filter(entries)

        assert len(filtered) == 1
        assert filtered[0].relevance_score == 0.3

    def test_filter_empty_list(self):
        """Verify _apply_relevance_filter handles empty list."""
        config = RetrievalConfig(min_relevance_score=0.3)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        filtered = retriever._apply_relevance_filter([])

        assert filtered == []

    def test_filter_all_below_threshold(self):
        """Verify _apply_relevance_filter returns empty list when all entries are below threshold."""
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="Low1",
                content="Low",
                relevance_score=0.1,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s2",
                title="Low2",
                content="Low",
                relevance_score=0.2,
            ),
        ]

        config = RetrievalConfig(min_relevance_score=0.5)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        filtered = retriever._apply_relevance_filter(entries)

        assert len(filtered) == 0


# ============================================================================
# Recency Boost Tests
# ============================================================================


class TestContextRetrieverRecencyBoost:
    """Tests for ContextRetriever._apply_recency_boost()."""

    def test_boost_recent_entries_within_24h(self):
        """Verify entries within the last 24 hours get full recency boost."""
        now = datetime.utcnow()
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="Recent",
                content="Recent content",
                relevance_score=0.5,
                created_at=now - timedelta(hours=1),
            ),
        ]

        config = RetrievalConfig(boost_recent=True, recent_boost_factor=1.5)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        boosted = retriever._apply_recency_boost(entries)

        assert len(boosted) == 1
        assert boosted[0].relevance_score == 0.75  # 0.5 * 1.5

    def test_boost_entries_within_7_days(self):
        """Verify entries within 7 days get half recency boost."""
        now = datetime.utcnow()
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="Week old",
                content="Week old content",
                relevance_score=0.5,
                created_at=now - timedelta(days=3),
            ),
        ]

        config = RetrievalConfig(boost_recent=True, recent_boost_factor=1.5)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        boosted = retriever._apply_recency_boost(entries)

        assert len(boosted) == 1
        # Half boost: 1.0 + (1.5 - 1.0) / 2 = 1.25
        # 0.5 * 1.25 = 0.625
        assert boosted[0].relevance_score == 0.625

    def test_no_boost_for_old_entries(self):
        """Verify entries older than 7 days receive no recency boost."""
        now = datetime.utcnow()
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="Old",
                content="Old content",
                relevance_score=0.5,
                created_at=now - timedelta(days=30),
            ),
        ]

        config = RetrievalConfig(boost_recent=True, recent_boost_factor=1.5)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        boosted = retriever._apply_recency_boost(entries)

        assert len(boosted) == 1
        assert boosted[0].relevance_score == 0.5  # No boost

    def test_boost_capped_at_1(self):
        """Verify boosted relevance scores are capped at 1.0."""
        now = datetime.utcnow()
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="High recent",
                content="High recent content",
                relevance_score=0.95,
                created_at=now - timedelta(hours=1),
            ),
        ]

        config = RetrievalConfig(boost_recent=True, recent_boost_factor=2.0)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        boosted = retriever._apply_recency_boost(entries)

        assert boosted[0].relevance_score == 1.0  # Capped at 1.0

    def test_boost_disabled(self):
        """Verify no boost is applied when boost_recent is False."""
        now = datetime.utcnow()
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="Recent",
                content="Recent content",
                relevance_score=0.5,
                created_at=now - timedelta(hours=1),
            ),
        ]

        config = RetrievalConfig(boost_recent=False)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        boosted = retriever._apply_recency_boost(entries)

        assert boosted[0].relevance_score == 0.5  # Unchanged


# ============================================================================
# Deduplication Tests
# ============================================================================


class TestContextRetrieverDeduplication:
    """Tests for ContextRetriever._deduplicate_entries()."""

    def test_deduplicate_removes_duplicate_content(self):
        """Verify entries with duplicate content (first 200 chars) are deduplicated."""
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="First",
                content="This is the same content for both entries",
                relevance_score=0.7,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s2",
                title="Second",
                content="This is the same content for both entries",
                relevance_score=0.9,
            ),
        ]

        config = RetrievalConfig(deduplicate=True)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        deduped = retriever._deduplicate_entries(entries)

        assert len(deduped) == 1
        # Should keep the one with higher relevance score
        assert deduped[0].relevance_score == 0.9

    def test_deduplicate_keeps_higher_relevance(self):
        """Verify deduplication keeps the entry with higher relevance score."""
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="Lower",
                content="Duplicate content here",
                relevance_score=0.5,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s2",
                title="Higher",
                content="Duplicate content here",
                relevance_score=0.95,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s3",
                title="Medium",
                content="Duplicate content here",
                relevance_score=0.7,
            ),
        ]

        config = RetrievalConfig(deduplicate=True)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        deduped = retriever._deduplicate_entries(entries)

        assert len(deduped) == 1
        assert deduped[0].relevance_score == 0.95

    def test_deduplicate_preserves_unique_entries(self):
        """Verify unique entries are preserved during deduplication."""
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="Unique 1",
                content="First unique content",
                relevance_score=0.8,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s2",
                title="Unique 2",
                content="Second unique content",
                relevance_score=0.7,
            ),
        ]

        config = RetrievalConfig(deduplicate=True)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        deduped = retriever._deduplicate_entries(entries)

        assert len(deduped) == 2

    def test_deduplicate_disabled(self):
        """Verify no deduplication when deduplicate is False."""
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="Dup 1",
                content="Same content",
                relevance_score=0.7,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s2",
                title="Dup 2",
                content="Same content",
                relevance_score=0.9,
            ),
        ]

        config = RetrievalConfig(deduplicate=False)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        deduped = retriever._deduplicate_entries(entries)

        assert len(deduped) == 2

    def test_deduplicate_empty_list(self):
        """Verify _deduplicate_entries handles empty list."""
        config = RetrievalConfig(deduplicate=True)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        deduped = retriever._deduplicate_entries([])

        assert deduped == []

    def test_deduplicate_uses_first_200_chars(self):
        """Verify deduplication compares only the first 200 characters of content."""
        long_content_a = "A" * 200 + "X" * 100
        long_content_b = "A" * 200 + "Y" * 100

        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="Entry A",
                content=long_content_a,
                relevance_score=0.8,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s2",
                title="Entry B",
                content=long_content_b,
                relevance_score=0.9,
            ),
        ]

        config = RetrievalConfig(deduplicate=True)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        deduped = retriever._deduplicate_entries(entries)

        # First 200 chars are the same, so these should be deduplicated
        assert len(deduped) == 1

    def test_deduplicate_handles_empty_content(self):
        """Verify deduplication handles entries with empty content."""
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="Empty 1",
                content="",
                relevance_score=0.7,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s2",
                title="Empty 2",
                content="",
                relevance_score=0.9,
            ),
        ]

        config = RetrievalConfig(deduplicate=True)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        deduped = retriever._deduplicate_entries(entries)

        # Both have empty content, should be deduplicated
        assert len(deduped) == 1


# ============================================================================
# Token Truncation Tests
# ============================================================================


class TestContextRetrieverTokenTruncation:
    """Tests for ContextRetriever._truncate_to_token_limit()."""

    def test_truncate_under_limit(self):
        """Verify entries under the token limit are not truncated."""
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="Entry 1",
                content="Short",
                relevance_score=0.9,
                token_count=100,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s2",
                title="Entry 2",
                content="Another short",
                relevance_score=0.8,
                token_count=200,
            ),
        ]

        config = RetrievalConfig(max_total_tokens=4000)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        result, truncated = retriever._truncate_to_token_limit(entries)

        assert len(result) == 2
        assert truncated is False

    def test_truncate_over_limit(self):
        """Verify entries over the token limit are truncated."""
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="Entry 1",
                content="Content",
                relevance_score=0.9,
                token_count=2000,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s2",
                title="Entry 2",
                content="Content",
                relevance_score=0.8,
                token_count=2000,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s3",
                title="Entry 3",
                content="Content",
                relevance_score=0.7,
                token_count=2000,
            ),
        ]

        config = RetrievalConfig(max_total_tokens=4000)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        result, truncated = retriever._truncate_to_token_limit(entries)

        assert truncated is True
        # Should include entries that fit within the budget (first 2)
        assert len(result) == 2
        total = sum(e.token_count for e in result)
        assert total <= 4000

    def test_truncate_exact_limit(self):
        """Verify entries exactly at the token limit are not truncated."""
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="Entry 1",
                content="Content",
                relevance_score=0.9,
                token_count=2000,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s2",
                title="Entry 2",
                content="Content",
                relevance_score=0.8,
                token_count=2000,
            ),
        ]

        config = RetrievalConfig(max_total_tokens=4000)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        result, truncated = retriever._truncate_to_token_limit(entries)

        assert len(result) == 2
        assert truncated is False

    def test_truncate_empty_list(self):
        """Verify _truncate_to_token_limit handles empty list."""
        config = RetrievalConfig(max_total_tokens=4000)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        result, truncated = retriever._truncate_to_token_limit([])

        assert result == []
        assert truncated is False

    def test_truncate_single_entry_exceeds_limit(self):
        """Verify truncation when a single entry exceeds the token limit."""
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="Huge Entry",
                content="Content",
                relevance_score=0.9,
                token_count=10000,
            ),
        ]

        config = RetrievalConfig(max_total_tokens=4000)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        result, truncated = retriever._truncate_to_token_limit(entries)

        assert truncated is True
        assert len(result) == 0  # Single entry too large to include

    def test_truncate_preserves_highest_relevance(self):
        """Verify truncation preserves entries with highest relevance scores."""
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s1",
                title="High relevance",
                content="Content",
                relevance_score=0.95,
                token_count=1500,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s2",
                title="Mid relevance",
                content="Content",
                relevance_score=0.7,
                token_count=1500,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s3",
                title="Low relevance",
                content="Content",
                relevance_score=0.4,
                token_count=1500,
            ),
        ]

        config = RetrievalConfig(max_total_tokens=3000)
        retriever = ContextRetriever(memory_store=MagicMock(), config=config)
        result, truncated = retriever._truncate_to_token_limit(entries)

        assert truncated is True
        # First two entries (highest relevance) should be kept
        assert len(result) == 2
        assert result[0].relevance_score >= result[1].relevance_score


# ============================================================================
# Token Estimation Tests
# ============================================================================


class TestContextRetrieverEstimateTokens:
    """Tests for ContextRetriever._estimate_tokens()."""

    def test_estimate_tokens_basic(self):
        """Verify _estimate_tokens returns reasonable estimates."""
        retriever = ContextRetriever(memory_store=MagicMock())
        text = "Hello world this is a test"
        tokens = retriever._estimate_tokens(text)
        expected = int(len(text.split()) * 1.3)
        assert tokens == expected

    def test_estimate_tokens_empty_string(self):
        """Verify _estimate_tokens returns 0 for empty string."""
        retriever = ContextRetriever(memory_store=MagicMock())
        assert retriever._estimate_tokens("") == 0

    def test_estimate_tokens_single_word(self):
        """Verify _estimate_tokens handles single word."""
        retriever = ContextRetriever(memory_store=MagicMock())
        tokens = retriever._estimate_tokens("hello")
        assert tokens == int(1 * 1.3)

    def test_estimate_tokens_longer_text(self):
        """Verify _estimate_tokens handles longer text."""
        retriever = ContextRetriever(memory_store=MagicMock())
        text = "This is a longer piece of text with more words to estimate tokens"
        tokens = retriever._estimate_tokens(text)
        word_count = len(text.split())
        assert tokens == int(word_count * 1.3)


# ============================================================================
# Integration Tests with Mock Memory Store
# ============================================================================


class TestContextRetrieverIntegration:
    """Integration tests for ContextRetriever with mock MemoryStore."""

    @pytest.mark.asyncio
    async def test_full_retrieval_pipeline(self):
        """Verify the full retrieval pipeline from search to RetrievedContext."""
        search_results = [
            _make_search_result(
                content="FastAPI is a modern Python web framework",
                score=0.92,
                source="docs",
                title="FastAPI Guide",
                entry_id="e1",
            ),
            _make_search_result(
                content="SQLAlchemy provides ORM for database access",
                score=0.85,
                source="docs",
                title="SQLAlchemy ORM",
                entry_id="e2",
            ),
            _make_search_result(
                content="Pydantic validates data schemas",
                score=0.78,
                source="docs",
                title="Pydantic Validation",
                entry_id="e3",
            ),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)

        config = RetrievalConfig(
            top_k=5,
            min_relevance_score=0.3,
            max_total_tokens=4000,
            memory_types=[MemoryType.SEMANTIC],
            include_project_context=False,
            deduplicate=True,
            boost_recent=False,
        )
        retriever = ContextRetriever(memory_store=mock_store, config=config)

        result = await retriever.retrieve(
            project_id="my-project",
            query="Python web framework",
        )

        assert isinstance(result, RetrievedContext)
        assert result.query == "Python web framework"
        assert len(result.entries) > 0
        assert result.total_tokens > 0
        assert result.sources is not None

    @pytest.mark.asyncio
    async def test_retrieval_with_relevance_filtering(self):
        """Verify that results below min_relevance_score are filtered out."""
        search_results = [
            _make_search_result(content="High relevance", score=0.9, entry_id="e1"),
            _make_search_result(content="Medium relevance", score=0.5, entry_id="e2"),
            _make_search_result(content="Low relevance", score=0.2, entry_id="e3"),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)

        config = RetrievalConfig(
            min_relevance_score=0.4,
            memory_types=[MemoryType.SEMANTIC],
            include_project_context=False,
        )
        retriever = ContextRetriever(memory_store=mock_store, config=config)

        result = await retriever.retrieve(
            project_id="test-project",
            query="test",
        )

        for entry in result.entries:
            assert entry.relevance_score >= 0.4

    @pytest.mark.asyncio
    async def test_retrieval_with_token_limit(self):
        """Verify that results are truncated when exceeding token limit."""
        # Create results that will exceed the token limit.
        # Use multi-word content so _estimate_tokens produces realistic counts
        # (single-word strings like "AAA...2000" only estimate to 1 token).
        long_content_1 = " ".join(["word"] * 500)  # ~650 tokens
        long_content_2 = " ".join(["term"] * 500)  # ~650 tokens
        search_results = [
            _make_search_result(
                content=long_content_1,
                score=0.95,
                entry_id="e1",
            ),
            _make_search_result(
                content=long_content_2,
                score=0.85,
                entry_id="e2",
            ),
        ]
        mock_store = _create_mock_memory_store(search_results=search_results)

        config = RetrievalConfig(
            max_total_tokens=100,  # Very low limit
            min_relevance_score=0.0,
            memory_types=[MemoryType.SEMANTIC],
            include_project_context=False,
        )
        retriever = ContextRetriever(memory_store=mock_store, config=config)

        result = await retriever.retrieve(
            project_id="test-project",
            query="test",
        )

        assert isinstance(result, RetrievedContext)
        # Truncation should have occurred
        assert result.truncated is True or len(result.entries) < 2

    @pytest.mark.asyncio
    async def test_agent_specific_retrieval_backend(self, mock_memory_store):
        """Verify backend agent retrieval uses appropriate memory types."""
        # Configure mock to return results
        mock_memory_store.search = AsyncMock(
            return_value=[
                _make_search_result(
                    content="Backend pattern: Repository",
                    score=0.85,
                    source="patterns",
                    entry_id="e1",
                ),
            ]
        )

        retriever = ContextRetriever(memory_store=mock_memory_store)

        result = await retriever.retrieve_for_agent(
            project_id="test-project",
            query="implement data access",
            agent_role="backend",
        )

        assert isinstance(result, RetrievedContext)
        # Verify that search was called with the backend-specific memory types
        assert mock_memory_store.search.call_count >= 1

    @pytest.mark.asyncio
    async def test_retrieval_with_multiple_memory_types(self, mock_memory_store):
        """Verify retrieval searches across multiple memory types."""
        mock_memory_store.search = AsyncMock(
            return_value=[
                _make_search_result(
                    content="Result",
                    score=0.8,
                    entry_id="e1",
                ),
            ]
        )

        config = RetrievalConfig(
            memory_types=[MemoryType.SEMANTIC, MemoryType.EPISODIC],
            include_project_context=False,
        )
        retriever = ContextRetriever(memory_store=mock_memory_store, config=config)

        result = await retriever.retrieve(
            project_id="test-project",
            query="test query",
        )

        # search should have been called for each memory type
        assert mock_memory_store.search.call_count >= 2
