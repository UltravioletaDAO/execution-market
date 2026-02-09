"""
Payment Dispatcher for Execution Market.

Routes payment operations to x402r escrow or EIP-3009 pre-auth based on EM_PAYMENT_MODE.

Two payment backends:
  - x402r: Locks funds on-chain via AuthCaptureEscrow contract (authorize/release/refund)
  - preauth: EIP-3009 pre-authorization, funds stay in agent wallet until settlement

Both backends go through the Ultravioleta Facilitator and are GASLESS for agents and workers.
"""

import os
import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Configuration
EM_PAYMENT_MODE = os.environ.get("EM_PAYMENT_MODE", "x402r")  # "x402r" or "preauth"

# --- x402r backend (advanced escrow) ---
try:
    from mcp_server.integrations.x402.advanced_escrow_integration import (
        EMAdvancedEscrow,
        PaymentStrategy,
        get_advanced_escrow,
        ADVANCED_ESCROW_AVAILABLE,
    )
except ImportError:
    ADVANCED_ESCROW_AVAILABLE = False
    EMAdvancedEscrow = None  # type: ignore[assignment,misc]
    PaymentStrategy = None  # type: ignore[assignment,misc]
    get_advanced_escrow = None  # type: ignore[assignment]

# --- preauth backend (EIP-3009 SDK) ---
try:
    from mcp_server.integrations.x402.sdk_client import (
        EMX402SDK,
        get_sdk,
        verify_x402_payment,
        SDK_AVAILABLE,
    )
except ImportError:
    SDK_AVAILABLE = False
    EMX402SDK = None  # type: ignore[assignment,misc]
    get_sdk = None  # type: ignore[assignment]
    verify_x402_payment = None  # type: ignore[assignment]


