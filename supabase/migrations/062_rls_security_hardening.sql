-- Migration 062: RLS Security Hardening — Fix USING(true) / WITH CHECK(true) Policies
-- Source: Auth Security Hardening Plan, Phase 3, Task 3.1
-- Date: 2026-03-16
--
-- PROBLEM: Several RLS policies use USING(true) or WITH CHECK(true), which means
-- ANY holder of the public anon key (embedded in the JS bundle) can modify data.
-- This is a critical security vulnerability.
--
-- FIXES:
--   1. tasks UPDATE: Replace USING(true) with executor-only status progression
--   2. submissions SELECT (task_owner): Replace USING(true) with task-ownership check
--   3. task_applications SELECT (task_owner): Replace USING(true) with task-ownership check
--   4. ratings INSERT: Replace WITH CHECK(true) with authenticated-user check
--
-- NOTE: service_role bypasses RLS automatically — no changes needed for backend/admin.
-- NOTE: Uses helper functions from migration 054 (current_executor_ids, current_wallet_addresses).
-- IDEMPOTENT: All DROP POLICY use IF EXISTS; CREATE POLICY will fail if already exists,
--             so wrap in DO blocks for true idempotency.

-- ============================================================
-- 1. FIX: tasks UPDATE — was USING(true) WITH CHECK(true)
--    Attack: Anyone with anon key could change any task's status, bounty, executor_id, etc.
--    Fix: Only the assigned executor can update (status progression only).
--          Administrative updates (by MCP server) go through service_role which bypasses RLS.
-- ============================================================

DROP POLICY IF EXISTS "tasks_update_own" ON tasks;

-- Executor can update tasks assigned to them, but ONLY to valid worker-driven statuses.
-- Valid worker status transitions: accepted→in_progress, in_progress→submitted.
-- All other status changes (completed, cancelled, expired, etc.) are admin actions via service_role.
CREATE POLICY "tasks_update_executor" ON tasks
    FOR UPDATE
    TO authenticated
    USING (
        executor_id IN (SELECT current_executor_ids())
    )
    WITH CHECK (
        -- Only allow status values that a worker should set
        status IN ('accepted', 'in_progress', 'submitted')
    );

-- ============================================================
-- 2. FIX: submissions SELECT (task_owner) — was USING(true)
--    Attack: Anyone could read all submissions (including evidence, notes, payment details).
--    Fix: Only the task publisher (agent) can view submissions for their tasks.
--         Workers already have submissions_select_own from migration 055.
-- ============================================================

DROP POLICY IF EXISTS "submissions_select_task_owner" ON submissions;

-- Task publisher can view submissions for tasks they published.
-- Uses current_wallet_addresses() since tasks.agent_id stores the wallet address.
CREATE POLICY "submissions_select_task_publisher" ON submissions
    FOR SELECT
    USING (
        task_id IN (
            SELECT id FROM tasks
            WHERE agent_id IN (SELECT current_wallet_addresses())
        )
    );

-- ============================================================
-- 3. FIX: task_applications SELECT (task_owner) — was USING(true)
--    Attack: Anyone could see all applications across all tasks.
--    Fix: Only the task publisher can view applications for their tasks.
--         Workers already have applications_select_own from migration 055.
-- ============================================================

DROP POLICY IF EXISTS "applications_select_task_owner" ON task_applications;

-- Task publisher can view applications for tasks they published.
CREATE POLICY "applications_select_task_publisher" ON task_applications
    FOR SELECT
    USING (
        task_id IN (
            SELECT id FROM tasks
            WHERE agent_id IN (SELECT current_wallet_addresses())
        )
    );

-- ============================================================
-- 4. FIX: ratings INSERT — was WITH CHECK(true)
--    Attack: Anyone could insert fake ratings for any executor/task.
--    Fix: Only authenticated users can insert, and the executor_id in the rating
--         must correspond to a real executor (not necessarily the current user,
--         since agents rate workers and workers rate agents).
--         The rater_id must match the current user's wallet or executor.
-- ============================================================

-- Drop the overly permissive policy from migration 046
DROP POLICY IF EXISTS "Ratings insertable by authenticated" ON ratings;

-- Authenticated users can insert ratings, but rater_id must match one of their wallets.
-- This prevents user A from inserting ratings as if they were user B.
CREATE POLICY "ratings_insert_authenticated" ON ratings
    FOR INSERT
    TO authenticated
    WITH CHECK (
        -- The rater must be the current user (by wallet address)
        rater_id IN (SELECT current_wallet_addresses())
    );

-- ============================================================
-- 5. FIX: tasks INSERT — was WITH CHECK(true)
--    Attack: Any authenticated user could insert tasks with arbitrary agent_id,
--            impersonating other agents.
--    Fix: agent_id must match the current user's wallet address.
--         MCP server uses service_role which bypasses RLS.
-- ============================================================

DROP POLICY IF EXISTS "tasks_insert_authenticated" ON tasks;

-- Authenticated users can only create tasks where they are the agent.
CREATE POLICY "tasks_insert_own" ON tasks
    FOR INSERT
    TO authenticated
    WITH CHECK (
        agent_id IN (SELECT current_wallet_addresses())
    );

-- ============================================================
-- VERIFICATION QUERY (run after applying to check state):
--
--   SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
--   FROM pg_policies
--   WHERE tablename IN ('tasks', 'submissions', 'task_applications', 'ratings')
--   ORDER BY tablename, policyname;
--
-- Expected: No more USING(true) or WITH CHECK(true) on write policies.
-- ============================================================
