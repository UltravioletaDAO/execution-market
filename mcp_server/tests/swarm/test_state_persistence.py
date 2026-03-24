"""
Tests for SwarmStatePersistence + RetryBackoff
================================================

Covers:
- PersistedState: serialization round-trip, defaults, from_dict edge cases
- RetryBackoff: exponential delay, readiness check, cleanup, restore
- SwarmStatePersistence: save/load/delete, atomic writes, age filtering,
  schema version handling, backup recovery, concurrent save safety
"""

import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from swarm.state_persistence import (
    PersistedState,
    RetryBackoff,
    SwarmStatePersistence,
    SCHEMA_VERSION,
)


# ---------------------------------------------------------------------------
# PersistedState
# ---------------------------------------------------------------------------


class TestPersistedState:
    """Test PersistedState dataclass and serialization."""

    def test_defaults(self):
        state = PersistedState()
        assert state.schema_version == SCHEMA_VERSION
        assert state.pending_tasks == []
        assert state.assigned_tasks == []
        assert state.total_ingested == 0
        assert state.total_bounty_earned == 0.0
        assert state.agent_reputations == {}
        assert state.retry_backoffs == {}

    def test_to_dict_structure(self):
        state = PersistedState(
            pending_tasks=[{"id": "t1"}],
            total_ingested=5,
            total_bounty_earned=1.25,
        )
        d = state.to_dict()
        assert d["schema_version"] == SCHEMA_VERSION
        assert len(d["pending_tasks"]) == 1
        assert d["counters"]["total_ingested"] == 5
        assert d["counters"]["total_bounty_earned"] == 1.25

    def test_round_trip(self):
        original = PersistedState(
            pending_tasks=[{"id": "t1"}, {"id": "t2"}],
            assigned_tasks=[{"id": "t3"}],
            total_ingested=10,
            total_assigned=5,
            total_completed=3,
            total_failed=1,
            total_expired=1,
            total_bounty_earned=2.50,
            agent_reputations={"agent-1": {"on_chain": 80, "internal": 90}},
            retry_backoffs={"t4": {"next_retry_at": "2026-01-01T00:00:00+00:00", "attempt": 2}},
        )
        d = original.to_dict()
        restored = PersistedState.from_dict(d)

        assert restored.pending_tasks == original.pending_tasks
        assert restored.assigned_tasks == original.assigned_tasks
        assert restored.total_ingested == original.total_ingested
        assert restored.total_assigned == original.total_assigned
        assert restored.total_completed == original.total_completed
        assert restored.total_failed == original.total_failed
        assert restored.total_expired == original.total_expired
        assert restored.total_bounty_earned == original.total_bounty_earned
        assert restored.agent_reputations == original.agent_reputations
        assert restored.retry_backoffs == original.retry_backoffs

    def test_from_dict_missing_keys(self):
        state = PersistedState.from_dict({})
        assert state.schema_version == 1
        assert state.pending_tasks == []
        assert state.total_ingested == 0

    def test_from_dict_extra_keys_ignored(self):
        state = PersistedState.from_dict({
            "schema_version": 1,
            "unknown_key": "should_not_crash",
            "counters": {"total_ingested": 7},
        })
        assert state.total_ingested == 7

    def test_saved_at_preserved(self):
        state = PersistedState()
        state.saved_at = "2026-03-24T05:00:00+00:00"
        d = state.to_dict()
        assert d["saved_at"] == "2026-03-24T05:00:00+00:00"
        restored = PersistedState.from_dict(d)
        assert restored.saved_at == "2026-03-24T05:00:00+00:00"


# ---------------------------------------------------------------------------
# RetryBackoff
# ---------------------------------------------------------------------------


