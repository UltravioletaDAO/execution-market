"""FIX-P1-02 — evidence presign-download/-upload deny-by-default authz.

The deny-by-default behaviour is gated by EM_REQUIRE_WORKER_AUTH; these tests
run with the flag ON (the target state). A flag-OFF legacy case at the bottom
verifies the endpoint is byte-identical to pre-WS-AUTH main when disabled.

Calls the handler functions directly (broken Starlette TestClient in WSL).
Asserts status codes and whether S3 presigning is reached.
"""

import sys

import pytest

pytestmark = pytest.mark.security

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from api.auth import WorkerAuth, AgentAuth

TASK_ID = "11111111-1111-1111-1111-111111111111"
EXEC_ID = "22222222-2222-2222-2222-222222222222"
KEY = f"tasks/{TASK_ID}/submissions/{EXEC_ID}/abc-photo.jpg"
AGENT_WALLET = "0x" + "ee" * 20


def _request(headers=None):
    req = MagicMock()
    req.url.path = "/api/v1/evidence/presign-download"
    req.headers = headers or {}
    return req


def _no_admin():
    """verify_admin_key that always rejects (not an admin)."""
    return AsyncMock(side_effect=HTTPException(status_code=401))


def _anon_agent():
    return AsyncMock(return_value=AgentAuth(agent_id="2106", auth_method="anonymous"))


async def _download(
    monkeypatch,
    *,
    worker_auth=None,
    agent_read=None,
    admin=None,
    key=KEY,
    task=None,
    task_raises=False,
    enforce=True,
):
    import api.routers.evidence as ev
    import supabase_client

    monkeypatch.setattr(ev, "EVIDENCE_BUCKET", "test-bucket")
    s3 = MagicMock()
    s3.generate_presigned_url.return_value = "https://s3/signed"
    if task_raises:
        get_task = AsyncMock(side_effect=RuntimeError("boom"))
    else:
        get_task = AsyncMock(return_value=task)

    with (
        patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", enforce),
        patch.object(ev, "_get_s3", return_value=s3),
        patch.object(ev, "verify_admin_key", new=(admin or _no_admin())),
        patch.object(ev, "verify_agent_auth_read", new=(agent_read or _anon_agent())),
        patch.object(supabase_client, "get_task", new=get_task),
    ):
        result = await ev.presign_download(
            raw_request=_request(),
            key=key,
            worker_auth=worker_auth,
        )
    return result, s3


@pytest.mark.asyncio
async def test_presign_download_anonymous_is_401_reproduces_bug(monkeypatch):
    """No principal at all → 401, and S3 is never signed (was 200 + URL)."""
    with pytest.raises(HTTPException) as exc:
        await _download(monkeypatch, task={"executor_id": EXEC_ID})
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_presign_download_wrong_worker_is_403(monkeypatch):
    wa = WorkerAuth(executor_id="other-exec", auth_method="jwt")
    with pytest.raises(HTTPException) as exc:
        await _download(monkeypatch, worker_auth=wa, task={"executor_id": EXEC_ID})
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_presign_download_assigned_executor_ok(monkeypatch):
    wa = WorkerAuth(executor_id=EXEC_ID, auth_method="jwt")
    result, s3 = await _download(
        monkeypatch, worker_auth=wa, task={"executor_id": EXEC_ID}
    )
    assert result.download_url == "https://s3/signed"
    s3.generate_presigned_url.assert_called_once()


@pytest.mark.asyncio
async def test_presign_download_publishing_agent_ok(monkeypatch):
    agent_read = AsyncMock(
        return_value=AgentAuth(
            agent_id=AGENT_WALLET,
            wallet_address=AGENT_WALLET,
            auth_method="erc8128",
        )
    )
    result, s3 = await _download(
        monkeypatch,
        agent_read=agent_read,
        task={"executor_id": EXEC_ID, "agent_id": AGENT_WALLET.upper()},
    )
    assert result.download_url == "https://s3/signed"


