"""
ENS Resolution Client for Execution Market

Read operations (no key needed):
  - reverse_resolve(address) → ENS name
  - resolve_name(name) → address
  - get_text_record(name, key) → value
  - get_ens_avatar(name) → avatar URL
  - get_em_metadata(name) → dict of EM text records

Write operations (needs ENS_OWNER_PRIVATE_KEY):
  - create_subname(label, owner_address) → TX hash

All web3.py calls are synchronous — wrapped in asyncio.to_thread().
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

from web3 import Web3

logger = logging.getLogger(__name__)

# ── Configuration ───────────────────────────────────────────────────────────

ETHEREUM_RPC_URL = os.environ.get(
    "ETHEREUM_RPC_URL", "https://ethereum-rpc.publicnode.com"
)
ENS_OWNER_PRIVATE_KEY = os.environ.get("ENS_OWNER_PRIVATE_KEY", "")
ENS_PARENT_DOMAIN = os.environ.get("ENS_PARENT_DOMAIN", "execution-market.eth")

# EM text record keys
EM_TEXT_RECORD_PREFIX = "com.execution.market"
EM_TEXT_KEYS = [
    "agentId",
    "role",
    "worldIdVerified",
    "worldIdLevel",
    "reputation",
    "tasksCompleted",
    "chains",
]

# Standard text record keys (ENSIP-5 / EIP-634)
STANDARD_TEXT_KEYS = [
    "url",
    "description",
    "avatar",
    "email",
    "com.twitter",
    "com.github",
    "org.telegram",
    "com.discord",
]

# ENS NameWrapper address (mainnet)
NAMEWRAPPER_ADDRESS = "0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401"

# Minimal NameWrapper ABI for setSubnodeRecord
NAMEWRAPPER_ABI = [
    {
        "inputs": [
            {"name": "parentNode", "type": "bytes32"},
            {"name": "label", "type": "string"},
            {"name": "owner", "type": "address"},
            {"name": "resolver", "type": "address"},
            {"name": "ttl", "type": "uint64"},
            {"name": "fuses", "type": "uint32"},
            {"name": "expiry", "type": "uint64"},
        ],
        "name": "setSubnodeRecord",
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

# Minimal resolver ABI for text()
RESOLVER_TEXT_ABI = [
    {
        "inputs": [
            {"name": "node", "type": "bytes32"},
            {"name": "key", "type": "string"},
        ],
        "name": "text",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    }
]

# Public resolver (mainnet)
PUBLIC_RESOLVER = "0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63"

# ── TTL Cache ───────────────────────────────────────────────────────────────

_cache: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 300  # 5 minutes


def _cache_get(key: str) -> Optional[object]:
    entry = _cache.get(key)
    if entry is not None:
        ts, val = entry
        if time.time() - ts < _CACHE_TTL:
            return val
        _cache.pop(key, None)
    return None


def _cache_set(key: str, val: object) -> None:
    _cache[key] = (time.time(), val)


# ── Web3 Singleton ──────────────────────────────────────────────────────────

_w3: Optional[Web3] = None


def _get_w3() -> Web3:
    global _w3
    if _w3 is None:
        _w3 = Web3(Web3.HTTPProvider(ETHEREUM_RPC_URL, request_kwargs={"timeout": 15}))
    return _w3


# ── Namehash (EIP-137) ─────────────────────────────────────────────────────

def namehash(name: str) -> bytes:
    """Compute ENS namehash per EIP-137."""
    if not name:
        return b"\x00" * 32
    labels = name.split(".")
    node = b"\x00" * 32
    for label in reversed(labels):
        label_hash = Web3.keccak(text=label)
        node = Web3.keccak(node + label_hash)
    return node


# ── Dataclasses ─────────────────────────────────────────────────────────────

@dataclass
class ENSResolution:
    name: Optional[str] = None
    address: Optional[str] = None
    avatar: Optional[str] = None
    resolved: bool = False
    error: Optional[str] = None


# ── Read Operations (no key needed) ─────────────────────────────────────────

def _sync_reverse_resolve(address: str) -> ENSResolution:
    """Synchronous reverse resolution (address → name)."""
    cache_key = f"rev:{address.lower()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        w3 = _get_w3()
        checksum = Web3.to_checksum_address(address)
        ens_name = w3.ens.name(checksum)

        if not ens_name:
            result = ENSResolution(address=address, resolved=False)
            _cache_set(cache_key, result)
            return result

        # Verify forward resolution matches (security: prevents spoofing)
        forward = w3.ens.address(ens_name)
        if not forward or forward.lower() != address.lower():
            result = ENSResolution(
                address=address,
                resolved=False,
                error="Reverse record does not match forward resolution",
            )
            _cache_set(cache_key, result)
            return result

        result = ENSResolution(name=ens_name, address=address, resolved=True)
        _cache_set(cache_key, result)
        return result

    except Exception as exc:
        logger.debug("ENS reverse resolve failed for %s: %s", address[:10], exc)
        return ENSResolution(address=address, error=str(exc))


def _sync_resolve_name(name: str) -> ENSResolution:
    """Synchronous forward resolution (name → address)."""
    cache_key = f"fwd:{name.lower()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        w3 = _get_w3()
        address = w3.ens.address(name)

        if not address:
            result = ENSResolution(name=name, resolved=False)
            _cache_set(cache_key, result)
            return result

        result = ENSResolution(name=name, address=address, resolved=True)
        _cache_set(cache_key, result)
        return result

    except Exception as exc:
        logger.debug("ENS resolve failed for %s: %s", name, exc)
        return ENSResolution(name=name, error=str(exc))


def _sync_get_text_record(name: str, key: str) -> Optional[str]:
    """Read a single text record from an ENS name."""
    cache_key = f"txt:{name.lower()}:{key}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        w3 = _get_w3()
        resolver_obj = w3.ens.resolver(name)
        if resolver_obj is None:
            return None

        resolver = w3.eth.contract(
            address=resolver_obj.address,
            abi=RESOLVER_TEXT_ABI,
        )
        node = namehash(name)
        value = resolver.functions.text(node, key).call()
        result = value if value else None
        _cache_set(cache_key, result)
        return result

    except Exception as exc:
        logger.debug("ENS text record %s for %s failed: %s", key, name, exc)
        return None


# ── Async Wrappers ──────────────────────────────────────────────────────────

async def reverse_resolve(address: str) -> ENSResolution:
    """Async: resolve address to ENS name."""
    return await asyncio.to_thread(_sync_reverse_resolve, address)


async def resolve_name(name: str) -> ENSResolution:
    """Async: resolve ENS name to address."""
    return await asyncio.to_thread(_sync_resolve_name, name)


async def get_text_record(name: str, key: str) -> Optional[str]:
    """Async: read a text record."""
    return await asyncio.to_thread(_sync_get_text_record, name, key)


async def get_ens_avatar(name: str) -> Optional[str]:
    """Get ENS avatar URL."""
    return await get_text_record(name, "avatar")


async def get_standard_records(name: str) -> dict:
    """Read standard ENS text records."""
    records = {}
    for key in STANDARD_TEXT_KEYS:
        value = await get_text_record(name, key)
        if value is not None:
            records[key] = value
    return records


async def get_em_metadata(name: str) -> dict:
    """Read Execution Market-specific text records."""
    metadata = {}
    for key in EM_TEXT_KEYS:
        full_key = f"{EM_TEXT_RECORD_PREFIX}.{key}"
        value = await get_text_record(name, full_key)
        if value is not None:
            metadata[key] = value
    return metadata


async def resolve_with_metadata(name_or_address: str) -> dict:
    """Resolve and fetch avatar in one call."""
    # Determine if input is address or name
    if name_or_address.startswith("0x") and len(name_or_address) == 42:
        res = await reverse_resolve(name_or_address)
    else:
        res = await resolve_name(name_or_address)

    result = {
        "name": res.name,
        "address": res.address,
        "resolved": res.resolved,
        "error": res.error,
    }

    if res.resolved and res.name:
        avatar = await get_ens_avatar(res.name)
        result["avatar"] = avatar

    return result


# ── Write Operations (needs ENS_OWNER_PRIVATE_KEY) ──────────────────────────

def _sync_create_subname(label: str, owner_address: str) -> dict:
    """
    Create a subname under ENS_PARENT_DOMAIN via NameWrapper.

    Args:
        label: subname label (e.g., "alice" for alice.execution-market.eth)
        owner_address: wallet that will own the subname

    Returns:
        dict with tx_hash, subname, explorer_link
    """
    if not ENS_OWNER_PRIVATE_KEY:
        return {"error": "ENS_OWNER_PRIVATE_KEY not configured", "success": False}

    try:
        w3 = _get_w3()
        parent_node = namehash(ENS_PARENT_DOMAIN)
        full_subname = f"{label}.{ENS_PARENT_DOMAIN}"

        # Check if subname already exists
        existing = w3.ens.address(full_subname)
        if existing:
            return {
                "error": f"Subname {full_subname} already registered to {existing}",
                "success": False,
                "subname": full_subname,
            }

        # Build transaction
        namewrapper = w3.eth.contract(
            address=Web3.to_checksum_address(NAMEWRAPPER_ADDRESS),
            abi=NAMEWRAPPER_ABI,
        )

        # Strip 0x prefix if present, get account from key
        key = ENS_OWNER_PRIVATE_KEY
        if key.startswith("0x"):
            key = key[2:]
        account = w3.eth.account.from_key(key)

        # setSubnodeRecord params:
        # fuses=0 (no restrictions), expiry=max uint64 (no expiry)
        tx = namewrapper.functions.setSubnodeRecord(
            parent_node,
            label,
            Web3.to_checksum_address(owner_address),
            Web3.to_checksum_address(PUBLIC_RESOLVER),
            0,  # ttl
            0,  # fuses (no restrictions)
            2**64 - 1,  # expiry (max)
        ).build_transaction(
            {
                "from": account.address,
                "nonce": w3.eth.get_transaction_count(account.address),
                "gas": 200_000,
                "maxFeePerGas": w3.eth.gas_price * 2,
                "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
                "chainId": w3.eth.chain_id,
            }
        )

        signed = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hex = tx_hash.hex()

        logger.info(
            "ENS subname created: %s -> %s (tx: %s)",
            full_subname,
            owner_address[:10],
            tx_hex[:16],
        )

        return {
            "success": True,
            "subname": full_subname,
            "owner": owner_address,
            "tx_hash": tx_hex,
            "explorer": f"https://etherscan.io/tx/{tx_hex}",
        }

    except Exception as exc:
        logger.error("Failed to create subname %s.%s: %s", label, ENS_PARENT_DOMAIN, exc)
        return {"error": str(exc), "success": False}


async def create_subname(label: str, owner_address: str) -> dict:
    """Async: create a subname under ENS_PARENT_DOMAIN."""
    return await asyncio.to_thread(_sync_create_subname, label, owner_address)
