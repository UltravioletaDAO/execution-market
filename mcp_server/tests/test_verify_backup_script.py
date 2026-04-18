"""
Tests for scripts/verify_backup.py (Phase 6.3 — Backup/DR canary).

The script is deliberately standalone (no mcp_server package imports) so
it can run as a cron canary with minimal dependencies. These tests load
it via importlib + register into sys.modules so @dataclass resolution
works under Python 3.11.

Coverage:
  - URL redaction strips credentials so stream-safe logs never leak.
  - Missing env vars exit 2 before any network call.
  - All-green path returns a report with ``all_ok=True`` and every table
    marked OK.
  - A 404 on a critical table flips ``all_ok=False`` with an explicit
    error.
  - Strict mode flips a stale table into a hard failure; non-strict
    mode keeps ``ok=True`` but records ``staleness_hours``.
  - Unexpectedly empty NONEMPTY_TABLES fail even on a 200 response.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "verify_backup.py"


@pytest.fixture(scope="module")
def verify_backup_module():
    """Load verify_backup.py as a module, register into sys.modules."""
    spec = importlib.util.spec_from_file_location("verify_backup", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["verify_backup"] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("verify_backup", None)


def _mock_transport(handler):
    """Wrap a dict-of-(path, handler) map into an httpx MockTransport."""
    return httpx.MockTransport(handler)


def _iso(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def _success_handler(rows_per_table: dict[str, int], freshness_hours: float):
    def _handler(request: httpx.Request) -> httpx.Response:
        table = request.url.path.rsplit("/", 1)[-1]
        count = rows_per_table.get(table, 0)

        # Count probe — Supabase sets content-range
        if request.url.params.get("select") == "id":
            return httpx.Response(
                200,
                json=[{"id": "stub"}] if count else [],
                headers={"content-range": f"0-0/{count}"},
            )

        # Freshness probe
        if request.url.params.get("select") == "created_at":
            if not count:
                return httpx.Response(200, json=[])
            return httpx.Response(200, json=[{"created_at": _iso(freshness_hours)}])

        return httpx.Response(400, text="unexpected query shape")

    return _handler


class TestUrlRedaction:
    def test_strips_credentials_and_path(self, verify_backup_module) -> None:
        redacted = verify_backup_module._redact_url(
            "postgres://user:secret@db.example.com:5432/postgres?sslmode=require"
        )
        assert "secret" not in redacted
        assert "postgres" in redacted  # scheme kept

    def test_falls_back_on_junk(self, verify_backup_module) -> None:
        # Even garbage input must not raise — canary must stay noisy but not crash.
        redacted = verify_backup_module._redact_url("not-a-url")
        assert isinstance(redacted, str)


class TestEnvRequirement:
    def test_missing_supabase_url_exits_2(
        self, verify_backup_module, monkeypatch, capsys
    ) -> None:
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "srv-key")
        with pytest.raises(SystemExit) as exc_info:
            verify_backup_module.run_checks(
                tables=("tasks",),
                staleness_hours=48,
                strict=False,
                timeout=5.0,
            )
        assert exc_info.value.code == 2
        assert "SUPABASE_URL" in capsys.readouterr().err

    def test_missing_service_role_key_exits_2(
        self, verify_backup_module, monkeypatch, capsys
    ) -> None:
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            verify_backup_module.run_checks(
                tables=("tasks",),
                staleness_hours=48,
                strict=False,
                timeout=5.0,
            )
        assert exc_info.value.code == 2
        assert "SUPABASE_SERVICE_ROLE_KEY" in capsys.readouterr().err


class TestCheckTable:
    def test_happy_path_marks_all_tables_ok(self, verify_backup_module) -> None:
        rows = {
            "tasks": 500,
            "executors": 10,
            "payment_events": 200,
        }
        transport = _mock_transport(_success_handler(rows, freshness_hours=0.5))
        with httpx.Client(
            base_url="https://stub.supabase.co",
            transport=transport,
            headers={"apikey": "x"},
        ) as client:
            rep = verify_backup_module._check_table(
                client, "tasks", staleness_hours=48, strict=False
            )
        assert rep.ok is True
        assert rep.row_count == 500
        assert rep.staleness_hours is not None
        assert rep.staleness_hours < 1.0
        assert rep.errors == []

    def test_missing_table_surfaces_404(self, verify_backup_module) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        transport = _mock_transport(handler)
        with httpx.Client(
            base_url="https://stub.supabase.co",
            transport=transport,
            headers={"apikey": "x"},
        ) as client:
            rep = verify_backup_module._check_table(
                client, "tasks", staleness_hours=48, strict=False
            )
        assert rep.ok is False
        assert any("404" in e for e in rep.errors)

    def test_empty_nonempty_table_fails(self, verify_backup_module) -> None:
        transport = _mock_transport(_success_handler({"tasks": 0}, 0.1))
        with httpx.Client(
            base_url="https://stub.supabase.co",
            transport=transport,
            headers={"apikey": "x"},
        ) as client:
            rep = verify_backup_module._check_table(
                client, "tasks", staleness_hours=48, strict=False
            )
        assert rep.ok is False
        assert any("unexpectedly empty" in e for e in rep.errors)

    def test_empty_allowed_table_is_ok(self, verify_backup_module) -> None:
        # 'applications' is NOT in NONEMPTY_TABLES → empty is fine.
        transport = _mock_transport(_success_handler({"applications": 0}, 0.1))
        with httpx.Client(
            base_url="https://stub.supabase.co",
            transport=transport,
            headers={"apikey": "x"},
        ) as client:
            rep = verify_backup_module._check_table(
                client, "applications", staleness_hours=48, strict=False
            )
        assert rep.ok is True
        assert rep.row_count == 0

    def test_stale_table_strict_fails(self, verify_backup_module) -> None:
        transport = _mock_transport(
            _success_handler({"tasks": 500}, freshness_hours=100)
        )
        with httpx.Client(
            base_url="https://stub.supabase.co",
            transport=transport,
            headers={"apikey": "x"},
        ) as client:
            rep = verify_backup_module._check_table(
                client, "tasks", staleness_hours=48, strict=True
            )
        assert rep.ok is False
        assert any("100.0h" in e or "100.1h" in e or "> 48h" in e for e in rep.errors)

    def test_stale_table_non_strict_passes_with_warning(
        self, verify_backup_module, capsys
    ) -> None:
        transport = _mock_transport(
            _success_handler({"tasks": 500}, freshness_hours=100)
        )
        with httpx.Client(
            base_url="https://stub.supabase.co",
            transport=transport,
            headers={"apikey": "x"},
        ) as client:
            rep = verify_backup_module._check_table(
                client, "tasks", staleness_hours=48, strict=False
            )
        assert rep.ok is True
        assert rep.staleness_hours is not None
        assert rep.staleness_hours > 48
        assert "WARN" in capsys.readouterr().err


class TestReportSerialization:
    def test_json_output_contains_all_tables(
        self, verify_backup_module, monkeypatch, capsys
    ) -> None:
        rows = {
            name: (1000 if name in verify_backup_module.NONEMPTY_TABLES else 0)
            for name in verify_backup_module.CRITICAL_TABLES
        }

        monkeypatch.setenv("SUPABASE_URL", "https://stub.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "stub-key")

        # Patch httpx.Client to use our mock transport.
        original_client = httpx.Client

        class _PatchedClient(original_client):
            def __init__(self, *args, **kwargs):
                kwargs["transport"] = _mock_transport(_success_handler(rows, 0.2))
                super().__init__(*args, **kwargs)

        monkeypatch.setattr(verify_backup_module.httpx, "Client", _PatchedClient)

        exit_code = verify_backup_module.main(["--json"])
        assert exit_code == 0

        out = capsys.readouterr().out
        payload = json.loads(out)
        assert payload["all_ok"] is True
        table_names = [t["name"] for t in payload["tables"]]
        assert set(table_names) == set(verify_backup_module.CRITICAL_TABLES)
