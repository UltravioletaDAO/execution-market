"""Tests for jobs/clawkey_sync.py.

Mocks both Supabase and the upstream ClawKey HTTP client. Covers the
single-row reconciliation matrix (verified / revoked / unchanged /
upstream_error) and the health pulse / master switch behaviour.
"""

from __future__ import annotations

import os
import sys
import time as _time
from pathlib import Path
from typing import Any

import pytest

# Ensure mcp_server root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Master switch must be set before importing the module so the loop is alive.
os.environ.setdefault("EM_CLAWKEY_ENABLED", "true")

from jobs import clawkey_sync as job  # noqa: E402
from integrations.clawkey.client import ClawKeyResult  # noqa: E402

pytestmark = pytest.mark.clawkey


# ---------------------------------------------------------------------------
# Supabase stub
# ---------------------------------------------------------------------------


class _Result:
    def __init__(self, data: list[dict]):
        self.data = data


class _QB:
    """Chainable Postgrest stub. Records updates."""

    def __init__(self, parent: "_FakeDB", table_name: str):
        self._parent = parent
        self._table_name = table_name
        self._select_filters: list[tuple[str, Any]] = []

    def select(self, *_args: Any, **_kwargs: Any) -> "_QB":
        return self

    def eq(self, col: str, val: Any) -> "_QB":
        self._select_filters.append((col, val))
        return self

    def limit(self, *_args: Any, **_kwargs: Any) -> "_QB":
        return self

    @property
    def not_(self) -> "_QB":
        return self

    def is_(self, *_args: Any, **_kwargs: Any) -> "_QB":
        return self

    def update(self, row: dict) -> "_QB":
        self._parent.updates.append(
            {
                "table": self._table_name,
                "row": row,
                "filters": list(self._select_filters),
            }
        )
        return self

    def execute(self) -> _Result:
        if self._table_name == "executors":
            return _Result(self._parent.executor_rows)
        return _Result([])


class _FakeDB:
    def __init__(self) -> None:
        self.executor_rows: list[dict] = []
        self.updates: list[dict] = []

    def table(self, name: str) -> _QB:
        return _QB(self, name)


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> _FakeDB:
    fake = _FakeDB()
    import supabase_client as sb

    monkeypatch.setattr(sb, "get_client", lambda: fake)
    return fake


# ---------------------------------------------------------------------------
# Stub the upstream client at the import site
# ---------------------------------------------------------------------------


def _patch_verify(monkeypatch: pytest.MonkeyPatch, result_or_exc: Any) -> list[str]:
    """Replace verify_by_public_key with a stub. Records call args.

    ``result_or_exc`` is either a ClawKeyResult (returned) or an Exception
    (raised). Returns the list that records pubkeys called.
    """
    calls: list[str] = []

    async def fake_verify(pubkey: str, *, use_cache: bool = True) -> ClawKeyResult:
        calls.append(pubkey)
        if isinstance(result_or_exc, Exception):
            raise result_or_exc
        return result_or_exc

    from integrations.clawkey import client as ck_client

    monkeypatch.setattr(ck_client, "verify_by_public_key", fake_verify)
    return calls


def _result(verified: bool, human_id: str | None = None) -> ClawKeyResult:
    return ClawKeyResult(
        registered=verified,
        verified=verified,
        human_id=human_id,
        registered_at="2026-04-30T00:00:00Z" if verified else None,
        raw={},
    )


# ---------------------------------------------------------------------------
# _sync_one_executor — the core reconciliation matrix
# ---------------------------------------------------------------------------


