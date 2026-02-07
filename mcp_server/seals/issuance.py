"""
Seal Issuance Logic

Handles the business logic for issuing seals:
- Checking eligibility based on requirements
- Automatic issuance for milestone seals
- Manual issuance workflow for skill seals
- Batch processing for efficiency

Issuance Flows:
1. AUTOMATIC: Worker meets criteria -> system issues seal
2. TEST_TASK: Worker completes test -> reviewer approves -> system issues
3. PORTFOLIO: Worker submits portfolio -> reviewer approves -> system issues
4. ADMIN: Admin manually issues (rare cases)
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass

from .types import (
    Seal,
    SealCategory,
    SealRequirement,
    VerificationMethod,
    BehaviorSealType,
    get_requirement,
    get_automatic_seals,
)
from .registry import SealRegistry, MockSealRegistry

logger = logging.getLogger(__name__)


@dataclass
class WorkerStats:
    """
    Worker statistics for eligibility checking.

    Collected from database/API before eligibility check.
    """

    wallet_address: str
    total_tasks_completed: int = 0
    total_earnings_usd: float = 0.0
    average_rating: float = 50.0
    active_days: int = 0
    cancellation_count: int = 0
    avg_response_time_minutes: float = 60.0

    # Category-specific
    tasks_by_category: Dict[str, int] = None
    ratings_by_category: Dict[str, float] = None

    # Behavioral
    on_time_percentage: float = 100.0
    rating_variance: float = 10.0

    def __post_init__(self):
        if self.tasks_by_category is None:
            self.tasks_by_category = {}
        if self.ratings_by_category is None:
            self.ratings_by_category = {}


@dataclass
class EligibilityResult:
    """Result of eligibility check."""

    is_eligible: bool
    seal_type: str
    reason: str
    missing_requirements: List[str] = None

    def __post_init__(self):
        if self.missing_requirements is None:
            self.missing_requirements = []


@dataclass
class IssuanceResult:
    """Result of seal issuance attempt."""

    success: bool
    seal_type: str
    tx_hash: Optional[str] = None
    error: Optional[str] = None
    seal: Optional[Seal] = None


class SealIssuanceService:
    """
    Service for managing seal issuance.

    Handles eligibility checking and issuance coordination.

    Example:
        >>> service = SealIssuanceService(registry)
        >>> stats = WorkerStats(
        ...     wallet_address="0x1234...",
        ...     total_tasks_completed=100,
        ...     average_rating=92.0
        ... )
        >>> results = await service.check_and_issue_automatic(stats)
        >>> for result in results:
        ...     if result.success:
        ...         print(f"Issued: {result.seal_type}")
    """

    def __init__(self, registry: SealRegistry | MockSealRegistry):
        """
        Initialize issuance service.

        Args:
            registry: SealRegistry instance for on-chain operations
        """
        self.registry = registry

    # =========================================================================
    # ELIGIBILITY CHECKING
    # =========================================================================

    def check_eligibility(
        self, stats: WorkerStats, requirement: SealRequirement
    ) -> EligibilityResult:
        """
        Check if a worker is eligible for a specific seal.

        Args:
            stats: Worker's current statistics
            requirement: Seal requirement to check against

        Returns:
            EligibilityResult with eligibility status and details
        """
        missing = []

        # Check minimum tasks
        if requirement.min_tasks is not None:
            if requirement.task_category:
                # Category-specific task count
                category_tasks = stats.tasks_by_category.get(
                    requirement.task_category, 0
                )
                if category_tasks < requirement.min_tasks:
                    missing.append(
                        f"Need {requirement.min_tasks} {requirement.task_category} tasks, "
                        f"have {category_tasks}"
                    )
            else:
                # Total task count
                if stats.total_tasks_completed < requirement.min_tasks:
                    missing.append(
                        f"Need {requirement.min_tasks} tasks, "
                        f"have {stats.total_tasks_completed}"
                    )

        # Check minimum earnings
        if requirement.min_earnings_usd is not None:
            if stats.total_earnings_usd < requirement.min_earnings_usd:
                missing.append(
                    f"Need ${requirement.min_earnings_usd:.2f} earned, "
                    f"have ${stats.total_earnings_usd:.2f}"
                )

        # Check minimum rating
        if requirement.min_rating is not None:
            if stats.average_rating < requirement.min_rating:
                missing.append(
                    f"Need {requirement.min_rating:.1f} rating, "
                    f"have {stats.average_rating:.1f}"
                )

        # Check active days
        if requirement.min_active_days is not None:
            if stats.active_days < requirement.min_active_days:
                missing.append(
                    f"Need {requirement.min_active_days} active days, "
                    f"have {stats.active_days}"
                )

        # Special behavioral checks
        if requirement.seal_type == BehaviorSealType.FAST_RESPONDER.value:
            if stats.avg_response_time_minutes > 60:
                missing.append(
                    f"Need avg response < 60 min, "
                    f"have {stats.avg_response_time_minutes:.0f} min"
                )

        if requirement.seal_type == BehaviorSealType.INSTANT_RESPONDER.value:
            if stats.avg_response_time_minutes > 15:
                missing.append(
                    f"Need avg response < 15 min, "
                    f"have {stats.avg_response_time_minutes:.0f} min"
                )

        if requirement.seal_type == BehaviorSealType.NEVER_CANCELLED.value:
            if stats.cancellation_count > 0:
                missing.append(f"Need 0 cancellations, have {stats.cancellation_count}")

        if requirement.seal_type == BehaviorSealType.ALWAYS_ON_TIME.value:
            if stats.on_time_percentage < 100:
                missing.append(
                    f"Need 100% on-time, have {stats.on_time_percentage:.1f}%"
                )

        # Determine eligibility
        is_eligible = len(missing) == 0 and (
            not requirement.requires_test and not requirement.requires_portfolio
        )

        return EligibilityResult(
            is_eligible=is_eligible,
            seal_type=requirement.seal_type,
            reason="Eligible" if is_eligible else "; ".join(missing),
            missing_requirements=missing,
        )

    def check_all_eligibility(
        self, stats: WorkerStats, category: Optional[SealCategory] = None
    ) -> List[EligibilityResult]:
        """
        Check eligibility for all automatic seals.

        Args:
            stats: Worker's current statistics
            category: Optional category filter

        Returns:
            List of EligibilityResult for each seal
        """
        results = []

        for requirement in get_automatic_seals():
            if category and requirement.category != category:
                continue

            result = self.check_eligibility(stats, requirement)
            results.append(result)

        return results

    def get_next_milestone_seals(
        self, stats: WorkerStats
    ) -> List[Tuple[SealRequirement, int]]:
        """
        Get seals the worker is closest to earning.

        Returns list of (requirement, percentage_complete) tuples,
        sorted by proximity to completion.

        Args:
            stats: Worker's current statistics

        Returns:
            List of upcoming seals with completion percentage
        """
        upcoming = []

        for requirement in get_automatic_seals():
            result = self.check_eligibility(stats, requirement)

            if result.is_eligible:
                continue  # Already eligible, skip

            # Calculate progress percentage
            progress = self._calculate_progress(stats, requirement)
            if 0 < progress < 100:
                upcoming.append((requirement, progress))

        # Sort by closest to completion
        upcoming.sort(key=lambda x: x[1], reverse=True)
        return upcoming[:5]  # Top 5

    def _calculate_progress(
        self, stats: WorkerStats, requirement: SealRequirement
    ) -> int:
        """Calculate progress percentage toward a seal."""
        if requirement.min_tasks is not None:
            if requirement.task_category:
                current = stats.tasks_by_category.get(requirement.task_category, 0)
            else:
                current = stats.total_tasks_completed
            return min(99, int(current / requirement.min_tasks * 100))

        if requirement.min_earnings_usd is not None:
            return min(
                99, int(stats.total_earnings_usd / requirement.min_earnings_usd * 100)
            )

        if requirement.min_active_days is not None:
            return min(99, int(stats.active_days / requirement.min_active_days * 100))

        return 0

    # =========================================================================
    # ISSUANCE OPERATIONS
    # =========================================================================

    async def issue_seal(
        self,
        holder_address: str,
        seal_type: str,
        verification_method: VerificationMethod = VerificationMethod.AUTOMATIC,
        verifier_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IssuanceResult:
        """
        Issue a single seal to a worker.

        Args:
            holder_address: Worker's wallet address
            seal_type: Seal type to issue
            verification_method: How it was verified
            verifier_id: Who verified (for non-automatic)
            metadata: Additional metadata

        Returns:
            IssuanceResult with success status
        """
        try:
            # Check if already has seal
            if await self.registry.has_seal(holder_address, seal_type):
                return IssuanceResult(
                    success=False,
                    seal_type=seal_type,
                    error="Worker already has this seal",
                )

            # Get requirement for expiration
            requirement = get_requirement(seal_type)
            expires_at = None
            if requirement and requirement.expires_after_days:
                expires_at = datetime.now(UTC) + timedelta(
                    days=requirement.expires_after_days
                )

            # Prepare metadata
            full_metadata = {
                "verification_method": verification_method.value,
                "issued_at": datetime.now(UTC).isoformat(),
            }
            if verifier_id:
                full_metadata["verifier_id"] = verifier_id
            if metadata:
                full_metadata.update(metadata)

            # Issue on-chain
            tx_hash = await self.registry.issue_seal(
                holder_address=holder_address,
                seal_type=seal_type,
                expires_at=expires_at,
                metadata=full_metadata,
            )

            if tx_hash:
                logger.info(f"Issued seal {seal_type} to {holder_address}")
                return IssuanceResult(
                    success=True,
                    seal_type=seal_type,
                    tx_hash=tx_hash,
                )
            else:
                return IssuanceResult(
                    success=False, seal_type=seal_type, error="Transaction failed"
                )

        except Exception as e:
            logger.error(f"Error issuing seal: {e}")
            return IssuanceResult(success=False, seal_type=seal_type, error=str(e))

    async def check_and_issue_automatic(
        self, stats: WorkerStats, dry_run: bool = False
    ) -> List[IssuanceResult]:
        """
        Check eligibility and issue all automatic seals the worker qualifies for.

        This is the main entry point for automatic seal issuance.
        Should be called after task completion, rating updates, etc.

        Args:
            stats: Worker's current statistics
            dry_run: If True, only check eligibility without issuing

        Returns:
            List of IssuanceResult for each seal checked
        """
        results = []

        # Get all eligibility results
        eligibility_results = self.check_all_eligibility(stats)

        for eligibility in eligibility_results:
            if not eligibility.is_eligible:
                continue

            # Check if already has seal
            if await self.registry.has_seal(
                stats.wallet_address, eligibility.seal_type
            ):
                continue

            if dry_run:
                results.append(
                    IssuanceResult(
                        success=True,
                        seal_type=eligibility.seal_type,
                        tx_hash=None,
                        error="DRY_RUN",
                    )
                )
            else:
                result = await self.issue_seal(
                    holder_address=stats.wallet_address,
                    seal_type=eligibility.seal_type,
                    verification_method=VerificationMethod.AUTOMATIC,
                )
                results.append(result)

        return results

    async def batch_issue_automatic(
        self,
        workers: List[WorkerStats],
    ) -> Dict[str, List[IssuanceResult]]:
        """
        Process automatic seal issuance for multiple workers.

        More efficient for batch processing (e.g., nightly jobs).

        Args:
            workers: List of worker statistics

        Returns:
            Dict mapping wallet address to list of issuance results
        """
        results = {}

        # Collect all issuances needed
        issuances = []

        for stats in workers:
            worker_results = []
            eligibility_results = self.check_all_eligibility(stats)

            for eligibility in eligibility_results:
                if not eligibility.is_eligible:
                    continue

                if await self.registry.has_seal(
                    stats.wallet_address, eligibility.seal_type
                ):
                    continue

                requirement = get_requirement(eligibility.seal_type)
                expires_at = None
                if requirement and requirement.expires_after_days:
                    expires_at = datetime.now(UTC) + timedelta(
                        days=requirement.expires_after_days
                    )

                issuances.append(
                    {
                        "holder": stats.wallet_address,
                        "seal_type": eligibility.seal_type,
                        "expires_at": expires_at,
                    }
                )

            results[stats.wallet_address] = worker_results

        # Batch issue if registry supports it
        if hasattr(self.registry, "batch_issue_seals") and issuances:
            try:
                tx_hash = await self.registry.batch_issue_seals(issuances)

                # Mark all as successful
                for issuance in issuances:
                    wallet = issuance["holder"]
                    if wallet not in results:
                        results[wallet] = []
                    results[wallet].append(
                        IssuanceResult(
                            success=True,
                            seal_type=issuance["seal_type"],
                            tx_hash=tx_hash,
                        )
                    )

            except Exception as e:
                logger.error(f"Batch issuance failed: {e}")
                # Fall back to individual issuance
                for issuance in issuances:
                    result = await self.issue_seal(
                        holder_address=issuance["holder"],
                        seal_type=issuance["seal_type"],
                    )
                    if issuance["holder"] not in results:
                        results[issuance["holder"]] = []
                    results[issuance["holder"]].append(result)

        return results

    # =========================================================================
    # SKILL SEAL WORKFLOWS
    # =========================================================================

    async def initiate_skill_verification(
        self,
        holder_address: str,
        seal_type: str,
    ) -> Dict[str, Any]:
        """
        Start the verification process for a skill seal.

        Returns instructions for the worker on what they need to do.

        Args:
            holder_address: Worker's wallet address
            seal_type: Skill seal type to verify

        Returns:
            Dict with verification instructions
        """
        requirement = get_requirement(seal_type)

        if not requirement:
            return {"error": f"Unknown seal type: {seal_type}"}

        if requirement.category != SealCategory.SKILL:
            return {"error": "This seal type doesn't require skill verification"}

        # Check if already has seal
        if await self.registry.has_seal(holder_address, seal_type):
            return {"error": "Worker already has this seal"}

        instructions = {
            "seal_type": seal_type,
            "display_name": requirement.display_name,
            "display_name_es": requirement.display_name_es,
            "verification_method": requirement.verification_method.value,
            "steps": [],
        }

        if requirement.requires_test:
            instructions["steps"].append(
                {
                    "type": "test_task",
                    "description": "Complete a verification task",
                    "description_es": "Completa una tarea de verificación",
                }
            )

        if requirement.requires_portfolio:
            instructions["steps"].append(
                {
                    "type": "portfolio",
                    "description": "Submit portfolio for review",
                    "description_es": "Envía tu portafolio para revisión",
                }
            )

        return instructions

    async def approve_skill_verification(
        self,
        holder_address: str,
        seal_type: str,
        verifier_id: str,
        verification_data: Dict[str, Any],
    ) -> IssuanceResult:
        """
        Approve a skill verification and issue the seal.

        Called by a reviewer/admin after verifying the worker's
        test task or portfolio.

        Args:
            holder_address: Worker's wallet address
            seal_type: Skill seal type
            verifier_id: ID of the reviewer
            verification_data: Data from verification (scores, notes, etc.)

        Returns:
            IssuanceResult
        """
        return await self.issue_seal(
            holder_address=holder_address,
            seal_type=seal_type,
            verification_method=VerificationMethod.PEER_REVIEW,
            verifier_id=verifier_id,
            metadata={
                "verification_data": verification_data,
                "approved_at": datetime.now(UTC).isoformat(),
            },
        )

    # =========================================================================
    # RENEWAL
    # =========================================================================

    async def check_and_renew_expiring(
        self,
        holder_address: str,
        stats: WorkerStats,
    ) -> List[IssuanceResult]:
        """
        Check for expiring seals and renew if still eligible.

        Behavior seals expire and need renewal if the worker
        maintains the required behavior.

        Args:
            holder_address: Worker's wallet address
            stats: Current worker statistics

        Returns:
            List of renewal results
        """
        results = []
        seals = await self.registry.get_seals(holder_address)

        for seal in seals:
            if not seal.expires_at:
                continue  # Permanent seal

            # Check if expiring within 7 days
            days_until_expiry = (seal.expires_at - datetime.now(UTC)).days
            if days_until_expiry > 7:
                continue

            requirement = get_requirement(seal.seal_type)
            if not requirement or not requirement.renewable:
                continue

            # Check if still eligible
            eligibility = self.check_eligibility(stats, requirement)

            if eligibility.is_eligible:
                # Renew
                new_expires_at = datetime.now(UTC) + timedelta(
                    days=requirement.expires_after_days
                )

                tx_hash = await self.registry.renew_seal(
                    holder_address=holder_address,
                    seal_type=seal.seal_type,
                    new_expires_at=new_expires_at,
                )

                results.append(
                    IssuanceResult(
                        success=tx_hash is not None,
                        seal_type=seal.seal_type,
                        tx_hash=tx_hash,
                        error=None if tx_hash else "Renewal failed",
                    )
                )
            else:
                logger.info(
                    f"Seal {seal.seal_type} not renewed - no longer eligible: "
                    f"{eligibility.reason}"
                )

        return results
