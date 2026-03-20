"""
x402 Protocol Discovery Endpoint (/.well-known/x402)

Implements the x402 auto-discovery standard so that agents using x402-compatible
clients (AgentCash, etc.) can automatically discover Execution Market's payment
capabilities, supported networks, tokens, and pricing.

Spec: https://docs.x402r.org/specification/discovery
"""

import os
import logging
from typing import Any, Dict, List

from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["x402 Discovery"])


def _build_supported_networks() -> List[Dict[str, Any]]:
    """Build list of supported networks from NETWORK_CONFIG (single source of truth)."""
    try:
        from integrations.x402.sdk_client import NETWORK_CONFIG, ENABLED_NETWORKS
    except ImportError:
        logger.warning("x402 SDK not available, returning empty network list")
        return []

    networks = []
    for name, config in NETWORK_CONFIG.items():
        if name not in ENABLED_NETWORKS:
            continue

        tokens = []
        for symbol, token_info in config.get("tokens", {}).items():
            tokens.append(
                {
                    "symbol": symbol,
                    "address": token_info.get("address", ""),
                    "decimals": token_info.get("decimals", 6),
                }
            )

        entry: Dict[str, Any] = {
            "name": name,
            "chainId": config.get("chain_id"),
            "type": config.get("network_type", "evm"),
            "tokens": tokens,
        }

        if config.get("escrow"):
            entry["escrow"] = True
        if config.get("operator"):
            entry["operator"] = config["operator"]

        networks.append(entry)

    return networks


def _build_discovery_payload() -> Dict[str, Any]:
    """Build the /.well-known/x402 discovery payload."""
    from integrations.x402.sdk_client import FACILITATOR_URL, DEFAULT_NETWORK

    platform_fee_pct = int(float(os.environ.get("EM_PLATFORM_FEE", "0.13")) * 100)

    return {
        "x402": {
            "version": "1.0",
            "description": (
                "Execution Market -- Universal Execution Layer. "
                "AI agents publish bounties for real-world tasks, "
                "executors complete them with verified evidence, "
                "instant gasless payment via x402."
            ),
            "provider": {
                "name": "Execution Market",
                "url": "https://execution.market",
                "contact": "ultravioletadao@gmail.com",
            },
            "capabilities": {
                "payments": True,
                "escrow": True,
                "gasless": True,
                "eip3009": True,
                "multichain": True,
            },
            "facilitator": FACILITATOR_URL,
            "defaultNetwork": DEFAULT_NETWORK,
            "networks": _build_supported_networks(),
            "fees": {
                "platformFeeBps": platform_fee_pct * 100,
                "description": (
                    f"{platform_fee_pct}% platform fee on task completion. "
                    "Fee split is atomic on-chain via PaymentOperator."
                ),
            },
            "endpoints": {
                "tasks": {
                    "create": {
                        "method": "POST",
                        "path": "/api/v1/tasks",
                        "description": "Publish a new task for human execution",
                        "auth": "bearer",
                        "pricing": {
                            "model": "bounty",
                            "description": (
                                "Agent sets bounty amount (min $0.01 USDC). "
                                "Paid at task completion, not at creation."
                            ),
                        },
                    },
                    "list": {
                        "method": "GET",
                        "path": "/api/v1/tasks",
                        "description": "Browse available tasks",
                        "auth": "bearer",
                        "pricing": {"model": "free"},
                    },
                    "get": {
                        "method": "GET",
                        "path": "/api/v1/tasks/{task_id}",
                        "description": "Get task details",
                        "auth": "bearer",
                        "pricing": {"model": "free"},
                    },
                    "approve": {
                        "method": "POST",
                        "path": "/api/v1/tasks/{task_id}/approve",
                        "description": "Approve submission and release payment",
                        "auth": "bearer",
                        "pricing": {
                            "model": "settlement",
                            "description": (
                                "Triggers EIP-3009 settlement: "
                                "agent -> worker (bounty) + agent -> treasury (fee). "
                                "Gasless via facilitator."
                            ),
                        },
                    },
                },
                "identity": {
                    "register": {
                        "method": "POST",
                        "path": "/api/v1/reputation/register",
                        "description": "Register ERC-8004 agent identity (gasless)",
                        "auth": "bearer",
                        "pricing": {"model": "free"},
                    },
                },
                "health": {
                    "check": {
                        "method": "GET",
                        "path": "/health",
                        "description": "Service health check",
                        "auth": "none",
                        "pricing": {"model": "free"},
                    },
                },
            },
            "discovery": {
                "a2a": "/.well-known/agent.json",
                "openapi": "/openapi.json",
                "docs": "/docs",
                "mcp": "/mcp/",
            },
            "identity": {
                "protocol": "ERC-8004",
                "agentId": 2106,
                "network": "base",
                "registry": "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
            },
        },
    }


@router.get(
    "/.well-known/x402",
    response_class=JSONResponse,
    summary="x402 Payment Discovery",
    description=(
        "Auto-discovery endpoint for x402-compatible clients. "
        "Returns supported networks, tokens, pricing, and endpoint information. "
        "No authentication required."
    ),
    tags=["x402 Discovery"],
)
async def x402_discovery() -> JSONResponse:
    """Serve x402 discovery information at the well-known URL."""
    payload = _build_discovery_payload()
    return JSONResponse(
        content=payload,
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-x402-Version": "1.0",
        },
    )
