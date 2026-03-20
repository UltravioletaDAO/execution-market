"""
WorkerDiscovery — Active Worker Recruitment & Supply Intelligence
==================================================================

The #1 problem for EM's swarm is worker supply. Currently 2 workers
handle 97% of tasks, and most task categories have zero coverage.

WorkerDiscovery addresses this by:

  1. **Demand Analysis**: Track which task categories/locations need workers
  2. **Coverage Mapping**: Identify geographic and skill gaps
  3. **Worker Scoring**: Score existing workers on reliability/availability
  4. **Recruitment Signals**: Generate actionable recruitment recommendations
  5. **Retention Tracking**: Monitor worker engagement and churn risk

This doesn't recruit workers directly (that's a human/marketing job),
but it provides the intelligence needed to recruit *the right* workers.

Architecture:
    TaskDemandTracker (what tasks need doing)
      + WorkerCoverageMap (who can do what, where)
      + RecruitmentEngine (where are the gaps?)
      = WorkerDiscovery (unified intelligence layer)

Thread-safe. No external dependencies.
"""

import logging
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger("em.swarm.worker_discovery")


# ─── Data Models ──────────────────────────────────────────────


@dataclass
class TaskDemandSignal:
    """A single task that indicates demand for a category/location."""

    task_id: str
    category: str
    location: str  # City/region or "remote"
    bounty_usd: float
    created_at: float = field(default_factory=time.time)
    status: str = "open"  # open, assigned, completed, expired
    time_to_assign_seconds: float | None = None  # How long to find a worker
    worker_wallet: str | None = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "category": self.category,
            "location": self.location,
            "bounty_usd": self.bounty_usd,
            "status": self.status,
            "time_to_assign_seconds": self.time_to_assign_seconds,
        }


@dataclass
class WorkerProfile:
    """Known worker with capabilities and performance history."""

    wallet: str
    name: str = ""
    categories: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    avg_rating: float = 0.0
    total_tasks: int = 0
    completed_tasks: int = 0
    response_time_avg_seconds: float = 0.0
    last_active: float = 0.0
    registered_at: float = field(default_factory=time.time)

    @property
    def completion_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.completed_tasks / self.total_tasks

    @property
    def is_active(self) -> bool:
        """Active if seen in last 7 days."""
        return (time.time() - self.last_active) < 7 * 86400

    @property
    def days_since_active(self) -> float:
        if self.last_active == 0:
            return float("inf")
        return (time.time() - self.last_active) / 86400

    @property
    def churn_risk(self) -> str:
        """Estimate churn risk based on activity."""
        days = self.days_since_active
        if days < 3:
            return "low"
        elif days < 7:
            return "medium"
        elif days < 14:
            return "high"
        else:
            return "churned"

    def to_dict(self) -> dict:
        return {
            "wallet": self.wallet,
            "name": self.name,
            "categories": self.categories,
            "locations": self.locations,
            "avg_rating": round(self.avg_rating, 2),
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "completion_rate": round(self.completion_rate * 100, 1),
            "response_time_avg_seconds": round(self.response_time_avg_seconds, 0),
            "is_active": self.is_active,
            "churn_risk": self.churn_risk,
        }


@dataclass
class CoverageGap:
    """Identified gap in worker coverage."""

    category: str
    location: str
    demand_count: int  # How many tasks needed workers here
    available_workers: int  # How many workers can serve this
    avg_time_to_assign_seconds: float  # How long assignment takes
    expiry_rate: float  # What % of tasks expire without completion
    severity: str  # "critical", "high", "medium", "low"
    recommendation: str  # What to do about it
    estimated_weekly_tasks: float  # Projected demand
    avg_bounty_usd: float  # Average task value

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "location": self.location,
            "demand_count": self.demand_count,
            "available_workers": self.available_workers,
            "avg_time_to_assign_hours": round(
                self.avg_time_to_assign_seconds / 3600, 1
            ),
            "expiry_rate_pct": round(self.expiry_rate * 100, 1),
            "severity": self.severity,
            "recommendation": self.recommendation,
            "estimated_weekly_tasks": round(self.estimated_weekly_tasks, 1),
            "avg_bounty_usd": round(self.avg_bounty_usd, 2),
        }


