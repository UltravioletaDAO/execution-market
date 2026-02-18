# Test Suite Design: A2A, H2A & Agent Executor

**Date**: 2026-02-18
**Based on**: 4 audit reports (H2A backend, Agent Executor, Dashboard, Infra/DB)
**Current state**: 950 tests (36 files). New code has 77 tests (test_h2a: 31, test_agent_executor: 46)
**Target**: +95 new tests across 5 new test files + extension of 2 existing files

---

## Overview

The recent pull introduced 3 major features with significant test gaps:

| Feature | New code (LOC) | Existing tests | Gap tests | Priority |
|---------|---------------|----------------|-----------|----------|
| H2A Marketplace | 1,028 (h2a.py) + 156 (models) | 31 | 35 | P0 |
| Agent Executor Tools | 446 (tools) | 46 | 17 | P0 |
| A2A Payment Bridge | 0 (gap in task_manager.py) | 0 | 6 | P0 |
| Dashboard (E2E) | 1,076 (6 pages) | 0 | 7 | P1 |
| DB Migrations | 124 (3 SQL files) | 2 | 22 | P2 |
| Cross-cutting | - | 0 | 8 | P1 |

---

## New Pytest Markers

Add to `mcp_server/pytest.ini`:

```ini
h2a: H2A Human-to-Agent marketplace
agent_executor: Agent executor MCP tools
a2a_bridge: A2A protocol payment/refund bridge
migrations: Database migration integrity
```

---

## FILE 1: `test_h2a_endpoints.py` — H2A API Endpoint Tests

**Marker**: `@pytest.mark.h2a`
**Priority**: P0 (5 CRIT) + P1 (10 HIGH) + P2 (15 MED)
**Estimated**: 30 tests

### P0 Critical (fix before production)

```python
class TestH2AApprovalCritical:
    """P0: Payment settlement atomicity and status validation."""

    @pytest.mark.h2a
    async def test_approve_happy_path_settles_both_txs(self):
        """
        CRIT TG-1: Full approval with SDK settlement.
        - Mock: task status=submitted, publisher_type=human, correct human_user_id
        - Mock: submission with executor.wallet_address
        - Mock: SDK settle_payment returns {"tx_hash": "0x..."} for both calls
        - Assert: response has real worker_tx and fee_tx
        - Assert: task updated to completed
        - Assert: submission updated with payment_tx and paid_at
        - Assert: 2 payment_events logged (settle + fee)
        """

    @pytest.mark.h2a
    async def test_approve_settlement_failure_is_atomic(self):
        """
        CRIT TG-2 / S-CRIT-01: Settlement failure must NOT mark task completed.
        - Mock: SDK settle_payment raises Exception
        - Assert: task status STAYS as submitted (NOT completed)
        - Assert: response is 502, NOT 200
        - Assert: payment_event logged as error
        - Assert: submission NOT updated with paid_at
        """

    @pytest.mark.h2a
    async def test_approve_rejects_already_completed_task(self):
        """
        CRIT TG-3 / S-CRIT-02: Cannot approve submission on completed task.
        - Mock: task status=completed
        - Assert: HTTPException 400 "Cannot approve task in status 'completed'"
        """

    @pytest.mark.h2a
    async def test_approve_rejects_cancelled_task(self):
        """
        CRIT TG-4: Cannot approve submission on cancelled task.
        - Mock: task status=cancelled
        - Assert: HTTPException 400
        """

    @pytest.mark.h2a
    async def test_approve_rejects_expired_task(self):
        """
        CRIT TG-4b: Cannot approve submission on expired task.
        """
```

### P1 High Priority

