"""
Payment Dispatcher for Execution Market.

Routes payment operations based on EM_PAYMENT_MODE:
  - fase2: On-chain escrow via agent-signed pre-auth + gasless facilitator (DEFAULT, production)
  - fase1: Balance check at creation, 2 direct EIP-3009 settlements at approval (testing only)

ADR-001: In production, agents sign their own payments via X-Payment-Auth header.
The server never signs payment transactions unless EM_SERVER_SIGNING=true (testing only).
All backends go through the Ultravioleta Facilitator and are GASLESS for agents and workers.
"""

import os
import json
import time
import asyncio
import logging
import threading
from decimal import ROUND_CEILING, Decimal
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from integrations.x402.payment_events import log_payment_event

logger = logging.getLogger(__name__)

# Configuration
EM_PAYMENT_MODE = os.environ.get(
    "EM_PAYMENT_MODE", "fase2"
)  # "fase2" (default, production). "fase1" for local testing only.

# Escrow release mode: controls whether escrow releases to platform wallet (legacy)
# or directly to worker (trustless).
# "platform_release" (default): escrow receiver = platform wallet, then platform disburses
# "direct_release": escrow receiver = worker wallet, 1-TX release, fee collected separately
EM_ESCROW_MODE = os.environ.get("EM_ESCROW_MODE", "platform_release")

# --- SDK backend (EIP-3009 SDK) ---
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
        get_operator_address,
    )
except ImportError:
    SDK_AVAILABLE = False
    EMX402SDK = None  # type: ignore[assignment,misc]
    get_sdk = None  # type: ignore[assignment]
    verify_x402_payment = None  # type: ignore[assignment]
    PLATFORM_FEE_PERCENT = Decimal("0.13")
    EM_TREASURY = "YOUR_TREASURY_WALLET"
    FACILITATOR_URL = "https://facilitator.ultravioletadao.xyz"
    NETWORK_CONFIG = {}  # type: ignore[assignment]
    get_operator_address = lambda network: None  # type: ignore[assignment]  # noqa: E731

# --- fase2 backend (AdvancedEscrowClient from SDK, gasless via facilitator) ---
try:
    from uvd_x402_sdk.advanced_escrow import (
        AdvancedEscrowClient,
        PaymentInfo as EscrowPaymentInfo,
        TaskTier,
        TransactionResult,
    )

    FASE2_SDK_AVAILABLE = True
except ImportError:
    FASE2_SDK_AVAILABLE = False
    AdvancedEscrowClient = None  # type: ignore[assignment,misc]
    EscrowPaymentInfo = None  # type: ignore[assignment,misc]
    TaskTier = None  # type: ignore[assignment,misc]
    TransactionResult = None  # type: ignore[assignment,misc]

# EM PaymentOperator address (Base Mainnet). Fase 5: Credit card model fee split.
# StaticFeeCalculator(1300 BPS = 13%) auto-splits at release: worker 87%, operator 13%.
# Bounty = lock amount = what agent pays. Fee deducted from bounty, not added on top.
# distributeFees() flushes operator balance to EM treasury.
# Override via env var when deploying operators on additional chains.
# Legacy: 0x4661...2Cd9 (fase5-1150bps), 0x0303...cBe5 (fase4), 0xd514...df95 (fase3-clean)
EM_OPERATOR = os.environ.get(
    "EM_PAYMENT_OPERATOR", "0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb"
)

# Fase 5: max_fee_bps to allow on-chain fee calculator to deduct from escrow.
# Actual fee is 1300 BPS (13%). Set max=1800 for headroom if x402r enables protocol fee (up to 5%).
FASE5_MAX_FEE_BPS = 1800
FASE5_FEE_BPS = 1300


def compute_lock_amount(bounty: Decimal, fee_bps: int = FASE5_FEE_BPS) -> Decimal:
    """Credit-card formula: lock enough so worker gets >= bounty after on-chain fee split.

    The on-chain StaticFeeCalculator deducts ``fee_bps`` from the locked amount
    and sends the remainder to the worker.  To guarantee the worker receives at
    least ``bounty``, we must lock::

        lock = ceil(bounty * 10000 / (10000 - fee_bps))

    This matches the formula in ``deploy-payment-operator.ts`` (line 224).

    Args:
        bounty: The worker's expected bounty in USDC (human-readable, 6 decimals).
        fee_bps: Fee in basis points (default 1300 = 13%).

    Returns:
        The amount to lock in escrow, quantized to 6 USDC decimals (ROUND_CEILING).
    """
    return (bounty * Decimal(10000) / Decimal(10000 - fee_bps)).quantize(
        Decimal("0.000001"), rounding=ROUND_CEILING
    )


# Fee model: who absorbs the 13% on-chain fee?
# "credit_card" (default): bounty = lock amount. Fee deducted from bounty. Worker gets 87%.
# "agent_absorbs": lock amount = bounty / 0.87. Agent pays extra so worker gets ~100% of bounty.
EM_FEE_MODEL = os.environ.get("EM_FEE_MODEL", "credit_card")

# Escrow timing: when are funds locked?
# "lock_on_assignment" (default): agent pre-signs at creation, lock executes at assignment
# "lock_on_creation": agent signs and escrow locks immediately at task creation
EM_ESCROW_TIMING = os.environ.get("EM_ESCROW_TIMING", "lock_on_assignment")

# USDC contract on Base Mainnet (for distributeFees calls)
USDC_BASE_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# Function selector for distributeFees(address) — keccak256("distributeFees(address)")[:4]
_SELECTOR_DISTRIBUTE_FEES = "0x9413f25c"

# x402r ProtocolFeeConfig contract on Base (singleton, shared by all operators).
# BackTrack controls this via multisig with 7-day timelock. Max 5% (500 BPS).
# We read the current protocol fee dynamically so treasury math auto-adjusts.
PROTOCOL_FEE_CONFIG_ADDRESS = "0x59314674BAbb1a24Eb2704468a9cCdD50668a1C6"
BASE_RPC_URL = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")

# Function selectors (precomputed keccak256)
_SELECTOR_CALCULATOR = "0xce3e39c0"  # calculator()
_SELECTOR_FEE_BPS = "0xbf333f2c"  # FEE_BPS()

# Cache: {bps: int, expires: float}
_protocol_fee_cache: Dict[str, Any] = {"bps": 0, "expires": 0.0}
_CACHE_TTL = 300  # 5 minutes


def _get_operator_for_network(network: str) -> Optional[str]:
    """Resolve EM PaymentOperator address for a given network.

    Returns None for SVM networks (Solana) — they use Fase 1 only, no escrow.

    Priority:
    1. NETWORK_CONFIG[network]["operator"] — per-chain hardcoded address
    2. EM_PAYMENT_OPERATOR env var — global override
    3. EM_OPERATOR module default — Base Mainnet Fase 5 operator
    """
    # SVM networks (Solana) have no on-chain escrow or operator
    net_config = NETWORK_CONFIG.get(network, {})
    if net_config.get("network_type") == "svm":
        return None

    per_chain = get_operator_address(network)
    if per_chain:
        return per_chain
    return os.environ.get("EM_PAYMENT_OPERATOR", EM_OPERATOR)


async def _get_protocol_fee_bps() -> int:
    """Read x402r protocol fee from ProtocolFeeConfig on Base via RPC.

    BackTrack controls this contract (7-day timelock, 5% hard cap).
    Cached for 5 minutes to avoid spamming RPC.
    Returns 0 if chain is unreachable (fail-open for treasury).
    """
    now = time.time()
    if now < _protocol_fee_cache["expires"]:
        return _protocol_fee_cache["bps"]

    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Step 1: Read calculator() address from ProtocolFeeConfig
            resp = await client.post(
                BASE_RPC_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_call",
                    "params": [
                        {
                            "to": PROTOCOL_FEE_CONFIG_ADDRESS,
                            "data": _SELECTOR_CALCULATOR,
                        },
                        "latest",
                    ],
                },
            )
            result = resp.json().get("result", "0x" + "0" * 64)
            calculator_addr = "0x" + result[-40:]

            if calculator_addr == "0x" + "0" * 40:
                # No calculator set -> 0% protocol fee
                _protocol_fee_cache.update({"bps": 0, "expires": now + _CACHE_TTL})
                logger.debug("x402r protocol fee: 0 BPS (no calculator set)")
                return 0

            # Step 2: Read FEE_BPS() from the calculator (StaticFeeCalculator)
            resp2 = await client.post(
                BASE_RPC_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "eth_call",
                    "params": [
                        {"to": calculator_addr, "data": _SELECTOR_FEE_BPS},
                        "latest",
                    ],
                },
            )
            result2 = resp2.json().get("result", "0x0")
            fee_bps = int(result2, 16) if result2 and result2 != "0x" else 0

            # Cap at 500 (5% max, matching contract's MAX_PROTOCOL_FEE_BPS)
            fee_bps = min(fee_bps, 500)

            _protocol_fee_cache.update({"bps": fee_bps, "expires": now + _CACHE_TTL})
            logger.info("x402r protocol fee: %d BPS (read from chain)", fee_bps)
            return fee_bps

    except Exception as e:
        logger.warning(
            "Failed to read protocol fee from chain: %s. Using cached value %d BPS.",
            e,
            _protocol_fee_cache.get("bps", 0),
        )
        return _protocol_fee_cache.get("bps", 0)


