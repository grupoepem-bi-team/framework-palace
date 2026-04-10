"""Módulo de seguimiento de costos para el Palace Framework.

Registra y controla el uso de tokens y costos asociados
a las invocaciones de modelos LLM en el framework.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import structlog


class CostTier(Enum):
    """Cost tier classification for LLM models."""

    FREE = "free"  # Local models (no cost)
    LOW = "low"  # Low cost models (<$0.001/1K tokens)
    MEDIUM = "medium"  # Medium cost models (<$0.01/1K tokens)
    HIGH = "high"  # High cost models (<$0.1/1K tokens)
    PREMIUM = "premium"  # Premium models (>$0.1/1K tokens)


@dataclass
class ModelPricing:
    """Pricing information for an LLM model."""

    model_name: str
    input_cost_per_1k: float = 0.0  # Cost per 1K input tokens
    output_cost_per_1k: float = 0.0  # Cost per 1K output tokens
    tier: CostTier = CostTier.FREE
    currency: str = "USD"


@dataclass
class UsageRecord:
    """Record of a single LLM model usage event."""

    record_id: str = field(default_factory=lambda: str(uuid4()))
    model_name: str = ""
    project_id: str = ""
    agent_role: str = ""
    session_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    task_description: str = ""


@dataclass
class CostBudget:
    """Budget constraints for a project."""

    project_id: str
    daily_limit: float = 10.0  # Daily budget in USD
    monthly_limit: float = 100.0  # Monthly budget in USD
    per_task_limit: float = 1.0  # Per-task budget in USD
    alert_threshold: float = 0.8  # Alert at 80% of limit
    current_daily_spend: float = 0.0
    current_monthly_spend: float = 0.0

    def is_within_budget(self, amount: float) -> bool:
        """Check if amount is within daily and monthly limits."""
        return (self.current_daily_spend + amount) <= self.daily_limit and (
            self.current_monthly_spend + amount
        ) <= self.monthly_limit

    def is_task_within_budget(self, amount: float) -> bool:
        """Check if amount is within per-task limit."""
        return amount <= self.per_task_limit

    def should_alert(self) -> bool:
        """Check if spending is above alert threshold."""
        daily_ratio = self.current_daily_spend / self.daily_limit if self.daily_limit > 0 else 0.0
        monthly_ratio = (
            self.current_monthly_spend / self.monthly_limit if self.monthly_limit > 0 else 0.0
        )
        return daily_ratio >= self.alert_threshold or monthly_ratio >= self.alert_threshold

    def add_spend(self, amount: float) -> None:
        """Add to current spend."""
        self.current_daily_spend += amount
        self.current_monthly_spend += amount

    def reset_daily(self) -> None:
        """Reset daily spend."""
        self.current_daily_spend = 0.0

    def reset_monthly(self) -> None:
        """Reset monthly spend."""
        self.current_monthly_spend = 0.0


class CostTracker:
    """LLM model cost tracker.

    Registers and controls token usage and associated costs
    for LLM model invocations in the framework.
    """

    def __init__(self, default_pricing: Optional[Dict[str, ModelPricing]] = None) -> None:
        """Initialize the CostTracker.

        Args:
            default_pricing: Optional dictionary of model name to ModelPricing
                to merge with the built-in defaults.
        """
        self._usage_records: List[UsageRecord] = []
        self._budgets: Dict[str, CostBudget] = {}

        _default_pricing = {
            "qwen3.5": ModelPricing(
                model_name="qwen3.5",
                input_cost_per_1k=0.0001,
                output_cost_per_1k=0.0002,
                tier=CostTier.LOW,
            ),
            "qwen3-coder-next": ModelPricing(
                model_name="qwen3-coder-next",
                input_cost_per_1k=0.0002,
                output_cost_per_1k=0.0004,
                tier=CostTier.LOW,
            ),
            "deepseek-v3.2": ModelPricing(
                model_name="deepseek-v3.2",
                input_cost_per_1k=0.0003,
                output_cost_per_1k=0.0006,
                tier=CostTier.LOW,
            ),
            "mistral-large": ModelPricing(
                model_name="mistral-large",
                input_cost_per_1k=0.002,
                output_cost_per_1k=0.006,
                tier=CostTier.MEDIUM,
            ),
            "gemma4:31b": ModelPricing(
                model_name="gemma4:31b",
                input_cost_per_1k=0.0001,
                output_cost_per_1k=0.0002,
                tier=CostTier.LOW,
            ),
        }
        self._pricing: Dict[str, ModelPricing] = _default_pricing

        if default_pricing:
            self._pricing.update(default_pricing)

        self._logger = structlog.get_logger()

    def record_usage(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        project_id: str = "",
        agent_role: str = "",
        session_id: str = "",
        task_description: str = "",
    ) -> UsageRecord:
        """Record a model usage event.

        Args:
            model_name: Name of the LLM model used.
            input_tokens: Number of input tokens consumed.
            output_tokens: Number of output tokens generated.
            project_id: Optional project identifier.
            agent_role: Optional agent role that made the invocation.
            session_id: Optional session identifier.
            task_description: Optional description of the task.

        Returns:
            UsageRecord with the recorded usage and estimated cost.
        """
        estimated_cost = self.estimate_cost(model_name, input_tokens, output_tokens)

        # Check budget constraints
        if project_id and project_id in self._budgets:
            budget = self._budgets[project_id]
            if not budget.is_within_budget(estimated_cost):
                self._logger.warning(
                    "budget_exceeded",
                    project_id=project_id,
                    estimated_cost=estimated_cost,
                    daily_spend=budget.current_daily_spend,
                    daily_limit=budget.daily_limit,
                    monthly_spend=budget.current_monthly_spend,
                    monthly_limit=budget.monthly_limit,
                )
            if not budget.is_task_within_budget(estimated_cost):
                self._logger.warning(
                    "task_budget_exceeded",
                    project_id=project_id,
                    estimated_cost=estimated_cost,
                    per_task_limit=budget.per_task_limit,
                )

        record = UsageRecord(
            model_name=model_name,
            project_id=project_id,
            agent_role=agent_role,
            session_id=session_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost=estimated_cost,
            task_description=task_description,
        )

        self._usage_records.append(record)

        # Update budget spend
        if project_id and project_id in self._budgets:
            self._budgets[project_id].add_spend(estimated_cost)

        self._logger.info(
            "usage_recorded",
            record_id=record.record_id,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=record.total_tokens,
            estimated_cost=estimated_cost,
            project_id=project_id,
            agent_role=agent_role,
        )

        return record

    def estimate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate the cost for a model invocation.

        Args:
            model_name: Name of the LLM model.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in the model's configured currency.
        """
        pricing = self._pricing.get(model_name)
        if pricing is None:
            self._logger.warning("unknown_model_pricing", model_name=model_name)
            return 0.0

        cost = (input_tokens / 1000) * pricing.input_cost_per_1k + (
            output_tokens / 1000
        ) * pricing.output_cost_per_1k
        return cost

    def check_budget(self, project_id: str, estimated_cost: float) -> bool:
        """Check if an estimated cost is within the project's budget.

        Args:
            project_id: Project identifier.
            estimated_cost: Estimated cost to check.

        Returns:
            True if within budget, False if over. Returns True if no
            budget is configured for the project.
        """
        budget = self._budgets.get(project_id)
        if budget is None:
            return True
        return budget.is_within_budget(estimated_cost)

    def set_budget(
        self,
        project_id: str,
        daily_limit: float = 10.0,
        monthly_limit: float = 100.0,
        per_task_limit: float = 1.0,
    ) -> None:
        """Create or update the cost budget for a project.

        Args:
            project_id: Project identifier.
            daily_limit: Daily budget in USD.
            monthly_limit: Monthly budget in USD.
            per_task_limit: Per-task budget in USD.
        """
        if project_id in self._budgets:
            budget = self._budgets[project_id]
            budget.daily_limit = daily_limit
            budget.monthly_limit = monthly_limit
            budget.per_task_limit = per_task_limit
        else:
            self._budgets[project_id] = CostBudget(
                project_id=project_id,
                daily_limit=daily_limit,
                monthly_limit=monthly_limit,
                per_task_limit=per_task_limit,
            )

        self._logger.info(
            "budget_set",
            project_id=project_id,
            daily_limit=daily_limit,
            monthly_limit=monthly_limit,
            per_task_limit=per_task_limit,
        )

    def get_usage_report(
        self,
        project_id: Optional[str] = None,
        model_name: Optional[str] = None,
        agent_role: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Generate a usage report with optional filters.

        Args:
            project_id: Filter by project identifier.
            model_name: Filter by model name.
            agent_role: Filter by agent role.
            start_date: Filter records after this date.
            end_date: Filter records before this date.

        Returns:
            Dictionary with usage statistics including totals,
            breakdowns by model, agent, and project.
        """
        filtered_records = self._usage_records

        if project_id is not None:
            filtered_records = [r for r in filtered_records if r.project_id == project_id]
        if model_name is not None:
            filtered_records = [r for r in filtered_records if r.model_name == model_name]
        if agent_role is not None:
            filtered_records = [r for r in filtered_records if r.agent_role == agent_role]
        if start_date is not None:
            filtered_records = [r for r in filtered_records if r.timestamp >= start_date]
        if end_date is not None:
            filtered_records = [r for r in filtered_records if r.timestamp <= end_date]

        total_tokens = sum(r.total_tokens for r in filtered_records)
        total_cost = sum(r.estimated_cost for r in filtered_records)

        by_model: Dict[str, Dict[str, Any]] = {}
        for r in filtered_records:
            if r.model_name not in by_model:
                by_model[r.model_name] = {"tokens": 0, "cost": 0.0, "count": 0}
            by_model[r.model_name]["tokens"] += r.total_tokens
            by_model[r.model_name]["cost"] += r.estimated_cost
            by_model[r.model_name]["count"] += 1

        by_agent: Dict[str, Dict[str, Any]] = {}
        for r in filtered_records:
            role = r.agent_role or "unassigned"
            if role not in by_agent:
                by_agent[role] = {"tokens": 0, "cost": 0.0, "count": 0}
            by_agent[role]["tokens"] += r.total_tokens
            by_agent[role]["cost"] += r.estimated_cost
            by_agent[role]["count"] += 1

        by_project: Dict[str, Dict[str, Any]] = {}
        for r in filtered_records:
            proj = r.project_id or "unassigned"
            if proj not in by_project:
                by_project[proj] = {"tokens": 0, "cost": 0.0, "count": 0}
            by_project[proj]["tokens"] += r.total_tokens
            by_project[proj]["cost"] += r.estimated_cost
            by_project[proj]["count"] += 1

        return {
            "total_records": len(filtered_records),
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "by_model": by_model,
            "by_agent": by_agent,
            "by_project": by_project,
        }

    def get_project_spend(self, project_id: str) -> Dict[str, float]:
        """Get the current spend for a project.

        Args:
            project_id: Project identifier.

        Returns:
            Dictionary with daily, monthly, and total spend.
        """
        budget = self._budgets.get(project_id)
        daily = budget.current_daily_spend if budget else 0.0
        monthly = budget.current_monthly_spend if budget else 0.0

        project_records = [r for r in self._usage_records if r.project_id == project_id]
        total = sum(r.estimated_cost for r in project_records)

        return {"daily": daily, "monthly": monthly, "total": total}

    def add_model_pricing(
        self,
        model_name: str,
        input_cost_per_1k: float,
        output_cost_per_1k: float,
        tier: CostTier = CostTier.LOW,
    ) -> None:
        """Add or update pricing for a model.

        Args:
            model_name: Name of the LLM model.
            input_cost_per_1k: Cost per 1K input tokens.
            output_cost_per_1k: Cost per 1K output tokens.
            tier: Cost tier classification.
        """
        self._pricing[model_name] = ModelPricing(
            model_name=model_name,
            input_cost_per_1k=input_cost_per_1k,
            output_cost_per_1k=output_cost_per_1k,
            tier=tier,
        )
        self._logger.info(
            "model_pricing_added",
            model_name=model_name,
            input_cost_per_1k=input_cost_per_1k,
            output_cost_per_1k=output_cost_per_1k,
            tier=tier.value,
        )

    def reset_daily_budgets(self) -> None:
        """Reset all daily budgets."""
        for budget in self._budgets.values():
            budget.reset_daily()
        self._logger.info("daily_budgets_reset")

    def reset_monthly_budgets(self) -> None:
        """Reset all monthly budgets."""
        for budget in self._budgets.values():
            budget.reset_monthly()
        self._logger.info("monthly_budgets_reset")

    def get_budget_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get the budget status for a project.

        Args:
            project_id: Project identifier.

        Returns:
            Dictionary with budget details, or None if no budget is configured.
        """
        budget = self._budgets.get(project_id)
        if budget is None:
            return None

        daily_remaining = max(budget.daily_limit - budget.current_daily_spend, 0.0)
        monthly_remaining = max(budget.monthly_limit - budget.current_monthly_spend, 0.0)
        daily_pct = (
            (budget.current_daily_spend / budget.daily_limit * 100)
            if budget.daily_limit > 0
            else 0.0
        )
        monthly_pct = (
            (budget.current_monthly_spend / budget.monthly_limit * 100)
            if budget.monthly_limit > 0
            else 0.0
        )

        return {
            "project_id": budget.project_id,
            "daily_limit": budget.daily_limit,
            "daily_spend": budget.current_daily_spend,
            "daily_remaining": daily_remaining,
            "daily_usage_pct": daily_pct,
            "monthly_limit": budget.monthly_limit,
            "monthly_spend": budget.current_monthly_spend,
            "monthly_remaining": monthly_remaining,
            "monthly_usage_pct": monthly_pct,
            "per_task_limit": budget.per_task_limit,
            "alert_threshold": budget.alert_threshold,
            "should_alert": budget.should_alert(),
        }

    def get_model_recommendation(
        self,
        task_type: str,
        budget_constraint: Optional[float] = None,
    ) -> str:
        """Get a model recommendation based on task type and budget.

        Args:
            task_type: Type of task (e.g., "coding", "architecture", "database").
            budget_constraint: Optional maximum cost per 1K tokens constraint.

        Returns:
            Recommended model name.
        """
        # Task-based recommendations
        task_recommendations: Dict[str, str] = {
            "coding": "qwen3-coder-next",
            "architecture": "mistral-large",
            "database": "deepseek-v3.2",
        }

        recommended = task_recommendations.get(task_type, "qwen3.5")

        # If budget is tight, check if recommended model fits
        if budget_constraint is not None:
            pricing = self._pricing.get(recommended)
            if pricing is not None:
                max_cost = max(pricing.input_cost_per_1k, pricing.output_cost_per_1k)
                if max_cost > budget_constraint:
                    # Try to find a lower-tier model
                    sorted_models = sorted(
                        self._pricing.values(),
                        key=lambda p: max(p.input_cost_per_1k, p.output_cost_per_1k),
                    )
                    for model in sorted_models:
                        model_max_cost = max(model.input_cost_per_1k, model.output_cost_per_1k)
                        if model_max_cost <= budget_constraint:
                            recommended = model.model_name
                            break

        self._logger.info(
            "model_recommended",
            task_type=task_type,
            budget_constraint=budget_constraint,
            recommended=recommended,
        )

        return recommended
