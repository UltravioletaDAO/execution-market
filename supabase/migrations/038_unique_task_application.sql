-- Migration 038: Ensure unique constraint on task_applications(task_id, executor_id)
--
-- The constraint was defined in 001_initial_schema.sql but may not exist in live DB
-- if schema diverged. This migration is idempotent: adds it only if missing.
-- Prevents race condition where two agents apply simultaneously and both pass the
-- read-check-then-insert without seeing each other's application.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'task_applications_unique'
    ) THEN
        ALTER TABLE task_applications
        ADD CONSTRAINT task_applications_unique UNIQUE(task_id, executor_id);
    END IF;
END
$$;
