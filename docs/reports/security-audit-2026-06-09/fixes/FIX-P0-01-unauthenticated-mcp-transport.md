---
date: 2026-06-09
tags: [type/incident, domain/security]
status: active
severity: P0
finding_id: FIX-P0-01
---
# FIX-P0-01 — Unauthenticated `/mcp` transport + self-asserted `agent_id` = full task-lifecycle authorization bypass (escrow drain)

> Consolidates findings **P0-01** and **P0-03** (same root cause, same fix surface).

## Summary

The MCP Streamable HTTP app is mounted at `/mcp` (`mcp_server/main.py:1206`) with **no authentication** — `FastMCP(...)` is constructed without an auth/token verifier (`mcp_server/server.py:266-270`), and none of the API middleware authenticates. Every money-moving `em_*` tool "authorizes" by string-comparing a **caller-supplied** `params.agent_id` / `params.executor_id` against stored data instead of a cryptographically verified principal. Any anonymous internet client can therefore impersonate any agent and drain a victim's escrowed bounty to an attacker-controlled wallet. The fix wraps the mounted MCP ASGI app in an ERC-8128 request-signature middleware (the same crypto the REST surface already enforces), injects the verified wallet as a trusted, un-spoofable scope header, and rewrites every mutating tool to derive identity from that verified wallet — never from the request body.

## Severity & Impact (why P0)

**Direct fund loss + complete object-level authorization bypass on the public, money-moving machine surface** (`https://mcp.execution.market/mcp/`).

An unauthenticated attacker can:
- **Drain a victim's escrow** via the chain `em_assign_task` → `em_submit_work` → `em_approve_submission` (relays the victim's stored EIP-3009 pre-auth with the attacker's wallet as escrow receiver, then releases it).
- **Force-cancel / force-refund** any agent's tasks (`em_cancel_task`) — griefing / DoS.
- **Force-approve** (premature escrow release) any agent's submissions (`em_approve_submission`).
- **Read all task PII** — worker wallets, evidence URLs, applicant messages (`em_check_submission`).
- **Withdraw any worker's earnings to an attacker wallet** (`em_withdraw_earnings` trusts `params.executor_id` and even honors `params.destination_address`).
- **Spam / impersonate** any agent_id (`em_publish_task`, `em_batch_create_tasks`).

At-risk funds: every USDC bounty currently in escrow under `lock_on_assignment` (pre-auth stored) or already locked (fase2). At-risk data: all submission/applicant PII. Asymmetry that proves this is an unintended gap: the REST surface (`verify_agent_auth_write`, `mcp_server/api/auth.py:545-673`) and the A2A surface (`a2a/jsonrpc_router.py`) both enforce ERC-8128 and 401 on failure. Only the MCP transport skips crypto auth.

## Affected code (verified at the cited lines on `main`, 2026-06-09)

**Transport mounted with no auth:**
- `mcp_server/server.py:266-270`
  ```python
  mcp = FastMCP(
      SERVER_INFO["name"],
      streamable_http_path="/",
      host="0.0.0.0",
  )   # ← no auth=/token_verifier
  ```
- `mcp_server/main.py:340` — `mcp_http_app = mcp_server.streamable_http_app()` (adds no verifier)
- `mcp_server/main.py:1205-1207`
  ```python
  if MCP_HTTP_AVAILABLE and mcp_http_app:
      app.mount("/mcp", mcp_http_app)   # ← no auth wrapper
  ```
- `mcp_server/api/middleware.py:688-717` (`add_api_middleware`) — installs only ErrorHandling, RateLimit, Idempotency, RequestLogging, SecurityHeaders. **None authenticate.** (And FastAPI `Depends`/middleware do **not** apply to a mounted Starlette sub-app.)
- `infrastructure/terraform/alb.tf:261-275` — `mcp.execution.market` is a plain `forward`, no `authenticate-*` action.

