-- Migration 055: Refactor RLS Policies to Use Helper Functions
-- Source: DB Optimization Audit 2026-03-15 (Phase 3, Tasks 3.2-3.4)
-- Replaces repeated subqueries with calls to current_executor_id() / current_executor_ids().
-- Before: each policy ran SELECT id FROM executors WHERE user_id = auth.uid()
-- After: single function call, STABLE (cached within transaction), with covering index.
-- Applied to production: pending.

-- ============================================================
-- SUBMISSIONS policies (Task 3.2)
-- ============================================================

-- SELECT: worker can see their own submissions
DROP POLICY IF EXISTS "submissions_select_own" ON submissions;
CREATE POLICY "submissions_select_own" ON submissions
    FOR SELECT
    USING (executor_id IN (SELECT current_executor_ids()));

-- Note: submissions_select_task_owner (USING true) stays as-is — API validates ownership

-- INSERT: worker can create submissions for their executor
-- Replaces migration 013's policy (was TO public, now TO authenticated for safety)
DROP POLICY IF EXISTS "Executors can insert submissions" ON submissions;
DROP POLICY IF EXISTS "submissions_insert_own" ON submissions;
CREATE POLICY "submissions_insert_own" ON submissions
    FOR INSERT
    TO authenticated
    WITH CHECK (executor_id IN (SELECT current_executor_ids()));

-- UPDATE: worker can update their own submissions
DROP POLICY IF EXISTS "submissions_update_own" ON submissions;
CREATE POLICY "submissions_update_own" ON submissions
    FOR UPDATE
    USING (executor_id IN (SELECT current_executor_ids()));

-- ============================================================
-- TASK_APPLICATIONS policies (Task 3.3)
-- ============================================================

-- SELECT: worker can see their own applications
DROP POLICY IF EXISTS "applications_select_own" ON task_applications;
CREATE POLICY "applications_select_own" ON task_applications
    FOR SELECT
    USING (executor_id IN (SELECT current_executor_ids()));

-- Note: applications_select_task_owner (USING true) stays as-is — API validates ownership

-- INSERT: worker can create applications for their executor
DROP POLICY IF EXISTS "applications_insert_own" ON task_applications;
CREATE POLICY "applications_insert_own" ON task_applications
    FOR INSERT
    TO authenticated
    WITH CHECK (executor_id IN (SELECT current_executor_ids()));

-- UPDATE: worker can update their own applications
DROP POLICY IF EXISTS "applications_update_own" ON task_applications;
CREATE POLICY "applications_update_own" ON task_applications
    FOR UPDATE
    USING (executor_id IN (SELECT current_executor_ids()));

-- ============================================================
-- TASKS draft visibility (Task 3.4)
-- ============================================================

-- The original policy referenced status = 'draft', but 'draft' does not exist
-- in the task_status enum in production. Tasks are created directly as 'published'.
-- Drop the non-functional policy. If drafts are added in the future, recreate
-- with: status = 'draft'::task_status AND agent_id IN (SELECT current_wallet_addresses())
DROP POLICY IF EXISTS "tasks_select_own_drafts" ON tasks;
