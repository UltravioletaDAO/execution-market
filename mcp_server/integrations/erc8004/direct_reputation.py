"""
Direct On-Chain Reputation Feedback for ERC-8004

Bypasses the Facilitator for giveFeedback() calls to the ReputationRegistry.
This eliminates nonce race conditions and provides correct msg.sender attribution.

Two-wallet strategy:
- Agent rates Worker: Platform wallet (WALLET_PRIVATE_KEY) — we don't own worker agents
- Worker rates Agent: Relay wallet (EM_REPUTATION_RELAY_KEY) — platform wallet owns Agent #2106,
  would trigger self-feedback revert

Contract: ReputationRegistry (CREATE2, same address on all mainnets)
Function: giveFeedback(uint256, int128, uint8, string, string, string, string, bytes32)
Access: Permissionless (except self-feedback: isAuthorizedOrOwner check)
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING, Optional

from web3 import Web3

try:
    from web3.middleware import ExtraDataToPOAMiddleware as _poa_middleware
except ImportError:
    from web3.middleware import geth_poa_middleware as _poa_middleware

if TYPE_CHECKING:
    from .facilitator_client import FeedbackResult

logger = logging.getLogger(__name__)

# ReputationRegistry — CREATE2 deterministic, same address on all mainnets
REPUTATION_REGISTRY_ADDRESS = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"

# Minimal ABI for giveFeedback
GIVE_FEEDBACK_ABI = [
    {
        "inputs": [
            {"name": "agentId", "type": "uint256"},
            {"name": "value", "type": "int128"},
            {"name": "valueDecimals", "type": "uint8"},
            {"name": "tag1", "type": "string"},
            {"name": "tag2", "type": "string"},
            {"name": "endpoint", "type": "string"},
            {"name": "feedbackURI", "type": "string"},
            {"name": "feedbackHash", "type": "bytes32"},
        ],
        "name": "giveFeedback",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

# Network config — reuse from identity.py
BASE_CHAIN_ID = 8453
BASE_RPC_URL = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")

# Module-level nonce lock to serialise direct on-chain TXs and prevent
# "replacement transaction underpriced" errors when multiple reputation
# calls fire in quick succession (e.g. WS-2b + WS-2 in the same approval).
_nonce_lock = asyncio.Lock()


def _get_web3() -> Web3:
    """Create a Web3 instance connected to Base Mainnet."""
    rpc_url = os.environ.get("X402_RPC_URL", BASE_RPC_URL)
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    w3.middleware_onion.inject(_poa_middleware, layer=0)
    return w3


def _normalize_feedback_hash(feedback_hash: Optional[str]) -> bytes:
    """Convert a hex string hash to bytes32, or return zero bytes."""
    if not feedback_hash:
        return b"\x00" * 32
    # Strip 0x prefix and convert
    hex_str = feedback_hash.replace("0x", "")
    # Pad or truncate to exactly 32 bytes
    hex_str = hex_str.ljust(64, "0")[:64]
    return bytes.fromhex(hex_str)


async def give_feedback_direct(
    agent_id: int,
    value: int,
    value_decimals: int = 0,
    tag1: str = "",
    tag2: str = "",
    endpoint: str = "",
    feedback_uri: str = "",
    feedback_hash: Optional[str] = None,
    private_key: Optional[str] = None,
) -> "FeedbackResult":
    """
    Submit reputation feedback directly on-chain to the ReputationRegistry.

    Uses web3.py to call giveFeedback() — no Facilitator intermediary.
    The msg.sender is the address derived from the provided private key.

    Args:
        agent_id: Target agent's ERC-8004 token ID
        value: Feedback value (0-100 for decimals=0)
        value_decimals: Decimal places for value
        tag1: Primary tag (e.g., "worker_rating", "agent_rating")
        tag2: Secondary tag
        endpoint: Service endpoint context (e.g., "task:<task_id>")
        feedback_uri: URI to off-chain feedback document (S3/CDN)
        feedback_hash: Keccak256 hash of feedback content (0x-prefixed hex)
        private_key: Private key for signing. Defaults to WALLET_PRIVATE_KEY.

    Returns:
        FeedbackResult with transaction hash on success.
    """
    from .facilitator_client import FeedbackResult, ERC8004_NETWORK

    pk = private_key or os.environ.get("WALLET_PRIVATE_KEY")
    if not pk:
        return FeedbackResult(
            success=False,
            error="No private key available for direct feedback",
            network=ERC8004_NETWORK,
        )

    hash_bytes = _normalize_feedback_hash(feedback_hash)

    def _send_tx():
        w3 = _get_web3()
        account = w3.eth.account.from_key(pk)
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(REPUTATION_REGISTRY_ADDRESS),
            abi=GIVE_FEEDBACK_ABI,
        )

        # Build transaction
        tx = contract.functions.giveFeedback(
            agent_id,
            value,
            value_decimals,
            tag1,
            tag2,
            endpoint,
            feedback_uri,
            hash_bytes,
        ).build_transaction(
            {
                "from": account.address,
                "chainId": BASE_CHAIN_ID,
                "gasPrice": w3.eth.gas_price,
                "nonce": w3.eth.get_transaction_count(account.address, "pending"),
            }
        )

        # Estimate gas with 20% buffer
        try:
            estimated = w3.eth.estimate_gas(tx)
            tx["gas"] = int(estimated * 1.2)
        except Exception as e:
            logger.warning("Gas estimation failed, using default 200k: %s", e)
            tx["gas"] = 200_000

        # Sign and send
        signed = w3.eth.account.sign_transaction(tx, pk)
        # web3.py v7+ uses `raw_transaction`, v6 uses `rawTransaction`
        raw_tx = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        tx_hash = w3.eth.send_raw_transaction(raw_tx)

        # Wait for receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        return tx_hash.hex(), receipt

    try:
        async with _nonce_lock:
            tx_hash_hex, receipt = await asyncio.to_thread(_send_tx)

        if receipt["status"] == 1:
            logger.info(
                "Direct feedback submitted: agent_id=%d, value=%d, tx=%s, sender=%s",
                agent_id,
                value,
                tx_hash_hex,
                receipt.get("from", "unknown"),
            )
            return FeedbackResult(
                success=True,
                transaction_hash=tx_hash_hex,
                network=ERC8004_NETWORK,
            )
        else:
            logger.error(
                "Direct feedback TX reverted: agent_id=%d, tx=%s",
                agent_id,
                tx_hash_hex,
            )
            return FeedbackResult(
                success=False,
                transaction_hash=tx_hash_hex,
                error="Transaction reverted (possible self-feedback or invalid agent ID)",
                network=ERC8004_NETWORK,
            )

    except Exception as e:
        error_msg = str(e)
        # Retry once on nonce-related errors (e.g. "replacement transaction
        # underpriced" or "nonce too low") — the pending nonce may have been
        # stale if a prior TX landed between our read and send.
        if any(
            s in error_msg.lower()
            for s in (
                "replacement transaction underpriced",
                "nonce too low",
                "already known",
            )
        ):
            logger.warning(
                "Direct feedback nonce conflict, retrying in 2s: agent_id=%d, error=%s",
                agent_id,
                error_msg,
            )
            try:
                await asyncio.sleep(2)
                async with _nonce_lock:
                    tx_hash_hex, receipt = await asyncio.to_thread(_send_tx)
                if receipt["status"] == 1:
                    logger.info(
                        "Direct feedback retry succeeded: agent_id=%d, tx=%s",
                        agent_id,
                        tx_hash_hex,
                    )
                    return FeedbackResult(
                        success=True,
                        transaction_hash=tx_hash_hex,
                        network=ERC8004_NETWORK,
                    )
            except Exception as retry_err:
                error_msg = f"Retry also failed: {retry_err}"

        logger.error(
            "Direct feedback failed: agent_id=%d, error=%s",
            agent_id,
            error_msg,
        )
        return FeedbackResult(
            success=False,
            error=error_msg,
            network=ERC8004_NETWORK,
        )
