"""Integration tests for api/routers/veryai.py.

Uses FastAPI TestClient + httpx mocks for the OAuth2 calls. Mocks the
Supabase client via supabase_client.get_client. Master switch is forced ON
for the duration of these tests so the router is registered.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest

# Ensure mcp_server root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Master switch + secrets must be set BEFORE importing the router module
os.environ.setdefault("EM_VERYAI_ENABLED", "true")
os.environ.setdefault("VERYAI_CLIENT_ID", "em-test-client")
os.environ.setdefault("VERYAI_CLIENT_SECRET", "em-test-secret")
os.environ.setdefault("VERYAI_REDIRECT_URI", "https://em.test/api/v1/very-id/callback")
os.environ.setdefault("VERYAI_STATE_SECRET", "em-test-state-secret")
os.environ.setdefault("EM_DASHBOARD_URL", "https://test.execution.market")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.routers.veryai import router as veryai_router  # noqa: E402
from integrations.veryai import client as veryai_client  # noqa: E402

pytestmark = pytest.mark.core


# ---------------------------------------------------------------------------
# Test app
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(veryai_router)
    return app


# ---------------------------------------------------------------------------
# Supabase stub
# ---------------------------------------------------------------------------


class _Result:
    def __init__(self, data: list[dict]):
        self.data = data


class _QB:
    """Chainable Postgrest stub. Records inserts/updates for assertions."""

    def __init__(self, parent: "_FakeDB", table_name: str):
        self._parent = parent
        self._table_name = table_name
        self._select_filters: list[tuple[str, Any]] = []

    def select(self, *_args: Any, **_kwargs: Any) -> "_QB":
        return self

    def eq(self, col: str, val: Any) -> "_QB":
        self._select_filters.append((col, val))
        return self

    def limit(self, *_args: Any, **_kwargs: Any) -> "_QB":
        return self

    def insert(self, row: dict) -> "_QB":
        self._parent.inserts.append({"table": self._table_name, "row": row})
        if self._table_name in self._parent.insert_errors:
            raise self._parent.insert_errors[self._table_name]
        return self

    def update(self, row: dict) -> "_QB":
        self._parent.updates.append({"table": self._table_name, "row": row})
        return self

    def execute(self) -> _Result:
        if self._table_name == "veryai_verifications":
            sub = next((v for c, v in self._select_filters if c == "veryai_sub"), None)
            if sub is not None:
                rows = self._parent.veryai_rows_by_sub.get(sub, [])
                return _Result(rows)
        if self._table_name == "executors":
            eid = next((v for c, v in self._select_filters if c == "id"), None)
            if eid is not None and eid in self._parent.executor_rows:
                return _Result([self._parent.executor_rows[eid]])
        return _Result([])


class _FakeDB:
    def __init__(self) -> None:
        self.veryai_rows_by_sub: dict[str, list[dict]] = {}
        self.executor_rows: dict[str, dict] = {}
        self.inserts: list[dict] = []
        self.updates: list[dict] = []
        self.insert_errors: dict[str, Exception] = {}

    def table(self, name: str) -> _QB:
        return _QB(self, name)


# ---------------------------------------------------------------------------
# httpx stub for OAuth calls
# ---------------------------------------------------------------------------


class _FakeAsyncClient:
    def __init__(self, responses: list[httpx.Response]):
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        self.calls.append({"method": "POST", "url": url, **kwargs})
        return self._responses.pop(0)

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        self.calls.append({"method": "GET", "url": url, **kwargs})
        return self._responses.pop(0)


def _mk_response(status_code: int, body: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=body or {},
        request=httpx.Request("POST", "https://api.very.org/test"),
    )


@pytest.fixture
def patch_paths(monkeypatch: pytest.MonkeyPatch):
    """Force the OAuth path resolver to known sandbox values."""

    async def _paths() -> dict:
        return {
            "base": "https://api.very.org",
            "authorize": "/oauth2/authorize",
            "token": "/oauth2/token",
            "userinfo": "/userinfo",
        }

    monkeypatch.setattr(veryai_client, "_resolved_paths", _paths)
    monkeypatch.setattr(veryai_client, "VERYAI_CLIENT_ID", "em-test-client")
    monkeypatch.setattr(veryai_client, "VERYAI_CLIENT_SECRET", "em-test-secret")
    monkeypatch.setattr(
        veryai_client,
        "VERYAI_REDIRECT_URI",
        "https://em.test/api/v1/very-id/callback",
    )
    monkeypatch.setattr(veryai_client, "VERYAI_STATE_SECRET", "em-test-state-secret")


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> _FakeDB:
    fake = _FakeDB()
    import supabase_client as sb
    from api.routers import veryai as router_mod

    monkeypatch.setattr(sb, "get_client", lambda: fake)
    monkeypatch.setattr(router_mod.db, "get_client", lambda: fake)
    return fake


# ---------------------------------------------------------------------------
# /oauth-url
# ---------------------------------------------------------------------------


class TestOAuthUrl:
    def test_returns_authorize_url_and_state(self, patch_paths: None) -> None:
        client = TestClient(_make_app())
        resp = client.get("/api/v1/very-id/oauth-url?executor_id=exec-1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["url"].startswith("https://api.very.org/oauth2/authorize?")
        assert "state=" in body["url"]
        # Round-trip the state — it should decode to executor_id="exec-1"
        decoded = veryai_client.verify_state_token(body["state"])
        assert decoded["executor_id"] == "exec-1"

    def test_503_when_client_id_missing(
        self,
        patch_paths: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(veryai_client, "VERYAI_CLIENT_ID", "")
        client = TestClient(_make_app())
        resp = client.get("/api/v1/very-id/oauth-url?executor_id=exec-1")
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# /callback
# ---------------------------------------------------------------------------


def _good_state(executor_id: str = "exec-1") -> tuple[str, str]:
    """Return (state_token, code_verifier) ready for callback."""
    verifier = "v" * 96
    state = veryai_client.create_state_token(executor_id, verifier)
    return state, verifier


class TestCallback:
    def test_invalid_state_redirects_with_error(self, patch_paths: None) -> None:
        client = TestClient(_make_app())
        resp = client.get(
            "/api/v1/very-id/callback?code=abc&state=not-a-jwt",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "veryai=error" in resp.headers["location"]
        assert "invalid_state" in resp.headers["location"]

    def test_oauth_idp_error_param_redirects_with_error(
        self, patch_paths: None
    ) -> None:
        client = TestClient(_make_app())
        state, _v = _good_state()
        resp = client.get(
            f"/api/v1/very-id/callback?code=&state={state}&error=access_denied",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "veryai=error" in resp.headers["location"]
        assert "access_denied" in resp.headers["location"]

    def test_token_exchange_failure_redirects_error(
        self,
        patch_paths: None,
        fake_db: _FakeDB,
    ) -> None:
        state, _v = _good_state()
        fake_http = _FakeAsyncClient([_mk_response(401, {"error": "invalid_client"})])
        with patch.object(httpx, "AsyncClient", return_value=fake_http):
            client = TestClient(_make_app())
            resp = client.get(
                f"/api/v1/very-id/callback?code=abc&state={state}",
                follow_redirects=False,
            )
        assert resp.status_code == 302
        assert "token_exchange_failed" in resp.headers["location"]

    def test_unverified_user_redirects_incomplete(
        self,
        patch_paths: None,
        fake_db: _FakeDB,
    ) -> None:
        state, _v = _good_state()
        fake_http = _FakeAsyncClient(
            [
                _mk_response(
                    200,
                    {
                        "access_token": "AT",
                        "id_token": "ID",
                        "expires_in": 3600,
                        "token_type": "Bearer",
                    },
                ),
                _mk_response(
                    200, {"sub": "veryai|abc", "verification_level": "unverified"}
                ),
            ]
        )
        with patch.object(httpx, "AsyncClient", return_value=fake_http):
            client = TestClient(_make_app())
            resp = client.get(
                f"/api/v1/very-id/callback?code=abc&state={state}",
                follow_redirects=False,
            )
        assert resp.status_code == 302
        assert "veryai=incomplete" in resp.headers["location"]
        assert len(fake_db.inserts) == 0
        assert len(fake_db.updates) == 0

    def test_success_inserts_row_and_updates_executor(
        self,
        patch_paths: None,
        fake_db: _FakeDB,
    ) -> None:
        state, _v = _good_state(executor_id="exec-1")
        fake_http = _FakeAsyncClient(
            [
                _mk_response(
                    200,
                    {
                        "access_token": "AT",
                        "id_token": "ID-TOKEN",
                        "expires_in": 3600,
                        "token_type": "Bearer",
                    },
                ),
                _mk_response(
                    200, {"sub": "veryai|abc", "verification_level": "palm_dual"}
                ),
            ]
        )
        with patch.object(httpx, "AsyncClient", return_value=fake_http):
            client = TestClient(_make_app())
            resp = client.get(
                f"/api/v1/very-id/callback?code=abc&state={state}",
                follow_redirects=False,
            )
        assert resp.status_code == 302
        assert "veryai=success" in resp.headers["location"]

        # Inserted into veryai_verifications
        v_inserts = [i for i in fake_db.inserts if i["table"] == "veryai_verifications"]
        assert len(v_inserts) == 1
        row = v_inserts[0]["row"]
        assert row["executor_id"] == "exec-1"
        assert row["veryai_sub"] == "veryai|abc"
        assert row["verification_level"] == "palm_dual"
        assert row["oidc_id_token"] == "ID-TOKEN"

        # Updated executor row
        e_updates = [u for u in fake_db.updates if u["table"] == "executors"]
        assert len(e_updates) == 1
        assert e_updates[0]["row"]["veryai_verified"] is True
        assert e_updates[0]["row"]["veryai_level"] == "palm_dual"
        assert e_updates[0]["row"]["veryai_sub"] == "veryai|abc"

    def test_sub_already_used_by_other_executor_blocks(
        self,
        patch_paths: None,
        fake_db: _FakeDB,
    ) -> None:
        # Pre-existing row: sub bound to a different executor
        fake_db.veryai_rows_by_sub["veryai|abc"] = [
            {"id": "v-prior", "executor_id": "exec-OTHER"}
        ]
        state, _v = _good_state(executor_id="exec-NEW")
        fake_http = _FakeAsyncClient(
            [
                _mk_response(
                    200,
                    {
                        "access_token": "AT",
                        "id_token": "ID",
                        "expires_in": 3600,
                        "token_type": "Bearer",
                    },
                ),
                _mk_response(
                    200, {"sub": "veryai|abc", "verification_level": "palm_single"}
                ),
            ]
        )
        with patch.object(httpx, "AsyncClient", return_value=fake_http):
            client = TestClient(_make_app())
            resp = client.get(
                f"/api/v1/very-id/callback?code=abc&state={state}",
                follow_redirects=False,
            )
        assert resp.status_code == 302
        assert "sub_already_used" in resp.headers["location"]
        assert len(fake_db.inserts) == 0

    def test_idempotent_reverify_same_executor(
        self,
        patch_paths: None,
        fake_db: _FakeDB,
    ) -> None:
        # Pre-existing row: sub already bound to the SAME executor
        fake_db.veryai_rows_by_sub["veryai|abc"] = [
            {"id": "v-prior", "executor_id": "exec-1"}
        ]
        state, _v = _good_state(executor_id="exec-1")
        fake_http = _FakeAsyncClient(
            [
                _mk_response(
                    200,
                    {
                        "access_token": "AT",
                        "id_token": "ID",
                        "expires_in": 3600,
                        "token_type": "Bearer",
                    },
                ),
                _mk_response(
                    200, {"sub": "veryai|abc", "verification_level": "palm_single"}
                ),
            ]
        )
        with patch.object(httpx, "AsyncClient", return_value=fake_http):
            client = TestClient(_make_app())
            resp = client.get(
                f"/api/v1/very-id/callback?code=abc&state={state}",
                follow_redirects=False,
            )
        assert resp.status_code == 302
        assert "veryai=success" in resp.headers["location"]
        assert "already_verified" in resp.headers["location"]
        # No new insert/update — idempotent path
        assert len(fake_db.inserts) == 0


# ---------------------------------------------------------------------------
# /verify
# ---------------------------------------------------------------------------


def test_verify_returns_501() -> None:
    client = TestClient(_make_app())
    resp = client.post("/api/v1/very-id/verify")
    assert resp.status_code == 501


# ---------------------------------------------------------------------------
# /status
# ---------------------------------------------------------------------------


class TestStatus:
    def test_status_verified(self, fake_db: _FakeDB) -> None:
        fake_db.executor_rows["exec-1"] = {
            "veryai_verified": True,
            "veryai_level": "palm_dual",
            "veryai_verified_at": "2026-04-30T12:00:00Z",
        }
        client = TestClient(_make_app())
        resp = client.get("/api/v1/very-id/status?executor_id=exec-1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["verified"] is True
        assert body["level"] == "palm_dual"
        assert body["verified_at"] == "2026-04-30T12:00:00Z"

    def test_status_unverified(self, fake_db: _FakeDB) -> None:
        fake_db.executor_rows["exec-2"] = {"veryai_verified": False}
        client = TestClient(_make_app())
        resp = client.get("/api/v1/very-id/status?executor_id=exec-2")
        assert resp.status_code == 200
        body = resp.json()
        assert body["verified"] is False
        assert body["level"] is None

    def test_status_unknown_executor(self, fake_db: _FakeDB) -> None:
        client = TestClient(_make_app())
        resp = client.get("/api/v1/very-id/status?executor_id=nobody")
        assert resp.status_code == 200
        assert resp.json()["verified"] is False
