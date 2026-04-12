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

_events_lock = asyncio.Lock()


async def emit_verification_event(
    submission_id: str,
    ring: int,
    step: str,
    status: str,
    detail: Optional[dict] = None,
) -> None:
    """Append a verification event to auto_check_details.verification_events.

    Thread-safe via asyncio.Lock.  Never raises -- errors are logged.

    Args:
        submission_id: The submission being verified.
        ring: 1 for Ring 1 (PHOTINT), 2 for Ring 2 (Arbiter).
        step: Machine-readable step name (e.g. ``"exif_extraction"``).
        status: ``"running"`` | ``"complete"`` | ``"failed"``.
        detail: Optional dict with step-specific summary fields.
    """
    try:
        async with _events_lock:
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
    except Exception as e:
        logger.warning("Failed to emit verification event %s/%s: %s", step, status, e)
