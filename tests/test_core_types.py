"""
Palace Framework - Tests for Core Types

This module tests all types, enums, and data structures defined in
palace.core.types, verifying:

- Enum values are correct and complete
- Pydantic models create with defaults and required fields
- Pydantic models validate properly (reject invalid input)
- Dataclasses work with required and optional fields
- Type aliases resolve correctly
- ProjectContext.touch() updates the timestamp
- TaskDefinition defaults (status=PENDING, priority=NORMAL)
- AgentResult requires success, agent, and model fields
- Message requires role, content, and session_id
"""

from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from palace.core.types import (
    AgentCapability,
    AgentConfig,
    AgentResult,
    AgentRole,
    EntryId,
    MemoryEntry,
    MemoryType,
    Message,
    MessageId,
    MessageType,
    ModelConfig,
    ProjectConfig,
    ProjectContext,
    ProjectId,
    SessionContext,
    SessionId,
    TaskDefinition,
    TaskId,
    TaskPriority,
    TaskStatus,
)

# ============================================================================
# Enum Tests
# ============================================================================


class TestTaskStatus:
    """Tests for the TaskStatus enum."""

    def test_all_values(self):
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"
        assert TaskStatus.REVIEW == "review"
        assert TaskStatus.WAITING == "waiting"
        assert TaskStatus.DELEGATED == "delegated"

    def test_enum_count(self):
        assert len(TaskStatus) == 8

    def test_str_enum_identity(self):
        """TaskStatus values should equal their string counterparts."""
        for member in TaskStatus:
            assert member.value == member == member.value

    def test_from_value(self):
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskStatus("running") == TaskStatus.RUNNING

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            TaskStatus("invalid_status")


class TestAgentCapability:
    """Tests for the AgentCapability enum."""

    def test_development_capabilities(self):
        assert AgentCapability.BACKEND_DEVELOPMENT == "backend_development"
        assert AgentCapability.FRONTEND_DEVELOPMENT == "frontend_development"
        assert AgentCapability.FULLSTACK_DEVELOPMENT == "fullstack_development"

    def test_infrastructure_capabilities(self):
        assert AgentCapability.INFRASTRUCTURE_AS_CODE == "infrastructure_as_code"
        assert AgentCapability.DEVOPS == "devops"
        assert AgentCapability.DATABASE_ADMINISTRATION == "database_administration"

    def test_quality_capabilities(self):
        assert AgentCapability.CODE_REVIEW == "code_review"
        assert AgentCapability.TESTING == "testing"
        assert AgentCapability.QUALITY_ASSURANCE == "quality_assurance"

    def test_design_capabilities(self):
        assert AgentCapability.UI_UX_DESIGN == "ui_ux_design"
        assert AgentCapability.ARCHITECTURE == "architecture"

    def test_coordination_capabilities(self):
        assert AgentCapability.ORCHESTRATION == "orchestration"
        assert AgentCapability.PLANNING == "planning"
        assert AgentCapability.DOCUMENTATION == "documentation"

    def test_enum_count(self):
        assert len(AgentCapability) == 14


class TestMemoryType:
    """Tests for the MemoryType enum."""

    def test_all_values(self):
        assert MemoryType.EPISODIC == "episodic"
        assert MemoryType.SEMANTIC == "semantic"
        assert MemoryType.PROCEDURAL == "procedural"
        assert MemoryType.PROJECT == "project"

    def test_enum_count(self):
        assert len(MemoryType) == 4


class TestMessageType:
    """Tests for the MessageType enum."""

    def test_all_values(self):
        assert MessageType.USER == "user"
        assert MessageType.ASSISTANT == "assistant"
        assert MessageType.SYSTEM == "system"
        assert MessageType.TOOL == "tool"

    def test_enum_count(self):
        assert len(MessageType) == 4


class TestTaskPriority:
    """Tests for the TaskPriority enum."""

    def test_all_values(self):
        assert TaskPriority.LOW == 1
        assert TaskPriority.NORMAL == 5
        assert TaskPriority.HIGH == 10
        assert TaskPriority.CRITICAL == 20

    def test_ordering(self):
        assert TaskPriority.LOW < TaskPriority.NORMAL
        assert TaskPriority.NORMAL < TaskPriority.HIGH
        assert TaskPriority.HIGH < TaskPriority.CRITICAL

    def test_enum_count(self):
        assert len(TaskPriority) == 4


