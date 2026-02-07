"""
Worker Protection Fund

Emergency fund for worker protection in edge cases where normal payment flows fail.

Sources of funding:
- 1% of each task bounty (FUND_CONTRIBUTION_PERCENT)
- Slashed agent bonds (when agents unfairly reject work)
- Manual deposits from treasury

Core operations:
- get_fund_balance() - Current fund balance
- contribute(task_id, amount) - Add to fund on task completion
- process_claim(claim_id) - Pay out approved claim

Use cases:
- Unpaid work (agent disappeared, payment failure)
- Dispute loss compensation
- Platform error remediation
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

FUND_CONTRIBUTION_PERCENT = Decimal("0.01")  # 1% of each task bounty


# =============================================================================
# Exceptions
# =============================================================================


class FundError(Exception):
    """Base exception for Protection Fund operations."""

    pass


class InsufficientFundsError(FundError):
    """Raised when fund balance is insufficient for a claim."""

    pass


class ClaimLimitExceededError(FundError):
    """Raised when worker has exceeded their claim limits."""

    pass


class ClaimNotFoundError(FundError):
    """Raised when a claim is not found."""

    pass


class InvalidClaimStateError(FundError):
    """Raised when claim operation is invalid for current state."""

    pass


# =============================================================================
# Enums
# =============================================================================


class ClaimType(str, Enum):
    """Types of protection fund claims."""

    AGENT_DISAPPEARED = "agent_disappeared"  # Agent stopped responding
    PAYMENT_FAILURE = "payment_failure"  # x402/escrow system failure
    UNJUST_REJECTION = (
        "unjust_rejection"  # Arbitration found for worker but payment failed
    )
    EMERGENCY_HARDSHIP = "emergency_hardship"  # Case-by-case emergency


class ClaimStatus(str, Enum):
    """Status of a protection fund claim."""

    PENDING = "pending"  # Awaiting review
    APPROVED = "approved"  # Approved, awaiting payment
    REJECTED = "rejected"  # Claim denied
    PAID = "paid"  # Payment sent to worker
    CANCELLED = "cancelled"  # Cancelled by worker


class ContributionSource(str, Enum):
    """Source of fund contributions."""

    PLATFORM_FEE = "platform_fee"  # 0.5% of platform fees
    SLASHED_BOND = "slashed_bond"  # Agent bond slashed for unfair rejection
    MANUAL_DEPOSIT = "manual_deposit"  # Manual top-up by treasury


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class FundConfig:
    """
    Configuration for the Worker Protection Fund.

    Attributes:
        contribution_rate: Percentage of task bounty contributed to fund (1%)
        max_claim_amount: Maximum amount per claim in USD
        max_monthly_per_worker: Maximum claims per worker per month in USD
        min_claim_amount: Minimum amount for a claim
        claim_review_timeout_hours: Hours before unreviewed claims auto-escalate
        min_fund_balance_warning: Balance below which to trigger warning
        max_claim_percent: Maximum claim as percentage of original bounty (80%)
        claim_cooldown_days: Days between claims for same worker (30)
    """

    contribution_rate: Decimal = FUND_CONTRIBUTION_PERCENT  # 1% of bounty
    max_claim_amount: Decimal = Decimal("50.00")  # $50 max per claim
    max_monthly_per_worker: Decimal = Decimal("200.00")  # $200/month/worker
    min_claim_amount: Decimal = Decimal("0.50")  # Minimum $0.50
    claim_review_timeout_hours: int = 72  # 3 days
    min_fund_balance_warning: Decimal = Decimal("100.00")  # Warn below $100
    max_claim_percent: Decimal = Decimal("0.80")  # Max 80% of original bounty
    claim_cooldown_days: int = 30  # 1 claim per 30 days


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class FundContribution:
    """
    Record of a contribution to the protection fund.

    Attributes:
        id: Unique contribution identifier
        source: Source of contribution (fee, slash, manual)
        amount: Amount contributed in USD
        task_id: Related task ID (if applicable)
        original_amount: Original amount from which contribution was derived
        description: Human-readable description
        contributed_at: Timestamp of contribution
    """

    id: str
    source: ContributionSource
    amount: Decimal
    task_id: Optional[str]
    original_amount: Optional[Decimal]
    description: str
    contributed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "source": self.source.value,
            "amount": float(self.amount),
            "task_id": self.task_id,
            "original_amount": float(self.original_amount)
            if self.original_amount
            else None,
            "description": self.description,
            "contributed_at": self.contributed_at.isoformat(),
        }


@dataclass
class FundClaim:
    """
    A worker's claim against the protection fund.

    Attributes:
        id: Unique claim identifier
        worker_id: Worker making the claim
        claim_type: Type of claim
        amount_requested: Amount requested by worker
        amount_approved: Amount approved (may be less than requested)
        reason: Worker's explanation for the claim
        evidence: Supporting evidence (task IDs, screenshots, etc.)
        status: Current status of the claim
        task_id: Related task ID (if applicable)
        created_at: When claim was submitted
        reviewed_at: When claim was reviewed
        reviewer_id: Who reviewed the claim
        reviewer_notes: Reviewer's notes
        paid_at: When payment was sent
        tx_hash: Transaction hash of payment
    """

    id: str
    worker_id: str
    claim_type: ClaimType
    amount_requested: Decimal
    amount_approved: Decimal
    reason: str
    evidence: Dict[str, Any]
    status: ClaimStatus
    task_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: Optional[datetime] = None
    reviewer_id: Optional[str] = None
    reviewer_notes: Optional[str] = None
    paid_at: Optional[datetime] = None
    tx_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "worker_id": self.worker_id,
            "claim_type": self.claim_type.value,
            "amount_requested": float(self.amount_requested),
            "amount_approved": float(self.amount_approved),
            "reason": self.reason,
            "evidence": self.evidence,
            "status": self.status.value,
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat(),
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewer_id": self.reviewer_id,
            "reviewer_notes": self.reviewer_notes,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "tx_hash": self.tx_hash,
        }


@dataclass
class WorkerClaimHistory:
    """
    Summary of a worker's claim history.

    Attributes:
        worker_id: Worker identifier
        total_claimed: Total amount claimed all time
        total_paid: Total amount paid all time
        claims_this_month: Amount claimed this calendar month
        paid_this_month: Amount paid this calendar month
        claim_count: Total number of claims
        last_claim_at: When last claim was submitted
    """

    worker_id: str
    total_claimed: Decimal = Decimal("0")
    total_paid: Decimal = Decimal("0")
    claims_this_month: Decimal = Decimal("0")
    paid_this_month: Decimal = Decimal("0")
    claim_count: int = 0
    last_claim_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "worker_id": self.worker_id,
            "total_claimed": float(self.total_claimed),
            "total_paid": float(self.total_paid),
            "claims_this_month": float(self.claims_this_month),
            "paid_this_month": float(self.paid_this_month),
            "claim_count": self.claim_count,
            "last_claim_at": self.last_claim_at.isoformat()
            if self.last_claim_at
            else None,
        }


# =============================================================================
# Protection Fund Manager
# =============================================================================


class ProtectionFund:
    """
    Manages the Worker Protection Fund.

    The protection fund is an emergency reserve to protect workers in edge cases
    where normal payment mechanisms fail. It's funded by:
    - 0.5% of all platform fees (automatic)
    - Slashed agent bonds (when agents unfairly reject work)

    Workers can claim up to $50 per claim and $200 per month.

    Example:
        >>> fund = ProtectionFund()
        >>>
        >>> # Contribute from platform fee
        >>> contrib = fund.contribute_from_fee("task123", Decimal("10.00"))
        >>> print(f"Added ${contrib.amount} from fee")
        Added $0.05 from fee
        >>>
        >>> # Worker submits claim
        >>> claim = await fund.submit_claim(
        ...     worker_id="worker456",
        ...     claim_type=ClaimType.AGENT_DISAPPEARED,
        ...     amount=Decimal("25.00"),
        ...     reason="Agent stopped responding after 3 days",
        ...     evidence={"task_id": "task123", "last_contact": "2026-01-20"}
        ... )
        >>>
        >>> # Admin approves and pays
        >>> claim = await fund.approve_claim(claim.id, "admin789", Decimal("25.00"))
    """

    def __init__(
        self,
        config: Optional[FundConfig] = None,
        initial_balance: Decimal = Decimal("0"),
    ):
        """
        Initialize the Protection Fund.

        Args:
            config: Fund configuration (uses defaults if not provided)
            initial_balance: Starting balance (for testing or seeding)
        """
        self.config = config or FundConfig()
        self._balance: Decimal = initial_balance
        self._contributions: List[FundContribution] = []
        self._claims: Dict[str, FundClaim] = {}
        self._worker_claims: Dict[str, List[str]] = {}  # worker_id -> [claim_ids]
        self._worker_history: Dict[str, WorkerClaimHistory] = {}

        logger.info(
            "ProtectionFund initialized: balance=$%.2f, max_claim=$%.2f, max_monthly=$%.2f",
            float(self._balance),
            float(self.config.max_claim_amount),
            float(self.config.max_monthly_per_worker),
        )

    # -------------------------------------------------------------------------
    # Fund Contributions (NOW-100)
    # -------------------------------------------------------------------------

    def contribute(
        self,
        task_id: str,
        bounty_amount: Decimal,
    ) -> FundContribution:
        """
        Contribute 1% of a task bounty to the fund.

        Called automatically when a task is completed.

        Args:
            task_id: Task ID the bounty came from
            bounty_amount: Total task bounty amount

        Returns:
            FundContribution record

        Example:
            >>> contrib = fund.contribute("task123", Decimal("10.00"))
            >>> contrib.amount
            Decimal('0.10')  # 1% of $10.00
        """
        contribution_amount = (bounty_amount * self.config.contribution_rate).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

        # Only contribute if amount is meaningful
        if contribution_amount <= Decimal("0"):
            logger.debug(
                "Bounty contribution too small for task %s: $%.4f",
                task_id,
                float(bounty_amount * self.config.contribution_rate),
            )
            contribution_amount = Decimal("0")

        contribution = FundContribution(
            id=f"contrib_{uuid.uuid4().hex[:12]}",
            source=ContributionSource.PLATFORM_FEE,
            amount=contribution_amount,
            task_id=task_id,
            original_amount=bounty_amount,
            description=f"1% of task bounty from task {task_id}",
        )

        self._balance += contribution_amount
        self._contributions.append(contribution)

        logger.info(
            "Bounty contribution for task %s: $%.4f (from $%.2f bounty). Balance: $%.2f",
            task_id,
            float(contribution_amount),
            float(bounty_amount),
            float(self._balance),
        )

        self._check_balance_warning()

        return contribution

    def contribute_from_fee(
        self,
        task_id: str,
        fee_amount: Decimal,
    ) -> FundContribution:
        """
        Contribute from a platform fee (legacy method).

        Kept for backward compatibility. Prefer contribute() for new code.

        Args:
            task_id: Task ID the fee came from
            fee_amount: Total platform fee amount

        Returns:
            FundContribution record
        """
        return self.contribute(task_id, fee_amount)

    def contribute_from_slash(
        self,
        amount: Decimal,
        reason: str,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> FundContribution:
        """
        Contribute slashed bond amount to the fund.

        Called when an agent's bond is slashed for unfair rejection.
        The slashed amount goes to the protection fund to help other workers.

        Args:
            amount: Amount slashed
            reason: Reason for the slash
            task_id: Related task ID (if any)
            agent_id: Agent whose bond was slashed

        Returns:
            FundContribution record

        Example:
            >>> contrib = fund.contribute_from_slash(
            ...     amount=Decimal("5.00"),
            ...     reason="Unfair rejection - arbitration ruled for worker",
            ...     task_id="task123",
            ...     agent_id="agent456"
            ... )
        """
        description = f"Slashed bond: {reason}"
        if agent_id:
            description += f" (agent: {agent_id[:8]}...)"

        contribution = FundContribution(
            id=f"contrib_{uuid.uuid4().hex[:12]}",
            source=ContributionSource.SLASHED_BOND,
            amount=amount,
            task_id=task_id,
            original_amount=amount,
            description=description,
        )

        self._balance += amount
        self._contributions.append(contribution)

        logger.info(
            "Slashed bond contribution: $%.2f. Reason: %s. Balance: $%.2f",
            float(amount),
            reason,
            float(self._balance),
        )

        return contribution

    def contribute_manual(
        self,
        amount: Decimal,
        description: str,
        contributor_id: str,
    ) -> FundContribution:
        """
        Manual contribution to the fund (treasury top-up).

        Args:
            amount: Amount to contribute
            description: Reason for contribution
            contributor_id: Who is contributing

        Returns:
            FundContribution record
        """
        contribution = FundContribution(
            id=f"contrib_{uuid.uuid4().hex[:12]}",
            source=ContributionSource.MANUAL_DEPOSIT,
            amount=amount,
            task_id=None,
            original_amount=amount,
            description=f"Manual deposit by {contributor_id}: {description}",
        )

        self._balance += amount
        self._contributions.append(contribution)

        logger.info(
            "Manual contribution: $%.2f by %s. Balance: $%.2f",
            float(amount),
            contributor_id,
            float(self._balance),
        )

        return contribution

    # -------------------------------------------------------------------------
    # Claim Submission (NOW-101)
    # -------------------------------------------------------------------------

    async def submit_claim(
        self,
        worker_id: str,
        claim_type: ClaimType,
        amount: Decimal,
        reason: str,
        evidence: Dict[str, Any],
        task_id: Optional[str] = None,
    ) -> FundClaim:
        """
        Submit a claim for review.

        Args:
            worker_id: Worker submitting the claim
            claim_type: Type of claim
            amount: Amount requested (max $50)
            reason: Explanation for the claim
            evidence: Supporting evidence
            task_id: Related task ID (if applicable)

        Returns:
            FundClaim with PENDING status

        Raises:
            ClaimLimitExceededError: If worker has exceeded monthly limits
            FundError: If amount is invalid

        Example:
            >>> claim = await fund.submit_claim(
            ...     worker_id="worker123",
            ...     claim_type=ClaimType.AGENT_DISAPPEARED,
            ...     amount=Decimal("30.00"),
            ...     reason="Agent stopped responding 5 days ago",
            ...     evidence={
            ...         "task_id": "task456",
            ...         "last_contact": "2026-01-20T10:00:00Z",
            ...         "screenshots": ["url1", "url2"]
            ...     }
            ... )
        """
        # Validate amount
        if amount < self.config.min_claim_amount:
            raise FundError(
                f"Claim amount ${float(amount):.2f} is below minimum "
                f"${float(self.config.min_claim_amount):.2f}"
            )

        if amount > self.config.max_claim_amount:
            raise FundError(
                f"Claim amount ${float(amount):.2f} exceeds maximum "
                f"${float(self.config.max_claim_amount):.2f} per claim"
            )

        # Check worker eligibility
        is_eligible, message = self.check_worker_eligibility(worker_id, amount)
        if not is_eligible:
            raise ClaimLimitExceededError(message)

        # Create claim
        claim = FundClaim(
            id=f"claim_{uuid.uuid4().hex[:12]}",
            worker_id=worker_id,
            claim_type=claim_type,
            amount_requested=amount,
            amount_approved=Decimal("0"),  # Set on approval
            reason=reason,
            evidence=evidence,
            status=ClaimStatus.PENDING,
            task_id=task_id,
        )

        # Store claim
        self._claims[claim.id] = claim

        # Update worker's claim list
        if worker_id not in self._worker_claims:
            self._worker_claims[worker_id] = []
        self._worker_claims[worker_id].append(claim.id)

        # Update worker history
        history = self._get_or_create_worker_history(worker_id)
        history.total_claimed += amount
        history.claims_this_month += amount
        history.claim_count += 1
        history.last_claim_at = claim.created_at

        logger.info(
            "Claim submitted: id=%s, worker=%s, type=%s, amount=$%.2f",
            claim.id,
            worker_id[:8] + "...",
            claim_type.value,
            float(amount),
        )

        return claim

    def check_worker_eligibility(
        self,
        worker_id: str,
        amount: Decimal,
    ) -> tuple[bool, str]:
        """
        Check if a worker can claim the requested amount.

        Args:
            worker_id: Worker ID
            amount: Amount they want to claim

        Returns:
            Tuple of (is_eligible, message explaining why/why not)

        Example:
            >>> eligible, msg = fund.check_worker_eligibility("worker123", Decimal("50.00"))
            >>> if not eligible:
            ...     print(f"Cannot claim: {msg}")
        """
        # Check per-claim limit
        if amount > self.config.max_claim_amount:
            return False, (
                f"Amount ${float(amount):.2f} exceeds per-claim limit of "
                f"${float(self.config.max_claim_amount):.2f}"
            )

        # Get worker history
        history = self._get_or_create_worker_history(worker_id)

        # Reset monthly counter if new month
        self._reset_monthly_if_needed(history)

        # Check monthly limit
        would_be_total = history.paid_this_month + amount
        if would_be_total > self.config.max_monthly_per_worker:
            remaining = self.config.max_monthly_per_worker - history.paid_this_month
            return False, (
                f"Would exceed monthly limit of ${float(self.config.max_monthly_per_worker):.2f}. "
                f"Already paid this month: ${float(history.paid_this_month):.2f}. "
                f"Remaining allowance: ${float(remaining):.2f}"
            )

        return True, (
            f"Eligible. Monthly remaining: "
            f"${float(self.config.max_monthly_per_worker - history.paid_this_month):.2f}"
        )

    # -------------------------------------------------------------------------
    # Claim Review
    # -------------------------------------------------------------------------

    async def approve_claim(
        self,
        claim_id: str,
        reviewer_id: str,
        amount: Decimal,
        notes: Optional[str] = None,
    ) -> FundClaim:
        """
        Approve a claim and initiate payment.

        Args:
            claim_id: Claim to approve
            reviewer_id: Who is approving
            amount: Amount to approve (can be less than requested)
            notes: Reviewer notes

        Returns:
            Updated FundClaim with APPROVED status

        Raises:
            ClaimNotFoundError: If claim doesn't exist
            InvalidClaimStateError: If claim is not pending
            InsufficientFundsError: If fund balance is too low

        Example:
            >>> claim = await fund.approve_claim(
            ...     claim_id="claim_abc123",
            ...     reviewer_id="admin456",
            ...     amount=Decimal("25.00"),
            ...     notes="Verified agent unresponsive. Partial approval."
            ... )
        """
        claim = self._get_claim(claim_id)

        # Validate state
        if claim.status != ClaimStatus.PENDING:
            raise InvalidClaimStateError(
                f"Cannot approve claim in status {claim.status.value}. "
                f"Only {ClaimStatus.PENDING.value} claims can be approved."
            )

        # Validate amount
        if amount > claim.amount_requested:
            raise FundError(
                f"Approved amount ${float(amount):.2f} exceeds requested "
                f"${float(claim.amount_requested):.2f}"
            )

        if amount > self.config.max_claim_amount:
            raise FundError(
                f"Approved amount ${float(amount):.2f} exceeds maximum "
                f"${float(self.config.max_claim_amount):.2f}"
            )

        # Check fund balance
        if amount > self._balance:
            raise InsufficientFundsError(
                f"Fund balance ${float(self._balance):.2f} is insufficient "
                f"for claim of ${float(amount):.2f}"
            )

        # Update claim
        claim.status = ClaimStatus.APPROVED
        claim.amount_approved = amount
        claim.reviewed_at = datetime.now(timezone.utc)
        claim.reviewer_id = reviewer_id
        claim.reviewer_notes = notes

        logger.info(
            "Claim approved: id=%s, worker=%s, amount=$%.2f (requested $%.2f)",
            claim_id,
            claim.worker_id[:8] + "...",
            float(amount),
            float(claim.amount_requested),
        )

        # Auto-pay immediately (in production, this would trigger actual payment)
        return await self._pay_claim(claim)

    async def reject_claim(
        self,
        claim_id: str,
        reviewer_id: str,
        reason: str,
    ) -> FundClaim:
        """
        Reject a claim.

        Args:
            claim_id: Claim to reject
            reviewer_id: Who is rejecting
            reason: Reason for rejection

        Returns:
            Updated FundClaim with REJECTED status

        Raises:
            ClaimNotFoundError: If claim doesn't exist
            InvalidClaimStateError: If claim is not pending
        """
        claim = self._get_claim(claim_id)

        if claim.status != ClaimStatus.PENDING:
            raise InvalidClaimStateError(
                f"Cannot reject claim in status {claim.status.value}. "
                f"Only {ClaimStatus.PENDING.value} claims can be rejected."
            )

        # Update claim
        claim.status = ClaimStatus.REJECTED
        claim.reviewed_at = datetime.now(timezone.utc)
        claim.reviewer_id = reviewer_id
        claim.reviewer_notes = reason

        # Revert the claimed amount from history since it won't be paid
        history = self._get_or_create_worker_history(claim.worker_id)
        history.total_claimed -= claim.amount_requested
        history.claims_this_month -= claim.amount_requested

        logger.info(
            "Claim rejected: id=%s, worker=%s, reason=%s",
            claim_id,
            claim.worker_id[:8] + "...",
            reason,
        )

        return claim

    # -------------------------------------------------------------------------
    # Fund Statistics
    # -------------------------------------------------------------------------

    def get_fund_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive fund statistics.

        Returns:
            Dict with fund statistics including balance, contributions, claims

        Example:
            >>> stats = fund.get_fund_stats()
            >>> print(f"Balance: ${stats['balance']}, Total paid: ${stats['total_paid']}")
        """
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Contribution stats
        total_from_fees = sum(
            c.amount
            for c in self._contributions
            if c.source == ContributionSource.PLATFORM_FEE
        )
        total_from_slashes = sum(
            c.amount
            for c in self._contributions
            if c.source == ContributionSource.SLASHED_BOND
        )
        total_manual = sum(
            c.amount
            for c in self._contributions
            if c.source == ContributionSource.MANUAL_DEPOSIT
        )

        contributions_this_month = [
            c for c in self._contributions if c.contributed_at >= month_start
        ]

        # Claim stats
        all_claims = list(self._claims.values())
        pending_claims = [c for c in all_claims if c.status == ClaimStatus.PENDING]
        approved_claims = [c for c in all_claims if c.status == ClaimStatus.APPROVED]
        paid_claims = [c for c in all_claims if c.status == ClaimStatus.PAID]
        rejected_claims = [c for c in all_claims if c.status == ClaimStatus.REJECTED]

        total_paid = sum(c.amount_approved for c in paid_claims)
        total_requested = sum(c.amount_requested for c in all_claims)

        claims_this_month = [c for c in all_claims if c.created_at >= month_start]
        paid_this_month = sum(
            c.amount_approved for c in claims_this_month if c.status == ClaimStatus.PAID
        )

        return {
            "balance": float(self._balance),
            "balance_warning": self._balance < self.config.min_fund_balance_warning,
            "contributions": {
                "total": float(total_from_fees + total_from_slashes + total_manual),
                "from_fees": float(total_from_fees),
                "from_slashes": float(total_from_slashes),
                "manual": float(total_manual),
                "count": len(self._contributions),
                "this_month": float(sum(c.amount for c in contributions_this_month)),
            },
            "claims": {
                "total_count": len(all_claims),
                "pending_count": len(pending_claims),
                "approved_count": len(approved_claims),
                "paid_count": len(paid_claims),
                "rejected_count": len(rejected_claims),
                "total_requested": float(total_requested),
                "total_paid": float(total_paid),
                "this_month": {
                    "count": len(claims_this_month),
                    "paid": float(paid_this_month),
                },
            },
            "config": {
                "contribution_rate": float(self.config.contribution_rate * 100),
                "max_claim_amount": float(self.config.max_claim_amount),
                "max_monthly_per_worker": float(self.config.max_monthly_per_worker),
                "max_claim_percent": float(self.config.max_claim_percent * 100),
                "claim_cooldown_days": self.config.claim_cooldown_days,
            },
            "unique_workers_claimed": len(self._worker_claims),
        }

    def get_claim(self, claim_id: str) -> Optional[FundClaim]:
        """Get a claim by ID."""
        return self._claims.get(claim_id)

    def get_worker_claims(self, worker_id: str) -> List[FundClaim]:
        """Get all claims for a worker."""
        claim_ids = self._worker_claims.get(worker_id, [])
        return [self._claims[cid] for cid in claim_ids if cid in self._claims]

    def get_worker_history(self, worker_id: str) -> Optional[WorkerClaimHistory]:
        """Get claim history for a worker."""
        history = self._worker_history.get(worker_id)
        if history:
            self._reset_monthly_if_needed(history)
        return history

    def get_pending_claims(self) -> List[FundClaim]:
        """Get all pending claims awaiting review."""
        return [c for c in self._claims.values() if c.status == ClaimStatus.PENDING]

    def get_recent_contributions(self, limit: int = 20) -> List[FundContribution]:
        """Get recent contributions."""
        return sorted(
            self._contributions, key=lambda c: c.contributed_at, reverse=True
        )[:limit]

    @property
    def balance(self) -> Decimal:
        """Current fund balance."""
        return self._balance

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------

    def _get_claim(self, claim_id: str) -> FundClaim:
        """Get claim or raise error."""
        claim = self._claims.get(claim_id)
        if not claim:
            raise ClaimNotFoundError(f"Claim not found: {claim_id}")
        return claim

    def _get_or_create_worker_history(self, worker_id: str) -> WorkerClaimHistory:
        """Get or create worker claim history."""
        if worker_id not in self._worker_history:
            self._worker_history[worker_id] = WorkerClaimHistory(worker_id=worker_id)
        return self._worker_history[worker_id]

    def _reset_monthly_if_needed(self, history: WorkerClaimHistory) -> None:
        """Reset monthly counters if it's a new month."""
        if not history.last_claim_at:
            return

        now = datetime.now(timezone.utc)
        last_claim_month = (history.last_claim_at.year, history.last_claim_at.month)
        current_month = (now.year, now.month)

        if last_claim_month != current_month:
            logger.debug(
                "Resetting monthly counters for worker %s",
                history.worker_id[:8] + "...",
            )
            history.claims_this_month = Decimal("0")
            history.paid_this_month = Decimal("0")

    async def _pay_claim(self, claim: FundClaim) -> FundClaim:
        """
        Execute payment for an approved claim.

        In production, this would integrate with x402 for actual payment.
        """
        if claim.status != ClaimStatus.APPROVED:
            raise InvalidClaimStateError(
                f"Cannot pay claim in status {claim.status.value}"
            )

        amount = claim.amount_approved

        # Check balance again (defensive)
        if amount > self._balance:
            raise InsufficientFundsError(
                f"Fund balance ${float(self._balance):.2f} is insufficient "
                f"for payment of ${float(amount):.2f}"
            )

        # Deduct from balance
        self._balance -= amount

        # Update claim
        claim.status = ClaimStatus.PAID
        claim.paid_at = datetime.now(timezone.utc)
        claim.tx_hash = f"sim_tx_{uuid.uuid4().hex[:12]}"  # Simulated tx hash

        # Update worker history
        history = self._get_or_create_worker_history(claim.worker_id)
        history.total_paid += amount
        history.paid_this_month += amount

        logger.info(
            "Claim paid: id=%s, worker=%s, amount=$%.2f, tx=%s. Fund balance: $%.2f",
            claim.id,
            claim.worker_id[:8] + "...",
            float(amount),
            claim.tx_hash,
            float(self._balance),
        )

        self._check_balance_warning()

        return claim

    def _check_balance_warning(self) -> None:
        """Log warning if balance is low."""
        if self._balance < self.config.min_fund_balance_warning:
            logger.warning(
                "Protection fund balance is LOW: $%.2f (warning threshold: $%.2f)",
                float(self._balance),
                float(self.config.min_fund_balance_warning),
            )

    # -------------------------------------------------------------------------
    # Process Claim (Main Entry Point)
    # -------------------------------------------------------------------------

    async def process_claim(self, claim_id: str) -> FundClaim:
        """
        Pay out an approved claim.

        This is the main entry point for processing claims after approval.
        It handles the actual payout via x402 integration.

        Args:
            claim_id: ID of the approved claim to process

        Returns:
            FundClaim with PAID status and transaction hash

        Raises:
            ClaimNotFoundError: If claim doesn't exist
            InvalidClaimStateError: If claim is not in APPROVED status
            InsufficientFundsError: If fund balance is too low

        Example:
            >>> # First approve the claim
            >>> claim = await fund.approve_claim(claim_id, "admin", amount)
            >>> # Then process the payout
            >>> paid_claim = await fund.process_claim(claim_id)
            >>> print(f"Paid via tx: {paid_claim.tx_hash}")
        """
        claim = self._get_claim(claim_id)

        if claim.status != ClaimStatus.APPROVED:
            raise InvalidClaimStateError(
                f"Cannot process claim in status {claim.status.value}. "
                f"Claim must be {ClaimStatus.APPROVED.value} first."
            )

        return await self._pay_claim(claim)


