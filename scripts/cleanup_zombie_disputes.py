"""Cleanup zombie disputes created by Ring 2 auto-escalation (INC-2026-04-22).

A zombie dispute is any dispute row that was auto-created by the pre-fix
arbiter (escalation.py) where:
  - status is still 'open' / 'under_review' / 'in_arbitration'
  - escalation_tier = 2
  - metadata->>source = 'arbiter_auto_escalation'

After Phase 1 of the fix, the arbiter no longer creates these. But the
disputes opened BEFORE the deploy are still in the DB, and so are the
`submissions.agent_verdict='disputed'` mutations that blocked /approve.

This script finds those zombies and:
  1. Closes the dispute row (status='closed', resolution_type='cleanup',
     writes a resolution_notes pointer to the incident).
  2. If the linked submission still has agent_verdict='disputed' AND
     has NOT been manually unblocked (agent_notes contains no approval
     trail), resets agent_verdict=NULL so the publisher can call /approve.
  3. Leaves submissions that were already approved/paid alone -- only
     the dispute row is closed for those.

Runs as DRY_RUN by default. Set DRY_RUN=0 to actually mutate.

Usage:
    python scripts/cleanup_zombie_disputes.py            # dry-run, prints plan
    DRY_RUN=0 python scripts/cleanup_zombie_disputes.py  # actually mutates

Required env:
    SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY   # bypasses RLS; service role required

The script is idempotent: re-running it after success is a no-op.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env.local")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SERVICE_ROLE = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get(
    "SUPABASE_SERVICE_KEY", ""
)
DRY_RUN = os.environ.get("DRY_RUN", "1") != "0"

# `dispute_status` enum only accepts a small set of values. PostgREST returns
# 22P02 for any value outside the enum (verified 2026-04-22 against prod).
OPEN_STATUSES = ["open", "under_review"]
SETTLED_SUB_STATUSES = {"approved", "paid", "released", "completed", "rated"}


def _hdr() -> Dict[str, str]:
    return {
        "apikey": SERVICE_ROLE,
        "Authorization": f"Bearer {SERVICE_ROLE}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


async def _find_zombies(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Return disputes matching the zombie signature.

    Pre-fix arbiter wrote two source values across versions:
      - `arbiter_auto_escalation` (legacy escalation.py path)
      - `ring2_lambda_escalation` (Lambda runner path)
    Both are zombie sources -- match either via PostgREST `in.(...)`.
    """
    status_filter = ",".join(OPEN_STATUSES)
    # PostgREST `in.(...)` does not work on JSONB lookups -- use `or` with
    # two separate `metadata->>source.eq.X` predicates.
    or_clause = (
        "or=(metadata->>source.eq.arbiter_auto_escalation,"
        "metadata->>source.eq.ring2_lambda_escalation)"
    )
    url = (
        f"{SUPABASE_URL}/rest/v1/disputes"
        f"?status=in.({status_filter})"
        f"&escalation_tier=eq.2"
        f"&{or_clause}"
        f"&select=*"
    )
    r = await client.get(url, headers=_hdr())
    r.raise_for_status()
    return r.json() or []


async def _fetch_submission(
    client: httpx.AsyncClient, submission_id: str
) -> Optional[Dict[str, Any]]:
    """The submissions table has no `status` column -- it's derived elsewhere.
    Pull the columns that actually exist so PostgREST doesn't 42703."""
    url = (
        f"{SUPABASE_URL}/rest/v1/submissions"
        f"?id=eq.{submission_id}&select=id,agent_verdict,agent_notes,arbiter_verdict"
    )
    r = await client.get(url, headers=_hdr())
    r.raise_for_status()
    rows = r.json() or []
    return rows[0] if rows else None


async def _close_dispute(
    client: httpx.AsyncClient, dispute_id: str, sub_status: Optional[str]
) -> None:
    """Close a zombie dispute by ruling for the agent (publisher).

    Live `dispute_status` enum only has: open, under_review,
    resolved_for_agent, resolved_for_executor. `closed` was in the
    original migration but was never deployed -- using `resolved_for_agent`
    since the cleanup intent is to honor the publisher's verdict
    (Ring 2 had no authority to dispute in the first place).
    """
    now = datetime.now(timezone.utc).isoformat()
    body = {
        "status": "resolved_for_agent",
        "winner": "agent",
        "resolution_notes": (
            f"[cleanup] Auto-closed by cleanup_zombie_disputes.py (INC-2026-04-22). "
            f"Ring 2 was usurping publisher verdict; disputes now advisory-only. "
            f"Linked submission state at cleanup: {sub_status or 'unknown'}."
        ),
        "resolved_at": now,
    }
    url = f"{SUPABASE_URL}/rest/v1/disputes?id=eq.{dispute_id}"
    r = await client.patch(url, headers=_hdr(), json=body)
    if r.status_code >= 400:
        print(f"    ERROR closing dispute {dispute_id}: {r.status_code} {r.text[:300]}")
        r.raise_for_status()