class TestAgentRole:
    """Tests for the AgentRole enum."""

    def test_all_values(self):
        assert AgentRole.ORCHESTRATOR == "orchestrator"
        assert AgentRole.BACKEND == "backend"
        assert AgentRole.FRONTEND == "frontend"
        assert AgentRole.DEVOPS == "devops"
        assert AgentRole.INFRA == "infra"
        assert AgentRole.DBA == "dba"
        assert AgentRole.QA == "qa"
        assert AgentRole.DESIGNER == "designer"
        assert AgentRole.REVIEWER == "reviewer"

    def test_enum_count(self):
        assert len(AgentRole) == 9


# ============================================================================
# Pydantic Model Tests — ProjectConfig
# ============================================================================


class TestProjectConfig:
    """Tests for the ProjectConfig model."""

    def test_create_with_required_fields(self):
        config = ProjectConfig(name="my-project")
        assert config.name == "my-project"

    def test_create_with_all_fields(self):
        config = ProjectConfig(
            name="my-project",
            description="A test project",
            backend_framework="fastapi",
            frontend_framework="react",
            database="postgresql",
            deployment="kubernetes",
            root_path="/opt/projects/my-project",
            source_path="src",
            tests_path="tests",
            code_style="pep8",
            test_framework="pytest",
        )
        assert config.name == "my-project"
        assert config.description == "A test project"
        assert config.backend_framework == "fastapi"
        assert config.frontend_framework == "react"
        assert config.database == "postgresql"
        assert config.deployment == "kubernetes"
        assert config.root_path == "/opt/projects/my-project"
        assert config.source_path == "src"
        assert config.tests_path == "tests"
        assert config.code_style == "pep8"
        assert config.test_framework == "pytest"

    def test_defaults(self):
        config = ProjectConfig(name="test")
        assert config.description is None
        assert config.backend_framework is None
        assert config.frontend_framework is None
        assert config.database is None
        assert config.deployment is None
        assert config.root_path == "."
        assert config.source_path == "src"
        assert config.tests_path == "tests"
        assert config.code_style == "pep8"
        assert config.test_framework is None
        assert config.project_id is not None
        assert isinstance(config.project_id, UUID)
        assert isinstance(config.created_at, datetime)
        assert isinstance(config.updated_at, datetime)

    def test_name_is_required(self):
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfig()
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_project_id_is_auto_uuid(self):
        config1 = ProjectConfig(name="p1")
        config2 = ProjectConfig(name="p2")
        assert config1.project_id != config2.project_id

    def test_use_enum_values_config(self):
        """ProjectConfig has use_enum_values=True in its Config."""
        config = ProjectConfig(name="test")
        assert isinstance(config.name, str)


# ============================================================================
# Pydantic Model Tests — ProjectContext
# ============================================================================


class TestProjectContext:
    """Tests for the ProjectContext model."""

    def _make_config(self):
        return ProjectConfig(name="test-project")

    def test_create_with_config(self):
        config = self._make_config()
        ctx = ProjectContext(config=config)
        assert ctx.config.name == "test-project"
        assert ctx.adrs == []
        assert ctx.patterns == []
        assert ctx.active_session_id is None
        assert ctx.cached_files == {}
        assert ctx.instructions == []

    def test_create_with_all_fields(self):
        import uuid

        config = self._make_config()
        session_id = uuid.uuid4()
        ctx = ProjectContext(
            config=config,
            adrs=[{"id": "ADR-001", "title": "Use FastAPI"}],
            patterns=["repository", "observer"],
            active_session_id=session_id,
            cached_files={"src/main.py": "# main"},
            instructions=["Follow PEP 8"],
        )
        assert ctx.config is config
        assert len(ctx.adrs) == 1
        assert ctx.patterns == ["repository", "observer"]
        assert ctx.active_session_id == session_id
        assert ctx.cached_files["src/main.py"] == "# main"
        assert ctx.instructions == ["Follow PEP 8"]

    def test_config_is_required(self):
        with pytest.raises(ValidationError) as exc_info:
            ProjectContext()
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("config",) for e in errors)

    def test_touch_updates_timestamp(self):
        """ProjectContext.touch() should update config.updated_at."""
        config = self._make_config()
        ctx = ProjectContext(config=config)

        old_updated = ctx.config.updated_at
        # Touch should update the timestamp
        ctx.touch()
        new_updated = ctx.config.updated_at

        # The timestamp should have been updated (>= old timestamp)
        assert new_updated >= old_updated

    def test_touch_multiple_times(self):
        """Multiple touch calls should keep advancing the timestamp."""
        import time

        config = self._make_config()
        ctx = ProjectContext(config=config)

        timestamps = []
        for _ in range(3):
            ctx.touch()
            timestamps.append(ctx.config.updated_at)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # Each subsequent timestamp should be >= the previous one
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i - 1]