@dataclass
class RecruitmentRecommendation:
    """Actionable recommendation for recruiting workers."""

    priority: int  # 1 = highest
    target_category: str
    target_location: str
    reason: str
    estimated_weekly_earnings_usd: float
    competition_level: str  # "none", "low", "medium", "high"
    recommended_channels: list[str]  # Where to recruit
    gap: CoverageGap | None = None

    def to_dict(self) -> dict:
        return {
            "priority": self.priority,
            "target_category": self.target_category,
            "target_location": self.target_location,
            "reason": self.reason,
            "estimated_weekly_earnings_usd": round(
                self.estimated_weekly_earnings_usd, 2
            ),
            "competition_level": self.competition_level,
            "recommended_channels": self.recommended_channels,
        }


# ─── Demand Tracker ──────────────────────────────────────────


class TaskDemandTracker:
    """Tracks task creation patterns to understand demand.

    Maintains a rolling window of task signals to identify:
    - Which categories are most demanded
    - Which locations need coverage
    - How quickly tasks get assigned
    - What bounty levels attract workers
    """

    def __init__(self, window_days: int = 30, max_signals: int = 10000):
        self._signals: list[TaskDemandSignal] = []
        self._window_seconds = window_days * 86400
        self._max_signals = max_signals

    def record_task(self, signal: TaskDemandSignal) -> None:
        """Record a new task demand signal."""
        self._signals.append(signal)
        if len(self._signals) > self._max_signals:
            self._signals = self._signals[-self._max_signals :]

    def record_assignment(
        self,
        task_id: str,
        worker_wallet: str,
        time_to_assign_seconds: float,
    ) -> None:
        """Record that a task was assigned to a worker."""
        for signal in reversed(self._signals):
            if signal.task_id == task_id:
                signal.status = "assigned"
                signal.worker_wallet = worker_wallet
                signal.time_to_assign_seconds = time_to_assign_seconds
                break

    def record_completion(self, task_id: str) -> None:
        """Record task completion."""
        for signal in reversed(self._signals):
            if signal.task_id == task_id:
                signal.status = "completed"
                break

    def record_expiry(self, task_id: str) -> None:
        """Record task expiration."""
        for signal in reversed(self._signals):
            if signal.task_id == task_id:
                signal.status = "expired"
                break

    def _active_signals(self) -> list[TaskDemandSignal]:
        """Get signals within the window."""
        cutoff = time.time() - self._window_seconds
        return [s for s in self._signals if s.created_at >= cutoff]

    def category_demand(self) -> dict[str, int]:
        """Count tasks per category in window."""
        counter = Counter()
        for s in self._active_signals():
            counter[s.category] += 1
        return dict(counter.most_common())

    def location_demand(self) -> dict[str, int]:
        """Count tasks per location in window."""
        counter = Counter()
        for s in self._active_signals():
            counter[s.location] += 1
        return dict(counter.most_common())

    def category_location_demand(self) -> dict[tuple[str, str], int]:
        """Count tasks per (category, location) pair."""
        counter = Counter()
        for s in self._active_signals():
            counter[(s.category, s.location)] += 1
        return dict(counter)

    def avg_time_to_assign(
        self, category: str | None = None, location: str | None = None
    ) -> float:
        """Average time to assign tasks (in seconds)."""
        signals = self._active_signals()
        if category:
            signals = [s for s in signals if s.category == category]
        if location:
            signals = [s for s in signals if s.location == location]

        assigned = [s for s in signals if s.time_to_assign_seconds is not None]
        if not assigned:
            return 0.0
        return sum(s.time_to_assign_seconds for s in assigned) / len(assigned)

    def expiry_rate(
        self, category: str | None = None, location: str | None = None
    ) -> float:
        """What percentage of tasks expire without assignment."""
        signals = self._active_signals()
        if category:
            signals = [s for s in signals if s.category == category]
        if location:
            signals = [s for s in signals if s.location == location]

        terminal = [s for s in signals if s.status in ("completed", "expired")]
        if not terminal:
            return 0.0
        expired = [s for s in terminal if s.status == "expired"]
        return len(expired) / len(terminal)

    def avg_bounty(
        self, category: str | None = None, location: str | None = None
    ) -> float:
        """Average bounty for tasks."""
        signals = self._active_signals()
        if category:
            signals = [s for s in signals if s.category == category]
        if location:
            signals = [s for s in signals if s.location == location]

        if not signals:
            return 0.0
        return sum(s.bounty_usd for s in signals) / len(signals)

    def demand_velocity(self, category: str | None = None) -> float:
        """Tasks per week for a category (or overall)."""
        signals = self._active_signals()
        if category:
            signals = [s for s in signals if s.category == category]
        if not signals:
            return 0.0

        time_span = time.time() - min(s.created_at for s in signals)
        if time_span < 3600:  # Less than 1 hour of data
            return 0.0
        weeks = time_span / (7 * 86400)
        return len(signals) / max(weeks, 0.01)

    def summary(self) -> dict:
        """Overall demand summary."""
        signals = self._active_signals()
        return {
            "total_tasks": len(signals),
            "categories": self.category_demand(),
            "locations": self.location_demand(),
            "avg_bounty_usd": round(self.avg_bounty(), 2),
            "overall_expiry_rate": round(self.expiry_rate() * 100, 1),
        }


