"""
Integration Tests for Palace Framework - Context Pipeline

Tests the full context flow:
  ProjectLoader loads files → ContextBuilder builds context → ContextRetriever retrieves context

Uses tmp_path with fake ai_context/ files and mocks the MemoryStore
for retrieval operations.
"""

# ---------------------------------------------------------------------------
# Bootstrap: prevent broken __init__.py imports from cascading
# ---------------------------------------------------------------------------
import sys
import types
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

_SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src"
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

from palace.context.builder import ContextBuilder
from palace.context.loader import ProjectLoader
from palace.context.retriever import ContextRetriever, RetrievalConfig
from palace.context.types import (
    ContextEntry,
    ContextType,
    ProjectConfig,
    RetrievedContext,
    SessionConfig,
)
from palace.memory.base import (
    MemoryEntry,
    MemoryPriority,
    MemoryStore,
    MemoryType,
    SearchQuery,
    SearchResult,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def ai_context_dir(tmp_path):
    """Create a fake /ai_context/ directory with standard context files."""
    context_dir = tmp_path / "ai_context"
    context_dir.mkdir()

    context_files = {
        "architecture.md": (
            "# Architecture\n\n"
            "## Overview\n"
            "This project follows a clean architecture pattern with separate layers.\n\n"
            "## Layers\n"
            "- Domain Layer: Core business logic and entities\n"
            "- Application Layer: Use cases and orchestration\n"
            "- Infrastructure Layer: External integrations and persistence\n"
            "- Presentation Layer: REST API endpoints\n"
        ),
        "stack.md": (
            "# Technology Stack\n\n"
            "## Backend\n"
            "- Language: Python 3.11+\n"
            "- Framework: FastAPI\n"
            "- ORM: SQLAlchemy 2.0+\n"
            "- Validation: Pydantic v2\n\n"
            "## Frontend\n"
            "- Framework: React 18\n"
            "- Language: TypeScript 5\n\n"
            "## Infrastructure\n"
            "- Containerization: Docker\n"
            "- Orchestration: Kubernetes\n"
            "- Database: PostgreSQL 15\n"
        ),
        "conventions.md": (
            "# Coding Conventions\n\n"
            "## General\n"
            "- Use type hints for all function signatures\n"
            "- Write docstrings for all public modules and functions\n"
            "- Follow PEP 8 style guide with 88-char line length\n\n"
            "## Testing\n"
            "- Use pytest for all tests\n"
            "- Maintain at least 80% code coverage\n"
            "- Write integration tests for API endpoints\n\n"
            "## Naming\n"
            "- Variables: snake_case\n"
            "- Classes: PascalCase\n"
            "- Constants: UPPER_SNAKE_CASE\n"
        ),
        "decisions.md": (
            "# Architecture Decision Records\n\n"
            "## ADR-001: Use FastAPI for REST API\n"
            "- Status: Accepted\n"
            "- Context: Need a modern async Python web framework\n"
            "- Decision: Use FastAPI with Pydantic models\n"
            "- Consequences: Fast development, automatic OpenAPI docs\n\n"
            "## ADR-002: Use SQLAlchemy 2.0+ async\n"
            "- Status: Accepted\n"
            "- Context: Need async database access for non-blocking I/O\n"
            "- Decision: Use SQLAlchemy with async sessions\n"
            "- Consequences: Better performance under concurrent load\n"
        ),
        "constraints.md": (
            "# Project Constraints\n\n"
            "## Performance\n"
            "- API response time < 200ms for 95th percentile\n"
            "- Support at least 100 concurrent users\n\n"
            "## Security\n"
            "- All endpoints must require authentication in production\n"
            "- Use OAuth 2.0 with JWT tokens\n"
            "- Encrypt all sensitive data at rest\n\n"
            "## Compatibility\n"
            "- Python 3.11+ required\n"
            "- PostgreSQL 15+ required\n"
        ),
    }

    for filename, content in context_files.items():
        filepath = context_dir / filename
        filepath.write_text(content, encoding="utf-8")

    return context_dir


@pytest.fixture
def project_path(tmp_path, ai_context_dir):
    """Return the project root path (parent of ai_context_dir)."""
    return tmp_path


@pytest.fixture
def mock_memory_store():
    """Create a mock MemoryStore for context retrieval."""
    store = AsyncMock(spec=MemoryStore)

    # Default: return empty search results
    store.search = AsyncMock(return_value=[])
    store.store = AsyncMock(return_value="test-entry-id")
    store.store_batch = AsyncMock(return_value=["id1", "id2"])
    store.retrieve = AsyncMock(return_value=None)
    store.delete = AsyncMock(return_value=True)
    store.count = AsyncMock(return_value=0)
    store.close = AsyncMock()
    store.initialize = AsyncMock()
    store.store_conversation = AsyncMock(return_value="conv-id")
    store.store_knowledge = AsyncMock(return_value="knowledge-id")
    store.store_procedure = AsyncMock(return_value="procedure-id")
    store.retrieve_context = AsyncMock(return_value=[])

    return store


# ============================================================================
# ProjectLoader Integration Tests
# ============================================================================


class TestProjectLoaderIntegration:
    """Integration tests for ProjectLoader loading context from files."""

    async def test_load_reads_all_context_files(self, project_path):
        """ProjectLoader should load all standard context files."""
        loader = ProjectLoader(project_path)
        config = await loader.load()

        assert config is not None
        assert config.project_id is not None
        assert config.name is not None
        assert config.context_path is not None

    async def test_load_populates_stack_info(self, project_path):
        """ProjectLoader should parse the stack.md and populate technology stack."""
        loader = ProjectLoader(project_path)
        config = await loader.load()

        assert isinstance(config.stack, dict)
        # stack.md lists Language, Framework, ORM etc.
        assert len(config.stack) > 0

    async def test_load_populates_conventions(self, project_path):
        """ProjectLoader should parse conventions.md and populate conventions."""
        loader = ProjectLoader(project_path)
        config = await loader.load()

        assert isinstance(config.conventions, list)
        assert len(config.conventions) > 0

    async def test_load_populates_decisions(self, project_path):
        """ProjectLoader should parse decisions.md and populate ADRs."""
        loader = ProjectLoader(project_path)
        config = await loader.load()

        assert isinstance(config.decisions, list)
        assert len(config.decisions) > 0

    async def test_load_populates_constraints(self, project_path):
        """ProjectLoader should parse constraints.md and populate constraints."""
        loader = ProjectLoader(project_path)
        config = await loader.load()

        assert isinstance(config.constraints, list)
        assert len(config.constraints) > 0

    async def test_load_sets_project_id(self, project_path):
        """ProjectLoader should set a project ID derived from the path."""
        loader = ProjectLoader(project_path)
        config = await loader.load()

        assert config.project_id is not None
        assert len(config.project_id) > 0

    async def test_load_sets_paths(self, project_path):
        """ProjectLoader should set root and context paths."""
        loader = ProjectLoader(project_path)
        config = await loader.load()

        assert config.root_path == project_path
        assert config.context_path == project_path / "ai_context"

    async def test_load_sets_last_loaded(self, project_path):
        """ProjectLoader should set last_loaded timestamp."""
        loader = ProjectLoader(project_path)
        config = await loader.load()

        assert config.last_loaded is not None
        assert isinstance(config.last_loaded, datetime)

    async def test_load_file_architecture(self, project_path):
        """ProjectLoader.load_file should return a ContextEntry for architecture.md."""
        loader = ProjectLoader(project_path)
        await loader.load()

        entry = await loader.load_file("architecture.md")
        assert entry is not None
        assert entry.context_type == ContextType.ARCHITECTURE
        assert "Architecture" in entry.content or "architecture" in entry.content.lower()

    async def test_load_file_stack(self, project_path):
        """ProjectLoader.load_file should return a ContextEntry for stack.md."""
        loader = ProjectLoader(project_path)
        await loader.load()

        entry = await loader.load_file("stack.md")
        assert entry is not None
        assert entry.context_type == ContextType.STACK

    async def test_load_file_conventions(self, project_path):
        """ProjectLoader.load_file should return a ContextEntry for conventions.md."""
        loader = ProjectLoader(project_path)
        await loader.load()

        entry = await loader.load_file("conventions.md")
        assert entry is not None
        assert entry.context_type == ContextType.CONVENTIONS

    async def test_load_file_decisions(self, project_path):
        """ProjectLoader.load_file should return a ContextEntry for decisions.md."""
        loader = ProjectLoader(project_path)
        await loader.load()

        entry = await loader.load_file("decisions.md")
        assert entry is not None
        assert entry.context_type == ContextType.DECISIONS

    async def test_load_file_constraints(self, project_path):
        """ProjectLoader.load_file should return a ContextEntry for constraints.md."""
        loader = ProjectLoader(project_path)
        await loader.load()

        entry = await loader.load_file("constraints.md")
        assert entry is not None
        assert entry.context_type == ContextType.CONSTRAINTS

    async def test_context_path_property(self, project_path):
        """ProjectLoader should expose context_path property."""
        loader = ProjectLoader(project_path)
        assert loader.context_path == project_path / "ai_context"

    async def test_is_loaded_property(self, project_path):
        """ProjectLoader.is_loaded should reflect load state."""
        loader = ProjectLoader(project_path)
        assert loader.is_loaded is False

        await loader.load()
        assert loader.is_loaded is True

    async def test_reload_updates_config(self, project_path):
        """Reloading should refresh the configuration."""
        loader = ProjectLoader(project_path)
        config1 = await loader.load()

        # Modify a file
        stack_file = project_path / "ai_context" / "stack.md"
        stack_file.write_text("# Updated Stack\n\n## New\n- New tech", encoding="utf-8")

        config2 = await loader.reload()
        assert config2 is not None

    async def test_get_file_content(self, project_path):
        """get_file_content should return raw content of a loaded file."""
        loader = ProjectLoader(project_path)
        await loader.load()

        content = await loader.get_file_content("architecture.md")
        assert content is not None
        assert "Architecture" in content or "architecture" in content.lower()

    async def test_get_file_content_nonexistent(self, project_path):
        """get_file_content should return None for a missing file."""
        loader = ProjectLoader(project_path)
        await loader.load()

        content = await loader.get_file_content("nonexistent.md")
        assert content is None

    async def test_cache_stats(self, project_path):
        """Cache stats should be available after loading."""
        loader = ProjectLoader(project_path)
        await loader.load()

        stats = loader.get_cache_stats()
        assert isinstance(stats, dict)

    async def test_invalidate_cache(self, project_path):
        """Invalidating cache should clear loaded data."""
        loader = ProjectLoader(project_path)
        await loader.load()
        assert loader.is_loaded is True

        loader.invalidate_cache()
        assert loader.is_loaded is False

    async def test_loaded_files_populated(self, project_path):
        """loaded_files should contain paths after loading."""
        loader = ProjectLoader(project_path)
        await loader.load()

        files = loader.loaded_files
        assert isinstance(files, list)
        assert len(files) > 0

    async def test_load_with_custom_context_dir_name(self, tmp_path):
        """ProjectLoader should support custom context directory names."""
        custom_dir = tmp_path / "custom_context"
        custom_dir.mkdir()
        (custom_dir / "architecture.md").write_text(
            "# Custom Architecture\n\nCustom content.", encoding="utf-8"
        )

        loader = ProjectLoader(tmp_path, context_dir_name="custom_context")
        config = await loader.load()

        assert config is not None

    async def test_load_empty_context_dir(self, tmp_path):
        """ProjectLoader should handle empty context directories gracefully."""
        empty_dir = tmp_path / "ai_context"
        empty_dir.mkdir()

        loader = ProjectLoader(tmp_path)
        config = await loader.load()

        # Should still return a valid ProjectConfig with empty data
        assert config is not None


# ============================================================================
# ContextBuilder Integration Tests
# ============================================================================


class TestContextBuilderIntegration:
    """Integration tests for ContextBuilder combining context sources."""

    async def test_builder_initialization(self, mock_memory_store):
        """ContextBuilder should initialize with a memory store."""
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=8000,
        )
        assert builder is not None

    async def test_builder_with_custom_retriever_config(self, mock_memory_store):
        """ContextBuilder should accept a custom RetrievalConfig."""
        retrieval_config = RetrievalConfig(
            top_k=10,
            min_relevance_score=0.5,
        )
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            retriever_config=retrieval_config,
        )
        assert builder is not None

    async def test_builder_with_custom_session_config(self, mock_memory_store):
        """ContextBuilder should accept a custom SessionConfig."""
        session_config = SessionConfig(
            max_messages=50,
            context_window_tokens=4000,
        )
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            session_config=session_config,
        )
        assert builder is not None

    async def test_load_project(self, project_path, mock_memory_store):
        """ContextBuilder.load_project should load project from path."""
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=8000,
        )
        project_config = await builder.load_project(project_path)
        assert project_config is not None
        assert project_config.root_path == project_path

    async def test_load_project_caches_result(self, project_path, mock_memory_store):
        """Loading the same project twice should use cache."""
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=8000,
        )
        config1 = await builder.load_project(project_path)
        config2 = await builder.load_project(project_path)
        assert config1.project_id == config2.project_id

    async def test_build_project_section(self, project_path, mock_memory_store):
        """ContextBuilder should build a project section from loaded context."""
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=8000,
        )
        project_config = await builder.load_project(project_path)
        section = await builder.build_project_section(project_config.project_id, 2400)
        assert isinstance(section, str)
        assert len(section) > 0

    async def test_build_memory_section_with_results(self, project_path, mock_memory_store):
        """ContextBuilder should build a memory section from search results."""
        # Set up mock memory results as dicts expected by _convert_to_entries
        mock_memory_store.search.return_value = [
            {
                "content": "Use repository pattern for data access",
                "score": 0.95,
                "metadata": {"title": "Pattern: Repository", "source": "knowledge"},
                "entry_id": "test-entry-1",
            }
        ]

        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=8000,
        )
        section = await builder.build_memory_section(
            "test-project", "data access patterns", "assistant", 2400
        )
        assert isinstance(section, str)
        assert len(section) > 0

    async def test_build_memory_section_empty_results(self, mock_memory_store):
        """ContextBuilder should handle empty memory results gracefully."""
        mock_memory_store.search.return_value = []

        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=8000,
        )
        section = await builder.build_memory_section(
            "test-project", "nonexistent query", "assistant", 2400
        )
        assert isinstance(section, str)

    async def test_build_task_section(self, mock_memory_store):
        """ContextBuilder should build a task section."""
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=8000,
        )
        section = await builder.build_task_section("Create a REST endpoint for users", 800)
        assert isinstance(section, str)
        assert "Create a REST endpoint for users" in section

    async def test_estimate_tokens(self, mock_memory_store):
        """ContextBuilder should estimate tokens for text."""
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=8000,
        )
        # A rough estimation: ~4 chars per token
        text = "Hello world this is a test"
        tokens = builder._estimate_tokens(text)
        assert tokens > 0
        assert tokens < len(text)  # Should be fewer tokens than characters


