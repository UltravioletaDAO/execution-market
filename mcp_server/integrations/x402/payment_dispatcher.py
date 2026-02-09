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
    from integrations.x402.advanced_escrow_integration import (
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
    from integrations.x402.sdk_client import (
        EMX402SDK,
        get_sdk,
        verify_x402_payment,
        SDK_AVAILABLE,
        PLATFORM_FEE_PERCENT,
        EM_TREASURY,
    )
except ImportError:
    SDK_AVAILABLE = False
    EMX402SDK = None  # type: ignore[assignment,misc]
    get_sdk = None  # type: ignore[assignment]
    verify_x402_payment = None  # type: ignore[assignment]
    PLATFORM_FEE_PERCENT = Decimal("0.08")
    EM_TREASURY = "YOUR_TREASURY_WALLET"


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
                    task_id, receiver, amount_usdc, strategy, x_payment_header
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
        x_payment_header: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Authorize via x402r escrow -- settles agent payment then locks funds on-chain.

        Two-step flow (both gasless via Facilitator):
        1. Settle agent's EIP-3009 auth (agent wallet -> platform wallet)
        2. Lock funds in AuthCaptureEscrow contract (platform wallet -> escrow)
        """
        escrow = self._get_escrow()
        sdk = self._get_sdk()
        strat = strategy or PaymentStrategy.ESCROW_CAPTURE

        # Step 1: Settle agent's X-Payment auth (agent -> platform)
        agent_settle_tx = None
        payer_address = None
        if x_payment_header:
            try:
                payer_address, _ = sdk.client.get_payer_address(x_payment_header)
                platform_address = sdk._get_agent_account().address

                if payer_address.lower() != platform_address.lower():
                    payload = sdk.client.extract_payload(x_payment_header)
                    settle_resp = sdk.client.settle_payment(payload, amount_usdc)
                    agent_settle_tx = sdk._extract_settlement_tx_hash(settle_resp)
                    logger.info(
                        "x402r: Agent auth settled: task=%s, agent=%s, tx=%s",
                        task_id,
                        payer_address[:10],
                        agent_settle_tx,
                    )
                else:
                    logger.info(
                        "x402r: Skipping agent settle (agent==platform) task=%s",
                        task_id,
                    )
            except Exception as e:
                logger.error(
                    "x402r: Agent auth settlement failed for task %s: %s",
                    task_id,
                    e,
                )
                return {
                    "success": False,
                    "tx_hash": None,
                    "mode": "x402r",
                    "escrow_status": "settlement_failed",
                    "payment_info": None,
                    "payer_address": payer_address,
                    "error": f"Agent auth settlement failed: {e}",
                }

        # Step 2: Lock funds in escrow contract (platform -> escrow)
        # Use platform address as receiver; on release we disburse to actual worker
        platform_address = sdk._get_agent_account().address
        payment = escrow.authorize_task(task_id, platform_address, amount_usdc, strat)

        tx_hash = payment.tx_hashes[0] if payment.tx_hashes else None
        return {
            "success": payment.status == "authorized",
            "tx_hash": tx_hash,
            "agent_settle_tx": agent_settle_tx,
            "mode": "x402r",
            "escrow_status": "deposited"
            if payment.status == "authorized"
            else payment.status,
            "payment_info": payment,
            "payer_address": payer_address,
            "error": None
            if payment.status == "authorized"
            else f"Escrow lock failed: {payment.status}",
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
                return await self._release_x402r(
                    task_id, worker_address, bounty_amount, network, token
                )
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
        worker_address: str,
        bounty_amount: Decimal,
        network: Optional[str] = None,
        token: str = "USDC",
    ) -> Dict[str, Any]:
        """
        Release from on-chain escrow then disburse to worker.

        Three-step flow (all gasless via Facilitator):
        1. Release from escrow contract -> platform wallet
        2. Platform -> worker (bounty minus fee) via EIP-3009
        3. Platform -> treasury (fee) via EIP-3009
        """
        escrow = self._get_escrow()
        sdk = self._get_sdk()

        # Step 1: Release from escrow (escrow -> platform)
        escrow_result = escrow.release_to_worker(task_id, bounty_amount)

        escrow_tx = (
            escrow_result.transaction_hash
            if hasattr(escrow_result, "transaction_hash")
            else None
        )
        escrow_success = (
            escrow_result.success
            if hasattr(escrow_result, "success")
            else bool(escrow_tx)
        )

        if not escrow_success:
            escrow_error = (
                escrow_result.error if hasattr(escrow_result, "error") else None
            )
            return {
                "success": False,
                "tx_hash": None,
                "escrow_release_tx": escrow_tx,
                "mode": "x402r",
                "error": f"Escrow release failed: {escrow_error}",
            }

        logger.info(
            "x402r: Escrow released for task %s, tx=%s. Disbursing to worker...",
            task_id,
            escrow_tx,
        )

        # Step 2: Calculate fee and disburse to worker
        platform_fee = (bounty_amount * PLATFORM_FEE_PERCENT).quantize(
            Decimal("0.000001")
        )
        if Decimal("0") < platform_fee < Decimal("0.01"):
            platform_fee = Decimal("0.01")
        worker_net = bounty_amount - platform_fee

        worker_result = await sdk.disburse_to_worker(
            worker_address=worker_address,
            amount_usdc=worker_net,
            task_id=task_id,
            network=network,
            token=token,
        )

        worker_tx = worker_result.get("tx_hash")
        if not worker_result.get("success") or not worker_tx:
            return {
                "success": False,
                "tx_hash": None,
                "escrow_release_tx": escrow_tx,
                "mode": "x402r",
                "error": worker_result.get("error", "Worker disbursement failed"),
            }

        # Step 3: Collect platform fee (non-blocking)
        fee_tx = None
        try:
            fee_result = await sdk.collect_platform_fee(
                fee_amount=platform_fee,
                task_id=task_id,
                network=network,
                token=token,
            )
            fee_tx = fee_result.get("tx_hash")
            if not fee_result.get("success"):
                logger.warning(
                    "x402r: Worker paid but fee collection failed for task %s: %s",
                    task_id,
                    fee_result.get("error"),
                )
        except Exception as fee_err:
            logger.warning(
                "x402r: Fee collection error for task %s: %s", task_id, fee_err
            )

        return {
            "success": True,
            "tx_hash": worker_tx,
            "escrow_release_tx": escrow_tx,
            "fee_tx_hash": fee_tx,
            "mode": "x402r",
            "gross_amount": float(bounty_amount),
            "platform_fee": float(platform_fee),
            "net_to_worker": float(worker_net),
            "error": None,
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
        agent_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refund a task payment.

        x402r mode: Refunds from on-chain escrow via EMAdvancedEscrow.refund_to_agent(),
                    then disburses from platform back to agent wallet.
        preauth mode: Auth expires naturally, returns success immediately.

        Args:
            task_id: Task identifier
            escrow_id: Escrow identifier (used by preauth SDK refund if available)
            reason: Reason for refund (for audit trail)
            agent_address: Agent's wallet address (for x402r refund disbursement)

        Returns:
            Uniform dict with success, tx_hash, mode, status, error.
        """
        try:
            if self.mode == "x402r":
                return await self._refund_x402r(task_id, agent_address)
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

    async def _refund_x402r(
        self,
        task_id: str,
        agent_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refund from on-chain escrow back to agent.

        Two-step flow (both gasless via Facilitator):
        1. Refund from escrow contract -> platform wallet
        2. Platform -> agent wallet via EIP-3009 (if agent address known)
        """
        escrow = self._get_escrow()

        # Step 1: Refund from escrow (escrow -> platform)
        result = escrow.refund_to_agent(task_id)

        tx_hash = (
            result.transaction_hash if hasattr(result, "transaction_hash") else None
        )
        error = result.error if hasattr(result, "error") else None
        success = result.success if hasattr(result, "success") else bool(tx_hash)

        if not success:
            return {
                "success": False,
                "tx_hash": tx_hash,
                "mode": "x402r",
                "status": "refund_failed",
                "error": f"Escrow refund failed: {error}",
            }

        # Step 2: Disburse from platform back to agent (if address known)
        agent_refund_tx = None
        if agent_address:
            try:
                sdk = self._get_sdk()
                payment = escrow.get_task_payment(task_id)
                refund_amount = payment.amount_usdc if payment else Decimal("0")
                if refund_amount > 0:
                    refund_result = await sdk.disburse_to_worker(
                        worker_address=agent_address,
                        amount_usdc=refund_amount,
                        task_id=f"{task_id}_refund",
                    )
                    agent_refund_tx = refund_result.get("tx_hash")
                    if not refund_result.get("success"):
                        logger.warning(
                            "x402r: Escrow refunded to platform but agent disbursement "
                            "failed for task %s: %s",
                            task_id,
                            refund_result.get("error"),
                        )
            except Exception as e:
                logger.warning(
                    "x402r: Agent refund disbursement failed for task %s: %s",
                    task_id,
                    e,
                )

        return {
            "success": True,
            "tx_hash": tx_hash,
            "agent_refund_tx": agent_refund_tx,
            "mode": "x402r",
            "status": "refunded",
            "error": None,
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
