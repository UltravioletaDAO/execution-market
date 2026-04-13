"""
Tests for PhaseGate — Swarm activation phase management.
"""

import time

from mcp_server.swarm.phase_gate import (
    Phase,
    PhaseGate,
    PhaseEvaluation,
    SwarmMetrics,
    GateCheck,
    PHASE_LABELS,
    PHASE_MODE_MAP,
    _gates_pre_flight_to_passive,
    _gates_passive_to_semi_auto,
    _gates_semi_auto_to_full_auto,
)


# ─── Fixture: Healthy Metrics ────────────────────────────────


def healthy_metrics(**overrides) -> SwarmMetrics:
    """Create a SwarmMetrics instance with all gates passing."""
    defaults = {
        "api_healthy": True,
        "api_response_ms": 50.0,
        "swarm_enabled": True,
        "swarm_mode": "passive",
        "coordinator_active": True,
        "error_count_last_hour": 0,
        "error_count_last_24h": 0,
        "tasks_ingested": 50,
        "tasks_completed": 30,
        "tasks_expired": 5,
        "expiry_rate": 0.10,
        "worker_count": 10,
        "categories_with_workers": 4,
        "total_categories": 5,
        "worker_hhi": 0.2,
        "agents_registered": 24,
        "agents_healthy": 20,
        "daily_spend_usd": 5.0,
        "daily_budget_usd": 25.0,
        "uptime_hours": 100.0,
        "days_in_current_phase": 10.0,
    }
    defaults.update(overrides)
    return SwarmMetrics(**defaults)


def minimal_metrics(**overrides) -> SwarmMetrics:
    """Create metrics with most gates failing."""
    defaults = {
        "api_healthy": False,
        "swarm_enabled": False,
        "coordinator_active": False,
        "error_count_last_hour": 20,
        "error_count_last_24h": 100,
        "tasks_ingested": 0,
        "tasks_completed": 0,
        "worker_count": 0,
        "worker_hhi": 1.0,
        "agents_registered": 0,
        "agents_healthy": 0,
        "uptime_hours": 0.1,
        "days_in_current_phase": 0.0,
    }
    defaults.update(overrides)
    return SwarmMetrics(**defaults)


# ─── Phase Enum ───────────────────────────────────────────────


class TestPhase:
    def test_labels(self):
        for phase in Phase:
            assert phase in PHASE_LABELS

    def test_mode_map(self):
        for phase in Phase:
            assert phase in PHASE_MODE_MAP
        assert PHASE_MODE_MAP[Phase.EMERGENCY] == "disabled"
        assert PHASE_MODE_MAP[Phase.PRE_FLIGHT] == "passive"
        assert PHASE_MODE_MAP[Phase.SEMI_AUTO] == "semi_auto"
        assert PHASE_MODE_MAP[Phase.FULL_AUTO] == "full_auto"


# ─── GateCheck ────────────────────────────────────────────────


class TestGateCheck:
    def test_default_severity(self):
        gate = GateCheck(name="g", description="d", passed=True)
        assert gate.severity == "blocker"


# ─── PhaseEvaluation ─────────────────────────────────────────


class TestPhaseEvaluation:
    def test_pass_rate_empty(self):
        ev = PhaseEvaluation(
            current_phase=Phase.PRE_FLIGHT,
            target_phase=Phase.PASSIVE,
        )
        assert ev.pass_rate == 0.0


# ─── Gate Functions ───────────────────────────────────────────


