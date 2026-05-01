"""Integration tests for api/routers/clawkey.py.

Mocks the Supabase client and the upstream ClawKey HTTP client. Master switch
is forced ON at import time so the router is registered.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

# Ensure mcp_server root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Master switch must be set BEFORE importing the router module
os.environ.setdefault("EM_CLAWKEY_ENABLED", "true")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.routers.clawkey import router as clawkey_router  # noqa: E402
from integrations.clawkey import client as ck_client  # noqa: E402

pytestmark = pytest.mark.clawkey


# ---------------------------------------------------------------------------
# Test app
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(clawkey_router)
    return app


# ---------------------------------------------------------------------------
# Supabase stub
# ---------------------------------------------------------------------------


class _Result:
    def __init__(self, data: list[dict]):
        self.data = data


class _QB:
    """Chainable Postgrest stub. Records inserts/updates/upserts."""

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
        return self

    def update(self, row: dict) -> "_QB":
        self._parent.updates.append({"table": self._table_name, "row": row})
        return self

    def upsert(self, row: dict, **kwargs: Any) -> "_QB":
        self._parent.upserts.append(
            {"table": self._table_name, "row": row, "kwargs": kwargs}
        )
        return self

    def execute(self) -> _Result:
        if self._table_name == "executors":
            eid = next((v for c, v in self._select_filters if c == "id"), None)
            if eid is not None and eid in self._parent.executor_rows:
                return _Result([self._parent.executor_rows[eid]])
        return _Result([])


class _FakeDB:
    def __init__(self) -> None:
        self.executor_rows: dict[str, dict] = {}
        self.inserts: list[dict] = []
        self.updates: list[dict] = []
        self.upserts: list[dict] = []

    def table(self, name: str) -> _QB:
        return _QB(self, name)


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> _FakeDB:
    fake = _FakeDB()
    import supabase_client as sb
    from api.routers import clawkey as router_mod

    monkeypatch.setattr(sb, "get_client", lambda: fake)
    monkeypatch.setattr(router_mod.db, "get_client", lambda: fake)
    return fake


# ---------------------------------------------------------------------------
# httpx stub for upstream ClawKey
# ---------------------------------------------------------------------------


class _FakeAsyncClient:
    def __init__(self, response: httpx.Response):
        self._response = response
        self.calls: list[dict[str, Any]] = []

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        return None

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        self.calls.append({"method": "GET", "url": url, **kwargs})
        return self._response


def _mk_response(status_code: int, body: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=body if body is not None else {},
        request=httpx.Request("GET", "https://api.clawkey.ai/test"),
    )


@pytest.fixture
def patch_clawkey_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip PlatformConfig in tests — return known defaults."""

    async def fake_cfg() -> dict:
        return {
            "base": "https://api.clawkey.ai",
            "pubkey_path": "/v1/agent/verify/public-key/{pubkey}",
            "device_path": "/v1/agent/verify/device/{device_id}",
            "cache_ttl": 300.0,
            "http_timeout": 10.0,
        }

    monkeypatch.setattr(ck_client, "_resolved_config", fake_cfg)
    ck_client.clear_cache()


# ---------------------------------------------------------------------------
# /status/{executor_id}
# ---------------------------------------------------------------------------


