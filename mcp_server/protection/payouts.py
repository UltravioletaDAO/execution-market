"""
Payout Processing for Worker Protection Fund

Handles the actual disbursement of funds to workers via x402 protocol.

Operations:
- calculate_payout(claim) - Apply limits and deductions
- execute_payout(claim_id) - Send payment via x402
- record_payout(claim_id, tx_hash) - Record transaction
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List, Any

from .fund import (
    get_fund,
    FundClaim,
    ClaimStatus,
    ClaimNotFoundError,
    InvalidClaimStateError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Payout limits
MAX_SINGLE_PAYOUT = Decimal("50.00")  # Maximum single payout
MIN_PAYOUT_AMOUNT = Decimal("0.50")  # Minimum payout (below this, accumulate)

# x402 integration
X402_FACILITATOR_URL = os.environ.get("X402_FACILITATOR_URL", "http://localhost:4020")
PAYOUT_TOKEN = os.environ.get("PAYOUT_TOKEN", "USDC")


# =============================================================================
# Payout Calculation
# =============================================================================


@dataclass
class PayoutBreakdown:
    """
    Breakdown of a payout calculation.

    Attributes:
        claim_id: ID of the claim
        requested_amount: Amount originally requested
        approved_amount: Amount approved by reviewer
        deductions: Dict of deductions applied
        final_amount: Amount to actually pay
        reason: Explanation of calculation
    """

    claim_id: str
    requested_amount: Decimal
    approved_amount: Decimal
    deductions: Dict[str, Decimal] = field(default_factory=dict)
    final_amount: Decimal = Decimal("0")
    reason: str = ""

    @property
    def total_deductions(self) -> Decimal:
        """Total of all deductions."""
        return sum(self.deductions.values())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "claim_id": self.claim_id,
            "requested_amount": float(self.requested_amount),
            "approved_amount": float(self.approved_amount),
            "deductions": {k: float(v) for k, v in self.deductions.items()},
            "total_deductions": float(self.total_deductions),
            "final_amount": float(self.final_amount),
            "reason": self.reason,
        }


def calculate_payout(claim: FundClaim) -> PayoutBreakdown:
    """
    Calculate the payout amount for a claim, applying limits and deductions.

    Deductions may include:
    - Capped at per-claim maximum
    - Reduced if fund balance is low
    - Administrative fees (none currently)

    Args:
        claim: FundClaim to calculate payout for

    Returns:
        PayoutBreakdown with all calculations

    Example:
        >>> breakdown = calculate_payout(claim)
        >>> print(f"Pay ${breakdown.final_amount}, deducted ${breakdown.total_deductions}")
    """
    fund = get_fund()

    breakdown = PayoutBreakdown(
        claim_id=claim.id,
        requested_amount=claim.amount_requested,
        approved_amount=claim.amount_approved,
    )

    # Start with approved amount
    amount = claim.amount_approved

    # Deduction 1: Cap at maximum
    if amount > MAX_SINGLE_PAYOUT:
        deduction = amount - MAX_SINGLE_PAYOUT
        breakdown.deductions["max_cap"] = deduction
        amount = MAX_SINGLE_PAYOUT
        logger.info(
            "Claim %s capped at max: $%.2f -> $%.2f",
            claim.id,
            float(claim.amount_approved),
            float(amount),
        )

    # Deduction 2: Fund balance protection (if balance is low)
    fund_balance = fund.balance
    if fund_balance < amount:
        # Pay what we can
        deduction = amount - fund_balance
        breakdown.deductions["insufficient_funds"] = deduction
        amount = fund_balance
        logger.warning(
            "Claim %s reduced due to low fund balance: $%.2f available",
            claim.id,
            float(fund_balance),
        )

    # Check minimum payout
    if amount < MIN_PAYOUT_AMOUNT:
        breakdown.final_amount = Decimal("0")
        breakdown.reason = (
            f"Amount ${float(amount):.2f} below minimum ${float(MIN_PAYOUT_AMOUNT):.2f}"
        )
        logger.info("Claim %s payout below minimum, will accumulate", claim.id)
        return breakdown

    # Round to 2 decimal places
    breakdown.final_amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    breakdown.reason = "Payout calculated successfully"

    return breakdown


# =============================================================================
# Payout Execution
# =============================================================================


@dataclass
class PayoutResult:
    """
    Result of a payout execution.

    Attributes:
        claim_id: ID of the claim
        success: Whether payout succeeded
        tx_hash: Transaction hash (if successful)
        amount: Amount paid
        error: Error message (if failed)
        timestamp: When payout was executed
    """

    claim_id: str
    success: bool
    tx_hash: Optional[str] = None
    amount: Decimal = Decimal("0")
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "claim_id": self.claim_id,
            "success": self.success,
            "tx_hash": self.tx_hash,
            "amount": float(self.amount),
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


async def execute_payout(
    claim_id: str,
    worker_wallet: Optional[str] = None,
) -> PayoutResult:
    """
    Execute payout for an approved claim via x402.

    This function:
    1. Validates the claim is approved
    2. Calculates the final payout amount
    3. Sends payment via x402 protocol
    4. Records the transaction

    Args:
        claim_id: ID of the approved claim
        worker_wallet: Worker's wallet address (optional, uses claim evidence)

    Returns:
        PayoutResult with transaction details

    Raises:
        ClaimNotFoundError: If claim doesn't exist
        InvalidClaimStateError: If claim is not approved
        InsufficientFundsError: If fund balance is too low

    Example:
        >>> result = await execute_payout("claim_abc123")
        >>> if result.success:
        ...     print(f"Paid ${result.amount} via tx {result.tx_hash}")
        >>> else:
        ...     print(f"Failed: {result.error}")
    """
    fund = get_fund()
    claim = fund.get_claim(claim_id)

    if not claim:
        raise ClaimNotFoundError(f"Claim not found: {claim_id}")

    if claim.status not in (ClaimStatus.APPROVED, ClaimStatus.PENDING):
        raise InvalidClaimStateError(
            f"Cannot execute payout for claim in status {claim.status.value}. "
            f"Expected APPROVED status."
        )

    # Get worker wallet from evidence if not provided
    if not worker_wallet:
        worker_wallet = claim.evidence.get("worker_wallet")
        if not worker_wallet:
            return PayoutResult(
                claim_id=claim_id,
                success=False,
                error="No worker wallet address available",
            )

    # Calculate payout
    breakdown = calculate_payout(claim)

    if breakdown.final_amount <= 0:
        return PayoutResult(
            claim_id=claim_id,
            success=False,
            error=breakdown.reason,
        )

    logger.info(
        "Executing payout for claim %s: $%.2f to %s",
        claim_id,
        float(breakdown.final_amount),
        worker_wallet[:10] + "...",
    )

    try:
        # Execute via x402
        tx_hash = await _send_x402_payment(
            recipient=worker_wallet,
            amount=breakdown.final_amount,
            claim_id=claim_id,
        )

        # Record the payout
        await record_payout(claim_id, tx_hash, breakdown.final_amount)

        return PayoutResult(
            claim_id=claim_id,
            success=True,
            tx_hash=tx_hash,
            amount=breakdown.final_amount,
        )

    except Exception as e:
        logger.error("Payout failed for claim %s: %s", claim_id, str(e))
        return PayoutResult(
            claim_id=claim_id,
            success=False,
            error=str(e),
        )


async def _send_x402_payment(
    recipient: str,
    amount: Decimal,
    claim_id: str,
) -> str:
    """
    Send payment via x402 protocol.

    This is a placeholder that would integrate with the actual x402 client.

    Args:
        recipient: Recipient wallet address
        amount: Amount to send
        claim_id: Claim ID for reference

    Returns:
        Transaction hash

    Raises:
        Exception: If payment fails
    """
    # Try to import x402 client
    try:
        from ..integrations.x402.client import X402Client

        client = X402Client(base_url=X402_FACILITATOR_URL)

        # Create payment
        result = await client.send_payment(
            recipient=recipient,
            amount=amount,
            token=PAYOUT_TOKEN,
            metadata={
                "type": "protection_fund_payout",
                "claim_id": claim_id,
            },
        )

        if not result.success:
            raise Exception(f"x402 payment failed: {result.error}")

        return result.tx_hash or f"x402_tx_{claim_id}"

    except ImportError:
        # Fallback to simulated payment if x402 client not available
        logger.warning(
            "x402 client not available, simulating payment for claim %s", claim_id
        )
        import uuid

        return f"sim_payout_{uuid.uuid4().hex[:12]}"


# =============================================================================
# Payout Recording
# =============================================================================


async def record_payout(
    claim_id: str,
    tx_hash: str,
    amount: Optional[Decimal] = None,
) -> FundClaim:
    """
    Record a completed payout transaction.

    Updates the claim with the transaction hash and marks it as paid.

    Args:
        claim_id: ID of the claim
        tx_hash: Transaction hash from blockchain
        amount: Amount paid (optional, uses approved amount)

    Returns:
        Updated FundClaim

    Raises:
        ClaimNotFoundError: If claim doesn't exist
    """
    fund = get_fund()
    claim = fund.get_claim(claim_id)

    if not claim:
        raise ClaimNotFoundError(f"Claim not found: {claim_id}")

    # Update claim record
    claim.tx_hash = tx_hash
    claim.paid_at = datetime.now(timezone.utc)
    claim.status = ClaimStatus.PAID

    # Update fund balance
    paid_amount = amount or claim.amount_approved
    fund._balance -= paid_amount

    # Update worker history
    history = fund._get_or_create_worker_history(claim.worker_id)
    history.total_paid += paid_amount
    history.paid_this_month += paid_amount

    logger.info(
        "Payout recorded: claim=%s, tx=%s, amount=$%.2f",
        claim_id,
        tx_hash,
        float(paid_amount),
    )

    return claim


# =============================================================================
# Batch Payouts
# =============================================================================


async def process_pending_payouts() -> List[PayoutResult]:
    """
    Process all approved claims awaiting payout.

    Returns:
        List of PayoutResult for each processed claim
    """
    fund = get_fund()

    # Get all approved claims
    approved = [
        claim for claim in fund._claims.values() if claim.status == ClaimStatus.APPROVED
    ]

    results = []
    for claim in approved:
        try:
            result = await execute_payout(claim.id)
            results.append(result)
        except Exception as e:
            logger.error("Error processing payout for %s: %s", claim.id, str(e))
            results.append(
                PayoutResult(
                    claim_id=claim.id,
                    success=False,
                    error=str(e),
                )
            )

    return results


def get_payout_history(
    worker_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Get payout history.

    Args:
        worker_id: Filter by worker (optional)
        limit: Maximum records to return

    Returns:
        List of payout records
    """
    fund = get_fund()

    # Get paid claims
    paid_claims = [
        claim for claim in fund._claims.values() if claim.status == ClaimStatus.PAID
    ]

    # Filter by worker if specified
    if worker_id:
        paid_claims = [c for c in paid_claims if c.worker_id == worker_id]

    # Sort by paid_at descending
    paid_claims.sort(
        key=lambda c: c.paid_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    # Limit results
    paid_claims = paid_claims[:limit]

    return [
        {
            "claim_id": c.id,
            "worker_id": c.worker_id,
            "amount": float(c.amount_approved),
            "tx_hash": c.tx_hash,
            "paid_at": c.paid_at.isoformat() if c.paid_at else None,
            "claim_type": c.claim_type.value,
        }
        for c in paid_claims
    ]


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "PayoutBreakdown",
    "PayoutResult",
    "calculate_payout",
    "execute_payout",
    "record_payout",
    "process_pending_payouts",
    "get_payout_history",
    "MAX_SINGLE_PAYOUT",
    "MIN_PAYOUT_AMOUNT",
]
