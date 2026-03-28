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


@dataclass
class ModelSelection:
    """Result of model routing decision."""

    tier: str  # "tier_1", "tier_2", "tier_3"
    reason: str  # Why this tier was selected


def select_tier(
    bounty_usd: float = 0.0,
    category: str = "general",
    worker_reputation: Optional[float] = None,
    worker_completed_tasks: Optional[int] = None,
    is_disputed: bool = False,
    has_exif: bool = True,
    photo_count: int = 1,
) -> ModelSelection:
    """
    Determine which verification tier to use.

    Args:
        bounty_usd: Task bounty amount in USD.
        category: Task category.
        worker_reputation: Worker's reputation score (0-5).
        worker_completed_tasks: Number of tasks the worker has completed.
        is_disputed: Whether this submission is disputed.
        has_exif: Whether the submitted image has EXIF metadata.
        photo_count: Number of photos submitted.

    Returns:
        ModelSelection with tier and reason.
    """
    # Disputes always get expert review
    if is_disputed:
        return ModelSelection(
            tier="tier_3",
            reason="Disputed submission requires expert review",
        )

    # High-value tasks get expert review
    if bounty_usd >= 10.0:
        return ModelSelection(
            tier="tier_3",
            reason=f"High-value task (${bounty_usd:.2f}) requires expert review",
        )

    # High-stakes categories always get detailed analysis
    if category in HIGH_STAKES_CATEGORIES:
        if bounty_usd >= 5.0:
            return ModelSelection(
                tier="tier_3",
                reason=f"High-stakes category '{category}' with bounty ${bounty_usd:.2f}",
            )
        return ModelSelection(
            tier="tier_2",
            reason=f"High-stakes category '{category}' requires detailed analysis",
        )

    # New workers get extra scrutiny
    if worker_completed_tasks is not None and worker_completed_tasks < 5:
        return ModelSelection(
            tier="tier_2",
            reason=f"New worker ({worker_completed_tasks} completed tasks)",
        )

    # Low reputation workers get extra scrutiny
    if worker_reputation is not None and worker_reputation < 3.0:
        return ModelSelection(
            tier="tier_2",
            reason=f"Low reputation worker ({worker_reputation:.1f})",
        )

    # No EXIF metadata is suspicious — needs deeper analysis
    if not has_exif and category not in LOW_STAKES_CATEGORIES:
        return ModelSelection(
            tier="tier_2",
            reason="No EXIF metadata — image may be processed or AI-generated",
        )

    # Medium-value tasks
    if bounty_usd >= 1.0:
        return ModelSelection(
            tier="tier_2",
            reason=f"Medium-value task (${bounty_usd:.2f})",
        )

    # Digital-only categories can use screening
    if category in LOW_STAKES_CATEGORIES:
        return ModelSelection(
            tier="tier_1",
            reason=f"Digital category '{category}' — screening sufficient",
        )

    # Low-value tasks with good indicators
    if bounty_usd < 0.50 and has_exif:
        return ModelSelection(
            tier="tier_1",
            reason=f"Low-value task (${bounty_usd:.2f}) with EXIF present",
        )

    # Default: Tier 2 (safe middle ground)
    return ModelSelection(
        tier="tier_2",
        reason="Default routing — detailed analysis",
    )


def should_escalate(
    tier: str,
    score: float,
    confidence: float,
) -> Optional[str]:
    """
    Determine if a tier result should be escalated to the next tier.

    Returns the next tier string, or None if no escalation needed.
    """
    if tier == "tier_1":
        if score < 0.90 or confidence < 0.80:
            return "tier_2"
    elif tier == "tier_2":
        if confidence < 0.70:
            return "tier_3"

    return None


def needs_consensus(bounty_usd: float, is_disputed: bool = False) -> bool:
    """Check if this task requires multi-model consensus verification."""
    return bounty_usd >= 10.0 or is_disputed
