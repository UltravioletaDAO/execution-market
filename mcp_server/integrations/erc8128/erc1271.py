"""
ERC-1271: Smart Contract Account Signature Verification

For smart contract wallets (Safe, ERC-4337 accounts), verification cannot
use ecrecover. Instead, we call isValidSignature(bytes32, bytes) on the
contract and check for the magic value 0x1626ba7e.

This module provides optional SCA verification for ERC-8128. If the EOA
ecrecover fails (e.g., address is a contract), the verifier can fall back
to ERC-1271 on-chain verification.

Requires an RPC endpoint for the chain specified in the keyid.
"""

import logging
import os
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# isValidSignature(bytes32,bytes) selector
IS_VALID_SIGNATURE_SELECTOR = "1626ba7e"

# Magic return value indicating valid signature
MAGIC_VALUE = "1626ba7e"

# RPC URL configuration (keyed by chain ID)
_RPC_URLS: dict[int, str] = {
    1: os.environ.get("ETH_RPC_URL", "https://eth.llamarpc.com"),
    8453: os.environ.get("BASE_RPC_URL", "https://mainnet.base.org"),
    11155111: os.environ.get("SEPOLIA_RPC_URL", "https://rpc.sepolia.org"),
    84532: os.environ.get("BASE_SEPOLIA_RPC_URL", "https://sepolia.base.org"),
}

# Cache for isValidSignature results (address:hash -> bool), TTL-based
_SCA_CACHE: dict[str, tuple[bool, float]] = {}
_SCA_CACHE_TTL = 300  # 5 minutes


# ---------------------------------------------------------------------------
# ABI encoding helpers
# ---------------------------------------------------------------------------


def _encode_is_valid_signature(message_hash: bytes, signature: bytes) -> str:
    """
    ABI-encode the isValidSignature(bytes32, bytes) call.

    Layout:
      4 bytes:  function selector
      32 bytes: message_hash (bytes32)
      32 bytes: offset to signature data (0x40 = 64)
      32 bytes: signature length
      N bytes:  signature data (padded to 32-byte boundary)
    """
    selector = IS_VALID_SIGNATURE_SELECTOR

    # bytes32 message_hash (already 32 bytes)
    hash_hex = message_hash.hex().zfill(64)

    # Offset to dynamic bytes parameter (after two 32-byte words = 64 = 0x40)
    offset = "0" * 62 + "40"

    # Length of signature
    sig_len = len(signature)
    length_hex = hex(sig_len)[2:].zfill(64)

    # Signature data padded to 32-byte boundary
    padded_len = ((sig_len + 31) // 32) * 32
    sig_hex = signature.hex().ljust(padded_len * 2, "0")

    return f"0x{selector}{hash_hex}{offset}{length_hex}{sig_hex}"


# ---------------------------------------------------------------------------
# RPC call
# ---------------------------------------------------------------------------


def _get_rpc_for_chain(chain_id: int) -> Optional[str]:
    """Get the RPC URL for a chain ID."""
    return _RPC_URLS.get(chain_id)


async def _eth_call(
    to: str, data: str, rpc_url: str
) -> Optional[str]:
    """Execute eth_call and return hex result."""
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": to, "data": data}, "latest"],
        "id": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(rpc_url, json=payload)
            body = resp.json()
        if "error" in body:
            logger.warning("RPC error for ERC-1271 call: %s", body["error"])
            return None
        return body.get("result", "0x")
    except Exception as e:
        logger.error("RPC call failed for ERC-1271: %s", e)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def verify_erc1271_signature(
    address: str,
    message_hash: bytes,
    signature: bytes,
    chain_id: int,
) -> bool:
    """
    Verify a signature using ERC-1271 isValidSignature on-chain.

    Parameters
    ----------
    address:
        The smart contract account address.
    message_hash:
        The keccak256 hash that was signed (32 bytes).
    signature:
        The raw signature bytes.
    chain_id:
        The chain to call the contract on.

    Returns
    -------
    True if the contract returns the magic value 0x1626ba7e, False otherwise.
    """
    # Check cache
    cache_key = f"{address.lower()}:{message_hash.hex()}"
    cached = _SCA_CACHE.get(cache_key)
    if cached is not None:
        result, ts = cached
        if time.time() - ts < _SCA_CACHE_TTL:
            return result

    rpc_url = _get_rpc_for_chain(chain_id)
    if not rpc_url:
        logger.warning(
            "No RPC URL configured for chain %d, cannot verify ERC-1271", chain_id
        )
        return False

    calldata = _encode_is_valid_signature(message_hash, signature)
    result_hex = await _eth_call(address, calldata, rpc_url)

    if result_hex is None:
        return False

    # Check for magic value in first 4 bytes of return
    clean = result_hex.replace("0x", "").ljust(64, "0")
    is_valid = clean[:8] == MAGIC_VALUE

    # Cache result
    _SCA_CACHE[cache_key] = (is_valid, time.time())

    if is_valid:
        logger.info(
            "ERC-1271 signature valid: address=%s chain=%d", address, chain_id
        )
    else:
        logger.warning(
            "ERC-1271 signature invalid: address=%s chain=%d result=%s",
            address,
            chain_id,
            result_hex[:20],
        )

    return is_valid


def clear_sca_cache() -> int:
    """Clear the SCA verification cache. Returns entries removed."""
    count = len(_SCA_CACHE)
    _SCA_CACHE.clear()
    return count
