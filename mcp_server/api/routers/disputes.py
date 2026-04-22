"""
Dispute Resolution Endpoints — Ring 2 L2 escalation + human arbitration.

Part of Phase 5 of the commerce scheme + arbiter integration.

The disputes table (migration 004) already has the full schema for
multi-arbitrator voting, timeline, and resolution. This router exposes
it via REST so:
  - Agents can view disputes for their tasks
  - Human arbiters can browse available disputes + submit verdicts
  - Dashboard can render the dispute inbox

Endpoints:
  GET  /api/v1/disputes             -- list disputes with filters
  GET  /api/v1/disputes/{id}        -- single dispute detail
  GET  /api/v1/disputes/available   -- disputes awaiting human arbiters
  POST /api/v1/disputes             -- create dispute (publisher-initiated)
  POST /api/v1/disputes/{id}/resolve -- submit human verdict

Auth:
  - Agents (AgentAuth) can only see/resolve disputes for their OWN tasks
  - Human arbiters need reputation_score >= 80 AND completed_tasks >= 10
    in the same category as the dispute
  - Admin override via X-Admin-Key header (for dashboard)
"""

import logging
import uuid as _uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

import supabase_client as db

from ..auth import AgentAuth, verify_agent_auth_read, verify_agent_auth_write
from ._pagination import set_pagination_headers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/disputes", tags=["Disputes"])


# ============================================================================
# Pydantic models
# ============================================================================


class DisputeSummary(BaseModel):
    """Lightweight dispute row for list endpoints."""

    id: str
    task_id: str
    submission_id: Optional[str] = None
    agent_id: str
    executor_id: Optional[str] = None
    reason: str
    description: str
    status: str
    priority: int
    escalation_tier: int
    disputed_amount_usdc: Optional[float] = None
    created_at: str
    response_deadline: Optional[str] = None
    resolved_at: Optional[str] = None
    winner: Optional[str] = None


class DisputeDetail(DisputeSummary):
    """Full dispute record, including the arbiter verdict snapshot."""

    arbiter_verdict_data: Optional[Dict[str, Any]] = None
    agent_evidence: Optional[Dict[str, Any]] = None
    executor_response: Optional[str] = None
    executor_evidence: Optional[Dict[str, Any]] = None
    agent_refund_usdc: Optional[float] = None
    executor_payout_usdc: Optional[float] = None
    resolution_notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DisputeListResponse(BaseModel):
    items: List[DisputeSummary]
    total: int


class CreateDisputeRequest(BaseModel):
    """Publisher-initiated dispute creation (INC-2026-04-22 Phase 3).

    Replaces the silent Ring 2 auto-escalation path that was removed in
    Phase 1. Publishers explicitly dispute a submission they believe is
    fraudulent or non-compliant, instead of Ring 2 making that decision
    for them.

    The new dispute is recorded with escalation_tier=1 (human-initiated,
    distinct from the deprecated escalation_tier=2 used by the pre-fix
    arbiter) and the linked submission's agent_verdict is set to
    'disputed' -- this time it's an explicit publisher decision, not a
    usurpation by the automated ring.
    """

    model_config = ConfigDict(extra="forbid")

    submission_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="UUID of the submission being disputed",
    )
    reason: str = Field(
        ...,
        pattern=(
            "^(incomplete_work|poor_quality|wrong_deliverable|late_delivery"
            "|fake_evidence|no_response|payment_issue|unfair_rejection|other)$"
        ),
        description="dispute_reason enum value (migration 004)",
    )
    description: str = Field(..., min_length=5, max_length=2000)


class ResolveDisputeRequest(BaseModel):
    """Human arbiter's verdict on an INCONCLUSIVE dispute.

    Verdict options:
      - 'release':   worker wins, full bounty released
      - 'refund':    agent wins, full bounty refunded
      - 'split':     partial release + partial refund
                     (provide split_pct = agent's refund %, 0-100)
    """

    model_config = ConfigDict(extra="forbid")

    verdict: str = Field(..., pattern="^(release|refund|split)$")
    reason: str = Field(..., min_length=5, max_length=2000)
    split_pct: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Agent refund % (required when verdict='split')",
    )


