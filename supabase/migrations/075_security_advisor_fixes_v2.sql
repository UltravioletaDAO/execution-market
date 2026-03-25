-- Migration 075: Security Advisor Fixes v2
-- Resolves remaining 2 Supabase Security Advisor errors (2026-03-25)
--
-- 1. public.applications view — SECURITY DEFINER (bypasses RLS on task_applications)
-- 2. public.spatial_ref_sys — PostGIS table without RLS
--
-- This migration is idempotent — safe to re-run.

-- ============================================================================
-- 1. Fix applications view: change from SECURITY DEFINER to SECURITY INVOKER
-- ============================================================================
-- The view was created in migration 047 without specifying security mode.
-- PostgreSQL defaults views to SECURITY DEFINER, which means queries through
-- the view run with the view owner's permissions (bypassing RLS on
-- task_applications). Setting security_invoker = true makes it respect the
-- calling user's permissions and RLS policies.
ALTER VIEW applications SET (security_invoker = true);

-- ============================================================================
-- 2. Fix spatial_ref_sys: enable RLS with permissive read policy
-- ============================================================================
-- spatial_ref_sys is a PostGIS extension table containing coordinate system
-- definitions. It's read-only reference data — safe to allow all reads.
-- Migration 043 skipped this ("cannot ALTER"), but the Supabase SQL Editor
-- runs as a privileged role that CAN alter extension tables.
ALTER TABLE IF EXISTS spatial_ref_sys ENABLE ROW LEVEL SECURITY;

-- Allow anyone to read coordinate system definitions (public reference data)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'spatial_ref_sys' AND policyname = 'spatial_ref_sys_read_all'
    ) THEN
        EXECUTE 'CREATE POLICY "spatial_ref_sys_read_all" ON spatial_ref_sys FOR SELECT USING (true)';
    END IF;
END $$;
