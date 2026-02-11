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
        admin_key=None,
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
        admin_key=None,
    )

    assert result["role"] == "admin"
    assert result["auth_source"] == "x-admin-key"


@pytest.mark.asyncio
async def test_verify_admin_key_accepts_legacy_query_param(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    result = await verify_admin_key(
        authorization=None,
        x_admin_key=None,
        x_admin_actor=None,
        admin_key="supersecret",
    )

    assert result["role"] == "admin"
    assert result["auth_source"] == "query"


@pytest.mark.asyncio
async def test_verify_admin_key_rejects_invalid_authorization_format(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    with pytest.raises(HTTPException) as exc:
        await verify_admin_key(
            authorization="Token supersecret",
            x_admin_key=None,
            x_admin_actor=None,
            admin_key=None,
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
            admin_key=None,
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
            admin_key=None,
        )

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_verify_admin_key_captures_actor_id(monkeypatch):
    monkeypatch.setenv("EM_ADMIN_KEY", "supersecret")

    result = await verify_admin_key(
        authorization="Bearer supersecret",
        x_admin_key=None,
        x_admin_actor="alice@example.com",
        admin_key=None,
    )

    assert result["actor_id"] == "alice@example.com"
