"""
Submission approval, rejection, and more-info endpoints.

Extracted from api/routes.py.
"""

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Depends, Path, Request

import supabase_client as db

from ..auth import (
    verify_agent_auth,
    AgentAuth,
    verify_agent_owns_task,
    verify_agent_owns_submission,
)

from ._models import (
    SubmissionResponse,
    SubmissionListResponse,
    ApprovalRequest,
    RejectionRequest,
    RequestMoreInfoRequest,
    SuccessResponse,
    ErrorResponse,
)

from ._helpers import (
    logger,
    UUID_PATTERN,
    _normalize_status,
    _settle_submission_payment,
    _execute_post_approval_side_effects,
    _build_explorer_url,
    EM_PAYMENT_MODE,
)

router = APIRouter(prefix="/api/v1", tags=["Submissions"])


@router.get(
    "/tasks/{task_id}/submissions",
    response_model=SubmissionListResponse,
    responses={
        200: {
            "description": "Submissions retrieved successfully with AI pre-check scores"
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to view submissions for this task",
        },
        404: {"model": ErrorResponse, "description": "Task not found"},
    },
    summary="Get Task Submissions",
    description="Retrieve all submissions for a specific task with AI verification scores",
    tags=["Submissions", "Agent"],
)
async def get_submissions(
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    auth: AgentAuth = Depends(verify_agent_auth),
) -> SubmissionListResponse:
    """
    Get all submissions for a specific task.

    Returns all work submissions from workers for the specified task, including
    evidence data, AI pre-check scores, and current review status. Only accessible
    to the agent who created the task.
    """
    # Verify ownership
    if not await verify_agent_owns_task(auth.agent_id, task_id):
        task = await db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        raise HTTPException(
            status_code=403, detail="Not authorized to view submissions"
        )

    submissions = await db.get_submissions_for_task(task_id)

    result = []
    for sub in submissions:
        # Use auto_check_details from verification pipeline (Phase 1)
        pre_check_score = None
        auto_check_details = sub.get("auto_check_details")
        if isinstance(auto_check_details, dict) and "score" in auto_check_details:
            pre_check_score = auto_check_details["score"]

        result.append(
            SubmissionResponse(
                id=sub["id"],
                task_id=sub["task_id"],
                executor_id=sub["executor_id"],
                status=sub.get("agent_verdict", "pending"),
                pre_check_score=pre_check_score,
                submitted_at=datetime.fromisoformat(
                    sub["submitted_at"].replace("Z", "+00:00")
                ),
                evidence=sub.get("evidence"),
                agent_verdict=sub.get("agent_verdict"),
                agent_notes=sub.get("agent_notes"),
                verified_at=datetime.fromisoformat(
                    sub["verified_at"].replace("Z", "+00:00")
                )
                if sub.get("verified_at")
                else None,
            )
        )

    return SubmissionListResponse(
        submissions=result,
        count=len(result),
    )


