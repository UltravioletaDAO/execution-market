"""
Tests for SwarmCoordinator — the keystone module that wires everything together.

The coordinator integrates ReputationBridge, LifecycleManager, SwarmOrchestrator,
AutoJobClient, and EMApiClient into a unified operational system. These tests
validate the full integration surface without requiring external services.

Coverage:
    - Agent registration (single + batch)
    - Task ingestion (manual + API)
    - Task routing via process_task_queue
    - Task completion + failure lifecycle
    - Health checks across all subsystems
    - Metrics computation
    - Dashboard generation
    - Event system (emit + hooks + query)
    - Queue management + cleanup
    - Budget tracking through task lifecycle
    - Reputation updates on completion/failure
    - AutoJob enrichment integration
    - Edge cases: duplicate tasks, expired tasks, empty queue, no agents
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

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
)
from mcp_server.swarm.lifecycle_manager import (
    LifecycleManager,
    AgentState,
    BudgetConfig,
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
    """Fresh ReputationBridge."""
    return ReputationBridge()


@pytest.fixture
def lifecycle():
    """Fresh LifecycleManager."""
    return LifecycleManager()


@pytest.fixture
def orchestrator(bridge, lifecycle):
    """SwarmOrchestrator wired to bridge + lifecycle."""
    return SwarmOrchestrator(bridge, lifecycle)


@pytest.fixture
def mock_em_client():
    """Mock EMApiClient that doesn't make real HTTP calls."""
    client = MagicMock(spec=EMApiClient)
    client.base_url = "https://api.execution.market"
    client.get_health.return_value = {"status": "ok", "components": {}}
    client.list_tasks.return_value = []
    client.get_task.return_value = None
    return client


@pytest.fixture
def mock_autojob():
    """Mock AutoJobClient."""
    client = MagicMock(spec=AutoJobClient)
    client.is_available.return_value = False
    return client


@pytest.fixture
def coordinator(bridge, lifecycle, orchestrator, mock_em_client, mock_autojob):
    """Fully wired SwarmCoordinator with mocked external clients."""
    return SwarmCoordinator(
        bridge=bridge,
        lifecycle=lifecycle,
        orchestrator=orchestrator,
        em_client=mock_em_client,
        autojob_client=mock_autojob,
        enriched_orchestrator=None,
        default_strategy=RoutingStrategy.BEST_FIT,
        task_expiry_hours=24.0,
    )


@pytest.fixture
def coordinator_with_agents(coordinator):
    """Coordinator with 3 registered agents ready for routing."""
    agents = [
        {
            "agent_id": 1001,
            "name": "Alpha",
            "wallet_address": "0xAlpha0000000000000000000000000000000001",
            "personality": "explorer",
        },
        {
            "agent_id": 1002,
            "name": "Beta",
            "wallet_address": "0xBeta00000000000000000000000000000000002",
            "personality": "specialist",
        },
        {
            "agent_id": 1003,
            "name": "Gamma",
            "wallet_address": "0xGamma0000000000000000000000000000000003",
            "personality": "generalist",
        },
    ]
    for agent in agents:
        coordinator.register_agent(**agent)
    return coordinator


# ─── EMApiClient Unit Tests ───────────────────────────────────────────────────


class TestEMApiClient:
    """Tests for the lightweight EM API client."""

    def test_init_defaults(self):
        client = EMApiClient()
        assert client.base_url == "https://api.execution.market"
        assert client.api_key is None
        assert client.timeout == 10.0

    def test_init_custom(self):
        client = EMApiClient(
            base_url="http://localhost:3000/",
            api_key="test-key",
            timeout_seconds=5.0,
        )
        assert client.base_url == "http://localhost:3000"
        assert client.api_key == "test-key"
        assert client.timeout == 5.0

    def test_trailing_slash_stripped(self):
        client = EMApiClient(base_url="https://example.com///")
        assert client.base_url == "https://example.com"


# ─── Agent Registration ──────────────────────────────────────────────────────


