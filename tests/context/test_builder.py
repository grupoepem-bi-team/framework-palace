"""
Palace Framework - Tests for Context Builder

This module tests the ContextBuilder from palace.context.builder, verifying:

- Token budget allocation (10% system, 30% project, 30% memory, 20% session, 10% task)
- Context building with all sections
- Project loading and caching
- Memory section building with mocked retriever
- Session section building with mocked session manager
- Task section building and truncation
- Prompt assembly and token estimation
- Error handling when dependencies fail
"""

from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from palace.context.builder import ContextBuilder
from palace.context.retriever import ContextRetriever, RetrievalConfig
from palace.context.session import SessionManager
from palace.context.types import (
    ContextEntry,
    ContextType,
    ProjectConfig,
    RetrievedContext,
    SessionConfig,
)

# ============================================================================
# Fixtures
# ============================================================================


def _make_context_entry(
    content: str = "Test content",
    context_type: ContextType = ContextType.MEMORY,
    source: str = "memory",
    title: str = "Test Entry",
    relevance_score: float = 0.8,
    token_count: int = 10,
) -> ContextEntry:
    """Create a ContextEntry for testing."""
    return ContextEntry(
        context_type=context_type,
        source=source,
        title=title,
        content=content,
        relevance_score=relevance_score,
        token_count=token_count,
    )


def _make_retrieved_context(
    query: str = "test query",
    entries: list[ContextEntry] | None = None,
    total_tokens: int = 0,
    truncated: bool = False,
    sources: list[str] | None = None,
    memory_hits: int = 0,
    retrieval_time_ms: int = 50,
) -> RetrievedContext:
    """Create a RetrievedContext for testing."""
    if entries is None:
        entries = []
    if sources is None:
        sources = [e.source for e in entries] if entries else []
    return RetrievedContext(
        query=query,
        entries=entries,
        total_tokens=total_tokens or sum(e.token_count for e in entries),
        truncated=truncated,
        sources=sources,
        memory_hits=memory_hits or len(entries),
        retrieval_time_ms=retrieval_time_ms,
    )


def _make_project_config(
    project_id: str = "test-project",
    name: str = "Test Project",
    root_path: str = "/projects/test",
    context_path: str = "/projects/test/ai_context",
    stack: dict[str, str] | None = None,
    conventions: list[str] | None = None,
    decisions: list[str] | None = None,
    constraints: list[str] | None = None,
) -> ProjectConfig:
    """Create a ProjectConfig for testing."""
    if stack is None:
        stack = {"backend": "fastapi", "frontend": "react", "database": "postgresql"}
    if conventions is None:
        conventions = ["Use type hints", "Follow PEP 8"]
    if decisions is None:
        decisions = ["ADR-001: Use FastAPI", "ADR-002: Use SQLAlchemy"]
    if constraints is None:
        constraints = ["Response time < 200ms"]
    return ProjectConfig(
        project_id=project_id,
        name=name,
        description="Test project description",
        root_path=Path(root_path),
        context_path=Path(context_path),
        stack=stack,
        conventions=conventions,
        decisions=decisions,
        constraints=constraints,
        last_loaded=datetime.utcnow(),
    )


@pytest.fixture
def mock_memory_store():
    """Create a mock MemoryStore for ContextBuilder."""
    store = MagicMock()
    store.initialize = AsyncMock()
    store.close = AsyncMock()
    store.store = AsyncMock(return_value="test-entry-id")
    store.search = AsyncMock(return_value=[])
    store.retrieve = AsyncMock(return_value={})
    store.count = AsyncMock(return_value=0)
    store.delete = AsyncMock(return_value=True)
    store.clear = AsyncMock()
    return store


@pytest.fixture
def builder(mock_memory_store) -> ContextBuilder:
    """Create a ContextBuilder with default settings and mocked memory store."""
    return ContextBuilder(
        memory_store=mock_memory_store,
        max_context_tokens=8000,
    )


@pytest.fixture
def builder_small_budget(mock_memory_store) -> ContextBuilder:
    """Create a ContextBuilder with a small token budget for truncation tests."""
    return ContextBuilder(
        memory_store=mock_memory_store,
        max_context_tokens=200,
    )


# ============================================================================
# Initialization Tests
# ============================================================================


