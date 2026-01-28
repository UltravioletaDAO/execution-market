"""
Chamba Prime - Premium Worker Tier (NOW-134)

Implements a premium worker tier with:
- Background checks
- Insurance coverage
- Service Level Agreements (SLAs)
- Priority task access
- Higher earnings potential

Prime workers get access to:
- High-value tasks ($50-500)
- Enterprise clients
- Guaranteed minimums
- Bonuses for SLA performance
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any


class PrimeStatus(str, Enum):
    """Status of a worker's Prime membership."""
    NONE = "none"                # Not a Prime worker
    PENDING = "pending"          # Application in review
    ACTIVE = "active"            # Active Prime member
    SUSPENDED = "suspended"      # Temporarily suspended
    REVOKED = "revoked"          # Permanently revoked


class BackgroundCheckStatus(str, Enum):
    """Status of background check."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    EXPIRED = "expired"          # Needs renewal


class InsuranceType(str, Enum):
    """Types of insurance coverage."""
    LIABILITY = "liability"       # General liability
    PROPERTY = "property"         # Property damage
    PROFESSIONAL = "professional" # Professional liability/E&O
    ACCIDENT = "accident"         # Personal accident


class SLALevel(str, Enum):
    """SLA commitment levels."""
    STANDARD = "standard"   # 95% on-time, 4-hour response
    PREMIUM = "premium"     # 98% on-time, 2-hour response
    ENTERPRISE = "enterprise"  # 99.5% on-time, 1-hour response


@dataclass
class BackgroundCheck:
    """
    Background check record.

    Attributes:
        check_id: Unique identifier
        check_type: Type of check (criminal, credit, employment)
        status: Current status
        provider: Background check provider
        submitted_at: When submitted
        completed_at: When completed
        expires_at: When check expires
        result_details: Details of results (redacted)
    """
    check_id: str
    check_type: str
    status: BackgroundCheckStatus
    provider: str
    submitted_at: datetime
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    result_details: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if background check is currently valid."""
        if self.status != BackgroundCheckStatus.PASSED:
            return False
        if self.expires_at and datetime.now(UTC) > self.expires_at:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (excludes sensitive details)."""
        return {
            "check_id": self.check_id,
            "check_type": self.check_type,
            "status": self.status.value,
            "provider": self.provider,
            "submitted_at": self.submitted_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_valid": self.is_valid(),
        }


@dataclass
class InsuranceCoverage:
    """
    Insurance coverage details.

    Attributes:
        insurance_type: Type of coverage
        coverage_amount: Maximum coverage in USD
        deductible: Deductible amount
        provider: Insurance provider
        policy_number: Policy number (redacted for display)
        effective_date: When coverage starts
        expiration_date: When coverage ends
        is_verified: Whether coverage has been verified
    """
    insurance_type: InsuranceType
    coverage_amount: Decimal
    deductible: Decimal
    provider: str
    policy_number: str
    effective_date: datetime
    expiration_date: datetime
    is_verified: bool = False

    def is_active(self) -> bool:
        """Check if coverage is currently active."""
        now = datetime.now(UTC)
        return (
            self.is_verified and
            self.effective_date <= now <= self.expiration_date
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "insurance_type": self.insurance_type.value,
            "coverage_amount": str(self.coverage_amount),
            "deductible": str(self.deductible),
            "provider": self.provider,
            "policy_number_last4": self.policy_number[-4:] if len(self.policy_number) >= 4 else "****",
            "effective_date": self.effective_date.isoformat(),
            "expiration_date": self.expiration_date.isoformat(),
            "is_verified": self.is_verified,
            "is_active": self.is_active(),
        }


@dataclass
class SLAConfig:
    """
    SLA configuration for a Prime worker.

    Attributes:
        level: SLA level
        on_time_target: Target on-time percentage (0-100)
        response_time_minutes: Max response time to accept task
        completion_rate_target: Target completion rate (0-100)
        quality_score_target: Min quality score (0-100)
        penalty_per_violation: Fee deducted per SLA miss
        bonus_for_perfect: Bonus for perfect monthly SLA
    """
    level: SLALevel
    on_time_target: float
    response_time_minutes: int
    completion_rate_target: float
    quality_score_target: float
    penalty_per_violation: Decimal
    bonus_for_perfect: Decimal

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "level": self.level.value,
            "on_time_target": self.on_time_target,
            "response_time_minutes": self.response_time_minutes,
            "completion_rate_target": self.completion_rate_target,
            "quality_score_target": self.quality_score_target,
            "penalty_per_violation": str(self.penalty_per_violation),
            "bonus_for_perfect": str(self.bonus_for_perfect),
        }


# Default SLA configurations
SLA_CONFIGS: Dict[SLALevel, SLAConfig] = {
    SLALevel.STANDARD: SLAConfig(
        level=SLALevel.STANDARD,
        on_time_target=95.0,
        response_time_minutes=240,  # 4 hours
        completion_rate_target=90.0,
        quality_score_target=70.0,
        penalty_per_violation=Decimal("5.00"),
        bonus_for_perfect=Decimal("25.00"),
    ),
    SLALevel.PREMIUM: SLAConfig(
        level=SLALevel.PREMIUM,
        on_time_target=98.0,
        response_time_minutes=120,  # 2 hours
        completion_rate_target=95.0,
        quality_score_target=80.0,
        penalty_per_violation=Decimal("10.00"),
        bonus_for_perfect=Decimal("50.00"),
    ),
    SLALevel.ENTERPRISE: SLAConfig(
        level=SLALevel.ENTERPRISE,
        on_time_target=99.5,
        response_time_minutes=60,  # 1 hour
        completion_rate_target=98.0,
        quality_score_target=90.0,
        penalty_per_violation=Decimal("25.00"),
        bonus_for_perfect=Decimal("100.00"),
    ),
}


@dataclass
class PrimeRequirements:
    """
    Requirements to become a Prime worker.

    Attributes:
        min_tasks_completed: Minimum completed tasks
        min_reputation: Minimum reputation score
        min_account_age_days: Minimum account age
        min_completion_rate: Minimum completion rate (0-100)
        background_check_required: Whether background check is needed
        insurance_required: Whether insurance is needed
        insurance_min_coverage: Minimum insurance coverage if required
    """
    min_tasks_completed: int = 100
    min_reputation: int = 70
    min_account_age_days: int = 30
    min_completion_rate: float = 95.0
    background_check_required: bool = True
    insurance_required: bool = True
    insurance_min_coverage: Decimal = Decimal("10000.00")

    def check_eligibility(
        self,
        tasks_completed: int,
        reputation: int,
        account_age_days: int,
        completion_rate: float,
        has_background_check: bool = False,
        has_insurance: bool = False,
        insurance_coverage: Decimal = Decimal("0"),
    ) -> tuple[bool, List[str]]:
        """
        Check if a worker meets Prime requirements.

        Returns:
            Tuple of (is_eligible, list of unmet requirements)
        """
        unmet = []

        if tasks_completed < self.min_tasks_completed:
            unmet.append(
                f"Need {self.min_tasks_completed - tasks_completed} more tasks "
                f"({tasks_completed}/{self.min_tasks_completed})"
            )

        if reputation < self.min_reputation:
            unmet.append(
                f"Reputation {reputation} below minimum {self.min_reputation}"
            )

        if account_age_days < self.min_account_age_days:
            unmet.append(
                f"Account must be {self.min_account_age_days} days old "
                f"(currently {account_age_days} days)"
            )

        if completion_rate < self.min_completion_rate:
            unmet.append(
                f"Completion rate {completion_rate:.1f}% below minimum {self.min_completion_rate}%"
            )

        if self.background_check_required and not has_background_check:
            unmet.append("Background check required")

        if self.insurance_required:
            if not has_insurance:
                unmet.append("Insurance coverage required")
            elif insurance_coverage < self.insurance_min_coverage:
                unmet.append(
                    f"Insurance coverage ${insurance_coverage} below minimum "
                    f"${self.insurance_min_coverage}"
                )

        return len(unmet) == 0, unmet

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "min_tasks_completed": self.min_tasks_completed,
            "min_reputation": self.min_reputation,
            "min_account_age_days": self.min_account_age_days,
            "min_completion_rate": self.min_completion_rate,
            "background_check_required": self.background_check_required,
            "insurance_required": self.insurance_required,
            "insurance_min_coverage": str(self.insurance_min_coverage),
        }


@dataclass
class PrimeMembership:
    """
    A worker's Prime membership.

    Attributes:
        worker_id: Worker identifier
        status: Current membership status
        sla_level: Current SLA commitment
        activated_at: When membership started
        expires_at: When membership expires (if not renewed)
        background_checks: List of background checks
        insurance_policies: List of insurance policies
        monthly_fee: Monthly membership fee
        earnings_multiplier: Bonus multiplier on earnings
        sla_performance: Current month's SLA metrics
    """
    worker_id: str
    status: PrimeStatus
    sla_level: SLALevel
    activated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    background_checks: List[BackgroundCheck] = field(default_factory=list)
    insurance_policies: List[InsuranceCoverage] = field(default_factory=list)
    monthly_fee: Decimal = Decimal("29.99")
    earnings_multiplier: Decimal = Decimal("1.20")  # 20% bonus
    sla_performance: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if membership is currently active."""
        if self.status != PrimeStatus.ACTIVE:
            return False
        if self.expires_at and datetime.now(UTC) > self.expires_at:
            return False
        return True

    def has_valid_background_check(self) -> bool:
        """Check if worker has a valid background check."""
        return any(bc.is_valid() for bc in self.background_checks)

    def has_valid_insurance(self, min_coverage: Decimal = Decimal("0")) -> bool:
        """Check if worker has valid insurance meeting minimum coverage."""
        for policy in self.insurance_policies:
            if policy.is_active() and policy.coverage_amount >= min_coverage:
                return True
        return False

    def get_sla_config(self) -> SLAConfig:
        """Get SLA configuration for current level."""
        return SLA_CONFIGS[self.sla_level]

    def calculate_effective_bounty(self, base_bounty: Decimal) -> Decimal:
        """Calculate bounty with Prime multiplier."""
        if not self.is_active():
            return base_bounty
        return base_bounty * self.earnings_multiplier

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "worker_id": self.worker_id,
            "status": self.status.value,
            "is_active": self.is_active(),
            "sla_level": self.sla_level.value,
            "sla_config": self.get_sla_config().to_dict(),
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "has_valid_background_check": self.has_valid_background_check(),
            "has_valid_insurance": self.has_valid_insurance(),
            "monthly_fee": str(self.monthly_fee),
            "earnings_multiplier": str(self.earnings_multiplier),
            "sla_performance": self.sla_performance,
        }


