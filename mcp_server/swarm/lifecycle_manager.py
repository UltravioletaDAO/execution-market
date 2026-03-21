"""
LifecycleManager — Manages agent states, budgets, and health.

State machine:
    INITIALIZING → IDLE → ACTIVE → WORKING → COOLDOWN → IDLE
                                             ↓
                                         DEGRADED → IDLE (on recovery)
                                             ↓
                                         SUSPENDED (manual intervention)

Budget tracking prevents runaway costs. Health monitoring ensures
agents respond to heartbeats within acceptable windows.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional


class AgentState(str, Enum):
    """Agent lifecycle states."""

    INITIALIZING = "initializing"  # First boot, workspace setup
    IDLE = "idle"  # Ready for work, not currently assigned
    ACTIVE = "active"  # Browsing task pool, not committed
    WORKING = "working"  # Committed to a task
    COOLDOWN = "cooldown"  # Post-task cooldown period
    DEGRADED = "degraded"  # Missed heartbeats or errors
    SUSPENDED = "suspended"  # Manually or auto-suspended (budget/abuse)


# Transitions allowed from each state
VALID_TRANSITIONS = {
    AgentState.INITIALIZING: {AgentState.IDLE, AgentState.SUSPENDED},
    AgentState.IDLE: {AgentState.ACTIVE, AgentState.SUSPENDED, AgentState.DEGRADED},
    AgentState.ACTIVE: {
        AgentState.IDLE,
        AgentState.WORKING,
        AgentState.SUSPENDED,
        AgentState.DEGRADED,
    },
    AgentState.WORKING: {
        AgentState.COOLDOWN,
        AgentState.DEGRADED,
        AgentState.SUSPENDED,
    },
    AgentState.COOLDOWN: {AgentState.IDLE, AgentState.DEGRADED, AgentState.SUSPENDED},
    AgentState.DEGRADED: {AgentState.IDLE, AgentState.SUSPENDED},
    AgentState.SUSPENDED: {AgentState.IDLE},  # Manual resume only
}


@dataclass
class BudgetConfig:
    """Budget limits for an agent."""

    daily_limit_usd: float = 5.0  # Max daily spend
    monthly_limit_usd: float = 100.0  # Max monthly spend
    task_limit_usd: float = 2.0  # Max per-task cost
    warning_threshold: float = 0.80  # Alert at 80% budget
    hard_stop_threshold: float = 1.0  # Suspend at 100%


@dataclass
class BudgetState:
    """Current budget consumption."""

    daily_spent_usd: float = 0.0
    monthly_spent_usd: float = 0.0
    last_reset_date: Optional[str] = None  # YYYY-MM-DD
    last_monthly_reset: Optional[str] = None  # YYYY-MM

    def check_daily_reset(self) -> None:
        """Reset daily counter if date changed."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.last_reset_date != today:
            self.daily_spent_usd = 0.0
            self.last_reset_date = today

    def check_monthly_reset(self) -> None:
        """Reset monthly counter if month changed."""
        this_month = datetime.now(timezone.utc).strftime("%Y-%m")
        if self.last_monthly_reset != this_month:
            self.monthly_spent_usd = 0.0
            self.last_monthly_reset = this_month


@dataclass
class HealthStatus:
    """Agent health tracking."""

    last_heartbeat: Optional[datetime] = None
    consecutive_missed: int = 0
    total_heartbeats: int = 0
    errors_last_hour: int = 0
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None

    # Thresholds
    max_missed_heartbeats: int = 3
    heartbeat_interval_seconds: int = 300  # 5 minutes

    @property
    def is_healthy(self) -> bool:
        return self.consecutive_missed < self.max_missed_heartbeats

    @property
    def seconds_since_heartbeat(self) -> float:
        if self.last_heartbeat is None:
            return float("inf")
        now = datetime.now(timezone.utc)
        if self.last_heartbeat.tzinfo is None:
            hb = self.last_heartbeat.replace(tzinfo=timezone.utc)
        else:
            hb = self.last_heartbeat
        return (now - hb).total_seconds()


