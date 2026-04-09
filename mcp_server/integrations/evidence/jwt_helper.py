"""Short-lived JWT for evidence presign authorization.

Bound to (task_id, submission_id, actor_id, exp). Signed by the MCP server
after ERC-8128 verification. Validated by the evidence presign Lambda
authorizer owned by Track D1.

Design contract (agreed with Track D1):
  - Algorithm: HS256 (shared secret lives in AWS Secrets Manager as
    EM_EVIDENCE_JWT_SECRET and is mounted into both the MCP task
    definition and the Lambda environment).
  - TTL: 5 minutes. The Lambda MUST reject anything older; the token is
    minted immediately before the client hits the presign endpoint.
  - Claims:
      task_id:        UUID of the task the evidence belongs to
      submission_id:  UUID of the (pending) submission
      actor_id:       executor_id of the caller (resolved from wallet)
      iat / exp:      unix seconds
      iss:            "execution-market-backend"
      aud:            "evidence-presign-lambda"

Phase 0 GR-0.4. See:
  docs/reports/security-audit-2026-04-07/40_FINAL_CONSOLIDATED_PLAN.md § 8.1
  docs/reports/security-audit-2026-04-07/specialists/SC_05_BACKEND_API.md
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

logger = logging.getLogger(__name__)

_JWT_ALGORITHM = "HS256"
_JWT_TTL_SECONDS = 300  # 5 minutes
_JWT_ISSUER = "execution-market-backend"
_JWT_AUDIENCE = "evidence-presign-lambda"


def _get_secret() -> str:
    """Fetch the signing secret from env at call time (not import time).

    Fetching at import time makes the module impossible to import in tests
    where the secret is set later via monkeypatch.
    """
    secret = os.environ.get("EM_EVIDENCE_JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "EM_EVIDENCE_JWT_SECRET not set — cannot mint evidence JWT. "
            "Set via AWS Secrets Manager in the ECS task definition."
        )
    return secret


def mint_evidence_jwt(
    task_id: str,
    submission_id: str,
    actor_id: str,
    *,
    ttl_seconds: Optional[int] = None,
) -> str:
    """Mint a short-lived JWT bound to (task, submission, actor).

    Args:
        task_id:       UUID of the task
        submission_id: UUID of the (pending) submission
        actor_id:      executor_id (or agent wallet) of the caller
        ttl_seconds:   Override default TTL (default 300s). Tests use this
                       to verify expiry enforcement.

    Returns:
        Encoded JWT string suitable for the `Authorization: Bearer <token>`
        header the client sends to the evidence presign Lambda.

    Raises:
        RuntimeError: if EM_EVIDENCE_JWT_SECRET is not configured.
        ValueError:   if any required claim is empty.
    """
    if not task_id:
        raise ValueError("task_id is required")
    if not submission_id:
        raise ValueError("submission_id is required")
    if not actor_id:
        raise ValueError("actor_id is required")

    secret = _get_secret()

    now = datetime.now(timezone.utc)
    ttl = ttl_seconds if ttl_seconds is not None else _JWT_TTL_SECONDS
    claims: Dict[str, Any] = {
        "task_id": str(task_id),
        "submission_id": str(submission_id),
        "actor_id": str(actor_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
        "iss": _JWT_ISSUER,
        "aud": _JWT_AUDIENCE,
    }

    token = jwt.encode(claims, secret, algorithm=_JWT_ALGORITHM)
    logger.debug(
        "Minted evidence JWT task=%s submission=%s actor=%s ttl=%ds",
        task_id,
        submission_id,
        str(actor_id)[:12],
        ttl,
    )
    return token


def decode_evidence_jwt(token: str) -> Dict[str, Any]:
    """Decode and verify an evidence JWT.

    Primarily used in tests — the Lambda authorizer in Track D1 does its
    own decoding with the same secret.

    Raises:
        jwt.ExpiredSignatureError: if the token is expired
        jwt.InvalidTokenError:     for any other validation failure
        RuntimeError:              if the secret is not configured
    """
    secret = _get_secret()
    return jwt.decode(
        token,
        secret,
        algorithms=[_JWT_ALGORITHM],
        audience=_JWT_AUDIENCE,
        issuer=_JWT_ISSUER,
    )
