"""
Network Connectivity Handling (NOW-171)

Grace periods and reconnection logic for unstable networks.
Designed for workers in areas with intermittent connectivity.

Key features:
- 30-minute grace period for disconnections
- Task preservation during offline periods
- Automatic state recovery on reconnection
- Heartbeat-based connection monitoring
"""

import logging
import asyncio
from typing import Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    """Worker connection states."""

    CONNECTED = "connected"  # Active, heartbeat recent
    DISCONNECTED = "disconnected"  # No heartbeat, within grace period
    GRACE_PERIOD = "grace_period"  # Explicitly in grace period
    EXPIRED = "expired"  # Grace period ended, tasks reassigned
    RECONNECTING = "reconnecting"  # Attempting to reconnect


class GracePeriodExpired(Exception):
    """Raised when grace period has expired."""

    def __init__(self, worker_id: str, offline_duration: timedelta):
        self.worker_id = worker_id
        self.offline_duration = offline_duration
        super().__init__(
            f"Grace period expired for worker {worker_id}. "
            f"Offline for {offline_duration}"
        )


class ConnectionLost(Exception):
    """Raised when connection is lost."""

    def __init__(self, worker_id: str, last_seen: datetime):
        self.worker_id = worker_id
        self.last_seen = last_seen
        super().__init__(
            f"Connection lost for worker {worker_id}. Last seen: {last_seen}"
        )


@dataclass
class WorkerConnection:
    """
    Tracks connection state for a single worker.

    Attributes:
        worker_id: Unique worker identifier
        last_seen: Last heartbeat timestamp
        state: Current connection state
        grace_until: When grace period expires (if applicable)
        active_tasks: List of task IDs assigned to this worker
        reconnect_attempts: Number of reconnection attempts
        metadata: Additional connection metadata
    """

    worker_id: str
    last_seen: datetime
    state: ConnectionState = ConnectionState.CONNECTED
    grace_until: Optional[datetime] = None
    active_tasks: List[str] = field(default_factory=list)
    reconnect_attempts: int = 0
    metadata: Dict = field(default_factory=dict)

    def is_online(self) -> bool:
        """Check if worker is considered online."""
        return self.state in (ConnectionState.CONNECTED, ConnectionState.RECONNECTING)

    def is_in_grace_period(self) -> bool:
        """Check if worker is in grace period."""
        if self.state != ConnectionState.GRACE_PERIOD:
            return False
        if not self.grace_until:
            return False
        return datetime.now(timezone.utc) < self.grace_until

    def time_until_expiry(self) -> Optional[timedelta]:
        """Get time remaining in grace period."""
        if not self.grace_until:
            return None
        remaining = self.grace_until - datetime.now(timezone.utc)
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    def offline_duration(self) -> timedelta:
        """Get how long worker has been offline."""
        return datetime.now(timezone.utc) - self.last_seen


@dataclass
class ConnectivityConfig:
    """Configuration for connectivity management."""

    # Grace period settings
    grace_period_minutes: int = 30
    heartbeat_interval_seconds: int = 30
    heartbeat_timeout_seconds: int = 90  # 3 missed heartbeats

    # Reconnection settings
    max_reconnect_attempts: int = 5
    reconnect_backoff_base: float = 1.5
    reconnect_max_delay_seconds: int = 300

    # Task handling
    preserve_tasks_during_grace: bool = True
    auto_reassign_on_expiry: bool = True
    notify_on_disconnection: bool = True
    notify_on_reconnection: bool = True


