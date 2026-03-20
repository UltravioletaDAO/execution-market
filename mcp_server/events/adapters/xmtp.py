"""
XMTP Event Bus Adapter — sends Event Bus events to XMTP users.

Subscribes to task lifecycle events and delivers notifications
to relevant XMTP addresses. Anti-echo: skips events originating
from XMTP to prevent notification loops.

Target resolution: looks up XMTP-reachable wallets from
irc_identities or executor profiles.
"""

import logging
from typing import List

import httpx

from ..models import EMEvent, EventSource
from ..bus import EventBus

logger = logging.getLogger(__name__)


class XMTPAdapter:
    """Bridge Event Bus events to XMTP mobile users."""

    def __init__(
        self,
        bus: EventBus,
        xmtp_bot_url: str = "http://localhost:3000",
    ):
        self._bus = bus
        self._bot_url = xmtp_bot_url.rstrip("/")
        self._subscription_ids: list[str] = []
        self._stats = {
            "notifications_sent": 0,
            "skipped_no_target": 0,
            "errors": 0,
        }

    def start(self) -> None:
        """Subscribe to events that should reach XMTP users."""
        patterns = [
            "task.created",
            "task.assigned",
            "task.completed",
            "task.cancelled",
            "submission.approved",
            "submission.rejected",
            "payment.released",
        ]
        for pattern in patterns:
            sub_id = self._bus.subscribe(
                pattern=pattern,
                handler=self._on_event,
                source_filter=EventSource.XMTP,  # anti-echo
            )
            self._subscription_ids.append(sub_id)

        logger.info("XMTPAdapter started with %d subscriptions", len(patterns))

    def stop(self) -> None:
        for sub_id in self._subscription_ids:
            self._bus.unsubscribe(sub_id)
        self._subscription_ids.clear()
        logger.info("XMTPAdapter stopped")

    async def _on_event(self, event: EMEvent) -> None:
        """Route event to target XMTP users."""
        targets = self._resolve_targets(event)
        if not targets:
            self._stats["skipped_no_target"] += 1
            return

        message = self._format_message(event)
        for address in targets:
            await self._send_to_xmtp(address, message)

    def _resolve_targets(self, event: EMEvent) -> List[str]:
        """Determine which XMTP addresses should receive this event."""
        targets = []

        # Explicit target_users from event
        targets.extend(event.target_users)

        # Extract wallets from payload
        p = event.payload
        if p.get("worker_wallet"):
            targets.append(p["worker_wallet"])
        if p.get("publisher_wallet"):
            targets.append(p["publisher_wallet"])

        # Deduplicate
        return list(set(t for t in targets if t))

    def _format_message(self, event: EMEvent) -> str:
        """Format event as XMTP notification text."""
        p = event.payload
        task_id = (p.get("task_id") or event.task_id or "?")[:8]
        title = p.get("title", "")

        formatters = {
            "task.created": lambda: (
                f"[New Task] {title} | ${p.get('bounty_usdc', 0)} USDC"
            ),
            "task.assigned": lambda: f"[Assigned] Task {task_id} assigned to you",
            "task.completed": lambda: f"[Completed] Task {task_id} finished",
            "task.cancelled": lambda: f"[Cancelled] Task {task_id}",
            "submission.approved": lambda: (
                f"[Approved] Task {task_id} — payment releasing"
            ),
            "submission.rejected": lambda: (
                f"[Rejected] Task {task_id}: {p.get('reason', '')}"
            ),
            "payment.released": lambda: (
                f"[Paid] ${p.get('amount_usd', 0)} USDC for task {task_id}"
            ),
        }

        formatter = formatters.get(event.event_type)
        if formatter:
            return formatter()
        return f"[{event.event_type}] Task {task_id}"

    async def _send_to_xmtp(self, address: str, message: str) -> None:
        """Send notification via XMTP bot HTTP API."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self._bot_url}/api/notify",
                    json={"address": address, "message": message},
                )
                if resp.status_code in (200, 204):
                    self._stats["notifications_sent"] += 1
                    logger.debug("XMTP notification sent to %s", address[:10])
                else:
                    self._stats["errors"] += 1
                    logger.debug(
                        "XMTP notify failed (%d): %s", resp.status_code, address[:10]
                    )
        except Exception as e:
            self._stats["errors"] += 1
            logger.debug("XMTP send failed for %s: %s", address[:10], e)

    @property
    def stats(self) -> dict:
        return dict(self._stats)
