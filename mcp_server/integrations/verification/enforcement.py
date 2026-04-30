"""Provider-agnostic tier enforcement.

Mirrors the CRY-007 fail-closed pattern from worldid/enforcement.py:90-105 —
any error in this path BLOCKS the worker rather than falling back to "allow".

A worker satisfies a tier iff at least one of the tier's providers is
verified on their executor record. The list of providers per tier is
configured via PlatformConfig (see verification/tiers.py).

Backward-compat: when EM_VERYAI_ENABLED is false (default), T1 enforcement
is skipped entirely so behavior matches the legacy "only enforce >= $500"
World ID flow.
"""

from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Optional

from .tiers import (
    PROVIDER_VERYAI_PALM,
    PROVIDER_WORLDID_DEVICE,
    PROVIDER_WORLDID_ORB,
    Tier,
    TierConfig,
    load_tier_config,
)

logger = logging.getLogger(__name__)


def resolve_tier_for_bounty(bounty_usd: Decimal, config: TierConfig) -> Tier:
    """Map a bounty amount to the tier that must be satisfied."""
    if bounty_usd >= config.t2_min_bounty_usd:
        return Tier.T2
    if bounty_usd >= config.t1_min_bounty_usd:
        return Tier.T1
    return Tier.T0


def _executor_satisfies_provider(executor_row: dict, provider: str) -> bool:
    """Check whether a single provider is satisfied for the executor."""
    if provider == PROVIDER_WORLDID_ORB:
        return (
            bool(executor_row.get("world_id_verified"))
            and executor_row.get("world_id_level") == "orb"
        )
    if provider == PROVIDER_WORLDID_DEVICE:
        return bool(executor_row.get("world_id_verified")) and executor_row.get(
            "world_id_level"
        ) in ("orb", "device")
    if provider == PROVIDER_VERYAI_PALM:
        return bool(executor_row.get("veryai_verified"))
    logger.warning("Unknown verification provider in tier config: %s", provider)
    return False


async def _is_tier_enforcement_active(
    tier: Tier, world_id_enabled: bool, veryai_enabled: bool
) -> bool:
    """Decide whether enforcement runs for a given tier.

    T0: never enforced.
    T1: only when both VeryAI is enabled AND the mid-value flag is on. This
        preserves legacy behavior (no enforcement < $500) when VeryAI is off.
    T2: enforced when World ID is enabled AND the high-value flag is on
        (existing PlatformConfig key — keeps the contract identical).
    """
    if tier == Tier.T0:
        return False

    from config.platform_config import PlatformConfig

    if tier == Tier.T1:
        if not veryai_enabled:
            return False
        return await PlatformConfig.get("feature.veryai_required_for_mid_value", True)

    # Tier.T2
    if not world_id_enabled:
        return False
    return await PlatformConfig.get("feature.world_id_required_for_high_value", True)


async def check_tier_eligibility(
    executor_id: str,
    bounty_usd: Decimal,
    db_client=None,
) -> tuple[bool, Optional[dict]]:
    """Check whether an executor satisfies the tier required by a bounty.

    Args:
        executor_id: The executor's UUID.
        bounty_usd: The task's bounty in USD.
        db_client: Optional Supabase client. Loaded on demand if None.

    Returns:
        (allowed, error_detail). If allowed, error_detail is None.
        On unrecoverable errors, returns (False, error) — fail-closed.
    """
    world_id_enabled = os.environ.get("EM_WORLD_ID_ENABLED", "true").lower() == "true"
    veryai_enabled = os.environ.get("EM_VERYAI_ENABLED", "false").lower() == "true"

    if not world_id_enabled and not veryai_enabled:
        return True, None

    try:
        config = await load_tier_config()
        tier = resolve_tier_for_bounty(bounty_usd, config)

        if not await _is_tier_enforcement_active(
            tier, world_id_enabled, veryai_enabled
        ):
            return True, None

        providers = config.t2_providers if tier == Tier.T2 else config.t1_providers

        active_providers = []
        for provider in providers:
            if provider in (PROVIDER_WORLDID_ORB, PROVIDER_WORLDID_DEVICE):
                if world_id_enabled:
                    active_providers.append(provider)
            elif provider == PROVIDER_VERYAI_PALM:
                if veryai_enabled:
                    active_providers.append(provider)
            else:
                active_providers.append(provider)

        if not active_providers:
            logger.error(
                "No active providers for %s on bounty $%s (executor=%s). "
                "Configured: %s. Active flags: world_id=%s veryai=%s.",
                tier.value,
                bounty_usd,
                executor_id,
                providers,
                world_id_enabled,
                veryai_enabled,
            )
            return False, _err_no_active_providers(tier, bounty_usd)

        if db_client is None:
            from supabase_client import get_client

            db_client = get_client()

        executor = (
            db_client.table("executors")
            .select("world_id_verified, world_id_level, veryai_verified, veryai_level")
            .eq("id", executor_id)
            .limit(1)
            .execute()
        )
        row = executor.data[0] if executor.data else {}

        for provider in active_providers:
            if _executor_satisfies_provider(row, provider):
                return True, None

        return False, _err_tier_required(tier, bounty_usd, active_providers, row)

    except Exception as e:
        logger.error(
            "Tier enforcement check failed (BLOCKING) for %s @ $%s: %s",
            executor_id,
            bounty_usd,
            e,
        )
        return False, {
            "error": "tier_check_failed",
            "message": (
                "Verification status could not be checked. "
                "Please try again later or contact support."
            ),
            "verification_url": "/profile",
        }


def _err_tier_required(
    tier: Tier,
    bounty_usd: Decimal,
    providers: list[str],
    row: dict,
) -> dict:
    """Build a structured 403-style error explaining what's missing."""
    if tier == Tier.T2:
        return {
            "error": "world_id_orb_required",
            "message": (
                f"Tasks with bounty >= ${bounty_usd} require "
                "World ID Orb verification. Please verify your "
                "identity at https://execution.market/profile."
            ),
            "verification_url": "/profile",
            "required_tier": tier.value,
            "required_providers": providers,
            "required_level": "orb",
            "current_level": row.get("world_id_level"),
            "current_world_id_level": row.get("world_id_level"),
            "current_veryai_level": row.get("veryai_level"),
        }

    return {
        "error": "veryai_or_orb_required",
        "message": (
            f"Tasks with bounty in the ${bounty_usd} band require either "
            "VeryAI palm verification or World ID Orb. "
            "Please verify your identity at https://execution.market/profile."
        ),
        "verification_url": "/profile",
        "required_tier": tier.value,
        "required_providers": providers,
        "current_world_id_level": row.get("world_id_level"),
        "current_veryai_level": row.get("veryai_level"),
    }


def _err_no_active_providers(tier: Tier, bounty_usd: Decimal) -> dict:
    """Failure when no provider for the tier is enabled in env."""
    return {
        "error": "no_active_providers",
        "message": (
            f"No verification provider for tier {tier.value} "
            f"(bounty ${bounty_usd}) is currently enabled. "
            "Please contact support."
        ),
        "verification_url": "/profile",
        "required_tier": tier.value,
    }
