-- ============================================================================
-- EXECUTION MARKET: Human Execution Layer for AI Agents
-- Migration: 010_auto_approve_submissions.sql
-- Description: Auto-approve ALL evidence submissions immediately.
--              Creates payment records so the UI can show payment status.
--              TODO: Replace with proper agent verification later
--              (see docs/planning/TODO-AGENT-VERIFICATION.md)
-- Date: 2026-02-03
-- ============================================================================

-- ============================================================================
-- FUNCTION: Auto-approve submission on INSERT
-- ============================================================================
CREATE OR REPLACE FUNCTION auto_approve_submission()
RETURNS TRIGGER AS $$
DECLARE
    v_task tasks%ROWTYPE;
    v_bounty DECIMAL(10, 2);
    v_worker_payout DECIMAL(10, 2);
    v_fee DECIMAL(10, 2);
BEGIN
    -- Get the associated task
    SELECT * INTO v_task FROM tasks WHERE id = NEW.task_id;
    IF v_task.id IS NULL THEN
        RETURN NEW;
    END IF;

    -- Only auto-approve if no verdict has been set yet
    IF NEW.agent_verdict IS NOT NULL THEN
        RETURN NEW;
    END IF;

    -- 1. Auto-approve the submission
    NEW.agent_verdict := 'accepted';
    NEW.verified_at := NOW();
    NEW.auto_check_passed := true;
    NEW.auto_check_score := 1.00;
    NEW.agent_notes := 'Auto-approved (agent verification pending)';

    -- 2. Calculate payment (8% platform fee)
    v_bounty := v_task.bounty_usd;
    v_fee := ROUND(v_bounty * 0.08, 2);
    v_worker_payout := v_bounty - v_fee;
    NEW.payment_amount := v_worker_payout;

    -- 3. Update task status to completed
    UPDATE tasks
    SET status = 'completed',
        completed_at = NOW()
    WHERE id = NEW.task_id
      AND status IN ('accepted', 'in_progress', 'submitted');

    -- 4. Update executor reputation (+5 for completed task)
    UPDATE executors
    SET reputation_score = COALESCE(reputation_score, 0) + 5
    WHERE id = NEW.executor_id;

    -- 5. Log reputation change
    INSERT INTO reputation_log (executor_id, change, reason, task_id)
    VALUES (NEW.executor_id, 5, 'Task completed (auto-approved)', NEW.task_id);

    -- 6. Create payment record (pending — background job will process)
    INSERT INTO payments (
        task_id,
        executor_id,
        submission_id,
        payment_type,
        status,
        amount_usdc,
        fee_usdc,
        memo,
        created_at
    ) VALUES (
        NEW.task_id,
        NEW.executor_id,
        NEW.id,
        'full_release',
        'pending',
        v_bounty,
        v_fee,
        'Auto-approved submission — payment pending release',
        NOW()
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- TRIGGER: Fire on every submissions INSERT
-- ============================================================================
DROP TRIGGER IF EXISTS submissions_auto_approve ON submissions;

CREATE TRIGGER submissions_auto_approve
    BEFORE INSERT ON submissions
    FOR EACH ROW
    EXECUTE FUNCTION auto_approve_submission();

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON FUNCTION auto_approve_submission() IS
    'Temporary: auto-approves ALL submissions, creates payment record. '
    'TODO: Replace with agent-driven verification (see TODO-AGENT-VERIFICATION.md)';
