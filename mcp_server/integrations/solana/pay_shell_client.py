"""pay.sh control-plane client (Phase 2.2).

Thin async wrapper over the control endpoints that pay.sh exposes for
session orchestration. Does NOT sign vouchers — pay.sh handles voucher
verification + settlement internally. We only:

  - check `/_health`
  - read session metadata (`GET /_sessions/{id}`)
  - subscribe to the session SSE event stream (`/_sessions/{id}/events`)
  - request a graceful close (`POST /_sessions/{id}/close-now`)

Why this is small: per D-15, pay.sh owns the SDK + facilitator internally.
The Python side only needs to coordinate task lifecycle ↔ channel lifecycle
(see services/task_channel_binding.py in Phase 2.5).

Security note: this client never holds keys. The facilitator keypair lives
only in pay.sh's process memory (loaded from secrets manager at boot, see
infrastructure/terraform/payshell.tf).
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import AsyncIterator, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PAYSHELL_URL = os.environ.get("EM_PAYSHELL_URL", "http://127.0.0.1:7081")
PAYSHELL_TIMEOUT_SECONDS = float(os.environ.get("EM_PAYSHELL_TIMEOUT", "30"))


# ---------------------------------------------------------------------------
# Models — match the JSON shapes that pay.sh emits (see upstream
# solana-foundation/pay docs / SOLANA_MPP_pay research note).
# ---------------------------------------------------------------------------


class SessionMetadata(BaseModel):
    """Snapshot of an active or settled MPP session as exposed by pay.sh."""

    channel_id: str = Field(alias="channelId")
    status: str  # "open" | "draining" | "settled" | "expired" | "errored"
    cap_usdc: Decimal = Field(alias="capUsdc")
    accepted_cumulative_usdc: Decimal = Field(alias="acceptedCumulativeUsdc")
    voucher_count: int = Field(alias="voucherCount")
    payer: str
    payee: str
    settlement_tx_hash: Optional[str] = Field(default=None, alias="settlementTxHash")
    opened_at: str = Field(alias="openedAt")
    settled_at: Optional[str] = Field(default=None, alias="settledAt")

    model_config = {"populate_by_name": True}


class CloseResult(BaseModel):
    channel_id: str = Field(alias="channelId")
    settlement_tx_hash: str = Field(alias="settlementTxHash")
    final_cumulative_usdc: Decimal = Field(alias="finalCumulativeUsdc")
    refund_usdc: Decimal = Field(alias="refundUsdc")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class PayShellError(Exception):
    """Raised when pay.sh returns a non-2xx status the caller cannot recover."""


class PayShellClient:
    """Async control-plane client for pay.sh.

    Reuses a single `httpx.AsyncClient`. Instantiate once per process or
    grab the module-level singleton via `get_pay_shell_client()`.
    """

    def __init__(
        self,
        base_url: str = PAYSHELL_URL,
        timeout: float = PAYSHELL_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout, connect=5.0),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    # ---- Health -----------------------------------------------------------

    async def health(self) -> dict:
        """Returns pay.sh's health payload. Raises PayShellError on non-200."""
        resp = await self._client.get("/_health")
        if resp.status_code != 200:
            raise PayShellError(f"pay.sh /_health returned {resp.status_code}")
        return resp.json()

    # ---- Session metadata -------------------------------------------------

    async def get_session(self, channel_id: str) -> SessionMetadata:
        resp = await self._client.get(f"/_sessions/{channel_id}")
        if resp.status_code == 404:
            raise PayShellError(f"session {channel_id} not found")
        if resp.status_code != 200:
            raise PayShellError(
                f"pay.sh /_sessions/{channel_id} returned {resp.status_code}: {resp.text[:200]}"
            )
        return SessionMetadata.model_validate(resp.json())

    # ---- Close ------------------------------------------------------------

    async def close_session(
        self,
        channel_id: str,
        *,
        final_increment_uusdc: Optional[int] = None,
    ) -> CloseResult:
        """Request a graceful close + settlement.

        If `final_increment_uusdc` is provided the facilitator will accept
        one last voucher equal to that increment before closing — useful
        when the worker has a final tick pending.

        pay.sh returns immediately after dispatching settleAndFinalize.
        The on-chain TX hash may take 1-3s to confirm — the SSE event
        stream (subscribe_events) emits `settlement_complete` when finalized.
        """
        payload: dict = {}
        if final_increment_uusdc is not None:
            payload["finalIncrementUusdc"] = final_increment_uusdc
        resp = await self._client.post(
            f"/_sessions/{channel_id}/close-now",
            json=payload,
        )
        if resp.status_code not in (200, 202):
            raise PayShellError(
                f"close session {channel_id} failed: {resp.status_code} {resp.text[:200]}"
            )
        return CloseResult.model_validate(resp.json())

    # ---- SSE event stream -------------------------------------------------

    @asynccontextmanager
    async def subscribe_events(
        self,
        channel_id: str,
    ) -> AsyncIterator[AsyncIterator[dict]]:
        """Yield an async iterator over SSE events from pay.sh.

        Each event is a dict with at least `event` and `data` keys.
        Events emitted by pay.sh (see upstream docs):
          - `session_open`
          - `voucher_accepted`
          - `session_close`
          - `settlement_complete`
          - `error`

        Usage:
            async with client.subscribe_events(channel_id) as stream:
                async for event in stream:
                    ...
        """
        # httpx 0.27 stream() is itself an async context manager — we wrap it
        # so callers don't need to know about httpx specifics.
        async with self._client.stream(
            "GET", f"/_sessions/{channel_id}/events"
        ) as resp:
            if resp.status_code != 200:
                raise PayShellError(
                    f"SSE subscribe {channel_id} returned {resp.status_code}"
                )

            async def _iter() -> AsyncIterator[dict]:
                event_type: Optional[str] = None
                async for raw_line in resp.aiter_lines():
                    if not raw_line:
                        # End-of-event delimiter (blank line per SSE spec).
                        continue
                    if raw_line.startswith("event:"):
                        event_type = raw_line[len("event:") :].strip()
                        continue
                    if raw_line.startswith("data:"):
                        data = raw_line[len("data:") :].strip()
                        try:
                            parsed = json.loads(data) if data else {}
                        except json.JSONDecodeError:
                            logger.warning(
                                "pay.sh SSE non-JSON data on %s: %s",
                                channel_id,
                                data[:120],
                            )
                            continue
                        yield {"event": event_type or "message", "data": parsed}
                        event_type = None

            yield _iter()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


_singleton: Optional[PayShellClient] = None


def get_pay_shell_client() -> PayShellClient:
    """Lazily build and reuse a single client. Don't `aclose` on each call."""
    global _singleton
    if _singleton is None:
        _singleton = PayShellClient()
    return _singleton
