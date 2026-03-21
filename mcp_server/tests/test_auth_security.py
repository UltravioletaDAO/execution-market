"""
Tests for Auth Security Hardening (Phase 6).

Covers:
1. Worker endpoints without auth — should log warning or 401
2. Worker endpoints with wrong executor_id vs auth token — should reject
3. Supabase service role key validation in production

Marker: security
"""

import os
import sys
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.security

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.auth import (
    verify_worker_auth,
    _enforce_worker_identity,
    WorkerAuth,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(path: str = "/api/v1/tasks/abc/submit", headers: dict = None):
    """Create a mock FastAPI Request."""
    req = MagicMock()
    req.url.path = path
    req.headers = headers or {}
    return req


# ---------------------------------------------------------------------------
# 1. submit_work without auth
# ---------------------------------------------------------------------------


class TestSubmitWithoutAuth:
    """POST /tasks/{id}/submit without auth token."""

    @pytest.mark.asyncio
    async def test_no_auth_logs_warning_when_not_required(self, caplog):
        """Without EM_REQUIRE_WORKER_AUTH, missing auth logs SECURITY_AUDIT warning."""
        request = _make_request("/api/v1/tasks/task-123/submit")

        with patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", False):
            result = await verify_worker_auth(request, authorization=None)

        assert result is None
        assert "SECURITY_AUDIT" in caplog.text
        assert "worker_auth.missing" in caplog.text

    @pytest.mark.asyncio
    async def test_no_auth_raises_401_when_required(self):
        """With EM_REQUIRE_WORKER_AUTH=true, missing auth returns 401."""
        request = _make_request("/api/v1/tasks/task-123/submit")

        with patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", True):
            with pytest.raises(HTTPException) as exc:
                await verify_worker_auth(request, authorization=None)
            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_token_logs_warning(self, caplog):
        """Empty bearer token logs SECURITY_AUDIT warning."""
        request = _make_request("/api/v1/tasks/task-123/submit")

        with patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", False):
            result = await verify_worker_auth(request, authorization="Bearer ")

        assert result is None
        assert "worker_auth.empty_token" in caplog.text


# ---------------------------------------------------------------------------
# 2. apply_to_task without auth
# ---------------------------------------------------------------------------


class TestApplyWithoutAuth:
    """POST /tasks/{id}/apply without auth token."""

    @pytest.mark.asyncio
    async def test_no_auth_logs_warning_when_not_required(self, caplog):
        """Without EM_REQUIRE_WORKER_AUTH, missing auth logs warning."""
        request = _make_request("/api/v1/tasks/task-123/apply")

        with patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", False):
            result = await verify_worker_auth(request, authorization=None)

        assert result is None
        assert "SECURITY_AUDIT" in caplog.text

    @pytest.mark.asyncio
    async def test_no_auth_raises_401_when_required(self):
        """With EM_REQUIRE_WORKER_AUTH=true, missing auth returns 401."""
        request = _make_request("/api/v1/tasks/task-123/apply")

        with patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", True):
            with pytest.raises(HTTPException) as exc:
                await verify_worker_auth(request, authorization=None)
            assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# 3. rate_agent without auth
# ---------------------------------------------------------------------------


class TestRateAgentWithoutAuth:
    """POST /reputation/agents/rate without auth token."""

    @pytest.mark.asyncio
    async def test_no_auth_logs_warning_when_not_required(self, caplog):
        """Without EM_REQUIRE_WORKER_AUTH, missing auth logs warning."""
        request = _make_request("/api/v1/reputation/agents/rate")

        with patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", False):
            result = await verify_worker_auth(request, authorization=None)

        assert result is None
        assert "SECURITY_AUDIT" in caplog.text

    @pytest.mark.asyncio
    async def test_no_auth_raises_401_when_required(self):
        """With EM_REQUIRE_WORKER_AUTH=true, missing auth returns 401."""
        request = _make_request("/api/v1/reputation/agents/rate")

        with patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", True):
            with pytest.raises(HTTPException) as exc:
                await verify_worker_auth(request, authorization=None)
            assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# 4. Submit with WRONG executor_id vs auth token
# ---------------------------------------------------------------------------


class TestExecutorIdMismatch:
    """Request body executor_id does not match JWT-verified executor_id."""

    def test_mismatch_raises_403_when_required(self):
        """With EM_REQUIRE_WORKER_AUTH=true, mismatch returns 403."""
        worker_auth = WorkerAuth(
            executor_id="exec-real-auth-id",
            user_id="user-123",
            auth_method="jwt",
        )

        with patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", True):
            with pytest.raises(HTTPException) as exc:
                _enforce_worker_identity(
                    worker_auth,
                    body_executor_id="exec-SPOOFED-id",
                    request_path="/api/v1/tasks/task-123/submit",
                )
            assert exc.value.status_code == 403
            assert "does not match" in exc.value.detail

    def test_mismatch_logs_warning_when_not_required(self, caplog):
        """Without EM_REQUIRE_WORKER_AUTH, mismatch logs warning but allows."""
        worker_auth = WorkerAuth(
            executor_id="exec-real-auth-id",
            user_id="user-123",
            auth_method="jwt",
        )

        with patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", False):
            result = _enforce_worker_identity(
                worker_auth,
                body_executor_id="exec-SPOOFED-id",
                request_path="/api/v1/tasks/task-123/submit",
            )

        # Falls back to body value when not enforced
        assert result == "exec-SPOOFED-id"
        assert "SECURITY_AUDIT" in caplog.text
        assert "mismatch_warn" in caplog.text

    def test_matching_ids_pass_through(self):
        """When executor_id matches JWT, no error raised."""
        worker_auth = WorkerAuth(
            executor_id="exec-correct-id",
            user_id="user-123",
            auth_method="jwt",
        )

        with patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", True):
            result = _enforce_worker_identity(
                worker_auth,
                body_executor_id="exec-correct-id",
                request_path="/api/v1/tasks/task-123/submit",
            )

        assert result == "exec-correct-id"

    def test_no_auth_falls_back_to_body(self, caplog):
        """When worker_auth is None, falls back to body executor_id."""
        with patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", False):
            result = _enforce_worker_identity(
                None,
                body_executor_id="exec-body-id",
                request_path="/api/v1/tasks/task-123/apply",
            )

        assert result == "exec-body-id"
        assert "body_fallback" in caplog.text


# ---------------------------------------------------------------------------
# 5. Apply with wrong executor_id
# ---------------------------------------------------------------------------


class TestApplyExecutorIdMismatch:
    """Apply endpoint with mismatched executor_id."""

    def test_apply_mismatch_raises_403_when_required(self):
        """With EM_REQUIRE_WORKER_AUTH=true, apply mismatch returns 403."""
        worker_auth = WorkerAuth(
            executor_id="exec-real-worker",
            user_id="user-456",
            auth_method="jwt",
        )

        with patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", True):
            with pytest.raises(HTTPException) as exc:
                _enforce_worker_identity(
                    worker_auth,
                    body_executor_id="exec-IMPERSONATOR",
                    request_path="/api/v1/tasks/task-999/apply",
                )
            assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# 6. Supabase service role key validation
# ---------------------------------------------------------------------------


class TestSupabaseKeyValidation:
    """Verify _get_key() fails loudly in production without service role key."""

    def test_production_fails_without_service_role_key(self):
        """In production (EM_ENVIRONMENT=production), missing service role key is fatal."""
        env = {
            "EM_ENVIRONMENT": "production",
            # No SUPABASE_SERVICE_ROLE_KEY, no SUPABASE_SERVICE_KEY
            "SUPABASE_ANON_KEY": "anon-key-here",
        }

        with patch.dict(os.environ, env, clear=False):
            # Clear any cached values
            with patch.dict(
                os.environ,
                {k: v for k, v in env.items()},
                clear=False,
            ):
                # Remove service role keys if they exist in env
                os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
                os.environ.pop("SUPABASE_SERVICE_KEY", None)

                from supabase_client import _get_key

                with pytest.raises(ValueError, match="CRITICAL.*production"):
                    _get_key()

    def test_production_succeeds_with_service_role_key(self):
        """In production, service role key is used."""
        env = {
            "EM_ENVIRONMENT": "production",
            "SUPABASE_SERVICE_ROLE_KEY": "service-role-key-here",
        }

        with patch.dict(os.environ, env, clear=False):
            from supabase_client import _get_key

            result = _get_key()
            assert result == "service-role-key-here"

    def test_non_production_falls_back_to_anon_key_with_warning(self, caplog):
        """Non-production: falls back to anon key with SECURITY_AUDIT warning."""
        env = {
            "EM_ENVIRONMENT": "development",
            "SUPABASE_ANON_KEY": "anon-key-for-dev",
        }

        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
            os.environ.pop("SUPABASE_SERVICE_KEY", None)

            from supabase_client import _get_key

            with caplog.at_level(logging.WARNING):
                result = _get_key()

            assert result == "anon-key-for-dev"
            assert "SECURITY_AUDIT" in caplog.text
            assert "anon_fallback" in caplog.text

    def test_service_key_alias_works(self):
        """SUPABASE_SERVICE_KEY (legacy alias) is accepted."""
        env = {
            "EM_ENVIRONMENT": "production",
            "SUPABASE_SERVICE_KEY": "legacy-service-key",
        }

        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)

            from supabase_client import _get_key

            result = _get_key()
            assert result == "legacy-service-key"

    def test_no_keys_at_all_raises(self):
        """With no keys at all, raises ValueError."""
        env = {
            "EM_ENVIRONMENT": "development",
        }

        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
            os.environ.pop("SUPABASE_SERVICE_KEY", None)
            os.environ.pop("SUPABASE_ANON_KEY", None)

            from supabase_client import _get_key

            with pytest.raises(ValueError):
                _get_key()


