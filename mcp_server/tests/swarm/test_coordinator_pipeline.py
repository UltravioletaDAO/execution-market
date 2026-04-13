"""
Tests for CoordinatorPipeline — Module #52
============================================

Tests cover:
1. Pipeline lifecycle (warmup, evaluate, route, audit, cooldown)
2. Signal harness integration
3. Audit trail generation
4. Metrics aggregation
5. Health checks and diagnostics
6. Graceful degradation (missing harness, missing coordinator)
7. Multiple cycle behavior
8. Edge cases (empty queue, all failures, etc.)
"""

import time
from unittest.mock import MagicMock

from mcp_server.swarm.coordinator_pipeline import (
    CoordinatorPipeline,
    PipelinePhase,
    PipelineResult,
    PipelineMetrics,
    RoutingVerdict,
    AuditEntry,
    SignalSnapshot,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


class MockAssignment:
    """Mock for orchestrator.Assignment."""

    def __init__(self, task_id="t1", agent_id=1, agent_name="Alpha", score=0.85):
        self.task_id = task_id
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.score = score
        self.task_title = f"Task {task_id}"
        self.categories = ["physical_verification"]
        self.bounty_usd = 0.25
        self.routing_time_ms = 12.5
        self.strategy_used = MagicMock(value="best_fit")


class MockRoutingFailure:
    """Mock for orchestrator.RoutingFailure."""

    def __init__(self, task_id="t2", reason="No agents available"):
        self.task_id = task_id
        self.task_title = f"Task {task_id}"
        self.categories = ["delivery"]
        self.bounty_usd = 0.15
        self.reason = reason


def make_coordinator(results=None):
    """Create a mock coordinator."""
    coord = MagicMock()
    if results is None:
        results = [MockAssignment()]
    coord.process_task_queue.return_value = results
    return coord


def make_harness(connected=3, available=13, healthy=True, coverage=0.23):
    """Create a mock signal harness."""
    harness = MagicMock()
    harness.health_summary.return_value = {
        "healthy": healthy,
        "connected": connected,
        "healthy_signals": connected if healthy else connected - 1,
        "degraded_signals": 0 if healthy else 1,
    }
    harness.status.return_value = {
        "connected": connected,
        "available": available,
        "coverage": coverage,
        "total_calls": 100,
        "total_errors": 2,
        "uptime_seconds": 300.0,
        "signals": {
            "reputation": {
                "source": "ReputationBridge",
                "calls": 50,
                "errors": 1,
                "avg_latency_ms": 0.5,
                "weight": 0.15,
            },
            "skill_match": {
                "source": "SkillMatcher",
                "calls": 30,
                "errors": 0,
                "avg_latency_ms": 0.3,
                "weight": 0.12,
            },
            "verification_quality": {
                "source": "VerificationAdapter",
                "calls": 20,
                "errors": 1,
                "avg_latency_ms": 0.8,
                "weight": 0.08,
            },
        },
    }
    return harness


# ──────────────────────────────────────────────────────────────
# Test Class: Pipeline Lifecycle
# ──────────────────────────────────────────────────────────────


class TestPipelineLifecycle:
    """Tests for basic pipeline creation and lifecycle."""

    def test_create_minimal(self):
        """Pipeline can be created with no arguments."""
        pipeline = CoordinatorPipeline()
        assert pipeline.coordinator is None
        assert pipeline.signal_harness is None
        assert pipeline.cycle_count == 0

    def test_create_with_coordinator(self):
        """Pipeline with just a coordinator (no harness)."""
        coord = make_coordinator()
        pipeline = CoordinatorPipeline(coordinator=coord)
        assert pipeline.coordinator is coord
        assert pipeline.signal_harness is None

    def test_create_with_both(self):
        """Pipeline with coordinator + signal harness."""
        coord = make_coordinator()
        harness = make_harness()
        pipeline = CoordinatorPipeline(coordinator=coord, signal_harness=harness)
        assert pipeline.coordinator is coord
        assert pipeline.signal_harness is harness

    def test_cycle_count_increments(self):
        """Each process() call increments cycle count."""
        coord = make_coordinator([])
        pipeline = CoordinatorPipeline(coordinator=coord)

        pipeline.process()
        assert pipeline.cycle_count == 1

        pipeline.process()
        assert pipeline.cycle_count == 2

        pipeline.process()
        assert pipeline.cycle_count == 3


# ──────────────────────────────────────────────────────────────
# Test Class: Pipeline Phases
# ──────────────────────────────────────────────────────────────


class TestPipelinePhases:
    """Tests for individual pipeline phases."""

    def test_all_phases_complete_happy_path(self):
        """All 5 phases complete when everything works."""
        coord = make_coordinator([MockAssignment()])
        harness = make_harness()
        pipeline = CoordinatorPipeline(coordinator=coord, signal_harness=harness)

        result = pipeline.process()

        assert result.success
        assert PipelinePhase.WARMUP.value in result.phases_completed
        assert PipelinePhase.EVALUATE.value in result.phases_completed
        assert PipelinePhase.ROUTE.value in result.phases_completed
        assert PipelinePhase.AUDIT.value in result.phases_completed
        assert PipelinePhase.COOLDOWN.value in result.phases_completed
        assert len(result.phases_failed) == 0

    def test_warmup_fails_without_coordinator(self):
        """Warmup fails and aborts when no coordinator."""
        pipeline = CoordinatorPipeline()
        result = pipeline.process()

        assert not result.success
        assert PipelinePhase.WARMUP.value in result.phases_failed
        assert "No coordinator" in result.errors[0]

    def test_warmup_fails_insufficient_coverage(self):
        """Warmup fails when signal coverage below threshold."""
        coord = make_coordinator([])
        harness = make_harness(coverage=0.1)  # 10%
        pipeline = CoordinatorPipeline(
            coordinator=coord,
            signal_harness=harness,
            min_signal_coverage=0.5,  # Require 50%
        )

        result = pipeline.process()

        assert not result.success
        assert PipelinePhase.WARMUP.value in result.phases_failed
        assert "coverage" in result.errors[0].lower()

    def test_evaluate_succeeds_without_harness(self):
        """Evaluate phase succeeds even without harness."""
        coord = make_coordinator([])
        pipeline = CoordinatorPipeline(coordinator=coord)
        result = pipeline.process()

        assert PipelinePhase.EVALUATE.value in result.phases_completed

    def test_route_delegates_to_coordinator(self):
        """Route phase calls coordinator.process_task_queue()."""
        coord = make_coordinator([MockAssignment()])
        pipeline = CoordinatorPipeline(coordinator=coord)

        result = pipeline.process()

        coord.process_task_queue.assert_called_once()
        assert result.tasks_assigned == 1

    def test_route_with_custom_strategy(self):
        """Route phase passes strategy to coordinator."""
        coord = make_coordinator([])
        pipeline = CoordinatorPipeline(coordinator=coord)

        mock_strategy = MagicMock()
        pipeline.process(strategy=mock_strategy)

        coord.process_task_queue.assert_called_with(
            strategy=mock_strategy, max_tasks=10
        )

    def test_route_with_custom_max_tasks(self):
        """Route phase respects max_tasks override."""
        coord = make_coordinator([])
        pipeline = CoordinatorPipeline(coordinator=coord)

        pipeline.process(max_tasks=5)

        coord.process_task_queue.assert_called_with(strategy=None, max_tasks=5)


# ──────────────────────────────────────────────────────────────
# Test Class: Routing Results
# ──────────────────────────────────────────────────────────────


class TestRoutingResults:
    """Tests for processing routing outcomes."""

    def test_single_assignment(self):
        """Single successful assignment produces audit entry."""
        assignment = MockAssignment(task_id="t1", agent_id=42, score=0.92)
        coord = make_coordinator([assignment])
        pipeline = CoordinatorPipeline(coordinator=coord)

        result = pipeline.process()

        assert result.tasks_processed == 1
        assert result.tasks_assigned == 1
        assert result.tasks_exhausted == 0
        assert len(result.audit_trail) == 1

        entry = result.audit_trail[0]
        assert entry.task_id == "t1"
        assert entry.agent_id == 42
        assert entry.score == 0.92
        assert entry.verdict == RoutingVerdict.ASSIGNED

    def test_single_failure(self):
        """Single routing failure produces audit entry."""
        failure = MockRoutingFailure(task_id="t2", reason="Budget exceeded")
        coord = make_coordinator([failure])
        pipeline = CoordinatorPipeline(coordinator=coord)

        result = pipeline.process()

        assert result.tasks_processed == 1
        assert result.tasks_assigned == 0
        assert result.tasks_exhausted == 1
        assert len(result.audit_trail) == 1

        entry = result.audit_trail[0]
        assert entry.task_id == "t2"
        assert entry.verdict == RoutingVerdict.EXHAUSTED
        assert entry.explanation == "Budget exceeded"

    def test_mixed_results(self):
        """Mix of assignments and failures."""
        results = [
            MockAssignment(task_id="t1", agent_id=1),
            MockRoutingFailure(task_id="t2"),
            MockAssignment(task_id="t3", agent_id=2),
            MockRoutingFailure(task_id="t4"),
            MockAssignment(task_id="t5", agent_id=3),
        ]
        coord = make_coordinator(results)
        pipeline = CoordinatorPipeline(coordinator=coord)

        result = pipeline.process()

        assert result.tasks_processed == 5
        assert result.tasks_assigned == 3
        assert result.tasks_exhausted == 2
        assert result.assignment_rate == 0.6

    def test_empty_queue(self):
        """Empty queue produces zero-task result."""
        coord = make_coordinator([])
        pipeline = CoordinatorPipeline(coordinator=coord)

        result = pipeline.process()

        assert result.tasks_processed == 0
        assert result.tasks_assigned == 0
        assert result.assignment_rate == 0.0
        assert len(result.audit_trail) == 0
        assert result.success


# ──────────────────────────────────────────────────────────────
# Test Class: Audit Trail
# ──────────────────────────────────────────────────────────────


class TestAuditTrail:
    """Tests for audit trail generation."""

    def test_audit_entry_serialization(self):
        """AuditEntry.to_dict() produces valid output."""
        entry = AuditEntry(
            task_id="t1",
            task_title="Test Task",
            categories=["physical"],
            bounty_usd=0.25,
            verdict=RoutingVerdict.ASSIGNED,
            agent_id=42,
            agent_name="Alpha",
            score=0.85,
            routing_time_ms=12.3,
            explanation="Best match",
            timestamp="2026-03-29T06:00:00Z",
        )

        d = entry.to_dict()
        assert d["task_id"] == "t1"
        assert d["verdict"] == "assigned"
        assert d["agent_id"] == 42
        assert d["score"] == 0.85
        assert d["routing_ms"] == 12.3

    def test_audit_entry_with_signal_snapshot(self):
        """AuditEntry includes signal snapshot when available."""
        snapshot = SignalSnapshot(
            connected_signals=5,
            active_signals=4,
            signal_scores={"reputation": 0.15, "skill_match": 0.12},
            coverage_pct=38.5,
        )
        entry = AuditEntry(
            task_id="t1",
            task_title="Test",
            categories=[],
            bounty_usd=0.0,
            verdict=RoutingVerdict.ASSIGNED,
            signal_snapshot=snapshot,
        )

        d = entry.to_dict()
        assert d["signals"]["connected"] == 5
        assert d["signals"]["active"] == 4
        assert d["signals"]["coverage_pct"] == 38.5

    def test_audit_trail_with_harness(self):
        """Audit trail includes signal snapshots when harness present."""
        coord = make_coordinator([MockAssignment()])
        harness = make_harness()
        pipeline = CoordinatorPipeline(coordinator=coord, signal_harness=harness)

        result = pipeline.process()

        assert len(result.audit_trail) == 1
        entry = result.audit_trail[0]
        assert entry.signal_snapshot is not None
        assert entry.signal_snapshot.connected_signals == 3

    def test_explain_decisions_flag(self):
        """Explanations generated when explain_decisions=True."""
        coord = make_coordinator([MockAssignment(agent_name="TestBot")])
        pipeline = CoordinatorPipeline(coordinator=coord, explain_decisions=True)

        result = pipeline.process()

        entry = result.audit_trail[0]
        assert "TestBot" in entry.explanation
        assert "scored" in entry.explanation

    def test_no_explain_when_disabled(self):
        """No explanations when explain_decisions=False."""
        coord = make_coordinator([MockAssignment()])
        pipeline = CoordinatorPipeline(coordinator=coord, explain_decisions=False)

        result = pipeline.process()

        entry = result.audit_trail[0]
        assert entry.explanation == ""


# ──────────────────────────────────────────────────────────────
# Test Class: Pipeline Metrics
# ──────────────────────────────────────────────────────────────


class TestPipelineMetrics:
    """Tests for metrics aggregation across cycles."""

    def test_initial_metrics(self):
        """Fresh pipeline has zero metrics."""
        pipeline = CoordinatorPipeline()
        m = pipeline.metrics()

        assert m.total_cycles == 0
        assert m.total_tasks_processed == 0
        assert m.total_tasks_assigned == 0
        assert m.avg_cycle_duration_ms == 0.0

    def test_metrics_accumulate(self):
        """Metrics accumulate across multiple cycles."""
        coord = make_coordinator([MockAssignment()])
        pipeline = CoordinatorPipeline(coordinator=coord)

        pipeline.process()
        pipeline.process()
        pipeline.process()

        m = pipeline.metrics()
        assert m.total_cycles == 3
        assert m.total_tasks_processed == 3
        assert m.total_tasks_assigned == 3
        assert m.avg_assignment_rate == 1.0

    def test_metrics_track_failures(self):
        """Metrics track exhausted tasks."""
        coord = make_coordinator([MockRoutingFailure()])
        pipeline = CoordinatorPipeline(coordinator=coord)

        pipeline.process()

        m = pipeline.metrics()
        assert m.total_tasks_exhausted == 1
        assert m.total_tasks_assigned == 0

    def test_metrics_best_worst_rates(self):
        """Metrics track best/worst assignment rates."""
        pipeline = CoordinatorPipeline()

        # Cycle 1: 100% assignment rate
        coord1 = make_coordinator([MockAssignment()])
        pipeline._coordinator = coord1
        pipeline.process()

        # Cycle 2: 0% assignment rate
        coord2 = make_coordinator([MockRoutingFailure()])
        pipeline._coordinator = coord2
        pipeline.process()

        # Cycle 3: 50% rate
        coord3 = make_coordinator([MockAssignment(), MockRoutingFailure()])
        pipeline._coordinator = coord3
        pipeline.process()

        m = pipeline.metrics()
        assert m.best_assignment_rate == 1.0
        assert m.worst_assignment_rate == 0.0

    def test_metrics_serialization(self):
        """PipelineMetrics.to_dict() produces clean output."""
        m = PipelineMetrics(
            total_cycles=10,
            total_tasks_processed=50,
            total_tasks_assigned=35,
            avg_assignment_rate=0.7,
        )
        d = m.to_dict()
        assert d["cycles"] == 10
        assert d["tasks_processed"] == 50
        assert d["avg_assignment_rate"] == 0.7


# ──────────────────────────────────────────────────────────────
# Test Class: Pipeline Result
# ──────────────────────────────────────────────────────────────


class TestPipelineResult:
    """Tests for PipelineResult data structure."""

    def test_success_when_no_failures(self):
        """Result is successful when no phases failed."""
        r = PipelineResult(
            cycle_id=1,
            started_at="2026-03-29T06:00:00Z",
            duration_ms=15.0,
            phases_completed=["warmup", "route", "cooldown"],
        )
        assert r.success

    def test_failure_when_phase_fails(self):
        """Result is not successful when any phase failed."""
        r = PipelineResult(
            cycle_id=1,
            started_at="2026-03-29T06:00:00Z",
            duration_ms=15.0,
            phases_completed=["warmup"],
            phases_failed=["route"],
        )
        assert not r.success

    def test_assignment_rate_zero_division(self):
        """Assignment rate is 0 when no tasks processed."""
        r = PipelineResult(
            cycle_id=1,
            started_at="2026-03-29T06:00:00Z",
            duration_ms=0,
        )
        assert r.assignment_rate == 0.0

    def test_summary_string(self):
        """Summary produces human-readable string."""
        r = PipelineResult(
            cycle_id=5,
            started_at="2026-03-29T06:00:00Z",
            duration_ms=42.5,
            tasks_processed=10,
            tasks_assigned=7,
        )
        s = r.summary()
        assert "#5" in s
        assert "7/10" in s
        assert "42ms" in s

    def test_to_dict_serialization(self):
        """PipelineResult.to_dict() has all expected fields."""
        r = PipelineResult(
            cycle_id=1,
            started_at="2026-03-29T06:00:00Z",
            duration_ms=10.0,
            phases_completed=["warmup", "route"],
            tasks_processed=3,
            tasks_assigned=2,
        )
        d = r.to_dict()
        assert d["cycle_id"] == 1
        assert d["tasks"]["processed"] == 3
        assert d["tasks"]["assigned"] == 2
        assert d["tasks"]["assignment_rate"] == 0.667


# ──────────────────────────────────────────────────────────────
# Test Class: Signal Harness Integration
# ──────────────────────────────────────────────────────────────


class TestSignalHarnessIntegration:
    """Tests for pipeline + signal harness behavior."""

    def test_harness_status_captured(self):
        """Pipeline captures harness status in result."""
        coord = make_coordinator([])
        harness = make_harness(connected=5)
        pipeline = CoordinatorPipeline(coordinator=coord, signal_harness=harness)

        result = pipeline.process()

        assert result.harness_status is not None
        assert result.harness_status["connected"] == 5

    def test_harness_health_logged(self):
        """Degraded harness doesn't block pipeline (just warns)."""
        coord = make_coordinator([MockAssignment()])
        harness = make_harness(healthy=False)
        pipeline = CoordinatorPipeline(coordinator=coord, signal_harness=harness)

        result = pipeline.process()

        # Should still succeed — degraded harness is a warning, not a blocker
        assert result.success
        assert result.tasks_assigned == 1

    def test_signal_coverage_tracked_in_metrics(self):
        """Signal coverage is tracked across cycles."""
        coord = make_coordinator([])
        harness = make_harness(coverage=0.5)
        pipeline = CoordinatorPipeline(coordinator=coord, signal_harness=harness)

        pipeline.process()
        pipeline.process()

        m = pipeline.metrics()
        assert m.avg_signal_coverage == 0.5

    def test_snapshot_populated_for_assignments(self):
        """Signal snapshots are captured for each assignment."""
        assignment = MockAssignment()
        coord = make_coordinator([assignment])
        harness = make_harness(connected=3, available=13)
        pipeline = CoordinatorPipeline(coordinator=coord, signal_harness=harness)

        result = pipeline.process()

        entry = result.audit_trail[0]
        snap = entry.signal_snapshot
        assert snap is not None
        assert snap.connected_signals == 3
        assert "reputation" in snap.signal_scores


# ──────────────────────────────────────────────────────────────
# Test Class: Graceful Degradation
# ──────────────────────────────────────────────────────────────


class TestGracefulDegradation:
    """Tests for pipeline behavior under failure conditions."""

    def test_routing_exception_captured(self):
        """Exception in coordinator.process_task_queue is captured."""
        coord = MagicMock()
        coord.process_task_queue.side_effect = RuntimeError("DB connection lost")
        pipeline = CoordinatorPipeline(coordinator=coord)

        result = pipeline.process()

        assert PipelinePhase.ROUTE.value in result.phases_failed
        assert "DB connection lost" in result.errors[0]

    def test_consecutive_failures_tracked(self):
        """Consecutive failures counter increases."""
        coord = MagicMock()
        coord.process_task_queue.side_effect = RuntimeError("fail")
        pipeline = CoordinatorPipeline(coordinator=coord)

        pipeline.process()
        assert pipeline._consecutive_failures == 1

        pipeline.process()
        assert pipeline._consecutive_failures == 2

    def test_consecutive_failures_reset_on_success(self):
        """Successful cycle resets consecutive failure counter."""
        # First: fail
        coord = MagicMock()
        coord.process_task_queue.side_effect = RuntimeError("fail")
        pipeline = CoordinatorPipeline(coordinator=coord)
        pipeline.process()
        assert pipeline._consecutive_failures == 1

        # Then: succeed
        coord.process_task_queue.side_effect = None
        coord.process_task_queue.return_value = []
        pipeline.process()
        assert pipeline._consecutive_failures == 0

    def test_health_check_detects_issues(self):
        """Health check reports issues accurately."""
        pipeline = CoordinatorPipeline()
        health = pipeline.health_check()
        assert not health["healthy"]
        assert "No coordinator" in health["issues"]

    def test_health_check_detects_consecutive_failures(self):
        """Health check flags consecutive failures."""
        coord = MagicMock()
        coord.process_task_queue.side_effect = RuntimeError("fail")
        pipeline = CoordinatorPipeline(coordinator=coord)

        for _ in range(3):
            pipeline.process()

        health = pipeline.health_check()
        assert not health["healthy"]
        assert any("consecutive" in i for i in health["issues"])


# ──────────────────────────────────────────────────────────────
# Test Class: History
# ──────────────────────────────────────────────────────────────


class TestHistory:
    """Tests for pipeline result history."""

    def test_recent_results_empty(self):
        """Empty pipeline has no history."""
        pipeline = CoordinatorPipeline()
        assert pipeline.recent_results() == []

    def test_recent_results_accumulated(self):
        """Results accumulate in history."""
        coord = make_coordinator([])
        pipeline = CoordinatorPipeline(coordinator=coord)

        for _ in range(5):
            pipeline.process()

        history = pipeline.recent_results()
        assert len(history) == 5

    def test_recent_results_limited(self):
        """History respects limit parameter."""
        coord = make_coordinator([])
        pipeline = CoordinatorPipeline(coordinator=coord)

        for _ in range(10):
            pipeline.process()

        history = pipeline.recent_results(limit=3)
        assert len(history) == 3

    def test_history_capped_at_50(self):
        """History deque never exceeds 50 entries."""
        coord = make_coordinator([])
        pipeline = CoordinatorPipeline(coordinator=coord)

        for _ in range(60):
            pipeline.process()

        assert len(pipeline._recent_results) == 50


# ──────────────────────────────────────────────────────────────
# Test Class: Diagnostics
# ──────────────────────────────────────────────────────────────


class TestDiagnostics:
    """Tests for pipeline diagnostic methods."""

    def test_status_output(self):
        """status() returns comprehensive dict."""
        coord = make_coordinator([])
        harness = make_harness()
        pipeline = CoordinatorPipeline(coordinator=coord, signal_harness=harness)

        s = pipeline.status()
        assert s["running"] is True
        assert s["coordinator"] is True
        assert s["signal_harness"] is True
        assert "config" in s
        assert "metrics" in s
        assert "harness_health" in s

    def test_repr(self):
        """__repr__ returns informative string."""
        pipeline = CoordinatorPipeline()
        r = repr(pipeline)
        assert "CoordinatorPipeline" in r
        assert "cycles=0" in r

    def test_health_check_healthy(self):
        """Health check reports healthy when all OK."""
        coord = make_coordinator([])
        harness = make_harness(healthy=True)
        pipeline = CoordinatorPipeline(coordinator=coord, signal_harness=harness)

        health = pipeline.health_check()
        assert health["healthy"]
        assert health["issues"] == []


# ──────────────────────────────────────────────────────────────
# Test Class: Duration and Timing
# ──────────────────────────────────────────────────────────────


class TestTimingMetrics:
    """Tests for timing-related metrics."""

    def test_duration_recorded(self):
        """Pipeline records execution duration."""
        coord = make_coordinator([])
        pipeline = CoordinatorPipeline(coordinator=coord)

        result = pipeline.process()

        assert result.duration_ms >= 0
        assert result.duration_ms < 5000  # Should be fast in tests

    def test_avg_duration_computed(self):
        """Average cycle duration computed from history."""
        coord = make_coordinator([])
        pipeline = CoordinatorPipeline(coordinator=coord)

        for _ in range(5):
            pipeline.process()

        m = pipeline.metrics()
        assert m.avg_cycle_duration_ms >= 0

    def test_uptime_tracked(self):
        """Status reports uptime since creation."""
        pipeline = CoordinatorPipeline()
        time.sleep(0.02)
        s = pipeline.status()
        assert s["uptime_seconds"] >= 0.0


# ──────────────────────────────────────────────────────────────
# Test Class: End-to-End Pipeline Scenarios
# ──────────────────────────────────────────────────────────────


class TestEndToEndScenarios:
    """Full pipeline scenarios combining multiple features."""

    def test_production_scenario_mixed_routing(self):
        """Simulate production scenario with mixed routing outcomes."""
        results = [
            MockAssignment(task_id="t1", agent_id=1, score=0.95),
            MockAssignment(task_id="t2", agent_id=2, score=0.72),
            MockRoutingFailure(task_id="t3", reason="No budget"),
            MockAssignment(task_id="t4", agent_id=3, score=0.88),
            MockRoutingFailure(task_id="t5", reason="Offline"),
        ]
        coord = make_coordinator(results)
        harness = make_harness(connected=5, coverage=0.38)

        pipeline = CoordinatorPipeline(
            coordinator=coord,
            signal_harness=harness,
            explain_decisions=True,
        )

        result = pipeline.process()

        assert result.success
        assert result.tasks_processed == 5
        assert result.tasks_assigned == 3
        assert result.tasks_exhausted == 2
        assert result.assignment_rate == 0.6
        assert len(result.audit_trail) == 5

        # Check assigned entries
        assigned = [
            a for a in result.audit_trail if a.verdict == RoutingVerdict.ASSIGNED
        ]
        assert len(assigned) == 3
        assert all(a.explanation != "" for a in assigned)

        # Check exhausted entries
        exhausted = [
            a for a in result.audit_trail if a.verdict == RoutingVerdict.EXHAUSTED
        ]
        assert len(exhausted) == 2

    def test_multi_cycle_production(self):
        """Multiple cycles with varying loads."""
        pipeline = CoordinatorPipeline(explain_decisions=True)

        # Cycle 1: Heavy load
        coord1 = make_coordinator(
            [MockAssignment(task_id=f"t{i}", agent_id=i) for i in range(10)]
        )
        pipeline._coordinator = coord1
        r1 = pipeline.process()
        assert r1.tasks_assigned == 10

        # Cycle 2: Empty
        coord2 = make_coordinator([])
        pipeline._coordinator = coord2
        r2 = pipeline.process()
        assert r2.tasks_processed == 0

        # Cycle 3: All failures
        coord3 = make_coordinator(
            [MockRoutingFailure(task_id=f"tf{i}") for i in range(5)]
        )
        pipeline._coordinator = coord3
        r3 = pipeline.process()
        assert r3.tasks_exhausted == 5

        # Verify cumulative metrics
        m = pipeline.metrics()
        assert m.total_cycles == 3
        assert m.total_tasks_processed == 15
        assert m.total_tasks_assigned == 10
        assert m.total_tasks_exhausted == 5

    def test_resilient_pipeline_survives_partial_failures(self):
        """Pipeline continues even when some phases fail."""
        coord = MagicMock()
        # process_task_queue works
        coord.process_task_queue.return_value = [MockAssignment()]

        harness = MagicMock()
        # health_summary works
        harness.health_summary.return_value = {"healthy": True, "connected": 1}
        harness.status.return_value = {
            "connected": 1,
            "available": 13,
            "coverage": 0.08,
            "signals": {},
        }

        pipeline = CoordinatorPipeline(
            coordinator=coord,
            signal_harness=harness,
        )

        result = pipeline.process()

        # Even with mocked components, pipeline should complete
        assert result.tasks_assigned == 1
        assert PipelinePhase.ROUTE.value in result.phases_completed
