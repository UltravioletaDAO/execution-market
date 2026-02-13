"""
Agent Bond Management for Execution Market

Implements the agent bonding mechanism that protects workers from unfair rejections.
Agents deposit bounty + 10-20% extra as a bond that gets slashed if they unfairly reject work.

References:
- NOW-096: Agent bond mechanism (bounty + 10-20% extra as bond)
- NOW-097: Proof of attempt payout (10-20% for valid attempt even if failed)
- NOW-098: Minimum net payout validation ($0.50 minimum after fees)
- NOW-099: Minimum payout by task_type (simple $0.50, physical $1.00, authority $5.00)
"""

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List

from ..integrations.x402.client import X402Client, X402Error


# =============================================================================
# Configuration Dataclasses
# =============================================================================


class TaskType(str, Enum):
    """Types of tasks with different minimum payout requirements."""

    SIMPLE = "simple"  # Digital tasks, data entry
    PHYSICAL = "physical"  # Requires physical presence
    AUTHORITY = "authority"  # Requires licensed professional
    SENSORY = "sensory"  # Taste tests, inspections
    EMERGENCY = "emergency"  # Time-critical tasks


class BondStatus(str, Enum):
    """Status of a locked bond."""

    LOCKED = "locked"
    RELEASED = "released"
    PARTIALLY_RELEASED = "partially_released"
    SLASHED = "slashed"


@dataclass
class BondConfig:
    """
    Configuration for agent bonding mechanism.

    Attributes:
        default_bond_percent: Default bond percentage (10-20% of bounty)
        min_bond_percent: Minimum allowed bond percentage
        max_bond_percent: Maximum allowed bond percentage
        proof_of_attempt_percent: Payout for valid attempt (10-20%)
        min_proof_of_attempt_usd: Minimum proof of attempt payout
        min_net_payout_usd: Global minimum net payout after fees ($0.50)
        platform_fee_percent: Platform fee deducted from bounty
    """

    default_bond_percent: Decimal = Decimal("0.15")  # 15% default
    min_bond_percent: Decimal = Decimal("0.10")  # 10% minimum
    max_bond_percent: Decimal = Decimal("0.20")  # 20% maximum
    proof_of_attempt_percent: Decimal = Decimal("0.15")  # 15% for valid attempt
    min_proof_of_attempt_usd: Decimal = Decimal("0.50")  # Minimum $0.50
    min_net_payout_usd: Decimal = Decimal("0.50")  # Global minimum
    platform_fee_percent: Decimal = Decimal("0.13")  # 13% platform fee


@dataclass
class TaskTypeConfig:
    """
    Minimum payout configuration by task type.

    NOW-099: Different task types have different minimum payouts to ensure
    workers are fairly compensated for different effort levels.
    """

    task_type: TaskType
    min_bounty_usd: Decimal
    min_net_payout_usd: Decimal
    description: str


# Default minimum payouts by task type (NOW-099)
TASK_TYPE_MINIMUMS: Dict[TaskType, TaskTypeConfig] = {
    TaskType.SIMPLE: TaskTypeConfig(
        task_type=TaskType.SIMPLE,
        min_bounty_usd=Decimal("0.75"),  # To achieve ~$0.50 net after 13% fee
        min_net_payout_usd=Decimal("0.50"),
        description="Simple digital tasks (data entry, screenshots)",
    ),
    TaskType.PHYSICAL: TaskTypeConfig(
        task_type=TaskType.PHYSICAL,
        min_bounty_usd=Decimal("1.50"),  # To achieve $1.00 net after fees
        min_net_payout_usd=Decimal("1.00"),
        description="Tasks requiring physical presence",
    ),
    TaskType.AUTHORITY: TaskTypeConfig(
        task_type=TaskType.AUTHORITY,
        min_bounty_usd=Decimal("7.00"),  # To achieve $5.00 net after fees
        min_net_payout_usd=Decimal("5.00"),
        description="Tasks requiring licensed professionals",
    ),
    TaskType.SENSORY: TaskTypeConfig(
        task_type=TaskType.SENSORY,
        min_bounty_usd=Decimal("2.00"),  # To achieve $1.50 net after fees
        min_net_payout_usd=Decimal("1.50"),
        description="Taste tests, quality inspections",
    ),
    TaskType.EMERGENCY: TaskTypeConfig(
        task_type=TaskType.EMERGENCY,
        min_bounty_usd=Decimal("3.00"),  # To achieve $2.50 net after fees
        min_net_payout_usd=Decimal("2.50"),
        description="Time-critical tasks",
    ),
}


