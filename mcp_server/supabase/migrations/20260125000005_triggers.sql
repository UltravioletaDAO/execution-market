-- Chamba MCP Server: Triggers for Automated Operations
-- Migration: 20260125000005_triggers.sql
-- Description: Triggers for status updates, reputation, and notifications

-- ============================================
-- TASK STATUS TRIGGERS
-- ============================================

-- Update task status when submission is created
CREATE OR REPLACE FUNCTION on_submission_created()
RETURNS TRIGGER AS $$
BEGIN
    -- Update task to 'submitted' status
    UPDATE tasks
    SET
        status = 'submitted',
        updated_at = NOW()
    WHERE id = NEW.task_id
      AND status IN ('accepted', 'in_progress');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_on_submission_created
    AFTER INSERT ON submissions
    FOR EACH ROW
    EXECUTE FUNCTION on_submission_created();

-- Handle submission verdict and update task/executor
CREATE OR REPLACE FUNCTION on_submission_verdict()
RETURNS TRIGGER AS $$
DECLARE
    v_task tasks%ROWTYPE;
    v_payment_amount DECIMAL;
    v_rep_delta INTEGER;
BEGIN
    -- Only process when status changes from pending
    IF OLD.status = 'pending' AND NEW.status != 'pending' THEN

        -- Get the task
        SELECT * INTO v_task FROM tasks WHERE id = NEW.task_id;

        IF NEW.status = 'approved' THEN
            -- Calculate payment (92% of bounty - 8% platform fee)
            v_payment_amount := v_task.bounty_usd * 0.92;
            v_rep_delta := 5;  -- +5 reputation for approved task

            -- Update task to completed
            UPDATE tasks
            SET
                status = 'completed',
                completed_at = NOW(),
                updated_at = NOW()
            WHERE id = NEW.task_id;

            -- Update executor stats and balance
            UPDATE executors
            SET
                tasks_completed = tasks_completed + 1,
                reputation_score = LEAST(100, reputation_score + v_rep_delta),
                balance_usdc = balance_usdc + v_payment_amount,
                total_earned_usdc = total_earned_usdc + v_payment_amount,
                last_active_at = NOW(),
                updated_at = NOW()
            WHERE id = NEW.executor_id;

            -- Update agent stats
            UPDATE agents
            SET
                total_tasks_completed = total_tasks_completed + 1,
                total_spent_usdc = total_spent_usdc + v_task.bounty_usd,
                updated_at = NOW()
            WHERE id = v_task.agent_id;

            -- Update escrow status
            UPDATE escrows
            SET
                status = 'released',
                released_at = NOW()
            WHERE task_id = NEW.task_id;

            -- Log reputation change
            INSERT INTO reputation_log (
                executor_id, task_id, delta, new_score, reason
            )
            SELECT
                NEW.executor_id,
                NEW.task_id,
                v_rep_delta,
                e.reputation_score,
                'Task approved: ' || v_task.title
            FROM executors e WHERE e.id = NEW.executor_id;

        ELSIF NEW.status = 'rejected' THEN
            v_rep_delta := -3;  -- -3 reputation for rejected task

            -- Reopen task for new applications
            UPDATE tasks
            SET
                status = 'published',
                executor_id = NULL,
                accepted_at = NULL,
                updated_at = NOW()
            WHERE id = NEW.task_id;

            -- Update executor reputation
            UPDATE executors
            SET
                reputation_score = GREATEST(0, reputation_score + v_rep_delta),
                updated_at = NOW()
            WHERE id = NEW.executor_id;

            -- Log reputation change
            INSERT INTO reputation_log (
                executor_id, task_id, delta, new_score, reason
            )
            SELECT
                NEW.executor_id,
                NEW.task_id,
                v_rep_delta,
                e.reputation_score,
                'Task rejected: ' || v_task.title
            FROM executors e WHERE e.id = NEW.executor_id;

        ELSIF NEW.status = 'disputed' THEN
            -- Update task to disputed
            UPDATE tasks
            SET
                status = 'disputed',
                updated_at = NOW()
            WHERE id = NEW.task_id;

            -- Update executor disputed count
            UPDATE executors
            SET
                tasks_disputed = tasks_disputed + 1,
                updated_at = NOW()
            WHERE id = NEW.executor_id;

            -- Freeze escrow
            UPDATE escrows
            SET status = 'disputed'
            WHERE task_id = NEW.task_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_on_submission_verdict
    AFTER UPDATE OF status ON submissions
    FOR EACH ROW
    WHEN (OLD.status = 'pending' AND NEW.status != 'pending')
    EXECUTE FUNCTION on_submission_verdict();

