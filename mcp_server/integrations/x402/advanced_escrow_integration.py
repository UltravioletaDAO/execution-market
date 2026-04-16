"""
Advanced Escrow Integration for Execution Market via uvd-x402-sdk.

Uses the AdvancedEscrowClient from uvd_x402_sdk to interact with the
PaymentOperator Advanced Escrow system. This replaces direct contract calls
with SDK calls, proving the full stack: EM -> SDK -> Facilitator -> On-chain.

The 5 Advanced Escrow flows available to AI agents:
1. AUTHORIZE          - Lock bounty in escrow when agent publishes task
2. RELEASE            - Pay worker when task is approved
3. REFUND IN ESCROW   - Return bounty when task is cancelled
4. CHARGE             - Instant payment for trusted workers (no escrow)
5. REFUND POST ESCROW - Dispute resolution after release

Contract mapping:
    operator.authorize()        -> escrow.authorize()   (lock funds)
    operator.release()          -> escrow.capture()      (pay receiver)
    operator.refundInEscrow()   -> escrow.partialVoid()  (refund payer)
    operator.charge()           -> escrow.charge()       (direct payment)
    operator.refundPostEscrow() -> escrow.refund()       (dispute refund)

Usage:
    from mcp_server.integrations.x402.advanced_escrow_integration import (
        get_advanced_escrow,
        authorize_task_bounty,
        release_to_worker,
        refund_to_agent,
        charge_trusted_worker,
    )

    # Lock bounty in escrow
    result = authorize_task_bounty(
        receiver="0xWorker...",
        amount_usdc=Decimal("5.00"),
        tier="standard",
    )

    # Pay worker after task completion
    tx = release_to_worker(result.payment_info)

    # Or refund if task cancelled
    tx = refund_to_agent(result.payment_info)
"""

import os
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import from uvd-x402-sdk
try:
    from uvd_x402_sdk.advanced_escrow import (
        AdvancedEscrowClient,
        PaymentInfo,
        TaskTier,
        AuthorizationResult,
        TransactionResult,
        TIER_TIMINGS,
        BASE_MAINNET_CONTRACTS,
    )

    ADVANCED_ESCROW_AVAILABLE = True
except ImportError:
    ADVANCED_ESCROW_AVAILABLE = False
    logger.warning(
        "uvd-x402-sdk advanced_escrow not available. Install: pip install uvd-x402-sdk>=0.6.0"
    )

    # Fallback stubs so the module can still be parsed
    class TaskTier(str, Enum):
        MICRO = "micro"
        STANDARD = "standard"
        PREMIUM = "premium"
        ENTERPRISE = "enterprise"

    class PaymentInfo:
        pass

    class AuthorizationResult:
        pass

    class TransactionResult:
        pass

    TIER_TIMINGS = {}
    BASE_MAINNET_CONTRACTS = {}


# =============================================================================
# Configuration
# =============================================================================

PLATFORM_FEE_BPS = int(os.environ.get("EM_PLATFORM_FEE_BPS", "1300"))  # 13%
USDC_DECIMALS = 6

# Contract deposit limit (set by PaymentOperator condition).
# As of 2026-02-03, the commerce-payments contracts enforce a $100 max deposit.
# Ask the protocol team to raise this if Execution Market needs higher bounties.
DEPOSIT_LIMIT_USDC = Decimal(os.environ.get("ESCROW_DEPOSIT_LIMIT_USDC", "100"))


def _get_facilitator_url() -> str:
    return os.environ.get(
        "X402_FACILITATOR_URL",
        "https://facilitator.ultravioletadao.xyz",
    )


def _get_rpc_url() -> str:
    return os.environ.get(
        "X402_RPC_URL", os.environ.get("RPC_URL_BASE", "https://mainnet.base.org")
    )


def _get_private_key() -> Optional[str]:
    return os.environ.get("WALLET_PRIVATE_KEY") or os.environ.get("X402_PRIVATE_KEY")


