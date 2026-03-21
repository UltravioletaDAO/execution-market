-- ============================================================================
-- Migration 010: Split apply_to_task — application only, no auto-assign
-- ============================================================================
-- BUG FIX: When workers apply from the web dashboard, apply_to_task() was
-- auto-assigning the task (status='accepted') directly in Postgres. This
-- bypassed the Python REST API where escrow lock code lives, so escrow
-- was never created on-chain.
--
-- FIX: apply_to_task() now ONLY creates an application with status='pending'.
-- The task stays 'published' until the agent calls POST /tasks/{id}/assign
-- on the backend, which handles both assignment AND escrow locking.
--
-- Flow after this migration:
--   Worker clicks "Apply" → apply_to_task() → application(status='pending')
--   Agent sees application → POST /assign → task assigned + escrow locked
-- ============================================================================

BEGIN;

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
    v_application_id UUID;
BEGIN
    -- Validate task exists
    SELECT * INTO v_task FROM tasks WHERE id = p_task_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Task not found');
    END IF;

    -- Task must be published (or accepted — allow multiple applications)
    IF v_task.status NOT IN ('published') THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Task is not available for applications');
    END IF;

    -- Validate executor exists
    SELECT * INTO v_executor FROM executors WHERE id = p_executor_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Executor not found');
    END IF;

    -- Cannot apply to own task
    IF v_executor.wallet_address IS NOT NULL
       AND lower(v_executor.wallet_address) = lower(v_task.agent_id) THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Cannot apply to your own task');
    END IF;

    -- Reputation check
    IF v_executor.reputation_score < v_task.min_reputation THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Insufficient reputation');
    END IF;

    -- Duplicate application check
    IF EXISTS (
        SELECT 1 FROM applications
        WHERE task_id = p_task_id AND executor_id = p_executor_id
    ) THEN
        RETURN jsonb_build_object('success', FALSE, 'error', 'Already applied to this task');
    END IF;

    -- ONLY create the application — do NOT auto-assign the task
    INSERT INTO applications (task_id, executor_id, message, status)
    VALUES (p_task_id, p_executor_id, p_message, 'pending')
    RETURNING id INTO v_application_id;

    RETURN jsonb_build_object(
        'success', TRUE,
        'application_id', v_application_id,
        'task_id', p_task_id,
        'executor_id', p_executor_id,
        'status', 'pending'
    );
END;
$$;

COMMIT;
