# Branch Merge Guide — Feb 13 Feature Branches

**Created:** Feb 13, 2026 (Dream Session)
**Author:** Clawd

---

## Overview

Three feature branches were built tonight, each on top of main:

| Branch | New Tests | Total Passing | Key Feature |
|--------|-----------|---------------|-------------|
| `main` | — | 843 Python + 27 React | Baseline (Fase 3 E2E evidence) |
| `feat/a2a-openclaw` | +39 | 882 | Agent executor (AI agents do tasks) |
| `feat/h2a-marketplace` | +29 | 911 | Human-to-Agent marketplace |
| `feat/erc8128-auth` | +81 | 924 | Wallet-based auth (no API keys) |

**After all merge: 992 Python + 27 React = 1,019 tests passing**

---

## Dependencies

```
main
├── feat/a2a-openclaw (2 commits on main)
│   └── feat/h2a-marketplace (built ON TOP of a2a-openclaw, +3 commits)
└── feat/erc8128-auth (2 commits on main, independent)
```

### Merge Order (recommended):
1. **feat/a2a-openclaw → main** (independent, clean)
2. **feat/h2a-marketplace → main** (depends on a2a-openclaw, merge after step 1)
3. **feat/erc8128-auth → main** (independent, can merge anytime)

### Why this order:
- `h2a-marketplace` includes the A2A commits (it was built sequentially). Merging A2A first avoids conflicts.
- `erc8128-auth` is fully independent — can go first, last, or whenever.

---

## What Each Branch Adds

### feat/a2a-openclaw
- **Migration 031:** Agent executor DB schema (executor_type, capabilities, verification_mode, etc.)
- **5 MCP Tools:** register_as_executor, browse_agent_tasks, accept_agent_task, submit_agent_work, get_my_executions
- **4 REST Endpoints:** POST/GET /api/v1/agents/, POST /api/v1/agent-tasks/{id}/accept|submit
- **Auto-verification engine:** Validates against criteria (required_fields, min_length, etc.)
- **Fee fix:** Added rates for 6 digital task categories
- **39 tests** (enums, models, capabilities, auto-verify, lifecycle)

### feat/h2a-marketplace
- **Migration 031:** H2A publisher support (publisher_type, human_wallet, agent_directory view)
- **8 REST Endpoints:** H2A task CRUD + agent directory + JWT auth
- **4 Dashboard Pages:** Agent directory, publisher dashboard, task wizard, submission review
- **TypeScript types:** Full H2A type mirror for frontend
- **API service:** `dashboard/src/services/h2a.ts`
- **29 tests** (models, JWT auth, fees, categories, integration)
- ⚠️ Note: Migration 031 on this branch differs from A2A's — may need manual merge of both ALTER TABLE statements

### feat/erc8128-auth
- **ERC-8128 verifier:** RFC 8941/9421 + EIP-191 ecrecover (684 lines)
- **Nonce store:** InMemory + DynamoDB backends with replay protection (210 lines)
- **ERC-1271:** Smart contract wallet verification with cache (191 lines)
- **Auth integration:** Unified `verify_agent_auth()` FastAPI dependency (179 lines)
- **2 API endpoints:** GET /auth/nonce, GET /auth/erc8128/info
- **Terraform:** DynamoDB nonce table + IAM policy
- **81 tests** (KeyId parsing, signatures, crypto, nonce, E2E, ERC-1271, middleware)

---

## Potential Conflicts

1. **Migration 031:** Both A2A and H2A have migration_031. When merging both, combine the ALTER TABLE statements into one migration or rename H2A's to 032.
2. **models.py:** Both A2A and H2A add enums and Pydantic models. H2A already includes A2A's changes (was built on top), so merging A2A first is cleanest.
3. **routes.py:** A2A adds agent executor endpoints, H2A adds H2A endpoints. Should be additive (different URL paths).
4. **fees.py:** Fixed on both A2A and H2A branches (same fix, no conflict).

---

## Quick Merge Commands

```bash
# Option A: Merge via GitHub PRs (recommended for history)
# Create PRs: a2a-openclaw → main, then h2a → main, then erc8128 → main

# Option B: Local merge
git checkout main
git merge feat/a2a-openclaw       # Clean, no conflicts expected
git merge feat/h2a-marketplace    # May need migration number fix
git merge feat/erc8128-auth       # Independent, clean

# Verify
python3 -m pytest mcp_server/tests/ -q --tb=short
```

---

## Test Verification (Done)

All branches tested at 1 AM Feb 13:

| Branch | Result |
|--------|--------|
| main | ✅ 843 passed, 147 skipped, 0 failed |
| feat/a2a-openclaw | ✅ 882 passed, 147 skipped, 0 failed |
| feat/h2a-marketplace | ✅ 911 passed, 147 skipped, 0 failed |
| feat/erc8128-auth | ✅ 924 passed, 147 skipped, 0 failed |
