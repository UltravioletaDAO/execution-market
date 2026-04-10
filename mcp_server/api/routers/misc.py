"""
Evidence verification, worker identity, auth, and health endpoints.

Extracted from api/routes.py.
"""

import ipaddress
import os
import uuid as _uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Path, Request

import supabase_client as db
from verification.ai_review import (
    verify_with_ai,
    VerificationDecision,
)

from ..auth import verify_agent_auth, AgentAuth

from ._models import (
    VerifyEvidenceRequest,
    VerifyEvidenceResponse,
    IdentityCheckResponse,
    RegisterIdentityRequest,
    RegisterIdentityResponse,
    ConfirmIdentityRequest,
    ErrorResponse,
)

from ._helpers import (
    logger,
    UUID_PATTERN,
    _is_valid_eth_address,
)

# Import worker identity functions (non-blocking)
try:
    from integrations.erc8004.identity import (
        check_worker_identity,
        build_worker_registration_tx,
        confirm_worker_registration,
        update_executor_identity,
        WorkerIdentityStatus,
    )

    WORKER_IDENTITY_AVAILABLE = True
except ImportError:
    WORKER_IDENTITY_AVAILABLE = False

router = APIRouter(prefix="/api/v1", tags=["Misc"])


# =============================================================================
# EVIDENCE URL HOST ALLOWLIST (SSRF defense)
# Phase 0 GR-0.4 — see docs/reports/security-audit-2026-04-07/specialists/SC_05_BACKEND_API.md [API-004]
# =============================================================================


def _derive_allowed_evidence_hosts() -> frozenset[str]:
    """
    Build the host allowlist for evidence URL fetching.

    Always includes our own domains. Pulls additional hosts from env vars so
    Supabase Storage + the evidence CloudFront distribution are honored in
    whichever environment the server runs in.
    """
    hosts: set[str] = {
        "execution.market",
        "api.execution.market",
        "cdn.execution.market",  # CloudFront for evidence S3
        "mcp.execution.market",
    }

    # Derive Supabase Storage host from SUPABASE_URL (e.g. https://abcxyz.supabase.co)
    supabase_url = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL")
    if supabase_url:
        try:
            parsed = urlparse(supabase_url)
            if parsed.hostname:
                hosts.add(parsed.hostname)
        except Exception:
            pass

    # Evidence CDN host (EVIDENCE_PUBLIC_BASE_URL points at the CloudFront dist)
    evidence_base = os.environ.get("EVIDENCE_PUBLIC_BASE_URL")
    if evidence_base:
        try:
            parsed = urlparse(evidence_base)
            if parsed.hostname:
                hosts.add(parsed.hostname)
        except Exception:
            pass

    # Evidence S3 bucket direct access (e.g. my-bucket.s3.us-east-2.amazonaws.com)
    evidence_bucket = os.environ.get("EVIDENCE_BUCKET")
    region = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")
    if evidence_bucket:
        hosts.add(f"{evidence_bucket}.s3.{region}.amazonaws.com")
        hosts.add(f"{evidence_bucket}.s3.amazonaws.com")

    # Optional additional allowed hosts from env (comma-separated)
    extra = os.environ.get("EM_EVIDENCE_ALLOWED_HOSTS", "")
    for host in extra.split(","):
        host = host.strip()
        if host:
            hosts.add(host)

    return frozenset(hosts)


ALLOWED_EVIDENCE_HOSTS: frozenset[str] = _derive_allowed_evidence_hosts()

# Cap response body to prevent memory exhaustion by a redirector that serves
# a huge payload once the URL passes host validation.
MAX_EVIDENCE_BYTES = 10 * 1024 * 1024  # 10 MB


