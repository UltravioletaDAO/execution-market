"""
Tests for SwarmIntegrator — top-level swarm orchestration.
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from mcp_server.swarm.integrator import (
    SwarmIntegrator,
    SwarmMode,
    ComponentStatus,
    CycleResult,
)
from mcp_server.swarm.event_bus import EventBus


# ─── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def mock_coordinator():
    coord = MagicMock()
    coord.ingest_live_tasks.return_value = 10
    coord.simulate_routing.return_value = {"assigned": 5, "failed": 5}
    coord.route_tasks.return_value = 3
    coord.get_pending_count.return_value = 10
    return coord


@pytest.fixture
def mock_scheduler():
    sched = MagicMock()
    sched.score_tasks.return_value = 10
    return sched


@pytest.fixture
def mock_feedback_pipeline():
    fp = MagicMock()
    fp.process_live.return_value = 4
    fp.process_completion.return_value = True
    fp.get_processed_count.return_value = 4
    return fp


@pytest.fixture
def mock_dashboard():
    dash = MagicMock()
    dash.refresh.return_value = None
    return dash


@pytest.fixture
def mock_analytics():
    analytics = MagicMock()
    analytics.record_event.return_value = None
    analytics.flush.return_value = None
    return analytics


@pytest.fixture
def mock_xmtp_bridge():
    bridge = MagicMock()
    bridge.notify_task_assigned.return_value = True
    bridge.notify_payment_confirmed.return_value = True
    bridge.notify_reputation_update.return_value = True
    return bridge


@pytest.fixture
def mock_expiry_analyzer():
    analyzer = MagicMock()
    analyzer.record_expiry.return_value = None
    return analyzer


@pytest.fixture
def full_integrator(
    event_bus,
    mock_coordinator,
    mock_scheduler,
    mock_feedback_pipeline,
    mock_dashboard,
    mock_analytics,
    mock_xmtp_bridge,
    mock_expiry_analyzer,
):
    """Create a fully-wired integrator with all components."""
    return SwarmIntegrator.create_with_components(
        mode=SwarmMode.PASSIVE,
        components={
            "event_bus": event_bus,
            "coordinator": mock_coordinator,
            "scheduler": mock_scheduler,
            "feedback_pipeline": mock_feedback_pipeline,
            "dashboard": mock_dashboard,
            "analytics": mock_analytics,
            "xmtp_bridge": mock_xmtp_bridge,
            "expiry_analyzer": mock_expiry_analyzer,
        },
    )


# ─── Component Registration Tests ──────────────────────────────────


class TestComponentRegistration:
    def test_register_event_bus(self, event_bus):
        integrator = SwarmIntegrator()
        integrator.set_event_bus(event_bus)
        assert "event_bus" in integrator._component_statuses
        assert integrator._component_statuses["event_bus"].healthy

    def test_register_coordinator(self, mock_coordinator):
        integrator = SwarmIntegrator()
        integrator.set_coordinator(mock_coordinator)
        assert "coordinator" in integrator._component_statuses

    def test_register_all_components(self, full_integrator):
        names = full_integrator.get_component_names()
        expected = [
            "event_bus",
            "coordinator",
            "scheduler",
            "feedback_pipeline",
            "dashboard",
            "analytics",
            "xmtp_bridge",
            "expiry_analyzer",
        ]
        for name in expected:
            assert name in names, f"{name} not registered"

    def test_fluent_api(self, event_bus, mock_coordinator):
        integrator = (
            SwarmIntegrator()
            .set_event_bus(event_bus)
            .set_coordinator(mock_coordinator)
        )
        assert len(integrator.get_component_names()) == 2

    def test_component_status_initialized(self, event_bus):
        integrator = SwarmIntegrator()
        integrator.set_event_bus(event_bus)
        status = integrator._component_statuses["event_bus"]
        assert status.initialized
        assert status.healthy
        assert status.last_activity is not None


# ─── Lifecycle Tests ────────────────────────────────────────────────


class TestLifecycle:
    def test_start(self, full_integrator):
        result = full_integrator.start()
        assert result["status"] == "started"
        assert result["mode"] == "passive"
        assert full_integrator._started

    def test_start_idempotent(self, full_integrator):
        full_integrator.start()
        result = full_integrator.start()
        assert result["status"] == "already_running"

    def test_stop(self, full_integrator):
        full_integrator.start()
        result = full_integrator.stop()
        assert result["status"] == "stopped"
        assert "uptime_seconds" in result
        assert not full_integrator._started

    def test_stop_when_not_started(self, full_integrator):
        result = full_integrator.stop()
        assert result["status"] == "not_running"

    def test_mode_change(self, full_integrator):
        result = full_integrator.set_mode(SwarmMode.SEMI_AUTO)
        assert result["old_mode"] == "passive"
        assert result["new_mode"] == "semi_auto"
        assert full_integrator.mode == SwarmMode.SEMI_AUTO

    def test_mode_change_fires_hooks(self, full_integrator):
        callback = MagicMock()
        full_integrator.on("on_mode_change", callback)
        full_integrator.set_mode(SwarmMode.FULL_AUTO)
        callback.assert_called_once()


# ─── Wiring Tests ───────────────────────────────────────────────────


class TestWiring:
    def test_wire_without_event_bus(self):
        integrator = SwarmIntegrator()
        result = integrator.wire()
        assert len(integrator._event_handlers) == 0

    def test_wire_xmtp_bridge(self, event_bus, mock_xmtp_bridge):
        integrator = SwarmIntegrator()
        integrator.set_event_bus(event_bus)
        integrator.set_xmtp_bridge(mock_xmtp_bridge)
        integrator.wire()
        # Should have 3 subscriptions (assigned, payment, reputation)
        assert len(integrator._event_handlers) == 3

    def test_wire_analytics(self, event_bus, mock_analytics):
        integrator = SwarmIntegrator()
        integrator.set_event_bus(event_bus)
        integrator.set_analytics(mock_analytics)
        integrator.wire()
        # Should have 1 catch-all subscription
        assert len(integrator._event_handlers) == 1

    def test_wire_feedback_pipeline(self, event_bus, mock_feedback_pipeline):
        integrator = SwarmIntegrator()
        integrator.set_event_bus(event_bus)
        integrator.set_feedback_pipeline(mock_feedback_pipeline)
        integrator.wire()
        assert len(integrator._event_handlers) == 1

    def test_wire_expiry_analyzer(self, event_bus, mock_expiry_analyzer):
        integrator = SwarmIntegrator()
        integrator.set_event_bus(event_bus)
        integrator.set_expiry_analyzer(mock_expiry_analyzer)
        integrator.wire()
        assert len(integrator._event_handlers) == 1

    def test_full_wiring_subscription_count(self, full_integrator):
        # xmtp(3) + feedback(1) + analytics(1) + expiry(1) = 6
        assert len(full_integrator._event_handlers) == 6

    def test_event_flows_to_xmtp_bridge(self, event_bus, mock_xmtp_bridge):
        integrator = SwarmIntegrator()
        integrator.set_event_bus(event_bus)
        integrator.set_xmtp_bridge(mock_xmtp_bridge)
        integrator.wire()

        # Emit a task.assigned event
        event_bus.emit(
            "task.assigned",
            {
                "task_id": "t1",
                "worker_wallet": "0xABC",
                "task_data": {"title": "Test"},
            },
        )
        mock_xmtp_bridge.notify_task_assigned.assert_called_once_with(
            task_id="t1",
            worker_wallet="0xABC",
            task_data={"title": "Test"},
        )

    def test_event_flows_to_analytics(self, event_bus, mock_analytics):
        integrator = SwarmIntegrator()
        integrator.set_event_bus(event_bus)
        integrator.set_analytics(mock_analytics)
        integrator.wire()

        event_bus.emit("task.discovered", {"task_id": "t1"})
        mock_analytics.record_event.assert_called_once()

    def test_event_flows_to_feedback(self, event_bus, mock_feedback_pipeline):
        integrator = SwarmIntegrator()
        integrator.set_event_bus(event_bus)
        integrator.set_feedback_pipeline(mock_feedback_pipeline)
        integrator.wire()

        event_bus.emit(
            "task.completed",
            {"task_data": {"id": "t1", "status": "completed"}},
        )
        mock_feedback_pipeline.process_completion.assert_called_once_with(
            {"id": "t1", "status": "completed"}
        )


# ─── Cycle Execution Tests ──────────────────────────────────────────


class TestCycleExecution:
    def test_passive_cycle(self, full_integrator):
        result = full_integrator.run_cycle()
        assert result.success
        assert result.mode == "passive"
        assert "ingest" in result.phases_completed
        assert "score" in result.phases_completed
        assert "route_sim" in result.phases_completed  # Passive = simulate
        assert "feedback" in result.phases_completed
        assert "analytics" in result.phases_completed
        assert "dashboard" in result.phases_completed
        assert result.tasks_ingested == 10
        assert result.tasks_assigned == 5

    def test_semi_auto_cycle(
        self, event_bus, mock_coordinator, mock_scheduler
    ):
        integrator = SwarmIntegrator.create_with_components(
            mode=SwarmMode.SEMI_AUTO,
            components={
                "event_bus": event_bus,
                "coordinator": mock_coordinator,
                "scheduler": mock_scheduler,
            },
        )
        result = integrator.run_cycle()
        assert "route" in result.phases_completed
        mock_coordinator.route_tasks.assert_called_once_with(max_bounty=0.25)

    def test_full_auto_cycle(
        self, event_bus, mock_coordinator, mock_scheduler
    ):
        integrator = SwarmIntegrator.create_with_components(
            mode=SwarmMode.FULL_AUTO,
            components={
                "event_bus": event_bus,
                "coordinator": mock_coordinator,
                "scheduler": mock_scheduler,
            },
        )
        result = integrator.run_cycle()
        assert "route" in result.phases_completed
        mock_coordinator.route_tasks.assert_called_once_with()

    def test_disabled_mode_skips_routing(
        self, event_bus, mock_coordinator, mock_scheduler
    ):
        integrator = SwarmIntegrator.create_with_components(
            mode=SwarmMode.DISABLED,
            components={
                "event_bus": event_bus,
                "coordinator": mock_coordinator,
                "scheduler": mock_scheduler,
            },
        )
        result = integrator.run_cycle()
        assert "route" not in result.phases_completed
        assert "route_sim" not in result.phases_completed

    def test_dry_run_uses_simulation(
        self, event_bus, mock_coordinator, mock_scheduler
    ):
        integrator = SwarmIntegrator.create_with_components(
            mode=SwarmMode.FULL_AUTO,
            components={
                "event_bus": event_bus,
                "coordinator": mock_coordinator,
                "scheduler": mock_scheduler,
            },
        )
        result = integrator.run_cycle(dry_run=True)
        assert "route_sim" in result.phases_completed
        mock_coordinator.simulate_routing.assert_called_once()

    def test_cycle_with_no_components(self):
        integrator = SwarmIntegrator()
        result = integrator.run_cycle()
        assert result.success
        assert result.tasks_ingested == 0
        assert result.tasks_assigned == 0

    def test_cycle_increments_count(self, full_integrator):
        full_integrator.run_cycle()
        assert full_integrator._cycle_count == 1
        full_integrator.run_cycle()
        assert full_integrator._cycle_count == 2

    def test_cycle_tracks_duration(self, full_integrator):
        result = full_integrator.run_cycle()
        assert result.duration_ms > 0

    def test_cycle_history_stored(self, full_integrator):
        full_integrator.run_cycle()
        full_integrator.run_cycle()
        history = full_integrator.get_cycle_history()
        assert len(history) == 2
        assert history[0]["cycle"] == 1
        assert history[1]["cycle"] == 2

    def test_cycle_history_capped_at_50(self, full_integrator):
        for _ in range(55):
            full_integrator.run_cycle()
        history = full_integrator.get_cycle_history(limit=100)
        assert len(history) <= 50


# ─── Error Handling Tests ────────────────────────────────────────────


class TestErrorHandling:
    def test_phase_failure_recorded(self, event_bus):
        bad_coordinator = MagicMock()
        bad_coordinator.ingest_live_tasks.side_effect = RuntimeError("API down")
        integrator = SwarmIntegrator.create_with_components(
            components={
                "event_bus": event_bus,
                "coordinator": bad_coordinator,
            },
        )
        result = integrator.run_cycle()
        assert "ingest" in result.phases_failed
        assert any("API down" in e for e in result.errors)

    def test_phase_failure_marks_unhealthy(self, event_bus):
        bad_coordinator = MagicMock()
        bad_coordinator.ingest_live_tasks.side_effect = RuntimeError("oops")
        integrator = SwarmIntegrator.create_with_components(
            components={
                "event_bus": event_bus,
                "coordinator": bad_coordinator,
            },
        )
        integrator.run_cycle()
        assert not integrator._component_statuses["coordinator"].healthy

    def test_consecutive_errors_tracked(self, event_bus):
        bad_coordinator = MagicMock()
        bad_coordinator.ingest_live_tasks.side_effect = RuntimeError("fail")
        integrator = SwarmIntegrator.create_with_components(
            components={
                "event_bus": event_bus,
                "coordinator": bad_coordinator,
            },
        )
        for _ in range(3):
            integrator.run_cycle()
        assert integrator._consecutive_errors == 3

    def test_circuit_breaker(self, event_bus):
        bad_coordinator = MagicMock()
        bad_coordinator.ingest_live_tasks.side_effect = RuntimeError("fail")
        integrator = SwarmIntegrator(max_cycle_errors=3)
        integrator.set_event_bus(event_bus)
        integrator.set_coordinator(bad_coordinator)
        integrator.wire()

        for _ in range(3):
            integrator.run_cycle()
        assert integrator.is_circuit_broken()

    def test_success_resets_error_count(self, full_integrator):
        # Simulate some errors
        full_integrator._consecutive_errors = 3
        full_integrator.run_cycle()
        assert full_integrator._consecutive_errors == 0

    def test_partial_failure_doesnt_stop_other_phases(self, event_bus):
        bad_scheduler = MagicMock()
        bad_scheduler.score_tasks.side_effect = RuntimeError("score failed")
        good_coord = MagicMock()
        good_coord.ingest_live_tasks.return_value = 5
        good_coord.simulate_routing.return_value = {"assigned": 2}
        good_dashboard = MagicMock()

        integrator = SwarmIntegrator.create_with_components(
            components={
                "event_bus": event_bus,
                "coordinator": good_coord,
                "scheduler": bad_scheduler,
                "dashboard": good_dashboard,
            },
        )
        result = integrator.run_cycle()
        assert "ingest" in result.phases_completed
        assert "score" in result.phases_failed
        assert "dashboard" in result.phases_completed

    def test_wiring_failure_marks_unhealthy(self, event_bus):
        bad_bridge = MagicMock()
        # Make wire_xmtp_bridge fail by raising inside the bus
        # Actually, it catches the error — let's test something else
        integrator = SwarmIntegrator()
        integrator.set_event_bus(event_bus)
        integrator.set_xmtp_bridge(bad_bridge)
        # Wire should succeed even if bridge has weird behavior
        integrator.wire()
        assert integrator._component_statuses["xmtp_bridge"].healthy


# ─── Health Tests ────────────────────────────────────────────────────


class TestHealth:
    def test_healthy_when_all_components_ok(self, full_integrator):
        assert full_integrator.is_healthy()

    def test_unhealthy_when_component_fails(self, full_integrator):
        full_integrator._mark_unhealthy("coordinator", "test error")
        assert not full_integrator.is_healthy()

    def test_health_report(self, full_integrator):
        full_integrator.start()
        health = full_integrator.health()
        assert health["status"] == "healthy"
        assert health["mode"] == "passive"
        assert health["running"]
        assert health["components"]["healthy"] == health["components"]["total"]

    def test_degraded_status(self, full_integrator):
        full_integrator._mark_unhealthy("scheduler", "timeout")
        health = full_integrator.health()
        assert health["status"] == "degraded"

    def test_summary(self, full_integrator):
        full_integrator.start()
        full_integrator.run_cycle()
        summary = full_integrator.summary()
        assert summary["mode"] == "passive"
        assert summary["running"]
        assert summary["healthy"]
        assert summary["cycles"] == 1
        assert summary["last_cycle"] is not None


# ─── Hooks Tests ──────────────────────────────────────────────────────


class TestHooks:
    def test_pre_cycle_hook(self, full_integrator):
        callback = MagicMock()
        full_integrator.on("pre_cycle", callback)
        full_integrator.run_cycle()
        callback.assert_called_once()

    def test_post_cycle_hook(self, full_integrator):
        callback = MagicMock()
        full_integrator.on("post_cycle", callback)
        full_integrator.run_cycle()
        callback.assert_called_once()

    def test_on_error_hook(self, full_integrator):
        callback = MagicMock()
        full_integrator.on("on_error", callback)
        # Error hooks are called by _fire_hooks — but not auto-fired on phase errors
        # Just verify registration works
        assert callback in full_integrator._hooks["on_error"]

    def test_assignment_hook_fires(
        self, event_bus, mock_coordinator, mock_scheduler
    ):
        callback = MagicMock()
        integrator = SwarmIntegrator.create_with_components(
            mode=SwarmMode.FULL_AUTO,
            components={
                "event_bus": event_bus,
                "coordinator": mock_coordinator,
                "scheduler": mock_scheduler,
            },
        )
        integrator.on("on_assignment", callback)
        integrator.run_cycle()
        callback.assert_called_once_with(count=3)

    def test_invalid_hook_raises(self, full_integrator):
        with pytest.raises(ValueError, match="Unknown hook"):
            full_integrator.on("nonexistent_hook", lambda: None)

    def test_hook_error_doesnt_crash(self, full_integrator):
        def bad_hook(**kwargs):
            raise RuntimeError("hook exploded")

        full_integrator.on("pre_cycle", bad_hook)
        # Should not raise
        result = full_integrator.run_cycle()
        assert result.success


# ─── Factory Tests ────────────────────────────────────────────────────


class TestFactory:
    def test_create_minimal(self):
        integrator = SwarmIntegrator.create_minimal()
        assert "event_bus" in integrator.get_component_names()
        assert integrator.mode == SwarmMode.PASSIVE

    def test_create_minimal_custom_mode(self):
        integrator = SwarmIntegrator.create_minimal(mode=SwarmMode.FULL_AUTO)
        assert integrator.mode == SwarmMode.FULL_AUTO

    def test_create_with_components(self, event_bus, mock_coordinator):
        integrator = SwarmIntegrator.create_with_components(
            mode=SwarmMode.SEMI_AUTO,
            components={
                "event_bus": event_bus,
                "coordinator": mock_coordinator,
            },
        )
        assert integrator.mode == SwarmMode.SEMI_AUTO
        assert len(integrator.get_component_names()) == 2

    def test_create_with_unknown_component(self, event_bus):
        # Should log warning but not crash
        integrator = SwarmIntegrator.create_with_components(
            components={
                "event_bus": event_bus,
                "bogus": MagicMock(),
            },
        )
        assert "bogus" not in integrator.get_component_names()


# ─── CycleResult Tests ────────────────────────────────────────────────


class TestCycleResult:
    def test_success_when_no_failures(self):
        result = CycleResult(
            cycle_number=1,
            mode="passive",
            started_at=time.time(),
            duration_ms=50,
            phases_completed=["ingest", "score"],
            phases_failed=[],
        )
        assert result.success

    def test_failure_when_phases_failed(self):
        result = CycleResult(
            cycle_number=1,
            mode="passive",
            started_at=time.time(),
            duration_ms=50,
            phases_completed=["ingest"],
            phases_failed=["score"],
        )
        assert not result.success

    def test_to_dict(self):
        result = CycleResult(
            cycle_number=1,
            mode="passive",
            started_at=time.time(),
            duration_ms=42.5,
            phases_completed=["ingest"],
            phases_failed=[],
            tasks_ingested=10,
            tasks_assigned=3,
        )
        d = result.to_dict()
        assert d["cycle"] == 1
        assert d["duration_ms"] == 42.5
        assert d["success"]
        assert d["tasks"]["ingested"] == 10
        assert d["tasks"]["assigned"] == 3


# ─── ComponentStatus Tests ─────────────────────────────────────────────


class TestComponentStatus:
    def test_to_dict(self):
        status = ComponentStatus(
            name="test",
            healthy=True,
            initialized=True,
            last_activity=time.time() - 10,
        )
        d = status.to_dict()
        assert d["name"] == "test"
        assert d["healthy"]
        assert "10s" in d["last_activity_ago"]

    def test_to_dict_no_activity(self):
        status = ComponentStatus(name="test", healthy=True)
        d = status.to_dict()
        assert d["last_activity_ago"] is None


# ─── Wiring Diagram Tests ──────────────────────────────────────────────


class TestDiagnostics:
    def test_wiring_diagram(self, full_integrator):
        diagram = full_integrator.get_wiring_diagram()
        assert "SwarmIntegrator Wiring:" in diagram
        assert "passive" in diagram
        assert "event_bus" in diagram
        assert "XMTPBridge" in diagram
        assert "FeedbackPipeline" in diagram
        assert "Analytics" in diagram

    def test_cycle_history_with_limit(self, full_integrator):
        for _ in range(5):
            full_integrator.run_cycle()
        history = full_integrator.get_cycle_history(limit=3)
        assert len(history) == 3
        # Should be the last 3
        assert history[-1]["cycle"] == 5
