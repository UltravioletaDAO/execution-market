"""
SwarmStatePersistence — Durable state for the KK V2 swarm coordinator.

Saves and restores coordinator state (task queue, metrics, agent data)
to JSON files, enabling swarm survival across process restarts.

Design principles:
- Atomic writes (write temp + rename) to prevent corruption
- Schema versioning for forward compatibility
- Selective restore (skip stale data older than TTL)
- Minimal dependencies (stdlib only)

Usage:
    persistence = SwarmStatePersistence("/var/swarm/state")

    # Save state periodically
    persistence.save(coordinator)

    # Restore on startup
    state = persistence.load()
    if state:
        coordinator.restore_from(state)
"""

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("em.swarm.persistence")

SCHEMA_VERSION = 1
DEFAULT_STATE_DIR = os.path.expanduser("~/.em-swarm")


@dataclass
class PersistedState:
    """Snapshot of coordinator state for persistence."""

    schema_version: int = SCHEMA_VERSION
    saved_at: str = ""

    # Task queue
    pending_tasks: list[dict] = field(default_factory=list)
    assigned_tasks: list[dict] = field(default_factory=list)

    # Counters
    total_ingested: int = 0
    total_assigned: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_expired: int = 0
    total_bounty_earned: float = 0.0

    # Agent state
    agent_reputations: dict = field(
        default_factory=dict
    )  # agent_id → {on_chain, internal}

    # Retry backoffs
    retry_backoffs: dict = field(
        default_factory=dict
    )  # task_id → {next_retry_at, attempt}

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "saved_at": self.saved_at,
            "pending_tasks": self.pending_tasks,
            "assigned_tasks": self.assigned_tasks,
            "counters": {
                "total_ingested": self.total_ingested,
                "total_assigned": self.total_assigned,
                "total_completed": self.total_completed,
                "total_failed": self.total_failed,
                "total_expired": self.total_expired,
                "total_bounty_earned": self.total_bounty_earned,
            },
            "agent_reputations": self.agent_reputations,
            "retry_backoffs": self.retry_backoffs,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PersistedState":
        counters = data.get("counters", {})
        return cls(
            schema_version=data.get("schema_version", 1),
            saved_at=data.get("saved_at", ""),
            pending_tasks=data.get("pending_tasks", []),
            assigned_tasks=data.get("assigned_tasks", []),
            total_ingested=counters.get("total_ingested", 0),
            total_assigned=counters.get("total_assigned", 0),
            total_completed=counters.get("total_completed", 0),
            total_failed=counters.get("total_failed", 0),
            total_expired=counters.get("total_expired", 0),
            total_bounty_earned=counters.get("total_bounty_earned", 0.0),
            agent_reputations=data.get("agent_reputations", {}),
            retry_backoffs=data.get("retry_backoffs", {}),
        )