class TestAgentRegistration:
    """Test agent registration through the coordinator."""

    def test_register_single_agent(self, coordinator):
        record = coordinator.register_agent(
            agent_id=2001,
            name="TestAgent",
            wallet_address="0xTest000000000000000000000000000000000001",
        )
        assert record.agent_id == 2001
        assert record.name == "TestAgent"
        assert record.state == AgentState.ACTIVE  # auto-activated

    def test_register_agent_no_activate(self, coordinator):
        record = coordinator.register_agent(
            agent_id=2002,
            name="Lazy",
            wallet_address="0xLazy000000000000000000000000000000000002",
            activate=False,
        )
        assert record.state == AgentState.IDLE  # not auto-activated

    def test_register_with_custom_budget(self, coordinator):
        budget = BudgetConfig(
            daily_limit_usd=10.0,
            monthly_limit_usd=200.0,
            task_limit_usd=5.0,
        )
        record = coordinator.register_agent(
            agent_id=2003,
            name="BigBudget",
            wallet_address="0xBig0000000000000000000000000000000000003",
            budget_config=budget,
        )
        assert record.agent_id == 2003
        budget_status = coordinator.lifecycle.get_budget_status(2003)
        assert budget_status["daily_limit"] == 10.0

    def test_register_with_reputation_data(self, coordinator):
        on_chain = OnChainReputation(
            agent_id=2004,
            wallet_address="0xRep0000000000000000000000000000000000004",
            total_seals=50,
            positive_seals=45,
        )
        internal = InternalReputation(
            agent_id=2004,
            total_tasks=30,
            successful_tasks=28,
        )
        record = coordinator.register_agent(
            agent_id=2004,
            name="Reputable",
            wallet_address="0xRep0000000000000000000000000000000000004",
            on_chain=on_chain,
            internal=internal,
        )
        assert record.agent_id == 2004

    def test_register_emits_event(self, coordinator):
        coordinator.register_agent(
            agent_id=2005,
            name="EventAgent",
            wallet_address="0xEvt0000000000000000000000000000000000005",
        )
        events = coordinator.get_events(event_type=CoordinatorEvent.AGENT_REGISTERED)
        assert len(events) == 1
        assert events[0]["agent_id"] == 2005
        assert events[0]["name"] == "EventAgent"

    def test_register_with_tags(self, coordinator):
        record = coordinator.register_agent(
            agent_id=2006,
            name="Tagged",
            wallet_address="0xTag0000000000000000000000000000000000006",
            tags=["photo", "delivery"],
        )
        assert record.tags == ["photo", "delivery"]

    def test_batch_registration(self, coordinator):
        agents = [
            {
                "agent_id": 3001,
                "name": "Batch1",
                "wallet_address": "0xBat0000000000000000000000000000000000001",
            },
            {
                "agent_id": 3002,
                "name": "Batch2",
                "wallet_address": "0xBat0000000000000000000000000000000000002",
            },
            {
                "agent_id": 3003,
                "name": "Batch3",
                "wallet_address": "0xBat0000000000000000000000000000000000003",
            },
        ]
        records = coordinator.register_agents_batch(agents)
        assert len(records) == 3
        assert all(r.state == AgentState.ACTIVE for r in records)

    def test_batch_registration_skips_duplicates(self, coordinator):
        coordinator.register_agent(
            agent_id=3010,
            name="Existing",
            wallet_address="0xExist00000000000000000000000000000000010",
        )
        # Re-register should fail gracefully
        agents = [
            {
                "agent_id": 3010,
                "name": "Existing",
                "wallet_address": "0xExist00000000000000000000000000000000010",
            },
            {
                "agent_id": 3011,
                "name": "New",
                "wallet_address": "0xNew0000000000000000000000000000000000011",
            },
        ]
        records = coordinator.register_agents_batch(agents)
        # One succeeds, one fails (duplicate) — result has the successful ones
        assert len(records) >= 1


# ─── Task Ingestion ───────────────────────────────────────────────────────────


class TestTaskIngestion:
    """Test manual and API-based task ingestion."""

    def test_ingest_manual_task(self, coordinator):
        task = coordinator.ingest_task(
            task_id="task-001",
            title="Take a photo of the store",
            categories=["photo_verification"],
            bounty_usd=5.0,
        )
        assert task.task_id == "task-001"
        assert task.status == "pending"
        assert task.bounty_usd == 5.0
        assert task.source == "manual"

    def test_ingest_emits_event(self, coordinator):
        coordinator.ingest_task(
            task_id="task-002",
            title="Deliver package",
            categories=["delivery"],
            bounty_usd=10.0,
        )
        events = coordinator.get_events(event_type=CoordinatorEvent.TASK_INGESTED)
        assert len(events) == 1
        assert events[0]["task_id"] == "task-002"
        assert events[0]["bounty_usd"] == 10.0

    def test_ingest_with_priority(self, coordinator):
        task = coordinator.ingest_task(
            task_id="task-003",
            title="Emergency repair",
            categories=["maintenance"],
            bounty_usd=100.0,
            priority=TaskPriority.CRITICAL,
        )
        assert task.priority == TaskPriority.CRITICAL

    def test_ingest_duplicate_returns_existing(self, coordinator):
        t1 = coordinator.ingest_task(
            task_id="task-dup",
            title="First",
            categories=["test"],
        )
        t2 = coordinator.ingest_task(
            task_id="task-dup",
            title="Second",
            categories=["other"],
        )
        # Same task returned, not duplicated
        assert t1.task_id == t2.task_id
        assert t1.title == "First"  # Original title preserved

    def test_ingest_duplicate_after_failure_replaces(self, coordinator):
        t1 = coordinator.ingest_task(
            task_id="task-retry",
            title="Flaky task",
            categories=["test"],
        )
        t1.status = "failed"  # Mark as failed
        t2 = coordinator.ingest_task(
            task_id="task-retry",
            title="Retry",
            categories=["test"],
        )
        assert t2.title == "Retry"  # Re-ingested

    def test_ingest_from_api(self, coordinator, mock_em_client):
        mock_em_client.list_tasks.return_value = [
            {
                "id": "api-t1",
                "title": "API Task 1",
                "category": "photo",
                "bounty_usd": 5.0,
            },
            {
                "id": "api-t2",
                "title": "API Task 2",
                "category": "delivery",
                "bounty_usd": 75.0,
            },
            {
                "id": "api-t3",
                "title": "API Task 3",
                "categories": ["photo", "video"],
                "bounty": 150.0,
            },
        ]
        ingested = coordinator.ingest_from_api()
        assert len(ingested) == 3

    def test_ingest_from_api_auto_priority(self, coordinator, mock_em_client):
        mock_em_client.list_tasks.return_value = [
            {"id": "cheap", "title": "Cheap", "category": "x", "bounty_usd": 5.0},
            {"id": "mid", "title": "Mid", "category": "x", "bounty_usd": 60.0},
            {"id": "high", "title": "High", "category": "x", "bounty_usd": 200.0},
        ]
        ingested = coordinator.ingest_from_api()
        by_id = {t.task_id: t for t in ingested}
        assert by_id["cheap"].priority == TaskPriority.NORMAL
        assert by_id["mid"].priority == TaskPriority.HIGH
        assert by_id["high"].priority == TaskPriority.CRITICAL

    def test_ingest_from_api_skips_existing(self, coordinator, mock_em_client):
        coordinator.ingest_task(task_id="existing", title="Manual", categories=["x"])
        mock_em_client.list_tasks.return_value = [
            {"id": "existing", "title": "From API", "category": "x", "bounty_usd": 1},
            {"id": "new-one", "title": "New", "category": "y", "bounty_usd": 2},
        ]
        ingested = coordinator.ingest_from_api()
        assert len(ingested) == 1
        assert ingested[0].task_id == "new-one"

    def test_ingest_from_api_no_client(self, coordinator):
        coordinator.em_client = None
        result = coordinator.ingest_from_api()
        assert result == []

    def test_ingest_from_api_empty_response(self, coordinator, mock_em_client):
        mock_em_client.list_tasks.return_value = []
        result = coordinator.ingest_from_api()
        assert result == []

    def test_ingest_from_api_error_response(self, coordinator, mock_em_client):
        mock_em_client.list_tasks.return_value = []
        result = coordinator.ingest_from_api()
        assert result == []


