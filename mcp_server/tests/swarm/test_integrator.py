"""
Tests for SwarmIntegrator — Top-level orchestration layer for KK V2 Swarm.

Covers:
    - SwarmMode enum
    - ComponentStatus dataclass
    - CycleResult dataclass and properties
    - Component registration and tracking
    - Lifecycle hooks (on, _fire_hooks)
    - Wiring with EventBus
    - Start/stop lifecycle
    - Mode switching (set_mode)
    - Cycle execution (run_cycle) in all modes
    - Dry-run vs live cycle
    - Phase execution (ingest, score, route, feedback, analytics, dashboard)
    - Error handling per phase
    - Consecutive error tracking + circuit breaker
    - Health checks
    - Cycle history
    - Diagnostics (wiring diagram, component names, summary)
    - Factory methods (create_minimal, create_with_components)
"""

import time
from unittest.mock import MagicMock

import pytest

from mcp_server.swarm.integrator import (
    SwarmIntegrator,
    SwarmMode,
    ComponentStatus,
    CycleResult,
)
from mcp_server.swarm.event_bus import EventBus


# ─── SwarmMode Tests ─────────────────────────────────────────────


class TestSwarmMode:
    def test_enum_values(self):
        assert SwarmMode.PASSIVE == "passive"
        assert SwarmMode.SEMI_AUTO == "semi_auto"
        assert SwarmMode.FULL_AUTO == "full_auto"
        assert SwarmMode.DISABLED == "disabled"

    def test_enum_from_string(self):
        assert SwarmMode("passive") == SwarmMode.PASSIVE
        assert SwarmMode("full_auto") == SwarmMode.FULL_AUTO


# ─── ComponentStatus Tests ───────────────────────────────────────


class TestComponentStatus:
    def test_basic_creation(self):
        status = ComponentStatus(name="event_bus", healthy=True, initialized=True)
        assert status.name == "event_bus"
        assert status.healthy is True
        assert status.initialized is True
        assert status.last_error is None
        assert status.metrics == {}

    def test_to_dict(self):
        now = time.time()
        status = ComponentStatus(
            name="coordinator",
            healthy=False,
            initialized=True,
            last_error="Connection lost",
            last_activity=now,
            metrics={"tasks": 5},
        )
        d = status.to_dict()
        assert d["name"] == "coordinator"
        assert d["healthy"] is False
        assert d["last_error"] == "Connection lost"
        assert d["metrics"] == {"tasks": 5}
        assert "s" in d["last_activity_ago"]  # e.g. "0s"

    def test_to_dict_no_activity(self):
        status = ComponentStatus(name="test", healthy=True)
        d = status.to_dict()
        assert d["last_activity_ago"] is None


# ─── CycleResult Tests ──────────────────────────────────────────


class TestCycleResult:
    def test_success_when_no_failures(self):
        result = CycleResult(
            cycle_number=1,
            mode="passive",
            started_at=time.time(),
            duration_ms=100.0,
            phases_completed=["ingest", "score", "route_sim"],
        )
        assert result.success is True

    def test_failure_when_phases_failed(self):
        result = CycleResult(
            cycle_number=1,
            mode="passive",
            started_at=time.time(),
            duration_ms=50.0,
            phases_completed=["ingest"],
            phases_failed=["score"],
            errors=["score: timeout"],
        )
        assert result.success is False

    def test_to_dict(self):
        result = CycleResult(
            cycle_number=3,
            mode="semi_auto",
            started_at=1711512000.0,
            duration_ms=250.7,
            phases_completed=["ingest", "score"],
            tasks_ingested=10,
            tasks_assigned=3,
            tasks_scored=7,
            feedback_processed=2,
            events_emitted=5,
        )
        d = result.to_dict()
        assert d["cycle"] == 3
        assert d["mode"] == "semi_auto"
        assert d["duration_ms"] == 250.7
        assert d["success"] is True
        assert d["tasks"]["ingested"] == 10
        assert d["tasks"]["assigned"] == 3

    def test_empty_result(self):
        result = CycleResult(
            cycle_number=0, mode="disabled", started_at=0, duration_ms=0
        )
        assert result.success is True
        assert result.to_dict()["errors"] == []


