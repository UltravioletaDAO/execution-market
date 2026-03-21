-- Migration 049: Performance Indexes P1 + Payment Idempotency
-- Source: DB Optimization Audit 2026-03-15
-- Secondary indexes for leaderboard, ratings history, applications,
-- reputation log, plus a UNIQUE constraint to prevent duplicate payment events.
-- Applied to production: pending.

-- 1. Leaderboard — sort by reputation_score + tasks_completed (2 columns)
--    Before: 50-100ms (2 index scans)  |  After: 5-10ms (single composite)
CREATE INDEX IF NOT EXISTS idx_executors_reputation_tasks
    ON executors(reputation_score DESC, tasks_completed DESC);

-- 2. Worker rating history — executor's ratings ordered by time
--    Before: 100-500ms  |  After: 5-15ms
CREATE INDEX IF NOT EXISTS idx_ratings_executor_created
    ON ratings(executor_id, created_at DESC);

-- 3. Publisher review — all applications for a task, newest first
--    Before: 50-200ms  |  After: 5-10ms
CREATE INDEX IF NOT EXISTS idx_task_applications_task_created
    ON task_applications(task_id, created_at DESC);

-- 4. Reputation log — GROUP BY event_type for analytics
--    Future leaderboard queries will need this
CREATE INDEX IF NOT EXISTS idx_reputation_log_event_executor
    ON reputation_log(event_type, executor_id, created_at DESC);

-- 5. Payment idempotency — prevent duplicate payment events for same TX
--    Without this, a retry could insert the same settle event twice,
--    causing double-counted earnings in dashboards.
CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_events_idempotent
    ON payment_events(tx_hash, event_type)
    WHERE tx_hash IS NOT NULL;
