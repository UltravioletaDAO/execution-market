"""FIX-P1-06 / FIX-P1-07 — World ID verify binds to the verified nullifier and
the authenticated executor, never the client-supplied values.

Covers:
  * client.py: API-sourced nullifier only; empty API nullifier → hard failure.
  * worldid.py: auth required; executor from JWT; uniqueness/insert keyed on the
    API nullifier; sybil replay with a fresh fake nullifier is blocked (409).

Handlers are called directly (broken Starlette TestClient in WSL).
"""

import pytest

pytestmark = pytest.mark.worldid

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from api.auth import WorkerAuth
from integrations.worldid.client import VerificationResult


REAL_NULL = "0xREAL00000000000000000000000000000000000000000000000000000000real"
EXEC_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
EXEC_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


# --------------------------------------------------------------------------- #
# client.py — nullifier provenance
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_verify_rejects_when_api_returns_no_nullifier():
    """Reproduces the bug: API success WITHOUT a nullifier must hard-fail
    (pre-fix it silently returned the client value)."""
    from integrations.worldid import client as wc

    resp = MagicMock(status_code=200)
    resp.json.return_value = {"success": True, "verification_level": "orb"}
    fake_http = MagicMock()
    fake_http.post = AsyncMock(return_value=resp)
    fake_ctx = MagicMock()
    fake_ctx.__aenter__ = AsyncMock(return_value=fake_http)
    fake_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.object(wc, "WORLD_ID_RP_ID", "rp-test"),
        patch.object(wc.httpx, "AsyncClient", return_value=fake_ctx),
    ):
        result = await wc.verify_world_id_proof(
            nullifier_hash="0xATTACKER",
            verification_level="orb",
            responses=[{"proof": "x"}],
        )
    assert result.success is False
    assert "nullifier" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_verify_uses_api_nullifier_not_client():
    from integrations.worldid import client as wc

    resp = MagicMock(status_code=200)
    resp.json.return_value = {
        "success": True,
        "nullifier": REAL_NULL,
        "verification_level": "orb",
    }
    fake_http = MagicMock()
    fake_http.post = AsyncMock(return_value=resp)
    fake_ctx = MagicMock()
    fake_ctx.__aenter__ = AsyncMock(return_value=fake_http)
    fake_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.object(wc, "WORLD_ID_RP_ID", "rp-test"),
        patch.object(wc.httpx, "AsyncClient", return_value=fake_ctx),
    ):
        result = await wc.verify_world_id_proof(
            nullifier_hash="0xCLIENTFAKE",
            verification_level="orb",
            responses=[{"proof": "x"}],
        )
    assert result.success is True
    assert result.nullifier_hash == REAL_NULL


# --------------------------------------------------------------------------- #
# worldid.py — endpoint binding
# --------------------------------------------------------------------------- #
class _FakeTable:
    def __init__(self, store, name):
        self._store = store
        self._name = name
        self._eq = {}

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._eq[col] = val
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        rows = self._store.get(self._name, [])
        matched = [r for r in rows if all(r.get(k) == v for k, v in self._eq.items())]
        return MagicMock(data=matched)

    def insert(self, row):
        self._pending = row
        return self

    def update(self, _row):
        return self


class _FakeInsertTable(_FakeTable):
    def execute(self):
        if getattr(self, "_pending", None) is not None:
            self._store.setdefault(self._name, []).append(self._pending)
            self._pending = None
            return MagicMock(data=[])
        return super().execute()


class _FakeClient:
    def __init__(self, store):
        self._store = store

    def table(self, name):
        return _FakeInsertTable(self._store, name)


def _req():
    r = MagicMock()
    r.url.path = "/api/v1/world-id/verify"
    return r


def _make_request(executor_id, nullifier):
    from api.routers.worldid import VerifyWorldIdRequest

    return VerifyWorldIdRequest(
        nullifier_hash=nullifier,
        verification_level="orb",
        executor_id=executor_id,
        responses=[{"proof": "valid"}],
    )


async def _verify(
    monkeypatch,
    *,
    worker_auth,
    body_executor,
    body_nullifier,
    store,
    api_nullifier=REAL_NULL,
    require_auth=True,
):
    """Call the handler with the local auth flag patched in-place (NO module
    reload — that corrupts module identity for the rest of the suite)."""
    import api.routers.worldid as wid

    proof_result = VerificationResult(
        success=True, nullifier_hash=api_nullifier, verification_level="orb"
    )
    fake_client = _FakeClient(store)
    with (
        patch.object(wid, "_WORLDID_REQUIRE_AUTH", require_auth),
        patch.object(wid.db, "get_client", return_value=fake_client),
        patch(
            "integrations.worldid.client.verify_world_id_proof",
            new=AsyncMock(return_value=proof_result),
        ),
    ):
        return await wid.verify_world_id(
            raw_request=_req(),
            request=_make_request(body_executor, body_nullifier),
            worker_auth=worker_auth,
        )


