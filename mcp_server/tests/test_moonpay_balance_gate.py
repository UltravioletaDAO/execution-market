"""Tests for the Solana balance gate + MoonPay on-ramp builder (Phase 4.7).

Covers three modules in isolation:

  - integrations.solana.balance.get_solana_usdc_balance
  - integrations.moonpay.onramp.build_insufficient_funds_onramp
  - integrations.moonpay.balance_gate.check_solana_balance_gate

The tests never touch live Solana RPCs or live MoonPay infrastructure —
the HTTP layer is patched (httpx.AsyncClient.post) and `sign_url()` is
either exercised with deterministic test secrets or monkeypatched.
"""

from __future__ import annotations

import importlib
import sys
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.payments


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_MOONPAY_SECRET = "sk_test_secret_for_balance_gate_unit_tests_only"
_MOONPAY_PUBLIC = "pk_test_public_for_balance_gate_unit_tests_only"


@pytest.fixture
def moonpay_enabled(monkeypatch):
    """Enable MoonPay with deterministic test keys."""
    monkeypatch.setenv("EM_MOONPAY_ENABLED", "true")
    monkeypatch.setenv("MOONPAY_SECRET_KEY", _MOONPAY_SECRET)
    monkeypatch.setenv("MOONPAY_PUBLIC_KEY", _MOONPAY_PUBLIC)
    monkeypatch.setenv("MOONPAY_WIDGET_BASE_URL", "https://buy.moonpay.com")
    # Force reload of moonpay client so it picks up the patched env.
    import integrations.moonpay.client  # noqa: F401

    importlib.reload(sys.modules["integrations.moonpay.client"])
    yield


@pytest.fixture
def moonpay_disabled(monkeypatch):
    """Disable MoonPay master switch."""
    monkeypatch.setenv("EM_MOONPAY_ENABLED", "false")
    yield


@pytest.fixture
def moonpay_misconfigured(monkeypatch):
    """MoonPay enabled but secret key missing."""
    monkeypatch.setenv("EM_MOONPAY_ENABLED", "true")
    monkeypatch.delenv("MOONPAY_SECRET_KEY", raising=False)
    monkeypatch.delenv("MOONPAY_PUBLIC_KEY", raising=False)
    import integrations.moonpay.client  # noqa: F401

    importlib.reload(sys.modules["integrations.moonpay.client"])
    yield


# ---------------------------------------------------------------------------
# get_solana_usdc_balance()
# ---------------------------------------------------------------------------


