"""
Task CRUD, batch, assign, cancel, and payment timeline endpoints.

Extracted from api/routes.py.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query, Path, Request
from fastapi.responses import JSONResponse

import supabase_client as db
from models import TaskCategory, TaskStatus

from ..auth import (
    verify_agent_auth,
    AgentAuth,
)

from ._models import (
    CreateTaskRequest,
    TaskResponse,
    TaskListResponse,
    AvailableTasksResponse,
    TaskPaymentResponse,
    TaskPaymentEventResponse,
    TaskTransactionsResponse,
    TransactionEventResponse,
    CancelRequest,
    WorkerAssignRequest,
    BatchCreateRequest,
    BatchCreateResponse,
    ApplicationResponse,
    ApplicationListResponse,
    SuccessResponse,
    ErrorResponse,
)

from ._helpers import (
    logger,
    X402_AVAILABLE,
    ERC8004_IDENTITY_AVAILABLE,
    get_payment_dispatcher,
    get_sdk,
    verify_x402_payment,
    verify_agent_identity,
    log_payment_event,
    get_platform_fee_percent,
    get_min_bounty,
    get_max_bounty,
    CONFIG_AVAILABLE,
    PlatformConfig,
    UUID_PATTERN,
    X402_AUTH_REF_PREFIX,
    REFUNDABLE_ESCROW_STATUSES,
    ALREADY_REFUNDED_ESCROW_STATUSES,
    NON_REFUNDABLE_ESCROW_STATUSES,
    AUTHORIZE_ONLY_ESCROW_STATUSES,
    PENDING_ASSIGNMENT_ESCROW_STATUSES,
    LIVE_TASK_STATUSES,
    ACTIVE_WORKER_TASK_STATUSES,
    TASK_PAYMENT_SETTLED_STATUSES,
    _TX_EVENT_LABELS,
    _normalize_status,
    _as_amount,
    _pick_first_tx_hash,
    _sanitize_reference,
    _insert_escrow_record,
    _is_missing_table_error,
    _is_not_found_error,
    _derive_payment_status,
    _build_explorer_url,
    _event_type_from_payment_row,
    _actor_from_event_type,
    _normalize_payment_network,
    _record_refund_payment,
    _extract_agent_wallet_from_header,
    dispatch_webhook,
)

router = APIRouter(prefix="/api/v1", tags=["Tasks"])


def _auto_register_agent_executor(
    client, wallet: str, erc8004_agent_id=None, agent_name: str = None
):
    """Auto-register an agent as executor in the directory (non-blocking upsert)."""
    wallet_lower = wallet.lower()
    existing = (
        client.table("executors")
        .select("id, erc8004_agent_id")
        .eq("wallet_address", wallet_lower)
        .eq("executor_type", "agent")
        .execute()
    )
    if existing.data:
        # Update erc8004_agent_id if missing
        row = existing.data[0]
        if erc8004_agent_id and not row.get("erc8004_agent_id"):
            client.table("executors").update(
                {"erc8004_agent_id": int(erc8004_agent_id)}
            ).eq("id", row["id"]).execute()
        return

    # Create new executor record
    display = agent_name or f"Agent {wallet[:6]}...{wallet[-4:]}"
    client.table("executors").insert(
        {
            "wallet_address": wallet_lower,
            "executor_type": "agent",
            "display_name": display,
            "erc8004_agent_id": int(erc8004_agent_id) if erc8004_agent_id else None,
        }
    ).execute()
    logger.info(
        "Auto-registered agent executor: wallet=%s, name=%s", wallet_lower, display
    )


# =============================================================================
# CONFIG ENDPOINTS (PUBLIC)
# =============================================================================


@router.get(
    "/config",
    responses={
        200: {"description": "Public platform configuration"},
    },
    summary="Get Platform Configuration",
    description="Retrieve public platform configuration including bounty limits, supported networks and tokens",
    tags=["Configuration"],
)
async def get_public_config():
    """
    Get public platform configuration.

    Returns publicly available configuration like bounty limits,
    supported payment networks, and tokens. Does not expose
    internal settings like fees or feature flags.
    """
    from ._models import PublicConfigResponse
    from integrations.x402.sdk_client import get_enabled_networks

    enabled = get_enabled_networks()

    require_api_key = os.environ.get("EM_REQUIRE_API_KEY", "false").lower() == "true"

    if CONFIG_AVAILABLE:
        try:
            config = await PlatformConfig.get_public_config()
            return PublicConfigResponse(
                min_bounty_usd=float(config.get("min_usd", 0.25)),
                max_bounty_usd=float(config.get("max_usd", 10000.00)),
                supported_networks=enabled,
                supported_tokens=config.get("supported_tokens", ["USDC"]),
                preferred_network=config.get("preferred_network", "base"),
                require_api_key=require_api_key,
            )
        except Exception as e:
            logger.warning(f"Error loading public config: {e}")

    return PublicConfigResponse(
        min_bounty_usd=0.25,
        max_bounty_usd=10000.00,
        supported_networks=enabled,
        supported_tokens=["USDC", "EURC", "USDT", "PYUSD", "AUSD"],
        preferred_network="base",
        require_api_key=require_api_key,
    )


@router.get(
    "/public/metrics",
    responses={
        200: {"description": "Public platform metrics"},
    },
    summary="Get Platform Metrics",
    description="Retrieve public platform statistics and activity metrics",
    tags=["Public", "Analytics"],
)
async def get_public_platform_metrics():
    """
    Get public platform metrics for landing and dashboard views.

    This endpoint is intentionally read-only and unauthenticated.
    Provides high-level statistics about platform activity.
    """
    from ._models import PublicPlatformMetricsResponse

    generated_at = datetime.now(timezone.utc)
    client = db.get_client()

    users = {
        "registered_workers": 0,
        "registered_agents": 0,
        "workers_with_tasks": 0,
        "workers_active_now": 0,
        "workers_completed": 0,
        "agents_active_now": 0,
    }
    tasks: Dict[str, int] = {
        "total": 0,
        "published": 0,
        "accepted": 0,
        "in_progress": 0,
        "submitted": 0,
        "verifying": 0,
        "completed": 0,
        "disputed": 0,
        "cancelled": 0,
        "expired": 0,
        "live": 0,
    }
    activity = {
        "workers_with_active_tasks": 0,
        "workers_with_completed_tasks": 0,
        "agents_with_live_tasks": 0,
    }
    payments = {
        "total_volume_usd": 0.0,
        "total_fees_usd": 0.0,
    }

    # Registered workers
    try:
        workers_result = client.table("executors").select("id", count="exact").execute()
        users["registered_workers"] = int(workers_result.count or 0)
    except Exception as e:
        logger.warning("Could not query executors count for public metrics: %s", e)

    # Registered agents (active API keys as proxy for active/registered agents)
    try:
        agents_result = (
            client.table("api_keys")
            .select("id", count="exact")
            .eq("is_active", True)
            .execute()
        )
        users["registered_agents"] = int(agents_result.count or 0)
    except Exception as e:
        logger.warning("Could not query agents count for public metrics: %s", e)

    # Task and activity aggregates
    try:
        tasks_result = (
            client.table("tasks")
            .select("status, executor_id, agent_id, bounty_usd")
            .execute()
        )
        task_rows = tasks_result.data or []
        fee_pct = float(await get_platform_fee_percent())

        workers_with_tasks = set()
        workers_active = set()
        workers_completed = set()
        agents_active = set()

        for row in task_rows:
            status = _normalize_status(row.get("status"))
            if not status:
                continue

            tasks[status] = tasks.get(status, 0) + 1
            tasks["total"] += 1
            amount = float(row.get("bounty_usd") or 0.0)
            payments["total_volume_usd"] += amount
            if status == "completed":
                payments["total_fees_usd"] += amount * fee_pct

            executor_id = row.get("executor_id")
            if executor_id:
                workers_with_tasks.add(executor_id)
                if status in ACTIVE_WORKER_TASK_STATUSES:
                    workers_active.add(executor_id)
                if status == "completed":
                    workers_completed.add(executor_id)

            agent_id = row.get("agent_id")
            if agent_id and status in LIVE_TASK_STATUSES:
                agents_active.add(agent_id)

        tasks["live"] = sum(tasks.get(status, 0) for status in LIVE_TASK_STATUSES)
        users["workers_with_tasks"] = len(workers_with_tasks)
        users["workers_active_now"] = len(workers_active)
        users["workers_completed"] = len(workers_completed)
        users["agents_active_now"] = len(agents_active)

        activity["workers_with_active_tasks"] = len(workers_active)
        activity["workers_with_completed_tasks"] = len(workers_completed)
        activity["agents_with_live_tasks"] = len(agents_active)
    except Exception as e:
        logger.warning("Could not query task aggregates for public metrics: %s", e)

    payments["total_volume_usd"] = round(payments["total_volume_usd"], 2)
    payments["total_fees_usd"] = round(payments["total_fees_usd"], 2)

    # Fallback derivation to avoid misleading zero counters in degraded schemas.
    if users["registered_workers"] == 0:
        try:
            submissions_result = (
                client.table("submissions").select("executor_id").execute()
            )
            worker_ids = {
                row.get("executor_id")
                for row in (submissions_result.data or [])
                if row.get("executor_id")
            }
            users["registered_workers"] = len(worker_ids)
        except Exception as e:
            logger.warning(
                "Could not derive registered_workers from submissions fallback: %s", e
            )

    if users["registered_agents"] == 0:
        try:
            tasks_agents_result = client.table("tasks").select("agent_id").execute()
            agent_ids = {
                row.get("agent_id")
                for row in (tasks_agents_result.data or [])
                if row.get("agent_id")
            }
            users["registered_agents"] = len(agent_ids)
        except Exception as e:
            logger.warning(
                "Could not derive registered_agents from tasks fallback: %s", e
            )

    return PublicPlatformMetricsResponse(
        users=users,
        tasks=tasks,
        activity=activity,
        payments=payments,
        generated_at=generated_at,
    )


# =============================================================================
# TASK CRUD
# =============================================================================


@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=201,
    responses={
        201: {"description": "Task created successfully"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request - check bounty limits, network support, or required fields",
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        402: {
            "description": "Payment required. Include X-Payment header with x402 payment authorization."
        },
        429: {
            "model": ErrorResponse,
            "description": "Rate limit exceeded - wait before creating more tasks",
        },
        503: {
            "model": ErrorResponse,
            "description": "x402 payment service unavailable",
        },
    },
    summary="Create Task",
    description="Create a new task with payment escrow (supports preauth, x402r, fase1, and fase2 modes)",
    tags=["Tasks", "Agent"],
)
async def create_task(
    http_request: Request,
    request: CreateTaskRequest,
    auth: AgentAuth = Depends(verify_agent_auth),
) -> TaskResponse:
    """
    Create a new task with automatic payment handling.

    Creates a new task that will be visible to workers. Requires authenticated API key
    and payment authorization via x402 protocol.
    """
    try:
        # Get configurable platform fee
        platform_fee_pct = await get_platform_fee_percent()
        min_bounty = await get_min_bounty()
        max_bounty = await get_max_bounty()

        # Calculate total payment required (bounty + platform fee)
        bounty = Decimal(str(request.bounty_usd))

        # Validate bounty against config limits
        if bounty < min_bounty:
            raise HTTPException(
                status_code=400,
                detail=f"Bounty ${bounty} is below minimum ${min_bounty}",
            )
        if bounty > max_bounty:
            raise HTTPException(
                status_code=400,
                detail=f"Bounty ${bounty} exceeds maximum ${max_bounty}",
            )

        # Validate payment network is enabled
        try:
            from integrations.x402.sdk_client import (
                validate_payment_network,
                validate_payment_token,
                get_enabled_networks,
            )

            validate_payment_network(request.payment_network)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Validate payment token exists on the selected network
        try:
            validate_payment_token(request.payment_network, request.payment_token)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        total_required = bounty * (1 + platform_fee_pct)
        total_required = total_required.quantize(Decimal("0.01"))

        # Verify x402 payment (or balance check for fase1 mode)
        payment_result = None
        x_payment_header = None  # Store original header for later settlement
        if not X402_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="x402 payment service unavailable; task creation is facilitator-only",
            )

        # Get the original X-Payment header before verification
        x_payment_header = http_request.headers.get(
            "X-Payment"
        ) or http_request.headers.get("x-payment")

        # Fase 1/2: X-Payment header is optional (balance check or escrow lock).
        dispatcher = get_payment_dispatcher()
        is_fase1_mode = dispatcher and dispatcher.get_mode() == "fase1"
        is_fase2_mode = dispatcher and dispatcher.get_mode() == "fase2"

        if not x_payment_header and (is_fase1_mode or is_fase2_mode):
            from integrations.x402.sdk_client import TaskPaymentResult

            payment_result = TaskPaymentResult(
                success=True,
                payer_address=auth.agent_id,
                amount_usd=total_required,
                network=request.payment_network or "base",
                timestamp=datetime.now(timezone.utc),
                task_id="pending",
            )
        else:
            payment_result = await verify_x402_payment(http_request, total_required)

        if not payment_result.success:
            return JSONResponse(
                status_code=402,
                content={
                    "error": "Payment required",
                    "message": f"Task creation requires x402 payment of ${total_required} (bounty ${bounty} + {platform_fee_pct * 100}% platform fee)",
                    "required_amount_usd": str(total_required),
                    "bounty_usd": str(bounty),
                    "platform_fee_percent": str(platform_fee_pct * 100),
                    "platform_fee_usd": str(total_required - bounty),
                    "payment_error": payment_result.error,
                    "x402_info": {
                        "facilitator": "https://facilitator.ultravioletadao.xyz",
                        "networks": get_enabled_networks(),
                        "tokens": ["USDC", "EURC", "USDT", "PYUSD"],
                    },
                },
                headers={
                    "X-402-Price": str(total_required),
                    "X-402-Currency": "USD",
                    "X-402-Description": f"Create task: {request.title[:50]}",
                },
            )

        logger.info(
            "x402 payment verified: payer=%s, amount=%.2f, tx=%s",
            payment_result.payer_address,
            payment_result.amount_usd,
            payment_result.tx_hash,
        )

        # ---- ERC-8004 Agent Identity Verification (non-blocking) --------
        erc8004_identity: Optional[Dict[str, Any]] = None
        if ERC8004_IDENTITY_AVAILABLE and verify_agent_identity is not None:
            try:
                erc8004_identity = await verify_agent_identity(
                    auth.agent_id,
                    network="base",
                )
                if erc8004_identity and erc8004_identity.get("registered"):
                    logger.info(
                        "ERC-8004 identity verified for agent %s: agent_id=%s, owner=%s",
                        auth.agent_id,
                        erc8004_identity.get("agent_id"),
                        erc8004_identity.get("owner"),
                    )
                else:
                    logger.warning(
                        "ERC-8004 identity NOT registered for agent %s (network=base). "
                        "Task creation will proceed without on-chain identity.",
                        auth.agent_id,
                    )
            except Exception as e:
                logger.warning(
                    "ERC-8004 identity check failed (non-blocking) for agent %s: %s",
                    auth.agent_id,
                    e,
                )

        # Calculate deadline
        deadline = datetime.now(timezone.utc) + timedelta(hours=request.deadline_hours)

        # Auto-geocode location_hint if no explicit coordinates provided
        location_lat = request.location_lat
        location_lng = request.location_lng
        location_radius_km = None
        if request.location_hint and (location_lat is None or location_lng is None):
            try:
                from integrations.geocoding import geocode_location

                geo = await geocode_location(request.location_hint)
                if geo:
                    location_lat = geo.lat
                    location_lng = geo.lng
                    location_radius_km = geo.radius_km
                    logger.info(
                        "[Task] Auto-geocoded '%s' -> (%s, %s) radius=%skm",
                        request.location_hint,
                        geo.lat,
                        geo.lng,
                        geo.radius_km,
                    )
            except Exception as e:
                logger.warning(
                    "[Task] Geocoding failed for '%s': %s", request.location_hint, e
                )

        # Create task
        task = await db.create_task(
            agent_id=auth.agent_id,
            title=request.title,
            instructions=request.instructions,
            category=request.category.value,
            bounty_usd=request.bounty_usd,
            deadline=deadline,
            evidence_required=[e.value for e in request.evidence_required],
            evidence_optional=[e.value for e in (request.evidence_optional or [])],
            location_hint=request.location_hint,
            min_reputation=request.min_reputation,
            payment_token=request.payment_token,
            payment_network=request.payment_network,
            target_executor_type=request.target_executor.value
            if request.target_executor
            else None,
            skills_required=request.skills_required,
            location_lat=location_lat,
            location_lng=location_lng,
            location_radius_km=location_radius_km,
        )

        # ---- Persist ERC-8004 identity on the task record ---------------
        if erc8004_identity and erc8004_identity.get("registered"):
            try:
                identity_updates: Dict[str, Any] = {}

                resolved_agent_id = erc8004_identity.get("agent_id")
                if resolved_agent_id is not None:
                    identity_updates["erc8004_agent_id"] = str(resolved_agent_id)

                existing_metadata = task.get("metadata") or {}
                if isinstance(existing_metadata, str):
                    existing_metadata = json.loads(existing_metadata)
                existing_metadata["erc8004"] = {
                    "agent_id": resolved_agent_id,
                    "owner": erc8004_identity.get("owner"),
                    "name": erc8004_identity.get("name"),
                    "metadata_uri": erc8004_identity.get("metadata_uri"),
                    "network": erc8004_identity.get("network"),
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                }
                identity_updates["metadata"] = existing_metadata

                if identity_updates:
                    await db.update_task(task["id"], identity_updates)
                    task.update(identity_updates)
                    logger.info(
                        "ERC-8004 identity stored on task %s: agent_id=%s",
                        task["id"],
                        resolved_agent_id,
                    )
            except Exception as e:
                logger.error(
                    "Failed to store ERC-8004 identity on task %s: %s",
                    task["id"],
                    e,
                )

        # Fallback: use agent_name from request if ERC-8004 didn't provide one
        if request.agent_name and not (
            erc8004_identity and erc8004_identity.get("name")
        ):
            try:
                existing_metadata = task.get("metadata") or {}
                if isinstance(existing_metadata, str):
                    existing_metadata = json.loads(existing_metadata)
                existing_metadata["agent_name"] = request.agent_name
                await db.update_task(task["id"], {"metadata": existing_metadata})
                task["metadata"] = existing_metadata
            except Exception:
                pass  # Non-blocking

        # Handle escrow based on payment mode
        is_direct_release = (
            dispatcher
            and is_fase2_mode
            and getattr(dispatcher, "escrow_mode", "platform_release")
            == "direct_release"
        )

        if is_direct_release and payment_result and payment_result.success:
            # Trustless mode: balance check only at creation time.
            try:
                import uuid

                escrow_ref = f"escrow_{task['id'][:8]}_{uuid.uuid4().hex[:8]}"
                payment_reference = f"{X402_AUTH_REF_PREFIX}{uuid.uuid4().hex[:16]}"

                auth_result = await dispatcher.authorize_payment(
                    task_id=task["id"],
                    receiver=auth.agent_id,
                    amount_usdc=total_required,
                    agent_address=auth.agent_id,
                    network=request.payment_network or "base",
                    token=request.payment_token or "USDC",
                    balance_check_only=True,
                )

                escrow_updates = {
                    "escrow_id": escrow_ref,
                    "escrow_tx": payment_reference,
                    "escrow_amount_usdc": float(total_required),
                    "escrow_created_at": datetime.now(timezone.utc).isoformat(),
                }
                await db.update_task(task["id"], escrow_updates)
                task.update(escrow_updates)

                _insert_escrow_record(
                    {
                        "task_id": task["id"],
                        "agent_id": auth.agent_id,
                        "escrow_id": escrow_ref,
                        "funding_tx": None,
                        "status": "pending_assignment",
                        "total_amount_usdc": float(total_required),
                        "platform_fee_usdc": float(total_required - bounty),
                        "beneficiary_address": payment_result.payer_address,
                        "network": request.payment_network or "base",
                        "metadata": {
                            "payment_mode": "fase2",
                            "escrow_mode": "direct_release",
                            "payment_reference": payment_reference,
                            "balance_info": auth_result.get("balance_info"),
                        },
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

                balance_warning = auth_result.get("warning")
                if balance_warning:
                    logger.warning(
                        "trustless balance warning for task %s: %s",
                        task["id"],
                        balance_warning,
                    )
                logger.info(
                    "trustless: Task created with deferred escrow: task=%s, amount=%.2f "
                    "(escrow lock deferred to assignment)",
                    task["id"],
                    float(total_required),
                )
            except Exception as e:
                logger.error(
                    "Error during trustless task creation escrow setup for task %s: %s",
                    task["id"],
                    e,
                )
        # Legacy escrow handling (platform_release or non-fase2 modes)
        elif (
            payment_result
            and payment_result.success
            and (x_payment_header or is_fase1_mode or is_fase2_mode)
        ):
            try:
                import uuid

                escrow_ref = f"escrow_{task['id'][:8]}_{uuid.uuid4().hex[:8]}"
                payment_reference = f"{X402_AUTH_REF_PREFIX}{uuid.uuid4().hex[:16]}"

                dispatcher = get_payment_dispatcher()
                if dispatcher and dispatcher.get_mode() == "fase2":
                    auth_result = await dispatcher.authorize_payment(
                        task_id=task["id"],
                        receiver=auth.agent_id,
                        amount_usdc=bounty,
                        network=request.payment_network or "base",
                        token=request.payment_token or "USDC",
                    )

                    escrow_tx = auth_result.get("tx_hash")
                    escrow_updates = {
                        "escrow_id": escrow_ref,
                        "escrow_tx": escrow_tx or payment_reference,
                        "escrow_amount_usdc": float(total_required),
                        "escrow_created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await db.update_task(task["id"], escrow_updates)
                    task.update(escrow_updates)

                    _insert_escrow_record(
                        {
                            "task_id": task["id"],
                            "agent_id": auth.agent_id,
                            "escrow_id": escrow_ref,
                            "funding_tx": escrow_tx,
                            "status": auth_result.get("escrow_status", "deposited"),
                            "total_amount_usdc": float(total_required),
                            "platform_fee_usdc": float(total_required - bounty),
                            "beneficiary_address": auth_result.get(
                                "payer_address", payment_result.payer_address
                            ),
                            "network": request.payment_network or "base",
                            "metadata": {
                                "payment_mode": "fase2",
                                "payment_reference": payment_reference,
                                "payment_info": auth_result.get(
                                    "payment_info_serialized"
                                ),
                            },
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                    if auth_result.get("success"):
                        logger.info(
                            "fase2 escrow deposited: task=%s, amount=%.2f, tx=%s",
                            task["id"],
                            float(total_required),
                            escrow_tx,
                        )
                    else:
                        escrow_error = auth_result.get("error", "Unknown escrow error")
                        logger.error(
                            "fase2 escrow lock failed for task %s: %s",
                            task["id"],
                            escrow_error,
                        )
                        try:
                            await db.cancel_task(task["id"], auth.agent_id)
                        except Exception:
                            try:
                                await db.update_task(
                                    task["id"], {"status": "cancelled"}
                                )
                            except Exception:
                                pass
                        raise HTTPException(
                            status_code=402,
                            detail=f"Escrow lock failed: {escrow_error}. Task cancelled.",
                        )

                elif dispatcher and dispatcher.get_mode() == "x402r":
                    auth_result = await dispatcher.authorize_payment(
                        task_id=task["id"],
                        receiver=payment_result.payer_address,
                        amount_usdc=total_required,
                        x_payment_header=x_payment_header,
                    )

                    escrow_status = auth_result.get("escrow_status", "failed")
                    escrow_tx = auth_result.get("tx_hash")
                    agent_settle_tx = auth_result.get("agent_settle_tx")

                    escrow_updates = {
                        "escrow_id": escrow_ref,
                        "escrow_tx": escrow_tx or payment_reference,
                        "escrow_amount_usdc": float(total_required),
                        "escrow_created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await db.update_task(task["id"], escrow_updates)
                    task.update(escrow_updates)

                    _insert_escrow_record(
                        {
                            "task_id": task["id"],
                            "agent_id": auth.agent_id,
                            "escrow_id": escrow_ref,
                            "funding_tx": escrow_tx,
                            "status": escrow_status,
                            "total_amount_usdc": float(total_required),
                            "platform_fee_usdc": float(total_required - bounty),
                            "beneficiary_address": auth_result.get(
                                "payer_address", payment_result.payer_address
                            ),
                            "network": payment_result.network,
                            "metadata": {
                                "payment_mode": "x402r",
                                "x_payment_header": x_payment_header,
                                "payment_reference": payment_reference,
                                "agent_settle_tx": agent_settle_tx,
                                "escrow_lock_tx": escrow_tx,
                                "payment_info": auth_result.get(
                                    "payment_info_serialized"
                                ),
                            },
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                    if auth_result.get("success"):
                        logger.info(
                            "x402r escrow deposited: task=%s, escrow=%s, amount=%.2f, "
                            "settle_tx=%s, lock_tx=%s",
                            task["id"],
                            escrow_ref,
                            float(total_required),
                            agent_settle_tx,
                            escrow_tx,
                        )
                    else:
                        escrow_error = auth_result.get("error", "Unknown escrow error")
                        logger.error(
                            "x402r escrow lock failed for task %s: %s",
                            task["id"],
                            escrow_error,
                        )
                        try:
                            await db.cancel_task(task["id"], auth.agent_id)
                        except Exception:
                            try:
                                await db.update_task(
                                    task["id"], {"status": "cancelled"}
                                )
                            except Exception:
                                pass
                        raise HTTPException(
                            status_code=402,
                            detail=f"Payment escrow failed: {escrow_error}. Task has been cancelled.",
                        )
                elif dispatcher and dispatcher.get_mode() == "fase1":
                    auth_result = await dispatcher.authorize_payment(
                        task_id=task["id"],
                        receiver=auth.agent_id,
                        amount_usdc=total_required,
                        network=request.payment_network or "base",
                        token=request.payment_token or "USDC",
                    )

                    escrow_updates = {
                        "escrow_id": escrow_ref,
                        "escrow_tx": payment_reference,
                        "escrow_amount_usdc": float(total_required),
                        "escrow_created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await db.update_task(task["id"], escrow_updates)
                    task.update(escrow_updates)

                    _insert_escrow_record(
                        {
                            "task_id": task["id"],
                            "agent_id": auth.agent_id,
                            "escrow_id": escrow_ref,
                            "funding_tx": None,
                            "status": auth_result.get(
                                "escrow_status", "balance_verified"
                            ),
                            "total_amount_usdc": float(total_required),
                            "platform_fee_usdc": float(total_required - bounty),
                            "beneficiary_address": payment_result.payer_address,
                            "network": payment_result.network,
                            "metadata": {
                                "payment_mode": "fase1",
                                "x_payment_header": x_payment_header,
                                "payment_reference": payment_reference,
                                "balance_info": auth_result.get("balance_info"),
                            },
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                    balance_warning = auth_result.get("warning")
                    if balance_warning:
                        logger.warning(
                            "fase1 balance warning for task %s: %s",
                            task["id"],
                            balance_warning,
                        )
                    logger.info(
                        "fase1 task authorized: task=%s, escrow=%s, amount=%.2f, status=%s",
                        task["id"],
                        escrow_ref,
                        float(total_required),
                        auth_result.get("escrow_status"),
                    )
                else:
                    # preauth: Store header for later settlement
                    escrow_updates = {
                        "escrow_id": escrow_ref,
                        "escrow_tx": payment_reference,
                        "escrow_amount_usdc": float(total_required),
                        "escrow_created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await db.update_task(task["id"], escrow_updates)
                    task.update(escrow_updates)

                    _insert_escrow_record(
                        {
                            "task_id": task["id"],
                            "agent_id": auth.agent_id,
                            "escrow_id": escrow_ref,
                            "funding_tx": None,
                            "status": "authorized",
                            "total_amount_usdc": float(total_required),
                            "platform_fee_usdc": float(total_required - bounty),
                            "beneficiary_address": payment_result.payer_address,
                            "network": payment_result.network,
                            "metadata": {
                                "payment_mode": "preauth",
                                "x_payment_header": x_payment_header,
                                "payment_reference": payment_reference,
                            },
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                    await log_payment_event(
                        task_id=task["id"],
                        event_type="store_auth",
                        status="success",
                        from_address=payment_result.payer_address,
                        amount_usdc=total_required,
                        network=payment_result.network,
                        metadata={"mode": "preauth", "escrow_ref": escrow_ref},
                    )
                    logger.info(
                        "preauth payment authorized: task=%s, escrow=%s, amount=%.2f, payer=%s",
                        task["id"],
                        escrow_ref,
                        float(total_required),
                        payment_result.payer_address[:10] + "...",
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.error("Failed to record escrow for task %s: %s", task["id"], e)

        logger.info(
            "Task created: id=%s, agent=%s, bounty=%.2f, paid_via_x402=%s",
            task["id"],
            auth.agent_id,
            request.bounty_usd,
            X402_AVAILABLE,
        )

        # ---- Auto-register agent in executor directory (non-blocking) ----
        try:
            _auto_register_agent_executor(
                client=db.get_client(),
                wallet=auth.agent_id,
                erc8004_agent_id=erc8004_identity.get("agent_id")
                if erc8004_identity and erc8004_identity.get("registered")
                else None,
                agent_name=erc8004_identity.get("name") if erc8004_identity else None,
            )
        except Exception as e:
            logger.warning("Auto-register agent executor failed (non-blocking): %s", e)

        # Extract agent_name from metadata or ERC-8004 identity
        metadata = task.get("metadata") or {}
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        resolved_agent_name = metadata.get("erc8004", {}).get("name") or metadata.get(
            "agent_name"
        )

        return TaskResponse(
            id=task["id"],
            title=task["title"],
            status=task["status"],
            category=task["category"],
            bounty_usd=task["bounty_usd"],
            deadline=datetime.fromisoformat(task["deadline"].replace("Z", "+00:00")),
            created_at=datetime.fromisoformat(
                task["created_at"].replace("Z", "+00:00")
            ),
            agent_id=task["agent_id"],
            instructions=task["instructions"],
            evidence_schema=task.get("evidence_schema"),
            location_hint=task.get("location_hint"),
            min_reputation=task.get("min_reputation", 0),
            erc8004_agent_id=task.get("erc8004_agent_id"),
            payment_network=task.get("payment_network", "base"),
            payment_token=task.get("payment_token", "USDC"),
            escrow_tx=task.get("escrow_tx"),
            refund_tx=task.get("refund_tx"),
            target_executor_type=task.get("target_executor_type"),
            agent_name=resolved_agent_name,
            skills_required=task.get("required_capabilities"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create task: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail="Internal error while creating task"
        )


@router.get(
    "/tasks/available",
    response_model=AvailableTasksResponse,
    responses={
        200: {"description": "Available tasks retrieved with applied filters"},
        500: {
            "model": ErrorResponse,
            "description": "Failed to retrieve available tasks",
        },
    },
    summary="Get Available Tasks",
    description="Public endpoint for workers to discover available tasks with filtering and pagination",
    tags=["Tasks", "Worker", "Public"],
)
async def get_available_tasks(
    lat: Optional[float] = Query(
        None, ge=-90, le=90, description="Latitude for location filtering"
    ),
    lng: Optional[float] = Query(
        None, ge=-180, le=180, description="Longitude for location filtering"
    ),
    radius_km: int = Query(50, ge=1, le=500, description="Search radius in kilometers"),
    category: Optional[TaskCategory] = Query(None, description="Filter by category"),
    min_bounty: Optional[float] = Query(None, ge=0, description="Minimum bounty USD"),
    max_bounty: Optional[float] = Query(
        None, le=10000, description="Maximum bounty USD"
    ),
    target_executor_type: Optional[str] = Query(
        None,
        description="Filter by executor type: human, agent, or any",
        pattern="^(human|agent|any)$",
    ),
    skills: Optional[str] = Query(
        None,
        description="Comma-separated list of required skills (e.g. photography,local_knowledge). Returns tasks that require ALL listed skills.",
    ),
    after: Optional[datetime] = Query(
        None,
        description="Only return tasks created after this timestamp (ISO 8601). Useful for polling new tasks.",
    ),
    include_expired: bool = Query(
        False,
        description="Include expired tasks in response. Useful as landing fallback when there are no active tasks.",
    ),
    exclude_executor: Optional[str] = Query(
        None,
        description="Executor ID to exclude tasks they already applied to",
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> AvailableTasksResponse:
    """Get available tasks for workers to apply to and complete."""
    try:
        client = db.get_client()

        applied_ids: List[str] = []
        if exclude_executor:
            try:
                applied_result = (
                    client.table("task_applications")
                    .select("task_id")
                    .eq("executor_id", exclude_executor)
                    .execute()
                )
                applied_ids = [r["task_id"] for r in (applied_result.data or [])]
            except Exception:
                pass  # Non-blocking: if lookup fails, show all tasks

        query = client.table("tasks").select("*")

        if include_expired:
            query = query.in_("status", ["published", "expired"])
        else:
            query = query.eq("status", "published")

        if category:
            query = query.eq("category", category.value)

        if min_bounty is not None:
            query = query.gte("bounty_usd", min_bounty)
        if max_bounty is not None:
            query = query.lte("bounty_usd", max_bounty)

        if target_executor_type:
            query = query.eq("target_executor_type", target_executor_type)

        if skills:
            skill_list = [s.strip().lower() for s in skills.split(",") if s.strip()]
            if skill_list:
                query = query.contains("required_capabilities", skill_list)

        if after:
            query = query.gte("created_at", after.isoformat())

        if applied_ids:
            query = query.not_.in_("id", applied_ids)

        result = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        tasks_raw = result.data or []

        # Strip PII / internal fields from public worker-facing response
        _pii_fields = {"executor_id", "human_wallet"}
        tasks = [
            {k: v for k, v in t.items() if k not in _pii_fields} for t in tasks_raw
        ]

        filters_applied = {
            "category": category.value if category else None,
            "min_bounty": min_bounty,
            "max_bounty": max_bounty,
            "target_executor_type": target_executor_type,
            "skills": skills,
            "after": after.isoformat() if after else None,
            "include_expired": include_expired,
            "location": {"lat": lat, "lng": lng, "radius_km": radius_km}
            if lat and lng
            else None,
        }

        return AvailableTasksResponse(
            tasks=tasks,
            count=len(tasks),
            offset=offset,
            filters_applied={k: v for k, v in filters_applied.items() if v is not None},
        )

    except Exception as e:
        logger.error("Failed to get available tasks: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to get available tasks")


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    responses={
        200: {"description": "Task details retrieved successfully"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to view this task",
        },
        404: {"model": ErrorResponse, "description": "Task not found"},
    },
    summary="Get Task Details",
    description="Retrieve detailed information about a specific task. Owners can see all their tasks. Other agents can see published/accepted/in_progress tasks.",
    tags=["Tasks", "Agent"],
)
async def get_task(
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    auth: AgentAuth = Depends(verify_agent_auth),
) -> TaskResponse:
    """Get detailed information about a specific task."""
    task = await db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Ownership: match by agent_id OR wallet_address (EIP-8128 resolves
    # agent_id to ERC-8004 token ID, but DB stores wallet address)
    is_owner = task["agent_id"] == auth.agent_id or (
        getattr(auth, "wallet_address", None)
        and task["agent_id"] == auth.wallet_address
    )
    task_status = _normalize_status(task.get("status"))
    public_statuses = {"published", "accepted", "in_progress", "submitted", "completed"}

    if not is_owner and task_status not in public_statuses:
        raise HTTPException(status_code=403, detail="Not authorized to view this task")

    # Extract agent_name from metadata or ERC-8004 identity
    metadata = task.get("metadata") or {}
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    resolved_agent_name = metadata.get("erc8004", {}).get("name") or metadata.get(
        "agent_name"
    )

    # Resolve payment_tx from submission or payment_events for completed tasks
    resolved_payment_tx: Optional[str] = None
    if _normalize_status(task.get("status")) == "completed":
        try:
            client = db.get_client()
            # Strategy 1: submission.payment_tx (set by _record_submission_paid_fields)
            sub_result = (
                client.table("submissions")
                .select("payment_tx")
                .eq("task_id", task["id"])
                .not_.is_("payment_tx", "null")
                .limit(1)
                .execute()
            )
            if sub_result.data and sub_result.data[0].get("payment_tx"):
                resolved_payment_tx = sub_result.data[0]["payment_tx"]
            else:
                # Strategy 2: payment_events table (escrow_release, settle_worker_direct, etc.)
                pe_result = (
                    client.table("payment_events")
                    .select("tx_hash")
                    .eq("task_id", task["id"])
                    .in_(
                        "event_type",
                        [
                            "settle_worker_direct",
                            "escrow_release",
                            "h2a_settle_worker",
                            "disburse_worker",
                        ],
                    )
                    .not_.is_("tx_hash", "null")
                    .limit(1)
                    .execute()
                )
                if pe_result.data and pe_result.data[0].get("tx_hash"):
                    resolved_payment_tx = pe_result.data[0]["tx_hash"]
        except Exception as ptx_err:
            logger.warning(
                "Could not resolve payment_tx for task %s: %s",
                task["id"],
                ptx_err,
            )

    return TaskResponse(
        id=task["id"],
        title=task["title"],
        status=task["status"],
        category=task["category"],
        bounty_usd=task["bounty_usd"],
        deadline=datetime.fromisoformat(task["deadline"].replace("Z", "+00:00")),
        created_at=datetime.fromisoformat(task["created_at"].replace("Z", "+00:00")),
        agent_id=task["agent_id"],
        executor_id=task.get("executor_id"),
        instructions=task["instructions"],
        evidence_schema=task.get("evidence_schema"),
        location_hint=task.get("location_hint"),
        min_reputation=task.get("min_reputation", 0),
        erc8004_agent_id=task.get("erc8004_agent_id"),
        payment_network=task.get("payment_network", "base"),
        payment_token=task.get("payment_token", "USDC"),
        escrow_tx=task.get("escrow_tx"),
        refund_tx=task.get("refund_tx"),
        target_executor_type=task.get("target_executor_type"),
        agent_name=resolved_agent_name,
        skills_required=task.get("required_capabilities"),
        payment_tx=resolved_payment_tx,
    )


@router.get(
    "/tasks/{task_id}/applications",
    response_model=ApplicationListResponse,
    responses={
        200: {"description": "Applications for this task"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized - only the task publisher can view applications",
        },
        404: {"model": ErrorResponse, "description": "Task not found"},
    },
    summary="Get Task Applications",
    description="List all applications submitted by workers for a task. Only the task publisher can view applications.",
    tags=["Tasks", "Agent"],
)
async def get_task_applications(
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    auth: AgentAuth = Depends(verify_agent_auth),
) -> ApplicationListResponse:
    """Get all applications for a task. Only the task publisher can view."""
    task = await db.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Ownership: match by agent_id OR wallet_address (EIP-8128 resolves
    # agent_id to ERC-8004 token ID, but DB stores wallet address)
    is_owner = task["agent_id"] == auth.agent_id or (
        getattr(auth, "wallet_address", None)
        and task["agent_id"] == auth.wallet_address
    )
    if not is_owner:
        raise HTTPException(
            status_code=403,
            detail="Not authorized - only the task publisher can view applications",
        )

    try:
        client = db.get_client()
        result = (
            client.table("task_applications")
            .select("id, task_id, executor_id, message, status, created_at")
            .eq("task_id", task_id)
            .order("created_at", desc=False)
            .execute()
        )
        applications = result.data or []

        return ApplicationListResponse(
            applications=[
                ApplicationResponse(
                    id=app["id"],
                    task_id=app["task_id"],
                    executor_id=app["executor_id"],
                    message=app.get("message"),
                    status=app.get("status", "pending"),
                    created_at=app["created_at"],
                )
                for app in applications
            ],
            count=len(applications),
        )
    except Exception as e:
        logger.error("Failed to get applications for task %s: %s", task_id, str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve applications")


@router.get(
    "/tasks/{task_id}/payment",
    response_model=TaskPaymentResponse,
    responses={
        200: {"description": "Payment timeline and status retrieved successfully"},
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to view payment details for draft tasks",
        },
        404: {"model": ErrorResponse, "description": "Task not found"},
        500: {
            "model": ErrorResponse,
            "description": "Failed to resolve task payment information",
        },
    },
    summary="Get Task Payment Timeline",
    description="Retrieve complete payment history and current status for a task",
    tags=["Tasks", "Payments", "Escrow"],
)
async def get_task_payment(
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    auth: AgentAuth = Depends(verify_agent_auth),
) -> TaskPaymentResponse:
    """Get comprehensive payment timeline and status for a specific task."""
    try:
        task = await db.get_task(task_id)
    except Exception as task_err:
        if _is_not_found_error(task_err):
            task = None
        else:
            logger.warning(
                "Failed to load task %s for payment endpoint: %s", task_id, task_err
            )
            raise HTTPException(
                status_code=500, detail="Failed to resolve task payment"
            )

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task_status = _normalize_status(task.get("status"))
    requester_is_owner = bool(
        auth
        and (
            task.get("agent_id") == auth.agent_id
            or (auth.wallet_address and task.get("agent_id") == auth.wallet_address)
        )
    )
    if task_status == "draft" and not requester_is_owner:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view draft task payment details",
        )

    client = db.get_client()
    payment_rows: List[Dict[str, Any]] = []
    escrows_row: Optional[Dict[str, Any]] = None
    submission_payment_row: Optional[Dict[str, Any]] = None

    try:
        payment_result = (
            client.table("payments")
            .select("*")
            .eq("task_id", task_id)
            .order("created_at", desc=False)
            .execute()
        )
        payment_rows = payment_result.data or []
    except Exception as payment_err:
        if not _is_missing_table_error(payment_err, "payments"):
            logger.warning(
                "Failed to query payments for task %s: %s", task_id, payment_err
            )

    try:
        escrows_result = (
            client.table("escrows")
            .select("*")
            .eq("task_id", task_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        escrows_rows = escrows_result.data or []
        if escrows_rows:
            escrows_row = escrows_rows[0]
    except Exception as escrow_err:
        if not _is_missing_table_error(escrow_err, "escrows"):
            logger.warning(
                "Failed to query escrows for task %s: %s", task_id, escrow_err
            )

    try:
        submission_result = (
            client.table("submissions")
            .select("id,payment_tx,payment_amount,paid_at,verified_at,submitted_at")
            .eq("task_id", task_id)
            .not_("payment_tx", "is", "null")
            .order("submitted_at", desc=True)
            .limit(1)
            .execute()
        )
        submission_rows = submission_result.data or []
        if submission_rows:
            submission_payment_row = submission_rows[0]
    except Exception as submission_err:
        if not _is_missing_table_error(submission_err, "submissions"):
            logger.warning(
                "Failed to query submission payment fallback for task %s: %s",
                task_id,
                submission_err,
            )

    default_network = "base"
    created_at = str(task.get("created_at") or datetime.now(timezone.utc).isoformat())
    updated_at = str(task.get("updated_at") or created_at)
    events: List[Dict[str, Any]] = []
    total_amount = _as_amount(task.get("bounty_usd"))
    released_amount = 0.0

    for index, row in enumerate(payment_rows):
        event_type = _event_type_from_payment_row(row)
        amount = _as_amount(
            row.get("amount_usdc")
            or row.get("amount")
            or row.get("total_amount_usdc")
            or row.get("net_amount_usdc")
            or row.get("released_amount_usdc")
            or row.get("released_amount")
        )
        status = _normalize_status(row.get("status"))
        if event_type == "escrow_created":
            total_amount = max(total_amount, amount)
        if (
            event_type in {"partial_release", "final_release"}
            and status in TASK_PAYMENT_SETTLED_STATUSES
        ):
            released_amount += amount

        event_timestamp = str(
            row.get("completed_at")
            or row.get("confirmed_at")
            or row.get("updated_at")
            or row.get("created_at")
            or updated_at
        )
        updated_at = max(updated_at, event_timestamp)

        network = _normalize_payment_network(row, default_network)
        tx_hash = _pick_first_tx_hash(
            row.get("tx_hash"),
            row.get("transaction_hash"),
            row.get("release_tx"),
            row.get("refund_tx"),
            row.get("deposit_tx"),
            row.get("funding_tx"),
        )
        note = _sanitize_reference(
            row.get("tx_hash")
            or row.get("transaction_hash")
            or row.get("deposit_tx")
            or row.get("funding_tx")
        )

        events.append(
            {
                "id": f"{row.get('id') or task_id}-{event_type}-{index}",
                "type": event_type,
                "actor": _actor_from_event_type(event_type),
                "amount": amount if amount > 0 else None,
                "tx_hash": tx_hash,
                "network": network,
                "timestamp": event_timestamp,
                "note": note,
            }
        )

    has_escrow_context = bool(
        task.get("escrow_id") or task.get("escrow_tx") or escrows_row
    )
    if has_escrow_context and not any(
        event["type"] in {"escrow_created", "escrow_funded"} for event in events
    ):
        escrow_amount = _as_amount(
            (escrows_row or {}).get("total_amount_usdc")
            or (escrows_row or {}).get("amount_usdc")
            or task.get("bounty_usd")
        )
        total_amount = max(total_amount, escrow_amount)

        escrow_timestamp = str(
            (escrows_row or {}).get("created_at")
            or task.get("created_at")
            or created_at
        )
        updated_at = max(updated_at, escrow_timestamp)
        escrow_tx_hash = _pick_first_tx_hash(
            (escrows_row or {}).get("deposit_tx"),
            (escrows_row or {}).get("funding_tx"),
            task.get("escrow_tx"),
        )
        escrow_reference = _sanitize_reference(task.get("escrow_tx"))
        events.append(
            {
                "id": f"{task_id}-escrow-created-fallback",
                "type": "escrow_created",
                "actor": "agent",
                "amount": escrow_amount if escrow_amount > 0 else None,
                "tx_hash": escrow_tx_hash,
                "network": default_network,
                "timestamp": escrow_timestamp,
                "note": escrow_reference,
            }
        )

    submission_tx = _pick_first_tx_hash(
        (submission_payment_row or {}).get("payment_tx")
    )
    if submission_tx and not any(
        event["type"] == "final_release" and event.get("tx_hash") == submission_tx
        for event in events
    ):
        submission_amount = _as_amount(
            (submission_payment_row or {}).get("payment_amount")
        )
        if submission_amount <= 0:
            submission_amount = total_amount
        released_amount = max(released_amount, submission_amount)
        total_amount = max(total_amount, submission_amount)

        payout_timestamp = str(
            (submission_payment_row or {}).get("paid_at")
            or (submission_payment_row or {}).get("verified_at")
            or (submission_payment_row or {}).get("submitted_at")
            or updated_at
        )
        updated_at = max(updated_at, payout_timestamp)
        events.append(
            {
                "id": f"{task_id}-submission-payout-{(submission_payment_row or {}).get('id') or 'latest'}",
                "type": "final_release",
                "actor": "system",
                "amount": submission_amount if submission_amount > 0 else None,
                "tx_hash": submission_tx,
                "network": default_network,
                "timestamp": payout_timestamp,
                "note": "Payment settled via x402 facilitator",
            }
        )

    # Inject refund event
    refund_tx_from_task = _pick_first_tx_hash(task.get("refund_tx"))
    if refund_tx_from_task and not any(
        event["type"] == "refund" and event.get("tx_hash") == refund_tx_from_task
        for event in events
    ):
        refund_timestamp = str(task.get("updated_at") or updated_at)
        events.append(
            {
                "id": f"{task_id}-refund-task",
                "type": "refund",
                "actor": "system",
                "amount": total_amount if total_amount > 0 else None,
                "tx_hash": refund_tx_from_task,
                "network": default_network,
                "timestamp": refund_timestamp,
                "note": "Escrow refunded to agent via facilitator",
            }
        )

    # For cancelled tasks without refund_tx
    if (
        task_status == "cancelled"
        and has_escrow_context
        and not refund_tx_from_task
        and not any(
            event["type"] in {"refund", "authorization_expired"} for event in events
        )
    ):
        cancel_timestamp = str(task.get("updated_at") or updated_at)
        events.append(
            {
                "id": f"{task_id}-auth-expired",
                "type": "authorization_expired",
                "actor": "system",
                "amount": None,
                "tx_hash": None,
                "network": default_network,
                "timestamp": cancel_timestamp,
                "note": "Payment authorization expired. No funds were moved.",
            }
        )

    events.sort(key=lambda event: event.get("timestamp") or "")

    if (
        _normalize_status(task.get("status")) == "completed"
        and released_amount <= 0
        and total_amount > 0
    ):
        released_amount = total_amount

    derived_status = _derive_payment_status(
        task_status=task_status,
        has_escrow_context=has_escrow_context,
        event_types=[event["type"] for event in events],
    )

    if not events:
        updated_at = str(task.get("updated_at") or task.get("created_at") or updated_at)

    return TaskPaymentResponse(
        task_id=task_id,
        status=derived_status,
        total_amount=round(total_amount, 6),
        released_amount=round(released_amount, 6),
        currency="USDC",
        escrow_tx=_pick_first_tx_hash(
            (escrows_row or {}).get("deposit_tx"),
            (escrows_row or {}).get("funding_tx"),
            task.get("escrow_tx"),
        ),
        escrow_contract=None,
        network=default_network,
        events=[TaskPaymentEventResponse(**event) for event in events],
        created_at=created_at,
        updated_at=updated_at,
    )


@router.get(
    "/tasks/{task_id}/transactions",
    response_model=TaskTransactionsResponse,
    responses={
        200: {"description": "Transaction history retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Task not found"},
    },
    summary="Get Task Transaction History",
    description="Retrieve chronological on-chain transaction history for a task from the payment_events audit trail",
    tags=["Tasks", "Payments"],
)
async def get_task_transactions(
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    auth: AgentAuth = Depends(verify_agent_auth),
) -> TaskTransactionsResponse:
    """Get all on-chain transactions for a task, ordered chronologically."""
    try:
        task = await db.get_task(task_id)
    except Exception as task_err:
        if _is_not_found_error(task_err):
            task = None
        else:
            raise HTTPException(status_code=500, detail="Failed to load task")

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    client = db.get_client()

    try:
        pe_result = (
            client.table("payment_events")
            .select("*")
            .eq("task_id", task_id)
            .order("created_at", desc=False)
            .execute()
        )
        pe_rows = pe_result.data or []
    except Exception as pe_err:
        logger.warning(
            "Failed to query payment_events for task %s: %s", task_id, pe_err
        )
        pe_rows = []

    default_network = task.get("payment_network") or "base"

    transactions: List[Dict[str, Any]] = []
    total_locked = 0.0
    total_released = 0.0
    total_refunded = 0.0
    fee_collected = 0.0

    for row in pe_rows:
        event_type = row.get("event_type", "unknown")
        amount = float(row.get("amount_usdc") or 0)
        status = row.get("status", "pending")
        tx_hash = row.get("tx_hash")
        network = row.get("network") or default_network

        if status == "success":
            if event_type in ("escrow_authorize",):
                total_locked += amount
            elif event_type in (
                "escrow_release",
                "settle_worker_direct",
                "disburse_worker",
                "settle",
            ):
                total_released += amount
            elif event_type in ("escrow_refund", "refund"):
                total_refunded += amount
            elif event_type in (
                "settle_fee_direct",
                "disburse_fee",
                "fee_collect",
            ):
                fee_collected += amount

        transactions.append(
            {
                "id": row.get("id", ""),
                "event_type": event_type,
                "tx_hash": tx_hash,
                "amount_usdc": amount if amount > 0 else None,
                "from_address": row.get("from_address"),
                "to_address": row.get("to_address"),
                "network": network,
                "token": row.get("token", "USDC"),
                "status": status,
                "explorer_url": _build_explorer_url(tx_hash, network),
                "label": _TX_EVENT_LABELS.get(event_type, event_type),
                "timestamp": str(row.get("created_at", "")),
                "metadata": row.get("metadata"),
            }
        )

    # Inject reputation events from task metadata
    existing_tx_hashes = {t["tx_hash"] for t in transactions if t.get("tx_hash")}

    try:
        escrows_result = (
            client.table("escrows")
            .select("metadata")
            .eq("task_id", task_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        escrow_meta = (
            (escrows_result.data[0].get("metadata") or {})
            if escrows_result.data
            else {}
        )
    except Exception:
        escrow_meta = {}

    for rep_key, rep_event_type in [
        ("reputation_agent_tx", "reputation_agent_rates_worker"),
        ("reputation_worker_tx", "reputation_worker_rates_agent"),
    ]:
        rep_tx = escrow_meta.get(rep_key)
        if rep_tx and rep_tx not in existing_tx_hashes:
            transactions.append(
                {
                    "id": f"{task_id}-{rep_event_type}",
                    "event_type": rep_event_type,
                    "tx_hash": rep_tx,
                    "amount_usdc": None,
                    "from_address": None,
                    "to_address": None,
                    "network": default_network,
                    "token": "USDC",
                    "status": "success",
                    "explorer_url": _build_explorer_url(rep_tx, default_network),
                    "label": _TX_EVENT_LABELS.get(rep_event_type, rep_event_type),
                    "timestamp": str(task.get("updated_at", "")),
                    "metadata": None,
                }
            )

    transactions.sort(key=lambda t: t.get("timestamp") or "")

    return TaskTransactionsResponse(
        task_id=task_id,
        transactions=[TransactionEventResponse(**t) for t in transactions],
        total_count=len(transactions),
        summary={
            "total_locked": round(total_locked, 6),
            "total_released": round(total_released, 6),
            "total_refunded": round(total_refunded, 6),
            "fee_collected": round(fee_collected, 6),
        },
    )


@router.get(
    "/tasks",
    response_model=TaskListResponse,
    responses={
        200: {"description": "Tasks retrieved successfully with pagination info"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
    },
    summary="List Agent Tasks",
    description="Retrieve paginated list of tasks for the authenticated agent with filtering options",
    tags=["Tasks", "Agent"],
)
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    category: Optional[TaskCategory] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    auth: AgentAuth = Depends(verify_agent_auth),
) -> TaskListResponse:
    """List tasks for the authenticated agent with filtering and pagination."""
    result = await db.get_tasks(
        agent_id=auth.agent_id,
        status=status.value if status else None,
        category=category.value if category else None,
        limit=limit,
        offset=offset,
    )

    tasks = []
    for task in result.get("tasks", []):
        tasks.append(
            TaskResponse(
                id=task["id"],
                title=task["title"],
                status=task["status"],
                category=task["category"],
                bounty_usd=task["bounty_usd"],
                deadline=datetime.fromisoformat(
                    task["deadline"].replace("Z", "+00:00")
                ),
                created_at=datetime.fromisoformat(
                    task["created_at"].replace("Z", "+00:00")
                ),
                agent_id=task["agent_id"],
                executor_id=task.get("executor_id"),
                min_reputation=task.get("min_reputation", 0),
                erc8004_agent_id=task.get("erc8004_agent_id"),
                payment_network=task.get("payment_network", "base"),
                payment_token=task.get("payment_token", "USDC"),
                escrow_tx=task.get("escrow_tx"),
                refund_tx=task.get("refund_tx"),
            )
        )

    return TaskListResponse(
        tasks=tasks,
        total=result["total"],
        count=result["count"],
        offset=offset,
        has_more=result["has_more"],
    )


# =============================================================================
# CANCEL
# =============================================================================


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=SuccessResponse,
    responses={
        200: {
            "description": "Task cancelled successfully with appropriate refund handling"
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to cancel this task",
        },
        404: {"model": ErrorResponse, "description": "Task not found"},
        409: {
            "model": ErrorResponse,
            "description": "Task cannot be cancelled in current status",
        },
        402: {
            "model": ErrorResponse,
            "description": "Escrow refund failed - task cancelled but manual refund required",
        },
    },
    summary="Cancel Task",
    description="Cancel a published task and handle payment refunds based on escrow status",
    tags=["Tasks", "Agent", "Payments"],
)
async def cancel_task(
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    request: CancelRequest = None,
    auth: AgentAuth = Depends(verify_agent_auth),
) -> SuccessResponse:
    """Cancel a task and handle payment refunds automatically."""
    refund_info = None
    try:
        reason = request.reason if request else None

        task = await db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        is_owner = task.get("agent_id") == auth.agent_id or (
            getattr(auth, "wallet_address", None)
            and task.get("agent_id") == auth.wallet_address
        )
        if not is_owner:
            raise HTTPException(
                status_code=403, detail="Not authorized to cancel this task"
            )

        task_status = _normalize_status(task.get("status"))
        if task_status == "cancelled":
            return SuccessResponse(
                message="Task already cancelled.",
                data={"task_id": task_id, "reason": reason, "idempotent": True},
            )

        dispatcher = get_payment_dispatcher()
        is_direct_release_cancel = (
            dispatcher
            and dispatcher.get_mode() == "fase2"
            and getattr(dispatcher, "escrow_mode", "platform_release")
            == "direct_release"
        )
        cancellable_statuses = {"published"}
        if is_direct_release_cancel:
            cancellable_statuses.add("accepted")

        if task_status not in cancellable_statuses:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Cannot cancel task in '{task_status}' status. "
                    f"Only {', '.join(sorted(cancellable_statuses))} tasks can be cancelled."
                ),
            )

        escrow_tx = task.get("escrow_tx")
        escrow_id = task.get("escrow_id")

        if escrow_tx:
            try:
                client = db.get_client()
                escrow_row = None
                try:
                    escrow_result = (
                        client.table("escrows")
                        .select(
                            "id,status,escrow_id,refunded_at,released_at,metadata,beneficiary_address"
                        )
                        .eq("task_id", task_id)
                        .single()
                        .execute()
                    )
                    escrow_row = escrow_result.data or None
                except Exception:
                    escrow_row = None

                escrow_status = _normalize_status(
                    (escrow_row or {}).get("status") or "authorized"
                )
                effective_escrow_id = (escrow_row or {}).get("escrow_id") or escrow_id

                if escrow_status in ALREADY_REFUNDED_ESCROW_STATUSES:
                    refund_info = {
                        "status": "already_refunded",
                        "escrow_id": effective_escrow_id,
                    }
                elif escrow_status in NON_REFUNDABLE_ESCROW_STATUSES:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Cannot cancel task because escrow is already {escrow_status}",
                    )
                elif escrow_status in REFUNDABLE_ESCROW_STATUSES:
                    dispatcher = get_payment_dispatcher()
                    if dispatcher:
                        escrow_meta = (escrow_row or {}).get("metadata") or {}
                        if isinstance(escrow_meta, str):
                            escrow_meta = json.loads(escrow_meta)
                        is_trustless_escrow = (
                            escrow_meta.get("escrow_mode") == "direct_release"
                        )

                        agent_address = None
                        try:
                            agent_address = (escrow_row or {}).get(
                                "beneficiary_address"
                            )
                            if not agent_address:
                                agent_address = escrow_meta.get(
                                    "beneficiary_address"
                                ) or _extract_agent_wallet_from_header(
                                    escrow_meta.get("x_payment_header")
                                )
                        except Exception:
                            pass

                        if is_trustless_escrow:
                            refund_result = await dispatcher.refund_trustless_escrow(
                                task_id=task_id,
                                reason=reason,
                            )
                        else:
                            refund_result = await dispatcher.refund_payment(
                                task_id=task_id,
                                escrow_id=str(effective_escrow_id or ""),
                                reason=reason,
                                agent_address=agent_address,
                            )
                        if refund_result.get("success"):
                            refund_tx_hash = refund_result.get("tx_hash")
                            refund_info = {
                                "status": "refunded",
                                "escrow_id": effective_escrow_id,
                                "tx_hash": refund_tx_hash,
                                "method": refund_result.get("mode", "unknown"),
                            }
                            if refund_tx_hash:
                                try:
                                    client.table("tasks").update(
                                        {
                                            "refund_tx": refund_tx_hash,
                                        }
                                    ).eq("id", task_id).execute()
                                except Exception as task_update_err:
                                    logger.warning(
                                        "Could not store refund_tx on task %s: %s",
                                        task_id,
                                        task_update_err,
                                    )
                            try:
                                client.table("escrows").update(
                                    {
                                        "status": "refunded",
                                        "refund_tx": refund_tx_hash,
                                        "refunded_at": datetime.now(
                                            timezone.utc
                                        ).isoformat(),
                                    }
                                ).eq("task_id", task_id).execute()
                            except Exception as escrow_update_err:
                                logger.warning(
                                    "Could not mark escrow refunded for task %s: %s",
                                    task_id,
                                    escrow_update_err,
                                )
                            _record_refund_payment(
                                task=task,
                                agent_id=auth.agent_id,
                                refund_tx=refund_tx_hash,
                                reason=reason,
                                settlement_method=refund_result.get("mode"),
                            )
                        else:
                            refund_info = {
                                "status": "refund_manual_required",
                                "escrow_id": effective_escrow_id,
                                "error": refund_result.get(
                                    "error", "Refund attempt failed"
                                ),
                            }
                    elif X402_AVAILABLE:
                        sdk = get_sdk()
                        refund_result = await sdk.refund_task_payment(
                            task_id=task_id,
                            escrow_id=str(effective_escrow_id or ""),
                            reason=reason,
                        )
                        if refund_result.get("success"):
                            refund_tx_hash = refund_result.get("tx_hash")
                            refund_info = {
                                "status": "refunded",
                                "escrow_id": effective_escrow_id,
                                "tx_hash": refund_tx_hash,
                                "method": refund_result.get("method", "unknown"),
                            }
                        else:
                            refund_info = {
                                "status": "refund_manual_required",
                                "escrow_id": effective_escrow_id,
                                "error": refund_result.get(
                                    "error", "Refund attempt failed"
                                ),
                            }
                    else:
                        refund_info = {
                            "status": "refund_manual_required",
                            "escrow_id": effective_escrow_id,
                            "error": "x402 SDK not available",
                        }
                elif escrow_status == "failed":
                    escrow_meta = (escrow_row or {}).get("metadata") or {}
                    if isinstance(escrow_meta, str):
                        escrow_meta = json.loads(escrow_meta)
                    agent_settle_tx = escrow_meta.get("agent_settle_tx")
                    if agent_settle_tx:
                        refund_info = {
                            "status": "refund_manual_required",
                            "escrow_id": effective_escrow_id,
                            "agent_settle_tx": agent_settle_tx,
                            "error": (
                                "Funds were settled from agent wallet but escrow lock "
                                "failed. Manual refund required. Settlement tx: "
                                f"{agent_settle_tx}"
                            ),
                        }
                        logger.error(
                            "FUND LOSS DETECTED: task=%s, agent_settle_tx=%s — "
                            "escrow lock failed after settlement. Manual refund required.",
                            task_id,
                            agent_settle_tx,
                        )
                        await log_payment_event(
                            task_id=task_id,
                            event_type="error",
                            status="failed",
                            tx_hash=agent_settle_tx,
                            error="FUND LOSS: escrow lock failed after agent settlement",
                            metadata={
                                "escrow_status": escrow_status,
                                "requires_manual_refund": True,
                            },
                        )
                    else:
                        refund_info = {
                            "status": "authorization_expired",
                            "message": "Escrow failed but no funds were moved. Authorization will expire.",
                        }
                elif escrow_status in PENDING_ASSIGNMENT_ESCROW_STATUSES:
                    refund_info = {
                        "status": "no_escrow_locked",
                        "message": "Escrow was not yet locked (pre-assignment). No funds to refund.",
                    }
                elif escrow_status in AUTHORIZE_ONLY_ESCROW_STATUSES:
                    refund_info = {
                        "status": "authorization_expired",
                        "message": "Payment authorization will expire. No funds were moved.",
                    }
                else:
                    logger.warning(
                        "Unknown escrow status '%s' for task %s, attempting refund",
                        escrow_status,
                        task_id,
                    )
                    if X402_AVAILABLE:
                        try:
                            sdk = get_sdk()
                            refund_result = await sdk.refund_task_payment(
                                task_id=task_id,
                                escrow_id=str(effective_escrow_id or ""),
                                reason=reason,
                            )
                            if refund_result.get("success"):
                                refund_tx_hash = refund_result.get("tx_hash")
                                refund_info = {
                                    "status": "refunded",
                                    "escrow_id": effective_escrow_id,
                                    "tx_hash": refund_tx_hash,
                                    "method": refund_result.get("method", "unknown"),
                                }
                                if refund_tx_hash:
                                    try:
                                        client.table("tasks").update(
                                            {
                                                "refund_tx": refund_tx_hash,
                                            }
                                        ).eq("id", task_id).execute()
                                    except Exception:
                                        pass
                                _record_refund_payment(
                                    task=task,
                                    agent_id=auth.agent_id,
                                    refund_tx=refund_tx_hash,
                                    reason=reason,
                                    settlement_method=refund_result.get("method"),
                                )
                            else:
                                refund_info = {
                                    "status": "refund_manual_required",
                                    "escrow_id": effective_escrow_id,
                                    "error": refund_result.get(
                                        "error", "Unknown status, refund failed"
                                    ),
                                }
                        except Exception as refund_err:
                            logger.warning(
                                "Refund attempt failed for task %s: %s",
                                task_id,
                                refund_err,
                            )
                            refund_info = {
                                "status": "authorization_expired",
                                "message": "Could not determine escrow state. Authorization will expire.",
                            }
                    else:
                        refund_info = {
                            "status": "authorization_expired",
                            "message": "Payment authorization will expire. No funds were moved.",
                        }

            except HTTPException:
                raise
            except Exception as escrow_err:
                logger.warning(
                    "Could not check/update escrow for task %s: %s", task_id, escrow_err
                )

        # Cancel the task in database
        try:
            await db.cancel_task(task_id, auth.agent_id)
        except Exception as cancel_err:
            cancel_error = str(cancel_err).lower()
            if (
                "status: cancelled" not in cancel_error
                and "already cancelled" not in cancel_error
            ):
                raise

        logger.info(
            "Task cancelled: id=%s, agent=%s, reason=%s, escrow=%s",
            task_id,
            auth.agent_id,
            reason,
            refund_info,
        )

        response_data = {"task_id": task_id, "reason": reason}
        if refund_info:
            response_data["escrow"] = refund_info

        status_label = (refund_info or {}).get("status")
        message_suffix = ""
        if status_label == "authorization_expired":
            message_suffix = " Payment authorization expired (no funds moved)."
        elif status_label == "refunded":
            message_suffix = " Escrow refunded to agent."
        elif status_label == "already_refunded":
            message_suffix = " Escrow was already refunded."
        elif status_label == "not_refundable":
            message_suffix = " Escrow was already released."
        elif status_label in {"refund_manual_required", "refund_failed"}:
            message_suffix = " Escrow refund requires manual intervention."

        return SuccessResponse(
            message=f"Task cancelled successfully.{message_suffix}", data=response_data
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail="Task not found")
        elif "not authorized" in error_msg.lower():
            raise HTTPException(status_code=403, detail=error_msg)
        elif "cannot cancel" in error_msg.lower() or "status" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg)
        logger.error("Unexpected error cancelling task %s: %s", task_id, error_msg)
        raise HTTPException(
            status_code=500, detail="Internal error while cancelling task"
        )


# =============================================================================
# ANALYTICS
# =============================================================================


@router.get(
    "/analytics",
    responses={
        200: {"description": "Analytics data retrieved successfully"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
    },
    summary="Get Agent Analytics",
    description="Comprehensive analytics dashboard data for the authenticated agent",
    tags=["Analytics", "Agent"],
)
async def get_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    auth: AgentAuth = Depends(verify_agent_auth),
):
    """Get comprehensive analytics for the authenticated agent."""
    from ._models import AnalyticsResponse

    result = await db.get_agent_analytics(
        agent_id=auth.agent_id,
        days=days,
    )

    return AnalyticsResponse(
        totals=result["totals"],
        by_status=result["by_status"],
        by_category=result["by_category"],
        average_times=result["average_times"],
        top_workers=result["top_workers"],
        period_days=result["period_days"],
    )


# =============================================================================
# ASSIGN
# =============================================================================


@router.post(
    "/tasks/{task_id}/assign",
    response_model=SuccessResponse,
    responses={
        200: {"description": "Task successfully assigned to worker"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to assign this task or worker ineligible",
        },
        404: {"model": ErrorResponse, "description": "Task or executor not found"},
        409: {
            "model": ErrorResponse,
            "description": "Task not assignable in current status",
        },
    },
    summary="Assign Task to Worker",
    description="Assign a published task to a specific worker executor",
    tags=["Tasks", "Agent"],
)
async def assign_task_to_worker(
    task_id: str = Path(..., description="UUID of the task", pattern=UUID_PATTERN),
    request: WorkerAssignRequest = ...,
    auth: AgentAuth = Depends(verify_agent_auth),
) -> SuccessResponse:
    """Assign a published task to a specific worker executor."""
    try:
        result = await db.assign_task(
            task_id=task_id,
            agent_id=auth.agent_id,
            executor_id=request.executor_id,
            notes=request.notes,
        )

        task = result.get("task", {})
        executor = result.get("executor", {})
        worker_wallet = executor.get("wallet_address")

        # --- Trustless escrow lock at assignment time ---
        escrow_data = {}
        dispatcher = get_payment_dispatcher()
        is_direct_release = (
            dispatcher
            and dispatcher.get_mode() == "fase2"
            and getattr(dispatcher, "escrow_mode", "platform_release")
            == "direct_release"
        )

        if is_direct_release and worker_wallet:
            try:
                bounty = Decimal(str(task.get("bounty_usd", 0)))
                network = task.get("payment_network") or "base"
                token = "USDC"
                agent_address = task.get("agent_id", auth.agent_id)

                try:
                    client = db.get_client()
                    esc_row = (
                        client.table("escrows")
                        .select("beneficiary_address")
                        .eq("task_id", task_id)
                        .limit(1)
                        .execute()
                    )
                    if esc_row.data:
                        agent_address = esc_row.data[0].get(
                            "beneficiary_address", agent_address
                        )
                except Exception:
                    pass

                if bounty > 0:
                    auth_result = await dispatcher.authorize_escrow_for_worker(
                        task_id=task_id,
                        agent_address=agent_address,
                        worker_address=worker_wallet,
                        bounty_usdc=bounty,
                        network=network,
                        token=token,
                    )

                    if auth_result.get("success"):
                        escrow_tx = auth_result.get("tx_hash")
                        escrow_metadata = {
                            "payment_mode": "fase2",
                            "escrow_mode": "direct_release",
                            "payment_info": auth_result.get("payment_info_serialized"),
                            "worker_address": worker_wallet,
                            "fee_method": auth_result.get(
                                "fee_method", "on_chain_fee_calculator"
                            ),
                        }
                        try:
                            client = db.get_client()
                            upd = (
                                client.table("escrows")
                                .update(
                                    {
                                        "status": "deposited",
                                        "funding_tx": escrow_tx,
                                        "metadata": escrow_metadata,
                                    }
                                )
                                .eq("task_id", task_id)
                                .execute()
                            )
                            # If no row was updated, insert one
                            if not upd.data:
                                _insert_escrow_record(
                                    {
                                        "task_id": task_id,
                                        "escrow_id": task.get(
                                            "escrow_id",
                                            f"escrow_{task_id[:8]}",
                                        ),
                                        "funding_tx": escrow_tx,
                                        "status": "deposited",
                                        "total_amount_usdc": float(bounty),
                                        "platform_fee_usdc": float(
                                            bounty * Decimal("0.13")
                                        ),
                                        "metadata": escrow_metadata,
                                        "created_at": datetime.now(
                                            timezone.utc
                                        ).isoformat(),
                                    }
                                )

                            await db.update_task(
                                task_id,
                                {
                                    "escrow_tx": escrow_tx,
                                    "escrow_amount_usdc": float(
                                        Decimal(
                                            str(
                                                auth_result.get(
                                                    "lock_amount_usdc", bounty
                                                )
                                            )
                                        )
                                    ),
                                },
                            )
                        except Exception as db_err:
                            logger.warning(
                                "Could not update escrow record for task %s: %s",
                                task_id,
                                db_err,
                            )

                        escrow_data = {
                            "escrow_tx": escrow_tx,
                            "escrow_status": "deposited",
                            "escrow_mode": "direct_release",
                            "fee_method": auth_result.get(
                                "fee_method", "on_chain_fee_calculator"
                            ),
                            "bounty_locked": str(bounty),
                            "fee_model": "credit_card",
                        }
                        logger.info(
                            "trustless: Escrow locked at assignment: task=%s, "
                            "worker=%s, tx=%s",
                            task_id,
                            worker_wallet[:10],
                            escrow_tx,
                        )
                    else:
                        escrow_error = auth_result.get("error", "Unknown escrow error")
                        logger.error(
                            "trustless: Escrow lock failed at assignment for "
                            "task %s: %s",
                            task_id,
                            escrow_error,
                        )
                        try:
                            await db.update_task(
                                task_id,
                                {
                                    "status": "published",
                                    "executor_id": None,
                                    "assigned_at": None,
                                },
                            )
                        except Exception:
                            pass
                        raise HTTPException(
                            status_code=402,
                            detail=(
                                f"Escrow lock failed during assignment: {escrow_error}. "
                                "Task remains published."
                            ),
                        )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    "trustless: Error during escrow lock at assignment for task %s: %s",
                    task_id,
                    e,
                )

        logger.info(
            "Task assigned: task=%s, agent=%s, executor=%s",
            task_id,
            auth.agent_id[:10],
            request.executor_id[:10],
        )

        # Non-blocking webhook dispatch
        try:
            from webhooks.events import WebhookEventType

            await dispatch_webhook(
                WebhookEventType.TASK_ASSIGNED,
                {
                    "task_id": task_id,
                    "executor_id": request.executor_id,
                    "agent_id": auth.agent_id,
                    "worker_wallet": worker_wallet,
                },
            )
        except Exception:
            pass  # Never block the assign flow

        response_data = {
            "task_id": task_id,
            "executor_id": request.executor_id,
            "status": task.get("status", "accepted"),
            "assigned_at": task.get("assigned_at"),
            "worker_wallet": worker_wallet,
        }
        if escrow_data:
            response_data["escrow"] = escrow_data

        return SuccessResponse(
            message="Task assigned successfully",
            data=response_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        lowered = error_msg.lower()
        if "not found" in lowered:
            if "executor" in lowered:
                raise HTTPException(status_code=404, detail="Executor not found")
            raise HTTPException(status_code=404, detail="Task not found")
        elif "not authorized" in lowered:
            raise HTTPException(
                status_code=403, detail="Not authorized to assign this task"
            )
        elif "cannot be assigned" in lowered or "status" in lowered:
            raise HTTPException(status_code=409, detail=error_msg)
        elif "insufficient reputation" in lowered:
            raise HTTPException(status_code=403, detail=error_msg)
        logger.error("Unexpected error assigning task %s: %s", task_id, error_msg)
        raise HTTPException(
            status_code=500, detail="Internal error while assigning task"
        )


# =============================================================================
# BATCH
# =============================================================================


@router.post(
    "/tasks/batch",
    response_model=BatchCreateResponse,
    status_code=201,
    responses={
        201: {"description": "Batch tasks created with success/failure breakdown"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request or too many tasks in batch",
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - invalid or missing API key",
        },
    },
    summary="Batch Create Tasks",
    description="Create multiple similar tasks in a single API call for efficiency",
    tags=["Tasks", "Agent", "Batch"],
)
async def batch_create_tasks(
    request: BatchCreateRequest,
    auth: AgentAuth = Depends(verify_agent_auth),
) -> BatchCreateResponse:
    """Create multiple tasks in a single request for efficiency."""
    created_tasks = []
    errors = []
    total_bounty = 0.0

    for i, task_def in enumerate(request.tasks):
        try:
            deadline = datetime.now(timezone.utc) + timedelta(
                hours=task_def.deadline_hours
            )

            task = await db.create_task(
                agent_id=auth.agent_id,
                title=task_def.title,
                instructions=task_def.instructions,
                category=task_def.category.value,
                bounty_usd=task_def.bounty_usd,
                deadline=deadline,
                evidence_required=[e.value for e in task_def.evidence_required],
                evidence_optional=[e.value for e in (task_def.evidence_optional or [])],
                location_hint=task_def.location_hint,
                min_reputation=task_def.min_reputation,
                payment_token=request.payment_token,
                payment_network=getattr(request, "payment_network", "base"),
            )

            created_tasks.append(
                {
                    "index": i,
                    "id": task["id"],
                    "title": task["title"],
                    "bounty_usd": task["bounty_usd"],
                }
            )
            total_bounty += task_def.bounty_usd

        except Exception as e:
            errors.append(
                {
                    "index": i,
                    "title": task_def.title,
                    "error": str(e),
                }
            )

    logger.info(
        "Batch create: agent=%s, created=%d, failed=%d, total_bounty=%.2f",
        auth.agent_id,
        len(created_tasks),
        len(errors),
        total_bounty,
    )

    return BatchCreateResponse(
        created=len(created_tasks),
        failed=len(errors),
        tasks=created_tasks,
        errors=errors,
        total_bounty=total_bounty,
    )
