"""
SwarmHeartbeatHandler — Integrates swarm coordination with OpenClaw heartbeat cycle.

This handler is designed to be called from the main session's heartbeat check.
It runs a condensed coordination cycle: poll → route → health → report.

Usage (from HEARTBEAT.md or heartbeat script):
    from swarm.heartbeat_handler import SwarmHeartbeatHandler

    handler = SwarmHeartbeatHandler(em_api_url="https://api.execution.market")
    report = handler.run_cycle()
    # Returns a summary string suitable for Telegram notification

The handler is stateless between invocations but persists state to disk
for continuity across heartbeats.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .coordinator import SwarmCoordinator
from .event_listener import EventListener

logger = logging.getLogger("em.swarm.heartbeat")


@dataclass
class HeartbeatReport:
    """Summary of one heartbeat coordination cycle."""

    timestamp: str = ""
    duration_ms: float = 0
    new_tasks: int = 0
    tasks_routed: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    agents_active: int = 0
    agents_degraded: int = 0
    em_api_healthy: bool = False
    autojob_available: bool = False
    errors: list = field(default_factory=list)
    skill_dna_updates: int = 0
    bounty_earned_usd: float = 0

    def to_summary(self) -> str:
        """Generate a concise Telegram-friendly summary."""
        status = (
            "🟢"
            if self.em_api_healthy and not self.errors
            else "🟡"
            if self.em_api_healthy
            else "🔴"
        )

        lines = [
            f"{status} **Swarm Heartbeat** ({self.duration_ms:.0f}ms)",
        ]

        if self.new_tasks or self.tasks_routed or self.tasks_completed:
            lines.append(
                f"📋 Tasks: +{self.new_tasks} new, {self.tasks_routed} routed, {self.tasks_completed} completed"
            )

        if self.agents_active:
            agent_str = f"🤖 Agents: {self.agents_active} active"
            if self.agents_degraded:
                agent_str += f" ({self.agents_degraded} degraded)"
            lines.append(agent_str)

        if self.bounty_earned_usd > 0:
            lines.append(f"💰 Earned: ${self.bounty_earned_usd:.2f}")

        if self.skill_dna_updates:
            lines.append(f"🧬 Skill DNA: {self.skill_dna_updates} updates")

        if self.errors:
            lines.append(f"⚠️ Issues: {', '.join(self.errors[:3])}")

        return "\n".join(lines)

    def is_notable(self) -> bool:
        """Should this heartbeat generate a notification?"""
        return bool(
            self.new_tasks > 0
            or self.tasks_completed > 0
            or self.agents_degraded > 0
            or len(self.errors) > 0
            or self.bounty_earned_usd > 0
        )

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "new_tasks": self.new_tasks,
            "tasks_routed": self.tasks_routed,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "agents_active": self.agents_active,
            "agents_degraded": self.agents_degraded,
            "em_api_healthy": self.em_api_healthy,
            "autojob_available": self.autojob_available,
            "errors": self.errors,
            "skill_dna_updates": self.skill_dna_updates,
            "bounty_earned_usd": self.bounty_earned_usd,
        }


# ─── State Persistence ────────────────────────────────────────────────────────

DEFAULT_STATE_DIR = os.path.expanduser("~/.em-swarm")


def _load_state(state_dir: str = DEFAULT_STATE_DIR) -> dict:
    """Load persistent state from disk."""
    state_file = os.path.join(state_dir, "heartbeat_state.json")
    try:
        with open(state_file, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "last_heartbeat": None,
            "total_cycles": 0,
            "total_tasks_processed": 0,
            "total_bounty_earned": 0,
            "known_task_ids": [],
            "worker_profiles": {},
        }


def _save_state(state: dict, state_dir: str = DEFAULT_STATE_DIR) -> None:
    """Save persistent state to disk."""
    os.makedirs(state_dir, exist_ok=True)
    state_file = os.path.join(state_dir, "heartbeat_state.json")
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2, default=str)


# ─── Handler ──────────────────────────────────────────────────────────────────


class SwarmHeartbeatHandler:
    """
    Runs a condensed swarm coordination cycle during heartbeat polls.

    Each cycle:
    1. Initialize coordinator (if needed)
    2. Poll EM API for new/completed tasks
    3. Route available tasks to agents
    4. Process completions → update reputation
    5. Run health checks
    6. Persist state
    7. Return summary report
    """

    def __init__(
        self,
        em_api_url: str = "https://api.execution.market",
        autojob_url: str = "http://localhost:8765",
        state_dir: str = DEFAULT_STATE_DIR,
        mode: str = "passive",  # passive | semi-auto | full-auto
        max_task_bounty: float = 1.0,
    ):
        self.em_api_url = em_api_url
        self.autojob_url = autojob_url
        self.state_dir = state_dir
        self.mode = mode
        self.max_task_bounty = max_task_bounty

        self._coordinator: Optional[SwarmCoordinator] = None
        self._event_listener: Optional[EventListener] = None

    def _init_coordinator(self) -> SwarmCoordinator:
        """Lazy-initialize the coordinator."""
        if self._coordinator is None:
            self._coordinator = SwarmCoordinator.create(
                em_api_url=self.em_api_url,
                autojob_url=self.autojob_url,
            )
        return self._coordinator

    def _init_event_listener(self) -> EventListener:
        """Lazy-initialize the event listener."""
        if self._event_listener is None:
            coord = self._init_coordinator()
            self._event_listener = EventListener(
                coordinator=coord,
                state_path=os.path.join(self.state_dir, "event_listener_state.json"),
            )
        return self._event_listener

    def run_cycle(self) -> HeartbeatReport:
        """
        Run one complete heartbeat coordination cycle.

        Returns a HeartbeatReport with summary metrics.
        """
        start = time.monotonic()
        report = HeartbeatReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        state = _load_state(self.state_dir)

        try:
            coord = self._init_coordinator()
        except Exception as e:
            report.errors.append(f"coordinator_init: {e}")
            report.duration_ms = (time.monotonic() - start) * 1000
            return report

        # Step 1: Check EM API health
        try:
            if coord.em_client:
                health = coord.em_client.get_health()
                report.em_api_healthy = health.get("status") == "healthy"
        except Exception:
            report.em_api_healthy = False

        # Step 2: Ingest new tasks
        try:
            new_tasks = coord.ingest_from_api()
            report.new_tasks = new_tasks
        except Exception as e:
            report.errors.append(f"ingest: {e}")

        # Step 3: Route tasks (mode-dependent, respects max_task_bounty)
        if self.mode != "passive" and report.new_tasks > 0:
            try:
                # Filter out tasks exceeding max_task_bounty before routing
                if self.max_task_bounty > 0:
                    for task in list(coord._task_queue.values()):
                        if (
                            task.status == "pending"
                            and task.bounty_usd > self.max_task_bounty
                        ):
                            logger.info(
                                f"Skipping task {task.task_id}: bounty ${task.bounty_usd:.2f} "
                                f"exceeds max ${self.max_task_bounty:.2f}"
                            )
                            task.status = "failed"
                assignments = coord.process_task_queue(max_tasks=5)
                report.tasks_routed = sum(
                    1 for a in assignments if hasattr(a, "agent_id")
                )
            except Exception as e:
                report.errors.append(f"routing: {e}")

        # Step 4: Process completed tasks via event listener
        try:
            listener = self._init_event_listener()
            poll_result = listener.poll_once()

            report.tasks_completed = poll_result.completed_tasks
            report.tasks_failed = poll_result.failed_tasks + poll_result.expired_tasks

            # Note: Skill DNA extraction happens when we have access to
            # individual completion evidence. The EventListener already
            # triggers coordinator updates for completions, so the
            # reputation pipeline runs automatically.

        except Exception as e:
            report.errors.append(f"event_processing: {e}")

        # Step 6: Run health checks
        try:
            health_report = coord.run_health_checks()
            agents = health_report.get("agents", {})
            report.agents_active = agents.get("healthy", 0)
            report.agents_degraded = agents.get("degraded", 0)

            # Check AutoJob
            systems = health_report.get("systems", {})
            report.autojob_available = systems.get("autojob") == "available"
        except Exception as e:
            report.errors.append(f"health_check: {e}")

        # Step 7: Update metrics
        try:
            metrics = coord.get_metrics()
            report.bounty_earned_usd = (
                metrics.bounty_earned if hasattr(metrics, "bounty_earned") else 0
            )
        except Exception:
            pass

        # Step 8: Persist state
        state["last_heartbeat"] = report.timestamp
        state["total_cycles"] = state.get("total_cycles", 0) + 1
        state["total_tasks_processed"] = (
            state.get("total_tasks_processed", 0) + report.tasks_completed
        )

        try:
            _save_state(state, self.state_dir)
        except Exception as e:
            report.errors.append(f"state_save: {e}")

        report.duration_ms = round((time.monotonic() - start) * 1000, 2)
        return report

    def get_state(self) -> dict:
        """Get current persistent state."""
        return _load_state(self.state_dir)

    def reset_state(self) -> None:
        """Reset persistent state (for testing/debugging)."""
        _save_state({}, self.state_dir)
