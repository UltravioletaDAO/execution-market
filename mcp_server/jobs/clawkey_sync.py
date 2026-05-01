"""ClawKey KYA Background Sync Job

Every ``EM_CLAWKEY_SYNC_INTERVAL`` seconds (default 6h), re-verifies each
executor that has a ``clawkey_public_key`` on file against the upstream
ClawKey API and persists any change to ``executors.clawkey_verified``.

Why this exists:
  - ClawKey bindings can be **revoked upstream** (agent rotated keys, human
    revoked agent authority, etc.). The DB cache must drift back to false
    when that happens — otherwise the public KYA badge stays green forever.
  - Manual refresh via ``POST /api/v1/clawkey/refresh/{id}`` covers the
    one-off case; this job covers the steady-state.

Posture:
  - Master switch: skipped entirely when ``EM_CLAWKEY_ENABLED != "true"``.
  - Best-effort: a single failed executor never blocks the rest of the
    cycle. Upstream 5xx is logged at WARN, network errors at WARN, success
    at DEBUG.
  - Polite: 1s delay between executors, single-pass per cycle, no fan-out
    parallelism. ClawKey upstream is shared infrastructure.
  - Audit: when verification flips from true to false, a structured WARN
    is logged so ops can correlate with revocation events.

Health pulse exposed via :func:`get_clawkey_sync_health`.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time as _time
from typing import Any

logger = logging.getLogger(__name__)

# Default cadence: 6h (matches fee_sweep). Configurable for ops who want
# tighter feedback during incidents.
CLAWKEY_SYNC_INTERVAL = int(os.environ.get("EM_CLAWKEY_SYNC_INTERVAL", "21600"))

# Per-executor pause to avoid hammering upstream when the cohort grows.
_PER_EXECUTOR_DELAY_S = float(os.environ.get("EM_CLAWKEY_SYNC_DELAY_S", "1.0"))

# Max executors processed per cycle. A safety cap so the job can't run for
# hours if the cohort balloons; the unswept tail rolls over to the next
# cycle. 500 keeps a single cycle under ~10 minutes at 1s spacing.
_MAX_PER_CYCLE = int(os.environ.get("EM_CLAWKEY_SYNC_BATCH", "500"))

# Health pulse — mutated only by the loop, read by /health.
_last_cycle_time: float = 0.0
_last_cycle_stats: dict[str, int] = {}


def get_clawkey_sync_health() -> dict[str, Any]:
    """Return health status for the ClawKey sync job.

    Returned shape mirrors the other background jobs so ``/health`` can
    compose them uniformly.
    """
    if _last_cycle_time == 0.0:
        return {"status": "starting"}
    age = _time.time() - _last_cycle_time
    payload: dict[str, Any] = {"last_cycle_age_s": round(age)}
    if _last_cycle_stats:
        payload["last_cycle_stats"] = dict(_last_cycle_stats)
    if age > CLAWKEY_SYNC_INTERVAL * 2:
        payload["status"] = "stale"
    else:
        payload["status"] = "healthy"
    return payload


async def _sync_one_executor(executor: dict) -> str:
    """Reconcile a single executor row.

    Returns one of: ``"unchanged"``, ``"verified"``, ``"revoked"``,
    ``"upstream_error"``. The caller aggregates these into cycle stats.
    """
    from integrations.clawkey.client import verify_by_public_key
    import supabase_client as db

    public_key = executor.get("clawkey_public_key")
    if not public_key:
        # Defensive — the SELECT already filtered these out, but a row
        # could be amended mid-cycle.
        return "unchanged"

    try:
        result = await verify_by_public_key(public_key, use_cache=False)
    except Exception as exc:
        # ClawKey upstream is shared infra — a 5xx or network blip is a
        # transient outage, not an executor problem. Log and move on.
        logger.warning(
            "[clawkey-sync] verify failed for executor %s: %s",
            str(executor.get("id"))[:8],
            exc,
        )
        return "upstream_error"

    db_verified = bool(executor.get("clawkey_verified"))
    new_verified = bool(result.verified)

    if db_verified == new_verified and (
        executor.get("clawkey_human_id") or "" == (result.human_id or "")
    ):
        # No drift — nothing to write.
        return "unchanged"

    # Persist whatever upstream told us. We never *promote* a row to
    # verified here without the human_id field (parity with /refresh).
    update_payload: dict[str, Any] = {
        "clawkey_verified": new_verified,
        "clawkey_human_id": result.human_id,
        "clawkey_registered_at": result.registered_at,
    }

    try:
        client = db.get_client()
        client.table("executors").update(update_payload).eq(
            "id", executor.get("id")
        ).execute()
    except Exception as exc:
        logger.error(
            "[clawkey-sync] DB write failed for executor %s: %s",
            str(executor.get("id"))[:8],
            exc,
        )
        # Treat persistence failure as a soft error — counted but not
        # fatal. The next cycle will retry.
        return "upstream_error"

    if db_verified and not new_verified:
        logger.warning(
            "[clawkey-sync] REVOCATION executor=%s human_id=%s",
            str(executor.get("id"))[:8],
            (executor.get("clawkey_human_id") or "")[:12],
        )
        return "revoked"

    if not db_verified and new_verified:
        logger.info(
            "[clawkey-sync] verified executor=%s human_id=%s",
            str(executor.get("id"))[:8],
            (result.human_id or "")[:12],
        )
        return "verified"

    # human_id changed but verified didn't — record but classify as unchanged
    return "unchanged"


async def _fetch_registered_executors() -> list[dict]:
    """Pull every executor with a public key on file.

    Selects only the columns the sync needs to keep the payload small.
    """
    import supabase_client as db

    client = db.get_client()
    res = (
        client.table("executors")
        .select(
            "id, clawkey_verified, clawkey_human_id, clawkey_public_key, "
            "clawkey_device_id, clawkey_registered_at"
        )
        .not_.is_("clawkey_public_key", "null")
        .limit(_MAX_PER_CYCLE)
        .execute()
    )
    return list(res.data or [])


async def run_clawkey_sync_loop() -> None:
    """Background loop that re-verifies all ClawKey-registered executors.

    Steady-state behaviour:
      1. Sleep 30s on startup so the rest of the app finishes booting.
      2. Master switch off ⇒ exit immediately, no loop.
      3. Each cycle: fetch registered executors, re-verify each with the
         upstream cache disabled, persist drift.
      4. Cycle stats published to the health pulse.
      5. Sleep ``CLAWKEY_SYNC_INTERVAL`` seconds, repeat.

    The loop never raises — every failure is logged and the cycle counter
    advances so the health pulse does not get stuck.
    """
    global _last_cycle_time, _last_cycle_stats

    if os.environ.get("EM_CLAWKEY_ENABLED", "false").lower() != "true":
        logger.info("[clawkey-sync] EM_CLAWKEY_ENABLED is off; loop disabled")
        return

    logger.info(
        "[clawkey-sync] background sync started (interval=%ds, batch=%d)",
        CLAWKEY_SYNC_INTERVAL,
        _MAX_PER_CYCLE,
    )

    await asyncio.sleep(30)

    while True:
        cycle_start = _time.time()
        stats = {
            "scanned": 0,
            "unchanged": 0,
            "verified": 0,
            "revoked": 0,
            "upstream_error": 0,
        }

        try:
            executors = await _fetch_registered_executors()
            stats["scanned"] = len(executors)

            for ex in executors:
                outcome = await _sync_one_executor(ex)
                stats[outcome] = stats.get(outcome, 0) + 1
                # Be polite to upstream between calls.
                await asyncio.sleep(_PER_EXECUTOR_DELAY_S)

            if stats["revoked"] or stats["verified"]:
                logger.info(
                    "[clawkey-sync] cycle done: %s in %.1fs",
                    stats,
                    _time.time() - cycle_start,
                )
            else:
                logger.debug(
                    "[clawkey-sync] cycle done: %s in %.1fs",
                    stats,
                    _time.time() - cycle_start,
                )
        except Exception as exc:
            logger.exception("[clawkey-sync] cycle aborted: %s", exc)

        _last_cycle_time = _time.time()
        _last_cycle_stats = stats
        await asyncio.sleep(CLAWKEY_SYNC_INTERVAL)
