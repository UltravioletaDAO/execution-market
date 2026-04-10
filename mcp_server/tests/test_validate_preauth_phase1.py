"""
Tests for SC-001 hardening of validate_agent_preauth (Phase 1 Security).

Validates that pre-auth payloads are checked against NETWORK_CONFIG:
  - Operator address must match the network's registered operator
  - Token address must be in the network's token allowlist
  - authorization.from must match the authenticated agent wallet
  - authorization.to must match the network's tokenCollector
  - paymentInfo.maxAmount must match the expected task total
  - Unknown networks are rejected
"""

import json
import os
import copy
import pytest
from decimal import Decimal
from unittest.mock import patch

DISPATCHER_MODULE = "integrations.x402.payment_dispatcher"

# ── Test NETWORK_CONFIG (mirrors production structure) ─────────
TEST_NETWORK_CONFIG = {
    "base": {
        "chain_id": 8453,
        "network_type": "evm",
        "rpc_url": "https://mainnet.base.org",
        "tokens": {
            "USDC": {
                "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "name": "USD Coin",
                "version": "2",
                "decimals": 6,
            },
            "EURC": {
                "address": "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42",
                "name": "EURC",
                "version": "2",
                "decimals": 6,
            },
        },
        "escrow": "0xb9488351E48b23D798f24e8174514F28B741Eb4f",
        "factory": "0x3D0837fF8Ea36F417261577b9BA568400A840260",
        "operator": "0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb",
        "x402r_infra": {
            "tokenCollector": "0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8",
        },
    },
}

VALID_AGENT_WALLET = "0xAgentWallet1234567890abcdef1234567890abcdef"
VALID_OPERATOR = "0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb"
VALID_TOKEN = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
VALID_COLLECTOR = "0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8"
VALID_AMOUNT = "5000000"

VALID_PAYLOAD = {
    "x402Version": 2,
    "scheme": "escrow",
    "payload": {
        "authorization": {
            "from": VALID_AGENT_WALLET,
            "to": VALID_COLLECTOR,
            "value": VALID_AMOUNT,
            "validAfter": "0",
            "validBefore": "1711843200",
            "nonce": "0x" + "ab" * 32,
        },
        "signature": "0x" + "cc" * 65,
        "paymentInfo": {
            "operator": VALID_OPERATOR,
            "receiver": "",
            "token": VALID_TOKEN,
            "maxAmount": VALID_AMOUNT,
        },
    },
}


def _make_dispatcher():
    """Create a PaymentDispatcher with TEST_NETWORK_CONFIG."""
    with (
        patch(f"{DISPATCHER_MODULE}.ADVANCED_ESCROW_AVAILABLE", False),
        patch(f"{DISPATCHER_MODULE}.FASE2_SDK_AVAILABLE", True),
        patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", True),
        patch(f"{DISPATCHER_MODULE}.NETWORK_CONFIG", TEST_NETWORK_CONFIG),
        patch(f"{DISPATCHER_MODULE}.PLATFORM_FEE_PERCENT", Decimal("0.13")),
        patch(
            f"{DISPATCHER_MODULE}._get_platform_address",
            return_value="0xPlatformAddr",
        ),
        patch.dict(os.environ, {"WALLET_PRIVATE_KEY": "0x" + "aa" * 32}),
    ):
        from integrations.x402.payment_dispatcher import PaymentDispatcher

        d = PaymentDispatcher(mode="fase2")
        d.escrow_mode = "direct_release"
        return d


class TestSC001RejectsUnknownOperator:
    """SC-001: paymentInfo.operator must match NETWORK_CONFIG[network].operator."""

    def test_rejects_unknown_operator(self):
        d = _make_dispatcher()
        payload = copy.deepcopy(VALID_PAYLOAD)
        payload["payload"]["paymentInfo"]["operator"] = (
            "0xMaliciousOperator000000000000000000000000"
        )
        with pytest.raises(ValueError, match="paymentInfo.operator must be"):
            d.validate_agent_preauth(
                json.dumps(payload),
                network="base",
                expected_payer=VALID_AGENT_WALLET,
            )


class TestSC001RejectsUnknownToken:
    """SC-001: paymentInfo.token must be in NETWORK_CONFIG[network].tokens allowlist."""

    def test_rejects_unknown_token(self):
        d = _make_dispatcher()
        payload = copy.deepcopy(VALID_PAYLOAD)
        payload["payload"]["paymentInfo"]["token"] = (
            "0xMaliciousToken0000000000000000000000000000"
        )
        with pytest.raises(ValueError, match="not in allowlist"):
            d.validate_agent_preauth(
                json.dumps(payload),
                network="base",
                expected_payer=VALID_AGENT_WALLET,
            )


