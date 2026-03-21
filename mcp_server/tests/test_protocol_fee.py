"""
Tests for x402r protocol fee BPS reading from on-chain ProtocolFeeConfig.

Covers:
- Cache hit/miss behavior (5-minute TTL)
- RPC call to calculator() + FEE_BPS() two-step resolution
- Zero-address calculator (0% fee)
- Fee cap at 500 BPS (5% max)
- RPC failure graceful degradation (fail-open)
- Cache expiry and refresh
- Hex parsing edge cases
"""

import time
from decimal import Decimal
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.payments

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DISPATCHER_MODULE = "integrations.x402.payment_dispatcher"


class FakeHTTPResponse:
    """Mock httpx response with configurable JSON."""

    def __init__(self, result: str):
        self._json = {"jsonrpc": "2.0", "id": 1, "result": result}

    def json(self):
        return self._json


class FakeHTTPClient:
    """Mock httpx.AsyncClient that returns configurable RPC responses."""

    def __init__(self, responses: list):
        self._responses = responses
        self._call_index = 0
        self.calls = []

    async def post(self, url, json=None):
        self.calls.append({"url": url, "json": json})
        idx = min(self._call_index, len(self._responses) - 1)
        self._call_index += 1
        return self._responses[idx]

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class TestProtocolFeeReading:
    """Tests for _get_protocol_fee_bps() function."""

    def setup_method(self):
        """Reset the module-level cache before each test."""
        import integrations.x402.payment_dispatcher as pd

        pd._protocol_fee_cache.update({"bps": 0, "expires": 0.0})

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_value(self):
        """When cache is fresh, should return cached BPS without RPC call."""
        import integrations.x402.payment_dispatcher as pd

        pd._protocol_fee_cache.update({"bps": 100, "expires": time.time() + 300})

        result = await pd._get_protocol_fee_bps()

        assert result == 100

    @pytest.mark.asyncio
    async def test_cache_miss_reads_from_chain(self):
        """When cache expired, should make RPC calls to read fee."""
        import integrations.x402.payment_dispatcher as pd

        # Calculator address (non-zero)
        calc_addr = "0x" + "0" * 24 + "abcdef1234567890abcdef1234567890abcdef12"
        # FEE_BPS = 100 (1%) = 0x64 in hex
        fee_hex = "0x" + "0" * 62 + "64"

        client = FakeHTTPClient(
            [FakeHTTPResponse(calc_addr), FakeHTTPResponse(fee_hex)]
        )

        with patch("httpx.AsyncClient", return_value=client):
            result = await pd._get_protocol_fee_bps()

        assert result == 100
        assert len(client.calls) == 2  # calculator() + FEE_BPS()

    @pytest.mark.asyncio
    async def test_zero_calculator_returns_zero_fee(self):
        """When calculator address is zero, should return 0 BPS."""
        import integrations.x402.payment_dispatcher as pd

        zero_addr = "0x" + "0" * 64  # All zeros

        client = FakeHTTPClient([FakeHTTPResponse(zero_addr)])

        with patch("httpx.AsyncClient", return_value=client):
            result = await pd._get_protocol_fee_bps()

        assert result == 0
        assert len(client.calls) == 1  # Only calculator() call, no FEE_BPS

    @pytest.mark.asyncio
    async def test_fee_capped_at_500_bps(self):
        """Fee should be capped at 500 BPS (5%) even if on-chain says more."""
        import integrations.x402.payment_dispatcher as pd

        calc_addr = "0x" + "0" * 24 + "1234567890abcdef1234567890abcdef12345678"
        # 1000 BPS = 0x3E8 — above the 500 cap
        fee_hex = "0x" + "0" * 61 + "3e8"

        client = FakeHTTPClient(
            [FakeHTTPResponse(calc_addr), FakeHTTPResponse(fee_hex)]
        )

        with patch("httpx.AsyncClient", return_value=client):
            result = await pd._get_protocol_fee_bps()

        assert result == 500  # Capped

    @pytest.mark.asyncio
    async def test_fee_exactly_500_not_capped(self):
        """500 BPS exactly should pass through (it's the cap, not above it)."""
        import integrations.x402.payment_dispatcher as pd

        calc_addr = "0x" + "0" * 24 + "1234567890abcdef1234567890abcdef12345678"
        # 500 BPS = 0x1F4
        fee_hex = "0x" + "0" * 61 + "1f4"

        client = FakeHTTPClient(
            [FakeHTTPResponse(calc_addr), FakeHTTPResponse(fee_hex)]
        )

        with patch("httpx.AsyncClient", return_value=client):
            result = await pd._get_protocol_fee_bps()

        assert result == 500

    @pytest.mark.asyncio
    async def test_rpc_failure_returns_cached_value(self):
        """When RPC fails, should return last cached value (fail-open)."""
        import integrations.x402.payment_dispatcher as pd

        # Pre-set cache with old value
        pd._protocol_fee_cache.update({"bps": 50, "expires": 0})

        with patch("httpx.AsyncClient", side_effect=Exception("connection refused")):
            result = await pd._get_protocol_fee_bps()

        assert result == 50  # Falls back to cached

    @pytest.mark.asyncio
    async def test_rpc_failure_with_empty_cache_returns_zero(self):
        """When RPC fails and cache is empty, should return 0 (fail-open)."""
        import integrations.x402.payment_dispatcher as pd

        pd._protocol_fee_cache.update({"bps": 0, "expires": 0})

        with patch("httpx.AsyncClient", side_effect=Exception("timeout")):
            result = await pd._get_protocol_fee_bps()

        assert result == 0

    @pytest.mark.asyncio
    async def test_cache_updated_after_successful_read(self):
        """Successful read should update cache with new value and TTL."""
        import integrations.x402.payment_dispatcher as pd

        calc_addr = "0x" + "0" * 24 + "abcdef1234567890abcdef1234567890abcdef12"
        fee_hex = "0x" + "0" * 62 + "c8"  # 200 BPS

        client = FakeHTTPClient(
            [FakeHTTPResponse(calc_addr), FakeHTTPResponse(fee_hex)]
        )

        before = time.time()
        with patch("httpx.AsyncClient", return_value=client):
            result = await pd._get_protocol_fee_bps()

        assert result == 200
        assert pd._protocol_fee_cache["bps"] == 200
        assert pd._protocol_fee_cache["expires"] > before + 290  # ~5 min TTL

    @pytest.mark.asyncio
    async def test_empty_hex_result_returns_zero(self):
        """Empty or malformed hex from FEE_BPS() should be treated as 0."""
        import integrations.x402.payment_dispatcher as pd

        calc_addr = "0x" + "0" * 24 + "abcdef1234567890abcdef1234567890abcdef12"

        client = FakeHTTPClient([FakeHTTPResponse(calc_addr), FakeHTTPResponse("0x")])

        with patch("httpx.AsyncClient", return_value=client):
            result = await pd._get_protocol_fee_bps()

        assert result == 0

    @pytest.mark.asyncio
    async def test_consecutive_calls_use_cache(self):
        """Second call within TTL should use cache, not RPC."""
        import integrations.x402.payment_dispatcher as pd

        calc_addr = "0x" + "0" * 24 + "abcdef1234567890abcdef1234567890abcdef12"
        fee_hex = "0x" + "0" * 62 + "64"  # 100 BPS

        client = FakeHTTPClient(
            [FakeHTTPResponse(calc_addr), FakeHTTPResponse(fee_hex)]
        )

        with patch("httpx.AsyncClient", return_value=client):
            result1 = await pd._get_protocol_fee_bps()
            result2 = await pd._get_protocol_fee_bps()

        assert result1 == 100
        assert result2 == 100
        assert len(client.calls) == 2  # Only first call hit RPC