```python
class TestH2AFeatureFlag:
    """P1: Feature flag enforcement."""

    @pytest.mark.h2a
    async def test_create_task_disabled_feature_returns_403(self):
        """TG-5 / S-HIGH-01: H2A endpoints return 403 when feature.h2a_enabled=false."""

    @pytest.mark.h2a
    async def test_feature_flag_db_error_fails_closed(self):
        """S-HIGH-01: If DB query for feature flag fails, deny request (fail closed)."""


class TestH2ATaskCreation:
    """P1: Task creation validation."""

    @pytest.mark.h2a
    async def test_create_task_happy_path(self):
        """TG-6: Full mock of DB insert, verify response fields."""

    @pytest.mark.h2a
    async def test_create_task_bounty_below_minimum(self):
        """TG-7: Bounty $0.10 rejected (min $0.50 for H2A)."""

    @pytest.mark.h2a
    async def test_create_task_bounty_above_maximum(self):
        """TG-8: Bounty $600 rejected (max $500)."""

    @pytest.mark.h2a
    async def test_create_task_invalid_network_rejected(self):
        """V-1: payment_network not in supported networks."""


class TestH2ATaskListing:
    """P1: Task listing and submissions."""

    @pytest.mark.h2a
    async def test_list_public_only_published(self):
        """TG-9: Public listing shows only published H2A tasks."""

    @pytest.mark.h2a
    async def test_list_my_tasks_requires_auth(self):
        """TG-10: my_tasks=true requires JWT, returns only user's tasks."""

    @pytest.mark.h2a
    async def test_view_submissions_owner_only(self):
        """TG-11: Non-owner gets 403 on submissions endpoint."""

    @pytest.mark.h2a
    async def test_view_submissions_h2a_only(self):
        """TG-12: Only H2A task submissions returned."""


class TestH2ACancellation:
    """P1: Task cancellation."""

    @pytest.mark.h2a
    async def test_cancel_completed_task_rejected(self):
        """TG-13: Cannot cancel completed task."""

    @pytest.mark.h2a
    async def test_cancel_in_progress_task_rejected(self):
        """V-6: Cannot cancel task with active submissions."""
```

### P2 Medium Priority

```python
class TestH2AAgentDirectory:
    """P2: Agent directory queries."""

    @pytest.mark.h2a
    async def test_directory_filter_by_capability(self):
        """TG-16: Only agents with matching capability returned."""

    @pytest.mark.h2a
    async def test_directory_filter_by_min_rating(self):
        """TG-17: Agents below min_rating excluded."""

    @pytest.mark.h2a
    async def test_directory_sort_options(self):
        """TG-18: Sort by rating/tasks_completed/display_name."""

    @pytest.mark.h2a
    async def test_directory_pagination(self):
        """TG-19: Correct page/total counts."""

    @pytest.mark.h2a
    async def test_directory_wallet_not_exposed(self):
        """S-HIGH-04: wallet_address NOT in public response."""


class TestH2AAuth:
    """P2: JWT edge cases."""

    @pytest.mark.h2a
    async def test_jwt_expired_token(self):
        """TG-20."""

    @pytest.mark.h2a
    async def test_jwt_no_sub_claim(self):
        """TG-21."""

    @pytest.mark.h2a
    async def test_jwt_wallet_db_fallback(self):
        """TG-22: No wallet in token, found via DB lookup."""


class TestH2AApprovalVerdicts:
    """P2: Non-accepted verdicts."""

    @pytest.mark.h2a
    async def test_needs_revision_moves_to_in_progress(self):
        """TG-23."""

    @pytest.mark.h2a
    async def test_rejected_no_payment(self):
        """TG-24: Rejected verdict doesn't attempt settlement."""


class TestH2ARegistration:
    """P2: Agent executor registration via REST."""

    @pytest.mark.h2a
    async def test_register_agent_happy_path(self):
        """TG-14."""

    @pytest.mark.h2a
    async def test_register_agent_update_existing(self):
        """TG-15."""

    @pytest.mark.h2a
    async def test_register_agent_no_auth_401(self):
        """TG-27."""

    @pytest.mark.h2a
    async def test_register_agent_missing_fields_400(self):
        """TG-28: request.json() without Pydantic validation (S-MED-05)."""
```

---

## FILE 2: `test_agent_executor_tools.py` (EXTEND existing)

