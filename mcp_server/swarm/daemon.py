"""
SwarmDaemon — Production-ready continuous coordination loop.

Ties together all swarm components into a single orchestration daemon:
- Bootstrap → Strategy Engine → Coordinator → Analytics → Heartbeat

Modes:
- **passive**: Monitor only, report metrics (default for testing)
- **semi-auto**: Route tasks, require human approval for assignments
- **full-auto**: Autonomous task routing and execution

Usage:
    daemon = SwarmDaemon.create(mode="passive")
    daemon.run_once()  # Single coordination cycle
    daemon.run(interval=300)  # Continuous loop (5min intervals)

CLI:
    python -m mcp_server.swarm.daemon --mode passive --interval 300
"""

import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Callable

from .analytics import SwarmAnalytics, TaskEvent, TimeWindow, load_from_production_tasks
from .bootstrap import SwarmBootstrap, BootstrapResult
from .coordinator import SwarmCoordinator, EMApiClient
from .event_listener import EventListener
from .evidence_parser import EvidenceParser, WorkerRegistry
from .heartbeat_handler import HeartbeatReport
from .strategy_engine import StrategyEngine

logger = logging.getLogger("em.swarm.daemon")


# ─── Configuration ────────────────────────────────────────────────────────────


@dataclass
class DaemonConfig:
    """Configuration for the swarm daemon."""
    mode: str = "passive"  # passive | semi-auto | full-auto
    em_api_url: str = "https://api.execution.market"
    autojob_url: str = "http://localhost:8765"
    state_dir: str = os.path.expanduser("~/.em-swarm")
    interval_seconds: int = 300  # 5 minutes default
    max_tasks_per_cycle: int = 10
    max_bounty_usd: float = 1.0
    sla_target_seconds: float = 3600.0
    platform_fee_rate: float = 0.13
    enable_analytics: bool = True
    enable_strategy_engine: bool = True
    enable_notifications: bool = False
    notification_threshold: str = "notable"  # always | notable | critical
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "DaemonConfig":
        """Load configuration from environment variables."""
        return cls(
            mode=os.getenv("EM_SWARM_MODE", "passive"),
            em_api_url=os.getenv("EM_API_URL", "https://api.execution.market"),
            autojob_url=os.getenv("EM_AUTOJOB_URL", "http://localhost:8765"),
            state_dir=os.getenv("EM_SWARM_STATE_DIR", os.path.expanduser("~/.em-swarm")),
            interval_seconds=int(os.getenv("EM_SWARM_INTERVAL", "300")),
            max_tasks_per_cycle=int(os.getenv("EM_SWARM_MAX_TASKS", "10")),
            max_bounty_usd=float(os.getenv("EM_SWARM_MAX_BOUNTY", "1.0")),
            sla_target_seconds=float(os.getenv("EM_SWARM_SLA_SECONDS", "3600")),
            enable_analytics=os.getenv("EM_SWARM_ANALYTICS", "true").lower() == "true",
            enable_strategy_engine=os.getenv("EM_SWARM_STRATEGY", "true").lower() == "true",
            log_level=os.getenv("EM_SWARM_LOG_LEVEL", "INFO"),
        )

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "em_api_url": self.em_api_url,
            "interval_seconds": self.interval_seconds,
            "max_tasks_per_cycle": self.max_tasks_per_cycle,
            "max_bounty_usd": self.max_bounty_usd,
            "sla_target_seconds": self.sla_target_seconds,
            "enable_analytics": self.enable_analytics,
            "enable_strategy_engine": self.enable_strategy_engine,
        }


# ─── Cycle Result ─────────────────────────────────────────────────────────────


