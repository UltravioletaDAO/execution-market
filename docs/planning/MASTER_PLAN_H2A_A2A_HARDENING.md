# MASTER PLAN: H2A + A2A Hardening

**Created**: 2026-02-18
**Based on**: 4 audit reports + test suite design
**Total tasks**: 32 across 4 phases
**References**:
- `docs/reports/AUDIT_H2A_BACKEND_2026-02-18.md`
- `docs/reports/AUDIT_AGENT_EXECUTOR_2026-02-18.md`
- `docs/reports/AUDIT_DASHBOARD_2026-02-18.md`
- `docs/reports/AUDIT_INFRA_DB_2026-02-18.md`
- `docs/reports/TEST_SUITE_DESIGN_2026-02-18.md`

---

## Phase 1: Critical Bug Fixes (P0 — Fund Safety)

> **Goal**: Fix all fund-loss and payment-bypass bugs. No feature work.
> **Estimated**: 16 tasks. Run `pytest` after each fix.

### Task 1.1 — Fix H2A settlement atomicity
**File**: `mcp_server/api/h2a.py` lines 616-647
**Bug**: S-CRIT-01 — Settlement exception caught, task marked completed with fake `pending:` tx hash
**Fix**: If SDK settlement fails, raise HTTPException 502. Do NOT update task/submission status. Log payment_event as error.
**Validation**: Write `test_approve_settlement_failure_is_atomic` (see TEST_SUITE_DESIGN Task TG-2)

### Task 1.2 — Add task status validation in H2A approval
**File**: `mcp_server/api/h2a.py` lines 566-584
**Bug**: S-CRIT-02 — No check on `task.status` before approving. Can approve completed/cancelled tasks.
**Fix**: After line 584, add: `if task.get("status") not in ("submitted", "in_progress"): raise HTTPException(400, "Cannot approve task in status X")`
**Validation**: Write `test_approve_rejects_already_completed_task`, `test_approve_rejects_cancelled_task`

### Task 1.3 — Fix A2A approve to use PaymentDispatcher
**File**: `mcp_server/a2a/task_manager.py` lines 535-547 (TextPart) and 571-579 (DataPart)
**Bug**: P0-3 — `send_message("approve")` sets status=completed without calling PaymentDispatcher
**Fix**: Import and call payment logic from routes.py `_execute_approval_payment()` or equivalent. If payment fails, don't update status. Both TextPart and DataPart approve paths need the fix.
**Validation**: Write `test_a2a_approve_calls_payment_dispatcher`

### Task 1.4 — Fix A2A cancel to trigger escrow refund
**File**: `mcp_server/a2a/task_manager.py` lines 447-454
**Bug**: P0-4 — `cancel_task()` only updates DB status, no escrow refund
**Fix**: Import PaymentDispatcher, call `refund_payment()` for tasks with escrow. If refund fails, don't cancel. For Fase 1 (no escrow), cancel is still a no-op payment-wise.
**Validation**: Write `test_a2a_cancel_calls_refund`, `test_a2a_cancel_no_escrow_succeeds`

### Task 1.5 — Fix treasury address fallback
**File**: `mcp_server/api/h2a.py` line 56-58
**Bug**: S-HIGH-02 — Fallback is `0x036CbD53842c5426634e7929541eC2318f3dCF7e` (wrong)
**Fix**: Change fallback to `0xae07B067934975cF3DA0aa1D09cF373b0FED3661` (documented treasury) or require env var.
**Validation**: Verify `EM_TREASURY_ADDRESS` is set in ECS task definition.

### Task 1.6 — Fix feature flag to fail closed
**File**: `mcp_server/api/h2a.py` lines 215-218
**Bug**: S-HIGH-01 — `except Exception: pass` allows H2A during DB outages
**Fix**: Change `pass` to `raise HTTPException(503, "Service temporarily unavailable")`. Keep the `except HTTPException: raise` above it.
**Validation**: Write `test_feature_flag_db_error_fails_closed`