# ─── Coverage Map ─────────────────────────────────────────────


class WorkerCoverageMap:
    """Maps worker availability across categories and locations.

    Identifies which (category, location) pairs have adequate
    coverage vs. gaps needing recruitment.
    """

    def __init__(self):
        self._workers: dict[str, WorkerProfile] = {}  # wallet → profile

    def add_worker(self, profile: WorkerProfile) -> None:
        """Register or update a worker profile."""
        self._workers[profile.wallet] = profile

    def remove_worker(self, wallet: str) -> None:
        """Remove a worker."""
        self._workers.pop(wallet, None)

    def get_worker(self, wallet: str) -> WorkerProfile | None:
        """Get a worker by wallet."""
        return self._workers.get(wallet)

    @property
    def total_workers(self) -> int:
        return len(self._workers)

    @property
    def active_workers(self) -> int:
        return sum(1 for w in self._workers.values() if w.is_active)

    def workers_for_category(self, category: str) -> list[WorkerProfile]:
        """Find workers who handle a category."""
        return [
            w
            for w in self._workers.values()
            if category in w.categories and w.is_active
        ]

    def workers_for_location(self, location: str) -> list[WorkerProfile]:
        """Find workers available in a location."""
        return [
            w for w in self._workers.values() if location in w.locations and w.is_active
        ]

    def workers_for_category_location(
        self, category: str, location: str
    ) -> list[WorkerProfile]:
        """Find workers who handle a category in a location."""
        return [
            w
            for w in self._workers.values()
            if category in w.categories and location in w.locations and w.is_active
        ]

    def category_coverage(self) -> dict[str, int]:
        """Count active workers per category."""
        coverage: dict[str, int] = defaultdict(int)
        for w in self._workers.values():
            if w.is_active:
                for cat in w.categories:
                    coverage[cat] += 1
        return dict(coverage)

    def location_coverage(self) -> dict[str, int]:
        """Count active workers per location."""
        coverage: dict[str, int] = defaultdict(int)
        for w in self._workers.values():
            if w.is_active:
                for loc in w.locations:
                    coverage[loc] += 1
        return dict(coverage)

    def concentration_index(self) -> float:
        """Herfindahl-Hirschman Index for worker concentration.

        0 = perfectly distributed, 10000 = one worker does everything.
        Values above 2500 indicate high concentration (dependency risk).
        """
        if not self._workers:
            return 0.0

        total_tasks = sum(w.completed_tasks for w in self._workers.values())
        if total_tasks == 0:
            return 0.0

        shares = [
            w.completed_tasks / total_tasks
            for w in self._workers.values()
            if w.completed_tasks > 0
        ]
        return sum(s**2 for s in shares) * 10000

    def churn_risk_report(self) -> dict[str, list[str]]:
        """Group workers by churn risk level."""
        risk_groups: dict[str, list[str]] = {
            "low": [],
            "medium": [],
            "high": [],
            "churned": [],
        }
        for w in self._workers.values():
            risk_groups[w.churn_risk].append(w.wallet)
        return risk_groups

    def top_performers(self, limit: int = 10) -> list[WorkerProfile]:
        """Get top workers by completion rate × rating."""
        scored = [
            (w, w.completion_rate * w.avg_rating)
            for w in self._workers.values()
            if w.total_tasks > 0
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [w for w, _ in scored[:limit]]

    def all_workers(self) -> list[WorkerProfile]:
        """Get all registered workers."""
        return list(self._workers.values())

    def summary(self) -> dict:
        """Coverage summary."""
        return {
            "total_workers": self.total_workers,
            "active_workers": self.active_workers,
            "category_coverage": self.category_coverage(),
            "location_coverage": self.location_coverage(),
            "concentration_index": round(self.concentration_index(), 0),
            "churn_risk": {k: len(v) for k, v in self.churn_risk_report().items()},
        }


# ─── Recruitment Engine ──────────────────────────────────────


# Standard recruitment channels by category
RECRUITMENT_CHANNELS = {
    "physical_verification": [
        "TaskRabbit",
        "Gigwalk",
        "Field Agent",
        "Local community boards",
    ],
    "delivery": ["DoorDash", "Uber Eats", "Postmates", "Local Facebook groups"],
    "data_collection": [
        "Upwork",
        "Freelancer",
        "Reddit r/beermoney",
        "MTurk communities",
    ],
    "survey": ["SurveyMonkey marketplace", "Reddit", "University job boards"],
    "mystery_shopping": [
        "Market Force",
        "BestMark",
        "IntelliShop",
        "Secret shopper forums",
    ],
    "quality_assurance": ["UserTesting", "TryMyUI", "Upwork", "Dev communities"],
    "content_creation": ["Fiverr", "Upwork", "99designs", "Twitter/X"],
    "default": ["execution.market", "XMTP bot", "Social media", "Word of mouth"],
}


class RecruitmentEngine:
    """Generates recruitment recommendations from demand + coverage data.

    Takes demand patterns and coverage maps, identifies gaps,
    and produces prioritized recruitment recommendations.
    """

    def __init__(
        self,
        demand_tracker: TaskDemandTracker,
        coverage_map: WorkerCoverageMap,
    ):
        self._demand = demand_tracker
        self._coverage = coverage_map

    def identify_gaps(self) -> list[CoverageGap]:
        """Find all coverage gaps ordered by severity.

        A gap exists when demand exceeds supply for a
        (category, location) pair.
        """
        demand = self._demand.category_location_demand()
        gaps: list[CoverageGap] = []

        for (category, location), count in demand.items():
            workers = self._coverage.workers_for_category_location(category, location)
            available = len(workers)

            expiry = self._demand.expiry_rate(category=category, location=location)
            tta = self._demand.avg_time_to_assign(category=category, location=location)
            avg_bounty = self._demand.avg_bounty(category=category, location=location)
            velocity = self._demand.demand_velocity(category=category)

            severity = self._calculate_severity(
                demand_count=count,
                available_workers=available,
                expiry_rate=expiry,
                time_to_assign=tta,
            )

            recommendation = self._generate_recommendation(
                category=category,
                location=location,
                available=available,
                expiry_rate=expiry,
                avg_bounty=avg_bounty,
            )

            gaps.append(
                CoverageGap(
                    category=category,
                    location=location,
                    demand_count=count,
                    available_workers=available,
                    avg_time_to_assign_seconds=tta,
                    expiry_rate=expiry,
                    severity=severity,
                    recommendation=recommendation,
                    estimated_weekly_tasks=velocity,
                    avg_bounty_usd=avg_bounty,
                )
            )

        # Sort by severity (critical first)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        gaps.sort(key=lambda g: (severity_order.get(g.severity, 99), -g.demand_count))

        return gaps

    def generate_recommendations(
        self, max_count: int = 10
    ) -> list[RecruitmentRecommendation]:
        """Generate prioritized recruitment recommendations.

        Each recommendation includes:
        - What category/location to target
        - Why it matters
        - Estimated earnings potential
        - Where to recruit
        """
        gaps = self.identify_gaps()
        recs: list[RecruitmentRecommendation] = []

        for i, gap in enumerate(gaps[:max_count]):
            channels = RECRUITMENT_CHANNELS.get(
                gap.category, RECRUITMENT_CHANNELS["default"]
            )

            weekly_earnings = (
                gap.estimated_weekly_tasks * gap.avg_bounty_usd * 0.87
            )  # After 13% fee

            competition = "none"
            if gap.available_workers == 0:
                competition = "none"
            elif gap.available_workers <= 2:
                competition = "low"
            elif gap.available_workers <= 5:
                competition = "medium"
            else:
                competition = "high"

            recs.append(
                RecruitmentRecommendation(
                    priority=i + 1,
                    target_category=gap.category,
                    target_location=gap.location,
                    reason=gap.recommendation,
                    estimated_weekly_earnings_usd=weekly_earnings,
                    competition_level=competition,
                    recommended_channels=channels,
                    gap=gap,
                )
            )

        return recs

    def _calculate_severity(
        self,
        demand_count: int,
        available_workers: int,
        expiry_rate: float,
        time_to_assign: float,
    ) -> str:
        """Calculate gap severity from multiple signals."""
        score = 0.0

        # No workers at all = critical
        if available_workers == 0:
            score += 50

        # High expiry rate
        if expiry_rate > 0.50:
            score += 30
        elif expiry_rate > 0.25:
            score += 15

        # Slow assignment
        if time_to_assign > 86400:  # More than 24 hours
            score += 20
        elif time_to_assign > 3600:  # More than 1 hour
            score += 10

        # High demand with low supply
        if demand_count > 10 and available_workers < 2:
            score += 10

        if score >= 50:
            return "critical"
        elif score >= 30:
            return "high"
        elif score >= 15:
            return "medium"
        else:
            return "low"

    def _generate_recommendation(
        self,
        category: str,
        location: str,
        available: int,
        expiry_rate: float,
        avg_bounty: float,
    ) -> str:
        """Generate human-readable recommendation."""
        parts = []

        if available == 0:
            parts.append(f"No workers for {category} in {location}")
        elif available == 1:
            parts.append(
                f"Only 1 worker for {category} in {location} — single point of failure"
            )

        if expiry_rate > 0.50:
            parts.append(f"{expiry_rate * 100:.0f}% of tasks expiring")
        elif expiry_rate > 0.25:
            parts.append(f"{expiry_rate * 100:.0f}% expiry rate is concerning")

        if avg_bounty > 0:
            parts.append(f"avg bounty ${avg_bounty:.2f}")

        return (
            "; ".join(parts)
            if parts
            else f"Coverage adequate for {category} in {location}"
        )


# ─── Worker Discovery (Unified) ──────────────────────────────


class WorkerDiscovery:
    """Unified worker supply intelligence layer.

    Combines demand tracking, coverage mapping, and recruitment
    recommendations into a single queryable interface.

    Usage:
        discovery = WorkerDiscovery()

        # Feed task data
        discovery.record_task("t1", "physical_verification", "Miami", 5.00)
        discovery.record_task("t2", "delivery", "NYC", 3.50)

        # Add known workers
        discovery.add_worker("0xABC", categories=["physical_verification"], locations=["Miami"])

        # Get intelligence
        gaps = discovery.identify_gaps()
        recs = discovery.get_recommendations()
        report = discovery.supply_report()
    """

    def __init__(self, window_days: int = 30):
        self._demand_tracker = TaskDemandTracker(window_days=window_days)
        self._coverage_map = WorkerCoverageMap()
        self._recruitment_engine = RecruitmentEngine(
            self._demand_tracker, self._coverage_map
        )

    # ─── Task Recording ───────────────────────────────────────

    def record_task(
        self,
        task_id: str,
        category: str,
        location: str = "remote",
        bounty_usd: float = 0.0,
        status: str = "open",
    ) -> TaskDemandSignal:
        """Record a task demand signal."""
        signal = TaskDemandSignal(
            task_id=task_id,
            category=category,
            location=location,
            bounty_usd=bounty_usd,
            status=status,
        )
        self._demand_tracker.record_task(signal)
        return signal

    def record_assignment(
        self,
        task_id: str,
        worker_wallet: str,
        time_to_assign_seconds: float,
    ) -> None:
        """Record task assignment."""
        self._demand_tracker.record_assignment(
            task_id, worker_wallet, time_to_assign_seconds
        )

    def record_completion(self, task_id: str) -> None:
        """Record task completion."""
        self._demand_tracker.record_completion(task_id)

    def record_expiry(self, task_id: str) -> None:
        """Record task expiration."""
        self._demand_tracker.record_expiry(task_id)

    # ─── Worker Management ────────────────────────────────────

    def add_worker(
        self,
        wallet: str,
        name: str = "",
        categories: list[str] | None = None,
        locations: list[str] | None = None,
        avg_rating: float = 0.0,
        total_tasks: int = 0,
        completed_tasks: int = 0,
    ) -> WorkerProfile:
        """Add or update a worker profile."""
        profile = WorkerProfile(
            wallet=wallet,
            name=name,
            categories=categories or [],
            locations=locations or [],
            avg_rating=avg_rating,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            last_active=time.time(),
        )
        self._coverage_map.add_worker(profile)
        return profile

    def update_worker_activity(self, wallet: str) -> None:
        """Mark a worker as recently active."""
        worker = self._coverage_map.get_worker(wallet)
        if worker:
            worker.last_active = time.time()

    def remove_worker(self, wallet: str) -> None:
        """Remove a worker."""
        self._coverage_map.remove_worker(wallet)

    # ─── Intelligence Queries ─────────────────────────────────

    def identify_gaps(self) -> list[CoverageGap]:
        """Find all coverage gaps ordered by severity."""
        return self._recruitment_engine.identify_gaps()

    def get_recommendations(
        self, max_count: int = 10
    ) -> list[RecruitmentRecommendation]:
        """Get prioritized recruitment recommendations."""
        return self._recruitment_engine.generate_recommendations(max_count=max_count)

    def demand_summary(self) -> dict:
        """Get demand overview."""
        return self._demand_tracker.summary()

    def coverage_summary(self) -> dict:
        """Get coverage overview."""
        return self._coverage_map.summary()

    def worker_concentration(self) -> float:
        """Get HHI concentration index (0-10000)."""
        return self._coverage_map.concentration_index()

    def churn_risk(self) -> dict[str, int]:
        """Get churn risk distribution."""
        report = self._coverage_map.churn_risk_report()
        return {k: len(v) for k, v in report.items()}

    def top_performers(self, limit: int = 5) -> list[dict]:
        """Get top workers by performance."""
        return [w.to_dict() for w in self._coverage_map.top_performers(limit)]

    # ─── Supply Report ────────────────────────────────────────

    def supply_report(self) -> dict:
        """Comprehensive supply-demand intelligence report.

        Returns a dict suitable for dashboards and decision-making.
        """
        demand = self._demand_tracker.summary()
        coverage = self._coverage_map.summary()
        gaps = self.identify_gaps()
        recs = self.get_recommendations(max_count=5)

        # Supply-demand ratio
        total_demand = demand["total_tasks"]
        total_supply = coverage["active_workers"]

        # Health assessment
        if total_demand == 0 and total_supply == 0:
            health = "no_data"
            supply_ratio = None
        elif total_demand == 0:
            health = "healthy"
            supply_ratio = None
        elif total_supply == 0:
            health = "no_supply"
            supply_ratio = 0.0
        else:
            supply_ratio = total_supply / total_demand
            if supply_ratio >= 1.0:
                health = "healthy"
            elif supply_ratio >= 0.5:
                health = "strained"
            else:
                health = "critical"

        critical_gaps = [g for g in gaps if g.severity == "critical"]
        high_gaps = [g for g in gaps if g.severity == "high"]

        return {
            "health": health,
            "supply_ratio": round(supply_ratio, 2)
            if supply_ratio is not None
            else None,
            "demand": demand,
            "coverage": coverage,
            "gaps": {
                "total": len(gaps),
                "critical": len(critical_gaps),
                "high": len(high_gaps),
                "top_gaps": [g.to_dict() for g in gaps[:5]],
            },
            "recommendations": [r.to_dict() for r in recs],
            "concentration_index": round(self.worker_concentration(), 0),
            "churn_risk": self.churn_risk(),
        }

    def diagnostic_report(self) -> str:
        """Human-readable diagnostic report."""
        report = self.supply_report()

        lines = [
            "╔═══════════════════════════════════════════════════╗",
            "║       WORKER DISCOVERY — SUPPLY INTELLIGENCE       ║",
            "╠═══════════════════════════════════════════════════╣",
            f"║ Health: {report['health']:<43}║",
            f"║ Workers: {report['coverage']['active_workers']} active / {report['coverage']['total_workers']} total{' ' * 28}║"[
                :53
            ]
            + "║",
            f"║ Tasks in window: {report['demand']['total_tasks']:<34}║",
            f"║ Concentration (HHI): {report['concentration_index']:<30}║",
        ]

        if report["gaps"]["critical"] > 0:
            lines.append("╠───────────────────────────────────────────────────╣")
            lines.append(f"║ 🔴 CRITICAL GAPS: {report['gaps']['critical']:<33}║")
            for gap in report["gaps"]["top_gaps"][:3]:
                desc = f"{gap['category']} in {gap['location']}"[:45]
                lines.append(f"║   {desc:<48}║")

        if report["recommendations"]:
            lines.append("╠───────────────────────────────────────────────────╣")
            lines.append("║ 📋 TOP RECOMMENDATIONS:                           ║")
            for rec in report["recommendations"][:3]:
                desc = f"#{rec['priority']}: {rec['target_category']} ({rec['target_location']})"[
                    :47
                ]
                lines.append(f"║  {desc:<49}║")

        churn = report["churn_risk"]
        if churn.get("high", 0) > 0 or churn.get("churned", 0) > 0:
            lines.append("╠───────────────────────────────────────────────────╣")
            lines.append(
                f"║ ⚠️  Churn: {churn.get('high', 0)} high risk, "
                f"{churn.get('churned', 0)} churned{' ' * 20}║"[:53]
                + "║"
            )

        lines.append("╚═══════════════════════════════════════════════════╝")
        return "\n".join(lines)