class ResolveDisputeResponse(BaseModel):
    success: bool
    dispute_id: str
    verdict: str
    agent_refund_usdc: float
    executor_payout_usdc: float
    resolved_at: str
    action_triggered: Optional[str] = None  # 'released', 'refunded', 'split', 'pending'


# ============================================================================
# Helpers
# ============================================================================


OPEN_STATUSES = {"open", "under_review", "awaiting_response", "in_arbitration"}


def _row_to_summary(row: Dict[str, Any]) -> DisputeSummary:
    return DisputeSummary(
        id=str(row.get("id")),
        task_id=str(row.get("task_id")),
        submission_id=str(row["submission_id"]) if row.get("submission_id") else None,
        agent_id=str(row.get("agent_id", "")),
        executor_id=str(row["executor_id"]) if row.get("executor_id") else None,
        reason=str(row.get("reason", "other")),
        description=str(row.get("description", "")),
        status=str(row.get("status", "open")),
        priority=int(row.get("priority", 5)),
        escalation_tier=int(row.get("escalation_tier", 2) or 2),
        disputed_amount_usdc=(
            float(row["disputed_amount_usdc"])
            if row.get("disputed_amount_usdc") is not None
            else None
        ),
        created_at=str(row.get("created_at", "")),
        response_deadline=(
            str(row["response_deadline"]) if row.get("response_deadline") else None
        ),
        resolved_at=str(row["resolved_at"]) if row.get("resolved_at") else None,
        winner=str(row["winner"]) if row.get("winner") else None,
    )


def _row_to_detail(row: Dict[str, Any]) -> DisputeDetail:
    summary = _row_to_summary(row)
    return DisputeDetail(
        **summary.model_dump(),
        arbiter_verdict_data=row.get("arbiter_verdict_data"),
        agent_evidence=row.get("agent_evidence"),
        executor_response=row.get("executor_response"),
        executor_evidence=row.get("executor_evidence"),
        agent_refund_usdc=(
            float(row["agent_refund_usdc"])
            if row.get("agent_refund_usdc") is not None
            else None
        ),
        executor_payout_usdc=(
            float(row["executor_payout_usdc"])
            if row.get("executor_payout_usdc") is not None
            else None
        ),
        resolution_notes=row.get("resolution_notes"),
        metadata=row.get("metadata"),
    )


async def _require_agent_owns_dispute(dispute: Dict[str, Any], auth: AgentAuth) -> None:
    """Check that the authenticated agent is the publisher of the task.

    Uses wallet_address comparison (cross-chain consistent) with agent_id
    fallback for pre-ERC-8128 records.
    """
    dispute_agent_id = (dispute.get("agent_id") or "").lower()
    caller_wallet = (getattr(auth, "wallet_address", "") or "").lower()
    caller_agent_id = (auth.agent_id or "").lower()

    if dispute_agent_id and dispute_agent_id not in (caller_wallet, caller_agent_id):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this dispute",
        )


