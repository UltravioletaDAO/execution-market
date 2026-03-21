-- Migration 054: RLS Performance Helpers
-- Source: DB Optimization Audit 2026-03-15 (Phase 3, Task 3.1)
-- Creates helper functions to replace repeated subqueries in RLS policies.
-- Instead of each policy running SELECT id FROM executors WHERE user_id = auth.uid(),
-- the planner can call a single STABLE function (cached within the transaction).
-- Note: Cannot use CONCURRENTLY in Supabase SQL Editor (runs inside transaction).
-- Applied to production: pending.

-- 1. current_executor_id(): returns the executor UUID for the current auth session.
--    Used by submissions, task_applications, and ratings RLS policies.
--    SECURITY DEFINER so it can read executors regardless of caller's RLS.
CREATE OR REPLACE FUNCTION current_executor_id()
RETURNS UUID
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT id FROM executors WHERE user_id = auth.uid() LIMIT 1;
$$;

-- 2. current_executor_ids(): returns ALL executor UUIDs for the current user.
--    A user may have multiple executor records (multi-wallet agents).
--    Used where IN (...) matching is needed.
CREATE OR REPLACE FUNCTION current_executor_ids()
RETURNS SETOF UUID
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT id FROM executors WHERE user_id = auth.uid();
$$;

-- 3. current_wallet_addresses(): returns all wallet addresses for the current user.
--    Used by tasks RLS (agent_id = wallet_address) for draft visibility.
CREATE OR REPLACE FUNCTION current_wallet_addresses()
RETURNS SETOF VARCHAR
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT wallet_address FROM executors WHERE user_id = auth.uid();
$$;

-- 4. Covering index for fast lookup (user_id → id + wallet_address)
--    This single index serves all three functions above.
CREATE INDEX IF NOT EXISTS idx_executors_user_id_covering
    ON executors(user_id) INCLUDE (id, wallet_address);
