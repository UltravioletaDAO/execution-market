"""
Payment utility endpoints (balances, network info).

Extracted as a dedicated router for payment-related queries that don't
belong in the task or worker lifecycle routers.
"""

import asyncio
import logging
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Path, Query

from integrations.x402.sdk_client import (
    NETWORK_CONFIG,
    get_enabled_networks,
    get_rpc_url,
    is_svm_network,
)

from ._models import ErrorResponse

logger = logging.getLogger("em.api.payments")

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])

# ERC-20 balanceOf(address) function selector
_BALANCE_OF_SELECTOR = "0x70a08231"

# Per-chain RPC timeout in seconds
_RPC_TIMEOUT = 5.0

# Regex for 0x-prefixed EVM addresses
_EVM_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


async def _query_evm_balance(
    network: str,
    address: str,
    token_symbol: str,
    token_config: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Query a single ERC-20 balance via JSON-RPC eth_call. Returns None on failure."""
    try:
        rpc_url = get_rpc_url(network)
        token_address = token_config["address"]
        decimals = token_config["decimals"]

        addr_clean = address.lower().replace("0x", "").zfill(64)
        call_data = _BALANCE_OF_SELECTOR + addr_clean

        payload = {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [
                {"to": token_address, "data": call_data},
                "latest",
            ],
            "id": 1,
        }

        async with httpx.AsyncClient() as http:
            resp = await http.post(rpc_url, json=payload, timeout=_RPC_TIMEOUT)
            data = resp.json()

        result_hex = data.get("result", "0x0")
        if not result_hex or result_hex == "0x":
            result_hex = "0x0"
        balance_raw = int(result_hex, 16)
        balance = Decimal(balance_raw) / Decimal(10**decimals)

        return {
            "network": network,
            "balance_usdc": str(balance),
            "token": token_symbol,
        }
    except Exception as e:
        logger.debug(
            "Balance query failed for %s on %s: %s",
            address[:10],
            network,
            e,
        )
        return None


@router.get(
    "/balance/{address}",
    responses={
        200: {
            "description": "USDC balances across enabled chains",
            "content": {
                "application/json": {
                    "example": {
                        "address": "0x1234...abcd",
                        "balances": [
                            {
                                "network": "base",
                                "balance_usdc": "1.230000",
                                "token": "USDC",
                            }
                        ],
                        "total_usdc": "5.670000",
                    }
                }
            },
        },
        400: {"model": ErrorResponse, "description": "Invalid address format"},
    },
    summary="Get USDC Balance",
    description=(
        "Query on-chain USDC balanceOf(address) across all enabled EVM networks. "
        "Optionally filter to a single network. Chains that fail to respond within "
        "5 seconds are silently skipped."
    ),
)
async def get_balance(
    address: str = Path(
        ...,
        description="Wallet address (0x-prefixed, EVM)",
        min_length=42,
        max_length=42,
    ),
    network: Optional[str] = Query(
        None, description="Filter to a single network (e.g. 'base', 'polygon')"
    ),
) -> Dict[str, Any]:
    """Return USDC balances for *address* across enabled EVM networks."""

    if not _EVM_ADDRESS_RE.match(address):
        raise HTTPException(status_code=400, detail="Invalid EVM address format")

    # Determine which networks to query
    if network:
        if network not in NETWORK_CONFIG:
            supported = ", ".join(sorted(NETWORK_CONFIG.keys()))
            raise HTTPException(
                status_code=400,
                detail=f"Unknown network '{network}'. Supported: {supported}",
            )
        if is_svm_network(network):
            raise HTTPException(
                status_code=400,
                detail=f"Network '{network}' is SVM-based. This endpoint supports EVM only.",
            )
        networks = [network]
    else:
        # All enabled EVM networks
        networks = [n for n in get_enabled_networks() if not is_svm_network(n)]

    # Build coroutines — one per network, querying USDC
    tasks: List[asyncio.Task] = []
    for net in networks:
        net_config = NETWORK_CONFIG.get(net, {})
        tokens = net_config.get("tokens", {})
        usdc_config = tokens.get("USDC")
        if not usdc_config:
            continue
        tasks.append(_query_evm_balance(net, address, "USDC", usdc_config))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    balances: List[Dict[str, Any]] = []
    total = Decimal("0")
    for r in results:
        if isinstance(r, dict) and r is not None:
            balances.append(r)
            try:
                total += Decimal(r["balance_usdc"])
            except Exception:
                pass

    return {
        "address": address,
        "balances": balances,
        "total_usdc": str(total),
    }
