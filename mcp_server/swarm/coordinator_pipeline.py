"""
CoordinatorPipeline — End-to-End Instrumented Routing Pipeline
===============================================================

Module #52 in the KK V2 Swarm.

Bridges the gap between SignalHarness (signal wiring layer) and
SwarmCoordinator (operational controller). The pipeline wraps the
Coordinator's process_task_queue() with instrumented routing that
flows through the SignalHarness.

Architecture:

    ┌──────────────────────────────────────────────────────┐
    │              CoordinatorPipeline                      │
    │                                                       │
    │  ┌──────────┐   ┌──────────────┐   ┌─────────────┐  │
    │  │QueuedTask│──►│ SignalHarness │──►│  Coordinator │  │
    │  └──────────┘   │  (13 signals) │   │ (assignment) │  │
    │                  └──────────────┘   └─────────────┘  │
    │                          │                    │       │
    │                  ┌───────▼────────┐           │       │
    │                  │DecisionSynth.  │           │       │
    │                  │ (blending)     │           │       │
    │                  └───────┬────────┘           │       │
    │                          │                    │       │
    │                  ┌───────▼────────────────────▼──┐   │
    │                  │     PipelineResult             │   │
    │                  │  (routing + telemetry + audit) │   │
    │                  └───────────────────────────────┘   │
    └──────────────────────────────────────────────────────┘

What this adds over raw Coordinator.process_task_queue():
1. Pre-routing signal evaluation via SignalHarness
2. Post-routing audit trail with signal breakdowns
3. Pipeline-level metrics (throughput, latency, signal coverage)
4. Routing decision explanation for each assignment
5. Warmup/cooldown lifecycle for the signal layer
6. Batch processing with configurable concurrency

Usage:
    from mcp_server.swarm.coordinator_pipeline import CoordinatorPipeline

    pipeline = CoordinatorPipeline(
        coordinator=coordinator,
        signal_harness=harness,
    )

    # Process queue with full instrumentation
    result = pipeline.process()

    # Get pipeline metrics
    metrics = pipeline.metrics()

    # Audit trail
    for entry in result.audit_trail:
        print(f"Task {entry.task_id} → Agent {entry.agent_id}: {entry.explanation}")
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger("em.swarm.coordinator_pipeline")


# ──────────────────────────────────────────────────────────────
# Types
# ──────────────────────────────────────────────────────────────


class PipelinePhase(str, Enum):
    """Phases of the routing pipeline."""

    WARMUP = "warmup"  # Initialize signals, check harness health
    EVALUATE = "evaluate"  # Run SignalHarness pre-scoring
    ROUTE = "route"  # Coordinator.process_task_queue()
    AUDIT = "audit"  # Build audit trail from results
    COOLDOWN = "cooldown"  # Post-routing cleanup


class RoutingVerdict(str, Enum):
    """Classification of routing outcomes."""

    ASSIGNED = "assigned"  # Task routed to an agent
    EXHAUSTED = "exhausted"  # All agents tried, none suitable
    DEFERRED = "deferred"  # Task held for later retry
    SKIPPED = "skipped"  # Task skipped (budget, mode, etc.)
    ERROR = "error"  # Routing threw an exception


@dataclass
class SignalSnapshot:
    """Snapshot of signal state for a single routing decision."""

    connected_signals: int
    active_signals: int  # Signals that returned non-None
    signal_scores: dict[str, float] = field(default_factory=dict)
    signal_latencies: dict[str, float] = field(default_factory=dict)
    total_score: float = 0.0
    coverage_pct: float = 0.0  # % of possible signals that fired


@dataclass
class AuditEntry:
    """Audit trail entry for a single routing decision."""

    task_id: str
    task_title: str
    categories: list[str]
    bounty_usd: float
    verdict: RoutingVerdict
    agent_id: Optional[int] = None
    agent_name: Optional[str] = None
    score: float = 0.0
    signal_snapshot: Optional[SignalSnapshot] = None
    routing_time_ms: float = 0.0
    explanation: str = ""
    attempt_number: int = 1
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "title": self.task_title,
            "categories": self.categories,
            "bounty_usd": self.bounty_usd,
            "verdict": self.verdict.value,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "score": round(self.score, 3),
            "signals": (
                {
                    "connected": self.signal_snapshot.connected_signals,
                    "active": self.signal_snapshot.active_signals,
                    "coverage_pct": round(self.signal_snapshot.coverage_pct, 1),
                    "scores": self.signal_snapshot.signal_scores,
                }
                if self.signal_snapshot
                else None
            ),
            "routing_ms": round(self.routing_time_ms, 1),
            "explanation": self.explanation,
            "attempt": self.attempt_number,
            "timestamp": self.timestamp,
        }


@dataclass
class PipelineResult:
    """Result of a full pipeline execution."""

    cycle_id: int
    started_at: str
    duration_ms: float
    phases_completed: list[str] = field(default_factory=list)
    phases_failed: list[str] = field(default_factory=list)
    tasks_processed: int = 0
    tasks_assigned: int = 0
    tasks_exhausted: int = 0
    tasks_deferred: int = 0
    tasks_errored: int = 0
    audit_trail: list[AuditEntry] = field(default_factory=list)
    harness_status: Optional[dict] = None
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.phases_failed) == 0

    @property
    def assignment_rate(self) -> float:
        if self.tasks_processed == 0:
            return 0.0
        return self.tasks_assigned / self.tasks_processed

    def to_dict(self) -> dict:
        return {
            "cycle_id": self.cycle_id,
            "started_at": self.started_at,
            "duration_ms": round(self.duration_ms, 1),
            "success": self.success,
            "phases": {
                "completed": self.phases_completed,
                "failed": self.phases_failed,
            },
            "tasks": {
                "processed": self.tasks_processed,
                "assigned": self.tasks_assigned,
                "exhausted": self.tasks_exhausted,
                "deferred": self.tasks_deferred,
                "errored": self.tasks_errored,
                "assignment_rate": round(self.assignment_rate, 3),
            },
            "harness": self.harness_status,
            "audit_trail": [a.to_dict() for a in self.audit_trail],
            "errors": self.errors,
        }

    def summary(self) -> str:
        """Human-readable one-line summary."""
        return (
            f"Pipeline #{self.cycle_id}: "
            f"{self.tasks_assigned}/{self.tasks_processed} assigned "
            f"({self.assignment_rate:.0%}), "
            f"{self.duration_ms:.0f}ms, "
            f"{'✅' if self.success else '❌'}"
        )


# ──────────────────────────────────────────────────────────────
# Pipeline Metrics
# ──────────────────────────────────────────────────────────────


@dataclass
class PipelineMetrics:
    """Aggregated metrics across pipeline executions."""

    total_cycles: int = 0
    total_tasks_processed: int = 0
    total_tasks_assigned: int = 0
    total_tasks_exhausted: int = 0
    total_errors: int = 0
    avg_cycle_duration_ms: float = 0.0
    avg_assignment_rate: float = 0.0
    avg_signal_coverage: float = 0.0
    best_assignment_rate: float = 0.0
    worst_assignment_rate: float = 1.0
    consecutive_failures: int = 0

    def to_dict(self) -> dict:
        return {
            "cycles": self.total_cycles,
            "tasks_processed": self.total_tasks_processed,
            "tasks_assigned": self.total_tasks_assigned,
            "tasks_exhausted": self.total_tasks_exhausted,
            "errors": self.total_errors,
            "avg_cycle_ms": round(self.avg_cycle_duration_ms, 1),
            "avg_assignment_rate": round(self.avg_assignment_rate, 3),
            "avg_signal_coverage": round(self.avg_signal_coverage, 3),
            "best_assignment_rate": round(self.best_assignment_rate, 3),
            "worst_assignment_rate": round(self.worst_assignment_rate, 3),
            "consecutive_failures": self.consecutive_failures,
        }


# ──────────────────────────────────────────────────────────────
# CoordinatorPipeline
# ──────────────────────────────────────────────────────────────


class CoordinatorPipeline:
    """
    End-to-end instrumented routing pipeline.

    Wraps SwarmCoordinator with SignalHarness to produce
    fully-audited routing decisions with signal telemetry.
    """

    def __init__(
        self,
        coordinator=None,
        signal_harness=None,
        max_tasks_per_cycle: int = 10,
        min_signal_coverage: float = 0.0,
        explain_decisions: bool = True,
    ):
        """
        Args:
            coordinator: SwarmCoordinator instance
            signal_harness: SignalHarness instance (optional)
            max_tasks_per_cycle: Max tasks to process per pipeline run
            min_signal_coverage: Minimum fraction of signals required (0.0-1.0)
            explain_decisions: Generate human-readable explanations
        """
        self._coordinator = coordinator
        self._harness = signal_harness
        self._max_tasks = max_tasks_per_cycle
        self._min_coverage = min_signal_coverage
        self._explain = explain_decisions

        # Metrics
        self._cycle_count = 0
        self._cycle_durations: deque[float] = deque(maxlen=100)
        self._assignment_rates: deque[float] = deque(maxlen=100)
        self._signal_coverages: deque[float] = deque(maxlen=100)
        self._total_processed = 0
        self._total_assigned = 0
        self._total_exhausted = 0
        self._total_errors = 0
        self._consecutive_failures = 0
        self._created_at = time.time()

        # History
        self._recent_results: deque[PipelineResult] = deque(maxlen=50)

    # ─── Properties ──────────────────────────────────────────

    @property
    def coordinator(self):
        return self._coordinator

    @property
    def signal_harness(self):
        return self._harness

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    # ─── Core Pipeline ───────────────────────────────────────

    def process(
        self,
        strategy=None,
        max_tasks: Optional[int] = None,
    ) -> PipelineResult:
        """
        Execute one full pipeline cycle:
        1. WARMUP: Validate harness health, check signal coverage
        2. EVALUATE: Pre-score candidates through SignalHarness
        3. ROUTE: Run Coordinator.process_task_queue()
        4. AUDIT: Build audit trail with signal breakdowns
        5. COOLDOWN: Update metrics, record history

        Returns PipelineResult with full telemetry.
        """
        self._cycle_count += 1
        start = time.monotonic()
        now = datetime.now(timezone.utc)

        result = PipelineResult(
            cycle_id=self._cycle_count,
            started_at=now.isoformat(),
            duration_ms=0,
        )

        max_to_process = max_tasks or self._max_tasks

        # ── Phase 1: WARMUP ────────────────────────────────
        try:
            warmup_ok = self._phase_warmup(result)
            if not warmup_ok:
                result.duration_ms = (time.monotonic() - start) * 1000
                self._record_result(result)
                return result
        except Exception as e:
            result.phases_failed.append(PipelinePhase.WARMUP.value)
            result.errors.append(f"warmup: {e}")
            logger.error(f"Pipeline warmup failed: {e}")
            result.duration_ms = (time.monotonic() - start) * 1000
            self._record_result(result)
            return result

        # ── Phase 2: EVALUATE ──────────────────────────────
        try:
            self._phase_evaluate(result)
        except Exception as e:
            result.phases_failed.append(PipelinePhase.EVALUATE.value)
            result.errors.append(f"evaluate: {e}")
            logger.error(f"Pipeline evaluate failed: {e}")
            # Non-fatal — routing can proceed without pre-evaluation

        # ── Phase 3: ROUTE ─────────────────────────────────
        try:
            self._phase_route(result, strategy, max_to_process)
        except Exception as e:
            result.phases_failed.append(PipelinePhase.ROUTE.value)
            result.errors.append(f"route: {e}")
            logger.error(f"Pipeline route failed: {e}")

        # ── Phase 4: AUDIT ─────────────────────────────────
        try:
            self._phase_audit(result)
        except Exception as e:
            result.phases_failed.append(PipelinePhase.AUDIT.value)
            result.errors.append(f"audit: {e}")
            logger.error(f"Pipeline audit failed: {e}")

        # ── Phase 5: COOLDOWN ──────────────────────────────
        try:
            self._phase_cooldown(result)
        except Exception as e:
            result.phases_failed.append(PipelinePhase.COOLDOWN.value)
            result.errors.append(f"cooldown: {e}")
            logger.error(f"Pipeline cooldown failed: {e}")

        result.duration_ms = (time.monotonic() - start) * 1000

        # Record duration AFTER it's computed
        self._cycle_durations.append(result.duration_ms)

        self._record_result(result)

        logger.info(result.summary())
        return result

    def _phase_warmup(self, result: PipelineResult) -> bool:
        """
        Phase 1: Validate pipeline readiness.

        Checks:
        - Coordinator is available
        - SignalHarness is connected (if required)
        - Signal coverage meets minimum threshold
        """
        if self._coordinator is None:
            result.phases_failed.append(PipelinePhase.WARMUP.value)
            result.errors.append("No coordinator configured")
            return False

        # Check harness health
        if self._harness is not None:
            harness_health = self._harness.health_summary()
            result.harness_status = self._harness.status()

            if not harness_health.get("healthy", True):
                logger.warning(
                    "SignalHarness degraded: %d/%d signals healthy",
                    harness_health.get("healthy_signals", 0),
                    harness_health.get("connected", 0),
                )

            # Check minimum coverage
            status = result.harness_status
            coverage = status.get("coverage", 0.0)
            if coverage < self._min_coverage:
                result.phases_failed.append(PipelinePhase.WARMUP.value)
                result.errors.append(
                    f"Signal coverage {coverage:.1%} below minimum {self._min_coverage:.1%}"
                )
                return False

        result.phases_completed.append(PipelinePhase.WARMUP.value)
        return True

    def _phase_evaluate(self, result: PipelineResult) -> None:
        """
        Phase 2: Pre-evaluate signal readiness.

        If a SignalHarness is connected, capture its current state
        for the audit trail. This doesn't change routing behavior —
        it provides observability into what signals are live.
        """
        if self._harness is None:
            result.phases_completed.append(PipelinePhase.EVALUATE.value)
            return

        status = self._harness.status()
        connected = status.get("connected", 0)
        available = status.get("available", 0)

        logger.info(
            "Signal evaluation: %d/%d signals connected (%.0f%% coverage)",
            connected,
            available,
            status.get("coverage", 0) * 100,
        )

        result.phases_completed.append(PipelinePhase.EVALUATE.value)

    def _is_assignment(self, r) -> bool:
        """Check if a routing result is an assignment (duck-typed)."""
        return (
            hasattr(r, "agent_id") and hasattr(r, "score") and hasattr(r, "agent_name")
        )

    def _is_failure(self, r) -> bool:
        """Check if a routing result is a failure (duck-typed)."""
        return hasattr(r, "reason") and not self._is_assignment(r)

    def _phase_route(
        self,
        result: PipelineResult,
        strategy,
        max_tasks: int,
    ) -> None:
        """
        Phase 3: Route tasks through the Coordinator.

        Delegates to Coordinator.process_task_queue() and captures
        results for audit trail construction. Uses duck typing to
        identify Assignment vs RoutingFailure results.
        """
        route_results = self._coordinator.process_task_queue(
            strategy=strategy,
            max_tasks=max_tasks,
        )

        for r in route_results:
            result.tasks_processed += 1

            if self._is_assignment(r):
                result.tasks_assigned += 1

                # Build signal snapshot from harness
                snapshot = self._capture_signal_snapshot()

                # Build audit entry
                entry = AuditEntry(
                    task_id=r.task_id,
                    task_title=r.task_title if hasattr(r, "task_title") else "",
                    categories=r.categories if hasattr(r, "categories") else [],
                    bounty_usd=r.bounty_usd if hasattr(r, "bounty_usd") else 0.0,
                    verdict=RoutingVerdict.ASSIGNED,
                    agent_id=r.agent_id,
                    agent_name=r.agent_name,
                    score=r.score,
                    signal_snapshot=snapshot,
                    routing_time_ms=r.routing_time_ms
                    if hasattr(r, "routing_time_ms")
                    else 0.0,
                    explanation=self._explain_assignment(r) if self._explain else "",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                result.audit_trail.append(entry)

            elif self._is_failure(r):
                result.tasks_exhausted += 1

                entry = AuditEntry(
                    task_id=r.task_id,
                    task_title=r.task_title if hasattr(r, "task_title") else "",
                    categories=r.categories if hasattr(r, "categories") else [],
                    bounty_usd=r.bounty_usd if hasattr(r, "bounty_usd") else 0.0,
                    verdict=RoutingVerdict.EXHAUSTED,
                    explanation=r.reason if hasattr(r, "reason") else "Unknown",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                result.audit_trail.append(entry)

        result.phases_completed.append(PipelinePhase.ROUTE.value)

    def _phase_audit(self, result: PipelineResult) -> None:
        """
        Phase 4: Finalize audit trail.

        Adds summary statistics and signal coverage info.
        """
        if self._harness:
            result.harness_status = self._harness.status()

        result.phases_completed.append(PipelinePhase.AUDIT.value)

    def _phase_cooldown(self, result: PipelineResult) -> None:
        """
        Phase 5: Update pipeline metrics and history.
        """
        # Update aggregates
        self._total_processed += result.tasks_processed
        self._total_assigned += result.tasks_assigned
        self._total_exhausted += result.tasks_exhausted
        self._total_errors += len(result.errors)

        self._assignment_rates.append(result.assignment_rate)

        if self._harness and result.harness_status:
            self._signal_coverages.append(result.harness_status.get("coverage", 0.0))

        if result.success:
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1

        result.phases_completed.append(PipelinePhase.COOLDOWN.value)

    # ─── Signal Helpers ──────────────────────────────────────

    def _capture_signal_snapshot(self) -> Optional[SignalSnapshot]:
        """Capture current signal state from the harness."""
        if self._harness is None:
            return None

        status = self._harness.status()
        signals = status.get("signals", {})

        scores = {}
        latencies = {}
        active = 0

        for name, info in signals.items():
            if info.get("calls", 0) > 0:
                active += 1
            latencies[name] = info.get("avg_latency_ms", 0.0)
            # Signal weight as proxy for relative importance
            scores[name] = info.get("weight", 0.0)

        connected = status.get("connected", 0)
        available = status.get("available", 1)

        return SignalSnapshot(
            connected_signals=connected,
            active_signals=active,
            signal_scores=scores,
            signal_latencies=latencies,
            coverage_pct=(connected / max(1, available)) * 100,
        )

    def _explain_assignment(self, assignment) -> str:
        """Generate a human-readable explanation of why this agent was chosen."""
        parts = [f"Agent {assignment.agent_name} (ID {assignment.agent_id})"]
        parts.append(f"scored {assignment.score:.2f}")

        if hasattr(assignment, "strategy_used"):
            parts.append(f"via {assignment.strategy_used.value} strategy")

        if self._harness:
            health = self._harness.health_summary()
            connected = health.get("connected", 0)
            parts.append(f"with {connected} signals active")

        return " ".join(parts)

    # ─── Metrics ─────────────────────────────────────────────

    def metrics(self) -> PipelineMetrics:
        """Compute aggregated pipeline metrics."""
        m = PipelineMetrics(
            total_cycles=self._cycle_count,
            total_tasks_processed=self._total_processed,
            total_tasks_assigned=self._total_assigned,
            total_tasks_exhausted=self._total_exhausted,
            total_errors=self._total_errors,
            consecutive_failures=self._consecutive_failures,
        )

        if self._cycle_durations:
            m.avg_cycle_duration_ms = sum(self._cycle_durations) / len(
                self._cycle_durations
            )

        if self._assignment_rates:
            rates = list(self._assignment_rates)
            m.avg_assignment_rate = sum(rates) / len(rates)
            m.best_assignment_rate = max(rates)
            m.worst_assignment_rate = min(rates)

        if self._signal_coverages:
            m.avg_signal_coverage = sum(self._signal_coverages) / len(
                self._signal_coverages
            )

        return m

    # ─── History ─────────────────────────────────────────────

    def recent_results(self, limit: int = 10) -> list[dict]:
        """Get recent pipeline results."""
        return [r.to_dict() for r in list(self._recent_results)[-limit:]]

    def _record_result(self, result: PipelineResult) -> None:
        """Store result in history."""
        self._recent_results.append(result)

    # ─── Diagnostics ─────────────────────────────────────────

    def status(self) -> dict:
        """Full pipeline diagnostic status."""
        return {
            "running": self._coordinator is not None,
            "cycle_count": self._cycle_count,
            "uptime_seconds": round(time.time() - self._created_at, 1),
            "coordinator": self._coordinator is not None,
            "signal_harness": self._harness is not None,
            "config": {
                "max_tasks_per_cycle": self._max_tasks,
                "min_signal_coverage": self._min_coverage,
                "explain_decisions": self._explain,
            },
            "metrics": self.metrics().to_dict(),
            "harness_health": (
                self._harness.health_summary() if self._harness else None
            ),
        }

    def health_check(self) -> dict:
        """Quick health check."""
        healthy = True
        issues = []

        if self._coordinator is None:
            healthy = False
            issues.append("No coordinator")

        if self._consecutive_failures >= 3:
            healthy = False
            issues.append(f"{self._consecutive_failures} consecutive failures")

        if self._harness:
            harness_health = self._harness.health_summary()
            if not harness_health.get("healthy", True):
                issues.append("SignalHarness degraded")

        return {
            "healthy": healthy,
            "issues": issues,
            "cycles": self._cycle_count,
            "assignment_rate": (
                round(self._total_assigned / max(1, self._total_processed), 3)
            ),
        }

    def __repr__(self) -> str:
        return (
            f"CoordinatorPipeline("
            f"cycles={self._cycle_count}, "
            f"processed={self._total_processed}, "
            f"assigned={self._total_assigned})"
        )
