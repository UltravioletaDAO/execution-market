"""Tests for the EVM USDC balance reader (Phase 1 — Base on-ramp gating).

Mirrors the Solana balance tests in test_moonpay_balance_gate.py. The HTTP
layer is mocked via an injected client; no live RPC is hit.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

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

    def test_base_floor_is_five(self, _moonpay_enabled):
        from integrations.moonpay.onramp import build_insufficient_funds_onramp

        result = build_insufficient_funds_onramp(
            wallet="0x1111111111111111111111111111111111111111",
            qty_needed=Decimal("2"),
            currency="usdc_base",
        )
        assert result is not None
        assert Decimal(result["qty_needed"]) == Decimal("5.00")
        assert result["currency"] == "usdc_base"


@pytest.fixture
def _moonpay_enabled(monkeypatch):
    """Enable MoonPay with deterministic test keys.

    Sets the module globals via monkeypatch on the imported module OBJECT (not a
    dotted string path) and reverts after the test. Using the object avoids
    monkeypatch's string-path resolution, which fails ("no attribute 'client'")
    after another test reloads integrations.moonpay.client earlier in the suite.
    No importlib.reload here — a reload is a global, non-reverted mutation that
    leaks across the suite. _is_moonpay_enabled() reads the env live, so setenv
    suffices.
    """
    import integrations.moonpay.client as mp_client

    monkeypatch.setenv("EM_MOONPAY_ENABLED", "true")
    monkeypatch.setattr(mp_client, "MOONPAY_SECRET_KEY", "sk_test_secret_evm_gate")
    monkeypatch.setattr(mp_client, "MOONPAY_PUBLIC_KEY", "pk_test_public_evm_gate")
    monkeypatch.setattr(mp_client, "MOONPAY_WIDGET_BASE_URL", "https://buy.moonpay.com")
    yield


class TestCheckEvmBalanceGate:
    """check_evm_balance_gate — the Base funding gate for publish/assign.

    Mocks get_evm_usdc_balance via unittest.mock.patch (the same pattern the
    Solana balance-gate tests use). A plain monkeypatch.setattr proved
    order-fragile under the full suite in CI; `patch` is robust.
    """

    @pytest.mark.asyncio
    async def test_sufficient_passes(self):
        from integrations.moonpay import balance_gate as gate_mod

        with patch(
            "integrations.evm.balance.get_evm_usdc_balance",
            new=AsyncMock(return_value=Decimal("100")),
        ):
            result = await gate_mod.check_evm_balance_gate(
                "0x1111111111111111111111111111111111111111",
                Decimal("10"),
                network="base",
            )
        assert result.sufficient is True
        assert result.onramp is None
        assert result.shortfall == Decimal("0")

    @pytest.mark.asyncio
    async def test_insufficient_returns_base_onramp(self, _moonpay_enabled):
        from integrations.moonpay import balance_gate as gate_mod

        with patch(
            "integrations.evm.balance.get_evm_usdc_balance",
            new=AsyncMock(return_value=Decimal("1")),
        ):
            result = await gate_mod.check_evm_balance_gate(
                "0x1111111111111111111111111111111111111111",
                Decimal("10"),
                network="base",
            )
        assert result.sufficient is False
        assert result.shortfall == Decimal("9")
        assert result.onramp is not None
        assert result.onramp["currency"] == "usdc_base"
        assert result.onramp["url"].startswith("https://buy.moonpay.com")


class TestH2HTargetExecutorType:
    """PublishH2ATaskRequest.target_executor_type — H2H enablement (Phase 4/5).

    The mobile wizard sends any|human|agent|robot; only 'human' enables H2H.
    The validator must accept all four (so mobile is never rejected) and
    default to 'agent' (historical behavior).
    """

    _BASE = dict(
        title="Entregar paquete",
        instructions="Recoger en X y entregar en Y antes de las 5pm hoy.",
        category="physical_presence",
        bounty_usd=10,
    )

    def test_accepts_all_mobile_values(self):
        from models import PublishH2ATaskRequest

        for tt in ("any", "human", "agent", "robot"):
            r = PublishH2ATaskRequest(**self._BASE, target_executor_type=tt)
            assert r.target_executor_type == tt

    def test_defaults_to_agent(self):
        from models import PublishH2ATaskRequest

        r = PublishH2ATaskRequest(**self._BASE)
        assert r.target_executor_type == "agent"

    def test_rejects_invalid(self):
        from models import PublishH2ATaskRequest

        with pytest.raises(Exception):
            PublishH2ATaskRequest(**self._BASE, target_executor_type="alien")
