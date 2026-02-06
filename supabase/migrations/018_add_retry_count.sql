-- Migration 018: Add retry_count to submissions for payment retry tracking
-- Tracks how many times the payment retry job has attempted settlement

ALTER TABLE submissions ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;

COMMENT ON COLUMN submissions.retry_count IS 'Number of payment settlement retry attempts';