@router.post(
    "/submissions/{submission_id}/approve",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Submission approved and payment released to worker"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to approve this submission",
        },
        404: {"model": ErrorResponse, "description": "Submission not found"},
        409: {
            "model": ErrorResponse,
            "description": "Submission already processed or task not in valid state",
        },
        502: {
            "model": ErrorResponse,
            "description": "Payment settlement failed - submission not approved",
        },
    },
    summary="Approve Submission",
    description="Approve a worker's submission and trigger payment settlement",
    tags=["Submissions", "Agent", "Payments"],
)
async def approve_submission(
    http_request: Request = None,
    submission_id: str = Path(
        ..., description="UUID of the submission", pattern=UUID_PATTERN
    ),
    request: ApprovalRequest = None,
    auth: AgentAuth = Depends(verify_agent_auth),
) -> SuccessResponse:
    """
    Approve a worker's submission and trigger payment settlement.

    This endpoint approves a worker's submitted work and immediately attempts to
    settle payment to the worker's wallet. The task status will be updated to
    'completed' upon successful payment settlement.
    """
    # Read optional Fase 1 payment auth headers
    _worker_auth = None
    _fee_auth = None
    if http_request is not None:
        _worker_auth = http_request.headers.get(
            "X-Payment-Worker"
        ) or http_request.headers.get("x-payment-worker")
        _fee_auth = http_request.headers.get(
            "X-Payment-Fee"
        ) or http_request.headers.get("x-payment-fee")
    # Verify ownership
    if not await verify_agent_owns_submission(auth.agent_id, submission_id):
        submission = await db.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        raise HTTPException(
            status_code=403, detail="Not authorized to approve this submission"
        )

    # Check if already processed.
    # If already accepted, return idempotent success for safe client retries.
    submission = await db.get_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    existing_verdict = _normalize_status(submission.get("agent_verdict"))
    if existing_verdict in {"accepted", "approved"}:
        settlement = await _settle_submission_payment(
            submission_id=submission_id,
            submission=submission,
            note="Idempotent settlement retry after prior approval",
            worker_auth_header=_worker_auth,
            fee_auth_header=_fee_auth,
        )
        idem_task = submission.get("task") or {}
        idem_network = idem_task.get("payment_network") or "base"
        response_data = {
            "submission_id": submission_id,
            "verdict": "accepted",
            "idempotent": True,
            "network": idem_network,
        }
        if settlement.get("payment_tx"):
            response_data["payment_tx"] = settlement["payment_tx"]
            explorer_url = _build_explorer_url(settlement["payment_tx"], idem_network)
            if explorer_url:
                response_data["explorer_url"] = explorer_url
        if settlement.get("payment_error"):
            response_data["payment_error"] = settlement["payment_error"]

        return SuccessResponse(
            message="Submission already approved.",
            data=response_data,
        )

    if existing_verdict not in {"", "pending"}:
        raise HTTPException(
            status_code=409,
            detail=f"Submission already processed with verdict: {submission.get('agent_verdict')}",
        )

    task = submission.get("task") or {}
    task_status = _normalize_status(task.get("status"))
    if task_status in {"cancelled", "refunded", "expired"}:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve submission while task status is '{task_status}'",
        )
    if task_status == "completed":
        raise HTTPException(
            status_code=409,
            detail="Cannot approve submission because task is already completed",
        )

    # --- Escrow validation: reject approval if escrow not in releasable state ---
    if EM_PAYMENT_MODE != "fase1":
        task_id = task.get("id")
        if task_id:
            _RELEASABLE_STATUSES = {
                "deposited",
                "funded",
                "locked",
                "active",
            }
            try:
                esc_check = (
                    db.get_client()
                    .table("escrows")
                    .select("status")
                    .eq("task_id", task_id)
                    .limit(1)
                    .execute()
                )
                esc_data = esc_check.data[0] if esc_check.data else None
            except Exception as e:
                logger.warning(
                    "Escrow lookup failed for task %s during approval: %s",
                    task_id,
                    e,
                )
                esc_data = None

            if not esc_data:
                raise HTTPException(
                    status_code=409,
                    detail="Cannot approve: no escrow record found for this task",
                )
            esc_status = _normalize_status(esc_data.get("status"))
            if esc_status not in _RELEASABLE_STATUSES:
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot approve: escrow not in releasable state (status: {esc_status})",
                )

    from audit import audit_log as _audit_approve

    _audit_approve("task_approved", task_id=task.get("id"), approved_by=auth.agent_id)

    notes = request.notes if request else None
    rating_score = getattr(request, "rating_score", None) if request else None
    settlement = await _settle_submission_payment(
        submission_id=submission_id,
        submission=submission,
        note="Manual approval payout via x402 facilitator",
        worker_auth_header=_worker_auth,
        fee_auth_header=_fee_auth,
        override_score=rating_score,
    )
    release_tx = settlement.get("payment_tx")
    release_error = settlement.get("payment_error")

    if not release_tx:
        raise HTTPException(
            status_code=502,
            detail=f"Could not settle payment before approval: {release_error or 'missing tx hash'}",
        )

    # Only mark approved/completed after settlement has tx evidence.
    try:
        await db.update_submission(
            submission_id=submission_id,
            agent_id=auth.agent_id,
            verdict="accepted",
            notes=notes,
        )
    except Exception as state_err:
        logger.error(
            "Payment released for submission %s but state update failed: %s",
            submission_id,
            state_err,
        )
        return SuccessResponse(
            message="Payment released, but submission state update needs retry.",
            data={
                "submission_id": submission_id,
                "verdict": "accepted_pending_state_update",
                "payment_tx": release_tx,
                "payment_error": str(state_err),
            },
        )

    logger.info(
        "Submission approved and paid: id=%s, agent=%s, tx=%s",
        submission_id,
        auth.agent_id,
        release_tx,
    )

    # Fire-and-forget: ERC-8004 side effects (WS-1 registration, WS-2 agent rating)
    try:
        await _execute_post_approval_side_effects(
            submission_id=submission_id,
            submission=submission,
            release_tx=release_tx,
        )
    except Exception as side_fx_err:
        logger.error(
            "Post-approval side effects error (non-blocking): submission=%s, error=%s",
            submission_id,
            side_fx_err,
        )

    # Lifecycle checkpoints: approved + payment released
    try:
        from audit.checkpoint_updater import mark_approved, mark_payment_released

        await mark_approved(task.get("id", ""))
        await mark_payment_released(
            task.get("id", ""),
            tx_hash=release_tx,
            worker_amount=settlement.get("worker_net_usdc"),
            fee_amount=settlement.get("platform_fee_usdc"),
        )
    except Exception:
        pass  # Non-blocking

    task_network = task.get("payment_network") or "base"
    response_data = {
        "submission_id": submission_id,
        "verdict": "accepted",
        "payment_tx": release_tx,
        "network": task_network,
    }
    if release_tx:
        explorer_url = _build_explorer_url(release_tx, task_network)
        if explorer_url:
            response_data["explorer_url"] = explorer_url
    if release_error:
        response_data["payment_error"] = release_error
    # Pass through detailed payment fields from settlement
    for key in (
        "fee_tx",
        "escrow_release_tx",
        "payment_mode",
        "platform_fee_usdc",
        "worker_net_usdc",
        "gross_amount_usdc",
    ):
        if settlement.get(key) is not None:
            response_data[key] = settlement[key]

    return SuccessResponse(
        message="Submission approved. Payment released to worker.", data=response_data
    )