**Tools authorize on the request body, not a verified caller:**
- `mcp_server/tools/core_tools.py:619-624` (`em_approve_submission`)
  ```python
  if (not task
      or (task.get("agent_id") or "").lower() != (params.agent_id or "").lower()):
      return "Error: Not authorized to update this submission"
  ```
  → then `dispatcher.release_payment(... worker_address=worker_wallet ...)` (`core_tools.py:639-647`).
- `mcp_server/tools/core_tools.py:897-900` (`em_cancel_task`) → `db.cancel_task(task_id, params.agent_id)` → guard `mcp_server/supabase_client.py:415`.
- `mcp_server/tools/agent_tools.py:476` (`em_assign_task`)
  ```python
  if task["agent_id"] != params.agent_id:
      return "Error: Not authorized to assign this task"
  ```
  → relays the victim's STORED pre-auth with attacker receiver: `agent_tools.py:642-666` →
  `relay_agent_auth_to_facilitator(..., worker_address=worker_wallet, ...)` →
  `payment_dispatcher.py:1585` sets `pi["receiver"] = worker_address`. The SC-010 guard
  (`payment_dispatcher.py:1563-1583`) blocks treasury/operator/zero/payer **but not** an
  attacker-controlled worker wallet. Server-side guard mirror: `supabase_client.py:1325`.
- `mcp_server/server.py:966` (`em_check_submission`) — same self-asserted check leaks submissions/PII.
- `mcp_server/tools/worker_tools.py` — `em_apply_to_task` (`:281`), `em_submit_work` (`:408`),
  `em_withdraw_earnings` (`:667`) trust `params.executor_id`; `em_withdraw_earnings` pays out to
  `executor.wallet_address` (or attacker-supplied `params.destination_address`).
- `mcp_server/server.py:1308-1313` (`em_resolve_dispute`) — builds a **synthetic** `AgentAuth` from
  `EM_CALLER_AGENT_ID`/`EM_CALLER_WALLET` env vars, **not** the caller. (Currently mitigated:
  `api/routers/disputes.py:674-685` rejects `auth.auth_method != "erc8128"` with 403, so the MCP path
  returns 403 today. Still spoofs platform identity if that guard is ever relaxed — fix anyway, lower priority.)

**Misleading comment that must be corrected:** `mcp_server/server.py:1304-1307` claims *"In production MCP tool calls flow through the same auth layer as the REST API"* — this is **false** today.

**Attacker bootstrap is unauthenticated:** `mcp_server/api/routers/workers.py:75-104` (`register_worker`) has no auth dependency → attacker mints an executor bound to their own wallet.

## Root cause

Two compounding defects:
1. **The MCP transport was never wired to the auth layer.** A mounted Starlette ASGI sub-app does not inherit FastAPI `Depends`, and the official MCP SDK's `FastMCP` was instantiated without its `auth=` provider. The transport is the only machine-facing surface (vs REST + A2A) with no authentication.
2. **The tools trust client-asserted identity for authorization.** Ownership checks compare `task.agent_id` to `params.agent_id` (a body field) rather than to a verified principal. Even if the transport were authenticated, a signer for wallet A could still pass `agent_id=B` and impersonate B unless the tools bind authorization to the verified wallet.

## Exploit scenario (concrete)

1. **Victim** agent (`0xVICTIM`) publishes a task via REST with `X-Payment-Auth` under the default `lock_on_assignment` timing. The EIP-3009 pre-auth is stored in the escrow row (`status=pending_assignment`, `metadata.preauth_signature`).
2. **Attacker** (no credentials) `POST /api/v1/workers/register {wallet: 0xATTACKER}` → gets `executor_id = E_attacker`.
3. Attacker opens an MCP session at `https://mcp.execution.market/mcp/` and calls `em_get_tasks` → learns `task_id` + `agent_id` of a funded victim task.
4. Attacker calls `em_assign_task{task_id, agent_id: 0xVICTIM, executor_id: E_attacker, skip_eligibility_check: true}`. The body check at `agent_tools.py:476` passes (self-asserted). The tool relays `0xVICTIM`'s stored pre-auth to the Facilitator with `worker_address = 0xATTACKER`; **the victim's USDC is now locked in escrow with the attacker as receiver.**
5. Attacker calls `em_submit_work{task_id, executor_id: E_attacker, evidence:{...}}` (escrow validation passes — escrow is funded).
6. Attacker calls `em_approve_submission{submission_id, agent_id: 0xVICTIM, verdict: accepted}`. `release_payment → _release_fase2` releases the escrow to `0xATTACKER`. **Funds stolen.**