class TestPreFlightToPassiveGates:
    def test_all_pass_with_healthy_metrics(self):
        m = healthy_metrics(uptime_hours=2.0, tasks_ingested=5, agents_registered=10)
        gates = _gates_pre_flight_to_passive(m)
        assert all(g.passed for g in gates)

    def test_api_unhealthy_blocks(self):
        m = healthy_metrics(api_healthy=False)
        gates = _gates_pre_flight_to_passive(m)
        api_gate = next(g for g in gates if g.name == "api_healthy")
        assert api_gate.passed is False
        assert api_gate.severity == "blocker"

    def test_swarm_not_enabled_blocks(self):
        m = healthy_metrics(swarm_enabled=False)
        gates = _gates_pre_flight_to_passive(m)
        swarm_gate = next(g for g in gates if g.name == "swarm_enabled")
        assert swarm_gate.passed is False

    def test_coordinator_inactive_blocks(self):
        m = healthy_metrics(coordinator_active=False)
        gates = _gates_pre_flight_to_passive(m)
        coord_gate = next(g for g in gates if g.name == "coordinator_active")
        assert coord_gate.passed is False

    def test_errors_block(self):
        m = healthy_metrics(error_count_last_hour=3)
        gates = _gates_pre_flight_to_passive(m)
        err_gate = next(g for g in gates if g.name == "no_errors_1h")
        assert err_gate.passed is False

    def test_insufficient_uptime_blocks(self):
        m = healthy_metrics(uptime_hours=0.5)
        gates = _gates_pre_flight_to_passive(m)
        up_gate = next(g for g in gates if g.name == "uptime_min")
        assert up_gate.passed is False

    def test_no_tasks_is_warning_not_blocker(self):
        m = healthy_metrics(tasks_ingested=0)
        gates = _gates_pre_flight_to_passive(m)
        task_gate = next(g for g in gates if g.name == "tasks_ingested")
        assert task_gate.passed is False
        assert task_gate.severity == "warning"

    def test_no_agents_is_warning_not_blocker(self):
        m = healthy_metrics(agents_registered=0)
        gates = _gates_pre_flight_to_passive(m)
        agent_gate = next(g for g in gates if g.name == "agents_registered")
        assert agent_gate.passed is False
        assert agent_gate.severity == "warning"


class TestPassiveToSemiAutoGates:
    def test_all_pass_with_healthy_metrics(self):
        m = healthy_metrics(days_in_current_phase=5.0, agents_healthy=10)
        gates = _gates_passive_to_semi_auto(m)
        assert all(g.passed for g in gates)

    def test_insufficient_observation_days(self):
        m = healthy_metrics(days_in_current_phase=1.0)
        gates = _gates_passive_to_semi_auto(m)
        day_gate = next(g for g in gates if g.name == "min_observation_days")
        assert day_gate.passed is False

    def test_too_many_errors_blocks(self):
        m = healthy_metrics(error_count_last_24h=10)
        gates = _gates_passive_to_semi_auto(m)
        err_gate = next(g for g in gates if g.name == "no_errors_24h")
        assert err_gate.passed is False

    def test_insufficient_tasks_blocks(self):
        m = healthy_metrics(tasks_ingested=3)
        gates = _gates_passive_to_semi_auto(m)
        task_gate = next(g for g in gates if g.name == "tasks_ingested")
        assert task_gate.passed is False

    def test_no_workers_blocks(self):
        m = healthy_metrics(worker_count=1)
        gates = _gates_passive_to_semi_auto(m)
        worker_gate = next(g for g in gates if g.name == "worker_count")
        assert worker_gate.passed is False

    def test_insufficient_agents_blocks(self):
        m = healthy_metrics(agents_healthy=2)
        gates = _gates_passive_to_semi_auto(m)
        agent_gate = next(g for g in gates if g.name == "agents_healthy")
        assert agent_gate.passed is False

    def test_low_category_coverage_is_warning(self):
        m = healthy_metrics(categories_with_workers=1)
        gates = _gates_passive_to_semi_auto(m)
        cat_gate = next(g for g in gates if g.name == "categories_coverage")
        assert cat_gate.passed is False
        assert cat_gate.severity == "warning"


