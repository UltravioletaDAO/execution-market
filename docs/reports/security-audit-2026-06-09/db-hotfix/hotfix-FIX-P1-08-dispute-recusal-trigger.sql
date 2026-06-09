-- ===========================================================================
-- HOTFIX FIX-P1-08 (paste into the Supabase SQL editor) — dispute resolver
-- recusal trigger. Rejects marking a dispute resolved with resolved_by equal to
-- a party (publisher agent_id or the executor's wallet). Idempotent.
-- Mirrors supabase/migrations/115_dispute_resolution_recusal_guard.sql.
-- ===========================================================================
CREATE OR REPLACE FUNCTION enforce_dispute_resolver_recusal()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE v_executor_wallet TEXT;
BEGIN
    IF NEW.status IN ('resolved_for_agent','resolved_for_executor','settled')
       AND NEW.resolved_by IS NOT NULL
       AND COALESCE(OLD.status::text,'') NOT IN
           ('resolved_for_agent','resolved_for_executor','settled','closed') THEN
        IF lower(NEW.resolved_by) = lower(COALESCE(NEW.agent_id,'')) THEN
            RAISE EXCEPTION 'Recusal: publisher (%) cannot resolve own dispute', NEW.agent_id;
        END IF;
        IF NEW.executor_id IS NOT NULL THEN
            SELECT lower(wallet_address) INTO v_executor_wallet
            FROM executors WHERE id = NEW.executor_id;
            IF v_executor_wallet IS NOT NULL
               AND lower(NEW.resolved_by) = v_executor_wallet THEN
                RAISE EXCEPTION 'Recusal: executor cannot resolve own dispute';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END; $$;

DROP TRIGGER IF EXISTS trg_dispute_resolver_recusal ON disputes;
CREATE TRIGGER trg_dispute_resolver_recusal
    BEFORE UPDATE ON disputes FOR EACH ROW
    EXECUTE FUNCTION enforce_dispute_resolver_recusal();