-- ============================================
-- APPLICATION TRIGGERS
-- ============================================

-- Notify agent when new application is received
CREATE OR REPLACE FUNCTION on_application_created()
RETURNS TRIGGER AS $$
DECLARE
    v_task tasks%ROWTYPE;
    v_executor executors%ROWTYPE;
BEGIN
    -- Get task and executor info
    SELECT * INTO v_task FROM tasks WHERE id = NEW.task_id;
    SELECT * INTO v_executor FROM executors WHERE id = NEW.executor_id;

    -- Create notification record (if notifications table exists)
    BEGIN
        INSERT INTO notifications (
            recipient_type,
            recipient_id,
            type,
            title,
            body,
            data
        ) VALUES (
            'agent',
            v_task.agent_id,
            'new_application',
            'New Application',
            v_executor.display_name || ' applied to: ' || v_task.title,
            jsonb_build_object(
                'task_id', NEW.task_id,
                'application_id', NEW.id,
                'executor_id', NEW.executor_id,
                'executor_name', v_executor.display_name,
                'reputation_score', v_executor.reputation_score
            )
        );
    EXCEPTION WHEN undefined_table THEN
        -- notifications table doesn't exist, skip
        NULL;
    END;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_on_application_created
    AFTER INSERT ON applications
    FOR EACH ROW
    EXECUTE FUNCTION on_application_created();

-- Handle application status change
CREATE OR REPLACE FUNCTION on_application_status_change()
RETURNS TRIGGER AS $$
DECLARE
    v_task tasks%ROWTYPE;
BEGIN
    IF NEW.status = 'accepted' AND OLD.status = 'pending' THEN
        -- Get task
        SELECT * INTO v_task FROM tasks WHERE id = NEW.task_id;

        -- Assign task to executor if not already assigned
        IF v_task.executor_id IS NULL THEN
            UPDATE tasks
            SET
                status = 'accepted',
                executor_id = NEW.executor_id,
                accepted_at = NOW(),
                updated_at = NOW()
            WHERE id = NEW.task_id
              AND status = 'published';

            -- Reject other pending applications
            UPDATE applications
            SET
                status = 'rejected',
                rejection_reason = 'Task assigned to another worker',
                reviewed_at = NOW()
            WHERE task_id = NEW.task_id
              AND id != NEW.id
              AND status = 'pending';
        END IF;

        -- Notify executor (if notifications table exists)
        BEGIN
            INSERT INTO notifications (
                recipient_type,
                recipient_id,
                type,
                title,
                body,
                data
            ) VALUES (
                'executor',
                NEW.executor_id,
                'application_accepted',
                'Application Accepted',
                'Your application was accepted for: ' || v_task.title,
                jsonb_build_object(
                    'task_id', NEW.task_id,
                    'application_id', NEW.id
                )
            );
        EXCEPTION WHEN undefined_table THEN
            NULL;
        END;

    ELSIF NEW.status = 'rejected' AND OLD.status = 'pending' THEN
        -- Get task
        SELECT * INTO v_task FROM tasks WHERE id = NEW.task_id;

        -- Notify executor of rejection
        BEGIN
            INSERT INTO notifications (
                recipient_type,
                recipient_id,
                type,
                title,
                body,
                data
            ) VALUES (
                'executor',
                NEW.executor_id,
                'application_rejected',
                'Application Not Selected',
                'Your application was not selected for: ' || v_task.title,
                jsonb_build_object(
                    'task_id', NEW.task_id,
                    'application_id', NEW.id,
                    'reason', NEW.rejection_reason
                )
            );
        EXCEPTION WHEN undefined_table THEN
            NULL;
        END;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_on_application_status_change
    AFTER UPDATE OF status ON applications
    FOR EACH ROW
    WHEN (OLD.status = 'pending' AND NEW.status != 'pending')
    EXECUTE FUNCTION on_application_status_change();

-- ============================================
-- ESCROW TRIGGERS
-- ============================================

-- Link escrow to task
CREATE OR REPLACE FUNCTION link_escrow_to_task()
RETURNS TRIGGER AS $$
BEGIN
    -- Update task with escrow reference
    UPDATE tasks
    SET
        escrow_id = NEW.id,
        updated_at = NOW()
    WHERE id = NEW.task_id
      AND escrow_id IS NULL;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_link_escrow_to_task
    AFTER INSERT ON escrows
    FOR EACH ROW
    EXECUTE FUNCTION link_escrow_to_task();

