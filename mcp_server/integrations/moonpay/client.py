"""MoonPay platform/widget client — URL signing, session creation, webhook verify.

Implements the server-side half of the Headless Onramp flow. Phase 4 of
`[[MASTER_PLAN_SOLANA_MPP_ROBOT_DEMO]]` uses the **Widget URL-signing** path
(`@moonpay/moonpay-js` overlay) as the production integration; the legacy
sessionToken path (`@moonpay/platform`) remains for the existing spike page
until Phase 4.8 retires it.

Surface:

  1. sign_url(params, base_url) -> {"url": signed_url, "signature": b64}
     Builds and HMAC-SHA256-signs a MoonPay Widget URL. The frontend hands
     `url` straight to `widget.show()`. Per
     dev.moonpay.com/docs/ramps-sdk-buy-url-signing.

  2. create_session(externalCustomerId, deviceIp) -> sessionToken (LEGACY)
     Hits POST {api_base_url}/platform/v1/sessions with sk_test_*. Returned
     token is passed to `@moonpay/platform` createClient({ sessionToken }).
     **DEPRECATED**: kept alive only for `/spike/moonpay` until Phase 4.8.

  3. verify_webhook(raw_body, signature_header) -> None (raises on mismatch)
     Validates the Moonpay-Signature-V2 header (HMAC-SHA256 with replay
     window). Used by POST /api/v1/moonpay/webhook.

Env vars (required when EM_MOONPAY_ENABLED=true):
  MOONPAY_SECRET_KEY        sk_live_*/sk_test_* (server-side, NEVER exposed)
  MOONPAY_PUBLIC_KEY        pk_live_*/pk_test_* (passed to frontend bundle)
  MOONPAY_WEBHOOK_SECRET    Shared secret from MoonPay dashboard for webhook HMAC
  MOONPAY_API_BASE_URL      https://api.moonpay.com (default; sandbox uses same host)
  MOONPAY_WIDGET_BASE_URL   https://buy.moonpay.com (default; sandbox: buy-sandbox)

Security model:
  - Secret key NEVER leaves backend; frontend only receives signed URLs (or
    short-lived session tokens for the legacy spike path).
  - Webhook payloads verified via constant-time HMAC compare to prevent forgery.
  - Signed URLs and signatures are bearer-like — never log them verbatim.
  - externalCustomerId carries the EM executor.id so MoonPay's Customer
    Connection can skip re-onboarding for returning customers.

References:
  - dev.moonpay.com/docs/ramps-sdk-buy-url-signing
  - dev.moonpay.com/platform/overview/introduction
  - dev.moonpay.com/platform/guides/connect-a-customer
  - dev.moonpay.com/api-reference/widget/webhooks/signature
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from typing import Mapping, Optional
from urllib.parse import quote_plus, urlencode

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration (env-driven; missing values raise on demand, never silently)
# ---------------------------------------------------------------------------


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


MOONPAY_SECRET_KEY = _env("MOONPAY_SECRET_KEY")
MOONPAY_PUBLIC_KEY = _env("MOONPAY_PUBLIC_KEY")
MOONPAY_WEBHOOK_SECRET = _env("MOONPAY_WEBHOOK_SECRET")
MOONPAY_API_BASE_URL = _env("MOONPAY_API_BASE_URL", "https://api.moonpay.com")
MOONPAY_WIDGET_BASE_URL = _env("MOONPAY_WIDGET_BASE_URL", "https://buy.moonpay.com")


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionResult:
    """Outcome of POST /platform/v1/sessions."""

    session_token: str
    expires_in_seconds: int
    raw: dict


@dataclass(frozen=True)
class SignedUrlResult:
    """Outcome of sign_url(): the URL the frontend hands to widget.show()."""

    url: str
    signature: str
    query_string: str


class WebhookSignatureError(Exception):
    """Raised when a webhook payload fails HMAC verification."""


# ---------------------------------------------------------------------------
# Widget URL signing (HMAC-SHA256 over canonical query string)
# ---------------------------------------------------------------------------


def sign_url(
    params: Mapping[str, str | int | float | bool],
    base_url: Optional[str] = None,
) -> SignedUrlResult:
    """Build and HMAC-sign a MoonPay Widget URL.

    Algorithm (per dev.moonpay.com/docs/ramps-sdk-buy-url-signing):

        query_string  = "?" + urlencode(params)         # leading "?"
        signature_raw = HMAC-SHA256(secret_key, query_string)
        signature_b64 = base64encode(signature_raw)
        signed_url    = base_url + query_string + "&signature=" + urlencode(b64)

    MoonPay's frontend verifier signs the URL's `search` substring (which
    starts with `?`). We replicate that exactly. Order of keys is preserved
    because MoonPay signs the raw query string, not a canonical form.

    `apiKey` is auto-injected from `MOONPAY_PUBLIC_KEY` if not present so
    callers cannot forget the most-likely-rejected param. Raises
    ValueError if the secret or public key is unset.

    The caller MUST NOT log the returned URL or signature — both are
    bearer-like and would let an attacker initiate buys against the EM
    MoonPay account.
    """
    secret = _require_secret_key()

    # Auto-inject apiKey (MoonPay requires it on every Widget URL).
    if "apiKey" not in params:
        if not MOONPAY_PUBLIC_KEY:
            raise ValueError(
                "MOONPAY_PUBLIC_KEY not configured; cannot sign Widget URL "
                "without an apiKey. Set it in .env.local or AWS Secrets Manager."
            )
        params = {"apiKey": MOONPAY_PUBLIC_KEY, **dict(params)}

    # urlencode preserves insertion order in Python 3.7+. MoonPay does NOT
    # sort params before signing, so order matters.
    query_string = "?" + urlencode(
        [(k, _coerce_param(v)) for k, v in params.items()],
        quote_via=quote_plus,
    )

    digest = hmac.new(
        secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature_b64 = base64.b64encode(digest).decode("ascii")

    target_base = (base_url or MOONPAY_WIDGET_BASE_URL).rstrip("/")
    signed_url = target_base + query_string + "&signature=" + quote_plus(signature_b64)

    return SignedUrlResult(
        url=signed_url,
        signature=signature_b64,
        query_string=query_string,
    )


def _coerce_param(value: object) -> str:
    """Render a param value the way MoonPay expects in the query string.

    Booleans become lowercase strings ("true"/"false") to match the JS SDK's
    default URL serialization; numbers become their str() form (preserving
    decimals); everything else is str()'d as-is.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


