"""
API Authentication Module

Handles API key verification, tier determination, and agent authorization.
Supports dual auth: traditional API keys AND ERC-8128 wallet-based authentication.

ERC-8128 Auth Flow:
  HTTP request with Signature + Signature-Input headers
    → verify_agent_auth()
      → Has Signature header? → verify_erc8128_request()
      → Has Bearer/X-API-Key? → verify_api_key() (existing, unchanged)
"""

import os
import logging
import hashlib
import secrets
import threading
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, Header, Request

try:
    from cachetools import TTLCache
except ImportError:  # pragma: no cover
    TTLCache = None

logger = logging.getLogger(__name__)


@dataclass
class APIKeyData:
    """Validated API key data."""

    key_hash: str
    agent_id: str
    tier: str
    organization_id: Optional[str] = None
    is_valid: bool = True
    created_at: Optional[datetime] = None
    last_used: Optional[datetime] = None


class APITier:
    """API tier constants."""

    FREE = "free"
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


# Thread-safe API key cache with TTL
_API_KEY_CACHE_TTL_SECONDS = 300  # 5 minutes
_API_KEY_CACHE_MAXSIZE = 256

if TTLCache is not None:
    _api_key_cache: TTLCache = TTLCache(
        maxsize=_API_KEY_CACHE_MAXSIZE, ttl=_API_KEY_CACHE_TTL_SECONDS
    )
else:
    _api_key_cache: dict[str, APIKeyData] = {}  # type: ignore[no-redef]

_api_key_cache_lock = threading.Lock()

# Legacy compat — kept as no-op reference for clear_api_key_cache()
_api_key_cache_timestamps: dict[str, float] = {}


def _is_cache_entry_valid(key_hash: str) -> bool:
    """Check if a cache entry is still within its TTL.

    With TTLCache this is automatic; for the dict fallback we check timestamps.
    """
    if TTLCache is not None:
        # TTLCache handles expiry automatically — if key is present, it's valid
        return key_hash in _api_key_cache
    import time

    cached_at = _api_key_cache_timestamps.get(key_hash)
    if cached_at is None:
        return False
    return (time.time() - cached_at) < _API_KEY_CACHE_TTL_SECONDS


async def verify_api_key(
    authorization: Optional[str] = Header(
        None, description="Bearer token with API key"
    ),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> APIKeyData:
    """
    Verify API key from Authorization header.

    Args:
        authorization: Bearer token header value

    Returns:
        APIKeyData with validated key information

    Raises:
        HTTPException: If key is invalid or missing
    """
    api_key: Optional[str] = None

    if authorization:
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format. Use: Bearer <api_key>",
                headers={"WWW-Authenticate": "Bearer"},
            )
        api_key = authorization[7:].strip()
    elif x_api_key:
        api_key = x_api_key.strip()

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required (Authorization Bearer or X-API-Key)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate key format (should be em_<tier>_<random>)
    if not _is_valid_key_format(api_key):
        raise HTTPException(status_code=401, detail="Invalid API key format")

    # Check cache first (thread-safe with TTL)
    key_hash = _hash_key(api_key)
    with _api_key_cache_lock:
        if key_hash in _api_key_cache and _is_cache_entry_valid(key_hash):
            cached = _api_key_cache[key_hash]
            if cached.is_valid:
                cached.last_used = datetime.now(timezone.utc)
                return cached
            else:
                raise HTTPException(status_code=401, detail="API key has been revoked")
        elif key_hash in _api_key_cache and not _is_cache_entry_valid(key_hash):
            # TTL expired, remove stale entry (only for dict fallback)
            del _api_key_cache[key_hash]
            _api_key_cache_timestamps.pop(key_hash, None)

    # Validate against database
    key_data = await _validate_key_from_db(api_key, key_hash)

    if not key_data or not key_data.is_valid:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")

    # Cache the validated key (thread-safe)
    with _api_key_cache_lock:
        _api_key_cache[key_hash] = key_data
        if TTLCache is None:
            import time

            _api_key_cache_timestamps[key_hash] = time.time()

    return key_data


