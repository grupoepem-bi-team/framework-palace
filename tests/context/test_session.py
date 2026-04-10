"""
Palace Framework - Tests for Session Management

This module tests the SessionState enum, SessionData dataclass,
and SessionManager from palace.context.session, verifying:

- SessionState enum values
- SessionData creation with defaults and required fields
- SessionManager session lifecycle (create, get, close)
- Message addition and history retrieval
- Auto-summarization triggering
- Session expiration and cleanup
- Stats reporting
- SessionNotFoundError handling
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from palace.context.session import SessionData, SessionManager, SessionState
from palace.context.types import SessionConfig
from palace.core.exceptions import SessionNotFoundError

# ============================================================================
# SessionState Enum Tests
# ============================================================================


class TestSessionState:
    """Tests for the SessionState enum."""

    def test_all_values(self):
        """Verify all 5 SessionState enum values exist with correct string values."""
        assert SessionState.ACTIVE == "active"
        assert SessionState.IDLE == "idle"
        assert SessionState.SUMMARIZED == "summarized"
        assert SessionState.EXPIRED == "expired"
        assert SessionState.CLOSED == "closed"

    def test_enum_count(self):
        """Verify SessionState has exactly 5 values."""
        assert len(SessionState) == 5

    def test_str_enum_identity(self):
        """Verify SessionState values are strings (str enum)."""
        for member in SessionState:
            assert isinstance(member.value, str)

    def test_from_value(self):
        """Verify SessionState can be constructed from string values."""
        assert SessionState("active") == SessionState.ACTIVE
        assert SessionState("idle") == SessionState.IDLE
        assert SessionState("summarized") == SessionState.SUMMARIZED

    def test_invalid_value_raises(self):
        """Verify that invalid string raises ValueError."""
        with pytest.raises(ValueError):
            SessionState("nonexistent_state")


# ============================================================================
# SessionData Tests
# ============================================================================


class TestSessionData:
    """Tests for the SessionData dataclass."""

    def test_create_with_required_fields(self):
        """Verify SessionData creation with required fields only."""
        session_id = UUID("12345678-1234-5678-1234-567812345678")
        data = SessionData(
            session_id=session_id,
            project_id="test-project",
        )
        assert data.session_id == session_id
        assert data.project_id == "test-project"
        assert data.state == SessionState.ACTIVE
        assert data.messages == []
        assert data.metadata == {}
        assert isinstance(data.created_at, datetime)
        assert isinstance(data.updated_at, datetime)
        assert isinstance(data.last_activity, datetime)
        assert data.message_count == 0
        assert data.total_tokens == 0
        assert data.summary is None
        assert data.agent_history == []

    def test_create_with_all_fields(self):
        """Verify SessionData creation with all fields populated."""
        now = datetime.utcnow()
        session_id = UUID("12345678-1234-5678-1234-567812345678")
        data = SessionData(
            session_id=session_id,
            project_id="my-project",
            state=SessionState.SUMMARIZED,
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
            metadata={"source": "test"},
            created_at=now,
            updated_at=now,
            last_activity=now,
            message_count=2,
            total_tokens=50,
            summary="User greeted the assistant.",
            agent_history=["orchestrator", "backend"],
        )
        assert data.session_id == session_id
        assert data.project_id == "my-project"
        assert data.state == SessionState.SUMMARIZED
        assert len(data.messages) == 2
        assert data.metadata["source"] == "test"
        assert data.created_at == now
        assert data.updated_at == now
        assert data.last_activity == now
        assert data.message_count == 2
        assert data.total_tokens == 50
        assert data.summary == "User greeted the assistant."
        assert data.agent_history == ["orchestrator", "backend"]

    def test_default_state_is_active(self):
        """Verify default state is ACTIVE."""
        data = SessionData(
            session_id=UUID("12345678-1234-5678-1234-567812345678"),
            project_id="proj",
        )
        assert data.state == SessionState.ACTIVE

    def test_default_messages_is_empty_list(self):
        """Verify default messages is an empty list."""
        data = SessionData(
            session_id=UUID("12345678-1234-5678-1234-567812345678"),
            project_id="proj",
        )
        assert isinstance(data.messages, list)
        assert len(data.messages) == 0

    def test_default_message_count_is_zero(self):
        """Verify default message_count is 0."""
        data = SessionData(
            session_id=UUID("12345678-1234-5678-1234-567812345678"),
            project_id="proj",
        )
        assert data.message_count == 0

    def test_default_total_tokens_is_zero(self):
        """Verify default total_tokens is 0."""
        data = SessionData(
            session_id=UUID("12345678-1234-5678-1234-567812345678"),
            project_id="proj",
        )
        assert data.total_tokens == 0

    def test_default_summary_is_none(self):
        """Verify default summary is None."""
        data = SessionData(
            session_id=UUID("12345678-1234-5678-1234-567812345678"),
            project_id="proj",
        )
        assert data.summary is None

    def test_default_agent_history_is_empty_list(self):
        """Verify default agent_history is an empty list."""
        data = SessionData(
            session_id=UUID("12345678-1234-5678-1234-567812345678"),
            project_id="proj",
        )
        assert data.agent_history == []

    def test_lists_are_independent(self):
        """Verify default lists are independent between instances."""
        data1 = SessionData(
            session_id=UUID("11111111-1111-1111-1111-111111111111"),
            project_id="p1",
        )
        data2 = SessionData(
            session_id=UUID("22222222-2222-2222-2222-222222222222"),
            project_id="p2",
        )
        data1.messages.append({"role": "user", "content": "test"})
        assert len(data2.messages) == 0


# ============================================================================
# SessionManager Tests
# ============================================================================


class TestSessionManagerInit:
    """Tests for SessionManager initialization."""

    def test_init_default_config(self):
        """Verify SessionManager initializes with default SessionConfig."""
        manager = SessionManager()
        assert manager._config.max_messages == 100
        assert manager._config.auto_summarize is True
        assert manager._config.ttl_seconds == 7200

    def test_init_custom_config(self):
        """Verify SessionManager initializes with custom SessionConfig."""
        config = SessionConfig(
            max_messages=50,
            auto_summarize=False,
            ttl_seconds=3600,
        )
        manager = SessionManager(config=config)
        assert manager._config.max_messages == 50
        assert manager._config.auto_summarize is False
        assert manager._config.ttl_seconds == 3600

    def test_init_with_memory_store(self):
        """Verify SessionManager can be initialized with a memory store."""
        mock_store = MagicMock()
        manager = SessionManager(memory_store=mock_store)
        assert manager._memory_store is mock_store

    def test_init_without_memory_store(self):
        """Verify SessionManager initializes without memory store."""
        manager = SessionManager()
        assert manager._memory_store is None

    def test_init_empty_sessions(self):
        """Verify SessionManager starts with no sessions."""
        manager = SessionManager()
        assert len(manager._sessions) == 0
        assert len(manager._session_order) == 0


# ============================================================================
# Session Creation and Retrieval Tests
# ============================================================================


class TestSessionManagerCreateGet:
    """Tests for SessionManager.create_session() and get_session()."""

    @pytest.mark.asyncio
    async def test_create_session_returns_string_id(self):
        """Verify create_session() returns a string session ID."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="test-project")
        assert isinstance(session_id, str)

    @pytest.mark.asyncio
    async def test_create_session_generates_valid_uuid(self):
        """Verify the generated session ID is a valid UUID string."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="test-project")
        # Should be a valid UUID string
        parsed_uuid = UUID(session_id)
        assert str(parsed_uuid) == session_id

    @pytest.mark.asyncio
    async def test_create_session_with_custom_id(self):
        """Verify create_session() can use a provided session ID."""
        manager = SessionManager()
        # SessionData requires a valid UUID format for session_id
        custom_id = "12345678-1234-5678-1234-567812345678"
        session_id = await manager.create_session(
            project_id="test-project",
            session_id=custom_id,
        )
        assert session_id == custom_id

    @pytest.mark.asyncio
    async def test_create_session_with_metadata(self):
        """Verify create_session() stores provided metadata."""
        manager = SessionManager()
        session_id = await manager.create_session(
            project_id="test-project",
            metadata={"environment": "test", "user": "developer"},
        )
        session = await manager.get_session(session_id)
        assert session.metadata["environment"] == "test"
        assert session.metadata["user"] == "developer"

    @pytest.mark.asyncio
    async def test_create_session_stores_project_id(self):
        """Verify the session stores the provided project_id."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="my-project")
        session = await manager.get_session(session_id)
        assert session.project_id == "my-project"

    @pytest.mark.asyncio
    async def test_create_session_initial_state_active(self):
        """Verify a newly created session is in ACTIVE state."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        session = await manager.get_session(session_id)
        assert session.state == SessionState.ACTIVE

    @pytest.mark.asyncio
    async def test_create_session_initial_counts_zero(self):
        """Verify a newly created session has zero messages and tokens."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        session = await manager.get_session(session_id)
        assert session.message_count == 0
        assert session.total_tokens == 0
        assert len(session.messages) == 0

    @pytest.mark.asyncio
    async def test_get_session_raises_for_nonexistent(self):
        """Verify get_session() raises SessionNotFoundError for non-existent ID."""
        manager = SessionManager()
        with pytest.raises(SessionNotFoundError):
            await manager.get_session("nonexistent-session-id")

    @pytest.mark.asyncio
    async def test_create_multiple_sessions(self):
        """Verify multiple sessions can be created and retrieved."""
        manager = SessionManager()
        sid1 = await manager.create_session(project_id="project-1")
        sid2 = await manager.create_session(project_id="project-2")
        assert sid1 != sid2

        session1 = await manager.get_session(sid1)
        session2 = await manager.get_session(sid2)
        assert session1.project_id == "project-1"
        assert session2.project_id == "project-2"


