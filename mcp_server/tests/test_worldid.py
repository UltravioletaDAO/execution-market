"""Tests for World ID 4.0 integration."""

import sys
from pathlib import Path

# Ensure mcp_server root is on sys.path for direct imports
_mcp_root = str(Path(__file__).resolve().parent.parent)
if _mcp_root not in sys.path:
    sys.path.insert(0, _mcp_root)

# Force-remove stale 'integrations' stub if another test file inserted one
if "integrations" in sys.modules and not hasattr(
    sys.modules["integrations"], "__path__"
):
    del sys.modules["integrations"]
if "integrations.worldid" in sys.modules and not hasattr(
    sys.modules["integrations.worldid"], "__path__"
):
    del sys.modules["integrations.worldid"]

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

pytestmark = pytest.mark.worldid


class TestWorldIdClient:
    """Test the World ID client crypto functions."""

    def test_hash_to_field_length(self):
        """hashToField returns 32 bytes with top byte zeroed."""
        from integrations.worldid.client import _hash_to_field

        result = _hash_to_field(b"test-input")
        assert len(result) == 32
        assert result[0] == 0  # Top byte is zero (right-shifted by 8)

    def test_hash_to_field_deterministic(self):
        """hashToField is deterministic."""
        from integrations.worldid.client import _hash_to_field

        r1 = _hash_to_field(b"same-input")
        r2 = _hash_to_field(b"same-input")
        assert r1 == r2

    def test_hash_ethereum_message(self):
        """EIP-191 message hashing produces 32-byte hash."""
        from integrations.worldid.client import _hash_ethereum_message

        result = _hash_ethereum_message(b"test message")
        assert len(result) == 32

    def test_compute_rp_signature_message_length(self):
        """RP signature message is 81 bytes: 1 + 32 + 8 + 8 + 32."""
        from integrations.worldid.client import (
            _compute_rp_signature_message,
            _hash_to_field,
        )

        nonce = _hash_to_field(b"random-nonce")
        msg = _compute_rp_signature_message(
            nonce=nonce,
            created_at=1700000000,
            expires_at=1700000300,
            action="verify-worker",
        )
        assert len(msg) == 81
        assert msg[0:1] == b"\x01"  # Version byte

    @patch.dict(
        "os.environ",
        {
            "WORLD_ID_SIGNING_KEY": "a" * 64,  # Dummy 32-byte hex key
            "WORLD_ID_RP_ID": "test-rp-id",
            "WORLD_ID_APP_ID": "app_test",
        },
    )
    def test_sign_request_returns_valid_structure(self):
        """sign_request() returns RPSignatureResult with correct fields."""
        # Reload module to pick up env vars
        import importlib
        import integrations.worldid.client as wc

        importlib.reload(wc)

        result = wc.sign_request(action="verify-worker")
        assert result.action == "verify-worker"
        assert result.rp_id == "test-rp-id"
        assert len(result.nonce) == 64  # 32 bytes hex
        assert len(result.signature) == 130  # 65 bytes hex
        assert result.expires_at > result.created_at

    def test_sign_request_no_key_raises(self):
        """sign_request() raises ValueError if signing key not configured."""
        import importlib
        import integrations.worldid.client as wc

        with patch.dict("os.environ", {"WORLD_ID_SIGNING_KEY": ""}, clear=False):
            importlib.reload(wc)
            with pytest.raises(ValueError, match="WORLD_ID_SIGNING_KEY"):
                wc.sign_request()


class TestWorldIdVerification:
    """Test the Cloud API verification function."""

    @pytest.mark.asyncio
    async def test_verify_returns_error_if_no_rp_id(self):
        """verify_world_id_proof returns error if RP ID not configured."""
        with patch.dict("os.environ", {"WORLD_ID_RP_ID": ""}, clear=False):
            import importlib
            import integrations.worldid.client as wc

            importlib.reload(wc)

            result = await wc.verify_world_id_proof(
                proof="0xabc",
                merkle_root="0xdef",
                nullifier_hash="0x123",
                verification_level="orb",
            )
            assert not result.success
            assert "not configured" in result.error

    @pytest.mark.asyncio
    async def test_verify_calls_cloud_api(self):
        """verify_world_id_proof calls the correct Cloud API endpoint."""
        with patch.dict("os.environ", {"WORLD_ID_RP_ID": "test-rp"}, clear=False):
            import importlib
            import integrations.worldid.client as wc

            importlib.reload(wc)

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "verification_level": "orb",
            }

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post.return_value = mock_response
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_cls.return_value = mock_client

                result = await wc.verify_world_id_proof(
                    proof="0xabc",
                    merkle_root="0xdef",
                    nullifier_hash="0x123",
                    verification_level="orb",
                )

                assert result.success
                assert result.verification_level == "orb"
                assert result.nullifier_hash == "0x123"

                # Verify correct URL was called
                call_args = mock_client.post.call_args
                assert "test-rp" in call_args[0][0]