def _validate_evidence_url(url: str) -> None:
    """
    Validate a caller-supplied evidence URL before fetching it.

    Defenses:
      - https only (blocks http://, file://, gopher://, etc.)
      - Hostname must be in ALLOWED_EVIDENCE_HOSTS
      - Reject raw IP addresses (SSRF defense-in-depth)

    Raises HTTPException(400) on any violation.
    """
    if not url or not isinstance(url, str):
        raise HTTPException(status_code=400, detail="Invalid evidence_url")

    try:
        parsed = urlparse(url)
    except Exception as e:
        logger.warning("Invalid evidence_url: %s", e)
        raise HTTPException(
            status_code=400, detail="Invalid evidence_url format"
        ) from e

    if parsed.scheme != "https":
        raise HTTPException(
            status_code=400,
            detail="evidence_url must use https",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=400, detail="evidence_url is missing a hostname"
        )

    # Block raw IP addresses — defense in depth even if the IP happened to
    # be in the allowlist (it shouldn't be).
    try:
        ipaddress.ip_address(hostname)
        raise HTTPException(
            status_code=400,
            detail="evidence_url cannot be a raw IP address",
        )
    except ValueError:
        pass  # Not an IP — good.

    # Hostname allowlist (case-insensitive)
    if hostname.lower() not in {h.lower() for h in ALLOWED_EVIDENCE_HOSTS}:
        logger.warning(
            "SECURITY_AUDIT action=evidence.verify.host_blocked host=%s url=%s",
            hostname,
            url[:200],
        )
        raise HTTPException(
            status_code=400,
            detail=(
                f"evidence_url host not in allowlist: {hostname}. "
                "Upload evidence through the /evidence/presign-upload flow."
            ),
        )


# =============================================================================
# EVIDENCE VERIFICATION
# =============================================================================


