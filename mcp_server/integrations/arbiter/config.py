"""
Arbiter Configuration — Reads from PlatformConfig.

Bridges the static defaults in registry.py / tier_router.py with
runtime overrides stored in the platform_config table. Lets ops adjust
thresholds, tier boundaries, and cost caps without redeploying.

Used by:
- ArbiterService.evaluate() to check if arbiter is globally enabled
- TierRouter to read overridden tier boundaries
- Phase 2 processor.py to gate whether the arbiter runs at all
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cached config keys (mirrors platform_config.py defaults)
# ---------------------------------------------------------------------------

KEY_MASTER_SWITCH = "feature.arbiter_enabled"
KEY_TIER_CHEAP_MAX = "arbiter.tier.cheap_max_usd"
KEY_TIER_STANDARD_MAX = "arbiter.tier.standard_max_usd"
KEY_PASS_THRESHOLD = "arbiter.thresholds.pass"
KEY_FAIL_THRESHOLD = "arbiter.thresholds.fail"
KEY_COST_MAX_PER_EVAL = "arbiter.cost.max_per_eval_usd"
KEY_COST_DAILY_BUDGET = "arbiter.cost.daily_budget_usd"
KEY_COST_ALERT_PCT = "arbiter.cost.alert_threshold_pct"
KEY_COST_BOUNTY_RATIO = "arbiter.cost.bounty_ratio_max"
KEY_ESCALATION_TIMEOUT_HOURS = "arbiter.escalation.timeout_hours"
KEY_ESCALATION_MIN_TRUST = "arbiter.escalation.min_human_trust_tier"
KEY_PROVIDER_RING2_A = "arbiter.providers.preferred_ring2_a"
KEY_PROVIDER_RING2_B = "arbiter.providers.preferred_ring2_b"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


async def is_arbiter_enabled() -> bool:
    """Check if arbiter mode is globally enabled.

    Returns False if:
    - PlatformConfig key is False (default)
    - PlatformConfig is unavailable (fail-closed)

    This is the master kill-switch. When False, all arbiter_mode values on
    tasks fall back to 'manual' regardless of what the agent requested.
    """
    try:
        from config.platform_config import PlatformConfig

        return bool(await PlatformConfig.get(KEY_MASTER_SWITCH, False))
    except Exception as e:
        logger.warning(
            "Failed to read arbiter master switch from PlatformConfig: %s -- defaulting to disabled",
            e,
        )
        return False


async def get_tier_boundaries() -> Dict[str, Decimal]:
    """Read tier boundaries from PlatformConfig.

    Returns dict with 'cheap_max' and 'standard_max' keys (USD).
    Falls back to defaults if config unavailable.
    """
    defaults = {
        "cheap_max": Decimal("1.00"),
        "standard_max": Decimal("10.00"),
    }
    try:
        from config.platform_config import PlatformConfig

        return {
            "cheap_max": Decimal(
                str(await PlatformConfig.get(KEY_TIER_CHEAP_MAX, defaults["cheap_max"]))
            ),
            "standard_max": Decimal(
                str(
                    await PlatformConfig.get(
                        KEY_TIER_STANDARD_MAX, defaults["standard_max"]
                    )
                )
            ),
        }
    except Exception as e:
        logger.warning("Failed to read tier boundaries: %s -- using defaults", e)
        return defaults


async def get_cost_controls() -> Dict[str, Any]:
    """Read cost control settings from PlatformConfig."""
    defaults = {
        "max_per_eval_usd": Decimal("0.20"),
        "daily_budget_usd": Decimal("100.00"),
        "alert_threshold_pct": Decimal("0.80"),
        "bounty_ratio_max": Decimal("0.10"),
    }
    try:
        from config.platform_config import PlatformConfig

        return {
            "max_per_eval_usd": Decimal(
                str(
                    await PlatformConfig.get(
                        KEY_COST_MAX_PER_EVAL, defaults["max_per_eval_usd"]
                    )
                )
            ),
            "daily_budget_usd": Decimal(
                str(
                    await PlatformConfig.get(
                        KEY_COST_DAILY_BUDGET, defaults["daily_budget_usd"]
                    )
                )
            ),
            "alert_threshold_pct": Decimal(
                str(
                    await PlatformConfig.get(
                        KEY_COST_ALERT_PCT, defaults["alert_threshold_pct"]
                    )
                )
            ),
            "bounty_ratio_max": Decimal(
                str(
                    await PlatformConfig.get(
                        KEY_COST_BOUNTY_RATIO, defaults["bounty_ratio_max"]
                    )
                )
            ),
        }
    except Exception as e:
        logger.warning("Failed to read cost controls: %s -- using defaults", e)
        return defaults


async def get_escalation_settings() -> Dict[str, Any]:
    """Read L2 escalation settings."""
    defaults = {
        "timeout_hours": 24,
        "min_human_trust_tier": "high",
    }
    try:
        from config.platform_config import PlatformConfig

        return {
            "timeout_hours": int(
                await PlatformConfig.get(
                    KEY_ESCALATION_TIMEOUT_HOURS, defaults["timeout_hours"]
                )
            ),
            "min_human_trust_tier": str(
                await PlatformConfig.get(
                    KEY_ESCALATION_MIN_TRUST, defaults["min_human_trust_tier"]
                )
            ),
        }
    except Exception as e:
        logger.warning("Failed to read escalation settings: %s -- using defaults", e)
        return defaults


async def get_preferred_providers() -> Dict[str, Optional[str]]:
    """Read preferred Ring 2 LLM providers (for tier MAX provider diversity)."""
    defaults = {
        "ring2_a": "anthropic",
        "ring2_b": "openai",
    }
    try:
        from config.platform_config import PlatformConfig

        return {
            "ring2_a": await PlatformConfig.get(
                KEY_PROVIDER_RING2_A, defaults["ring2_a"]
            ),
            "ring2_b": await PlatformConfig.get(
                KEY_PROVIDER_RING2_B, defaults["ring2_b"]
            ),
        }
    except Exception as e:
        logger.warning("Failed to read provider preferences: %s -- using defaults", e)
        return defaults


async def resolve_arbiter_mode(requested_mode: str) -> str:
    """Apply master switch + fallback logic to a requested arbiter_mode.

    Rules:
    - If master switch is OFF, force 'manual' regardless of request
    - If requested mode is 'auto' but Ring 2 LLM not yet wired (Phase 1),
      degrade to 'hybrid' with a log warning
    - Otherwise pass through unchanged

    Use this in Phase 2 when reading task.arbiter_mode at evaluation time.
    """
    if not await is_arbiter_enabled():
        if requested_mode != "manual":
            logger.info(
                "Arbiter master switch OFF -- ignoring requested mode '%s', forcing manual",
                requested_mode,
            )
        return "manual"
    return requested_mode
