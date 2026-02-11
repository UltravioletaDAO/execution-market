-- Migration 029: Feedback Documents
-- Stores references to S3-hosted feedback documents for ERC-8004 reputation.
-- The actual JSON lives on S3; this table provides fast lookups by task_id.

CREATE TABLE IF NOT EXISTS feedback_documents (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    task_id     UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('worker_rating', 'agent_rating', 'rejection')),
    feedback_uri  TEXT NOT NULL,
    feedback_hash TEXT NOT NULL,  -- keccak256 hex (0x-prefixed), stored on-chain
    score       INTEGER NOT NULL CHECK (score >= 0 AND score <= 100),
    reputation_tx TEXT,           -- on-chain reputation tx hash
    created_at  TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Index for fast lookups by task_id
CREATE INDEX IF NOT EXISTS idx_feedback_documents_task_id ON feedback_documents(task_id);

-- Index for lookups by feedback_hash (verify on-chain data)
CREATE INDEX IF NOT EXISTS idx_feedback_documents_hash ON feedback_documents(feedback_hash);

-- RLS: public read (feedback is on-chain, no secrets), service-only write
ALTER TABLE feedback_documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "feedback_documents_public_read"
    ON feedback_documents FOR SELECT
    USING (true);

CREATE POLICY "feedback_documents_service_insert"
    ON feedback_documents FOR INSERT
    WITH CHECK (true);