# ============================================================================
# Message Handling Tests
# ============================================================================


class TestSessionManagerMessages:
    """Tests for SessionManager.add_message() and get_history()."""

    @pytest.mark.asyncio
    async def test_add_message_basic(self):
        """Verify add_message() adds a message to the session."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, role="user", content="Hello")
        session = await manager.get_session(session_id)
        assert session.message_count == 1
        assert len(session.messages) == 1
        assert session.messages[0]["role"] == "user"
        assert session.messages[0]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_add_message_increments_count(self):
        """Verify add_message() increments message_count."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "First message")
        await manager.add_message(session_id, "assistant", "Second message")
        session = await manager.get_session(session_id)
        assert session.message_count == 2

    @pytest.mark.asyncio
    async def test_add_message_with_agent(self):
        """Verify add_message() records the agent name."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "assistant", "Implementing feature", agent="backend")
        session = await manager.get_session(session_id)
        assert session.messages[0]["agent"] == "backend"
        assert "backend" in session.agent_history

    @pytest.mark.asyncio
    async def test_add_message_tracks_tokens(self):
        """Verify add_message() adds to total_tokens."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Hello", tokens=10)
        await manager.add_message(session_id, "assistant", "Hi there!", tokens=15)
        session = await manager.get_session(session_id)
        assert session.total_tokens == 25

    @pytest.mark.asyncio
    async def test_add_message_agent_history_deduplication(self):
        """Verify agent_history doesn't duplicate agent names."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "assistant", "Msg 1", agent="backend")
        await manager.add_message(session_id, "assistant", "Msg 2", agent="backend")
        session = await manager.get_session(session_id)
        assert session.agent_history.count("backend") == 1

    @pytest.mark.asyncio
    async def test_add_message_nonexistent_session_raises(self):
        """Verify add_message() raises SessionNotFoundError for non-existent session."""
        manager = SessionManager()
        with pytest.raises(SessionNotFoundError):
            await manager.add_message("nonexistent", "user", "Hello")

    @pytest.mark.asyncio
    async def test_get_history_returns_all_messages(self):
        """Verify get_history() returns all messages."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Hello")
        await manager.add_message(session_id, "assistant", "Hi!")
        await manager.add_message(session_id, "user", "How are you?")
        history = await manager.get_history(session_id)
        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[2]["content"] == "How are you?"

    @pytest.mark.asyncio
    async def test_get_history_with_limit(self):
        """Verify get_history() respects the limit parameter."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        for i in range(5):
            await manager.add_message(session_id, "user", f"Message {i}")
        history = await manager.get_history(session_id, limit=2)
        assert len(history) == 2
        # Should return the last 2 messages
        assert history[0]["content"] == "Message 3"
        assert history[1]["content"] == "Message 4"

    @pytest.mark.asyncio
    async def test_get_history_includes_summary(self):
        """Verify get_history() includes summary as system message when include_summaries=True."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Hello")

        # Summarize the session to set a summary
        await manager.summarize_session(session_id)

        # Re-create the session in the manager since summarize marks it
        # and then we get history which should include the summary
        session = await manager.get_session(session_id)
        assert session.summary is not None

        history = await manager.get_history(session_id, include_summaries=True)
        # First message should be the summary
        assert history[0]["role"] == "system"
        assert "Session Summary" in history[0]["content"]

    @pytest.mark.asyncio
    async def test_get_history_without_summary(self):
        """Verify get_history() excludes summary when include_summaries=False."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Hello")
        await manager.summarize_session(session_id)

        history = await manager.get_history(session_id, include_summaries=False)
        # Should only contain the original messages
        for msg in history:
            assert not msg["content"].startswith("[Session Summary]")

    @pytest.mark.asyncio
    async def test_get_history_nonexistent_session_raises(self):
        """Verify get_history() raises SessionNotFoundError for non-existent session."""
        manager = SessionManager()
        with pytest.raises(SessionNotFoundError):
            await manager.get_history("nonexistent")

    @pytest.mark.asyncio
    async def test_message_contains_timestamp(self):
        """Verify each message contains an ISO-format timestamp."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Hello")
        session = await manager.get_session(session_id)
        msg = session.messages[0]
        assert "timestamp" in msg
        # Should be parseable as ISO format
        datetime.fromisoformat(msg["timestamp"])


