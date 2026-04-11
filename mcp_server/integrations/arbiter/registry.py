"""
Arbiter Registry — Per-category configuration.

Maps each of the 21 task categories (from mcp_server.models.TaskCategory)
to an ArbiterConfig with thresholds, evidence requirements, and tier caps.

Categories that fall outside this dict get GENERIC_FALLBACK config.
Per-task overrides can be applied via PlatformConfig at runtime.
"""

import logging
from typing import Dict, List, Optional

from .types import ArbiterConfig, ArbiterTier

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Two-axis blend weights: authenticity (Ring 1) vs completion (Ring 2)
#
# Guidelines:
#   - Physical proof categories: authenticity 70%, completion 30%
#   - Knowledge/content categories: authenticity 30%, completion 70%
#   - Balanced categories: 50/50
#   - Authority/bureaucratic categories: authenticity 60%, completion 40%
#   - Digital/agent categories: authenticity 20%, completion 80%
#     (no photo expected; completion quality matters most)
# ---------------------------------------------------------------------------

BlendWeights = Dict[str, float]  # {"authenticity": float, "completion": float}

BLEND_WEIGHTS: Dict[str, BlendWeights] = {
    # Physical-world categories -- authenticity matters more
    "physical_presence": {"authenticity": 0.70, "completion": 0.30},
    "location_based": {"authenticity": 0.70, "completion": 0.30},
    "sensory": {"authenticity": 0.70, "completion": 0.30},
    "emergency": {"authenticity": 0.70, "completion": 0.30},
    # Balanced categories
    "simple_action": {"authenticity": 0.50, "completion": 0.50},
    "digital_physical": {"authenticity": 0.50, "completion": 0.50},
    "social": {"authenticity": 0.50, "completion": 0.50},
    "social_proof": {"authenticity": 0.50, "completion": 0.50},
    "proxy": {"authenticity": 0.50, "completion": 0.50},
    "verification": {"authenticity": 0.50, "completion": 0.50},
    # Authority/bureaucratic -- authenticity still matters
    "human_authority": {"authenticity": 0.60, "completion": 0.40},
    "bureaucratic": {"authenticity": 0.60, "completion": 0.40},
    # Knowledge/content categories -- completion matters more
    "knowledge_access": {"authenticity": 0.30, "completion": 0.70},
    "data_collection": {"authenticity": 0.30, "completion": 0.70},
    "creative": {"authenticity": 0.30, "completion": 0.70},
    # Digital/agent categories -- completion dominates
    "data_processing": {"authenticity": 0.20, "completion": 0.80},
    "api_integration": {"authenticity": 0.20, "completion": 0.80},
    "content_generation": {"authenticity": 0.20, "completion": 0.80},
    "code_execution": {"authenticity": 0.20, "completion": 0.80},
    "research": {"authenticity": 0.20, "completion": 0.80},
    "multi_step_workflow": {"authenticity": 0.20, "completion": 0.80},
}

# Fallback blend weights for unknown categories -- conservative 50/50
GENERIC_BLEND_WEIGHTS: BlendWeights = {"authenticity": 0.50, "completion": 0.50}


# ---------------------------------------------------------------------------
# Per-category configurations
# ---------------------------------------------------------------------------

# Physical-world categories — usually require photo + GPS, high stakes
PHYSICAL_CONFIGS: Dict[str, ArbiterConfig] = {
    "physical_presence": ArbiterConfig(
        category="physical_presence",
        pass_threshold=0.80,
        fail_threshold=0.30,
        requires_photo=True,
        requires_gps=True,
    ),
    "simple_action": ArbiterConfig(
        category="simple_action",
        pass_threshold=0.75,
        fail_threshold=0.30,
        requires_photo=True,
    ),
    "location_based": ArbiterConfig(
        category="location_based",
        pass_threshold=0.80,
        fail_threshold=0.30,
        requires_photo=True,
        requires_gps=True,
    ),
    "digital_physical": ArbiterConfig(
        category="digital_physical",
        pass_threshold=0.80,
        fail_threshold=0.25,
        requires_photo=True,
    ),
    "sensory": ArbiterConfig(
        category="sensory",
        pass_threshold=0.70,  # Subjective by nature -- lower bar
        fail_threshold=0.25,
        requires_photo=True,
    ),
    "social": ArbiterConfig(
        category="social",
        pass_threshold=0.70,
        fail_threshold=0.25,
    ),
    "creative": ArbiterConfig(
        category="creative",
        pass_threshold=0.70,
        fail_threshold=0.25,
    ),
    "emergency": ArbiterConfig(
        category="emergency",
        pass_threshold=0.85,  # High bar -- emergencies have legal weight
        fail_threshold=0.20,
        requires_photo=True,
        consensus_required=True,  # Always force MAX tier
    ),
}

