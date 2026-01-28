"""
Eligibility Rules for Worker Protection Fund

Determines if a worker is eligible to submit a claim based on:
- Verified identity
- Minimum completed tasks (5)
- No fraud flags
- Cooldown period (1 claim per 30 days)
- Maximum claim amount (80% of original bounty)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional, List, Any, Tuple

from .fund import get_fund, FundConfig, WorkerClaimHistory
from .claims import ClaimType

logger = logging.getLogger(__name__)


# =============================================================================
# Eligibility Requirements
# =============================================================================


@dataclass
class EligibilityRequirements:
    """
    Requirements for fund claim eligibility.

    Attributes:
        min_completed_tasks: Minimum tasks completed before eligible (5)
        require_verified_identity: Whether identity verification is required
        cooldown_days: Days between claims (30)
        max_claim_percent: Maximum claim as % of original bounty (80%)
        fraud_flag_blocks: Whether fraud flags block eligibility
    """
    min_completed_tasks: int = 5
    require_verified_identity: bool = True
    cooldown_days: int = 30
    max_claim_percent: Decimal = Decimal("0.80")  # 80%
    fraud_flag_blocks: bool = True


# Default requirements
DEFAULT_REQUIREMENTS = EligibilityRequirements()


# =============================================================================
# Eligibility Status
# =============================================================================


class EligibilityStatus(str, Enum):
    """Status of eligibility check."""
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    PENDING_VERIFICATION = "pending_verification"
    COOLDOWN = "cooldown"
    FLAGGED = "flagged"


@dataclass
class EligibilityResult:
    """
    Result of an eligibility check.

    Attributes:
        executor_id: Worker's ID
        status: Eligibility status
        eligible: Boolean for quick checks
        reason: Human-readable explanation
        max_claimable: Maximum amount worker can claim
        cooldown_ends: When cooldown period ends (if applicable)
        missing_requirements: List of unmet requirements
    """
    executor_id: str
    status: EligibilityStatus
    eligible: bool
    reason: str
    max_claimable: Decimal = Decimal("0")
    cooldown_ends: Optional[datetime] = None
    missing_requirements: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "executor_id": self.executor_id,
            "status": self.status.value,
            "eligible": self.eligible,
            "reason": self.reason,
            "max_claimable": float(self.max_claimable),
            "cooldown_ends": self.cooldown_ends.isoformat() if self.cooldown_ends else None,
            "missing_requirements": self.missing_requirements,
        }


# =============================================================================
# Worker Profile (Mock for now - would integrate with workers module)
# =============================================================================


@dataclass
class WorkerProfile:
    """
    Worker profile for eligibility checking.

    In production, this would come from the workers module.
    """
    executor_id: str
    completed_tasks: int = 0
    identity_verified: bool = False
    fraud_flags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# In-memory cache (would be replaced with DB lookup)
_worker_profiles: Dict[str, WorkerProfile] = {}


def get_worker_profile(executor_id: str) -> Optional[WorkerProfile]:
    """
    Get worker profile for eligibility checking.

    Args:
        executor_id: Worker's executor ID

    Returns:
        WorkerProfile or None if not found
    """
    return _worker_profiles.get(executor_id)


def register_worker_profile(
    executor_id: str,
    completed_tasks: int = 0,
    identity_verified: bool = False,
    fraud_flags: Optional[List[str]] = None,
) -> WorkerProfile:
    """
    Register a worker profile (for testing and initialization).

    Args:
        executor_id: Worker's executor ID
        completed_tasks: Number of completed tasks
        identity_verified: Whether identity is verified
        fraud_flags: List of fraud flags

    Returns:
        Created WorkerProfile
    """
    profile = WorkerProfile(
        executor_id=executor_id,
        completed_tasks=completed_tasks,
        identity_verified=identity_verified,
        fraud_flags=fraud_flags or [],
    )
    _worker_profiles[executor_id] = profile
    return profile


def update_worker_tasks(executor_id: str, completed_tasks: int) -> None:
    """Update a worker's completed task count."""
    profile = _worker_profiles.get(executor_id)
    if profile:
        profile.completed_tasks = completed_tasks
    else:
        register_worker_profile(executor_id, completed_tasks=completed_tasks)


