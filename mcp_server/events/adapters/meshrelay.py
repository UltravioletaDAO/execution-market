"""
MeshRelay Adapter — forwards Event Bus events to MeshRelay's webhook endpoint.

Subscribes to all task/submission/payment events and delivers them as
structured JSON payloads with HMAC-SHA256 signatures.

Anti-echo: skips events originating from MeshRelay itself.

Webhook schema (agreed 2026-03-20):
  Body: {event_id, event_type, source, timestamp, payload}
  Headers: X-EM-Signature (HMAC-SHA256), X-EM-Timestamp (Unix seconds)
  HMAC: HMAC(secret, timestamp + '.' + body)
"""

import hashlib
import hmac
import json
import logging
import os
import time
import uuid

import httpx

from ..bus import EventBus
from ..models import EMEvent, EventSource

logger = logging.getLogger(__name__)

# Default webhook URL (overridden by env var or constructor arg)
DEFAULT_WEBHOOK_URL = "https://api.meshrelay.xyz/hooks/em/events"


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
        return f"[CANCELLED] Task {task_id}" + (
            f" | Reason: {reason}" if reason else ""
        )

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

    if event_type == "reputation.updated":
        task_id = (event.task_id or "?")[:8]
        score = p.get("score", "?")
        return f"[REP] Task {task_id} | Score: {score}"

    # Generic fallback
    task_id = (event.task_id or "")[:8]
    return f"[{event_type.upper()}] Task {task_id}"


def _sign_payload(body: str, secret: str, timestamp: int) -> str:
    """Generate HMAC-SHA256 signature: HMAC(secret, timestamp.body)."""
    signed_payload = f"{timestamp}.{body}"
    return hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class MeshRelayAdapter:
    """
    Bridges Event Bus -> MeshRelay webhook endpoint.

    Sends structured JSON payloads with HMAC-SHA256 signatures.
    Anti-echo: skips events from EventSource.MESHRELAY.

    Config (env vars):
        MESHRELAY_WEBHOOK_URL: Webhook endpoint (default: api.meshrelay.xyz)
        MESHRELAY_WEBHOOK_SECRET: HMAC signing secret (from AWS SM em/meshrelay)
    """

    def __init__(
        self,
        bus: EventBus,
        webhook_url: str | None = None,
        webhook_secret: str = "",
    ):
        self._bus = bus
        self._webhook_url = webhook_url or os.environ.get(
            "MESHRELAY_WEBHOOK_URL", DEFAULT_WEBHOOK_URL
        )
        self._webhook_secret = webhook_secret or os.environ.get(
            "MESHRELAY_WEBHOOK_SECRET", ""
        )
        self._subscription_ids: list[str] = []
        self._stats = {"forwarded": 0, "errors": 0, "skipped_echo": 0}
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def start(self) -> None:
        """Subscribe to relevant event patterns."""
        patterns = ["task.*", "submission.*", "payment.*", "reputation.*"]
        for pattern in patterns:
            sub_id = self._bus.subscribe(
                pattern=pattern,
                handler=self._handle_event,
                source_filter=EventSource.MESHRELAY,  # anti-echo
            )
            self._subscription_ids.append(sub_id)

        has_secret = bool(self._webhook_secret)
        logger.info(
            "MeshRelayAdapter started: url=%s, hmac=%s, patterns=%d",
            self._webhook_url,
            "configured" if has_secret else "NOT SET",
            len(patterns),
        )

    def stop(self) -> None:
        """Unsubscribe from all patterns."""
        for sub_id in self._subscription_ids:
            self._bus.unsubscribe(sub_id)
        self._subscription_ids.clear()
        logger.info("MeshRelayAdapter stopped")

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _build_webhook_body(self, event: EMEvent) -> dict:
        """Build the webhook payload matching the agreed schema."""
        return {
            "event_id": event.id or str(uuid.uuid4()),
            "event_type": event.event_type,
            "source": event.source.value if event.source else "system",
            "timestamp": event.timestamp or int(time.time()),
            "payload": event.payload,
            "text": _format_irc_line(event),
        }

    async def _handle_event(self, event: EMEvent) -> None:
        """Format and forward event to MeshRelay."""
        if not self._webhook_url:
            logger.debug("MeshRelayAdapter (no URL): %s", _format_irc_line(event))
            self._stats["forwarded"] += 1
            return

        if not self._webhook_secret:
            logger.warning(
                "MeshRelayAdapter: MESHRELAY_WEBHOOK_SECRET not set, skipping %s",
                event.event_type,
            )
            self._stats["errors"] += 1
            return

        try:
            body_dict = self._build_webhook_body(event)
            body_json = json.dumps(body_dict, default=str)
            timestamp = int(time.time())
            signature = _sign_payload(body_json, self._webhook_secret, timestamp)

            headers = {
                "Content-Type": "application/json",
                "X-EM-Signature": signature,
                "X-EM-Timestamp": str(timestamp),
                "User-Agent": "ExecutionMarket-MeshRelay/2.0",
            }

            client = await self._get_client()
            resp = await client.post(
                self._webhook_url,
                content=body_json,
                headers=headers,
            )

            if resp.status_code in (200, 201, 202, 204):
                self._stats["forwarded"] += 1
                logger.debug(
                    "MeshRelayAdapter: forwarded %s (status=%d)",
                    event.event_type,
                    resp.status_code,
                )
            else:
                self._stats["errors"] += 1
                logger.warning(
                    "MeshRelayAdapter: %s returned %d: %s",
                    event.event_type,
                    resp.status_code,
                    resp.text[:200],
                )
        except Exception:
            self._stats["errors"] += 1
            logger.exception("MeshRelayAdapter: failed to forward %s", event.event_type)

    @property
    def stats(self) -> dict:
        return dict(self._stats)
