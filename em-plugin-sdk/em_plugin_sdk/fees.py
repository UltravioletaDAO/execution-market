"""Fee calculator for Execution Market — pure computation, no server calls.

Mirrors the fee logic from mcp_server/payments/fees.py. Useful for agents
to know exactly how much workers will receive before posting a task.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from pydantic import BaseModel

from .models import TaskCategory

# Fee rates by category (11-13%)
FEE_RATES: dict[str, Decimal] = {
    "physical_presence": Decimal("0.13"),
    "knowledge_access": Decimal("0.12"),
    "human_authority": Decimal("0.11"),
    "simple_action": Decimal("0.13"),
    "digital_physical": Decimal("0.12"),
    "location_based": Decimal("0.13"),
    "verification": Decimal("0.13"),
    "social_proof": Decimal("0.13"),
    "data_collection": Decimal("0.12"),
    "sensory": Decimal("0.13"),
    "social": Decimal("0.13"),
    "proxy": Decimal("0.13"),
    "bureaucratic": Decimal("0.12"),
    "emergency": Decimal("0.13"),
    "creative": Decimal("0.12"),
    "data_processing": Decimal("0.13"),
    "api_integration": Decimal("0.12"),
    "content_generation": Decimal("0.13"),
    "code_execution": Decimal("0.12"),
    "research": Decimal("0.12"),
    "multi_step_workflow": Decimal("0.13"),
}

DEFAULT_FEE_RATE = Decimal("0.13")
MIN_FEE = Decimal("0.01")
MAX_FEE_RATE = Decimal("0.15")


class FeeBreakdown(BaseModel):
    """Result of a fee calculation."""
    gross_amount: float
    fee_rate: float
    fee_rate_percent: float
    fee_amount: float
    worker_amount: float
    category: str


def calculate_fee(bounty_usd: float, category: str | TaskCategory = "simple_action") -> FeeBreakdown:
    """Calculate the fee breakdown for a given bounty.

    Args:
        bounty_usd: Gross bounty amount the agent posts.
        category: Task category (determines fee rate, 11-13%).

    Returns:
        FeeBreakdown with exact amounts.

    Example::

        >>> fee = calculate_fee(10.00, "physical_presence")
        >>> fee.worker_amount  # 8.70
        >>> fee.fee_amount     # 1.30
    """
    if bounty_usd <= 0:
        raise ValueError("Bounty must be positive")

    cat_str = category.value if isinstance(category, TaskCategory) else category
    rate = FEE_RATES.get(cat_str, DEFAULT_FEE_RATE)
    rate = min(rate, MAX_FEE_RATE)

    bounty = Decimal(str(bounty_usd))
    fee = (bounty * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if fee < MIN_FEE:
        fee = MIN_FEE

    worker = bounty - fee

    return FeeBreakdown(
        gross_amount=float(bounty),
        fee_rate=float(rate),
        fee_rate_percent=float(rate * 100),
        fee_amount=float(fee),
        worker_amount=float(worker),
        category=cat_str,
    )


def calculate_reverse_fee(desired_worker_amount: float, category: str | TaskCategory = "simple_action") -> FeeBreakdown:
    """Calculate the bounty needed for a worker to receive a specific amount.

    Args:
        desired_worker_amount: What the worker should receive after fees.
        category: Task category.

    Example::

        >>> fee = calculate_reverse_fee(10.00, "simple_action")
        >>> fee.gross_amount  # ~11.49 (the bounty to post)
        >>> fee.worker_amount  # ~10.00
    """
    if desired_worker_amount <= 0:
        raise ValueError("Desired amount must be positive")

    cat_str = category.value if isinstance(category, TaskCategory) else category
    rate = FEE_RATES.get(cat_str, DEFAULT_FEE_RATE)
    rate = min(rate, MAX_FEE_RATE)

    desired = Decimal(str(desired_worker_amount))
    bounty = (desired / (1 - rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return calculate_fee(float(bounty), cat_str)


def get_fee_rate(category: str | TaskCategory = "simple_action") -> float:
    """Get the fee rate for a category (e.g., 0.13 for 13%)."""
    cat_str = category.value if isinstance(category, TaskCategory) else category
    return float(FEE_RATES.get(cat_str, DEFAULT_FEE_RATE))
