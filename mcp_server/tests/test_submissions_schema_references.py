"""
Regression guard: the `submissions` table has `agent_verdict`, not `status`.

A previous incident (see docs/reports/INC-2026-04-21-phase-b-discrepancy.md)
used `.eq("status", "approved")` / `.in_("status", [...])` against the
`submissions` table, which produced:

    postgrest.exceptions.APIError: column submissions.status does not exist

The historic site (`jobs/phase_b_recovery.py`) was deleted in commit 26845522
when Phase B verification was migrated to SQS + Lambda, but the same pattern
still existed in three reputation-related files. This test scans every
``mcp_server/**/*.py`` file outside tests and fails if any query against the
``submissions`` table filters or updates on ``status``.

Keep this test lightweight: AST-based regex pass over source text. No DB
calls. No Supabase import required.
"""

from __future__ import annotations

import re
from pathlib import Path

# Root of the mcp_server package.
ROOT = Path(__file__).resolve().parents[1]

# File/folder excludes: tests may legitimately mock `submissions` with legacy
# column names, migrations reference historical schemas, and supabase_client
# has shared helpers we want to spot-check manually.
EXCLUDE_DIRS = {"tests", "__pycache__", "scripts"}
EXCLUDE_FILES = {"test_submissions_schema_references.py"}

# Regex: look for any `submissions` table builder chained with a filter on
# the "status" column. The chain can span lines (multiline=True).
_PATTERN = re.compile(
    r"""table\(["']submissions["']\)  # submissions table builder
        [\s\S]{0,400}?                 # up to 400 chars of chained calls
        \.(?:eq|in_|neq|match|filter)  # filter-like call
        \(\s*["']status["']            # ...on the "status" column
    """,
    re.VERBOSE,
)


def _iter_py_sources():
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if path.name in EXCLUDE_FILES:
            continue
        yield path


def test_submissions_table_never_filters_on_status_column():
    """No production .py file should reference submissions.status."""
    offenders: list[tuple[str, str]] = []
    for path in _iter_py_sources():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in _PATTERN.finditer(text):
            offenders.append((str(path.relative_to(ROOT)), match.group(0)[:200]))

    assert not offenders, (
        "Found Supabase queries that filter `submissions` on the non-existent "
        "`status` column (should be `agent_verdict`). Offenders:\n"
        + "\n".join(f"  - {rel}: {snippet!r}" for rel, snippet in offenders)
    )