@router.post(
    "/submissions/{submission_id}/reject",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Submission rejected and task returned to available pool"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to reject this submission",
        },
        404: {"model": ErrorResponse, "description": "Submission not found"},
        409: {
            "model": ErrorResponse,
            "description": "Submission already processed with different verdict",
        },
    },
    summary="Reject Submission",
    description="Reject a worker's submission and return task to available pool",
    tags=["Submissions", "Agent"],
)
async def reject_submission(
    submission_id: str = Path(
        ..., description="UUID of the submission", pattern=UUID_PATTERN
    ),
    request: RejectionRequest = ...,
    auth: AgentAuth = Depends(verify_agent_auth),
) -> SuccessResponse:
    """
    Reject a worker's submission and return the task to available status.

    When a submission doesn't meet requirements, the agent can reject it with
    detailed feedback. The task returns to 'published' status so other workers
    can apply and complete it properly.
    """
    # Verify ownership
    if not await verify_agent_owns_submission(auth.agent_id, submission_id):
        submission = await db.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        raise HTTPException(
            status_code=403, detail="Not authorized to reject this submission"
        )

    # Check if already processed
    submission = await db.get_submission(submission_id)
    if submission.get("agent_verdict") not in [None, "pending"]:
        raise HTTPException(
            status_code=409,
            detail=f"Submission already processed with verdict: {submission.get('agent_verdict')}",
        )

    # Validate severity-specific constraints
    if request.severity == "major" and request.reputation_score is not None:
        if request.reputation_score > 50:
            raise HTTPException(
                status_code=400,
                detail="Major rejection reputation_score must be 0-50",
            )

    # Update submission — prefix notes with [MAJOR] so update_submission
    # knows to return the task to the public pool (published) vs keeping
    # the same worker (in_progress for minor rejections).
    rejection_notes = (
        f"[MAJOR] {request.notes}" if request.severity == "major" else request.notes
    )
    await db.update_submission(
        submission_id=submission_id,
        agent_id=auth.agent_id,
        verdict="rejected",
        notes=rejection_notes,
    )

    logger.info(
        "Submission rejected: id=%s, agent=%s, severity=%s, reason=%s",
        submission_id,
        auth.agent_id,
        request.severity,
        request.notes[:50],
    )

    side_effect_id = None
    if request.severity == "major":
        from config.platform_config import PlatformConfig

        rejection_enabled = await PlatformConfig.is_feature_enabled(
            "erc8004_rejection_feedback"
        )

        if rejection_enabled:
            # Rate-limit: max 3 major rejections per agent per 24h
            try:
                client = db.get_client()
                cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
                count_result = (
                    client.table("erc8004_side_effects")
                    .select("id", count="exact")
                    .eq("effect_type", "rate_worker_on_rejection")
                    .gte("created_at", cutoff)
                    .execute()
                )
                recent_count = (
                    count_result.count if count_result.count is not None else 0
                )
                # Filter by agent_id from payload
                if recent_count >= 3:
                    # Additional check: count only this agent's rejections
                    all_rows = (
                        client.table("erc8004_side_effects")
                        .select("payload")
                        .eq("effect_type", "rate_worker_on_rejection")
                        .gte("created_at", cutoff)
                        .execute()
                    )
                    agent_count = sum(
                        1
                        for r in (all_rows.data or [])
                        if (r.get("payload") or {}).get("agent_id") == auth.agent_id
                    )
                    if agent_count >= 3:
                        raise HTTPException(
                            status_code=429,
                            detail="Rate limit exceeded: max 3 major rejections per 24 hours",
                        )
            except HTTPException:
                raise
            except Exception as rl_err:
                logger.warning(
                    "Rate limit check failed for rejection feedback: %s", rl_err
                )

            # Verify agent exists on-chain before enqueuing rejection feedback
            score = (
                request.reputation_score if request.reputation_score is not None else 30
            )
            task = submission.get("task") or {}
            executor = submission.get("executor") or {}

            # Use erc8004_agent_id (per-chain numeric ID) for feedback,
            # not auth.agent_id (which is always a wallet address now).
            agent_id_for_feedback = getattr(auth, "erc8004_agent_id", None)
            if agent_id_for_feedback is not None:
                try:
                    from integrations.erc8004.identity import verify_agent_identity

                    agent_check = await verify_agent_identity(
                        str(agent_id_for_feedback),
                        network=task.get("payment_network", "base"),
                    )
                    if not agent_check.get("registered"):
                        logger.warning(
                            "Rejection feedback skip: agent %d not found on-chain",
                            agent_id_for_feedback,
                        )
                        agent_id_for_feedback = None
                except Exception as vc_err:
                    logger.warning(
                        "Rejection feedback skip: identity check failed for agent %s: %s",
                        agent_id_for_feedback,
                        vc_err,
                    )
                    agent_id_for_feedback = None

            if agent_id_for_feedback is not None:
                try:
                    from reputation.side_effects import enqueue_side_effect

                    effect = await enqueue_side_effect(
                        supabase=db.get_client(),
                        submission_id=submission_id,
                        effect_type="rate_worker_on_rejection",
                        payload={
                            "task_id": task.get("id"),
                            "worker_wallet": executor.get("wallet_address"),
                            "agent_id": agent_id_for_feedback,
                            "severity": "major",
                            "notes": request.notes[:200],
                        },
                        score=score,
                    )
                    if effect:
                        side_effect_id = effect.get("id")

                    logger.info(
                        "Major rejection feedback enqueued: submission=%s, agent=%s, score=%d",
                        submission_id,
                        agent_id_for_feedback,
                        score,
                    )
                except Exception as se_err:
                    logger.error(
                        "Failed to enqueue rejection feedback for submission %s: %s",
                        submission_id,
                        se_err,
                    )

    response_data = {"submission_id": submission_id, "verdict": "rejected"}
    if request.severity == "major":
        response_data["severity"] = "major"
    if side_effect_id:
        response_data["side_effect_id"] = side_effect_id

    return SuccessResponse(
        message="Submission rejected. Task returned to available pool.",
        data=response_data,
    )


