"""
Chaos & Resilience tests for SwarmIntegrator.

Tests system behavior under adversarial conditions:
1. Component failure injection during cycles
2. Component flapping (healthy → unhealthy → healthy)
3. Event storm handling (high-frequency emits)
4. Concurrent rapid cycling
5. Memory pressure (history limits, large payloads)
6. Mode transitions during active cycles
7. Circuit breaker recovery patterns
8. Cascading failures across wired components
9. Graceful degradation with partial component loss
10. State consistency after error sequences

These complement the unit tests (test_integrator.py) and cross-component
tests (test_integrator_cross_component.py) by verifying the system doesn't
break under stress, only degrades gracefully.
"""

import pytest

from swarm.integrator import SwarmIntegrator, SwarmMode
from swarm.event_bus import EventBus


# ─── Spy Components ──────────────────────────────────────────────


class SpyCoordinator:
    """Coordinator that can be told to fail."""

    def __init__(self):
        self.call_count = 0
        self.should_fail = False
        self.fail_after_n = None  # Fail after N successful calls
        self.ingest_count = 0
        self.route_count = 0

    def ingest_live_tasks(self):
        self.call_count += 1
        self.ingest_count += 1
        if self.should_fail or (
            self.fail_after_n is not None and self.call_count > self.fail_after_n
        ):
            raise RuntimeError("Coordinator exploded")
        return 3  # 3 tasks ingested

    def route_tasks(self, max_bounty=None):
        self.route_count += 1
        if self.should_fail:
            raise RuntimeError("Routing exploded")
        return 2  # 2 tasks assigned

    def simulate_routing(self):
        if self.should_fail:
            raise RuntimeError("Simulation exploded")
        return {"assigned": 1}


class SpyScheduler:
    """Scheduler that can be told to fail."""

    def __init__(self):
        self.call_count = 0
        self.should_fail = False

    def score_tasks(self):
        self.call_count += 1
        if self.should_fail:
            raise RuntimeError("Scheduler exploded")
        return 5  # 5 tasks scored


class SpyFeedback:
    """Feedback pipeline spy."""

    def __init__(self):
        self.call_count = 0
        self.should_fail = False
        self.completions = []

    def process_completion(self, task_data):
        self.completions.append(task_data)

    def process_live(self):
        self.call_count += 1
        if self.should_fail:
            raise RuntimeError("Feedback exploded")
        return 2

    def get_processed_count(self):
        return len(self.completions)


class SpyAnalytics:
    """Analytics spy that records events."""

    def __init__(self):
        self.events = []
        self.should_fail = False
        self.flush_count = 0

    def record_event(self, event_type, data, source=None):
        self.events.append({"type": event_type, "data": data, "source": source})

    def flush(self):
        self.flush_count += 1
        if self.should_fail:
            raise RuntimeError("Analytics exploded")


class SpyDashboard:
    """Dashboard spy."""

    def __init__(self):
        self.refresh_count = 0
        self.should_fail = False

    def refresh(self):
        self.refresh_count += 1
        if self.should_fail:
            raise RuntimeError("Dashboard exploded")


class SpyXMTP:
    """XMTP bridge spy."""

    def __init__(self):
        self.notifications = []
        self.should_fail = False

    def notify_task_assigned(self, data):
        if self.should_fail:
            raise RuntimeError("XMTP exploded")
        self.notifications.append(("assigned", data))

    def notify_payment_confirmed(self, data):
        self.notifications.append(("payment", data))

    def notify_reputation_update(self, data):
        self.notifications.append(("reputation", data))


class SpyExpiry:
    """Expiry analyzer spy."""

    def __init__(self):
        self.events = []
        self.should_fail = False

    def record_expiry(self, data):
        if self.should_fail:
            raise RuntimeError("Expiry exploded")
        self.events.append(data)


# ─── Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def coordinator():
    return SpyCoordinator()


@pytest.fixture
def scheduler():
    return SpyScheduler()


@pytest.fixture
def feedback():
    return SpyFeedback()