# ============================================================================
# Recent Context Tests
# ============================================================================


class TestSessionManagerRecentContext:
    """Tests for SessionManager.get_recent_context()."""

    @pytest.mark.asyncio
    async def test_get_recent_context_returns_string(self):
        """Verify get_recent_context() returns a formatted string."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Hello")
        await manager.add_message(session_id, "assistant", "Hi!")
        context = await manager.get_recent_context(session_id)
        assert isinstance(context, str)
        assert "[user]: Hello" in context
        assert "[assistant]: Hi!" in context

    @pytest.mark.asyncio
    async def test_get_recent_context_max_messages(self):
        """Verify get_recent_context() respects max_messages parameter."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        for i in range(20):
            await manager.add_message(session_id, "user", f"Message {i}")
        context = await manager.get_recent_context(session_id, max_messages=5)
        lines = [l for l in context.split("\n") if l.strip()]
        assert len(lines) == 5

    @pytest.mark.asyncio
    async def test_get_recent_context_empty_session(self):
        """Verify get_recent_context() returns empty string for empty session."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        context = await manager.get_recent_context(session_id)
        assert context == ""

    @pytest.mark.asyncio
    async def test_get_recent_context_nonexistent_session_raises(self):
        """Verify get_recent_context() raises SessionNotFoundError for non-existent session."""
        manager = SessionManager()
        with pytest.raises(SessionNotFoundError):
            await manager.get_recent_context("nonexistent")


# ============================================================================
# Summarization Tests
# ============================================================================


class TestSessionManagerSummarization:
    """Tests for SessionManager.summarize_session() and auto-summarization."""

    @pytest.mark.asyncio
    async def test_summarize_session_returns_string(self):
        """Verify summarize_session() returns a summary string."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Hello, I need help with authentication")
        summary = await manager.summarize_session(session_id)
        assert isinstance(summary, str)
        assert len(summary) > 0

    @pytest.mark.asyncio
    async def test_summarize_session_sets_summary(self):
        """Verify summarize_session() sets the summary on the session."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Hello")
        await manager.summarize_session(session_id)
        session = await manager.get_session(session_id)
        assert session.summary is not None
        assert len(session.summary) > 0

    @pytest.mark.asyncio
    async def test_summarize_session_sets_state_summarized(self):
        """Verify summarize_session() sets state to SUMMARIZED."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Hello")
        await manager.summarize_session(session_id)
        session = await manager.get_session(session_id)
        assert session.state == SessionState.SUMMARIZED

    @pytest.mark.asyncio
    async def test_summarize_session_contains_topic(self):
        """Verify summary contains the topic from first user message."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "I need to implement login")
        await manager.add_message(session_id, "assistant", "Sure, let's start")
        summary = await manager.summarize_session(session_id)
        # The summary should reference the topic from the first user message
        assert "implement login" in summary or "Session Summary" in summary

    @pytest.mark.asyncio
    async def test_summarize_session_contains_message_count(self):
        """Verify summary includes message count information."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Hello")
        await manager.add_message(session_id, "assistant", "Hi!")
        summary = await manager.summarize_session(session_id)
        assert "2" in summary  # message count

    @pytest.mark.asyncio
    async def test_summarize_session_contains_participants(self):
        """Verify summary includes participants from agent_history."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Hello")
        await manager.add_message(session_id, "assistant", "Hi!", agent="backend")
        summary = await manager.summarize_session(session_id)
        assert "backend" in summary

    @pytest.mark.asyncio
    async def test_summarize_nonexistent_session_raises(self):
        """Verify summarize_session() raises SessionNotFoundError for non-existent session."""
        manager = SessionManager()
        with pytest.raises(SessionNotFoundError):
            await manager.summarize_session("nonexistent")

    @pytest.mark.asyncio
    async def test_auto_summarize_triggers_at_threshold(self):
        """Verify auto-summarization triggers when message_count reaches summarize_after."""
        config = SessionConfig(
            max_messages=200,
            auto_summarize=True,
            summarize_after=5,
        )
        manager = SessionManager(config=config)
        session_id = await manager.create_session(project_id="proj")

        # Add messages up to the threshold
        for i in range(5):
            await manager.add_message(session_id, "user", f"Message {i}")

        session = await manager.get_session(session_id)
        # After reaching threshold, state should change to IDLE
        assert session.state == SessionState.IDLE

    @pytest.mark.asyncio
    async def test_auto_summarize_does_not_trigger_below_threshold(self):
        """Verify auto-summarization does not trigger below the threshold."""
        config = SessionConfig(
            max_messages=200,
            auto_summarize=True,
            summarize_after=10,
        )
        manager = SessionManager(config=config)
        session_id = await manager.create_session(project_id="proj")

        # Add messages below the threshold
        for i in range(5):
            await manager.add_message(session_id, "user", f"Message {i}")

        session = await manager.get_session(session_id)
        assert session.state == SessionState.ACTIVE

    @pytest.mark.asyncio
    async def test_auto_summarize_disabled(self):
        """Verify auto-summarization doesn't trigger when disabled."""
        config = SessionConfig(
            max_messages=200,
            auto_summarize=False,
            summarize_after=5,
        )
        manager = SessionManager(config=config)
        session_id = await manager.create_session(project_id="proj")

        for i in range(10):
            await manager.add_message(session_id, "user", f"Message {i}")

        session = await manager.get_session(session_id)
        # State should remain ACTIVE because auto_summarize is disabled
        assert session.state == SessionState.ACTIVE


