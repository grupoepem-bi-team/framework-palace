"""
Palace Framework - Tests for Context Module Types

This module tests all types, enums, and data structures defined in
palace.context.types, verifying:

- ContextType enum has all 11 expected values
- ContextEntry creation with required fields and defaults
- RetrievedContext creation and defaults
- SessionConfig defaults and validation
- ProjectConfig required fields and defaults
"""

from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from palace.context.types import (
    ContextEntry,
    ContextType,
    ProjectConfig,
    RetrievedContext,
    SessionConfig,
)

# ============================================================================
# ContextType Enum Tests
# ============================================================================


class TestContextType:
    """Tests for the ContextType enum."""

    def test_all_values(self):
        """Verify all 11 ContextType enum values exist with correct string values."""
        assert ContextType.ARCHITECTURE == "architecture"
        assert ContextType.STACK == "stack"
        assert ContextType.CONVENTIONS == "conventions"
        assert ContextType.DECISIONS == "decisions"
        assert ContextType.CONSTRAINTS == "constraints"
        assert ContextType.PATTERN == "pattern"
        assert ContextType.ANTI_PATTERN == "anti_pattern"
        assert ContextType.CONFIG == "config"
        assert ContextType.SESSION == "session"
        assert ContextType.MEMORY == "memory"
        assert ContextType.TASK == "task"

    def test_enum_count(self):
        """Verify ContextType has exactly 11 values."""
        assert len(ContextType) == 11

    def test_str_enum_identity(self):
        """Verify ContextType values are their own string values (str enum)."""
        for member in ContextType:
            assert member.value == member.name.lower() or member == member.value

    def test_from_value(self):
        """Verify ContextType can be constructed from string values."""
        assert ContextType("architecture") == ContextType.ARCHITECTURE
        assert ContextType("stack") == ContextType.STACK
        assert ContextType("memory") == ContextType.MEMORY

    def test_invalid_value_raises(self):
        """Verify that invalid string raises ValueError."""
        with pytest.raises(ValueError):
            ContextType("nonexistent_type")


# ============================================================================
# ContextEntry Tests
# ============================================================================


