"""Tests for palace.pipelines.types — Pipeline type definitions.

Covers StepType, PipelineType, StepConfig, PipelineConfig,
StepDefinition, and PipelineDefinition.
"""

import pytest

from palace.pipelines.types import (
    PipelineConfig,
    PipelineDefinition,
    PipelineType,
    StepConfig,
    StepDefinition,
    StepType,
)

# ---------------------------------------------------------------------------
# StepType enum
# ---------------------------------------------------------------------------


class TestStepType:
    """Tests for the StepType enum."""

    def test_step_type_has_six_values(self):
        """StepType should define exactly 6 members."""
        assert len(StepType) == 6

    def test_step_type_agent_task(self):
        assert StepType.AGENT_TASK == "agent_task"

    def test_step_type_conditional(self):
        assert StepType.CONDITIONAL == "conditional"

    def test_step_type_parallel(self):
        assert StepType.PARALLEL == "parallel"

    def test_step_type_validation(self):
        assert StepType.VALIDATION == "validation"

    def test_step_type_transform(self):
        assert StepType.TRANSFORM == "transform"

    def test_step_type_human_approval(self):
        assert StepType.HUMAN_APPROVAL == "human_approval"

    def test_step_type_values(self):
        values = {m.value for m in StepType}
        assert values == {
            "agent_task",
            "conditional",
            "parallel",
            "validation",
            "transform",
            "human_approval",
        }

    def test_step_type_is_str_enum(self):
        """StepType values should be strings."""
        for member in StepType:
            assert isinstance(member.value, str)


# ---------------------------------------------------------------------------
# PipelineType enum
# ---------------------------------------------------------------------------


class TestPipelineType:
    """Tests for the PipelineType enum."""

    def test_pipeline_type_has_eight_values(self):
        """PipelineType should define exactly 8 members."""
        assert len(PipelineType) == 8

    def test_pipeline_type_feature_development(self):
        assert PipelineType.FEATURE_DEVELOPMENT == "feature_development"

    def test_pipeline_type_code_review(self):
        assert PipelineType.CODE_REVIEW == "code_review"

    def test_pipeline_type_deployment(self):
        assert PipelineType.DEPLOYMENT == "deployment"

    def test_pipeline_type_database_migration(self):
        assert PipelineType.DATABASE_MIGRATION == "database_migration"

    def test_pipeline_type_refactoring(self):
        assert PipelineType.REFACTORING == "refactoring"

    def test_pipeline_type_documentation(self):
        assert PipelineType.DOCUMENTATION == "documentation"

    def test_pipeline_type_bug_fix(self):
        assert PipelineType.BUG_FIX == "bug_fix"

    def test_pipeline_type_custom(self):
        assert PipelineType.CUSTOM == "custom"

    def test_pipeline_type_values(self):
        values = {m.value for m in PipelineType}
        assert values == {
            "feature_development",
            "code_review",
            "deployment",
            "database_migration",
            "refactoring",
            "documentation",
            "bug_fix",
            "custom",
        }

    def test_pipeline_type_is_str_enum(self):
        for member in PipelineType:
            assert isinstance(member.value, str)


# ---------------------------------------------------------------------------
# StepConfig
# ---------------------------------------------------------------------------


