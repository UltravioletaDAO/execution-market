"""
Execution Market Task Insurance (NOW-139, NOW-140)

Implements tiered task insurance:
- Basic: 5% fee, covers up to $50
- Standard: 10% fee, covers up to $200
- Premium: 20% fee, covers up to $1000

Insurance covers:
- Worker non-completion (task expires without delivery)
- Fraud/fake submissions
- Quality failures (after dispute)
- Damage during delivery

Does NOT cover:
- Agent cancellation
- Force majeure
- Worker disputes in progress
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4


class InsuranceTier(str, Enum):
    """Insurance tier levels."""
    NONE = "none"           # No insurance
    BASIC = "basic"         # 5% fee, up to $50
    STANDARD = "standard"   # 10% fee, up to $200
    PREMIUM = "premium"     # 20% fee, up to $1000


class ClaimType(str, Enum):
    """Types of insurance claims."""
    NON_COMPLETION = "non_completion"  # Task not completed
    FRAUD = "fraud"                    # Fake/fraudulent submission
    QUALITY_FAILURE = "quality_failure"  # Quality below standard
    DAMAGE = "damage"                  # Damage during task
    THEFT = "theft"                    # Item stolen
    LATE_DELIVERY = "late_delivery"    # Severe delivery delay


class ClaimStatus(str, Enum):
    """Status of an insurance claim."""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DENIED = "denied"
    PAID = "paid"


@dataclass
class InsuranceTierConfig:
    """
    Configuration for an insurance tier.

    Attributes:
        tier: The tier level
        fee_percentage: Fee as percentage of task bounty
        max_coverage: Maximum payout
        deductible: Amount agent pays before insurance kicks in
        eligible_claims: Types of claims covered
        processing_days: Days to process a claim
        description: Tier description
    """
    tier: InsuranceTier
    fee_percentage: Decimal
    max_coverage: Decimal
    deductible: Decimal
    eligible_claims: List[ClaimType]
    processing_days: int
    description: str = ""

    def calculate_fee(self, bounty: Decimal) -> Decimal:
        """
        Calculate insurance fee for a bounty.

        Args:
            bounty: Task bounty amount

        Returns:
            Fee amount
        """
        return (bounty * self.fee_percentage / 100).quantize(Decimal("0.01"))

    def calculate_payout(self, claim_amount: Decimal) -> Decimal:
        """
        Calculate payout for a claim.

        Args:
            claim_amount: Amount being claimed

        Returns:
            Actual payout after deductible and max coverage
        """
        # Subtract deductible
        after_deductible = max(Decimal("0"), claim_amount - self.deductible)

        # Apply max coverage
        payout = min(after_deductible, self.max_coverage)

        return payout.quantize(Decimal("0.01"))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "tier": self.tier.value,
            "fee_percentage": str(self.fee_percentage),
            "max_coverage": str(self.max_coverage),
            "deductible": str(self.deductible),
            "eligible_claims": [c.value for c in self.eligible_claims],
            "processing_days": self.processing_days,
            "description": self.description,
        }


# Default tier configurations
INSURANCE_TIERS: Dict[InsuranceTier, InsuranceTierConfig] = {
    InsuranceTier.NONE: InsuranceTierConfig(
        tier=InsuranceTier.NONE,
        fee_percentage=Decimal("0"),
        max_coverage=Decimal("0"),
        deductible=Decimal("0"),
        eligible_claims=[],
        processing_days=0,
        description="No insurance coverage",
    ),
    InsuranceTier.BASIC: InsuranceTierConfig(
        tier=InsuranceTier.BASIC,
        fee_percentage=Decimal("5"),
        max_coverage=Decimal("50"),
        deductible=Decimal("2"),
        eligible_claims=[
            ClaimType.NON_COMPLETION,
            ClaimType.FRAUD,
        ],
        processing_days=5,
        description="Basic coverage for task non-completion and fraud",
    ),
    InsuranceTier.STANDARD: InsuranceTierConfig(
        tier=InsuranceTier.STANDARD,
        fee_percentage=Decimal("10"),
        max_coverage=Decimal("200"),
        deductible=Decimal("5"),
        eligible_claims=[
            ClaimType.NON_COMPLETION,
            ClaimType.FRAUD,
            ClaimType.QUALITY_FAILURE,
            ClaimType.LATE_DELIVERY,
        ],
        processing_days=3,
        description="Standard coverage including quality failures",
    ),
    InsuranceTier.PREMIUM: InsuranceTierConfig(
        tier=InsuranceTier.PREMIUM,
        fee_percentage=Decimal("20"),
        max_coverage=Decimal("1000"),
        deductible=Decimal("0"),  # No deductible for premium
        eligible_claims=[
            ClaimType.NON_COMPLETION,
            ClaimType.FRAUD,
            ClaimType.QUALITY_FAILURE,
            ClaimType.DAMAGE,
            ClaimType.THEFT,
            ClaimType.LATE_DELIVERY,
        ],
        processing_days=1,
        description="Full coverage with no deductible, priority processing",
    ),
}


@dataclass
class TaskInsurance:
    """
    Insurance policy for a specific task.

    Attributes:
        policy_id: Unique policy identifier
        task_id: Covered task ID
        tier: Insurance tier
        bounty_covered: Original bounty amount
        fee_paid: Insurance fee paid
        max_payout: Maximum possible payout
        created_at: When policy was created
        expires_at: When coverage expires
        is_active: Whether policy is active
        claims: List of claims against this policy
    """
    policy_id: str
    task_id: str
    tier: InsuranceTier
    bounty_covered: Decimal
    fee_paid: Decimal
    max_payout: Decimal
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: Optional[datetime] = None
    is_active: bool = True
    claims: List["InsuranceClaim"] = field(default_factory=list)

    def can_claim(self, claim_type: ClaimType) -> tuple[bool, str]:
        """
        Check if a claim type can be filed.

        Args:
            claim_type: Type of claim

        Returns:
            Tuple of (can_claim, reason)
        """
        if not self.is_active:
            return False, "Policy is no longer active"

        if self.expires_at and datetime.now(UTC) > self.expires_at:
            return False, "Policy has expired"

        tier_config = INSURANCE_TIERS[self.tier]

        if claim_type not in tier_config.eligible_claims:
            return False, f"Claim type {claim_type.value} not covered by {self.tier.value} tier"

        # Check if there's already an approved claim
        for claim in self.claims:
            if claim.status in [ClaimStatus.APPROVED, ClaimStatus.PAID]:
                return False, "Policy already has an approved claim"

        return True, "Eligible for claim"

    @property
    def remaining_coverage(self) -> Decimal:
        """Calculate remaining coverage after claims."""
        paid_claims = sum(
            c.payout_amount for c in self.claims
            if c.status == ClaimStatus.PAID
        )
        return max(Decimal("0"), self.max_payout - paid_claims)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "policy_id": self.policy_id,
            "task_id": self.task_id,
            "tier": self.tier.value,
            "bounty_covered": str(self.bounty_covered),
            "fee_paid": str(self.fee_paid),
            "max_payout": str(self.max_payout),
            "remaining_coverage": str(self.remaining_coverage),
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "claims_count": len(self.claims),
        }


@dataclass
class InsuranceClaim:
    """
    An insurance claim.

    Attributes:
        claim_id: Unique claim identifier
        policy_id: Related policy ID
        task_id: Related task ID
        claim_type: Type of claim
        claimed_amount: Amount being claimed
        payout_amount: Approved payout amount
        status: Claim status
        reason: Detailed reason for claim
        evidence: List of evidence URLs
        submitted_at: When claim was submitted
        reviewed_at: When claim was reviewed
        reviewer_notes: Notes from reviewer
    """
    claim_id: str
    policy_id: str
    task_id: str
    claim_type: ClaimType
    claimed_amount: Decimal
    payout_amount: Decimal = Decimal("0")
    status: ClaimStatus = ClaimStatus.SUBMITTED
    reason: str = ""
    evidence: List[str] = field(default_factory=list)
    submitted_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reviewed_at: Optional[datetime] = None
    reviewer_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "claim_id": self.claim_id,
            "policy_id": self.policy_id,
            "task_id": self.task_id,
            "claim_type": self.claim_type.value,
            "claimed_amount": str(self.claimed_amount),
            "payout_amount": str(self.payout_amount),
            "status": self.status.value,
            "reason": self.reason,
            "evidence_count": len(self.evidence),
            "submitted_at": self.submitted_at.isoformat(),
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }


class InsuranceManager:
    """
    Manages task insurance policies and claims.
    """

    def __init__(
        self,
        tier_configs: Optional[Dict[InsuranceTier, InsuranceTierConfig]] = None,
    ):
        self.tier_configs = tier_configs or INSURANCE_TIERS

    def get_tier_config(self, tier: InsuranceTier) -> InsuranceTierConfig:
        """Get configuration for a tier."""
        return self.tier_configs[tier]

    def calculate_insurance_options(
        self,
        bounty: Decimal,
    ) -> Dict[str, Any]:
        """
        Calculate insurance options and fees for a task.

        Args:
            bounty: Task bounty amount

        Returns:
            Dict with all tier options
        """
        options = {}

        for tier, config in self.tier_configs.items():
            if tier == InsuranceTier.NONE:
                options[tier.value] = {
                    "fee": "0.00",
                    "max_coverage": "0.00",
                    "description": config.description,
                }
            else:
                fee = config.calculate_fee(bounty)
                # Max coverage is either the bounty or tier max, whichever is lower
                effective_coverage = min(bounty, config.max_coverage)

                options[tier.value] = {
                    "fee": str(fee),
                    "fee_percentage": str(config.fee_percentage),
                    "max_coverage": str(effective_coverage),
                    "deductible": str(config.deductible),
                    "eligible_claims": [c.value for c in config.eligible_claims],
                    "processing_days": config.processing_days,
                    "description": config.description,
                }

        return {
            "bounty": str(bounty),
            "options": options,
            "recommended": self._recommend_tier(bounty),
        }

    def _recommend_tier(self, bounty: Decimal) -> str:
        """Recommend an insurance tier based on bounty."""
        if bounty <= Decimal("10"):
            return InsuranceTier.NONE.value
        elif bounty <= Decimal("50"):
            return InsuranceTier.BASIC.value
        elif bounty <= Decimal("200"):
            return InsuranceTier.STANDARD.value
        else:
            return InsuranceTier.PREMIUM.value

    def create_policy(
        self,
        task_id: str,
        bounty: Decimal,
        tier: InsuranceTier,
        validity_days: int = 30,
    ) -> TaskInsurance:
        """
        Create an insurance policy for a task.

        Args:
            task_id: Task to insure
            bounty: Task bounty amount
            tier: Insurance tier
            validity_days: How long policy is valid

        Returns:
            New TaskInsurance policy
        """
        if tier == InsuranceTier.NONE:
            raise ValueError("Cannot create policy with NONE tier")

        config = self.tier_configs[tier]
        fee = config.calculate_fee(bounty)
        max_payout = min(bounty, config.max_coverage)

        return TaskInsurance(
            policy_id=str(uuid4()),
            task_id=task_id,
            tier=tier,
            bounty_covered=bounty,
            fee_paid=fee,
            max_payout=max_payout,
            expires_at=datetime.now(UTC) + timedelta(days=validity_days),
        )

    def submit_claim(
        self,
        policy: TaskInsurance,
        claim_type: ClaimType,
        claimed_amount: Decimal,
        reason: str,
        evidence: List[str],
    ) -> InsuranceClaim:
        """
        Submit an insurance claim.

        Args:
            policy: The insurance policy
            claim_type: Type of claim
            claimed_amount: Amount being claimed
            reason: Reason for claim
            evidence: Evidence URLs

        Returns:
            New InsuranceClaim

        Raises:
            ValueError: If claim cannot be submitted
        """
        can_claim, error = policy.can_claim(claim_type)
        if not can_claim:
            raise ValueError(error)

        claim = InsuranceClaim(
            claim_id=str(uuid4()),
            policy_id=policy.policy_id,
            task_id=policy.task_id,
            claim_type=claim_type,
            claimed_amount=claimed_amount,
            reason=reason,
            evidence=evidence,
        )

        policy.claims.append(claim)
        return claim

    def review_claim(
        self,
        claim: InsuranceClaim,
        policy: TaskInsurance,
        approved: bool,
        reviewer_notes: str = "",
    ) -> InsuranceClaim:
        """
        Review and decide on a claim.

        Args:
            claim: The claim to review
            policy: The related policy
            approved: Whether to approve
            reviewer_notes: Reviewer's notes

        Returns:
            Updated claim
        """
        claim.reviewed_at = datetime.now(UTC)
        claim.reviewer_notes = reviewer_notes

        if approved:
            claim.status = ClaimStatus.APPROVED

            # Calculate payout
            config = self.tier_configs[policy.tier]
            claim.payout_amount = config.calculate_payout(claim.claimed_amount)

            # Cap at remaining coverage
            claim.payout_amount = min(
                claim.payout_amount,
                policy.remaining_coverage,
            )
        else:
            claim.status = ClaimStatus.DENIED
            claim.payout_amount = Decimal("0")

        return claim

    def process_payout(self, claim: InsuranceClaim) -> Dict[str, Any]:
        """
        Process payout for an approved claim.

        Args:
            claim: Approved claim

        Returns:
            Payout details
        """
        if claim.status != ClaimStatus.APPROVED:
            raise ValueError("Can only process payouts for approved claims")

        claim.status = ClaimStatus.PAID

        return {
            "claim_id": claim.claim_id,
            "payout_amount": str(claim.payout_amount),
            "processed_at": datetime.now(UTC).isoformat(),
            "status": "paid",
        }

    def get_claim_statistics(
        self,
        claims: List[InsuranceClaim],
    ) -> Dict[str, Any]:
        """
        Calculate statistics for a list of claims.

        Args:
            claims: List of claims to analyze

        Returns:
            Statistics dict
        """
        if not claims:
            return {
                "total_claims": 0,
                "approved_rate": 0,
                "total_claimed": "0.00",
                "total_paid": "0.00",
            }

        total = len(claims)
        approved = sum(1 for c in claims if c.status in [ClaimStatus.APPROVED, ClaimStatus.PAID])
        denied = sum(1 for c in claims if c.status == ClaimStatus.DENIED)

        total_claimed = sum(c.claimed_amount for c in claims)
        total_paid = sum(c.payout_amount for c in claims if c.status == ClaimStatus.PAID)

        by_type = {}
        for claim in claims:
            ct = claim.claim_type.value
            if ct not in by_type:
                by_type[ct] = {"count": 0, "claimed": Decimal("0"), "paid": Decimal("0")}
            by_type[ct]["count"] += 1
            by_type[ct]["claimed"] += claim.claimed_amount
            if claim.status == ClaimStatus.PAID:
                by_type[ct]["paid"] += claim.payout_amount

        return {
            "total_claims": total,
            "approved": approved,
            "denied": denied,
            "pending": total - approved - denied,
            "approved_rate": round((approved / total) * 100, 1) if total > 0 else 0,
            "total_claimed": str(total_claimed),
            "total_paid": str(total_paid),
            "by_type": {
                k: {
                    "count": v["count"],
                    "claimed": str(v["claimed"]),
                    "paid": str(v["paid"]),
                }
                for k, v in by_type.items()
            },
        }


# Convenience functions
def get_insurance_fee(bounty_usd: float, tier: InsuranceTier) -> float:
    """
    Quick calculation of insurance fee.

    Args:
        bounty_usd: Task bounty
        tier: Insurance tier

    Returns:
        Fee amount
    """
    if tier == InsuranceTier.NONE:
        return 0.0

    config = INSURANCE_TIERS[tier]
    return float(config.calculate_fee(Decimal(str(bounty_usd))))


def get_max_coverage(tier: InsuranceTier) -> float:
    """Get maximum coverage for a tier."""
    return float(INSURANCE_TIERS[tier].max_coverage)


def recommend_tier(bounty_usd: float) -> InsuranceTier:
    """
    Get recommended insurance tier for a bounty.

    Args:
        bounty_usd: Task bounty

    Returns:
        Recommended InsuranceTier
    """
    bounty = Decimal(str(bounty_usd))

    if bounty <= Decimal("10"):
        return InsuranceTier.NONE
    elif bounty <= Decimal("50"):
        return InsuranceTier.BASIC
    elif bounty <= Decimal("200"):
        return InsuranceTier.STANDARD
    else:
        return InsuranceTier.PREMIUM


def get_tier_comparison() -> List[Dict[str, Any]]:
    """Get comparison of all insurance tiers."""
    return [config.to_dict() for config in INSURANCE_TIERS.values()]