**Marker**: `@pytest.mark.agent_executor`
**Priority**: P0/P1
**Estimated**: 17 new tests (add to existing 46)

### P0/P1: Full Tool Tests with Mock DB

```python
class TestRegisterAsExecutorTool:
    """Test em_register_as_executor with mock DB."""

    @pytest.mark.agent_executor
    async def test_register_new_agent_executor(self):
        """Create new executor with type=agent, capabilities, agent_card_url."""

    @pytest.mark.agent_executor
    async def test_update_existing_executor_capabilities(self):
        """Upsert: update capabilities of existing agent executor."""

    @pytest.mark.agent_executor
    async def test_register_preserves_human_executors(self):
        """Agent registration doesn't affect human executors."""


class TestBrowseAgentTasksTool:
    """Test em_browse_agent_tasks with mock DB."""

    @pytest.mark.agent_executor
    async def test_browse_filters_target_executor_type(self):
        """Only tasks with target_executor_type in ('agent', 'any') returned."""

    @pytest.mark.agent_executor
    async def test_browse_client_side_capability_filter(self):
        """Tasks without matching capabilities excluded."""

    @pytest.mark.agent_executor
    async def test_browse_json_format(self):
        """response_format=json returns valid JSON."""


class TestAcceptAgentTaskTool:
    """Test em_accept_agent_task with mock DB."""

    @pytest.mark.agent_executor
    async def test_accept_published_task_success(self):
        """Agent accepts published task, status -> accepted."""

    @pytest.mark.agent_executor
    async def test_reject_human_only_task(self):
        """Error when target_executor_type='human'."""

    @pytest.mark.agent_executor
    async def test_reject_insufficient_reputation(self):
        """Error when executor_rep < task.min_reputation."""

    @pytest.mark.agent_executor
    async def test_reject_missing_capabilities(self):
        """Error when required capabilities not met."""

    @pytest.mark.agent_executor
    async def test_reject_non_published_task(self):
        """Error when task status != 'published'."""


class TestSubmitAgentWorkTool:
    """Test em_submit_agent_work with mock DB."""

    @pytest.mark.agent_executor
    async def test_auto_approve_with_fee_calculation(self):
        """Auto-approval calculates fees and logs payment event."""

    @pytest.mark.agent_executor
    async def test_auto_reject_reverts_to_accepted(self):
        """Auto-rejection reverts task status to 'accepted'."""

    @pytest.mark.agent_executor
    async def test_manual_verification_pending(self):
        """Non-auto mode leaves submission in 'pending'."""

    @pytest.mark.agent_executor
    async def test_reject_wrong_executor(self):
        """Error when executor_id doesn't match task assignment."""


class TestGetMyExecutionsTool:
    """Test em_get_my_executions with mock DB."""

    @pytest.mark.agent_executor
    async def test_filter_by_status(self):
        """Only returns tasks matching requested status."""

    @pytest.mark.agent_executor
    async def test_json_format_output(self):
        """response_format=json returns valid JSON."""
```

---

## FILE 3: `test_a2a_payment_bridge.py` — A2A Payment Integration Tests

**Marker**: `@pytest.mark.a2a_bridge`
**Priority**: P0 (critical bugs found in audit)
**Estimated**: 6 tests

