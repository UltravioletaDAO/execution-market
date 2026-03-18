"""
SwarmDashboard — Real-Time Fleet Health Monitoring
====================================================

Single pane of glass for the 24-agent KarmaCadabra V2 swarm.
Aggregates data from Analytics, LifecycleManager, Scheduler, and
AcontextAdapter into unified health reports and operational insights.

Key capabilities:
1. **Fleet Status** — Agent states, health scores, last-seen timestamps
2. **Task Pipeline** — Queued/active/completed/failed task counts with flow rates
3. **Performance Heatmap** — Per-agent × per-category success rates
4. **Budget Burn** — Real-time spend tracking with projections and alerts
5. **Coordination Health** — Acontext lock contention, IRC connectivity
6. **SLA Monitoring** — Task completion time vs. deadline adherence
7. **Alert Triage** — Prioritized actionable alerts with severity levels

Architecture:
    SwarmAnalytics ─┐
    LifecycleManager ─┤
    SwarmScheduler ───┼─→ SwarmDashboard → DashboardSnapshot
    AcontextAdapter ──┤
    StatePersistence ─┘

Output:
    DashboardSnapshot — Full fleet snapshot for MCP tools / heartbeat reports
    HealthReport — Condensed health summary for IRC broadcast / notifications

No external dependencies. All data sourced from in-memory module state.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional


# ──────────────────────────────────────────────────────────────
# Severity & Status Types
# ──────────────────────────────────────────────────────────────


class Severity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class FleetStatus(str, Enum):
    """Overall fleet health assessment."""
    HEALTHY = "healthy"          # >80% agents operational, no critical alerts
    DEGRADED = "degraded"        # 50-80% operational OR warning alerts
    IMPAIRED = "impaired"        # 25-50% operational OR critical alerts
    DOWN = "down"                # <25% operational OR emergency alerts


class PipelineStage(str, Enum):
    """Task pipeline stages."""
    QUEUED = "queued"
    SCHEDULING = "scheduling"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


# ──────────────────────────────────────────────────────────────
# Dashboard Data Types
# ──────────────────────────────────────────────────────────────


@dataclass
class AgentStatus:
    """Current status snapshot for a single agent."""
    agent_id: str
    state: str = "unknown"
    health_score: float = 0.0          # 0.0 - 1.0
    tasks_completed_today: int = 0
    tasks_failed_today: int = 0
    success_rate: float = 0.0          # 0.0 - 1.0
    avg_completion_time_s: float = 0.0
    daily_spend_usd: float = 0.0
    daily_budget_usd: float = 5.0
    budget_utilization: float = 0.0    # 0.0 - 1.0
    last_activity_ts: float = 0.0
    current_task_id: Optional[str] = None
    specializations: list[str] = field(default_factory=list)
    consecutive_failures: int = 0
    uptime_seconds: float = 0.0

    @property
    def is_stale(self) -> bool:
        """Agent hasn't reported in over 10 minutes."""
        return (time.time() - self.last_activity_ts) > 600 if self.last_activity_ts > 0 else True

    @property
    def budget_headroom_usd(self) -> float:
        return max(0, self.daily_budget_usd - self.daily_spend_usd)


@dataclass
class PipelineMetrics:
    """Task pipeline flow metrics."""
    queued: int = 0
    scheduling: int = 0
    assigned: int = 0
    in_progress: int = 0
    pending_review: int = 0
    completed_today: int = 0
    failed_today: int = 0
    expired_today: int = 0
    throughput_per_hour: float = 0.0   # Tasks completed per hour (rolling 1h)
    avg_queue_wait_s: float = 0.0      # Average time in queue before assignment
    avg_completion_s: float = 0.0      # Average time from assignment to completion
    sla_adherence: float = 1.0         # Fraction of tasks completed before deadline

    @property
    def total_active(self) -> int:
        return self.queued + self.scheduling + self.assigned + self.in_progress

    @property
    def total_resolved_today(self) -> int:
        return self.completed_today + self.failed_today + self.expired_today


