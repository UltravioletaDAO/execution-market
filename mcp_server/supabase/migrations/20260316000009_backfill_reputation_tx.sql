-- ============================================================================
-- MIGRATION: Backfill reputation_tx in feedback_documents from payment_events
-- Date: 2026-03-16
-- Description:
--   1. Ensure all required columns exist on tables created dynamically by the app.
--   2. Backfill feedback_documents.reputation_tx from payment_events where
--      the on-chain TX hash was logged but never written back to the feedback doc.
--   3. Reset stale worker->agent rating state so workers can re-rate.
--
-- Safe to run multiple times (idempotent).
-- Designed for Supabase SQL Editor (no CONCURRENTLY, no multi-statement transactions).
-- ============================================================================

-- ============================================================================
-- PART 1: Ensure tables and columns exist
--
-- These tables are created dynamically by the app (best-effort inserts).
-- CREATE TABLE IF NOT EXISTS handles the case where they don't exist yet.
-- ALTER TABLE ADD COLUMN IF NOT EXISTS handles the case where the table
-- exists but is missing columns added later.
-- ============================================================================

CREATE TABLE IF NOT EXISTS feedback_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID,
    feedback_type TEXT,
    feedback_uri TEXT,
    feedback_hash TEXT,
    score INTEGER,
    reputation_tx TEXT,
    document_json JSONB,
    prepare_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- If the table already existed, ensure all columns are present
ALTER TABLE feedback_documents ADD COLUMN IF NOT EXISTS feedback_uri TEXT;
ALTER TABLE feedback_documents ADD COLUMN IF NOT EXISTS feedback_hash TEXT;
ALTER TABLE feedback_documents ADD COLUMN IF NOT EXISTS reputation_tx TEXT;
ALTER TABLE feedback_documents ADD COLUMN IF NOT EXISTS document_json JSONB;
ALTER TABLE feedback_documents ADD COLUMN IF NOT EXISTS prepare_id TEXT;

CREATE TABLE IF NOT EXISTS payment_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID,
    event_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    tx_hash TEXT,
    from_address TEXT,
    to_address TEXT,
    amount_usdc NUMERIC(18, 6),
    network TEXT,
    token TEXT DEFAULT 'USDC',
    error TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ratings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    executor_id UUID,
    task_id UUID,
    rater_id TEXT,
    rater_type TEXT,
    rating INTEGER,
    stars NUMERIC(3, 1),
    comment TEXT,
    task_value_usdc NUMERIC(10, 2),
    is_public BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(executor_id, task_id, rater_type)
);

-- Indexes for the joins below
CREATE INDEX IF NOT EXISTS idx_feedback_documents_task_type
    ON feedback_documents(task_id, feedback_type);
CREATE INDEX IF NOT EXISTS idx_payment_events_event_type
    ON payment_events(event_type);
CREATE INDEX IF NOT EXISTS idx_payment_events_task_event
    ON payment_events(task_id, event_type);
CREATE INDEX IF NOT EXISTS idx_ratings_task_rater_type
    ON ratings(task_id, rater_type);

-- ============================================================================
-- PART 2: Backfill feedback_documents.reputation_tx from payment_events
--
-- Logic: For each feedback_documents row where reputation_tx IS NULL or empty,
-- find the corresponding successful payment_event with a TX hash:
--   - feedback_type='worker_rating' matches event_type='reputation_agent_rates_worker'
--   - feedback_type='agent_rating'  matches event_type='reputation_worker_rates_agent'
-- ============================================================================

-- 2a: Backfill worker_rating (agent rates worker)
UPDATE feedback_documents fd
SET reputation_tx = pe.tx_hash
FROM (
    SELECT DISTINCT ON (task_id)
        task_id,
        tx_hash
    FROM payment_events
    WHERE event_type = 'reputation_agent_rates_worker'
      AND status = 'success'
      AND tx_hash IS NOT NULL
      AND tx_hash != ''
    ORDER BY task_id, created_at DESC
) pe
WHERE fd.task_id = pe.task_id
  AND fd.feedback_type = 'worker_rating'
  AND (fd.reputation_tx IS NULL OR fd.reputation_tx = '');

