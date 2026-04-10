"""Tests for palace.core.costs — Cost tracking and budgeting.

Covers CostTier, ModelPricing, UsageRecord, CostBudget, and CostTracker.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from palace.core.costs import (
    CostBudget,
    CostTier,
    CostTracker,
    ModelPricing,
    UsageRecord,
)

# ---------------------------------------------------------------------------
# CostTier enum
# ---------------------------------------------------------------------------


class TestCostTier:
    """Tests for the CostTier enum."""

    def test_has_five_values(self):
        """CostTier should define exactly 5 members."""
        assert len(CostTier) == 5

    def test_free(self):
        assert CostTier.FREE.value == "free"

    def test_low(self):
        assert CostTier.LOW.value == "low"

    def test_medium(self):
        assert CostTier.MEDIUM.value == "medium"

    def test_high(self):
        assert CostTier.HIGH.value == "high"

    def test_premium(self):
        assert CostTier.PREMIUM.value == "premium"

    def test_all_values(self):
        values = {m.value for m in CostTier}
        assert values == {"free", "low", "medium", "high", "premium"}

    def test_is_enum(self):
        """CostTier members should be Enum members with string values."""
        for member in CostTier:
            assert isinstance(member.value, str)
            assert isinstance(member, CostTier)

    def test_tier_members_are_distinct(self):
        """Cost tier members should be distinct."""
        assert CostTier.FREE != CostTier.LOW
        assert CostTier.LOW != CostTier.MEDIUM
        assert CostTier.MEDIUM != CostTier.HIGH
        assert CostTier.HIGH != CostTier.PREMIUM


# ---------------------------------------------------------------------------
# ModelPricing dataclass
# ---------------------------------------------------------------------------


class TestModelPricing:
    """Tests for the ModelPricing dataclass."""

    def test_creation_with_required_fields(self):
        """ModelPricing requires model_name."""
        pricing = ModelPricing(model_name="gpt-4")
        assert pricing.model_name == "gpt-4"

    def test_defaults(self):
        """ModelPricing should provide sensible defaults."""
        pricing = ModelPricing(model_name="test-model")
        assert pricing.input_cost_per_1k == 0.0
        assert pricing.output_cost_per_1k == 0.0
        assert pricing.tier == CostTier.FREE
        assert pricing.currency == "USD"

    def test_all_fields(self):
        """ModelPricing should accept all fields."""
        pricing = ModelPricing(
            model_name="gpt-4",
            input_cost_per_1k=0.03,
            output_cost_per_1k=0.06,
            tier=CostTier.HIGH,
            currency="EUR",
        )
        assert pricing.model_name == "gpt-4"
        assert pricing.input_cost_per_1k == 0.03
        assert pricing.output_cost_per_1k == 0.06
        assert pricing.tier == CostTier.HIGH
        assert pricing.currency == "EUR"

    def test_different_tiers(self):
        """ModelPricing should accept different cost tiers."""
        for tier in CostTier:
            pricing = ModelPricing(model_name=f"model-{tier.value}", tier=tier)
            assert pricing.tier == tier

    def test_zero_cost_model(self):
        """ModelPricing can represent a free model."""
        pricing = ModelPricing(
            model_name="local-llama",
            input_cost_per_1k=0.0,
            output_cost_per_1k=0.0,
            tier=CostTier.FREE,
        )
        assert pricing.input_cost_per_1k == 0.0
        assert pricing.output_cost_per_1k == 0.0
        assert pricing.tier == CostTier.FREE

    def test_high_cost_model(self):
        """ModelPricing can represent an expensive model."""
        pricing = ModelPricing(
            model_name="gpt-4-turbo",
            input_cost_per_1k=0.01,
            output_cost_per_1k=0.03,
            tier=CostTier.MEDIUM,
        )
        assert pricing.input_cost_per_1k == 0.01
        assert pricing.output_cost_per_1k == 0.03

    def test_negative_cost_allowed(self):
        """ModelPricing should allow negative costs (though unusual)."""
        pricing = ModelPricing(
            model_name="test-model",
            input_cost_per_1k=-0.01,
            output_cost_per_1k=-0.02,
        )
        assert pricing.input_cost_per_1k == -0.01
        assert pricing.output_cost_per_1k == -0.02


# ---------------------------------------------------------------------------
# UsageRecord dataclass
# ---------------------------------------------------------------------------


class TestUsageRecord:
    """Tests for the UsageRecord dataclass."""

    def test_creation_with_defaults(self):
        """UsageRecord should be creatable with defaults only."""
        record = UsageRecord()
        assert record.record_id  # Should have a generated UUID
        assert record.model_name == ""
        assert record.project_id == ""
        assert record.agent_role == ""
        assert record.session_id == ""
        assert record.input_tokens == 0
        assert record.output_tokens == 0
        assert record.total_tokens == 0
        assert record.estimated_cost == 0.0
        assert record.task_description == ""

    def test_creation_with_all_fields(self):
        """UsageRecord should accept all fields."""
        now = datetime.utcnow()
        record = UsageRecord(
            record_id="rec-123",
            model_name="gpt-4",
            project_id="proj-1",
            agent_role="backend",
            session_id="sess-456",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            estimated_cost=0.005,
            timestamp=now,
            task_description="Implement login",
        )
        assert record.record_id == "rec-123"
        assert record.model_name == "gpt-4"
        assert record.project_id == "proj-1"
        assert record.agent_role == "backend"
        assert record.session_id == "sess-456"
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.total_tokens == 150
        assert record.estimated_cost == 0.005
        assert record.timestamp == now
        assert record.task_description == "Implement login"

    def test_auto_generated_record_id(self):
        """UsageRecord should auto-generate a unique record_id."""
        record1 = UsageRecord()
        record2 = UsageRecord()
        assert record1.record_id != record2.record_id

    def test_auto_generated_timestamp(self):
        """UsageRecord should auto-generate a timestamp."""
        before = datetime.utcnow()
        record = UsageRecord()
        after = datetime.utcnow()
        assert before <= record.timestamp <= after

    def test_custom_record_id(self):
        """UsageRecord should accept a custom record_id."""
        record = UsageRecord(record_id="my-custom-id")
        assert record.record_id == "my-custom-id"

    def test_custom_timestamp(self):
        """UsageRecord should accept a custom timestamp."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        record = UsageRecord(timestamp=custom_time)
        assert record.timestamp == custom_time

    def test_total_tokens_set_manually(self):
        """UsageRecord total_tokens should be settable independently."""
        record = UsageRecord(input_tokens=100, output_tokens=50, total_tokens=150)
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.total_tokens == 150

    def test_total_tokens_can_differ_from_sum(self):
        """UsageRecord total_tokens can be different from input + output."""
        record = UsageRecord(input_tokens=100, output_tokens=50, total_tokens=200)
        assert record.total_tokens == 200


