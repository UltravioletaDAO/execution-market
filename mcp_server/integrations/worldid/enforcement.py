"""
World ID enforcement for task applications.

Shared utility used by both REST API and MCP tools to enforce
World ID Orb verification on high-value task applications.

Phase 1.5 (MASTER_PLAN_VERYAI_INTEGRATION): when EM_VERYAI_ENABLED=true,
this wrapper delegates to the multi-provider tier resolver
(integrations.verification.enforcement). When EM_VERYAI_ENABLED=false
(default), the legacy Orb-only logic runs unchanged so existing tests and
behavior are preserved byte-for-byte.
"""

import logging
import os
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


async def check_world_id_eligibility(
    executor_id: str,
    bounty_usd: Decimal,
    db_client=None,
) -> tuple[bool, Optional[dict]]:
    """Check if a worker is eligible to apply based on identity verification.

    Args:
        executor_id: The executor's UUID.
        bounty_usd: The task's bounty in USD.
        db_client: Supabase client instance. If None, imports from supabase_client.

    Returns:
        Tuple of (allowed: bool, error_detail: dict | None).
        If allowed, error_detail is None.
        If blocked, error_detail contains structured error info matching
        the REST API 403 response format.
    """
    world_id_enabled = os.environ.get("EM_WORLD_ID_ENABLED", "true").lower() == "true"
    if not world_id_enabled:
        return True, None

    veryai_enabled = os.environ.get("EM_VERYAI_ENABLED", "false").lower() == "true"

    if veryai_enabled:
        # Delegate to multi-provider tier resolver.
        from integrations.verification.enforcement import check_tier_eligibility

        allowed, err = await check_tier_eligibility(
            executor_id, bounty_usd, db_client=db_client
        )
        if not allowed and err and err.get("error") == "tier_check_failed":
            # Re-map to the legacy error code so existing clients don't break.
            err = {
                **err,
                "error": "world_id_check_failed",
                "message": (
                    "World ID verification could not be checked. "
                    "Please try again later or contact support."
                ),
            }
        return allowed, err

    # ------------------------------------------------------------------
    # Legacy Orb-only path (unchanged from pre-VeryAI behavior).
    # ------------------------------------------------------------------
    try:
        from config.platform_config import PlatformConfig

        required_for_high_value = await PlatformConfig.get(
            "feature.world_id_required_for_high_value", True
        )
        if not required_for_high_value:
            return True, None

        orb_threshold = await PlatformConfig.get(
            "worldid.min_bounty_for_orb_usd", Decimal("500.00")
        )

        if bounty_usd < orb_threshold:
            return True, None

        if db_client is None:
            from supabase_client import get_client

            db_client = get_client()

        wid_check = (
            db_client.table("executors")
            .select("world_id_verified, world_id_level")
            .eq("id", executor_id)
            .limit(1)
            .execute()
        )
        wid_data = wid_check.data[0] if wid_check.data else {}
        wid_verified = wid_data.get("world_id_verified", False)
        wid_level = wid_data.get("world_id_level")

        if not wid_verified or wid_level != "orb":
            return False, {
                "error": "world_id_orb_required",
                "message": (
                    f"Tasks with bounty >= ${orb_threshold} require "
                    "World ID Orb verification. Please verify your "
                    "identity at https://execution.market/profile."
                ),
                "verification_url": "/profile",
                "required_level": "orb",
                "current_level": wid_level,
            }

        return True, None

    except Exception as e:
        # CRY-007: Fail-CLOSED on errors — do NOT allow unverified access
        # when enforcement cannot be checked. This prevents bypassing
        # World ID gates via intentional error injection.
        logger.error(
            "World ID enforcement check failed (BLOCKING) for %s: %s",
            executor_id,
            e,
        )
        return False, {
            "error": "world_id_check_failed",
            "message": (
                "World ID verification could not be checked. "
                "Please try again later or contact support."
            ),
            "verification_url": "/profile",
        }