class TestSemiAutoToFullAutoGates:
    def test_all_pass_with_healthy_metrics(self):
        m = healthy_metrics(days_in_current_phase=10.0)
        gates = _gates_semi_auto_to_full_auto(m)
        assert all(g.passed for g in gates)

    def test_insufficient_days(self):
        m = healthy_metrics(days_in_current_phase=3.0)
        gates = _gates_semi_auto_to_full_auto(m)
        day_gate = next(g for g in gates if g.name == "min_semi_auto_days")
        assert day_gate.passed is False

    def test_high_expiry_rate_blocks(self):
        m = healthy_metrics(expiry_rate=0.35)
        gates = _gates_semi_auto_to_full_auto(m)
        exp_gate = next(g for g in gates if g.name == "expiry_rate")
        assert exp_gate.passed is False

    def test_worker_monopoly_blocks(self):
        m = healthy_metrics(worker_hhi=0.8)
        gates = _gates_semi_auto_to_full_auto(m)
        hhi_gate = next(g for g in gates if g.name == "worker_concentration")
        assert hhi_gate.passed is False

    def test_insufficient_completions_blocks(self):
        m = healthy_metrics(tasks_completed=5)
        gates = _gates_semi_auto_to_full_auto(m)
        comp_gate = next(g for g in gates if g.name == "tasks_completed")
        assert comp_gate.passed is False

    def test_budget_overspend_blocks(self):
        m = healthy_metrics(daily_spend_usd=22.0, daily_budget_usd=25.0)
        gates = _gates_semi_auto_to_full_auto(m)
        budget_gate = next(g for g in gates if g.name == "budget_under_control")
        assert budget_gate.passed is False  # 22/25 = 88% > 80%

    def test_budget_zero_passes(self):
        """When budget is 0, budget gate passes (no limit set)."""
        m = healthy_metrics(daily_budget_usd=0.0, daily_spend_usd=0.0)
        gates = _gates_semi_auto_to_full_auto(m)
        budget_gate = next(g for g in gates if g.name == "budget_under_control")
        assert budget_gate.passed is True


# ─── PhaseGate Core ───────────────────────────────────────────


class TestPhaseGateInit:
    def test_default_phase(self):
        gate = PhaseGate()
        assert gate.phase == Phase.PRE_FLIGHT

    def test_custom_initial_phase(self):
        gate = PhaseGate(initial_phase=Phase.PASSIVE)
        assert gate.phase == Phase.PASSIVE

    def test_phase_label(self):
        gate = PhaseGate()
        assert "Pre-Flight" in gate.phase_label

    def test_mode(self):
        gate = PhaseGate()
        assert gate.mode == "passive"

        gate = PhaseGate(initial_phase=Phase.SEMI_AUTO)
        assert gate.mode == "semi_auto"

    def test_empty_history(self):
        gate = PhaseGate()
        assert gate.history == []


class TestPhaseGateSetPhase:
    def test_set_same_phase_no_history(self):
        gate = PhaseGate()
        gate.set_phase(Phase.PRE_FLIGHT, reason="same")
        assert len(gate.history) == 0

    def test_clears_emergency(self):
        gate = PhaseGate()
        gate.emergency_stop("test")
        assert gate.phase == Phase.EMERGENCY

        gate.set_phase(Phase.PRE_FLIGHT, reason="cleared")
        assert gate.phase == Phase.PRE_FLIGHT


class TestPhaseGateEmergencyStop:
    def test_emergency_blocks_advance(self):
        gate = PhaseGate()
        gate.emergency_stop("test")

        ev = gate.evaluate_advance(healthy_metrics())
        assert ev.can_advance is False
        assert "manually cleared" in ev.blockers[0].lower()


