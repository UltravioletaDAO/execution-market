"""
Worker apply and submit endpoints.

Extracted from api/routes.py.
"""

from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Path

import supabase_client as db
import asyncio

from verification.pipeline import run_verification_pipeline
from verification.background_runner import run_phase_b_verification

from ._models import (
    WorkerApplicationRequest,
    WorkerSubmissionRequest,
    SuccessResponse,
    ErrorResponse,
)

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
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    request: WorkerApplicationRequest = ...,
) -> SuccessResponse:
    """
    Apply to a task.

    Worker endpoint for submitting task applications. Checks reputation requirements.
    """
    try:
        result = await db.apply_to_task(
            task_id=task_id,
            executor_id=request.executor_id,
            message=request.message,
        )

        logger.info(
            "Application submitted: task=%s, executor=%s",
            task_id,
            request.executor_id[:8],
        )

        # Non-blocking webhook dispatch
        try:
            from webhooks.events import WebhookEventType

            await dispatch_webhook(
                WebhookEventType.WORKER_APPLIED,
                {
                    "task_id": task_id,
                    "worker_id": request.executor_id,
                    "application_id": result["application"]["id"],
                    "message": request.message,
                },
            )
        except Exception:
            pass  # Never block the apply flow

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
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    request: WorkerSubmissionRequest = ...,
) -> SuccessResponse:
    """
    Submit completed work with evidence for agent review.

    Worker endpoint for submitting finished work with required evidence.
    Automatically attempts instant payment settlement when possible, otherwise
    queues submission for agent review.
    """
    try:
        result = await db.submit_work(
            task_id=task_id,
            executor_id=request.executor_id,
            evidence=request.evidence,
            notes=request.notes,
        )

        submission_id = result["submission"]["id"]
        logger.info(
            "Work submitted: task=%s, executor=%s, submission=%s",
            task_id,
            request.executor_id[:8],
            submission_id,
        )

        # --- Automated evidence verification (non-blocking) ---
        verification_result = None
        try:
            task = await db.get_task(task_id)
            if task:
                submission_data = {
                    "id": submission_id,
                    "evidence": request.evidence,
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
                "checks": len(verification_result.checks),
                "warnings": verification_result.warnings,
                "phase": "A",
                "phase_b_status": "pending",
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
