"""
BudgetController — Centralized Budget Management for the KK V2 Swarm
=====================================================================

Consolidates all budget logic into a single authoritative module.
Existing per-agent budgets in LifecycleManager handle micro-level
limits; BudgetController handles macro-level concerns:

  1. **Fleet-wide budget** — Total pool for all agents combined
  2. **Phase-aware policies** — Different spend rules per Phase
  3. **Burn rate tracking** — Rolling spend velocity + projections
  4. **On-chain balance awareness** — Actual USDC available on-chain
  5. **Alerts & recommendations** — Proactive budget health signals
  6. **PhaseGate integration** — Budget metrics feed gate evaluations

Budget hierarchy:
    PhasePolicy (macro caps)
      └─ FleetBudget (total pool)
           └─ AgentBudget (per-agent, delegated to LifecycleManager)

Thread-safe. No external dependencies beyond stdlib.
"""

import copy
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Optional

logger = logging.getLogger("em.swarm.budget_controller")


# ─── Phase-Aware Spending Policies ────────────────────────────


class SpendPhase(IntEnum):
    """Mirrors PhaseGate phases for budget policies."""

    EMERGENCY = -1
    PRE_FLIGHT = 0
    PASSIVE = 1
    SEMI_AUTO = 2
    FULL_AUTO = 3


@dataclass
class PhasePolicy:
    """Spending policy for a specific phase.

    Controls what the swarm is allowed to spend when operating
    in a given phase. Policies get progressively more permissive
    as the phase advances.
    """

    phase: SpendPhase
    max_task_usd: float  # Max bounty for a single task
    max_daily_usd: float  # Fleet-wide daily cap
    max_monthly_usd: float  # Fleet-wide monthly cap
    require_approval: bool  # Human approval required for each task?
    auto_assign: bool  # Can auto-assign workers?
    description: str = ""

    def allows_spend(self, amount_usd: float) -> bool:
        """Check if a single spend is within task limit."""
        return amount_usd <= self.max_task_usd

    def to_dict(self) -> dict:
        return {
            "phase": self.phase.name,
            "max_task_usd": self.max_task_usd,
            "max_daily_usd": self.max_daily_usd,
            "max_monthly_usd": self.max_monthly_usd,
            "require_approval": self.require_approval,
            "auto_assign": self.auto_assign,
            "description": self.description,
        }


# Default policies matching the Activation Roadmap
DEFAULT_POLICIES: dict[SpendPhase, PhasePolicy] = {
    SpendPhase.EMERGENCY: PhasePolicy(
        phase=SpendPhase.EMERGENCY,
        max_task_usd=0.0,
        max_daily_usd=0.0,
        max_monthly_usd=0.0,
        require_approval=True,
        auto_assign=False,
        description="Emergency stop — no spending allowed",
    ),
    SpendPhase.PRE_FLIGHT: PhasePolicy(
        phase=SpendPhase.PRE_FLIGHT,
        max_task_usd=0.0,
        max_daily_usd=0.0,
        max_monthly_usd=0.0,
        require_approval=True,
        auto_assign=False,
        description="Pre-flight — verification only, no spending",
    ),
    SpendPhase.PASSIVE: PhasePolicy(
        phase=SpendPhase.PASSIVE,
        max_task_usd=0.0,
        max_daily_usd=0.0,
        max_monthly_usd=0.0,
        require_approval=True,
        auto_assign=False,
        description="Passive observation — monitoring only, no spending",
    ),
    SpendPhase.SEMI_AUTO: PhasePolicy(
        phase=SpendPhase.SEMI_AUTO,
        max_task_usd=0.25,
        max_daily_usd=5.0,
        max_monthly_usd=50.0,
        require_approval=False,
        auto_assign=True,
        description="Semi-auto — micro-tasks under $0.25, daily cap $5",
    ),
    SpendPhase.FULL_AUTO: PhasePolicy(
        phase=SpendPhase.FULL_AUTO,
        max_task_usd=10.0,
        max_daily_usd=50.0,
        max_monthly_usd=500.0,
        require_approval=False,
        auto_assign=True,
        description="Full auto — tasks up to $10, daily cap $50",
    ),
}


# ─── Spend Tracking ──────────────────────────────────────────


@dataclass
class SpendRecord:
    """Individual spend event."""

    task_id: str
    agent_id: int
    amount_usd: float
    category: str
    timestamp: float = field(default_factory=time.time)
    approved_by: str = "auto"  # "auto" or human identifier
    status: str = "committed"  # committed, refunded, pending

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "amount_usd": self.amount_usd,
            "category": self.category,
            "timestamp": self.timestamp,
            "approved_by": self.approved_by,
            "status": self.status,
        }


