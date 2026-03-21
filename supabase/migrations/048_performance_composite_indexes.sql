-- Migration 048: Performance Composite Indexes (P0)
-- Source: DB Optimization Audit 2026-03-15
-- These indexes cover the hottest query paths identified across
-- dashboard, mobile app, MCP server, and payment retry jobs.
-- Note: Cannot use CONCURRENTLY in Supabase SQL Editor (runs inside transaction).
-- For production with large tables, run each CREATE INDEX separately via psql.
-- Applied to production: pending.

-- 1. Dashboard getTasks() — filters by status + category, orders by created_at
--    Before: Seq Scan (2-5s at scale)  |  After: Index Range Scan (~50ms)
CREATE INDEX IF NOT EXISTS idx_tasks_status_category_created
    ON tasks(status, category, created_at DESC)
    WHERE status IN ('published', 'accepted', 'in_progress');

-- 2. Agent dashboard — "my tasks" filtered by status
--    Before: 200-2000ms  |  After: 10-30ms
CREATE INDEX IF NOT EXISTS idx_tasks_agent_status_created
    ON tasks(agent_id, status, created_at DESC);

-- 3. Worker active task list — executor's assigned/in-progress tasks
--    Before: 200-2000ms  |  After: 10-30ms
CREATE INDEX IF NOT EXISTS idx_tasks_executor_status_created
    ON tasks(executor_id, status, created_at DESC)
    WHERE status IN ('accepted', 'in_progress', 'submitted');

-- 4. Payment retry job — finds orphaned submissions (approved but no payment_tx)
--    Runs every 60s. Before: full scan on 2M+ rows  |  After: <50ms
CREATE INDEX IF NOT EXISTS idx_submissions_orphaned
    ON submissions(agent_verdict, submitted_at ASC, task_id)
    WHERE agent_verdict IN ('accepted', 'approved') AND payment_tx IS NULL;

-- 5. Admin dashboard — pending/failed payment events
--    payment_events grows unbounded. Before: O(n) on 100M+  |  After: <50ms
CREATE INDEX IF NOT EXISTS idx_payment_events_pending
    ON payment_events(event_type, created_at DESC)
    WHERE status IN ('pending', 'failed');
