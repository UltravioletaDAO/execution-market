-- Migration 113: Lock down ALL anon-executable SECURITY DEFINER RPCs (FIX-P1-05).
-- Security audit 2026-06-09. Completes the partial lockdown of migration 092.
-- Applied to production: pending.
--
-- ROOT CAUSE
-- ----------
-- PostgreSQL grants EXECUTE to PUBLIC by default on every new function, and
-- Supabase anon/authenticated INHERIT from PUBLIC. Migration 092 documented
-- this (092:99-102) but only revoked 15 functions by HAND-ENUMERATING GRANT
-- statements — which can never see the implicit PUBLIC default grant. It also
-- falsely asserted (092:83-86) that assign_task_to_executor, complete_submission,
-- expire_overdue_tasks were "service_role ONLY" and escalate_to_arbitration was
-- "default-deny". An explicit GRANT TO service_role does NOT remove PUBLIC's
-- default grant, so ~14 SECURITY DEFINER money/state RPCs stayed anon-executable
-- via POST /rest/v1/rpc/<fn>, bypassing RLS (run as owner). See FIX-P1-05.
--
-- APPROACH
-- --------
-- Do NOT hand-enumerate (that is how 092 missed these). Loop over pg_proc and
-- REVOKE EXECUTE FROM PUBLIC, anon, authenticated for EVERY SECURITY DEFINER
-- function in schema public that anon OR authenticated can currently execute,
-- except an explicit allowlist of intentionally-anon SECURITY DEFINER funcs.
-- Then GRANT EXECUTE TO service_role. Idempotent and safe to re-run.

BEGIN;

DO $$
DECLARE
    r RECORD;
    -- Intentionally anon/authenticated-callable SECURITY DEFINER functions.
    -- get_or_create_executor: re-granted to anon by migration 097 for login.
    --   (Its DB-001 account-rebind concern is handled in migration 111 / FIX-P0-02,
    --   which ALSO revokes it from anon — so by the time both ship it will no longer
    --   be anon-executable. The allowlist here keeps THIS migration from depending on
    --   the apply-order of 111: if 111 ran first, the loop already skips it; if 113
    --   runs first, the allowlist prevents a double-handling. Either order is safe.)
    -- get_tasks_near_location: app-defined SECURITY DEFINER read-only location
    -- search, intentionally anon (matches the secondary-tree allowlist). Not a
    -- money/state RPC — out of scope for FIX-P1-05.
    allowlist text[] := ARRAY['get_or_create_executor', 'get_tasks_near_location', 'current_executor_ids'];
BEGIN
    FOR r IN
        SELECT p.oid::regprocedure AS sig, p.proname AS name
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.prosecdef                                   -- SECURITY DEFINER only
          AND p.proname <> ALL(allowlist)
          -- Exclude extension-owned functions (PostGIS st_*, pgcrypto, etc.).
          -- They are not app RPCs, are not a security risk, and are often not
          -- revocable by the migration role (owned by the extension installer).
          AND NOT EXISTS (
                SELECT 1 FROM pg_depend d
                WHERE d.objid = p.oid AND d.deptype = 'e'
              )
          AND (
                has_function_privilege('anon', p.oid, 'EXECUTE')
                OR has_function_privilege('authenticated', p.oid, 'EXECUTE')
              )
    LOOP
        EXECUTE format(
            'REVOKE EXECUTE ON FUNCTION %s FROM PUBLIC, anon, authenticated', r.sig);
        EXECUTE format(
            'GRANT EXECUTE ON FUNCTION %s TO service_role', r.sig);
        RAISE NOTICE '113: locked down %', r.sig;
    END LOOP;
END $$;

-- ---------------------------------------------------------------------------
-- Correct the false comments left by migration 092 (092:83-86).
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    r RECORD;
    msg constant text :=
        'REVOKED from PUBLIC/anon/authenticated 2026-06-09 (FIX-P1-05, migration 113). '
        'Service_role only. Migration 092 left this anon-executable via the default PUBLIC grant.';
BEGIN
    FOR r IN
        SELECT p.oid::regprocedure AS sig
        FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public' AND p.prosecdef
          AND p.proname = ANY(ARRAY[
              'resolve_dispute','escalate_to_arbitration','assign_task_to_executor',
              'complete_submission','expire_overdue_tasks','fund_escrow',
              'release_partial_payment','release_final_payment','refund_escrow',
              'recalculate_executor_reputation','award_badge','award_tier_badge',
              'check_milestone_badges','create_reputation_snapshot'])
    LOOP
        EXECUTE format('COMMENT ON FUNCTION %s IS %L', r.sig, msg);
    END LOOP;
END $$;

-- ---------------------------------------------------------------------------
-- ASSERTION: fail the migration if ANY non-allowlisted SECURITY DEFINER
-- function in public is still anon- or authenticated-executable.
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    leaked text;
    -- get_tasks_near_location: app-defined SECURITY DEFINER read-only location
    -- search, intentionally anon (matches the secondary-tree allowlist). Not a
    -- money/state RPC — out of scope for FIX-P1-05.
    allowlist text[] := ARRAY['get_or_create_executor', 'get_tasks_near_location', 'current_executor_ids'];
BEGIN
    SELECT string_agg(p.oid::regprocedure::text, ', ')
    INTO leaked
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.prosecdef
      AND p.proname <> ALL(allowlist)
      AND NOT EXISTS (                                       -- skip extension funcs
            SELECT 1 FROM pg_depend d
            WHERE d.objid = p.oid AND d.deptype = 'e'
          )
      AND (
            has_function_privilege('anon', p.oid, 'EXECUTE')
            OR has_function_privilege('authenticated', p.oid, 'EXECUTE')
          );

    IF leaked IS NOT NULL THEN
        RAISE EXCEPTION
            '113 ASSERTION FAILED: SECURITY DEFINER funcs still anon/authenticated-executable: %',
            leaked;
    END IF;
    RAISE NOTICE '113: assertion passed — no non-allowlisted anon-executable SECURITY DEFINER funcs remain';
END $$;

COMMIT;

-- ===========================================================================
-- ROLLBACK (manual — NOT recommended, re-opens the anon RLS bypass)
-- ===========================================================================
-- BEGIN;
-- -- Restore default PUBLIC EXECUTE on each locked-down function, e.g.:
-- -- GRANT EXECUTE ON FUNCTION public.resolve_dispute(uuid, character varying, text, numeric, character varying) TO PUBLIC;
-- -- GRANT EXECUTE ON FUNCTION public.assign_task_to_executor(uuid, uuid, text, text) TO PUBLIC;
-- -- ... (repeat per function). There is no behavioural reason to do this; the
-- -- backend uses service_role and is unaffected.
-- COMMIT;