@router.post(
    "/submissions/{submission_id}/request-more-info",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Additional information requested from worker"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to update this submission",
        },
        404: {"model": ErrorResponse, "description": "Submission not found"},
        409: {
            "model": ErrorResponse,
            "description": "Submission already processed with final verdict",
        },
    },
    summary="Request More Information",
    description="Request additional evidence or clarification from the assigned worker",
    tags=["Submissions", "Agent"],
)
async def request_more_info_submission(
    submission_id: str = Path(
        ..., description="UUID of the submission", pattern=UUID_PATTERN
    ),
    request: RequestMoreInfoRequest = ...,
    auth: AgentAuth = Depends(verify_agent_auth),
) -> SuccessResponse:
    """
    Request additional evidence or clarification from the assigned worker.

    When a submission is close to meeting requirements but needs additional
    evidence or clarification, the agent can request more information instead
    of rejecting outright.
    """
    if not await verify_agent_owns_submission(auth.agent_id, submission_id):
        submission = await db.get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        raise HTTPException(
            status_code=403, detail="Not authorized to update this submission"
        )

    submission = await db.get_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    existing_verdict = _normalize_status(submission.get("agent_verdict"))
    if existing_verdict in {"accepted", "approved", "rejected", "disputed"}:
        raise HTTPException(
            status_code=409,
            detail=f"Submission already processed with verdict: {submission.get('agent_verdict')}",
        )

    task = submission.get("task") or {}
    task_id = task.get("id")
    if not task_id:
        raise HTTPException(
            status_code=500, detail="Submission is missing task context"
        )

    await db.update_submission(
        submission_id=submission_id,
        agent_id=auth.agent_id,
        verdict="more_info_requested",
        notes=request.notes,
    )
    await db.update_task(task_id, {"status": "in_progress"})

    logger.info(
        "More info requested: submission=%s, task=%s, agent=%s",
        submission_id,
        task_id,
        auth.agent_id,
    )

    return SuccessResponse(
        message="More information requested from worker.",
        data={
            "submission_id": submission_id,
            "task_id": task_id,
            "verdict": "more_info_requested",
        },
    )
