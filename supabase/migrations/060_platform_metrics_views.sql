-- Migration 060: Platform Metrics & Leaderboard Materialized Views
-- Source: DB Optimization Audit 2026-03-15 (Phase 5, Tasks 5.1, 5.2, 5.3)
-- Replaces full table scans on every dashboard load with pre-computed views.
-- REFRESH MATERIALIZED VIEW CONCURRENTLY runs outside transaction context,
-- so it works fine when called from a pg_cron job or backend RPC — NOT from
-- the SQL Editor (which wraps in a transaction).
-- Applied to production: pending.

-- ============================================================
-- 1. Platform Metrics (Task 5.1)
-- ============================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS platform_metrics AS
SELECT
    COUNT(*) AS total_tasks,
    COUNT(*) FILTER (WHERE status = 'published') AS published_tasks,
    COUNT(*) FILTER (WHERE status = 'completed') AS completed_tasks,
    COUNT(*) FILTER (WHERE status IN ('accepted', 'in_progress', 'submitted')) AS active_tasks,
    COALESCE(SUM(bounty_usd) FILTER (WHERE status = 'completed'), 0) AS total_volume_usd,
    (SELECT COUNT(*) FROM executors WHERE status = 'active') AS active_executors
FROM tasks;

-- Unique index required for CONCURRENTLY refresh
CREATE UNIQUE INDEX ON platform_metrics ((1));

-- ============================================================
-- 2. Executor Leaderboard (Task 5.2)
-- ============================================================
-- Note: a regular VIEW `reputation_leaderboard` already exists (migration 003).
-- This materialized view is separate — pre-computed, indexed, much faster.

CREATE MATERIALIZED VIEW IF NOT EXISTS executor_leaderboard AS
SELECT
    e.id,
    e.display_name,
    e.reputation_score,
    e.tier,
    e.tasks_completed,
    e.avg_rating,
    (SELECT COUNT(*) FROM badges b WHERE b.executor_id = e.id) AS badges_count,
    RANK() OVER (ORDER BY e.reputation_score DESC, e.tasks_completed DESC) AS rank
FROM executors e
WHERE e.status = 'active'
ORDER BY e.reputation_score DESC, e.tasks_completed DESC
LIMIT 500;

CREATE UNIQUE INDEX ON executor_leaderboard (id);
CREATE INDEX ON executor_leaderboard (rank);
CREATE INDEX ON executor_leaderboard (reputation_score DESC);

-- ============================================================
-- 3. Refresh Function (Task 5.3)
-- ============================================================
-- Called by backend admin endpoint or pg_cron job.
-- CONCURRENTLY allows reads during refresh (requires unique index, created above).
-- SECURITY DEFINER so it can be called from an RPC without elevated role.

CREATE OR REPLACE FUNCTION refresh_platform_views()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY platform_metrics;
    REFRESH MATERIALIZED VIEW CONCURRENTLY executor_leaderboard;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