class TestPhaseGateEvaluateAdvance:
    def test_pre_flight_passes(self):
        gate = PhaseGate(initial_phase=Phase.PRE_FLIGHT)
        m = healthy_metrics(uptime_hours=2.0)
        ev = gate.evaluate_advance(m)
        # Gates pass but days_in_current_phase is auto-injected from gate duration
        # Since we just created the gate, duration ≈ 0, but uptime_min checks uptime_hours
        assert isinstance(ev, PhaseEvaluation)
        assert ev.target_phase == Phase.PASSIVE

    def test_full_auto_already_max(self):
        gate = PhaseGate(initial_phase=Phase.FULL_AUTO)
        ev = gate.evaluate_advance(healthy_metrics())
        assert ev.can_advance is True  # "at max" gate passes
        assert ev.target_phase == Phase.FULL_AUTO

    def test_injects_days_in_current_phase(self):
        gate = PhaseGate(initial_phase=Phase.PASSIVE)
        # Hack: set phase start to 5 days ago
        gate._phase_start = time.time() - (5 * 24 * 3600)

        m = healthy_metrics()
        gate.evaluate_advance(m)

        # The metrics should have been updated with ~5 days
        assert m.days_in_current_phase >= 4.9


class TestPhaseGateAdvance:
    def test_advance_with_passing_gates(self):
        gate = PhaseGate(initial_phase=Phase.PRE_FLIGHT)
        # Need uptime >= 1h
        m = healthy_metrics(uptime_hours=2.0)

        transition = gate.advance(m, reason="all gates pass")
        assert transition is not None
        assert gate.phase == Phase.PASSIVE
        assert transition.from_phase == Phase.PRE_FLIGHT
        assert transition.to_phase == Phase.PASSIVE

    def test_advance_blocked_by_failing_gates(self):
        gate = PhaseGate(initial_phase=Phase.PRE_FLIGHT)
        m = minimal_metrics()

        transition = gate.advance(m)
        assert transition is None
        assert gate.phase == Phase.PRE_FLIGHT  # Unchanged

    def test_force_advance(self):
        gate = PhaseGate(initial_phase=Phase.PRE_FLIGHT)
        m = minimal_metrics()

        transition = gate.advance(m, reason="override", force=True)
        assert transition is not None
        assert gate.phase == Phase.PASSIVE
        assert "FORCED" in transition.reason

    def test_cannot_advance_past_full_auto(self):
        gate = PhaseGate(initial_phase=Phase.FULL_AUTO)
        m = healthy_metrics()

        transition = gate.advance(m)
        assert transition is None
        assert gate.phase == Phase.FULL_AUTO

    def test_cannot_advance_from_emergency_without_force(self):
        gate = PhaseGate()
        gate.emergency_stop("test")

        transition = gate.advance(healthy_metrics())
        assert transition is None

    def test_force_advance_from_emergency(self):
        gate = PhaseGate()
        gate.emergency_stop("test")

        transition = gate.advance(healthy_metrics(), force=True, reason="cleared")
        assert transition is not None
        assert gate.phase == Phase.PRE_FLIGHT

    def test_metrics_snapshot_in_transition(self):
        gate = PhaseGate(initial_phase=Phase.PRE_FLIGHT)
        m = healthy_metrics(uptime_hours=2.0, expiry_rate=0.15, worker_count=8)

        transition = gate.advance(m)
        assert transition is not None
        assert transition.metrics_snapshot["expiry_rate"] == 0.15
        assert transition.metrics_snapshot["worker_count"] == 8


class TestPhaseGateAdvanceFullJourney:
    """Test advancing through all phases."""

    def test_full_journey(self):
        gate = PhaseGate(initial_phase=Phase.PRE_FLIGHT)

        # Phase 0 → 1
        m = healthy_metrics(uptime_hours=2.0)
        t1 = gate.advance(m)
        assert t1 is not None
        assert gate.phase == Phase.PASSIVE

        # Phase 1 → 2: need 3+ days
        gate._phase_start = time.time() - (4 * 24 * 3600)
        m = healthy_metrics(agents_healthy=10)
        t2 = gate.advance(m)
        assert t2 is not None
        assert gate.phase == Phase.SEMI_AUTO

        # Phase 2 → 3: need 7+ days
        gate._phase_start = time.time() - (8 * 24 * 3600)
        m = healthy_metrics()
        t3 = gate.advance(m)
        assert t3 is not None
        assert gate.phase == Phase.FULL_AUTO

        # History should have all transitions
        assert len(gate.history) == 3