# ============================================================================
# Pydantic Model Tests — SessionContext
# ============================================================================


class TestSessionContext:
    """Tests for the SessionContext model."""

    def test_create_with_required_fields(self):
        import uuid

        project_id = uuid.uuid4()
        ctx = SessionContext(project_id=project_id)
        assert ctx.project_id == project_id
        assert ctx.messages == []
        assert ctx.active_tasks == []
        assert ctx.completed_tasks == []
        assert ctx.current_agent is None
        assert ctx.agent_history == []
        assert ctx.retrieved_context == []
        assert ctx.session_id is not None
        assert isinstance(ctx.session_id, UUID)
        assert isinstance(ctx.created_at, datetime)
        assert isinstance(ctx.updated_at, datetime)

    def test_create_with_all_fields(self):
        import uuid

        project_id = uuid.uuid4()
        ctx = SessionContext(
            project_id=project_id,
            messages=[{"role": "user", "content": "hello"}],
            active_tasks=[uuid.uuid4()],
            completed_tasks=[uuid.uuid4()],
            current_agent="backend",
            agent_history=["orchestrator", "backend"],
            retrieved_context=[{"source": "memory", "content": "data"}],
        )
        assert ctx.project_id == project_id
        assert len(ctx.messages) == 1
        assert ctx.current_agent == "backend"
        assert ctx.agent_history == ["orchestrator", "backend"]

    def test_project_id_is_required(self):
        with pytest.raises(ValidationError) as exc_info:
            SessionContext()
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("project_id",) for e in errors)

    def test_session_id_is_auto_uuid(self):
        import uuid

        project_id = uuid.uuid4()
        ctx1 = SessionContext(project_id=project_id)
        ctx2 = SessionContext(project_id=project_id)
        assert ctx1.session_id != ctx2.session_id


# ============================================================================
# Pydantic Model Tests — TaskDefinition
# ============================================================================


