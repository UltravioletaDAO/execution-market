-- ===========================================================================
-- HOTFIX FIX-P1-04 (paste into the Supabase SQL editor) — extend the executor
-- immutable-field guard to trust / financial / identity columns. Idempotent.
-- Mirrors supabase/migrations/112_executor_immutable_trust_columns_guard.sql.
--
-- COLUMN-NAME CAVEAT: before running, confirm the live executors table has every
-- referenced column (veryai_*, clawkey_*, etc. — i.e. migrations 104/106 applied).
-- plpgsql is late-bound, so a missing column raises at the first UPDATE, not at
-- CREATE FUNCTION. If a DB is behind on 104/106, run those first or remove the
-- corresponding IF blocks for columns that do not yet exist.
-- ===========================================================================
BEGIN;

CREATE OR REPLACE FUNCTION prevent_executor_tampering()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.reputation_score   IS DISTINCT FROM OLD.reputation_score   THEN RAISE EXCEPTION 'Cannot modify reputation_score directly'; END IF;
    IF NEW.tier               IS DISTINCT FROM OLD.tier               THEN RAISE EXCEPTION 'Cannot modify tier directly'; END IF;
    IF NEW.tasks_completed    IS DISTINCT FROM OLD.tasks_completed    THEN RAISE EXCEPTION 'Cannot modify tasks_completed directly'; END IF;
    IF NEW.tasks_disputed     IS DISTINCT FROM OLD.tasks_disputed     THEN RAISE EXCEPTION 'Cannot modify tasks_disputed directly'; END IF;
    IF NEW.tasks_abandoned    IS DISTINCT FROM OLD.tasks_abandoned    THEN RAISE EXCEPTION 'Cannot modify tasks_abandoned directly'; END IF;
    IF NEW.world_id_verified  IS DISTINCT FROM OLD.world_id_verified  THEN RAISE EXCEPTION 'Cannot modify world_id_verified directly'; END IF;
    IF NEW.world_id_level     IS DISTINCT FROM OLD.world_id_level     THEN RAISE EXCEPTION 'Cannot modify world_id_level directly'; END IF;
    IF NEW.veryai_verified    IS DISTINCT FROM OLD.veryai_verified    THEN RAISE EXCEPTION 'Cannot modify veryai_verified directly'; END IF;
    IF NEW.veryai_level       IS DISTINCT FROM OLD.veryai_level       THEN RAISE EXCEPTION 'Cannot modify veryai_level directly'; END IF;
    IF NEW.veryai_sub         IS DISTINCT FROM OLD.veryai_sub         THEN RAISE EXCEPTION 'Cannot modify veryai_sub directly'; END IF;
    IF NEW.veryai_verified_at IS DISTINCT FROM OLD.veryai_verified_at THEN RAISE EXCEPTION 'Cannot modify veryai_verified_at directly'; END IF;
    IF NEW.clawkey_verified   IS DISTINCT FROM OLD.clawkey_verified   THEN RAISE EXCEPTION 'Cannot modify clawkey_verified directly'; END IF;
    IF NEW.clawkey_human_id   IS DISTINCT FROM OLD.clawkey_human_id   THEN RAISE EXCEPTION 'Cannot modify clawkey_human_id directly'; END IF;
    IF NEW.clawkey_device_id  IS DISTINCT FROM OLD.clawkey_device_id  THEN RAISE EXCEPTION 'Cannot modify clawkey_device_id directly'; END IF;
    IF NEW.clawkey_public_key IS DISTINCT FROM OLD.clawkey_public_key THEN RAISE EXCEPTION 'Cannot modify clawkey_public_key directly'; END IF;
    IF NEW.clawkey_registered_at IS DISTINCT FROM OLD.clawkey_registered_at THEN RAISE EXCEPTION 'Cannot modify clawkey_registered_at directly'; END IF;
    IF NEW.is_verified        IS DISTINCT FROM OLD.is_verified        THEN RAISE EXCEPTION 'Cannot modify is_verified directly'; END IF;
    IF NEW.kyc_completed_at   IS DISTINCT FROM OLD.kyc_completed_at   THEN RAISE EXCEPTION 'Cannot modify kyc_completed_at directly'; END IF;
    IF NEW.balance_usdc       IS DISTINCT FROM OLD.balance_usdc       THEN RAISE EXCEPTION 'Cannot modify balance_usdc directly'; END IF;
    IF NEW.total_earned_usdc  IS DISTINCT FROM OLD.total_earned_usdc  THEN RAISE EXCEPTION 'Cannot modify total_earned_usdc directly'; END IF;
    IF NEW.total_withdrawn_usdc IS DISTINCT FROM OLD.total_withdrawn_usdc THEN RAISE EXCEPTION 'Cannot modify total_withdrawn_usdc directly'; END IF;
    IF NEW.wallet_address     IS DISTINCT FROM OLD.wallet_address     THEN RAISE EXCEPTION 'Cannot modify wallet_address directly'; END IF;
    IF NEW.status             IS DISTINCT FROM OLD.status             THEN RAISE EXCEPTION 'Cannot modify status directly'; END IF;
    IF NEW.erc8004_agent_id   IS DISTINCT FROM OLD.erc8004_agent_id   THEN RAISE EXCEPTION 'Cannot modify erc8004_agent_id directly'; END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Ensure the trigger exists (no-op if migration 050 already created it).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'guard_executor_immutable_fields'
          AND tgrelid = 'public.executors'::regclass
    ) THEN
        CREATE TRIGGER guard_executor_immutable_fields
            BEFORE UPDATE ON executors FOR EACH ROW
            WHEN (current_setting('role', true) IS DISTINCT FROM 'service_role')
            EXECUTE FUNCTION prevent_executor_tampering();
    END IF;
END $$;

COMMIT;
