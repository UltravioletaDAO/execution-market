"""Balance gate for Solana task publish + assign (Phase 4.7).

Combines `get_solana_usdc_balance()` + `build_insufficient_funds_onramp()`
into one async helper that the publish + assign code paths share (REST
API in `api/routers/tasks.py` and MCP tools in `tools/`).

Surface:

  check_solana_balance_gate(wallet, required_usdc, *, external_customer_id)
      -> BalanceGateResult

The result tells the caller whether to let the request through, or to
respond with 402 INSUFFICIENT_FUNDS plus an on-ramp link. `wallet` is the
Solana base58 address the publisher will spend from; `required_usdc` is
the bounty plus platform fee.

Returns:

  BalanceGateResult(
      sufficient: bool,            # True => let request through
      balance: Decimal,            # what we observed
      shortfall: Decimal,          # max(0, required - balance)
      onramp: dict | None,         # {url, signature, qty_needed, currency}
                                   # None if MoonPay disabled or
                                   # misconfigured (frontend should
                                   # show a generic "deposit USDC" hint).
  )

The gate ONLY runs for Solana. EVM flows use x402r escrow or fase1 server
signing; neither path benefits from a MoonPay handoff at request time.
Callers MUST short-circuit on `payment_network != "solana"` before
invoking this helper.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BalanceGateResult:
    sufficient: bool
    balance: Decimal
    shortfall: Decimal
    onramp: Optional[dict]


async def check_solana_balance_gate(
    wallet: str,
    required_usdc: Decimal,
    *,
    external_customer_id: Optional[str] = None,
) -> BalanceGateResult:
    """Probe the wallet's USDC balance and build an on-ramp payload if short."""
    from integrations.solana.balance import get_solana_usdc_balance

    balance = await get_solana_usdc_balance(wallet)
    if balance >= required_usdc:
        return BalanceGateResult(
            sufficient=True,
            balance=balance,
            shortfall=Decimal("0"),
            onramp=None,
        )

    shortfall = required_usdc - balance

    from integrations.moonpay.onramp import build_insufficient_funds_onramp

    onramp = build_insufficient_funds_onramp(
        wallet=wallet,
        qty_needed=shortfall,
        external_customer_id=external_customer_id,
    )

    masked = (wallet[:6] + "..." + wallet[-4:]) if len(wallet) > 10 else "***"
    logger.info(
        "Balance gate blocked: wallet=%s balance=%s required=%s shortfall=%s "
        "onramp_available=%s",
        masked,
        balance,
        required_usdc,
        shortfall,
        bool(onramp),
    )

    return BalanceGateResult(
        sufficient=False,
        balance=balance,
        shortfall=shortfall,
        onramp=onramp,
    )


# ---------------------------------------------------------------------------
# EVM gate (Base by default) — trustless funding path for the human-hires-human
# loop. Unlike Solana (Fase 1, no escrow), Base lands USDC where the publisher
# then signs an EIP-3009 escrow pre-auth (ADR-001). The gate only decides
# whether an on-ramp handoff is needed before that signature.
# ---------------------------------------------------------------------------

# MoonPay crypto currency codes for USDC per EVM network (verified against
# api.moonpay.com/v3/currencies on 2026-06-04). Note ethereum=usdc and
# avalanche=usdc_cchain are NOT usdc_<network>, hence an explicit map.
_EVM_MOONPAY_USDC_CODE = {
    "base": "usdc_base",
    "ethereum": "usdc",
    "polygon": "usdc_polygon",
    "arbitrum": "usdc_arbitrum",
    "optimism": "usdc_optimism",
    "avalanche": "usdc_cchain",
}


async def check_evm_balance_gate(
    wallet: str,
    required_usdc: Decimal,
    *,
    network: str = "base",
    external_customer_id: Optional[str] = None,
) -> BalanceGateResult:
    """EVM twin of check_solana_balance_gate (default Base).

    Probes the wallet's USDC balance on `network` and, if short, builds a
    MoonPay on-ramp payload pinned to that chain's currency code (usdc_base,
    usdc_polygon, ...). `wallet` is the 0x address the publisher will sign the
    escrow pre-auth from; `required_usdc` is the amount the escrow actually
    locks for the active fee model (the bounty in the default credit_card
    model — the fee is taken on-chain at release, not pre-funded). Callers
    compute it via ``payment_dispatcher.publisher_hold_amount``.
    """
    from integrations.evm.balance import get_evm_usdc_balance

    balance = await get_evm_usdc_balance(wallet, network)
    if balance >= required_usdc:
        return BalanceGateResult(
            sufficient=True,
            balance=balance,
            shortfall=Decimal("0"),
            onramp=None,
        )

    shortfall = required_usdc - balance

    from integrations.moonpay.onramp import build_insufficient_funds_onramp

    currency = _EVM_MOONPAY_USDC_CODE.get(network, "usdc_base")
    onramp = build_insufficient_funds_onramp(
        wallet=wallet,
        qty_needed=shortfall,
        currency=currency,
        external_customer_id=external_customer_id,
    )

    masked = (wallet[:6] + "..." + wallet[-4:]) if len(wallet) > 10 else "***"
    logger.info(
        "EVM balance gate blocked: wallet=%s network=%s balance=%s required=%s "
        "shortfall=%s onramp_available=%s",
        masked,
        network,
        balance,
        required_usdc,
        shortfall,
        bool(onramp),
    )

    return BalanceGateResult(
        sufficient=False,
        balance=balance,
        shortfall=shortfall,
        onramp=onramp,
    )
