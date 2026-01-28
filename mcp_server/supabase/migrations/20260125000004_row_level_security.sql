-- Chamba MCP Server: Row Level Security Policies
-- Migration: 20260125000004_row_level_security.sql
-- Description: RLS policies for secure data access

-- ============================================
-- ENABLE RLS ON ALL TABLES
-- ============================================

ALTER TABLE executors ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE escrows ENABLE ROW LEVEL SECURITY;

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Get current executor ID from auth context
CREATE OR REPLACE FUNCTION get_current_executor_id()
RETURNS UUID
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT id FROM executors WHERE user_id = auth.uid() LIMIT 1;
$$;

-- Get current agent ID from auth context (for API key auth)
CREATE OR REPLACE FUNCTION get_current_agent_id()
RETURNS UUID
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    -- For service role, this returns NULL (service role bypasses RLS)
    -- For user auth, this could be extended to support agent login
    SELECT NULL::UUID;
$$;

-- Check if request is from service role
CREATE OR REPLACE FUNCTION is_service_role()
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT auth.role() = 'service_role';
$$;

-- ============================================
-- EXECUTORS POLICIES
-- ============================================

-- Public: Anyone can view executor profiles (reputation is public)
CREATE POLICY "executors_select_public"
    ON executors
    FOR SELECT
    USING (TRUE);

-- Authenticated: Executors can update their own profile
CREATE POLICY "executors_update_own"
    ON executors
    FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Authenticated: Users can insert their own executor profile
CREATE POLICY "executors_insert_own"
    ON executors
    FOR INSERT
    WITH CHECK (
        user_id = auth.uid()
        OR user_id IS NULL  -- Allow creation without user_id (API-based)
    );

-- Service role: Full access for backend operations
CREATE POLICY "executors_service_role"
    ON executors
    FOR ALL
    USING (is_service_role())
    WITH CHECK (is_service_role());

-- ============================================
-- AGENTS POLICIES
-- ============================================

-- Public: Anyone can view verified agent profiles
CREATE POLICY "agents_select_public"
    ON agents
    FOR SELECT
    USING (TRUE);

-- Service role: Full access for agent management
CREATE POLICY "agents_service_role"
    ON agents
    FOR ALL
    USING (is_service_role())
    WITH CHECK (is_service_role());

-- Note: Agent creation/update is handled via service role (API key auth)

-- ============================================
-- TASKS POLICIES
-- ============================================

-- Public: Anyone can view published tasks
CREATE POLICY "tasks_select_public"
    ON tasks
    FOR SELECT
    USING (
        status = 'published'
        OR status = 'accepted'
        OR status = 'in_progress'
        OR status = 'submitted'
        OR status = 'verifying'
        OR status = 'completed'
        -- Allow executors to see their own assigned tasks regardless of status
        OR executor_id = get_current_executor_id()
    );

-- Authenticated: Executors can view all details of tasks they're assigned to
CREATE POLICY "tasks_select_assigned"
    ON tasks
    FOR SELECT
    USING (executor_id = get_current_executor_id());

-- Service role: Full access for task management (agents create via API)
CREATE POLICY "tasks_service_role"
    ON tasks
    FOR ALL
    USING (is_service_role())
    WITH CHECK (is_service_role());

-- Authenticated: Allow executors to update task status (in_progress)
CREATE POLICY "tasks_update_executor"
    ON tasks
    FOR UPDATE
    USING (
        executor_id = get_current_executor_id()
        AND status IN ('accepted', 'in_progress')
    )
    WITH CHECK (
        executor_id = get_current_executor_id()
        AND status IN ('accepted', 'in_progress', 'submitted')
    );

-- ============================================
-- APPLICATIONS POLICIES
-- ============================================

-- Authenticated: Executors can view their own applications
CREATE POLICY "applications_select_own"
    ON applications
    FOR SELECT
    USING (executor_id = get_current_executor_id());

-- Authenticated: Executors can insert applications
CREATE POLICY "applications_insert_executor"
    ON applications
    FOR INSERT
    WITH CHECK (executor_id = get_current_executor_id());

-- Authenticated: Executors can withdraw their pending applications
CREATE POLICY "applications_update_executor"
    ON applications
    FOR UPDATE
    USING (
        executor_id = get_current_executor_id()
        AND status = 'pending'
    )
    WITH CHECK (
        executor_id = get_current_executor_id()
        AND status IN ('pending', 'withdrawn')
    );

