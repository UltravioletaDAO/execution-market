from __future__ import annotations
"""
ExpiryAnalyzer — Diagnoses task expiry patterns and recommends countermeasures.

The #1 business problem: 35.6% of tasks expire without completion.
This module analyzes WHY tasks expire and proposes data-driven countermeasures.

Root cause taxonomy:
    1. NO_WORKERS     — No workers available for the category
    2. LOW_BOUNTY     — Bounty too low for workers to accept
    3. SHORT_DEADLINE — Not enough time for workers to discover & complete
    4. NICHE_CATEGORY — Category has few workers (knowledge_access, code_execution)
    5. UNCLEAR_TASK   — Title/instructions too vague (workers skip)
    6. SUPPLY_GAP     — Worker supply < task demand in a time window

Countermeasures:
    - Automatic deadline extension for tasks with no bids
    - Bounty escalation curve (increase bounty as deadline approaches)
    - Worker notification push (alert workers in matching categories)
    - Category pooling (batch similar tasks to attract worker attention)
    - Repost strategy (cancel-and-repost with improved params)

Usage:
    analyzer = ExpiryAnalyzer.create(em_api_url="https://api.execution.market")

    # Run full diagnosis
    report = analyzer.analyze()
    print(report.summary())

    # Get recommendations for a specific task
    recs = analyzer.recommend_for_task(task_data)
"""

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger("em.swarm.expiry_analyzer")


class ExpiryReason(str, Enum):
    """Root cause categories for task expiry."""

    NO_WORKERS = "no_workers"
    LOW_BOUNTY = "low_bounty"
    SHORT_DEADLINE = "short_deadline"
    NICHE_CATEGORY = "niche_category"
    UNCLEAR_TASK = "unclear_task"
    SUPPLY_GAP = "supply_gap"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    """Severity of the expiry pattern."""

    CRITICAL = "critical"  # >50% expiry in category
    HIGH = "high"  # 30-50% expiry
    MEDIUM = "medium"  # 15-30% expiry
    LOW = "low"  # <15% expiry


class CountermeasureType(str, Enum):
    """Types of countermeasures."""

    EXTEND_DEADLINE = "extend_deadline"
    ESCALATE_BOUNTY = "escalate_bounty"
    PUSH_NOTIFICATION = "push_notification"
    BATCH_TASKS = "batch_tasks"
    REPOST = "repost"
    RECRUIT_WORKERS = "recruit_workers"
    IMPROVE_INSTRUCTIONS = "improve_instructions"


@dataclass
class CategoryHealth:
    """Health metrics for a single task category."""

    category: str
    total_tasks: int = 0
    completed: int = 0
    expired: int = 0
    cancelled: int = 0
    active: int = 0  # open + assigned + in_progress
    unique_workers: int = 0
    avg_bounty_completed: float = 0.0
    avg_bounty_expired: float = 0.0
    avg_completion_hours: float = 0.0
    worker_concentration: float = 0.0  # HHI (0-1, higher = more concentrated)

    @property
    def expiry_rate(self) -> float:
        """Expiry rate as fraction (0-1)."""
        denominator = self.completed + self.expired
        if denominator == 0:
            return 0.0
        return self.expired / denominator

    @property
    def severity(self) -> Severity:
        """Severity based on expiry rate."""
        rate = self.expiry_rate
        if rate > 0.50:
            return Severity.CRITICAL
        elif rate > 0.30:
            return Severity.HIGH
        elif rate > 0.15:
            return Severity.MEDIUM
        return Severity.LOW

    @property
    def has_workers(self) -> bool:
        return self.unique_workers > 0

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "total_tasks": self.total_tasks,
            "completed": self.completed,
            "expired": self.expired,
            "cancelled": self.cancelled,
            "active": self.active,
            "unique_workers": self.unique_workers,
            "expiry_rate": round(self.expiry_rate, 3),
            "severity": self.severity.value,
            "avg_bounty_completed": round(self.avg_bounty_completed, 2),
            "avg_bounty_expired": round(self.avg_bounty_expired, 2),
            "worker_concentration": round(self.worker_concentration, 3),
        }