Even without the full chain: unauthenticated force-cancel/refund, force-approve, and full PII read are each directly reachable.

## The Fix (precise, code-level)

Strategy: **(A)** an ASGI middleware that ERC-8128-verifies every `/mcp` request and injects the recovered wallet as a trusted, un-spoofable scope header; **(B)** every mutating tool reads identity from that header (via the FastMCP `Context`) and binds authorization to it; **(C)** flag-gated, fail-safe rollout.

> **Why a scope header and not a `contextvar`?** In the official MCP SDK (`mcp==1.26.0`) the tool handler runs in a **separate task** spawned by the session manager's `task_group` (`run_server`/`run_stateless_server` in `mcp/server/streamable_http_manager.py`), decoupled from the per-request ASGI task — so a `contextvar` set in middleware will **not** propagate to the tool in either stateful or stateless mode. However, the SDK attaches the originating Starlette `Request` to each JSON-RPC message via `ServerMessageMetadata(request_context=request)` (`mcp/server/streamable_http.py`), and that `Request` reaches the tool as `ctx.request_context.request`. Because the transport reconstructs `Request(scope, ...)` from the **same ASGI scope** the middleware mutated, a header we inject into `scope["headers"]` is visible to the tool. This is the only reliable, task-independent channel.

### File 1 (NEW) — `mcp_server/api/mcp_auth_middleware.py`

ASGI middleware wrapping the mounted MCP app. Buffers the body (so the inner app can re-read it), runs `verify_erc8128_request`, strips any inbound spoof of the trusted header, injects the verified wallet, and 401s on failure when enforcement is ON.

```python
"""ERC-8128 authentication for the mounted MCP Streamable HTTP app (FIX-P0-01).

The MCP transport at /mcp is the public, money-moving agent surface. FastAPI
`Depends` do NOT apply to a mounted Starlette sub-app, so we authenticate here,
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
    return os.environ.get("EM_MCP_AUTH_ENABLED", "false").lower() in ("1", "true", "yes")


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
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 1. Buffer the whole body so both the verifier and the inner app can read it.
        body = b""
        more = True
        while more:
            message = await receive()
            if message["type"] == "http.request":
                body += message.get("body", b"")
                more = message.get("more_body", False)
            else:  # http.disconnect
                more = False

        async def replay_receive() -> Message:
            return {"type": "http.request", "body": body, "more_body": False}

        # 2. Strip any client-supplied trusted headers (anti-spoof) BEFORE anything reads them.
        scope = dict(scope)
        scope["headers"] = [
            (k, v)
            for (k, v) in scope.get("headers", [])
            if k.lower() not in (VERIFIED_WALLET_HEADER, VERIFIED_CHAIN_HEADER)
        ]

        if not _enabled():
            logger.warning(
                "SECURITY_AUDIT action=mcp_auth.bypass reason=flag_off path=%s "
                "(EM_MCP_AUTH_ENABLED=false — MCP transport is UNAUTHENTICATED)",
                scope.get("path"),
            )
            await self.app(scope, replay_receive, send)
            return

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
                scope.get("path"), result.reason,
            )
            await self._reject(send, f"ERC-8128 verification failed: {result.reason}")
            return

        # 4. Inject the trusted, verified identity into the scope headers.
        scope["headers"] = scope["headers"] + [
            (VERIFIED_WALLET_HEADER, result.address.lower().encode()),
            (VERIFIED_CHAIN_HEADER, str(result.chain_id or "").encode()),
        ]
        logger.info("MCP auth: verified wallet=%s chain=%s", result.address, result.chain_id)
        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _reject(send: Send, detail: str) -> None:
        body = json.dumps({"error": "unauthorized", "detail": detail}).encode()
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"www-authenticate", b'ERC8128 realm="execution-market"'),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": body})
```

