-- Migration 119: Universal Hiring Matrix — enable 'robot' party
-- Part of MASTER_PLAN_UNIVERSAL_HIRING_MATRIX.md (Phase 0, Tasks 0.2 + 0.3)
--
-- The party taxonomy {human, agent, robot} must apply symmetrically to
-- publishers and executors. Migrations 031 + 034 introduced the columns but
-- their CHECK constraints only allow {human, agent}, which silently rejects
-- 'robot'. This migration widens the three constraints to include 'robot'.
-- Idempotent + non-destructive: only constraint definitions change, no data.

-- ============================================================================
-- 1. executors.executor_type — allow 'robot' (was: human|agent)
-- ============================================================================
ALTER TABLE executors DROP CONSTRAINT IF EXISTS executors_executor_type_check;
ALTER TABLE executors
  ADD CONSTRAINT executors_executor_type_check
  CHECK (executor_type IN ('human', 'agent', 'robot'));

-- ============================================================================
-- 2. tasks.target_executor_type — allow 'robot' (was: human|agent|any)
-- ============================================================================
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_target_executor_type_check;
ALTER TABLE tasks
  ADD CONSTRAINT tasks_target_executor_type_check
  CHECK (target_executor_type IN ('human', 'agent', 'robot', 'any'));

-- ============================================================================
-- 3. tasks.publisher_type — allow 'robot' (was: agent|human)
-- ============================================================================
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS chk_tasks_publisher_type;
ALTER TABLE tasks
  ADD CONSTRAINT chk_tasks_publisher_type
  CHECK (publisher_type IN ('agent', 'human', 'robot'));

-- ============================================================================
-- 4. Widen the capabilities index to include robot-targeted tasks
-- ============================================================================
DROP INDEX IF EXISTS idx_tasks_required_capabilities;
CREATE INDEX IF NOT EXISTS idx_tasks_required_capabilities
  ON tasks USING GIN(required_capabilities)
  WHERE target_executor_type IN ('agent', 'robot', 'any');