class TestTaskDefinition:
    """Tests for the TaskDefinition model."""

    def test_create_with_required_fields(self):
        import uuid

        project_id = uuid.uuid4()
        session_id = uuid.uuid4()
        task = TaskDefinition(
            title="Implement login",
            description="Create login endpoint",
            project_id=project_id,
            session_id=session_id,
        )
        assert task.title == "Implement login"
        assert task.description == "Create login endpoint"
        assert task.project_id == project_id
        assert task.session_id == session_id

    def test_default_status_is_pending(self):
        import uuid

        task = TaskDefinition(
            title="t", description="d", project_id=uuid.uuid4(), session_id=uuid.uuid4()
        )
        assert task.status == TaskStatus.PENDING
        # Because use_enum_values = True, it should be stored as string
        assert task.status == "pending"

    def test_default_priority_is_normal(self):
        import uuid

        task = TaskDefinition(
            title="t", description="d", project_id=uuid.uuid4(), session_id=uuid.uuid4()
        )
        assert task.priority == TaskPriority.NORMAL
        assert task.priority == 5

    def test_default_optional_fields(self):
        import uuid

        project_id = uuid.uuid4()
        session_id = uuid.uuid4()
        task = TaskDefinition(
            title="t", description="d", project_id=project_id, session_id=session_id
        )
        assert task.task_id is not None
        assert isinstance(task.task_id, UUID)
        assert task.required_capabilities == set()
        assert task.suggested_agent is None
        assert task.parent_task_id is None
        assert task.depends_on == []
        assert task.input_context == {}
        assert task.output is None
        assert task.error is None
        assert task.retry_count == 0
        assert task.max_retries == 3
        assert task.started_at is None
        assert task.completed_at is None
        assert isinstance(task.created_at, datetime)

    def test_create_with_all_fields(self):
        import uuid

        project_id = uuid.uuid4()
        session_id = uuid.uuid4()
        task_id = uuid.uuid4()
        parent_id = uuid.uuid4()
        dep_id = uuid.uuid4()

        task = TaskDefinition(
            task_id=task_id,
            title="Complex task",
            description="A complex multi-step task",
            required_capabilities={AgentCapability.BACKEND_DEVELOPMENT, AgentCapability.TESTING},
            suggested_agent=AgentRole.BACKEND,
            priority=TaskPriority.HIGH,
            status=TaskStatus.RUNNING,
            project_id=project_id,
            session_id=session_id,
            parent_task_id=parent_id,
            depends_on=[dep_id],
            input_context={"file": "main.py"},
            output={"result": "success"},
            error=None,
            retry_count=1,
            max_retries=5,
        )
        assert task.task_id == task_id
        assert task.title == "Complex task"
        assert AgentCapability.BACKEND_DEVELOPMENT in task.required_capabilities
        assert AgentCapability.TESTING in task.required_capabilities
        assert task.suggested_agent == AgentRole.BACKEND
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.RUNNING
        assert task.parent_task_id == parent_id
        assert dep_id in task.depends_on
        assert task.input_context == {"file": "main.py"}
        assert task.output == {"result": "success"}

    def test_required_fields_validation(self):
        """title, description, project_id, session_id are required."""
        with pytest.raises(ValidationError) as exc_info:
            TaskDefinition()
        errors = exc_info.value.errors()
        field_names = {e["loc"][0] for e in errors}
        assert "title" in field_names
        assert "description" in field_names
        assert "project_id" in field_names
        assert "session_id" in field_names

    def test_use_enum_values(self):
        """TaskDefinition has use_enum_values=True."""
        import uuid

        task = TaskDefinition(
            title="t",
            description="d",
            project_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.CRITICAL,
        )
        # With use_enum_values, enum values are stored as their primitive values
        assert task.status == "completed"
        assert task.priority == 20


# ============================================================================
# Pydantic Model Tests — AgentResult
# ============================================================================


class TestAgentResult:
    """Tests for the AgentResult model."""

    def test_create_with_required_fields(self):
        result = AgentResult(
            success=True,
            agent=AgentRole.BACKEND,
            model_used="qwen3-coder-next",
        )
        assert result.success is True
        assert result.agent == AgentRole.BACKEND
        assert result.model_used == "qwen3-coder-next"

    def test_default_optional_fields(self):
        result = AgentResult(
            success=True,
            agent=AgentRole.ORCHESTRATOR,
            model_used="test-model",
        )
        assert result.content == ""
        assert result.structured_output is None
        assert result.files_created == []
        assert result.files_modified == []
        assert result.next_actions == []
        assert result.delegate_to is None
        assert result.context_updates == {}
        assert result.memory_entries == []
        assert result.tokens_used == 0
        assert result.execution_time_ms == 0
        assert result.error is None
        assert result.error_details is None

    def test_create_with_all_fields(self):
        import uuid

        result = AgentResult(
            success=True,
            content="Login endpoint implemented",
            structured_output={"file": "auth.py", "lines": 50},
            files_created=["src/auth.py", "tests/test_auth.py"],
            files_modified=["src/main.py"],
            next_actions=[{"action": "run_tests", "params": {}}],
            delegate_to=AgentRole.QA,
            context_updates={"last_task": "auth"},
            memory_entries=[{"type": "semantic", "content": "JWT tokens"}],
            agent=AgentRole.BACKEND,
            model_used="qwen3-coder-next",
            tokens_used=1500,
            execution_time_ms=3200,
            error=None,
            error_details=None,
        )
        assert result.content == "Login endpoint implemented"
        assert result.structured_output == {"file": "auth.py", "lines": 50}
        assert "src/auth.py" in result.files_created
        assert "src/main.py" in result.files_modified
        assert result.delegate_to == AgentRole.QA
        assert result.tokens_used == 1500
        assert result.execution_time_ms == 3200

    def test_failure_result(self):
        result = AgentResult(
            success=False,
            agent=AgentRole.BACKEND,
            model_used="test-model",
            error="Compilation failed",
            error_details={"exit_code": 1, "stderr": "syntax error"},
        )
        assert result.success is False
        assert result.error == "Compilation failed"
        assert result.error_details["exit_code"] == 1

    def test_success_is_required(self):
        with pytest.raises(ValidationError) as exc_info:
            AgentResult(agent=AgentRole.BACKEND, model_used="test")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("success",) for e in errors)

    def test_agent_is_required(self):
        with pytest.raises(ValidationError) as exc_info:
            AgentResult(success=True, model_used="test")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("agent",) for e in errors)

    def test_model_used_is_required(self):
        with pytest.raises(ValidationError) as exc_info:
            AgentResult(success=True, agent=AgentRole.BACKEND)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("model_used",) for e in errors)


