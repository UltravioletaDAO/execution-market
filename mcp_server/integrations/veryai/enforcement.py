"""VeryAI palm enforcement (T1 tier).

Mirror of `worldid/enforcement.py` for the VeryAI provider. Returns whether
an executor satisfies the *VeryAI palm* requirement for a given bounty.

This is the provider-specific check. The composite "any T1 provider
satisfies T1" decision lives in `verification/enforcement.py`. Callers that
want to know "is VeryAI alone enough?" use this module; callers that want
"is the worker eligible by any tier provider?" use the verification module.

Same fail-closed contract as CRY-007 / `worldid/enforcement.py:90-105`:
errors BLOCK the worker, never silently allow.
"""

from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


async def check_veryai_eligibility(
    executor_id: str,
    bounty_usd: Decimal,
    db_client=None,
) -> tuple[bool, Optional[dict]]:
    """Check whether the executor has VeryAI palm verification for a bounty.

    Args:
        executor_id: Executor UUID.
        bounty_usd: Task bounty in USD.
        db_client: Optional Supabase client; loaded on demand.

    Returns:
        (allowed, error_detail). On any unrecoverable error, returns
        (False, error) — never silently allows.
    """
    veryai_enabled = os.environ.get("EM_VERYAI_ENABLED", "false").lower() == "true"
    if not veryai_enabled:
        return True, None

    try:
        from config.platform_config import PlatformConfig

        required = await PlatformConfig.get(
            "feature.veryai_required_for_mid_value", True
        )
        if not required:
            return True, None

        threshold_raw = await PlatformConfig.get(
            "veryai.min_bounty_for_palm_usd", Decimal("50.00")
        )
        threshold = Decimal(str(threshold_raw))

        if bounty_usd < threshold:
            return True, None

        if db_client is None:
            from supabase_client import get_client

            db_client = get_client()

        result = (
            db_client.table("executors")
            .select("veryai_verified, veryai_level")
            .eq("id", executor_id)
            .limit(1)
            .execute()
        )
        row = result.data[0] if result.data else {}

        if row.get("veryai_verified"):
            return True, None

        return False, {
            "error": "veryai_required",
            "message": (
                f"Tasks with bounty >= ${threshold} require VeryAI palm "
                "verification. Please verify at "
                "https://execution.market/profile."
            ),
            "verification_url": "/profile",
            "required_provider": "veryai_palm",
            "current_level": row.get("veryai_level"),
        }

    except Exception as exc:
        logger.error(
            "VeryAI enforcement check failed (BLOCKING) for executor %s: %s",
            executor_id,
            exc,
        )
        return False, {
            "error": "veryai_check_failed",
            "message": (
                "VeryAI verification could not be checked. "
                "Please try again later or contact support."
            ),
            "verification_url": "/profile",
        }
