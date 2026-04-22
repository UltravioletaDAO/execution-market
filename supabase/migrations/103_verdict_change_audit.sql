-- Migration 103: Audit trail for every submissions.agent_verdict mutation
-- Source: MASTER_PLAN_ARBITER_ZOMBIE_DISPUTE_FIX.md Phase 4.3 (INC-2026-04-22)
--
-- After the INC-2026-04-22 incident, we need unambiguous forensics on who
-- changed a submission's agent_verdict and from what. Two signals caught us
-- by surprise in the incident:
--   (a) Ring 2 arbiter was mutating agent_verdict via escalation.py without
--       any audit row. We only noticed by querying the submissions table.
--   (b) The service-role patch that unblocked Souk el Hbous / Rick's Cafe
--       left no trail either. "Who reset this?" required Git archaeology.
--
-- Strategy: DB trigger. Independent of Python paths (approve/reject, H2A,
-- agent executor tools, arbiter processor, escalation, manual service-role
-- patches all go through the same trigger). Writes into payment_events as
-- event_type='verdict_change' with OLD + NEW verdict in metadata.
--
-- Idempotent: DROP IF EXISTS on constraint + trigger.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Extend payment_events.event_type CHECK constraint to accept 'verdict_change'
-- ---------------------------------------------------------------------------
-- The constraint from migration 053 enumerates every valid event_type. We
-- must drop + re-create to add the new value. All existing values preserved.

ALTER TABLE payment_events DROP CONSTRAINT IF EXISTS chk_payment_events_event_type;

ALTER TABLE payment_events
    ADD CONSTRAINT chk_payment_events_event_type
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
        'error',
        -- Ring 2 arbiter + publisher decision audit (INC-2026-04-22)
        'verdict_change',
        -- Task expiration refund (pre-existing in code, now explicit)
        'refund_failed'
    ));

-- ---------------------------------------------------------------------------
-- 2. Trigger function: log verdict change
-- ---------------------------------------------------------------------------
-- Fires on UPDATE of agent_verdict. IS DISTINCT FROM handles NULL correctly.
-- Writes a payment_events row with:
--   task_id        = OLD.task_id   (always present, FK to tasks)
--   event_type     = 'verdict_change'
--   status         = 'success'
--   metadata.submission_id  = OLD.id
--   metadata.old_verdict    = OLD.agent_verdict (nullable)
--   metadata.new_verdict    = NEW.agent_verdict (nullable)
--   metadata.actor          = JWT sub claim if present, else NULL
--   metadata.source         = 'db_trigger'
--   metadata.changed_at     = NOW()

CREATE OR REPLACE FUNCTION log_submission_verdict_change()
RETURNS TRIGGER AS $$
DECLARE
    v_actor TEXT := NULL;
    v_jwt_role TEXT := NULL;
BEGIN
    -- PostgREST populates request.jwt.claims on every call. Reading it is
    -- best-effort -- failures here must NOT block the mutation.
    BEGIN
        v_actor := current_setting('request.jwt.claims', true)::json->>'sub';
        v_jwt_role := current_setting('request.jwt.claims', true)::json->>'role';
    EXCEPTION WHEN OTHERS THEN
        v_actor := NULL;
        v_jwt_role := NULL;
    END;

    INSERT INTO payment_events (
        task_id,
        event_type,
        status,
        metadata,
        created_at
    ) VALUES (
        OLD.task_id,
        'verdict_change',
        'success',
        jsonb_build_object(
            'submission_id', OLD.id,
            'old_verdict',   OLD.agent_verdict,
            'new_verdict',   NEW.agent_verdict,
            'actor',         v_actor,
            'jwt_role',      v_jwt_role,
            'source',        'db_trigger',
            'changed_at',    NOW()
        ),
        NOW()
    );

    RETURN NEW;
EXCEPTION WHEN OTHERS THEN
    -- Never let audit failure block a legitimate verdict change.
    RAISE WARNING 'verdict_change trigger failed for submission %: %', OLD.id, SQLERRM;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION log_submission_verdict_change() IS
    'Inserts a payment_events verdict_change audit row whenever '
    'submissions.agent_verdict changes. Non-blocking (errors raise WARNING). '
    'Added 2026-04-22 after INC-2026-04-22 zombie dispute incident.';

-- ---------------------------------------------------------------------------
-- 3. Trigger wire-up
-- ---------------------------------------------------------------------------
-- AFTER UPDATE OF agent_verdict fires only when that column is the UPDATE
-- target, and the WHEN clause ensures we don't log UPDATEs that leave the
-- value unchanged (e.g. bulk UPDATEs that touch every column).

DROP TRIGGER IF EXISTS trg_submissions_verdict_change ON submissions;

CREATE TRIGGER trg_submissions_verdict_change
    AFTER UPDATE OF agent_verdict ON submissions
    FOR EACH ROW
    WHEN (OLD.agent_verdict IS DISTINCT FROM NEW.agent_verdict)
    EXECUTE FUNCTION log_submission_verdict_change();

COMMENT ON TRIGGER trg_submissions_verdict_change ON submissions IS
    'INC-2026-04-22 audit trigger: any change to agent_verdict writes a '
    'verdict_change event to payment_events. Captures mutations from any '
    'path: approve/reject API, H2A endpoint, MCP tools, arbiter processor, '
    'escalation, and direct service-role patches.';

COMMIT;