async def _check_human_arbiter_eligibility(executor_id: str, category: str) -> bool:
    """Human arbiter eligibility check.

    Criteria (from MASTER_PLAN Phase 2 Task 2.3):
      - reputation_score >= 80
      - completed_tasks >= 10 (total, across categories)
      - (optional) specialty in the dispute's category

    Returns True if the executor is eligible to resolve disputes in this
    category. False otherwise.
    """
    try:
        client = db.get_client()
        result = (
            client.table("executors")
            .select("reputation_score, tasks_completed, specialties")
            .eq("id", executor_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            return False
        exec_row = result.data[0]
        score = exec_row.get("reputation_score", 0) or 0
        completed = exec_row.get("tasks_completed", 0) or 0
        specialties = exec_row.get("specialties") or []
        if score < 80:
            return False
        if completed < 10:
            return False
        # Category specialty is bonus, not mandatory
        _ = category in specialties
        return True
    except Exception as e:
        logger.warning("Failed to check arbiter eligibility for %s: %s", executor_id, e)
        return False


# ============================================================================
# Endpoints: list + detail
# ============================================================================


@router.get("", response_model=DisputeListResponse)
async def list_disputes(
    request: Request,
    response: Response,
    status: Optional[str] = Query(
        default=None,
        description="Filter by status (open, resolved_for_agent, settled, etc.)",
    ),
    task_id: Optional[str] = Query(default=None, description="Filter by task ID"),
    submission_id: Optional[str] = Query(
        default=None, description="Filter by submission ID"
    ),
    category: Optional[str] = Query(
        default=None, description="Filter by task category (via join)"
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    auth: AgentAuth = Depends(verify_agent_auth_read),
) -> DisputeListResponse:
    """List disputes visible to the authenticated agent.

    Agents see only disputes for their own tasks (auth.agent_id / wallet_address).
    Admin dashboards bypass this filter via the moderation endpoints.
    """
    try:
        client = db.get_client()
        query = client.table("disputes").select("*", count="exact")

        # Caller scope: only disputes where agent_id matches caller wallet or agent_id.
        # INC-2026-04-22: wallet addresses are stored lowercase in DB but auth may
        # return them in checksum format; normalize before the IN filter so
        # publishers actually see their own disputes.
        caller_ids: List[str] = []
        for v in (getattr(auth, "wallet_address", None), auth.agent_id):
            if not v:
                continue
            if isinstance(v, str) and v.startswith("0x"):
                caller_ids.append(v.lower())
            else:
                caller_ids.append(v)
        if caller_ids:
            # Supabase PostgREST uses .in_() for IN queries
            query = query.in_("agent_id", caller_ids)

        if status:
            query = query.eq("status", status)
        if task_id:
            query = query.eq("task_id", task_id)
        if submission_id:
            query = query.eq("submission_id", submission_id)

        # Pagination + ordering
        query = query.order("priority", desc=True).order("created_at", desc=True)
        result = query.range(offset, offset + limit - 1).execute()

        rows = result.data or []
        total = result.count or len(rows)

        # Optional category filter via in-memory pass (requires task join)
        if category:
            task_ids = list({r.get("task_id") for r in rows if r.get("task_id")})
            if task_ids:
                t_result = (
                    client.table("tasks")
                    .select("id, category")
                    .in_("id", task_ids)
                    .execute()
                )
                category_by_task = {
                    t["id"]: t.get("category") for t in (t_result.data or [])
                }
                rows = [
                    r
                    for r in rows
                    if category_by_task.get(r.get("task_id")) == category
                ]
                total = len(rows)

        set_pagination_headers(
            response, request, total=total, offset=offset, limit=limit
        )

        return DisputeListResponse(
            items=[_row_to_summary(r) for r in rows],
            total=total,
        )

    except HTTPException:
        raise
    except Exception:
        req_id = str(_uuid.uuid4())[:8]
        logger.exception("list_disputes failed [req=%s]", req_id)
        raise HTTPException(status_code=500, detail=f"Internal error (ref: {req_id})")


@router.get("/available", response_model=DisputeListResponse)
async def list_available_disputes(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    limit: int = Query(default=20, ge=1, le=100),
    auth: AgentAuth = Depends(verify_agent_auth_read),
) -> DisputeListResponse:
    """List open disputes available for human arbiters to pick up.

    Only returns disputes with status='open' that have an arbiter verdict
    (meaning they were escalated from Ring 2, not manually opened).

    Any authenticated agent can query this endpoint -- eligibility is
    enforced at /resolve time via _check_human_arbiter_eligibility.
    """
    try:
        client = db.get_client()
        query = (
            client.table("disputes")
            .select("*", count="exact")
            .in_("status", list(OPEN_STATUSES))
            .not_.is_("arbiter_verdict_data", "null")
        )
        query = query.order("priority", desc=True).order("created_at", desc=True)
        result = query.range(0, limit - 1).execute()

        rows = result.data or []

        # Optional category filter
        if category:
            task_ids = list({r.get("task_id") for r in rows if r.get("task_id")})
            if task_ids:
                t_result = (
                    client.table("tasks")
                    .select("id, category")
                    .in_("id", task_ids)
                    .execute()
                )
                category_by_task = {
                    t["id"]: t.get("category") for t in (t_result.data or [])
                }
                rows = [
                    r
                    for r in rows
                    if category_by_task.get(r.get("task_id")) == category
                ]

        return DisputeListResponse(
            items=[_row_to_summary(r) for r in rows],
            total=len(rows),
        )
    except Exception:
        req_id = str(_uuid.uuid4())[:8]
        logger.exception("list_available_disputes failed [req=%s]", req_id)
        raise HTTPException(status_code=500, detail=f"Internal error (ref: {req_id})")


@router.get("/{dispute_id}", response_model=DisputeDetail)
async def get_dispute(
    dispute_id: str,
    auth: AgentAuth = Depends(verify_agent_auth_read),
) -> DisputeDetail:
    """Get full details of a single dispute.

    Agents can only view their own task disputes.
    """
    try:
        client = db.get_client()
        result = (
            client.table("disputes").select("*").eq("id", dispute_id).limit(1).execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Dispute not found")

        row = result.data[0]
        await _require_agent_owns_dispute(row, auth)

        return _row_to_detail(row)
    except HTTPException:
        raise
    except Exception:
        req_id = str(_uuid.uuid4())[:8]
        logger.exception("get_dispute failed [req=%s]", req_id)
        raise HTTPException(status_code=500, detail=f"Internal error (ref: {req_id})")


# ============================================================================
# Endpoint: create (publisher-initiated)
# ============================================================================


@router.post("", response_model=DisputeDetail, status_code=201)
async def create_dispute(
    body: CreateDisputeRequest,
    auth: AgentAuth = Depends(verify_agent_auth_write),
) -> DisputeDetail:
    """Publisher-initiated dispute against a submission (Phase 3).

    Replaces the silent Ring 2 auto-escalation that was removed in Phase 1.
    The publisher explicitly decides a submission is fraudulent/non-compliant
    and opens a dispute -- this is a conscious action with a paper trail.

    Preconditions:
      - Caller is authenticated with ERC-8128 wallet signing
      - Submission exists
      - Caller is the publisher of the parent task (wallet or agent_id match)
      - Submission has no active dispute (no open/under_review/in_arbitration row)
      - Submission has not been paid yet (can't dispute a settled submission)

    Side effects:
      - Inserts a disputes row with escalation_tier=1 (human-initiated)
      - Sets submissions.agent_verdict='disputed' (explicit publisher decision;
        trigger trg_submissions_verdict_change writes a payment_events audit row)
      - Emits dispute.opened event
    """
    try:
        # Require ERC-8128 wallet signing -- aligns with resolve endpoint policy
        if auth.auth_method != "erc8128":
            raise HTTPException(
                status_code=403,
                detail="Dispute creation requires ERC-8128 wallet signing",
            )
        if not auth.wallet_address:
            raise HTTPException(
                status_code=403,
                detail="Wallet address required for dispute creation",
            )

        client = db.get_client()

        # 1. Fetch submission + parent task (single query via join, then unpack)
        sub_result = (
            client.table("submissions")
            .select("*, task:tasks(*)")
            .eq("id", body.submission_id)
            .limit(1)
            .execute()
        )
        if not sub_result.data:
            raise HTTPException(status_code=404, detail="Submission not found")

        submission = sub_result.data[0]
        task = submission.get("task") or {}
        task_id = submission.get("task_id") or task.get("id")
        if not task_id:
            raise HTTPException(
                status_code=500,
                detail="Submission has no linked task (data integrity error)",
            )

        # 2. Authorization: caller must be the publisher of the task
        task_agent_id = (task.get("agent_id") or "").lower()
        caller_wallet = (auth.wallet_address or "").lower()
        caller_agent_id = (auth.agent_id or "").lower()
        if not task_agent_id or task_agent_id not in (caller_wallet, caller_agent_id):
            raise HTTPException(
                status_code=403,
                detail="Only the publisher of the task can create a dispute",
            )

        # 3. Guard: submission must not be already settled/paid
        sub_status = (submission.get("status") or "").lower()
        terminal_statuses = {"paid", "released", "completed", "rated", "refunded"}
        if sub_status in terminal_statuses:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot dispute a {sub_status} submission",
            )

        # 4. Guard: no existing open dispute for this submission
        existing_result = (
            client.table("disputes")
            .select("id, status")
            .eq("submission_id", body.submission_id)
            .in_("status", list(OPEN_STATUSES))
            .limit(1)
            .execute()
        )
        if existing_result.data:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Submission already has an active dispute "
                    f"(id={existing_result.data[0].get('id')})"
                ),
            )

        # 5. Insert dispute row. escalation_tier=1 marks this as a human-
        # initiated dispute (not the deprecated Ring 2 auto-escalation path
        # which used escalation_tier=2 + metadata.source='arbiter_auto_escalation').
        now = datetime.now(timezone.utc).isoformat()
        dispute_row = {
            "task_id": task_id,
            "submission_id": body.submission_id,
            "agent_id": task.get("agent_id"),
            "executor_id": submission.get("executor_id"),
            "reason": body.reason,
            "description": body.description,
            "status": "open",
            "priority": 5,
            "escalation_tier": 1,
            "disputed_amount_usdc": float(task.get("bounty_usd", 0) or 0),
            "metadata": {
                "source": "publisher_initiated",
                "created_by": caller_wallet or caller_agent_id,
                "created_at": now,
            },
        }

        insert_result = client.table("disputes").insert(dispute_row).execute()
        if not insert_result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create dispute (empty insert result)",
            )
        created = insert_result.data[0]
        dispute_id = str(created.get("id"))

        # 6. Mark the submission as disputed -- this time it's an explicit
        # publisher decision (trigger trg_submissions_verdict_change will
        # write a verdict_change row to payment_events for the audit trail).
        try:
            client.table("submissions").update(
                {
                    "agent_verdict": "disputed",
                    "agent_notes": (
                        f"Publisher opened dispute {dispute_id} (reason={body.reason})."
                    ),
                }
            ).eq("id", body.submission_id).execute()
        except Exception as e:
            # Don't roll back the dispute -- the dispute row is the source of
            # truth. Log so we can reconcile manually.
            logger.warning(
                "Dispute %s created but submission %s update failed: %s",
                dispute_id,
                body.submission_id,
                e,
            )

        # 7. Emit event (best-effort)
        try:
            from events.bus import get_event_bus
            from events.models import EMEvent, EventSource

            await get_event_bus().publish(
                EMEvent(
                    event_type="dispute.opened",
                    task_id=task_id,
                    source=EventSource.REST_API,
                    payload={
                        "dispute_id": dispute_id,
                        "task_id": task_id,
                        "submission_id": body.submission_id,
                        "reason": body.reason,
                        "created_by": caller_wallet or caller_agent_id,
                        "escalation_tier": 1,
                    },
                )
            )
        except Exception as e:
            logger.warning("Failed to emit dispute.opened event: %s", e)

        logger.info(
            "Created publisher-initiated dispute %s for submission %s (reason=%s)",
            dispute_id,
            body.submission_id,
            body.reason,
        )

        return _row_to_detail(created)

    except HTTPException:
        raise
    except Exception:
        req_id = str(_uuid.uuid4())[:8]
        logger.exception("create_dispute failed [req=%s]", req_id)
        raise HTTPException(status_code=500, detail=f"Internal error (ref: {req_id})")


