"""
World ID 4.0 REST Endpoints

Provides RP signing for IDKit and Cloud API proof verification.
Stores verified proof data and enforces nullifier uniqueness (anti-sybil).
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

import supabase_client as db

from ..auth import verify_worker_auth, WorkerAuth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/world-id", tags=["World ID"])

# Endpoint-specific auth enforcement for World ID verification (FIX-P1-07).
# Defaults to the global EM_REQUIRE_WORKER_AUTH switch so this stays a total
# no-op (byte-identical to main) until worker auth is enabled. Set
# EM_WORLDID_REQUIRE_AUTH explicitly to override the inherited default.
_WORLDID_REQUIRE_AUTH = (
    os.environ.get(
        "EM_WORLDID_REQUIRE_AUTH",
        os.environ.get("EM_REQUIRE_WORKER_AUTH", "false"),
    ).lower()
    == "true"
)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class RPSignatureResponse(BaseModel):
    """RP signature data for IDKit initialization."""

    nonce: str
    created_at: int
    expires_at: int
    action: str
    signature: str
    rp_id: str
    app_id: str


class VerifyWorldIdRequest(BaseModel):
    """World ID proof verification request from frontend."""

    model_config = ConfigDict(extra="forbid")

    # Required fields
    nullifier_hash: str = Field(
        ..., description="Unique nullifier hash for this person+app"
    )
    verification_level: str = Field(..., description="'orb' or 'device'")
    executor_id: str = Field(..., description="UUID of the executor being verified")

    # v4 Cloud API fields — forwarded as-is from IDKit result
    protocol_version: str = Field(
        default="3.0", description="IDKit protocol version ('3.0' or '4.0')"
    )
    nonce: str = Field(default="", description="Nonce from IDKit result")
    action: str = Field(
        default="verify-worker",
        description="Action string used during proof generation",
    )
    responses: Optional[list] = Field(
        default=None, description="Raw IDKit responses array for v4 Cloud API"
    )

    # Legacy/DB storage fields (optional — extracted from responses by frontend)
    proof: str = Field(default="", description="ZK proof (for DB storage)")
    merkle_root: str = Field(default="", description="Merkle root (for DB storage)")
    signal: str = Field(default="", description="Signal used during proof generation")


class VerifyWorldIdResponse(BaseModel):
    """World ID verification result."""

    verified: bool
    verification_level: Optional[str] = None
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _update_erc8004_worldid_metadata(
    executor_id: str,
    verification_level: str,
) -> None:
    """
    Fire-and-forget: update ERC-8004 agent metadata with World ID verification.

    Non-critical — logs errors but never raises.
    """
    try:
        client = db.get_client()
        result = (
            client.table("executors")
            .select("erc8004_agent_id, wallet_address")
            .eq("id", executor_id)
            .limit(1)
            .execute()
        )

        if not result.data:
            return

        agent_id = result.data[0].get("erc8004_agent_id")
        if not agent_id:
            logger.info(
                "Executor %s has no ERC-8004 agent ID, skipping metadata update",
                executor_id[:8],
            )
            return

        from integrations.erc8004.facilitator_client import ERC8004FacilitatorClient

        fac = ERC8004FacilitatorClient()
        # Update metadata with World ID badge
        await fac.update_metadata(
            agent_id=agent_id,
            metadata={
                "world_id_verified": True,
                "world_id_level": verification_level,
            },
            network="base",
        )
        logger.info(
            "ERC-8004 metadata updated with World ID for agent #%s (level=%s)",
            agent_id,
            verification_level,
        )
    except Exception as exc:
        logger.warning(
            "Failed to update ERC-8004 metadata with World ID for executor %s: %s",
            executor_id[:8],
            exc,
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/rp-signature",
    response_model=RPSignatureResponse,
    summary="Get RP Signature for IDKit",
    description=(
        "Generate a signed RP request for World ID IDKit initialization. "
        "The frontend uses this data to configure IDKit before prompting the user."
    ),
)
async def get_rp_signature(
    action: str = "verify-worker",
) -> RPSignatureResponse:
    """Generate RP signature for IDKit v4."""
    from integrations.worldid.client import sign_request, WORLD_ID_APP_ID

    try:
        result = sign_request(action=action)
    except ValueError as exc:
        logger.error("World ID RP signing failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="World ID signing service temporarily unavailable",
        )

    return RPSignatureResponse(
        nonce=result.nonce,
        created_at=result.created_at,
        expires_at=result.expires_at,
        action=result.action,
        signature=result.signature,
        rp_id=result.rp_id,
        app_id=WORLD_ID_APP_ID,
    )


@router.post(
    "/verify",
    response_model=VerifyWorldIdResponse,
    responses={
        200: {"description": "Verification successful"},
        400: {"description": "Invalid proof or already verified"},
        409: {"description": "Nullifier already used (sybil attempt)"},
        503: {"description": "World ID service unavailable"},
    },
    summary="Verify World ID Proof",
    description=(
        "Verify a World ID ZK proof via the Cloud API, check nullifier uniqueness, "
        "store verification data, and update the executor profile."
    ),
)
async def verify_world_id(
    raw_request: Request,
    request: VerifyWorldIdRequest,
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
) -> VerifyWorldIdResponse:
    """Verify World ID proof and store verification."""
    # SECURITY (FIX-P1-07): World ID verification is identity-critical and must
    # NOT trust a body-supplied executor_id. When _WORLDID_REQUIRE_AUTH is on,
    # require an authenticated worker and derive the executor_id exclusively
    # from the verified identity. When off (staged rollout — default), fall back
    # to the body value with a loud audit log (byte-identical to legacy).
    if _WORLDID_REQUIRE_AUTH and worker_auth is None:
        logger.warning(
            "SECURITY_AUDIT action=worldid.verify.unauthenticated path=%s "
            "body_executor=%s (rejected)",
            raw_request.url.path,
            (request.executor_id or "none")[:8],
        )
        raise HTTPException(
            status_code=401,
            detail="Authentication required to verify World ID (Bearer <supabase_jwt>)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if worker_auth is not None:
        # Authoritative identity from the verified JWT — never the body value.
        if request.executor_id and request.executor_id != worker_auth.executor_id:
            logger.warning(
                "SECURITY_AUDIT action=worldid.verify.executor_mismatch "
                "jwt_executor=%s body_executor=%s path=%s (using jwt value)",
                worker_auth.executor_id[:8],
                request.executor_id[:8],
                raw_request.url.path,
            )
        executor_id = worker_auth.executor_id
    else:
        # Only reachable when _WORLDID_REQUIRE_AUTH is off (staged rollout).
        logger.warning(
            "SECURITY_AUDIT action=worldid.verify.body_fallback executor_id=%s "
            "path=%s (EM_WORLDID_REQUIRE_AUTH=false)",
            (request.executor_id or "none")[:8],
            raw_request.url.path,
        )
        executor_id = request.executor_id

    # 1. Check if executor is already verified
    client = db.get_client()
    existing = (
        client.table("world_id_verifications")
        .select("id, verification_level")
        .eq("executor_id", executor_id)
        .limit(1)
        .execute()
    )

    if existing.data:
        level = existing.data[0].get("verification_level", "unknown")
        return VerifyWorldIdResponse(
            verified=True,
            verification_level=level,
            message=f"Already verified at {level} level",
        )

    # 2. Verify proof via Cloud API FIRST (FIX-P1-06). The uniqueness check and
    # storage MUST use the cryptographically-bound nullifier returned by World,
    # NEVER the client-supplied request value.
    from integrations.worldid.client import verify_world_id_proof

    result = await verify_world_id_proof(
        nullifier_hash=request.nullifier_hash,  # used only by the v2 legacy path
        verification_level=request.verification_level,
        protocol_version=request.protocol_version,
        nonce=request.nonce,
        responses=request.responses,
        proof=request.proof,
        merkle_root=request.merkle_root,
        action=request.action,
        signal=request.signal,
    )

    if not result.success:
        raise HTTPException(
            status_code=400,
            detail=result.error or "World ID proof verification failed",
        )

    # SECURITY (FIX-P1-06/P1-07): trust the Cloud-API-returned nullifier, never
    # the body. client.py already rejects an empty API nullifier, but never
    # proceed without a verified one.
    nullifier_hash = result.nullifier_hash
    if not nullifier_hash:
        logger.error(
            "World ID Cloud API returned success with no nullifier (executor=%s)",
            executor_id[:8],
        )
        raise HTTPException(
            status_code=502,
            detail="World ID verification returned no nullifier",
        )

    # 3. Check nullifier uniqueness (anti-sybil) using the VERIFIED nullifier.
    nullifier_check = (
        client.table("world_id_verifications")
        .select("id, executor_id")
        .eq("nullifier_hash", nullifier_hash)
        .limit(1)
        .execute()
    )

    if nullifier_check.data:
        logger.warning(
            "SYBIL_ATTEMPT: nullifier %s...%s already used by executor %s, "
            "attempted reuse by executor %s",
            nullifier_hash[:10],
            nullifier_hash[-6:],
            str(nullifier_check.data[0].get("executor_id", "?"))[:8],
            executor_id[:8],
        )
        raise HTTPException(
            status_code=409,
            detail="This World ID has already been used to verify another account",
        )

    # 4. Store verification record
    now = datetime.now(timezone.utc).isoformat()
    try:
        client.table("world_id_verifications").insert(
            {
                "executor_id": executor_id,
                "nullifier_hash": nullifier_hash,
                "merkle_root": request.merkle_root,
                "verification_level": result.verification_level
                or request.verification_level,
                "proof": request.proof,
                "verified_at": now,
            }
        ).execute()
    except Exception as exc:
        error_str = str(exc)
        if "uq_world_id_nullifier" in error_str:
            raise HTTPException(
                status_code=409,
                detail="This World ID has already been used to verify another account",
            )
        if "uq_world_id_executor" in error_str:
            return VerifyWorldIdResponse(
                verified=True,
                verification_level=result.verification_level,
                message="Already verified (race condition resolved)",
            )
        logger.error("Failed to store World ID verification: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to store verification record",
        )

    # 5. Update executor profile
    try:
        client.table("executors").update(
            {
                "world_id_verified": True,
                "world_id_level": result.verification_level
                or request.verification_level,
            }
        ).eq("id", executor_id).execute()
    except Exception as exc:
        logger.error(
            "Failed to update executor %s with World ID status: %s",
            executor_id[:8],
            exc,
        )

    # 6. Fire-and-forget: update ERC-8004 metadata
    level = result.verification_level or request.verification_level
    try:
        asyncio.get_running_loop().create_task(
            _update_erc8004_worldid_metadata(executor_id, level)
        )
    except Exception:
        pass  # Non-critical

    logger.info(
        "World ID verified: executor=%s, level=%s, nullifier=%s...%s",
        executor_id[:8],
        level,
        nullifier_hash[:10],
        nullifier_hash[-6:],
    )

    return VerifyWorldIdResponse(
        verified=True,
        verification_level=level,
        message=f"World ID verified at {level} level",
    )
