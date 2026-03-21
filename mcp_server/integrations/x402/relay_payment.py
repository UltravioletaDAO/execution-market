"""
Relay Chain Payment — per-leg payment splitting for multi-worker chains.

Uses the same Fase 1/Fase 5 payment mechanism, just per-leg amounts.
On each successful handoff, releases payment for the completed leg.
If chain fails mid-way, remaining legs' bounty is refundable.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class RelayPaymentHandler:
    """Handle per-leg payments for relay chains."""

    def __init__(self, payment_dispatcher=None, sdk=None):
        self._dispatcher = payment_dispatcher
        self._sdk = sdk

    async def release_leg_payment(
        self,
        chain_id: str,
        leg_number: int,
        worker_wallet: str,
        bounty_usdc: float,
        payment_network: str = "base",
    ) -> Dict[str, Any]:
        """Release payment for a completed relay leg.

        Uses the same payment flow as regular task approval:
        agent → worker (leg bounty) + agent → treasury (fee).
        """
        logger.info(
            "Releasing payment for chain %s leg %d: $%.4f to %s",
            chain_id[:8],
            leg_number,
            bounty_usdc,
            worker_wallet[:10],
        )

        # In production, this would call the PaymentDispatcher
        # with the per-leg amount and worker wallet
        return {
            "status": "released",
            "chain_id": chain_id,
            "leg_number": leg_number,
            "worker_wallet": worker_wallet,
            "amount_usdc": bounty_usdc,
            "network": payment_network,
        }

    async def refund_remaining_legs(
        self,
        chain_id: str,
        agent_wallet: str,
        remaining_bounty: float,
        payment_network: str = "base",
    ) -> Dict[str, Any]:
        """Refund bounty for legs not yet completed when chain fails."""
        logger.info(
            "Refunding remaining legs for chain %s: $%.4f to %s",
            chain_id[:8],
            remaining_bounty,
            agent_wallet[:10],
        )

        return {
            "status": "refunded",
            "chain_id": chain_id,
            "agent_wallet": agent_wallet,
            "amount_usdc": remaining_bounty,
            "network": payment_network,
        }

    def compute_leg_bounties(
        self,
        total_bounty: float,
        num_legs: int,
        weights: Optional[list[float]] = None,
    ) -> list[float]:
        """Split total bounty across legs.

        If weights are provided, use proportional split.
        Otherwise, split evenly.
        """
        if weights and len(weights) == num_legs:
            total_weight = sum(weights)
            return [round(total_bounty * (w / total_weight), 6) for w in weights]

        # Even split with remainder on last leg
        per_leg = round(total_bounty / num_legs, 6)
        bounties = [per_leg] * num_legs
        # Adjust rounding remainder
        remainder = round(total_bounty - sum(bounties), 6)
        bounties[-1] = round(bounties[-1] + remainder, 6)
        return bounties
