#!/usr/bin/env python3
"""
Populate Agent Directory — register existing task publishers as executor agents.

Queries all tasks to find unique agent publishers, then registers them in the
executors table so they appear in the Agent Directory.

Usage:
    python scripts/populate_agent_directory.py --dry-run   # Preview only
    python scripts/populate_agent_directory.py              # Execute
    python scripts/populate_agent_directory.py --api-url https://api.execution.market
"""

import argparse
import os
import sys

# Add mcp_server to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))


def main():
    parser = argparse.ArgumentParser(description="Populate agent directory from task publishers")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    parser.add_argument("--api-url", default=None, help="API URL (default: use Supabase directly)")
    args = parser.parse_args()

    # Load env
    from dotenv import load_dotenv

    env_path = os.path.join(os.path.dirname(__file__), "..", ".env.local")
    load_dotenv(env_path)

    import supabase_client as db

    client = db.get_client()

    # 1. Get all tasks with non-human publishers
    print("[1/4] Querying tasks for agent publishers...")
    result = client.table("tasks").select(
        "agent_id, agent_name, erc8004_agent_id, publisher_type"
    ).neq("publisher_type", "human").execute()

    if not result.data:
        print("No agent-published tasks found.")
        return

    # 2. Aggregate unique publishers
    publishers = {}
    for row in result.data:
        agent_id = (row.get("agent_id") or "").lower()
        if not agent_id:
            continue
        if agent_id not in publishers:
            publishers[agent_id] = {
                "wallet": agent_id,
                "agent_name": row.get("agent_name"),
                "erc8004_agent_id": row.get("erc8004_agent_id"),
                "task_count": 0,
            }
        publishers[agent_id]["task_count"] += 1
        # Keep latest non-null values
        if row.get("agent_name") and not publishers[agent_id]["agent_name"]:
            publishers[agent_id]["agent_name"] = row["agent_name"]
        if row.get("erc8004_agent_id") and not publishers[agent_id]["erc8004_agent_id"]:
            publishers[agent_id]["erc8004_agent_id"] = row["erc8004_agent_id"]

    print(f"   Found {len(publishers)} unique agent publishers")

    # 3. Check which are already registered
    print("[2/4] Checking existing executor registrations...")
    existing = client.table("executors").select(
        "wallet_address"
    ).eq("executor_type", "agent").execute()

    existing_wallets = {(r.get("wallet_address") or "").lower() for r in (existing.data or [])}
    to_register = {k: v for k, v in publishers.items() if k not in existing_wallets}

    print(f"   Already registered: {len(existing_wallets)}")
    print(f"   Need registration: {len(to_register)}")

    if not to_register:
        print("\n[OK] All publishers already registered. Nothing to do.")
        return

    # 4. Register
    print(f"\n[3/4] {'[DRY RUN] Would register' if args.dry_run else 'Registering'} {len(to_register)} agents...")
    registered = 0
    for wallet, info in to_register.items():
        display = info["agent_name"] or (
            f"Agent {wallet[:6]}...{wallet[-4:]}" if len(wallet) >= 10 else f"Agent {wallet}"
        )
        erc_id = info.get("erc8004_agent_id")

        print(f"   {'[DRY]' if args.dry_run else '[REG]'} {display} ({wallet[:10]}...) - {info['task_count']} tasks"
              + (f" - ERC-8004 #{erc_id}" if erc_id else ""))

        if not args.dry_run:
            try:
                record = {
                    "wallet_address": wallet,
                    "executor_type": "agent",
                    "display_name": display,
                }
                if erc_id:
                    record["erc8004_agent_id"] = int(erc_id)
                client.table("executors").insert(record).execute()
                registered += 1
            except Exception as e:
                print(f"   [ERROR] Failed to register {wallet}: {e}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would have registered {len(to_register)} agents.")
    else:
        print(f"\n[4/4] Registered {registered}/{len(to_register)} agents successfully.")


if __name__ == "__main__":
    main()
