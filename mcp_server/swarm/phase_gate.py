"""
PhaseGate — Swarm Activation Phase Management
================================================

Manages the transition between swarm activation phases
as defined in the Activation Roadmap:

    Phase 0: Pre-Flight    → Verify no regressions
    Phase 1: Passive       → Collect baseline metrics
    Phase 2: Semi-Auto     → Auto-assign under $0.25
    Phase 3: Full-Auto     → Full autonomous operation
    EMERGENCY: Disabled    → Kill switch

Each phase transition requires passing a set of "gates" —
measurable conditions that must be met before advancing.
Gates prevent premature activation that could waste money
or degrade the platform.

Architecture:
    PhaseGate.evaluate(current_metrics) → PhaseEvaluation
    PhaseEvaluation.can_advance → bool
    PhaseEvaluation.blockers → list[str]
    PhaseEvaluation.recommendations → list[str]

Thread-safe. No external dependencies.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Optional

logger = logging.getLogger("em.swarm.phase_gate")


# ─── Types ────────────────────────────────────────────────────────


class Phase(IntEnum):
    """Activation phases in order."""

    EMERGENCY = -1  # Kill switch — everything off
    PRE_FLIGHT = 0  # Phase 0: verify no regressions
    PASSIVE = 1  # Phase 1: observe and collect metrics
    SEMI_AUTO = 2  # Phase 2: auto-assign micro-tasks
    FULL_AUTO = 3  # Phase 3: full autonomous operation


PHASE_LABELS = {
    Phase.EMERGENCY: "EMERGENCY STOP",
    Phase.PRE_FLIGHT: "Phase 0: Pre-Flight",
    Phase.PASSIVE: "Phase 1: Passive Observation",
    Phase.SEMI_AUTO: "Phase 2: Semi-Auto Routing",
    Phase.FULL_AUTO: "Phase 3: Full Autonomous",
}

PHASE_MODE_MAP = {
    Phase.EMERGENCY: "disabled",
    Phase.PRE_FLIGHT: "passive",
    Phase.PASSIVE: "passive",
    Phase.SEMI_AUTO: "semi_auto",
    Phase.FULL_AUTO: "full_auto",
}


@dataclass
class GateCheck:
    """Result of evaluating a single gate condition."""

    name: str
    description: str
    passed: bool
    current_value: Any = None
    required_value: Any = None
    severity: str = "blocker"  # "blocker" or "warning"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "passed": self.passed,
            "current": self.current_value,
            "required": self.required_value,
            "severity": self.severity,
        }


@dataclass
class PhaseEvaluation:
    """Complete evaluation of whether phase transition is safe."""

    current_phase: Phase
    target_phase: Phase
    gates: list[GateCheck] = field(default_factory=list)
    evaluated_at: float = field(default_factory=time.time)

    @property
    def can_advance(self) -> bool:
        """True if all blocker gates pass."""
        return all(g.passed for g in self.gates if g.severity == "blocker")

    @property
    def blockers(self) -> list[str]:
        """List of failing blocker gate descriptions."""
        return [
            g.description
            for g in self.gates
            if not g.passed and g.severity == "blocker"
        ]

    @property
    def warnings(self) -> list[str]:
        """List of failing warning gate descriptions."""
        return [
            g.description
            for g in self.gates
            if not g.passed and g.severity == "warning"
        ]

    @property
    def pass_rate(self) -> float:
        """Percentage of all gates passing."""
        if not self.gates:
            return 0.0
        return sum(1 for g in self.gates if g.passed) / len(self.gates)

    def to_dict(self) -> dict:
        return {
            "current_phase": PHASE_LABELS.get(
                self.current_phase, str(self.current_phase)
            ),
            "target_phase": PHASE_LABELS.get(self.target_phase, str(self.target_phase)),
            "can_advance": self.can_advance,
            "pass_rate": round(self.pass_rate, 2),
            "blockers": self.blockers,
            "warnings": self.warnings,
            "gates": [g.to_dict() for g in self.gates],
            "evaluated_at": datetime.fromtimestamp(
                self.evaluated_at, tz=timezone.utc
            ).isoformat(),
        }


@dataclass
class SwarmMetrics:
    """Snapshot of current swarm and platform metrics."""

    # API health
    api_healthy: bool = False
    api_response_ms: float = 0.0

    # Swarm health
    swarm_enabled: bool = False
    swarm_mode: str = "disabled"
    coordinator_active: bool = False
    error_count_last_hour: int = 0
    error_count_last_24h: int = 0

    # Task metrics
    tasks_ingested: int = 0
    tasks_completed: int = 0
    tasks_expired: int = 0
    expiry_rate: float = 0.0

    # Worker metrics
    worker_count: int = 0
    categories_with_workers: int = 0
    total_categories: int = 5
    worker_hhi: float = 1.0  # Herfindahl-Hirschman Index (1.0 = monopoly)

    # Agent metrics
    agents_registered: int = 0
    agents_healthy: int = 0

    # Financial
    daily_spend_usd: float = 0.0
    daily_budget_usd: float = 0.0

    # Timing
    uptime_hours: float = 0.0
    days_in_current_phase: float = 0.0


@dataclass
class PhaseTransition:
    """Record of a phase transition."""

    from_phase: Phase
    to_phase: Phase
    reason: str
    metrics_snapshot: dict
    timestamp: float = field(default_factory=time.time)
    auto: bool = False  # True if auto-advanced, False if manual

    def to_dict(self) -> dict:
        return {
            "from": PHASE_LABELS.get(self.from_phase, str(self.from_phase)),
            "to": PHASE_LABELS.get(self.to_phase, str(self.to_phase)),
            "reason": self.reason,
            "auto": self.auto,
            "timestamp": datetime.fromtimestamp(
                self.timestamp, tz=timezone.utc
            ).isoformat(),
        }


# ─── Gate Definitions ─────────────────────────────────────────


def _gates_pre_flight_to_passive(m: SwarmMetrics) -> list[GateCheck]:
    """Phase 0 → Phase 1: Is the swarm running without errors?"""
    return [
        GateCheck(
            name="api_healthy",
            description="EM API returns healthy status",
            passed=m.api_healthy,
            current_value=m.api_healthy,
            required_value=True,
        ),
        GateCheck(
            name="swarm_enabled",
            description="Swarm is enabled in configuration",
            passed=m.swarm_enabled,
            current_value=m.swarm_enabled,
            required_value=True,
        ),
        GateCheck(
            name="coordinator_active",
            description="Coordinator is active and accepting tasks",
            passed=m.coordinator_active,
            current_value=m.coordinator_active,
            required_value=True,
        ),
        GateCheck(
            name="no_errors_1h",
            description="No errors in the last hour",
            passed=m.error_count_last_hour == 0,
            current_value=m.error_count_last_hour,
            required_value=0,
        ),
        GateCheck(
            name="uptime_min",
            description="Swarm has been running for at least 1 hour",
            passed=m.uptime_hours >= 1.0,
            current_value=round(m.uptime_hours, 1),
            required_value=1.0,
        ),
        GateCheck(
            name="tasks_ingested",
            description="Swarm has ingested at least 1 task",
            passed=m.tasks_ingested >= 1,
            current_value=m.tasks_ingested,
            required_value=1,
            severity="warning",
        ),
        GateCheck(
            name="agents_registered",
            description="At least 1 agent registered from ERC-8004",
            passed=m.agents_registered >= 1,
            current_value=m.agents_registered,
            required_value=1,
            severity="warning",
        ),
    ]


def _gates_passive_to_semi_auto(m: SwarmMetrics) -> list[GateCheck]:
    """Phase 1 → Phase 2: Enough data and stability to start routing?"""
    return [
        GateCheck(
            name="api_healthy",
            description="EM API returns healthy status",
            passed=m.api_healthy,
            current_value=m.api_healthy,
            required_value=True,
        ),
        GateCheck(
            name="min_observation_days",
            description="At least 3 days in passive observation",
            passed=m.days_in_current_phase >= 3.0,
            current_value=round(m.days_in_current_phase, 1),
            required_value=3.0,
        ),
        GateCheck(
            name="no_errors_24h",
            description="Fewer than 5 errors in last 24 hours",
            passed=m.error_count_last_24h < 5,
            current_value=m.error_count_last_24h,
            required_value="< 5",
        ),
        GateCheck(
            name="tasks_ingested",
            description="At least 10 tasks ingested during observation",
            passed=m.tasks_ingested >= 10,
            current_value=m.tasks_ingested,
            required_value=10,
        ),
        GateCheck(
            name="worker_count",
            description="At least 2 active workers",
            passed=m.worker_count >= 2,
            current_value=m.worker_count,
            required_value=2,
        ),
        GateCheck(
            name="agents_healthy",
            description="At least 5 healthy agents in fleet",
            passed=m.agents_healthy >= 5,
            current_value=m.agents_healthy,
            required_value=5,
        ),
        GateCheck(
            name="categories_coverage",
            description="Workers in at least 2 task categories",
            passed=m.categories_with_workers >= 2,
            current_value=m.categories_with_workers,
            required_value=2,
            severity="warning",
        ),
    ]


def _gates_semi_auto_to_full_auto(m: SwarmMetrics) -> list[GateCheck]:
    """Phase 2 → Phase 3: Semi-auto performing well enough for full auto?"""
    return [
        GateCheck(
            name="api_healthy",
            description="EM API returns healthy status",
            passed=m.api_healthy,
            current_value=m.api_healthy,
            required_value=True,
        ),
        GateCheck(
            name="min_semi_auto_days",
            description="At least 7 days in semi-auto mode",
            passed=m.days_in_current_phase >= 7.0,
            current_value=round(m.days_in_current_phase, 1),
            required_value=7.0,
        ),
        GateCheck(
            name="expiry_rate",
            description="Expiry rate below 25%",
            passed=m.expiry_rate < 0.25,
            current_value=round(m.expiry_rate, 3),
            required_value="< 0.25",
        ),
        GateCheck(
            name="worker_count",
            description="At least 5 active workers",
            passed=m.worker_count >= 5,
            current_value=m.worker_count,
            required_value=5,
        ),
        GateCheck(
            name="worker_concentration",
            description="Worker HHI below 0.5 (no monopoly)",
            passed=m.worker_hhi < 0.5,
            current_value=round(m.worker_hhi, 3),
            required_value="< 0.5",
        ),
        GateCheck(
            name="low_errors",
            description="Fewer than 3 errors in last 24 hours",
            passed=m.error_count_last_24h < 3,
            current_value=m.error_count_last_24h,
            required_value="< 3",
        ),
        GateCheck(
            name="tasks_completed",
            description="At least 20 tasks completed via swarm routing",
            passed=m.tasks_completed >= 20,
            current_value=m.tasks_completed,
            required_value=20,
        ),
        GateCheck(
            name="budget_under_control",
            description="Daily spend under 80% of budget",
            passed=(
                m.daily_budget_usd > 0 and m.daily_spend_usd / m.daily_budget_usd < 0.8
            )
            if m.daily_budget_usd > 0
            else True,
            current_value=round(m.daily_spend_usd, 2),
            required_value=f"< {round(m.daily_budget_usd * 0.8, 2)}",
        ),
        GateCheck(
            name="categories_coverage",
            description="Workers in at least 3 task categories",
            passed=m.categories_with_workers >= 3,
            current_value=m.categories_with_workers,
            required_value=3,
            severity="warning",
        ),
    ]


# ─── PhaseGate ────────────────────────────────────────────────


class PhaseGate:
    """
    Manages swarm activation phases and transition gates.

    Usage:
        gate = PhaseGate()
        gate.set_phase(Phase.PRE_FLIGHT)

        metrics = collect_metrics()
        evaluation = gate.evaluate_advance(metrics)
        if evaluation.can_advance:
            gate.advance(metrics, reason="All gates passed")
    """

    def __init__(self, initial_phase: Phase = Phase.PRE_FLIGHT):
        self._phase = initial_phase
        self._phase_start = time.time()
        self._history: list[PhaseTransition] = []
        self._emergency_reason: Optional[str] = None

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def phase_label(self) -> str:
        return PHASE_LABELS.get(self._phase, str(self._phase))

    @property
    def mode(self) -> str:
        """Returns the swarm mode string for the current phase."""
        return PHASE_MODE_MAP.get(self._phase, "disabled")

    @property
    def phase_duration_hours(self) -> float:
        return (time.time() - self._phase_start) / 3600

    @property
    def phase_duration_days(self) -> float:
        return self.phase_duration_hours / 24

    @property
    def history(self) -> list[PhaseTransition]:
        return list(self._history)

    def set_phase(self, phase: Phase, reason: str = "manual set") -> None:
        """Set phase directly (for initialization or manual override)."""
        old = self._phase
        self._phase = phase
        self._phase_start = time.time()
        self._emergency_reason = None

        if old != phase:
            transition = PhaseTransition(
                from_phase=old,
                to_phase=phase,
                reason=reason,
                metrics_snapshot={},
                auto=False,
            )
            self._history.append(transition)
            logger.info(
                "Phase set: %s → %s (reason: %s)",
                PHASE_LABELS.get(old, str(old)),
                PHASE_LABELS.get(phase, str(phase)),
                reason,
            )

    def emergency_stop(self, reason: str = "manual emergency stop") -> None:
        """Immediately transition to EMERGENCY phase."""
        old = self._phase
        self._phase = Phase.EMERGENCY
        self._phase_start = time.time()
        self._emergency_reason = reason

        transition = PhaseTransition(
            from_phase=old,
            to_phase=Phase.EMERGENCY,
            reason=f"EMERGENCY: {reason}",
            metrics_snapshot={},
            auto=True,
        )
        self._history.append(transition)
        logger.critical(
            "EMERGENCY STOP: %s (was: %s)", reason, PHASE_LABELS.get(old, str(old))
        )

    def evaluate_advance(self, metrics: SwarmMetrics) -> PhaseEvaluation:
        """
        Evaluate whether the swarm is ready to advance to the next phase.
        Returns a PhaseEvaluation with gate results.
        """
        if self._phase == Phase.EMERGENCY:
            return PhaseEvaluation(
                current_phase=Phase.EMERGENCY,
                target_phase=Phase.PRE_FLIGHT,
                gates=[
                    GateCheck(
                        name="emergency_cleared",
                        description="Emergency stop must be manually cleared",
                        passed=False,
                        current_value=self._emergency_reason or "emergency active",
                        required_value="manual clear",
                    )
                ],
            )

        if self._phase == Phase.FULL_AUTO:
            return PhaseEvaluation(
                current_phase=Phase.FULL_AUTO,
                target_phase=Phase.FULL_AUTO,
                gates=[
                    GateCheck(
                        name="at_max_phase",
                        description="Already at maximum phase",
                        passed=True,
                        current_value="full_auto",
                        required_value="full_auto",
                    )
                ],
            )

        # Inject days_in_current_phase from gate's own tracking
        metrics.days_in_current_phase = self.phase_duration_days

        target = Phase(self._phase + 1)

        gate_fn = {
            Phase.PRE_FLIGHT: _gates_pre_flight_to_passive,
            Phase.PASSIVE: _gates_passive_to_semi_auto,
            Phase.SEMI_AUTO: _gates_semi_auto_to_full_auto,
        }.get(self._phase)

        if gate_fn is None:
            return PhaseEvaluation(
                current_phase=self._phase,
                target_phase=target,
                gates=[],
            )

        gates = gate_fn(metrics)

        return PhaseEvaluation(
            current_phase=self._phase,
            target_phase=target,
            gates=gates,
        )

    def advance(
        self,
        metrics: SwarmMetrics,
        reason: str = "gates passed",
        force: bool = False,
        auto: bool = False,
    ) -> PhaseTransition | None:
        """
        Advance to the next phase if gates pass (or if forced).
        Returns the transition record, or None if advance was blocked.
        """
        if self._phase == Phase.FULL_AUTO:
            logger.info("Already at Phase 3 (Full Auto), cannot advance further")
            return None

        if self._phase == Phase.EMERGENCY and not force:
            logger.warning("Cannot advance from EMERGENCY without force=True")
            return None

        evaluation = self.evaluate_advance(metrics)

        if not evaluation.can_advance and not force:
            logger.warning(
                "Cannot advance from %s: %d blockers: %s",
                self.phase_label,
                len(evaluation.blockers),
                "; ".join(evaluation.blockers),
            )
            return None

        old_phase = self._phase
        new_phase = (
            Phase(self._phase + 1)
            if self._phase != Phase.EMERGENCY
            else Phase.PRE_FLIGHT
        )

        self._phase = new_phase
        self._phase_start = time.time()
        self._emergency_reason = None

        transition = PhaseTransition(
            from_phase=old_phase,
            to_phase=new_phase,
            reason=reason if not force else f"FORCED: {reason}",
            metrics_snapshot={
                "expiry_rate": metrics.expiry_rate,
                "worker_count": metrics.worker_count,
                "error_count_24h": metrics.error_count_last_24h,
                "tasks_ingested": metrics.tasks_ingested,
                "tasks_completed": metrics.tasks_completed,
                "worker_hhi": metrics.worker_hhi,
            },
            auto=auto,
        )
        self._history.append(transition)

        logger.info(
            "Phase advanced: %s → %s (reason: %s, forced: %s)",
            PHASE_LABELS.get(old_phase, str(old_phase)),
            PHASE_LABELS.get(new_phase, str(new_phase)),
            reason,
            force,
        )

        return transition

    def evaluate_health(self, metrics: SwarmMetrics) -> list[GateCheck]:
        """
        Evaluate health gates for the CURRENT phase.
        If health gates fail, the swarm should consider emergency stop or rollback.
        """
        checks = []

        # Universal health checks (all phases)
        checks.append(
            GateCheck(
                name="api_reachable",
                description="EM API is reachable",
                passed=metrics.api_healthy,
                current_value=metrics.api_healthy,
                required_value=True,
            )
        )

        if self._phase >= Phase.PASSIVE:
            checks.append(
                GateCheck(
                    name="error_rate",
                    description="Error count in last hour < 10",
                    passed=metrics.error_count_last_hour < 10,
                    current_value=metrics.error_count_last_hour,
                    required_value="< 10",
                )
            )

        if self._phase >= Phase.SEMI_AUTO:
            checks.append(
                GateCheck(
                    name="budget_not_exceeded",
                    description="Daily spend not exceeding budget",
                    passed=(
                        metrics.daily_budget_usd == 0
                        or metrics.daily_spend_usd <= metrics.daily_budget_usd
                    ),
                    current_value=round(metrics.daily_spend_usd, 2),
                    required_value=f"<= {round(metrics.daily_budget_usd, 2)}",
                )
            )

            checks.append(
                GateCheck(
                    name="expiry_not_worsening",
                    description="Expiry rate not above 50% (getting worse)",
                    passed=metrics.expiry_rate < 0.50,
                    current_value=round(metrics.expiry_rate, 3),
                    required_value="< 0.50",
                )
            )

        return checks

    def should_emergency_stop(self, metrics: SwarmMetrics) -> tuple[bool, str]:
        """
        Check if conditions warrant an emergency stop.
        Returns (should_stop, reason).
        """
        if self._phase <= Phase.PRE_FLIGHT:
            return False, ""

        # Runaway spending
        if (
            metrics.daily_budget_usd > 0
            and metrics.daily_spend_usd > metrics.daily_budget_usd * 2
        ):
            return (
                True,
                f"Spend ${metrics.daily_spend_usd:.2f} exceeds 2x budget ${metrics.daily_budget_usd:.2f}",
            )

        # Error storm
        if metrics.error_count_last_hour > 50:
            return (
                True,
                f"Error storm: {metrics.error_count_last_hour} errors in last hour",
            )

        # API down for extended period (check via response time > 30s or unhealthy)
        if not metrics.api_healthy and metrics.uptime_hours > 0.5:
            return True, "API unreachable for extended period"

        return False, ""

    def status(self) -> dict:
        """Return complete phase gate status."""
        return {
            "phase": self._phase.value,
            "phase_label": self.phase_label,
            "mode": self.mode,
            "phase_duration_hours": round(self.phase_duration_hours, 2),
            "phase_duration_days": round(self.phase_duration_days, 2),
            "emergency_reason": self._emergency_reason,
            "history_count": len(self._history),
            "last_transition": (self._history[-1].to_dict() if self._history else None),
        }

    def to_dict(self) -> dict:
        """Full serialization including history."""
        return {
            **self.status(),
            "history": [t.to_dict() for t in self._history],
        }
