"""
WebSocket Event Handlers for Chamba

Handles broadcasting events to appropriate room subscribers with:
- Permission filtering
- Rate limiting per event type
- Event enrichment
- Delivery tracking

These handlers are called from MCP tools when state changes occur.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from collections import defaultdict
from dataclasses import dataclass, field

from .events import (
    WebSocketEvent,
    WebSocketEventType,
    TaskCreatedPayload,
    TaskUpdatedPayload,
    TaskCancelledPayload,
    ApplicationReceivedPayload,
    WorkerAssignedPayload,
    SubmissionReceivedPayload,
    SubmissionApprovedPayload,
    SubmissionRejectedPayload,
    PaymentReleasedPayload,
    PaymentFailedPayload,
    NotificationNewPayload,
    get_task_room,
    get_user_room,
    get_category_room,
    get_global_room,
)
from .server import ws_manager, Connection

logger = logging.getLogger(__name__)


# ============== RATE LIMITING ==============


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting events."""
    max_events_per_minute: int = 60
    max_events_per_hour: int = 1000
    cooldown_seconds: float = 0.1  # Min time between events of same type


class EventRateLimiter:
    """Rate limiter for WebSocket events by user and event type."""

    def __init__(self):
        # Track events per user per minute
        self._minute_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._hour_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._last_event: Dict[str, Dict[str, datetime]] = defaultdict(dict)
        self._minute_reset: datetime = datetime.now(timezone.utc)
        self._hour_reset: datetime = datetime.now(timezone.utc)
        self._config = RateLimitConfig()

    def check_and_record(self, user_id: str, event_type: str) -> bool:
        """
        Check if an event can be sent and record it if allowed.

        Returns:
            True if event is allowed, False if rate limited
        """
        now = datetime.now(timezone.utc)

        # Reset minute counter
        if (now - self._minute_reset).total_seconds() > 60:
            self._minute_counts.clear()
            self._minute_reset = now

        # Reset hour counter
        if (now - self._hour_reset).total_seconds() > 3600:
            self._hour_counts.clear()
            self._hour_reset = now

        # Check cooldown
        last = self._last_event[user_id].get(event_type)
        if last and (now - last).total_seconds() < self._config.cooldown_seconds:
            return False

        # Check minute limit
        if self._minute_counts[user_id][event_type] >= self._config.max_events_per_minute:
            logger.warning(f"Rate limit (minute) for {user_id}/{event_type}")
            return False

        # Check hour limit
        if self._hour_counts[user_id][event_type] >= self._config.max_events_per_hour:
            logger.warning(f"Rate limit (hour) for {user_id}/{event_type}")
            return False

        # Record event
        self._minute_counts[user_id][event_type] += 1
        self._hour_counts[user_id][event_type] += 1
        self._last_event[user_id][event_type] = now

        return True


# Global rate limiter
rate_limiter = EventRateLimiter()


# ============== PERMISSION CHECKING ==============


async def check_task_access(connection: Connection, task_id: str, task_data: Dict[str, Any]) -> bool:
    """
    Check if a connection has access to task events.

    Args:
        connection: The WebSocket connection
        task_id: The task ID
        task_data: Task data containing agent_id and executor_id

    Returns:
        True if connection has access
    """
    if not connection.is_authenticated:
        return False

    user_id = connection.user_id

    # Task owner (agent) always has access
    if task_data.get("agent_id") == user_id:
        return True

    # Assigned worker has access
    if task_data.get("executor_id") == user_id:
        return True

    # Workers subscribed to category have limited access (only new tasks)
    # This is handled by room subscriptions

    return False


async def check_submission_access(
    connection: Connection,
    submission_data: Dict[str, Any],
    task_data: Dict[str, Any]
) -> bool:
    """Check if a connection has access to submission events."""
    if not connection.is_authenticated:
        return False

    user_id = connection.user_id

    # Task owner sees all submissions
    if task_data.get("agent_id") == user_id:
        return True

    # Submitter sees their own submissions
    if submission_data.get("executor_id") == user_id:
        return True

    return False


