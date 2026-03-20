---
date: 2026-03-20
tags:
  - type/report
  - domain/operations
  - domain/payments
  - domain/security
  - domain/infrastructure
  - priority/p0
status: active
aliases:
  - Post-Audit Remediation
  - March 2026 Audit
related-files:
  - docs/planning/MASTER_PLAN_POST_AUDIT_2026_03.md
  - mcp_server/tools/core_tools.py
  - mcp_server/server.py
  - mcp_server/api/routers/_helpers.py
  - mcp_server/integrations/x402/sdk_client.py
  - mcp_server/api/auth.py
  - infrastructure/terraform/ecs.tf
  - dashboard/Dockerfile
  - dashboard/src/i18n/locales/pt.json
---

# Post-Audit Remediation (March 2026)

> 20-task remediation plan from 3-auditor parallel audit (backend A-, frontend B+, infra B+).
> Source plan: `docs/planning/MASTER_PLAN_POST_AUDIT_2026_03.md`

## Verification Audit — 2026-03-20

Parallel verification by 5 agent teammates confirmed **17/20 DONE, 2 PARTIAL, 1 NOT DONE** (92.5%).

### Phase 1: [[fase-1-direct-settlement|Payment Safety]] (P0) — 4/4 DONE

| Task | Description | Status | Test |
|------|-------------|--------|------|
| 1.1 | Pay before marking accepted in `em_approve_submission` | DONE | MISSING |
| 1.2 | Idempotency check queries both `payments` + `payment_events` | DONE | MISSING |
| 1.3 | Status guard in `em_cancel_task` (reject in_progress+) | DONE | MISSING |
| 1.4 | Case-insensitive `agent_id` comparison | DONE | MISSING |

**Key evidence:**
- `core_tools.py:529-633` — payment attempted first, verdict only updated on success
- `_helpers.py:347-388` — fallback to `payment_events` for settle/disburse_worker
- `core_tools.py:787-792` — rejects status not in `{published, accepted}`
- `server.py:904` — `.lower()` on both sides of comparison

### Phase 2: Backend Hardening (P0) — 4/4 DONE

| Task | Description | Status | Test |
|------|-------------|--------|------|
| 2.1 | [[treasury|Treasury]] address fail-fast RuntimeError | DONE | MISSING |
| 2.2 | Balance check at task assignment | DONE | MISSING |
| 2.3 | Auto-approve checks task status (cancelled/expired/completed) | DONE | MISSING |
| 2.4 | Thread-safe API key cache (TTLCache + Lock) | DONE | MISSING |

**Key evidence:**
- `sdk_client.py:81-89` — module-level RuntimeError if `EM_TREASURY_ADDRESS` unset
- `supabase_client.py:1098-1134` — `check_agent_balance()` blocks assignment if insufficient
- `supabase_client.py:513-541` — skips auto-approve if task cancelled/expired/completed
- `auth.py:17-66` — `cachetools.TTLCache` with `threading.Lock`

### Phase 3: [[ecs-fargate|Infrastructure]] Security (P1) — 3/4 DONE

| Task | Description | Status |
|------|-------------|--------|
| 3.1 | OIDC migration for deploy workflows | **NOT DONE** |
| 3.2 | ECS auto-scaling (CPU 60%, 1-4 tasks) | DONE |
| 3.3 | Dashboard Dockerfile `npm ci` + lock file | DONE |
| 3.4 | Remove dead ECS dashboard service | DONE |

**Gap:** Both `deploy-prod.yml` and `deploy-staging.yml` still use static `aws-access-key-id` / `aws-secret-access-key`. No `role-to-assume` pattern anywhere.

### Phase 4: Frontend Quality (P1) — 3 DONE, 1 PARTIAL

| Task | Description | Status |
|------|-------------|--------|
| 4.1 | PT i18n complete (was 44%, now 100%) | DONE |
| 4.2 | Hardcoded Spanish removed from App.tsx + CreateRequest.tsx | DONE |
| 4.3 | Tests for AuthContext + services | PARTIAL |
| 4.4 | Extract inline components from App.tsx (555->310 lines) | DONE |

**Gap:** `AuthContext.test.ts` (32 tests) and `tasks.test.ts` (39 tests) exist. `SubmissionForm.test.tsx` is missing.

### Phase 5: Code Health (P2) — 3 DONE, 1 PARTIAL

| Task | Description | Status |
|------|-------------|--------|
| 5.1 | Core MCP tools extracted to `tools/core_tools.py` | DONE |
| 5.2 | [[dashboard|TxLink/TxHashLink]] consolidated (alias remains) | DONE |
| 5.3 | Admin dashboard imported to [[terraform|Terraform]] state | DONE |
| 5.4 | `as any` cleanup + react-query decision | PARTIAL |

**Gap:** `as any` reduced from 26 to 12. `@tanstack/react-query` still in package.json (used by `RatingsHistory.tsx`).

## Remaining Work

| Item | Priority | Effort |
|------|----------|--------|
| OIDC migration (deploy-prod.yml, deploy-staging.yml) | P1 | Medium |
| SubmissionForm.test.tsx | P1 | Small |
| 12 remaining `as any` casts | P2 | Small |
| 8 missing audit-specific tests (Phases 1-2) | P2 | Medium |

## Related Notes

- [[master-plans-tracker]] — overall plan progress
- [[golden-flow]] — E2E acceptance test
- [[fee-structure]] — 13% platform fee mechanics
- [[github-actions-cicd]] — CI/CD pipeline (OIDC gap)
- [[authentication]] — API key cache security
