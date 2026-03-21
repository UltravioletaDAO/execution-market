"""
Tests for SwarmStatePersistence and RetryBackoff.

Verifies:
- Atomic state save/load cycle
- Schema versioning and compatibility
- Backoff timing and exponential delay
- Corruption recovery (backup file)
- TTL-based state expiry
- Edge cases (empty state, missing files, etc.)
"""

import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from swarm.state_persistence import (
    SwarmStatePersistence,
    PersistedState,
    RetryBackoff,
    SCHEMA_VERSION,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_state_dir():
    """Create a temporary directory for state files."""
    with tempfile.TemporaryDirectory(prefix="swarm_test_") as d:
        yield d


@pytest.fixture
def persistence(tmp_state_dir):
    """SwarmStatePersistence pointing at a temp directory."""
    return SwarmStatePersistence(state_dir=tmp_state_dir)


@pytest.fixture
def backoff():
    """Fresh RetryBackoff instance."""
    return RetryBackoff()


@pytest.fixture
def sample_state():
    """Sample PersistedState with realistic data."""
    return PersistedState(
        pending_tasks=[
            {
                "task_id": "t1",
                "title": "Photo verification",
                "categories": ["photo"],
                "bounty_usd": 2.50,
                "status": "pending",
            },
            {
                "task_id": "t2",
                "title": "Data collection",
                "categories": ["data"],
                "bounty_usd": 5.00,
                "status": "pending",
            },
        ],
        assigned_tasks=[
            {
                "task_id": "t3",
                "title": "Physical presence",
                "agent_id": 101,
                "status": "assigned",
            },
        ],
        total_ingested=100,
        total_assigned=85,
        total_completed=75,
        total_failed=5,
        total_expired=3,
        total_bounty_earned=450.50,
        agent_reputations={
            "101": {"on_chain_score": 85, "internal_score": 72},
            "102": {"on_chain_score": 90, "internal_score": 88},
        },
    )


# ─── PersistedState Tests ─────────────────────────────────────────────────────


class TestPersistedState:
    """Test PersistedState data class."""

    def test_default_state(self):
        state = PersistedState()
        assert state.schema_version == SCHEMA_VERSION
        assert state.pending_tasks == []
        assert state.total_ingested == 0
        assert state.total_bounty_earned == 0.0

    def test_to_dict_roundtrip(self, sample_state):
        data = sample_state.to_dict()
        restored = PersistedState.from_dict(data)
        assert restored.total_ingested == 100
        assert restored.total_completed == 75
        assert len(restored.pending_tasks) == 2
        assert len(restored.assigned_tasks) == 1
        assert restored.total_bounty_earned == 450.50

    def test_to_dict_structure(self, sample_state):
        data = sample_state.to_dict()
        assert "schema_version" in data
        assert "counters" in data
        assert data["counters"]["total_ingested"] == 100
        assert len(data["pending_tasks"]) == 2

    def test_from_dict_missing_fields(self):
        """Missing fields should use defaults."""
        state = PersistedState.from_dict({"schema_version": 1})
        assert state.pending_tasks == []
        assert state.total_ingested == 0
        assert state.agent_reputations == {}

    def test_from_dict_empty(self):
        state = PersistedState.from_dict({})
        assert state.schema_version == 1
        assert state.total_completed == 0


# ─── RetryBackoff Tests ───────────────────────────────────────────────────────


class TestRetryBackoff:
    """Test exponential backoff for task retries."""

    def test_first_attempt_delay(self, backoff):
        delay = backoff.record_failure("t1", attempt=1)
        assert delay == 30  # BASE_DELAY_SECONDS

    def test_exponential_increase(self, backoff):
        d1 = backoff.record_failure("t1", attempt=1)
        d2 = backoff.record_failure("t1", attempt=2)
        d3 = backoff.record_failure("t1", attempt=3)
        assert d1 == 30
        assert d2 == 60
        assert d3 == 120

    def test_max_delay_cap(self, backoff):
        delay = backoff.record_failure("t1", attempt=10)
        assert delay == 300  # MAX_DELAY_SECONDS

    def test_is_ready_no_backoff(self, backoff):
        """Tasks without backoff records are always ready."""
        assert backoff.is_ready("unknown-task") is True

    def test_is_ready_before_window(self, backoff):
        """Task in active backoff should not be ready."""
        backoff.record_failure("t1", attempt=1)  # 30s delay
        assert backoff.is_ready("t1") is False

    def test_is_ready_after_window(self, backoff):
        """Task past its backoff window should be ready."""
        backoff.record_failure("t1", attempt=1)
        # Manually set next_retry to the past
        backoff._backoffs["t1"]["next_retry_at"] = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
        ).isoformat()
        assert backoff.is_ready("t1") is True

    def test_clear_removes_entry(self, backoff):
        backoff.record_failure("t1", attempt=1)
        assert "t1" in backoff._backoffs
        backoff.clear("t1")
        assert "t1" not in backoff._backoffs
        assert backoff.is_ready("t1") is True

    def test_clear_nonexistent_ok(self, backoff):
        """Clearing a non-existent entry should not raise."""
        backoff.clear("nonexistent")

    def test_get_status(self, backoff):
        backoff.record_failure("t1", attempt=2)
        status = backoff.get_status("t1")
        assert status is not None
        assert status["attempt"] == 2
        assert status["delay_seconds"] == 60
        assert "next_retry_at" in status

    def test_get_status_nonexistent(self, backoff):
        assert backoff.get_status("missing") is None

    def test_get_all(self, backoff):
        backoff.record_failure("t1", attempt=1)
        backoff.record_failure("t2", attempt=2)
        all_entries = backoff.get_all()
        assert len(all_entries) == 2
        assert "t1" in all_entries
        assert "t2" in all_entries

    def test_restore(self, backoff):
        """Restore backoff state from persisted data."""
        data = {
            "t1": {
                "next_retry_at": (
                    datetime.now(timezone.utc) + timedelta(seconds=60)
                ).isoformat(),
                "attempt": 2,
                "delay_seconds": 60,
            }
        }
        backoff.restore(data)
        assert backoff.is_ready("t1") is False
        assert backoff.get_status("t1")["attempt"] == 2

    def test_cleanup_expired(self, backoff):
        """Old backoff entries should be cleaned up."""
        # Add an old entry
        backoff._backoffs["old-task"] = {
            "next_retry_at": (
                datetime.now(timezone.utc) - timedelta(hours=48)
            ).isoformat(),
            "attempt": 3,
            "delay_seconds": 120,
        }
        # Add a recent entry
        backoff.record_failure("new-task", attempt=1)

        removed = backoff.cleanup_expired(max_age_hours=24.0)
        assert removed == 1
        assert "old-task" not in backoff._backoffs
        assert "new-task" in backoff._backoffs

    def test_pending_count(self, backoff):
        """Count tasks currently waiting for backoff to expire."""
        backoff.record_failure("t1", attempt=1)  # Active backoff
        backoff.record_failure("t2", attempt=1)  # Active backoff
        # Add one that's already past
        backoff._backoffs["t3"] = {
            "next_retry_at": (
                datetime.now(timezone.utc) - timedelta(seconds=1)
            ).isoformat(),
            "attempt": 1,
            "delay_seconds": 30,
        }
        assert backoff.pending_count == 2  # t1 and t2 are pending, t3 is past

    def test_multiple_tasks_independent(self, backoff):
        """Different tasks have independent backoff windows."""
        backoff.record_failure("t1", attempt=1)  # 30s
        backoff.record_failure("t2", attempt=3)  # 120s

        s1 = backoff.get_status("t1")
        s2 = backoff.get_status("t2")
        assert s1["delay_seconds"] == 30
        assert s2["delay_seconds"] == 120