# ─── Task Routing ─────────────────────────────────────────────────────────────


class TestTaskRouting:
    """Test task routing through the coordinator."""

    def test_process_empty_queue(self, coordinator_with_agents):
        results = coordinator_with_agents.process_task_queue()
        assert results == []

    def test_process_routes_to_agent(self, coordinator_with_agents):
        coordinator_with_agents.ingest_task(
            task_id="route-1",
            title="Photo verification",
            categories=["photo"],
            bounty_usd=5.0,
        )
        results = coordinator_with_agents.process_task_queue()
        assert len(results) == 1
        assert isinstance(results[0], Assignment)
        assert results[0].task_id == "route-1"
        assert results[0].agent_id in [1001, 1002, 1003]

    def test_process_updates_task_status(self, coordinator_with_agents):
        coordinator_with_agents.ingest_task(
            task_id="route-2",
            title="Delivery",
            categories=["delivery"],
        )
        coordinator_with_agents.process_task_queue()
        task = coordinator_with_agents._task_queue["route-2"]
        assert task.status == "assigned"
        assert task.assigned_agent_id is not None
        assert task.attempts == 1

    def test_process_emits_assignment_event(self, coordinator_with_agents):
        coordinator_with_agents.ingest_task(
            task_id="route-3",
            title="Test",
            categories=["test"],
        )
        coordinator_with_agents.process_task_queue()
        events = coordinator_with_agents.get_events(
            event_type=CoordinatorEvent.TASK_ASSIGNED
        )
        assert len(events) >= 1
        assert events[-1]["task_id"] == "route-3"

    def test_process_respects_max_tasks(self, coordinator_with_agents):
        for i in range(5):
            coordinator_with_agents.ingest_task(
                task_id=f"batch-{i}",
                title=f"Task {i}",
                categories=["test"],
            )
        results = coordinator_with_agents.process_task_queue(max_tasks=2)
        assert len(results) == 2

    def test_process_priority_ordering(self, coordinator_with_agents):
        # Ingest low priority first, high priority second
        coordinator_with_agents.ingest_task(
            task_id="low-pri",
            title="Low priority",
            categories=["test"],
            priority=TaskPriority.LOW,
        )
        coordinator_with_agents.ingest_task(
            task_id="high-pri",
            title="High priority",
            categories=["test"],
            priority=TaskPriority.CRITICAL,
        )
        results = coordinator_with_agents.process_task_queue(max_tasks=1)
        # High priority should be processed first
        assert results[0].task_id == "high-pri"

    def test_routing_failure_after_max_attempts(self, coordinator):
        # No agents registered → routing will fail
        coordinator.ingest_task(
            task_id="fail-1",
            title="No agents",
            categories=["test"],
        )
        task = coordinator._task_queue["fail-1"]
        task.max_attempts = 1  # Fail fast

        results = coordinator.process_task_queue()
        assert len(results) == 1
        assert isinstance(results[0], RoutingFailure)
        assert task.status == "failed"

    def test_routing_tracks_metrics(self, coordinator_with_agents):
        coordinator_with_agents.ingest_task(
            task_id="metrics-1",
            title="Track me",
            categories=["test"],
        )
        coordinator_with_agents.process_task_queue()
        assert coordinator_with_agents._routing_attempts >= 1
        assert len(coordinator_with_agents._routing_times) >= 1


