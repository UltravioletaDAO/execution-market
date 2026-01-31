"""
x402 Integration for Chamba (NOW-019 to NOW-024)

Provides payment processing via the x402 protocol with multi-token support.

Merchant Setup (NOW-019, NOW-020):
1. Register Chamba as merchant on MerchantRouter
2. Deploy relay proxy via DepositRelayFactory
3. Use relay for escrow deposits

Escrow Lifecycle (NOW-021 to NOW-024):
1. publish_task -> create_escrow_for_task (deposit funds)
2. submission -> release_partial_on_submission (optional 30% proof-of-work)
3. approve_submission -> release_on_approval (remaining to worker + fees)
4. cancel_task -> refund_on_cancel (full refund to agent)
5. dispute -> handle_dispute (lock pending resolution)

Multi-Token Support (NOW-024):
- USDC, EURC, DAI, USDT
- Multi-network: Base, Polygon, Optimism, Arbitrum
"""

from .client import (
    # Main client
    X402Client,
    # Enums (client module)
    PaymentToken as ClientPaymentToken,
    EscrowStatus as ClientEscrowStatus,
    # Exceptions
    X402Error,
    EscrowCreationError,
    EscrowReleaseError,
    EscrowRefundError,
    FacilitatorError,
    InsufficientFundsError,
    # Data classes (client module)
    PaymentResult as ClientPaymentResult,
    EscrowDeposit,
    EscrowInfo,
    # Constants
    DEFAULT_FACILITATOR_URL,
    TOKEN_ADDRESSES,
    TOKEN_DECIMALS,
    CHAIN_IDS,
    MERCHANT_ROUTER,
    DEPOSIT_RELAY_FACTORY,
    # Convenience functions (client module)
    create_chamba_escrow,
    release_task_payment,
    refund_task_escrow,
)

from .escrow import (
    # Manager class
    EscrowManager,
    # Enums (escrow module)
    EscrowStatus,
    PaymentToken,
    # Exceptions
    EscrowStateError,
    # Data classes (escrow module)
    TaskEscrow,
    FeeBreakdown,
    ReleaseRecord,
    # Convenience functions (escrow module)
    get_manager,
    create_escrow_for_task,
    release_partial_on_submission,
    release_on_approval,
    refund_on_cancel,
    # Constants
    PLATFORM_FEE_PERCENT,
    MINIMUM_PAYOUT,
    PARTIAL_RELEASE_PERCENT,
)

from .merchant import (
    # Merchant registration (NOW-019, NOW-020)
    X402Merchant,
    MerchantConfig,
    setup_chamba_merchant,
    # Contract addresses (merchant module)
    MERCHANT_ROUTER as MERCHANT_ROUTER_ADDRESS,
    DEPOSIT_RELAY_FACTORY as RELAY_FACTORY_ADDRESS,
    USDC_BASE,
)

# SDK Integration (NOW-202) - uses official uvd-x402-sdk
from .sdk_client import (
    # Main SDK wrapper
    ChambaX402SDK,
    # Configuration
    ChambaPaymentConfig,
    TaskPaymentResult,
    FACILITATOR_URL,
    CHAMBA_TREASURY,
    # Setup functions
    get_sdk,
    setup_x402_for_app,
    verify_x402_payment,
    check_sdk_available,
    get_sdk_info,
)

# x402r Escrow Integration (PRODUCTION) - direct contract interaction
# This is the production-ready implementation using the proven x402r system
from .x402r_escrow import (
    # Main client
    X402rEscrow,
    # Types
    DepositState,
    DepositInfo,
    ReleaseResult,
    RefundResult,
    # Convenience functions
    get_x402r_escrow,
    release_payment,
    refund_payment,
    get_deposit_info,
    # Contract addresses
    CONTRACTS as X402R_CONTRACTS,
)

__all__ = [
    # Main client
    "X402Client",
    # Client enums (renamed to avoid conflicts)
    "ClientPaymentToken",
    "ClientEscrowStatus",
    # Escrow manager enums (primary)
    "PaymentToken",
    "EscrowStatus",
    # All exceptions
    "X402Error",
    "EscrowCreationError",
    "EscrowReleaseError",
    "EscrowRefundError",
    "FacilitatorError",
    "InsufficientFundsError",
    "EscrowStateError",
    # Client data classes
    "ClientPaymentResult",
    "EscrowDeposit",
    "EscrowInfo",
    # Escrow manager data classes
    "EscrowManager",
    "TaskEscrow",
    "FeeBreakdown",
    "ReleaseRecord",
    # Merchant registration (NOW-019, NOW-020)
    "X402Merchant",
    "MerchantConfig",
    "setup_chamba_merchant",
    # Constants (client)
    "DEFAULT_FACILITATOR_URL",
    "TOKEN_ADDRESSES",
    "TOKEN_DECIMALS",
    "CHAIN_IDS",
    "MERCHANT_ROUTER",
    "DEPOSIT_RELAY_FACTORY",
    # Constants (merchant)
    "MERCHANT_ROUTER_ADDRESS",
    "RELAY_FACTORY_ADDRESS",
    "USDC_BASE",
    # Constants (escrow)
    "PLATFORM_FEE_PERCENT",
    "MINIMUM_PAYOUT",
    "PARTIAL_RELEASE_PERCENT",
    # Convenience functions (client)
    "create_chamba_escrow",
    "release_task_payment",
    "refund_task_escrow",
    # Convenience functions (escrow manager)
    "get_manager",
    "create_escrow_for_task",
    "release_partial_on_submission",
    "release_on_approval",
    "refund_on_cancel",
    # SDK Integration (NOW-202)
    "ChambaX402SDK",
    "ChambaPaymentConfig",
    "TaskPaymentResult",
    "FACILITATOR_URL",
    "CHAMBA_TREASURY",
    "get_sdk",
    "setup_x402_for_app",
    "verify_x402_payment",
    "check_sdk_available",
    "get_sdk_info",
    # x402r Escrow (PRODUCTION)
    "X402rEscrow",
    "DepositState",
    "DepositInfo",
    "ReleaseResult",
    "RefundResult",
    "get_x402r_escrow",
    "release_payment",
    "refund_payment",
    "get_deposit_info",
    "X402R_CONTRACTS",
]