# ============================================================================
# ContextRetriever Integration Tests
# ============================================================================


class TestContextRetrieverIntegration:
    """Integration tests for ContextRetriever RAG-based retrieval."""

    async def test_retriever_initialization(self, mock_memory_store):
        """ContextRetriever should initialize with a memory store."""
        retriever = ContextRetriever(mock_memory_store)
        assert retriever is not None

    async def test_retriever_with_custom_config(self, mock_memory_store):
        """ContextRetriever should accept a custom RetrievalConfig."""
        config = RetrievalConfig(
            top_k=10,
            min_relevance_score=0.5,
            max_total_tokens=2000,
        )
        retriever = ContextRetriever(mock_memory_store, config)
        assert retriever is not None

    async def test_retrieve_with_memory_results(self, mock_memory_store):
        """ContextRetriever.retrieve should return RetrievedContext with hits."""
        # Return dicts as expected by _convert_to_entries
        mock_memory_store.search.return_value = [
            {
                "content": "Users authenticate via JWT tokens with refresh token rotation",
                "score": 0.92,
                "metadata": {"title": "Authentication Pattern", "source": "knowledge"},
                "entry_id": "test-entry-1",
            }
        ]

        retriever = ContextRetriever(mock_memory_store)
        result = await retriever.retrieve(
            project_id="test-project",
            query="How does authentication work?",
        )

        assert isinstance(result, RetrievedContext)
        assert result.query == "How does authentication work?"
        assert len(result.entries) > 0

    async def test_retrieve_empty_results(self, mock_memory_store):
        """ContextRetriever.retrieve should handle no results gracefully."""
        mock_memory_store.search.return_value = []

        retriever = ContextRetriever(mock_memory_store)
        result = await retriever.retrieve(
            project_id="test-project",
            query="nonexistent information",
        )

        assert isinstance(result, RetrievedContext)
        assert result.query == "nonexistent information"
        assert len(result.entries) == 0

    async def test_retrieve_for_agent(self, mock_memory_store):
        """ContextRetriever.retrieve_for_agent should filter by agent role."""
        # Return dicts as expected by _convert_to_entries
        mock_memory_store.search.return_value = [
            {
                "content": "Backend should follow repository pattern",
                "score": 0.88,
                "metadata": {"source": "knowledge"},
                "entry_id": "test-entry-1",
            }
        ]

        retriever = ContextRetriever(mock_memory_store)
        result = await retriever.retrieve_for_agent(
            project_id="test-project",
            query="backend patterns",
            agent_role="backend",
        )

        assert isinstance(result, RetrievedContext)

    async def test_retrieve_project_context(self, mock_memory_store):
        """ContextRetriever.retrieve_project_context should search project memory."""
        # Return dicts as expected by _convert_to_entries
        mock_memory_store.search.return_value = [
            {
                "content": "Project uses clean architecture",
                "score": 0.95,
                "metadata": {"source": "knowledge"},
                "entry_id": "test-entry-1",
            }
        ]

        retriever = ContextRetriever(mock_memory_store)
        result = await retriever.retrieve_project_context("test-project")

        assert isinstance(result, list)


