"""
Tests for EventListener — Polls EM API for task lifecycle events.

Covers:
    - Category mapping (EM categories → swarm routing categories)
    - Priority estimation from bounty amounts
    - ListenerState: mark_seen, is_seen, FIFO eviction, save/load
    - PollResult aggregation and to_dict
    - EventListener: poll_new_tasks, poll_completions, poll_failures
    - EventListener: poll_once (full cycle), run loop, stop
    - Event callbacks
    - Evidence summarization
    - Watermark-based deduplication
    - Error handling and graceful degradation
"""

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from mcp_server.swarm.event_listener import (
    EM_CATEGORY_MAP,
    map_categories,
    estimate_priority,
    ListenerEvent,
    ListenerState,
    PollResult,
    EventListener,
)


# ─── Category Mapping ─────────────────────────────────────────────────────────


class TestCategoryMapping:
    def test_known_categories(self):
        assert "physical" in map_categories("delivery")
        assert "physical" in map_categories("pickup")
        assert "physical" in map_categories("errand")
        assert "digital" in map_categories("coding")
        assert "digital" in map_categories("research")
        assert "blockchain" in map_categories("defi")
        assert "verification" in map_categories("photo_verification")

    def test_case_insensitive(self):
        assert map_categories("DELIVERY") == map_categories("delivery")
        assert map_categories("Coding") == map_categories("coding")

    def test_whitespace_trimmed(self):
        assert map_categories("  delivery  ") == map_categories("delivery")

    def test_unknown_category(self):
        result = map_categories("quantum_teleportation")
        assert "general" in result
        assert "quantum_teleportation" in result

    def test_none_category(self):
        result = map_categories(None)
        assert result == ["general", "misc"]

    def test_empty_string(self):
        result = map_categories("")
        assert result == ["general", "misc"]

    def test_all_map_entries_valid(self):
        """Every mapped category should return a non-empty list."""
        for key, values in EM_CATEGORY_MAP.items():
            assert isinstance(values, list)
            assert len(values) >= 1


# ─── Priority Estimation ──────────────────────────────────────────────────────


class TestPriorityEstimation:
    def test_high_bounty(self):
        assert estimate_priority({"bounty_amount": 100}) == "HIGH"
        assert estimate_priority({"bounty_amount": 50}) == "HIGH"

    def test_normal_bounty(self):
        assert estimate_priority({"bounty_amount": 25}) == "NORMAL"
        assert estimate_priority({"bounty_amount": 10}) == "NORMAL"

    def test_low_bounty(self):
        assert estimate_priority({"bounty_amount": 5}) == "LOW"
        assert estimate_priority({"bounty_amount": 1}) == "LOW"

    def test_zero_bounty(self):
        assert estimate_priority({"bounty_amount": 0}) == "NORMAL"

    def test_missing_bounty(self):
        assert estimate_priority({}) == "NORMAL"

    def test_none_bounty(self):
        assert estimate_priority({"bounty_amount": None}) == "NORMAL"

    def test_string_bounty(self):
        assert estimate_priority({"bounty_amount": "not_a_number"}) == "NORMAL"


# ─── ListenerState ────────────────────────────────────────────────────────────