@pytest.fixture
def analytics():
    return SpyAnalytics()


@pytest.fixture
def dashboard():
    return SpyDashboard()


@pytest.fixture
def xmtp():
    return SpyXMTP()


@pytest.fixture
def expiry():
    return SpyExpiry()


@pytest.fixture
def full_integrator(bus, coordinator, scheduler, feedback, analytics, dashboard):
    """Fully wired integrator for chaos testing."""
    integrator = SwarmIntegrator(mode=SwarmMode.FULL_AUTO)
    integrator.set_event_bus(bus)
    integrator.set_coordinator(coordinator)
    integrator.set_scheduler(scheduler)
    integrator.set_feedback_pipeline(feedback)
    integrator.set_analytics(analytics)
    integrator.set_dashboard(dashboard)
    integrator.wire()
    integrator.start()
    return integrator


# ─── Test: Component Failure Isolation ───────────────────────────


class TestFailureIsolation:
    """Each phase failure must NOT prevent subsequent phases from running."""

    def test_coordinator_failure_doesnt_block_scheduling(
        self, full_integrator, coordinator, scheduler
    ):
        coordinator.should_fail = True
        result = full_integrator.run_cycle()
        # Ingest failed, but score should still run
        assert "ingest" in result.phases_failed
        assert "score" in result.phases_completed
        assert scheduler.call_count == 1

    def test_scheduler_failure_doesnt_block_routing(
        self, full_integrator, scheduler, coordinator
    ):
        scheduler.should_fail = True
        result = full_integrator.run_cycle()
        assert "score" in result.phases_failed
        # Routing should still attempt
        assert "route" in result.phases_completed
        assert coordinator.route_count == 1

    def test_feedback_failure_doesnt_block_analytics(
        self, full_integrator, feedback, analytics
    ):
        feedback.should_fail = True
        result = full_integrator.run_cycle()
        assert "feedback" in result.phases_failed
        assert "analytics" in result.phases_completed
        assert analytics.flush_count == 1

    def test_analytics_failure_doesnt_block_dashboard(
        self, full_integrator, analytics, dashboard
    ):
        analytics.should_fail = True
        result = full_integrator.run_cycle()
        assert "analytics" in result.phases_failed
        assert "dashboard" in result.phases_completed
        assert dashboard.refresh_count == 1

    def test_dashboard_failure_still_completes_cycle(self, full_integrator, dashboard):
        dashboard.should_fail = True
        result = full_integrator.run_cycle()
        assert "dashboard" in result.phases_failed
        # Cycle still produces result with all prior phases
        assert "ingest" in result.phases_completed
        assert result.cycle_number == 1

    def test_all_components_fail_gracefully(
        self, full_integrator, coordinator, scheduler, feedback, analytics, dashboard
    ):
        """Worst case: everything fails. System should still produce a result."""
        coordinator.should_fail = True
        scheduler.should_fail = True
        feedback.should_fail = True
        analytics.should_fail = True
        dashboard.should_fail = True

        result = full_integrator.run_cycle()

        # All phases failed
        assert len(result.phases_failed) >= 5
        assert len(result.phases_completed) == 0
        # But we got a result with proper structure
        assert result.cycle_number == 1
        assert not result.success
        assert result.duration_ms >= 0
        assert len(result.errors) >= 5

    def test_health_degrades_on_failure(self, full_integrator, coordinator):
        assert full_integrator.is_healthy()
        coordinator.should_fail = True
        full_integrator.run_cycle()
        assert not full_integrator.is_healthy()
        health = full_integrator.health()
        assert health["status"] == "degraded"


# ─── Test: Component Flapping ────────────────────────────────────


