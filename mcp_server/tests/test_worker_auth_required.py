"""FIX-P1-01 — worker auth identity resolution, strictly gated by
EM_REQUIRE_WORKER_AUTH, + production boot guard.

The fail-closed behaviour (401/403) only activates when EM_REQUIRE_WORKER_AUTH
is enabled. With the flag OFF (the staged-rollout default) the helpers are
byte-identical to pre-WS-AUTH main: the body value is trusted. Both modes are
covered here.

Exercises the auth helpers directly (the WSL TestClient is broken). Endpoint
behavior is covered transitively: apply/submit call resolve_worker_identity,
all other soft-auth call sites call _enforce_worker_identity.
"""

import sys

import pytest

pytestmark = pytest.mark.security

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from api.auth import (
    WorkerAuth,
    AgentAuth,
    _enforce_worker_identity,
    resolve_worker_identity,
)

EXEC_A = "exec-aaaa"
EXEC_B = "exec-bbbb"
TASK_ID = "task-1234"


@contextmanager
def _enforce(on: bool):
    """Patch the worker-auth master switch for the duration of the block."""
    with patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", on):
        yield


def _request(headers=None):
    req = MagicMock()
    req.url.path = "/api/v1/tasks/task-1234/apply"
    req.headers = headers or {}
    return req


# --------------------------------------------------------------------------- #
# _enforce_worker_identity — fail-closed (flag ON)
# --------------------------------------------------------------------------- #
def test_enforce_worker_identity_no_auth_raises_401_when_on():
    """Reproduces the bug: previously returned the body value, now 401."""
    with _enforce(True):
        with pytest.raises(HTTPException) as exc:
            _enforce_worker_identity(None, EXEC_A, "/p")
        assert exc.value.status_code == 401


def test_enforce_worker_identity_mismatch_raises_403_when_on():
    wa = WorkerAuth(executor_id=EXEC_A, auth_method="jwt")
    with _enforce(True):
        with pytest.raises(HTTPException) as exc:
            _enforce_worker_identity(wa, EXEC_B, "/p")
        assert exc.value.status_code == 403


def test_enforce_worker_identity_match_passes_when_on():
    wa = WorkerAuth(executor_id=EXEC_A, auth_method="jwt")
    with _enforce(True):
        assert _enforce_worker_identity(wa, EXEC_A, "/p") == EXEC_A


def test_enforce_worker_identity_empty_body_uses_jwt_when_on():
    wa = WorkerAuth(executor_id=EXEC_A, auth_method="jwt")
    with _enforce(True):
        assert _enforce_worker_identity(wa, "", "/p") == EXEC_A


# --------------------------------------------------------------------------- #
# _enforce_worker_identity — legacy permissive (flag OFF, byte-identical)
# --------------------------------------------------------------------------- #
def test_enforce_worker_identity_no_auth_falls_back_to_body_when_off():
    with _enforce(False):
        assert _enforce_worker_identity(None, EXEC_A, "/p") == EXEC_A


def test_enforce_worker_identity_mismatch_allows_body_when_off():
    wa = WorkerAuth(executor_id=EXEC_A, auth_method="jwt")
    with _enforce(False):
        # Legacy: a mismatch logs a warning but returns the body value.
        assert _enforce_worker_identity(wa, EXEC_B, "/p") == EXEC_B


def test_enforce_worker_identity_match_passes_when_off():
    wa = WorkerAuth(executor_id=EXEC_A, auth_method="jwt")
    with _enforce(False):
        assert _enforce_worker_identity(wa, EXEC_A, "/p") == EXEC_A


# --------------------------------------------------------------------------- #
# resolve_worker_identity — fail-closed (flag ON): JWT, anon, H2H agent path
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_resolve_worker_identity_jwt_authoritative_when_on():
    wa = WorkerAuth(executor_id=EXEC_A, auth_method="jwt")
    with _enforce(True):
        out = await resolve_worker_identity(_request(), wa, EXEC_A, task_id=TASK_ID)
    assert out == EXEC_A