# =============================================================================
# Module-Level Singleton
# =============================================================================


_default_fund: Optional[ProtectionFund] = None


def get_fund() -> ProtectionFund:
    """
    Get or create the default ProtectionFund instance.

    Returns:
        ProtectionFund singleton instance
    """
    global _default_fund
    if _default_fund is None:
        _default_fund = ProtectionFund()
    return _default_fund


def reset_fund() -> None:
    """Reset the singleton fund (for testing)."""
    global _default_fund
    _default_fund = None


# =============================================================================
# Convenience Functions
# =============================================================================


def contribute_fee(task_id: str, fee_amount: Decimal) -> FundContribution:
    """
    Convenience function to contribute from a platform fee.

    Args:
        task_id: Task the fee came from
        fee_amount: Platform fee amount

    Returns:
        FundContribution record
    """
    return get_fund().contribute_from_fee(task_id, fee_amount)


def contribute_slash(
    amount: Decimal,
    reason: str,
    task_id: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> FundContribution:
    """
    Convenience function to contribute from a slashed bond.

    Args:
        amount: Slashed amount
        reason: Reason for slash
        task_id: Related task ID
        agent_id: Agent whose bond was slashed

    Returns:
        FundContribution record
    """
    return get_fund().contribute_from_slash(amount, reason, task_id, agent_id)


async def submit_worker_claim(
    worker_id: str,
    claim_type: ClaimType,
    amount: Decimal,
    reason: str,
    evidence: Dict[str, Any],
    task_id: Optional[str] = None,
) -> FundClaim:
    """
    Convenience function to submit a worker claim.

    Args:
        worker_id: Worker ID
        claim_type: Type of claim
        amount: Amount requested
        reason: Explanation
        evidence: Supporting evidence
        task_id: Related task ID

    Returns:
        FundClaim in PENDING status
    """
    return await get_fund().submit_claim(
        worker_id=worker_id,
        claim_type=claim_type,
        amount=amount,
        reason=reason,
        evidence=evidence,
        task_id=task_id,
    )


def get_fund_balance() -> Decimal:
    """Get current fund balance."""
    return get_fund().balance


def get_fund_statistics() -> Dict[str, Any]:
    """Get fund statistics."""
    return get_fund().get_fund_stats()