# ============================================================================
# Endpoint: resolve
# ============================================================================


@router.post("/{dispute_id}/resolve", response_model=ResolveDisputeResponse)
async def resolve_dispute(
    dispute_id: str,
    body: ResolveDisputeRequest,
    auth: AgentAuth = Depends(verify_agent_auth_write),
) -> ResolveDisputeResponse:
    """Submit a resolution verdict on a dispute.

    Who can call this:
      1. The publishing agent (can always close their own dispute)
      2. An eligible human arbiter (reputation_score >= 80,
         tasks_completed >= 10)

    Verdict options:
      - 'release' -> worker wins, trigger Facilitator /settle
      - 'refund'  -> agent wins, trigger Facilitator /refund
      - 'split'   -> partial release + partial refund (requires split_pct)

    Side effects:
      - Updates disputes row (status, winner, resolution_type='manual',
        agent_refund_usdc, executor_payout_usdc)
      - Triggers the appropriate payment flow
      - Emits dispute.resolved event
    """
    try:
        # Phase 1 GR-1.5 / API-003: Require ERC-8128 wallet signing
        if auth.auth_method != "erc8128":
            raise HTTPException(
                status_code=403,
                detail="Dispute resolution requires ERC-8128 wallet signing",
            )
        if not auth.wallet_address:
            raise HTTPException(
                status_code=403,
                detail="Wallet address required for dispute resolution",
            )

        client = db.get_client()

        # 1. Fetch dispute
        result = (
            client.table("disputes").select("*").eq("id", dispute_id).limit(1).execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Dispute not found")
        dispute = result.data[0]

        # 2. Guard: already resolved
        already_resolved = {
            "resolved_for_agent",
            "resolved_for_executor",
            "settled",
            "closed",
        }
        if dispute.get("status") in already_resolved:
            raise HTTPException(
                status_code=409,
                detail=f"Dispute already resolved (status={dispute['status']})",
            )

        # 3. Authorization check: wallet-based ownership OR eligible human arbiter
        # API-003 fix: compare wallet_address, not agent_id (which defaults to
        # "2106" for platform-owned tasks and can be impersonated).
        caller_wallet = (auth.wallet_address or "").lower()
        caller_agent_id = (auth.agent_id or "").lower()

        # Check ownership via wallet address primarily, agent_id as fallback
        # for pre-ERC-8128 records
        dispute_agent_id = (dispute.get("agent_id") or "").lower()
        is_task_owner = dispute_agent_id and dispute_agent_id in (
            caller_wallet,
            caller_agent_id,
        )

        if not is_task_owner:
            # Not the task owner -- must be an eligible human arbiter.
            # Resolve the caller's executor_id via wallet.
            exec_query = (
                client.table("executors")
                .select("id")
                .eq("wallet_address", caller_wallet)
                .limit(1)
                .execute()
            )
            if not exec_query.data:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized: not task owner and not a registered executor",
                )
            executor_id = exec_query.data[0]["id"]

            # Resolve task category for eligibility check
            task_query = (
                client.table("tasks")
                .select("category")
                .eq("id", dispute.get("task_id"))
                .limit(1)
                .execute()
            )
            category = (
                task_query.data[0].get("category", "general")
                if task_query.data
                else "general"
            )

            eligible = await _check_human_arbiter_eligibility(executor_id, category)
            if not eligible:
                raise HTTPException(
                    status_code=403,
                    detail="Not eligible: human arbiter requires reputation>=80 and 10+ completed tasks",
                )

        # 4. Compute split
        disputed_amount = float(dispute.get("disputed_amount_usdc", 0) or 0)
        if body.verdict == "release":
            agent_pct = 0.0
        elif body.verdict == "refund":
            agent_pct = 100.0
        else:  # split
            if body.split_pct is None:
                raise HTTPException(
                    status_code=400,
                    detail="split verdict requires split_pct (0-100)",
                )
            agent_pct = body.split_pct

        agent_refund = disputed_amount * (agent_pct / 100.0)
        executor_payout = disputed_amount - agent_refund

        # 5. Update dispute row
        new_status = {
            "release": "resolved_for_executor",
            "refund": "resolved_for_agent",
            "split": "settled",
        }[body.verdict]

        resolved_at = datetime.now(timezone.utc).isoformat()
        update = {
            "status": new_status,
            "resolution_type": "manual",
            "resolution_notes": body.reason[:2000],
            "winner": {
                "release": "executor",
                "refund": "agent",
                "split": "split",
            }[body.verdict],
            "agent_refund_usdc": agent_refund,
            "executor_payout_usdc": executor_payout,
            "resolved_by": caller_wallet or caller_agent_id,
            "resolved_at": resolved_at,
            "closed_at": resolved_at,
        }
        client.table("disputes").update(update).eq("id", dispute_id).execute()

        # 6. Trigger payment action (best-effort; errors are logged, not raised
        # to the caller because the dispute is already marked resolved in DB)
        action_triggered = await _trigger_resolution_payment(
            dispute=dispute,
            verdict=body.verdict,
            agent_refund=agent_refund,
            executor_payout=executor_payout,
        )

        # 7. Emit event
        try:
            from events.bus import get_event_bus
            from events.models import EMEvent, EventSource

            await get_event_bus().publish(
                EMEvent(
                    event_type="dispute.resolved",
                    task_id=dispute.get("task_id"),
                    source=EventSource.REST_API,
                    payload={
                        "dispute_id": dispute_id,
                        "task_id": dispute.get("task_id"),
                        "submission_id": dispute.get("submission_id"),
                        "verdict": body.verdict,
                        "agent_refund_usdc": agent_refund,
                        "executor_payout_usdc": executor_payout,
                        "resolved_by": caller_wallet or caller_agent_id,
                        "action_triggered": action_triggered,
                    },
                )
            )
        except Exception as e:
            logger.warning("Failed to emit dispute.resolved event: %s", e)

        return ResolveDisputeResponse(
            success=True,
            dispute_id=dispute_id,
            verdict=body.verdict,
            agent_refund_usdc=agent_refund,
            executor_payout_usdc=executor_payout,
            resolved_at=resolved_at,
            action_triggered=action_triggered,
        )

    except HTTPException:
        raise
    except Exception:
        req_id = str(_uuid.uuid4())[:8]
        logger.exception("resolve_dispute failed [req=%s]", req_id)
        raise HTTPException(status_code=500, detail=f"Internal error (ref: {req_id})")


