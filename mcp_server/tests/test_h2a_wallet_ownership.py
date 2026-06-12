"""Wallet-fallback publisher ownership (H2A) + self-apply guard.

Anonymous Supabase sessions rotate on Dynamic logout/login cycles, orphaning
tasks whose human_user_id points at a dead session. Ownership now follows the
WALLET (proven via the signed link-wallet challenge): _h2a_is_owner backs all
five publisher gates, the my_tasks listing or-filters on human_wallet, and
link-wallet reclaims orphaned tasks. The apply endpoint refuses the publisher's
own wallet (self-apply) before any escrow machinery runs.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from api.h2a import JWTData, _h2a_is_owner


SESSION_A = "a49a8a40-1271-4f19-8ede-b01bfe40d261"
SESSION_B = "802822cb-4eaf-411f-931f-9532df44e4e3"
WALLET = "0xE4dC963C56979e0260fc146B87eE24F18220e545"


def _auth(user_id: str, wallet: str | None) -> JWTData:
    return JWTData(user_id=user_id, wallet_address=wallet)


class TestH2AIsOwner:
    def test_session_match(self):
        task = {"human_user_id": SESSION_A, "human_wallet": None}
        assert _h2a_is_owner(task, _auth(SESSION_A, None)) is True

    def test_wallet_match_after_session_rotation(self):
        """The exact prod failure: task owned by a dead session, same wallet."""
        task = {"human_user_id": SESSION_A, "human_wallet": WALLET.lower()}
        assert _h2a_is_owner(task, _auth(SESSION_B, WALLET)) is True

    def test_wallet_match_is_case_insensitive(self):
        task = {"human_user_id": SESSION_A, "human_wallet": WALLET.lower()}
        assert _h2a_is_owner(task, _auth(SESSION_B, WALLET.upper().replace("0X", "0x")))

    def test_no_match(self):
        task = {"human_user_id": SESSION_A, "human_wallet": WALLET.lower()}
        other = "0x" + "ab" * 20
        assert _h2a_is_owner(task, _auth(SESSION_B, other)) is False

    def test_empty_wallets_never_match(self):
        task = {"human_user_id": SESSION_A, "human_wallet": None}
        assert _h2a_is_owner(task, _auth(SESSION_B, None)) is False
        task2 = {"human_user_id": SESSION_A, "human_wallet": ""}
        assert _h2a_is_owner(task2, _auth(SESSION_B, "")) is False


class TestSelfApplyGuard:
    @pytest.mark.asyncio
    async def test_publisher_wallet_cannot_apply_to_own_task(self, monkeypatch):
        from api.routers import workers as workers_mod

        monkeypatch.setattr(
            workers_mod,
            "resolve_worker_identity",
            AsyncMock(return_value="executor-1"),
        )
        monkeypatch.setattr(
            workers_mod.db,
            "get_task",
            AsyncMock(return_value={"id": "task-1", "human_wallet": WALLET.lower()}),
        )
        monkeypatch.setattr(
            workers_mod.db,
            "get_executor_stats",
            AsyncMock(return_value={"wallet_address": WALLET}),
        )

        request = type("Req", (), {"executor_id": "executor-1", "message": "hi"})()
        with pytest.raises(HTTPException) as exc:
            await workers_mod.apply_to_task(
                raw_request=None,
                task_id="00000000-0000-0000-0000-000000000001",
                request=request,
                worker_auth=None,
            )
        assert exc.value.status_code == 403
        assert "your own task" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_guard_lookup_failure_falls_through(self, monkeypatch):
        """A DB hiccup in the guard must not block legitimate applies — the
        handler proceeds (and fails later on unrelated mocks, which is fine)."""
        from api.routers import workers as workers_mod

        monkeypatch.setattr(
            workers_mod,
            "resolve_worker_identity",
            AsyncMock(return_value="executor-1"),
        )
        monkeypatch.setattr(
            workers_mod.db,
            "get_task",
            AsyncMock(side_effect=RuntimeError("db down")),
        )

        request = type("Req", (), {"executor_id": "executor-1", "message": "hi"})()
        with pytest.raises(Exception) as exc:
            await workers_mod.apply_to_task(
                raw_request=None,
                task_id="00000000-0000-0000-0000-000000000001",
                request=request,
                worker_auth=None,
            )
        # Whatever failed downstream, it was NOT the self-apply 403.
        if isinstance(exc.value, HTTPException):
            assert exc.value.status_code != 403 or "your own task" not in str(
                exc.value.detail
            )


class TestLinkWalletReclaim:
    @pytest.mark.asyncio
    async def test_link_reclaims_orphaned_tasks(self, monkeypatch):
        """POST /account/link-wallet re-points human_user_id of tasks published
        by the proven wallet under previous sessions."""
        from eth_account import Account
        from eth_account.messages import encode_defunct
        from datetime import datetime, timezone

        from api.routers import account as account_mod

        acct = Account.create()
        wallet = acct.address.lower()
        timestamp = datetime.now(timezone.utc).isoformat()
        message = (
            f"Execution Market: link wallet {wallet} "
            f"to Supabase user {SESSION_B} at {timestamp}"
        )
        sig = Account.sign_message(
            encode_defunct(text=message), private_key=acct.key
        ).signature.hex()
        if not sig.startswith("0x"):
            sig = "0x" + sig

        calls = {}

        class _Result:
            def __init__(self, data):
                self.data = data

        class _Table:
            def __init__(self, name):
                self.name = name
                self.ops = []

            def update(self, payload):
                self.ops.append(("update", payload))
                return self

            def select(self, *a, **k):
                self.ops.append(("select", a))
                return self

            def eq(self, *a):
                self.ops.append(("eq", a))
                return self

            def neq(self, *a):
                self.ops.append(("neq", a))
                return self

            def limit(self, *a):
                return self

            def execute(self):
                calls.setdefault(self.name, []).append(list(self.ops))
                self.ops = []
                if self.name == "tasks":
                    return _Result([{"id": "t1"}])
                # executors: existing row already bound to this session
                return _Result([{"id": "exec-1", "user_id": SESSION_B}])

        class _Client:
            def table(self, name):
                return _Table(name)

        monkeypatch.setattr(account_mod.db, "get_client", lambda: _Client())
        monkeypatch.setattr(
            account_mod,
            "_decode_jwt_for_link",
            None,
            raising=False,
        )

        # Bypass the JWT decode with a stub payload.
        with patch("api.h2a._decode_supabase_jwt", return_value={"sub": SESSION_B}):
            from api.routers._models import LinkWalletRequest

            req = LinkWalletRequest(
                wallet_address=wallet, message=message, signature=sig
            )
            result = await account_mod.link_wallet_to_session(
                request=req, authorization="Bearer dummy-token"
            )

        assert result["executor_id"] == "exec-1"
        # The tasks table got the reclaim update with the new session sub.
        tasks_calls = calls.get("tasks", [])
        assert tasks_calls, "expected a reclaim update on tasks"
        first = tasks_calls[0]
        assert ("update", {"human_user_id": SESSION_B}) in first
        assert ("eq", ("publisher_type", "human")) in first
        assert ("eq", ("human_wallet", wallet)) in first
        assert ("neq", ("human_user_id", SESSION_B)) in first