-- 2b: Backfill agent_rating (worker rates agent)
UPDATE feedback_documents fd
SET reputation_tx = pe.tx_hash
FROM (
    SELECT DISTINCT ON (task_id)
        task_id,
        tx_hash
    FROM payment_events
    WHERE event_type = 'reputation_worker_rates_agent'
      AND status = 'success'
      AND tx_hash IS NOT NULL
      AND tx_hash != ''
    ORDER BY task_id, created_at DESC
) pe
WHERE fd.task_id = pe.task_id
  AND fd.feedback_type = 'agent_rating'
  AND (fd.reputation_tx IS NULL OR fd.reputation_tx = '');

-- NOTE: submissions table does NOT have a reputation_tx column.
-- Reputation TX is stored only in feedback_documents and payment_events.

-- ============================================================================
-- PART 3: Reset incomplete worker->agent ratings so workers can re-rate
--
-- The worker->agent flow uses feedback_documents.prepare_id for the
-- prepare -> sign -> confirm cycle. If the flow failed mid-way (e.g.,
-- SignedTransaction error), the prepare_id is set but reputation_tx is NULL.
-- This blocks re-rating because the system sees an existing row.
--
-- Fix: Clear the stale prepare_id so the prepare-feedback endpoint
-- can issue a new one.
-- ============================================================================

-- 3a: Clear stale prepare_id where worker never completed the TX
UPDATE feedback_documents
SET prepare_id = NULL
WHERE feedback_type = 'agent_rating'
  AND prepare_id IS NOT NULL
  AND (reputation_tx IS NULL OR reputation_tx = '');

-- 3b: For tasks that have a worker_rating (agent rated worker) but NO
-- agent_rating feedback_documents row at all, insert a placeholder so
-- the worker can use prepare-feedback.
INSERT INTO feedback_documents (task_id, feedback_type, feedback_uri, feedback_hash, score, reputation_tx, created_at)
SELECT
    fd.task_id,
    'agent_rating',
    '',
    '',
    0,
    NULL,
    NOW()
FROM feedback_documents fd
LEFT JOIN feedback_documents fd2
    ON fd.task_id = fd2.task_id
    AND fd2.feedback_type = 'agent_rating'
WHERE fd.feedback_type = 'worker_rating'
  AND fd2.task_id IS NULL
ON CONFLICT DO NOTHING;

-- ============================================================================
-- PART 4: Diagnostic queries (uncomment to run manually)
-- ============================================================================

/*
-- 4a: Count of feedback_documents with/without reputation_tx after backfill
SELECT
    feedback_type,
    COUNT(*) AS total,
    COUNT(reputation_tx) FILTER (WHERE reputation_tx IS NOT NULL AND reputation_tx != '') AS has_tx,
    COUNT(*) FILTER (WHERE reputation_tx IS NULL OR reputation_tx = '') AS missing_tx
FROM feedback_documents
GROUP BY feedback_type
ORDER BY feedback_type;

-- 4b: Count of payment_events by reputation event type
SELECT
    event_type,
    status,
    COUNT(*) AS total,
    COUNT(tx_hash) FILTER (WHERE tx_hash IS NOT NULL AND tx_hash != '') AS has_tx
FROM payment_events
WHERE event_type LIKE 'reputation_%'
GROUP BY event_type, status
ORDER BY event_type, status;

-- 4c: Tasks still missing worker->agent rating after cleanup
SELECT
    fd.task_id,
    fd.reputation_tx AS agent_rates_worker_tx,
    t.title,
    t.completed_at,
    e.display_name AS worker_name
FROM feedback_documents fd
LEFT JOIN feedback_documents fd2
    ON fd.task_id = fd2.task_id AND fd2.feedback_type = 'agent_rating'
LEFT JOIN tasks t ON fd.task_id = t.id
LEFT JOIN executors e ON t.executor_id = e.id
WHERE fd.feedback_type = 'worker_rating'
  AND (fd2.reputation_tx IS NULL OR fd2.reputation_tx = '')
ORDER BY fd.created_at DESC;
*/