async def check_payment_access(connection: Connection, payment_data: Dict[str, Any]) -> bool:
    """Check if a connection has access to payment events."""
    if not connection.is_authenticated:
        return False

    user_id = connection.user_id

    # Payer (agent) has access
    if payment_data.get("agent_id") == user_id:
        return True

    # Recipient (worker) has access
    if payment_data.get("recipient_id") == user_id:
        return True

    return False


# ============== EVENT HANDLERS ==============


class EventHandlers:
    """
    Centralized event handlers for broadcasting WebSocket events.

    Usage:
        from websocket.handlers import handlers
        await handlers.task_created(task_data)
    """

    def __init__(self):
        self._delivery_stats: Dict[str, int] = defaultdict(int)

    # ============== TASK EVENTS ==============

    async def task_created(self, task: Dict[str, Any]) -> int:
        """
        Broadcast task creation event.

        Notifies:
        - Task owner (via user room)
        - Workers subscribed to the task category

        Args:
            task: Task data dict

        Returns:
            Number of connections notified
        """
        agent_id = task.get("agent_id", "")

        if not rate_limiter.check_and_record(agent_id, "TaskCreated"):
            return 0

        payload = TaskCreatedPayload(
            task_id=task["id"],
            title=task["title"],
            category=task["category"],
            bounty_usd=task["bounty_usd"],
            deadline=task.get("deadline", ""),
            agent_id=agent_id,
            location_hint=task.get("location_hint"),
            min_reputation=task.get("min_reputation", 0),
            evidence_required=task.get("evidence_required", []),
            payment_token=task.get("payment_token", "USDC"),
        )

        event = WebSocketEvent.task_created(payload)
        total_sent = 0

        # Notify task owner
        sent = await ws_manager.send_to_user(agent_id, event)
        total_sent += sent

        # Notify workers subscribed to category
        category_room = get_category_room(task["category"])
        # For category room, we broadcast the full task info for discovery
        sent = await ws_manager.broadcast_to_room(category_room, event)
        total_sent += sent

        self._delivery_stats["TaskCreated"] += total_sent
        logger.info(f"TaskCreated event sent to {total_sent} connections")
        return total_sent

    async def task_updated(
        self,
        task: Dict[str, Any],
        updated_fields: List[str],
        previous_status: Optional[str] = None,
    ) -> int:
        """
        Broadcast task update event.

        Notifies:
        - Task owner
        - Assigned worker (if any)
        - Subscribers to task room

        Args:
            task: Updated task data
            updated_fields: List of fields that changed
            previous_status: Previous task status if changed

        Returns:
            Number of connections notified
        """
        agent_id = task.get("agent_id", "")

        if not rate_limiter.check_and_record(agent_id, "TaskUpdated"):
            return 0

        payload = TaskUpdatedPayload(
            task_id=task["id"],
            status=task["status"],
            previous_status=previous_status,
            updated_fields=updated_fields,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        event = WebSocketEvent.task_updated(payload, get_task_room(task["id"]))
        total_sent = 0

        # Notify task room subscribers
        sent = await ws_manager.broadcast_to_room(get_task_room(task["id"]), event)
        total_sent += sent

        # Also notify owner directly if not subscribed to task room
        sent = await ws_manager.send_to_user(agent_id, event)
        total_sent += sent

        # Notify assigned worker
        executor_id = task.get("executor_id")
        if executor_id:
            sent = await ws_manager.send_to_user(executor_id, event)
            total_sent += sent

        self._delivery_stats["TaskUpdated"] += total_sent
        logger.info(f"TaskUpdated event sent to {total_sent} connections")
        return total_sent

    async def task_cancelled(
        self,
        task: Dict[str, Any],
        reason: Optional[str] = None,
        refund_initiated: bool = False,
    ) -> int:
        """
        Broadcast task cancellation event.

        Notifies:
        - Task owner
        - Assigned worker (if any)
        - All task room subscribers

        Args:
            task: Cancelled task data
            reason: Cancellation reason
            refund_initiated: Whether refund was initiated

        Returns:
            Number of connections notified
        """
        agent_id = task.get("agent_id", "")

        if not rate_limiter.check_and_record(agent_id, "TaskCancelled"):
            return 0

        payload = TaskCancelledPayload(
            task_id=task["id"],
            title=task["title"],
            reason=reason,
            cancelled_by=agent_id,
            refund_initiated=refund_initiated,
        )

        event = WebSocketEvent.task_cancelled(payload, get_task_room(task["id"]))
        total_sent = 0

        # Notify task room
        sent = await ws_manager.broadcast_to_room(get_task_room(task["id"]), event)
        total_sent += sent

        # Notify owner
        sent = await ws_manager.send_to_user(agent_id, event)
        total_sent += sent

        # Notify assigned worker
        executor_id = task.get("executor_id")
        if executor_id:
            sent = await ws_manager.send_to_user(executor_id, event)
            total_sent += sent

        self._delivery_stats["TaskCancelled"] += total_sent
        logger.info(f"TaskCancelled event sent to {total_sent} connections")
        return total_sent

    # ============== APPLICATION EVENTS ==============

    async def application_received(
        self,
        application: Dict[str, Any],
        task: Dict[str, Any],
        worker: Dict[str, Any],
    ) -> int:
        """
        Broadcast worker application event.

        Notifies:
        - Task owner (agent)

        Args:
            application: Application data
            task: Task data
            worker: Worker data

        Returns:
            Number of connections notified
        """
        agent_id = task.get("agent_id", "")

        if not rate_limiter.check_and_record(agent_id, "ApplicationReceived"):
            return 0

        payload = ApplicationReceivedPayload(
            application_id=application.get("id", ""),
            task_id=task["id"],
            worker_id=worker.get("id", ""),
            worker_name=worker.get("display_name"),
            worker_reputation=worker.get("reputation_score", 0.0),
            message=application.get("message"),
            applied_at=application.get("created_at"),
        )

        event = WebSocketEvent.application_received(payload, agent_id)

        sent = await ws_manager.send_to_user(agent_id, event)

        self._delivery_stats["ApplicationReceived"] += sent
        logger.info(f"ApplicationReceived event sent to {sent} connections")
        return sent

    async def worker_assigned(
        self,
        task: Dict[str, Any],
        worker: Dict[str, Any],
    ) -> int:
        """
        Broadcast worker assignment event.

        Notifies:
        - Task owner (agent)
        - Assigned worker

        Args:
            task: Task data
            worker: Assigned worker data

        Returns:
            Number of connections notified
        """
        agent_id = task.get("agent_id", "")
        worker_id = worker.get("id", "")

        if not rate_limiter.check_and_record(agent_id, "WorkerAssigned"):
            return 0

        payload = WorkerAssignedPayload(
            task_id=task["id"],
            worker_id=worker_id,
            worker_name=worker.get("display_name"),
            worker_wallet=worker.get("wallet_address"),
            assigned_at=datetime.now(timezone.utc).isoformat(),
            expected_completion=task.get("deadline"),
        )

        events = WebSocketEvent.worker_assigned(
            payload,
            rooms=[get_user_room(agent_id), get_user_room(worker_id)]
        )

        total_sent = 0
        for event in events:
            sent = await ws_manager.broadcast_to_room(event.room, event)
            total_sent += sent

        self._delivery_stats["WorkerAssigned"] += total_sent
        logger.info(f"WorkerAssigned event sent to {total_sent} connections")
        return total_sent

    # ============== SUBMISSION EVENTS ==============

    async def submission_received(
        self,
        submission: Dict[str, Any],
        task: Dict[str, Any],
    ) -> int:
        """
        Broadcast submission received event.

        Notifies:
        - Task owner (agent)

        Args:
            submission: Submission data
            task: Task data

        Returns:
            Number of connections notified
        """
        agent_id = task.get("agent_id", "")

        if not rate_limiter.check_and_record(agent_id, "SubmissionReceived"):
            return 0

        evidence = submission.get("evidence", {})
        evidence_types = list(evidence.keys()) if isinstance(evidence, dict) else []

        payload = SubmissionReceivedPayload(
            submission_id=submission["id"],
            task_id=task["id"],
            task_title=task["title"],
            worker_id=submission.get("executor_id", ""),
            evidence_types=evidence_types,
            submitted_at=submission.get("submitted_at"),
            auto_verification_score=submission.get("verification_score"),
        )

        event = WebSocketEvent.submission_received(payload, agent_id)

        sent = await ws_manager.send_to_user(agent_id, event)

        self._delivery_stats["SubmissionReceived"] += sent
        logger.info(f"SubmissionReceived event sent to {sent} connections")
        return sent

    async def submission_approved(
        self,
        submission: Dict[str, Any],
        task: Dict[str, Any],
        notes: Optional[str] = None,
        payment_initiated: bool = False,
    ) -> int:
        """
        Broadcast submission approval event.

        Notifies:
        - Worker (submitter)
        - Task room subscribers

        Args:
            submission: Approved submission
            task: Task data
            notes: Approval notes
            payment_initiated: Whether payment was initiated

        Returns:
            Number of connections notified
        """
        worker_id = submission.get("executor_id", "")
        agent_id = task.get("agent_id", "")

        if not rate_limiter.check_and_record(worker_id, "SubmissionApproved"):
            return 0

        payload = SubmissionApprovedPayload(
            submission_id=submission["id"],
            task_id=task["id"],
            worker_id=worker_id,
            approved_by=agent_id,
            notes=notes,
            payment_initiated=payment_initiated,
            approved_at=datetime.now(timezone.utc).isoformat(),
        )

        event = WebSocketEvent.submission_approved(payload)
        total_sent = 0

        # Notify worker
        sent = await ws_manager.send_to_user(worker_id, event)
        total_sent += sent

        # Notify task room
        sent = await ws_manager.broadcast_to_room(get_task_room(task["id"]), event)
        total_sent += sent

        self._delivery_stats["SubmissionApproved"] += total_sent
        logger.info(f"SubmissionApproved event sent to {total_sent} connections")
        return total_sent

    async def submission_rejected(
        self,
        submission: Dict[str, Any],
        task: Dict[str, Any],
        reason: str,
        can_resubmit: bool = True,
    ) -> int:
        """
        Broadcast submission rejection event.

        Notifies:
        - Worker (submitter)

        Args:
            submission: Rejected submission
            task: Task data
            reason: Rejection reason
            can_resubmit: Whether worker can resubmit

        Returns:
            Number of connections notified
        """
        worker_id = submission.get("executor_id", "")
        agent_id = task.get("agent_id", "")

        if not rate_limiter.check_and_record(worker_id, "SubmissionRejected"):
            return 0

        payload = SubmissionRejectedPayload(
            submission_id=submission["id"],
            task_id=task["id"],
            worker_id=worker_id,
            rejected_by=agent_id,
            reason=reason,
            can_resubmit=can_resubmit,
            rejected_at=datetime.now(timezone.utc).isoformat(),
        )

        event = WebSocketEvent.submission_rejected(payload)

        sent = await ws_manager.send_to_user(worker_id, event)

        self._delivery_stats["SubmissionRejected"] += sent
        logger.info(f"SubmissionRejected event sent to {sent} connections")
        return sent

    # ============== PAYMENT EVENTS ==============

    async def payment_released(
        self,
        payment: Dict[str, Any],
        task: Dict[str, Any],
        worker_id: str,
    ) -> int:
        """
        Broadcast payment released event.

        Notifies:
        - Worker (recipient)
        - Task owner (payer)

        Args:
            payment: Payment data
            task: Task data
            worker_id: Recipient worker ID

        Returns:
            Number of connections notified
        """
        agent_id = task.get("agent_id", "")

        if not rate_limiter.check_and_record(worker_id, "PaymentReleased"):
            return 0

        payload = PaymentReleasedPayload(
            payment_id=payment.get("id", ""),
            task_id=task["id"],
            amount_usd=payment.get("amount_usd", task.get("bounty_usd", 0)),
            worker_amount=payment.get("worker_amount", 0),
            platform_fee=payment.get("platform_fee", 0),
            recipient_wallet=payment.get("recipient_wallet", ""),
            tx_hash=payment.get("tx_hash"),
            token=payment.get("token", "USDC"),
            chain=payment.get("chain", "base"),
            released_at=datetime.now(timezone.utc).isoformat(),
        )

        event = WebSocketEvent.payment_released(payload, worker_id)
        total_sent = 0

        # Notify worker
        sent = await ws_manager.send_to_user(worker_id, event)
        total_sent += sent

        # Also notify agent
        sent = await ws_manager.send_to_user(agent_id, event)
        total_sent += sent

        self._delivery_stats["PaymentReleased"] += total_sent
        logger.info(f"PaymentReleased event sent to {total_sent} connections")
        return total_sent

    async def payment_failed(
        self,
        task: Dict[str, Any],
        error_code: str,
        error_message: str,
        retry_available: bool = True,
    ) -> int:
        """
        Broadcast payment failure event.

        Notifies:
        - Task owner (agent)
        - Worker (if known)

        Args:
            task: Task data
            error_code: Error code
            error_message: Error description
            retry_available: Whether retry is possible

        Returns:
            Number of connections notified
        """
        agent_id = task.get("agent_id", "")

        if not rate_limiter.check_and_record(agent_id, "PaymentFailed"):
            return 0

        payload = PaymentFailedPayload(
            task_id=task["id"],
            amount_usd=task.get("bounty_usd", 0),
            error_code=error_code,
            error_message=error_message,
            retry_available=retry_available,
            failed_at=datetime.now(timezone.utc).isoformat(),
        )

        event = WebSocketEvent.payment_failed(payload, agent_id)
        total_sent = 0

        # Notify agent
        sent = await ws_manager.send_to_user(agent_id, event)
        total_sent += sent

        # Notify worker if assigned
        executor_id = task.get("executor_id")
        if executor_id:
            event_for_worker = WebSocketEvent.payment_failed(payload, executor_id)
            sent = await ws_manager.send_to_user(executor_id, event_for_worker)
            total_sent += sent

        self._delivery_stats["PaymentFailed"] += total_sent
        logger.info(f"PaymentFailed event sent to {total_sent} connections")
        return total_sent

    # ============== NOTIFICATION EVENTS ==============

    async def send_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        task_id: Optional[str] = None,
        action_url: Optional[str] = None,
        priority: str = "normal",
    ) -> int:
        """
        Send a notification event to a user.

        Args:
            user_id: Target user
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            task_id: Related task ID
            action_url: URL for action button
            priority: Notification priority

        Returns:
            Number of connections notified
        """
        if not rate_limiter.check_and_record(user_id, "NotificationNew"):
            return 0

        payload = NotificationNewPayload(
            notification_id=f"notif_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
            task_id=task_id,
            priority=priority,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        event = WebSocketEvent.notification(payload, user_id)

        sent = await ws_manager.send_to_user(user_id, event)

        self._delivery_stats["NotificationNew"] += sent
        return sent

    # ============== STATISTICS ==============

    def get_delivery_stats(self) -> Dict[str, int]:
        """Get event delivery statistics."""
        return dict(self._delivery_stats)

    def reset_stats(self) -> None:
        """Reset delivery statistics."""
        self._delivery_stats.clear()


# ============== GLOBAL INSTANCE ==============


handlers = EventHandlers()


# ============== EXPORTS ==============


__all__ = [
    "EventHandlers",
    "EventRateLimiter",
    "handlers",
    "rate_limiter",
    "check_task_access",
    "check_submission_access",
    "check_payment_access",
]
