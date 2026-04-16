"""
Tests for agent-signed escrow flow (ADR-001 Phase 2).

Covers:
  1. Pre-auth validation (valid/invalid payloads)
  2. Mode A: lock_on_creation (relay to Facilitator)
  3. Mode B: lock_on_assignment (store pre-auth, execute at assignment)
  4. Lock failure rollback
  5. Server signing fallback
"""

import json
import os
import time
import pytest
from decimal import Decimal
from unittest.mock import patch, AsyncMock, MagicMock

DISPATCHER_MODULE = "integrations.x402.payment_dispatcher"


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


def _future_timestamp(offset_seconds: int = 3600) -> int:
    """Return a Unix timestamp in the future (default: 1 hour from now)."""
    return int(time.time()) + offset_seconds


def _make_valid_preauth_payload() -> dict:
    """Build a valid preauth payload with a future validBefore timestamp."""
    future_ts = _future_timestamp()
    return {
        "x402Version": 2,
        "scheme": "escrow",
        "payload": {
            "authorization": {
                "from": "0xAgentWallet1234567890abcdef1234567890abcdef",
                "to": "0xTokenCollector1234567890abcdef1234567890ab",
                "value": "5000000",
                "validAfter": "0",
                "validBefore": str(future_ts),
                "nonce": "0x" + "ab" * 32,
            },
            "signature": "0x" + "cc" * 65,
            "paymentInfo": {
                "operator": "0xOperator1234567890abcdef1234567890abcdef12",
                "receiver": "",
                "token": "0xUSDC1234567890abcdef1234567890abcdef123456",
                "maxAmount": "5000000",
                "preApprovalExpiry": future_ts,
                "authorizationExpiry": future_ts,
                "refundExpiry": future_ts + 86400,
                "minFeeBps": 0,
                "maxFeeBps": 1800,
                "feeReceiver": "0xOperator1234567890abcdef1234567890abcdef12",
                "salt": "0x" + "dd" * 32,
            },
        },
        "paymentRequirements": {
            "scheme": "escrow",
            "network": "eip155:8453",
        },
    }


# Keep a module-level reference for tests that only need structural validation
# (not time-dependent).  Re-generated per test run so validBefore is always future.
VALID_PREAUTH_PAYLOAD = _make_valid_preauth_payload()


# Dummy operator used in VALID_PREAUTH_PAYLOAD (must match for SC-009 check)
_TEST_OPERATOR = "0xOperator1234567890abcdef1234567890abcdef12"


