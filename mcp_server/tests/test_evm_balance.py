"""Tests for the EVM USDC balance reader (Phase 1 — Base on-ramp gating).

Mirrors the Solana balance tests in test_moonpay_balance_gate.py. The HTTP
layer is mocked via an injected client; no live RPC is hit.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.payments


def _eth_call_ok(result_hex: str) -> dict:
    return {"jsonrpc": "2.0", "id": 1, "result": result_hex}


class TestGetEvmUsdcBalance:
    @pytest.mark.asyncio
    async def test_reads_balance_base(self):
        from integrations.evm import balance as mod

        # 100.5 USDC at 6 decimals = 100_500_000 base units.
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _eth_call_ok(hex(100_500_000))

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        bal = await mod.get_evm_usdc_balance(
            "0x1111111111111111111111111111111111111111",
            network="base",
            http=mock_client,
        )
        assert bal == Decimal("100.5")

    @pytest.mark.asyncio
    async def test_zero_balance(self):
        from integrations.evm import balance as mod

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _eth_call_ok("0x0")
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        bal = await mod.get_evm_usdc_balance("0xabc", http=mock_client)
        assert bal == Decimal("0")

    @pytest.mark.asyncio
    async def test_rpc_error_returns_zero(self):
        from integrations.evm import balance as mod

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32000, "message": "execution reverted"},
        }
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        bal = await mod.get_evm_usdc_balance("0xabc", http=mock_client)
        assert bal == Decimal("0")

    @pytest.mark.asyncio
    async def test_http_500_returns_zero(self):
        from integrations.evm import balance as mod

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {}
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        bal = await mod.get_evm_usdc_balance("0xabc", http=mock_client)
        assert bal == Decimal("0")

    @pytest.mark.asyncio
    async def test_exception_returns_zero(self):
        from integrations.evm import balance as mod

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=RuntimeError("network down"))

        bal = await mod.get_evm_usdc_balance("0xabc", http=mock_client)
        assert bal == Decimal("0")

    @pytest.mark.asyncio
    async def test_unknown_network_returns_zero(self):
        from integrations.evm import balance as mod

        bal = await mod.get_evm_usdc_balance("0xabc", network="fakechain")
        assert bal == Decimal("0")

    @pytest.mark.asyncio
    async def test_empty_wallet_returns_zero(self):
        from integrations.evm import balance as mod

        bal = await mod.get_evm_usdc_balance("", network="base")
        assert bal == Decimal("0")

    @pytest.mark.asyncio
    async def test_non_hex_result_returns_zero(self):
        from integrations.evm import balance as mod

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _eth_call_ok("not-hex")
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        bal = await mod.get_evm_usdc_balance("0xabc", http=mock_client)
        assert bal == Decimal("0")


class TestEncodeBalanceOf:
    def test_pads_address_and_prefixes_selector(self):
        from integrations.evm.balance import _encode_balance_of

        data = _encode_balance_of("0xAbC0000000000000000000000000000000000001")
        assert data.startswith("0x70a08231")
        # selector ("0x" + 8 hex) + 64-hex (32-byte) address arg.
        assert len(data) == 10 + 64
        assert data.endswith("abc0000000000000000000000000000000000001")


class TestOnrampMinBuy:
    """build_insufficient_funds_onramp floors per-currency (Base=$5, Sol=$20)."""

    def test_base_floor_is_five(self, monkeypatch):
        monkeypatch.setenv("EM_MOONPAY_ENABLED", "true")
        monkeypatch.setenv("MOONPAY_SECRET_KEY", "sk_test_unit")
        monkeypatch.setenv("MOONPAY_PUBLIC_KEY", "pk_test_unit")
        monkeypatch.setenv("MOONPAY_WIDGET_BASE_URL", "https://buy.moonpay.com")
        import importlib
        import sys

        import integrations.moonpay.client  # noqa: F401

        importlib.reload(sys.modules["integrations.moonpay.client"])
        from integrations.moonpay.onramp import build_insufficient_funds_onramp

        result = build_insufficient_funds_onramp(
            wallet="0x1111111111111111111111111111111111111111",
            qty_needed=Decimal("2"),
            currency="usdc_base",
        )
        assert result is not None
        assert Decimal(result["qty_needed"]) == Decimal("5.00")
        assert result["currency"] == "usdc_base"