def _get_chain_id() -> int:
    return int(os.environ.get("CHAIN_ID", "8453"))


# =============================================================================
# Execution Market Payment Strategy
# =============================================================================


class PaymentStrategy(str, Enum):
    """Payment strategy that an AI agent can choose for an Execution Market task."""

    ESCROW_CAPTURE = "escrow_capture"
    """Standard: AUTHORIZE -> RELEASE. Best for $5-$200 tasks."""

    ESCROW_CANCEL = "escrow_cancel"
    """Cancellable: AUTHORIZE -> REFUND IN ESCROW. For weather/event dependent tasks."""

    INSTANT_PAYMENT = "instant_payment"
    """Direct: CHARGE. For micro-tasks <$5 or trusted workers (>90% rep)."""

    PARTIAL_PAYMENT = "partial_payment"
    """Partial: AUTHORIZE -> partial RELEASE + REFUND remainder. For proof-of-attempt."""

    DISPUTE_RESOLUTION = "dispute_resolution"
    """Arbiter escrow: AUTHORIZE -> arbiter reviews -> RELEASE or REFUND IN ESCROW.
    Keeps funds in escrow under arbiter control until dispute is resolved.
    Preferred over post-escrow refund per protocol team recommendation."""


@dataclass
class TaskPayment:
    """Represents an Execution Market task payment state."""

    task_id: str
    strategy: PaymentStrategy
    payment_info: Optional[Any] = None  # PaymentInfo from SDK
    authorization: Optional[Any] = None  # AuthorizationResult from SDK
    amount_usdc: Decimal = Decimal("0")
    released_usdc: Decimal = Decimal("0")
    refunded_usdc: Decimal = Decimal("0")
    status: str = "pending"
    tx_hashes: List[str] = field(default_factory=list)


# =============================================================================
# Execution Market Advanced Escrow Wrapper
# =============================================================================