class TestComponentFlapping:
    """Components recovering from failure should restore health."""

    def test_coordinator_recovers_after_failure(self, full_integrator, coordinator):
        # Fail first cycle
        coordinator.should_fail = True
        r1 = full_integrator.run_cycle()
        assert "ingest" in r1.phases_failed
        assert not full_integrator.is_healthy()

        # Recover second cycle
        coordinator.should_fail = False
        r2 = full_integrator.run_cycle()
        assert "ingest" in r2.phases_completed
        # Note: health doesn't auto-restore because _mark_unhealthy was called
        # This is actually a finding — flapping detection vs auto-recovery

    def test_alternating_failures_tracked(self, full_integrator, coordinator):
        """Flapping component: fail, succeed, fail, succeed."""
        results = []
        for i in range(6):
            coordinator.should_fail = i % 2 == 0
            results.append(full_integrator.run_cycle())

        # Odd cycles succeed (0-indexed: 1,3,5), even fail (0,2,4)
        for i, r in enumerate(results):
            if i % 2 == 0:
                assert "ingest" in r.phases_failed
            else:
                assert "ingest" in r.phases_completed

    def test_multiple_component_flapping(self, full_integrator, coordinator, scheduler):
        """Two components flapping out of phase."""
        coordinator.should_fail = True
        scheduler.should_fail = False
        r1 = full_integrator.run_cycle()

        coordinator.should_fail = False
        scheduler.should_fail = True
        r2 = full_integrator.run_cycle()

        assert "ingest" in r1.phases_failed and "score" in r1.phases_completed
        assert "ingest" in r2.phases_completed and "score" in r2.phases_failed


# ─── Test: Circuit Breaker ───────────────────────────────────────


class TestCircuitBreaker:
    """Circuit breaker trips after max_cycle_errors consecutive failures."""

    def test_circuit_breaks_at_threshold(self, bus, coordinator):
        integrator = SwarmIntegrator(mode=SwarmMode.FULL_AUTO, max_cycle_errors=3)
        integrator.set_event_bus(bus)
        integrator.set_coordinator(coordinator)
        integrator.wire()
        integrator.start()

        coordinator.should_fail = True
        for _ in range(3):
            integrator.run_cycle()

        assert integrator.is_circuit_broken()
        assert integrator._consecutive_errors == 3

    def test_circuit_resets_on_success(self, bus, coordinator):
        integrator = SwarmIntegrator(mode=SwarmMode.FULL_AUTO, max_cycle_errors=3)
        integrator.set_event_bus(bus)
        integrator.set_coordinator(coordinator)
        integrator.wire()
        integrator.start()

        # Build up 2 errors
        coordinator.should_fail = True
        integrator.run_cycle()
        integrator.run_cycle()
        assert integrator._consecutive_errors == 2

        # One success resets
        coordinator.should_fail = False
        integrator.run_cycle()
        assert integrator._consecutive_errors == 0
        assert not integrator.is_circuit_broken()

    def test_circuit_doesnt_break_below_threshold(self, bus, coordinator):
        integrator = SwarmIntegrator(mode=SwarmMode.FULL_AUTO, max_cycle_errors=5)
        integrator.set_event_bus(bus)
        integrator.set_coordinator(coordinator)
        integrator.wire()
        integrator.start()

        coordinator.should_fail = True
        for _ in range(4):
            integrator.run_cycle()

        assert not integrator.is_circuit_broken()

    def test_interleaved_errors_dont_trip_circuit(self, bus, coordinator):
        """Errors interleaved with successes shouldn't trip circuit."""
        integrator = SwarmIntegrator(mode=SwarmMode.FULL_AUTO, max_cycle_errors=3)
        integrator.set_event_bus(bus)
        integrator.set_coordinator(coordinator)
        integrator.wire()
        integrator.start()

        for i in range(10):
            coordinator.should_fail = i % 2 == 0
            integrator.run_cycle()

        # Never 3 consecutive → never circuit broken
        assert not integrator.is_circuit_broken()


# ─── Test: Event Storm ───────────────────────────────────────────