def _make_dispatcher():
    """Create a PaymentDispatcher in fase2/direct_release mode."""
    with (
        patch(f"{DISPATCHER_MODULE}.FASE2_SDK_AVAILABLE", True),
        patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", True),
        patch(
            f"{DISPATCHER_MODULE}.NETWORK_CONFIG",
            {
                "base": {
                    "chain_id": 8453,
                    "rpc_url": "https://mainnet.base.org",
                    "tokens": {
                        "USDC": {
                            "decimals": 6,
                            "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                        }
                    },
                    "escrow_address": "0xEscrowContract",
                    "token_collector": "0xTokenCollector",
                    "operator": _TEST_OPERATOR,
                }
            },
        ),
        patch(f"{DISPATCHER_MODULE}.PLATFORM_FEE_PERCENT", Decimal("0.13")),
        patch(
            f"{DISPATCHER_MODULE}._get_platform_address",
            return_value="0xPlatformAddr",
        ),
        patch(
            f"{DISPATCHER_MODULE}._get_operator_for_network",
            return_value=_TEST_OPERATOR,
        ),
        patch.dict(os.environ, {"WALLET_PRIVATE_KEY": "0x" + "aa" * 32}),
    ):
        from integrations.x402.payment_dispatcher import PaymentDispatcher

        d = PaymentDispatcher(mode="fase2")
        d.escrow_mode = "direct_release"
        return d


# ═══════════════════════════════════════════════════════════════
# 1. Validation Tests
# ═══════════════════════════════════════════════════════════════


class TestValidateAgentPreauth:
    def test_valid_payload(self):
        d = _make_dispatcher()
        result = d.validate_agent_preauth(json.dumps(VALID_PREAUTH_PAYLOAD))
        assert result["x402Version"] == 2
        assert result["payload"]["authorization"]["from"].startswith("0x")
        assert result["payload"]["signature"].startswith("0x")

    def test_invalid_json(self):
        d = _make_dispatcher()
        with pytest.raises(ValueError, match="not valid JSON"):
            d.validate_agent_preauth("not json at all {{{")

    def test_missing_payload(self):
        d = _make_dispatcher()
        with pytest.raises(ValueError, match="missing 'payload'"):
            d.validate_agent_preauth(json.dumps({"x402Version": 2}))

    def test_missing_authorization(self):
        d = _make_dispatcher()
        bad = {
            "payload": {
                "signature": "0x123",
                "paymentInfo": {"operator": "0x1", "token": "0x2", "maxAmount": "1"},
            }
        }
        with pytest.raises(ValueError, match="missing 'payload.authorization'"):
            d.validate_agent_preauth(json.dumps(bad))

    def test_missing_auth_fields(self):
        d = _make_dispatcher()
        bad = {
            "payload": {
                "authorization": {"from": "0xAgent"},
                "signature": "0x123",
                "paymentInfo": {"operator": "0x1", "token": "0x2", "maxAmount": "1"},
            }
        }
        with pytest.raises(ValueError, match="authorization missing fields"):
            d.validate_agent_preauth(json.dumps(bad))

    def test_missing_signature(self):
        d = _make_dispatcher()
        bad = {
            "payload": {
                "authorization": {
                    "from": "0x1",
                    "to": "0x2",
                    "value": "100",
                    "validAfter": "0",
                    "validBefore": "999",
                    "nonce": "0x00",
                },
                "paymentInfo": {"operator": "0x1", "token": "0x2", "maxAmount": "1"},
            }
        }
        with pytest.raises(ValueError, match="missing 'payload.signature'"):
            d.validate_agent_preauth(json.dumps(bad))

    def test_missing_payment_info_fields(self):
        d = _make_dispatcher()
        bad = {
            "payload": {
                "authorization": {
                    "from": "0x1",
                    "to": "0x2",
                    "value": "100",
                    "validAfter": "0",
                    "validBefore": "999",
                    "nonce": "0x00",
                },
                "signature": "0x123",
                "paymentInfo": {"operator": "0x1"},
            }
        }
        with pytest.raises(ValueError, match="paymentInfo missing fields"):
            d.validate_agent_preauth(json.dumps(bad))


# ═══════════════════════════════════════════════════════════════
# 2. Mode A: Lock on Creation
# ═══════════════════════════════════════════════════════════════


class TestRelayToFacilitator:
    """Tests for relay_agent_auth_to_facilitator.

    Each test patches _get_operator_for_network so SC-009 sees the same dummy
    operator that lives in VALID_PREAUTH_PAYLOAD (avoids coupling tests to
    production contract addresses).
    """

    @pytest.mark.asyncio
    async def test_success(self):
        d = _make_dispatcher()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "transaction": {"hash": "0x" + "ab" * 32},
        }

        with (
            patch(
                f"{DISPATCHER_MODULE}._get_operator_for_network",
                return_value=_TEST_OPERATOR,
            ),
            patch("httpx.AsyncClient") as MockClient,
        ):
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            result = await d.relay_agent_auth_to_facilitator(
                payload=dict(VALID_PREAUTH_PAYLOAD),
                worker_address="0xWorker123",
                network="base",
            )

        assert result["success"] is True
        assert result["tx_hash"] == "0x" + "ab" * 32
        assert result["escrow_status"] == "locked"

    @pytest.mark.asyncio
    async def test_facilitator_rejects(self):
        d = _make_dispatcher()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": False,
            "error": "Insufficient allowance",
        }

        with (
            patch(
                f"{DISPATCHER_MODULE}._get_operator_for_network",
                return_value=_TEST_OPERATOR,
            ),
            patch("httpx.AsyncClient") as MockClient,
        ):
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            result = await d.relay_agent_auth_to_facilitator(
                payload=dict(VALID_PREAUTH_PAYLOAD),
                worker_address="0xWorker123",
                network="base",
            )

        assert result["success"] is False
        assert "Insufficient allowance" in result["error"]
        assert result["escrow_status"] == "lock_failed"

    @pytest.mark.asyncio
    async def test_fills_worker_address(self):
        d = _make_dispatcher()
        captured_payload = {}
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "transaction": {"hash": "0xabc"},
        }

        with (
            patch(
                f"{DISPATCHER_MODULE}._get_operator_for_network",
                return_value=_TEST_OPERATOR,
            ),
            patch("httpx.AsyncClient") as MockClient,
        ):
            mock_client_instance = AsyncMock()

            async def capture_post(url, json=None, **kwargs):
                captured_payload.update(json or {})
                return mock_response

            mock_client_instance.post = capture_post
            mock_client_instance.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            import copy

            payload = copy.deepcopy(VALID_PREAUTH_PAYLOAD)
            await d.relay_agent_auth_to_facilitator(
                payload=payload,
                worker_address="0xWorkerFilled",
                network="base",
            )

        # Verify worker address was filled in
        pi = captured_payload.get("payload", {}).get("paymentInfo", {})
        assert pi.get("receiver") == "0xWorkerFilled"
        pr = captured_payload.get("paymentRequirements", {})
        assert pr.get("payTo") == "0xWorkerFilled"


