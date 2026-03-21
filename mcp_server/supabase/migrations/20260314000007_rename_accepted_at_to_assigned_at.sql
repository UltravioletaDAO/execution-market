-- ============================================================================
-- Migration 007: Rename accepted_at → assigned_at on tasks table
-- ============================================================================
-- The column "accepted_at" has always tracked when a worker was ASSIGNED to
-- a task, not when the agent accepted evidence. Rename for clarity.
--
-- Also recreates all functions that reference the column by name in SQL
-- strings (ALTER TABLE RENAME does NOT auto-fix function bodies).
-- ============================================================================

BEGIN;

-- 1. Rename the column
ALTER TABLE tasks RENAME COLUMN accepted_at TO assigned_at;

-- 2. Recreate: apply_to_task (RPC function)
CREATE OR REPLACE FUNCTION apply_to_task(
    p_task_id UUID,
    p_executor_id UUID,
    p_message TEXT DEFAULT NULL
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_task tasks%ROWTYPE;
    v_executor executors%ROWTYPE;
BEGIN
    SELECT * INTO v_task FROM tasks WHERE id = p_task_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Task not found');
    END IF;

    IF v_task.status != 'published' THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Task is not available for applications');
    END IF;

    SELECT * INTO v_executor FROM executors WHERE id = p_executor_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Executor not found');
    END IF;

    IF EXISTS (
        SELECT 1 FROM applications
        WHERE task_id = p_task_id AND executor_id = p_executor_id
    ) THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Already applied to this task');
    END IF;

    IF v_executor.wallet_address IS NOT NULL
       AND lower(v_executor.wallet_address) = lower(v_task.agent_id) THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Cannot apply to your own task');
    END IF;

    IF v_executor.reputation_score < v_task.min_reputation THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Insufficient reputation');
    END IF;

    UPDATE tasks
    SET status = 'accepted',
        executor_id = p_executor_id,
        assigned_at = NOW(),
        updated_at = NOW()
    WHERE id = p_task_id;

    UPDATE applications
    SET status = 'accepted', reviewed_at = NOW()
    WHERE task_id = p_task_id AND executor_id = p_executor_id;

    UPDATE applications
    SET status = 'rejected', reviewed_at = NOW(),
        rejection_reason = 'Task assigned to another worker'
    WHERE task_id = p_task_id AND executor_id != p_executor_id AND status = 'pending';

    RETURN jsonb_build_object(
        'success', TRUE,
        'task_id', p_task_id,
        'executor_id', p_executor_id,
        'assigned_at', NOW()
    );
END;
$$;

-- 3. Recreate: complete_task (rejection path sets assigned_at = NULL)
--    Only the rejection branch references the column; read the full function
--    from 20260125000003 and patch the column name.
CREATE OR REPLACE FUNCTION complete_task(
    p_submission_id UUID,
    p_verdict TEXT,
    p_notes TEXT DEFAULT NULL
) RETURNS JSONB
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
    SELECT * INTO v_submission FROM submissions WHERE id = p_submission_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Submission not found');
    END IF;

    IF v_submission.agent_verdict != 'pending' THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Submission already reviewed');
    END IF;

    SELECT * INTO v_task FROM tasks WHERE id = v_submission.task_id;
    SELECT * INTO v_executor FROM executors WHERE id = v_submission.executor_id;

    IF p_verdict = 'approved' THEN
        v_payment_amount := v_task.bounty_usd * 0.92;
        v_rep_delta := 5;

        UPDATE submissions
        SET status = 'approved',
            agent_verdict = 'approved',
            agent_notes = p_notes,
            verified_at = NOW()
        WHERE id = p_submission_id;

        UPDATE tasks
        SET status = 'completed',
            completed_at = NOW(),
            updated_at = NOW()
        WHERE id = v_task.id;

        UPDATE executors
        SET tasks_completed = tasks_completed + 1,
            reputation_score = LEAST(100, reputation_score + v_rep_delta),
            balance_usdc = balance_usdc + v_payment_amount,
            total_earned_usdc = total_earned_usdc + v_payment_amount,
            last_active_at = NOW(),
            updated_at = NOW()
        WHERE id = v_executor.id;

        UPDATE escrows
        SET status = 'released', released_at = NOW()
        WHERE task_id = v_task.id;

    ELSIF p_verdict = 'rejected' THEN
        v_rep_delta := -3;

        UPDATE submissions
        SET status = 'rejected',
            agent_verdict = 'rejected',
            agent_notes = p_notes,
            verified_at = NOW()
        WHERE id = p_submission_id;

        -- Reopen task — use assigned_at (renamed from accepted_at)
        UPDATE tasks
        SET status = 'published',
            executor_id = NULL,
            assigned_at = NULL
        WHERE id = v_task.id;

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

-- 4. Recreate: on_submission_verdict (trigger — rejection sets assigned_at = NULL)
CREATE OR REPLACE FUNCTION on_submission_verdict()
RETURNS TRIGGER AS $$
DECLARE
    v_task tasks%ROWTYPE;
    v_payment_amount DECIMAL;
    v_rep_delta INTEGER;
BEGIN
    IF OLD.status = 'pending' AND NEW.status != 'pending' THEN
        SELECT * INTO v_task FROM tasks WHERE id = NEW.task_id;

        IF NEW.status = 'approved' THEN
            v_payment_amount := v_task.bounty_usd * 0.92;
            v_rep_delta := 5;

            UPDATE tasks
            SET status = 'completed',
                completed_at = NOW(),
                updated_at = NOW()
            WHERE id = NEW.task_id;

            UPDATE executors
            SET tasks_completed = tasks_completed + 1,
                reputation_score = LEAST(100, reputation_score + v_rep_delta),
                balance_usdc = balance_usdc + v_payment_amount,
                total_earned_usdc = total_earned_usdc + v_payment_amount,
                last_active_at = NOW(),
                updated_at = NOW()
            WHERE id = NEW.executor_id;

            UPDATE agents
            SET total_tasks_completed = total_tasks_completed + 1,
                total_spent_usdc = total_spent_usdc + v_task.bounty_usd,
                updated_at = NOW()
            WHERE id = v_task.agent_id;

            UPDATE escrows
            SET status = 'released', released_at = NOW()
            WHERE task_id = NEW.task_id;

            INSERT INTO reputation_log (executor_id, task_id, delta, new_score, reason)
            SELECT NEW.executor_id, NEW.task_id, v_rep_delta, e.reputation_score,
                   'Task approved: ' || v_task.title
            FROM executors e WHERE e.id = NEW.executor_id;

        ELSIF NEW.status = 'rejected' THEN
            v_rep_delta := -3;

            UPDATE tasks
            SET status = 'published',
                executor_id = NULL,
                assigned_at = NULL,
                updated_at = NOW()
            WHERE id = NEW.task_id;

            UPDATE executors
            SET reputation_score = GREATEST(0, reputation_score + v_rep_delta),
                updated_at = NOW()
            WHERE id = NEW.executor_id;

            INSERT INTO reputation_log (executor_id, task_id, delta, new_score, reason)
            SELECT NEW.executor_id, NEW.task_id, v_rep_delta, e.reputation_score,
                   'Task rejected: ' || v_task.title
            FROM executors e WHERE e.id = NEW.executor_id;

        ELSIF NEW.status = 'disputed' THEN
            UPDATE tasks
            SET status = 'disputed', updated_at = NOW()
            WHERE id = NEW.task_id;

            UPDATE executors
            SET tasks_disputed = tasks_disputed + 1, updated_at = NOW()
            WHERE id = NEW.executor_id;

            UPDATE escrows
            SET status = 'disputed'
            WHERE task_id = NEW.task_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. Recreate: on_application_status_change (trigger — assignment sets assigned_at)
CREATE OR REPLACE FUNCTION on_application_status_change()
RETURNS TRIGGER AS $$
DECLARE
    v_task tasks%ROWTYPE;
BEGIN
    IF NEW.status = 'accepted' AND OLD.status = 'pending' THEN
        SELECT * INTO v_task FROM tasks WHERE id = NEW.task_id;

        IF v_task.executor_id IS NULL THEN
            UPDATE tasks
            SET status = 'accepted',
                executor_id = NEW.executor_id,
                assigned_at = NOW(),
                updated_at = NOW()
            WHERE id = NEW.task_id
              AND status = 'published';

            UPDATE applications
            SET status = 'rejected',
                rejection_reason = 'Task assigned to another worker',
                reviewed_at = NOW()
            WHERE task_id = NEW.task_id
              AND id != NEW.id
              AND status = 'pending';
        END IF;

        BEGIN
            INSERT INTO notifications (recipient_type, recipient_id, type, title, body, data)
            VALUES ('executor', NEW.executor_id, 'application_accepted', 'Application Accepted',
                    'Your application was accepted for: ' || v_task.title,
                    jsonb_build_object('task_id', NEW.task_id, 'application_id', NEW.id));
        EXCEPTION WHEN undefined_table THEN NULL;
        END;

    ELSIF NEW.status = 'rejected' AND OLD.status = 'pending' THEN
        SELECT * INTO v_task FROM tasks WHERE id = NEW.task_id;

        BEGIN
            INSERT INTO notifications (recipient_type, recipient_id, type, title, body, data)
            VALUES ('executor', NEW.executor_id, 'application_rejected', 'Application Not Selected',
                    'Your application was not selected for: ' || v_task.title,
                    jsonb_build_object('task_id', NEW.task_id, 'application_id', NEW.id,
                                       'reason', NEW.rejection_reason));
        EXCEPTION WHEN undefined_table THEN NULL;
        END;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 6. Recreate: get_executor_dashboard (returns assigned_at in JSON)
CREATE OR REPLACE FUNCTION get_executor_dashboard(p_executor_id UUID)
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
    SELECT * INTO v_executor FROM executors WHERE id = p_executor_id;

    IF v_executor.id IS NULL THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Executor not found');
    END IF;

    SELECT COALESCE(jsonb_agg(task_data), '[]'::jsonb) INTO v_active_tasks
    FROM (
        SELECT jsonb_build_object(
            'id', t.id,
            'title', t.title,
            'bounty_usd', t.bounty_usd,
            'status', t.status,
            'deadline', t.deadline,
            'assigned_at', t.assigned_at
        ) as task_data
        FROM tasks t
        WHERE t.executor_id = p_executor_id
          AND t.status IN ('accepted', 'in_progress', 'submitted', 'verifying')
        ORDER BY t.deadline ASC
        LIMIT 10
    ) at;

    SELECT COALESCE(jsonb_agg(app_data), '[]'::jsonb) INTO v_pending_applications
    FROM (
        SELECT jsonb_build_object(
            'id', a.id,
            'task_id', a.task_id,
            'task_title', t.title,
            'task_bounty', t.bounty_usd,
            'applied_at', a.created_at,
            'status', a.status
        ) as app_data
        FROM applications a
        JOIN tasks t ON t.id = a.task_id
        WHERE a.executor_id = p_executor_id
          AND a.status = 'pending'
        ORDER BY a.created_at DESC
        LIMIT 10
    ) ap;

    SELECT COALESCE(jsonb_agg(sub_data), '[]'::jsonb) INTO v_recent_submissions
    FROM (
        SELECT jsonb_build_object(
            'id', s.id,
            'task_id', s.task_id,
            'task_title', t.title,
            'status', s.status,
            'submitted_at', s.submitted_at,
            'agent_verdict', s.agent_verdict
        ) as sub_data
        FROM submissions s
        JOIN tasks t ON t.id = s.task_id
        WHERE s.executor_id = p_executor_id
        ORDER BY s.submitted_at DESC
        LIMIT 10
    ) sb;

    v_earnings := jsonb_build_object(
        'total_earned', v_executor.total_earned_usdc,
        'balance', v_executor.balance_usdc,
        'tasks_completed', v_executor.tasks_completed
    );

    RETURN jsonb_build_object(
        'success', TRUE,
        'executor', jsonb_build_object(
            'id', v_executor.id,
            'display_name', v_executor.display_name,
            'reputation_score', v_executor.reputation_score,
            'tasks_completed', v_executor.tasks_completed
        ),
        'active_tasks', v_active_tasks,
        'pending_applications', v_pending_applications,
        'recent_submissions', v_recent_submissions,
        'earnings', v_earnings
    );
END;
$$;

COMMIT;