# ─── Component Registration ─────────────────────────────────────


class TestComponentRegistration:
    def test_set_event_bus(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        result = integrator.set_event_bus(bus)
        assert result is integrator  # fluent interface
        assert "event_bus" in integrator._component_statuses
        assert integrator._component_statuses["event_bus"].healthy is True

    def test_set_multiple_components(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        mock_coord = MagicMock()
        mock_scheduler = MagicMock()

        integrator.set_event_bus(bus)
        integrator.set_coordinator(mock_coord)
        integrator.set_scheduler(mock_scheduler)

        assert len(integrator._component_statuses) == 3
        assert all(s.initialized for s in integrator._component_statuses.values())

    def test_all_component_setters(self):
        integrator = SwarmIntegrator()
        setters = [
            "set_event_bus",
            "set_coordinator",
            "set_scheduler",
            "set_runner",
            "set_dashboard",
            "set_feedback_pipeline",
            "set_xmtp_bridge",
            "set_expiry_analyzer",
            "set_config_manager",
            "set_analytics",
        ]
        for setter_name in setters:
            getattr(integrator, setter_name)(MagicMock())

        assert len(integrator._component_statuses) == 10


# ─── Hooks ───────────────────────────────────────────────────────


class TestHooks:
    def test_register_valid_hook(self):
        integrator = SwarmIntegrator()
        called = []
        integrator.on("pre_cycle", lambda **kw: called.append(kw))
        integrator._fire_hooks("pre_cycle", cycle=1)
        assert len(called) == 1
        assert called[0]["cycle"] == 1

    def test_register_invalid_hook(self):
        integrator = SwarmIntegrator()
        with pytest.raises(ValueError, match="Unknown hook"):
            integrator.on("nonexistent", lambda: None)

    def test_multiple_hooks(self):
        integrator = SwarmIntegrator()
        results = []
        integrator.on("post_cycle", lambda **kw: results.append("a"))
        integrator.on("post_cycle", lambda **kw: results.append("b"))
        integrator._fire_hooks("post_cycle", result=None)
        assert results == ["a", "b"]

    def test_hook_error_doesnt_crash(self):
        integrator = SwarmIntegrator()

        def bad_hook(**kw):
            raise RuntimeError("hook exploded")

        results = []
        integrator.on("pre_cycle", bad_hook)
        integrator.on("pre_cycle", lambda **kw: results.append("ok"))
        integrator._fire_hooks("pre_cycle", cycle=1)
        assert results == ["ok"]  # second hook still ran


# ─── Wiring ──────────────────────────────────────────────────────


class TestWiring:
    def test_wire_with_no_bus(self):
        integrator = SwarmIntegrator()
        result = integrator.wire()
        assert result is integrator  # no-op, returns self

    def test_wire_with_bus_only(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        integrator.set_event_bus(bus)
        integrator.wire()
        # Should complete without error, 0 subscriptions (no other components)

    def test_wire_with_xmtp_bridge(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        mock_bridge = MagicMock()
        integrator.set_event_bus(bus)
        integrator.set_xmtp_bridge(mock_bridge)
        integrator.wire()
        assert integrator._component_statuses["xmtp_bridge"].healthy is True

    def test_wire_with_feedback_pipeline(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        mock_pipeline = MagicMock()
        integrator.set_event_bus(bus)
        integrator.set_feedback_pipeline(mock_pipeline)
        integrator.wire()
        # Should have wired TASK_COMPLETED → pipeline

    def test_wire_with_analytics(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        mock_analytics = MagicMock()
        mock_analytics.record_event = MagicMock()
        integrator.set_event_bus(bus)
        integrator.set_analytics(mock_analytics)
        integrator.wire()

    def test_wire_with_expiry_analyzer(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        mock_expiry = MagicMock()
        integrator.set_event_bus(bus)
        integrator.set_expiry_analyzer(mock_expiry)
        integrator.wire()


# ─── Lifecycle (Start/Stop) ──────────────────────────────────────


class TestLifecycle:
    def test_start(self):
        integrator = SwarmIntegrator()
        result = integrator.start()
        assert result["status"] == "started"
        assert result["mode"] == "passive"
        assert integrator._started is True

    def test_start_already_running(self):
        integrator = SwarmIntegrator()
        integrator.start()
        result = integrator.start()
        assert result["status"] == "already_running"

    def test_stop(self):
        integrator = SwarmIntegrator()
        integrator.start()
        result = integrator.stop()
        assert result["status"] == "stopped"
        assert "uptime_seconds" in result
        assert "cycles_completed" in result
        assert integrator._started is False

    def test_stop_not_running(self):
        integrator = SwarmIntegrator()
        result = integrator.stop()
        assert result["status"] == "not_running"

    def test_start_emits_event(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        received = []
        bus.on("swarm.started", lambda e: received.append(e))
        integrator.set_event_bus(bus)
        integrator.start()
        assert len(received) == 1

    def test_stop_emits_event(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        received = []
        bus.on("swarm.stopped", lambda e: received.append(e))
        integrator.set_event_bus(bus)
        integrator.start()
        integrator.stop()
        assert len(received) == 1


# ─── Mode Switching ──────────────────────────────────────────────


class TestModeSwitching:
    def test_set_mode(self):
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        result = integrator.set_mode(SwarmMode.SEMI_AUTO)
        assert result["old_mode"] == "passive"
        assert result["new_mode"] == "semi_auto"
        assert integrator.mode == SwarmMode.SEMI_AUTO

    def test_mode_change_fires_hook(self):
        integrator = SwarmIntegrator()
        changes = []
        integrator.on("on_mode_change", lambda **kw: changes.append(kw))
        integrator.set_mode(SwarmMode.FULL_AUTO)
        assert len(changes) == 1
        assert changes[0]["old_mode"] == SwarmMode.PASSIVE
        assert changes[0]["new_mode"] == SwarmMode.FULL_AUTO

    def test_mode_change_emits_event(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        received = []
        bus.on("swarm.mode_changed", lambda e: received.append(e))
        integrator.set_event_bus(bus)
        integrator.set_mode(SwarmMode.DISABLED)
        assert len(received) == 1


# ─── Cycle Execution ─────────────────────────────────────────────


class TestCycleExecution:
    def test_basic_dry_run_cycle(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        integrator.set_event_bus(bus)
        integrator.wire()
        integrator.start()

        result = integrator.run_cycle(dry_run=True)
        assert isinstance(result, CycleResult)
        assert result.cycle_number == 1
        assert result.mode == "passive"
        assert result.duration_ms >= 0
        assert result.success is True

    def test_cycle_increments_count(self):
        integrator = SwarmIntegrator()
        integrator.start()
        integrator.run_cycle(dry_run=True)
        integrator.run_cycle(dry_run=True)
        integrator.run_cycle(dry_run=True)
        assert integrator._cycle_count == 3

    def test_cycle_with_coordinator_ingest(self):
        integrator = SwarmIntegrator()
        mock_coord = MagicMock()
        mock_coord.ingest_live_tasks.return_value = 5
        mock_coord.simulate_routing.return_value = {"assigned": 2}

        integrator.set_coordinator(mock_coord)
        result = integrator.run_cycle(dry_run=True)

        assert result.tasks_ingested == 5
        assert "ingest" in result.phases_completed

    def test_cycle_with_scheduler(self):
        integrator = SwarmIntegrator()
        mock_scheduler = MagicMock()
        mock_scheduler.score_tasks.return_value = 8

        integrator.set_scheduler(mock_scheduler)
        result = integrator.run_cycle()

        assert result.tasks_scored == 8
        assert "score" in result.phases_completed

    def test_cycle_passive_mode_simulates(self):
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        mock_coord = MagicMock()
        mock_coord.simulate_routing.return_value = {"assigned": 3}
        mock_coord.ingest_live_tasks.return_value = 0

        integrator.set_coordinator(mock_coord)
        result = integrator.run_cycle()

        assert "route_sim" in result.phases_completed
        mock_coord.route_tasks.assert_not_called()

    def test_cycle_semi_auto_routes_with_threshold(self):
        integrator = SwarmIntegrator(mode=SwarmMode.SEMI_AUTO, bounty_threshold=0.50)
        bus = EventBus()
        mock_coord = MagicMock()
        mock_coord.ingest_live_tasks.return_value = 0
        mock_coord.route_tasks.return_value = 2

        integrator.set_event_bus(bus)
        integrator.set_coordinator(mock_coord)
        result = integrator.run_cycle()

        mock_coord.route_tasks.assert_called_once_with(max_bounty=0.50)
        assert result.tasks_assigned == 2
        assert "route" in result.phases_completed

    def test_cycle_full_auto_routes_all(self):
        integrator = SwarmIntegrator(mode=SwarmMode.FULL_AUTO)
        bus = EventBus()
        mock_coord = MagicMock()
        mock_coord.ingest_live_tasks.return_value = 0
        mock_coord.route_tasks.return_value = 4

        integrator.set_event_bus(bus)
        integrator.set_coordinator(mock_coord)
        result = integrator.run_cycle()

        mock_coord.route_tasks.assert_called_once_with()
        assert result.tasks_assigned == 4

    def test_cycle_disabled_mode_skips_routing(self):
        integrator = SwarmIntegrator(mode=SwarmMode.DISABLED)
        mock_coord = MagicMock()
        integrator.set_coordinator(mock_coord)
        integrator.run_cycle()

        mock_coord.route_tasks.assert_not_called()
        mock_coord.simulate_routing.assert_not_called()

    def test_cycle_with_feedback_pipeline(self):
        integrator = SwarmIntegrator()
        mock_fp = MagicMock()
        mock_fp.process_live.return_value = 3

        integrator.set_feedback_pipeline(mock_fp)
        result = integrator.run_cycle()

        assert result.feedback_processed == 3
        assert "feedback" in result.phases_completed

    def test_cycle_with_analytics(self):
        integrator = SwarmIntegrator()
        mock_analytics = MagicMock()

        integrator.set_analytics(mock_analytics)
        result = integrator.run_cycle()

        mock_analytics.flush.assert_called_once()
        assert "analytics" in result.phases_completed

    def test_cycle_with_dashboard(self):
        integrator = SwarmIntegrator()
        mock_dash = MagicMock()

        integrator.set_dashboard(mock_dash)
        result = integrator.run_cycle()

        mock_dash.refresh.assert_called_once()
        assert "dashboard" in result.phases_completed

    def test_cycle_fires_hooks(self):
        integrator = SwarmIntegrator()
        pre_cycles = []
        post_cycles = []
        integrator.on("pre_cycle", lambda **kw: pre_cycles.append(kw))
        integrator.on("post_cycle", lambda **kw: post_cycles.append(kw))

        integrator.run_cycle()

        assert len(pre_cycles) == 1
        assert pre_cycles[0]["cycle"] == 1
        assert len(post_cycles) == 1
        assert isinstance(post_cycles[0]["result"], CycleResult)

    def test_cycle_emits_events(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        events = []
        bus.on("swarm.cycle.end", lambda e: events.append(e))
        integrator.set_event_bus(bus)

        integrator.run_cycle()

        assert len(events) == 1


# ─── Phase Error Handling ────────────────────────────────────────


class TestPhaseErrors:
    def test_ingest_error_recorded(self):
        integrator = SwarmIntegrator()
        mock_coord = MagicMock()
        mock_coord.ingest_live_tasks.side_effect = RuntimeError("API down")

        integrator.set_coordinator(mock_coord)
        result = integrator.run_cycle()

        assert "ingest" in result.phases_failed
        assert any("ingest" in e for e in result.errors)

    def test_score_error_recorded(self):
        integrator = SwarmIntegrator()
        mock_sched = MagicMock()
        mock_sched.score_tasks.side_effect = ValueError("bad data")

        integrator.set_scheduler(mock_sched)
        result = integrator.run_cycle()

        assert "score" in result.phases_failed

    def test_route_error_recorded(self):
        integrator = SwarmIntegrator(mode=SwarmMode.FULL_AUTO)
        mock_coord = MagicMock()
        mock_coord.ingest_live_tasks.return_value = 0
        mock_coord.route_tasks.side_effect = ConnectionError("lost connection")

        integrator.set_coordinator(mock_coord)
        result = integrator.run_cycle()

        assert "route" in result.phases_failed

    def test_feedback_error_recorded(self):
        integrator = SwarmIntegrator()
        mock_fp = MagicMock()
        mock_fp.process_live.side_effect = TypeError("unexpected type")

        integrator.set_feedback_pipeline(mock_fp)
        result = integrator.run_cycle()

        assert "feedback" in result.phases_failed

    def test_analytics_error_recorded(self):
        integrator = SwarmIntegrator()
        mock_analytics = MagicMock()
        mock_analytics.flush.side_effect = IOError("disk full")

        integrator.set_analytics(mock_analytics)
        result = integrator.run_cycle()

        assert "analytics" in result.phases_failed

    def test_dashboard_error_recorded(self):
        integrator = SwarmIntegrator()
        mock_dash = MagicMock()
        mock_dash.refresh.side_effect = RuntimeError("template error")

        integrator.set_dashboard(mock_dash)
        result = integrator.run_cycle()

        assert "dashboard" in result.phases_failed

    def test_phase_error_marks_component_unhealthy(self):
        integrator = SwarmIntegrator()
        mock_coord = MagicMock()
        mock_coord.ingest_live_tasks.side_effect = RuntimeError("fail")
        integrator.set_coordinator(mock_coord)

        integrator.run_cycle()

        assert integrator._component_statuses["coordinator"].healthy is False
        assert integrator._component_statuses["coordinator"].last_error is not None


# ─── Consecutive Errors & Circuit Breaker ────────────────────────


class TestCircuitBreaker:
    def test_successful_cycle_resets_errors(self):
        integrator = SwarmIntegrator()
        integrator._consecutive_errors = 3
        integrator.run_cycle()
        assert integrator._consecutive_errors == 0

    def test_failed_cycle_increments_errors(self):
        integrator = SwarmIntegrator()
        mock_coord = MagicMock()
        mock_coord.ingest_live_tasks.side_effect = RuntimeError("fail")
        integrator.set_coordinator(mock_coord)

        integrator.run_cycle()
        assert integrator._consecutive_errors == 1
        integrator.run_cycle()
        assert integrator._consecutive_errors == 2

    def test_circuit_broken_after_max_errors(self):
        integrator = SwarmIntegrator(max_cycle_errors=3)
        mock_coord = MagicMock()
        mock_coord.ingest_live_tasks.side_effect = RuntimeError("fail")
        integrator.set_coordinator(mock_coord)

        for _ in range(3):
            integrator.run_cycle()

        assert integrator.is_circuit_broken() is True

    def test_circuit_not_broken_below_threshold(self):
        integrator = SwarmIntegrator(max_cycle_errors=5)
        integrator._consecutive_errors = 4
        assert integrator.is_circuit_broken() is False


# ─── Health Checks ───────────────────────────────────────────────


class TestHealth:
    def test_healthy_with_all_components(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        integrator.set_event_bus(bus)
        integrator.start()

        health = integrator.health()
        assert health["status"] == "healthy"
        assert health["running"] is True
        assert health["components"]["healthy"] == 1
        assert health["components"]["total"] == 1

    def test_degraded_with_unhealthy_component(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        integrator.set_event_bus(bus)
        integrator._mark_unhealthy("event_bus", "test error")

        health = integrator.health()
        assert health["status"] == "degraded"

    def test_is_healthy_all_ok(self):
        integrator = SwarmIntegrator()
        integrator.set_event_bus(EventBus())
        assert integrator.is_healthy() is True

    def test_is_healthy_with_failure(self):
        integrator = SwarmIntegrator()
        integrator.set_event_bus(EventBus())
        integrator._mark_unhealthy("event_bus", "broken")
        assert integrator.is_healthy() is False

    def test_health_uptime(self):
        integrator = SwarmIntegrator()
        integrator.start()
        time.sleep(0.05)
        health = integrator.health()
        assert health["uptime_seconds"] >= 0

    def test_health_cycle_info(self):
        integrator = SwarmIntegrator()
        integrator.start()
        integrator.run_cycle()
        health = integrator.health()
        assert health["cycles"]["completed"] == 1
        assert health["cycles"]["last_cycle_ago"] is not None


# ─── Cycle History ───────────────────────────────────────────────


class TestCycleHistory:
    def test_history_grows(self):
        integrator = SwarmIntegrator()
        for _ in range(5):
            integrator.run_cycle()
        history = integrator.get_cycle_history()
        assert len(history) == 5

    def test_history_limit(self):
        integrator = SwarmIntegrator()
        for _ in range(10):
            integrator.run_cycle()
        history = integrator.get_cycle_history(limit=3)
        assert len(history) == 3

    def test_history_capped_at_50(self):
        integrator = SwarmIntegrator()
        for _ in range(60):
            integrator.run_cycle()
        assert len(integrator._cycle_history) == 50


# ─── Diagnostics ─────────────────────────────────────────────────


class TestDiagnostics:
    def test_get_component_names(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        mock = MagicMock()
        integrator.set_event_bus(bus)
        integrator.set_coordinator(mock)
        names = integrator.get_component_names()
        assert "event_bus" in names
        assert "coordinator" in names

    def test_wiring_diagram(self):
        integrator = SwarmIntegrator()
        bus = EventBus()
        integrator.set_event_bus(bus)
        integrator.set_xmtp_bridge(MagicMock())
        integrator.set_feedback_pipeline(MagicMock())
        integrator.wire()

        diagram = integrator.get_wiring_diagram()
        assert "SwarmIntegrator Wiring" in diagram
        assert "passive" in diagram
        assert "event_bus" in diagram

    def test_summary(self):
        integrator = SwarmIntegrator()
        integrator.start()
        integrator.run_cycle()

        s = integrator.summary()
        assert s["mode"] == "passive"
        assert s["running"] is True
        assert s["healthy"] is True
        assert s["cycles"] == 1
        assert s["last_cycle"] is not None

    def test_summary_no_cycles(self):
        integrator = SwarmIntegrator()
        s = integrator.summary()
        assert s["cycles"] == 0
        assert s["last_cycle"] is None


# ─── Factory Methods ─────────────────────────────────────────────


class TestFactoryMethods:
    def test_create_minimal(self):
        integrator = SwarmIntegrator.create_minimal()
        assert integrator._event_bus is not None
        assert integrator.mode == SwarmMode.PASSIVE
        assert "event_bus" in integrator._component_statuses

    def test_create_minimal_custom_mode(self):
        integrator = SwarmIntegrator.create_minimal(mode=SwarmMode.SEMI_AUTO)
        assert integrator.mode == SwarmMode.SEMI_AUTO

    def test_create_with_components(self):
        mock_coord = MagicMock()
        mock_scheduler = MagicMock()

        integrator = SwarmIntegrator.create_with_components(
            mode=SwarmMode.FULL_AUTO,
            components={
                "event_bus": EventBus(),
                "coordinator": mock_coord,
                "scheduler": mock_scheduler,
            },
        )
        assert integrator.mode == SwarmMode.FULL_AUTO
        assert "coordinator" in integrator._component_statuses
        assert "scheduler" in integrator._component_statuses

    def test_create_with_unknown_component(self):
        # Unknown components should be silently ignored
        integrator = SwarmIntegrator.create_with_components(
            components={"event_bus": EventBus(), "unknown_thing": MagicMock()}
        )
        assert "unknown_thing" not in integrator._component_statuses

    def test_create_with_empty_components(self):
        integrator = SwarmIntegrator.create_with_components()
        assert len(integrator._component_statuses) == 0


# ─── Edge Cases ──────────────────────────────────────────────────


class TestIntegratorEdgeCases:
    def test_run_cycle_without_start(self):
        """Cycle should work even without explicit start."""
        integrator = SwarmIntegrator()
        result = integrator.run_cycle()
        assert result.success is True

    def test_assignment_fires_hook(self):
        integrator = SwarmIntegrator(mode=SwarmMode.FULL_AUTO)
        bus = EventBus()
        mock_coord = MagicMock()
        mock_coord.ingest_live_tasks.return_value = 0
        mock_coord.route_tasks.return_value = 3

        assignments = []
        integrator.on("on_assignment", lambda **kw: assignments.append(kw))
        integrator.set_event_bus(bus)
        integrator.set_coordinator(mock_coord)

        integrator.run_cycle()
        assert len(assignments) == 1
        assert assignments[0]["count"] == 3

    def test_no_assignment_no_hook(self):
        integrator = SwarmIntegrator(mode=SwarmMode.FULL_AUTO)
        bus = EventBus()
        mock_coord = MagicMock()
        mock_coord.ingest_live_tasks.return_value = 0
        mock_coord.route_tasks.return_value = 0

        assignments = []
        integrator.on("on_assignment", lambda **kw: assignments.append(kw))
        integrator.set_event_bus(bus)
        integrator.set_coordinator(mock_coord)

        integrator.run_cycle()
        assert len(assignments) == 0

    def test_mark_unhealthy(self):
        integrator = SwarmIntegrator()
        integrator.set_event_bus(EventBus())
        integrator._mark_unhealthy("event_bus", "test error")
        assert integrator._component_statuses["event_bus"].healthy is False
        assert integrator._component_statuses["event_bus"].last_error == "test error"

    def test_mark_unhealthy_unknown_component(self):
        integrator = SwarmIntegrator()
        integrator._mark_unhealthy("nonexistent", "error")
        # Should not raise, just no-op

    def test_touch_component_updates_time(self):
        integrator = SwarmIntegrator()
        integrator.set_event_bus(EventBus())
        old_time = integrator._component_statuses["event_bus"].last_activity
        time.sleep(0.01)
        integrator._touch_component("event_bus")
        new_time = integrator._component_statuses["event_bus"].last_activity
        assert new_time > old_time

    def test_coordinator_get_pending_count_fallback(self):
        """When coordinator has get_pending_count but not ingest_live_tasks."""
        integrator = SwarmIntegrator()
        mock_coord = MagicMock(spec=[])
        mock_coord.get_pending_count = MagicMock(return_value=7)
        # Remove ingest_live_tasks
        del mock_coord.ingest_live_tasks

        integrator.set_coordinator(mock_coord)
        result = integrator.run_cycle()
        assert result.tasks_ingested == 7

    def test_feedback_get_processed_count_fallback(self):
        """When feedback pipeline has get_processed_count but not process_live."""
        integrator = SwarmIntegrator()
        mock_fp = MagicMock(spec=[])
        mock_fp.get_processed_count = MagicMock(return_value=12)
        del mock_fp.process_live

        integrator.set_feedback_pipeline(mock_fp)
        result = integrator.run_cycle()
        assert result.feedback_processed == 12
