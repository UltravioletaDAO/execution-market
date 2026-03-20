---
date: 2026-03-19
tags:
  - type/plan
  - domain/payments
  - domain/security
  - domain/infrastructure
  - priority/p0
status: active
related-files:
  - mcp_server/server.py
  - mcp_server/api/routers/submissions.py
  - mcp_server/api/routers/tasks.py
  - mcp_server/api/routers/_helpers.py
  - mcp_server/supabase_client.py
  - mcp_server/integrations/x402/sdk_client.py
  - mcp_server/api/auth.py
  - mcp_server/verification/background_runner.py
  - dashboard/src/App.tsx
  - dashboard/src/i18n/locales/pt.json
  - dashboard/src/services/tasks.ts
  - .github/workflows/deploy.yml
  - infrastructure/terraform/ecs.tf
---

# MASTER PLAN: Post-Audit Remediation (March 2026)

**Severity:** P0 (Phases 1-2), P1 (Phases 3-4), P2 (Phase 5)
**Created:** 2026-03-19
**Source:** Agent Teams audit — 3 auditors (backend A-, frontend B+, infra B+)
**Impact:** 7 race condition/order-of-operations bugs (2 can cause double payments or lost funds), security gaps in CI/CD, frontend i18n blocking LATAM market

## Summary

A parallel audit by 3 agent teammates uncovered 7 bugs in payment order-of-operations (BUG-1 through BUG-7), infrastructure security gaps (static IAM credentials in CI/CD), and frontend quality issues (PT i18n at 44%, no tests on critical flows). The most urgent findings are in the MCP tool payment path: `em_approve_submission` marks submissions as accepted BEFORE paying (inverse of REST API), and the payment idempotency check queries the wrong table in fase1 mode — both can result in double payments or unpaid accepted work. This plan addresses all findings in 5 phases ordered by business impact.

---

## Phase 1: Payment Safety — Fix Critical Order-of-Operations Bugs (P0 - CRITICAL)

> Prevent double payments, unpaid accepted submissions, and unauthorized state transitions via MCP tools.

### Task 1.1: Fix approve order in MCP `em_approve_submission` — pay BEFORE marking accepted -- DONE

- **File:** `mcp_server/server.py` — `em_approve_submission()` (line ~1222-1296)
- **Bug:** BUG-4 — MCP tool marks `submission.agent_verdict = "accepted"` THEN attempts payment. If payment fails, submission stays accepted without payment. REST API (`submissions.py:183-215`) does it correctly: pay first, mark after.
- **Fix:** Restructure the function to match REST API order:
  1. Validate submission exists and is pending
  2. Attempt payment via `PaymentDispatcher`
  3. Only if payment succeeds, update `agent_verdict = "accepted"`
  4. If payment fails, leave verdict unchanged and return error
- **Edge case:** In `fase1` mode, payment failure should NOT mark the submission. In `fase2`, escrow release failure should also block the verdict update.
- **Validation:** Create `test_mcp_approve_payment_failure_no_verdict_change` — mock payment to fail, verify verdict stays `pending`

### Task 1.2: Unify payment idempotency check across `payments` + `payment_events` tables -- DONE

- **File:** `mcp_server/api/routers/_helpers.py` — `_get_existing_submission_payment()` (line ~329)
- **Bug:** BUG-2 — Idempotency check only queries `payments` table, but fase1 writes to `payment_events`. A retry after DB timeout can trigger double payment.
- **Fix:** Extend `_get_existing_submission_payment()` to also query `payment_events` for a `settle` or `disburse_worker` event with matching `task_id` and `status = "success"`. If found in either table, return existing payment and skip re-settlement.
- **Edge case:** Check both tables atomically. If `payment_events` has a success but `payments` doesn't, still treat as paid (the audit trail is authoritative).
- **Validation:** Create `test_idempotency_checks_payment_events_table` — insert a success event in `payment_events` only, verify second approve returns existing payment

### Task 1.3: Add status guard to MCP `em_cancel_task` -- DONE

- **File:** `mcp_server/server.py` — `em_cancel_task()` (line ~1428)
- **Bug:** BUG-7 — MCP tool delegates to `supabase_client.cancel_task()` without checking task status. REST API (`tasks.py:1978`) only allows cancel on `published` or `accepted` (in `direct_release` mode).
- **Fix:** Before calling `db.cancel_task()`, verify `task.status in ("published", "accepted")`. For `accepted`, only allow if `EM_ESCROW_MODE == "direct_release"`. Return error for `in_progress`, `submitted`, `verifying`, `completed`.
- **Edge case:** If task is `accepted` with escrow locked (fase2 platform_release), trigger escrow refund before cancelling.
- **Validation:** Create `test_mcp_cancel_rejects_in_progress_task` — attempt cancel on `in_progress` task, verify 409-equivalent error

