"""Resolve the authenticated MCP caller (FIX-P0-01).

Reads the wallet the MCPAuthMiddleware verified and injected as a trusted scope
header (x-em-verified-wallet). Tools MUST derive identity from this, never from
params.agent_id / params.executor_id.

The middleware (integrations/erc8128/mcp_auth_middleware.py) injects the recovered
wallet into the ASGI scope headers. The MCP SDK threads the originating Starlette
Request into the tool as ``ctx.request_context.request``, so the header is readable
there. When the master flag ``EM_MCP_AUTH_ENABLED`` is off (staged rollout) no
verified wallet is present and tools fall back to the legacy body value — the
bypass is loudly audit-logged by the middleware.
"""

from __future__ import annotations

import os
from typing import Optional


class MCPAuthError(Exception):
    """Raised when no verified caller is present (enforcement on, no signature)."""


def _enabled() -> bool:
    return os.environ.get("EM_MCP_AUTH_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )


def get_verified_wallet(ctx) -> Optional[str]:
    """Return the lowercased verified wallet, or None if unauthenticated.

    ``ctx`` is the FastMCP ``Context`` (or None when a tool is called directly,
    e.g. unit tests / stdio with no signed request). We read the trusted header
    the middleware injected onto the originating Starlette Request.
    """
    if ctx is None:
        return None
    try:
        request = ctx.request_context.request  # Starlette Request threaded by the SDK
    except Exception:
        request = None
    if request is None:
        return None
    try:
        wallet = request.headers.get("x-em-verified-wallet")
    except Exception:
        wallet = None
    return wallet.lower() if wallet else None


def require_agent_identity(ctx, claimed_agent_id: Optional[str]) -> str:
    """Return the authoritative agent_id for ownership checks.

    Enforcement ON: returns the verified wallet; raises MCPAuthError if absent.
      The verified wallet IS the agent_id for ERC-8128 callers (mirrors
      api/auth.py, which sets agent_id = wallet address).
    Enforcement OFF (staged rollout): falls back to the claimed body value so
      legacy/local flows keep working; the bypass is logged by the middleware.
    """
    wallet = get_verified_wallet(ctx)
    if wallet:
        return wallet
    if _enabled():
        raise MCPAuthError(
            "Authentication required: sign this MCP request with ERC-8128 "
            "(see https://execution.market/skill.md)."
        )
    return (claimed_agent_id or "").lower()


def require_executor_wallet(ctx) -> Optional[str]:
    """Verified wallet for worker-side tools (bind executor_id to this wallet).

    Enforcement ON with no verified wallet → MCPAuthError. Enforcement OFF →
    returns None and the caller falls back to legacy body-asserted identity.
    """
    wallet = get_verified_wallet(ctx)
    if not wallet and _enabled():
        raise MCPAuthError(
            "Authentication required: sign this MCP request with ERC-8128."
        )
    return wallet
