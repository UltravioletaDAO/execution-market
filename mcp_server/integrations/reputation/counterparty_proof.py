"""
Reputation counterparty proof verification (SAAS hardening Task 5.2).

Binds a rating submission to a concrete on-chain payment so that only
real counterparties of a settled task can rate each other. Without this,
`POST /api/v1/reputation/workers/rate` (and the symmetric agent-rate
flow) accepts any ``proof_tx`` or none at all — a rating-bomb vector.

The verification flow
---------------------

1. The caller passes a 0x-prefixed tx hash plus the claimed rater and
   ratee wallet addresses and the task's payment network.
2. We fetch the receipt via web3.py on the correct chain. A missing
   receipt (``None``) means the tx is not mined; a ``status == 0``
   receipt means it reverted. Both are rejected.
3. We parse the receipt logs for ``Transfer(address,address,uint256)``
   events emitted by the USDC contract configured for that network.
4. We accept the proof if:
     a. Direct match — some USDC Transfer has ``(from, to)`` equal to
        ``(rater, ratee)`` OR ``(ratee, rater)``. Covers the Fase 2
        direct EIP-3009 settlement where agent→worker is one hop.
     b. Or intermediary match — rater and ratee EACH appear in some
        USDC Transfer log (as from or to) in this same TX. Covers the
        Fase 5 Operator flow where funds travel agent→TokenStore and
        TokenStore→worker as two separate Transfers inside the same
        ``captureAuthorization`` tx.
   Both branches reject the "rating bomb" case where the proof_tx is
   unrelated to the claimed pair — neither party appears.

Consumed by ``mcp_server/api/reputation.py``. Gated by
``EM_REQUIRE_COUNTERPARTY_PROOF`` so we can deploy the verification
in shadow mode first and flip the enforcement once telemetry says it
is stable.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _compute_transfer_topic() -> str:
    """Return ERC-20 Transfer event topic[0] as a 0x-prefixed hex string.

    We compute it at import time from the event signature rather than
    hard-coding the 64-hex literal, both to avoid repeating a magic
    constant and to keep the repo's pre-commit ``0x + 64 hex chars``
    secret scanner from mistaking the public topic hash for a leaked
    private key.
    """
    from web3 import Web3  # type: ignore

    h = Web3.keccak(text="Transfer(address,address,uint256)").hex()
    return h if h.startswith("0x") else "0x" + h


# keccak256("Transfer(address,address,uint256)") — ERC-20 Transfer event topic[0].
_TRANSFER_TOPIC = _compute_transfer_topic()


class CounterpartyProofError(Exception):
    """Base class for counterparty proof failures."""


class ProofMissing(CounterpartyProofError):
    """Caller did not provide a proof_tx or it was malformed."""


class ProofUnverifiable(CounterpartyProofError):
    """RPC failure, tx not yet mined, or chain unreachable."""


class ProofRejected(CounterpartyProofError):
    """Proof exists but the tx reverted or emitted no USDC transfer."""


class ProofMismatch(CounterpartyProofError):
    """Tx succeeded but the transfer counterparties don't match."""


def counterparty_proof_required() -> bool:
    """Feature flag — whether missing/invalid proofs reject the request.

    Default ``false``: we validate when a proof is supplied (audit
    signal) but do not yet reject calls without one. Flip to ``true``
    once the endpoint clients (dashboard, KK, external agents) have
    been updated to pass ``proof_tx``.
    """
    return os.environ.get("EM_REQUIRE_COUNTERPARTY_PROOF", "false").lower() in (
        "true",
        "1",
        "yes",
    )


