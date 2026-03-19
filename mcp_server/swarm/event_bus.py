"""
EventBus — Unified event system for the KK V2 Swarm.

Connects all swarm components through a publish/subscribe event model:

    SwarmCoordinator ──► EventBus ──► XMTPBridge (worker notifications)
                                  ──► FeedbackPipeline (learning)
                                  ──► Analytics (metrics)
                                  ──► EventListener (external hooks)

Design:
    - Synchronous by default (events processed inline)
    - Typed events with dataclass payloads
    - Wildcard subscriptions (listen to all events of a category)
    - Event history for debugging (configurable retention)
    - Thread-safe for future async integration

Usage:
    bus = EventBus()

    # Subscribe to specific events
    bus.on("task.assigned", lambda e: notify_worker(e))
    bus.on("task.completed", lambda e: update_reputation(e))
    bus.on("agent.*", lambda e: log_agent_activity(e))  # Wildcard

    # Emit events from coordinator
    bus.emit("task.assigned", {
        "task_id": "uuid",
        "agent_id": 42,
        "worker_wallet": "0x...",
    })

    # Wire up components
    bus.wire_xmtp_bridge(bridge)
    bus.wire_feedback_pipeline(pipeline)
"""

import fnmatch
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional, Any

logger = logging.getLogger("em.swarm.event_bus")


# ─── Event Types ──────────────────────────────────────────────────────────────


# Task lifecycle events
TASK_DISCOVERED = "task.discovered"
TASK_ENRICHED = "task.enriched"
TASK_ASSIGNED = "task.assigned"
TASK_STARTED = "task.started"
TASK_SUBMITTED = "task.submitted"
TASK_COMPLETED = "task.completed"
TASK_FAILED = "task.failed"
TASK_EXPIRED = "task.expired"
TASK_CANCELLED = "task.cancelled"

# Agent lifecycle events
AGENT_REGISTERED = "agent.registered"
AGENT_ACTIVATED = "agent.activated"
AGENT_DEACTIVATED = "agent.deactivated"
AGENT_DEGRADED = "agent.degraded"
AGENT_SUSPENDED = "agent.suspended"
AGENT_COOLDOWN = "agent.cooldown"
AGENT_ERROR = "agent.error"

# Worker events (from XMTP bot)
WORKER_REGISTERED = "worker.registered"
WORKER_APPLIED = "worker.applied"
WORKER_EVIDENCE = "worker.evidence"
WORKER_RATED = "worker.rated"
WORKER_MESSAGE = "worker.message"

# Swarm operational events
SWARM_CYCLE_START = "swarm.cycle.start"
SWARM_CYCLE_END = "swarm.cycle.end"
SWARM_HEALTH_CHECK = "swarm.health_check"
SWARM_STATE_SAVED = "swarm.state_saved"

# Notification events
NOTIFICATION_SENT = "notification.sent"
NOTIFICATION_FAILED = "notification.failed"
NOTIFICATION_RATE_LIMITED = "notification.rate_limited"

# Reputation events
REPUTATION_UPDATED = "reputation.updated"
SKILL_DNA_UPDATED = "skill_dna.updated"

# Payment events
PAYMENT_ESCROWED = "payment.escrowed"
PAYMENT_RELEASED = "payment.released"
PAYMENT_CONFIRMED = "payment.confirmed"


# ─── Event Data ───────────────────────────────────────────────────────────────


@dataclass
class Event:
    """An event flowing through the swarm event bus."""

    type: str
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = ""  # Component that emitted the event
    correlation_id: Optional[str] = None  # For tracing related events

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "correlation_id": self.correlation_id,
        }


@dataclass
class Subscription:
    """A registered event handler."""

    pattern: str  # Event type pattern (supports * wildcard)
    handler: Callable[[Event], None]
    source: str = ""  # Who registered this handler
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    call_count: int = 0
    last_called: Optional[datetime] = None
    errors: int = 0


# ─── Event Bus ────────────────────────────────────────────────────────────────


