"""
Facilitator HTTP reliability primitives — Phase 2 SAAS_PRODUCTION_HARDENING.

Centralises the retry and timeout policy used for every HTTP call to the
Ultravioleta Facilitator (payments + ERC-8004 reputation).

Why a shared module
-------------------
Before this module:
  - A blip of network traffic would fail the whole payment/reputation flow.
  - `payment_dispatcher.py` had a `timeout=300` per facilitator call, which
    froze a request worker for 5 minutes and cascaded to other requests.

Policy
------
* Retry only on transient network issues:
    - ``httpx.TimeoutException`` (connect, read, write, pool)
    - ``httpx.NetworkError`` (DNS, connection refused, reset, etc.)
    - ``httpx.RemoteProtocolError`` (connection closed mid-stream)
    - 5xx responses (via ``httpx.HTTPStatusError`` where ``status_code >= 500``)
* Never retry on 4xx (bad request, auth, not-found, idempotency conflicts,
  validation errors). These are deterministic; retrying would only amplify
  the error.
* Never retry on 2xx — even if ``success=false`` in the JSON body. That is a
  business-level error, not a transient one.
* Never retry if the response JSON already contains a transaction hash. If
  the facilitator already broadcast a tx, retrying would risk double-settle.

Timeouts
--------
All facilitator httpx clients must use ``facilitator_timeout()`` (or a value
capped by ``FACILITATOR_TIMEOUT_SECONDS``, default 30s). Splitting
connect/read/write prevents a single stalled phase from dominating the
total budget. If a call needs longer, the retry policy plus facilitator
idempotency are the intended recovery path — not a larger timeout.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, TypeVar

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Timeout config
# ---------------------------------------------------------------------------

# Facilitator HTTP timeout cap in seconds. Any value greater than this will be
# clamped. Keep it aggressive so stalled facilitator calls do not monopolise
# request workers — retries + on-chain state queries are the recovery path.
FACILITATOR_TIMEOUT_SECONDS: int = int(
    os.environ.get("FACILITATOR_TIMEOUT_SECONDS", "30")
)


def facilitator_timeout(
    total: float | int | None = None,
) -> httpx.Timeout:
    """Return an ``httpx.Timeout`` suitable for facilitator calls.

    Args:
        total: Optional caller-requested total timeout. Capped at
            ``FACILITATOR_TIMEOUT_SECONDS`` so callers cannot accidentally
            request a 300s timeout.

    Returns:
        ``httpx.Timeout`` with ``connect=5`` and ``read=write=pool`` equal to
        the capped total.
    """
    if total is None:
        total = FACILITATOR_TIMEOUT_SECONDS
    total = min(float(total), float(FACILITATOR_TIMEOUT_SECONDS))
    # Connect phase gets a short budget (5s) so DNS / TCP handshake stalls
    # fail fast; read/write/pool share the rest. Total effective wall-clock
    # is bounded by ``total``.
    connect = min(5.0, total)
    return httpx.Timeout(connect=connect, read=total, write=total, pool=connect)


# ---------------------------------------------------------------------------
# Retry predicate
# ---------------------------------------------------------------------------

# Exceptions that indicate a genuine transient transport issue. httpx raises
# all of these as subclasses of ``httpx.HTTPError``, but we enumerate them
# explicitly so 4xx/validation errors do not accidentally match.
_TRANSIENT_TRANSPORT_EXC: tuple[type[BaseException], ...] = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
)


def _is_retryable(exc: BaseException) -> bool:
    """Return True if ``exc`` is a transient transport issue worth retrying.

    Retry rules:
      * Transient transport exceptions (timeout/network/remote-protocol): yes.
      * HTTPStatusError with ``status_code >= 500``: yes, unless the response
        JSON already contains a transaction hash (in which case the tx was
        broadcast and retrying would risk double-settle).
      * Everything else (including 4xx): no.
    """
    if isinstance(exc, _TRANSIENT_TRANSPORT_EXC):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status < 500:
            return False
        # 5xx — check for tx_hash in the body before retrying.
        try:
            body = exc.response.json()
        except Exception:
            return True
        if _response_has_tx_hash(body):
            logger.warning(
                "Facilitator returned %d but body contains tx_hash — "
                "not retrying to avoid double-settle.",
                status,
            )
            return False
        return True
    return False


def _response_has_tx_hash(body: Any) -> bool:
    """Return True if the response body already contains a tx hash.

    The facilitator can respond with {success: false, transaction: {hash:...}}
    when the on-chain tx went through but the response is flagged as error
    (e.g. a non-fatal post-settle hook failed). Retrying in that state would
    broadcast a second tx.
    """
    if not isinstance(body, dict):
        return False
    tx = body.get("transaction")
    if isinstance(tx, dict) and tx.get("hash"):
        return True
    if isinstance(tx, str) and tx:
        return True
    if body.get("txHash") or body.get("tx_hash") or body.get("transaction_hash"):
        return True
    return False


# ---------------------------------------------------------------------------
# Public decorator
# ---------------------------------------------------------------------------

F = TypeVar("F", bound=Callable[..., Any])


def facilitator_retry(fn: F) -> F:
    """Decorate an async function that calls the facilitator with retry policy.

    Example::

        @facilitator_retry
        async def _call_facilitator(...):
            async with httpx.AsyncClient(timeout=facilitator_timeout()) as c:
                resp = await c.post(...)
                resp.raise_for_status()
                ...

    Behaviour:
      * Up to 3 attempts.
      * Exponential backoff: 1s, 2s, 4s (capped at 10s).
      * Retries only on transient transport issues and retryable 5xx (see
        ``_is_retryable``).
      * Re-raises the last exception if all attempts fail.
    """
    return retry(  # type: ignore[return-value]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception(_is_retryable),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )(fn)


def raise_for_status_if_no_tx(response: httpx.Response) -> None:
    """Raise ``HTTPStatusError`` on 4xx/5xx unless the body already has a tx hash.

    Use this as a drop-in replacement for ``response.raise_for_status()`` in
    raw httpx paths where we want to trigger retries on 5xx but avoid
    retrying if the facilitator already broadcast a tx despite the error
    status. 4xx always raises (not retryable).
    """
    status = response.status_code
    if status < 400:
        return
    if status < 500:
        response.raise_for_status()
        return
    # 5xx — only raise if there is no tx hash. If there is one, the caller
    # will see the body and can decide how to treat it.
    try:
        body = response.json()
    except Exception:
        response.raise_for_status()
        return
    if _response_has_tx_hash(body):
        return
    response.raise_for_status()


__all__ = [
    "FACILITATOR_TIMEOUT_SECONDS",
    "facilitator_timeout",
    "facilitator_retry",
    "raise_for_status_if_no_tx",
]