### File 2 — `mcp_server/main.py` (wrap the mount)

Change `main.py:1205-1207`:

```python
if MCP_HTTP_AVAILABLE and mcp_http_app:
    from api.mcp_auth_middleware import MCPAuthMiddleware  # FIX-P0-01
    app.mount("/mcp", MCPAuthMiddleware(mcp_http_app))
    logger.info(
        "MCP Streamable HTTP mounted at /mcp/ (auth enabled=%s)",
        os.environ.get("EM_MCP_AUTH_ENABLED", "false"),
    )
else:
    logger.warning("MCP Streamable HTTP not available - stdio transport only")
```

### File 3 (NEW) — `mcp_server/tools/mcp_identity.py` (shared principal resolver)

Single source of truth for reading the verified wallet from the tool `Context` and mapping it to the agent identity used in ownership checks.

```python
"""Resolve the authenticated MCP caller (FIX-P0-01).

Reads the wallet the MCPAuthMiddleware verified and injected as a trusted scope
header (x-em-verified-wallet). Tools MUST derive identity from this, never from
params.agent_id / params.executor_id.
"""

from __future__ import annotations

import os
from typing import Optional


class MCPAuthError(Exception):
    """Raised when no verified caller is present (enforcement on, no signature)."""


def _enabled() -> bool:
    return os.environ.get("EM_MCP_AUTH_ENABLED", "false").lower() in ("1", "true", "yes")


def get_verified_wallet(ctx) -> Optional[str]:
    """Return the lowercased verified wallet, or None if unauthenticated."""
    try:
        request = ctx.request_context.request  # Starlette Request threaded by the SDK
    except Exception:
        request = None
    if request is None:
        return None
    wallet = request.headers.get("x-em-verified-wallet")
    return wallet.lower() if wallet else None


def require_agent_identity(ctx, claimed_agent_id: Optional[str]) -> str:
    """Return the authoritative agent_id for ownership checks.

    Enforcement ON: returns the verified wallet; raises MCPAuthError if absent.
      The verified wallet IS the agent_id for ERC-8128 callers (mirrors
      api/auth.py:590-597, which sets agent_id = wallet address).
    Enforcement OFF (staged rollout): falls back to the claimed body value so
      legacy/local flows keep working; the bypass is logged by the middleware.
    """
    wallet = get_verified_wallet(ctx)
    if wallet:
        return wallet
    if _enabled():
        raise MCPAuthError(
            "Authentication required: sign this MCP request with ERC-8128 "
            "(see https://execution.market/skill.md)."
        )
    return (claimed_agent_id or "").lower()


def require_executor_wallet(ctx) -> Optional[str]:
    """Verified wallet for worker-side tools (bind executor_id to this wallet)."""
    wallet = get_verified_wallet(ctx)
    if not wallet and _enabled():
        raise MCPAuthError("Authentication required: sign this MCP request with ERC-8128.")
    return wallet
```

### File 4 — every mutating tool: add `ctx: Context`, derive identity from the principal

Add a `ctx: Context` parameter to each tool (FastMCP auto-injects it — no input-model change) and replace each body-asserted ownership check. Pattern (shown for `em_approve_submission`, `mcp_server/tools/core_tools.py:617-624`):

