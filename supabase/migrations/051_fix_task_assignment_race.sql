-- Migration 051: Fix Task Assignment Race Condition
-- Source: DB Optimization Audit 2026-03-15 (Phase 2, Task 2.2)
-- Adds a partial UNIQUE index that prevents two executors from being
-- assigned to the same task simultaneously. The existing assign_task_to_executor()
-- already uses SELECT ... FOR UPDATE, but this index adds a DB-level guarantee
-- even if the function is bypassed or a new code path is introduced.
-- Applied to production: pending.

-- Ensure only one executor can be assigned to an active task.
-- A task in accepted/in_progress/submitted/verifying can have at most
-- one non-null executor_id. Completed/cancelled tasks are excluded to
-- allow historical data (e.g., re-assignment after cancellation).
CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_single_active_executor
    ON tasks(id)
    WHERE executor_id IS NOT NULL
      AND status IN ('accepted', 'in_progress', 'submitted', 'verifying');
