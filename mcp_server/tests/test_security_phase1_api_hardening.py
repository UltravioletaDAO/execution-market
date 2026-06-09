"""
Tests for Phase 1 Track H — Backend API Hardening.

Covers:
  - API-002: POST /tasks/batch returns 503 (disabled)
  - API-003: POST /disputes/{id}/resolve requires ERC-8128, rejects API key auth
  - API-019: A2A JSON-RPC _extract_agent_id uses verified auth, not raw headers

Marker: security
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.security

# Add mcp_server/ to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.auth import AgentAuth  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_auth(
    *,
    agent_id: str = "0xtestcaller",
    wallet_address: str | None = "0xdeadbeef",
    auth_method: str = "erc8128",
) -> AgentAuth:
    return AgentAuth(
        agent_id=agent_id,
        wallet_address=wallet_address,
        auth_method=auth_method,
    )


def _make_request(headers: dict[str, str] | None = None):
    """Minimal Request stand-in: resolve_dispute only reads request.headers.get()."""
    req = MagicMock()
    req.headers = headers or {}
    return req


# ===========================================================================
# API-002: Batch endpoint disabled
# ===========================================================================


class TestBatchEndpointDisabled:
    """POST /tasks/batch must return 503 regardless of auth."""

    @pytest.fixture(autouse=True)
    def _patch_deps(self):
        """Patch heavy dependencies so we can import the router."""
        with (
            patch.dict(
                sys.modules,
                {
                    "supabase_client": MagicMock(),
                    "audit": MagicMock(),
                },
            ),
        ):
            yield

    @pytest.mark.asyncio
    async def test_batch_returns_503(self):
        """Batch endpoint always raises HTTPException(503)."""
        from fastapi import HTTPException

        # Import the endpoint function directly
        from api.routers.tasks import batch_create_tasks

        # Build a minimal BatchCreateRequest mock
        mock_request = MagicMock()
        mock_request.tasks = []

        auth = _make_auth()

        with pytest.raises(HTTPException) as exc_info:
            await batch_create_tasks(request=mock_request, auth=auth)

        assert exc_info.value.status_code == 503
        assert "temporarily disabled" in exc_info.value.detail
        assert "API-002" in exc_info.value.detail


# ===========================================================================
# API-003: Dispute resolve requires ERC-8128
# ===========================================================================


class TestDisputeResolveHardened:
    """POST /disputes/{id}/resolve must reject non-ERC-8128 callers."""

    @pytest.fixture(autouse=True)
    def _patch_deps(self):
        """Patch supabase_client.get_client for dispute router."""
        mock_client = MagicMock()
        # Default: no dispute found
        mock_execute = MagicMock()
        mock_execute.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_execute
        with patch("supabase_client.get_client", return_value=mock_client):
            yield

    @pytest.mark.asyncio
    async def test_rejects_api_key_auth(self):
        """API key auth method must be rejected with 403."""
        from fastapi import HTTPException
        from api.routers.disputes import resolve_dispute, ResolveDisputeRequest

        auth = _make_auth(auth_method="api_key")
        body = ResolveDisputeRequest(verdict="release", reason="Testing release")

        with pytest.raises(HTTPException) as exc_info:
            await resolve_dispute(
                dispute_id="test-dispute-1",
                body=body,
                request=_make_request(),
                auth=auth,
            )

        assert exc_info.value.status_code == 403
        assert "ERC-8128" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_rejects_missing_wallet(self):
        """Missing wallet_address must be rejected with 403."""
        from fastapi import HTTPException
        from api.routers.disputes import resolve_dispute, ResolveDisputeRequest

        auth = _make_auth(wallet_address=None)
        body = ResolveDisputeRequest(verdict="refund", reason="Testing refund")

        with pytest.raises(HTTPException) as exc_info:
            await resolve_dispute(
                dispute_id="test-dispute-2",
                body=body,
                request=_make_request(),
                auth=auth,
            )

        assert exc_info.value.status_code == 403
        assert "Wallet address required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_allows_erc8128_with_wallet(self):
        """ERC-8128 auth with wallet should pass the auth gate (may 404 on dispute lookup)."""
        from fastapi import HTTPException
        from api.routers.disputes import resolve_dispute, ResolveDisputeRequest

        auth = _make_auth(auth_method="erc8128", wallet_address="0xvalidwallet")
        body = ResolveDisputeRequest(verdict="release", reason="Legitimate resolution")

        # Should pass the auth gate and hit 404 (no dispute found in mock DB)
        with pytest.raises(HTTPException) as exc_info:
            await resolve_dispute(
                dispute_id="nonexistent-dispute",
                body=body,
                request=_make_request(),
                auth=auth,
            )

        # If we get 404, the auth gate was passed
        assert exc_info.value.status_code == 404


# ===========================================================================
# API-019: A2A header spoofing prevention
# ===========================================================================


class TestA2AAgentIdExtraction:
    """_extract_agent_id must use verified auth, not raw headers."""

    @pytest.fixture(autouse=True)
    def _import_auth_module(self):
        """Pre-import api.auth so patch.object works on the module attribute."""
        import api.auth  # noqa: F401

        yield

    @pytest.mark.asyncio
    async def test_rejects_spoofed_erc8004_header(self):
        """Raw X-ERC8004-Agent-Id header must NOT be trusted without signature."""
        import api.auth as auth_mod
        from a2a.jsonrpc_router import _extract_agent_id

        mock_request = MagicMock()
        mock_request.headers = {"X-ERC8004-Agent-Id": "spoofed-agent-9999"}

        # Patch verify_agent_auth_write to raise (simulating failed auth)
        with patch.object(
            auth_mod,
            "verify_agent_auth_write",
            new_callable=AsyncMock,
            side_effect=Exception("Auth failed"),
        ):
            result = await _extract_agent_id(mock_request)

        # Must return None (unauthenticated), NOT the spoofed header value
        assert result is None

    @pytest.mark.asyncio
    async def test_uses_verified_wallet(self):
        """Verified ERC-8128 auth should return the wallet address."""
        import api.auth as auth_mod
        from a2a.jsonrpc_router import _extract_agent_id

        mock_request = MagicMock()
        mock_auth = AgentAuth(
            agent_id="2106",
            wallet_address="0xverifiedwallet",
            auth_method="erc8128",
        )

        with patch.object(
            auth_mod,
            "verify_agent_auth_write",
            new_callable=AsyncMock,
            return_value=mock_auth,
        ):
            result = await _extract_agent_id(mock_request)

        assert result == "erc8004:0xverifiedwallet"

    @pytest.mark.asyncio
    async def test_falls_back_to_agent_id_without_wallet(self):
        """If verified auth has no wallet, fall back to agent_id."""
        import api.auth as auth_mod
        from a2a.jsonrpc_router import _extract_agent_id

        mock_request = MagicMock()
        mock_auth = AgentAuth(
            agent_id="test-agent-42",
            wallet_address=None,
            auth_method="api_key",
        )

        with patch.object(
            auth_mod,
            "verify_agent_auth_write",
            new_callable=AsyncMock,
            return_value=mock_auth,
        ):
            result = await _extract_agent_id(mock_request)

        assert result == "agent:test-agent-42"

    @pytest.mark.asyncio
    async def test_returns_none_on_auth_failure(self):
        """When auth fails entirely, return None (caller gets 401)."""
        import api.auth as auth_mod
        from a2a.jsonrpc_router import _extract_agent_id

        mock_request = MagicMock()
        mock_request.headers = {
            "X-API-Key": "invalid-key",
            "X-ERC8004-Agent-Id": "spoofed",
        }

        with patch.object(
            auth_mod,
            "verify_agent_auth_write",
            new_callable=AsyncMock,
            side_effect=Exception("No valid auth"),
        ):
            result = await _extract_agent_id(mock_request)

        assert result is None


# ===========================================================================
# FIX-P1-08: Dispute resolution recusal + neutral-resolver enforcement
# ===========================================================================


def _make_dispute_fake_client(
    *,
    dispute: dict,
    executors_by_wallet: dict[str, dict] | None = None,
    executor_rows_by_id: dict[str, dict] | None = None,
    arbitrators_by_wallet: dict[str, dict] | None = None,
    votes: list[dict] | None = None,
    tasks: list[dict] | None = None,
    submissions: list[dict] | None = None,
):
    """Build a per-table fake supabase client for resolve_dispute.

    Each table's select chain captures the filters applied (.eq) and returns
    the matching rows on .execute(). This mirrors the real PostgREST chain
    closely enough to exercise the recusal/assignment/eligibility branches.
    """
    executors_by_wallet = executors_by_wallet or {}
    executor_rows_by_id = executor_rows_by_id or {}
    arbitrators_by_wallet = arbitrators_by_wallet or {}
    votes = votes or []
    tasks = tasks or []
    submissions = submissions or []

    def mk_table(name):
        table = MagicMock()

        def select(*_args, **_kwargs):
            filters: dict[str, object] = {}

            chain = MagicMock()

            def eq(col, val):
                filters[col] = val
                return chain

            def limit(_n):
                return chain

            def execute():
                if name == "disputes":
                    rows = [dispute] if filters.get("id") == dispute.get("id") else []
                elif name == "executors":
                    if "wallet_address" in filters:
                        row = executors_by_wallet.get(filters["wallet_address"])
                        rows = [row] if row else []
                    elif "id" in filters:
                        row = executor_rows_by_id.get(filters["id"])
                        rows = [row] if row else []
                    else:
                        rows = []
                elif name == "arbitrators":
                    row = arbitrators_by_wallet.get(filters.get("wallet_address"))
                    rows = [row] if row else []
                elif name == "arbitration_votes":
                    rows = [
                        v
                        for v in votes
                        if v.get("dispute_id") == filters.get("dispute_id")
                        and v.get("arbitrator_id") == filters.get("arbitrator_id")
                    ]
                elif name == "tasks":
                    rows = [t for t in tasks if t.get("id") == filters.get("id")]
                elif name == "submissions":
                    rows = [
                        s for s in submissions if s.get("id") == filters.get("id")
                    ]
                else:
                    rows = []
                return MagicMock(data=rows, count=len(rows))

            chain.eq.side_effect = eq
            chain.limit.side_effect = limit
            chain.execute.side_effect = execute
            return chain

        # update().eq().execute() is a no-op that returns empty
        upd_chain = MagicMock()
        upd_chain.eq.return_value = upd_chain
        upd_chain.execute.return_value = MagicMock(data=[], count=0)

        table.select.side_effect = select
        table.update.return_value = upd_chain
        return table

    client = MagicMock()
    client.table.side_effect = mk_table
    return client


@pytest.mark.asyncio
class TestDisputeRecusal:
    """FIX-P1-08: a conflicted/unilateral arbiter cannot redirect escrow.

    Reproduces the worker-self-deal and publisher-self-judge vectors and
    proves the admin path + flag-gated assigned-arbiter path work.
    """

    DISPUTE_ID = "11111111-1111-1111-1111-111111111111"
    TASK_ID = "22222222-2222-2222-2222-222222222222"
    SUBMISSION_ID = "33333333-3333-3333-3333-333333333333"
    EXECUTOR_ID = "44444444-4444-4444-4444-444444444444"
    PUBLISHER_WALLET = "0xpublisher"

    def _open_dispute(self):
        return {
            "id": self.DISPUTE_ID,
            "task_id": self.TASK_ID,
            "submission_id": self.SUBMISSION_ID,
            "agent_id": self.PUBLISHER_WALLET,
            "executor_id": self.EXECUTOR_ID,
            "status": "open",
            "disputed_amount_usdc": 10.0,
        }

    async def test_executor_party_release_rejected(self, monkeypatch):
        """REPRODUCES bug: the disputed executor cannot release to themselves."""
        from fastapi import HTTPException
        from api.routers import disputes as disputes_mod
        from api.routers.disputes import resolve_dispute, ResolveDisputeRequest

        monkeypatch.delenv("EM_ARBITER_UNILATERAL_RESOLUTION", raising=False)
        # Caller wallet maps to the executor that IS the dispute's executor_id.
        worker_wallet = "0xworker"
        client = _make_dispute_fake_client(
            dispute=self._open_dispute(),
            executors_by_wallet={worker_wallet: {"id": self.EXECUTOR_ID}},
        )
        monkeypatch.setattr(disputes_mod.db, "get_client", lambda: client)

        # Guard: payment must NEVER be dispatched on a recused caller.
        pay_mock = AsyncMock()
        monkeypatch.setattr(
            disputes_mod, "_trigger_resolution_payment", pay_mock
        )

        auth = _make_auth(wallet_address=worker_wallet, agent_id="0xworker")
        body = ResolveDisputeRequest(verdict="release", reason="my work is valid")

        with pytest.raises(HTTPException) as exc_info:
            await resolve_dispute(
                dispute_id=self.DISPUTE_ID,
                body=body,
                request=_make_request(),
                auth=auth,
            )

        assert exc_info.value.status_code == 403
        assert "Recusal" in exc_info.value.detail
        pay_mock.assert_not_awaited()

    async def test_publisher_party_refund_rejected(self, monkeypatch):
        """The publisher (agent_id) cannot self-judge a refund."""
        from fastapi import HTTPException
        from api.routers import disputes as disputes_mod
        from api.routers.disputes import resolve_dispute, ResolveDisputeRequest

        monkeypatch.delenv("EM_ARBITER_UNILATERAL_RESOLUTION", raising=False)
        client = _make_dispute_fake_client(
            dispute=self._open_dispute(),
            executors_by_wallet={},  # publisher has no executor row
        )
        monkeypatch.setattr(disputes_mod.db, "get_client", lambda: client)

        auth = _make_auth(
            wallet_address=self.PUBLISHER_WALLET, agent_id=self.PUBLISHER_WALLET
        )
        body = ResolveDisputeRequest(verdict="refund", reason="reclaiming funds")

        with pytest.raises(HTTPException) as exc_info:
            await resolve_dispute(
                dispute_id=self.DISPUTE_ID,
                body=body,
                request=_make_request(),
                auth=auth,
            )

        assert exc_info.value.status_code == 403
        assert "Recusal" in exc_info.value.detail

    async def test_non_admin_unilateral_disabled(self, monkeypatch):
        """A neutral eligible executor is rejected when the flag is unset."""
        from fastapi import HTTPException
        from api.routers import disputes as disputes_mod
        from api.routers.disputes import resolve_dispute, ResolveDisputeRequest

        monkeypatch.delenv("EM_ARBITER_UNILATERAL_RESOLUTION", raising=False)
        neutral_wallet = "0xneutral"
        neutral_executor_id = "55555555-5555-5555-5555-555555555555"
        client = _make_dispute_fake_client(
            dispute=self._open_dispute(),
            executors_by_wallet={neutral_wallet: {"id": neutral_executor_id}},
        )
        monkeypatch.setattr(disputes_mod.db, "get_client", lambda: client)

        auth = _make_auth(wallet_address=neutral_wallet, agent_id="0xneutral")
        body = ResolveDisputeRequest(verdict="release", reason="neutral verdict")

        with pytest.raises(HTTPException) as exc_info:
            await resolve_dispute(
                dispute_id=self.DISPUTE_ID,
                body=body,
                request=_make_request(),
                auth=auth,
            )

        assert exc_info.value.status_code == 403
        assert "requires admin authority" in exc_info.value.detail

    async def test_unassigned_arbiter_rejected_when_flag_on(self, monkeypatch):
        """With the flag ON, a neutral arbiter with no vote row is rejected."""
        from fastapi import HTTPException
        from api.routers import disputes as disputes_mod
        from api.routers.disputes import resolve_dispute, ResolveDisputeRequest

        monkeypatch.setenv("EM_ARBITER_UNILATERAL_RESOLUTION", "true")
        neutral_wallet = "0xneutral"
        neutral_executor_id = "55555555-5555-5555-5555-555555555555"
        client = _make_dispute_fake_client(
            dispute=self._open_dispute(),
            executors_by_wallet={neutral_wallet: {"id": neutral_executor_id}},
            # arbitrator row exists, but there is NO arbitration_votes row.
            arbitrators_by_wallet={
                neutral_wallet: {"id": "66666666-6666-6666-6666-666666666666"}
            },
            votes=[],
        )
        monkeypatch.setattr(disputes_mod.db, "get_client", lambda: client)

        auth = _make_auth(wallet_address=neutral_wallet, agent_id="0xneutral")
        body = ResolveDisputeRequest(verdict="release", reason="neutral verdict")

        with pytest.raises(HTTPException) as exc_info:
            await resolve_dispute(
                dispute_id=self.DISPUTE_ID,
                body=body,
                request=_make_request(),
                auth=auth,
            )

        assert exc_info.value.status_code == 403
        assert "Not assigned to this dispute" in exc_info.value.detail

    async def test_admin_resolution_allowed(self, monkeypatch):
        """A valid X-Admin-Key resolves the dispute and dispatches payment."""
        from api.routers import disputes as disputes_mod
        from api.routers.disputes import resolve_dispute, ResolveDisputeRequest

        monkeypatch.setenv("EM_ADMIN_KEY", "super-secret-admin-key")
        monkeypatch.delenv("EM_ARBITER_UNILATERAL_RESOLUTION", raising=False)
        client = _make_dispute_fake_client(
            dispute=self._open_dispute(),
            executors_by_wallet={},
            submissions=[{"id": self.SUBMISSION_ID, "status": "submitted"}],
        )
        monkeypatch.setattr(disputes_mod.db, "get_client", lambda: client)

        pay_mock = AsyncMock(return_value="released")
        monkeypatch.setattr(
            disputes_mod, "_trigger_resolution_payment", pay_mock
        )

        # Admin caller is NOT a party (distinct wallet) and presents the key.
        auth = _make_auth(wallet_address="0xadminoperator", agent_id="0xadminoperator")
        body = ResolveDisputeRequest(verdict="release", reason="admin verdict")
        request = _make_request({"X-Admin-Key": "super-secret-admin-key"})

        resp = await resolve_dispute(
            dispute_id=self.DISPUTE_ID,
            body=body,
            request=request,
            auth=auth,
        )

        assert resp.success is True
        assert resp.verdict == "release"
        pay_mock.assert_awaited_once()

    async def test_settle_payment_not_called_on_recusal(self, monkeypatch):
        """Defense in depth: no funds move when the caller is recused."""
        from fastapi import HTTPException
        from api.routers import disputes as disputes_mod
        from api.routers.disputes import resolve_dispute, ResolveDisputeRequest

        monkeypatch.delenv("EM_ARBITER_UNILATERAL_RESOLUTION", raising=False)
        worker_wallet = "0xworker"
        client = _make_dispute_fake_client(
            dispute=self._open_dispute(),
            executors_by_wallet={worker_wallet: {"id": self.EXECUTOR_ID}},
        )
        monkeypatch.setattr(disputes_mod.db, "get_client", lambda: client)

        pay_mock = AsyncMock()
        monkeypatch.setattr(
            disputes_mod, "_trigger_resolution_payment", pay_mock
        )

        auth = _make_auth(wallet_address=worker_wallet, agent_id="0xworker")
        body = ResolveDisputeRequest(verdict="release", reason="self deal attempt")

        with pytest.raises(HTTPException):
            await resolve_dispute(
                dispute_id=self.DISPUTE_ID,
                body=body,
                request=_make_request(),
                auth=auth,
            )

        pay_mock.assert_not_awaited()
