"""
Partial Release Payment System for Execution Market

Implements worker protection through partial payouts:
1. Release on submission (30-50% when evidence uploaded)
2. Release on completion (remaining after approval)
3. Rollback on valid rejection
4. Prorated completion scenarios

Addresses TODO items:
- NOW-091: Partial payout on submission (30-50% of bounty when evidence uploaded)
- NOW-092: Escrow split tracking with partial_released and partial_amount columns
- NOW-094: Partial rollback on valid rejection
- NOW-095: Partial completion scenarios (0-30% no pago, 30-70% proof of attempt, 70-90% prorated)
"""

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List

from ..integrations.x402.escrow import EscrowManager, FeeBreakdown, EscrowStatus
from ..integrations.x402.client import X402Error


# Configure logging
logger = logging.getLogger(__name__)


class CompletionTier(str, Enum):
    """Completion percentage tiers for prorated payouts."""
    NO_PAYMENT = "no_payment"           # 0-30%: No payout (insufficient attempt)
    PROOF_OF_ATTEMPT = "proof_of_attempt"  # 30-70%: Proof of attempt payment
    PRORATED = "prorated"               # 70-90%: Prorated based on completion
    FULL = "full"                       # 90-100%: Full payment


class PartialReleaseType(str, Enum):
    """Types of partial release operations."""
    SUBMISSION = "submission"       # Released when worker submits evidence
    COMPLETION = "completion"       # Released when agent approves
    PROOF_OF_ATTEMPT = "proof_of_attempt"  # Released for valid attempt
    PRORATED = "prorated"           # Released for partial completion
    ROLLBACK = "rollback"           # Clawed back on valid rejection


@dataclass
class PartialReleaseConfig:
    """
    Configuration for partial release percentages.

    Attributes:
        submission_percent: Percentage released on evidence submission (default 30%)
        min_submission_percent: Minimum submission release (default 30%)
        max_submission_percent: Maximum submission release (default 50%)
        proof_of_attempt_percent: Payment for valid but failed attempts (default 15%)
        rollback_enabled: Whether to allow rollback on valid rejection
        tier_thresholds: Completion percentage thresholds for each tier
    """
    submission_percent: float = 0.30  # 30% on submission
    min_submission_percent: float = 0.30
    max_submission_percent: float = 0.50
    proof_of_attempt_percent: float = 0.15  # 15% for valid attempt
    rollback_enabled: bool = True

    # Completion tier thresholds
    tier_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "no_payment_max": 0.30,      # 0-30% = no payment
        "proof_of_attempt_max": 0.70,  # 30-70% = proof of attempt
        "prorated_max": 0.90,        # 70-90% = prorated
        # 90-100% = full payment
    })


