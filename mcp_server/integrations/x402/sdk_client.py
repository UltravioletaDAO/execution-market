"""
x402 SDK Integration for Execution Market (NOW-202)

Uses the official uvd-x402-sdk for payment processing with the Ultravioleta DAO facilitator.
This module replaces the custom client implementation with the standardized SDK.

The SDK provides:
- Gasless EIP-3009 payments
- Automatic facilitator integration
- FastAPI native support
- Multi-network support (18+ chains)

Facilitator: https://facilitator.ultravioletadao.xyz
"""

import os
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response, Depends
from pydantic import BaseModel

# Import from uvd-x402-sdk
try:
    from uvd_x402_sdk import (
        X402Client as SDKClient,
        X402Config,
        PaymentResult as SDKPaymentResult,
    )
    from uvd_x402_sdk.integrations import FastAPIX402
    from uvd_x402_sdk.exceptions import (
        X402Error as SDKError,
        PaymentRequiredError,
        PaymentVerificationError,
        PaymentSettlementError,
    )
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    # Provide stubs for type hints
    SDKClient = None
    X402Config = None
    SDKPaymentResult = None
    FastAPIX402 = None
    SDKError = Exception
    PaymentRequiredError = Exception
    PaymentVerificationError = Exception
    PaymentSettlementError = Exception


logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Default facilitator URL (Ultravioleta DAO production)
FACILITATOR_URL = os.environ.get(
    "X402_FACILITATOR_URL",
    "https://facilitator.ultravioletadao.xyz"
)

# Execution Market treasury address for fee collection
EM_TREASURY = os.environ.get(
    "EM_TREASURY_ADDRESS",
    os.environ.get("EM_TREASURY_ADDRESS",
    "0x0000000000000000000000000000000000000000")
)

# Default network for payments
DEFAULT_NETWORK = os.environ.get("X402_NETWORK", "base")

# Platform fee percentage
PLATFORM_FEE_PERCENT = Decimal(os.environ.get("EM_PLATFORM_FEE", "0.08"))


# =============================================================================
# Payment Models
# =============================================================================

class EMPaymentConfig(BaseModel):
    """Configuration for Execution Market payment endpoints."""
    recipient_address: str
    description: str = "Execution Market task payment"
    network: str = DEFAULT_NETWORK
    resource: Optional[str] = None


class TaskPaymentResult(BaseModel):
    """Result of a task payment verification."""
    success: bool
    payer_address: str
    amount_usd: Decimal
    tx_hash: Optional[str] = None
    network: str
    timestamp: datetime
    task_id: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# SDK Wrapper Class
# =============================================================================

