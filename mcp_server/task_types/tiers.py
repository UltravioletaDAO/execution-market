"""
Chamba Task Tiers (NOW-131)

Defines the three-tier pricing structure for tasks:
- Tier 1 ($1-5): Quick tasks, low barrier, high volume
- Tier 2 ($10-30): Detailed tasks, moderate requirements
- Tier 3 ($50-500): Complex tasks, professional-level work

Each tier has:
- Bounty range
- Minimum reputation requirements
- Verification level
- Insurance requirements
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any


class TaskTier(str, Enum):
    """
    Task pricing tiers based on complexity and requirements.

    TIER_1 (Simple): $1-5
        - Quick observations, single photo evidence
        - No special skills required
        - Basic verification only
        - Insurance optional

    TIER_2 (Standard): $10-30
        - Detailed inspections, multiple evidence types
        - May require specific location/time
        - AI-assisted verification
        - Basic insurance recommended

    TIER_3 (Premium): $50-500
        - Professional-level work
        - Complex multi-step verification
        - May require credentials or special access
        - Insurance required
    """
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"


@dataclass
class TierConfig:
    """
    Configuration for a task tier.

    Attributes:
        tier: The tier level
        min_bounty: Minimum bounty in USD
        max_bounty: Maximum bounty in USD
        min_reputation: Minimum reputation score (0-100)
        verification_level: Level of verification required
        insurance_required: Whether task insurance is mandatory
        max_active_tasks: Max concurrent tasks a worker can have
        default_deadline_hours: Default deadline for this tier
        escrow_hold_hours: How long to hold escrow after completion
    """
    tier: TaskTier
    min_bounty: Decimal
    max_bounty: Decimal
    min_reputation: int
    verification_level: str
    insurance_required: bool
    max_active_tasks: int = 5
    default_deadline_hours: int = 24
    escrow_hold_hours: int = 24
    description: str = ""

    def validate_bounty(self, bounty: Decimal) -> tuple[bool, str]:
        """
        Validate that a bounty falls within tier range.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if bounty < self.min_bounty:
            return False, f"Bounty ${bounty} is below tier minimum ${self.min_bounty}"
        if bounty > self.max_bounty:
            return False, f"Bounty ${bounty} exceeds tier maximum ${self.max_bounty}"
        return True, ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "tier": self.tier.value,
            "min_bounty": str(self.min_bounty),
            "max_bounty": str(self.max_bounty),
            "min_reputation": self.min_reputation,
            "verification_level": self.verification_level,
            "insurance_required": self.insurance_required,
            "max_active_tasks": self.max_active_tasks,
            "default_deadline_hours": self.default_deadline_hours,
            "escrow_hold_hours": self.escrow_hold_hours,
            "description": self.description,
        }


# Default tier configurations
TIER_CONFIGS: Dict[TaskTier, TierConfig] = {
    TaskTier.TIER_1: TierConfig(
        tier=TaskTier.TIER_1,
        min_bounty=Decimal("1.00"),
        max_bounty=Decimal("5.00"),
        min_reputation=0,  # Anyone can start
        verification_level="basic",
        insurance_required=False,
        max_active_tasks=10,  # Can take many simple tasks
        default_deadline_hours=4,
        escrow_hold_hours=12,
        description="Quick tasks: observations, store checks, simple photos",
    ),
    TaskTier.TIER_2: TierConfig(
        tier=TaskTier.TIER_2,
        min_bounty=Decimal("10.00"),
        max_bounty=Decimal("30.00"),
        min_reputation=30,  # Some track record
        verification_level="ai_assisted",
        insurance_required=False,  # Recommended but not required
        max_active_tasks=5,
        default_deadline_hours=24,
        escrow_hold_hours=24,
        description="Detailed tasks: inspections, multi-photo evidence, trials",
    ),
    TaskTier.TIER_3: TierConfig(
        tier=TaskTier.TIER_3,
        min_bounty=Decimal("50.00"),
        max_bounty=Decimal("500.00"),
        min_reputation=60,  # Proven track record
        verification_level="multi_step",
        insurance_required=True,
        max_active_tasks=3,  # Focus on quality
        default_deadline_hours=48,
        escrow_hold_hours=48,
        description="Professional tasks: complex deliveries, credentialed work",
    ),
}