class TestListenerState:
    def test_initial_state(self):
        state = ListenerState()
        assert state.last_poll_at is None
        assert state.poll_count == 0
        assert state.total_new_tasks == 0

    def test_mark_seen_and_is_seen(self):
        state = ListenerState()
        assert not state.is_seen("t1")
        state.mark_seen("t1")
        assert state.is_seen("t1")

    def test_mark_seen_idempotent(self):
        state = ListenerState()
        state.mark_seen("t1")
        state.mark_seen("t1")
        assert state.is_seen("t1")
        # Should not have duplicates internally
        assert len(state._known_set) == 1

    def test_fifo_eviction(self):
        """When maxlen is reached, oldest items should be evicted."""
        state = ListenerState()
        # Override maxlen to a small value for testing
        state._known_deque = type(state._known_deque)(maxlen=3)
        state._known_set = set()

        state.mark_seen("t1")
        state.mark_seen("t2")
        state.mark_seen("t3")
        assert state.is_seen("t1")

        # Adding t4 should evict t1
        state.mark_seen("t4")
        assert not state.is_seen("t1")
        assert state.is_seen("t2")
        assert state.is_seen("t3")
        assert state.is_seen("t4")

    def test_to_dict(self):
        state = ListenerState()
        state.poll_count = 10
        state.total_new_tasks = 5
        state.total_completions = 3
        state.mark_seen("t1")
        state.mark_seen("t2")

        d = state.to_dict()
        assert d["poll_count"] == 10
        assert d["total_new_tasks"] == 5
        assert d["total_completions"] == 3
        assert d["known_task_count"] == 2

    def test_save_and_load(self):
        state = ListenerState()
        state.poll_count = 7
        state.total_new_tasks = 3
        state.total_completions = 2
        state.total_failures = 1
        state.total_errors = 0
        state.last_poll_at = datetime(2026, 3, 16, 2, 0, 0, tzinfo=timezone.utc)
        state.last_new_task_id = "t5"
        state.mark_seen("t1")
        state.mark_seen("t2")
        state.mark_seen("t3")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            state.save(path)
            loaded = ListenerState.load(path)

            assert loaded.poll_count == 7
            assert loaded.total_new_tasks == 3
            assert loaded.total_completions == 2
            assert loaded.total_failures == 1
            assert loaded.last_new_task_id == "t5"
            assert loaded.is_seen("t1")
            assert loaded.is_seen("t2")
            assert loaded.is_seen("t3")
            assert not loaded.is_seen("t4")
        finally:
            os.unlink(path)

    def test_load_missing_file(self):
        state = ListenerState.load("/nonexistent/file.json")
        assert state.poll_count == 0
        assert not state.is_seen("anything")

    def test_load_corrupt_file(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write("{bad json!!")
            path = f.name
        try:
            state = ListenerState.load(path)
            assert state.poll_count == 0
        finally:
            os.unlink(path)

    def test_max_known_tasks_constant(self):
        assert ListenerState.MAX_KNOWN_TASKS == 10000


# ─── PollResult ───────────────────────────────────────────────────────────────


class TestPollResult:
    def test_total_events(self):
        r = PollResult(new_tasks=3, completed_tasks=2, failed_tasks=1, expired_tasks=1)
        assert r.total_events == 7

    def test_total_events_zero(self):
        r = PollResult()
        assert r.total_events == 0

    def test_to_dict(self):
        r = PollResult(
            new_tasks=5,
            completed_tasks=2,
            duration_ms=123.456,
            errors=["some error"],
        )
        d = r.to_dict()
        assert d["new_tasks"] == 5
        assert d["completed_tasks"] == 2
        assert d["duration_ms"] == 123.5
        assert d["errors"] == ["some error"]
        assert d["total_events"] == 7
        assert "timestamp" in d


# ─── EventListener ────────────────────────────────────────────────────────────


def _make_mock_coordinator():
    """Create a mock coordinator with the necessary interface."""
    coordinator = MagicMock()
    coordinator.em_client = MagicMock()
    coordinator.ingest_task = MagicMock()
    coordinator.complete_task = MagicMock(return_value=True)
    coordinator.fail_task = MagicMock(return_value=True)
    coordinator.process_task_queue = MagicMock()
    coordinator.run_health_checks = MagicMock(return_value={})
    return coordinator


class TestEventListenerInit:
    def test_basic_init(self):
        coord = _make_mock_coordinator()
        listener = EventListener(coord)
        assert listener.coordinator is coord
        assert listener.em_client is coord.em_client
        assert listener.state_path is None
        assert not listener._running

    def test_init_with_state_path(self):
        coord = _make_mock_coordinator()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
            f.write(b'{}')  # Empty valid JSON

        try:
            listener = EventListener(coord, state_path=path)
            assert listener.state_path == path
        finally:
            os.unlink(path)

    def test_init_with_callback(self):
        coord = _make_mock_coordinator()
        cb = MagicMock()
        listener = EventListener(coord, on_event=cb)
        assert listener.on_event is cb


class TestPollNewTasks:
    def test_ingests_new_tasks(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "title": "Test Task", "category": "delivery", "bounty_amount": 10},
            {"id": "t2", "title": "Task Two", "category": "coding", "bounty_amount": 25},
        ]
        listener = EventListener(coord)
        ingested = listener.poll_new_tasks()

        assert len(ingested) == 2
        assert coord.ingest_task.call_count == 2

    def test_skips_already_seen_tasks(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "title": "Old Task", "category": "general"},
        ]
        listener = EventListener(coord)
        listener.state.mark_seen("t1")

        ingested = listener.poll_new_tasks()
        assert len(ingested) == 0
        assert coord.ingest_task.call_count == 0

    def test_skips_tasks_without_id(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"title": "No ID Task", "category": "general"},
        ]
        listener = EventListener(coord)
        ingested = listener.poll_new_tasks()
        assert len(ingested) == 0

    def test_handles_api_error(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.side_effect = Exception("API down")
        listener = EventListener(coord)
        ingested = listener.poll_new_tasks()
        assert len(ingested) == 0
        assert listener.state.total_errors == 1

    def test_handles_empty_response(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = []
        listener = EventListener(coord)
        ingested = listener.poll_new_tasks()
        assert len(ingested) == 0

    def test_handles_ingest_error(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "title": "Fail Task", "category": "general"},
        ]
        coord.ingest_task.side_effect = Exception("ingest failed")
        listener = EventListener(coord)
        ingested = listener.poll_new_tasks()
        assert len(ingested) == 0
        assert listener.state.total_errors == 1

    def test_updates_state_on_success(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "title": "Test", "category": "delivery", "bounty_amount": 5},
        ]
        listener = EventListener(coord)
        listener.poll_new_tasks()

        assert listener.state.is_seen("t1")
        assert listener.state.last_new_task_id == "t1"
        assert listener.state.total_new_tasks == 1

    def test_emits_event_callback(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "title": "Test", "category": "delivery"},
        ]
        cb = MagicMock()
        listener = EventListener(coord, on_event=cb)
        listener.poll_new_tasks()

        cb.assert_called_once()
        args = cb.call_args[0]
        assert args[0] == ListenerEvent.NEW_TASK
        assert args[1]["task_id"] == "t1"

    def test_maps_bounty_correctly(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "title": "Expensive", "category": "general", "bounty_amount": 75},
        ]
        listener = EventListener(coord)
        listener.poll_new_tasks()

        call_kwargs = coord.ingest_task.call_args[1]
        assert call_kwargs["bounty_usd"] == 75.0

    def test_handles_invalid_bounty(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "title": "Bad Bounty", "category": "general", "bounty_amount": "free"},
        ]
        listener = EventListener(coord)
        listener.poll_new_tasks()

        call_kwargs = coord.ingest_task.call_args[1]
        assert call_kwargs["bounty_usd"] == 0.0

    def test_uses_task_id_field(self):
        """API may return 'task_id' instead of 'id'."""
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"task_id": "t1", "title": "Alt ID", "category": "general"},
        ]
        listener = EventListener(coord)
        ingested = listener.poll_new_tasks()
        assert len(ingested) == 1


