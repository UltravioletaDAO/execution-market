-- Migration 114: Defense-in-depth for payment_events (FIX-P1-03)
-- Source: Security Audit 2026-06-09, finding FIX-P1-03.
-- The REST endpoint GET /api/v1/payments/events previously read this table via
-- the service-role client with no ownership check, bypassing RLS. The code fix
-- (mcp_server/api/routers/workers.py — owned by the API work-stream) adds
-- ownership/internal-auth enforcement; this migration ensures the table can
-- never be read or written by anon/authenticated roles except through the
-- migration-045 own-tasks SELECT policy. RLS remains ENABLED (migration 027).
--
-- Idempotent: ENABLE RLS / REVOKE / GRANT are all re-runnable.
-- Applied to production: pending.

BEGIN;

-- Ensure RLS is on (idempotent).
ALTER TABLE payment_events ENABLE ROW LEVEL SECURITY;

-- Remove any direct table grants to anon/authenticated; RLS policies (045) are
-- the only sanctioned read path for non-service roles. anon gets nothing.
REVOKE ALL ON TABLE payment_events FROM anon;
REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE payment_events FROM authenticated;

-- Re-grant ONLY the SELECT needed for the migration-045 own-tasks policy to
-- function for authenticated workers (mobile timeline read).
GRANT SELECT ON TABLE payment_events TO authenticated;

COMMENT ON TABLE payment_events IS
    'Audit trail for payment ops. Non-service reads MUST go through the '
    'migration-045 own-tasks RLS policy. REST reads are ownership-checked in '
    'api/routers/workers.py:get_payment_events (FIX-P1-03, migration 114).';

COMMIT;

-- ===========================================================================
-- VERIFICATION (expect: anon has no privilege; authenticated has SELECT only)
-- ===========================================================================
-- SELECT has_table_privilege('anon',          'public.payment_events', 'SELECT') AS anon_select;          -- expect f
-- SELECT has_table_privilege('anon',          'public.payment_events', 'INSERT') AS anon_insert;          -- expect f
-- SELECT has_table_privilege('authenticated', 'public.payment_events', 'SELECT') AS authed_select;        -- expect t
-- SELECT has_table_privilege('authenticated', 'public.payment_events', 'INSERT') AS authed_insert;        -- expect f
