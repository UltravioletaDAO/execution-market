"""
Fee Collection Module (NOW-025, NOW-026)

Handles platform fee calculation, collection, and analytics.

Features:
- Variable platform fees by task category (6-8%)
- Fee collection on bounty release (worker gets 92-94%, treasury gets 6-8%)
- Comprehensive fee tracking and analytics
- Support for fee waivers and promotional discounts

Fee Structure:
- PHYSICAL_PRESENCE: 8% (highest effort, highest platform value)
- KNOWLEDGE_ACCESS: 7% (specialized knowledge tasks)
- HUMAN_AUTHORITY: 6% (licensed professional tasks - incentivize)
- SIMPLE_ACTION: 8% (high volume, standard rate)
- DIGITAL_PHYSICAL: 7% (hybrid tasks)
"""

import os
import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional, Dict, Any, List

from ..models import TaskCategory

logger = logging.getLogger(__name__)


# =============================================================================
# Fee Configuration
# =============================================================================


class FeeType(str, Enum):
    """Types of fees that can be collected."""
    PLATFORM = "platform"           # Standard platform fee
    EXPEDITED = "expedited"         # Rush/priority task fee
    DISPUTE = "dispute"             # Dispute resolution fee
    WITHDRAWAL = "withdrawal"       # Early withdrawal fee
    PROMOTIONAL = "promotional"     # Promotional/waived fee


class FeeStatus(str, Enum):
    """Status of a fee record."""
    PENDING = "pending"             # Fee calculated but not collected
    COLLECTED = "collected"         # Fee successfully collected
    FAILED = "failed"               # Collection attempt failed
    WAIVED = "waived"               # Fee waived (promotional, etc.)
    REFUNDED = "refunded"           # Fee refunded to agent


# Fee rates by task category (NOW-025)
# Rates are designed to balance platform sustainability with worker incentives
FEE_RATES: Dict[TaskCategory, Decimal] = {
    TaskCategory.PHYSICAL_PRESENCE: Decimal("0.08"),   # 8% - high effort tasks
    TaskCategory.KNOWLEDGE_ACCESS: Decimal("0.07"),    # 7% - specialized knowledge
    TaskCategory.HUMAN_AUTHORITY: Decimal("0.06"),     # 6% - incentivize licensed pros
    TaskCategory.SIMPLE_ACTION: Decimal("0.08"),       # 8% - standard digital tasks
    TaskCategory.DIGITAL_PHYSICAL: Decimal("0.07"),    # 7% - hybrid tasks
}

# Default fee rate for unknown categories
DEFAULT_FEE_RATE = Decimal("0.08")  # 8%

# Minimum fee to collect (avoid dust transactions)
MIN_FEE_AMOUNT = Decimal("0.01")  # $0.01

# Maximum fee cap (protect against extreme cases)
MAX_FEE_PERCENT = Decimal("0.10")  # 10% absolute maximum


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class FeeBreakdown:
    """
    Complete breakdown of fees for a task payment.

    Attributes:
        gross_amount: Total bounty before fees
        fee_rate: Applied fee percentage (0.06-0.08)
        fee_amount: Actual fee amount in USD
        worker_amount: Amount worker receives after fees
        treasury_wallet: Destination for collected fees
        category: Task category that determined the rate
        is_waived: Whether the fee was waived
        waiver_reason: Reason for fee waiver (if applicable)
    """
    gross_amount: Decimal
    fee_rate: Decimal
    fee_amount: Decimal
    worker_amount: Decimal
    treasury_wallet: str
    category: TaskCategory
    is_waived: bool = False
    waiver_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "gross_amount": float(self.gross_amount),
            "fee_rate": float(self.fee_rate),
            "fee_rate_percent": float(self.fee_rate * 100),
            "fee_amount": float(self.fee_amount),
            "worker_amount": float(self.worker_amount),
            "worker_percent": float((self.worker_amount / self.gross_amount) * 100) if self.gross_amount > 0 else 0,
            "treasury_wallet": self.treasury_wallet,
            "category": self.category.value,
            "is_waived": self.is_waived,
            "waiver_reason": self.waiver_reason,
        }


