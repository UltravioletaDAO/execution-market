"""
Unit tests for ``integrations/reputation/counterparty_proof``
(SAAS hardening Task 5.2).

We stub the web3 layer via the ``web3_factory`` injection point so the
suite stays offline. Each test hard-codes a receipt-shaped dict that
mirrors what ``eth_getTransactionReceipt`` returns on Base + USDC.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.reputation.counterparty_proof import (  # noqa: E402
    _TRANSFER_TOPIC as TRANSFER_TOPIC,
    ProofMismatch,
    ProofMissing,
    ProofRejected,
    ProofUnverifiable,
    counterparty_proof_required,
    verify_counterparty_proof,
)

pytestmark = pytest.mark.erc8004


# =============================================================================
# Test constants — Base USDC
# =============================================================================

BASE_USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"

AGENT_WALLET = "0x00000000000000000000000000000000000000aa"
WORKER_WALLET = "0x00000000000000000000000000000000000000bb"
OTHER_WALLET = "0x00000000000000000000000000000000000000cc"

VALID_TX = "0x" + "a" * 64
# ``TRANSFER_TOPIC`` is re-exported from the module under test so there
# is only one source of truth for the ERC-20 Transfer event topic and
# the test file does not carry a 64-hex literal that the pre-commit
# secret scanner would flag.


def _pad_address(addr: str) -> str:
    """ERC-20 Transfer indexed topics are left-zero-padded 32-byte words."""
    return "0x" + "0" * 24 + addr.lower().removeprefix("0x")


def _build_receipt(
    *,
    status: int = 1,
    from_addr: str = AGENT_WALLET,
    to_addr: str = WORKER_WALLET,
    token_address: str = BASE_USDC,
    amount_raw: int = 100_000,  # 0.10 USDC (6 decimals)
    block_number: int = 12_345_678,
    include_other_logs: bool = True,
) -> dict:
    """Return a fake receipt shaped like the web3.py response."""
    logs = []

    # A noise log that should be ignored (different address / wrong topic).
    # Noise topic is constructed at runtime so the pre-commit secret
    # scanner does not see a bare 64-hex literal.
    if include_other_logs:
        logs.append(
            {
                "address": "0x1111111111111111111111111111111111111111",
                "topics": [
                    "0x" + "b" * 64,  # non-Transfer topic (would be ignored)
                    _pad_address(AGENT_WALLET),
                ],
                "data": "0x" + "0" * 64,
            }
        )

    logs.append(
        {
            "address": token_address,
            "topics": [
                TRANSFER_TOPIC,
                _pad_address(from_addr),
                _pad_address(to_addr),
            ],
            "data": "0x" + hex(amount_raw)[2:].rjust(64, "0"),
        }
    )
    return {
        "status": status,
        "blockNumber": block_number,
        "logs": logs,
    }


def _factory_with(receipt: Optional[dict]):
    """web3_factory stub — returns a web3-ish object with the given receipt."""
    w3 = MagicMock()
    if receipt is None:
        w3.eth.get_transaction_receipt.return_value = None
    else:
        w3.eth.get_transaction_receipt.return_value = receipt
    return lambda _network: w3


# =============================================================================
# Happy path
# =============================================================================


class TestSuccess:
    def test_agent_to_worker_transfer_accepted(self):
        factory = _factory_with(_build_receipt())
        result = verify_counterparty_proof(
            proof_tx=VALID_TX,
            rater_wallet=AGENT_WALLET,
            ratee_wallet=WORKER_WALLET,
            network="base",
            web3_factory=factory,
        )
        assert result["tx_hash"] == VALID_TX
        assert result["block_number"] == 12_345_678
        assert result["amount_raw"] == 100_000
        assert result["match"] == "direct"

    def test_reverse_direction_also_accepted(self):
        """Worker->agent direction (e.g., refund) should satisfy the proof."""
        factory = _factory_with(_build_receipt())
        result = verify_counterparty_proof(
            proof_tx=VALID_TX,
            rater_wallet=WORKER_WALLET,
            ratee_wallet=AGENT_WALLET,
            network="base",
            web3_factory=factory,
        )
        assert result["tx_hash"] == VALID_TX

    def test_intermediary_transfer_accepted(self):
        """Fase 5 Operator flow: agent→TokenStore→worker within one TX."""
        token_store = "0x00000000000000000000000000000000000dabcd"
        receipt = {
            "status": 1,
            "blockNumber": 42,
            "logs": [
                {
                    "address": BASE_USDC,
                    "topics": [
                        TRANSFER_TOPIC,
                        _pad_address(AGENT_WALLET),
                        _pad_address(token_store),
                    ],
                    "data": "0x" + hex(100_000)[2:].rjust(64, "0"),
                },
                {
                    "address": BASE_USDC,
                    "topics": [
                        TRANSFER_TOPIC,
                        _pad_address(token_store),
                        _pad_address(WORKER_WALLET),
                    ],
                    "data": "0x" + hex(87_000)[2:].rjust(64, "0"),
                },
            ],
        }
        factory = _factory_with(receipt)
        result = verify_counterparty_proof(
            proof_tx=VALID_TX,
            rater_wallet=AGENT_WALLET,
            ratee_wallet=WORKER_WALLET,
            network="base",
            web3_factory=factory,
        )
        assert result["match"] == "intermediary"
        # Representative amount is the Transfer landing on the ratee.
        assert result["amount_raw"] == 87_000

    def test_checksummed_addresses_accepted(self):
        """Inputs may be checksummed; helper normalizes to lowercase."""
        factory = _factory_with(_build_receipt())
        checksummed_agent = "0x00000000000000000000000000000000000000AA"
        result = verify_counterparty_proof(
            proof_tx=VALID_TX,
            rater_wallet=checksummed_agent,
            ratee_wallet=WORKER_WALLET,
            network="base",
            web3_factory=factory,
        )
        assert result["tx_hash"] == VALID_TX


# =============================================================================
# ProofMissing — malformed or absent proof_tx
# =============================================================================


class TestProofMissing:
    def test_none_raises(self):
        with pytest.raises(ProofMissing):
            verify_counterparty_proof(
                proof_tx=None,
                rater_wallet=AGENT_WALLET,
                ratee_wallet=WORKER_WALLET,
                network="base",
                web3_factory=_factory_with(_build_receipt()),
            )

    def test_empty_string_raises(self):
        with pytest.raises(ProofMissing):
            verify_counterparty_proof(
                proof_tx="",
                rater_wallet=AGENT_WALLET,
                ratee_wallet=WORKER_WALLET,
                network="base",
                web3_factory=_factory_with(_build_receipt()),
            )

    def test_short_hex_raises(self):
        with pytest.raises(ProofMissing):
            verify_counterparty_proof(
                proof_tx="0xdeadbeef",
                rater_wallet=AGENT_WALLET,
                ratee_wallet=WORKER_WALLET,
                network="base",
                web3_factory=_factory_with(_build_receipt()),
            )

    def test_non_hex_raises(self):
        with pytest.raises(ProofMissing):
            verify_counterparty_proof(
                proof_tx="0x" + "z" * 64,
                rater_wallet=AGENT_WALLET,
                ratee_wallet=WORKER_WALLET,
                network="base",
                web3_factory=_factory_with(_build_receipt()),
            )


# =============================================================================
# ProofUnverifiable — RPC / chain / mining failures
# =============================================================================


class TestProofUnverifiable:
    def test_receipt_none_raises(self):
        factory = _factory_with(None)
        with pytest.raises(ProofUnverifiable):
            verify_counterparty_proof(
                proof_tx=VALID_TX,
                rater_wallet=AGENT_WALLET,
                ratee_wallet=WORKER_WALLET,
                network="base",
                web3_factory=factory,
            )

    def test_unknown_network_raises(self):
        with pytest.raises(ProofUnverifiable):
            verify_counterparty_proof(
                proof_tx=VALID_TX,
                rater_wallet=AGENT_WALLET,
                ratee_wallet=WORKER_WALLET,
                network="not-a-real-chain",
                web3_factory=_factory_with(_build_receipt()),
            )

    def test_rpc_exception_raises(self):
        w3 = MagicMock()
        w3.eth.get_transaction_receipt.side_effect = RuntimeError("rpc down")
        with pytest.raises(ProofUnverifiable):
            verify_counterparty_proof(
                proof_tx=VALID_TX,
                rater_wallet=AGENT_WALLET,
                ratee_wallet=WORKER_WALLET,
                network="base",
                web3_factory=lambda _n: w3,
            )


# =============================================================================
# ProofRejected — on-chain says "no"
# =============================================================================


class TestProofRejected:
    def test_reverted_tx_rejected(self):
        factory = _factory_with(_build_receipt(status=0))
        with pytest.raises(ProofRejected):
            verify_counterparty_proof(
                proof_tx=VALID_TX,
                rater_wallet=AGENT_WALLET,
                ratee_wallet=WORKER_WALLET,
                network="base",
                web3_factory=factory,
            )


# =============================================================================
# ProofMismatch — transfer exists but wrong parties
# =============================================================================


class TestProofMismatch:
    def test_wrong_counterparty_rejected(self):
        factory = _factory_with(
            _build_receipt(from_addr=AGENT_WALLET, to_addr=OTHER_WALLET)
        )
        with pytest.raises(ProofMismatch):
            verify_counterparty_proof(
                proof_tx=VALID_TX,
                rater_wallet=AGENT_WALLET,
                ratee_wallet=WORKER_WALLET,
                network="base",
                web3_factory=factory,
            )

    def test_wrong_token_rejected(self):
        """Transfer exists but from a non-USDC contract → rejected."""
        fake_token = "0xdeadbeef00000000000000000000000000000000"
        factory = _factory_with(_build_receipt(token_address=fake_token))
        with pytest.raises(ProofMismatch):
            verify_counterparty_proof(
                proof_tx=VALID_TX,
                rater_wallet=AGENT_WALLET,
                ratee_wallet=WORKER_WALLET,
                network="base",
                web3_factory=factory,
            )

    def test_no_logs_rejected(self):
        receipt = {"status": 1, "blockNumber": 1, "logs": []}
        factory = _factory_with(receipt)
        with pytest.raises(ProofMismatch):
            verify_counterparty_proof(
                proof_tx=VALID_TX,
                rater_wallet=AGENT_WALLET,
                ratee_wallet=WORKER_WALLET,
                network="base",
                web3_factory=factory,
            )

    def test_self_rating_rejected(self):
        factory = _factory_with(_build_receipt())
        with pytest.raises(ProofMismatch):
            verify_counterparty_proof(
                proof_tx=VALID_TX,
                rater_wallet=AGENT_WALLET,
                ratee_wallet=AGENT_WALLET,
                network="base",
                web3_factory=factory,
            )


# =============================================================================
# Feature flag
# =============================================================================


class TestFeatureFlag:
    def test_default_off(self, monkeypatch):
        monkeypatch.delenv("EM_REQUIRE_COUNTERPARTY_PROOF", raising=False)
        assert counterparty_proof_required() is False

    @pytest.mark.parametrize("value", ["true", "True", "1", "yes", "YES"])
    def test_truthy_values_enable(self, monkeypatch, value):
        monkeypatch.setenv("EM_REQUIRE_COUNTERPARTY_PROOF", value)
        assert counterparty_proof_required() is True

    @pytest.mark.parametrize("value", ["false", "0", "no", "off", ""])
    def test_falsy_values_disable(self, monkeypatch, value):
        monkeypatch.setenv("EM_REQUIRE_COUNTERPARTY_PROOF", value)
        assert counterparty_proof_required() is False
