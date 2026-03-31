"""
Model Router — Tier-based Verification Routing

Decides which model tier to use based on task value, category,
worker reputation, and screening results.

Tier 0: Automated checks (EXIF, hashing, C2PA) — $0
Tier 1: Fast AI screening (Gemini Flash, GPT-4o-mini, Haiku) — ~$0.002/img
Tier 2: Detailed analysis (Claude Sonnet, GPT-4o) — ~$0.01/img
Tier 3: Expert review (Claude Opus) — ~$0.05/img

Part of PHOTINT Verification Overhaul (Phase 4).
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

TIER_ORDER = {"tier_0": 0, "tier_1": 1, "tier_2": 2, "tier_3": 3, "tier_4": 4}


def tier_exceeds(tier_a: str, tier_b: str) -> bool:
    """Check if tier_a is strictly higher than tier_b using numeric ordering."""
    return TIER_ORDER.get(tier_a, 0) > TIER_ORDER.get(tier_b, 0)


# Categories that always require Tier 2+ (high-stakes)
HIGH_STAKES_CATEGORIES = {
    "physical_presence",
    "human_authority",
    "bureaucratic",
    "emergency",
}

# Categories where Tier 1 screening is sufficient for low-value
LOW_STAKES_CATEGORIES = {
    "data_processing",
    "api_integration",
    "content_generation",
    "code_execution",
    "research",
    "multi_step_workflow",
}

# Physical categories where missing EXIF is suspicious
PHYSICAL_CATEGORIES = {"physical_presence", "simple_action"}


@dataclass
class ModelSelection:
    """Result of model routing decision."""

    start_tier: str  # Where verification begins
    max_tier: str  # Bounty-determined ceiling
    reason: str  # Why this routing was chosen
    tier: str = ""  # Backward compat alias for start_tier

    def __post_init__(self):
        if not self.tier:
            self.tier = self.start_tier


def select_tier(
    bounty_usd: float = 0.0,
    category: str = "general",
    worker_reputation: Optional[float] = None,
    worker_completed_tasks: Optional[int] = None,
    is_disputed: bool = False,
    has_exif: bool = True,
    photo_count: int = 1,
) -> ModelSelection:
    """Select verification tier based on bounty cap + category/worker start.

    Architecture:
    - max_tier: determined by bounty (cheap tasks can't use expensive models)
    - start_tier: determined by category + worker profile (risky submissions start higher)
    - Escalation within [start_tier, max_tier] range driven by confidence
    """
    # 1. Disputes bypass everything — expert review required
    if is_disputed:
        return ModelSelection(
            start_tier="tier_4",
            max_tier="tier_4",
            reason="Disputed submission — expert review required",
        )

    # 2. Determine max_tier from bounty
    if bounty_usd >= 1.0:
        max_tier = "tier_4"
    elif bounty_usd >= 0.10:
        max_tier = "tier_3"
    else:
        max_tier = "tier_2"

    # 3. Determine start_tier from category + worker signals
    if category in HIGH_STAKES_CATEGORIES:
        start_tier = "tier_2"
        reason = f"High-stakes category ({category})"
    elif worker_reputation is not None and worker_reputation < 3.0:
        start_tier = "tier_2"
        reason = f"Low reputation worker ({worker_reputation:.1f})"
    elif worker_completed_tasks is not None and worker_completed_tasks < 5:
        start_tier = "tier_2"
        reason = f"New worker ({worker_completed_tasks} completed tasks)"
    elif not has_exif and category in PHYSICAL_CATEGORIES:
        start_tier = "tier_2"
        reason = "No EXIF metadata on physical task"
    else:
        start_tier = "tier_1"
        reason = "Standard routing — start cheap"

    # 4. Ensure start_tier doesn't exceed max_tier
    if tier_exceeds(start_tier, max_tier):
        start_tier = max_tier

    return ModelSelection(start_tier=start_tier, max_tier=max_tier, reason=reason)


def should_escalate(
    tier: str,
    score: float,
    confidence: float,
) -> Optional[str]:
    """Check if current tier result warrants escalation to a higher tier.

    Uses AND logic for Tier 1-2 (both score AND confidence must be low)
    plus a safety valve for clearly bad scores. This keeps ~95% of images
    at Tier 1 while still escalating uncertain results.
    """
    if tier == "tier_1":
        if (score < 0.70 and confidence < 0.60) or score < 0.30:
            return "tier_2"
    elif tier == "tier_2":
        if (score < 0.60 and confidence < 0.50) or score < 0.25:
            return "tier_3"
    elif tier == "tier_3":
        if confidence < 0.50:
            return "tier_4"
    # tier_4 is terminal — never escalate
    return None
