"""
Phase B Orphaned Submission Recovery Job

When the ECS container restarts (deploy, crash, scaling), any in-flight
Phase B verification tasks die silently. The submission stays in "pending"
with Ring 1/Ring 2 showing "Running..." forever.

This module provides:
  - ``recover_orphaned_phase_b()``: runs ONCE at startup, re-queues
    orphaned Phase B verifications with a concurrency limit.
  - ``_shutting_down`` flag + ``graceful_shutdown_phase_b()`` for clean
    container shutdown.

Wired into ``main.py`` lifespan handler.
"""

import asyncio
import logging
import os
from typing import Set

logger = logging.getLogger(__name__)

# Maximum number of concurrent Phase B recoveries at startup to avoid
# overwhelming the container with AI inference requests.
MAX_CONCURRENT_RECOVERIES = int(os.environ.get("PHASE_B_RECOVERY_MAX_CONCURRENT", "5"))

# Submissions older than this threshold (seconds) since submitted_at are
# considered orphaned. Gives Phase B 2 minutes to complete normally before
# recovery kicks in.
ORPHAN_AGE_THRESHOLD_SECONDS = int(os.environ.get("PHASE_B_ORPHAN_AGE_SECONDS", "120"))

# ── Graceful shutdown machinery ──────────────────────────────────────────

_shutting_down: bool = False
_inflight_tasks: Set[asyncio.Task] = set()
_inflight_lock = asyncio.Lock()

# Must be less than ECS stopTimeout (120s) to leave room for SIGKILL buffer.
SHUTDOWN_GRACE_SECONDS = int(os.environ.get("PHASE_B_SHUTDOWN_GRACE_SECONDS", "110"))


def is_shutting_down() -> bool:
    """Return True if the server is in the process of shutting down."""
    return _shutting_down


def inflight_count() -> int:
    """Return the number of in-flight Phase B tasks (recovery + normal)."""
    return len(_inflight_tasks)


def track_phase_b_task(task: asyncio.Task, submission_id: str) -> None:
    """Register ANY Phase B asyncio.Task for graceful-shutdown tracking.

    Call this from the submit endpoint, the admin reprocess endpoint, or
    anywhere else that launches ``run_phase_b_verification`` as a background
    task.  The task auto-unregisters on completion via a done callback.
    """
    task._recovery_submission_id = submission_id  # type: ignore[attr-defined]
    _inflight_tasks.add(task)

    def _on_done(t: asyncio.Task) -> None:
        _inflight_tasks.discard(t)

    task.add_done_callback(_on_done)


async def _track_task(task: asyncio.Task) -> None:
    """Register a Phase B task for graceful shutdown tracking (legacy helper).

    Used by the startup recovery flow.  New callers should prefer
    :func:`track_phase_b_task` which is non-async and callback-based.
    """
    _inflight_tasks.add(task)
    try:
        await task
    finally:
        _inflight_tasks.discard(task)


async def graceful_shutdown_phase_b() -> None:
    """Wait for in-flight Phase B tasks to complete, up to SHUTDOWN_GRACE_SECONDS.

    For any tasks still running after the grace period, emit a "failed"
    verification event with reason "container shutdown" so the frontend
    does not show a spinner indefinitely.
    """
    global _shutting_down
    _shutting_down = True

    async with _inflight_lock:
        pending = set(_inflight_tasks)

    if not pending:
        logger.info("[RECOVERY] No in-flight Phase B tasks at shutdown")
        return

    logger.info(
        "[RECOVERY] Waiting up to %ds for %d in-flight Phase B task(s) to finish",
        SHUTDOWN_GRACE_SECONDS,
        len(pending),
    )

    done, still_running = await asyncio.wait(pending, timeout=SHUTDOWN_GRACE_SECONDS)

    if not still_running:
        logger.info(
            "[RECOVERY] All %d Phase B task(s) completed before shutdown",
            len(done),
        )
        return

    logger.warning(
        "[RECOVERY] %d Phase B task(s) still running after %ds grace period; "
        "emitting failure events",
        len(still_running),
        SHUTDOWN_GRACE_SECONDS,
    )

    # Emit failure events for still-running tasks.  The task name carries
    # the submission_id (set during _launch_recovery below).
    for task in still_running:
        submission_id = getattr(task, "_recovery_submission_id", None)
        if submission_id:
            try:
                from verification.events import emit_verification_event

                await emit_verification_event(
                    submission_id,
                    ring=1,
                    step="phase_b_recovery",
                    status="failed",
                    detail={"reason": "container shutdown before completion"},
                )
                logger.info(
                    "[RECOVERY] Emitted shutdown failure event for submission %s",
                    submission_id[:8],
                )
            except Exception as exc:
                logger.warning(
                    "[RECOVERY] Could not emit shutdown event for %s: %s",
                    submission_id[:8] if submission_id else "unknown",
                    exc,
                )
        task.cancel()

    # Let cancellations propagate
    for task in still_running:
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


