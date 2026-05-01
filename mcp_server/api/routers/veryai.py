"""VeryAI OAuth2 / OIDC REST endpoints.

Mirrors the shape of `worldid.py` but speaks OAuth2:

  GET  /api/v1/very-id/oauth-url   — start flow (returns authorize URL + state)
  GET  /api/v1/very-id/callback    — finish flow (OAuth redirect target)
  POST /api/v1/very-id/verify      — Phase 7 native-SDK path (501 in MVP)
  GET  /api/v1/very-id/status      — poll executor's current status

The callback runs anonymously from the user's browser (OAuth redirect) and
relies on the signed state JWT for identity binding + CSRF protection.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

import supabase_client as db

from ..auth import WorkerAuth, _enforce_worker_identity, verify_worker_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/very-id", tags=["VeryAI"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class OAuthUrlResponse(BaseModel):
    """Returns an authorize URL the frontend redirects to."""

    url: str
    state: str


class VeryAiStatusResponse(BaseModel):
    """Current VeryAI status for an executor."""

    verified: bool = Field(default=False)
    level: Optional[str] = Field(
        default=None, description="palm_single | palm_dual | None"
    )
    verified_at: Optional[str] = Field(default=None, description="ISO 8601 timestamp")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dashboard_url() -> str:
    """Return the dashboard origin used to bounce users back after callback."""
    return (
        os.environ.get("EM_DASHBOARD_URL")
        or os.environ.get("DASHBOARD_URL")
        or "https://execution.market"
    ).rstrip("/")


def _redirect_with_status(
    status: str, reason: Optional[str] = None
) -> RedirectResponse:
    """Bounce the user back to /profile with a status query param."""
    base = _dashboard_url()
    params = f"veryai={status}"
    if reason:
        from urllib.parse import quote

        params += f"&reason={quote(reason)}"
    return RedirectResponse(url=f"{base}/profile?{params}", status_code=302)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/oauth-url",
    response_model=OAuthUrlResponse,
    summary="Start VeryAI OAuth2 flow",
    description=(
        "Returns the authorize URL the frontend should redirect the user to. "
        "Encodes a signed state JWT containing the executor_id + PKCE verifier."
    ),
)
async def get_oauth_url(
    raw_request: Request,
    executor_id: str = Query(..., description="UUID of the executor starting the flow"),
    redirect_uri: Optional[str] = Query(
        default=None,
        description="Override redirect URI (defaults to VERYAI_REDIRECT_URI env)",
    ),
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
) -> OAuthUrlResponse:
    """Start the OAuth2 + PKCE flow."""
    # Anchor identity to the authenticated worker when present; fall back to
    # the body executor_id (gated by EM_REQUIRE_WORKER_AUTH).
    bound_executor_id = _enforce_worker_identity(
        worker_auth, executor_id, raw_request.url.path
    )

    from integrations.veryai.client import get_authorization_url

    try:
        result = await get_authorization_url(
            executor_id=bound_executor_id,
            redirect_uri=redirect_uri,
        )
    except ValueError as exc:
        logger.error("VeryAI oauth-url misconfigured: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="VeryAI signing service temporarily unavailable",
        )

    return OAuthUrlResponse(url=result.url, state=result.state)


@router.get(
    "/callback",
    summary="VeryAI OAuth2 callback",
    description=(
        "OAuth redirect target. Exchanges code+state for tokens, fetches "
        "/userinfo, performs anti-sybil check, stores verification, and "
        "redirects the user back to the dashboard with a status flag."
    ),
)
async def callback(
    code: str = Query(..., description="Authorization code from VeryAI"),
    state: str = Query(..., description="Signed state JWT issued by /oauth-url"),
    error: Optional[str] = Query(default=None, description="OAuth error code"),
    error_description: Optional[str] = Query(default=None),
):
    """Finish the OAuth flow."""
    if error:
        logger.warning(
            "VeryAI callback received error from IdP: %s — %s",
            error,
            error_description,
        )
        return _redirect_with_status("error", reason=error)

    from integrations.veryai.client import (
        StateTokenError,
        exchange_code_for_token,
        get_userinfo,
        verify_state_token,
    )

    # 1. Verify state JWT — pulls out executor_id + code_verifier
    try:
        decoded = verify_state_token(state)
    except StateTokenError as exc:
        logger.warning("VeryAI callback rejected: %s", exc)
        return _redirect_with_status("error", reason="invalid_state")

    executor_id = decoded["executor_id"]
    code_verifier = decoded["code_verifier"]

    # 2. Exchange code -> tokens
    try:
        token_result = await exchange_code_for_token(
            code=code,
            code_verifier=code_verifier,
        )
    except Exception as exc:
        logger.error("VeryAI token exchange failed: %s", exc)
        return _redirect_with_status("error", reason="token_exchange_failed")

    # 3. Fetch /userinfo
    try:
        info = await get_userinfo(token_result.access_token)
    except Exception as exc:
        logger.error("VeryAI userinfo failed: %s", exc)
        return _redirect_with_status("error", reason="userinfo_failed")

    if info.verification_level not in ("palm_single", "palm_dual"):
        logger.info(
            "VeryAI callback for executor %s: not yet palm-verified (level=%s)",
            executor_id[:8],
            info.verification_level,
        )
        return _redirect_with_status("incomplete", reason="not_palm_verified")

    # 4. Anti-sybil — sub uniqueness across executors
    client = db.get_client()
    sybil_check = (
        client.table("veryai_verifications")
        .select("id, executor_id")
        .eq("veryai_sub", info.sub)
        .limit(1)
        .execute()
    )
    if sybil_check.data:
        prior = sybil_check.data[0].get("executor_id")
        if prior != executor_id:
            logger.warning(
                "SYBIL_ATTEMPT: VeryAI sub %s already bound to %s, attempted by %s",
                info.sub,
                str(prior)[:8],
                executor_id[:8],
            )
            return _redirect_with_status("error", reason="sub_already_used")
        # Same executor — already verified; no-op success
        return _redirect_with_status("success", reason="already_verified")

    # 5. Insert verification + update executor
    now = datetime.now(timezone.utc).isoformat()
    try:
        client.table("veryai_verifications").insert(
            {
                "executor_id": executor_id,
                "veryai_sub": info.sub,
                "verification_level": info.verification_level,
                "oidc_id_token": token_result.id_token or "",
                "verified_at": now,
            }
        ).execute()
    except Exception as exc:
        error_str = str(exc)
        if "uq_veryai_sub" in error_str:
            return _redirect_with_status("error", reason="sub_already_used")
        if "uq_veryai_executor" in error_str:
            return _redirect_with_status("success", reason="already_verified")
        logger.error("Failed to store VeryAI verification: %s", exc)
        return _redirect_with_status("error", reason="store_failed")

    try:
        client.table("executors").update(
            {
                "veryai_verified": True,
                "veryai_level": info.verification_level,
                "veryai_sub": info.sub,
                "veryai_verified_at": now,
            }
        ).eq("id", executor_id).execute()
    except Exception as exc:
        logger.error(
            "Failed to update executor %s with VeryAI status: %s",
            executor_id[:8],
            exc,
        )
        # DB write of the verification record succeeded — surface success but
        # log so we can backfill the executor flag offline.

    # 6. Fire-and-forget metadata update
    try:
        from integrations.veryai.metadata_sync import (
            update_erc8004_veryai_metadata,
        )

        asyncio.get_running_loop().create_task(
            update_erc8004_veryai_metadata(executor_id, info.verification_level)
        )
    except Exception:
        pass  # Non-critical

    logger.info(
        "VeryAI verified: executor=%s, level=%s, sub=%s",
        executor_id[:8],
        info.verification_level,
        info.sub,
    )
    return _redirect_with_status("success")


@router.post(
    "/verify",
    status_code=501,
    summary="Native-SDK verification (Phase 7)",
    description=(
        "Reserved for the Phase 7 native-SDK path. Returns 501 in the OAuth-only MVP."
    ),
)
async def verify_native_sdk():
    raise HTTPException(
        status_code=501,
        detail="Native-SDK verification is not yet implemented",
    )


@router.get(
    "/status",
    response_model=VeryAiStatusResponse,
    summary="Get the current executor's VeryAI status",
)
async def get_status(
    raw_request: Request,
    executor_id: str = Query(..., description="UUID of the executor"),
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
) -> VeryAiStatusResponse:
    bound_executor_id = _enforce_worker_identity(
        worker_auth, executor_id, raw_request.url.path
    )
    client = db.get_client()
    try:
        res = (
            client.table("executors")
            .select("veryai_verified, veryai_level, veryai_verified_at")
            .eq("id", bound_executor_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("VeryAI status lookup failed for %s: %s", bound_executor_id, exc)
        raise HTTPException(status_code=500, detail="status_lookup_failed")

    row = res.data[0] if res.data else {}
    return VeryAiStatusResponse(
        verified=bool(row.get("veryai_verified")),
        level=row.get("veryai_level"),
        verified_at=row.get("veryai_verified_at"),
    )
