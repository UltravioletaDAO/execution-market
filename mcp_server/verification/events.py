"""
Verification Event Log — append-only event stream inside submissions.auto_check_details.

Each event records a step in the Ring 1 / Ring 2 verification pipeline so the
frontend can poll and show live progress.

Event structure:
    {"ts": 1712345678, "ring": 1, "step": "exif_extraction", "status": "complete", "detail": {...}}

The helper is isolated in its own module to avoid circular imports between
background_runner.py and integrations/arbiter/service.py.
"""

import asyncio
import logging
import time as _time
from typing import Optional

import supabase_client as db

logger = logging.getLogger(__name__)

# Timeout for the entire emit operation (DB read + append + DB write).
# If Supabase is slow, we give up rather than blocking the verification pipeline.
_EMIT_TIMEOUT_SECONDS = 10


async def emit_verification_event(
    submission_id: str,
    ring: int,
    step: str,
    status: str,
    detail: Optional[dict] = None,
) -> None:
    """Append a verification event to auto_check_details.verification_events.

    Uses a timeout instead of a lock — if the DB is slow, the event is dropped
    rather than blocking the entire Ring 1/Ring 2 pipeline.  Events are
    append-only so a lost event is cosmetic, not fatal.

    Never raises -- errors and timeouts are logged.

    Args:
        submission_id: The submission being verified.
        ring: 1 for Ring 1 (PHOTINT), 2 for Ring 2 (Arbiter).
        step: Machine-readable step name (e.g. ``"exif_extraction"``).
        status: ``"running"`` | ``"complete"`` | ``"failed"``.
        detail: Optional dict with step-specific summary fields.
    """
    try:
        await asyncio.wait_for(
            _emit_inner(submission_id, ring, step, status, detail),
            timeout=_EMIT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "Verification event emit timed out after %ds: ring=%d step=%s status=%s sub=%s",
            _EMIT_TIMEOUT_SECONDS,
            ring,
            step,
            status,
            submission_id[:8],
        )
    except Exception as e:
        logger.warning("Failed to emit verification event %s/%s: %s", step, status, e)


async def _emit_inner(
    submission_id: str,
    ring: int,
    step: str,
    status: str,
    detail: Optional[dict],
) -> None:
    """Inner emit — reads current events, appends, writes back."""
    current_sub = await db.get_submission(submission_id)
    current = (current_sub or {}).get("auto_check_details") or {}
    events = current.get("verification_events", [])
    events.append(
        {
            "ts": int(_time.time()),
            "ring": ring,
            "step": step,
            "status": status,
            "detail": detail or {},
        }
    )
    current["verification_events"] = events
    await db.update_submission_auto_check(
        submission_id=submission_id,
        auto_check_passed=current.get("passed", False),
        auto_check_details=current,
    )
