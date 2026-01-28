"""
WebSocket Integration Module for Chamba MCP Tools

Provides simple functions for emitting WebSocket events from MCP tools
and other parts of the application. This module handles the complexity
of importing and using the WebSocket handlers.

Usage in MCP tools:
    from websocket.integration import emit_event, events

    # Emit a task created event
    await events.task_created(task_data)

    # Or use the generic emit_event
    await emit_event("task_created", task_data)
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# ============== EVENT EMITTER ==============


class EventEmitter:
    """
    Lazy-loading event emitter for WebSocket events.

    This class provides a simple interface for emitting events
    while handling the complexity of optional WebSocket availability.
    """

    def __init__(self):
        self._handlers = None
        self._initialized = False

    def _get_handlers(self):
        """Lazy-load the handlers module."""
        if not self._initialized:
            self._initialized = True
            try:
                from .handlers import handlers
                self._handlers = handlers
                logger.debug("WebSocket handlers loaded")
            except ImportError as e:
                logger.debug(f"WebSocket handlers not available: {e}")
                self._handlers = None
        return self._handlers

    @property
    def available(self) -> bool:
        """Check if WebSocket handlers are available."""
        return self._get_handlers() is not None

    # ============== TASK EVENTS ==============

    async def task_created(self, task: Dict[str, Any]) -> int:
        """
        Emit TaskCreated event.

        Args:
            task: Task data dict with id, title, category, bounty_usd, etc.

        Returns:
            Number of connections notified (0 if unavailable)
        """
        handlers = self._get_handlers()
        if handlers:
            try:
                return await handlers.task_created(task)
            except Exception as e:
                logger.error(f"Failed to emit task_created: {e}")
        return 0

    async def task_updated(
        self,
        task: Dict[str, Any],
        updated_fields: list = None,
        previous_status: Optional[str] = None,
    ) -> int:
        """Emit TaskUpdated event."""
        handlers = self._get_handlers()
        if handlers:
            try:
                return await handlers.task_updated(
                    task, updated_fields or [], previous_status
                )
            except Exception as e:
                logger.error(f"Failed to emit task_updated: {e}")
        return 0

    async def task_cancelled(
        self,
        task: Dict[str, Any],
        reason: Optional[str] = None,
        refund_initiated: bool = False,
    ) -> int:
        """Emit TaskCancelled event."""
        handlers = self._get_handlers()
        if handlers:
            try:
                return await handlers.task_cancelled(task, reason, refund_initiated)
            except Exception as e:
                logger.error(f"Failed to emit task_cancelled: {e}")
        return 0

    # ============== APPLICATION EVENTS ==============

    async def application_received(
        self,
        application: Dict[str, Any],
        task: Dict[str, Any],
        worker: Dict[str, Any],
    ) -> int:
        """
        Emit ApplicationReceived event.

        Args:
            application: Application data
            task: Task data
            worker: Worker data

        Returns:
            Number of connections notified
        """
        handlers = self._get_handlers()
        if handlers:
            try:
                return await handlers.application_received(application, task, worker)
            except Exception as e:
                logger.error(f"Failed to emit application_received: {e}")
        return 0

    async def worker_assigned(
        self,
        task: Dict[str, Any],
        worker: Dict[str, Any],
    ) -> int:
        """Emit WorkerAssigned event."""
        handlers = self._get_handlers()
        if handlers:
            try:
                return await handlers.worker_assigned(task, worker)
            except Exception as e:
                logger.error(f"Failed to emit worker_assigned: {e}")
        return 0

    # ============== SUBMISSION EVENTS ==============

    async def submission_received(
        self,
        submission: Dict[str, Any],
        task: Dict[str, Any],
    ) -> int:
        """Emit SubmissionReceived event."""
        handlers = self._get_handlers()
        if handlers:
            try:
                return await handlers.submission_received(submission, task)
            except Exception as e:
                logger.error(f"Failed to emit submission_received: {e}")
        return 0

    async def submission_approved(
        self,
        submission: Dict[str, Any],
        task: Dict[str, Any],
        notes: Optional[str] = None,
        payment_initiated: bool = False,
    ) -> int:
        """Emit SubmissionApproved event."""
        handlers = self._get_handlers()
        if handlers:
            try:
                return await handlers.submission_approved(
                    submission, task, notes, payment_initiated
                )
            except Exception as e:
                logger.error(f"Failed to emit submission_approved: {e}")
        return 0

    async def submission_rejected(
        self,
        submission: Dict[str, Any],
        task: Dict[str, Any],
        reason: str,
        can_resubmit: bool = True,
    ) -> int:
        """Emit SubmissionRejected event."""
        handlers = self._get_handlers()
        if handlers:
            try:
                return await handlers.submission_rejected(
                    submission, task, reason, can_resubmit
                )
            except Exception as e:
                logger.error(f"Failed to emit submission_rejected: {e}")
        return 0

    # ============== PAYMENT EVENTS ==============

    async def payment_released(
        self,
        payment: Dict[str, Any],
        task: Dict[str, Any],
        worker_id: str,
    ) -> int:
        """Emit PaymentReleased event."""
        handlers = self._get_handlers()
        if handlers:
            try:
                return await handlers.payment_released(payment, task, worker_id)
            except Exception as e:
                logger.error(f"Failed to emit payment_released: {e}")
        return 0

    async def payment_failed(
        self,
        task: Dict[str, Any],
        error_code: str,
        error_message: str,
        retry_available: bool = True,
    ) -> int:
        """Emit PaymentFailed event."""
        handlers = self._get_handlers()
        if handlers:
            try:
                return await handlers.payment_failed(
                    task, error_code, error_message, retry_available
                )
            except Exception as e:
                logger.error(f"Failed to emit payment_failed: {e}")
        return 0

    # ============== NOTIFICATION EVENTS ==============

    async def notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        task_id: Optional[str] = None,
        action_url: Optional[str] = None,
        priority: str = "normal",
    ) -> int:
        """Send a notification to a user."""
        handlers = self._get_handlers()
        if handlers:
            try:
                return await handlers.send_notification(
                    user_id=user_id,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    task_id=task_id,
                    action_url=action_url,
                    priority=priority,
                )
            except Exception as e:
                logger.error(f"Failed to emit notification: {e}")
        return 0

    # ============== GENERIC EMIT ==============

    async def emit(self, event_name: str, **kwargs) -> int:
        """
        Generic event emit by name.

        Args:
            event_name: Name of the event (e.g., "task_created")
            **kwargs: Event-specific arguments

        Returns:
            Number of connections notified
        """
        method = getattr(self, event_name, None)
        if method and callable(method):
            return await method(**kwargs)
        else:
            logger.warning(f"Unknown event type: {event_name}")
            return 0


# ============== GLOBAL INSTANCE ==============


# Global event emitter instance
events = EventEmitter()


# ============== CONVENIENCE FUNCTIONS ==============


async def emit_event(event_name: str, **kwargs) -> int:
    """
    Emit a WebSocket event by name.

    Convenience function that wraps the global events emitter.

    Args:
        event_name: Name of the event (e.g., "task_created")
        **kwargs: Event-specific arguments

    Returns:
        Number of connections notified (0 if WebSocket unavailable)

    Examples:
        await emit_event("task_created", task=task_data)
        await emit_event("submission_received", submission=sub, task=task)
        await emit_event("notification", user_id="...", title="...", message="...")
    """
    return await events.emit(event_name, **kwargs)


def is_websocket_available() -> bool:
    """Check if WebSocket functionality is available."""
    return events.available


# ============== EXPORTS ==============


__all__ = [
    "EventEmitter",
    "events",
    "emit_event",
    "is_websocket_available",
]
