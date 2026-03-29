"""
FleetManager — Agent Fleet Lifecycle and Capability Management
=============================================================

Module #53 in the KK V2 Swarm.

Manages the registered agent fleet as a first-class operational concern:
- Agent capability profiles (what each agent can do)
- Availability windows (when agents are active)
- Load balancing and capacity tracking
- Fleet-level health metrics
- Agent grouping and tagging

Architecture:

    ┌─────────────────────────────────────────────────────────┐
    │                   FleetManager                           │
    │                                                          │
    │  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐  │
    │  │ AgentProfile  │  │  Capability  │  │  Availability │  │
    │  │  Registry     │  │    Matrix    │  │    Windows    │  │
    │  └──────┬───────┘  └──────┬──────┘  └───────┬───────┘  │
    │         │                  │                  │          │
    │         └──────────┬───────┘──────────────────┘          │
    │                    │                                     │
    │           ┌────────▼────────┐                            │
    │           │  Fleet Metrics  │                            │
    │           │  & Load Balance │                            │
    │           └─────────────────┘                            │
    └─────────────────────────────────────────────────────────┘

What this adds over LifecycleManager:
1. Capability-based routing (what can an agent do?)
2. Availability windows (when is an agent active?)
3. Load balancing with configurable strategies
4. Fleet segmentation by tags/groups
5. Capacity forecasting based on historical utilization
6. Agent fitness scoring for specific task types

Usage:
    from mcp_server.swarm.fleet_manager import FleetManager

    fleet = FleetManager()
    fleet.register_agent(AgentProfile(
        agent_id=2106,
        name="UltraClawd",
        capabilities=["delivery", "photography", "research"],
        max_concurrent_tasks=3,
    ))

    # Find best agents for a task
    candidates = fleet.find_capable_agents("delivery", min_fitness=0.7)

    # Check fleet capacity
    capacity = fleet.capacity_snapshot()
"""

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger("em.swarm.fleet_manager")


# ──────────────────────────────────────────────────────────────
# Types
# ──────────────────────────────────────────────────────────────


class AgentStatus(str, Enum):
    """Fleet-level agent status."""

    ACTIVE = "active"  # Available for task assignment
    BUSY = "busy"  # At max concurrent tasks
    IDLE = "idle"  # Registered but not recently active
    OFFLINE = "offline"  # Explicitly offline or timed out
    SUSPENDED = "suspended"  # Administratively suspended
    COOLDOWN = "cooldown"  # Between tasks, brief rest


class LoadBalanceStrategy(str, Enum):
    """How to distribute tasks across agents."""

    ROUND_ROBIN = "round_robin"  # Rotate evenly
    LEAST_LOADED = "least_loaded"  # Prefer agents with fewest tasks
    BEST_FIT = "best_fit"  # Highest capability score for task type
    WEIGHTED = "weighted"  # Combine fitness + load + availability


class CapabilityLevel(str, Enum):
    """How well an agent can handle a capability."""

    NOVICE = "novice"  # Can do it, but slowly/less reliably
    COMPETENT = "competent"  # Standard performance
    PROFICIENT = "proficient"  # Above average
    EXPERT = "expert"  # Top tier
    SPECIALIST = "specialist"  # Best in fleet for this


CAPABILITY_SCORES = {
    CapabilityLevel.NOVICE: 0.2,
    CapabilityLevel.COMPETENT: 0.5,
    CapabilityLevel.PROFICIENT: 0.7,
    CapabilityLevel.EXPERT: 0.9,
    CapabilityLevel.SPECIALIST: 1.0,
}


@dataclass
class AvailabilityWindow:
    """When an agent is available for work."""

    day_of_week: int  # 0=Monday, 6=Sunday
    start_hour: int  # 0-23 UTC
    end_hour: int  # 0-23 UTC (end_hour < start_hour means overnight)

    def is_active_at(self, dt: datetime) -> bool:
        """Check if this window covers the given datetime."""
        if dt.weekday() != self.day_of_week:
            return False
        hour = dt.hour
        if self.start_hour <= self.end_hour:
            return self.start_hour <= hour < self.end_hour
        else:
            # Overnight window (e.g., 22:00 - 06:00)
            return hour >= self.start_hour or hour < self.end_hour