### Task 1.4: Fix case-sensitivity in `em_check_submission` agent_id comparison -- DONE

- **File:** `mcp_server/server.py` — `em_check_submission()` (line ~1149)
- **Bug:** `task["agent_id"] != params.agent_id` without `.lower()` — mixed-case wallet addresses cause false "Not authorized" responses
- **Fix:** Change to `task["agent_id"].lower() != params.agent_id.lower()`
- **Edge case:** Audit all other `agent_id` comparisons in `server.py` for consistency. Known: other comparisons already use `.lower()`.
- **Validation:** Create `test_check_submission_case_insensitive_agent_id` — use mixed-case agent_id, verify access granted

---

## Phase 2: Backend Hardening — Fail-Fast and Race Condition Guards (P0)

> Eliminate silent failures and reduce race condition windows in payment and assignment flows.

### Task 2.1: Fail loudly if `EM_TREASURY_ADDRESS` is not set -- DONE

- **File:** `mcp_server/integrations/x402/sdk_client.py` (line ~81) and `mcp_server/payments/payment_dispatcher.py` (line ~75)
- **Bug:** Fallback to literal string `"YOUR_TREASURY_WALLET"` if env var missing — fee payment would go to invalid address
- **Fix:** At module import time, check `EM_TREASURY_ADDRESS`. If not set and `EM_PAYMENT_MODE != "disabled"`, raise `RuntimeError("EM_TREASURY_ADDRESS must be set")`. Same pattern as `SUPABASE_SERVICE_ROLE_KEY` check in `supabase_client.py`.
- **Edge case:** Allow missing treasury in test environments where `EM_PAYMENT_MODE=disabled` or `TESTING=true`
- **Validation:** Create `test_missing_treasury_address_raises_on_import` — unset env var, verify RuntimeError

### Task 2.2: Add verified balance check at task assignment (BUG-1 mitigation) -- DONE

- **File:** `mcp_server/supabase_client.py` — `apply_to_task()` (line ~638) or the assignment flow
- **Bug:** BUG-1 — In fase1, worker can accept and complete work without any guarantee agent has funds. Balance check at creation is advisory only.
- **Fix:** When assigning a worker to a task, call `check_agent_balance(agent_wallet, bounty_amount, network)`. If balance insufficient, reject assignment with clear error: "Agent has insufficient USDC balance to cover bounty. Assignment blocked."
- **Edge case:** Balance can change between check and approval — this is a best-effort guard, not a guarantee. Log the balance at assignment time in `payment_events` for audit trail.
- **Validation:** Create `test_assignment_rejects_insufficient_balance` — mock balance below bounty, verify assignment fails

### Task 2.3: Phase B auto-approve must verify task is still active (BUG-5) -- DONE

- **File:** `mcp_server/supabase_client.py` — `auto_approve_submission()` (line ~455-509)
- **Bug:** BUG-5 — Phase B AI verification can auto-approve a submission whose task has been cancelled. Only checks `submission.verdict`, not `task.status`.
- **Fix:** Before auto-approving, fetch task status. If `task.status in ("cancelled", "expired", "completed")`, skip auto-approve and log warning.
- **Edge case:** Task cancelled during Phase B with escrow already refunded — auto-approve would create accepted submission with no payment path.
- **Validation:** Create `test_auto_approve_skips_cancelled_task` — set task to cancelled, run auto_approve, verify submission stays pending

### Task 2.4: Thread-safe API key cache -- DONE

- **File:** `mcp_server/api/auth.py` (line ~51-52)
- **Bug:** Module-level dicts `_api_key_cache` and `_api_key_cache_timestamps` are not thread-safe under concurrent access
- **Fix:** Replace with `cachetools.TTLCache(maxsize=256, ttl=300)` protected by `threading.Lock()`. Or use `functools.lru_cache` with TTL wrapper. Single import, drop-in replacement.
- **Edge case:** Under uvicorn async (single thread), this is low risk but still technically incorrect. Fix is cheap.
- **Validation:** Create `test_api_key_cache_concurrent_access` — spawn 10 threads hitting cache simultaneously, verify no KeyError or stale reads

---

## Phase 3: Infrastructure Security & Resilience (P1)

> Close CI/CD security gaps and add production resilience.

### Task 3.1: Migrate `deploy.yml` to OIDC authentication -- NOT DONE

