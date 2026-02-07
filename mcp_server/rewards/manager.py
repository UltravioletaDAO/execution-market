"""
Rewards Manager

Handles reward lifecycle: creation, escrow, release, refund.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from .types import (
    RewardType,
    RewardConfig,
    Reward,
    RewardStatus,
    PointsBalance,
    get_default_config,
)

logger = logging.getLogger(__name__)


class RewardsManager:
    """
    Manages rewards across different reward types.

    Provides unified interface for:
    - Creating rewards (escrow)
    - Releasing rewards (payment)
    - Refunding rewards
    - Balance queries
    """

    def __init__(
        self,
        default_type: RewardType = RewardType.X402,
        configs: Optional[Dict[RewardType, RewardConfig]] = None,
    ):
        """
        Initialize rewards manager.

        Args:
            default_type: Default reward type
            configs: Custom configurations by type
        """
        self.default_type = default_type
        self.configs = configs or {}
        self._rewards: Dict[str, Reward] = {}
        self._points_balances: Dict[str, PointsBalance] = {}

    def get_config(self, reward_type: RewardType) -> RewardConfig:
        """Get configuration for reward type."""
        return self.configs.get(reward_type) or get_default_config(reward_type)

    async def create_reward(
        self,
        task_id: str,
        amount: float,
        recipient_id: str,
        reward_type: Optional[RewardType] = None,
        recipient_wallet: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Reward:
        """
        Create a new reward (and escrow if required).

        Args:
            task_id: Associated task
            amount: Reward amount
            recipient_id: Worker's executor ID
            reward_type: Type of reward (default: manager default)
            recipient_wallet: Wallet for crypto rewards
            metadata: Additional metadata

        Returns:
            Created Reward
        """
        r_type = reward_type or self.default_type
        config = self.get_config(r_type)

        # Validate amount
        if amount < config.min_amount:
            raise ValueError(f"Amount {amount} below minimum {config.min_amount}")
        if amount > config.max_amount:
            raise ValueError(f"Amount {amount} above maximum {config.max_amount}")

        # Determine unit
        unit = self._get_unit(r_type, config)

        reward = Reward(
            id=str(uuid.uuid4()),
            task_id=task_id,
            reward_type=r_type,
            amount=amount,
            unit=unit,
            recipient_id=recipient_id,
            recipient_wallet=recipient_wallet,
            status=RewardStatus.PENDING,
            metadata=metadata or {},
        )

        # Handle escrow if required
        if config.requires_escrow:
            await self._escrow_reward(reward, config)
            reward.status = RewardStatus.ESCROWED

        self._rewards[reward.id] = reward
        logger.info(f"Reward created: {reward.id} ({r_type.value}, {amount} {unit})")

        return reward

    async def release_reward(
        self, reward_id: str, partial_amount: Optional[float] = None
    ) -> Reward:
        """
        Release reward to recipient.

        Args:
            reward_id: Reward ID
            partial_amount: Partial release amount (optional)

        Returns:
            Updated Reward
        """
        reward = self._rewards.get(reward_id)
        if not reward:
            raise ValueError(f"Reward not found: {reward_id}")

        if reward.status not in [RewardStatus.PENDING, RewardStatus.ESCROWED]:
            raise ValueError(f"Reward cannot be released: {reward.status}")

        config = self.get_config(reward.reward_type)
        amount = partial_amount or reward.amount

        # Handle by type
        if reward.reward_type == RewardType.X402:
            tx_hash = await self._release_x402(reward, amount)
            reward.tx_hash = tx_hash
        elif reward.reward_type == RewardType.POINTS:
            await self._release_points(reward, amount)
        elif reward.reward_type == RewardType.TOKEN:
            tx_hash = await self._release_token(reward, amount)
            reward.tx_hash = tx_hash
        elif reward.reward_type == RewardType.NONE:
            pass  # No action needed
        elif reward.reward_type == RewardType.CUSTOM:
            await self._release_custom(reward, amount, config)

        reward.status = RewardStatus.RELEASED
        reward.released_at = datetime.utcnow()

        logger.info(f"Reward released: {reward_id} ({amount} {reward.unit})")
        return reward

    async def refund_reward(self, reward_id: str, reason: str) -> Reward:
        """
        Refund reward to task creator.

        Args:
            reward_id: Reward ID
            reason: Refund reason

        Returns:
            Updated Reward
        """
        reward = self._rewards.get(reward_id)
        if not reward:
            raise ValueError(f"Reward not found: {reward_id}")

        if reward.status not in [RewardStatus.PENDING, RewardStatus.ESCROWED]:
            raise ValueError(f"Reward cannot be refunded: {reward.status}")

        config = self.get_config(reward.reward_type)

        if config.requires_escrow:
            # Release from escrow back to creator
            if reward.reward_type == RewardType.X402:
                await self._refund_x402(reward)
            elif reward.reward_type == RewardType.TOKEN:
                await self._refund_token(reward)

        reward.status = RewardStatus.REFUNDED
        reward.metadata["refund_reason"] = reason

        logger.info(f"Reward refunded: {reward_id} ({reason})")
        return reward

    async def get_points_balance(self, executor_id: str) -> PointsBalance:
        """Get worker's points balance."""
        if executor_id not in self._points_balances:
            self._points_balances[executor_id] = PointsBalance(
                executor_id=executor_id,
                balance=0.0,
                lifetime_earned=0.0,
                last_updated=datetime.utcnow(),
            )
        return self._points_balances[executor_id]

    async def convert_points_to_usd(
        self, executor_id: str, points: float, config: Optional[RewardConfig] = None
    ) -> float:
        """Convert points to USD equivalent."""
        cfg = config or self.get_config(RewardType.POINTS)
        return points / cfg.points_per_usd

    async def convert_usd_to_points(
        self, usd: float, config: Optional[RewardConfig] = None
    ) -> float:
        """Convert USD to points."""
        cfg = config or self.get_config(RewardType.POINTS)
        return usd * cfg.points_per_usd

    # Private methods

    def _get_unit(self, reward_type: RewardType, config: RewardConfig) -> str:
        """Get unit string for reward type."""
        if reward_type == RewardType.X402:
            return config.token_symbol or "USDC"
        elif reward_type == RewardType.POINTS:
            return config.points_name or "Points"
        elif reward_type == RewardType.TOKEN:
            return config.token_symbol or "TOKEN"
        elif reward_type == RewardType.NONE:
            return "N/A"
        else:
            return "CUSTOM"

    async def _escrow_reward(self, reward: Reward, config: RewardConfig):
        """Escrow reward funds."""
        if reward.reward_type == RewardType.X402:
            # Would call x402 escrow
            logger.info(f"Escrowing {reward.amount} USDC for reward {reward.id}")
        elif reward.reward_type == RewardType.TOKEN:
            # Would lock tokens
            logger.info(f"Escrowing {reward.amount} tokens for reward {reward.id}")

    async def _release_x402(self, reward: Reward, amount: float) -> str:
        """Release x402 payment."""
        # Would call x402 client
        logger.info(f"Releasing {amount} USDC to {reward.recipient_wallet}")
        return "0x" + "0" * 64  # Placeholder tx hash

    async def _release_points(self, reward: Reward, amount: float):
        """Credit points to worker."""
        balance = await self.get_points_balance(reward.recipient_id)
        balance.balance += amount
        balance.lifetime_earned += amount
        balance.last_updated = datetime.utcnow()
        logger.info(f"Credited {amount} points to {reward.recipient_id}")

    async def _release_token(self, reward: Reward, amount: float) -> str:
        """Release token payment."""
        # Would call token contract
        logger.info(f"Releasing {amount} tokens to {reward.recipient_wallet}")
        return "0x" + "0" * 64

    async def _release_custom(
        self, reward: Reward, amount: float, config: RewardConfig
    ):
        """Handle custom reward release."""
        if config.custom_handler:
            # Would dynamically load and call handler
            logger.info(f"Custom reward handler: {config.custom_handler}")
        logger.info(f"Custom reward released: {reward.id}")

    async def _refund_x402(self, reward: Reward):
        """Refund x402 escrow."""
        logger.info(f"Refunding {reward.amount} USDC escrow")

    async def _refund_token(self, reward: Reward):
        """Refund token escrow."""
        logger.info(f"Refunding {reward.amount} token escrow")