class TestPollCompletions:
    def test_processes_completions(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "worker_agent_id": 42, "evidence": [{"type": "photo"}]},
        ]
        listener = EventListener(coord)
        completed = listener.poll_completions()

        assert len(completed) == 1
        coord.complete_task.assert_called_once()

    def test_skips_seen_completions(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1"},
        ]
        listener = EventListener(coord)
        listener.state.mark_seen("completed_t1")

        completed = listener.poll_completions()
        assert len(completed) == 0

    def test_handles_external_task_completion(self):
        """Tasks not in coordinator queue should be silently skipped."""
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t_external"},
        ]
        coord.complete_task.side_effect = KeyError("not in queue")
        listener = EventListener(coord)
        completed = listener.poll_completions()
        # External task gets marked as seen but not added to completed list
        assert listener.state.is_seen("completed_t_external")

    def test_handles_api_error(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.side_effect = Exception("Network error")
        listener = EventListener(coord)
        completed = listener.poll_completions()
        assert len(completed) == 0
        assert listener.state.total_errors == 1

    def test_emits_completion_event(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "worker_agent_id": 42, "evidence": []},
        ]
        cb = MagicMock()
        listener = EventListener(coord, on_event=cb)
        listener.poll_completions()

        cb.assert_called_once()
        assert cb.call_args[0][0] == ListenerEvent.TASK_COMPLETED


