-- ============================================================================
-- Migration 079: Add assigned_at column to tasks table
-- ============================================================================
-- The code (supabase_client.py, agent_executor_tools.py, tasks.py) writes to
-- tasks.assigned_at when assigning workers to tasks. The original schema (001)
-- defined "accepted_at" for this purpose, but the application layer uses
-- "assigned_at" consistently.
--
-- This migration adds assigned_at alongside accepted_at so both old and new
-- code paths work. The accepted_at column is preserved for backward
-- compatibility; its data is copied into assigned_at for existing rows.
--
-- References:
--   supabase_client.py:1388  — assign_task() writes assigned_at
--   agent_executor_tools.py:366 — em_accept_agent_task writes assigned_at
--   tasks.py:3007,3113,3270,3386 — assignment rollback sets assigned_at=NULL
--   mcp_server/supabase/migrations/20260314000007 — parallel migration set
-- ============================================================================

-- 1. Add the column (nullable TIMESTAMPTZ, same type as accepted_at)
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ;

-- 2. Backfill from accepted_at for any existing assigned tasks
UPDATE tasks
SET assigned_at = accepted_at
WHERE accepted_at IS NOT NULL
  AND assigned_at IS NULL;

-- 3. Index for querying recently assigned tasks
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_at
  ON tasks(assigned_at DESC)
  WHERE assigned_at IS NOT NULL;

COMMENT ON COLUMN tasks.assigned_at IS
  'Timestamp when a worker was assigned to this task. '
  'Written by assign_task() in supabase_client.py. '
  'Equivalent to accepted_at (legacy name from migration 001).';
