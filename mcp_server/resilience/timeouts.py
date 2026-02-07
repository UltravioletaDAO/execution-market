"""
Submission and Task Timeout Management (NOW-172)

Handles timeouts for task submissions and completion.
Default 4-hour submission window with configurable extensions.

Key features:
- Configurable timeout periods per task type
- Warning notifications before expiry
- Automatic task reassignment on expiry
- Extension requests for legitimate delays
"""

import logging
import asyncio
from typing import Dict, List, Optional, Callable, Awaitable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class TimeoutType(str, Enum):
    """Types of timeouts in the system."""

    SUBMISSION = "submission"  # Time to submit work after accepting
    REVIEW = "review"  # Time for agent to review submission
    DISPUTE = "dispute"  # Time to respond to dispute
    EXTENSION = "extension"  # Extension request validity
    PAYMENT = "payment"  # Payment processing timeout


class TimeoutExpired(Exception):
    """Raised when a timeout has expired."""

    def __init__(self, task_id: str, timeout_type: TimeoutType, expired_at: datetime):
        self.task_id = task_id
        self.timeout_type = timeout_type
        self.expired_at = expired_at
        super().__init__(
            f"Timeout expired for task {task_id}. "
            f"Type: {timeout_type.value}, Expired: {expired_at}"
        )


class TimeoutWarning(Exception):
    """Raised when a timeout warning threshold is reached."""

    def __init__(
        self, task_id: str, timeout_type: TimeoutType, time_remaining: timedelta
    ):
        self.task_id = task_id
        self.timeout_type = timeout_type
        self.time_remaining = time_remaining
        super().__init__(
            f"Timeout warning for task {task_id}. "
            f"Type: {timeout_type.value}, Remaining: {time_remaining}"
        )


@dataclass
class TimeoutConfig:
    """
    Configuration for timeout handling.

    Attributes:
        submission_hours: Hours allowed to submit work (default 4)
        review_hours: Hours for agent review (default 24)
        dispute_hours: Hours to respond to dispute (default 48)
        extension_max_hours: Maximum extension allowed (default 12)
        warning_thresholds: List of warning thresholds (hours before expiry)
        auto_extend_on_progress: Auto-extend if worker shows progress
        max_extensions: Maximum number of extensions allowed
    """

    submission_hours: float = 4.0
    review_hours: float = 24.0
    dispute_hours: float = 48.0
    extension_max_hours: float = 12.0
    warning_thresholds: List[float] = field(
        default_factory=lambda: [1.0, 0.5, 0.25]  # 1hr, 30min, 15min
    )
    auto_extend_on_progress: bool = True
    max_extensions: int = 2