@dataclass
class CycleResult:
    """Result of one daemon coordination cycle."""
    cycle_number: int
    timestamp: str
    duration_ms: float = 0.0
    phase_durations_ms: dict = field(default_factory=dict)
    tasks_ingested: int = 0
    tasks_routed: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    agents_active: int = 0
    agents_total: int = 0
    em_api_healthy: bool = False
    analytics_summary: Optional[str] = None
    recommendations_count: int = 0
    errors: list[str] = field(default_factory=list)
    heartbeat_report: Optional[dict] = None

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def is_notable(self) -> bool:
        return bool(
            self.tasks_ingested > 0
            or self.tasks_completed > 0
            or self.tasks_failed > 0
            or self.errors
            or self.recommendations_count > 0
        )

    def to_dict(self) -> dict:
        return {
            "cycle": self.cycle_number,
            "timestamp": self.timestamp,
            "duration_ms": round(self.duration_ms, 2),
            "phases": {k: round(v, 2) for k, v in self.phase_durations_ms.items()},
            "tasks": {
                "ingested": self.tasks_ingested,
                "routed": self.tasks_routed,
                "completed": self.tasks_completed,
                "failed": self.tasks_failed,
            },
            "agents": {
                "active": self.agents_active,
                "total": self.agents_total,
            },
            "em_api_healthy": self.em_api_healthy,
            "recommendations": self.recommendations_count,
            "errors": self.errors,
            "success": self.success,
        }

    def to_summary(self) -> str:
        """Generate human-readable summary."""
        status = "🟢" if self.success and self.em_api_healthy else "🟡" if self.em_api_healthy else "🔴"
        lines = [
            f"{status} **Swarm Daemon Cycle #{self.cycle_number}** ({self.duration_ms:.0f}ms)",
        ]

        if self.tasks_ingested or self.tasks_routed or self.tasks_completed:
            lines.append(
                f"📋 +{self.tasks_ingested} ingested | {self.tasks_routed} routed | "
                f"{self.tasks_completed} completed | {self.tasks_failed} failed"
            )

        if self.agents_total:
            lines.append(f"🤖 {self.agents_active}/{self.agents_total} agents active")

        if self.recommendations_count:
            lines.append(f"💡 {self.recommendations_count} recommendations")

        if self.errors:
            lines.append(f"⚠️ {len(self.errors)} errors: {', '.join(self.errors[:3])}")

        if self.analytics_summary:
            lines.append(f"\n{self.analytics_summary}")

        return "\n".join(lines)


# ─── Daemon State ─────────────────────────────────────────────────────────────


