"""
Tests for EventListener — EM API polling and task lifecycle event processing.

Coverage targets:
    - Polling new tasks (ingestion, dedup, category mapping)
    - Polling completions (reputation, Skill DNA triggers)
    - Polling failures (cancelled, expired, disputed)
    - Full poll cycle (poll_once)
    - Watermark state (persistence, pruning, idempotency)
    - Category mapping (all EM categories)
    - Priority estimation
    - Continuous run mode (with max_polls)
    - Edge cases (API errors, malformed data, empty responses)
"""

import json
import os
import tempfile
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, call

import pytest

from mcp_server.swarm.event_listener import (
    EventListener,
    ListenerEvent,
    ListenerState,
    PollResult,
    map_categories,
    estimate_priority,
    EM_CATEGORY_MAP,
)
from mcp_server.swarm.coordinator import (
    SwarmCoordinator,
    EMApiClient,
    CoordinatorEvent,
)
from mcp_server.swarm.reputation_bridge import ReputationBridge
from mcp_server.swarm.lifecycle_manager import LifecycleManager, AgentState
from mcp_server.swarm.orchestrator import SwarmOrchestrator, TaskPriority


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_em_client():
    client = MagicMock(spec=EMApiClient)
    client.base_url = "https://api.execution.market"
    client.list_tasks.return_value = []
    client.get_health.return_value = {"status": "healthy"}
    return client


@pytest.fixture
def coordinator(mock_em_client):
    bridge = ReputationBridge()
    lifecycle = LifecycleManager()
    orchestrator = SwarmOrchestrator(bridge, lifecycle)
    coord = SwarmCoordinator(
        bridge=bridge,
        lifecycle=lifecycle,
        orchestrator=orchestrator,
        em_client=mock_em_client,
    )
    # Register an agent for routing
    coord.register_agent(agent_id=1, name="Test-Agent", wallet_address="0x" + "a1" * 20)
    return coord


@pytest.fixture
def listener(coordinator):
    return EventListener(coordinator)


