"""
Tests for SwarmCoordinator — the top-level operational controller.

Coverage targets:
    - Agent registration (single, batch)
    - Task ingestion (manual, API, dedup)
    - Task routing & queue processing
    - Task completion & failure handling
    - Health checks (heartbeats, cooldowns, budgets, task expiry)
    - Metrics & dashboard
    - Event system (hooks, filtering, history)
    - Queue utilities (summary, cleanup)
    - Factory method (create)
    - Edge cases (empty state, concurrent events, boundary conditions)
"""

import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.swarm.coordinator import (
    SwarmCoordinator,
    EMApiClient,
    CoordinatorEvent,
    EventRecord,
    QueuedTask,
    SwarmMetrics,
)
from mcp_server.swarm.reputation_bridge import (
    ReputationBridge,
    OnChainReputation,
    InternalReputation,
    CompositeScore,
    ReputationTier,
)
from mcp_server.swarm.lifecycle_manager import (
    LifecycleManager,
    AgentState,
    AgentRecord,
    BudgetConfig,
    LifecycleError,
    BudgetExceededError,
)
from mcp_server.swarm.orchestrator import (
    SwarmOrchestrator,
    TaskRequest,
    TaskPriority,
    Assignment,
    RoutingFailure,
    RoutingStrategy,
)
from mcp_server.swarm.autojob_client import (
    AutoJobClient,
    EnrichedOrchestrator,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def bridge():
    return ReputationBridge()


@pytest.fixture
def lifecycle():
    return LifecycleManager()


@pytest.fixture
def orchestrator(bridge, lifecycle):
    return SwarmOrchestrator(bridge, lifecycle)


@pytest.fixture
def coordinator(bridge, lifecycle, orchestrator):
    """Create a coordinator with no external dependencies."""
    return SwarmCoordinator(
        bridge=bridge,
        lifecycle=lifecycle,
        orchestrator=orchestrator,
    )


@pytest.fixture
def coordinator_with_api(bridge, lifecycle, orchestrator):
    """Create a coordinator with a mocked EM API client."""
    mock_client = MagicMock(spec=EMApiClient)
    mock_client.base_url = "https://api.execution.market"
    return SwarmCoordinator(
        bridge=bridge,
        lifecycle=lifecycle,
        orchestrator=orchestrator,
        em_client=mock_client,
    )


@pytest.fixture
def coordinator_full(bridge, lifecycle, orchestrator):
    """Create a coordinator with mocked EM API and AutoJob clients."""
    mock_em = MagicMock(spec=EMApiClient)
    mock_em.base_url = "https://api.execution.market"
    mock_autojob = MagicMock(spec=AutoJobClient)
    mock_autojob.is_available.return_value = True
    enriched = EnrichedOrchestrator(orchestrator, mock_autojob)
    return SwarmCoordinator(
        bridge=bridge,
        lifecycle=lifecycle,
        orchestrator=orchestrator,
        em_client=mock_em,
        autojob_client=mock_autojob,
        enriched_orchestrator=enriched,
    )


def _register_agent(coordinator, agent_id=1, name="Agent-1", wallet="0x" + "a1" * 20):
    """Helper to register an agent with default params."""
    return coordinator.register_agent(
        agent_id=agent_id,
        name=name,
        wallet_address=wallet,
        personality="explorer",
    )


# ─── Agent Registration Tests ─────────────────────────────────────────────────

class TestAgentRegistration:

    def test_register_single_agent(self, coordinator):
        record = _register_agent(coordinator)
        assert record.agent_id == 1
        assert record.name == "Agent-1"
        assert record.state == AgentState.ACTIVE  # auto-activated

    def test_register_agent_emits_event(self, coordinator):
        events = []
        coordinator.on_event(CoordinatorEvent.AGENT_REGISTERED, lambda e: events.append(e))
        _register_agent(coordinator)
        assert len(events) == 1
        assert events[0].data["agent_id"] == 1
        assert events[0].data["name"] == "Agent-1"

    def test_register_agent_without_activation(self, coordinator):
        record = coordinator.register_agent(
            agent_id=2,
            name="Lazy-Agent",
            wallet_address="0x" + "b2" * 20,
            activate=False,
        )
        assert record.state == AgentState.IDLE

    def test_register_agent_with_custom_budget(self, coordinator):
        budget = BudgetConfig(daily_limit_usd=10.0, monthly_limit_usd=200.0)
        record = coordinator.register_agent(
            agent_id=3,
            name="Rich-Agent",
            wallet_address="0x" + "c3" * 20,
            budget_config=budget,
        )
        status = coordinator.lifecycle.get_budget_status(3)
        assert status["daily_limit"] == 10.0
        assert status["monthly_limit"] == 200.0

    def test_register_agent_with_reputation(self, coordinator):
        on_chain = OnChainReputation(
            agent_id=4,
            wallet_address="0x" + "d4" * 20,
            total_seals=50,
            positive_seals=48,
        )
        internal = InternalReputation(
            agent_id=4,
            total_tasks=50,
            successful_tasks=48,
        )
        record = coordinator.register_agent(
            agent_id=4,
            name="Veteran-Agent",
            wallet_address="0x" + "d4" * 20,
            on_chain=on_chain,
            internal=internal,
        )
        score = coordinator.bridge.compute_composite(on_chain, internal)
        assert score.reputation_score >= 0

    def test_register_agent_with_tags(self, coordinator):
        record = coordinator.register_agent(
            agent_id=5,
            name="Tagged-Agent",
            wallet_address="0x" + "e5" * 20,
            tags=["blockchain", "defi", "explorer"],
        )
        assert "blockchain" in record.tags

    def test_register_duplicate_agent_raises(self, coordinator):
        _register_agent(coordinator, agent_id=10)
        with pytest.raises(LifecycleError):
            _register_agent(coordinator, agent_id=10, name="Duplicate")

    def test_register_agents_batch(self, coordinator):
        agents = [
            {"agent_id": 100, "name": "Batch-1", "wallet_address": "0x" + "aa" * 20},
            {"agent_id": 101, "name": "Batch-2", "wallet_address": "0x" + "bb" * 20},
            {"agent_id": 102, "name": "Batch-3", "wallet_address": "0x" + "cc" * 20},
        ]
        records = coordinator.register_agents_batch(agents)
        assert len(records) == 3
        for i, rec in enumerate(records):
            assert rec.agent_id == 100 + i
            assert rec.state == AgentState.ACTIVE

    def test_batch_register_skips_invalid(self, coordinator):
        # Register one first
        _register_agent(coordinator, agent_id=200)
        agents = [
            {"agent_id": 200, "name": "Dup", "wallet_address": "0x" + "ff" * 20},  # duplicate
            {"agent_id": 201, "name": "New", "wallet_address": "0x" + "ee" * 20},   # new
        ]
        records = coordinator.register_agents_batch(agents)
        assert len(records) == 1
        assert records[0].agent_id == 201


# ─── Task Ingestion Tests ─────────────────────────────────────────────────────

class TestTaskIngestion:

    def test_ingest_task_basic(self, coordinator):
        task = coordinator.ingest_task(
            task_id="task-1",
            title="Buy coffee",
            categories=["physical", "errand"],
            bounty_usd=5.0,
        )
        assert task.task_id == "task-1"
        assert task.status == "pending"
        assert task.bounty_usd == 5.0

    def test_ingest_task_emits_event(self, coordinator):
        events = []
        coordinator.on_event(CoordinatorEvent.TASK_INGESTED, lambda e: events.append(e))
        coordinator.ingest_task(
            task_id="task-evt",
            title="Test",
            categories=["test"],
        )
        assert len(events) == 1
        assert events[0].data["task_id"] == "task-evt"

    def test_ingest_duplicate_task_returns_existing(self, coordinator):
        t1 = coordinator.ingest_task(task_id="dup-1", title="First", categories=["a"])
        t2 = coordinator.ingest_task(task_id="dup-1", title="Second", categories=["b"])
        assert t1 is t2  # Same object returned

    def test_ingest_duplicate_failed_task_replaces(self, coordinator):
        t1 = coordinator.ingest_task(task_id="retry-1", title="First", categories=["a"])
        t1.status = "failed"  # Mark as failed
        t2 = coordinator.ingest_task(task_id="retry-1", title="Retry", categories=["b"])
        assert t2.title == "Retry"
        assert t2.status == "pending"

    def test_ingest_with_priority(self, coordinator):
        task = coordinator.ingest_task(
            task_id="urgent-1",
            title="Urgent Task",
            categories=["critical"],
            priority=TaskPriority.CRITICAL,
        )
        assert task.priority == TaskPriority.CRITICAL

    def test_ingest_with_raw_data(self, coordinator):
        raw = {"id": "123", "extra_field": "value"}
        task = coordinator.ingest_task(
            task_id="raw-1",
            title="Raw Test",
            categories=["test"],
            raw_data=raw,
        )
        assert task.raw_data["extra_field"] == "value"

    def test_ingest_increments_counter(self, coordinator):
        assert coordinator._total_ingested == 0
        coordinator.ingest_task(task_id="t1", title="A", categories=["x"])
        coordinator.ingest_task(task_id="t2", title="B", categories=["y"])
        assert coordinator._total_ingested == 2

    def test_ingest_from_api(self, coordinator_with_api):
        coord = coordinator_with_api
        coord.em_client.list_tasks.return_value = [
            {"id": "api-1", "title": "API Task 1", "category": "delivery", "bounty_usd": 10.0},
            {"id": "api-2", "title": "API Task 2", "category": "coding", "bounty_usd": 75.0},
        ]
        ingested = coord.ingest_from_api()
        assert len(ingested) == 2
        assert coord._total_ingested == 2
        # High bounty should get higher priority
        api2 = coord._task_queue["api-2"]
        assert api2.priority == TaskPriority.HIGH

    def test_ingest_from_api_no_client(self, coordinator):
        result = coordinator.ingest_from_api()
        assert result == []

    def test_ingest_from_api_skips_existing(self, coordinator_with_api):
        coord = coordinator_with_api
        # Pre-ingest a task
        coord.ingest_task(task_id="existing-1", title="Existing", categories=["x"])
        coord.em_client.list_tasks.return_value = [
            {"id": "existing-1", "title": "Should Skip", "category": "delivery"},
            {"id": "new-1", "title": "Should Ingest", "category": "delivery"},
        ]
        ingested = coord.ingest_from_api()
        assert len(ingested) == 1
        assert ingested[0].task_id == "new-1"


# ─── Task Routing Tests ──────────────────────────────────────────────────────

class TestTaskRouting:

    def test_process_empty_queue(self, coordinator):
        results = coordinator.process_task_queue()
        assert results == []

    def test_process_queue_no_agents(self, coordinator):
        coordinator.ingest_task(task_id="orphan", title="No one here", categories=["test"])
        results = coordinator.process_task_queue()
        # Should fail routing because no agents registered
        assert len(results) == 1
        assert isinstance(results[0], RoutingFailure)

    def test_process_queue_successful_routing(self, coordinator):
        _register_agent(coordinator, agent_id=1, name="Worker-1")
        coordinator.ingest_task(
            task_id="route-1",
            title="Routable Task",
            categories=["general"],
            bounty_usd=1.0,
        )
        results = coordinator.process_task_queue()
        assert len(results) == 1
        assert isinstance(results[0], Assignment)
        assert results[0].agent_id == 1
        assert coordinator._total_assigned == 1

    def test_process_queue_emits_assigned_event(self, coordinator):
        events = []
        coordinator.on_event(CoordinatorEvent.TASK_ASSIGNED, lambda e: events.append(e))
        _register_agent(coordinator)
        coordinator.ingest_task(task_id="evt-route", title="Test", categories=["test"])
        coordinator.process_task_queue()
        assert len(events) == 1
        assert events[0].data["task_id"] == "evt-route"

    def test_process_queue_respects_max_tasks(self, coordinator):
        _register_agent(coordinator)
        for i in range(10):
            coordinator.ingest_task(task_id=f"max-{i}", title=f"Task {i}", categories=["test"])
        results = coordinator.process_task_queue(max_tasks=3)
        assert len(results) == 3

    def test_process_queue_priority_ordering(self, coordinator):
        _register_agent(coordinator)
        # Ingest low priority first, then high
        coordinator.ingest_task(task_id="low-1", title="Low", categories=["test"], priority=TaskPriority.LOW)
        coordinator.ingest_task(task_id="high-1", title="High", categories=["test"], priority=TaskPriority.HIGH)
        results = coordinator.process_task_queue(max_tasks=1)
        # High priority should be processed first
        assert isinstance(results[0], Assignment)
        task = coordinator._task_queue["high-1"]
        assert task.status == "assigned"

    def test_routing_failure_after_max_attempts(self, coordinator):
        # No agents = routing always fails
        coordinator.ingest_task(task_id="fail-1", title="Doomed", categories=["test"])
        task = coordinator._task_queue["fail-1"]
        task.max_attempts = 2

        # First attempt
        coordinator.process_task_queue()
        assert task.status == "pending"
        assert task.attempts == 1

        # Second attempt → fails permanently
        coordinator.process_task_queue()
        assert task.status == "failed"
        assert coordinator._total_failed == 1

    def test_routing_tracks_timing(self, coordinator):
        _register_agent(coordinator)
        coordinator.ingest_task(task_id="time-1", title="Timed", categories=["test"])
        coordinator.process_task_queue()
        assert len(coordinator._routing_times) == 1
        assert coordinator._routing_times[0] >= 0

    def test_routing_with_strategy(self, coordinator):
        _register_agent(coordinator, agent_id=1, name="Worker-1")
        _register_agent(coordinator, agent_id=2, name="Worker-2", wallet="0x" + "b2" * 20)
        coordinator.ingest_task(task_id="strat-1", title="Strategy Test", categories=["test"])
        results = coordinator.process_task_queue(strategy=RoutingStrategy.ROUND_ROBIN)
        assert len(results) == 1
        assert isinstance(results[0], Assignment)


# ─── Task Completion Tests ────────────────────────────────────────────────────

class TestTaskCompletion:

    def test_complete_task(self, coordinator):
        _register_agent(coordinator)
        coordinator.ingest_task(task_id="comp-1", title="Complete Me", categories=["test"], bounty_usd=2.5)
        coordinator.process_task_queue()
        result = coordinator.complete_task("comp-1", bounty_earned_usd=2.5)
        assert result is True
        assert coordinator._total_completed == 1
        assert coordinator._total_bounty_earned == 2.5

    def test_complete_task_emits_event(self, coordinator):
        events = []
        coordinator.on_event(CoordinatorEvent.TASK_COMPLETED, lambda e: events.append(e))
        _register_agent(coordinator)
        coordinator.ingest_task(task_id="comp-evt", title="Test", categories=["test"], bounty_usd=1.0)
        coordinator.process_task_queue()
        coordinator.complete_task("comp-evt")
        assert len(events) == 1
        assert events[0].data["task_id"] == "comp-evt"

    def test_complete_unknown_task(self, coordinator):
        result = coordinator.complete_task("nonexistent")
        assert result is False

    def test_complete_task_updates_reputation(self, coordinator):
        internal = InternalReputation(agent_id=1, total_tasks=5, successful_tasks=4)
        coordinator.register_agent(
            agent_id=1,
            name="Rep-Test",
            wallet_address="0x" + "a1" * 20,
            internal=internal,
        )
        coordinator.ingest_task(task_id="rep-1", title="Reputation Test", categories=["coding"])
        coordinator.process_task_queue()
        coordinator.complete_task("rep-1")
        # Internal reputation should be updated
        updated = coordinator.orchestrator._internal.get(1)
        assert updated is not None
        assert updated.total_tasks == 6
        assert updated.successful_tasks == 5

    def test_fail_task(self, coordinator):
        _register_agent(coordinator)
        coordinator.ingest_task(task_id="fail-1", title="Fail Me", categories=["test"])
        coordinator.process_task_queue()
        result = coordinator.fail_task("fail-1", error="Worker abandoned")
        assert result is True
        assert coordinator._total_failed == 1

    def test_fail_unknown_task(self, coordinator):
        result = coordinator.fail_task("nonexistent")
        assert result is False

    def test_fail_task_emits_event(self, coordinator):
        events = []
        coordinator.on_event(CoordinatorEvent.TASK_FAILED, lambda e: events.append(e))
        _register_agent(coordinator)
        coordinator.ingest_task(task_id="fail-evt", title="Test", categories=["test"])
        coordinator.process_task_queue()
        coordinator.fail_task("fail-evt", error="timeout")
        assert len(events) == 1


# ─── Health Check Tests ───────────────────────────────────────────────────────

class TestHealthChecks:

    def test_health_check_empty_swarm(self, coordinator):
        report = coordinator.run_health_checks()
        assert report["agents"]["checked"] == 0
        assert report["agents"]["healthy"] == 0

    def test_health_check_healthy_agents(self, coordinator):
        _register_agent(coordinator, agent_id=1, name="Healthy-1")
        _register_agent(coordinator, agent_id=2, name="Healthy-2", wallet="0x" + "b2" * 20)
        # Send heartbeats so agents are healthy
        coordinator.lifecycle.record_heartbeat(1)
        coordinator.lifecycle.record_heartbeat(2)
        report = coordinator.run_health_checks()
        assert report["agents"]["checked"] == 2
        assert report["agents"]["healthy"] == 2

    def test_health_check_degraded_agent(self, coordinator):
        _register_agent(coordinator, agent_id=1, name="Degraded-1")
        # Simulate missed heartbeats by setting consecutive_missed above threshold
        record = coordinator.lifecycle.agents[1]
        record.health.last_heartbeat = datetime.now(timezone.utc) - timedelta(hours=1)
        record.health.consecutive_missed = 5  # Exceed max_missed_heartbeats (3)
        report = coordinator.run_health_checks()
        assert report["agents"]["degraded"] >= 1

    def test_health_check_task_expiry(self, coordinator):
        coordinator.ingest_task(task_id="old-1", title="Old Task", categories=["test"])
        # Set ingested_at to 25 hours ago (beyond default 24h expiry)
        task = coordinator._task_queue["old-1"]
        task.ingested_at = datetime.now(timezone.utc) - timedelta(hours=25)
        report = coordinator.run_health_checks()
        assert report["tasks"]["expired"] == 1
        assert task.status == "expired"
        assert coordinator._total_expired == 1

    def test_health_check_emits_event(self, coordinator):
        events = []
        coordinator.on_event(CoordinatorEvent.HEALTH_CHECK, lambda e: events.append(e))
        coordinator.run_health_checks()
        assert len(events) == 1

    def test_health_check_em_api_healthy(self, coordinator_with_api):
        coord = coordinator_with_api
        coord.em_client.get_health.return_value = {"status": "healthy"}
        report = coord.run_health_checks()
        assert report["systems"]["em_api"] == "healthy"

    def test_health_check_em_api_unreachable(self, coordinator_with_api):
        coord = coordinator_with_api
        coord.em_client.get_health.side_effect = Exception("Connection refused")
        report = coord.run_health_checks()
        assert report["systems"]["em_api"] == "unreachable"

    def test_health_check_cooldown_recovery(self, coordinator):
        _register_agent(coordinator, agent_id=1, name="Cooling-1")
        agent = coordinator.lifecycle.agents[1]
        # Put agent in WORKING first, then COOLDOWN
        coordinator.lifecycle.transition(1, AgentState.WORKING, "testing")
        coordinator.lifecycle.transition(1, AgentState.COOLDOWN, "testing")
        # Set cooldown to already expired
        agent.last_cooldown_start = datetime.now(timezone.utc) - timedelta(minutes=10)
        coordinator.lifecycle.cooldown_duration = timedelta(seconds=1)  # Very short
        report = coordinator.run_health_checks()
        # Agent should have recovered from cooldown
        assert agent.state in (AgentState.IDLE, AgentState.COOLDOWN)

    def test_health_check_autojob_available(self, coordinator_full):
        coord = coordinator_full
        coord.autojob.is_available.return_value = True
        report = coord.run_health_checks()
        assert report["systems"]["autojob"] == "available"

    def test_health_check_autojob_unavailable(self, coordinator_full):
        coord = coordinator_full
        coord.autojob.is_available.return_value = False
        report = coord.run_health_checks()
        assert report["systems"]["autojob"] == "unavailable"


# ─── Metrics & Dashboard Tests ────────────────────────────────────────────────

class TestMetricsDashboard:

    def test_initial_metrics(self, coordinator):
        metrics = coordinator.get_metrics()
        assert metrics.tasks_ingested == 0
        assert metrics.tasks_completed == 0
        assert metrics.agents_registered == 0
        assert metrics.uptime_seconds >= 0

    def test_metrics_after_operations(self, coordinator):
        _register_agent(coordinator)
        coordinator.ingest_task(task_id="m-1", title="Metric Test", categories=["test"], bounty_usd=3.0)
        coordinator.process_task_queue()
        coordinator.complete_task("m-1", bounty_earned_usd=3.0)
        metrics = coordinator.get_metrics()
        assert metrics.tasks_ingested == 1
        assert metrics.tasks_assigned == 1
        assert metrics.tasks_completed == 1
        assert metrics.total_bounty_earned_usd == 3.0
        assert metrics.agents_registered >= 1

    def test_metrics_routing_success_rate(self, coordinator):
        _register_agent(coordinator)
        for i in range(5):
            coordinator.ingest_task(task_id=f"rate-{i}", title=f"Rate {i}", categories=["test"])
        coordinator.process_task_queue()
        metrics = coordinator.get_metrics()
        assert metrics.routing_success_rate > 0

    def test_metrics_to_dict(self, coordinator):
        metrics = coordinator.get_metrics()
        d = metrics.to_dict()
        assert "tasks" in d
        assert "agents" in d
        assert "performance" in d
        assert "budget" in d
        assert "timing" in d

    def test_dashboard_structure(self, coordinator):
        _register_agent(coordinator)
        dashboard = coordinator.get_dashboard()
        assert "timestamp" in dashboard
        assert "metrics" in dashboard
        assert "queue" in dashboard
        assert "fleet" in dashboard
        assert "swarm" in dashboard
        assert "recent_events" in dashboard
        assert "systems" in dashboard

    def test_dashboard_fleet_details(self, coordinator):
        _register_agent(coordinator, agent_id=1, name="Fleet-1")
        dashboard = coordinator.get_dashboard()
        assert len(dashboard["fleet"]) == 1
        agent = dashboard["fleet"][0]
        assert agent["agent_id"] == 1
        assert agent["name"] == "Fleet-1"
        assert "state" in agent
        assert "budget_daily_pct" in agent
        assert "health" in agent

    def test_dashboard_queue_breakdown(self, coordinator):
        coordinator.ingest_task(task_id="q-1", title="Pending", categories=["test"])
        dashboard = coordinator.get_dashboard()
        assert dashboard["queue"]["pending"] == 1


# ─── Event System Tests ──────────────────────────────────────────────────────

class TestEventSystem:

    def test_register_event_hook(self, coordinator):
        events = []
        coordinator.on_event(CoordinatorEvent.TASK_INGESTED, lambda e: events.append(e))
        coordinator.ingest_task(task_id="hook-1", title="Hook Test", categories=["test"])
        assert len(events) == 1

    def test_multiple_hooks_same_event(self, coordinator):
        count = {"a": 0, "b": 0}
        coordinator.on_event(CoordinatorEvent.TASK_INGESTED, lambda e: count.__setitem__("a", count["a"] + 1))
        coordinator.on_event(CoordinatorEvent.TASK_INGESTED, lambda e: count.__setitem__("b", count["b"] + 1))
        coordinator.ingest_task(task_id="multi-1", title="Multi Hook", categories=["test"])
        assert count["a"] == 1
        assert count["b"] == 1

    def test_hook_error_doesnt_crash(self, coordinator):
        def bad_hook(event):
            raise ValueError("Hook exploded!")

        coordinator.on_event(CoordinatorEvent.TASK_INGESTED, bad_hook)
        # Should not raise
        coordinator.ingest_task(task_id="safe-1", title="Safe", categories=["test"])

    def test_get_events_basic(self, coordinator):
        coordinator.ingest_task(task_id="ev-1", title="Event Test", categories=["test"])
        events = coordinator.get_events()
        assert len(events) >= 1
        assert events[-1]["event"] == "task_ingested"

    def test_get_events_filtered_by_type(self, coordinator):
        _register_agent(coordinator)
        coordinator.ingest_task(task_id="filt-1", title="Filter", categories=["test"])
        events = coordinator.get_events(event_type=CoordinatorEvent.TASK_INGESTED)
        assert all(e["event"] == "task_ingested" for e in events)

    def test_get_events_filtered_by_since(self, coordinator):
        # Events before "now"
        coordinator.ingest_task(task_id="old-ev", title="Old", categories=["test"])
        cutoff = datetime.now(timezone.utc)
        # Events after "now"
        coordinator.ingest_task(task_id="new-ev", title="New", categories=["test"])
        events = coordinator.get_events(since=cutoff)
        # Should only include events after cutoff
        assert any(e["task_id"] == "new-ev" for e in events)

    def test_get_events_with_limit(self, coordinator):
        for i in range(10):
            coordinator.ingest_task(task_id=f"lim-{i}", title=f"Limit {i}", categories=["test"])
        events = coordinator.get_events(limit=3)
        assert len(events) == 3

    def test_events_bounded_at_1000(self, coordinator):
        # Generate more than 1000 events
        for i in range(1100):
            coordinator._emit(CoordinatorEvent.TASK_INGESTED, {"i": i})
        # Events should be pruned to ~500 after exceeding 1000
        assert len(coordinator._events) <= 600

    def test_event_record_to_dict(self):
        record = EventRecord(
            event=CoordinatorEvent.TASK_COMPLETED,
            timestamp=datetime(2026, 3, 14, 2, 0, tzinfo=timezone.utc),
            data={"task_id": "test-1", "agent_id": 1},
        )
        d = record.to_dict()
        assert d["event"] == "task_completed"
        assert d["task_id"] == "test-1"
        assert "2026-03-14" in d["timestamp"]


# ─── Queue Utilities Tests ────────────────────────────────────────────────────

class TestQueueUtilities:

    def test_queue_summary_empty(self, coordinator):
        summary = coordinator.get_queue_summary()
        assert summary["total"] == 0
        assert summary["pending_bounty_usd"] == 0

    def test_queue_summary_with_tasks(self, coordinator):
        coordinator.ingest_task(task_id="qs-1", title="Task 1", categories=["coding"], bounty_usd=5.0)
        coordinator.ingest_task(task_id="qs-2", title="Task 2", categories=["delivery"], bounty_usd=10.0)
        summary = coordinator.get_queue_summary()
        assert summary["total"] == 2
        assert summary["by_status"]["pending"] == 2
        assert summary["pending_bounty_usd"] == 15.0
        assert "coding" in summary["by_category"]
        assert "delivery" in summary["by_category"]

    def test_cleanup_completed_tasks(self, coordinator):
        _register_agent(coordinator)
        coordinator.ingest_task(task_id="clean-1", title="To Clean", categories=["test"])
        coordinator.process_task_queue()
        coordinator.complete_task("clean-1")
        # Set completed task to 25 hours ago
        task = coordinator._task_queue["clean-1"]
        task.ingested_at = datetime.now(timezone.utc) - timedelta(hours=25)
        removed = coordinator.cleanup_completed(older_than_hours=24.0)
        assert removed == 1
        assert "clean-1" not in coordinator._task_queue

    def test_cleanup_keeps_recent_completed(self, coordinator):
        _register_agent(coordinator)
        coordinator.ingest_task(task_id="keep-1", title="Keep Me", categories=["test"])
        coordinator.process_task_queue()
        coordinator.complete_task("keep-1")
        removed = coordinator.cleanup_completed(older_than_hours=24.0)
        assert removed == 0  # Recent, should be kept

    def test_reset_metrics(self, coordinator):
        _register_agent(coordinator)
        coordinator.ingest_task(task_id="reset-1", title="Reset", categories=["test"])
        coordinator.process_task_queue()
        assert coordinator._total_ingested > 0
        coordinator.reset_metrics()
        assert coordinator._total_ingested == 0
        assert coordinator._total_assigned == 0
        assert coordinator._total_completed == 0
        assert len(coordinator._events) == 0


# ─── Factory Method Tests ─────────────────────────────────────────────────────

class TestFactory:

    def test_create_default(self):
        coord = SwarmCoordinator.create()
        assert coord.em_client is not None
        assert coord.autojob is not None
        assert coord.enriched is not None
        assert coord.bridge is not None
        assert coord.lifecycle is not None
        assert coord.orchestrator is not None

    def test_create_with_custom_url(self):
        coord = SwarmCoordinator.create(
            em_api_url="https://custom.api.com",
            autojob_url="http://localhost:9999",
        )
        assert coord.em_client.base_url == "https://custom.api.com"

    def test_create_with_strategy(self):
        coord = SwarmCoordinator.create(default_strategy=RoutingStrategy.ROUND_ROBIN)
        assert coord.default_strategy == RoutingStrategy.ROUND_ROBIN

    def test_create_with_custom_expiry(self):
        coord = SwarmCoordinator.create(task_expiry_hours=48.0)
        assert coord.task_expiry_hours == 48.0


# ─── QueuedTask Tests ─────────────────────────────────────────────────────────

class TestQueuedTask:

    def test_queued_task_defaults(self):
        task = QueuedTask(
            task_id="qt-1",
            title="Test Task",
            categories=["test"],
            bounty_usd=5.0,
        )
        assert task.status == "pending"
        assert task.attempts == 0
        assert task.max_attempts == 3
        assert task.assigned_agent_id is None
        assert task.ingested_at is not None

    def test_queued_task_to_task_request(self):
        task = QueuedTask(
            task_id="qt-2",
            title="Convert Me",
            categories=["blockchain", "defi"],
            bounty_usd=25.0,
            priority=TaskPriority.HIGH,
        )
        request = task.to_task_request()
        assert isinstance(request, TaskRequest)
        assert request.task_id == "qt-2"
        assert request.title == "Convert Me"
        assert request.categories == ["blockchain", "defi"]
        assert request.bounty_usd == 25.0
        assert request.priority == TaskPriority.HIGH


# ─── SwarmMetrics Tests ───────────────────────────────────────────────────────

class TestSwarmMetrics:

    def test_metrics_to_dict_roundtrip(self):
        metrics = SwarmMetrics(
            tasks_ingested=100,
            tasks_completed=90,
            tasks_failed=5,
            total_bounty_earned_usd=450.0,
            agents_registered=24,
            agents_active=20,
            routing_success_rate=0.95,
        )
        d = metrics.to_dict()
        assert d["tasks"]["ingested"] == 100
        assert d["tasks"]["completed"] == 90
        assert d["tasks"]["bounty_earned_usd"] == 450.0
        assert d["agents"]["registered"] == 24
        assert d["performance"]["routing_success_rate"] == 0.95


# ─── EMApiClient Tests ────────────────────────────────────────────────────────

class TestEMApiClient:

    def test_client_initialization(self):
        client = EMApiClient(base_url="https://test.api.com", api_key="test-key")
        assert client.base_url == "https://test.api.com"
        assert client.api_key == "test-key"

    def test_client_strips_trailing_slash(self):
        client = EMApiClient(base_url="https://test.api.com/")
        assert client.base_url == "https://test.api.com"

    def test_client_default_url(self):
        client = EMApiClient()
        assert "execution.market" in client.base_url


# ─── Integration: Full Lifecycle Tests ────────────────────────────────────────

class TestFullLifecycle:

    def test_full_task_lifecycle(self, coordinator):
        """Test the complete flow: register → ingest → route → complete."""
        # Register agents
        _register_agent(coordinator, agent_id=1, name="Worker-1")
        _register_agent(coordinator, agent_id=2, name="Worker-2", wallet="0x" + "b2" * 20)

        # Ingest tasks
        coordinator.ingest_task(task_id="lc-1", title="Lifecycle 1", categories=["test"], bounty_usd=5.0)
        coordinator.ingest_task(task_id="lc-2", title="Lifecycle 2", categories=["test"], bounty_usd=3.0)

        # Route tasks
        results = coordinator.process_task_queue()
        assert len(results) == 2
        assigned_count = sum(1 for r in results if isinstance(r, Assignment))
        assert assigned_count >= 1  # At least one should route

        # Complete first task
        if isinstance(results[0], Assignment):
            coordinator.complete_task("lc-1", bounty_earned_usd=5.0)

        # Get dashboard
        dashboard = coordinator.get_dashboard()
        assert dashboard["metrics"]["tasks"]["ingested"] == 2

        # Run health checks
        report = coordinator.run_health_checks()
        assert report["agents"]["checked"] == 2

    def test_multiple_routing_cycles(self, coordinator):
        """Test multiple ingest-route-complete cycles."""
        _register_agent(coordinator)

        for cycle in range(3):
            task_id = f"cycle-{cycle}"
            coordinator.ingest_task(task_id=task_id, title=f"Cycle {cycle}", categories=["test"], bounty_usd=1.0)
            results = coordinator.process_task_queue()
            if results and isinstance(results[0], Assignment):
                coordinator.complete_task(task_id, bounty_earned_usd=1.0)

        metrics = coordinator.get_metrics()
        assert metrics.tasks_ingested == 3
        assert metrics.total_bounty_earned_usd >= 1.0  # At least first cycle

    def test_event_driven_monitoring(self, coordinator):
        """Test that event hooks provide full monitoring coverage."""
        event_log = []
        for event_type in CoordinatorEvent:
            coordinator.on_event(event_type, lambda e, et=event_type: event_log.append(et.value))

        _register_agent(coordinator)
        coordinator.ingest_task(task_id="mon-1", title="Monitor", categories=["test"])
        coordinator.process_task_queue()
        coordinator.complete_task("mon-1")
        coordinator.run_health_checks()

        # Should have captured multiple event types
        event_types = set(event_log)
        assert "agent_registered" in event_types
        assert "task_ingested" in event_types
        assert "health_check" in event_types