class EMAdvancedEscrow:
    """
    Execution Market wrapper around uvd-x402-sdk AdvancedEscrowClient.

    Provides EM-specific logic on top of the SDK:
    - Task tier mapping
    - Fee calculations
    - Payment strategy selection
    - Task state tracking
    """

    def __init__(
        self,
        private_key: Optional[str] = None,
        facilitator_url: Optional[str] = None,
        rpc_url: Optional[str] = None,
        chain_id: Optional[int] = None,
    ):
        if not ADVANCED_ESCROW_AVAILABLE:
            raise ImportError(
                "uvd-x402-sdk advanced_escrow module not available. "
                "Install: pip install uvd-x402-sdk>=0.6.0"
            )

        pk = private_key or _get_private_key()
        if not pk:
            raise ValueError("Private key required. Set WALLET_PRIVATE_KEY env var.")

        self.client = AdvancedEscrowClient(
            private_key=pk,
            facilitator_url=facilitator_url or _get_facilitator_url(),
            rpc_url=rpc_url or _get_rpc_url(),
            chain_id=chain_id or _get_chain_id(),
        )
        self.payer = self.client.payer
        self._task_payments: Dict[str, TaskPayment] = {}

        logger.info(
            "EMAdvancedEscrow initialized: payer=%s..., facilitator=%s",
            self.payer[:10],
            self.client.facilitator_url,
        )

    def _amount_to_atomic(self, amount_usdc: Decimal) -> int:
        """Convert USDC amount to atomic units (6 decimals)."""
        return int(amount_usdc * Decimal(10**USDC_DECIMALS))

    def _amount_from_atomic(self, amount: int) -> Decimal:
        """Convert atomic units to USDC."""
        return Decimal(amount) / Decimal(10**USDC_DECIMALS)

    def _get_tier(self, amount_usdc: Decimal) -> TaskTier:
        """Determine task tier based on bounty amount."""
        if amount_usdc < 5:
            return TaskTier.MICRO
        elif amount_usdc < 50:
            return TaskTier.STANDARD
        elif amount_usdc < 200:
            return TaskTier.PREMIUM
        else:
            return TaskTier.ENTERPRISE

    def recommend_strategy(
        self,
        amount_usdc: Decimal,
        worker_reputation: float = 0.0,
        external_dependency: bool = False,
        requires_quality_review: bool = False,
        erc8004_score: Optional[float] = None,
    ) -> PaymentStrategy:
        """
        Recommend a payment strategy based on task parameters.

        This implements the Execution Market Agent Decision Tree.
        When ERC-8004 reputation data is available, it takes precedence
        over the generic worker_reputation parameter.

        Args:
            amount_usdc: Bounty amount in USDC
            worker_reputation: Worker reputation score (0.0-1.0), used as fallback
            external_dependency: Task depends on external factors (weather, events)
            requires_quality_review: Task requires quality assurance after delivery
            erc8004_score: On-chain ERC-8004 reputation score (0.0-1.0).
                           If provided, overrides worker_reputation for trust decisions.
                           Query via: mcp_server.integrations.erc8004.facilitator_client
        """
        # Prefer on-chain ERC-8004 reputation when available
        effective_reputation = (
            erc8004_score if erc8004_score is not None else worker_reputation
        )

        if effective_reputation >= 0.90 and amount_usdc < 5:
            return PaymentStrategy.INSTANT_PAYMENT

        if external_dependency:
            return PaymentStrategy.ESCROW_CANCEL

        if requires_quality_review and amount_usdc >= 50:
            # Use escrow-based dispute: keep funds locked until arbiter decides.
            # Per protocol team: in-escrow refund is safer than post-escrow
            # because funds are guaranteed available and under arbiter control.
            return PaymentStrategy.DISPUTE_RESOLUTION

        # For low-reputation workers with high-value tasks, keep funds in escrow
        if effective_reputation < 0.50 and amount_usdc >= 50:
            return PaymentStrategy.DISPUTE_RESOLUTION

        return PaymentStrategy.ESCROW_CAPTURE

    # =========================================================================
    # Flow 1: AUTHORIZE (Lock bounty in escrow)
    # =========================================================================

    def authorize_task(
        self,
        task_id: str,
        receiver: str,
        amount_usdc: Decimal,
        strategy: PaymentStrategy = PaymentStrategy.ESCROW_CAPTURE,
        tier: Optional[str] = None,
    ) -> TaskPayment:
        """
        Lock bounty in escrow for a task.

        This is the first step for escrow-based payment strategies.

        Args:
            task_id: Unique task identifier
            receiver: Worker wallet address (or self for testing)
            amount_usdc: Bounty amount in USDC
            strategy: Payment strategy to use
            tier: Override tier (auto-determined from amount if not set)
        """
        if amount_usdc > DEPOSIT_LIMIT_USDC:
            logger.warning(
                "Task %s amount %s exceeds contract deposit limit %s USDC. "
                "Transaction will likely fail on-chain.",
                task_id,
                amount_usdc,
                DEPOSIT_LIMIT_USDC,
            )

        amount_atomic = self._amount_to_atomic(amount_usdc)
        task_tier = TaskTier(tier) if tier else self._get_tier(amount_usdc)

        pi = self.client.build_payment_info(
            receiver=receiver,
            amount=amount_atomic,
            tier=task_tier,
            max_fee_bps=PLATFORM_FEE_BPS,
        )

        logger.info(
            "Authorizing task %s: %s USDC to %s... (tier=%s, strategy=%s)",
            task_id,
            amount_usdc,
            receiver[:10],
            task_tier.value,
            strategy.value,
        )

        result = self.client.authorize(pi)

        payment = TaskPayment(
            task_id=task_id,
            strategy=strategy,
            payment_info=pi,
            authorization=result,
            amount_usdc=amount_usdc,
            status="authorized" if result.success else "failed",
        )

        if result.success:
            payment.tx_hashes.append(result.transaction_hash)
            logger.info(
                "Task %s authorized: tx=%s", task_id, result.transaction_hash[:20]
            )
        else:
            logger.error("Task %s authorization failed: %s", task_id, result.error)

        self._task_payments[task_id] = payment
        return payment

    # =========================================================================
    # Flow 2: RELEASE (Pay worker)
    # =========================================================================

    def release_to_worker(
        self,
        task_id: str,
        amount_usdc: Optional[Decimal] = None,
    ) -> TransactionResult:
        """
        Release escrowed funds to the worker.

        Args:
            task_id: Task identifier
            amount_usdc: Amount to release (defaults to full bounty)
        """
        payment = self._task_payments.get(task_id)
        if not payment or not payment.payment_info:
            raise ValueError(f"Task {task_id} not found or not authorized")

        amount = self._amount_to_atomic(amount_usdc) if amount_usdc else None

        logger.info(
            "Releasing payment for task %s: %s USDC",
            task_id,
            amount_usdc or payment.amount_usdc,
        )

        result = self.client.release(payment.payment_info, amount)

        if result.success:
            released = amount_usdc or payment.amount_usdc
            payment.released_usdc += released
            payment.status = "released"
            payment.tx_hashes.append(result.transaction_hash)
            logger.info(
                "Task %s released: tx=%s, gas=%s",
                task_id,
                result.transaction_hash[:20],
                result.gas_used,
            )
        else:
            logger.error("Task %s release failed: %s", task_id, result.error)

        return result

    # =========================================================================
    # Flow 3: REFUND IN ESCROW (Cancel task)
    # =========================================================================

    def refund_to_agent(
        self,
        task_id: str,
        amount_usdc: Optional[Decimal] = None,
    ) -> TransactionResult:
        """
        Return escrowed funds to the agent (cancel task).

        Args:
            task_id: Task identifier
            amount_usdc: Amount to refund (defaults to full bounty)
        """
        payment = self._task_payments.get(task_id)
        if not payment or not payment.payment_info:
            raise ValueError(f"Task {task_id} not found or not authorized")

        amount = self._amount_to_atomic(amount_usdc) if amount_usdc else None

        logger.info(
            "Refunding task %s: %s USDC",
            task_id,
            amount_usdc or payment.amount_usdc,
        )

        result = self.client.refund_in_escrow(payment.payment_info, amount)

        if result.success:
            refunded = amount_usdc or payment.amount_usdc
            payment.refunded_usdc += refunded
            payment.status = "refunded"
            payment.tx_hashes.append(result.transaction_hash)
            logger.info(
                "Task %s refunded: tx=%s, gas=%s",
                task_id,
                result.transaction_hash[:20],
                result.gas_used,
            )
        else:
            logger.error("Task %s refund failed: %s", task_id, result.error)

        return result

    # =========================================================================
    # Flow 4: CHARGE (Instant payment for trusted workers)
    # =========================================================================

    def charge_instant(
        self,
        task_id: str,
        receiver: str,
        amount_usdc: Decimal,
        tier: Optional[str] = None,
    ) -> TaskPayment:
        """
        Direct instant payment to a trusted worker (no escrow).

        Args:
            task_id: Task identifier
            receiver: Worker wallet address
            amount_usdc: Payment amount in USDC
            tier: Override tier
        """
        amount_atomic = self._amount_to_atomic(amount_usdc)
        task_tier = TaskTier(tier) if tier else self._get_tier(amount_usdc)

        pi = self.client.build_payment_info(
            receiver=receiver,
            amount=amount_atomic,
            tier=task_tier,
            max_fee_bps=PLATFORM_FEE_BPS,
        )

        if amount_usdc > DEPOSIT_LIMIT_USDC:
            logger.warning(
                "Task %s charge amount %s exceeds contract deposit limit %s USDC.",
                task_id,
                amount_usdc,
                DEPOSIT_LIMIT_USDC,
            )

        logger.info(
            "Charging instant payment for task %s: %s USDC to %s...",
            task_id,
            amount_usdc,
            receiver[:10],
        )

        result = self.client.charge(pi)

        payment = TaskPayment(
            task_id=task_id,
            strategy=PaymentStrategy.INSTANT_PAYMENT,
            payment_info=pi,
            amount_usdc=amount_usdc,
            released_usdc=amount_usdc if result.success else Decimal("0"),
            status="charged" if result.success else "failed",
        )

        if result.success:
            payment.tx_hashes.append(result.transaction_hash)
            logger.info(
                "Task %s charged: tx=%s, gas=%s",
                task_id,
                result.transaction_hash[:20],
                result.gas_used,
            )
        else:
            logger.error("Task %s charge failed: %s", task_id, result.error)

        self._task_payments[task_id] = payment
        return payment

    # =========================================================================
    # Flow 5: Partial Release + Refund (Proof of Attempt)
    # =========================================================================

    def partial_release_and_refund(
        self,
        task_id: str,
        release_percent: int = 15,
    ) -> Dict[str, Any]:
        """
        Partial release for proof-of-attempt, refund the remainder.

        Args:
            task_id: Task identifier
            release_percent: Percentage to release to worker (default 15%)
        """
        payment = self._task_payments.get(task_id)
        if not payment or not payment.payment_info:
            raise ValueError(f"Task {task_id} not found or not authorized")

        total_atomic = payment.payment_info.max_amount
        release_amount = total_atomic * release_percent // 100
        refund_amount = total_atomic - release_amount

        logger.info(
            "Partial release for task %s: %d%% release (%s), %d%% refund (%s)",
            task_id,
            release_percent,
            self._amount_from_atomic(release_amount),
            100 - release_percent,
            self._amount_from_atomic(refund_amount),
        )

        # Step 1: Release partial to worker
        release_result = self.client.release(payment.payment_info, release_amount)
        if not release_result.success:
            return {
                "success": False,
                "error": f"Release failed: {release_result.error}",
                "release_result": release_result,
            }

        payment.released_usdc = self._amount_from_atomic(release_amount)
        payment.tx_hashes.append(release_result.transaction_hash)

        # Step 2: Refund remainder to agent
        refund_result = self.client.refund_in_escrow(
            payment.payment_info, refund_amount
        )
        if not refund_result.success:
            return {
                "success": True,  # Partial success
                "warning": f"Refund failed: {refund_result.error}",
                "release_result": release_result,
                "refund_result": refund_result,
            }

        payment.refunded_usdc = self._amount_from_atomic(refund_amount)
        payment.status = "partial_released"
        payment.tx_hashes.append(refund_result.transaction_hash)

        return {
            "success": True,
            "release_result": release_result,
            "refund_result": refund_result,
            "released_usdc": str(payment.released_usdc),
            "refunded_usdc": str(payment.refunded_usdc),
        }

    # =========================================================================
    # Flow 6: Dispute (REFUND POST ESCROW) - DISABLED for production
    # =========================================================================
    #
    # NOTE (2026-02-03): Per protocol team (Ali), refundPostEscrow requires a
    # special tokenCollector that has NOT been implemented yet. Additionally,
    # the team recommends using refund-in-escrow for dispute resolution because
    # funds are guaranteed available and under arbiter control, vs post-escrow
    # which relies on merchant goodwill.
    #
    # The dispute_resolution strategy now uses:
    #   AUTHORIZE -> arbiter reviews -> RELEASE or REFUND IN ESCROW
    # instead of:
    #   AUTHORIZE -> RELEASE -> REFUND POST ESCROW
    #
    # This method is kept for future use when tokenCollector is implemented.
    # Do NOT call from production flows.
    #

    def initiate_dispute(
        self,
        task_id: str,
        amount_usdc: Optional[Decimal] = None,
    ) -> TransactionResult:
        """
        Initiate a dispute refund after funds were released.

        WARNING: NOT FUNCTIONAL IN PRODUCTION. Requires a tokenCollector
        contract that has not been implemented by the protocol team yet.
        Use refund_to_agent() while funds are still in escrow instead.

        Kept for future use when the protocol team implements tokenCollector.

        Args:
            task_id: Task identifier
            amount_usdc: Amount to dispute (defaults to full bounty)
        """
        payment = self._task_payments.get(task_id)
        if not payment or not payment.payment_info:
            raise ValueError(f"Task {task_id} not found or not authorized")

        amount = self._amount_to_atomic(amount_usdc) if amount_usdc else None

        logger.info(
            "Initiating dispute for task %s: %s USDC",
            task_id,
            amount_usdc or payment.amount_usdc,
        )

        result = self.client.refund_post_escrow(payment.payment_info, amount)

        if result.success:
            payment.status = "disputed"
            payment.tx_hashes.append(result.transaction_hash)
            logger.info(
                "Task %s dispute initiated: tx=%s",
                task_id,
                result.transaction_hash[:20],
            )
        else:
            logger.warning(
                "Task %s dispute failed (expected - tokenCollector not implemented): %s",
                task_id,
                result.error,
            )

        return result

    # =========================================================================
    # State Query
    # =========================================================================

    def get_task_payment(self, task_id: str) -> Optional[TaskPayment]:
        """Get the payment state for a task."""
        return self._task_payments.get(task_id)

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return {
            "available": ADVANCED_ESCROW_AVAILABLE,
            "payer": self.payer,
            "facilitator_url": self.client.facilitator_url,
            "chain_id": self.client.chain_id,
            "contracts": self.client.contracts,
            "platform_fee_bps": PLATFORM_FEE_BPS,
        }


