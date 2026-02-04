"""
ERC-8004 Reputation Management

On-chain reputation storage and queries for Execution Market workers.
Uses ERC-8004 metadata for raw score storage and events emission.
"""

import os
import json
import struct
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from .register import ERC8004Registry

logger = logging.getLogger(__name__)


# Metadata keys for reputation
REPUTATION_KEY = "em_reputation"
REPUTATION_HISTORY_KEY = "em_rep_history"
TASK_COUNT_KEY = "em_task_count"


@dataclass
class ReputationScore:
    """Worker reputation score."""
    raw_score: float          # 0-100 scale
    bayesian_score: float     # Adjusted with Bayesian average
    total_tasks: int
    successful_tasks: int
    disputed_tasks: int
    last_updated: datetime
    on_chain: bool            # Whether stored on-chain


@dataclass
class ReputationEvent:
    """Reputation change event."""
    timestamp: datetime
    task_id: str
    score_delta: float
    reason: str
    tx_hash: Optional[str] = None


# Reputation Events ABI (for event emission)
REPUTATION_EVENTS_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "tokenId", "type": "uint256"},
            {"indexed": False, "name": "newScore", "type": "uint256"},
            {"indexed": False, "name": "taskId", "type": "bytes32"},
            {"indexed": False, "name": "reason", "type": "string"}
        ],
        "name": "ReputationUpdated",
        "type": "event"
    },
    {
        "inputs": [
            {"name": "tokenId", "type": "uint256"},
            {"name": "newScore", "type": "uint256"},
            {"name": "taskId", "type": "bytes32"},
            {"name": "reason", "type": "string"}
        ],
        "name": "emitReputationUpdate",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]


