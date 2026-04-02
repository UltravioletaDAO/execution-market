-- Migration 083: Enable RLS on admin_actions_log + hide spatial_ref_sys from PostgREST
-- Resolves 2 Supabase Security Advisor errors (2026-04-01)
--
-- 1. admin_actions_log — created in 076 without RLS. Admin-only table.
-- 2. spatial_ref_sys — PostGIS extension table. Cannot ALTER (not owner).
--    Fix: move to 'extensions' schema so PostgREST doesn't expose it.
--
-- Idempotent — safe to re-run.

-- ============================================================================
-- 1. admin_actions_log: enable RLS, service-role-only access
-- ============================================================================
ALTER TABLE admin_actions_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "admin_actions_log_service_all"
  ON admin_actions_log
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

-- ============================================================================
-- 2. spatial_ref_sys: revoke access from API roles
-- ============================================================================
-- PostGIS extension owns this table — cannot ALTER or SET SCHEMA.
-- Revoking access from anon/authenticated makes it invisible to PostgREST,
-- which silences the Security Advisor linter.
REVOKE ALL ON public.spatial_ref_sys FROM anon, authenticated;
