"""
Unit tests for IdempotencyMiddleware (Task 4.5).

Goal of this suite: verify the middleware's dedup contract *without*
standing up Supabase. We substitute the ``_lookup_idempotency`` /
``_store_idempotency`` helpers with in-memory fakes via monkeypatch and
drive the middleware through a real Starlette app + TestClient.

What we're pinning down:

  - Requests outside the allow-list (GET, non-matching path) are
    forwarded untouched.
  - POSTs to allow-listed paths WITHOUT ``Idempotency-Key`` forward
    untouched and do NOT touch the cache.
  - A well-formed first request runs the handler, populates the cache,
    and returns the handler's response.
  - A replay with the same key + same body returns the CACHED response
    (not the handler's new response). The handler must not be invoked
    twice.
  - A replay with the same key + DIFFERENT body returns HTTP 409
    ``idempotency_key_conflict``.
  - Non-2xx responses are NOT cached (transient failures shouldn't be
    memoised — the client should be able to retry with the same key and
    eventually see a real outcome).
  - Invalid keys (empty, oversize) return HTTP 400 without ever hitting
    Supabase or the handler.

The tests avoid reaching into Supabase entirely: we swap the two async
helpers the middleware calls (``_lookup_idempotency`` and
``_store_idempotency``) for in-memory stand-ins. That keeps the suite
hermetic and fast.
"""

from __future__ import annotations

import hashlib
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

from api import middleware as api_middleware


# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_cache(monkeypatch: pytest.MonkeyPatch) -> dict[tuple[str, str], dict]:
    """In-memory replacement for the Supabase-backed cache.

    Keyed by ``(idem_key, auth_scope_hash)`` to match the production
    table's primary key. Returning the dict lets individual tests seed
    or inspect state.
    """
    store: dict[tuple[str, str], dict] = {}

    async def fake_lookup(key: str, auth_scope_hash: str):
        return store.get((key, auth_scope_hash))

    async def fake_store(
        *,
        key,
        auth_scope_hash,
        request_hash,
        response_status,
        response_body,
        method,
        path,
        agent_id=None,
    ):
        store[(key, auth_scope_hash)] = {
            "request_hash": request_hash,
            "response_status": response_status,
            "response_body": response_body,
            "method": method,
            "path": path,
            "agent_id": agent_id,
        }

    monkeypatch.setattr(api_middleware, "_lookup_idempotency", fake_lookup)
    monkeypatch.setattr(api_middleware, "_store_idempotency", fake_store)
    return store


@pytest.fixture
def app_and_counts(fake_cache) -> tuple[FastAPI, dict[str, int]]:
    """Build a minimal app that exposes:

      - POST /api/v1/submissions/{id}/approve → 200 {"ok": True, "id": id}
      - POST /api/v1/tasks                    → 201 {"id": "t-1"}
      - POST /api/v1/submissions/{id}/fail    → 500 {"error": "boom"}
      - GET  /api/v1/tasks                    → 200 (control: never deduped)

    The handler counter lets tests assert that a cache hit short-circuits
    before the handler runs.
    """
    app = FastAPI()
    app.add_middleware(api_middleware.IdempotencyMiddleware)
    counts = {"approve": 0, "create": 0, "fail": 0, "get": 0}

    @app.post("/api/v1/submissions/{sub_id}/approve")
    async def _approve(sub_id: str) -> dict[str, Any]:
        counts["approve"] += 1
        return {"ok": True, "id": sub_id}

    @app.post("/api/v1/tasks")
    async def _create() -> JSONResponse:
        counts["create"] += 1
        return JSONResponse(status_code=201, content={"id": "t-1"})

    @app.post("/api/v1/submissions/{sub_id}/fail")
    async def _fail(sub_id: str) -> JSONResponse:
        counts["fail"] += 1
        return JSONResponse(status_code=500, content={"error": "boom"})

    @app.get("/api/v1/tasks")
    async def _list() -> dict[str, Any]:
        counts["get"] += 1
        return {"tasks": []}

    return app, counts


