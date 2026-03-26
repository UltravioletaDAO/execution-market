---
date: 2026-03-26
tags:
  - type/plan
  - domain/infrastructure
  - domain/payments
  - domain/identity
  - domain/operations
  - priority/p0
status: active
related-files:
  - infrastructure/terraform/ecs.tf
  - mcp_server/api/reputation.py
  - mcp_server/api/routers/workers.py
  - mcp_server/api/routers/_helpers.py
  - mcp_server/integrations/erc8004/facilitator_client.py
  - mcp_server/integrations/erc8004/direct_reputation.py
  - dashboard/src/components/TaskRatings.tsx
  - dashboard/src/components/RateAgentModal.tsx
  - dashboard/src/components/TaskDetail.tsx
  - dashboard/src/components/TaskDetailModal.tsx
---

# MASTER PLAN: Stability & Observability — Post-Incident 2026-03-26

**Severity:** P0
**Created:** 2026-03-26
**Incident:** MCP server OOM crash during payment + rating errors + identity duplication
**Impact:** Customers cannot complete the full task lifecycle (publish → pay → rate). Every OOM crash causes 2+ minutes of downtime with zero alerting. External agents get duplicate ERC-8004 identities. Workers cannot rate agents after task completion.

## Summary

On 2026-03-26 at ~14:08 ET, the MCP server (ECS Fargate) crashed with an OOM kill during a task approval flow. The container had `cpu=256/memory=512` — **half of what Terraform specifies** (`cpu=512/memory=1024`), due to task definition drift (rev 298 registered outside Terraform with old values). Memory spiked from 39% to 70% when AI image verification (S3 download + Anthropic call) ran concurrently with a background task expiration job processing 14 tasks (98 HTTP calls/cycle). There are **zero CloudWatch alarms** for the MCP service — no memory, no running-task-count, no 5xx, no unhealthy-target alerts.