@router.post(
    "/evidence/verify",
    response_model=VerifyEvidenceResponse,
    responses={
        200: {
            "description": "AI verification result with confidence score and decision"
        },
        400: {"model": ErrorResponse, "description": "Invalid evidence URL"},
        401: {"model": ErrorResponse, "description": "Unauthenticated"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        413: {"model": ErrorResponse, "description": "Evidence too large"},
        503: {
            "model": ErrorResponse,
            "description": "AI verification service unavailable",
        },
    },
    summary="Verify Evidence with AI",
    description="Pre-verify submitted evidence against task requirements using AI vision models",
    tags=["Evidence", "AI", "Worker"],
)
async def verify_evidence(
    request: VerifyEvidenceRequest,
    # TODO: switch to verify_agent_auth_write after Track A lands.
    # Phase 0 GR-0.4 — closes API-004 (endpoint was unauthenticated).
    auth: AgentAuth = Depends(verify_agent_auth),
) -> VerifyEvidenceResponse:
    """
    Verify evidence against task requirements using AI vision models.

    Worker-facing endpoint for pre-verification of evidence before submission.
    Uses AI vision models to analyze uploaded evidence and provide instant feedback
    on whether it meets the task requirements.

    Security (Phase 0 GR-0.4):
      - Requires authenticated caller (ERC-8128 wallet signature).
      - evidence_url MUST be https and its hostname MUST be in
        ALLOWED_EVIDENCE_HOSTS (blocks SSRF into AWS metadata, RDS, etc.).
      - The downstream AI verifier fetches with follow_redirects=False
        and caps the response body to MAX_EVIDENCE_BYTES.
    """
    from ..verification_helpers import get_verifier

    # Reject anonymous/unauthenticated callers even if the global auth dep
    # allows anonymous access on read endpoints. This endpoint is write-ish:
    # it triggers AI spend and (before the fix) was an SSRF vector.
    if auth.auth_method == "anonymous":
        logger.warning(
            "SECURITY_AUDIT action=evidence.verify.unauth path=/evidence/verify"
        )
        raise HTTPException(
            status_code=401,
            detail=(
                "Authentication required. Sign the request with ERC-8128 "
                "(Signature + Signature-Input headers)."
            ),
        )

    # Validate the URL BEFORE any network I/O. Blocks SSRF into internal
    # services (AWS metadata, RDS, VPC endpoints, ECS task metadata, ...).
    _validate_evidence_url(request.evidence_url)

    # Get task details
    task = await db.get_task(request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    verifier = get_verifier()

    if not verifier.is_available:
        logger.info(
            "AI verification unavailable (no provider configured): task=%s",
            request.task_id,
        )
        return VerifyEvidenceResponse(
            verified=True,
            confidence=0.5,
            decision="approved",
            explanation=f"Evidence received for '{task.get('title', 'task')}'. AI verification not configured — accepted for agent review.",
            issues=[],
        )

    try:
        result = await verify_with_ai(
            task={
                "title": task.get("title", ""),
                "category": task.get("category", "general"),
                "instructions": task.get("instructions", ""),
                "evidence_schema": task.get("evidence_schema", {}),
            },
            evidence={
                "type": request.evidence_type,
                "notes": "",
            },
            photo_urls=[request.evidence_url],
        )

        return VerifyEvidenceResponse(
            verified=result.decision == VerificationDecision.APPROVED,
            confidence=result.confidence,
            decision=result.decision.value,
            explanation=result.explanation,
            issues=result.issues,
        )

    except Exception as e:
        logger.warning("AI verification error for task %s: %s", request.task_id, e)
        return VerifyEvidenceResponse(
            verified=True,
            confidence=0.5,
            decision="approved",
            explanation="AI verification temporarily unavailable. Evidence accepted for agent review.",
            issues=[],
        )


# =============================================================================
# WORKER IDENTITY (ERC-8004)
# =============================================================================


@router.get(
    "/executors/{executor_id}/identity",
    response_model=IdentityCheckResponse,
    responses={
        200: {"description": "Identity status retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Executor not found"},
        503: {"model": ErrorResponse, "description": "Identity service unavailable"},
    },
    summary="Check Worker Identity",
    description="Check worker's ERC-8004 on-chain identity registration status",
    tags=["Workers", "Identity", "ERC-8004"],
)
async def get_worker_identity(
    executor_id: str = Path(
        ..., description="UUID of the executor", pattern=UUID_PATTERN
    ),
) -> IdentityCheckResponse:
    """
    Check a worker's ERC-8004 on-chain identity registration status.

    Queries the ERC-8004 Identity Registry on Base Mainnet to determine
    whether the worker's wallet address holds a registered identity token.
    """
    if not WORKER_IDENTITY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Worker identity service not available",
        )

    # Look up executor
    try:
        client = db.get_client()
        result = (
            client.table("executors")
            .select("id, wallet_address, erc8004_agent_id")
            .eq("id", executor_id)
            .execute()
        )
    except Exception as e:
        logger.error("Failed to look up executor %s: %s", executor_id, e)
        raise HTTPException(status_code=500, detail="Database error")

    if not result.data:
        raise HTTPException(status_code=404, detail="Executor not found")

    executor = result.data[0]
    wallet = executor.get("wallet_address")

    if not wallet or not _is_valid_eth_address(wallet):
        raise HTTPException(
            status_code=400,
            detail="Executor has no valid wallet address",
        )

    # Check if we already have the agent_id cached in Supabase
    cached_agent_id = executor.get("erc8004_agent_id")
    if cached_agent_id is not None:
        return IdentityCheckResponse(
            status="registered",
            agent_id=cached_agent_id,
            wallet_address=wallet,
        )

    # Check on-chain
    try:
        identity = await check_worker_identity(wallet)
    except Exception as e:
        logger.error("Identity check failed for executor %s: %s", executor_id, e)
        return IdentityCheckResponse(
            status="error",
            wallet_address=wallet,
            error=str(e),
        )

    # If registered, persist the agent_id in Supabase
    if identity.status == WorkerIdentityStatus.REGISTERED and identity.agent_id:
        try:
            await update_executor_identity(executor_id, identity.agent_id)
        except Exception as e:
            logger.warning(
                "Failed to persist agent_id for executor %s: %s", executor_id, e
            )

    return IdentityCheckResponse(
        status=identity.status.value,
        agent_id=identity.agent_id,
        wallet_address=identity.wallet_address,
        network=identity.network,
        chain_id=identity.chain_id,
        registry_address=identity.registry_address,
        error=identity.error,
    )


@router.post(
    "/executors/{executor_id}/register-identity",
    response_model=RegisterIdentityResponse,
    responses={
        200: {"description": "Registration transaction prepared or already registered"},
        400: {
            "model": ErrorResponse,
            "description": "Executor has no valid wallet address",
        },
        404: {"model": ErrorResponse, "description": "Executor not found"},
        503: {
            "model": ErrorResponse,
            "description": "Identity service unavailable or registration tx preparation failed",
        },
    },
    summary="Prepare Identity Registration",
    description="Prepare ERC-8004 identity registration transaction for worker wallet to sign",
    tags=["Workers", "Identity", "ERC-8004"],
)
async def register_worker_identity(
    executor_id: str = Path(
        ..., description="UUID of the executor", pattern=UUID_PATTERN
    ),
    request: RegisterIdentityRequest = RegisterIdentityRequest(),
) -> RegisterIdentityResponse:
    """
    Prepare an ERC-8004 identity registration transaction for a worker.

    Creates an unsigned transaction that the worker's wallet must sign and submit
    to register their on-chain identity. If already registered, returns existing
    identity information.
    """
    if not WORKER_IDENTITY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Worker identity service not available",
        )

    # Look up executor
    try:
        client = db.get_client()
        result = (
            client.table("executors")
            .select("id, wallet_address, erc8004_agent_id")
            .eq("id", executor_id)
            .execute()
        )
    except Exception as e:
        logger.error("Failed to look up executor %s: %s", executor_id, e)
        raise HTTPException(status_code=500, detail="Database error")

    if not result.data:
        raise HTTPException(status_code=404, detail="Executor not found")

    executor = result.data[0]
    wallet = executor.get("wallet_address")

    if not wallet or not _is_valid_eth_address(wallet):
        raise HTTPException(
            status_code=400,
            detail="Executor has no valid wallet address",
        )

    # Check current on-chain status
    try:
        identity = await check_worker_identity(wallet)
    except Exception as e:
        req_id = str(_uuid.uuid4())[:8]
        logger.error(
            "Identity check failed for %s [req=%s]: %s", executor_id, req_id, e
        )
        raise HTTPException(
            status_code=503,
            detail=f"Could not check on-chain identity (ref: {req_id})",
        )

    # Already registered
    if identity.status == WorkerIdentityStatus.REGISTERED:
        # Persist if not already saved
        if identity.agent_id and not executor.get("erc8004_agent_id"):
            try:
                await update_executor_identity(executor_id, identity.agent_id)
            except Exception:
                pass

        return RegisterIdentityResponse(
            status="registered",
            agent_id=identity.agent_id,
            transaction=None,
            message=f"Worker already registered with agent ID {identity.agent_id}",
        )

    # Build registration tx
    try:
        tx_data = await build_worker_registration_tx(
            wallet_address=wallet,
            agent_uri=request.agent_uri,
        )
    except Exception as e:
        req_id = str(_uuid.uuid4())[:8]
        logger.error(
            "Failed to build registration tx for %s [req=%s]: %s",
            executor_id,
            req_id,
            e,
        )
        raise HTTPException(
            status_code=503,
            detail=f"Could not prepare registration transaction (ref: {req_id})",
        )

    logger.info(
        "Registration tx prepared: executor=%s, wallet=%s, chain=%d, gas=%s",
        executor_id,
        wallet[:10],
        tx_data.chain_id,
        tx_data.estimated_gas,
    )

    return RegisterIdentityResponse(
        status="not_registered",
        agent_id=None,
        transaction=tx_data.to_dict(),
        message="Sign and submit this transaction to register your on-chain identity",
    )


