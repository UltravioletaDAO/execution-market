"""
Payment Dispatcher for Execution Market.

Routes payment operations based on EM_PAYMENT_MODE:
  - fase1: Balance check at creation, 2 direct EIP-3009 settlements at approval (default)
  - fase2: On-chain escrow via AdvancedEscrowClient + gasless facilitator release/refund
  - preauth: EIP-3009 pre-authorization, funds stay in agent wallet until settlement
  - x402r: Legacy on-chain escrow via EMAdvancedEscrow (requires gas + operator key)

All backends go through the Ultravioleta Facilitator and are GASLESS for agents and workers.
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
    "EM_PAYMENT_MODE", "fase1"
)  # "fase1" (default), "preauth", or "x402r"

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
    PLATFORM_FEE_BPS = 1300

# --- preauth backend (EIP-3009 SDK) ---
try:
    from integrations.x402.sdk_client import (
        EMX402SDK,
        get_sdk,
        verify_x402_payment,
        SDK_AVAILABLE,
        PLATFORM_FEE_PERCENT,
        EM_TREASURY,
        FACILITATOR_URL,
        NETWORK_CONFIG,
    )
except ImportError:
    SDK_AVAILABLE = False
    EMX402SDK = None  # type: ignore[assignment,misc]
    get_sdk = None  # type: ignore[assignment]
    verify_x402_payment = None  # type: ignore[assignment]
    PLATFORM_FEE_PERCENT = Decimal("0.13")
    EM_TREASURY = "0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad"
    FACILITATOR_URL = "https://facilitator.ultravioletadao.xyz"
    NETWORK_CONFIG = {}  # type: ignore[assignment]

# --- fase2 backend (AdvancedEscrowClient from SDK, gasless via facilitator) ---
try:
    from uvd_x402_sdk.advanced_escrow import (
        AdvancedEscrowClient,
        PaymentInfo as EscrowPaymentInfo,
        TaskTier,
    )

    FASE2_SDK_AVAILABLE = True
except ImportError:
    FASE2_SDK_AVAILABLE = False
    AdvancedEscrowClient = None  # type: ignore[assignment,misc]
    EscrowPaymentInfo = None  # type: ignore[assignment,misc]
    TaskTier = None  # type: ignore[assignment,misc]

# EM PaymentOperator address (Base Mainnet). Fase 3 Clean: OR(Payer|Facilitator), no operator fee.
# Only x402r ProtocolFeeConfig (controlled by BackTrack) can take on-chain fees.
# Override via env var when deploying operators on additional chains.
# Legacy: 0x8D3D...c2E6 (fase3 w/1% fee), 0xb963...d723 (fase2)
EM_OPERATOR = os.environ.get(
    "EM_PAYMENT_OPERATOR", "0xd5149049e7c212ce5436a9581b4307EB9595df95"
)

# On-chain protocol fee (in basis points) that x402r deducts when releasing escrow.
# Fase 2 uses 0 (feeCalculator=address(0)). Fase 3 will set this to 100 (1%).
# This is used to compute how much the platform wallet actually receives after escrow
# release, so that treasury disbursement does not attempt to send more than available.
X402R_ON_CHAIN_FEE_BPS = int(os.environ.get("X402R_ON_CHAIN_FEE_BPS", "0"))


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


def _compute_treasury_remainder(
    bounty_amount: Decimal, total_locked: Decimal
) -> Decimal:
    """
    Compute the treasury fee as the remainder after paying the worker.

    Treasury receives whatever is left in the platform wallet after the worker
    gets their full bounty. This naturally handles any on-chain protocol fee
    deduction from x402r — if the escrow takes a cut, the treasury amount
    shrinks accordingly instead of the transfer failing.

    Args:
        bounty_amount: The worker's bounty (they always get this in full).
        total_locked: The total amount originally locked in escrow
                      (bounty + platform fee).

    Returns:
        The amount to send to treasury (>= 0, quantized to 6 decimals).
    """
    on_chain_fee_rate = Decimal(X402R_ON_CHAIN_FEE_BPS) / Decimal(10000)
    total_received = total_locked * (Decimal("1") - on_chain_fee_rate)
    treasury_amount = (total_received - bounty_amount).quantize(Decimal("0.000001"))

    # Ensure non-negative (safety: if on-chain fee is unexpectedly high)
    if treasury_amount < Decimal("0"):
        logger.warning(
            "Treasury remainder is negative (%.6f). On-chain fee may have exceeded "
            "platform fee margin. Setting treasury to 0.",
            treasury_amount,
        )
        treasury_amount = Decimal("0")

    # Apply minimum fee ($0.01) if non-zero
    if Decimal("0") < treasury_amount < Decimal("0.01"):
        treasury_amount = Decimal("0.01")

    return treasury_amount


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

        if self.mode not in ("x402r", "preauth", "fase1", "fase2"):
            logger.warning(
                "Unknown EM_PAYMENT_MODE '%s', falling back to 'fase1'",
                self.mode,
            )
            self.mode = "fase1"

        # Validate availability and fall back if needed
        if self.mode == "fase2" and not FASE2_SDK_AVAILABLE:
            logger.warning(
                "fase2 mode requested but AdvancedEscrowClient SDK not available. "
                "Falling back to fase1 mode."
            )
            self.mode = "fase1"

        # fase2 also needs the base SDK for post-release disbursement
        if self.mode == "fase2" and not SDK_AVAILABLE:
            logger.warning(
                "fase2 mode requested but uvd-x402-sdk not available for "
                "disbursement operations. Falling back to fase1 mode."
            )
            self.mode = "fase1"

        if self.mode == "x402r" and not ADVANCED_ESCROW_AVAILABLE:
            logger.warning(
                "x402r mode requested but advanced escrow SDK not available. "
                "Falling back to fase1 mode."
            )
            self.mode = "fase1"

        # x402r mode also requires the SDK for disbursement (disburse_to_worker,
        # collect_platform_fee, settle agent auth). Fall back if unavailable.
        if self.mode == "x402r" and not SDK_AVAILABLE:
            logger.warning(
                "x402r mode requested but uvd-x402-sdk not available for "
                "disbursement operations. Falling back to fase1 mode."
            )
            self.mode = "fase1"

        if self.mode in ("preauth", "fase1") and not SDK_AVAILABLE:
            logger.error(
                "%s mode requested but uvd-x402-sdk not available. "
                "Payment operations will fail.",
                self.mode,
            )

        # Lazy-initialized backend instances
        self._escrow: Optional[Any] = None
        self._sdk: Optional[Any] = None
        self._fase2_clients: Dict[int, Any] = {}  # chain_id → AdvancedEscrowClient

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

    def _get_fase2_client(self, network: str = "base") -> "AdvancedEscrowClient":
        """Lazy-init an AdvancedEscrowClient for the given network."""
        config = NETWORK_CONFIG.get(network, {})
        chain_id = config.get("chain_id", 8453)

        if chain_id not in self._fase2_clients:
            pk = os.environ.get("WALLET_PRIVATE_KEY")
            if not pk:
                raise RuntimeError(
                    "WALLET_PRIVATE_KEY not set — cannot init AdvancedEscrowClient"
                )

            rpc_url = config.get("rpc_url", "https://mainnet.base.org")
            operator = os.environ.get("EM_PAYMENT_OPERATOR", EM_OPERATOR)

            self._fase2_clients[chain_id] = AdvancedEscrowClient(
                private_key=pk,
                facilitator_url=FACILITATOR_URL,
                rpc_url=rpc_url,
                chain_id=chain_id,
                operator_address=operator,
            )
            logger.info(
                "Fase2 AdvancedEscrowClient initialized: chain=%d, operator=%s",
                chain_id,
                operator[:10],
            )

        return self._fase2_clients[chain_id]

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
        agent_address: Optional[str] = None,
        network: Optional[str] = None,
        token: str = "USDC",
    ) -> Dict[str, Any]:
        """
        Authorize (lock or verify) a payment for a task.

        x402r mode: Settles agent auth + locks funds on-chain via escrow contract.
        preauth mode: Verifies EIP-3009 signature via verify_x402_payment().
        fase1 mode: Checks agent's on-chain balance (no funds move).

        Args:
            task_id: Unique task identifier
            receiver: Unused for x402r (platform address is used); agent address for preauth
            amount_usdc: Total amount including fee (bounty + platform fee)
            strategy: PaymentStrategy for x402r mode (optional)
            x_payment_header: X-Payment header from agent request
            agent_address: Agent wallet address (for fase1 balance check)
            network: Payment network (for fase1)
            token: Payment token (for fase1)

        Returns:
            Uniform dict with success, tx_hash, mode, escrow_status, payment_info, error.
        """
        try:
            if self.mode == "x402r":
                return await self._authorize_x402r(
                    task_id, receiver, amount_usdc, strategy, x_payment_header
                )
            elif self.mode == "fase2":
                return await self._authorize_fase2(task_id, amount_usdc, network, token)
            elif self.mode == "fase1":
                return await self._authorize_fase1(
                    task_id, amount_usdc, agent_address, network, token
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

    async def _authorize_fase1(
        self,
        task_id: str,
        amount_usdc: Decimal,
        agent_address: Optional[str] = None,
        network: Optional[str] = None,
        token: str = "USDC",
    ) -> Dict[str, Any]:
        """
        Authorize via fase1 — balance check only, no funds move.

        Checks that agent has enough tokens on-chain. Advisory: task still
        creates even if balance check fails (payment enforced at approval).
        """
        sdk = self._get_sdk()

        # Derive agent address from WALLET_PRIVATE_KEY if not provided
        if not agent_address:
            try:
                agent_address = sdk._get_agent_account().address
            except Exception:
                agent_address = None

        if not agent_address:
            return {
                "success": True,
                "tx_hash": None,
                "mode": "fase1",
                "escrow_status": "balance_unknown",
                "payment_info": None,
                "payment_info_serialized": None,
                "error": None,
                "warning": "No agent address available for balance check",
            }

        balance_result = await sdk.check_agent_balance(
            agent_address=agent_address,
            required_amount=amount_usdc,
            network=network or sdk.network,
            token=token,
        )

        await log_payment_event(
            task_id=task_id,
            event_type="balance_check",
            status="success" if balance_result.get("sufficient") else "warning",
            from_address=agent_address,
            amount_usdc=amount_usdc,
            network=network or sdk.network,
            token=token,
            metadata={
                "mode": "fase1",
                "balance": str(balance_result.get("balance")),
                "sufficient": balance_result.get("sufficient"),
                "warning": balance_result.get("warning"),
            },
        )

        sufficient = balance_result.get("sufficient", True)
        return {
            "success": True,  # Always succeed — balance check is advisory
            "tx_hash": None,
            "mode": "fase1",
            "escrow_status": "balance_verified"
            if sufficient
            else "insufficient_balance",
            "payment_info": None,
            "payment_info_serialized": None,
            "balance_info": balance_result,
            "error": None,
            "warning": None
            if sufficient
            else (
                f"Agent balance may be insufficient "
                f"(have {balance_result.get('balance')}, need {amount_usdc})"
            ),
        }

    async def _authorize_fase2(
        self,
        task_id: str,
        amount_usdc: Decimal,
        network: Optional[str] = None,
        token: str = "USDC",
    ) -> Dict[str, Any]:
        """
        Authorize via fase2 — lock funds on-chain in escrow via facilitator.

        Uses AdvancedEscrowClient.authorize() which signs an EIP-3009 auth
        and sends it to the facilitator, which locks funds in the
        AuthCaptureEscrow contract. Fully gasless for the agent.

        Receiver = platform wallet. On release, we disburse to worker + fee.
        """
        network = network or "base"
        client = self._get_fase2_client(network)
        platform_address = _get_platform_address()

        # Total to lock = bounty + platform fee
        total_amount = amount_usdc * (Decimal("1") + PLATFORM_FEE_PERCENT)
        total_amount = total_amount.quantize(Decimal("0.000001"))

        # Convert to atomic units (6 decimals for USDC)
        config = NETWORK_CONFIG.get(network, {})
        decimals = 6
        for t_info in (config.get("tokens", {}).get(token, {}),):
            if t_info:
                decimals = t_info.get("decimals", 6)
        amount_atomic = int(total_amount * Decimal(10**decimals))

        # Determine tier from amount
        tier = TaskTier.MICRO
        if amount_usdc >= Decimal("100"):
            tier = TaskTier.ENTERPRISE
        elif amount_usdc >= Decimal("25"):
            tier = TaskTier.PREMIUM
        elif amount_usdc >= Decimal("5"):
            tier = TaskTier.STANDARD

        # Build PaymentInfo (receiver = platform wallet for post-release disbursement)
        pi = await asyncio.to_thread(
            client.build_payment_info,
            receiver=platform_address,
            amount=amount_atomic,
            tier=tier,
            max_fee_bps=int(PLATFORM_FEE_PERCENT * 10000),
        )

        logger.info(
            "fase2: Built PaymentInfo for task %s: amount=%d, tier=%s, salt=%s...",
            task_id,
            amount_atomic,
            tier.value if hasattr(tier, "value") else tier,
            pi.salt[:18],
        )

        # Authorize (lock funds) via facilitator — synchronous, run in thread
        auth_result = await asyncio.to_thread(client.authorize, pi)

        if not auth_result.success:
            await log_payment_event(
                task_id=task_id,
                event_type="escrow_authorize",
                status="failed",
                amount_usdc=total_amount,
                network=network,
                token=token,
                error=auth_result.error,
                metadata={"mode": "fase2", "tier": str(tier)},
            )
            return {
                "success": False,
                "tx_hash": None,
                "mode": "fase2",
                "escrow_status": "authorize_failed",
                "payment_info": None,
                "payment_info_serialized": None,
                "error": f"Escrow authorize failed: {auth_result.error}",
            }

        tx_hash = auth_result.transaction_hash

        # Serialize full PaymentInfo for DB persistence (state reconstruction)
        payment_info_serialized = {
            "mode": "fase2",
            "operator": pi.operator,
            "receiver": pi.receiver,
            "token": pi.token,
            "max_amount": pi.max_amount,
            "pre_approval_expiry": pi.pre_approval_expiry,
            "authorization_expiry": pi.authorization_expiry,
            "refund_expiry": pi.refund_expiry,
            "min_fee_bps": pi.min_fee_bps,
            "max_fee_bps": pi.max_fee_bps,
            "fee_receiver": pi.fee_receiver,
            "salt": pi.salt,
            "chain_id": client.chain_id,
            "network": network,
        }

        await log_payment_event(
            task_id=task_id,
            event_type="escrow_authorize",
            status="success",
            tx_hash=tx_hash,
            from_address=client.payer,
            to_address=platform_address,
            amount_usdc=total_amount,
            network=network,
            token=token,
            metadata={
                "mode": "fase2",
                "tier": str(tier),
                "salt": pi.salt[:18],
                "bounty": str(amount_usdc),
            },
        )

        logger.info(
            "fase2: Funds locked in escrow: task=%s, amount=%s, tx=%s",
            task_id,
            total_amount,
            tx_hash,
        )

        return {
            "success": True,
            "tx_hash": tx_hash,
            "mode": "fase2",
            "escrow_status": "deposited",
            "payment_info": pi,
            "payment_info_serialized": payment_info_serialized,
            "payer_address": client.payer,
            "error": None,
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
        worker_auth_header: Optional[str] = None,
        fee_auth_header: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Release payment to a worker after task approval.

        x402r mode: Releases from on-chain escrow, disburses bounty to worker + fee to treasury.
        preauth mode: Settles EIP-3009 auth via EMX402SDK.settle_task_payment().
        fase1 mode: 2 direct settlements agent->worker + agent->treasury (no intermediary).

        Args:
            task_id: Task identifier
            worker_address: Worker wallet address
            bounty_amount: The bounty amount (NOT including platform fee).
                           Worker receives this full amount.
            payment_header: Original X-Payment header (required for preauth only)
            network: Payment network (optional, defaults to SDK default)
            token: Payment token (default: USDC)
            worker_auth_header: Pre-signed auth for worker payment (fase1 external agents)
            fee_auth_header: Pre-signed auth for fee payment (fase1 external agents)

        Returns:
            Uniform dict with success, tx_hash, mode, error.
        """
        try:
            if self.mode == "x402r":
                return await self._release_x402r(
                    task_id, worker_address, bounty_amount, network, token
                )
            elif self.mode == "fase2":
                return await self._release_fase2(
                    task_id, worker_address, bounty_amount, network, token
                )
            elif self.mode == "fase1":
                return await self._release_fase1(
                    task_id,
                    worker_address,
                    bounty_amount,
                    worker_auth_header,
                    fee_auth_header,
                    network,
                    token,
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

        # Step 3: Collect platform fee (non-blocking — worker already paid).
        # Treasury receives the remainder after worker payment. This naturally
        # handles any on-chain protocol fee deduction from x402r — if the escrow
        # contract takes a cut, the treasury amount shrinks accordingly instead
        # of the transfer failing due to insufficient funds.
        total_locked = bounty_amount * (Decimal("1") + PLATFORM_FEE_PERCENT)
        total_locked = total_locked.quantize(Decimal("0.000001"))
        platform_fee = _compute_treasury_remainder(bounty_amount, total_locked)

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

    async def _release_fase1(
        self,
        task_id: str,
        worker_address: str,
        bounty_amount: Decimal,
        worker_auth_header: Optional[str],
        fee_auth_header: Optional[str],
        network: Optional[str],
        token: str,
    ) -> Dict[str, Any]:
        """
        Fase 1: 2 direct settlements — agent->worker + agent->treasury.

        No intermediary wallet. Server-managed agents: server signs both auths.
        External agents: provide pre-signed auth headers.
        """
        sdk = self._get_sdk()
        result = await sdk.settle_direct_payments(
            task_id=task_id,
            worker_address=worker_address,
            bounty_amount=bounty_amount,
            worker_auth_header=worker_auth_header,
            fee_auth_header=fee_auth_header,
            network=network,
            token=token,
        )

        worker_tx = result.get("tx_hash")
        fee_tx = result.get("fee_tx_hash")

        await log_payment_event(
            task_id=task_id,
            event_type="settle_worker_direct",
            status="success" if result.get("success") else "failed",
            tx_hash=worker_tx,
            to_address=worker_address,
            amount_usdc=bounty_amount,
            network=network,
            token=token,
            error=result.get("error"),
            metadata={"mode": "fase1"},
        )

        if fee_tx:
            platform_fee = Decimal(str(result.get("platform_fee", 0)))
            await log_payment_event(
                task_id=task_id,
                event_type="settle_fee_direct",
                status="success",
                tx_hash=fee_tx,
                to_address=EM_TREASURY,
                amount_usdc=platform_fee,
                network=network,
                token=token,
                metadata={"mode": "fase1"},
            )

        return {
            "success": result.get("success", False),
            "tx_hash": worker_tx,
            "fee_tx_hash": fee_tx,
            "mode": "fase1",
            "gross_amount": result.get("gross_amount"),
            "platform_fee": result.get("platform_fee"),
            "net_to_worker": result.get("net_to_worker"),
            "error": result.get("error"),
        }

    async def _release_fase2(
        self,
        task_id: str,
        worker_address: str,
        bounty_amount: Decimal,
        network: Optional[str] = None,
        token: str = "USDC",
    ) -> Dict[str, Any]:
        """
        Fase 2: Release from on-chain escrow (gasless) then disburse to worker.

        Three-step flow:
        1. Reconstruct PaymentInfo from DB (escrows table metadata)
        2. Release full escrowed amount via facilitator (escrow → platform, gasless)
        3. Disburse bounty to worker + fee to treasury via EIP-3009
        """
        network = network or "base"

        # Step 1: Reconstruct PaymentInfo from DB
        pi, pi_meta = await self._reconstruct_fase2_state(task_id)
        if pi is None:
            return {
                "success": False,
                "tx_hash": None,
                "mode": "fase2",
                "error": (
                    f"Cannot release task {task_id}: escrow payment state not found. "
                    "The payment_info metadata may be missing from the escrows table."
                ),
            }

        stored_network = pi_meta.get("network", network)
        client = self._get_fase2_client(stored_network)

        # Step 2: Release from escrow via facilitator (gasless)
        logger.info("fase2: Releasing escrow for task %s via facilitator...", task_id)
        release_result = await asyncio.to_thread(client.release_via_facilitator, pi)

        if not release_result.success:
            await log_payment_event(
                task_id=task_id,
                event_type="escrow_release",
                status="failed",
                network=stored_network,
                token=token,
                error=release_result.error,
                metadata={"mode": "fase2"},
            )
            return {
                "success": False,
                "tx_hash": None,
                "mode": "fase2",
                "error": f"Escrow release failed: {release_result.error}",
            }

        escrow_tx = release_result.transaction_hash
        await log_payment_event(
            task_id=task_id,
            event_type="escrow_release",
            status="success",
            tx_hash=escrow_tx,
            to_address=pi.receiver,
            amount_usdc=bounty_amount,
            network=stored_network,
            token=token,
            metadata={"mode": "fase2"},
        )

        logger.info(
            "fase2: Escrow released for task %s, tx=%s. Disbursing to worker...",
            task_id,
            escrow_tx,
        )

        # Step 3: Disburse bounty to worker from platform wallet
        sdk = self._get_sdk()
        worker_result = await sdk.disburse_to_worker(
            worker_address=worker_address,
            amount_usdc=bounty_amount,
            task_id=task_id,
            network=stored_network,
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
            network=stored_network,
            token=token,
            error=worker_result.get("error"),
            metadata={"mode": "fase2", "escrow_release_tx": escrow_tx},
        )

        if not worker_result.get("success") or not worker_tx:
            return {
                "success": False,
                "tx_hash": None,
                "escrow_release_tx": escrow_tx,
                "mode": "fase2",
                "error": worker_result.get("error", "Worker disbursement failed"),
            }

        # Step 4: Collect platform fee (non-blocking — worker already paid).
        # Treasury receives the remainder after worker payment. This naturally
        # handles any on-chain protocol fee deduction from x402r — if the escrow
        # contract takes a cut, the treasury amount shrinks accordingly instead
        # of the transfer failing due to insufficient funds.
        total_locked = bounty_amount * (Decimal("1") + PLATFORM_FEE_PERCENT)
        total_locked = total_locked.quantize(Decimal("0.000001"))
        platform_fee = _compute_treasury_remainder(bounty_amount, total_locked)

        fee_tx = None
        fee_error = None
        try:
            fee_result = await sdk.collect_platform_fee(
                fee_amount=platform_fee,
                task_id=task_id,
                network=stored_network,
                token=token,
            )
            fee_tx = fee_result.get("tx_hash")
            if not fee_result.get("success"):
                fee_error = fee_result.get("error", "Fee collection failed")
                logger.warning(
                    "fase2: Worker paid but fee collection failed for task %s: %s",
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
                network=stored_network,
                token=token,
                error=fee_error,
                metadata={"mode": "fase2"},
            )
        except Exception as fee_err:
            fee_error = str(fee_err)
            logger.warning(
                "fase2: Fee collection error for task %s: %s", task_id, fee_err
            )

        return {
            "success": True,
            "tx_hash": worker_tx,
            "escrow_release_tx": escrow_tx,
            "fee_tx_hash": fee_tx,
            "fee_collection_error": fee_error,
            "mode": "fase2",
            "gross_amount": float(bounty_amount + platform_fee),
            "platform_fee": float(platform_fee),
            "net_to_worker": float(bounty_amount),
            "error": None,
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
        fase2 mode: Gasless refund via facilitator (funds return to agent directly).
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
            elif self.mode == "fase2":
                return await self._refund_fase2(task_id, reason)
            elif self.mode == "fase1":
                return await self._refund_fase1(task_id, reason)
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

    async def _refund_fase1(
        self,
        task_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fase 1 refund: no funds were moved, nothing to refund."""
        logger.info(
            "Fase 1 refund for task %s: no funds moved, nothing to refund",
            task_id,
        )
        await log_payment_event(
            task_id=task_id,
            event_type="refund",
            status="success",
            metadata={"mode": "fase1", "method": "no_funds_moved", "reason": reason},
        )
        return {
            "success": True,
            "tx_hash": None,
            "mode": "fase1",
            "status": "no_funds_moved",
            "error": None,
        }

    async def _refund_fase2(
        self,
        task_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fase 2 refund: gasless refund from on-chain escrow via facilitator.

        Funds return directly to the agent's wallet. No platform intermediary
        needed because the escrow contract sends funds to the original payer.
        """
        # Reconstruct PaymentInfo from DB
        pi, pi_meta = await self._reconstruct_fase2_state(task_id)
        if pi is None:
            # If no escrow found, maybe task was created but authorize failed.
            # Treat as no-op like fase1.
            logger.info(
                "fase2: No escrow state for task %s — treating as no-op refund",
                task_id,
            )
            await log_payment_event(
                task_id=task_id,
                event_type="escrow_refund",
                status="success",
                metadata={
                    "mode": "fase2",
                    "method": "no_escrow_found",
                    "reason": reason,
                },
            )
            return {
                "success": True,
                "tx_hash": None,
                "mode": "fase2",
                "status": "no_escrow_found",
                "error": None,
            }

        stored_network = pi_meta.get("network", "base")
        client = self._get_fase2_client(stored_network)

        logger.info("fase2: Refunding escrow for task %s via facilitator...", task_id)
        refund_result = await asyncio.to_thread(client.refund_via_facilitator, pi)

        if not refund_result.success:
            await log_payment_event(
                task_id=task_id,
                event_type="escrow_refund",
                status="failed",
                network=stored_network,
                error=refund_result.error,
                metadata={"mode": "fase2", "reason": reason},
            )
            return {
                "success": False,
                "tx_hash": None,
                "mode": "fase2",
                "status": "refund_failed",
                "error": f"Escrow refund failed: {refund_result.error}",
            }

        tx_hash = refund_result.transaction_hash
        await log_payment_event(
            task_id=task_id,
            event_type="escrow_refund",
            status="success",
            tx_hash=tx_hash,
            from_address=pi.receiver,
            to_address=client.payer,
            network=stored_network,
            metadata={"mode": "fase2", "reason": reason},
        )

        logger.info(
            "fase2: Escrow refunded for task %s, tx=%s",
            task_id,
            tx_hash,
        )

        return {
            "success": True,
            "tx_hash": tx_hash,
            "mode": "fase2",
            "status": "refunded",
            "error": None,
        }

    # =========================================================================
    # State Reconstruction (survives server restarts)
    # =========================================================================

    async def _reconstruct_fase2_state(self, task_id: str) -> tuple:
        """
        Reconstruct a Fase 2 PaymentInfo from the escrows table metadata.

        Returns (PaymentInfo, metadata_dict) or (None, {}) if not found.
        """
        try:
            import supabase_client as db

            client = db.get_client()
            result = (
                client.table("escrows")
                .select("metadata,total_amount_usdc,status")
                .eq("task_id", task_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if not rows:
                logger.warning("fase2: No escrow row found for task %s", task_id)
                return None, {}

            row = rows[0]
            escrow_status = (row.get("status") or "").lower()

            # Block operations on already-terminal escrows
            terminal_statuses = {
                "released",
                "refunded",
                "completed",
                "authorization_expired",
            }
            if escrow_status in terminal_statuses:
                logger.warning(
                    "fase2: Escrow for task %s is in terminal state '%s' — "
                    "refusing to reconstruct.",
                    task_id,
                    escrow_status,
                )
                return None, {}

            metadata = row.get("metadata") or {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            pi_data = metadata.get("payment_info")
            if not pi_data or pi_data.get("mode") != "fase2":
                logger.warning(
                    "fase2: No fase2 payment_info in escrow metadata for task %s",
                    task_id,
                )
                return None, {}

            # Reconstruct PaymentInfo dataclass
            pi = EscrowPaymentInfo(
                operator=pi_data["operator"],
                receiver=pi_data["receiver"],
                token=pi_data["token"],
                max_amount=pi_data["max_amount"],
                pre_approval_expiry=pi_data["pre_approval_expiry"],
                authorization_expiry=pi_data["authorization_expiry"],
                refund_expiry=pi_data["refund_expiry"],
                min_fee_bps=pi_data["min_fee_bps"],
                max_fee_bps=pi_data["max_fee_bps"],
                fee_receiver=pi_data["fee_receiver"],
                salt=pi_data["salt"],
            )

            logger.info("fase2: Reconstructed PaymentInfo for task %s from DB", task_id)
            return pi, pi_data

        except Exception as e:
            logger.error(
                "fase2: Failed to reconstruct state for task %s: %s", task_id, e
            )
            return None, {}

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
            "fase2_available": FASE2_SDK_AVAILABLE,
            "preauth_available": SDK_AVAILABLE,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self.mode == "x402r" and self._escrow is not None:
            try:
                info["x402r_config"] = self._escrow.get_config()
            except Exception:
                pass

        if self.mode == "fase2" and self._fase2_clients:
            info["fase2_config"] = {
                "operator": EM_OPERATOR,
                "chains": list(self._fase2_clients.keys()),
                "facilitator_url": FACILITATOR_URL,
            }

        if self.mode in ("preauth", "fase1") and self._sdk is not None:
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