class TestPollFailures:
    def test_processes_cancelled_tasks(self):
        coord = _make_mock_coordinator()
        # list_tasks called for each of: cancelled, expired, disputed
        coord.em_client.list_tasks.side_effect = [
            [{"id": "t1", "cancellation_reason": "user cancelled"}],  # cancelled
            [],  # expired
            [],  # disputed
        ]
        listener = EventListener(coord)
        failures = listener.poll_failures()

        assert len(failures) == 1
        coord.fail_task.assert_called_once()

    def test_processes_expired_tasks(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.side_effect = [
            [],  # cancelled
            [{"id": "t1", "failure_reason": "timeout"}],  # expired
            [],  # disputed
        ]
        listener = EventListener(coord)
        failures = listener.poll_failures()
        assert len(failures) == 1

    def test_processes_disputed_tasks(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.side_effect = [
            [],  # cancelled
            [],  # expired
            [{"id": "t1", "failure_reason": "dispute"}],  # disputed
        ]
        listener = EventListener(coord)
        failures = listener.poll_failures()
        assert len(failures) == 1

    def test_skips_seen_failures(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.side_effect = [
            [{"id": "t1"}],  # cancelled
            [],
            [],
        ]
        listener = EventListener(coord)
        listener.state.mark_seen("cancelled_t1")
        failures = listener.poll_failures()
        assert len(failures) == 0

    def test_handles_external_task_failure(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.side_effect = [
            [{"id": "t_ext"}],
            [],
            [],
        ]
        coord.fail_task.side_effect = KeyError("not in queue")
        listener = EventListener(coord)
        failures = listener.poll_failures()
        assert listener.state.is_seen("cancelled_t_ext")

    def test_handles_api_error_per_status(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.side_effect = [
            Exception("cancelled API error"),
            [],  # expired OK
            [],  # disputed OK
        ]
        listener = EventListener(coord)
        failures = listener.poll_failures()
        assert listener.state.total_errors >= 1


class TestPollOnce:
    def test_full_cycle(self):
        coord = _make_mock_coordinator()
        # poll_new_tasks
        coord.em_client.list_tasks.side_effect = [
            [{"id": "t1", "title": "New", "category": "delivery", "bounty_amount": 5}],  # published
            [],  # completed
            [],  # cancelled
            [],  # expired
            [],  # disputed
        ]
        listener = EventListener(coord)
        result = listener.poll_once()

        assert isinstance(result, PollResult)
        assert result.new_tasks == 1
        assert result.completed_tasks == 0
        assert result.duration_ms > 0
        assert listener.state.poll_count == 1
        coord.process_task_queue.assert_called_once()
        coord.run_health_checks.assert_called_once()

    def test_no_events_cycle(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = []
        listener = EventListener(coord)
        result = listener.poll_once()

        assert result.total_events == 0
        coord.process_task_queue.assert_not_called()  # No new tasks → no processing
        coord.run_health_checks.assert_called_once()

    def test_saves_state_after_poll(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = []

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
            f.write(b'{}')

        try:
            listener = EventListener(coord, state_path=path)
            listener.poll_once()

            # Verify state was saved
            with open(path) as f:
                data = json.load(f)
            assert data["poll_count"] == 1
        finally:
            os.unlink(path)

    def test_health_check_error_captured(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = []
        coord.run_health_checks.side_effect = Exception("health error")
        listener = EventListener(coord)
        result = listener.poll_once()
        assert any("health_check" in e for e in result.errors)

    def test_queue_processing_error_captured(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.side_effect = [
            [{"id": "t1", "title": "X", "category": "general"}],
            [],
            [],
            [],
            [],
        ]
        coord.process_task_queue.side_effect = Exception("queue error")
        listener = EventListener(coord)
        result = listener.poll_once()
        assert any("queue_processing" in e for e in result.errors)


class TestEvidenceSummarization:
    def test_empty_evidence(self):
        coord = _make_mock_coordinator()
        listener = EventListener(coord)
        assert listener._summarize_evidence(None) == "no_evidence"
        assert listener._summarize_evidence([]) == "no_evidence"

    def test_string_evidence(self):
        coord = _make_mock_coordinator()
        listener = EventListener(coord)
        result = listener._summarize_evidence("simple string evidence")
        assert result == "simple string evidence"

    def test_string_evidence_truncated(self):
        coord = _make_mock_coordinator()
        listener = EventListener(coord)
        long_str = "x" * 500
        result = listener._summarize_evidence(long_str)
        assert len(result) <= 200

    def test_list_evidence(self):
        coord = _make_mock_coordinator()
        listener = EventListener(coord)
        evidence = [
            {"type": "photo"},
            {"evidence_type": "text_response"},
            {"type": "screenshot"},
        ]
        result = listener._summarize_evidence(evidence)
        assert "photo" in result
        assert "text_response" in result
        assert "screenshot" in result


class TestRunLoop:
    def test_run_with_max_polls(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = []
        listener = EventListener(coord)

        listener.run(poll_interval=0.01, max_polls=3)
        assert listener.state.poll_count == 3
        assert not listener._running

    def test_stop(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = []
        listener = EventListener(coord)

        # Stop immediately via max_polls
        listener.run(poll_interval=0.01, max_polls=1)
        assert not listener._running

    def test_get_status(self):
        coord = _make_mock_coordinator()
        coord.em_client.base_url = "https://api.execution.market"
        listener = EventListener(coord)

        status = listener.get_status()
        assert status["running"] is False
        assert "state" in status
        assert status["em_api_url"] == "https://api.execution.market"


class TestEventCallbackErrorHandling:
    def test_callback_error_does_not_crash(self):
        coord = _make_mock_coordinator()
        coord.em_client.list_tasks.return_value = [
            {"id": "t1", "title": "Test", "category": "general"},
        ]

        def bad_callback(event, data):
            raise RuntimeError("callback exploded")

        listener = EventListener(coord, on_event=bad_callback)
        # Should not raise despite callback error
        ingested = listener.poll_new_tasks()
        assert len(ingested) == 1
