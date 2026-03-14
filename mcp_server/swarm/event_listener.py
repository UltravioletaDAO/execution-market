"""
EventListener — Polls the EM API for new tasks and completion events.

This is the input side of the feedback loop. It watches for:
1. New published tasks → feeds them into the coordinator for routing
2. Completed tasks → triggers reputation updates and Skill DNA extraction
3. Failed/expired tasks → triggers agent reputation penalties

The listener runs as a polling loop with configurable intervals.
It maintains a watermark (last-seen timestamp) to avoid reprocessing.

Usage:
    coordinator = SwarmCoordinator.create(...)
    listener = EventListener(coordinator)

    # One-shot poll (for cron/heartbeat integration)
    results = listener.poll_once()

    # Or run continuous loop (for daemon mode)
    listener.run(poll_interval=30)

Design decisions:
    - Polling over webhooks: simpler deployment, no public endpoint needed
    - Watermark-based: idempotent, safe to restart
    - Category mapping: maps EM task categories to swarm routing categories
    - Graceful degradation: continues on individual task failures
"""

import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Callable
from enum import Enum

logger = logging.getLogger("em.swarm.event_listener")


# ─── Category Mapping ─────────────────────────────────────────────────────────

# Maps EM API task categories to swarm routing categories
EM_CATEGORY_MAP = {
    # Physical tasks
    "delivery": ["physical", "delivery", "logistics"],
    "pickup": ["physical", "delivery", "logistics"],
    "errand": ["physical", "errand", "simple_action"],
    "cleaning": ["physical", "cleaning", "manual_labor"],
    "moving": ["physical", "moving", "manual_labor"],
    "handyman": ["physical", "repair", "skilled_trade"],
    "assembly": ["physical", "assembly", "manual_labor"],
    # Digital tasks
    "data_entry": ["digital", "data_entry", "clerical"],
    "research": ["digital", "research", "analysis"],
    "writing": ["digital", "writing", "content"],
    "translation": ["digital", "translation", "language"],
    "design": ["digital", "design", "creative"],
    "coding": ["digital", "coding", "technical"],
    "testing": ["digital", "testing", "qa"],
    # Verification tasks
    "photo_verification": ["verification", "photo", "evidence"],
    "location_verification": ["verification", "geo", "evidence"],
    "mystery_shopping": ["verification", "retail", "assessment"],
    # Blockchain tasks
    "blockchain": ["blockchain", "crypto", "technical"],
    "defi": ["blockchain", "defi", "finance"],
    "nft": ["blockchain", "nft", "creative"],
    # Default
    "general": ["general", "misc"],
    "other": ["general", "misc"],
}


def map_categories(em_category: Optional[str]) -> list[str]:
    """Map an EM task category to swarm routing categories."""
    if not em_category:
        return ["general", "misc"]
    key = em_category.lower().strip()
    return EM_CATEGORY_MAP.get(key, ["general", key])


# ─── Event Types ──────────────────────────────────────────────────────────────


class ListenerEvent(str, Enum):
    """Events emitted by the listener."""

    NEW_TASK = "new_task"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_EXPIRED = "task_expired"
    POLL_COMPLETE = "poll_complete"
    POLL_ERROR = "poll_error"