class TierManager:
    """
    Manages task tier operations.

    Provides methods for:
    - Determining appropriate tier for a bounty
    - Checking worker eligibility for tiers
    - Tier progression recommendations
    """

    def __init__(self, configs: Optional[Dict[TaskTier, TierConfig]] = None):
        self.configs = configs or TIER_CONFIGS

    def get_config(self, tier: TaskTier) -> TierConfig:
        """Get configuration for a tier."""
        return self.configs[tier]

    def determine_tier(self, bounty: Decimal) -> TaskTier:
        """
        Determine appropriate tier for a bounty amount.

        Args:
            bounty: Bounty amount in USD

        Returns:
            Appropriate TaskTier

        Raises:
            ValueError: If bounty is outside all tier ranges
        """
        # Check tiers in order from lowest to highest
        for tier in [TaskTier.TIER_1, TaskTier.TIER_2, TaskTier.TIER_3]:
            config = self.configs[tier]
            if config.min_bounty <= bounty <= config.max_bounty:
                return tier

        # Handle edge cases
        if bounty < self.configs[TaskTier.TIER_1].min_bounty:
            raise ValueError(
                f"Bounty ${bounty} is below minimum allowed "
                f"(${self.configs[TaskTier.TIER_1].min_bounty})"
            )
        if bounty > self.configs[TaskTier.TIER_3].max_bounty:
            raise ValueError(
                f"Bounty ${bounty} exceeds maximum allowed "
                f"(${self.configs[TaskTier.TIER_3].max_bounty})"
            )

        # Bounty falls in a gap - assign to lower tier
        if self.configs[TaskTier.TIER_1].max_bounty < bounty < self.configs[TaskTier.TIER_2].min_bounty:
            return TaskTier.TIER_1  # Round down to Tier 1 max
        if self.configs[TaskTier.TIER_2].max_bounty < bounty < self.configs[TaskTier.TIER_3].min_bounty:
            return TaskTier.TIER_2  # Round down to Tier 2 max

        return TaskTier.TIER_1  # Fallback

    def check_worker_eligibility(
        self,
        tier: TaskTier,
        worker_reputation: int,
        worker_active_tasks: int = 0,
    ) -> tuple[bool, List[str]]:
        """
        Check if a worker is eligible for tasks in a tier.

        Args:
            tier: Target tier
            worker_reputation: Worker's reputation score
            worker_active_tasks: Number of tasks worker currently has

        Returns:
            Tuple of (is_eligible, list of blocking reasons)
        """
        config = self.configs[tier]
        blocking_reasons = []

        if worker_reputation < config.min_reputation:
            blocking_reasons.append(
                f"Reputation {worker_reputation} is below tier minimum {config.min_reputation}"
            )

        if worker_active_tasks >= config.max_active_tasks:
            blocking_reasons.append(
                f"Already at max active tasks ({config.max_active_tasks}) for this tier"
            )

        return len(blocking_reasons) == 0, blocking_reasons

    def get_accessible_tiers(self, worker_reputation: int) -> List[TaskTier]:
        """
        Get all tiers a worker can access based on reputation.

        Args:
            worker_reputation: Worker's reputation score

        Returns:
            List of accessible tiers
        """
        accessible = []
        for tier in TaskTier:
            config = self.configs[tier]
            if worker_reputation >= config.min_reputation:
                accessible.append(tier)
        return accessible

    def suggest_next_tier(
        self,
        current_tier: TaskTier,
        worker_reputation: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Suggest what the worker needs to reach the next tier.

        Args:
            current_tier: Worker's current tier
            worker_reputation: Worker's reputation score

        Returns:
            Dict with next tier info and requirements, or None if at max tier
        """
        tier_order = [TaskTier.TIER_1, TaskTier.TIER_2, TaskTier.TIER_3]
        current_idx = tier_order.index(current_tier)

        if current_idx >= len(tier_order) - 1:
            return None  # Already at highest tier

        next_tier = tier_order[current_idx + 1]
        next_config = self.configs[next_tier]

        reputation_needed = max(0, next_config.min_reputation - worker_reputation)

        return {
            "next_tier": next_tier.value,
            "current_reputation": worker_reputation,
            "required_reputation": next_config.min_reputation,
            "reputation_needed": reputation_needed,
            "tier_description": next_config.description,
            "bounty_range": f"${next_config.min_bounty} - ${next_config.max_bounty}",
            "insurance_required": next_config.insurance_required,
        }

    def calculate_tier_stats(self, tier: TaskTier) -> Dict[str, Any]:
        """
        Get comprehensive stats for a tier.

        Args:
            tier: The tier to get stats for

        Returns:
            Dict with tier statistics
        """
        config = self.configs[tier]

        # Calculate expected hourly rate
        avg_bounty = (config.min_bounty + config.max_bounty) / 2
        tasks_per_hour = {
            TaskTier.TIER_1: Decimal("4"),  # ~15 min tasks
            TaskTier.TIER_2: Decimal("2"),  # ~30 min tasks
            TaskTier.TIER_3: Decimal("0.5"),  # ~2 hour tasks
        }[tier]

        expected_hourly = avg_bounty * tasks_per_hour

        return {
            "tier": tier.value,
            "bounty_range": {
                "min": str(config.min_bounty),
                "max": str(config.max_bounty),
                "average": str(avg_bounty),
            },
            "requirements": {
                "min_reputation": config.min_reputation,
                "insurance_required": config.insurance_required,
            },
            "limits": {
                "max_active_tasks": config.max_active_tasks,
                "default_deadline_hours": config.default_deadline_hours,
            },
            "expected_hourly_rate": str(expected_hourly),
            "verification_level": config.verification_level,
            "description": config.description,
        }


# Convenience function for simple tier lookup
def get_tier_for_bounty(bounty_usd: float) -> TaskTier:
    """
    Quick lookup of tier for a bounty amount.

    Args:
        bounty_usd: Bounty amount in USD

    Returns:
        Appropriate TaskTier
    """
    manager = TierManager()
    return manager.determine_tier(Decimal(str(bounty_usd)))


def get_tier_config(tier: TaskTier) -> TierConfig:
    """
    Get configuration for a tier.

    Args:
        tier: The tier

    Returns:
        TierConfig for that tier
    """
    return TIER_CONFIGS[tier]
