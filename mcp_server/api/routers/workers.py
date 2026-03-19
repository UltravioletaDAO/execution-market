"""
Worker apply and submit endpoints.

Extracted from api/routes.py.
"""

from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

import supabase_client as db
import asyncio

from ..auth import verify_worker_auth, WorkerAuth, _enforce_worker_identity

from verification.pipeline import run_verification_pipeline
from verification.background_runner import run_phase_b_verification

from ._models import (
    WorkerRegisterRequest,
    WorkerApplicationRequest,
    WorkerSubmissionRequest,
    SuccessResponse,
    ErrorResponse,
)

from decimal import Decimal

from ._helpers import (
    logger,
    UUID_PATTERN,
    _settle_submission_payment,
    _is_submission_ready_for_instant_payout,
    _auto_approve_submission,
    dispatch_webhook,
)

router = APIRouter(prefix="/api/v1", tags=["Workers"])


@router.post(
    "/workers/register",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Worker registered or retrieved"},
        400: {"model": ErrorResponse, "description": "Invalid wallet address"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
    summary="Register Worker",
    description="Register a new worker by wallet address, or return the existing executor if already registered.",
    tags=["Workers"],
)
async def register_worker(
    request: WorkerRegisterRequest,
) -> SuccessResponse:
    """
    Register a worker by wallet address.

    Calls the Supabase RPC ``get_or_create_executor`` which either creates a
    new executor record or returns the existing one. Used by XMTP bot and
    other external integrations that onboard workers by wallet.
    """
    try:
        client = db.get_client()
        result = client.rpc(
            "get_or_create_executor",
            {
                "p_wallet": request.wallet_address.lower(),
                "p_display_name": request.name,
                "p_email": request.email,
            },
        ).execute()

        if not result.data:
            raise HTTPException(
                status_code=500, detail="No response from executor registration"
            )

        rpc_result = result.data
        executor = rpc_result.get("executor", {})

        logger.info(
            "Worker registered: wallet=%s, executor=%s, new=%s",
            request.wallet_address[:10],
            str(executor.get("id", ""))[:8],
            rpc_result.get("is_new"),
        )

        return SuccessResponse(
            message="Worker registered successfully"
            if rpc_result.get("is_new")
            else "Worker already registered",
            data={
                "executor_id": executor.get("id"),
                "wallet_address": executor.get("wallet_address"),
                "created": rpc_result.get("is_new", False),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error("Error registering worker: %s", error_msg)
        raise HTTPException(
            status_code=500, detail="Internal error while registering worker"
        )


@router.get(
    "/workers/tasks/{task_id}/my-submission",
    response_model=SuccessResponse,
    responses={
        404: {"model": ErrorResponse, "description": "No submission found"},
    },
    summary="Get My Submission",
    description="Get the executor's own submission for a task (evidence, verdict, verification).",
    tags=["Workers", "Submissions"],
)
async def get_my_submission(
    raw_request: Request,
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    executor_id: str = Query(..., description="UUID of the executor"),
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
) -> SuccessResponse:
    """Get the executor's own submission for a task (evidence, verdict, verification)."""
    # Enforce: caller must be the executor they claim to be
    executor_id = _enforce_worker_identity(
        worker_auth, executor_id, raw_request.url.path
    )

    client = db.get_client()
    result = (
        client.table("submissions")
        .select(
            "id, task_id, executor_id, evidence, notes, agent_verdict, "
            "auto_check_passed, auto_check_details, created_at, updated_at, payment_tx"
        )
        .eq("task_id", task_id)
        .eq("executor_id", executor_id)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="No submission found for this task")

    submission = result.data[0]
    return SuccessResponse(
        message="Submission retrieved",
        data=submission,
    )


@router.post(
    "/tasks/{task_id}/apply",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Application submitted"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        403: {"model": ErrorResponse, "description": "Not eligible"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        409: {"model": ErrorResponse, "description": "Already applied"},
    },
)
async def apply_to_task(
    raw_request: Request,
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    request: WorkerApplicationRequest = ...,
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
) -> SuccessResponse:
    """
    Apply to a task.

    Worker endpoint for submitting task applications. Checks reputation requirements.
    """
    executor_id = _enforce_worker_identity(
        worker_auth, request.executor_id, raw_request.url.path
    )
    try:
        result = await db.apply_to_task(
            task_id=task_id,
            executor_id=executor_id,
            message=request.message,
        )

        logger.info(
            "Application submitted: task=%s, executor=%s",
            task_id,
            executor_id[:8],
        )

        # Non-blocking webhook dispatch
        try:
            from webhooks.events import WebhookEventType

            await dispatch_webhook(
                WebhookEventType.WORKER_APPLIED,
                {
                    "task_id": task_id,
                    "worker_id": executor_id,
                    "application_id": result["application"]["id"],
                    "message": request.message,
                },
            )
        except Exception:
            pass  # Never block the apply flow

        # Event Bus publish (coexists with legacy — Strangler Fig)
        try:
            from events import get_event_bus, EMEvent, EventSource

            await get_event_bus().publish(
                EMEvent(
                    event_type="worker.applied",
                    task_id=task_id,
                    source=EventSource.REST_API,
                    payload={
                        "task_id": task_id,
                        "worker_id": executor_id,
                        "application_id": result["application"]["id"],
                    },
                )
            )
        except Exception:
            pass

        return SuccessResponse(
            message="Application submitted successfully",
            data={
                "application_id": result["application"]["id"],
                "task_id": task_id,
                "status": "pending",
            },
        )

    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            if "executor" in error_msg.lower():
                raise HTTPException(status_code=404, detail="Executor not found")
            raise HTTPException(status_code=404, detail="Task not found")
        elif "not available" in error_msg.lower():
            raise HTTPException(
                status_code=409, detail="Task is not available for applications"
            )
        elif "insufficient reputation" in error_msg.lower():
            raise HTTPException(status_code=403, detail=error_msg)
        elif "cannot apply to your own task" in error_msg.lower():
            raise HTTPException(status_code=403, detail="Cannot apply to your own task")
        elif "already applied" in error_msg.lower():
            raise HTTPException(status_code=409, detail="Already applied to this task")
        logger.error("Unexpected error applying to task %s: %s", task_id, error_msg)
        raise HTTPException(
            status_code=500, detail="Internal error while applying to task"
        )


@router.post(
    "/tasks/{task_id}/submit",
    response_model=SuccessResponse,
    responses={
        200: {
            "description": "Work submitted successfully, with optional instant payment"
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid request or missing required evidence",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not assigned to this task or not authorized",
        },
        404: {"model": ErrorResponse, "description": "Task not found"},
        409: {"model": ErrorResponse, "description": "Task not in submittable state"},
    },
    summary="Submit Work",
    description="Submit completed work with evidence for agent review (supports instant payment)",
    tags=["Tasks", "Worker", "Submissions"],
)
async def submit_work(
    raw_request: Request,
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    request: WorkerSubmissionRequest = ...,
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
) -> SuccessResponse:
    """
    Submit completed work with evidence for agent review.

    Worker endpoint for submitting finished work with required evidence.
    Automatically attempts instant payment settlement when possible, otherwise
    queues submission for agent review.
    """
    executor_id = _enforce_worker_identity(
        worker_auth, request.executor_id, raw_request.url.path
    )
    try:
        # Merge device_metadata into evidence so the verification pipeline
        # can extract GPS coordinates from it (mobile sends GPS there).
        evidence = dict(request.evidence)
        if request.device_metadata:
            evidence["device_metadata"] = request.device_metadata

        result = await db.submit_work(
            task_id=task_id,
            executor_id=executor_id,
            evidence=evidence,
            notes=request.notes,
        )

        submission_id = result["submission"]["id"]
        logger.info(
            "Work submitted: task=%s, executor=%s, submission=%s",
            task_id,
            executor_id[:8],
            submission_id,
        )

        # --- Automated evidence verification (non-blocking) ---
        verification_result = None
        try:
            task = await db.get_task(task_id)
            if task:
                submission_data = {
                    "id": submission_id,
                    "evidence": evidence,
                    "submitted_at": result["submission"].get("submitted_at"),
                    "notes": request.notes,
                }
                verification_result = await run_verification_pipeline(
                    submission=submission_data, task=task
                )
                await db.update_submission_auto_check(
                    submission_id=submission_id,
                    auto_check_passed=verification_result.passed,
                    auto_check_details=verification_result.to_dict(),
                )
                logger.info(
                    "Auto-check (Phase A) for submission %s: passed=%s, score=%.2f",
                    submission_id,
                    verification_result.passed,
                    verification_result.score,
                )

                # Launch Phase B (async, non-blocking)
                asyncio.create_task(
                    run_phase_b_verification(
                        submission_id=submission_id,
                        submission=submission_data,
                        task=task,
                    )
                )
        except Exception as verify_err:
            logger.warning(
                "Evidence verification failed for submission %s: %s",
                submission_id,
                verify_err,
            )

        response_data: Dict[str, Any] = {
            "submission_id": submission_id,
            "task_id": task_id,
            "status": "submitted",
        }
        if verification_result:
            response_data["verification"] = {
                "passed": verification_result.passed,
                "score": round(verification_result.score, 3),
                "checks": [
                    {
                        "name": c.name,
                        "passed": c.passed,
                        "score": round(c.score, 3),
                        "reason": c.reason,
                    }
                    for c in verification_result.checks
                ],
                "warnings": verification_result.warnings,
                "phase": "A",
                "phase_b_status": "pending",
                "summary": _build_verification_summary(verification_result),
            }
        response_message = "Work submitted successfully. Awaiting agent review."

        # Attempt instant payout at submission time when x402 settlement context exists.
        try:
            submission = await db.get_submission(submission_id)
            if submission:
                readiness = await _is_submission_ready_for_instant_payout(
                    submission_id=submission_id,
                    submission=submission,
                )
                if readiness.get("ready"):
                    settlement = await _settle_submission_payment(
                        submission_id=submission_id,
                        submission=submission,
                        note="Instant payout on worker submission via x402 facilitator",
                    )
                    payment_tx = settlement.get("payment_tx")
                    payment_error = settlement.get("payment_error")

                    if payment_tx:
                        try:
                            await _auto_approve_submission(
                                submission_id=submission_id,
                                submission=submission,
                                note="Auto-approved after successful instant payout",
                            )
                            response_data["status"] = "completed"
                            response_data["verdict"] = "accepted"
                        except Exception as finalize_err:
                            payment_error = (
                                payment_error
                                or f"Payment released but could not finalize task state: {finalize_err}"
                            )
                        response_data["payment_tx"] = payment_tx
                        response_message = "Work submitted and paid instantly."

                    if payment_error:
                        response_data["payment_error"] = payment_error
                else:
                    logger.info(
                        "Instant payout skipped for submission %s (reason=%s)",
                        submission_id,
                        readiness.get("reason"),
                    )
        except Exception as instant_err:
            logger.error(
                "Instant payout attempt failed for submission %s: %s",
                submission_id,
                instant_err,
            )
            response_data["payment_error"] = str(instant_err)

        return SuccessResponse(
            message=response_message,
            data=response_data,
        )

    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail="Task not found")
        elif "not assigned" in error_msg.lower():
            raise HTTPException(
                status_code=403, detail="You are not assigned to this task"
            )
        elif "not in a submittable state" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg)
        elif "missing required evidence" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        logger.error(
            "Unexpected error submitting work for task %s: %s", task_id, error_msg
        )
        raise HTTPException(
            status_code=500, detail="Internal error while submitting work"
        )