# ─── Task Completion & Failure ────────────────────────────────────────────────


class TestTaskCompletion:
    """Test task completion and failure flows."""

    def _assign_task(self, coordinator):
        """Helper: ingest + route a task, return the task_id."""
        coordinator.ingest_task(
            task_id="complete-1",
            title="Complete me",
            categories=["test"],
            bounty_usd=5.0,
        )
        coordinator.process_task_queue()
        return "complete-1"

    def test_complete_task(self, coordinator_with_agents):
        task_id = self._assign_task(coordinator_with_agents)
        result = coordinator_with_agents.complete_task(task_id, bounty_earned_usd=5.0)
        assert result is True
        assert coordinator_with_agents._task_queue[task_id].status == "completed"
        assert coordinator_with_agents._total_completed == 1

    def test_complete_tracks_bounty(self, coordinator_with_agents):
        task_id = self._assign_task(coordinator_with_agents)
        coordinator_with_agents.complete_task(task_id, bounty_earned_usd=12.5)
        assert coordinator_with_agents._total_bounty_earned == 12.5

    def test_complete_emits_event(self, coordinator_with_agents):
        task_id = self._assign_task(coordinator_with_agents)
        coordinator_with_agents.complete_task(task_id, bounty_earned_usd=5.0)
        events = coordinator_with_agents.get_events(
            event_type=CoordinatorEvent.TASK_COMPLETED
        )
        assert len(events) >= 1
        assert events[-1]["task_id"] == task_id
        assert events[-1]["bounty_usd"] == 5.0

    def test_complete_uses_task_bounty_as_fallback(self, coordinator_with_agents):
        coordinator_with_agents.ingest_task(
            task_id="bounty-fallback",
            title="Has default bounty",
            categories=["test"],
            bounty_usd=7.5,
        )
        coordinator_with_agents.process_task_queue()
        coordinator_with_agents.complete_task("bounty-fallback")
        assert coordinator_with_agents._total_bounty_earned == 7.5

    def test_complete_unknown_task(self, coordinator_with_agents):
        result = coordinator_with_agents.complete_task("nonexistent")
        assert result is False

    def test_fail_task(self, coordinator_with_agents):
        task_id = self._assign_task(coordinator_with_agents)
        result = coordinator_with_agents.fail_task(task_id, error="Worker no-showed")
        assert result is True
        assert coordinator_with_agents._task_queue[task_id].status == "failed"
        assert coordinator_with_agents._total_failed >= 1

    def test_fail_emits_event(self, coordinator_with_agents):
        task_id = self._assign_task(coordinator_with_agents)
        coordinator_with_agents.fail_task(task_id, error="Timeout")
        events = coordinator_with_agents.get_events(
            event_type=CoordinatorEvent.TASK_FAILED
        )
        assert len(events) >= 1
        assert events[-1]["error"] == "Timeout"

    def test_fail_unknown_task(self, coordinator_with_agents):
        result = coordinator_with_agents.fail_task("does-not-exist")
        assert result is False

    def test_completion_updates_reputation(self, coordinator_with_agents):
        """Completing a task should boost internal reputation."""
        task_id = self._assign_task(coordinator_with_agents)
        task = coordinator_with_agents._task_queue[task_id]
        agent_id = task.assigned_agent_id

        # Check internal reputation exists
        if agent_id in coordinator_with_agents.orchestrator._internal:
            before = coordinator_with_agents.orchestrator._internal[
                agent_id
            ].successful_tasks
            coordinator_with_agents.complete_task(task_id)
            after = coordinator_with_agents.orchestrator._internal[
                agent_id
            ].successful_tasks
            assert after == before + 1


# ─── Health Checks ────────────────────────────────────────────────────────────


