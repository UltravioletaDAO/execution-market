#!/usr/bin/env python3
"""CI guard: fail if the migration tree's NET final state leaves any locked-down
SECURITY DEFINER money/identity RPC granted to anon/authenticated.

Security Audit 2026-06-09. Migration 097 re-granted get_or_create_executor to
anon and reopened the DB-001 cross-account takeover (FIX-P0-02). Migrations 111
and 113 close that and lock down every anon-executable SECURITY DEFINER RPC
(FIX-P1-05). This static check prevents a *future* migration from silently
re-introducing the same class of regression: it replays GRANT/REVOKE statements
in migration apply-order and fails if a protected function ends up
anon/authenticated-executable after the last migration.

Dependency-free and DB-free so it runs in any CI job. Textual parse only.

Usage:
    python scripts/assert_no_anon_rpc_regrant.py
Exit 0 = clean (net state secure); 1 = a protected RPC is left anon-executable.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Each tree is replayed independently (they are alternative schemas, not merged).
MIGRATION_DIRS = [
    REPO_ROOT / "supabase" / "migrations",
    REPO_ROOT / "mcp_server" / "supabase" / "migrations",
]

# SECURITY DEFINER money/identity/state RPCs that must NEVER end up
# anon/authenticated-executable. Matched by bare function name.
PROTECTED_FUNCS = {
    "get_or_create_executor", "resolve_dispute", "escalate_to_arbitration",
    "assign_task_to_executor", "assign_task", "complete_submission",
    "complete_task", "expire_overdue_tasks", "fund_escrow",
    "release_partial_payment", "release_final_payment", "refund_escrow",
    "recalculate_executor_reputation", "update_reputation", "award_badge",
    "award_tier_badge", "check_milestone_badges", "create_reputation_snapshot",
    "reconcile_executor_balances", "create_task_escrow", "submit_rating",
    "submit_work", "claim_task", "apply_to_task", "abandon_task",
    "submit_evidence", "release_task", "create_dispute", "respond_to_dispute",
    "submit_arbitration_vote", "link_wallet_to_session", "update_executor_profile",
}

GRANT_RE = re.compile(
    r"GRANT\s+EXECUTE\s+ON\s+FUNCTION\s+(?P<body>.+?)\s+TO\s+(?P<roles>[^;]+);",
    re.IGNORECASE | re.DOTALL,
)
REVOKE_RE = re.compile(
    r"REVOKE\s+EXECUTE\s+ON\s+FUNCTION\s+(?P<body>.+?)\s+FROM\s+(?P<roles>[^;]+);",
    re.IGNORECASE | re.DOTALL,
)
# A dynamic, pg_proc-driven revoke loop (migrations 092 / 113 / the secondary
# 20260609 revoke) revokes EXECUTE from anon/authenticated for EVERY matching
# SECURITY DEFINER function. We treat its presence in a file as revoking all
# protected functions, since it provably leaves the net state secure.
DYNAMIC_REVOKE_RE = re.compile(
    r"REVOKE\s+EXECUTE\s+ON\s+FUNCTION\s+%s\s+FROM\s+PUBLIC\s*,\s*anon\s*,\s*authenticated",
    re.IGNORECASE,
)


def is_comment_line(line: str) -> bool:
    return line.lstrip().startswith("--")


def strip_sql_comments(text: str) -> str:
    """Drop line comments so ROLLBACK example blocks (commented out) are ignored."""
    return "\n".join(l for l in text.splitlines() if not is_comment_line(l))


def func_name(body: str) -> str:
    m = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(", body)
    if m:
        return m.group(1).lower()
    return body.strip().split()[0].split(".")[-1].lower()


def roles_set(roles: str) -> set[str]:
    out = set()
    for r in roles.replace(",", " ").split():
        r = r.strip().lower()
        if r in ("anon", "authenticated", "public"):
            out.add(r)
    return out


def replay_dir(mdir: Path) -> list[str]:
    """Return list of protected funcs left anon/authenticated-executable."""
    # state[fn] = set of roles among {anon, authenticated} currently granted.
    state: dict[str, set[str]] = {}
    for sql in sorted(mdir.glob("*.sql")):
        text = strip_sql_comments(sql.read_text(encoding="utf-8", errors="replace"))

        # Process in file order: interleave grants/revokes by their position so a
        # later revoke in the same file wins over an earlier grant.
        events: list[tuple[int, str, str, set[str]]] = []
        for m in GRANT_RE.finditer(text):
            fn = func_name(m.group("body"))
            if fn in PROTECTED_FUNCS:
                events.append((m.start(), "grant", fn, roles_set(m.group("roles"))))
        for m in REVOKE_RE.finditer(text):
            fn = func_name(m.group("body"))
            if fn in PROTECTED_FUNCS:
                events.append((m.start(), "revoke", fn, roles_set(m.group("roles"))))
        events.sort(key=lambda e: e[0])
        for _, kind, fn, roles in events:
            cur = state.setdefault(fn, set())
            anon_authed = roles & {"anon", "authenticated"}
            # PUBLIC implies both anon and authenticated in Supabase.
            if "public" in roles:
                anon_authed |= {"anon", "authenticated"}
            if kind == "grant":
                cur |= anon_authed
            else:
                cur -= anon_authed

        # A dynamic, signature-agnostic revoke loop neutralises ALL protected fns.
        if DYNAMIC_REVOKE_RE.search(text):
            for fn in PROTECTED_FUNCS:
                state[fn] = set()

    return sorted(fn for fn, roles in state.items() if roles)


def main() -> int:
    bad = False
    for mdir in MIGRATION_DIRS:
        if not mdir.is_dir():
            continue
        leaked = replay_dir(mdir)
        rel = mdir.relative_to(REPO_ROOT)
        if leaked:
            bad = True
            print(f"FAIL [{rel}]: protected SECURITY DEFINER RPC(s) left anon/authenticated-executable:")
            for fn in leaked:
                print(f"  - {fn}")
        else:
            print(f"OK   [{rel}]: net final state leaves no protected RPC anon-executable.")

    if bad:
        print(
            "\nThese RPCs must stay service_role-only (Security Audit 2026-06-09, "
            "FIX-P0-02 / FIX-P1-05). If a new migration re-grants one to anon/"
            "authenticated, add a matching REVOKE (or route browser onboarding "
            "through the backend service_role API instead)."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
