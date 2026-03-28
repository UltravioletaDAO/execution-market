"""
Test Suite: SwarmStatePersistence — Durable State for Swarm Coordinator
=========================================================================

Tests cover:
    1. PersistedState (to_dict, from_dict, round-trip)
    2. RetryBackoff (exponential backoff, is_ready, cleanup)
    3. SwarmStatePersistence (save, load, atomic writes, staleness)
    4. Edge cases (corruption, schema version, backup fallback)
"""

import json
import os
import tempfile
from datetime import datetime, timezone, timedelta

from mcp_server.swarm.state_persistence import (
    PersistedState,
    RetryBackoff,
    SwarmStatePersistence,
    SCHEMA_VERSION,
)


# ══════════════════════════════════════════════════════════════
# PersistedState Tests
# ══════════════════════════════════════════════════════════════


class TestPersistedState:
    def test_defaults(self):
        state = PersistedState()
        assert state.schema_version == SCHEMA_VERSION
        assert state.total_ingested == 0
        assert state.pending_tasks == []

    def test_to_dict(self):
        state = PersistedState(
            total_ingested=10,
            total_completed=5,
            pending_tasks=[{"id": "t1"}],
        )
        d = state.to_dict()
        assert d["counters"]["total_ingested"] == 10
        assert d["counters"]["total_completed"] == 5
        assert len(d["pending_tasks"]) == 1

    def test_from_dict(self):
        data = {
            "schema_version": 1,
            "saved_at": "2026-03-28T00:00:00Z",
            "pending_tasks": [{"id": "t1"}, {"id": "t2"}],
            "assigned_tasks": [{"id": "t3"}],
            "counters": {
                "total_ingested": 20,
                "total_assigned": 15,
                "total_completed": 10,
                "total_failed": 2,
                "total_expired": 3,
                "total_bounty_earned": 42.50,
            },
            "agent_reputations": {"42": {"score": 85}},
            "retry_backoffs": {},
        }
        state = PersistedState.from_dict(data)
        assert state.total_ingested == 20
        assert state.total_bounty_earned == 42.50
        assert len(state.pending_tasks) == 2

    def test_round_trip(self):
        original = PersistedState(
            total_ingested=100,
            total_completed=80,
            pending_tasks=[{"id": "t1"}],
            agent_reputations={"42": {"on_chain": 85}},
        )
        data = original.to_dict()
        restored = PersistedState.from_dict(data)
        assert restored.total_ingested == 100
        assert restored.total_completed == 80
        assert len(restored.pending_tasks) == 1

    def test_from_dict_missing_fields(self):
        state = PersistedState.from_dict({})
        assert state.total_ingested == 0
        assert state.pending_tasks == []


# ══════════════════════════════════════════════════════════════
# RetryBackoff Tests
# ══════════════════════════════════════════════════════════════


class TestRetryBackoff:
    def test_first_attempt_delay(self):
        backoff = RetryBackoff()
        delay = backoff.record_failure("t1", attempt=1)
        assert delay == 30.0  # BASE_DELAY_SECONDS

    def test_second_attempt_delay(self):
        backoff = RetryBackoff()
        delay = backoff.record_failure("t1", attempt=2)
        assert delay == 60.0  # 30 * 2^1

    def test_third_attempt_delay(self):
        backoff = RetryBackoff()
        delay = backoff.record_failure("t1", attempt=3)
        assert delay == 120.0  # 30 * 2^2

    def test_max_delay_cap(self):
        backoff = RetryBackoff()
        delay = backoff.record_failure("t1", attempt=10)
        assert delay == 300.0  # MAX_DELAY_SECONDS

    def test_is_ready_no_backoff(self):
        backoff = RetryBackoff()
        assert backoff.is_ready("t1") is True

    def test_is_ready_in_backoff(self):
        backoff = RetryBackoff()
        backoff.record_failure("t1", attempt=1)
        # Just recorded → should NOT be ready (30s delay)
        assert backoff.is_ready("t1") is False

    def test_clear_removes_backoff(self):
        backoff = RetryBackoff()
        backoff.record_failure("t1", attempt=1)
        backoff.clear("t1")
        assert backoff.is_ready("t1") is True

    def test_get_status(self):
        backoff = RetryBackoff()
        backoff.record_failure("t1", attempt=2)
        status = backoff.get_status("t1")
        assert status is not None
        assert status["attempt"] == 2
        assert status["delay_seconds"] == 60.0

    def test_get_status_missing(self):
        backoff = RetryBackoff()
        assert backoff.get_status("nonexistent") is None

    def test_get_all(self):
        backoff = RetryBackoff()
        backoff.record_failure("t1", attempt=1)
        backoff.record_failure("t2", attempt=2)
        all_backoffs = backoff.get_all()
        assert len(all_backoffs) == 2

    def test_restore(self):
        backoff = RetryBackoff()
        now = datetime.now(timezone.utc)
        data = {
            "t1": {
                "next_retry_at": (now + timedelta(seconds=30)).isoformat(),
                "attempt": 1,
                "delay_seconds": 30,
            }
        }
        backoff.restore(data)
        assert not backoff.is_ready("t1")

    def test_cleanup_expired(self):
        backoff = RetryBackoff()
        old_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        backoff._backoffs = {
            "old": {"next_retry_at": old_time, "attempt": 1, "delay_seconds": 30},
            "recent": {
                "next_retry_at": (
                    datetime.now(timezone.utc) + timedelta(seconds=30)
                ).isoformat(),
                "attempt": 1,
                "delay_seconds": 30,
            },
        }
        removed = backoff.cleanup_expired(max_age_hours=24.0)
        assert removed == 1
        assert "old" not in backoff._backoffs
        assert "recent" in backoff._backoffs

    def test_pending_count(self):
        backoff = RetryBackoff()
        backoff.record_failure("t1", attempt=1)  # In backoff
        backoff.record_failure("t2", attempt=2)  # In backoff
        assert backoff.pending_count == 2