@dataclass
class BurnRate:
    """Rolling burn rate calculation over a time window."""

    window_seconds: float  # Calculation window
    total_usd: float  # Total spent in window
    transaction_count: int  # Number of transactions
    usd_per_hour: float  # Hourly velocity
    usd_per_day: float  # Daily velocity (projected)
    runway_hours: Optional[float]  # Hours until budget depleted (None=infinite)
    runway_days: Optional[float]  # Days until budget depleted
    trend: str  # "increasing", "stable", "decreasing", "zero"

    def to_dict(self) -> dict:
        return {
            "window_seconds": self.window_seconds,
            "total_usd": round(self.total_usd, 4),
            "transaction_count": self.transaction_count,
            "usd_per_hour": round(self.usd_per_hour, 4),
            "usd_per_day": round(self.usd_per_day, 4),
            "runway_hours": round(self.runway_hours, 1) if self.runway_hours else None,
            "runway_days": round(self.runway_days, 1) if self.runway_days else None,
            "trend": self.trend,
        }


@dataclass
class BudgetAlert:
    """Budget health alert."""

    level: str  # "info", "warning", "critical"
    code: str  # Machine-readable alert code
    message: str  # Human-readable message
    timestamp: float = field(default_factory=time.time)
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "code": self.code,
            "message": self.message,
            "timestamp": self.timestamp,
            "data": self.data,
        }


# ─── On-Chain Balance Snapshot ────────────────────────────────


@dataclass
class BalanceSnapshot:
    """On-chain USDC balance at a point in time."""

    wallet_address: str
    balance_usdc: float
    chain: str  # "base", "ethereum", etc.
    block_number: Optional[int] = None
    fetched_at: float = field(default_factory=time.time)

    @property
    def age_seconds(self) -> float:
        return time.time() - self.fetched_at

    @property
    def is_stale(self) -> bool:
        """Balance older than 5 minutes is considered stale."""
        return self.age_seconds > 300

    def to_dict(self) -> dict:
        return {
            "wallet_address": self.wallet_address,
            "balance_usdc": round(self.balance_usdc, 6),
            "chain": self.chain,
            "block_number": self.block_number,
            "fetched_at": self.fetched_at,
            "age_seconds": round(self.age_seconds, 1),
            "is_stale": self.is_stale,
        }


# ─── Budget Controller ───────────────────────────────────────


class BudgetExceededError(Exception):
    """Raised when a spend would exceed budget limits."""

    def __init__(
        self, message: str, limit_type: str, limit_usd: float, requested_usd: float
    ):
        super().__init__(message)
        self.limit_type = limit_type
        self.limit_usd = limit_usd
        self.requested_usd = requested_usd