def _normalize_tx_hash(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    s = str(value).strip().lower()
    if not s.startswith("0x"):
        s = "0x" + s
    # 0x + 64 hex chars
    if len(s) != 66:
        return None
    try:
        int(s, 16)
    except ValueError:
        return None
    return s


def _normalize_address(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    s = str(value).strip().lower()
    if not s.startswith("0x") or len(s) != 42:
        return None
    try:
        int(s, 16)
    except ValueError:
        return None
    return s


def _topic_to_address(topic: Any) -> Optional[str]:
    """Extract an address from a 32-byte indexed-topic log entry."""
    if topic is None:
        return None
    if isinstance(topic, bytes):
        hex_topic = "0x" + topic.hex()
    else:
        hex_topic = str(topic).lower()
    if not hex_topic.startswith("0x"):
        hex_topic = "0x" + hex_topic
    if len(hex_topic) != 66:
        return None
    # Last 40 hex chars = 20-byte address, left-padded with zeros.
    return "0x" + hex_topic[-40:]


def _log_address(log: Any) -> Optional[str]:
    """web3.py gives us a dict-like or AttributeDict. Both expose 'address'."""
    if log is None:
        return None
    if hasattr(log, "get"):
        addr = log.get("address")
    else:
        addr = getattr(log, "address", None)
    if addr is None:
        return None
    return str(addr).lower()


def _log_topics(log: Any) -> list:
    if log is None:
        return []
    if hasattr(log, "get"):
        topics = log.get("topics") or []
    else:
        topics = getattr(log, "topics", None) or []
    return list(topics)


def verify_counterparty_proof(
    *,
    proof_tx: Optional[str],
    rater_wallet: str,
    ratee_wallet: str,
    network: str,
    web3_factory: Optional[Any] = None,
) -> dict:
    """Verify that ``proof_tx`` settled USDC between rater and ratee.

    Args:
        proof_tx: 0x-prefixed tx hash of the payment release TX.
        rater_wallet: Wallet of the account submitting the rating.
        ratee_wallet: Wallet of the account being rated.
        network: Payment network name (``"base"``, ``"ethereum"``, ...).
            Must be in the x402 NETWORK_CONFIG.
        web3_factory: Optional callable that returns a configured
            ``Web3`` instance for ``network``. Injected only in tests;
            production callers let the helper build its own w3.

    Returns:
        ``{"tx_hash": str, "block_number": int, "amount_raw": int}``
        on success. Callers typically log it to the audit trail.

    Raises:
        ProofMissing: ``proof_tx`` is absent or malformed.
        ProofUnverifiable: RPC error, tx not mined, or network unknown.
        ProofRejected: Tx reverted or emitted no USDC Transfer.
        ProofMismatch: Transfer present but (from, to) don't match.
    """
    tx_hash = _normalize_tx_hash(proof_tx)
    if not tx_hash:
        raise ProofMissing("proof_tx is missing or not a valid 0x-prefixed tx hash")

    rater = _normalize_address(rater_wallet)
    ratee = _normalize_address(ratee_wallet)
    if not rater or not ratee:
        raise ProofMismatch("rater_wallet or ratee_wallet is not a valid address")
    if rater == ratee:
        # Self-feedback is blocked at the endpoint layer; treat as
        # mismatch here defensively.
        raise ProofMismatch("rater and ratee wallets are identical")

    # Locate the USDC token address for this chain. We only accept
    # USDC-denominated proofs today — EM settlements are always USDC.
    try:
        from integrations.x402.sdk_client import (
            get_rpc_url,
            get_token_config,
        )
    except ImportError as exc:  # pragma: no cover — import path only
        raise ProofUnverifiable(f"x402 sdk_client unavailable: {exc}") from exc

    try:
        token = get_token_config(network, "USDC")
    except ValueError as exc:
        raise ProofUnverifiable(
            f"USDC not configured for network '{network}': {exc}"
        ) from exc

    token_address = str(token.get("address") or "").lower()
    if not token_address:
        raise ProofUnverifiable(f"USDC address missing in config for '{network}'")

    # Build (or receive) the web3 client.
    if web3_factory is not None:
        w3 = web3_factory(network)
    else:
        try:
            from web3 import Web3
        except ImportError as exc:  # pragma: no cover — dep always present
            raise ProofUnverifiable(f"web3.py not installed: {exc}") from exc
        rpc_url = get_rpc_url(network)
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 15}))

    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
    except Exception as exc:  # noqa: BLE001 — RPC surface varies
        raise ProofUnverifiable(
            f"failed to fetch receipt for {tx_hash[:12]}...: {exc}"
        ) from exc

    if receipt is None:
        raise ProofUnverifiable(f"tx {tx_hash[:12]}... not mined on {network}")

    status = None
    if hasattr(receipt, "get"):
        status = receipt.get("status")
    if status is None:
        status = getattr(receipt, "status", None)
    if status is not None and int(status) != 1:
        raise ProofRejected(f"tx {tx_hash[:12]}... reverted (status={status})")

    logs = []
    if hasattr(receipt, "get"):
        logs = receipt.get("logs") or []
    if not logs:
        logs = getattr(receipt, "logs", None) or []

    # Collect all USDC Transfer logs in a single pass, then decide
    # whether the proof matches directly OR via an intermediary.
    transfers: list[dict] = []
    for log in logs:
        if _log_address(log) != token_address:
            continue
        topics = _log_topics(log)
        if len(topics) < 3:
            continue
        topic0 = topics[0]
        topic0_hex = (
            "0x" + topic0.hex() if isinstance(topic0, bytes) else str(topic0).lower()
        )
        if not topic0_hex.startswith("0x"):
            topic0_hex = "0x" + topic0_hex
        if topic0_hex != _TRANSFER_TOPIC:
            continue
        from_addr = _topic_to_address(topics[1])
        to_addr = _topic_to_address(topics[2])
        if not from_addr or not to_addr:
            continue
        transfers.append(
            {
                "from": from_addr,
                "to": to_addr,
                "amount": _parse_transfer_amount(log),
            }
        )

    if not transfers:
        raise ProofMismatch(
            f"tx {tx_hash[:12]}... on {network} has no USDC Transfer logs"
        )

    block_number = None
    if hasattr(receipt, "get"):
        block_number = receipt.get("blockNumber")
    if block_number is None:
        block_number = getattr(receipt, "blockNumber", None)

    # Branch (a) — direct transfer between rater and ratee.
    for t in transfers:
        if {t["from"], t["to"]} == {rater, ratee}:
            logger.info(
                "counterparty_proof verified (direct): tx=%s network=%s amount_raw=%s",
                tx_hash[:12] + "...",
                network,
                t["amount"],
            )
            return {
                "tx_hash": tx_hash,
                "block_number": int(block_number) if block_number is not None else 0,
                "amount_raw": int(t["amount"]) if t["amount"] is not None else 0,
                "match": "direct",
            }

    # Branch (b) — both parties appear across the Transfer set (Fase 5
    # Operator flow routes funds via a TokenStore clone, so there is no
    # single Transfer with both addresses).
    parties_seen: set[str] = set()
    for t in transfers:
        parties_seen.add(t["from"])
        parties_seen.add(t["to"])
    if rater in parties_seen and ratee in parties_seen:
        # Pick the Transfer involving the ratee as receiver as the
        # representative amount — that is the bounty release in the
        # escrow flow (TokenStore → worker).
        amount = 0
        for t in transfers:
            if t["to"] == ratee and t["amount"] is not None:
                amount = int(t["amount"])
                break
        logger.info(
            "counterparty_proof verified (intermediary): tx=%s network=%s amount_raw=%s",
            tx_hash[:12] + "...",
            network,
            amount,
        )
        return {
            "tx_hash": tx_hash,
            "block_number": int(block_number) if block_number is not None else 0,
            "amount_raw": amount,
            "match": "intermediary",
        }

    raise ProofMismatch(
        f"tx {tx_hash[:12]}... on {network} has no USDC Transfer "
        f"between rater and ratee"
    )


def _parse_transfer_amount(log: Any) -> Optional[int]:
    """Decode the 32-byte data field of a Transfer log into a uint256."""
    data = None
    if hasattr(log, "get"):
        data = log.get("data")
    if data is None:
        data = getattr(log, "data", None)
    if data is None:
        return None
    if isinstance(data, bytes):
        hex_data = data.hex()
    else:
        hex_data = str(data).lower().removeprefix("0x")
    if not hex_data:
        return None
    try:
        return int(hex_data, 16)
    except ValueError:
        return None
