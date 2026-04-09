"""
Tier Router — Selects Ring 2 inference strategy based on task bounty.

This is the cost-control gate: cheap tasks skip Ring 2 inference entirely,
medium tasks run a single LLM check, high-value tasks run a 3-way consensus.

Default thresholds (override-able via PlatformConfig):
- CHEAP:    bounty <  $1     -> no LLM call ($0)
- STANDARD: bounty $1 - $10  -> 1 LLM call (~$0.001)
- MAX:      bounty >= $10    -> 2 LLM calls + consensus (~$0.003)

Thresholds can be overridden per-category via ArbiterConfig.consensus_required
(forces MAX even on low bounty for high-stakes categories like human_authority).
"""

import logging
from dataclasses import dataclass
from decimal import Decimal

from .types import ArbiterConfig, ArbiterTier

logger = logging.getLogger(__name__)


# Default tier boundaries (USD). Override via PlatformConfig keys:
#   arbiter.tier.cheap_max_usd
#   arbiter.tier.standard_max_usd
DEFAULT_CHEAP_MAX_USD = Decimal("1.00")
DEFAULT_STANDARD_MAX_USD = Decimal("10.00")


@dataclass
class TierDecision:
    """Result of tier routing."""

    tier: ArbiterTier
    reason: str
    bounty_usd: float
    max_cost_allowed_usd: float  # Cost cap derived from bounty * config ratio


class TierRouter:
    """Routes a task to the appropriate Ring 2 inference tier.

    Cost control is enforced here BEFORE any LLM call is made:
    1. Bounty-based tier selection (cheap/standard/max)
    2. Hard cost cap from config (max_cost_per_eval_usd)
    3. Cost-to-bounty ratio cap (default 10%)
    """

    def __init__(
        self,
        cheap_max_usd: Decimal = DEFAULT_CHEAP_MAX_USD,
        standard_max_usd: Decimal = DEFAULT_STANDARD_MAX_USD,
    ):
        self.cheap_max_usd = cheap_max_usd
        self.standard_max_usd = standard_max_usd

    def select_tier(
        self,
        bounty_usd: float,
        config: ArbiterConfig,
        is_disputed: bool = False,
    ) -> TierDecision:
        """Decide which Ring 2 tier to use for this task.

        Args:
            bounty_usd: Task bounty in USD (gross, before fee split)
            config: Per-category arbiter config with thresholds + caps
            is_disputed: If true, bypass tier routing and go straight to MAX

        Returns:
            TierDecision with selected tier, reason, and cost cap.
        """
        # Defensive: clamp invalid bounty values to 0 (cheap tier, no LLM cost).
        # Negative bounty would produce a negative cost cap downstream.
        if bounty_usd is None or bounty_usd < 0:
            logger.error(
                "Invalid bounty_usd %r -- clamping to 0 (forces CHEAP tier)",
                bounty_usd,
            )
            bounty_usd = 0.0
        bounty = Decimal(str(bounty_usd))

        # 1. Disputes always escalate to max safety
        if is_disputed:
            return TierDecision(
                tier=ArbiterTier.MAX,
                reason="Disputed submission -- max safety required",
                bounty_usd=bounty_usd,
                max_cost_allowed_usd=self._compute_cost_cap(bounty_usd, config),
            )

        # 2. Category override (e.g., human_authority always needs consensus)
        if config.consensus_required:
            return TierDecision(
                tier=ArbiterTier.MAX,
                reason=f"Category {config.category} requires consensus",
                bounty_usd=bounty_usd,
                max_cost_allowed_usd=self._compute_cost_cap(bounty_usd, config),
            )

        # 3. Bounty-based selection
        if bounty < self.cheap_max_usd:
            tier = ArbiterTier.CHEAP
            reason = f"Cheap tier: bounty ${bounty_usd:.4f} < ${self.cheap_max_usd}"
        elif bounty < self.standard_max_usd:
            tier = ArbiterTier.STANDARD
            reason = (
                f"Standard tier: ${self.cheap_max_usd} <= ${bounty_usd:.2f} "
                f"< ${self.standard_max_usd}"
            )
        else:
            tier = ArbiterTier.MAX
            reason = (
                f"Max safety tier: bounty ${bounty_usd:.2f} >= ${self.standard_max_usd}"
            )

        # 4. Cap by category max_tier (e.g., a category may forbid MAX)
        tier = self._apply_max_tier_cap(tier, config.max_tier)

        return TierDecision(
            tier=tier,
            reason=reason,
            bounty_usd=bounty_usd,
            max_cost_allowed_usd=self._compute_cost_cap(bounty_usd, config),
        )

    @staticmethod
    def _apply_max_tier_cap(
        selected: ArbiterTier, max_allowed: ArbiterTier
    ) -> ArbiterTier:
        """Don't exceed the category's max_tier setting."""
        order = {ArbiterTier.CHEAP: 0, ArbiterTier.STANDARD: 1, ArbiterTier.MAX: 2}
        if order[selected] > order[max_allowed]:
            return max_allowed
        return selected

    @staticmethod
    def _compute_cost_cap(bounty_usd: float, config: ArbiterConfig) -> float:
        """Compute hard USD cap on Ring 2 inference cost.

        Cap = max(0, min(absolute_max, bounty * ratio))

        Example: bounty=$0.50, ratio=0.10, absolute=$0.20
                 -> cap = min(0.20, 0.05) = $0.05
        """
        bounty = max(0.0, float(bounty_usd or 0))
        ratio_cap = bounty * config.cost_to_bounty_ratio_max
        absolute_cap = config.max_cost_per_eval_usd
        # Clamp to >= 0 to defend against any future negative defaults.
        return max(0.0, min(absolute_cap, ratio_cap))


def get_default_router() -> TierRouter:
    """Factory: returns router with default thresholds.

    PlatformConfig overrides should be applied at the call site
    (Phase 1 Task 1.5 wires this up).
    """
    return TierRouter()