### Task 1.7 — Create test file `test_h2a_endpoints.py` (Critical section)
**File**: NEW `mcp_server/tests/test_h2a_endpoints.py`
**Content**: 5 P0 tests from TEST_SUITE_DESIGN section "P0 Critical":
- `test_approve_happy_path_settles_both_txs`
- `test_approve_settlement_failure_is_atomic`
- `test_approve_rejects_already_completed_task`
- `test_approve_rejects_cancelled_task`
- `test_approve_rejects_expired_task`
**Marker**: `@pytest.mark.h2a`

### Task 1.8 — Create test file `test_a2a_payment_bridge.py`
**File**: NEW `mcp_server/tests/test_a2a_payment_bridge.py`
**Content**: 6 P0 tests from TEST_SUITE_DESIGN:
- `test_a2a_approve_calls_payment_dispatcher`
- `test_a2a_approve_payment_failure_stays_working`
- `test_a2a_approve_triggers_webhooks`
- `test_a2a_cancel_calls_refund`
- `test_a2a_cancel_no_escrow_succeeds`
- `test_a2a_cancel_refund_failure_stays_active`
**Marker**: `@pytest.mark.a2a_bridge`

### Task 1.9 — Add new pytest markers
**File**: `mcp_server/pytest.ini`
**Fix**: Add markers: `h2a`, `agent_executor`, `a2a_bridge`, `migrations`

### Task 1.10 — Run full test suite and verify
**Command**: `cd mcp_server && python -m pytest -x -v`
**Expected**: All new + existing tests pass. Zero failures.

---

## Phase 2: H2A Endpoint Hardening + Agent Executor Tests (P1)

> **Goal**: Complete H2A test coverage (HIGH priority) + Agent Executor tool-level tests
> **Estimated**: 10 tasks

### Task 2.1 — Extend `test_h2a_endpoints.py` with feature flag + creation tests
**File**: `mcp_server/tests/test_h2a_endpoints.py`
**Content**: 4 tests:
- `test_create_task_disabled_feature_returns_403`
- `test_create_task_happy_path`
- `test_create_task_bounty_below_minimum`
- `test_create_task_bounty_above_maximum`

### Task 2.2 — Extend `test_h2a_endpoints.py` with listing + cancellation tests
**Content**: 5 tests:
- `test_list_public_only_published`
- `test_list_my_tasks_requires_auth`
- `test_view_submissions_owner_only`
- `test_cancel_completed_task_rejected`
- `test_cancel_in_progress_task_rejected`

### Task 2.3 — Extend `test_h2a_endpoints.py` with registration tests
**Content**: 4 tests:
- `test_register_agent_happy_path`
- `test_register_agent_update_existing`
- `test_register_agent_no_auth_401`
- `test_register_agent_missing_fields_400`

### Task 2.4 — Fix `register_agent_executor` to use Pydantic validation
**File**: `mcp_server/api/h2a.py` line ~939
**Bug**: S-MED-05 — Uses raw `request.json()` instead of Pydantic model
**Fix**: Use `RegisterAgentExecutorInput` or create new `RegisterAgentExecutorRequest` Pydantic model for request parsing

### Task 2.5 — Add Agent Executor tool-level tests (register + browse)
**File**: `mcp_server/tests/test_agent_executor.py` (EXTEND)
**Content**: 6 tests with mock DB:
- `test_register_new_agent_executor` (tool)
- `test_update_existing_executor_capabilities` (tool)
- `test_register_preserves_human_executors` (tool)
- `test_browse_filters_target_executor_type` (tool)
- `test_browse_client_side_capability_filter` (tool)
- `test_browse_json_format` (tool)

### Task 2.6 — Add Agent Executor tool-level tests (accept + submit + get)
**File**: `mcp_server/tests/test_agent_executor.py` (EXTEND)
**Content**: 11 tests with mock DB:
- `test_accept_published_task_success`
- `test_reject_human_only_task`
- `test_reject_insufficient_reputation`
- `test_reject_missing_capabilities`
- `test_reject_non_published_task`
- `test_auto_approve_with_fee_calculation`
- `test_auto_reject_reverts_to_accepted`
- `test_manual_verification_pending`
- `test_reject_wrong_executor`
- `test_filter_by_status` (get_my_executions)
- `test_json_format_output` (get_my_executions)

