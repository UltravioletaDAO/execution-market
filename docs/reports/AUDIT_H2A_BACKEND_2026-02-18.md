# Audit Report: H2A Marketplace Backend

**Date**: 2026-02-18
**Auditor**: h2a-auditor (Claude Opus 4.6)
**Scope**: `mcp_server/api/h2a.py`, `mcp_server/models.py` (H2A models), `mcp_server/payments/fees.py`, `mcp_server/tests/test_h2a.py`
**Related**: Migration `033_h2a_marketplace.sql`, Migration `031_agent_executor_support.sql`, `mcp_server/tools/agent_executor_tools.py`

---

## 1. Architecture Overview

The H2A (Human-to-Agent) Marketplace is a **reversal of the existing A2H flow**. Instead of AI agents publishing tasks for humans, **humans publish tasks for AI agents to execute**.

### Data Flow

```
Human (browser, JWT auth) → POST /api/v1/h2a/tasks → Task (publisher_type=human)
                                                          ↓
Agent Executor (API key) → em_browse_agent_tasks → Accept → Submit → Human Approves → Payment
```

### Key Design Decisions

- **Separate endpoints** (`/api/v1/h2a/*`) to avoid breaking existing A2H flows
- **JWT auth for humans** (Supabase tokens) vs **API key auth for agents**
- **Sign-on-approval payment model**: no upfront escrow — human signs EIP-3009 authorizations only at approval time
- **Feature flag gated**: `feature.h2a_enabled` in `platform_config`
- **Agent Directory**: public listing of registered agent executors

---

## 2. Endpoints Inventory

| # | Method | Path | Auth | Purpose |
|---|--------|------|------|---------|
| 1 | `POST` | `/api/v1/h2a/tasks` | JWT | Human publishes task for agents |
| 2 | `GET` | `/api/v1/h2a/tasks` | Optional JWT | List H2A tasks (public or my_tasks) |
| 3 | `GET` | `/api/v1/h2a/tasks/{task_id}` | None | View H2A task details (public) |
| 4 | `GET` | `/api/v1/h2a/tasks/{task_id}/submissions` | JWT | View agent submissions (owner only) |
| 5 | `POST` | `/api/v1/h2a/tasks/{task_id}/approve` | JWT | Approve/reject/revise submission |
| 6 | `POST` | `/api/v1/h2a/tasks/{task_id}/cancel` | JWT | Cancel published/accepted task |
| 7 | `GET` | `/api/v1/agents/directory` | None | Browse registered agent executors |
| 8 | `POST` | `/api/v1/agents/register-executor` | API Key | Register agent as executor |

---

## 3. Security Findings

### CRITICAL

#### S-CRIT-01: Payment settlement continues silently on failure (h2a.py:643-647)

When the SDK settlement fails in `approve_h2a_submission`, the code **catches the exception and stores a fake "pending" tx hash** instead of failing the operation. The task is then marked as `completed` and the submission as `accepted` with `paid_at` set — but **no actual payment was made**. This means:

- The agent's work is marked as paid without actual on-chain settlement
- The "pending" tx hash (`pending:0xabc123...`) is not a real transaction and there is **no retry mechanism**
- The human never actually paid, but the task shows as completed

**Recommendation**: Fail the approval atomically. If settlement fails, do NOT update task/submission status. Return a 502 error and let the human retry.

```python
# Lines 643-647 — current code silently continues
except Exception as e:
    logger.error("H2A payment settlement failed: %s", str(e))
    # Log but don't fail — store the auth headers for retry
    worker_tx = f"pending:{request.settlement_auth_worker[:20]}..."
    fee_tx = f"pending:{request.settlement_auth_fee[:20]}..."
```

#### S-CRIT-02: No task status validation in approval endpoint (h2a.py:567-576)

The `approve_h2a_submission` endpoint does NOT check the task's current status. A human could approve a submission on a task that is already `completed`, `cancelled`, or `expired`. This could lead to double-payment.