def verify_worker_identity(executor_id: str) -> None:
    """Mark a worker's identity as verified."""
    profile = _worker_profiles.get(executor_id)
    if profile:
        profile.identity_verified = True
    else:
        register_worker_profile(executor_id, identity_verified=True)


def add_fraud_flag(executor_id: str, flag: str) -> None:
    """Add a fraud flag to a worker."""
    profile = _worker_profiles.get(executor_id)
    if profile:
        profile.fraud_flags.append(flag)
    else:
        register_worker_profile(executor_id, fraud_flags=[flag])


def clear_fraud_flags(executor_id: str) -> None:
    """Clear all fraud flags for a worker."""
    profile = _worker_profiles.get(executor_id)
    if profile:
        profile.fraud_flags = []


# =============================================================================
# Main Eligibility Check
# =============================================================================


def check_eligibility(
    executor_id: str,
    claim_type: ClaimType,
    amount: Optional[Decimal] = None,
    original_bounty: Optional[Decimal] = None,
    requirements: Optional[EligibilityRequirements] = None,
) -> EligibilityResult:
    """
    Check if a worker is eligible to submit a claim.

    Requirements:
    1. Verified identity (if required)
    2. Minimum 5 completed tasks
    3. No fraud flags
    4. Not in cooldown period (30 days since last claim)
    5. Claim amount <= 80% of original bounty

    Args:
        executor_id: Worker's executor ID
        claim_type: Type of claim being submitted
        amount: Amount being claimed (optional)
        original_bounty: Original task bounty (for percentage calculation)
        requirements: Custom requirements (defaults to DEFAULT_REQUIREMENTS)

    Returns:
        EligibilityResult with status and details

    Example:
        >>> result = check_eligibility(
        ...     executor_id="exec_123",
        ...     claim_type=ClaimType.UNPAID,
        ...     amount=Decimal("25.00"),
        ...     original_bounty=Decimal("30.00")
        ... )
        >>> if result.eligible:
        ...     submit_claim(...)
        >>> else:
        ...     print(f"Not eligible: {result.reason}")
    """
    reqs = requirements or DEFAULT_REQUIREMENTS
    missing = []
    fund = get_fund()

    # Get worker profile
    profile = get_worker_profile(executor_id)
    if not profile:
        # Create a default profile for unknown workers
        profile = WorkerProfile(executor_id=executor_id)

    # Get claim history
    history = fund.get_worker_history(executor_id)

    # Check 1: Verified identity
    if reqs.require_verified_identity and not profile.identity_verified:
        missing.append("verified_identity")
        logger.debug("Worker %s missing identity verification", executor_id[:8])

    # Check 2: Minimum completed tasks
    if profile.completed_tasks < reqs.min_completed_tasks:
        missing.append(f"min_tasks_{reqs.min_completed_tasks}")
        logger.debug(
            "Worker %s has %d tasks, need %d",
            executor_id[:8],
            profile.completed_tasks,
            reqs.min_completed_tasks,
        )

    # Check 3: Fraud flags
    if reqs.fraud_flag_blocks and profile.fraud_flags:
        return EligibilityResult(
            executor_id=executor_id,
            status=EligibilityStatus.FLAGGED,
            eligible=False,
            reason=f"Account flagged: {', '.join(profile.fraud_flags)}",
            missing_requirements=["no_fraud_flags"],
        )

    # Check 4: Cooldown period
    if history and history.last_claim_at:
        cooldown_end = history.last_claim_at + timedelta(days=reqs.cooldown_days)
        now = datetime.now(timezone.utc)
        if now < cooldown_end:
            days_remaining = (cooldown_end - now).days + 1
            return EligibilityResult(
                executor_id=executor_id,
                status=EligibilityStatus.COOLDOWN,
                eligible=False,
                reason=f"Cooldown period active. {days_remaining} days remaining.",
                cooldown_ends=cooldown_end,
                missing_requirements=["cooldown_complete"],
            )

    # Calculate max claimable amount
    fund_config = fund.config
    max_claimable = fund_config.max_claim_amount

    if original_bounty and original_bounty > 0:
        # Apply 80% limit
        bounty_limit = original_bounty * reqs.max_claim_percent
        max_claimable = min(max_claimable, bounty_limit)

    # Check 5: Amount validation
    if amount and amount > max_claimable:
        return EligibilityResult(
            executor_id=executor_id,
            status=EligibilityStatus.INELIGIBLE,
            eligible=False,
            reason=f"Requested amount ${float(amount):.2f} exceeds maximum "
                   f"${float(max_claimable):.2f} (80% of bounty or per-claim limit)",
            max_claimable=max_claimable,
            missing_requirements=["amount_within_limit"],
        )

    # Check monthly limit
    if history:
        monthly_remaining = fund_config.max_monthly_per_worker - history.paid_this_month
        max_claimable = min(max_claimable, monthly_remaining)

        if monthly_remaining <= 0:
            return EligibilityResult(
                executor_id=executor_id,
                status=EligibilityStatus.INELIGIBLE,
                eligible=False,
                reason=f"Monthly limit exceeded. Already claimed "
                       f"${float(history.paid_this_month):.2f} this month.",
                max_claimable=Decimal("0"),
                missing_requirements=["monthly_limit_available"],
            )

    # If missing requirements, return pending/ineligible
    if missing:
        status = EligibilityStatus.PENDING_VERIFICATION if "verified_identity" in missing else EligibilityStatus.INELIGIBLE
        return EligibilityResult(
            executor_id=executor_id,
            status=status,
            eligible=False,
            reason=f"Missing requirements: {', '.join(missing)}",
            max_claimable=Decimal("0"),
            missing_requirements=missing,
        )

    # All checks passed
    return EligibilityResult(
        executor_id=executor_id,
        status=EligibilityStatus.ELIGIBLE,
        eligible=True,
        reason="Eligible to submit claim",
        max_claimable=max_claimable,
    )