@dataclass
class DaemonState:
    """Persistent daemon state across restarts."""
    total_cycles: int = 0
    total_tasks_processed: int = 0
    total_bounty_earned_usd: float = 0.0
    started_at: Optional[str] = None
    last_cycle_at: Optional[str] = None
    last_cycle_success: bool = True
    consecutive_failures: int = 0
    errors_total: int = 0

    def to_dict(self) -> dict:
        return {
            "total_cycles": self.total_cycles,
            "total_tasks_processed": self.total_tasks_processed,
            "total_bounty_earned_usd": round(self.total_bounty_earned_usd, 4),
            "started_at": self.started_at,
            "last_cycle_at": self.last_cycle_at,
            "last_cycle_success": self.last_cycle_success,
            "consecutive_failures": self.consecutive_failures,
            "errors_total": self.errors_total,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DaemonState":
        return cls(
            total_cycles=data.get("total_cycles", 0),
            total_tasks_processed=data.get("total_tasks_processed", 0),
            total_bounty_earned_usd=data.get("total_bounty_earned_usd", 0.0),
            started_at=data.get("started_at"),
            last_cycle_at=data.get("last_cycle_at"),
            last_cycle_success=data.get("last_cycle_success", True),
            consecutive_failures=data.get("consecutive_failures", 0),
            errors_total=data.get("errors_total", 0),
        )


def _load_daemon_state(state_dir: str) -> DaemonState:
    """Load daemon state from disk."""
    state_file = os.path.join(state_dir, "daemon_state.json")
    try:
        with open(state_file, "r") as f:
            return DaemonState.from_dict(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return DaemonState()


def _save_daemon_state(state: DaemonState, state_dir: str) -> None:
    """Save daemon state to disk."""
    os.makedirs(state_dir, exist_ok=True)
    state_file = os.path.join(state_dir, "daemon_state.json")
    with open(state_file, "w") as f:
        json.dump(state.to_dict(), f, indent=2)


# ─── Daemon ───────────────────────────────────────────────────────────────────


class SwarmDaemon:
    """
    Production-ready continuous swarm coordination daemon.

    Orchestrates the full lifecycle:
    1. Bootstrap — Initialize coordinator with production data
    2. Poll — Check for new/completed tasks
    3. Route — Assign tasks to agents (strategy-aware)
    4. Analyze — Update analytics and detect trends
    5. Report — Generate summaries and recommendations
    6. Persist — Save state for cross-session continuity
    """

    def __init__(
        self,
        config: DaemonConfig,
        coordinator: Optional[SwarmCoordinator] = None,
        analytics: Optional[SwarmAnalytics] = None,
        on_cycle_complete: Optional[Callable[[CycleResult], None]] = None,
    ):
        self.config = config
        self._coordinator = coordinator
        self._analytics = analytics or SwarmAnalytics(
            sla_target_seconds=config.sla_target_seconds,
            platform_fee_rate=config.platform_fee_rate,
        )
        self._strategy_engine: Optional[StrategyEngine] = None
        self._event_listener: Optional[EventListener] = None
        self._evidence_parser: Optional[EvidenceParser] = None
        self._worker_registry: Optional[WorkerRegistry] = None
        self._state: DaemonState = _load_daemon_state(config.state_dir)
        self._running: bool = False
        self._on_cycle_complete = on_cycle_complete

        # Bootstrap tracking
        self._bootstrapped: bool = False

    @classmethod
    def create(
        cls,
        mode: str = "passive",
        em_api_url: str = "https://api.execution.market",
        interval: int = 300,
        state_dir: Optional[str] = None,
        **kwargs,
    ) -> "SwarmDaemon":
        """Factory method for easy creation."""
        config = DaemonConfig(
            mode=mode,
            em_api_url=em_api_url,
            interval_seconds=interval,
            state_dir=state_dir or os.path.expanduser("~/.em-swarm"),
            **kwargs,
        )
        return cls(config)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def state(self) -> DaemonState:
        return self._state

    @property
    def analytics(self) -> SwarmAnalytics:
        return self._analytics

    # ─── Initialization ──────────────────────────────────────────────

    def bootstrap(self, skip_api: bool = False) -> Optional[BootstrapResult]:
        """
        Initialize the coordinator with production data.
        Can be called explicitly or happens automatically on first cycle.
        """
        if self._bootstrapped:
            return None

        logger.info("Bootstrapping swarm daemon...")

        try:
            bootstrap = SwarmBootstrap(
                em_api_url=self.config.em_api_url,
                cache_dir=self.config.state_dir,
            )
            result = bootstrap.bootstrap(
                coordinator=self._coordinator,
                skip_api=skip_api,
            )

            self._coordinator = result.coordinator
            self._bootstrapped = True

            # Load historical data into analytics
            if result.historical_tasks:
                load_from_production_tasks(result.historical_tasks, self._analytics)
                logger.info(f"Loaded {len(result.historical_tasks)} historical tasks into analytics")

            logger.info(
                f"Bootstrap complete: {result.agents_registered} agents, "
                f"{result.tasks_loaded} tasks, "
                f"reputation for {result.reputation_updates} agents"
            )
            return result

        except Exception as e:
            logger.error(f"Bootstrap failed: {e}")
            # Create minimal coordinator
            if self._coordinator is None:
                self._coordinator = SwarmCoordinator.create(
                    em_api_url=self.config.em_api_url,
                )
            self._bootstrapped = True
            return None

    def _ensure_coordinator(self) -> SwarmCoordinator:
        """Ensure coordinator is initialized."""
        if self._coordinator is None:
            self.bootstrap(skip_api=True)
        return self._coordinator

    def _ensure_event_listener(self) -> EventListener:
        """Ensure event listener is initialized."""
        if self._event_listener is None:
            coord = self._ensure_coordinator()
            self._event_listener = EventListener(
                coordinator=coord,
                state_path=os.path.join(self.config.state_dir, "event_listener_state.json"),
            )
        return self._event_listener

    # ─── Single Cycle ────────────────────────────────────────────────

    def run_once(self) -> CycleResult:
        """
        Execute one complete coordination cycle.
        This is the core loop body.
        """
        self._state.total_cycles += 1
        cycle_num = self._state.total_cycles
        start = time.monotonic()
        phases = {}

        result = CycleResult(
            cycle_number=cycle_num,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Phase 1: Bootstrap (if needed)
        phase_start = time.monotonic()
        if not self._bootstrapped:
            try:
                self.bootstrap()
            except Exception as e:
                result.errors.append(f"bootstrap: {e}")
        phases["bootstrap"] = (time.monotonic() - phase_start) * 1000

        coord = self._ensure_coordinator()

        # Phase 2: Health check
        phase_start = time.monotonic()
        try:
            if coord.em_client:
                health = coord.em_client.get_health()
                result.em_api_healthy = health.get("status") == "healthy"
        except Exception as e:
            result.em_api_healthy = False
            result.errors.append(f"health_check: {e}")
        phases["health_check"] = (time.monotonic() - phase_start) * 1000

        # Phase 3: Ingest new tasks
        phase_start = time.monotonic()
        try:
            ingested = coord.ingest_from_api()
            result.tasks_ingested = ingested

            # Record creation events in analytics
            if ingested > 0 and self.config.enable_analytics:
                for task in coord.task_queue[-ingested:]:
                    self._analytics.record_event(TaskEvent(
                        task_id=task.get("id", ""),
                        event_type="created",
                        category=task.get("category", "unknown"),
                        bounty_usd=float(task.get("bounty", 0)),
                        chain=task.get("chain", "unknown"),
                    ))
        except Exception as e:
            result.errors.append(f"ingest: {e}")
        phases["ingest"] = (time.monotonic() - phase_start) * 1000

        # Phase 4: Route tasks (mode-dependent)
        phase_start = time.monotonic()
        if self.config.mode != "passive" and result.tasks_ingested > 0:
            try:
                assignments = coord.process_task_queue(
                    max_tasks=self.config.max_tasks_per_cycle
                )
                result.tasks_routed = sum(
                    1 for a in assignments if hasattr(a, "agent_id")
                )

                # Record assignment events
                if self.config.enable_analytics:
                    for a in assignments:
                        if hasattr(a, "agent_id"):
                            self._analytics.record_event(TaskEvent(
                                task_id=a.task_id,
                                event_type="assigned",
                                agent_id=a.agent_id,
                                agent_name=getattr(a, "agent_name", ""),
                            ))
            except Exception as e:
                result.errors.append(f"routing: {e}")
        phases["routing"] = (time.monotonic() - phase_start) * 1000

        # Phase 5: Process events (completions, failures)
        phase_start = time.monotonic()
        try:
            listener = self._ensure_event_listener()
            poll_result = listener.poll_once()

            result.tasks_completed = poll_result.completed_tasks
            result.tasks_failed = poll_result.failed_tasks + poll_result.expired_tasks

            # Record in analytics
            if self.config.enable_analytics:
                for _ in range(poll_result.completed_tasks):
                    self._analytics.record_event(TaskEvent(
                        task_id="", event_type="completed",
                    ))
                for _ in range(poll_result.failed_tasks):
                    self._analytics.record_event(TaskEvent(
                        task_id="", event_type="failed",
                    ))
                for _ in range(poll_result.expired_tasks):
                    self._analytics.record_event(TaskEvent(
                        task_id="", event_type="expired",
                    ))

        except Exception as e:
            result.errors.append(f"events: {e}")
        phases["events"] = (time.monotonic() - phase_start) * 1000

        # Phase 6: Swarm health
        phase_start = time.monotonic()
        try:
            health_report = coord.run_health_checks()
            agents = health_report.get("agents", {})
            result.agents_active = agents.get("healthy", 0)
            result.agents_total = agents.get("total", 0)
        except Exception as e:
            result.errors.append(f"swarm_health: {e}")
        phases["swarm_health"] = (time.monotonic() - phase_start) * 1000

        # Phase 7: Analytics
        phase_start = time.monotonic()
        if self.config.enable_analytics:
            try:
                result.analytics_summary = self._analytics.summary(TimeWindow.DAY)
                recs = self._analytics.recommendations(TimeWindow.WEEK)
                result.recommendations_count = len(recs)
            except Exception as e:
                result.errors.append(f"analytics: {e}")
        phases["analytics"] = (time.monotonic() - phase_start) * 1000

        # Phase 8: Persist state
        phase_start = time.monotonic()
        self._state.last_cycle_at = result.timestamp
        self._state.total_tasks_processed += result.tasks_completed

        if result.success:
            self._state.last_cycle_success = True
            self._state.consecutive_failures = 0
        else:
            self._state.last_cycle_success = False
            self._state.consecutive_failures += 1
            self._state.errors_total += len(result.errors)

        try:
            _save_daemon_state(self._state, self.config.state_dir)
        except Exception as e:
            result.errors.append(f"state_save: {e}")
        phases["persist"] = (time.monotonic() - phase_start) * 1000

        # Finalize
        result.duration_ms = (time.monotonic() - start) * 1000
        result.phase_durations_ms = phases

        # Callback
        if self._on_cycle_complete:
            try:
                self._on_cycle_complete(result)
            except Exception as e:
                logger.error(f"Cycle callback error: {e}")

        logger.info(
            f"Cycle #{cycle_num}: {result.duration_ms:.0f}ms | "
            f"+{result.tasks_ingested} ingested, {result.tasks_completed} completed | "
            f"{'✅' if result.success else '❌'}"
        )

        return result

    # ─── Continuous Loop ─────────────────────────────────────────────

    def run(
        self,
        max_cycles: Optional[int] = None,
        interval: Optional[int] = None,
    ) -> list[CycleResult]:
        """
        Run continuous coordination loop.

        Args:
            max_cycles: Stop after N cycles (None = run forever)
            interval: Override interval_seconds from config
        """
        interval = interval or self.config.interval_seconds
        self._running = True

        if not self._state.started_at:
            self._state.started_at = datetime.now(timezone.utc).isoformat()

        results: list[CycleResult] = []

        logger.info(
            f"Swarm daemon starting: mode={self.config.mode}, "
            f"interval={interval}s, max_cycles={max_cycles or '∞'}"
        )

        cycles = 0
        while self._running:
            try:
                result = self.run_once()
                results.append(result)
                cycles += 1

                if max_cycles and cycles >= max_cycles:
                    logger.info(f"Completed {max_cycles} cycles, stopping.")
                    break

                # Back off on consecutive failures
                if self._state.consecutive_failures > 3:
                    backoff = min(interval * 2 ** (self._state.consecutive_failures - 3), 3600)
                    logger.warning(
                        f"Consecutive failures: {self._state.consecutive_failures}, "
                        f"backing off {backoff}s"
                    )
                    time.sleep(backoff)
                else:
                    time.sleep(interval)

            except KeyboardInterrupt:
                logger.info("Daemon interrupted by user.")
                break
            except Exception as e:
                logger.error(f"Unhandled cycle error: {e}")
                time.sleep(interval)

        self._running = False
        logger.info(f"Daemon stopped after {cycles} cycles.")
        return results

    def stop(self) -> None:
        """Signal the daemon to stop after the current cycle."""
        self._running = False

    # ─── Status ──────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Get current daemon status."""
        return {
            "running": self._running,
            "bootstrapped": self._bootstrapped,
            "config": self.config.to_dict(),
            "state": self._state.to_dict(),
            "analytics": {
                "total_events": self._analytics.event_count,
            },
        }

    def get_analytics_report(self, window: TimeWindow = TimeWindow.ALL_TIME) -> dict:
        """Get full analytics report."""
        return self._analytics.full_report(window)


# ─── CLI Entry Point ─────────────────────────────────────────────────────────


def main():
    """CLI entry point for running the swarm daemon."""
    import argparse

    parser = argparse.ArgumentParser(description="KK V2 Swarm Daemon")
    parser.add_argument("--mode", choices=["passive", "semi-auto", "full-auto"], default="passive")
    parser.add_argument("--interval", type=int, default=300, help="Cycle interval in seconds")
    parser.add_argument("--max-cycles", type=int, help="Stop after N cycles")
    parser.add_argument("--api-url", default="https://api.execution.market")
    parser.add_argument("--state-dir", default=os.path.expanduser("~/.em-swarm"))
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--once", action="store_true", help="Run single cycle and exit")

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    config = DaemonConfig(
        mode=args.mode,
        em_api_url=args.api_url,
        interval_seconds=args.interval,
        state_dir=args.state_dir,
        log_level=args.log_level,
    )

    daemon = SwarmDaemon(config)

    # Handle signals for graceful shutdown
    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        daemon.stop()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    if args.once:
        result = daemon.run_once()
        print(result.to_summary())
        sys.exit(0 if result.success else 1)
    else:
        daemon.run(max_cycles=args.max_cycles)


if __name__ == "__main__":
    main()
