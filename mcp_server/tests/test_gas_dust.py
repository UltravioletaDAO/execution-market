"""
Tests for the gas dust module.

Gas dust funds workers with tiny ETH for on-chain reputation TX gas.
Anti-farming: one per wallet, monthly budget cap, rate limit.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.payments

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFundWorkerGasDust:
    """Tests for fund_worker_gas_dust()."""

    @pytest.mark.asyncio
    async def test_fund_happy_path(self):
        """Successful funding returns tx_hash and updates DB."""
        mock_client = MagicMock()
        # Not already funded
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"gas_dust_funded_at": None}]
        )
        # Insert event
        mock_client.table.return_value.insert.return_value.execute.return_value = (
            MagicMock(data=[{"id": "event-1"}])
        )
        # Update executor + event
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with (
            patch("integrations.gas_dust.db") as mock_db,
            patch(
                "integrations.gas_dust._send_eth_dust",
                new_callable=AsyncMock,
                return_value="0xabc123",
            ),
            patch(
                "integrations.gas_dust.check_rate_limit",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "integrations.gas_dust.check_gas_dust_budget",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            mock_db.get_client.return_value = mock_client

            from integrations.gas_dust import fund_worker_gas_dust

            result = await fund_worker_gas_dust(
                wallet_address="0x1234567890abcdef1234567890abcdef12345678",
                executor_id="exec-1",
            )

        assert result == "0xabc123"

    @pytest.mark.asyncio
    async def test_skip_already_funded(self):
        """Skip if worker already received gas dust."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"gas_dust_funded_at": "2026-02-14T00:00:00Z"}]
        )

        with patch("integrations.gas_dust.db") as mock_db:
            mock_db.get_client.return_value = mock_client

            from integrations.gas_dust import fund_worker_gas_dust

            result = await fund_worker_gas_dust(
                wallet_address="0x1234567890abcdef1234567890abcdef12345678",
                executor_id="exec-1",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_skip_rate_limited(self):
        """Skip if rate limit exceeded."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"gas_dust_funded_at": None}]
        )

        with (
            patch("integrations.gas_dust.db") as mock_db,
            patch(
                "integrations.gas_dust.check_rate_limit",
                new_callable=AsyncMock,
                return_value=False,
            ),
        ):
            mock_db.get_client.return_value = mock_client

            from integrations.gas_dust import fund_worker_gas_dust

            result = await fund_worker_gas_dust(
                wallet_address="0x1234567890abcdef1234567890abcdef12345678",
                executor_id="exec-1",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_skip_budget_exceeded(self):
        """Skip if monthly budget exceeded."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"gas_dust_funded_at": None}]
        )

        with (
            patch("integrations.gas_dust.db") as mock_db,
            patch(
                "integrations.gas_dust.check_rate_limit",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "integrations.gas_dust.check_gas_dust_budget",
                new_callable=AsyncMock,
                return_value=False,
            ),
        ):
            mock_db.get_client.return_value = mock_client

            from integrations.gas_dust import fund_worker_gas_dust

            result = await fund_worker_gas_dust(
                wallet_address="0x1234567890abcdef1234567890abcdef12345678",
                executor_id="exec-1",
            )

        assert result is None


class TestCheckBudget:
    """Tests for check_gas_dust_budget()."""

    @pytest.mark.asyncio
    async def test_budget_has_capacity(self):
        """Returns True when budget has capacity."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
            data=[{"amount_eth": 0.0001}, {"amount_eth": 0.0001}]
        )

        with patch("integrations.gas_dust.db") as mock_db:
            mock_db.get_client.return_value = mock_client

            from integrations.gas_dust import check_gas_dust_budget

            result = await check_gas_dust_budget()

        assert result is True

    @pytest.mark.asyncio
    async def test_budget_exhausted(self):
        """Returns False when budget is used up."""
        # 500 entries * 0.0001 = 0.05 ETH (matches default budget)
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
            data=[{"amount_eth": 0.0001}] * 500
        )

        with patch("integrations.gas_dust.db") as mock_db:
            mock_db.get_client.return_value = mock_client

            from integrations.gas_dust import check_gas_dust_budget

            result = await check_gas_dust_budget()

        assert result is False
