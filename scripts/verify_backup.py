"""
Backup canary — Phase 6.3 of SaaS production hardening.

Verifies the live Supabase data layer is healthy enough that tonight's
backup will capture something useful. This is not a backup itself; it's
a fence that triggers when the input to the backup pipeline breaks.

Checks performed:
  1. SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY reachable via PostgREST.
  2. Critical tables exist and are readable.
  3. Row counts above zero for tables that should never be empty in
     production (tasks, executors, payment_events).
  4. Freshness — the most recent created_at on each critical table is
     within a configurable staleness budget (default: 48 hours).
     A 48-hour silence doesn't prove anything is broken — weekends
     exist — but it's a useful signal to investigate.

Exit codes:
  0  — all green
  1  — one or more checks failed (stderr has details)
  2  — configuration error (missing env vars)

Usage:
  python scripts/verify_backup.py [--strict] [--table T [T ...]]

  --strict          Freshness failures (rather than warnings) exit 1.
  --table / -t T    Restrict checks to table(s). Default: all critical.
  --json            Machine-readable output. Default: human-readable.
  --staleness-h N   Staleness threshold in hours. Default: 48.

Environment variables (read from the process env — never hardcoded):
  SUPABASE_URL                — PostgREST base URL
  SUPABASE_SERVICE_ROLE_KEY   — service-role JWT
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    import httpx
except ImportError:
    print(
        "ERROR: httpx is required. Install with `pip install httpx`.",
        file=sys.stderr,
    )
    sys.exit(2)


CRITICAL_TABLES: tuple[str, ...] = (
    "tasks",
    "executors",
    "submissions",
    "escrows",
    "payment_events",
    "applications",
)

# Tables that should never be empty in production. If they are, the DB is
# either blank (disaster) or the migration state has regressed.
NONEMPTY_TABLES: frozenset[str] = frozenset({"tasks", "executors", "payment_events"})

DEFAULT_STALENESS_HOURS: int = 48
DEFAULT_TIMEOUT_SECONDS: float = 15.0


@dataclass
class TableReport:
    name: str
    ok: bool
    row_count: Optional[int] = None
    latest_created_at: Optional[str] = None
    staleness_hours: Optional[float] = None
    errors: list[str] = field(default_factory=list)


@dataclass
class BackupReport:
    supabase_url: str
    checked_at: str
    all_ok: bool
    tables: list[TableReport]
    errors: list[str] = field(default_factory=list)


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"ERROR: environment variable {name} is not set", file=sys.stderr)
        sys.exit(2)
    return value


def _redact_url(url: str) -> str:
    """Drop credentials + narrow the surface we print to stream-safe levels.

    ``urlparse(...).netloc`` includes any embedded ``user:pass@`` prefix,
    so we must strip it explicitly before logging — otherwise the backup
    canary would leak DSNs to stdout.
    """
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname or ""
        netloc = host
        if parsed.port:
            netloc = f"{host}:{parsed.port}"
        if not netloc:
            return "<supabase>"
        return f"{parsed.scheme}://{netloc}"
    except Exception:
        return "<supabase>"


def _check_table(
    client: httpx.Client,
    table: str,
    *,
    staleness_hours: int,
    strict: bool,
) -> TableReport:
    report = TableReport(name=table, ok=False)

    # Count rows via the Prefer: count=exact header on a HEAD-style select.
    try:
        response = client.get(
            f"/rest/v1/{table}",
            params={"select": "id", "limit": "1"},
            headers={"Prefer": "count=exact"},
        )
    except httpx.HTTPError as exc:
        report.errors.append(f"network error on count query: {exc}")
        return report

    if response.status_code == 404:
        report.errors.append(f"table '{table}' does not exist (404)")
        return report
    if response.status_code >= 400:
        report.errors.append(
            f"count query failed ({response.status_code}): {response.text[:200]}"
        )
        return report

    content_range = response.headers.get("content-range", "")
    # Supabase returns 'content-range: 0-0/<total>' or '*/<total>' when empty.
    try:
        total_part = content_range.split("/")[-1]
        report.row_count = int(total_part) if total_part.isdigit() else 0
    except Exception:
        report.row_count = 0

    if table in NONEMPTY_TABLES and (report.row_count or 0) == 0:
        report.errors.append(
            f"table '{table}' is unexpectedly empty — possible data loss"
        )
        return report

    # Freshness probe — most recent created_at.
    try:
        freshness_resp = client.get(
            f"/rest/v1/{table}",
            params={
                "select": "created_at",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
    except httpx.HTTPError as exc:
        report.errors.append(f"network error on freshness query: {exc}")
        return report

    if freshness_resp.status_code >= 400:
        report.errors.append(f"freshness query failed ({freshness_resp.status_code})")
        return report

    rows = freshness_resp.json() or []
    if rows and rows[0].get("created_at"):
        latest_raw = rows[0]["created_at"]
        report.latest_created_at = latest_raw
        try:
            latest_dt = datetime.fromisoformat(latest_raw.replace("Z", "+00:00"))
            delta = datetime.now(timezone.utc) - latest_dt
            report.staleness_hours = delta.total_seconds() / 3600.0
            if delta > timedelta(hours=staleness_hours):
                msg = (
                    f"table '{table}' latest row is "
                    f"{report.staleness_hours:.1f}h old "
                    f"(> {staleness_hours}h)"
                )
                if strict:
                    report.errors.append(msg)
                    return report
                # Non-strict: record as a soft signal but still OK.
                print(f"WARN: {msg}", file=sys.stderr)
        except ValueError:
            report.errors.append(f"unparseable created_at: {latest_raw!r}")
            return report

    report.ok = True
    return report


def run_checks(
    *,
    tables: tuple[str, ...],
    staleness_hours: int,
    strict: bool,
    timeout: float,
) -> BackupReport:
    url = _require_env("SUPABASE_URL")
    key = _require_env("SUPABASE_SERVICE_ROLE_KEY")

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }

    report = BackupReport(
        supabase_url=_redact_url(url),
        checked_at=datetime.now(timezone.utc).isoformat(),
        all_ok=True,
        tables=[],
    )

    try:
        with httpx.Client(base_url=url, headers=headers, timeout=timeout) as client:
            for table in tables:
                table_report = _check_table(
                    client,
                    table,
                    staleness_hours=staleness_hours,
                    strict=strict,
                )
                report.tables.append(table_report)
                if not table_report.ok:
                    report.all_ok = False
    except httpx.HTTPError as exc:
        report.all_ok = False
        report.errors.append(f"supabase connection failed: {exc}")

    return report


def _format_human(report: BackupReport) -> str:
    lines = [
        f"Supabase backup canary @ {report.checked_at}",
        f"Target: {report.supabase_url}",
        "",
    ]
    for t in report.tables:
        status = "OK" if t.ok else "FAIL"
        row = f"  [{status}] {t.name:<16}"
        if t.row_count is not None:
            row += f" rows={t.row_count}"
        if t.staleness_hours is not None:
            row += f" age={t.staleness_hours:.1f}h"
        lines.append(row)
        for err in t.errors:
            lines.append(f"         - {err}")
    if report.errors:
        lines.append("")
        lines.append("Global errors:")
        for err in report.errors:
            lines.append(f"  - {err}")
    lines.append("")
    lines.append(f"Overall: {'PASS' if report.all_ok else 'FAIL'}")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "-t",
        "--table",
        action="append",
        dest="tables",
        help="Restrict to the given table (repeatable).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Freshness failures cause non-zero exit.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as JSON instead of a human-readable summary.",
    )
    parser.add_argument(
        "--staleness-h",
        type=int,
        default=DEFAULT_STALENESS_HOURS,
        help=f"Staleness threshold in hours (default: {DEFAULT_STALENESS_HOURS}).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS}).",
    )
    args = parser.parse_args(argv)

    tables = tuple(args.tables) if args.tables else CRITICAL_TABLES

    report = run_checks(
        tables=tables,
        staleness_hours=args.staleness_h,
        strict=args.strict,
        timeout=args.timeout,
    )

    if args.json:
        print(json.dumps(asdict(report), indent=2, sort_keys=True))
    else:
        print(_format_human(report))

    return 0 if report.all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
