"""
Chamba Flexible Rewards Module

Supports multiple reward types for enterprise flexibility:
- x402: USDC/crypto payments
- points: Internal point system
- token: Custom tokens
- none: Volunteer/research tasks
- custom: Arbitrary reward definitions
"""

from .types import RewardType, RewardConfig, Reward
from .manager import RewardsManager
from .converters import PointsConverter, TokenConverter

__all__ = [
    'RewardType',
    'RewardConfig',
    'Reward',
    'RewardsManager',
    'PointsConverter',
    'TokenConverter'
]
