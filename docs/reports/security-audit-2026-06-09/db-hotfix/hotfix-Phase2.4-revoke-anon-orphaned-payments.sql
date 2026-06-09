-- ===========================================================================
-- HOTFIX Phase 2.4 (paste into the Supabase SQL editor) — lock down the anon
-- read surface on v_orphaned_payments and get_orphaned_payment_count().
-- Migration 017 granted SELECT/EXECUTE to anon, leaking the platform's stuck-
-- payout operational/financial state to any anonymous caller. Only the
-- service_role backend health checks need it. Idempotent.
-- Mirrors supabase/migrations/117_revoke_anon_orphaned_payments.sql.
-- ===========================================================================
DO $$
BEGIN
    EXECUTE 'REVOKE SELECT ON v_orphaned_payments FROM anon, authenticated';
    EXECUTE 'GRANT SELECT ON v_orphaned_payments TO service_role';
    RAISE NOTICE 'HOTFIX 2.4: revoked anon/authenticated SELECT on v_orphaned_payments';
EXCEPTION WHEN undefined_table OR undefined_object THEN
    RAISE NOTICE 'HOTFIX 2.4: v_orphaned_payments not found';
END $$;

DO $$
BEGIN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION get_orphaned_payment_count() FROM PUBLIC, anon, authenticated';
    EXECUTE 'GRANT EXECUTE ON FUNCTION get_orphaned_payment_count() TO service_role';
    RAISE NOTICE 'HOTFIX 2.4: revoked anon/authenticated EXECUTE on get_orphaned_payment_count()';
EXCEPTION WHEN undefined_function OR undefined_object THEN
    RAISE NOTICE 'HOTFIX 2.4: get_orphaned_payment_count() not found';
END $$;

-- Verify (expect f, f, t):
SELECT
    has_table_privilege('anon',          'public.v_orphaned_payments', 'SELECT') AS anon_select,
    has_table_privilege('authenticated', 'public.v_orphaned_payments', 'SELECT') AS authed_select,
    has_table_privilege('service_role',  'public.v_orphaned_payments', 'SELECT') AS service_select;
