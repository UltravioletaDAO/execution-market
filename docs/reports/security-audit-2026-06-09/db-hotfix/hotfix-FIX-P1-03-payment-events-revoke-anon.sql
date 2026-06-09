-- ===========================================================================
-- HOTFIX FIX-P1-03 (paste into the Supabase SQL editor) — defense-in-depth for
-- payment_events. Removes anon access entirely and restricts authenticated to
-- SELECT only (so the migration-045 own-tasks RLS policy is the only non-service
-- read path). RLS stays ENABLED. Idempotent.
--
-- NOTE: this is DEFENSE-IN-DEPTH only. The real fix is the ownership/internal-
-- auth enforcement in mcp_server/api/routers/workers.py:get_payment_events,
-- because that endpoint uses the service-role client (which bypasses RLS).
-- Mirrors supabase/migrations/114_payment_events_revoke_anon.sql.
-- ===========================================================================
DO $$
BEGIN
    EXECUTE 'ALTER TABLE payment_events ENABLE ROW LEVEL SECURITY';
    EXECUTE 'REVOKE ALL ON TABLE payment_events FROM anon';
    EXECUTE 'REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE payment_events FROM authenticated';
    EXECUTE 'GRANT SELECT ON TABLE payment_events TO authenticated';
    RAISE NOTICE 'HOTFIX FIX-P1-03: payment_events anon=none, authenticated=SELECT-only';
EXCEPTION WHEN undefined_table THEN
    RAISE NOTICE 'HOTFIX FIX-P1-03: payment_events table not found';
END $$;

-- Verify (expect: anon f/f, authenticated SELECT t / INSERT f):
SELECT
    has_table_privilege('anon',          'public.payment_events', 'SELECT') AS anon_select,
    has_table_privilege('anon',          'public.payment_events', 'INSERT') AS anon_insert,
    has_table_privilege('authenticated', 'public.payment_events', 'SELECT') AS authed_select,
    has_table_privilege('authenticated', 'public.payment_events', 'INSERT') AS authed_insert;