# =============================================================================
# Convenience Functions
# =============================================================================


def is_eligible(executor_id: str, claim_type: ClaimType) -> bool:
    """
    Quick check if worker is eligible for any claim.

    Args:
        executor_id: Worker's executor ID
        claim_type: Type of claim

    Returns:
        True if eligible, False otherwise
    """
    result = check_eligibility(executor_id, claim_type)
    return result.eligible


def get_max_claim_amount(
    executor_id: str,
    original_bounty: Optional[Decimal] = None,
) -> Decimal:
    """
    Get the maximum amount a worker can claim.

    Args:
        executor_id: Worker's executor ID
        original_bounty: Original task bounty (for 80% calculation)

    Returns:
        Maximum claimable amount
    """
    result = check_eligibility(
        executor_id,
        ClaimType.UNPAID,  # Type doesn't affect max amount calculation
        original_bounty=original_bounty,
    )
    return result.max_claimable


def get_cooldown_status(executor_id: str) -> Tuple[bool, Optional[datetime]]:
    """
    Check if worker is in cooldown period.

    Args:
        executor_id: Worker's executor ID

    Returns:
        Tuple of (is_in_cooldown, cooldown_end_time)
    """
    fund = get_fund()
    history = fund.get_worker_history(executor_id)

    if not history or not history.last_claim_at:
        return False, None

    reqs = DEFAULT_REQUIREMENTS
    cooldown_end = history.last_claim_at + timedelta(days=reqs.cooldown_days)
    now = datetime.now(timezone.utc)

    if now < cooldown_end:
        return True, cooldown_end

    return False, None


def check_fraud_status(executor_id: str) -> Tuple[bool, List[str]]:
    """
    Check if worker has fraud flags.

    Args:
        executor_id: Worker's executor ID

    Returns:
        Tuple of (has_flags, list_of_flags)
    """
    profile = get_worker_profile(executor_id)
    if not profile:
        return False, []

    return bool(profile.fraud_flags), profile.fraud_flags.copy()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "EligibilityRequirements",
    "EligibilityStatus",
    "EligibilityResult",
    "WorkerProfile",
    "check_eligibility",
    "is_eligible",
    "get_max_claim_amount",
    "get_cooldown_status",
    "check_fraud_status",
    "get_worker_profile",
    "register_worker_profile",
    "update_worker_tasks",
    "verify_worker_identity",
    "add_fraud_flag",
    "clear_fraud_flags",
    "DEFAULT_REQUIREMENTS",
]
