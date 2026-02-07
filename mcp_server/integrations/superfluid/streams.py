"""
Stream Manager for Execution Market Tasks

High-level stream management for long-running tasks.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .client import SuperfluidClient

logger = logging.getLogger(__name__)


class StreamStatus(str, Enum):
    """Status of a task stream."""

    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class TaskStream:
    """Stream associated with a task."""

    task_id: str
    executor_id: str
    executor_wallet: str
    hourly_rate_usd: float
    flow_rate_wei: int
    status: StreamStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_streamed_usd: float = 0.0
    tx_hashes: List[str] = field(default_factory=list)


class StreamManager:
    """
    Manages payment streams for Execution Market tasks.

    Features:
    - Create streams for long-running tasks
    - Pause/resume based on verification
    - Track total streamed amounts
    - Auto-complete when task finishes
    """

    # Default hourly rate
    DEFAULT_HOURLY_RATE = 18.0  # $18/hr

    # Verification interval for live tasks
    VERIFICATION_INTERVAL_MINUTES = 15

    def __init__(
        self, client: Optional[SuperfluidClient] = None, network: str = "base"
    ):
        """
        Initialize stream manager.

        Args:
            client: Superfluid client (or creates new)
            network: Network name
        """
        self.client = client or SuperfluidClient(network=network)
        self._active_streams: Dict[str, TaskStream] = {}

    async def create_task_stream(
        self,
        task_id: str,
        executor_id: str,
        executor_wallet: str,
        hourly_rate_usd: float = DEFAULT_HOURLY_RATE,
        auto_start: bool = True,
    ) -> TaskStream:
        """
        Create a stream for a task.

        Args:
            task_id: Task identifier
            executor_id: Worker's executor ID
            executor_wallet: Worker's wallet address
            hourly_rate_usd: Hourly rate in USD
            auto_start: Start stream immediately

        Returns:
            TaskStream
        """
        flow_rate = self.client.calculate_flow_rate(hourly_rate_usd)

        stream = TaskStream(
            task_id=task_id,
            executor_id=executor_id,
            executor_wallet=executor_wallet,
            hourly_rate_usd=hourly_rate_usd,
            flow_rate_wei=flow_rate,
            status=StreamStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        if auto_start:
            tx_hash = await self.client.create_stream(
                receiver=executor_wallet, flow_rate=flow_rate, task_id=task_id
            )

            if tx_hash:
                stream.status = StreamStatus.ACTIVE
                stream.started_at = datetime.utcnow()
                stream.tx_hashes.append(tx_hash)
                logger.info(f"Stream started for task {task_id}: ${hourly_rate_usd}/hr")
            else:
                logger.error(f"Failed to start stream for task {task_id}")

        self._active_streams[task_id] = stream
        return stream

    async def pause_stream(self, task_id: str, reason: str = "verification") -> bool:
        """
        Pause a task's stream.

        Args:
            task_id: Task identifier
            reason: Reason for pause

        Returns:
            True if paused successfully
        """
        stream = self._active_streams.get(task_id)
        if not stream or stream.status != StreamStatus.ACTIVE:
            return False

        tx_hash = await self.client.pause_stream(stream.executor_wallet)

        if tx_hash:
            # Calculate streamed amount before pause
            if stream.started_at:
                elapsed_hours = (
                    datetime.utcnow() - stream.started_at
                ).total_seconds() / 3600
                stream.total_streamed_usd += elapsed_hours * stream.hourly_rate_usd

            stream.status = StreamStatus.PAUSED
            stream.paused_at = datetime.utcnow()
            stream.tx_hashes.append(tx_hash)

            logger.info(f"Stream paused for task {task_id}: {reason}")
            return True

        return False

    async def resume_stream(self, task_id: str) -> bool:
        """
        Resume a paused stream.

        Args:
            task_id: Task identifier

        Returns:
            True if resumed successfully
        """
        stream = self._active_streams.get(task_id)
        if not stream or stream.status != StreamStatus.PAUSED:
            return False

        tx_hash = await self.client.resume_stream(
            receiver=stream.executor_wallet, flow_rate=stream.flow_rate_wei
        )

        if tx_hash:
            stream.status = StreamStatus.ACTIVE
            stream.started_at = datetime.utcnow()  # Reset start for tracking
            stream.paused_at = None
            stream.tx_hashes.append(tx_hash)

            logger.info(f"Stream resumed for task {task_id}")
            return True

        return False

    async def complete_stream(self, task_id: str) -> TaskStream:
        """
        Complete and finalize a task's stream.

        Args:
            task_id: Task identifier

        Returns:
            Final TaskStream with total amounts
        """
        stream = self._active_streams.get(task_id)
        if not stream:
            raise ValueError(f"No stream found for task {task_id}")

        # Stop the stream if active
        if stream.status == StreamStatus.ACTIVE:
            tx_hash = await self.client.delete_stream(stream.executor_wallet)
            if tx_hash:
                stream.tx_hashes.append(tx_hash)

        # Calculate final streamed amount
        if stream.started_at and stream.status == StreamStatus.ACTIVE:
            elapsed_hours = (
                datetime.utcnow() - stream.started_at
            ).total_seconds() / 3600
            stream.total_streamed_usd += elapsed_hours * stream.hourly_rate_usd

        stream.status = StreamStatus.COMPLETED
        stream.completed_at = datetime.utcnow()

        logger.info(
            f"Stream completed for task {task_id}: "
            f"total ${stream.total_streamed_usd:.2f}"
        )

        return stream

    async def cancel_stream(self, task_id: str, reason: str) -> bool:
        """
        Cancel a stream without completion.

        Args:
            task_id: Task identifier
            reason: Cancellation reason

        Returns:
            True if cancelled
        """
        stream = self._active_streams.get(task_id)
        if not stream:
            return False

        if stream.status == StreamStatus.ACTIVE:
            await self.client.delete_stream(stream.executor_wallet)

        stream.status = StreamStatus.CANCELLED
        logger.info(f"Stream cancelled for task {task_id}: {reason}")

        return True

    async def get_stream_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a task's stream.

        Args:
            task_id: Task identifier

        Returns:
            Status dict or None
        """
        stream = self._active_streams.get(task_id)
        if not stream:
            return None

        # Get live info from chain
        chain_info = await self.client.get_stream_info(
            sender=self.client.account.address if self.client.account else "",
            receiver=stream.executor_wallet,
        )

        current_streamed = stream.total_streamed_usd
        if stream.status == StreamStatus.ACTIVE and stream.started_at:
            elapsed_hours = (
                datetime.utcnow() - stream.started_at
            ).total_seconds() / 3600
            current_streamed += elapsed_hours * stream.hourly_rate_usd

        return {
            "task_id": task_id,
            "status": stream.status.value,
            "executor_wallet": stream.executor_wallet,
            "hourly_rate_usd": stream.hourly_rate_usd,
            "total_streamed_usd": round(current_streamed, 4),
            "started_at": stream.started_at.isoformat() if stream.started_at else None,
            "chain_active": chain_info is not None and chain_info.is_active
            if chain_info
            else False,
        }

    async def verify_and_adjust(self, task_id: str, verification_score: float) -> str:
        """
        Verify task progress and adjust stream accordingly.

        Called periodically for live verification.

        Args:
            task_id: Task identifier
            verification_score: 0-1 verification confidence

        Returns:
            Action taken
        """
        stream = self._active_streams.get(task_id)
        if not stream:
            return "no_stream"

        # High confidence - continue streaming
        if verification_score >= 0.8:
            if stream.status == StreamStatus.PAUSED:
                await self.resume_stream(task_id)
                return "resumed"
            return "continue"

        # Low confidence - pause for manual review
        if verification_score < 0.5:
            if stream.status == StreamStatus.ACTIVE:
                await self.pause_stream(task_id, "low_verification_score")
                return "paused"
            return "already_paused"

        # Medium confidence - reduce rate temporarily
        if 0.5 <= verification_score < 0.8:
            # Could implement rate reduction here
            return "monitoring"

        return "no_action"

    def get_active_streams(self) -> List[TaskStream]:
        """Get all active streams."""
        return [
            s for s in self._active_streams.values() if s.status == StreamStatus.ACTIVE
        ]

    def calculate_total_outflow(self) -> float:
        """Calculate total USD/hour being streamed."""
        return sum(
            s.hourly_rate_usd
            for s in self._active_streams.values()
            if s.status == StreamStatus.ACTIVE
        )
