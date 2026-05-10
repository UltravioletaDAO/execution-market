"""Shared admin authentication dependency for internal/admin surfaces."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Header, HTTPException, Query

logger = logging.getLogger(__name__)


async def verify_admin_key(
    authorization: Optional[str] = Header(None, description="Bearer admin key"),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    x_admin_actor: Optional[str] = Header(None, alias="X-Admin-Actor"),
    admin_key: Optional[str] = Query(None, alias="admin_key"),
):
    """Verify legacy admin API access, including the historic query fallback."""

    return _verify_admin_key(
        authorization=authorization,
        x_admin_key=x_admin_key,
        x_admin_actor=x_admin_actor,
        admin_key=admin_key,
        allow_query_param=True,
    )


async def verify_internal_admin_key(
    authorization: Optional[str] = Header(None, description="Bearer admin key"),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    x_admin_actor: Optional[str] = Header(None, alias="X-Admin-Actor"),
    admin_key: Optional[str] = Query(None, alias="admin_key"),
):
    """Verify internal/admin access without allowing query-string secrets."""

    return _verify_admin_key(
        authorization=authorization,
        x_admin_key=x_admin_key,
        x_admin_actor=x_admin_actor,
        admin_key=admin_key,
        allow_query_param=False,
    )


def _verify_admin_key(
    *,
    authorization: Optional[str],
    x_admin_key: Optional[str],
    x_admin_actor: Optional[str],
    admin_key: Optional[str],
    allow_query_param: bool,
):
    """
    Verify admin key using constant-time comparison.

    Preferred auth order:
    1. Authorization: Bearer <admin_key>
    2. X-Admin-Key: <admin_key>
    3. admin_key query param (legacy fallback, disabled for internal/admin)
    """
    import os
    import secrets as _secrets

    expected_key = os.environ.get("EM_ADMIN_KEY", "").strip()

    if not expected_key:
        raise HTTPException(status_code=503, detail="Admin access not configured")

    provided_key = None
    source = None

    if admin_key and not allow_query_param:
        raise HTTPException(
            status_code=401,
            detail="Admin query-param auth is not allowed for internal/admin routes",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if authorization:
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format. Use: Bearer <admin_key>",
                headers={"WWW-Authenticate": "Bearer"},
            )
        provided_key = authorization[7:].strip()
        source = "authorization"
    elif x_admin_key:
        provided_key = x_admin_key.strip()
        source = "x-admin-key"
    elif admin_key:
        provided_key = admin_key.strip()
        source = "query"
        logger.warning("Legacy admin auth via query param used")
    else:
        raise HTTPException(
            status_code=401,
            detail="Admin credentials required (Authorization Bearer or X-Admin-Key)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not provided_key:
        raise HTTPException(
            status_code=401,
            detail="Admin key is empty",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not _secrets.compare_digest(provided_key.encode(), expected_key.encode()):
        raise HTTPException(status_code=403, detail="Invalid admin key")

    actor_id = ((x_admin_actor or "").strip()[:128]) or "system"

    return {
        "role": "admin",
        "auth_source": source,
        "actor_id": actor_id,
    }
