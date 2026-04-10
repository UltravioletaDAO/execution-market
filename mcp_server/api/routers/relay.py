"""
Relay Chain CRUD — multi-worker chained execution management.

Endpoints:
- POST   /api/v1/relay-chains              — Create relay chain from parent task
- GET    /api/v1/relay-chains/{chain_id}    — Get chain status with all legs
- POST   /api/v1/relay-chains/{chain_id}/legs/{leg_number}/assign  — Assign worker to leg
- POST   /api/v1/relay-chains/{chain_id}/legs/{leg_number}/handoff — Record handoff
"""

import logging
import secrets
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict, Field

import supabase_client as db
from ..auth import verify_agent_auth_write, AgentAuth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/relay-chains", tags=["relay"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class LegInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pickup_location: Optional[Dict[str, Any]] = None
    dropoff_location: Optional[Dict[str, Any]] = None
    bounty_usdc: float = Field(gt=0, description="Bounty for this leg in USDC")


class CreateRelayChainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(..., description="Parent task ID")
    legs: List[LegInput] = Field(..., min_length=2, description="At least 2 legs")


class AssignLegRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    worker_wallet: str = Field(..., min_length=42, max_length=42)
    worker_nick: Optional[str] = None


class HandoffRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handoff_code: str = Field(..., min_length=4, max_length=8)
    evidence: Optional[Dict[str, Any]] = None


class LegResponse(BaseModel):
    leg_id: str
    leg_number: int
    worker_wallet: Optional[str] = None
    worker_nick: Optional[str] = None
    status: str
    pickup_location: Optional[Dict[str, Any]] = None
    dropoff_location: Optional[Dict[str, Any]] = None
    bounty_usdc: float
    handoff_code: Optional[str] = None
    picked_up_at: Optional[str] = None
    handed_off_at: Optional[str] = None


class RelayChainResponse(BaseModel):
    chain_id: str
    parent_task_id: str
    status: str
    total_legs: int
    completed_legs: int
    legs: List[LegResponse] = []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=RelayChainResponse, status_code=201)
async def create_relay_chain(
    req: CreateRelayChainRequest,
    auth: AgentAuth = Depends(verify_agent_auth_write),
):
    """Create a relay chain from a parent task."""
    # Verify parent task exists and is owned by caller
    task_resp = db.client.table("tasks").select("*").eq("id", req.task_id).execute()
    if not task_resp.data:
        raise HTTPException(404, "Parent task not found")

    task = task_resp.data[0]
    if task.get("publisher_wallet") != auth.wallet_address:
        raise HTTPException(403, "Only the publisher can create relay chains")

    total_legs = len(req.legs)

    # Create chain
    chain_resp = (
        db.client.table("relay_chains")
        .insert(
            {
                "parent_task_id": req.task_id,
                "status": "pending",
                "total_legs": total_legs,
                "completed_legs": 0,
            }
        )
        .execute()
    )
    chain = chain_resp.data[0]
    chain_id = chain["chain_id"]

    # Create legs
    legs_data = []
    for i, leg in enumerate(req.legs, 1):
        legs_data.append(
            {
                "chain_id": chain_id,
                "leg_number": i,
                "pickup_location": leg.pickup_location,
                "dropoff_location": leg.dropoff_location,
                "bounty_usdc": leg.bounty_usdc,
                "status": "pending",
                "handoff_code": secrets.token_hex(4).upper(),
            }
        )

    legs_resp = db.client.table("relay_legs").insert(legs_data).execute()

    logger.info(
        "Relay chain %s created with %d legs for task %s",
        chain_id[:8],
        total_legs,
        req.task_id[:8],
    )

    return RelayChainResponse(
        chain_id=chain_id,
        parent_task_id=req.task_id,
        status="pending",
        total_legs=total_legs,
        completed_legs=0,
        legs=[
            LegResponse(
                leg_id=leg["leg_id"],
                leg_number=leg["leg_number"],
                worker_wallet=leg.get("worker_wallet"),
                worker_nick=leg.get("worker_nick"),
                status=leg["status"],
                pickup_location=leg.get("pickup_location"),
                dropoff_location=leg.get("dropoff_location"),
                bounty_usdc=float(leg["bounty_usdc"]),
                handoff_code=leg.get("handoff_code"),
            )
            for leg in legs_resp.data
        ],
    )


