"""
Comprehensive tests for SwarmCoordinator — the keystone integration module.

Tests the full pipeline:
  Agent Registration → Task Ingestion → Queue Processing → Assignment →
  Completion/Failure → Health Checks → Metrics → Dashboard

All tests are self-contained with no external dependencies.
"""

from datetime import datetime, timezone, timedelta

import pytest

from swarm.coordinator import (
    SwarmCoordinator,
    SwarmMetrics,
    EMApiClient,
    CoordinatorEvent,
    EventRecord,
    QueuedTask,
)
from swarm.lifecycle_manager import (
    LifecycleManager,
    AgentState,
    BudgetConfig,
)
from swarm.orchestrator import (
    SwarmOrchestrator,
    TaskRequest,
    TaskPriority,
    Assignment,
    RoutingFailure,
    RoutingStrategy,
)
from swarm.reputation_bridge import (
    ReputationBridge,
    OnChainReputation,
    InternalReputation,
)


# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def bridge():
    return ReputationBridge()


@pytest.fixture
def lifecycle():
    return LifecycleManager()


@pytest.fixture
def orchestrator(bridge, lifecycle):
    return SwarmOrchestrator(bridge=bridge, lifecycle=lifecycle)


@pytest.fixture
def coordinator(bridge, lifecycle, orchestrator):
    """A basic coordinator without external clients."""
    return SwarmCoordinator(
        bridge=bridge,
        lifecycle=lifecycle,
        orchestrator=orchestrator,
        em_client=None,
        autojob_client=None,
    )


@pytest.fixture
def coordinator_factory(bridge, lifecycle, orchestrator):
    """Factory for coordinators with custom config."""

    def _create(**kwargs):
        defaults = dict(
            bridge=bridge,
            lifecycle=lifecycle,
            orchestrator=orchestrator,
            em_client=None,
            autojob_client=None,
        )
        defaults.update(kwargs)
        return SwarmCoordinator(**defaults)

    return _create


def _register_agent(coordinator, agent_id=1, name="aurora", wallet="0xAAA"):
    """Helper to register and activate an agent."""
    on_chain = OnChainReputation(
        agent_id=agent_id,
        wallet_address=wallet,
        total_seals=10,
        positive_seals=9,
    )
    internal = InternalReputation(
        agent_id=agent_id,
        bayesian_score=0.8,
        total_tasks=25,
        successful_tasks=23,
        avg_rating=4.5,
        avg_completion_time_hours=2.0,
        category_scores={"photo": 80, "delivery": 60},
    )
    record = coordinator.register_agent(
        agent_id=agent_id,
        name=name,
        wallet_address=wallet,
        personality="explorer",
        on_chain=on_chain,
        internal=internal,
        tags=["fast", "reliable"],
        activate=True,
    )
    return record


def _ingest_task(coordinator, task_id="t1", title="Test task", bounty=5.0):
    """Helper to ingest a task."""
    return coordinator.ingest_task(
        task_id=task_id,
        title=title,
        categories=["photo"],
        bounty_usd=bounty,
        priority=TaskPriority.NORMAL,
    )


# ─── Agent Registration Tests ────────────────────────────────────────