@dataclass
class LockedBond:
    """
    Represents a bond locked for a specific task.

    Attributes:
        bond_id: Unique identifier for this bond
        agent_id: The agent who deposited the bond
        task_id: The task this bond is associated with
        amount_usd: Amount locked as bond
        bounty_usd: The original bounty amount
        bond_percent: The percentage used for this bond
        escrow_id: x402 escrow ID holding the bond
        status: Current status of the bond
        locked_at: When the bond was locked
        released_at: When the bond was released (if applicable)
        slash_reason: Reason for slashing (if applicable)
        slash_amount: Amount slashed (if partially slashed)
    """

    bond_id: str
    agent_id: str
    task_id: str
    amount_usd: Decimal
    bounty_usd: Decimal
    bond_percent: Decimal
    escrow_id: str
    status: BondStatus = BondStatus.LOCKED
    locked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    released_at: Optional[datetime] = None
    slash_reason: Optional[str] = None
    slash_amount: Optional[Decimal] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BondCalculation:
    """
    Result of bond calculation for a task.

    Shows the complete breakdown of what an agent needs to deposit.
    """

    bounty_usd: Decimal
    bond_percent: Decimal
    bond_amount_usd: Decimal
    platform_fee_usd: Decimal
    total_deposit_usd: Decimal
    net_payout_to_worker: Decimal
    proof_of_attempt_amount: Decimal
    task_type: TaskType
    is_valid: bool
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class ProofOfAttemptResult:
    """
    Result of a proof of attempt payout.

    When a worker documents a valid obstacle (guard, closed location, etc.),
    they receive a portion of the bounty for their effort.
    """

    task_id: str
    executor_id: str
    attempt_score: float  # 0.0 to 1.0, how valid the attempt was
    base_payout_usd: Decimal
    actual_payout_usd: Decimal  # Scaled by attempt_score
    tx_hash: Optional[str]
    success: bool
    error: Optional[str] = None


# =============================================================================
# Agent Bond Manager
# =============================================================================


