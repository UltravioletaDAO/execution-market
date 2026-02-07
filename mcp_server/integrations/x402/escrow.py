"""
Escrow Integration for Task Lifecycle (NOW-021 to NOW-023)

Integrates x402 escrow with task state machine.

Lifecycle:
1. publish_task -> deposit_for_task (escrow created)
2. submission received -> optional partial release (30% proof-of-work)
3. approve_submission -> release_on_approval (remaining to worker + fees to treasury)
4. cancel_task -> refund_on_cancel (full refund to agent)
5. dispute -> handle_dispute (lock escrow pending resolution)
"""

import logging
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from .client import (
    X402Client,
    X402Error,
    PaymentToken as ClientPaymentToken,
)

logger = logging.getLogger(__name__)


# Configuration constants (defaults - use PlatformConfig for dynamic values)
# These are fallbacks when config system is unavailable
DEFAULT_PLATFORM_FEE_PERCENT = Decimal("0.08")  # 8%
DEFAULT_MINIMUM_PAYOUT = Decimal("0.50")  # $0.50 minimum
DEFAULT_PARTIAL_RELEASE_PERCENT = Decimal("0.30")  # 30% on submission

# Legacy aliases for backward compatibility (use PlatformConfig in new code)
PLATFORM_FEE_PERCENT = DEFAULT_PLATFORM_FEE_PERCENT
MINIMUM_PAYOUT = DEFAULT_MINIMUM_PAYOUT
PARTIAL_RELEASE_PERCENT = DEFAULT_PARTIAL_RELEASE_PERCENT


async def get_platform_fee_pct() -> Decimal:
    """Get platform fee from config system."""
    try:
        from config import PlatformConfig

        return await PlatformConfig.get_fee_pct()
    except Exception:
        return DEFAULT_PLATFORM_FEE_PERCENT


async def get_partial_release_pct() -> Decimal:
    """Get partial release percentage from config system."""
    try:
        from config import PlatformConfig

        return await PlatformConfig.get_partial_release_pct()
    except Exception:
        return DEFAULT_PARTIAL_RELEASE_PERCENT


async def get_min_bounty() -> Decimal:
    """Get minimum bounty from config system."""
    try:
        from config import PlatformConfig

        return await PlatformConfig.get_min_bounty()
    except Exception:
        return DEFAULT_MINIMUM_PAYOUT


class PaymentToken(str, Enum):
    """Supported payment tokens."""

    USDC = "USDC"
    EURC = "EURC"
    DAI = "DAI"
    USDT = "USDT"


class EscrowStatus(str, Enum):
    """Status of an escrow in the lifecycle."""

    PENDING = "pending"  # Awaiting deposit transaction
    DEPOSITED = "deposited"  # Funds locked in escrow
    PARTIAL_RELEASED = "partial_released"  # Some funds released on submission
    RELEASED = "released"  # All funds released on approval
    REFUNDED = "refunded"  # Funds returned to agent on cancel
    DISPUTED = "disputed"  # Escrow locked during dispute resolution
    FAILED = "failed"  # Transaction failed


@dataclass
class FeeBreakdown:
    """Breakdown of fees for a payment."""

    gross_amount: Decimal
    platform_fee: Decimal
    net_to_worker: Decimal
    fee_percent: Decimal

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gross_amount": float(self.gross_amount),
            "platform_fee": float(self.platform_fee),
            "net_to_worker": float(self.net_to_worker),
            "fee_percent": float(self.fee_percent),
        }


@dataclass
class ReleaseRecord:
    """Record of a release transaction."""

    tx_hash: str
    amount: Decimal
    recipient: str
    timestamp: datetime
    release_type: str  # "partial", "final", "fee"