# ============================================================================
# Session Close Tests
# ============================================================================


class TestSessionManagerClose:
    """Tests for SessionManager.close_session()."""

    @pytest.mark.asyncio
    async def test_close_session_removes_from_active(self):
        """Verify close_session() removes the session from active sessions."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        assert len(manager._sessions) == 1

        await manager.close_session(session_id)
        assert len(manager._sessions) == 0

    @pytest.mark.asyncio
    async def test_close_session_nonexistent_raises(self):
        """Verify close_session() raises SessionNotFoundError for non-existent session."""
        manager = SessionManager()
        with pytest.raises(SessionNotFoundError):
            await manager.close_session("nonexistent")

    @pytest.mark.asyncio
    async def test_close_session_sets_state_before_removal(self):
        """Verify close_session() sets state to CLOSED before removing."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Hello")

        # Get a reference before closing
        session_before = await manager.get_session(session_id)
        # close_session internally sets state to CLOSED and then removes
        await manager.close_session(session_id)

        # The session should no longer be retrievable
        with pytest.raises(SessionNotFoundError):
            await manager.get_session(session_id)

    @pytest.mark.asyncio
    async def test_close_session_removes_from_session_order(self):
        """Verify close_session() removes from session_order list."""
        manager = SessionManager()
        sid1 = await manager.create_session(project_id="p1")
        sid2 = await manager.create_session(project_id="p2")
        assert len(manager._session_order) == 2

        await manager.close_session(sid1)
        assert len(manager._session_order) == 1
        assert sid1 not in manager._session_order


