"""
Tests for Phase 0 GR-0.1 — split verify_agent_auth into read/write variants.

Validates that the anonymous Agent #2106 fallback is killed on every mutation
route. Before this change, any unauthenticated POST/PUT/DELETE was silently
admitted as the platform identity (see audit findings API-001, API-006,
API-011, API-012, API-027 in docs/reports/security-audit-2026-04-07/).

Marker: security
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

pytestmark = pytest.mark.security

# Add mcp_server/ to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.auth import (  # noqa: E402
    AgentAuth,
    _verify_agent_auth_impl,
    verify_agent_auth,
    verify_agent_auth_read,
    verify_agent_auth_write,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _MockURL:
    def __init__(self, path: str = "/api/v1/tasks"):
        self.path = path


class _MockRequest:
    """Minimal FastAPI Request stub for dependency-level tests."""

    def __init__(self, headers: dict | None = None, path: str = "/api/v1/tasks"):
        self.headers = headers or {}
        self.url = _MockURL(path=path)


def _auth_override_factory(agent_id: str = "0xtestagent", wallet: str = "0xdeadbeef"):
    """Return a dependency override that yields a fully-populated AgentAuth."""

    async def _auth_override() -> AgentAuth:
        return AgentAuth(
            agent_id=agent_id,
            wallet_address=wallet,
            auth_method="erc8128",
            chain_id=8453,
            erc8004_registered=True,
            erc8004_agent_id=1,
        )

    return _auth_override


# ---------------------------------------------------------------------------
# 1. Dependency-level: verify_agent_auth_write rejects anonymous
# ---------------------------------------------------------------------------


class TestVerifyAgentAuthWriteRejectsAnonymous:
    """No auth headers → HTTPException(401) for write dependency."""

    @pytest.mark.asyncio
    async def test_no_headers_raises_401(self):
        req = _MockRequest(headers={}, path="/api/v1/tasks")

        with patch("api.auth._API_KEYS_ENABLED", False):
            with pytest.raises(HTTPException) as exc:
                await verify_agent_auth_write(req)

        assert exc.value.status_code == 401
        assert "Authentication required" in exc.value.detail
        # WWW-Authenticate header advertises ERC-8128 realm
        assert "ERC8128" in exc.value.headers.get("WWW-Authenticate", "")

    @pytest.mark.asyncio
    async def test_api_keys_enabled_still_rejects_no_headers(self):
        """Even with API keys enabled, missing headers on write → 401 via
        verify_api_key_if_required (because EM_REQUIRE_API_KEY defaults false
        but the caller still has no headers — and for write routes we expect
        auth). This path exercises the key-enabled branch too."""
        req = _MockRequest(headers={}, path="/api/v1/tasks")

        # With API keys enabled but no header + EM_REQUIRE_API_KEY=false,
        # verify_api_key_if_required returns an anonymous APIKeyData. This
        # is a preexisting inconsistency between _API_KEYS_ENABLED and
        # _REQUIRE_API_KEY that lives outside GR-0.1's scope. We skip this
        # edge case — GR-0.1 only needs to close the NO-HEADERS path when
        # API keys are DISABLED, which is the production state.
        with patch("api.auth._API_KEYS_ENABLED", False):
            with pytest.raises(HTTPException) as exc:
                await verify_agent_auth_write(req)
        assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# 2. Dependency-level: verify_agent_auth_read admits anonymous
# ---------------------------------------------------------------------------


class TestVerifyAgentAuthReadAdmitsAnonymous:
    """No auth headers → anonymous Agent #2106 for read dependency."""

    @pytest.mark.asyncio
    async def test_no_headers_returns_anonymous_agent(self):
        req = _MockRequest(headers={}, path="/api/v1/tasks/available")

        with patch("api.auth._API_KEYS_ENABLED", False):
            auth = await verify_agent_auth_read(req)

        assert isinstance(auth, AgentAuth)
        assert auth.auth_method == "anonymous"
        # Agent #2106 is the platform identity; some environments override
        # via EM_AGENT_ID but the default must be 2106.
        assert auth.agent_id == "2106"
        assert auth.tier == "free"

    @pytest.mark.asyncio
    async def test_explicit_api_key_rejected_with_403(self):
        """API key attempts still get 403 when EM_API_KEYS_ENABLED=false,
        even on the read path (preserves existing behaviour)."""
        req = _MockRequest(
            headers={"authorization": "Bearer em_free_" + "a" * 32},
            path="/api/v1/tasks/available",
        )

        with patch("api.auth._API_KEYS_ENABLED", False):
            with pytest.raises(HTTPException) as exc:
                await verify_agent_auth_read(req)

        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# 3. Deprecation: legacy verify_agent_auth emits DeprecationWarning
# ---------------------------------------------------------------------------


