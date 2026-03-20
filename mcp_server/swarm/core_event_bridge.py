"""
Core → Swarm Event Bridge
===========================

Bridges the EM Core EventBus (async, Pydantic EMEvent) with the Swarm
EventBus (sync, dataclass Event). This lets the swarm coordinator
receive real-time task lifecycle events from the EM platform without polling.

Architecture:
    ┌──────────────────────────────────────────────────────────┐
    │                    EM Core                                │
    │                                                          │
    │   REST API ──► EventBus ──► MeshRelay Adapter            │
    │                    │    ──► XMTP Adapter                 │
    │                    │    ──► Webhook Dispatcher            │
    │                    │                                     │
    │                    └──► CoreEventBridge ──────────────┐   │
    └────────────────────────────────────────────────────────│──┘
                                                            │
    ┌──────────────────────────────────────────────────────│──┐
    │                  KK V2 Swarm                          │  │
    │                                                      ▼  │
    │   SwarmEventBus ◄──────────────────── bridge events      │
    │       │                                                  │
    │       ├──► Coordinator (task routing)                     │
    │       ├──► FeedbackPipeline (learning)                    │
    │       ├──► TaskMonitor (intervention)                     │
    │       └──► Analytics (metrics)                            │
    └──────────────────────────────────────────────────────────┘

Event Mapping:
    Core EMEvent(event_type="task.created")  → Swarm Event(type="task.discovered")
    Core EMEvent(event_type="task.assigned") → Swarm Event(type="task.assigned")
    Core EMEvent(event_type="task.completed") → Swarm Event(type="task.completed")
    ...etc

Usage:
    from mcp_server.events.bus import EventBus as CoreEventBus
    from mcp_server.swarm.event_bus import EventBus as SwarmEventBus
    from mcp_server.swarm.core_event_bridge import CoreEventBridge

    core_bus = CoreEventBus()
    swarm_bus = SwarmEventBus()
    bridge = CoreEventBridge(core_bus, swarm_bus)
    bridge.start()

    # Now core events flow into the swarm automatically
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from ..events.bus import EventBus as CoreEventBus
from ..events.models import EMEvent, EventSource
from .event_bus import EventBus as SwarmEventBus

logger = logging.getLogger("em.swarm.core_event_bridge")


# ---------------------------------------------------------------------------
# Event Type Mapping: Core → Swarm
# ---------------------------------------------------------------------------

# Core event_type → Swarm event type
# Some map directly, some rename for swarm context
EVENT_TYPE_MAP: Dict[str, str] = {
    # Task lifecycle
    "task.created": "task.discovered",  # In swarm context, created = discovered
    "task.updated": "task.enriched",  # Updates add context
    "task.assigned": "task.assigned",
    "task.started": "task.started",
    "task.submitted": "task.submitted",
    "task.completed": "task.completed",
    "task.expired": "task.expired",
    "task.cancelled": "task.cancelled",
    # Submission events
    "submission.received": "task.submitted",
    "submission.approved": "task.completed",
    "submission.rejected": "task.failed",
    "submission.revision_requested": "worker.message",
    # Payment events
    "payment.escrowed": "payment.escrowed",
    "payment.released": "payment.released",
    "payment.refunded": "payment.confirmed",
    # Worker events
    "worker.registered": "worker.registered",
    "worker.application": "worker.applied",
}

# Core event sources that the bridge should SKIP to avoid echo loops
SKIP_SOURCES: Set[EventSource] = {
    # Don't bridge events that originated FROM the swarm
    # (prevents: swarm → core → bridge → swarm infinite loop)
}


# ---------------------------------------------------------------------------
# Bridge Statistics
# ---------------------------------------------------------------------------


@dataclass
class BridgeStats:
    """Metrics for the core→swarm event bridge."""

    events_received: int = 0
    events_bridged: int = 0
    events_skipped: int = 0
    events_filtered: int = 0
    errors: int = 0
    events_by_type: Dict[str, int] = field(default_factory=dict)
    last_bridged_at: Optional[datetime] = None
    started_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Event Filters
# ---------------------------------------------------------------------------


@dataclass
class BridgeFilter:
    """
    Configurable filter for which core events to bridge.

    Allows fine-grained control:
    - event_types: only bridge these types (None = all mapped types)
    - min_bounty_usd: only bridge tasks above this bounty
    - categories: only bridge these task categories
    - exclude_sources: skip events from these sources
    """

    event_types: Optional[Set[str]] = None
    min_bounty_usd: float = 0.0
    categories: Optional[Set[str]] = None
    exclude_sources: Set[EventSource] = field(default_factory=lambda: set(SKIP_SOURCES))

    def should_bridge(self, event: EMEvent) -> bool:
        """Check if an event passes all filters."""
        # Source filter (anti-echo)
        if event.source in self.exclude_sources:
            return False

        # Event type filter
        if self.event_types and event.event_type not in self.event_types:
            return False

        # Bounty filter
        if self.min_bounty_usd > 0:
            bounty = event.payload.get("bounty_usd", 0)
            if bounty < self.min_bounty_usd:
                return False

        # Category filter
        if self.categories:
            category = event.payload.get("category", "")
            if category and category not in self.categories:
                return False

        return True


# ---------------------------------------------------------------------------
# Core Event Bridge
# ---------------------------------------------------------------------------


class CoreEventBridge:
    """
    Bridges EM Core EventBus → Swarm EventBus.

    Subscribes to all mapped core event types and re-emits them as
    swarm events. Handles async→sync transition, anti-echo filtering,
    and payload transformation.
    """

    def __init__(
        self,
        core_bus: CoreEventBus,
        swarm_bus: SwarmEventBus,
        bridge_filter: Optional[BridgeFilter] = None,
        transform_payload: Optional[Callable[[EMEvent], Dict[str, Any]]] = None,
    ):
        self._core_bus = core_bus
        self._swarm_bus = swarm_bus
        self._filter = bridge_filter or BridgeFilter()
        self._transform = transform_payload or self._default_transform
        self._subscription_ids: List[str] = []
        self._stats = BridgeStats()
        self._started = False

    def start(self) -> None:
        """Start bridging core events to swarm."""
        if self._started:
            logger.warning("CoreEventBridge already started")
            return

        # Subscribe to all mapped event types on the core bus
        for core_type in EVENT_TYPE_MAP:
            sub_id = self._core_bus.subscribe(
                pattern=core_type,
                handler=self._handle_core_event,
            )
            self._subscription_ids.append(sub_id)

        self._started = True
        self._stats.started_at = datetime.now(timezone.utc)
        logger.info(
            "CoreEventBridge started: %d event type mappings active",
            len(EVENT_TYPE_MAP),
        )

    def stop(self) -> None:
        """Stop bridging and unsubscribe from core bus."""
        for sub_id in self._subscription_ids:
            self._core_bus.unsubscribe(sub_id)
        self._subscription_ids.clear()
        self._started = False
        logger.info("CoreEventBridge stopped")

    async def _handle_core_event(self, event: EMEvent) -> None:
        """
        Async handler for core events. Transforms and re-emits as swarm events.
        """
        self._stats.events_received += 1

        # Apply filter
        if not self._filter.should_bridge(event):
            self._stats.events_filtered += 1
            return

        # Map event type
        swarm_type = EVENT_TYPE_MAP.get(event.event_type)
        if not swarm_type:
            self._stats.events_skipped += 1
            return

        try:
            # Transform payload
            swarm_data = self._transform(event)

            # Emit on swarm bus (sync)
            self._swarm_bus.emit(
                event_type=swarm_type,
                data=swarm_data,
                source="core_event_bridge",
                correlation_id=event.correlation_id or event.id,
            )

            self._stats.events_bridged += 1
            self._stats.events_by_type[swarm_type] = (
                self._stats.events_by_type.get(swarm_type, 0) + 1
            )
            self._stats.last_bridged_at = datetime.now(timezone.utc)

            logger.debug(
                "Bridged: %s → %s (task=%s)",
                event.event_type,
                swarm_type,
                event.task_id or "N/A",
            )

        except Exception as e:
            self._stats.errors += 1
            logger.error("Bridge error for %s: %s", event.event_type, e, exc_info=True)

    @staticmethod
    def _default_transform(event: EMEvent) -> Dict[str, Any]:
        """
        Default payload transformation: Core EMEvent → Swarm Event data.

        Preserves all payload fields and adds bridge metadata.
        """
        data = dict(event.payload)
        data["_bridge"] = {
            "core_event_id": event.id,
            "core_event_type": event.event_type,
            "core_source": event.source.value
            if isinstance(event.source, EventSource)
            else str(event.source),
            "core_timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }
        if event.task_id:
            data["task_id"] = event.task_id
        return data

    @property
    def stats(self) -> Dict[str, Any]:
        """Return bridge statistics as a dict."""
        return {
            "events_received": self._stats.events_received,
            "events_bridged": self._stats.events_bridged,
            "events_skipped": self._stats.events_skipped,
            "events_filtered": self._stats.events_filtered,
            "errors": self._stats.errors,
            "events_by_type": dict(self._stats.events_by_type),
            "last_bridged_at": (
                self._stats.last_bridged_at.isoformat()
                if self._stats.last_bridged_at
                else None
            ),
            "started": self._started,
            "subscription_count": len(self._subscription_ids),
        }

    @property
    def is_running(self) -> bool:
        return self._started