```python
"""
Tests for A2A Protocol <-> Payment System bridge.

These tests verify that A2A operations (approve, cancel) properly
integrate with PaymentDispatcher to avoid fund loss.

P0 bugs found in audit:
- task_manager.py:540 - send_message("approve") bypasses PaymentDispatcher
- task_manager.py:448 - cancel_task() doesn't trigger refund
"""


class TestA2AApprovalPaymentBridge:
    """P0: A2A approval must trigger payment release."""

    @pytest.mark.a2a_bridge
    async def test_a2a_approve_calls_payment_dispatcher(self):
        """
        P0-3: send_message with "approve" content MUST call
        PaymentDispatcher.execute_payment() before marking completed.
        - Mock: task with escrow, executor with wallet
        - Assert: PaymentDispatcher.execute_payment called
        - Assert: task status -> completed ONLY after payment succeeds
        """

    @pytest.mark.a2a_bridge
    async def test_a2a_approve_payment_failure_stays_working(self):
        """
        If PaymentDispatcher fails, task should NOT move to completed.
        A2A state should remain 'working', not 'completed'.
        """

    @pytest.mark.a2a_bridge
    async def test_a2a_approve_triggers_webhooks(self):
        """
        A2A approval must dispatch webhooks like regular approval.
        - Assert: webhook_dispatch called with correct payload
        """


class TestA2ACancellationRefund:
    """P0: A2A cancellation must trigger escrow refund."""

    @pytest.mark.a2a_bridge
    async def test_a2a_cancel_calls_refund(self):
        """
        P0-4: cancel_task() MUST call PaymentDispatcher.refund_payment()
        when task has active escrow.
        - Mock: task with escrow_id in escrows table
        - Assert: PaymentDispatcher.refund_payment called
        - Assert: task status -> cancelled ONLY after refund succeeds
        """

    @pytest.mark.a2a_bridge
    async def test_a2a_cancel_no_escrow_succeeds(self):
        """
        Cancelling a task with no escrow (balance-check-only / Fase 1)
        should succeed without calling refund.
        """

    @pytest.mark.a2a_bridge
    async def test_a2a_cancel_refund_failure_stays_active(self):
        """
        If refund fails, task should NOT move to cancelled.
        """
```

---

## FILE 4: `test_a2a_agent_executor_lifecycle.py` — Integration Tests

**Marker**: `@pytest.mark.agent_executor` + `@pytest.mark.a2a_bridge`
**Priority**: P1
**Estimated**: 8 tests

```python
"""
Integration tests for the full Agent Executor lifecycle.
Tests the complete flow: register -> browse -> accept -> submit -> approve.
Also tests cross-layer interactions between A2A and MCP tools.
"""


class TestAgentExecutorLifecycle:
    """Full lifecycle integration tests."""

    @pytest.mark.agent_executor
    async def test_full_lifecycle_auto_approve(self):
        """
        Complete flow: register -> browse -> accept -> submit -> auto-approve.
        Verify each status transition and final fee calculation.
        """

    @pytest.mark.agent_executor
    async def test_full_lifecycle_manual_approve(self):
        """
        register -> browse -> accept -> submit (manual) -> pending.
        """

    @pytest.mark.agent_executor
    async def test_rejection_retry_flow(self):
        """
        submit (auto-reject) -> task reverts to accepted -> retry -> auto-approve.
        """

    @pytest.mark.agent_executor
    async def test_concurrent_accept_race_condition(self):
        """
        Two agents accept the same task simultaneously.
        One should succeed, one should get "task not published" error.
        """


class TestA2AMCPBridgeGap:
    """Tests documenting the gap between A2A and MCP layers."""

    @pytest.mark.a2a_bridge
    async def test_a2a_create_includes_escrow(self):
        """
        A2A create_task should include escrow authorization
        (currently bypasses it — this test should FAIL until fixed).
        """

    @pytest.mark.a2a_bridge
    async def test_a2a_create_dispatches_webhooks(self):
        """
        A2A create_task should dispatch webhooks
        (currently bypasses — this test should FAIL until fixed).
        """

    @pytest.mark.a2a_bridge
    async def test_a2a_create_sends_ws_notification(self):
        """
        A2A create_task should send WebSocket notification
        (currently bypasses — this test should FAIL until fixed).
        """


class TestAgentExecutorSecurity:
    """Security tests for Agent Executor tools."""

    @pytest.mark.agent_executor
    @pytest.mark.security
    async def test_cannot_submit_as_wrong_executor(self):
        """
        Agent A cannot submit work for a task assigned to Agent B.
        """
```

---

## FILE 5: `test_migrations_031_033.py` — DB Migration Integrity