@dataclass
class Capability:
    """A specific thing an agent can do."""

    name: str
    level: CapabilityLevel = CapabilityLevel.COMPETENT
    tasks_completed: int = 0
    avg_completion_time_s: float = 0.0
    success_rate: float = 1.0
    last_used: Optional[float] = None

    @property
    def score(self) -> float:
        """Composite capability score (0-1)."""
        base = CAPABILITY_SCORES.get(self.level, 0.5)
        # Boost for experience (diminishing returns)
        experience_bonus = min(0.1, self.tasks_completed * 0.005)
        # Penalty for low success rate
        success_factor = max(0.5, self.success_rate)
        return min(1.0, base * success_factor + experience_bonus)


@dataclass
class TaskLoad:
    """Current task load for an agent."""

    active_tasks: int = 0
    tasks_today: int = 0
    tasks_this_hour: int = 0
    total_tasks_ever: int = 0
    last_task_completed: Optional[float] = None
    last_task_assigned: Optional[float] = None


@dataclass
class AgentProfile:
    """Complete profile for a fleet agent."""

    agent_id: int
    name: str = ""
    wallet_address: str = ""
    capabilities: dict[str, Capability] = field(default_factory=dict)
    tags: set[str] = field(default_factory=set)
    max_concurrent_tasks: int = 3
    availability: list[AvailabilityWindow] = field(default_factory=list)
    status: AgentStatus = AgentStatus.ACTIVE
    load: TaskLoad = field(default_factory=TaskLoad)
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    # Cooldown config
    cooldown_seconds: float = 30.0  # Rest between tasks
    _cooldown_until: float = 0.0

    @property
    def is_available(self) -> bool:
        """Can this agent accept a new task right now?"""
        if self.status in (AgentStatus.OFFLINE, AgentStatus.SUSPENDED):
            return False
        if self.status == AgentStatus.COOLDOWN:
            if time.time() < self._cooldown_until:
                return False
        if self.load.active_tasks >= self.max_concurrent_tasks:
            return False
        return True

    @property
    def utilization(self) -> float:
        """Current utilization ratio (0-1)."""
        if self.max_concurrent_tasks == 0:
            return 1.0
        return self.load.active_tasks / self.max_concurrent_tasks

    def has_capability(self, name: str) -> bool:
        """Check if agent has a specific capability."""
        return name.lower() in {k.lower() for k in self.capabilities}

    def get_capability_score(self, name: str) -> float:
        """Get the score for a specific capability (0 if missing)."""
        for k, v in self.capabilities.items():
            if k.lower() == name.lower():
                return v.score
        return 0.0

    def enter_cooldown(self, duration: Optional[float] = None) -> None:
        """Put agent in cooldown after task completion."""
        self.status = AgentStatus.COOLDOWN
        self._cooldown_until = time.time() + (duration or self.cooldown_seconds)

    def exit_cooldown(self) -> None:
        """Check and exit cooldown if expired."""
        if self.status == AgentStatus.COOLDOWN and time.time() >= self._cooldown_until:
            if self.load.active_tasks > 0:
                self.status = AgentStatus.BUSY
            else:
                self.status = AgentStatus.ACTIVE


@dataclass
class FleetSnapshot:
    """Point-in-time fleet status."""

    timestamp: float
    total_agents: int
    active_agents: int
    busy_agents: int
    idle_agents: int
    offline_agents: int
    suspended_agents: int
    cooldown_agents: int
    total_capacity: int  # Sum of max_concurrent_tasks
    used_capacity: int  # Sum of active_tasks
    utilization: float  # used/total ratio

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "agents": {
                "total": self.total_agents,
                "active": self.active_agents,
                "busy": self.busy_agents,
                "idle": self.idle_agents,
                "offline": self.offline_agents,
                "suspended": self.suspended_agents,
                "cooldown": self.cooldown_agents,
            },
            "capacity": {
                "total": self.total_capacity,
                "used": self.used_capacity,
                "available": self.total_capacity - self.used_capacity,
                "utilization": round(self.utilization, 3),
            },
        }


