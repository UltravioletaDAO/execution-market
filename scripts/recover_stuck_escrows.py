"""
Recover Stuck Escrow Funds from Test Tasks

Queries Supabase for active escrows without release/refund, checks their
authorizationExpiry timestamps, and attempts recovery via the cancel API.

Usage:
  cd mcp_server
  python ../scripts/recover_stuck_escrows.py [--dry-run] [--task-id TASK_ID]

Requires: SUPABASE_URL, SUPABASE_ANON_KEY (or SUPABASE_SERVICE_ROLE_KEY) in env or .env.local
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Load env files from project root (.env first, .env.local overrides)
project_root = Path(__file__).parent.parent
for env_name in [".env", ".env.local", "dashboard/.env.local"]:
    env_file = project_root / env_name
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and val:
                    os.environ[key] = val

try:
    from supabase import create_client
except ImportError:
    print("ERROR: pip install supabase")
    sys.exit(1)


def get_client():
    url = os.environ.get("SUPABASE_URL")
    # Prefer service role key > anon JWT > VITE_SUPABASE_ANON_KEY
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key or not key.startswith("eyJ"):
        anon = os.environ.get("SUPABASE_ANON_KEY", "")
        if anon.startswith("eyJ"):
            key = anon
        else:
            # .env.local may have sb_pub* management token; dashboard .env has the real JWT
            vite_key = os.environ.get("VITE_SUPABASE_ANON_KEY", "")
            key = vite_key if vite_key.startswith("eyJ") else None
    if not url or not key:
        print("ERROR: No valid Supabase JWT key found in .env or .env.local")
        sys.exit(1)
    return create_client(url, key)


def find_stuck_escrows(client, task_id=None):
    """Find escrows that are active but have no release or refund TX."""
    query = (
        client.table("escrows")
        .select(
            "id, task_id, amount_usdc, status, deposit_tx, release_tx, refund_tx, metadata, created_at"
        )
        .eq("status", "active")
        .is_("release_tx", "null")
        .is_("refund_tx", "null")
    )

    if task_id:
        query = query.eq("task_id", task_id)

    result = query.order("created_at", desc=True).limit(20).execute()
    return result.data or []


def get_task_info(client, task_id):
    """Get task title and status."""
    result = (
        client.table("tasks")
        .select("id, title, status, bounty_usd, deadline, agent_id")
        .eq("id", task_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def main():
    parser = argparse.ArgumentParser(description="Recover stuck escrow funds")
    parser.add_argument("--dry-run", action="store_true", help="Only show, don't act")
    parser.add_argument("--task-id", help="Filter by specific task ID (prefix match)")
    args = parser.parse_args()

    client = get_client()
    now = int(time.time())

    print("=" * 70)
    print("STUCK ESCROW RECOVERY TOOL")
    print("=" * 70)
    print()

    escrows = find_stuck_escrows(client, task_id=args.task_id)

    if not escrows:
        print("No stuck escrows found.")
        return

    print(f"Found {len(escrows)} stuck escrow(s):\n")

    for esc in escrows:
        task_id = esc.get("task_id", "?")
        task = get_task_info(client, task_id)
        metadata = esc.get("metadata") or {}

        # Extract payment_info for expiry check
        payment_info = metadata.get("payment_info", {})
        if isinstance(payment_info, str):
            try:
                payment_info = json.loads(payment_info)
            except Exception:
                payment_info = {}

        auth_expiry = payment_info.get("authorizationExpiry", 0)
        refund_expiry = payment_info.get("refundExpiry", 0)
        payer = payment_info.get("payer", "unknown")

        # Check if expired
        auth_expired = now > auth_expiry if auth_expiry else "unknown"
        refund_expired = now > refund_expiry if refund_expiry else "unknown"

        print(f"  Task: {task_id[:8]}...")
        print(f"  Title: {task.get('title', '?') if task else '?'}")
        print(f"  Status: {task.get('status', '?') if task else '?'}")
        print(f"  Amount: ${esc.get('amount_usdc', '?')}")
        print(f"  Payer: {payer}")
        print(f"  Deposit TX: {esc.get('deposit_tx', 'none')}")
        print(f"  Created: {esc.get('created_at', '?')}")
        print(f"  Auth Expiry: {auth_expiry} (expired: {auth_expired})")
        print(f"  Refund Expiry: {refund_expiry} (expired: {refund_expired})")

        # Determine recovery method
        has_deposit = esc.get("deposit_tx") and esc["deposit_tx"].startswith("0x")

        if not has_deposit:
            print(f"  --> Recovery: DB-only cancel (no on-chain lock)")
            method = "db_cancel"
        elif auth_expired is True:
            print(f"  --> Recovery: reclaim() available (auth expired)")
            method = "reclaim"
        else:
            print(f"  --> Recovery: cancel via API (Facilitator refund)")
            method = "api_cancel"

        if not args.dry_run and task:
            task_status = task.get("status", "")
            if task_status in ("published", "accepted", "in_progress"):
                if method == "db_cancel":
                    # Just update DB status
                    try:
                        client.table("tasks").update({"status": "cancelled"}).eq(
                            "id", task_id
                        ).execute()
                        client.table("escrows").update({"status": "cancelled"}).eq(
                            "id", esc["id"]
                        ).execute()
                        print(f"  --> DONE: DB status set to cancelled")
                    except Exception as e:
                        print(f"  --> ERROR: {e}")
                else:
                    print(f"  --> ACTION NEEDED: Use cancel API or cast send reclaim()")
                    print(
                        f"     curl -X POST https://api.execution.market/api/v1/tasks/{task_id}/cancel \\"
                    )
                    print(f'       -H "Content-Type: application/json" \\')
                    print(f'       -d \'{{"reason": "E2E test cleanup"}}\'')
            else:
                print(f"  --> SKIP: task already in terminal status '{task_status}'")

        print()

    if args.dry_run:
        print("(dry-run mode — no changes made)")


if __name__ == "__main__":
    main()