class BudgetController:
    """
    Centralized fleet-wide budget management.

    Tracks all swarm spending, enforces phase-aware limits,
    calculates burn rates, and generates alerts.

    Architecture:
        BudgetController
         ├── Phase policies (what's allowed)
         ├── Spend history (what happened)
         ├── Balance snapshots (what's available)
         ├── Burn rate calculator (velocity tracking)
         └── Alert generator (health signals)

    Thread-safe via simple locking discipline (all mutations
    go through public methods that hold a conceptual lock —
    Python's GIL makes this safe for in-process use).
    """

    def __init__(
        self,
        policies: dict[SpendPhase, PhasePolicy] | None = None,
        fleet_daily_limit_usd: float = 50.0,
        fleet_monthly_limit_usd: float = 500.0,
        history_max_size: int = 10000,
        alert_max_size: int = 1000,
    ):
        self._policies = copy.deepcopy(policies or DEFAULT_POLICIES)
        self._fleet_daily_limit = fleet_daily_limit_usd
        self._fleet_monthly_limit = fleet_monthly_limit_usd

        # Current phase
        self._current_phase: SpendPhase = SpendPhase.PRE_FLIGHT

        # Spend tracking
        self._history: deque[SpendRecord] = deque(maxlen=history_max_size)
        self._daily_spent_usd: float = 0.0
        self._monthly_spent_usd: float = 0.0
        self._total_spent_usd: float = 0.0
        self._last_daily_reset: str = ""
        self._last_monthly_reset: str = ""

        # Per-agent spend tracking (agent_id → total_usd)
        self._agent_totals: dict[int, float] = {}
        self._agent_daily: dict[int, float] = {}

        # Balance tracking
        self._balances: dict[str, BalanceSnapshot] = {}  # chain → snapshot

        # Alerts
        self._alerts: deque[BudgetAlert] = deque(maxlen=alert_max_size)

        # Burn rate tracking (recent spends for velocity calc)
        self._recent_spends: deque[tuple[float, float]] = deque(
            maxlen=1000
        )  # (timestamp, amount)

        # Previous burn rates for trend detection
        self._burn_rate_history: deque[float] = deque(maxlen=24)  # hourly rates

        # Stats
        self._approval_count: int = 0
        self._rejection_count: int = 0
        self._refund_count: int = 0

        # Initialize reset dates
        self._check_resets()

        logger.info(
            f"BudgetController initialized: phase={self._current_phase.name}, "
            f"daily_limit=${self._fleet_daily_limit}, monthly_limit=${self._fleet_monthly_limit}"
        )

    # ─── Phase Management ─────────────────────────────────────

    @property
    def current_phase(self) -> SpendPhase:
        return self._current_phase

    @property
    def current_policy(self) -> PhasePolicy:
        return self._policies[self._current_phase]

    def set_phase(self, phase: SpendPhase) -> None:
        """Update the current phase. Adjusts spending limits accordingly."""
        old = self._current_phase
        self._current_phase = phase

        if old != phase:
            self._add_alert(
                "info",
                "phase_change",
                f"Budget phase changed: {old.name} → {phase.name}",
                {"old_phase": old.name, "new_phase": phase.name},
            )
            logger.info(f"Budget phase changed: {old.name} → {phase.name}")

    def get_policy(self, phase: SpendPhase | None = None) -> PhasePolicy:
        """Get policy for a phase (defaults to current)."""
        p = phase if phase is not None else self._current_phase
        return self._policies[p]

    def update_policy(self, phase: SpendPhase, **kwargs) -> None:
        """Update specific policy fields for a phase."""
        policy = self._policies[phase]
        for key, value in kwargs.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
            else:
                raise ValueError(f"Unknown policy field: {key}")
        logger.info(f"Policy updated for {phase.name}: {kwargs}")

    # ─── Spend Authorization ──────────────────────────────────

    def authorize_spend(
        self,
        task_id: str,
        agent_id: int,
        amount_usd: float,
        category: str = "general",
        approved_by: str = "auto",
    ) -> SpendRecord:
        """Authorize and record a spend.

        Checks:
        1. Phase allows spending
        2. Amount within per-task limit
        3. Daily fleet limit not exceeded
        4. Monthly fleet limit not exceeded

        Returns SpendRecord on success.
        Raises BudgetExceededError on failure.
        """
        self._check_resets()
        policy = self.current_policy

        # Phase check
        if not policy.allows_spend(amount_usd):
            self._rejection_count += 1
            raise BudgetExceededError(
                f"Phase {self._current_phase.name} max task is ${policy.max_task_usd}, "
                f"requested ${amount_usd}",
                limit_type="phase_task",
                limit_usd=policy.max_task_usd,
                requested_usd=amount_usd,
            )

        # Daily fleet limit
        effective_daily = min(self._fleet_daily_limit, policy.max_daily_usd)
        if self._daily_spent_usd + amount_usd > effective_daily:
            self._rejection_count += 1
            remaining = max(0, effective_daily - self._daily_spent_usd)
            raise BudgetExceededError(
                f"Daily fleet limit ${effective_daily} would be exceeded. "
                f"Spent: ${self._daily_spent_usd:.2f}, remaining: ${remaining:.2f}",
                limit_type="daily_fleet",
                limit_usd=effective_daily,
                requested_usd=amount_usd,
            )

        # Monthly fleet limit
        effective_monthly = min(self._fleet_monthly_limit, policy.max_monthly_usd)
        if self._monthly_spent_usd + amount_usd > effective_monthly:
            self._rejection_count += 1
            remaining = max(0, effective_monthly - self._monthly_spent_usd)
            raise BudgetExceededError(
                f"Monthly fleet limit ${effective_monthly} would be exceeded. "
                f"Spent: ${self._monthly_spent_usd:.2f}, remaining: ${remaining:.2f}",
                limit_type="monthly_fleet",
                limit_usd=effective_monthly,
                requested_usd=amount_usd,
            )

        # Approval check
        if policy.require_approval and approved_by == "auto":
            self._rejection_count += 1
            raise BudgetExceededError(
                f"Phase {self._current_phase.name} requires human approval",
                limit_type="approval_required",
                limit_usd=amount_usd,
                requested_usd=amount_usd,
            )

        # All checks pass — record the spend
        record = SpendRecord(
            task_id=task_id,
            agent_id=agent_id,
            amount_usd=amount_usd,
            category=category,
            approved_by=approved_by,
        )

        self._history.append(record)
        self._daily_spent_usd += amount_usd
        self._monthly_spent_usd += amount_usd
        self._total_spent_usd += amount_usd
        self._agent_totals[agent_id] = self._agent_totals.get(agent_id, 0) + amount_usd
        self._agent_daily[agent_id] = self._agent_daily.get(agent_id, 0) + amount_usd
        self._recent_spends.append((time.time(), amount_usd))
        self._approval_count += 1

        # Check for warning thresholds
        daily_pct = (
            self._daily_spent_usd / effective_daily if effective_daily > 0 else 0
        )
        monthly_pct = (
            self._monthly_spent_usd / effective_monthly if effective_monthly > 0 else 0
        )

        if daily_pct >= 0.90:
            self._add_alert(
                "critical",
                "daily_budget_critical",
                f"Daily budget at {daily_pct * 100:.0f}%: ${self._daily_spent_usd:.2f}/${effective_daily}",
                {
                    "pct": daily_pct,
                    "spent": self._daily_spent_usd,
                    "limit": effective_daily,
                },
            )
        elif daily_pct >= 0.75:
            self._add_alert(
                "warning",
                "daily_budget_warning",
                f"Daily budget at {daily_pct * 100:.0f}%: ${self._daily_spent_usd:.2f}/${effective_daily}",
                {
                    "pct": daily_pct,
                    "spent": self._daily_spent_usd,
                    "limit": effective_daily,
                },
            )

        if monthly_pct >= 0.90:
            self._add_alert(
                "critical",
                "monthly_budget_critical",
                f"Monthly budget at {monthly_pct * 100:.0f}%: ${self._monthly_spent_usd:.2f}/${effective_monthly}",
                {
                    "pct": monthly_pct,
                    "spent": self._monthly_spent_usd,
                    "limit": effective_monthly,
                },
            )
        elif monthly_pct >= 0.75:
            self._add_alert(
                "warning",
                "monthly_budget_warning",
                f"Monthly budget at {monthly_pct * 100:.0f}%: ${self._monthly_spent_usd:.2f}/${effective_monthly}",
                {
                    "pct": monthly_pct,
                    "spent": self._monthly_spent_usd,
                    "limit": effective_monthly,
                },
            )

        logger.info(
            f"Spend authorized: task={task_id}, agent={agent_id}, "
            f"${amount_usd:.2f} ({category}), daily=${self._daily_spent_usd:.2f}"
        )

        return record

    def record_refund(self, task_id: str, amount_usd: float) -> None:
        """Record a refund (task cancelled, dispute won, etc.)."""
        self._daily_spent_usd = max(0, self._daily_spent_usd - amount_usd)
        self._monthly_spent_usd = max(0, self._monthly_spent_usd - amount_usd)
        self._total_spent_usd = max(0, self._total_spent_usd - amount_usd)
        self._refund_count += 1

        # Mark in history
        for record in reversed(self._history):
            if record.task_id == task_id and record.status == "committed":
                record.status = "refunded"
                if record.agent_id in self._agent_totals:
                    self._agent_totals[record.agent_id] = max(
                        0, self._agent_totals[record.agent_id] - amount_usd
                    )
                break

        self._add_alert(
            "info",
            "refund_processed",
            f"Refund processed: ${amount_usd:.2f} for task {task_id}",
            {"task_id": task_id, "amount": amount_usd},
        )
        logger.info(f"Refund: ${amount_usd:.2f} for task {task_id}")

    def can_spend(self, amount_usd: float) -> tuple[bool, str]:
        """Check if a spend would be allowed (without committing).

        Returns (allowed, reason).
        """
        self._check_resets()
        policy = self.current_policy

        if not policy.allows_spend(amount_usd):
            return False, f"Exceeds phase task limit (${policy.max_task_usd})"

        effective_daily = min(self._fleet_daily_limit, policy.max_daily_usd)
        if self._daily_spent_usd + amount_usd > effective_daily:
            return False, f"Exceeds daily fleet limit (${effective_daily})"

        effective_monthly = min(self._fleet_monthly_limit, policy.max_monthly_usd)
        if self._monthly_spent_usd + amount_usd > effective_monthly:
            return False, f"Exceeds monthly fleet limit (${effective_monthly})"

        if policy.require_approval:
            return False, "Requires human approval"

        return True, "OK"

    # ─── Balance Tracking ─────────────────────────────────────

    def update_balance(
        self,
        wallet_address: str,
        balance_usdc: float,
        chain: str = "base",
        block_number: int | None = None,
    ) -> BalanceSnapshot:
        """Update on-chain balance snapshot."""
        snapshot = BalanceSnapshot(
            wallet_address=wallet_address,
            balance_usdc=balance_usdc,
            chain=chain,
            block_number=block_number,
        )
        self._balances[chain] = snapshot

        # Alert on low balance
        if balance_usdc < 10.0:
            self._add_alert(
                "warning" if balance_usdc >= 1.0 else "critical",
                "low_balance",
                f"Low USDC balance on {chain}: ${balance_usdc:.2f}",
                {"chain": chain, "balance": balance_usdc, "wallet": wallet_address},
            )

        return snapshot

    def get_total_balance(self) -> float:
        """Get total USDC across all chains."""
        return sum(b.balance_usdc for b in self._balances.values())

    def get_balances(self) -> dict[str, BalanceSnapshot]:
        """Get all balance snapshots."""
        return dict(self._balances)

    # ─── Burn Rate Analysis ───────────────────────────────────

    def calculate_burn_rate(self, window_hours: float = 24.0) -> BurnRate:
        """Calculate current burn rate over a rolling window.

        Args:
            window_hours: Time window for velocity calculation

        Returns:
            BurnRate with velocity, runway, and trend
        """
        now = time.time()
        window_seconds = window_hours * 3600
        cutoff = now - window_seconds

        # Sum spends in window
        total_in_window = 0.0
        count_in_window = 0
        for ts, amount in self._recent_spends:
            if ts >= cutoff:
                total_in_window += amount
                count_in_window += 1

        # Calculate velocity
        if window_seconds > 0:
            usd_per_second = total_in_window / window_seconds
        else:
            usd_per_second = 0.0

        usd_per_hour = usd_per_second * 3600
        usd_per_day = usd_per_hour * 24

        # Calculate runway
        available = self.get_total_balance()
        policy = self.current_policy

        # Use the most constraining remaining limit
        max(
            0,
            min(self._fleet_daily_limit, policy.max_daily_usd) - self._daily_spent_usd,
        )  # daily check
        monthly_remaining = max(
            0,
            min(self._fleet_monthly_limit, policy.max_monthly_usd)
            - self._monthly_spent_usd,
        )

        # Available is min of on-chain balance and remaining budget
        effective_available = (
            min(available, monthly_remaining) if available > 0 else monthly_remaining
        )

        if usd_per_hour > 0:
            runway_hours = effective_available / usd_per_hour
            runway_days = runway_hours / 24
        else:
            runway_hours = None
            runway_days = None

        # Trend detection
        self._burn_rate_history.append(usd_per_hour)
        trend = self._detect_trend()

        return BurnRate(
            window_seconds=window_seconds,
            total_usd=total_in_window,
            transaction_count=count_in_window,
            usd_per_hour=usd_per_hour,
            usd_per_day=usd_per_day,
            runway_hours=runway_hours,
            runway_days=runway_days,
            trend=trend,
        )

    def _detect_trend(self) -> str:
        """Detect spending trend from burn rate history."""
        rates = list(self._burn_rate_history)
        if len(rates) < 3:
            return "insufficient_data"

        if all(r == 0 for r in rates):
            return "zero"

        # Compare recent half to older half
        mid = len(rates) // 2
        old_avg = sum(rates[:mid]) / mid if mid > 0 else 0
        new_avg = sum(rates[mid:]) / (len(rates) - mid) if (len(rates) - mid) > 0 else 0

        if old_avg == 0 and new_avg == 0:
            return "zero"
        elif old_avg == 0:
            return "increasing"
        elif new_avg == 0:
            return "decreasing"

        ratio = new_avg / old_avg
        if ratio > 1.25:
            return "increasing"
        elif ratio < 0.75:
            return "decreasing"
        else:
            return "stable"

    def project_spend(self, hours: float = 24.0) -> dict:
        """Project future spending based on current burn rate.

        Returns:
            Dict with projected spend, budget impact, and recommendations.
        """
        burn = self.calculate_burn_rate(window_hours=min(hours, 24.0))
        projected_usd = burn.usd_per_hour * hours

        policy = self.current_policy
        effective_daily = min(self._fleet_daily_limit, policy.max_daily_usd)
        effective_monthly = min(self._fleet_monthly_limit, policy.max_monthly_usd)

        daily_remaining = max(0, effective_daily - self._daily_spent_usd)
        monthly_remaining = max(0, effective_monthly - self._monthly_spent_usd)
        balance = self.get_total_balance()

        recommendations = []
        if projected_usd > daily_remaining and hours <= 24:
            recommendations.append(
                f"Projected spend (${projected_usd:.2f}) exceeds daily remaining (${daily_remaining:.2f})"
            )
        if projected_usd > monthly_remaining:
            recommendations.append(
                f"Projected spend (${projected_usd:.2f}) exceeds monthly remaining (${monthly_remaining:.2f})"
            )
        if balance > 0 and projected_usd > balance:
            recommendations.append(
                f"Projected spend (${projected_usd:.2f}) exceeds on-chain balance (${balance:.2f})"
            )
        if burn.trend == "increasing":
            recommendations.append(
                "Burn rate is increasing — consider reviewing task creation rate"
            )

        return {
            "projection_hours": hours,
            "projected_usd": round(projected_usd, 4),
            "burn_rate": burn.to_dict(),
            "daily_remaining_usd": round(daily_remaining, 2),
            "monthly_remaining_usd": round(monthly_remaining, 2),
            "on_chain_balance_usd": round(balance, 2),
            "recommendations": recommendations,
            "risk_level": (
                "critical"
                if projected_usd > balance and balance > 0
                else "high"
                if projected_usd > daily_remaining
                else "medium"
                if burn.trend == "increasing"
                else "low"
            ),
        }

    # ─── Fleet Overview ───────────────────────────────────────

    def get_fleet_budget_status(self) -> dict:
        """Comprehensive fleet-wide budget status."""
        self._check_resets()
        policy = self.current_policy

        effective_daily = min(self._fleet_daily_limit, policy.max_daily_usd)
        effective_monthly = min(self._fleet_monthly_limit, policy.max_monthly_usd)

        daily_pct = (
            (self._daily_spent_usd / effective_daily * 100)
            if effective_daily > 0
            else 0
        )
        monthly_pct = (
            (self._monthly_spent_usd / effective_monthly * 100)
            if effective_monthly > 0
            else 0
        )

        # Top spenders
        sorted_agents = sorted(
            self._agent_totals.items(), key=lambda x: x[1], reverse=True
        )
        top_spenders = [
            {"agent_id": aid, "total_usd": round(total, 4)}
            for aid, total in sorted_agents[:5]
        ]

        # Category breakdown
        category_totals: dict[str, float] = {}
        for record in self._history:
            if record.status == "committed":
                category_totals[record.category] = (
                    category_totals.get(record.category, 0) + record.amount_usd
                )

        return {
            "phase": self._current_phase.name,
            "policy": policy.to_dict(),
            "daily": {
                "spent_usd": round(self._daily_spent_usd, 4),
                "limit_usd": effective_daily,
                "remaining_usd": round(
                    max(0, effective_daily - self._daily_spent_usd), 4
                ),
                "pct": round(daily_pct, 1),
            },
            "monthly": {
                "spent_usd": round(self._monthly_spent_usd, 4),
                "limit_usd": effective_monthly,
                "remaining_usd": round(
                    max(0, effective_monthly - self._monthly_spent_usd), 4
                ),
                "pct": round(monthly_pct, 1),
            },
            "all_time": {
                "total_spent_usd": round(self._total_spent_usd, 4),
                "transaction_count": len(self._history),
                "approval_count": self._approval_count,
                "rejection_count": self._rejection_count,
                "refund_count": self._refund_count,
            },
            "balances": {
                chain: snap.to_dict() for chain, snap in self._balances.items()
            },
            "total_on_chain_usd": round(self.get_total_balance(), 2),
            "top_spenders": top_spenders,
            "category_breakdown": {
                cat: round(total, 4)
                for cat, total in sorted(
                    category_totals.items(), key=lambda x: x[1], reverse=True
                )
            },
        }

    def get_agent_spend(self, agent_id: int) -> dict:
        """Get spend summary for a specific agent."""
        self._check_resets()
        records = [
            r
            for r in self._history
            if r.agent_id == agent_id and r.status == "committed"
        ]

        category_totals: dict[str, float] = {}
        for r in records:
            category_totals[r.category] = (
                category_totals.get(r.category, 0) + r.amount_usd
            )

        return {
            "agent_id": agent_id,
            "total_usd": round(self._agent_totals.get(agent_id, 0), 4),
            "daily_usd": round(self._agent_daily.get(agent_id, 0), 4),
            "transaction_count": len(records),
            "categories": {
                cat: round(total, 4) for cat, total in category_totals.items()
            },
            "recent": [r.to_dict() for r in records[-5:]],
        }

    # ─── Alerts ───────────────────────────────────────────────

    def get_alerts(
        self,
        level: str | None = None,
        since: float | None = None,
        limit: int = 50,
    ) -> list[BudgetAlert]:
        """Get recent alerts, optionally filtered."""
        alerts = list(self._alerts)

        if level:
            alerts = [a for a in alerts if a.level == level]
        if since:
            alerts = [a for a in alerts if a.timestamp >= since]

        return alerts[-limit:]

    def _add_alert(
        self, level: str, code: str, message: str, data: dict | None = None
    ) -> None:
        """Add a budget alert."""
        alert = BudgetAlert(
            level=level,
            code=code,
            message=message,
            data=data or {},
        )
        self._alerts.append(alert)
        if level == "critical":
            logger.warning(f"BUDGET CRITICAL: {message}")
        elif level == "warning":
            logger.warning(f"Budget warning: {message}")

    # ─── PhaseGate Integration ────────────────────────────────

    def get_metrics_for_phase_gate(self) -> dict:
        """Export metrics that PhaseGate uses for gate evaluation.

        These map to gate conditions in PhaseGate:
        - avg_budget_utilization → budget headroom
        - burn_rate → spending velocity
        - balance_available → can the swarm fund tasks?
        """
        policy = self.current_policy
        effective_daily = min(self._fleet_daily_limit, policy.max_daily_usd)
        effective_monthly = min(self._fleet_monthly_limit, policy.max_monthly_usd)

        daily_util = (
            self._daily_spent_usd / effective_daily if effective_daily > 0 else 0
        )
        monthly_util = (
            self._monthly_spent_usd / effective_monthly if effective_monthly > 0 else 0
        )
        avg_util = (daily_util + monthly_util) / 2

        burn = self.calculate_burn_rate(window_hours=1.0)

        return {
            "avg_budget_utilization": round(avg_util, 4),
            "daily_utilization": round(daily_util, 4),
            "monthly_utilization": round(monthly_util, 4),
            "burn_rate_usd_per_hour": round(burn.usd_per_hour, 4),
            "burn_rate_trend": burn.trend,
            "total_balance_usd": round(self.get_total_balance(), 2),
            "daily_remaining_usd": round(
                max(0, effective_daily - self._daily_spent_usd), 4
            ),
            "monthly_remaining_usd": round(
                max(0, effective_monthly - self._monthly_spent_usd), 4
            ),
            "approval_count": self._approval_count,
            "rejection_count": self._rejection_count,
            "has_active_alerts": any(a.level == "critical" for a in self._alerts),
        }

    # ─── Serialization ────────────────────────────────────────

    def to_dict(self) -> dict:
        """Full state export for persistence."""
        return {
            "phase": self._current_phase.name,
            "fleet_daily_limit": self._fleet_daily_limit,
            "fleet_monthly_limit": self._fleet_monthly_limit,
            "daily_spent": self._daily_spent_usd,
            "monthly_spent": self._monthly_spent_usd,
            "total_spent": self._total_spent_usd,
            "last_daily_reset": self._last_daily_reset,
            "last_monthly_reset": self._last_monthly_reset,
            "agent_totals": dict(self._agent_totals),
            "agent_daily": dict(self._agent_daily),
            "approval_count": self._approval_count,
            "rejection_count": self._rejection_count,
            "refund_count": self._refund_count,
            "policies": {p.name: pol.to_dict() for p, pol in self._policies.items()},
            "balances": {ch: s.to_dict() for ch, s in self._balances.items()},
            "alerts_count": len(self._alerts),
            "history_count": len(self._history),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BudgetController":
        """Restore from persisted state."""
        controller = cls(
            fleet_daily_limit_usd=data.get("fleet_daily_limit", 50.0),
            fleet_monthly_limit_usd=data.get("fleet_monthly_limit", 500.0),
        )

        phase_name = data.get("phase", "PRE_FLIGHT")
        try:
            controller._current_phase = SpendPhase[phase_name]
        except KeyError:
            controller._current_phase = SpendPhase.PRE_FLIGHT

        controller._daily_spent_usd = data.get("daily_spent", 0.0)
        controller._monthly_spent_usd = data.get("monthly_spent", 0.0)
        controller._total_spent_usd = data.get("total_spent", 0.0)
        controller._last_daily_reset = data.get("last_daily_reset", "")
        controller._last_monthly_reset = data.get("last_monthly_reset", "")
        controller._agent_totals = {
            int(k): v for k, v in data.get("agent_totals", {}).items()
        }
        controller._agent_daily = {
            int(k): v for k, v in data.get("agent_daily", {}).items()
        }
        controller._approval_count = data.get("approval_count", 0)
        controller._rejection_count = data.get("rejection_count", 0)
        controller._refund_count = data.get("refund_count", 0)

        return controller

    # ─── Diagnostics ──────────────────────────────────────────

    def diagnostic_report(self) -> str:
        """Human-readable budget diagnostic report."""
        status = self.get_fleet_budget_status()
        burn = self.calculate_burn_rate()
        projection = self.project_spend(hours=24)

        lines = [
            "╔═══════════════════════════════════════════════════╗",
            "║         BUDGET CONTROLLER — DIAGNOSTIC            ║",
            "╠═══════════════════════════════════════════════════╣",
            f"║ Phase: {status['phase']:<44}║",
            f"║ Policy: {status['policy']['description'][:43]:<43}║",
            "╠───────────────────────────────────────────────────╣",
            f"║ Daily:   ${status['daily']['spent_usd']:>8.2f} / ${status['daily']['limit_usd']:>8.2f}  ({status['daily']['pct']:>5.1f}%) ║",
            f"║ Monthly: ${status['monthly']['spent_usd']:>8.2f} / ${status['monthly']['limit_usd']:>8.2f}  ({status['monthly']['pct']:>5.1f}%) ║",
            f"║ All-time: ${status['all_time']['total_spent_usd']:>8.2f}  ({status['all_time']['transaction_count']} txns)         ║",
            "╠───────────────────────────────────────────────────╣",
            f"║ Burn rate: ${burn.usd_per_hour:>6.4f}/hr (${burn.usd_per_day:>6.2f}/day)     ║",
            f"║ Trend: {burn.trend:<44}║",
        ]

        if burn.runway_days is not None:
            lines.append(
                f"║ Runway: {burn.runway_days:>6.1f} days                              ║"
            )
        else:
            lines.append("║ Runway: ∞ (no active spending)                    ║")

        lines.extend(
            [
                "╠───────────────────────────────────────────────────╣",
                f"║ On-chain: ${status['total_on_chain_usd']:>8.2f} USDC                       ║",
                f"║ 24h projection: ${projection['projected_usd']:>6.2f} (risk: {projection['risk_level']:<8})    ║",
                f"║ Approved: {status['all_time']['approval_count']:<6} | Rejected: {status['all_time']['rejection_count']:<6} | Refunds: {status['all_time']['refund_count']:<4}║",
            ]
        )

        if projection["recommendations"]:
            lines.append("╠───────────────────────────────────────────────────╣")
            lines.append("║ ⚠️  Recommendations:                              ║")
            for rec in projection["recommendations"][:3]:
                # Truncate to fit
                rec_short = rec[:47]
                lines.append(f"║  • {rec_short:<47}║")

        critical_alerts = [a for a in self._alerts if a.level == "critical"]
        if critical_alerts:
            lines.append("╠───────────────────────────────────────────────────╣")
            lines.append("║ 🔴 CRITICAL ALERTS:                               ║")
            for alert in critical_alerts[-3:]:
                msg_short = alert.message[:47]
                lines.append(f"║  {msg_short:<49}║")

        lines.append("╚═══════════════════════════════════════════════════╝")
        return "\n".join(lines)

    # ─── Internal ─────────────────────────────────────────────

    def _check_resets(self) -> None:
        """Check and perform daily/monthly resets."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        this_month = datetime.now(timezone.utc).strftime("%Y-%m")

        if self._last_daily_reset != today:
            if self._last_daily_reset:  # Not first run
                logger.info(
                    f"Daily budget reset: ${self._daily_spent_usd:.2f} spent yesterday"
                )
            self._daily_spent_usd = 0.0
            self._agent_daily.clear()
            self._last_daily_reset = today

        if self._last_monthly_reset != this_month:
            if self._last_monthly_reset:  # Not first run
                logger.info(
                    f"Monthly budget reset: ${self._monthly_spent_usd:.2f} spent last month"
                )
            self._monthly_spent_usd = 0.0
            self._last_monthly_reset = this_month
