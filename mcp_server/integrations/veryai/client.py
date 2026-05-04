"""VeryAI OAuth2 / OIDC client.

Implements the authorization-code + PKCE flow against api.very.org. Mirrors
the shape of integrations/worldid/client.py but speaks OAuth2 instead of
World ID's RP-signed nonce.

Endpoints (paths configurable via PlatformConfig keys):
  authorize:  GET  {api_base_url}{oauth2_authorize_path}
  token:      POST {api_base_url}{oauth2_token_path}     (form-urlencoded)
  userinfo:   GET  {api_base_url}{oauth2_userinfo_path}  (Bearer token)

Env vars (required when EM_VERYAI_ENABLED=true):
  VERYAI_CLIENT_ID
  VERYAI_CLIENT_SECRET
  VERYAI_REDIRECT_URI
  VERYAI_STATE_SECRET   (HMAC key for signed state token; HS256)

Security model:
  - PKCE binds the authorization request to the token exchange.
  - State token is a signed JWT containing executor_id + code_verifier + nonce
    + exp; verified on callback. Self-contained — no server-side cache needed.
  - id_token signature verification uses VeryAI JWKS (cached 1h).
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
import time
from dataclasses import dataclass
from typing import Optional

import httpx
import jwt
from jwt import PyJWKClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration (env-driven; missing values raise on demand, never silently)
# ---------------------------------------------------------------------------


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


VERYAI_CLIENT_ID = _env("VERYAI_CLIENT_ID")
VERYAI_CLIENT_SECRET = _env("VERYAI_CLIENT_SECRET")
VERYAI_REDIRECT_URI = _env("VERYAI_REDIRECT_URI")
VERYAI_STATE_SECRET = _env("VERYAI_STATE_SECRET")

# Default action string identifying our use of VeryAI.
DEFAULT_ACTION = "verify-worker"

# State token TTL — short window between /oauth-url and /callback.
STATE_TOKEN_TTL_SECONDS = 300  # 5 min

# JWKS cache TTL — ID-token signature keys.
JWKS_CACHE_TTL_SECONDS = 3600  # 1 hour


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthorizationRequest:
    """Bundle returned to the REST router for a fresh OAuth start."""

    url: str
    state: str  # signed JWT — opaque to caller
    code_verifier: str  # held in state JWT; surfaced for tests/diagnostics


@dataclass(frozen=True)
class TokenResult:
    """Token exchange result from VeryAI /oauth2/token."""

    access_token: str
    id_token: Optional[str]
    refresh_token: Optional[str]
    expires_in: int
    token_type: str


@dataclass(frozen=True)
class UserInfo:
    """Subset of /userinfo we trust as source of truth.

    Per Very's official docs (docs.very.org/developers/oauth2-integration and
    /developers/api-reference, captured 2026-05-04), `GET /userinfo` returns
    ONLY `sub`. The fact that Very issued an access token at all means the
    user completed a palm scan — Very's OAuth2 flow gates the authorization
    `code` issuance behind palm verification, so a valid sub == palm-verified.

    `verification_level` is therefore an internal label we default to "palm"
    when `sub` is present. We keep parsing it defensively from the response
    so any future Very extension (e.g. richer levels like "palm_single" or
    "palm_dual" surfaced as a non-standard claim) flows through unchanged.

    `sub` is stable per VeryAI account — used for anti-sybil uniqueness.
    """

    sub: str
    verification_level: str
    raw: dict


# ---------------------------------------------------------------------------
# PKCE helpers (RFC 7636)
# ---------------------------------------------------------------------------


def _b64url_no_pad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_pkce() -> tuple[str, str]:
    """Generate a PKCE (code_verifier, code_challenge) pair using S256.

    code_verifier: 96 chars of base64url alphabet (RFC 7636 allows 43–128).
    code_challenge: base64url-no-pad of SHA-256(code_verifier) — always 43 chars.
    """
    code_verifier = _b64url_no_pad(secrets.token_bytes(72))  # 72 bytes → 96 chars
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = _b64url_no_pad(digest)
    return code_verifier, code_challenge


# ---------------------------------------------------------------------------
# State token (signed JWT, self-contained)
# ---------------------------------------------------------------------------


class StateTokenError(Exception):
    """Raised when a callback presents an invalid or expired state token."""


def _require_state_secret() -> str:
    if not VERYAI_STATE_SECRET:
        raise ValueError(
            "VERYAI_STATE_SECRET not configured. "
            "Set it in .env.local or AWS Secrets Manager."
        )
    return VERYAI_STATE_SECRET


def create_state_token(
    executor_id: str,
    code_verifier: str,
    action: str = DEFAULT_ACTION,
    ttl_seconds: int = STATE_TOKEN_TTL_SECONDS,
) -> str:
    """Build a signed state JWT carrying everything we need on callback.

    The token is the only thing that survives the user's round-trip to
    VeryAI — it must contain enough context to validate + complete the flow
    without persistent server state.
    """
    secret = _require_state_secret()
    now = int(time.time())
    payload = {
        "executor_id": executor_id,
        "code_verifier": code_verifier,
        "action": action,
        "nonce": secrets.token_urlsafe(16),
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_state_token(token: str) -> dict:
    """Verify and decode a state JWT; raise StateTokenError on any failure."""
    secret = _require_state_secret()
    try:
        decoded = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["exp", "executor_id", "code_verifier"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise StateTokenError("state token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise StateTokenError(f"state token invalid: {exc}") from exc
    return decoded


# ---------------------------------------------------------------------------
# OAuth2 / OIDC operations
# ---------------------------------------------------------------------------


async def _resolved_paths() -> dict:
    """Pull base URL + paths from PlatformConfig.

    Lets us swap between sandbox and production without redeploying.
    """
    from config.platform_config import PlatformConfig

    return {
        "base": await PlatformConfig.get("veryai.api_base_url", "https://api.very.org"),
        "authorize": await PlatformConfig.get(
            "veryai.oauth2_authorize_path", "/oauth2/authorize"
        ),
        "token": await PlatformConfig.get("veryai.oauth2_token_path", "/oauth2/token"),
        "userinfo": await PlatformConfig.get(
            "veryai.oauth2_userinfo_path", "/oauth2/userinfo"
        ),
        # Scope is operator-tunable: per Very's /authorize error response,
        # only "openid" and "offline_access" are accepted. We default to
        # the minimum — "openid" alone — because we do a one-shot
        # verification per executor and never refresh, so refresh tokens
        # would only be data we hold without using. If Very later exposes
        # a custom verification scope (e.g. "veryai.verification") flip
        # this PlatformConfig key without a redeploy.
        "scope": await PlatformConfig.get("veryai.oauth2_scope", "openid"),
    }


async def get_authorization_url(
    executor_id: str,
    redirect_uri: Optional[str] = None,
    action: Optional[str] = None,
) -> AuthorizationRequest:
    """Build the authorize URL for the user's browser."""
    if not VERYAI_CLIENT_ID:
        raise ValueError("VERYAI_CLIENT_ID not configured")

    paths = await _resolved_paths()
    code_verifier, code_challenge = generate_pkce()
    state = create_state_token(
        executor_id=executor_id,
        code_verifier=code_verifier,
        action=action or DEFAULT_ACTION,
    )

    from urllib.parse import urlencode

    params = {
        "response_type": "code",
        "client_id": VERYAI_CLIENT_ID,
        "redirect_uri": redirect_uri or VERYAI_REDIRECT_URI,
        "scope": paths["scope"],
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    url = f"{paths['base'].rstrip('/')}{paths['authorize']}?{urlencode(params)}"
    return AuthorizationRequest(url=url, state=state, code_verifier=code_verifier)


async def exchange_code_for_token(
    code: str,
    code_verifier: str,
    redirect_uri: Optional[str] = None,
) -> TokenResult:
    """Trade an authorization code + PKCE verifier for tokens."""
    if not VERYAI_CLIENT_ID or not VERYAI_CLIENT_SECRET:
        raise ValueError("VeryAI client credentials not configured")

    paths = await _resolved_paths()
    url = f"{paths['base'].rstrip('/')}{paths['token']}"

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri or VERYAI_REDIRECT_URI,
        "code_verifier": code_verifier,
        "client_id": VERYAI_CLIENT_ID,
        "client_secret": VERYAI_CLIENT_SECRET,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            url,
            data=data,
            headers={"Accept": "application/json"},
        )

    if resp.status_code != 200:
        body = resp.text[:200]
        logger.error(
            "VeryAI token exchange failed: status=%d body=%s",
            resp.status_code,
            body,
        )
        raise httpx.HTTPStatusError(
            f"VeryAI token exchange returned {resp.status_code}: {body}",
            request=resp.request,
            response=resp,
        )

    payload = resp.json()
    return TokenResult(
        access_token=payload["access_token"],
        id_token=payload.get("id_token"),
        refresh_token=payload.get("refresh_token"),
        expires_in=int(payload.get("expires_in", 3600)),
        token_type=payload.get("token_type", "Bearer"),
    )


