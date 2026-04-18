"""
SwarmRunner — Production daemon loop for the KK V2 agent swarm.

This is the top-level entry point that runs the swarm as a continuous service.
It orchestrates 7 phases per cycle:

    Phase 1: DISCOVER  — Poll EM API for new tasks
    Phase 2: ENRICH    — Fetch AutoJob intelligence for candidate tasks
    Phase 3: ROUTE     — Assign tasks to best-fit agents
    Phase 4: MONITOR   — Check agent health and heartbeats
    Phase 5: COLLECT   — Poll for completed tasks, harvest evidence
    Phase 6: LEARN     — Update Skill DNA from completed evidence
    Phase 7: REPORT    — Emit metrics, persist state, log summary

Usage:
    # Start the swarm daemon
    python3 -m mcp_server.swarm.runner --mode passive
    python3 -m mcp_server.swarm.runner --mode active --cycle-interval 60

    # Or import and use programmatically:
    runner = SwarmRunner.create(
        em_api_url="https://api.execution.market",
        mode="passive",
    )
    runner.run()
"""

import json
import logging
import os
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from .coordinator import SwarmCoordinator
from .event_listener import EventListener
from .evidence_parser import EvidenceParser, WorkerRegistry
from utils.pii import truncate_wallet

logger = logging.getLogger("em.swarm.runner")


class RunMode(str, Enum):
    """Runner operational modes."""

    PASSIVE = "passive"  # Observe only — no task applications
    ACTIVE = "active"  # Full autonomous operation
    DRY_RUN = "dry_run"  # Process but don't execute API calls


class Phase(str, Enum):
    """The 7 phases of each coordination cycle."""

    DISCOVER = "discover"
    ENRICH = "enrich"
    ROUTE = "route"
    MONITOR = "monitor"
    COLLECT = "collect"
    LEARN = "learn"
    REPORT = "report"


@dataclass
class CycleResult:
    """Result of one coordination cycle."""

    cycle_number: int = 0
    started_at: str = ""
    duration_ms: float = 0
    mode: str = "passive"
    phases_completed: list = field(default_factory=list)
    phases_failed: list = field(default_factory=list)

    # Phase 1: Discover
    tasks_discovered: int = 0
    tasks_new: int = 0

    # Phase 2: Enrich
    tasks_enriched: int = 0
    enrichment_source: str = ""

    # Phase 3: Route
    tasks_routed: int = 0
    routing_failures: int = 0

    # Phase 4: Monitor
    agents_active: int = 0
    agents_degraded: int = 0
    agents_suspended: int = 0
    health_checks_run: int = 0

    # Phase 5: Collect
    tasks_completed: int = 0
    tasks_failed: int = 0
    evidence_collected: int = 0
    bounty_earned_usd: float = 0

    # Phase 6: Learn
    skill_updates: int = 0
    reputation_updates: int = 0

    # Phase 7: Report
    em_api_healthy: bool = False
    errors: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}

    def summary_line(self) -> str:
        """One-line summary for logging."""
        parts = [f"Cycle #{self.cycle_number}"]
        if self.tasks_new:
            parts.append(f"+{self.tasks_new} tasks")
        if self.tasks_routed:
            parts.append(f"{self.tasks_routed} routed")
        if self.tasks_completed:
            parts.append(f"{self.tasks_completed} completed")
        if self.bounty_earned_usd > 0:
            parts.append(f"${self.bounty_earned_usd:.2f} earned")
        if self.agents_degraded:
            parts.append(f"⚠ {self.agents_degraded} degraded")
        if self.errors:
            parts.append(f"❌ {len(self.errors)} errors")
        parts.append(f"({self.duration_ms:.0f}ms)")
        return " | ".join(parts)