# ═══════════════════════════════════════════════════════════════
# 3. Mode B: Store Pre-auth
# ═══════════════════════════════════════════════════════════════


class TestStorePreauth:
    def test_stores_successfully(self):
        d = _make_dispatcher()
        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": 1}]
        )
        mock_client = MagicMock()
        mock_client.table.return_value = mock_table

        # db is imported lazily inside store_preauth, so we need to
        # inject a mock db module into sys.modules before calling
        import sys

        mock_db = MagicMock()
        mock_db.get_client.return_value = mock_client
        original_db = sys.modules.get("db")
        sys.modules["db"] = mock_db

        valid_before = _future_timestamp()
        payload = _make_valid_preauth_payload()
        try:
            result = d.store_preauth(
                task_id="task-123",
                payload_json=json.dumps(payload),
                valid_before=valid_before,
                network="base",
            )
        finally:
            if original_db is not None:
                sys.modules["db"] = original_db
            else:
                sys.modules.pop("db", None)

        assert result["success"] is True
        assert result["escrow_status"] == "pending_assignment"

        # Verify the insert was called with correct data
        insert_call = mock_table.insert.call_args[0][0]
        assert insert_call["task_id"] == "task-123"
        assert insert_call["status"] == "pending_assignment"
        meta = insert_call["metadata"]
        assert meta["escrow_timing"] == "lock_on_assignment"
        assert meta["preauth_valid_before"] == valid_before
        assert "preauth_signature" in meta

    def test_db_failure(self):
        d = _make_dispatcher()

        import sys

        mock_db = MagicMock()
        mock_db.get_client.side_effect = Exception("DB connection failed")
        original_db = sys.modules.get("db")
        sys.modules["db"] = mock_db

        valid_before = _future_timestamp()
        payload = _make_valid_preauth_payload()
        try:
            result = d.store_preauth(
                task_id="task-fail",
                payload_json=json.dumps(payload),
                valid_before=valid_before,
                network="base",
            )
        finally:
            if original_db is not None:
                sys.modules["db"] = original_db
            else:
                sys.modules.pop("db", None)

        assert result["success"] is False
        assert "DB connection failed" in result["error"]


# ═══════════════════════════════════════════════════════════════
# 4. EM_SERVER_SIGNING Guard
# ═══════════════════════════════════════════════════════════════


class TestServerSigningGuard:
    def test_server_signing_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("EM_SERVER_SIGNING", None)
            from integrations.x402.payment_dispatcher import _is_server_signing_enabled

            assert _is_server_signing_enabled() is False

    def test_server_signing_enabled(self):
        with patch.dict(os.environ, {"EM_SERVER_SIGNING": "true"}):
            from integrations.x402.payment_dispatcher import _is_server_signing_enabled

            assert _is_server_signing_enabled() is True

    def test_server_signing_key_raises_when_disabled(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("EM_SERVER_SIGNING", None)
            from integrations.x402.payment_dispatcher import _get_server_signing_key

            with pytest.raises(RuntimeError, match="Server-side signing is disabled"):
                _get_server_signing_key()
