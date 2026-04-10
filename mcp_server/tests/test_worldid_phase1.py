"""
Tests for Phase 1 CRY-002, CRY-007, CRY-010 — World ID security hardening.

CRY-002: verification_level must come from Cloud API response, not client input.
CRY-007: World ID enforcement must fail-closed on errors (not fail-open).
CRY-010: action parameter must be server-pinned (DEFAULT_ACTION), not client-controlled.

Marker: security
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.security

# Add mcp_server/ to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Stub external dependencies
for _m in [
    "integrations.erc8004",
    "integrations.erc8004.identity",
    "integrations.erc8004.facilitator_client",
    "supabase_client",
]:
    if _m not in sys.modules:
        s = ModuleType(_m)
        if _m.endswith(".identity"):
            s.check_worker_identity = None
        elif _m.endswith(".facilitator_client"):
            s.get_facilitator_client = None
        elif _m == "supabase_client":
            s.get_client = MagicMock()
        sys.modules[_m] = s


from integrations.worldid.client import (
    verify_world_id_proof,
    DEFAULT_ACTION,
)


# ---------------------------------------------------------------------------
# CRY-002 Tests — verification_level from API, not client
# ---------------------------------------------------------------------------


class TestCRY002VerificationLevelFromAPI:
    """CRY-002: verification_level must come from Cloud API, not client."""

    @pytest.mark.asyncio
    async def test_client_cannot_forge_orb_level(self):
        """Client claims 'orb' but API says 'device' -> returned level is 'device'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "nullifier": "0xabc123",
            "verification_level": "device",  # API says device
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("integrations.worldid.client.WORLD_ID_RP_ID", "test-rp-id"):
            with patch(
                "integrations.worldid.client.httpx.AsyncClient",
                return_value=mock_client,
            ):
                result = await verify_world_id_proof(
                    nullifier_hash="0xabc123",
                    verification_level="orb",  # Client claims orb
                    nonce="test-nonce",
                    responses=[{"response": "data"}],
                )

        assert result.success is True
        # CRITICAL: level must be "device" (from API), NOT "orb" (from client)
        assert result.verification_level == "device", (
            f"Expected 'device' from API but got '{result.verification_level}' — "
            "CRY-002 verification_level forgery not fixed"
        )

    @pytest.mark.asyncio
    async def test_api_orb_level_trusted(self):
        """API says 'orb' -> returned level is 'orb' regardless of client input."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "nullifier": "0xdef456",
            "verification_level": "orb",  # API confirms orb
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("integrations.worldid.client.WORLD_ID_RP_ID", "test-rp-id"):
            with patch(
                "integrations.worldid.client.httpx.AsyncClient",
                return_value=mock_client,
            ):
                result = await verify_world_id_proof(
                    nullifier_hash="0xdef456",
                    verification_level="device",  # Client says device
                    nonce="test-nonce",
                    responses=[{"response": "data"}],
                )

        assert result.success is True
        assert result.verification_level == "orb", (
            f"Expected 'orb' from API but got '{result.verification_level}'"
        )

    @pytest.mark.asyncio
    async def test_api_no_level_defaults_to_device(self):
        """API does not return verification_level -> default to 'device' (safest)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "nullifier": "0xghi789",
            # No verification_level or credential_type in response
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("integrations.worldid.client.WORLD_ID_RP_ID", "test-rp-id"):
            with patch(
                "integrations.worldid.client.httpx.AsyncClient",
                return_value=mock_client,
            ):
                result = await verify_world_id_proof(
                    nullifier_hash="0xghi789",
                    verification_level="orb",  # Client claims orb
                    nonce="test-nonce",
                    responses=[{"response": "data"}],
                )

        assert result.success is True
        assert result.verification_level == "device", (
            f"Expected 'device' default but got '{result.verification_level}'"
        )

    @pytest.mark.asyncio
    async def test_api_credential_type_fallback(self):
        """API returns credential_type instead of verification_level -> use it."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "nullifier": "0xjkl012",
            "credential_type": "orb",  # Alternative field name
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("integrations.worldid.client.WORLD_ID_RP_ID", "test-rp-id"):
            with patch(
                "integrations.worldid.client.httpx.AsyncClient",
                return_value=mock_client,
            ):
                result = await verify_world_id_proof(
                    nullifier_hash="0xjkl012",
                    verification_level="device",  # Client says device
                    nonce="test-nonce",
                    responses=[{"response": "data"}],
                )

        assert result.success is True
        assert result.verification_level == "orb"


# ---------------------------------------------------------------------------
# CRY-007 Tests — fail-closed on errors
# ---------------------------------------------------------------------------


class TestCRY007FailClosed:
    """CRY-007: World ID enforcement must fail-closed on errors."""

    @pytest.mark.asyncio
    async def test_api_error_fails_closed(self):
        """API returns HTTP error -> verification fails (not passes)."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("integrations.worldid.client.WORLD_ID_RP_ID", "test-rp-id"):
            with patch(
                "integrations.worldid.client.httpx.AsyncClient",
                return_value=mock_client,
            ):
                result = await verify_world_id_proof(
                    nullifier_hash="0xerror",
                    verification_level="orb",
                    nonce="test-nonce",
                    responses=[{"response": "data"}],
                )

        assert result.success is False, "API error must fail-closed (reject)"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_api_network_error_fails_closed(self):
        """Network timeout/error -> verification fails."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("integrations.worldid.client.WORLD_ID_RP_ID", "test-rp-id"):
            with patch(
                "integrations.worldid.client.httpx.AsyncClient",
                return_value=mock_client,
            ):
                result = await verify_world_id_proof(
                    nullifier_hash="0xtimeout",
                    verification_level="orb",
                    nonce="test-nonce",
                    responses=[{"response": "data"}],
                )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_enforcement_db_error_fails_closed(self):
        """CRY-007: DB error in enforcement check -> blocks (not allows)."""
        from integrations.worldid.enforcement import check_world_id_eligibility

        # Mock PlatformConfig to enable enforcement and return threshold
        mock_platform_config = MagicMock()
        mock_platform_config.get = AsyncMock(side_effect=[True, Decimal("500.00")])

        # Mock DB client that throws an error
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = Exception(
            "DB connection lost"
        )

        with patch.dict("os.environ", {"EM_WORLD_ID_ENABLED": "true"}):
            with patch.dict(
                "sys.modules",
                {
                    "config": MagicMock(),
                    "config.platform_config": MagicMock(
                        PlatformConfig=mock_platform_config
                    ),
                },
            ):
                allowed, error = await check_world_id_eligibility(
                    executor_id="test-executor-123",
                    bounty_usd=Decimal("1000.00"),  # Above threshold
                    db_client=mock_db,
                )

        assert allowed is False, (
            "DB error must fail-CLOSED (block access), not fail-open"
        )
        assert error is not None
        assert error.get("error") == "world_id_check_failed"

    @pytest.mark.asyncio
    async def test_enforcement_allows_when_below_threshold(self):
        """Bounty below threshold -> allowed without World ID."""
        from integrations.worldid.enforcement import check_world_id_eligibility

        mock_platform_config = MagicMock()
        mock_platform_config.get = AsyncMock(side_effect=[True, Decimal("500.00")])

        with patch.dict("os.environ", {"EM_WORLD_ID_ENABLED": "true"}):
            with patch.dict(
                "sys.modules",
                {
                    "config": MagicMock(),
                    "config.platform_config": MagicMock(
                        PlatformConfig=mock_platform_config
                    ),
                },
            ):
                allowed, error = await check_world_id_eligibility(
                    executor_id="test-executor-123",
                    bounty_usd=Decimal("10.00"),  # Below $500 threshold
                )

        assert allowed is True
        assert error is None


# ---------------------------------------------------------------------------
# CRY-010 Tests — action is server-pinned
# ---------------------------------------------------------------------------


class TestCRY010ActionServerPinned:
    """CRY-010: action parameter sent to API must come from server, not client."""

    @pytest.mark.asyncio
    async def test_action_is_server_pinned(self):
        """Action sent to Cloud API uses DEFAULT_ACTION, ignoring client input."""
        captured_payload = {}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "nullifier": "0xaction_test",
            "verification_level": "orb",
        }

        async def capture_post(url, json=None, **kwargs):
            captured_payload.update(json or {})
            return mock_response

        mock_client = AsyncMock()
        mock_client.post = capture_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("integrations.worldid.client.WORLD_ID_RP_ID", "test-rp-id"):
            with patch(
                "integrations.worldid.client.httpx.AsyncClient",
                return_value=mock_client,
            ):
                await verify_world_id_proof(
                    nullifier_hash="0xaction_test",
                    verification_level="orb",
                    nonce="test-nonce",
                    action="malicious-action",  # Attacker-supplied action
                    responses=[{"response": "data"}],
                )

        # The action sent to the API must be the server's DEFAULT_ACTION
        assert captured_payload.get("action") == DEFAULT_ACTION, (
            f"Expected server-pinned action '{DEFAULT_ACTION}' but got "
            f"'{captured_payload.get('action')}' — client can control action"
        )

    @pytest.mark.asyncio
    async def test_action_pinned_in_legacy_v2_path(self):
        """Action is also server-pinned in the v2 legacy fallback path."""
        captured_payload = {}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "nullifier": "0xlegacy_test",
            "verification_level": "device",
        }

        async def capture_post(url, json=None, **kwargs):
            captured_payload.update(json or {})
            return mock_response

        mock_client = AsyncMock()
        mock_client.post = capture_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # WORLD_ID_RP_ID must be set (non-empty) to avoid early return.
        # v2 path is triggered by responses=None.
        with patch("integrations.worldid.client.WORLD_ID_APP_ID", "test-app-id"):
            with patch("integrations.worldid.client.WORLD_ID_RP_ID", "test-rp-id"):
                with patch(
                    "integrations.worldid.client.httpx.AsyncClient",
                    return_value=mock_client,
                ):
                    await verify_world_id_proof(
                        nullifier_hash="0xlegacy_test",
                        verification_level="device",
                        proof="0xproof",
                        merkle_root="0xroot",
                        action="attacker-action",  # Should be ignored
                        responses=None,  # No responses -> v2 path
                    )

        assert captured_payload.get("action") == DEFAULT_ACTION, (
            f"v2 path: expected '{DEFAULT_ACTION}' but got '{captured_payload.get('action')}'"
        )
