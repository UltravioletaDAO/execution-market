"""MoonPay Headless Onramp REST endpoints (Phase 4).

  POST /api/v1/moonpay/sign-url  — HMAC-sign a Widget URL (PRODUCTION path)
  POST /api/v1/moonpay/session   — create a sessionToken (LEGACY — Phase 1D spike)
  POST /api/v1/moonpay/webhook   — receive transaction events + persist mirror
  GET  /api/v1/moonpay/health    — config sanity check (no secrets exposed)

Master switch: EM_MOONPAY_ENABLED. When unset/false the routes are not even
registered, so /api/v1/moonpay/* returns 404 instead of 503 — same gating
pattern as VeryAI / ClawKey.

The `/sign-url` endpoint is the canonical Phase 4 surface; the frontend
overlay (`@moonpay/moonpay-js`, see Phase 4.8) calls it to get a pre-signed
URL ready for `widget.show()`. The `/session` endpoint stays alive only for
the existing `/spike/moonpay` page and is removed in Phase 4.8.

The `/webhook` endpoint verifies Moonpay-Signature-V2 and upserts each event
into the `moonpay_transactions` table (migration 109). Persistence is
best-effort: a failed UPSERT is logged but the endpoint still ACKs 200, so
MoonPay does not enter a retry storm. The dashboard hook useMoonPayOnramp
(Phase 4.9) subscribes to that table via Supabase Realtime.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/moonpay", tags=["MoonPay"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class SignUrlRequest(BaseModel):
    """Body for POST /sign-url.

    `wallet_address` MUST match the chain implied by `currency_code` — e.g. a
    Solana base58 address when `currency_code=usdc_sol`. MoonPay will reject
    the buy if the wallet format mismatches the chain.

    `base_currency_amount` defaults to USD; MoonPay's Solana USDC floor is
    $20 (per D-13 of `[[MASTER_PLAN_SOLANA_MPP_ROBOT_DEMO]]`).
    """

    wallet_address: str = Field(
        ...,
        min_length=1,
        description="Destination wallet (chain depends on currency_code)",
    )
    base_currency_amount: float = Field(
        ...,
        gt=0,
        description="Fiat amount the user pays (usually USD). Min $20 for Solana USDC.",
    )
    currency_code: str = Field(
        default="usdc_sol",
        min_length=1,
        description="MoonPay crypto currency code (e.g. usdc_sol, usdc_base)",
    )
    base_currency_code: str = Field(
        default="usd",
        min_length=1,
        description="Fiat currency code (ISO 4217 lowercase)",
    )
    external_customer_id: Optional[str] = Field(
        default=None,
        description="EM executor.id UUID — enables MoonPay Customer Connection re-use",
    )
    redirect_url: Optional[str] = Field(
        default=None,
        description="Where MoonPay sends the user after purchase completes (optional)",
    )
    color_code: Optional[str] = Field(
        default=None,
        description="Hex color (with #) for the Widget primary action",
    )
    theme: Optional[str] = Field(
        default=None, description="Widget theme: 'light' or 'dark'"
    )
    base_url: Optional[str] = Field(
        default=None,
        description="Override Widget base URL (e.g. https://buy-sandbox.moonpay.com)",
    )

    @field_validator("redirect_url")
    @classmethod
    def _redirect_url_must_be_https_or_local(
        cls, value: Optional[str]
    ) -> Optional[str]:
        if value is None:
            return value
        if not (
            value.startswith("https://")
            or value.startswith("http://localhost")
            or value.startswith("http://127.0.0.1")
        ):
            raise ValueError("redirect_url must be https:// or http://localhost")
        return value


class SignUrlResponse(BaseModel):
    url: str = Field(..., description="Signed Widget URL ready for widget.show()")
    currency_code: str
    wallet_address: str


class SessionRequest(BaseModel):
    """Body for POST /session (LEGACY — `/spike/moonpay` only).

    `external_customer_id` is the EM executor.id (UUID). Passing the same
    id across sessions lets MoonPay's Customer Connection skip re-onboarding
    for returning customers.
    """

    external_customer_id: str = Field(
        ..., description="EM executor.id UUID used as MoonPay externalCustomerId"
    )
    device_ip: Optional[str] = Field(
        default=None,
        description="Optional override; defaults to the request's client IP",
    )


class SessionResponse(BaseModel):
    session_token: str
    public_key: str = Field(..., description="MoonPay pk_test_* for SDK init")
    expires_in_seconds: int


class HealthResponse(BaseModel):
    enabled: bool
    secret_key_configured: bool
    public_key_configured: bool
    webhook_secret_configured: bool
    api_base_url: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_device_ip(request: Request, override: Optional[str]) -> str:
    """Pick the client IP MoonPay's risk engine should see.

    Honors X-Forwarded-For only when present (ECS/ALB injects it). Falls
    back to the direct TCP peer. The spike doesn't enforce TRUSTED_PROXY_CIDRS
    since this route runs behind the same ALB the rest of the API uses.
    """
    if override:
        return override
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/sign-url",
    response_model=SignUrlResponse,
    summary="Sign a MoonPay Widget URL for the Headless overlay",
    description=(
        "Builds a Widget URL with the requested params and HMAC-SHA256-signs "
        "the query string using MOONPAY_SECRET_KEY (per "
        "dev.moonpay.com/docs/ramps-sdk-buy-url-signing). The frontend hands "
        "the returned URL straight to `widget.show()`. The signed URL is "
        "bearer-like: do NOT log it or expose it outside the user's session."
    ),
)
async def sign_url_endpoint(body: SignUrlRequest) -> SignUrlResponse:
    from integrations.moonpay.client import sign_url

    params: dict = {
        "currencyCode": body.currency_code,
        "baseCurrencyAmount": body.base_currency_amount,
        "baseCurrencyCode": body.base_currency_code,
        "walletAddress": body.wallet_address,
    }
    if body.external_customer_id:
        params["externalCustomerId"] = body.external_customer_id
    if body.redirect_url:
        params["redirectURL"] = body.redirect_url
    if body.color_code:
        params["colorCode"] = body.color_code
    if body.theme:
        params["theme"] = body.theme

    try:
        result = sign_url(params, base_url=body.base_url)
    except ValueError as exc:
        logger.error("MoonPay sign-url misconfigured: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="MoonPay onramp temporarily unavailable",
        )
    except Exception as exc:
        logger.error("MoonPay sign-url failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Failed to sign MoonPay URL",
        )

    # Log only non-bearer fields. The URL and signature are intentionally
    # omitted: an attacker with the signed URL can initiate a buy that
    # debits our MoonPay account.
    wallet = body.wallet_address
    masked = wallet[:6] + "..." + wallet[-4:] if len(wallet) > 10 else "***"
    logger.info(
        "MoonPay sign-url issued: wallet=%s amount=%s currency=%s ext_customer=%s",
        masked,
        body.base_currency_amount,
        body.currency_code,
        "yes" if body.external_customer_id else "no",
    )

    return SignUrlResponse(
        url=result.url,
        currency_code=body.currency_code,
        wallet_address=body.wallet_address,
    )


@router.post(
    "/session",
    response_model=SessionResponse,
    summary="Create a MoonPay platform session for headless SDK init",
    description=(
        "Calls MoonPay's POST /platform/v1/sessions with sk_test_*, returns a "
        "short-lived sessionToken the frontend hands to createClient(). The "
        "externalCustomerId carries the EM executor.id so Customer Connection "
        "can skip re-onboarding on subsequent sessions."
    ),
)
async def create_session(body: SessionRequest, request: Request) -> SessionResponse:
    from integrations.moonpay.client import (
        MOONPAY_PUBLIC_KEY,
        create_session as moonpay_create_session,
    )

    device_ip = _resolve_device_ip(request, body.device_ip)

    try:
        result = await moonpay_create_session(
            external_customer_id=body.external_customer_id,
            device_ip=device_ip,
        )
    except ValueError as exc:
        logger.error("MoonPay session misconfigured: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="MoonPay onramp temporarily unavailable",
        )
    except Exception as exc:
        logger.error("MoonPay session creation failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Failed to create MoonPay session",
        )

    if not MOONPAY_PUBLIC_KEY:
        logger.error("MOONPAY_PUBLIC_KEY missing — frontend cannot init SDK without it")
        raise HTTPException(
            status_code=503,
            detail="MoonPay onramp misconfigured (public key)",
        )

    return SessionResponse(
        session_token=result.session_token,
        public_key=MOONPAY_PUBLIC_KEY,
        expires_in_seconds=result.expires_in_seconds,
    )


def _extract_moonpay_row(payload: dict) -> Optional[dict]:
    """Project a MoonPay webhook payload onto the moonpay_transactions schema.

    Returns None when the payload lacks the columns we *require* to persist
    a row (moonpay_transaction_id + wallet_address). MoonPay's payload
    shape varies by event type, but the canonical wrapper is:

        {
          "type": "transaction_updated",
          "data": {
            "id": "<uuid>",
            "status": "completed",
            "walletAddress": "...",
            "externalCustomerId": "<executor uuid>" | null,
            "currency":     {"code": "usdc_sol"} | null,
            "currencyCode": "usdc_sol",  # sometimes flat, sometimes nested
            "baseCurrencyAmount":  100.0,
            "quoteCurrencyAmount": 99.5,
            "feeAmount":           0.5,
            "cryptoTransactionId": "<chain tx hash>"
          }
        }

    We accept both nested (`currency.code`) and flat (`currencyCode`) forms
    because MoonPay emits both depending on event version. Numbers are
    coerced to float and trimmed to 6 decimal places by NUMERIC(20,6).
    """
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return None

    txn_id = data.get("id") or payload.get("id")
    wallet = data.get("walletAddress") or data.get("wallet_address")
    if not txn_id or not wallet:
        return None

    currency_obj = data.get("currency")
    currency_code = (
        (currency_obj.get("code") if isinstance(currency_obj, dict) else None)
        or data.get("currencyCode")
        or data.get("cryptoCurrencyCode")
        or "unknown"
    )

    def _num(value: object) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    return {
        "moonpay_transaction_id": str(txn_id),
        "external_customer_id": data.get("externalCustomerId"),
        "wallet_address": str(wallet),
        "crypto_currency_code": str(currency_code),
        "base_amount": _num(data.get("baseCurrencyAmount")),
        "quote_amount": _num(data.get("quoteCurrencyAmount")),
        "fee_amount": _num(data.get("feeAmount")),
        "status": str(data.get("status") or "pending"),
        "crypto_transaction_id": data.get("cryptoTransactionId")
        or data.get("crypto_transaction_id"),
        "raw_event": payload,
    }


def _persist_moonpay_webhook(payload: dict) -> bool:
    """Upsert the MoonPay webhook into moonpay_transactions.

    Returns True on success, False on any failure (missing fields, DB error).
    Best-effort: NEVER raises — the webhook endpoint must ACK regardless so
    MoonPay does not retry-storm.
    """
    row = _extract_moonpay_row(payload)
    if row is None:
        logger.warning(
            "MoonPay webhook missing required fields (id/walletAddress); skipping persist"
        )
        return False

    try:
        import supabase_client as db

        db.get_client().table("moonpay_transactions").upsert(
            row, on_conflict="moonpay_transaction_id"
        ).execute()
        return True
    except Exception as exc:
        logger.error(
            "MoonPay webhook persist failed: txn=%s err=%s",
            str(row["moonpay_transaction_id"])[:16],
            exc,
        )
        return False


@router.post(
    "/webhook",
    summary="Receive MoonPay transaction webhooks",
    description=(
        "MoonPay POSTs transaction lifecycle events here with a "
        "Moonpay-Signature-V2 header. The body is HMAC-verified, then "
        "upserted into moonpay_transactions. ACKs with 200 on signature "
        "success even if persistence fails (logged); signature mismatch "
        "returns 401."
    ),
)
async def receive_webhook(
    request: Request,
    moonpay_signature_v2: str = Header(default="", alias="Moonpay-Signature-V2"),
):
    from integrations.moonpay.client import (
        WebhookSignatureError,
        verify_webhook,
    )

    raw_body = await request.body()

    try:
        verify_webhook(raw_body, moonpay_signature_v2)
    except ValueError as exc:
        logger.error("MoonPay webhook misconfigured: %s", exc)
        raise HTTPException(status_code=503, detail="webhook not configured")
    except WebhookSignatureError as exc:
        logger.warning("MoonPay webhook signature rejected: %s", exc)
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        import json

        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        logger.warning("MoonPay webhook body not valid JSON: %s", exc)
        raise HTTPException(status_code=400, detail="invalid json body")

    event_type = payload.get("type") or payload.get("eventType") or "unknown"
    txn_id = (payload.get("data") or {}).get("id") or payload.get("id") or "unknown"

    persisted = _persist_moonpay_webhook(payload)

    logger.info(
        "MoonPay webhook accepted: type=%s txn=%s persisted=%s",
        event_type,
        str(txn_id)[:16],
        persisted,
    )
    return {"ok": True, "event": event_type, "persisted": persisted}


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="MoonPay integration health probe (no secrets exposed)",
)
async def health() -> HealthResponse:
    import os

    from integrations.moonpay.client import config_status

    status = config_status()
    return HealthResponse(
        enabled=os.environ.get("EM_MOONPAY_ENABLED", "false").lower() == "true",
        **status,
    )
