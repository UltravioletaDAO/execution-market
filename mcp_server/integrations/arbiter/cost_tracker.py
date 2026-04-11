"""Daily and per-caller cost tracking for Ring 2 arbiter inference."""

import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DEFAULT_DAILY_BUDGET_USD = 100.0
DEFAULT_PER_CALLER_BUDGET_USD = 10.0
ANONYMOUS_PER_CALLER_BUDGET_USD = 1.0
MAX_PER_EVAL_USD = 0.20

# In-memory tracking (adequate while AaaS is single-instance on ECS)
_daily_total: float = 0.0
_daily_date: str = ""
_per_caller: dict[str, float] = {}


class CostTracker:
    """Track daily and per-caller inference spend.

    In-memory implementation suitable for single-instance ECS deployment.
    Resets daily totals at midnight UTC. Per-caller budgets reset daily.

    Budget hierarchy:
        1. Per-eval cap: MAX_PER_EVAL_USD ($0.20)
        2. Per-caller cap: $10/day (external) or $1/day (anonymous/platform)
        3. Daily global cap: configurable via env var ARBITER_DAILY_BUDGET_USD
    """

    def __init__(
        self,
        daily_budget: float | None = None,
        per_caller_budget: float | None = None,
    ):
        self.daily_budget = daily_budget or float(
            os.environ.get("ARBITER_DAILY_BUDGET_USD", DEFAULT_DAILY_BUDGET_USD)
        )
        self.per_caller_budget = per_caller_budget or float(
            os.environ.get(
                "ARBITER_PER_CALLER_BUDGET_USD", DEFAULT_PER_CALLER_BUDGET_USD
            )
        )

    def can_spend(self, estimated_cost: float, caller_id: str) -> tuple[bool, str]:
        """Pre-check whether a spend is allowed.

        Args:
            estimated_cost: Estimated USD cost of this evaluation.
            caller_id: Wallet address, agent ID, or "anonymous".

        Returns:
            (allowed, reason) -- reason is "ok" if allowed, otherwise
            a human-readable explanation of why the budget was exceeded.
        """
        global _daily_total, _daily_date, _per_caller
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if _daily_date != today:
            _daily_total = 0.0
            _per_caller.clear()
            _daily_date = today

        if estimated_cost > MAX_PER_EVAL_USD:
            return False, (
                f"Single eval exceeds cap (${estimated_cost:.3f} > ${MAX_PER_EVAL_USD})"
            )
        if _daily_total + estimated_cost > self.daily_budget:
            return False, (
                f"Daily budget exceeded (${_daily_total:.2f}/${self.daily_budget:.2f})"
            )

        caller_budget = (
            ANONYMOUS_PER_CALLER_BUDGET_USD
            if caller_id in ("anonymous", "2106")
            else self.per_caller_budget
        )
        caller_spent = _per_caller.get(caller_id, 0.0)
        if caller_spent + estimated_cost > caller_budget:
            return False, (
                f"Per-caller budget exceeded (${caller_spent:.2f}/${caller_budget:.2f})"
            )

        return True, "ok"

    def record_spend(self, cost: float, caller_id: str) -> None:
        """Record actual spend after evaluation completes."""
        global _daily_total, _per_caller
        _daily_total += cost
        _per_caller[caller_id] = _per_caller.get(caller_id, 0.0) + cost
        logger.info(
            "ARBITER_COST caller=%s cost=%.4f daily=%.2f",
            caller_id,
            cost,
            _daily_total,
        )