@dataclass
class TaskEscrow:
    """Complete state of a task's escrow."""

    task_id: str
    escrow_id: str
    total_amount: Decimal
    released_amount: Decimal
    status: EscrowStatus
    token: PaymentToken
    depositor_wallet: str
    beneficiary_wallet: Optional[str]
    deposit_tx: str
    release_txs: List[ReleaseRecord] = field(default_factory=list)
    refund_tx: Optional[str] = None
    dispute_reason: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    timeout_timestamp: int = 0
    fees: Optional[FeeBreakdown] = None

    @property
    def remaining_amount(self) -> Decimal:
        """Calculate remaining amount in escrow."""
        return self.total_amount - self.released_amount

    @property
    def is_active(self) -> bool:
        """Check if escrow is still active (not finalized)."""
        return self.status in (
            EscrowStatus.DEPOSITED,
            EscrowStatus.PARTIAL_RELEASED,
            EscrowStatus.DISPUTED,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "task_id": self.task_id,
            "escrow_id": self.escrow_id,
            "total_amount": float(self.total_amount),
            "released_amount": float(self.released_amount),
            "remaining_amount": float(self.remaining_amount),
            "status": self.status.value,
            "token": self.token.value,
            "depositor_wallet": self.depositor_wallet,
            "beneficiary_wallet": self.beneficiary_wallet,
            "deposit_tx": self.deposit_tx,
            "release_txs": [
                {
                    "tx_hash": r.tx_hash,
                    "amount": float(r.amount),
                    "recipient": r.recipient,
                    "timestamp": r.timestamp.isoformat(),
                    "release_type": r.release_type,
                }
                for r in self.release_txs
            ],
            "refund_tx": self.refund_tx,
            "dispute_reason": self.dispute_reason,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "timeout_timestamp": self.timeout_timestamp,
            "fees": self.fees.to_dict() if self.fees else None,
        }


class EscrowStateError(Exception):
    """Raised when escrow operation is invalid for current state."""

    pass