class TestStepConfig:
    """Tests for the StepConfig model."""

    def test_required_fields(self):
        """StepConfig requires step_id, name, and step_type."""
        config = StepConfig(
            step_id="step-1",
            name="First step",
            step_type=StepType.AGENT_TASK,
        )
        assert config.step_id == "step-1"
        assert config.name == "First step"
        assert config.step_type == StepType.AGENT_TASK

    def test_defaults(self):
        """StepConfig should provide sensible defaults for optional fields."""
        config = StepConfig(
            step_id="step-1",
            name="First step",
            step_type=StepType.AGENT_TASK,
        )
        assert config.retry_count == 0
        assert config.timeout_seconds == 300
        assert config.depends_on == []
        assert config.parallel_steps == []
        assert config.metadata == {}
        assert config.agent_role is None
        assert config.task_template == ""
        assert config.condition is None
        assert config.validation_criteria is None

    def test_all_fields(self):
        """StepConfig should accept all fields."""
        inner = StepConfig(
            step_id="sub-1",
            name="Sub step",
            step_type=StepType.AGENT_TASK,
        )
        config = StepConfig(
            step_id="step-2",
            name="Second step",
            step_type=StepType.PARALLEL,
            agent_role="backend",
            task_template="Implement {feature}",
            condition="variables.has_tests == True",
            depends_on=["step-1"],
            retry_count=3,
            timeout_seconds=600,
            parallel_steps=[inner],
            validation_criteria="all_tests_pass",
            metadata={"priority": "high"},
        )
        assert config.step_id == "step-2"
        assert config.name == "Second step"
        assert config.step_type == StepType.PARALLEL
        assert config.agent_role == "backend"
        assert config.task_template == "Implement {feature}"
        assert config.condition == "variables.has_tests == True"
        assert config.depends_on == ["step-1"]
        assert config.retry_count == 3
        assert config.timeout_seconds == 600
        assert len(config.parallel_steps) == 1
        assert config.parallel_steps[0].step_id == "sub-1"
        assert config.validation_criteria == "all_tests_pass"
        assert config.metadata == {"priority": "high"}

    def test_depends_on_is_independent(self):
        """Each StepConfig instance should have its own depends_on list."""
        config1 = StepConfig(step_id="s1", name="S1", step_type=StepType.AGENT_TASK)
        config2 = StepConfig(step_id="s2", name="S2", step_type=StepType.AGENT_TASK)
        config1.depends_on.append("other")
        assert config2.depends_on == []

    def test_metadata_is_independent(self):
        """Each StepConfig instance should have its own metadata dict."""
        config1 = StepConfig(step_id="s1", name="S1", step_type=StepType.AGENT_TASK)
        config2 = StepConfig(step_id="s2", name="S2", step_type=StepType.AGENT_TASK)
        config1.metadata["key"] = "value"
        assert config2.metadata == {}

    def test_parallel_steps_is_independent(self):
        """Each StepConfig instance should have its own parallel_steps list."""
        config1 = StepConfig(step_id="s1", name="S1", step_type=StepType.PARALLEL)
        config2 = StepConfig(step_id="s2", name="S2", step_type=StepType.PARALLEL)
        inner = StepConfig(step_id="sub", name="Sub", step_type=StepType.AGENT_TASK)
        config1.parallel_steps.append(inner)
        assert config2.parallel_steps == []

    def test_missing_required_fields(self):
        """StepConfig should raise ValidationError if required fields are missing."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            StepConfig(step_id="s1")  # missing name, step_type

        with pytest.raises(ValidationError):
            StepConfig(name="Step")  # missing step_id, step_type

        with pytest.raises(ValidationError):
            StepConfig(step_type=StepType.AGENT_TASK)  # missing step_id, name

    def test_invalid_step_type(self):
        """StepConfig should reject invalid step_type values."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            StepConfig(
                step_id="s1",
                name="Bad",
                step_type="invalid_type",
            )


# ---------------------------------------------------------------------------
# PipelineConfig
# ---------------------------------------------------------------------------


