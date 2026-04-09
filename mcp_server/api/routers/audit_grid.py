"""
Audit Grid API — lifecycle checkpoint visibility for every task.

Provides a single endpoint that returns tasks with their full checkpoint
status, completion percentage, and grouping metadata for dashboard grids.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query, Depends

from ..auth import verify_agent_auth_read, AgentAuth

import supabase_client as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Audit"])

# Checkpoint groups for the grouped + expandable UI
CHECKPOINT_GROUPS = {
    "auth": ["auth_erc8128", "identity_erc8004"],
    "payment": [
        "balance_sufficient",
        "payment_auth_signed",
        "escrow_locked",
        "payment_released",
    ],
    "execution": [
        "task_created",
        "worker_assigned",
        "evidence_submitted",
        "ai_verified",
        "approved",
    ],
    "reputation": ["agent_rated_worker", "worker_rated_agent"],
}

# Which checkpoints are expected per terminal state
EXPECTED_CHECKPOINTS = {
    "completed": [
        "auth_erc8128",
        "identity_erc8004",
        "balance_sufficient",
        "payment_auth_signed",
        "task_created",
        "escrow_locked",
        "worker_assigned",
        "evidence_submitted",
        "ai_verified",
        "approved",
        "payment_released",
        "agent_rated_worker",
        "worker_rated_agent",
        "fees_distributed",
    ],
    "cancelled": ["task_created", "cancelled"],
    "expired": ["task_created", "expired"],
}

# Default expectation for non-terminal states
DEFAULT_EXPECTED = [
    "auth_erc8128",
    "identity_erc8004",
    "balance_sufficient",
    "task_created",
]


def _compute_completion_pct(checkpoint: Dict[str, Any], task_status: str) -> int:
    """Compute completion percentage based on expected vs achieved checkpoints."""
    expected = EXPECTED_CHECKPOINTS.get(task_status, DEFAULT_EXPECTED)
    if not expected:
        return 0
    achieved = sum(1 for key in expected if checkpoint.get(key, False))
    return round((achieved / len(expected)) * 100)


def _build_checkpoint_response(
    checkpoint: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a structured checkpoint response with group metadata."""
    if not checkpoint:
        return {
            group: {"done": 0, "total": len(keys), "items": {}}
            for group, keys in CHECKPOINT_GROUPS.items()
        }

    result = {}
    for group, keys in CHECKPOINT_GROUPS.items():
        items = {}
        done_count = 0
        for key in keys:
            is_done = bool(checkpoint.get(key, False))
            if is_done:
                done_count += 1
            item: Dict[str, Any] = {"done": is_done}
            # Add timestamp if available
            at_key = f"{key}_at"
            if checkpoint.get(at_key):
                item["at"] = checkpoint[at_key]
            # Add extra metadata per checkpoint type
            if key == "identity_erc8004" and checkpoint.get("agent_id_resolved"):
                item["agent_id"] = checkpoint["agent_id_resolved"]
            elif key == "balance_sufficient" and checkpoint.get("balance_amount_usdc"):
                item["amount"] = float(checkpoint["balance_amount_usdc"])
            elif key == "escrow_locked" and checkpoint.get("escrow_tx"):
                item["tx"] = checkpoint["escrow_tx"]
            elif key == "payment_released":
                if checkpoint.get("payment_tx"):
                    item["tx"] = checkpoint["payment_tx"]
                if checkpoint.get("worker_amount_usdc"):
                    item["worker_amount"] = float(checkpoint["worker_amount_usdc"])
                if checkpoint.get("fee_amount_usdc"):
                    item["fee_amount"] = float(checkpoint["fee_amount_usdc"])
            elif key == "worker_assigned" and checkpoint.get("worker_id"):
                item["worker_id"] = checkpoint["worker_id"]
            elif key == "evidence_submitted" and checkpoint.get("evidence_count"):
                item["count"] = checkpoint["evidence_count"]
            elif key == "ai_verified" and checkpoint.get("ai_verdict"):
                item["verdict"] = checkpoint["ai_verdict"]
            items[key] = item
        result[group] = {"done": done_count, "total": len(keys), "items": items}

    # Add terminal states as flat fields
    for terminal in ("cancelled", "refunded", "expired", "fees_distributed"):
        result[terminal] = {
            "done": bool(checkpoint.get(terminal, False)),
        }
        at_key = f"{terminal}_at"
        if checkpoint.get(at_key):
            result[terminal]["at"] = checkpoint[at_key]
        tx_keys = {"refunded": "refund_tx", "fees_distributed": "fees_tx"}
        if terminal in tx_keys and checkpoint.get(tx_keys[terminal]):
            result[terminal]["tx"] = checkpoint[tx_keys[terminal]]

    return result