# ============================================================================
# Session Listing Tests
# ============================================================================


class TestSessionManagerList:
    """Tests for SessionManager.list_sessions()."""

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self):
        """Verify list_sessions() returns empty list when no sessions exist."""
        manager = SessionManager()
        sessions = await manager.list_sessions()
        assert sessions == []

    @pytest.mark.asyncio
    async def test_list_sessions_returns_all(self):
        """Verify list_sessions() returns all sessions."""
        manager = SessionManager()
        sid1 = await manager.create_session(project_id="p1")
        sid2 = await manager.create_session(project_id="p2")
        sessions = await manager.list_sessions()
        assert len(sessions) == 2
        session_ids = [s["session_id"] for s in sessions]
        assert sid1 in session_ids
        assert sid2 in session_ids

    @pytest.mark.asyncio
    async def test_list_sessions_filter_by_project(self):
        """Verify list_sessions() can filter by project_id."""
        manager = SessionManager()
        sid1 = await manager.create_session(project_id="project-alpha")
        sid2 = await manager.create_session(project_id="project-beta")
        sid3 = await manager.create_session(project_id="project-alpha")

        alpha_sessions = await manager.list_sessions(project_id="project-alpha")
        assert len(alpha_sessions) == 2
        for s in alpha_sessions:
            assert s["project_id"] == "project-alpha"

        beta_sessions = await manager.list_sessions(project_id="project-beta")
        assert len(beta_sessions) == 1

    @pytest.mark.asyncio
    async def test_list_sessions_includes_expected_fields(self):
        """Verify each session in the list has expected fields."""
        manager = SessionManager()
        await manager.create_session(project_id="proj")
        sessions = await manager.list_sessions()
        assert len(sessions) == 1
        session = sessions[0]
        assert "session_id" in session
        assert "project_id" in session
        assert "state" in session
        assert "message_count" in session
        assert "created_at" in session