@dataclass
class PollResult:
    """Result of a single poll cycle."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    new_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    expired_tasks: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def total_events(self) -> int:
        return (
            self.new_tasks
            + self.completed_tasks
            + self.failed_tasks
            + self.expired_tasks
        )

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "new_tasks": self.new_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "expired_tasks": self.expired_tasks,
            "total_events": self.total_events,
            "errors": self.errors,
            "duration_ms": round(self.duration_ms, 1),
        }


# ─── Watermark State ──────────────────────────────────────────────────────────


@dataclass
class ListenerState:
    """Persisted state for the event listener."""

    last_poll_at: Optional[datetime] = None
    last_new_task_id: Optional[str] = None
    last_completed_task_id: Optional[str] = None
    poll_count: int = 0
    total_new_tasks: int = 0
    total_completions: int = 0
    total_failures: int = 0
    total_errors: int = 0

    # Limit known_task_ids to prevent unbounded growth.
    # Using a deque ensures deterministic FIFO eviction of oldest items.
    MAX_KNOWN_TASKS = 10000

    def __post_init__(self):
        # _known_deque preserves insertion order; _known_set enables O(1) lookup.
        self._known_deque: deque[str] = deque(maxlen=self.MAX_KNOWN_TASKS)
        self._known_set: set[str] = set()

    def mark_seen(self, task_id: str):
        """Mark a task as seen (FIFO eviction when full)."""
        if task_id in self._known_set:
            return
        # If deque is at capacity, the oldest item is auto-evicted.
        if len(self._known_deque) == self._known_deque.maxlen:
            evicted = self._known_deque[0]  # will be popped by append
            self._known_set.discard(evicted)
        self._known_deque.append(task_id)
        self._known_set.add(task_id)

    def is_seen(self, task_id: str) -> bool:
        """Check if a task has already been processed."""
        return task_id in self._known_set

    def to_dict(self) -> dict:
        return {
            "last_poll_at": self.last_poll_at.isoformat()
            if self.last_poll_at
            else None,
            "last_new_task_id": self.last_new_task_id,
            "last_completed_task_id": self.last_completed_task_id,
            "known_task_count": len(self._known_set),
            "poll_count": self.poll_count,
            "total_new_tasks": self.total_new_tasks,
            "total_completions": self.total_completions,
            "total_failures": self.total_failures,
            "total_errors": self.total_errors,
        }

    def save(self, path: str):
        """Save state to a JSON file."""
        data = self.to_dict()
        data["known_task_ids"] = list(self._known_deque)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "ListenerState":
        """Load state from a JSON file."""
        try:
            with open(path) as f:
                data = json.load(f)
            state = cls()
            state.last_poll_at = (
                datetime.fromisoformat(data["last_poll_at"])
                if data.get("last_poll_at")
                else None
            )
            state.last_new_task_id = data.get("last_new_task_id")
            state.last_completed_task_id = data.get("last_completed_task_id")
            # Restore known task IDs preserving saved order
            for task_id in data.get("known_task_ids", []):
                state.mark_seen(task_id)
            state.poll_count = data.get("poll_count", 0)
            state.total_new_tasks = data.get("total_new_tasks", 0)
            state.total_completions = data.get("total_completions", 0)
            state.total_failures = data.get("total_failures", 0)
            state.total_errors = data.get("total_errors", 0)
            return state
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return cls()


# ─── Priority Mapping ─────────────────────────────────────────────────────────


def estimate_priority(task: dict) -> str:
    """Estimate task priority from EM task data."""
    bounty = task.get("bounty_amount", 0) or 0
    try:
        bounty = float(bounty)
    except (ValueError, TypeError):
        bounty = 0

    # High-value tasks get higher priority
    if bounty >= 50:
        return "HIGH"
    elif bounty >= 10:
        return "NORMAL"
    elif bounty >= 1:
        return "LOW"
    return "NORMAL"


# ─── Event Listener ──────────────────────────────────────────────────────────


class EventListener:
    """
    Polls the EM API for task lifecycle events and feeds them
    into the SwarmCoordinator.

    Supports two modes:
    1. poll_once() — single poll cycle (for cron/heartbeat)
    2. run() — continuous polling loop (for daemon mode)
    """

    def __init__(
        self,
        coordinator,  # SwarmCoordinator (avoid circular import)
        state_path: Optional[str] = None,
        on_event: Optional[Callable] = None,
    ):
        self.coordinator = coordinator
        self.em_client = coordinator.em_client
        self.state = ListenerState.load(state_path) if state_path else ListenerState()
        self.state_path = state_path
        self.on_event = on_event
        self._running = False

    def _emit(self, event: ListenerEvent, data: dict):
        """Emit an event to the callback handler."""
        if self.on_event:
            try:
                self.on_event(event, data)
            except Exception as e:
                logger.warning(f"Event callback error: {e}")

    def _save_state(self):
        """Persist state if a path is configured."""
        if self.state_path:
            try:
                self.state.save(self.state_path)
            except Exception as e:
                logger.warning(f"Failed to save listener state: {e}")

    def poll_new_tasks(self) -> list[dict]:
        """
        Poll for new published tasks and ingest them into the coordinator.

        Returns list of newly ingested task dicts.
        """
        ingested = []
        try:
            tasks = self.em_client.list_tasks(status="published", limit=100)
            if not tasks:
                return ingested

            for task in tasks:
                task_id = str(task.get("id", task.get("task_id", "")))
                if not task_id or self.state.is_seen(task_id):
                    continue

                # Map EM task to coordinator format
                title = task.get("title", "Untitled")
                category = task.get("category", "general")
                categories = map_categories(category)
                bounty = task.get("bounty_amount", 0)
                try:
                    bounty = float(bounty)
                except (ValueError, TypeError):
                    bounty = 0.0

                priority_str = estimate_priority(task)

                # Ingest into coordinator
                try:
                    from .orchestrator import TaskPriority

                    priority = TaskPriority[priority_str]

                    self.coordinator.ingest_task(
                        task_id=task_id,
                        title=title,
                        categories=categories,
                        bounty_usd=bounty,
                        priority=priority,
                        source="api",
                        raw_data=task,
                    )

                    self.state.mark_seen(task_id)
                    self.state.last_new_task_id = task_id
                    self.state.total_new_tasks += 1
                    ingested.append(task)

                    self._emit(
                        ListenerEvent.NEW_TASK,
                        {
                            "task_id": task_id,
                            "title": title,
                            "categories": categories,
                            "bounty": bounty,
                        },
                    )

                    logger.info(
                        f"Ingested new task: {task_id} '{title}' ({category}) ${bounty}"
                    )

                except Exception as e:
                    logger.error(f"Failed to ingest task {task_id}: {e}")
                    self.state.total_errors += 1

        except Exception as e:
            logger.error(f"Error polling new tasks: {e}")
            self.state.total_errors += 1

        return ingested

    def poll_completions(self) -> list[dict]:
        """
        Poll for completed tasks and update reputation/metrics.

        Returns list of newly detected completions.
        """
        completed = []
        try:
            tasks = self.em_client.list_tasks(status="completed", limit=50)
            if not tasks:
                return completed

            completion_key_prefix = "completed_"
            for task in tasks:
                task_id = str(task.get("id", task.get("task_id", "")))
                completion_key = f"{completion_key_prefix}{task_id}"

                if not task_id or self.state.is_seen(completion_key):
                    continue

                # Check if this task was assigned by our swarm
                assigned_agent = task.get("worker_agent_id") or task.get("assigned_to")

                # Try to complete in coordinator (will update reputation)
                try:
                    # Extract evidence data for Skill DNA
                    evidence = task.get("evidence", [])
                    evidence_summary = self._summarize_evidence(evidence)

                    self.coordinator.complete_task(
                        task_id=task_id,
                        evidence_summary=evidence_summary,
                    )

                    self.state.mark_seen(completion_key)
                    self.state.last_completed_task_id = task_id
                    self.state.total_completions += 1
                    completed.append(task)

                    self._emit(
                        ListenerEvent.TASK_COMPLETED,
                        {
                            "task_id": task_id,
                            "agent_id": assigned_agent,
                            "evidence_count": len(evidence)
                            if isinstance(evidence, list)
                            else 0,
                        },
                    )

                    logger.info(
                        f"Processed completion: {task_id} (agent: {assigned_agent})"
                    )

                except KeyError:
                    # Task not in our queue — was completed externally
                    self.state.mark_seen(completion_key)
                    logger.debug(f"Completion for external task: {task_id}")

                except Exception as e:
                    logger.error(f"Failed to process completion for {task_id}: {e}")
                    self.state.total_errors += 1

        except Exception as e:
            logger.error(f"Error polling completions: {e}")
            self.state.total_errors += 1

        return completed

    def poll_failures(self) -> list[dict]:
        """
        Poll for failed/cancelled/expired tasks and update state.

        Returns list of newly detected failures.
        """
        failures = []
        for status in ("cancelled", "expired", "disputed"):
            try:
                tasks = self.em_client.list_tasks(status=status, limit=50)
                if not tasks:
                    continue

                failure_key_prefix = f"{status}_"
                for task in tasks:
                    task_id = str(task.get("id", task.get("task_id", "")))
                    failure_key = f"{failure_key_prefix}{task_id}"

                    if not task_id or self.state.is_seen(failure_key):
                        continue

                    try:
                        reason = task.get(
                            "failure_reason", task.get("cancellation_reason", status)
                        )
                        self.coordinator.fail_task(task_id=task_id, reason=str(reason))

                        self.state.mark_seen(failure_key)
                        self.state.total_failures += 1
                        failures.append(task)

                        event_type = (
                            ListenerEvent.TASK_EXPIRED
                            if status == "expired"
                            else ListenerEvent.TASK_FAILED
                        )
                        self._emit(
                            event_type,
                            {
                                "task_id": task_id,
                                "status": status,
                                "reason": str(reason),
                            },
                        )

                        logger.info(f"Processed {status}: {task_id}")

                    except KeyError:
                        self.state.mark_seen(failure_key)
                        logger.debug(f"{status.title()} for external task: {task_id}")

                    except Exception as e:
                        logger.error(f"Failed to process {status} for {task_id}: {e}")
                        self.state.total_errors += 1

            except Exception as e:
                logger.error(f"Error polling {status} tasks: {e}")
                self.state.total_errors += 1

        return failures

    def _summarize_evidence(self, evidence) -> str:
        """Summarize task evidence for reputation updates."""
        if not evidence:
            return "no_evidence"
        if isinstance(evidence, str):
            return evidence[:200]
        if isinstance(evidence, list):
            types = []
            for e in evidence:
                if isinstance(e, dict):
                    types.append(e.get("type", e.get("evidence_type", "unknown")))
                else:
                    types.append(str(e)[:50])
            return f"evidence_types: {', '.join(types[:10])}"
        return str(evidence)[:200]

    def poll_once(self) -> PollResult:
        """
        Run a single poll cycle: check for new tasks, completions, and failures.

        Returns a PollResult with counts and timing.
        """
        start = time.monotonic()
        result = PollResult()

        # Poll in order: new tasks, completions, failures
        new_tasks = self.poll_new_tasks()
        result.new_tasks = len(new_tasks)

        completions = self.poll_completions()
        result.completed_tasks = len(completions)

        failures = self.poll_failures()
        result.failed_tasks = len([f for f in failures if f.get("status") != "expired"])
        result.expired_tasks = len(
            [f for f in failures if f.get("status") == "expired"]
        )

        # Process the task queue after ingestion
        if result.new_tasks > 0:
            try:
                self.coordinator.process_task_queue()
            except Exception as e:
                logger.error(f"Error processing task queue: {e}")
                result.errors.append(f"queue_processing: {e}")

        # Run health checks
        try:
            self.coordinator.run_health_checks()
        except Exception as e:
            logger.error(f"Error running health checks: {e}")
            result.errors.append(f"health_check: {e}")

        # Update state
        result.duration_ms = (time.monotonic() - start) * 1000
        self.state.last_poll_at = result.timestamp
        self.state.poll_count += 1

        self._save_state()
        self._emit(ListenerEvent.POLL_COMPLETE, result.to_dict())

        logger.info(
            f"Poll #{self.state.poll_count}: "
            f"+{result.new_tasks} tasks, "
            f"{result.completed_tasks} completed, "
            f"{result.failed_tasks} failed, "
            f"{result.expired_tasks} expired "
            f"({result.duration_ms:.0f}ms)"
        )

        return result

    def run(
        self,
        poll_interval: float = 30.0,
        max_polls: Optional[int] = None,
    ):
        """
        Run continuous polling loop.

        Args:
            poll_interval: Seconds between polls (default 30s)
            max_polls: Stop after N polls (None = run forever)
        """
        self._running = True
        polls = 0

        logger.info(
            f"EventListener starting (interval={poll_interval}s, "
            f"max_polls={max_polls or 'unlimited'})"
        )

        while self._running:
            try:
                self.poll_once()
                polls += 1

                if max_polls and polls >= max_polls:
                    logger.info(f"Reached max_polls ({max_polls}), stopping")
                    break

                time.sleep(poll_interval)

            except KeyboardInterrupt:
                logger.info("EventListener stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error in poll loop: {e}")
                time.sleep(poll_interval * 2)  # Back off on errors

        self._running = False
        self._save_state()
        logger.info(f"EventListener stopped after {polls} polls")

    def stop(self):
        """Signal the polling loop to stop."""
        self._running = False

    def get_status(self) -> dict:
        """Get listener status summary."""
        return {
            "running": self._running,
            "state": self.state.to_dict(),
            "em_api_url": self.em_client.base_url,
        }