class TestSC001RejectsAmountMismatch:
    """SC-001: paymentInfo.maxAmount must match expected total_required."""

    def test_rejects_amount_mismatch(self):
        d = _make_dispatcher()
        payload = copy.deepcopy(VALID_PAYLOAD)
        # Attacker tries to lock less than the bounty
        payload["payload"]["paymentInfo"]["maxAmount"] = "1000000"
        with pytest.raises(ValueError, match="does not match expected"):
            d.validate_agent_preauth(
                json.dumps(payload),
                network="base",
                expected_payer=VALID_AGENT_WALLET,
                expected_amount_atomic=VALID_AMOUNT,
            )


class TestSC001RejectsWrongPayer:
    """SC-001: authorization.from must match the authenticated agent wallet."""

    def test_rejects_wrong_payer(self):
        d = _make_dispatcher()
        payload = copy.deepcopy(VALID_PAYLOAD)
        payload["payload"]["authorization"]["from"] = (
            "0xAttackerWallet000000000000000000000000000"
        )
        with pytest.raises(
            ValueError, match="must match the authenticated agent wallet"
        ):
            d.validate_agent_preauth(
                json.dumps(payload),
                network="base",
                expected_payer=VALID_AGENT_WALLET,
            )


class TestSC001RejectsWrongTokenCollector:
    """SC-001: authorization.to must match NETWORK_CONFIG tokenCollector."""

    def test_rejects_wrong_collector(self):
        d = _make_dispatcher()
        payload = copy.deepcopy(VALID_PAYLOAD)
        payload["payload"]["authorization"]["to"] = (
            "0xMaliciousCollector0000000000000000000000"
        )
        with pytest.raises(ValueError, match="authorization.to must be tokenCollector"):
            d.validate_agent_preauth(
                json.dumps(payload),
                network="base",
                expected_payer=VALID_AGENT_WALLET,
            )


class TestSC001RejectsUnknownNetwork:
    """SC-001: Unknown network not in NETWORK_CONFIG is rejected."""

    def test_rejects_unknown_network(self):
        d = _make_dispatcher()
        payload = copy.deepcopy(VALID_PAYLOAD)
        with pytest.raises(ValueError, match="Unknown payment network"):
            d.validate_agent_preauth(
                json.dumps(payload),
                network="nonexistent_chain",
                expected_payer=VALID_AGENT_WALLET,
            )


class TestSC001AcceptsValidPreauth:
    """SC-001: A fully valid payload with all checks passes validation."""

    def test_accepts_valid_preauth(self):
        d = _make_dispatcher()
        payload = copy.deepcopy(VALID_PAYLOAD)
        result = d.validate_agent_preauth(
            json.dumps(payload),
            network="base",
            expected_payer=VALID_AGENT_WALLET,
            expected_amount_atomic=VALID_AMOUNT,
        )
        assert result["x402Version"] == 2
        assert result["payload"]["authorization"]["from"] == VALID_AGENT_WALLET
        assert result["payload"]["paymentInfo"]["operator"] == VALID_OPERATOR
        assert result["payload"]["paymentInfo"]["token"] == VALID_TOKEN

    def test_case_insensitive_address_matching(self):
        """Addresses should be compared case-insensitively (EIP-55 checksum)."""
        d = _make_dispatcher()
        payload = copy.deepcopy(VALID_PAYLOAD)
        # Use uppercase versions of addresses
        payload["payload"]["paymentInfo"]["operator"] = VALID_OPERATOR.upper()
        payload["payload"]["paymentInfo"]["token"] = VALID_TOKEN.upper()
        payload["payload"]["authorization"]["to"] = VALID_COLLECTOR.upper()
        payload["payload"]["authorization"]["from"] = VALID_AGENT_WALLET.upper()
        result = d.validate_agent_preauth(
            json.dumps(payload),
            network="base",
            expected_payer=VALID_AGENT_WALLET.lower(),
            expected_amount_atomic=VALID_AMOUNT,
        )
        assert result is not None

    def test_backward_compat_no_network(self):
        """Without network/payer args, only structural validation runs (backward compat)."""
        d = _make_dispatcher()
        payload = copy.deepcopy(VALID_PAYLOAD)
        # Use completely wrong addresses — should still pass without network param
        payload["payload"]["paymentInfo"]["operator"] = (
            "0x0000000000000000000000000000000000000000"
        )
        result = d.validate_agent_preauth(json.dumps(payload))
        assert result["x402Version"] == 2

    def test_accepts_eurc_token(self):
        """EURC is also in the Base allowlist and should be accepted."""
        d = _make_dispatcher()
        payload = copy.deepcopy(VALID_PAYLOAD)
        payload["payload"]["paymentInfo"]["token"] = (
            "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42"
        )
        result = d.validate_agent_preauth(
            json.dumps(payload),
            network="base",
            expected_payer=VALID_AGENT_WALLET,
        )
        assert result is not None