@router.post(
    "/executors/{executor_id}/confirm-identity",
    response_model=IdentityCheckResponse,
    responses={
        200: {"description": "Registration confirmed"},
        404: {"model": ErrorResponse, "description": "Executor not found"},
        503: {"model": ErrorResponse, "description": "Identity service unavailable"},
    },
    tags=["Workers", "Identity"],
)
async def confirm_identity_registration(
    executor_id: str = Path(
        ..., description="UUID of the executor", pattern=UUID_PATTERN
    ),
    request: ConfirmIdentityRequest = ...,
) -> IdentityCheckResponse:
    """
    Confirm a worker's identity registration after the transaction is mined.

    After the worker signs and submits the registration tx, the frontend
    calls this endpoint with the tx hash. The backend re-checks the on-chain
    state and stores the agent ID if registration succeeded.
    """
    if not WORKER_IDENTITY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Worker identity service not available",
        )

    # Look up executor
    try:
        client = db.get_client()
        result = (
            client.table("executors")
            .select("id, wallet_address")
            .eq("id", executor_id)
            .execute()
        )
    except Exception as e:
        logger.error("Failed to look up executor %s: %s", executor_id, e)
        raise HTTPException(status_code=500, detail="Database error")

    if not result.data:
        raise HTTPException(status_code=404, detail="Executor not found")

    executor = result.data[0]
    wallet = executor.get("wallet_address")

    if not wallet or not _is_valid_eth_address(wallet):
        raise HTTPException(
            status_code=400,
            detail="Executor has no valid wallet address",
        )

    # Confirm on-chain
    try:
        identity = await confirm_worker_registration(wallet, request.tx_hash)
    except Exception as e:
        logger.error("Identity confirmation failed for %s: %s", executor_id, e)
        return IdentityCheckResponse(
            status="error",
            wallet_address=wallet,
            error=str(e),
        )

    # Persist agent_id if registered
    if identity.status == WorkerIdentityStatus.REGISTERED and identity.agent_id:
        try:
            await update_executor_identity(executor_id, identity.agent_id)
        except Exception as e:
            logger.warning("Failed to persist agent_id for %s: %s", executor_id, e)

    logger.info(
        "Identity confirmation: executor=%s, status=%s, agent_id=%s, tx=%s",
        executor_id,
        identity.status.value,
        identity.agent_id,
        request.tx_hash,
    )

    return IdentityCheckResponse(
        status=identity.status.value,
        agent_id=identity.agent_id,
        wallet_address=identity.wallet_address,
        network=identity.network,
        chain_id=identity.chain_id,
        registry_address=identity.registry_address,
        error=identity.error,
    )


