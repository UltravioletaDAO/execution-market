"""Multi-executor sessions (one Supabase sub, several linked wallets).

POST /account/link-wallet binds one executor row per proven wallet to the SAME
session sub, so a user with an external + an embedded wallet owns TWO executor
rows. The limit-1 lookups (verify_worker_auth, verify_jwt_auth) pick only one:

- Worker side (EM_REQUIRE_WORKER_AUTH=true in prod): a body executor_id naming
  the SIBLING executor of the same user must not 403 on apply/submit —
  _executor_belongs_to_user verifies the binding fail-closed.
- Publisher side: _h2a_is_owner / the my_tasks filters must match ANY proven
  wallet of the session, not just the most recently updated one.
"""

import sys
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from api.auth import (
    WorkerAuth,
    _enforce_worker_identity,
    _executor_belongs_to_user,
    resolve_worker_identity,
)
from api.h2a import JWTData, _h2a_is_owner, _h2a_owner_filter, verify_jwt_auth

pytestmark = pytest.mark.security

USER = "a49a8a40-1271-4f19-8ede-b01bfe40d261"
EXEC_A = "exec-aaaa"
EXEC_B = "exec-bbbb"
WALLET_EXTERNAL = "0xE4dC963C56979e0260fc146B87eE24F18220e545".lower()
WALLET_EMBEDDED = "0x" + "ab" * 20


@contextmanager
def _enforce(on: bool):
    with patch.object(sys.modules["api.auth"], "_REQUIRE_WORKER_AUTH", on):
        yield


def _request():
    req = MagicMock()
    req.url.path = "/api/v1/tasks/task-1234/submit"
    req.headers = {}
    return req


class _Result:
    def __init__(self, data):
        self.data = data


def _client_returning(data):
    """Fake supabase client whose chained query returns _Result(data)."""
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = _Result(
        data
    )
    return client


# --------------------------------------------------------------------------- #
# _executor_belongs_to_user — fail-closed DB-verified sibling check
# --------------------------------------------------------------------------- #
class TestExecutorBelongsToUser:
    def test_true_when_row_bound_to_user(self):
        with patch(
            "supabase_client.get_client",
            return_value=_client_returning([{"id": EXEC_B}]),
        ):
            assert _executor_belongs_to_user(EXEC_B, USER) is True

    def test_false_when_no_row(self):
        with patch("supabase_client.get_client", return_value=_client_returning([])):
            assert _executor_belongs_to_user(EXEC_B, USER) is False

    def test_false_on_db_error(self):
        with patch("supabase_client.get_client", side_effect=RuntimeError("db down")):
            assert _executor_belongs_to_user(EXEC_B, USER) is False

    def test_false_when_data_is_mock_not_list(self):
        # Mocked DB clients return truthy MagicMocks for .data — only a real
        # non-empty list counts (isinstance guard).
        client = MagicMock()
        with patch("supabase_client.get_client", return_value=client):
            assert _executor_belongs_to_user(EXEC_B, USER) is False

    def test_false_without_user_id(self):
        assert _executor_belongs_to_user(EXEC_B, None) is False
        assert _executor_belongs_to_user("", USER) is False


# --------------------------------------------------------------------------- #
# _enforce_worker_identity — sibling executor of the same user (flag ON)
# --------------------------------------------------------------------------- #
class TestEnforceWorkerIdentitySiblings:
    def test_mismatch_same_user_returns_body(self):
        wa = WorkerAuth(executor_id=EXEC_A, user_id=USER, auth_method="jwt")
        with (
            _enforce(True),
            patch("api.auth._executor_belongs_to_user", return_value=True),
        ):
            assert _enforce_worker_identity(wa, EXEC_B, "/p") == EXEC_B

    def test_mismatch_other_user_still_403(self):
        wa = WorkerAuth(executor_id=EXEC_A, user_id=USER, auth_method="jwt")
        with (
            _enforce(True),
            patch("api.auth._executor_belongs_to_user", return_value=False),
        ):
            with pytest.raises(HTTPException) as exc:
                _enforce_worker_identity(wa, EXEC_B, "/p")
            assert exc.value.status_code == 403

    def test_mismatch_without_user_id_still_403(self):
        # No user_id on the principal -> the sibling check cannot verify
        # anything (fail-closed, no DB call needed).
        wa = WorkerAuth(executor_id=EXEC_A, auth_method="jwt")
        with _enforce(True):
            with pytest.raises(HTTPException) as exc:
                _enforce_worker_identity(wa, EXEC_B, "/p")
            assert exc.value.status_code == 403