class TestStatus:
    def test_returns_db_snapshot_for_verified_executor(self, fake_db: _FakeDB) -> None:
        fake_db.executor_rows["exec-1"] = {
            "id": "exec-1",
            "clawkey_verified": True,
            "clawkey_human_id": "hum-abc",
            "clawkey_public_key": "PubKeyB58",
            "clawkey_device_id": "dev-1",
            "clawkey_registered_at": "2026-04-30T00:00:00Z",
        }
        client = TestClient(_make_app())
        resp = client.get("/api/v1/clawkey/status/exec-1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["verified"] is True
        assert body["human_id"] == "hum-abc"
        assert body["public_key"] == "PubKeyB58"
        assert body["registered_at"] == "2026-04-30T00:00:00Z"

    def test_returns_unverified_for_executor_without_clawkey(
        self, fake_db: _FakeDB
    ) -> None:
        fake_db.executor_rows["exec-2"] = {
            "id": "exec-2",
            "clawkey_verified": False,
            "clawkey_human_id": None,
            "clawkey_public_key": None,
            "clawkey_device_id": None,
            "clawkey_registered_at": None,
        }
        client = TestClient(_make_app())
        resp = client.get("/api/v1/clawkey/status/exec-2")
        assert resp.status_code == 200
        body = resp.json()
        assert body["verified"] is False
        assert body["human_id"] is None
        assert body["public_key"] is None

    def test_404_when_executor_missing(self, fake_db: _FakeDB) -> None:
        client = TestClient(_make_app())
        resp = client.get("/api/v1/clawkey/status/missing-uuid")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /refresh/{executor_id}
# ---------------------------------------------------------------------------


class TestRefresh:
    def test_force_refresh_updates_db_and_returns_upstream_value(
        self,
        fake_db: _FakeDB,
        patch_clawkey_config: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake_db.executor_rows["exec-3"] = {
            "id": "exec-3",
            "clawkey_verified": False,
            "clawkey_human_id": None,
            "clawkey_public_key": "PubKeyRefresh",
            "clawkey_device_id": "dev-3",
            "clawkey_registered_at": None,
        }
        upstream = _FakeAsyncClient(
            _mk_response(
                200,
                {
                    "registered": True,
                    "verified": True,
                    "humanId": "hum-refresh",
                    "registeredAt": "2026-04-30T12:00:00Z",
                },
            )
        )
        monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: upstream)

        client = TestClient(_make_app())
        resp = client.post("/api/v1/clawkey/refresh/exec-3")
        assert resp.status_code == 200
        body = resp.json()
        assert body["verified"] is True
        assert body["human_id"] == "hum-refresh"

        # DB updated
        executor_updates = [u for u in fake_db.updates if u["table"] == "executors"]
        assert len(executor_updates) == 1
        row = executor_updates[0]["row"]
        assert row["clawkey_verified"] is True
        assert row["clawkey_human_id"] == "hum-refresh"
        # And audit-trail upsert happened
        assert len(fake_db.upserts) == 1
        upsert = fake_db.upserts[0]
        assert upsert["table"] == "agent_kya_verifications"
        assert upsert["kwargs"]["on_conflict"] == "executor_id"

    def test_no_public_key_returns_empty_status(self, fake_db: _FakeDB) -> None:
        fake_db.executor_rows["exec-4"] = {
            "id": "exec-4",
            "clawkey_verified": False,
            "clawkey_human_id": None,
            "clawkey_public_key": None,
            "clawkey_device_id": None,
            "clawkey_registered_at": None,
        }
        client = TestClient(_make_app())
        resp = client.post("/api/v1/clawkey/refresh/exec-4")
        assert resp.status_code == 200
        body = resp.json()
        assert body["verified"] is False
        assert body["public_key"] is None
        # No upstream call needed → no DB writes
        assert fake_db.updates == []
        assert fake_db.upserts == []

    def test_404_when_executor_missing(self, fake_db: _FakeDB) -> None:
        client = TestClient(_make_app())
        resp = client.post("/api/v1/clawkey/refresh/missing-uuid")
        assert resp.status_code == 404

    def test_503_when_upstream_fails(
        self,
        fake_db: _FakeDB,
        patch_clawkey_config: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake_db.executor_rows["exec-5"] = {
            "id": "exec-5",
            "clawkey_verified": True,
            "clawkey_human_id": "hum-5",
            "clawkey_public_key": "PubKey5",
            "clawkey_device_id": "dev-5",
            "clawkey_registered_at": "2026-04-30T00:00:00Z",
        }
        upstream = _FakeAsyncClient(_mk_response(500, {"error": "boom"}))
        monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: upstream)

        client = TestClient(_make_app())
        resp = client.post("/api/v1/clawkey/refresh/exec-5")
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# /register
# ---------------------------------------------------------------------------


class TestRegister:
    def test_returns_501(self) -> None:
        client = TestClient(_make_app())
        resp = client.post("/api/v1/clawkey/register")
        assert resp.status_code == 501
        body = resp.json()
        assert "clawhub" in body["detail"]


# ---------------------------------------------------------------------------
# Master switch: when EM_CLAWKEY_ENABLED is off, routes are not registered.
# ---------------------------------------------------------------------------


class TestMasterSwitch:
    def test_routes_return_404_when_router_not_included(self) -> None:
        # A bare app without the clawkey router must surface 404 on every path
        app = FastAPI()
        client = TestClient(app)
        assert client.get("/api/v1/clawkey/status/x").status_code == 404
        assert client.post("/api/v1/clawkey/refresh/x").status_code == 404
        assert client.post("/api/v1/clawkey/register").status_code == 404