# ─── SwarmStatePersistence Tests ──────────────────────────────────────────────


class TestSwarmStatePersistence:
    """Test file-based state persistence."""

    def test_creates_directory(self, tmp_state_dir):
        subdir = os.path.join(tmp_state_dir, "nested", "deep")
        SwarmStatePersistence(state_dir=subdir)
        assert os.path.isdir(subdir)

    def test_save_and_load(self, persistence, sample_state):
        """Full save/load cycle preserves data."""
        assert persistence.save(sample_state) is True

        loaded = persistence.load()
        assert loaded is not None
        assert loaded.total_ingested == 100
        assert loaded.total_completed == 75
        assert len(loaded.pending_tasks) == 2
        assert loaded.total_bounty_earned == 450.50
        assert loaded.saved_at != ""  # Timestamp was set

    def test_save_creates_file(self, persistence, sample_state):
        persistence.save(sample_state)
        assert persistence.state_file.exists()

    def test_save_creates_backup_on_update(self, persistence, sample_state):
        """Second save should create a backup of the first."""
        persistence.save(sample_state)
        assert persistence.state_file.exists()
        assert not persistence.backup_file.exists()

        # Save again
        sample_state.total_ingested = 200
        persistence.save(sample_state)
        assert persistence.state_file.exists()
        assert persistence.backup_file.exists()

        # Backup should have old data
        with open(persistence.backup_file) as f:
            backup_data = json.load(f)
        assert backup_data["counters"]["total_ingested"] == 100

    def test_load_nonexistent_returns_none(self, persistence):
        assert persistence.load() is None

    def test_load_falls_back_to_backup(self, persistence, sample_state):
        """If main state file is missing, load from backup."""
        persistence.save(sample_state)
        sample_state.total_ingested = 200
        persistence.save(sample_state)

        # Delete main, keep backup
        persistence.state_file.unlink()

        loaded = persistence.load()
        assert loaded is not None
        assert loaded.total_ingested == 100  # From backup

    def test_load_corrupted_returns_none(self, persistence):
        """Corrupted JSON should not crash."""
        persistence.state_file.write_text("not valid json {{{")
        assert persistence.load() is None

    def test_load_rejects_future_schema(self, persistence):
        """State with newer schema version should be rejected."""
        data = {
            "schema_version": 999,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        persistence.state_file.write_text(json.dumps(data))
        assert persistence.load() is None

    def test_load_rejects_stale_state(self, persistence, sample_state):
        """State older than max_age_hours should be rejected."""
        sample_state.saved_at = (
            datetime.now(timezone.utc) - timedelta(hours=100)
        ).isoformat()

        # Save with the old timestamp
        with open(persistence.state_file, "w") as f:
            json.dump(sample_state.to_dict(), f)

        loaded = persistence.load(max_age_hours=48.0)
        assert loaded is None

    def test_load_accepts_recent_state(self, persistence, sample_state):
        """State within max_age_hours should be accepted."""
        persistence.save(sample_state)
        loaded = persistence.load(max_age_hours=48.0)
        assert loaded is not None

    def test_delete(self, persistence, sample_state):
        persistence.save(sample_state)
        sample_state.total_ingested = 200
        persistence.save(sample_state)

        assert persistence.state_file.exists()
        assert persistence.backup_file.exists()

        result = persistence.delete()
        assert result is True
        assert not persistence.state_file.exists()
        assert not persistence.backup_file.exists()

    def test_delete_no_files(self, persistence):
        assert persistence.delete() is False

    def test_get_info_empty(self, persistence):
        info = persistence.get_info()
        assert info["has_state"] is False
        assert "state_dir" in info

    def test_get_info_with_state(self, persistence, sample_state):
        persistence.save(sample_state)
        info = persistence.get_info()
        assert info["has_state"] is True
        assert info["size_bytes"] > 0
        assert "modified_at" in info

    def test_atomic_write_survives_corruption(self, persistence, sample_state):
        """If a write fails mid-way, the old state should be recoverable via backup."""
        persistence.save(sample_state)
        original_file = persistence.state_file
        assert original_file.exists()

        # Read original content for verification
        with open(original_file) as f:
            original_data = json.load(f)
        assert original_data["counters"]["total_ingested"] == 100

        # The save method catches exceptions and returns False on failure
        # We verify that partial failure doesn't corrupt the existing state
        _real_replace = os.replace
        call_count = [0]

        def patched_replace(src, dst):
            call_count[0] += 1
            if call_count[0] == 2:  # Fail on atomic rename (temp→state)
                raise OSError("disk full")
            return _real_replace(src, dst)

        with patch("os.replace", side_effect=patched_replace):
            result = persistence.save(PersistedState(total_ingested=999))

        assert result is False  # Save reported failure
        # The backup file should have the original data (first replace succeeded)
        assert persistence.backup_file.exists()
        with open(persistence.backup_file) as f:
            backup_data = json.load(f)
        assert backup_data["counters"]["total_ingested"] == 100

    def test_save_empty_state(self, persistence):
        """Empty state should save and load cleanly."""
        state = PersistedState()
        assert persistence.save(state) is True
        loaded = persistence.load()
        assert loaded is not None
        assert loaded.pending_tasks == []
        assert loaded.total_ingested == 0

    def test_retry_backoffs_persist(self, persistence):
        """RetryBackoff data should survive save/load."""
        state = PersistedState(
            retry_backoffs={
                "t1": {
                    "next_retry_at": "2026-03-16T05:00:00+00:00",
                    "attempt": 2,
                    "delay_seconds": 60,
                },
            }
        )
        persistence.save(state)
        loaded = persistence.load()
        assert "t1" in loaded.retry_backoffs
        assert loaded.retry_backoffs["t1"]["attempt"] == 2

    def test_agent_reputations_persist(self, persistence, sample_state):
        persistence.save(sample_state)
        loaded = persistence.load()
        assert "101" in loaded.agent_reputations
        assert loaded.agent_reputations["101"]["on_chain_score"] == 85


# ─── Integration: BackOff + Persistence ───────────────────────────────────────


class TestBackoffPersistenceIntegration:
    """Test that backoff state survives save/load cycles."""

    def test_backoff_roundtrip(self, persistence):
        backoff = RetryBackoff()
        backoff.record_failure("t1", attempt=1)
        backoff.record_failure("t2", attempt=3)

        # Save
        state = PersistedState(retry_backoffs=backoff.get_all())
        persistence.save(state)

        # Load into new backoff
        loaded = persistence.load()
        new_backoff = RetryBackoff()
        new_backoff.restore(loaded.retry_backoffs)

        assert new_backoff.get_status("t1") is not None
        assert new_backoff.get_status("t2")["attempt"] == 3
        assert new_backoff.get_status("t2")["delay_seconds"] == 120