# ── Startup recovery ─────────────────────────────────────────────────────


async def recover_orphaned_phase_b() -> None:
    """Query Supabase for orphaned Phase B submissions and re-queue them.

    Runs ONCE at server startup (called from the lifespan handler).
    Never blocks startup -- launches recoveries as background tasks
    with a semaphore to limit concurrency.

    Criteria for orphaned submissions:
      - status IN ('pending', 'submitted')
      - auto_check_details->>'phase' = 'A'  (Phase A done, Phase B never finished)
      - submitted_at < NOW() - ORPHAN_AGE_THRESHOLD_SECONDS
      - ai_verification_result IS NULL (Phase B did not produce results)
    """
    try:
        from supabase_client import get_client
        from datetime import datetime, timezone, timedelta

        client = get_client()

        cutoff = (
            datetime.now(timezone.utc) - timedelta(seconds=ORPHAN_AGE_THRESHOLD_SECONDS)
        ).isoformat()

        # Supabase PostgREST: filter on JSONB field via arrow operator
        # auto_check_details->>'phase' = 'A'
        result = (
            client.table("submissions")
            .select("id, task_id, evidence, submitted_at, auto_check_details")
            .in_("agent_verdict", ["pending", "submitted"])
            .is_("ai_verification_result", "null")
            .lt("submitted_at", cutoff)
            .execute()
        )

        candidates = result.data or []

        # Filter in Python: only those where auto_check_details.phase == 'A'
        # (PostgREST JSONB arrow filtering can be unreliable across versions)
        orphaned = []
        for row in candidates:
            details = row.get("auto_check_details") or {}
            if details.get("phase") == "A":
                orphaned.append(row)

        if not orphaned:
            logger.info("[RECOVERY] No orphaned Phase B submissions found at startup")
            return

        logger.info(
            "[RECOVERY] Found %d orphaned Phase B submission(s) to re-queue",
            len(orphaned),
        )

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_RECOVERIES)

        for row in orphaned:
            task = asyncio.create_task(_launch_recovery(row, semaphore))
            task._recovery_submission_id = row["id"]
            asyncio.create_task(_track_task(task))

    except Exception as exc:
        logger.error(
            "[RECOVERY] Failed to query orphaned submissions at startup: %s",
            exc,
            exc_info=True,
        )


async def _launch_recovery(row: dict, semaphore: asyncio.Semaphore) -> None:
    """Re-queue a single Phase B verification with concurrency limiting."""
    submission_id = row["id"]
    task_id = row["task_id"]
    sid = submission_id[:8]

    async with semaphore:
        if _shutting_down:
            logger.info("[RECOVERY] Skipping %s — server is shutting down", sid)
            return

        logger.info(
            "[RECOVERY] Re-queuing Phase B for orphaned submission %s (submitted %s)",
            sid,
            row.get("submitted_at", "unknown"),
        )

        try:
            import supabase_client as db
            from verification.background_runner import run_phase_b_verification

            # Fetch full submission and task data
            submission = await db.get_submission(submission_id)
            if not submission:
                logger.warning(
                    "[RECOVERY] Submission %s no longer exists, skipping", sid
                )
                return

            task = await db.get_task(task_id)
            if not task:
                logger.warning(
                    "[RECOVERY] Task %s for submission %s no longer exists, skipping",
                    task_id,
                    sid,
                )
                return

            # Check if Phase B already completed while we were querying
            current_details = submission.get("auto_check_details") or {}
            if current_details.get("phase") != "A":
                logger.info(
                    "[RECOVERY] Submission %s phase is now '%s', skipping recovery",
                    sid,
                    current_details.get("phase", "unknown"),
                )
                return
            if submission.get("ai_verification_result") is not None:
                logger.info(
                    "[RECOVERY] Submission %s already has ai_verification_result, "
                    "skipping recovery",
                    sid,
                )
                return

            # Emit a recovery event for the frontend
            try:
                from verification.events import emit_verification_event

                await emit_verification_event(
                    submission_id,
                    ring=1,
                    step="phase_b_recovery",
                    status="running",
                    detail={"reason": "re-queued after container restart"},
                )
            except Exception:
                pass

            await run_phase_b_verification(
                submission_id=submission_id,
                submission=submission,
                task=task,
            )

            logger.info("[RECOVERY] Phase B recovery completed for submission %s", sid)

        except Exception as exc:
            logger.error(
                "[RECOVERY] Phase B recovery failed for submission %s: %s",
                sid,
                exc,
                exc_info=True,
            )

            # Emit failure event so frontend stops spinning
            try:
                from verification.events import emit_verification_event

                await emit_verification_event(
                    submission_id,
                    ring=1,
                    step="phase_b_recovery",
                    status="failed",
                    detail={"reason": f"recovery failed: {str(exc)[:200]}"},
                )
            except Exception:
                pass