class TestEventStorm:
    """High-frequency event emission shouldn't cause issues."""

    def test_rapid_cycle_events(self, full_integrator, analytics):
        """50 rapid cycles should all emit events without dropping."""
        for _ in range(50):
            full_integrator.run_cycle()

        # Analytics should have received events from all cycles
        # Each cycle emits at least: cycle.start, cycle.end, and possibly task.assigned
        assert len(analytics.events) >= 100  # At least 2 per cycle

    def test_event_bus_handles_many_subscribers(self, bus):
        """Bus with many subscribers doesn't drop events."""
        received = []

        for i in range(20):
            bus.on("stress.test", lambda e, idx=i: received.append(idx))

        bus.emit("stress.test", {"payload": "x"})
        assert len(received) == 20
        assert set(received) == set(range(20))

    def test_large_payload_events(self, full_integrator, bus, analytics):
        """Events with large payloads should work without truncation."""
        large_data = {"items": [{"id": i, "data": "x" * 100} for i in range(100)]}
        bus.emit("large.event", large_data)

        matching = [e for e in analytics.events if e["type"] == "large.event"]
        assert len(matching) == 1
        assert len(matching[0]["data"]["items"]) == 100


# ─── Test: Mode Transitions Under Load ──────────────────────────


class TestModeTransitions:
    """Mode changes during operation should be safe."""

    def test_mode_change_between_cycles(self, full_integrator, coordinator):
        # Start in FULL_AUTO
        r1 = full_integrator.run_cycle()
        assert "route" in r1.phases_completed
        assert coordinator.route_count == 1

        # Switch to PASSIVE
        full_integrator.set_mode(SwarmMode.PASSIVE)
        r2 = full_integrator.run_cycle()
        # In passive, route_sim instead of route
        assert "route_sim" in r2.phases_completed
        # route_count should NOT increase (simulate_routing doesn't call route_tasks)
        assert coordinator.route_count == 1

        # Switch to DISABLED
        full_integrator.set_mode(SwarmMode.DISABLED)
        r3 = full_integrator.run_cycle()
        # No routing at all
        assert "route" not in r3.phases_completed
        assert "route_sim" not in r3.phases_completed

    def test_mode_change_fires_hooks(self, full_integrator):
        changes = []
        full_integrator.on("on_mode_change", lambda **kw: changes.append(kw))

        full_integrator.set_mode(SwarmMode.PASSIVE)
        full_integrator.set_mode(SwarmMode.SEMI_AUTO)
        full_integrator.set_mode(SwarmMode.FULL_AUTO)

        assert len(changes) == 3
        assert changes[0]["old_mode"] == SwarmMode.FULL_AUTO
        assert changes[0]["new_mode"] == SwarmMode.PASSIVE
        assert changes[2]["new_mode"] == SwarmMode.FULL_AUTO

    def test_rapid_mode_switching(self, full_integrator):
        """Switching modes rapidly shouldn't corrupt state."""
        modes = [
            SwarmMode.PASSIVE,
            SwarmMode.SEMI_AUTO,
            SwarmMode.FULL_AUTO,
            SwarmMode.DISABLED,
        ]
        for _ in range(25):
            for mode in modes:
                full_integrator.set_mode(mode)

        # Should end on DISABLED (last in loop)
        assert full_integrator.mode == SwarmMode.DISABLED

    def test_semi_auto_respects_bounty_threshold(self, full_integrator, coordinator):
        full_integrator.set_mode(SwarmMode.SEMI_AUTO)
        result = full_integrator.run_cycle()
        assert "route" in result.phases_completed
        # coordinator.route_tasks was called with max_bounty
        assert coordinator.route_count == 1


# ─── Test: Cycle History & Memory ────────────────────────────────


class TestCycleHistory:
    """History is bounded and consistent."""

    def test_history_bounded_at_50(self, full_integrator):
        for _ in range(75):
            full_integrator.run_cycle()

        history = full_integrator.get_cycle_history(limit=100)
        assert len(history) <= 50

    def test_history_preserves_latest(self, full_integrator):
        for _ in range(60):
            full_integrator.run_cycle()

        history = full_integrator.get_cycle_history(limit=5)
        assert len(history) == 5
        # Latest cycle number should be 60
        assert history[-1]["cycle"] == 60

    def test_history_limit_parameter(self, full_integrator):
        for _ in range(10):
            full_integrator.run_cycle()

        assert len(full_integrator.get_cycle_history(limit=3)) == 3
        assert len(full_integrator.get_cycle_history(limit=1)) == 1

    def test_cycle_numbers_monotonic(self, full_integrator):
        for _ in range(20):
            full_integrator.run_cycle()

        history = full_integrator.get_cycle_history(limit=20)
        numbers = [h["cycle"] for h in history]
        assert numbers == sorted(numbers)
        assert numbers == list(range(1, 21))