**Marker**: `@pytest.mark.migrations`
**Priority**: P2
**Estimated**: 22 tests

```python
"""
Database migration integrity tests for migrations 031-033.
Tests column existence, constraints, defaults, indexes, and cross-migration consistency.
"""


class TestMigration031AgentExecutor:
    """Migration 031: Agent Executor Support."""

    @pytest.mark.migrations
    def test_executor_type_column_exists(self):
        """executors.executor_type column present."""

    @pytest.mark.migrations
    def test_executor_type_default_human(self):
        """New executors default to 'human'."""

    @pytest.mark.migrations
    def test_executor_type_constraint_values(self):
        """Only 'human' or 'agent' allowed."""

    @pytest.mark.migrations
    def test_capabilities_column_is_text_array(self):
        """executors.capabilities is TEXT[]."""

    @pytest.mark.migrations
    def test_target_executor_type_default_any(self):
        """tasks.target_executor_type defaults to 'any'."""

    @pytest.mark.migrations
    def test_target_executor_type_constraint(self):
        """Only 'human', 'agent', 'any' allowed."""

    @pytest.mark.migrations
    def test_verification_mode_constraint(self):
        """Only 'manual', 'auto', 'oracle' allowed."""

    @pytest.mark.migrations
    def test_api_key_type_constraint(self):
        """Only 'publisher', 'executor', 'admin' allowed."""

    @pytest.mark.migrations
    def test_new_task_categories_exist(self):
        """All 6 digital categories in task_category enum."""

    @pytest.mark.migrations
    def test_gin_index_capabilities(self):
        """GIN index on capabilities supports containment."""


class TestMigration032AgentCards:
    """Migration 032: Agent Cards + Activity Feed."""

    @pytest.mark.migrations
    def test_agent_type_constraint(self):
        """Only 'human', 'ai', 'organization' allowed."""

    @pytest.mark.migrations
    def test_activity_feed_table_exists(self):
        """activity_feed table created."""

    @pytest.mark.migrations
    def test_activity_feed_trigger_on_insert(self):
        """Published task insert creates feed entry."""

    @pytest.mark.migrations
    def test_activity_feed_trigger_on_complete(self):
        """Status -> completed creates feed entry."""

    @pytest.mark.migrations
    def test_activity_feed_rls_public_read(self):
        """Anyone can SELECT from activity_feed."""

    @pytest.mark.migrations
    def test_activity_feed_rls_no_anon_insert(self):
        """Anonymous cannot INSERT into activity_feed."""


class TestMigration033H2A:
    """Migration 033: H2A Marketplace."""

    @pytest.mark.migrations
    def test_publisher_type_default_agent(self):
        """tasks.publisher_type defaults to 'agent'."""

    @pytest.mark.migrations
    def test_publisher_type_constraint(self):
        """Only 'agent' or 'human' allowed."""

    @pytest.mark.migrations
    def test_human_wallet_nullable(self):
        """human_wallet can be NULL for A2H tasks."""

    @pytest.mark.migrations
    def test_h2a_feature_flags_exist(self):
        """3 H2A feature flags in platform_config."""


class TestCrossMigrationConsistency:
    """Cross-migration consistency checks."""

    @pytest.mark.migrations
    def test_model_db_enum_match_executor_type(self):
        """Python ExecutorType matches DB CHECK constraint."""

    @pytest.mark.migrations
    def test_model_db_enum_match_publisher_type(self):
        """Python PublisherType matches DB CHECK constraint."""
```

---

## FILE 6 (E2E): `e2e/h2a-publisher.spec.ts` — Dashboard E2E

**Priority**: P1
**Estimated**: 7 scenarios

```typescript
// Scenarios (see dashboard audit for full details):
// 1. Publisher creates H2A task via 4-step wizard
// 2. Publisher dashboard shows created tasks with correct stats
// 3. Publisher reviews agent submission (expect payment error with placeholders)
// 4. Agent Directory allows browsing and capability filtering
// 5. Agent selected from directory pre-fills wizard
// 6. Publisher cancels published task
// 7. FAQ page renders H2A and A2A sections
```

