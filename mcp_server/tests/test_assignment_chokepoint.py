"""Tripwire: assignment transitions must stay inside the censused allowlist.

Every transition of a ``tasks`` row from published -> accepted must either
lock escrow through the shared chokepoint (``integrations/x402/escrow_lock.py``)
or be a documented exclusion in the census report
(``docs/reports/ASSIGNMENT_CENSUS_2026-06-11.md``).

This test does NOT verify behavior — the behavioral suites do that
(test_h2a_escrow.py, test_evm_balance_gate_routes.py, test_agent_executor_tools.py,
test_escrow_validation.py). It is a source scan that fails when a NEW file
introduces an assignment-transition pattern, forcing the author to route the
new path through the chokepoint (or document the exclusion) and re-run the
census before extending the allowlist.

Patterns (kept deliberately simple and literal — no AST):

1. ``{"status": "accepted"}`` dict-literal writes (both quote styles), the
   form every in-repo task/application acceptance write uses.
2. ``db.assign_task(`` / ``db_module.assign_task(`` callsites — the
   DB-layer helper that performs the accepted transition for REST/MCP assign.

Scope: ``mcp_server/**/*.py`` excluding ``tests/`` and tooling caches.
"""

import re
from pathlib import Path

MCP_SERVER_ROOT = Path(__file__).resolve().parent.parent

EXCLUDED_DIRS = {
    "tests",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "htmlcov",
}

# Dict-literal task/application acceptance writes: {"status": "accepted"}
STATUS_ACCEPTED_RE = re.compile(r"[\"']status[\"']\s*:\s*[\"']accepted[\"']")

# DB-layer assignment helper callsites (the published->accepted transition).
DB_ASSIGN_TASK_RE = re.compile(r"\bdb(?:_module)?\.assign_task\s*\(")

# ---------------------------------------------------------------------------
# Censused allowlists — see docs/reports/ASSIGNMENT_CENSUS_2026-06-11.md for
# the per-path audit (auth surface, chokepoint compliance, exclusions).
# ---------------------------------------------------------------------------

STATUS_ACCEPTED_ALLOWLIST = {
    # H2A assign endpoint: escrow-mode branch locks via lock_with_fresh_auth()
    # with rollback; legacy branch is the documented sign-on-approval drain.
    "api/h2a.py",
    # supabase_client.assign_task(): shared DB-layer helper; its CALLERS
    # (allowlisted below) own the escrow lock + rollback.
    "supabase_client.py",
    # em_accept_agent_task: REFUSES tasks with a pending_assignment escrows
    # row (D2/EC-06); legacy no-marker self-accept + submitted->accepted
    # revert after auto-verification rejection.
    "tools/agent_executor_tools.py",
    # Mock example client (simulated MCP responses) — not server code.
    "examples/worker_complete_task.py",
}

DB_ASSIGN_TASK_ALLOWLIST = {
    # REST POST /tasks/{id}/assign: SDK-locked / Mode A fresh header /
    # Mode B lock_stored_preauth() + ESCROW GUARD rollback.
    "api/routers/tasks.py",
    # MCP em_assign_task: Mode B via lock_stored_preauth() with rollback.
    "tools/agent_tools.py",
}

GUIDANCE = (
    "Every published->accepted transition of a tasks row must lock escrow "
    "through the shared chokepoint (mcp_server/integrations/x402/escrow_lock.py: "
    "lock_with_fresh_auth / lock_stored_preauth) or be a documented exclusion. "
    "Re-run the census, update docs/reports/ASSIGNMENT_CENSUS_2026-06-11.md, "
    "and only then extend the allowlist in this test."
)


def _scan(pattern: re.Pattern) -> set:
    """Return posix-relative paths of non-test .py files matching pattern."""
    found = set()
    for path in MCP_SERVER_ROOT.rglob("*.py"):
        rel = path.relative_to(MCP_SERVER_ROOT)
        if EXCLUDED_DIRS.intersection(rel.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if pattern.search(text):
            found.add(rel.as_posix())
    return found


def _diff_message(label: str, found: set, allowlist: set) -> str:
    added = sorted(found - allowlist)
    removed = sorted(allowlist - found)
    lines = [f"{label} drifted from the censused allowlist."]
    if added:
        lines.append(f"NEW files with assignment-transition code: {added}")
    if removed:
        lines.append(f"Allowlisted files no longer match (stale allowlist?): {removed}")
    lines.append(GUIDANCE)
    return "\n".join(lines)


def test_status_accepted_writes_match_census():
    """No new file may write {"status": "accepted"} outside the census."""
    found = _scan(STATUS_ACCEPTED_RE)
    assert found == STATUS_ACCEPTED_ALLOWLIST, _diff_message(
        'Dict-literal {"status": "accepted"} writes', found, STATUS_ACCEPTED_ALLOWLIST
    )


def test_db_assign_task_callsites_match_census():
    """No new file may call db.assign_task() outside the census."""
    found = _scan(DB_ASSIGN_TASK_RE)
    assert found == DB_ASSIGN_TASK_ALLOWLIST, _diff_message(
        "db.assign_task() callsites", found, DB_ASSIGN_TASK_ALLOWLIST
    )


def test_chokepoint_module_exists():
    """The chokepoint the allowlist points to must keep existing."""
    chokepoint = MCP_SERVER_ROOT / "integrations" / "x402" / "escrow_lock.py"
    assert chokepoint.is_file(), (
        "integrations/x402/escrow_lock.py (the assignment escrow chokepoint) "
        "is missing — assignment paths have nothing to lock through. " + GUIDANCE
    )
    text = chokepoint.read_text(encoding="utf-8", errors="ignore")
    for symbol in (
        "def lock_with_fresh_auth",
        "def lock_stored_preauth",
        "def create_escrow_marker",
        "def get_escrow_marker",
    ):
        assert symbol in text, f"escrow_lock.py lost its public helper: {symbol}"