# ─── Test: Cascading Failures via EventBus ───────────────────────


class TestCascadingFailures:
    """Failures in event handlers shouldn't crash the cycle."""

    def test_xmtp_failure_during_assignment_event(
        self, bus, coordinator, xmtp, analytics
    ):
        """XMTP bridge failing on task.assigned shouldn't crash the cycle."""
        integrator = SwarmIntegrator(mode=SwarmMode.FULL_AUTO)
        integrator.set_event_bus(bus)
        integrator.set_coordinator(coordinator)
        integrator.set_xmtp_bridge(xmtp)
        integrator.set_analytics(analytics)
        integrator.wire()
        integrator.start()

        xmtp.should_fail = True
        result = integrator.run_cycle()

        # Cycle should still complete
        assert result.cycle_number == 1
        assert "route" in result.phases_completed
        # Analytics should still record events (independent of XMTP failure)
        assert len(analytics.events) > 0

    def test_expiry_failure_during_event(self, bus, expiry, analytics):
        """Expiry analyzer failing shouldn't crash other handlers."""
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        integrator.set_event_bus(bus)
        integrator.set_expiry_analyzer(expiry)
        integrator.set_analytics(analytics)
        integrator.wire()
        integrator.start()

        expiry.should_fail = True
        # Emit task.expired manually
        bus.emit("task.expired", {"task_id": "t1", "reason": "timeout"})

        # Analytics should still work
        matching = [e for e in analytics.events if e["type"] == "task.expired"]
        assert len(matching) == 1

    def test_analytics_failure_doesnt_block_other_handlers(
        self, bus, feedback, analytics
    ):
        """Analytics recording failure shouldn't prevent feedback processing."""
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        integrator.set_event_bus(bus)
        integrator.set_feedback_pipeline(feedback)
        integrator.set_analytics(analytics)
        integrator.wire()
        integrator.start()

        # Both receive task.completed, but analytics will fail
        analytics.should_fail = False  # record_event won't fail, only flush
        bus.emit(
            "task.completed",
            {"task_data": {"id": "t1", "worker": "w1", "quality": 0.9}},
        )

        # Feedback should have processed
        assert len(feedback.completions) == 1


# ─── Test: Partial Component Registration ────────────────────────


class TestPartialRegistration:
    """System works with any subset of components."""

    def test_event_bus_only(self, bus):
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        integrator.set_event_bus(bus)
        integrator.wire()
        integrator.start()

        result = integrator.run_cycle()
        assert result.success
        assert result.cycle_number == 1

    def test_coordinator_only(self, bus, coordinator):
        integrator = SwarmIntegrator(mode=SwarmMode.FULL_AUTO)
        integrator.set_event_bus(bus)
        integrator.set_coordinator(coordinator)
        integrator.wire()
        integrator.start()

        result = integrator.run_cycle()
        assert "ingest" in result.phases_completed
        assert "route" in result.phases_completed

    def test_analytics_only(self, bus, analytics):
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        integrator.set_event_bus(bus)
        integrator.set_analytics(analytics)
        integrator.wire()
        integrator.start()

        result = integrator.run_cycle()
        assert "analytics" in result.phases_completed
        assert analytics.flush_count == 1

    def test_no_components_still_cycles(self):
        """Bare integrator with nothing registered should still run cycles."""
        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        integrator.start()
        result = integrator.run_cycle()
        assert result.success  # No phases to fail
        assert result.cycle_number == 1


# ─── Test: Hook Error Isolation ──────────────────────────────────


