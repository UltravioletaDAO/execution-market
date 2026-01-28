-- Chamba MCP Server: RPC Functions
-- Migration: 20260125000003_rpc_functions.sql
-- Description: Server-side functions for complex operations

-- ============================================
-- GET OR CREATE EXECUTOR
-- ============================================

-- Get existing executor by wallet or create new one
CREATE OR REPLACE FUNCTION get_or_create_executor(
    p_wallet VARCHAR(255),
    p_email VARCHAR(255) DEFAULT NULL,
    p_display_name VARCHAR(100) DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_executor executors%ROWTYPE;
    v_is_new BOOLEAN := FALSE;
BEGIN
    -- Normalize wallet address to lowercase
    p_wallet := LOWER(p_wallet);

    -- Try to find existing executor
    SELECT * INTO v_executor
    FROM executors
    WHERE LOWER(wallet_address) = p_wallet;

    -- If not found, create new one
    IF v_executor.id IS NULL THEN
        INSERT INTO executors (
            wallet_address,
            email,
            display_name,
            reputation_score,
            created_at,
            updated_at
        ) VALUES (
            p_wallet,
            p_email,
            COALESCE(p_display_name, 'Worker ' || SUBSTRING(p_wallet FROM 1 FOR 8)),
            50,  -- Default starting reputation
            NOW(),
            NOW()
        )
        RETURNING * INTO v_executor;

        v_is_new := TRUE;
    ELSE
        -- Update last active and optionally email
        UPDATE executors
        SET
            last_active_at = NOW(),
            email = COALESCE(p_email, email),
            display_name = COALESCE(p_display_name, display_name)
        WHERE id = v_executor.id
        RETURNING * INTO v_executor;
    END IF;

    RETURN jsonb_build_object(
        'success', TRUE,
        'is_new', v_is_new,
        'executor', jsonb_build_object(
            'id', v_executor.id,
            'wallet_address', v_executor.wallet_address,
            'display_name', v_executor.display_name,
            'email', v_executor.email,
            'reputation_score', v_executor.reputation_score,
            'tasks_completed', v_executor.tasks_completed,
            'balance_usdc', v_executor.balance_usdc,
            'created_at', v_executor.created_at
        )
    );
END;
$$;

-- ============================================
-- GET TASKS NEAR LOCATION
-- ============================================

-- Find published tasks within a radius of a point
CREATE OR REPLACE FUNCTION get_tasks_near_location(
    p_lat FLOAT,
    p_lng FLOAT,
    p_radius_km FLOAT DEFAULT 10.0,
    p_category task_category DEFAULT NULL,
    p_min_bounty DECIMAL DEFAULT 0,
    p_limit INTEGER DEFAULT 20,
    p_offset INTEGER DEFAULT 0
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_point GEOGRAPHY;
    v_tasks JSONB;
    v_total INTEGER;
BEGIN
    -- Create point from coordinates
    v_point := ST_MakePoint(p_lng, p_lat)::geography;

    -- Get total count first
    SELECT COUNT(*) INTO v_total
    FROM tasks
    WHERE status = 'published'
      AND (location IS NULL OR ST_DWithin(location, v_point, p_radius_km * 1000))
      AND (p_category IS NULL OR category = p_category)
      AND bounty_usd >= p_min_bounty;

    -- Get paginated results with distance
    SELECT COALESCE(jsonb_agg(task_data), '[]'::jsonb) INTO v_tasks
    FROM (
        SELECT jsonb_build_object(
            'id', t.id,
            'title', t.title,
            'description', t.description,
            'category', t.category,
            'bounty_usd', t.bounty_usd,
            'deadline', t.deadline,
            'location_hint', t.location_hint,
            'location_required', t.location_required,
            'min_reputation', t.min_reputation,
            'evidence_schema', t.evidence_schema,
            'created_at', t.created_at,
            'distance_km', CASE
                WHEN t.location IS NOT NULL
                THEN ROUND((ST_Distance(t.location, v_point) / 1000)::numeric, 2)
                ELSE NULL
            END,
            'agent', jsonb_build_object(
                'id', a.id,
                'name', a.name,
                'verified', a.verified
            )
        ) AS task_data
        FROM tasks t
        JOIN agents a ON t.agent_id = a.id
        WHERE t.status = 'published'
          AND (t.location IS NULL OR ST_DWithin(t.location, v_point, p_radius_km * 1000))
          AND (p_category IS NULL OR t.category = p_category)
          AND t.bounty_usd >= p_min_bounty
        ORDER BY
            CASE WHEN t.location IS NOT NULL
                 THEN ST_Distance(t.location, v_point)
                 ELSE 999999999 END ASC,
            t.bounty_usd DESC
        LIMIT p_limit
        OFFSET p_offset
    ) subquery;

    RETURN jsonb_build_object(
        'success', TRUE,
        'total', v_total,
        'count', jsonb_array_length(v_tasks),
        'offset', p_offset,
        'has_more', v_total > p_offset + jsonb_array_length(v_tasks),
        'search_radius_km', p_radius_km,
        'tasks', v_tasks
    );
END;
$$;

-- ============================================
-- UPDATE REPUTATION
-- ============================================

-- Atomic reputation update with logging
CREATE OR REPLACE FUNCTION update_reputation(
    p_executor_id UUID,
    p_delta INTEGER,
    p_reason VARCHAR(255),
    p_task_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_executor executors%ROWTYPE;
    v_new_score INTEGER;
BEGIN
    -- Lock executor row for update
    SELECT * INTO v_executor
    FROM executors
    WHERE id = p_executor_id
    FOR UPDATE;

    IF v_executor.id IS NULL THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'error', 'Executor not found'
        );
    END IF;

    -- Calculate new score (clamped to 0-100)
    v_new_score := GREATEST(0, LEAST(100, v_executor.reputation_score + p_delta));

    -- Update executor
    UPDATE executors
    SET
        reputation_score = v_new_score,
        updated_at = NOW()
    WHERE id = p_executor_id;

    -- Log the reputation change (if reputation_log table exists)
    BEGIN
        INSERT INTO reputation_log (
            executor_id,
            task_id,
            delta,
            new_score,
            reason,
            created_at
        ) VALUES (
            p_executor_id,
            p_task_id,
            p_delta,
            v_new_score,
            p_reason,
            NOW()
        );
    EXCEPTION WHEN undefined_table THEN
        -- reputation_log table doesn't exist, skip logging
        NULL;
    END;

    RETURN jsonb_build_object(
        'success', TRUE,
        'executor_id', p_executor_id,
        'previous_score', v_executor.reputation_score,
        'delta', p_delta,
        'new_score', v_new_score,
        'reason', p_reason
    );
END;
$$;

-- ============================================
-- GET AGENT STATS
-- ============================================

-- Get comprehensive statistics for an agent
CREATE OR REPLACE FUNCTION get_agent_stats(
    p_agent_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_agent agents%ROWTYPE;
    v_start_date TIMESTAMPTZ;
    v_stats JSONB;
    v_by_status JSONB;
    v_by_category JSONB;
    v_top_workers JSONB;
BEGIN
    -- Get agent
    SELECT * INTO v_agent
    FROM agents
    WHERE id = p_agent_id;

    IF v_agent.id IS NULL THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'error', 'Agent not found'
        );
    END IF;

    v_start_date := NOW() - (p_days || ' days')::interval;

    -- Tasks by status
    SELECT jsonb_object_agg(status, count) INTO v_by_status
    FROM (
        SELECT status, COUNT(*) as count
        FROM tasks
        WHERE agent_id = p_agent_id
          AND created_at >= v_start_date
        GROUP BY status
    ) s;

    -- Tasks by category
    SELECT jsonb_object_agg(category, count) INTO v_by_category
    FROM (
        SELECT category, COUNT(*) as count
        FROM tasks
        WHERE agent_id = p_agent_id
          AND created_at >= v_start_date
        GROUP BY category
    ) c;

    -- Top workers (by completed tasks for this agent)
    SELECT COALESCE(jsonb_agg(worker_data), '[]'::jsonb) INTO v_top_workers
    FROM (
        SELECT jsonb_build_object(
            'executor_id', e.id,
            'display_name', e.display_name,
            'reputation_score', e.reputation_score,
            'tasks_completed', COUNT(t.id)
        ) as worker_data
        FROM tasks t
        JOIN executors e ON t.executor_id = e.id
        WHERE t.agent_id = p_agent_id
          AND t.status = 'completed'
          AND t.completed_at >= v_start_date
        GROUP BY e.id, e.display_name, e.reputation_score
        ORDER BY COUNT(t.id) DESC
        LIMIT 5
    ) w;

    -- Build comprehensive stats
    SELECT jsonb_build_object(
        'total_tasks', COUNT(*),
        'completed_tasks', COUNT(*) FILTER (WHERE status = 'completed'),
        'pending_tasks', COUNT(*) FILTER (WHERE status IN ('published', 'accepted', 'in_progress', 'submitted', 'verifying')),
        'cancelled_tasks', COUNT(*) FILTER (WHERE status = 'cancelled'),
        'expired_tasks', COUNT(*) FILTER (WHERE status = 'expired'),
        'disputed_tasks', COUNT(*) FILTER (WHERE status = 'disputed'),
        'total_bounty_posted', COALESCE(SUM(bounty_usd), 0),
        'total_bounty_paid', COALESCE(SUM(bounty_usd) FILTER (WHERE status = 'completed'), 0),
        'avg_bounty', COALESCE(AVG(bounty_usd), 0),
        'completion_rate', CASE
            WHEN COUNT(*) > 0
            THEN ROUND((COUNT(*) FILTER (WHERE status = 'completed')::numeric / COUNT(*)::numeric) * 100, 2)
            ELSE 0
        END
    ) INTO v_stats
    FROM tasks
    WHERE agent_id = p_agent_id
      AND created_at >= v_start_date;

    RETURN jsonb_build_object(
        'success', TRUE,
        'agent', jsonb_build_object(
            'id', v_agent.id,
            'name', v_agent.name,
            'tier', v_agent.tier,
            'verified', v_agent.verified,
            'total_tasks_created', v_agent.total_tasks_created,
            'total_spent_usdc', v_agent.total_spent_usdc
        ),
        'period_days', p_days,
        'stats', v_stats,
        'by_status', COALESCE(v_by_status, '{}'::jsonb),
        'by_category', COALESCE(v_by_category, '{}'::jsonb),
        'top_workers', v_top_workers
    );
END;
$$;

-- ============================================
-- GET EXECUTOR DASHBOARD
-- ============================================

-- Get comprehensive dashboard data for an executor
CREATE OR REPLACE FUNCTION get_executor_dashboard(
    p_executor_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_executor executors%ROWTYPE;
    v_active_tasks JSONB;
    v_pending_applications JSONB;
    v_recent_submissions JSONB;
    v_earnings JSONB;
BEGIN
    -- Get executor
    SELECT * INTO v_executor
    FROM executors
    WHERE id = p_executor_id;

    IF v_executor.id IS NULL THEN
        RETURN jsonb_build_object(
            'success', FALSE,
            'error', 'Executor not found'
        );
    END IF;

    -- Active tasks (accepted, in_progress)
    SELECT COALESCE(jsonb_agg(task_data), '[]'::jsonb) INTO v_active_tasks
    FROM (
        SELECT jsonb_build_object(
            'id', t.id,
            'title', t.title,
            'bounty_usd', t.bounty_usd,
            'status', t.status,
            'deadline', t.deadline,
            'accepted_at', t.accepted_at
        ) as task_data
        FROM tasks t
        WHERE t.executor_id = p_executor_id
          AND t.status IN ('accepted', 'in_progress', 'submitted', 'verifying')
        ORDER BY t.deadline ASC
        LIMIT 10
    ) at;

    -- Pending applications
    SELECT COALESCE(jsonb_agg(app_data), '[]'::jsonb) INTO v_pending_applications
    FROM (
        SELECT jsonb_build_object(
            'id', a.id,
            'task_id', a.task_id,
            'task_title', t.title,
            'bounty_usd', t.bounty_usd,
            'created_at', a.created_at
        ) as app_data
        FROM applications a
        JOIN tasks t ON a.task_id = t.id
        WHERE a.executor_id = p_executor_id
          AND a.status = 'pending'
        ORDER BY a.created_at DESC
        LIMIT 10
    ) pa;

    -- Recent submissions
    SELECT COALESCE(jsonb_agg(sub_data), '[]'::jsonb) INTO v_recent_submissions
    FROM (
        SELECT jsonb_build_object(
            'id', s.id,
            'task_id', s.task_id,
            'task_title', t.title,
            'status', s.status,
            'submitted_at', s.submitted_at,
            'payment_amount', s.payment_amount
        ) as sub_data
        FROM submissions s
        JOIN tasks t ON s.task_id = t.id
        WHERE s.executor_id = p_executor_id
        ORDER BY s.submitted_at DESC
        LIMIT 10
    ) rs;

    -- Earnings summary
    SELECT jsonb_build_object(
        'balance_usdc', v_executor.balance_usdc,
        'total_earned_usdc', v_executor.total_earned_usdc,
        'total_withdrawn_usdc', v_executor.total_withdrawn_usdc,
        'pending_usdc', COALESCE(SUM(t.bounty_usd), 0)
    ) INTO v_earnings
    FROM tasks t
    WHERE t.executor_id = p_executor_id
      AND t.status IN ('submitted', 'verifying');

    RETURN jsonb_build_object(
        'success', TRUE,
        'executor', jsonb_build_object(
            'id', v_executor.id,
            'display_name', v_executor.display_name,
            'reputation_score', v_executor.reputation_score,
            'tasks_completed', v_executor.tasks_completed,
            'tasks_disputed', v_executor.tasks_disputed,
            'avg_rating', v_executor.avg_rating,
            'created_at', v_executor.created_at
        ),
        'active_tasks', v_active_tasks,
        'pending_applications', v_pending_applications,
        'recent_submissions', v_recent_submissions,
        'earnings', v_earnings
    );
END;
$$;

-- ============================================
-- ASSIGN TASK TO EXECUTOR
-- ============================================

-- Atomically assign a task to an executor
CREATE OR REPLACE FUNCTION assign_task(
    p_task_id UUID,
    p_executor_id UUID,
    p_agent_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_task tasks%ROWTYPE;
    v_executor executors%ROWTYPE;
BEGIN
    -- Lock task for update
    SELECT * INTO v_task
    FROM tasks
    WHERE id = p_task_id
    FOR UPDATE;

    IF v_task.id IS NULL THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Task not found');
    END IF;

    IF v_task.agent_id != p_agent_id THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Not authorized');
    END IF;

    IF v_task.status != 'published' THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Task is not available');
    END IF;

    -- Get executor
    SELECT * INTO v_executor
    FROM executors
    WHERE id = p_executor_id;

    IF v_executor.id IS NULL THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Executor not found');
    END IF;

    -- Check reputation
    IF v_executor.reputation_score < v_task.min_reputation THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Insufficient reputation');
    END IF;

    -- Update task
    UPDATE tasks
    SET
        status = 'accepted',
        executor_id = p_executor_id,
        accepted_at = NOW(),
        updated_at = NOW()
    WHERE id = p_task_id;

    -- Update application if exists
    UPDATE applications
    SET status = 'accepted', reviewed_at = NOW()
    WHERE task_id = p_task_id AND executor_id = p_executor_id;

    -- Reject other applications
    UPDATE applications
    SET status = 'rejected', reviewed_at = NOW(), rejection_reason = 'Task assigned to another worker'
    WHERE task_id = p_task_id AND executor_id != p_executor_id AND status = 'pending';

    RETURN jsonb_build_object(
        'success', TRUE,
        'task_id', p_task_id,
        'executor_id', p_executor_id,
        'assigned_at', NOW()
    );
END;
$$;

-- ============================================
-- COMPLETE TASK
-- ============================================

-- Complete a task and release payment
CREATE OR REPLACE FUNCTION complete_task(
    p_submission_id UUID,
    p_agent_id UUID,
    p_verdict VARCHAR(50),
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
    v_rep_delta INTEGER;
BEGIN
    -- Get submission
    SELECT * INTO v_submission
    FROM submissions
    WHERE id = p_submission_id
    FOR UPDATE;

    IF v_submission.id IS NULL THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Submission not found');
    END IF;

    -- Get task
    SELECT * INTO v_task
    FROM tasks
    WHERE id = v_submission.task_id
    FOR UPDATE;

    IF v_task.agent_id != p_agent_id THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Not authorized');
    END IF;

    -- Get executor
    SELECT * INTO v_executor
    FROM executors
    WHERE id = v_submission.executor_id;

    IF p_verdict = 'approved' THEN
        -- Calculate payment (bounty - 8% platform fee)
        v_payment_amount := v_task.bounty_usd * 0.92;
        v_rep_delta := 5;

        -- Update submission
        UPDATE submissions
        SET
            status = 'approved',
            agent_verdict = 'approved',
            agent_notes = p_notes,
            agent_rating = p_rating,
            verified_at = NOW(),
            payment_amount = v_payment_amount
        WHERE id = p_submission_id;

        -- Update task
        UPDATE tasks
        SET
            status = 'completed',
            completed_at = NOW()
        WHERE id = v_task.id;

        -- Update executor
        UPDATE executors
        SET
            tasks_completed = tasks_completed + 1,
            reputation_score = LEAST(100, reputation_score + v_rep_delta),
            balance_usdc = balance_usdc + v_payment_amount,
            total_earned_usdc = total_earned_usdc + v_payment_amount
        WHERE id = v_executor.id;

        -- Update agent stats
        UPDATE agents
        SET
            total_tasks_completed = total_tasks_completed + 1,
            total_spent_usdc = total_spent_usdc + v_task.bounty_usd
        WHERE id = p_agent_id;

    ELSIF p_verdict = 'rejected' THEN
        v_rep_delta := -3;

        -- Update submission
        UPDATE submissions
        SET
            status = 'rejected',
            agent_verdict = 'rejected',
            agent_notes = p_notes,
            verified_at = NOW()
        WHERE id = p_submission_id;

        -- Reopen task
        UPDATE tasks
        SET
            status = 'published',
            executor_id = NULL,
            accepted_at = NULL
        WHERE id = v_task.id;

        -- Update executor reputation
        UPDATE executors
        SET reputation_score = GREATEST(0, reputation_score + v_rep_delta)
        WHERE id = v_executor.id;

    ELSE
        RETURN jsonb_build_object('success', FALSE, 'error', 'Invalid verdict');
    END IF;

    RETURN jsonb_build_object(
        'success', TRUE,
        'submission_id', p_submission_id,
        'verdict', p_verdict,
        'payment_amount', CASE WHEN p_verdict = 'approved' THEN v_payment_amount ELSE 0 END,
        'reputation_delta', v_rep_delta
    );
END;
$$;

-- ============================================
-- GRANT PERMISSIONS
-- ============================================

GRANT EXECUTE ON FUNCTION get_or_create_executor TO authenticated, anon;
GRANT EXECUTE ON FUNCTION get_tasks_near_location TO authenticated, anon;
GRANT EXECUTE ON FUNCTION update_reputation TO authenticated;
GRANT EXECUTE ON FUNCTION get_agent_stats TO authenticated;
GRANT EXECUTE ON FUNCTION get_executor_dashboard TO authenticated;
GRANT EXECUTE ON FUNCTION assign_task TO authenticated;
GRANT EXECUTE ON FUNCTION complete_task TO authenticated;

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON FUNCTION get_or_create_executor IS 'Get existing executor by wallet or create a new one';
COMMENT ON FUNCTION get_tasks_near_location IS 'Find published tasks within a radius of coordinates';
COMMENT ON FUNCTION update_reputation IS 'Atomic reputation update with audit logging';
COMMENT ON FUNCTION get_agent_stats IS 'Comprehensive dashboard statistics for an agent';
COMMENT ON FUNCTION get_executor_dashboard IS 'Comprehensive dashboard data for an executor';
COMMENT ON FUNCTION assign_task IS 'Atomically assign a task to an executor';
COMMENT ON FUNCTION complete_task IS 'Complete a task and process payment';