-- Authenticated: Executors can delete their pending applications
CREATE POLICY "applications_delete_executor"
    ON applications
    FOR DELETE
    USING (
        executor_id = get_current_executor_id()
        AND status = 'pending'
    );

-- Service role: Full access (agents review applications via API)
CREATE POLICY "applications_service_role"
    ON applications
    FOR ALL
    USING (is_service_role())
    WITH CHECK (is_service_role());

-- ============================================
-- SUBMISSIONS POLICIES
-- ============================================

-- Authenticated: Executors can view their own submissions
CREATE POLICY "submissions_select_own"
    ON submissions
    FOR SELECT
    USING (executor_id = get_current_executor_id());

-- Authenticated: Executors can insert submissions for their assigned tasks
CREATE POLICY "submissions_insert_executor"
    ON submissions
    FOR INSERT
    WITH CHECK (
        executor_id = get_current_executor_id()
        AND EXISTS (
            SELECT 1 FROM tasks
            WHERE tasks.id = task_id
            AND tasks.executor_id = get_current_executor_id()
            AND tasks.status IN ('accepted', 'in_progress')
        )
    );

-- Authenticated: Executors can update their pending submissions (add evidence)
CREATE POLICY "submissions_update_executor"
    ON submissions
    FOR UPDATE
    USING (
        executor_id = get_current_executor_id()
        AND status = 'pending'
    )
    WITH CHECK (
        executor_id = get_current_executor_id()
        AND status IN ('pending', 'more_info')
    );

-- Service role: Full access (agents review submissions via API)
CREATE POLICY "submissions_service_role"
    ON submissions
    FOR ALL
    USING (is_service_role())
    WITH CHECK (is_service_role());

-- ============================================
-- ESCROWS POLICIES
-- ============================================

-- Authenticated: Executors can view escrows for their assigned tasks
CREATE POLICY "escrows_select_executor"
    ON escrows
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM tasks
            WHERE tasks.id = task_id
            AND tasks.executor_id = get_current_executor_id()
        )
    );

-- Service role: Full access (escrow management via API)
CREATE POLICY "escrows_service_role"
    ON escrows
    FOR ALL
    USING (is_service_role())
    WITH CHECK (is_service_role());

-- ============================================
-- ADDITIONAL SECURITY MEASURES
-- ============================================

-- Prevent executors from modifying critical fields
CREATE OR REPLACE FUNCTION prevent_executor_critical_update()
RETURNS TRIGGER AS $$
BEGIN
    -- Prevent changing wallet_address
    IF OLD.wallet_address != NEW.wallet_address THEN
        RAISE EXCEPTION 'Cannot change wallet address';
    END IF;

    -- Prevent directly modifying reputation
    IF OLD.reputation_score != NEW.reputation_score
       AND auth.role() != 'service_role' THEN
        RAISE EXCEPTION 'Cannot directly modify reputation score';
    END IF;

    -- Prevent modifying completed tasks count directly
    IF OLD.tasks_completed != NEW.tasks_completed
       AND auth.role() != 'service_role' THEN
        RAISE EXCEPTION 'Cannot directly modify tasks_completed';
    END IF;

    -- Prevent modifying balance directly
    IF OLD.balance_usdc != NEW.balance_usdc
       AND auth.role() != 'service_role' THEN
        RAISE EXCEPTION 'Cannot directly modify balance';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER executors_prevent_critical_update
    BEFORE UPDATE ON executors
    FOR EACH ROW
    EXECUTE FUNCTION prevent_executor_critical_update();

-- Prevent changing task bounty after publication
CREATE OR REPLACE FUNCTION prevent_bounty_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status != 'draft' AND OLD.bounty_usd != NEW.bounty_usd THEN
        RAISE EXCEPTION 'Cannot change bounty after task is published';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tasks_prevent_bounty_change
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION prevent_bounty_change();

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON FUNCTION get_current_executor_id IS 'Get the executor ID for the currently authenticated user';
COMMENT ON FUNCTION is_service_role IS 'Check if the current request is from service role';
COMMENT ON POLICY "executors_select_public" ON executors IS 'Anyone can view executor profiles (reputation is public)';
COMMENT ON POLICY "tasks_select_public" ON tasks IS 'Anyone can view non-cancelled tasks';
COMMENT ON POLICY "applications_insert_executor" ON applications IS 'Executors can apply to published tasks';
COMMENT ON POLICY "submissions_insert_executor" ON submissions IS 'Executors can submit evidence for assigned tasks';