async def get_userinfo(access_token: str) -> UserInfo:
    """Fetch /userinfo with the access token; trust the response as canonical."""
    paths = await _resolved_paths()
    url = f"{paths['base'].rstrip('/')}{paths['userinfo']}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )

    if resp.status_code != 200:
        body = resp.text[:200]
        logger.error(
            "VeryAI /userinfo failed: status=%d body=%s",
            resp.status_code,
            body,
        )
        raise httpx.HTTPStatusError(
            f"VeryAI /userinfo returned {resp.status_code}: {body}",
            request=resp.request,
            response=resp,
        )

    raw = resp.json()
    sub = str(raw.get("sub") or "").strip()
    if not sub:
        raise ValueError("VeryAI /userinfo returned no 'sub' — cannot identify user")

    # Per Very's OAuth2 docs, /userinfo only contractually returns `sub`.
    # An access token can only exist after a successful palm scan, so a
    # valid sub IS the palm-verified signal — we default the internal label
    # to "palm". The defensive `.get()` chain stays so any future Very
    # extension (richer level claims) flows through without code changes.
    level = str(
        raw.get("verification_level") or raw.get("veryai_verification_level") or "palm"
    )
    return UserInfo(sub=sub, verification_level=level, raw=raw)


# ---------------------------------------------------------------------------
# ID-token verification (JWKS, cached 1h)
# ---------------------------------------------------------------------------


_jwks_client: Optional[PyJWKClient] = None
_jwks_fetched_at: float = 0.0


def _jwks_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/.well-known/jwks.json"


async def verify_id_token(id_token: str) -> dict:
    """Verify the OIDC ID token against VeryAI's published JWKS.

    Returns the decoded claims on success; raises jwt.InvalidTokenError on
    any signature / claim failure. PyJWKClient is sync; calls under the hood
    are infrequent (≤ once per hour after warm-up) so we accept the cost
    rather than wiring a separate async JWKS fetcher.
    """
    global _jwks_client, _jwks_fetched_at  # noqa: PLW0603 — module cache by design

    paths = await _resolved_paths()
    now = time.time()
    if _jwks_client is None or (now - _jwks_fetched_at) > JWKS_CACHE_TTL_SECONDS:
        _jwks_client = PyJWKClient(_jwks_url(paths["base"]))
        _jwks_fetched_at = now

    signing_key = _jwks_client.get_signing_key_from_jwt(id_token).key
    return jwt.decode(
        id_token,
        signing_key,
        algorithms=["RS256", "ES256"],
        audience=VERYAI_CLIENT_ID,
        options={"require": ["exp", "iat", "sub"]},
    )