# ══════════════════════════════════════════════════════════════
# SwarmStatePersistence Tests
# ══════════════════════════════════════════════════════════════


class TestSwarmStatePersistence:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = SwarmStatePersistence(tmpdir)
            state = PersistedState(
                total_ingested=50,
                total_completed=30,
                pending_tasks=[{"id": "t1"}],
            )
            assert persistence.save(state) is True

            loaded = persistence.load()
            assert loaded is not None
            assert loaded.total_ingested == 50
            assert loaded.total_completed == 30

    def test_load_no_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = SwarmStatePersistence(tmpdir)
            loaded = persistence.load()
            assert loaded is None

    def test_atomic_backup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = SwarmStatePersistence(tmpdir)

            # Save first state
            state1 = PersistedState(total_ingested=10)
            persistence.save(state1)

            # Save second state → first should become backup
            state2 = PersistedState(total_ingested=20)
            persistence.save(state2)

            assert persistence.backup_file.exists()

    def test_load_corrupted_falls_back(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = SwarmStatePersistence(tmpdir)

            # Write corrupt primary
            with open(persistence.state_file, "w") as f:
                f.write("not valid json{{{")

            loaded = persistence.load()
            assert loaded is None

    def test_load_backup_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = SwarmStatePersistence(tmpdir)

            # Only backup exists
            state = PersistedState(total_ingested=42)
            data = state.to_dict()
            data["saved_at"] = datetime.now(timezone.utc).isoformat()
            with open(persistence.backup_file, "w") as f:
                json.dump(data, f)

            loaded = persistence.load()
            assert loaded is not None
            assert loaded.total_ingested == 42

    def test_load_stale_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = SwarmStatePersistence(tmpdir)

            # Create old state
            old_time = (datetime.now(timezone.utc) - timedelta(hours=100)).isoformat()
            data = PersistedState(total_ingested=10).to_dict()
            data["saved_at"] = old_time
            with open(persistence.state_file, "w") as f:
                json.dump(data, f)

            loaded = persistence.load(max_age_hours=48.0)
            assert loaded is None

    def test_load_future_schema(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = SwarmStatePersistence(tmpdir)

            data = {
                "schema_version": 999,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(persistence.state_file, "w") as f:
                json.dump(data, f)

            loaded = persistence.load()
            assert loaded is None

    def test_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = SwarmStatePersistence(tmpdir)
            state = PersistedState(total_ingested=10)
            persistence.save(state)

            assert persistence.delete() is True
            assert not persistence.state_file.exists()

    def test_delete_no_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = SwarmStatePersistence(tmpdir)
            assert persistence.delete() is False

    def test_get_info_no_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = SwarmStatePersistence(tmpdir)
            info = persistence.get_info()
            assert info["has_state"] is False

    def test_get_info_with_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = SwarmStatePersistence(tmpdir)
            state = PersistedState(total_ingested=10)
            persistence.save(state)

            info = persistence.get_info()
            assert info["has_state"] is True
            assert info["size_bytes"] > 0

    def test_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "deep", "nested", "dir")
            SwarmStatePersistence(nested)  # side effect: creates directory
            assert os.path.isdir(nested)
