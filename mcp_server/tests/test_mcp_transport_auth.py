"""FIX-P0-01 — MCP transport ERC-8128 auth + verified-identity binding.

Covers:
  * MCPAuthMiddleware (integrations/erc8128/mcp_auth_middleware.py): reject
    unsigned when enabled, pass-through when disabled, strip spoofed headers,
    inject verified wallet, replayable body.
  * tools.mcp_identity resolver.
  * Bug-reproducing authorization tests for the money-moving tools: a forged
    body agent_id / executor_id cannot impersonate the verified principal.

These tests pre-import `server` at module load so the lazy `from server import`
inside helpers is a cache hit (avoids the pydantic-generics import-ordering
KeyError seen when this file is collected in isolation).
"""

import pytest

pytestmark = pytest.mark.security

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import server  # noqa: F401  (pre-import — see module docstring)
from models import (
    ApproveSubmissionInput,
    AssignTaskInput,
    SubmissionVerdict,
    WithdrawEarningsInput,
)

# 42-char EVM addresses (0x + 40 hex), already lowercase.
VICTIM = "0x" + "a1" * 20
ATTACKER = "0x" + "b2" * 20


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
class _StubHeaders(dict):
    """Case-insensitive header mapping like Starlette's."""

    def get(self, key, default=None):  # type: ignore[override]
        return super().get(key.lower(), default)


def _ctx_with_wallet(wallet):
    """Build a stub FastMCP Context exposing a verified-wallet header."""
    ctx = MagicMock()
    headers = _StubHeaders()
    if wallet is not None:
        headers["x-em-verified-wallet"] = wallet
    ctx.request_context.request.headers = headers
    return ctx


# --------------------------------------------------------------------------- #
# mcp_identity resolver
# --------------------------------------------------------------------------- #
def test_get_verified_wallet_reads_injected_header(monkeypatch):
    from tools import mcp_identity

    ctx = _ctx_with_wallet("0xAbC")
    assert mcp_identity.get_verified_wallet(ctx) == "0xabc"
    assert mcp_identity.get_verified_wallet(_ctx_with_wallet(None)) is None
    assert mcp_identity.get_verified_wallet(None) is None


def test_require_agent_identity_enforced(monkeypatch):
    from tools import mcp_identity

    monkeypatch.setenv("EM_MCP_AUTH_ENABLED", "true")
    # No verified wallet + enforcement on → raises.
    with pytest.raises(mcp_identity.MCPAuthError):
        mcp_identity.require_agent_identity(_ctx_with_wallet(None), "0xclaim")
    # Verified wallet always wins over the claimed body value.
    assert (
        mcp_identity.require_agent_identity(_ctx_with_wallet(VICTIM), "0xclaim")
        == VICTIM
    )


def test_require_agent_identity_fallback_when_disabled(monkeypatch):
    from tools import mcp_identity

    monkeypatch.delenv("EM_MCP_AUTH_ENABLED", raising=False)
    # Enforcement off + no wallet → fall back to claimed body value (lowercased).
    assert (
        mcp_identity.require_agent_identity(_ctx_with_wallet(None), "0xCLAIM")
        == "0xclaim"
    )


# --------------------------------------------------------------------------- #
# MCPAuthMiddleware
# --------------------------------------------------------------------------- #
def _scope(headers=None):
    return {
        "type": "http",
        "method": "POST",
        "path": "/mcp/",
        "headers": headers or [],
        "query_string": b"",
        "server": ("mcp.execution.market", 443),
    }


async def _drive(mw, scope, body=b'{"jsonrpc":"2.0"}'):
    """Run the middleware once; capture downstream calls + response."""
    sent = []
    received = {"scope": None, "body": None, "called": False}

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        sent.append(message)

    # Wrap the inner app to record what it sees.
    async def inner(scope_in, receive_in, send_in):
        received["called"] = True
        received["scope"] = scope_in
        msg = await receive_in()
        received["body"] = msg.get("body")

    mw.app = inner
    await mw(scope, receive, send)
    return sent, received


@pytest.mark.asyncio
async def test_mcp_middleware_passthrough_when_disabled(monkeypatch):
    from integrations.erc8128.mcp_auth_middleware import MCPAuthMiddleware

    monkeypatch.delenv("EM_MCP_AUTH_ENABLED", raising=False)
    mw = MCPAuthMiddleware(None)
    sent, received = await _drive(mw, _scope())
    assert received["called"] is True
    # No verified-wallet header injected.
    inj = [h for h in received["scope"]["headers"] if h[0] == b"x-em-verified-wallet"]
    assert inj == []


@pytest.mark.asyncio
async def test_mcp_middleware_rejects_unsigned_when_enabled(monkeypatch):
    from integrations.erc8128.mcp_auth_middleware import MCPAuthMiddleware

    monkeypatch.setenv("EM_MCP_AUTH_ENABLED", "true")
    mw = MCPAuthMiddleware(None)
    # No Signature headers present → verifier returns ok=False → 401.
    sent, received = await _drive(mw, _scope())
    assert received["called"] is False  # inner app NEVER reached
    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 401


@pytest.mark.asyncio
async def test_mcp_middleware_strips_spoofed_header(monkeypatch):
    from integrations.erc8128.mcp_auth_middleware import MCPAuthMiddleware

    monkeypatch.delenv("EM_MCP_AUTH_ENABLED", raising=False)  # pass-through
    mw = MCPAuthMiddleware(None)
    spoofed = [(b"x-em-verified-wallet", VICTIM.encode())]
    sent, received = await _drive(mw, _scope(headers=spoofed))
    # The client-supplied trusted header must be stripped before downstream.
    assert all(
        h[0] != b"x-em-verified-wallet" for h in received["scope"]["headers"]
    )