# =============================================================================
# ERC-8128 AUTH ENDPOINTS
# =============================================================================


@router.get(
    "/auth/nonce",
    responses={
        200: {"description": "Fresh nonce for ERC-8128 authentication"},
    },
    summary="Get Authentication Nonce",
    description="Generate a fresh single-use nonce for ERC-8128 wallet-based authentication",
    tags=["Authentication"],
)
async def get_auth_nonce(request: Request):
    """
    Generate a fresh nonce for ERC-8128 authentication.

    The nonce must be included in the Signature-Input `nonce` parameter
    when signing requests with ERC-8128. Each nonce is single-use and
    expires after 5 minutes.
    """
    from ..auth import generate_auth_nonce

    return await generate_auth_nonce(request)


@router.get(
    "/auth/erc8128/nonce",
    responses={
        200: {"description": "Fresh nonce for ERC-8128 request signing"},
    },
    summary="Get ERC-8128 Nonce",
    description="Generate a fresh nonce for EIP-8128 request signing (alias for /auth/nonce)",
    tags=["Authentication"],
)
async def get_erc8128_nonce(request: Request):
    """Generate a fresh nonce for EIP-8128 request signing."""
    from ..auth import generate_auth_nonce

    return await generate_auth_nonce(request)


@router.get(
    "/auth/erc8128/info",
    responses={
        200: {"description": "ERC-8128 authentication configuration"},
    },
    summary="ERC-8128 Auth Info",
    description="Get ERC-8128 authentication configuration (supported chains, policy, nonce TTL)",
    tags=["Authentication"],
)
async def get_erc8128_info():
    """
    Get ERC-8128 authentication configuration.

    Helps agents discover ERC-8128 support and understand the server's
    verification policy.
    """
    return {
        "supported": True,
        "version": "ERC-8128 Draft",
        "supported_chains": [1, 8453, 11155111, 84532],
        "signing": {
            "algorithm": "EIP-191 personal_sign",
            "signature_format": "base64 (RFC 8941 byte sequence)",
            "covered_components": [
                "@method",
                "@authority",
                "@path",
                "@query",
                "content-digest",
            ],
            "content_digest": "sha-256 (RFC 9530)",
            "label": "eth",
            "keyid_format": "erc8128:{chain_id}:{address}",
        },
        "policy": {
            "max_validity_sec": 300,
            "clock_skew_sec": 30,
            "require_request_bound": True,
            "require_nonce": True,
        },
        "nonce_endpoint": "/api/v1/auth/erc8128/nonce",
        "erc8004_cross_reference": True,
        "documentation": "https://eip.tools/eip/8128",
    }