class TestContextBuilderInit:
    """Tests for ContextBuilder initialization."""

    def test_init_with_memory_store(self, mock_memory_store):
        """Verify ContextBuilder initializes with a memory store."""
        builder = ContextBuilder(memory_store=mock_memory_store)
        assert builder._memory_store is mock_memory_store

    def test_init_default_max_context_tokens(self, mock_memory_store):
        """Verify default max_context_tokens is 8000."""
        builder = ContextBuilder(memory_store=mock_memory_store)
        assert builder._max_context_tokens == 8000

    def test_init_custom_max_context_tokens(self, mock_memory_store):
        """Verify custom max_context_tokens is set correctly."""
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=16000,
        )
        assert builder._max_context_tokens == 16000

    def test_init_creates_retriever(self, mock_memory_store):
        """Verify ContextBuilder creates a ContextRetriever."""
        builder = ContextBuilder(memory_store=mock_memory_store)
        assert isinstance(builder._retriever, ContextRetriever)

    def test_init_creates_session_manager(self, mock_memory_store):
        """Verify ContextBuilder creates a SessionManager."""
        builder = ContextBuilder(memory_store=mock_memory_store)
        assert isinstance(builder._session_manager, SessionManager)

    def test_init_custom_retriever_config(self, mock_memory_store):
        """Verify ContextBuilder uses custom RetrievalConfig."""
        config = RetrievalConfig(top_k=20, min_relevance_score=0.5)
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            retriever_config=config,
        )
        assert builder._retriever._config.top_k == 20
        assert builder._retriever._config.min_relevance_score == 0.5

    def test_init_custom_session_config(self, mock_memory_store):
        """Verify ContextBuilder uses custom SessionConfig."""
        config = SessionConfig(max_messages=50, auto_summarize=False)
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            session_config=config,
        )
        assert builder._session_manager._config.max_messages == 50
        assert builder._session_manager._config.auto_summarize is False

    def test_init_no_project_loader(self, mock_memory_store):
        """Verify project_loader is None by default."""
        builder = ContextBuilder(memory_store=mock_memory_store)
        assert builder._project_loader is None

    def test_init_empty_loaded_projects(self, mock_memory_store):
        """Verify loaded_projects dict is empty by default."""
        builder = ContextBuilder(memory_store=mock_memory_store)
        assert builder._loaded_projects == {}


# ============================================================================
# Token Budget Allocation Tests
# ============================================================================


class TestCalculateBudgets:
    """Tests for ContextBuilder._calculate_budgets()."""

    def test_default_budget_allocation(self, builder):
        """Verify default budget allocation follows 10/30/30/20/10 split."""
        budgets = builder._calculate_budgets()
        assert budgets["system"] == 800  # 10% of 8000
        assert budgets["project"] == 2400  # 30% of 8000
        assert budgets["memory"] == 2400  # 30% of 8000
        assert budgets["session"] == 1600  # 20% of 8000
        assert budgets["task"] == 800  # 10% of 8000

    def test_budget_allocation_custom_tokens(self, mock_memory_store):
        """Verify budget allocation scales with custom max_context_tokens."""
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=16000,
        )
        budgets = builder._calculate_budgets()
        assert budgets["system"] == 1600  # 10% of 16000
        assert budgets["project"] == 4800  # 30% of 16000
        assert budgets["memory"] == 4800  # 30% of 16000
        assert budgets["session"] == 3200  # 20% of 16000
        assert budgets["task"] == 1600  # 10% of 16000

    def test_budget_allocation_small_tokens(self, mock_memory_store):
        """Verify budget allocation with a small token budget."""
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=100,
        )
        budgets = builder._calculate_budgets()
        assert budgets["system"] == 10  # 10% of 100
        assert budgets["project"] == 30  # 30% of 100
        assert budgets["memory"] == 30  # 30% of 100
        assert budgets["session"] == 20  # 20% of 100
        assert budgets["task"] == 10  # 10% of 100

    def test_budget_allocation_total_matches_max(self, builder):
        """Verify all budget values sum to max_context_tokens."""
        budgets = builder._calculate_budgets()
        total = sum(budgets.values())
        assert total == builder._max_context_tokens

    def test_budget_allocation_rounds_down(self, mock_memory_store):
        """Verify budget allocation rounds down (int) for non-divisible values."""
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=3333,
        )
        budgets = builder._calculate_budgets()
        # 10% of 3333 = 333.3 → 333
        assert budgets["system"] == 333
        assert budgets["project"] == 999
        assert budgets["memory"] == 999
        assert budgets["session"] == 666
        assert budgets["task"] == 333

    def test_system_budget_pct(self):
        """Verify SYSTEM_PROMPT_BUDGET_PCT is 10%."""
        assert ContextBuilder.SYSTEM_PROMPT_BUDGET_PCT == 0.10

    def test_project_budget_pct(self):
        """Verify PROJECT_CONTEXT_BUDGET_PCT is 30%."""
        assert ContextBuilder.PROJECT_CONTEXT_BUDGET_PCT == 0.30

    def test_memory_budget_pct(self):
        """Verify MEMORY_CONTEXT_BUDGET_PCT is 30%."""
        assert ContextBuilder.MEMORY_CONTEXT_BUDGET_PCT == 0.30

    def test_session_budget_pct(self):
        """Verify SESSION_CONTEXT_BUDGET_PCT is 20%."""
        assert ContextBuilder.SESSION_CONTEXT_BUDGET_PCT == 0.20

    def test_task_budget_pct(self):
        """Verify TASK_CONTEXT_BUDGET_PCT is 10%."""
        assert ContextBuilder.TASK_CONTEXT_BUDGET_PCT == 0.10

    def test_budget_percentages_sum_to_one(self):
        """Verify all budget percentages sum to 1.0 (100%)."""
        total_pct = (
            ContextBuilder.SYSTEM_PROMPT_BUDGET_PCT
            + ContextBuilder.PROJECT_CONTEXT_BUDGET_PCT
            + ContextBuilder.MEMORY_CONTEXT_BUDGET_PCT
            + ContextBuilder.SESSION_CONTEXT_BUDGET_PCT
            + ContextBuilder.TASK_CONTEXT_BUDGET_PCT
        )
        assert abs(total_pct - 1.0) < 1e-9