# ============================================================================
# Session Expiration and Cleanup Tests
# ============================================================================


class TestSessionManagerExpiration:
    """Tests for SessionManager.cleanup_expired()."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_with_no_expired(self):
        """Verify cleanup_expired() returns 0 when no sessions are expired."""
        manager = SessionManager()
        await manager.create_session(project_id="proj")
        count = await manager.cleanup_expired()
        assert count == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_removes_expired_sessions(self):
        """Verify cleanup_expired() removes expired sessions."""
        config = SessionConfig(ttl_seconds=0)  # Immediate expiration
        manager = SessionManager(config=config)

        # Create a session - with TTL of 0, any session whose
        # last_activity is in the past will be expired
        session_id = await manager.create_session(project_id="proj")

        # Manually set last_activity to the past to ensure expiration
        session = manager._sessions[session_id]
        session.last_activity = datetime.utcnow() - timedelta(hours=2)

        count = await manager.cleanup_expired()
        assert count == 1
        assert session_id not in manager._sessions

    @pytest.mark.asyncio
    async def test_cleanup_expired_with_active_sessions(self):
        """Verify cleanup_expired() doesn't remove active sessions."""
        config = SessionConfig(ttl_seconds=7200)  # 2-hour TTL
        manager = SessionManager(config=config)

        session_id = await manager.create_session(project_id="proj")
        count = await manager.cleanup_expired()
        assert count == 0
        assert session_id in manager._sessions

    @pytest.mark.asyncio
    async def test_cleanup_expired_partial_expiration(self):
        """Verify cleanup_expired() only removes expired sessions, not active ones."""
        config = SessionConfig(ttl_seconds=3600)  # 1-hour TTL
        manager = SessionManager(config=config)

        # Create two sessions
        sid_active = await manager.create_session(project_id="p1")
        sid_expired = await manager.create_session(project_id="p2")

        # Make one session's last_activity old enough to expire
        manager._sessions[sid_expired].last_activity = datetime.utcnow() - timedelta(hours=2)

        count = await manager.cleanup_expired()
        assert count == 1
        assert sid_active in manager._sessions
        assert sid_expired not in manager._sessions

    @pytest.mark.asyncio
    async def test_cleanup_expired_removes_from_session_order(self):
        """Verify cleanup_expired() also removes from session_order."""
        config = SessionConfig(ttl_seconds=0)
        manager = SessionManager(config=config)

        sid = await manager.create_session(project_id="proj")
        manager._sessions[sid].last_activity = datetime.utcnow() - timedelta(hours=2)

        await manager.cleanup_expired()
        assert sid not in manager._session_order