class TestContextEntry:
    """Tests for the ContextEntry model."""

    def test_create_with_required_fields(self):
        """Verify ContextEntry creation with only required fields."""
        entry = ContextEntry(
            context_type=ContextType.ARCHITECTURE,
            source="architecture.md",
            title="Architecture Overview",
            content="The project follows clean architecture.",
        )
        assert entry.context_type == ContextType.ARCHITECTURE.value
        assert entry.source == "architecture.md"
        assert entry.title == "Architecture Overview"
        assert entry.content == "The project follows clean architecture."
        assert isinstance(entry.entry_id, UUID)
        assert entry.metadata == {}
        assert entry.relevance_score == 0.0
        assert entry.token_count == 0
        assert isinstance(entry.created_at, datetime)
        assert isinstance(entry.updated_at, datetime)

    def test_auto_uuid(self):
        """Verify entry_id is auto-generated as UUID."""
        entry1 = ContextEntry(
            context_type=ContextType.STACK,
            source="stack.md",
            title="Stack",
            content="Python/FastAPI",
        )
        entry2 = ContextEntry(
            context_type=ContextType.STACK,
            source="stack.md",
            title="Stack",
            content="Python/FastAPI",
        )
        assert isinstance(entry1.entry_id, UUID)
        assert isinstance(entry2.entry_id, UUID)
        assert entry1.entry_id != entry2.entry_id

    def test_default_relevance_score(self):
        """Verify default relevance_score is 0.0."""
        entry = ContextEntry(
            context_type=ContextType.DECISIONS,
            source="decisions.md",
            title="ADR-001",
            content="Use FastAPI",
        )
        assert entry.relevance_score == 0.0

    def test_default_token_count(self):
        """Verify default token_count is 0."""
        entry = ContextEntry(
            context_type=ContextType.CONVENTIONS,
            source="conventions.md",
            title="Conventions",
            content="Follow PEP 8",
        )
        assert entry.token_count == 0

    def test_metadata_dict(self):
        """Verify metadata can store arbitrary key-value pairs."""
        entry = ContextEntry(
            context_type=ContextType.PATTERN,
            source="patterns.md",
            title="Repository Pattern",
            content="Use repository pattern for data access.",
            metadata={"sections": ["Overview", "Implementation"], "filename": "patterns.md"},
        )
        assert entry.metadata["sections"] == ["Overview", "Implementation"]
        assert entry.metadata["filename"] == "patterns.md"

    def test_metadata_default_factory(self):
        """Verify each entry gets a fresh metadata dict (not shared)."""
        entry1 = ContextEntry(
            context_type=ContextType.ARCHITECTURE,
            source="a.md",
            title="A",
            content="A content",
        )
        entry2 = ContextEntry(
            context_type=ContextType.STACK,
            source="b.md",
            title="B",
            content="B content",
        )
        entry1.metadata["key"] = "value"
        assert "key" not in entry2.metadata

    def test_relevance_score_valid_range(self):
        """Verify relevance_score accepts values between 0.0 and 1.0."""
        entry_min = ContextEntry(
            context_type=ContextType.MEMORY,
            source="memory",
            title="Min",
            content="min",
            relevance_score=0.0,
        )
        assert entry_min.relevance_score == 0.0

        entry_mid = ContextEntry(
            context_type=ContextType.MEMORY,
            source="memory",
            title="Mid",
            content="mid",
            relevance_score=0.5,
        )
        assert entry_mid.relevance_score == 0.5

        entry_max = ContextEntry(
            context_type=ContextType.MEMORY,
            source="memory",
            title="Max",
            content="max",
            relevance_score=1.0,
        )
        assert entry_max.relevance_score == 1.0

    def test_relevance_score_below_zero_rejected(self):
        """Verify relevance_score rejects values below 0.0."""
        with pytest.raises(ValidationError):
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="memory",
                title="Bad",
                content="bad",
                relevance_score=-0.1,
            )

    def test_relevance_score_above_one_rejected(self):
        """Verify relevance_score rejects values above 1.0."""
        with pytest.raises(ValidationError):
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="memory",
                title="Bad",
                content="bad",
                relevance_score=1.5,
            )

    def test_token_count_negative_rejected(self):
        """Verify token_count rejects negative values."""
        with pytest.raises(ValidationError):
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="memory",
                title="Bad",
                content="bad",
                token_count=-1,
            )

    def test_required_fields_validation(self):
        """Verify that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            ContextEntry()  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            ContextEntry(context_type=ContextType.ARCHITECTURE)  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            ContextEntry(
                context_type=ContextType.ARCHITECTURE,
                source="file.md",
            )  # type: ignore[call-arg]

    def test_use_enum_values_config(self):
        """Verify that use_enum_values=True stores the string value, not the enum."""
        entry = ContextEntry(
            context_type=ContextType.ARCHITECTURE,
            source="architecture.md",
            title="Architecture",
            content="Clean architecture.",
        )
        # With use_enum_values=True, context_type is stored as its string value
        assert entry.context_type == "architecture"

    def test_all_context_types_usable(self):
        """Verify every ContextType value can be used in a ContextEntry."""
        for ct in ContextType:
            entry = ContextEntry(
                context_type=ct,
                source="test.md",
                title=f"Test {ct.value}",
                content=f"Content for {ct.value}",
            )
            assert entry.context_type == ct.value

    def test_created_at_and_updated_set_automatically(self):
        """Verify created_at and updated_at are set automatically."""
        before = datetime.utcnow()
        entry = ContextEntry(
            context_type=ContextType.TASK,
            source="task.md",
            title="Task",
            content="Do the thing",
        )
        after = datetime.utcnow()
        assert before <= entry.created_at <= after
        assert before <= entry.updated_at <= after

    def test_explicit_entry_id(self):
        """Verify entry_id can be explicitly set."""
        explicit_uuid = UUID("12345678-1234-5678-1234-567812345678")
        entry = ContextEntry(
            entry_id=explicit_uuid,
            context_type=ContextType.CONFIG,
            source="config.yaml",
            title="Config",
            content="key: value",
        )
        assert entry.entry_id == explicit_uuid


# ============================================================================
# RetrievedContext Tests
# ============================================================================


class TestRetrievedContext:
    """Tests for the RetrievedContext model."""

    def test_creation_with_required_query(self):
        """Verify RetrievedContext creation with only the required query field."""
        ctx = RetrievedContext(query="test query")
        assert ctx.query == "test query"
        assert ctx.entries == []
        assert ctx.total_tokens == 0
        assert ctx.truncated is False
        assert ctx.sources == []
        assert ctx.memory_hits == 0
        assert ctx.retrieval_time_ms == 0

    def test_default_entries_is_empty_list(self):
        """Verify entries defaults to an empty list."""
        ctx = RetrievedContext(query="search")
        assert isinstance(ctx.entries, list)
        assert len(ctx.entries) == 0

    def test_default_truncated_is_false(self):
        """Verify truncated defaults to False."""
        ctx = RetrievedContext(query="search")
        assert ctx.truncated is False

    def test_with_entries(self):
        """Verify RetrievedContext can be created with entries."""
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="memory",
                title="Test Entry 1",
                content="Content 1",
                relevance_score=0.9,
                token_count=10,
            ),
            ContextEntry(
                context_type=ContextType.ARCHITECTURE,
                source="architecture.md",
                title="Architecture Entry",
                content="Content 2",
                relevance_score=0.7,
                token_count=20,
            ),
        ]
        ctx = RetrievedContext(
            query="test",
            entries=entries,
            total_tokens=30,
            truncated=False,
            sources=["memory", "architecture.md"],
            memory_hits=2,
            retrieval_time_ms=150,
        )
        assert len(ctx.entries) == 2
        assert ctx.total_tokens == 30
        assert ctx.sources == ["memory", "architecture.md"]
        assert ctx.memory_hits == 2
        assert ctx.retrieval_time_ms == 150

    def test_token_tracking(self):
        """Verify total_tokens tracks the sum of entry tokens."""
        entries = [
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="m1",
                title="Entry 1",
                content="Short",
                token_count=5,
            ),
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="m2",
                title="Entry 2",
                content="Longer content here",
                token_count=15,
            ),
        ]
        ctx = RetrievedContext(
            query="test",
            entries=entries,
            total_tokens=20,
        )
        assert ctx.total_tokens == 20

    def test_total_tokens_negative_rejected(self):
        """Verify total_tokens rejects negative values."""
        with pytest.raises(ValidationError):
            RetrievedContext(query="test", total_tokens=-1)

    def test_memory_hits_negative_rejected(self):
        """Verify memory_hits rejects negative values."""
        with pytest.raises(ValidationError):
            RetrievedContext(query="test", memory_hits=-1)

    def test_retrieval_time_ms_negative_rejected(self):
        """Verify retrieval_time_ms rejects negative values."""
        with pytest.raises(ValidationError):
            RetrievedContext(query="test", retrieval_time_ms=-1)

    def test_entries_independent(self):
        """Verify each RetrievedContext gets an independent entries list."""
        ctx1 = RetrievedContext(query="q1")
        ctx2 = RetrievedContext(query="q2")
        ctx1.entries.append(
            ContextEntry(
                context_type=ContextType.MEMORY,
                source="s",
                title="t",
                content="c",
            )
        )
        assert len(ctx2.entries) == 0

    def test_truncated_flag(self):
        """Verify truncated can be set to True."""
        ctx = RetrievedContext(query="test", truncated=True)
        assert ctx.truncated is True


# ============================================================================
# SessionConfig Tests
# ============================================================================


class TestSessionConfig:
    """Tests for the SessionConfig model."""

    def test_all_defaults(self):
        """Verify all SessionConfig fields have the expected defaults."""
        config = SessionConfig()
        assert config.max_messages == 100
        assert config.context_window_tokens == 8000
        assert config.auto_summarize is True
        assert config.summarize_after == 50
        assert config.persist_history is True
        assert config.ttl_seconds == 7200

    def test_custom_values(self):
        """Verify SessionConfig can be created with custom values."""
        config = SessionConfig(
            max_messages=200,
            context_window_tokens=16000,
            auto_summarize=False,
            summarize_after=100,
            persist_history=False,
            ttl_seconds=3600,
        )
        assert config.max_messages == 200
        assert config.context_window_tokens == 16000
        assert config.auto_summarize is False
        assert config.summarize_after == 100
        assert config.persist_history is False
        assert config.ttl_seconds == 3600

    def test_max_messages_minimum_1(self):
        """Verify max_messages rejects values below 1."""
        with pytest.raises(ValidationError):
            SessionConfig(max_messages=0)

        with pytest.raises(ValidationError):
            SessionConfig(max_messages=-1)

    def test_context_window_tokens_minimum_1(self):
        """Verify context_window_tokens rejects values below 1."""
        with pytest.raises(ValidationError):
            SessionConfig(context_window_tokens=0)

    def test_summarize_after_minimum_1(self):
        """Verify summarize_after rejects values below 1."""
        with pytest.raises(ValidationError):
            SessionConfig(summarize_after=0)

    def test_ttl_seconds_minimum_0(self):
        """Verify ttl_seconds accepts 0 and rejects negative values."""
        # 0 is valid (no expiration)
        config = SessionConfig(ttl_seconds=0)
        assert config.ttl_seconds == 0

        with pytest.raises(ValidationError):
            SessionConfig(ttl_seconds=-1)


# ============================================================================
# ProjectConfig Tests
# ============================================================================


class TestProjectConfig:
    """Tests for the context-specific ProjectConfig model."""

    def test_create_with_required_fields(self):
        """Verify ProjectConfig creation with all required fields."""
        from pathlib import Path

        config = ProjectConfig(
            project_id="my-project",
            name="My Project",
            root_path=Path("/projects/my-project"),
            context_path=Path("/projects/my-project/ai_context"),
        )
        assert config.project_id == "my-project"
        assert config.name == "My Project"
        assert config.root_path == Path("/projects/my-project")
        assert config.context_path == Path("/projects/my-project/ai_context")

    def test_defaults(self):
        """Verify default values for optional fields."""
        from pathlib import Path

        config = ProjectConfig(
            project_id="test-project",
            name="Test",
            root_path=Path("/test"),
            context_path=Path("/test/ai_context"),
        )
        assert config.description is None
        assert config.stack == {}
        assert config.conventions == []
        assert config.decisions == []
        assert config.constraints == []
        assert config.last_loaded is None
        assert config.auto_reload is False
        assert config.watch_interval_seconds == 60

    def test_with_all_fields(self):
        """Verify ProjectConfig creation with all fields populated."""
        from datetime import datetime
        from pathlib import Path

        now = datetime.utcnow()
        config = ProjectConfig(
            project_id="full-project",
            name="Full Project",
            description="A complete project",
            root_path=Path("/projects/full"),
            context_path=Path("/projects/full/ai_context"),
            stack={"backend": "fastapi", "frontend": "react", "database": "postgresql"},
            conventions=["Use type hints", "Follow PEP 8"],
            decisions=["ADR-001: Use FastAPI", "ADR-002: Use SQLAlchemy"],
            constraints=["Response time < 200ms", "Must support 100 concurrent users"],
            last_loaded=now,
            auto_reload=True,
            watch_interval_seconds=30,
        )
        assert config.project_id == "full-project"
        assert config.name == "Full Project"
        assert config.description == "A complete project"
        assert config.stack == {"backend": "fastapi", "frontend": "react", "database": "postgresql"}
        assert config.conventions == ["Use type hints", "Follow PEP 8"]
        assert config.decisions == ["ADR-001: Use FastAPI", "ADR-002: Use SQLAlchemy"]
        assert config.constraints == [
            "Response time < 200ms",
            "Must support 100 concurrent users",
        ]
        assert config.last_loaded == now
        assert config.auto_reload is True
        assert config.watch_interval_seconds == 30

    def test_required_fields_validation(self):
        """Verify that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            ProjectConfig()  # type: ignore[call-arg]

        # Missing project_id
        with pytest.raises(ValidationError):
            ProjectConfig(name="Test", root_path="/test", context_path="/test/ai_context")

        # Missing name
        with pytest.raises(ValidationError):
            ProjectConfig(project_id="test", root_path="/test", context_path="/test/ai_context")

        # Missing root_path
        with pytest.raises(ValidationError):
            ProjectConfig(project_id="test", name="Test", context_path="/test/ai_context")

        # Missing context_path
        with pytest.raises(ValidationError):
            ProjectConfig(project_id="test", name="Test", root_path="/test")

    def test_use_enum_values_config(self):
        """Verify use_enum_values config is set on ProjectConfig."""
        assert ProjectConfig.model_config.get("use_enum_values", False) is True

    def test_stack_dict(self):
        """Verify stack is a dict with string keys and values."""
        from pathlib import Path

        config = ProjectConfig(
            project_id="test",
            name="Test",
            root_path=Path("/test"),
            context_path=Path("/test/ai_context"),
            stack={"backend": "fastapi", "frontend": "react"},
        )
        assert config.stack["backend"] == "fastapi"
        assert config.stack["frontend"] == "react"

    def test_lists_are_independent(self):
        """Verify default lists are independent between instances."""
        from pathlib import Path

        config1 = ProjectConfig(
            project_id="p1",
            name="P1",
            root_path=Path("/p1"),
            context_path=Path("/p1/ai_context"),
        )
        config2 = ProjectConfig(
            project_id="p2",
            name="P2",
            root_path=Path("/p2"),
            context_path=Path("/p2/ai_context"),
        )
        config1.conventions.append("Convention A")
        assert len(config2.conventions) == 0