# ============================================================================
# System Section Tests
# ============================================================================


class TestBuildSystemSection:
    """Tests for ContextBuilder._build_system_section()."""

    def test_build_system_section_contains_role(self, builder):
        """Verify system section includes the agent role."""
        section = builder._build_system_section("backend")
        assert "backend" in section
        assert "Agent Role" in section

    def test_build_system_section_format(self, builder):
        """Verify system section follows expected format."""
        section = builder._build_system_section("frontend")
        assert "## Agent Role" in section
        assert "frontend" in section
        assert "context" in section.lower()

    def test_build_system_section_different_roles(self, builder):
        """Verify system section changes based on agent role."""
        backend_section = builder._build_system_section("backend")
        frontend_section = builder._build_system_section("frontend")
        orchestrator_section = builder._build_system_section("orchestrator")

        assert "backend" in backend_section
        assert "frontend" in frontend_section
        assert "orchestrator" in orchestrator_section


# ============================================================================
# Token Estimation Tests
# ============================================================================


class TestEstimateTokens:
    """Tests for ContextBuilder._estimate_tokens()."""

    def test_estimate_tokens_basic(self, builder):
        """Verify _estimate_tokens returns reasonable estimates."""
        text = "Hello world this is a test"
        tokens = builder._estimate_tokens(text)
        expected = int(len(text.split()) * 1.3)
        assert tokens == expected

    def test_estimate_tokens_empty_string(self, builder):
        """Verify _estimate_tokens returns 0 for empty string."""
        assert builder._estimate_tokens("") == 0

    def test_estimate_tokens_single_word(self, builder):
        """Verify _estimate_tokens handles single word."""
        tokens = builder._estimate_tokens("hello")
        assert tokens == int(1 * 1.3)

    def test_estimate_tokens_longer_text(self, builder):
        """Verify _estimate_tokens scales with text length."""
        short_text = "short"
        long_text = "this is a much longer piece of text with many more words"
        short_tokens = builder._estimate_tokens(short_text)
        long_tokens = builder._estimate_tokens(long_text)
        assert long_tokens > short_tokens


# ============================================================================
# Truncate to Tokens Tests
# ============================================================================


class TestTruncateToTokens:
    """Tests for ContextBuilder._truncate_to_tokens()."""

    def test_truncate_under_limit(self, builder):
        """Verify text under the limit is not truncated."""
        text = "This is a short text."
        result = builder._truncate_to_tokens(text, max_tokens=1000)
        assert result == text

    def test_truncate_over_limit(self, builder):
        """Verify text over the limit is truncated with ellipsis."""
        # Create text that will exceed the token limit
        long_text = " ".join(["word"] * 500)
        result = builder._truncate_to_tokens(long_text, max_tokens=50)
        assert result != long_text
        assert result.endswith("...")
        assert len(result) < len(long_text)

    def test_truncate_exact_limit(self, builder):
        """Verify text at exactly the limit is not truncated."""
        # Create text that fits within the limit
        text = "Short text"
        result = builder._truncate_to_tokens(text, max_tokens=100)
        assert result == text

    def test_truncate_very_small_limit(self, builder):
        """Verify truncation with a very small token budget."""
        text = "This is a test"
        result = builder._truncate_to_tokens(text, max_tokens=1)
        # Should return something, even if very short
        assert isinstance(result, str)
        assert len(result) > 0

    def test_truncate_preserves_start(self, builder):
        """Verify truncated text preserves the beginning of the original."""
        long_text = "START " + " ".join(["middle"] * 200) + " END"
        result = builder._truncate_to_tokens(long_text, max_tokens=20)
        assert result.startswith("START")


# ============================================================================
# Project Section Tests
# ============================================================================