def _auth_scope(header: str) -> str:
    return hashlib.sha256(header.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Forward-path (middleware is a no-op)
# ---------------------------------------------------------------------------


class TestPassthrough:
    def test_get_request_passes_through_unconditionally(
        self, app_and_counts, fake_cache
    ):
        app, counts = app_and_counts
        with TestClient(app) as client:
            r = client.get("/api/v1/tasks", headers={"Idempotency-Key": "k-1"})
        assert r.status_code == 200
        assert counts["get"] == 1
        # Even though we sent a header, GET must not populate the cache.
        assert fake_cache == {}

    def test_post_outside_allowlist_passes_through(self, fake_cache):
        # A fresh app that has a POST route NOT on the allow-list.
        app = FastAPI()
        app.add_middleware(api_middleware.IdempotencyMiddleware)
        calls = {"n": 0}

        @app.post("/api/v1/other/thing")
        async def _handler():
            calls["n"] += 1
            return {"ok": True}

        with TestClient(app) as client:
            r = client.post(
                "/api/v1/other/thing",
                headers={"Idempotency-Key": "k-1", "Authorization": "Bearer t"},
                json={"a": 1},
            )
        assert r.status_code == 200
        assert calls["n"] == 1
        assert fake_cache == {}

    def test_post_without_key_header_passes_through(self, app_and_counts, fake_cache):
        app, counts = app_and_counts
        with TestClient(app) as client:
            r = client.post(
                "/api/v1/submissions/abc/approve",
                headers={"Authorization": "Bearer t"},
                json={},
            )
        assert r.status_code == 200
        assert counts["approve"] == 1
        assert fake_cache == {}

    def test_post_without_auth_header_passes_through(self, app_and_counts, fake_cache):
        # No Authorization → middleware cannot scope the cache, so it
        # must forward rather than silently share cache across clients.
        app, counts = app_and_counts
        with TestClient(app) as client:
            r = client.post(
                "/api/v1/submissions/abc/approve",
                headers={"Idempotency-Key": "k-1"},
                json={},
            )
        assert r.status_code == 200
        assert counts["approve"] == 1
        assert fake_cache == {}


# ---------------------------------------------------------------------------
# Cache miss → store
# ---------------------------------------------------------------------------


class TestCacheMiss:
    def test_first_request_runs_handler_and_populates_cache(
        self, app_and_counts, fake_cache
    ):
        app, counts = app_and_counts
        auth = "Bearer abc"
        with TestClient(app) as client:
            r = client.post(
                "/api/v1/submissions/sub-1/approve",
                headers={"Idempotency-Key": "k-1", "Authorization": auth},
                json={"note": "ok"},
            )
        assert r.status_code == 200
        assert r.json() == {"ok": True, "id": "sub-1"}
        assert counts["approve"] == 1
        assert ("k-1", _auth_scope(auth)) in fake_cache

    def test_201_responses_are_cached(self, app_and_counts, fake_cache):
        app, counts = app_and_counts
        auth = "Bearer abc"
        with TestClient(app) as client:
            r = client.post(
                "/api/v1/tasks",
                headers={"Idempotency-Key": "k-tasks", "Authorization": auth},
                json={"title": "x"},
            )
        assert r.status_code == 201
        assert ("k-tasks", _auth_scope(auth)) in fake_cache

    def test_5xx_responses_are_not_cached(self, app_and_counts, fake_cache):
        app, counts = app_and_counts
        auth = "Bearer abc"
        with TestClient(app) as client:
            r = client.post(
                "/api/v1/submissions/sub-9/fail",
                headers={"Idempotency-Key": "k-fail", "Authorization": auth},
                json={},
            )
        assert r.status_code == 500
        assert counts["fail"] == 1
        # Transient failures must not be memoised.
        assert fake_cache == {}


# ---------------------------------------------------------------------------
# Cache hit → replay
# ---------------------------------------------------------------------------


class TestCacheHit:
    def test_same_key_same_body_replays_cached_response(
        self, app_and_counts, fake_cache
    ):
        app, counts = app_and_counts
        auth = "Bearer abc"
        hdr = {"Idempotency-Key": "k-1", "Authorization": auth}
        with TestClient(app) as client:
            r1 = client.post(
                "/api/v1/submissions/sub-1/approve", headers=hdr, json={"a": 1}
            )
            r2 = client.post(
                "/api/v1/submissions/sub-1/approve", headers=hdr, json={"a": 1}
            )
        assert r1.status_code == r2.status_code == 200
        # Critical: handler ran exactly once despite two client requests.
        assert counts["approve"] == 1
        assert r1.json() == r2.json()
        assert r2.headers.get("idempotency-replay") == "true"

    def test_same_key_different_body_returns_409_conflict(
        self, app_and_counts, fake_cache
    ):
        app, counts = app_and_counts
        auth = "Bearer abc"
        hdr = {"Idempotency-Key": "k-1", "Authorization": auth}
        with TestClient(app) as client:
            r1 = client.post(
                "/api/v1/submissions/sub-1/approve", headers=hdr, json={"a": 1}
            )
            r2 = client.post(
                "/api/v1/submissions/sub-1/approve", headers=hdr, json={"a": 2}
            )
        assert r1.status_code == 200
        assert r2.status_code == 409
        body = r2.json()
        assert body["error"] == "idempotency_key_conflict"
        # Handler ran ONCE; the second request was rejected before exec.
        assert counts["approve"] == 1

    def test_different_auth_tokens_do_not_share_cache(self, app_and_counts, fake_cache):
        # Two clients send the same Idempotency-Key but different bearer
        # tokens. They must not collide — each gets its own handler call.
        app, counts = app_and_counts
        with TestClient(app) as client:
            client.post(
                "/api/v1/submissions/sub-1/approve",
                headers={"Idempotency-Key": "shared", "Authorization": "Bearer A"},
                json={},
            )
            client.post(
                "/api/v1/submissions/sub-1/approve",
                headers={"Idempotency-Key": "shared", "Authorization": "Bearer B"},
                json={},
            )
        assert counts["approve"] == 2
        assert len(fake_cache) == 2


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestHeaderValidation:
    def test_empty_key_returns_400(self, app_and_counts, fake_cache):
        app, counts = app_and_counts
        with TestClient(app) as client:
            r = client.post(
                "/api/v1/submissions/sub-1/approve",
                headers={"Idempotency-Key": "   ", "Authorization": "Bearer t"},
                json={},
            )
        assert r.status_code == 400
        assert r.json()["error"] == "invalid_idempotency_key"
        # Handler must not run when the header itself is malformed.
        assert counts["approve"] == 0

    def test_oversized_key_returns_400(self, app_and_counts, fake_cache):
        app, counts = app_and_counts
        oversized = "a" * (api_middleware.IdempotencyMiddleware._MAX_KEY_LENGTH + 1)
        with TestClient(app) as client:
            r = client.post(
                "/api/v1/submissions/sub-1/approve",
                headers={"Idempotency-Key": oversized, "Authorization": "Bearer t"},
                json={},
            )
        assert r.status_code == 400
        assert counts["approve"] == 0