@dataclass
class CollectedFee:
    """
    Record of a collected fee for audit and analytics.

    Attributes:
        id: Unique fee record identifier
        task_id: Associated task ID
        amount: Fee amount in USD
        rate: Fee rate applied
        category: Task category
        fee_type: Type of fee
        status: Current status
        tx_hash: Blockchain transaction hash
        collected_at: Timestamp of collection
        agent_id: Agent who paid the fee
        worker_id: Worker who executed the task
        metadata: Additional context
    """
    id: str
    task_id: str
    amount: Decimal
    rate: Decimal
    category: TaskCategory
    fee_type: FeeType
    status: FeeStatus
    tx_hash: Optional[str]
    collected_at: datetime
    agent_id: Optional[str] = None
    worker_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "amount": float(self.amount),
            "rate": float(self.rate),
            "rate_percent": float(self.rate * 100),
            "category": self.category.value,
            "fee_type": self.fee_type.value,
            "status": self.status.value,
            "tx_hash": self.tx_hash,
            "collected_at": self.collected_at.isoformat(),
            "agent_id": self.agent_id,
            "worker_id": self.worker_id,
            "metadata": self.metadata,
        }


@dataclass
class FeeAnalytics:
    """
    Fee analytics summary for a time period.

    Attributes:
        start_date: Start of analysis period
        end_date: End of analysis period
        total_collected: Total fees collected
        total_waived: Total fees waived
        total_refunded: Total fees refunded
        transaction_count: Number of fee transactions
        by_category: Breakdown by task category
        by_status: Breakdown by fee status
        average_rate: Weighted average fee rate
        top_agents: Top fee-paying agents
    """
    start_date: datetime
    end_date: datetime
    total_collected: Decimal
    total_waived: Decimal
    total_refunded: Decimal
    transaction_count: int
    by_category: Dict[str, Decimal]
    by_status: Dict[str, int]
    average_rate: Decimal
    top_agents: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "period": {
                "start": self.start_date.isoformat(),
                "end": self.end_date.isoformat(),
                "days": (self.end_date - self.start_date).days,
            },
            "totals": {
                "collected": float(self.total_collected),
                "waived": float(self.total_waived),
                "refunded": float(self.total_refunded),
                "net": float(self.total_collected - self.total_refunded),
            },
            "transaction_count": self.transaction_count,
            "by_category": {k: float(v) for k, v in self.by_category.items()},
            "by_status": self.by_status,
            "average_rate_percent": float(self.average_rate * 100),
            "top_agents": self.top_agents,
        }


# =============================================================================
# Fee Manager
# =============================================================================


