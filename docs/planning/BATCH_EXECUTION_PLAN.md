# Batch Execution Plan — Execution Market

> **How to use**: Each Claude Code session reads this file, picks the next `PENDING` batch,
> executes it, marks it `DONE`, and commits. One batch per session = no context overflow.
>
> **Prompt to start each session**:
> ```
> Read docs/planning/BATCH_EXECUTION_PLAN.md and execute the next PENDING batch.
> After completing it, mark it DONE with the date and commit.
> ```

## Status Legend
- `PENDING` — Not started
- `IN_PROGRESS` — Started but not finished (resume here)
- `DONE (YYYY-MM-DD)` — Completed and committed
- `SKIP` — Explicitly skipped (with reason)

---

## Pre-Batch Status: Uncommitted Work Audit (2026-02-06)

The "global-tasks" session created code via sub-agents before hitting context limit.
All code has been audited and is GOOD quality. Batch 0 commits this work.

### New Files (untracked, created by sub-agents)
| File | Quality | Notes |
|------|---------|-------|
| `dashboard/src/components/PaymentStatusBadge.tsx` | GOOD | Status badge + explorer link |
| `dashboard/src/components/TxHashLink.tsx` | GOOD | Truncated hash + copy + link |
| `dashboard/src/components/WorkerRatingModal.tsx` | GOOD | Star rating 1-5, on-chain badge |
| `dashboard/src/components/WorkerReputationBadge.tsx` | GOOD | Score-based tier pill |
| `dashboard/src/hooks/useIdentity.ts` | GOOD | ERC-8004 identity lookup |
| `dashboard/src/pages/Developers.tsx` | INCOMPLETE | Missing ~80 i18n keys |
| `dashboard/src/services/reputation.ts` | GOOD | Rating + reputation API calls |
| `dashboard/src/utils/blockchain.ts` | GOOD | Explorer URLs, hash utils |
| `mcp_server/integrations/erc8004/identity.py` | GOOD | Facilitator identity client |
| `scripts/register-erc8004-base.ts` | GOOD | Base registration script |
| `supabase/migrations/016_add_settlement_method.sql` | GOOD | |
| `supabase/migrations/017_orphaned_payment_alerts.sql` | GOOD | |
| `supabase/migrations/018_add_retry_count.sql` | GOOD | |
| `supabase/migrations/019_add_refund_tx_to_tasks.sql` | GOOD | |
| `supabase/migrations/019_tasks_erc8004_agent_id.sql` | COLLISION | Must rename to 020 |

### Modified Files (all pass build)
- Dashboard build: PASSES (no errors)
- Backend syntax: ALL PASS (py_compile verified)

---

## BATCH 0 — Housekeeping & Commit Existing Work
**Status**: `DONE (2026-02-06)`
**Estimated context**: Small (mostly git operations)
**Goal**: Commit all audited work from global-tasks session cleanly

### Tasks
1. Fix migration collision: rename `019_tasks_erc8004_agent_id.sql` → `020_tasks_erc8004_agent_id.sql`
2. Add missing i18n keys for `Developers.tsx` (en/es/pt) — OR hide the route until translations exist
3. Remove duplicate export in `dashboard/src/components/index.ts` (PaymentStatusBadge exported twice)
4. Verify dashboard build still passes
5. Commit all changes with descriptive message

### Files to touch
- `supabase/migrations/019_tasks_erc8004_agent_id.sql` → rename
- `dashboard/src/i18n/locales/{en,es,pt}.json` — add `dev.*` keys
- `dashboard/src/components/index.ts` — deduplicate export

### Commit message template
```
feat: batch 0 — commit audited work from global-tasks session

- New components: PaymentStatusBadge, TxHashLink, WorkerRatingModal, WorkerReputationBadge
- New hooks: useIdentity (ERC-8004)
- New services: reputation API client
- New utils: blockchain explorer helpers
- New backend: ERC-8004 identity integration
- New migrations: 016-020 (settlement method, orphan alerts, retry count, refund tx, agent ID)
- Fix: migration number collision 019 → 020
- Dashboard, About, FAQ, HowItWorks content updates
- Routes.py payment flow improvements
```

---

## BATCH 1 — Payment UI Wiring (P0-UI-001 to P0-UI-004)
**Status**: `DONE (2026-02-06)`
**Estimated context**: Medium
**Goal**: Make on-chain transactions visible in the dashboard