# =============================================================================
# Module-Level Instance
# =============================================================================

_default_instance: Optional[EMAdvancedEscrow] = None


def get_advanced_escrow() -> EMAdvancedEscrow:
    """Get or create the default EMAdvancedEscrow instance."""
    global _default_instance
    if _default_instance is None:
        _default_instance = EMAdvancedEscrow()
    return _default_instance


# =============================================================================
# Convenience Functions
# =============================================================================


def authorize_task_bounty(
    task_id: str,
    receiver: str,
    amount_usdc: Decimal,
    strategy: PaymentStrategy = PaymentStrategy.ESCROW_CAPTURE,
    tier: Optional[str] = None,
) -> TaskPayment:
    """Lock bounty in escrow for a task (convenience function)."""
    escrow = get_advanced_escrow()
    return escrow.authorize_task(task_id, receiver, amount_usdc, strategy, tier)


def release_to_worker(
    task_id: str, amount_usdc: Optional[Decimal] = None
) -> TransactionResult:
    """Release escrowed funds to worker (convenience function)."""
    escrow = get_advanced_escrow()
    return escrow.release_to_worker(task_id, amount_usdc)


def refund_to_agent(
    task_id: str, amount_usdc: Optional[Decimal] = None
) -> TransactionResult:
    """Refund escrowed funds to agent (convenience function)."""
    escrow = get_advanced_escrow()
    return escrow.refund_to_agent(task_id, amount_usdc)


def charge_trusted_worker(
    task_id: str,
    receiver: str,
    amount_usdc: Decimal,
) -> TaskPayment:
    """Instant payment to trusted worker (convenience function)."""
    escrow = get_advanced_escrow()
    return escrow.charge_instant(task_id, receiver, amount_usdc)


def partial_release(task_id: str, release_percent: int = 15) -> Dict[str, Any]:
    """Partial release + refund for proof-of-attempt (convenience function)."""
    escrow = get_advanced_escrow()
    return escrow.partial_release_and_refund(task_id, release_percent)
