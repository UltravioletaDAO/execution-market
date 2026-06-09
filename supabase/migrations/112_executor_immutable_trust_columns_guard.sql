-- Migration 112: Extend executor immutable-field guard to trust/financial columns
-- Source: Security Audit 2026-06-09, finding FIX-P1-04
-- Closes the gap where executors_update_own (001) + the incomplete
-- prevent_executor_tampering trigger (050) let an authenticated browser
-- self-set World ID / VeryAI / ClawKey / KYC flags and edit wallet_address,
-- balance_usdc, status, and erc8004_agent_id on its OWN executor row.
--
-- The backend (service_role key, mcp_server/supabase_client.py) bypasses this
-- guard via the trigger's WHEN (current_setting('role') <> 'service_role')
-- clause, so all legitimate server-side writes (worldid.py, veryai.py,
-- clawkey.py, payment reconciliation) continue to work. The SPA profile-edit
-- paths only touch non-guarded columns and are unaffected.
--
-- Idempotent: CREATE OR REPLACE FUNCTION; the trigger from 050 is reused.
-- Applied to production: pending.

BEGIN;

CREATE OR REPLACE FUNCTION prevent_executor_tampering()
RETURNS TRIGGER AS $$
BEGIN
    -- ---- Reputation & task stats (original 050 set — unchanged) ----
    IF NEW.reputation_score IS DISTINCT FROM OLD.reputation_score THEN
        RAISE EXCEPTION 'Cannot modify reputation_score directly — use backend functions';
    END IF;
    IF NEW.tier IS DISTINCT FROM OLD.tier THEN
        RAISE EXCEPTION 'Cannot modify tier directly — managed by update_executor_tier trigger';
    END IF;
    IF NEW.tasks_completed IS DISTINCT FROM OLD.tasks_completed THEN
        RAISE EXCEPTION 'Cannot modify tasks_completed directly — managed by task completion trigger';
    END IF;
    IF NEW.tasks_disputed IS DISTINCT FROM OLD.tasks_disputed THEN
        RAISE EXCEPTION 'Cannot modify tasks_disputed directly';
    END IF;
    IF NEW.tasks_abandoned IS DISTINCT FROM OLD.tasks_abandoned THEN
        RAISE EXCEPTION 'Cannot modify tasks_abandoned directly';
    END IF;

    -- ---- World ID trust flags (084) — anti-sybil gate source ----
    IF NEW.world_id_verified IS DISTINCT FROM OLD.world_id_verified THEN
        RAISE EXCEPTION 'Cannot modify world_id_verified directly — set by backend after World ID Cloud API verification';
    END IF;
    IF NEW.world_id_level IS DISTINCT FROM OLD.world_id_level THEN
        RAISE EXCEPTION 'Cannot modify world_id_level directly — set by backend';
    END IF;

    -- ---- VeryAI trust flags (104) ----
    IF NEW.veryai_verified IS DISTINCT FROM OLD.veryai_verified THEN
        RAISE EXCEPTION 'Cannot modify veryai_verified directly — set by backend after VeryAI OIDC verification';
    END IF;
    IF NEW.veryai_level IS DISTINCT FROM OLD.veryai_level THEN
        RAISE EXCEPTION 'Cannot modify veryai_level directly — set by backend';
    END IF;
    IF NEW.veryai_sub IS DISTINCT FROM OLD.veryai_sub THEN
        RAISE EXCEPTION 'Cannot modify veryai_sub directly — set by backend';
    END IF;
    IF NEW.veryai_verified_at IS DISTINCT FROM OLD.veryai_verified_at THEN
        RAISE EXCEPTION 'Cannot modify veryai_verified_at directly — set by backend';
    END IF;

    -- ---- ClawKey KYA flags (106) ----
    IF NEW.clawkey_verified IS DISTINCT FROM OLD.clawkey_verified THEN
        RAISE EXCEPTION 'Cannot modify clawkey_verified directly — set by backend ClawKey sync';
    END IF;
    IF NEW.clawkey_human_id IS DISTINCT FROM OLD.clawkey_human_id THEN
        RAISE EXCEPTION 'Cannot modify clawkey_human_id directly — set by backend';
    END IF;
    IF NEW.clawkey_device_id IS DISTINCT FROM OLD.clawkey_device_id THEN
        RAISE EXCEPTION 'Cannot modify clawkey_device_id directly — set by backend';
    END IF;
    IF NEW.clawkey_public_key IS DISTINCT FROM OLD.clawkey_public_key THEN
        RAISE EXCEPTION 'Cannot modify clawkey_public_key directly — set by backend';
    END IF;
    IF NEW.clawkey_registered_at IS DISTINCT FROM OLD.clawkey_registered_at THEN
        RAISE EXCEPTION 'Cannot modify clawkey_registered_at directly — set by backend';
    END IF;

    -- ---- Generic KYC / verification (001) ----
    IF NEW.is_verified IS DISTINCT FROM OLD.is_verified THEN
        RAISE EXCEPTION 'Cannot modify is_verified directly — set by backend';
    END IF;
    IF NEW.kyc_completed_at IS DISTINCT FROM OLD.kyc_completed_at THEN
        RAISE EXCEPTION 'Cannot modify kyc_completed_at directly — set by backend';
    END IF;

    -- ---- Financial mirror columns (001) ----
    IF NEW.balance_usdc IS DISTINCT FROM OLD.balance_usdc THEN
        RAISE EXCEPTION 'Cannot modify balance_usdc directly — managed by payment reconciliation';
    END IF;
    IF NEW.total_earned_usdc IS DISTINCT FROM OLD.total_earned_usdc THEN
        RAISE EXCEPTION 'Cannot modify total_earned_usdc directly — managed by payment reconciliation';
    END IF;
    IF NEW.total_withdrawn_usdc IS DISTINCT FROM OLD.total_withdrawn_usdc THEN
        RAISE EXCEPTION 'Cannot modify total_withdrawn_usdc directly — managed by payment reconciliation';
    END IF;

    -- ---- Identity / lifecycle ----
    IF NEW.wallet_address IS DISTINCT FROM OLD.wallet_address THEN
        RAISE EXCEPTION 'Cannot modify wallet_address directly — set at registration via backend';
    END IF;
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        RAISE EXCEPTION 'Cannot modify status directly — managed by backend';
    END IF;
    IF NEW.erc8004_agent_id IS DISTINCT FROM OLD.erc8004_agent_id THEN
        RAISE EXCEPTION 'Cannot modify erc8004_agent_id directly — set by backend after on-chain registration';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- The trigger from migration 050 (guard_executor_immutable_fields) already