- **File:** `.github/workflows/deploy.yml` — `aws-actions/configure-aws-credentials` step
- **Bug:** Uses static `aws-access-key-id` + `aws-secret-access-key` (IAM user credentials). `deploy-prod.yml` and `deploy-staging.yml` already use OIDC (`role-to-assume`).
- **Fix:** Replace the credentials block with OIDC pattern from `deploy-prod.yml`:
  ```yaml
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: ${{ secrets.AWS_ROLE_ARN_PRODUCTION }}
      aws-region: us-east-2
  ```
  Remove `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` from GitHub Secrets after migration.
- **Edge case:** Verify OIDC trust policy allows the `deploy.yml` workflow (may need to update the IAM role's trust conditions).
- **Validation:** Push a test branch, verify deploy workflow authenticates via OIDC. Check CloudTrail for `AssumeRoleWithWebIdentity` event.

### Task 3.2: Add auto-scaling to MCP server ECS service -- DONE

- **File:** `infrastructure/terraform/ecs.tf` — `aws_ecs_service.mcp_server`
- **Bug:** Fixed `desired_count` with no auto-scaling target or policy. Traffic spike = degradation.
- **Fix:** Add:
  ```hcl
  resource "aws_appautoscaling_target" "mcp_server" {
    max_capacity       = 4
    min_capacity       = 1
    resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.mcp_server.name}"
    scalable_dimension = "ecs:service:DesiredCount"
    service_namespace  = "ecs"
  }
  resource "aws_appautoscaling_policy" "mcp_server_cpu" {
    name               = "mcp-server-cpu-scaling"
    policy_type        = "TargetTrackingScaling"
    resource_id        = aws_appautoscaling_target.mcp_server.resource_id
    scalable_dimension = aws_appautoscaling_target.mcp_server.scalable_dimension
    service_namespace  = aws_appautoscaling_target.mcp_server.service_namespace
    target_tracking_scaling_policy_configuration {
      target_value = 60.0
      predefined_metric_specification {
        predefined_metric_type = "ECSServiceAverageCPUUtilization"
      }
    }
  }
  ```
- **Edge case:** Keep `lifecycle { ignore_changes = [desired_count] }` so manual scaling and auto-scaling don't conflict.
- **Validation:** `terraform plan` shows 2 new resources. Deploy and verify in AWS Console under ECS > Service > Auto Scaling.

### Task 3.3: Fix dashboard Dockerfile — reproducible builds -- DONE

- **File:** `dashboard/Dockerfile`
- **Bug:** `COPY package.json ./` without `package-lock.json`, then `npm install --legacy-peer-deps` = non-reproducible builds
- **Fix:** Change to:
  ```dockerfile
  COPY package.json package-lock.json ./
  RUN npm ci
  ```
  If `--legacy-peer-deps` is needed, resolve the peer dep conflicts properly or use `npm ci --legacy-peer-deps` as last resort with a comment explaining why.
- **Edge case:** Verify `package-lock.json` is not in `.dockerignore`.
- **Validation:** Build locally twice — verify identical `node_modules` hash. Run `npm ci` in CI and confirm no errors.

### Task 3.4: Remove redundant ECS dashboard service -- DONE

- **File:** `infrastructure/terraform/ecs.tf` — `aws_ecs_service.dashboard`, `aws_ecs_task_definition.dashboard`
- **Bug:** Dashboard serves from S3+CloudFront (`dashboard-cdn.tf`) but ECS service/task definition still defined. Dead code, confusing, and costs ~$15/month if running.
- **Fix:** Remove `aws_ecs_service.dashboard`, `aws_ecs_task_definition.dashboard`, related ALB target group and listener rule. Keep ECR repo if CI/CD still pushes there.
- **Edge case:** Verify the ECS service is not actually running (`aws ecs describe-services`). If it is, drain it first.
- **Validation:** `terraform plan` shows resources being destroyed. Verify `execution.market` still loads from CloudFront after apply.

---

## Phase 4: Frontend Quality — i18n, Tests, Code Health (P1)

> Complete Portuguese translations, add critical test coverage, reduce code complexity.

### Task 4.1: Complete PT i18n — 680 missing keys -- DONE

- **File:** `dashboard/src/i18n/locales/pt.json`
- **Bug:** PT at 44% coverage (868/1548 keys). Missing: dev (112), about (64), landing (64), evidence (58), profile (47), tax (38), stake (36), verification (30), plus others.
- **Fix:** Copy structure from `en.json`, translate all missing sections. Use ES translations as reference for context since many terms are similar.
- **Edge case:** Some keys may reference brand names or technical terms that should stay in English (e.g., "USDC", "ERC-8004").
- **Validation:** Run `node -e "const en=require('./en.json'); const pt=require('./pt.json'); console.log(Object.keys(en).length, Object.keys(pt).length)"` — counts must match.

### Task 4.2: Remove hardcoded Spanish strings from App.tsx and CreateTask.tsx -- DONE

- **File:** `dashboard/src/App.tsx` (lines ~92, 103, 109, 115, 244), `dashboard/src/pages/publisher/CreateRequest.tsx`
- **Bug:** ~10 hardcoded Spanish strings bypass i18n system: "Cargando perfil...", "No se pudo cargar tu perfil.", "Reintentar", "Volver al inicio", "Mis Ganancias", placeholder text.
- **Fix:** Replace each with `t('key')` call. Add keys to all 3 locale files (en, es, pt).
- **Edge case:** The `EarningsPage` component embedded in `App.tsx` (lines 148-259) should be extracted to its own file first (Task 4.4), then fix i18n in the extracted file.
- **Validation:** `grep -rn "Cargando\|Reintentar\|Volver al inicio\|Mis Ganancias" dashboard/src/` returns 0 results

### Task 4.3: Add tests for AuthContext and critical services -- PARTIAL

- **File:** `dashboard/src/test/` (new files)
- **Bug:** `AuthContext` (most complex component), `useTasks`, `services/tasks.ts`, `SubmissionForm` — all untested. Current coverage ~15-20%.
- **Fix:** Create:
  - `test/context/AuthContext.test.tsx` — test login flow, logout debounce, executor resolution, tab visibility refresh
  - `test/services/tasks.test.ts` — test applyToTask, submitWork, error handling
  - `test/components/SubmissionForm.test.tsx` — test evidence upload, GPS capture, validation
- **Edge case:** AuthContext depends on Dynamic.xyz — mock the wallet provider. SubmissionForm depends on Supabase — mock the client.
- **Validation:** `npm run test` passes with new tests. Coverage of tested files > 70%.

### Task 4.4: Extract inline components from App.tsx -- DONE

- **File:** `dashboard/src/App.tsx` (555 lines)
- **Bug:** Contains `EarningsPage` (110 lines), `ProfilePageWrapper`, `AgentDashboardPage` inline — routing file mixed with business logic.
- **Fix:** Move each wrapper to its own file in `pages/`. `App.tsx` should only contain route definitions and layout.
- **Edge case:** Verify lazy imports still work after extraction.
- **Validation:** `App.tsx` < 200 lines. All routes still render correctly.

---

## Phase 5: Code Health & Cleanup (P2)

> Reduce technical debt and improve maintainability.

### Task 5.1: Extract MCP core tools from server.py to tools/core_tools.py -- DONE

- **File:** `mcp_server/server.py` (1882 lines) → `mcp_server/tools/core_tools.py` (new)
- **Bug:** `em_publish_task` (250 lines), `em_approve_submission` (200 lines), `em_cancel_task` (90 lines) live in the main server file.
- **Fix:** Move to `tools/core_tools.py` following the pattern of `tools/worker_tools.py` and `tools/agent_tools.py`. Register via `register_core_tools(mcp)` function. Keep `server.py` as the entry point that wires everything together.
- **Edge case:** Tests that patch `server.em_publish_task` need updating to patch `tools.core_tools.em_publish_task`.
- **Validation:** All 2384 tests pass. `server.py` < 800 lines.

### Task 5.2: Consolidate TxLink and TxHashLink components -- DONE

- **File:** `dashboard/src/components/TxLink.tsx` and `dashboard/src/components/TxHashLink.tsx`
- **Bug:** Two nearly identical components for displaying transaction hash links to block explorers.
- **Fix:** Keep `TxLink.tsx` as the canonical component, update all imports of `TxHashLink` to use `TxLink`, delete `TxHashLink.tsx`.
- **Edge case:** Check prop interfaces match — if `TxHashLink` has extra props, merge them into `TxLink`.
- **Validation:** `grep -rn "TxHashLink" dashboard/src/` returns 0 results. All tx links still render correctly.

### Task 5.3: Import admin dashboard into Terraform state -- DONE

- **File:** `infrastructure/terraform/admin-dashboard.tf`
- **Bug:** S3 bucket, CloudFront distribution, and ACM cert for `admin.execution.market` exist in AWS but are NOT in Terraform state. Resources are commented out with `<YOUR_CLOUDFRONT_DIST_ID>` placeholders.
- **Fix:** Uncomment resources, fill in real IDs, run `terraform import` for each:
  ```bash
  terraform import aws_s3_bucket.admin_dashboard em-production-admin-dashboard
  terraform import aws_cloudfront_distribution.admin_dashboard E2IUZLTDUFIAQP
  ```
- **Edge case:** `terraform plan` after import should show 0 changes. If it shows drift, fix the TF config to match reality before applying.
- **Validation:** `terraform plan` shows "No changes" for admin dashboard resources.

### Task 5.4: Clean up `as any` casts and unused react-query -- PARTIAL

- **File:** `dashboard/src/services/tasks.ts` (line 25: `const db = supabase as any`), plus 25 other `as any` instances
- **Bug:** Type-safety bypassed in 26 places. `@tanstack/react-query` installed but used in only 1 component.
- **Fix:** Remove `as any` in `tasks.ts` by properly typing the Supabase client. For other instances, fix or add proper type assertions. Decision on react-query: either commit to it (Phase 4 unification) or remove the dependency.
- **Edge case:** Some `as any` may be necessary for genuinely untyped third-party libs — add `// eslint-disable-next-line` with explanation in those cases only.
- **Validation:** `grep -c "as any" dashboard/src/**/*.ts dashboard/src/**/*.tsx` < 5 (down from 26)

---

## Summary

> **Audit date:** 2026-03-20 | **Result:** 17 DONE, 2 PARTIAL, 1 NOT DONE (92.5%)
> **Gap:** 8 audit-specific unit tests never written (Phases 1-2), OIDC migration pending (3.1)

| Phase | Tasks | Priority | Status | Notes |
|-------|-------|----------|--------|-------|
| Phase 1: Payment Safety | 4 tasks | P0 | **4/4 DONE** | All fixes in place; 4 named tests MISSING |
| Phase 2: Backend Hardening | 4 tasks | P0 | **4/4 DONE** | All fixes in place; 4 named tests MISSING |
| Phase 3: Infra Security | 4 tasks | P1 | **3/4 DONE** | 3.1 OIDC migration NOT DONE |
| Phase 4: Frontend Quality | 4 tasks | P1 | **3/4 DONE, 1 PARTIAL** | 4.3 SubmissionForm test missing |
| Phase 5: Code Health | 4 tasks | P2 | **3/4 DONE, 1 PARTIAL** | 5.4 `as any` 26->12, react-query still present |
| **TOTAL** | **20 tasks** | | **92.5%** | |

### Remaining Work

| Item | Priority | Effort |
|------|----------|--------|
| 3.1: OIDC migration for deploy-prod.yml / deploy-staging.yml | P1 | Medium (needs IAM trust policy update) |
| 4.3: Create SubmissionForm.test.tsx | P1 | Small |
| 5.4: Reduce remaining 12 `as any` casts | P2 | Small |
| Phase 1-2: Write 8 missing audit tests | P2 | Medium |

## Files Modified (Complete List)

| File | Phase | Changes |
|------|-------|---------|
| `mcp_server/server.py` | 1, 5 | Fix approve order, case-sensitivity, extract core tools |
| `mcp_server/api/routers/_helpers.py` | 1 | Unify idempotency check |
| `mcp_server/integrations/x402/sdk_client.py` | 2 | Fail-fast treasury address |
| `mcp_server/payments/payment_dispatcher.py` | 2 | Fail-fast treasury address |
| `mcp_server/supabase_client.py` | 2 | Balance check at assign, Phase B task status check |
| `mcp_server/api/auth.py` | 2 | Thread-safe cache |
| `.github/workflows/deploy.yml` | 3 | OIDC migration |
| `infrastructure/terraform/ecs.tf` | 3 | Auto-scaling, remove dashboard ECS |
| `dashboard/Dockerfile` | 3 | Reproducible builds |
| `dashboard/src/i18n/locales/pt.json` | 4 | Complete PT translations |
| `dashboard/src/App.tsx` | 4 | Remove hardcoded strings, extract components |
| `dashboard/src/pages/publisher/CreateRequest.tsx` | 4 | Remove hardcoded strings |
| `dashboard/src/test/` | 4 | New test files |
| `mcp_server/tools/core_tools.py` | 5 | New file — extracted MCP tools |
| `dashboard/src/components/TxLink.tsx` | 5 | Consolidate with TxHashLink |
| `dashboard/src/services/tasks.ts` | 5 | Remove `as any` |
| `infrastructure/terraform/admin-dashboard.tf` | 5 | Import to TF state |