class TestBuildProjectSection:
    """Tests for ContextBuilder.build_project_section()."""

    @pytest.mark.asyncio
    async def test_build_project_section_no_project_loaded(self, builder):
        """Verify project section returns note when no project is loaded."""
        section = await builder.build_project_section("nonexistent-project", token_budget=1000)
        assert "No project context loaded" in section or "Project Context" in section

    @pytest.mark.asyncio
    async def test_build_project_section_with_loaded_project(self, builder):
        """Verify project section includes project details when project is loaded."""
        project = _make_project_config()
        builder._loaded_projects["test-project"] = project

        section = await builder.build_project_section("test-project", token_budget=2000)
        assert "Project Context" in section
        assert "fastapi" in section.lower() or "FastAPI" in section or "backend" in section.lower()

    @pytest.mark.asyncio
    async def test_build_project_section_contains_stack(self, builder):
        """Verify project section includes technology stack information."""
        project = _make_project_config(
            stack={"backend": "fastapi", "frontend": "react", "database": "postgresql"}
        )
        builder._loaded_projects["test-project"] = project

        section = await builder.build_project_section("test-project", token_budget=2000)
        assert "fastapi" in section.lower()

    @pytest.mark.asyncio
    async def test_build_project_section_contains_conventions(self, builder):
        """Verify project section includes conventions."""
        project = _make_project_config(conventions=["Use type hints", "Follow PEP 8"])
        builder._loaded_projects["test-project"] = project

        section = await builder.build_project_section("test-project", token_budget=2000)
        assert "type hints" in section.lower() or "PEP 8" in section or "Conventions" in section

    @pytest.mark.asyncio
    async def test_build_project_section_contains_decisions(self, builder):
        """Verify project section includes architectural decisions."""
        project = _make_project_config(decisions=["ADR-001: Use FastAPI"])
        builder._loaded_projects["test-project"] = project

        section = await builder.build_project_section("test-project", token_budget=2000)
        assert "Decisions" in section or "ADR" in section

    @pytest.mark.asyncio
    async def test_build_project_section_contains_constraints(self, builder):
        """Verify project section includes project constraints."""
        project = _make_project_config(constraints=["Response time < 200ms"])
        builder._loaded_projects["test-project"] = project

        section = await builder.build_project_section("test-project", token_budget=2000)
        assert "Constraints" in section or "200ms" in section

    @pytest.mark.asyncio
    async def test_build_project_section_truncation(self, builder_small_budget):
        """Verify project section is truncated when exceeding token budget."""
        project = _make_project_config(
            stack={f"tech_{i}": f"framework_{i}" for i in range(50)},
            conventions=[f"Convention {i}" for i in range(50)],
        )
        builder_small_budget._loaded_projects["test-project"] = project

        section = await builder_small_budget.build_project_section("test-project", token_budget=20)
        estimated_tokens = builder_small_budget._estimate_tokens(section)
        # Should be truncated to fit within budget
        # The truncation adds "..." so it may be slightly over
        assert estimated_tokens <= 20 + 5  # small margin for truncation marker


# ============================================================================
# Memory Section Tests
# ============================================================================


class TestBuildMemorySection:
    """Tests for ContextBuilder.build_memory_section()."""

    @pytest.mark.asyncio
    async def test_build_memory_section_with_results(self, builder):
        """Verify memory section includes retrieved context entries."""
        entries = [
            _make_context_entry(
                content="FastAPI is a modern web framework",
                relevance_score=0.9,
                source="docs",
                title="FastAPI Guide",
                token_count=20,
            ),
        ]
        mock_retrieved = _make_retrieved_context(
            query="test query",
            entries=entries,
            total_tokens=20,
        )

        with patch.object(
            builder._retriever, "retrieve_for_agent", new_callable=AsyncMock
        ) as mock_retrieve:
            mock_retrieve.return_value = mock_retrieved

            section = await builder.build_memory_section(
                project_id="test-project",
                query="test query",
                agent_role="backend",
                token_budget=1000,
            )

            assert "Relevant Context from Memory" in section
            assert "FastAPI" in section
            mock_retrieve.assert_called_once_with(
                project_id="test-project",
                query="test query",
                agent_role="backend",
            )

    @pytest.mark.asyncio
    async def test_build_memory_section_empty_results(self, builder):
        """Verify memory section returns empty string when no results."""
        mock_retrieved = _make_retrieved_context(
            query="test query",
            entries=[],
            total_tokens=0,
        )

        with patch.object(
            builder._retriever, "retrieve_for_agent", new_callable=AsyncMock
        ) as mock_retrieve:
            mock_retrieve.return_value = mock_retrieved

            section = await builder.build_memory_section(
                project_id="test-project",
                query="test query",
                agent_role="backend",
                token_budget=1000,
            )

            assert section == ""

    @pytest.mark.asyncio
    async def test_build_memory_section_includes_relevance(self, builder):
        """Verify memory section includes relevance scores."""
        entries = [
            _make_context_entry(
                content="Test content",
                relevance_score=0.92,
                source="docs",
                title="Test Entry",
                token_count=10,
            ),
        ]
        mock_retrieved = _make_retrieved_context(
            query="test",
            entries=entries,
            total_tokens=10,
        )

        with patch.object(
            builder._retriever, "retrieve_for_agent", new_callable=AsyncMock
        ) as mock_retrieve:
            mock_retrieve.return_value = mock_retrieved

            section = await builder.build_memory_section(
                project_id="test-project",
                query="test",
                agent_role="backend",
                token_budget=1000,
            )

            assert "0.92" in section

    @pytest.mark.asyncio
    async def test_build_memory_section_includes_source(self, builder):
        """Verify memory section includes source attribution."""
        entries = [
            _make_context_entry(
                content="Source content",
                relevance_score=0.8,
                source="architecture.md",
                title="Architecture Overview",
                token_count=10,
            ),
        ]
        mock_retrieved = _make_retrieved_context(
            query="test",
            entries=entries,
            total_tokens=10,
        )

        with patch.object(
            builder._retriever, "retrieve_for_agent", new_callable=AsyncMock
        ) as mock_retrieve:
            mock_retrieve.return_value = mock_retrieved

            section = await builder.build_memory_section(
                project_id="test-project",
                query="test",
                agent_role="backend",
                token_budget=1000,
            )

            assert "architecture.md" in section

    @pytest.mark.asyncio
    async def test_build_memory_section_truncation(self, builder_small_budget):
        """Verify memory section is truncated when exceeding token budget."""
        long_content = " ".join(["word"] * 500)
        entries = [
            _make_context_entry(
                content=long_content,
                relevance_score=0.9,
                source="memory",
                title="Long Entry",
                token_count=650,
            ),
        ]
        mock_retrieved = _make_retrieved_context(
            query="test",
            entries=entries,
            total_tokens=650,
        )

        with patch.object(
            builder_small_budget._retriever, "retrieve_for_agent", new_callable=AsyncMock
        ) as mock_retrieve:
            mock_retrieve.return_value = mock_retrieved

            section = await builder_small_budget.build_memory_section(
                project_id="test-project",
                query="test",
                agent_role="backend",
                token_budget=30,
            )

            estimated_tokens = builder_small_budget._estimate_tokens(section)
            assert estimated_tokens <= 35  # small margin for truncation

    @pytest.mark.asyncio
    async def test_build_memory_section_handles_error(self, builder):
        """Verify memory section handles retriever errors gracefully."""
        with patch.object(
            builder._retriever,
            "retrieve_for_agent",
            new_callable=AsyncMock,
            side_effect=Exception("Retriever error"),
        ):
            section = await builder.build_memory_section(
                project_id="test-project",
                query="test",
                agent_role="backend",
                token_budget=1000,
            )

            assert "Error" in section or section == ""


