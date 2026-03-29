-- ============================================================================
-- Migration 079: Add assigned_at column to tasks table
-- ============================================================================
-- The code (supabase_client.py, agent_executor_tools.py, tasks.py) writes to
-- tasks.assigned_at when assigning workers to tasks. The original schema (001)
-- did NOT include this column (accepted_at also doesn't exist).
--
-- References:
--   supabase_client.py:1388  — assign_task() writes assigned_at
--   agent_executor_tools.py:366 — em_accept_agent_task writes assigned_at
--   tasks.py:3007,3113,3270,3386 — assignment rollback sets assigned_at=NULL
-- ============================================================================

-- 1. Add the column (nullable TIMESTAMPTZ)
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ;

-- 2. Index for querying recently assigned tasks
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_at
  ON tasks(assigned_at DESC)
  WHERE assigned_at IS NOT NULL;

-- 3. Refresh PostgREST schema cache (fixes "metadata missing" warning)
NOTIFY pgrst, 'reload schema';
