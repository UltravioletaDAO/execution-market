"""
x402 Integration for Execution Market (NOW-019 to NOW-024)

Provides payment processing via the x402 protocol with multi-token support.

Merchant Setup (NOW-019, NOW-020):
1. Register Execution Market as merchant on MerchantRouter
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
    create_em_escrow,
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
    setup_em_merchant,
    # Contract addresses (merchant module)
    MERCHANT_ROUTER as MERCHANT_ROUTER_ADDRESS,
    DEPOSIT_RELAY_FACTORY as RELAY_FACTORY_ADDRESS,
    USDC_BASE,
)

# SDK Integration (NOW-202) - uses official uvd-x402-sdk
from .sdk_client import (
    # Main SDK wrapper
    EMX402SDK,
    # Configuration
    EMPaymentConfig,
    TaskPaymentResult,
    FACILITATOR_URL,
    EM_TREASURY,
    # Setup functions
    get_sdk,
    setup_x402_for_app,
    verify_x402_payment,
    check_sdk_available,
    get_sdk_info,
)

# Advanced Escrow Integration (PaymentOperator via uvd-x402-sdk)
# Uses the SDK as abstraction layer: EM -> SDK -> Facilitator -> On-chain
try:
    from .advanced_escrow_integration import (
        # Main client
        EMAdvancedEscrow,
        # Types
        PaymentStrategy,
        TaskPayment,
        # Convenience functions
        get_advanced_escrow,
        authorize_task_bounty,
        release_to_worker as advanced_release_to_worker,
        refund_to_agent as advanced_refund_to_agent,
        charge_trusted_worker,
        partial_release,
        # Constants
        ADVANCED_ESCROW_AVAILABLE,
    )
except ImportError:
    ADVANCED_ESCROW_AVAILABLE = False

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
    "setup_em_merchant",
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
    "create_em_escrow",
    "release_task_payment",
    "refund_task_escrow",
    # Convenience functions (escrow manager)
    "get_manager",
    "create_escrow_for_task",
    "release_partial_on_submission",
    "release_on_approval",
    "refund_on_cancel",
    # SDK Integration (NOW-202)
    "EMX402SDK",
    "EMPaymentConfig",
    "TaskPaymentResult",
    "FACILITATOR_URL",
    "EM_TREASURY",
    "get_sdk",
    "setup_x402_for_app",
    "verify_x402_payment",
    "check_sdk_available",
    "get_sdk_info",
    # Advanced Escrow (PaymentOperator via SDK)
    "ADVANCED_ESCROW_AVAILABLE",
]

# Conditionally add Advanced Escrow names only if SDK is available
if ADVANCED_ESCROW_AVAILABLE:
    __all__ += [
        "EMAdvancedEscrow",
        "PaymentStrategy",
        "TaskPayment",
        "get_advanced_escrow",
        "authorize_task_bounty",
        "advanced_release_to_worker",
        "advanced_refund_to_agent",
        "charge_trusted_worker",
        "partial_release",
    ]