class ConnectivityManager:
    """
    Manages worker connections with grace period support.

    Handles:
    - Heartbeat tracking and connection state
    - Grace periods for disconnected workers
    - Task preservation during offline periods
    - Automatic task reassignment on expiry
    - Reconnection coordination

    Example:
        manager = ConnectivityManager()

        # Register worker
        await manager.register_worker("worker-123")

        # Record heartbeat
        await manager.heartbeat("worker-123")

        # Check if worker can accept tasks
        if manager.can_accept_tasks("worker-123"):
            await assign_task(...)

        # Handle disconnection gracefully
        connection = await manager.handle_disconnection("worker-123")
        if connection.is_in_grace_period():
            # Tasks preserved, wait for reconnection
            pass
    """

    def __init__(self, config: Optional[ConnectivityConfig] = None):
        """
        Initialize connectivity manager.

        Args:
            config: Connectivity configuration (uses defaults if None)
        """
        self.config = config or ConnectivityConfig()
        self._connections: Dict[str, WorkerConnection] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

        # Callbacks
        self._on_disconnection: List[Callable[[WorkerConnection], Awaitable[None]]] = []
        self._on_reconnection: List[Callable[[WorkerConnection], Awaitable[None]]] = []
        self._on_grace_expired: List[Callable[[WorkerConnection], Awaitable[None]]] = []

    async def start(self):
        """Start the connectivity monitor."""
        if self._running:
            return

        self._running = True
        self._heartbeat_task = asyncio.create_task(self._monitor_heartbeats())
        logger.info("Connectivity manager started")

    async def stop(self):
        """Stop the connectivity monitor."""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info("Connectivity manager stopped")

    async def register_worker(
        self, worker_id: str, metadata: Optional[Dict] = None
    ) -> WorkerConnection:
        """
        Register a new worker.

        Args:
            worker_id: Worker identifier
            metadata: Optional connection metadata

        Returns:
            WorkerConnection object
        """
        connection = WorkerConnection(
            worker_id=worker_id,
            last_seen=datetime.now(timezone.utc),
            state=ConnectionState.CONNECTED,
            metadata=metadata or {},
        )
        self._connections[worker_id] = connection

        logger.info(f"Worker registered: {worker_id}")
        return connection

    async def unregister_worker(self, worker_id: str) -> Optional[WorkerConnection]:
        """
        Unregister a worker.

        Args:
            worker_id: Worker identifier

        Returns:
            Removed connection or None
        """
        connection = self._connections.pop(worker_id, None)
        if connection:
            logger.info(f"Worker unregistered: {worker_id}")
        return connection

    async def heartbeat(
        self, worker_id: str, metadata: Optional[Dict] = None
    ) -> WorkerConnection:
        """
        Record a heartbeat from a worker.

        Args:
            worker_id: Worker identifier
            metadata: Optional updated metadata

        Returns:
            Updated WorkerConnection

        Raises:
            KeyError: If worker not registered
        """
        connection = self._connections.get(worker_id)
        if not connection:
            # Auto-register if not found
            connection = await self.register_worker(worker_id, metadata)

        now = datetime.now(timezone.utc)
        was_disconnected = connection.state in (
            ConnectionState.DISCONNECTED,
            ConnectionState.GRACE_PERIOD,
        )

        connection.last_seen = now
        connection.reconnect_attempts = 0

        if was_disconnected:
            # Handle reconnection
            connection.state = ConnectionState.CONNECTED
            connection.grace_until = None

            logger.info(
                f"Worker reconnected: {worker_id} "
                f"(was offline for {connection.offline_duration()})"
            )

            # Fire reconnection callbacks
            if self.config.notify_on_reconnection:
                for callback in self._on_reconnection:
                    try:
                        await callback(connection)
                    except Exception as e:
                        logger.error(f"Reconnection callback error: {e}")
        else:
            connection.state = ConnectionState.CONNECTED

        if metadata:
            connection.metadata.update(metadata)

        return connection

    async def handle_disconnection(
        self, worker_id: str, reason: Optional[str] = None
    ) -> WorkerConnection:
        """
        Handle worker disconnection.

        Starts grace period and preserves tasks.

        Args:
            worker_id: Worker identifier
            reason: Optional disconnection reason

        Returns:
            Updated WorkerConnection

        Raises:
            KeyError: If worker not registered
        """
        connection = self._connections.get(worker_id)
        if not connection:
            raise KeyError(f"Worker not found: {worker_id}")

        if connection.state == ConnectionState.CONNECTED:
            connection.state = ConnectionState.GRACE_PERIOD
            connection.grace_until = datetime.now(timezone.utc) + timedelta(
                minutes=self.config.grace_period_minutes
            )

            logger.warning(
                f"Worker disconnected: {worker_id}, reason: {reason}. "
                f"Grace period until {connection.grace_until}"
            )

            # Fire disconnection callbacks
            if self.config.notify_on_disconnection:
                for callback in self._on_disconnection:
                    try:
                        await callback(connection)
                    except Exception as e:
                        logger.error(f"Disconnection callback error: {e}")

        return connection

    async def expire_grace_period(self, worker_id: str) -> WorkerConnection:
        """
        Expire a worker's grace period.

        Called when grace period ends without reconnection.

        Args:
            worker_id: Worker identifier

        Returns:
            Updated WorkerConnection
        """
        connection = self._connections.get(worker_id)
        if not connection:
            raise KeyError(f"Worker not found: {worker_id}")

        tasks_to_reassign = connection.active_tasks.copy()
        connection.state = ConnectionState.EXPIRED
        connection.grace_until = None

        logger.warning(
            f"Grace period expired: {worker_id}. "
            f"Tasks to reassign: {len(tasks_to_reassign)}"
        )

        # Fire expiry callbacks
        for callback in self._on_grace_expired:
            try:
                await callback(connection)
            except Exception as e:
                logger.error(f"Grace expiry callback error: {e}")

        return connection

    def get_connection(self, worker_id: str) -> Optional[WorkerConnection]:
        """Get worker connection by ID."""
        return self._connections.get(worker_id)

    def can_accept_tasks(self, worker_id: str) -> bool:
        """
        Check if worker can accept new tasks.

        Workers can accept tasks if:
        - They are connected
        - They are in grace period (tasks queued for when they reconnect)
        """
        connection = self._connections.get(worker_id)
        if not connection:
            return False

        return connection.state in (
            ConnectionState.CONNECTED,
            ConnectionState.GRACE_PERIOD,
        )

    def assign_task(self, worker_id: str, task_id: str) -> bool:
        """
        Assign a task to a worker.

        Args:
            worker_id: Worker identifier
            task_id: Task identifier

        Returns:
            True if assigned, False if worker can't accept tasks
        """
        connection = self._connections.get(worker_id)
        if not connection or not self.can_accept_tasks(worker_id):
            return False

        if task_id not in connection.active_tasks:
            connection.active_tasks.append(task_id)

        return True

    def unassign_task(self, worker_id: str, task_id: str) -> bool:
        """
        Remove a task from a worker.

        Args:
            worker_id: Worker identifier
            task_id: Task identifier

        Returns:
            True if removed, False if not found
        """
        connection = self._connections.get(worker_id)
        if not connection:
            return False

        if task_id in connection.active_tasks:
            connection.active_tasks.remove(task_id)
            return True
        return False

    def get_workers_in_grace_period(self) -> List[WorkerConnection]:
        """Get all workers currently in grace period."""
        return [
            conn
            for conn in self._connections.values()
            if conn.state == ConnectionState.GRACE_PERIOD
        ]

    def get_online_workers(self) -> List[WorkerConnection]:
        """Get all online workers."""
        return [conn for conn in self._connections.values() if conn.is_online()]

    def get_expired_workers(self) -> List[WorkerConnection]:
        """Get all workers with expired grace periods."""
        return [
            conn
            for conn in self._connections.values()
            if conn.state == ConnectionState.EXPIRED
        ]

    # Callback registration

    def on_disconnection(self, callback: Callable[[WorkerConnection], Awaitable[None]]):
        """Register callback for worker disconnection."""
        self._on_disconnection.append(callback)

    def on_reconnection(self, callback: Callable[[WorkerConnection], Awaitable[None]]):
        """Register callback for worker reconnection."""
        self._on_reconnection.append(callback)

    def on_grace_expired(self, callback: Callable[[WorkerConnection], Awaitable[None]]):
        """Register callback for grace period expiry."""
        self._on_grace_expired.append(callback)

    # Internal monitoring

    async def _monitor_heartbeats(self):
        """Background task to monitor heartbeats and grace periods."""
        while self._running:
            try:
                await self._check_connections()
                await asyncio.sleep(self.config.heartbeat_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")
                await asyncio.sleep(5)

    async def _check_connections(self):
        """Check all connections for timeouts and expiries."""
        now = datetime.now(timezone.utc)
        timeout = timedelta(seconds=self.config.heartbeat_timeout_seconds)

        for worker_id, connection in list(self._connections.items()):
            # Check for heartbeat timeout
            if connection.state == ConnectionState.CONNECTED:
                if now - connection.last_seen > timeout:
                    await self.handle_disconnection(
                        worker_id, reason="heartbeat_timeout"
                    )

            # Check for grace period expiry
            elif connection.state == ConnectionState.GRACE_PERIOD:
                if connection.grace_until and now >= connection.grace_until:
                    await self.expire_grace_period(worker_id)

    # Statistics

    def get_stats(self) -> Dict:
        """Get connectivity statistics."""
        states = {}
        for state in ConnectionState:
            states[state.value] = sum(
                1 for c in self._connections.values() if c.state == state
            )

        total_tasks = sum(len(c.active_tasks) for c in self._connections.values())

        grace_period_workers = self.get_workers_in_grace_period()
        tasks_at_risk = sum(len(c.active_tasks) for c in grace_period_workers)

        return {
            "total_workers": len(self._connections),
            "states": states,
            "total_active_tasks": total_tasks,
            "workers_in_grace_period": len(grace_period_workers),
            "tasks_at_risk": tasks_at_risk,
            "config": {
                "grace_period_minutes": self.config.grace_period_minutes,
                "heartbeat_timeout_seconds": self.config.heartbeat_timeout_seconds,
            },
        }