class TestPhaseGateHealth:
    def test_health_checks_passive(self):
        gate = PhaseGate(initial_phase=Phase.PASSIVE)
        m = healthy_metrics()
        checks = gate.evaluate_health(m)
        assert all(c.passed for c in checks)

    def test_health_error_rate_fails(self):
        gate = PhaseGate(initial_phase=Phase.PASSIVE)
        m = healthy_metrics(error_count_last_hour=15)
        checks = gate.evaluate_health(m)
        err_check = next(c for c in checks if c.name == "error_rate")
        assert err_check.passed is False

    def test_health_budget_exceeded(self):
        gate = PhaseGate(initial_phase=Phase.SEMI_AUTO)
        m = healthy_metrics(daily_spend_usd=30.0, daily_budget_usd=25.0)
        checks = gate.evaluate_health(m)
        budget_check = next(c for c in checks if c.name == "budget_not_exceeded")
        assert budget_check.passed is False

    def test_health_high_expiry(self):
        gate = PhaseGate(initial_phase=Phase.SEMI_AUTO)
        m = healthy_metrics(expiry_rate=0.55)
        checks = gate.evaluate_health(m)
        exp_check = next(c for c in checks if c.name == "expiry_not_worsening")
        assert exp_check.passed is False

    def test_health_pre_flight_minimal(self):
        gate = PhaseGate(initial_phase=Phase.PRE_FLIGHT)
        m = healthy_metrics()
        checks = gate.evaluate_health(m)
        # Only api_reachable at pre-flight
        assert len(checks) == 1
        assert checks[0].name == "api_reachable"


class TestPhaseGateEmergencyDetection:
    def test_runaway_spending(self):
        gate = PhaseGate(initial_phase=Phase.SEMI_AUTO)
        m = healthy_metrics(daily_spend_usd=60.0, daily_budget_usd=25.0)
        should_stop, reason = gate.should_emergency_stop(m)
        assert should_stop is True
        assert "2x budget" in reason

    def test_error_storm(self):
        gate = PhaseGate(initial_phase=Phase.PASSIVE)
        m = healthy_metrics(error_count_last_hour=100)
        should_stop, reason = gate.should_emergency_stop(m)
        assert should_stop is True
        assert "Error storm" in reason

    def test_api_down(self):
        gate = PhaseGate(initial_phase=Phase.PASSIVE)
        m = healthy_metrics(api_healthy=False, uptime_hours=1.0)
        should_stop, reason = gate.should_emergency_stop(m)
        assert should_stop is True
        assert "unreachable" in reason

    def test_no_emergency_when_healthy(self):
        gate = PhaseGate(initial_phase=Phase.FULL_AUTO)
        m = healthy_metrics()
        should_stop, _ = gate.should_emergency_stop(m)
        assert should_stop is False

    def test_no_emergency_in_pre_flight(self):
        gate = PhaseGate(initial_phase=Phase.PRE_FLIGHT)
        m = minimal_metrics(error_count_last_hour=100)
        should_stop, _ = gate.should_emergency_stop(m)
        assert should_stop is False  # Pre-flight is safe


class TestPhaseGateStatus:
    def test_status_dict(self):
        gate = PhaseGate(initial_phase=Phase.PASSIVE)
        s = gate.status()
        assert s["phase"] == Phase.PASSIVE.value
        assert "Passive" in s["phase_label"]
        assert s["mode"] == "passive"
        assert "phase_duration_hours" in s


class TestSwarmMetrics:
    def test_defaults(self):
        m = SwarmMetrics()
        assert m.api_healthy is False
        assert m.worker_count == 0
        assert m.expiry_rate == 0.0

    def test_custom_values(self):
        m = SwarmMetrics(worker_count=10, expiry_rate=0.15)
        assert m.worker_count == 10
        assert m.expiry_rate == 0.15
