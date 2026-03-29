"""
SwarmIntegrator — Top-level orchestration layer for the KK V2 Swarm.

Wires together all swarm components into a unified system:

    ┌─────────────────────────────────────────────────────┐
    │                 SwarmIntegrator                       │
    │                                                      │
    │  ┌──────────┐   ┌──────────┐   ┌────────────────┐  │
    │  │Coordinator│──►│ EventBus │──►│  XMTPBridge    │  │
    │  └──────────┘   │          │   └────────────────┘  │
    │                  │          │                        │
    │  ┌──────────┐   │          │   ┌────────────────┐  │
    │  │ Scheduler │──►│          │──►│FeedbackPipeline│  │
    │  └──────────┘   │          │   └────────────────┘  │
    │                  │          │                        │
    │  ┌──────────┐   │          │   ┌────────────────┐  │
    │  │  Runner  │──►│          │──►│   Analytics    │  │
    │  └──────────┘   └──────────┘   └────────────────┘  │
    │                                                      │
    │  ┌──────────┐   ┌────────────┐  ┌──────────────┐   │
    │  │Dashboard │   │ExpiryAnalyz│  │ConfigManager │   │
    │  └──────────┘   └────────────┘  └──────────────┘   │
    └─────────────────────────────────────────────────────┘

This module provides:
    1. Component lifecycle management (init, start, stop)
    2. Event bus wiring between all components
    3. Integrated health checks across all systems
    4. Operational modes (passive, semi-auto, full-auto)
    5. Graceful degradation when components fail

Usage:
    integrator = SwarmIntegrator.create(
        api_url="https://api.execution.market",
        mode="passive",
    )
    await integrator.start()

    # Check health
    health = integrator.health()

    # Run a single cycle
    result = integrator.run_cycle()

    # Shutdown
    await integrator.stop()
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger("em.swarm.integrator")


# ─── Types ────────────────────────────────────────────────────────


class SwarmMode(str, Enum):
    """Operational modes with increasing autonomy."""

    PASSIVE = "passive"  # Observe only — no task assignments
    SEMI_AUTO = "semi_auto"  # Auto-assign tasks under bounty threshold
    FULL_AUTO = "full_auto"  # Full autonomous operation
    DISABLED = "disabled"  # All components stopped


@dataclass
class ComponentStatus:
    """Health status of a single component."""

    name: str
    healthy: bool
    initialized: bool = False
    last_error: Optional[str] = None
    last_activity: Optional[float] = None
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "healthy": self.healthy,
            "initialized": self.initialized,
            "last_error": self.last_error,
            "last_activity_ago": (
                f"{time.time() - self.last_activity:.0f}s"
                if self.last_activity
                else None
            ),
            "metrics": self.metrics,
        }


@dataclass
class CycleResult:
    """Result of a single swarm cycle."""

    cycle_number: int
    mode: str
    started_at: float
    duration_ms: float
    phases_completed: list[str] = field(default_factory=list)
    phases_failed: list[str] = field(default_factory=list)
    tasks_ingested: int = 0
    tasks_assigned: int = 0
    tasks_scored: int = 0
    feedback_processed: int = 0
    events_emitted: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.phases_failed) == 0

    def to_dict(self) -> dict:
        return {
            "cycle": self.cycle_number,
            "mode": self.mode,
            "duration_ms": round(self.duration_ms, 1),
            "success": self.success,
            "phases_completed": self.phases_completed,
            "phases_failed": self.phases_failed,
            "tasks": {
                "ingested": self.tasks_ingested,
                "assigned": self.tasks_assigned,
                "scored": self.tasks_scored,
            },
            "feedback_processed": self.feedback_processed,
            "events_emitted": self.events_emitted,
            "errors": self.errors,
        }


# ─── SwarmIntegrator ──────────────────────────────────────────────


class SwarmIntegrator:
    """
    Top-level swarm orchestrator. Manages component lifecycle,
    event routing, and operational modes.
    """

    def __init__(
        self,
        mode: SwarmMode = SwarmMode.PASSIVE,
        bounty_threshold: float = 0.25,
        max_cycle_errors: int = 5,
    ):
        self.mode = mode
        self.bounty_threshold = bounty_threshold
        self.max_cycle_errors = max_cycle_errors

        # Components (lazy-initialized)
        self._event_bus = None
        self._coordinator = None
        self._scheduler = None
        self._runner = None
        self._dashboard = None
        self._feedback_pipeline = None
        self._xmtp_bridge = None
        self._expiry_analyzer = None
        self._config_manager = None
        self._analytics = None
        self._verification_adapter = None
        self._decision_synthesizer = None

        # State
        self._started = False
        self._cycle_count = 0
        self._consecutive_errors = 0
        self._component_statuses: dict[str, ComponentStatus] = {}
        self._start_time: Optional[float] = None
        self._last_cycle_time: Optional[float] = None
        self._cycle_history: list[CycleResult] = []
        self._event_handlers: list = []
        self._hooks: dict[str, list[Callable]] = {
            "pre_cycle": [],
            "post_cycle": [],
            "on_error": [],
            "on_assignment": [],
            "on_mode_change": [],
        }

    # ─── Component Registration ───────────────────────────────

    def set_event_bus(self, bus) -> "SwarmIntegrator":
        """Register the EventBus."""
        self._event_bus = bus
        self._register_component("event_bus", bus)
        return self

    def set_coordinator(self, coordinator) -> "SwarmIntegrator":
        """Register the SwarmCoordinator."""
        self._coordinator = coordinator
        self._register_component("coordinator", coordinator)
        return self

    def set_scheduler(self, scheduler) -> "SwarmIntegrator":
        """Register the Scheduler."""
        self._scheduler = scheduler
        self._register_component("scheduler", scheduler)
        return self

    def set_runner(self, runner) -> "SwarmIntegrator":
        """Register the Runner."""
        self._runner = runner
        self._register_component("runner", runner)
        return self

    def set_dashboard(self, dashboard) -> "SwarmIntegrator":
        """Register the Dashboard."""
        self._dashboard = dashboard
        self._register_component("dashboard", dashboard)
        return self

    def set_feedback_pipeline(self, pipeline) -> "SwarmIntegrator":
        """Register the FeedbackPipeline."""
        self._feedback_pipeline = pipeline
        self._register_component("feedback_pipeline", pipeline)
        return self

    def set_xmtp_bridge(self, bridge) -> "SwarmIntegrator":
        """Register the XMTPBridge."""
        self._xmtp_bridge = bridge
        self._register_component("xmtp_bridge", bridge)
        return self

    def set_expiry_analyzer(self, analyzer) -> "SwarmIntegrator":
        """Register the ExpiryAnalyzer."""
        self._expiry_analyzer = analyzer
        self._register_component("expiry_analyzer", analyzer)
        return self

    def set_config_manager(self, config) -> "SwarmIntegrator":
        """Register the ConfigManager."""
        self._config_manager = config
        self._register_component("config_manager", config)
        return self

    def set_analytics(self, analytics) -> "SwarmIntegrator":
        """Register the Analytics module."""
        self._analytics = analytics
        self._register_component("analytics", analytics)
        return self

    def set_decision_synthesizer(self, synthesizer) -> "SwarmIntegrator":
        """Register the DecisionSynthesizer."""
        self._decision_synthesizer = synthesizer
        self._register_component("decision_synthesizer", synthesizer)
        return self

    def set_verification_adapter(self, adapter) -> "SwarmIntegrator":
        """
        Register the VerificationAdapter (PHOTINT evidence quality).

        If a DecisionSynthesizer is already registered, automatically
        wires the adapter as Signal #13 (verification_quality).
        """
        self._verification_adapter = adapter
        self._register_component("verification_adapter", adapter)

        # Auto-wire into DecisionSynthesizer if available
        if self._decision_synthesizer is not None:
            try:
                from .decision_synthesizer import SignalType
                self._decision_synthesizer.register_signal(
                    SignalType.VERIFICATION_QUALITY,
                    adapter.score,
                )
                logger.info(
                    "VerificationAdapter wired into DecisionSynthesizer as Signal #13"
                )
            except Exception as e:
                logger.warning(f"Failed to wire VerificationAdapter: {e}")
        return self

    def _register_component(self, name: str, component) -> None:
        """Track a component's health status."""
        self._component_statuses[name] = ComponentStatus(
            name=name,
            healthy=True,
            initialized=True,
            last_activity=time.time(),
        )
        logger.info(f"Component registered: {name}")

    # ─── Hooks ────────────────────────────────────────────────

    def on(self, hook: str, callback: Callable) -> None:
        """Register a lifecycle hook."""
        if hook not in self._hooks:
            raise ValueError(f"Unknown hook: {hook}. Available: {list(self._hooks)}")
        self._hooks[hook].append(callback)

    def _fire_hooks(self, hook: str, **kwargs) -> None:
        """Fire all callbacks for a hook."""
        for cb in self._hooks.get(hook, []):
            try:
                cb(**kwargs)
            except Exception as e:
                logger.error(f"Hook {hook} error: {e}")

    # ─── Wiring ───────────────────────────────────────────────

    def wire(self) -> "SwarmIntegrator":
        """
        Wire all registered components together via the EventBus.
        Call after all components are registered.
        """
        if not self._event_bus:
            logger.warning("No EventBus — skipping wiring")
            return self

        bus = self._event_bus
        subscriptions = []

        # Wire XMTP bridge for worker notifications
        if self._xmtp_bridge:
            try:
                subs = bus.wire_xmtp_bridge(self._xmtp_bridge)
                subscriptions.extend(subs)
                logger.info("Wired: EventBus → XMTPBridge")
            except Exception as e:
                logger.error(f"Failed to wire XMTPBridge: {e}")
                self._mark_unhealthy("xmtp_bridge", str(e))

        # Wire feedback pipeline for learning
        if self._feedback_pipeline:
            try:
                from .event_bus import TASK_COMPLETED

                def on_task_completed(event):
                    try:
                        task_data = event.data.get("task_data", {})
                        if task_data:
                            self._feedback_pipeline.process_completion(task_data)
                    except Exception as e:
                        logger.error(f"Feedback pipeline error: {e}")

                sub = bus.on(TASK_COMPLETED, on_task_completed, source="feedback")
                subscriptions.append(sub)
                logger.info("Wired: EventBus → FeedbackPipeline")
            except Exception as e:
                logger.error(f"Failed to wire FeedbackPipeline: {e}")
                self._mark_unhealthy("feedback_pipeline", str(e))

        # Wire analytics recorder
        if self._analytics:
            try:

                def analytics_recorder(event):
                    try:
                        if hasattr(self._analytics, "record_event"):
                            self._analytics.record_event(
                                event.type,
                                event.data,
                                source=event.source,
                            )
                    except Exception as e:
                        logger.error(f"Analytics recorder error: {e}")

                sub = bus.wire_analytics(analytics_recorder)
                subscriptions.append(sub)
                logger.info("Wired: EventBus → Analytics")
            except Exception as e:
                logger.error(f"Failed to wire Analytics: {e}")
                self._mark_unhealthy("analytics", str(e))

        # Wire expiry analyzer for task.expired events
        if self._expiry_analyzer:
            try:
                from .event_bus import TASK_EXPIRED

                def on_task_expired(event):
                    try:
                        if hasattr(self._expiry_analyzer, "record_expiry"):
                            self._expiry_analyzer.record_expiry(event.data)
                    except Exception as e:
                        logger.error(f"Expiry analyzer error: {e}")

                sub = bus.on(TASK_EXPIRED, on_task_expired, source="expiry")
                subscriptions.append(sub)
                logger.info("Wired: EventBus → ExpiryAnalyzer")
            except Exception as e:
                logger.error(f"Failed to wire ExpiryAnalyzer: {e}")
                self._mark_unhealthy("expiry_analyzer", str(e))

        self._event_handlers = subscriptions
        logger.info(
            f"Wiring complete: {len(subscriptions)} subscriptions across "
            f"{len(self._component_statuses)} components"
        )
        return self

    def _mark_unhealthy(self, component: str, error: str) -> None:
        """Mark a component as unhealthy."""
        if component in self._component_statuses:
            self._component_statuses[component].healthy = False
            self._component_statuses[component].last_error = error

    # ─── Lifecycle ────────────────────────────────────────────

    def start(self) -> dict:
        """Start the swarm integrator."""
        if self._started:
            return {"status": "already_running", "mode": self.mode.value}

        self._started = True
        self._start_time = time.time()
        self._consecutive_errors = 0

        # Emit swarm.started event
        if self._event_bus:
            self._event_bus.emit(
                "swarm.started",
                {
                    "mode": self.mode.value,
                    "components": list(self._component_statuses.keys()),
                    "bounty_threshold": self.bounty_threshold,
                },
            )

        logger.info(
            f"SwarmIntegrator started: mode={self.mode.value}, "
            f"components={len(self._component_statuses)}"
        )

        return {
            "status": "started",
            "mode": self.mode.value,
            "components": len(self._component_statuses),
            "bounty_threshold": self.bounty_threshold,
        }

    def stop(self) -> dict:
        """Stop the swarm integrator."""
        if not self._started:
            return {"status": "not_running"}

        self._started = False
        uptime = time.time() - (self._start_time or time.time())

        if self._event_bus:
            self._event_bus.emit(
                "swarm.stopped",
                {
                    "uptime_seconds": uptime,
                    "cycles_completed": self._cycle_count,
                },
            )

        logger.info(
            f"SwarmIntegrator stopped after {uptime:.0f}s, {self._cycle_count} cycles"
        )

        return {
            "status": "stopped",
            "uptime_seconds": round(uptime, 1),
            "cycles_completed": self._cycle_count,
        }

    def set_mode(self, mode: SwarmMode) -> dict:
        """Change the operational mode."""
        old_mode = self.mode
        self.mode = mode
        self._fire_hooks("on_mode_change", old_mode=old_mode, new_mode=mode)

        if self._event_bus:
            self._event_bus.emit(
                "swarm.mode_changed",
                {
                    "old_mode": old_mode.value,
                    "new_mode": mode.value,
                },
            )

        logger.info(f"Mode changed: {old_mode.value} → {mode.value}")
        return {"old_mode": old_mode.value, "new_mode": mode.value}

    # ─── Cycle Execution ──────────────────────────────────────

    def run_cycle(self, dry_run: bool = False) -> CycleResult:
        """
        Execute one full swarm cycle:
        1. Ingest tasks from EM API
        2. Score & prioritize tasks
        3. Route tasks to agents (if mode allows)
        4. Process feedback from completions
        5. Update analytics
        6. Emit events

        Returns a CycleResult with metrics.
        """
        self._cycle_count += 1
        start_time = time.time()
        result = CycleResult(
            cycle_number=self._cycle_count,
            mode=self.mode.value,
            started_at=start_time,
            duration_ms=0,
        )

        self._fire_hooks("pre_cycle", cycle=self._cycle_count)

        if self._event_bus:
            from .event_bus import SWARM_CYCLE_START

            self._event_bus.emit(
                SWARM_CYCLE_START,
                {"cycle": self._cycle_count, "mode": self.mode.value},
            )

        # Phase 1: Ingest tasks
        result = self._phase_ingest(result, dry_run)

        # Phase 2: Score & schedule
        result = self._phase_score(result)

        # Phase 3: Route assignments (mode-dependent)
        result = self._phase_route(result, dry_run)

        # Phase 4: Process feedback
        result = self._phase_feedback(result)

        # Phase 5: Analytics
        result = self._phase_analytics(result)

        # Phase 6: Dashboard update
        result = self._phase_dashboard(result)

        # Finalize
        result.duration_ms = (time.time() - start_time) * 1000
        self._last_cycle_time = time.time()

        # Track errors
        if result.success:
            self._consecutive_errors = 0
        else:
            self._consecutive_errors += 1

        # Store in history (keep last 50)
        self._cycle_history.append(result)
        if len(self._cycle_history) > 50:
            self._cycle_history = self._cycle_history[-50:]

        if self._event_bus:
            self._event_bus.emit(
                "swarm.cycle.end",
                result.to_dict(),
            )

        self._fire_hooks("post_cycle", result=result)

        logger.info(
            f"Cycle {self._cycle_count} complete: "
            f"{len(result.phases_completed)}/{len(result.phases_completed) + len(result.phases_failed)} phases, "
            f"{result.duration_ms:.0f}ms"
        )

        return result

    def _phase_ingest(self, result: CycleResult, dry_run: bool) -> CycleResult:
        """Phase 1: Ingest tasks from EM API."""
        if not self._coordinator:
            return result

        try:
            if hasattr(self._coordinator, "ingest_live_tasks"):
                ingested = self._coordinator.ingest_live_tasks()
                result.tasks_ingested = ingested if isinstance(ingested, int) else 0
            elif hasattr(self._coordinator, "get_pending_count"):
                result.tasks_ingested = self._coordinator.get_pending_count()
            result.phases_completed.append("ingest")
            self._touch_component("coordinator")
        except Exception as e:
            result.phases_failed.append("ingest")
            result.errors.append(f"ingest: {e}")
            self._mark_unhealthy("coordinator", str(e))
            logger.error(f"Phase ingest failed: {e}")

        return result

    def _phase_score(self, result: CycleResult) -> CycleResult:
        """Phase 2: Score and prioritize tasks."""
        if not self._scheduler:
            return result

        try:
            if hasattr(self._scheduler, "score_tasks"):
                scored = self._scheduler.score_tasks()
                result.tasks_scored = scored if isinstance(scored, int) else 0
            result.phases_completed.append("score")
            self._touch_component("scheduler")
        except Exception as e:
            result.phases_failed.append("score")
            result.errors.append(f"score: {e}")
            self._mark_unhealthy("scheduler", str(e))
            logger.error(f"Phase score failed: {e}")

        return result

    def _phase_route(self, result: CycleResult, dry_run: bool) -> CycleResult:
        """Phase 3: Route tasks to agents (respects mode)."""
        if self.mode == SwarmMode.DISABLED:
            return result

        if not self._coordinator:
            return result

        try:
            if self.mode == SwarmMode.PASSIVE or dry_run:
                # Simulate without actual assignment
                if hasattr(self._coordinator, "simulate_routing"):
                    sim = self._coordinator.simulate_routing()
                    result.tasks_assigned = (
                        sim.get("assigned", 0) if isinstance(sim, dict) else 0
                    )
                result.phases_completed.append("route_sim")
            elif self.mode == SwarmMode.SEMI_AUTO:
                # Only assign tasks under bounty threshold
                if hasattr(self._coordinator, "route_tasks"):
                    assigned = self._coordinator.route_tasks(
                        max_bounty=self.bounty_threshold
                    )
                    result.tasks_assigned = assigned if isinstance(assigned, int) else 0
                result.phases_completed.append("route")
            elif self.mode == SwarmMode.FULL_AUTO:
                if hasattr(self._coordinator, "route_tasks"):
                    assigned = self._coordinator.route_tasks()
                    result.tasks_assigned = assigned if isinstance(assigned, int) else 0
                result.phases_completed.append("route")

            self._touch_component("coordinator")

            # Emit assignment events
            if result.tasks_assigned > 0 and self._event_bus:
                from .event_bus import TASK_ASSIGNED

                self._event_bus.emit(
                    TASK_ASSIGNED,
                    {"count": result.tasks_assigned, "mode": self.mode.value},
                )
                self._fire_hooks("on_assignment", count=result.tasks_assigned)

        except Exception as e:
            result.phases_failed.append("route")
            result.errors.append(f"route: {e}")
            self._mark_unhealthy("coordinator", str(e))
            logger.error(f"Phase route failed: {e}")

        return result

    def _phase_feedback(self, result: CycleResult) -> CycleResult:
        """Phase 4: Process feedback from completed tasks."""
        if not self._feedback_pipeline:
            return result

        try:
            if hasattr(self._feedback_pipeline, "process_live"):
                processed = self._feedback_pipeline.process_live()
                result.feedback_processed = (
                    processed if isinstance(processed, int) else 0
                )
            elif hasattr(self._feedback_pipeline, "get_processed_count"):
                result.feedback_processed = (
                    self._feedback_pipeline.get_processed_count()
                )
            result.phases_completed.append("feedback")
            self._touch_component("feedback_pipeline")
        except Exception as e:
            result.phases_failed.append("feedback")
            result.errors.append(f"feedback: {e}")
            self._mark_unhealthy("feedback_pipeline", str(e))
            logger.error(f"Phase feedback failed: {e}")

        return result

    def _phase_analytics(self, result: CycleResult) -> CycleResult:
        """Phase 5: Update analytics."""
        if not self._analytics:
            return result

        try:
            if hasattr(self._analytics, "flush"):
                self._analytics.flush()
            result.phases_completed.append("analytics")
            self._touch_component("analytics")
        except Exception as e:
            result.phases_failed.append("analytics")
            result.errors.append(f"analytics: {e}")
            logger.error(f"Phase analytics failed: {e}")

        return result

    def _phase_dashboard(self, result: CycleResult) -> CycleResult:
        """Phase 6: Refresh dashboard data."""
        if not self._dashboard:
            return result

        try:
            if hasattr(self._dashboard, "refresh"):
                self._dashboard.refresh()
            result.phases_completed.append("dashboard")
            self._touch_component("dashboard")
        except Exception as e:
            result.phases_failed.append("dashboard")
            result.errors.append(f"dashboard: {e}")
            logger.error(f"Phase dashboard failed: {e}")

        return result

    def _touch_component(self, name: str) -> None:
        """Update a component's last activity timestamp."""
        if name in self._component_statuses:
            self._component_statuses[name].last_activity = time.time()

    # ─── Health ───────────────────────────────────────────────

    def health(self) -> dict:
        """
        Get comprehensive health status of the entire swarm.
        """
        components = {
            name: status.to_dict() for name, status in self._component_statuses.items()
        }

        healthy_count = sum(1 for s in self._component_statuses.values() if s.healthy)
        total_count = len(self._component_statuses)

        uptime = time.time() - self._start_time if self._start_time else 0

        return {
            "status": "healthy" if healthy_count == total_count else "degraded",
            "mode": self.mode.value,
            "running": self._started,
            "uptime_seconds": round(uptime, 1),
            "components": {
                "healthy": healthy_count,
                "total": total_count,
                "details": components,
            },
            "cycles": {
                "completed": self._cycle_count,
                "consecutive_errors": self._consecutive_errors,
                "last_cycle_ago": (
                    f"{time.time() - self._last_cycle_time:.0f}s"
                    if self._last_cycle_time
                    else None
                ),
            },
            "event_bus": (self._event_bus.get_status() if self._event_bus else None),
        }

    def is_healthy(self) -> bool:
        """Quick boolean health check."""
        return all(s.healthy for s in self._component_statuses.values())

    def is_circuit_broken(self) -> bool:
        """Check if too many consecutive errors have occurred."""
        return self._consecutive_errors >= self.max_cycle_errors

    # ─── Diagnostics ──────────────────────────────────────────

    def get_cycle_history(self, limit: int = 10) -> list[dict]:
        """Get recent cycle results."""
        return [c.to_dict() for c in self._cycle_history[-limit:]]

    def get_component_names(self) -> list[str]:
        """List all registered components."""
        return list(self._component_statuses.keys())

    def get_wiring_diagram(self) -> str:
        """Return a text representation of the current wiring."""
        lines = ["SwarmIntegrator Wiring:"]
        lines.append(f"  Mode: {self.mode.value}")
        lines.append(f"  Components: {len(self._component_statuses)}")

        if self._event_bus:
            lines.append(f"  EventBus: {len(self._event_handlers)} subscriptions")

        lines.append("\n  Component Status:")
        for name, status in self._component_statuses.items():
            icon = "✅" if status.healthy else "❌"
            lines.append(f"    {icon} {name}")
            if status.last_error:
                lines.append(f"       Error: {status.last_error}")

        if self._event_bus:
            lines.append("\n  Event Wiring:")
            if self._xmtp_bridge:
                lines.append("    task.assigned → XMTPBridge.notify_task_assigned")
                lines.append(
                    "    payment.confirmed → XMTPBridge.notify_payment_confirmed"
                )
                lines.append(
                    "    reputation.updated → XMTPBridge.notify_reputation_update"
                )
            if self._feedback_pipeline:
                lines.append("    task.completed → FeedbackPipeline.process_completion")
            if self._analytics:
                lines.append("    * → Analytics.record_event")
            if self._expiry_analyzer:
                lines.append("    task.expired → ExpiryAnalyzer.record_expiry")

        return "\n".join(lines)

    def summary(self) -> dict:
        """Compact summary suitable for MCP tool response."""
        return {
            "mode": self.mode.value,
            "running": self._started,
            "healthy": self.is_healthy(),
            "components": len(self._component_statuses),
            "cycles": self._cycle_count,
            "circuit_broken": self.is_circuit_broken(),
            "last_cycle": (
                self._cycle_history[-1].to_dict() if self._cycle_history else None
            ),
        }

    # ─── Factory ──────────────────────────────────────────────

    @classmethod
    def create_minimal(
        cls,
        mode: SwarmMode = SwarmMode.PASSIVE,
    ) -> "SwarmIntegrator":
        """
        Create a minimal integrator with just EventBus.
        Good for testing or bootstrapping.
        """
        from .event_bus import EventBus

        integrator = cls(mode=mode)
        bus = EventBus()
        integrator.set_event_bus(bus)
        integrator.wire()
        return integrator

    @classmethod
    def create_with_components(
        cls,
        mode: SwarmMode = SwarmMode.PASSIVE,
        components: Optional[dict] = None,
    ) -> "SwarmIntegrator":
        """
        Create an integrator with specific components.

        Args:
            mode: Operational mode
            components: Dict mapping component name to instance.
                        Keys: event_bus, coordinator, scheduler, runner,
                              dashboard, feedback_pipeline, xmtp_bridge,
                              expiry_analyzer, config_manager, analytics
        """
        integrator = cls(mode=mode)
        components = components or {}

        setters = {
            "event_bus": integrator.set_event_bus,
            "coordinator": integrator.set_coordinator,
            "scheduler": integrator.set_scheduler,
            "runner": integrator.set_runner,
            "dashboard": integrator.set_dashboard,
            "feedback_pipeline": integrator.set_feedback_pipeline,
            "xmtp_bridge": integrator.set_xmtp_bridge,
            "expiry_analyzer": integrator.set_expiry_analyzer,
            "config_manager": integrator.set_config_manager,
            "analytics": integrator.set_analytics,
            "decision_synthesizer": integrator.set_decision_synthesizer,
            "verification_adapter": integrator.set_verification_adapter,
        }

        for name, instance in components.items():
            setter = setters.get(name)
            if setter:
                setter(instance)
            else:
                logger.warning(f"Unknown component: {name}")

        integrator.wire()
        return integrator