@dataclass
class ExpiryDiagnosis:
    """Diagnosis for a single expired task or pattern."""

    task_id: Optional[str] = None
    category: str = ""
    primary_reason: ExpiryReason = ExpiryReason.UNKNOWN
    secondary_reasons: list[ExpiryReason] = field(default_factory=list)
    confidence: float = 0.0  # 0-1
    details: str = ""
    bounty_usd: float = 0.0
    deadline_hours: float = 0.0

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "category": self.category,
            "primary_reason": self.primary_reason.value,
            "secondary_reasons": [r.value for r in self.secondary_reasons],
            "confidence": round(self.confidence, 2),
            "details": self.details,
            "bounty_usd": self.bounty_usd,
            "deadline_hours": self.deadline_hours,
        }


@dataclass
class Countermeasure:
    """A recommended action to reduce expiry."""

    type: CountermeasureType
    priority: int  # 1 = highest
    category: str = ""
    description: str = ""
    expected_impact: float = 0.0  # Estimated reduction in expiry rate (0-1)
    implementation: str = ""  # Concrete steps
    estimated_effort: str = ""  # "low", "medium", "high"

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "priority": self.priority,
            "category": self.category,
            "description": self.description,
            "expected_impact": round(self.expected_impact, 2),
            "implementation": self.implementation,
            "estimated_effort": self.estimated_effort,
        }


@dataclass
class ExpiryReport:
    """Complete expiry analysis report."""

    generated_at: str = ""
    total_tasks: int = 0
    total_completed: int = 0
    total_expired: int = 0
    total_cancelled: int = 0
    overall_expiry_rate: float = 0.0
    overall_severity: Severity = Severity.LOW

    # Per-category health
    category_health: list[CategoryHealth] = field(default_factory=list)

    # Diagnoses
    diagnoses: list[ExpiryDiagnosis] = field(default_factory=list)

    # Recommendations
    countermeasures: list[Countermeasure] = field(default_factory=list)

    # Worker supply metrics
    total_workers: int = 0
    worker_hhi: float = 0.0  # Herfindahl-Hirschman Index for worker concentration
    top_worker_share: float = 0.0

    # Time patterns
    busiest_hour_utc: int = 0
    quietest_hour_utc: int = 0

    analysis_duration_ms: float = 0.0

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"📊 Expiry Analysis Report — {self.generated_at[:10]}",
            "",
            f"Overall: {self.total_expired}/{self.total_completed + self.total_expired} "
            f"expired ({self.overall_expiry_rate:.1%}) — {self.overall_severity.value.upper()}",
            f"Workers: {self.total_workers} active, HHI={self.worker_hhi:.3f} "
            f"(top worker: {self.top_worker_share:.0%} of completions)",
            "",
            "Category Health:",
        ]

        for ch in sorted(self.category_health, key=lambda x: -x.expiry_rate):
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}[
                ch.severity.value
            ]
            lines.append(
                f"  {icon} {ch.category}: {ch.expiry_rate:.0%} expiry "
                f"({ch.completed}✅ {ch.expired}❌) "
                f"workers={ch.unique_workers}"
            )

        if self.diagnoses:
            lines.append("")
            lines.append("Top Diagnoses:")
            # Group by reason
            reasons = defaultdict(int)
            for d in self.diagnoses:
                reasons[d.primary_reason] += 1
            for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
                lines.append(f"  • {reason.value}: {count} tasks")

        if self.countermeasures:
            lines.append("")
            lines.append("Recommended Countermeasures:")
            for cm in sorted(self.countermeasures, key=lambda x: x.priority)[:5]:
                lines.append(
                    f"  {cm.priority}. [{cm.type.value}] {cm.description} "
                    f"(impact: {cm.expected_impact:.0%}, effort: {cm.estimated_effort})"
                )

        lines.append("")
        lines.append(f"Analysis took {self.analysis_duration_ms:.0f}ms")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "overall": {
                "total_tasks": self.total_tasks,
                "completed": self.total_completed,
                "expired": self.total_expired,
                "cancelled": self.total_cancelled,
                "expiry_rate": round(self.overall_expiry_rate, 3),
                "severity": self.overall_severity.value,
            },
            "workers": {
                "total": self.total_workers,
                "hhi": round(self.worker_hhi, 3),
                "top_share": round(self.top_worker_share, 3),
            },
            "categories": [ch.to_dict() for ch in self.category_health],
            "diagnoses_summary": {
                reason.value: sum(
                    1 for d in self.diagnoses if d.primary_reason == reason
                )
                for reason in ExpiryReason
                if any(d.primary_reason == reason for d in self.diagnoses)
            },
            "countermeasures": [cm.to_dict() for cm in self.countermeasures],
            "analysis_duration_ms": round(self.analysis_duration_ms, 1),
        }


