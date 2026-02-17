"""
Execution Market Payments Module

Active modules:
- fees: Platform fee calculation and collection (FeeManager, calculate_platform_fee)

All payment processing flows through x402 SDK + Facilitator.
See integrations/x402/ for the main payment pipeline.
"""

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

__all__ = [
    # Fees (NOW-025, NOW-026)
    "FeeManager",
    "FEE_RATES",
    "DEFAULT_FEE_RATE",
    "MIN_FEE_AMOUNT",
    "MAX_FEE_PERCENT",
    "FeeType",
    "FeeStatus",
    "FeeBreakdown",
    "CollectedFee",
    "FeeAnalytics",
    "calculate_platform_fee",
    "get_fee_rate_for_category",
    "get_all_fee_rates",
]
