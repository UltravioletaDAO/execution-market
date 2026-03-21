"""
Capacity Planner — Swarm Workforce Intelligence
=================================================

Forecasts skill gaps, capacity needs, and bottlenecks in the worker
pool. The swarm coordinator uses this to proactively recruit before
demand spikes, identify single-point-of-failure workers, and balance
workload distribution.

Core analyses:
    1. SkillGapAnalysis: What skills does the pool lack?
    2. CapacityForecast: Can the pool handle projected task volume?
    3. ConcentrationRisk: Are we over-reliant on one worker?
    4. WorkloadBalance: How evenly is work distributed?
    5. RecruitmentPlan: Who should we recruit next?

Usage:
    from swarm.capacity_planner import CapacityPlanner

    planner = CapacityPlanner()
    gap = planner.analyze_skill_gaps(agents, recent_tasks)
    risk = planner.concentration_risk(agents, recent_tasks)
    plan = planner.recruitment_plan(agents, task_forecast)
"""

import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import timezone
from typing import Optional

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Minimum tasks a skill appears in to be considered "in demand"
MIN_DEMAND_THRESHOLD = 2

# Maximum acceptable concentration ratio for a single worker
MAX_HEALTHY_CONCENTRATION = 0.50  # No worker should do >50% of tasks

# Target utilization range (below = underutilized, above = overloaded)
TARGET_UTILIZATION_LOW = 0.3
TARGET_UTILIZATION_HIGH = 0.8

# Tasks per worker per day capacity estimate
DEFAULT_TASKS_PER_WORKER_PER_DAY = 3

# Recruitment urgency thresholds
URGENCY_CRITICAL = 0.9
URGENCY_HIGH = 0.7
URGENCY_MEDIUM = 0.4


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


@dataclass
class SkillDemand:
    """Demand profile for a single skill."""

    skill: str
    demand_count: int  # How many tasks needed this skill
    supply_count: int  # How many agents have this skill
    gap: int  # demand - supply (positive = shortage)
    coverage_ratio: float  # supply / demand (0-inf, <1 = shortage)
    avg_quality: float  # Average skill quality among agents (0-1)
    severity: str = ""  # Computed post-init
    is_critical: bool = False  # Computed post-init

    def __post_init__(self):
        self.is_critical = self.supply_count == 0 and self.demand_count > 0
        if self.supply_count == 0 and self.demand_count > 0:
            self.severity = "critical"
        elif self.coverage_ratio < 0.5:
            self.severity = "high"
        elif self.coverage_ratio < 1.0:
            self.severity = "medium"
        else:
            self.severity = "healthy"


@dataclass
class ConcentrationReport:
    """Worker concentration risk assessment."""

    total_tasks: int
    total_workers: int
    active_workers: int
    herfindahl_index: float  # 0-1, higher = more concentrated
    top_worker_share: float  # Share of top worker (0-1)
    top_worker_wallet: Optional[str] = None
    gini_coefficient: float = 0.0
    risk_level: str = "unknown"  # healthy, moderate, high, critical
    recommendations: list = field(default_factory=list)


@dataclass
class CapacityEstimate:
    """Capacity forecast result."""

    current_capacity_daily: float  # Tasks/day the pool can handle
    projected_demand_daily: float  # Forecasted tasks/day
    utilization: float  # demand / capacity (0-inf)
    headroom: float  # capacity - demand
    workers_needed: int  # Additional workers to meet demand
    status: str  # "surplus", "balanced", "shortage", "critical"
    bottleneck_skills: list = field(default_factory=list)


@dataclass
class RecruitmentTarget:
    """A specific recruitment recommendation."""

    skill: str
    priority: str  # critical, high, medium, low
    urgency_score: float  # 0-1
    current_supply: int
    gap_size: int
    reason: str


@dataclass
class WorkloadEntry:
    """Single worker's workload stats."""

    wallet: str
    task_count: int
    share: float  # Fraction of total tasks
    categories: list = field(default_factory=list)
    is_overloaded: bool = False
    is_underutilized: bool = False


# ---------------------------------------------------------------------------
# Capacity Planner
# ---------------------------------------------------------------------------


