"""Evidence presign API Gateway JWT authorizer.

Phase 0 security guardrail GR-0.4 (CLOUD-003).

Validates a short-lived HS256 JWT issued by the backend MCP server after
ERC-8128 verification. The JWT is bound to (task_id, submission_id, actor_id,
exp) and must match the task_id query/path parameter when present.

Token flow:
  1. Agent signs ERC-8128 auth against the MCP server.
  2. MCP mints a scoped HS256 JWT via `mint_evidence_jwt(task_id, submission_id, actor_id)`
     (Track D2 backend helper).
  3. Client presents the JWT in `Authorization: Bearer <token>` to the
     evidence API Gateway.
  4. This authorizer verifies the signature, expiry, required claims, and
     cross-checks task_id against the request before allowing the Lambda
     integration to run.

The authorizer is intentionally zero-dependency (Python stdlib only) so the
Lambda ZIP stays identical in shape to `evidence_presign.py` — no pip, no
layer, no build step. HS256 is implemented directly with `hmac` + `hashlib`.

HTTP API Authorizer payload format: v2.0 simple responses
(`enable_simple_responses = true` in Terraform).

Secret resolution order (first hit wins):
  1. Environment variable `EM_EVIDENCE_JWT_SECRET` (used by unit tests and
     local debugging).
  2. AWS Secrets Manager, secret ID from `EM_EVIDENCE_JWT_SECRET_ARN`
     (production path — Terraform injects the ARN).

The Lambda execution role is granted `secretsmanager:GetSecretValue` on
`em/evidence-jwt-secret` via evidence.tf. The secret is fetched once at
cold start and cached in module scope.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional


_SECRET_ENV = "EM_EVIDENCE_JWT_SECRET"
_SECRET_ARN_ENV = "EM_EVIDENCE_JWT_SECRET_ARN"
_ALG = "HS256"
_REQUIRED_CLAIMS = ("task_id", "submission_id", "actor_id", "exp")

_DENY: Dict[str, Any] = {"isAuthorized": False}

# Module-level cache for the resolved secret (populated on cold start).
_cached_secret: Optional[str] = None


def _load_secret() -> Optional[str]:
    """Resolve the HS256 signing secret, caching the result across invocations."""
    global _cached_secret
    if _cached_secret is not None:
        return _cached_secret

    # Prefer direct env var (tests, local debug, small deploys).
    env_value = os.environ.get(_SECRET_ENV)
    if env_value:
        _cached_secret = env_value
        return _cached_secret

    # Fall back to AWS Secrets Manager using the ARN injected by Terraform.
    secret_arn = os.environ.get(_SECRET_ARN_ENV)
    if not secret_arn:
        return None

    try:
        import boto3  # imported lazily so tests do not need boto3 installed

        client = boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=secret_arn)
    except Exception:
        return None

    secret_value = response.get("SecretString")
    if not secret_value:
        return None
    _cached_secret = secret_value
    return _cached_secret


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _decode_hs256(token: str, secret: str) -> Optional[Dict[str, Any]]:
    """Minimal HS256 JWT decoder. Returns claims dict on success, None on failure."""
    if not token or token.count(".") != 2:
        return None
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        header_bytes = _b64url_decode(header_b64)
        payload_bytes = _b64url_decode(payload_b64)
        signature = _b64url_decode(signature_b64)
    except (ValueError, base64.binascii.Error):
        return None

    try:
        header = json.loads(header_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    if not isinstance(header, dict):
        return None
    if header.get("alg") != _ALG:
        return None
    if header.get("typ") not in (None, "JWT"):
        return None

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, signature):
        return None

    try:
        claims = json.loads(payload_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(claims, dict):
        return None
    return claims


def _extract_bearer(event: Dict[str, Any]) -> str:
    headers = event.get("headers") or {}
    # HTTP API lowercases header keys, but be defensive.
    auth = (
        headers.get("authorization")
        or headers.get("Authorization")
        or ""
    )
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return auth.strip()


def _route_task_ids(event: Dict[str, Any]) -> list[str]:
    """Collect every task_id the downstream Lambda might read.

    The current routes (GET /upload-url, GET /download-url) use a query-string
    parameter. Path parameters are included for forward-compatibility: if the
    API Gateway route is ever templated (e.g. GET /tasks/{task_id}/upload-url),
    the path variant will also be checked. Every value collected here must
    match the JWT task_id claim, so an attacker cannot smuggle a mismatching
    id through a parameter the authorizer doesn't inspect.
    """
    candidates: list[str] = []

    path_params = event.get("pathParameters") or {}
    for key in ("task_id", "taskId"):
        value = path_params.get(key)
        if value:
            candidates.append(str(value))

    qs = event.get("queryStringParameters") or {}
    for key in ("taskId", "task_id"):
        value = qs.get(key)
        if value:
            candidates.append(str(value))

    return candidates


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    secret = _load_secret()
    if not secret:
        # Fail closed if the secret is not wired — never allow open access.
        return _DENY

    token = _extract_bearer(event)
    if not token:
        return _DENY

    claims = _decode_hs256(token, secret)
    if claims is None:
        return _DENY

    for required in _REQUIRED_CLAIMS:
        if required not in claims:
            return _DENY

    # Expiry check (seconds since epoch, as the backend mints it)
    try:
        exp = int(claims["exp"])
    except (TypeError, ValueError):
        return _DENY
    if exp < int(time.time()):
        return _DENY

    # Optional "not before"
    nbf = claims.get("nbf")
    if nbf is not None:
        try:
            if int(nbf) > int(time.time()):
                return _DENY
        except (TypeError, ValueError):
            return _DENY

    # Cross-check: EVERY task_id the downstream Lambda might read must match
    # the JWT claim. This prevents a token minted for task A from being
    # replayed against task B — and prevents smuggling a mismatching id
    # through a parameter the authorizer doesn't inspect.
    jwt_tid = str(claims["task_id"])
    for candidate in _route_task_ids(event):
        if candidate != jwt_tid:
            return _DENY

    return {
        "isAuthorized": True,
        "context": {
            "task_id": jwt_tid,
            "submission_id": str(claims["submission_id"]),
            "actor_id": str(claims["actor_id"]),
        },
    }


# Alias to match the `handler` naming used by the sibling Lambda.
handler = lambda_handler