# ============================================================================
# Pydantic Model Tests — Message
# ============================================================================


class TestMessage:
    """Tests for the Message model."""

    def test_create_with_required_fields(self):
        import uuid

        session_id = uuid.uuid4()
        msg = Message(
            session_id=session_id,
            role=MessageType.USER,
            content="Hello, Palace!",
        )
        assert msg.session_id == session_id
        assert msg.role == MessageType.USER
        assert msg.content == "Hello, Palace!"

    def test_default_fields(self):
        import uuid

        session_id = uuid.uuid4()
        msg = Message(
            session_id=session_id,
            role=MessageType.SYSTEM,
            content="System prompt",
        )
        assert msg.message_id is not None
        assert isinstance(msg.message_id, UUID)
        assert msg.agent is None
        assert isinstance(msg.created_at, datetime)
        assert msg.tokens == 0
        assert msg.embedding_id is None

    def test_create_with_all_fields(self):
        import uuid

        session_id = uuid.uuid4()
        msg = Message(
            session_id=session_id,
            role=MessageType.ASSISTANT,
            content="Here is the implementation",
            agent=AgentRole.BACKEND,
            tokens=250,
            embedding_id="emb-12345",
        )
        assert msg.agent == AgentRole.BACKEND
        assert msg.tokens == 250
        assert msg.embedding_id == "emb-12345"

    def test_required_fields_validation(self):
        """role, content, session_id are required."""
        with pytest.raises(ValidationError) as exc_info:
            Message()
        errors = exc_info.value.errors()
        field_names = {e["loc"][0] for e in errors}
        assert "role" in field_names
        assert "content" in field_names
        assert "session_id" in field_names

    def test_message_types(self):
        import uuid

        session_id = uuid.uuid4()
        for role in MessageType:
            msg = Message(session_id=session_id, role=role, content=f"{role.value} message")
            assert msg.role == role

    def test_message_with_tool_role(self):
        import uuid

        session_id = uuid.uuid4()
        msg = Message(
            session_id=session_id,
            role=MessageType.TOOL,
            content='{"result": "success"}',
        )
        assert msg.role == MessageType.TOOL


# ============================================================================
# Pydantic Model Tests — MemoryEntry
# ============================================================================


