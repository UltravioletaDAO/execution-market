"""On-ramp payload builder for 402 INSUFFICIENT_FUNDS responses (Phase 4.7).

Surface:

  build_insufficient_funds_onramp(wallet, qty_needed, *, currency,
                                  external_customer_id=None) -> dict | None

Returns the JSON sub-object `{onramp: {url, signature, qty_needed, currency}}`
that backend endpoints attach to a 402 response when the agent's on-chain
balance is below `bounty + fee`. The frontend (Phase 4.8) hands the `url`
straight to `widget.show()`.

Why this lives next to the MoonPay client, not in the router:
  - The router exposes /sign-url as a generic helper for the frontend.
  - The balance-gate at /tasks needs the *same* signed URL but wants to
    surface it inline in a 402 body instead of issuing two round-trips
    (balance check → sign-url call). One helper, two callers.

Returns None when MoonPay is not configured (master switch off or secret
key missing). The balance gate must treat None as "no onramp available"
and degrade gracefully (return 402 with a textual hint, but no link).
"""

from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


# MoonPay's minBuyAmount per crypto code (verified against
# api.moonpay.com/v3/currencies on 2026-06-04). USDC on EVM chains is $5,
# which matches the EM $5 min-bounty floor (O6). usdc_sol historically
# floored at $20 (Solana is feature-gated / "coming soon"); kept as-is so the
# existing Solana balance-gate path is unchanged. Buying below the floor
# throws "BadRequest" server-side, so we round qty_needed UP to it.
_MIN_BUY_USD: dict[str, Decimal] = {
    "usdc_base": Decimal("5"),
    "usdc": Decimal("5"),
    "usdc_sol": Decimal("20"),
}
_DEFAULT_MIN_BUY_USD = Decimal("5")


def _min_buy_for(currency: str) -> Decimal:
    """Return MoonPay's buy floor for a crypto code (default $5)."""
    return _MIN_BUY_USD.get(currency, _DEFAULT_MIN_BUY_USD)


def _is_moonpay_enabled() -> bool:
    flag = os.environ.get("EM_MOONPAY_ENABLED", "false").strip().lower()
    return flag in ("1", "true", "yes", "on")


def build_insufficient_funds_onramp(
    wallet: str,
    qty_needed: Decimal,
    *,
    currency: str = "usdc_sol",
    external_customer_id: Optional[str] = None,
) -> Optional[dict]:
    """Build the `{onramp: {...}}` payload for a 402 response.

    `qty_needed` is the *crypto* amount the agent is short (bounty + fee
    minus current balance). We pass it through `baseCurrencyAmount` after
    flooring to MoonPay's $20 USDC minimum. Treating USD ~= USDC for the
    UX is accurate enough on a $20 sale (slippage <0.5 %).

    `currency` matches MoonPay's crypto code (`usdc_sol` for USDC on
    Solana). The master plan uses `usdc_solana` colloquially but MoonPay
    expects `usdc_sol`; we use the API code by default.

    Returns None if MoonPay is disabled or misconfigured.
    """
    if not _is_moonpay_enabled():
        return None

    try:
        from integrations.moonpay.client import sign_url
    except Exception as exc:
        logger.warning("MoonPay client import failed: %s", exc)
        return None

    floor = _min_buy_for(currency)
    if qty_needed <= 0:
        amount = floor
    else:
        amount = max(qty_needed, floor)
    # MoonPay rejects > 2 decimal places on USD. quantize handles that.
    amount = amount.quantize(Decimal("0.01"))

    params: dict = {
        "currencyCode": currency,
        "baseCurrencyAmount": float(amount),
        "baseCurrencyCode": "usd",
        "walletAddress": wallet,
    }
    if external_customer_id:
        params["externalCustomerId"] = external_customer_id

    try:
        signed = sign_url(params)
    except ValueError as exc:
        logger.warning("MoonPay sign_url misconfigured: %s", exc)
        return None
    except Exception as exc:
        logger.error("MoonPay sign_url failed: %s", exc)
        return None

    return {
        "url": signed.url,
        "signature": signed.signature,
        "qty_needed": str(amount),
        "currency": currency,
    }