@router.get(
    "/tasks/audit-grid",
    summary="Task Lifecycle Audit Grid",
    description=(
        "Returns paginated tasks with their full lifecycle checkpoint status. "
        "Each task includes grouped checkpoints (auth, payment, execution, reputation) "
        "and a completion percentage."
    ),
    tags=["Audit", "Tasks"],
)
async def get_audit_grid(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Tasks per page"),
    status: Optional[str] = Query(None, description="Filter by task status"),
    network: Optional[str] = Query(None, description="Filter by payment network"),
    skill_version: Optional[str] = Query(None, description="Filter by skill version"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    has_issue: Optional[bool] = Query(
        None,
        description="Show only tasks with completion < 100% on terminal states",
    ),
    sort_by: str = Query(
        "created_at",
        description="Sort field",
        pattern="^(created_at|completion_pct|bounty_usd)$",
    ),
    sort_dir: str = Query("desc", description="Sort direction", pattern="^(asc|desc)$"),
    auth: AgentAuth = Depends(verify_agent_auth_read),
):
    """Get the task lifecycle audit grid."""
    try:
        client = db.get_client()
        offset = (page - 1) * limit

        # Query tasks
        query = client.table("tasks").select(
            "id, title, status, agent_id, bounty_usd, created_at, "
            "payment_network, payment_token, skill_version, erc8004_agent_id, "
            "executor_id, escrow_tx",
            count="exact",
        )

        if status:
            query = query.eq("status", status)
        if network:
            query = query.eq("payment_network", network)
        if skill_version:
            query = query.eq("skill_version", skill_version)
        if agent_id:
            query = query.eq("agent_id", agent_id)

        if sort_dir == "desc":
            query = query.order(sort_by, desc=True)
        else:
            query = query.order(sort_by)

        query = query.range(offset, offset + limit - 1)
        result = query.execute()

        tasks = result.data or []
        total = result.count or 0

        if not tasks:
            return {
                "tasks": [],
                "total": total,
                "page": page,
                "limit": limit,
            }

        # Batch fetch checkpoints
        task_ids = [t["id"] for t in tasks]
        from audit.checkpoint_updater import get_checkpoints_batch

        checkpoints = await get_checkpoints_batch(task_ids)

        # Build response
        grid_tasks = []
        for task in tasks:
            checkpoint = checkpoints.get(task["id"])
            task_status = task.get("status", "unknown")
            completion = (
                _compute_completion_pct(checkpoint, task_status) if checkpoint else 0
            )

            # Filter by has_issue
            if has_issue is not None:
                is_terminal = task_status in ("completed", "cancelled", "expired")
                if has_issue and (not is_terminal or completion >= 100):
                    continue
                if not has_issue and is_terminal and completion < 100:
                    continue

            grid_tasks.append(
                {
                    "task_id": task["id"],
                    "title": task.get("title", ""),
                    "status": task_status,
                    "skill_version": task.get("skill_version"),
                    "network": task.get("payment_network", "base"),
                    "token": task.get("payment_token", "USDC"),
                    "bounty_usdc": float(task.get("bounty_usd", 0)),
                    "agent_id": task.get("agent_id", ""),
                    "erc8004_agent_id": task.get("erc8004_agent_id"),
                    "created_at": task.get("created_at"),
                    "checkpoints": _build_checkpoint_response(checkpoint),
                    "completion_pct": completion,
                }
            )

        return {
            "tasks": grid_tasks,
            "total": total,
            "page": page,
            "limit": limit,
        }

    except Exception as e:
        logger.error("Audit grid query failed: %s", e, exc_info=True)
        return {"tasks": [], "total": 0, "page": page, "limit": limit, "error": str(e)}
