"""
Tests for admin fee management endpoints (GET /fees/accrued, POST /fees/sweep).

These endpoints enable batch fee collection: fees accrue in the platform wallet
during task approvals (2-TX flow) and are swept to treasury on demand.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.payments

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DISPATCHER_MODULE = "integrations.x402.payment_dispatcher"


@pytest.fixture
def mock_admin_key():
    """Bypass admin auth for testing."""
    return {"role": "admin", "auth_source": "test", "actor_id": "test-admin"}


@pytest.fixture
def mock_dispatcher():
    """Create a mock PaymentDispatcher with fee methods."""
    dispatcher = MagicMock()
    dispatcher.get_accrued_fees = AsyncMock()
    dispatcher.sweep_fees_to_treasury = AsyncMock()
    return dispatcher


# ---------------------------------------------------------------------------
# Test: GET /admin/fees/accrued
# ---------------------------------------------------------------------------


class TestGetAccruedFees:
    """Tests for GET /api/v1/admin/fees/accrued endpoint."""

    @pytest.mark.asyncio
    async def test_accrued_fees_success(self, mock_dispatcher, mock_admin_key):
        """Should return accrued fee info from dispatcher."""
        mock_dispatcher.get_accrued_fees.return_value = {
            "platform_wallet": "0xPlatform",
            "balance_usdc": 15.50,
            "safety_buffer_usdc": 1.00,
            "sweepable_usdc": 14.50,
            "accrued_from_tasks_usdc": 3.90,
            "treasury_address": "0xTreasury",
            "network": "base",
            "token": "USDC",
        }

        with patch(
            f"{DISPATCHER_MODULE}.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            from api.admin import get_accrued_fees

            result = await get_accrued_fees(
                network="base", token="USDC", admin=mock_admin_key
            )

        assert result["sweepable_usdc"] == 14.50
        assert result["accrued_from_tasks_usdc"] == 3.90
        assert result["balance_usdc"] == 15.50

    @pytest.mark.asyncio
    async def test_accrued_fees_dispatcher_error(self, mock_admin_key):
        """Should return 500 if dispatcher raises exception."""
        bad_dispatcher = MagicMock()
        bad_dispatcher.get_accrued_fees = AsyncMock(
            side_effect=RuntimeError("SDK not initialized")
        )

        from fastapi import HTTPException

        with patch(
            f"{DISPATCHER_MODULE}.get_dispatcher",
            return_value=bad_dispatcher,
        ):
            from api.admin import get_accrued_fees

            with pytest.raises(HTTPException) as exc_info:
                await get_accrued_fees(
                    network="base", token="USDC", admin=mock_admin_key
                )
            assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# Test: POST /admin/fees/sweep
# ---------------------------------------------------------------------------


class TestSweepFees:
    """Tests for POST /api/v1/admin/fees/sweep endpoint."""

    @pytest.mark.asyncio
    async def test_sweep_success(self, mock_dispatcher, mock_admin_key):
        """Should execute sweep and return tx hash."""
        mock_dispatcher.sweep_fees_to_treasury.return_value = {
            "success": True,
            "tx_hash": "0x" + "ab" * 32,
            "amount_swept_usdc": 14.50,
            "balance_before_usdc": 15.50,
            "treasury_address": "0xTreasury",
            "error": None,
        }

        with patch(
            f"{DISPATCHER_MODULE}.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            from api.admin import sweep_fees_to_treasury

            result = await sweep_fees_to_treasury(
                network="base", token="USDC", admin=mock_admin_key
            )

        assert result["success"] is True
        assert result["amount_swept_usdc"] == 14.50
        assert result["tx_hash"] is not None

    @pytest.mark.asyncio
    async def test_sweep_below_minimum(self, mock_dispatcher, mock_admin_key):
        """Should return failure if amount below minimum."""
        mock_dispatcher.sweep_fees_to_treasury.return_value = {
            "success": False,
            "error": "Sweepable amount ($0.05) below minimum ($0.10)",
            "balance_usdc": 1.05,
            "sweepable_usdc": 0.05,
        }

        with patch(
            f"{DISPATCHER_MODULE}.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            from api.admin import sweep_fees_to_treasury

            result = await sweep_fees_to_treasury(
                network="base", token="USDC", admin=mock_admin_key
            )

        assert result["success"] is False
        assert "below minimum" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_sweep_tx_failure(self, mock_dispatcher, mock_admin_key):
        """Should handle TX failure from dispatcher."""
        mock_dispatcher.sweep_fees_to_treasury.return_value = {
            "success": False,
            "tx_hash": None,
            "amount_swept_usdc": 0,
            "error": "Nonce too low",
        }

        with patch(
            f"{DISPATCHER_MODULE}.get_dispatcher",
            return_value=mock_dispatcher,
        ):
            from api.admin import sweep_fees_to_treasury

            result = await sweep_fees_to_treasury(
                network="base", token="USDC", admin=mock_admin_key
            )

        assert result["success"] is False
        assert result["amount_swept_usdc"] == 0
        assert "Nonce too low" in result["error"]