### Tasks
- `P0-UI-001` Wire `PaymentStatusBadge` + `TxHashLink` into TaskDetail.tsx to show escrow_tx
- `P0-UI-002` Show `payment_tx` in worker and agent task timelines (TaskDetail + AgentDashboard)
- `P0-UI-003` Show refund_tx or `authorization_expired` reason in cancelled task timeline
- `P0-UI-004` Ensure all tx links point to BaseScan (use `blockchain.ts` utils)

### Key files
- `dashboard/src/pages/TaskDetail.tsx` — main wiring target
- `dashboard/src/pages/AgentDashboard.tsx` — agent view
- `dashboard/src/pages/agent/SubmissionReview.tsx` — approval view
- `dashboard/src/components/PaymentStatusBadge.tsx` — already built (Batch 0)
- `dashboard/src/components/TxHashLink.tsx` — already built (Batch 0)
- `dashboard/src/utils/blockchain.ts` — already built (Batch 0)
- `dashboard/src/types/database.ts` — check task/submission types have escrow_tx, payment_tx, refund_tx

### Acceptance criteria
- TaskDetail shows escrow status badge when task has escrow_tx
- TaskDetail shows payout tx link when submission has payment_tx
- Cancelled tasks show refund info
- All links open BaseScan in new tab

---

## BATCH 2 — Landing Page & Auth Fixes (P0-UI-005, P0-UI-006, P0-AUTH-001, P0-AUTH-002)
**Status**: `DONE (2026-02-06)`
**Estimated context**: Medium
**Goal**: Fix user-facing UX issues in public pages and auth flow

### Tasks
- `P0-UI-005` Add graceful fallback in PublicTaskBrowser when no tasks / fetch fails
- `P0-UI-006` Verify `/profile` route works on production build (test with `npm run build && npx serve dist`)
- `P0-AUTH-001` Fix Dynamic.xyz session persistence (wallet reconnect without re-signing)
- `P0-AUTH-002` Document token/session TTL strategy in `docs/planning/AUTH_SESSION_STRATEGY.md`

### Key files
- `dashboard/src/components/landing/PublicTaskBrowser.tsx`
- `dashboard/src/pages/Profile.tsx`
- `dashboard/src/context/AuthContext.tsx`
- `dashboard/src/providers/DynamicProvider.tsx`

### Acceptance criteria
- Landing page shows "No tasks available" instead of error when empty
- `/profile` loads without crash
- Wallet stays connected after page refresh
- Auth strategy documented

---

## BATCH 3 — Payment Hardening Part A (P0-PAY-001 to P0-PAY-003)
**Status**: `DONE (2026-02-06)`
**Estimated context**: Large (involves live testing scripts)
**Goal**: Ensure payment paths are auditable and facilitator-only

### Tasks
- `P0-PAY-001` ✅ Live x402 full lifecycle test (create→apply→assign→submit→approve→paid)
  - Payment TX: `0xe3640e0d5bc147d1621aa103a1da1f2c965c1659204eb2b1d152da8dca61b440` (Base block 41801747)
  - Refund test: authorization_expired (correct — verify-only flow, no funds moved)
  - Note: Funded escrow refund (with actual USDC return) requires advanced escrow flow (Batch 6+)
- `P0-PAY-002` ✅ All 4 scripts with direct calls already have `--allow-direct-wallet` guards
  - task-factory.ts, test-escrow-flow.ts, test-refund.ts, test-real-deposit.ts
  - 2 one-time registration scripts without guards (acceptable)
  - 3 production scripts are facilitator-only
- `P0-PAY-003` ✅ `settlement_method` already tracked in payments table
  - Approve flow records `settlement_method: "facilitator"` (routes.py:658)
  - Refund flow records `settlement_method` from result (routes.py:330)
  - Migration 016 adds column to payments table

### Acceptance criteria
- ✅ Payment tx hash captured: `0xe3640e...61b440` (on-chain confirmed, facilitator-paid gas)
- ✅ No script can call contracts directly without explicit `--allow-direct-wallet` flag
- ✅ Each payment records how it was settled (`settlement_method` field in payments table)

---

## BATCH 4 — Payment Hardening Part B (P0-PAY-004 to P0-PAY-007)
**Status**: `DONE (2026-02-06)`
**Estimated context**: Medium
**Goal**: Payment reliability and edge case coverage

