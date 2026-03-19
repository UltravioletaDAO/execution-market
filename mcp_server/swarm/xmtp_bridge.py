"""
XMTPBridge — Connects the KK V2 Swarm to the XMTP Worker Bot.

This module bridges the swarm coordinator's task routing decisions to the
XMTP messaging layer, enabling:

    1. PUSH NOTIFICATIONS: When the swarm assigns a task → notify the worker via XMTP
    2. TASK BROADCASTS: New high-priority tasks → broadcast to registered workers
    3. DEADLINE ALERTS: Approaching deadlines → reminder messages to assigned workers
    4. COMPLETION EVENTS: Worker submits evidence via XMTP → swarm processes feedback
    5. REPUTATION UPDATES: After task completion → notify worker of reputation change

Architecture:
    SwarmCoordinator ──► XMTPBridge ──► XMTP Bot API
                                  ◄──  Webhook events

    The XMTP bot exposes a local HTTP API for the swarm to push notifications.
    The bot also sends webhook callbacks to the swarm when workers take actions.

Usage:
    bridge = XMTPBridge(
        bot_api_url="http://localhost:3100",
        em_api_url="https://api.execution.market",
    )

    # Push notification when swarm assigns task
    bridge.notify_task_assigned("task-uuid", "0xWorkerWallet", {
        "title": "Deliver coffee",
        "bounty_usdc": 5.0,
        "deadline": "2026-03-20T12:00:00Z",
    })

    # Broadcast new task to matching workers
    bridge.broadcast_new_task(task_data, worker_wallets=["0x...", "0x..."])

    # Process webhook callback from XMTP bot
    bridge.handle_webhook(event_type="submission", payload={...})
"""

import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Callable
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger("em.swarm.xmtp_bridge")


# ─── Event Types ──────────────────────────────────────────────────────────────


class XMTPEventType(str, Enum):
    """Events flowing between XMTP bot and swarm."""

    # Swarm → XMTP (push to workers)
    TASK_ASSIGNED = "task_assigned"
    TASK_BROADCAST = "task_broadcast"
    DEADLINE_REMINDER = "deadline_reminder"
    REPUTATION_UPDATE = "reputation_update"
    PAYMENT_CONFIRMED = "payment_confirmed"
    TASK_CANCELLED = "task_cancelled"

    # XMTP → Swarm (webhooks from workers)
    WORKER_REGISTERED = "worker_registered"
    WORKER_APPLIED = "worker_applied"
    EVIDENCE_SUBMITTED = "evidence_submitted"
    WORKER_RATED = "worker_rated"
    WORKER_MESSAGE = "worker_message"


