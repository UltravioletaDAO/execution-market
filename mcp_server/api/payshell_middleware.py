"""pay.sh session-context middleware (Phase 2.4).

When pay.sh proxies a request to the EM backend it stamps four headers that
describe the active MPP session. We surface those headers as a typed object
on `request.state.payshell` so route handlers and the payment dispatcher's
`solana_session` branch can read session context without re-parsing.

Headers emitted by pay.sh (matches solana-foundation/pay control-plane spec):

    x-payshell-channel-id:        <base58 channel pubkey>
    x-payshell-cumulative-usdc:   <decimal string, e.g. "0.000003">
    x-payshell-payer:             <base58 payer pubkey>
    x-payshell-status:            open | draining | settled | expired | errored

We do NOT verify the headers — pay.sh already verified the voucher signature
and timing on the wire, and the headers are stamped INSIDE pay.sh's process
(an attacker cannot forge them unless they have already breached the
sidecar). Route handlers treat `request.state.payshell` as authoritative
context, not as untrusted input.

Master switch: `EM_PAYSHELL_ENABLED` (env var, default `false`).
  - When `false`, the middleware short-circuits and `request.state.payshell`
    is always `None`. This keeps the legacy direct-routed mcp-server task
    behavior identical to pre-Phase-2.
  - When `true`, the middleware parses headers on every request. Absent
    headers (e.g., a request that bypassed pay.sh) still produce
    `request.state.payshell = None` — handlers must handle both cases.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Master switch — read once at import time so the middleware is a cheap
# pass-through when EM_PAYSHELL_ENABLED=false. Toggling at runtime requires
# a task restart, which is fine — the flag is set via ECS task definition.
# ---------------------------------------------------------------------------

PAYSHELL_ENABLED: bool = os.environ.get("EM_PAYSHELL_ENABLED", "false").lower() in (
    "1",
    "true",
    "yes",
)


# Valid status values per pay.sh upstream docs. We accept-and-pass anything
# else (forward compatibility) but log a warning so we notice drift.
_KNOWN_STATUSES = frozenset({"open", "draining", "settled", "expired", "errored"})


@dataclass(frozen=True)
class PayShellSessionContext:
    """Snapshot of pay.sh's MPP session context for the current request.

    All fields are Optional because pay.sh may stamp a partial header set on
    requests that don't open a session (e.g., health checks, OPTIONS
    preflights, 402 challenges that haven't authenticated yet). Handlers
    should treat the context as "best-effort metadata" — the
    `payment_dispatcher.solana_session` branch checks every field before
    trusting the session.
    """

    channel_id: Optional[str]
    cumulative_usdc: Optional[Decimal]
    payer: Optional[str]
    status: Optional[str]

    @property
    def is_active(self) -> bool:
        """True when pay.sh signals an open or draining session."""
        return self.status in ("open", "draining")

    @property
    def is_settled(self) -> bool:
        return self.status == "settled"


class PayShellSessionMiddleware(BaseHTTPMiddleware):
    """Parse pay.sh session headers into `request.state.payshell`.

    Installation order: AFTER RequestLoggingMiddleware (so we have a
    request_id to log against) and AFTER RateLimitMiddleware (so the
    middleware doesn't run for rate-limited responses). See
    `add_payshell_middleware()` below for the wiring.
    """

    # Header names are case-insensitive per RFC 9110; we use lower-case here
    # because Starlette normalizes headers to lower-case on the request
    # object regardless of what pay.sh emits on the wire.
    HEADER_CHANNEL_ID = "x-payshell-channel-id"
    HEADER_CUMULATIVE = "x-payshell-cumulative-usdc"
    HEADER_PAYER = "x-payshell-payer"
    HEADER_STATUS = "x-payshell-status"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Master switch — no-op when payshell is disabled. We still set the
        # attribute to None so downstream handlers can rely on its existence
        # via `getattr(request.state, "payshell", None)` without branching
        # on the env var themselves.
        if not PAYSHELL_ENABLED:
            request.state.payshell = None
            return await call_next(request)

        headers = request.headers
        channel_id = headers.get(self.HEADER_CHANNEL_ID)

        # Fast path: no channel id ⇒ this request did not come from pay.sh
        # (or pay.sh chose not to stamp a session, e.g., health probes).
        if not channel_id:
            request.state.payshell = None
            return await call_next(request)

        cumulative_raw = headers.get(self.HEADER_CUMULATIVE)
        payer = headers.get(self.HEADER_PAYER)
        status = headers.get(self.HEADER_STATUS)

        cumulative_usdc: Optional[Decimal] = None
        if cumulative_raw:
            try:
                cumulative_usdc = Decimal(cumulative_raw)
            except (InvalidOperation, ValueError):
                # Malformed decimal — log and drop. Don't 400 the request:
                # pay.sh might be emitting a newer format we don't recognize,
                # and the legacy path through the same handler still works.
                logger.warning(
                    "payshell: malformed %s header value=%r channel=%s",
                    self.HEADER_CUMULATIVE,
                    cumulative_raw,
                    channel_id,
                )

        if status and status not in _KNOWN_STATUSES:
            logger.warning(
                "payshell: unknown status=%r channel=%s — accepting forward-compat",
                status,
                channel_id,
            )

        ctx = PayShellSessionContext(
            channel_id=channel_id,
            cumulative_usdc=cumulative_usdc,
            payer=payer,
            status=status,
        )
        request.state.payshell = ctx

        return await call_next(request)


def add_payshell_middleware(app: FastAPI) -> None:
    """Attach the pay.sh middleware to a FastAPI app.

    Called from `mcp_server/main.py` AFTER `add_api_middleware()` so this
    middleware sits closer to the route handlers in the stack and only runs
    once rate limiting + idempotency have passed. That ordering matters: we
    don't want to populate session context on a request that's about to be
    short-circuited with a 429 response.
    """
    app.add_middleware(PayShellSessionMiddleware)
    logger.info(
        "PayShellSessionMiddleware installed (EM_PAYSHELL_ENABLED=%s)", PAYSHELL_ENABLED
    )


__all__ = [
    "PAYSHELL_ENABLED",
    "PayShellSessionContext",
    "PayShellSessionMiddleware",
    "add_payshell_middleware",
]