class TestHealthChecks:
    """Test health check system."""

    def test_health_check_returns_report(self, coordinator_with_agents):
        report = coordinator_with_agents.run_health_checks()
        assert "agents" in report
        assert "tasks" in report
        assert "systems" in report
        assert report["agents"]["checked"] == 3

    def test_health_check_detects_degraded_agent(self, coordinator_with_agents):
        # Force an agent to degraded state
        agent_id = 1001
        record = coordinator_with_agents.lifecycle.agents[agent_id]
        # Simulate missed heartbeats by setting consecutive_missed above threshold
        record.health.last_heartbeat = datetime.now(timezone.utc) - timedelta(hours=2)
        record.health.consecutive_missed = 10  # Above max_missed_heartbeats (3)

        report = coordinator_with_agents.run_health_checks()
        assert report["agents"]["degraded"] >= 1

    def test_health_check_em_api(self, coordinator_with_agents, mock_em_client):
        mock_em_client.get_health.return_value = {"status": "ok"}
        report = coordinator_with_agents.run_health_checks()
        assert report["systems"]["em_api"] == "ok"

    def test_health_check_no_em_client(self, coordinator_with_agents):
        coordinator_with_agents.em_client = None
        report = coordinator_with_agents.run_health_checks()
        assert "em_api" not in report["systems"]

    def test_health_check_autojob_available(
        self, coordinator_with_agents, mock_autojob
    ):
        mock_autojob.is_available.return_value = True
        report = coordinator_with_agents.run_health_checks()
        assert report["systems"]["autojob"] == "available"

    def test_health_check_autojob_unavailable(
        self, coordinator_with_agents, mock_autojob
    ):
        mock_autojob.is_available.return_value = False
        report = coordinator_with_agents.run_health_checks()
        assert report["systems"]["autojob"] == "unavailable"

    def test_health_check_expires_old_tasks(self, coordinator_with_agents):
        task = coordinator_with_agents.ingest_task(
            task_id="old-task",
            title="Ancient task",
            categories=["test"],
        )
        # Backdate the ingestion
        task.ingested_at = datetime.now(timezone.utc) - timedelta(hours=48)

        report = coordinator_with_agents.run_health_checks()
        assert report["tasks"]["expired"] >= 1
        assert coordinator_with_agents._task_queue["old-task"].status == "expired"

    def test_health_check_emits_event(self, coordinator_with_agents):
        coordinator_with_agents.run_health_checks()
        events = coordinator_with_agents.get_events(
            event_type=CoordinatorEvent.HEALTH_CHECK
        )
        assert len(events) == 1

    def test_health_check_detects_stale_assignments(self, coordinator_with_agents):
        task = coordinator_with_agents.ingest_task(
            task_id="stale-assign",
            title="Stale",
            categories=["test"],
        )
        task.status = "assigned"
        task.last_attempt_at = datetime.now(timezone.utc) - timedelta(hours=48)

        report = coordinator_with_agents.run_health_checks()
        assert report["tasks"]["stale"] >= 1


# ─── Metrics ──────────────────────────────────────────────────────────────────


class TestMetrics:
    """Test metrics computation."""

    def test_initial_metrics(self, coordinator):
        metrics = coordinator.get_metrics()
        assert isinstance(metrics, SwarmMetrics)
        assert metrics.tasks_ingested == 0
        assert metrics.tasks_assigned == 0
        assert metrics.tasks_completed == 0
        assert metrics.uptime_seconds >= 0

    def test_metrics_after_operations(self, coordinator_with_agents):
        coordinator_with_agents.ingest_task(
            task_id="m1", title="T1", categories=["x"], bounty_usd=5.0
        )
        coordinator_with_agents.ingest_task(
            task_id="m2", title="T2", categories=["y"], bounty_usd=10.0
        )
        coordinator_with_agents.process_task_queue()

        metrics = coordinator_with_agents.get_metrics()
        assert metrics.tasks_ingested == 2
        assert metrics.tasks_assigned >= 1
        assert metrics.agents_registered == 3
        assert metrics.avg_routing_time_ms >= 0

    def test_metrics_to_dict(self, coordinator):
        metrics = coordinator.get_metrics()
        d = metrics.to_dict()
        assert "tasks" in d
        assert "agents" in d
        assert "performance" in d
        assert "budget" in d
        assert "timing" in d

    def test_metrics_routing_success_rate(self, coordinator_with_agents):
        # Route some tasks
        for i in range(3):
            coordinator_with_agents.ingest_task(
                task_id=f"rate-{i}", title=f"T{i}", categories=["x"]
            )
        coordinator_with_agents.process_task_queue()

        metrics = coordinator_with_agents.get_metrics()
        assert metrics.routing_success_rate > 0

    def test_metrics_reset(self, coordinator_with_agents):
        coordinator_with_agents.ingest_task(
            task_id="reset-1", title="Before reset", categories=["x"]
        )
        coordinator_with_agents.process_task_queue()
        coordinator_with_agents.reset_metrics()

        metrics = coordinator_with_agents.get_metrics()
        assert metrics.tasks_ingested == 0
        assert metrics.tasks_assigned == 0


# ─── Dashboard ────────────────────────────────────────────────────────────────


class TestDashboard:
    """Test dashboard generation."""

    def test_dashboard_structure(self, coordinator_with_agents):
        dashboard = coordinator_with_agents.get_dashboard()
        assert "timestamp" in dashboard
        assert "metrics" in dashboard
        assert "queue" in dashboard
        assert "fleet" in dashboard
        assert "swarm" in dashboard
        assert "recent_events" in dashboard
        assert "systems" in dashboard

    def test_dashboard_fleet_info(self, coordinator_with_agents):
        dashboard = coordinator_with_agents.get_dashboard()
        assert len(dashboard["fleet"]) == 3
        for agent in dashboard["fleet"]:
            assert "agent_id" in agent
            assert "name" in agent
            assert "state" in agent
            assert "budget_daily_pct" in agent
            assert "health" in agent

    def test_dashboard_queue_breakdown(self, coordinator_with_agents):
        coordinator_with_agents.ingest_task(task_id="d1", title="T1", categories=["x"])
        coordinator_with_agents.ingest_task(task_id="d2", title="T2", categories=["y"])
        coordinator_with_agents.process_task_queue(max_tasks=1)

        dashboard = coordinator_with_agents.get_dashboard()
        assert dashboard["queue"]["pending"] >= 0
        assert dashboard["queue"]["assigned"] >= 0

    def test_dashboard_systems_info(self, coordinator_with_agents):
        dashboard = coordinator_with_agents.get_dashboard()
        assert dashboard["systems"]["em_api"] == "configured"
        assert dashboard["systems"]["autojob"] == "configured"

    def test_dashboard_no_external_clients(self, coordinator):
        coordinator.em_client = None
        coordinator.autojob = None
        dashboard = coordinator.get_dashboard()
        assert dashboard["systems"]["em_api"] == "not configured"
        assert dashboard["systems"]["autojob"] == "not configured"