@pytest.mark.asyncio
async def test_presign_download_anonymous_agent_does_not_match(monkeypatch):
    """auth_method='anonymous' (Agent #2106) must NOT count as a principal."""
    with pytest.raises(HTTPException) as exc:
        await _download(monkeypatch, task={"executor_id": EXEC_ID, "agent_id": "2106"})
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_presign_download_admin_ok(monkeypatch):
    admin = AsyncMock(return_value={"actor": "admin"})
    result, s3 = await _download(monkeypatch, admin=admin, task=None)
    assert result.download_url == "https://s3/signed"


@pytest.mark.asyncio
async def test_presign_download_bad_key_shape_is_403(monkeypatch):
    wa = WorkerAuth(executor_id=EXEC_ID, auth_method="jwt")
    with pytest.raises(HTTPException) as exc:
        await _download(monkeypatch, worker_auth=wa, key="foo/bar")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_presign_download_path_traversal_is_400(monkeypatch):
    wa = WorkerAuth(executor_id=EXEC_ID, auth_method="jwt")
    with pytest.raises(HTTPException) as exc:
        await _download(monkeypatch, worker_auth=wa, key="tasks/../secret")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_presign_download_db_error_fails_closed(monkeypatch):
    wa = WorkerAuth(executor_id=EXEC_ID, auth_method="jwt")
    with pytest.raises(HTTPException) as exc:
        await _download(monkeypatch, worker_auth=wa, task_raises=True)
    assert exc.value.status_code == 503


# --------------------------------------------------------------------------- #
# Upload hardening
# --------------------------------------------------------------------------- #
async def _upload(
    monkeypatch,
    *,
    worker_auth=None,
    agent_read=None,
    admin=None,
    task=None,
    enforce=True,
):
    import api.routers.evidence as ev
    import supabase_client

    monkeypatch.setattr(ev, "EVIDENCE_BUCKET", "test-bucket")
    s3 = MagicMock()
    s3.generate_presigned_url.return_value = "https://s3/put"
    get_task = AsyncMock(return_value=task)

    with (
        patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", enforce),
        patch.object(ev, "_get_s3", return_value=s3),
        patch.object(ev, "verify_admin_key", new=(admin or _no_admin())),
        patch.object(ev, "verify_agent_auth_read", new=(agent_read or _anon_agent())),
        patch.object(supabase_client, "get_task", new=get_task),
    ):
        result = await ev.presign_upload(
            raw_request=_request(),
            task_id=TASK_ID,
            executor_id=EXEC_ID,
            filename="photo.jpg",
            evidence_type="photo",
            content_type="image/jpeg",
            worker_auth=worker_auth,
        )
    return result, s3


@pytest.mark.asyncio
async def test_presign_upload_anonymous_is_401(monkeypatch):
    """No worker JWT → _enforce_worker_identity raises 401 (fail-closed)."""
    with pytest.raises(HTTPException) as exc:
        await _upload(monkeypatch, task={"executor_id": EXEC_ID})
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_presign_upload_assigned_executor_ok(monkeypatch):
    wa = WorkerAuth(executor_id=EXEC_ID, auth_method="jwt")
    result, s3 = await _upload(
        monkeypatch, worker_auth=wa, task={"executor_id": EXEC_ID}
    )
    assert result.upload_url == "https://s3/put"
    s3.generate_presigned_url.assert_called_once()


# --------------------------------------------------------------------------- #
# Flag OFF — byte-identical legacy behaviour (EM_REQUIRE_WORKER_AUTH unset)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_presign_download_anonymous_allowed_when_flag_off(monkeypatch):
    """Legacy: with enforcement off, an anonymous download mints a URL (the
    pre-WS-AUTH behaviour). Deny-by-default only activates when the flag is on."""
    result, s3 = await _download(
        monkeypatch, task={"executor_id": EXEC_ID}, enforce=False
    )
    assert result.download_url == "https://s3/signed"
    s3.generate_presigned_url.assert_called_once()


@pytest.mark.asyncio
async def test_presign_upload_anonymous_allowed_when_flag_off(monkeypatch):
    """Legacy: with enforcement off, an anonymous upload to an unassigned task
    is permitted (soft-auth body fallback)."""
    result, s3 = await _upload(monkeypatch, task=None, enforce=False)
    assert result.upload_url == "https://s3/put"