# ---------------------------------------------------------------------------
# CostBudget dataclass
# ---------------------------------------------------------------------------


class TestCostBudget:
    """Tests for the CostBudget dataclass."""

    def test_creation_with_required_fields(self):
        """CostBudget requires project_id."""
        budget = CostBudget(project_id="proj-1")
        assert budget.project_id == "proj-1"

    def test_defaults(self):
        """CostBudget should provide sensible defaults."""
        budget = CostBudget(project_id="proj-1")
        assert budget.daily_limit == 10.0
        assert budget.monthly_limit == 100.0
        assert budget.per_task_limit == 1.0
        assert budget.alert_threshold == 0.8
        assert budget.current_daily_spend == 0.0
        assert budget.current_monthly_spend == 0.0

    def test_all_fields(self):
        """CostBudget should accept all fields."""
        budget = CostBudget(
            project_id="proj-2",
            daily_limit=50.0,
            monthly_limit=500.0,
            per_task_limit=5.0,
            alert_threshold=0.9,
            current_daily_spend=10.0,
            current_monthly_spend=80.0,
        )
        assert budget.project_id == "proj-2"
        assert budget.daily_limit == 50.0
        assert budget.monthly_limit == 500.0
        assert budget.per_task_limit == 5.0
        assert budget.alert_threshold == 0.9
        assert budget.current_daily_spend == 10.0
        assert budget.current_monthly_spend == 80.0

    def test_is_within_budget_true(self):
        """is_within_budget should return True when spend is within limits."""
        budget = CostBudget(
            project_id="proj-1",
            daily_limit=10.0,
            monthly_limit=100.0,
            current_daily_spend=5.0,
            current_monthly_spend=50.0,
        )
        assert budget.is_within_budget(3.0) is True

    def test_is_within_budget_exactly_at_daily_limit(self):
        """is_within_budget should return True when spend exactly hits daily limit."""
        budget = CostBudget(
            project_id="proj-1",
            daily_limit=10.0,
            monthly_limit=100.0,
            current_daily_spend=7.0,
            current_monthly_spend=0.0,
        )
        assert budget.is_within_budget(3.0) is True

    def test_is_within_budget_false_daily_exceeded(self):
        """is_within_budget should return False when daily limit exceeded."""
        budget = CostBudget(
            project_id="proj-1",
            daily_limit=10.0,
            monthly_limit=100.0,
            current_daily_spend=8.0,
            current_monthly_spend=0.0,
        )
        assert budget.is_within_budget(3.0) is False

    def test_is_within_budget_false_monthly_exceeded(self):
        """is_within_budget should return False when monthly limit exceeded."""
        budget = CostBudget(
            project_id="proj-1",
            daily_limit=100.0,
            monthly_limit=100.0,
            current_daily_spend=0.0,
            current_monthly_spend=98.0,
        )
        assert budget.is_within_budget(3.0) is False

    def test_is_within_budget_zero_spend(self):
        """is_within_budget with zero spend should allow any amount within limits."""
        budget = CostBudget(project_id="proj-1", daily_limit=10.0, monthly_limit=100.0)
        assert budget.is_within_budget(10.0) is True
        assert budget.is_within_budget(10.01) is False

    def test_is_task_within_budget_true(self):
        """is_task_within_budget should return True when amount is under per-task limit."""
        budget = CostBudget(project_id="proj-1", per_task_limit=1.0)
        assert budget.is_task_within_budget(0.5) is True
        assert budget.is_task_within_budget(1.0) is True

    def test_is_task_within_budget_false(self):
        """is_task_within_budget should return False when amount exceeds per-task limit."""
        budget = CostBudget(project_id="proj-1", per_task_limit=1.0)
        assert budget.is_task_within_budget(1.01) is False
        assert budget.is_task_within_budget(5.0) is False

    def test_should_alert_below_threshold(self):
        """should_alert should return False when spending is below threshold."""
        budget = CostBudget(
            project_id="proj-1",
            daily_limit=100.0,
            monthly_limit=1000.0,
            alert_threshold=0.8,
            current_daily_spend=50.0,
            current_monthly_spend=500.0,
        )
        assert budget.should_alert() is False

    def test_should_alert_at_daily_threshold(self):
        """should_alert should return True when daily spend reaches threshold."""
        budget = CostBudget(
            project_id="proj-1",
            daily_limit=100.0,
            monthly_limit=1000.0,
            alert_threshold=0.8,
            current_daily_spend=80.0,
            current_monthly_spend=0.0,
        )
        assert budget.should_alert() is True

    def test_should_alert_at_monthly_threshold(self):
        """should_alert should return True when monthly spend reaches threshold."""
        budget = CostBudget(
            project_id="proj-1",
            daily_limit=100.0,
            monthly_limit=1000.0,
            alert_threshold=0.8,
            current_daily_spend=0.0,
            current_monthly_spend=800.0,
        )
        assert budget.should_alert() is True

    def test_should_alert_above_threshold(self):
        """should_alert should return True when spending exceeds threshold."""
        budget = CostBudget(
            project_id="proj-1",
            daily_limit=100.0,
            monthly_limit=1000.0,
            alert_threshold=0.8,
            current_daily_spend=90.0,
            current_monthly_spend=900.0,
        )
        assert budget.should_alert() is True

    def test_should_alert_zero_limits(self):
        """should_alert with zero limits should return False (avoid division by zero)."""
        budget = CostBudget(
            project_id="proj-1",
            daily_limit=0.0,
            monthly_limit=0.0,
            alert_threshold=0.8,
            current_daily_spend=0.0,
            current_monthly_spend=0.0,
        )
        assert budget.should_alert() is False

    def test_add_spend(self):
        """add_spend should update daily and monthly spend."""
        budget = CostBudget(project_id="proj-1")
        assert budget.current_daily_spend == 0.0
        assert budget.current_monthly_spend == 0.0

        budget.add_spend(5.0)
        assert budget.current_daily_spend == 5.0
        assert budget.current_monthly_spend == 5.0

        budget.add_spend(3.0)
        assert budget.current_daily_spend == 8.0
        assert budget.current_monthly_spend == 8.0

    def test_add_spend_multiple_times(self):
        """add_spend should accumulate correctly over multiple calls."""
        budget = CostBudget(project_id="proj-1")
        for amount in [1.0, 2.0, 3.0]:
            budget.add_spend(amount)
        assert budget.current_daily_spend == 6.0
        assert budget.current_monthly_spend == 6.0

    def test_add_spend_zero(self):
        """add_spend with zero should not change spend."""
        budget = CostBudget(project_id="proj-1", current_daily_spend=5.0, current_monthly_spend=5.0)
        budget.add_spend(0.0)
        assert budget.current_daily_spend == 5.0
        assert budget.current_monthly_spend == 5.0

    def test_reset_daily(self):
        """reset_daily should reset daily spend to zero."""
        budget = CostBudget(
            project_id="proj-1",
            current_daily_spend=50.0,
            current_monthly_spend=500.0,
        )
        budget.reset_daily()
        assert budget.current_daily_spend == 0.0
        assert budget.current_monthly_spend == 500.0

    def test_reset_monthly(self):
        """reset_monthly should reset monthly spend to zero."""
        budget = CostBudget(
            project_id="proj-1",
            current_daily_spend=50.0,
            current_monthly_spend=500.0,
        )
        budget.reset_monthly()
        assert budget.current_daily_spend == 50.0
        assert budget.current_monthly_spend == 0.0

    def test_reset_daily_and_monthly(self):
        """Resetting both daily and monthly should zero both."""
        budget = CostBudget(
            project_id="proj-1",
            current_daily_spend=50.0,
            current_monthly_spend=500.0,
        )
        budget.reset_daily()
        budget.reset_monthly()
        assert budget.current_daily_spend == 0.0
        assert budget.current_monthly_spend == 0.0

    def test_budget_enforcement_flow(self):
        """Test a typical budget enforcement flow."""
        budget = CostBudget(
            project_id="proj-1",
            daily_limit=10.0,
            monthly_limit=100.0,
            per_task_limit=2.0,
        )
        # Initial: everything is within budget
        assert budget.is_within_budget(5.0) is True
        assert budget.is_task_within_budget(1.5) is True

        # Add some spend
        budget.add_spend(8.0)
        assert budget.is_within_budget(2.0) is True  # 8 + 2 = 10, exactly at daily limit
        assert budget.is_within_budget(2.01) is False  # Over daily limit

        # Per-task check
        assert budget.is_task_within_budget(2.0) is True
        assert budget.is_task_within_budget(2.01) is False