class PaymentDispatcher:
    """
    Routes payment operations to the correct backend based on EM_PAYMENT_MODE.

    Provides a uniform interface for authorize, release, and refund regardless
    of whether x402r (on-chain escrow) or preauth (EIP-3009 signature) is used.
    """

    def __init__(self, mode: Optional[str] = None):
        self.mode = (mode or EM_PAYMENT_MODE).lower()

        if self.mode not in ("x402r", "preauth"):
            logger.warning(
                "Unknown EM_PAYMENT_MODE '%s', falling back to 'preauth'",
                self.mode,
            )
            self.mode = "preauth"

        # Validate availability and fall back if needed
        if self.mode == "x402r" and not ADVANCED_ESCROW_AVAILABLE:
            logger.warning(
                "x402r mode requested but advanced escrow SDK not available. "
                "Falling back to preauth mode."
            )
            self.mode = "preauth"

        if self.mode == "preauth" and not SDK_AVAILABLE:
            logger.error(
                "preauth mode requested but uvd-x402-sdk not available. "
                "Payment operations will fail."
            )

        # Lazy-initialized backend instances
        self._escrow: Optional[Any] = None
        self._sdk: Optional[Any] = None

        logger.info("PaymentDispatcher initialized: mode=%s", self.mode)

    def _get_escrow(self) -> "EMAdvancedEscrow":
        """Lazy-init the x402r escrow backend."""
        if self._escrow is None:
            self._escrow = get_advanced_escrow()
        return self._escrow

    def _get_sdk(self) -> "EMX402SDK":
        """Lazy-init the preauth SDK backend."""
        if self._sdk is None:
            self._sdk = get_sdk()
        return self._sdk

    # =========================================================================
    # authorize_payment
    # =========================================================================

    async def authorize_payment(
        self,
        task_id: str,
        receiver: str,
        amount_usdc: Decimal,
        strategy: Optional[Any] = None,
        x_payment_header: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Authorize (lock or verify) a payment for a task.

        x402r mode: Locks funds on-chain via EMAdvancedEscrow.authorize_task().
        preauth mode: Verifies EIP-3009 signature via verify_x402_payment().

        Args:
            task_id: Unique task identifier
            receiver: Worker wallet address
            amount_usdc: Bounty amount in USDC
            strategy: PaymentStrategy for x402r mode (optional)
            x_payment_header: X-Payment header for preauth mode (required in preauth)

        Returns:
            Uniform dict with success, tx_hash, mode, escrow_status, payment_info, error.
        """
        try:
            if self.mode == "x402r":
                return await self._authorize_x402r(
                    task_id, receiver, amount_usdc, strategy
                )
            else:
                return await self._authorize_preauth(
                    task_id, amount_usdc, x_payment_header
                )
        except Exception as e:
            logger.error(
                "authorize_payment failed: task=%s, mode=%s, error=%s",
                task_id,
                self.mode,
                e,
            )
            return {
                "success": False,
                "tx_hash": None,
                "mode": self.mode,
                "escrow_status": "error",
                "payment_info": None,
                "error": str(e),
            }

    async def _authorize_x402r(
        self,
        task_id: str,
        receiver: str,
        amount_usdc: Decimal,
        strategy: Optional[Any],
    ) -> Dict[str, Any]:
        """Authorize via x402r escrow -- locks funds on-chain."""
        escrow = self._get_escrow()
        strat = strategy or PaymentStrategy.ESCROW_CAPTURE

        # EMAdvancedEscrow.authorize_task is synchronous (HTTP under the hood)
        payment = escrow.authorize_task(task_id, receiver, amount_usdc, strat)

        tx_hash = payment.tx_hashes[0] if payment.tx_hashes else None
        return {
            "success": payment.status == "authorized",
            "tx_hash": tx_hash,
            "mode": "x402r",
            "escrow_status": payment.status,
            "payment_info": payment,
            "error": None
            if payment.status == "authorized"
            else f"Status: {payment.status}",
        }

    async def _authorize_preauth(
        self,
        task_id: str,
        amount_usdc: Decimal,
        x_payment_header: Optional[str],
    ) -> Dict[str, Any]:
        """Authorize via preauth -- verifies EIP-3009 signature, no funds move."""
        if not x_payment_header:
            return {
                "success": False,
                "tx_hash": None,
                "mode": "preauth",
                "escrow_status": "missing_header",
                "payment_info": None,
                "error": "X-Payment header required for preauth mode",
            }

        sdk = self._get_sdk()
        result = await sdk.verify_task_payment(
            task_id=task_id,
            payment_header=x_payment_header,
            expected_amount=amount_usdc,
            worker_address=sdk.recipient_address,
        )

        return {
            "success": result.success,
            "tx_hash": result.tx_hash,
            "mode": "preauth",
            "escrow_status": "verified" if result.success else "verification_failed",
            "payment_info": result,
            "error": result.error,
        }

    # =========================================================================
    # release_payment
    # =========================================================================

    async def release_payment(
        self,
        task_id: str,
        worker_address: str,
        bounty_amount: Decimal,
        payment_header: Optional[str] = None,
        network: Optional[str] = None,
        token: str = "USDC",
    ) -> Dict[str, Any]:
        """
        Release payment to a worker after task approval.

        x402r mode: Releases from on-chain escrow via EMAdvancedEscrow.release_to_worker().
        preauth mode: Settles EIP-3009 auth via EMX402SDK.settle_task_payment().

        Args:
            task_id: Task identifier
            worker_address: Worker wallet address
            bounty_amount: Total bounty amount in USDC
            payment_header: Original X-Payment header (required for preauth)
            network: Payment network (optional, defaults to SDK default)
            token: Payment token (default: USDC)

        Returns:
            Uniform dict with success, tx_hash, mode, error.
        """
        try:
            if self.mode == "x402r":
                return await self._release_x402r(task_id, bounty_amount)
            else:
                return await self._release_preauth(
                    task_id,
                    worker_address,
                    bounty_amount,
                    payment_header,
                    network,
                    token,
                )
        except Exception as e:
            logger.error(
                "release_payment failed: task=%s, mode=%s, error=%s",
                task_id,
                self.mode,
                e,
            )
            return {
                "success": False,
                "tx_hash": None,
                "mode": self.mode,
                "error": str(e),
            }

    async def _release_x402r(
        self,
        task_id: str,
        amount_usdc: Decimal,
    ) -> Dict[str, Any]:
        """Release from on-chain escrow to worker."""
        escrow = self._get_escrow()

        # EMAdvancedEscrow.release_to_worker is synchronous
        result = escrow.release_to_worker(task_id, amount_usdc)

        tx_hash = (
            result.transaction_hash if hasattr(result, "transaction_hash") else None
        )
        error = result.error if hasattr(result, "error") else None
        success = result.success if hasattr(result, "success") else bool(tx_hash)

        return {
            "success": success,
            "tx_hash": tx_hash,
            "mode": "x402r",
            "error": error if not success else None,
        }

    async def _release_preauth(
        self,
        task_id: str,
        worker_address: str,
        bounty_amount: Decimal,
        payment_header: Optional[str],
        network: Optional[str],
        token: str,
    ) -> Dict[str, Any]:
        """Settle EIP-3009 auth: collect from agent, disburse to worker + fee."""
        if not payment_header:
            return {
                "success": False,
                "tx_hash": None,
                "mode": "preauth",
                "error": "X-Payment header required for preauth settlement",
            }

        sdk = self._get_sdk()
        result = await sdk.settle_task_payment(
            task_id=task_id,
            payment_header=payment_header,
            worker_address=worker_address,
            bounty_amount=bounty_amount,
            network=network,
            token=token,
        )

        return {
            "success": result.get("success", False),
            "tx_hash": result.get("tx_hash"),
            "mode": "preauth",
            "error": result.get("error"),
        }

    # =========================================================================
    # refund_payment
    # =========================================================================

    async def refund_payment(
        self,
        task_id: str,
        escrow_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refund a task payment.

        x402r mode: Refunds from on-chain escrow via EMAdvancedEscrow.refund_to_agent().
        preauth mode: Auth expires naturally, returns success immediately.

        Args:
            task_id: Task identifier
            escrow_id: Escrow identifier (used by preauth SDK refund if available)
            reason: Reason for refund (for audit trail)

        Returns:
            Uniform dict with success, tx_hash, mode, status, error.
        """
        try:
            if self.mode == "x402r":
                return await self._refund_x402r(task_id)
            else:
                return await self._refund_preauth(task_id, escrow_id, reason)
        except Exception as e:
            logger.error(
                "refund_payment failed: task=%s, mode=%s, error=%s",
                task_id,
                self.mode,
                e,
            )
            return {
                "success": False,
                "tx_hash": None,
                "mode": self.mode,
                "status": "error",
                "error": str(e),
            }

    async def _refund_x402r(self, task_id: str) -> Dict[str, Any]:
        """Refund from on-chain escrow back to agent."""
        escrow = self._get_escrow()

        # EMAdvancedEscrow.refund_to_agent is synchronous
        result = escrow.refund_to_agent(task_id)

        tx_hash = (
            result.transaction_hash if hasattr(result, "transaction_hash") else None
        )
        error = result.error if hasattr(result, "error") else None
        success = result.success if hasattr(result, "success") else bool(tx_hash)

        return {
            "success": success,
            "tx_hash": tx_hash,
            "mode": "x402r",
            "status": "refunded" if success else "refund_failed",
            "error": error if not success else None,
        }

    async def _refund_preauth(
        self,
        task_id: str,
        escrow_id: Optional[str],
        reason: Optional[str],
    ) -> Dict[str, Any]:
        """Preauth refund: auth expires naturally, no on-chain action needed."""
        # If there is an escrow_id, try the SDK's refund path
        if escrow_id:
            sdk = self._get_sdk()
            result = await sdk.refund_task_payment(
                task_id=task_id,
                escrow_id=escrow_id,
                reason=reason,
            )
            return {
                "success": result.get("success", False),
                "tx_hash": result.get("tx_hash"),
                "mode": "preauth",
                "status": result.get("status", "refund_attempted"),
                "error": result.get("error"),
            }

        # No escrow_id means pure preauth -- auth simply expires
        logger.info(
            "Preauth refund for task %s: no escrow_id, auth expires naturally",
            task_id,
        )
        return {
            "success": True,
            "tx_hash": None,
            "mode": "preauth",
            "status": "auth_expired",
            "error": None,
        }

    # =========================================================================
    # Info / Config
    # =========================================================================

    def get_mode(self) -> str:
        """Return the current payment mode."""
        return self.mode

    def get_info(self) -> Dict[str, Any]:
        """Return dispatcher configuration and backend availability."""
        info: Dict[str, Any] = {
            "mode": self.mode,
            "x402r_available": ADVANCED_ESCROW_AVAILABLE,
            "preauth_available": SDK_AVAILABLE,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self.mode == "x402r" and self._escrow is not None:
            try:
                info["x402r_config"] = self._escrow.get_config()
            except Exception:
                pass

        if self.mode == "preauth" and self._sdk is not None:
            info["preauth_config"] = {
                "facilitator_url": self._sdk.facilitator_url,
                "network": self._sdk.network,
                "recipient": self._sdk.recipient_address,
            }

        return info


# =============================================================================
# Singleton
# =============================================================================

_dispatcher: Optional[PaymentDispatcher] = None


def get_dispatcher() -> PaymentDispatcher:
    """Get or create the default PaymentDispatcher singleton."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = PaymentDispatcher()
    return _dispatcher
