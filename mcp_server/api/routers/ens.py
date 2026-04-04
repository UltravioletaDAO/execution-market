"""
ENS REST Endpoints for Execution Market

Provides ENS name resolution, text record reading, subname management,
and profile linking for workers and agents.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

import supabase_client as db

from ..auth import verify_worker_auth, WorkerAuth, _enforce_worker_identity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ens", tags=["ENS"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class ENSResolveResponse(BaseModel):
    """ENS resolution result."""

    name: Optional[str] = None
    address: Optional[str] = None
    resolved: bool
    avatar: Optional[str] = None
    network: str = "mainnet"
    ens_link: Optional[str] = None
    error: Optional[str] = None


class ENSRecordsResponse(BaseModel):
    """ENS text records for a name."""

    name: str
    standard_records: dict = {}
    em_metadata: dict = {}
    total_records: int = 0
    network: str = "mainnet"


class LinkENSRequest(BaseModel):
    """Link an existing ENS name to executor profile."""

    executor_id: str = Field(..., description="UUID of the executor")


class LinkENSResponse(BaseModel):
    """Result of ENS linking."""

    linked: bool
    ens_name: Optional[str] = None
    ens_avatar: Optional[str] = None
    message: str


class ClaimSubnameRequest(BaseModel):
    """Claim a subname under execution-market.eth."""

    executor_id: str = Field(..., description="UUID of the executor")
    label: str = Field(
        ...,
        description="Subname label (e.g., 'alice' for alice.execution-market.eth)",
        min_length=1,
        max_length=63,
    )


class ClaimSubnameResponse(BaseModel):
    """Result of subname claim."""

    success: bool
    subname: Optional[str] = None
    tx_hash: Optional[str] = None
    explorer: Optional[str] = None
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LABEL_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


def _validate_label(label: str) -> Optional[str]:
    """Validate subname label. Returns error message or None."""
    label = label.lower().strip()
    if len(label) < 1 or len(label) > 63:
        return "Label must be 1-63 characters"
    if not _LABEL_RE.match(label):
        return "Label must be lowercase alphanumeric (hyphens allowed, not at start/end)"
    if label in ("www", "mail", "ftp", "admin", "api", "mcp", "app"):
        return f"Label '{label}' is reserved"
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/resolve/{name_or_address}",
    response_model=ENSResolveResponse,
    summary="Resolve ENS name or address",
    description=(
        "Forward-resolve an ENS name to an address, or reverse-resolve "
        "an address to an ENS name. Includes avatar if available."
    ),
)
async def resolve_ens(name_or_address: str) -> ENSResolveResponse:
    """Resolve ENS name ↔ address."""
    from integrations.ens.client import resolve_with_metadata

    result = await resolve_with_metadata(name_or_address)

    ens_link = None
    if result.get("name"):
        ens_link = f"https://app.ens.domains/{result['name']}"

    return ENSResolveResponse(
        name=result.get("name"),
        address=result.get("address"),
        resolved=result.get("resolved", False),
        avatar=result.get("avatar"),
        ens_link=ens_link,
        error=result.get("error"),
    )


@router.get(
    "/records/{name}",
    response_model=ENSRecordsResponse,
    summary="Read ENS text records",
    description="Read standard and Execution Market-specific text records from an ENS name.",
)
async def get_records(name: str) -> ENSRecordsResponse:
    """Read text records for an ENS name."""
    from integrations.ens.client import get_standard_records, get_em_metadata

    standard = await get_standard_records(name)
    em = await get_em_metadata(name)

    return ENSRecordsResponse(
        name=name,
        standard_records=standard,
        em_metadata=em,
        total_records=len(standard) + len(em),
    )


@router.get(
    "/subname/{subname}",
    response_model=ENSResolveResponse,
    summary="Resolve a worker subname",
    description="Resolve a worker subname (e.g., alice.execution-market.eth) to address + metadata.",
)
async def resolve_subname(subname: str) -> ENSResolveResponse:
    """Resolve a worker subname."""
    from integrations.ens.client import resolve_name, get_ens_avatar

    result = await resolve_name(subname)

    avatar = None
    if result.resolved and result.name:
        avatar = await get_ens_avatar(result.name)

    return ENSResolveResponse(
        name=result.name,
        address=result.address,
        resolved=result.resolved,
        avatar=avatar,
        ens_link=f"https://app.ens.domains/{subname}" if result.resolved else None,
        error=result.error,
    )


@router.post(
    "/link",
    response_model=LinkENSResponse,
    summary="Link ENS to executor profile",
    description=(
        "Auto-detect ENS name for the authenticated worker's wallet "
        "and save it to their profile. Uses reverse resolution."
    ),
)
async def link_ens(
    raw_request: Request,
    request: LinkENSRequest,
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
) -> LinkENSResponse:
    """Link ENS name to executor profile via reverse resolution."""
    from integrations.ens.client import reverse_resolve, get_ens_avatar

    executor_id = _enforce_worker_identity(
        worker_auth, request.executor_id, raw_request.url.path
    )

    # Get executor's wallet
    client = db.get_client()
    executor = (
        client.table("executors")
        .select("wallet_address, ens_name")
        .eq("id", executor_id)
        .limit(1)
        .execute()
    )

    if not executor.data:
        raise HTTPException(status_code=404, detail="Executor not found")

    wallet = executor.data[0].get("wallet_address")
    if not wallet:
        raise HTTPException(status_code=400, detail="Executor has no wallet address")

    # Reverse resolve
    result = await reverse_resolve(wallet)

    if not result.resolved or not result.name:
        return LinkENSResponse(
            linked=False,
            message="No ENS name found for this wallet. Register at app.ens.domains.",
        )

    # Get avatar
    avatar = await get_ens_avatar(result.name)

    # Update executor profile
    now = datetime.now(timezone.utc).isoformat()
    try:
        client.table("executors").update(
            {
                "ens_name": result.name,
                "ens_avatar": avatar,
                "ens_resolved_at": now,
            }
        ).eq("id", executor_id).execute()
    except Exception as exc:
        logger.error("Failed to update ENS for executor %s: %s", executor_id[:8], exc)
        raise HTTPException(status_code=500, detail="Failed to save ENS data")

    logger.info(
        "ENS linked: executor=%s, name=%s", executor_id[:8], result.name
    )

    return LinkENSResponse(
        linked=True,
        ens_name=result.name,
        ens_avatar=avatar,
        message=f"ENS name {result.name} linked to your profile",
    )


@router.post(
    "/claim-subname",
    response_model=ClaimSubnameResponse,
    responses={
        200: {"description": "Subname claimed successfully"},
        400: {"description": "Invalid label or already claimed"},
        409: {"description": "Label already taken"},
        503: {"description": "ENS owner key not configured"},
    },
    summary="Claim a subname under execution-market.eth",
    description=(
        "Claim a subname like alice.execution-market.eth. "
        "Creates the subname on-chain via NameWrapper. "
        "The subname resolves to the worker's wallet address."
    ),
)
async def claim_subname(
    raw_request: Request,
    request: ClaimSubnameRequest,
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
) -> ClaimSubnameResponse:
    """Claim a subname under execution-market.eth."""
    from integrations.ens.client import create_subname, ENS_OWNER_PRIVATE_KEY, ENS_PARENT_DOMAIN

    if not ENS_OWNER_PRIVATE_KEY:
        raise HTTPException(
            status_code=503,
            detail="Subname registration is not configured on this server",
        )

    executor_id = _enforce_worker_identity(
        worker_auth, request.executor_id, raw_request.url.path
    )

    # Validate label
    label = request.label.lower().strip()
    error = _validate_label(label)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # Get executor
    client = db.get_client()
    executor = (
        client.table("executors")
        .select("wallet_address, ens_subname")
        .eq("id", executor_id)
        .limit(1)
        .execute()
    )

    if not executor.data:
        raise HTTPException(status_code=404, detail="Executor not found")

    wallet = executor.data[0].get("wallet_address")
    existing_subname = executor.data[0].get("ens_subname")

    if existing_subname:
        return ClaimSubnameResponse(
            success=True,
            subname=existing_subname,
            message=f"You already have subname {existing_subname}",
        )

    # Check if label is taken in our DB
    taken = (
        client.table("executors")
        .select("id")
        .eq("ens_subname", f"{label}.{ENS_PARENT_DOMAIN}")
        .limit(1)
        .execute()
    )

    if taken.data:
        raise HTTPException(
            status_code=409,
            detail=f"Label '{label}' is already taken. Try a different name.",
        )

    # Create on-chain
    result = await create_subname(label, wallet)

    if not result.get("success"):
        error_msg = result.get("error", "Unknown error")
        logger.error("Subname creation failed: %s", error_msg)
        raise HTTPException(status_code=500, detail=f"On-chain creation failed: {error_msg}")

    # Save to DB
    full_subname = result["subname"]
    try:
        client.table("executors").update(
            {"ens_subname": full_subname}
        ).eq("id", executor_id).execute()
    except Exception as exc:
        logger.error("Failed to save subname for executor %s: %s", executor_id[:8], exc)

    logger.info(
        "Subname claimed: %s -> %s (tx: %s)",
        full_subname,
        wallet[:10],
        result.get("tx_hash", "?")[:16],
    )

    return ClaimSubnameResponse(
        success=True,
        subname=full_subname,
        tx_hash=result.get("tx_hash"),
        explorer=result.get("explorer"),
        message=f"Subname {full_subname} created and linked to your wallet",
    )
