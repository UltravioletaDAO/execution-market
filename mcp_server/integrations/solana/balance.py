"""Solana SPL token balance lookups (Phase 4.7 balance-gating).

Surface:

  get_solana_usdc_balance(wallet, *, http=None, rpc_url=None) -> Decimal

Calls Solana JSON-RPC `getTokenAccountsByOwner` filtered to the USDC mint,
sums all token accounts the wallet owns (in case of multiple ATAs), and
returns the human-readable balance as a Decimal.

Returns Decimal("0") on any failure — RPC error, network blip, wallet has
no SPL accounts, malformed response. The balance-gate caller treats "0
or below threshold" as "needs on-ramp" regardless of why, so collapsing
errors to 0 is the right default. Logs the underlying error so we can
diagnose without forcing the gate to bubble exceptions.

Why this lives outside `integrations/x402/solana_handler` (Fase 1 SPL
settlement): the handler is data-plane (it moves funds). This is a
read-only RPC probe used by HTTP request handlers, with no shared state.
"""

from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# USDC mint on Solana mainnet-beta. Same value lives in
# integrations.x402.sdk_client NETWORK_CONFIG["solana"]["tokens"]["USDC"];
# we duplicate it here to avoid an import cycle (sdk_client imports
# integrations modules at boot, this module would be imported by routes
# which sdk_client doesn't know about).
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

_DEFAULT_RPC = "https://api.mainnet-beta.solana.com"


def _resolve_rpc_url(override: Optional[str]) -> str:
    """Pick the Solana RPC: explicit override > env > public mainnet-beta."""
    if override:
        return override
    return os.environ.get("SOLANA_RPC_URL") or _DEFAULT_RPC


async def get_solana_usdc_balance(
    wallet: str,
    *,
    http: Optional[httpx.AsyncClient] = None,
    rpc_url: Optional[str] = None,
    timeout_seconds: float = 5.0,
) -> Decimal:
    """Return the wallet's total USDC balance on Solana.

    Sums every USDC SPL token account the wallet owns. A wallet without
    any USDC account returns Decimal("0") (no SPL accounts found is a
    valid state, not an error). Network failures also return Decimal("0")
    — see module docstring.

    The optional `http` parameter exists for tests that mock the HTTP
    layer. Production callers should let the function manage its own
    short-lived AsyncClient.
    """
    if not isinstance(wallet, str) or len(wallet.strip()) == 0:
        return Decimal("0")

    url = _resolve_rpc_url(rpc_url)
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            wallet,
            {"mint": USDC_MINT},
            {"encoding": "jsonParsed"},
        ],
    }

    try:
        if http is None:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                resp = await client.post(url, json=payload)
        else:
            resp = await http.post(url, json=payload, timeout=timeout_seconds)
    except Exception as exc:
        logger.warning(
            "Solana getTokenAccountsByOwner failed for %s: %s",
            (wallet[:8] + "...") if len(wallet) > 8 else wallet,
            exc,
        )
        return Decimal("0")

    if resp.status_code != 200:
        logger.warning(
            "Solana RPC returned %d for %s",
            resp.status_code,
            (wallet[:8] + "...") if len(wallet) > 8 else wallet,
        )
        return Decimal("0")

    try:
        body = resp.json()
    except ValueError:
        logger.warning("Solana RPC returned non-JSON response")
        return Decimal("0")

    if "error" in body:
        logger.warning("Solana RPC error: %s", body["error"])
        return Decimal("0")

    accounts = (body.get("result") or {}).get("value") or []
    total = Decimal("0")
    for entry in accounts:
        try:
            ui_amount = entry["account"]["data"]["parsed"]["info"]["tokenAmount"][
                "uiAmountString"
            ]
        except (KeyError, TypeError):
            continue
        try:
            total += Decimal(ui_amount)
        except Exception:
            continue

    return total