# =============================================================================
# Helpers
# =============================================================================


def _is_valid_tx_id(val: Any) -> bool:
    """Check if a value looks like a valid transaction identifier (EVM or Solana)."""
    if not isinstance(val, str) or not val:
        return False
    # EVM: 0x-prefixed 66-char hex (32 bytes)
    if val.startswith("0x") and len(val) == 66:
        return True
    # Solana: Base58 signature, typically 87-88 chars, no 0x prefix
    if len(val) >= 80 and not val.startswith("0x"):
        import re

        if re.match(r"^[1-9A-HJ-NP-Za-km-z]+$", val):
            return True
    return False


def _extract_tx_hash(response: Any) -> Optional[str]:
    """Extract tx hash from various SDK response formats (model objects or dicts)."""
    if response is None:
        return None

    # Try get_transaction_hash() method first (SDK model objects)
    getter = getattr(response, "get_transaction_hash", None)
    if callable(getter):
        try:
            val = getter()
            if _is_valid_tx_id(val):
                return val
        except Exception:
            pass

    # Try attribute access
    for attr in ("transaction_hash", "tx_hash", "transaction", "hash"):
        val = getattr(response, attr, None)
        if _is_valid_tx_id(val):
            return val

    # Try dict access
    if isinstance(response, dict):
        for key in ("transaction_hash", "tx_hash", "transaction", "hash"):
            val = response.get(key)
            if _is_valid_tx_id(val):
                return val

    return None


def _compute_treasury_remainder(
    bounty_amount: Decimal, total_locked: Decimal, on_chain_fee_bps: int = 0
) -> Decimal:
    """
    Compute the treasury fee as the remainder after paying the worker.

    .. note::
        **ADVISORY ONLY** — this function provides an off-chain *estimate*
        for logging and analytics.  The on-chain ``StaticFeeCalculator``
        (1300 BPS) is the authoritative source of truth for the actual fee
        split at escrow release time.

    Treasury receives whatever is left in the platform wallet after the worker
    gets their full bounty. This naturally handles any on-chain protocol fee
    deduction from x402r -- if the escrow takes a cut, the treasury amount
    shrinks accordingly instead of the transfer failing.

    Args:
        bounty_amount: The worker's bounty (they always get this in full).
        total_locked: The total amount originally locked in escrow
                      (bounty + platform fee).
        on_chain_fee_bps: Protocol fee in basis points, read dynamically from
                          ProtocolFeeConfig on Base via ``_get_protocol_fee_bps()``.
                          Defaults to 0 (no on-chain fee).

    Returns:
        The amount to send to treasury (>= 0, quantized to 6 decimals).
    """
    on_chain_fee_rate = Decimal(on_chain_fee_bps) / Decimal(10000)
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


def _is_server_signing_enabled() -> bool:
    """Check if server-side signing is enabled (testing only).

    EM_SERVER_SIGNING=true enables the server to sign payment transactions
    using WALLET_PRIVATE_KEY. This is for internal testing ONLY.

    In production, this must be false (or unset). External agents sign their
    own payments — the server never touches funds.
    """
    return os.environ.get("EM_SERVER_SIGNING", "").lower() == "true"


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


def _get_server_signing_key() -> str:
    """Get the platform private key for server-side signing (testing only).

    Raises:
        RuntimeError: If server signing is disabled or key is not set.
    """
    if not _is_server_signing_enabled():
        raise RuntimeError(
            "Server-side signing is disabled (EM_SERVER_SIGNING != true). "
            "External agents must sign their own payments via X-Payment-Auth header. "
            "Set EM_SERVER_SIGNING=true for testing only."
        )
    pk = os.environ.get("WALLET_PRIVATE_KEY")
    if not pk:
        raise RuntimeError("WALLET_PRIVATE_KEY not set — cannot sign payments")
    return pk


# =============================================================================
# PaymentDispatcher
# =============================================================================


