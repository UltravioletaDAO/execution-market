"""
Tests for Phase 1 Track H — Backend API Hardening.

Covers:
  - API-002: POST /tasks/batch returns 503 (disabled)
  - API-003: POST /disputes/{id}/resolve requires ERC-8128, rejects API key auth
  - API-019: A2A JSON-RPC _extract_agent_id uses verified auth, not raw headers

Marker: security
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.security

# Add mcp_server/ to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.auth import AgentAuth  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_auth(
    *,
    agent_id: str = "0xtestcaller",
    wallet_address: str | None = "0xdeadbeef",
    auth_method: str = "erc8128",
) -> AgentAuth:
    return AgentAuth(
        agent_id=agent_id,
        wallet_address=wallet_address,
        auth_method=auth_method,
    )


# ===========================================================================
# API-002: Batch endpoint disabled
# ===========================================================================


class TestBatchEndpointDisabled:
    """POST /tasks/batch must return 503 regardless of auth."""

    @pytest.fixture(autouse=True)
    def _patch_deps(self):
        """Patch heavy dependencies so we can import the router."""
        with (
            patch.dict(
                sys.modules,
                {
                    "supabase_client": MagicMock(),
                    "audit": MagicMock(),
                },
            ),
        ):
            yield

    def test_batch_returns_503(self):
        """Batch endpoint always raises HTTPException(503)."""
        from fastapi import HTTPException

        # Import the endpoint function directly
        from api.routers.tasks import batch_create_tasks

        import asyncio

        # Build a minimal BatchCreateRequest mock
        mock_request = MagicMock()
        mock_request.tasks = []

        auth = _make_auth()

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                batch_create_tasks(request=mock_request, auth=auth)
            )

        assert exc_info.value.status_code == 503
        assert "temporarily disabled" in exc_info.value.detail
        assert "API-002" in exc_info.value.detail


# ===========================================================================
# API-003: Dispute resolve requires ERC-8128
# ===========================================================================


class TestDisputeResolveHardened:
    """POST /disputes/{id}/resolve must reject non-ERC-8128 callers."""

    @pytest.fixture(autouse=True)
    def _patch_deps(self):
        """Patch supabase_client.get_client for dispute router."""
        mock_client = MagicMock()
        # Default: no dispute found
        mock_execute = MagicMock()
        mock_execute.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_execute
        with patch("supabase_client.get_client", return_value=mock_client):
            yield

    @pytest.mark.asyncio
    async def test_rejects_api_key_auth(self):
        """API key auth method must be rejected with 403."""
        from fastapi import HTTPException
        from api.routers.disputes import resolve_dispute, ResolveDisputeRequest

        auth = _make_auth(auth_method="api_key")
        body = ResolveDisputeRequest(verdict="release", reason="Testing release")

        with pytest.raises(HTTPException) as exc_info:
            await resolve_dispute(dispute_id="test-dispute-1", body=body, auth=auth)

        assert exc_info.value.status_code == 403
        assert "ERC-8128" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_rejects_missing_wallet(self):
        """Missing wallet_address must be rejected with 403."""
        from fastapi import HTTPException
        from api.routers.disputes import resolve_dispute, ResolveDisputeRequest

        auth = _make_auth(wallet_address=None)
        body = ResolveDisputeRequest(verdict="refund", reason="Testing refund")

        with pytest.raises(HTTPException) as exc_info:
            await resolve_dispute(dispute_id="test-dispute-2", body=body, auth=auth)

        assert exc_info.value.status_code == 403
        assert "Wallet address required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_allows_erc8128_with_wallet(self):
        """ERC-8128 auth with wallet should pass the auth gate (may 404 on dispute lookup)."""
        from fastapi import HTTPException
        from api.routers.disputes import resolve_dispute, ResolveDisputeRequest

        auth = _make_auth(auth_method="erc8128", wallet_address="0xvalidwallet")
        body = ResolveDisputeRequest(verdict="release", reason="Legitimate resolution")

        # Should pass the auth gate and hit 404 (no dispute found in mock DB)
        with pytest.raises(HTTPException) as exc_info:
            await resolve_dispute(
                dispute_id="nonexistent-dispute", body=body, auth=auth
            )

        # If we get 404, the auth gate was passed
        assert exc_info.value.status_code == 404


# ===========================================================================
# API-019: A2A header spoofing prevention
# ===========================================================================


class TestA2AAgentIdExtraction:
    """_extract_agent_id must use verified auth, not raw headers."""

    @pytest.fixture(autouse=True)
    def _import_auth_module(self):
        """Pre-import api.auth so patch.object works on the module attribute."""
        import api.auth  # noqa: F401

        yield

    @pytest.mark.asyncio
    async def test_rejects_spoofed_erc8004_header(self):
        """Raw X-ERC8004-Agent-Id header must NOT be trusted without signature."""
        import api.auth as auth_mod
        from a2a.jsonrpc_router import _extract_agent_id

        mock_request = MagicMock()
        mock_request.headers = {"X-ERC8004-Agent-Id": "spoofed-agent-9999"}

        # Patch verify_agent_auth_write to raise (simulating failed auth)
        with patch.object(
            auth_mod,
            "verify_agent_auth_write",
            new_callable=AsyncMock,
            side_effect=Exception("Auth failed"),
        ):
            result = await _extract_agent_id(mock_request)

        # Must return None (unauthenticated), NOT the spoofed header value
        assert result is None

    @pytest.mark.asyncio
    async def test_uses_verified_wallet(self):
        """Verified ERC-8128 auth should return the wallet address."""
        import api.auth as auth_mod
        from a2a.jsonrpc_router import _extract_agent_id

        mock_request = MagicMock()
        mock_auth = AgentAuth(
            agent_id="2106",
            wallet_address="0xverifiedwallet",
            auth_method="erc8128",
        )

        with patch.object(
            auth_mod,
            "verify_agent_auth_write",
            new_callable=AsyncMock,
            return_value=mock_auth,
        ):
            result = await _extract_agent_id(mock_request)

        assert result == "erc8004:0xverifiedwallet"

    @pytest.mark.asyncio
    async def test_falls_back_to_agent_id_without_wallet(self):
        """If verified auth has no wallet, fall back to agent_id."""
        import api.auth as auth_mod
        from a2a.jsonrpc_router import _extract_agent_id

        mock_request = MagicMock()
        mock_auth = AgentAuth(
            agent_id="test-agent-42",
            wallet_address=None,
            auth_method="api_key",
        )

        with patch.object(
            auth_mod,
            "verify_agent_auth_write",
            new_callable=AsyncMock,
            return_value=mock_auth,
        ):
            result = await _extract_agent_id(mock_request)

        assert result == "agent:test-agent-42"

    @pytest.mark.asyncio
    async def test_returns_none_on_auth_failure(self):
        """When auth fails entirely, return None (caller gets 401)."""
        import api.auth as auth_mod
        from a2a.jsonrpc_router import _extract_agent_id

        mock_request = MagicMock()
        mock_request.headers = {
            "X-API-Key": "invalid-key",
            "X-ERC8004-Agent-Id": "spoofed",
        }

        with patch.object(
            auth_mod,
            "verify_agent_auth_write",
            new_callable=AsyncMock,
            side_effect=Exception("No valid auth"),
        ):
            result = await _extract_agent_id(mock_request)

        assert result is None