class TestRetryBackoff:
    """Test exponential backoff logic."""

    def test_first_failure_base_delay(self):
        rb = RetryBackoff()
        delay = rb.record_failure("task-1", attempt=1)
        assert delay == 30.0  # BASE_DELAY_SECONDS

    def test_second_failure_doubled(self):
        rb = RetryBackoff()
        delay = rb.record_failure("task-1", attempt=2)
        assert delay == 60.0  # 30 * 2^1

    def test_third_failure_quadrupled(self):
        rb = RetryBackoff()
        delay = rb.record_failure("task-1", attempt=3)
        assert delay == 120.0  # 30 * 2^2

    def test_max_delay_capped(self):
        rb = RetryBackoff()
        delay = rb.record_failure("task-1", attempt=10)
        assert delay == 300.0  # MAX_DELAY_SECONDS

    def test_is_ready_before_record(self):
        rb = RetryBackoff()
        assert rb.is_ready("task-1") is True  # No backoff recorded

    def test_is_ready_after_failure(self):
        rb = RetryBackoff()
        rb.record_failure("task-1", attempt=1)
        # Just recorded, not ready yet (30s delay)
        assert rb.is_ready("task-1") is False

    def test_clear_removes_backoff(self):
        rb = RetryBackoff()
        rb.record_failure("task-1", attempt=1)
        rb.clear("task-1")
        assert rb.is_ready("task-1") is True

    def test_clear_nonexistent_ok(self):
        rb = RetryBackoff()
        rb.clear("nonexistent")  # Should not raise

    def test_get_status(self):
        rb = RetryBackoff()
        rb.record_failure("task-1", attempt=2)
        status = rb.get_status("task-1")
        assert status is not None
        assert status["attempt"] == 2
        assert status["delay_seconds"] == 60.0

    def test_get_status_nonexistent(self):
        rb = RetryBackoff()
        assert rb.get_status("unknown") is None

    def test_get_all(self):
        rb = RetryBackoff()
        rb.record_failure("t1", attempt=1)
        rb.record_failure("t2", attempt=2)
        all_backoffs = rb.get_all()
        assert "t1" in all_backoffs
        assert "t2" in all_backoffs

    def test_restore(self):
        rb = RetryBackoff()
        rb.record_failure("t1", attempt=1)
        saved = rb.get_all()

        rb2 = RetryBackoff()
        rb2.restore(saved)
        assert rb2.get_status("t1") is not None

    def test_cleanup_expired(self):
        rb = RetryBackoff()
        # Fake an old entry
        old_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        rb._backoffs["old-task"] = {
            "next_retry_at": old_time,
            "attempt": 1,
            "delay_seconds": 30,
        }
        rb.record_failure("new-task", attempt=1)

        removed = rb.cleanup_expired(max_age_hours=24.0)
        assert removed == 1
        assert "old-task" not in rb._backoffs
        assert "new-task" in rb._backoffs

    def test_pending_count(self):
        rb = RetryBackoff()
        rb.record_failure("t1", attempt=1)
        rb.record_failure("t2", attempt=2)
        assert rb.pending_count == 2  # Both are in backoff

    def test_independent_tasks(self):
        rb = RetryBackoff()
        rb.record_failure("t1", attempt=1)
        rb.record_failure("t2", attempt=3)
        s1 = rb.get_status("t1")
        s2 = rb.get_status("t2")
        assert s1["delay_seconds"] == 30
        assert s2["delay_seconds"] == 120


# ---------------------------------------------------------------------------
# SwarmStatePersistence
# ---------------------------------------------------------------------------