class EMX402SDK:
    """
    Wrapper around uvd-x402-sdk for Execution Market-specific functionality.

    Provides:
    - FastAPI integration for payment-gated endpoints
    - Task-specific payment processing
    - Fee calculation and collection
    - Multi-network support
    """

    def __init__(
        self,
        app: Optional[FastAPI] = None,
        recipient_address: Optional[str] = None,
        facilitator_url: Optional[str] = None,
        network: str = DEFAULT_NETWORK,
    ):
        """
        Initialize Execution Market x402 SDK wrapper.

        Args:
            app: FastAPI application (for automatic integration)
            recipient_address: Default recipient for payments (treasury)
            facilitator_url: Facilitator URL (default: Ultravioleta DAO)
            network: Default network for payments
        """
        if not SDK_AVAILABLE:
            raise ImportError(
                "uvd-x402-sdk not installed. "
                "Install with: pip install uvd-x402-sdk[fastapi]"
            )

        self.recipient_address = recipient_address or EM_TREASURY
        self.facilitator_url = facilitator_url or FACILITATOR_URL
        self.network = network

        # Create SDK config
        self.config = X402Config(
            recipient_evm=self.recipient_address,
            facilitator_url=self.facilitator_url,
            supported_networks=[network],
        )

        # Create SDK client
        self.client = SDKClient(config=self.config)

        # FastAPI integration (if app provided)
        self.fastapi_x402: Optional[FastAPIX402] = None
        if app:
            self._setup_fastapi(app)

        logger.info(
            "EMX402SDK initialized: facilitator=%s, network=%s",
            self.facilitator_url,
            self.network
        )

    def _setup_fastapi(self, app: FastAPI) -> None:
        """Setup FastAPI integration with x402."""
        self.fastapi_x402 = FastAPIX402(
            app,
            recipient_address=self.recipient_address,
            facilitator_url=self.facilitator_url,
        )
        logger.info("FastAPI x402 integration enabled")

    # =========================================================================
    # Payment Dependencies
    # =========================================================================

    def require_payment(
        self,
        amount_usd: str,
        description: Optional[str] = None,
        network: Optional[str] = None,
    ) -> Callable:
        """
        FastAPI dependency that requires payment for endpoint access.

        Usage:
            @app.get("/api/premium")
            async def premium(
                payment: PaymentResult = Depends(x402.require_payment(amount_usd="5.00"))
            ):
                return {"payer": payment.payer_address}

        Args:
            amount_usd: Payment amount in USD (string for precision)
            description: Payment description
            network: Network for payment (default: configured network)

        Returns:
            FastAPI dependency function
        """
        if not self.fastapi_x402:
            raise RuntimeError("FastAPI integration not configured")

        return self.fastapi_x402.require_payment(
            amount_usd=amount_usd,
            description=description or "Execution Market payment",
            network=network or self.network,
        )

    def optional_payment(
        self,
        amount_usd: str,
        description: Optional[str] = None,
    ) -> Callable:
        """
        FastAPI dependency for optional payments.

        Returns payment result if provided, None otherwise.
        """
        if not self.fastapi_x402:
            raise RuntimeError("FastAPI integration not configured")

        return self.fastapi_x402.optional_payment(
            amount_usd=amount_usd,
            description=description or "Execution Market optional payment",
        )

    # =========================================================================
    # Task Payment Processing
    # =========================================================================

    async def verify_task_payment(
        self,
        task_id: str,
        payment_header: str,
        expected_amount: Decimal,
        worker_address: str,
    ) -> TaskPaymentResult:
        """
        Verify a payment for task completion.

        Args:
            task_id: Task identifier
            payment_header: x402 payment header from request
            expected_amount: Expected payment amount
            worker_address: Worker's wallet address (recipient)

        Returns:
            TaskPaymentResult with verification details
        """
        try:
            # Extract and validate payment payload from X-Payment header
            payload = self.client.extract_payload(payment_header)

            # Get payer address from the payload
            payer_address, payer_network = self.client.get_payer_address(payment_header)

            # Verify with facilitator (validates signature on-chain without settling)
            verify_response = self.client.verify_payment(payload, expected_amount)

            if not verify_response.isValid:
                return TaskPaymentResult(
                    success=False,
                    payer_address=verify_response.payer or payer_address or "unknown",
                    amount_usd=expected_amount,
                    network=payload.network,
                    timestamp=datetime.now(timezone.utc),
                    task_id=task_id,
                    error=verify_response.invalidReason or verify_response.message or "Payment verification failed",
                )

            return TaskPaymentResult(
                success=True,
                payer_address=verify_response.payer or payer_address,
                amount_usd=expected_amount,
                tx_hash=None,  # No tx_hash until settlement
                network=payload.network,
                timestamp=datetime.now(timezone.utc),
                task_id=task_id,
            )

        except Exception as e:
            logger.error("Task payment verification failed: %s", str(e))
            return TaskPaymentResult(
                success=False,
                payer_address="unknown",
                amount_usd=Decimal("0"),
                network=self.network,
                timestamp=datetime.now(timezone.utc),
                task_id=task_id,
                error=str(e),
            )

    async def settle_task_payment(
        self,
        task_id: str,
        payment_header: str,
        worker_address: str,
        bounty_amount: Decimal,
    ) -> Dict[str, Any]:
        """
        Settle a task payment (release to worker).

        Calculates platform fee and distributes:
        - 92% to worker (net after 8% fee)
        - 8% to Execution Market treasury

        Args:
            task_id: Task identifier
            payment_header: x402 payment header
            worker_address: Worker's wallet address
            bounty_amount: Full bounty amount

        Returns:
            Dict with settlement details
        """
        try:
            # Calculate fee breakdown
            platform_fee = (bounty_amount * PLATFORM_FEE_PERCENT).quantize(Decimal("0.01"))
            worker_net = bounty_amount - platform_fee

            # Extract payload from header
            payload = self.client.extract_payload(payment_header)

            # Settle via facilitator (on-chain transfer)
            settle_response = self.client.settle_payment(payload, bounty_amount)

            return {
                "success": settle_response.success,
                "task_id": task_id,
                "worker_address": worker_address,
                "gross_amount": float(bounty_amount),
                "platform_fee": float(platform_fee),
                "net_to_worker": float(worker_net),
                "tx_hash": settle_response.get_transaction_hash(),
                "network": payload.network,
                "payer": settle_response.payer,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error("Task payment settlement failed: %s", str(e))
            return {
                "success": False,
                "task_id": task_id,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def refund_task_payment(
        self,
        task_id: str,
        escrow_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refund a task payment back to the agent.

        This uses the x402r escrow integration when available.
        The operation is best-effort and returns a structured result.

        Args:
            task_id: Task identifier
            escrow_id: Escrow/deposit identifier
            reason: Optional refund reason for logs/audit

        Returns:
            Dict with refund details
        """
        if not escrow_id:
            return {
                "success": False,
                "task_id": task_id,
                "escrow_id": escrow_id,
                "error": "Missing escrow_id",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        try:
            from .x402r_escrow import refund_payment
        except Exception:
            return {
                "success": False,
                "task_id": task_id,
                "escrow_id": escrow_id,
                "error": "x402r refund integration not available",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        try:
            refund_result = await refund_payment(deposit_id=escrow_id)
            amount = getattr(refund_result, "amount", None)
            return {
                "success": bool(getattr(refund_result, "success", False)),
                "task_id": task_id,
                "escrow_id": escrow_id,
                "tx_hash": getattr(refund_result, "tx_hash", None),
                "payer": getattr(refund_result, "payer", None),
                "amount": str(amount) if amount is not None else None,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error("Task payment refund failed: %s", str(e))
            return {
                "success": False,
                "task_id": task_id,
                "escrow_id": escrow_id,
                "error": str(e),
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> Dict[str, Any]:
        """
        Check x402 SDK and facilitator health.

        Returns:
            Dict with health status
        """
        try:
            import httpx
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(
                    f"{self.facilitator_url}/health",
                    timeout=10.0,
                )
                facilitator_health = response.json() if response.status_code == 200 else {}

            return {
                "sdk_available": True,
                "facilitator_url": self.facilitator_url,
                "facilitator_healthy": response.status_code == 200,
                "facilitator_status": facilitator_health.get("status", "unknown"),
                "network": self.network,
                "recipient": self.recipient_address,
            }
        except Exception as e:
            return {
                "sdk_available": True,
                "facilitator_url": self.facilitator_url,
                "facilitator_healthy": False,
                "error": str(e),
                "network": self.network,
            }


# =============================================================================
# Module-Level Functions
# =============================================================================

_default_sdk: Optional[EMX402SDK] = None


def get_sdk() -> EMX402SDK:
    """Get or create the default EMX402SDK instance."""
    global _default_sdk
    if _default_sdk is None:
        _default_sdk = EMX402SDK()
    return _default_sdk


def setup_x402_for_app(
    app: FastAPI,
    recipient_address: Optional[str] = None,
    network: str = DEFAULT_NETWORK,
) -> EMX402SDK:
    """
    Setup x402 integration for a FastAPI app.

    Usage:
        from integrations.x402.sdk_client import setup_x402_for_app

        app = FastAPI()
        x402 = setup_x402_for_app(app, recipient_address="0x...")

        @app.get("/paid")
        async def paid_endpoint(payment = Depends(x402.require_payment("1.00"))):
            return {"paid_by": payment.payer_address}

    Args:
        app: FastAPI application
        recipient_address: Payment recipient address
        network: Default network

    Returns:
        Configured EMX402SDK instance
    """
    global _default_sdk
    _default_sdk = EMX402SDK(
        app=app,
        recipient_address=recipient_address,
        network=network,
    )
    return _default_sdk


async def verify_x402_payment(
    request: Request,
    expected_amount: Decimal,
) -> TaskPaymentResult:
    """
    Verify x402 payment from request headers.

    Args:
        request: FastAPI request object
        expected_amount: Expected payment amount

    Returns:
        TaskPaymentResult
    """
    sdk = get_sdk()

    # Get x402 payment header
    payment_header = request.headers.get("X-Payment") or request.headers.get("x-payment")

    if not payment_header:
        return TaskPaymentResult(
            success=False,
            payer_address="none",
            amount_usd=Decimal("0"),
            network=sdk.network,
            timestamp=datetime.now(timezone.utc),
            error="No X-Payment header provided",
        )

    return await sdk.verify_task_payment(
        task_id="direct",
        payment_header=payment_header,
        expected_amount=expected_amount,
        worker_address=sdk.recipient_address,
    )


# =============================================================================
# Check SDK Availability
# =============================================================================

def check_sdk_available() -> bool:
    """Check if uvd-x402-sdk is available."""
    return SDK_AVAILABLE


def get_sdk_info() -> Dict[str, Any]:
    """Get information about SDK installation."""
    if not SDK_AVAILABLE:
        return {
            "available": False,
            "error": "uvd-x402-sdk not installed",
            "install": "pip install uvd-x402-sdk[fastapi]",
        }

    try:
        import uvd_x402_sdk
        return {
            "available": True,
            "version": getattr(uvd_x402_sdk, "__version__", "unknown"),
            "facilitator_url": FACILITATOR_URL,
        }
    except Exception as e:
        return {
            "available": True,
            "error": str(e),
        }