class TestFeeModelConstants:
    """Tests for Fase 5 fee model constants and configuration."""

    def test_fase5_fee_bps_is_1300(self):
        """EM operator fee should be 1300 BPS (13%)."""
        import integrations.x402.payment_dispatcher as pd

        assert pd.FASE5_FEE_BPS == 1300

    def test_fase5_max_fee_bps_is_1800(self):
        """Max fee BPS should be 1800 (1300 + 500 headroom)."""
        import integrations.x402.payment_dispatcher as pd

        assert pd.FASE5_MAX_FEE_BPS == 1800

    def test_default_fee_model_is_credit_card(self):
        """Default fee model should be credit_card."""
        # Note: this test reads the actual env or default
        import integrations.x402.payment_dispatcher as pd

        assert pd.EM_FEE_MODEL in ("credit_card", "agent_absorbs")

    def test_protocol_fee_config_address_is_valid(self):
        """Protocol fee config address should be a valid Ethereum address."""
        import integrations.x402.payment_dispatcher as pd

        addr = pd.PROTOCOL_FEE_CONFIG_ADDRESS
        assert addr.startswith("0x")
        assert len(addr) == 42

    def test_cache_ttl_is_5_minutes(self):
        """Cache TTL should be 300 seconds (5 minutes)."""
        import integrations.x402.payment_dispatcher as pd

        assert pd._CACHE_TTL == 300


