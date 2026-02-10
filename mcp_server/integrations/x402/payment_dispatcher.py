"""
Payment Dispatcher for Execution Market.

Routes payment operations to x402r escrow or EIP-3009 pre-auth based on EM_PAYMENT_MODE.

Two payment backends:
  - x402r: Locks funds on-chain via AuthCaptureEscrow contract (authorize/release/refund)
  - preauth: EIP-3009 pre-authorization, funds stay in agent wallet until settlement

Both backends go through the Ultravioleta Facilitator and are GASLESS for agents and workers.
"""

import os
import json
import asyncio
import logging
import threading
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from integrations.x402.payment_events import log_payment_event

logger = logging.getLogger(__name__)

# Configuration
EM_PAYMENT_MODE = os.environ.get(
    "EM_PAYMENT_MODE", "preauth"
)  # "preauth" (default) or "x402r"

# --- x402r backend (advanced escrow) ---
try:
    from integrations.x402.advanced_escrow_integration import (
        EMAdvancedEscrow,
        PaymentStrategy,
        TaskPayment,
        get_advanced_escrow,
        ADVANCED_ESCROW_AVAILABLE,
        PLATFORM_FEE_BPS,
    )
except ImportError:
    ADVANCED_ESCROW_AVAILABLE = False
    EMAdvancedEscrow = None  # type: ignore[assignment,misc]
    PaymentStrategy = None  # type: ignore[assignment,misc]
    TaskPayment = None  # type: ignore[assignment,misc]
    get_advanced_escrow = None  # type: ignore[assignment]
    PLATFORM_FEE_BPS = 800

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
    EM_TREASURY = "0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad"


# =============================================================================
# Helpers
# =============================================================================


def _extract_tx_hash(response: Any) -> Optional[str]:
    """Extract tx hash from various SDK response formats (model objects or dicts)."""
    if response is None:
        return None

    # Try get_transaction_hash() method first (SDK model objects)
    getter = getattr(response, "get_transaction_hash", None)
    if callable(getter):
        try:
            val = getter()
            if isinstance(val, str) and val.startswith("0x") and len(val) == 66:
                return val
        except Exception:
            pass

    # Try attribute access
    for attr in ("transaction_hash", "tx_hash", "transaction", "hash"):
        val = getattr(response, attr, None)
        if isinstance(val, str) and val.startswith("0x") and len(val) == 66:
            return val

    # Try dict access
    if isinstance(response, dict):
        for key in ("transaction_hash", "tx_hash", "transaction", "hash"):
            val = response.get(key)
            if isinstance(val, str) and val.startswith("0x") and len(val) == 66:
                return val

    return None


_cached_platform_address: Optional[str] = None


def _get_platform_address() -> str:
    """Get the platform wallet address from WALLET_PRIVATE_KEY env var (cached)."""
    global _cached_platform_address
    if _cached_platform_address is not None:
        return _cached_platform_address

    pk = os.environ.get("WALLET_PRIVATE_KEY")
    if not pk:
        raise RuntimeError(
            "WALLET_PRIVATE_KEY not set — cannot determine platform address"
        )
    from eth_account import Account

    _cached_platform_address = Account.from_key(pk).address
    return _cached_platform_address