class TestPipelineConfig:
    """Tests for the PipelineConfig model."""

    def test_required_fields(self):
        """PipelineConfig requires pipeline_id, name, pipeline_type, project_id."""
        config = PipelineConfig(
            pipeline_id="pipe-1",
            name="Test Pipeline",
            pipeline_type=PipelineType.FEATURE_DEVELOPMENT,
            project_id="proj-1",
        )
        assert config.pipeline_id == "pipe-1"
        assert config.name == "Test Pipeline"
        assert config.pipeline_type == PipelineType.FEATURE_DEVELOPMENT
        assert config.project_id == "proj-1"

    def test_defaults(self):
        """PipelineConfig should provide sensible defaults."""
        config = PipelineConfig(
            pipeline_id="pipe-1",
            name="Test",
            pipeline_type=PipelineType.CUSTOM,
            project_id="proj-1",
        )
        assert config.max_retries == 3
        assert config.timeout_seconds == 3600
        assert config.auto_approve is False
        assert config.stop_on_failure is True
        assert config.save_intermediate_results is True
        assert config.description == ""
        assert config.steps == []
        assert config.metadata == {}

    def test_all_fields(self):
        """PipelineConfig should accept all fields."""
        step = StepConfig(step_id="s1", name="S1", step_type=StepType.AGENT_TASK)
        config = PipelineConfig(
            pipeline_id="pipe-2",
            name="Full Pipeline",
            pipeline_type=PipelineType.DEPLOYMENT,
            project_id="proj-2",
            description="A full pipeline config",
            steps=[step],
            max_retries=5,
            timeout_seconds=7200,
            auto_approve=True,
            stop_on_failure=False,
            save_intermediate_results=False,
            metadata={"env": "production"},
        )
        assert config.description == "A full pipeline config"
        assert len(config.steps) == 1
        assert config.max_retries == 5
        assert config.timeout_seconds == 7200
        assert config.auto_approve is True
        assert config.stop_on_failure is False
        assert config.save_intermediate_results is False
        assert config.metadata == {"env": "production"}

    def test_steps_is_independent(self):
        """Each PipelineConfig instance should have its own steps list."""
        config1 = PipelineConfig(
            pipeline_id="p1",
            name="P1",
            pipeline_type=PipelineType.CUSTOM,
            project_id="proj-1",
        )
        config2 = PipelineConfig(
            pipeline_id="p2",
            name="P2",
            pipeline_type=PipelineType.CUSTOM,
            project_id="proj-1",
        )
        step = StepConfig(step_id="s1", name="S1", step_type=StepType.AGENT_TASK)
        config1.steps.append(step)
        assert config2.steps == []

    def test_metadata_is_independent(self):
        """Each PipelineConfig instance should have its own metadata dict."""
        config1 = PipelineConfig(
            pipeline_id="p1",
            name="P1",
            pipeline_type=PipelineType.CUSTOM,
            project_id="proj-1",
        )
        config2 = PipelineConfig(
            pipeline_id="p2",
            name="P2",
            pipeline_type=PipelineType.CUSTOM,
            project_id="proj-1",
        )
        config1.metadata["key"] = "value"
        assert config2.metadata == {}

    def test_missing_required_fields(self):
        """PipelineConfig should raise ValidationError for missing required fields."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PipelineConfig(
                pipeline_id="p1",
                name="P1",
                pipeline_type=PipelineType.CUSTOM,
                # missing project_id
            )

        with pytest.raises(ValidationError):
            PipelineConfig(
                pipeline_id="p1",
                name="P1",
                # missing pipeline_type and project_id
            )


# ---------------------------------------------------------------------------
# StepDefinition
# ---------------------------------------------------------------------------


class TestStepDefinition:
    """Tests for the StepDefinition model."""

    def test_creation(self):
        """StepDefinition combines id, name, type, and config."""
        step_config = StepConfig(
            step_id="step-1",
            name="First step",
            step_type=StepType.AGENT_TASK,
        )
        step_def = StepDefinition(
            id="step-1",
            name="First step",
            type=StepType.AGENT_TASK,
            config=step_config,
        )
        assert step_def.id == "step-1"
        assert step_def.name == "First step"
        assert step_def.type == StepType.AGENT_TASK
        assert step_def.config is step_config

    def test_config_reference(self):
        """StepDefinition config should reference the original StepConfig."""
        step_config = StepConfig(step_id="s1", name="S1", step_type=StepType.VALIDATION)
        step_def = StepDefinition(
            id="s1",
            name="S1",
            type=StepType.VALIDATION,
            config=step_config,
        )
        assert step_def.config is step_config
        assert step_def.config.step_id == "s1"
        assert step_def.config.step_type == StepType.VALIDATION

    def test_id_and_name_match_config(self):
        """StepDefinition id and name can differ from config step_id and name."""
        step_config = StepConfig(step_id="s1", name="Step One", step_type=StepType.VALIDATION)
        step_def = StepDefinition(
            id="step-1",
            name="Validation Step",
            type=StepType.VALIDATION,
            config=step_config,
        )
        assert step_def.id == "step-1"
        assert step_def.name == "Validation Step"
        assert step_def.config.step_id == "s1"
        assert step_def.config.name == "Step One"


# ---------------------------------------------------------------------------
# PipelineDefinition
# ---------------------------------------------------------------------------


class TestPipelineDefinition:
    """Tests for the PipelineDefinition model."""

    def test_creation(self):
        """PipelineDefinition combines config and step definitions."""
        step_config = StepConfig(step_id="s1", name="S1", step_type=StepType.AGENT_TASK)
        pipeline_config = PipelineConfig(
            pipeline_id="pipe-1",
            name="Test",
            pipeline_type=PipelineType.CUSTOM,
            project_id="proj-1",
            steps=[step_config],
        )
        step_def = StepDefinition(
            id="s1",
            name="S1",
            type=StepType.AGENT_TASK,
            config=step_config,
        )
        pipe_def = PipelineDefinition(
            id="pipe-1",
            name="Test Pipeline",
            type=PipelineType.CUSTOM,
            config=pipeline_config,
            steps=[step_def],
        )
        assert pipe_def.id == "pipe-1"
        assert pipe_def.name == "Test Pipeline"
        assert pipe_def.type == PipelineType.CUSTOM
        assert pipe_def.config is pipeline_config
        assert len(pipe_def.steps) == 1
        assert pipe_def.steps[0] is step_def

    def test_defaults(self):
        """PipelineDefinition steps defaults to empty list and description to empty string."""
        pipeline_config = PipelineConfig(
            pipeline_id="pipe-1",
            name="Test",
            pipeline_type=PipelineType.CUSTOM,
            project_id="proj-1",
        )
        pipe_def = PipelineDefinition(
            id="pipe-1",
            name="Test Pipeline",
            type=PipelineType.CUSTOM,
            config=pipeline_config,
        )
        assert pipe_def.steps == []
        assert pipe_def.description == ""

    def test_steps_is_independent(self):
        """Each PipelineDefinition should have its own steps list."""
        pipeline_config = PipelineConfig(
            pipeline_id="pipe-1",
            name="Test",
            pipeline_type=PipelineType.CUSTOM,
            project_id="proj-1",
        )
        pipe_def1 = PipelineDefinition(
            id="pipe-1",
            name="P1",
            type=PipelineType.CUSTOM,
            config=pipeline_config,
        )
        pipe_def2 = PipelineDefinition(
            id="pipe-2",
            name="P2",
            type=PipelineType.CUSTOM,
            config=pipeline_config,
        )
        step_config = StepConfig(step_id="s1", name="S1", step_type=StepType.AGENT_TASK)
        step_def = StepDefinition(id="s1", name="S1", type=StepType.AGENT_TASK, config=step_config)
        pipe_def1.steps.append(step_def)
        assert pipe_def2.steps == []

    def test_multiple_pipeline_types(self):
        """PipelineDefinition should work with all PipelineType values."""
        for pt in PipelineType:
            pipeline_config = PipelineConfig(
                pipeline_id=f"pipe-{pt.value}",
                name=f"Pipeline {pt.value}",
                pipeline_type=pt,
                project_id="proj-1",
            )
            pipe_def = PipelineDefinition(
                id=f"pipe-{pt.value}",
                name=f"Pipeline {pt.value}",
                type=pt,
                config=pipeline_config,
            )
            assert pipe_def.type == pt

    def test_multiple_step_types(self):
        """StepDefinition should work with all StepType values."""
        for st in StepType:
            step_config = StepConfig(
                step_id=f"step-{st.value}",
                name=f"Step {st.value}",
                step_type=st,
            )
            step_def = StepDefinition(
                id=f"step-{st.value}",
                name=f"Step {st.value}",
                type=st,
                config=step_config,
            )
            assert step_def.type == st