def _rpc_response(accounts: list[dict]) -> dict:
    """Build a JSON-RPC `getTokenAccountsByOwner` success payload."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"context": {"slot": 1}, "value": accounts},
    }


def _token_account(ui_amount: str) -> dict:
    """Build one token account entry matching jsonParsed shape."""
    return {
        "pubkey": "TokenAccount1111111111111111111111111111111",
        "account": {
            "data": {
                "parsed": {
                    "info": {
                        "tokenAmount": {
                            "uiAmountString": ui_amount,
                            "uiAmount": float(ui_amount),
                            "decimals": 6,
                            "amount": str(int(float(ui_amount) * 1_000_000)),
                        }
                    }
                }
            }
        },
    }


class TestGetSolanaUsdcBalance:
    @pytest.mark.asyncio
    async def test_single_account_returns_balance(self):
        from integrations.solana import balance as mod

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _rpc_response([_token_account("50.5")])

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        bal = await mod.get_solana_usdc_balance(
            wallet="11111111111111111111111111111111", http=mock_client
        )
        assert bal == Decimal("50.5")

    @pytest.mark.asyncio
    async def test_multiple_accounts_sum(self):
        from integrations.solana import balance as mod

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _rpc_response(
            [_token_account("10.25"), _token_account("5.75"), _token_account("1")]
        )

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        bal = await mod.get_solana_usdc_balance(
            wallet="11111111111111111111111111111111", http=mock_client
        )
        assert bal == Decimal("17.00")

    @pytest.mark.asyncio
    async def test_no_accounts_returns_zero(self):
        from integrations.solana import balance as mod

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _rpc_response([])

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        bal = await mod.get_solana_usdc_balance(
            wallet="11111111111111111111111111111111", http=mock_client
        )
        assert bal == Decimal("0")

    @pytest.mark.asyncio
    async def test_rpc_error_returns_zero(self):
        from integrations.solana import balance as mod

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32602, "message": "Invalid params"},
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        bal = await mod.get_solana_usdc_balance(
            wallet="11111111111111111111111111111111", http=mock_client
        )
        assert bal == Decimal("0")

    @pytest.mark.asyncio
    async def test_http_500_returns_zero(self):
        from integrations.solana import balance as mod

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {}

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        bal = await mod.get_solana_usdc_balance(
            wallet="11111111111111111111111111111111", http=mock_client
        )
        assert bal == Decimal("0")

    @pytest.mark.asyncio
    async def test_exception_returns_zero(self):
        from integrations.solana import balance as mod

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=RuntimeError("network down"))

        bal = await mod.get_solana_usdc_balance(
            wallet="11111111111111111111111111111111", http=mock_client
        )
        assert bal == Decimal("0")

    @pytest.mark.asyncio
    async def test_empty_wallet_returns_zero(self):
        from integrations.solana import balance as mod

        bal = await mod.get_solana_usdc_balance(wallet="")
        assert bal == Decimal("0")

    @pytest.mark.asyncio
    async def test_malformed_account_skipped(self):
        from integrations.solana import balance as mod

        bad_entry = {"pubkey": "X", "account": {"data": {"parsed": {}}}}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _rpc_response([bad_entry, _token_account("3.14")])

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        bal = await mod.get_solana_usdc_balance(
            wallet="11111111111111111111111111111111", http=mock_client
        )
        # The malformed entry is skipped; the valid one is counted.
        assert bal == Decimal("3.14")


# ---------------------------------------------------------------------------
# build_insufficient_funds_onramp()
# ---------------------------------------------------------------------------


class TestBuildOnramp:
    def test_disabled_returns_none(self, moonpay_disabled):
        from integrations.moonpay.onramp import build_insufficient_funds_onramp

        result = build_insufficient_funds_onramp(
            wallet="So1anaWa11et", qty_needed=Decimal("5")
        )
        assert result is None

    def test_misconfigured_returns_none(self, moonpay_misconfigured):
        from integrations.moonpay.onramp import build_insufficient_funds_onramp

        result = build_insufficient_funds_onramp(
            wallet="So1anaWa11et", qty_needed=Decimal("5")
        )
        assert result is None

    def test_floors_to_min_buy(self, moonpay_enabled):
        from integrations.moonpay.onramp import build_insufficient_funds_onramp

        result = build_insufficient_funds_onramp(
            wallet="So1anaWa11et", qty_needed=Decimal("5")
        )
        assert result is not None
        # MoonPay $20 USDC minimum is enforced.
        assert Decimal(result["qty_needed"]) == Decimal("20.00")
        assert result["currency"] == "usdc_sol"
        assert "url" in result and result["url"].startswith("https://buy.moonpay.com")
        assert "signature" in result and len(result["signature"]) > 0

    def test_above_min_buy_passes_through(self, moonpay_enabled):
        from integrations.moonpay.onramp import build_insufficient_funds_onramp

        result = build_insufficient_funds_onramp(
            wallet="So1anaWa11et", qty_needed=Decimal("100")
        )
        assert result is not None
        assert Decimal(result["qty_needed"]) == Decimal("100.00")

    def test_zero_qty_uses_min_buy(self, moonpay_enabled):
        from integrations.moonpay.onramp import build_insufficient_funds_onramp

        result = build_insufficient_funds_onramp(
            wallet="So1anaWa11et", qty_needed=Decimal("0")
        )
        assert result is not None
        assert Decimal(result["qty_needed"]) == Decimal("20.00")

    def test_external_customer_id_in_signed_url(self, moonpay_enabled):
        from integrations.moonpay.onramp import build_insufficient_funds_onramp

        result = build_insufficient_funds_onramp(
            wallet="So1anaWa11et",
            qty_needed=Decimal("25"),
            external_customer_id="executor-uuid-1234",
        )
        assert result is not None
        # externalCustomerId is in the signed query string.
        assert "externalCustomerId" in result["url"]


# ---------------------------------------------------------------------------
# check_solana_balance_gate()
# ---------------------------------------------------------------------------


class TestBalanceGate:
    @pytest.mark.asyncio
    async def test_sufficient_balance_passes(self, moonpay_enabled):
        from integrations.moonpay import balance_gate as gate_mod

        with patch(
            "integrations.solana.balance.get_solana_usdc_balance",
            new=AsyncMock(return_value=Decimal("100")),
        ):
            result = await gate_mod.check_solana_balance_gate(
                wallet="So1anaWa11et",
                required_usdc=Decimal("10"),
            )
        assert result.sufficient is True
        assert result.balance == Decimal("100")
        assert result.shortfall == Decimal("0")
        assert result.onramp is None

    @pytest.mark.asyncio
    async def test_insufficient_balance_with_onramp(self, moonpay_enabled):
        from integrations.moonpay import balance_gate as gate_mod

        with patch(
            "integrations.solana.balance.get_solana_usdc_balance",
            new=AsyncMock(return_value=Decimal("3")),
        ):
            result = await gate_mod.check_solana_balance_gate(
                wallet="So1anaWa11et",
                required_usdc=Decimal("10"),
            )
        assert result.sufficient is False
        assert result.balance == Decimal("3")
        assert result.shortfall == Decimal("7")
        assert result.onramp is not None
        assert result.onramp["currency"] == "usdc_sol"
        # MoonPay $20 minimum lifts qty_needed even though shortfall is $7.
        assert Decimal(result.onramp["qty_needed"]) == Decimal("20.00")

    @pytest.mark.asyncio
    async def test_insufficient_balance_moonpay_disabled(self, moonpay_disabled):
        from integrations.moonpay import balance_gate as gate_mod

        with patch(
            "integrations.solana.balance.get_solana_usdc_balance",
            new=AsyncMock(return_value=Decimal("3")),
        ):
            result = await gate_mod.check_solana_balance_gate(
                wallet="So1anaWa11et",
                required_usdc=Decimal("10"),
            )
        assert result.sufficient is False
        assert result.balance == Decimal("3")
        assert result.shortfall == Decimal("7")
        assert result.onramp is None

    @pytest.mark.asyncio
    async def test_zero_balance(self, moonpay_enabled):
        from integrations.moonpay import balance_gate as gate_mod

        with patch(
            "integrations.solana.balance.get_solana_usdc_balance",
            new=AsyncMock(return_value=Decimal("0")),
        ):
            result = await gate_mod.check_solana_balance_gate(
                wallet="So1anaWa11et",
                required_usdc=Decimal("0.10"),
            )
        assert result.sufficient is False
        assert result.balance == Decimal("0")
        assert result.shortfall == Decimal("0.10")
        # MoonPay onramp is built even for tiny shortfalls (floors to $20).
        assert result.onramp is not None
        assert Decimal(result.onramp["qty_needed"]) == Decimal("20.00")

    @pytest.mark.asyncio
    async def test_exact_balance_passes(self, moonpay_enabled):
        from integrations.moonpay import balance_gate as gate_mod

        with patch(
            "integrations.solana.balance.get_solana_usdc_balance",
            new=AsyncMock(return_value=Decimal("10")),
        ):
            result = await gate_mod.check_solana_balance_gate(
                wallet="So1anaWa11et",
                required_usdc=Decimal("10"),
            )
        assert result.sufficient is True
        assert result.onramp is None

    @pytest.mark.asyncio
    async def test_external_customer_id_forwarded(self, moonpay_enabled):
        from integrations.moonpay import balance_gate as gate_mod

        with patch(
            "integrations.solana.balance.get_solana_usdc_balance",
            new=AsyncMock(return_value=Decimal("0")),
        ):
            result = await gate_mod.check_solana_balance_gate(
                wallet="So1anaWa11et",
                required_usdc=Decimal("5"),
                external_customer_id="exec-42",
            )
        assert result.onramp is not None
        assert "externalCustomerId" in result.onramp["url"]
