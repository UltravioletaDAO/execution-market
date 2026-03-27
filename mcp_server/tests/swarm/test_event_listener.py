"""
Tests for EventListener — Polls the EM API for new tasks and completion events.

Covers:
    - Category mapping (EM → swarm routing categories)
    - Priority estimation from bounty amounts
    - ListenerEvent enum
    - PollResult dataclass and properties
    - ListenerState watermark management
    - ListenerState serialization (save/load)
    - Known task deduplication with FIFO eviction
    - EventListener initialization
    - poll_new_tasks() with mocked coordinator
    - poll_completions() with mocked coordinator
    - poll_failures() with mocked coordinator
    - poll_once() full cycle
    - Event callbacks
    - Error handling and graceful degradation
    - Continuous run() with max_polls
    - stop() signal
    - get_status()
"""

import json
import os
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.swarm.event_listener import (
    EM_CATEGORY_MAP,
    map_categories,
    estimate_priority,
    ListenerEvent,
    PollResult,
    ListenerState,
    EventListener,
)


# ─── Category Mapping ────────────────────────────────────────────


class TestCategoryMapping:
    def test_known_category(self):
        result = map_categories("delivery")
        assert result == ["physical", "delivery", "logistics"]

    def test_coding_category(self):
        result = map_categories("coding")
        assert result == ["digital", "coding", "technical"]

    def test_blockchain_category(self):
        result = map_categories("blockchain")
        assert result == ["blockchain", "crypto", "technical"]

    def test_case_insensitive(self):
        result = map_categories("DELIVERY")
        assert result == ["physical", "delivery", "logistics"]

    def test_whitespace_stripped(self):
        result = map_categories("  design  ")
        assert result == ["digital", "design", "creative"]

    def test_unknown_category(self):
        result = map_categories("something_new")
        assert result == ["general", "something_new"]

    def test_none_category(self):
        result = map_categories(None)
        assert result == ["general", "misc"]

    def test_empty_string(self):
        result = map_categories("")
        assert result == ["general", "misc"]

    def test_all_mapped_categories(self):
        """Verify all entries in EM_CATEGORY_MAP are lists."""
        for key, value in EM_CATEGORY_MAP.items():
            assert isinstance(value, list), f"Category {key} is not a list"
            assert len(value) >= 2, f"Category {key} has fewer than 2 routing tags"


# ─── Priority Estimation ─────────────────────────────────────────


class TestPriorityEstimation:
    def test_high_bounty(self):
        assert estimate_priority({"bounty_amount": 100}) == "HIGH"

    def test_normal_bounty(self):
        assert estimate_priority({"bounty_amount": 25}) == "NORMAL"

    def test_low_bounty(self):
        assert estimate_priority({"bounty_amount": 3}) == "LOW"

    def test_zero_bounty(self):
        assert estimate_priority({"bounty_amount": 0}) == "NORMAL"

    def test_missing_bounty(self):
        assert estimate_priority({}) == "NORMAL"

    def test_none_bounty(self):
        assert estimate_priority({"bounty_amount": None}) == "NORMAL"

    def test_string_bounty(self):
        assert estimate_priority({"bounty_amount": "invalid"}) == "NORMAL"

    def test_boundary_50(self):
        assert estimate_priority({"bounty_amount": 50}) == "HIGH"

    def test_boundary_10(self):
        assert estimate_priority({"bounty_amount": 10}) == "NORMAL"

    def test_boundary_1(self):
        assert estimate_priority({"bounty_amount": 1}) == "LOW"

    def test_float_bounty(self):
        assert estimate_priority({"bounty_amount": 49.99}) == "NORMAL"


# ─── ListenerEvent Enum ──────────────────────────────────────────


class TestListenerEvent:
    def test_event_values(self):
        assert ListenerEvent.NEW_TASK == "new_task"
        assert ListenerEvent.TASK_COMPLETED == "task_completed"
        assert ListenerEvent.TASK_FAILED == "task_failed"
        assert ListenerEvent.TASK_EXPIRED == "task_expired"
        assert ListenerEvent.POLL_COMPLETE == "poll_complete"
        assert ListenerEvent.POLL_ERROR == "poll_error"


# ─── PollResult ──────────────────────────────────────────────────