# ============================================================================
# Session Section Tests
# ============================================================================


class TestBuildSessionSection:
    """Tests for ContextBuilder.build_session_section()."""

    @pytest.mark.asyncio
    async def test_build_session_section_no_session_id(self, builder):
        """Verify session section returns empty string when no session_id."""
        section = await builder.build_session_section(
            project_id="test-project",
            session_id=None,
            token_budget=1000,
        )
        assert section == ""

    @pytest.mark.asyncio
    async def test_build_session_section_with_session(self, builder):
        """Verify session section includes conversation history."""
        # Create a session and add messages
        session_id = await builder._session_manager.create_session(project_id="test-project")
        await builder._session_manager.add_message(session_id, "user", "Hello, I need help")
        await builder._session_manager.add_message(session_id, "assistant", "Sure, how can I help?")

        section = await builder.build_session_section(
            project_id="test-project",
            session_id=session_id,
            token_budget=2000,
        )

        assert "Conversation History" in section
        assert "user" in section.lower()
        assert "Hello" in section

    @pytest.mark.asyncio
    async def test_build_session_section_invalid_session(self, builder):
        """Verify session section handles invalid session_id gracefully."""
        section = await builder.build_session_section(
            project_id="test-project",
            session_id="nonexistent-session",
            token_budget=1000,
        )
        # Should not crash; may return empty or error string
        assert isinstance(section, str)

    @pytest.mark.asyncio
    async def test_build_session_section_truncation(self, builder_small_budget):
        """Verify session section is truncated when exceeding token budget."""
        session_id = await builder_small_budget._session_manager.create_session(
            project_id="test-project"
        )
        # Add a lot of messages
        for i in range(20):
            await builder_small_budget._session_manager.add_message(
                session_id,
                "user",
                f"This is message number {i} with some extra content to make it longer",
            )

        section = await builder_small_budget.build_session_section(
            project_id="test-project",
            session_id=session_id,
            token_budget=30,
        )

        estimated_tokens = builder_small_budget._estimate_tokens(section)
        # Should be truncated
        assert estimated_tokens <= 35  # small margin


# ============================================================================
# Task Section Tests
# ============================================================================


class TestBuildTaskSection:
    """Tests for ContextBuilder.build_task_section()."""

    @pytest.mark.asyncio
    async def test_build_task_section_basic(self, builder):
        """Verify task section includes the task description."""
        section = await builder.build_task_section(
            task_description="Implement user authentication",
            token_budget=1000,
        )
        assert "Current Task" in section
        assert "Implement user authentication" in section

    @pytest.mark.asyncio
    async def test_build_task_section_long_description(self, builder):
        """Verify task section handles a long description."""
        long_task = "Implement a complete authentication system with JWT tokens, " * 10
        section = await builder.build_task_section(
            task_description=long_task,
            token_budget=5000,
        )
        assert "Current Task" in section
        assert "authentication" in section

    @pytest.mark.asyncio
    async def test_build_task_section_truncation(self, builder_small_budget):
        """Verify task section is truncated when exceeding token budget."""
        long_task = " ".join(["implement"] * 500)
        section = await builder_small_budget.build_task_section(
            task_description=long_task,
            token_budget=20,
        )
        estimated_tokens = builder_small_budget._estimate_tokens(section)
        assert estimated_tokens <= 25  # small margin

    @pytest.mark.asyncio
    async def test_build_task_section_format(self, builder):
        """Verify task section follows expected format."""
        section = await builder.build_task_section(
            task_description="Fix the login bug",
            token_budget=1000,
        )
        assert section.startswith("## Current Task")