class EscrowManager:
    """
    Manages escrow lifecycle for tasks.

    Thread-safe state management with transaction history tracking.
    Integrates with x402 protocol for on-chain operations.
    """

    def __init__(
        self,
        x402_client: Optional[X402Client] = None,
        treasury_address: Optional[str] = None,
    ):
        """
        Initialize escrow manager.

        Args:
            x402_client: X402Client instance (creates one if not provided)
            treasury_address: Address for platform fee collection
        """
        self.client = x402_client or X402Client()
        self.treasury_address = treasury_address or os.environ.get(
            "EM_TREASURY_ADDRESS", "0x0000000000000000000000000000000000000000"
        )
        # In-memory cache of escrow states (should be backed by DB in production)
        self._escrows: Dict[str, TaskEscrow] = {}
        logger.info(
            "EscrowManager initialized with treasury: %s",
            self.treasury_address[:10] + "..." if self.treasury_address else "None",
        )

    def calculate_fees(self, bounty_usd: Decimal) -> FeeBreakdown:
        """
        Calculate fee breakdown for a bounty.

        Args:
            bounty_usd: Total bounty amount

        Returns:
            FeeBreakdown with all amounts

        Raises:
            X402Error: If net payout would be below minimum
        """
        gross = Decimal(str(bounty_usd))
        fee = (gross * PLATFORM_FEE_PERCENT).quantize(Decimal("0.01"))
        net = gross - fee

        if net < MINIMUM_PAYOUT:
            raise X402Error(
                f"Net payout ${float(net):.2f} is below minimum ${float(MINIMUM_PAYOUT):.2f}. "
                f"Increase bounty to at least ${float(MINIMUM_PAYOUT / (1 - PLATFORM_FEE_PERCENT)):.2f}"
            )

        return FeeBreakdown(
            gross_amount=gross,
            platform_fee=fee,
            net_to_worker=net,
            fee_percent=PLATFORM_FEE_PERCENT * 100,
        )

    async def deposit_for_task(
        self,
        task_id: str,
        bounty_usd: Decimal,
        agent_wallet: str,
        token: PaymentToken = PaymentToken.USDC,
        timeout_hours: int = 48,
    ) -> TaskEscrow:
        """
        Create escrow when task is published (NOW-021).

        Deposits the full bounty amount into escrow. The escrow will be:
        - Released to worker on approval
        - Refunded to agent on cancellation
        - Locked during disputes

        Args:
            task_id: Unique task identifier
            bounty_usd: Bounty amount in USD
            agent_wallet: Agent's wallet address (for refunds)
            token: Payment token (default USDC)
            timeout_hours: Hours until escrow can be refunded

        Returns:
            TaskEscrow with complete state

        Raises:
            X402Error: If escrow creation fails
            EscrowStateError: If escrow already exists for task
        """
        # Check for existing escrow
        if task_id in self._escrows:
            existing = self._escrows[task_id]
            if existing.status != EscrowStatus.FAILED:
                raise EscrowStateError(
                    f"Escrow already exists for task {task_id} in status {existing.status.value}"
                )
            logger.info("Retrying failed escrow for task %s", task_id)

        # Calculate fees upfront
        bounty_decimal = Decimal(str(bounty_usd))
        fees = self.calculate_fees(bounty_decimal)

        logger.info(
            "Creating escrow for task %s: $%.2f (net to worker: $%.2f)",
            task_id,
            float(bounty_decimal),
            float(fees.net_to_worker),
        )

        # Create initial escrow state
        escrow = TaskEscrow(
            task_id=task_id,
            escrow_id="",  # Will be set after on-chain creation
            total_amount=bounty_decimal,
            released_amount=Decimal("0"),
            status=EscrowStatus.PENDING,
            token=token,
            depositor_wallet=agent_wallet,
            beneficiary_wallet=None,  # Set when worker assigned
            deposit_tx="",
            fees=fees,
        )
        self._escrows[task_id] = escrow

        try:
            # Create on-chain escrow
            # Convert PaymentToken enum if needed
            client_token = ClientPaymentToken(token.value.lower())
            result = await self.client.create_escrow(
                task_id=task_id,
                amount=bounty_decimal,
                token=client_token,
                beneficiary=agent_wallet,  # Initially points to agent for refund
                timeout_hours=timeout_hours,
            )

            # Result is EscrowDeposit on success
            # Update escrow state
            escrow.escrow_id = result.escrow_id
            escrow.deposit_tx = result.tx_hash or ""
            escrow.timeout_timestamp = int(result.timeout_at.timestamp())
            escrow.status = EscrowStatus.DEPOSITED
            escrow.updated_at = datetime.now(timezone.utc)

            logger.info(
                "Escrow created for task %s: escrow_id=%s, tx=%s",
                task_id,
                escrow.escrow_id,
                escrow.deposit_tx,
            )

            return escrow

        except Exception as e:
            escrow.status = EscrowStatus.FAILED
            escrow.updated_at = datetime.now(timezone.utc)
            logger.error("Failed to create escrow for task %s: %s", task_id, str(e))
            raise

    async def release_partial_on_submission(
        self,
        task_id: str,
        worker_wallet: str,
    ) -> TaskEscrow:
        """
        Release partial payment when worker submits evidence.

        Releases 30% of the net bounty as proof-of-work payment.
        This protects workers from malicious rejections.

        Args:
            task_id: Task identifier
            worker_wallet: Worker's wallet address

        Returns:
            Updated TaskEscrow

        Raises:
            EscrowStateError: If escrow not in valid state for partial release
            X402Error: If release transaction fails
        """
        escrow = self._get_escrow(task_id)

        # Validate state
        if escrow.status != EscrowStatus.DEPOSITED:
            raise EscrowStateError(
                f"Cannot release partial: escrow in status {escrow.status.value}, "
                f"expected {EscrowStatus.DEPOSITED.value}"
            )

        # Calculate partial amount
        if not escrow.fees:
            escrow.fees = self.calculate_fees(escrow.total_amount)

        partial_amount = (escrow.fees.net_to_worker * PARTIAL_RELEASE_PERCENT).quantize(
            Decimal("0.01")
        )

        logger.info(
            "Releasing partial payment for task %s: $%.2f (%.0f%%) to %s",
            task_id,
            float(partial_amount),
            float(PARTIAL_RELEASE_PERCENT * 100),
            worker_wallet[:10] + "...",
        )

        # Update beneficiary if first release
        escrow.beneficiary_wallet = worker_wallet

        try:
            result = await self.client.release_escrow(
                escrow_id=escrow.escrow_id,
                recipient=worker_wallet,
                amount=partial_amount,
            )

            if not result.success:
                raise X402Error(f"Failed to release partial payment: {result.error}")

            # Record the release
            release_record = ReleaseRecord(
                tx_hash=result.tx_hash or "",
                amount=partial_amount,
                recipient=worker_wallet,
                timestamp=datetime.now(timezone.utc),
                release_type="partial",
            )
            escrow.release_txs.append(release_record)
            escrow.released_amount += partial_amount
            escrow.status = EscrowStatus.PARTIAL_RELEASED
            escrow.updated_at = datetime.now(timezone.utc)

            logger.info(
                "Partial release complete for task %s: tx=%s, released=$%.2f, remaining=$%.2f",
                task_id,
                result.tx_hash,
                float(escrow.released_amount),
                float(escrow.remaining_amount),
            )

            return escrow

        except Exception as e:
            logger.error("Failed partial release for task %s: %s", task_id, str(e))
            raise

    async def release_on_approval(
        self,
        task_id: str,
        worker_wallet: str,
        partial: bool = False,
        partial_pct: float = 1.0,
    ) -> str:
        """
        Release escrow when submission is approved (NOW-022).

        Releases remaining bounty to worker and platform fees to treasury.
        Handles both full releases and custom partial percentages.

        Args:
            task_id: Task identifier
            worker_wallet: Worker's wallet address
            partial: If True, only release partial_pct of remaining
            partial_pct: Percentage to release (0.0 to 1.0)

        Returns:
            Transaction hash of worker payment

        Raises:
            EscrowStateError: If escrow not in valid state
            X402Error: If release transaction fails
        """
        escrow = self._get_escrow(task_id)

        # Validate state
        valid_states = (EscrowStatus.DEPOSITED, EscrowStatus.PARTIAL_RELEASED)
        if escrow.status not in valid_states:
            raise EscrowStateError(
                f"Cannot release: escrow in status {escrow.status.value}, "
                f"expected one of {[s.value for s in valid_states]}"
            )

        if not escrow.fees:
            escrow.fees = self.calculate_fees(escrow.total_amount)

        # Update beneficiary
        escrow.beneficiary_wallet = worker_wallet

        # Calculate amounts
        already_released = escrow.released_amount
        total_to_worker = escrow.fees.net_to_worker * Decimal(str(partial_pct))
        worker_remaining = (total_to_worker - already_released).quantize(
            Decimal("0.01")
        )

        # Ensure non-negative
        worker_remaining = max(worker_remaining, Decimal("0"))

        logger.info(
            "Releasing final payment for task %s: "
            "$%.2f to worker (already released: $%.2f), $%.2f platform fee",
            task_id,
            float(worker_remaining),
            float(already_released),
            float(escrow.fees.platform_fee),
        )

        tx_hashes: List[str] = []

        try:
            # Release to worker
            if worker_remaining > 0:
                worker_result = await self.client.release_escrow(
                    escrow_id=escrow.escrow_id,
                    recipient=worker_wallet,
                    amount=worker_remaining,
                )

                if not worker_result.success:
                    raise X402Error(
                        f"Failed to release worker payment: {worker_result.error}"
                    )

                release_record = ReleaseRecord(
                    tx_hash=worker_result.tx_hash or "",
                    amount=worker_remaining,
                    recipient=worker_wallet,
                    timestamp=datetime.now(timezone.utc),
                    release_type="final",
                )
                escrow.release_txs.append(release_record)
                escrow.released_amount += worker_remaining
                tx_hashes.append(worker_result.tx_hash or "")

                logger.info(
                    "Worker payment released for task %s: tx=%s",
                    task_id,
                    worker_result.tx_hash,
                )

            # Collect platform fees
            if (
                escrow.fees.platform_fee > 0
                and self.treasury_address
                and self.treasury_address
                != "0x0000000000000000000000000000000000000000"
            ):
                fee_result = await self.client.release_escrow(
                    escrow_id=escrow.escrow_id,
                    recipient=self.treasury_address,
                    amount=escrow.fees.platform_fee,
                )

                if not fee_result.success:
                    # Log but don't fail - worker already paid
                    logger.warning(
                        "Failed to collect platform fee for task %s: %s",
                        task_id,
                        fee_result.error,
                    )
                else:
                    fee_record = ReleaseRecord(
                        tx_hash=fee_result.tx_hash or "",
                        amount=escrow.fees.platform_fee,
                        recipient=self.treasury_address,
                        timestamp=datetime.now(timezone.utc),
                        release_type="fee",
                    )
                    escrow.release_txs.append(fee_record)
                    escrow.released_amount += escrow.fees.platform_fee
                    tx_hashes.append(fee_result.tx_hash or "")

                    logger.info(
                        "Platform fee collected for task %s: tx=%s",
                        task_id,
                        fee_result.tx_hash,
                    )

            # Update final status
            if not partial or partial_pct >= 1.0:
                escrow.status = EscrowStatus.RELEASED
            escrow.updated_at = datetime.now(timezone.utc)

            logger.info(
                "Approval release complete for task %s: status=%s, total_released=$%.2f",
                task_id,
                escrow.status.value,
                float(escrow.released_amount),
            )

            return tx_hashes[0] if tx_hashes else ""

        except Exception as e:
            logger.error("Failed to release escrow for task %s: %s", task_id, str(e))
            raise

    async def refund_on_cancel(
        self,
        task_id: str,
        reason: str,
    ) -> str:
        """
        Refund escrow when task is cancelled (NOW-023).

        Returns the full escrowed amount to the agent.
        Only allowed if no partial payments have been made.

        Args:
            task_id: Task identifier
            reason: Reason for cancellation

        Returns:
            Transaction hash of refund

        Raises:
            EscrowStateError: If escrow not in valid state for refund
            X402Error: If refund transaction fails
        """
        escrow = self._get_escrow(task_id)

        # Validate state
        if escrow.status not in (EscrowStatus.DEPOSITED,):
            raise EscrowStateError(
                f"Cannot refund: escrow in status {escrow.status.value}. "
                f"Only {EscrowStatus.DEPOSITED.value} escrows can be fully refunded."
            )

        # Check if partial payments made
        if escrow.released_amount > 0:
            raise EscrowStateError(
                "Cannot fully refund: $%.2f already released. "
                "Use partial refund instead." % float(escrow.released_amount)
            )

        logger.info(
            "Refunding escrow for cancelled task %s: $%.2f to %s. Reason: %s",
            task_id,
            float(escrow.total_amount),
            escrow.depositor_wallet[:10] + "...",
            reason,
        )

        try:
            result = await self.client.refund_escrow(
                escrow_id=escrow.escrow_id,
                reason=reason,
            )

            if not result.success:
                raise X402Error(f"Failed to refund escrow: {result.error}")

            # Update state
            escrow.refund_tx = result.tx_hash
            escrow.status = EscrowStatus.REFUNDED
            escrow.dispute_reason = reason  # Store cancellation reason
            escrow.updated_at = datetime.now(timezone.utc)

            logger.info(
                "Refund complete for task %s: tx=%s",
                task_id,
                result.tx_hash,
            )

            return result.tx_hash or ""

        except Exception as e:
            logger.error("Failed to refund escrow for task %s: %s", task_id, str(e))
            raise

    async def handle_dispute(
        self,
        task_id: str,
        dispute_reason: Optional[str] = None,
    ) -> None:
        """
        Lock escrow during dispute resolution.

        Marks the escrow as disputed, preventing further releases or refunds
        until the dispute is resolved.

        Args:
            task_id: Task identifier
            dispute_reason: Reason for dispute

        Raises:
            EscrowStateError: If escrow not in valid state for dispute
        """
        escrow = self._get_escrow(task_id)

        # Validate state
        valid_states = (EscrowStatus.DEPOSITED, EscrowStatus.PARTIAL_RELEASED)
        if escrow.status not in valid_states:
            raise EscrowStateError(
                f"Cannot dispute: escrow in status {escrow.status.value}, "
                f"expected one of {[s.value for s in valid_states]}"
            )

        logger.info(
            "Locking escrow for dispute on task %s. Reason: %s",
            task_id,
            dispute_reason or "Not specified",
        )

        escrow.status = EscrowStatus.DISPUTED
        escrow.dispute_reason = dispute_reason
        escrow.updated_at = datetime.now(timezone.utc)

        logger.info(
            "Escrow locked for task %s. Remaining: $%.2f",
            task_id,
            float(escrow.remaining_amount),
        )

    async def resolve_dispute(
        self,
        task_id: str,
        winner: str,  # "worker" or "agent"
        worker_wallet: Optional[str] = None,
        worker_pct: float = 1.0,
    ) -> str:
        """
        Resolve a disputed escrow.

        Args:
            task_id: Task identifier
            winner: "worker" for worker wins, "agent" for agent wins
            worker_wallet: Worker's wallet (required if worker wins)
            worker_pct: Percentage to pay worker (0.0 to 1.0)

        Returns:
            Transaction hash

        Raises:
            EscrowStateError: If escrow not disputed
            ValueError: If winner invalid
        """
        escrow = self._get_escrow(task_id)

        if escrow.status != EscrowStatus.DISPUTED:
            raise EscrowStateError(
                f"Cannot resolve: escrow in status {escrow.status.value}, "
                f"expected {EscrowStatus.DISPUTED.value}"
            )

        logger.info(
            "Resolving dispute for task %s: winner=%s, worker_pct=%.0f%%",
            task_id,
            winner,
            worker_pct * 100,
        )

        if winner == "worker":
            if not worker_wallet:
                raise ValueError("worker_wallet required when worker wins dispute")

            # Temporarily set to deposited to allow release
            escrow.status = EscrowStatus.PARTIAL_RELEASED

            return await self.release_on_approval(
                task_id=task_id,
                worker_wallet=worker_wallet,
                partial=worker_pct < 1.0,
                partial_pct=worker_pct,
            )

        elif winner == "agent":
            # Temporarily set to deposited to allow refund
            escrow.status = EscrowStatus.DEPOSITED

            return await self.refund_on_cancel(
                task_id=task_id,
                reason=f"Dispute resolved in favor of agent. Original reason: {escrow.dispute_reason}",
            )

        else:
            raise ValueError(f"Invalid winner: {winner}. Must be 'worker' or 'agent'")

    def get_escrow(self, task_id: str) -> Optional[TaskEscrow]:
        """
        Get escrow state for a task.

        Args:
            task_id: Task identifier

        Returns:
            TaskEscrow or None if not found
        """
        return self._escrows.get(task_id)

    def get_escrow_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get escrow status as dictionary for API responses.

        Args:
            task_id: Task identifier

        Returns:
            Dictionary with escrow state

        Raises:
            EscrowStateError: If escrow not found
        """
        escrow = self._get_escrow(task_id)
        return escrow.to_dict()

    def _get_escrow(self, task_id: str) -> TaskEscrow:
        """
        Get escrow, raising error if not found.

        Args:
            task_id: Task identifier

        Returns:
            TaskEscrow

        Raises:
            EscrowStateError: If escrow not found
        """
        escrow = self._escrows.get(task_id)
        if not escrow:
            raise EscrowStateError(f"No escrow found for task {task_id}")
        return escrow


# ============== Convenience Functions ==============

# Module-level manager instance for convenience functions
_default_manager: Optional[EscrowManager] = None


def get_manager() -> EscrowManager:
    """Get or create the default EscrowManager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = EscrowManager()
    return _default_manager