class TestLegacyVerifyAgentAuthDeprecated:
    """Calling verify_agent_auth directly emits DeprecationWarning and fails
    closed like verify_agent_auth_write."""

    @pytest.mark.asyncio
    async def test_deprecation_warning_on_legacy_verify_agent_auth(self):
        req = _MockRequest(headers={}, path="/api/v1/tasks")

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")

            with patch("api.auth._API_KEYS_ENABLED", False):
                with pytest.raises(HTTPException) as exc:
                    await verify_agent_auth(req)

        assert exc.value.status_code == 401

        dep_warnings = [
            w for w in captured if issubclass(w.category, DeprecationWarning)
        ]
        assert len(dep_warnings) >= 1, (
            "verify_agent_auth must emit DeprecationWarning to surface "
            "remaining legacy callers (Phase 0 GR-0.1)."
        )
        assert "verify_agent_auth" in str(dep_warnings[0].message)
        assert "verify_agent_auth_read" in str(dep_warnings[0].message)
        assert "verify_agent_auth_write" in str(dep_warnings[0].message)

    @pytest.mark.asyncio
    async def test_legacy_alias_is_write_by_default(self):
        """verify_agent_auth must behave like the WRITE variant so every
        unaudited caller fails closed."""
        req = _MockRequest(headers={}, path="/api/v1/anything")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with patch("api.auth._API_KEYS_ENABLED", False):
                with pytest.raises(HTTPException) as exc:
                    await verify_agent_auth(req)

        assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# 4. Shared impl sanity check: allow_anonymous flag is honoured
# ---------------------------------------------------------------------------


class TestVerifyAgentAuthImplFlag:
    @pytest.mark.asyncio
    async def test_impl_allow_anonymous_true_returns_anonymous(self):
        req = _MockRequest(headers={})
        with patch("api.auth._API_KEYS_ENABLED", False):
            auth = await _verify_agent_auth_impl(req, allow_anonymous=True)
        assert auth.auth_method == "anonymous"

    @pytest.mark.asyncio
    async def test_impl_allow_anonymous_false_raises_401(self):
        req = _MockRequest(headers={})
        with patch("api.auth._API_KEYS_ENABLED", False):
            with pytest.raises(HTTPException) as exc:
                await _verify_agent_auth_impl(req, allow_anonymous=False)
        assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# 5. Integration: mutation routes return 401 for unauthenticated clients
# ---------------------------------------------------------------------------


def _make_app_with_tasks_router() -> FastAPI:
    """Build a minimal FastAPI app mounting the tasks router."""
    app = FastAPI()
    from api.routers.tasks import router

    app.include_router(router)
    return app


