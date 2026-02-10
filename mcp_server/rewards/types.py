"""
Reward Types and Configuration

Defines flexible reward types for enterprise customers.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class RewardType(str, Enum):
    """Supported reward types (NOW-157)."""

    X402 = "x402"  # USDC via x402 protocol
    POINTS = "points"  # Internal points system
    TOKEN = "token"  # Custom ERC-20 token
    NONE = "none"  # Volunteer/research (no reward)
    CUSTOM = "custom"  # Arbitrary custom reward


class RewardStatus(str, Enum):
    """Status of a reward."""

    PENDING = "pending"
    ESCROWED = "escrowed"
    RELEASED = "released"
    REFUNDED = "refunded"
    EXPIRED = "expired"


@dataclass
class RewardConfig:
    """Configuration for a reward type."""

    reward_type: RewardType
    # For x402/token
    token_address: Optional[str] = None
    token_symbol: Optional[str] = None
    token_decimals: int = 18
    # For points
    points_per_usd: float = 100.0  # 100 points = $1
    points_name: str = "Points"
    # For custom
    custom_schema: Optional[Dict[str, Any]] = None
    custom_handler: Optional[str] = None  # Module path
    # General
    min_amount: float = 0.0
    max_amount: float = 10000.0
    requires_escrow: bool = True
    instant_release: bool = False


@dataclass
class Reward:
    """A reward for task completion."""

    id: str
    task_id: str
    reward_type: RewardType
    amount: float
    unit: str  # "USDC", "points", token symbol, etc.
    recipient_id: str
    recipient_wallet: Optional[str] = None
    status: RewardStatus = RewardStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    released_at: Optional[datetime] = None
    tx_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PointsBalance:
    """Worker's points balance."""

    executor_id: str
    balance: float
    lifetime_earned: float
    last_updated: datetime
    pending_withdrawal: float = 0.0


@dataclass
class TokenReward:
    """Token-specific reward details."""

    token_address: str
    token_symbol: str
    amount: float
    chain_id: int
    decimals: int = 18


# Default configurations

DEFAULT_X402_CONFIG = RewardConfig(
    reward_type=RewardType.X402,
    token_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC on Base
    token_symbol="USDC",
    token_decimals=6,
    min_amount=0.50,
    max_amount=10000.0,
    requires_escrow=True,
)

DEFAULT_POINTS_CONFIG = RewardConfig(
    reward_type=RewardType.POINTS,
    points_per_usd=100.0,
    points_name="Execution Market Points",
    min_amount=1.0,
    max_amount=100000.0,
    requires_escrow=False,
    instant_release=True,
)

DEFAULT_NONE_CONFIG = RewardConfig(
    reward_type=RewardType.NONE, requires_escrow=False, instant_release=True
)


def get_default_config(reward_type: RewardType) -> RewardConfig:
    """Get default configuration for a reward type."""
    configs = {
        RewardType.X402: DEFAULT_X402_CONFIG,
        RewardType.POINTS: DEFAULT_POINTS_CONFIG,
        RewardType.NONE: DEFAULT_NONE_CONFIG,
    }
    return configs.get(reward_type, DEFAULT_X402_CONFIG)