class ReputationManager:
    """
    Manages worker reputation on-chain via ERC-8004.

    Responsibilities:
    - Store raw reputation scores as ERC-8004 metadata
    - Emit reputation events for transparency
    - Query reputation history
    - Calculate Bayesian-adjusted scores
    """

    # Bayesian average parameters (from TODO_NOW.md)
    BAYESIAN_C = 15       # Prior weight
    BAYESIAN_M = 50       # Prior mean (neutral)
    DECAY_FACTOR = 0.9    # Monthly decay

    def __init__(
        self,
        registry: Optional[ERC8004Registry] = None,
        network: str = "sepolia",
        private_key: Optional[str] = None
    ):
        """
        Initialize Reputation Manager.

        Args:
            registry: Existing ERC8004Registry (or creates new)
            network: Network name
            private_key: Private key for write operations
        """
        self.registry = registry or ERC8004Registry(
            network=network,
            private_key=private_key
        )
        self.network = network
        self._cache: Dict[str, ReputationScore] = {}

    async def get_reputation(
        self,
        wallet_address: str,
        use_cache: bool = True
    ) -> Optional[ReputationScore]:
        """
        Get worker's reputation score.

        Args:
            wallet_address: Worker's wallet
            use_cache: Use cached value if available

        Returns:
            ReputationScore or None
        """
        cache_key = wallet_address.lower()

        # Check cache
        if use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            # Cache valid for 5 minutes
            if (datetime.utcnow() - cached.last_updated).seconds < 300:
                return cached

        # Get identity
        identity = await self.registry.get_identity(wallet_address)
        if not identity:
            return None

        # Get on-chain reputation
        rep_data = await self._get_onchain_reputation(identity.token_id)

        if rep_data:
            score = self._parse_reputation(rep_data)
            self._cache[cache_key] = score
            return score

        # Return default for new workers
        return ReputationScore(
            raw_score=50.0,
            bayesian_score=50.0,
            total_tasks=0,
            successful_tasks=0,
            disputed_tasks=0,
            last_updated=datetime.utcnow(),
            on_chain=False
        )

    async def update_reputation(
        self,
        wallet_address: str,
        task_id: str,
        success: bool,
        disputed: bool = False,
        rating: Optional[float] = None
    ) -> Optional[ReputationScore]:
        """
        Update worker reputation after task completion.

        Args:
            wallet_address: Worker's wallet
            task_id: Completed task ID
            success: Whether task was successful
            disputed: Whether task was disputed
            rating: Optional explicit rating (0-100)

        Returns:
            Updated ReputationScore
        """
        identity = await self.registry.get_identity(wallet_address)
        if not identity:
            logger.error(f"No identity for {wallet_address}")
            return None

        # Get current reputation
        current = await self.get_reputation(wallet_address, use_cache=False)
        if not current:
            current = ReputationScore(
                raw_score=50.0,
                bayesian_score=50.0,
                total_tasks=0,
                successful_tasks=0,
                disputed_tasks=0,
                last_updated=datetime.utcnow(),
                on_chain=False
            )

        # Calculate new score
        new_score = self._calculate_new_score(current, success, disputed, rating)

        # Store on-chain
        stored = await self._store_onchain_reputation(
            identity.token_id,
            new_score,
            task_id,
            "task_completed" if success else ("disputed" if disputed else "task_failed")
        )

        new_score.on_chain = stored

        # Update cache
        self._cache[wallet_address.lower()] = new_score

        # Emit event
        if stored:
            await self._emit_reputation_event(
                identity.token_id,
                new_score.raw_score,
                task_id,
                "task_completed" if success else "task_outcome"
            )

        return new_score

    async def get_reputation_history(
        self,
        wallet_address: str,
        limit: int = 20
    ) -> List[ReputationEvent]:
        """
        Get reputation change history.

        Args:
            wallet_address: Worker's wallet
            limit: Max events to return

        Returns:
            List of ReputationEvent
        """
        identity = await self.registry.get_identity(wallet_address)
        if not identity:
            return []

        # Get history from metadata
        history_data = await self.registry.get_metadata(
            identity.token_id,
            REPUTATION_HISTORY_KEY
        )

        if not history_data:
            return []

        try:
            events_json = json.loads(history_data.decode('utf-8'))
            events = []
            for e in events_json[-limit:]:
                events.append(ReputationEvent(
                    timestamp=datetime.fromisoformat(e['timestamp']),
                    task_id=e['task_id'],
                    score_delta=e['delta'],
                    reason=e['reason'],
                    tx_hash=e.get('tx_hash')
                ))
            return events
        except Exception as e:
            logger.error(f"Error parsing history: {e}")
            return []

    def calculate_bayesian_score(
        self,
        raw_score: float,
        total_tasks: int
    ) -> float:
        """
        Calculate Bayesian-adjusted score.

        Formula: (C * M + n * raw) / (C + n)
        Where:
            C = prior weight (15)
            M = prior mean (50)
            n = number of tasks
            raw = raw score

        Args:
            raw_score: Raw reputation score
            total_tasks: Total completed tasks

        Returns:
            Bayesian-adjusted score
        """
        n = total_tasks
        adjusted = (
            (self.BAYESIAN_C * self.BAYESIAN_M + n * raw_score) /
            (self.BAYESIAN_C + n)
        )
        return round(adjusted, 2)

    # Private methods

    async def _get_onchain_reputation(self, token_id: int) -> Optional[bytes]:
        """Get raw reputation data from chain."""
        return await self.registry.get_metadata(token_id, REPUTATION_KEY)

    async def _store_onchain_reputation(
        self,
        token_id: int,
        score: ReputationScore,
        task_id: str,
        reason: str
    ) -> bool:
        """Store reputation on-chain."""
        try:
            # Pack reputation data
            data = self._pack_reputation(score)

            # Store in metadata
            success = await self.registry.set_metadata(
                token_id,
                REPUTATION_KEY,
                data
            )

            if success:
                # Update history
                await self._append_history(token_id, task_id, score, reason)

            return success

        except Exception as e:
            logger.error(f"Error storing reputation: {e}")
            return False

    async def _append_history(
        self,
        token_id: int,
        task_id: str,
        score: ReputationScore,
        reason: str
    ) -> bool:
        """Append to reputation history."""
        try:
            # Get current history
            history_data = await self.registry.get_metadata(
                token_id,
                REPUTATION_HISTORY_KEY
            )

            if history_data:
                history = json.loads(history_data.decode('utf-8'))
            else:
                history = []

            # Append new event
            history.append({
                'timestamp': datetime.utcnow().isoformat(),
                'task_id': task_id,
                'delta': score.raw_score - 50,  # Delta from neutral
                'reason': reason
            })

            # Keep last 100 events
            history = history[-100:]

            # Store
            return await self.registry.set_metadata(
                token_id,
                REPUTATION_HISTORY_KEY,
                json.dumps(history).encode('utf-8')
            )

        except Exception as e:
            logger.error(f"Error appending history: {e}")
            return False

    async def _emit_reputation_event(
        self,
        token_id: int,
        score: float,
        task_id: str,
        reason: str
    ) -> Optional[str]:
        """Emit reputation update event (NOW-052)."""
        # This would call a separate events contract
        # For now, just log
        logger.info(
            f"ReputationUpdated: token={token_id}, "
            f"score={score}, task={task_id}, reason={reason}"
        )
        return None  # Would return tx_hash

    def _calculate_new_score(
        self,
        current: ReputationScore,
        success: bool,
        disputed: bool,
        rating: Optional[float]
    ) -> ReputationScore:
        """Calculate new reputation score."""
        # Update counters
        total = current.total_tasks + 1
        successful = current.successful_tasks + (1 if success else 0)
        disputes = current.disputed_tasks + (1 if disputed else 0)

        # Calculate raw score
        if rating is not None:
            # Use explicit rating
            # Weighted average with existing
            n = current.total_tasks
            raw = ((current.raw_score * n) + rating) / (n + 1) if n > 0 else rating
        else:
            # Calculate from success rate
            if total > 0:
                success_rate = successful / total
                # Map to 0-100 with dispute penalty
                raw = (success_rate * 100) - (disputes * 5)
                raw = max(0, min(100, raw))
            else:
                raw = 50.0

        # Calculate Bayesian score
        bayesian = self.calculate_bayesian_score(raw, total)

        return ReputationScore(
            raw_score=round(raw, 2),
            bayesian_score=bayesian,
            total_tasks=total,
            successful_tasks=successful,
            disputed_tasks=disputes,
            last_updated=datetime.utcnow(),
            on_chain=False  # Set by caller after storage
        )

    def _pack_reputation(self, score: ReputationScore) -> bytes:
        """Pack reputation into bytes for on-chain storage."""
        # Format: raw(f32) + bayesian(f32) + total(u32) + success(u32) + disputes(u32) + timestamp(u64)
        return struct.pack(
            '<ffIIIQ',
            score.raw_score,
            score.bayesian_score,
            score.total_tasks,
            score.successful_tasks,
            score.disputed_tasks,
            int(score.last_updated.timestamp())
        )

    def _parse_reputation(self, data: bytes) -> ReputationScore:
        """Parse reputation from on-chain bytes."""
        try:
            raw, bayesian, total, success, disputes, ts = struct.unpack('<ffIIIQ', data)
            return ReputationScore(
                raw_score=raw,
                bayesian_score=bayesian,
                total_tasks=total,
                successful_tasks=success,
                disputed_tasks=disputes,
                last_updated=datetime.fromtimestamp(ts),
                on_chain=True
            )
        except Exception as e:
            logger.error(f"Error parsing reputation: {e}")
            return ReputationScore(
                raw_score=50.0,
                bayesian_score=50.0,
                total_tasks=0,
                successful_tasks=0,
                disputed_tasks=0,
                last_updated=datetime.utcnow(),
                on_chain=False
            )


# Utility functions

def reputation_tier(score: float) -> str:
    """
    Get reputation tier name.

    Args:
        score: Bayesian-adjusted score

    Returns:
        Tier name
    """
    if score >= 90:
        return "elite"
    elif score >= 75:
        return "trusted"
    elif score >= 60:
        return "established"
    elif score >= 40:
        return "new"
    else:
        return "at_risk"


def min_reputation_for_bounty(bounty_usd: float) -> int:
    """
    Get minimum reputation required for a bounty amount.

    Args:
        bounty_usd: Bounty in USD

    Returns:
        Minimum reputation score
    """
    if bounty_usd < 10:
        return 0
    elif bounty_usd < 50:
        return 30
    elif bounty_usd < 200:
        return 50
    elif bounty_usd < 500:
        return 70
    else:
        return 85