@dataclass
class BudgetSummary:
    """Fleet-wide budget status."""
    total_daily_budget_usd: float = 120.0   # 24 agents × $5/day default
    total_spent_today_usd: float = 0.0
    projected_daily_usd: float = 0.0        # Based on current burn rate
    agents_over_budget: int = 0
    agents_near_budget: int = 0              # >80% utilized
    burn_rate_per_hour_usd: float = 0.0
    hours_until_exhaustion: float = float("inf")

    @property
    def utilization(self) -> float:
        if self.total_daily_budget_usd <= 0:
            return 0.0
        return min(1.0, self.total_spent_today_usd / self.total_daily_budget_usd)


@dataclass
class CoordinationHealth:
    """Acontext / IRC coordination status."""
    irc_connected: bool = False
    active_locks: int = 0
    stale_locks: int = 0                    # Locks held >5 min without activity
    lock_contentions_1h: int = 0            # Times two agents tried same worker
    avg_lock_duration_s: float = 0.0
    agents_online: int = 0                  # Agents seen on IRC in last 5 min
    last_heartbeat_ts: float = 0.0
    message_rate_per_min: float = 0.0


@dataclass
class CategoryHeatmapEntry:
    """Per-agent per-category performance."""
    agent_id: str
    category: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_quality: float = 0.0
    avg_duration_s: float = 0.0

    @property
    def success_rate(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        return self.tasks_completed / total if total > 0 else 0.0


@dataclass
class DashboardAlert:
    """Prioritized actionable alert."""
    severity: Severity
    title: str
    message: str
    agent_id: Optional[str] = None
    category: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    action_required: str = ""
    auto_resolvable: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class SLAMetrics:
    """Service Level Agreement tracking."""
    total_tasks_with_deadline: int = 0
    tasks_met_deadline: int = 0
    tasks_missed_deadline: int = 0
    avg_deadline_margin_s: float = 0.0     # Avg time before deadline when completed
    worst_overdue_s: float = 0.0           # Worst deadline violation

    @property
    def adherence_rate(self) -> float:
        total = self.tasks_met_deadline + self.tasks_missed_deadline
        return self.tasks_met_deadline / total if total > 0 else 1.0


@dataclass
class DashboardSnapshot:
    """Complete fleet health snapshot at a point in time."""
    timestamp: float = field(default_factory=time.time)
    fleet_status: FleetStatus = FleetStatus.HEALTHY
    agent_count: int = 0
    agents_operational: int = 0
    agents_working: int = 0
    agents_idle: int = 0
    agents_degraded: int = 0
    agents_suspended: int = 0
    pipeline: PipelineMetrics = field(default_factory=PipelineMetrics)
    budget: BudgetSummary = field(default_factory=BudgetSummary)
    coordination: CoordinationHealth = field(default_factory=CoordinationHealth)
    sla: SLAMetrics = field(default_factory=SLAMetrics)
    agent_statuses: list[AgentStatus] = field(default_factory=list)
    heatmap: list[CategoryHeatmapEntry] = field(default_factory=list)
    alerts: list[DashboardAlert] = field(default_factory=list)
    uptime_seconds: float = 0.0

    @property
    def operational_rate(self) -> float:
        return self.agents_operational / self.agent_count if self.agent_count > 0 else 0.0

    def summary_line(self) -> str:
        """One-line summary for IRC broadcast."""
        return (
            f"[{self.fleet_status.value.upper()}] "
            f"{self.agents_operational}/{self.agent_count} agents | "
            f"{self.pipeline.completed_today} done, {self.pipeline.failed_today} failed | "
            f"${self.budget.total_spent_today_usd:.2f} spent | "
            f"{len([a for a in self.alerts if a.severity in (Severity.CRITICAL, Severity.EMERGENCY)])} critical alerts"
        )

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "fleet_status": self.fleet_status.value,
            "agent_count": self.agent_count,
            "agents_operational": self.agents_operational,
            "agents_working": self.agents_working,
            "agents_idle": self.agents_idle,
            "agents_degraded": self.agents_degraded,
            "agents_suspended": self.agents_suspended,
            "operational_rate": round(self.operational_rate, 3),
            "pipeline": asdict(self.pipeline),
            "budget": asdict(self.budget),
            "coordination": asdict(self.coordination),
            "sla": asdict(self.sla),
            "alert_count": len(self.alerts),
            "critical_alerts": len([a for a in self.alerts if a.severity in (Severity.CRITICAL, Severity.EMERGENCY)]),
            "uptime_seconds": self.uptime_seconds,
        }


