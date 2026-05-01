"""ClawKey KYA REST endpoints.

Three routes:

  GET  /api/v1/clawkey/status/{executor_id}    — read DB cached KYA status
  POST /api/v1/clawkey/refresh/{executor_id}   — force upstream re-verification
  POST /api/v1/clawkey/register                — 501 (deferred to clawhub CLI)

Schema note: this project uses ``executors.agent_type='ai'`` instead of a
separate ``agents`` table (see migration 106). All endpoints are keyed by
``executor_id``.

ClawKey is *additive*: these endpoints never block task creation or
application. The status payload is purely informational — frontends use it
to render a KYA badge.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel, Field

import supabase_client as db

from ..auth import WorkerAuth, _enforce_worker_identity, verify_worker_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/clawkey", tags=["ClawKey"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ClawKeyStatusResponse(BaseModel):
    """Snapshot of an executor's ClawKey KYA binding."""

    verified: bool = Field(default=False)
    human_id: Optional[str] = Field(
        default=None,
        description="ClawKey humanId. Multiple agents may share one human.",
    )
    registered_at: Optional[str] = Field(default=None, description="ISO 8601 timestamp")
    public_key: Optional[str] = Field(
        default=None, description="Agent Ed25519 public key (base58)"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_status() -> ClawKeyStatusResponse:
    return ClawKeyStatusResponse(
        verified=False, human_id=None, registered_at=None, public_key=None
    )


def _fetch_executor_row(executor_id: str) -> Optional[dict]:
    """Pull the ClawKey-relevant columns for an executor.

    Returns None if the executor doesn't exist; raises HTTPException(500) on
    DB errors so the caller can convert that into a clean response.
    """
    client = db.get_client()
    try:
        res = (
            client.table("executors")
            .select(
                "id, clawkey_verified, clawkey_human_id, clawkey_public_key, "
                "clawkey_device_id, clawkey_registered_at"
            )
            .eq("id", executor_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("ClawKey lookup failed for %s: %s", executor_id, exc)
        raise HTTPException(status_code=500, detail="status_lookup_failed")

    return res.data[0] if res.data else None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/status/{executor_id}",
    response_model=ClawKeyStatusResponse,
    summary="Get ClawKey KYA status for an executor",
    description=(
        "Returns the cached ClawKey binding for an executor. Public read — "
        "KYA is a public trust signal by design. Background sync (job 4.5) "
        "keeps these values fresh."
    ),
)
async def get_status(
    executor_id: str = Path(..., description="UUID of the executor"),
) -> ClawKeyStatusResponse:
    row = _fetch_executor_row(executor_id)
    if row is None:
        raise HTTPException(status_code=404, detail="executor_not_found")

    return ClawKeyStatusResponse(
        verified=bool(row.get("clawkey_verified")),
        human_id=row.get("clawkey_human_id"),
        registered_at=row.get("clawkey_registered_at"),
        public_key=row.get("clawkey_public_key"),
    )


@router.post(
    "/refresh/{executor_id}",
    response_model=ClawKeyStatusResponse,
    summary="Force ClawKey re-verification against upstream",
    description=(
        "Bypasses the in-memory cache and DB snapshot, hits api.clawkey.ai, "
        "and persists the result. Auth: agent owner only. Returns the "
        "refreshed status."
    ),
)
async def refresh(
    raw_request: Request,
    executor_id: str = Path(..., description="UUID of the executor"),
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
) -> ClawKeyStatusResponse:
    # Enforce ownership — only the agent owner can trigger a refresh
    bound_executor_id = _enforce_worker_identity(
        worker_auth, executor_id, raw_request.url.path
    )

    row = _fetch_executor_row(bound_executor_id)
    if row is None:
        raise HTTPException(status_code=404, detail="executor_not_found")

    public_key = row.get("clawkey_public_key")
    if not public_key:
        # Not registered upstream yet — nothing to refresh. Surface a
        # consistent empty status rather than 400 so the frontend can render
        # "not registered" without special-casing the error path.
        return _empty_status()

    from integrations.clawkey.client import verify_by_public_key

    try:
        result = await verify_by_public_key(public_key, use_cache=False)
    except httpx.HTTPError as exc:
        logger.warning(
            "ClawKey upstream unavailable during refresh for %s: %s",
            bound_executor_id[:8],
            exc,
        )
        raise HTTPException(status_code=503, detail="clawkey_upstream_unavailable")

    now = datetime.now(timezone.utc).isoformat()
    client = db.get_client()
    try:
        client.table("executors").update(
            {
                "clawkey_verified": result.verified,
                "clawkey_human_id": result.human_id,
                "clawkey_registered_at": result.registered_at,
            }
        ).eq("id", bound_executor_id).execute()
    except Exception as exc:
        # Persisting the refresh is best-effort. The upstream answer is what
        # we return regardless — the sync job will reconcile DB later.
        logger.error(
            "Failed to persist ClawKey refresh for %s: %s",
            bound_executor_id[:8],
            exc,
        )

    if result.verified and result.human_id:
        # Upsert audit-trail row (UNIQUE on executor_id ensures idempotency)
        try:
            client.table("agent_kya_verifications").upsert(
                {
                    "executor_id": bound_executor_id,
                    "clawkey_human_id": result.human_id,
                    "clawkey_device_id": row.get("clawkey_device_id") or "",
                    "clawkey_public_key": public_key,
                    "last_verified_at": now,
                },
                on_conflict="executor_id",
            ).execute()
        except Exception as exc:
            logger.warning(
                "Failed to upsert agent_kya_verifications for %s: %s",
                bound_executor_id[:8],
                exc,
            )

    return ClawKeyStatusResponse(
        verified=result.verified,
        human_id=result.human_id,
        registered_at=result.registered_at,
        public_key=public_key,
    )


@router.post(
    "/register",
    status_code=501,
    summary="Bootstrap ClawKey registration (deferred)",
    description=(
        "Reserved for a future bootstrap flow. In the MVP, agents register "
        "directly through the `clawhub` CLI on their own device."
    ),
)
async def register_placeholder():
    raise HTTPException(
        status_code=501,
        detail="ClawKey registration must be performed via the `clawhub` CLI",
    )
