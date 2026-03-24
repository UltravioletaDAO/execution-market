"""
Tests for PhaseGate — Swarm Activation Phase Management
=========================================================

Covers:
- Phase enum, labels, modes
- GateCheck, PhaseEvaluation properties
- Gate definitions per transition (P0→P1, P1→P2, P2→P3)
- PhaseGate: advance, emergency_stop, health checks, should_emergency_stop
- History tracking, status, serialization
"""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from swarm.phase_gate import (
    Phase,
    PHASE_LABELS,
    PHASE_MODE_MAP,
    GateCheck,
    PhaseEvaluation,
    SwarmMetrics,
    PhaseTransition,
    PhaseGate,
    _gates_pre_flight_to_passive,
    _gates_passive_to_semi_auto,
    _gates_semi_auto_to_full_auto,
)


# ---------------------------------------------------------------------------
# Phase enum
# ---------------------------------------------------------------------------


class TestPhaseEnum:
    def test_values(self):
        assert Phase.EMERGENCY == -1
        assert Phase.PRE_FLIGHT == 0
        assert Phase.PASSIVE == 1
        assert Phase.SEMI_AUTO == 2
        assert Phase.FULL_AUTO == 3

    def test_ordering(self):
        assert Phase.PRE_FLIGHT < Phase.PASSIVE < Phase.SEMI_AUTO < Phase.FULL_AUTO

    def test_labels_defined(self):
        for phase in Phase:
            assert phase in PHASE_LABELS

    def test_modes_defined(self):
        for phase in Phase:
            assert phase in PHASE_MODE_MAP


# ---------------------------------------------------------------------------
# GateCheck
# ---------------------------------------------------------------------------


class TestGateCheck:
    def test_to_dict(self):
        g = GateCheck(
            name="test", description="Test gate", passed=True,
            current_value=5, required_value=3,
        )
        d = g.to_dict()
        assert d["name"] == "test"
        assert d["passed"] is True
        assert d["current"] == 5
        assert d["required"] == 3

    def test_default_severity_blocker(self):
        g = GateCheck(name="x", description="x", passed=True)
        assert g.severity == "blocker"


# ---------------------------------------------------------------------------
# PhaseEvaluation
# ---------------------------------------------------------------------------


class TestPhaseEvaluation:
    def test_can_advance_all_pass(self):
        ev = PhaseEvaluation(
            current_phase=Phase.PRE_FLIGHT,
            target_phase=Phase.PASSIVE,
            gates=[
                GateCheck(name="a", description="a", passed=True),
                GateCheck(name="b", description="b", passed=True),
            ],
        )
        assert ev.can_advance is True

    def test_can_advance_blocker_fails(self):
        ev = PhaseEvaluation(
            current_phase=Phase.PRE_FLIGHT,
            target_phase=Phase.PASSIVE,
            gates=[
                GateCheck(name="a", description="a", passed=True),
                GateCheck(name="b", description="B fails", passed=False, severity="blocker"),
            ],
        )
        assert ev.can_advance is False

    def test_can_advance_warning_doesnt_block(self):
        ev = PhaseEvaluation(
            current_phase=Phase.PRE_FLIGHT,
            target_phase=Phase.PASSIVE,
            gates=[
                GateCheck(name="a", description="a", passed=True),
                GateCheck(name="b", description="B warns", passed=False, severity="warning"),
            ],
        )
        assert ev.can_advance is True

    def test_blockers_list(self):
        ev = PhaseEvaluation(
            current_phase=Phase.PRE_FLIGHT,
            target_phase=Phase.PASSIVE,
            gates=[
                GateCheck(name="a", description="Gate A", passed=False, severity="blocker"),
                GateCheck(name="b", description="Gate B", passed=True),
                GateCheck(name="c", description="Gate C", passed=False, severity="blocker"),
            ],
        )
        assert ev.blockers == ["Gate A", "Gate C"]

    def test_warnings_list(self):
        ev = PhaseEvaluation(
            current_phase=Phase.PRE_FLIGHT,
            target_phase=Phase.PASSIVE,
            gates=[
                GateCheck(name="a", description="Gate A", passed=False, severity="warning"),
                GateCheck(name="b", description="Gate B", passed=True),
            ],
        )
        assert ev.warnings == ["Gate A"]
        assert ev.blockers == []

    def test_pass_rate(self):
        ev = PhaseEvaluation(
            current_phase=Phase.PRE_FLIGHT,
            target_phase=Phase.PASSIVE,
            gates=[
                GateCheck(name="a", description="a", passed=True),
                GateCheck(name="b", description="b", passed=False),
                GateCheck(name="c", description="c", passed=True),
                GateCheck(name="d", description="d", passed=True),
            ],
        )
        assert ev.pass_rate == 0.75

    def test_pass_rate_no_gates(self):
        ev = PhaseEvaluation(
            current_phase=Phase.PRE_FLIGHT,
            target_phase=Phase.PASSIVE,
        )
        assert ev.pass_rate == 0.0

    def test_to_dict(self):
        ev = PhaseEvaluation(
            current_phase=Phase.PRE_FLIGHT,
            target_phase=Phase.PASSIVE,
            gates=[GateCheck(name="a", description="a", passed=True)],
        )
        d = ev.to_dict()
        assert "can_advance" in d
        assert "pass_rate" in d
        assert "evaluated_at" in d


