"""
EventInjector — Injects task lifecycle events into chat channels as system messages.

Subscribes to the Event Bus and forwards relevant events to the IRC task channel
AND to any connected WebSocket clients via the IRCPool.

Anti-echo: events originating from the chat relay itself are skipped.
"""

import asyncio
import logging
from typing import Optional

from events import EventBus, EMEvent, EventSource

logger = logging.getLogger(__name__)

# Map event types to human-readable system messages
_EVENT_TEMPLATES: dict[str, str] = {
    "submission.received": "[System] Evidence submitted for review",
    "submission.approved": "[System] Evidence approved! Payment processing...",
    "submission.rejected": "[System] Evidence rejected: {reason}",
    "payment.released": "[System] Payment of ${amount_usd} USDC released",
    "task.cancelled": "[System] Task cancelled{reason_suffix}",
    "task.assigned": "[System] Worker assigned to this task",
}


def _format_system_message(event: EMEvent) -> Optional[str]:
    """Format an EMEvent into a chat system message, or None to skip."""
    template = _EVENT_TEMPLATES.get(event.event_type)
    if not template:
        return None

    p = event.payload
    try:
        if event.event_type == "submission.rejected":
            reason = p.get("reason", "No reason given")
            return template.format(reason=reason)
        if event.event_type == "payment.released":
            amount = p.get("amount_usd", p.get("bounty_usd", "?"))
            return template.format(amount_usd=amount)
        if event.event_type == "task.cancelled":
            reason = p.get("reason", "")
            suffix = f": {reason}" if reason else ""
            return template.format(reason_suffix=suffix)
        return template
    except Exception:
        return template  # Return un-formatted on error


class EventInjector:
    """
    Bridges Event Bus -> IRC chat channels.

    On relevant task events, posts a system message to ``#task-{id}``
    via the IRCPool. Also persists to task_chat_log.
    """

    def __init__(self, bus: EventBus):
        self._bus = bus
        self._subscription_ids: list[str] = []
        self._stats = {"injected": 0, "skipped": 0, "errors": 0}

    def start(self) -> None:
        """Subscribe to task lifecycle events."""
        patterns = ["submission.*", "payment.*", "task.cancelled", "task.assigned"]
        for pattern in patterns:
            sub_id = self._bus.subscribe(
                pattern=pattern,
                handler=self._handle_event,
                source_filter=EventSource.DASHBOARD,  # anti-echo from chat
            )
            self._subscription_ids.append(sub_id)
        logger.info("EventInjector started: %d patterns", len(patterns))

    def stop(self) -> None:
        """Unsubscribe from all patterns."""
        for sub_id in self._subscription_ids:
            self._bus.unsubscribe(sub_id)
        self._subscription_ids.clear()
        logger.info("EventInjector stopped")

    async def _handle_event(self, event: EMEvent) -> None:
        """Format event and inject into the task's chat channel."""
        task_id = event.task_id
        if not task_id:
            self._stats["skipped"] += 1
            return

        text = _format_system_message(event)
        if not text:
            self._stats["skipped"] += 1
            return

        channel = f"#task-{task_id[:8].lower()}"

        try:
            from .irc_pool import IRCPool

            pool = IRCPool.get_instance()
            if pool.is_connected:
                await pool.send_message(channel, text)

            # Persist as system message via ChatLogService
            from .log_service import get_log_service

            log_svc = get_log_service()
            asyncio.create_task(
                log_svc.log_message(
                    task_id, "system", text, source="system", msg_type="system"
                )
            )

            self._stats["injected"] += 1
            logger.debug("EventInjector: %s -> %s", event.event_type, channel)
        except Exception:
            self._stats["errors"] += 1
            logger.exception("EventInjector: failed to inject %s", event.event_type)

    @property
    def stats(self) -> dict:
        return dict(self._stats)