# ============================================================================
# RetrievalConfig Tests
# ============================================================================


class TestRetrievalConfig:
    """Tests for RetrievalConfig dataclass."""

    def test_default_values(self):
        config = RetrievalConfig()
        assert config.top_k == 5
        assert config.min_relevance_score == 0.3
        assert config.max_total_tokens == 4000
        assert config.include_project_context is True
        assert config.deduplicate is True
        assert config.boost_recent is True
        assert config.recent_boost_factor == 1.2

    def test_custom_values(self):
        config = RetrievalConfig(
            top_k=10,
            min_relevance_score=0.5,
            max_total_tokens=8000,
            include_project_context=False,
            deduplicate=False,
            boost_recent=False,
            recent_boost_factor=1.5,
        )
        assert config.top_k == 10
        assert config.min_relevance_score == 0.5
        assert config.max_total_tokens == 8000
        assert config.include_project_context is False
        assert config.deduplicate is False
        assert config.boost_recent is False
        assert config.recent_boost_factor == 1.5

    def test_default_memory_types(self):
        config = RetrievalConfig()
        assert MemoryType.SEMANTIC in config.memory_types
        assert MemoryType.EPISODIC in config.memory_types
        assert MemoryType.PROCEDURAL in config.memory_types


# ============================================================================
# Full Pipeline Integration Tests
# ============================================================================