@router.get("/{chain_id}", response_model=RelayChainResponse)
async def get_relay_chain(chain_id: str):
    """Get relay chain status with all legs."""
    chain_resp = (
        db.client.table("relay_chains").select("*").eq("chain_id", chain_id).execute()
    )
    if not chain_resp.data:
        raise HTTPException(404, "Relay chain not found")

    chain = chain_resp.data[0]

    legs_resp = (
        db.client.table("relay_legs")
        .select("*")
        .eq("chain_id", chain_id)
        .order("leg_number")
        .execute()
    )

    return RelayChainResponse(
        chain_id=chain["chain_id"],
        parent_task_id=chain["parent_task_id"],
        status=chain["status"],
        total_legs=chain["total_legs"],
        completed_legs=chain["completed_legs"],
        legs=[
            LegResponse(
                leg_id=leg["leg_id"],
                leg_number=leg["leg_number"],
                worker_wallet=leg.get("worker_wallet"),
                worker_nick=leg.get("worker_nick"),
                status=leg["status"],
                pickup_location=leg.get("pickup_location"),
                dropoff_location=leg.get("dropoff_location"),
                bounty_usdc=float(leg["bounty_usdc"]),
                handoff_code=leg.get("handoff_code"),
                picked_up_at=leg.get("picked_up_at"),
                handed_off_at=leg.get("handed_off_at"),
            )
            for leg in legs_resp.data
        ],
    )


@router.post("/{chain_id}/legs/{leg_number}/assign")
async def assign_leg_worker(
    chain_id: str,
    leg_number: int,
    req: AssignLegRequest,
    auth: AgentAuth = Depends(verify_agent_auth_write),
):
    """Assign a worker to a relay chain leg."""
    # Verify chain exists
    chain_resp = (
        db.client.table("relay_chains").select("*").eq("chain_id", chain_id).execute()
    )
    if not chain_resp.data:
        raise HTTPException(404, "Relay chain not found")

    # Update leg
    leg_resp = (
        db.client.table("relay_legs")
        .update(
            {
                "worker_wallet": req.worker_wallet,
                "worker_nick": req.worker_nick,
                "status": "assigned",
            }
        )
        .eq("chain_id", chain_id)
        .eq("leg_number", leg_number)
        .execute()
    )

    if not leg_resp.data:
        raise HTTPException(404, f"Leg {leg_number} not found")

    # If first assignment, activate the chain
    if chain_resp.data[0]["status"] == "pending":
        db.client.table("relay_chains").update({"status": "active"}).eq(
            "chain_id", chain_id
        ).execute()

    logger.info(
        "Leg %d of chain %s assigned to %s",
        leg_number,
        chain_id[:8],
        req.worker_wallet[:10],
    )

    return {"status": "assigned", "leg_number": leg_number, "chain_id": chain_id}


@router.post("/{chain_id}/legs/{leg_number}/handoff")
async def record_handoff(
    chain_id: str,
    leg_number: int,
    req: HandoffRequest,
    auth: AgentAuth = Depends(verify_agent_auth_write),
):
    """Record a handoff between relay workers. Requires matching handoff code."""
    # Get the leg
    leg_resp = (
        db.client.table("relay_legs")
        .select("*")
        .eq("chain_id", chain_id)
        .eq("leg_number", leg_number)
        .execute()
    )
    if not leg_resp.data:
        raise HTTPException(404, f"Leg {leg_number} not found")

    leg = leg_resp.data[0]

    if leg["status"] not in ("assigned", "in_transit"):
        raise HTTPException(
            400, f"Leg {leg_number} is not in progress (status: {leg['status']})"
        )

    # Verify handoff code
    if (
        leg.get("handoff_code")
        and req.handoff_code.upper() != leg["handoff_code"].upper()
    ):
        raise HTTPException(403, "Invalid handoff code")

    # Update leg as handed off
    from datetime import datetime, timezone

    db.client.table("relay_legs").update(
        {
            "status": "handed_off",
            "handed_off_at": datetime.now(timezone.utc).isoformat(),
            "evidence": req.evidence or {},
        }
    ).eq("leg_id", leg["leg_id"]).execute()

    # Update chain progress
    chain_resp = (
        db.client.table("relay_chains").select("*").eq("chain_id", chain_id).execute()
    )
    chain = chain_resp.data[0]
    new_completed = chain["completed_legs"] + 1
    chain_status = "completed" if new_completed >= chain["total_legs"] else "active"

    db.client.table("relay_chains").update(
        {"completed_legs": new_completed, "status": chain_status}
    ).eq("chain_id", chain_id).execute()

    logger.info(
        "Handoff for leg %d of chain %s (%d/%d complete)",
        leg_number,
        chain_id[:8],
        new_completed,
        chain["total_legs"],
    )

    return {
        "status": "handed_off",
        "leg_number": leg_number,
        "chain_id": chain_id,
        "completed_legs": new_completed,
        "total_legs": chain["total_legs"],
        "chain_status": chain_status,
    }
