# Open Source Prep — Status Snapshot (2026-02-21)

> **Decision**: Deferred. Resume when ready to make repo public.
> **Full plan**: `docs/planning/MASTER_PLAN_OPEN_SOURCE_PREP.md` (39 tasks, 5 phases)

---

## Security Scan Results

### HIGH — Action needed before going public

| Issue | Files | Real Risk |
|-------|-------|-----------|
| Supabase anon key (full JWT) in tracked files | `dashboard/.env.production`, `scripts/task-factory.ts`, `.claude/scripts/deploy.sh` | Low in practice — anon keys are "publishable" by design (frontend JS, RLS-protected). But they're in git history. |
| `docs/internal/` (12 files tracked) | Pitches, DMs, internal questions for Ali/Marco | Not credentials, but private business correspondence |

### MEDIUM — OPSEC (not credentials)

| Issue | Files |
|-------|-------|
| AWS account ID `518898403364` + user `cuchorapido` | `CLAUDE.md`, `README.md`, task-def JSON, deploy scripts (30+ refs) |
| Supabase project ID `puyhpytmtkyevnxffksl` | Hardcoded as fallback in 6+ files |
| Secrets Manager path structure (`em/x402`, `em/supabase`) | `infrastructure/task-def-mcp.json` |
| Partial Supabase mgmt token prefix `sbp_c5dd...` | `CLAUDE.md` |

### SAFE — No action needed

| Item | Status |
|------|--------|
| QuikNode RPC URL | NOT exposed (only AWS SM reference) |
| Dev wallet private key | NOT exposed (only public address `0x857f`) |
| AWS access keys (AKIA) | NONE found |
| Hardcoded private keys | Only Hardhat test account #0 (public, well-known) |
| Dynamic.xyz env ID | Publishable by design |

## Pending Decision

`git-filter-repo` (Task 1.4) rewrites ALL git history — destructive, requires force push, invalidates forks/clones. Alternative: `git rm --cached` + `.gitignore` (faster, less disruptive, but secrets remain in history).

## When to Resume

Before flipping GitHub visibility to Public:
1. Execute Phase 1 (secret scrubbing)
2. Execute Phase 2 (SECURITY.md, CONTRIBUTING.md, .env.examples)
3. Phases 3-5 can be done incrementally after going public