**Recommendation**: Add status check: only tasks in `submitted` or `in_progress` status should be approvable.

### HIGH

#### S-HIGH-01: Feature flag fails open (h2a.py:217-218)

If the database query for `feature.h2a_enabled` fails (connection error, timeout, schema mismatch), the code silently passes and **allows the request through**. An attacker could potentially exploit this during a DB outage to use H2A endpoints before they're officially enabled.

```python
except Exception:
    pass  # If config check fails, allow (fail open)
```

**Recommendation**: Fail closed in production — if the feature flag can't be read, deny the request.

#### S-HIGH-02: Treasury address hardcoded as fallback (h2a.py:56-58)

The `TREASURY_ADDRESS` fallback is `0x036CbD53842c5426634e7929541eC2318f3dCF7e`, which does NOT match the project's documented treasury (`0xae07...`). If `EM_TREASURY_ADDRESS` env var is missing, fees go to an unknown/incorrect address.

```python
TREASURY_ADDRESS = os.environ.get(
    "EM_TREASURY_ADDRESS", "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
)
```

**Recommendation**: Remove hardcoded default or use the correct treasury address. Fail if env var is not set.

#### S-HIGH-03: No rate limiting on task creation (h2a.py:256-367)

There is no rate limiting on `POST /api/v1/h2a/tasks`. A malicious human with a valid JWT could spam-create thousands of tasks at no cost (since there's no upfront escrow).

**Recommendation**: Add per-user rate limiting (e.g., max 10 tasks per hour) or require a deposit/reputation threshold.

#### S-HIGH-04: wallet_address exposed in agent directory (h2a.py:889)

The agent directory endpoint is public (no auth) and exposes `wallet_address` for every agent. This leaks financial information that could be used for:
- On-chain tracking/surveillance of agents
- Targeted phishing using known wallet addresses
- Competitive intelligence on agent earnings

**Recommendation**: Remove `wallet_address` from the public directory response, or make it opt-in.

### MEDIUM

#### S-MED-01: No validation of submission ownership by executor (h2a.py:586-598)

The approval endpoint validates that the task belongs to the requesting human, but does NOT validate that the submission actually belongs to an executor assigned to that task. The only check is `eq("task_id", task_id)` on the submissions table. If the submissions table has no FK constraint enforced, a human could approve any submission ID from any task.

**Recommendation**: Also verify `submission.executor_id == task.executor_id`.

#### S-MED-02: Error messages leak internal state (h2a.py:367, 487, 541, etc.)

Multiple endpoints pass raw exception messages to the HTTP response via `detail=str(e)` or `detail=f"Task creation failed: {str(e)}"`. This can leak:
- Database schema details (column names, constraint names)
- Internal service URLs
- Stack trace fragments

**Recommendation**: Use generic error messages for 500 responses. Log the full error server-side.

#### S-MED-03: JWT wallet lookup has no validation (h2a.py:135-148)

When the JWT doesn't contain a `wallet_address` claim, the code looks up the wallet from the `executors` table using `user_id`. This lookup:
- Uses the Supabase service client (bypasses RLS)
- Does not validate the wallet format
- Silently continues with `wallet_address=None` on failure

**Recommendation**: Validate wallet address format (0x + 40 hex chars) when found.

#### S-MED-04: Dual auth token sniffing (h2a.py:181-189)

The `verify_auth_method` function identifies token type by prefix (`em_`, `sk_em_`, `ey`). The `ey` prefix is used to identify JWTs, but this is fragile — any Base64-encoded string could start with `ey`. A malformed API key starting with `ey` would be sent to JWT verification and could produce confusing error messages.

**Recommendation**: Try both auth methods with proper error handling rather than prefix sniffing.

#### S-MED-05: `register_agent_executor` uses raw `request.json()` (h2a.py:939)

The endpoint reads the request body via `request.json()` instead of using a Pydantic model. This bypasses all input validation — there's no length limit on `display_name`, `bio`, `capabilities` array size, or URL format validation on `agent_card_url`/`mcp_endpoint_url`.

Compare with the MCP tool `RegisterAgentExecutorInput` (models.py:557-564) which properly validates everything.

**Recommendation**: Use a Pydantic model (`RegisterAgentExecutorInput` or a new one) for request validation.

### LOW

#### S-LOW-01: H2A fee calculation diverges from FeeManager (h2a.py:61-68 vs fees.py)

The H2A endpoint calculates fees using a flat `get_platform_fee_percent()` which returns a single rate, ignoring the category-based fee structure in `FeeManager`. The existing A2H flow uses per-category rates (11-13%). H2A tasks always pay the default 13% regardless of category.

**Recommendation**: Use the `FeeManager.calculate_fee()` method with the task category for consistency.

#### S-LOW-02: `_check_h2a_enabled` compares to string "false" (h2a.py:210)

The feature flag check compares the stored value to the string `"false"`. But migration 033 inserts the value as `'true'::jsonb`, which is a JSON boolean, not a string. The comparison `result.data[0].get("value") == "false"` would never match if the value is the JSON boolean `false`.

**Recommendation**: Handle both string and boolean representations: `value in ("false", False)`.

#### S-LOW-03: `list_h2a_tasks` calls `verify_jwt_auth` twice (h2a.py:397, 413-416)

When `my_tasks=true`, the JWT is verified twice — once for the main query and once for the count query. This is wasteful and could cause inconsistencies if the token expires between calls.

**Recommendation**: Verify once and reuse the result.

#### S-LOW-04: No pagination bounds on agent directory total count (h2a.py:896)

`total` falls back to `len(agents)` if `result.count` is None, which would only reflect the current page count, not the actual total.

---

## 4. Missing Validations & Edge Cases

### Missing Validations

| # | Location | Missing Validation |
|---|----------|--------------------|
| V-1 | `create_h2a_task` | No check that `payment_network` is a supported network |
| V-2 | `create_h2a_task` | No check for duplicate tasks (same title + user in short window) |
| V-3 | `approve_h2a_submission` | No task status validation (can approve completed/cancelled tasks) |
| V-4 | `approve_h2a_submission` | No validation that the submission is in `pending` status |
| V-5 | `approve_h2a_submission` | No validation of `settlement_auth_*` format (EIP-3009 headers) |
| V-6 | `cancel_h2a_task` | No handling of tasks that have active submissions (should reject or notify) |
| V-7 | `register_agent_executor` | No wallet address format validation |
| V-8 | `register_agent_executor` | No limit on capabilities array size |
| V-9 | `register_agent_executor` | No URL format validation for `agent_card_url`, `mcp_endpoint_url` |
| V-10 | `get_h2a_task` | UUID format not validated (min/max length constraint but not UUID pattern) |
| V-11 | All endpoints | No CORS configuration specific to H2A (relies on global config) |

### Unimplemented Flows

| # | Flow | Status |
|---|------|--------|
| F-1 | **Agent acceptance of H2A tasks** | No `/api/v1/h2a/tasks/{id}/accept` endpoint — agents must use MCP tools (`em_accept_agent_task`) |
| F-2 | **Agent submission to H2A tasks** | No REST endpoint — agents must use MCP tools (`em_submit_agent_work`) |
| F-3 | **H2A task assignment** | No mechanism for the human to select which agent when multiple apply |
| F-4 | **Escrow for H2A** | No on-chain escrow support — only sign-on-approval (Fase 1 equivalent) |
| F-5 | **Dispute flow** | No H2A-specific dispute mechanism — `needs_revision` is informal |
| F-6 | **Deadline enforcement** | No expiry mechanism for H2A tasks — no cron/scheduler |
| F-7 | **Reputation after H2A** | No integration with ERC-8004 reputation for H2A task completions |
| F-8 | **WebSocket notifications** | No real-time push for new submissions, approvals, etc. |
| F-9 | **Retry failed settlements** | No retry queue for "pending:" tx hashes from failed settlements |

### TODO Comments Found

None in the code — but several implicit TODOs based on incomplete flows above.

---

## 5. Test Coverage Analysis

### What IS Tested (test_h2a.py: 31 tests across 5 classes)

| Class | Tests | Coverage Area |
|-------|-------|---------------|
| `TestH2AModels` (16 tests) | Model validation: valid/invalid inputs, bounty limits, rounding, all verdict types, directory models |
| `TestH2AAuth` (4 tests) | JWT: no header, empty bearer, invalid token, valid token, dual auth with API key |
| `TestH2AFees` (3 tests) | Fee math: standard $5, min $0.50, max $500 |
| `TestH2ACategories` (2 tests) | Digital categories exist, H2A tasks accept them |
| `TestH2AIntegration` (2 tests) | Create task without wallet, cancel wrong owner's task |

### What is NOT Tested (Test Gaps)

#### CRITICAL GAPS

| # | Missing Test | Priority |
|---|-------------|----------|
| TG-1 | **Approval with payment settlement** — happy path where SDK settles both worker + fee payments | CRITICAL |
| TG-2 | **Approval when settlement fails** — verify the "pending" fallback behavior (or ideally, that it fails properly) | CRITICAL |
| TG-3 | **Double approval** — approve the same submission twice | CRITICAL |
| TG-4 | **Approve on wrong task status** — approve a cancelled, expired, or already-completed task | CRITICAL |
| TG-5 | **Feature flag disabled** — verify endpoints return 403 when `feature.h2a_enabled=false` | HIGH |

#### HIGH PRIORITY GAPS

| # | Missing Test | Priority |
|---|-------------|----------|
| TG-6 | **Task creation happy path** — full mock of DB insert, verify response fields | HIGH |
| TG-7 | **Task creation with bounty below H2A minimum** ($0.50) | HIGH |
| TG-8 | **Task creation with bounty above H2A maximum** ($500) | HIGH |
| TG-9 | **List H2A tasks (public)** — verify only published tasks shown, no auth needed | HIGH |
| TG-10 | **List H2A tasks (my_tasks=true)** — verify auth required and returns only user's tasks | HIGH |
| TG-11 | **View submissions** — verify task ownership check (403 for non-owner) | HIGH |
| TG-12 | **View submissions** — verify only H2A task submissions returned | HIGH |
| TG-13 | **Cancel task in non-cancellable status** (e.g., `completed`, `in_progress`) | HIGH |
| TG-14 | **Register agent executor** — new agent registration happy path | HIGH |
| TG-15 | **Register agent executor** — update existing agent | HIGH |

#### MEDIUM PRIORITY GAPS

| # | Missing Test | Priority |
|---|-------------|----------|
| TG-16 | **Agent directory** — filter by capability | MEDIUM |
| TG-17 | **Agent directory** — filter by min_rating | MEDIUM |
| TG-18 | **Agent directory** — sort options (rating, tasks_completed, display_name) | MEDIUM |
| TG-19 | **Agent directory** — pagination | MEDIUM |
| TG-20 | **JWT with expired token** | MEDIUM |
| TG-21 | **JWT without `sub` claim** | MEDIUM |
| TG-22 | **JWT with wallet lookup fallback** (no wallet in token, found in DB) | MEDIUM |
| TG-23 | **Approval with `needs_revision` verdict** — verify task moves to `in_progress` | MEDIUM |
| TG-24 | **Approval with `rejected` verdict** — verify no payment attempted | MEDIUM |
| TG-25 | **Task creation with all optional fields** (required_capabilities, verification_mode, target_agent_id) | MEDIUM |
| TG-26 | **Get H2A task that is actually A2H** — verify 404 | MEDIUM |
| TG-27 | **Register agent executor without auth** — verify 401 | MEDIUM |
| TG-28 | **Register agent executor with missing fields** — verify 400 | MEDIUM |
| TG-29 | **Fee calculation per category** — verify category-based rates from FeeManager | MEDIUM |
| TG-30 | **Payment event logging** — verify events written for both settle and fee | MEDIUM |

#### LOW PRIORITY GAPS

| # | Missing Test | Priority |
|---|-------------|----------|
| TG-31 | **Concurrent task creation** by same user | LOW |
| TG-32 | **Bounty edge cases**: $0.01, $0.005 (below model min), negative | LOW |
| TG-33 | **XSS in task title/instructions** — verify no HTML injection in responses | LOW |
| TG-34 | **SQL injection via category filter** | LOW |
| TG-35 | **Large payload** — task with max-length instructions (10000 chars) | LOW |

---

## 6. Suggested Test Cases (Ready to Implement)

### Test Case: Approval Happy Path (CRITICAL)

```python
@pytest.mark.asyncio
async def test_approve_h2a_submission_accepted_happy_path():
    """Full approval: task owned by human, submission found, SDK settles both TXs."""
    # Mock DB: task with status=submitted, publisher_type=human, correct human_user_id
    # Mock DB: submission with executor having wallet_address
    # Mock SDK: settle_payment returns {"tx_hash": "0x..."} for both calls
    # Assert: response has worker_tx and fee_tx
    # Assert: task updated to completed
    # Assert: submission updated with payment_tx and paid_at
    # Assert: payment events logged
```

### Test Case: Settlement Failure (CRITICAL)

```python
@pytest.mark.asyncio
async def test_approve_h2a_submission_settlement_fails():
    """If SDK settlement fails, approval should NOT mark task as completed."""
    # Mock SDK: settle_payment raises Exception
    # Assert: task status NOT updated to completed (stays as submitted)
    # Assert: response is 502 or 500, NOT 200
    # Assert: payment event logged as error
```

### Test Case: Double Approval (CRITICAL)

```python
@pytest.mark.asyncio
async def test_approve_h2a_submission_already_completed():
    """Cannot approve submission on an already-completed task."""
    # Mock DB: task with status=completed
    # Assert: HTTPException 400 "Cannot approve task in status 'completed'"
```

### Test Case: Feature Flag Disabled (HIGH)

```python
@pytest.mark.asyncio
async def test_create_h2a_task_feature_disabled():
    """H2A task creation fails when feature flag is disabled."""
    # Mock DB: platform_config returns feature.h2a_enabled = "false"
    # Assert: HTTPException 403
```

### Test Case: Bounty Below H2A Minimum (HIGH)

```python
@pytest.mark.asyncio
async def test_create_h2a_task_bounty_below_minimum():
    """Task creation fails when bounty is below H2A minimum."""
    # Auth with wallet, feature enabled, bounty = $0.10 (min is $0.50)
    # Assert: HTTPException 400 with "below H2A minimum"
```

### Test Case: Agent Directory with Filters (MEDIUM)

```python
@pytest.mark.asyncio
async def test_agent_directory_capability_filter():
    """Directory filters agents by capability."""
    # Mock DB: 3 agents, only 1 has "web_scraping" capability
    # Call with capability="web_scraping"
    # Assert: only 1 agent returned
```

---

## 7. Integration Consistency Issues

### Model vs Migration Mismatches

| Field | Model (models.py) | Migration (033) | Issue |
|-------|-------------------|-----------------|-------|
| `publisher_type` | `PublisherType` enum: `agent`, `human` | `VARCHAR(10) CHECK (IN ('agent', 'human'))` | OK, matches |
| `human_wallet` | Used in h2a.py task_data | `ALTER TABLE tasks ADD COLUMN human_wallet TEXT` | OK |
| `human_user_id` | Used in h2a.py task_data | `ALTER TABLE tasks ADD COLUMN human_user_id TEXT` | OK |
| `target_executor_type` | `TargetExecutorType` enum: `human`, `agent`, `any` | Migration 031: CHECK constraint matches | OK |
| `verification_mode` | `VerificationMode` enum: `manual`, `auto`, `oracle` | Migration 031: CHECK constraint matches | OK |
| `required_capabilities` | Used in task_data dict | Migration 031: `TEXT[]` column | OK |
| `bounty_usd` model max | `le=500` in `PublishH2ATaskRequest` | `feature.h2a_max_bounty = 500.0` in config | OK, but could diverge |
| **executor columns** | `bio`, `avatar_url`, `pricing` used in directory | **No migration adds these columns** | MISMATCH |

### MISMATCH: Missing executor columns

The `AgentDirectoryEntry` model and the `register_agent_executor` endpoint reference `bio`, `avatar_url`, and `pricing` columns on the `executors` table, but **no migration adds these columns**. Migration 031 adds `agent_card_url`, `mcp_endpoint_url`, `capabilities`, `a2a_protocol_version` — but not `bio`, `avatar_url`, or `pricing`.

**Impact**: Agent registration and directory queries will fail silently (Supabase ignores unknown columns on insert) or throw errors on select if the columns don't exist.

**Recommendation**: Add migration 034 to create these columns.

### Fee Architecture Divergence

The H2A flow uses `get_platform_fee_percent()` (flat 13% from `PlatformConfig`), while:
- The A2H flow uses `PaymentDispatcher` with `FeeManager.calculate_fee()` (category-based 11-13%)
- The agent executor tools use `_calculate_fee_breakdown()` which calls `FeeManager` (category-based)

This means H2A tasks **always pay 13% regardless of category**, while A2H tasks pay a category-dependent rate. This is likely intentional (H2A is simpler), but should be documented.

---

## 8. Summary & Recommendations

### Overall Assessment

The H2A backend is a **solid first implementation** with clean separation from the existing A2H flow. The endpoint structure, JWT auth, and model design are well-thought-out. However, there are **2 critical security issues** and **significant test gaps** that must be addressed before production use.

### Priority Actions

| Priority | Action | Effort |
|----------|--------|--------|
| P0 | Fix S-CRIT-01: Make settlement failure atomic (don't mark completed on payment fail) | 1h |
| P0 | Fix S-CRIT-02: Add task status validation in approval endpoint | 30min |
| P1 | Fix S-HIGH-02: Correct treasury address fallback | 15min |
| P1 | Fix S-HIGH-03: Add rate limiting on task creation | 2h |
| P1 | Fix S-MED-05: Use Pydantic model for agent registration | 1h |
| P1 | Add CRITICAL test gaps (TG-1 through TG-5) | 3h |
| P2 | Fix S-HIGH-01: Feature flag fail-closed | 30min |
| P2 | Fix S-HIGH-04: Remove wallet from public directory | 30min |
| P2 | Add HIGH test gaps (TG-6 through TG-15) | 4h |
| P2 | Add missing migration for `bio`, `avatar_url`, `pricing` columns | 30min |
| P3 | Fix remaining MEDIUM/LOW issues | 3h |
| P3 | Add MEDIUM/LOW test gaps | 4h |

### Files Audited

| File | Lines | Findings |
|------|-------|----------|
| `mcp_server/api/h2a.py` | 1029 | 2 CRIT, 4 HIGH, 5 MED, 4 LOW |
| `mcp_server/models.py` (H2A section) | 80 | 0 (models are well-designed) |
| `mcp_server/payments/fees.py` | 811 | 0 (not directly affected, but divergence noted) |
| `mcp_server/tests/test_h2a.py` | 404 | 35 test gap items identified |
| `supabase/migrations/033_h2a_marketplace.sql` | 41 | 1 migration mismatch (missing columns) |

---

*Report generated by h2a-auditor on 2026-02-18.*
