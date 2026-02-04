"""
Execution Market Payments Module

Handles all payment-related functionality including escrow,
partial releases, agent bonds, fees, and worker protection.

Key Components:
- PartialReleaseManager: Handles partial payments on submission (NOW-093)
- AgentBondManager: Manages agent bonds and slashing (NOW-096)
- FeeManager: Platform fee calculation and collection (NOW-025, NOW-026)
- MultiTokenPayments: Multi-token support USDC/EURC/DAI/USDT (NOW-027)
- TokenPreferenceManager: Worker token preferences (NOW-028)
- Proof of attempt payout functionality (NOW-097)
- Minimum payout validation (NOW-098, NOW-099)
"""

from .partial_release import (
    PartialReleaseManager,
    PartialReleaseConfig,
    PartialReleaseRecord,
    PartialReleaseType,
    EscrowSplitState,
    CompletionTier,
    release_partial_on_submission,
    release_on_task_completion,
    calculate_completion_tier,
)

from .agent_bond import (
    # Manager class
    AgentBondManager,
    # Configuration
    BondConfig,
    TaskTypeConfig,
    TASK_TYPE_MINIMUMS,
    # Enums
    TaskType,
    BondStatus,
    # Data classes
    LockedBond,
    BondCalculation,
    ProofOfAttemptResult,
    # Convenience functions
    calculate_total_deposit,
    validate_bounty,
    get_fee_structure,
)

from .fees import (
    # Manager class
    FeeManager,
    # Configuration
    FEE_RATES,
    DEFAULT_FEE_RATE,
    MIN_FEE_AMOUNT,
    MAX_FEE_PERCENT,
    # Enums
    FeeType,
    FeeStatus,
    # Data classes
    FeeBreakdown,
    CollectedFee,
    FeeAnalytics,
    # Convenience functions
    calculate_platform_fee,
    get_fee_rate_for_category,
    get_all_fee_rates,
)

from .multi_token import (
    # Manager class
    MultiTokenPayments,
    get_multi_token_payments,
    # Configuration
    TOKEN_CONFIGS,
    # Enums
    PaymentToken,
    # Data classes
    TokenConfig,
    WorkerTokenPreference,
    PaymentRequest,
)

from .token_preferences import (
    # Manager class
    TokenPreferenceManager,
    get_token_preference_manager,
)

__all__ = [
    # Partial Release
    'PartialReleaseManager',
    'PartialReleaseConfig',
    'PartialReleaseRecord',
    'PartialReleaseType',
    'EscrowSplitState',
    'CompletionTier',
    'release_partial_on_submission',
    'release_on_task_completion',
    'calculate_completion_tier',
    # Agent Bond
    'AgentBondManager',
    'BondConfig',
    'TaskTypeConfig',
    'TASK_TYPE_MINIMUMS',
    'TaskType',
    'BondStatus',
    'LockedBond',
    'BondCalculation',
    'ProofOfAttemptResult',
    'calculate_total_deposit',
    'validate_bounty',
    'get_fee_structure',
    # Fees (NOW-025, NOW-026)
    'FeeManager',
    'FEE_RATES',
    'DEFAULT_FEE_RATE',
    'MIN_FEE_AMOUNT',
    'MAX_FEE_PERCENT',
    'FeeType',
    'FeeStatus',
    'FeeBreakdown',
    'CollectedFee',
    'FeeAnalytics',
    'calculate_platform_fee',
    'get_fee_rate_for_category',
    'get_all_fee_rates',
    # Multi-Token (NOW-027)
    'MultiTokenPayments',
    'get_multi_token_payments',
    'TOKEN_CONFIGS',
    'PaymentToken',
    'TokenConfig',
    'WorkerTokenPreference',
    'PaymentRequest',
    # Token Preferences (NOW-028)
    'TokenPreferenceManager',
    'get_token_preference_manager',
]
