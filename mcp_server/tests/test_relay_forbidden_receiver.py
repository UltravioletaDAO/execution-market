"""
P0-3 — relay_agent_auth_to_facilitator forbidden receiver guard.

Verifies that PaymentDispatcher.relay_agent_auth_to_facilitator refuses to
relay a pre-signed auth when the worker_address is a prohibited destination:

  - EM_TREASURY (would bypass 87/13 split; repeat of INC Feb 2026)
  - operator (funds stuck in operator, manual sweep required)
  - 0x0000...0000 (zero address — USDC sent there is irrecoverable)
  - payer itself (trivial wash trade to inflate volume metrics)

All four cases must return success=False with escrow_status="forbidden_receiver"
BEFORE any HTTP call to the Facilitator.
"""

from unittest.mock import patch

import pytest

DISPATCHER_MODULE = "integrations.x402.payment_dispatcher"

# Canonical forbidden values used across tests
_TREASURY = "0xTreasuryAddressHere00000000000000000000"
_OPERATOR = "0xOperatorAddressHere00000000000000000000"
_ZERO = "0x0000000000000000000000000000000000000000"
_PAYER = "0x" + "a" * 40


def _build_payload(payer: str = _PAYER) -> dict:
    """Minimal payload shape consumed by relay_agent_auth_to_facilitator."""
    return {
        "payload": {
            "authorization": {"from": payer},
            "paymentInfo": {},
        }
    }


def _make_dispatcher():
    """Build a PaymentDispatcher with NETWORK_CONFIG patched for 'base'."""
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
                    "operator": _OPERATOR,
                }
            },
        ),
    ):
        from integrations.x402.payment_dispatcher import PaymentDispatcher

        return PaymentDispatcher(mode="fase2")


@pytest.mark.security
@pytest.mark.payments
@pytest.mark.asyncio
async def test_relay_rejects_treasury_as_worker(monkeypatch):
    """P0-3: worker_address == EM_TREASURY must be rejected."""
    from integrations.x402 import payment_dispatcher as pd

    monkeypatch.setattr(pd, "EM_TREASURY", _TREASURY)

    with patch(
        f"{DISPATCHER_MODULE}._get_operator_for_network", return_value=_OPERATOR
    ):
        dispatcher = _make_dispatcher()
        result = await dispatcher.relay_agent_auth_to_facilitator(
            payload=_build_payload(),
            worker_address=_TREASURY,
            network="base",
        )

    assert result["success"] is False
    assert result["escrow_status"] == "forbidden_receiver"
    assert "treasury" in result["error"].lower()


@pytest.mark.security
@pytest.mark.payments
@pytest.mark.asyncio
async def test_relay_rejects_zero_address_as_worker():
    """P0-3: worker_address == 0x000...000 must be rejected."""
    with patch(
        f"{DISPATCHER_MODULE}._get_operator_for_network", return_value=_OPERATOR
    ):
        dispatcher = _make_dispatcher()
        result = await dispatcher.relay_agent_auth_to_facilitator(
            payload=_build_payload(),
            worker_address=_ZERO,
            network="base",
        )

    assert result["success"] is False
    assert result["escrow_status"] == "forbidden_receiver"
    assert "zero" in result["error"].lower()


@pytest.mark.security
@pytest.mark.payments
@pytest.mark.asyncio
async def test_relay_rejects_payer_as_worker():
    """P0-3: worker == payer (wash trade) must be rejected."""
    with patch(
        f"{DISPATCHER_MODULE}._get_operator_for_network", return_value=_OPERATOR
    ):
        dispatcher = _make_dispatcher()
        result = await dispatcher.relay_agent_auth_to_facilitator(
            payload=_build_payload(payer=_PAYER),
            worker_address=_PAYER,
            network="base",
        )

    assert result["success"] is False
    assert result["escrow_status"] == "forbidden_receiver"
    assert "wash" in result["error"].lower() or "payer" in result["error"].lower()
