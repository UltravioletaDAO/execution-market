"""
Worker Seal Management for Chamba (NOW-166)

Manages worker seals: SKILLFUL, RELIABLE, THOROUGH, ON_TIME

Worker seals are earned through consistent task performance and
are visible to agents when selecting workers for tasks.

Flow:
1. Worker completes task
2. System evaluates performance against seal criteria
3. If criteria met, seal is created on describe.net
4. If criteria no longer met, seal may be revoked
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple

from .seals import (
    WorkerSealType,
    Seal,
    SealCriteria,
    SealStatus,
    WORKER_SEAL_CRITERIA,
    get_seal_criteria,
)
from .client import DescribeNetClient, DescribeNetError

logger = logging.getLogger(__name__)


@dataclass
class WorkerMetrics:
    """
    Aggregated metrics for evaluating worker seal eligibility.

    These metrics are calculated from task history and used
    to determine if a worker qualifies for seals.
    """
    worker_id: str
    total_tasks: int = 0
    successful_tasks: int = 0
    disputed_tasks: int = 0
    on_time_tasks: int = 0
    average_rating: float = 0.0
    tasks_with_extra_evidence: int = 0
    first_task_date: Optional[datetime] = None
    last_task_date: Optional[datetime] = None
    lookback_start: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0-1)."""
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks

    @property
    def on_time_rate(self) -> float:
        """Calculate on-time completion rate (0-1)."""
        if self.total_tasks == 0:
            return 0.0
        return self.on_time_tasks / self.total_tasks

    @property
    def extra_evidence_rate(self) -> float:
        """Calculate rate of providing extra evidence (0-1)."""
        if self.total_tasks == 0:
            return 0.0
        return self.tasks_with_extra_evidence / self.total_tasks

    @property
    def days_active(self) -> int:
        """Calculate days since first task."""
        if not self.first_task_date:
            return 0
        delta = datetime.now(timezone.utc) - self.first_task_date.replace(tzinfo=timezone.utc)
        return max(0, delta.days)

    @property
    def has_recent_activity(self) -> bool:
        """Check if worker has task in last 30 days."""
        if not self.last_task_date:
            return False
        delta = datetime.now(timezone.utc) - self.last_task_date.replace(tzinfo=timezone.utc)
        return delta.days <= 30

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API/storage."""
        return {
            "worker_id": self.worker_id,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "disputed_tasks": self.disputed_tasks,
            "on_time_tasks": self.on_time_tasks,
            "average_rating": round(self.average_rating, 2),
            "tasks_with_extra_evidence": self.tasks_with_extra_evidence,
            "success_rate": round(self.success_rate, 3),
            "on_time_rate": round(self.on_time_rate, 3),
            "extra_evidence_rate": round(self.extra_evidence_rate, 3),
            "days_active": self.days_active,
            "has_recent_activity": self.has_recent_activity,
            "first_task_date": self.first_task_date.isoformat() if self.first_task_date else None,
            "last_task_date": self.last_task_date.isoformat() if self.last_task_date else None,
        }


class WorkerSealManager:
    """
    Manages worker seal lifecycle: evaluation, creation, and revocation.

    Usage:
        manager = WorkerSealManager(client)

        # After task completion
        result = await manager.evaluate_and_update(worker_id, metrics)
        for seal in result.seals_earned:
            print(f"Earned: {seal.seal_type}")
    """

    def __init__(
        self,
        client: Optional[DescribeNetClient] = None,
        local_mode: bool = False,
    ):
        """
        Initialize worker seal manager.

        Args:
            client: describe.net API client
            local_mode: If True, don't sync to describe.net (for testing)
        """
        self.client = client or DescribeNetClient.from_env()
        self.local_mode = local_mode
        self._seal_cache: Dict[str, List[Seal]] = {}

    async def evaluate_seal_eligibility(
        self,
        worker_id: str,
        metrics: WorkerMetrics,
    ) -> Dict[WorkerSealType, Tuple[bool, str]]:
        """
        Evaluate worker's eligibility for each seal type.

        Args:
            worker_id: Worker ID
            metrics: Current worker metrics

        Returns:
            Dict mapping seal type to (eligible, reason)
        """
        results = {}

        for seal_type, criteria in WORKER_SEAL_CRITERIA.items():
            eligible, reason = self._check_criteria(seal_type, criteria, metrics)
            results[seal_type] = (eligible, reason)

        return results

    def _check_criteria(
        self,
        seal_type: WorkerSealType,
        criteria: SealCriteria,
        metrics: WorkerMetrics,
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
        if metrics.total_tasks < criteria.min_tasks:
            return False, f"Need {criteria.min_tasks} tasks, have {metrics.total_tasks}"

        # Check success rate
        if metrics.success_rate < criteria.min_success_rate:
            return False, f"Success rate {metrics.success_rate:.1%} < {criteria.min_success_rate:.1%}"

        # Check rating
        if metrics.average_rating < criteria.min_rating:
            return False, f"Rating {metrics.average_rating:.1f} < {criteria.min_rating}"

        # Check on-time rate
        if metrics.on_time_rate < criteria.min_on_time_rate:
            return False, f"On-time rate {metrics.on_time_rate:.1%} < {criteria.min_on_time_rate:.1%}"

        # Check days active
        if metrics.days_active < criteria.min_days_active:
            return False, f"Active {metrics.days_active} days < {criteria.min_days_active} required"

        # Check custom criteria
        if criteria.custom_criteria:
            for key, threshold in criteria.custom_criteria.items():
                if key == "min_extra_evidence_rate":
                    if metrics.extra_evidence_rate < threshold:
                        return False, f"Extra evidence rate {metrics.extra_evidence_rate:.1%} < {threshold:.1%}"

        return True, "All criteria met"

    async def evaluate_and_update(
        self,
        worker_id: str,
        metrics: WorkerMetrics,
    ) -> "SealUpdateResult":
        """
        Evaluate worker and update seals on describe.net.

        This is the main entry point called after task completion.

        Args:
            worker_id: Worker ID
            metrics: Current worker metrics

        Returns:
            SealUpdateResult with earned/revoked seals
        """
        # Get current seals
        current_seals = await self.get_worker_seals(worker_id)
        current_seal_types = {s.seal_type for s in current_seals if s.is_active}

        # Evaluate eligibility for all seals
        eligibility = await self.evaluate_seal_eligibility(worker_id, metrics)

        seals_earned = []
        seals_revoked = []

        for seal_type, (eligible, reason) in eligibility.items():
            has_seal = seal_type.value in current_seal_types

            if eligible and not has_seal:
                # Earn new seal
                seal = await self.create_seal(worker_id, seal_type, metrics)
                if seal:
                    seals_earned.append(seal)
                    logger.info(f"Worker {worker_id} earned seal: {seal_type.value}")

            elif not eligible and has_seal:
                # Consider revocation (with grace period)
                existing_seal = next(
                    (s for s in current_seals if s.seal_type == seal_type.value),
                    None
                )
                if existing_seal and self._should_revoke(existing_seal, reason):
                    revoked = await self.revoke_seal(existing_seal, reason)
                    if revoked:
                        seals_revoked.append(existing_seal)
                        logger.info(f"Worker {worker_id} lost seal: {seal_type.value} - {reason}")

        return SealUpdateResult(
            worker_id=worker_id,
            seals_earned=seals_earned,
            seals_revoked=seals_revoked,
            current_seals=await self.get_worker_seals(worker_id),
            eligibility=eligibility,
            metrics=metrics,
        )

    def _should_revoke(self, seal: Seal, reason: str) -> bool:
        """
        Determine if a seal should be revoked.

        Implements a grace period to avoid revoking for temporary dips.
        """
        # If seal was earned recently (< 14 days), don't revoke yet
        if seal.earned_at:
            days_since_earned = (datetime.now(timezone.utc) - seal.earned_at.replace(tzinfo=timezone.utc)).days
            if days_since_earned < 14:
                logger.debug(f"Seal {seal.seal_type} in grace period, not revoking")
                return False

        # Always revoke for serious reasons
        serious_reasons = ["dispute", "fraud", "violation"]
        if any(r in reason.lower() for r in serious_reasons):
            return True

        # For performance-based reasons, require sustained underperformance
        # This would be enhanced with historical tracking
        return True

    async def create_seal(
        self,
        worker_id: str,
        seal_type: WorkerSealType,
        metrics: WorkerMetrics,
    ) -> Optional[Seal]:
        """
        Create a new seal for a worker.

        Args:
            worker_id: Worker ID
            seal_type: Type of seal to create
            metrics: Current metrics (saved as snapshot)

        Returns:
            Created Seal or None on failure
        """
        if self.local_mode:
            # Local mode - create seal without API
            seal = Seal(
                seal_type=seal_type.value,
                user_id=worker_id,
                user_type="worker",
                status=SealStatus.ACTIVE,
                earned_at=datetime.now(timezone.utc),
                criteria_snapshot=metrics.to_dict(),
            )
            self._update_cache(worker_id, seal)
            return seal

        try:
            seal = await self.client.create_seal(
                seal_type=seal_type,
                user_id=worker_id,
                user_type="worker",
                criteria_snapshot=metrics.to_dict(),
            )
            self._update_cache(worker_id, seal)
            return seal

        except DescribeNetError as e:
            logger.error(f"Failed to create seal {seal_type.value} for {worker_id}: {e}")
            return None

    async def revoke_seal(
        self,
        seal: Seal,
        reason: str,
    ) -> bool:
        """
        Revoke a worker's seal.

        Args:
            seal: Seal to revoke
            reason: Reason for revocation

        Returns:
            True if revoked successfully
        """
        if self.local_mode:
            seal.status = SealStatus.REVOKED
            seal.revoked_at = datetime.now(timezone.utc)
            seal.revocation_reason = reason
            return True

        if not seal.describe_net_id:
            logger.warning(f"Cannot revoke seal without describe_net_id")
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

    async def get_worker_seals(
        self,
        worker_id: str,
        active_only: bool = True,
    ) -> List[Seal]:
        """
        Get all seals for a worker.

        Args:
            worker_id: Worker ID
            active_only: Only return active seals

        Returns:
            List of worker's seals
        """
        if self.local_mode:
            seals = self._seal_cache.get(worker_id, [])
            if active_only:
                return [s for s in seals if s.is_active]
            return seals

        try:
            return await self.client.get_user_seals(
                user_id=worker_id,
                user_type="worker",
                active_only=active_only,
            )
        except DescribeNetError as e:
            logger.error(f"Failed to get seals for {worker_id}: {e}")
            return self._seal_cache.get(worker_id, [])

    def _update_cache(self, worker_id: str, seal: Seal):
        """Update local seal cache."""
        if worker_id not in self._seal_cache:
            self._seal_cache[worker_id] = []

        # Remove existing seal of same type
        self._seal_cache[worker_id] = [
            s for s in self._seal_cache[worker_id]
            if s.seal_type != seal.seal_type
        ]
        self._seal_cache[worker_id].append(seal)

    async def get_seal_display(
        self,
        worker_id: str,
    ) -> Dict[str, Any]:
        """
        Get formatted seal display for worker profile.

        Returns display-ready seal information for UI.
        """
        seals = await self.get_worker_seals(worker_id, active_only=True)

        seal_icons = {
            WorkerSealType.SKILLFUL.value: "[S]",  # Star
            WorkerSealType.RELIABLE.value: "[R]",  # Shield
            WorkerSealType.THOROUGH.value: "[T]",  # Magnifier
            WorkerSealType.ON_TIME.value: "[C]",   # Clock
        }

        seal_descriptions = {
            WorkerSealType.SKILLFUL.value: "Consistently delivers high-quality work",
            WorkerSealType.RELIABLE.value: "Dependable, completes commitments",
            WorkerSealType.THOROUGH.value: "Goes beyond requirements",
            WorkerSealType.ON_TIME.value: "Meets deadlines consistently",
        }

        return {
            "worker_id": worker_id,
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
            "reputation_boost": len(seals) * 5,  # Each seal adds +5 to matching priority
        }


@dataclass
class SealUpdateResult:
    """Result of seal evaluation and update."""
    worker_id: str
    seals_earned: List[Seal]
    seals_revoked: List[Seal]
    current_seals: List[Seal]
    eligibility: Dict[WorkerSealType, Tuple[bool, str]]
    metrics: WorkerMetrics

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "worker_id": self.worker_id,
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

def calculate_worker_metrics_from_tasks(
    worker_id: str,
    tasks: List[Dict[str, Any]],
    lookback_days: int = 90,
) -> WorkerMetrics:
    """
    Calculate worker metrics from task history.

    Args:
        worker_id: Worker ID
        tasks: List of task records
        lookback_days: Days to look back

    Returns:
        Calculated WorkerMetrics
    """
    now = datetime.now(timezone.utc)
    lookback_start = now - timedelta(days=lookback_days)

    metrics = WorkerMetrics(worker_id=worker_id, lookback_start=lookback_start)

    if not tasks:
        return metrics

    # Filter to lookback window
    relevant_tasks = []
    for task in tasks:
        completed_at = task.get("completed_at")
        if completed_at:
            if isinstance(completed_at, str):
                completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            if completed_at >= lookback_start:
                relevant_tasks.append(task)

    if not relevant_tasks:
        return metrics

    # Calculate metrics
    ratings = []
    for task in relevant_tasks:
        metrics.total_tasks += 1

        if task.get("status") == "completed":
            metrics.successful_tasks += 1

        if task.get("disputed"):
            metrics.disputed_tasks += 1

        if task.get("on_time", True):  # Default to on-time if not specified
            metrics.on_time_tasks += 1

        if task.get("extra_evidence_provided"):
            metrics.tasks_with_extra_evidence += 1

        if task.get("rating"):
            ratings.append(task["rating"])

        completed_at = task.get("completed_at")
        if completed_at:
            if isinstance(completed_at, str):
                completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))

            if metrics.first_task_date is None or completed_at < metrics.first_task_date:
                metrics.first_task_date = completed_at

            if metrics.last_task_date is None or completed_at > metrics.last_task_date:
                metrics.last_task_date = completed_at

    if ratings:
        metrics.average_rating = sum(ratings) / len(ratings)

    return metrics