### Task 2.7 — Add MCP annotations to Agent Executor tools
**File**: `mcp_server/tools/agent_executor_tools.py`
**Bug**: P1-6 — 5 tools lack `annotations=` (readOnlyHint, destructiveHint, etc.)
**Fix**: Add annotations matching the pattern used in `server.py` existing tools

### Task 2.8 — Update root endpoint tool listing
**File**: `mcp_server/main.py` line 752
**Bug**: P1-7 — Missing 5 new tools from the list
**Fix**: Add `em_register_as_executor`, `em_browse_agent_tasks`, `em_accept_agent_task`, `em_submit_agent_work`, `em_get_my_executions`

### Task 2.9 — Deduplicate `format_bounty` / `format_datetime`
**Files**: `mcp_server/tools/agent_executor_tools.py`, `mcp_server/server.py`
**Bug**: P1-9 — Identical functions in both files
**Fix**: Move to `mcp_server/utils/formatting.py` (or similar), import from both locations

### Task 2.10 — Create `test_a2a_agent_executor_lifecycle.py`
**File**: NEW `mcp_server/tests/test_a2a_agent_executor_lifecycle.py`
**Content**: 8 integration tests:
- `test_full_lifecycle_auto_approve`
- `test_full_lifecycle_manual_approve`
- `test_rejection_retry_flow`
- `test_concurrent_accept_race_condition`
- `test_a2a_create_includes_escrow` (expected FAIL — documents gap)
- `test_a2a_create_dispatches_webhooks` (expected FAIL — documents gap)
- `test_a2a_create_sends_ws_notification` (expected FAIL — documents gap)
- `test_cannot_submit_as_wrong_executor`
**Markers**: `@pytest.mark.agent_executor`, `@pytest.mark.a2a_bridge`

---

## Phase 3: Dashboard Fixes + i18n + E2E (P1-P2)

> **Goal**: Fix broken dashboard flows, complete i18n, add E2E tests
> **Estimated**: 8 tasks

### Task 3.1 — Fix route param mismatch `:id` vs `:taskId`
**File**: `dashboard/src/App.tsx` line ~411
**Bug**: ISSUE-02 — Route uses `:id` but `ReviewSubmission.tsx` expects `:taskId`
**Fix**: Change route to `/publisher/requests/:taskId/review`

### Task 3.2 — Extend `TaskCategory` with digital categories
**File**: `dashboard/src/types/database.ts` lines 4-10
**Bug**: ISSUE-03 — Missing 6 H2A categories
**Fix**: Add `data_processing`, `research`, `content_generation`, `code_execution`, `api_integration`, `multi_step_workflow`

### Task 3.3 — Add H2A fields to `Task` type
**File**: `dashboard/src/types/database.ts` lines 106-135
**Bug**: ISSUE-04 — Missing `publisher_type`, `human_wallet`, `human_user_id`, `target_executor_type`, `required_capabilities`, `verification_mode`
**Fix**: Add optional fields to the `Task` interface

### Task 3.4 — Add Publisher Dashboard link to AppHeader
**File**: `dashboard/src/components/layout/AppHeader.tsx`
**Bug**: G-02 — No navigation link to publisher dashboard
**Fix**: Add "Mis Solicitudes" or "Panel de Publicador" link for authenticated users, pointing to `/publisher/dashboard`

### Task 3.5 — Complete pt.json FAQ translations
**File**: `dashboard/src/i18n/locales/pt.json`
**Bug**: ISSUE-08 — Missing entire `help.faq`, `help.categories` sections
**Fix**: Translate all FAQ entries to Portuguese (28+ keys: `help.faq.whatIsA2A`, `help.faq.howA2AWorks`, etc.)

### Task 3.6 — Remove wallet_address from public directory response
**File**: `mcp_server/api/h2a.py` line ~889
**Bug**: S-HIGH-04 — `wallet_address` exposed in public API without auth
**Fix**: Remove `wallet_address` from the fields returned in agent directory response

### Task 3.7 — Create E2E test file `e2e/h2a-publisher.spec.ts`
**File**: NEW `e2e/h2a-publisher.spec.ts`
**Content**: 7 E2E scenarios:
1. Publisher creates H2A task via wizard
2. Publisher dashboard shows created tasks
3. Publisher reviews agent submission (error path — placeholder sigs)
4. Agent Directory allows browsing and filtering
5. Agent selected from directory pre-fills wizard
6. Publisher cancels published task
7. FAQ page renders H2A and A2A sections