class EventBus:
    """
    Central event bus for the KK V2 Swarm.

    Manages pub/sub event flow between all swarm components with:
    - Pattern matching (exact + wildcard)
    - Event history for debugging
    - Handler error isolation
    - Metrics tracking
    """

    def __init__(
        self,
        history_size: int = 500,
        error_threshold: int = 10,
    ):
        self._subscriptions: list[Subscription] = []
        self._history: deque[Event] = deque(maxlen=history_size)
        self._error_threshold = error_threshold

        # Metrics
        self._total_events = 0
        self._total_deliveries = 0
        self._total_errors = 0
        self._events_by_type: dict[str, int] = {}

    # ─── Subscribe ────────────────────────────────────────────────

    def on(
        self,
        pattern: str,
        handler: Callable[[Event], None],
        source: str = "",
    ) -> Subscription:
        """
        Subscribe to events matching a pattern.

        Patterns:
            "task.assigned"     → exact match
            "task.*"            → all task events
            "*.completed"       → all completion events
            "*"                 → all events
        """
        sub = Subscription(
            pattern=pattern,
            handler=handler,
            source=source,
        )
        self._subscriptions.append(sub)
        logger.debug(f"Subscription added: {pattern} from {source or 'anonymous'}")
        return sub

    def off(self, subscription: Subscription) -> bool:
        """Remove a subscription. Returns True if found and removed."""
        try:
            self._subscriptions.remove(subscription)
            return True
        except ValueError:
            return False

    def once(
        self,
        pattern: str,
        handler: Callable[[Event], None],
        source: str = "",
    ) -> Subscription:
        """Subscribe to an event pattern for a single invocation."""
        sub = None

        def wrapper(event: Event):
            handler(event)
            if sub is not None:
                self.off(sub)

        sub = self.on(pattern, wrapper, source=source)
        return sub

    # ─── Emit ─────────────────────────────────────────────────────

    def emit(
        self,
        event_type: str,
        data: Optional[dict] = None,
        source: str = "",
        correlation_id: Optional[str] = None,
    ) -> Event:
        """
        Emit an event to all matching subscribers.

        Returns the Event object for chaining/tracking.
        """
        event = Event(
            type=event_type,
            data=data or {},
            source=source,
            correlation_id=correlation_id,
        )

        self._total_events += 1
        self._events_by_type[event_type] = (
            self._events_by_type.get(event_type, 0) + 1
        )
        self._history.append(event)

        # Find matching subscriptions
        matching = [
            sub
            for sub in self._subscriptions
            if self._matches(sub.pattern, event_type)
        ]

        for sub in matching:
            try:
                sub.handler(event)
                sub.call_count += 1
                sub.last_called = datetime.now(timezone.utc)
                self._total_deliveries += 1
            except Exception as e:
                sub.errors += 1
                self._total_errors += 1
                logger.error(
                    f"Event handler error: {event_type} → "
                    f"{sub.source or 'anonymous'}: {e}"
                )

                # Disable handler if error threshold exceeded
                if sub.errors >= self._error_threshold:
                    logger.warning(
                        f"Disabling handler {sub.source} for {sub.pattern}: "
                        f"{sub.errors} errors exceeded threshold"
                    )
                    self.off(sub)

        return event

    # ─── Pattern Matching ─────────────────────────────────────────

    @staticmethod
    def _matches(pattern: str, event_type: str) -> bool:
        """Check if an event type matches a subscription pattern."""
        if pattern == "*":
            return True
        if "*" in pattern:
            return fnmatch.fnmatch(event_type, pattern)
        return pattern == event_type

    # ─── Component Wiring ─────────────────────────────────────────

    def wire_xmtp_bridge(self, bridge: Any) -> list[Subscription]:
        """
        Wire XMTP bridge to receive task lifecycle events.

        Maps swarm events → XMTP notifications:
            task.assigned → notify_task_assigned()
            task.completed → notify_payment_confirmed()
            reputation.updated → notify_reputation_update()
        """
        subs = []

        def on_task_assigned(event: Event):
            try:
                bridge.notify_task_assigned(
                    task_id=event.data.get("task_id", ""),
                    worker_wallet=event.data.get("worker_wallet", ""),
                    task_data=event.data.get("task_data", {}),
                )
            except Exception as e:
                logger.error(f"XMTP bridge task_assigned failed: {e}")

        def on_payment_confirmed(event: Event):
            try:
                bridge.notify_payment_confirmed(
                    worker_wallet=event.data.get("worker_wallet", ""),
                    task_id=event.data.get("task_id", ""),
                    amount=event.data.get("amount", 0),
                    chain=event.data.get("chain", "base"),
                    tx_hash=event.data.get("tx_hash", ""),
                )
            except Exception as e:
                logger.error(f"XMTP bridge payment_confirmed failed: {e}")

        def on_reputation_updated(event: Event):
            try:
                bridge.notify_reputation_update(
                    worker_wallet=event.data.get("worker_wallet", ""),
                    task_id=event.data.get("task_id", ""),
                    score=event.data.get("score", 0),
                    new_average=event.data.get("new_average", 0),
                    total_ratings=event.data.get("total_ratings", 0),
                )
            except Exception as e:
                logger.error(f"XMTP bridge reputation_updated failed: {e}")

        subs.append(self.on(TASK_ASSIGNED, on_task_assigned, source="xmtp_bridge"))
        subs.append(self.on(PAYMENT_CONFIRMED, on_payment_confirmed, source="xmtp_bridge"))
        subs.append(self.on(REPUTATION_UPDATED, on_reputation_updated, source="xmtp_bridge"))

        logger.info("XMTP bridge wired to event bus (3 subscriptions)")
        return subs

    def wire_analytics(self, recorder: Callable[[Event], None]) -> Subscription:
        """Wire a catch-all analytics recorder."""
        return self.on("*", recorder, source="analytics")

    # ─── Status & Debugging ───────────────────────────────────────

    def get_status(self) -> dict:
        """Get event bus status."""
        return {
            "total_events": self._total_events,
            "total_deliveries": self._total_deliveries,
            "total_errors": self._total_errors,
            "subscriptions": len(self._subscriptions),
            "history_size": len(self._history),
            "top_events": dict(
                sorted(
                    self._events_by_type.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:10]
            ),
            "subscription_details": [
                {
                    "pattern": sub.pattern,
                    "source": sub.source,
                    "calls": sub.call_count,
                    "errors": sub.errors,
                }
                for sub in self._subscriptions
            ],
        }

    def get_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 50,
        correlation_id: Optional[str] = None,
    ) -> list[dict]:
        """
        Get event history, optionally filtered.

        Args:
            event_type: Filter by exact type or pattern (supports *)
            limit: Max events to return
            correlation_id: Filter by correlation ID
        """
        events = list(self._history)

        if event_type:
            events = [
                e
                for e in events
                if self._matches(event_type, e.type)
            ]

        if correlation_id:
            events = [
                e for e in events if e.correlation_id == correlation_id
            ]

        return [e.to_dict() for e in events[-limit:]]

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()

    def reset_metrics(self) -> None:
        """Reset all metrics counters."""
        self._total_events = 0
        self._total_deliveries = 0
        self._total_errors = 0
        self._events_by_type.clear()
        for sub in self._subscriptions:
            sub.call_count = 0
            sub.errors = 0