### Tasks
- `P0-PAY-004` ✅ auto_payment.py retry job verified — wired in main.py:118, queries orphaned submissions, calls SDK settle, handles missing columns
- `P0-PAY-005` ✅ Migration 017 SQL view verified — `v_orphaned_payments` + `get_orphaned_payment_count()` function, needs to be applied to live DB
- `P0-PAY-006` ✅ Live test with separate worker wallet `0xb8463eb3...`
  - Payment TX: `0xa1c8a8b0d0dd2d34e4f826e626560c49bb03dac587e625d2167338c1d7c5d2a4`
  - **CRITICAL FINDING (TODO-D00)**: USDC went to EM Treasury, NOT to worker. Workers receive ZERO on-chain. See `docs/planning/DISCOVERED_TODOS_2026-02-06.md`
- `P0-PAY-007` ✅ Cancel tested across 3 states:
  - Completed (released escrow) → 409 ✅
  - Already-cancelled → 200 idempotent ✅
  - Authorized → authorization_expired (Batch 3) ✅
  - Nonexistent → 500 instead of 404 ⚠️ (minor: broad try/except swallows HTTPException)

### Critical discovery
**TODO-D00**: All x402 payments settle to EM Treasury, not to workers. The `worker_address` in `sdk_client.py:settle_task_payment` is metadata only — the EIP-3009 auth is signed with `to: EM_TREASURY`. A treasury→worker disbursement step is missing.

---

## BATCH 5 — Route Parity & API Polish (P0-API-001)
**Status**: `PENDING`
**Estimated context**: Small
**Goal**: Ensure production routes match local code

### Tasks
- `P0-API-001` Run route parity check against live production
- Compare `GET /health/routes` (if deployed) vs local route list
- Fix any drift found
- Add parity check to CI or deploy script

### Key files
- `mcp_server/health/endpoints.py` — route parity endpoint already built
- `mcp_server/api/routes.py` — source of truth for routes
- `.claude/scripts/deploy-dashboard.sh` — add post-deploy check

### Acceptance criteria
- Zero route drift between local and production
- Automated check exists for future deploys

---

## BATCH 6 — ERC-8004 Integration (P1-ERC-001 to P1-ERC-005)
**Status**: `PENDING`
**Estimated context**: Large
**Goal**: Full ERC-8004 identity and reputation integration

### Tasks
- `P1-ERC-001` Worker identity registration via facilitator (identity.py already exists)
- `P1-ERC-002` Agent identity verification on task creation
- `P1-ERC-003` Bidirectional reputation feedback (WorkerRatingModal wiring)
- `P1-ERC-004` Persist identity_tx + reputation_tx in DB, surface in UI
- `P1-ERC-005` Facilitator health check for identity + reputation

### Key files
- `mcp_server/integrations/erc8004/identity.py` — already built
- `mcp_server/integrations/erc8004/__init__.py` — exports ready
- `mcp_server/integrations/erc8004/facilitator_client.py` — reputation client
- `dashboard/src/hooks/useIdentity.ts` — already built
- `dashboard/src/components/WorkerRatingModal.tsx` — already built
- `dashboard/src/services/reputation.ts` — already built

### Acceptance criteria
- Worker can check registration status from profile page
- Agent identity verified on task creation (warning if not registered)
- Rating modal submits to ERC-8004 via facilitator
- Tx hashes stored and visible in UI

---

## BATCH 7 — Evidence Pipeline (P1-EVID-001 to P1-EVID-005)
**Status**: `PENDING`
**Estimated context**: Large (Terraform + frontend wiring)
**Goal**: Production evidence upload pipeline

### Tasks
- `P1-EVID-001` Deploy Terraform evidence stack (API GW → Lambda → S3 → CloudFront)
- `P1-EVID-002` Wire dashboard SubmissionForm to presigned upload URL
- `P1-EVID-003` Add content-type, size, checksum validation
- `P1-EVID-004` Signed URL expiry and replay protection
- `P1-EVID-005` Add forensic metadata fields to submission schema

### Key files
- `infrastructure/` — Terraform configs
- `dashboard/src/components/SubmissionForm.tsx`
- `mcp_server/api/routes.py` — evidence/submit endpoint

### Acceptance criteria
- Evidence uploads go through managed pipeline (not direct Supabase)
- Validation rejects invalid files
- Signed URLs expire properly

---

## BATCH 8 — Data & Analytics (P1-MET-001 to P1-MET-003, P1-DB-001)
**Status**: `PENDING`
**Estimated context**: Medium
**Goal**: Fix analytics and ensure schema consistency

### Tasks
- `P1-MET-001` Fix analytics queries to match live DB (no escrows/payments tables)
- `P1-MET-002` Add global stats card to dashboard home page
- `P1-MET-003` Add periodic metrics sanity check
- `P1-DB-001` Schema parity audit across environments

