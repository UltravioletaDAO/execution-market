"""
Focused tests for admin authentication dependency.
"""

import pytest

pytestmark = pytest.mark.core
from fastapi import HTTPException

from ..api.admin import verify_admin_key


@pytest.mark.asyncio
async def test_verify_admin_key_accepts_bearer_header(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    result = await verify_admin_key(
        authorization="Bearer supersecret",
        x_admin_key=None,
        x_admin_actor=None,
    )

    assert result["role"] == "admin"
    assert result["auth_source"] == "authorization"


@pytest.mark.asyncio
async def test_verify_admin_key_accepts_x_admin_key_header(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    result = await verify_admin_key(
        authorization=None,
        x_admin_key="supersecret",
        x_admin_actor=None,
    )

    assert result["role"] == "admin"
    assert result["auth_source"] == "x-admin-key"


@pytest.mark.asyncio
async def test_verify_admin_key_rejects_query_param(monkeypatch):
    """Query-param auth was removed in Phase 0.4 because ?admin_key=... leaks
    into ALB access logs, browser history, and proxy caches.

    The signature no longer accepts ``admin_key`` as a Query kwarg, so the
    caller cannot pass it. A real HTTP request with only ``?admin_key=...``
    arrives with no Authorization / X-Admin-Key header, which must yield 401.
    """
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    # Legacy kwarg must not be accepted by the function signature.
    with pytest.raises(TypeError):
        await verify_admin_key(
            authorization=None,
            x_admin_key=None,
            x_admin_actor=None,
            admin_key="supersecret",
        )

    # Simulate a request that ONLY carries ?admin_key=... in the URL — no
    # auth headers reach the dependency, so it must reject with 401.
    with pytest.raises(HTTPException) as exc:
        await verify_admin_key(
            authorization=None,
            x_admin_key=None,
            x_admin_actor=None,
        )

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_admin_key_rejects_invalid_authorization_format(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    with pytest.raises(HTTPException) as exc:
        await verify_admin_key(
            authorization="Token supersecret",
            x_admin_key=None,
            x_admin_actor=None,
        )

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_admin_key_requires_credentials(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    with pytest.raises(HTTPException) as exc:
        await verify_admin_key(
            authorization=None,
            x_admin_key=None,
            x_admin_actor=None,
        )

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_admin_key_requires_server_config(monkeypatch):
    monkeypatch.delenv("EM_ADMIN_KEY", raising=False)

    with pytest.raises(HTTPException) as exc:
        await verify_admin_key(
            authorization="Bearer anything",
            x_admin_key=None,
            x_admin_actor=None,
        )

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_verify_admin_key_captures_actor_id(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    result = await verify_admin_key(
        authorization="Bearer supersecret",
        x_admin_key=None,
        x_admin_actor="alice@example.com",
    )

    assert result["actor_id"] == "alice@example.com"
