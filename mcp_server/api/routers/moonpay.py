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
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from utils.net import get_client_ip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/moonpay", tags=["MoonPay"])


# ---------------------------------------------------------------------------
# Fraud velocity caps (F-05) — enforced BEFORE signing a Widget URL.
#
# A signed URL is bearer-like: anyone holding it can debit our MoonPay
# account (threat "onramp link abuse" / R3 chargeback rings in
# docs/runbooks/onramp-fraud.md). We cap onramp velocity across the three
# dimensions the runbook requires — per user (external_customer_id), per
# wallet, per IP — counting attempts in a rolling 24h window from the
# moonpay_onramp_attempts ledger (migration 110). Defaults match the runbook
# (~3 onramps/24h, ~$200/24h per user); all are env-overridable.
# ---------------------------------------------------------------------------
_VELOCITY_WINDOW_HOURS = int(os.environ.get("EM_MOONPAY_VELOCITY_WINDOW_HOURS", "24"))
_MAX_ONRAMPS_PER_USER = int(os.environ.get("EM_MOONPAY_MAX_ONRAMPS_PER_USER", "3"))
_MAX_USD_PER_USER = float(os.environ.get("EM_MOONPAY_MAX_USD_PER_USER", "200"))
_MAX_ONRAMPS_PER_WALLET = int(os.environ.get("EM_MOONPAY_MAX_ONRAMPS_PER_WALLET", "3"))
_MAX_ONRAMPS_PER_IP = int(os.environ.get("EM_MOONPAY_MAX_ONRAMPS_PER_IP", "5"))


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

    Delegates to the hardened :func:`utils.net.get_client_ip` so the
    trusted-proxy boundary and right-most-hop selection (FIX-P2-02) apply.
    An explicit ``override`` (validated upstream) still wins.
    """
    if override:
        return override
    return get_client_ip(request)


def _window_cutoff_iso() -> str:
    """ISO timestamp for the start of the rolling velocity window."""
    return (
        datetime.now(timezone.utc) - timedelta(hours=_VELOCITY_WINDOW_HOURS)
    ).isoformat()


def _count_attempts(db, column: str, value: str, cutoff: str) -> int:
    """Count sign-url attempts for one dimension in the rolling window.

    Returns the count, or 0 if the query fails. NOTE: failing open here is a
    deliberate availability tradeoff — a transient DB blip should not block a
    legitimate funder. The cap is a velocity speed-bump layered on top of
    MoonPay's own card-fraud/3DS controls (it is the merchant of record), not
    the only line of defense. Failures are logged so a sustained outage that
    silently disables the cap is visible.
    """
    try:
        resp = (
            db.get_client()
            .table("moonpay_onramp_attempts")
            .select("id", count="exact")
            .eq(column, value)
            .gte("created_at", cutoff)
            .execute()
        )
        return resp.count or 0
    except Exception as exc:
        logger.error(
            "MoonPay velocity count failed (%s) — failing open: %s", column, exc
        )
        return 0


def _sum_user_usd(db, external_customer_id: str, cutoff: str) -> float:
    """Sum fiat requested by one user in the rolling window. 0.0 on failure."""
    try:
        resp = (
            db.get_client()
            .table("moonpay_onramp_attempts")
            .select("base_amount")
            .eq("external_customer_id", external_customer_id)
            .gte("created_at", cutoff)
            .execute()
        )
        total = 0.0
        for row in resp.data or []:
            try:
                total += float(row.get("base_amount") or 0)
            except (TypeError, ValueError):
                continue
        return total
    except Exception as exc:
        logger.error("MoonPay velocity USD sum failed — failing open: %s", exc)
        return 0.0


def _enforce_velocity_caps(body: SignUrlRequest, request_ip: str) -> None:
    """Reject the sign-url request with 429 if any velocity cap is hit.

    Checked BEFORE signing so a denied attempt never produces a usable URL.
    Dimensions (per docs/runbooks/onramp-fraud.md):
      - per user (external_customer_id): max count AND max USD / window
      - per wallet: max count / window
      - per IP: max count / window (catches account farming)

    The denied reason is logged (LOW-severity probing signal per the runbook's
    Sentry table) but NOT echoed in full to the client — we return a generic
    429 so a probe can't map the exact cap that tripped.
    """
    try:
        import supabase_client as db
    except Exception as exc:  # pragma: no cover - import guard
        logger.error(
            "MoonPay velocity gate: supabase_client unavailable — failing open: %s",
            exc,
        )
        return

    cutoff = _window_cutoff_iso()
    wallet = body.wallet_address
    masked = wallet[:6] + "..." + wallet[-4:] if len(wallet) > 10 else "***"

    # Per-user dimensions (only when the caller supplied an identity).
    if body.external_customer_id:
        user_count = _count_attempts(
            db, "external_customer_id", body.external_customer_id, cutoff
        )
        if user_count >= _MAX_ONRAMPS_PER_USER:
            logger.warning(
                "SECURITY_AUDIT action=moonpay.velocity_denied reason=user_count "
                "ext_customer=%s count=%s limit=%s window_h=%s",
                body.external_customer_id,
                user_count,
                _MAX_ONRAMPS_PER_USER,
                _VELOCITY_WINDOW_HOURS,
            )
            raise HTTPException(
                status_code=429,
                detail="Onramp velocity limit reached. Try again later.",
            )

        user_usd = _sum_user_usd(db, body.external_customer_id, cutoff)
        if user_usd + body.base_currency_amount > _MAX_USD_PER_USER:
            logger.warning(
                "SECURITY_AUDIT action=moonpay.velocity_denied reason=user_usd "
                "ext_customer=%s spent=%.2f requested=%.2f limit=%.2f window_h=%s",
                body.external_customer_id,
                user_usd,
                body.base_currency_amount,
                _MAX_USD_PER_USER,
                _VELOCITY_WINDOW_HOURS,
            )
            raise HTTPException(
                status_code=429,
                detail="Onramp amount limit reached. Try again later.",
            )

    # Per-wallet dimension (applies even to anonymous callers).
    wallet_count = _count_attempts(db, "wallet_address", wallet, cutoff)
    if wallet_count >= _MAX_ONRAMPS_PER_WALLET:
        logger.warning(
            "SECURITY_AUDIT action=moonpay.velocity_denied reason=wallet_count "
            "wallet=%s count=%s limit=%s window_h=%s",
            masked,
            wallet_count,
            _MAX_ONRAMPS_PER_WALLET,
            _VELOCITY_WINDOW_HOURS,
        )
        raise HTTPException(
            status_code=429,
            detail="Onramp velocity limit reached. Try again later.",
        )

    # Per-IP dimension (account farming).
    ip_count = _count_attempts(db, "request_ip", request_ip, cutoff)
    if ip_count >= _MAX_ONRAMPS_PER_IP:
        logger.warning(
            "SECURITY_AUDIT action=moonpay.velocity_denied reason=ip_count "
            "ip=%s count=%s limit=%s window_h=%s",
            request_ip,
            ip_count,
            _MAX_ONRAMPS_PER_IP,
            _VELOCITY_WINDOW_HOURS,
        )
        raise HTTPException(
            status_code=429,
            detail="Onramp velocity limit reached. Try again later.",
        )


def _record_attempt(body: SignUrlRequest, request_ip: str) -> None:
    """Append the issued attempt to moonpay_onramp_attempts. Never raises.

    Called only after caps passed and signing succeeded, so the ledger
    reflects URLs actually issued. Best-effort: a failed insert is logged but
    does not fail the request (the URL is already signed by then).
    """
    try:
        import supabase_client as db

        db.get_client().table("moonpay_onramp_attempts").insert(
            {
                "external_customer_id": body.external_customer_id,
                "wallet_address": body.wallet_address,
                "request_ip": request_ip,
                "base_amount": body.base_currency_amount,
                "base_currency_code": body.base_currency_code,
                "crypto_currency_code": body.currency_code,
            }
        ).execute()
    except Exception as exc:
        logger.error("MoonPay attempt ledger insert failed: %s", exc)


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
async def sign_url_endpoint(body: SignUrlRequest, request: Request) -> SignUrlResponse:
    from integrations.moonpay.client import sign_url

    # Fraud velocity caps (F-05): reject over-limit callers with 429 BEFORE
    # signing, so a denied attempt never yields a usable bearer-like URL.
    request_ip = get_client_ip(request)
    _enforce_velocity_caps(body, request_ip)

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

    # Record the issued attempt for the velocity ledger (best-effort).
    _record_attempt(body, request_ip)

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