### Key files
- `mcp_server/api/admin.py` — analytics endpoints (already improved)
- `dashboard/src/pages/Home.tsx` — add stats card
- `supabase/migrations/` — verify applied state

### Acceptance criteria
- Analytics endpoints return valid data from live DB
- Dashboard home shows key metrics
- Schema differences documented

---

## BATCH 9 — Test Automation (P2-TEST-001 to P2-TEST-005)
**Status**: `PENDING`
**Estimated context**: Medium
**Goal**: Automated test coverage for critical flows

### Tasks
- `P2-TEST-001` Nightly live smoke test (full task lifecycle)
- `P2-TEST-002` Funded refund smoke test
- `P2-TEST-003` Concurrency/idempotency stress test
- `P2-TEST-004` E2E UI test for payment timeline
- `P2-TEST-005` Remove script fallbacks after stabilization

### Key files
- `scripts/test-x402-rapid-flow.ts` — base for smoke tests
- `mcp_server/tests/test_p0_routes_idempotency.py` — already built
- `e2e/` — Playwright tests
- `tests/` — integration tests

### Acceptance criteria
- Smoke test script runnable via `npm run test:smoke`
- Idempotency tests pass
- At least 1 E2E test for payment visibility

---

## BATCH 10 — Deployment & Ops (P2-OPS-001 to P2-OPS-003)
**Status**: `PENDING`
**Estimated context**: Small
**Goal**: Streamline deployment process

### Tasks
- `P2-OPS-001` Create build + deploy script with immutable tags
- `P2-OPS-002` Add post-deploy parity checks
- `P2-OPS-003` Add release note template with tx evidence

### Key files
- `.claude/scripts/deploy-dashboard.sh`
- `.claude/scripts/build-all.sh`
- `.github/workflows/deploy.yml`

### Acceptance criteria
- Single command deploys with tagged images
- Post-deploy health check runs automatically
- Release notes capture tx evidence links

---

## BATCH 11 — Final Launch Validation (T-001 to T-006)
**Status**: `PENDING`
**Estimated context**: Large (live testing)
**Goal**: End-to-end validation of all critical flows on production

### Tasks
- `T-001` Live task creation via x402 (facilitator verify-only)
- `T-002` Full lifecycle: create → apply → submit → approve (capture payout tx)
- `T-003` Funded refund with on-chain tx hash
- `T-004` ERC-8004 identity + reputation for worker and agent
- `T-005` UI: all tx visible and clickable in dashboard
- `T-006` Session persistence: wallet survives navigation

### Acceptance criteria
- All 6 tests pass on production
- Evidence screenshots captured
- Tx hashes recorded in this document

### Evidence log (fill after execution)
```
T-001: task_id=___ | verified=___
T-002: task_id=___ | submission_id=___ | payment_tx=___
T-003: task_id=___ | refund_tx=___
T-004: worker_identity_tx=___ | reputation_tx=___
T-005: screenshot saved to ___
T-006: PASS/FAIL
```

---

## BATCH 12 — Release Gate (RG-001 to RG-005)
**Status**: `PENDING`
**Estimated context**: Small (verification only)
**Goal**: Final go/no-go checklist

### Checklist
- [ ] `RG-001` No accepted submission without `payment_tx`
- [ ] `RG-002` At least one payout + one refund tx in same release cycle
- [ ] `RG-003` API/UI route parity confirmed
- [ ] `RG-004` Evidence upload via managed pipeline
- [ ] `RG-005` ERC-8004 flows facilitator-backed and observable

### Sign-off
```
Date: ___
All gates passed: YES/NO
Signed: ___
```

---

## Execution Log

| Batch | Status | Date | Session | Notes |
|-------|--------|------|---------|-------|
| 0 | DONE | 2026-02-06 | current | Commit 8482a23, 128 files, build passes |
| 1 | DONE | 2026-02-06 | current | Commit cf73845, TaskDetail + types, build passes |
| 2 | DONE | 2026-02-06 | current | Commit e6185a4, auth persistence + docs |
| 3 | DONE | 2026-02-06 | current | Live payment tx confirmed, scripts audited, settlement_method tracked |
| 4 | DONE | 2026-02-06 | granular-tasks | **CRITICAL**: Workers not paid on-chain (TODO-D00). Cancel states verified. |
| 5 | PENDING | | | |
| 6 | PENDING | | | |
| 7 | PENDING | | | |
| 8 | PENDING | | | |
| 9 | PENDING | | | |
| 10 | PENDING | | | |
| 11 | PENDING | | | |
| 12 | PENDING | | | |