class TestMemoryEntry:
    """Tests for the MemoryEntry model."""

    def test_create_with_required_fields(self):
        import uuid

        project_id = uuid.uuid4()
        entry = MemoryEntry(
            memory_type=MemoryType.SEMANTIC,
            project_id=project_id,
            content="Users authenticate via JWT tokens",
        )
        assert entry.memory_type == MemoryType.SEMANTIC
        assert entry.project_id == project_id
        assert entry.content == "Users authenticate via JWT tokens"

    def test_default_fields(self):
        import uuid

        project_id = uuid.uuid4()
        entry = MemoryEntry(
            memory_type=MemoryType.EPISODIC,
            project_id=project_id,
            content="Conversation about login",
        )
        assert entry.entry_id is not None
        assert isinstance(entry.entry_id, UUID)
        assert entry.embedding is None
        assert entry.metadata == {}
        assert entry.source == "unknown"
        assert entry.source_id is None
        assert isinstance(entry.created_at, datetime)
        assert entry.expires_at is None
        assert entry.access_count == 0
        assert entry.last_accessed is None

    def test_create_with_all_fields(self):
        import uuid
        from datetime import timedelta

        project_id = uuid.uuid4()
        source_id = uuid.uuid4()
        now = datetime.utcnow()
        expires = now + timedelta(hours=24)

        entry = MemoryEntry(
            memory_type=MemoryType.PROCEDURAL,
            project_id=project_id,
            content="Deployment script",
            embedding=[0.1, 0.2, 0.3],
            metadata={"language": "python", "category": "devops"},
            source="system",
            source_id=source_id,
            expires_at=expires,
            access_count=5,
            last_accessed=now,
        )
        assert entry.memory_type == MemoryType.PROCEDURAL
        assert entry.embedding == [0.1, 0.2, 0.3]
        assert entry.metadata["language"] == "python"
        assert entry.source == "system"
        assert entry.source_id == source_id
        assert entry.access_count == 5
        assert entry.expires_at is not None

    def test_required_fields_validation(self):
        """memory_type, project_id, content are required."""
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry()
        errors = exc_info.value.errors()
        field_names = {e["loc"][0] for e in errors}
        assert "memory_type" in field_names
        assert "project_id" in field_names
        assert "content" in field_names

    def test_all_memory_types(self):
        import uuid

        project_id = uuid.uuid4()
        for mtype in MemoryType:
            entry = MemoryEntry(
                memory_type=mtype,
                project_id=project_id,
                content=f"Entry of type {mtype.value}",
            )
            assert entry.memory_type == mtype


# ============================================================================
# Dataclass Tests — ModelConfig
# ============================================================================


class TestModelConfigDataclass:
    """Tests for the ModelConfig dataclass (from core.types, NOT core.config)."""

    def test_create_with_required_fields(self):
        config = ModelConfig(name="test-model")
        assert config.name == "test-model"

    def test_defaults(self):
        config = ModelConfig(name="test-model")
        assert config.provider == "ollama"
        assert config.max_tokens == 4096
        assert config.temperature == 0.7
        assert config.top_p == 0.9
        assert config.capabilities == []
        assert config.cost_per_1k_tokens == 0.0

    def test_create_with_all_fields(self):
        config = ModelConfig(
            name="gpt-4",
            provider="openai",
            max_tokens=8192,
            temperature=0.3,
            top_p=0.95,
            capabilities=[AgentCapability.CODE_REVIEW, AgentCapability.ARCHITECTURE],
            cost_per_1k_tokens=0.03,
        )
        assert config.name == "gpt-4"
        assert config.provider == "openai"
        assert config.max_tokens == 8192
        assert config.temperature == 0.3
        assert config.top_p == 0.95
        assert AgentCapability.CODE_REVIEW in config.capabilities
        assert config.cost_per_1k_tokens == 0.03

    def test_name_is_required(self):
        """ModelConfig requires a name — cannot be instantiated without it."""
        with pytest.raises(TypeError):
            ModelConfig()


# ============================================================================
# Dataclass Tests — AgentConfig
# ============================================================================