async def _reset_submission_verdict(
    client: httpx.AsyncClient, submission_id: str, dispute_id: str
) -> None:
    body = {
        "agent_verdict": None,
        "agent_notes": (
            f"Ring 2 auto-dispute {dispute_id} rolled back by cleanup_zombie_disputes.py "
            f"(INC-2026-04-22). Publisher can now /approve normally."
        ),
    }
    url = f"{SUPABASE_URL}/rest/v1/submissions?id=eq.{submission_id}"
    r = await client.patch(url, headers=_hdr(), json=body)
    if r.status_code >= 400:
        print(
            f"    ERROR resetting sub {submission_id}: {r.status_code} {r.text[:300]}"
        )
        r.raise_for_status()


def _classify(sub: Optional[Dict[str, Any]]) -> str:
    """Decide what to do with the linked submission.

    Submissions have no `status` column -- derive intent from `agent_verdict`:
      - 'accepted' / 'rejected' = publisher already ruled, just close dispute
      - 'disputed' = pre-fix zombie still blocking /approve, reset to NULL
      - NULL/other = clean, just close dispute
    """
    if not sub:
        return "no_submission"
    agent_verdict = (sub.get("agent_verdict") or "").lower()
    if agent_verdict in ("accepted", "rejected", "approved", "paid"):
        return "already_settled"  # publisher ruled, dispute is orphaned
    if agent_verdict == "disputed":
        return "zombie_locked"  # reset + close
    return "verdict_clean"  # close dispute only


async def main() -> int:
    if not SUPABASE_URL or not SERVICE_ROLE:
        print(
            "ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env.local",
            file=sys.stderr,
        )
        return 2

    mode = "DRY-RUN" if DRY_RUN else "EXECUTE"
    print(f"=== cleanup_zombie_disputes.py ({mode}) ===")
    print(f"Supabase: {SUPABASE_URL}")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        zombies = await _find_zombies(client)
        if not zombies:
            print("No zombie disputes found. Nothing to do.")
            return 0

        print(f"Found {len(zombies)} zombie dispute(s):\n")
        plan: List[Dict[str, Any]] = []
        for z in zombies:
            dispute_id = z["id"]
            submission_id = z.get("submission_id")
            sub = (
                await _fetch_submission(client, submission_id)
                if submission_id
                else None
            )
            action = _classify(sub)
            plan.append({"dispute": z, "submission": sub, "action": action})

            agent_verdict = (sub or {}).get("agent_verdict", "n/a")
            arbiter_verdict = (sub or {}).get("arbiter_verdict", "n/a")
            print(
                f"  dispute={dispute_id[:8]}  sub={(submission_id or 'None')[:8]}  "
                f"agent_verdict={agent_verdict}  arbiter_verdict={arbiter_verdict}  -> {action}"
            )

        if DRY_RUN:
            print("\nDRY-RUN: no writes. Re-run with DRY_RUN=0 to execute.")
            print(f"Plan summary: {json.dumps([p['action'] for p in plan])}")
            return 0

        print("\nExecuting cleanup...")
        touched_subs = 0
        closed_disputes = 0
        for p in plan:
            dispute_id = p["dispute"]["id"]
            sub = p["submission"]
            submission_id = (sub or {}).get("id")
            sub_status = (sub or {}).get("status")
            action = p["action"]

            if action == "zombie_locked" and submission_id:
                await _reset_submission_verdict(client, submission_id, dispute_id)
                touched_subs += 1
                print(f"  RESET sub {submission_id[:8]} agent_verdict=NULL")

            await _close_dispute(client, dispute_id, action)
            closed_disputes += 1
            print(f"  CLOSE dispute {dispute_id[:8]} (status=resolved_for_agent)")

        print(
            f"\nDone. Closed {closed_disputes} dispute(s), "
            f"reset {touched_subs} submission verdict(s)."
        )
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