@dataclass
class CandidateScore:
    """Score for a candidate agent for a specific task."""

    agent_id: int
    fitness: float  # Capability fit (0-1)
    load_score: float  # Load availability (0-1, higher = less loaded)
    availability_score: float  # Schedule fit (0 or 1)
    composite: float  # Final weighted score

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "fitness": round(self.fitness, 3),
            "load_score": round(self.load_score, 3),
            "availability_score": round(self.availability_score, 3),
            "composite": round(self.composite, 3),
        }


# ──────────────────────────────────────────────────────────────
# FleetManager
# ──────────────────────────────────────────────────────────────


class FleetManager:
    """
    Manages the agent fleet as a first-class operational concern.

    Responsibilities:
    - Agent registration and deregistration
    - Capability tracking and querying
    - Load balancing across agents
    - Availability window management
    - Fleet health metrics
    - Capacity forecasting
    """

    def __init__(
        self,
        default_strategy: LoadBalanceStrategy = LoadBalanceStrategy.WEIGHTED,
        heartbeat_timeout_s: float = 300.0,
        history_size: int = 100,
    ):
        self._agents: dict[int, AgentProfile] = {}
        self._strategy = default_strategy
        self._heartbeat_timeout = heartbeat_timeout_s
        self._history: deque[FleetSnapshot] = deque(maxlen=history_size)

        # Indexes for fast lookup
        self._by_capability: dict[str, set[int]] = defaultdict(set)
        self._by_tag: dict[str, set[int]] = defaultdict(set)
        self._by_status: dict[AgentStatus, set[int]] = defaultdict(set)

        # Round-robin state
        self._rr_index = 0

        # Metrics
        self._total_assignments = 0
        self._total_completions = 0
        self._assignment_history: deque[dict] = deque(maxlen=500)

    # ─── Agent Registration ───────────────────────────────────

    def register_agent(self, profile: AgentProfile) -> AgentProfile:
        """Register a new agent or update an existing one."""
        old = self._agents.get(profile.agent_id)
        if old:
            # Remove old indexes
            self._remove_indexes(old)

        self._agents[profile.agent_id] = profile
        self._add_indexes(profile)
        logger.info(f"Agent {profile.agent_id} registered: {profile.name}")
        return profile

    def deregister_agent(self, agent_id: int) -> Optional[AgentProfile]:
        """Remove an agent from the fleet."""
        profile = self._agents.pop(agent_id, None)
        if profile:
            self._remove_indexes(profile)
            logger.info(f"Agent {agent_id} deregistered")
        return profile

    def get_agent(self, agent_id: int) -> Optional[AgentProfile]:
        """Get an agent profile by ID."""
        return self._agents.get(agent_id)

    def list_agents(
        self,
        status: Optional[AgentStatus] = None,
        capability: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> list[AgentProfile]:
        """List agents with optional filters."""
        candidates = set(self._agents.keys())

        if status is not None:
            candidates &= self._by_status.get(status, set())

        if capability is not None:
            cap_lower = capability.lower()
            matching = set()
            for cap_key, agent_ids in self._by_capability.items():
                if cap_key.lower() == cap_lower:
                    matching |= agent_ids
            candidates &= matching

        if tag is not None:
            candidates &= self._by_tag.get(tag, set())

        return [self._agents[aid] for aid in candidates if aid in self._agents]

    def agent_count(self) -> int:
        """Total registered agents."""
        return len(self._agents)

    # ─── Capability Management ────────────────────────────────

    def add_capability(
        self,
        agent_id: int,
        capability_name: str,
        level: CapabilityLevel = CapabilityLevel.COMPETENT,
    ) -> bool:
        """Add or update a capability for an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        cap = agent.capabilities.get(capability_name)
        if cap:
            cap.level = level
        else:
            agent.capabilities[capability_name] = Capability(
                name=capability_name, level=level
            )
            self._by_capability[capability_name].add(agent_id)

        return True

    def remove_capability(self, agent_id: int, capability_name: str) -> bool:
        """Remove a capability from an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        if capability_name in agent.capabilities:
            del agent.capabilities[capability_name]
            self._by_capability[capability_name].discard(agent_id)
            return True
        return False

    def get_capability_matrix(self) -> dict[str, list[dict]]:
        """
        Get a matrix of all capabilities and which agents have them.

        Returns:
            {"delivery": [{"agent_id": 2106, "level": "expert", "score": 0.9}, ...]}
        """
        matrix: dict[str, list[dict]] = {}
        for cap_name, agent_ids in self._by_capability.items():
            matrix[cap_name] = []
            for aid in agent_ids:
                agent = self._agents.get(aid)
                if agent and cap_name in agent.capabilities:
                    cap = agent.capabilities[cap_name]
                    matrix[cap_name].append({
                        "agent_id": aid,
                        "name": agent.name,
                        "level": cap.level.value,
                        "score": round(cap.score, 3),
                        "tasks_completed": cap.tasks_completed,
                    })
            # Sort by score descending
            matrix[cap_name].sort(key=lambda x: x["score"], reverse=True)
        return matrix

    # ─── Tag Management ───────────────────────────────────────

    def add_tag(self, agent_id: int, tag: str) -> bool:
        """Tag an agent for grouping."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.tags.add(tag)
        self._by_tag[tag].add(agent_id)
        return True

    def remove_tag(self, agent_id: int, tag: str) -> bool:
        """Remove a tag from an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        if tag not in agent.tags:
            return False
        agent.tags.discard(tag)
        self._by_tag[tag].discard(agent_id)
        return True

    # ─── Status Management ────────────────────────────────────

    def set_status(self, agent_id: int, status: AgentStatus) -> bool:
        """Update an agent's fleet status."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        old_status = agent.status
        self._by_status[old_status].discard(agent_id)
        agent.status = status
        self._by_status[status].add(agent_id)
        return True

    def heartbeat(self, agent_id: int) -> bool:
        """Record an agent heartbeat (prove liveness)."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        agent.last_heartbeat = time.time()
        # Auto-revive from idle if heartbeat received
        if agent.status == AgentStatus.IDLE:
            self.set_status(agent_id, AgentStatus.ACTIVE)
        return True

    def check_heartbeats(self) -> list[int]:
        """
        Check all agents for heartbeat timeout.
        Returns list of agents moved to IDLE.
        """
        now = time.time()
        idled = []
        for aid, agent in self._agents.items():
            if agent.status in (AgentStatus.ACTIVE, AgentStatus.BUSY):
                if now - agent.last_heartbeat > self._heartbeat_timeout:
                    self.set_status(aid, AgentStatus.IDLE)
                    idled.append(aid)
                    logger.warning(f"Agent {aid} heartbeat timeout → IDLE")
        return idled

    # ─── Task Load Tracking ──────────────────────────────────

    def record_task_assigned(self, agent_id: int) -> bool:
        """Record that a task was assigned to an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        agent.load.active_tasks += 1
        agent.load.tasks_today += 1
        agent.load.tasks_this_hour += 1
        agent.load.total_tasks_ever += 1
        agent.load.last_task_assigned = time.time()

        # Update status
        if agent.load.active_tasks >= agent.max_concurrent_tasks:
            self.set_status(agent_id, AgentStatus.BUSY)

        self._total_assignments += 1
        self._assignment_history.append({
            "agent_id": agent_id,
            "timestamp": time.time(),
            "type": "assigned",
        })

        return True

    def record_task_completed(
        self,
        agent_id: int,
        success: bool = True,
        capability_name: Optional[str] = None,
        duration_s: float = 0.0,
    ) -> bool:
        """Record that an agent completed a task."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        agent.load.active_tasks = max(0, agent.load.active_tasks - 1)
        agent.load.last_task_completed = time.time()

        # Update capability stats if provided
        if capability_name and capability_name in agent.capabilities:
            cap = agent.capabilities[capability_name]
            cap.tasks_completed += 1
            cap.last_used = time.time()
            if duration_s > 0:
                # Rolling average
                if cap.avg_completion_time_s == 0:
                    cap.avg_completion_time_s = duration_s
                else:
                    cap.avg_completion_time_s = (
                        cap.avg_completion_time_s * 0.8 + duration_s * 0.2
                    )
            if not success:
                total = cap.tasks_completed
                cap.success_rate = (cap.success_rate * (total - 1) + (1.0 if success else 0.0)) / total

        # Enter cooldown
        agent.enter_cooldown()

        self._total_completions += 1
        self._assignment_history.append({
            "agent_id": agent_id,
            "timestamp": time.time(),
            "type": "completed",
            "success": success,
        })

        return True

    # ─── Load Balancing ──────────────────────────────────────

    def find_capable_agents(
        self,
        capability: str,
        min_fitness: float = 0.0,
        available_only: bool = True,
        limit: int = 10,
    ) -> list[CandidateScore]:
        """
        Find agents capable of a specific task type, scored and ranked.

        Args:
            capability: Required capability name
            min_fitness: Minimum capability score threshold
            available_only: Only include agents that can accept tasks
            limit: Max results

        Returns:
            List of CandidateScore, sorted by composite score descending
        """
        now = datetime.now(timezone.utc)
        candidates = []

        for agent in self._agents.values():
            # Check availability
            if available_only and not agent.is_available:
                # But check if cooldown has expired
                agent.exit_cooldown()
                if not agent.is_available:
                    continue

            # Check capability (must actually have the capability)
            if not agent.has_capability(capability):
                continue
            fitness = agent.get_capability_score(capability)
            if fitness < min_fitness:
                continue

            # Load score: inverse of utilization (less loaded = higher score)
            load_score = 1.0 - agent.utilization

            # Availability window score
            availability_score = 1.0
            if agent.availability:
                availability_score = 1.0 if any(
                    w.is_active_at(now) for w in agent.availability
                ) else 0.0

            # Composite score (weighted blend)
            composite = (
                fitness * 0.50
                + load_score * 0.30
                + availability_score * 0.20
            )

            candidates.append(CandidateScore(
                agent_id=agent.agent_id,
                fitness=fitness,
                load_score=load_score,
                availability_score=availability_score,
                composite=composite,
            ))

        # Sort by composite descending
        candidates.sort(key=lambda c: c.composite, reverse=True)
        return candidates[:limit]

    def select_agent(
        self,
        capability: str,
        strategy: Optional[LoadBalanceStrategy] = None,
    ) -> Optional[CandidateScore]:
        """
        Select the best single agent for a task using the configured strategy.

        Returns None if no capable agent is available.
        """
        strategy = strategy or self._strategy

        if strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._select_round_robin(capability)
        elif strategy == LoadBalanceStrategy.LEAST_LOADED:
            return self._select_least_loaded(capability)
        elif strategy == LoadBalanceStrategy.BEST_FIT:
            candidates = self.find_capable_agents(capability, limit=1)
            return candidates[0] if candidates else None
        elif strategy == LoadBalanceStrategy.WEIGHTED:
            candidates = self.find_capable_agents(capability, limit=1)
            return candidates[0] if candidates else None

        return None

    def _select_round_robin(self, capability: str) -> Optional[CandidateScore]:
        """Round-robin selection among capable agents."""
        capable = [
            a for a in self._agents.values()
            if a.is_available and a.has_capability(capability)
        ]
        if not capable:
            return None

        self._rr_index = self._rr_index % len(capable)
        agent = capable[self._rr_index]
        self._rr_index += 1

        fitness = agent.get_capability_score(capability)
        load_score = 1.0 - agent.utilization
        return CandidateScore(
            agent_id=agent.agent_id,
            fitness=fitness,
            load_score=load_score,
            availability_score=1.0,
            composite=fitness * 0.5 + load_score * 0.3 + 0.2,
        )

    def _select_least_loaded(self, capability: str) -> Optional[CandidateScore]:
        """Select the least loaded capable agent."""
        candidates = self.find_capable_agents(capability)
        if not candidates:
            return None
        # Re-sort by load_score (highest = least loaded)
        candidates.sort(key=lambda c: c.load_score, reverse=True)
        return candidates[0]

    # ─── Fleet Metrics ────────────────────────────────────────

    def capacity_snapshot(self) -> FleetSnapshot:
        """Take a point-in-time snapshot of fleet capacity."""
        now = time.time()

        # Ensure cooldowns are processed
        for agent in self._agents.values():
            agent.exit_cooldown()

        status_counts = defaultdict(int)
        total_capacity = 0
        used_capacity = 0

        for agent in self._agents.values():
            status_counts[agent.status] += 1
            total_capacity += agent.max_concurrent_tasks
            used_capacity += agent.load.active_tasks

        utilization = used_capacity / total_capacity if total_capacity > 0 else 0.0

        snapshot = FleetSnapshot(
            timestamp=now,
            total_agents=len(self._agents),
            active_agents=status_counts.get(AgentStatus.ACTIVE, 0),
            busy_agents=status_counts.get(AgentStatus.BUSY, 0),
            idle_agents=status_counts.get(AgentStatus.IDLE, 0),
            offline_agents=status_counts.get(AgentStatus.OFFLINE, 0),
            suspended_agents=status_counts.get(AgentStatus.SUSPENDED, 0),
            cooldown_agents=status_counts.get(AgentStatus.COOLDOWN, 0),
            total_capacity=total_capacity,
            used_capacity=used_capacity,
            utilization=utilization,
        )

        self._history.append(snapshot)
        return snapshot

    def utilization_trend(self, points: int = 10) -> list[float]:
        """Get recent utilization trend from snapshot history."""
        recent = list(self._history)[-points:]
        return [s.utilization for s in recent]

    def throughput_stats(self) -> dict:
        """Get assignment/completion throughput stats."""
        now = time.time()
        recent = [
            e for e in self._assignment_history
            if now - e["timestamp"] < 3600  # Last hour
        ]
        assignments = sum(1 for e in recent if e["type"] == "assigned")
        completions = sum(1 for e in recent if e["type"] == "completed")
        successes = sum(
            1 for e in recent
            if e["type"] == "completed" and e.get("success", True)
        )

        return {
            "last_hour": {
                "assignments": assignments,
                "completions": completions,
                "successes": successes,
                "success_rate": successes / completions if completions > 0 else 0.0,
            },
            "all_time": {
                "assignments": self._total_assignments,
                "completions": self._total_completions,
            },
        }

    # ─── Diagnostics ──────────────────────────────────────────

    def health(self) -> dict:
        """Comprehensive fleet health report."""
        snapshot = self.capacity_snapshot()
        capable_categories = set()
        for caps in self._by_capability.values():
            if caps:
                capable_categories.add(next(iter(caps)))

        return {
            "fleet": snapshot.to_dict(),
            "capabilities": len(self._by_capability),
            "tags": len(self._by_tag),
            "strategy": self._strategy.value,
            "throughput": self.throughput_stats(),
            "health_status": (
                "healthy" if snapshot.active_agents > 0
                else "degraded" if snapshot.total_agents > 0
                else "empty"
            ),
        }

    def summary(self) -> dict:
        """Compact summary for MCP tool responses."""
        snapshot = self.capacity_snapshot()
        return {
            "agents": snapshot.total_agents,
            "available": snapshot.active_agents,
            "busy": snapshot.busy_agents,
            "utilization": round(snapshot.utilization, 3),
            "capabilities": list(self._by_capability.keys()),
            "strategy": self._strategy.value,
        }

    def get_agent_ranking(
        self,
        capability: Optional[str] = None,
        metric: str = "tasks_completed",
    ) -> list[dict]:
        """Rank agents by a metric. For leaderboard displays."""
        agents = self._agents.values()
        ranked = []

        for agent in agents:
            value = 0
            if metric == "tasks_completed":
                value = agent.load.total_tasks_ever
            elif metric == "utilization":
                value = agent.utilization
            elif metric == "capability_score" and capability:
                value = agent.get_capability_score(capability)

            ranked.append({
                "agent_id": agent.agent_id,
                "name": agent.name,
                "value": round(value, 3) if isinstance(value, float) else value,
                "status": agent.status.value,
            })

        ranked.sort(key=lambda r: r["value"], reverse=True)
        return ranked

    # ─── Persistence ──────────────────────────────────────────

    def save(self) -> dict:
        """Serialize fleet state for persistence."""
        agents_data = []
        for agent in self._agents.values():
            agents_data.append({
                "agent_id": agent.agent_id,
                "name": agent.name,
                "wallet_address": agent.wallet_address,
                "capabilities": {
                    name: {
                        "level": cap.level.value,
                        "tasks_completed": cap.tasks_completed,
                        "avg_completion_time_s": cap.avg_completion_time_s,
                        "success_rate": cap.success_rate,
                    }
                    for name, cap in agent.capabilities.items()
                },
                "tags": list(agent.tags),
                "max_concurrent_tasks": agent.max_concurrent_tasks,
                "status": agent.status.value,
                "load": {
                    "total_tasks_ever": agent.load.total_tasks_ever,
                },
                "metadata": agent.metadata,
            })
        return {
            "version": 1,
            "strategy": self._strategy.value,
            "agents": agents_data,
            "metrics": {
                "total_assignments": self._total_assignments,
                "total_completions": self._total_completions,
            },
        }

    @classmethod
    def load(cls, data: dict) -> "FleetManager":
        """Deserialize fleet state."""
        strategy = LoadBalanceStrategy(
            data.get("strategy", "weighted")
        )
        fleet = cls(default_strategy=strategy)

        for agent_data in data.get("agents", []):
            capabilities = {}
            for name, cap_data in agent_data.get("capabilities", {}).items():
                capabilities[name] = Capability(
                    name=name,
                    level=CapabilityLevel(cap_data.get("level", "competent")),
                    tasks_completed=cap_data.get("tasks_completed", 0),
                    avg_completion_time_s=cap_data.get("avg_completion_time_s", 0),
                    success_rate=cap_data.get("success_rate", 1.0),
                )

            profile = AgentProfile(
                agent_id=agent_data["agent_id"],
                name=agent_data.get("name", ""),
                wallet_address=agent_data.get("wallet_address", ""),
                capabilities=capabilities,
                tags=set(agent_data.get("tags", [])),
                max_concurrent_tasks=agent_data.get("max_concurrent_tasks", 3),
                status=AgentStatus(agent_data.get("status", "active")),
                metadata=agent_data.get("metadata", {}),
            )
            profile.load.total_tasks_ever = (
                agent_data.get("load", {}).get("total_tasks_ever", 0)
            )

            fleet.register_agent(profile)

        metrics = data.get("metrics", {})
        fleet._total_assignments = metrics.get("total_assignments", 0)
        fleet._total_completions = metrics.get("total_completions", 0)

        return fleet

    # ─── Internal Indexing ────────────────────────────────────

    def _add_indexes(self, profile: AgentProfile) -> None:
        """Add an agent to all lookup indexes."""
        for cap_name in profile.capabilities:
            self._by_capability[cap_name].add(profile.agent_id)
        for tag in profile.tags:
            self._by_tag[tag].add(profile.agent_id)
        self._by_status[profile.status].add(profile.agent_id)

    def _remove_indexes(self, profile: AgentProfile) -> None:
        """Remove an agent from all lookup indexes."""
        for cap_name in profile.capabilities:
            self._by_capability[cap_name].discard(profile.agent_id)
        for tag in profile.tags:
            self._by_tag[tag].discard(profile.agent_id)
        self._by_status[profile.status].discard(profile.agent_id)