# ---------------------------------------------------------------------------
# Gate Definitions
# ---------------------------------------------------------------------------


class TestGateDefinitions:
    """Test that gate functions produce correct checks."""

    def _healthy_metrics(self, **overrides):
        m = SwarmMetrics(
            api_healthy=True,
            swarm_enabled=True,
            coordinator_active=True,
            error_count_last_hour=0,
            error_count_last_24h=0,
            uptime_hours=100,
            tasks_ingested=50,
            tasks_completed=30,
            tasks_expired=2,
            expiry_rate=0.04,
            worker_count=10,
            categories_with_workers=4,
            agents_registered=24,
            agents_healthy=20,
            daily_spend_usd=5.0,
            daily_budget_usd=20.0,
            worker_hhi=0.25,
            days_in_current_phase=10,
        )
        for k, v in overrides.items():
            setattr(m, k, v)
        return m

    def test_pre_flight_to_passive_all_pass(self):
        gates = _gates_pre_flight_to_passive(self._healthy_metrics())
        blockers = [g for g in gates if not g.passed and g.severity == "blocker"]
        assert len(blockers) == 0

    def test_pre_flight_to_passive_api_down(self):
        gates = _gates_pre_flight_to_passive(self._healthy_metrics(api_healthy=False))
        api_gate = next(g for g in gates if g.name == "api_healthy")
        assert not api_gate.passed

    def test_pre_flight_to_passive_low_uptime(self):
        gates = _gates_pre_flight_to_passive(self._healthy_metrics(uptime_hours=0.5))
        uptime_gate = next(g for g in gates if g.name == "uptime_min")
        assert not uptime_gate.passed

    def test_passive_to_semi_auto_all_pass(self):
        gates = _gates_passive_to_semi_auto(self._healthy_metrics())
        blockers = [g for g in gates if not g.passed and g.severity == "blocker"]
        assert len(blockers) == 0

    def test_passive_to_semi_auto_too_few_days(self):
        gates = _gates_passive_to_semi_auto(self._healthy_metrics(days_in_current_phase=1))
        day_gate = next(g for g in gates if g.name == "min_observation_days")
        assert not day_gate.passed

    def test_passive_to_semi_auto_too_few_workers(self):
        gates = _gates_passive_to_semi_auto(self._healthy_metrics(worker_count=1))
        worker_gate = next(g for g in gates if g.name == "worker_count")
        assert not worker_gate.passed

    def test_semi_auto_to_full_auto_all_pass(self):
        gates = _gates_semi_auto_to_full_auto(self._healthy_metrics())
        blockers = [g for g in gates if not g.passed and g.severity == "blocker"]
        assert len(blockers) == 0

    def test_semi_auto_to_full_auto_high_expiry(self):
        gates = _gates_semi_auto_to_full_auto(self._healthy_metrics(expiry_rate=0.30))
        expiry_gate = next(g for g in gates if g.name == "expiry_rate")
        assert not expiry_gate.passed

    def test_semi_auto_to_full_auto_monopoly_worker(self):
        gates = _gates_semi_auto_to_full_auto(self._healthy_metrics(worker_hhi=0.8))
        hhi_gate = next(g for g in gates if g.name == "worker_concentration")
        assert not hhi_gate.passed

    def test_semi_auto_to_full_auto_over_budget(self):
        gates = _gates_semi_auto_to_full_auto(self._healthy_metrics(
            daily_spend_usd=18.0, daily_budget_usd=20.0
        ))
        budget_gate = next(g for g in gates if g.name == "budget_under_control")
        assert not budget_gate.passed  # 18/20 = 90% > 80%