class TestSwarmStatePersistence:
    """Test file-based state persistence."""

    def test_save_creates_file(self, tmp_path):
        p = SwarmStatePersistence(str(tmp_path))
        state = PersistedState(total_ingested=5)
        assert p.save(state)
        assert (tmp_path / "coordinator_state.json").exists()

    def test_save_sets_saved_at(self, tmp_path):
        p = SwarmStatePersistence(str(tmp_path))
        state = PersistedState()
        p.save(state)
        assert state.saved_at != ""

    def test_load_after_save(self, tmp_path):
        p = SwarmStatePersistence(str(tmp_path))
        state = PersistedState(
            pending_tasks=[{"id": "t1"}],
            total_ingested=10,
            total_bounty_earned=3.50,
        )
        p.save(state)

        loaded = p.load()
        assert loaded is not None
        assert loaded.pending_tasks == [{"id": "t1"}]
        assert loaded.total_ingested == 10
        assert loaded.total_bounty_earned == 3.50

    def test_load_no_file(self, tmp_path):
        p = SwarmStatePersistence(str(tmp_path))
        loaded = p.load()
        assert loaded is None

    def test_load_corrupted_file(self, tmp_path):
        p = SwarmStatePersistence(str(tmp_path))
        # Write invalid JSON
        (tmp_path / "coordinator_state.json").write_text("NOT JSON!!!")
        loaded = p.load()
        assert loaded is None

    def test_backup_created_on_save(self, tmp_path):
        p = SwarmStatePersistence(str(tmp_path))

        # First save
        state1 = PersistedState(total_ingested=1)
        p.save(state1)
        assert not (tmp_path / "coordinator_state.backup.json").exists()

        # Second save creates backup
        state2 = PersistedState(total_ingested=2)
        p.save(state2)
        assert (tmp_path / "coordinator_state.backup.json").exists()

    def test_load_falls_back_to_backup(self, tmp_path):
        p = SwarmStatePersistence(str(tmp_path))

        # Save state
        state = PersistedState(total_ingested=42)
        p.save(state)

        # Save again to create backup
        state2 = PersistedState(total_ingested=99)
        p.save(state2)

        # Delete primary
        (tmp_path / "coordinator_state.json").unlink()

        # Should load from backup
        loaded = p.load()
        assert loaded is not None
        assert loaded.total_ingested == 42  # From backup, not primary

    def test_load_rejects_old_state(self, tmp_path):
        p = SwarmStatePersistence(str(tmp_path))

        # Save state with old timestamp
        state = PersistedState(total_ingested=5)
        state.saved_at = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        d = state.to_dict()
        (tmp_path / "coordinator_state.json").write_text(json.dumps(d))

        loaded = p.load(max_age_hours=48.0)
        assert loaded is None

    def test_load_accepts_fresh_state(self, tmp_path):
        p = SwarmStatePersistence(str(tmp_path))

        state = PersistedState(total_ingested=5)
        p.save(state)

        loaded = p.load(max_age_hours=48.0)
        assert loaded is not None
        assert loaded.total_ingested == 5

    def test_load_rejects_future_schema(self, tmp_path):
        p = SwarmStatePersistence(str(tmp_path))

        d = {"schema_version": SCHEMA_VERSION + 1, "saved_at": datetime.now(timezone.utc).isoformat()}
        (tmp_path / "coordinator_state.json").write_text(json.dumps(d))

        loaded = p.load()
        assert loaded is None

    def test_delete(self, tmp_path):
        p = SwarmStatePersistence(str(tmp_path))

        state = PersistedState()
        p.save(state)
        p.save(state)  # Creates backup too

        assert p.delete()
        assert not (tmp_path / "coordinator_state.json").exists()
        assert not (tmp_path / "coordinator_state.backup.json").exists()

    def test_delete_no_files(self, tmp_path):
        p = SwarmStatePersistence(str(tmp_path))
        assert not p.delete()

    def test_get_info_empty(self, tmp_path):
        p = SwarmStatePersistence(str(tmp_path))
        info = p.get_info()
        assert info["has_state"] is False

    def test_get_info_with_state(self, tmp_path):
        p = SwarmStatePersistence(str(tmp_path))
        p.save(PersistedState())
        info = p.get_info()
        assert info["has_state"] is True
        assert info["size_bytes"] > 0

    def test_get_info_with_backup(self, tmp_path):
        p = SwarmStatePersistence(str(tmp_path))
        p.save(PersistedState())
        p.save(PersistedState())
        info = p.get_info()
        assert info.get("has_backup") is True

    def test_creates_state_dir(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "dir"
        p = SwarmStatePersistence(str(nested))
        assert nested.exists()

    def test_atomic_write_no_corruption(self, tmp_path):
        """Save should be atomic — state file should always be valid JSON."""
        p = SwarmStatePersistence(str(tmp_path))

        # Save multiple times rapidly
        for i in range(10):
            state = PersistedState(total_ingested=i)
            p.save(state)

        # Final load should work
        loaded = p.load()
        assert loaded is not None
        assert loaded.total_ingested == 9
