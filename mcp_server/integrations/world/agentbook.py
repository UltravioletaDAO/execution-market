"""
World AgentKit — AgentBook Human Verification (Read-Only On-Chain Lookup)

Checks the AgentBook contract on Base to determine whether a wallet
address belongs to a World-verified human.  Returns a ``humanId`` (>0)
for verified humans, 0 for unverified addresses.

This module follows the exact same lightweight JSON-RPC pattern used by
``integrations/erc8004/identity.py`` -- no web3 dependency, just raw
``eth_call`` via httpx.

Contract: 0xE1D1D3526A6FAa37eb36bD10B933C1b77f4561a4 (Base Mainnet)
ABI:      lookupHuman(address) -> uint256
"""

import logging
import os
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Contract constants
# ---------------------------------------------------------------------------

AGENTBOOK_ADDRESS = "0xE1D1D3526A6FAa37eb36bD10B933C1b77f4561a4"

# Pre-computed 4-byte selector: keccak256("lookupHuman(address)")[:4]
# >>> hashlib.sha3_256(b"lookupHuman(address)").hexdigest()[:8]
SELECTOR_LOOKUP_HUMAN = "0x87e870c3"

# Base Mainnet RPC (same env var as ERC-8004)
BASE_RPC_URL = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class WorldHumanStatus(str, Enum):
    """World AgentBook verification status."""

    VERIFIED = "verified"
    NOT_VERIFIED = "not_verified"
    ERROR = "error"


@dataclass
class WorldHumanResult:
    """Result of a World AgentBook human lookup."""

    status: WorldHumanStatus
    human_id: Optional[int] = None
    wallet_address: Optional[str] = None
    error: Optional[str] = None

    @property
    def is_human(self) -> bool:
        """Return True if the wallet belongs to a World-verified human."""
        return self.status == WorldHumanStatus.VERIFIED and bool(
            self.human_id and self.human_id > 0
        )

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        for k, v in asdict(self).items():
            d[k] = v.value if isinstance(v, Enum) else v
        d["is_human"] = self.is_human
        return d


# ---------------------------------------------------------------------------
# ABI encoding helper
# ---------------------------------------------------------------------------


def _encode_address(addr: str) -> str:
    """ABI-encode an address as a left-padded 32-byte hex word (no 0x prefix)."""
    return addr.lower().replace("0x", "").zfill(64)


# ---------------------------------------------------------------------------
# Lightweight JSON-RPC helper (no web3 needed)
# ---------------------------------------------------------------------------


async def _eth_call(to: str, data: str, rpc_url: Optional[str] = None) -> str:
    """Execute an ``eth_call`` and return the hex-encoded result."""
    url = rpc_url or BASE_RPC_URL
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{"to": to, "data": data}, "latest"],
        "id": 1,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload)
        body = resp.json()
    if "error" in body:
        raise RuntimeError(f"RPC error: {body['error']}")
    return body.get("result", "0x")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def lookup_human(
    wallet_address: str,
    rpc_url: Optional[str] = None,
) -> WorldHumanResult:
    """
    Look up a wallet address in the AgentBook contract on Base.

    Parameters
    ----------
    wallet_address:
        Ethereum address (``0x``-prefixed).
    rpc_url:
        Optional override for the Base RPC endpoint.

    Returns
    -------
    WorldHumanResult
        Contains ``status``, ``human_id``, and the ``is_human`` property.
        Never raises -- errors are captured in the result.
    """
    try:
        calldata = SELECTOR_LOOKUP_HUMAN + _encode_address(wallet_address)
        raw = await _eth_call(AGENTBOOK_ADDRESS, calldata, rpc_url=rpc_url)
        human_id = int(raw, 16) if raw and raw != "0x" else 0

        if human_id > 0:
            logger.info(
                "World AgentBook: wallet=%s is verified human (humanId=%d)",
                wallet_address[:10],
                human_id,
            )
            return WorldHumanResult(
                status=WorldHumanStatus.VERIFIED,
                human_id=human_id,
                wallet_address=wallet_address.lower(),
            )

        logger.debug(
            "World AgentBook: wallet=%s not verified (humanId=0)",
            wallet_address[:10],
        )
        return WorldHumanResult(
            status=WorldHumanStatus.NOT_VERIFIED,
            human_id=0,
            wallet_address=wallet_address.lower(),
        )

    except Exception as exc:
        logger.warning(
            "World AgentBook lookup failed for %s: %s",
            wallet_address[:10] if wallet_address else "?",
            exc,
        )
        return WorldHumanResult(
            status=WorldHumanStatus.ERROR,
            wallet_address=(wallet_address or "").lower() or None,
            error=str(exc),
        )


async def is_human(wallet_address: str) -> bool:
    """
    Quick boolean check: is the wallet a World-verified human?

    Convenience wrapper around :func:`lookup_human`.  Returns ``False``
    on any error (never raises).
    """
    result = await lookup_human(wallet_address)
    return result.is_human