# ---------------------------------------------------------------------------
# PhaseGate — Core Operations
# ---------------------------------------------------------------------------


class TestPhaseGateCore:

    def _healthy_metrics(self):
        return SwarmMetrics(
            api_healthy=True, swarm_enabled=True, coordinator_active=True,
            error_count_last_hour=0, error_count_last_24h=0,
            uptime_hours=100, tasks_ingested=50, tasks_completed=30,
            expiry_rate=0.04, worker_count=10, categories_with_workers=4,
            agents_registered=24, agents_healthy=20,
            daily_spend_usd=5, daily_budget_usd=20,
            worker_hhi=0.25, days_in_current_phase=10,
        )

    def test_initial_phase(self):
        gate = PhaseGate()
        assert gate.phase == Phase.PRE_FLIGHT
        assert gate.mode == "passive"

    def test_set_phase(self):
        gate = PhaseGate()
        gate.set_phase(Phase.PASSIVE, reason="test")
        assert gate.phase == Phase.PASSIVE
        assert gate.mode == "passive"

    def test_set_phase_records_history(self):
        gate = PhaseGate()
        gate.set_phase(Phase.PASSIVE, reason="test")
        assert len(gate.history) == 1
        assert gate.history[0].from_phase == Phase.PRE_FLIGHT
        assert gate.history[0].to_phase == Phase.PASSIVE

    def test_advance_success(self):
        gate = PhaseGate()
        m = self._healthy_metrics()
        transition = gate.advance(m)
        assert transition is not None
        assert gate.phase == Phase.PASSIVE

    def test_advance_blocked(self):
        gate = PhaseGate()
        m = SwarmMetrics()  # All defaults, nothing healthy
        transition = gate.advance(m)
        assert transition is None
        assert gate.phase == Phase.PRE_FLIGHT  # Didn't advance

    def test_advance_forced(self):
        gate = PhaseGate()
        m = SwarmMetrics()  # Would normally be blocked
        transition = gate.advance(m, force=True, reason="testing")
        assert transition is not None
        assert gate.phase == Phase.PASSIVE
        assert "FORCED" in transition.reason

    def test_advance_from_full_auto(self):
        gate = PhaseGate(initial_phase=Phase.FULL_AUTO)
        m = self._healthy_metrics()
        transition = gate.advance(m)
        assert transition is None  # Can't go past full auto

    def test_advance_from_emergency_blocked(self):
        gate = PhaseGate()
        gate.emergency_stop("test")
        m = self._healthy_metrics()
        transition = gate.advance(m)
        assert transition is None  # Can't advance from emergency without force

    def test_advance_from_emergency_forced(self):
        gate = PhaseGate()
        gate.emergency_stop("test")
        m = self._healthy_metrics()
        transition = gate.advance(m, force=True)
        assert transition is not None
        assert gate.phase == Phase.PRE_FLIGHT  # Goes back to pre-flight


# ---------------------------------------------------------------------------
# PhaseGate — Emergency Stop
# ---------------------------------------------------------------------------


