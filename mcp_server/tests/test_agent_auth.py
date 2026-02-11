"""
Tests for Agent Authentication endpoint (POST /api/v1/agent/auth).

Covers:
- Valid API key → JWT returned
- Invalid key format → 401
- Key not in DB → 401
- Revoked/inactive key → 401
- JWT contains correct claims
- Dev mode fallback
"""

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest

pytestmark = pytest.mark.core
from fastapi import HTTPException

# Add parent to path for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.agent_auth import (
    authenticate_agent,
    create_agent_jwt,
    verify_agent_jwt,
    AgentAuthRequest,
    JWT_SECRET,
    JWT_ALGORITHM,
)


# ---------------------------------------------------------------------------
# JWT helper tests
# ---------------------------------------------------------------------------


class TestCreateAgentJWT:
    """Tests for create_agent_jwt helper."""

    def test_creates_valid_jwt(self):
        token, expires_at = create_agent_jwt("agent-123", "starter")

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify claims
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["sub"] == "agent-123"
        assert payload["agent_id"] == "agent-123"
        assert payload["tier"] == "starter"
        assert payload["type"] == "agent"
        assert "iat" in payload
        assert "exp" in payload

    def test_includes_organization_id_when_provided(self):
        token, _ = create_agent_jwt("agent-123", "enterprise", "org-456")

        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["org_id"] == "org-456"

    def test_omits_organization_id_when_none(self):
        token, _ = create_agent_jwt("agent-123", "free")

        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert "org_id" not in payload

    def test_returns_future_expiration(self):
        _, expires_at = create_agent_jwt("agent-123", "free")

        assert expires_at > datetime.now(timezone.utc)


class TestVerifyAgentJWT:
    """Tests for verify_agent_jwt helper."""

    def test_verifies_valid_token(self):
        token, _ = create_agent_jwt("agent-123", "growth")

        payload = verify_agent_jwt(token)
        assert payload["agent_id"] == "agent-123"
        assert payload["tier"] == "growth"

    def test_rejects_expired_token(self):
        # Create a token that's already expired
        payload = {
            "sub": "agent-123",
            "agent_id": "agent-123",
            "tier": "free",
            "type": "agent",
            "iat": int(time.time()) - 7200,
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        with pytest.raises(jwt.ExpiredSignatureError):
            verify_agent_jwt(token)

    def test_rejects_invalid_signature(self):
        token, _ = create_agent_jwt("agent-123", "free")

        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong-secret", algorithms=[JWT_ALGORITHM])

    def test_rejects_malformed_token(self):
        with pytest.raises(jwt.DecodeError):
            verify_agent_jwt("not-a-jwt-token")


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


class TestAuthenticateAgent:
    """Tests for POST /api/v1/agent/auth endpoint."""

    @pytest.mark.asyncio
    async def test_rejects_invalid_key_format(self):
        """Keys that don't match em_<tier>_<random> format should be rejected."""
        request = AgentAuthRequest(api_key="invalid-key-format")

        with pytest.raises(HTTPException) as exc:
            await authenticate_agent(request)

        assert exc.value.status_code == 401
        assert "invalid_key" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_rejects_empty_key(self):
        """Empty/whitespace keys should be rejected by pydantic validation."""
        with pytest.raises(Exception):
            AgentAuthRequest(api_key="")

    @pytest.mark.asyncio
    async def test_valid_key_returns_jwt(self):
        """A valid, active API key should return a JWT with correct claims."""
        api_key = "em_starter_" + "a" * 32

        # Mock the Supabase client
        mock_client = MagicMock()
        mock_execute = MagicMock()
        mock_execute.data = {
            "id": "key-1",
            "agent_id": "agent-42",
            "tier": "starter",
            "organization_id": "org-99",
            "is_active": True,
            "created_at": "2025-01-01T00:00:00Z",
        }

        # Chain: client.table().select().eq().single().execute()
        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_execute

        # Mock the update chain for last_used_at
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch("supabase_client.get_client", return_value=mock_client):
            request = AgentAuthRequest(api_key=api_key)
            response = await authenticate_agent(request)

        assert response.agent_id == "agent-42"
        assert response.tier == "starter"
        assert response.token is not None

        # Verify the JWT claims
        payload = jwt.decode(response.token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["agent_id"] == "agent-42"
        assert payload["tier"] == "starter"
        assert payload["org_id"] == "org-99"
        assert payload["type"] == "agent"

    @pytest.mark.asyncio
    async def test_inactive_key_returns_401(self):
        """A revoked/inactive key should return 401."""
        api_key = "em_free_" + "b" * 32

        mock_client = MagicMock()
        mock_execute = MagicMock()
        mock_execute.data = {
            "id": "key-2",
            "agent_id": "agent-99",
            "tier": "free",
            "organization_id": None,
            "is_active": False,  # Revoked!
            "created_at": "2025-01-01T00:00:00Z",
        }

        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_execute

        with patch("supabase_client.get_client", return_value=mock_client):
            request = AgentAuthRequest(api_key=api_key)

            with pytest.raises(HTTPException) as exc:
                await authenticate_agent(request)

            assert exc.value.status_code == 401
            assert "revoked" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_key_not_found_returns_401(self):
        """A key that doesn't exist in the DB should return 401."""
        api_key = "em_growth_" + "c" * 32

        mock_client = MagicMock()
        mock_execute = MagicMock()
        mock_execute.data = None  # Not found

        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_execute

        with patch("supabase_client.get_client", return_value=mock_client):
            request = AgentAuthRequest(api_key=api_key)

            with pytest.raises(HTTPException) as exc:
                await authenticate_agent(request)

            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_db_error_returns_401(self):
        """Database errors should return 401 (not 500) for security."""
        api_key = "em_free_" + "d" * 32

        with patch(
            "supabase_client.get_client",
            side_effect=Exception("Connection refused"),
        ):
            request = AgentAuthRequest(api_key=api_key)

            with pytest.raises(HTTPException) as exc:
                await authenticate_agent(request)

            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_dev_mode_fallback(self, monkeypatch):
        """In dev mode with DEV_ALLOW_FAKE_KEYS, should authenticate without DB."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("DEV_ALLOW_FAKE_KEYS", "true")

        api_key = "em_enterprise_testAgent_" + "e" * 32

        with patch(
            "supabase_client.get_client",
            side_effect=Exception("No DB"),
        ):
            request = AgentAuthRequest(api_key=api_key)
            response = await authenticate_agent(request)

        assert response.agent_id == "testAgent"
        assert response.tier == "enterprise"
        assert response.token is not None

    @pytest.mark.asyncio
    async def test_legacy_key_format_rejected(self):
        """Legacy sk_em_ format keys should still be validated."""
        api_key = "sk_em_" + "f" * 32

        mock_client = MagicMock()
        mock_execute = MagicMock()
        mock_execute.data = {
            "id": "key-legacy",
            "agent_id": "agent-legacy",
            "tier": "starter",
            "organization_id": None,
            "is_active": True,
            "created_at": "2025-01-01T00:00:00Z",
        }

        mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_execute
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch("supabase_client.get_client", return_value=mock_client):
            request = AgentAuthRequest(api_key=api_key)
            response = await authenticate_agent(request)

        assert response.agent_id == "agent-legacy"
