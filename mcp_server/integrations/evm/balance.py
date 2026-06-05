"""EVM ERC-20 USDC balance lookups (Phase 1 — Base onramp balance-gating).

Surface:

  get_evm_usdc_balance(wallet, network="base", *, http=None, rpc_url=None) -> Decimal

Calls the chain's JSON-RPC `eth_call` against the USDC contract's
`balanceOf(address)` selector and returns the human-readable balance as a
Decimal (USDC is 6 decimals on every EVM chain we support).

This is the EVM twin of `integrations/solana/balance.py::get_solana_usdc_balance`.
It backs the Base balance-gate that decides whether a publisher needs a
MoonPay on-ramp handoff before their EIP-3009 escrow pre-auth can be signed
(ADR-001). The gate only needs "does the wallet hold >= bounty+fee"; it never
moves funds.

Returns Decimal("0") on any failure — RPC error, network blip, unknown
network, malformed response. The balance-gate caller treats "0 or below
threshold" as "needs on-ramp" regardless of why, so collapsing errors to 0
is the right default. The underlying error is logged for diagnosis.

USDC contract addresses are duplicated here (not imported from
`integrations.x402.sdk_client.NETWORK_CONFIG`) to avoid an import cycle —
sdk_client imports integration modules at boot, and this module is imported
by the route handlers that sdk_client does not know about. Same rationale as
the Solana module's USDC_MINT duplication. They were cross-checked against
both NETWORK_CONFIG and MoonPay's /v3/currencies contractAddress on
2026-06-04; keep them in sync if USDC ever migrates.
"""

from __future__ import annotations

import logging
import os
import re
from decimal import Decimal
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# A syntactically valid EVM address: 0x followed by exactly 40 hex chars.
# We do NOT enforce EIP-55 checksum casing — balanceOf is case-insensitive and
# the address is lower-cased before encoding. This is purely a shape guard so a
# non-address value (e.g. an API-key agent_id) never reaches eth_call as
# malformed calldata that silently returns balance 0.
_EVM_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

# ERC-20 balanceOf(address) selector: keccak256("balanceOf(address)")[:4].
_BALANCE_OF_SELECTOR = "0x70a08231"

# USDC is 6 decimals on all supported EVM chains.
_USDC_DECIMALS = 6

# Per-network USDC contract + RPC resolution. RPC env vars follow the
# QuikNode-private convention from the repo RPC policy (prefer env, public
# endpoint as fallback only).
_EVM_NETWORKS: dict[str, dict[str, str]] = {
    "base": {
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "rpc_env": "BASE_RPC_URL",
        "default_rpc": "https://mainnet.base.org",
    },
    "ethereum": {
        "usdc": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "rpc_env": "ETHEREUM_RPC_URL",
        "default_rpc": "https://eth.llamarpc.com",
    },
    "polygon": {
        "usdc": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "rpc_env": "POLYGON_RPC_URL",
        "default_rpc": "https://polygon-rpc.com",
    },
    "arbitrum": {
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "rpc_env": "ARBITRUM_RPC_URL",
        "default_rpc": "https://arb1.arbitrum.io/rpc",
    },
    "optimism": {
        "usdc": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
        "rpc_env": "OPTIMISM_RPC_URL",
        "default_rpc": "https://mainnet.optimism.io",
    },
    "avalanche": {
        "usdc": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
        "rpc_env": "AVALANCHE_RPC_URL",
        "default_rpc": "https://api.avax.network/ext/bc/C/rpc",
    },
}


def is_valid_evm_address(wallet: object) -> bool:
    """Return True iff ``wallet`` is a syntactically valid 0x EVM address.

    Shape only: ``0x`` + 40 hex chars (case-insensitive). Used by the balance
    gate to reject non-address values (API-key ``agent_id``, empty strings)
    BEFORE they reach ``balanceOf`` encoding — otherwise malformed calldata
    yields a balance of 0 and a misleading "needs on-ramp" 402.
    """
    return isinstance(wallet, str) and bool(_EVM_ADDRESS_RE.match(wallet))


def _resolve_rpc_url(network: str, override: Optional[str]) -> Optional[str]:
    """Pick the RPC for a network: explicit override > env > public default."""
    if override:
        return override
    cfg = _EVM_NETWORKS.get(network)
    if not cfg:
        return None
    return os.environ.get(cfg["rpc_env"]) or cfg["default_rpc"]


def _encode_balance_of(wallet: str) -> str:
    """ABI-encode balanceOf(address): selector + 32-byte left-padded address."""
    addr = wallet.lower()
    if addr.startswith("0x"):
        addr = addr[2:]
    return _BALANCE_OF_SELECTOR + addr.rjust(64, "0")


async def get_evm_usdc_balance(
    wallet: str,
    network: str = "base",
    *,
    http: Optional[httpx.AsyncClient] = None,
    rpc_url: Optional[str] = None,
    timeout_seconds: float = 5.0,
) -> Decimal:
    """Return the wallet's USDC balance on an EVM network (default Base).

    Issues a single `eth_call` to USDC's `balanceOf(wallet)`. A wallet that
    has never held USDC returns Decimal("0") (a zero balance is a valid
    state). Network failures, unknown networks, and malformed responses also
    return Decimal("0") — see module docstring.

    The optional `http` parameter exists for tests that mock the HTTP layer.
    Production callers should let the function manage its own short-lived
    AsyncClient.
    """
    if not is_valid_evm_address(wallet):
        logger.warning(
            "get_evm_usdc_balance: invalid EVM address shape on %s — refusing "
            "to encode balanceOf",
            network,
        )
        return Decimal("0")

    cfg = _EVM_NETWORKS.get(network)
    if not cfg:
        logger.warning("get_evm_usdc_balance: unsupported network %r", network)
        return Decimal("0")

    url = _resolve_rpc_url(network, rpc_url)
    if not url:
        return Decimal("0")

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [
            {"to": cfg["usdc"], "data": _encode_balance_of(wallet)},
            "latest",
        ],
    }

    masked = (wallet[:6] + "...") if len(wallet) > 6 else wallet
    try:
        if http is None:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                resp = await client.post(url, json=payload)
        else:
            resp = await http.post(url, json=payload, timeout=timeout_seconds)
    except Exception as exc:
        logger.warning(
            "EVM eth_call balanceOf failed for %s on %s: %s", masked, network, exc
        )
        return Decimal("0")

    if resp.status_code != 200:
        logger.warning(
            "EVM RPC returned %d for %s on %s", resp.status_code, masked, network
        )
        return Decimal("0")

    try:
        body = resp.json()
    except ValueError:
        logger.warning("EVM RPC returned non-JSON response on %s", network)
        return Decimal("0")

    if "error" in body:
        logger.warning("EVM RPC error on %s: %s", network, body["error"])
        return Decimal("0")

    raw = body.get("result")
    if not isinstance(raw, str) or not raw.startswith("0x"):
        return Decimal("0")

    try:
        units = int(raw, 16)
    except ValueError:
        return Decimal("0")

    return Decimal(units) / (Decimal(10) ** _USDC_DECIMALS)