class PaymentDispatcher:
    """
    Routes payment operations to the correct backend based on EM_PAYMENT_MODE.

    Provides a uniform interface for authorize, release, and refund.
    """

    def __init__(self, mode: Optional[str] = None):
        self.mode = (mode or EM_PAYMENT_MODE).lower()

        if self.mode not in ("fase1", "fase2"):
            logger.warning(
                "Unknown EM_PAYMENT_MODE '%s', falling back to 'fase2'",
                self.mode,
            )
            self.mode = "fase2"

        if self.mode == "fase1":
            logger.warning(
                "EM_PAYMENT_MODE='fase1' is for local testing only (ADR-001). "
                "Production uses fase2 with agent-signed X-Payment-Auth headers.",
            )

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

        if self.mode == "fase1" and not SDK_AVAILABLE:
            logger.error(
                "fase1 mode requested but uvd-x402-sdk not available. "
                "Payment operations will fail.",
            )

        # Escrow release mode: "platform_release" (legacy) or "direct_release" (trustless)
        self.escrow_mode = os.environ.get("EM_ESCROW_MODE", EM_ESCROW_MODE).lower()
        if self.escrow_mode not in ("platform_release", "direct_release"):
            logger.warning(
                "Unknown EM_ESCROW_MODE '%s', falling back to 'platform_release'",
                self.escrow_mode,
            )
            self.escrow_mode = "platform_release"

        # Lazy-initialized backend instances
        self._sdk: Optional[Any] = None
        # Multi-wallet: separate client caches per wallet label
        # Key: (chain_id, wallet_label) → AdvancedEscrowClient
        self._fase2_clients: Dict[tuple, Any] = {}

        logger.info(
            "PaymentDispatcher initialized: mode=%s, escrow_mode=%s",
            self.mode,
            self.escrow_mode,
        )

    def _get_sdk(self) -> "EMX402SDK":
        """Lazy-init the SDK backend."""
        if self._sdk is None:
            self._sdk = get_sdk()
        return self._sdk

    def _get_fase2_client(
        self,
        network: str = "base",
    ) -> "AdvancedEscrowClient":
        """Lazy-init an AdvancedEscrowClient for the given network.

        Uses WALLET_PRIVATE_KEY for signing. Only works when
        EM_SERVER_SIGNING=true (testing mode). In production, agents sign
        their own payments — this path is not used.

        Args:
            network: Target blockchain network (e.g., "base", "ethereum").

        Returns:
            AdvancedEscrowClient configured with the platform wallet key.

        Raises:
            RuntimeError: If server signing is disabled.
        """
        config = NETWORK_CONFIG.get(network, {})
        chain_id = config.get("chain_id", 8453)
        cache_key = chain_id

        if cache_key not in self._fase2_clients:
            pk = _get_server_signing_key()  # raises if EM_SERVER_SIGNING != true
            rpc_url = config.get("rpc_url", "https://mainnet.base.org")
            operator = _get_operator_for_network(network)
            addr = _get_platform_address()

            self._fase2_clients[cache_key] = AdvancedEscrowClient(
                private_key=pk,
                facilitator_url=FACILITATOR_URL,
                rpc_url=rpc_url,
                chain_id=chain_id,
                operator_address=operator,
            )
            logger.info(
                "Fase2 AdvancedEscrowClient initialized (SERVER_SIGNING mode): "
                "chain=%d, wallet=%s, operator=%s",
                chain_id,
                addr[:10] + "...",
                operator[:10] if operator else "None",
            )

        return self._fase2_clients[cache_key]

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
        balance_check_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Authorize (lock or verify) a payment for a task.

        fase2 mode: Locks escrow via server signing (requires EM_SERVER_SIGNING=true).
        fase1 mode: Checks agent's on-chain balance (no funds move). Testing only.

        Note: In production, agents sign their own payments. Server-side signing
        (fase2 via this method) is only for testing with EM_SERVER_SIGNING=true.

        Args:
            task_id: Unique task identifier
            receiver: Agent address (used for phase context)
            amount_usdc: Total amount including fee (bounty + platform fee)
            strategy: Unused (kept for API compatibility)
            x_payment_header: X-Payment header from agent request
            agent_address: Agent wallet address (for fase1 balance check)
            network: Payment network
            token: Payment token (default: USDC)
            balance_check_only: Force balance-check mode regardless of dispatcher mode.
                Used for direct_release at task creation (escrow lock deferred to assignment).

        Returns:
            Uniform dict with success, tx_hash, mode, escrow_status, payment_info, error.
        """
        try:
            if balance_check_only:
                return await self._authorize_fase1(
                    task_id, amount_usdc, agent_address, network, token
                )
            if self.mode == "fase2":
                return await self._authorize_fase2(task_id, amount_usdc, network, token)
            else:
                return await self._authorize_fase1(
                    task_id, amount_usdc, agent_address, network, token
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
        AuthCaptureEscrow contract. Fully gasless.

        Requires EM_SERVER_SIGNING=true (testing only). In production, agents
        sign their own escrow operations via X-Payment-Auth header.

        Receiver = platform wallet. On release, we disburse to worker + fee.
        """
        network = network or "base"
        client = self._get_fase2_client(network)
        platform_address = _get_platform_address()

        # Total to lock = credit-card formula (worker gets >= bounty after 13% deduction)
        total_amount = compute_lock_amount(amount_usdc)

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
        # Ethereum L1 needs longer timeout (blocks ~12s vs ~2s on L2s)
        config_chain = NETWORK_CONFIG.get(network, {})
        chain_id_check = config_chain.get("chain_id", 8453)
        if chain_id_check == 1:  # Ethereum mainnet — 900s margin over Facilitator 600s
            auth_result = await asyncio.to_thread(
                self._authorize_with_extended_timeout, client, pi, 900
            )
        else:
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
            "payer_address": client.payer,
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
    # Trustless Direct Release (EM_ESCROW_MODE=direct_release)
    # =========================================================================

    @staticmethod
    def _authorize_with_extended_timeout(client, pi, timeout_seconds: int = 600):
        """Authorize escrow with extended HTTP timeout for slow chains (Ethereum L1)."""
        return PaymentDispatcher._call_with_extended_timeout(
            client.authorize, pi, timeout_seconds
        )

    @staticmethod
    def _call_with_extended_timeout(func, pi, timeout_seconds: int = 600):
        """Call an SDK method with extended HTTP timeout for slow chains.

        The SDK hardcodes httpx.post timeout=120. For Ethereum L1 (blocks ~12s),
        the Facilitator may need up to 300s+ to confirm the TX on-chain. This
        wrapper monkey-patches httpx.post temporarily.
        """
        import httpx as _httpx

        _original_post = _httpx.post

        logger.info(
            "Applying extended timeout (%ds) for facilitator call (func=%s)",
            timeout_seconds,
            getattr(func, "__name__", str(func)),
        )

        def _patched_post(*args, **kwargs):
            old_timeout = kwargs.get("timeout")
            kwargs["timeout"] = timeout_seconds
            logger.info(
                "httpx.post monkey-patch: overriding timeout %s -> %ds",
                old_timeout,
                timeout_seconds,
            )
            resp = _original_post(*args, **kwargs)
            if resp.status_code >= 400:
                logger.error(
                    "Facilitator returned HTTP %d for slow-chain call: %s",
                    resp.status_code,
                    resp.text[:500],
                )
            else:
                logger.info(
                    "Facilitator responded HTTP %d for slow-chain call (%d bytes)",
                    resp.status_code,
                    len(resp.text),
                )
            return resp

        try:
            _httpx.post = _patched_post
            return func(pi)
        finally:
            _httpx.post = _original_post

    async def authorize_escrow_for_worker(
        self,
        task_id: str,
        agent_address: str,
        worker_address: str,
        bounty_usdc: Decimal,
        network: Optional[str] = None,
        token: str = "USDC",
    ) -> Dict[str, Any]:
        """
        Lock bounty in escrow with worker as direct receiver (trustless).

        Fase 5: On-chain fee calculator (StaticFeeCalculator 1300 BPS) splits at release.
        Fee model controlled by EM_FEE_MODEL:
        - "credit_card": bounty = lock amount. Worker gets 87%. Agent pays bounty only.
        - "agent_absorbs": lock = bounty/0.87. Worker gets ~100%. Agent pays bounty + fee.

        Requires EM_SERVER_SIGNING=true (testing only). In production, agents sign
        their own escrow operations.

        Args:
            task_id: Task identifier.
            agent_address: Agent's wallet address (for metadata/logging).
            worker_address: Worker's wallet address (escrow receiver).
            bounty_usdc: The bounty amount (interpretation depends on EM_FEE_MODEL).
            network: Payment network (default: base).
            token: Payment token (default: USDC).

        Returns:
            Dict with success, tx_hash, escrow_status, etc.
        """
        network = network or "base"
        client = self._get_fase2_client(network)

        actual_payer = client.payer
        logger.info(
            "authorize_escrow_for_worker (SERVER_SIGNING): task=%s, payer=%s, worker=%s",
            task_id,
            actual_payer[:10] + "...",
            worker_address[:10] + "...",
        )

        fee_model = EM_FEE_MODEL

        if fee_model == "agent_absorbs":
            # Agent pays extra so worker gets ~100% of bounty after 13% fee deduction.
            lock_amount = compute_lock_amount(bounty_usdc)
        else:
            # credit_card (default): bounty IS the lock amount. Fee deducted on-chain.
            lock_amount = bounty_usdc

        # Convert to atomic units (6 decimals for USDC)
        config = NETWORK_CONFIG.get(network, {})
        decimals = 6
        for t_info in (config.get("tokens", {}).get(token, {}),):
            if t_info:
                decimals = t_info.get("decimals", 6)
        amount_atomic = int(lock_amount * Decimal(10**decimals))

        # Determine tier from bounty
        tier = TaskTier.MICRO
        if bounty_usdc >= Decimal("100"):
            tier = TaskTier.ENTERPRISE
        elif bounty_usdc >= Decimal("25"):
            tier = TaskTier.PREMIUM
        elif bounty_usdc >= Decimal("5"):
            tier = TaskTier.STANDARD

        # Build PaymentInfo with WORKER as receiver (trustless)
        # Fase 5: max_fee_bps allows the on-chain fee calculator to deduct
        pi = await asyncio.to_thread(
            client.build_payment_info,
            receiver=worker_address,
            amount=amount_atomic,
            tier=tier,
            max_fee_bps=FASE5_MAX_FEE_BPS,
        )

        logger.info(
            "trustless: Built PaymentInfo for task %s: receiver=%s, amount=%d, "
            "bounty=%s, fee_model=%s",
            task_id,
            worker_address[:10],
            amount_atomic,
            bounty_usdc,
            fee_model,
        )

        # Authorize (lock funds) via facilitator — gasless
        # Ethereum L1 needs longer timeout (blocks ~12s vs ~2s on L2s)
        # 900s gives margin above the Facilitator's 600s TxWatcher timeout
        config_chain = NETWORK_CONFIG.get(network, {})
        chain_id = config_chain.get("chain_id", 8453)
        if chain_id == 1:  # Ethereum mainnet
            auth_result = await asyncio.to_thread(
                self._authorize_with_extended_timeout, client, pi, 900
            )
        else:
            auth_result = await asyncio.to_thread(client.authorize, pi)

        if not auth_result.success:
            # On-chain fallback: if authorize timed out, the TX may have mined
            # despite the HTTP timeout. Query escrow state to verify.
            is_timeout = "timed out" in (auth_result.error or "").lower()
            if is_timeout:
                logger.warning(
                    "trustless: Authorize timed out for task %s on %s "
                    "— checking on-chain escrow state...",
                    task_id,
                    network,
                )
                try:
                    await asyncio.sleep(20)  # give TX time to mine
                    state = await asyncio.to_thread(client.query_escrow_state, pi)
                    capturable = int(state.get("capturableAmount", "0"))
                    logger.info(
                        "trustless: Escrow state after authorize timeout: "
                        "capturableAmount=%d, full=%s",
                        capturable,
                        state,
                    )
                    if capturable > 0:
                        logger.info(
                            "trustless: Escrow capturableAmount=%d > 0 — "
                            "authorize confirmed on-chain despite timeout "
                            "for task %s",
                            capturable,
                            task_id,
                        )
                        # Override auth_result with success
                        if TransactionResult is not None:
                            auth_result = TransactionResult(
                                success=True,
                                transaction_hash="timeout-verified-onchain",
                                error=None,
                            )
                        else:
                            # SDK class not available — create a mock
                            class _MockResult:
                                success = True
                                transaction_hash = "timeout-verified-onchain"
                                error = None
                                gas_used = None

                            auth_result = _MockResult()
                        await log_payment_event(
                            task_id=task_id,
                            event_type="escrow_authorize",
                            status="timeout_recovered",
                            tx_hash="timeout-verified-onchain",
                            from_address=agent_address,
                            to_address=worker_address,
                            amount_usdc=lock_amount,
                            network=network,
                            token=token,
                            metadata={
                                "mode": "fase2",
                                "escrow_mode": "direct_release",
                                "timeout_recovery": True,
                                "escrow_state": state,
                            },
                        )
                except Exception as state_err:
                    logger.error(
                        "trustless: Escrow state query failed after authorize "
                        "timeout for task %s: %s",
                        task_id,
                        state_err,
                    )

        if not auth_result.success:
            await log_payment_event(
                task_id=task_id,
                event_type="escrow_authorize",
                status="failed",
                amount_usdc=lock_amount,
                network=network,
                token=token,
                error=auth_result.error,
                metadata={
                    "mode": "fase2",
                    "escrow_mode": "direct_release",
                    "receiver": worker_address,
                },
            )
            return {
                "success": False,
                "tx_hash": None,
                "mode": "fase2",
                "escrow_mode": "direct_release",
                "escrow_status": "authorize_failed",
                "payment_info": None,
                "payment_info_serialized": None,
                "error": f"Escrow authorize failed: {auth_result.error}",
            }

        escrow_tx = auth_result.transaction_hash

        # Serialize PaymentInfo for DB persistence
        payment_info_serialized = {
            "mode": "fase2",
            "escrow_mode": "direct_release",
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
            "worker_address": worker_address,
            "bounty_usdc": str(bounty_usdc),
            "lock_amount_usdc": str(lock_amount),
            "fee_model": fee_model,
            "payer_address": client.payer,
        }

        await log_payment_event(
            task_id=task_id,
            event_type="escrow_authorize",
            status="success",
            tx_hash=escrow_tx,
            from_address=agent_address,
            to_address=worker_address,
            amount_usdc=lock_amount,
            network=network,
            token=token,
            metadata={
                "mode": "fase2",
                "escrow_mode": "direct_release",
                "fee_model": fee_model,
                "bounty": str(bounty_usdc),
                "salt": pi.salt[:18],
            },
        )

        logger.info(
            "trustless: Bounty locked in escrow (%s): task=%s, "
            "receiver=%s, lock_amount=%s, tx=%s",
            fee_model,
            task_id,
            worker_address[:10],
            lock_amount,
            escrow_tx,
        )

        return {
            "success": True,
            "tx_hash": escrow_tx,
            "fee_method": "on_chain_fee_calculator",
            "fee_model": fee_model,
            "mode": "fase2",
            "escrow_mode": "direct_release",
            "escrow_status": "deposited",
            "payment_info": pi,
            "payment_info_serialized": payment_info_serialized,
            "payer_address": client.payer,
            "worker_address": worker_address,
            "bounty_usdc": str(bounty_usdc),
            "lock_amount_usdc": str(lock_amount),
            "error": None,
        }

    # =========================================================================
    # Agent-Signed Escrow (ADR-001 Phase 2)
    # =========================================================================

    @staticmethod
    def validate_agent_preauth(
        payload_json: str,
        *,
        network: Optional[str] = None,
        expected_payer: Optional[str] = None,
        expected_amount_atomic: Optional[str] = None,
    ) -> dict:
        """Validate an agent's pre-signed X-Payment-Auth payload.

        The payload is the JSON that the agent would normally send to the
        Facilitator /settle endpoint. Validates structure AND — when network,
        expected_payer, or expected_amount_atomic are provided — verifies that
        the payload targets the correct operator, token, amount, and payer
        registered in NETWORK_CONFIG (SC-001 hardening).

        Args:
            payload_json: Raw JSON string from the X-Payment-Auth header.
            network: Payment network name (e.g. "base"). When provided, validates
                operator and token against NETWORK_CONFIG.
            expected_payer: Authenticated agent's wallet address. When provided,
                validates authorization.from matches.
            expected_amount_atomic: Expected lock amount in atomic units (e.g. "5000000"
                for $5 USDC). When provided, validates paymentInfo.maxAmount matches.

        Returns:
            Parsed dict with the payload structure.

        Raises:
            ValueError: If the payload is malformed, missing required fields,
                or fails security validation against NETWORK_CONFIG.
        """
        try:
            data = json.loads(payload_json)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"X-Payment-Auth is not valid JSON: {e}")

        # Validate top-level structure
        if not isinstance(data, dict):
            raise ValueError("X-Payment-Auth must be a JSON object")

        payload = data.get("payload")
        if not payload or not isinstance(payload, dict):
            raise ValueError("X-Payment-Auth missing 'payload' object")

        # Validate authorization fields
        auth = payload.get("authorization")
        if not auth or not isinstance(auth, dict):
            raise ValueError("X-Payment-Auth missing 'payload.authorization'")
        required_auth_fields = [
            "from",
            "to",
            "value",
            "validAfter",
            "validBefore",
            "nonce",
        ]
        missing = [f for f in required_auth_fields if f not in auth]
        if missing:
            raise ValueError(f"X-Payment-Auth authorization missing fields: {missing}")

        # Validate signature
        if not payload.get("signature"):
            raise ValueError("X-Payment-Auth missing 'payload.signature'")

        # Validate paymentInfo (may be partially filled — receiver added at assignment)
        pi = payload.get("paymentInfo")
        if not pi or not isinstance(pi, dict):
            raise ValueError("X-Payment-Auth missing 'payload.paymentInfo'")
        required_pi_fields = ["operator", "token", "maxAmount"]
        missing_pi = [f for f in required_pi_fields if f not in pi]
        if missing_pi:
            raise ValueError(f"X-Payment-Auth paymentInfo missing fields: {missing_pi}")

        # ── SC-001: Validate against NETWORK_CONFIG ──────────────────
        # Prevents attacker from routing funds to a malicious operator
        # or unauthorized token contract.
        if network is not None:
            cfg = NETWORK_CONFIG.get(network)
            if not cfg:
                raise ValueError(f"Unknown payment network: {network}")

            # Validate operator matches expected for this network
            expected_operator = cfg.get("operator") or (
                cfg.get("x402r_infra", {}).get("operator")
            )
            if (
                expected_operator
                and pi["operator"].lower() != expected_operator.lower()
            ):
                raise ValueError(
                    f"paymentInfo.operator must be {expected_operator} for network {network}"
                )

            # Validate token is in the network's allowlist
            allowed_tokens = {
                t.get("address", "").lower()
                for t in cfg.get("tokens", {}).values()
                if t.get("address")
            }
            if allowed_tokens and pi["token"].lower() not in allowed_tokens:
                raise ValueError(
                    f"paymentInfo.token {pi['token']} not in allowlist for network {network}"
                )

            # Validate authorization.to is the correct tokenCollector
            expected_collector = cfg.get("x402r_infra", {}).get(
                "tokenCollector"
            ) or cfg.get("token_collector")
            if expected_collector and auth["to"].lower() != expected_collector.lower():
                raise ValueError(
                    f"authorization.to must be tokenCollector {expected_collector} "
                    f"for network {network}"
                )

        # Validate payer matches authenticated agent wallet
        if expected_payer is not None:
            if auth["from"].lower() != expected_payer.lower():
                raise ValueError(
                    "authorization.from must match the authenticated agent wallet"
                )

        # Validate amount matches expected total (bounty = lock amount in credit_card model)
        if expected_amount_atomic is not None:
            if str(pi["maxAmount"]) != str(expected_amount_atomic):
                raise ValueError(
                    f"paymentInfo.maxAmount {pi['maxAmount']} does not match "
                    f"expected {expected_amount_atomic}"
                )

        return data

    async def relay_agent_auth_to_facilitator(
        self,
        payload: dict,
        worker_address: str,
        network: str = "base",
    ) -> Dict[str, Any]:
        """Relay an agent's pre-signed escrow auth to the Facilitator.

        The server fills in the receiver (worker address) and network-specific
        contract addresses, then forwards the agent's signed payload directly
        to the Facilitator /settle endpoint. The server does NOT sign anything.

        Args:
            payload: Parsed X-Payment-Auth payload (from validate_agent_preauth).
            worker_address: Worker's wallet address (escrow receiver).
            network: Payment network.

        Returns:
            Dict with success, tx_hash, error.
        """
        import httpx

        config = NETWORK_CONFIG.get(network, {})
        operator = _get_operator_for_network(network) or EM_OPERATOR
        chain_id = config.get("chain_id", 8453)

        # Fill in receiver and network-specific fields
        inner = payload.get("payload", {})
        pi = inner.get("paymentInfo", {})

        # SC-009: Assert the agent's signed operator matches our expected operator
        # for this network. Prevents agents from routing funds through rogue operators.
        signed_operator = (pi.get("operator") or "").lower()
        expected_operator = operator.lower()
        if signed_operator and signed_operator != expected_operator:
            logger.warning(
                "SC-009 REJECT: agent signed operator=%s but expected=%s for network=%s",
                signed_operator,
                expected_operator,
                network,
            )
            return {
                "success": False,
                "tx_hash": None,
                "escrow_status": "operator_mismatch",
                "error": (
                    f"Operator mismatch: signed {signed_operator[:10]}... "
                    f"does not match expected {expected_operator[:10]}... for {network}"
                ),
            }

        pi["receiver"] = worker_address

        # Ensure paymentRequirements exists and is populated
        pr = payload.get("paymentRequirements", {})
        pr["scheme"] = "escrow"
        pr["network"] = f"eip155:{chain_id}"
        pr["payTo"] = worker_address
        pr["maxAmountRequired"] = str(pi.get("maxAmount", "0"))
        pr["asset"] = config.get("tokens", {}).get("USDC", {}).get("address", "")

        # Fill extra with contract addresses
        escrow_address = config.get("escrow", config.get("escrow_address", ""))
        x402r = config.get("x402r_infra", {})
        token_collector = x402r.get("tokenCollector", config.get("token_collector", ""))
        pr.setdefault("extra", {})
        pr["extra"]["escrowAddress"] = escrow_address
        pr["extra"]["operatorAddress"] = operator
        pr["extra"]["tokenCollector"] = token_collector

        payload["paymentRequirements"] = pr
        payload.setdefault("x402Version", 2)
        payload.setdefault("scheme", "escrow")

        # Log the outbound payload structure (with nonce, without full signature)
        auth_obj = inner.get("authorization", {})
        sig_hex = inner.get("signature", "")
        sig_preview = sig_hex[:20] + "..." if len(sig_hex) > 20 else sig_hex
        debug_payload = {
            "x402Version": payload.get("x402Version"),
            "scheme": payload.get("scheme"),
            "payload.authorization.from": auth_obj.get("from"),
            "payload.authorization.to": auth_obj.get("to"),
            "payload.authorization.value": auth_obj.get("value"),
            "payload.authorization.validAfter": auth_obj.get("validAfter"),
            "payload.authorization.validBefore": auth_obj.get("validBefore"),
            "payload.authorization.nonce": auth_obj.get("nonce"),
            "payload.signature_preview": sig_preview,
            "payload.paymentInfo.operator": pi.get("operator"),
            "payload.paymentInfo.receiver": pi.get("receiver"),
            "payload.paymentInfo.token": pi.get("token"),
            "payload.paymentInfo.maxAmount": pi.get("maxAmount"),
            "paymentRequirements.scheme": pr.get("scheme"),
            "paymentRequirements.network": pr.get("network"),
            "paymentRequirements.payTo": pr.get("payTo"),
            "paymentRequirements.extra.escrowAddress": pr.get("extra", {}).get(
                "escrowAddress"
            ),
            "paymentRequirements.extra.operatorAddress": pr.get("extra", {}).get(
                "operatorAddress"
            ),
            "paymentRequirements.extra.tokenCollector": pr.get("extra", {}).get(
                "tokenCollector"
            ),
        }
        logger.info("Relaying agent auth to facilitator: %s", debug_payload)

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{FACILITATOR_URL}/settle",
                    json=payload,
                )
                logger.info(
                    "Facilitator /settle response: status=%d, body=%s",
                    response.status_code,
                    response.text[:500],
                )
                result = response.json()

            if result.get("success"):
                tx_hash = result.get("transaction", {}).get("hash") or result.get(
                    "txHash", ""
                )
                logger.info(
                    "Agent-signed escrow locked: network=%s, worker=%s, tx=%s",
                    network,
                    worker_address[:10] + "...",
                    tx_hash[:16] + "..." if tx_hash else "none",
                )
                return {
                    "success": True,
                    "tx_hash": tx_hash,
                    "escrow_status": "locked",
                    "error": None,
                }
            else:
                error = result.get(
                    "error",
                    result.get("message", result.get("detail", "Facilitator rejected")),
                )
                logger.warning(
                    "Agent-signed escrow lock failed: network=%s, status=%d, error=%s, full_response=%s",
                    network,
                    response.status_code,
                    error,
                    response.text[:500],
                )
                return {
                    "success": False,
                    "tx_hash": None,
                    "escrow_status": "lock_failed",
                    "error": str(error),
                }
        except Exception as e:
            logger.error("Failed to relay agent auth to facilitator: %s", e)
            return {
                "success": False,
                "tx_hash": None,
                "escrow_status": "lock_failed",
                "error": str(e),
            }

    def store_preauth(
        self,
        task_id: str,
        payload_json: str,
        valid_before: int,
        network: str = "base",
    ) -> Dict[str, Any]:
        """Store an agent's pre-signed auth for deferred escrow lock (Mode B).

        The pre-auth is stored in the escrows table metadata and executed
        later when a worker is assigned to the task.

        Args:
            task_id: Task identifier.
            payload_json: Raw X-Payment-Auth JSON string.
            valid_before: Unix timestamp when the pre-auth expires.
            network: Payment network.

        Returns:
            Dict with success, escrow_status.
        """
        # Validate valid_before is sane (must be future, max 14 days out)
        now = int(time.time())
        if valid_before <= now:
            raise ValueError(
                f"valid_before ({valid_before}) must be in the future (now={now})"
            )
        max_valid_before = now + 86400 * 14  # 14 days
        if valid_before > max_valid_before:
            raise ValueError(
                f"valid_before ({valid_before}) exceeds 14-day maximum ({max_valid_before})"
            )

        parsed = json.loads(payload_json)
        agent_address = (
            parsed.get("payload", {}).get("authorization", {}).get("from", "")
        )
        amount_atomic = (
            parsed.get("payload", {}).get("paymentInfo", {}).get("maxAmount", "0")
        )
        amount_usdc = str(Decimal(str(amount_atomic)) / Decimal(10**6))

        metadata = {
            "payment_mode": "fase2",
            "escrow_timing": "lock_on_assignment",
            "preauth_signature": payload_json,
            "preauth_valid_before": valid_before,
            "network": network,
            "agent_address": agent_address,
        }

        # Store via DB — uses _insert_escrow_record from _helpers or direct insert.
        # The escrow record is created with status=pending_assignment.
        try:
            import db

            client = db.get_client()
            client.table("escrows").insert(
                {
                    "task_id": task_id,
                    "status": "pending_assignment",
                    "total_amount_usdc": amount_usdc,
                    "metadata": metadata,
                }
            ).execute()
        except Exception as e:
            logger.error("Failed to store pre-auth for task %s: %s", task_id, e)
            return {
                "success": False,
                "escrow_status": "store_failed",
                "error": str(e),
            }

        logger.info(
            "Stored pre-auth for task %s: agent=%s, validBefore=%d, network=%s",
            task_id,
            agent_address[:10] + "..." if agent_address else "unknown",
            valid_before,
            network,
        )

        return {
            "success": True,
            "escrow_status": "pending_assignment",
            "error": None,
        }

    async def release_direct_to_worker(
        self,
        task_id: str,
        network: Optional[str] = None,
        token: str = "USDC",
    ) -> Dict[str, Any]:
        """
        Release escrow directly to worker. Fully trustless.

        Fase 5: The on-chain fee calculator auto-splits at release.
        Fee model (EM_FEE_MODEL) determines what worker/agent pays:
        - credit_card: worker gets 87% of bounty, agent pays bounty only
        - agent_absorbs: worker gets ~100% of bounty, agent paid bounty + fee
        Single TX settlement.

        Args:
            task_id: Task identifier.
            network: Payment network.
            token: Payment token.

        Returns:
            Dict with success, release_tx_hash, method, fee_distribute_tx, etc.
        """
        network = network or "base"

        # Reconstruct PaymentInfo from DB
        pi, pi_meta = await self._reconstruct_fase2_state(task_id)
        if pi is None:
            return {
                "success": False,
                "tx_hash": None,
                "mode": "fase2",
                "escrow_mode": "direct_release",
                "error": (
                    f"Cannot release task {task_id}: escrow payment state not found. "
                    "The payment_info metadata may be missing from the escrows table."
                ),
            }

        stored_network = pi_meta.get("network", network)

        # Single TX: release from escrow directly to worker via facilitator HTTP
        # No private key needed — the Facilitator pays gas and executes on-chain.
        logger.info(
            "trustless: Releasing escrow for task %s directly to worker via facilitator HTTP...",
            task_id,
        )
        config_chain = NETWORK_CONFIG.get(stored_network, {})
        chain_id = config_chain.get("chain_id", 8453)
        operator = _get_operator_for_network(stored_network) or EM_OPERATOR
        escrow_address = config_chain.get(
            "escrow", config_chain.get("escrow_address", "")
        )
        x402r_infra = config_chain.get("x402r_infra", {})
        token_collector = x402r_infra.get("tokenCollector", "")

        # Build PaymentInfo dict for the Facilitator
        pi_dict = {
            "operator": pi.operator,
            "receiver": pi.receiver,
            "token": pi.token,
            "maxAmount": str(pi.max_amount),
            "preApprovalExpiry": pi.pre_approval_expiry,
            "authorizationExpiry": pi.authorization_expiry,
            "refundExpiry": pi.refund_expiry,
            "minFeeBps": pi.min_fee_bps,
            "maxFeeBps": pi.max_fee_bps,
            "feeReceiver": pi.fee_receiver,
            "salt": pi.salt,
        }

        # Determine payer (agent wallet) — required by Facilitator for release.
        # Sources (in priority order):
        # 1. pi_meta["payer"] — set by _reconstruct_fase2_state from payment_info
        # 2. pi_meta["agent_address"] — set at assign time from auth.wallet_address
        # 3. Look up task.agent_id if it's a wallet address
        payer = pi_meta.get("payer", "")
        if not payer or not payer.startswith("0x") or len(payer) != 42:
            payer = pi_meta.get("agent_address", "")
        if not payer or not payer.startswith("0x") or len(payer) != 42:
            try:
                import supabase_client as db_mod

                task_data = await db_mod.get_task(task_id)
                if task_data:
                    aid = task_data.get("agent_id", "")
                    if aid.startswith("0x") and len(aid) == 42:
                        payer = aid
            except Exception as e:
                logger.warning("Could not resolve payer for task %s: %s", task_id, e)
        if not payer or not payer.startswith("0x") or len(payer) != 42:
            logger.error(
                "CRITICAL: Cannot determine payer wallet for task %s release. "
                "The agent must include 'payer' in payment_info when assigning.",
                task_id,
            )
            return {
                "success": False,
                "tx_hash": None,
                "mode": "fase2",
                "escrow_mode": "direct_release",
                "error": (
                    "Cannot release: payer wallet unknown. "
                    "Agent must include 'payer' (wallet address) in payment_info."
                ),
            }

        release_payload = {
            "x402Version": 2,
            "scheme": "escrow",
            "action": "release",
            "payload": {
                "paymentInfo": pi_dict,
                "payer": payer,
                "amount": str(pi.max_amount),
            },
            "paymentRequirements": {
                "scheme": "escrow",
                "network": f"eip155:{chain_id}",
                "extra": {
                    "escrowAddress": escrow_address,
                    "operatorAddress": operator,
                    "tokenCollector": token_collector,
                },
            },
        }

        logger.info(
            "trustless: Release payload for task %s: payer=%s, receiver=%s, amount=%s, network=%s",
            task_id,
            payer[:10] + "..." if payer else "unknown",
            pi.receiver[:10] + "..." if pi.receiver else "unknown",
            pi.max_amount,
            stored_network,
        )

        import httpx

        try:
            async with httpx.AsyncClient(timeout=300) as http_client:
                response = await http_client.post(
                    f"{FACILITATOR_URL}/settle",
                    json=release_payload,
                )
                logger.info(
                    "Facilitator /settle release response: status=%d, body=%s",
                    response.status_code,
                    response.text[:500],
                )
                release_data = response.json()
        except Exception as e:
            logger.error("Facilitator release HTTP failed for task %s: %s", task_id, e)
            release_data = {"success": False, "errorReason": str(e)}

        # Convert to SDK-compatible result for the rest of the flow
        class _ReleaseResult:
            def __init__(self, data: dict):
                self.success = data.get("success", False)
                self.transaction_hash = (
                    data.get("transaction", {}).get("hash")
                    if isinstance(data.get("transaction"), dict)
                    else data.get("transaction", data.get("txHash", ""))
                )
                self.error = (
                    data.get("errorReason", data.get("error"))
                    if not self.success
                    else None
                )
                self.gas_used = 0

        release_result = _ReleaseResult(release_data)

        if not release_result.success:
            # ------------------------------------------------------------------
            # Timeout fallback: If the release timed out, the Facilitator may
            # have completed the TX on-chain but the HTTP response was cut by a
            # proxy (observed on Ethereum L1 at ~90s).  Before reporting failure
            # we query the escrow state.  If capturableAmount == 0 the release
            # went through.
            # ------------------------------------------------------------------
            is_timeout = "timed out" in (release_result.error or "").lower()
            if is_timeout:
                logger.warning(
                    "trustless: Release timed out for task %s — checking on-chain escrow state...",
                    task_id,
                )
                try:
                    await asyncio.sleep(15)  # give the TX time to mine
                    # Try to query on-chain state via SDK client (if available)
                    try:
                        _client = self._get_fase2_client(stored_network)
                    except RuntimeError:
                        _client = None
                    if not _client:
                        logger.warning(
                            "trustless: Cannot check on-chain state (no signing key). "
                            "Manual verification needed for task %s",
                            task_id,
                        )
                        raise Exception("No client for on-chain query")
                    state = await asyncio.to_thread(_client.query_escrow_state, pi)
                    capturable = int(state.get("capturableAmount", "1"))
                    logger.info(
                        "trustless: Escrow state after timeout: capturableAmount=%d, full=%s",
                        capturable,
                        state,
                    )
                    if capturable == 0:
                        # Release DID succeed on-chain — the proxy just ate the response
                        logger.info(
                            "trustless: Escrow capturableAmount=0 — release confirmed on-chain despite timeout for task %s",
                            task_id,
                        )
                        await log_payment_event(
                            task_id=task_id,
                            event_type="escrow_release",
                            status="released_to_worker",
                            tx_hash="timeout-verified-onchain",
                            network=stored_network,
                            token=token,
                            metadata={
                                "mode": "fase2",
                                "escrow_mode": "direct_release",
                                "timeout_recovery": True,
                                "escrow_state": state,
                            },
                        )
                        worker_address = pi_meta.get("worker_address", pi.receiver)
                        bounty_usdc = pi_meta.get("bounty_usdc", "0")
                        return {
                            "success": True,
                            "tx_hash": "timeout-verified-onchain",
                            "mode": "fase2",
                            "escrow_mode": "direct_release",
                            "worker_address": worker_address,
                            "bounty_usdc": str(bounty_usdc),
                            "timeout_recovery": True,
                        }
                except Exception as state_err:
                    logger.error(
                        "trustless: Escrow state query failed after timeout for task %s: %s",
                        task_id,
                        state_err,
                    )

            await log_payment_event(
                task_id=task_id,
                event_type="escrow_release",
                status="failed",
                network=stored_network,
                token=token,
                error=release_result.error,
                metadata={"mode": "fase2", "escrow_mode": "direct_release"},
            )
            return {
                "success": False,
                "tx_hash": None,
                "mode": "fase2",
                "escrow_mode": "direct_release",
                "error": f"Escrow release failed: {release_result.error}",
            }

        release_tx = release_result.transaction_hash
        worker_address = pi_meta.get("worker_address", pi.receiver)
        bounty_usdc = pi_meta.get("bounty_usdc", "0")

        await log_payment_event(
            task_id=task_id,
            event_type="escrow_release",
            status="released_to_worker",
            tx_hash=release_tx,
            to_address=worker_address,
            amount_usdc=Decimal(str(bounty_usdc)),
            network=stored_network,
            token=token,
            metadata={
                "mode": "fase2",
                "escrow_mode": "direct_release",
                "method": "direct_release",
            },
        )

        logger.info(
            "trustless: Escrow released directly to worker: task=%s, worker=%s, tx=%s",
            task_id,
            worker_address[:10] if worker_address else "?",
            release_tx,
        )

        # Fase 5: Best-effort flush of operator fees to treasury via distributeFees()
        # TODO: Move to periodic cron (every 15 min). Currently called per-release,
        # wasting gas from the hot wallet. Phase 3 SC-010.
        fee_distribute_tx = None
        try:
            fee_distribute_tx = await self._distribute_operator_fees(
                network=stored_network, token=token
            )
            if fee_distribute_tx:
                await log_payment_event(
                    task_id=task_id,
                    event_type="distribute_fees",
                    status="success",
                    tx_hash=fee_distribute_tx,
                    to_address=EM_TREASURY,
                    network=stored_network,
                    token=token,
                    metadata={
                        "mode": "fase2",
                        "escrow_mode": "direct_release",
                        "operator": EM_OPERATOR,
                    },
                )
                logger.info(
                    "trustless: Operator fees distributed to treasury: task=%s, tx=%s",
                    task_id,
                    fee_distribute_tx,
                )
        except Exception as e:
            logger.warning(
                "trustless: distributeFees() failed (non-blocking): task=%s, error=%s",
                task_id,
                e,
            )

        bounty_dec = Decimal(str(bounty_usdc))
        fee_model = pi_meta.get("fee_model", EM_FEE_MODEL)
        lock_usdc = Decimal(str(pi_meta.get("lock_amount_usdc", bounty_usdc)))

        # Net to worker depends on fee model — but on-chain it's always 87% of lock
        net_worker = float((lock_usdc * Decimal("0.87")).quantize(Decimal("0.000001")))
        fee_amount = float(lock_usdc) - net_worker

        return {
            "success": True,
            "tx_hash": release_tx,
            "escrow_release_tx": release_tx,
            "fee_distribute_tx": fee_distribute_tx,
            "fee_status": "on_chain",
            "fee_model": fee_model,
            "mode": "fase2",
            "escrow_mode": "direct_release",
            "method": "direct_release",
            "worker_paid": True,
            "bounty_usdc": float(bounty_dec),
            "lock_amount_usdc": float(lock_usdc),
            "net_to_worker": net_worker,
            "fee_to_treasury": fee_amount,
            # Keys expected by routes.py _settle_submission_payment():
            "worker_net": net_worker,
            "platform_fee": fee_amount,
            "gross_amount": float(lock_usdc),
            "error": None,
        }

    async def refund_trustless_escrow(
        self,
        task_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refund a trustless escrow (direct_release mode).

        Fase 5 credit card model: The full bounty returns to agent via
        escrow refund. No fee was collected off-chain, nothing to refund separately.

        Args:
            task_id: Task identifier.
            reason: Reason for refund.

        Returns:
            Dict with success, tx_hash, etc.
        """
        # Reconstruct PaymentInfo from DB
        pi, pi_meta = await self._reconstruct_fase2_state(task_id)
        if pi is None:
            logger.info(
                "trustless: No escrow state for task %s — treating as no-op refund",
                task_id,
            )
            await log_payment_event(
                task_id=task_id,
                event_type="escrow_refund",
                status="success",
                metadata={
                    "mode": "fase2",
                    "escrow_mode": "direct_release",
                    "method": "no_escrow_found",
                    "reason": reason,
                },
            )
            return {
                "success": True,
                "tx_hash": None,
                "mode": "fase2",
                "escrow_mode": "direct_release",
                "status": "no_escrow_found",
                "error": None,
            }

        stored_network = pi_meta.get("network", "base")
        client = self._get_fase2_client(stored_network)

        # Step 1: Refund escrow via facilitator — bounty returns to agent
        logger.info(
            "trustless: Refunding escrow for task %s via facilitator...", task_id
        )
        refund_result = await asyncio.to_thread(client.refund_via_facilitator, pi)

        if not refund_result.success:
            await log_payment_event(
                task_id=task_id,
                event_type="escrow_refund",
                status="failed",
                network=stored_network,
                error=refund_result.error,
                metadata={
                    "mode": "fase2",
                    "escrow_mode": "direct_release",
                    "reason": reason,
                },
            )
            return {
                "success": False,
                "tx_hash": None,
                "mode": "fase2",
                "escrow_mode": "direct_release",
                "status": "refund_failed",
                "error": f"Escrow refund failed: {refund_result.error}",
            }

        escrow_tx = refund_result.transaction_hash
        await log_payment_event(
            task_id=task_id,
            event_type="escrow_refund",
            status="success",
            tx_hash=escrow_tx,
            from_address=pi.receiver,
            to_address=client.payer,
            network=stored_network,
            metadata={
                "mode": "fase2",
                "escrow_mode": "direct_release",
                "reason": reason,
            },
        )

        logger.info("trustless: Escrow refunded for task %s, tx=%s", task_id, escrow_tx)

        # Fase 5 credit card model: Full bounty returns to agent via single escrow refund.
        # No separate fee was ever collected, so no fee refund needed.

        return {
            "success": True,
            "tx_hash": escrow_tx,
            "mode": "fase2",
            "escrow_mode": "direct_release",
            "status": "refunded",
            "error": None,
        }

    # =========================================================================
    # distributeFees — flush operator fees to treasury (Fase 5)
    # =========================================================================

    async def _distribute_operator_fees(
        self, network: str = "base", token: str = "USDC"
    ) -> Optional[str]:
        """
        Call distributeFees(token) on the PaymentOperator contract.

        This is a permissionless function — anyone can call it.
        It flushes all accumulated operator fees for the given token
        to the FEE_RECIPIENT (EM treasury).

        Uses raw RPC (eth_sendRawTransaction) to avoid extra dependencies.
        Returns the transaction hash or None if the call fails.
        """
        import httpx

        pk = os.environ.get("WALLET_PRIVATE_KEY")
        if not pk:
            logger.warning("distributeFees: No WALLET_PRIVATE_KEY, skipping")
            return None

        config = NETWORK_CONFIG.get(network, {})
        rpc_url = config.get("rpc_url", BASE_RPC_URL)

        # Find USDC address for this network
        token_info = config.get("tokens", {}).get(token, {})
        token_address = token_info.get("address", USDC_BASE_ADDRESS)

        # Build calldata: distributeFees(address token)
        # Pad token address to 32 bytes
        token_clean = token_address.lower().replace("0x", "")
        calldata = _SELECTOR_DISTRIBUTE_FEES + token_clean.zfill(64)

        operator = _get_operator_for_network(network)

        try:
            from eth_account import Account

            account = Account.from_key(pk)

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get nonce
                nonce_resp = await client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_getTransactionCount",
                        "params": [account.address, "latest"],
                    },
                )
                nonce = int(nonce_resp.json()["result"], 16)

                # Estimate gas (distributeFees is cheap ~30-50k gas)
                gas_resp = await client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "eth_estimateGas",
                        "params": [
                            {
                                "from": account.address,
                                "to": operator,
                                "data": "0x" + calldata,
                            }
                        ],
                    },
                )
                gas_result = gas_resp.json()
                if "error" in gas_result:
                    # Gas estimation failed — maybe no fees to distribute
                    logger.info(
                        "distributeFees: gas estimation failed (likely no fees): %s",
                        gas_result.get("error", {}).get("message", "unknown"),
                    )
                    return None
                gas_limit = int(gas_result["result"], 16)

                # Get gas price
                gas_price_resp = await client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "eth_gasPrice",
                        "params": [],
                    },
                )
                gas_price = int(gas_price_resp.json()["result"], 16)

                # Get chain ID
                chain_id = config.get("chain_id", 8453)

                # Build and sign transaction
                tx = {
                    "nonce": nonce,
                    "gasPrice": gas_price,
                    "gas": gas_limit + 10000,  # Add buffer
                    "to": operator,
                    "value": 0,
                    "data": bytes.fromhex(calldata),
                    "chainId": chain_id,
                }
                signed = account.sign_transaction(tx)

                # Send raw transaction
                send_resp = await client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "eth_sendRawTransaction",
                        "params": [
                            (
                                getattr(signed, "raw_transaction", None)
                                or signed.rawTransaction
                            ).hex()
                        ],
                    },
                )
                send_result = send_resp.json()
                if "error" in send_result:
                    logger.warning(
                        "distributeFees: send failed: %s",
                        send_result["error"].get("message", "unknown"),
                    )
                    return None

                tx_hash = send_result["result"]
                logger.info(
                    "distributeFees: TX sent: %s (operator=%s, token=%s)",
                    tx_hash,
                    operator[:10],
                    token,
                )
                return tx_hash

        except Exception as e:
            logger.warning("distributeFees failed: %s", e)
            return None

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

        fase2 mode: Gasless release via facilitator (1-TX, fee split on-chain).
        fase1 mode: 2 direct settlements agent->worker + agent->treasury (testing only).

        Args:
            task_id: Task identifier
            worker_address: Worker wallet address
            bounty_amount: The bounty amount (NOT including platform fee).
                           Worker receives this full amount.
            payment_header: Unused (kept for API compatibility)
            network: Payment network (optional, defaults to SDK default)
            token: Payment token (default: USDC)
            worker_auth_header: Pre-signed auth for worker payment (fase1 external agents)
            fee_auth_header: Pre-signed auth for fee payment (fase1 external agents)

        Returns:
            Uniform dict with success, tx_hash, mode, error.
        """
        try:
            if self.mode == "fase2":
                return await self._release_fase2(
                    task_id, worker_address, bounty_amount, network, token
                )
            else:
                return await self._release_fase1(
                    task_id,
                    worker_address,
                    bounty_amount,
                    worker_auth_header,
                    fee_auth_header,
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
        config_chain = NETWORK_CONFIG.get(stored_network, {})
        chain_id_check = config_chain.get("chain_id", 8453)
        release_timeout = 900 if chain_id_check == 1 else 300
        logger.info(
            "fase2: Releasing escrow for task %s via facilitator (chain_id=%s, timeout=%ds)...",
            task_id,
            chain_id_check,
            release_timeout,
        )
        release_result = await asyncio.to_thread(
            self._call_with_extended_timeout,
            client.release_via_facilitator,
            pi,
            release_timeout,
        )

        if not release_result.success:
            # Timeout fallback: check on-chain state (same as direct_release)
            is_timeout = "timed out" in (release_result.error or "").lower()
            if is_timeout:
                logger.warning(
                    "fase2: Release timed out for task %s — checking on-chain escrow state...",
                    task_id,
                )
                try:
                    await asyncio.sleep(15)
                    state = await asyncio.to_thread(client.query_escrow_state, pi)
                    capturable = int(state.get("capturableAmount", "1"))
                    logger.info(
                        "fase2: Escrow state after timeout: capturableAmount=%d",
                        capturable,
                    )
                    if capturable == 0:
                        logger.info(
                            "fase2: Release confirmed on-chain despite timeout for task %s",
                            task_id,
                        )
                        # Treat as success — continue the normal post-release flow
                        release_result = TransactionResult(
                            success=True,
                            transaction_hash="timeout-verified-onchain",
                            error=None,
                        )
                except Exception as state_err:
                    logger.error(
                        "fase2: Escrow state query failed after timeout: %s",
                        state_err,
                    )

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

        # Step 4: Calculate platform fee (ACCRUED — no TX).
        # Fee stays in platform wallet. Use admin sweep endpoint to collect.
        # Treasury receives the remainder after worker payment. This naturally
        # handles any on-chain protocol fee deduction from x402r — if the escrow
        # contract takes a cut, the treasury amount shrinks accordingly instead
        # of the transfer failing due to insufficient funds.
        # ADVISORY: This is an off-chain estimate for logging only.
        # The on-chain StaticFeeCalculator is the source of truth for the actual split.
        total_locked = compute_lock_amount(bounty_amount)
        on_chain_bps = await _get_protocol_fee_bps()
        platform_fee = _compute_treasury_remainder(
            bounty_amount, total_locked, on_chain_bps
        )

        # Log fee as accrued (no TX — stays in platform wallet for batch sweep)
        await log_payment_event(
            task_id=task_id,
            event_type="disburse_fee",
            status="accrued",
            to_address=EM_TREASURY,
            amount_usdc=platform_fee,
            network=stored_network,
            token=token,
            metadata={"mode": "fase2", "batch_collection": True},
        )

        logger.info(
            "fase2: Fee accrued for task %s: $%s (batch sweep later)",
            task_id,
            platform_fee,
        )

        return {
            "success": True,
            "tx_hash": worker_tx,
            "escrow_release_tx": escrow_tx,
            "fee_tx_hash": None,
            "fee_status": "accrued",
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

        fase2 mode: Gasless refund via facilitator (funds return to agent directly).
        fase1 mode: No funds moved, returns success immediately (testing only).

        Args:
            task_id: Task identifier
            escrow_id: Unused (kept for API compatibility)
            reason: Reason for refund (for audit trail)
            agent_address: Unused (kept for API compatibility)

        Returns:
            Uniform dict with success, tx_hash, mode, status, error.
        """
        try:
            if self.mode == "fase2":
                return await self._refund_fase2(task_id, reason)
            else:
                return await self._refund_fase1(task_id, reason)
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
                # Provide specific diagnostics for SDK-locked escrows
                escrow_timing = metadata.get("escrow_timing", "unknown")
                payment_mode = metadata.get("payment_mode", "unknown")
                logger.warning(
                    "fase2: No fase2 payment_info in escrow metadata for task %s "
                    "(escrow_timing=%s, payment_mode=%s). "
                    "SDK-locked escrows require the agent to send payment_info "
                    "in the assign request body.",
                    task_id,
                    escrow_timing,
                    payment_mode,
                )
                return None, {}

            # Validate required PaymentInfo fields before reconstruction
            required_pi_fields = [
                "operator",
                "receiver",
                "token",
                "max_amount",
                "pre_approval_expiry",
                "authorization_expiry",
                "refund_expiry",
                "min_fee_bps",
                "max_fee_bps",
                "fee_receiver",
                "salt",
            ]
            missing = [f for f in required_pi_fields if f not in pi_data]
            if missing:
                logger.warning(
                    "fase2: payment_info for task %s is missing fields: %s",
                    task_id,
                    missing,
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

            # Merge metadata-level fields into pi_data for callers that read
            # worker_address, network, bounty_usdc, payer, etc.
            merged = dict(pi_data)
            for k in (
                "worker_address",
                "network",
                "bounty_usdc",
                "lock_tx",
                "agent_address",
                "payer",
            ):
                if k not in merged and k in metadata:
                    merged[k] = metadata[k]
            # Ensure payer is available — the release needs it
            if "payer" not in merged:
                merged["payer"] = metadata.get(
                    "agent_address", pi_data.get("payer", "")
                )

            logger.info("fase2: Reconstructed PaymentInfo for task %s from DB", task_id)
            return pi, merged

        except Exception as e:
            logger.error(
                "fase2: Failed to reconstruct state for task %s: %s", task_id, e
            )
            return None, {}

    # =========================================================================
    # Fee Sweep (Batch Collection)
    # =========================================================================

    async def get_accrued_fees(
        self, network: str = "base", token: str = "USDC"
    ) -> Dict[str, Any]:
        """
        Get the accumulated fees in platform wallet available for sweep.

        Reads on-chain USDC balance and subtracts a safety buffer ($1.00)
        to ensure the platform wallet retains enough for operational gas/nonce.
        """
        safety_buffer = Decimal("1.00")

        try:
            sdk = self._get_sdk()
            platform_address = _get_platform_address()

            # Read on-chain USDC balance
            balance_result = await sdk.check_agent_balance(
                agent_address=platform_address,
                required_amount=Decimal("0"),
                network=network,
                token=token,
            )
            balance = Decimal(str(balance_result.get("balance", "0")))

            sweepable = max(balance - safety_buffer, Decimal("0"))

            # Count accrued fee events from DB
            accrued_total = Decimal("0")
            try:
                import supabase_client as db_mod

                client = db_mod.get_client()
                result = (
                    client.table("payment_events")
                    .select("amount_usdc")
                    .eq("event_type", "disburse_fee")
                    .eq("status", "accrued")
                    .execute()
                )
                for row in result.data or []:
                    accrued_total += Decimal(str(row.get("amount_usdc", 0)))
            except Exception as e:
                logger.warning("Could not sum accrued fees from DB: %s", e)

            # Fase 5: Also check operator contract USDC balance (fees pending distributeFees)
            operator_fees_usdc = Decimal("0")
            try:
                operator_address = _get_operator_for_network(network)
                operator_balance = await sdk.check_agent_balance(
                    agent_address=operator_address,
                    required_amount=Decimal("0"),
                    network=network,
                    token=token,
                )
                operator_fees_usdc = Decimal(str(operator_balance.get("balance", "0")))
            except Exception as e:
                logger.warning("Could not read operator USDC balance: %s", e)

            return {
                "platform_wallet": platform_address,
                "balance_usdc": float(balance),
                "safety_buffer_usdc": float(safety_buffer),
                "sweepable_usdc": float(sweepable),
                "accrued_from_tasks_usdc": float(accrued_total),
                "operator_fees_pending_usdc": float(operator_fees_usdc),
                "operator_address": _get_operator_for_network(network),
                "treasury_address": EM_TREASURY,
                "network": network,
                "token": token,
            }
        except Exception as e:
            logger.error("get_accrued_fees failed: %s", e)
            return {
                "error": str(e),
                "sweepable_usdc": 0,
                "accrued_from_tasks_usdc": 0,
            }

    async def sweep_fees_to_treasury(
        self, network: str = "base", token: str = "USDC"
    ) -> Dict[str, Any]:
        """
        Sweep accumulated fees to treasury.

        Fase 5: First calls distributeFees() on operator to flush on-chain
        fees to treasury. Then sweeps any remaining platform wallet balance
        (from legacy tasks) via EIP-3009 transfer.
        """
        safety_buffer = Decimal("1.00")
        min_sweep = Decimal("0.10")  # Don't sweep less than $0.10

        try:
            # Fase 5: First flush operator fees to treasury via distributeFees()
            # TODO: Move to periodic cron (every 15 min). Currently called per-release,
            # wasting gas from the hot wallet. Phase 3 SC-010.
            distribute_tx = None
            try:
                distribute_tx = await self._distribute_operator_fees(
                    network=network, token=token
                )
                if distribute_tx:
                    logger.info("sweep: distributeFees() sent: tx=%s", distribute_tx)
            except Exception as e:
                logger.warning("sweep: distributeFees() failed (non-blocking): %s", e)

            sdk = self._get_sdk()
            platform_address = _get_platform_address()

            # Read on-chain USDC balance
            balance_result = await sdk.check_agent_balance(
                agent_address=platform_address,
                required_amount=Decimal("0"),
                network=network,
                token=token,
            )
            balance = Decimal(str(balance_result.get("balance", "0")))
            sweepable = (balance - safety_buffer).quantize(Decimal("0.000001"))

            if sweepable < min_sweep:
                return {
                    "success": False,
                    "error": (
                        f"Sweepable amount (${sweepable}) below minimum (${min_sweep}). "
                        f"Balance: ${balance}, buffer: ${safety_buffer}"
                    ),
                    "balance_usdc": float(balance),
                    "sweepable_usdc": float(max(sweepable, Decimal("0"))),
                }

            # Execute sweep: platform wallet -> treasury via EIP-3009
            sweep_result = await sdk.collect_platform_fee(
                fee_amount=sweepable,
                task_id="fee_sweep",
                network=network,
                token=token,
            )

            sweep_tx = sweep_result.get("tx_hash")
            success = sweep_result.get("success", False)

            await log_payment_event(
                task_id="fee_sweep",
                event_type="fee_sweep",
                status="success" if success else "failed",
                tx_hash=sweep_tx,
                from_address=platform_address,
                to_address=EM_TREASURY,
                amount_usdc=sweepable,
                network=network,
                token=token,
                error=sweep_result.get("error"),
                metadata={"balance_before": float(balance)},
            )

            if success:
                # Mark accrued events as swept
                try:
                    import supabase_client as db_mod

                    client = db_mod.get_client()
                    client.table("payment_events").update({"status": "swept"}).eq(
                        "event_type", "disburse_fee"
                    ).eq("status", "accrued").execute()
                except Exception as e:
                    logger.warning("Could not mark accrued fees as swept: %s", e)

                logger.info(
                    "Fee sweep complete: $%s -> treasury, tx=%s",
                    sweepable,
                    sweep_tx,
                )

            return {
                "success": success,
                "tx_hash": sweep_tx,
                "distribute_fees_tx": distribute_tx,
                "amount_swept_usdc": float(sweepable) if success else 0,
                "balance_before_usdc": float(balance),
                "treasury_address": EM_TREASURY,
                "error": sweep_result.get("error"),
            }

        except Exception as e:
            logger.error("sweep_fees_to_treasury failed: %s", e)
            return {
                "success": False,
                "tx_hash": None,
                "amount_swept_usdc": 0,
                "error": str(e),
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
            "escrow_mode": self.escrow_mode,
            "fee_model": EM_FEE_MODEL,
            "fase2_available": FASE2_SDK_AVAILABLE,
            "sdk_available": SDK_AVAILABLE,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self.mode == "fase2" and self._fase2_clients:
            info["fase2_config"] = {
                "operator": EM_OPERATOR,
                "chains": list(self._fase2_clients.keys()),
                "facilitator_url": FACILITATOR_URL,
            }

        if self.mode == "fase1" and self._sdk is not None:
            info["fase1_config"] = {
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
