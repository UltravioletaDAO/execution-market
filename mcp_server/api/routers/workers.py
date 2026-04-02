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
    UpdateSocialLinksRequest,
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
    "/workers/world-status",
    response_model=SuccessResponse,
    responses={
        200: {"description": "World verification status retrieved"},
        400: {"model": ErrorResponse, "description": "Invalid wallet address"},
        500: {"model": ErrorResponse, "description": "Lookup failed"},
    },
    summary="Check World Human Verification",
    description=(
        "Check whether a wallet address belongs to a World-verified human "
        "via the AgentBook contract on Base."
    ),
    tags=["Workers", "World"],
)
async def get_world_status(
    wallet: str = Query(
        ...,
        description="Wallet address to check (0x-prefixed)",
        min_length=42,
        max_length=42,
    ),
) -> SuccessResponse:
    """Check World AgentBook verification status for a wallet address."""
    if not wallet.startswith("0x"):
        raise HTTPException(status_code=400, detail="Wallet must be 0x-prefixed")
    try:
        from integrations.world import lookup_human

        result = await lookup_human(wallet)
        return SuccessResponse(
            message="World verification status retrieved",
            data=result.to_dict(),
        )
    except Exception as e:
        logger.error("World status lookup failed for %s: %s", wallet[:10], e)
        raise HTTPException(
            status_code=500, detail="Error checking World verification status"
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


@router.get(
    "/submissions/{submission_id}",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Submission details retrieved"},
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to view this submission",
        },
        404: {"model": ErrorResponse, "description": "Submission not found"},
    },
    summary="Get Submission Detail",
    description=(
        "Get a submission's full details including AI verification results. "
        "Workers use this to poll for Phase B verification updates after submitting evidence."
    ),
    tags=["Workers", "Submissions"],
)
async def get_submission_detail(
    raw_request: Request,
    submission_id: str = Path(
        ..., description="UUID of the submission", pattern=UUID_PATTERN
    ),
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
) -> SuccessResponse:
    """Get a submission's details including async AI verification results.

    After submitting evidence, Phase A verification runs synchronously and is
    returned in the submit response.  Phase B runs asynchronously and updates
    the ``ai_verification_result`` column in the database.  Workers call this
    endpoint to retrieve the latest verification state.
    """
    # Fetch submission by ID (uses supabase_client.get_submission which joins
    # task and executor data via .select("*, task:tasks(*), executor:executors(...)"))
    submission = await db.get_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Auth: verify caller is the executor who submitted this work.
    # If worker_auth is present, the executor_id must match the submission's.
    sub_executor_id = submission.get("executor_id")
    if worker_auth and worker_auth.executor_id:
        if worker_auth.executor_id != sub_executor_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view this submission",
            )
    else:
        # Soft auth: log warning but allow (matches body-fallback pattern)
        logger.warning(
            "SECURITY_AUDIT action=submission_detail.no_auth submission_id=%s path=%s",
            submission_id[:8],
            raw_request.url.path,
        )

    return SuccessResponse(
        message="Submission retrieved",
        data={
            "id": submission.get("id"),
            "task_id": submission.get("task_id"),
            "executor_id": sub_executor_id,
            "status": submission.get("agent_verdict"),
            "evidence": submission.get("evidence"),
            "notes": submission.get("notes"),
            "auto_check_passed": submission.get("auto_check_passed"),
            "auto_check_details": submission.get("auto_check_details"),
            "ai_verification_result": submission.get("ai_verification_result"),
            "submitted_at": submission.get("submitted_at")
            or submission.get("created_at"),
            "verified_at": submission.get("verified_at")
            or submission.get("updated_at"),
            "payment_tx": submission.get("payment_tx"),
        },
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

    # ---- ERC-8004 Worker Identity (check + auto-register) ----------------
    # Controlled by EM_REQUIRE_ERC8004_WORKER env var (default: false).
    # When true: worker must have on-chain identity to apply. If not registered,
    # we auto-register gaslessly (Facilitator pays). Fails only if no wallet.
    # Identity is created on the SAME chain as the task's payment_network.
    import os

    _require_worker_erc8004 = (
        os.environ.get("EM_REQUIRE_ERC8004_WORKER", "false").lower() == "true"
    )
    if _require_worker_erc8004:
        try:
            from integrations.erc8004 import (
                check_worker_identity,
                register_worker_gasless,
            )

            # Resolve the task's payment network so worker identity is created
            # on the correct chain (not hardcoded to Base).
            task_data = await db.get_task(task_id)
            task_network = (task_data or {}).get("payment_network", "base")

            # Validate the network is supported for ERC-8004
            from integrations.erc8004.facilitator_client import ERC8004_CONTRACTS

            if task_network not in ERC8004_CONTRACTS:
                logger.warning(
                    "Task %s payment_network=%s not supported for ERC-8004 identity "
                    "(supported: %s). Skipping worker identity check.",
                    task_id,
                    task_network,
                    list(ERC8004_CONTRACTS.keys()),
                )
            else:
                executor_stats = await db.get_executor_stats(executor_id)
                worker_wallet = (executor_stats or {}).get("wallet_address")

                if not worker_wallet:
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "error": "wallet_required",
                            "message": (
                                "You need a connected wallet to apply for tasks. "
                                "Connect your wallet in the Execution Market dashboard."
                            ),
                        },
                    )

                # Guard 1: DB check — fast path (avoid unnecessary on-chain calls)
                _db_executor = (
                    db.get_client()
                    .table("executors")
                    .select("erc8004_agent_id")
                    .eq("id", executor_id)
                    .limit(1)
                    .execute()
                )
                _db_agent_id = (
                    _db_executor.data[0].get("erc8004_agent_id")
                    if _db_executor.data
                    else None
                )
                if _db_agent_id:
                    logger.info(
                        "Worker %s already has erc8004_agent_id=%s (DB), skipping registration",
                        executor_id,
                        _db_agent_id,
                    )
                    identity = None  # skip on-chain check + registration
                else:
                    # Guard 2: On-chain check on the task's payment network
                    identity = await check_worker_identity(
                        worker_wallet, network=task_network
                    )

                if identity is not None and not identity.agent_id:
                    logger.info(
                        "Worker %s has no ERC-8004 identity on %s — auto-registering gaslessly",
                        executor_id,
                        task_network,
                    )
                    reg = await register_worker_gasless(
                        worker_wallet, network=task_network
                    )
                    if not reg.agent_id:
                        raise HTTPException(
                            status_code=403,
                            detail={
                                "error": "identity_registration_failed",
                                "message": (
                                    "Could not register your on-chain identity. "
                                    "Please try again or contact support."
                                ),
                            },
                        )
                    logger.info(
                        "Worker %s auto-registered on ERC-8004: agent_id=%s, network=%s",
                        executor_id,
                        reg.agent_id,
                        task_network,
                    )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(
                "ERC-8004 worker identity check failed (non-blocking) for %s: %s",
                executor_id,
                e,
            )

    # ---- World AgentKit Human Verification (non-blocking) -------------------
    # When enabled, checks the AgentBook contract on Base to determine whether
    # the worker is a World-verified human.  Result is stored in DB but NEVER
    # blocks the application flow.
    world_verified = False
    world_human_id = None
    try:
        from config.platform_config import PlatformConfig

        _world_enabled = await PlatformConfig.get(
            "feature.world_agentkit_enabled", True
        )
        if _world_enabled:
            from integrations.world import lookup_human

            # Reuse wallet fetched by ERC-8004 block when available
            if not locals().get("worker_wallet"):
                _exec_stats = await db.get_executor_stats(executor_id)
                worker_wallet = (_exec_stats or {}).get("wallet_address")

            if worker_wallet:
                world_result = await lookup_human(worker_wallet)
                if world_result.is_human:
                    world_verified = True
                    world_human_id = world_result.human_id
                    from datetime import datetime, timezone

                    client = db.get_client()
                    client.table("executors").update(
                        {
                            "world_human_id": world_result.human_id,
                            "world_verified_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ).eq("id", executor_id).execute()
                    logger.info(
                        "World AgentKit: executor=%s is verified human (humanId=%d)",
                        executor_id[:8],
                        world_result.human_id,
                    )
                else:
                    logger.debug(
                        "World AgentKit: executor=%s not verified (status=%s)",
                        executor_id[:8],
                        world_result.status,
                    )
    except Exception as e:
        logger.warning(
            "World AgentKit check failed (non-blocking) for %s: %s",
            executor_id,
            e,
        )

    # ---- World ID Verification (high-value task enforcement) ----------------
    # When enabled: tasks above the bounty threshold require World ID Orb verification.
    import os as _os

    _world_id_enabled = (
        _os.environ.get("EM_WORLD_ID_ENABLED", "true").lower() == "true"
    )
    if _world_id_enabled:
        try:
            from config.platform_config import PlatformConfig

            _world_id_required_high_value = await PlatformConfig.get(
                "feature.world_id_required_for_high_value", True
            )

            if _world_id_required_high_value:
                if not locals().get("task_data"):
                    task_data = await db.get_task(task_id)

                task_bounty = Decimal(str((task_data or {}).get("bounty_usd", 0)))
                orb_threshold = await PlatformConfig.get(
                    "worldid.min_bounty_for_orb_usd", Decimal("5.00")
                )

                _wid_check = (
                    db.get_client()
                    .table("executors")
                    .select("world_id_verified, world_id_level")
                    .eq("id", executor_id)
                    .limit(1)
                    .execute()
                )
                _wid_data = _wid_check.data[0] if _wid_check.data else {}
                _wid_verified = _wid_data.get("world_id_verified", False)
                _wid_level = _wid_data.get("world_id_level")

                if task_bounty >= orb_threshold and (
                    not _wid_verified or _wid_level != "orb"
                ):
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "error": "world_id_orb_required",
                            "message": (
                                f"Tasks with bounty >= ${orb_threshold} require "
                                "World ID Orb verification. Please verify your "
                                "identity at https://execution.market/profile."
                            ),
                            "verification_url": "/profile",
                            "required_level": "orb",
                            "current_level": _wid_level,
                        },
                    )

        except HTTPException:
            raise
        except Exception as e:
            logger.warning(
                "World ID enforcement check failed (non-blocking) for %s: %s",
                executor_id,
                e,
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
                owner_id=result.get("task", {}).get("agent_id"),
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
                "world_verified": world_verified,
                "world_human_id": world_human_id,
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

        # GPS debug: log evidence structure (never log actual coordinates)
        _gps_keys = []
        for ek, ev in evidence.items():
            if isinstance(ev, dict):
                if "gps" in ev:
                    _gps_keys.append(f"{ek}.gps")
                meta = ev.get("metadata")
                if isinstance(meta, dict):
                    if "gps" in meta:
                        _gps_keys.append(f"{ek}.metadata.gps")
        logger.info(
            "[AUDIT] submit_work GPS_DEBUG evidence_keys=%s gps_found=%s",
            list(evidence.keys()),
            _gps_keys or "none",
        )

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

        from audit import audit_log as _audit_evidence

        _audit_evidence(
            "evidence_submitted",
            task_id=task_id,
            submission_id=submission_id,
            score=None,
            evidence_count=len(evidence),
        )

        # Lifecycle checkpoint: evidence submitted
        try:
            from audit.checkpoint_updater import mark_evidence_submitted

            await mark_evidence_submitted(task_id, evidence_count=len(evidence))
        except Exception:
            pass  # Non-blocking

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

                # Lifecycle checkpoint: AI verification complete
                try:
                    from audit.checkpoint_updater import mark_ai_verified

                    verdict = "passed" if verification_result.passed else "failed"
                    await mark_ai_verified(task_id, verdict=verdict)
                except Exception:
                    pass  # Non-blocking

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


# ---------------------------------------------------------------------------
# Social Links
# ---------------------------------------------------------------------------

import re

_X_HANDLE_RE = re.compile(r"^@[A-Za-z0-9_]{1,15}$")


@router.put(
    "/workers/social-links",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Social link updated"},
        400: {"model": ErrorResponse, "description": "Invalid handle"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
    summary="Update Social Links",
    description="Add or update a social platform link on the worker profile.",
    tags=["Workers"],
)
async def update_social_links(
    raw_request: Request,
    request: UpdateSocialLinksRequest,
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
) -> SuccessResponse:
    """Add or update a social link (e.g. X/Twitter handle) on executor profile."""
    if not worker_auth or not worker_auth.executor_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    executor_id = worker_auth.executor_id
    platform = request.platform.lower()
    handle = request.handle.strip()

    # Platform-specific validation
    if platform == "x":
        if not _X_HANDLE_RE.match(handle):
            raise HTTPException(
                status_code=400,
                detail="Invalid X handle. Must be @username (1-15 alphanumeric/underscore chars).",
            )

    try:
        client = db.get_client()
        from datetime import datetime, timezone

        # Fetch current social_links
        existing = (
            client.table("executors")
            .select("social_links")
            .eq("id", executor_id)
            .limit(1)
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Executor not found")

        social_links = existing.data[0].get("social_links") or {}
        social_links[platform] = {
            "handle": handle,
            "verified": False,
            "linked_at": datetime.now(timezone.utc).isoformat(),
        }

        client.table("executors").update({"social_links": social_links}).eq(
            "id", executor_id
        ).execute()

        logger.info(
            "Social link updated: executor=%s, platform=%s, handle=%s",
            executor_id[:8],
            platform,
            handle,
        )

        return SuccessResponse(
            message=f"Social link for {platform} updated",
            data={"platform": platform, "handle": handle},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating social links: %s", e)
        raise HTTPException(
            status_code=500, detail="Internal error while updating social links"
        )