Additionally, the worker rating flow ("Rate Agent" from dashboard) fails with "task agent does not match rated agent identity" for tasks created by external agents (non-platform agents like #37322). The ERC-8004 identity registration path lacks idempotency — it registers new identities without checking if the wallet already owns one. Reputation feedback also has no deduplication.

This plan addresses 5 interconnected problems in 5 phases, ordered by blast radius.

---

## Phase 1: ECS Stability — Fix OOM Root Cause (P0 - CRITICAL)

> Stop the server from crashing during payment operations.

### Task 1.1: Fix Task Definition CPU/Memory Drift

- **File:** `infrastructure/terraform/ecs.tf` — ECS task definition resource
- **Bug:** Deployed rev 298 has `cpu=256, memory=512` but Terraform specifies `cpu=512, memory=1024`. Image tag is a SHA hash instead of `:latest`. Task definition registered outside Terraform caused drift.
- **Fix:** Run `terraform apply` to register corrected task definition. If Terraform state is too far drifted, manually register new task definition:
  ```bash
  # Verify current state
  aws ecs describe-task-definition --task-definition em-production-mcp-server --region us-east-2 \
    --query '{cpu:taskDefinition.cpu,memory:taskDefinition.memory,image:taskDefinition.containerDefinitions[0].image}'
  # If drifted: terraform apply, then force new deployment
  ```
- **Consider upgrading to:** `cpu=1024, memory=2048` — even 512/1024 may be tight when AI verification (image download + Anthropic API) runs concurrently with background jobs.
- **Validation:** `aws ecs describe-services ... --query 'services[0].{running:runningCount,cpu:taskDefinition}' ` shows correct values; no OOM kills in 24h.

### Task 1.2: Fix Background Task Expiration Job

- **File:** `mcp_server/api/routers/_helpers.py` (or wherever the 60-second expiration cron runs)
- **Bug:** 14 expired tasks with `missing_payment_header` are re-checked every 60 seconds, each making ~7 Supabase HTTP calls (98 calls/cycle). This is a steady memory/CPU tax that leaves minimal headroom.
- **Fix:** (a) Mark tasks as permanently non-payable after N retries (e.g., `payment_failed` status). (b) Add backoff — don't re-process tasks that have been expired for > 1 hour. (c) Batch queries — fetch all expired tasks in 1 query instead of N individual queries.
- **Validation:** After fix, expired tasks are processed once and not re-queried on subsequent cycles. Memory baseline drops below 35%.

### Task 1.3: Fix `SyncSelectRequestBuilder` Bug in Payment Endpoint

- **File:** `mcp_server/api/routers/_helpers.py` — payment query fallback
- **Bug:** `WARNING: Failed to query submission payment fallback for task 78f231a1: 'SyncSelectRequestBuilder' object is not callable'`. Double-call on Supabase client: `.select(...)()`.
- **Fix:** Remove the extra `()` call — change `.select("*")()` to `.select("*")`.
- **Validation:** No more `SyncSelectRequestBuilder` warnings in logs.

### Task 1.4: Fix `submissions.notes` Schema Mismatch

- **File:** `mcp_server/supabase_client.py` or the submission insert logic
- **Bug:** `WARNING: submissions.notes missing in current schema; retrying submission insert without it`. Every submission insert fails once and retries, doubling write overhead.
- **Fix:** Either (a) add `notes` column via migration, or (b) remove `notes` from the insert payload if the column doesn't exist.
- **Validation:** Submission inserts succeed on first try; no retry warnings.

---

## Phase 2: Observability — CloudWatch Alarms & Monitoring (P0 - CRITICAL)

> Ensure we are notified immediately when the service degrades, before customers notice.

### Task 2.1: Create SNS Notification Topic

- **File:** `infrastructure/terraform/monitoring.tf` (new file)
- **Bug:** No alarm delivery mechanism exists. Alarms fire into the void.
- **Fix:** Create SNS topic `em-production-alerts` with email subscription (platform owner) + optional Slack/Telegram webhook.
  ```hcl
  resource "aws_sns_topic" "alerts" {
    name = "em-production-alerts"
  }
  resource "aws_sns_topic_subscription" "email" {
    topic_arn = aws_sns_topic.alerts.arn
    protocol  = "email"
    endpoint  = var.alert_email
  }
  ```
- **Validation:** SNS topic visible in AWS console; email subscription confirmed.

### Task 2.2: Add CloudWatch Alarms for MCP Server

- **File:** `infrastructure/terraform/monitoring.tf`
- **Bug:** Zero alarms exist for the MCP service. Container can crash, restart, and stay down with no notification.
- **Fix:** Create 4 critical alarms:
  1. **RunningTaskCount < 1** (60s period, 1 eval) — "MCP server is DOWN"
  2. **MemoryUtilization > 80%** (60s period, 2 eval) — "OOM risk"
  3. **HTTPCode_Target_5XX_Count > 5** (60s period, 1 eval) — "Errors spike"
  4. **UnHealthyHostCount > 0** (60s period, 1 eval) — "Health check failing"
  All alarm actions → SNS topic from Task 2.1.
- **Validation:** Trigger a test alarm; verify email/notification arrives within 2 minutes.

### Task 2.3: Create CloudWatch Dashboard

- **File:** `infrastructure/terraform/monitoring.tf`
- **Bug:** Container Insights is enabled but no dashboard exists to visualize metrics.
- **Fix:** Create CloudWatch dashboard `em-production-mcp` with widgets:
  - RunningTaskCount vs DesiredTaskCount (line graph)
  - MemoryUtilization + CPUUtilization (stacked area)
  - ALB 5xx count + TargetResponseTime (bar + line)
  - UnHealthyHostCount (number widget)
- **Validation:** Dashboard accessible at CloudWatch console; shows live data.

### Task 2.4: Add Structured Health Logging

- **File:** `mcp_server/server.py` — startup / health check
- **Bug:** Logs are plain text, hard to filter by severity. No structured metrics for background job performance.
- **Fix:** Add JSON-structured log entries for:
  - Startup: `{"event":"startup","cpu":X,"memory":X,"revision":X}`
  - Health: `{"event":"health","memory_pct":X,"active_tasks":X,"bg_job_last_run":X}`
  - Payment: `{"event":"payment_release","task_id":X,"duration_ms":X,"success":bool}`
  - Background job: `{"event":"expire_tasks","count":X,"duration_ms":X}`
- **Validation:** Logs visible in CloudWatch Logs Insights with JSON filters.

---

## Phase 3: Rating & Identity Fixes (P0 - CRITICAL)

> Fix worker→agent rating flow and prevent ERC-8004 identity duplication.

### Task 3.1: Fix "task agent does not match rated agent identity" Error

- **File:** `mcp_server/api/reputation.py` — `rate_agent_endpoint()` (line ~809-915)
- **Bug:** When a worker rates an agent from the dashboard, the backend compares `task.erc8004_agent_id` (from DB) with `request.agent_id` (from frontend). If the dashboard's Supabase query returns `null` for `erc8004_agent_id` (e.g., during stale cache or partial load), the frontend falls back to `2106`, causing mismatch with the stored value (e.g., `37322`).
- **Fix:**
  1. **Add diagnostic logging** before the comparison at line 885:
     ```python
     logger.info(
         "RATING_DEBUG task=%s task_erc8004_id=%r request_agent_id=%r EM_AGENT_ID=%d",
         request.task_id, task_erc8004_id, request.agent_id, EM_AGENT_ID,
     )
     ```
  2. **Return the actual values in the error detail** so we can debug:
     ```python
     detail=f"Task agent ({task_erc8004_id}) does not match rated agent ({request.agent_id})"
     ```
  3. **Add graceful handling**: If `task_erc8004_id` is set and doesn't match, but the requested agent IS the platform agent (2106), allow it as a legacy fallback with a warning (the dashboard might be falling back).
- **Validation:** Create a test task with external agent, attempt rating from dashboard — should succeed or show clear diagnostic in logs.

### Task 3.2: Fix Dashboard `agentId` Fallback to 2106

- **File:** `dashboard/src/components/TaskDetail.tsx` (line 724), `dashboard/src/components/TaskDetailModal.tsx` (line 233)
- **Bug:** Both components hardcode `agentId={task.erc8004_agent_id ? Number(task.erc8004_agent_id) : 2106}`. If `erc8004_agent_id` is null/undefined (stale load, missing field), it silently falls back to the platform agent #2106, which is wrong for external agents.
- **Fix:**
  1. **Don't fallback to 2106** — if `erc8004_agent_id` is null, show a message like "Agent identity not available for rating" instead of silently using wrong ID.
  2. **Or fetch the agent ID from the API** as a fallback: `GET /api/v1/tasks/{id}` returns `erc8004_agent_id` from the backend (which uses a join query that's more reliable).
  3. Update `TaskRatings.tsx` (line 218) similarly: `agentId={agentId || 2106}` → don't default.
- **Validation:** Open a task created by an external agent on mobile web; "Rate Agent" modal shows correct agent ID (not 2106).

### Task 3.3: Add Identity Idempotency Check Before Registration

- **File:** `mcp_server/api/routers/workers.py` — `apply_to_task_endpoint()` (line ~212-234)
- **Bug:** When a worker applies, `register_worker_gasless()` is called without comprehensive guards. The check `if not identity.agent_id` fails when `check_worker_identity()` returns None due to cache miss or RPC error, triggering unnecessary re-registration.
- **Fix:** Port the comprehensive guard pattern from `_helpers.py:809-886` (WS-1):
  ```python
  # Guard 1: DB check (fast path)
  existing = executor.get("erc8004_agent_id")
  if existing:
      logger.info("Worker already has agent_id=%s (DB), skip registration", existing)
      return

  # Guard 2: On-chain check
  identity = await check_worker_identity(worker_wallet)
  if identity and identity.status.value == "registered" and identity.agent_id:
      logger.info("Worker already has agent_id=%s (on-chain), skip registration", identity.agent_id)
      await update_executor_identity(executor_id, identity.agent_id)
      return

  # Guard 3: Only register if truly unregistered
  reg = await register_worker_gasless(worker_wallet)
  ```
- **Validation:** Apply to a task twice with the same wallet — second apply should NOT trigger registration.

### Task 3.4: Add Reputation Feedback Deduplication

- **File:** `mcp_server/integrations/erc8004/direct_reputation.py` — `give_feedback_direct()` (line ~83-212)
- **Bug:** Zero deduplication. Every call to rate creates a new on-chain feedback record. Multiple calls from the same rater for the same task create duplicates.
- **Fix:** Before calling `giveFeedback()` on-chain, check if feedback already exists:
  ```python
  # Check feedback_documents table for existing entry
  existing = client.table("feedback_documents") \
      .select("id") \
      .eq("task_id", task_id) \
      .eq("feedback_type", "agent_rating") \
      .limit(1).execute()
  if existing.data:
      logger.warning("Feedback already exists for task=%s, skipping duplicate", task_id)
      return FeedbackResult(success=True, error="Already rated", ...)
  ```
- **Validation:** Rate the same worker/agent twice — second call returns "already rated" instead of creating duplicate.

### Task 3.5: Add Missing `/reputation/identity/{wallet}` Endpoint

- **File:** `mcp_server/api/reputation.py` — new endpoint
- **Bug:** The skill file (`skill.md` v3.19.0 STEP 1) tells agents to check `GET /reputation/identity/{wallet}` before registering, but this endpoint doesn't exist. Only `/reputation/identity/{agent_id}` (by numeric ID) exists.
- **Fix:** Add wallet-based identity lookup:
  ```python
  @router.get("/identity/wallet/{wallet_address}")
  async def lookup_identity_by_wallet(wallet_address: str):
      result = await check_worker_identity(wallet_address)
      if result and result.agent_id:
          return {"registered": True, "agent_id": result.agent_id, "wallet": wallet_address}
      raise HTTPException(status_code=404, detail="No identity found")
  ```
- **Validation:** `curl /api/v1/reputation/identity/wallet/0x52E05C...` returns agent_id if registered.

---

## Phase 4: Frontend & UX Fixes (P1 - HIGH)

> Fix stale UI state and improve real-time feedback.

### Task 4.1: Fix Stale Evidence Status After Approval

- **File:** `dashboard/src/components/TaskDetail.tsx`, `dashboard/src/components/TaskDetailModal.tsx`
- **Bug:** After task approval, evidence still shows "reviewing / in review" until a second page refresh. The first refresh doesn't update because the component fetches data on mount but doesn't refetch when navigating back.
- **Fix:**
  1. Add a `key={taskId + Date.now()}` to force remount on navigation, or
  2. Add `useEffect` dependency on a refetch trigger (e.g., `location.key`), or
  3. Best: Add Supabase realtime subscription for the task status:
     ```typescript
     useEffect(() => {
       const channel = supabase.channel(`task-${taskId}`)
         .on('postgres_changes', {
           event: 'UPDATE', schema: 'public', table: 'tasks',
           filter: `id=eq.${taskId}`
         }, (payload) => setTask(prev => ({ ...prev, ...payload.new })))
         .subscribe()
       return () => { supabase.removeChannel(channel) }
     }, [taskId])
     ```
- **Validation:** Approve a task; navigate to task detail — status should show "completed" immediately without manual refresh.

### Task 4.2: Improve Rating Modal Error Messages

- **File:** `dashboard/src/components/RateAgentModal.tsx` — `handleSubmit()` (line 59-87)
- **Bug:** Errors are displayed as raw backend messages (e.g., "task agent does not match rated agent identity") which are cryptic for workers.
- **Fix:** Map known error strings to user-friendly messages:
  ```typescript
  const ERROR_MAP: Record<string, string> = {
    'task agent does not match': t('ratings.errorAgentMismatch', 'Unable to rate this agent. Please refresh and try again.'),
    'already submitted': t('ratings.errorAlreadyRated', 'You have already rated this agent.'),
    'Task status': t('ratings.errorNotCompleted', 'This task is not yet completed.'),
  }
  ```
- **Validation:** Trigger a known error; modal shows user-friendly message instead of raw backend detail.

---

## Phase 5: Hardening & Cleanup (P1 - HIGH)

> Fix nonce conflicts, optimize background jobs, prevent future drift.

### Task 5.1: Fix Reputation Nonce Conflict

- **File:** `mcp_server/api/routers/_helpers.py` — WS-2 side effect (line ~966) and payment release flow
- **Bug:** "replacement transaction underpriced" error — the payment release TX and the reputation feedback TX compete for the same nonce when both run in parallel.
- **Fix:** Ensure reputation TX runs AFTER payment release TX completes:
  1. In the approval flow, `await` the payment release fully before triggering reputation side effects.
  2. Add a small delay or use a nonce manager that serializes TX submission.
  3. Alternatively, use the Facilitator for reputation (gasless), avoiding nonce conflicts entirely.
- **Edge case:** If release TX is slow (>10s), the reputation side effect should retry with correct nonce, not fail permanently.
- **Validation:** Approve a task; both payment release and reputation TX succeed without nonce errors.

### Task 5.2: Add Terraform Drift Detection

- **File:** `infrastructure/terraform/` or `.github/workflows/`
- **Bug:** Task definition registered outside Terraform caused cpu/memory drift that went undetected for weeks.
- **Fix:** Add a GitHub Action or scheduled job that runs `terraform plan` weekly and alerts if drift is detected:
  ```yaml
  # .github/workflows/drift-check.yml
  schedule:
    - cron: '0 9 * * 1'  # Every Monday 9am
  jobs:
    drift-check:
      steps:
        - uses: hashicorp/setup-terraform@v3
        - run: terraform plan -detailed-exitcode
        # Exit code 2 = drift detected
  ```
- **Validation:** Manually drift a resource; verify the workflow detects it on next run.

### Task 5.3: Improve Facilitator Error Handling for "Already Registered"

- **File:** `mcp_server/integrations/erc8004/facilitator_client.py` — `register_agent()` (line ~283-357)
- **Bug:** When the Facilitator returns "already registered" or "duplicate", the code treats it as a generic failure. Should be treated as idempotent success.
- **Fix:** Parse the error response and treat "already" / "duplicate" / "exists" as success:
  ```python
  error_msg = data.get("error", "")
  if any(s in error_msg.lower() for s in ("already", "duplicate", "exists")):
      logger.info("Registration idempotent: %s (treating as success)", error_msg)
      return {"success": True, "idempotent": True, "network": network, ...}
  ```
- **Validation:** Register the same wallet twice — second call returns success with `idempotent: true`.

---

## Phase 6: Financial Auditor — Transaction & Lifecycle Observability (P0 - CRITICAL)

> An automated "accountant" that audits every financial event end-to-end: wallet balances, escrow deposits, releases, refunds, fee splits, and lifecycle state transitions. If the math doesn't add up or a step is skipped, it flags it immediately.

### Task 6.1: Implement Financial Audit Event Logger

- **File:** `mcp_server/api/routers/_helpers.py` (new decorator/middleware), `mcp_server/audit/financial_auditor.py` (new module)
- **What:** Create an event-driven audit system that logs every financial state transition to the `payment_events` table (migration 027 already exists) with enriched data:
  ```
  LIFECYCLE EVENTS (each one audited):
  ┌─────────────────────────────────────────────────────────────────┐
  │ 1. TASK_CREATED       → agent wallet, balance check, bounty    │
  │ 2. PREAUTH_SIGNED     → EIP-3009 auth hash, amount, validBefore│
  │ 3. ESCROW_LOCKED      → tx_hash, escrow contract, amount       │
  │ 4. WORKER_ASSIGNED    → worker wallet, worker agent_id          │
  │ 5. EVIDENCE_SUBMITTED → submission_id, score, timestamp         │
  │ 6. TASK_APPROVED      → approval timestamp                      │
  │ 7. PAYMENT_RELEASED   → tx_hash, gross amount                   │
  │ 8. FEE_SPLIT          → worker_net (87%), treasury_fee (13%)    │
  │ 9. REPUTATION_LOGGED  → agent→worker + worker→agent tx_hashes   │
  │ 10. TASK_CANCELLED    → refund_tx_hash, amount returned          │
  │ 11. PREAUTH_EXPIRED   → no-op confirmation, zero cost           │
  └─────────────────────────────────────────────────────────────────┘
  ```
- **Fix:** For each event, log: `task_id`, `event_type`, `timestamp`, `amounts` (gross, net, fee), `tx_hashes`, `wallets` (from, to), `escrow_balance_before`, `escrow_balance_after`, `audit_status` (pass/fail/warn).
- **Validation:** Run a full task lifecycle; verify all 9 events (create→release) are logged with correct amounts.

### Task 6.2: Implement Fee Math Verification

- **File:** `mcp_server/audit/financial_auditor.py` (new)
- **What:** After every payment release, automatically verify the math:
  ```python
  async def verify_fee_split(task_id: str, release_event: dict) -> AuditResult:
      gross = release_event["amount_usd"]
      worker_received = release_event["worker_amount"]
      treasury_received = release_event["fee_amount"]
      protocol_fee = release_event.get("protocol_fee", 0)

      expected_fee = round(gross * 0.13, 6)  # 13% platform fee
      expected_worker = gross - expected_fee
      expected_treasury = expected_fee - protocol_fee

      checks = {
          "worker_correct": abs(worker_received - expected_worker) < 0.001,
          "treasury_correct": abs(treasury_received - expected_treasury) < 0.001,
          "total_balanced": abs((worker_received + treasury_received + protocol_fee) - gross) < 0.001,
      }

      if not all(checks.values()):
          logger.critical("AUDIT_FAIL task=%s checks=%s", task_id, checks)
          # Alert via SNS
          await send_audit_alert(task_id, checks, release_event)

      return AuditResult(passed=all(checks.values()), checks=checks)
  ```
- **Edge cases:** Handle USDC 6-decimal precision, $0.01 minimum fee, x402r protocol fee deduction.
- **Validation:** Create tasks with various bounties ($0.05, $0.10, $1.00); verify fee math passes for all.

### Task 6.3: Implement Escrow Balance Reconciliation

- **File:** `mcp_server/audit/financial_auditor.py`, `scripts/audit_escrow_balances.py` (new CLI tool)
- **What:** A scheduled check (cron or background task) that:
  1. Queries all active escrows from the `escrows` table
  2. For each, reads the on-chain escrow balance via RPC
  3. Compares DB state (`deposited`, `released`, `refunded`) with on-chain state
  4. Flags any discrepancy: "DB says deposited but on-chain balance is 0" or "DB says released but funds still locked"
  ```
  RECONCILIATION CHECKS:
  ├── escrow.status == "deposited" → on-chain balance >= task.bounty ✓/✗
  ├── escrow.status == "released"  → on-chain balance == 0 ✓/✗
  ├── escrow.status == "refunded"  → agent wallet balance increased ✓/✗
  └── task.status == "expired"     → pre-auth expired, no funds moved ✓/✗
  ```
- **Frequency:** Run every 15 minutes for active escrows, daily for historical reconciliation.
- **Validation:** Intentionally create a state mismatch (e.g., mark escrow as released in DB without actual release); verify reconciliation flags it.

### Task 6.4: Lifecycle State Machine Validator

- **File:** `mcp_server/audit/lifecycle_validator.py` (new)
- **What:** A deterministic state machine that validates every task transition is legal:
  ```
  VALID TRANSITIONS:
  published → accepted (worker assigned, escrow locked)
  published → cancelled (no-op if lock_on_assignment, refund if lock_on_creation)
  published → expired (pre-auth expires silently)
  accepted → in_progress (worker starts)
  in_progress → submitted (evidence uploaded)
  submitted → verifying (AI review started)
  verifying → completed (approved + payment released)
  verifying → in_progress (evidence rejected, worker retries)
  accepted → cancelled (escrow refund)
  in_progress → cancelled (escrow refund)

  ILLEGAL TRANSITIONS (flag immediately):
  published → completed (skipped escrow + verification!)
  cancelled → completed (zombie task!)
  expired → accepted (expired pre-auth!)
  ```
- **Implementation:** Hook into `db.update_task()` — before every status change, validate the transition. Log illegal transitions as `AUDIT_CRITICAL` and alert via SNS.
- **Validation:** Attempt to force an illegal transition via direct DB update; verify the validator catches it.

### Task 6.5: Audit Dashboard Endpoint

- **File:** `mcp_server/api/admin.py` — new endpoint
- **What:** `GET /admin/audit/summary` that returns:
  ```json
  {
    "period": "last_24h",
    "tasks_created": 5,
    "tasks_completed": 3,
    "tasks_cancelled": 1,
    "tasks_expired": 1,
    "total_escrowed_usd": 1.25,
    "total_released_usd": 0.75,
    "total_refunded_usd": 0.25,
    "total_fees_collected_usd": 0.0975,
    "fee_math_checks_passed": 3,
    "fee_math_checks_failed": 0,
    "escrow_reconciliation_ok": true,
    "illegal_transitions": 0,
    "open_escrows": [
      {"task_id": "abc", "amount": 0.25, "status": "deposited", "age_hours": 2}
    ],
    "alerts": []
  }
  ```
- **Auth:** Protected by `X-Admin-Key` (same as existing admin endpoints).
- **Validation:** Hit the endpoint after running a Golden Flow; verify all numbers match expected values.

---

## Summary

| Phase | Tasks | Priority | Effort | Description |
|-------|-------|----------|--------|-------------|
| Phase 1 | 4 tasks | P0 | ~2h | Fix OOM root cause, background job, secondary bugs |
| Phase 2 | 4 tasks | P0 | ~2h | CloudWatch alarms, SNS, dashboard, structured logging |
| Phase 3 | 5 tasks | P0 | ~4h | Rating error, identity duplication, dedup, missing endpoint |
| Phase 4 | 2 tasks | P1 | ~2h | Stale UI, error messages |
| Phase 5 | 3 tasks | P1 | ~2h | Nonce conflict, drift detection, facilitator handling |
| Phase 6 | 5 tasks | P0 | ~6h | Financial auditor: event logging, fee verification, escrow reconciliation, state machine |
| **TOTAL** | **23 tasks** | | **~18h** | |

## Files Modified (Complete List)

| File | Phase | Changes |
|------|-------|---------|
| `infrastructure/terraform/ecs.tf` | 1 | Fix cpu/memory, consider upgrade to 1024/2048 |
| `infrastructure/terraform/monitoring.tf` | 2 | New file: SNS topic, 4 alarms, dashboard |
| `mcp_server/api/routers/_helpers.py` | 1, 5 | Fix expiration job, SyncSelectRequestBuilder bug, nonce serialization |
| `mcp_server/api/reputation.py` | 3 | Fix rate_agent logging, add wallet identity endpoint |
| `mcp_server/api/routers/workers.py` | 3 | Add comprehensive identity guards before registration |
| `mcp_server/integrations/erc8004/facilitator_client.py` | 5 | Handle "already registered" as success |
| `mcp_server/integrations/erc8004/direct_reputation.py` | 3 | Add feedback deduplication check |
| `mcp_server/supabase_client.py` | 1 | Fix submissions.notes schema mismatch |
| `mcp_server/server.py` | 2 | Add structured health/startup logging |
| `dashboard/src/components/TaskDetail.tsx` | 3, 4 | Fix agentId fallback, add realtime subscription |
| `dashboard/src/components/TaskDetailModal.tsx` | 3, 4 | Fix agentId fallback, add realtime subscription |
| `dashboard/src/components/TaskRatings.tsx` | 3 | Remove hardcoded 2106 fallback |
| `dashboard/src/components/RateAgentModal.tsx` | 4 | Map errors to user-friendly messages |
| `.github/workflows/drift-check.yml` | 5 | New file: weekly Terraform drift detection |
| `mcp_server/audit/financial_auditor.py` | 6 | New file: fee verification, reconciliation, alerts |
| `mcp_server/audit/lifecycle_validator.py` | 6 | New file: state machine transition validator |
| `scripts/audit_escrow_balances.py` | 6 | New file: CLI tool for manual escrow reconciliation |
| `mcp_server/api/admin.py` | 6 | Add /admin/audit/summary endpoint |

## Diagnostic Commands for Future Incidents

```bash
# Quick health check
aws ecs describe-services --cluster em-production-cluster --services em-production-mcp-server \
  --region us-east-2 --query 'services[0].{running:runningCount,desired:desiredCount,taskDef:taskDefinition}'

# Check actual task definition sizing
aws ecs describe-task-definition --task-definition em-production-mcp-server --region us-east-2 \
  --query '{cpu:taskDefinition.cpu,memory:taskDefinition.memory,image:taskDefinition.containerDefinitions[0].image}'

# Memory around crash time
aws cloudwatch get-metric-statistics --namespace AWS/ECS --metric-name MemoryUtilization \
  --dimensions Name=ClusterName,Value=em-production-cluster Name=ServiceName,Value=em-production-mcp-server \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Maximum --region us-east-2

# Error logs
aws logs filter-log-events --log-group-name /ecs/em-production/mcp-server \
  --start-time $(date -d '1 hour ago' +%s000) --filter-pattern "ERROR" --region us-east-2

# Target group health
aws elbv2 describe-target-health --target-group-arn \
  arn:aws:elasticloadbalancing:us-east-2:518898403364:targetgroup/em-production-mcp-tg/89ea90aa895ff2b1 --region us-east-2
```