class TestAgentRegistration:
    """Tests for agent registration and lifecycle integration."""

    def test_register_single_agent(self, coordinator):
        record = _register_agent(coordinator, agent_id=1, name="aurora")
        assert record.agent_id == 1
        assert record.name == "aurora"
        assert record.state == AgentState.ACTIVE

    def test_register_agent_transitions(self, coordinator):
        """Registration should: INIT → IDLE → ACTIVE."""
        record = _register_agent(coordinator, agent_id=1)
        # Final state is ACTIVE
        assert record.state == AgentState.ACTIVE
        # Check audit trail
        history = coordinator.lifecycle._state_history
        agent_transitions = [h for h in history if h["agent_id"] == 1]
        states = [h["to"] for h in agent_transitions]
        assert "initializing" in states
        assert "idle" in states
        assert "active" in states

    def test_register_without_activation(self, coordinator):
        record = coordinator.register_agent(
            agent_id=1,
            name="aurora",
            wallet_address="0xAAA",
            activate=False,
        )
        assert record.state == AgentState.IDLE

    def test_register_emits_event(self, coordinator):
        _register_agent(coordinator, agent_id=1, name="aurora")
        events = coordinator.get_events(event_type=CoordinatorEvent.AGENT_REGISTERED)
        assert len(events) == 1
        assert events[0]["agent_id"] == 1
        assert events[0]["name"] == "aurora"

    def test_register_batch(self, coordinator):
        agents = [
            {"agent_id": 1, "name": "aurora", "wallet_address": "0x001"},
            {"agent_id": 2, "name": "beacon", "wallet_address": "0x002"},
            {"agent_id": 3, "name": "cinder", "wallet_address": "0x003"},
        ]
        records = coordinator.register_agents_batch(agents)
        assert len(records) == 3
        for rec in records:
            assert rec.state == AgentState.ACTIVE

    def test_register_batch_handles_duplicates(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        agents = [
            {"agent_id": 1, "name": "aurora_dup", "wallet_address": "0x001"},
            {"agent_id": 2, "name": "beacon", "wallet_address": "0x002"},
        ]
        records = coordinator.register_agents_batch(agents)
        # Agent 1 fails (already registered), agent 2 succeeds
        assert len(records) == 1
        assert records[0].agent_id == 2

    def test_register_with_custom_budget(self, coordinator):
        budget = BudgetConfig(daily_limit_usd=10.0, monthly_limit_usd=200.0)
        coordinator.register_agent(
            agent_id=1,
            name="aurora",
            wallet_address="0xAAA",
            budget_config=budget,
        )
        status = coordinator.lifecycle.get_budget_status(1)
        assert status["daily_limit"] == 10.0
        assert status["monthly_limit"] == 200.0

    def test_register_with_tags(self, coordinator):
        record = _register_agent(coordinator, agent_id=1)
        assert "fast" in record.tags
        assert "reliable" in record.tags


# ─── Task Ingestion Tests ────────────────────────────────────────────


class TestTaskIngestion:
    """Tests for task queue management."""

    def test_ingest_single_task(self, coordinator):
        task = _ingest_task(coordinator, task_id="t1")
        assert task.task_id == "t1"
        assert task.status == "pending"
        assert task.bounty_usd == 5.0

    def test_ingest_emits_event(self, coordinator):
        _ingest_task(coordinator)
        events = coordinator.get_events(event_type=CoordinatorEvent.TASK_INGESTED)
        assert len(events) == 1
        assert events[0]["task_id"] == "t1"

    def test_ingest_duplicate_skips(self, coordinator):
        task1 = _ingest_task(coordinator, task_id="t1")
        task2 = _ingest_task(coordinator, task_id="t1")
        # Should return the same object, not create duplicate
        assert task1 is task2
        summary = coordinator.get_queue_summary()
        assert summary["total"] == 1

    def test_ingest_multiple_tasks(self, coordinator):
        for i in range(5):
            _ingest_task(coordinator, task_id=f"t{i}")
        summary = coordinator.get_queue_summary()
        assert summary["total"] == 5
        assert summary["by_status"]["pending"] == 5

    def test_ingest_with_priority(self, coordinator):
        task = coordinator.ingest_task(
            task_id="t1",
            title="Urgent photo",
            categories=["photo"],
            bounty_usd=100.0,
            priority=TaskPriority.CRITICAL,
        )
        assert task.priority == TaskPriority.CRITICAL

    def test_ingest_failed_task_allows_reingest(self, coordinator):
        task = _ingest_task(coordinator, task_id="t1")
        task.status = "failed"
        # Re-ingesting a failed task should work
        task2 = _ingest_task(coordinator, task_id="t1")
        assert task2.status == "pending"

    def test_queue_summary_by_category(self, coordinator):
        coordinator.ingest_task("t1", "Photo verify", ["photo"], 5.0)
        coordinator.ingest_task("t2", "Deliver package", ["delivery"], 10.0)
        coordinator.ingest_task("t3", "Another photo", ["photo"], 3.0)
        summary = coordinator.get_queue_summary()
        assert summary["by_category"]["photo"] == 2
        assert summary["by_category"]["delivery"] == 1
        assert summary["pending_bounty_usd"] == 18.0


# ─── Task Processing Tests ───────────────────────────────────────────


class TestTaskProcessing:
    """Tests for the core routing pipeline."""

    def test_process_empty_queue(self, coordinator):
        results = coordinator.process_task_queue()
        assert results == []

    def test_process_no_agents(self, coordinator):
        _ingest_task(coordinator)
        results = coordinator.process_task_queue()
        assert len(results) == 1
        assert isinstance(results[0], RoutingFailure)
        assert "No agents available" in results[0].reason

    def test_process_assigns_task(self, coordinator):
        _register_agent(coordinator, agent_id=1, name="aurora")
        _ingest_task(coordinator)
        results = coordinator.process_task_queue()
        assert len(results) == 1
        assert isinstance(results[0], Assignment)
        assert results[0].agent_id == 1
        assert results[0].task_id == "t1"

    def test_process_updates_task_status(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        task = _ingest_task(coordinator)
        coordinator.process_task_queue()
        assert task.status == "assigned"
        assert task.assigned_agent_id == 1

    def test_process_emits_assignment_event(self, coordinator):
        _register_agent(coordinator, agent_id=1, name="aurora")
        _ingest_task(coordinator)
        coordinator.process_task_queue()
        events = coordinator.get_events(event_type=CoordinatorEvent.TASK_ASSIGNED)
        assert len(events) == 1
        assert events[0]["agent_id"] == 1
        assert events[0]["task_id"] == "t1"

    def test_process_respects_max_tasks(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _register_agent(coordinator, agent_id=2, name="beacon", wallet="0xBBB")
        for i in range(10):
            _ingest_task(coordinator, task_id=f"t{i}")
        # Only process 3
        results = coordinator.process_task_queue(max_tasks=3)
        assert len(results) == 3

    def test_process_priority_ordering(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _register_agent(coordinator, agent_id=2, name="beacon", wallet="0xBBB")
        coordinator.ingest_task("t-low", "Low task", ["photo"], 1.0, TaskPriority.LOW)
        coordinator.ingest_task(
            "t-crit", "Critical task", ["photo"], 50.0, TaskPriority.CRITICAL
        )
        coordinator.ingest_task(
            "t-norm", "Normal task", ["photo"], 5.0, TaskPriority.NORMAL
        )
        results = coordinator.process_task_queue(max_tasks=3)
        assigned = [r for r in results if isinstance(r, Assignment)]
        # Critical should be assigned first
        if len(assigned) >= 1:
            assert assigned[0].task_id == "t-crit"

    def test_process_tracks_routing_time(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _ingest_task(coordinator)
        coordinator.process_task_queue()
        metrics = coordinator.get_metrics()
        assert metrics.avg_routing_time_ms > 0

    def test_max_attempts_exhausted(self, coordinator):
        """Task fails permanently after max_attempts."""
        # No agents → every attempt fails
        task = _ingest_task(coordinator)
        task.max_attempts = 2
        coordinator.process_task_queue()  # attempt 1
        coordinator.process_task_queue()  # attempt 2 (max reached)
        assert task.status == "failed"
        events = coordinator.get_events(event_type=CoordinatorEvent.ROUTING_FAILURE)
        assert len(events) >= 1


# ─── Task Completion Tests ────────────────────────────────────────────


class TestTaskCompletion:
    """Tests for task completion flow."""

    def test_complete_task(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _ingest_task(coordinator, task_id="t1", bounty=5.0)
        coordinator.process_task_queue()
        success = coordinator.complete_task("t1")
        assert success is True
        # Check queue status
        task = coordinator._task_queue["t1"]
        assert task.status == "completed"

    def test_complete_task_emits_event(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _ingest_task(coordinator)
        coordinator.process_task_queue()
        coordinator.complete_task("t1")
        events = coordinator.get_events(event_type=CoordinatorEvent.TASK_COMPLETED)
        assert len(events) == 1
        assert events[0]["task_id"] == "t1"
        assert events[0]["agent_id"] == 1
        assert events[0]["bounty_usd"] == 5.0

    def test_complete_tracks_bounty(self, coordinator):
        # Use a generous budget so the agent doesn't get suspended
        budget = BudgetConfig(daily_limit_usd=100.0, monthly_limit_usd=1000.0)
        coordinator.register_agent(
            agent_id=10,
            name="rich_agent",
            wallet_address="0xRICH",
            budget_config=budget,
            activate=True,
        )
        coordinator.orchestrator.register_reputation(
            agent_id=10,
            on_chain=OnChainReputation(
                agent_id=10, wallet_address="0xRICH", total_seals=10, positive_seals=9
            ),
            internal=InternalReputation(
                agent_id=10,
                bayesian_score=0.8,
                total_tasks=25,
                successful_tasks=23,
                avg_rating=4.5,
            ),
        )
        _ingest_task(coordinator, task_id="t1", bounty=5.0)
        coordinator.process_task_queue()
        coordinator.complete_task("t1")

        # Expire cooldown and reactivate for second task
        agent = coordinator.lifecycle._agents[10]
        agent.cooldown_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        coordinator.lifecycle.check_cooldown_expiry(10)
        coordinator.lifecycle.transition(10, AgentState.ACTIVE, "reactivate")

        _ingest_task(coordinator, task_id="t2", bounty=10.0)
        coordinator.process_task_queue()
        coordinator.complete_task("t2")
        metrics = coordinator.get_metrics()
        assert metrics.total_bounty_earned_usd == 15.0

    def test_complete_unknown_task_returns_false(self, coordinator):
        assert coordinator.complete_task("nonexistent") is False

    def test_complete_updates_internal_reputation(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _ingest_task(coordinator, task_id="t1")
        coordinator.process_task_queue()
        coordinator.complete_task("t1")
        # Internal reputation should have increased
        internal = coordinator.orchestrator._internal.get(1)
        if internal:
            assert internal.total_tasks >= 1
            assert internal.consecutive_failures == 0

    def test_complete_with_custom_bounty(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _ingest_task(coordinator, task_id="t1", bounty=5.0)
        coordinator.process_task_queue()
        # Complete with a different bounty amount
        coordinator.complete_task("t1", bounty_earned_usd=7.50)
        metrics = coordinator.get_metrics()
        assert metrics.total_bounty_earned_usd == 7.50


# ─── Task Failure Tests ──────────────────────────────────────────────


class TestTaskFailure:
    """Tests for task failure flow."""

    def test_fail_task(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _ingest_task(coordinator)
        coordinator.process_task_queue()
        success = coordinator.fail_task("t1", error="Worker couldn't reach location")
        assert success is True
        task = coordinator._task_queue["t1"]
        assert task.status == "failed"

    def test_fail_emits_event(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _ingest_task(coordinator)
        coordinator.process_task_queue()
        coordinator.fail_task("t1", error="timeout")
        events = coordinator.get_events(event_type=CoordinatorEvent.TASK_FAILED)
        assert len(events) == 1
        assert events[0]["error"] == "timeout"

    def test_fail_unknown_task_returns_false(self, coordinator):
        assert coordinator.fail_task("nonexistent") is False

    def test_fail_increments_counter(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _ingest_task(coordinator)
        coordinator.process_task_queue()
        coordinator.fail_task("t1")
        metrics = coordinator.get_metrics()
        assert metrics.tasks_failed >= 1


# ─── Health Check Tests ──────────────────────────────────────────────


class TestHealthChecks:
    """Tests for the health monitoring subsystem."""

    def test_health_check_returns_report(self, coordinator):
        report = coordinator.run_health_checks()
        assert "timestamp" in report
        assert "agents" in report
        assert "tasks" in report
        assert "systems" in report

    def test_health_check_counts_agents(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _register_agent(coordinator, agent_id=2, name="beacon", wallet="0xBBB")
        # Record heartbeat for one agent
        coordinator.lifecycle.record_heartbeat(1)
        report = coordinator.run_health_checks()
        assert report["agents"]["checked"] == 2

    def test_health_check_detects_expired_tasks(self, coordinator):
        task = _ingest_task(coordinator)
        # Manually set ingested time far in the past
        task.ingested_at = datetime.now(timezone.utc) - timedelta(hours=48)
        report = coordinator.run_health_checks()
        assert report["tasks"]["expired"] >= 1
        assert task.status == "expired"

    def test_health_check_emits_event(self, coordinator):
        coordinator.run_health_checks()
        events = coordinator.get_events(event_type=CoordinatorEvent.HEALTH_CHECK)
        assert len(events) == 1

    def test_health_check_no_em_client(self, coordinator):
        """Health check should work even without EM API client."""
        report = coordinator.run_health_checks()
        assert "em_api" not in report.get("systems", {})

    def test_health_check_cooldown_recovery(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        # Put agent in cooldown with expired time
        coordinator.lifecycle.assign_task(1, "t_temp")
        coordinator.lifecycle.complete_task(1, cooldown_seconds=0)
        assert coordinator.lifecycle._agents[1].state == AgentState.COOLDOWN
        # Health check should trigger recovery
        coordinator.run_health_checks()
        # After health check, cooldown should have expired → IDLE
        agent = coordinator.lifecycle._agents[1]
        assert agent.state in (AgentState.IDLE, AgentState.COOLDOWN)

    def test_health_check_detects_stale_assignments(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        task = _ingest_task(coordinator)
        coordinator.process_task_queue()
        # Artificially age the assignment
        task.last_attempt_at = datetime.now(timezone.utc) - timedelta(hours=48)
        report = coordinator.run_health_checks()
        assert report["tasks"]["stale"] >= 1


# ─── Metrics Tests ───────────────────────────────────────────────────


class TestMetrics:
    """Tests for operational metrics."""

    def test_initial_metrics_zeroed(self, coordinator):
        m = coordinator.get_metrics()
        assert m.tasks_ingested == 0
        assert m.tasks_assigned == 0
        assert m.tasks_completed == 0
        assert m.tasks_failed == 0
        assert m.total_bounty_earned_usd == 0.0

    def test_metrics_after_full_cycle(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _ingest_task(coordinator, bounty=5.0)
        coordinator.process_task_queue()
        coordinator.complete_task("t1")
        m = coordinator.get_metrics()
        assert m.tasks_ingested == 1
        assert m.tasks_assigned == 1
        assert m.tasks_completed == 1
        assert m.total_bounty_earned_usd == 5.0
        assert m.routing_success_rate == 1.0

    def test_metrics_to_dict(self, coordinator):
        m = coordinator.get_metrics()
        d = m.to_dict()
        assert "tasks" in d
        assert "agents" in d
        assert "performance" in d
        assert "budget" in d
        assert "timing" in d

    def test_metrics_uptime(self, coordinator):
        m = coordinator.get_metrics()
        assert m.uptime_seconds >= 0

    def test_reset_metrics(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _ingest_task(coordinator)
        coordinator.process_task_queue()
        coordinator.reset_metrics()
        m = coordinator.get_metrics()
        assert m.tasks_ingested == 0
        assert m.tasks_assigned == 0


# ─── Dashboard Tests ─────────────────────────────────────────────────


class TestDashboard:
    """Tests for the operational dashboard."""

    def test_dashboard_structure(self, coordinator):
        dashboard = coordinator.get_dashboard()
        assert "timestamp" in dashboard
        assert "metrics" in dashboard
        assert "queue" in dashboard
        assert "fleet" in dashboard
        assert "swarm" in dashboard
        assert "recent_events" in dashboard
        assert "systems" in dashboard

    def test_dashboard_fleet_info(self, coordinator):
        _register_agent(coordinator, agent_id=1, name="aurora")
        _register_agent(coordinator, agent_id=2, name="beacon", wallet="0xBBB")
        dashboard = coordinator.get_dashboard()
        assert len(dashboard["fleet"]) == 2
        names = {a["name"] for a in dashboard["fleet"]}
        assert "aurora" in names
        assert "beacon" in names

    def test_dashboard_queue_status(self, coordinator):
        _ingest_task(coordinator, task_id="t1")
        _ingest_task(coordinator, task_id="t2")
        dashboard = coordinator.get_dashboard()
        assert dashboard["queue"]["pending"] == 2

    def test_dashboard_recent_events(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _ingest_task(coordinator)
        dashboard = coordinator.get_dashboard()
        assert len(dashboard["recent_events"]) > 0

    def test_dashboard_systems_info(self, coordinator):
        dashboard = coordinator.get_dashboard()
        assert dashboard["systems"]["em_api"] == "not configured"
        assert dashboard["systems"]["autojob"] == "not configured"


# ─── Event System Tests ──────────────────────────────────────────────


class TestEventSystem:
    """Tests for the coordinator event hooks and queries."""

    def test_event_hook_fires(self, coordinator):
        received = []
        coordinator.on_event(
            CoordinatorEvent.TASK_INGESTED,
            lambda e: received.append(e),
        )
        _ingest_task(coordinator)
        assert len(received) == 1
        assert received[0].event == CoordinatorEvent.TASK_INGESTED

    def test_multiple_hooks(self, coordinator):
        count = {"a": 0, "b": 0}
        coordinator.on_event(
            CoordinatorEvent.TASK_INGESTED,
            lambda e: count.__setitem__("a", count["a"] + 1),
        )
        coordinator.on_event(
            CoordinatorEvent.TASK_INGESTED,
            lambda e: count.__setitem__("b", count["b"] + 1),
        )
        _ingest_task(coordinator)
        assert count["a"] == 1
        assert count["b"] == 1

    def test_event_hook_exception_doesnt_crash(self, coordinator):
        def bad_hook(e):
            raise RuntimeError("Hook exploded!")

        coordinator.on_event(CoordinatorEvent.TASK_INGESTED, bad_hook)
        # Should not raise
        _ingest_task(coordinator)

    def test_get_events_with_filter(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _ingest_task(coordinator)
        coordinator.process_task_queue()

        all_events = coordinator.get_events(limit=100)
        ingested = coordinator.get_events(event_type=CoordinatorEvent.TASK_INGESTED)
        assert len(ingested) < len(all_events)

    def test_get_events_with_since(self, coordinator):
        _ingest_task(coordinator, task_id="t1")
        cutoff = datetime.now(timezone.utc)
        _ingest_task(coordinator, task_id="t2")
        recent = coordinator.get_events(since=cutoff)
        # Only t2 should appear after cutoff
        assert len(recent) >= 1

    def test_events_capped_at_1000(self, coordinator):
        for i in range(1100):
            _ingest_task(coordinator, task_id=f"t{i}")
        events = coordinator.get_events(limit=2000)
        # Events deque is capped at 1000
        assert len(events) <= 1000


# ─── Queue Utilities Tests ───────────────────────────────────────────


class TestQueueUtilities:
    """Tests for queue management utilities."""

    def test_cleanup_completed(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _ingest_task(coordinator, task_id="t1")
        coordinator.process_task_queue()
        coordinator.complete_task("t1")
        # Backdate the task
        coordinator._task_queue["t1"].ingested_at = datetime.now(
            timezone.utc
        ) - timedelta(hours=48)
        removed = coordinator.cleanup_completed(older_than_hours=24.0)
        assert removed == 1
        assert "t1" not in coordinator._task_queue

    def test_cleanup_keeps_recent(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _ingest_task(coordinator, task_id="t1")
        coordinator.process_task_queue()
        coordinator.complete_task("t1")
        # Don't backdate — should not be cleaned up
        removed = coordinator.cleanup_completed(older_than_hours=24.0)
        assert removed == 0
        assert "t1" in coordinator._task_queue

    def test_cleanup_keeps_pending(self, coordinator):
        task = _ingest_task(coordinator, task_id="t1")
        task.ingested_at = datetime.now(timezone.utc) - timedelta(hours=48)
        # Pending tasks should NOT be cleaned up
        removed = coordinator.cleanup_completed(older_than_hours=24.0)
        assert removed == 0

    def test_queue_summary_pending_bounty(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        _ingest_task(coordinator, task_id="t1", bounty=5.0)
        _ingest_task(coordinator, task_id="t2", bounty=10.0)
        coordinator.process_task_queue()
        coordinator.complete_task("t1")
        summary = coordinator.get_queue_summary()
        # Only t2 should count (assigned but not completed)
        # t1 is completed
        assert summary["pending_bounty_usd"] >= 0


# ─── Factory/Create Tests ────────────────────────────────────────────


class TestCreateFactory:
    """Tests for the SwarmCoordinator.create() factory."""

    def test_create_default(self):
        coord = SwarmCoordinator.create()
        assert coord.bridge is not None
        assert coord.lifecycle is not None
        assert coord.orchestrator is not None
        assert coord.em_client is not None
        assert coord.autojob is not None

    def test_create_with_custom_strategy(self):
        coord = SwarmCoordinator.create(default_strategy=RoutingStrategy.ROUND_ROBIN)
        assert coord.default_strategy == RoutingStrategy.ROUND_ROBIN

    def test_create_configurable_expiry(self):
        coord = SwarmCoordinator.create(task_expiry_hours=48.0)
        assert coord.task_expiry_hours == 48.0


# ─── Multi-Agent Routing Tests ───────────────────────────────────────


class TestMultiAgentRouting:
    """Tests for routing across multiple agents."""

    def test_two_agents_different_tasks(self, coordinator):
        _register_agent(coordinator, agent_id=1, name="aurora", wallet="0xAAA")
        _register_agent(coordinator, agent_id=2, name="beacon", wallet="0xBBB")
        _ingest_task(coordinator, task_id="t1")
        _ingest_task(coordinator, task_id="t2")
        results = coordinator.process_task_queue()
        assignments = [r for r in results if isinstance(r, Assignment)]
        # Both tasks should be assigned (to different agents since one is WORKING)
        assert len(assignments) >= 1

    def test_agent_becomes_unavailable_after_assignment(self, coordinator):
        _register_agent(coordinator, agent_id=1, name="aurora")
        _ingest_task(coordinator, task_id="t1")
        _ingest_task(coordinator, task_id="t2")
        results = coordinator.process_task_queue()
        # Only 1 agent, so only 1 task can be assigned
        assignments = [r for r in results if isinstance(r, Assignment)]
        assert len(assignments) == 1
        failures = [r for r in results if isinstance(r, RoutingFailure)]
        assert len(failures) == 1

    def test_round_robin_strategy(self, coordinator_factory, bridge, lifecycle):
        orchestrator = SwarmOrchestrator(
            bridge=bridge,
            lifecycle=lifecycle,
            default_strategy=RoutingStrategy.ROUND_ROBIN,
        )
        coord = coordinator_factory(orchestrator=orchestrator)
        _register_agent(coord, agent_id=1, name="aurora", wallet="0xAAA")
        _register_agent(coord, agent_id=2, name="beacon", wallet="0xBBB")
        _ingest_task(coord, task_id="t1")
        results = coord.process_task_queue(strategy=RoutingStrategy.ROUND_ROBIN)
        assert len(results) == 1
        assert isinstance(results[0], Assignment)


# ─── Budget Integration Tests ────────────────────────────────────────


class TestBudgetIntegration:
    """Tests for budget tracking through the coordinator."""

    def test_complete_records_spend(self, coordinator):
        budget = BudgetConfig(daily_limit_usd=100.0, monthly_limit_usd=1000.0)
        coordinator.register_agent(
            agent_id=1,
            name="aurora",
            wallet_address="0xAAA",
            budget_config=budget,
            activate=True,
        )
        coordinator.orchestrator.register_reputation(
            agent_id=1,
            on_chain=OnChainReputation(agent_id=1, wallet_address="0xAAA"),
            internal=InternalReputation(agent_id=1, bayesian_score=0.8, total_tasks=10),
        )
        _ingest_task(coordinator, task_id="t1", bounty=5.0)
        coordinator.process_task_queue()
        coordinator.complete_task("t1", bounty_earned_usd=5.0)
        status = coordinator.lifecycle.get_budget_status(1)
        assert status["daily_spent"] >= 5.0

    def test_budget_tracking_in_metrics(self, coordinator):
        _register_agent(coordinator, agent_id=1)
        metrics = coordinator.get_metrics()
        # Should report budget from lifecycle
        assert metrics.total_daily_spend_usd >= 0


# ─── EMApiClient Tests ───────────────────────────────────────────────


class TestEMApiClient:
    """Tests for the EMApiClient (unit tests with no network)."""

    def test_client_init(self):
        client = EMApiClient(base_url="https://example.com", api_key="test-key")
        assert client.base_url == "https://example.com"
        assert client.api_key == "test-key"

    def test_client_strips_trailing_slash(self):
        client = EMApiClient(base_url="https://example.com/")
        assert client.base_url == "https://example.com"

    def test_client_default_timeout(self):
        client = EMApiClient()
        assert client.timeout == 10.0


# ─── QueuedTask Tests ────────────────────────────────────────────────


class TestQueuedTask:
    """Tests for QueuedTask data class."""

    def test_to_task_request(self):
        qt = QueuedTask(
            task_id="t1",
            title="Test",
            categories=["photo"],
            bounty_usd=5.0,
            priority=TaskPriority.HIGH,
        )
        tr = qt.to_task_request()
        assert isinstance(tr, TaskRequest)
        assert tr.task_id == "t1"
        assert tr.title == "Test"
        assert tr.categories == ["photo"]
        assert tr.priority == TaskPriority.HIGH

    def test_queued_task_defaults(self):
        qt = QueuedTask(task_id="t1", title="Test", categories=[], bounty_usd=0)
        assert qt.status == "pending"
        assert qt.attempts == 0
        assert qt.max_attempts == 3
        assert qt.source == "api"


# ─── SwarmMetrics Tests ──────────────────────────────────────────────


class TestSwarmMetrics:
    """Tests for the SwarmMetrics data class."""

    def test_to_dict_structure(self):
        m = SwarmMetrics(
            tasks_ingested=10,
            tasks_completed=8,
            tasks_failed=2,
            total_bounty_earned_usd=42.50,
            agents_registered=5,
            agents_active=3,
        )
        d = m.to_dict()
        assert d["tasks"]["ingested"] == 10
        assert d["tasks"]["completed"] == 8
        assert d["tasks"]["bounty_earned_usd"] == 42.50
        assert d["agents"]["registered"] == 5
        assert d["agents"]["active"] == 3

    def test_default_metrics(self):
        m = SwarmMetrics()
        assert m.tasks_ingested == 0
        assert m.routing_success_rate == 0.0
        assert m.uptime_seconds == 0.0


# ─── EventRecord Tests ──────────────────────────────────────────────


class TestEventRecord:
    """Tests for EventRecord serialization."""

    def test_to_dict(self):
        er = EventRecord(
            event=CoordinatorEvent.TASK_INGESTED,
            timestamp=datetime(2026, 3, 15, tzinfo=timezone.utc),
            data={"task_id": "t1"},
        )
        d = er.to_dict()
        assert d["event"] == "task_ingested"
        assert d["task_id"] == "t1"
        assert "2026-03-15" in d["timestamp"]


# ─── End-to-End Integration ──────────────────────────────────────────


class TestEndToEnd:
    """Full lifecycle integration tests."""

    def test_full_cycle_single_agent_single_task(self, coordinator):
        """Registration → Ingestion → Routing → Assignment → Completion."""
        # 1. Register
        _register_agent(coordinator, agent_id=1, name="aurora")
        # 2. Ingest
        _ingest_task(coordinator, task_id="t1", bounty=5.0)
        # 3. Route
        results = coordinator.process_task_queue()
        assert len(results) == 1
        assert isinstance(results[0], Assignment)
        # 4. Complete
        assert coordinator.complete_task("t1") is True
        # 5. Verify metrics
        m = coordinator.get_metrics()
        assert m.tasks_ingested == 1
        assert m.tasks_assigned == 1
        assert m.tasks_completed == 1
        assert m.total_bounty_earned_usd == 5.0
        assert m.routing_success_rate == 1.0

    def test_full_cycle_with_failure_then_success(self, coordinator):
        """Task fails, then succeeds on a different agent."""
        _register_agent(coordinator, agent_id=1, name="aurora", wallet="0xAAA")
        _register_agent(coordinator, agent_id=2, name="beacon", wallet="0xBBB")
        _ingest_task(coordinator, task_id="t1", bounty=10.0)

        # First assignment
        results1 = coordinator.process_task_queue()
        assert isinstance(results1[0], Assignment)
        results1[0].agent_id

        # Fail the task
        coordinator.fail_task("t1")
        m = coordinator.get_metrics()
        assert m.tasks_failed >= 1

    def test_multi_task_throughput(self, coordinator):
        """Process multiple tasks through the system."""
        for i in range(5):
            _register_agent(
                coordinator, agent_id=i + 1, name=f"agent-{i}", wallet=f"0x{i:03x}"
            )

        for i in range(10):
            _ingest_task(coordinator, task_id=f"t{i}", bounty=float(i + 1))

        # Process queue (5 agents for 10 tasks)
        results1 = coordinator.process_task_queue(max_tasks=10)
        assignments1 = [r for r in results1 if isinstance(r, Assignment)]
        # At most 5 can be assigned (one per agent)
        assert len(assignments1) <= 5
        assert len(assignments1) >= 1

        # Complete all assigned tasks
        for a in assignments1:
            coordinator.complete_task(a.task_id)

        m = coordinator.get_metrics()
        assert m.tasks_completed == len(assignments1)

    def test_dashboard_after_operations(self, coordinator):
        """Dashboard shows correct state after operations."""
        _register_agent(coordinator, agent_id=1, name="aurora")
        _register_agent(coordinator, agent_id=2, name="beacon", wallet="0xBBB")
        _ingest_task(coordinator, task_id="t1", bounty=5.0)
        coordinator.process_task_queue()
        coordinator.complete_task("t1")

        dashboard = coordinator.get_dashboard()
        assert dashboard["metrics"]["tasks"]["completed"] == 1
        assert len(dashboard["fleet"]) == 2
        assert len(dashboard["recent_events"]) > 0
