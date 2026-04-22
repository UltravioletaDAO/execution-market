"""
CoordinatorPipeline Unit Tests — Module #52 in KK V2 Swarm
============================================================

Tests the full 5-phase instrumented routing pipeline:
  Phase 1: WARMUP (harness health, signal coverage)
  Phase 2: EVALUATE (signal state capture)
  Phase 3: ROUTE (coordinator delegation, audit trail)
  Phase 4: AUDIT (finalization)
  Phase 5: COOLDOWN (metrics, history)

Also covers:
  - PipelineResult data model
  - AuditEntry serialization
  - PipelineMetrics aggregation
  - Fluent setter API (chain_router, task_validator, batch_scheduler)
  - Health check and diagnostics
  - History management
  - Error handling (phase failures, coordinator errors)
  - Edge cases (no harness, no coordinator, empty queues)
"""
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

# Add parent paths for imports — direct import to avoid __init__.py Python 3.9 compat issues
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Direct module import avoids swarm/__init__.py which triggers 3.10+ syntax in expiry_analyzer
import importlib.util
_mod_path = str(Path(__file__).parent.parent / "coordinator_pipeline.py")
_spec = importlib.util.spec_from_file_location("coordinator_pipeline", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["coordinator_pipeline"] = _mod  # Register so dataclass can find it
_spec.loader.exec_module(_mod)

_coord_path = str(Path(__file__).parent.parent / "coordinator.py")
_coord_spec = importlib.util.spec_from_file_location("swarm_coordinator", _coord_path)
_coord_mod = importlib.util.module_from_spec(_coord_spec)
sys.modules["swarm_coordinator"] = _coord_mod

AuditEntry = _mod.AuditEntry
CoordinatorPipeline = _mod.CoordinatorPipeline
PipelineMetrics = _mod.PipelineMetrics
PipelinePhase = _mod.PipelinePhase
PipelineResult = _mod.PipelineResult
RoutingVerdict = _mod.RoutingVerdict
SignalSnapshot = _mod.SignalSnapshot


# ---------------------------------------------------------------------------
# Mock Objects
# ---------------------------------------------------------------------------

class _MockStrategy:
    """Fake routing strategy enum value."""
    value = "round_robin"


@dataclass
class MockAssignment:
    """Simulates a routing assignment result."""
    task_id: str
    task_title: str = "Test Task"
    categories: list = None
    bounty_usd: float = 2.00
    agent_id: int = 100
    agent_name: str = "TestAgent"
    score: float = 0.85
    routing_time_ms: float = 12.5
    strategy_used: object = None

    def __post_init__(self):
        if self.categories is None:
            self.categories = ["data_collection"]
        if self.strategy_used is None:
            self.strategy_used = _MockStrategy()


@dataclass
class MockFailure:
    """Simulates a routing failure result."""
    task_id: str
    task_title: str = "Failed Task"
    categories: list = None
    bounty_usd: float = 1.00
    reason: str = "No suitable agents available"

    def __post_init__(self):
        if self.categories is None:
            self.categories = ["physical_verification"]


def make_mock_coordinator(results=None):
    """Create a mock SwarmCoordinator."""
    coord = MagicMock()
    coord.process_task_queue.return_value = results or []
    return coord


def make_mock_harness(connected=5, available=10, healthy=True):
    """Create a mock SignalHarness."""
    harness = MagicMock()
    harness.status.return_value = {
        "connected": connected,
        "available": available,
        "coverage": connected / max(1, available),
        "signals": {
            f"signal_{i}": {
                "calls": 10 if i < connected else 0,
                "avg_latency_ms": 5.0 + i,
                "weight": 0.1,
            }
            for i in range(available)
        },
    }
    harness.health_summary.return_value = {
        "healthy": healthy,
        "connected": connected,
        "healthy_signals": connected if healthy else 0,
    }
    return harness


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def coordinator():
    return make_mock_coordinator()


@pytest.fixture
def harness():
    return make_mock_harness()


@pytest.fixture
def pipeline(coordinator, harness):
    return CoordinatorPipeline(
        coordinator=coordinator,
        signal_harness=harness,
    )


@pytest.fixture
def bare_pipeline(coordinator):
    """Pipeline without signal harness."""
    return CoordinatorPipeline(coordinator=coordinator)


# ---------------------------------------------------------------------------
# Tests: Data Models
# ---------------------------------------------------------------------------

class TestPipelinePhase:
    def test_all_phases_exist(self):
        assert PipelinePhase.WARMUP.value == "warmup"
        assert PipelinePhase.EVALUATE.value == "evaluate"
        assert PipelinePhase.ROUTE.value == "route"
        assert PipelinePhase.AUDIT.value == "audit"
        assert PipelinePhase.COOLDOWN.value == "cooldown"


class TestRoutingVerdict:
    def test_all_verdicts_exist(self):
        assert RoutingVerdict.ASSIGNED.value == "assigned"
        assert RoutingVerdict.EXHAUSTED.value == "exhausted"
        assert RoutingVerdict.DEFERRED.value == "deferred"
        assert RoutingVerdict.SKIPPED.value == "skipped"
        assert RoutingVerdict.ERROR.value == "error"


class TestSignalSnapshot:
    def test_defaults(self):
        s = SignalSnapshot(connected_signals=5, active_signals=3)
        assert s.connected_signals == 5
        assert s.active_signals == 3
        assert s.total_score == 0.0
        assert s.coverage_pct == 0.0

    def test_with_scores(self):
        s = SignalSnapshot(
            connected_signals=3,
            active_signals=2,
            signal_scores={"reputation": 0.8, "speed": 0.6},
            signal_latencies={"reputation": 5.0, "speed": 3.0},
            coverage_pct=75.0,
        )
        assert s.signal_scores["reputation"] == 0.8
        assert s.signal_latencies["speed"] == 3.0


class TestAuditEntry:
    def test_basic_entry(self):
        entry = AuditEntry(
            task_id="t1",
            task_title="Test",
            categories=["data_collection"],
            bounty_usd=2.50,
            verdict=RoutingVerdict.ASSIGNED,
            agent_id=100,
            agent_name="Agent Alpha",
            score=0.87,
        )
        assert entry.task_id == "t1"
        assert entry.verdict == RoutingVerdict.ASSIGNED

    def test_to_dict_with_snapshot(self):
        snapshot = SignalSnapshot(
            connected_signals=5,
            active_signals=3,
            signal_scores={"rep": 0.8},
            coverage_pct=62.5,
        )
        entry = AuditEntry(
            task_id="t2",
            task_title="Audit Test",
            categories=["physical_verification"],
            bounty_usd=5.00,
            verdict=RoutingVerdict.ASSIGNED,
            signal_snapshot=snapshot,
            score=0.91,
        )
        d = entry.to_dict()
        assert d["task_id"] == "t2"
        assert d["verdict"] == "assigned"
        assert d["signals"]["connected"] == 5
        assert d["signals"]["active"] == 3

    def test_to_dict_without_snapshot(self):
        entry = AuditEntry(
            task_id="t3",
            task_title="No Signals",
            categories=[],
            bounty_usd=1.00,
            verdict=RoutingVerdict.EXHAUSTED,
        )
        d = entry.to_dict()
        assert d["signals"] is None


class TestPipelineResult:
    def test_success_when_no_failures(self):
        r = PipelineResult(cycle_id=1, started_at="2026-04-10T01:00:00Z", duration_ms=50)
        r.phases_completed = ["warmup", "evaluate", "route", "audit", "cooldown"]
        assert r.success is True

    def test_failure_when_phases_failed(self):
        r = PipelineResult(cycle_id=1, started_at="2026-04-10T01:00:00Z", duration_ms=50)
        r.phases_failed = ["route"]
        assert r.success is False

    def test_assignment_rate(self):
        r = PipelineResult(cycle_id=1, started_at="now", duration_ms=0)
        r.tasks_processed = 10
        r.tasks_assigned = 7
        assert r.assignment_rate == pytest.approx(0.7)

    def test_assignment_rate_zero_tasks(self):
        r = PipelineResult(cycle_id=1, started_at="now", duration_ms=0)
        assert r.assignment_rate == 0.0

    def test_to_dict(self):
        r = PipelineResult(cycle_id=42, started_at="2026-04-10T01:00:00Z", duration_ms=123.4)
        r.tasks_processed = 5
        r.tasks_assigned = 3
        r.phases_completed = ["warmup", "route"]
        d = r.to_dict()
        assert d["cycle_id"] == 42
        assert d["tasks"]["processed"] == 5
        assert d["tasks"]["assigned"] == 3
        assert d["tasks"]["assignment_rate"] == 0.6

    def test_summary_string(self):
        r = PipelineResult(cycle_id=1, started_at="now", duration_ms=100)
        r.tasks_processed = 10
        r.tasks_assigned = 8
        s = r.summary()
        assert "8/10" in s
        assert "80%" in s
        assert "✅" in s

    def test_summary_failed(self):
        r = PipelineResult(cycle_id=1, started_at="now", duration_ms=100)
        r.phases_failed = ["route"]
        s = r.summary()
        assert "❌" in s


class TestPipelineMetrics:
    def test_defaults(self):
        m = PipelineMetrics()
        assert m.total_cycles == 0
        assert m.total_tasks_processed == 0

    def test_to_dict(self):
        m = PipelineMetrics(
            total_cycles=10,
            total_tasks_processed=50,
            total_tasks_assigned=35,
            avg_cycle_duration_ms=75.5,
            avg_assignment_rate=0.7,
        )
        d = m.to_dict()
        assert d["cycles"] == 10
        assert d["avg_assignment_rate"] == 0.7


# ---------------------------------------------------------------------------
# Tests: Pipeline Construction
# ---------------------------------------------------------------------------

class TestPipelineConstruction:
    def test_default_config(self, coordinator, harness):
        p = CoordinatorPipeline(coordinator=coordinator, signal_harness=harness)
        assert p.coordinator is coordinator
        assert p.signal_harness is harness
        assert p.cycle_count == 0

    def test_without_harness(self, coordinator):
        p = CoordinatorPipeline(coordinator=coordinator)
        assert p.signal_harness is None

    def test_custom_config(self, coordinator, harness):
        p = CoordinatorPipeline(
            coordinator=coordinator,
            signal_harness=harness,
            max_tasks_per_cycle=20,
            min_signal_coverage=0.5,
            explain_decisions=False,
        )
        assert p._max_tasks == 20
        assert p._min_coverage == 0.5
        assert p._explain is False

    def test_fluent_setters(self, pipeline):
        mock_router = MagicMock()
        mock_validator = MagicMock()
        mock_scheduler = MagicMock()

        result = pipeline.set_chain_router(mock_router)
        assert result is pipeline  # Fluent
        assert pipeline.chain_router is mock_router

        pipeline.set_task_validator(mock_validator)
        assert pipeline.task_validator is mock_validator

        pipeline.set_batch_scheduler(mock_scheduler)
        assert pipeline.batch_scheduler is mock_scheduler

    def test_repr(self, pipeline):
        r = repr(pipeline)
        assert "CoordinatorPipeline" in r
        assert "cycles=0" in r


# ---------------------------------------------------------------------------
# Tests: Pipeline Process — Happy Path
# ---------------------------------------------------------------------------

class TestPipelineProcess:
    def test_empty_queue(self, pipeline):
        pipeline.coordinator.process_task_queue.return_value = []
        result = pipeline.process()

        assert result.success
        assert result.tasks_processed == 0
        assert result.cycle_id == 1
        assert "warmup" in result.phases_completed
        assert "route" in result.phases_completed
        assert "cooldown" in result.phases_completed

    def test_single_assignment(self, pipeline):
        assignment = MockAssignment(task_id="t1")
        pipeline.coordinator.process_task_queue.return_value = [assignment]

        result = pipeline.process()
        assert result.success
        assert result.tasks_processed == 1
        assert result.tasks_assigned == 1
        assert len(result.audit_trail) == 1
        assert result.audit_trail[0].verdict == RoutingVerdict.ASSIGNED
        assert result.audit_trail[0].agent_id == 100

    def test_multiple_assignments(self, pipeline):
        assignments = [MockAssignment(task_id=f"t{i}", score=0.9 - i * 0.1) for i in range(5)]
        pipeline.coordinator.process_task_queue.return_value = assignments

        result = pipeline.process()
        assert result.tasks_processed == 5
        assert result.tasks_assigned == 5
        assert len(result.audit_trail) == 5

    def test_mixed_assignments_and_failures(self, pipeline):
        results = [
            MockAssignment(task_id="t1"),
            MockFailure(task_id="t2"),
            MockAssignment(task_id="t3"),
            MockFailure(task_id="t4"),
        ]
        pipeline.coordinator.process_task_queue.return_value = results

        result = pipeline.process()
        assert result.tasks_processed == 4
        assert result.tasks_assigned == 2
        assert result.tasks_exhausted == 2
        assert result.assignment_rate == 0.5

    def test_all_failures(self, pipeline):
        failures = [MockFailure(task_id=f"f{i}") for i in range(3)]
        pipeline.coordinator.process_task_queue.return_value = failures

        result = pipeline.process()
        assert result.tasks_assigned == 0
        assert result.tasks_exhausted == 3
        assert result.assignment_rate == 0.0

    def test_cycle_count_increments(self, pipeline):
        pipeline.coordinator.process_task_queue.return_value = []

        r1 = pipeline.process()
        r2 = pipeline.process()
        r3 = pipeline.process()

        assert r1.cycle_id == 1
        assert r2.cycle_id == 2
        assert r3.cycle_id == 3
        assert pipeline.cycle_count == 3

    def test_max_tasks_passed_to_coordinator(self, pipeline):
        pipeline.process(max_tasks=5)
        pipeline.coordinator.process_task_queue.assert_called_once_with(
            strategy=None, max_tasks=5
        )

    def test_strategy_passed_to_coordinator(self, pipeline):
        mock_strategy = MagicMock()
        pipeline.process(strategy=mock_strategy)
        pipeline.coordinator.process_task_queue.assert_called_once_with(
            strategy=mock_strategy, max_tasks=10
        )


# ---------------------------------------------------------------------------
# Tests: Pipeline Without Harness
# ---------------------------------------------------------------------------

class TestPipelineWithoutHarness:
    def test_processes_without_harness(self, bare_pipeline):
        bare_pipeline.coordinator.process_task_queue.return_value = [
            MockAssignment(task_id="t1")
        ]
        result = bare_pipeline.process()
        assert result.success
        assert result.tasks_assigned == 1
        assert result.harness_status is None

    def test_audit_entry_no_snapshot(self, bare_pipeline):
        bare_pipeline.coordinator.process_task_queue.return_value = [
            MockAssignment(task_id="t1")
        ]
        result = bare_pipeline.process()
        assert result.audit_trail[0].signal_snapshot is None


# ---------------------------------------------------------------------------
# Tests: Warmup Phase
# ---------------------------------------------------------------------------

class TestWarmupPhase:
    def test_no_coordinator_fails_warmup(self):
        p = CoordinatorPipeline(coordinator=None)
        result = p.process()
        assert not result.success
        assert "warmup" in result.phases_failed
        assert any("No coordinator" in e for e in result.errors)

    def test_low_signal_coverage_fails_warmup(self, coordinator):
        harness = make_mock_harness(connected=1, available=10)  # 10% coverage
        p = CoordinatorPipeline(
            coordinator=coordinator,
            signal_harness=harness,
            min_signal_coverage=0.5,  # Require 50%
        )
        result = p.process()
        assert not result.success
        assert "warmup" in result.phases_failed
        assert any("coverage" in e.lower() for e in result.errors)

    def test_sufficient_coverage_passes(self, coordinator):
        harness = make_mock_harness(connected=8, available=10)  # 80%
        p = CoordinatorPipeline(
            coordinator=coordinator,
            signal_harness=harness,
            min_signal_coverage=0.5,
        )
        p.coordinator.process_task_queue.return_value = []
        result = p.process()
        assert result.success

    def test_degraded_harness_warns_but_continues(self, coordinator):
        harness = make_mock_harness(connected=5, available=10, healthy=False)
        p = CoordinatorPipeline(
            coordinator=coordinator,
            signal_harness=harness,
            min_signal_coverage=0.0,  # No minimum
        )
        p.coordinator.process_task_queue.return_value = []
        result = p.process()
        # Should succeed despite degraded harness (no minimum set)
        assert result.success

    def test_warmup_exception_captured(self, coordinator):
        harness = MagicMock()
        harness.health_summary.side_effect = RuntimeError("Harness crash")
        harness.status.side_effect = RuntimeError("Harness crash")

        p = CoordinatorPipeline(coordinator=coordinator, signal_harness=harness)
        result = p.process()
        assert not result.success
        assert "warmup" in result.phases_failed


# ---------------------------------------------------------------------------
# Tests: Route Phase Errors
# ---------------------------------------------------------------------------

class TestRoutePhaseErrors:
    def test_coordinator_exception_captured(self, pipeline):
        pipeline.coordinator.process_task_queue.side_effect = RuntimeError("DB down")
        result = pipeline.process()
        assert "route" in result.phases_failed
        assert any("route:" in e for e in result.errors)

    def test_partial_exception_in_route(self, pipeline):
        """If coordinator returns results then raises, partial results captured."""
        # This tests that the exception is caught, not that partial results are kept
        pipeline.coordinator.process_task_queue.side_effect = RuntimeError("Timeout")
        result = pipeline.process()
        assert "route" in result.phases_failed


# ---------------------------------------------------------------------------
# Tests: Audit Trail
# ---------------------------------------------------------------------------

class TestAuditTrail:
    def test_assignment_audit_entry_fields(self, pipeline):
        assignment = MockAssignment(
            task_id="audit_t1",
            task_title="Verify Storefront",
            categories=["physical_verification"],
            bounty_usd=5.00,
            agent_id=200,
            agent_name="FieldBot",
            score=0.93,
            routing_time_ms=15.3,
        )
        pipeline.coordinator.process_task_queue.return_value = [assignment]
        result = pipeline.process()

        entry = result.audit_trail[0]
        assert entry.task_id == "audit_t1"
        assert entry.task_title == "Verify Storefront"
        assert entry.bounty_usd == 5.00
        assert entry.verdict == RoutingVerdict.ASSIGNED
        assert entry.agent_id == 200
        assert entry.agent_name == "FieldBot"
        assert entry.score == 0.93
        assert entry.routing_time_ms == 15.3

    def test_failure_audit_entry_fields(self, pipeline):
        failure = MockFailure(
            task_id="fail_t1",
            task_title="Impossible Task",
            reason="No agents with required skills",
        )
        pipeline.coordinator.process_task_queue.return_value = [failure]
        result = pipeline.process()

        entry = result.audit_trail[0]
        assert entry.verdict == RoutingVerdict.EXHAUSTED
        assert "No agents" in entry.explanation

    def test_explanation_generated(self, pipeline):
        assignment = MockAssignment(task_id="explain_t1")
        pipeline.coordinator.process_task_queue.return_value = [assignment]
        result = pipeline.process()

        entry = result.audit_trail[0]
        assert "TestAgent" in entry.explanation
        assert "100" in entry.explanation  # agent_id

    def test_explanation_disabled(self, coordinator, harness):
        p = CoordinatorPipeline(
            coordinator=coordinator,
            signal_harness=harness,
            explain_decisions=False,
        )
        assignment = MockAssignment(task_id="no_explain")
        p.coordinator.process_task_queue.return_value = [assignment]
        result = p.process()

        entry = result.audit_trail[0]
        assert entry.explanation == ""


class TestCoordinatorDecisionEvents:
    def test_coordinator_emits_route_and_outcome_events(self, tmp_path):
        try:
            _coord_spec.loader.exec_module(_coord_mod)
        except Exception as exc:
            pytest.skip(f"Coordinator imports unavailable in this runtime: {exc}")

        bridge = _coord_mod.ReputationBridge()
        lifecycle = _coord_mod.LifecycleManager()
        orchestrator = _coord_mod.SwarmOrchestrator(bridge, lifecycle)
        journal_path = tmp_path / "decision-journal.jsonl"
        coordinator = _coord_mod.SwarmCoordinator(
            bridge=bridge,
            lifecycle=lifecycle,
            orchestrator=orchestrator,
            decision_journal_path=str(journal_path),
        )

        coordinator.register_agent(
            agent_id=2106,
            name="clawd",
            wallet_address="0x1234567890abcdef1234567890abcdef12345678",
            activate=True,
        )
        coordinator.ingest_task(
            task_id="em_123",
            title="Verify storefront",
            categories=["photo_geo"],
            bounty_usd=0.42,
        )

        results = coordinator.process_task_queue()
        assert len(results) == 1
        assert isinstance(results[0], _coord_mod.Assignment)

        event_names = [event["event"] for event in coordinator.get_events(limit=20)]
        assert "route_recorded" in event_names
        assert "task_assigned" in event_names

        assert coordinator.complete_task("em_123", bounty_earned_usd=0.42, evidence_summary="photo verified") is True

        event_names = [event["event"] for event in coordinator.get_events(limit=50)]
        assert "route_outcome" in event_names
        assert "task_completed" in event_names

        journal_lines = journal_path.read_text(encoding="utf-8").strip().splitlines()
        assert journal_lines
        assert any("coord_em_123" in line for line in journal_lines)


# ---------------------------------------------------------------------------
# Tests: Metrics
# ---------------------------------------------------------------------------

class TestMetrics:
    def test_initial_metrics(self, pipeline):
        m = pipeline.metrics()
        assert m.total_cycles == 0
        assert m.total_tasks_processed == 0

    def test_metrics_after_processing(self, pipeline):
        pipeline.coordinator.process_task_queue.return_value = [
            MockAssignment(task_id="m1"),
            MockAssignment(task_id="m2"),
            MockFailure(task_id="m3"),
        ]
        pipeline.process()

        m = pipeline.metrics()
        assert m.total_cycles == 1
        assert m.total_tasks_processed == 3
        assert m.total_tasks_assigned == 2
        assert m.total_tasks_exhausted == 1

    def test_metrics_accumulate_across_cycles(self, pipeline):
        pipeline.coordinator.process_task_queue.return_value = [
            MockAssignment(task_id="a1"),
        ]

        for _ in range(5):
            pipeline.process()

        m = pipeline.metrics()
        assert m.total_cycles == 5
        assert m.total_tasks_processed == 5
        assert m.total_tasks_assigned == 5

    def test_best_worst_assignment_rate(self, pipeline):
        # Cycle 1: 100% assignment
        pipeline.coordinator.process_task_queue.return_value = [
            MockAssignment(task_id="good1"),
            MockAssignment(task_id="good2"),
        ]
        pipeline.process()

        # Cycle 2: 0% assignment
        pipeline.coordinator.process_task_queue.return_value = [
            MockFailure(task_id="bad1"),
        ]
        pipeline.process()

        m = pipeline.metrics()
        assert m.best_assignment_rate == 1.0
        assert m.worst_assignment_rate == 0.0

    def test_avg_cycle_duration(self, pipeline):
        pipeline.coordinator.process_task_queue.return_value = []
        pipeline.process()

        m = pipeline.metrics()
        assert m.avg_cycle_duration_ms >= 0


# ---------------------------------------------------------------------------
# Tests: Health Check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_healthy_pipeline(self, pipeline):
        pipeline.coordinator.process_task_queue.return_value = []
        pipeline.process()

        h = pipeline.health_check()
        assert h["healthy"] is True
        assert h["issues"] == []

    def test_no_coordinator(self):
        p = CoordinatorPipeline(coordinator=None)
        h = p.health_check()
        assert h["healthy"] is False
        assert "No coordinator" in h["issues"]

    def test_consecutive_failures_unhealthy(self, pipeline):
        pipeline.coordinator.process_task_queue.side_effect = RuntimeError("Boom")
        for _ in range(3):
            pipeline.process()

        h = pipeline.health_check()
        assert h["healthy"] is False
        assert any("consecutive" in i for i in h["issues"])

    def test_consecutive_failures_reset_on_success(self, pipeline):
        # 2 failures
        pipeline.coordinator.process_task_queue.side_effect = RuntimeError("Fail")
        pipeline.process()
        pipeline.process()

        # Then success
        pipeline.coordinator.process_task_queue.side_effect = None
        pipeline.coordinator.process_task_queue.return_value = []
        pipeline.process()

        h = pipeline.health_check()
        assert h["healthy"] is True


# ---------------------------------------------------------------------------
# Tests: Diagnostics & Status
# ---------------------------------------------------------------------------

class TestDiagnostics:
    def test_status_structure(self, pipeline):
        s = pipeline.status()
        assert "running" in s
        assert "cycle_count" in s
        assert "config" in s
        assert "metrics" in s
        assert s["coordinator"] is True
        assert s["signal_harness"] is True

    def test_status_without_harness(self, bare_pipeline):
        s = bare_pipeline.status()
        assert s["signal_harness"] is False
        assert s["harness_health"] is None

    def test_status_shows_optional_modules(self, pipeline):
        s = pipeline.status()
        assert s["chain_router"] is False
        assert s["task_validator"] is False
        assert s["batch_scheduler"] is False

        pipeline.set_chain_router(MagicMock())
        s = pipeline.status()
        assert s["chain_router"] is True


# ---------------------------------------------------------------------------
# Tests: History
# ---------------------------------------------------------------------------

class TestHistory:
    def test_recent_results_empty(self, pipeline):
        assert pipeline.recent_results() == []

    def test_recent_results_after_processing(self, pipeline):
        pipeline.coordinator.process_task_queue.return_value = []
        pipeline.process()
        pipeline.process()

        results = pipeline.recent_results()
        assert len(results) == 2
        assert results[0]["cycle_id"] == 1
        assert results[1]["cycle_id"] == 2

    def test_recent_results_limit(self, pipeline):
        pipeline.coordinator.process_task_queue.return_value = []
        for _ in range(10):
            pipeline.process()

        results = pipeline.recent_results(limit=3)
        assert len(results) == 3
        # Should be the most recent 3
        assert results[-1]["cycle_id"] == 10

    def test_history_capped_at_50(self, pipeline):
        pipeline.coordinator.process_task_queue.return_value = []
        for _ in range(60):
            pipeline.process()

        results = pipeline.recent_results(limit=100)
        assert len(results) == 50  # Capped by deque maxlen


# ---------------------------------------------------------------------------
# Tests: Signal Snapshot Capture
# ---------------------------------------------------------------------------

class TestSignalSnapshotCapture:
    def test_snapshot_captures_harness_state(self, pipeline):
        assignment = MockAssignment(task_id="snap_t1")
        pipeline.coordinator.process_task_queue.return_value = [assignment]
        result = pipeline.process()

        snapshot = result.audit_trail[0].signal_snapshot
        assert snapshot is not None
        assert snapshot.connected_signals == 5
        assert len(snapshot.signal_scores) > 0
        assert len(snapshot.signal_latencies) > 0

    def test_snapshot_none_without_harness(self, bare_pipeline):
        assignment = MockAssignment(task_id="nosnap_t1")
        bare_pipeline.coordinator.process_task_queue.return_value = [assignment]
        result = bare_pipeline.process()

        assert result.audit_trail[0].signal_snapshot is None


# ---------------------------------------------------------------------------
# Tests: Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_duration_is_positive(self, pipeline):
        pipeline.coordinator.process_task_queue.return_value = []
        result = pipeline.process()
        assert result.duration_ms >= 0

    def test_process_result_serializable(self, pipeline):
        pipeline.coordinator.process_task_queue.return_value = [
            MockAssignment(task_id="serial_t1"),
            MockFailure(task_id="serial_t2"),
        ]
        result = pipeline.process()
        d = result.to_dict()
        # Should be fully serializable to JSON
        import json
        json_str = json.dumps(d)
        assert "serial_t1" in json_str
        assert "serial_t2" in json_str

    def test_multiple_cycles_dont_leak_state(self, pipeline):
        """Each cycle starts fresh — audit trail doesn't carry over."""
        pipeline.coordinator.process_task_queue.return_value = [
            MockAssignment(task_id="cycle1_t1"),
        ]
        r1 = pipeline.process()
        assert len(r1.audit_trail) == 1

        pipeline.coordinator.process_task_queue.return_value = [
            MockAssignment(task_id="cycle2_t1"),
            MockAssignment(task_id="cycle2_t2"),
        ]
        r2 = pipeline.process()
        assert len(r2.audit_trail) == 2  # Only cycle 2 entries

    def test_audit_phase_error_nonfatal(self, pipeline):
        """Audit phase error shouldn't crash the pipeline."""
        pipeline.coordinator.process_task_queue.return_value = []
        # Force harness.status to fail during audit
        call_count = [0]
        original_status = pipeline.signal_harness.status

        def failing_status():
            call_count[0] += 1
            if call_count[0] > 2:  # Fail on audit phase call
                raise RuntimeError("Status failed")
            return original_status()

        pipeline.signal_harness.status = failing_status
        result = pipeline.process()
        # Pipeline should still complete (audit failure is non-fatal)
        assert result.duration_ms >= 0

    def test_cooldown_phase_error_nonfatal(self, pipeline):
        """Cooldown phase error shouldn't crash the pipeline."""
        pipeline.coordinator.process_task_queue.return_value = []

        # Mock _phase_cooldown to fail
        original_cooldown = pipeline._phase_cooldown

        def failing_cooldown(result):
            raise RuntimeError("Cooldown failed")

        pipeline._phase_cooldown = failing_cooldown
        result = pipeline.process()
        assert "cooldown" in result.phases_failed
