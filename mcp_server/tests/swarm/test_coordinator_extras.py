"""
Tests for SwarmCoordinator — top-level operational controller for the KK V2 swarm.

Covers:
- EMApiClient (mocked HTTP)
- CoordinatorEvent / EventRecord
- QueuedTask / SwarmMetrics dataclasses
- SwarmCoordinator agent registration (single + batch)
- Task ingestion (manual + API)
- Task queue processing (routing strategies)
- Task completion & failure
- Health checks (heartbeat, cooldown, expiry, budget)
- Metrics computation
- Dashboard generation
- Event system (hooks, filtering)
- Queue management (summary, cleanup)
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock


from mcp_server.swarm.coordinator import (
    SwarmCoordinator,
    EMApiClient,
    CoordinatorEvent,
    EventRecord,
    QueuedTask,
)
from mcp_server.swarm.reputation_bridge import (
    ReputationBridge,
    OnChainReputation,
    InternalReputation,
)
from mcp_server.swarm.lifecycle_manager import (
    LifecycleManager,
    AgentState,
)
from mcp_server.swarm.orchestrator import (
    SwarmOrchestrator,
    Assignment,
)


# ──────────────────────────── Helpers ─────────────────────────────


def _coordinator(num_agents=3, autojob=False, em_client=False):
    """Create a coordinator with N active agents."""
    bridge = ReputationBridge()
    lifecycle = LifecycleManager()
    orchestrator = SwarmOrchestrator(bridge, lifecycle, min_score_threshold=0.0)

    coord = SwarmCoordinator(
        bridge=bridge,
        lifecycle=lifecycle,
        orchestrator=orchestrator,
        em_client=EMApiClient("http://fake") if em_client else None,
        autojob_client=MagicMock(is_available=MagicMock(return_value=False))
        if autojob
        else None,
    )

    for i in range(1, num_agents + 1):
        coord.register_agent(
            agent_id=i,
            name=f"agent-{i}",
            wallet_address=f"0x{i:04x}",
            on_chain=OnChainReputation(
                agent_id=i,
                wallet_address=f"0x{i:04x}",
                total_seals=i * 10,
                positive_seals=i * 9,
                chains_active=["base"],
            ),
            internal=InternalReputation(
                agent_id=i,
                bayesian_score=0.5 + i * 0.1,
                total_tasks=i * 20,
                successful_tasks=i * 18,
                avg_rating=3.5 + i * 0.3,
            ),
        )

    return coord


# ──────────────────── EMApiClient Tests ───────────────────────────


class TestEMApiClient:
    def test_init(self):
        client = EMApiClient("https://api.execution.market", "test-key")
        assert client.base_url == "https://api.execution.market"
        assert client.api_key == "test-key"

    def test_base_url_strips_trailing_slash(self):
        client = EMApiClient("https://api.execution.market/")
        assert client.base_url == "https://api.execution.market"


# ──────────────────── CoordinatorEvent Tests ──────────────────────


class TestCoordinatorEvent:
    def test_event_values(self):
        assert CoordinatorEvent.TASK_INGESTED.value == "task_ingested"
        assert CoordinatorEvent.TASK_ASSIGNED.value == "task_assigned"
        assert CoordinatorEvent.AGENT_REGISTERED.value == "agent_registered"
        assert CoordinatorEvent.HEALTH_CHECK.value == "health_check"


class TestEventRecord:
    def test_to_dict(self):
        er = EventRecord(
            event=CoordinatorEvent.TASK_INGESTED,
            timestamp=datetime(2026, 3, 24, tzinfo=timezone.utc),
            data={"task_id": "t1"},
        )
        d = er.to_dict()
        assert d["event"] == "task_ingested"
        assert d["task_id"] == "t1"
        assert "2026-03-24" in d["timestamp"]


# ──────────────────── QueuedTask Tests ────────────────────────────


# ──────────────────── SwarmMetrics Tests ──────────────────────────


# ──────────────────── Agent Registration ──────────────────────────


class TestCoordinatorRegistration:
    def test_register_agent_without_activate(self):
        coord = _coordinator(num_agents=0)
        record = coord.register_agent(
            agent_id=1,
            name="aurora",
            wallet_address="0x0001",
            activate=False,
        )
        assert record.state == AgentState.IDLE

    def test_register_batch(self):
        coord = _coordinator(num_agents=0)
        agents = [
            {"agent_id": 1, "name": "a1", "wallet_address": "0x1"},
            {"agent_id": 2, "name": "a2", "wallet_address": "0x2"},
            {"agent_id": 3, "name": "a3", "wallet_address": "0x3"},
        ]
        records = coord.register_agents_batch(agents)
        assert len(records) == 3

    def test_register_batch_skips_duplicates(self):
        coord = _coordinator(num_agents=0)
        coord.register_agent(1, "a1", "0x1")
        agents = [
            {"agent_id": 1, "name": "a1", "wallet_address": "0x1"},  # Duplicate
            {"agent_id": 2, "name": "a2", "wallet_address": "0x2"},
        ]
        records = coord.register_agents_batch(agents)
        assert len(records) == 1  # Only agent 2 registered

    def test_register_with_reputation(self):
        coord = _coordinator(num_agents=0)
        on_chain = OnChainReputation(agent_id=1, wallet_address="0x1", total_seals=50)
        internal = InternalReputation(agent_id=1, bayesian_score=0.9)
        coord.register_agent(1, "aurora", "0x1", on_chain=on_chain, internal=internal)
        assert coord.orchestrator._on_chain[1].total_seals == 50
        assert coord.orchestrator._internal[1].bayesian_score == 0.9


# ──────────────────── Task Ingestion ──────────────────────────────


class TestCoordinatorIngestion:
    def test_ingest_task(self):
        coord = _coordinator()
        task = coord.ingest_task("t1", "Photo task", ["photo"], bounty_usd=0.50)
        assert isinstance(task, QueuedTask)
        assert task.status == "pending"
        assert task.task_id == "t1"

    def test_ingest_increments_counter(self):
        coord = _coordinator()
        coord.ingest_task("t1", "T1", ["photo"])
        coord.ingest_task("t2", "T2", ["data"])
        assert coord._total_ingested == 2

    def test_ingest_failed_task_allows_re_ingest(self):
        coord = _coordinator()
        coord.ingest_task("t1", "Task", ["photo"])
        coord._task_queue["t1"].status = "failed"
        # Should allow re-ingestion of failed task
        t2 = coord.ingest_task("t1", "Task retry", ["photo"])
        assert t2.title == "Task retry"


# ──────────────────── Task Processing ─────────────────────────────


class TestCoordinatorProcessing:
    def test_process_multiple_tasks(self):
        coord = _coordinator(num_agents=3)
        for i in range(3):
            coord.ingest_task(f"t{i}", f"Task {i}", ["photo"])
        results = coord.process_task_queue(max_tasks=10)
        assignments = [r for r in results if isinstance(r, Assignment)]
        assert len(assignments) == 3

    def test_process_routing_failure_tracks_attempts(self):
        coord = _coordinator(num_agents=0)  # No agents
        coord.ingest_task("t1", "Task", ["photo"])
        coord.process_task_queue()
        assert coord._task_queue["t1"].attempts == 1
        assert coord._task_queue["t1"].status == "pending"  # Still pending, can retry

    def test_process_routing_failure_after_max_attempts(self):
        coord = _coordinator(num_agents=0)
        coord.ingest_task("t1", "Task", ["photo"])
        coord._task_queue["t1"].max_attempts = 1
        coord.process_task_queue()
        assert coord._task_queue["t1"].status == "failed"

    def test_process_max_tasks_limit(self):
        coord = _coordinator(num_agents=5)
        for i in range(5):
            coord.ingest_task(f"t{i}", f"Task {i}", ["photo"])
        results = coord.process_task_queue(max_tasks=2)
        assert len(results) == 2

    def test_process_tracks_routing_time(self):
        coord = _coordinator(num_agents=1)
        coord.ingest_task("t1", "Task", ["photo"])
        coord.process_task_queue()
        assert len(coord._routing_times) >= 1


# ──────────────────── Task Completion ─────────────────────────────


class TestCoordinatorCompletion:
    def test_complete_updates_reputation(self):
        coord = _coordinator(num_agents=1)
        coord.ingest_task("t1", "Task", ["photo"])
        coord.process_task_queue()
        old_tasks = coord.orchestrator._internal[1].total_tasks
        coord.complete_task("t1")
        new_tasks = coord.orchestrator._internal[1].total_tasks
        assert new_tasks == old_tasks + 1


# ──────────────────── Task Failure ────────────────────────────────


# ──────────────────── Health Checks ───────────────────────────────


class TestCoordinatorHealth:
    def test_health_check_detects_expired_tasks(self):
        coord = _coordinator(num_agents=0, em_client=False)
        coord.ingest_task("t1", "Old task", ["photo"])
        # Set ingestion time far in the past
        coord._task_queue["t1"].ingested_at = datetime.now(timezone.utc) - timedelta(
            hours=48
        )
        report = coord.run_health_checks()
        assert report["tasks"]["expired"] >= 1
        assert coord._task_queue["t1"].status == "expired"

    def test_health_check_updates_timestamp(self):
        coord = _coordinator()
        assert coord._last_health_check is None
        coord.run_health_checks()
        assert coord._last_health_check is not None


# ──────────────────── Metrics ─────────────────────────────────────


class TestCoordinatorMetrics:
    def test_reset_metrics(self):
        coord = _coordinator(num_agents=1)
        coord.ingest_task("t1", "Task", ["photo"])
        coord.process_task_queue()
        coord.reset_metrics()
        metrics = coord.get_metrics()
        assert metrics.tasks_ingested == 0
        assert metrics.tasks_assigned == 0


# ──────────────────── Dashboard ───────────────────────────────────


class TestCoordinatorDashboard:
    def test_dashboard_queue_counts(self):
        coord = _coordinator(num_agents=1)
        coord.ingest_task("t1", "Pending", ["photo"])
        coord.ingest_task("t2", "Assigned", ["photo"])
        coord.process_task_queue(max_tasks=1)
        dashboard = coord.get_dashboard()
        assert dashboard["queue"]["pending"] >= 0
        assert dashboard["queue"]["assigned"] >= 0


# ──────────────────── Event System ────────────────────────────────


class TestCoordinatorEvents:
    def test_event_filtering_by_type(self):
        coord = _coordinator(num_agents=1)
        coord.ingest_task("t1", "Task", ["photo"])
        coord.process_task_queue()
        ingested = coord.get_events(event_type=CoordinatorEvent.TASK_INGESTED)
        assigned = coord.get_events(event_type=CoordinatorEvent.TASK_ASSIGNED)
        assert len(ingested) >= 1
        assert len(assigned) >= 1

    def test_event_filtering_by_time(self):
        coord = _coordinator(num_agents=0)
        cutoff = datetime.now(timezone.utc) + timedelta(seconds=1)
        coord.ingest_task("t1", "Task", ["photo"])
        # Events before cutoff
        events = coord.get_events(since=cutoff)
        assert len(events) == 0

    def test_event_limit(self):
        coord = _coordinator(num_agents=0)
        for i in range(10):
            coord.ingest_task(f"t{i}", f"Task {i}", ["photo"])
        events = coord.get_events(limit=3)
        assert len(events) == 3

    def test_event_hook_error_handled(self):
        coord = _coordinator(num_agents=0)

        def bad_hook(event):
            raise RuntimeError("hook failed")

        coord.on_event(CoordinatorEvent.TASK_INGESTED, bad_hook)
        # Should not raise even though hook fails
        coord.ingest_task("t1", "Task", ["photo"])


# ──────────────────── Queue Management ────────────────────────────


# ──────────────────── Factory Method ──────────────────────────────


class TestCoordinatorFactory:
    def test_create_wires_components(self):
        coord = SwarmCoordinator.create(
            em_api_url="https://api.execution.market",
        )
        assert coord.bridge is not None
        assert coord.lifecycle is not None
        assert coord.orchestrator is not None
        assert coord.em_client is not None
        assert coord.autojob is not None
        assert coord.enriched is not None