@dataclass
class TaskTimeout:
    """
    Tracks timeout state for a single task.

    Attributes:
        task_id: Task identifier
        timeout_type: Type of timeout being tracked
        started_at: When timeout started
        expires_at: When timeout expires
        warning_sent: List of warning thresholds already sent
        extensions: Number of extensions granted
        extension_reasons: Reasons for each extension
        metadata: Additional timeout metadata
    """

    task_id: str
    timeout_type: TimeoutType
    started_at: datetime
    expires_at: datetime
    warning_sent: List[float] = field(default_factory=list)
    extensions: int = 0
    extension_reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if timeout has expired."""
        return datetime.utcnow() >= self.expires_at

    def time_remaining(self) -> timedelta:
        """Get time remaining until expiry."""
        remaining = self.expires_at - datetime.utcnow()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    def elapsed(self) -> timedelta:
        """Get time elapsed since start."""
        return datetime.utcnow() - self.started_at

    def progress_pct(self) -> float:
        """Get timeout progress as percentage (0-100)."""
        total = (self.expires_at - self.started_at).total_seconds()
        elapsed = self.elapsed().total_seconds()
        return min(100.0, (elapsed / total) * 100) if total > 0 else 100.0


@dataclass
class ExtensionRequest:
    """Request for timeout extension."""

    task_id: str
    requested_by: str  # worker_id or agent_id
    reason: str
    requested_hours: float
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved: Optional[bool] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None


class TimeoutManager:
    """
    Manages task timeouts and extensions.

    Handles:
    - Starting and tracking timeouts
    - Warning notifications before expiry
    - Extension requests and approvals
    - Automatic actions on expiry

    Example:
        manager = TimeoutManager()
        await manager.start()

        # Start submission timeout
        timeout = await manager.start_timeout(
            task_id="task-123",
            timeout_type=TimeoutType.SUBMISSION,
            worker_id="worker-456"
        )

        # Check status
        remaining = timeout.time_remaining()
        print(f"Time remaining: {remaining}")

        # Request extension
        await manager.request_extension(
            task_id="task-123",
            requested_by="worker-456",
            reason="Traffic delay",
            hours=2.0
        )
    """

    def __init__(self, config: Optional[TimeoutConfig] = None):
        """
        Initialize timeout manager.

        Args:
            config: Timeout configuration (uses defaults if None)
        """
        self.config = config or TimeoutConfig()
        self._timeouts: Dict[str, TaskTimeout] = {}
        self._extension_requests: Dict[str, ExtensionRequest] = {}
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False

        # Callbacks
        self._on_warning: List[Callable[[TaskTimeout, float], Awaitable[None]]] = []
        self._on_expired: List[Callable[[TaskTimeout], Awaitable[None]]] = []
        self._on_extension_requested: List[
            Callable[[ExtensionRequest], Awaitable[None]]
        ] = []

    async def start(self):
        """Start the timeout monitor."""
        if self._running:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_timeouts())
        logger.info("Timeout manager started")

    async def stop(self):
        """Stop the timeout monitor."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Timeout manager stopped")

    def _get_timeout_duration(self, timeout_type: TimeoutType) -> timedelta:
        """Get timeout duration for a type."""
        hours = {
            TimeoutType.SUBMISSION: self.config.submission_hours,
            TimeoutType.REVIEW: self.config.review_hours,
            TimeoutType.DISPUTE: self.config.dispute_hours,
            TimeoutType.EXTENSION: 1.0,  # Extension requests valid for 1 hour
            TimeoutType.PAYMENT: 1.0,  # Payment should complete in 1 hour
        }
        return timedelta(hours=hours.get(timeout_type, 4.0))

    async def start_timeout(
        self,
        task_id: str,
        timeout_type: TimeoutType,
        worker_id: Optional[str] = None,
        custom_duration: Optional[timedelta] = None,
        metadata: Optional[Dict] = None,
    ) -> TaskTimeout:
        """
        Start a new timeout for a task.

        Args:
            task_id: Task identifier
            timeout_type: Type of timeout
            worker_id: Optional worker ID for context
            custom_duration: Override default duration
            metadata: Additional metadata

        Returns:
            Created TaskTimeout
        """
        now = datetime.utcnow()
        duration = custom_duration or self._get_timeout_duration(timeout_type)

        timeout = TaskTimeout(
            task_id=task_id,
            timeout_type=timeout_type,
            started_at=now,
            expires_at=now + duration,
            metadata={"worker_id": worker_id, **(metadata or {})},
        )

        # Use composite key for different timeout types on same task
        key = f"{task_id}:{timeout_type.value}"
        self._timeouts[key] = timeout

        logger.info(
            f"Timeout started: {task_id}, type: {timeout_type.value}, "
            f"expires: {timeout.expires_at}"
        )

        return timeout

    async def cancel_timeout(
        self, task_id: str, timeout_type: TimeoutType
    ) -> Optional[TaskTimeout]:
        """
        Cancel an active timeout.

        Args:
            task_id: Task identifier
            timeout_type: Type of timeout to cancel

        Returns:
            Cancelled timeout or None
        """
        key = f"{task_id}:{timeout_type.value}"
        timeout = self._timeouts.pop(key, None)

        if timeout:
            logger.info(f"Timeout cancelled: {task_id}, type: {timeout_type.value}")

        return timeout

    async def extend_timeout(
        self, task_id: str, timeout_type: TimeoutType, hours: float, reason: str
    ) -> Optional[TaskTimeout]:
        """
        Extend an active timeout.

        Args:
            task_id: Task identifier
            timeout_type: Type of timeout
            hours: Hours to extend
            reason: Reason for extension

        Returns:
            Extended timeout or None if not found or max extensions reached
        """
        key = f"{task_id}:{timeout_type.value}"
        timeout = self._timeouts.get(key)

        if not timeout:
            logger.warning(f"Timeout not found for extension: {task_id}")
            return None

        if timeout.extensions >= self.config.max_extensions:
            logger.warning(
                f"Max extensions reached for {task_id}: "
                f"{timeout.extensions}/{self.config.max_extensions}"
            )
            return None

        # Cap extension to max allowed
        hours = min(hours, self.config.extension_max_hours)
        extension = timedelta(hours=hours)

        timeout.expires_at += extension
        timeout.extensions += 1
        timeout.extension_reasons.append(reason)

        logger.info(
            f"Timeout extended: {task_id}, +{hours}h, new expiry: {timeout.expires_at}"
        )

        return timeout

    async def request_extension(
        self, task_id: str, requested_by: str, reason: str, hours: float
    ) -> ExtensionRequest:
        """
        Request a timeout extension.

        Args:
            task_id: Task identifier
            requested_by: ID of requester (worker or agent)
            reason: Reason for extension
            hours: Hours requested

        Returns:
            Created ExtensionRequest
        """
        # Cap to max allowed
        hours = min(hours, self.config.extension_max_hours)

        request = ExtensionRequest(
            task_id=task_id,
            requested_by=requested_by,
            reason=reason,
            requested_hours=hours,
        )

        self._extension_requests[task_id] = request

        logger.info(
            f"Extension requested: {task_id}, by: {requested_by}, "
            f"hours: {hours}, reason: {reason}"
        )

        # Fire callbacks
        for callback in self._on_extension_requested:
            try:
                await callback(request)
            except Exception as e:
                logger.error(f"Extension request callback error: {e}")

        return request

    async def approve_extension(
        self, task_id: str, approved_by: str, approved_hours: Optional[float] = None
    ) -> Optional[TaskTimeout]:
        """
        Approve a pending extension request.

        Args:
            task_id: Task identifier
            approved_by: ID of approver
            approved_hours: Hours to grant (default: requested amount)

        Returns:
            Extended timeout or None
        """
        request = self._extension_requests.get(task_id)
        if not request:
            logger.warning(f"No extension request found: {task_id}")
            return None

        hours = approved_hours or request.requested_hours
        request.approved = True
        request.approved_at = datetime.utcnow()
        request.approved_by = approved_by

        # Find and extend the submission timeout
        timeout = await self.extend_timeout(
            task_id=task_id,
            timeout_type=TimeoutType.SUBMISSION,
            hours=hours,
            reason=f"Extension approved: {request.reason}",
        )

        if timeout:
            logger.info(
                f"Extension approved: {task_id}, by: {approved_by}, hours: {hours}"
            )

        return timeout

    async def deny_extension(
        self, task_id: str, denied_by: str, reason: Optional[str] = None
    ) -> Optional[ExtensionRequest]:
        """
        Deny a pending extension request.

        Args:
            task_id: Task identifier
            denied_by: ID of denier
            reason: Optional denial reason

        Returns:
            Denied request or None
        """
        request = self._extension_requests.get(task_id)
        if not request:
            return None

        request.approved = False
        request.approved_at = datetime.utcnow()
        request.approved_by = denied_by

        logger.info(f"Extension denied: {task_id}, by: {denied_by}, reason: {reason}")

        return request

    def get_timeout(
        self, task_id: str, timeout_type: TimeoutType
    ) -> Optional[TaskTimeout]:
        """Get active timeout for a task."""
        key = f"{task_id}:{timeout_type.value}"
        return self._timeouts.get(key)

    def get_all_timeouts(self, task_id: str) -> List[TaskTimeout]:
        """Get all active timeouts for a task."""
        prefix = f"{task_id}:"
        return [
            timeout for key, timeout in self._timeouts.items() if key.startswith(prefix)
        ]

    def get_expiring_soon(self, within_hours: float = 1.0) -> List[TaskTimeout]:
        """Get timeouts expiring within specified hours."""
        threshold = datetime.utcnow() + timedelta(hours=within_hours)
        return [
            timeout
            for timeout in self._timeouts.values()
            if timeout.expires_at <= threshold and not timeout.is_expired()
        ]

    def get_expired(self) -> List[TaskTimeout]:
        """Get all expired timeouts (not yet processed)."""
        return [timeout for timeout in self._timeouts.values() if timeout.is_expired()]

    # Callback registration

    def on_warning(self, callback: Callable[[TaskTimeout, float], Awaitable[None]]):
        """Register callback for timeout warnings."""
        self._on_warning.append(callback)

    def on_expired(self, callback: Callable[[TaskTimeout], Awaitable[None]]):
        """Register callback for timeout expiry."""
        self._on_expired.append(callback)

    def on_extension_requested(
        self, callback: Callable[[ExtensionRequest], Awaitable[None]]
    ):
        """Register callback for extension requests."""
        self._on_extension_requested.append(callback)

    # Internal monitoring

    async def _monitor_timeouts(self):
        """Background task to monitor timeouts."""
        while self._running:
            try:
                await self._check_timeouts()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Timeout monitor error: {e}")
                await asyncio.sleep(5)

    async def _check_timeouts(self):
        """Check all timeouts for warnings and expiries."""
        datetime.utcnow()

        for key, timeout in list(self._timeouts.items()):
            # Check for expiry
            if timeout.is_expired():
                logger.warning(
                    f"Timeout expired: {timeout.task_id}, "
                    f"type: {timeout.timeout_type.value}"
                )

                # Fire expiry callbacks
                for callback in self._on_expired:
                    try:
                        await callback(timeout)
                    except Exception as e:
                        logger.error(f"Expiry callback error: {e}")

                # Remove expired timeout
                self._timeouts.pop(key, None)
                continue

            # Check for warnings
            remaining_hours = timeout.time_remaining().total_seconds() / 3600

            for threshold in self.config.warning_thresholds:
                if (
                    remaining_hours <= threshold
                    and threshold not in timeout.warning_sent
                ):
                    timeout.warning_sent.append(threshold)

                    logger.info(
                        f"Timeout warning: {timeout.task_id}, "
                        f"type: {timeout.timeout_type.value}, "
                        f"remaining: {remaining_hours:.2f}h"
                    )

                    # Fire warning callbacks
                    for callback in self._on_warning:
                        try:
                            await callback(timeout, threshold)
                        except Exception as e:
                            logger.error(f"Warning callback error: {e}")

    # Statistics

    def get_stats(self) -> Dict:
        """Get timeout statistics."""
        by_type = {}
        for timeout_type in TimeoutType:
            by_type[timeout_type.value] = sum(
                1 for t in self._timeouts.values() if t.timeout_type == timeout_type
            )

        expiring_soon = self.get_expiring_soon(within_hours=1.0)
        expired = self.get_expired()

        pending_extensions = sum(
            1 for r in self._extension_requests.values() if r.approved is None
        )

        return {
            "active_timeouts": len(self._timeouts),
            "by_type": by_type,
            "expiring_within_1h": len(expiring_soon),
            "expired_pending": len(expired),
            "pending_extensions": pending_extensions,
            "config": {
                "submission_hours": self.config.submission_hours,
                "review_hours": self.config.review_hours,
                "max_extensions": self.config.max_extensions,
            },
        }
