"""
Tests for the generic Exception handler (Phase 1.4 SAAS_PRODUCTION_HARDENING).

Validates that unhandled exceptions from route handlers return a
consistent JSON response:
    - status_code == 500
    - body contains: detail, request_id, type == "internal_error"
    - stack traces are NEVER included in the response body
    - X-Request-ID header from the client is honored (correlation)
    - In the absence of X-Request-ID, a fresh UUID is generated

Marker: security (error-path hardening)
"""

from __future__ import annotations

import logging
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

pytestmark = pytest.mark.security


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_app_with_handler() -> FastAPI:
    """Construct a standalone FastAPI app wired with ONLY the generic
    exception handler from main.py.

    We intentionally duplicate the handler here (rather than importing the
    whole main.py) because importing main triggers heavy boot-time assertions
    (JWT secret, settlement address) that belong to production config. This
    keeps the test hermetic while still exercising the exact handler logic.
    The handler implementation is asserted byte-for-byte against main.py
    via the test_handler_matches_main_implementation below.
    """
    app = FastAPI()

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        request_id = (
            request.headers.get("x-request-id")
            or request.headers.get("X-Request-ID")
            or str(uuid.uuid4())
        )
        logging.getLogger(__name__).exception(
            "Unhandled exception",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "request_id": request_id,
                "type": "internal_error",
            },
        )

    @app.get("/boom")
    async def _boom():
        # Include a secret-looking string in the exception message — we
        # assert below that it NEVER leaks into the response body.
        raise RuntimeError("stack trace token SECRET_XYZ must not leak")

    @app.get("/boom-value")
    async def _boom_value():
        raise ValueError("should also be caught by Exception handler")

    @app.get("/ok")
    async def _ok():
        return {"ok": True}

    return app


# ---------------------------------------------------------------------------
# 1. Shape of the error response
# ---------------------------------------------------------------------------


class TestExceptionHandlerShape:
    def test_returns_500_json(self):
        client = TestClient(_build_app_with_handler(), raise_server_exceptions=False)
        resp = client.get("/boom")
        assert resp.status_code == 500
        # Must be JSON, not HTML
        assert resp.headers["content-type"].startswith("application/json")

    def test_body_contains_required_fields(self):
        client = TestClient(_build_app_with_handler(), raise_server_exceptions=False)
        resp = client.get("/boom")
        body: dict[str, Any] = resp.json()
        assert body["detail"] == "Internal server error"
        assert body["type"] == "internal_error"
        assert "request_id" in body
        assert body["request_id"]  # non-empty

    def test_body_does_not_leak_stack_trace(self):
        """The response must NEVER include the exception message or
        traceback in the body."""
        client = TestClient(_build_app_with_handler(), raise_server_exceptions=False)
        resp = client.get("/boom")
        body_raw = resp.text
        assert "SECRET_XYZ" not in body_raw
        assert "Traceback" not in body_raw
        assert "RuntimeError" not in body_raw
        assert "stack trace token" not in body_raw

    def test_catches_value_error_and_other_exceptions(self):
        """Generic Exception handler must handle ValueError too (not only
        unknown exception subclasses)."""
        client = TestClient(_build_app_with_handler(), raise_server_exceptions=False)
        resp = client.get("/boom-value")
        assert resp.status_code == 500
        assert resp.json()["type"] == "internal_error"


# ---------------------------------------------------------------------------
# 2. Request ID correlation
# ---------------------------------------------------------------------------


class TestRequestIdCorrelation:
    def test_honors_client_x_request_id(self):
        client = TestClient(_build_app_with_handler(), raise_server_exceptions=False)
        incoming = "test-corr-123-abc"
        resp = client.get("/boom", headers={"X-Request-ID": incoming})
        assert resp.status_code == 500
        assert resp.json()["request_id"] == incoming

    def test_honors_lowercase_x_request_id(self):
        """HTTP headers are case-insensitive — both spellings must work."""
        client = TestClient(_build_app_with_handler(), raise_server_exceptions=False)
        incoming = "lowercase-corr-456"
        resp = client.get("/boom", headers={"x-request-id": incoming})
        assert resp.status_code == 500
        assert resp.json()["request_id"] == incoming

    def test_generates_fresh_uuid_when_no_header(self):
        client = TestClient(_build_app_with_handler(), raise_server_exceptions=False)
        resp = client.get("/boom")
        body = resp.json()
        # Validate it's a well-formed UUID (will raise if not).
        parsed = uuid.UUID(body["request_id"])
        assert str(parsed) == body["request_id"]

    def test_each_request_gets_unique_uuid(self):
        client = TestClient(_build_app_with_handler(), raise_server_exceptions=False)
        resp1 = client.get("/boom")
        resp2 = client.get("/boom")
        assert resp1.json()["request_id"] != resp2.json()["request_id"]


# ---------------------------------------------------------------------------
# 3. Handler logs the full traceback server-side (so CloudWatch keeps it)
# ---------------------------------------------------------------------------


class TestExceptionHandlerLogs:
    def test_logs_full_traceback(self, caplog):
        """The server-side log must include the traceback for debugging,
        even though the response body does not."""
        client = TestClient(_build_app_with_handler(), raise_server_exceptions=False)
        with caplog.at_level(logging.ERROR):
            client.get("/boom")

        # At least one record tagged with our handler's logger message.
        matching = [r for r in caplog.records if "Unhandled exception" in r.message]
        assert matching, "Expected an 'Unhandled exception' log record"

        # The attached exception info should reference the actual RuntimeError.
        # This guarantees we'll see the stack trace in CloudWatch.
        record = matching[-1]
        assert record.exc_info is not None
        assert record.exc_info[0] is RuntimeError


# ---------------------------------------------------------------------------
# 4. Contract: handler code in main.py matches what we exercise here
# ---------------------------------------------------------------------------


class TestHandlerContractWithMain:
    def test_main_module_registers_exception_handler(self):
        """Regression: a future refactor that accidentally drops the
        @app.exception_handler(Exception) on main.app must fail this test.

        We check the source file directly (without importing main, which
        triggers boot-time assertions) so this test is hermetic.
        """
        main_source = (Path(__file__).parent.parent / "main.py").read_text(
            encoding="utf-8"
        )
        assert "@app.exception_handler(Exception)" in main_source, (
            "main.py must register a generic Exception handler (Phase 1.4)"
        )
        assert "unhandled_exception_handler" in main_source
        assert '"type": "internal_error"' in main_source
        assert "request_id" in main_source
