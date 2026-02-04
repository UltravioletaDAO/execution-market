"""
Requester Seal Management for Execution Market (NOW-167, NOW-170)

Manages requester (agent) seals: FAIR_EVALUATOR, CLEAR_INSTRUCTIONS, FAST_PAYMENT

Requester seals create bidirectional accountability:
- Workers can filter tasks by requester reputation
- Bad actors get fewer applications
- Good requesters get priority matching

NOW-170: Worker-side filtering by requester reputation
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple

from .seals import (
    RequesterSealType,
    Seal,
    SealCriteria,
    SealStatus,
    REQUESTER_SEAL_CRITERIA,
)
from .client import DescribeNetClient, DescribeNetError

logger = logging.getLogger(__name__)


@dataclass
class RequesterMetrics:
    """
    Aggregated metrics for evaluating requester seal eligibility.

    These metrics are calculated from task history and used
    to determine if a requester qualifies for seals.
    """
    requester_id: str
    total_tasks_posted: int = 0
    tasks_completed: int = 0
    tasks_disputed: int = 0
    tasks_cancelled: int = 0
    submissions_accepted: int = 0
    submissions_rejected: int = 0
    clarifications_requested: int = 0
    first_submission_accepts: int = 0  # Accepted on first try
    payment_times_hours: List[float] = None  # Hours to release payment
    first_task_date: Optional[datetime] = None
    last_task_date: Optional[datetime] = None
    lookback_start: Optional[datetime] = None

    def __post_init__(self):
        if self.payment_times_hours is None:
            self.payment_times_hours = []

    @property
    def acceptance_rate(self) -> float:
        """Calculate submission acceptance rate (0-1)."""
        total = self.submissions_accepted + self.submissions_rejected
        if total == 0:
            return 0.0
        return self.submissions_accepted / total

    @property
    def dispute_rate(self) -> float:
        """Calculate dispute rate (0-1)."""
        if self.total_tasks_posted == 0:
            return 0.0
        return self.tasks_disputed / self.total_tasks_posted

    @property
    def clarification_rate(self) -> float:
        """Calculate rate of tasks needing clarification (0-1)."""
        if self.total_tasks_posted == 0:
            return 0.0
        return self.clarifications_requested / self.total_tasks_posted

    @property
    def first_submission_accept_rate(self) -> float:
        """Calculate rate of first submission acceptance (0-1)."""
        if self.tasks_completed == 0:
            return 0.0
        return self.first_submission_accepts / self.tasks_completed

    @property
    def median_payment_hours(self) -> float:
        """Calculate median time to release payment."""
        if not self.payment_times_hours:
            return float('inf')
        sorted_times = sorted(self.payment_times_hours)
        n = len(sorted_times)
        if n % 2 == 0:
            return (sorted_times[n//2 - 1] + sorted_times[n//2]) / 2
        return sorted_times[n//2]

    @property
    def payment_hours_p95(self) -> float:
        """Calculate 95th percentile payment time."""
        if not self.payment_times_hours:
            return float('inf')
        sorted_times = sorted(self.payment_times_hours)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]

    @property
    def has_recent_activity(self) -> bool:
        """Check if requester has task in last 30 days."""
        if not self.last_task_date:
            return False
        delta = datetime.now(timezone.utc) - self.last_task_date.replace(tzinfo=timezone.utc)
        return delta.days <= 30

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API/storage."""
        return {
            "requester_id": self.requester_id,
            "total_tasks_posted": self.total_tasks_posted,
            "tasks_completed": self.tasks_completed,
            "tasks_disputed": self.tasks_disputed,
            "tasks_cancelled": self.tasks_cancelled,
            "submissions_accepted": self.submissions_accepted,
            "submissions_rejected": self.submissions_rejected,
            "clarifications_requested": self.clarifications_requested,
            "first_submission_accepts": self.first_submission_accepts,
            "acceptance_rate": round(self.acceptance_rate, 3),
            "dispute_rate": round(self.dispute_rate, 3),
            "clarification_rate": round(self.clarification_rate, 3),
            "first_submission_accept_rate": round(self.first_submission_accept_rate, 3),
            "median_payment_hours": round(self.median_payment_hours, 2),
            "payment_hours_p95": round(self.payment_hours_p95, 2),
            "has_recent_activity": self.has_recent_activity,
            "first_task_date": self.first_task_date.isoformat() if self.first_task_date else None,
            "last_task_date": self.last_task_date.isoformat() if self.last_task_date else None,
        }