---

## Existing File Extensions

### `test_h2a.py` — Add missing model tests

```python
# Extend TestH2AModels:
def test_h2a_task_with_all_optional_fields(self):
    """TG-25: required_capabilities, verification_mode, target_agent_id."""

def test_h2a_task_a2h_returns_404(self):
    """TG-26: GET /h2a/tasks/{id} for non-H2A task returns 404."""

def test_fee_calculation_per_category(self):
    """TG-29: Category-based rates from FeeManager vs flat 13%."""
```

### `test_a2a_protocol.py` — Add payment bridge coverage

```python
# Extend existing A2A tests:
def test_a2a_status_mapping_includes_payment_check(self):
    """A2A completed state requires payment confirmation."""

def test_a2a_task_manager_uses_shared_logic(self):
    """create_task in A2A uses same validation as em_publish_task."""
```

---

## Summary Table

| File | New tests | Markers | Priority |
|------|-----------|---------|----------|
| `test_h2a_endpoints.py` | 30 | `h2a` | P0-P2 |
| `test_agent_executor.py` (extend) | 17 | `agent_executor` | P0-P1 |
| `test_a2a_payment_bridge.py` | 6 | `a2a_bridge` | P0 |
| `test_a2a_agent_executor_lifecycle.py` | 8 | `agent_executor`, `a2a_bridge` | P1 |
| `test_migrations_031_033.py` | 22 | `migrations` | P2 |
| `e2e/h2a-publisher.spec.ts` | 7 | E2E | P1 |
| `test_h2a.py` (extend) | 3 | `h2a` | P2 |
| `test_a2a_protocol.py` (extend) | 2 | `infrastructure` | P2 |
| **TOTAL** | **95** | | |

---

## Implementation Order

### Sprint 1 (P0 — Block production)
1. `test_a2a_payment_bridge.py` — 6 tests (validates fund-loss bugs)
2. `test_h2a_endpoints.py` Critical section — 5 tests (settlement atomicity)
3. `test_agent_executor.py` extensions — 5 tool tests (accept/submit)

### Sprint 2 (P1 — Current sprint)
4. `test_h2a_endpoints.py` High section — 10 tests
5. `test_a2a_agent_executor_lifecycle.py` — 8 tests
6. `test_agent_executor.py` remaining — 12 tests
7. `e2e/h2a-publisher.spec.ts` — 7 E2E scenarios

### Sprint 3 (P2 — Next sprint)
8. `test_h2a_endpoints.py` Medium section — 15 tests
9. `test_migrations_031_033.py` — 22 tests
10. Extensions to existing files — 5 tests

---

## Post-test Fixes Required

The following code fixes should accompany the tests:

| Fix | File | Description | Tests that validate |
|-----|------|-------------|---------------------|
| **FIX-1** | `a2a/task_manager.py:540` | Integrate PaymentDispatcher in approve flow | `test_a2a_approve_calls_payment_dispatcher` |
| **FIX-2** | `a2a/task_manager.py:448` | Call refund on cancel | `test_a2a_cancel_calls_refund` |
| **FIX-3** | `api/h2a.py:643` | Make settlement atomic (fail on payment error) | `test_approve_settlement_failure_is_atomic` |
| **FIX-4** | `api/h2a.py:567` | Add task status validation in approve | `test_approve_rejects_already_completed_task` |
| **FIX-5** | `api/h2a.py:56` | Fix treasury address fallback | Manual verification |
| **FIX-6** | `api/h2a.py:217` | Feature flag fail-closed | `test_feature_flag_db_error_fails_closed` |
| **FIX-7** | `dashboard/src/App.tsx:411` | Fix `:id` vs `:taskId` param | E2E tests |

---

*Generated from consolidated audit findings. See individual reports in `docs/reports/AUDIT_*_2026-02-18.md`.*