def _build_verification_summary(result) -> str:
    """Build a human-readable one-liner for verification results."""
    total = len(result.checks)
    passed = sum(1 for c in result.checks if c.passed)
    pct = round(result.score * 100)

    failed_names = [c.name for c in result.checks if not c.passed]

    base = f"Verificacion inicial: {passed}/{total} checks pasaron ({pct}%)."
    if result.passed and not failed_names:
        return f"{base} Verificacion por IA en progreso..."
    if failed_names:
        reasons = ", ".join(
            c.reason for c in result.checks if not c.passed and c.reason
        )
        if reasons:
            return f"{base} {reasons}"
        return f"{base} Fallaron: {', '.join(failed_names)}"
    return f"{base} Verificacion por IA en progreso..."


# ---------------------------------------------------------------------------
# Payment events (worker earnings / history)
# ---------------------------------------------------------------------------

# Event types that represent money received by a worker
_EARNING_EVENT_TYPES = {"disburse_worker", "settle", "settle_worker_direct"}


@router.get(
    "/payments/events",
    response_model=None,
    summary="Get Payment Events",
    description=(
        "Retrieve payment events filtered by wallet address. "
        "Used by workers to view their earnings history."
    ),
    tags=["Workers", "Payments"],
)
async def get_payment_events(
    address: str = Query(
        ...,
        description="Wallet address to filter by (matches from_address or to_address)",
        min_length=10,
        max_length=128,
    ),
    since: Optional[str] = Query(
        None,
        description="ISO 8601 timestamp — only return events after this time",
    ),
    limit: int = Query(20, description="Max events to return", ge=1, le=100),
    event_type: Optional[str] = Query(
        None,
        description="Filter by event type (e.g. disburse_worker, settle, escrow_release)",
        alias="event_type",
    ),
) -> Dict[str, Any]:
    """Return payment events where *address* appears as sender or receiver."""
    addr = address.strip().lower()

    client = db.get_client()

    try:
        # Supabase PostgREST `or` filter: match from_address OR to_address
        query = (
            client.table("payment_events")
            .select("*")
            .or_(f"from_address.ilike.{addr},to_address.ilike.{addr}")
            .order("created_at", desc=True)
            .limit(limit)
        )

        if event_type:
            query = query.eq("event_type", event_type)

        if since:
            query = query.gte("created_at", since)

        result = query.execute()
        rows: List[Dict[str, Any]] = result.data or []
    except Exception as exc:
        logger.error("Failed to query payment_events for address %s: %s", addr, exc)
        raise HTTPException(status_code=500, detail="Error querying payment events")

    # Build response events with fields the XMTP bot and dashboard expect
    events: List[Dict[str, Any]] = []
    for row in rows:
        events.append(
            {
                "id": row.get("id"),
                "task_id": row.get("task_id"),
                "event_type": row.get("event_type"),
                "status": row.get("status"),
                "tx_hash": row.get("tx_hash"),
                "from_address": row.get("from_address"),
                "to_address": row.get("to_address"),
                "amount": row.get("amount_usdc"),
                "amount_usdc": row.get("amount_usdc"),
                "network": row.get("network"),
                "payment_network": row.get("network"),
                "token": row.get("token", "USDC"),
                "created_at": row.get("created_at"),
                "metadata": row.get("metadata"),
            }
        )

    # Compute total earned: sum of amounts where to_address matches and
    # event_type is one of the earning types.
    total_earned = Decimal("0")
    earning_count = 0
    for evt in events:
        evt_type = evt.get("event_type", "")
        to_addr = (evt.get("to_address") or "").lower()
        amt = evt.get("amount_usdc")
        if to_addr == addr and evt_type in _EARNING_EVENT_TYPES and amt is not None:
            try:
                total_earned += Decimal(str(amt))
                earning_count += 1
            except Exception:
                pass

    return {
        "events": events,
        "total_earned_usdc": str(total_earned.quantize(Decimal("0.01"))),
        "count": len(events),
        "earning_count": earning_count,
    }