class TestPollResult:
    def test_default_creation(self):
        result = PollResult()
        assert result.new_tasks == 0
        assert result.completed_tasks == 0
        assert result.failed_tasks == 0
        assert result.expired_tasks == 0
        assert result.errors == []
        assert result.duration_ms == 0.0
        assert result.total_events == 0

    def test_total_events(self):
        result = PollResult(new_tasks=5, completed_tasks=3, failed_tasks=1, expired_tasks=2)
        assert result.total_events == 11

    def test_to_dict(self):
        result = PollResult(
            new_tasks=10,
            completed_tasks=5,
            duration_ms=123.456,
            errors=["timeout"],
        )
        d = result.to_dict()
        assert d["new_tasks"] == 10
        assert d["completed_tasks"] == 5
        assert d["duration_ms"] == 123.5
        assert d["total_events"] == 15
        assert d["errors"] == ["timeout"]
        assert "timestamp" in d


# ─── ListenerState ───────────────────────────────────────────────


class TestListenerState:
    def test_default_state(self):
        state = ListenerState()
        assert state.poll_count == 0
        assert state.total_new_tasks == 0
        assert state.last_poll_at is None

    def test_mark_seen(self):
        state = ListenerState()
        state.mark_seen("task-001")
        assert state.is_seen("task-001") is True
        assert state.is_seen("task-002") is False

    def test_mark_seen_duplicate(self):
        state = ListenerState()
        state.mark_seen("task-001")
        state.mark_seen("task-001")
        assert len(state._known_set) == 1

    def test_fifo_eviction(self):
        """Known tasks should evict oldest when exceeding MAX_KNOWN_TASKS."""
        state = ListenerState()
        # Override maxlen for testing
        state._known_deque = __import__("collections").deque(maxlen=5)
        state._known_set = set()

        for i in range(7):
            state.mark_seen(f"task-{i:03d}")

        # First 2 should have been evicted
        assert state.is_seen("task-000") is False
        assert state.is_seen("task-001") is False
        # Last 5 should still be there
        assert state.is_seen("task-002") is True
        assert state.is_seen("task-006") is True
        assert len(state._known_set) == 5

    def test_to_dict(self):
        state = ListenerState()
        state.poll_count = 10
        state.total_new_tasks = 50
        state.mark_seen("x")
        d = state.to_dict()
        assert d["poll_count"] == 10
        assert d["total_new_tasks"] == 50
        assert d["known_task_count"] == 1

    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            state = ListenerState()
            state.poll_count = 42
            state.total_new_tasks = 100
            state.mark_seen("task-a")
            state.mark_seen("task-b")
            state.save(path)

            loaded = ListenerState.load(path)
            assert loaded.poll_count == 42
            assert loaded.total_new_tasks == 100
            assert loaded.is_seen("task-a") is True
            assert loaded.is_seen("task-b") is True
        finally:
            os.unlink(path)

    def test_load_nonexistent_file(self):
        state = ListenerState.load("/nonexistent/path.json")
        assert state.poll_count == 0
        assert state.total_new_tasks == 0

    def test_load_corrupt_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{bad json")
            path = f.name

        try:
            state = ListenerState.load(path)
            assert state.poll_count == 0
        finally:
            os.unlink(path)

    def test_state_preserves_order_on_load(self):
        """Loaded state should preserve insertion order for FIFO eviction."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            state = ListenerState()
            for i in range(5):
                state.mark_seen(f"task-{i}")
            state.save(path)

            loaded = ListenerState.load(path)
            # All should be present
            for i in range(5):
                assert loaded.is_seen(f"task-{i}") is True
        finally:
            os.unlink(path)


# ─── EventListener Construction ──────────────────────────────────


def _make_mock_coordinator():
    """Create a mock SwarmCoordinator for EventListener tests."""
    coord = MagicMock()
    coord.em_client = MagicMock()
    coord.em_client.base_url = "https://api.execution.market"
    return coord


class TestEventListenerInit:
    def test_default_init(self):
        coord = _make_mock_coordinator()
        listener = EventListener(coord)
        assert listener.coordinator is coord
        assert listener.em_client is coord.em_client
        assert listener.state_path is None
        assert listener._running is False

    def test_init_with_state_path(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"poll_count": 5, "total_new_tasks": 10,
                        "total_completions": 3, "total_failures": 1,
                        "total_errors": 0}, f)
            path = f.name

        try:
            coord = _make_mock_coordinator()
            listener = EventListener(coord, state_path=path)
            assert listener.state.poll_count == 5
        finally:
            os.unlink(path)


# ─── poll_new_tasks() ────────────────────────────────────────────


class TestPollNewTasks:
    def test_no_tasks(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = []

        listener = EventListener(coord)
        result = listener.poll_new_tasks()
        assert result == []

    def test_ingest_new_tasks(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "title": "Buy coffee", "category": "errand", "bounty_amount": 5.0},
            {"id": "t2", "title": "Code review", "category": "coding", "bounty_amount": 20.0},
        ]

        listener = EventListener(coord)
        result = listener.poll_new_tasks()

        assert len(result) == 2
        assert coord.ingest_task.call_count == 2
        assert listener.state.total_new_tasks == 2

    def test_deduplication(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "title": "Task", "category": "general", "bounty_amount": 1.0},
        ]

        listener = EventListener(coord)
        listener.poll_new_tasks()
        listener.poll_new_tasks()  # Second poll with same task

        assert coord.ingest_task.call_count == 1  # Only ingested once

    def test_api_error_handled(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.side_effect = ConnectionError("API down")

        listener = EventListener(coord)
        result = listener.poll_new_tasks()
        assert result == []
        assert listener.state.total_errors == 1

    def test_ingest_error_handled(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "title": "Task", "category": "general", "bounty_amount": 1.0},
        ]
        coord.ingest_task.side_effect = RuntimeError("ingest fail")

        listener = EventListener(coord)
        result = listener.poll_new_tasks()
        assert result == []
        assert listener.state.total_errors == 1

    def test_event_callback_fires(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "title": "Task", "category": "general", "bounty_amount": 5.0},
        ]

        events = []
        listener = EventListener(coord, on_event=lambda evt, data: events.append((evt, data)))
        listener.poll_new_tasks()

        assert len(events) == 1
        assert events[0][0] == ListenerEvent.NEW_TASK
        assert events[0][1]["task_id"] == "t1"

    def test_tasks_with_task_id_field(self):
        """Handle tasks that use 'task_id' instead of 'id'."""
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"task_id": "t1", "title": "Task", "category": "general", "bounty_amount": 1.0},
        ]

        listener = EventListener(coord)
        result = listener.poll_new_tasks()
        assert len(result) == 1

    def test_none_tasks_response(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = None

        listener = EventListener(coord)
        result = listener.poll_new_tasks()
        assert result == []


# ─── poll_completions() ──────────────────────────────────────────


class TestPollCompletions:
    def test_no_completions(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = []

        listener = EventListener(coord)
        result = listener.poll_completions()
        assert result == []

    def test_process_completions(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "worker_agent_id": 2101, "evidence": [{"type": "photo"}]},
        ]

        listener = EventListener(coord)
        result = listener.poll_completions()

        assert len(result) == 1
        coord.complete_task.assert_called_once()
        assert listener.state.total_completions == 1

    def test_external_completion_handled(self):
        """Tasks not in our queue should be silently skipped."""
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "evidence": []},
        ]
        coord.complete_task.side_effect = KeyError("not in queue")

        listener = EventListener(coord)
        result = listener.poll_completions()
        assert result == []

    def test_completion_deduplication(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "evidence": []},
        ]

        listener = EventListener(coord)
        listener.poll_completions()
        listener.poll_completions()  # Second poll

        assert coord.complete_task.call_count == 1

    def test_completion_event_callback(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "worker_agent_id": 2101, "evidence": [{"type": "photo"}]},
        ]

        events = []
        listener = EventListener(coord, on_event=lambda e, d: events.append((e, d)))
        listener.poll_completions()

        completed = [e for e in events if e[0] == ListenerEvent.TASK_COMPLETED]
        assert len(completed) == 1


# ─── poll_failures() ─────────────────────────────────────────────


class TestPollFailures:
    def test_no_failures(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = []

        listener = EventListener(coord)
        result = listener.poll_failures()
        assert result == []

    def test_cancelled_task(self):
        coord = _make_mock_coordinator()
        # Return cancelled task for first status query, empty for others
        coord.em_client.list_tasks.side_effect = [
            [{"id": "t1", "status": "cancelled", "cancellation_reason": "no workers"}],
            [],  # expired
            [],  # disputed
        ]

        listener = EventListener(coord)
        result = listener.poll_failures()

        assert len(result) == 1
        coord.fail_task.assert_called_once()
        assert listener.state.total_failures == 1

    def test_expired_task_fires_expired_event(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.side_effect = [
            [],  # cancelled
            [{"id": "t1", "status": "expired"}],  # expired
            [],  # disputed
        ]

        events = []
        listener = EventListener(coord, on_event=lambda e, d: events.append((e, d)))
        listener.poll_failures()

        expired = [e for e in events if e[0] == ListenerEvent.TASK_EXPIRED]
        assert len(expired) == 1

    def test_failure_deduplication(self):
        coord = _make_mock_coordinator()
        cancelled_tasks = [{"id": "t1", "status": "cancelled"}]
        coord.em_client.list_tasks.side_effect = [
            cancelled_tasks, [], [],  # First poll
            cancelled_tasks, [], [],  # Second poll
        ]

        listener = EventListener(coord)
        listener.poll_failures()
        listener.poll_failures()

        assert coord.fail_task.call_count == 1

    def test_external_failure_handled(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.side_effect = [
            [{"id": "t1", "status": "cancelled"}], [], [],
        ]
        coord.fail_task.side_effect = KeyError("not in queue")

        listener = EventListener(coord)
        result = listener.poll_failures()
        assert result == []


# ─── poll_once() ─────────────────────────────────────────────────


class TestPollOnce:
    def test_full_poll_cycle(self):
        coord = _make_mock_coordinator()
        # list_tasks called for: published, completed, cancelled, expired, disputed
        coord.em_client.list_tasks.return_value = []

        listener = EventListener(coord)
        result = listener.poll_once()

        assert isinstance(result, PollResult)
        assert result.duration_ms >= 0
        assert listener.state.poll_count == 1
        assert listener.state.last_poll_at is not None

    def test_poll_with_new_tasks_triggers_queue_processing(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.side_effect = [
            [{"id": "t1", "title": "Test", "category": "general", "bounty_amount": 1.0}],
            [],  # completed
            [], [], [],  # failures
        ]

        listener = EventListener(coord)
        result = listener.poll_once()

        assert result.new_tasks == 1
        coord.process_task_queue.assert_called_once()
        coord.run_health_checks.assert_called_once()

    def test_poll_errors_collected(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = []
        coord.run_health_checks.side_effect = RuntimeError("health check boom")

        listener = EventListener(coord)
        result = listener.poll_once()

        assert any("health_check" in e for e in result.errors)

    def test_poll_fires_complete_event(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = []

        events = []
        listener = EventListener(coord, on_event=lambda e, d: events.append((e, d)))
        listener.poll_once()

        complete = [e for e in events if e[0] == ListenerEvent.POLL_COMPLETE]
        assert len(complete) == 1

    def test_poll_saves_state(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            coord = _make_mock_coordinator()
            coord.em_client.list_tasks.return_value = []
            listener = EventListener(coord, state_path=path)
            listener.poll_once()

            # Verify state file was written
            with open(path) as f:
                data = json.load(f)
            assert data["poll_count"] == 1
        finally:
            os.unlink(path)


# ─── Evidence Summarization ──────────────────────────────────────


class TestEvidenceSummarization:
    def test_no_evidence(self):
        coord = _make_mock_coordinator()
        listener = EventListener(coord)
        assert listener._summarize_evidence(None) == "no_evidence"
        assert listener._summarize_evidence([]) == "no_evidence"

    def test_string_evidence(self):
        coord = _make_mock_coordinator()
        listener = EventListener(coord)
        result = listener._summarize_evidence("some evidence text")
        assert result == "some evidence text"

    def test_list_evidence_with_types(self):
        coord = _make_mock_coordinator()
        listener = EventListener(coord)
        evidence = [
            {"type": "photo"},
            {"type": "gps"},
            {"evidence_type": "receipt"},
        ]
        result = listener._summarize_evidence(evidence)
        assert "photo" in result
        assert "gps" in result
        assert "receipt" in result

    def test_long_string_truncated(self):
        coord = _make_mock_coordinator()
        listener = EventListener(coord)
        result = listener._summarize_evidence("x" * 500)
        assert len(result) == 200


# ─── Continuous Run ──────────────────────────────────────────────


class TestContinuousRun:
    def test_run_with_max_polls(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = []

        listener = EventListener(coord)
        listener.run(poll_interval=0.01, max_polls=3)

        assert listener.state.poll_count == 3
        assert listener._running is False

    def test_stop_signal(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = []

        listener = EventListener(coord)
        # Stop before run starts (simulate quick stop)
        listener._running = False
        # This should exit immediately since _running check happens after first poll
        listener.run(poll_interval=0.01, max_polls=100)


# ─── get_status() ────────────────────────────────────────────────


class TestGetStatus:
    def test_status_structure(self):
        coord = _make_mock_coordinator()
        listener = EventListener(coord)
        status = listener.get_status()
        assert "running" in status
        assert "state" in status
        assert "em_api_url" in status
        assert status["running"] is False


# ─── Callback Error Handling ─────────────────────────────────────


class TestCallbackErrors:
    def test_event_callback_error_doesnt_crash(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "title": "Task", "category": "general", "bounty_amount": 1.0},
        ]

        def bad_callback(event, data):
            raise RuntimeError("callback exploded")

        listener = EventListener(coord, on_event=bad_callback)
        result = listener.poll_new_tasks()
        # Should still ingest despite callback error
        assert len(result) == 1