class TestSyncOneExecutor:
    @pytest.mark.asyncio
    async def test_no_public_key_short_circuits(self, fake_db: _FakeDB) -> None:
        out = await job._sync_one_executor(
            {"id": "exec-x", "clawkey_public_key": None, "clawkey_verified": False}
        )
        assert out == "unchanged"
        assert fake_db.updates == []

    @pytest.mark.asyncio
    async def test_unchanged_when_state_matches(
        self, fake_db: _FakeDB, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_verify(monkeypatch, _result(True, "hum-1"))
        out = await job._sync_one_executor(
            {
                "id": "exec-1",
                "clawkey_public_key": "PubKey1",
                "clawkey_verified": True,
                "clawkey_human_id": "hum-1",
            }
        )
        assert out == "unchanged"
        # No DB write when nothing drifted
        assert fake_db.updates == []

    @pytest.mark.asyncio
    async def test_promotes_when_db_false_upstream_true(
        self, fake_db: _FakeDB, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_verify(monkeypatch, _result(True, "hum-new"))
        out = await job._sync_one_executor(
            {
                "id": "exec-2",
                "clawkey_public_key": "PubKey2",
                "clawkey_verified": False,
                "clawkey_human_id": None,
            }
        )
        assert out == "verified"
        assert len(fake_db.updates) == 1
        upd = fake_db.updates[0]
        assert upd["table"] == "executors"
        assert upd["row"]["clawkey_verified"] is True
        assert upd["row"]["clawkey_human_id"] == "hum-new"

    @pytest.mark.asyncio
    async def test_revokes_when_db_true_upstream_false(
        self, fake_db: _FakeDB, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The headline path: ClawKey upstream revoked → DB must follow.
        _patch_verify(monkeypatch, _result(False, None))
        out = await job._sync_one_executor(
            {
                "id": "exec-3",
                "clawkey_public_key": "PubKey3",
                "clawkey_verified": True,
                "clawkey_human_id": "hum-3",
            }
        )
        assert out == "revoked"
        assert len(fake_db.updates) == 1
        assert fake_db.updates[0]["row"]["clawkey_verified"] is False

    @pytest.mark.asyncio
    async def test_upstream_exception_is_swallowed(
        self, fake_db: _FakeDB, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_verify(monkeypatch, RuntimeError("upstream 503"))
        out = await job._sync_one_executor(
            {
                "id": "exec-4",
                "clawkey_public_key": "PubKey4",
                "clawkey_verified": True,
                "clawkey_human_id": "hum-4",
            }
        )
        assert out == "upstream_error"
        # No DB write — we keep the previous state until upstream answers
        assert fake_db.updates == []

    @pytest.mark.asyncio
    async def test_human_id_drift_triggers_write(
        self, fake_db: _FakeDB, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Regression: an earlier version had `db_hid or "" == upstream`
        # which, by Python operator precedence, evaluated as
        # `db_hid or ("" == upstream)` and silently classified drift as
        # "unchanged" whenever the DB human_id was truthy. Same verified
        # flag on both sides + different human_id MUST trigger a write.
        _patch_verify(monkeypatch, _result(True, "hum-NEW"))
        out = await job._sync_one_executor(
            {
                "id": "exec-drift",
                "clawkey_public_key": "PubKeyDrift",
                "clawkey_verified": True,
                "clawkey_human_id": "hum-OLD",
            }
        )
        # verified flag did not flip, so this is neither "verified" nor
        # "revoked" — the bookkeeping branch returns "unchanged" but a
        # DB write must still have occurred to persist the new human_id.
        assert out == "unchanged"
        assert len(fake_db.updates) == 1
        assert fake_db.updates[0]["row"]["clawkey_human_id"] == "hum-NEW"


# ---------------------------------------------------------------------------
# get_clawkey_sync_health — the pulse exposed to /health
# ---------------------------------------------------------------------------


class TestHealthPulse:
    def test_starting_before_first_cycle(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(job, "_last_cycle_time", 0.0)
        monkeypatch.setattr(job, "_last_cycle_stats", {})
        assert job.get_clawkey_sync_health() == {"status": "starting"}

    def test_healthy_when_recent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(job, "_last_cycle_time", _time.time() - 5)
        monkeypatch.setattr(
            job,
            "_last_cycle_stats",
            {
                "scanned": 3,
                "verified": 1,
                "revoked": 0,
                "upstream_error": 0,
                "unchanged": 2,
            },
        )
        h = job.get_clawkey_sync_health()
        assert h["status"] == "healthy"
        assert h["last_cycle_age_s"] >= 0
        assert h["last_cycle_stats"]["scanned"] == 3

    def test_stale_when_two_intervals_old(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # CLAWKEY_SYNC_INTERVAL defaults to 21600s. Two intervals ago is stale.
        monkeypatch.setattr(
            job, "_last_cycle_time", _time.time() - (job.CLAWKEY_SYNC_INTERVAL * 2 + 60)
        )
        monkeypatch.setattr(job, "_last_cycle_stats", {"scanned": 0})
        h = job.get_clawkey_sync_health()
        assert h["status"] == "stale"


# ---------------------------------------------------------------------------
# Master switch — when EM_CLAWKEY_ENABLED is off, the loop must exit cleanly.
# ---------------------------------------------------------------------------


class TestMasterSwitch:
    @pytest.mark.asyncio
    async def test_loop_returns_immediately_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("EM_CLAWKEY_ENABLED", "false")
        # If the master switch leaks, the loop sleeps 30s+ — our timeout
        # would fail. So a clean return inside the timeout proves the path.
        import asyncio

        await asyncio.wait_for(job.run_clawkey_sync_loop(), timeout=2.0)