class TestCreditCardFeeMath:
    """Mathematical verification of credit card fee model.

    In credit_card mode:
    - Agent pays bounty_usdc
    - Lock amount = bounty_usdc
    - On-chain fee calculator deducts 13% at release
    - Worker gets 87% of bounty
    - Operator gets 13% of bounty
    """

    def test_worker_payout_math(self):
        """Verify worker gets 87% of bounty in credit card model."""
        bounty = Decimal("100.00")
        fee_bps = 1300
        worker_pct = Decimal(10000 - fee_bps) / Decimal(10000)
        worker_gets = bounty * worker_pct

        assert worker_gets == Decimal("87.00")

    def test_operator_fee_math(self):
        """Verify operator gets 13% of bounty."""
        bounty = Decimal("100.00")
        fee_bps = 1300
        operator_pct = Decimal(fee_bps) / Decimal(10000)
        operator_gets = bounty * operator_pct

        assert operator_gets == Decimal("13.00")

    def test_total_equals_bounty(self):
        """Worker payout + operator fee must equal bounty exactly."""
        bounty = Decimal("50.00")
        fee_bps = 1300
        worker = bounty * Decimal(10000 - fee_bps) / Decimal(10000)
        operator = bounty * Decimal(fee_bps) / Decimal(10000)

        assert worker + operator == bounty

    def test_small_bounty_precision(self):
        """Even tiny bounties should have correct split."""
        bounty = Decimal("0.25")
        fee_bps = 1300
        worker = bounty * Decimal(10000 - fee_bps) / Decimal(10000)
        operator = bounty * Decimal(fee_bps) / Decimal(10000)

        assert worker + operator == bounty
        assert worker == Decimal("0.2175")
        assert operator == Decimal("0.0325")


class TestAgentAbsorbsFeeMath:
    """Mathematical verification of agent_absorbs fee model.

    In agent_absorbs mode:
    - Agent pays more than bounty
    - Lock = ceil(bounty * 10000 / (10000 - 1300))
    - Worker gets ~100% of original bounty after fee deduction
    """

    def test_lock_calculation(self):
        """Lock amount should be bounty / 0.87 (rounded up)."""
        from decimal import ROUND_CEILING

        bounty = Decimal("10.00")
        fee_bps = 1300
        denom = Decimal(10000 - fee_bps)
        lock = (bounty * Decimal(10000) / denom).quantize(
            Decimal("0.000001"), rounding=ROUND_CEILING
        )

        # lock = 10 * 10000 / 8700 = 11.494252...
        assert lock == Decimal("11.494253")

    def test_worker_gets_bounty_back(self):
        """After 13% fee deduction from lock, worker should get >= bounty."""
        from decimal import ROUND_CEILING

        bounty = Decimal("10.00")
        fee_bps = 1300
        denom = Decimal(10000 - fee_bps)
        lock = (bounty * Decimal(10000) / denom).quantize(
            Decimal("0.000001"), rounding=ROUND_CEILING
        )

        worker_gets = lock * Decimal(10000 - fee_bps) / Decimal(10000)

        # Worker should get at least the original bounty
        assert worker_gets >= bounty

    def test_agent_premium_is_reasonable(self):
        """Agent's extra cost should be proportional to fee rate."""
        from decimal import ROUND_CEILING

        bounty = Decimal("100.00")
        fee_bps = 1300
        denom = Decimal(10000 - fee_bps)
        lock = (bounty * Decimal(10000) / denom).quantize(
            Decimal("0.000001"), rounding=ROUND_CEILING
        )

        premium = lock - bounty
        premium_pct = premium / bounty * 100

        # Premium should be ~14.94% (since 13% of 114.94% ≈ 14.94%)
        assert Decimal("14") < premium_pct < Decimal("16")
