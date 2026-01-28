-- ============================================================================
-- CHAMBA: Human Execution Layer for AI Agents
-- Migration: 005_rpc_functions.sql
-- Description: Required RPC functions for all major operations
-- Version: 2.0.0
-- Date: 2026-01-25
-- ============================================================================

-- ============================================================================
-- EXECUTOR MANAGEMENT FUNCTIONS
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Get or Create Executor (Main registration function)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_or_create_executor(
    p_wallet_address TEXT,
    p_display_name TEXT DEFAULT NULL,
    p_email TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    wallet_address TEXT,
    display_name TEXT,
    email TEXT,
    reputation_score INTEGER,
    tier executor_tier,
    tasks_completed INTEGER,
    balance_usdc DECIMAL(18, 6),
    created_at TIMESTAMPTZ,
    is_new BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_executor_id UUID;
    v_is_new BOOLEAN := FALSE;
    v_user_id UUID;
    v_normalized_wallet TEXT;
BEGIN
    -- Get current authenticated user
    v_user_id := auth.uid();

    -- Normalize wallet address to lowercase
    v_normalized_wallet := LOWER(p_wallet_address);

    -- Validate wallet address format
    IF v_normalized_wallet !~ '^0x[a-f0-9]{40}$' THEN
        RAISE EXCEPTION 'Invalid wallet address format: %', p_wallet_address;
    END IF;

    -- Check if executor exists by wallet address
    SELECT e.id INTO v_executor_id
    FROM executors e
    WHERE LOWER(e.wallet_address) = v_normalized_wallet;

    IF v_executor_id IS NULL THEN
        -- Create new executor
        INSERT INTO executors (
            wallet_address,
            user_id,
            display_name,
            email,
            reputation_score,
            tier,
            status
        )
        VALUES (
            v_normalized_wallet,
            v_user_id,
            COALESCE(p_display_name, 'Worker_' || SUBSTRING(v_normalized_wallet FROM 3 FOR 8)),
            p_email,
            50,  -- Neutral starting reputation
            'probation',
            'active'
        )
        RETURNING executors.id INTO v_executor_id;

        v_is_new := TRUE;

        -- Log initial reputation
        INSERT INTO reputation_log (executor_id, event_type, delta, old_score, new_score, reason)
        VALUES (v_executor_id, 'initial_registration', 50, 0, 50, 'Account created');

        -- Link wallet to user if authenticated
        IF v_user_id IS NOT NULL THEN
            INSERT INTO user_wallets (user_id, wallet_address, is_primary)
            VALUES (v_user_id, v_normalized_wallet, TRUE)
            ON CONFLICT (user_id, wallet_address) DO NOTHING;
        END IF;

        -- Award newcomer badge (progress at 0)
        INSERT INTO badges (executor_id, badge_type, name, description, progress, max_progress)
        VALUES (v_executor_id, 'newcomer', 'Newcomer', 'Complete your first task', 0, 1);

    ELSE
        -- Update existing executor
        UPDATE executors
        SET
            last_active_at = NOW(),
            user_id = COALESCE(executors.user_id, v_user_id),
            email = COALESCE(executors.email, p_email)
        WHERE executors.id = v_executor_id;
    END IF;

    -- Return executor data
    RETURN QUERY
    SELECT
        e.id,
        e.wallet_address::TEXT,
        e.display_name::TEXT,
        e.email::TEXT,
        e.reputation_score,
        e.tier,
        e.tasks_completed,
        e.balance_usdc,
        e.created_at,
        v_is_new
    FROM executors e
    WHERE e.id = v_executor_id;
END;
$$;

-- ---------------------------------------------------------------------------
-- Link Wallet to Session
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION link_wallet_to_session(
    p_user_id UUID,
    p_wallet_address TEXT,
    p_chain_id INTEGER DEFAULT 8453
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_normalized_wallet TEXT;
BEGIN
    IF p_user_id IS NULL THEN
        RAISE EXCEPTION 'User ID is required';
    END IF;

    v_normalized_wallet := LOWER(p_wallet_address);

    IF v_normalized_wallet !~ '^0x[a-f0-9]{40}$' THEN
        RAISE EXCEPTION 'Invalid wallet address format';
    END IF;

    -- Update user metadata
    UPDATE auth.users
    SET raw_user_meta_data = COALESCE(raw_user_meta_data, '{}'::jsonb) ||
        jsonb_build_object('wallet_address', v_normalized_wallet)
    WHERE id = p_user_id;

    -- Create or update wallet link
    INSERT INTO user_wallets (user_id, wallet_address, is_primary, chain_id)
    VALUES (p_user_id, v_normalized_wallet, TRUE, p_chain_id)
    ON CONFLICT (user_id, wallet_address)
    DO UPDATE SET is_primary = TRUE, updated_at = NOW();

    -- Set other wallets as non-primary
    UPDATE user_wallets
    SET is_primary = FALSE, updated_at = NOW()
    WHERE user_id = p_user_id AND wallet_address != v_normalized_wallet;

    -- Link executor if exists
    UPDATE executors
    SET user_id = p_user_id, last_active_at = NOW()
    WHERE LOWER(wallet_address) = v_normalized_wallet
      AND user_id IS NULL;

    RETURN TRUE;
END;
$$;

-- ---------------------------------------------------------------------------
-- Get Executor Stats
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_executor_stats(p_executor_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'executor_id', e.id,
        'wallet_address', e.wallet_address,
        'display_name', e.display_name,
        'reputation_score', e.reputation_score,
        'tier', e.tier,
        'tasks_completed', e.tasks_completed,
        'tasks_disputed', e.tasks_disputed,
        'tasks_abandoned', e.tasks_abandoned,
        'avg_rating', e.avg_rating,
        'balance_usdc', e.balance_usdc,
        'total_earned_usdc', e.total_earned_usdc,
        'total_withdrawn_usdc', e.total_withdrawn_usdc,
        'member_since', e.created_at,
        'last_active', e.last_active_at,
        'badges_count', (SELECT COUNT(*) FROM badges b WHERE b.executor_id = e.id AND b.revoked_at IS NULL),
        'active_tasks', (SELECT COUNT(*) FROM tasks t WHERE t.executor_id = e.id AND t.status IN ('accepted', 'in_progress')),
        'pending_applications', (SELECT COUNT(*) FROM task_applications ta WHERE ta.executor_id = e.id AND ta.status = 'pending'),
        'approval_rate', CASE
            WHEN (SELECT COUNT(*) FROM submissions s WHERE s.executor_id = e.id AND s.agent_verdict IS NOT NULL) > 0 THEN
                ROUND((SELECT COUNT(*) FILTER (WHERE s.agent_verdict = 'approved')::DECIMAL /
                    NULLIF(COUNT(*), 0) * 100 FROM submissions s
                    WHERE s.executor_id = e.id AND s.agent_verdict IS NOT NULL), 2)
            ELSE NULL
        END
    ) INTO v_result
    FROM executors e
    WHERE e.id = p_executor_id;

    RETURN v_result;
END;
$$;

-- ============================================================================
-- TASK MANAGEMENT FUNCTIONS
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Get Nearby Tasks (PostGIS)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_nearby_tasks(
    p_lat DECIMAL,
    p_lng DECIMAL,
    p_radius_km INTEGER DEFAULT 50,
    p_limit INTEGER DEFAULT 20,
    p_category task_category DEFAULT NULL,
    p_min_bounty DECIMAL DEFAULT NULL,
    p_max_reputation INTEGER DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    instructions TEXT,
    bounty_usd DECIMAL(10, 2),
    category task_category,
    deadline TIMESTAMPTZ,
    distance_km DECIMAL,
    min_reputation INTEGER,
    evidence_schema JSONB,
    agent_id TEXT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.title::TEXT,
        t.instructions::TEXT,
        t.bounty_usd,
        t.category,
        t.deadline,
        ROUND((ST_Distance(
            t.location,
            ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)::geography
        ) / 1000)::DECIMAL, 2) as distance_km,
        t.min_reputation,
        t.evidence_schema,
        t.agent_id::TEXT,
        t.created_at
    FROM tasks t
    WHERE t.status = 'published'
      AND t.deadline > NOW()
      AND t.location IS NOT NULL
      AND (p_category IS NULL OR t.category = p_category)
      AND (p_min_bounty IS NULL OR t.bounty_usd >= p_min_bounty)
      AND (p_max_reputation IS NULL OR t.min_reputation <= p_max_reputation)
      AND ST_DWithin(
          t.location,
          ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)::geography,
          p_radius_km * 1000
      )
    ORDER BY distance_km ASC, t.bounty_usd DESC
    LIMIT p_limit;
END;
$$;

-- ---------------------------------------------------------------------------
-- Search Tasks
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION search_tasks(
    p_query TEXT DEFAULT NULL,
    p_category task_category DEFAULT NULL,
    p_min_bounty DECIMAL DEFAULT NULL,
    p_max_bounty DECIMAL DEFAULT NULL,
    p_status task_status DEFAULT 'published',
    p_limit INTEGER DEFAULT 20,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    instructions TEXT,
    bounty_usd DECIMAL(10, 2),
    category task_category,
    deadline TIMESTAMPTZ,
    min_reputation INTEGER,
    agent_id TEXT,
    has_location BOOLEAN,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.title::TEXT,
        t.instructions::TEXT,
        t.bounty_usd,
        t.category,
        t.deadline,
        t.min_reputation,
        t.agent_id::TEXT,
        t.location IS NOT NULL as has_location,
        t.created_at
    FROM tasks t
    WHERE t.status = p_status
      AND t.deadline > NOW()
      AND (p_query IS NULL OR (
          t.title ILIKE '%' || p_query || '%' OR
          t.instructions ILIKE '%' || p_query || '%' OR
          p_query = ANY(t.tags)
      ))
      AND (p_category IS NULL OR t.category = p_category)
      AND (p_min_bounty IS NULL OR t.bounty_usd >= p_min_bounty)
      AND (p_max_bounty IS NULL OR t.bounty_usd <= p_max_bounty)
    ORDER BY t.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$;

-- ---------------------------------------------------------------------------
-- Claim Task (First-come-first-served)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION claim_task(
    p_task_id UUID,
    p_executor_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_task tasks%ROWTYPE;
    v_executor executors%ROWTYPE;
BEGIN
    -- Lock task row
    SELECT * INTO v_task
    FROM tasks
    WHERE id = p_task_id
    FOR UPDATE SKIP LOCKED;

    IF v_task.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task not available or already claimed');
    END IF;

    IF v_task.status != 'published' THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task is not open for claiming');
    END IF;

    IF v_task.deadline < NOW() THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task deadline has passed');
    END IF;

    -- Get executor
    SELECT * INTO v_executor FROM executors WHERE id = p_executor_id;
    IF v_executor.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Executor not found');
    END IF;

    IF v_executor.status != 'active' THEN
        RETURN jsonb_build_object('success', false, 'error', 'Executor is not active');
    END IF;

    -- Check reputation requirement
    IF v_executor.reputation_score < v_task.min_reputation THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Insufficient reputation. Required: ' || v_task.min_reputation || ', yours: ' || v_executor.reputation_score
        );
    END IF;

    -- Check tier requirement
    IF v_task.required_tier IS NOT NULL AND v_executor.tier < v_task.required_tier THEN
        RETURN jsonb_build_object('success', false, 'error', 'Tier requirement not met');
    END IF;

    -- Claim the task
    UPDATE tasks
    SET
        status = 'accepted',
        executor_id = p_executor_id,
        accepted_at = NOW()
    WHERE id = p_task_id;

    -- Update executor
    UPDATE executors SET last_active_at = NOW() WHERE id = p_executor_id;

    RETURN jsonb_build_object(
        'success', true,
        'task_id', p_task_id,
        'executor_id', p_executor_id,
        'claimed_at', NOW(),
        'deadline', v_task.deadline,
        'bounty_usd', v_task.bounty_usd
    );
END;
$$;

-- ---------------------------------------------------------------------------
-- Apply to Task
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION apply_to_task(
    p_task_id UUID,
    p_executor_id UUID,
    p_message TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_task tasks%ROWTYPE;
    v_executor executors%ROWTYPE;
    v_application_id UUID;
BEGIN
    SELECT * INTO v_task FROM tasks WHERE id = p_task_id;
    IF v_task.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task not found');
    END IF;

    IF v_task.status != 'published' THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task is not open for applications');
    END IF;

    SELECT * INTO v_executor FROM executors WHERE id = p_executor_id;
    IF v_executor.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Executor not found');
    END IF;

    IF v_executor.reputation_score < v_task.min_reputation THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Minimum reputation required: ' || v_task.min_reputation
        );
    END IF;

    -- Check for existing application
    IF EXISTS (SELECT 1 FROM task_applications WHERE task_id = p_task_id AND executor_id = p_executor_id) THEN
        RETURN jsonb_build_object('success', false, 'error', 'Already applied to this task');
    END IF;

    -- Create application
    INSERT INTO task_applications (task_id, executor_id, message, status)
    VALUES (p_task_id, p_executor_id, p_message, 'pending')
    RETURNING id INTO v_application_id;

    RETURN jsonb_build_object(
        'success', true,
        'application_id', v_application_id,
        'task_id', p_task_id,
        'executor_id', p_executor_id
    );
END;
$$;

-- ---------------------------------------------------------------------------
-- Assign Task to Executor
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION assign_task_to_executor(
    p_task_id UUID,
    p_executor_id UUID,
    p_agent_id TEXT,
    p_notes TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_task tasks%ROWTYPE;
    v_executor executors%ROWTYPE;
BEGIN
    SELECT * INTO v_task FROM tasks WHERE id = p_task_id FOR UPDATE;

    IF v_task.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task not found');
    END IF;

    IF v_task.status != 'published' THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task not available for assignment');
    END IF;

    IF v_task.agent_id != p_agent_id THEN
        RETURN jsonb_build_object('success', false, 'error', 'Not authorized to assign this task');
    END IF;

    SELECT * INTO v_executor FROM executors WHERE id = p_executor_id;
    IF v_executor.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Executor not found');
    END IF;

    -- Update task
    UPDATE tasks
    SET
        status = 'accepted',
        executor_id = p_executor_id,
        accepted_at = NOW(),
        assignment_notes = p_notes
    WHERE id = p_task_id;

    -- Update application if exists
    UPDATE task_applications
    SET status = 'accepted', responded_at = NOW()
    WHERE task_id = p_task_id AND executor_id = p_executor_id;

    -- Reject other applications
    UPDATE task_applications
    SET status = 'rejected', responded_at = NOW()
    WHERE task_id = p_task_id AND executor_id != p_executor_id AND status = 'pending';

    RETURN jsonb_build_object(
        'success', true,
        'task_id', p_task_id,
        'executor_id', p_executor_id,
        'assigned_at', NOW()
    );
END;
$$;

-- ---------------------------------------------------------------------------
-- Abandon Task
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION abandon_task(
    p_task_id UUID,
    p_executor_id UUID,
    p_reason TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_task tasks%ROWTYPE;
    v_executor executors%ROWTYPE;
    v_penalty INTEGER := 5;
BEGIN
    SELECT * INTO v_task FROM tasks WHERE id = p_task_id FOR UPDATE;

    IF v_task.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task not found');
    END IF;

    IF v_task.executor_id != p_executor_id THEN
        RETURN jsonb_build_object('success', false, 'error', 'Not your task');
    END IF;

    IF v_task.status NOT IN ('accepted', 'in_progress') THEN
        RETURN jsonb_build_object('success', false, 'error', 'Cannot abandon task in current status');
    END IF;

    SELECT * INTO v_executor FROM executors WHERE id = p_executor_id;

    -- Reopen task
    UPDATE tasks
    SET
        status = 'published',
        executor_id = NULL,
        accepted_at = NULL,
        started_at = NULL
    WHERE id = p_task_id;

    -- Apply reputation penalty
    UPDATE executors
    SET
        reputation_score = GREATEST(0, reputation_score - v_penalty),
        tasks_abandoned = tasks_abandoned + 1
    WHERE id = p_executor_id;

    -- Log penalty
    INSERT INTO reputation_log (
        executor_id, task_id, event_type, delta, old_score, new_score, reason
    ) VALUES (
        p_executor_id, p_task_id, 'task_abandoned', -v_penalty,
        v_executor.reputation_score, GREATEST(0, v_executor.reputation_score - v_penalty),
        'Task abandoned' || COALESCE(': ' || p_reason, '')
    );

    RETURN jsonb_build_object(
        'success', true,
        'task_id', p_task_id,
        'reputation_penalty', v_penalty,
        'new_reputation', GREATEST(0, v_executor.reputation_score - v_penalty)
    );
END;
$$;

-- ============================================================================
-- SUBMISSION FUNCTIONS
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Submit Evidence
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION submit_evidence(
    p_task_id UUID,
    p_executor_id UUID,
    p_evidence JSONB,
    p_notes TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_task tasks%ROWTYPE;
    v_submission_id UUID;
BEGIN
    SELECT * INTO v_task FROM tasks WHERE id = p_task_id FOR UPDATE;

    IF v_task.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task not found');
    END IF;

    IF v_task.executor_id != p_executor_id THEN
        RETURN jsonb_build_object('success', false, 'error', 'Not assigned to this task');
    END IF;

    IF v_task.status NOT IN ('accepted', 'in_progress') THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task not in submittable state');
    END IF;

    IF v_task.deadline < NOW() THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task deadline has passed');
    END IF;

    -- Create or update submission
    INSERT INTO submissions (task_id, executor_id, evidence, notes)
    VALUES (p_task_id, p_executor_id, p_evidence, p_notes)
    ON CONFLICT (task_id, executor_id)
    DO UPDATE SET
        evidence = EXCLUDED.evidence,
        notes = EXCLUDED.notes,
        submitted_at = NOW()
    RETURNING id INTO v_submission_id;

    -- Update task status
    UPDATE tasks SET status = 'submitted' WHERE id = p_task_id;

    -- Update executor last active
    UPDATE executors SET last_active_at = NOW() WHERE id = p_executor_id;

    RETURN jsonb_build_object(
        'success', true,
        'submission_id', v_submission_id,
        'task_id', p_task_id,
        'submitted_at', NOW()
    );
END;
$$;

-- ---------------------------------------------------------------------------
-- Complete Submission (Approve/Reject)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION complete_submission(
    p_submission_id UUID,
    p_agent_id TEXT,
    p_verdict TEXT,  -- 'approved' or 'rejected'
    p_notes TEXT DEFAULT NULL,
    p_rating INTEGER DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_submission submissions%ROWTYPE;
    v_task tasks%ROWTYPE;
    v_executor executors%ROWTYPE;
    v_payment_amount DECIMAL;
    v_reputation_delta INTEGER;
BEGIN
    SELECT * INTO v_submission FROM submissions WHERE id = p_submission_id FOR UPDATE;
    IF v_submission.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Submission not found');
    END IF;

    SELECT * INTO v_task FROM tasks WHERE id = v_submission.task_id;
    IF v_task.agent_id != p_agent_id THEN
        RETURN jsonb_build_object('success', false, 'error', 'Not authorized');
    END IF;

    SELECT * INTO v_executor FROM executors WHERE id = v_submission.executor_id;

    IF p_verdict = 'approved' THEN
        -- Calculate payment (bounty - 8% platform fee)
        v_payment_amount := v_task.bounty_usd * 0.92;
        v_reputation_delta := 5;

        UPDATE submissions
        SET
            agent_verdict = 'approved',
            agent_notes = p_notes,
            verified_at = NOW(),
            payment_amount = v_payment_amount
        WHERE id = p_submission_id;

        UPDATE tasks
        SET status = 'completed', completed_at = NOW()
        WHERE id = v_task.id;

        -- Update reputation
        UPDATE executors
        SET reputation_score = LEAST(100, reputation_score + v_reputation_delta)
        WHERE id = v_executor.id;

        -- Submit rating if provided
        IF p_rating IS NOT NULL THEN
            PERFORM submit_rating(v_executor.id, v_task.id, p_agent_id, p_rating, p_notes);
        END IF;

    ELSIF p_verdict = 'rejected' THEN
        v_reputation_delta := -3;

        UPDATE submissions
        SET agent_verdict = 'rejected', agent_notes = p_notes, verified_at = NOW()
        WHERE id = p_submission_id;

        -- Reopen task
        UPDATE tasks
        SET status = 'published', executor_id = NULL, accepted_at = NULL
        WHERE id = v_task.id;

        UPDATE executors
        SET reputation_score = GREATEST(0, reputation_score + v_reputation_delta)
        WHERE id = v_executor.id;
    ELSE
        RETURN jsonb_build_object('success', false, 'error', 'Invalid verdict');
    END IF;

    -- Log reputation change
    INSERT INTO reputation_log (
        executor_id, task_id, submission_id, event_type, delta,
        old_score, new_score, reason
    ) VALUES (
        v_executor.id, v_task.id, p_submission_id,
        CASE p_verdict WHEN 'approved' THEN 'task_approved' ELSE 'task_rejected' END,
        v_reputation_delta, v_executor.reputation_score,
        CASE p_verdict WHEN 'approved' THEN LEAST(100, v_executor.reputation_score + v_reputation_delta)
        ELSE GREATEST(0, v_executor.reputation_score + v_reputation_delta) END,
        'Submission ' || p_verdict || ': ' || v_task.title
    );

    -- Check for milestone badges
    IF p_verdict = 'approved' THEN
        PERFORM check_milestone_badges(v_executor.id);
    END IF;

    RETURN jsonb_build_object(
        'success', true,
        'submission_id', p_submission_id,
        'verdict', p_verdict,
        'payment_amount', CASE WHEN p_verdict = 'approved' THEN v_payment_amount ELSE 0 END,
        'reputation_delta', v_reputation_delta
    );
END;
$$;

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Get Task Details
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_task_details(p_task_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'task', jsonb_build_object(
            'id', t.id,
            'title', t.title,
            'instructions', t.instructions,
            'category', t.category,
            'bounty_usd', t.bounty_usd,
            'deadline', t.deadline,
            'status', t.status,
            'min_reputation', t.min_reputation,
            'evidence_schema', t.evidence_schema,
            'created_at', t.created_at,
            'accepted_at', t.accepted_at,
            'completed_at', t.completed_at,
            'has_location', t.location IS NOT NULL,
            'location_hint', t.location_hint
        ),
        'agent', jsonb_build_object(
            'id', t.agent_id,
            'name', t.agent_name
        ),
        'executor', CASE WHEN e.id IS NOT NULL THEN jsonb_build_object(
            'id', e.id,
            'display_name', e.display_name,
            'reputation_score', e.reputation_score,
            'tier', e.tier
        ) ELSE NULL END,
        'submission', CASE WHEN s.id IS NOT NULL THEN jsonb_build_object(
            'id', s.id,
            'submitted_at', s.submitted_at,
            'verdict', s.agent_verdict,
            'verified_at', s.verified_at
        ) ELSE NULL END,
        'applications_count', (SELECT COUNT(*) FROM task_applications ta WHERE ta.task_id = t.id AND ta.status = 'pending'),
        'has_escrow', t.escrow_id IS NOT NULL
    ) INTO v_result
    FROM tasks t
    LEFT JOIN executors e ON t.executor_id = e.id
    LEFT JOIN submissions s ON s.task_id = t.id AND s.executor_id = t.executor_id
    WHERE t.id = p_task_id;

    RETURN v_result;
END;
$$;

-- ---------------------------------------------------------------------------
-- Get Executor Tasks
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_executor_tasks(
    p_executor_id UUID,
    p_status task_status DEFAULT NULL,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    task_id UUID,
    title TEXT,
    category task_category,
    bounty_usd DECIMAL(10, 2),
    status task_status,
    deadline TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    submission_id UUID,
    submission_verdict TEXT,
    payment_amount DECIMAL(10, 2)
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.title::TEXT,
        t.category,
        t.bounty_usd,
        t.status,
        t.deadline,
        t.accepted_at,
        t.completed_at,
        s.id,
        s.agent_verdict::TEXT,
        s.payment_amount
    FROM tasks t
    LEFT JOIN submissions s ON s.task_id = t.id AND s.executor_id = p_executor_id
    WHERE t.executor_id = p_executor_id
      AND (p_status IS NULL OR t.status = p_status)
    ORDER BY
        CASE t.status
            WHEN 'accepted' THEN 1
            WHEN 'in_progress' THEN 2
            WHEN 'submitted' THEN 3
            WHEN 'verifying' THEN 4
            ELSE 5
        END,
        t.deadline ASC
    LIMIT p_limit;
END;
$$;

-- ---------------------------------------------------------------------------
-- Expire Tasks (Called by cron)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION expire_overdue_tasks()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_count INTEGER;
BEGIN
    WITH expired AS (
        UPDATE tasks
        SET status = 'expired'
        WHERE status = 'published'
          AND deadline < NOW()
        RETURNING id
    )
    SELECT COUNT(*) INTO v_count FROM expired;

    RETURN v_count;
END;
$$;

-- ---------------------------------------------------------------------------
-- Get Platform Stats (Public)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_platform_stats()
RETURNS JSONB
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'total_tasks', (SELECT COUNT(*) FROM tasks),
        'completed_tasks', (SELECT COUNT(*) FROM tasks WHERE status = 'completed'),
        'open_tasks', (SELECT COUNT(*) FROM tasks WHERE status = 'published'),
        'total_executors', (SELECT COUNT(*) FROM executors WHERE status = 'active'),
        'total_bounties_usd', (SELECT COALESCE(SUM(bounty_usd), 0) FROM tasks),
        'completed_bounties_usd', (SELECT COALESCE(SUM(bounty_usd), 0) FROM tasks WHERE status = 'completed'),
        'avg_completion_time_hours', (
            SELECT ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - accepted_at)) / 3600)::DECIMAL, 2)
            FROM tasks WHERE status = 'completed' AND completed_at IS NOT NULL AND accepted_at IS NOT NULL
        ),
        'categories', (
            SELECT jsonb_object_agg(category, count)
            FROM (SELECT category, COUNT(*) as count FROM tasks WHERE status = 'published' GROUP BY category) c
        )
    ) INTO v_result;

    RETURN v_result;
END;
$$;

-- ============================================================================
-- GRANTS
-- ============================================================================

-- Public functions (anon + authenticated)
GRANT EXECUTE ON FUNCTION get_or_create_executor TO authenticated;
GRANT EXECUTE ON FUNCTION get_executor_stats TO authenticated;
GRANT EXECUTE ON FUNCTION get_nearby_tasks TO anon, authenticated;
GRANT EXECUTE ON FUNCTION search_tasks TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_task_details TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_platform_stats TO anon, authenticated;

-- Authenticated only
GRANT EXECUTE ON FUNCTION link_wallet_to_session TO authenticated;
GRANT EXECUTE ON FUNCTION claim_task TO authenticated;
GRANT EXECUTE ON FUNCTION apply_to_task TO authenticated;
GRANT EXECUTE ON FUNCTION abandon_task TO authenticated;
GRANT EXECUTE ON FUNCTION submit_evidence TO authenticated;
GRANT EXECUTE ON FUNCTION get_executor_tasks TO authenticated;

-- Service role only
GRANT EXECUTE ON FUNCTION assign_task_to_executor TO service_role;
GRANT EXECUTE ON FUNCTION complete_submission TO service_role;
GRANT EXECUTE ON FUNCTION expire_overdue_tasks TO service_role;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON FUNCTION get_or_create_executor IS 'Get existing or create new executor by wallet address';
COMMENT ON FUNCTION link_wallet_to_session IS 'Link a wallet address to a user session';
COMMENT ON FUNCTION get_executor_stats IS 'Get comprehensive executor statistics';
COMMENT ON FUNCTION get_nearby_tasks IS 'Find published tasks within radius using PostGIS';
COMMENT ON FUNCTION search_tasks IS 'Search tasks with filters';
COMMENT ON FUNCTION claim_task IS 'Claim an open task (first-come-first-served)';
COMMENT ON FUNCTION apply_to_task IS 'Apply to a task';
COMMENT ON FUNCTION assign_task_to_executor IS 'Agent assigns task to specific executor';
COMMENT ON FUNCTION abandon_task IS 'Executor abandons claimed task (with penalty)';
COMMENT ON FUNCTION submit_evidence IS 'Submit evidence for a task';
COMMENT ON FUNCTION complete_submission IS 'Agent approves or rejects submission';
COMMENT ON FUNCTION get_task_details IS 'Get full task details with related data';
COMMENT ON FUNCTION get_executor_tasks IS 'Get tasks for an executor';
COMMENT ON FUNCTION expire_overdue_tasks IS 'Mark overdue published tasks as expired';
COMMENT ON FUNCTION get_platform_stats IS 'Get public platform statistics';