-- points at this function with the correct service_role bypass; no DDL change
-- to the trigger is needed. Re-assert it defensively in case 050 was never
-- applied to this database.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'guard_executor_immutable_fields'
          AND tgrelid = 'public.executors'::regclass
    ) THEN
        CREATE TRIGGER guard_executor_immutable_fields
            BEFORE UPDATE ON executors
            FOR EACH ROW
            WHEN (current_setting('role', true) IS DISTINCT FROM 'service_role')
            EXECUTE FUNCTION prevent_executor_tampering();
        RAISE NOTICE '112: created missing guard_executor_immutable_fields trigger';
    ELSE
        RAISE NOTICE '112: guard_executor_immutable_fields trigger already present (reusing)';
    END IF;
END $$;

COMMENT ON FUNCTION prevent_executor_tampering() IS
    'Blocks non-service_role UPDATEs to immutable executor columns: reputation/stats (050) '
    'plus trust flags (world_id_*, veryai_*, clawkey_*, is_verified, kyc_completed_at), '
    'financial mirrors (balance_usdc, total_earned_usdc, total_withdrawn_usdc), and '
    'identity (wallet_address, status, erc8004_agent_id). Extended by migration 112 '
    '(Security Audit 2026-06-09, FIX-P1-04).';

COMMIT;

-- ============================================================================
-- ROLLBACK (re-opens the hole — emergency use only)
-- ============================================================================
-- CREATE OR REPLACE FUNCTION prevent_executor_tampering()
-- RETURNS TRIGGER AS $$
-- BEGIN
--     IF NEW.reputation_score IS DISTINCT FROM OLD.reputation_score THEN RAISE EXCEPTION 'Cannot modify reputation_score directly'; END IF;
--     IF NEW.tier            IS DISTINCT FROM OLD.tier            THEN RAISE EXCEPTION 'Cannot modify tier directly'; END IF;
--     IF NEW.tasks_completed IS DISTINCT FROM OLD.tasks_completed THEN RAISE EXCEPTION 'Cannot modify tasks_completed directly'; END IF;
--     IF NEW.tasks_disputed  IS DISTINCT FROM OLD.tasks_disputed  THEN RAISE EXCEPTION 'Cannot modify tasks_disputed directly'; END IF;
--     IF NEW.tasks_abandoned IS DISTINCT FROM OLD.tasks_abandoned THEN RAISE EXCEPTION 'Cannot modify tasks_abandoned directly'; END IF;
--     RETURN NEW;
-- END;
-- $$ LANGUAGE plpgsql;
