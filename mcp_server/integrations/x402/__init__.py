"""
x402 Integration for Execution Market

Provides payment processing via the x402 protocol with multi-token support.
Uses the official uvd-x402-sdk for all payment operations via the Facilitator.

Active modules:
- sdk_client: EMX402SDK wrapper + multichain token registry (single source of truth)
- payment_dispatcher: PaymentDispatcher (fase1 testing / fase2 production)
- payment_events: Payment audit trail logging
- advanced_escrow_integration: PaymentOperator via SDK (Fase 5 trustless)
"""

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

# Payment Dispatcher (fase1 testing / fase2 production)
try:
    from .payment_dispatcher import (
        PaymentDispatcher,
        get_dispatcher as get_payment_dispatcher,
        EM_PAYMENT_MODE,
    )
except ImportError:
    EM_PAYMENT_MODE = "fase2"

__all__ = [
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
    # Payment Dispatcher
    "PaymentDispatcher",
    "get_payment_dispatcher",
    "EM_PAYMENT_MODE",
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