# =============================================================================
# HEALTH & INFO ENDPOINTS
# =============================================================================


@router.get(
    "/health",
    responses={
        200: {"description": "API is healthy and operational"},
        503: {"description": "API is unhealthy or degraded"},
    },
    summary="Health Check",
    description="System health check endpoint for monitoring and load balancers",
    tags=["System"],
)
async def api_health():
    """
    API health check endpoint.

    Provides system health status for monitoring, load balancers, and uptime checks.
    """
    return {
        "status": "healthy",
        "api_version": "v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/agent-info",
    summary="Dynamic Agent Info",
    description="Live agent metadata with real-time stats. Enriches static agent-card.json with DB stats.",
    tags=["System"],
)
async def agent_info():
    """
    Dynamic agent info endpoint — combines static agent-card.json metadata
    with live platform statistics from the database.
    """
    from config.platform_config import get_platform_config

    config = get_platform_config()

    # Live stats from DB
    stats = {
        "tasks_completed": 0,
        "tasks_published": 0,
        "active_workers": 0,
        "total_volume_usd": 0.0,
    }
    try:
        result = (
            db.client.table("tasks")
            .select("id", count="exact")
            .eq("status", "completed")
            .execute()
        )
        stats["tasks_completed"] = result.count or 0

        result = db.client.table("tasks").select("id", count="exact").execute()
        stats["tasks_published"] = result.count or 0

        result = (
            db.client.table("executors")
            .select("id", count="exact")
            .eq("status", "active")
            .execute()
        )
        stats["active_workers"] = result.count or 0
    except Exception:
        pass  # Stats are best-effort, endpoint still returns metadata

    # Enabled networks from config
    enabled_networks = config.get("payments", {}).get(
        "enabled_networks",
        [
            "base",
            "ethereum",
            "polygon",
            "arbitrum",
            "celo",
            "monad",
            "avalanche",
            "optimism",
            "skale",
        ],
    )

    return {
        "name": "Execution Market",
        "tagline": "Universal Execution Layer — humans today, robots tomorrow",
        "version": "2.0.0",
        "agent_id": 2106,
        "network": "base",
        "identity": {
            "standard": "ERC-8004",
            "agent_id": 2106,
            "registry": "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
            "reputation_registry": "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
        },
        "protocols": {
            "a2a": "https://api.execution.market/.well-known/agent.json",
            "mcp": "https://mcp.execution.market/mcp/",
            "rest": "https://api.execution.market/api/v1",
            "websocket": "wss://api.execution.market/ws",
            "docs": "https://api.execution.market/docs",
        },
        "payment": {
            "networks": enabled_networks,
            "tokens": ["USDC", "EURC", "PYUSD", "AUSD", "USDT"],
            "protocol": "x402",
            "gasless": True,
            "fee_percent": config.get("payments", {}).get("platform_fee_percent", 13),
            "minimum_bounty_usd": 0.01,
        },
        "stats": stats,
        "skills": [
            {
                "name": "publish_task",
                "description": "Publish a bounty for real-world execution",
            },
            {
                "name": "verify_evidence",
                "description": "AI-powered evidence verification (photo, GPS, EXIF)",
            },
            {
                "name": "manage_escrow",
                "description": "x402r on-chain escrow (lock, release, refund)",
            },
            {
                "name": "track_reputation",
                "description": "Bidirectional on-chain reputation (ERC-8004)",
            },
            {
                "name": "register_identity",
                "description": "Gasless ERC-8004 identity registration (15 networks)",
            },
            {
                "name": "manage_workers",
                "description": "Worker discovery, assignment, and lifecycle",
            },
            {
                "name": "batch_operations",
                "description": "Bulk task creation and management",
            },
        ],
        "task_categories": [
            "physical_presence",
            "knowledge_access",
            "human_authority",
            "simple_action",
            "digital_physical",
            "location_based",
            "verification",
            "social_proof",
            "data_collection",
            "sensory",
            "social",
            "proxy",
            "bureaucratic",
            "emergency",
            "creative",
            "data_processing",
            "api_integration",
            "content_generation",
            "code_execution",
            "research",
            "multi_step_workflow",
        ],
        "links": {
            "dashboard": "https://execution.market",
            "github": "https://github.com/UltravioletaDAO/execution-market",
            "dao": "https://ultravioletadao.xyz",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/skills",
    summary="Agent Skills",
    description="Machine-readable skill descriptors for agent discovery.",
    tags=["System"],
)
async def agent_skills():
    """
    Agent skill descriptors following the open standard for agent capabilities.

    Each skill maps to one or more MCP tools / REST endpoints that implement it.
    """
    return {
        "agent": "Execution Market",
        "agent_id": 2106,
        "version": "1.0",
        "skills": [
            {
                "id": "publish_task",
                "name": "Publish Task",
                "description": "Publish a bounty for real-world execution by humans or robots",
                "mcp_tools": ["em_publish_task"],
                "rest_endpoint": "POST /api/v1/tasks",
                "input_schema": {
                    "required": ["title", "description", "category", "bounty_usdc"],
                    "optional": [
                        "deadline_minutes",
                        "location",
                        "evidence_schema",
                        "payment_network",
                    ],
                },
                "output": "task_id, status, escrow_tx (if applicable)",
                "trust_level": "api_key",
            },
            {
                "id": "verify_evidence",
                "name": "Verify Evidence",
                "description": "AI-powered verification of submitted evidence (photos, GPS, EXIF)",
                "mcp_tools": ["em_check_submission"],
                "rest_endpoint": "POST /api/v1/evidence/verify",
                "input_schema": {
                    "required": ["submission_id"],
                    "optional": ["verification_criteria"],
                },
                "output": "decision (approved/rejected/needs_review), confidence, reasoning",
                "trust_level": "api_key",
            },
            {
                "id": "manage_escrow",
                "name": "Manage Escrow",
                "description": "Lock, release, or refund x402r on-chain escrow for task payments",
                "mcp_tools": ["em_approve_submission"],
                "rest_endpoint": "POST /api/v1/tasks/{id}/approve",
                "input_schema": {
                    "required": ["task_id", "verdict"],
                    "optional": ["reason"],
                },
                "output": "payment_tx, amount_usd, worker_address",
                "trust_level": "api_key + task_owner",
            },
            {
                "id": "track_reputation",
                "name": "Track Reputation",
                "description": "Bidirectional on-chain reputation scores (ERC-8004)",
                "rest_endpoint": "GET /api/v1/reputation/lookup",
                "input_schema": {
                    "required": ["wallet"],
                    "optional": ["network"],
                },
                "output": "reputation_score, total_ratings, agent_id",
                "trust_level": "public (read), api_key (write)",
            },
            {
                "id": "register_identity",
                "name": "Register Identity",
                "description": "Gasless ERC-8004 identity registration across 15 networks",
                "rest_endpoint": "POST /api/v1/reputation/register",
                "input_schema": {
                    "required": ["wallet_address"],
                    "optional": ["network", "metadata_uri"],
                },
                "output": "agent_id, tx_hash, network",
                "trust_level": "authenticated",
            },
            {
                "id": "manage_workers",
                "name": "Manage Workers",
                "description": "Discover, assign, and manage executor lifecycle",
                "rest_endpoint": "GET /api/v1/tasks/{id}/applications",
                "input_schema": {
                    "required": ["task_id"],
                    "optional": ["executor_id"],
                },
                "output": "applications[], assigned_executor",
                "trust_level": "api_key + task_owner",
            },
            {
                "id": "batch_operations",
                "name": "Batch Operations",
                "description": "Bulk task creation, status queries, and management",
                "mcp_tools": ["em_get_tasks"],
                "rest_endpoint": "GET /api/v1/tasks",
                "input_schema": {
                    "required": [],
                    "optional": ["status", "category", "agent_id", "limit", "offset"],
                },
                "output": "tasks[], total_count",
                "trust_level": "api_key",
            },
        ],
    }