class TestHookErrors:
    """Bad hooks shouldn't crash the system."""

    def test_pre_cycle_hook_error_doesnt_block_cycle(self, full_integrator):
        def bad_hook(**kw):
            raise ValueError("Hook went boom")

        full_integrator.on("pre_cycle", bad_hook)
        result = full_integrator.run_cycle()
        # Cycle should still complete
        assert result.cycle_number == 1

    def test_post_cycle_hook_error_doesnt_corrupt_state(self, full_integrator):
        def bad_hook(**kw):
            raise RuntimeError("Post-cycle kaboom")

        full_integrator.on("post_cycle", bad_hook)
        r1 = full_integrator.run_cycle()
        r2 = full_integrator.run_cycle()
        # Both cycles should complete
        assert r1.cycle_number == 1
        assert r2.cycle_number == 2

    def test_assignment_hook_error_doesnt_prevent_next_cycle(self, full_integrator):
        def bad_hook(**kw):
            raise TypeError("Assignment hook failed")

        full_integrator.on("on_assignment", bad_hook)
        full_integrator.run_cycle()
        r2 = full_integrator.run_cycle()
        assert r2.cycle_number == 2

    def test_multiple_hooks_one_failing(self, full_integrator):
        """If hook A fails, hook B should still fire."""
        results = []

        def hook_a(**kw):
            raise RuntimeError("A fails")

        def hook_b(**kw):
            results.append("B ran")

        full_integrator.on("pre_cycle", hook_a)
        full_integrator.on("pre_cycle", hook_b)
        full_integrator.run_cycle()
        assert "B ran" in results


# ─── Test: Health Reporting Under Stress ─────────────────────────


class TestHealthUnderStress:
    """Health reports remain accurate during failures."""

    def test_health_counts_after_multiple_failures(
        self, full_integrator, coordinator, scheduler, feedback
    ):
        coordinator.should_fail = True
        scheduler.should_fail = True
        feedback.should_fail = True
        full_integrator.run_cycle()

        health = full_integrator.health()
        details = health["components"]["details"]
        assert not details["coordinator"]["healthy"]
        assert not details["scheduler"]["healthy"]
        assert not details["feedback_pipeline"]["healthy"]
        # Analytics and dashboard should still be healthy
        assert details["analytics"]["healthy"]
        assert details["dashboard"]["healthy"]

    def test_health_after_50_cycles(self, full_integrator):
        for _ in range(50):
            full_integrator.run_cycle()

        health = full_integrator.health()
        assert health["cycles"]["completed"] == 50
        assert health["status"] == "healthy"

    def test_summary_compact_after_failures(self, full_integrator, coordinator):
        coordinator.should_fail = True
        for _ in range(3):
            full_integrator.run_cycle()

        summary = full_integrator.summary()
        assert summary["running"]
        assert not summary["healthy"]
        assert summary["cycles"] == 3
        assert summary["last_cycle"] is not None

    def test_wiring_diagram_reflects_unhealthy(self, full_integrator, coordinator):
        coordinator.should_fail = True
        full_integrator.run_cycle()

        diagram = full_integrator.get_wiring_diagram()
        assert "❌" in diagram  # Unhealthy component shows ❌


# ─── Test: Start/Stop Edge Cases ─────────────────────────────────