class AgentBondManager:
    """
    Manages agent bonds for Execution Market tasks.

    The bond mechanism protects workers from unfair rejections:
    - Agents deposit bounty + 10-20% extra as bond
    - Bond is returned if they approve valid work
    - Bond is slashed if arbitration finds unfair rejection
    - Proof of attempt pays workers for documented obstacles

    Example:
        >>> manager = AgentBondManager()
        >>> calc = manager.calculate_required_bond(10.0, TaskType.PHYSICAL)
        >>> print(f"Total deposit needed: ${calc.total_deposit_usd}")
        Total deposit needed: $11.95
        >>> bond = await manager.lock_bond("agent123", "task456", calc.bond_amount_usd)
    """

    def __init__(
        self,
        config: Optional[BondConfig] = None,
        x402_client: Optional[X402Client] = None,
    ):
        """
        Initialize bond manager.

        Args:
            config: Bond configuration (uses defaults if not provided)
            x402_client: X402 client for escrow operations
        """
        self.config = config or BondConfig()
        self.client = x402_client or X402Client()

        # In-memory storage for bonds (would be database in production)
        self._bonds: Dict[str, LockedBond] = {}

        # Treasury address for slashed bonds
        self.treasury_address = os.environ.get(
            "EM_TREASURY_ADDRESS", "0x0000000000000000000000000000000000000000"
        )

        # Worker Protection Fund address (receives slashed bonds)
        self.protection_fund_address = os.environ.get(
            "EM_PROTECTION_FUND_ADDRESS", "0x0000000000000000000000000000000000000000"
        )

    # -------------------------------------------------------------------------
    # Bond Calculation (NOW-096, NOW-098, NOW-099)
    # -------------------------------------------------------------------------

    def calculate_required_bond(
        self,
        bounty_usd: float,
        task_type: TaskType,
        custom_bond_percent: Optional[float] = None,
    ) -> BondCalculation:
        """
        Calculate the required bond for a task.

        Args:
            bounty_usd: The bounty amount in USD
            task_type: Type of task (affects minimum payout requirements)
            custom_bond_percent: Optional custom bond percentage (0.10-0.20)

        Returns:
            BondCalculation with full breakdown and validation

        Example:
            >>> calc = manager.calculate_required_bond(10.0, TaskType.PHYSICAL)
            >>> calc.total_deposit_usd
            Decimal('11.95')  # $10 bounty + $1.50 bond + $0.80 fee - adjusted
        """
        bounty = Decimal(str(bounty_usd))
        validation_errors: List[str] = []

        # Determine bond percentage
        if custom_bond_percent is not None:
            bond_percent = Decimal(str(custom_bond_percent))
            if bond_percent < self.config.min_bond_percent:
                validation_errors.append(
                    f"Bond percent {bond_percent} is below minimum {self.config.min_bond_percent}"
                )
                bond_percent = self.config.min_bond_percent
            elif bond_percent > self.config.max_bond_percent:
                validation_errors.append(
                    f"Bond percent {bond_percent} exceeds maximum {self.config.max_bond_percent}"
                )
                bond_percent = self.config.max_bond_percent
        else:
            bond_percent = self.config.default_bond_percent

        # Calculate amounts
        bond_amount = bounty * bond_percent
        platform_fee = bounty * self.config.platform_fee_percent
        total_deposit = bounty + bond_amount + platform_fee
        net_payout = bounty - platform_fee

        # Calculate proof of attempt amount
        proof_of_attempt = max(
            bounty * self.config.proof_of_attempt_percent,
            self.config.min_proof_of_attempt_usd,
        )

        # Validate minimum payouts (NOW-098, NOW-099)
        type_config = TASK_TYPE_MINIMUMS.get(task_type)
        if type_config:
            if bounty < type_config.min_bounty_usd:
                validation_errors.append(
                    f"Bounty ${bounty} is below minimum ${type_config.min_bounty_usd} "
                    f"for {task_type.value} tasks"
                )
            if net_payout < type_config.min_net_payout_usd:
                validation_errors.append(
                    f"Net payout ${net_payout} is below minimum "
                    f"${type_config.min_net_payout_usd} for {task_type.value} tasks"
                )

        # Global minimum check (NOW-098)
        if net_payout < self.config.min_net_payout_usd:
            validation_errors.append(
                f"Net payout ${net_payout} is below global minimum "
                f"${self.config.min_net_payout_usd}"
            )

        return BondCalculation(
            bounty_usd=bounty,
            bond_percent=bond_percent,
            bond_amount_usd=bond_amount,
            platform_fee_usd=platform_fee,
            total_deposit_usd=total_deposit,
            net_payout_to_worker=net_payout,
            proof_of_attempt_amount=proof_of_attempt,
            task_type=task_type,
            is_valid=len(validation_errors) == 0,
            validation_errors=validation_errors,
        )

    def validate_minimum_payout(
        self,
        bounty_usd: float,
        task_type: TaskType,
    ) -> tuple[bool, List[str]]:
        """
        Validate that a bounty meets minimum payout requirements.

        Args:
            bounty_usd: Proposed bounty amount
            task_type: Type of task

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        calc = self.calculate_required_bond(bounty_usd, task_type)
        return calc.is_valid, calc.validation_errors

    def get_minimum_bounty_for_type(self, task_type: TaskType) -> Decimal:
        """
        Get the minimum bounty required for a task type.

        Args:
            task_type: Type of task

        Returns:
            Minimum bounty in USD
        """
        type_config = TASK_TYPE_MINIMUMS.get(task_type)
        if type_config:
            return type_config.min_bounty_usd

        # Calculate minimum to achieve global minimum net payout
        # net = bounty * (1 - fee_percent)
        # min_net = min_bounty * (1 - fee_percent)
        # min_bounty = min_net / (1 - fee_percent)
        return self.config.min_net_payout_usd / (1 - self.config.platform_fee_percent)

    # -------------------------------------------------------------------------
    # Bond Locking / Unlocking (NOW-096)
    # -------------------------------------------------------------------------

    async def lock_bond(
        self,
        agent_id: str,
        task_id: str,
        bounty_usd: float,
        task_type: TaskType = TaskType.SIMPLE,
        custom_bond_percent: Optional[float] = None,
        timeout_hours: int = 72,
    ) -> LockedBond:
        """
        Lock a bond for a task in x402 escrow.

        Args:
            agent_id: The agent depositing the bond
            task_id: The task this bond is for
            bounty_usd: The bounty amount (bond is calculated from this)
            task_type: Type of task for minimum validation
            custom_bond_percent: Optional custom bond percentage
            timeout_hours: Hours until bond can be auto-released

        Returns:
            LockedBond with escrow details

        Raises:
            ValueError: If bounty doesn't meet minimum requirements
            X402Error: If escrow creation fails
        """
        # Calculate bond
        calc = self.calculate_required_bond(bounty_usd, task_type, custom_bond_percent)

        if not calc.is_valid:
            raise ValueError(
                f"Bond validation failed: {'; '.join(calc.validation_errors)}"
            )

        # Create escrow for the bond amount
        result = await self.client.create_escrow(
            task_id=f"bond_{task_id}",
            amount_usdc=float(calc.bond_amount_usd),
            beneficiary=agent_id,  # Agent gets it back on success
            timeout_hours=timeout_hours,
        )

        if not result.success:
            raise X402Error(f"Failed to create bond escrow: {result.error}")

        # Create bond record
        bond = LockedBond(
            bond_id=str(uuid.uuid4()),
            agent_id=agent_id,
            task_id=task_id,
            amount_usd=calc.bond_amount_usd,
            bounty_usd=calc.bounty_usd,
            bond_percent=calc.bond_percent,
            escrow_id=result.escrow_id,
            status=BondStatus.LOCKED,
            metadata={
                "task_type": task_type.value,
                "tx_hash": result.tx_hash,
                "timeout_timestamp": result.timeout_timestamp,
            },
        )

        # Store bond
        self._bonds[bond.bond_id] = bond

        return bond

    async def release_bond(
        self,
        agent_id: str,
        task_id: str,
    ) -> Dict[str, Any]:
        """
        Release a bond back to the agent after successful task completion.

        Called when:
        - Agent approves worker's submission
        - Task expires without claims

        Args:
            agent_id: The agent who deposited the bond
            task_id: The task ID

        Returns:
            Dict with release details and transaction info

        Raises:
            ValueError: If bond not found or already processed
            X402Error: If release fails
        """
        # Find the bond
        bond = self._find_bond(agent_id, task_id)
        if not bond:
            raise ValueError(f"No bond found for agent {agent_id} on task {task_id}")

        if bond.status != BondStatus.LOCKED:
            raise ValueError(f"Bond is not locked (status: {bond.status})")

        # Release from escrow back to agent
        result = await self.client.release_escrow(
            escrow_id=bond.escrow_id,
            recipient=agent_id,
            amount_usdc=float(bond.amount_usd),
        )

        if not result.success:
            raise X402Error(f"Failed to release bond: {result.error}")

        # Update bond status
        bond.status = BondStatus.RELEASED
        bond.released_at = datetime.now(timezone.utc)

        return {
            "success": True,
            "bond_id": bond.bond_id,
            "amount_released": float(bond.amount_usd),
            "tx_hash": result.tx_hash,
            "message": "Bond released back to agent",
        }

    async def slash_bond(
        self,
        agent_id: str,
        task_id: str,
        reason: str,
        slash_amount: Optional[float] = None,
        recipient: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Slash an agent's bond for unfair rejection.

        Called when arbitration finds the agent unfairly rejected valid work.
        The slashed amount goes to:
        1. The worker (if specified as recipient)
        2. The Worker Protection Fund (default)

        Args:
            agent_id: The agent whose bond is slashed
            task_id: The task ID
            reason: Reason for slashing (for audit trail)
            slash_amount: Amount to slash (defaults to full bond)
            recipient: Where to send slashed funds (default: protection fund)

        Returns:
            Dict with slash details

        Raises:
            ValueError: If bond not found or invalid state
            X402Error: If slash transaction fails
        """
        # Find the bond
        bond = self._find_bond(agent_id, task_id)
        if not bond:
            raise ValueError(f"No bond found for agent {agent_id} on task {task_id}")

        if bond.status not in (BondStatus.LOCKED, BondStatus.PARTIALLY_RELEASED):
            raise ValueError(f"Bond cannot be slashed (status: {bond.status})")

        # Determine slash amount
        amount_to_slash = (
            Decimal(str(slash_amount)) if slash_amount else bond.amount_usd
        )
        if amount_to_slash > bond.amount_usd:
            amount_to_slash = bond.amount_usd

        # Determine recipient
        target_address = recipient or self.protection_fund_address

        # Execute slash via escrow release
        result = await self.client.release_escrow(
            escrow_id=bond.escrow_id,
            recipient=target_address,
            amount_usdc=float(amount_to_slash),
        )

        if not result.success:
            raise X402Error(f"Failed to slash bond: {result.error}")

        # Update bond status
        remaining = bond.amount_usd - amount_to_slash
        if remaining <= 0:
            bond.status = BondStatus.SLASHED
        else:
            bond.status = BondStatus.PARTIALLY_RELEASED

        bond.slash_reason = reason
        bond.slash_amount = amount_to_slash
        bond.released_at = datetime.now(timezone.utc)

        return {
            "success": True,
            "bond_id": bond.bond_id,
            "amount_slashed": float(amount_to_slash),
            "remaining_bond": float(remaining),
            "recipient": target_address,
            "reason": reason,
            "tx_hash": result.tx_hash,
            "message": f"Bond slashed: {reason}",
        }

    # -------------------------------------------------------------------------
    # Proof of Attempt (NOW-097)
    # -------------------------------------------------------------------------

    async def pay_proof_of_attempt(
        self,
        task_id: str,
        executor_id: str,
        attempt_score: float,
        bounty_usd: float,
        escrow_id: str,
        obstacle_description: Optional[str] = None,
    ) -> ProofOfAttemptResult:
        """
        Pay a worker for a valid attempt that couldn't be completed.

        When a worker documents a legitimate obstacle (guard, closed location,
        private property, etc.), they receive 10-20% of the bounty for their
        effort and displacement.

        The attempt_score (0.0-1.0) scales the payout:
        - 1.0: Full proof of attempt (clear documentation of obstacle)
        - 0.7-0.9: Good attempt (some documentation issues)
        - 0.3-0.6: Partial attempt (minimal documentation)
        - 0.0-0.3: No payout (insufficient proof)

        Args:
            task_id: The task that couldn't be completed
            executor_id: The worker who made the attempt
            attempt_score: Score from 0.0 to 1.0 for attempt validity
            bounty_usd: Original bounty amount
            escrow_id: Escrow ID holding the bounty
            obstacle_description: Description of the obstacle encountered

        Returns:
            ProofOfAttemptResult with payout details

        Example:
            >>> result = await manager.pay_proof_of_attempt(
            ...     task_id="task123",
            ...     executor_id="worker456",
            ...     attempt_score=0.85,  # Good documentation
            ...     bounty_usd=10.0,
            ...     escrow_id="escrow789",
            ...     obstacle_description="Location was closed due to holiday"
            ... )
            >>> result.actual_payout_usd
            Decimal('1.275')  # $1.50 base * 0.85 score
        """
        bounty = Decimal(str(bounty_usd))
        score = max(0.0, min(1.0, attempt_score))  # Clamp to 0-1

        # Calculate base proof of attempt payout
        base_payout = max(
            bounty * self.config.proof_of_attempt_percent,
            self.config.min_proof_of_attempt_usd,
        )

        # Scale by attempt score
        actual_payout = base_payout * Decimal(str(score))

        # Minimum threshold: if score < 0.3, no payout
        if score < 0.3:
            return ProofOfAttemptResult(
                task_id=task_id,
                executor_id=executor_id,
                attempt_score=score,
                base_payout_usd=base_payout,
                actual_payout_usd=Decimal("0"),
                tx_hash=None,
                success=False,
                error=f"Attempt score {score} is below minimum threshold (0.3)",
            )

        # Execute payout from bounty escrow
        try:
            result = await self.client.release_escrow(
                escrow_id=escrow_id,
                recipient=executor_id,
                amount_usdc=float(actual_payout),
            )

            if not result.success:
                return ProofOfAttemptResult(
                    task_id=task_id,
                    executor_id=executor_id,
                    attempt_score=score,
                    base_payout_usd=base_payout,
                    actual_payout_usd=actual_payout,
                    tx_hash=None,
                    success=False,
                    error=result.error,
                )

            return ProofOfAttemptResult(
                task_id=task_id,
                executor_id=executor_id,
                attempt_score=score,
                base_payout_usd=base_payout,
                actual_payout_usd=actual_payout,
                tx_hash=result.tx_hash,
                success=True,
            )

        except Exception as e:
            return ProofOfAttemptResult(
                task_id=task_id,
                executor_id=executor_id,
                attempt_score=score,
                base_payout_usd=base_payout,
                actual_payout_usd=actual_payout,
                tx_hash=None,
                success=False,
                error=str(e),
            )

    def calculate_proof_of_attempt(
        self,
        bounty_usd: float,
        attempt_score: float,
    ) -> Dict[str, Any]:
        """
        Calculate proof of attempt payout without executing.

        Useful for showing workers what they'll receive before submission.

        Args:
            bounty_usd: Original bounty amount
            attempt_score: Expected attempt score (0.0-1.0)

        Returns:
            Dict with payout calculation details
        """
        bounty = Decimal(str(bounty_usd))
        score = max(0.0, min(1.0, attempt_score))

        base_payout = max(
            bounty * self.config.proof_of_attempt_percent,
            self.config.min_proof_of_attempt_usd,
        )
        actual_payout = (
            base_payout * Decimal(str(score)) if score >= 0.3 else Decimal("0")
        )

        return {
            "bounty_usd": float(bounty),
            "attempt_score": score,
            "base_payout_usd": float(base_payout),
            "actual_payout_usd": float(actual_payout),
            "payout_percent": float(self.config.proof_of_attempt_percent * 100),
            "eligible": score >= 0.3,
            "score_breakdown": {
                "0.9-1.0": "Excellent documentation - full payout",
                "0.7-0.9": "Good documentation - 70-90% of base",
                "0.3-0.7": "Partial documentation - 30-70% of base",
                "0.0-0.3": "Insufficient proof - no payout",
            },
        }

    # -------------------------------------------------------------------------
    # Bond Queries
    # -------------------------------------------------------------------------

    def get_bond(self, bond_id: str) -> Optional[LockedBond]:
        """Get a bond by its ID."""
        return self._bonds.get(bond_id)

    def get_bonds_for_agent(self, agent_id: str) -> List[LockedBond]:
        """Get all bonds for an agent."""
        return [bond for bond in self._bonds.values() if bond.agent_id == agent_id]

    def get_bond_for_task(self, task_id: str) -> Optional[LockedBond]:
        """Get the bond associated with a task."""
        for bond in self._bonds.values():
            if bond.task_id == task_id:
                return bond
        return None

    def get_total_locked_bonds(self, agent_id: str) -> Decimal:
        """Get total amount of locked bonds for an agent."""
        return sum(
            bond.amount_usd
            for bond in self._bonds.values()
            if bond.agent_id == agent_id and bond.status == BondStatus.LOCKED
        )

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------

    def _find_bond(self, agent_id: str, task_id: str) -> Optional[LockedBond]:
        """Find a bond by agent and task ID."""
        for bond in self._bonds.values():
            if bond.agent_id == agent_id and bond.task_id == task_id:
                return bond
        return None