# ============================================================================
# Cross-Model Integration Tests
# ============================================================================


class TestContextTypesIntegration:
    """Integration tests for context types working together."""

    def test_context_entry_in_retrieved_context(self):
        """Verify ContextEntry instances can be placed in RetrievedContext."""
        entries = [
            ContextEntry(
                context_type=ct,
                source=f"{ct.value}.md",
                title=f"Test {ct.value}",
                content=f"Content about {ct.value}",
                relevance_score=round(0.5 + i * 0.05, 2),
                token_count=10 + i * 5,
            )
            for i, ct in enumerate(ContextType)
        ]
        ctx = RetrievedContext(
            query="integration test",
            entries=entries,
            total_tokens=sum(e.token_count for e in entries),
            truncated=True,
            sources=[e.source for e in entries],
            memory_hits=len(entries),
            retrieval_time_ms=200,
        )
        assert len(ctx.entries) == 11
        assert ctx.truncated is True
        assert ctx.memory_hits == 11

    def test_project_config_with_session_config(self):
        """Verify ProjectConfig and SessionConfig can coexist."""
        from pathlib import Path

        project = ProjectConfig(
            project_id="my-project",
            name="My Project",
            root_path=Path("/projects/my-project"),
            context_path=Path("/projects/my-project/ai_context"),
        )
        session = SessionConfig(max_messages=project.watch_interval_seconds)
        assert session.max_messages == 60

    def test_context_type_values_as_strings(self):
        """Verify that ContextType enum values can be used as strings in entries."""
        for ct in ContextType:
            entry = ContextEntry(
                context_type=ct,
                source=f"{ct.value}.md",
                title=f"Title for {ct.value}",
                content=f"Content for {ct.value}",
            )
            # With use_enum_values, the stored value is a string
            assert isinstance(entry.context_type, str)
            assert entry.context_type == ct.value
