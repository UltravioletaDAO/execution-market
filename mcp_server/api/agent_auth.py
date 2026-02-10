"""
Agent Authentication Endpoint

POST /api/v1/agent/auth — validates an API key and returns a JWT
for agent dashboard access. Separate from the existing API key auth
(which is header-based for MCP/REST calls). This endpoint is for
the dashboard login flow.
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .auth import _is_valid_key_format, _hash_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["Agent Auth"])

# JWT configuration
JWT_SECRET = os.environ.get(
    "EM_JWT_SECRET",
    os.environ.get("SUPABASE_JWT_SECRET", "em-dev-jwt-secret-change-me"),
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.environ.get("EM_JWT_EXPIRATION_HOURS", "24"))


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class AgentAuthRequest(BaseModel):
    """Request body for agent authentication."""

    api_key: str = Field(
        ...,
        description="Agent API key (format: em_<tier>_<random>)",
        min_length=10,
    )


class AgentAuthResponse(BaseModel):
    """Successful authentication response."""

    token: str = Field(..., description="JWT token for agent dashboard access")
    agent_id: str = Field(..., description="The authenticated agent's ID")
    tier: str = Field(..., description="API tier (free, starter, growth, enterprise)")
    expires_at: str = Field(..., description="Token expiration timestamp (ISO 8601)")


class AgentAuthError(BaseModel):
    """Error response."""

    error: str
    message: str


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def create_agent_jwt(
    agent_id: str, tier: str, organization_id: Optional[str] = None
) -> tuple[str, datetime]:
    """
    Create a JWT token for agent dashboard access.

    Returns:
        Tuple of (token_string, expiration_datetime)
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=JWT_EXPIRATION_HOURS)

    payload = {
        "sub": agent_id,
        "agent_id": agent_id,
        "tier": tier,
        "type": "agent",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    if organization_id:
        payload["org_id"] = organization_id

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expires_at


def verify_agent_jwt(token: str) -> dict:
    """
    Verify and decode an agent JWT token.

    Returns:
        Decoded payload dict

    Raises:
        jwt.ExpiredSignatureError: Token has expired
        jwt.InvalidTokenError: Token is invalid
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/auth",
    response_model=AgentAuthResponse,
    responses={
        200: {"description": "Authentication successful", "model": AgentAuthResponse},
        401: {"description": "Invalid or expired API key", "model": AgentAuthError},
    },
    summary="Authenticate agent with API key",
    description=(
        "Validates an agent API key against the database and returns a JWT "
        "for agent dashboard access. The JWT contains the agent_id claim "
        "and expires after the configured duration."
    ),
)
async def authenticate_agent(request: AgentAuthRequest) -> AgentAuthResponse:
    """
    Authenticate an agent using their API key.

    - Validates key format
    - Looks up key hash in Supabase `api_keys` table
    - Returns JWT with agent_id claim on success
    - Returns 401 on invalid/expired/revoked key
    """
    api_key = request.api_key.strip()

    # Validate key format
    if not _is_valid_key_format(api_key):
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_key", "message": "Invalid API key format"},
        )

    # Hash the key for DB lookup
    key_hash = _hash_key(api_key)

    # Look up in database
    try:
        from supabase_client import get_client

        client = get_client()

        result = (
            client.table("api_keys")
            .select("id, agent_id, tier, organization_id, is_active, created_at")
            .eq("key_hash", key_hash)
            .single()
            .execute()
        )

        if not result.data:
            logger.warning("Agent auth: API key not found (hash=%s...)", key_hash[:12])
            raise HTTPException(
                status_code=401,
                detail={"error": "invalid_key", "message": "Invalid API key"},
            )

        key_data = result.data

        # Check if key is active
        if not key_data.get("is_active", False):
            logger.warning(
                "Agent auth: Revoked key used (agent_id=%s)",
                key_data.get("agent_id"),
            )
            raise HTTPException(
                status_code=401,
                detail={"error": "key_revoked", "message": "API key has been revoked"},
            )

        # Update last_used_at
        try:
            client.table("api_keys").update(
                {"last_used_at": datetime.now(timezone.utc).isoformat()}
            ).eq("id", key_data["id"]).execute()
        except Exception as e:
            # Non-critical — don't fail auth if we can't update last_used
            logger.warning("Could not update last_used_at: %s", e)

        # Create JWT
        agent_id = key_data["agent_id"]
        tier = key_data.get("tier", "free")
        organization_id = key_data.get("organization_id")

        token, expires_at = create_agent_jwt(agent_id, tier, organization_id)

        logger.info("Agent authenticated: agent_id=%s, tier=%s", agent_id, tier)

        return AgentAuthResponse(
            token=token,
            agent_id=agent_id,
            tier=tier,
            expires_at=expires_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Agent auth error: %s", str(e))

        # In development mode with fake keys enabled, fall back
        if (
            os.environ.get("ENVIRONMENT") == "development"
            and os.environ.get("DEV_ALLOW_FAKE_KEYS") == "true"
        ):
            logger.warning("Dev mode: using fake key auth (DB unavailable)")
            return _dev_authenticate(api_key)

        raise HTTPException(
            status_code=401,
            detail={"error": "auth_error", "message": "Authentication failed"},
        )


def _dev_authenticate(api_key: str) -> AgentAuthResponse:
    """Development-only fallback authentication."""
    from .auth import APITier

    tier = APITier.FREE
    agent_id = "dev_agent"

    if api_key.startswith("em_enterprise_"):
        tier = APITier.ENTERPRISE
    elif api_key.startswith("em_growth_"):
        tier = APITier.GROWTH
    elif api_key.startswith("em_starter_"):
        tier = APITier.STARTER

    parts = api_key.split("_")
    if len(parts) >= 4:
        agent_id = parts[2]

    token, expires_at = create_agent_jwt(agent_id, tier)

    return AgentAuthResponse(
        token=token,
        agent_id=agent_id,
        tier=tier,
        expires_at=expires_at.isoformat(),
    )