@dataclass
class RunnerState:
    """Persistent runner state across restarts."""

    last_cycle: int = 0
    last_cycle_at: str = ""
    total_cycles: int = 0
    total_tasks_routed: int = 0
    total_tasks_completed: int = 0
    total_bounty_earned_usd: float = 0
    started_at: str = ""
    errors_total: int = 0

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: dict) -> "RunnerState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class SwarmRunner:
    """
    Production daemon for the KK V2 agent swarm.

    Runs an infinite loop of 7-phase coordination cycles. Each cycle:
    1. Discovers new tasks from the EM API
    2. Enriches candidate tasks with AutoJob intelligence
    3. Routes tasks to best-fit agents
    4. Monitors agent health (heartbeats, budgets, state)
    5. Collects completed tasks and evidence
    6. Learns from evidence (updates Skill DNA)
    7. Reports metrics and persists state
    """

    def __init__(
        self,
        coordinator: SwarmCoordinator,
        event_listener: Optional[EventListener] = None,
        evidence_parser: Optional[EvidenceParser] = None,
        worker_registry: Optional[WorkerRegistry] = None,
        mode: RunMode = RunMode.PASSIVE,
        cycle_interval_seconds: float = 120.0,
        state_dir: Optional[str] = None,
        max_tasks_per_cycle: int = 10,
        max_cycles: int = 0,  # 0 = unlimited
    ):
        self.coordinator = coordinator
        self.event_listener = event_listener or EventListener(
            coordinator=coordinator,
        )
        self.evidence_parser = evidence_parser or EvidenceParser()
        self.worker_registry = worker_registry or WorkerRegistry()
        self.mode = mode
        self.cycle_interval = cycle_interval_seconds
        self.state_dir = Path(state_dir or os.path.expanduser("~/.em-swarm"))
        self.max_tasks_per_cycle = max_tasks_per_cycle
        self.max_cycles = max_cycles

        # Runtime state
        self._running = False
        self._state = RunnerState()
        self._cycle_history: list[CycleResult] = []
        self._known_task_ids: set[str] = set()
        self._max_cycle_history = 500
        self._max_known_tasks = 10000

    @classmethod
    def create(
        cls,
        em_api_url: str = "https://api.execution.market",
        em_api_key: Optional[str] = None,
        autojob_url: Optional[str] = None,
        mode: str = "passive",
        cycle_interval: float = 120.0,
        state_dir: Optional[str] = None,
        max_tasks_per_cycle: int = 10,
        max_cycles: int = 0,
    ) -> "SwarmRunner":
        """Factory method for creating a fully-wired SwarmRunner."""
        coordinator = SwarmCoordinator.create(
            em_api_url=em_api_url,
            em_api_key=em_api_key,
            autojob_url=autojob_url or "https://autojob.cc",
        )

        run_mode = RunMode(mode) if isinstance(mode, str) else mode

        return cls(
            coordinator=coordinator,
            mode=run_mode,
            cycle_interval_seconds=cycle_interval,
            state_dir=state_dir,
            max_tasks_per_cycle=max_tasks_per_cycle,
            max_cycles=max_cycles,
        )

    # ── Lifecycle ─────────────────────────────────────────────────────

    def run(self):
        """Main entry point — run the daemon loop."""
        self._running = True
        self._state.started_at = datetime.now(timezone.utc).isoformat()
        self._load_state()
        self._setup_signals()

        logger.info(
            f"SwarmRunner started — mode={self.mode.value}, "
            f"interval={self.cycle_interval}s, "
            f"max_tasks={self.max_tasks_per_cycle}"
        )

        try:
            while self._running:
                cycle = self._run_cycle()
                self._cycle_history.append(cycle)
                if len(self._cycle_history) > self._max_cycle_history:
                    self._cycle_history = self._cycle_history[
                        -self._max_cycle_history :
                    ]
                self._update_state(cycle)
                self._save_state()

                logger.info(cycle.summary_line())

                if self.max_cycles > 0 and self._state.total_cycles >= self.max_cycles:
                    logger.info(f"Reached max cycles ({self.max_cycles}). Stopping.")
                    break

                if self._running:
                    time.sleep(self.cycle_interval)

        except KeyboardInterrupt:
            logger.info("SwarmRunner stopped by keyboard interrupt.")
        finally:
            self._running = False
            self._save_state()
            logger.info(
                f"SwarmRunner shut down. Total cycles: {self._state.total_cycles}, "
                f"tasks routed: {self._state.total_tasks_routed}, "
                f"earned: ${self._state.total_bounty_earned_usd:.2f}"
            )

    def stop(self):
        """Signal the runner to stop after current cycle."""
        self._running = False

    def run_once(self) -> CycleResult:
        """Run a single cycle and return the result. Useful for testing."""
        self._load_state()
        cycle = self._run_cycle()
        self._cycle_history.append(cycle)
        if len(self._cycle_history) > self._max_cycle_history:
            self._cycle_history = self._cycle_history[-self._max_cycle_history :]
        self._update_state(cycle)
        self._save_state()
        return cycle

    # ── 7-Phase Cycle ─────────────────────────────────────────────────

    def _run_cycle(self) -> CycleResult:
        """Execute one complete 7-phase coordination cycle."""
        result = CycleResult(
            cycle_number=self._state.total_cycles + 1,
            started_at=datetime.now(timezone.utc).isoformat(),
            mode=self.mode.value,
        )
        start = time.monotonic()

        phases = [
            (Phase.DISCOVER, self._phase_discover),
            (Phase.ENRICH, self._phase_enrich),
            (Phase.ROUTE, self._phase_route),
            (Phase.MONITOR, self._phase_monitor),
            (Phase.COLLECT, self._phase_collect),
            (Phase.LEARN, self._phase_learn),
            (Phase.REPORT, self._phase_report),
        ]

        for phase_name, phase_fn in phases:
            try:
                phase_fn(result)
                result.phases_completed.append(phase_name.value)
            except Exception as e:
                error_msg = f"{phase_name.value}: {type(e).__name__}: {e}"
                result.phases_failed.append(phase_name.value)
                result.errors.append(error_msg)
                logger.error(f"Phase {phase_name.value} failed: {e}")

        result.duration_ms = (time.monotonic() - start) * 1000
        return result

    def _phase_discover(self, result: CycleResult):
        """Phase 1: Discover new tasks from the EM API."""
        if not self.coordinator.em_client:
            return

        tasks = self.coordinator.em_client.list_tasks(
            status="published",
            limit=self.max_tasks_per_cycle,
        )

        result.tasks_discovered = len(tasks)
        new_count = 0

        for task_data in tasks:
            task_id = str(task_data.get("id", ""))
            if not task_id or task_id in self._known_task_ids:
                continue

            self._known_task_ids.add(task_id)
            # Cap known tasks to prevent unbounded growth in daemon mode
            if len(self._known_task_ids) > self._max_known_tasks:
                # Evict oldest entries (convert to list, trim, back to set)
                overflow = len(self._known_task_ids) - self._max_known_tasks
                ids_list = list(self._known_task_ids)
                self._known_task_ids = set(ids_list[overflow:])
            new_count += 1

            # Map EM category to coordinator categories list
            em_category = task_data.get("category", "simple_action")
            categories = [em_category] if isinstance(em_category, str) else em_category

            # Map priority string to enum
            priority_str = task_data.get("priority", "normal").upper()
            try:
                from .orchestrator import TaskPriority

                priority = TaskPriority[priority_str]
            except (KeyError, ImportError):
                from .orchestrator import TaskPriority

                priority = TaskPriority.NORMAL

            # Ingest into coordinator queue
            self.coordinator.ingest_task(
                task_id=task_id,
                title=task_data.get("title", ""),
                categories=categories,
                bounty_usd=float(task_data.get("bounty_amount", 0)),
                priority=priority,
                source="em_api",
                raw_data=task_data,
            )

        result.tasks_new = new_count

    def _phase_enrich(self, result: CycleResult):
        """Phase 2: Enrich queued tasks with AutoJob intelligence."""
        autojob = getattr(self.coordinator, "autojob", None)
        if not autojob:
            return

        try:
            health = autojob.health_check()
            if health.get("status") == "ok":
                result.enrichment_source = "autojob"
                # Enrichment happens during routing via EnrichedOrchestrator
                result.tasks_enriched = result.tasks_new
        except Exception:
            result.enrichment_source = "none"

    def _phase_route(self, result: CycleResult):
        """Phase 3: Route queued tasks to best-fit agents."""
        if self.mode == RunMode.PASSIVE:
            # In passive mode, we discover and log but don't assign
            queue_summary = self.coordinator.get_queue_summary()
            result.tasks_routed = 0
            return

        if self.mode == RunMode.DRY_RUN:
            # Dry run: process queue but don't execute API calls
            queue_summary = self.coordinator.get_queue_summary()
            result.tasks_routed = queue_summary.get("pending", 0)
            return

        # Active mode: actually process the task queue
        process_result = self.coordinator.process_task_queue(
            max_tasks=self.max_tasks_per_cycle,
        )

        result.tasks_routed = process_result.get("assigned", 0)
        result.routing_failures = process_result.get("failed", 0)

    def _phase_monitor(self, result: CycleResult):
        """Phase 4: Check agent health — heartbeats, budgets, states."""
        health = self.coordinator.run_health_checks()

        agents_report = health.get("agents", {})
        result.health_checks_run = agents_report.get("checked", 0)
        result.agents_degraded = agents_report.get("degraded", 0)

        # Count active agents from lifecycle manager
        result.agents_active = sum(
            1
            for r in self.coordinator.lifecycle.agents.values()
            if r.state.value in ("idle", "active", "working", "cooldown")
        )
        result.agents_suspended = sum(
            1
            for r in self.coordinator.lifecycle.agents.values()
            if r.state.value == "suspended"
        )

    def _phase_collect(self, result: CycleResult):
        """Phase 5: Poll for completed/failed tasks, harvest evidence."""
        if not self.coordinator.em_client:
            return

        # Check for recently completed tasks
        completed = self.coordinator.em_client.list_tasks(
            status="completed",
            limit=20,
        )

        failed = self.coordinator.em_client.list_tasks(
            status="disputed",
            limit=10,
        )

        result.tasks_completed = len(completed)
        result.tasks_failed = len(failed)

        # Calculate bounty earned (from tasks we assigned)
        for task in completed:
            task_id = str(task.get("id", ""))
            bounty = float(task.get("bounty_amount", 0))
            if task_id in self._known_task_ids and bounty > 0:
                result.bounty_earned_usd += bounty

    def _phase_learn(self, result: CycleResult):
        """Phase 6: Update Skill DNA from completed evidence."""
        # Use EvidenceParser to extract skills from completed tasks
        # This integrates with AutoJob's evidence flywheel
        if not self.coordinator.em_client:
            return

        completed = self.coordinator.em_client.list_tasks(
            status="completed",
            limit=20,
        )

        for task in completed:
            worker_wallet = task.get("worker_wallet", "")
            if not worker_wallet:
                continue

            # Build evidence from task data
            evidence = {
                "category": task.get("category", ""),
                "quality_rating": task.get("quality_rating"),
                "completion_time_hours": task.get("completion_time_hours"),
                "bounty_amount": task.get("bounty_amount"),
            }

            # Update worker registry
            try:
                self.worker_registry.update_worker(worker_wallet, evidence)
                result.skill_updates += 1
            except Exception as e:
                logger.debug(
                    "Skill update failed for %s: %s", truncate_wallet(worker_wallet), e
                )

    def _phase_report(self, result: CycleResult):
        """Phase 7: Emit metrics, check EM health, persist state."""
        if self.coordinator.em_client:
            try:
                health = self.coordinator.em_client.get_health()
                result.em_api_healthy = health.get("status") == "healthy"
            except Exception:
                result.em_api_healthy = False

    # ── State Management ──────────────────────────────────────────────

    def _update_state(self, cycle: CycleResult):
        """Update runner state from cycle result."""
        self._state.total_cycles += 1
        self._state.last_cycle = cycle.cycle_number
        self._state.last_cycle_at = cycle.started_at
        self._state.total_tasks_routed += cycle.tasks_routed
        self._state.total_tasks_completed += cycle.tasks_completed
        self._state.total_bounty_earned_usd += cycle.bounty_earned_usd
        self._state.errors_total += len(cycle.errors)

    def _load_state(self):
        """Load persistent state from disk."""
        state_file = self.state_dir / "runner_state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                self._state = RunnerState.from_dict(data)
                logger.info(f"Loaded state: {self._state.total_cycles} previous cycles")
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")

    def _save_state(self):
        """Persist state to disk."""
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            state_file = self.state_dir / "runner_state.json"
            state_file.write_text(json.dumps(self._state.to_dict(), indent=2))
        except Exception as e:
            logger.warning(f"Failed to save state: {e}")

    def _setup_signals(self):
        """Set up signal handlers for graceful shutdown."""

        def _handle_sigterm(signum, frame):
            logger.info("Received SIGTERM, shutting down gracefully...")
            self._running = False

        def _handle_sigusr1(signum, frame):
            logger.info("Received SIGUSR1, forcing single cycle...")
            # This is a no-op in the main loop but can be used for diagnostics

        try:
            signal.signal(signal.SIGTERM, _handle_sigterm)
            signal.signal(signal.SIGUSR1, _handle_sigusr1)
        except (OSError, ValueError, AttributeError):
            # Signals may not be available in all environments
            pass

    # ── Dashboard & Diagnostics ───────────────────────────────────────

    def get_status(self) -> dict:
        """Get runner status for monitoring."""
        return {
            "running": self._running,
            "mode": self.mode.value,
            "state": self._state.to_dict(),
            "cycle_interval_seconds": self.cycle_interval,
            "known_tasks": len(self._known_task_ids),
            "recent_cycles": [c.to_dict() for c in self._cycle_history[-5:]],
            "coordinator_dashboard": self.coordinator.get_dashboard(),
        }

    def get_cycle_history(self, limit: int = 20) -> list[dict]:
        """Get recent cycle history."""
        return [c.to_dict() for c in self._cycle_history[-limit:]]