# ============================================================================
# Build Context Integration Tests
# ============================================================================


class TestBuildContext:
    """Integration tests for ContextBuilder.build_context()."""

    @pytest.mark.asyncio
    async def test_build_context_basic(self, builder):
        """Verify build_context returns a non-empty string."""
        # Pre-load a project
        project = _make_project_config()
        builder._loaded_projects["test-project"] = project

        result = await builder.build_context(
            project_id="test-project",
            query="implement authentication",
            agent_role="backend",
        )

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_build_context_contains_system_section(self, builder):
        """Verify build_context includes the system section."""
        project = _make_project_config()
        builder._loaded_projects["test-project"] = project

        result = await builder.build_context(
            project_id="test-project",
            query="test query",
            agent_role="backend",
        )

        assert "Agent Role" in result
        assert "backend" in result

    @pytest.mark.asyncio
    async def test_build_context_contains_project_section(self, builder):
        """Verify build_context includes the project section."""
        project = _make_project_config(
            stack={"backend": "fastapi"},
            conventions=["Use type hints"],
        )
        builder._loaded_projects["test-project"] = project

        result = await builder.build_context(
            project_id="test-project",
            query="test query",
            agent_role="backend",
        )

        assert "Project Context" in result

    @pytest.mark.asyncio
    async def test_build_context_with_task(self, builder):
        """Verify build_context includes the task section when provided."""
        project = _make_project_config()
        builder._loaded_projects["test-project"] = project

        result = await builder.build_context(
            project_id="test-project",
            query="test query",
            agent_role="backend",
            task_description="Implement user login endpoint",
        )

        assert "Current Task" in result
        assert "Implement user login endpoint" in result

    @pytest.mark.asyncio
    async def test_build_context_without_task(self, builder):
        """Verify build_context omits task section when no task_description."""
        project = _make_project_config()
        builder._loaded_projects["test-project"] = project

        result = await builder.build_context(
            project_id="test-project",
            query="test query",
            agent_role="backend",
        )

        assert "Current Task" not in result

    @pytest.mark.asyncio
    async def test_build_context_with_session(self, builder):
        """Verify build_context includes session section when session_id provided."""
        project = _make_project_config()
        builder._loaded_projects["test-project"] = project

        # Create a session with messages
        session_id = await builder._session_manager.create_session(project_id="test-project")
        await builder._session_manager.add_message(session_id, "user", "Hello")

        result = await builder.build_context(
            project_id="test-project",
            query="test query",
            agent_role="backend",
            session_id=session_id,
        )

        assert "Conversation History" in result or "user" in result.lower()

    @pytest.mark.asyncio
    async def test_build_context_handles_project_load_error(self, builder):
        """Verify build_context handles project loading errors gracefully."""
        # No project loaded, and no way to load one from memory
        result = await builder.build_context(
            project_id="nonexistent-project",
            query="test query",
            agent_role="backend",
        )

        # Should still return a prompt (with error notes)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_build_context_all_sections_separated(self, builder):
        """Verify build_context assembles sections with separators."""
        project = _make_project_config()
        builder._loaded_projects["test-project"] = project

        result = await builder.build_context(
            project_id="test-project",
            query="test query",
            agent_role="orchestrator",
            task_description="Complete the sprint goal",
        )

        # Should have section separators
        assert "---" in result

    @pytest.mark.asyncio
    async def test_build_context_memory_section_with_results(self, builder):
        """Verify build_context includes memory section with mock results."""
        project = _make_project_config()
        builder._loaded_projects["test-project"] = project

        entries = [
            _make_context_entry(
                content="Use repository pattern for data access",
                relevance_score=0.9,
                source="patterns.md",
                title="Repository Pattern",
                token_count=20,
            ),
        ]
        mock_retrieved = _make_retrieved_context(
            query="data access pattern",
            entries=entries,
            total_tokens=20,
        )

        with patch.object(
            builder._retriever, "retrieve_for_agent", new_callable=AsyncMock
        ) as mock_retrieve:
            mock_retrieve.return_value = mock_retrieved

            result = await builder.build_context(
                project_id="test-project",
                query="data access pattern",
                agent_role="backend",
            )

            assert "Relevant Context from Memory" in result or "repository" in result.lower()


# ============================================================================
# Project Loading Tests
# ============================================================================


