"""
Worker Probation System (NOW-174)

Manages new worker onboarding with limited task access.

New workers start in probation tier with:
- Maximum 10 tasks before graduation
- Maximum $5 per task value
- Extra verification requirements
- Closer agent oversight

This prevents:
- Sybil attacks (creating many accounts)
- Low-quality flooding
- Scam attempts from new accounts

Graduation criteria:
- Complete 10 tasks
- Maintain >3.5 average rating
- No disputes
- Valid identity verification
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class WorkerTier(str, Enum):
    """Worker trust tiers with progressive access."""
    PROBATION = "probation"      # First 10 tasks, max $5
    STANDARD = "standard"        # Normal access
    TRUSTED = "trusted"          # 50+ tasks, >4.5 rating
    EXPERT = "expert"            # 200+ tasks, specialized skills
    SUSPENDED = "suspended"      # Reputation too low or violations


@dataclass
class ProbationConfig:
    """Configuration for probation system."""
    # Task limits
    probation_task_count: int = 10
    probation_max_value: float = 5.00

    # Graduation requirements
    min_graduation_rating: float = 3.5
    max_disputes_allowed: int = 0
    require_identity_verification: bool = True

    # Trusted tier requirements
    trusted_task_count: int = 50
    trusted_min_rating: float = 4.5

    # Expert tier requirements
    expert_task_count: int = 200
    expert_min_rating: float = 4.7

    # Suspension thresholds
    suspension_rating_threshold: float = 2.0
    suspension_dispute_threshold: int = 3


@dataclass
class ProbationStatus:
    """Current probation status for a worker."""
    worker_id: str
    tier: WorkerTier
    tasks_completed: int
    average_rating: float
    total_disputes: int
    max_task_value: float
    extra_verification_required: bool
    identity_verified: bool
    graduated_at: Optional[datetime] = None
    tier_upgraded_at: Optional[datetime] = None
    suspension_reason: Optional[str] = None

    @property
    def is_probation(self) -> bool:
        """Check if worker is in probation."""
        return self.tier == WorkerTier.PROBATION

    @property
    def tasks_until_graduation(self) -> int:
        """Tasks remaining until graduation."""
        if self.tier != WorkerTier.PROBATION:
            return 0
        return max(0, 10 - self.tasks_completed)

    @property
    def can_graduate(self) -> bool:
        """Check if worker meets graduation criteria."""
        return (
            self.tasks_completed >= 10
            and self.average_rating >= 3.5
            and self.total_disputes == 0
            and self.identity_verified
        )


@dataclass
class TaskEligibility:
    """Eligibility result for a worker applying to a task."""
    eligible: bool
    reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    extra_verification: List[str] = field(default_factory=list)


class ProbationManager:
    """
    Manages worker probation lifecycle.

    Features:
    - Track probation progress
    - Enforce task value limits
    - Handle tier graduation
    - Apply extra verification requirements

    Example:
        >>> manager = ProbationManager()
        >>> status = await manager.get_status("worker_123")
        >>> eligibility = await manager.check_task_eligibility(
        ...     "worker_123", task_value=3.00
        ... )
        >>> if eligibility.eligible:
        ...     # Proceed with task assignment
        ...     pass
    """

    def __init__(self, config: Optional[ProbationConfig] = None):
        """Initialize with optional custom config."""
        self.config = config or ProbationConfig()
        self._cache: Dict[str, ProbationStatus] = {}

    async def get_status(
        self,
        worker_id: str,
        db_client: Optional[Any] = None
    ) -> ProbationStatus:
        """
        Get current probation status for a worker.

        Args:
            worker_id: Worker's unique identifier
            db_client: Optional database client for fetching data

        Returns:
            ProbationStatus with current tier and metrics
        """
        # Check cache first
        if worker_id in self._cache:
            return self._cache[worker_id]

        # Fetch from database or create new
        if db_client:
            status = await self._fetch_status(worker_id, db_client)
        else:
            # Return new worker status
            status = ProbationStatus(
                worker_id=worker_id,
                tier=WorkerTier.PROBATION,
                tasks_completed=0,
                average_rating=0.0,
                total_disputes=0,
                max_task_value=self.config.probation_max_value,
                extra_verification_required=True,
                identity_verified=False,
            )

        self._cache[worker_id] = status
        return status

    async def check_task_eligibility(
        self,
        worker_id: str,
        task_value: float,
        task_category: Optional[str] = None,
        requires_trust: bool = False,
        db_client: Optional[Any] = None
    ) -> TaskEligibility:
        """
        Check if a worker is eligible for a specific task.

        Args:
            worker_id: Worker's unique identifier
            task_value: Task bounty in USD
            task_category: Optional category for skill matching
            requires_trust: If task requires TRUSTED tier or higher
            db_client: Optional database client

        Returns:
            TaskEligibility with detailed eligibility info
        """
        status = await self.get_status(worker_id, db_client)
        warnings: List[str] = []
        extra_verification: List[str] = []

        # Check suspension
        if status.tier == WorkerTier.SUSPENDED:
            return TaskEligibility(
                eligible=False,
                reason=f"Account suspended: {status.suspension_reason or 'Contact support'}",
            )

        # Check trust requirement
        if requires_trust:
            if status.tier == WorkerTier.PROBATION:
                return TaskEligibility(
                    eligible=False,
                    reason="This task requires TRUSTED status. Complete more tasks to qualify.",
                )

        # Check task value limit for probation
        if status.tier == WorkerTier.PROBATION:
            if task_value > status.max_task_value:
                return TaskEligibility(
                    eligible=False,
                    reason=f"Maximum task value during probation: ${status.max_task_value:.2f}. "
                           f"Complete {status.tasks_until_graduation} more tasks to increase limit.",
                )

            # Add warnings for probation workers
            warnings.append(
                f"Probation status: {status.tasks_until_graduation} tasks until graduation"
            )

            # Extra verification for probation
            extra_verification.extend([
                "photo_selfie",        # Selfie with task evidence
                "realtime_timestamp",  # Cannot use old photos
            ])

            if not status.identity_verified:
                extra_verification.append("identity_document")
                warnings.append("Identity verification pending - limited task access")

        # Check if worker has recent disputes
        if status.total_disputes > 0:
            warnings.append(
                f"Note: {status.total_disputes} dispute(s) on record - "
                "extra scrutiny may apply"
            )

        return TaskEligibility(
            eligible=True,
            warnings=warnings,
            extra_verification=extra_verification,
        )

    async def record_task_completion(
        self,
        worker_id: str,
        task_id: str,
        rating: float,
        task_value: float,
        was_disputed: bool = False,
        db_client: Optional[Any] = None
    ) -> ProbationStatus:
        """
        Record a completed task and update probation status.

        Args:
            worker_id: Worker's unique identifier
            task_id: Completed task ID
            rating: Rating received (1-5)
            task_value: Task bounty value
            was_disputed: If task had a dispute
            db_client: Optional database client

        Returns:
            Updated ProbationStatus
        """
        status = await self.get_status(worker_id, db_client)

        # Update metrics
        old_total = status.tasks_completed * status.average_rating
        status.tasks_completed += 1
        status.average_rating = (old_total + rating) / status.tasks_completed

        if was_disputed:
            status.total_disputes += 1

        logger.info(
            f"Task completed for {worker_id}: "
            f"rating={rating}, tasks={status.tasks_completed}, "
            f"avg_rating={status.average_rating:.2f}"
        )

        # Check for tier changes
        status = await self._check_tier_changes(status, db_client)

        # Update cache
        self._cache[worker_id] = status

        return status

    async def record_identity_verification(
        self,
        worker_id: str,
        verified: bool,
        verification_method: str,
        db_client: Optional[Any] = None
    ) -> ProbationStatus:
        """
        Record identity verification result.

        Args:
            worker_id: Worker's unique identifier
            verified: Verification result
            verification_method: Method used (e.g., "passport", "drivers_license")
            db_client: Optional database client

        Returns:
            Updated ProbationStatus
        """
        status = await self.get_status(worker_id, db_client)
        status.identity_verified = verified

        if verified:
            logger.info(f"Identity verified for {worker_id} via {verification_method}")
        else:
            logger.warning(f"Identity verification failed for {worker_id}")

        # Check if can now graduate
        status = await self._check_tier_changes(status, db_client)

        self._cache[worker_id] = status
        return status

    async def suspend_worker(
        self,
        worker_id: str,
        reason: str,
        suspended_by: str,
        db_client: Optional[Any] = None
    ) -> ProbationStatus:
        """
        Suspend a worker account.

        Args:
            worker_id: Worker's unique identifier
            reason: Suspension reason
            suspended_by: Admin/system identifier
            db_client: Optional database client

        Returns:
            Updated ProbationStatus
        """
        status = await self.get_status(worker_id, db_client)

        old_tier = status.tier
        status.tier = WorkerTier.SUSPENDED
        status.suspension_reason = reason
        status.max_task_value = 0.0

        logger.warning(
            f"Worker {worker_id} suspended by {suspended_by}: {reason} "
            f"(was: {old_tier.value})"
        )

        self._cache[worker_id] = status
        return status

    async def _check_tier_changes(
        self,
        status: ProbationStatus,
        db_client: Optional[Any] = None
    ) -> ProbationStatus:
        """Check and apply tier upgrades/downgrades."""
        now = datetime.now(timezone.utc)

        # Check for suspension (low rating or too many disputes)
        if (
            status.average_rating < self.config.suspension_rating_threshold
            and status.tasks_completed >= 5
        ):
            status.tier = WorkerTier.SUSPENDED
            status.suspension_reason = "Rating below minimum threshold"
            status.max_task_value = 0.0
            logger.warning(f"Worker {status.worker_id} auto-suspended: low rating")
            return status

        if status.total_disputes >= self.config.suspension_dispute_threshold:
            status.tier = WorkerTier.SUSPENDED
            status.suspension_reason = "Too many disputes"
            status.max_task_value = 0.0
            logger.warning(f"Worker {status.worker_id} auto-suspended: too many disputes")
            return status

        # Check for graduation from probation
        if status.tier == WorkerTier.PROBATION and status.can_graduate:
            status.tier = WorkerTier.STANDARD
            status.graduated_at = now
            status.tier_upgraded_at = now
            status.max_task_value = 1000.0  # Standard limit
            status.extra_verification_required = False
            logger.info(f"Worker {status.worker_id} graduated to STANDARD tier")

        # Check for upgrade to TRUSTED
        if (
            status.tier == WorkerTier.STANDARD
            and status.tasks_completed >= self.config.trusted_task_count
            and status.average_rating >= self.config.trusted_min_rating
        ):
            status.tier = WorkerTier.TRUSTED
            status.tier_upgraded_at = now
            status.max_task_value = 5000.0  # Higher limit for trusted
            logger.info(f"Worker {status.worker_id} upgraded to TRUSTED tier")

        # Check for upgrade to EXPERT
        if (
            status.tier == WorkerTier.TRUSTED
            and status.tasks_completed >= self.config.expert_task_count
            and status.average_rating >= self.config.expert_min_rating
        ):
            status.tier = WorkerTier.EXPERT
            status.tier_upgraded_at = now
            status.max_task_value = 10000.0  # No practical limit for experts
            logger.info(f"Worker {status.worker_id} upgraded to EXPERT tier")

        return status

    async def _fetch_status(
        self,
        worker_id: str,
        db_client: Any
    ) -> ProbationStatus:
        """Fetch status from database."""
        # Query worker record
        result = db_client.table("workers").select(
            "id, tier, tasks_completed, average_rating, total_disputes, "
            "identity_verified, graduated_at, tier_upgraded_at, suspension_reason"
        ).eq("id", worker_id).single().execute()

        if not result.data:
            # New worker
            return ProbationStatus(
                worker_id=worker_id,
                tier=WorkerTier.PROBATION,
                tasks_completed=0,
                average_rating=0.0,
                total_disputes=0,
                max_task_value=self.config.probation_max_value,
                extra_verification_required=True,
                identity_verified=False,
            )

        data = result.data
        tier = WorkerTier(data.get("tier", "probation"))

        # Determine max task value based on tier
        max_value_map = {
            WorkerTier.PROBATION: self.config.probation_max_value,
            WorkerTier.STANDARD: 1000.0,
            WorkerTier.TRUSTED: 5000.0,
            WorkerTier.EXPERT: 10000.0,
            WorkerTier.SUSPENDED: 0.0,
        }

        return ProbationStatus(
            worker_id=worker_id,
            tier=tier,
            tasks_completed=data.get("tasks_completed", 0),
            average_rating=data.get("average_rating", 0.0),
            total_disputes=data.get("total_disputes", 0),
            max_task_value=max_value_map.get(tier, 5.0),
            extra_verification_required=tier == WorkerTier.PROBATION,
            identity_verified=data.get("identity_verified", False),
            graduated_at=data.get("graduated_at"),
            tier_upgraded_at=data.get("tier_upgraded_at"),
            suspension_reason=data.get("suspension_reason"),
        )

    def get_tier_benefits(self, tier: WorkerTier) -> Dict[str, Any]:
        """
        Get benefits and limits for a tier.

        Args:
            tier: Worker tier

        Returns:
            Dict with tier benefits
        """
        benefits = {
            WorkerTier.PROBATION: {
                "max_task_value": self.config.probation_max_value,
                "max_concurrent_tasks": 1,
                "priority_access": False,
                "premium_tasks": False,
                "instant_payout": False,
                "verification_level": "enhanced",
                "badge": None,
            },
            WorkerTier.STANDARD: {
                "max_task_value": 1000.0,
                "max_concurrent_tasks": 3,
                "priority_access": False,
                "premium_tasks": False,
                "instant_payout": False,
                "verification_level": "standard",
                "badge": "verified",
            },
            WorkerTier.TRUSTED: {
                "max_task_value": 5000.0,
                "max_concurrent_tasks": 5,
                "priority_access": True,
                "premium_tasks": True,
                "instant_payout": True,
                "verification_level": "minimal",
                "badge": "trusted",
            },
            WorkerTier.EXPERT: {
                "max_task_value": 10000.0,
                "max_concurrent_tasks": 10,
                "priority_access": True,
                "premium_tasks": True,
                "instant_payout": True,
                "verification_level": "minimal",
                "badge": "expert",
            },
            WorkerTier.SUSPENDED: {
                "max_task_value": 0.0,
                "max_concurrent_tasks": 0,
                "priority_access": False,
                "premium_tasks": False,
                "instant_payout": False,
                "verification_level": "blocked",
                "badge": "suspended",
            },
        }

        return benefits.get(tier, benefits[WorkerTier.PROBATION])

    def clear_cache(self, worker_id: Optional[str] = None):
        """
        Clear cached status.

        Args:
            worker_id: Specific worker to clear, or None for all
        """
        if worker_id:
            self._cache.pop(worker_id, None)
        else:
            self._cache.clear()