# ---------------------------------------------------------------------------
# Session creation (server-side; uses sk_test_*)
# ---------------------------------------------------------------------------


def _require_secret_key() -> str:
    if not MOONPAY_SECRET_KEY:
        raise ValueError(
            "MOONPAY_SECRET_KEY not configured. "
            "Set it in .env.local or AWS Secrets Manager (em/moonpay-secret-key)."
        )
    return MOONPAY_SECRET_KEY


async def create_session(
    external_customer_id: str,
    device_ip: str,
    api_base_url: Optional[str] = None,
) -> SessionResult:
    """Create a MoonPay platform session for headless SDK initialization.

    Per dev.moonpay.com/platform/guides/connect-a-customer, the response body
    carries a `sessionToken` (sometimes nested under `token`) that the
    frontend hands to `createClient({ sessionToken })`.
    """
    secret = _require_secret_key()
    base = (api_base_url or MOONPAY_API_BASE_URL).rstrip("/")
    url = f"{base}/platform/v1/sessions"

    payload = {
        "externalCustomerId": external_customer_id,
        "deviceIp": device_ip,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            url,
            json=payload,
            headers={
                "Api-Key": secret,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    if resp.status_code not in (200, 201):
        body = resp.text[:300]
        logger.error(
            "MoonPay session creation failed: status=%d body=%s",
            resp.status_code,
            body,
        )
        raise httpx.HTTPStatusError(
            f"MoonPay session creation returned {resp.status_code}: {body}",
            request=resp.request,
            response=resp,
        )

    raw = resp.json()
    token = (
        raw.get("sessionToken")
        or raw.get("token")
        or (raw.get("data") or {}).get("sessionToken")
    )
    if not token:
        raise ValueError(
            f"MoonPay session response missing sessionToken; raw keys: {list(raw)}"
        )

    expires = int(
        raw.get("expiresIn")
        or raw.get("expires_in")
        or (raw.get("data") or {}).get("expiresIn")
        or 900
    )
    return SessionResult(session_token=token, expires_in_seconds=expires, raw=raw)


# ---------------------------------------------------------------------------
# Webhook signature verification (HMAC-SHA256, Moonpay-Signature-V2)
# ---------------------------------------------------------------------------


def _require_webhook_secret() -> str:
    if not MOONPAY_WEBHOOK_SECRET:
        raise ValueError(
            "MOONPAY_WEBHOOK_SECRET not configured. "
            "Pull from MoonPay dashboard -> Webhooks -> Signing secret."
        )
    return MOONPAY_WEBHOOK_SECRET


def _parse_signature_v2(header_value: str) -> dict:
    """Parse a Moonpay-Signature-V2 header into {timestamp, signature}.

    Format per dev.moonpay.com/api-reference/widget/webhooks/signature:
      t=1700000000,s=abc123...
    """
    out: dict = {}
    for part in (header_value or "").split(","):
        if "=" in part:
            key, value = part.split("=", 1)
            out[key.strip()] = value.strip()
    return out


def verify_webhook(
    raw_body: bytes,
    signature_header: str,
    max_age_seconds: int = 300,
) -> None:
    """Validate a MoonPay webhook signature; raise WebhookSignatureError on failure.

    Algorithm (per MoonPay docs):
      signed_payload = f"{timestamp}.{raw_body_utf8}"
      expected = HMAC-SHA256(secret, signed_payload).hexdigest()
      constant-time compare against header.s
      reject if abs(now - timestamp) > max_age_seconds (replay protection)
    """
    import time

    secret = _require_webhook_secret()
    parts = _parse_signature_v2(signature_header)
    timestamp = parts.get("t")
    signature = parts.get("s")

    if not timestamp or not signature:
        raise WebhookSignatureError(
            "Moonpay-Signature-V2 header missing t= or s= component"
        )

    try:
        ts_int = int(timestamp)
    except ValueError as exc:
        raise WebhookSignatureError(f"invalid timestamp '{timestamp}'") from exc

    age = abs(int(time.time()) - ts_int)
    if age > max_age_seconds:
        raise WebhookSignatureError(
            f"webhook timestamp age {age}s exceeds max {max_age_seconds}s"
        )

    signed_payload = f"{timestamp}.{raw_body.decode('utf-8')}".encode("utf-8")
    expected = hmac.new(
        secret.encode("utf-8"), signed_payload, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise WebhookSignatureError("HMAC signature mismatch")


# ---------------------------------------------------------------------------
# Health probe (no secrets exposed)
# ---------------------------------------------------------------------------


def config_status() -> dict:
    """Return a non-sensitive snapshot of MoonPay configuration.

    Used by /api/v1/moonpay/health to confirm wiring without leaking keys.
    """
    return {
        "secret_key_configured": bool(MOONPAY_SECRET_KEY),
        "public_key_configured": bool(MOONPAY_PUBLIC_KEY),
        "webhook_secret_configured": bool(MOONPAY_WEBHOOK_SECRET),
        "api_base_url": MOONPAY_API_BASE_URL,
    }