class RetryBackoff:
    """
    Exponential backoff tracker for task retry scheduling.

    Implements capped exponential backoff:
    - Attempt 1: 30s delay
    - Attempt 2: 60s delay
    - Attempt 3: 120s delay
    - Max: 300s (5 min)

    Usage:
        backoff = RetryBackoff()

        # After a failed routing attempt
        backoff.record_failure("task-123", attempt=1)

        # Before processing
        if backoff.is_ready("task-123"):
            # Process the task
        else:
            # Skip, not ready for retry yet
    """

    BASE_DELAY_SECONDS = 30
    MAX_DELAY_SECONDS = 300
    BACKOFF_FACTOR = 2.0

    def __init__(self):
        self._backoffs: dict[
            str, dict
        ] = {}  # task_id → {next_retry_at, attempt, delay}

    def record_failure(self, task_id: str, attempt: int) -> float:
        """
        Record a failed attempt and compute next retry time.

        Returns the delay in seconds before next retry.
        """
        delay = min(
            self.BASE_DELAY_SECONDS * (self.BACKOFF_FACTOR ** (attempt - 1)),
            self.MAX_DELAY_SECONDS,
        )
        next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay)

        self._backoffs[task_id] = {
            "next_retry_at": next_retry.isoformat(),
            "attempt": attempt,
            "delay_seconds": delay,
        }

        logger.debug(
            f"Task {task_id} retry scheduled in {delay:.0f}s (attempt {attempt})"
        )
        return delay

    def is_ready(self, task_id: str) -> bool:
        """Check if a task is ready for retry (past its backoff window)."""
        if task_id not in self._backoffs:
            return True

        entry = self._backoffs[task_id]
        next_retry = datetime.fromisoformat(entry["next_retry_at"])
        return datetime.now(timezone.utc) >= next_retry

    def clear(self, task_id: str) -> None:
        """Remove backoff tracking for a task (e.g., on success)."""
        self._backoffs.pop(task_id, None)

    def get_status(self, task_id: str) -> Optional[dict]:
        """Get backoff status for a task."""
        return self._backoffs.get(task_id)

    def get_all(self) -> dict:
        """Get all backoff entries (for persistence)."""
        return dict(self._backoffs)

    def restore(self, data: dict) -> None:
        """Restore backoff state from persisted data."""
        self._backoffs = dict(data)

    def cleanup_expired(self, max_age_hours: float = 24.0) -> int:
        """Remove backoff entries older than threshold."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        to_remove = []
        for task_id, entry in self._backoffs.items():
            try:
                next_retry = datetime.fromisoformat(entry["next_retry_at"])
                if next_retry < cutoff:
                    to_remove.append(task_id)
            except (ValueError, KeyError):
                to_remove.append(task_id)

        for task_id in to_remove:
            del self._backoffs[task_id]
        return len(to_remove)

    @property
    def pending_count(self) -> int:
        """Number of tasks currently in backoff."""
        now = datetime.now(timezone.utc)
        return sum(
            1
            for entry in self._backoffs.values()
            if datetime.fromisoformat(entry["next_retry_at"]) > now
        )


class SwarmStatePersistence:
    """
    File-based state persistence for the SwarmCoordinator.

    Writes state as JSON with atomic rename to prevent corruption.
    Supports versioned schemas for forward compatibility.
    """

    def __init__(self, state_dir: str = DEFAULT_STATE_DIR):
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "coordinator_state.json"
        self.backup_file = self.state_dir / "coordinator_state.backup.json"
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Create state directory if it doesn't exist."""
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def save(self, state: PersistedState) -> bool:
        """
        Save coordinator state atomically.

        1. Write to temp file
        2. Rename existing to .backup
        3. Rename temp to primary

        Returns True on success.
        """
        state.saved_at = datetime.now(timezone.utc).isoformat()

        try:
            # Write to temp file first
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self.state_dir), suffix=".tmp", prefix="state_"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(state.to_dict(), f, indent=2)
            except Exception:
                os.unlink(tmp_path)
                raise

            # Backup existing state
            if self.state_file.exists():
                try:
                    os.replace(str(self.state_file), str(self.backup_file))
                except OSError:
                    pass  # Backup is best-effort

            # Atomic rename
            os.replace(tmp_path, str(self.state_file))

            logger.debug(f"State saved to {self.state_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            return False

    def load(self, max_age_hours: float = 48.0) -> Optional[PersistedState]:
        """
        Load coordinator state from disk.

        Returns None if:
        - No state file exists
        - State is older than max_age_hours
        - State is corrupted
        - Schema version is incompatible
        """
        file_to_load = self.state_file
        if not file_to_load.exists():
            file_to_load = self.backup_file
            if not file_to_load.exists():
                logger.info("No persisted state found")
                return None

        try:
            with open(file_to_load) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read state from {file_to_load}: {e}")
            return None

        # Check schema version
        version = data.get("schema_version", 0)
        if version > SCHEMA_VERSION:
            logger.warning(
                f"State schema v{version} is newer than supported v{SCHEMA_VERSION}"
            )
            return None

        # Check age
        saved_at_str = data.get("saved_at", "")
        if saved_at_str:
            try:
                saved_at = datetime.fromisoformat(saved_at_str)
                age = datetime.now(timezone.utc) - saved_at
                if age > timedelta(hours=max_age_hours):
                    logger.info(
                        f"State is {age.total_seconds() / 3600:.1f}h old "
                        f"(max {max_age_hours}h), skipping"
                    )
                    return None
            except ValueError:
                pass  # Can't parse date, continue with load

        state = PersistedState.from_dict(data)
        logger.info(
            f"Loaded state: {len(state.pending_tasks)} pending, "
            f"{len(state.assigned_tasks)} assigned tasks"
        )
        return state

    def delete(self) -> bool:
        """Remove all state files."""
        removed = False
        for f in [self.state_file, self.backup_file]:
            if f.exists():
                f.unlink()
                removed = True
        return removed

    def get_info(self) -> dict:
        """Get info about persisted state without loading it."""
        info = {"state_dir": str(self.state_dir), "has_state": False}

        if self.state_file.exists():
            stat = self.state_file.stat()
            info["has_state"] = True
            info["state_file"] = str(self.state_file)
            info["size_bytes"] = stat.st_size
            info["modified_at"] = datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat()

        if self.backup_file.exists():
            info["has_backup"] = True

        return info