```python
from mcp.server.fastmcp import Context  # at top of file
from tools.mcp_identity import require_agent_identity, MCPAuthError

@mcp.tool()
async def em_approve_submission(params: ApproveSubmissionInput, ctx: Context) -> str:
    try:
        caller_agent_id = require_agent_identity(ctx, params.agent_id)
    except MCPAuthError as e:
        return f"Error: {e}"
    ...
    task = submission.get("task")
    if not task or (task.get("agent_id") or "").lower() != caller_agent_id:
        return "Error: Not authorized to update this submission"
```

Apply the identical substitution (`params.<field>` → verified principal) to **every** tool below:

| File:line | Tool | Change |
|-----------|------|--------|
| `tools/core_tools.py:619-624` | `em_approve_submission` | compare `task.agent_id` to `require_agent_identity(ctx, params.agent_id)` |
| `tools/core_tools.py:897-900` | `em_cancel_task` | pass `require_agent_identity(...)` into `db.cancel_task(task_id, <verified>)` |
| `tools/core_tools.py` (`em_publish_task`) | `em_publish_task` | set `agent_id = require_agent_identity(ctx, params.agent_id)` on the created task |
| `tools/agent_tools.py:476` | `em_assign_task` | compare `task["agent_id"]` to verified wallet; pass verified value to `db.assign_task(agent_id=...)` |
| `tools/agent_tools.py` (`em_batch_create_tasks`) | `em_batch_create_tasks` | stamp verified `agent_id` on each created task |
| `server.py:966` | `em_check_submission` | compare `task.agent_id` to `require_agent_identity(ctx, params.agent_id)` |
| `tools/worker_tools.py:281` | `em_apply_to_task` | bind `params.executor_id` to `require_executor_wallet(ctx)` (executor.wallet_address must match) |
| `tools/worker_tools.py:408` | `em_submit_work` | same executor↔wallet binding |
| `tools/worker_tools.py:667` | `em_withdraw_earnings` | require executor.wallet_address == verified wallet; **reject `destination_address` ≠ verified wallet** |
| `server.py:1308-1313` | `em_resolve_dispute` | replace synthetic `AgentAuth(EM_CALLER_*)` with `AgentAuth(agent_id=<verified>, wallet_address=<verified>, auth_method="erc8128")`; if no verified wallet and enforcement on → 403 |

**Executor↔wallet binding helper** (apply in worker tools): after fetching the executor row, assert
`(<executor>.wallet_address or "").lower() == require_executor_wallet(ctx)` — else
`return "Error: Not authorized — executor does not belong to the signing wallet"`.

**Also fix the false comment** at `server.py:1304-1307` to state that auth is enforced by `MCPAuthMiddleware` when `EM_MCP_AUTH_ENABLED=true`.

**Defense-in-depth in `db.assign_task` / `db.cancel_task`:** these already compare `task.agent_id` to the passed `agent_id` (`supabase_client.py:415,1325`). They become correct automatically once callers pass the verified wallet. No change required there, but keep them as the last-line guard.

### Feature flag / env var

| Var | Safe default | Meaning | ECS action |
|-----|--------------|---------|------------|
| `EM_MCP_AUTH_ENABLED` | `false` (fail-open, staged) → flip to `true` after canary | When `true`, all `/mcp` requests require valid ERC-8128 and tools enforce verified identity | Add to the `mcp-server` task definition `environment` (NOT a secret). Register a new revision and `aws ecs update-service --force-new-deployment`. |

Set it via the `mcp-server` task definition `environment` block:
```hcl
# infrastructure/terraform/<mcp task def>.tf — environment[]
{ name = "EM_MCP_AUTH_ENABLED", value = "true" }
```
Manual fallback: `aws ecs register-task-definition` from the current JSON with the env var added, then `aws ecs update-service --cluster <YOUR_ECS_CLUSTER> --service <YOUR_ECR_MCP_REPO> --task-definition <new-rev> --force-new-deployment --region us-east-2`.

### Infra (defense-in-depth, optional, NOT a substitute)

Optionally add a WAF rule that drops any inbound request to `mcp.execution.market/mcp*` lacking a `Signature-Input` header (cheap pre-filter). This is belt-and-suspenders — the app-layer binding in File 1+4 is the primary control. No Terraform change is required for the core fix.