async def verify_api_key_optional(
    authorization: Optional[str] = Header(None, description="Optional Bearer token"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Optional[APIKeyData]:
    """
    Optionally verify API key (for public endpoints with optional auth).

    Returns None if no authorization header provided.
    """
    if not authorization and not x_api_key:
        return None

    try:
        return await verify_api_key(authorization, x_api_key)
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# Configurable auth: when EM_REQUIRE_API_KEY=false, agent endpoints accept
# unauthenticated requests and fall back to the platform agent identity.
# ---------------------------------------------------------------------------

_REQUIRE_API_KEY = os.environ.get("EM_REQUIRE_API_KEY", "false").lower() == "true"

# Kill switch: when false, ALL API key auth is rejected. Only ERC-8128 wallet
# signing is accepted. Set EM_API_KEYS_ENABLED=true to re-enable API keys.
# DEFAULT: disabled — API keys are a security risk (tasks created as Agent #2106).
_API_KEYS_ENABLED = os.environ.get("EM_API_KEYS_ENABLED", "false").lower() == "true"


def _anonymous_agent_data() -> APIKeyData:
    """Return a default APIKeyData for unauthenticated requests."""
    _agent_id = os.environ.get("EM_AGENT_ID", "2106")
    return APIKeyData(
        key_hash="anonymous",
        agent_id=str(_agent_id),
        tier=APITier.FREE,
        is_valid=True,
        created_at=datetime.now(timezone.utc),
        last_used=datetime.now(timezone.utc),
    )


async def verify_api_key_if_required(
    authorization: Optional[str] = Header(
        None, description="Bearer token with API key"
    ),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> APIKeyData:
    """
    Verify API key only when EM_REQUIRE_API_KEY=true.

    When disabled, returns anonymous agent data (platform agent identity).
    If a valid key IS provided even when not required, it will be used.
    """
    if authorization or x_api_key:
        try:
            return await verify_api_key(authorization, x_api_key)
        except HTTPException:
            if _REQUIRE_API_KEY:
                raise
            # Key was provided but invalid — when auth not required, fall through
            logger.warning("Invalid API key provided (auth not required, ignoring)")

    if _REQUIRE_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required. Set EM_REQUIRE_API_KEY=false to disable.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _anonymous_agent_data()


def get_api_tier(api_key_data: Optional[APIKeyData]) -> str:
    """Get the tier from API key data, defaulting to FREE."""
    if not api_key_data:
        return APITier.FREE
    return api_key_data.tier


def _is_valid_key_format(api_key: str) -> bool:
    """
    Validate API key format.

    Expected formats:
    - em_free_<32 chars>
    - em_starter_<32 chars>
    - em_growth_<32 chars>
    - em_enterprise_<32 chars>
    - Legacy: sk_em_<32 chars>
    - Legacy: sk_em_<32 chars>
    """
    if not api_key:
        return False

    # Legacy format
    if api_key.startswith("sk_em_"):
        return len(api_key) >= 38  # sk_em_ + 32 chars

    # Standard format
    valid_prefixes = [
        "em_free_",
        "em_starter_",
        "em_growth_",
        "em_enterprise_",
        "em_bot_",  # Service/bot accounts
    ]

    for prefix in valid_prefixes:
        if api_key.startswith(prefix):
            suffix = api_key[len(prefix) :]
            return len(suffix) >= 32

    return False


def _hash_key(api_key: str) -> str:
    """Hash API key for storage/comparison."""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def _validate_key_from_db(api_key: str, key_hash: str) -> Optional[APIKeyData]:
    """
    Validate API key against database.

    In production, this queries the api_keys table.
    """
    try:
        # Import here to avoid circular imports
        from supabase_client import get_client

        client = get_client()

        # Query by hash for security
        result = (
            client.table("api_keys")
            .select(
                "id, agent_id, tier, organization_id, is_active, created_at, last_used_at"
            )
            .eq("key_hash", key_hash)
            .single()
            .execute()
        )

        if not result.data:
            logger.warning("API key not found in database")
            return None

        data = result.data

        if not data.get("is_active", False):
            logger.warning("API key is inactive: agent_id=%s", data.get("agent_id"))
            return None

        # Update last_used_at
        client.table("api_keys").update(
            {"last_used_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", data["id"]).execute()

        return APIKeyData(
            key_hash=key_hash,
            agent_id=data["agent_id"],
            tier=data.get("tier", APITier.FREE),
            organization_id=data.get("organization_id"),
            is_valid=True,
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
            last_used=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error("Error validating API key: %s", str(e))

        # In development, allow keys matching pattern without DB (requires explicit opt-in)
        if (
            os.environ.get("ENVIRONMENT") == "development"
            and os.environ.get("DEV_ALLOW_FAKE_KEYS") == "true"
        ):
            logger.warning("Dev mode: using fake key validation (DB unavailable)")
            return _dev_validate_key(api_key, key_hash)

        return None


def _dev_validate_key(api_key: str, key_hash: str) -> Optional[APIKeyData]:
    """
    Development-only key validation.

    Extracts tier from key prefix for testing without database.
    """
    tier = APITier.FREE
    agent_id = "dev_agent"

    if api_key.startswith("em_enterprise_"):
        tier = APITier.ENTERPRISE
    elif api_key.startswith("em_growth_"):
        tier = APITier.GROWTH
    elif api_key.startswith("em_starter_"):
        tier = APITier.STARTER
    elif api_key.startswith("sk_em_"):
        tier = APITier.STARTER

    # Extract agent_id from key if present (format: em_tier_agentid_random)
    parts = api_key.split("_")
    if len(parts) >= 4:
        agent_id = parts[2]

    logger.warning("Using development API key validation for: %s...", api_key[:20])

    return APIKeyData(
        key_hash=key_hash,
        agent_id=agent_id,
        tier=tier,
        is_valid=True,
        created_at=datetime.now(timezone.utc),
        last_used=datetime.now(timezone.utc),
    )


def generate_api_key(tier: str = APITier.FREE, agent_id: Optional[str] = None) -> str:
    """
    Generate a new API key.

    Args:
        tier: API tier (free, starter, growth, enterprise)
        agent_id: Optional agent ID to embed in key

    Returns:
        New API key string
    """
    random_part = secrets.token_hex(16)  # 32 chars

    if agent_id:
        # Sanitize agent_id for key
        safe_agent_id = "".join(c for c in agent_id[:16] if c.isalnum())
        return f"em_{tier}_{safe_agent_id}_{random_part}"

    return f"em_{tier}_{random_part}"


async def verify_agent_owns_task(agent_id: str, task_id: str) -> bool:
    """
    Verify that an agent owns a specific task.

    Args:
        agent_id: The agent's identifier
        task_id: The task UUID

    Returns:
        True if agent owns the task
    """
    try:
        from supabase_client import get_task

        task = await get_task(task_id)
        if not task:
            return False

        # Compare case-insensitively — agent_id may be wallet (0x...) or legacy numeric
        task_agent = (task.get("agent_id") or "").lower()
        return task_agent == agent_id.lower()

    except Exception as e:
        logger.error("Error verifying task ownership: %s", str(e))
        return False


async def verify_agent_owns_submission(agent_id: str, submission_id: str) -> bool:
    """
    Verify that an agent owns the task associated with a submission.

    Args:
        agent_id: The agent's identifier
        submission_id: The submission UUID

    Returns:
        True if agent owns the submission's task
    """
    try:
        from supabase_client import get_submission

        submission = await get_submission(submission_id)
        if not submission:
            return False

        task = submission.get("task")
        if not task:
            return False

        task_agent = (task.get("agent_id") or "").lower()
        return task_agent == agent_id.lower()

    except Exception as e:
        logger.error("Error verifying submission ownership: %s", str(e))
        return False


# ==========================================================================
# ERC-8128 Wallet-Based Authentication (Unified Auth)
# ==========================================================================


@dataclass
class AgentAuth:
    """
    Unified auth result for both API keys and ERC-8128 wallet signatures.

    This is the new canonical auth type. Routes can migrate from
    Depends(verify_api_key_if_required) to Depends(verify_agent_auth).
    """

    agent_id: str
    wallet_address: Optional[str] = None
    tier: str = "free"
    auth_method: str = "api_key"  # "api_key" | "erc8128"
    chain_id: Optional[int] = None
    organization_id: Optional[str] = None
    erc8004_registered: bool = False
    erc8004_agent_id: Optional[int] = None


# Lazy-initialized nonce store (avoids import-time side effects)
_erc8128_nonce_store = None


def _get_erc8128_nonce_store():
    """Get or create the ERC-8128 nonce store."""
    global _erc8128_nonce_store
    if _erc8128_nonce_store is None:
        try:
            from integrations.erc8128.nonce_store import get_nonce_store

            _erc8128_nonce_store = get_nonce_store()
        except ImportError:
            logger.warning("ERC-8128 nonce store not available")
            return None
    return _erc8128_nonce_store


async def _resolve_erc8004_identity(wallet_address: str, chain_id: int) -> dict:
    """
    Cross-reference a wallet address with ERC-8004 identity.

    Returns dict with agent_id, registered, etc.
    Timeout at 5s to avoid blocking the auth flow.
    """
    import asyncio as _aio

    try:
        from integrations.erc8004.identity import check_worker_identity

        result = await _aio.wait_for(
            check_worker_identity(wallet_address),
            timeout=5.0,
        )
        return {
            "registered": result.status.value == "registered",
            "agent_id": result.agent_id,
        }
    except _aio.TimeoutError:
        logger.warning(
            "ERC-8004 identity lookup timed out (5s) for %s", wallet_address[:10]
        )
    except ImportError:
        logger.debug("ERC-8004 identity module not available")
    except Exception as e:
        logger.warning("ERC-8004 identity lookup failed: %s", e)

    return {"registered": False, "agent_id": None}


async def verify_agent_auth(request: Request) -> AgentAuth:
    """
    Unified auth dependency: tries ERC-8128 first (if Signature header present),
    falls back to API key auth.

    Usage in routes::

        @router.post("/api/v1/tasks")
        async def create_task(auth: AgentAuth = Depends(verify_agent_auth)):
            print(f"Authenticated: {auth.agent_id} via {auth.auth_method}")

    Priority:
      1. Signature header present → ERC-8128 verification
      2. Bearer/X-API-Key header → existing API key verification
      3. Neither → depends on EM_REQUIRE_API_KEY setting
    """
    # Path 1: ERC-8128 signature-based auth
    sig_header = request.headers.get("signature")
    sig_input_header = request.headers.get("signature-input")

    if sig_header and sig_input_header:
        try:
            from integrations.erc8128.verifier import verify_erc8128_request

            nonce_store = _get_erc8128_nonce_store()
            result = await verify_erc8128_request(request, nonce_store=nonce_store)

            if result.ok:
                # Cross-reference with ERC-8004 identity
                identity = await _resolve_erc8004_identity(
                    result.address, result.chain_id
                )

                # Always use wallet address as agent_id for ERC-8128 auth.
                # The numeric ERC-8004 token ID (e.g. 37500 on Base, 246 on SKALE)
                # is stored in erc8004_agent_id — it's per-chain and NOT suitable
                # as the universal agent identifier. Wallet address is chain-invariant.
                return AgentAuth(
                    agent_id=result.address,
                    wallet_address=result.address,
                    auth_method="erc8128",
                    chain_id=result.chain_id,
                    erc8004_registered=identity.get("registered", False),
                    erc8004_agent_id=identity.get("agent_id"),
                )

            # ERC-8128 failed — DON'T fall through to API key
            raise HTTPException(
                status_code=401,
                detail=f"ERC-8128 verification failed: {result.reason}",
                headers={"WWW-Authenticate": 'ERC8128 realm="execution-market"'},
            )

        except HTTPException:
            raise
        except ImportError:
            logger.warning(
                "ERC-8128 module not available, falling through to API key auth"
            )
        except Exception as e:
            logger.error("ERC-8128 verification error: %s", e)
            raise HTTPException(
                status_code=401,
                detail=f"ERC-8128 verification error: {e}",
                headers={"WWW-Authenticate": 'ERC8128 realm="execution-market"'},
            )

    # Path 2: API key auth — disabled by default (EM_API_KEYS_ENABLED=false)
    authorization = request.headers.get("authorization")
    x_api_key = request.headers.get("x-api-key")

    if not _API_KEYS_ENABLED:
        # Reject explicit API key attempts with 403
        if authorization or x_api_key:
            logger.warning(
                "API key auth attempted but EM_API_KEYS_ENABLED=false — rejected"
            )
            raise HTTPException(
                status_code=403,
                detail=(
                    "API key authentication is disabled. "
                    "Use ERC-8128 wallet signing instead. "
                    "See https://execution.market/skill.md for setup instructions."
                ),
            )
        # No auth headers at all — allow anonymous read access (Agent #2106)
        # This preserves dashboard/public endpoint functionality.
        return AgentAuth(
            agent_id=str(os.environ.get("EM_AGENT_ID", "2106")),
            tier="free",
            auth_method="anonymous",
        )

    # Path 2b: API key auth (only reachable when EM_API_KEYS_ENABLED=true)
    authorization = request.headers.get("authorization")
    x_api_key = request.headers.get("x-api-key")

    api_key_data = await verify_api_key_if_required(
        authorization=authorization, x_api_key=x_api_key
    )

    return AgentAuth(
        agent_id=api_key_data.agent_id,
        tier=api_key_data.tier,
        auth_method="api_key",
        organization_id=api_key_data.organization_id,
    )


# ==========================================================================
# Nonce endpoint helper
# ==========================================================================

# IP-based rate limiting for nonce generation (in-memory sliding window)
_nonce_requests: dict = {}  # ip -> list of timestamps
_NONCE_RATE_LIMIT = 5
_NONCE_RATE_WINDOW = 60  # seconds


def _check_nonce_rate_limit(ip: str) -> tuple[bool, int]:
    """Check nonce generation rate limit. Returns (is_limited, retry_after_seconds)."""
    import time

    now = time.time()
    timestamps = _nonce_requests.setdefault(ip, [])
    cutoff = now - _NONCE_RATE_WINDOW
    timestamps[:] = [t for t in timestamps if t > cutoff]
    if len(timestamps) >= _NONCE_RATE_LIMIT:
        retry_after = int(_NONCE_RATE_WINDOW - (now - timestamps[0])) if timestamps else _NONCE_RATE_WINDOW
        return True, retry_after
    timestamps.append(now)
    return False, 0


def _get_nonce_client_ip(request: Request) -> str:
    """Extract client IP from request for nonce rate limiting."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return "unknown"


async def generate_auth_nonce(request: Request) -> dict:
    """Generate a fresh nonce for ERC-8128 authentication."""
    from fastapi.responses import JSONResponse

    # Rate limit: max 5 nonces per IP per 60 seconds
    client_ip = _get_nonce_client_ip(request)
    is_limited, retry_after = _check_nonce_rate_limit(client_ip)
    if is_limited:
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded for nonce generation"},
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Type": "nonce",
            },
        )

    store = _get_erc8128_nonce_store()
    if store is None:
        return JSONResponse(
            status_code=503,
            content={"error": "Nonce store not available", "nonce": None},
        )

    nonce = await store.generate()
    return {
        "nonce": nonce,
        "ttl_seconds": 300,
        "message": "Include this nonce in the Signature-Input nonce parameter",
    }


# ==========================================================================
# Worker Authentication (Supabase JWT → executor_id)
# ==========================================================================

_REQUIRE_WORKER_AUTH = (
    os.environ.get("EM_REQUIRE_WORKER_AUTH", "false").lower() == "true"
)


@dataclass
class WorkerAuth:
    """Verified worker identity from Supabase JWT."""

    executor_id: str
    user_id: Optional[str] = None
    wallet_address: Optional[str] = None
    auth_method: str = "jwt"  # "jwt" | "body_fallback"


async def verify_worker_auth(
    request: Request,
    authorization: Optional[str] = Header(None, description="Bearer <supabase_jwt>"),
) -> Optional[WorkerAuth]:
    """
    Verify worker identity via Supabase JWT.

    Extracts user_id from the JWT ``sub`` claim, then resolves it to an
    executor_id via the ``executors.user_id`` column.

    Behaviour controlled by ``EM_REQUIRE_WORKER_AUTH`` env var:
      - **false** (default): If no token or invalid token, log a warning and
        return ``None``.  The calling endpoint should fall back to the
        executor_id supplied in the request body.
      - **true**: Reject with 401/403 when the token is missing or invalid.

    Usage in routes::

        @router.post("/tasks/{task_id}/submit")
        async def submit_work(
            ...,
            worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
        ):
            ...
    """
    # --- Try to extract and validate the JWT ---
    if not authorization or not authorization.startswith("Bearer "):
        if _REQUIRE_WORKER_AUTH:
            raise HTTPException(
                status_code=401,
                detail="Authorization header required (Bearer <supabase_jwt>)",
                headers={"WWW-Authenticate": "Bearer"},
            )
        logger.warning(
            "SECURITY_AUDIT action=worker_auth.missing "
            "path=%s (EM_REQUIRE_WORKER_AUTH=false, allowing)",
            request.url.path,
        )
        return None

    token = authorization[7:].strip()
    if not token:
        if _REQUIRE_WORKER_AUTH:
            raise HTTPException(status_code=401, detail="Empty token")
        logger.warning(
            "SECURITY_AUDIT action=worker_auth.empty_token path=%s", request.url.path
        )
        return None

    # Decode the Supabase JWT (reuse h2a decode logic)
    try:
        import jwt as pyjwt

        from .h2a import _decode_supabase_jwt

        payload = _decode_supabase_jwt(token, pyjwt)

        user_id = payload.get("sub") or payload.get("user_id")
        if not user_id:
            if _REQUIRE_WORKER_AUTH:
                raise HTTPException(status_code=401, detail="Invalid token: no user_id")
            logger.warning(
                "SECURITY_AUDIT action=worker_auth.no_user_id path=%s", request.url.path
            )
            return None

        # Resolve user_id -> executor_id via executors table
        try:
            from supabase_client import get_client

            client = get_client()
            result = (
                client.table("executors")
                .select("id, wallet_address")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )

            if not result.data:
                if _REQUIRE_WORKER_AUTH:
                    raise HTTPException(
                        status_code=403,
                        detail="No executor profile linked to this account",
                    )
                logger.warning(
                    "SECURITY_AUDIT action=worker_auth.no_executor user_id=%s path=%s",
                    user_id,
                    request.url.path,
                )
                return None

            executor = result.data[0]
            return WorkerAuth(
                executor_id=executor["id"],
                user_id=user_id,
                wallet_address=executor.get("wallet_address"),
                auth_method="jwt",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error resolving executor for user %s: %s", user_id, e)
            if _REQUIRE_WORKER_AUTH:
                raise HTTPException(
                    status_code=500,
                    detail="Could not resolve executor identity",
                )
            return None

    except HTTPException:
        raise
    except ImportError:
        logger.error("JWT library (PyJWT) not available for worker auth")
        if _REQUIRE_WORKER_AUTH:
            raise HTTPException(status_code=500, detail="JWT library not available")
        return None
    except Exception as e:
        if _REQUIRE_WORKER_AUTH:
            raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
        logger.warning(
            "SECURITY_AUDIT action=worker_auth.invalid_token path=%s error=%s",
            request.url.path,
            e,
        )
        return None


def _enforce_worker_identity(
    worker_auth: Optional[WorkerAuth],
    body_executor_id: str,
    request_path: str,
) -> str:
    """
    Compare verified executor_id from JWT with the one in the request body.

    Returns the authoritative executor_id to use.

    When ``EM_REQUIRE_WORKER_AUTH=true`` and the IDs mismatch, raises 403.
    When ``false``, logs a warning and falls back to the body value.
    """
    if worker_auth is None:
        # No JWT auth — feature flag is off or token was missing
        logger.warning(
            "SECURITY_AUDIT action=worker_auth.body_fallback executor_id=%s path=%s",
            body_executor_id[:8] if body_executor_id else "none",
            request_path,
        )
        return body_executor_id

    if worker_auth.executor_id != body_executor_id:
        if _REQUIRE_WORKER_AUTH:
            logger.warning(
                "SECURITY_AUDIT action=worker_auth.mismatch "
                "jwt_executor=%s body_executor=%s path=%s",
                worker_auth.executor_id[:8],
                body_executor_id[:8],
                request_path,
            )
            raise HTTPException(
                status_code=403,
                detail="Executor ID in request does not match authenticated identity",
            )
        logger.warning(
            "SECURITY_AUDIT action=worker_auth.mismatch_warn "
            "jwt_executor=%s body_executor=%s path=%s "
            "(EM_REQUIRE_WORKER_AUTH=false, allowing body value)",
            worker_auth.executor_id[:8],
            body_executor_id[:8],
            request_path,
        )
        return body_executor_id

    return worker_auth.executor_id


def clear_api_key_cache() -> int:
    """
    Clear the API key cache (thread-safe).

    Returns:
        Number of entries cleared
    """
    global _api_key_cache, _api_key_cache_timestamps
    with _api_key_cache_lock:
        count = len(_api_key_cache)
        if TTLCache is not None:
            _api_key_cache = TTLCache(
                maxsize=_API_KEY_CACHE_MAXSIZE, ttl=_API_KEY_CACHE_TTL_SECONDS
            )
        else:
            _api_key_cache = {}
        _api_key_cache_timestamps = {}
    return count


def invalidate_api_key(key_hash: str) -> bool:
    """
    Invalidate a specific API key in cache (thread-safe).

    Args:
        key_hash: Hash of the key to invalidate

    Returns:
        True if key was in cache and invalidated
    """
    with _api_key_cache_lock:
        if key_hash in _api_key_cache:
            del _api_key_cache[key_hash]
            _api_key_cache_timestamps.pop(key_hash, None)
            return True
    return False