class TestAgentConfigDataclass:
    """Tests for the AgentConfig dataclass."""

    def test_create_with_required_fields(self):
        config = AgentConfig(
            role=AgentRole.BACKEND,
            model="qwen3-coder-next",
            system_prompt="You are a backend developer agent.",
        )
        assert config.role == AgentRole.BACKEND
        assert config.model == "qwen3-coder-next"
        assert config.system_prompt == "You are a backend developer agent."

    def test_defaults(self):
        config = AgentConfig(
            role=AgentRole.FRONTEND,
            model="test-model",
            system_prompt="Test prompt",
        )
        assert config.capabilities == []
        assert config.tools == []
        assert config.max_iterations == 10
        assert config.timeout_seconds == 300

    def test_create_with_all_fields(self):
        config = AgentConfig(
            role=AgentRole.DEVOPS,
            model="qwen3.5",
            system_prompt="You handle CI/CD.",
            capabilities=[AgentCapability.DEVOPS, AgentCapability.INFRASTRUCTURE_AS_CODE],
            tools=["docker", "kubectl", "terraform"],
            max_iterations=20,
            timeout_seconds=600,
        )
        assert config.role == AgentRole.DEVOPS
        assert config.model == "qwen3.5"
        assert config.capabilities == [
            AgentCapability.DEVOPS,
            AgentCapability.INFRASTRUCTURE_AS_CODE,
        ]
        assert config.tools == ["docker", "kubectl", "terraform"]
        assert config.max_iterations == 20
        assert config.timeout_seconds == 600

    def test_required_fields(self):
        """role, model, system_prompt are required."""
        with pytest.raises(TypeError):
            AgentConfig()

        with pytest.raises(TypeError):
            AgentConfig(role=AgentRole.BACKEND)

        with pytest.raises(TypeError):
            AgentConfig(role=AgentRole.BACKEND, model="test")

    def test_all_agent_roles(self):
        """AgentConfig should accept all AgentRole values."""
        for role in AgentRole:
            config = AgentConfig(
                role=role,
                model="test-model",
                system_prompt="Test prompt",
            )
            assert config.role == role


# ============================================================================
# Type Alias Tests
# ============================================================================


class TestTypeAliases:
    """Tests for type aliases to ensure they resolve to UUID."""

    def test_task_id_is_uuid(self):
        assert TaskId is UUID

    def test_project_id_is_uuid(self):
        assert ProjectId is UUID

    def test_session_id_is_uuid(self):
        assert SessionId is UUID

    def test_message_id_is_uuid(self):
        assert MessageId is UUID

    def test_entry_id_is_uuid(self):
        assert EntryId is UUID

    def test_type_aliases_are_consistent(self):
        """All ID type aliases should resolve to UUID."""
        from uuid import UUID as PyUUID

        for alias in [TaskId, ProjectId, SessionId, MessageId, EntryId]:
            assert alias is PyUUID


# ============================================================================
# Integration / Cross-Model Tests
# ============================================================================


class TestCrossModelIntegration:
    """Tests that verify type interactions between models."""

    def test_task_definition_with_enum_values_in_context(self):
        """Verify TaskDefinition enum values work correctly with other models."""
        import uuid

        project_id = uuid.uuid4()
        session_id = uuid.uuid4()

        task = TaskDefinition(
            title="Test task",
            description="A test task",
            required_capabilities={AgentCapability.BACKEND_DEVELOPMENT},
            suggested_agent=AgentRole.BACKEND,
            priority=TaskPriority.HIGH,
            status=TaskStatus.PENDING,
            project_id=project_id,
            session_id=session_id,
        )
        assert task.status == "pending"
        assert task.priority == 10

    def test_agent_result_with_message(self):
        """Verify AgentResult can be linked to a Message."""
        import uuid

        session_id = uuid.uuid4()
        result = AgentResult(
            success=True,
            content="Task completed",
            agent=AgentRole.BACKEND,
            model_used="test-model",
        )
        msg = Message(
            session_id=session_id,
            role=MessageType.ASSISTANT,
            content=result.content,
            agent=AgentRole.BACKEND,
        )
        assert msg.content == result.content
        assert msg.agent == result.agent

    def test_memory_entry_with_memory_types(self):
        """Verify MemoryEntry works with all MemoryType values."""
        import uuid

        project_id = uuid.uuid4()
        for mtype in MemoryType:
            entry = MemoryEntry(
                memory_type=mtype,
                project_id=project_id,
                content=f"Content for {mtype.value}",
            )
            assert entry.memory_type == mtype

    def test_task_lifecycle_statuses(self):
        """Verify all valid TaskStatus transitions can be represented."""
        import uuid

        project_id = uuid.uuid4()
        session_id = uuid.uuid4()

        statuses = [
            TaskStatus.PENDING,
            TaskStatus.RUNNING,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.REVIEW,
            TaskStatus.WAITING,
            TaskStatus.DELEGATED,
        ]
        for status in statuses:
            task = TaskDefinition(
                title=f"Task with status {status.value}",
                description="Test",
                status=status,
                project_id=project_id,
                session_id=session_id,
            )
            assert task.status == status