# ── CLI Entry Point ───────────────────────────────────────────────────────────


def main():
    """CLI entry point for the SwarmRunner."""
    import argparse

    parser = argparse.ArgumentParser(
        description="KK V2 SwarmRunner — Production daemon for agent swarm coordination"
    )
    parser.add_argument(
        "--mode",
        choices=["passive", "active", "dry_run"],
        default="passive",
        help="Runner mode: passive (observe only), active (full operation), dry_run (process without API calls)",
    )
    parser.add_argument(
        "--cycle-interval",
        type=float,
        default=120.0,
        help="Seconds between coordination cycles (default: 120)",
    )
    parser.add_argument(
        "--max-tasks", type=int, default=10, help="Max tasks per cycle (default: 10)"
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=0,
        help="Max cycles (0 = unlimited, default: 0)",
    )
    parser.add_argument(
        "--em-url",
        default="https://api.execution.market",
        help="Execution Market API URL",
    )
    parser.add_argument(
        "--autojob-url", default="https://autojob.cc", help="AutoJob API URL"
    )
    parser.add_argument(
        "--state-dir",
        default=None,
        help="Directory for persistent state (default: ~/.em-swarm)",
    )
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    runner = SwarmRunner.create(
        em_api_url=args.em_url,
        autojob_url=args.autojob_url,
        mode=args.mode,
        cycle_interval=args.cycle_interval,
        max_tasks_per_cycle=args.max_tasks,
        max_cycles=1 if args.once else args.max_cycles,
        state_dir=args.state_dir,
    )

    if args.once:
        result = runner.run_once()
        print(result.summary_line())
        if result.errors:
            for err in result.errors:
                print(f"  ❌ {err}")
    else:
        runner.run()


if __name__ == "__main__":
    main()