class TestFullContextPipeline:
    """End-to-end integration tests for the complete context pipeline."""

    async def test_project_load_to_context_build(self, project_path, mock_memory_store):
        """Test loading a project and building context from it."""
        # Step 1: Load project context
        loader = ProjectLoader(project_path)
        project_config = await loader.load()

        assert project_config is not None
        assert project_config.project_id is not None

        # Step 2: Build context from loaded project
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=8000,
        )
        await builder.load_project(project_path)

        project_section = await builder.build_project_section(project_config.project_id, 2400)
        assert isinstance(project_section, str)
        assert len(project_section) > 0

    async def test_project_load_to_memory_retrieval(self, project_path, mock_memory_store):
        """Test loading a project and retrieving memory context for a query."""
        # Set up memory results
        memory_entry = MemoryEntry(
            content="Use FastAPI for the REST API with Pydantic models",
            memory_type=MemoryType.SEMANTIC,
            project_id="test-project",
            source="knowledge",
            metadata={"title": "ADR-001: FastAPI"},
        )
        search_result = SearchResult(entry=memory_entry, score=0.92)
        mock_memory_store.search.return_value = [search_result]

        # Step 1: Load project
        loader = ProjectLoader(project_path)
        project_config = await loader.load()

        # Step 2: Retrieve context via Retriever
        retriever = ContextRetriever(mock_memory_store)
        result = await retriever.retrieve(
            project_id="test-project",
            query="What framework should we use?",
        )

        assert isinstance(result, RetrievedContext)
        assert result.query == "What framework should we use?"

    async def test_full_pipeline_with_all_sources(self, project_path, mock_memory_store):
        """Test full pipeline: load project → build context → retrieve memory."""
        # Set up mock memory results as dicts expected by _convert_to_entries
        mock_memory_store.search.return_value = [
            {
                "content": "Authentication uses JWT with refresh tokens",
                "score": 0.95,
                "metadata": {"title": "Auth Pattern", "source": "knowledge"},
                "entry_id": "test-entry-1",
            },
            {
                "content": "Previously discussed API design patterns",
                "score": 0.80,
                "metadata": {"source": "user"},
                "entry_id": "test-entry-2",
            },
        ]

        # Step 1: Load project context from files
        loader = ProjectLoader(project_path)
        project_config = await loader.load()
        assert project_config is not None

        # Step 2: Build project section
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=8000,
        )
        await builder.load_project(project_path)

        project_section = await builder.build_project_section(project_config.project_id, 2400)
        assert len(project_section) > 0

        # Step 3: Retrieve memory context
        memory_section = await builder.build_memory_section(
            "test-project", "authentication patterns", "assistant", 2400
        )
        assert isinstance(memory_section, str)

        # Step 4: Build task section
        task_section = await builder.build_task_section(
            "Implement user authentication endpoint", 800
        )
        assert "Implement user authentication endpoint" in task_section

    async def test_pipeline_handles_empty_memory(self, project_path, mock_memory_store):
        """Pipeline should work correctly when memory returns no results."""
        mock_memory_store.search.return_value = []

        # Load project
        loader = ProjectLoader(project_path)
        project_config = await loader.load()

        # Build context
        builder = ContextBuilder(
            memory_store=mock_memory_store,
            max_context_tokens=8000,
        )
        await builder.load_project(project_path)

        project_section = await builder.build_project_section(project_config.project_id, 2400)
        assert len(project_section) > 0

        # Memory section should handle empty results
        memory_section = await builder.build_memory_section(
            "test-project", "nonexistent topic", "assistant", 2400
        )
        assert isinstance(memory_section, str)

    async def test_pipeline_context_entries_have_correct_types(self, project_path):
        """All loaded ContextEntry objects should have correct ContextType."""
        loader = ProjectLoader(project_path)
        await loader.load()

        # Check each standard file has the correct type
        architecture = await loader.load_file("architecture.md")
        if architecture:
            assert architecture.context_type == ContextType.ARCHITECTURE

        stack = await loader.load_file("stack.md")
        if stack:
            assert stack.context_type == ContextType.STACK

        conventions = await loader.load_file("conventions.md")
        if conventions:
            assert conventions.context_type == ContextType.CONVENTIONS

        decisions = await loader.load_file("decisions.md")
        if decisions:
            assert decisions.context_type == ContextType.DECISIONS

        constraints = await loader.load_file("constraints.md")
        if constraints:
            assert constraints.context_type == ContextType.CONSTRAINTS

    async def test_pipeline_project_config_has_all_fields(self, project_path):
        """ProjectConfig should have all expected fields populated."""
        loader = ProjectLoader(project_path)
        config = await loader.load()

        # Check that config has populated fields
        assert config.project_id is not None
        assert config.name is not None
        assert config.root_path is not None
        assert config.context_path is not None
        assert config.last_loaded is not None
        # Stack should have entries parsed from stack.md
        assert isinstance(config.stack, dict)
        # Conventions, decisions, constraints should be lists
        assert isinstance(config.conventions, list)
        assert isinstance(config.decisions, list)
        assert isinstance(config.constraints, list)

    async def test_pipeline_retriever_deduplication(self, mock_memory_store):
        """Retriever should be able to deduplicate results."""
        # Return dicts as expected by _convert_to_entries (same content, different scores)
        mock_memory_store.search.return_value = [
            {
                "content": "Use repository pattern",
                "score": 0.95,
                "metadata": {"source": "knowledge"},
                "entry_id": "id-1",
            },
            {
                "content": "Use repository pattern",  # Same content
                "score": 0.80,
                "metadata": {"source": "knowledge"},
                "entry_id": "id-2",
            },
        ]

        retriever = ContextRetriever(
            mock_memory_store,
            RetrievalConfig(deduplicate=True),
        )
        result = await retriever.retrieve(
            project_id="test-project",
            query="repository pattern",
        )

        assert isinstance(result, RetrievedContext)

    async def test_pipeline_multiple_file_types(self, tmp_path):
        """Pipeline should handle projects with varying numbers of context files."""
        # Create project with only some files
        context_dir = tmp_path / "ai_context"
        context_dir.mkdir()
        (context_dir / "architecture.md").write_text(
            "# Simple Architecture\n\nMinimal content.", encoding="utf-8"
        )
        (context_dir / "stack.md").write_text("# Stack\n\n- Python\n- FastAPI", encoding="utf-8")
        # No conventions, decisions, or constraints

        loader = ProjectLoader(tmp_path)
        config = await loader.load()

        assert config is not None
        # Should still have stack info
        assert isinstance(config.stack, dict)

    async def test_pipeline_reload_reflects_file_changes(self, tmp_path):
        """Reloading should pick up file changes."""
        context_dir = tmp_path / "ai_context"
        context_dir.mkdir()
        (context_dir / "architecture.md").write_text(
            "# Original Architecture\n\nOriginal content.", encoding="utf-8"
        )

        loader = ProjectLoader(tmp_path)
        config1 = await loader.load()

        # Modify the file
        (context_dir / "architecture.md").write_text(
            "# Updated Architecture\n\nUpdated content with more details.", encoding="utf-8"
        )

        config2 = await loader.reload()
        assert config2 is not None

    async def test_pipeline_retriever_with_different_memory_types(self, mock_memory_store):
        """Retriever should filter by memory types correctly."""
        # Return dicts as expected by _convert_to_entries
        mock_memory_store.search.return_value = [
            {
                "content": "Architecture pattern: Clean Architecture",
                "score": 0.9,
                "metadata": {"source": "knowledge"},
                "entry_id": "test-entry-1",
            },
            {
                "content": "Deploy script: docker-compose up",
                "score": 0.85,
                "metadata": {"source": "procedure"},
                "entry_id": "test-entry-2",
            },
        ]

        config = RetrievalConfig(
            memory_types=[MemoryType.SEMANTIC, MemoryType.PROCEDURAL],
        )
        retriever = ContextRetriever(mock_memory_store, config)
        result = await retriever.retrieve(
            project_id="test-project",
            query="patterns and procedures",
        )

        assert isinstance(result, RetrievedContext)

    async def test_pipeline_retrieval_config_defaults(self):
        """RetrievalConfig should have sensible defaults."""
        config = RetrievalConfig()
        assert config.top_k > 0
        assert 0 <= config.min_relevance_score <= 1
        assert config.max_total_tokens > 0
        assert len(config.memory_types) > 0

    async def test_pipeline_context_entry_properties(self, project_path):
        """ContextEntry objects should have all expected properties."""
        loader = ProjectLoader(project_path)
        await loader.load()

        entry = await loader.load_file("architecture.md")
        if entry is not None:
            assert entry.entry_id is not None
            assert entry.context_type == ContextType.ARCHITECTURE
            assert entry.source is not None
            assert entry.title is not None
            assert entry.content is not None
            assert len(entry.content) > 0
            assert isinstance(entry.relevance_score, float)
            assert isinstance(entry.token_count, int)
            assert entry.token_count >= 0