# Knowledge / authority / bureaucratic — high accuracy needed
HIGH_STAKES_CONFIGS: Dict[str, ArbiterConfig] = {
    "knowledge_access": ArbiterConfig(
        category="knowledge_access",
        pass_threshold=0.80,
        fail_threshold=0.25,
        requires_photo=True,
    ),
    "human_authority": ArbiterConfig(
        category="human_authority",
        pass_threshold=0.90,  # Notarization, legal -- max bar
        fail_threshold=0.20,
        requires_photo=True,
        consensus_required=True,  # Always force MAX tier
    ),
    "bureaucratic": ArbiterConfig(
        category="bureaucratic",
        pass_threshold=0.85,
        fail_threshold=0.20,
        requires_photo=True,
        consensus_required=True,  # Always force MAX tier
    ),
    "verification": ArbiterConfig(
        category="verification",
        pass_threshold=0.80,
        fail_threshold=0.25,
        requires_photo=True,
    ),
}

# Social proof / data collection / proxy — variable evidence types
SOCIAL_DATA_CONFIGS: Dict[str, ArbiterConfig] = {
    "social_proof": ArbiterConfig(
        category="social_proof",
        pass_threshold=0.75,
        fail_threshold=0.30,
    ),
    "data_collection": ArbiterConfig(
        category="data_collection",
        pass_threshold=0.80,
        fail_threshold=0.25,
    ),
    "proxy": ArbiterConfig(
        category="proxy",
        pass_threshold=0.80,  # Trust-heavy -- worker acts on behalf of agent
        fail_threshold=0.25,
        requires_photo=True,
    ),
}

# Digital/agent categories — no photo expected, schema-driven validation
DIGITAL_CONFIGS: Dict[str, ArbiterConfig] = {
    "data_processing": ArbiterConfig(
        category="data_processing",
        pass_threshold=0.75,
        fail_threshold=0.30,
        requires_photo=False,
        max_tier=ArbiterTier.STANDARD,  # Cap cost -- mostly schema checks
    ),
    "api_integration": ArbiterConfig(
        category="api_integration",
        pass_threshold=0.75,
        fail_threshold=0.30,
        requires_photo=False,
        max_tier=ArbiterTier.STANDARD,
    ),
    "content_generation": ArbiterConfig(
        category="content_generation",
        pass_threshold=0.70,  # Subjective output
        fail_threshold=0.25,
        requires_photo=False,
    ),
    "code_execution": ArbiterConfig(
        category="code_execution",
        pass_threshold=0.80,
        fail_threshold=0.25,
        requires_photo=False,
    ),
    "research": ArbiterConfig(
        category="research",
        pass_threshold=0.70,
        fail_threshold=0.25,
        requires_photo=False,
    ),
    "multi_step_workflow": ArbiterConfig(
        category="multi_step_workflow",
        pass_threshold=0.75,
        fail_threshold=0.30,
        requires_photo=False,
    ),
}

# ---------------------------------------------------------------------------
# Combined registry (21 categories total)
# ---------------------------------------------------------------------------

CATEGORY_CONFIGS: Dict[str, ArbiterConfig] = {
    **PHYSICAL_CONFIGS,
    **HIGH_STAKES_CONFIGS,
    **SOCIAL_DATA_CONFIGS,
    **DIGITAL_CONFIGS,
}

# Fallback for unknown categories -- conservative thresholds
GENERIC_FALLBACK = ArbiterConfig(
    category="__generic__",
    pass_threshold=0.85,  # High bar when we don't know what we're verifying
    fail_threshold=0.25,
)


# ---------------------------------------------------------------------------
# Registry interface
# ---------------------------------------------------------------------------


class ArbiterRegistry:
    """Looks up per-category arbiter configuration.

    Falls back to GENERIC_FALLBACK for unknown categories. Future: add
    runtime overrides via PlatformConfig (Phase 1 Task 1.5 wires this).
    """

    def __init__(
        self,
        configs: Optional[Dict[str, ArbiterConfig]] = None,
        blend_weights: Optional[Dict[str, BlendWeights]] = None,
    ):
        self._configs = configs if configs is not None else CATEGORY_CONFIGS
        self._blend_weights = (
            blend_weights if blend_weights is not None else BLEND_WEIGHTS
        )

    def get(self, category: str) -> ArbiterConfig:
        """Return config for category, or fallback if unknown."""
        if not category:
            logger.warning("Empty category -- using generic fallback")
            return GENERIC_FALLBACK
        config = self._configs.get(category)
        if config is None:
            logger.warning(
                "Unknown category '%s' -- using generic fallback (pass=%.2f, fail=%.2f)",
                category,
                GENERIC_FALLBACK.pass_threshold,
                GENERIC_FALLBACK.fail_threshold,
            )
            return GENERIC_FALLBACK
        return config

    def get_blend_weights(self, category: str) -> BlendWeights:
        """Return authenticity/completion blend weights for a category.

        Falls back to GENERIC_BLEND_WEIGHTS (50/50) for unknown categories.
        """
        if not category:
            return GENERIC_BLEND_WEIGHTS
        return self._blend_weights.get(category, GENERIC_BLEND_WEIGHTS)

    def all_categories(self) -> List[str]:
        """Return list of all configured categories (for testing/debug)."""
        return sorted(self._configs.keys())

    def consensus_required_categories(self) -> List[str]:
        """Return categories that always force MAX tier (consensus_required=True)."""
        return sorted(
            cat for cat, cfg in self._configs.items() if cfg.consensus_required
        )


def get_default_registry() -> ArbiterRegistry:
    """Factory: returns registry loaded with the 21 default category configs."""
    return ArbiterRegistry()
