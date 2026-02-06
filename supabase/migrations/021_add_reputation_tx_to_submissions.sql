-- Migration 021: Add reputation_tx to submissions for ERC-8004 feedback tracking
-- Stores the on-chain transaction hash when an agent rates a worker via ERC-8004.

ALTER TABLE submissions ADD COLUMN IF NOT EXISTS reputation_tx TEXT;

COMMENT ON COLUMN submissions.reputation_tx IS 'ERC-8004 Reputation Registry feedback tx hash (set after agent rates worker)';

-- Index for finding submissions with reputation feedback
CREATE INDEX IF NOT EXISTS idx_submissions_reputation_tx ON submissions(reputation_tx) WHERE reputation_tx IS NOT NULL;