class DeliveryStatus(str, Enum):
    """Delivery status for outbound messages."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


# ─── Data Models ──────────────────────────────────────────────────────────────


@dataclass
class NotificationPayload:
    """A message to be pushed to a worker via XMTP."""

    event_type: XMTPEventType
    recipient_wallet: str
    task_id: Optional[str] = None
    title: str = ""
    body: str = ""
    data: dict = field(default_factory=dict)
    priority: str = "normal"  # "normal", "high", "urgent"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "recipient": self.recipient_wallet,
            "task_id": self.task_id,
            "title": self.title,
            "body": self.body,
            "data": self.data,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class WebhookEvent:
    """An incoming event from the XMTP bot."""

    event_type: XMTPEventType
    sender_wallet: str
    task_id: Optional[str] = None
    payload: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_dict(cls, data: dict) -> "WebhookEvent":
        event_type_str = data.get("event_type", "worker_message")
        try:
            event_type = XMTPEventType(event_type_str)
        except ValueError:
            event_type = XMTPEventType.WORKER_MESSAGE

        return cls(
            event_type=event_type,
            sender_wallet=data.get("sender_wallet", data.get("sender", "")),
            task_id=data.get("task_id"),
            payload=data.get("payload", data.get("data", {})),
            timestamp=datetime.now(timezone.utc),
        )


@dataclass
class DeliveryRecord:
    """Tracks delivery of a notification."""

    notification_id: str
    status: DeliveryStatus
    recipient: str
    event_type: str
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    error: Optional[str] = None
    delivered_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "id": self.notification_id,
            "status": self.status.value,
            "recipient": self.recipient[:10] + "...",
            "event": self.event_type,
            "attempts": self.attempts,
            "last_attempt": self.last_attempt.isoformat()
            if self.last_attempt
            else None,
            "error": self.error,
        }


# ─── XMTP Bridge ─────────────────────────────────────────────────────────────


class XMTPBridge:
    """
    Bidirectional bridge between the KK V2 Swarm and the XMTP Worker Bot.

    Handles:
    - Outbound: Push notifications to workers when tasks are assigned/updated
    - Inbound: Process webhook callbacks from the XMTP bot
    - Delivery tracking: Monitor notification delivery with retry logic
    - Rate limiting: Prevent notification spam to workers
    """

    def __init__(
        self,
        bot_api_url: str = "http://localhost:3100",
        em_api_url: str = "https://api.execution.market",
        max_retries: int = 3,
        retry_delay_seconds: int = 5,
        rate_limit_per_worker: int = 10,  # Max notifications per hour per worker
        rate_limit_window: int = 3600,  # Window in seconds (1 hour)
    ):
        self.bot_api_url = bot_api_url.rstrip("/")
        self.em_api_url = em_api_url.rstrip("/")
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.rate_limit_per_worker = rate_limit_per_worker
        self.rate_limit_window = rate_limit_window

        # Delivery tracking
        self._delivery_log: deque[DeliveryRecord] = deque(maxlen=1000)
        self._pending_retries: list[NotificationPayload] = []

        # Rate limiting: wallet → list of timestamps
        self._rate_tracker: dict[str, list[float]] = {}

        # Webhook handlers
        self._webhook_handlers: dict[XMTPEventType, list[Callable]] = {}

        # Stats
        self._stats = {
            "notifications_sent": 0,
            "notifications_failed": 0,
            "notifications_rate_limited": 0,
            "webhooks_received": 0,
            "webhooks_processed": 0,
        }

        # Notification counter for IDs
        self._notification_counter = 0

    # ─── Outbound: Push Notifications ─────────────────────────────

    def notify_task_assigned(
        self,
        task_id: str,
        worker_wallet: str,
        task_data: dict,
    ) -> DeliveryRecord:
        """
        Notify a worker that they've been assigned a task.

        This is the primary notification path — triggered when the
        SwarmOrchestrator.route_task() selects a worker.
        """
        title = task_data.get("title", "New task assigned")
        bounty = task_data.get("bounty_usdc", task_data.get("bounty", 0))
        deadline = task_data.get("deadline", "No deadline")

        body = (
            f"📋 *Task Assigned*\n\n"
            f"**{title}**\n"
            f"💰 ${bounty:.2f} USDC\n"
            f"⏰ Deadline: {deadline}\n\n"
            f"Use `/status {task_id[:8]}` for details.\n"
            f"Use `/submit {task_id[:8]}` when ready."
        )

        notification = NotificationPayload(
            event_type=XMTPEventType.TASK_ASSIGNED,
            recipient_wallet=worker_wallet,
            task_id=task_id,
            title=f"Task Assigned: {title}",
            body=body,
            data=task_data,
            priority="high",
        )

        return self._send_notification(notification)

    def broadcast_new_task(
        self,
        task_data: dict,
        worker_wallets: list[str],
    ) -> list[DeliveryRecord]:
        """
        Broadcast a new available task to multiple workers.

        Used when the swarm discovers a new task that matches
        multiple workers' skill profiles.
        """
        title = task_data.get("title", "New task available")
        bounty = task_data.get("bounty_usdc", task_data.get("bounty", 0))
        category = task_data.get("category", "general")
        task_id = task_data.get("id", "")

        body = (
            f"🆕 *New Task Available*\n\n"
            f"**{title}**\n"
            f"📁 Category: {category}\n"
            f"💰 ${bounty:.2f} USDC\n\n"
            f"Use `/apply {task_id[:8]}` to apply."
        )

        results = []
        for wallet in worker_wallets:
            notification = NotificationPayload(
                event_type=XMTPEventType.TASK_BROADCAST,
                recipient_wallet=wallet,
                task_id=task_id,
                title=f"New Task: {title}",
                body=body,
                data=task_data,
                priority="normal",
            )
            result = self._send_notification(notification)
            results.append(result)

        return results

    def notify_deadline_reminder(
        self,
        task_id: str,
        worker_wallet: str,
        task_title: str,
        deadline: str,
        hours_remaining: float,
    ) -> DeliveryRecord:
        """Send a deadline reminder to an assigned worker."""
        urgency = "🔴" if hours_remaining < 2 else "🟡" if hours_remaining < 6 else "🟢"

        body = (
            f"{urgency} *Deadline Reminder*\n\n"
            f"**{task_title}**\n"
            f"⏰ {hours_remaining:.1f} hours remaining\n"
            f"📅 Deadline: {deadline}\n\n"
            f"Use `/submit {task_id[:8]}` to submit evidence."
        )

        notification = NotificationPayload(
            event_type=XMTPEventType.DEADLINE_REMINDER,
            recipient_wallet=worker_wallet,
            task_id=task_id,
            title=f"Deadline in {hours_remaining:.0f}h: {task_title}",
            body=body,
            priority="high" if hours_remaining < 2 else "normal",
        )

        return self._send_notification(notification)

    def notify_reputation_update(
        self,
        worker_wallet: str,
        task_id: str,
        score: float,
        new_average: float,
        total_ratings: int,
    ) -> DeliveryRecord:
        """Notify a worker about a reputation update after task completion."""
        stars = "★" * round(score / 20) + "☆" * (5 - round(score / 20))

        body = (
            f"⭐ *Reputation Updated*\n\n"
            f"New rating: {stars} ({score}/100)\n"
            f"Average: {new_average:.1f}/5.0\n"
            f"Total ratings: {total_ratings}\n\n"
            f"Use `/reputation` to see full details."
        )

        notification = NotificationPayload(
            event_type=XMTPEventType.REPUTATION_UPDATE,
            recipient_wallet=worker_wallet,
            task_id=task_id,
            title="Reputation Updated",
            body=body,
            priority="normal",
        )

        return self._send_notification(notification)

    def notify_payment_confirmed(
        self,
        worker_wallet: str,
        task_id: str,
        amount: float,
        chain: str,
        tx_hash: str,
    ) -> DeliveryRecord:
        """Notify a worker that payment has been confirmed on-chain."""
        body = (
            f"💰 *Payment Confirmed*\n\n"
            f"Amount: ${amount:.2f} USDC\n"
            f"Chain: {chain}\n"
            f"TX: `{tx_hash[:10]}...{tx_hash[-6:]}`\n\n"
            f"Use `/balance` to check your balance.\n"
            f"Use `/earnings` for payment history."
        )

        notification = NotificationPayload(
            event_type=XMTPEventType.PAYMENT_CONFIRMED,
            recipient_wallet=worker_wallet,
            task_id=task_id,
            title=f"Payment: ${amount:.2f} USDC on {chain}",
            body=body,
            data={"amount": amount, "chain": chain, "tx_hash": tx_hash},
            priority="high",
        )

        return self._send_notification(notification)

    # ─── Inbound: Webhook Processing ─────────────────────────────

    def register_webhook_handler(
        self,
        event_type: XMTPEventType,
        handler: Callable[[WebhookEvent], None],
    ) -> None:
        """Register a handler for incoming XMTP webhook events."""
        if event_type not in self._webhook_handlers:
            self._webhook_handlers[event_type] = []
        self._webhook_handlers[event_type].append(handler)

    def handle_webhook(self, raw_event: dict) -> bool:
        """
        Process an incoming webhook event from the XMTP bot.

        Returns True if the event was handled, False otherwise.
        """
        self._stats["webhooks_received"] += 1

        try:
            event = WebhookEvent.from_dict(raw_event)
        except Exception as e:
            logger.error(f"Failed to parse webhook event: {e}")
            return False

        handlers = self._webhook_handlers.get(event.event_type, [])
        if not handlers:
            logger.debug(f"No handlers for event type: {event.event_type.value}")
            return False

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Webhook handler error for {event.event_type.value}: {e}")

        self._stats["webhooks_processed"] += 1
        return True

    # ─── Rate Limiting ────────────────────────────────────────────

    def _check_rate_limit(self, wallet: str) -> bool:
        """
        Check if a worker has exceeded their notification rate limit.

        Returns True if the notification should be ALLOWED.
        """
        now = time.time()
        window_start = now - self.rate_limit_window

        # Clean old entries
        if wallet in self._rate_tracker:
            self._rate_tracker[wallet] = [
                ts for ts in self._rate_tracker[wallet] if ts > window_start
            ]
        else:
            self._rate_tracker[wallet] = []

        # Check limit
        if len(self._rate_tracker[wallet]) >= self.rate_limit_per_worker:
            return False

        # Record this notification
        self._rate_tracker[wallet].append(now)
        return True

    # ─── Internal: Send Notification ──────────────────────────────

    def _send_notification(self, notification: NotificationPayload) -> DeliveryRecord:
        """
        Send a notification to the XMTP bot API.

        Handles rate limiting, delivery tracking, and retry scheduling.
        """
        self._notification_counter += 1
        notification_id = f"notif-{self._notification_counter:06d}"

        record = DeliveryRecord(
            notification_id=notification_id,
            status=DeliveryStatus.PENDING,
            recipient=notification.recipient_wallet,
            event_type=notification.event_type.value,
        )

        # Rate limit check
        if not self._check_rate_limit(notification.recipient_wallet):
            record.status = DeliveryStatus.FAILED
            record.error = "Rate limited"
            self._stats["notifications_rate_limited"] += 1
            self._delivery_log.append(record)
            logger.warning(
                f"Rate limited notification to {notification.recipient_wallet[:10]}..."
            )
            return record

        # Attempt delivery
        success = self._deliver(notification, record)

        if success:
            record.status = DeliveryStatus.SENT
            record.delivered_at = datetime.now(timezone.utc)
            self._stats["notifications_sent"] += 1
        else:
            record.status = DeliveryStatus.FAILED
            self._stats["notifications_failed"] += 1
            # Schedule for retry if under max retries
            if record.attempts < self.max_retries:
                record.status = DeliveryStatus.RETRYING
                self._pending_retries.append(notification)

        self._delivery_log.append(record)
        return record

    def _deliver(
        self, notification: NotificationPayload, record: DeliveryRecord
    ) -> bool:
        """
        Actually send the HTTP request to the XMTP bot API.

        Returns True on success, False on failure.
        """
        record.attempts += 1
        record.last_attempt = datetime.now(timezone.utc)

        url = f"{self.bot_api_url}/api/notify"
        payload = json.dumps(notification.to_dict()).encode("utf-8")

        try:
            req = Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=10) as resp:
                if resp.status < 300:
                    logger.info(
                        f"Notification sent: {notification.event_type.value} "
                        f"to {notification.recipient_wallet[:10]}..."
                    )
                    return True
                else:
                    record.error = f"HTTP {resp.status}"
                    return False
        except (URLError, HTTPError, TimeoutError) as e:
            record.error = str(e)[:200]
            logger.warning(
                f"Notification delivery failed: {notification.event_type.value} "
                f"to {notification.recipient_wallet[:10]}...: {e}"
            )
            return False
        except Exception as e:
            record.error = f"Unexpected: {str(e)[:100]}"
            logger.error(f"Unexpected notification error: {e}")
            return False

    def process_retry_queue(self) -> int:
        """
        Process pending retries. Returns number of successful retries.

        Called periodically by the SwarmRunner's MONITOR phase.
        """
        if not self._pending_retries:
            return 0

        retries = self._pending_retries[:]
        self._pending_retries.clear()
        successes = 0

        for notification in retries:
            record = DeliveryRecord(
                notification_id=f"retry-{self._notification_counter:06d}",
                status=DeliveryStatus.RETRYING,
                recipient=notification.recipient_wallet,
                event_type=notification.event_type.value,
            )
            if self._deliver(notification, record):
                record.status = DeliveryStatus.SENT
                record.delivered_at = datetime.now(timezone.utc)
                self._stats["notifications_sent"] += 1
                successes += 1
            else:
                self._stats["notifications_failed"] += 1

            self._delivery_log.append(record)

        return successes

    # ─── Status & Metrics ─────────────────────────────────────────

    def get_status(self) -> dict:
        """Get bridge operational status."""
        recent_deliveries = [r.to_dict() for r in list(self._delivery_log)[-10:]]

        return {
            "connected": True,  # TODO: health check to bot API
            "bot_api_url": self.bot_api_url,
            "stats": self._stats.copy(),
            "pending_retries": len(self._pending_retries),
            "total_delivery_records": len(self._delivery_log),
            "recent_deliveries": recent_deliveries,
            "registered_handlers": {
                et.value: len(handlers)
                for et, handlers in self._webhook_handlers.items()
            },
            "rate_limit": {
                "per_worker_per_hour": self.rate_limit_per_worker,
                "tracked_wallets": len(self._rate_tracker),
            },
        }

    def get_delivery_history(self, limit: int = 50) -> list[dict]:
        """Get recent delivery history."""
        return [r.to_dict() for r in list(self._delivery_log)[-limit:]]

    def get_stats(self) -> dict:
        """Get bridge statistics."""
        total = self._stats["notifications_sent"] + self._stats["notifications_failed"]
        success_rate = (
            (self._stats["notifications_sent"] / total * 100) if total > 0 else 0.0
        )
        return {
            **self._stats,
            "total_attempted": total,
            "success_rate_pct": round(success_rate, 1),
        }