async def create_escrow_for_task(
    task_id: str,
    bounty_usdc: float,
    agent_address: str,
    timeout_hours: int = 48,
) -> Dict[str, Any]:
    """
    Create escrow for a task (NOW-021).

    Convenience function for publish_task integration.

    Args:
        task_id: Unique task identifier
        bounty_usdc: Bounty amount in USDC
        agent_address: Agent's wallet address
        timeout_hours: Hours until escrow expires

    Returns:
        Dict with escrow details
    """
    manager = get_manager()
    escrow = await manager.deposit_for_task(
        task_id=task_id,
        bounty_usd=Decimal(str(bounty_usdc)),
        agent_wallet=agent_address,
        timeout_hours=timeout_hours,
    )
    return escrow.to_dict()


async def release_partial_on_submission(
    task_id: str,
    worker_address: str,
) -> Dict[str, Any]:
    """
    Release partial payment on submission.

    Convenience function for submit_work integration.

    Args:
        task_id: Task identifier
        worker_address: Worker's wallet address

    Returns:
        Dict with release details
    """
    manager = get_manager()
    escrow = await manager.release_partial_on_submission(
        task_id=task_id,
        worker_wallet=worker_address,
    )
    return {
        "success": True,
        "tx_hash": escrow.release_txs[-1].tx_hash if escrow.release_txs else "",
        "amount_released": float(escrow.release_txs[-1].amount)
        if escrow.release_txs
        else 0,
        "percent_released": float(PARTIAL_RELEASE_PERCENT * 100),
        "remaining": float(escrow.remaining_amount),
        "type": "partial",
    }