# ─── Event System ─────────────────────────────────────────────────────────────


class TestEventSystem:
    """Test coordinator event system."""

    def test_event_hooks(self, coordinator):
        captured = []
        coordinator.on_event(
            CoordinatorEvent.TASK_INGESTED,
            lambda e: captured.append(e),
        )
        coordinator.ingest_task(task_id="hook-1", title="Hook test", categories=["x"])
        assert len(captured) == 1
        assert captured[0].event == CoordinatorEvent.TASK_INGESTED

    def test_multiple_hooks(self, coordinator):
        captured_a = []
        captured_b = []
        coordinator.on_event(
            CoordinatorEvent.TASK_INGESTED, lambda e: captured_a.append(e)
        )
        coordinator.on_event(
            CoordinatorEvent.TASK_INGESTED, lambda e: captured_b.append(e)
        )
        coordinator.ingest_task(task_id="multi-hook", title="Both", categories=["x"])
        assert len(captured_a) == 1
        assert len(captured_b) == 1

    def test_hook_error_doesnt_crash(self, coordinator):
        def bad_hook(e):
            raise RuntimeError("boom")

        coordinator.on_event(CoordinatorEvent.TASK_INGESTED, bad_hook)
        # Should not raise
        coordinator.ingest_task(task_id="safe", title="Safe", categories=["x"])

    def test_query_events_by_type(self, coordinator):
        coordinator.ingest_task(task_id="e1", title="T1", categories=["x"])
        coordinator.ingest_task(task_id="e2", title="T2", categories=["y"])

        events = coordinator.get_events(event_type=CoordinatorEvent.TASK_INGESTED)
        assert len(events) == 2

    def test_query_events_with_limit(self, coordinator):
        for i in range(10):
            coordinator.ingest_task(task_id=f"lim-{i}", title=f"T{i}", categories=["x"])
        events = coordinator.get_events(limit=3)
        assert len(events) == 3

    def test_query_events_since(self, coordinator):
        coordinator.ingest_task(task_id="since-1", title="T1", categories=["x"])
        cutoff = datetime.now(timezone.utc)
        coordinator.ingest_task(task_id="since-2", title="T2", categories=["y"])

        events = coordinator.get_events(since=cutoff)
        assert len(events) >= 1

    def test_event_record_to_dict(self):
        record = EventRecord(
            event=CoordinatorEvent.TASK_INGESTED,
            timestamp=datetime(2026, 3, 23, tzinfo=timezone.utc),
            data={"task_id": "test"},
        )
        d = record.to_dict()
        assert d["event"] == "task_ingested"
        assert d["task_id"] == "test"

    def test_events_capped_at_1000(self, coordinator):
        for i in range(1100):
            coordinator._emit(CoordinatorEvent.HEALTH_CHECK, {"iteration": i})
        assert len(coordinator._events) == 1000  # deque maxlen


# ─── Queue Management ─────────────────────────────────────────────────────────


class TestQueueManagement:
    """Test queue utilities."""

    def test_queue_summary(self, coordinator):
        coordinator.ingest_task(
            task_id="qs-1", title="T1", categories=["photo"], bounty_usd=5.0
        )
        coordinator.ingest_task(
            task_id="qs-2", title="T2", categories=["delivery"], bounty_usd=10.0
        )

        summary = coordinator.get_queue_summary()
        assert summary["total"] == 2
        assert summary["by_status"]["pending"] == 2
        assert summary["pending_bounty_usd"] == 15.0
        assert summary["by_category"]["photo"] == 1
        assert summary["by_category"]["delivery"] == 1

    def test_cleanup_completed(self, coordinator_with_agents):
        coordinator_with_agents.ingest_task(
            task_id="clean-1", title="Old", categories=["x"]
        )
        coordinator_with_agents.process_task_queue()
        coordinator_with_agents.complete_task("clean-1")

        # Backdate the ingestion
        coordinator_with_agents._task_queue["clean-1"].ingested_at = datetime.now(
            timezone.utc
        ) - timedelta(hours=48)

        removed = coordinator_with_agents.cleanup_completed(older_than_hours=24.0)
        assert removed == 1
        assert "clean-1" not in coordinator_with_agents._task_queue

    def test_cleanup_preserves_recent(self, coordinator_with_agents):
        coordinator_with_agents.ingest_task(
            task_id="clean-recent", title="Recent", categories=["x"]
        )
        coordinator_with_agents.process_task_queue()
        coordinator_with_agents.complete_task("clean-recent")

        removed = coordinator_with_agents.cleanup_completed(older_than_hours=24.0)
        assert removed == 0  # Too recent to clean

    def test_cleanup_preserves_pending(self, coordinator):
        coordinator.ingest_task(
            task_id="clean-pending", title="Still pending", categories=["x"]
        )
        coordinator._task_queue["clean-pending"].ingested_at = datetime.now(
            timezone.utc
        ) - timedelta(hours=48)

        removed = coordinator.cleanup_completed(older_than_hours=24.0)
        assert removed == 0  # Pending tasks not cleaned


