-- Migration: Add missing columns to task_applications
-- Fix: columns "reviewed_at", "rejection_reason", etc. missing from production
-- (error 42703). These are referenced by apply_to_task RPC and assignment triggers.
-- Note: "applications" is a VIEW over "task_applications" (the real table).

ALTER TABLE task_applications
  ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS rejection_reason TEXT,
  ADD COLUMN IF NOT EXISTS proposed_rate_usd DECIMAL(10, 2),
  ADD COLUMN IF NOT EXISTS proposed_deadline TIMESTAMPTZ;

-- Recreate the view so it picks up all new columns
DROP VIEW IF EXISTS applications;
CREATE VIEW applications AS SELECT * FROM task_applications;
