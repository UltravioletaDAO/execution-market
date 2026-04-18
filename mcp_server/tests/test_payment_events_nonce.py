"""
Unit tests for EIP-3009 nonce persistence in payment_events (Task 5.1).

These exercise the ``nonce`` + ``token_address`` kwargs we added to
``log_payment_event``. The helper must:

  1. Promote both values into ``metadata`` (so migration 102's UNIQUE
     partial index can enforce uniqueness at the DB layer).
  2. Lowercase ``token_address`` before writing — the index is built on
     the raw JSONB value, so upper/lower-case variants would bypass it.
  3. Swallow the Postgres 23505 unique-violation benignly: a duplicate
     nonce is a REPLAY SIGNAL, not an error. We want the ingest path to
     keep moving and the original audit row to remain intact.
  4. Never raise. Audit logging is fire-and-forget by contract — a
     failure here must not crash the caller.

We substitute the Supabase client with an in-memory fake via monkeypatch
so the suite stays hermetic. The fake captures every insert and can be
programmed to raise the exact exception shapes Supabase surfaces in
practice (``APIError`` with ``code=23505``, or a bare ``Exception``
whose ``str()`` contains "duplicate key").
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from integrations.x402 import payment_events as pe


# ---------------------------------------------------------------------------
# Fake Supabase client
# ---------------------------------------------------------------------------


class _FakeInsertResult:
    """Mimics the Supabase ``.insert(...).execute()`` return shape."""

    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _FakeTable:
    """Captures insert payloads; can be programmed to raise on execute()."""

    def __init__(self, parent: "_FakeSupabaseClient") -> None:
        self._parent = parent
        self._pending: dict[str, Any] | None = None

    def insert(self, record: dict[str, Any]) -> "_FakeTable":
        self._pending = record
        return self

    def execute(self) -> _FakeInsertResult:
        assert self._pending is not None, "insert() must precede execute()"
        record = self._pending
        self._pending = None

        if self._parent.raise_on_insert is not None:
            raise self._parent.raise_on_insert

        self._parent.inserts.append(record)
        return _FakeInsertResult([{"id": f"evt-{len(self._parent.inserts)}"}])


class _FakeSupabaseClient:
    def __init__(self) -> None:
        self.inserts: list[dict[str, Any]] = []
        self.raise_on_insert: Exception | None = None

    def table(self, name: str) -> _FakeTable:
        assert name == "payment_events", f"unexpected table: {name}"
        return _FakeTable(self)


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> _FakeSupabaseClient:
    fake = _FakeSupabaseClient()

    # The helper does ``import supabase_client as db; db.get_client()``.
    # We build a stub module on the fly and insert it into sys.modules so
    # the import inside the helper resolves to our fake.
    import sys
    import types

    stub = types.ModuleType("supabase_client")
    stub.get_client = lambda: fake  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "supabase_client", stub)
    return fake


# ---------------------------------------------------------------------------
# Happy path — nonce & token_address promoted into metadata
# ---------------------------------------------------------------------------


class TestNoncePromotion:
    @pytest.mark.asyncio
    async def test_nonce_and_token_are_written_into_metadata(self, fake_db):
        result = await pe.log_payment_event(
            task_id="11111111-1111-1111-1111-111111111111",
            event_type="store_auth",
            status="success",
            from_address="0xAgent",
            amount_usdc=Decimal("0.25"),
            network="base",
            nonce="0xabc123",
            token_address="0xDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF",
        )

        assert result == "evt-1"
        assert len(fake_db.inserts) == 1

        record = fake_db.inserts[0]
        assert "metadata" in record, "metadata must be populated when nonce is set"
        md = record["metadata"]
        assert md["nonce"] == "0xabc123"
        # Lowercased — see migration 102 partial-index contract.
        assert md["token_address"] == "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"

    @pytest.mark.asyncio
    async def test_existing_metadata_is_preserved_and_merged(self, fake_db):
        await pe.log_payment_event(
            task_id="11111111-1111-1111-1111-111111111111",
            event_type="store_auth",
            nonce="0xfeed",
            token_address="0xABCD",
            metadata={"payment_mode": "fase2", "escrow_timing": "lock_on_assignment"},
        )
        md = fake_db.inserts[0]["metadata"]
        assert md["payment_mode"] == "fase2"
        assert md["escrow_timing"] == "lock_on_assignment"
        assert md["nonce"] == "0xfeed"
        assert md["token_address"] == "0xabcd"

    @pytest.mark.asyncio
    async def test_no_metadata_written_when_no_nonce_or_extras(self, fake_db):
        # Legacy call sites (balance_check, fee_sweep) pass neither nonce
        # nor metadata. We must not synthesise an empty {} — the column
        # default takes over and the partial index stays out of the way.
        await pe.log_payment_event(
            task_id="2",
            event_type="balance_check",
            status="success",
        )
        record = fake_db.inserts[0]
        assert "metadata" not in record


# ---------------------------------------------------------------------------
# Duplicate-nonce replay — must be swallowed benignly
# ---------------------------------------------------------------------------


class TestDuplicateNonceHandling:
    @pytest.mark.asyncio
    async def test_unique_violation_returns_none_without_raising(self, fake_db):
        class _APIError(Exception):
            """Mimics Supabase's PostgREST APIError string form."""

            def __str__(self) -> str:
                return (
                    "{'code': '23505', 'message': 'duplicate key value violates "
                    'unique constraint "idx_payment_events_nonce_unique"\'}'
                )

        fake_db.raise_on_insert = _APIError()

        result = await pe.log_payment_event(
            task_id="t-1",
            event_type="store_auth",
            nonce="0xreplayed",
            token_address="0xTokenX",
        )
        assert result is None  # benign — original row already exists

    @pytest.mark.asyncio
    async def test_duplicate_text_in_exception_also_swallowed(self, fake_db):
        # Some drivers raise with ``duplicate key`` in the error text but
        # no SQLSTATE. The heuristic must still catch it.
        fake_db.raise_on_insert = Exception("duplicate key violates constraint")

        result = await pe.log_payment_event(
            task_id="t-1",
            event_type="store_auth",
            nonce="0xABC",
            token_address="0xDeF",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_unrelated_errors_are_not_mistaken_for_dup(self, fake_db):
        # A connection refused / timeout / schema drift must NOT be
        # treated as a benign dup — we want the warning in logs and
        # ``None`` returned so the caller keeps going (non-blocking
        # audit contract), but not silently.
        fake_db.raise_on_insert = RuntimeError("connection refused")

        result = await pe.log_payment_event(
            task_id="t-1",
            event_type="store_auth",
            nonce="0xFF",
            token_address="0xAA",
        )
        # Return type same (None) — the distinction is in the log level,
        # but we at least pin that the exception is swallowed.
        assert result is None


# ---------------------------------------------------------------------------
# Backwards compatibility — existing callers keep working
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    @pytest.mark.asyncio
    async def test_caller_without_nonce_kwarg_still_writes_row(self, fake_db):
        # Existing call sites (there are ~40 of them in payment_dispatcher
        # alone) pass neither nonce nor token_address. Those must keep
        # producing identical rows.
        await pe.log_payment_event(
            task_id="t-1",
            event_type="escrow_authorize",
            status="success",
            tx_hash="0xTX",
            from_address="0xFrom",
            to_address="0xTo",
            amount_usdc=Decimal("1.5"),
            network="base",
            metadata={"mode": "fase2", "tier": "MICRO"},
        )
        record = fake_db.inserts[0]
        assert record["tx_hash"] == "0xTX"
        # Legacy metadata survived untouched.
        assert record["metadata"] == {"mode": "fase2", "tier": "MICRO"}
