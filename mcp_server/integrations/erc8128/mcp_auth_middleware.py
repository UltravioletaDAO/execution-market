"""ERC-8128 authentication for the mounted MCP Streamable HTTP app (FIX-P0-01).

The MCP transport at /mcp is the public, money-moving agent surface. FastAPI
``Depends`` do NOT apply to a mounted Starlette sub-app, so we authenticate here,
at the ASGI boundary, with the SAME ERC-8128 request-signature scheme the REST
and A2A surfaces enforce (mcp_server/api/auth.py::verify_agent_auth_write).

Verified principal propagation:
  The MCP SDK runs tool handlers in a task decoupled from the request task, so a
  contextvar would not reach the tool. Instead we inject the recovered wallet as
  a trusted ASGI scope header (X-EM-Verified-Wallet). The SDK threads the
  originating Starlette Request (built from the same scope) into the tool as
  ctx.request_context.request, so tools read the header there. We FIRST strip any
  client-supplied copy of that header so it cannot be spoofed.

Master switch: EM_MCP_AUTH_ENABLED (default "false" — fail-OPEN until staged on).
  - "false": pass-through (legacy behavior). Logs an audit warning so the gap is
    visible in CloudWatch while we stage the rollout.
  - "true":  every /mcp request MUST carry a valid ERC-8128 signature, else 401.
"""

from __future__ import annotations

import json
import logging
import os

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)

VERIFIED_WALLET_HEADER = b"x-em-verified-wallet"
VERIFIED_CHAIN_HEADER = b"x-em-verified-chain-id"


def _enabled() -> bool:
    return os.environ.get("EM_MCP_AUTH_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )


class _ReplayRequest:
    """Minimal request-like object for verify_erc8128_request over a buffered body."""

    def __init__(self, scope: Scope, body: bytes):
        from starlette.requests import Request

        self._r = Request(scope)
        self._body = body
        # surface attributes verify_erc8128_request reads
        self.headers = self._r.headers
        self.method = self._r.method
        self.url = self._r.url

    async def body(self) -> bytes:
        return self._body


class MCPAuthMiddleware:
    """ASGI middleware that ERC-8128-verifies requests to the mounted /mcp app."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 1. Strip any client-supplied trusted headers (anti-spoof) BEFORE anything
        #    reads them. Header surgery needs no body interaction.
        scope = dict(scope)
        scope["headers"] = [
            (k, v)
            for (k, v) in scope.get("headers", [])
            if k.lower() not in (VERIFIED_WALLET_HEADER, VERIFIED_CHAIN_HEADER)
        ]

        if not _enabled():
            # Flag off: hand the REAL receive straight through. The streamable
            # HTTP transport polls receive() to detect client disconnect while a
            # session streams; any wrapper that synthesizes http.request messages
            # forever busy-loops the event loop and freezes the whole server
            # (INC 2026-06-10: prod boot-looped on every MCP session).
            logger.warning(
                "SECURITY_AUDIT action=mcp_auth.bypass reason=flag_off path=%s "
                "(EM_MCP_AUTH_ENABLED=false — MCP transport is UNAUTHENTICATED)",
                scope.get("path"),
            )
            await self.app(scope, receive, send)
            return

        # 2. Buffer the whole body so both the verifier and the inner app can read it.
        body = b""
        more = True
        while more:
            message = await receive()
            if message["type"] == "http.request":
                body += message.get("body", b"")
                more = message.get("more_body", False)
            else:  # http.disconnect — client gone before the body finished
                return

        replayed = False

        async def replay_receive() -> Message:
            # Replay the buffered body exactly once, then delegate to the real
            # receive so the inner app can await http.disconnect (the streamable
            # transport polls this to notice the client leaving — returning the
            # same http.request forever would busy-loop the event loop).
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        # 3. Verify ERC-8128 over the raw request.
        from integrations.erc8128.verifier import verify_erc8128_request
        from api.auth import _get_erc8128_nonce_store  # reuse the REST nonce store

        try:
            result = await verify_erc8128_request(
                _ReplayRequest(scope, body),
                nonce_store=_get_erc8128_nonce_store(),
            )
        except Exception as exc:  # never fail-open on a verifier crash
            logger.error("MCP auth: verifier error: %s", exc)
            await self._reject(send, "ERC-8128 verification error")
            return

        if not result.ok:
            logger.warning(
                "SECURITY_AUDIT action=mcp_auth.rejected path=%s reason=%s",
                scope.get("path"),
                result.reason,
            )
            await self._reject(send, f"ERC-8128 verification failed: {result.reason}")
            return

        # 4. Inject the trusted, verified identity into the scope headers.
        scope["headers"] = scope["headers"] + [
            (VERIFIED_WALLET_HEADER, (result.address or "").lower().encode()),
            (VERIFIED_CHAIN_HEADER, str(result.chain_id or "").encode()),
        ]
        logger.info(
            "MCP auth: verified wallet=%s chain=%s", result.address, result.chain_id
        )
        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _reject(send: Send, detail: str) -> None:
        body = json.dumps({"error": "unauthorized", "detail": detail}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"www-authenticate", b'ERC8128 realm="execution-market"'),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
