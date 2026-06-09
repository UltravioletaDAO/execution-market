-- Migration 117: Lock down the anon read surface on v_orphaned_payments
-- (Security Audit 2026-06-09, Phase 2.4 — anon read surface that is a DB grant).
-- Applied to production: pending.
--
-- ROOT CAUSE
-- ----------
-- Migration 017 created the operational view v_orphaned_payments (submissions
-- accepted/approved with no payment_tx — i.e. stuck/orphaned payouts) and the
-- count function get_orphaned_payment_count(), and granted SELECT/EXECUTE to
-- anon, authenticated, AND service_role:
--   GRANT SELECT ON v_orphaned_payments TO anon, authenticated, service_role;
--   GRANT EXECUTE ON FUNCTION get_orphaned_payment_count() TO anon, authenticated, service_role;
-- The view leaks, to any anonymous caller, the financial/operational state of
-- the platform: submission_id, task_id, executor_id, agent_id, bounty_usd,
-- payment_tx status, and hours-since-verdict for every stuck payout. This is an
-- information-disclosure surface that exists purely as a DB grant — it is only
-- needed by the service_role backend health checks / alerting.
--
-- FIX
-- ---
-- Revoke anon (and authenticated) access to both objects; keep service_role.
-- Idempotent: REVOKE of a non-granted privilege is a no-op.

BEGIN;

DO $$
BEGIN
    EXECUTE 'REVOKE SELECT ON v_orphaned_payments FROM anon, authenticated';
    EXECUTE 'GRANT SELECT ON v_orphaned_payments TO service_role';
    RAISE NOTICE '117: revoked anon/authenticated SELECT on v_orphaned_payments';
EXCEPTION WHEN undefined_table OR undefined_object THEN
    RAISE NOTICE '117: SKIPPED v_orphaned_payments (view does not exist in this database)';
END;
$$;

DO $$
BEGIN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION get_orphaned_payment_count() FROM PUBLIC, anon, authenticated';
    EXECUTE 'GRANT EXECUTE ON FUNCTION get_orphaned_payment_count() TO service_role';
    RAISE NOTICE '117: revoked anon/authenticated EXECUTE on get_orphaned_payment_count()';
EXCEPTION WHEN undefined_function OR undefined_object THEN
    RAISE NOTICE '117: SKIPPED get_orphaned_payment_count() (function does not exist in this database)';
END;
$$;

COMMIT;

-- ===========================================================================
-- VERIFICATION (expect f, f, t)
-- ===========================================================================
-- SELECT has_table_privilege('anon',          'public.v_orphaned_payments', 'SELECT'); -- expect f
-- SELECT has_table_privilege('authenticated', 'public.v_orphaned_payments', 'SELECT'); -- expect f
-- SELECT has_table_privilege('service_role',  'public.v_orphaned_payments', 'SELECT'); -- expect t