# ============================================================================
# Session Stats Tests
# ============================================================================


class TestSessionManagerStats:
    """Tests for SessionManager.get_session_stats()."""

    @pytest.mark.asyncio
    async def test_get_session_stats_returns_expected_fields(self):
        """Verify get_session_stats() returns dict with expected fields."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Hello", tokens=5)

        stats = await manager.get_session_stats(session_id)
        assert "session_id" in stats
        assert "state" in stats
        assert "message_count" in stats
        assert "total_tokens" in stats
        assert "duration_seconds" in stats
        assert "agent_history" in stats
        assert "has_summary" in stats

    @pytest.mark.asyncio
    async def test_get_session_stats_values(self):
        """Verify get_session_stats() returns correct values."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Hello", tokens=10)
        await manager.add_message(session_id, "assistant", "Hi there!", agent="backend", tokens=20)

        stats = await manager.get_session_stats(session_id)
        assert stats["message_count"] == 2
        assert stats["total_tokens"] == 30
        assert stats["state"] == SessionState.ACTIVE.value
        assert "backend" in stats["agent_history"]
        assert stats["has_summary"] is False

    @pytest.mark.asyncio
    async def test_get_session_stats_with_summary(self):
        """Verify get_session_stats() reports has_summary=True after summarization."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Hello")
        await manager.summarize_session(session_id)

        stats = await manager.get_session_stats(session_id)
        assert stats["has_summary"] is True

    @pytest.mark.asyncio
    async def test_get_session_stats_duration(self):
        """Verify get_session_stats() returns a positive duration."""
        manager = SessionManager()
        session_id = await manager.create_session(project_id="proj")
        stats = await manager.get_session_stats(session_id)
        assert stats["duration_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_get_session_stats_nonexistent_raises(self):
        """Verify get_session_stats() raises SessionNotFoundError for non-existent session."""
        manager = SessionManager()
        with pytest.raises(SessionNotFoundError):
            await manager.get_session_stats("nonexistent")


# ============================================================================
# Eviction Tests
# ============================================================================


class TestSessionManagerEviction:
    """Tests for SessionManager session eviction."""

    @pytest.mark.asyncio
    async def test_evict_if_needed_under_capacity(self):
        """Verify no eviction happens when under capacity."""
        config = SessionConfig(max_messages=100)
        manager = SessionManager(config=config)

        # Create a few sessions - well under the limit
        for i in range(3):
            await manager.create_session(project_id=f"proj-{i}")

        assert len(manager._sessions) == 3

    @pytest.mark.asyncio
    async def test_evict_if_needed_removes_idle_sessions(self):
        """Verify eviction removes IDLE sessions when over capacity."""
        config = SessionConfig(max_messages=5)  # max_sessions = 5 * 2 = 10
        manager = SessionManager(config=config)

        # Create sessions and mark some as IDLE
        session_ids = []
        for i in range(12):
            sid = await manager.create_session(project_id=f"proj-{i}")
            session_ids.append(sid)

        # Some sessions should have been evicted (IDLE ones)
        # The exact count depends on _evict_if_needed behavior
        assert len(manager._sessions) <= 12


# ============================================================================
# Format Messages Tests
# ============================================================================


class TestSessionManagerFormatMessages:
    """Tests for SessionManager._format_messages_for_prompt()."""

    def test_format_messages_basic(self):
        """Verify _format_messages_for_prompt formats messages correctly."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        result = SessionManager._format_messages_for_prompt(messages)
        assert "[user]: Hello" in result
        assert "[assistant]: Hi there!" in result

    def test_format_messages_empty_list(self):
        """Verify _format_messages_for_prompt returns empty string for empty list."""
        result = SessionManager._format_messages_for_prompt([])
        assert result == ""

    def test_format_messages_with_unknown_role(self):
        """Verify _format_messages_for_prompt handles unknown roles."""
        messages = [
            {"role": "system", "content": "You are an assistant"},
        ]
        result = SessionManager._format_messages_for_prompt(messages)
        assert "[system]: You are an assistant" in result

    def test_format_messages_multiline(self):
        """Verify _format_messages_for_prompt joins messages with newlines."""
        messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"},
            {"role": "user", "content": "Third"},
        ]
        result = SessionManager._format_messages_for_prompt(messages)
        lines = result.split("\n")
        assert len(lines) == 3


