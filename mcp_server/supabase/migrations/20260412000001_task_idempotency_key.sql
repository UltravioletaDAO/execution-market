-- Add idempotency_key column to tasks table for client-side deduplication.
-- When an agent retries task creation (e.g. after a 429), the server detects
-- the duplicate key and returns the original task instead of creating a second one.

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(255);

-- Unique partial index: enforce uniqueness only for non-null keys.
-- Old tasks without a key are unaffected.
CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_idempotency_key
  ON tasks (idempotency_key) WHERE idempotency_key IS NOT NULL;