@pytest.mark.asyncio
async def test_verify_rejects_unauthenticated_even_when_global_flag_off(monkeypatch):
    """No worker_auth → 401; proof verification is NOT reached."""
    import api.routers.worldid as wid

    proof = AsyncMock()
    with (
        patch.object(wid, "_WORLDID_REQUIRE_AUTH", True),
        patch.object(wid.db, "get_client", return_value=_FakeClient({})),
        patch("integrations.worldid.client.verify_world_id_proof", new=proof),
    ):
        with pytest.raises(HTTPException) as exc:
            await wid.verify_world_id(
                raw_request=_req(),
                request=_make_request(EXEC_A, "0xfake"),
                worker_auth=None,
            )
    assert exc.value.status_code == 401
    proof.assert_not_called()


@pytest.mark.asyncio
async def test_sybil_replay_with_fresh_fake_nullifier_is_blocked(monkeypatch):
    """Two executors replay the SAME proof (same API nullifier) with DIFFERENT
    fake body nullifiers. Request 2 must be 409 because the uniqueness check now
    runs against the API nullifier (REAL_NULL), already stored by request 1."""
    store = {}

    # Request 1 — executor A, fake nullifier 0xFAKE1.
    wa_a = WorkerAuth(executor_id=EXEC_A, auth_method="jwt")
    resp1 = await _verify(
        monkeypatch,
        worker_auth=wa_a,
        body_executor=EXEC_A,
        body_nullifier="0xFAKE1",
        store=store,
    )
    assert resp1.verified is True
    stored = store["world_id_verifications"][0]
    assert stored["nullifier_hash"] == REAL_NULL  # API value, NOT 0xFAKE1
    assert stored["executor_id"] == EXEC_A

    # Request 2 — executor B, different fake nullifier 0xFAKE2, same proof.
    wa_b = WorkerAuth(executor_id=EXEC_B, auth_method="jwt")
    with pytest.raises(HTTPException) as exc:
        await _verify(
            monkeypatch,
            worker_auth=wa_b,
            body_executor=EXEC_B,
            body_nullifier="0xFAKE2",
            store=store,
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_verify_uses_jwt_executor_not_body(monkeypatch):
    """Body executor=ATTACKER, JWT executor=A → row keyed on A."""
    store = {}
    wa = WorkerAuth(executor_id=EXEC_A, auth_method="jwt")
    await _verify(
        monkeypatch,
        worker_auth=wa,
        body_executor=EXEC_B,  # mismatched body
        body_nullifier="0xCLIENT",
        store=store,
    )
    stored = store["world_id_verifications"][0]
    assert stored["executor_id"] == EXEC_A
    assert stored["nullifier_hash"] == REAL_NULL


@pytest.mark.asyncio
async def test_verify_502_when_api_returns_no_nullifier(monkeypatch):
    store = {}
    wa = WorkerAuth(executor_id=EXEC_A, auth_method="jwt")
    with pytest.raises(HTTPException) as exc:
        await _verify(
            monkeypatch,
            worker_auth=wa,
            body_executor=EXEC_A,
            body_nullifier="0xclient",
            store=store,
            api_nullifier=None,
        )
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_same_executor_reverify_is_idempotent_success(monkeypatch):
    store = {}
    wa = WorkerAuth(executor_id=EXEC_A, auth_method="jwt")
    r1 = await _verify(
        monkeypatch,
        worker_auth=wa,
        body_executor=EXEC_A,
        body_nullifier="0xREAL",
        store=store,
    )
    assert r1.verified is True
    # Second call for the same executor short-circuits to "Already verified".
    r2 = await _verify(
        monkeypatch,
        worker_auth=wa,
        body_executor=EXEC_A,
        body_nullifier="0xREAL",
        store=store,
    )
    assert r2.verified is True


@pytest.mark.asyncio
async def test_verify_body_fallback_when_flag_explicitly_off(monkeypatch):
    """EM_WORLDID_REQUIRE_AUTH=false + no JWT → body executor used (rollback path),
    but the nullifier still comes from the API (the nullifier fix stays active)."""
    store = {}
    resp = await _verify(
        monkeypatch,
        worker_auth=None,
        body_executor=EXEC_A,
        body_nullifier="0xBODYFAKE",
        store=store,
        require_auth=False,
    )
    assert resp.verified is True
    stored = store["world_id_verifications"][0]
    assert stored["executor_id"] == EXEC_A  # body value used in rollback mode
    assert stored["nullifier_hash"] == REAL_NULL  # but nullifier from API
