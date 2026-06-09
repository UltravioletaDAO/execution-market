"""Taxímetro: SSE relay of pay.sh MPP session events (Phase 2.8).

  GET /api/v1/taximetro/{channel_id}/stream   — SSE stream of voucher ticks

This router proxies pay.sh's native SSE endpoint
(`/_sessions/{channel_id}/events`) to dashboard/robot UI clients. Two
reasons we relay instead of letting the UI hit pay.sh directly:

  1. **Auth**: pay.sh sits behind the internal loopback on ECS; the UI
     never has a path to its port (7081 is not on the ALB). The relay
     terminates on the public API (mcp.execution.market) which already
     has CORS, rate limiting, and authentication.

  2. **Persistence**: we tee every event into `mpp_session_events`
     (migration 108) so reconnects can replay history without depending
     on pay.sh remembering past events. pay.sh streams forward-only;
     `replay` query param walks the DB mirror first.

Master switch: `EM_PAYSHELL_ENABLED`. When unset/false the route is not
registered, so `/api/v1/taximetro/*` returns 404 instead of 503 — same
gating pattern as VeryAI / MoonPay.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from ..auth import AgentAuth, verify_agent_auth_write

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/taximetro", tags=["Taxímetro"])


# ---------------------------------------------------------------------------
# Config — read once at import; relay reconnects don't re-read env.
# ---------------------------------------------------------------------------
PAYSHELL_ENABLED: bool = os.environ.get("EM_PAYSHELL_ENABLED", "false").lower() in (
    "1",
    "true",
    "yes",
)

# Max events to walk back when a client requests `?replay=true`. Keeps the
# initial flush bounded so a client reconnecting after hours doesn't pull
# a multi-megabyte page on the first chunk.
MAX_REPLAY_EVENTS = int(os.environ.get("EM_TAXIMETRO_REPLAY_LIMIT", "200"))

# Solana pubkey (base58, 32-44 chars). Enforced at this boundary AND inside
# PayShellClient so a hostile channel_id cannot inject upstream path segments
# (e.g. "..%2F_admin") into pay.sh control-plane URLs. (Security review 2026-06-04.)
_CHANNEL_ID_RE = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}")


def _validate_channel_id(channel_id: str) -> None:
    if not channel_id or not _CHANNEL_ID_RE.fullmatch(channel_id):
        raise HTTPException(status_code=400, detail="invalid channel_id")


def _wallets_match(a: Optional[str], b: Optional[str]) -> bool:
    """Case-insensitive compare of two wallet identifiers (None-safe)."""
    if not a or not b:
        return False
    return a.lower() == b.lower()


async def _authorize_channel_access(channel_id: str, auth: AgentAuth) -> None:
    """Enforce that ``auth`` owns the task/channel behind ``channel_id`` (F-10).

    The taximetro relays a payment voucher stream — exposing it to any caller
    that merely knows a base58 channel_id is an IDOR (the channel_id appears in
    on-chain data and SSE URLs). We resolve the channel to its task via
    task_channel_bindings (migration 108) and authorize the caller as either:

      - the **publisher** — ``task.agent_id`` matches the caller's agent_id or
        wallet (the canonical task-ownership check, mirroring routers/tasks.py),
        or ``task.human_wallet`` matches the caller's wallet (H2H publisher); or
      - the **assigned worker** — ``task.executor_id`` resolves to an executor
        whose ``wallet_address`` equals the caller's wallet; or
      - a wallet that equals the channel's recorded ``payer``/``payee`` (covers
        a chain-native signer whose address is the on-chain counterparty).

    Fails CLOSED: if the binding, the task, or ownership cannot be established,
    raise 403. A missing binding means the caller cannot prove ownership — we
    do not leak the stream on the benefit of the doubt.
    """
    from services.task_channel_binding import _lookup_binding

    binding = _lookup_binding(channel_id)
    if not binding:
        logger.warning(
            "SECURITY_AUDIT action=taximetro.access_denied reason=no_binding "
            "channel=%s agent=%s",
            channel_id,
            auth.agent_id,
        )
        raise HTTPException(status_code=403, detail="not authorized for this channel")

    caller_wallet = getattr(auth, "wallet_address", None)

    # Channel counterparty match (payer/payee are base58; a Solana-native
    # caller authenticating with that same address is the counterparty).
    if _wallets_match(caller_wallet, binding.get("payer")) or _wallets_match(
        caller_wallet, binding.get("payee")
    ):
        return

    task_id = binding.get("task_id")
    if task_id:
        try:
            from supabase_client import get_task

            task = await get_task(task_id)
        except Exception as e:
            logger.warning(
                "taximetro ownership task lookup failed channel=%s task=%s: %s",
                channel_id,
                task_id,
                e,
            )
            task = None

        if task:
            # Publisher: agent_id matches caller agent_id or wallet (mirrors
            # routers/tasks.py), or human_wallet matches caller wallet (H2H).
            task_agent = task.get("agent_id")
            if (
                _wallets_match(task_agent, auth.agent_id)
                or _wallets_match(task_agent, caller_wallet)
                or _wallets_match(task.get("human_wallet"), caller_wallet)
            ):
                return

            # Assigned worker: executor_id -> executors.wallet_address.
            executor_id = task.get("executor_id")
            if (
                executor_id
                and caller_wallet
                and _executor_owns(executor_id, caller_wallet)
            ):
                return

    logger.warning(
        "SECURITY_AUDIT action=taximetro.access_denied reason=not_owner "
        "channel=%s task=%s agent=%s",
        channel_id,
        task_id,
        auth.agent_id,
    )
    raise HTTPException(status_code=403, detail="not authorized for this channel")


def _executor_owns(executor_id: str, caller_wallet: str) -> bool:
    """True if ``executor_id`` resolves to an executor with ``caller_wallet``."""
    try:
        import supabase_client as db

        resp = (
            db.get_client()
            .table("executors")
            .select("wallet_address")
            .eq("id", executor_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return False
        return _wallets_match(rows[0].get("wallet_address"), caller_wallet)
    except Exception as e:
        logger.warning(
            "taximetro executor lookup failed executor=%s: %s", executor_id, e
        )
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sse_format(event_type: str, data: dict) -> bytes:
    """Encode a dict as one SSE frame.

    Per the SSE spec, an event is `event:<type>\\ndata:<json>\\n\\n`.
    The blank line at the end is the frame terminator — browsers buffer
    until they see it. We always force a trailing newline pair.
    """
    payload = json.dumps(data, separators=(",", ":"), default=str)
    return f"event: {event_type}\ndata: {payload}\n\n".encode("utf-8")


async def _replay_from_db(channel_id: str, limit: int) -> AsyncIterator[bytes]:
    """Yield historical events for a channel from mpp_session_events.

    Reads forward-chronologically (oldest first) so the UI replays in
    the same order it would receive a live stream. Failures here are
    logged but never break the stream — the client can still consume
    live events even if replay fails.
    """
    try:
        import supabase_client as db

        supabase = db.get_client()
        resp = (
            supabase.table("mpp_session_events")
            .select(
                "event_type, cumulative_uusdc, voucher_index, tx_hash, payload, received_at"
            )
            .eq("channel_id", channel_id)
            .order("received_at", desc=False)
            .limit(limit)
            .execute()
        )
        for row in resp.data or []:
            yield _sse_format(
                row.get("event_type") or "message",
                {
                    "replay": True,
                    "channel_id": channel_id,
                    "received_at": row.get("received_at"),
                    "cumulative_uusdc": row.get("cumulative_uusdc"),
                    "voucher_index": row.get("voucher_index"),
                    "tx_hash": row.get("tx_hash"),
                    "payload": row.get("payload") or {},
                },
            )
    except Exception as e:
        logger.warning("taximetro replay failed channel=%s: %s", channel_id, e)


async def _live_from_payshell(channel_id: str) -> AsyncIterator[bytes]:
    """Yield live events from pay.sh, teeing each one into the DB mirror.

    Uses the PayShellClient.subscribe_events context manager (Phase 2.2).
    Errors propagate as an `event: error` frame so the UI can react —
    we don't tear down the stream because pay.sh may reconnect shortly.
    """
    from integrations.solana.pay_shell_client import (
        get_pay_shell_client,
        PayShellError,
    )

    client = get_pay_shell_client()
    try:
        async with client.subscribe_events(channel_id) as stream:
            async for event in stream:
                event_type = event.get("event") or "message"
                data = event.get("data") or {}
                # Tee to DB — non-blocking. Best-effort: if the mirror
                # write fails the UI still gets the live frame.
                asyncio.create_task(_persist_event(channel_id, event_type, data))
                yield _sse_format(event_type, data)
    except PayShellError as e:
        logger.warning("taximetro live stream failed channel=%s: %s", channel_id, e)
        yield _sse_format(
            "error",
            {"channel_id": channel_id, "error": str(e), "source": "payshell"},
        )


async def _persist_event(channel_id: str, event_type: str, data: dict) -> None:
    """Append one SSE event to the DB mirror. Never raises.

    Maps pay.sh's event names to the CHECK-allowed values from migration
    108. Unknown events are recorded as `error` with the original name
    in metadata so we don't silently drop forward-compat additions.
    """
    try:
        import supabase_client as db

        supabase = db.get_client()

        # Normalize event type to migration 108's allowed values.
        allowed = {
            "session_open",
            "voucher_accepted",
            "session_close",
            "settlement_complete",
            "error",
        }
        normalized = event_type if event_type in allowed else "error"

        # Pull common fields out of the payload when present.
        cumulative = (
            data.get("cumulativeUusdc")
            or data.get("cumulative_uusdc")
            or data.get("cumulative")
        )
        voucher_idx = data.get("voucherIndex") or data.get("voucher_index")
        tx_hash = data.get("txHash") or data.get("tx_hash") or data.get("signature")
        task_id = data.get("taskId") or data.get("task_id")

        row = {
            "channel_id": channel_id,
            "task_id": task_id,
            "event_type": normalized,
            "cumulative_uusdc": cumulative,
            "voucher_index": voucher_idx,
            "tx_hash": tx_hash,
            "payload": data,
        }
        supabase.table("mpp_session_events").insert(row).execute()
    except Exception as e:
        # Stay silent on the user-visible stream; just log the drop.
        logger.warning(
            "mpp_session_events insert failed channel=%s event=%s: %s",
            channel_id,
            event_type,
            e,
        )


# ---------------------------------------------------------------------------
# Routes
#
# SECURITY (F-10, MASTER_PLAN_ONRAMP_H2H_POST_AUDIT_2026-06-05 Task 4.3):
# /stream and /history now require caller auth (verify_agent_auth_write —
# ERC-8128 wallet signing, the EM standard; fails closed on missing creds)
# AND a channel-ownership check (_authorize_channel_access) that resolves the
# channel to its task via task_channel_bindings and authorizes only the
# payer/payee, the task publisher, or the assigned worker. This closes the
# IDOR where any client knowing a base58 channel_id could read the voucher
# stream. The router stays feature-gated OFF by default (EM_PAYSHELL_ENABLED,
# returns 404) — the documented pre-flag blocker is now resolved, but the
# flag should still only flip on after the rest of the go/no-go checklist is
# green. /health stays unauthenticated (no per-channel data).
# ---------------------------------------------------------------------------


@router.get("/{channel_id}/stream")
async def taximetro_stream(
    channel_id: str,
    request: Request,
    replay: bool = Query(
        default=True,
        description="If true, flush historical events from the DB mirror before live stream starts.",
    ),
    replay_limit: Optional[int] = Query(
        default=None,
        ge=1,
        le=1000,
        description="Override max replay events (capped at EM_TAXIMETRO_REPLAY_LIMIT).",
    ),
    auth: AgentAuth = Depends(verify_agent_auth_write),
):
    """SSE stream of pay.sh MPP session events for a single channel.

    Sequence on each connection:
      1. (optional) Replay historical events from mpp_session_events
      2. Subscribe to pay.sh /_sessions/{channel_id}/events
      3. For each pay.sh event: persist + relay

    Disconnects mid-stream are normal — the client reconnects with
    `replay=true` and the gap is filled from the DB mirror. Idempotency
    on the mirror means a client retrying inside the replay window may
    see a few duplicates, but the SSE protocol's `id:` field is what
    browsers use for last-event-id replay anyway. We don't set `id:`
    today; clients should de-dupe by tx_hash on settlement events.
    """
    _validate_channel_id(channel_id)
    await _authorize_channel_access(channel_id, auth)

    effective_limit = min(replay_limit or MAX_REPLAY_EVENTS, MAX_REPLAY_EVENTS)

    async def generator() -> AsyncIterator[bytes]:
        # Initial frame so clients know the connection is live even
        # before the first event lands. Useful for spinners/timeouts.
        yield _sse_format(
            "hello",
            {
                "channel_id": channel_id,
                "replay": replay,
                "replay_limit": effective_limit,
            },
        )

        if replay:
            async for frame in _replay_from_db(channel_id, effective_limit):
                if await request.is_disconnected():
                    return
                yield frame

        async for frame in _live_from_payshell(channel_id):
            if await request.is_disconnected():
                return
            yield frame

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",  # tell nginx-style proxies not to buffer
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        generator(), media_type="text/event-stream", headers=headers
    )


@router.get("/{channel_id}/history")
async def taximetro_history(
    channel_id: str,
    limit: int = Query(default=50, ge=1, le=1000),
    auth: AgentAuth = Depends(verify_agent_auth_write),
):
    """JSON dump of recent events for a channel. Used by tests + admin UI.

    Not an SSE endpoint — just a one-shot fetch from the DB mirror.
    Returns events in chronological order (oldest first).
    """
    _validate_channel_id(channel_id)
    await _authorize_channel_access(channel_id, auth)
    try:
        import supabase_client as db

        supabase = db.get_client()
        resp = (
            supabase.table("mpp_session_events")
            .select("*")
            .eq("channel_id", channel_id)
            .order("received_at", desc=False)
            .limit(limit)
            .execute()
        )
        return {"channel_id": channel_id, "events": resp.data or []}
    except Exception as e:
        logger.warning("taximetro history failed channel=%s: %s", channel_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def taximetro_health():
    """Reports relay readiness without exposing pay.sh internals."""
    payshell_reachable: Optional[bool] = None
    try:
        from integrations.solana.pay_shell_client import get_pay_shell_client

        client = get_pay_shell_client()
        await client.health()
        payshell_reachable = True
    except Exception as e:
        logger.debug("payshell health probe failed: %s", e)
        payshell_reachable = False

    return {
        "enabled": PAYSHELL_ENABLED,
        "payshell_reachable": payshell_reachable,
        "replay_limit_default": MAX_REPLAY_EVENTS,
    }
