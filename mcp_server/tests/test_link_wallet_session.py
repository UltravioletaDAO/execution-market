"""Tests for POST /api/v1/account/link-wallet — the session-binding bootstrap.

This endpoint replaces the revoked link_wallet_to_session RPC (migration 092)
and the anon-revoked get_or_create_executor (migration 111). It binds
executors.user_id to the Supabase JWT sub after verifying a wallet-ownership
signature, so worker-auth endpoints (apply/submit/withdraw) can resolve the
executor again under EM_REQUIRE_WORKER_AUTH=true.

The handler is exercised directly (the WSL TestClient is broken — see
test_worker_auth_required.py). Signatures are real (eth_account); the JWT decode
and Supabase client are mocked.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import HTTPException

pytestmark = pytest.mark.security

from api.routers._models import LinkWalletRequest
from api.routers.account import link_wallet_to_session

SUB = "11111111-1111-1111-1111-111111111111"


def _sign(acct, message: str) -> str:
    signed = acct.sign_message(encode_defunct(text=message))
    sig = signed.signature.hex()
    return sig if sig.startswith("0x") else "0x" + sig


def _challenge(wallet: str, sub: str = SUB, ts: datetime | None = None) -> str:
    ts = ts or datetime.now(timezone.utc)
    return (
        f"Execution Market: link wallet {wallet} to Supabase user {sub} "
        f"at {ts.isoformat()}"
    )


def _mock_client(existing_row):
    """Mock the Supabase service_role client.

    existing_row: list passed back from the executors lookup .execute().data
    """
    client = MagicMock()
    lookup = MagicMock()
    lookup.execute.return_value = MagicMock(data=existing_row)
    client.table.return_value.select.return_value.eq.return_value.limit.return_value = (
        lookup
    )
    client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )
    return client


@pytest.mark.asyncio
async def test_valid_signature_binds_user_id():
    acct = Account.create()
    wallet = acct.address.lower()
    msg = _challenge(wallet)
    req = LinkWalletRequest(
        wallet_address=wallet, message=msg, signature=_sign(acct, msg)
    )
    client = _mock_client([{"id": "exec-1", "user_id": None}])

    with (
        patch("api.h2a._decode_supabase_jwt", return_value={"sub": SUB}),
        patch("api.routers.account.db.get_client", return_value=client),
    ):
        out = await link_wallet_to_session(req, authorization="Bearer tok")

    assert out["linked"] is True
    assert out["executor_id"] == "exec-1"
    # The update must set user_id to the JWT sub.
    update_arg = client.table.return_value.update.call_args[0][0]
    assert update_arg["user_id"] == SUB


@pytest.mark.asyncio
async def test_already_linked_is_noop():
    acct = Account.create()
    wallet = acct.address.lower()
    msg = _challenge(wallet)
    req = LinkWalletRequest(
        wallet_address=wallet, message=msg, signature=_sign(acct, msg)
    )
    client = _mock_client([{"id": "exec-1", "user_id": SUB}])

    with (
        patch("api.h2a._decode_supabase_jwt", return_value={"sub": SUB}),
        patch("api.routers.account.db.get_client", return_value=client),
    ):
        out = await link_wallet_to_session(req, authorization="Bearer tok")

    assert out["linked"] is False
    # The executor BIND is skipped (already linked), but the H2A task reclaim
    # still runs: tasks published by this wallet under rotated sessions follow
    # the wallet. The only update is the reclaim payload — never a user_id bind.
    update_calls = client.table.return_value.update.call_args_list
    assert len(update_calls) == 1
    assert set(update_calls[0].args[0].keys()) == {"human_user_id"}


@pytest.mark.asyncio
async def test_captured_signature_cannot_rebind_to_other_session():
    """Account-takeover guard: a valid signature the victim made to bind to
    THEIR session must not rebind the executor when replayed under a different
    JWT. The sub is bound into the message, so the prefix check fails (400)."""
    victim_sub = "22222222-2222-2222-2222-222222222222"
    attacker_sub = "33333333-3333-3333-3333-333333333333"
    acct = Account.create()  # the victim's wallet
    wallet = acct.address.lower()
    # Victim signs consent to bind to victim_sub — a genuine, valid signature.
    msg = _challenge(wallet, sub=victim_sub)
    req = LinkWalletRequest(
        wallet_address=wallet, message=msg, signature=_sign(acct, msg)
    )

    # Attacker replays it under their own JWT.
    with patch("api.h2a._decode_supabase_jwt", return_value={"sub": attacker_sub}):
        with pytest.raises(HTTPException) as exc:
            await link_wallet_to_session(req, authorization="Bearer attacker-tok")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_signature_mismatch_403():
    signer = Account.create()
    other = Account.create()  # message claims `other` but `signer` signs it
    wallet = other.address.lower()
    msg = _challenge(wallet)
    req = LinkWalletRequest(
        wallet_address=wallet, message=msg, signature=_sign(signer, msg)
    )

    with patch("api.h2a._decode_supabase_jwt", return_value={"sub": SUB}):
        with pytest.raises(HTTPException) as exc:
            await link_wallet_to_session(req, authorization="Bearer tok")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_missing_authorization_401():
    acct = Account.create()
    wallet = acct.address.lower()
    msg = _challenge(wallet)
    req = LinkWalletRequest(
        wallet_address=wallet, message=msg, signature=_sign(acct, msg)
    )
    with pytest.raises(HTTPException) as exc:
        await link_wallet_to_session(req, authorization=None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_expired_challenge_400():
    acct = Account.create()
    wallet = acct.address.lower()
    stale = datetime.now(timezone.utc) - timedelta(minutes=20)
    msg = _challenge(wallet, ts=stale)
    req = LinkWalletRequest(
        wallet_address=wallet, message=msg, signature=_sign(acct, msg)
    )

    with patch("api.h2a._decode_supabase_jwt", return_value={"sub": SUB}):
        with pytest.raises(HTTPException) as exc:
            await link_wallet_to_session(req, authorization="Bearer tok")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_wrong_message_prefix_400():
    acct = Account.create()
    wallet = acct.address.lower()
    # Valid signature, but the message is not the expected challenge schema.
    msg = f"gm please link {wallet} at {datetime.now(timezone.utc).isoformat()}"
    req = LinkWalletRequest(
        wallet_address=wallet, message=msg, signature=_sign(acct, msg)
    )

    with patch("api.h2a._decode_supabase_jwt", return_value={"sub": SUB}):
        with pytest.raises(HTTPException) as exc:
            await link_wallet_to_session(req, authorization="Bearer tok")
    assert exc.value.status_code == 400