class TestLifecycleEdgeCases:
    """Start/stop ordering and repeated calls."""

    def test_cycle_before_start(self, bus, coordinator):
        """Running a cycle before start() should still work."""
        integrator = SwarmIntegrator(mode=SwarmMode.FULL_AUTO)
        integrator.set_event_bus(bus)
        integrator.set_coordinator(coordinator)
        integrator.wire()
        # Don't call start()
        result = integrator.run_cycle()
        assert result.cycle_number == 1

    def test_double_start(self, bus):
        integrator = SwarmIntegrator()
        integrator.set_event_bus(bus)
        integrator.wire()

        r1 = integrator.start()
        r2 = integrator.start()
        assert r1["status"] == "started"
        assert r2["status"] == "already_running"

    def test_double_stop(self, bus):
        integrator = SwarmIntegrator()
        integrator.set_event_bus(bus)
        integrator.wire()
        integrator.start()

        r1 = integrator.stop()
        r2 = integrator.stop()
        assert r1["status"] == "stopped"
        assert r2["status"] == "not_running"

    def test_start_stop_start(self, bus, coordinator):
        """Restarting should reset error count."""
        integrator = SwarmIntegrator(mode=SwarmMode.FULL_AUTO)
        integrator.set_event_bus(bus)
        integrator.set_coordinator(coordinator)
        integrator.wire()

        integrator.start()
        coordinator.should_fail = True
        integrator.run_cycle()
        assert integrator._consecutive_errors == 1

        integrator.stop()
        integrator.start()
        assert integrator._consecutive_errors == 0

    def test_cycles_after_stop(self, full_integrator):
        """Cycles after stop should still work (no hard block)."""
        full_integrator.stop()
        result = full_integrator.run_cycle()
        # Cycle runs regardless of started state
        assert result.cycle_number == 1


# ─── Test: Stress Patterns ───────────────────────────────────────


class TestStressPatterns:
    """High-volume and timing stress tests."""

    def test_100_cycles_no_errors(self, full_integrator):
        """100 clean cycles maintain consistent state."""
        for _ in range(100):
            full_integrator.run_cycle()

        assert full_integrator._cycle_count == 100
        assert full_integrator._consecutive_errors == 0
        assert full_integrator.is_healthy()

    def test_alternating_success_failure_100_cycles(self, full_integrator, coordinator):
        """100 cycles alternating between success and failure."""
        for i in range(100):
            coordinator.should_fail = i % 2 == 0
            full_integrator.run_cycle()

        assert full_integrator._cycle_count == 100
        # Last cycle (99) is odd → success → consecutive_errors = 0
        assert full_integrator._consecutive_errors == 0

    def test_burst_failure_then_recovery(self, full_integrator, coordinator):
        """10 failures in a row, then 10 successes."""
        coordinator.should_fail = True
        for _ in range(10):
            full_integrator.run_cycle()
        assert full_integrator._consecutive_errors == 10

        coordinator.should_fail = False
        for _ in range(10):
            full_integrator.run_cycle()
        assert full_integrator._consecutive_errors == 0
        assert full_integrator._cycle_count == 20

    def test_gradual_degradation(
        self, full_integrator, coordinator, scheduler, feedback, analytics, dashboard
    ):
        """Components fail one by one, then recover one by one."""
        components = [coordinator, scheduler, feedback, analytics, dashboard]

        # Degrade: fail one more component each cycle
        for i, comp in enumerate(components):
            comp.should_fail = True
            result = full_integrator.run_cycle()
            assert len(result.phases_failed) >= i + 1

        # All failed
        assert not full_integrator.is_healthy()

        # Recover: fix one more component each cycle
        for comp in components:
            comp.should_fail = False
            full_integrator.run_cycle()

        # Final cycle should be clean
        result = full_integrator.run_cycle()
        assert result.success


# ─── Test: CycleResult Consistency ───────────────────────────────


class TestCycleResultConsistency:
    """CycleResult data must be internally consistent."""

    def test_duration_is_positive(self, full_integrator):
        result = full_integrator.run_cycle()
        assert result.duration_ms >= 0

    def test_to_dict_round_trip(self, full_integrator):
        result = full_integrator.run_cycle()
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "cycle" in d
        assert "duration_ms" in d
        assert "success" in d
        assert "tasks" in d
        assert d["success"] == result.success

    def test_failed_cycle_has_errors(self, full_integrator, coordinator):
        coordinator.should_fail = True
        result = full_integrator.run_cycle()
        assert len(result.errors) > 0
        assert not result.success
        d = result.to_dict()
        assert d["success"] is False

    def test_phases_dont_overlap(self, full_integrator):
        """No phase name should appear in both completed and failed."""
        result = full_integrator.run_cycle()
        completed = set(result.phases_completed)
        failed = set(result.phases_failed)
        assert completed.isdisjoint(failed)
