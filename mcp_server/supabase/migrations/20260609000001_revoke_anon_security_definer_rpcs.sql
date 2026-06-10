-- Migration 20260609000001: Revoke anon/authenticated EXECUTE on SECURITY DEFINER
-- RPCs in the secondary (mcp_server) migration tree.
-- Source: Security Audit 2026-06-09, findings FIX-P0-02 + FIX-P1-05.
--
-- WHY THIS TREE TOO
-- -----------------
-- 20260125000003_rpc_functions.sql:678-684 re-grants EXECUTE to anon/authenticated
-- on several SECURITY DEFINER state/identity RPCs (get_or_create_executor,
-- get_tasks_near_location, update_reputation, get_agent_stats,
-- get_executor_dashboard, assign_task, complete_task). If THIS tree is the one
-- applied to a given database, those grants re-open exactly the anon-executable
-- SECURITY DEFINER RLS-bypass that the primary tree's migrations 111/113 close.
-- This migration applies the same lockdown here so neither tree can leave a
-- money/state RPC anon-executable.
--
-- APPROACH (mirrors primary-tree migration 113)
-- ---------------------------------------------
-- Loop over pg_proc and REVOKE EXECUTE FROM PUBLIC, anon, authenticated for
-- EVERY SECURITY DEFINER function in schema public that anon OR authenticated
-- can currently execute, except the read-only allowlist below. Then GRANT to
-- service_role. Signature-agnostic, so it works regardless of overload drift
-- between the two trees. Idempotent and safe to re-run.
--
-- NOTE: get_or_create_executor is NOT allowlisted here — per FIX-P0-02 it must
-- be revoked from anon (browser onboarding routes through the backend
-- service_role path). The intentionally-anon read-only RPCs are allowlisted.

BEGIN;

DO $$
DECLARE
    r RECORD;
    -- Read-only, public-data RPCs that are deliberately anon-callable.
    -- (These are SECURITY DEFINER in this tree but only read public task data.)
    allowlist text[] := ARRAY['get_tasks_near_location', 'current_executor_ids'];
BEGIN
    FOR r IN
        SELECT p.oid::regprocedure AS sig
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.prosecdef
          AND p.proname <> ALL(allowlist)
          AND NOT EXISTS (SELECT 1 FROM pg_depend d   -- skip extension funcs (PostGIS st_*, etc.)
                          WHERE d.objid = p.oid AND d.deptype = 'e')
          AND ( has_function_privilege('anon', p.oid, 'EXECUTE')
             OR has_function_privilege('authenticated', p.oid, 'EXECUTE') )
    LOOP
        EXECUTE format('REVOKE EXECUTE ON FUNCTION %s FROM PUBLIC, anon, authenticated', r.sig);
        EXECUTE format('GRANT  EXECUTE ON FUNCTION %s TO service_role', r.sig);
        RAISE NOTICE '20260609000001: locked down %', r.sig;
    END LOOP;
END $$;

-- Assertion: no non-allowlisted SECURITY DEFINER function in public stays
-- anon/authenticated-executable.
DO $$
DECLARE
    leaked text;
    allowlist text[] := ARRAY['get_tasks_near_location', 'current_executor_ids'];
BEGIN
    SELECT string_agg(p.oid::regprocedure::text, ', ')
    INTO leaked
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.prosecdef
      AND p.proname <> ALL(allowlist)
      AND NOT EXISTS (SELECT 1 FROM pg_depend d   -- skip extension funcs (PostGIS st_*, etc.)
                      WHERE d.objid = p.oid AND d.deptype = 'e')
      AND ( has_function_privilege('anon', p.oid, 'EXECUTE')
         OR has_function_privilege('authenticated', p.oid, 'EXECUTE') );
    IF leaked IS NOT NULL THEN
        RAISE EXCEPTION
            '20260609000001 ASSERTION FAILED: SECURITY DEFINER funcs still anon-executable: %',
            leaked;
    END IF;
    RAISE NOTICE '20260609000001: assertion passed';
END $$;

COMMIT;
