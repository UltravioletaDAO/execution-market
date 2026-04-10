"""
World ID enforcement for task applications.

Shared utility used by both REST API and MCP tools to enforce
World ID Orb verification on high-value task applications.
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
    """Check if a worker is eligible to apply based on World ID verification.

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
    # Check if World ID enforcement is enabled via env var
    world_id_enabled = os.environ.get("EM_WORLD_ID_ENABLED", "true").lower() == "true"
    if not world_id_enabled:
        return True, None

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

        # Only enforce for high-value tasks
        if bounty_usd < orb_threshold:
            return True, None

        # Get DB client
        if db_client is None:
            from supabase_client import get_client

            db_client = get_client()

        # Query executor's World ID status
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
