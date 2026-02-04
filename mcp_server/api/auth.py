"""
API Authentication Module

Handles API key verification, tier determination, and agent authorization.
"""

import os
import logging
import hashlib
import secrets
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, Header, Request, Depends
from pydantic import BaseModel

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


# Cache for API key validation with TTL (in production, use Redis)
_API_KEY_CACHE_TTL_SECONDS = 300  # 5 minutes
_api_key_cache: dict[str, APIKeyData] = {}
_api_key_cache_timestamps: dict[str, float] = {}


def _is_cache_entry_valid(key_hash: str) -> bool:
    """Check if a cache entry is still within its TTL."""
    import time
    cached_at = _api_key_cache_timestamps.get(key_hash)
    if cached_at is None:
        return False
    return (time.time() - cached_at) < _API_KEY_CACHE_TTL_SECONDS


async def verify_api_key(
    authorization: str = Header(..., description="Bearer token with API key")
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
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Use: Bearer <api_key>",
            headers={"WWW-Authenticate": "Bearer"}
        )

    api_key = authorization[7:].strip()

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key is empty",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Validate key format (should be em_<tier>_<random>)
    if not _is_valid_key_format(api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key format"
        )

    # Check cache first (with TTL)
    key_hash = _hash_key(api_key)
    if key_hash in _api_key_cache and _is_cache_entry_valid(key_hash):
        cached = _api_key_cache[key_hash]
        if cached.is_valid:
            cached.last_used = datetime.now(timezone.utc)
            return cached
        else:
            raise HTTPException(
                status_code=401,
                detail="API key has been revoked"
            )
    elif key_hash in _api_key_cache and not _is_cache_entry_valid(key_hash):
        # TTL expired, remove stale entry
        del _api_key_cache[key_hash]
        _api_key_cache_timestamps.pop(key_hash, None)

    # Validate against database
    key_data = await _validate_key_from_db(api_key, key_hash)

    if not key_data or not key_data.is_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key"
        )

    # Cache the validated key with TTL
    import time
    _api_key_cache[key_hash] = key_data
    _api_key_cache_timestamps[key_hash] = time.time()

    return key_data


async def verify_api_key_optional(
    authorization: Optional[str] = Header(None, description="Optional Bearer token")
) -> Optional[APIKeyData]:
    """
    Optionally verify API key (for public endpoints with optional auth).

    Returns None if no authorization header provided.
    """
    if not authorization:
        return None

    try:
        return await verify_api_key(authorization)
    except HTTPException:
        return None


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
    - Legacy (deprecated): chamba_<tier>_<32 chars>, sk_chamba_<32 chars>
    """
    if not api_key:
        return False

    # Legacy format (deprecated)
    if api_key.startswith("sk_chamba_"):
        return len(api_key) >= 42  # sk_chamba_ + 32 chars

    # Legacy format (deprecated)
    if api_key.startswith("sk_em_"):
        return len(api_key) >= 38  # sk_em_ + 32 chars

    # New format
    valid_prefixes = [
        "em_free_",
        "em_starter_",
        "em_growth_",
        "em_enterprise_",
        # Legacy (deprecated) prefixes
        "chamba_free_",
        "chamba_starter_",
        "chamba_growth_",
        "chamba_enterprise_",
    ]

    for prefix in valid_prefixes:
        if api_key.startswith(prefix):
            suffix = api_key[len(prefix):]
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
        result = client.table("api_keys").select(
            "id, agent_id, tier, organization_id, is_active, created_at, last_used_at"
        ).eq("key_hash", key_hash).single().execute()

        if not result.data:
            logger.warning("API key not found in database")
            return None

        data = result.data

        if not data.get("is_active", False):
            logger.warning("API key is inactive: agent_id=%s", data.get("agent_id"))
            return None

        # Update last_used_at
        client.table("api_keys").update({
            "last_used_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", data["id"]).execute()

        return APIKeyData(
            key_hash=key_hash,
            agent_id=data["agent_id"],
            tier=data.get("tier", APITier.FREE),
            organization_id=data.get("organization_id"),
            is_valid=True,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            last_used=datetime.now(timezone.utc)
        )

    except Exception as e:
        logger.error("Error validating API key: %s", str(e))

        # In development, allow keys matching pattern without DB (requires explicit opt-in)
        if (os.environ.get("ENVIRONMENT") == "development"
                and os.environ.get("DEV_ALLOW_FAKE_KEYS") == "true"):
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

    if api_key.startswith("em_enterprise_") or api_key.startswith("chamba_enterprise_"):
        tier = APITier.ENTERPRISE
    elif api_key.startswith("em_growth_") or api_key.startswith("chamba_growth_"):
        tier = APITier.GROWTH
    elif api_key.startswith("em_starter_") or api_key.startswith("chamba_starter_"):
        tier = APITier.STARTER
    elif api_key.startswith("sk_em_") or api_key.startswith("sk_chamba_"):
        # Legacy key, assume starter tier
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
        last_used=datetime.now(timezone.utc)
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

        return task.get("agent_id") == agent_id

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

        return task.get("agent_id") == agent_id

    except Exception as e:
        logger.error("Error verifying submission ownership: %s", str(e))
        return False


def clear_api_key_cache() -> int:
    """
    Clear the API key cache.

    Returns:
        Number of entries cleared
    """
    global _api_key_cache, _api_key_cache_timestamps
    count = len(_api_key_cache)
    _api_key_cache = {}
    _api_key_cache_timestamps = {}
    return count


def invalidate_api_key(key_hash: str) -> bool:
    """
    Invalidate a specific API key in cache.

    Args:
        key_hash: Hash of the key to invalidate

    Returns:
        True if key was in cache and invalidated
    """
    if key_hash in _api_key_cache:
        del _api_key_cache[key_hash]
        _api_key_cache_timestamps.pop(key_hash, None)
        return True
    return False