# ---------------------------------------------------------------------------
# CostTracker
# ---------------------------------------------------------------------------


class TestCostTracker:
    """Tests for the CostTracker class."""

    def test_initialization_default(self):
        """CostTracker should initialize with default pricing."""
        tracker = CostTracker()
        assert len(tracker._usage_records) == 0
        assert len(tracker._budgets) == 0
        assert len(tracker._pricing) > 0

    def test_initialization_default_pricing_models(self):
        """CostTracker should have default model pricing for known models."""
        tracker = CostTracker()
        assert "qwen3.5" in tracker._pricing
        assert "qwen3-coder-next" in tracker._pricing
        assert "deepseek-v3.2" in tracker._pricing
        assert "mistral-large" in tracker._pricing
        assert "gemma4:31b" in tracker._pricing

    def test_initialization_with_custom_pricing(self):
        """CostTracker should accept custom pricing overrides."""
        custom_pricing = {
            "my-model": ModelPricing(
                model_name="my-model",
                input_cost_per_1k=0.05,
                output_cost_per_1k=0.10,
                tier=CostTier.HIGH,
            ),
        }
        tracker = CostTracker(default_pricing=custom_pricing)
        assert "my-model" in tracker._pricing
        assert tracker._pricing["my-model"].input_cost_per_1k == 0.05

    def test_initialization_custom_pricing_merges_with_defaults(self):
        """Custom pricing should merge with, not replace, default pricing."""
        custom_pricing = {
            "my-model": ModelPricing(model_name="my-model", tier=CostTier.LOW),
        }
        tracker = CostTracker(default_pricing=custom_pricing)
        assert "my-model" in tracker._pricing
        assert "qwen3.5" in tracker._pricing  # Default still present

    def test_initialization_custom_pricing_overrides_default(self):
        """Custom pricing should override default pricing for same model."""
        custom_pricing = {
            "qwen3.5": ModelPricing(
                model_name="qwen3.5",
                input_cost_per_1k=0.99,
                output_cost_per_1k=0.99,
                tier=CostTier.PREMIUM,
            ),
        }
        tracker = CostTracker(default_pricing=custom_pricing)
        assert tracker._pricing["qwen3.5"].input_cost_per_1k == 0.99

    def test_estimate_cost_known_model(self):
        """estimate_cost should calculate cost for a known model."""
        tracker = CostTracker()
        # qwen3.5: input_cost_per_1k=0.0001, output_cost_per_1k=0.0002
        cost = tracker.estimate_cost("qwen3.5", 1000, 1000)
        assert cost == pytest.approx(0.0001 + 0.0002, abs=1e-10)

    def test_estimate_cost_unknown_model(self):
        """estimate_cost should return 0 for an unknown model."""
        tracker = CostTracker()
        cost = tracker.estimate_cost("unknown-model", 1000, 1000)
        assert cost == 0.0

    def test_estimate_cost_zero_tokens(self):
        """estimate_cost should return 0 for zero tokens."""
        tracker = CostTracker()
        cost = tracker.estimate_cost("qwen3.5", 0, 0)
        assert cost == 0.0

    def test_estimate_cost_partial_tokens(self):
        """estimate_cost should handle partial 1K tokens correctly."""
        tracker = CostTracker()
        # qwen3.5: input=0.0001/1k, output=0.0002/1k
        # 500 input tokens = 0.0001 * (500/1000) = 0.00005
        # 250 output tokens = 0.0002 * (250/1000) = 0.00005
        cost = tracker.estimate_cost("qwen3.5", 500, 250)
        assert cost == pytest.approx(0.0001, abs=1e-10)

    def test_record_usage(self):
        """record_usage should create and store a UsageRecord."""
        tracker = CostTracker()
        record = tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=100,
            output_tokens=50,
            project_id="proj-1",
            agent_role="backend",
            session_id="sess-1",
            task_description="Test task",
        )
        assert record.model_name == "qwen3.5"
        assert record.input_tokens == 100
        assert record.output_tokens == 50
        assert record.total_tokens == 150
        assert record.project_id == "proj-1"
        assert record.agent_role == "backend"
        assert record.session_id == "sess-1"
        assert record.task_description == "Test task"
        assert record.estimated_cost > 0

    def test_record_usage_stored_in_records(self):
        """record_usage should store the record in the tracker."""
        tracker = CostTracker()
        tracker.record_usage(model_name="qwen3.5", input_tokens=100, output_tokens=50)
        assert len(tracker._usage_records) == 1

    def test_record_usage_multiple(self):
        """Multiple record_usage calls should accumulate records."""
        tracker = CostTracker()
        for i in range(5):
            tracker.record_usage(
                model_name="qwen3.5",
                input_tokens=100,
                output_tokens=50,
            )
        assert len(tracker._usage_records) == 5

    def test_record_usage_with_budget(self):
        """record_usage should update budget spend when a budget exists."""
        tracker = CostTracker()
        tracker.set_budget("proj-1", daily_limit=100.0, monthly_limit=1000.0, per_task_limit=10.0)

        tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=1000,
            output_tokens=500,
            project_id="proj-1",
        )

        spend = tracker.get_project_spend("proj-1")
        assert spend["daily"] > 0
        assert spend["monthly"] > 0
        assert spend["total"] > 0

    def test_record_usage_without_project_id(self):
        """record_usage without project_id should not require a budget."""
        tracker = CostTracker()
        record = tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=100,
            output_tokens=50,
        )
        assert record.project_id == ""
        assert record.estimated_cost >= 0

    def test_check_budget_no_budget(self):
        """check_budget should return True when no budget is set."""
        tracker = CostTracker()
        assert tracker.check_budget("proj-no-budget", 1.0) is True

    def test_check_budget_within_budget(self):
        """check_budget should return True when spend is within budget."""
        tracker = CostTracker()
        tracker.set_budget("proj-1", daily_limit=100.0, monthly_limit=1000.0)
        assert tracker.check_budget("proj-1", 10.0) is True

    def test_check_budget_over_daily_limit(self):
        """check_budget should return False when daily limit is exceeded."""
        tracker = CostTracker()
        tracker.set_budget("proj-1", daily_limit=5.0, monthly_limit=1000.0)
        # Spend to near the daily limit
        tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=50000,  # 50 * 0.0001 = 0.005
            output_tokens=25000,
            project_id="proj-1",
        )
        # Check with an amount that would exceed the budget
        assert tracker.check_budget("proj-1", 100.0) is False

    def test_check_budget_over_monthly_limit(self):
        """check_budget should return False when monthly limit is exceeded."""
        tracker = CostTracker()
        tracker.set_budget("proj-1", daily_limit=1000.0, monthly_limit=5.0)
        tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=50000,
            output_tokens=25000,
            project_id="proj-1",
        )
        assert tracker.check_budget("proj-1", 100.0) is False

    def test_set_budget(self):
        """set_budget should create a budget for a project."""
        tracker = CostTracker()
        tracker.set_budget("proj-1", daily_limit=50.0, monthly_limit=500.0, per_task_limit=2.0)

        budget = tracker._budgets["proj-1"]
        assert budget.project_id == "proj-1"
        assert budget.daily_limit == 50.0
        assert budget.monthly_limit == 500.0
        assert budget.per_task_limit == 2.0

    def test_set_budget_update_existing(self):
        """set_budget should update an existing budget."""
        tracker = CostTracker()
        tracker.set_budget("proj-1", daily_limit=50.0, monthly_limit=500.0, per_task_limit=2.0)
        tracker.set_budget("proj-1", daily_limit=100.0, monthly_limit=1000.0, per_task_limit=5.0)

        budget = tracker._budgets["proj-1"]
        assert budget.daily_limit == 100.0
        assert budget.monthly_limit == 1000.0
        assert budget.per_task_limit == 5.0

    def test_set_budget_default_values(self):
        """set_budget should use default values when not specified."""
        tracker = CostTracker()
        tracker.set_budget("proj-1")

        budget = tracker._budgets["proj-1"]
        assert budget.daily_limit == 10.0
        assert budget.monthly_limit == 100.0
        assert budget.per_task_limit == 1.0

    def test_get_usage_report_empty(self):
        """get_usage_report should return empty report when no records exist."""
        tracker = CostTracker()
        report = tracker.get_usage_report()
        assert report["total_records"] == 0
        assert report["total_tokens"] == 0
        assert report["total_cost"] == 0.0
        assert report["by_model"] == {}
        assert report["by_agent"] == {}
        assert report["by_project"] == {}

    def test_get_usage_report_with_records(self):
        """get_usage_report should aggregate usage records correctly."""
        tracker = CostTracker()
        tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=1000,
            output_tokens=500,
            project_id="proj-1",
            agent_role="backend",
        )
        tracker.record_usage(
            model_name="qwen3-coder-next",
            input_tokens=2000,
            output_tokens=1000,
            project_id="proj-1",
            agent_role="frontend",
        )

        report = tracker.get_usage_report()
        assert report["total_records"] == 2
        assert report["total_tokens"] == 4500
        assert report["total_cost"] > 0
        assert "qwen3.5" in report["by_model"]
        assert "qwen3-coder-next" in report["by_model"]
        assert "backend" in report["by_agent"]
        assert "frontend" in report["by_agent"]
        assert "proj-1" in report["by_project"]

    def test_get_usage_report_filter_by_project(self):
        """get_usage_report should filter by project_id."""
        tracker = CostTracker()
        tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=100,
            output_tokens=50,
            project_id="proj-1",
        )
        tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=200,
            output_tokens=100,
            project_id="proj-2",
        )

        report = tracker.get_usage_report(project_id="proj-1")
        assert report["total_records"] == 1
        assert "proj-1" in report["by_project"]

    def test_get_usage_report_filter_by_model(self):
        """get_usage_report should filter by model_name."""
        tracker = CostTracker()
        tracker.record_usage(model_name="qwen3.5", input_tokens=100, output_tokens=50)
        tracker.record_usage(model_name="qwen3-coder-next", input_tokens=200, output_tokens=100)

        report = tracker.get_usage_report(model_name="qwen3.5")
        assert report["total_records"] == 1
        assert "qwen3.5" in report["by_model"]

    def test_get_usage_report_filter_by_agent(self):
        """get_usage_report should filter by agent_role."""
        tracker = CostTracker()
        tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=100,
            output_tokens=50,
            agent_role="backend",
        )
        tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=100,
            output_tokens=50,
            agent_role="frontend",
        )

        report = tracker.get_usage_report(agent_role="backend")
        assert report["total_records"] == 1
        assert "backend" in report["by_agent"]

    def test_get_usage_report_filter_by_date(self):
        """get_usage_report should filter by date range."""
        tracker = CostTracker()
        tracker.record_usage(model_name="qwen3.5", input_tokens=100, output_tokens=50)

        # Filter by date range - all records should be included
        now = datetime.utcnow()
        report = tracker.get_usage_report(
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=1),
        )
        assert report["total_records"] == 1

        # Filter by date range that excludes all records
        report = tracker.get_usage_report(
            start_date=now + timedelta(days=1),
            end_date=now + timedelta(days=2),
        )
        assert report["total_records"] == 0

    def test_get_usage_report_combined_filters(self):
        """get_usage_report should apply multiple filters simultaneously."""
        tracker = CostTracker()
        tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=100,
            output_tokens=50,
            project_id="proj-1",
            agent_role="backend",
        )
        tracker.record_usage(
            model_name="qwen3-coder-next",
            input_tokens=200,
            output_tokens=100,
            project_id="proj-2",
            agent_role="frontend",
        )

        report = tracker.get_usage_report(project_id="proj-1", model_name="qwen3.5")
        assert report["total_records"] == 1

    def test_get_usage_report_by_model_aggregation(self):
        """get_usage_report should correctly aggregate by model."""
        tracker = CostTracker()
        tracker.record_usage(model_name="qwen3.5", input_tokens=1000, output_tokens=500)
        tracker.record_usage(model_name="qwen3.5", input_tokens=2000, output_tokens=1000)

        report = tracker.get_usage_report()
        model_stats = report["by_model"]["qwen3.5"]
        assert model_stats["tokens"] == 4500
        assert model_stats["count"] == 2
        assert model_stats["cost"] > 0

    def test_get_usage_report_by_agent_aggregation(self):
        """get_usage_report should correctly aggregate by agent."""
        tracker = CostTracker()
        tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=100,
            output_tokens=50,
            agent_role="backend",
        )
        tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=200,
            output_tokens=100,
            agent_role="backend",
        )

        report = tracker.get_usage_report()
        agent_stats = report["by_agent"]["backend"]
        assert agent_stats["tokens"] == 450
        assert agent_stats["count"] == 2

    def test_get_usage_report_unassigned_agent(self):
        """get_usage_report should group records without agent_role as 'unassigned'."""
        tracker = CostTracker()
        tracker.record_usage(model_name="qwen3.5", input_tokens=100, output_tokens=50)

        report = tracker.get_usage_report()
        assert "unassigned" in report["by_agent"]

    def test_get_usage_report_unassigned_project(self):
        """get_usage_report should group records without project_id as 'unassigned'."""
        tracker = CostTracker()
        tracker.record_usage(model_name="qwen3.5", input_tokens=100, output_tokens=50)

        report = tracker.get_usage_report()
        assert "unassigned" in report["by_project"]

    def test_get_project_spend_with_budget(self):
        """get_project_spend should return spend data for a project with a budget."""
        tracker = CostTracker()
        tracker.set_budget("proj-1", daily_limit=100.0, monthly_limit=1000.0)
        tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=10000,
            output_tokens=5000,
            project_id="proj-1",
        )

        spend = tracker.get_project_spend("proj-1")
        assert spend["daily"] > 0
        assert spend["monthly"] > 0
        assert spend["total"] > 0

    def test_get_project_spend_without_budget(self):
        """get_project_spend should return zeros for projects without a budget."""
        tracker = CostTracker()
        tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=100,
            output_tokens=50,
            project_id="proj-no-budget",
        )

        spend = tracker.get_project_spend("proj-no-budget")
        assert spend["daily"] == 0.0
        assert spend["monthly"] == 0.0
        assert spend["total"] > 0

    def test_get_project_spend_nonexistent_project(self):
        """get_project_spend should return zeros for nonexistent projects."""
        tracker = CostTracker()
        spend = tracker.get_project_spend("nonexistent")
        assert spend["daily"] == 0.0
        assert spend["monthly"] == 0.0
        assert spend["total"] == 0.0

    def test_add_model_pricing(self):
        """add_model_pricing should add pricing for a new model."""
        tracker = CostTracker()
        tracker.add_model_pricing(
            model_name="new-model",
            input_cost_per_1k=0.05,
            output_cost_per_1k=0.10,
            tier=CostTier.HIGH,
        )

        assert "new-model" in tracker._pricing
        assert tracker._pricing["new-model"].input_cost_per_1k == 0.05
        assert tracker._pricing["new-model"].output_cost_per_1k == 0.10
        assert tracker._pricing["new-model"].tier == CostTier.HIGH

    def test_add_model_pricing_overrides_default(self):
        """add_model_pricing should override pricing for an existing model."""
        tracker = CostTracker()
        tracker.add_model_pricing(
            model_name="qwen3.5",
            input_cost_per_1k=0.99,
            output_cost_per_1k=0.99,
            tier=CostTier.PREMIUM,
        )

        assert tracker._pricing["qwen3.5"].input_cost_per_1k == 0.99
        assert tracker._pricing["qwen3.5"].output_cost_per_1k == 0.99
        assert tracker._pricing["qwen3.5"].tier == CostTier.PREMIUM

    def test_add_model_pricing_default_tier(self):
        """add_model_pricing should default to LOW tier."""
        tracker = CostTracker()
        tracker.add_model_pricing(
            model_name="new-model",
            input_cost_per_1k=0.001,
            output_cost_per_1k=0.002,
        )

        assert tracker._pricing["new-model"].tier == CostTier.LOW

    def test_estimate_cost_after_add_pricing(self):
        """estimate_cost should use newly added pricing."""
        tracker = CostTracker()
        tracker.add_model_pricing(
            model_name="new-model",
            input_cost_per_1k=0.05,
            output_cost_per_1k=0.10,
        )

        cost = tracker.estimate_cost("new-model", 1000, 1000)
        assert cost == pytest.approx(0.05 + 0.10, abs=1e-10)

    def test_reset_daily_budgets(self):
        """reset_daily_budgets should reset daily spend for all budgets."""
        tracker = CostTracker()
        tracker.set_budget("proj-1", daily_limit=100.0, monthly_limit=1000.0)
        tracker.set_budget("proj-2", daily_limit=50.0, monthly_limit=500.0)

        # Add some spend
        tracker._budgets["proj-1"].add_spend(25.0)
        tracker._budgets["proj-2"].add_spend(10.0)

        tracker.reset_daily_budgets()

        assert tracker._budgets["proj-1"].current_daily_spend == 0.0
        assert tracker._budgets["proj-2"].current_daily_spend == 0.0
        # Monthly spend should NOT be reset
        assert tracker._budgets["proj-1"].current_monthly_spend == 25.0
        assert tracker._budgets["proj-2"].current_monthly_spend == 10.0

    def test_reset_monthly_budgets(self):
        """reset_monthly_budgets should reset monthly spend for all budgets."""
        tracker = CostTracker()
        tracker.set_budget("proj-1", daily_limit=100.0, monthly_limit=1000.0)
        tracker.set_budget("proj-2", daily_limit=50.0, monthly_limit=500.0)

        tracker._budgets["proj-1"].add_spend(25.0)
        tracker._budgets["proj-2"].add_spend(10.0)

        tracker.reset_monthly_budgets()

        assert tracker._budgets["proj-1"].current_monthly_spend == 0.0
        assert tracker._budgets["proj-2"].current_monthly_spend == 0.0
        # Daily spend should NOT be reset
        assert tracker._budgets["proj-1"].current_daily_spend == 25.0
        assert tracker._budgets["proj-2"].current_daily_spend == 10.0

    def test_reset_daily_budgets_empty(self):
        """reset_daily_budgets should work with no budgets."""
        tracker = CostTracker()
        tracker.reset_daily_budgets()  # Should not raise

    def test_reset_monthly_budgets_empty(self):
        """reset_monthly_budgets should work with no budgets."""
        tracker = CostTracker()
        tracker.reset_monthly_budgets()  # Should not raise

    def test_get_budget_status_no_budget(self):
        """get_budget_status should return None when no budget is set."""
        tracker = CostTracker()
        status = tracker.get_budget_status("proj-no-budget")
        assert status is None

    def test_get_budget_status_with_budget(self):
        """get_budget_status should return detailed budget information."""
        tracker = CostTracker()
        tracker.set_budget("proj-1", daily_limit=100.0, monthly_limit=1000.0, per_task_limit=5.0)

        status = tracker.get_budget_status("proj-1")
        assert status is not None
        assert status["project_id"] == "proj-1"
        assert status["daily_limit"] == 100.0
        assert status["monthly_limit"] == 1000.0
        assert status["per_task_limit"] == 5.0
        assert status["daily_spend"] == 0.0
        assert status["monthly_spend"] == 0.0
        assert status["daily_remaining"] == 100.0
        assert status["monthly_remaining"] == 1000.0
        assert status["daily_usage_pct"] == 0.0
        assert status["monthly_usage_pct"] == 0.0
        assert status["alert_threshold"] == 0.8
        assert status["should_alert"] is False

    def test_get_budget_status_after_spend(self):
        """get_budget_status should reflect spending."""
        tracker = CostTracker()
        tracker.set_budget("proj-1", daily_limit=100.0, monthly_limit=1000.0)

        tracker._budgets["proj-1"].add_spend(50.0)

        status = tracker.get_budget_status("proj-1")
        assert status is not None
        assert status["daily_spend"] == 50.0
        assert status["monthly_spend"] == 50.0
        assert status["daily_remaining"] == 50.0
        assert status["monthly_remaining"] == 950.0
        assert status["daily_usage_pct"] == 50.0
        assert status["monthly_usage_pct"] == 5.0

    def test_get_budget_status_alert_threshold(self):
        """get_budget_status should detect when spending crosses alert threshold."""
        tracker = CostTracker()
        tracker.set_budget("proj-1", daily_limit=100.0, monthly_limit=100.0)

        tracker._budgets["proj-1"].add_spend(85.0)

        status = tracker.get_budget_status("proj-1")
        assert status["should_alert"] is True

    def test_get_budget_status_zero_limits(self):
        """get_budget_status with zero limits should avoid division by zero."""
        tracker = CostTracker()
        tracker.set_budget("proj-1", daily_limit=0.0, monthly_limit=0.0)

        status = tracker.get_budget_status("proj-1")
        assert status is not None
        assert status["daily_usage_pct"] == 0.0
        assert status["monthly_usage_pct"] == 0.0

    def test_get_model_recommendation_coding(self):
        """get_model_recommendation should recommend qwen3-coder-next for coding tasks."""
        tracker = CostTracker()
        recommendation = tracker.get_model_recommendation("coding")
        assert recommendation == "qwen3-coder-next"

    def test_get_model_recommendation_architecture(self):
        """get_model_recommendation should recommend mistral-large for architecture tasks."""
        tracker = CostTracker()
        recommendation = tracker.get_model_recommendation("architecture")
        assert recommendation == "mistral-large"

    def test_get_model_recommendation_database(self):
        """get_model_recommendation should recommend deepseek-v3.2 for database tasks."""
        tracker = CostTracker()
        recommendation = tracker.get_model_recommendation("database")
        assert recommendation == "deepseek-v3.2"

    def test_get_model_recommendation_unknown_task(self):
        """get_model_recommendation should default to qwen3.5 for unknown tasks."""
        tracker = CostTracker()
        recommendation = tracker.get_model_recommendation("unknown_task")
        assert recommendation == "qwen3.5"

    def test_get_model_recommendation_with_budget_constraint(self):
        """get_model_recommendation should fall back to cheaper models when budget is tight."""
        tracker = CostTracker()

        # With a budget constraint that the default coding model exceeds,
        # should fall back to a cheaper model that fits the budget.
        # qwen3-coder-next (default for "coding") has max_cost=0.0004
        # qwen3.5 and gemma4:31b have max_cost=0.0002, which fits 0.0003
        recommendation = tracker.get_model_recommendation("coding", budget_constraint=0.0003)
        assert recommendation is not None
        # The recommended model's max cost should be within the budget
        pricing = tracker._pricing[recommendation]
        max_cost = max(pricing.input_cost_per_1k, pricing.output_cost_per_1k)
        assert max_cost <= 0.0003

    def test_get_model_recommendation_with_generous_budget(self):
        """get_model_recommendation should recommend the task-specific model when budget allows."""
        tracker = CostTracker()
        recommendation = tracker.get_model_recommendation("coding", budget_constraint=1.0)
        assert recommendation == "qwen3-coder-next"

    def test_get_model_recommendation_no_budget_constraint(self):
        """get_model_recommendation without budget_constraint should use task default."""
        tracker = CostTracker()
        recommendation = tracker.get_model_recommendation("coding", budget_constraint=None)
        assert recommendation == "qwen3-coder-next"

    def test_cost_tracker_full_workflow(self):
        """Test a complete workflow: set budget, record usage, check budget, get report."""
        tracker = CostTracker()
        tracker.set_budget("proj-1", daily_limit=10.0, monthly_limit=100.0, per_task_limit=2.0)

        # Record some usage
        tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=1000,
            output_tokens=500,
            project_id="proj-1",
            agent_role="backend",
            task_description="Implement login",
        )

        # Check budget
        assert tracker.check_budget("proj-1", 5.0) is True

        # Get usage report
        report = tracker.get_usage_report(project_id="proj-1")
        assert report["total_records"] == 1
        assert report["total_tokens"] == 1500
        assert report["total_cost"] > 0

        # Get budget status
        status = tracker.get_budget_status("proj-1")
        assert status is not None
        assert status["daily_spend"] > 0
        assert status["should_alert"] is False

        # Get project spend
        spend = tracker.get_project_spend("proj-1")
        assert spend["daily"] > 0
        assert spend["monthly"] > 0

    def test_cost_tracker_multiple_projects(self):
        """CostTracker should handle multiple projects independently."""
        tracker = CostTracker()
        tracker.set_budget("proj-1", daily_limit=10.0, monthly_limit=100.0)
        tracker.set_budget("proj-2", daily_limit=20.0, monthly_limit=200.0)

        tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=1000,
            output_tokens=500,
            project_id="proj-1",
        )
        tracker.record_usage(
            model_name="qwen3.5",
            input_tokens=2000,
            output_tokens=1000,
            project_id="proj-2",
        )

        # Verify budgets are tracked separately
        spend_1 = tracker.get_project_spend("proj-1")
        spend_2 = tracker.get_project_spend("proj-2")

        assert spend_1["total"] != spend_2["total"]

        # Verify usage report aggregates across projects
        report = tracker.get_usage_report()
        assert report["total_records"] == 2

        # Verify per-project report
        report_proj1 = tracker.get_usage_report(project_id="proj-1")
        assert report_proj1["total_records"] == 1
