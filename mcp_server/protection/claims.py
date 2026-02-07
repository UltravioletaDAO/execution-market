"""
Claim Management for Worker Protection Fund

Handles submission, review, approval, and rejection of worker protection claims.

Claim Types:
- UNPAID: Work completed but payment not received
- DISPUTE_LOSS: Worker lost dispute but deserves partial compensation
- PLATFORM_ERROR: Technical failure caused loss

Flow:
1. submit_claim() - Worker submits claim with evidence
2. review_claim() - Auto-review with rules engine
3. approve_claim() / reject_claim() - Manual decision if needed
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional, List, Any

from .fund import (
    get_fund,
    FundClaim,
    ClaimStatus,
    ClaimType as BaseClaimType,
    ClaimNotFoundError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Claim Types (Extended)
# =============================================================================


class ClaimType(str, Enum):
    """
    Types of protection fund claims.

    These map to different review rules and payout limits.
    """

    UNPAID = "unpaid"  # Work completed but payment not received
    DISPUTE_LOSS = "dispute_loss"  # Worker lost dispute but deserves compensation
    PLATFORM_ERROR = "platform_error"  # Technical failure caused loss

    # Legacy types (mapped from fund.py)
    AGENT_DISAPPEARED = "agent_disappeared"
    PAYMENT_FAILURE = "payment_failure"
    UNJUST_REJECTION = "unjust_rejection"
    EMERGENCY_HARDSHIP = "emergency_hardship"


# Mapping from new types to base types for backward compatibility
_TYPE_MAPPING = {
    ClaimType.UNPAID: BaseClaimType.PAYMENT_FAILURE,
    ClaimType.DISPUTE_LOSS: BaseClaimType.UNJUST_REJECTION,
    ClaimType.PLATFORM_ERROR: BaseClaimType.PAYMENT_FAILURE,
    ClaimType.AGENT_DISAPPEARED: BaseClaimType.AGENT_DISAPPEARED,
    ClaimType.PAYMENT_FAILURE: BaseClaimType.PAYMENT_FAILURE,
    ClaimType.UNJUST_REJECTION: BaseClaimType.UNJUST_REJECTION,
    ClaimType.EMERGENCY_HARDSHIP: BaseClaimType.EMERGENCY_HARDSHIP,
}


# =============================================================================
# Review Rules
# =============================================================================


@dataclass
class ReviewRule:
    """
    Rule for auto-reviewing claims.

    Attributes:
        claim_type: Type of claim this rule applies to
        auto_approve_threshold: Max amount to auto-approve
        required_evidence: List of required evidence fields
        max_payout_percent: Max percentage of original bounty
        priority: Higher priority rules checked first
    """

    claim_type: ClaimType
    auto_approve_threshold: Decimal = Decimal("10.00")
    required_evidence: List[str] = field(default_factory=list)
    max_payout_percent: Decimal = Decimal("0.80")  # 80% max
    priority: int = 0


# Default review rules by claim type
DEFAULT_REVIEW_RULES: Dict[ClaimType, ReviewRule] = {
    ClaimType.UNPAID: ReviewRule(
        claim_type=ClaimType.UNPAID,
        auto_approve_threshold=Decimal("25.00"),
        required_evidence=["task_id", "submission_id"],
        max_payout_percent=Decimal("1.0"),  # Full amount for unpaid work
        priority=10,
    ),
    ClaimType.DISPUTE_LOSS: ReviewRule(
        claim_type=ClaimType.DISPUTE_LOSS,
        auto_approve_threshold=Decimal("10.00"),
        required_evidence=["task_id", "dispute_id", "dispute_reason"],
        max_payout_percent=Decimal("0.50"),  # 50% for dispute losses
        priority=5,
    ),
    ClaimType.PLATFORM_ERROR: ReviewRule(
        claim_type=ClaimType.PLATFORM_ERROR,
        auto_approve_threshold=Decimal("50.00"),  # Higher threshold for platform errors
        required_evidence=["error_id", "error_description"],
        max_payout_percent=Decimal("1.0"),  # Full amount for platform errors
        priority=15,
    ),
    ClaimType.AGENT_DISAPPEARED: ReviewRule(
        claim_type=ClaimType.AGENT_DISAPPEARED,
        auto_approve_threshold=Decimal("20.00"),
        required_evidence=["task_id", "last_contact"],
        max_payout_percent=Decimal("0.80"),
        priority=8,
    ),
}


@dataclass
class ReviewResult:
    """
    Result of claim review process.

    Attributes:
        claim_id: ID of the reviewed claim
        decision: "approve", "reject", or "manual_review"
        amount: Recommended payout amount (if approved)
        reason: Explanation for the decision
        missing_evidence: List of missing required evidence
        rule_applied: Name of the rule that was applied
    """

    claim_id: str
    decision: str  # "approve", "reject", "manual_review"
    amount: Decimal
    reason: str
    missing_evidence: List[str] = field(default_factory=list)
    rule_applied: Optional[str] = None


# =============================================================================
# Claim Submission
# =============================================================================


async def submit_claim(
    executor_id: str,
    claim_type: ClaimType,
    amount: Decimal,
    evidence: Dict[str, Any],
    reason: Optional[str] = None,
    task_id: Optional[str] = None,
) -> FundClaim:
    """
    Submit a claim to the protection fund.

    Args:
        executor_id: Worker's executor ID
        claim_type: Type of claim (UNPAID, DISPUTE_LOSS, PLATFORM_ERROR)
        amount: Amount requested
        evidence: Supporting evidence dictionary
        reason: Explanation for the claim
        task_id: Related task ID (if applicable)

    Returns:
        FundClaim with PENDING status

    Raises:
        ClaimLimitExceededError: If worker has exceeded limits
        FundError: If amount is invalid

    Example:
        >>> claim = await submit_claim(
        ...     executor_id="exec_123",
        ...     claim_type=ClaimType.UNPAID,
        ...     amount=Decimal("25.00"),
        ...     evidence={
        ...         "task_id": "task_456",
        ...         "submission_id": "sub_789",
        ...         "screenshots": ["url1", "url2"]
        ...     },
        ...     reason="Agent disappeared after I submitted work"
        ... )
    """
    fund = get_fund()

    # Map to base claim type
    base_type = _TYPE_MAPPING.get(claim_type, BaseClaimType.PAYMENT_FAILURE)

    # Build reason from type if not provided
    if not reason:
        reason = f"Claim type: {claim_type.value}"

    # Add claim type to evidence for tracking
    evidence["claim_type_extended"] = claim_type.value

    logger.info(
        "Submitting claim: executor=%s, type=%s, amount=$%.2f",
        executor_id[:8] + "...",
        claim_type.value,
        float(amount),
    )

    claim = await fund.submit_claim(
        worker_id=executor_id,
        claim_type=base_type,
        amount=amount,
        reason=reason,
        evidence=evidence,
        task_id=task_id,
    )

    logger.info(
        "Claim submitted: id=%s, status=%s",
        claim.id,
        claim.status.value,
    )

    return claim


# =============================================================================
# Claim Review
# =============================================================================


def review_claim(claim_id: str) -> ReviewResult:
    """
    Auto-review a claim using rules engine.

    This function applies automatic review rules to determine if a claim
    can be auto-approved, should be rejected, or needs manual review.

    Args:
        claim_id: ID of the claim to review

    Returns:
        ReviewResult with decision and reasoning

    Raises:
        ClaimNotFoundError: If claim doesn't exist

    Example:
        >>> result = review_claim("claim_abc123")
        >>> if result.decision == "approve":
        ...     await approve_claim(claim_id, "auto", result.amount)
        >>> elif result.decision == "reject":
        ...     await reject_claim(claim_id, result.reason)
        >>> else:
        ...     # Needs manual review
        ...     notify_admin(claim_id, result.reason)
    """
    fund = get_fund()
    claim = fund.get_claim(claim_id)

    if not claim:
        raise ClaimNotFoundError(f"Claim not found: {claim_id}")

    # Get extended claim type from evidence
    extended_type_str = claim.evidence.get("claim_type_extended")
    try:
        claim_type = (
            ClaimType(extended_type_str) if extended_type_str else ClaimType.UNPAID
        )
    except ValueError:
        # Fall back to mapping from base type
        claim_type = ClaimType.UNPAID

    # Get applicable rule
    rule = DEFAULT_REVIEW_RULES.get(claim_type)
    if not rule:
        # Default rule for unknown types
        rule = ReviewRule(
            claim_type=claim_type,
            auto_approve_threshold=Decimal("10.00"),
            required_evidence=[],
            max_payout_percent=Decimal("0.50"),
        )

    # Check for missing evidence
    missing_evidence = []
    for required in rule.required_evidence:
        if required not in claim.evidence or not claim.evidence[required]:
            missing_evidence.append(required)

    # Calculate max allowed amount
    original_bounty = claim.evidence.get("original_bounty")
    if original_bounty:
        max_amount = Decimal(str(original_bounty)) * rule.max_payout_percent
    else:
        max_amount = claim.amount_requested

    # Cap at per-claim limit
    fund_config = fund.config
    max_amount = min(max_amount, fund_config.max_claim_amount)

    # Determine decision
    if missing_evidence:
        return ReviewResult(
            claim_id=claim_id,
            decision="manual_review",
            amount=Decimal("0"),
            reason=f"Missing required evidence: {', '.join(missing_evidence)}",
            missing_evidence=missing_evidence,
            rule_applied=f"rule_{claim_type.value}",
        )

    # Check if amount qualifies for auto-approval
    if claim.amount_requested <= rule.auto_approve_threshold:
        approved_amount = min(claim.amount_requested, max_amount)
        return ReviewResult(
            claim_id=claim_id,
            decision="approve",
            amount=approved_amount,
            reason=f"Auto-approved: amount ${float(approved_amount):.2f} within threshold",
            rule_applied=f"rule_{claim_type.value}",
        )

    # Amount too high for auto-approval
    return ReviewResult(
        claim_id=claim_id,
        decision="manual_review",
        amount=min(claim.amount_requested, max_amount),
        reason=f"Amount ${float(claim.amount_requested):.2f} exceeds auto-approve threshold "
        f"of ${float(rule.auto_approve_threshold):.2f}",
        rule_applied=f"rule_{claim_type.value}",
    )


# =============================================================================
# Claim Approval/Rejection
# =============================================================================


async def approve_claim(
    claim_id: str,
    reviewer_id: str = "system",
    amount: Optional[Decimal] = None,
    notes: Optional[str] = None,
) -> FundClaim:
    """
    Approve a claim for payout.

    Args:
        claim_id: ID of the claim to approve
        reviewer_id: ID of the reviewer (default "system" for auto-approval)
        amount: Amount to approve (defaults to requested amount)
        notes: Reviewer notes

    Returns:
        Updated FundClaim with PAID status

    Raises:
        ClaimNotFoundError: If claim doesn't exist
        InvalidClaimStateError: If claim is not pending
        InsufficientFundsError: If fund balance is too low

    Example:
        >>> claim = await approve_claim(
        ...     claim_id="claim_abc123",
        ...     reviewer_id="admin_456",
        ...     amount=Decimal("20.00"),
        ...     notes="Verified work was completed"
        ... )
    """
    fund = get_fund()
    claim = fund.get_claim(claim_id)

    if not claim:
        raise ClaimNotFoundError(f"Claim not found: {claim_id}")

    # Default to requested amount
    if amount is None:
        amount = claim.amount_requested

    logger.info(
        "Approving claim: id=%s, amount=$%.2f, reviewer=%s",
        claim_id,
        float(amount),
        reviewer_id,
    )

    return await fund.approve_claim(
        claim_id=claim_id,
        reviewer_id=reviewer_id,
        amount=amount,
        notes=notes,
    )


async def reject_claim(
    claim_id: str,
    reason: str,
    reviewer_id: str = "system",
) -> FundClaim:
    """
    Reject a claim.

    Args:
        claim_id: ID of the claim to reject
        reason: Reason for rejection
        reviewer_id: ID of the reviewer

    Returns:
        Updated FundClaim with REJECTED status

    Raises:
        ClaimNotFoundError: If claim doesn't exist
        InvalidClaimStateError: If claim is not pending

    Example:
        >>> claim = await reject_claim(
        ...     claim_id="claim_abc123",
        ...     reason="Insufficient evidence of work completion",
        ...     reviewer_id="admin_456"
        ... )
    """
    fund = get_fund()
    claim = fund.get_claim(claim_id)

    if not claim:
        raise ClaimNotFoundError(f"Claim not found: {claim_id}")

    logger.info(
        "Rejecting claim: id=%s, reason=%s, reviewer=%s",
        claim_id,
        reason[:50] + "..." if len(reason) > 50 else reason,
        reviewer_id,
    )

    return await fund.reject_claim(
        claim_id=claim_id,
        reviewer_id=reviewer_id,
        reason=reason,
    )


# =============================================================================
# Batch Operations
# =============================================================================


async def auto_review_pending_claims() -> List[ReviewResult]:
    """
    Auto-review all pending claims.

    Returns:
        List of ReviewResult for each pending claim
    """
    fund = get_fund()
    pending = fund.get_pending_claims()

    results = []
    for claim in pending:
        try:
            result = review_claim(claim.id)
            results.append(result)

            # Auto-process approved claims
            if result.decision == "approve":
                await approve_claim(
                    claim_id=claim.id,
                    reviewer_id="auto_review",
                    amount=result.amount,
                    notes=result.reason,
                )
        except Exception as e:
            logger.error("Error reviewing claim %s: %s", claim.id, str(e))
            results.append(
                ReviewResult(
                    claim_id=claim.id,
                    decision="error",
                    amount=Decimal("0"),
                    reason=str(e),
                )
            )

    return results


def get_claims_by_status(status: ClaimStatus) -> List[FundClaim]:
    """
    Get all claims with a specific status.

    Args:
        status: Status to filter by

    Returns:
        List of matching claims
    """
    fund = get_fund()
    return [claim for claim in fund._claims.values() if claim.status == status]


def get_claims_for_worker(worker_id: str) -> List[FundClaim]:
    """
    Get all claims for a specific worker.

    Args:
        worker_id: Worker's ID

    Returns:
        List of claims for the worker
    """
    fund = get_fund()
    return fund.get_worker_claims(worker_id)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "ClaimType",
    "ReviewRule",
    "ReviewResult",
    "submit_claim",
    "review_claim",
    "approve_claim",
    "reject_claim",
    "auto_review_pending_claims",
    "get_claims_by_status",
    "get_claims_for_worker",
]
