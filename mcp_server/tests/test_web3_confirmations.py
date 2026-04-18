"""
Unit tests for chain-aware confirmation waiting (Task 5.3).

We exercise ``wait_for_confirmations`` with a hand-rolled fake web3 rather
than a live node. The fake:

  - Starts at a caller-specified head block.
  - Advances the head on every ``block_number`` read (or by a configurable
    step), simulating new blocks arriving between polls.
  - Returns a canned receipt on ``wait_for_transaction_receipt``.
  - Lets the test program what ``get_transaction_receipt`` returns on the
    second lookup (for the reorg scenario).

We also squash the ``time.sleep`` call inside the helper so confirmation
loops finish instantly — otherwise a 2-second poll interval would drag
the suite out.
"""

from __future__ import annotations

import pytest

from integrations import web3_confirmations as wc


# ---------------------------------------------------------------------------
# Fake web3
# ---------------------------------------------------------------------------


class _FakeEth:
    """Minimal stand-in for ``w3.eth`` — only what wait_for_confirmations uses."""

    def __init__(
        self,
        *,
        chain_id: int = 8453,
        receipt: dict,
        head_start: int,
        head_step: int = 1,
        second_receipt: dict | None = None,
    ) -> None:
        self.chain_id = chain_id
        self._receipt = receipt
        # The "refetch" receipt (simulates what get_transaction_receipt
        # returns AFTER the wait loop completes — different blockHash means
        # a reorg happened).
        self._second_receipt = second_receipt if second_receipt is not None else receipt
        self._head = head_start
        self._head_step = head_step
        self._refetched = False

    # -- The helper only calls these four attributes/methods. --

    def wait_for_transaction_receipt(self, tx_hash, timeout):  # noqa: ARG002
        return self._receipt

    @property
    def block_number(self) -> int:
        # Advance monotonically on every read. Callers that want a
        # non-advancing head pass ``head_step=0``.
        current = self._head
        self._head += self._head_step
        return current

    def get_transaction_receipt(self, tx_hash):  # noqa: ARG002
        self._refetched = True
        return self._second_receipt