@pytest.mark.asyncio
async def test_resolve_worker_identity_jwt_mismatch_403_when_on():
    wa = WorkerAuth(executor_id=EXEC_A, auth_method="jwt")
    with _enforce(True):
        with pytest.raises(HTTPException) as exc:
            await resolve_worker_identity(_request(), wa, EXEC_B, task_id=TASK_ID)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_resolve_worker_identity_anon_no_sig_raises_401_when_on():
    # No worker_auth and no signature headers → 401 (fail-closed).
    with _enforce(True):
        with pytest.raises(HTTPException) as exc:
            await resolve_worker_identity(
                _request(headers={}), None, EXEC_A, task_id=TASK_ID
            )
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_resolve_worker_identity_agent_owns_task_allowed_when_on():
    """H2H: publishing agent (ERC-8128) may act for its assigned executor."""
    headers = {"signature": "sig", "signature-input": "sig-in"}
    agent = AgentAuth(agent_id="0xAGENT", auth_method="erc8128")
    fake_task = {"executor_id": EXEC_A}

    with (
        _enforce(True),
        patch("api.auth.verify_agent_auth_write", new=AsyncMock(return_value=agent)),
        patch("api.auth.verify_agent_owns_task", new=AsyncMock(return_value=True)),
        patch("supabase_client.get_task", new=AsyncMock(return_value=fake_task)),
    ):
        out = await resolve_worker_identity(
            _request(headers=headers), None, EXEC_A, task_id=TASK_ID
        )
    assert out == EXEC_A


@pytest.mark.asyncio
async def test_resolve_worker_identity_agent_not_owner_403_when_on():
    headers = {"signature": "sig", "signature-input": "sig-in"}
    agent = AgentAuth(agent_id="0xAGENT", auth_method="erc8128")
    with (
        _enforce(True),
        patch("api.auth.verify_agent_auth_write", new=AsyncMock(return_value=agent)),
        patch("api.auth.verify_agent_owns_task", new=AsyncMock(return_value=False)),
    ):
        with pytest.raises(HTTPException) as exc:
            await resolve_worker_identity(
                _request(headers=headers), None, EXEC_A, task_id=TASK_ID
            )
    assert exc.value.status_code == 403


# --------------------------------------------------------------------------- #
# resolve_worker_identity — legacy permissive (flag OFF, byte-identical)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_resolve_worker_identity_anon_falls_back_to_body_when_off():
    # Legacy: with the flag off, an anonymous caller's body value is trusted and
    # the ERC-8128 signature path is NEVER reached (headers untouched).
    with _enforce(False):
        out = await resolve_worker_identity(
            _request(headers={}), None, EXEC_A, task_id=TASK_ID
        )
    assert out == EXEC_A


@pytest.mark.asyncio
async def test_resolve_worker_identity_jwt_authoritative_when_off():
    wa = WorkerAuth(executor_id=EXEC_A, auth_method="jwt")
    with _enforce(False):
        out = await resolve_worker_identity(_request(), wa, EXEC_A, task_id=TASK_ID)
    assert out == EXEC_A


# --------------------------------------------------------------------------- #
# Production boot assertion
# --------------------------------------------------------------------------- #
def test_boot_assert_worker_auth_required(monkeypatch):
    try:
        import main
    except ModuleNotFoundError as e:  # optional logging dep missing in some envs
        pytest.skip(f"main import unavailable in this env: {e}")

    # production + flag off → raises
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("EM_REQUIRE_WORKER_AUTH", "false")
    with pytest.raises(RuntimeError):
        main._assert_worker_auth_required_in_production()

    # production + flag true → no raise
    monkeypatch.setenv("EM_REQUIRE_WORKER_AUTH", "true")
    main._assert_worker_auth_required_in_production()

    # non-production → no raise regardless
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("EM_REQUIRE_WORKER_AUTH", "false")
    main._assert_worker_auth_required_in_production()