@dataclass
class HealthReport:
    """Condensed health report for notifications."""
    fleet_status: FleetStatus
    summary: str
    critical_alerts: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


# ──────────────────────────────────────────────────────────────
# Dashboard Engine
# ──────────────────────────────────────────────────────────────


class SwarmDashboard:
    """
    Real-time fleet health monitoring for the KarmaCadabra V2 swarm.

    Pulls data from existing swarm modules and produces unified
    DashboardSnapshot reports. Designed to be called periodically
    (every 30s-60s) from the SwarmRunner or HeartbeatHandler.
    """

    # Thresholds
    STALE_AGENT_TIMEOUT_S = 600       # 10 min without activity = stale
    BUDGET_WARNING_THRESHOLD = 0.80   # 80% budget utilized = warning
    FAILURE_STREAK_WARNING = 3        # 3 consecutive failures = warning
    FAILURE_STREAK_CRITICAL = 5       # 5 consecutive failures = critical
    SLA_WARNING_THRESHOLD = 0.90      # <90% SLA adherence = warning
    SLA_CRITICAL_THRESHOLD = 0.75     # <75% SLA adherence = critical
    LOCK_STALE_TIMEOUT_S = 300        # 5 min lock without activity = stale

    def __init__(self):
        self._start_time = time.time()
        self._agent_events: dict[str, list[dict]] = defaultdict(list)
        self._pipeline_events: list[dict] = []
        self._lock_events: list[dict] = []
        self._agent_states: dict[str, str] = {}
        self._agent_budgets: dict[str, tuple[float, float]] = {}  # agent -> (spent, limit)
        self._agent_tasks: dict[str, Optional[str]] = {}  # agent -> current task
        self._agent_specializations: dict[str, list[str]] = {}
        self._agent_start_times: dict[str, float] = {}
        self._irc_connected = False
        self._active_locks: dict[str, dict] = {}  # worker_id -> {agent, ts, task}
        self._contention_count_1h = 0
        self._agents_seen_irc: dict[str, float] = {}  # agent -> last seen ts
        self._message_timestamps: list[float] = []  # IRC message timestamps for rate calc
        self._deadline_results: list[dict] = []  # {met: bool, margin_s: float}
        self._alert_history: list[DashboardAlert] = []

    # ──────── Data Ingestion ────────

    def register_agent(self, agent_id: str, budget_limit_usd: float = 5.0,
                       specializations: Optional[list[str]] = None):
        """Register an agent in the dashboard."""
        if agent_id not in self._agent_states:
            self._agent_states[agent_id] = "idle"
        self._agent_budgets[agent_id] = (
            self._agent_budgets.get(agent_id, (0.0, budget_limit_usd))[0],
            budget_limit_usd,
        )
        if specializations:
            self._agent_specializations[agent_id] = specializations
        if agent_id not in self._agent_start_times:
            self._agent_start_times[agent_id] = time.time()

    def update_agent_state(self, agent_id: str, state: str, task_id: Optional[str] = None):
        """Update agent lifecycle state."""
        self._agent_states[agent_id] = state
        if task_id is not None:
            self._agent_tasks[agent_id] = task_id
        elif state in ("idle", "suspended", "degraded"):
            self._agent_tasks[agent_id] = None

    def record_task_event(self, agent_id: str, task_id: str, event_type: str,
                          category: str = "", bounty_usd: float = 0.0,
                          quality: float = 0.0, duration_s: float = 0.0,
                          deadline_ts: Optional[float] = None):
        """Record a task lifecycle event."""
        event = {
            "agent_id": agent_id,
            "task_id": task_id,
            "event_type": event_type,
            "category": category,
            "bounty_usd": bounty_usd,
            "quality": quality,
            "duration_s": duration_s,
            "timestamp": time.time(),
        }
        self._agent_events[agent_id].append(event)
        self._pipeline_events.append(event)

        # Track budget
        if event_type == "task_completed" and bounty_usd > 0:
            spent, limit = self._agent_budgets.get(agent_id, (0.0, 5.0))
            self._agent_budgets[agent_id] = (spent + bounty_usd, limit)

        # Track SLA
        if deadline_ts and event_type in ("task_completed", "task_failed"):
            completed_at = time.time()
            met = completed_at <= deadline_ts
            margin = deadline_ts - completed_at
            self._deadline_results.append({"met": met, "margin_s": margin})

    def record_lock_event(self, event_type: str, worker_id: str,
                          agent_id: str = "", task_type: str = ""):
        """Record an Acontext lock event."""
        now = time.time()
        if event_type == "lock":
            if worker_id in self._active_locks and self._active_locks[worker_id]["agent"] != agent_id:
                self._contention_count_1h += 1
            self._active_locks[worker_id] = {"agent": agent_id, "ts": now, "task": task_type}
        elif event_type == "release":
            self._active_locks.pop(worker_id, None)
        self._lock_events.append({"type": event_type, "worker": worker_id,
                                   "agent": agent_id, "ts": now})

    def record_irc_activity(self, agent_id: str):
        """Record that an agent was seen on IRC."""
        now = time.time()
        self._agents_seen_irc[agent_id] = now
        self._message_timestamps.append(now)
        # Clean old timestamps (keep last hour)
        cutoff = now - 3600
        self._message_timestamps = [t for t in self._message_timestamps if t > cutoff]

    def set_irc_connected(self, connected: bool):
        """Update IRC connection status."""
        self._irc_connected = connected

    # ──────── Snapshot Generation ────────

    def generate_snapshot(self) -> DashboardSnapshot:
        """Generate a complete fleet health snapshot."""
        now = time.time()
        today_start = _today_start_ts()

        # Build per-agent statuses
        agent_statuses = []
        for agent_id in sorted(self._agent_states.keys()):
            status = self._build_agent_status(agent_id, now, today_start)
            agent_statuses.append(status)

        # Count states
        states = [s.state for s in agent_statuses]
        operational_states = {"idle", "active", "working", "cooldown"}
        agents_operational = sum(1 for s in states if s in operational_states)
        agents_working = sum(1 for s in states if s == "working")
        agents_idle = sum(1 for s in states if s in ("idle", "active"))
        agents_degraded = sum(1 for s in states if s == "degraded")
        agents_suspended = sum(1 for s in states if s == "suspended")

        # Pipeline metrics
        pipeline = self._build_pipeline_metrics(now, today_start)

        # Budget summary
        budget = self._build_budget_summary(agent_statuses, now, today_start)

        # Coordination health
        coordination = self._build_coordination_health(now)

        # SLA metrics
        sla = self._build_sla_metrics()

        # Heatmap
        heatmap = self._build_heatmap(today_start)

        # Generate alerts
        alerts = self._generate_alerts(agent_statuses, pipeline, budget, coordination, sla, now)

        # Fleet status
        agent_count = len(agent_statuses) if agent_statuses else 0
        fleet_status = self._assess_fleet_status(
            agent_count, agents_operational, alerts
        )

        snapshot = DashboardSnapshot(
            timestamp=now,
            fleet_status=fleet_status,
            agent_count=agent_count,
            agents_operational=agents_operational,
            agents_working=agents_working,
            agents_idle=agents_idle,
            agents_degraded=agents_degraded,
            agents_suspended=agents_suspended,
            pipeline=pipeline,
            budget=budget,
            coordination=coordination,
            sla=sla,
            agent_statuses=agent_statuses,
            heatmap=heatmap,
            alerts=alerts,
            uptime_seconds=now - self._start_time,
        )

        self._alert_history.extend(alerts)
        return snapshot

    def generate_health_report(self) -> HealthReport:
        """Generate a condensed health report for notifications."""
        snapshot = self.generate_snapshot()

        critical = [a.message for a in snapshot.alerts
                    if a.severity in (Severity.CRITICAL, Severity.EMERGENCY)]

        recommendations = []
        if snapshot.agents_degraded > 0:
            recommendations.append(
                f"Investigate {snapshot.agents_degraded} degraded agent(s) — check heartbeats and error logs"
            )
        if snapshot.budget.agents_over_budget > 0:
            recommendations.append(
                f"Review {snapshot.budget.agents_over_budget} agent(s) over daily budget"
            )
        if snapshot.coordination.stale_locks > 0:
            recommendations.append(
                f"Clean up {snapshot.coordination.stale_locks} stale worker lock(s)"
            )
        if snapshot.sla.adherence_rate < self.SLA_WARNING_THRESHOLD:
            recommendations.append(
                f"SLA adherence at {snapshot.sla.adherence_rate:.0%} — review task deadlines and agent capacity"
            )
        if snapshot.pipeline.expired_today > 0:
            recommendations.append(
                f"{snapshot.pipeline.expired_today} tasks expired today — consider increasing agent capacity or adjusting deadlines"
            )

        return HealthReport(
            fleet_status=snapshot.fleet_status,
            summary=snapshot.summary_line(),
            critical_alerts=critical,
            recommendations=recommendations,
        )

    # ──────── Internal Builders ────────

    def _build_agent_status(self, agent_id: str, now: float,
                            today_start: float) -> AgentStatus:
        """Build status for a single agent."""
        events = self._agent_events.get(agent_id, [])
        today_events = [e for e in events if e["timestamp"] >= today_start]

        completed = [e for e in today_events if e["event_type"] == "task_completed"]
        failed = [e for e in today_events if e["event_type"] == "task_failed"]

        tasks_completed = len(completed)
        tasks_failed = len(failed)
        total = tasks_completed + tasks_failed
        success_rate = tasks_completed / total if total > 0 else 0.0

        avg_time = 0.0
        if completed:
            avg_time = sum(e["duration_s"] for e in completed) / len(completed)

        avg_quality = 0.0
        if completed:
            qualities = [e["quality"] for e in completed if e["quality"] > 0]
            if qualities:
                avg_quality = sum(qualities) / len(qualities)

        spent, limit = self._agent_budgets.get(agent_id, (0.0, 5.0))
        utilization = min(1.0, spent / limit) if limit > 0 else 0.0

        last_activity = max((e["timestamp"] for e in events), default=0.0)

        # Consecutive failures (look backward from most recent)
        consecutive_failures = 0
        for e in reversed(events):
            if e["event_type"] == "task_failed":
                consecutive_failures += 1
            elif e["event_type"] == "task_completed":
                break

        # Health score: weighted composite
        health = self._compute_health_score(
            success_rate, utilization, consecutive_failures, now, last_activity
        )

        start_time = self._agent_start_times.get(agent_id, now)

        return AgentStatus(
            agent_id=agent_id,
            state=self._agent_states.get(agent_id, "unknown"),
            health_score=round(health, 3),
            tasks_completed_today=tasks_completed,
            tasks_failed_today=tasks_failed,
            success_rate=round(success_rate, 3),
            avg_completion_time_s=round(avg_time, 1),
            daily_spend_usd=round(spent, 2),
            daily_budget_usd=limit,
            budget_utilization=round(utilization, 3),
            last_activity_ts=last_activity,
            current_task_id=self._agent_tasks.get(agent_id),
            specializations=self._agent_specializations.get(agent_id, []),
            consecutive_failures=consecutive_failures,
            uptime_seconds=round(now - start_time, 1),
        )

    def _compute_health_score(self, success_rate: float, budget_util: float,
                              consecutive_failures: int, now: float,
                              last_activity: float) -> float:
        """Compute agent health score (0.0-1.0)."""
        # Base: success rate (40%)
        score = success_rate * 0.4

        # Budget health (20%): penalize over-budget, reward headroom
        budget_health = max(0, 1.0 - budget_util)
        score += budget_health * 0.2

        # Freshness (20%): penalize stale agents
        if last_activity > 0:
            staleness = (now - last_activity) / self.STALE_AGENT_TIMEOUT_S
            freshness = max(0, 1.0 - staleness)
        else:
            freshness = 0.0
        score += freshness * 0.2

        # Reliability (20%): penalize consecutive failures
        if consecutive_failures >= self.FAILURE_STREAK_CRITICAL:
            reliability = 0.0
        elif consecutive_failures >= self.FAILURE_STREAK_WARNING:
            reliability = 0.3
        elif consecutive_failures >= 1:
            reliability = 0.7
        else:
            reliability = 1.0
        score += reliability * 0.2

        return min(1.0, max(0.0, score))

    def _build_pipeline_metrics(self, now: float, today_start: float) -> PipelineMetrics:
        """Build task pipeline metrics."""
        today_events = [e for e in self._pipeline_events if e["timestamp"] >= today_start]

        completed = [e for e in today_events if e["event_type"] == "task_completed"]
        failed = [e for e in today_events if e["event_type"] == "task_failed"]
        expired = [e for e in today_events if e["event_type"] == "task_expired"]
        assigned = [e for e in today_events if e["event_type"] == "task_assigned"]

        # Throughput: completions in last hour
        one_hour_ago = now - 3600
        recent_completed = [e for e in completed if e["timestamp"] > one_hour_ago]
        throughput = len(recent_completed)

        # Average durations
        avg_completion = 0.0
        if completed:
            durations = [e["duration_s"] for e in completed if e["duration_s"] > 0]
            if durations:
                avg_completion = sum(durations) / len(durations)

        # In-progress: agents currently working
        in_progress = sum(1 for t in self._agent_tasks.values() if t is not None)

        return PipelineMetrics(
            queued=0,  # Would come from scheduler queue
            in_progress=in_progress,
            completed_today=len(completed),
            failed_today=len(failed),
            expired_today=len(expired),
            throughput_per_hour=throughput,
            avg_completion_s=round(avg_completion, 1),
            sla_adherence=self._build_sla_metrics().adherence_rate,
        )

    def _build_budget_summary(self, agents: list[AgentStatus], now: float,
                              today_start: float) -> BudgetSummary:
        """Build fleet-wide budget summary."""
        total_budget = sum(a.daily_budget_usd for a in agents) if agents else 0.0
        total_spent = sum(a.daily_spend_usd for a in agents) if agents else 0.0
        over_budget = sum(1 for a in agents if a.daily_spend_usd > a.daily_budget_usd)
        near_budget = sum(1 for a in agents if a.budget_utilization >= self.BUDGET_WARNING_THRESHOLD
                         and a.daily_spend_usd <= a.daily_budget_usd)

        hours_elapsed = max(0.1, (now - today_start) / 3600)
        burn_rate = total_spent / hours_elapsed
        remaining = max(0, total_budget - total_spent)
        hours_left = remaining / burn_rate if burn_rate > 0 else float("inf")
        projected = burn_rate * 24

        return BudgetSummary(
            total_daily_budget_usd=round(total_budget, 2),
            total_spent_today_usd=round(total_spent, 2),
            projected_daily_usd=round(projected, 2),
            agents_over_budget=over_budget,
            agents_near_budget=near_budget,
            burn_rate_per_hour_usd=round(burn_rate, 2),
            hours_until_exhaustion=round(hours_left, 1) if hours_left < 1e6 else float("inf"),
        )

    def _build_coordination_health(self, now: float) -> CoordinationHealth:
        """Build Acontext coordination health metrics."""
        stale_locks = sum(
            1 for lock in self._active_locks.values()
            if (now - lock["ts"]) > self.LOCK_STALE_TIMEOUT_S
        )

        agents_online = sum(
            1 for ts in self._agents_seen_irc.values()
            if (now - ts) <= 300
        )

        avg_duration = 0.0
        completed_locks = [e for e in self._lock_events if e["type"] == "release"]
        if completed_locks:
            durations = []
            for release in completed_locks:
                # Find corresponding lock
                for lock in reversed(self._lock_events):
                    if lock["type"] == "lock" and lock["worker"] == release["worker"] and lock["ts"] < release["ts"]:
                        durations.append(release["ts"] - lock["ts"])
                        break
            if durations:
                avg_duration = sum(durations) / len(durations)

        recent_messages = [t for t in self._message_timestamps if (now - t) <= 60]
        msg_rate = len(recent_messages)

        return CoordinationHealth(
            irc_connected=self._irc_connected,
            active_locks=len(self._active_locks),
            stale_locks=stale_locks,
            lock_contentions_1h=self._contention_count_1h,
            avg_lock_duration_s=round(avg_duration, 1),
            agents_online=agents_online,
            last_heartbeat_ts=max(self._agents_seen_irc.values(), default=0.0),
            message_rate_per_min=msg_rate,
        )

    def _build_sla_metrics(self) -> SLAMetrics:
        """Build SLA tracking metrics."""
        if not self._deadline_results:
            return SLAMetrics()

        met = sum(1 for r in self._deadline_results if r["met"])
        missed = sum(1 for r in self._deadline_results if not r["met"])
        margins = [r["margin_s"] for r in self._deadline_results]
        avg_margin = sum(margins) / len(margins) if margins else 0.0
        worst_overdue = min(margins) if margins else 0.0  # Most negative = worst

        return SLAMetrics(
            total_tasks_with_deadline=len(self._deadline_results),
            tasks_met_deadline=met,
            tasks_missed_deadline=missed,
            avg_deadline_margin_s=round(avg_margin, 1),
            worst_overdue_s=round(abs(min(0, worst_overdue)), 1),
        )

    def _build_heatmap(self, today_start: float) -> list[CategoryHeatmapEntry]:
        """Build per-agent × per-category performance heatmap."""
        entries: dict[tuple[str, str], CategoryHeatmapEntry] = {}

        for agent_id, events in self._agent_events.items():
            for e in events:
                if e["timestamp"] < today_start or not e.get("category"):
                    continue
                key = (agent_id, e["category"])
                if key not in entries:
                    entries[key] = CategoryHeatmapEntry(
                        agent_id=agent_id, category=e["category"]
                    )
                entry = entries[key]
                if e["event_type"] == "task_completed":
                    entry.tasks_completed += 1
                    if e.get("quality", 0) > 0:
                        # Running average
                        total = entry.tasks_completed
                        entry.avg_quality = (
                            (entry.avg_quality * (total - 1) + e["quality"]) / total
                        )
                    if e.get("duration_s", 0) > 0:
                        total = entry.tasks_completed
                        entry.avg_duration_s = (
                            (entry.avg_duration_s * (total - 1) + e["duration_s"]) / total
                        )
                elif e["event_type"] == "task_failed":
                    entry.tasks_failed += 1

        return sorted(entries.values(), key=lambda x: (x.agent_id, x.category))

    # ──────── Alert Generation ────────

    def _generate_alerts(self, agents: list[AgentStatus], pipeline: PipelineMetrics,
                         budget: BudgetSummary, coordination: CoordinationHealth,
                         sla: SLAMetrics, now: float) -> list[DashboardAlert]:
        """Generate prioritized alerts based on current state."""
        alerts = []

        # Per-agent alerts
        for agent in agents:
            if agent.consecutive_failures >= self.FAILURE_STREAK_CRITICAL:
                alerts.append(DashboardAlert(
                    severity=Severity.CRITICAL,
                    title=f"Agent {agent.agent_id} failure streak",
                    message=f"{agent.consecutive_failures} consecutive failures. Agent may be misconfigured or encountering systematic errors.",
                    agent_id=agent.agent_id,
                    action_required="Investigate error logs and consider suspending agent",
                ))
            elif agent.consecutive_failures >= self.FAILURE_STREAK_WARNING:
                alerts.append(DashboardAlert(
                    severity=Severity.WARNING,
                    title=f"Agent {agent.agent_id} failing",
                    message=f"{agent.consecutive_failures} consecutive failures.",
                    agent_id=agent.agent_id,
                    action_required="Monitor next task attempt",
                    auto_resolvable=True,
                ))

            if agent.daily_spend_usd > agent.daily_budget_usd:
                alerts.append(DashboardAlert(
                    severity=Severity.WARNING,
                    title=f"Agent {agent.agent_id} over budget",
                    message=f"${agent.daily_spend_usd:.2f} spent vs ${agent.daily_budget_usd:.2f} limit",
                    agent_id=agent.agent_id,
                    action_required="Review budget allocation or pause agent",
                ))

            if agent.is_stale and agent.state not in ("suspended", "initializing"):
                alerts.append(DashboardAlert(
                    severity=Severity.WARNING,
                    title=f"Agent {agent.agent_id} unresponsive",
                    message=f"No activity for {int((now - agent.last_activity_ts) / 60)} minutes",
                    agent_id=agent.agent_id,
                    action_required="Check agent health and restart if needed",
                    auto_resolvable=True,
                ))

        # Fleet-wide alerts
        if budget.agents_over_budget > len(agents) * 0.25:
            alerts.append(DashboardAlert(
                severity=Severity.CRITICAL,
                title="Fleet budget crisis",
                message=f"{budget.agents_over_budget} agents over daily budget",
                action_required="Review fleet budget strategy",
            ))

        if coordination.stale_locks > 0:
            alerts.append(DashboardAlert(
                severity=Severity.WARNING,
                title="Stale worker locks",
                message=f"{coordination.stale_locks} lock(s) held >5 minutes without activity",
                action_required="Force-release stale locks to unblock worker assignment",
                auto_resolvable=True,
            ))

        if not coordination.irc_connected and len(agents) > 1:
            alerts.append(DashboardAlert(
                severity=Severity.WARNING,
                title="IRC coordination offline",
                message="Acontext not connected — agents cannot coordinate hiring",
                action_required="Reconnect to MeshRelay IRC",
            ))

        if sla.adherence_rate < self.SLA_CRITICAL_THRESHOLD:
            alerts.append(DashboardAlert(
                severity=Severity.CRITICAL,
                title="SLA critically degraded",
                message=f"Only {sla.adherence_rate:.0%} of deadlined tasks completed on time",
                action_required="Increase agent capacity or extend deadlines",
            ))
        elif sla.adherence_rate < self.SLA_WARNING_THRESHOLD:
            alerts.append(DashboardAlert(
                severity=Severity.WARNING,
                title="SLA degrading",
                message=f"{sla.adherence_rate:.0%} deadline adherence (target: 90%+)",
                action_required="Monitor task throughput",
                auto_resolvable=True,
            ))

        if pipeline.expired_today > pipeline.completed_today and pipeline.completed_today > 0:
            alerts.append(DashboardAlert(
                severity=Severity.WARNING,
                title="High task expiry rate",
                message=f"{pipeline.expired_today} expired vs {pipeline.completed_today} completed today",
                action_required="Review task deadlines and agent assignment speed",
            ))

        # Sort by severity (emergency first)
        severity_order = {Severity.EMERGENCY: 0, Severity.CRITICAL: 1,
                          Severity.WARNING: 2, Severity.INFO: 3}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 99))

        return alerts

    def _assess_fleet_status(self, total: int, operational: int,
                             alerts: list[DashboardAlert]) -> FleetStatus:
        """Determine overall fleet health status."""
        if total == 0:
            return FleetStatus.DOWN

        op_rate = operational / total
        has_emergency = any(a.severity == Severity.EMERGENCY for a in alerts)
        has_critical = any(a.severity == Severity.CRITICAL for a in alerts)

        if has_emergency or op_rate < 0.25:
            return FleetStatus.DOWN
        if has_critical or op_rate < 0.50:
            return FleetStatus.IMPAIRED
        if op_rate < 0.80 or any(a.severity == Severity.WARNING for a in alerts):
            return FleetStatus.DEGRADED
        return FleetStatus.HEALTHY

    # ──────── Utilities ────────

    def get_agent_ids(self) -> list[str]:
        """Get all registered agent IDs."""
        return sorted(self._agent_states.keys())

    def get_top_performers(self, n: int = 5) -> list[AgentStatus]:
        """Get top N agents by health score."""
        snapshot = self.generate_snapshot()
        return sorted(snapshot.agent_statuses, key=lambda a: a.health_score, reverse=True)[:n]

    def get_struggling_agents(self) -> list[AgentStatus]:
        """Get agents that need attention."""
        snapshot = self.generate_snapshot()
        return [a for a in snapshot.agent_statuses
                if a.health_score < 0.5 or a.consecutive_failures >= self.FAILURE_STREAK_WARNING]

    def reset_daily_counters(self):
        """Reset daily counters (call at midnight)."""
        for agent_id in self._agent_budgets:
            _, limit = self._agent_budgets[agent_id]
            self._agent_budgets[agent_id] = (0.0, limit)
        self._contention_count_1h = 0
        self._deadline_results.clear()


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────


def _today_start_ts() -> float:
    """Get timestamp for start of today (UTC)."""
    now = datetime.now(timezone.utc)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.timestamp()
