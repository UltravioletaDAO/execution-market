-- Migration 115: Defense-in-depth guard for dispute resolution recusal.
-- Source: Security Audit 2026-06-09, finding FIX-P1-08.
-- The REST resolve path enforces recusal in Python (service-role bypasses RLS),
-- so this migration adds an audit-friendly DB trigger that rejects a
-- party-as-resolver, callable from any future non-service path, plus a
-- comment documenting the control.
--
-- Idempotent: CREATE OR REPLACE FUNCTION + DROP/CREATE TRIGGER.
-- Applied to production: pending.

BEGIN;

-- Trigger-enforced recusal: a dispute may not be marked resolved with
-- resolved_by equal to either party (publisher agent_id or the executor's wallet).
CREATE OR REPLACE FUNCTION enforce_dispute_resolver_recusal()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_executor_wallet TEXT;
BEGIN
    -- Only check on transition INTO a resolved state with a resolver set.
    -- NEW.status is the dispute_status enum; comparing against text literals
    -- works because PostgreSQL coerces the literals to the enum type.
    IF NEW.status IN (
        'resolved_for_agent', 'resolved_for_executor', 'settled'
    ) AND NEW.resolved_by IS NOT NULL
      AND COALESCE(OLD.status::text, '') NOT IN (
        'resolved_for_agent', 'resolved_for_executor', 'settled', 'closed'
    ) THEN
        -- Publisher (agent_id) may not be the resolver.
        IF lower(NEW.resolved_by) = lower(COALESCE(NEW.agent_id, '')) THEN
            RAISE EXCEPTION
                'Recusal: dispute publisher (%) cannot resolve their own dispute',
                NEW.agent_id;
        END IF;
        -- Executor wallet may not be the resolver.
        IF NEW.executor_id IS NOT NULL THEN
            SELECT lower(wallet_address) INTO v_executor_wallet
            FROM executors WHERE id = NEW.executor_id;
            IF v_executor_wallet IS NOT NULL
               AND lower(NEW.resolved_by) = v_executor_wallet THEN
                RAISE EXCEPTION
                    'Recusal: dispute executor cannot resolve their own dispute';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_dispute_resolver_recusal ON disputes;
CREATE TRIGGER trg_dispute_resolver_recusal
    BEFORE UPDATE ON disputes
    FOR EACH ROW
    EXECUTE FUNCTION enforce_dispute_resolver_recusal();

COMMENT ON FUNCTION enforce_dispute_resolver_recusal() IS
    'FIX-P1-08 (migration 115): rejects a dispute resolution where resolved_by is a party '
    '(publisher agent_id or executor wallet). Recusal enforcement (defense-in-depth '
    'behind the Python resolve path in api/routers/disputes.py).';

COMMIT;

-- ===========================================================================
-- ROLLBACK (manual)
-- ===========================================================================
-- DROP TRIGGER IF EXISTS trg_dispute_resolver_recusal ON disputes;
-- DROP FUNCTION IF EXISTS enforce_dispute_resolver_recusal();
