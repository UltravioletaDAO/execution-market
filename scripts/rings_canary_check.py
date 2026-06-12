#!/usr/bin/env python3
"""Rings canary check — assert Ring 1/Ring 2 produced coherent results.

Phase 6 (Task 6.3) of MASTER_PLAN_RINGS_VERIFICATION_FIXES_2026-06-11
(C-39: the rings slept for 7 weeks without anyone noticing).

Run AFTER a synthetic submission (e.g. scripts/e2e_golden_flow.py) against
the same environment. Finds the newest submission created in the lookback
window and asserts:
  - ring1_status reached a terminal state: 'complete' (media evidence) or
    'skipped_no_media' (text-only). 'error' or eternal 'running' FAILS.
  - arbiter_verdict (Ring 2) is set within the timeout — unless the
    feature.arbiter_enabled master switch is off, which downgrades that
    assertion to a warning.
  - verification_events exist and are coherent with the path taken.

Environment:
    SUPABASE_URL          -- target environment's Supabase URL
    SUPABASE_SERVICE_KEY  -- service role key (or SUPABASE_SERVICE_ROLE_KEY)
    CANARY_LOOKBACK_MIN   -- how far back to look for the submission (default 30)
    CANARY_TIMEOUT_SEC    -- how long to poll for Ring 2 (default 300)

Exit codes: 0 = healthy, 1 = rings unhealthy, 2 = misconfigured.
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone

import httpx

SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY", ""
)
LOOKBACK_MIN = int(os.environ.get("CANARY_LOOKBACK_MIN", "30"))
TIMEOUT_SEC = int(os.environ.get("CANARY_TIMEOUT_SEC", "300"))

TERMINAL_OK = {"complete", "skipped_no_media"}


def _headers() -> dict:
    return {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}


def _get(path: str) -> list:
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/{path}", headers=_headers(), timeout=20.0)
    r.raise_for_status()
    return r.json()


def _arbiter_enabled() -> bool:
    try:
        rows = _get("platform_config?key=eq.feature.arbiter_enabled&select=value")
        if rows:
            raw = rows[0].get("value")
            if isinstance(raw, bool):
                return raw
            return str(raw).strip().lower() in ("true", "1", "yes")
    except Exception as exc:
        print(f"[WARN] could not read arbiter master switch: {exc}")
    return False


def _latest_submission() -> dict | None:
    since = (datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MIN)).isoformat()
    rows = _get(
        "submissions?select=id,created_at,auto_check_passed,auto_check_details,"
        "arbiter_verdict,arbiter_score"
        f"&created_at=gte.{since}&order=created_at.desc&limit=1"
    )
    return rows[0] if rows else None


def main() -> int:
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[FAIL] SUPABASE_URL / SUPABASE_SERVICE_KEY not configured")
        return 2

    sub = _latest_submission()
    if not sub:
        print(
            f"[FAIL] no submission found in the last {LOOKBACK_MIN} min — "
            "did the synthetic submission step run?"
        )
        return 1

    sid = sub["id"]
    print(f"[INFO] canary submission: {sid} (created {sub['created_at']})")

    arbiter_on = _arbiter_enabled()
    if not arbiter_on:
        print(
            "[WARN] feature.arbiter_enabled is OFF — Ring 2 verdict "
            "assertion downgraded to warning (see Task 2.3)"
        )

    deadline = time.monotonic() + TIMEOUT_SEC
    ring1_status = None
    verdict = None
    details: dict = {}

    while time.monotonic() < deadline:
        rows = _get(
            "submissions?select=auto_check_details,arbiter_verdict,arbiter_score"
            f"&id=eq.{sid}"
        )
        row = rows[0] if rows else {}
        details = row.get("auto_check_details") or {}
        ring1_status = details.get("ring1_status")
        verdict = row.get("arbiter_verdict")

        ring1_done = ring1_status in TERMINAL_OK or ring1_status == "error"
        ring2_done = verdict is not None or not arbiter_on
        if ring1_done and ring2_done:
            break
        time.sleep(10)

    failures = []

    if ring1_status not in TERMINAL_OK:
        failures.append(
            f"ring1_status={ring1_status!r} (expected one of {sorted(TERMINAL_OK)})"
        )
    else:
        print(f"[OK] ring1_status={ring1_status}")

    if arbiter_on:
        if verdict is None:
            failures.append(
                f"arbiter_verdict still NULL after {TIMEOUT_SEC}s — Ring 2 silent"
            )
        elif verdict == "error":
            failures.append("arbiter_verdict='error'")
        else:
            print(f"[OK] arbiter_verdict={verdict}")
    elif verdict is not None:
        print(f"[OK] arbiter_verdict={verdict} (switch off but verdict present)")

    events = details.get("verification_events") or []
    if ring1_status == "complete" and not any(e.get("ring") == 1 for e in events):
        failures.append("ring1 complete but no ring-1 verification_events")
    if verdict is not None and not any(e.get("ring") == 2 for e in events):
        print("[WARN] arbiter verdict present but no ring-2 events recorded")
    print(f"[INFO] verification_events: {len(events)}")

    if failures:
        for f in failures:
            print(f"[FAIL] {f}")
        return 1

    print("[OK] rings canary healthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
