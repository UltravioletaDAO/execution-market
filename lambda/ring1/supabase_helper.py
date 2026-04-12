"""
Lightweight Supabase REST client for Ring 1 Lambda.

Uses httpx to call Supabase PostgREST directly instead of the full
supabase-py client.  Secrets are injected at cold-start via init().

This module mirrors the subset of mcp_server/supabase_client.py that
the background_runner needs: get_submission, update_auto_check,
update_ai_verification, update_perceptual_hashes, get_existing_hashes.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Module-level state set once by init() during cold start.
_url: Optional[str] = None
_key: Optional[str] = None

# Reusable timeout for all Supabase calls.
_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


def init(url: str, service_key: str) -> None:
    """Inject Supabase credentials (called once at Lambda cold start)."""
    global _url, _key
    _url = url.rstrip("/")
    _key = service_key
    logger.info("supabase_helper.init: url=%s key=set", _url)


def _headers() -> Dict[str, str]:
    assert _url and _key, "supabase_helper.init() not called"
    return {
        "apikey": _key,
        "Authorization": f"Bearer {_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def _rest_url(path: str) -> str:
    return f"{_url}/rest/v1/{path}"


# ── Reads ────────────────────────────────────────────────────────────────


async def get_submission(submission_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single submission by ID (with nested task and executor)."""
    url = _rest_url(
        f"submissions?id=eq.{submission_id}"
        f"&select=*,task:tasks(*),executor:executors(id,display_name,wallet_address,reputation_score,erc8004_agent_id)"
    )
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.get(url, headers=_headers())
        r.raise_for_status()
        data = r.json()
        return data[0] if data else None


async def get_existing_perceptual_hashes(
    exclude_task_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Query recent submissions with perceptual hashes for duplicate detection."""
    qs = (
        "submissions?select=id,task_id,perceptual_hashes"
        "&perceptual_hashes=not.is.null"
        "&order=submitted_at.desc"
        f"&limit={limit}"
    )
    if exclude_task_id:
        qs += f"&task_id=neq.{exclude_task_id}"

    url = _rest_url(qs)
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.get(url, headers=_headers())
        r.raise_for_status()
        rows = r.json()

    # Normalize: PostgREST returns perceptual_hashes as JSONB.
    result = []
    for row in rows:
        hashes = row.get("perceptual_hashes") or {}
        result.append(
            {"id": row["id"], "task_id": row.get("task_id"), "hashes": hashes}
        )
    return result


# ── Writes ───────────────────────────────────────────────────────────────


async def update_auto_check(
    submission_id: str,
    passed: bool,
    details: Dict[str, Any],
) -> None:
    """Update auto_check_passed + auto_check_details on a submission."""
    url = _rest_url(f"submissions?id=eq.{submission_id}")
    payload = {"auto_check_passed": passed, "auto_check_details": details}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.patch(url, json=payload, headers=_headers())
        r.raise_for_status()
    logger.debug("update_auto_check %s passed=%s", submission_id[:8], passed)


async def update_ai_verification(
    submission_id: str,
    result: Dict[str, Any],
) -> None:
    """Store ai_verification_result JSONB on a submission."""
    url = _rest_url(f"submissions?id=eq.{submission_id}")
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.patch(
            url, json={"ai_verification_result": result}, headers=_headers()
        )
        r.raise_for_status()
    logger.debug("update_ai_verification %s", submission_id[:8])


async def update_perceptual_hashes(
    submission_id: str,
    hashes: Dict[str, Any],
) -> None:
    """Store perceptual_hashes JSONB on a submission."""
    url = _rest_url(f"submissions?id=eq.{submission_id}")
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.patch(url, json={"perceptual_hashes": hashes}, headers=_headers())
        r.raise_for_status()
    logger.debug("update_perceptual_hashes %s", submission_id[:8])
