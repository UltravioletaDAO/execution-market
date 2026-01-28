"""
Worker Protection Module

Provides emergency fund and worker safety mechanisms for the Chamba platform.

Components:
- fund.py: Core ProtectionFund class with contribute() and process_claim()
- claims.py: Claim submission, review, approval/rejection
- eligibility.py: Worker eligibility checks (verified, 5+ tasks, no fraud, cooldown)
- payouts.py: x402 integration for actual fund disbursement
- reporting.py: Fund stats, claims summary, sustainability forecast
"""

# Core fund
from .fund import (
    # Constants
    FUND_CONTRIBUTION_PERCENT,
    # Exceptions
    FundError,
    InsufficientFundsError,
    ClaimLimitExceededError,
    ClaimNotFoundError,
    InvalidClaimStateError,
    # Enums
    ClaimType,
    ClaimStatus,
    ContributionSource,
    # Data classes
    FundConfig,
    FundContribution,
    FundClaim,
    WorkerClaimHistory,
    # Main class
    ProtectionFund,
    # Singleton
    get_fund,
    reset_fund,
    # Convenience functions
    contribute_fee,
    contribute_slash,
    submit_worker_claim,
    get_fund_balance,
    get_fund_statistics,
)

# Claims management
from .claims import (
    ClaimType as ExtendedClaimType,
    ReviewRule,
    ReviewResult,
    submit_claim,
    review_claim,
    approve_claim,
    reject_claim,
    auto_review_pending_claims,
    get_claims_by_status,
    get_claims_for_worker,
)

# Eligibility
from .eligibility import (
    EligibilityRequirements,
    EligibilityStatus,
    EligibilityResult,
    WorkerProfile,
    check_eligibility,
    is_eligible,
    get_max_claim_amount,
    get_cooldown_status,
    check_fraud_status,
    get_worker_profile,
    register_worker_profile,
    update_worker_tasks,
    verify_worker_identity,
    add_fraud_flag,
    clear_fraud_flags,
    DEFAULT_REQUIREMENTS,
)

# Payouts
from .payouts import (
    PayoutBreakdown,
    PayoutResult,
    calculate_payout,
    execute_payout,
    record_payout,
    process_pending_payouts,
    get_payout_history,
    MAX_SINGLE_PAYOUT,
    MIN_PAYOUT_AMOUNT,
)

# Reporting
from .reporting import (
    ReportPeriod,
    FundStats,
    ClaimsSummary,
    SustainabilityForecast,
    WorkerAnalytics,
    get_fund_stats,
    get_claims_summary,
    forecast_sustainability,
    get_worker_analytics,
    get_top_claimants,
    generate_full_report,
)

__all__ = [
    # Constants
    "FUND_CONTRIBUTION_PERCENT",
    "MAX_SINGLE_PAYOUT",
    "MIN_PAYOUT_AMOUNT",
    # Exceptions
    "FundError",
    "InsufficientFundsError",
    "ClaimLimitExceededError",
    "ClaimNotFoundError",
    "InvalidClaimStateError",
    # Enums
    "ClaimType",
    "ExtendedClaimType",
    "ClaimStatus",
    "ContributionSource",
    "EligibilityStatus",
    "ReportPeriod",
    # Core data classes
    "FundConfig",
    "FundContribution",
    "FundClaim",
    "WorkerClaimHistory",
    "ProtectionFund",
    # Claims data classes
    "ReviewRule",
    "ReviewResult",
    # Eligibility data classes
    "EligibilityRequirements",
    "EligibilityResult",
    "WorkerProfile",
    "DEFAULT_REQUIREMENTS",
    # Payout data classes
    "PayoutBreakdown",
    "PayoutResult",
    # Reporting data classes
    "FundStats",
    "ClaimsSummary",
    "SustainabilityForecast",
    "WorkerAnalytics",
    # Fund functions
    "get_fund",
    "reset_fund",
    "contribute_fee",
    "contribute_slash",
    "submit_worker_claim",
    "get_fund_balance",
    "get_fund_statistics",
    # Claims functions
    "submit_claim",
    "review_claim",
    "approve_claim",
    "reject_claim",
    "auto_review_pending_claims",
    "get_claims_by_status",
    "get_claims_for_worker",
    # Eligibility functions
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
    # Payout functions
    "calculate_payout",
    "execute_payout",
    "record_payout",
    "process_pending_payouts",
    "get_payout_history",
    # Reporting functions
    "get_fund_stats",
    "get_claims_summary",
    "forecast_sustainability",
    "get_worker_analytics",
    "get_top_claimants",
    "generate_full_report",
]