class ExpiryAnalyzer:
    """
    Analyzes task expiry patterns and recommends countermeasures.

    Pulls data from the EM API, computes category health metrics,
    diagnoses root causes per expired task, and generates prioritized
    countermeasures.
    """

    def __init__(
        self,
        em_api_url: str = "https://api.execution.market",
        api_key: Optional[str] = None,
        timeout_seconds: float = 10.0,
    ):
        self.em_api_url = em_api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout_seconds

        # Thresholds for diagnosis
        self.low_bounty_threshold = 0.15  # USD — below this is "low bounty"
        self.short_deadline_hours = 2.0  # Hours — below this is "short deadline"
        self.niche_worker_threshold = 2  # Categories with fewer workers are "niche"
        self.vague_title_min_words = 4  # Titles shorter than this may be "unclear"

        # Real-time expiry event log (populated by integrator via record_expiry)
        self._recent_expiry_events: list[dict] = []
        self._max_recent_events: int = 500

    @classmethod
    def create(
        cls,
        em_api_url: str = "https://api.execution.market",
        api_key: Optional[str] = None,
    ) -> "ExpiryAnalyzer":
        return cls(em_api_url=em_api_url, api_key=api_key)

    # ── Real-Time Event Recording ─────────────────────────────────────

    def record_expiry(self, event_data: dict) -> None:
        """
        Record a real-time task.expired event from the integrator.

        Called by the SwarmIntegrator when a task.expired event fires.
        Builds a running log that can be used for incremental analysis
        without re-fetching all historical data from the API.

        Args:
            event_data: Event payload from the EventBus, typically:
                {
                    "task_id": "...",
                    "category": "...",
                    "bounty_usd": 0.25,
                    "title": "...",
                    "created_at": "2026-...",
                    "expired_at": "2026-..."
                }
        """
        if not isinstance(event_data, dict):
            logger.warning("record_expiry: expected dict, got %s", type(event_data))
            return

        import time as _time

        event = {
            **event_data,
            "_recorded_at": _time.time(),
        }
        self._recent_expiry_events.append(event)

        # Trim to max size (FIFO — keep most recent)
        if len(self._recent_expiry_events) > self._max_recent_events:
            self._recent_expiry_events = self._recent_expiry_events[
                -self._max_recent_events :
            ]

        logger.debug(
            "record_expiry: task_id=%s category=%s bounty=%.2f",
            event_data.get("task_id", "?"),
            event_data.get("category", "?"),
            float(event_data.get("bounty_usd", 0) or 0),
        )

    def get_recent_expiry_events(self, limit: int = 50) -> list[dict]:
        """Return the most recent recorded expiry events (real-time buffer)."""
        return list(self._recent_expiry_events[-limit:])

    def analyze_recent(self) -> Optional["ExpiryReport"]:
        """
        Run analysis on recently recorded events (real-time buffer).

        Useful for continuous monitoring without expensive API calls.
        Returns None if no recent events have been recorded.
        """
        if not self._recent_expiry_events:
            return None

        # Build fake completed list — we only have expired events
        # but analyze_offline needs both to compute rates
        return self.analyze_offline(
            completed=[],
            expired=list(self._recent_expiry_events),
            cancelled=[],
        )

    # ── API Fetching ──────────────────────────────────────────────────

    def _fetch_tasks(self, status: str, limit: int = 200) -> list[dict]:
        """Fetch tasks from EM API with pagination."""
        tasks = []
        offset = 0
        while offset < limit:
            batch_size = min(50, limit - offset)
            url = (
                f"{self.em_api_url}/api/v1/tasks"
                f"?status={status}&limit={batch_size}&offset={offset}"
            )
            try:
                req = Request(url)
                if self.api_key:
                    req.add_header("Authorization", f"Bearer {self.api_key}")
                resp = urlopen(req, timeout=self.timeout)
                data = json.loads(resp.read())
                batch = data.get("tasks", [])
                if not batch:
                    break
                tasks.extend(batch)
                offset += len(batch)
                if not data.get("has_more", False):
                    break
            except (URLError, HTTPError) as e:
                logger.warning(
                    f"Failed to fetch {status} tasks at offset {offset}: {e}"
                )
                break
        return tasks

    # ── Core Analysis ─────────────────────────────────────────────────

    def analyze(self) -> ExpiryReport:
        """Run full expiry analysis against live EM API data."""
        start = time.monotonic()
        report = ExpiryReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        # Fetch all task data
        completed = self._fetch_tasks("completed", limit=500)
        expired = self._fetch_tasks("expired", limit=500)
        cancelled = self._fetch_tasks("cancelled", limit=200)

        report.total_completed = len(completed)
        report.total_expired = len(expired)
        report.total_cancelled = len(cancelled)
        report.total_tasks = len(completed) + len(expired) + len(cancelled)

        if report.total_completed + report.total_expired > 0:
            report.overall_expiry_rate = report.total_expired / (
                report.total_completed + report.total_expired
            )

        # Determine severity
        if report.overall_expiry_rate > 0.50:
            report.overall_severity = Severity.CRITICAL
        elif report.overall_expiry_rate > 0.30:
            report.overall_severity = Severity.HIGH
        elif report.overall_expiry_rate > 0.15:
            report.overall_severity = Severity.MEDIUM
        else:
            report.overall_severity = Severity.LOW

        # Compute category health
        report.category_health = self._compute_category_health(
            completed, expired, cancelled
        )

        # Worker concentration analysis
        worker_stats = self._analyze_workers(completed)
        report.total_workers = worker_stats["total_workers"]
        report.worker_hhi = worker_stats["hhi"]
        report.top_worker_share = worker_stats["top_share"]

        # Diagnose each expired task
        report.diagnoses = self._diagnose_expired(expired, report.category_health)

        # Generate countermeasures
        report.countermeasures = self._generate_countermeasures(report)

        report.analysis_duration_ms = (time.monotonic() - start) * 1000
        return report

    def analyze_offline(
        self,
        completed: list[dict],
        expired: list[dict],
        cancelled: list[dict] | None = None,
    ) -> ExpiryReport:
        """
        Run analysis on pre-fetched data (for testing/offline use).
        """
        start = time.monotonic()
        cancelled = cancelled or []

        report = ExpiryReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_completed=len(completed),
            total_expired=len(expired),
            total_cancelled=len(cancelled),
            total_tasks=len(completed) + len(expired) + len(cancelled),
        )

        if report.total_completed + report.total_expired > 0:
            report.overall_expiry_rate = report.total_expired / (
                report.total_completed + report.total_expired
            )

        if report.overall_expiry_rate > 0.50:
            report.overall_severity = Severity.CRITICAL
        elif report.overall_expiry_rate > 0.30:
            report.overall_severity = Severity.HIGH
        elif report.overall_expiry_rate > 0.15:
            report.overall_severity = Severity.MEDIUM
        else:
            report.overall_severity = Severity.LOW

        report.category_health = self._compute_category_health(
            completed, expired, cancelled
        )

        worker_stats = self._analyze_workers(completed)
        report.total_workers = worker_stats["total_workers"]
        report.worker_hhi = worker_stats["hhi"]
        report.top_worker_share = worker_stats["top_share"]

        report.diagnoses = self._diagnose_expired(expired, report.category_health)
        report.countermeasures = self._generate_countermeasures(report)

        report.analysis_duration_ms = (time.monotonic() - start) * 1000
        return report

    def _compute_category_health(
        self,
        completed: list[dict],
        expired: list[dict],
        cancelled: list[dict],
    ) -> list[CategoryHealth]:
        """Compute health metrics per category."""
        categories: dict[str, CategoryHealth] = {}

        def ensure(cat: str) -> CategoryHealth:
            if cat not in categories:
                categories[cat] = CategoryHealth(category=cat)
            return categories[cat]

        # Process completed
        for t in completed:
            cat = t.get("category", "unknown")
            ch = ensure(cat)
            ch.completed += 1
            ch.total_tasks += 1
            bounty = t.get("bounty_usd", 0) or 0
            # Running average for bounty
            n = ch.completed
            ch.avg_bounty_completed = (ch.avg_bounty_completed * (n - 1) + bounty) / n

        # Process expired
        for t in expired:
            cat = t.get("category", "unknown")
            ch = ensure(cat)
            ch.expired += 1
            ch.total_tasks += 1
            bounty = t.get("bounty_usd", 0) or 0
            n = ch.expired
            ch.avg_bounty_expired = (ch.avg_bounty_expired * (n - 1) + bounty) / n

        # Process cancelled
        for t in cancelled:
            cat = t.get("category", "unknown")
            ch = ensure(cat)
            ch.cancelled += 1
            ch.total_tasks += 1

        # Worker analysis per category
        cat_workers: dict[str, set] = defaultdict(set)
        for t in completed:
            cat = t.get("category", "unknown")
            wid = t.get("executor_id", "")
            if wid:
                cat_workers[cat].add(wid)

        for cat, workers in cat_workers.items():
            if cat in categories:
                categories[cat].unique_workers = len(workers)

        # Worker concentration (HHI per category)
        for cat, ch in categories.items():
            worker_counts = defaultdict(int)
            for t in completed:
                if t.get("category") == cat:
                    wid = t.get("executor_id", "")
                    if wid:
                        worker_counts[wid] += 1
            if worker_counts and ch.completed > 0:
                shares = [c / ch.completed for c in worker_counts.values()]
                ch.worker_concentration = sum(s * s for s in shares)

        return sorted(categories.values(), key=lambda x: -x.expiry_rate)

    def _analyze_workers(self, completed: list[dict]) -> dict:
        """Analyze worker supply and concentration."""
        worker_counts: dict[str, int] = defaultdict(int)
        for t in completed:
            wid = t.get("executor_id", "")
            if wid:
                worker_counts[wid] += 1

        total_workers = len(worker_counts)
        total_tasks = sum(worker_counts.values())

        if total_tasks == 0:
            return {"total_workers": 0, "hhi": 0.0, "top_share": 0.0}

        shares = [c / total_tasks for c in worker_counts.values()]
        hhi = sum(s * s for s in shares)
        top_share = max(shares) if shares else 0.0

        return {
            "total_workers": total_workers,
            "hhi": hhi,
            "top_share": top_share,
        }

    def _diagnose_expired(
        self,
        expired: list[dict],
        category_health: list[CategoryHealth],
    ) -> list[ExpiryDiagnosis]:
        """Diagnose root cause for each expired task."""
        # Build category lookup
        cat_lookup = {ch.category: ch for ch in category_health}
        diagnoses = []

        for task in expired:
            diag = self._diagnose_single(task, cat_lookup)
            diagnoses.append(diag)

        return diagnoses

    def _diagnose_single(
        self,
        task: dict,
        cat_lookup: dict[str, CategoryHealth],
    ) -> ExpiryDiagnosis:
        """Diagnose a single expired task."""
        task_id = task.get("id", "")
        category = task.get("category", "unknown")
        bounty = task.get("bounty_usd", 0) or 0
        title = task.get("title", "")
        deadline_str = task.get("deadline", "")
        created_str = task.get("created_at", "")

        # Calculate deadline hours
        deadline_hours = 0.0
        if deadline_str and created_str:
            try:
                deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
                created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                deadline_hours = (deadline - created).total_seconds() / 3600
            except (ValueError, TypeError):
                pass

        # Get category health
        ch = cat_lookup.get(category)

        # Score each potential cause
        scores: dict[ExpiryReason, float] = {}

        # NO_WORKERS: category has zero workers
        if ch and ch.unique_workers == 0:
            scores[ExpiryReason.NO_WORKERS] = 0.95
        elif ch and ch.unique_workers == 1:
            scores[ExpiryReason.NO_WORKERS] = 0.4

        # LOW_BOUNTY
        if bounty < self.low_bounty_threshold:
            scores[ExpiryReason.LOW_BOUNTY] = 0.7
        elif (
            ch
            and ch.avg_bounty_completed > 0
            and bounty < ch.avg_bounty_completed * 0.5
        ):
            scores[ExpiryReason.LOW_BOUNTY] = 0.6

        # SHORT_DEADLINE
        if 0 < deadline_hours < self.short_deadline_hours:
            scores[ExpiryReason.SHORT_DEADLINE] = 0.65
        elif 0 < deadline_hours < 4:
            scores[ExpiryReason.SHORT_DEADLINE] = 0.35

        # NICHE_CATEGORY
        if ch and ch.unique_workers < self.niche_worker_threshold:
            if ch.unique_workers == 0:
                scores[ExpiryReason.NICHE_CATEGORY] = 0.85
            else:
                scores[ExpiryReason.NICHE_CATEGORY] = 0.5

        # UNCLEAR_TASK
        word_count = len(title.split()) if title else 0
        if word_count < self.vague_title_min_words:
            scores[ExpiryReason.UNCLEAR_TASK] = 0.4
        if title.startswith("[") and "]" in title:
            # Prefixed titles like "[KK Data]" — might be auto-generated
            scores[ExpiryReason.UNCLEAR_TASK] = max(
                scores.get(ExpiryReason.UNCLEAR_TASK, 0), 0.3
            )

        # SUPPLY_GAP (if workers exist but expiry rate is still high)
        if ch and ch.unique_workers > 0 and ch.expiry_rate > 0.3:
            scores[ExpiryReason.SUPPLY_GAP] = 0.55

        if not scores:
            scores[ExpiryReason.UNKNOWN] = 0.5

        # Select primary reason (highest score)
        sorted_reasons = sorted(scores.items(), key=lambda x: -x[1])
        primary = sorted_reasons[0]
        secondary = [r for r, s in sorted_reasons[1:] if s >= 0.3]

        details_parts = []
        if ch:
            details_parts.append(
                f"Category {category}: {ch.unique_workers} workers, "
                f"{ch.expiry_rate:.0%} expiry rate"
            )
        if bounty > 0:
            details_parts.append(f"bounty=${bounty:.2f}")
        if deadline_hours > 0:
            details_parts.append(f"deadline={deadline_hours:.1f}h")

        return ExpiryDiagnosis(
            task_id=task_id,
            category=category,
            primary_reason=primary[0],
            secondary_reasons=secondary,
            confidence=primary[1],
            details="; ".join(details_parts),
            bounty_usd=bounty,
            deadline_hours=deadline_hours,
        )

    def _generate_countermeasures(self, report: ExpiryReport) -> list[Countermeasure]:
        """Generate prioritized countermeasures based on analysis."""
        countermeasures = []
        priority = 1

        # 1. Worker concentration is extreme (HHI > 0.5 means >70% from one worker)
        if report.worker_hhi > 0.5:
            countermeasures.append(
                Countermeasure(
                    type=CountermeasureType.RECRUIT_WORKERS,
                    priority=priority,
                    description=(
                        f"Critical worker concentration: top worker handles "
                        f"{report.top_worker_share:.0%} of completions. "
                        f"Platform risk if this worker leaves."
                    ),
                    expected_impact=0.25,
                    implementation=(
                        "1. Create worker onboarding tasks with clear instructions\n"
                        "2. Post on freelance platforms (Fiverr, Upwork) with EM link\n"
                        "3. Implement referral bonus for existing workers\n"
                        "4. Auto-create 'first task' tutorial with guaranteed $0.25 payout"
                    ),
                    estimated_effort="high",
                )
            )
            priority += 1

        # 2. Categories with 100% expiry (no workers at all)
        zero_worker_cats = [
            ch
            for ch in report.category_health
            if ch.unique_workers == 0 and ch.expired > 0
        ]
        if zero_worker_cats:
            cat_names = ", ".join(ch.category for ch in zero_worker_cats)
            total_expired = sum(ch.expired for ch in zero_worker_cats)
            countermeasures.append(
                Countermeasure(
                    type=CountermeasureType.RECRUIT_WORKERS,
                    priority=priority,
                    category=cat_names,
                    description=(
                        f"Categories with ZERO workers: {cat_names} "
                        f"({total_expired} expired tasks). "
                        f"These tasks can never complete without category-specific workers."
                    ),
                    expected_impact=min(
                        total_expired / max(report.total_expired, 1), 1.0
                    ),
                    implementation=(
                        "1. Identify skills needed for each category\n"
                        "2. For code_execution: recruit developer-workers\n"
                        "3. For knowledge_access: recruit data analysts\n"
                        "4. For research: recruit researchers/students\n"
                        "5. Consider AI agent workers for digital categories"
                    ),
                    estimated_effort="high",
                )
            )
            priority += 1

        # 3. Bounty escalation for low-bounty expired tasks
        low_bounty_count = sum(
            1
            for d in report.diagnoses
            if d.primary_reason == ExpiryReason.LOW_BOUNTY
            or ExpiryReason.LOW_BOUNTY in d.secondary_reasons
        )
        if low_bounty_count > 0:
            countermeasures.append(
                Countermeasure(
                    type=CountermeasureType.ESCALATE_BOUNTY,
                    priority=priority,
                    description=(
                        f"{low_bounty_count} tasks expired with bounty below "
                        f"${self.low_bounty_threshold:.2f}. "
                        f"Implement automatic bounty escalation curve."
                    ),
                    expected_impact=0.15,
                    implementation=(
                        "1. At 50% deadline elapsed with no bids: increase bounty by 25%\n"
                        "2. At 75% deadline elapsed: increase by 50%\n"
                        "3. Set minimum effective bounty at $0.15 for any task\n"
                        "4. Notify task creator when escalation happens"
                    ),
                    estimated_effort="medium",
                )
            )
            priority += 1

        # 4. Deadline extension for tasks approaching expiry
        short_deadline_count = sum(
            1
            for d in report.diagnoses
            if d.primary_reason == ExpiryReason.SHORT_DEADLINE
        )
        if short_deadline_count > 5:
            countermeasures.append(
                Countermeasure(
                    type=CountermeasureType.EXTEND_DEADLINE,
                    priority=priority,
                    description=(
                        f"{short_deadline_count} tasks had deadlines under "
                        f"{self.short_deadline_hours}h. "
                        f"Auto-extend deadlines when no bids received."
                    ),
                    expected_impact=0.10,
                    implementation=(
                        "1. If no bids at 50% deadline: auto-extend by 2x\n"
                        "2. Maximum 2 auto-extensions per task\n"
                        "3. Notify creator of extension\n"
                        "4. Set minimum deadline of 4h for all tasks"
                    ),
                    estimated_effort="low",
                )
            )
            priority += 1

        # 5. Push notifications to matching workers
        if report.total_expired > 10:
            countermeasures.append(
                Countermeasure(
                    type=CountermeasureType.PUSH_NOTIFICATION,
                    priority=priority,
                    description=(
                        "Implement worker push notifications for new tasks "
                        "matching their skill categories."
                    ),
                    expected_impact=0.20,
                    implementation=(
                        "1. Track worker category preferences from completions\n"
                        "2. When new task posted: notify workers with matching skills\n"
                        "3. Channels: email, Telegram, in-app push\n"
                        "4. Frequency cap: max 5 notifications/day per worker"
                    ),
                    estimated_effort="medium",
                )
            )
            priority += 1

        # 6. Enable the swarm for automated task management
        countermeasures.append(
            Countermeasure(
                type=CountermeasureType.BATCH_TASKS,
                priority=priority,
                description=(
                    "Enable KK V2 Swarm in production (currently SWARM_ENABLED=false). "
                    "The swarm has 12.5K LOC, 1,082 tests, and 21 modules — "
                    "but it's never been activated. Start with passive mode."
                ),
                expected_impact=0.15,
                implementation=(
                    "1. Set SWARM_ENABLED=true, SWARM_MODE=passive in ECS\n"
                    "2. Verify /api/v1/swarm/status returns coordinator=active\n"
                    "3. Run 24h in passive mode — collect metrics\n"
                    "4. Graduate to semi-auto: auto-assign tasks <$0.25\n"
                    "5. Full-auto after 1 week of stable semi-auto"
                ),
                estimated_effort="low",
            )
        )
        priority += 1

        return countermeasures

    # ── Single Task Recommendation ────────────────────────────────────

    def recommend_for_task(
        self,
        task: dict,
        category_health: Optional[list[CategoryHealth]] = None,
    ) -> list[Countermeasure]:
        """
        Get recommendations for a specific task to prevent expiry.

        Useful for real-time intervention before a task expires.
        """
        recs = []
        category = task.get("category", "unknown")
        bounty = task.get("bounty_usd", 0) or 0
        title = task.get("title", "")

        # Check if category has workers
        if category_health:
            ch_lookup = {ch.category: ch for ch in category_health}
            ch = ch_lookup.get(category)
            if ch and ch.unique_workers == 0:
                recs.append(
                    Countermeasure(
                        type=CountermeasureType.RECRUIT_WORKERS,
                        priority=1,
                        category=category,
                        description=f"No workers for category '{category}'",
                        expected_impact=0.9,
                        implementation="Recruit workers with matching skills",
                        estimated_effort="high",
                    )
                )

        # Low bounty
        if bounty < self.low_bounty_threshold:
            recs.append(
                Countermeasure(
                    type=CountermeasureType.ESCALATE_BOUNTY,
                    priority=2,
                    description=f"Bounty ${bounty:.2f} is below ${self.low_bounty_threshold:.2f} threshold",
                    expected_impact=0.5,
                    implementation=f"Increase bounty to at least ${self.low_bounty_threshold:.2f}",
                    estimated_effort="low",
                )
            )

        # Short title
        if len(title.split()) < self.vague_title_min_words:
            recs.append(
                Countermeasure(
                    type=CountermeasureType.IMPROVE_INSTRUCTIONS,
                    priority=3,
                    description="Task title is too short/vague",
                    expected_impact=0.2,
                    implementation="Add clearer title and detailed instructions",
                    estimated_effort="low",
                )
            )

        return recs