async def release_on_approval(
    task_id: str,
    escrow_id: str,  # Kept for API compatibility, not used
    worker_address: str,
    bounty_usdc: float,  # Kept for API compatibility, not used
    partial_released: float = 0,  # Kept for API compatibility, not used
) -> Dict[str, Any]:
    """
    Release escrow when task is approved (NOW-022).

    Convenience function for approve_submission integration.

    Args:
        task_id: Task identifier
        escrow_id: Escrow identifier (unused, kept for compatibility)
        worker_address: Worker's wallet address
        bounty_usdc: Bounty amount (unused, retrieved from state)
        partial_released: Amount already released (unused, tracked internally)

    Returns:
        Dict with release details
    """
    manager = get_manager()
    await manager.release_on_approval(
        task_id=task_id,
        worker_wallet=worker_address,
    )
    escrow = manager.get_escrow(task_id)

    return {
        "success": True,
        "tx_hashes": [r.tx_hash for r in escrow.release_txs] if escrow else [],
        "worker_payment": float(escrow.fees.net_to_worker)
        if escrow and escrow.fees
        else 0,
        "platform_fee": float(escrow.fees.platform_fee)
        if escrow and escrow.fees
        else 0,
        "total_released": float(escrow.released_amount) if escrow else 0,
        "type": "final",
    }


async def refund_on_cancel(
    task_id: str,
    escrow_id: str,  # Kept for API compatibility, not used
    reason: str = "Task cancelled",
) -> Dict[str, Any]:
    """
    Refund escrow when task is cancelled (NOW-023).

    Convenience function for cancel_task integration.

    Args:
        task_id: Task identifier
        escrow_id: Escrow identifier (unused, kept for compatibility)
        reason: Cancellation reason

    Returns:
        Dict with refund details
    """
    manager = get_manager()
    tx_hash = await manager.refund_on_cancel(
        task_id=task_id,
        reason=reason,
    )
    escrow = manager.get_escrow(task_id)

    return {
        "success": True,
        "tx_hash": tx_hash,
        "amount_refunded": float(escrow.total_amount) if escrow else 0,
        "type": "refund",
    }