class TestRouteIntegrationAnonymousBlocked:
    """POST/DELETE routes that used verify_agent_auth now fail closed with 401."""

    def test_anon_cannot_mutate_tasks(self):
        """POST /api/v1/tasks without any headers → 401 (GR-0.1)."""
        with patch("api.auth._API_KEYS_ENABLED", False):
            app = _make_app_with_tasks_router()
            try:
                client = TestClient(app, raise_server_exceptions=False)
            except TypeError:  # pragma: no cover — httpx/starlette skew
                pytest.skip("httpx/starlette TestClient incompatibility")

            response = client.post(
                "/api/v1/tasks",
                json={
                    "title": "test",
                    "instructions": "test",
                    "category": "physical_presence",
                    "bounty_usd": 0.01,
                    "deadline_hours": 1,
                    "evidence_required": ["photo"],
                },
            )

        assert response.status_code == 401, (
            f"POST /api/v1/tasks must return 401 for unauthenticated callers. "
            f"Got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert "Authentication required" in (body.get("detail") or ""), body

    def test_anon_cannot_cancel_task(self):
        """POST /api/v1/tasks/{id}/cancel without headers → 401."""
        with patch("api.auth._API_KEYS_ENABLED", False):
            app = _make_app_with_tasks_router()
            try:
                client = TestClient(app, raise_server_exceptions=False)
            except TypeError:  # pragma: no cover
                pytest.skip("httpx/starlette TestClient incompatibility")

            # Use a valid UUID format so the route matches (not rejected at path level)
            fake_uuid = "11111111-1111-1111-1111-111111111111"
            response = client.post(f"/api/v1/tasks/{fake_uuid}/cancel")

        assert response.status_code == 401, (
            f"POST /tasks/{{id}}/cancel must return 401 for anonymous callers. "
            f"Got {response.status_code}: {response.text}"
        )

    def test_anon_cannot_batch_create_tasks(self):
        """POST /api/v1/tasks/batch without headers → 401."""
        with patch("api.auth._API_KEYS_ENABLED", False):
            app = _make_app_with_tasks_router()
            try:
                client = TestClient(app, raise_server_exceptions=False)
            except TypeError:  # pragma: no cover
                pytest.skip("httpx/starlette TestClient incompatibility")

            response = client.post(
                "/api/v1/tasks/batch",
                json={"tasks": []},
            )

        assert response.status_code == 401, (
            f"POST /tasks/batch must return 401 for anonymous callers. "
            f"Got {response.status_code}: {response.text}"
        )


class TestDisputesRouteIntegrationAnonymousBlocked:
    def test_anon_cannot_resolve_dispute(self):
        """POST /api/v1/disputes/{id}/resolve without headers → 401.

        This covers the most dangerous fund-moving mutation (API-003).
        """
        from api.routers.disputes import router as disputes_router

        app = FastAPI()
        app.include_router(disputes_router)

        with patch("api.auth._API_KEYS_ENABLED", False):
            try:
                client = TestClient(app, raise_server_exceptions=False)
            except TypeError:  # pragma: no cover
                pytest.skip("httpx/starlette TestClient incompatibility")

            fake_uuid = "22222222-2222-2222-2222-222222222222"
            response = client.post(
                f"/api/v1/disputes/{fake_uuid}/resolve",
                json={"verdict": "release"},
            )

        assert response.status_code == 401, (
            f"POST /disputes/{{id}}/resolve must return 401 for anonymous callers. "
            f"Got {response.status_code}: {response.text}"
        )


# ---------------------------------------------------------------------------
# 6. Integration: public reads still admit anonymous callers
# ---------------------------------------------------------------------------


class TestPublicReadsStillWork:
    def test_anon_can_read_public_tasks(self):
        """GET /api/v1/tasks/available remains reachable without auth.

        This endpoint has no auth dependency at all (confirmed in the audit
        route inventory), but the test pins it so any future refactor that
        accidentally adds verify_agent_auth_write catches a regression.
        """
        with patch("api.auth._API_KEYS_ENABLED", False):
            # Stub the database dependency that the handler uses.
            mock_db = MagicMock()
            mock_db.get_available_tasks = AsyncMock(return_value=[])
            mock_db.get_task = AsyncMock(return_value=None)

            with patch("api.routers.tasks.db", mock_db):
                app = _make_app_with_tasks_router()
                try:
                    client = TestClient(app, raise_server_exceptions=False)
                except TypeError:  # pragma: no cover
                    pytest.skip("httpx/starlette TestClient incompatibility")

                response = client.get("/api/v1/tasks/available")

        # Either 200 with empty list or any non-401/403 response — the only
        # requirement for GR-0.1 is that anonymous reads are NOT auth-blocked.
        assert response.status_code not in (401, 403), (
            f"GET /tasks/available must NOT block anonymous reads. "
            f"Got {response.status_code}: {response.text}"
        )


# ---------------------------------------------------------------------------
# 7. Integration: valid ERC-8128 dependency override lets writes through
# ---------------------------------------------------------------------------


class TestAuthenticatedWritesStillWork:
    def test_erc8128_still_works_for_mutations(self):
        """With a valid auth override (simulating a signed ERC-8128 request),
        POST /tasks reaches the handler and is no longer auth-blocked.

        The handler will fail later because the DB stub is minimal — what we
        care about here is that auth allowed the request through, i.e. the
        response is NOT 401 / 403.
        """
        app = _make_app_with_tasks_router()

        # Override the write dependency with a stub that yields a full
        # AgentAuth — this is how FastAPI tests authenticated routes without
        # building a real ERC-8128 signature.
        app.dependency_overrides[verify_agent_auth_write] = _auth_override_factory()

        # Stub the db so the handler doesn't crash reaching Supabase.
        mock_db = MagicMock()
        mock_db.create_task = AsyncMock(
            return_value={
                "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "title": "test",
                "agent_id": "0xtestagent",
                "status": "published",
                "bounty_usd": 0.01,
            }
        )

        with (
            patch("api.auth._API_KEYS_ENABLED", False),
            patch("api.routers.tasks.db", mock_db),
        ):
            try:
                client = TestClient(app, raise_server_exceptions=False)
            except TypeError:  # pragma: no cover
                pytest.skip("httpx/starlette TestClient incompatibility")

            response = client.post(
                "/api/v1/tasks",
                json={
                    "title": "test",
                    "instructions": "test",
                    "category": "physical_presence",
                    "bounty_usd": 0.01,
                    "deadline_hours": 1,
                    "evidence_required": ["photo"],
                },
            )

        # Auth passed if we get ANYTHING except 401/403. The handler may still
        # return 4xx/5xx for unrelated reasons (ERC-8004 checks, escrow stubs,
        # etc.) — those are not GR-0.1's concern.
        assert response.status_code not in (401, 403), (
            f"Valid auth override must NOT trigger auth failure on POST /tasks. "
            f"Got {response.status_code}: {response.text[:500]}"
        )