# ---------------------------------------------------------------------------
# 7. Invalid JWT token handling
# ---------------------------------------------------------------------------


class TestInvalidJWTHandling:
    """Verify handling of malformed/invalid JWT tokens."""

    @pytest.mark.asyncio
    async def test_invalid_jwt_returns_none_when_not_required(self, caplog):
        """Invalid JWT returns None when auth not enforced (non-HTTP errors)."""
        request = _make_request("/api/v1/tasks/task-123/submit")

        # Simulate a generic JWT decode failure (not HTTPException)
        with (
            patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", False),
            patch("api.h2a._decode_supabase_jwt", side_effect=ValueError("bad token")),
        ):
            result = await verify_worker_auth(
                request, authorization="Bearer invalid.jwt.token"
            )

        assert result is None
        assert "SECURITY_AUDIT" in caplog.text
        assert "worker_auth.invalid_token" in caplog.text

    @pytest.mark.asyncio
    async def test_invalid_jwt_raises_401_when_required(self):
        """Invalid JWT raises 401 when auth enforced."""
        request = _make_request("/api/v1/tasks/task-123/submit")

        with patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", True):
            with pytest.raises(HTTPException) as exc:
                await verify_worker_auth(
                    request, authorization="Bearer not.a.valid.jwt"
                )
            assert exc.value.status_code in (401, 500)
