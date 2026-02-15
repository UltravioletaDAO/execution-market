#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleanup Test Tasks — Identify and cancel E2E test tasks in production.

Finds tasks with titles matching E2E test patterns and cancels them
if they're still in a cancellable state (published, accepted).

Usage:
    python scripts/cleanup_test_tasks.py              # Dry run (list only)
    python scripts/cleanup_test_tasks.py --execute     # Actually cancel them
    python scripts/cleanup_test_tasks.py --all         # Include completed/cancelled (just list)

Environment:
    SUPABASE_URL         -- Supabase project URL
    SUPABASE_SERVICE_KEY -- Service role key (bypasses RLS)
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment
# ---------------------------------------------------------------------------
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / "mcp_server" / ".env")
load_dotenv(_project_root / ".env.local")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Patterns that identify E2E test tasks
TEST_PATTERNS = [
    "[E2E ",
    "[E2E Refund ",
    "[E2E Rejection]",
    "[E2E Golden Flow]",
    "[E2E Cancel]",
    "[TEST]",
    "e2e_golden_flow",
    "e2e_refund_flow",
    "e2e_rejection_flow",
    "e2e_mcp_api",
]


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Cleanup E2E test tasks")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually cancel tasks (default: dry run)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all test tasks including completed/cancelled",
    )
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required")
        sys.exit(1)

    try:
        from supabase import create_client
    except ImportError:
        print("ERROR: pip install supabase")
        sys.exit(1)

    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    print(f"\n{'=' * 60}")
    print("  CLEANUP TEST TASKS")
    print(f"{'=' * 60}")
    print(f"  Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")
    print(f"  Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # Query tasks with test patterns in title
    # Use ilike for case-insensitive pattern matching
    all_test_tasks = []
    for pattern in TEST_PATTERNS:
        result = (
            client.table("tasks")
            .select("id, title, status, bounty_usd, created_at, agent_id")
            .ilike("title", f"%{pattern}%")
            .order("created_at", desc=True)
            .execute()
        )
        for task in result.data or []:
            if task["id"] not in [t["id"] for t in all_test_tasks]:
                all_test_tasks.append(task)

    if not all_test_tasks:
        print("\n  No test tasks found.")
        return

    # Categorize
    cancellable = [
        t
        for t in all_test_tasks
        if t["status"] in ("published", "accepted", "in_progress")
    ]
    non_cancellable = [
        t
        for t in all_test_tasks
        if t["status"] not in ("published", "accepted", "in_progress")
    ]

    print(f"\n  Found {len(all_test_tasks)} test tasks total:")
    print(f"    Cancellable: {len(cancellable)}")
    print(f"    Already terminal: {len(non_cancellable)}")

    if cancellable:
        print(f"\n  {'─' * 56}")
        print("  CANCELLABLE TASKS:")
        print(f"  {'─' * 56}")
        for t in cancellable:
            title = t["title"][:50]
            print(f"    [{t['status']:12s}] ${t['bounty_usd']:6.2f}  {title}")
            print(f"                  ID: {t['id']}")
            print(f"                  Created: {t['created_at'][:19]}")

    if args.all and non_cancellable:
        print(f"\n  {'─' * 56}")
        print("  TERMINAL TASKS (no action needed):")
        print(f"  {'─' * 56}")
        for t in non_cancellable:
            title = t["title"][:50]
            print(f"    [{t['status']:12s}] ${t['bounty_usd']:6.2f}  {title}")

    if args.execute and cancellable:
        print(f"\n  {'─' * 56}")
        print("  CANCELLING...")
        print(f"  {'─' * 56}")
        cancelled = 0
        for t in cancellable:
            try:
                client.table("tasks").update(
                    {
                        "status": "cancelled",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).eq("id", t["id"]).execute()
                cancelled += 1
                print(f"    [OK] Cancelled: {t['id'][:8]}... ({t['title'][:40]})")
            except Exception as e:
                print(f"    [FAIL] {t['id'][:8]}...: {e}")

        print(f"\n  Cancelled {cancelled}/{len(cancellable)} tasks.")
    elif cancellable and not args.execute:
        print(f"\n  Run with --execute to cancel {len(cancellable)} tasks.")

    print()


if __name__ == "__main__":
    main()