class RequesterSealManager:
    """
    Manages requester seal lifecycle: evaluation, creation, and revocation.

    Also provides worker-side filtering by requester reputation (NOW-170).

    Usage:
        manager = RequesterSealManager(client)

        # After task completion
        result = await manager.evaluate_and_update(requester_id, metrics)

        # Worker filtering tasks by requester quality
        filtered = await manager.filter_tasks_by_requester_quality(tasks, min_seals=1)
    """

    def __init__(
        self,
        client: Optional[DescribeNetClient] = None,
        local_mode: bool = False,
    ):
        """
        Initialize requester seal manager.

        Args:
            client: describe.net API client
            local_mode: If True, don't sync to describe.net (for testing)
        """
        self.client = client or DescribeNetClient.from_env()
        self.local_mode = local_mode
        self._seal_cache: Dict[str, List[Seal]] = {}

    async def evaluate_seal_eligibility(
        self,
        requester_id: str,
        metrics: RequesterMetrics,
    ) -> Dict[RequesterSealType, Tuple[bool, str]]:
        """
        Evaluate requester's eligibility for each seal type.

        Args:
            requester_id: Requester ID
            metrics: Current requester metrics

        Returns:
            Dict mapping seal type to (eligible, reason)
        """
        results = {}

        for seal_type, criteria in REQUESTER_SEAL_CRITERIA.items():
            eligible, reason = self._check_criteria(seal_type, criteria, metrics)
            results[seal_type] = (eligible, reason)

        return results

    def _check_criteria(
        self,
        seal_type: RequesterSealType,
        criteria: SealCriteria,
        metrics: RequesterMetrics,
    ) -> Tuple[bool, str]:
        """
        Check if metrics meet criteria for a seal.

        Returns:
            (eligible, reason) tuple
        """
        # Check recent activity
        if criteria.require_recent_activity and not metrics.has_recent_activity:
            return False, "No recent activity (30 days)"

        # Check minimum tasks
        if metrics.total_tasks_posted < criteria.min_tasks:
            return False, f"Need {criteria.min_tasks} tasks, have {metrics.total_tasks_posted}"

        # Check custom criteria based on seal type
        custom = criteria.custom_criteria or {}

        if seal_type == RequesterSealType.FAIR_EVALUATOR:
            # Check acceptance rate (min_success_rate maps to acceptance)
            if metrics.acceptance_rate < criteria.min_success_rate:
                return False, f"Acceptance rate {metrics.acceptance_rate:.1%} < {criteria.min_success_rate:.1%}"
            # Check dispute rate
            max_dispute = custom.get("max_dispute_rate", 0.10)
            if metrics.dispute_rate > max_dispute:
                return False, f"Dispute rate {metrics.dispute_rate:.1%} > {max_dispute:.1%}"

        elif seal_type == RequesterSealType.CLEAR_INSTRUCTIONS:
            # Check clarification rate
            max_clarification = custom.get("max_clarification_rate", 0.15)
            if metrics.clarification_rate > max_clarification:
                return False, f"Clarification rate {metrics.clarification_rate:.1%} > {max_clarification:.1%}"
            # Check first submission acceptance
            min_first_accept = custom.get("min_first_submission_accept", 0.70)
            if metrics.first_submission_accept_rate < min_first_accept:
                return False, f"First-try accept rate {metrics.first_submission_accept_rate:.1%} < {min_first_accept:.1%}"

        elif seal_type == RequesterSealType.FAST_PAYMENT:
            # Check median payment time
            max_median = custom.get("median_payment_hours", 24)
            if metrics.median_payment_hours > max_median:
                return False, f"Median payment time {metrics.median_payment_hours:.1f}h > {max_median}h"
            # Check 95th percentile
            max_p95 = custom.get("max_payment_hours_p95", 72)
            if metrics.payment_hours_p95 > max_p95:
                return False, f"P95 payment time {metrics.payment_hours_p95:.1f}h > {max_p95}h"

        return True, "All criteria met"

    async def evaluate_and_update(
        self,
        requester_id: str,
        metrics: RequesterMetrics,
    ) -> "RequesterSealUpdateResult":
        """
        Evaluate requester and update seals on describe.net.

        This is called after task completion/payment.

        Args:
            requester_id: Requester ID
            metrics: Current requester metrics

        Returns:
            RequesterSealUpdateResult with earned/revoked seals
        """
        # Get current seals
        current_seals = await self.get_requester_seals(requester_id)
        current_seal_types = {s.seal_type for s in current_seals if s.is_active}

        # Evaluate eligibility for all seals
        eligibility = await self.evaluate_seal_eligibility(requester_id, metrics)

        seals_earned = []
        seals_revoked = []

        for seal_type, (eligible, reason) in eligibility.items():
            has_seal = seal_type.value in current_seal_types

            if eligible and not has_seal:
                # Earn new seal
                seal = await self.create_seal(requester_id, seal_type, metrics)
                if seal:
                    seals_earned.append(seal)
                    logger.info(f"Requester {requester_id} earned seal: {seal_type.value}")

            elif not eligible and has_seal:
                # Consider revocation
                existing_seal = next(
                    (s for s in current_seals if s.seal_type == seal_type.value),
                    None
                )
                if existing_seal and self._should_revoke(existing_seal, reason):
                    revoked = await self.revoke_seal(existing_seal, reason)
                    if revoked:
                        seals_revoked.append(existing_seal)
                        logger.info(f"Requester {requester_id} lost seal: {seal_type.value} - {reason}")

        return RequesterSealUpdateResult(
            requester_id=requester_id,
            seals_earned=seals_earned,
            seals_revoked=seals_revoked,
            current_seals=await self.get_requester_seals(requester_id),
            eligibility=eligibility,
            metrics=metrics,
        )

    def _should_revoke(self, seal: Seal, reason: str) -> bool:
        """Determine if a seal should be revoked."""
        # Grace period for recent seals
        if seal.earned_at:
            days_since_earned = (datetime.now(timezone.utc) - seal.earned_at.replace(tzinfo=timezone.utc)).days
            if days_since_earned < 14:
                return False
        return True

    async def create_seal(
        self,
        requester_id: str,
        seal_type: RequesterSealType,
        metrics: RequesterMetrics,
    ) -> Optional[Seal]:
        """Create a new seal for a requester."""
        if self.local_mode:
            seal = Seal(
                seal_type=seal_type.value,
                user_id=requester_id,
                user_type="requester",
                status=SealStatus.ACTIVE,
                earned_at=datetime.now(timezone.utc),
                criteria_snapshot=metrics.to_dict(),
            )
            self._update_cache(requester_id, seal)
            return seal

        try:
            seal = await self.client.create_seal(
                seal_type=seal_type,
                user_id=requester_id,
                user_type="requester",
                criteria_snapshot=metrics.to_dict(),
            )
            self._update_cache(requester_id, seal)
            return seal

        except DescribeNetError as e:
            logger.error(f"Failed to create seal {seal_type.value} for {requester_id}: {e}")
            return None

    async def revoke_seal(self, seal: Seal, reason: str) -> bool:
        """Revoke a requester's seal."""
        if self.local_mode:
            seal.status = SealStatus.REVOKED
            seal.revoked_at = datetime.now(timezone.utc)
            seal.revocation_reason = reason
            return True

        if not seal.describe_net_id:
            return False

        try:
            success = await self.client.revoke_seal(seal.describe_net_id, reason)
            if success:
                seal.status = SealStatus.REVOKED
                seal.revoked_at = datetime.now(timezone.utc)
                seal.revocation_reason = reason
            return success
        except DescribeNetError as e:
            logger.error(f"Failed to revoke seal: {e}")
            return False

    async def get_requester_seals(
        self,
        requester_id: str,
        active_only: bool = True,
    ) -> List[Seal]:
        """Get all seals for a requester."""
        if self.local_mode:
            seals = self._seal_cache.get(requester_id, [])
            if active_only:
                return [s for s in seals if s.is_active]
            return seals

        try:
            return await self.client.get_user_seals(
                user_id=requester_id,
                user_type="requester",
                active_only=active_only,
            )
        except DescribeNetError as e:
            logger.error(f"Failed to get seals for {requester_id}: {e}")
            return self._seal_cache.get(requester_id, [])

    def _update_cache(self, requester_id: str, seal: Seal):
        """Update local seal cache."""
        if requester_id not in self._seal_cache:
            self._seal_cache[requester_id] = []
        self._seal_cache[requester_id] = [
            s for s in self._seal_cache[requester_id]
            if s.seal_type != seal.seal_type
        ]
        self._seal_cache[requester_id].append(seal)

    # ============== WORKER-SIDE FILTERING (NOW-170) ==============

    async def filter_tasks_by_requester_quality(
        self,
        tasks: List[Dict[str, Any]],
        min_seals: int = 0,
        required_seals: Optional[List[RequesterSealType]] = None,
        exclude_without_seals: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Filter tasks based on requester reputation seals.

        This enables workers to choose tasks from quality requesters.

        Args:
            tasks: List of task dictionaries (must have 'agent_id')
            min_seals: Minimum number of seals requester must have
            required_seals: Specific seals requester must have
            exclude_without_seals: If True, exclude requesters with 0 seals

        Returns:
            Filtered and sorted list of tasks
        """
        if not tasks:
            return []

        # Get unique requester IDs
        requester_ids = {t.get("agent_id") for t in tasks if t.get("agent_id")}

        # Fetch seals for all requesters
        requester_seals: Dict[str, List[Seal]] = {}
        for rid in requester_ids:
            requester_seals[rid] = await self.get_requester_seals(rid)

        filtered_tasks = []
        for task in tasks:
            agent_id = task.get("agent_id")
            if not agent_id:
                continue

            seals = requester_seals.get(agent_id, [])
            seal_count = len(seals)
            seal_types = {s.seal_type for s in seals}

            # Apply filters
            if exclude_without_seals and seal_count == 0:
                continue

            if seal_count < min_seals:
                continue

            if required_seals:
                required_values = {s.value for s in required_seals}
                if not required_values.issubset(seal_types):
                    continue

            # Add seal info to task
            task_with_seals = {
                **task,
                "_requester_seals": [s.to_dict() for s in seals],
                "_requester_seal_count": seal_count,
            }
            filtered_tasks.append(task_with_seals)

        # Sort by requester quality (more seals = higher priority)
        filtered_tasks.sort(key=lambda t: t.get("_requester_seal_count", 0), reverse=True)

        return filtered_tasks

    async def get_requester_reputation_display(
        self,
        requester_id: str,
    ) -> Dict[str, Any]:
        """
        Get formatted seal display for requester profile.

        Shown to workers considering a task.
        """
        seals = await self.get_requester_seals(requester_id, active_only=True)

        seal_icons = {
            RequesterSealType.FAIR_EVALUATOR.value: "[F]",      # Scales
            RequesterSealType.CLEAR_INSTRUCTIONS.value: "[I]",  # Document
            RequesterSealType.FAST_PAYMENT.value: "[P]",        # Lightning
        }

        seal_descriptions = {
            RequesterSealType.FAIR_EVALUATOR.value: "Accepts reasonable work fairly",
            RequesterSealType.CLEAR_INSTRUCTIONS.value: "Writes clear task specs",
            RequesterSealType.FAST_PAYMENT.value: "Pays promptly after approval",
        }

        # Calculate trust level
        trust_levels = {
            0: ("new", "New requester - no track record"),
            1: ("emerging", "Building reputation"),
            2: ("established", "Good track record"),
            3: ("trusted", "Excellent track record"),
        }
        trust_level, trust_desc = trust_levels.get(len(seals), trust_levels[3])

        return {
            "requester_id": requester_id,
            "seals": [
                {
                    "type": s.seal_type,
                    "icon": seal_icons.get(s.seal_type, "[?]"),
                    "description": seal_descriptions.get(s.seal_type, ""),
                    "earned_at": s.earned_at.isoformat() if s.earned_at else None,
                }
                for s in seals
            ],
            "seal_count": len(seals),
            "trust_level": trust_level,
            "trust_description": trust_desc,
            "worker_advice": self._get_worker_advice(seals),
        }

    def _get_worker_advice(self, seals: List[Seal]) -> str:
        """Generate advice for worker based on requester seals."""
        seal_types = {s.seal_type for s in seals}

        if not seals:
            return "New requester. Consider starting with smaller tasks."

        advice_parts = []

        if RequesterSealType.FAIR_EVALUATOR.value in seal_types:
            advice_parts.append("Fair evaluator - your work will be judged reasonably.")

        if RequesterSealType.CLEAR_INSTRUCTIONS.value in seal_types:
            advice_parts.append("Clear instructions - task requirements are well-defined.")

        if RequesterSealType.FAST_PAYMENT.value in seal_types:
            advice_parts.append("Fast payment - expect quick payment after approval.")

        if len(seals) == 3:
            return "Excellent requester with all seals. Highly recommended."

        return " ".join(advice_parts) if advice_parts else "Good requester track record."


@dataclass
class RequesterSealUpdateResult:
    """Result of requester seal evaluation and update."""
    requester_id: str
    seals_earned: List[Seal]
    seals_revoked: List[Seal]
    current_seals: List[Seal]
    eligibility: Dict[RequesterSealType, Tuple[bool, str]]
    metrics: RequesterMetrics

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "requester_id": self.requester_id,
            "seals_earned": [s.to_dict() for s in self.seals_earned],
            "seals_revoked": [s.to_dict() for s in self.seals_revoked],
            "current_seals": [s.to_dict() for s in self.current_seals],
            "eligibility": {
                k.value: {"eligible": v[0], "reason": v[1]}
                for k, v in self.eligibility.items()
            },
            "metrics": self.metrics.to_dict(),
        }


# ============== UTILITY FUNCTIONS ==============

def calculate_requester_metrics_from_tasks(
    requester_id: str,
    tasks: List[Dict[str, Any]],
    lookback_days: int = 90,
) -> RequesterMetrics:
    """
    Calculate requester metrics from task history.

    Args:
        requester_id: Requester ID
        tasks: List of task records
        lookback_days: Days to look back

    Returns:
        Calculated RequesterMetrics
    """
    now = datetime.now(timezone.utc)
    lookback_start = now - timedelta(days=lookback_days)

    metrics = RequesterMetrics(requester_id=requester_id, lookback_start=lookback_start)

    if not tasks:
        return metrics

    # Filter to lookback window
    relevant_tasks = []
    for task in tasks:
        created_at = task.get("created_at")
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if created_at >= lookback_start:
                relevant_tasks.append(task)

    if not relevant_tasks:
        return metrics

    # Calculate metrics
    payment_times = []
    for task in relevant_tasks:
        metrics.total_tasks_posted += 1

        status = task.get("status")
        if status == "completed":
            metrics.tasks_completed += 1

            # Check if accepted on first submission
            if task.get("first_submission_accepted"):
                metrics.first_submission_accepts += 1

            # Calculate payment time
            completed_at = task.get("completed_at")
            paid_at = task.get("paid_at")
            if completed_at and paid_at:
                if isinstance(completed_at, str):
                    completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                if isinstance(paid_at, str):
                    paid_at = datetime.fromisoformat(paid_at.replace("Z", "+00:00"))
                hours = (paid_at - completed_at).total_seconds() / 3600
                payment_times.append(hours)

        elif status == "disputed":
            metrics.tasks_disputed += 1

        elif status == "cancelled":
            metrics.tasks_cancelled += 1

        # Count submissions
        metrics.submissions_accepted += task.get("submissions_accepted", 0)
        metrics.submissions_rejected += task.get("submissions_rejected", 0)

        if task.get("clarification_requested"):
            metrics.clarifications_requested += 1

        # Track dates
        created_at = task.get("created_at")
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

            if metrics.first_task_date is None or created_at < metrics.first_task_date:
                metrics.first_task_date = created_at

            if metrics.last_task_date is None or created_at > metrics.last_task_date:
                metrics.last_task_date = created_at

    metrics.payment_times_hours = payment_times

    return metrics