class TestPhaseGateEmergency:

    def test_emergency_stop(self):
        gate = PhaseGate(initial_phase=Phase.SEMI_AUTO)
        gate.emergency_stop("test crash")
        assert gate.phase == Phase.EMERGENCY
        assert gate.mode == "disabled"

    def test_emergency_evaluation(self):
        gate = PhaseGate()
        gate.emergency_stop("crash")
        ev = gate.evaluate_advance(SwarmMetrics())
        assert not ev.can_advance
        assert any("manually cleared" in b for b in ev.blockers)

    def test_should_emergency_stop_runaway_spend(self):
        gate = PhaseGate(initial_phase=Phase.SEMI_AUTO)
        m = SwarmMetrics(
            daily_spend_usd=50, daily_budget_usd=20,
            api_healthy=True, uptime_hours=5,
        )
        should_stop, reason = gate.should_emergency_stop(m)
        assert should_stop
        assert "budget" in reason.lower() or "spend" in reason.lower()

    def test_should_emergency_stop_error_storm(self):
        gate = PhaseGate(initial_phase=Phase.PASSIVE)
        m = SwarmMetrics(
            error_count_last_hour=100,
            api_healthy=True, uptime_hours=5,
        )
        should_stop, reason = gate.should_emergency_stop(m)
        assert should_stop
        assert "error" in reason.lower()

    def test_should_emergency_stop_api_down(self):
        gate = PhaseGate(initial_phase=Phase.PASSIVE)
        m = SwarmMetrics(api_healthy=False, uptime_hours=1)
        should_stop, reason = gate.should_emergency_stop(m)
        assert should_stop

    def test_no_emergency_in_preflight(self):
        gate = PhaseGate(initial_phase=Phase.PRE_FLIGHT)
        m = SwarmMetrics(error_count_last_hour=100)
        should_stop, _ = gate.should_emergency_stop(m)
        assert not should_stop  # Pre-flight doesn't trigger emergency


# ---------------------------------------------------------------------------
# PhaseGate — Health Checks
# ---------------------------------------------------------------------------


class TestPhaseGateHealth:

    def test_health_check_preflight(self):
        gate = PhaseGate(initial_phase=Phase.PRE_FLIGHT)
        checks = gate.evaluate_health(SwarmMetrics(api_healthy=True))
        assert len(checks) >= 1
        assert all(c.passed for c in checks)

    def test_health_check_passive_includes_errors(self):
        gate = PhaseGate(initial_phase=Phase.PASSIVE)
        checks = gate.evaluate_health(SwarmMetrics(
            api_healthy=True, error_count_last_hour=0
        ))
        names = [c.name for c in checks]
        assert "error_rate" in names

    def test_health_check_semi_auto_includes_budget(self):
        gate = PhaseGate(initial_phase=Phase.SEMI_AUTO)
        checks = gate.evaluate_health(SwarmMetrics(
            api_healthy=True, error_count_last_hour=0,
            daily_spend_usd=5, daily_budget_usd=20,
            expiry_rate=0.1,
        ))
        names = [c.name for c in checks]
        assert "budget_not_exceeded" in names
        assert "expiry_not_worsening" in names


# ---------------------------------------------------------------------------
# PhaseGate — Status & Serialization
# ---------------------------------------------------------------------------


class TestPhaseGateSerialization:

    def test_status_structure(self):
        gate = PhaseGate()
        s = gate.status()
        assert "phase" in s
        assert "phase_label" in s
        assert "mode" in s
        assert "phase_duration_hours" in s

    def test_to_dict_includes_history(self):
        gate = PhaseGate()
        gate.set_phase(Phase.PASSIVE)
        d = gate.to_dict()
        assert "history" in d
        assert len(d["history"]) == 1

    def test_phase_duration_tracking(self):
        gate = PhaseGate()
        assert gate.phase_duration_hours >= 0
        assert gate.phase_duration_days >= 0

    def test_transition_to_dict(self):
        t = PhaseTransition(
            from_phase=Phase.PRE_FLIGHT,
            to_phase=Phase.PASSIVE,
            reason="test",
            metrics_snapshot={"worker_count": 5},
        )
        d = t.to_dict()
        assert "from" in d
        assert "to" in d
        assert "reason" in d
        assert "auto" in d

    def test_evaluate_full_auto_returns_at_max(self):
        gate = PhaseGate(initial_phase=Phase.FULL_AUTO)
        ev = gate.evaluate_advance(SwarmMetrics())
        assert ev.can_advance  # "at max" gate is passed=True
        assert ev.current_phase == Phase.FULL_AUTO