# =============================================================================
# PaymentDispatcher
# =============================================================================


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

        # x402r mode also requires the SDK for disbursement (disburse_to_worker,
        # collect_platform_fee, settle agent auth). Fall back if unavailable.
        if self.mode == "x402r" and not SDK_AVAILABLE:
            logger.warning(
                "x402r mode requested but uvd-x402-sdk not available for "
                "disbursement operations. Falling back to preauth mode."
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

        x402r mode: Settles agent auth + locks funds on-chain via escrow contract.
        preauth mode: Verifies EIP-3009 signature via verify_x402_payment().

        Args:
            task_id: Unique task identifier
            receiver: Unused for x402r (platform address is used); agent address for preauth
            amount_usdc: Total amount including fee (bounty + platform fee)
            strategy: PaymentStrategy for x402r mode (optional)
            x_payment_header: X-Payment header from agent request

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
                "payment_info_serialized": None,
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
        Authorize via x402r escrow — settles agent payment then locks funds on-chain.

        Two-step flow (both gasless via Facilitator):
        1. Settle agent's EIP-3009 auth (agent wallet → platform wallet)
        2. Lock funds in AuthCaptureEscrow contract (platform wallet → escrow)

        Args:
            amount_usdc: Total required (bounty + platform fee). The full amount is
                         locked in escrow. On release, worker gets bounty and treasury
                         gets fee. On refund, agent gets full amount back.
        """
        escrow = self._get_escrow()
        sdk = self._get_sdk()
        strat = strategy or PaymentStrategy.ESCROW_CAPTURE
        platform_address = _get_platform_address()

        # Step 1: Settle agent's X-Payment auth (agent → platform)
        agent_settle_tx = None
        payer_address = None
        if x_payment_header:
            try:
                payer_address, _ = sdk.client.get_payer_address(x_payment_header)

                if payer_address.lower() != platform_address.lower():
                    payload = sdk.client.extract_payload(x_payment_header)
                    settle_resp = sdk.client.settle_payment(payload, amount_usdc)
                    agent_settle_tx = _extract_tx_hash(settle_resp)
                    await log_payment_event(
                        task_id=task_id,
                        event_type="settle",
                        status="success",
                        tx_hash=agent_settle_tx,
                        from_address=payer_address,
                        to_address=platform_address,
                        amount_usdc=amount_usdc,
                        metadata={"mode": "x402r", "step": "agent_settle"},
                    )
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
                await log_payment_event(
                    task_id=task_id,
                    event_type="settle",
                    status="failed",
                    from_address=payer_address,
                    to_address=platform_address,
                    amount_usdc=amount_usdc,
                    error=str(e),
                    metadata={"mode": "x402r", "step": "agent_settle"},
                )
                return {
                    "success": False,
                    "tx_hash": None,
                    "mode": "x402r",
                    "escrow_status": "settlement_failed",
                    "payment_info": None,
                    "payment_info_serialized": None,
                    "payer_address": payer_address,
                    "error": f"Agent auth settlement failed: {e}",
                }

        # Step 2: Lock funds in escrow contract (platform → escrow)
        # Use platform address as receiver; on release we disburse to actual worker
        # Run synchronous SDK call in a thread to avoid blocking the event loop
        payment = await asyncio.to_thread(
            escrow.authorize_task,
            task_id,
            platform_address,
            amount_usdc,
            strat,
        )

        tx_hash = payment.tx_hashes[0] if payment.tx_hashes else None
        success = payment.status == "authorized"

        # Serialize PaymentInfo build params for DB persistence.
        # This allows reconstructing PaymentInfo after server restart so that
        # release/refund can reference the same on-chain escrow.
        payment_info_serialized = None
        if payment.payment_info:
            try:
                pi = payment.payment_info
                tier_val = getattr(pi, "tier", None)
                if hasattr(tier_val, "value"):
                    tier_val = tier_val.value
                payment_info_serialized = {
                    "receiver": platform_address,
                    "amount": escrow._amount_to_atomic(amount_usdc),
                    "tier": str(tier_val) if tier_val else "standard",
                    "max_fee_bps": PLATFORM_FEE_BPS,
                }
            except Exception as ser_err:
                logger.warning(
                    "Could not serialize PaymentInfo for task %s: %s",
                    task_id,
                    ser_err,
                )

        return {
            "success": success,
            "tx_hash": tx_hash,
            "agent_settle_tx": agent_settle_tx,
            "mode": "x402r",
            "escrow_status": "deposited" if success else payment.status,
            "payment_info": payment,
            "payment_info_serialized": payment_info_serialized,
            "payer_address": payer_address,
            "error": None if success else f"Escrow lock failed: {payment.status}",
        }

    async def _authorize_preauth(
        self,
        task_id: str,
        amount_usdc: Decimal,
        x_payment_header: Optional[str],
    ) -> Dict[str, Any]:
        """Authorize via preauth — verifies EIP-3009 signature, no funds move."""
        if not x_payment_header:
            return {
                "success": False,
                "tx_hash": None,
                "mode": "preauth",
                "escrow_status": "missing_header",
                "payment_info": None,
                "payment_info_serialized": None,
                "error": "X-Payment header required for preauth mode",
            }

        sdk = self._get_sdk()
        result = await sdk.verify_task_payment(
            task_id=task_id,
            payment_header=x_payment_header,
            expected_amount=amount_usdc,
            worker_address=sdk.recipient_address,
        )

        await log_payment_event(
            task_id=task_id,
            event_type="verify",
            status="success" if result.success else "failed",
            amount_usdc=amount_usdc,
            to_address=sdk.recipient_address,
            network=sdk.network,
            error=result.error,
            metadata={"mode": "preauth"},
        )

        return {
            "success": result.success,
            "tx_hash": result.tx_hash,
            "mode": "preauth",
            "escrow_status": "verified" if result.success else "verification_failed",
            "payment_info": result,
            "payment_info_serialized": None,
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

        x402r mode: Releases from on-chain escrow, disburses bounty to worker + fee to treasury.
        preauth mode: Settles EIP-3009 auth via EMX402SDK.settle_task_payment().

        Args:
            task_id: Task identifier
            worker_address: Worker wallet address
            bounty_amount: The bounty amount (NOT including platform fee).
                           Worker receives this full amount.
            payment_header: Original X-Payment header (required for preauth only)
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
        1. Release full escrowed amount from escrow contract → platform wallet
        2. Platform → worker: full bounty_amount via EIP-3009
        3. Platform → treasury: platform fee via EIP-3009

        The escrow holds bounty + fee. Worker receives the full bounty (no fee
        deduction). Fee goes to treasury. This avoids double-charging.
        """
        escrow = self._get_escrow()
        sdk = self._get_sdk()

        # Ensure the escrow backend has this task's state in memory.
        # Handles server restarts by reconstructing from DB.
        state_ok = await self._ensure_escrow_state(task_id)
        if not state_ok:
            return {
                "success": False,
                "tx_hash": None,
                "mode": "x402r",
                "error": (
                    f"Cannot release task {task_id}: escrow payment state not found. "
                    "The server may have restarted and the escrow metadata is missing "
                    "payment_info for reconstruction. Manual intervention required."
                ),
            }

        # Step 1: Release full amount from escrow (escrow → platform)
        # Pass None for amount to release the entire escrowed balance
        escrow_result = await asyncio.to_thread(escrow.release_to_worker, task_id, None)

        escrow_tx = _extract_tx_hash(escrow_result)
        escrow_success = getattr(escrow_result, "success", bool(escrow_tx))

        if not escrow_success:
            escrow_error = getattr(escrow_result, "error", None)
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

        # Step 2: Disburse FULL BOUNTY to worker (NO fee deduction here).
        # The fee was included as extra on top of bounty when the agent paid.
        worker_result = await sdk.disburse_to_worker(
            worker_address=worker_address,
            amount_usdc=bounty_amount,
            task_id=task_id,
            network=network,
            token=token,
        )

        worker_tx = worker_result.get("tx_hash")
        await log_payment_event(
            task_id=task_id,
            event_type="disburse_worker",
            status="success" if worker_result.get("success") else "failed",
            tx_hash=worker_tx,
            to_address=worker_address,
            amount_usdc=bounty_amount,
            network=network,
            token=token,
            error=worker_result.get("error"),
            metadata={"mode": "x402r", "escrow_release_tx": escrow_tx},
        )
        if not worker_result.get("success") or not worker_tx:
            return {
                "success": False,
                "tx_hash": None,
                "escrow_release_tx": escrow_tx,
                "mode": "x402r",
                "error": worker_result.get("error", "Worker disbursement failed"),
            }

        # Step 3: Collect platform fee (non-blocking — worker already paid)
        platform_fee = (bounty_amount * PLATFORM_FEE_PERCENT).quantize(
            Decimal("0.000001")
        )
        if Decimal("0") < platform_fee < Decimal("0.01"):
            platform_fee = Decimal("0.01")

        fee_tx = None
        fee_error = None
        try:
            fee_result = await sdk.collect_platform_fee(
                fee_amount=platform_fee,
                task_id=task_id,
                network=network,
                token=token,
            )
            fee_tx = fee_result.get("tx_hash")
            if not fee_result.get("success"):
                fee_error = fee_result.get("error", "Fee collection failed")
                logger.warning(
                    "x402r: Worker paid but fee collection failed for task %s: %s",
                    task_id,
                    fee_error,
                )
            await log_payment_event(
                task_id=task_id,
                event_type="disburse_fee",
                status="success" if fee_result.get("success") else "failed",
                tx_hash=fee_tx,
                to_address=EM_TREASURY,
                amount_usdc=platform_fee,
                network=network,
                token=token,
                error=fee_error,
                metadata={"mode": "x402r"},
            )
        except Exception as fee_err:
            fee_error = str(fee_err)
            logger.warning(
                "x402r: Fee collection error for task %s: %s", task_id, fee_err
            )

        return {
            "success": True,
            "tx_hash": worker_tx,
            "escrow_release_tx": escrow_tx,
            "fee_tx_hash": fee_tx,
            "fee_collection_error": fee_error,
            "mode": "x402r",
            "gross_amount": float(bounty_amount + platform_fee),
            "platform_fee": float(platform_fee),
            "net_to_worker": float(bounty_amount),
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

        await log_payment_event(
            task_id=task_id,
            event_type="settle",
            status="success" if result.get("success") else "failed",
            tx_hash=result.get("tx_hash"),
            to_address=worker_address,
            amount_usdc=bounty_amount,
            network=network,
            token=token,
            error=result.get("error"),
            metadata={"mode": "preauth"},
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
                    then disburses full amount from platform back to agent wallet.
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
        1. Refund from escrow contract → platform wallet
        2. Platform → agent wallet via EIP-3009 (full amount including fee)
        """
        escrow = self._get_escrow()

        # Ensure in-memory state is loaded (handles server restarts)
        state_ok = await self._ensure_escrow_state(task_id)
        if not state_ok:
            return {
                "success": False,
                "tx_hash": None,
                "mode": "x402r",
                "status": "state_not_found",
                "error": (
                    f"Cannot refund task {task_id}: escrow payment state not found. "
                    "Manual intervention required."
                ),
            }

        # Step 1: Refund from escrow (escrow → platform)
        result = await asyncio.to_thread(escrow.refund_to_agent, task_id, None)

        tx_hash = _extract_tx_hash(result)
        error = getattr(result, "error", None)
        success = getattr(result, "success", bool(tx_hash))

        if not success:
            return {
                "success": False,
                "tx_hash": tx_hash,
                "mode": "x402r",
                "status": "refund_failed",
                "error": f"Escrow refund failed: {error}",
            }

        # Step 2: Disburse from platform back to agent (if address known)
        # The refund amount is the full escrowed amount (bounty + fee)
        agent_refund_tx = None
        disbursement_error = None
        if agent_address:
            try:
                sdk = self._get_sdk()
                payment = escrow.get_task_payment(task_id)
                refund_amount = payment.amount_usdc if payment else Decimal("0")

                # Fallback: load amount from DB if in-memory is 0
                if refund_amount <= 0:
                    refund_amount = await self._get_escrow_amount_from_db(task_id)

                if refund_amount > 0:
                    # NOTE: disburse_to_worker is a generic EIP-3009 transfer.
                    # Here we use it to send funds back to the agent (refund).
                    # The task_id suffix _refund distinguishes from worker payouts.
                    refund_result = await sdk.disburse_to_worker(
                        worker_address=agent_address,
                        amount_usdc=refund_amount,
                        task_id=f"{task_id}_refund",
                    )
                    agent_refund_tx = refund_result.get("tx_hash")
                    if not refund_result.get("success"):
                        disbursement_error = (
                            f"Escrow refunded to platform but agent disbursement "
                            f"failed: {refund_result.get('error')}. "
                            f"Funds ({refund_amount} USDC) are in the platform wallet "
                            f"and need manual transfer to {agent_address}."
                        )
                        logger.error("x402r: %s (task=%s)", disbursement_error, task_id)
                else:
                    disbursement_error = (
                        f"Refund amount is 0 for task {task_id} — cannot disburse to agent. "
                        "Escrow was released to platform but amount is unknown."
                    )
                    logger.error("x402r: %s", disbursement_error)
            except Exception as e:
                disbursement_error = (
                    f"Agent refund disbursement exception: {e}. "
                    f"Funds may be stuck in platform wallet for task {task_id}."
                )
                logger.error("x402r: %s", disbursement_error)
        else:
            disbursement_error = (
                f"No agent_address provided for task {task_id} — "
                "escrow refunded to platform but cannot disburse to agent."
            )
            logger.warning("x402r: %s", disbursement_error)

        # Only report full success if agent actually received the funds
        if disbursement_error:
            return {
                "success": False,
                "tx_hash": tx_hash,
                "agent_refund_tx": agent_refund_tx,
                "mode": "x402r",
                "status": "partial_refund",
                "error": disbursement_error,
            }

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
        await log_payment_event(
            task_id=task_id,
            event_type="refund",
            status="success",
            metadata={"mode": "preauth", "method": "auth_expired"},
        )
        return {
            "success": True,
            "tx_hash": None,
            "mode": "preauth",
            "status": "auth_expired",
            "error": None,
        }

    # =========================================================================
    # State Reconstruction (survives server restarts)
    # =========================================================================

    async def _ensure_escrow_state(self, task_id: str) -> bool:
        """
        Ensure the EMAdvancedEscrow backend has this task's payment state in memory.

        After a server restart, the in-memory `_task_payments` dict is empty.
        This method reconstructs the PaymentInfo from serialized data stored in
        the escrows table metadata, allowing release/refund to proceed.
        """
        escrow = self._get_escrow()
        if escrow.get_task_payment(task_id) is not None:
            return True

        # Try to reconstruct from DB
        try:
            import supabase_client as db

            client = db.get_client()
            result = (
                client.table("escrows")
                .select("metadata,total_amount_usdc,beneficiary_address,status")
                .eq("task_id", task_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if not rows:
                logger.warning("No escrow row found for task %s", task_id)
                return False

            row = rows[0]
            escrow_status = (row.get("status") or "").lower()

            # Prevent reconstructing state for already-completed escrows.
            # This blocks re-release or re-refund of already-settled escrows.
            terminal_statuses = {
                "released",
                "refunded",
                "completed",
                "authorization_expired",
            }
            if escrow_status in terminal_statuses:
                logger.warning(
                    "Escrow for task %s is already in terminal state '%s' — "
                    "refusing to reconstruct state to prevent duplicate operations.",
                    task_id,
                    escrow_status,
                )
                return False

            metadata = row.get("metadata") or {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            pi_data = metadata.get("payment_info")
            if not pi_data:
                logger.warning(
                    "No payment_info in escrow metadata for task %s — cannot "
                    "reconstruct state. This task may predate payment_info "
                    "persistence. Manual intervention required.",
                    task_id,
                )
                return False

            # Reconstruct PaymentInfo using the SDK
            from integrations.x402.advanced_escrow_integration import TaskTier

            tier_val = pi_data.get("tier", "standard")
            try:
                tier = TaskTier(tier_val)
            except (ValueError, KeyError):
                tier = TaskTier.STANDARD

            pi = escrow.client.build_payment_info(
                receiver=pi_data["receiver"],
                amount=pi_data["amount"],
                tier=tier,
                max_fee_bps=pi_data.get("max_fee_bps", PLATFORM_FEE_BPS),
            )

            # Register the reconstructed state in memory
            # NOTE: The on-chain escrow was already created with these exact params.
            # Rebuilding with the same values produces the same PaymentInfo hash,
            # which the contract uses to reference the escrow.
            amount_usdc = Decimal(str(row.get("total_amount_usdc", 0)))
            payment = TaskPayment(
                task_id=task_id,
                strategy=PaymentStrategy.ESCROW_CAPTURE,
                payment_info=pi,
                amount_usdc=amount_usdc,
                status=row.get("status", "deposited"),
            )
            escrow._task_payments[task_id] = payment
            logger.info(
                "Reconstructed escrow state for task %s from DB (amount=%s)",
                task_id,
                amount_usdc,
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to reconstruct escrow state for task %s: %s", task_id, e
            )
            return False

    async def _get_escrow_amount_from_db(self, task_id: str) -> Decimal:
        """Load the escrowed amount from the DB as fallback."""
        try:
            import supabase_client as db

            client = db.get_client()
            result = (
                client.table("escrows")
                .select("total_amount_usdc")
                .eq("task_id", task_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if rows:
                return Decimal(str(rows[0].get("total_amount_usdc", 0)))
        except Exception as e:
            logger.warning(
                "Could not load escrow amount from DB for task %s: %s", task_id, e
            )
        return Decimal("0")

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
_dispatcher_lock = threading.Lock()


def get_dispatcher() -> PaymentDispatcher:
    """Get or create the default PaymentDispatcher singleton (thread-safe)."""
    global _dispatcher
    if _dispatcher is None:
        with _dispatcher_lock:
            # Double-check pattern: another thread may have created it
            if _dispatcher is None:
                _dispatcher = PaymentDispatcher()
    return _dispatcher