-- ============================================
-- TASK EXPIRATION
-- ============================================

-- Function to expire tasks past deadline (called by cron)
CREATE OR REPLACE FUNCTION expire_overdue_tasks()
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    WITH expired AS (
        UPDATE tasks
        SET
            status = 'expired',
            updated_at = NOW()
        WHERE status IN ('published', 'accepted', 'in_progress')
          AND deadline < NOW()
        RETURNING id, executor_id
    )
    SELECT COUNT(*) INTO v_count FROM expired;

    -- Handle abandoned tasks (executor had task but didn't complete)
    UPDATE executors
    SET
        tasks_abandoned = tasks_abandoned + 1,
        reputation_score = GREATEST(0, reputation_score - 5),
        updated_at = NOW()
    WHERE id IN (
        SELECT DISTINCT executor_id
        FROM tasks
        WHERE status = 'expired'
          AND executor_id IS NOT NULL
          AND updated_at > NOW() - interval '1 minute'  -- Just updated
    );

    -- Refund escrows for expired tasks
    UPDATE escrows
    SET
        status = 'refunded',
        refunded_at = NOW()
    WHERE task_id IN (
        SELECT id FROM tasks
        WHERE status = 'expired'
          AND updated_at > NOW() - interval '1 minute'
    )
    AND status IN ('active', 'pending');

    RETURN v_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- AGENT STATS UPDATE
-- ============================================

-- Update agent monthly task count
CREATE OR REPLACE FUNCTION update_agent_task_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.status = 'published' THEN
        UPDATE agents
        SET
            total_tasks_created = total_tasks_created + 1,
            tasks_created_this_month = tasks_created_this_month + 1,
            updated_at = NOW()
        WHERE id = NEW.agent_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_update_agent_task_count
    AFTER INSERT ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_agent_task_count();

-- Reset monthly task count (called by cron on 1st of month)
CREATE OR REPLACE FUNCTION reset_monthly_task_counts()
RETURNS void AS $$
BEGIN
    UPDATE agents
    SET
        tasks_created_this_month = 0,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- REPUTATION LOG TABLE (AUDIT)
-- ============================================

-- Create reputation_log table if it doesn't exist
CREATE TABLE IF NOT EXISTS reputation_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    executor_id UUID NOT NULL REFERENCES executors(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    delta INTEGER NOT NULL,
    new_score INTEGER NOT NULL,
    reason VARCHAR(255) NOT NULL,
    tx_hash VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reputation_log_executor
    ON reputation_log(executor_id);

CREATE INDEX IF NOT EXISTS idx_reputation_log_created
    ON reputation_log(created_at DESC);

-- RLS for reputation_log
ALTER TABLE reputation_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "reputation_log_select_public"
    ON reputation_log
    FOR SELECT
    USING (TRUE);

CREATE POLICY "reputation_log_service_role"
    ON reputation_log
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- ============================================
-- NOTIFICATIONS TABLE (OPTIONAL)
-- ============================================

-- Create notifications table if it doesn't exist
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_type VARCHAR(50) NOT NULL,  -- 'agent' or 'executor'
    recipient_id UUID NOT NULL,
    type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT,
    data JSONB DEFAULT '{}',
    read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_recipient
    ON notifications(recipient_type, recipient_id);

CREATE INDEX IF NOT EXISTS idx_notifications_unread
    ON notifications(recipient_type, recipient_id, created_at DESC)
    WHERE read = FALSE;

-- RLS for notifications
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "notifications_select_executor"
    ON notifications
    FOR SELECT
    USING (
        recipient_type = 'executor'
        AND recipient_id = get_current_executor_id()
    );

CREATE POLICY "notifications_update_executor"
    ON notifications
    FOR UPDATE
    USING (
        recipient_type = 'executor'
        AND recipient_id = get_current_executor_id()
    );

CREATE POLICY "notifications_service_role"
    ON notifications
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON FUNCTION on_submission_created IS 'Updates task status when evidence is submitted';
COMMENT ON FUNCTION on_submission_verdict IS 'Processes approval/rejection and updates reputation';
COMMENT ON FUNCTION on_application_created IS 'Notifies agent of new task application';
COMMENT ON FUNCTION on_application_status_change IS 'Handles task assignment when application is accepted';
COMMENT ON FUNCTION expire_overdue_tasks IS 'Expires tasks past deadline and handles abandonments';
COMMENT ON TABLE reputation_log IS 'Audit trail for all reputation changes';
COMMENT ON TABLE notifications IS 'In-app notifications for agents and executors';