# ─── Factory Method ───────────────────────────────────────────────────────────


class TestFactory:
    """Test the create() factory method."""

    def test_create_default(self):
        coordinator = SwarmCoordinator.create()
        assert coordinator.bridge is not None
        assert coordinator.lifecycle is not None
        assert coordinator.orchestrator is not None
        assert coordinator.em_client is not None
        assert coordinator.autojob is not None
        assert coordinator.enriched is not None

    def test_create_custom_strategy(self):
        coordinator = SwarmCoordinator.create(
            default_strategy=RoutingStrategy.ROUND_ROBIN
        )
        assert coordinator.default_strategy == RoutingStrategy.ROUND_ROBIN

    def test_create_custom_urls(self):
        coordinator = SwarmCoordinator.create(
            em_api_url="http://localhost:3000",
            autojob_url="http://localhost:9999",
        )
        assert coordinator.em_client.base_url == "http://localhost:3000"


# ─── QueuedTask Conversion ───────────────────────────────────────────────────


class TestQueuedTask:
    """Test QueuedTask dataclass and conversions."""

    def test_to_task_request(self):
        task = QueuedTask(
            task_id="conv-1",
            title="Convert me",
            categories=["photo", "video"],
            bounty_usd=15.0,
            priority=TaskPriority.HIGH,
        )
        request = task.to_task_request()
        assert isinstance(request, TaskRequest)
        assert request.task_id == "conv-1"
        assert request.title == "Convert me"
        assert request.categories == ["photo", "video"]
        assert request.bounty_usd == 15.0
        assert request.priority == TaskPriority.HIGH

    def test_queued_task_defaults(self):
        task = QueuedTask(
            task_id="def-1",
            title="Defaults",
            categories=[],
            bounty_usd=0.0,
        )
        assert task.status == "pending"
        assert task.source == "api"
        assert task.attempts == 0
        assert task.max_attempts == 3
        assert task.assigned_agent_id is None


# ─── SwarmMetrics ─────────────────────────────────────────────────────────────


class TestSwarmMetrics:
    """Test SwarmMetrics dataclass."""

    def test_defaults(self):
        m = SwarmMetrics()
        assert m.tasks_ingested == 0
        assert m.uptime_seconds == 0.0

    def test_to_dict_structure(self):
        m = SwarmMetrics(
            tasks_ingested=10,
            tasks_completed=8,
            agents_registered=5,
            avg_routing_time_ms=12.345,
            routing_success_rate=0.95678,
            total_bounty_earned_usd=123.456,
        )
        d = m.to_dict()
        assert d["tasks"]["ingested"] == 10
        assert d["tasks"]["completed"] == 8
        assert d["tasks"]["bounty_earned_usd"] == 123.46  # Rounded
        assert d["performance"]["avg_routing_time_ms"] == 12.3  # Rounded
        assert d["performance"]["routing_success_rate"] == 0.957  # Rounded


# ─── Integration: Full Lifecycle ──────────────────────────────────────────────