@dataclass
class AgentRecord:
    """Complete lifecycle record for one agent."""

    agent_id: int
    name: str
    wallet_address: str
    state: AgentState = AgentState.INITIALIZING
    personality: str = "explorer"
    budget_config: BudgetConfig = field(default_factory=BudgetConfig)
    budget_state: BudgetState = field(default_factory=BudgetState)
    health: HealthStatus = field(default_factory=HealthStatus)
    current_task_id: Optional[str] = None
    cooldown_until: Optional[datetime] = None
    state_changed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        now = datetime.now(timezone.utc)
        if self.created_at is None:
            self.created_at = now
        if self.state_changed_at is None:
            self.state_changed_at = now


class LifecycleError(Exception):
    """Error in lifecycle state transitions."""

    pass


class BudgetExceededError(LifecycleError):
    """Agent budget has been exceeded."""

    pass


class LifecycleManager:
    """
    Manages the lifecycle of all agents in the swarm.

    Usage:
        manager = LifecycleManager()
        manager.register_agent(agent_id=1, name="aurora", wallet="0x...")
        manager.transition(1, AgentState.IDLE)
        manager.transition(1, AgentState.ACTIVE)
        manager.assign_task(1, "task-123")
        manager.record_heartbeat(1)
        cost = 0.50
        manager.record_spend(1, cost)
        manager.complete_task(1, cooldown_seconds=60)
    """

    def __init__(self):
        self._agents: dict[int, AgentRecord] = {}
        self._state_history: list[dict] = []  # Audit log

    @property
    def agents(self) -> dict[int, AgentRecord]:
        return self._agents.copy()

    def register_agent(
        self,
        agent_id: int,
        name: str,
        wallet_address: str,
        personality: str = "explorer",
        budget_config: Optional[BudgetConfig] = None,
        tags: Optional[list[str]] = None,
    ) -> AgentRecord:
        """Register a new agent in the lifecycle system."""
        if agent_id in self._agents:
            raise LifecycleError(f"Agent {agent_id} already registered")

        record = AgentRecord(
            agent_id=agent_id,
            name=name,
            wallet_address=wallet_address,
            personality=personality,
            budget_config=budget_config or BudgetConfig(),
            tags=tags or [],
        )
        self._agents[agent_id] = record
        self._log_transition(agent_id, None, AgentState.INITIALIZING, "registered")
        return record

    def unregister_agent(self, agent_id: int) -> None:
        """Remove an agent from the lifecycle system."""
        if agent_id not in self._agents:
            raise LifecycleError(f"Agent {agent_id} not found")
        del self._agents[agent_id]

    def transition(
        self, agent_id: int, new_state: AgentState, reason: str = ""
    ) -> AgentRecord:
        """
        Transition an agent to a new state.
        Validates the transition is legal.
        """
        record = self._get_agent(agent_id)
        old_state = record.state

        if new_state not in VALID_TRANSITIONS.get(old_state, set()):
            raise LifecycleError(
                f"Invalid transition: {old_state.value} → {new_state.value} "
                f"for agent {agent_id}. "
                f"Valid targets: {[s.value for s in VALID_TRANSITIONS.get(old_state, set())]}"
            )

        record.state = new_state
        record.state_changed_at = datetime.now(timezone.utc)
        self._log_transition(agent_id, old_state, new_state, reason)
        return record

    def assign_task(self, agent_id: int, task_id: str) -> AgentRecord:
        """Assign a task to an agent. Must be in ACTIVE state."""
        record = self._get_agent(agent_id)

        if record.state != AgentState.ACTIVE:
            raise LifecycleError(
                f"Agent {agent_id} must be ACTIVE to accept tasks, "
                f"currently {record.state.value}"
            )

        # Check budget before assigning
        self._check_budget(record)

        record.current_task_id = task_id
        self.transition(agent_id, AgentState.WORKING, f"assigned task {task_id}")
        return record

    def complete_task(
        self,
        agent_id: int,
        cooldown_seconds: int = 30,
    ) -> AgentRecord:
        """Complete current task and enter cooldown."""
        record = self._get_agent(agent_id)

        if record.state != AgentState.WORKING:
            raise LifecycleError(
                f"Agent {agent_id} must be WORKING to complete tasks, "
                f"currently {record.state.value}"
            )

        task_id = record.current_task_id
        record.current_task_id = None
        record.cooldown_until = datetime.now(timezone.utc) + timedelta(
            seconds=cooldown_seconds
        )
        self.transition(agent_id, AgentState.COOLDOWN, f"completed task {task_id}")
        return record

    def check_cooldown_expiry(self, agent_id: int) -> bool:
        """
        Check if an agent's cooldown has expired.
        If so, transition to IDLE. Returns True if transitioned.
        """
        record = self._get_agent(agent_id)

        if record.state != AgentState.COOLDOWN:
            return False

        if record.cooldown_until is None:
            # No cooldown set, transition immediately
            self.transition(agent_id, AgentState.IDLE, "cooldown expired (no duration)")
            return True

        now = datetime.now(timezone.utc)
        if now >= record.cooldown_until:
            record.cooldown_until = None
            self.transition(agent_id, AgentState.IDLE, "cooldown expired")
            return True

        return False

    def record_heartbeat(self, agent_id: int) -> AgentRecord:
        """Record a successful heartbeat from an agent."""
        record = self._get_agent(agent_id)
        record.health.last_heartbeat = datetime.now(timezone.utc)
        record.health.consecutive_missed = 0
        record.health.total_heartbeats += 1

        # If agent was degraded, recover to IDLE
        if record.state == AgentState.DEGRADED:
            self.transition(agent_id, AgentState.IDLE, "recovered after heartbeat")

        return record

    def check_heartbeat(self, agent_id: int) -> bool:
        """
        Check if an agent's heartbeat is overdue.
        Returns True if healthy, False if degraded.
        """
        record = self._get_agent(agent_id)

        if record.health.last_heartbeat is None:
            # Never sent a heartbeat — only flag if past initial grace period
            if record.state == AgentState.INITIALIZING:
                return True
            record.health.consecutive_missed += 1
        elif (
            record.health.seconds_since_heartbeat
            > record.health.heartbeat_interval_seconds
        ):
            record.health.consecutive_missed += 1

        if not record.health.is_healthy and record.state not in (
            AgentState.DEGRADED,
            AgentState.SUSPENDED,
        ):
            self.transition(agent_id, AgentState.DEGRADED, "missed heartbeats")
            return False

        return record.health.is_healthy

    def record_error(self, agent_id: int, error: str) -> None:
        """Record an error for health tracking."""
        record = self._get_agent(agent_id)
        record.health.errors_last_hour += 1
        record.health.last_error = error
        record.health.last_error_at = datetime.now(timezone.utc)

    def record_spend(self, agent_id: int, amount_usd: float) -> None:
        """Record spending and check budget limits."""
        record = self._get_agent(agent_id)
        record.budget_state.check_daily_reset()
        record.budget_state.check_monthly_reset()

        record.budget_state.daily_spent_usd += amount_usd
        record.budget_state.monthly_spent_usd += amount_usd

        # Check hard stop
        self._check_budget(record)

    def get_budget_status(self, agent_id: int) -> dict:
        """Get current budget utilization."""
        record = self._get_agent(agent_id)
        record.budget_state.check_daily_reset()
        record.budget_state.check_monthly_reset()

        daily_pct = (
            record.budget_state.daily_spent_usd / record.budget_config.daily_limit_usd
            if record.budget_config.daily_limit_usd > 0
            else 0
        )
        monthly_pct = (
            record.budget_state.monthly_spent_usd
            / record.budget_config.monthly_limit_usd
            if record.budget_config.monthly_limit_usd > 0
            else 0
        )

        return {
            "agent_id": agent_id,
            "daily_spent": record.budget_state.daily_spent_usd,
            "daily_limit": record.budget_config.daily_limit_usd,
            "daily_pct": round(daily_pct * 100, 1),
            "monthly_spent": record.budget_state.monthly_spent_usd,
            "monthly_limit": record.budget_config.monthly_limit_usd,
            "monthly_pct": round(monthly_pct * 100, 1),
            "at_warning": daily_pct >= record.budget_config.warning_threshold
            or monthly_pct >= record.budget_config.warning_threshold,
            "at_limit": daily_pct >= record.budget_config.hard_stop_threshold
            or monthly_pct >= record.budget_config.hard_stop_threshold,
        }

    def get_available_agents(self) -> list[AgentRecord]:
        """Get agents that are ready for task assignment."""
        available = []
        for record in self._agents.values():
            # Check cooldown expiry for cooldown agents
            if record.state == AgentState.COOLDOWN:
                self.check_cooldown_expiry(record.agent_id)

            if record.state in (AgentState.IDLE, AgentState.ACTIVE):
                # Also check budget
                try:
                    self._check_budget(record)
                    available.append(record)
                except BudgetExceededError:
                    continue
        return available

    def get_swarm_status(self) -> dict:
        """Get overview of swarm health."""
        counts = {state.value: 0 for state in AgentState}
        for record in self._agents.values():
            counts[record.state.value] += 1

        total_daily = sum(r.budget_state.daily_spent_usd for r in self._agents.values())
        total_monthly = sum(
            r.budget_state.monthly_spent_usd for r in self._agents.values()
        )

        return {
            "total_agents": len(self._agents),
            "state_counts": counts,
            "available_count": len(self.get_available_agents()),
            "total_daily_spend": round(total_daily, 2),
            "total_monthly_spend": round(total_monthly, 2),
            "degraded_agents": [
                r.agent_id
                for r in self._agents.values()
                if r.state == AgentState.DEGRADED
            ],
            "suspended_agents": [
                r.agent_id
                for r in self._agents.values()
                if r.state == AgentState.SUSPENDED
            ],
        }

    def _get_agent(self, agent_id: int) -> AgentRecord:
        """Get agent record or raise."""
        if agent_id not in self._agents:
            raise LifecycleError(f"Agent {agent_id} not found")
        return self._agents[agent_id]

    def _check_budget(self, record: AgentRecord) -> None:
        """Check if agent is within budget. Raises BudgetExceededError if not."""
        record.budget_state.check_daily_reset()
        record.budget_state.check_monthly_reset()

        daily_pct = (
            record.budget_state.daily_spent_usd / record.budget_config.daily_limit_usd
            if record.budget_config.daily_limit_usd > 0
            else 0
        )
        monthly_pct = (
            record.budget_state.monthly_spent_usd
            / record.budget_config.monthly_limit_usd
            if record.budget_config.monthly_limit_usd > 0
            else 0
        )

        if daily_pct >= record.budget_config.hard_stop_threshold:
            if record.state not in (AgentState.SUSPENDED,):
                try:
                    self.transition(
                        record.agent_id, AgentState.SUSPENDED, "daily budget exceeded"
                    )
                except LifecycleError:
                    pass
            raise BudgetExceededError(
                f"Agent {record.agent_id} daily budget exceeded: "
                f"${record.budget_state.daily_spent_usd:.2f}/${record.budget_config.daily_limit_usd:.2f}"
            )

        if monthly_pct >= record.budget_config.hard_stop_threshold:
            if record.state not in (AgentState.SUSPENDED,):
                try:
                    self.transition(
                        record.agent_id, AgentState.SUSPENDED, "monthly budget exceeded"
                    )
                except LifecycleError:
                    pass
            raise BudgetExceededError(
                f"Agent {record.agent_id} monthly budget exceeded: "
                f"${record.budget_state.monthly_spent_usd:.2f}/${record.budget_config.monthly_limit_usd:.2f}"
            )

    def _log_transition(
        self,
        agent_id: int,
        from_state: Optional[AgentState],
        to_state: AgentState,
        reason: str,
    ) -> None:
        """Log state transition for audit."""
        self._state_history.append(
            {
                "agent_id": agent_id,
                "from": from_state.value if from_state else None,
                "to": to_state.value,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    @property
    def state_history(self) -> list[dict]:
        """Get state transition audit log."""
        return self._state_history.copy()