@dataclass
class SLAMetrics:
    """
    SLA performance metrics for a time period.

    Attributes:
        period_start: Start of measurement period
        period_end: End of measurement period
        tasks_completed: Total tasks completed
        tasks_on_time: Tasks completed on time
        tasks_late: Tasks completed late
        average_response_minutes: Average response time
        quality_score_average: Average quality score
        violations: List of SLA violations
    """
    period_start: datetime
    period_end: datetime
    tasks_completed: int = 0
    tasks_on_time: int = 0
    tasks_late: int = 0
    average_response_minutes: float = 0.0
    quality_score_average: float = 0.0
    violations: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def on_time_rate(self) -> float:
        """Calculate on-time percentage."""
        if self.tasks_completed == 0:
            return 100.0
        return (self.tasks_on_time / self.tasks_completed) * 100

    @property
    def completion_rate(self) -> float:
        """Calculate completion rate."""
        total = self.tasks_completed + self.tasks_late
        if total == 0:
            return 100.0
        return (self.tasks_completed / total) * 100

    def check_sla_compliance(self, sla_config: SLAConfig) -> Dict[str, Any]:
        """
        Check if metrics meet SLA requirements.

        Args:
            sla_config: SLA configuration to check against

        Returns:
            Dict with compliance status for each metric
        """
        return {
            "on_time": {
                "target": sla_config.on_time_target,
                "actual": round(self.on_time_rate, 2),
                "compliant": self.on_time_rate >= sla_config.on_time_target,
            },
            "response_time": {
                "target_minutes": sla_config.response_time_minutes,
                "actual_minutes": round(self.average_response_minutes, 1),
                "compliant": self.average_response_minutes <= sla_config.response_time_minutes,
            },
            "quality_score": {
                "target": sla_config.quality_score_target,
                "actual": round(self.quality_score_average, 1),
                "compliant": self.quality_score_average >= sla_config.quality_score_target,
            },
            "overall_compliant": (
                self.on_time_rate >= sla_config.on_time_target and
                self.average_response_minutes <= sla_config.response_time_minutes and
                self.quality_score_average >= sla_config.quality_score_target
            ),
            "violations_count": len(self.violations),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "tasks_completed": self.tasks_completed,
            "tasks_on_time": self.tasks_on_time,
            "tasks_late": self.tasks_late,
            "on_time_rate": round(self.on_time_rate, 2),
            "average_response_minutes": round(self.average_response_minutes, 1),
            "quality_score_average": round(self.quality_score_average, 1),
            "violations_count": len(self.violations),
        }


