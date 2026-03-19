"""
Tests for SwarmStatePersistence & RetryBackoff — durable state for swarm coordination.

Covers:
- PersistedState serialization (to_dict/from_dict)
- RetryBackoff exponential backoff logic
- SwarmStatePersistence save/load/delete
- Atomic writes and backup
- Schema version checking
- Age-based state expiry
"""

import json
import os
import pytest
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

from mcp_server.swarm.state_persistence import (
    SwarmStatePersistence,
    PersistedState,
    RetryBackoff,
    SCHEMA_VERSION,
)


# ─── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def tmp_dir():
    """Temporary directory for state files."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def persistence(tmp_dir):
    return SwarmStatePersistence(state_dir=tmp_dir)


@pytest.fixture
def backoff():
    return RetryBackoff()


# ─── PersistedState Model ─────────────────────────────────────────


class TestPersistedState:
    """State serialization and deserialization."""

    def test_defaults(self):
        state = PersistedState()
        assert state.schema_version == SCHEMA_VERSION
        assert state.pending_tasks == []
        assert state.assigned_tasks == []
        assert state.total_ingested == 0
        assert state.total_bounty_earned == 0.0

    def test_to_dict(self):
        state = PersistedState(
            pending_tasks=[{"id": "t1"}],
            assigned_tasks=[{"id": "t2"}],
            total_ingested=10,
            total_completed=5,
            total_bounty_earned=12.50,
            agent_reputations={"1": {"score": 80}},
        )
        d = state.to_dict()
        assert d["schema_version"] == SCHEMA_VERSION
        assert len(d["pending_tasks"]) == 1
        assert d["counters"]["total_ingested"] == 10
        assert d["counters"]["total_completed"] == 5
        assert d["counters"]["total_bounty_earned"] == 12.50
        assert "1" in d["agent_reputations"]

    def test_from_dict_roundtrip(self):
        original = PersistedState(
            pending_tasks=[{"id": "t1"}, {"id": "t2"}],
            total_assigned=3,
            total_failed=1,
            agent_reputations={"42": {"avg": 4.5}},
            retry_backoffs={"t3": {"attempt": 2}},
        )
        d = original.to_dict()
        restored = PersistedState.from_dict(d)
        assert len(restored.pending_tasks) == 2
        assert restored.total_assigned == 3
        assert restored.total_failed == 1
        assert "42" in restored.agent_reputations
        assert "t3" in restored.retry_backoffs

    def test_from_dict_missing_fields(self):
        """Should handle missing fields gracefully."""
        state = PersistedState.from_dict({})
        assert state.pending_tasks == []
        assert state.total_ingested == 0

    def test_from_dict_legacy_no_counters(self):
        """Handle old format without nested counters."""
        state = PersistedState.from_dict({"saved_at": "2026-01-01"})
        assert state.total_ingested == 0


# ─── RetryBackoff ─────────────────────────────────────────────────


class TestRetryBackoff:
    """Exponential backoff for failed task routing."""

    def test_first_attempt_delay(self, backoff):
        delay = backoff.record_failure("t1", attempt=1)
        assert delay == 30.0  # BASE_DELAY_SECONDS

    def test_exponential_increase(self, backoff):
        d1 = backoff.record_failure("t1", attempt=1)
        d2 = backoff.record_failure("t1", attempt=2)
        d3 = backoff.record_failure("t1", attempt=3)
        assert d1 == 30.0
        assert d2 == 60.0
        assert d3 == 120.0

    def test_capped_at_max(self, backoff):
        delay = backoff.record_failure("t1", attempt=10)
        assert delay == 300.0  # MAX_DELAY_SECONDS

    def test_is_ready_new_task(self, backoff):
        """Task with no backoff should be ready."""
        assert backoff.is_ready("new-task") is True

    def test_is_ready_after_delay(self, backoff):
        """Task should be ready after its backoff window expires."""
        backoff.record_failure("t1", attempt=1)
        # Manually set next_retry_at to the past
        backoff._backoffs["t1"]["next_retry_at"] = (
            datetime.now(timezone.utc) - timedelta(seconds=60)
        ).isoformat()
        assert backoff.is_ready("t1") is True

    def test_not_ready_during_backoff(self, backoff):
        backoff.record_failure("t1", attempt=1)
        # Just recorded, should NOT be ready
        assert backoff.is_ready("t1") is False

    def test_clear_removes_backoff(self, backoff):
        backoff.record_failure("t1", attempt=1)
        backoff.clear("t1")
        assert backoff.is_ready("t1") is True
        assert backoff.get_status("t1") is None

    def test_clear_nonexistent_noop(self, backoff):
        backoff.clear("nonexistent")  # Should not raise

    def test_get_status(self, backoff):
        backoff.record_failure("t1", attempt=2)
        status = backoff.get_status("t1")
        assert status is not None
        assert status["attempt"] == 2
        assert status["delay_seconds"] == 60.0

    def test_get_all_for_persistence(self, backoff):
        backoff.record_failure("t1", attempt=1)
        backoff.record_failure("t2", attempt=3)
        all_data = backoff.get_all()
        assert "t1" in all_data
        assert "t2" in all_data

    def test_restore_from_persisted(self, backoff):
        data = {
            "t1": {
                "next_retry_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                "attempt": 2,
                "delay_seconds": 60,
            }
        }
        backoff.restore(data)
        assert backoff.is_ready("t1") is False

    def test_cleanup_expired(self, backoff):
        # Add old entry
        backoff._backoffs["old"] = {
            "next_retry_at": (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat(),
            "attempt": 1,
        }
        backoff._backoffs["recent"] = {
            "next_retry_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "attempt": 1,
        }
        removed = backoff.cleanup_expired(max_age_hours=24.0)
        assert removed == 1
        assert "old" not in backoff._backoffs
        assert "recent" in backoff._backoffs

    def test_pending_count(self, backoff):
        # Add 2 pending, 1 expired
        backoff.record_failure("t1", attempt=1)
        backoff.record_failure("t2", attempt=1)
        backoff._backoffs["t3"] = {
            "next_retry_at": (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat(),
            "attempt": 1,
        }
        assert backoff.pending_count == 2  # t1 and t2 are still pending


# ─── SwarmStatePersistence ────────────────────────────────────────


class TestSwarmStatePersistence:
    """File-based state persistence."""

    def test_save_creates_file(self, persistence, tmp_dir):
        state = PersistedState(pending_tasks=[{"id": "t1"}])
        result = persistence.save(state)
        assert result is True
        assert Path(tmp_dir, "coordinator_state.json").exists()

    def test_save_sets_saved_at(self, persistence):
        state = PersistedState()
        persistence.save(state)
        assert state.saved_at != ""

    def test_save_load_roundtrip(self, persistence):
        original = PersistedState(
            pending_tasks=[{"id": "t1"}, {"id": "t2"}],
            assigned_tasks=[{"id": "t3"}],
            total_ingested=100,
            total_completed=80,
            total_bounty_earned=45.50,
        )
        persistence.save(original)
        loaded = persistence.load()
        assert loaded is not None
        assert len(loaded.pending_tasks) == 2
        assert loaded.total_ingested == 100
        assert loaded.total_bounty_earned == 45.50

    def test_load_nonexistent_returns_none(self, tmp_dir):
        p = SwarmStatePersistence(state_dir=os.path.join(tmp_dir, "empty"))
        result = p.load()
        assert result is None

    def test_load_corrupted_returns_none(self, persistence, tmp_dir):
        # Write garbage
        with open(os.path.join(tmp_dir, "coordinator_state.json"), "w") as f:
            f.write("not json{{{")
        result = persistence.load()
        assert result is None

    def test_load_future_schema_returns_none(self, persistence, tmp_dir):
        """State with newer schema version should be rejected."""
        with open(os.path.join(tmp_dir, "coordinator_state.json"), "w") as f:
            json.dump({
                "schema_version": SCHEMA_VERSION + 1,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }, f)
        result = persistence.load()
        assert result is None

    def test_load_stale_state_returns_none(self, persistence, tmp_dir):
        """State older than max_age_hours should be rejected."""
        old_time = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        with open(os.path.join(tmp_dir, "coordinator_state.json"), "w") as f:
            json.dump({
                "schema_version": SCHEMA_VERSION,
                "saved_at": old_time,
                "pending_tasks": [],
            }, f)
        result = persistence.load(max_age_hours=48.0)
        assert result is None

    def test_save_creates_backup(self, persistence, tmp_dir):
        # Save twice to trigger backup
        state1 = PersistedState(pending_tasks=[{"id": "t1"}])
        persistence.save(state1)

        state2 = PersistedState(pending_tasks=[{"id": "t2"}])
        persistence.save(state2)

        assert Path(tmp_dir, "coordinator_state.backup.json").exists()

    def test_load_from_backup_if_primary_missing(self, persistence, tmp_dir):
        state = PersistedState(pending_tasks=[{"id": "backup-t"}])
        persistence.save(state)

        # Save again to create backup, then delete primary
        state2 = PersistedState(pending_tasks=[{"id": "primary-t"}])
        persistence.save(state2)

        # Delete primary
        os.unlink(os.path.join(tmp_dir, "coordinator_state.json"))

        loaded = persistence.load()
        assert loaded is not None
        # Should load from backup
        assert len(loaded.pending_tasks) >= 1

    def test_delete_removes_files(self, persistence, tmp_dir):
        state = PersistedState()
        persistence.save(state)
        persistence.save(state)  # Creates backup too

        result = persistence.delete()
        assert result is True
        assert not Path(tmp_dir, "coordinator_state.json").exists()
        assert not Path(tmp_dir, "coordinator_state.backup.json").exists()

    def test_delete_no_files_returns_false(self, persistence):
        result = persistence.delete()
        assert result is False

    def test_get_info_with_state(self, persistence, tmp_dir):
        state = PersistedState(pending_tasks=[{"id": "t1"}])
        persistence.save(state)

        info = persistence.get_info()
        assert info["has_state"] is True
        assert info["size_bytes"] > 0
        assert "modified_at" in info

    def test_get_info_no_state(self, persistence):
        info = persistence.get_info()
        assert info["has_state"] is False

    def test_concurrent_saves(self, persistence):
        """Multiple rapid saves should not corrupt state."""
        for i in range(10):
            state = PersistedState(
                pending_tasks=[{"id": f"t{i}"}],
                total_ingested=i,
            )
            assert persistence.save(state) is True

        loaded = persistence.load()
        assert loaded is not None
        assert loaded.total_ingested == 9  # Last save