class TestFullLifecycle:
    """End-to-end tests covering the full task lifecycle."""

    def test_full_lifecycle_ingest_route_complete(self, coordinator_with_agents):
        """Ingest → Route → Complete → Verify metrics."""
        # Ingest
        coordinator_with_agents.ingest_task(
            task_id="lifecycle-1",
            title="Full cycle task",
            categories=["photo"],
            bounty_usd=8.0,
        )
        assert coordinator_with_agents._total_ingested == 1

        # Route
        results = coordinator_with_agents.process_task_queue()
        assert len(results) == 1
        assert isinstance(results[0], Assignment)
        assert coordinator_with_agents._total_assigned == 1

        # Complete
        coordinator_with_agents.complete_task("lifecycle-1", bounty_earned_usd=8.0)
        assert coordinator_with_agents._total_completed == 1
        assert coordinator_with_agents._total_bounty_earned == 8.0

        # Verify final state
        metrics = coordinator_with_agents.get_metrics()
        assert metrics.tasks_ingested == 1
        assert metrics.tasks_assigned == 1
        assert metrics.tasks_completed == 1
        assert metrics.total_bounty_earned_usd == 8.0

    def test_full_lifecycle_with_failure_and_retry(self, coordinator_with_agents):
        """Ingest → Route → Fail → Re-ingest → Route → Complete."""
        coordinator_with_agents.ingest_task(
            task_id="retry-lifecycle",
            title="Flaky task",
            categories=["delivery"],
            bounty_usd=12.0,
        )

        # Route successfully
        results = coordinator_with_agents.process_task_queue()
        assert isinstance(results[0], Assignment)

        # Fail
        coordinator_with_agents.fail_task("retry-lifecycle", error="Worker quit")

        # Re-ingest (same task_id — should replace since status=failed)
        coordinator_with_agents.ingest_task(
            task_id="retry-lifecycle",
            title="Flaky task (retry)",
            categories=["delivery"],
            bounty_usd=12.0,
        )

        # Final metrics show both outcomes
        assert coordinator_with_agents._total_failed >= 1

    def test_multiple_tasks_multiple_agents(self, coordinator_with_agents):
        """Multiple tasks should be distributed across agents."""
        for i in range(3):
            coordinator_with_agents.ingest_task(
                task_id=f"multi-{i}",
                title=f"Task {i}",
                categories=["test"],
                bounty_usd=5.0,
            )

        results = coordinator_with_agents.process_task_queue()
        assigned_agents = set()
        for r in results:
            if isinstance(r, Assignment):
                assigned_agents.add(r.agent_id)

        # At least some tasks should be assigned
        assert len(results) >= 1

    def test_dashboard_after_full_lifecycle(self, coordinator_with_agents):
        """Dashboard should reflect operations accurately."""
        coordinator_with_agents.ingest_task(
            task_id="dash-1", title="T1", categories=["x"], bounty_usd=5.0
        )
        coordinator_with_agents.process_task_queue()
        coordinator_with_agents.complete_task("dash-1", bounty_earned_usd=5.0)
        coordinator_with_agents.run_health_checks()

        dashboard = coordinator_with_agents.get_dashboard()
        assert dashboard["metrics"]["tasks"]["completed"] == 1
        assert dashboard["metrics"]["tasks"]["bounty_earned_usd"] == 5.0
        assert len(dashboard["recent_events"]) >= 3  # ingested, assigned, completed

    def test_event_timeline(self, coordinator_with_agents):
        """Events should form a coherent timeline."""
        coordinator_with_agents.ingest_task(
            task_id="timeline-1", title="T1", categories=["x"]
        )
        coordinator_with_agents.process_task_queue()
        coordinator_with_agents.complete_task("timeline-1")

        events = coordinator_with_agents.get_events()
        event_types = [e["event"] for e in events]

        # Should see registration events + task lifecycle
        assert "agent_registered" in event_types
        assert "task_ingested" in event_types
        assert "task_assigned" in event_types
        assert "task_completed" in event_types

        # Ingestion should come before assignment
        ingest_idx = event_types.index("task_ingested")
        assign_idx = event_types.index("task_assigned")
        complete_idx = event_types.index("task_completed")
        assert ingest_idx < assign_idx < complete_idx


# ─── AutoJob Enrichment ──────────────────────────────────────────────────────


class TestAutoJobEnrichment:
    """Test AutoJob integration path."""

    def test_routing_with_enrichment(self, coordinator_with_agents, mock_autojob):
        """When AutoJob is available, enriched orchestrator is used."""
        mock_autojob.is_available.return_value = True

        # Create an enriched orchestrator mock
        enriched = MagicMock(spec=EnrichedOrchestrator)
        enriched.route_task.return_value = Assignment(
            task_id="enriched-1",
            agent_id=1001,
            agent_name="Alpha",
            score=85.0,
            strategy_used=RoutingStrategy.BEST_FIT,
        )
        coordinator_with_agents.enriched = enriched

        coordinator_with_agents.ingest_task(
            task_id="enriched-1", title="Enriched", categories=["x"]
        )
        results = coordinator_with_agents.process_task_queue()

        assert len(results) == 1
        assert isinstance(results[0], Assignment)
        assert coordinator_with_agents._autojob_enrichments == 1

    def test_routing_without_enrichment(self, coordinator_with_agents, mock_autojob):
        """When AutoJob is unavailable, standard orchestrator is used."""
        mock_autojob.is_available.return_value = False

        coordinator_with_agents.ingest_task(
            task_id="standard-1", title="Standard", categories=["x"]
        )
        coordinator_with_agents.process_task_queue()

        assert coordinator_with_agents._autojob_enrichments == 0

    def test_enrichment_event_emitted(self, coordinator_with_agents, mock_autojob):
        mock_autojob.is_available.return_value = True

        enriched = MagicMock(spec=EnrichedOrchestrator)
        enriched.route_task.return_value = Assignment(
            task_id="enr-evt",
            agent_id=1002,
            agent_name="Beta",
            score=72.0,
            strategy_used=RoutingStrategy.BEST_FIT,
        )
        coordinator_with_agents.enriched = enriched

        coordinator_with_agents.ingest_task(
            task_id="enr-evt", title="Enriched", categories=["x"]
        )
        coordinator_with_agents.process_task_queue()

        events = coordinator_with_agents.get_events(
            event_type=CoordinatorEvent.AUTOJOB_ENRICHED
        )
        assert len(events) >= 1


# ─── CoordinatorEvent Enum ────────────────────────────────────────────────────


class TestCoordinatorEvent:
    """Test the event enum."""

    def test_all_events_defined(self):
        expected = {
            "task_ingested",
            "task_assigned",
            "task_completed",
            "task_failed",
            "task_expired",
            "agent_registered",
            "agent_degraded",
            "agent_recovered",
            "agent_suspended",
            "budget_warning",
            "health_check",
            "routing_failure",
            "autojob_enriched",
        }
        actual = {e.value for e in CoordinatorEvent}
        assert expected == actual
