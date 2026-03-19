"""
MeshRelay Adapter — forwards Event Bus events to MeshRelay's webhook endpoint.

Subscribes to all task/submission/payment events and delivers them as
IRC-friendly formatted payloads. Anti-echo: skips events originating
from MeshRelay itself.
"""

import logging
from typing import Optional

from ..models import EMEvent, EventSource
from ..bus import EventBus

logger = logging.getLogger(__name__)


def _format_irc_line(event: EMEvent) -> str:
    """Format an EMEvent as a single IRC-friendly line."""
    p = event.payload
    event_type = event.event_type

    if event_type == "task.created":
        title = p.get("title", "Untitled")
        bounty = p.get("bounty_usd", 0)
        category = p.get("category", "unknown")
        task_id = (p.get("task_id") or event.task_id or "?")[:8]
        chain = p.get("payment_network", "base")
        return (
            f"[NEW TASK] {title} | ${bounty:.2f} USDC ({chain}) "
            f"| {category} | /claim {task_id}"
        )

    if event_type == "task.assigned":
        task_id = (event.task_id or "?")[:8]
        worker = p.get("worker_wallet", p.get("executor_id", "?"))
        if isinstance(worker, str) and len(worker) > 10:
            worker = f"{worker[:6]}...{worker[-4:]}"
        return f"[ASSIGNED] Task {task_id} | Worker: {worker}"

    if event_type == "task.cancelled":
        task_id = (event.task_id or "?")[:8]
        reason = p.get("reason", "")
        return f"[CANCELLED] Task {task_id}" + (f" | Reason: {reason}" if reason else "")

    if event_type == "submission.received":
        task_id = (event.task_id or "?")[:8]
        return f"[SUBMITTED] Task {task_id} | Evidence submitted for review"

    if event_type == "submission.approved":
        task_id = (event.task_id or "?")[:8]
        bounty = p.get("bounty_usd", p.get("amount_usd", 0))
        return f"[APPROVED] Task {task_id} | Payment: ${bounty:.2f} USDC"

    if event_type == "submission.rejected":
        task_id = (event.task_id or "?")[:8]
        reason = p.get("reason", "No reason given")
        return f"[REJECTED] Task {task_id} | {reason}"

    if event_type == "payment.released":
        task_id = (event.task_id or "?")[:8]
        amount = p.get("amount_usd", 0)
        tx_hash = p.get("tx_hash", "")
        tx_short = f" | TX: {tx_hash[:14]}..." if tx_hash else ""
        chain = p.get("chain", "base")
        return f"[PAID] Task {task_id} | ${amount:.2f} USDC ({chain}){tx_short}"

    # Generic fallback
    task_id = (event.task_id or "")[:8]
    return f"[{event_type.upper()}] Task {task_id}"


class MeshRelayAdapter:
    """
    Bridges Event Bus → MeshRelay webhook endpoint.

    Formats events as IRC-friendly text and delivers via WebhookSender.
    Anti-echo: skips events from EventSource.MESHRELAY.
    """

    def __init__(
        self,
        bus: EventBus,
        webhook_url: Optional[str] = None,
        webhook_secret: str = "",
    ):
        self._bus = bus
        self._webhook_url = webhook_url
        self._webhook_secret = webhook_secret
        self._subscription_ids: list[str] = []
        self._stats = {"forwarded": 0, "errors": 0, "skipped_echo": 0}

    def start(self) -> None:
        """Subscribe to relevant event patterns."""
        patterns = ["task.*", "submission.*", "payment.*"]
        for pattern in patterns:
            sub_id = self._bus.subscribe(
                pattern=pattern,
                handler=self._handle_event,
                source_filter=EventSource.MESHRELAY,  # anti-echo
            )
            self._subscription_ids.append(sub_id)
        logger.info(
            "MeshRelayAdapter started, subscribed to %d patterns",
            len(patterns),
        )

    def stop(self) -> None:
        """Unsubscribe from all patterns."""
        for sub_id in self._subscription_ids:
            self._bus.unsubscribe(sub_id)
        self._subscription_ids.clear()
        logger.info("MeshRelayAdapter stopped")

    async def _handle_event(self, event: EMEvent) -> None:
        """Format and forward event to MeshRelay."""
        irc_line = _format_irc_line(event)

        if self._webhook_url:
            try:
                from webhooks.sender import send_webhook
                from webhooks.events import WebhookEvent, WebhookEventType

                # Build webhook event with IRC text + raw payload
                wh_event = WebhookEvent(
                    event_type=WebhookEventType(event.event_type),
                    payload={"text": irc_line, "raw": event.payload},
                )
                await send_webhook(
                    url=self._webhook_url,
                    event=wh_event,
                    secret=self._webhook_secret,
                    webhook_id=f"meshrelay-adapter-{event.id[:8]}",
                )
                self._stats["forwarded"] += 1
            except Exception:
                self._stats["errors"] += 1
                logger.exception("MeshRelayAdapter: failed to forward %s", event.event_type)
        else:
            # No webhook URL configured — log for debugging
            logger.debug("MeshRelayAdapter (no URL): %s", irc_line)
            self._stats["forwarded"] += 1

    @property
    def stats(self) -> dict:
        return dict(self._stats)
