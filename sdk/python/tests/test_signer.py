"""Tests for execution_market._signer.

Covers the wire-format invariants (lowercase keyid, alg=eip191, deterministic
fingerprint), the OWS subprocess contract, and the retry helper. All tests
are pure unit tests — no HTTP, no real `ows` CLI invocation.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from execution_market._signer import (
    OwsEM8128Client,
    OwsSignError,
    task_fingerprint,
    with_backoff,
)


# ----------------------------------------------------------------------
# task_fingerprint — pure function, deterministic identity hash
# ----------------------------------------------------------------------


def test_task_fingerprint_is_deterministic():
    body = {
        "title": "Verify storefront open",
        "instructions": "Photo with GPS",
        "bounty_usd": 0.10,
        "deadline_hours": 4,
        "evidence_required": ["photo_geo"],
        "payment_network": "base",
    }
    assert task_fingerprint(body) == task_fingerprint(body)


def test_task_fingerprint_normalizes_string_case_and_whitespace():
    a = {"title": "Hello World", "bounty_usd": 1.0}
    b = {"title": "  hello world  ", "bounty_usd": 1.0}
    assert task_fingerprint(a) == task_fingerprint(b)


def test_task_fingerprint_ignores_metadata_fields():
    base = {"title": "T", "bounty_usd": 1.0, "deadline_hours": 4}
    with_meta = {**base, "agent_name": "RandomBot", "skills_required": ["x"], "arbiter_mode": "auto"}
    assert task_fingerprint(base) == task_fingerprint(with_meta)


def test_task_fingerprint_changes_when_identity_field_changes():
    base = {"title": "T", "bounty_usd": 1.0}
    diff = {"title": "T", "bounty_usd": 2.0}
    assert task_fingerprint(base) != task_fingerprint(diff)


def test_task_fingerprint_returns_hex_sha256():
    body = {"title": "T"}
    fp = task_fingerprint(body)
    # 64 hex chars = sha256 hex digest
    assert len(fp) == 64
    assert all(c in "0123456789abcdef" for c in fp)


# ----------------------------------------------------------------------
# Construction / validation
# ----------------------------------------------------------------------


def test_constructor_requires_wallet_name():
    with pytest.raises(ValueError, match="wallet_name"):
        OwsEM8128Client(wallet_name="", wallet_address="0x" + "a" * 40)


def test_constructor_rejects_bad_address():
    with pytest.raises(ValueError, match="42-char"):
        OwsEM8128Client(wallet_name="x", wallet_address="0xabc")
    with pytest.raises(ValueError, match="42-char"):
        OwsEM8128Client(wallet_name="x", wallet_address="not-an-address")


def test_constructor_strips_trailing_slash_from_api_url():
    c = OwsEM8128Client(
        wallet_name="x",
        wallet_address="0x" + "a" * 40,
        api_url="https://api.execution.market/",
    )
    assert c.api_url == "https://api.execution.market"


# ----------------------------------------------------------------------
# _build_sig_params — formatting of @signature-params per RFC 9421
# ----------------------------------------------------------------------


def _client():
    return OwsEM8128Client(wallet_name="my-agent", wallet_address="0x" + "a" * 40)


def test_build_sig_params_includes_alg_eip191():
    c = _client()
    params = {"created": 100, "expires": 400, "nonce": "N", "keyid": "K", "alg": "eip191"}
    sp = c._build_sig_params(["@method", "@authority"], params)
    assert 'alg="eip191"' in sp


def test_build_sig_params_orders_covered_first_then_params():
    c = _client()
    params = {"created": 100, "expires": 400, "nonce": "N", "keyid": "K", "alg": "eip191"}
    sp = c._build_sig_params(["@method", "@authority", "@path"], params)
    # covered tuple comes first, parenthesized, with quoted components
    assert sp.startswith('("@method" "@authority" "@path")')
    # then the params, in canonical order
    tail = sp.split(";", 1)[1]
    assert tail.startswith("created=100;expires=400;")
    assert "alg=\"eip191\"" in tail


# ----------------------------------------------------------------------
# Keyid lowercasing — the bug v10.0.0 fixed (skill Option C → removed)
# ----------------------------------------------------------------------


def test_keyid_is_lowercased_even_when_address_is_checksum():
    """The wallet address may be passed in checksum case, but the keyid
    we send MUST be lowercase — the server normalizes both sides
    (verifier.py:152/249/779). Mismatched case → silent auth failure.
    """
    checksum_addr = "0x" + "Aa" * 20  # mixed case (40 hex chars)
    c = OwsEM8128Client(wallet_name="x", wallet_address=checksum_addr)

    # Capture what _sign_eip191 receives — that's the signature base, which
    # has the keyid embedded in its @signature-params line.
    captured = {}

    def fake_sign(msg: str) -> bytes:
        captured["msg"] = msg
        return b"\x00" * 65  # valid 65-byte signature

    fake_nonce_resp = MagicMock()
    fake_nonce_resp.raise_for_status = MagicMock()
    fake_nonce_resp.json = MagicMock(return_value={"nonce": "N"})

    with patch.object(c, "_sign_eip191", side_effect=fake_sign), \
         patch("execution_market._signer.httpx.AsyncClient") as fake_client_cls:
        # Async context manager → returns a client whose .get is async
        fake_client = MagicMock()

        async def fake_get(url):
            return fake_nonce_resp

        fake_client.get = fake_get
        fake_client_cls.return_value.__aenter__.return_value = fake_client

        asyncio.run(c._sign_headers("GET", "https://api.execution.market/api/v1/tasks"))

    msg = captured["msg"]
    # keyid must contain the lowercased address, never the checksum
    assert checksum_addr.lower() in msg, "keyid is not using lowercase wallet address"
    assert checksum_addr not in msg, "keyid leaked checksum-case wallet address"
    # alg must be eip191
    assert 'alg="eip191"' in msg


# ----------------------------------------------------------------------
# _sign_eip191 — subprocess contract
# ----------------------------------------------------------------------


def _ows_proc_ok(sig_bytes: bytes = b"\x00" * 65) -> MagicMock:
    """Build a successful subprocess.CompletedProcess mock."""
    out = json.dumps({"signature": sig_bytes.hex()})
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.stdout = out
    proc.returncode = 0
    return proc


def test_sign_eip191_invokes_ows_with_hex_encoding():
    c = _client()
    with patch("execution_market._signer.subprocess.run", return_value=_ows_proc_ok()) as run:
        sig = c._sign_eip191("hello\nworld")
        assert len(sig) == 65
        args = run.call_args[0][0]
        # The CLI command: ows sign message --chain base --wallet <name> --message <hex> --encoding hex --json
        assert "sign" in args and "message" in args
        assert "--wallet" in args
        assert "my-agent" in args
        assert "--encoding" in args and "hex" in args
        assert "--json" in args
        # Message is passed as hex of utf-8 bytes, never raw (avoids shell-escape traps)
        hex_idx = args.index("--message") + 1
        assert args[hex_idx] == "hello\nworld".encode("utf-8").hex()


def test_sign_eip191_raises_on_short_signature():
    c = _client()
    with patch("execution_market._signer.subprocess.run", return_value=_ows_proc_ok(b"\x00" * 64)):
        with pytest.raises(OwsSignError, match="64-byte"):
            c._sign_eip191("anything")


def test_sign_eip191_raises_helpful_error_when_ows_not_installed():
    c = _client()
    with patch("execution_market._signer.subprocess.run", side_effect=FileNotFoundError("ows")):
        with pytest.raises(OwsSignError, match="OWS CLI not found"):
            c._sign_eip191("anything")


def test_sign_eip191_raises_on_subprocess_error():
    c = _client()
    err = subprocess.CalledProcessError(1, ["ows"], output="", stderr="vault locked")
    with patch("execution_market._signer.subprocess.run", side_effect=err):
        with pytest.raises(OwsSignError, match="vault locked"):
            c._sign_eip191("anything")


# ----------------------------------------------------------------------
# with_backoff — retry helper
# ----------------------------------------------------------------------


def test_with_backoff_returns_first_success_without_sleeping():
    async def fn():
        return "ok"

    with patch("execution_market._signer.asyncio.sleep") as sleep_mock:
        result = asyncio.run(with_backoff(fn, tries=4))
    assert result == "ok"
    sleep_mock.assert_not_called()


def test_with_backoff_retries_until_success():
    attempts = {"n": 0}

    async def fn():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    async def fake_sleep(_):
        return None

    with patch("execution_market._signer.asyncio.sleep", side_effect=fake_sleep) as sleep_mock:
        result = asyncio.run(with_backoff(fn, tries=4, base=0.01))
    assert result == "ok"
    assert attempts["n"] == 3
    # Two failures → two sleeps before the successful third call
    assert sleep_mock.call_count == 2


def test_with_backoff_raises_after_exhausting_tries():
    async def fn():
        raise ValueError("nope")

    async def fake_sleep(_):
        return None

    with patch("execution_market._signer.asyncio.sleep", side_effect=fake_sleep):
        with pytest.raises(ValueError, match="nope"):
            asyncio.run(with_backoff(fn, tries=3, base=0.01))
