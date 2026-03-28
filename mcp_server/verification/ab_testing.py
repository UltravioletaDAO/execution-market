"""
A/B Testing Framework for Verification Prompts

Routes a percentage of submissions to alternate prompt versions
for evaluation. Traffic splits are configured via environment variable.

Config format (JSON):
  VERIFICATION_AB_TEST='{"photint-v1.1-physical_presence": 0.20}'

This means 20% of physical_presence submissions will use v1.1 prompts.

Part of PHOTINT Verification Overhaul (Phase 6).
"""

import json
import logging
import os
import random

logger = logging.getLogger(__name__)


def _load_ab_config() -> dict:
    """Load A/B test config from environment."""
    raw = os.environ.get("VERIFICATION_AB_TEST", "")
    if not raw:
        return {}
    try:
        config = json.loads(raw)
        if not isinstance(config, dict):
            return {}
        return config
    except (json.JSONDecodeError, TypeError):
        logger.warning("Invalid VERIFICATION_AB_TEST config: %s", raw)
        return {}


def select_prompt_variant(
    category: str,
    base_version: str,
) -> str:
    """
    Select which prompt version to use, considering A/B test config.

    Args:
        category: Task category (e.g. "physical_presence").
        base_version: Default prompt version (e.g. "photint-v1.0-physical_presence").

    Returns:
        The version string to use (either base or variant).
    """
    config = _load_ab_config()
    if not config:
        return base_version

    # Check if any variant matches this category
    for variant_version, traffic_pct in config.items():
        if category in variant_version:
            if random.random() < traffic_pct:
                logger.info(
                    "A/B test: routing to variant %s (%.0f%% traffic)",
                    variant_version,
                    traffic_pct * 100,
                )
                return variant_version

    return base_version


def get_active_experiments() -> dict:
    """List active A/B test experiments."""
    return _load_ab_config()
