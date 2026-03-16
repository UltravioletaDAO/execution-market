-- Migration: Add reviewed_at column to applications
-- Fix: column "reviewed_at" of relation "applications" does not exist (error 42703)
-- The column is referenced by apply_to_task RPC and assignment triggers but was
-- missing from the production table.
-- Note: "applications" is a VIEW over "task_applications" (the real table).

ALTER TABLE task_applications
  ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;

-- Recreate the view so it picks up the new column
DROP VIEW IF EXISTS applications;
CREATE VIEW applications AS SELECT * FROM task_applications;