### Backward-compatibility & safe rollout

- **Documented production flows use REST**, not MCP. `dashboard/public/skill.md` demonstrates every mutation via `POST /api/v1/tasks`, `/assign`, `/cancel`, `/submissions` (already ERC-8128-signed) — only advertises the `/mcp/` transport's existence (skill.md:140). So enabling auth on `/mcp` has **low lock-out risk** for documented agents.
- **Risk:** any internal tooling / MCP IDE client that connects to `/mcp/` **without** signing will break when the flag flips. Mitigate with the staged rollout:
  1. **Ship code with `EM_MCP_AUTH_ENABLED=false`** (pass-through). Middleware logs `SECURITY_AUDIT action=mcp_auth.bypass` on every `/mcp` hit — gives a CloudWatch inventory of who actually uses the transport.
  2. **Watch logs 24–48 h.** Confirm no legitimate unsigned MCP traffic (or migrate it to signed calls / REST).
  3. **Flip `EM_MCP_AUTH_ENABLED=true`** in the task definition; force a new deployment; run the E2E below.
  4. If anything breaks, set the env var back to `false` and redeploy (instant, no code rollback).
- **Fail-safe property:** the middleware **never fails open on a verifier crash** (returns 401). It only passes unauthenticated traffic when the operator has explicitly left the flag `false`.
- **skill.md update (separate task, not blocking):** once the flag is on, bump `dashboard/public/skill.md` to state that the `/mcp/` transport requires ERC-8128 signing (same signer as REST), and sync to `mcp_server/skills/SKILL.md`.

## Test plan

### Unit / integration tests to add — `mcp_server/tests/test_mcp_transport_auth.py` (`pytest.mark.security`)

1. `test_mcp_middleware_rejects_unsigned_when_enabled` — with `EM_MCP_AUTH_ENABLED=true`, drive `MCPAuthMiddleware` with an ASGI scope/body carrying **no** `Signature`/`Signature-Input` → asserts a `401` `http.response.start` and the inner app is **never** called.
2. `test_mcp_middleware_passthrough_when_disabled` — flag `false` → inner app called, no `x-em-verified-wallet` injected.
3. `test_mcp_middleware_strips_spoofed_header` — client sends `x-em-verified-wallet: 0xVICTIM` with no signature → header is stripped before the inner app sees it (assert it is absent in the scope handed downstream).
4. `test_mcp_middleware_injects_verified_wallet` — monkeypatch `verify_erc8128_request` to return `ok=True, address=0xAAA…` → asserts inner app receives `x-em-verified-wallet=0xaaa…` and body is replayable (inner app can `await request.body()`).
5. **Bug-reproducing authz test** — `test_em_approve_submission_rejects_forged_agent_id`:
   - Build a `Context` whose `request_context.request.headers["x-em-verified-wallet"]` = `0xATTACKER`.
   - Task owned by `0xVICTIM`; call `em_approve_submission(ApproveSubmissionInput(agent_id="0xVICTIM", ...), ctx)`.
   - **Before fix:** approves + releases payment. **After fix:** returns `"Error: Not authorized…"` and `dispatcher.release_payment` is **not** called. This is the exact impersonation primitive.
6. `test_em_assign_task_rejects_forged_agent_id` — verified wallet `0xATTACKER`, body `agent_id=0xVICTIM` → `"Error: Not authorized to assign this task"`; `relay_agent_auth_to_facilitator` not called.
7. `test_em_withdraw_earnings_binds_executor_to_wallet` — verified wallet `0xATTACKER`, `executor_id` whose `wallet_address=0xVICTIM` → rejected; and `destination_address=0xATTACKER` with a victim executor → rejected.
8. `test_em_resolve_dispute_uses_verified_caller` — assert the `AgentAuth` passed to `resolve_dispute_endpoint` carries the verified wallet + `auth_method="erc8128"`, not `EM_CALLER_*`.

