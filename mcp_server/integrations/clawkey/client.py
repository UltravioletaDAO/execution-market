"""ClawKey KYA HTTP client.

Public-read API at api.clawkey.ai/v1. No authentication: KYA bindings are a
public trust signal by design (same posture as ERC-8004 reputation reads).

Two endpoints:
  GET /v1/agent/verify/public-key/{pubkey_b58}
  GET /v1/agent/verify/device/{device_id}

Both return:
  {
    "registered": bool,
    "verified": bool,
    "humanId": str | null,
    "registeredAt": str | null   # ISO-8601 timestamp
  }

Caching:
  - In-memory dict, TTL configurable via PlatformConfig key
    `clawkey.cache_ttl_seconds` (default 300s).
  - Two key spaces: `pk:{pubkey}` and `dev:{device_id}`. They never collide.
  - Cache stores both hits and misses (a 200-with-`registered=false` is also
    a fact worth caching — avoids hammering upstream when an agent is
    repeatedly asked about a never-registered key).
  - Errors (network / non-200) are NOT cached: callers retry on transient
    failures rather than getting stale "down" answers.

Failure mode: ClawKey is additive. The router will surface a 503-style
result if upstream is down; downstream code should treat that as "unknown",
not "unverified".
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Defaults (overridable via PlatformConfig)
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://api.clawkey.ai"
DEFAULT_VERIFY_BY_PUBKEY_PATH = "/v1/agent/verify/public-key/{pubkey}"
DEFAULT_VERIFY_BY_DEVICE_PATH = "/v1/agent/verify/device/{device_id}"
DEFAULT_CACHE_TTL_SECONDS = 300  # 5 min
DEFAULT_HTTP_TIMEOUT_SECONDS = 10.0


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClawKeyResult:
    """Snapshot of an agent's KYA status from upstream.

    `verified` implies `registered`. `human_id` is None when not registered;
    upstream may also withhold it for privacy when registered-but-unverified.
    """

    registered: bool
    verified: bool
    human_id: Optional[str]
    registered_at: Optional[str]
    raw: dict


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


# Module-level cache: { key: (expiry_epoch, ClawKeyResult) }
_cache: dict[str, tuple[float, ClawKeyResult]] = {}


def _cache_get(key: str) -> Optional[ClawKeyResult]:
    entry = _cache.get(key)
    if entry is None:
        return None
    expiry, result = entry
    if time.time() >= expiry:
        # Lazy expiration; do not raise on missing key in case of races.
        _cache.pop(key, None)
        return None
    return result


def _cache_put(key: str, result: ClawKeyResult, ttl_seconds: float) -> None:
    _cache[key] = (time.time() + ttl_seconds, result)


def clear_cache() -> None:
    """Drop every cached entry. Test helper + manual ops escape hatch."""
    _cache.clear()


# ---------------------------------------------------------------------------
# PlatformConfig resolution
# ---------------------------------------------------------------------------


async def _resolved_config() -> dict:
    """Load runtime overrides from PlatformConfig with safe defaults.

    All keys are optional — they only matter for ops who need to point at
    a sandbox or change cache TTL without redeploying.
    """
    from config.platform_config import PlatformConfig

    return {
        "base": await PlatformConfig.get("clawkey.api_base_url", DEFAULT_BASE_URL),
        "pubkey_path": await PlatformConfig.get(
            "clawkey.verify_by_public_key_path", DEFAULT_VERIFY_BY_PUBKEY_PATH
        ),
        "device_path": await PlatformConfig.get(
            "clawkey.verify_by_device_path", DEFAULT_VERIFY_BY_DEVICE_PATH
        ),
        "cache_ttl": float(
            await PlatformConfig.get(
                "clawkey.cache_ttl_seconds", DEFAULT_CACHE_TTL_SECONDS
            )
        ),
        "http_timeout": float(
            await PlatformConfig.get(
                "clawkey.http_timeout_seconds", DEFAULT_HTTP_TIMEOUT_SECONDS
            )
        ),
    }


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_response(payload: Any) -> ClawKeyResult:
    """Normalize an upstream JSON body into a ClawKeyResult.

    Defensive: upstream may use camelCase OR snake_case; missing fields
    default to safe values (registered=False, verified=False).
    """
    data = payload if isinstance(payload, dict) else {}
    registered = bool(data.get("registered", False))
    verified = bool(data.get("verified", False))
    # Accept both camel + snake variants without judging upstream
    human_id = data.get("humanId") or data.get("human_id")
    registered_at = data.get("registeredAt") or data.get("registered_at")
    return ClawKeyResult(
        registered=registered,
        verified=verified,
        human_id=str(human_id) if human_id else None,
        registered_at=str(registered_at) if registered_at else None,
        raw=data,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def verify_by_public_key(
    pubkey_b58: str,
    *,
    use_cache: bool = True,
) -> ClawKeyResult:
    """Look up an agent by its Ed25519 public key (base58).

    Set `use_cache=False` from the manual-refresh router endpoint to force
    a fresh upstream hit.
    """
    if not pubkey_b58:
        raise ValueError("pubkey_b58 is required")

    cache_key = f"pk:{pubkey_b58}"
    if use_cache:
        hit = _cache_get(cache_key)
        if hit is not None:
            return hit

    cfg = await _resolved_config()
    path = cfg["pubkey_path"].format(pubkey=pubkey_b58)
    url = f"{cfg['base'].rstrip('/')}{path}"

    async with httpx.AsyncClient(timeout=cfg["http_timeout"]) as client:
        resp = await client.get(url, headers={"Accept": "application/json"})

    if resp.status_code == 404:
        # Upstream tells us "no such key" — that's a legitimate negative
        # answer worth caching to avoid hammering them on a missing agent.
        result = ClawKeyResult(
            registered=False, verified=False, human_id=None, registered_at=None, raw={}
        )
        _cache_put(cache_key, result, cfg["cache_ttl"])
        return result

    if resp.status_code != 200:
        body = resp.text[:200]
        logger.error(
            "ClawKey verify_by_public_key failed: status=%d body=%s",
            resp.status_code,
            body,
        )
        raise httpx.HTTPStatusError(
            f"ClawKey returned {resp.status_code}: {body}",
            request=resp.request,
            response=resp,
        )

    result = _parse_response(resp.json())
    _cache_put(cache_key, result, cfg["cache_ttl"])
    return result


async def verify_by_device_id(
    device_id: str,
    *,
    use_cache: bool = True,
) -> ClawKeyResult:
    """Look up an agent by its device id.

    Same caching + error semantics as `verify_by_public_key`.
    """
    if not device_id:
        raise ValueError("device_id is required")

    cache_key = f"dev:{device_id}"
    if use_cache:
        hit = _cache_get(cache_key)
        if hit is not None:
            return hit

    cfg = await _resolved_config()
    path = cfg["device_path"].format(device_id=device_id)
    url = f"{cfg['base'].rstrip('/')}{path}"

    async with httpx.AsyncClient(timeout=cfg["http_timeout"]) as client:
        resp = await client.get(url, headers={"Accept": "application/json"})

    if resp.status_code == 404:
        result = ClawKeyResult(
            registered=False, verified=False, human_id=None, registered_at=None, raw={}
        )
        _cache_put(cache_key, result, cfg["cache_ttl"])
        return result

    if resp.status_code != 200:
        body = resp.text[:200]
        logger.error(
            "ClawKey verify_by_device_id failed: status=%d body=%s",
            resp.status_code,
            body,
        )
        raise httpx.HTTPStatusError(
            f"ClawKey returned {resp.status_code}: {body}",
            request=resp.request,
            response=resp,
        )

    result = _parse_response(resp.json())
    _cache_put(cache_key, result, cfg["cache_ttl"])
    return result