class TestLoadProject:
    """Tests for ContextBuilder.load_project()."""

    @pytest.mark.asyncio
    async def test_load_project_returns_config(self, builder, sample_context_path):
        """Verify load_project() returns a ProjectConfig."""
        project_root = sample_context_path.parent
        config = await builder.load_project(str(project_root))

        assert isinstance(config, ProjectConfig)
        assert config.name == project_root.name

    @pytest.mark.asyncio
    async def test_load_project_caches_in_builder(self, builder, sample_context_path):
        """Verify load_project() caches the config in _loaded_projects."""
        project_root = sample_context_path.parent
        config = await builder.load_project(str(project_root))

        assert config.project_id in builder._loaded_projects
        assert builder._loaded_projects[config.project_id] is config

    @pytest.mark.asyncio
    async def test_load_project_sets_project_loader(self, builder, sample_context_path):
        """Verify load_project() creates a ProjectLoader."""
        from palace.context.loader import ProjectLoader

        project_root = sample_context_path.parent
        await builder.load_project(str(project_root))

        assert builder._project_loader is not None
        assert isinstance(builder._project_loader, ProjectLoader)

    @pytest.mark.asyncio
    async def test_load_project_populates_stack(self, builder, sample_context_path):
        """Verify load_project() parses and populates the stack."""
        project_root = sample_context_path.parent
        config = await builder.load_project(str(project_root))

        assert isinstance(config.stack, dict)
        assert len(config.stack) > 0

    @pytest.mark.asyncio
    async def test_load_project_populates_conventions(self, builder, sample_context_path):
        """Verify load_project() parses and populates conventions."""
        project_root = sample_context_path.parent
        config = await builder.load_project(str(project_root))

        assert isinstance(config.conventions, list)

    @pytest.mark.asyncio
    async def test_load_project_populates_decisions(self, builder, sample_context_path):
        """Verify load_project() parses and populates decisions."""
        project_root = sample_context_path.parent
        config = await builder.load_project(str(project_root))

        assert isinstance(config.decisions, list)

    @pytest.mark.asyncio
    async def test_load_project_populates_constraints(self, builder, sample_context_path):
        """Verify load_project() parses and populates constraints."""
        project_root = sample_context_path.parent
        config = await builder.load_project(str(project_root))

        assert isinstance(config.constraints, list)


# ============================================================================
# Load or Get Project Tests
# ============================================================================


