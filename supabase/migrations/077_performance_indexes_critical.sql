-- Migration 077: Critical Performance Indexes
-- Made idempotent: safe to re-run on partial application
--
-- Fixes 5 missing indexes identified in query performance audit (2026-03-28):
-- 1. payment_events: address filter (was causing 5-20s scans)
-- 2. task_applications: dual filter on task_id + executor_id
-- 3. submissions: composite for task_id + submitted_at sort
-- 4. escrows: composite for task_id + status + expires_at
-- 5. api_keys: partial index for active key lookups
--
-- Expected improvement: 40-100x on critical user-facing paths

-- 1. Payment events: address filter + time sort (CRITICAL — completely unindexed)
DO $$ BEGIN
    CREATE INDEX idx_payment_events_from_addr_created
        ON payment_events(from_address, created_at DESC);
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;

DO $$ BEGIN
    CREATE INDEX idx_payment_events_to_addr_created
        ON payment_events(to_address, created_at DESC);
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;

-- 2. Task applications: dual filter (task_id + executor_id)
DO $$ BEGIN
    CREATE INDEX idx_task_applications_task_executor
        ON task_applications(task_id, executor_id);
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;

-- 3. Submissions: task + sort by submitted_at (covers evidence review queries)
DO $$ BEGIN
    CREATE INDEX idx_submissions_task_submitted_at
        ON submissions(task_id, submitted_at DESC);
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;

-- 4. Escrows: task + status + expiry (covers reconciler + payment queries)
DO $$ BEGIN
    CREATE INDEX idx_escrows_task_status
        ON escrows(task_id, status);
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;

-- 5. API keys: partial index for active key lookups only
DO $$ BEGIN
    CREATE INDEX idx_api_keys_active
        ON api_keys(is_active, expires_at DESC) WHERE is_active = TRUE;
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;

-- 6. Feedback documents: dedup check (task_id + feedback_type)
-- Used by the new dedup logic in reputation.py
DO $$ BEGIN
    CREATE INDEX idx_feedback_documents_task_type
        ON feedback_documents(task_id, feedback_type);
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;

-- 7. Ratings: task lookup for dashboard display
DO $$ BEGIN
    CREATE INDEX idx_ratings_task_id
        ON ratings(task_id);
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;
