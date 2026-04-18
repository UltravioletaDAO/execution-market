"""
Tests for SecurityHeadersMiddleware (Phase 1.1 SAAS_PRODUCTION_HARDENING).

Validates that every response carries the defense-in-depth security headers:
    - Strict-Transport-Security
    - X-Content-Type-Options
    - X-Frame-Options
    - Referrer-Policy
    - Permissions-Policy

Also asserts the middleware still applies on:
    * 404 responses (no matching route)
    * exception / 500 responses (error paths)
    * handler-set headers are preserved (no override of explicit values)

Marker: security
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

pytestmark = pytest.mark.security

from api.middleware import SecurityHeadersMiddleware  # noqa: E402


EXPECTED_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=(), payment=()",
}


def _build_app() -> FastAPI:
    """Build a minimal FastAPI app wired with SecurityHeadersMiddleware only.

    We deliberately avoid importing mcp_server.main because the full app has
    heavy imports (web3, supabase, etc.) that we don't need to validate
    header injection behavior on the happy path, 404, HTTPException, and
    handler-override cases.

    NOTE: 500 responses from an unhandled exception that escapes to
    Starlette's ``ServerErrorMiddleware`` are NOT covered by this bare
    wiring — see ``test_headers_on_unhandled_exception_via_production_stack``
    for why, and for the end-to-end guarantee via ``add_api_middleware``.
    """
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/health")
    async def _health():
        return {"status": "ok"}

    @app.get("/http-error")
    async def _http_error():
        raise HTTPException(status_code=418, detail="I'm a teapot")

    @app.get("/preset-header")
    async def _preset():
        # Handler explicitly sets X-Frame-Options — middleware must not
        # override it (setdefault semantics).
        return JSONResponse(
            content={"ok": True},
            headers={"X-Frame-Options": "SAMEORIGIN"},
        )

    return app


# ---------------------------------------------------------------------------
# 1. Happy path — all 5 headers present on 200 responses
# ---------------------------------------------------------------------------


class TestSecurityHeadersPresent:
    def test_all_five_headers_on_200(self):
        client = TestClient(_build_app())
        resp = client.get("/health")

        assert resp.status_code == 200
        for header_name, expected_value in EXPECTED_HEADERS.items():
            assert header_name in resp.headers, (
                f"Missing security header: {header_name}"
            )
            assert resp.headers[header_name] == expected_value, (
                f"Wrong value for {header_name}: "
                f"got {resp.headers[header_name]!r}, "
                f"expected {expected_value!r}"
            )

    def test_hsts_includes_preload_flag(self):
        """Strict-Transport-Security must be preload-ready for HSTS list submission."""
        client = TestClient(_build_app())
        resp = client.get("/health")
        hsts = resp.headers["Strict-Transport-Security"]
        assert "max-age=63072000" in hsts  # 2 years
        assert "includeSubDomains" in hsts
        assert "preload" in hsts

    def test_permissions_policy_denies_sensitive_apis(self):
        """The default permissions policy must deny geo/camera/mic/payment."""
        client = TestClient(_build_app())
        resp = client.get("/health")
        policy = resp.headers["Permissions-Policy"]
        for api_name in ("geolocation", "camera", "microphone", "payment"):
            # Every listed API must be explicitly set to () (= deny all origins).
            assert f"{api_name}=()" in policy, (
                f"Permissions-Policy must deny {api_name} by default"
            )


# ---------------------------------------------------------------------------
# 2. Error paths — headers still injected on 404 / 500 / HTTPException
# ---------------------------------------------------------------------------


class TestSecurityHeadersOnErrors:
    def test_headers_on_404(self):
        client = TestClient(_build_app())
        resp = client.get("/does-not-exist")
        assert resp.status_code == 404
        for header_name in EXPECTED_HEADERS:
            assert header_name in resp.headers, f"Missing {header_name} on 404"

    def test_headers_on_http_exception(self):
        client = TestClient(_build_app())
        resp = client.get("/http-error")
        assert resp.status_code == 418
        for header_name in EXPECTED_HEADERS:
            assert header_name in resp.headers

    def test_headers_on_unhandled_exception_via_production_stack(self):
        """Even when the route raises an unhandled RuntimeError, security
        headers must land on the 500 response — BUT only via the full
        production middleware stack (``add_api_middleware``), not via a
        bare ``app.add_middleware(SecurityHeadersMiddleware)`` + generic
        ``@app.exception_handler(Exception)``.

        Why: Starlette's ``build_middleware_stack`` routes
        ``@app.exception_handler(Exception)`` (and 500 handlers) to
        ``ServerErrorMiddleware``, which sits OUTSIDE the user middleware
        stack — so a response emitted by that handler bypasses
        ``SecurityHeadersMiddleware`` entirely.

        Production avoids this hole because ``ErrorHandlingMiddleware``
        (an inner ``BaseHTTPMiddleware``) catches ``Exception`` INSIDE the
        user stack and emits a JSON 500 that flows back out through
        ``SecurityHeadersMiddleware``. This test wires the full stack and
        asserts the end-to-end guarantee.
        """
        from api.middleware import add_api_middleware

        app = FastAPI()

        @app.get("/boom")
        async def _boom_inner():
            raise RuntimeError("boom from route")

        add_api_middleware(app)

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/boom")
        assert resp.status_code == 500
        # ErrorHandlingMiddleware catches the RuntimeError and produces a
        # JSON 500 that flows through SecurityHeadersMiddleware on the way
        # out — headers land.
        for header_name in EXPECTED_HEADERS:
            assert header_name in resp.headers, (
                f"Missing {header_name} on 500 (production stack)"
            )


# ---------------------------------------------------------------------------
# 3. Handler-set headers are preserved
# ---------------------------------------------------------------------------


class TestSecurityHeadersRespectExplicit:
    def test_handler_override_is_preserved(self):
        """If a handler explicitly sets one of the security headers, the
        middleware must NOT clobber it. We use setdefault semantics so that
        a specialized page (e.g. a framed OAuth callback) can opt into
        SAMEORIGIN without losing the other defaults.
        """
        client = TestClient(_build_app())
        resp = client.get("/preset-header")
        assert resp.status_code == 200
        # Handler value wins:
        assert resp.headers["X-Frame-Options"] == "SAMEORIGIN"
        # Other defaults are still present:
        for header_name, expected_value in EXPECTED_HEADERS.items():
            if header_name == "X-Frame-Options":
                continue
            assert resp.headers[header_name] == expected_value


# ---------------------------------------------------------------------------
# 4. Integration with the full middleware stack via add_api_middleware
# ---------------------------------------------------------------------------


class TestAddApiMiddlewareWiresSecurityHeaders:
    def test_add_api_middleware_registers_security_headers(self):
        """Ensure SecurityHeadersMiddleware is part of the standard stack.

        Exercises the exact wiring used by main.py so a future refactor
        that accidentally removes the add_middleware call is caught.
        """
        from api.middleware import add_api_middleware

        app = FastAPI()

        @app.get("/ping")
        async def _ping():
            return {"pong": True}

        add_api_middleware(app)

        client = TestClient(app)
        resp = client.get("/ping")
        # Rate limiting / request logging shouldn't interfere on a single
        # unauthenticated request — /ping is not in EXEMPT_PATHS but a
        # single hit won't trigger the limiter.
        assert resp.status_code == 200
        for header_name in EXPECTED_HEADERS:
            assert header_name in resp.headers, (
                f"add_api_middleware failed to wire {header_name}"
            )
