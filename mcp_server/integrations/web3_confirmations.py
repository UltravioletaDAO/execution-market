"""
Chain-aware confirmation waiting (Task 5.3 — chain reorg handling).

Background
----------
``w3.eth.wait_for_transaction_receipt`` returns as soon as a block
containing the transaction is mined — **zero confirmations past
inclusion**. That's adequate for a test harness, but in production a
single-conf receipt on a chain that occasionally reorgs at depth >= 1
means the settlement we "succeeded" against may revert on the next
block.

Observed reorg characteristics (empirical + operator guidance):

  - Ethereum L1 ........ up to 6-block reorgs under contention.
  - Base L2 ............ occasional 1-block; 2-3 block has happened.
  - Polygon PoS ........ 2-3 block reorgs are common.
  - Arbitrum / Optimism  1-2 block, rare.
  - Avalanche / Celo ... 1-block, uncommon.
  - Monad / SKALE ...... fast finality, 1 conf is generally fine.

We therefore wait for BOTH the receipt AND for the head block to be
at least ``required_confirmations`` past the receipt block. After the
depth is reached we do one last ``get_transaction_receipt`` call to
detect the case where the original block was orphaned and the tx
settled in a sibling — in that scenario we return the NEW receipt so
callers who rely on ``blockNumber`` or event logs don't carry stale
references.

Override knobs:

  - ``chain_id=...``          — skip the RPC lookup.
  - ``min_confirmations=...`` — explicit depth (useful for tests and
                                 chain-agnostic callers).

Both defaults are module-level constants so test suites can monkeypatch
them without threading config objects through the call chain.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


# Chain-specific depth requirements. See module docstring.
CHAIN_CONFIRMATIONS: dict[int, int] = {
    1: 6,  # Ethereum mainnet
    8453: 3,  # Base
    137: 3,  # Polygon PoS
    42161: 2,  # Arbitrum One
    10: 2,  # Optimism
    43114: 2,  # Avalanche C-Chain
    42220: 2,  # Celo
    146: 2,  # Sonic
    10143: 1,  # Monad (fast finality)
    2046399126: 1,  # SKALE (instant finality)
    11155111: 2,  # Sepolia (lower requirement — testnet)
}

# Fallback for unknown chain IDs. Deliberately conservative.
DEFAULT_CONFIRMATIONS = 2


def confirmations_for(chain_id: int) -> int:
    """Return the required confirmation depth for a given chain id.

    Kept as a separate function so callers that want the count WITHOUT
    triggering the wait loop (e.g. metric labels, log messages) can ask
    directly. Unknown chains fall back to ``DEFAULT_CONFIRMATIONS``.
    """
    return CHAIN_CONFIRMATIONS.get(chain_id, DEFAULT_CONFIRMATIONS)


def wait_for_confirmations(
    w3: Any,
    tx_hash: Union[bytes, str],
    *,
    chain_id: Optional[int] = None,
    min_confirmations: Optional[int] = None,
    receipt_timeout: float = 120.0,
    confirm_timeout: float = 300.0,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """Wait for a transaction to be included AND confirmed at depth N.

    Args:
        w3: web3.py ``Web3`` instance.
        tx_hash: Transaction hash (bytes or 0x-prefixed hex string).
        chain_id: When ``None`` (default), queried from ``w3.eth.chain_id``.
            Pass explicitly when testing or when the RPC node's
            advertised chain id might differ from the real one.
        min_confirmations: Explicit depth. ``None`` → resolve from
            ``chain_id`` via ``CHAIN_CONFIRMATIONS``. ``0`` disables the
            depth check entirely (returns as soon as a receipt exists),
            which reproduces the legacy behaviour.
        receipt_timeout: Seconds to wait for first inclusion.
        confirm_timeout: Seconds to wait AFTER inclusion for the required
            depth. Separate from ``receipt_timeout`` so callers can
            budget independently.
        poll_interval: Seconds between block-head polls. Kept at 2s to
            match most chains' block time without spamming the RPC.

    Returns:
        The confirmed receipt. In the rare case of a 1-block reorg
        after inclusion, the receipt is re-fetched and the NEW one is
        returned (different ``blockNumber``/``blockHash``).

    Raises:
        TimeoutError: If ``confirm_timeout`` elapses before reaching
            the required depth. Caller should decide whether to retry
            (the tx may still be valid, just slow to confirm) or abort.
    """
    # 1) Wait for the tx to be included. This preserves the existing
    #    timeout budget for callers that previously had just this step.
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=receipt_timeout)

    # Resolve depth requirement.
    if min_confirmations is None:
        if chain_id is None:
            try:
                chain_id = w3.eth.chain_id
            except Exception as exc:  # noqa: BLE001 — RPC may glitch
                logger.warning(
                    "chain_id probe failed, falling back to default depth: %s", exc
                )
                chain_id = None
        required = (
            confirmations_for(chain_id)
            if chain_id is not None
            else DEFAULT_CONFIRMATIONS
        )
    else:
        required = int(min_confirmations)

    if required <= 0:
        return receipt

    receipt_block = receipt["blockNumber"]
    target_block = receipt_block + required

    logger.debug(
        "waiting for %d confs past block %d (target %d) — chain_id=%s",
        required,
        receipt_block,
        target_block,
        chain_id,
    )

    deadline = time.monotonic() + confirm_timeout
    while time.monotonic() < deadline:
        head = w3.eth.block_number
        if head >= target_block:
            # 2) Reorg-safety: re-fetch the receipt. If the canonical
            #    block changed, return the new one so callers don't act
            #    on stale data. ``blockHash`` is the authoritative ID —
            #    ``blockNumber`` can repeat across forks.
            fresh = w3.eth.get_transaction_receipt(tx_hash)
            if fresh.get("blockHash") != receipt.get("blockHash"):
                logger.warning(
                    "reorg detected for tx=%s: original block=%s, new block=%s",
                    _tx_hash_repr(tx_hash),
                    receipt.get("blockHash"),
                    fresh.get("blockHash"),
                )
                return fresh
            return receipt
        time.sleep(poll_interval)

    raise TimeoutError(
        f"confirmations({required}) not reached within {confirm_timeout}s "
        f"for tx={_tx_hash_repr(tx_hash)}"
    )


def _tx_hash_repr(tx_hash: Union[bytes, str]) -> str:
    """Render a hash in a log-safe way regardless of the web3.py version."""
    if hasattr(tx_hash, "hex"):
        try:
            return tx_hash.hex()
        except Exception:  # noqa: BLE001
            pass
    return str(tx_hash)