class FeeManager:
    """
    Manages platform fee calculation, collection, and analytics.

    The fee structure is designed to:
    1. Be sustainable for platform operations
    2. Incentivize high-value task categories
    3. Provide transparency to agents and workers
    4. Support promotional campaigns and waivers

    Example:
        >>> manager = FeeManager()
        >>> breakdown = manager.calculate_fee(
        ...     bounty=Decimal("100.00"),
        ...     category=TaskCategory.PHYSICAL_PRESENCE
        ... )
        >>> print(f"Worker gets ${breakdown.worker_amount}, fee is ${breakdown.fee_amount}")
        Worker gets $92.00, fee is $8.00

        >>> collected = await manager.collect_fee(
        ...     task_id="task-123",
        ...     breakdown=breakdown,
        ...     release_tx="0x..."
        ... )
    """

    def __init__(
        self,
        treasury_wallet: Optional[str] = None,
        custom_rates: Optional[Dict[TaskCategory, Decimal]] = None,
    ):
        """
        Initialize fee manager.

        Args:
            treasury_wallet: DAO treasury wallet address
            custom_rates: Override default fee rates (for testing/promotions)
        """
        self.treasury_wallet = treasury_wallet or os.environ.get(
            "EM_TREASURY_ADDRESS",
            "0x0000000000000000000000000000000000000000"
        )
        self.fee_rates = custom_rates or FEE_RATES.copy()

        # In-memory storage (would be database in production)
        self._collected_fees: Dict[str, CollectedFee] = {}
        self._waiver_codes: Dict[str, Dict[str, Any]] = {}

        logger.info(
            f"FeeManager initialized with treasury {self.treasury_wallet[:10]}... "
            f"and {len(self.fee_rates)} category rates"
        )

    # -------------------------------------------------------------------------
    # Fee Calculation (NOW-025)
    # -------------------------------------------------------------------------

    def get_fee_rate(self, category: TaskCategory) -> Decimal:
        """
        Get the fee rate for a task category.

        Args:
            category: Task category

        Returns:
            Fee rate as decimal (e.g., 0.08 for 8%)
        """
        rate = self.fee_rates.get(category, DEFAULT_FEE_RATE)
        # Ensure rate doesn't exceed maximum
        return min(rate, MAX_FEE_PERCENT)

    def calculate_fee(
        self,
        bounty: Decimal,
        category: TaskCategory,
        waiver_code: Optional[str] = None,
    ) -> FeeBreakdown:
        """
        Calculate fee breakdown for a bounty.

        Args:
            bounty: Gross bounty amount in USD
            category: Task category (determines fee rate)
            waiver_code: Optional promotional code for fee waiver

        Returns:
            FeeBreakdown with all calculated amounts

        Raises:
            ValueError: If bounty is invalid
        """
        # Validate bounty
        if bounty <= 0:
            raise ValueError(f"Bounty must be positive, got {bounty}")

        # Ensure Decimal type
        bounty = Decimal(str(bounty))

        # Get fee rate for category
        fee_rate = self.get_fee_rate(category)

        # Check for waiver
        is_waived = False
        waiver_reason = None

        if waiver_code and waiver_code in self._waiver_codes:
            waiver = self._waiver_codes[waiver_code]
            if self._is_waiver_valid(waiver):
                is_waived = True
                waiver_reason = waiver.get("reason", "Promotional waiver")
                fee_rate = Decimal("0")

        # Calculate fee amount
        fee_amount = (bounty * fee_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Enforce minimum fee (unless waived)
        if not is_waived and fee_amount > 0 and fee_amount < MIN_FEE_AMOUNT:
            fee_amount = MIN_FEE_AMOUNT

        # Calculate worker amount
        worker_amount = bounty - fee_amount

        logger.debug(
            f"Fee calculated: bounty=${bounty}, rate={fee_rate*100}%, "
            f"fee=${fee_amount}, worker=${worker_amount}"
        )

        return FeeBreakdown(
            gross_amount=bounty,
            fee_rate=fee_rate,
            fee_amount=fee_amount,
            worker_amount=worker_amount,
            treasury_wallet=self.treasury_wallet,
            category=category,
            is_waived=is_waived,
            waiver_reason=waiver_reason,
        )

    def calculate_reverse_fee(
        self,
        desired_worker_amount: Decimal,
        category: TaskCategory,
    ) -> FeeBreakdown:
        """
        Calculate bounty needed to achieve a specific worker payout.

        Useful for agents who want workers to receive exactly X amount.

        Args:
            desired_worker_amount: Amount worker should receive
            category: Task category

        Returns:
            FeeBreakdown with required bounty

        Example:
            >>> # Agent wants worker to receive exactly $10
            >>> breakdown = manager.calculate_reverse_fee(
            ...     desired_worker_amount=Decimal("10.00"),
            ...     category=TaskCategory.SIMPLE_ACTION
            ... )
            >>> print(f"Post bounty of ${breakdown.gross_amount}")
            Post bounty of $10.87
        """
        if desired_worker_amount <= 0:
            raise ValueError(f"Desired amount must be positive, got {desired_worker_amount}")

        desired = Decimal(str(desired_worker_amount))
        fee_rate = self.get_fee_rate(category)

        # bounty - (bounty * fee_rate) = desired
        # bounty * (1 - fee_rate) = desired
        # bounty = desired / (1 - fee_rate)
        bounty = (desired / (1 - fee_rate)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Recalculate to get exact breakdown
        return self.calculate_fee(bounty, category)

    # -------------------------------------------------------------------------
    # Fee Collection (NOW-026)
    # -------------------------------------------------------------------------

    async def collect_fee(
        self,
        task_id: str,
        breakdown: FeeBreakdown,
        release_tx: str,
        agent_id: Optional[str] = None,
        worker_id: Optional[str] = None,
    ) -> CollectedFee:
        """
        Record fee collection after bounty release.

        This method records the fee as collected. The actual fund transfer
        happens during the bounty release in EscrowManager.release_final().

        Args:
            task_id: Task identifier
            breakdown: Fee breakdown from calculate_fee()
            release_tx: Transaction hash of the bounty release
            agent_id: Agent who posted the task
            worker_id: Worker who completed the task

        Returns:
            CollectedFee record for audit trail
        """
        # Handle waived fees
        if breakdown.is_waived or breakdown.fee_amount <= 0:
            fee_record = CollectedFee(
                id=f"fee_{uuid.uuid4().hex[:12]}",
                task_id=task_id,
                amount=Decimal("0"),
                rate=breakdown.fee_rate,
                category=breakdown.category,
                fee_type=FeeType.PROMOTIONAL if breakdown.is_waived else FeeType.PLATFORM,
                status=FeeStatus.WAIVED,
                tx_hash=None,
                collected_at=datetime.now(timezone.utc),
                agent_id=agent_id,
                worker_id=worker_id,
                metadata={
                    "waiver_reason": breakdown.waiver_reason,
                    "original_amount": float(breakdown.fee_amount),
                    "release_tx": release_tx,
                },
            )
            self._collected_fees[fee_record.id] = fee_record
            logger.info(f"Fee waived for task {task_id}: {breakdown.waiver_reason}")
            return fee_record

        # Record collected fee
        fee_record = CollectedFee(
            id=f"fee_{uuid.uuid4().hex[:12]}",
            task_id=task_id,
            amount=breakdown.fee_amount,
            rate=breakdown.fee_rate,
            category=breakdown.category,
            fee_type=FeeType.PLATFORM,
            status=FeeStatus.COLLECTED,
            tx_hash=release_tx,  # Fee transfer happens in same tx as release
            collected_at=datetime.now(timezone.utc),
            agent_id=agent_id,
            worker_id=worker_id,
            metadata={
                "gross_amount": float(breakdown.gross_amount),
                "worker_amount": float(breakdown.worker_amount),
                "treasury_wallet": breakdown.treasury_wallet,
            },
        )

        self._collected_fees[fee_record.id] = fee_record

        logger.info(
            f"Fee collected: task={task_id}, amount=${fee_record.amount}, "
            f"rate={fee_record.rate*100}%, tx={release_tx[:16]}..."
        )

        return fee_record

    async def refund_fee(
        self,
        fee_id: str,
        reason: str,
        refund_tx: Optional[str] = None,
    ) -> CollectedFee:
        """
        Refund a previously collected fee.

        Used when a task is cancelled after completion or in dispute resolution.

        Args:
            fee_id: ID of the fee to refund
            reason: Reason for the refund
            refund_tx: Transaction hash of the refund

        Returns:
            Updated fee record

        Raises:
            ValueError: If fee not found or cannot be refunded
        """
        fee = self._collected_fees.get(fee_id)
        if not fee:
            raise ValueError(f"Fee {fee_id} not found")

        if fee.status != FeeStatus.COLLECTED:
            raise ValueError(f"Cannot refund fee with status {fee.status}")

        # Update fee status
        fee.status = FeeStatus.REFUNDED
        fee.metadata["refund_reason"] = reason
        fee.metadata["refund_tx"] = refund_tx
        fee.metadata["refunded_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"Fee refunded: {fee_id}, reason={reason}")

        return fee

    # -------------------------------------------------------------------------
    # Waiver Management
    # -------------------------------------------------------------------------

    def register_waiver_code(
        self,
        code: str,
        reason: str,
        expires_at: Optional[datetime] = None,
        max_uses: Optional[int] = None,
    ) -> None:
        """
        Register a promotional fee waiver code.

        Args:
            code: Waiver code string
            reason: Reason/description for the waiver
            expires_at: When the code expires
            max_uses: Maximum number of times code can be used
        """
        self._waiver_codes[code] = {
            "reason": reason,
            "expires_at": expires_at,
            "max_uses": max_uses,
            "use_count": 0,
            "created_at": datetime.now(timezone.utc),
        }
        logger.info(f"Waiver code registered: {code}")

    def _is_waiver_valid(self, waiver: Dict[str, Any]) -> bool:
        """Check if a waiver code is still valid."""
        now = datetime.now(timezone.utc)

        # Check expiration
        if waiver.get("expires_at") and waiver["expires_at"] < now:
            return False

        # Check usage limit
        if waiver.get("max_uses") and waiver["use_count"] >= waiver["max_uses"]:
            return False

        return True

    # -------------------------------------------------------------------------
    # Analytics (NOW-026)
    # -------------------------------------------------------------------------

    def get_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[TaskCategory] = None,
    ) -> FeeAnalytics:
        """
        Get fee analytics for a time period.

        Args:
            start_date: Start of analysis period (default: 30 days ago)
            end_date: End of analysis period (default: now)
            category: Filter by task category (optional)

        Returns:
            FeeAnalytics with comprehensive breakdown
        """
        # Default to last 30 days
        now = datetime.now(timezone.utc)
        if end_date is None:
            end_date = now
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        # Filter fees by date range
        fees_in_range = [
            fee for fee in self._collected_fees.values()
            if start_date <= fee.collected_at <= end_date
        ]

        # Apply category filter if specified
        if category:
            fees_in_range = [f for f in fees_in_range if f.category == category]

        # Calculate totals
        total_collected = Decimal("0")
        total_waived = Decimal("0")
        total_refunded = Decimal("0")
        by_category: Dict[str, Decimal] = {}
        by_status: Dict[str, int] = {}
        weighted_rate_sum = Decimal("0")
        agent_totals: Dict[str, Decimal] = {}

        for fee in fees_in_range:
            # Count by status
            status = fee.status.value
            by_status[status] = by_status.get(status, 0) + 1

            # Sum by category
            cat = fee.category.value
            if cat not in by_category:
                by_category[cat] = Decimal("0")

            if fee.status == FeeStatus.COLLECTED:
                total_collected += fee.amount
                by_category[cat] += fee.amount
                weighted_rate_sum += fee.rate * fee.amount

                # Track by agent
                if fee.agent_id:
                    if fee.agent_id not in agent_totals:
                        agent_totals[fee.agent_id] = Decimal("0")
                    agent_totals[fee.agent_id] += fee.amount

            elif fee.status == FeeStatus.WAIVED:
                total_waived += fee.metadata.get("original_amount", 0)
            elif fee.status == FeeStatus.REFUNDED:
                total_refunded += fee.amount

        # Calculate average rate
        average_rate = (
            weighted_rate_sum / total_collected
            if total_collected > 0
            else DEFAULT_FEE_RATE
        )

        # Get top agents
        top_agents = sorted(
            [
                {"agent_id": aid, "total_fees": float(total)}
                for aid, total in agent_totals.items()
            ],
            key=lambda x: x["total_fees"],
            reverse=True
        )[:10]

        return FeeAnalytics(
            start_date=start_date,
            end_date=end_date,
            total_collected=total_collected,
            total_waived=total_waived,
            total_refunded=total_refunded,
            transaction_count=len(fees_in_range),
            by_category=by_category,
            by_status=by_status,
            average_rate=average_rate,
            top_agents=top_agents,
        )

    def get_fee_record(self, fee_id: str) -> Optional[CollectedFee]:
        """Get a specific fee record by ID."""
        return self._collected_fees.get(fee_id)

    def get_fees_for_task(self, task_id: str) -> List[CollectedFee]:
        """Get all fee records for a task."""
        return [
            fee for fee in self._collected_fees.values()
            if fee.task_id == task_id
        ]

    def get_fees_for_agent(
        self,
        agent_id: str,
        limit: int = 100,
    ) -> List[CollectedFee]:
        """Get fee records for an agent."""
        fees = [
            fee for fee in self._collected_fees.values()
            if fee.agent_id == agent_id
        ]
        # Sort by date descending and limit
        fees.sort(key=lambda f: f.collected_at, reverse=True)
        return fees[:limit]

    # -------------------------------------------------------------------------
    # Fee Structure Info
    # -------------------------------------------------------------------------

    def get_fee_structure(self) -> Dict[str, Any]:
        """
        Get current fee structure for display/documentation.

        Returns:
            Dict with all fee rates and limits
        """
        return {
            "rates_by_category": {
                cat.value: {
                    "rate": float(rate),
                    "rate_percent": float(rate * 100),
                    "description": self._get_category_description(cat),
                }
                for cat, rate in self.fee_rates.items()
            },
            "default_rate": {
                "rate": float(DEFAULT_FEE_RATE),
                "rate_percent": float(DEFAULT_FEE_RATE * 100),
            },
            "limits": {
                "minimum_fee": float(MIN_FEE_AMOUNT),
                "maximum_rate_percent": float(MAX_FEE_PERCENT * 100),
            },
            "treasury_wallet": self.treasury_wallet,
            "distribution": {
                "worker_percent": "92-94%",
                "platform_percent": "6-8%",
            },
        }

    def _get_category_description(self, category: TaskCategory) -> str:
        """Get description for a task category."""
        descriptions = {
            TaskCategory.PHYSICAL_PRESENCE: "Tasks requiring physical presence at a location",
            TaskCategory.KNOWLEDGE_ACCESS: "Tasks requiring specialized local knowledge",
            TaskCategory.HUMAN_AUTHORITY: "Tasks requiring licensed professional authority",
            TaskCategory.SIMPLE_ACTION: "Simple digital or physical actions",
            TaskCategory.DIGITAL_PHYSICAL: "Hybrid digital-physical tasks",
        }
        return descriptions.get(category, "Unknown category")


# =============================================================================
# Convenience Functions
# =============================================================================


def calculate_platform_fee(
    bounty_usd: float,
    category: TaskCategory,
) -> Dict[str, Any]:
    """
    Calculate platform fee for a bounty (convenience function).

    Args:
        bounty_usd: Bounty amount in USD
        category: Task category

    Returns:
        Dict with fee breakdown
    """
    manager = FeeManager()
    breakdown = manager.calculate_fee(
        bounty=Decimal(str(bounty_usd)),
        category=category,
    )
    return breakdown.to_dict()


def get_fee_rate_for_category(category: TaskCategory) -> float:
    """
    Get the fee rate for a task category (convenience function).

    Args:
        category: Task category

    Returns:
        Fee rate as float (e.g., 0.08 for 8%)
    """
    return float(FEE_RATES.get(category, DEFAULT_FEE_RATE))


def get_all_fee_rates() -> Dict[str, float]:
    """
    Get all fee rates by category (convenience function).

    Returns:
        Dict mapping category names to fee rates
    """
    return {
        cat.value: float(rate)
        for cat, rate in FEE_RATES.items()
    }