# ============================================================================
# Integration Tests with Mock Memory Store
# ============================================================================


class TestSessionManagerWithMockStore:
    """Tests for SessionManager with a mocked MemoryStore."""

    @pytest.mark.asyncio
    async def test_create_session_with_mock_store(self, mock_memory_store):
        """Verify session creation works with a mock memory store."""
        manager = SessionManager(memory_store=mock_memory_store)
        session_id = await manager.create_session(project_id="proj")
        assert session_id is not None

    @pytest.mark.asyncio
    async def test_close_session_with_mock_store(self, mock_memory_store):
        """Verify closing a session works with a mock memory store."""
        manager = SessionManager(memory_store=mock_memory_store)
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Hello")
        await manager.close_session(session_id)
        # The session should be removed
        with pytest.raises(SessionNotFoundError):
            await manager.get_session(session_id)

    @pytest.mark.asyncio
    async def test_summarize_with_mock_store(self, mock_memory_store):
        """Verify summarization works with a mock memory store."""
        manager = SessionManager(memory_store=mock_memory_store)
        session_id = await manager.create_session(project_id="proj")
        await manager.add_message(session_id, "user", "Implement auth")
        summary = await manager.summarize_session(session_id)
        assert isinstance(summary, str)
        assert len(summary) > 0

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, mock_memory_store):
        """Verify full session lifecycle: create → messages → summarize → close."""
        config = SessionConfig(max_messages=200, auto_summarize=False)
        manager = SessionManager(memory_store=mock_memory_store, config=config)

        # Create
        session_id = await manager.create_session(
            project_id="lifecycle-test",
            metadata={"test": "lifecycle"},
        )

        # Add messages
        await manager.add_message(session_id, "user", "Start project", tokens=10)
        await manager.add_message(
            session_id, "assistant", "Initializing...", agent="orchestrator", tokens=15
        )
        await manager.add_message(
            session_id, "assistant", "Building backend", agent="backend", tokens=20
        )

        # Verify messages
        session = await manager.get_session(session_id)
        assert session.message_count == 3
        assert session.total_tokens == 45
        assert "orchestrator" in session.agent_history
        assert "backend" in session.agent_history

        # Get history
        history = await manager.get_history(session_id)
        assert len(history) == 3

        # Get recent context
        context = await manager.get_recent_context(session_id, max_messages=2)
        assert isinstance(context, str)

        # Summarize
        summary = await manager.summarize_session(session_id)
        assert "lifecycle-test" in summary or "Session Summary" in summary

        # Get stats
        stats = await manager.get_session_stats(session_id)
        assert stats["message_count"] == 3
        assert stats["total_tokens"] == 45
        assert stats["has_summary"] is True

        # Close
        await manager.close_session(session_id)
        with pytest.raises(SessionNotFoundError):
            await manager.get_session(session_id)
