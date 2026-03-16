-- Migration 036: H2A RLS Policies
-- Protects human_wallet PII from unauthorized access
-- Applied: 2026-02-18
--
-- NOTE: PostgreSQL doesn't support column-level RLS natively.
-- Primary PII protection is at the API layer (h2a.py strips human_wallet
-- and human_user_id from public responses).
-- This migration adds a security view as defense-in-depth.

-- ============================================================================
-- 1. Create a public-safe view for H2A tasks (no PII columns)
-- ============================================================================
CREATE OR REPLACE VIEW h2a_tasks_public AS
SELECT
  id,
  agent_id,
  title,
  instructions,
  category,
  bounty_usd,
  payment_token,
  payment_network,
  deadline,
  status,
  publisher_type,
  target_executor_type,
  required_capabilities,
  verification_mode,
  min_reputation,
  required_roles,
  max_executors,
  executor_id,
  created_at,
  updated_at
FROM tasks
WHERE publisher_type = 'human'
  AND status = 'published';

COMMENT ON VIEW h2a_tasks_public IS 'Public view of H2A tasks — excludes human_wallet and human_user_id PII';

-- ============================================================================
-- 2. Grant read access to anon and authenticated roles
-- ============================================================================
GRANT SELECT ON h2a_tasks_public TO anon;
GRANT SELECT ON h2a_tasks_public TO authenticated;