# =============================================================================
# Convenience Functions
# =============================================================================


async def calculate_total_deposit(
    bounty_usd: float,
    task_type: TaskType = TaskType.SIMPLE,
    bond_percent: Optional[float] = None,
) -> BondCalculation:
    """
    Calculate the total deposit needed for a task (bounty + bond + fee).

    Args:
        bounty_usd: The bounty amount
        task_type: Type of task
        bond_percent: Optional custom bond percentage

    Returns:
        BondCalculation with full breakdown
    """
    manager = AgentBondManager()
    return manager.calculate_required_bond(bounty_usd, task_type, bond_percent)


async def validate_bounty(
    bounty_usd: float,
    task_type: TaskType,
) -> Dict[str, Any]:
    """
    Validate a bounty meets minimum requirements.

    Args:
        bounty_usd: Proposed bounty
        task_type: Type of task

    Returns:
        Dict with validation result and details
    """
    manager = AgentBondManager()
    is_valid, errors = manager.validate_minimum_payout(bounty_usd, task_type)

    return {
        "is_valid": is_valid,
        "errors": errors,
        "bounty_usd": bounty_usd,
        "task_type": task_type.value,
        "minimum_bounty_for_type": float(
            manager.get_minimum_bounty_for_type(task_type)
        ),
    }


def get_fee_structure() -> Dict[str, Any]:
    """
    Get the current fee structure for reference.

    Returns:
        Dict with all fee percentages and minimums
    """
    config = BondConfig()

    return {
        "bond_percent": {
            "default": float(config.default_bond_percent * 100),
            "min": float(config.min_bond_percent * 100),
            "max": float(config.max_bond_percent * 100),
        },
        "platform_fee_percent": float(config.platform_fee_percent * 100),
        "proof_of_attempt_percent": float(config.proof_of_attempt_percent * 100),
        "minimum_payouts": {
            "global": float(config.min_net_payout_usd),
            "proof_of_attempt": float(config.min_proof_of_attempt_usd),
        },
        "task_type_minimums": {
            task_type.value: {
                "min_bounty": float(cfg.min_bounty_usd),
                "min_net_payout": float(cfg.min_net_payout_usd),
                "description": cfg.description,
            }
            for task_type, cfg in TASK_TYPE_MINIMUMS.items()
        },
    }