@pytest.mark.asyncio
async def test_mcp_middleware_injects_verified_wallet(monkeypatch):
    from integrations.erc8128.mcp_auth_middleware import MCPAuthMiddleware

    monkeypatch.setenv("EM_MCP_AUTH_ENABLED", "true")
    mw = MCPAuthMiddleware(None)

    fake_result = MagicMock(ok=True, address="0xAAA", chain_id=8453, reason=None)
    with patch(
        "integrations.erc8128.verifier.verify_erc8128_request",
        new=AsyncMock(return_value=fake_result),
    ):
        sent, received = await _drive(mw, _scope())

    assert received["called"] is True
    inj = dict(received["scope"]["headers"])
    assert inj[b"x-em-verified-wallet"] == b"0xaaa"
    # Body is still replayable by the inner app.
    assert received["body"] == b'{"jsonrpc":"2.0"}'


# --------------------------------------------------------------------------- #
# Bug-reproducing authorization tests (impersonation primitive)
# --------------------------------------------------------------------------- #
def _db():
    db = MagicMock()
    db.get_submission = AsyncMock()
    db.get_task = AsyncMock()
    db.assign_task = AsyncMock()
    db.get_client = MagicMock()
    db.get_executor_stats = AsyncMock()
    db.get_executor_earnings = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_em_approve_submission_rejects_forged_agent_id(monkeypatch):
    """Verified wallet=ATTACKER, body agent_id=VICTIM → Not authorized.

    Pre-fix this approved + released payment. Post-fix it is rejected and the
    payment dispatcher is never invoked.
    """
    monkeypatch.setenv("EM_MCP_AUTH_ENABLED", "true")
    from server import em_approve_submission

    sub_id = str(uuid4())
    task_id = str(uuid4())
    db = _db()
    db.get_submission.return_value = {
        "id": sub_id,
        "task": {"id": task_id, "agent_id": VICTIM, "bounty_usd": 5.0},
        "executor": {"wallet_address": ATTACKER},
    }
    dispatcher = MagicMock()
    dispatcher.release_payment = AsyncMock(return_value={"success": True})

    params = ApproveSubmissionInput(
        submission_id=sub_id,
        agent_id=VICTIM,  # forged — attacker claims the victim
        verdict=SubmissionVerdict.ACCEPTED,
    )
    ctx = _ctx_with_wallet(ATTACKER)
    with (
        patch("server.db", db),
        patch(
            "integrations.x402.payment_dispatcher.get_dispatcher",
            return_value=dispatcher,
        ),
    ):
        result = await em_approve_submission(params, ctx)

    assert "Not authorized" in result
    dispatcher.release_payment.assert_not_called()


@pytest.mark.asyncio
async def test_em_assign_task_rejects_forged_agent_id(monkeypatch):
    """Verified wallet=ATTACKER, body agent_id=VICTIM → Not authorized."""
    monkeypatch.setenv("EM_MCP_AUTH_ENABLED", "true")
    from tools.agent_tools import register_agent_tools
    from mcp.server.fastmcp import FastMCP

    task_id = str(uuid4())
    db = _db()
    db.get_task.return_value = {
        "id": task_id,
        "agent_id": VICTIM,
        "status": "published",
    }
    mcp = FastMCP("t")
    captured = {}

    real_tool = mcp.tool

    def _capture_tool(*a, **k):
        deco = real_tool(*a, **k)

        def wrap(fn):
            captured[k.get("name", fn.__name__)] = fn
            return deco(fn)

        return wrap

    mcp.tool = _capture_tool
    register_agent_tools(mcp, db)

    params = AssignTaskInput(
        task_id=task_id,
        agent_id=VICTIM,  # forged
        executor_id=str(uuid4()),
    )
    ctx = _ctx_with_wallet(ATTACKER)
    result = await captured["em_assign_task"](params, ctx)
    assert "Not authorized to assign this task" in result
    db.assign_task.assert_not_called()


@pytest.mark.asyncio
async def test_em_withdraw_earnings_binds_executor_to_wallet(monkeypatch):
    """A withdrawal for an executor owned by another wallet is rejected, and a
    destination_address != verified wallet is rejected."""
    monkeypatch.setenv("EM_MCP_AUTH_ENABLED", "true")
    from tools.worker_tools import register_worker_tools, WorkerToolsConfig
    from mcp.server.fastmcp import FastMCP

    exec1 = str(uuid4())
    exec2 = str(uuid4())
    db = _db()
    # Executor belongs to the VICTIM wallet, not the attacker.
    db.get_executor_stats.return_value = {
        "id": exec1,
        "wallet_address": VICTIM,
    }
    mcp = FastMCP("t")
    captured = {}
    real_tool = mcp.tool

    def _capture_tool(*a, **k):
        deco = real_tool(*a, **k)

        def wrap(fn):
            captured[k.get("name", fn.__name__)] = fn
            return deco(fn)

        return wrap

    mcp.tool = _capture_tool
    register_worker_tools(mcp, db, None, WorkerToolsConfig())

    # Case 1: executor not owned by the verified wallet → rejected.
    params = WithdrawEarningsInput(executor_id=exec1)
    ctx = _ctx_with_wallet(ATTACKER)
    result = await captured["em_withdraw_earnings"](params, ctx)
    assert "does not belong to the signing wallet" in result
    db.get_executor_earnings.assert_not_called()

    # Case 2: executor owned by attacker but destination is a foreign wallet.
    db.get_executor_stats.return_value = {
        "id": exec2,
        "wallet_address": ATTACKER,
    }
    params2 = WithdrawEarningsInput(
        executor_id=exec2, destination_address=VICTIM
    )
    result2 = await captured["em_withdraw_earnings"](params2, _ctx_with_wallet(ATTACKER))
    assert "destination must be the verified signing wallet" in result2