async def _trigger_resolution_payment(
    dispute: Dict[str, Any],
    verdict: str,
    agent_refund: float,
    executor_payout: float,
) -> Optional[str]:
    """Dispatch the payment action implied by the dispute verdict.

    release -> Facilitator /settle (worker payment)
    refund  -> Facilitator /refund (agent refund)
    split   -> not yet wired (Phase 7 -- needs partial settlement support)

    Best-effort: errors logged but not raised.
    """
    task_id = dispute.get("task_id")
    submission_id = dispute.get("submission_id")
    if not task_id:
        return None

    try:
        if verdict == "release" and submission_id:
            # Fetch submission and trigger _settle_submission_payment
            client = db.get_client()
            sub_result = (
                client.table("submissions")
                .select("*, task:tasks(*), executor:executors(*)")
                .eq("id", submission_id)
                .limit(1)
                .execute()
            )
            if not sub_result.data:
                return "pending"
            submission = sub_result.data[0]

            from api.routers._helpers import _settle_submission_payment

            result = await _settle_submission_payment(
                submission_id=submission_id,
                submission=submission,
                note=f"Dispute {dispute['id']} resolved release (human arbiter)",
            )
            if result and result.get("payment_tx"):
                return "released"
            return "pending"

        elif verdict == "refund":
            from integrations.x402.payment_dispatcher import get_dispatcher

            dispatcher = get_dispatcher()
            if dispatcher:
                refund = await dispatcher.refund_trustless_escrow(
                    task_id=task_id,
                    reason=f"Dispute {dispute['id']} resolved refund (human arbiter)",
                )
                if refund and refund.get("success"):
                    return "refunded"
            return "pending"

        elif verdict == "split":
            # Partial settlement not yet supported in the current escrow
            # implementation -- Phase 7 will add this.
            logger.warning(
                "Split verdict for dispute %s: partial settlement not yet supported",
                dispute.get("id"),
            )
            return "pending"

    except Exception as e:
        logger.error(
            "Payment dispatch failed for dispute %s (verdict=%s): %s",
            dispute.get("id"),
            verdict,
            e,
        )
        return "pending"

    return "pending"