class CapacityPlanner:
    """Workforce intelligence engine for the swarm.

    Analyzes the gap between what the swarm needs and what it has,
    then produces actionable plans to close those gaps.
    """

    def __init__(
        self,
        tasks_per_worker_per_day: float = DEFAULT_TASKS_PER_WORKER_PER_DAY,
    ):
        self.tasks_per_worker_per_day = tasks_per_worker_per_day

    # -------------------------------------------------------------------
    # 1. Skill Gap Analysis
    # -------------------------------------------------------------------

    def analyze_skill_gaps(
        self,
        agents: list,
        recent_tasks: list,
    ) -> dict:
        """Identify skills where demand exceeds supply.

        Args:
            agents: List of agent dicts with 'skills' or 'capabilities'
            recent_tasks: List of task dicts with 'category', 'required_skills'

        Returns:
            Dict with skill_demands, critical_gaps, overall_coverage
        """
        # Build demand profile
        skill_demand = Counter()
        for task in recent_tasks:
            skills = self._extract_task_skills(task)
            for skill in skills:
                skill_demand[skill] += 1

        # Build supply profile
        skill_supply = Counter()
        skill_quality = defaultdict(list)
        for agent in agents:
            agent_skills = self._extract_agent_skills(agent)
            for skill, quality in agent_skills.items():
                skill_supply[skill] += 1
                skill_quality[skill].append(quality)

        # Compute gaps
        all_skills = set(skill_demand.keys()) | set(skill_supply.keys())
        demands = []
        for skill in sorted(all_skills):
            demand = skill_demand.get(skill, 0)
            supply = skill_supply.get(skill, 0)
            qualities = skill_quality.get(skill, [])
            avg_q = sum(qualities) / len(qualities) if qualities else 0.0

            demands.append(
                SkillDemand(
                    skill=skill,
                    demand_count=demand,
                    supply_count=supply,
                    gap=max(0, demand - supply),
                    coverage_ratio=supply / demand if demand > 0 else float("inf"),
                    avg_quality=round(avg_q, 3),
                )
            )

        # Sort by severity (critical first)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "healthy": 3}
        demands.sort(key=lambda d: (severity_order.get(d.severity, 4), -d.demand_count))

        critical = [d for d in demands if d.severity == "critical"]
        in_demand = [d for d in demands if d.demand_count >= MIN_DEMAND_THRESHOLD]
        covered = [d for d in in_demand if d.coverage_ratio >= 1.0]

        return {
            "skill_demands": [asdict(d) for d in demands],
            "critical_gaps": [asdict(d) for d in critical],
            "critical_count": len(critical),
            "in_demand_skills": len(in_demand),
            "covered_skills": len(covered),
            "overall_coverage": (
                round(len(covered) / len(in_demand), 3) if in_demand else 1.0
            ),
            "total_skills_seen": len(all_skills),
        }

    # -------------------------------------------------------------------
    # 2. Capacity Forecast
    # -------------------------------------------------------------------

    def forecast_capacity(
        self,
        agents: list,
        projected_daily_tasks: float,
        active_fraction: float = 0.7,
    ) -> CapacityEstimate:
        """Forecast whether the pool can handle projected demand.

        Args:
            agents: List of agent dicts
            projected_daily_tasks: Expected tasks per day
            active_fraction: Fraction of agents likely active (0-1)

        Returns:
            CapacityEstimate with utilization and worker needs
        """
        total_agents = len(agents)
        active_agents = max(1, int(total_agents * active_fraction))
        capacity = active_agents * self.tasks_per_worker_per_day
        demand = projected_daily_tasks

        utilization = demand / capacity if capacity > 0 else float("inf")
        headroom = capacity - demand
        workers_needed = max(
            0, math.ceil((demand - capacity) / self.tasks_per_worker_per_day)
        )

        if utilization <= TARGET_UTILIZATION_LOW:
            status = "surplus"
        elif utilization <= TARGET_UTILIZATION_HIGH:
            status = "balanced"
        elif utilization <= 1.0:
            status = "tight"
        else:
            status = "shortage" if utilization <= 1.5 else "critical"

        return CapacityEstimate(
            current_capacity_daily=round(capacity, 1),
            projected_demand_daily=round(demand, 1),
            utilization=round(utilization, 3),
            headroom=round(headroom, 1),
            workers_needed=workers_needed,
            status=status,
        )

    # -------------------------------------------------------------------
    # 3. Concentration Risk
    # -------------------------------------------------------------------

    def concentration_risk(
        self,
        agents: list,
        recent_tasks: list,
    ) -> ConcentrationReport:
        """Assess how concentrated work is among workers.

        High concentration = single point of failure risk.
        Uses Herfindahl-Hirschman Index and Gini coefficient.
        """
        # Count tasks per worker
        worker_tasks = Counter()
        for task in recent_tasks:
            worker = (
                task.get("assigned_worker")
                or task.get("worker_wallet")
                or task.get("worker_id")
                or "unassigned"
            )
            if worker != "unassigned":
                worker_tasks[worker] += 1

        total_tasks = sum(worker_tasks.values())
        total_workers = len(agents)
        active_workers = len(worker_tasks)

        if total_tasks == 0:
            return ConcentrationReport(
                total_tasks=0,
                total_workers=total_workers,
                active_workers=0,
                herfindahl_index=0.0,
                top_worker_share=0.0,
                gini_coefficient=0.0,
                risk_level="no_data",
                recommendations=["Need task history to assess concentration"],
            )

        # Shares
        shares = [count / total_tasks for count in worker_tasks.values()]

        # Herfindahl-Hirschman Index (sum of squared shares)
        hhi = sum(s * s for s in shares)

        # Top worker
        top_worker, top_count = worker_tasks.most_common(1)[0]
        top_share = top_count / total_tasks

        # Gini coefficient
        gini = self._gini_coefficient(list(worker_tasks.values()))

        # Risk assessment
        recommendations = []
        if top_share > MAX_HEALTHY_CONCENTRATION:
            risk_level = "critical" if top_share > 0.8 else "high"
            recommendations.append(
                f"Top worker handles {top_share:.0%} of tasks — "
                f"recruit more workers with similar skills"
            )
        elif hhi > 0.25:
            risk_level = "moderate"
            recommendations.append("Work is moderately concentrated — diversify pool")
        else:
            risk_level = "healthy"

        if active_workers < 3 and total_tasks > 5:
            recommendations.append(
                f"Only {active_workers} active workers — minimum 3 recommended"
            )

        if active_workers > 0 and active_workers < total_workers * 0.3:
            recommendations.append(
                f"Only {active_workers}/{total_workers} workers are active — "
                f"investigate inactive workers"
            )

        return ConcentrationReport(
            total_tasks=total_tasks,
            total_workers=total_workers,
            active_workers=active_workers,
            herfindahl_index=round(hhi, 4),
            top_worker_share=round(top_share, 4),
            top_worker_wallet=top_worker,
            gini_coefficient=round(gini, 4),
            risk_level=risk_level,
            recommendations=recommendations,
        )

    # -------------------------------------------------------------------
    # 4. Workload Balance
    # -------------------------------------------------------------------

    def workload_balance(
        self,
        agents: list,
        recent_tasks: list,
    ) -> dict:
        """Analyze how evenly work is distributed.

        Returns per-worker stats and overall balance metrics.
        """
        # Count tasks per worker, track categories
        worker_tasks = defaultdict(lambda: {"count": 0, "categories": []})
        for task in recent_tasks:
            worker = (
                task.get("assigned_worker")
                or task.get("worker_wallet")
                or task.get("worker_id")
            )
            if worker:
                worker_tasks[worker]["count"] += 1
                cat = task.get("category", "unknown")
                if cat not in worker_tasks[worker]["categories"]:
                    worker_tasks[worker]["categories"].append(cat)

        total_tasks = sum(w["count"] for w in worker_tasks.values())
        avg_tasks = total_tasks / len(worker_tasks) if worker_tasks else 0

        entries = []
        for wallet, data in worker_tasks.items():
            share = data["count"] / total_tasks if total_tasks > 0 else 0
            entries.append(
                WorkloadEntry(
                    wallet=wallet,
                    task_count=data["count"],
                    share=round(share, 4),
                    categories=data["categories"],
                    is_overloaded=share > MAX_HEALTHY_CONCENTRATION,
                    is_underutilized=share < 0.05 and total_tasks > 10,
                )
            )

        entries.sort(key=lambda e: -e.task_count)

        # Compute balance score (0=perfectly unbalanced, 1=perfectly balanced)
        if len(entries) > 1:
            counts = [e.task_count for e in entries]
            cv = (
                statistics.stdev(counts) / statistics.mean(counts)
                if statistics.mean(counts) > 0
                else 0
            )
            balance_score = max(0, 1 - cv)
        elif len(entries) == 1:
            balance_score = 0.0  # Single worker = no balance
        else:
            balance_score = 1.0  # No tasks = perfectly balanced (vacuously)

        overloaded = [e for e in entries if e.is_overloaded]
        underutilized = [e for e in entries if e.is_underutilized]

        return {
            "workers": [asdict(e) for e in entries],
            "total_tasks": total_tasks,
            "active_workers": len(entries),
            "avg_tasks_per_worker": round(avg_tasks, 1),
            "balance_score": round(balance_score, 3),
            "overloaded_count": len(overloaded),
            "underutilized_count": len(underutilized),
        }

    # -------------------------------------------------------------------
    # 5. Recruitment Plan
    # -------------------------------------------------------------------

    def recruitment_plan(
        self,
        agents: list,
        recent_tasks: list,
        projected_daily_tasks: float = 10.0,
    ) -> dict:
        """Generate a prioritized recruitment plan.

        Combines skill gap analysis, concentration risk, and capacity
        forecasting into actionable recruitment targets.
        """
        # Run sub-analyses
        gaps = self.analyze_skill_gaps(agents, recent_tasks)
        capacity = self.forecast_capacity(agents, projected_daily_tasks)
        risk = self.concentration_risk(agents, recent_tasks)

        targets = []

        # From skill gaps
        for gap in gaps.get("critical_gaps", []):
            targets.append(
                RecruitmentTarget(
                    skill=gap["skill"],
                    priority="critical",
                    urgency_score=URGENCY_CRITICAL,
                    current_supply=gap["supply_count"],
                    gap_size=gap["gap"],
                    reason=f"Zero workers with '{gap['skill']}' — {gap['demand_count']} tasks need it",
                )
            )

        # High-gap skills
        for demand in gaps.get("skill_demands", []):
            if demand["severity"] == "high" and demand["skill"] not in [
                t.skill for t in targets
            ]:
                targets.append(
                    RecruitmentTarget(
                        skill=demand["skill"],
                        priority="high",
                        urgency_score=URGENCY_HIGH,
                        current_supply=demand["supply_count"],
                        gap_size=demand["gap"],
                        reason=f"Only {demand['supply_count']} workers for {demand['demand_count']} tasks",
                    )
                )

        # From capacity shortage
        if capacity.status in ("shortage", "critical"):
            targets.append(
                RecruitmentTarget(
                    skill="general",
                    priority="high" if capacity.status == "shortage" else "critical",
                    urgency_score=URGENCY_HIGH
                    if capacity.status == "shortage"
                    else URGENCY_CRITICAL,
                    current_supply=len(agents),
                    gap_size=capacity.workers_needed,
                    reason=f"Pool at {capacity.utilization:.0%} utilization — "
                    f"need {capacity.workers_needed} more workers",
                )
            )

        # From concentration risk
        if risk.risk_level in ("high", "critical"):
            targets.append(
                RecruitmentTarget(
                    skill="diversification",
                    priority="high",
                    urgency_score=URGENCY_HIGH,
                    current_supply=risk.active_workers,
                    gap_size=max(2, 3 - risk.active_workers),
                    reason=f"Top worker handles {risk.top_worker_share:.0%} — "
                    f"need diversification",
                )
            )

        # Sort by urgency
        targets.sort(key=lambda t: -t.urgency_score)

        return {
            "targets": [asdict(t) for t in targets],
            "total_targets": len(targets),
            "critical_count": sum(1 for t in targets if t.priority == "critical"),
            "capacity_status": capacity.status,
            "concentration_risk": risk.risk_level,
            "overall_coverage": gaps.get("overall_coverage", 0),
            "workers_needed": capacity.workers_needed,
        }

    # -------------------------------------------------------------------
    # Comprehensive Report
    # -------------------------------------------------------------------

    def full_report(
        self,
        agents: list,
        recent_tasks: list,
        projected_daily_tasks: float = 10.0,
    ) -> dict:
        """Generate a comprehensive workforce intelligence report.

        Combines all analyses into a single dashboard-ready output.
        """
        gaps = self.analyze_skill_gaps(agents, recent_tasks)
        capacity = self.forecast_capacity(agents, projected_daily_tasks)
        risk = self.concentration_risk(agents, recent_tasks)
        balance = self.workload_balance(agents, recent_tasks)
        plan = self.recruitment_plan(agents, recent_tasks, projected_daily_tasks)

        # Overall health score (0-100)
        health_components = [
            min(1.0, gaps.get("overall_coverage", 0)),
            1.0 - min(1.0, capacity.utilization)
            if capacity.utilization <= 1.0
            else 0.0,
            1.0
            if risk.risk_level == "healthy"
            else 0.5
            if risk.risk_level == "moderate"
            else 0.2,
            balance.get("balance_score", 0),
        ]
        health_score = round(sum(health_components) / len(health_components) * 100, 1)

        return {
            "health_score": health_score,
            "skill_gaps": gaps,
            "capacity": asdict(capacity),
            "concentration_risk": asdict(risk),
            "workload_balance": balance,
            "recruitment_plan": plan,
            "summary": {
                "total_agents": len(agents),
                "total_recent_tasks": len(recent_tasks),
                "critical_gaps": gaps.get("critical_count", 0),
                "capacity_status": capacity.status,
                "risk_level": risk.risk_level,
                "balance_score": balance.get("balance_score", 0),
                "health_score": health_score,
            },
        }

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    def _extract_task_skills(self, task: dict) -> list:
        """Extract required skills from a task."""
        skills = []

        # Direct skills field
        if "required_skills" in task:
            rs = task["required_skills"]
            if isinstance(rs, list):
                skills.extend(rs)
            elif isinstance(rs, dict):
                skills.extend(rs.keys())

        # Category-based skills
        category = task.get("category", "")
        if category:
            skills.append(category)

        # Title-based extraction (basic)
        title = task.get("title", "").lower()
        for kw in [
            "photo",
            "video",
            "verify",
            "deliver",
            "survey",
            "write",
            "research",
            "translate",
            "design",
            "code",
        ]:
            if kw in title:
                skills.append(kw)

        return list(set(s.lower().strip() for s in skills if s))

    def _extract_agent_skills(self, agent: dict) -> dict:
        """Extract skills and quality from an agent profile.

        Returns: {skill: quality_score (0-1)}
        """
        skills = {}

        # Direct skills dict
        agent_skills = agent.get("skills", agent.get("capabilities", {}))
        if isinstance(agent_skills, dict):
            for skill, data in agent_skills.items():
                if isinstance(data, dict):
                    # Quality from confidence or level
                    conf = data.get("confidence", 0.5)
                    level = data.get("level", "").upper()
                    level_scores = {
                        "EXPERT": 1.0,
                        "ADVANCED": 0.8,
                        "INTERMEDIATE": 0.6,
                        "BEGINNER": 0.3,
                    }
                    quality = max(conf, level_scores.get(level, 0.5))
                elif isinstance(data, (int, float)):
                    quality = min(1.0, data / 100 if data > 1 else data)
                else:
                    quality = 0.5
                skills[skill.lower().strip()] = quality
        elif isinstance(agent_skills, list):
            for s in agent_skills:
                skills[s.lower().strip()] = 0.5

        # Categories handled
        for cat in agent.get("categories", []):
            if isinstance(cat, str) and cat.lower() not in skills:
                skills[cat.lower()] = 0.5

        return skills

    @staticmethod
    def _gini_coefficient(values: list) -> float:
        """Compute Gini coefficient for a list of values.

        0 = perfect equality, 1 = perfect inequality.
        """
        if not values or all(v == 0 for v in values):
            return 0.0

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        total = sum(sorted_vals)

        if total == 0:
            return 0.0

        numerator = sum((2 * (i + 1) - n - 1) * v for i, v in enumerate(sorted_vals))
        return numerator / (n * total)