# --------------------------------------------------------------------------- #
# resolve_worker_identity — the apply/submit path (flag ON)
# --------------------------------------------------------------------------- #
class TestResolveWorkerIdentitySiblings:
    @pytest.mark.asyncio
    async def test_mismatch_same_user_returns_body(self):
        wa = WorkerAuth(executor_id=EXEC_A, user_id=USER, auth_method="jwt")
        with (
            _enforce(True),
            patch("api.auth._executor_belongs_to_user", return_value=True),
        ):
            out = await resolve_worker_identity(
                _request(), wa, EXEC_B, task_id="task-1234"
            )
        assert out == EXEC_B

    @pytest.mark.asyncio
    async def test_mismatch_other_user_still_403(self):
        wa = WorkerAuth(executor_id=EXEC_A, user_id=USER, auth_method="jwt")
        with (
            _enforce(True),
            patch("api.auth._executor_belongs_to_user", return_value=False),
        ):
            with pytest.raises(HTTPException) as exc:
                await resolve_worker_identity(
                    _request(), wa, EXEC_B, task_id="task-1234"
                )
            assert exc.value.status_code == 403


# --------------------------------------------------------------------------- #
# Publisher side: ownership matches ANY proven wallet of the session
# --------------------------------------------------------------------------- #
class TestH2AOwnerMultiWallet:
    def test_owner_via_second_wallet(self):
        auth = JWTData(
            user_id="other-session",
            wallet_address=WALLET_EMBEDDED,
            wallet_addresses=[WALLET_EMBEDDED, WALLET_EXTERNAL],
        )
        task = {"human_user_id": USER, "human_wallet": WALLET_EXTERNAL}
        assert _h2a_is_owner(task, auth) is True

    def test_not_owner_when_no_wallet_matches(self):
        auth = JWTData(
            user_id="other-session",
            wallet_address=WALLET_EMBEDDED,
            wallet_addresses=[WALLET_EMBEDDED],
        )
        task = {"human_user_id": USER, "human_wallet": WALLET_EXTERNAL}
        assert _h2a_is_owner(task, auth) is False

    def test_owner_filter_includes_all_wallets(self):
        auth = JWTData(
            user_id=USER,
            wallet_address=WALLET_EMBEDDED,
            wallet_addresses=[WALLET_EMBEDDED, WALLET_EXTERNAL],
        )
        expr = _h2a_owner_filter(auth)
        assert f"human_user_id.eq.{USER}" in expr
        assert f"human_wallet.eq.{WALLET_EMBEDDED}" in expr
        assert f"human_wallet.eq.{WALLET_EXTERNAL}" in expr

    def test_owner_filter_none_without_wallets(self):
        auth = JWTData(user_id=USER)
        assert _h2a_owner_filter(auth) is None


# --------------------------------------------------------------------------- #
# verify_jwt_auth — resolves ALL wallets for the session
# --------------------------------------------------------------------------- #
class TestVerifyJwtAuthMultiWallet:
    @pytest.mark.asyncio
    async def test_collects_all_wallets_most_recent_first(self, monkeypatch):
        import api.h2a as h2a_mod

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = _Result(
            [
                {"wallet_address": WALLET_EXTERNAL},
                {"wallet_address": WALLET_EMBEDDED},
            ]
        )
        monkeypatch.setattr(h2a_mod.db, "get_client", lambda: client)

        with patch("api.h2a._decode_supabase_jwt", return_value={"sub": USER}):
            auth = await verify_jwt_auth("Bearer dummy-token")

        assert auth.user_id == USER
        assert auth.wallet_address == WALLET_EXTERNAL
        assert auth.wallet_addresses == [WALLET_EXTERNAL, WALLET_EMBEDDED]

    @pytest.mark.asyncio
    async def test_wallet_claim_populates_single_entry_list(self):
        with patch(
            "api.h2a._decode_supabase_jwt",
            return_value={"sub": USER, "wallet_address": WALLET_EXTERNAL},
        ):
            auth = await verify_jwt_auth("Bearer dummy-token")
        assert auth.wallet_address == WALLET_EXTERNAL
        assert auth.wallet_addresses == [WALLET_EXTERNAL]


# --------------------------------------------------------------------------- #
# main.py config: H2A on-chain endpoints get the long request timeout; CORS
# preflight admits PATCH (account/wallet) and X-Payment-Auth (escrow assign).
# --------------------------------------------------------------------------- #
class TestMainConfig:
    """Source-level assertions: importing main twice in one pytest process
    trips the local pydantic-shadowing flake (conftest restores sys.modules
    between tests, so a second import re-executes the whole tree), and
    test_worker_auth_required.py already imports main for the boot guard.
    The middleware/CORS values are module-level literals, so asserting on the
    source is exact and side-effect free."""

    @staticmethod
    def _main_source() -> str:
        import pathlib

        return (pathlib.Path(__file__).resolve().parents[1] / "main.py").read_text(
            encoding="utf-8"
        )

    def test_h2a_paths_get_long_timeout(self):
        src = self._main_source()
        block = src.split("LONG_TIMEOUT_PATHS = (", 1)[1].split(")", 1)[0]
        assert '"/api/v1/h2a/"' in block
        assert '"/api/v1/tasks/"' in block

    def test_cors_allows_patch_and_payment_auth(self):
        src = self._main_source()
        methods = src.split("allow_methods=[", 1)[1].split("]", 1)[0]
        assert '"PATCH"' in methods
        headers = src.split("allow_headers=[", 1)[1].split("]", 1)[0]
        assert '"X-Payment-Auth"' in headers
