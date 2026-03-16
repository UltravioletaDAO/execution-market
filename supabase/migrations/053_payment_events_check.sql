-- Migration 053: CHECK Constraint on payment_events.event_type
-- Source: DB Optimization Audit 2026-03-15 (Phase 2, Task 2.4)
-- Currently event_type is TEXT with no validation — any string is accepted.
-- This constraint enforces the known event types from the codebase,
-- preventing typos and invalid data from entering the audit trail.
-- Applied to production: pending.

-- Complete list derived from mcp_server/integrations/x402/payment_dispatcher.py,
-- mcp_server/api/h2a.py, mcp_server/api/reputation.py, mcp_server/server.py,
-- and mcp_server/api/routers/tasks.py.
ALTER TABLE payment_events ADD CONSTRAINT chk_payment_events_event_type
    CHECK (event_type IN (
        -- Core payment flow
        'verify',
        'balance_check',
        'store_auth',
        'settle',
        -- Fase 1 direct settlement
        'settle_worker_direct',
        'settle_fee_direct',
        -- Fase 2/5 escrow flow
        'escrow_authorize',
        'escrow_release',
        'escrow_refund',
        -- Platform release disbursements
        'disburse_worker',
        'disburse_fee',
        'distribute_fees',
        'fee_sweep',
        'fee_collect',
        -- H2A (human-published tasks)
        'h2a_settle_worker',
        'h2a_settle_fee',
        'h2a_settle_error',
        -- Reputation events
        'reputation_agent_rates_worker',
        'reputation_worker_rates_agent',
        -- Lifecycle
        'refund',
        'cancel',
        'error'
    ));