class _FakeWeb3:
    def __init__(self, **kwargs) -> None:
        self.eth = _FakeEth(**kwargs)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Patch ``time.sleep`` inside the helper so the loop spins instantly."""
    monkeypatch.setattr(wc.time, "sleep", lambda _s: None)


# ---------------------------------------------------------------------------
# Chain-ID-driven depth resolution
# ---------------------------------------------------------------------------


class TestDepthResolution:
    def test_unknown_chain_falls_back_to_default(self):
        assert wc.confirmations_for(9999999) == wc.DEFAULT_CONFIRMATIONS

    def test_ethereum_requires_six_confs(self):
        # Ethereum reorg depth per module docstring — guards against an
        # accidental table edit.
        assert wc.confirmations_for(1) == 6

    def test_base_requires_three(self):
        assert wc.confirmations_for(8453) == 3

    def test_monad_fast_finality_one_conf(self):
        assert wc.confirmations_for(10143) == 1


# ---------------------------------------------------------------------------
# Happy path — depth satisfied
# ---------------------------------------------------------------------------


class TestDepthSatisfied:
    def test_returns_receipt_once_head_advances_past_target(self):
        receipt = {"blockNumber": 100, "blockHash": b"\xaa" * 32, "status": 1}
        w3 = _FakeWeb3(
            chain_id=8453,  # Base → 3 confs
            receipt=receipt,
            head_start=103,  # already at target on first poll
        )
        out = wc.wait_for_confirmations(w3, b"\xde\xad" * 16, poll_interval=0.001)
        assert out is receipt  # identity — no reorg, no refetch surprise
        assert w3.eth._refetched is True  # reorg-safety always re-fetches

    def test_depth_zero_returns_immediately_without_polling(self):
        receipt = {"blockNumber": 100, "blockHash": b"\xbb" * 32, "status": 1}
        w3 = _FakeWeb3(
            chain_id=8453,
            receipt=receipt,
            head_start=0,  # would fail a depth check, but depth=0 skips it
        )
        out = wc.wait_for_confirmations(
            w3,
            b"\xde\xad" * 16,
            min_confirmations=0,
            poll_interval=0.001,
        )
        assert out is receipt
        # min_confirmations=0 is the escape hatch — no re-fetch required.
        assert w3.eth._refetched is False

    def test_explicit_min_confirmations_overrides_chain_lookup(self):
        # Ethereum default is 6, but caller forces 1 — tx should clear
        # after a single-block advance.
        receipt = {"blockNumber": 500, "blockHash": b"\xcc" * 32, "status": 1}
        w3 = _FakeWeb3(chain_id=1, receipt=receipt, head_start=501)
        out = wc.wait_for_confirmations(
            w3,
            b"\xde\xad" * 16,
            min_confirmations=1,
            poll_interval=0.001,
        )
        assert out is receipt


# ---------------------------------------------------------------------------
# Reorg detection
# ---------------------------------------------------------------------------


class TestReorgDetection:
    def test_blockhash_mismatch_returns_fresh_receipt(self):
        original = {"blockNumber": 100, "blockHash": b"\xaa" * 32, "status": 1}
        reorged = {"blockNumber": 101, "blockHash": b"\xff" * 32, "status": 1}
        w3 = _FakeWeb3(
            chain_id=8453,
            receipt=original,
            head_start=103,
            second_receipt=reorged,  # sibling block on canonical chain
        )
        out = wc.wait_for_confirmations(w3, b"\xde\xad" * 16, poll_interval=0.001)
        # The new receipt is what we return — callers relying on
        # blockNumber/logs would otherwise act on a dead fork.
        assert out is reorged
        assert out["blockHash"] != original["blockHash"]


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestTimeout:
    def test_confirm_timeout_raises_when_depth_never_reached(self):
        receipt = {"blockNumber": 1000, "blockHash": b"\xee" * 32, "status": 1}
        # Head stays at 1000 forever (head_step=0) → never reaches target.
        w3 = _FakeWeb3(
            chain_id=8453,
            receipt=receipt,
            head_start=1000,
            head_step=0,
        )
        with pytest.raises(TimeoutError) as exc:
            wc.wait_for_confirmations(
                w3,
                b"\xde\xad" * 16,
                confirm_timeout=0.05,  # fast fail
                poll_interval=0.001,
            )
        assert "confirmations" in str(exc.value)


# ---------------------------------------------------------------------------
# Chain-ID probe failure — RPC hiccups must not crash the helper
# ---------------------------------------------------------------------------


class TestChainIdProbeResilience:
    def test_chain_id_rpc_failure_falls_back_to_default(self):
        # Standalone fake that raises on chain_id access. Kept separate
        # from _FakeEth because ``chain_id`` is set as a plain attribute
        # there — overriding it with a raising property requires a fresh
        # class without that __init__ assignment.
        receipt = {"blockNumber": 100, "blockHash": b"\xaa" * 32, "status": 1}
        head = 200

        class _BoomEth:
            @property
            def chain_id(self):
                raise RuntimeError("RPC unavailable")

            def wait_for_transaction_receipt(self, tx_hash, timeout):  # noqa: ARG002
                return receipt

            @property
            def block_number(self):
                return head

            def get_transaction_receipt(self, tx_hash):  # noqa: ARG002
                return receipt

        class _BoomWeb3:
            eth = _BoomEth()

        w3 = _BoomWeb3()

        # Should NOT raise — helper falls back to DEFAULT_CONFIRMATIONS (2).
        # head=200 is far past any sensible target so the call completes.
        out = wc.wait_for_confirmations(w3, b"\xde\xad" * 16, poll_interval=0.001)
        assert out is receipt


# ---------------------------------------------------------------------------
# Tx hash repr — web3.py v6 (bytes) vs v7 (HexBytes) compat
# ---------------------------------------------------------------------------


class TestTxHashRepr:
    def test_bytes_hash_rendered(self):
        assert wc._tx_hash_repr(b"\xab\xcd") in ("abcd", "b'\\xab\\xcd'")

    def test_string_hash_passed_through(self):
        assert wc._tx_hash_repr("0xdeadbeef") == "0xdeadbeef"

    def test_object_with_hex_method_preferred(self):
        class _FakeHexBytes:
            def hex(self) -> str:
                return "deadbeef"

        assert wc._tx_hash_repr(_FakeHexBytes()) == "deadbeef"