### Task 3.8 — Run full frontend checks
**Commands**: `cd dashboard && npx tsc --noEmit && npm run lint && npm run test`
**Expected**: Zero TS errors, zero lint errors, all tests pass.

---

## Phase 4: DB Integrity + Documentation + Cleanup (P2)

> **Goal**: Database migration tests, doc fixes, cleanup
> **Estimated**: 8 tasks

### Task 4.1 — Create migration for missing executor columns
**File**: NEW `supabase/migrations/034_executor_profile_extended.sql`
**Bug**: `bio`, `avatar_url`, `pricing` columns used in code but not in any migration
**Fix**: `ALTER TABLE executors ADD COLUMN IF NOT EXISTS bio TEXT, avatar_url TEXT, pricing JSONB`

### Task 4.2 — Add RLS policy for `human_wallet`
**File**: NEW `supabase/migrations/035_h2a_rls_policies.sql`
**Bug**: `human_wallet` is PII exposed via tasks SELECT
**Fix**: Create RLS policy that hides `human_wallet` for non-owners, or filter at API layer

### Task 4.3 — Create `test_migrations_031_033.py`
**File**: NEW `mcp_server/tests/test_migrations_031_033.py`
**Content**: 22 migration integrity tests from TEST_SUITE_DESIGN:
- Column existence, defaults, constraints for migrations 031, 032, 033
- Activity feed trigger tests
- RLS policy tests
- Cross-migration consistency tests
**Marker**: `@pytest.mark.migrations`

### Task 4.4 — Extend `test_h2a_endpoints.py` with Medium priority tests
**Content**: 15 tests:
- Directory: filter capability, min_rating, sort, pagination, wallet not exposed
- Auth: expired JWT, no sub claim, wallet DB fallback
- Verdicts: needs_revision, rejected
- Registration: all optional fields, A2H task 404, fee per category, payment event logging

### Task 4.5 — Fix README test count discrepancy
**File**: `README.md`
**Bug**: Says 1,258 tests but actual is ~1,027
**Fix**: Update to accurate count after all new tests are written

### Task 4.6 — Fix SKILL.md recipient wallet in payment example
**Files**: `skills/execution-market/SKILL.md`, `dashboard/public/skill.md`
**Bug**: Payment example uses dev wallet `0x857f` instead of correct address
**Fix**: Update the example + keep both files in sync

### Task 4.7 — Fix landing page stats
**File**: `landing/index.html`
**Bug**: Says "17 MAINNETS LIVE" but actual is 9 mainnets + 6 testnets = 15 total
**Fix**: Correct to accurate numbers

### Task 4.8 — Run full CI check + final validation
**Commands**:
```bash
# Backend
cd mcp_server && ruff check . && ruff format --check .
cd mcp_server && TESTING=true python -m pytest -v --tb=short
# Frontend
cd dashboard && npx tsc --noEmit && npm run lint
```
**Expected**: All green. Document final test count.

---

## Phase Summary

| Phase | Tasks | Focus | Blocking? |
|-------|-------|-------|-----------|
| **Phase 1** | 10 | P0 fund-safety bugs + critical tests | YES — before production |
| **Phase 2** | 10 | P1 H2A/Agent Executor hardening | YES — before launch |
| **Phase 3** | 8 | Dashboard fixes + i18n + E2E | Before public launch |
| **Phase 4** | 8 | DB integrity + docs + cleanup | Nice to have |
| **TOTAL** | **36** | | |

---

## How to Execute

```
User: "Empieza Phase 1"
→ Claude executes Tasks 1.1 through 1.10 sequentially
→ Reports: "Phase 1 complete. X/10 tasks done. Y tests added. Z bugs fixed."

User: "Phase 2"
→ Claude executes Tasks 2.1 through 2.10
→ Reports completion

User: "Phase 3"
→ Tasks 3.1 through 3.8

User: "Phase 4"
→ Tasks 4.1 through 4.8
→ Final validation
```

---

*Plan generated from consolidated audit findings. All task references point to specific files, line numbers, and bug IDs from the audit reports.*