class PrimeManager:
    """
    Manages Prime worker memberships and SLA tracking.
    """

    def __init__(
        self,
        requirements: Optional[PrimeRequirements] = None,
        sla_configs: Optional[Dict[SLALevel, SLAConfig]] = None,
    ):
        self.requirements = requirements or PrimeRequirements()
        self.sla_configs = sla_configs or SLA_CONFIGS

    def check_prime_eligibility(
        self,
        tasks_completed: int,
        reputation: int,
        account_age_days: int,
        completion_rate: float,
        has_background_check: bool = False,
        has_insurance: bool = False,
        insurance_coverage: Decimal = Decimal("0"),
    ) -> Dict[str, Any]:
        """
        Check if a worker is eligible for Prime.

        Returns:
            Dict with eligibility status and details
        """
        is_eligible, unmet = self.requirements.check_eligibility(
            tasks_completed=tasks_completed,
            reputation=reputation,
            account_age_days=account_age_days,
            completion_rate=completion_rate,
            has_background_check=has_background_check,
            has_insurance=has_insurance,
            insurance_coverage=insurance_coverage,
        )

        return {
            "is_eligible": is_eligible,
            "unmet_requirements": unmet,
            "requirements": self.requirements.to_dict(),
            "benefits": self._get_prime_benefits(),
        }

    def _get_prime_benefits(self) -> Dict[str, Any]:
        """Get summary of Prime benefits."""
        return {
            "earnings_multiplier": "1.20x (20% bonus)",
            "task_access": "Tier 3 tasks ($50-500)",
            "priority_matching": "First access to new tasks",
            "sla_bonuses": "Up to $100/month for perfect SLA",
            "enterprise_access": "Access to enterprise clients",
            "insurance_coverage": "Backed by verified insurance",
            "support_priority": "Priority customer support",
        }

    def create_membership(
        self,
        worker_id: str,
        sla_level: SLALevel = SLALevel.STANDARD,
        duration_months: int = 1,
    ) -> PrimeMembership:
        """
        Create a new Prime membership.

        Args:
            worker_id: Worker identifier
            sla_level: Initial SLA level
            duration_months: Membership duration

        Returns:
            New PrimeMembership
        """
        now = datetime.now(UTC)

        return PrimeMembership(
            worker_id=worker_id,
            status=PrimeStatus.PENDING,  # Starts as pending until checks complete
            sla_level=sla_level,
            activated_at=None,  # Set when approved
            expires_at=now + timedelta(days=30 * duration_months),
        )

    def activate_membership(self, membership: PrimeMembership) -> PrimeMembership:
        """
        Activate a pending membership.

        Args:
            membership: Membership to activate

        Returns:
            Activated membership
        """
        # Verify requirements
        if not membership.has_valid_background_check():
            raise ValueError("Cannot activate: no valid background check")

        if not membership.has_valid_insurance(self.requirements.insurance_min_coverage):
            raise ValueError("Cannot activate: insufficient insurance coverage")

        membership.status = PrimeStatus.ACTIVE
        membership.activated_at = datetime.now(UTC)

        return membership

    def calculate_monthly_settlement(
        self,
        membership: PrimeMembership,
        metrics: SLAMetrics,
    ) -> Dict[str, Any]:
        """
        Calculate monthly settlement for a Prime worker.

        Includes:
        - SLA compliance check
        - Violation penalties
        - Perfect performance bonuses
        - Monthly fee

        Args:
            membership: Worker's membership
            metrics: Month's SLA metrics

        Returns:
            Dict with settlement details
        """
        sla_config = membership.get_sla_config()
        compliance = metrics.check_sla_compliance(sla_config)

        # Calculate penalties
        penalty_total = sla_config.penalty_per_violation * len(metrics.violations)

        # Calculate bonus (if perfect compliance)
        bonus = Decimal("0")
        if compliance["overall_compliant"] and len(metrics.violations) == 0:
            bonus = sla_config.bonus_for_perfect

        # Net adjustment
        net_adjustment = bonus - penalty_total - membership.monthly_fee

        return {
            "period": {
                "start": metrics.period_start.isoformat(),
                "end": metrics.period_end.isoformat(),
            },
            "sla_compliance": compliance,
            "violations": len(metrics.violations),
            "penalty_total": str(penalty_total),
            "perfect_bonus": str(bonus) if bonus > 0 else None,
            "monthly_fee": str(membership.monthly_fee),
            "net_adjustment": str(net_adjustment),
            "breakdown": {
                "bonus": str(bonus),
                "penalties": str(penalty_total),
                "fee": str(membership.monthly_fee),
                "total": str(net_adjustment),
            }
        }

    def recommend_sla_upgrade(
        self,
        metrics: SLAMetrics,
        current_level: SLALevel,
    ) -> Optional[Dict[str, Any]]:
        """
        Recommend SLA upgrade if worker qualifies.

        Args:
            metrics: Recent performance metrics
            current_level: Current SLA level

        Returns:
            Upgrade recommendation or None
        """
        level_order = [SLALevel.STANDARD, SLALevel.PREMIUM, SLALevel.ENTERPRISE]
        current_idx = level_order.index(current_level)

        if current_idx >= len(level_order) - 1:
            return None  # Already at highest level

        next_level = level_order[current_idx + 1]
        next_config = self.sla_configs[next_level]

        # Check if worker exceeds next level requirements
        exceeds_on_time = metrics.on_time_rate >= next_config.on_time_target
        exceeds_response = metrics.average_response_minutes <= next_config.response_time_minutes
        exceeds_quality = metrics.quality_score_average >= next_config.quality_score_target

        if exceeds_on_time and exceeds_response and exceeds_quality:
            return {
                "recommended_level": next_level.value,
                "current_performance": {
                    "on_time_rate": round(metrics.on_time_rate, 2),
                    "response_minutes": round(metrics.average_response_minutes, 1),
                    "quality_score": round(metrics.quality_score_average, 1),
                },
                "next_level_requirements": next_config.to_dict(),
                "additional_benefits": {
                    "higher_bonus": str(next_config.bonus_for_perfect),
                    "faster_response_expected": f"{next_config.response_time_minutes} minutes",
                }
            }

        return None


# Convenience functions
def check_prime_eligibility(
    tasks_completed: int,
    reputation: int,
    account_age_days: int,
    completion_rate: float,
) -> Dict[str, Any]:
    """Quick check of Prime eligibility (without insurance/background checks)."""
    manager = PrimeManager()
    return manager.check_prime_eligibility(
        tasks_completed=tasks_completed,
        reputation=reputation,
        account_age_days=account_age_days,
        completion_rate=completion_rate,
    )


def get_sla_config(level: SLALevel) -> SLAConfig:
    """Get SLA configuration for a level."""
    return SLA_CONFIGS[level]


def get_prime_requirements() -> PrimeRequirements:
    """Get Prime membership requirements."""
    return PrimeRequirements()
