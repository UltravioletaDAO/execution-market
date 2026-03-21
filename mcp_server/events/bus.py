"""
EventBus — asyncio-based in-process pub/sub.

MVP implementation using asyncio. At scale, swap internals for Redis Streams
without changing the publish/subscribe API.
"""

import logging
from typing import Any, Callable, Coroutine, Dict, Optional
from uuid import uuid4

from .models import EMEvent, EventSource

logger = logging.getLogger(__name__)

# Type alias for async event handlers
EventHandler = Callable[[EMEvent], Coroutine[Any, Any, None]]


class _Subscription:
    __slots__ = ("id", "pattern", "handler", "source_filter")

    def __init__(
        self,
        sub_id: str,
        pattern: str,
        handler: EventHandler,
        source_filter: Optional[EventSource] = None,
    ):
        self.id = sub_id
        self.pattern = pattern
        self.handler = handler
        self.source_filter = source_filter


class EventBus:
    """
    Async in-process event bus with pattern matching and anti-echo.

    Usage::

        bus = EventBus()
        bus.subscribe("task.*", my_handler, source_filter=EventSource.MESHRELAY)
        await bus.publish(EMEvent(event_type="task.created", ...))
    """

    def __init__(self) -> None:
        self._subscriptions: Dict[str, _Subscription] = {}
        self._stats = {
            "events_published": 0,
            "events_delivered": 0,
            "delivery_errors": 0,
        }

    def subscribe(
        self,
        pattern: str,
        handler: EventHandler,
        source_filter: Optional[EventSource] = None,
    ) -> str:
        """Subscribe to events matching a pattern.

        Args:
            pattern: Event type pattern ("task.created", "task.*", "*")
            handler: Async callable receiving EMEvent
            source_filter: If set, skip events FROM this source (anti-echo)

        Returns:
            Subscription ID (for unsubscribe)
        """
        sub_id = str(uuid4())
        self._subscriptions[sub_id] = _Subscription(
            sub_id=sub_id,
            pattern=pattern,
            handler=handler,
            source_filter=source_filter,
        )
        logger.debug("Subscribed %s to pattern '%s'", sub_id[:8], pattern)
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription. Returns True if found."""
        removed = self._subscriptions.pop(subscription_id, None)
        return removed is not None

    async def publish(self, event: EMEvent) -> int:
        """Publish an event to all matching subscribers.

        Args:
            event: The event to publish

        Returns:
            Number of handlers that received the event
        """
        self._stats["events_published"] += 1
        delivered = 0

        for sub in list(self._subscriptions.values()):
            # Pattern matching
            if not event.matches(sub.pattern):
                continue

            # Anti-echo: skip if event source matches the subscriber's filter
            if sub.source_filter and event.source == sub.source_filter:
                continue

            try:
                await sub.handler(event)
                delivered += 1
            except Exception:
                self._stats["delivery_errors"] += 1
                logger.exception(
                    "Error delivering %s to subscriber %s",
                    event.event_type,
                    sub.id[:8],
                )

        self._stats["events_delivered"] += delivered
        logger.debug("Published %s → %d handlers", event.event_type, delivered)
        return delivered

    @property
    def stats(self) -> Dict[str, int]:
        """Return delivery statistics."""
        return dict(self._stats)

    @property
    def subscription_count(self) -> int:
        return len(self._subscriptions)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get or create the global EventBus instance."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
