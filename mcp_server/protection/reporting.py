"""
Fund Reporting for Worker Protection Fund

Provides analytics and reporting for the protection fund.

Operations:
- get_fund_stats() - Contributions, payouts, balance
- get_claims_summary(period) - Claims by type, status
- forecast_sustainability() - Project fund health
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional, List, Any, Tuple

from .fund import (
    get_fund,
    FundConfig,
    FundContribution,
    FundClaim,
    ClaimStatus,
    ClaimType,
    ContributionSource,
    WorkerClaimHistory,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Report Periods
# =============================================================================


class ReportPeriod(str, Enum):
    """Time periods for reporting."""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    ALL_TIME = "all_time"


def _get_period_start(period: ReportPeriod) -> datetime:
    """Get the start datetime for a period."""
    now = datetime.now(timezone.utc)

    if period == ReportPeriod.DAY:
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == ReportPeriod.WEEK:
        days_since_monday = now.weekday()
        return (now - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    elif period == ReportPeriod.MONTH:
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == ReportPeriod.QUARTER:
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        return now.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == ReportPeriod.YEAR:
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # ALL_TIME
        return datetime.min.replace(tzinfo=timezone.utc)


# =============================================================================
# Fund Statistics
# =============================================================================


@dataclass
class FundStats:
    """
    Comprehensive fund statistics.

    Attributes:
        balance: Current fund balance
        total_contributions: Total contributed all time
        total_payouts: Total paid out all time
        contributions_by_source: Breakdown by contribution source
        active_claims: Number of pending claims
        total_claims: Total claims all time
        average_claim_amount: Average claim amount
        approval_rate: Percentage of claims approved
    """
    balance: Decimal
    total_contributions: Decimal
    total_payouts: Decimal
    contributions_by_source: Dict[str, Decimal]
    active_claims: int
    total_claims: int
    average_claim_amount: Decimal
    approval_rate: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "balance": float(self.balance),
            "total_contributions": float(self.total_contributions),
            "total_payouts": float(self.total_payouts),
            "contributions_by_source": {
                k: float(v) for k, v in self.contributions_by_source.items()
            },
            "active_claims": self.active_claims,
            "total_claims": self.total_claims,
            "average_claim_amount": float(self.average_claim_amount),
            "approval_rate": round(self.approval_rate * 100, 1),
            "timestamp": self.timestamp.isoformat(),
        }


def get_fund_stats() -> FundStats:
    """
    Get comprehensive fund statistics.

    Returns:
        FundStats with current fund state

    Example:
        >>> stats = get_fund_stats()
        >>> print(f"Balance: ${stats.balance}, Approval rate: {stats.approval_rate*100}%")
    """
    fund = get_fund()

    # Get all contributions
    contributions = fund._contributions
    total_contributions = sum(c.amount for c in contributions)

    # Group by source
    contributions_by_source: Dict[str, Decimal] = {}
    for source in ContributionSource:
        amount = sum(c.amount for c in contributions if c.source == source)
        if amount > 0:
            contributions_by_source[source.value] = amount

    # Get all claims
    claims = list(fund._claims.values())
    total_claims = len(claims)
    active_claims = len([c for c in claims if c.status == ClaimStatus.PENDING])

    # Calculate payouts
    paid_claims = [c for c in claims if c.status == ClaimStatus.PAID]
    total_payouts = sum(c.amount_approved for c in paid_claims)

    # Average claim amount
    if claims:
        average_claim = sum(c.amount_requested for c in claims) / len(claims)
    else:
        average_claim = Decimal("0")

    # Approval rate
    decided_claims = [c for c in claims if c.status in (ClaimStatus.PAID, ClaimStatus.REJECTED)]
    if decided_claims:
        approved_count = len([c for c in decided_claims if c.status == ClaimStatus.PAID])
        approval_rate = approved_count / len(decided_claims)
    else:
        approval_rate = 0.0

    return FundStats(
        balance=fund.balance,
        total_contributions=total_contributions,
        total_payouts=total_payouts,
        contributions_by_source=contributions_by_source,
        active_claims=active_claims,
        total_claims=total_claims,
        average_claim_amount=average_claim,
        approval_rate=approval_rate,
    )


# =============================================================================
# Claims Summary
# =============================================================================


@dataclass
class ClaimsSummary:
    """
    Summary of claims for a period.

    Attributes:
        period: Report period
        period_start: Start of period
        total_claims: Number of claims in period
        claims_by_type: Count by claim type
        claims_by_status: Count by status
        total_requested: Total amount requested
        total_approved: Total amount approved
        total_paid: Total amount paid
        average_processing_time: Average time to process (hours)
    """
    period: str
    period_start: datetime
    total_claims: int
    claims_by_type: Dict[str, int]
    claims_by_status: Dict[str, int]
    total_requested: Decimal
    total_approved: Decimal
    total_paid: Decimal
    average_processing_time: float  # hours

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "period": self.period,
            "period_start": self.period_start.isoformat(),
            "total_claims": self.total_claims,
            "claims_by_type": self.claims_by_type,
            "claims_by_status": self.claims_by_status,
            "total_requested": float(self.total_requested),
            "total_approved": float(self.total_approved),
            "total_paid": float(self.total_paid),
            "average_processing_time_hours": round(self.average_processing_time, 2),
        }


def get_claims_summary(period: ReportPeriod = ReportPeriod.MONTH) -> ClaimsSummary:
    """
    Get claims summary for a period.

    Args:
        period: Time period to summarize

    Returns:
        ClaimsSummary with aggregated data

    Example:
        >>> summary = get_claims_summary(ReportPeriod.WEEK)
        >>> print(f"This week: {summary.total_claims} claims, ${summary.total_paid} paid")
    """
    fund = get_fund()
    period_start = _get_period_start(period)

    # Filter claims by period
    claims = [
        c for c in fund._claims.values()
        if c.created_at >= period_start
    ]

    # Count by type
    claims_by_type: Dict[str, int] = {}
    for claim_type in ClaimType:
        count = len([c for c in claims if c.claim_type == claim_type])
        if count > 0:
            claims_by_type[claim_type.value] = count

    # Count by status
    claims_by_status: Dict[str, int] = {}
    for status in ClaimStatus:
        count = len([c for c in claims if c.status == status])
        if count > 0:
            claims_by_status[status.value] = count

    # Totals
    total_requested = sum(c.amount_requested for c in claims)
    total_approved = sum(c.amount_approved for c in claims if c.status in (ClaimStatus.APPROVED, ClaimStatus.PAID))
    total_paid = sum(c.amount_approved for c in claims if c.status == ClaimStatus.PAID)

    # Average processing time
    processed_claims = [
        c for c in claims
        if c.reviewed_at and c.created_at
    ]
    if processed_claims:
        total_hours = sum(
            (c.reviewed_at - c.created_at).total_seconds() / 3600
            for c in processed_claims
        )
        avg_processing_time = total_hours / len(processed_claims)
    else:
        avg_processing_time = 0.0

    return ClaimsSummary(
        period=period.value,
        period_start=period_start,
        total_claims=len(claims),
        claims_by_type=claims_by_type,
        claims_by_status=claims_by_status,
        total_requested=total_requested,
        total_approved=total_approved,
        total_paid=total_paid,
        average_processing_time=avg_processing_time,
    )


# =============================================================================
# Sustainability Forecast
# =============================================================================


@dataclass
class SustainabilityForecast:
    """
    Forecast of fund sustainability.

    Attributes:
        current_balance: Current fund balance
        avg_monthly_inflow: Average monthly contributions
        avg_monthly_outflow: Average monthly payouts
        net_monthly_flow: Net monthly change
        months_runway: Estimated months until fund exhaustion
        health_status: "healthy", "warning", "critical"
        recommendations: List of recommendations
    """
    current_balance: Decimal
    avg_monthly_inflow: Decimal
    avg_monthly_outflow: Decimal
    net_monthly_flow: Decimal
    months_runway: float
    health_status: str
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "current_balance": float(self.current_balance),
            "avg_monthly_inflow": float(self.avg_monthly_inflow),
            "avg_monthly_outflow": float(self.avg_monthly_outflow),
            "net_monthly_flow": float(self.net_monthly_flow),
            "months_runway": round(self.months_runway, 1) if self.months_runway < float('inf') else "unlimited",
            "health_status": self.health_status,
            "recommendations": self.recommendations,
        }


def forecast_sustainability(months_lookback: int = 3) -> SustainabilityForecast:
    """
    Forecast fund health and sustainability.

    Uses historical data to project future fund balance and
    provide recommendations.

    Args:
        months_lookback: Number of months of history to analyze

    Returns:
        SustainabilityForecast with projections and recommendations

    Example:
        >>> forecast = forecast_sustainability()
        >>> print(f"Runway: {forecast.months_runway} months")
        >>> print(f"Status: {forecast.health_status}")
        >>> for rec in forecast.recommendations:
        ...     print(f"  - {rec}")
    """
    fund = get_fund()
    now = datetime.now(timezone.utc)
    lookback_start = now - timedelta(days=months_lookback * 30)

    # Calculate average monthly inflow
    contributions_in_period = [
        c for c in fund._contributions
        if c.contributed_at >= lookback_start
    ]
    total_inflow = sum(c.amount for c in contributions_in_period)
    avg_monthly_inflow = total_inflow / months_lookback if months_lookback > 0 else Decimal("0")

    # Calculate average monthly outflow
    paid_claims_in_period = [
        c for c in fund._claims.values()
        if c.status == ClaimStatus.PAID and c.paid_at and c.paid_at >= lookback_start
    ]
    total_outflow = sum(c.amount_approved for c in paid_claims_in_period)
    avg_monthly_outflow = total_outflow / months_lookback if months_lookback > 0 else Decimal("0")

    # Net monthly flow
    net_monthly_flow = avg_monthly_inflow - avg_monthly_outflow

    # Calculate runway
    current_balance = fund.balance
    if net_monthly_flow >= 0:
        months_runway = float('inf')  # Growing or stable
    elif avg_monthly_outflow > 0:
        months_runway = float(current_balance / avg_monthly_outflow)
    else:
        months_runway = float('inf')

    # Determine health status
    if months_runway == float('inf') or months_runway > 6:
        health_status = "healthy"
    elif months_runway > 3:
        health_status = "warning"
    else:
        health_status = "critical"

    # Generate recommendations
    recommendations = []

    if health_status == "critical":
        recommendations.append("URGENT: Increase fund contributions immediately")
        recommendations.append("Consider reducing maximum claim amounts temporarily")
    elif health_status == "warning":
        recommendations.append("Review contribution rates - consider increasing from 1%")
        recommendations.append("Monitor claim patterns for unusual activity")

    if avg_monthly_outflow > avg_monthly_inflow:
        recommendations.append(
            f"Outflow (${float(avg_monthly_outflow):.2f}/mo) exceeds inflow "
            f"(${float(avg_monthly_inflow):.2f}/mo)"
        )

    if current_balance < fund.config.min_fund_balance_warning:
        recommendations.append(
            f"Balance ${float(current_balance):.2f} is below warning threshold "
            f"${float(fund.config.min_fund_balance_warning):.2f}"
        )

    if not recommendations:
        recommendations.append("Fund is operating within healthy parameters")

    return SustainabilityForecast(
        current_balance=current_balance,
        avg_monthly_inflow=avg_monthly_inflow,
        avg_monthly_outflow=avg_monthly_outflow,
        net_monthly_flow=net_monthly_flow,
        months_runway=months_runway,
        health_status=health_status,
        recommendations=recommendations,
    )


# =============================================================================
# Worker Analytics
# =============================================================================


@dataclass
class WorkerAnalytics:
    """
    Analytics for a specific worker.

    Attributes:
        worker_id: Worker's ID
        total_claims: Number of claims submitted
        approved_claims: Number approved
        rejected_claims: Number rejected
        total_received: Total amount received
        average_claim: Average claim amount
        last_claim_at: When last claim was submitted
    """
    worker_id: str
    total_claims: int
    approved_claims: int
    rejected_claims: int
    total_received: Decimal
    average_claim: Decimal
    last_claim_at: Optional[datetime]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "worker_id": self.worker_id,
            "total_claims": self.total_claims,
            "approved_claims": self.approved_claims,
            "rejected_claims": self.rejected_claims,
            "approval_rate": round(self.approved_claims / self.total_claims * 100, 1) if self.total_claims > 0 else 0,
            "total_received": float(self.total_received),
            "average_claim": float(self.average_claim),
            "last_claim_at": self.last_claim_at.isoformat() if self.last_claim_at else None,
        }


def get_worker_analytics(worker_id: str) -> WorkerAnalytics:
    """
    Get analytics for a specific worker.

    Args:
        worker_id: Worker's ID

    Returns:
        WorkerAnalytics with worker's claim history
    """
    fund = get_fund()
    claims = fund.get_worker_claims(worker_id)

    total_claims = len(claims)
    approved_claims = len([c for c in claims if c.status == ClaimStatus.PAID])
    rejected_claims = len([c for c in claims if c.status == ClaimStatus.REJECTED])
    total_received = sum(c.amount_approved for c in claims if c.status == ClaimStatus.PAID)

    if claims:
        average_claim = sum(c.amount_requested for c in claims) / len(claims)
        last_claim_at = max(c.created_at for c in claims)
    else:
        average_claim = Decimal("0")
        last_claim_at = None

    return WorkerAnalytics(
        worker_id=worker_id,
        total_claims=total_claims,
        approved_claims=approved_claims,
        rejected_claims=rejected_claims,
        total_received=total_received,
        average_claim=average_claim,
        last_claim_at=last_claim_at,
    )


def get_top_claimants(limit: int = 10) -> List[WorkerAnalytics]:
    """
    Get workers with the most claims.

    Args:
        limit: Maximum number of workers to return

    Returns:
        List of WorkerAnalytics sorted by claim count
    """
    fund = get_fund()

    # Group claims by worker
    worker_claims: Dict[str, List[FundClaim]] = {}
    for claim in fund._claims.values():
        if claim.worker_id not in worker_claims:
            worker_claims[claim.worker_id] = []
        worker_claims[claim.worker_id].append(claim)

    # Get analytics for each
    analytics = [
        get_worker_analytics(worker_id)
        for worker_id in worker_claims.keys()
    ]

    # Sort by total claims descending
    analytics.sort(key=lambda a: a.total_claims, reverse=True)

    return analytics[:limit]


# =============================================================================
# Report Generation
# =============================================================================


def generate_full_report() -> Dict[str, Any]:
    """
    Generate a comprehensive fund report.

    Returns:
        Dict with all report sections
    """
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fund_stats": get_fund_stats().to_dict(),
        "claims_summary": {
            "daily": get_claims_summary(ReportPeriod.DAY).to_dict(),
            "weekly": get_claims_summary(ReportPeriod.WEEK).to_dict(),
            "monthly": get_claims_summary(ReportPeriod.MONTH).to_dict(),
        },
        "sustainability": forecast_sustainability().to_dict(),
        "top_claimants": [a.to_dict() for a in get_top_claimants(5)],
    }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "ReportPeriod",
    "FundStats",
    "ClaimsSummary",
    "SustainabilityForecast",
    "WorkerAnalytics",
    "get_fund_stats",
    "get_claims_summary",
    "forecast_sustainability",
    "get_worker_analytics",
    "get_top_claimants",
    "generate_full_report",
]