@pytest.fixture
def listener_with_state():
    """Listener with file-backed state."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name

    bridge = ReputationBridge()
    lifecycle = LifecycleManager()
    orchestrator = SwarmOrchestrator(bridge, lifecycle)
    mock_client = MagicMock(spec=EMApiClient)
    mock_client.base_url = "https://test.api.com"
    mock_client.list_tasks.return_value = []
    mock_client.get_health.return_value = {"status": "healthy"}

    coord = SwarmCoordinator(
        bridge=bridge,
        lifecycle=lifecycle,
        orchestrator=orchestrator,
        em_client=mock_client,
    )
    coord.register_agent(agent_id=1, name="Test", wallet_address="0x" + "a1" * 20)
    lst = EventListener(coord, state_path=path)

    yield lst, path

    if os.path.exists(path):
        os.unlink(path)


# ─── Category Mapping Tests ──────────────────────────────────────────────────

class TestCategoryMapping:

    def test_map_physical_categories(self):
        for cat in ("delivery", "pickup", "errand", "cleaning", "moving", "handyman", "assembly"):
            mapped = map_categories(cat)
            assert "physical" in mapped, f"Expected 'physical' in mapping for {cat}"

    def test_map_digital_categories(self):
        for cat in ("data_entry", "research", "writing", "translation", "design", "coding", "testing"):
            mapped = map_categories(cat)
            assert "digital" in mapped, f"Expected 'digital' in mapping for {cat}"

    def test_map_verification_categories(self):
        for cat in ("photo_verification", "location_verification", "mystery_shopping"):
            mapped = map_categories(cat)
            assert "verification" in mapped, f"Expected 'verification' in mapping for {cat}"

    def test_map_blockchain_categories(self):
        for cat in ("blockchain", "defi", "nft"):
            mapped = map_categories(cat)
            assert "blockchain" in mapped, f"Expected 'blockchain' in mapping for {cat}"

    def test_map_unknown_category(self):
        mapped = map_categories("quantum_computing")
        assert "general" in mapped
        assert "quantum_computing" in mapped

    def test_map_none_category(self):
        mapped = map_categories(None)
        assert mapped == ["general", "misc"]

    def test_map_empty_string(self):
        mapped = map_categories("")
        assert mapped == ["general", "misc"]

    def test_map_case_insensitive(self):
        mapped = map_categories("DELIVERY")
        assert "physical" in mapped
        assert "delivery" in mapped

    def test_all_em_categories_have_mappings(self):
        for cat in EM_CATEGORY_MAP:
            mapped = map_categories(cat)
            assert len(mapped) >= 2, f"Category {cat} should map to at least 2 routing categories"


# ─── Priority Estimation Tests ────────────────────────────────────────────────

class TestPriorityEstimation:

    def test_high_bounty_priority(self):
        assert estimate_priority({"bounty_amount": 100}) == "HIGH"

    def test_medium_bounty_priority(self):
        assert estimate_priority({"bounty_amount": 25}) == "NORMAL"

    def test_low_bounty_priority(self):
        assert estimate_priority({"bounty_amount": 2}) == "LOW"

    def test_zero_bounty_priority(self):
        assert estimate_priority({"bounty_amount": 0}) == "NORMAL"

    def test_missing_bounty(self):
        assert estimate_priority({}) == "NORMAL"

    def test_none_bounty(self):
        assert estimate_priority({"bounty_amount": None}) == "NORMAL"

    def test_string_bounty(self):
        assert estimate_priority({"bounty_amount": "not_a_number"}) == "NORMAL"


# ─── Poll New Tasks Tests ────────────────────────────────────────────────────

class TestPollNewTasks:

    def test_poll_no_new_tasks(self, listener):
        listener.em_client.list_tasks.return_value = []
        ingested = listener.poll_new_tasks()
        assert ingested == []

    def test_poll_new_tasks_basic(self, listener):
        listener.em_client.list_tasks.return_value = [
            {"id": "t1", "title": "Task 1", "category": "delivery", "bounty_amount": 5.0},
            {"id": "t2", "title": "Task 2", "category": "coding", "bounty_amount": 10.0},
        ]
        ingested = listener.poll_new_tasks()
        assert len(ingested) == 2
        assert listener.state.total_new_tasks == 2

    def test_poll_deduplication(self, listener):
        listener.em_client.list_tasks.return_value = [
            {"id": "dup-1", "title": "Dup Task", "category": "delivery"},
        ]
        # First poll
        listener.poll_new_tasks()
        assert listener.state.total_new_tasks == 1
        # Second poll with same task
        listener.poll_new_tasks()
        assert listener.state.total_new_tasks == 1  # Not re-ingested

    def test_poll_marks_seen(self, listener):
        listener.em_client.list_tasks.return_value = [
            {"id": "seen-1", "title": "Seen", "category": "general"},
        ]
        listener.poll_new_tasks()
        assert listener.state.is_seen("seen-1")

    def test_poll_updates_last_task_id(self, listener):
        listener.em_client.list_tasks.return_value = [
            {"id": "last-1", "title": "Last", "category": "general"},
        ]
        listener.poll_new_tasks()
        assert listener.state.last_new_task_id == "last-1"

    def test_poll_emits_new_task_event(self, listener):
        events = []
        listener.on_event = lambda event, data: events.append((event, data))
        listener.em_client.list_tasks.return_value = [
            {"id": "evt-1", "title": "Event Task", "category": "delivery", "bounty_amount": 5.0},
        ]
        listener.poll_new_tasks()
        assert len(events) == 1
        assert events[0][0] == ListenerEvent.NEW_TASK
        assert events[0][1]["task_id"] == "evt-1"

    def test_poll_handles_api_error(self, listener):
        listener.em_client.list_tasks.side_effect = Exception("API down")
        ingested = listener.poll_new_tasks()
        assert ingested == []
        assert listener.state.total_errors == 1

    def test_poll_skips_empty_task_id(self, listener):
        listener.em_client.list_tasks.return_value = [
            {"title": "No ID", "category": "delivery"},  # Missing id
            {"id": "valid-1", "title": "Valid", "category": "delivery"},
        ]
        ingested = listener.poll_new_tasks()
        assert len(ingested) == 1

    def test_poll_maps_categories(self, listener):
        listener.em_client.list_tasks.return_value = [
            {"id": "cat-1", "title": "Delivery", "category": "delivery"},
        ]
        listener.poll_new_tasks()
        # Check that the coordinator got mapped categories
        task = listener.coordinator._task_queue.get("cat-1")
        assert task is not None
        assert "physical" in task.categories or "delivery" in task.categories

    def test_poll_uses_task_id_field(self, listener):
        listener.em_client.list_tasks.return_value = [
            {"task_id": "alt-1", "title": "Alt ID", "category": "general"},
        ]
        ingested = listener.poll_new_tasks()
        assert len(ingested) == 1


# ─── Poll Completions Tests ──────────────────────────────────────────────────

class TestPollCompletions:

    def test_poll_no_completions(self, listener):
        listener.em_client.list_tasks.return_value = []
        completed = listener.poll_completions()
        assert completed == []

    def test_poll_completion_basic(self, listener):
        # First ingest a task into the coordinator
        listener.coordinator.ingest_task(
            task_id="comp-1", title="To Complete", categories=["test"]
        )
        listener.coordinator.process_task_queue()

        # Now poll for completion
        listener.em_client.list_tasks.return_value = [
            {"id": "comp-1", "title": "Completed", "status": "completed", "evidence": []},
        ]
        completed = listener.poll_completions()
        assert len(completed) == 1
        assert listener.state.total_completions == 1

    def test_poll_completion_external_task(self, listener):
        """Completion for a task not in our queue should be silently marked as seen."""
        listener.em_client.list_tasks.return_value = [
            {"id": "ext-1", "title": "External", "status": "completed"},
        ]
        completed = listener.poll_completions()
        # External task — silently skipped
        assert listener.state.is_seen("completed_ext-1")

    def test_poll_completion_dedup(self, listener):
        listener.em_client.list_tasks.return_value = [
            {"id": "cdup-1", "title": "Dup Comp", "status": "completed"},
        ]
        listener.poll_completions()
        listener.poll_completions()  # Second call
        # Should only count once
        assert listener.state.is_seen("completed_cdup-1")

    def test_poll_completion_with_evidence(self, listener):
        listener.coordinator.ingest_task(task_id="ev-comp", title="Evidence Task", categories=["test"])
        listener.coordinator.process_task_queue()

        listener.em_client.list_tasks.return_value = [{
            "id": "ev-comp",
            "title": "Evidence Task",
            "status": "completed",
            "evidence": [
                {"type": "photo", "content": "delivery pic"},
                {"type": "text_response", "content": "Done!"},
            ],
        }]
        completed = listener.poll_completions()
        assert len(completed) == 1

    def test_poll_completion_emits_event(self, listener):
        events = []
        listener.on_event = lambda event, data: events.append((event, data))

        listener.coordinator.ingest_task(task_id="evt-comp", title="Event Comp", categories=["test"])
        listener.coordinator.process_task_queue()

        listener.em_client.list_tasks.return_value = [
            {"id": "evt-comp", "title": "Event Comp", "status": "completed", "evidence": []},
        ]
        listener.poll_completions()
        task_completed = [e for e in events if e[0] == ListenerEvent.TASK_COMPLETED]
        assert len(task_completed) == 1


# ─── Poll Failures Tests ─────────────────────────────────────────────────────

class TestPollFailures:

    def test_poll_no_failures(self, listener):
        listener.em_client.list_tasks.return_value = []
        failures = listener.poll_failures()
        assert failures == []

    def test_poll_cancelled_task(self, listener):
        listener.coordinator.ingest_task(task_id="cancel-1", title="Cancelled", categories=["test"])

        # Setup: first call returns cancelled, next two return empty
        listener.em_client.list_tasks.side_effect = [
            [{"id": "cancel-1", "title": "Cancelled", "status": "cancelled", "cancellation_reason": "user"}],
            [],  # expired
            [],  # disputed
        ]
        failures = listener.poll_failures()
        assert len(failures) == 1
        assert listener.state.total_failures == 1

    def test_poll_expired_task(self, listener):
        listener.coordinator.ingest_task(task_id="expire-1", title="Expired", categories=["test"])

        listener.em_client.list_tasks.side_effect = [
            [],  # cancelled
            [{"id": "expire-1", "title": "Expired", "status": "expired"}],
            [],  # disputed
        ]
        failures = listener.poll_failures()
        assert len(failures) == 1

    def test_poll_disputed_task(self, listener):
        listener.coordinator.ingest_task(task_id="dispute-1", title="Disputed", categories=["test"])

        listener.em_client.list_tasks.side_effect = [
            [],  # cancelled
            [],  # expired
            [{"id": "dispute-1", "title": "Disputed", "status": "disputed", "failure_reason": "evidence mismatch"}],
        ]
        failures = listener.poll_failures()
        assert len(failures) == 1

    def test_poll_failure_emits_event(self, listener):
        events = []
        listener.on_event = lambda event, data: events.append((event, data))

        listener.coordinator.ingest_task(task_id="fev-1", title="Fail Event", categories=["test"])

        listener.em_client.list_tasks.side_effect = [
            [{"id": "fev-1", "title": "Fail", "status": "cancelled"}],
            [],
            [],
        ]
        listener.poll_failures()
        failed_events = [e for e in events if e[0] == ListenerEvent.TASK_FAILED]
        assert len(failed_events) == 1

    def test_poll_failure_dedup(self, listener):
        listener.em_client.list_tasks.side_effect = [
            [{"id": "fdup-1", "title": "Fail Dup", "status": "cancelled"}],
            [],
            [],
            [{"id": "fdup-1", "title": "Fail Dup", "status": "cancelled"}],  # Same on next poll
            [],
            [],
        ]
        listener.poll_failures()
        listener.poll_failures()
        assert listener.state.total_failures == 1  # Only counted once

    def test_poll_failure_api_error(self, listener):
        listener.em_client.list_tasks.side_effect = Exception("API error")
        failures = listener.poll_failures()
        assert failures == []
        assert listener.state.total_errors >= 1


# ─── Full Poll Cycle Tests ───────────────────────────────────────────────────

class TestPollOnce:

    def test_poll_once_empty(self, listener):
        listener.em_client.list_tasks.return_value = []
        result = listener.poll_once()
        assert isinstance(result, PollResult)
        assert result.total_events == 0
        assert result.duration_ms >= 0
        assert listener.state.poll_count == 1

    def test_poll_once_with_new_tasks(self, listener):
        # list_tasks called multiple times: for new tasks, completions, failures
        listener.em_client.list_tasks.side_effect = [
            [{"id": "poll-1", "title": "New", "category": "general"}],  # new
            [],  # completed
            [],  # cancelled
            [],  # expired
            [],  # disputed
        ]
        result = listener.poll_once()
        assert result.new_tasks == 1

    def test_poll_once_triggers_queue_processing(self, listener):
        listener.em_client.list_tasks.side_effect = [
            [{"id": "proc-1", "title": "Process Me", "category": "general"}],
            [],
            [],
            [],
            [],
        ]
        result = listener.poll_once()
        # Task should have been ingested AND queue processed
        task = listener.coordinator._task_queue.get("proc-1")
        assert task is not None

    def test_poll_once_runs_health_checks(self, listener):
        listener.em_client.list_tasks.return_value = []
        listener.poll_once()
        # Health check should have been called (em_client.get_health)
        listener.em_client.get_health.assert_called()

    def test_poll_once_emits_poll_complete(self, listener):
        events = []
        listener.on_event = lambda event, data: events.append((event, data))
        listener.em_client.list_tasks.return_value = []
        listener.poll_once()
        poll_complete = [e for e in events if e[0] == ListenerEvent.POLL_COMPLETE]
        assert len(poll_complete) == 1

    def test_poll_once_updates_state(self, listener):
        listener.em_client.list_tasks.return_value = []
        listener.poll_once()
        assert listener.state.poll_count == 1
        assert listener.state.last_poll_at is not None


# ─── PollResult Tests ────────────────────────────────────────────────────────

class TestPollResult:

    def test_poll_result_defaults(self):
        result = PollResult()
        assert result.new_tasks == 0
        assert result.completed_tasks == 0
        assert result.total_events == 0

    def test_poll_result_total_events(self):
        result = PollResult(new_tasks=3, completed_tasks=2, failed_tasks=1, expired_tasks=1)
        assert result.total_events == 7

    def test_poll_result_to_dict(self):
        result = PollResult(
            new_tasks=5,
            completed_tasks=3,
            duration_ms=123.456,
        )
        d = result.to_dict()
        assert d["new_tasks"] == 5
        assert d["completed_tasks"] == 3
        assert d["total_events"] == 8
        assert d["duration_ms"] == 123.5  # Rounded


# ─── Listener State Tests ────────────────────────────────────────────────────

class TestListenerState:

    def test_state_defaults(self):
        state = ListenerState()
        assert state.poll_count == 0
        assert state.total_new_tasks == 0
        assert len(state.known_task_ids) == 0

    def test_mark_seen(self):
        state = ListenerState()
        state.mark_seen("task-1")
        assert state.is_seen("task-1")
        assert not state.is_seen("task-2")

    def test_mark_seen_pruning(self):
        state = ListenerState()
        # Exceed MAX_KNOWN_TASKS
        for i in range(state.MAX_KNOWN_TASKS + 100):
            state.mark_seen(f"task-{i}")
        assert len(state.known_task_ids) <= state.MAX_KNOWN_TASKS

    def test_state_to_dict(self):
        state = ListenerState()
        state.poll_count = 5
        state.total_new_tasks = 10
        state.mark_seen("s1")
        d = state.to_dict()
        assert d["poll_count"] == 5
        assert d["total_new_tasks"] == 10
        assert d["known_task_count"] == 1

    def test_state_save_and_load(self):
        state = ListenerState()
        state.poll_count = 42
        state.total_new_tasks = 100
        state.mark_seen("saved-1")
        state.mark_seen("saved-2")
        state.last_poll_at = datetime(2026, 3, 14, 2, 0, tzinfo=timezone.utc)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            state.save(path)
            loaded = ListenerState.load(path)
            assert loaded.poll_count == 42
            assert loaded.total_new_tasks == 100
            assert loaded.is_seen("saved-1")
            assert loaded.is_seen("saved-2")
            assert loaded.last_poll_at is not None
        finally:
            os.unlink(path)

    def test_load_nonexistent_file(self):
        state = ListenerState.load("/nonexistent/path.json")
        assert state.poll_count == 0

    def test_load_corrupt_file(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write("not valid json {{{")
            path = f.name
        try:
            state = ListenerState.load(path)
            assert state.poll_count == 0  # Falls back to empty state
        finally:
            os.unlink(path)


# ─── Listener State Persistence Tests ────────────────────────────────────────

class TestListenerStatePersistence:

    def test_state_persisted_on_poll(self, listener_with_state):
        listener, path = listener_with_state
        listener.em_client.list_tasks.return_value = []
        listener.poll_once()

        # State should be saved to disk
        with open(path) as f:
            data = json.load(f)
        assert data["poll_count"] == 1

    def test_state_survives_restart(self, listener_with_state):
        listener, path = listener_with_state

        # Poll once
        listener.em_client.list_tasks.return_value = [
            {"id": "persist-1", "title": "Persist", "category": "general"},
        ]
        listener.poll_new_tasks()
        listener._save_state()

        # Create new listener from same state file
        new_listener = EventListener(listener.coordinator, state_path=path)
        assert new_listener.state.is_seen("persist-1")
        assert new_listener.state.total_new_tasks == 1


# ─── Evidence Summary Tests ──────────────────────────────────────────────────

class TestEvidenceSummary:

    def test_summarize_no_evidence(self, listener):
        assert listener._summarize_evidence(None) == "no_evidence"
        assert listener._summarize_evidence([]) == "no_evidence"

    def test_summarize_string_evidence(self, listener):
        result = listener._summarize_evidence("plain text evidence")
        assert "plain text" in result

    def test_summarize_list_evidence(self, listener):
        evidence = [
            {"type": "photo", "content": "pic"},
            {"type": "text_response", "content": "text"},
        ]
        result = listener._summarize_evidence(evidence)
        assert "photo" in result
        assert "text_response" in result

    def test_summarize_truncates_long_string(self, listener):
        long_string = "x" * 500
        result = listener._summarize_evidence(long_string)
        assert len(result) <= 200


# ─── Listener Run Mode Tests ─────────────────────────────────────────────────

class TestListenerRun:

    def test_run_with_max_polls(self, listener):
        listener.em_client.list_tasks.return_value = []
        listener.run(poll_interval=0.01, max_polls=3)
        assert listener.state.poll_count == 3

    def test_stop_signal(self, listener):
        listener.em_client.list_tasks.return_value = []
        # Stop immediately
        listener.stop()
        assert listener._running is False

    def test_get_status(self, listener):
        status = listener.get_status()
        assert "running" in status
        assert "state" in status
        assert "em_api_url" in status
        assert status["running"] is False


# ─── Event Callback Tests ────────────────────────────────────────────────────

class TestEventCallbacks:

    def test_callback_receives_all_events(self, listener):
        events = []
        listener.on_event = lambda event, data: events.append(event.value)

        listener.em_client.list_tasks.side_effect = [
            [{"id": "cb-1", "title": "Callback", "category": "general"}],
            [],
            [],
            [],
            [],
        ]
        listener.poll_once()

        assert ListenerEvent.NEW_TASK.value in events
        assert ListenerEvent.POLL_COMPLETE.value in events

    def test_callback_error_doesnt_crash(self, listener):
        def bad_callback(event, data):
            raise RuntimeError("Callback exploded!")

        listener.on_event = bad_callback
        listener.em_client.list_tasks.return_value = [
            {"id": "safe-1", "title": "Safe", "category": "general"},
        ]
        # Should not raise
        listener.poll_new_tasks()
