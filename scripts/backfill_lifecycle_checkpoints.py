#!/usr/bin/env python3
"""
Backfill task_lifecycle_checkpoints from existing data.

Reconstructs checkpoint state from:
  - tasks table (status, timestamps, escrow fields)
  - payment_events table (all payment steps)
  - submissions table (evidence)
  - erc8004_side_effects table (reputation)

Idempotent: safe to re-run. Uses UPSERT on task_id.

Usage:
    cd mcp_server && python ../scripts/backfill_lifecycle_checkpoints.py
"""

import asyncio
import logging
import os
import sys

# Add mcp_server to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_server"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


async def backfill():
    import supabase_client as db

    client = db.get_client()

    # Fetch all tasks
    offset = 0
    batch_size = 100
    total_processed = 0

    while True:
        result = (
            client.table("tasks")
            .select(
                "id, status, agent_id, bounty_usd, created_at, "
                "published_at, assigned_at, completed_at, "
                "escrow_tx, escrow_created_at, refund_tx, "
                "payment_network, payment_token, skill_version, "
                "executor_id, erc8004_agent_id"
            )
            .order("created_at")
            .range(offset, offset + batch_size - 1)
            .execute()
        )

        tasks = result.data or []
        if not tasks:
            break

        for task in tasks:
            tid = task["id"]
            status = task.get("status", "unknown")
            checkpoint = {
                "task_id": tid,
                "task_created": True,
                "task_created_at": task.get("created_at") or task.get("published_at"),
                "network": task.get("payment_network"),
                "token": task.get("payment_token"),
                "bounty_usdc": task.get("bounty_usd"),
                "skill_version": task.get("skill_version"),
            }

            # ERC-8004 identity
            if task.get("erc8004_agent_id"):
                checkpoint["identity_erc8004"] = True
                checkpoint["agent_id_resolved"] = str(task["erc8004_agent_id"])[:20]

            # Escrow
            if task.get("escrow_tx"):
                checkpoint["escrow_locked"] = True
                checkpoint["escrow_locked_at"] = task.get("escrow_created_at")
                checkpoint["escrow_tx"] = task["escrow_tx"]

            # Assignment
            if task.get("executor_id"):
                checkpoint["worker_assigned"] = True
                checkpoint["worker_assigned_at"] = task.get("assigned_at")
                checkpoint["worker_id"] = task["executor_id"]

            # Terminal states
            if status == "completed":
                checkpoint["approved"] = True
                checkpoint["approved_at"] = task.get("completed_at")
            elif status == "cancelled":
                checkpoint["cancelled"] = True
            elif status == "expired":
                checkpoint["expired"] = True

            # Refund
            if task.get("refund_tx"):
                checkpoint["refunded"] = True
                checkpoint["refund_tx"] = task["refund_tx"]

            # Check payment_events for this task
            try:
                pe_result = (
                    client.table("payment_events")
                    .select("event_type, tx_hash, amount_usdc, created_at, status")
                    .eq("task_id", tid)
                    .eq("status", "success")
                    .execute()
                )
                for pe in pe_result.data or []:
                    et = pe["event_type"]
                    if et == "balance_check":
                        checkpoint["balance_sufficient"] = True
                        checkpoint["balance_checked_at"] = pe["created_at"]
                        if pe.get("amount_usdc"):
                            checkpoint["balance_amount_usdc"] = pe["amount_usdc"]
                    elif et in ("escrow_authorize", "store_auth"):
                        checkpoint["payment_auth_signed"] = True
                        checkpoint["payment_auth_at"] = pe["created_at"]
                    elif et in ("escrow_release", "disburse_worker", "settle_worker_direct"):
                        checkpoint["payment_released"] = True
                        checkpoint["payment_released_at"] = pe["created_at"]
                        if pe.get("tx_hash"):
                            checkpoint["payment_tx"] = pe["tx_hash"]
                        if pe.get("amount_usdc"):
                            checkpoint["worker_amount_usdc"] = pe["amount_usdc"]
                    elif et in ("disburse_fee", "settle_fee_direct", "distribute_fees"):
                        checkpoint["fees_distributed"] = True
                        checkpoint["fees_distributed_at"] = pe["created_at"]
                        if pe.get("tx_hash"):
                            checkpoint["fees_tx"] = pe["tx_hash"]
                        if pe.get("amount_usdc"):
                            checkpoint["fee_amount_usdc"] = pe["amount_usdc"]
                    elif et == "reputation_agent_rates_worker":
                        checkpoint["agent_rated_worker"] = True
                        checkpoint["agent_rated_worker_at"] = pe["created_at"]
                    elif et == "reputation_worker_rates_agent":
                        checkpoint["worker_rated_agent"] = True
                        checkpoint["worker_rated_agent_at"] = pe["created_at"]
                    elif et in ("escrow_refund", "refund"):
                        checkpoint["refunded"] = True
                        checkpoint["refunded_at"] = pe["created_at"]
                        if pe.get("tx_hash"):
                            checkpoint["refund_tx"] = pe["tx_hash"]
            except Exception as e:
                logger.warning("Could not fetch payment_events for %s: %s", tid[:8], e)

            # Check submissions for evidence
            try:
                sub_result = (
                    client.table("submissions")
                    .select("id, submitted_at, agent_verdict")
                    .eq("task_id", tid)
                    .execute()
                )
                subs = sub_result.data or []
                if subs:
                    checkpoint["evidence_submitted"] = True
                    checkpoint["evidence_submitted_at"] = subs[0].get("submitted_at")
                    checkpoint["evidence_count"] = len(subs)
                    # Check if AI verified
                    verdicts = [s.get("agent_verdict") for s in subs if s.get("agent_verdict")]
                    if verdicts:
                        checkpoint["ai_verified"] = True
                        checkpoint["ai_verdict"] = verdicts[-1]
            except Exception as e:
                logger.warning("Could not fetch submissions for %s: %s", tid[:8], e)

            # Upsert
            try:
                client.table("task_lifecycle_checkpoints").upsert(
                    checkpoint, on_conflict="task_id"
                ).execute()
            except Exception as e:
                logger.error("Failed to upsert checkpoint for %s: %s", tid[:8], e)

            total_processed += 1

        logger.info("Processed %d tasks (batch offset=%d)", total_processed, offset)
        offset += batch_size

        if len(tasks) < batch_size:
            break

    logger.info("Backfill complete: %d tasks processed", total_processed)


if __name__ == "__main__":
    asyncio.run(backfill())