> Test harness notes: tools take `ctx: Context`; build a stub `Context` with a `request_context.request` exposing a `headers` mapping (mirror existing `tests/test_mcp_tools.py` mocking style). Reset the nonce store with `integrations.erc8128.nonce_store.reset_nonce_store()` between cases.

### Manual / E2E verification (against staging or prod canary)

- **A. Unsigned is blocked:** `curl -sS -X POST https://mcp.execution.market/mcp/ -H 'content-type: application/json' -d '{"jsonrpc":"2.0","method":"initialize",...}'` → **401** (flag on).
- **B. Signed legitimate flow still works:** run the existing Golden Flow signer (OWS `ows_sign_erc8128_request`) against `/mcp/` `em_publish_task` → succeeds, task `agent_id` == signer wallet.
- **C. Impersonation blocked:** sign as wallet A, call `em_approve_submission` with body `agent_id=B` → `"Not authorized"`.
- **D. Regression:** `python scripts/e2e_golden_flow.py` (REST path) still 7/8+ PASS (REST surface untouched).
- **E.** Re-run the P0-01/P0-03 exploit chain end-to-end → fails at step 4 (`em_assign_task` 401/Not-authorized).

## Rollback plan

- **Fast path (no redeploy of code):** set `EM_MCP_AUTH_ENABLED=false` in the `mcp-server` task definition and force a new deployment. The middleware reverts to pass-through; tools fall back to legacy body-asserted identity. ~2–3 min.
- **Full code rollback:** revert the `app.mount` wrap (`main.py:1206`) to the bare mount and redeploy the prior MCP image (`deploy-mcp` skill). The tool `ctx: Context` parameters are additive/backward-compatible (FastMCP injects `ctx`; when no verified header is present and the flag is off, `require_agent_identity` returns the body value) so they can remain.
- No DB migration is involved → no schema rollback needed.

## Verification checklist

- [ ] `mcp_server/api/mcp_auth_middleware.py` added; `MCPAuthMiddleware` wraps the mount at `main.py:1206`.
- [ ] Body buffering verified: a signed `/mcp` POST's body is readable by BOTH the verifier and the inner MCP app (no "empty body"/hang).
- [ ] Inbound `x-em-verified-wallet` / `x-em-verified-chain-id` headers are **stripped** before any downstream read (anti-spoof).
- [ ] `tools/mcp_identity.py` added; `require_agent_identity` / `require_executor_wallet` used by ALL tools in the table.
- [ ] `em_approve_submission`, `em_cancel_task`, `em_publish_task`, `em_assign_task`, `em_batch_create_tasks`, `em_check_submission` derive `agent_id` from the verified wallet — not `params.agent_id`.
- [ ] `em_apply_to_task`, `em_submit_work`, `em_withdraw_earnings` bind `executor_id` to the verified wallet; `em_withdraw_earnings` rejects `destination_address != verified wallet`.
- [ ] `em_resolve_dispute` uses the verified caller (not `EM_CALLER_*`); 403 when unauthenticated under enforcement.
- [ ] False comment at `server.py:1304-1307` corrected.
- [ ] `EM_MCP_AUTH_ENABLED` added to the `mcp-server` ECS task definition (default `false` for ship, then flipped to `true` post-canary).
- [ ] New tests in `tests/test_mcp_transport_auth.py` pass; bug-reproducing test #5 fails before the tool change and passes after.
- [ ] Full backend suite green: `pytest -m "core or security"`.
- [ ] Manual checks A–E pass on canary; Golden Flow (REST) regression-clean.
- [ ] Staged rollout executed: shipped flag-off → 24–48 h bypass-log review → flag-on → exploit chain re-run fails.
- [ ] (Deferred, non-blocking) `dashboard/public/skill.md` updated to document `/mcp/` ERC-8128 requirement and synced to `mcp_server/skills/SKILL.md` (version bump + changelog row).