class TestLoadOrGetProject:
    """Tests for ContextBuilder._load_or_get_project()."""

    @pytest.mark.asyncio
    async def test_load_or_get_from_cache(self, builder):
        """Verify _load_or_get_project returns cached project."""
        project = _make_project_config(project_id="cached-project")
        builder._loaded_projects["cached-project"] = project

        result = await builder._load_or_get_project("cached-project")
        assert result is project

    @pytest.mark.asyncio
    async def test_load_or_get_not_found(self, builder):
        """Verify _load_or_get_project returns None when project not found."""
        # No project in cache and memory store returns empty results
        result = await builder._load_or_get_project("nonexistent-project")
        assert result is None

    @pytest.mark.asyncio
    async def test_load_or_get_from_memory(self, builder):
        """Verify _load_or_get_project attempts to load from memory store."""
        # Set up mock memory store to return project-related entries
        mock_entries = [
            _make_context_entry(
                content="FastAPI for backend",
                context_type=ContextType.STACK,
                source="stack.md",
                title="backend",
                relevance_score=0.9,
                token_count=10,
            ),
        ]
        mock_retrieved = _make_retrieved_context(
            query="project configuration",
            entries=mock_entries,
            total_tokens=10,
        )

        with patch.object(builder._retriever, "retrieve", new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = mock_retrieved

            result = await builder._load_or_get_project("from-memory-project")
            # Should have attempted to load from memory
            assert mock_retrieve.called


# ============================================================================
# Prompt Assembly Tests
# ============================================================================


class TestAssemblePrompt:
    """Tests for ContextBuilder._assemble_prompt()."""

    def test_assemble_prompt_all_sections(self, builder):
        """Verify _assemble_prompt assembles all sections in order."""
        sections = {
            "system": "## Agent Role\n\nYou are a backend agent.",
            "project": "## Project Context\n\nFastAPI project.",
            "memory": "## Relevant Context\n\nSome memory.",
            "session": "## Conversation History\n\n[user]: Hello",
            "task": "## Current Task\n\nFix the bug.",
        }
        result = builder._assemble_prompt(sections)

        # Should contain all sections
        assert "Agent Role" in result
        assert "Project Context" in result
        assert "Relevant Context" in result
        assert "Conversation History" in result
        assert "Current Task" in result
        # Should be separated by ---
        assert "---" in result

    def test_assemble_prompt_skips_empty_sections(self, builder):
        """Verify _assemble_prompt skips empty sections."""
        sections = {
            "system": "## Agent Role\n\nYou are an agent.",
            "project": "## Project Context\n\nProject info.",
            "memory": "",
            "session": "",
            "task": "## Current Task\n\nDo something.",
        }
        result = builder._assemble_prompt(sections)

        assert "Agent Role" in result
        assert "Project Context" in result
        assert "Current Task" in result

    def test_assemble_prompt_skips_whitespace_sections(self, builder):
        """Verify _assemble_prompt skips sections that are only whitespace."""
        sections = {
            "system": "## Agent Role\n\nBackend agent.",
            "project": "   ",
            "memory": "",
            "session": "\n\n",
            "task": "## Current Task\n\nFix bug.",
        }
        result = builder._assemble_prompt(sections)

        assert "Agent Role" in result
        assert "Current Task" in result

    def test_assemble_prompt_order(self, builder):
        """Verify _assemble_prompt maintains section order: system, project, memory, session, task."""
        sections = {
            "system": "SECTION_SYSTEM",
            "project": "SECTION_PROJECT",
            "memory": "SECTION_MEMORY",
            "session": "SECTION_SESSION",
            "task": "SECTION_TASK",
        }
        result = builder._assemble_prompt(sections)

        system_pos = result.find("SECTION_SYSTEM")
        project_pos = result.find("SECTION_PROJECT")
        memory_pos = result.find("SECTION_MEMORY")
        session_pos = result.find("SECTION_SESSION")
        task_pos = result.find("SECTION_TASK")

        assert system_pos < project_pos
        assert project_pos < memory_pos
        assert memory_pos < session_pos
        assert session_pos < task_pos

    def test_assemble_prompt_all_empty(self, builder):
        """Verify _assemble_prompt returns empty string when all sections are empty."""
        sections = {
            "system": "",
            "project": "",
            "memory": "",
            "session": "",
            "task": "",
        }
        result = builder._assemble_prompt(sections)
        assert result == ""


# ============================================================================
# Full Integration Tests
# ============================================================================


class TestContextBuilderIntegration:
    """Integration tests for the full ContextBuilder pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_all_sections(self, builder):
        """Verify the full context building pipeline with all sections."""
        # Pre-load a project
        project = _make_project_config(
            project_id="integration-project",
            stack={"backend": "fastapi", "frontend": "react"},
            conventions=["Use type hints"],
            decisions=["ADR-001: Use FastAPI"],
            constraints=["Response time < 200ms"],
        )
        builder._loaded_projects["integration-project"] = project

        # Create a session
        session_id = await builder._session_manager.create_session(project_id="integration-project")
        await builder._session_manager.add_message(session_id, "user", "I need to build an API")

        # Mock memory retrieval
        entries = [
            _make_context_entry(
                content="FastAPI provides automatic OpenAPI documentation",
                relevance_score=0.85,
                source="docs",
                title="FastAPI Features",
                token_count=15,
            ),
        ]
        mock_retrieved = _make_retrieved_context(
            query="build API",
            entries=entries,
            total_tokens=15,
        )

        with patch.object(
            builder._retriever, "retrieve_for_agent", new_callable=AsyncMock
        ) as mock_retrieve:
            mock_retrieve.return_value = mock_retrieved

            result = await builder.build_context(
                project_id="integration-project",
                query="build API",
                agent_role="backend",
                task_description="Implement REST API endpoints",
                session_id=session_id,
            )

        # Verify all sections are present
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Agent Role" in result
        assert "backend" in result
        assert "Project Context" in result
        assert "Current Task" in result
        assert "Implement REST API endpoints" in result

    @pytest.mark.asyncio
    async def test_pipeline_with_truncation(self, builder_small_budget):
        """Verify the pipeline handles truncation with a small budget."""
        project = _make_project_config(project_id="small-project")
        builder_small_budget._loaded_projects["small-project"] = project

        result = await builder_small_budget.build_context(
            project_id="small-project",
            query="test",
            agent_role="backend",
        )

        # Should produce a result, even if truncated
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_pipeline_error_resilience(self, builder):
        """Verify the pipeline continues when individual sections fail."""
        # Don't load any project - project section should show error message
        result = await builder.build_context(
            project_id="error-project",
            query="test",
            agent_role="backend",
        )

        # Should still produce a result
        assert isinstance(result, str)
        assert len(result) > 0
        # Should at least have the system section
        assert "Agent Role" in result

    @pytest.mark.asyncio
    async def test_pipeline_with_mock_memory_store(self, mock_memory_store):
        """Verify the pipeline works with the shared mock_memory_store fixture."""
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=4000,
        )

        project = _make_project_config(project_id="mock-project")
        builder._loaded_projects["mock-project"] = project

        result = await builder.build_context(
            project_id="mock-project",
            query="test query",
            agent_role="orchestrator",
        )

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_pipeline_respects_token_budgets(self, mock_memory_store):
        """Verify the overall context respects token budgets."""
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=1000,
        )

        project = _make_project_config(project_id="budget-project")
        builder._loaded_projects["budget-project"] = project

        result = await builder.build_context(
            project_id="budget-project",
            query="test",
            agent_role="backend",
            task_description="Fix the bug",
        )

        estimated_tokens = builder._estimate_tokens(result)
        # Allow some margin for the estimation heuristic
        # The result should be roughly within the max_context_tokens budget
        # (may exceed slightly due to truncation markers and section headers)
        assert estimated_tokens < 1500  # reasonable margin over 1000
