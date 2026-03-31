"""
FleetLifecycleBridge — Bidirectional sync between FleetManager and LifecycleManager
====================================================================================

Module #54 in the KK V2 Swarm.

Two systems manage agents independently:
- **LifecycleManager**: State machine + budgets + health heartbeats
- **FleetManager**: Capabilities + availability + load balancing + fleet metrics

This bridge keeps them in sync without coupling them. Neither system knows about
the other directly — the bridge observes events and propagates state changes.

Architecture:

    ┌─────────────────┐         ┌───────────────────┐
    │ LifecycleManager │◄──────►│   FleetManager     │
    │                  │        │                    │
    │  State machine   │  ┌──►  │  Capabilities      │
    │  Budgets         │  │     │  Load balancing    │
    │  Heartbeats      │  │     │  Availability      │
    └────────┬─────────┘  │     └────────┬───────────┘
             │            │              │
             └──────┬─────┘──────────────┘
                    │
           ┌────────▼────────┐
           │ FleetLifecycle  │
           │    Bridge       │
           │                 │
           │ • State sync    │
           │ • Health sync   │
           │ • Budget gates  │
           │ • Unified query │
           │ • Audit trail   │
           └─────────────────┘

Sync rules:
    1. LifecycleManager state → FleetManager status (WORKING→BUSY, IDLE→ACTIVE, etc.)
    2. FleetManager heartbeat timeout → LifecycleManager degraded state
    3. Budget exceeded → FleetManager SUSPENDED status
    4. Cooldown completion → Both systems updated atomically
    5. Task assignment/completion → Both systems notified

Usage:
    bridge = FleetLifecycleBridge(lifecycle_manager, fleet_manager)

    # Sync lifecycle state change to fleet
    bridge.sync_state_change(agent_id=2106, new_state=AgentState.WORKING)

    # Sync fleet heartbeat timeout to lifecycle
    bridge.sync_heartbeat_timeout(agent_id=2106)

    # Unified agent view
    view = bridge.get_unified_view(agent_id=2106)

    # Full fleet reconciliation
    report = bridge.reconcile()
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger("em.swarm.fleet_lifecycle_bridge")


# ──────────────────────────────────────────────────────────────
# State Mapping
# ──────────────────────────────────────────────────────────────


class SyncDirection(str, Enum):
    """Direction of a sync event."""

    LIFECYCLE_TO_FLEET = "lifecycle_to_fleet"
    FLEET_TO_LIFECYCLE = "fleet_to_lifecycle"
    BIDIRECTIONAL = "bidirectional"


class SyncEventType(str, Enum):
    """Types of synchronization events."""

    STATE_CHANGE = "state_change"
    HEARTBEAT_TIMEOUT = "heartbeat_timeout"
    HEARTBEAT_RECOVERY = "heartbeat_recovery"
    BUDGET_EXCEEDED = "budget_exceeded"
    BUDGET_RECOVERED = "budget_recovered"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    COOLDOWN_STARTED = "cooldown_started"
    COOLDOWN_EXPIRED = "cooldown_expired"
    AGENT_REGISTERED = "agent_registered"
    AGENT_DEREGISTERED = "agent_deregistered"
    RECONCILIATION = "reconciliation"
    CONFLICT_RESOLVED = "conflict_resolved"


@dataclass
class SyncEvent:
    """Record of a synchronization action."""

    event_type: SyncEventType
    direction: SyncDirection
    agent_id: int
    timestamp: float = field(default_factory=time.time)
    details: dict = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "direction": self.direction.value,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "details": self.details,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class UnifiedAgentView:
    """Combined view of an agent from both systems."""

    agent_id: int
    # From LifecycleManager
    lifecycle_state: Optional[str] = None
    current_task_id: Optional[str] = None
    budget_daily_spent: float = 0.0
    budget_monthly_spent: float = 0.0
    budget_daily_limit: float = 0.0
    budget_at_warning: bool = False
    budget_at_limit: bool = False
    health_heartbeat_ok: bool = True
    health_consecutive_missed: int = 0
    cooldown_until: Optional[datetime] = None
    error_count: int = 0
    # From FleetManager
    fleet_status: Optional[str] = None
    capabilities: list[str] = field(default_factory=list)
    capability_scores: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    current_load: int = 0
    max_concurrent: int = 1
    utilization: float = 0.0
    total_completed: int = 0
    total_failed: int = 0
    # Sync metadata
    in_sync: bool = True
    conflicts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "lifecycle": {
                "state": self.lifecycle_state,
                "current_task": self.current_task_id,
                "budget": {
                    "daily_spent": self.budget_daily_spent,
                    "monthly_spent": self.budget_monthly_spent,
                    "daily_limit": self.budget_daily_limit,
                    "at_warning": self.budget_at_warning,
                    "at_limit": self.budget_at_limit,
                },
                "health": {
                    "heartbeat_ok": self.health_heartbeat_ok,
                    "consecutive_missed": self.health_consecutive_missed,
                },
                "cooldown_until": (
                    self.cooldown_until.isoformat() if self.cooldown_until else None
                ),
                "error_count": self.error_count,
            },
            "fleet": {
                "status": self.fleet_status,
                "capabilities": self.capabilities,
                "capability_scores": self.capability_scores,
                "tags": self.tags,
                "load": f"{self.current_load}/{self.max_concurrent}",
                "utilization": round(self.utilization, 3),
                "completed": self.total_completed,
                "failed": self.total_failed,
            },
            "sync": {
                "in_sync": self.in_sync,
                "conflicts": self.conflicts,
            },
        }


@dataclass
class ReconciliationReport:
    """Result of a full fleet reconciliation."""

    timestamp: float = field(default_factory=time.time)
    agents_checked: int = 0
    agents_in_sync: int = 0
    agents_out_of_sync: int = 0
    conflicts_found: int = 0
    conflicts_resolved: int = 0
    sync_events: list = field(default_factory=list)
    lifecycle_only: list = field(default_factory=list)
    fleet_only: list = field(default_factory=list)

    @property
    def all_in_sync(self) -> bool:
        return self.agents_out_of_sync == 0

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "agents_checked": self.agents_checked,
            "agents_in_sync": self.agents_in_sync,
            "agents_out_of_sync": self.agents_out_of_sync,
            "conflicts_found": self.conflicts_found,
            "conflicts_resolved": self.conflicts_resolved,
            "all_in_sync": self.all_in_sync,
            "sync_events": [e.to_dict() for e in self.sync_events],
            "lifecycle_only": self.lifecycle_only,
            "fleet_only": self.fleet_only,
        }


# ──────────────────────────────────────────────────────────────
# State Mapping Tables
# ──────────────────────────────────────────────────────────────

# LifecycleManager AgentState → FleetManager AgentStatus
# These are string-based to avoid hard imports; duck-typed resolution
LIFECYCLE_TO_FLEET_STATUS = {
    "initializing": "offline",
    "idle": "active",
    "active": "active",
    "working": "busy",
    "cooldown": "cooldown",
    "degraded": "idle",  # Degraded agents shouldn't get new tasks
    "suspended": "suspended",
}

# FleetManager AgentStatus → LifecycleManager AgentState
# Reverse mapping for fleet→lifecycle sync
FLEET_TO_LIFECYCLE_STATE = {
    "active": "idle",  # Fleet ACTIVE = lifecycle IDLE (ready)
    "busy": "working",
    "idle": "degraded",  # Fleet IDLE = missed heartbeats
    "offline": "suspended",
    "suspended": "suspended",
    "cooldown": "cooldown",
}


# ──────────────────────────────────────────────────────────────
# Bridge
# ──────────────────────────────────────────────────────────────


class FleetLifecycleBridge:
    """
    Bidirectional sync layer between FleetManager and LifecycleManager.

    Keeps both systems consistent without coupling them directly.
    Handles state mapping, conflict resolution, and audit logging.
    """

    def __init__(
        self,
        lifecycle_manager=None,
        fleet_manager=None,
        max_history: int = 200,
        auto_resolve_conflicts: bool = True,
    ):
        self._lifecycle = lifecycle_manager
        self._fleet = fleet_manager
        self._auto_resolve = auto_resolve_conflicts
        self._history: deque = deque(maxlen=max_history)
        self._conflict_count = 0
        self._sync_count = 0
        self._error_count = 0
        self._last_reconciliation: Optional[float] = None
        self._created_at = time.time()

    # ── Component setters (fluent) ────────────────────────────

    def set_lifecycle_manager(self, lm) -> "FleetLifecycleBridge":
        """Set or replace the LifecycleManager."""
        self._lifecycle = lm
        return self

    def set_fleet_manager(self, fm) -> "FleetLifecycleBridge":
        """Set or replace the FleetManager."""
        self._fleet = fm
        return self

    # ── Lifecycle → Fleet sync ────────────────────────────────

    def sync_state_change(self, agent_id: int, new_state: str) -> SyncEvent:
        """
        Propagate a LifecycleManager state change to FleetManager.

        Maps lifecycle states to fleet statuses and updates the fleet.
        """
        new_state_str = (
            new_state.value if hasattr(new_state, "value") else str(new_state)
        )
        fleet_status = LIFECYCLE_TO_FLEET_STATUS.get(new_state_str)

        event = SyncEvent(
            event_type=SyncEventType.STATE_CHANGE,
            direction=SyncDirection.LIFECYCLE_TO_FLEET,
            agent_id=agent_id,
            details={
                "lifecycle_state": new_state_str,
                "fleet_status": fleet_status,
            },
        )

        if fleet_status is None:
            event.success = False
            event.error = (
                f"No fleet status mapping for lifecycle state: {new_state_str}"
            )
            self._record_event(event)
            return event

        if self._fleet is not None:
            try:
                # Resolve fleet status enum
                fleet_status_enum = self._resolve_fleet_status(fleet_status)
                if fleet_status_enum is not None:
                    self._fleet.set_status(agent_id, fleet_status_enum)
                else:
                    event.success = False
                    event.error = f"Could not resolve fleet status: {fleet_status}"
            except Exception as e:
                event.success = False
                event.error = str(e)
                self._error_count += 1
                logger.warning(f"Fleet sync failed for agent {agent_id}: {e}")
        else:
            event.success = False
            event.error = "FleetManager not connected"

        self._record_event(event)
        return event

    def sync_task_assigned(self, agent_id: int, task_id: str) -> SyncEvent:
        """
        Propagate task assignment to both systems.

        - LifecycleManager: assign_task (state → WORKING)
        - FleetManager: record_task_assigned (load++)
        """
        event = SyncEvent(
            event_type=SyncEventType.TASK_ASSIGNED,
            direction=SyncDirection.BIDIRECTIONAL,
            agent_id=agent_id,
            details={"task_id": task_id},
        )

        errors = []

        # Lifecycle side
        if self._lifecycle is not None:
            try:
                self._lifecycle.assign_task(agent_id, task_id)
            except Exception as e:
                errors.append(f"lifecycle: {e}")
                logger.warning(f"Lifecycle assign_task failed for {agent_id}: {e}")

        # Fleet side
        if self._fleet is not None:
            try:
                self._fleet.record_task_assigned(agent_id)
            except Exception as e:
                errors.append(f"fleet: {e}")
                logger.warning(f"Fleet record_task_assigned failed for {agent_id}: {e}")

        if errors:
            event.success = False
            event.error = "; ".join(errors)
            self._error_count += 1

        self._record_event(event)
        return event

    def sync_task_completed(
        self,
        agent_id: int,
        task_id: str,
        success: bool = True,
        cost_usd: float = 0.0,
    ) -> SyncEvent:
        """
        Propagate task completion to both systems.

        - LifecycleManager: complete_task (state → COOLDOWN, budget update)
        - FleetManager: record_task_completed (load--, stats update)
        """
        event = SyncEvent(
            event_type=SyncEventType.TASK_COMPLETED,
            direction=SyncDirection.BIDIRECTIONAL,
            agent_id=agent_id,
            details={
                "task_id": task_id,
                "success": success,
                "cost_usd": cost_usd,
            },
        )

        errors = []

        # Lifecycle side
        if self._lifecycle is not None:
            try:
                self._lifecycle.complete_task(agent_id, task_id, cost_usd=cost_usd)
            except Exception as e:
                errors.append(f"lifecycle: {e}")
                logger.warning(f"Lifecycle complete_task failed for {agent_id}: {e}")

        # Fleet side
        if self._fleet is not None:
            try:
                self._fleet.record_task_completed(agent_id, success=success)
            except Exception as e:
                errors.append(f"fleet: {e}")
                logger.warning(
                    f"Fleet record_task_completed failed for {agent_id}: {e}"
                )

        if errors:
            event.success = False
            event.error = "; ".join(errors)
            self._error_count += 1

        self._record_event(event)
        return event

    def sync_heartbeat(self, agent_id: int) -> SyncEvent:
        """
        Propagate heartbeat to both systems.

        - LifecycleManager: record_heartbeat
        - FleetManager: heartbeat (updates last_seen)
        """
        event = SyncEvent(
            event_type=SyncEventType.HEARTBEAT_RECOVERY,
            direction=SyncDirection.BIDIRECTIONAL,
            agent_id=agent_id,
        )

        errors = []

        if self._lifecycle is not None:
            try:
                self._lifecycle.record_heartbeat(agent_id)
            except Exception as e:
                errors.append(f"lifecycle: {e}")

        if self._fleet is not None:
            try:
                self._fleet.heartbeat(agent_id)
            except Exception as e:
                errors.append(f"fleet: {e}")

        if errors:
            event.success = False
            event.error = "; ".join(errors)
            self._error_count += 1

        self._record_event(event)
        return event

    def sync_heartbeat_timeout(self, agent_id: int) -> SyncEvent:
        """
        Handle heartbeat timeout detected by FleetManager.

        Propagates to LifecycleManager as DEGRADED state.
        """
        event = SyncEvent(
            event_type=SyncEventType.HEARTBEAT_TIMEOUT,
            direction=SyncDirection.FLEET_TO_LIFECYCLE,
            agent_id=agent_id,
        )

        if self._lifecycle is not None:
            try:
                # Check if transition is valid
                agent = self._lifecycle._get_agent(agent_id)
                from .lifecycle_manager import AgentState as LCState, VALID_TRANSITIONS

                if LCState.DEGRADED in VALID_TRANSITIONS.get(agent.state, set()):
                    self._lifecycle.transition(agent_id, LCState.DEGRADED)
                    event.details["previous_state"] = agent.state.value
                    event.details["new_state"] = "degraded"
                else:
                    event.details["skipped"] = True
                    event.details["reason"] = (
                        f"Cannot transition from {agent.state.value} to degraded"
                    )
            except Exception as e:
                event.success = False
                event.error = str(e)
                self._error_count += 1
        else:
            event.success = False
            event.error = "LifecycleManager not connected"

        self._record_event(event)
        return event

    def sync_budget_exceeded(self, agent_id: int) -> SyncEvent:
        """
        Handle budget exceeded from LifecycleManager.

        Propagates SUSPENDED status to FleetManager.
        """
        event = SyncEvent(
            event_type=SyncEventType.BUDGET_EXCEEDED,
            direction=SyncDirection.LIFECYCLE_TO_FLEET,
            agent_id=agent_id,
        )

        if self._fleet is not None:
            try:
                suspended_status = self._resolve_fleet_status("suspended")
                if suspended_status is not None:
                    self._fleet.set_status(agent_id, suspended_status)
            except Exception as e:
                event.success = False
                event.error = str(e)
                self._error_count += 1
        else:
            event.success = False
            event.error = "FleetManager not connected"

        self._record_event(event)
        return event

    def sync_cooldown_started(
        self, agent_id: int, duration_seconds: float = 300.0
    ) -> SyncEvent:
        """
        Handle cooldown start from LifecycleManager.

        Propagates COOLDOWN status to FleetManager.
        """
        event = SyncEvent(
            event_type=SyncEventType.COOLDOWN_STARTED,
            direction=SyncDirection.LIFECYCLE_TO_FLEET,
            agent_id=agent_id,
            details={"duration_seconds": duration_seconds},
        )

        if self._fleet is not None:
            try:
                agent = self._fleet.get_agent(agent_id)
                if agent is not None:
                    agent.enter_cooldown(duration_seconds)
                    event.details["fleet_updated"] = True
                else:
                    event.success = False
                    event.error = f"Agent {agent_id} not in fleet"
            except Exception as e:
                event.success = False
                event.error = str(e)
                self._error_count += 1
        else:
            event.success = False
            event.error = "FleetManager not connected"

        self._record_event(event)
        return event

    def sync_cooldown_expired(self, agent_id: int) -> SyncEvent:
        """
        Handle cooldown expiry — move both systems back to ready state.
        """
        event = SyncEvent(
            event_type=SyncEventType.COOLDOWN_EXPIRED,
            direction=SyncDirection.BIDIRECTIONAL,
            agent_id=agent_id,
        )

        errors = []

        # Fleet side
        if self._fleet is not None:
            try:
                agent = self._fleet.get_agent(agent_id)
                if agent is not None:
                    agent.exit_cooldown()
                    active_status = self._resolve_fleet_status("active")
                    if active_status is not None:
                        self._fleet.set_status(agent_id, active_status)
            except Exception as e:
                errors.append(f"fleet: {e}")

        # Lifecycle side
        if self._lifecycle is not None:
            try:
                result = self._lifecycle.check_cooldown_expiry(agent_id)
                event.details["lifecycle_transitioned"] = result
            except Exception as e:
                errors.append(f"lifecycle: {e}")

        if errors:
            event.success = False
            event.error = "; ".join(errors)
            self._error_count += 1

        self._record_event(event)
        return event

    def sync_agent_registered(
        self,
        agent_id: int,
        name: str,
        wallet_address: str = "",
        capabilities: Optional[list] = None,
        tags: Optional[list] = None,
    ) -> SyncEvent:
        """
        Register an agent in both systems simultaneously.
        """
        event = SyncEvent(
            event_type=SyncEventType.AGENT_REGISTERED,
            direction=SyncDirection.BIDIRECTIONAL,
            agent_id=agent_id,
            details={
                "name": name,
                "capabilities": capabilities or [],
                "tags": tags or [],
            },
        )

        errors = []

        # Lifecycle side
        if self._lifecycle is not None:
            try:
                self._lifecycle.register_agent(
                    agent_id=agent_id,
                    name=name,
                    wallet_address=wallet_address,
                )
            except Exception as e:
                errors.append(f"lifecycle: {e}")

        # Fleet side
        if self._fleet is not None:
            try:
                from .fleet_manager import AgentProfile

                profile = AgentProfile(
                    agent_id=agent_id,
                    name=name,
                )
                self._fleet.register_agent(profile)

                # Add capabilities
                for cap in capabilities or []:
                    try:
                        self._fleet.add_capability(agent_id, cap)
                    except Exception:
                        pass

                # Add tags
                for tag in tags or []:
                    try:
                        self._fleet.add_tag(agent_id, tag)
                    except Exception:
                        pass

            except Exception as e:
                errors.append(f"fleet: {e}")

        if errors:
            event.success = False
            event.error = "; ".join(errors)
            self._error_count += 1

        self._record_event(event)
        return event

    # ── Unified Queries ───────────────────────────────────────

    def get_unified_view(self, agent_id: int) -> UnifiedAgentView:
        """
        Get a combined view of an agent from both systems.

        Detects conflicts where the two systems disagree.
        """
        view = UnifiedAgentView(agent_id=agent_id)

        # Pull from LifecycleManager
        if self._lifecycle is not None:
            try:
                agent = self._lifecycle._get_agent(agent_id)
                view.lifecycle_state = agent.state.value
                view.current_task_id = agent.current_task_id
                view.budget_daily_spent = agent.budget_state.daily_spent_usd
                view.budget_monthly_spent = agent.budget_state.monthly_spent_usd
                view.budget_daily_limit = agent.budget_config.daily_limit_usd
                view.health_heartbeat_ok = agent.health.is_healthy
                view.health_consecutive_missed = agent.health.consecutive_missed
                view.cooldown_until = agent.cooldown_until
                view.error_count = agent.health.error_count
                budget_status = self._lifecycle.get_budget_status(agent_id)
                view.budget_at_warning = budget_status.get("at_warning", False)
                view.budget_at_limit = budget_status.get("at_limit", False)
            except Exception as e:
                view.conflicts.append(f"lifecycle_error: {e}")

        # Pull from FleetManager
        if self._fleet is not None:
            try:
                agent = self._fleet.get_agent(agent_id)
                if agent is not None:
                    view.fleet_status = (
                        agent.status.value
                        if hasattr(agent.status, "value")
                        else str(agent.status)
                    )
                    view.capabilities = (
                        [c.name for c in agent.capabilities]
                        if hasattr(agent, "capabilities") and agent.capabilities
                        else []
                    )
                    view.capability_scores = (
                        {c.name: c.score() for c in agent.capabilities}
                        if hasattr(agent, "capabilities") and agent.capabilities
                        else {}
                    )
                    view.tags = list(agent.tags) if hasattr(agent, "tags") else []
                    view.current_load = (
                        agent.current_load if hasattr(agent, "current_load") else 0
                    )
                    view.max_concurrent = (
                        agent.max_concurrent_tasks
                        if hasattr(agent, "max_concurrent_tasks")
                        else 1
                    )
                    view.utilization = (
                        agent.utilization if hasattr(agent, "utilization") else 0.0
                    )
                    view.total_completed = (
                        agent.total_completed
                        if hasattr(agent, "total_completed")
                        else 0
                    )
                    view.total_failed = (
                        agent.total_failed if hasattr(agent, "total_failed") else 0
                    )
                else:
                    view.conflicts.append("fleet: agent not registered")
            except Exception as e:
                view.conflicts.append(f"fleet_error: {e}")

        # Detect state conflicts
        if view.lifecycle_state and view.fleet_status:
            expected_fleet = LIFECYCLE_TO_FLEET_STATUS.get(view.lifecycle_state)
            if expected_fleet and expected_fleet != view.fleet_status:
                view.in_sync = False
                view.conflicts.append(
                    f"state_mismatch: lifecycle={view.lifecycle_state} expects "
                    f"fleet={expected_fleet}, got fleet={view.fleet_status}"
                )

        if view.conflicts:
            view.in_sync = False

        return view

    def get_fleet_overview(self) -> dict:
        """
        Get a unified overview of the entire fleet from both systems.
        """
        overview = {
            "lifecycle": None,
            "fleet": None,
            "sync_status": {
                "total_syncs": self._sync_count,
                "total_errors": self._error_count,
                "total_conflicts": self._conflict_count,
                "last_reconciliation": self._last_reconciliation,
            },
        }

        if self._lifecycle is not None:
            try:
                overview["lifecycle"] = self._lifecycle.get_swarm_status()
            except Exception as e:
                overview["lifecycle"] = {"error": str(e)}

        if self._fleet is not None:
            try:
                overview["fleet"] = self._fleet.health()
            except Exception as e:
                overview["fleet"] = {"error": str(e)}

        return overview

    # ── Reconciliation ────────────────────────────────────────

    def reconcile(self, fix: bool = True) -> ReconciliationReport:
        """
        Full reconciliation pass between both systems.

        Checks every agent in both systems for state mismatches.
        If fix=True and auto_resolve_conflicts is enabled, fixes conflicts
        by treating LifecycleManager as the source of truth.
        """
        report = ReconciliationReport()

        lifecycle_ids = set()
        fleet_ids = set()

        # Gather agent IDs from both systems
        if self._lifecycle is not None:
            lifecycle_ids = set(self._lifecycle.agents.keys())

        if self._fleet is not None:
            for agent in self._fleet.list_agents():
                fleet_ids.add(agent.agent_id)

        all_ids = lifecycle_ids | fleet_ids
        report.agents_checked = len(all_ids)

        # Find agents only in one system
        report.lifecycle_only = sorted(lifecycle_ids - fleet_ids)
        report.fleet_only = sorted(fleet_ids - lifecycle_ids)

        # Check each agent in both systems
        for agent_id in lifecycle_ids & fleet_ids:
            view = self.get_unified_view(agent_id)

            if view.in_sync:
                report.agents_in_sync += 1
            else:
                report.agents_out_of_sync += 1
                report.conflicts_found += len(view.conflicts)

                # Auto-resolve: lifecycle is source of truth
                if fix and self._auto_resolve and view.lifecycle_state:
                    try:
                        event = self.sync_state_change(agent_id, view.lifecycle_state)
                        if event.success:
                            report.conflicts_resolved += 1
                            report.sync_events.append(event)
                            self._conflict_count += 1
                    except Exception as e:
                        logger.warning(f"Auto-resolve failed for agent {agent_id}: {e}")

        self._last_reconciliation = time.time()
        return report

    # ── Health & Diagnostics ──────────────────────────────────

    def health(self) -> dict:
        """Bridge health status."""
        return {
            "healthy": self._error_count == 0
            or (self._sync_count > 0 and self._error_count / self._sync_count < 0.1),
            "lifecycle_connected": self._lifecycle is not None,
            "fleet_connected": self._fleet is not None,
            "sync_count": self._sync_count,
            "error_count": self._error_count,
            "conflict_count": self._conflict_count,
            "last_reconciliation": self._last_reconciliation,
            "uptime_seconds": time.time() - self._created_at,
            "history_size": len(self._history),
        }

    def get_recent_events(self, limit: int = 20) -> list[dict]:
        """Get recent sync events."""
        events = list(self._history)[-limit:]
        return [e.to_dict() for e in events]

    def get_sync_stats(self) -> dict:
        """Get sync statistics by event type."""
        stats: dict = {}
        for event in self._history:
            et = event.event_type.value
            if et not in stats:
                stats[et] = {"count": 0, "successes": 0, "failures": 0}
            stats[et]["count"] += 1
            if event.success:
                stats[et]["successes"] += 1
            else:
                stats[et]["failures"] += 1
        return stats

    def summary(self) -> dict:
        """Compact summary for dashboards."""
        return {
            "bridge": "fleet_lifecycle",
            "healthy": self.health()["healthy"],
            "syncs": self._sync_count,
            "errors": self._error_count,
            "conflicts": self._conflict_count,
            "last_reconciliation_ago": (
                f"{time.time() - self._last_reconciliation:.0f}s"
                if self._last_reconciliation
                else None
            ),
        }

    # ── Internal ──────────────────────────────────────────────

    def _record_event(self, event: SyncEvent) -> None:
        """Record a sync event to history."""
        self._history.append(event)
        self._sync_count += 1
        if not event.success:
            logger.debug(
                f"Sync event {event.event_type.value} for agent {event.agent_id}: "
                f"error={event.error}"
            )

    def _resolve_fleet_status(self, status_str: str):
        """Resolve a string to a FleetManager AgentStatus enum."""
        if self._fleet is None:
            return None
        try:
            from .fleet_manager import AgentStatus

            return AgentStatus(status_str)
        except (ValueError, ImportError):
            return None