@dataclass
class PartialReleaseRecord:
    """
    Record of a partial release operation for audit trail.

    Attributes:
        task_id: Task identifier
        executor_id: Worker identifier
        release_type: Type of release operation
        amount_usdc: Amount released in USDC
        percentage: Percentage of total bounty
        tx_hash: Blockchain transaction hash
        timestamp: When the release occurred
        notes: Optional notes about the release
        metadata: Additional data for audit purposes
    """
    task_id: str
    executor_id: str
    release_type: PartialReleaseType
    amount_usdc: float
    percentage: float
    tx_hash: Optional[str]
    timestamp: datetime
    notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EscrowSplitState:
    """
    Tracks the current state of an escrow's partial releases.

    Addresses NOW-092: Escrow split tracking with partial_released and partial_amount.
    """
    task_id: str
    escrow_id: str
    total_bounty: float
    partial_released: bool  # Whether any partial has been released
    partial_amount: float   # Total amount released as partial
    remaining_amount: float
    release_records: List[PartialReleaseRecord] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PartialReleaseManager:
    """
    Manages partial release operations for Execution Market tasks.

    Features:
    - Release on submission: 30-50% when worker uploads evidence
    - Release on completion: Remaining bounty on approval
    - Rollback on rejection: Recover partial if rejection is valid
    - Prorated completion: Scale payment based on completion percentage

    Example:
        >>> manager = PartialReleaseManager()
        >>> # Worker submits evidence - release 30%
        >>> result = await manager.release_on_submission("task-123", "executor-456")
        >>> print(f"Released ${result['amount_released']:.2f}")

        >>> # Agent approves - release remaining
        >>> result = await manager.release_on_completion("task-123", "executor-456")
        >>> print(f"Final release: ${result['amount_released']:.2f}")
    """

    def __init__(
        self,
        config: Optional[PartialReleaseConfig] = None,
        escrow_manager: Optional[EscrowManager] = None,
    ):
        """
        Initialize partial release manager.

        Args:
            config: Configuration for partial release percentages
            escrow_manager: EscrowManager instance (creates one if not provided)
        """
        self.config = config or PartialReleaseConfig()
        self.escrow_manager = escrow_manager or EscrowManager()

        # In-memory state tracking (would be replaced by database in production)
        self._escrow_states: Dict[str, EscrowSplitState] = {}
        self._audit_log: List[PartialReleaseRecord] = []

    def _get_escrow_state(self, task_id: str) -> Optional[EscrowSplitState]:
        """Get current escrow state for a task."""
        return self._escrow_states.get(task_id)

    def _update_escrow_state(
        self,
        task_id: str,
        escrow_id: str,
        total_bounty: float,
        released_amount: float,
        record: PartialReleaseRecord,
    ) -> EscrowSplitState:
        """Update escrow state after a release operation."""
        state = self._escrow_states.get(task_id)

        if state is None:
            state = EscrowSplitState(
                task_id=task_id,
                escrow_id=escrow_id,
                total_bounty=total_bounty,
                partial_released=True,
                partial_amount=released_amount,
                remaining_amount=total_bounty - released_amount,
            )
        else:
            state.partial_released = True
            state.partial_amount += released_amount
            state.remaining_amount -= released_amount
            state.updated_at = datetime.now(timezone.utc)

        state.release_records.append(record)
        self._escrow_states[task_id] = state

        return state

    def _log_audit(self, record: PartialReleaseRecord) -> None:
        """Add record to audit trail."""
        self._audit_log.append(record)
        logger.info(
            f"Partial release: task={record.task_id}, "
            f"type={record.release_type.value}, "
            f"amount=${record.amount_usdc:.2f}, "
            f"percentage={record.percentage * 100:.1f}%"
        )

    def calculate_submission_amount(
        self,
        total_bounty: float,
        percentage: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate the amount to release on submission.

        Args:
            total_bounty: Total task bounty in USDC
            percentage: Override percentage (default: config.submission_percent)

        Returns:
            Dict with release_amount, percentage, and fee breakdown
        """
        # Use provided percentage or default
        pct = percentage or self.config.submission_percent

        # Clamp to configured min/max
        pct = max(self.config.min_submission_percent, min(self.config.max_submission_percent, pct))

        # Calculate fees on full bounty
        fees = self.escrow_manager.calculate_fees(total_bounty)

        # Calculate partial amount from net (after fees)
        net_bounty = Decimal(str(fees.net_to_worker))
        release_amount = float(net_bounty * Decimal(str(pct)))

        return {
            "release_amount": release_amount,
            "percentage": pct,
            "net_bounty": float(net_bounty),
            "remaining_after_release": float(net_bounty) - release_amount,
            "fees": {
                "platform_fee": fees.platform_fee,
                "fee_percent": fees.fee_percent,
            }
        }

    def calculate_prorated_release(
        self,
        total_bounty: float,
        completion_percentage: float,
    ) -> Dict[str, Any]:
        """
        Calculate prorated release based on completion percentage.

        Implements NOW-095: Partial completion scenarios:
        - 0-30%: No payment (insufficient attempt)
        - 30-70%: Proof of attempt payment (fixed percentage)
        - 70-90%: Prorated payment based on completion
        - 90-100%: Full payment

        Args:
            total_bounty: Total task bounty in USDC
            completion_percentage: Task completion percentage (0.0 to 1.0)

        Returns:
            Dict with tier, release_amount, and calculation details
        """
        # Clamp completion percentage
        completion = max(0.0, min(1.0, completion_percentage))

        # Calculate fees on full bounty
        fees = self.escrow_manager.calculate_fees(total_bounty)
        net_bounty = float(fees.net_to_worker)

        thresholds = self.config.tier_thresholds

        # Determine tier and calculate amount
        if completion <= thresholds["no_payment_max"]:
            # 0-30%: No payment
            tier = CompletionTier.NO_PAYMENT
            release_amount = 0.0
            payout_percentage = 0.0
            notes = "Insufficient completion for payment"

        elif completion <= thresholds["proof_of_attempt_max"]:
            # 30-70%: Proof of attempt
            tier = CompletionTier.PROOF_OF_ATTEMPT
            payout_percentage = self.config.proof_of_attempt_percent
            release_amount = net_bounty * payout_percentage
            notes = "Proof of attempt payment for valid but incomplete work"

        elif completion <= thresholds["prorated_max"]:
            # 70-90%: Prorated payment
            tier = CompletionTier.PRORATED
            # Linear scale from 70% completion = 70% payout to 90% = 90%
            payout_percentage = completion
            release_amount = net_bounty * payout_percentage
            notes = f"Prorated payment at {completion * 100:.1f}% completion"

        else:
            # 90-100%: Full payment
            tier = CompletionTier.FULL
            payout_percentage = 1.0
            release_amount = net_bounty
            notes = "Full payment for substantially complete work"

        return {
            "tier": tier.value,
            "completion_percentage": completion,
            "payout_percentage": payout_percentage,
            "release_amount": release_amount,
            "net_bounty": net_bounty,
            "notes": notes,
            "thresholds": thresholds,
        }

    async def release_on_submission(
        self,
        task_id: str,
        executor_id: str,
        escrow_id: str,
        total_bounty: float,
        worker_address: str,
        percentage: float = 0.30,
    ) -> Dict[str, Any]:
        """
        Release partial payment when worker submits evidence.

        Implements NOW-091: Partial payout on submission (30-50% of bounty when evidence uploaded).

        Args:
            task_id: Task identifier
            executor_id: Worker identifier
            escrow_id: Escrow identifier
            total_bounty: Total bounty amount in USDC
            worker_address: Worker's wallet address
            percentage: Percentage to release (default 30%, max 50%)

        Returns:
            Dict with release details and transaction info

        Raises:
            X402Error: If release fails
            ValueError: If escrow already has partial release
        """
        # Check if partial already released
        existing_state = self._get_escrow_state(task_id)
        if existing_state and existing_state.partial_released:
            raise ValueError(f"Partial already released for task {task_id}")

        # Calculate release amount
        calc = self.calculate_submission_amount(total_bounty, percentage)
        release_amount = calc["release_amount"]

        # Execute release via escrow manager
        result = await self.escrow_manager.release_partial(
            task_id=task_id,
            escrow_id=escrow_id,
            worker_address=worker_address,
            total_bounty=total_bounty,
        )

        if not result.get("success"):
            raise X402Error(f"Failed to release partial payment: {result.get('error')}")

        # Create audit record
        record = PartialReleaseRecord(
            task_id=task_id,
            executor_id=executor_id,
            release_type=PartialReleaseType.SUBMISSION,
            amount_usdc=result["amount_released"],
            percentage=percentage,
            tx_hash=result.get("tx_hash"),
            timestamp=datetime.now(timezone.utc),
            notes="Partial release on evidence submission",
            metadata={
                "escrow_id": escrow_id,
                "worker_address": worker_address,
                "total_bounty": total_bounty,
            }
        )

        # Update state and log
        self._update_escrow_state(
            task_id=task_id,
            escrow_id=escrow_id,
            total_bounty=total_bounty,
            released_amount=result["amount_released"],
            record=record,
        )
        self._log_audit(record)

        return {
            "success": True,
            "task_id": task_id,
            "executor_id": executor_id,
            "amount_released": result["amount_released"],
            "percentage_released": percentage,
            "remaining_amount": calc["remaining_after_release"],
            "tx_hash": result.get("tx_hash"),
            "type": PartialReleaseType.SUBMISSION.value,
            "timestamp": record.timestamp.isoformat(),
        }

    async def release_on_completion(
        self,
        task_id: str,
        executor_id: str,
        escrow_id: Optional[str] = None,
        total_bounty: Optional[float] = None,
        worker_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Release remaining payment when task is approved.

        Args:
            task_id: Task identifier
            executor_id: Worker identifier
            escrow_id: Escrow identifier (optional if state exists)
            total_bounty: Total bounty amount (optional if state exists)
            worker_address: Worker's wallet address

        Returns:
            Dict with release details and transaction info

        Raises:
            X402Error: If release fails
            ValueError: If missing required parameters
        """
        # Get existing state
        state = self._get_escrow_state(task_id)

        # Use state values if available
        if state:
            escrow_id = escrow_id or state.escrow_id
            total_bounty = total_bounty or state.total_bounty
            partial_released = state.partial_amount
        else:
            partial_released = 0.0

        # Validate required parameters
        if not escrow_id or not total_bounty or not worker_address:
            raise ValueError("Missing required parameters: escrow_id, total_bounty, worker_address")

        # Execute final release
        result = await self.escrow_manager.release_final(
            task_id=task_id,
            escrow_id=escrow_id,
            worker_address=worker_address,
            total_bounty=total_bounty,
            partial_already_released=partial_released,
        )

        if not result.get("success"):
            raise X402Error(f"Failed to release final payment: {result.get('error')}")

        # Create audit record
        record = PartialReleaseRecord(
            task_id=task_id,
            executor_id=executor_id,
            release_type=PartialReleaseType.COMPLETION,
            amount_usdc=result["worker_payment"],
            percentage=1.0 - (partial_released / total_bounty) if partial_released else 1.0,
            tx_hash=result["tx_hashes"][0] if result.get("tx_hashes") else None,
            timestamp=datetime.now(timezone.utc),
            notes="Final release on task approval",
            metadata={
                "escrow_id": escrow_id,
                "worker_address": worker_address,
                "total_bounty": total_bounty,
                "partial_already_released": partial_released,
                "platform_fee": result.get("platform_fee"),
            }
        )

        # Update state and log
        self._update_escrow_state(
            task_id=task_id,
            escrow_id=escrow_id,
            total_bounty=total_bounty,
            released_amount=result["worker_payment"],
            record=record,
        )
        self._log_audit(record)

        return {
            "success": True,
            "task_id": task_id,
            "executor_id": executor_id,
            "amount_released": result["worker_payment"],
            "total_released": result["total_released"],
            "platform_fee": result.get("platform_fee"),
            "tx_hashes": result.get("tx_hashes", []),
            "type": PartialReleaseType.COMPLETION.value,
            "timestamp": record.timestamp.isoformat(),
        }

    async def rollback_partial(
        self,
        task_id: str,
        reason: str,
        executor_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Rollback partial payment on valid rejection.

        Implements NOW-094: Partial rollback on valid rejection.

        Note: This is a soft rollback that marks the release as clawed back.
        The actual funds recovery depends on the escrow contract supporting
        partial refunds, which may require additional contract logic.

        Args:
            task_id: Task identifier
            reason: Reason for rollback
            executor_id: Worker identifier (optional)
            agent_id: Agent who rejected (optional)

        Returns:
            Dict with rollback status and details

        Raises:
            ValueError: If rollback not enabled or no partial to rollback
        """
        if not self.config.rollback_enabled:
            raise ValueError("Partial rollback is not enabled in configuration")

        # Get existing state
        state = self._get_escrow_state(task_id)

        if not state or not state.partial_released:
            raise ValueError(f"No partial release to rollback for task {task_id}")

        # Calculate rollback amount
        rollback_amount = state.partial_amount

        # Create audit record for rollback
        record = PartialReleaseRecord(
            task_id=task_id,
            executor_id=executor_id or "unknown",
            release_type=PartialReleaseType.ROLLBACK,
            amount_usdc=-rollback_amount,  # Negative to indicate rollback
            percentage=-(rollback_amount / state.total_bounty),
            tx_hash=None,  # Would be populated if on-chain rollback
            timestamp=datetime.now(timezone.utc),
            notes=f"Rollback on valid rejection: {reason}",
            metadata={
                "escrow_id": state.escrow_id,
                "agent_id": agent_id,
                "original_partial_amount": rollback_amount,
                "reason": reason,
            }
        )

        # Update state to reflect rollback
        state.partial_amount = 0.0
        state.remaining_amount = state.total_bounty
        state.partial_released = False
        state.updated_at = datetime.now(timezone.utc)
        state.release_records.append(record)

        self._log_audit(record)

        logger.warning(
            f"Partial rollback executed: task={task_id}, "
            f"amount=${rollback_amount:.2f}, reason={reason}"
        )

        return {
            "success": True,
            "task_id": task_id,
            "rollback_amount": rollback_amount,
            "reason": reason,
            "type": PartialReleaseType.ROLLBACK.value,
            "timestamp": record.timestamp.isoformat(),
            "note": "Soft rollback recorded. On-chain recovery depends on escrow contract capabilities.",
        }

    async def release_prorated(
        self,
        task_id: str,
        executor_id: str,
        escrow_id: str,
        total_bounty: float,
        worker_address: str,
        completion_percentage: float,
    ) -> Dict[str, Any]:
        """
        Release prorated payment based on completion percentage.

        Implements NOW-095: Partial completion scenarios:
        - 0-30%: No payment
        - 30-70%: Proof of attempt (15%)
        - 70-90%: Prorated
        - 90-100%: Full payment

        Args:
            task_id: Task identifier
            executor_id: Worker identifier
            escrow_id: Escrow identifier
            total_bounty: Total bounty amount
            worker_address: Worker's wallet address
            completion_percentage: Assessed completion (0.0 to 1.0)

        Returns:
            Dict with release details and tier information
        """
        # Calculate prorated amount
        calc = self.calculate_prorated_release(total_bounty, completion_percentage)

        if calc["tier"] == CompletionTier.NO_PAYMENT.value:
            # No payment tier - just log and return
            record = PartialReleaseRecord(
                task_id=task_id,
                executor_id=executor_id,
                release_type=PartialReleaseType.PRORATED,
                amount_usdc=0.0,
                percentage=0.0,
                tx_hash=None,
                timestamp=datetime.now(timezone.utc),
                notes=calc["notes"],
                metadata={
                    "completion_percentage": completion_percentage,
                    "tier": calc["tier"],
                }
            )
            self._log_audit(record)

            return {
                "success": True,
                "task_id": task_id,
                "executor_id": executor_id,
                "amount_released": 0.0,
                "completion_percentage": completion_percentage,
                "tier": calc["tier"],
                "notes": calc["notes"],
                "type": PartialReleaseType.PRORATED.value,
                "timestamp": record.timestamp.isoformat(),
            }

        # Get existing state for partial_already_released
        state = self._get_escrow_state(task_id)
        partial_already_released = state.partial_amount if state else 0.0

        # Determine release type
        if calc["tier"] == CompletionTier.PROOF_OF_ATTEMPT.value:
            release_type = PartialReleaseType.PROOF_OF_ATTEMPT
        else:
            release_type = PartialReleaseType.PRORATED

        # Calculate actual amount to release (accounting for any partial already released)
        target_release = calc["release_amount"]
        actual_release = max(0.0, target_release - partial_already_released)

        if actual_release <= 0:
            # Already released enough via partial
            return {
                "success": True,
                "task_id": task_id,
                "executor_id": executor_id,
                "amount_released": 0.0,
                "total_received": partial_already_released,
                "completion_percentage": completion_percentage,
                "tier": calc["tier"],
                "notes": "No additional release needed - partial already exceeds prorated amount",
                "type": release_type.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # Execute release
        # For prorated, we release the calculated amount instead of using release_final
        # which would release the full remaining amount
        from ..integrations.x402.client import X402Client
        client = self.escrow_manager.client

        result = await client.release_escrow(
            escrow_id=escrow_id,
            recipient=worker_address,
            amount_usdc=actual_release,
        )

        if not result.success:
            raise X402Error(f"Failed to release prorated payment: {result.error}")

        # Create audit record
        record = PartialReleaseRecord(
            task_id=task_id,
            executor_id=executor_id,
            release_type=release_type,
            amount_usdc=actual_release,
            percentage=calc["payout_percentage"],
            tx_hash=result.tx_hash,
            timestamp=datetime.now(timezone.utc),
            notes=calc["notes"],
            metadata={
                "escrow_id": escrow_id,
                "worker_address": worker_address,
                "completion_percentage": completion_percentage,
                "tier": calc["tier"],
                "target_release": target_release,
                "partial_already_released": partial_already_released,
            }
        )

        # Update state and log
        self._update_escrow_state(
            task_id=task_id,
            escrow_id=escrow_id,
            total_bounty=total_bounty,
            released_amount=actual_release,
            record=record,
        )
        self._log_audit(record)

        return {
            "success": True,
            "task_id": task_id,
            "executor_id": executor_id,
            "amount_released": actual_release,
            "total_received": partial_already_released + actual_release,
            "completion_percentage": completion_percentage,
            "payout_percentage": calc["payout_percentage"],
            "tier": calc["tier"],
            "notes": calc["notes"],
            "tx_hash": result.tx_hash,
            "type": release_type.value,
            "timestamp": record.timestamp.isoformat(),
        }

    def get_escrow_split_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current escrow split state for a task.

        Implements NOW-092: Escrow split tracking.

        Args:
            task_id: Task identifier

        Returns:
            Dict with escrow state or None if not found
        """
        state = self._get_escrow_state(task_id)
        if not state:
            return None

        return {
            "task_id": state.task_id,
            "escrow_id": state.escrow_id,
            "total_bounty": state.total_bounty,
            "partial_released": state.partial_released,
            "partial_amount": state.partial_amount,
            "remaining_amount": state.remaining_amount,
            "release_count": len(state.release_records),
            "releases": [
                {
                    "type": r.release_type.value,
                    "amount": r.amount_usdc,
                    "percentage": r.percentage,
                    "timestamp": r.timestamp.isoformat(),
                    "tx_hash": r.tx_hash,
                }
                for r in state.release_records
            ],
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
        }

    def get_audit_trail(
        self,
        task_id: Optional[str] = None,
        executor_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get audit trail of partial release operations.

        Args:
            task_id: Filter by task (optional)
            executor_id: Filter by executor (optional)
            limit: Maximum records to return

        Returns:
            List of audit records
        """
        records = self._audit_log

        # Apply filters
        if task_id:
            records = [r for r in records if r.task_id == task_id]
        if executor_id:
            records = [r for r in records if r.executor_id == executor_id]

        # Sort by timestamp descending and limit
        records = sorted(records, key=lambda r: r.timestamp, reverse=True)[:limit]

        return [
            {
                "task_id": r.task_id,
                "executor_id": r.executor_id,
                "type": r.release_type.value,
                "amount_usdc": r.amount_usdc,
                "percentage": r.percentage,
                "tx_hash": r.tx_hash,
                "timestamp": r.timestamp.isoformat(),
                "notes": r.notes,
                "metadata": r.metadata,
            }
            for r in records
        ]


# Convenience functions for common operations

async def release_partial_on_submission(
    task_id: str,
    executor_id: str,
    escrow_id: str,
    total_bounty: float,
    worker_address: str,
    percentage: float = 0.30,
) -> Dict[str, Any]:
    """
    Convenience function to release partial on submission.

    Args:
        task_id: Task identifier
        executor_id: Worker identifier
        escrow_id: Escrow identifier
        total_bounty: Total bounty in USDC
        worker_address: Worker's wallet
        percentage: Release percentage (default 30%)

    Returns:
        Dict with release details
    """
    manager = PartialReleaseManager()
    return await manager.release_on_submission(
        task_id=task_id,
        executor_id=executor_id,
        escrow_id=escrow_id,
        total_bounty=total_bounty,
        worker_address=worker_address,
        percentage=percentage,
    )


async def release_on_task_completion(
    task_id: str,
    executor_id: str,
    escrow_id: str,
    total_bounty: float,
    worker_address: str,
    partial_already_released: float = 0.0,
) -> Dict[str, Any]:
    """
    Convenience function to release remaining on completion.

    Args:
        task_id: Task identifier
        executor_id: Worker identifier
        escrow_id: Escrow identifier
        total_bounty: Total bounty in USDC
        worker_address: Worker's wallet
        partial_already_released: Amount already released

    Returns:
        Dict with release details
    """
    manager = PartialReleaseManager()

    # Pre-populate state if partial was already released
    if partial_already_released > 0:
        manager._escrow_states[task_id] = EscrowSplitState(
            task_id=task_id,
            escrow_id=escrow_id,
            total_bounty=total_bounty,
            partial_released=True,
            partial_amount=partial_already_released,
            remaining_amount=total_bounty - partial_already_released,
        )

    return await manager.release_on_completion(
        task_id=task_id,
        executor_id=executor_id,
        escrow_id=escrow_id,
        total_bounty=total_bounty,
        worker_address=worker_address,
    )


def calculate_completion_tier(completion_percentage: float) -> Dict[str, Any]:
    """
    Calculate which tier a completion percentage falls into.

    Args:
        completion_percentage: Task completion (0.0 to 1.0)

    Returns:
        Dict with tier, payout rules, and thresholds
    """
    manager = PartialReleaseManager()
    return manager.calculate_prorated_release(
        total_bounty=100.0,  # Use $100 for percentage calculation
        completion_percentage=completion_percentage,
    )
