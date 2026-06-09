-- ===========================================================================
-- HOTFIX FIX-P1-05 (paste into the Supabase SQL editor) — lock down every
-- anon-executable SECURITY DEFINER RPC in schema public, except the login
-- allowlist (get_or_create_executor — itself revoked from anon by FIX-P0-02).
-- Idempotent; safe to run multiple times. Run as the project owner.
-- Mirrors supabase/migrations/113_lockdown_security_definer_rpcs.sql.
-- ===========================================================================
BEGIN;

DO $$
DECLARE
    r RECORD;
    allowlist text[] := ARRAY['get_or_create_executor'];
BEGIN
    FOR r IN
        SELECT p.oid::regprocedure AS sig
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.prosecdef
          AND p.proname <> ALL(allowlist)
          AND ( has_function_privilege('anon', p.oid, 'EXECUTE')
             OR has_function_privilege('authenticated', p.oid, 'EXECUTE') )
    LOOP
        EXECUTE format('REVOKE EXECUTE ON FUNCTION %s FROM PUBLIC, anon, authenticated', r.sig);
        EXECUTE format('GRANT  EXECUTE ON FUNCTION %s TO service_role', r.sig);
        RAISE NOTICE 'hotfix FIX-P1-05: locked %', r.sig;
    END LOOP;
END $$;

COMMIT;

-- Verify: this SELECT must return ZERO rows after the fix.
SELECT p.oid::regprocedure AS still_anon_executable
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public'
  AND p.prosecdef
  AND p.proname <> 'get_or_create_executor'
  AND ( has_function_privilege('anon', p.oid, 'EXECUTE')
     OR has_function_privilege('authenticated', p.oid, 'EXECUTE') );

-- For reference, the functions this typically REVOKEs (signatures may vary):
--   resolve_dispute(uuid, character varying, text, numeric, character varying)
--   escalate_to_arbitration(uuid)
--   assign_task_to_executor(uuid, uuid, text, text)
--   complete_submission(uuid, text, text, text, integer)
--   expire_overdue_tasks()
--   fund_escrow(uuid, character varying)
--   release_partial_payment(uuid, uuid, character varying)
--   release_final_payment(uuid, character varying)
--   refund_escrow(uuid, text, character varying)
--   recalculate_executor_reputation(uuid)
--   award_badge(uuid, badge_type, character varying, text, task_category)
--   award_tier_badge(uuid, executor_tier)
--   check_milestone_badges(uuid)
--   create_reputation_snapshot(date, character varying)
--   (plus any other SECURITY DEFINER function the loop discovers).
