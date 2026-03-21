-- Migration 050: Reputation Tampering Guard
-- Source: DB Optimization Audit 2026-03-15 (Phase 2, Task 2.1)
-- Prevents non-service_role users from directly modifying immutable
-- executor fields (reputation_score, tier, tasks_completed, etc.).
-- These fields should ONLY be updated by backend triggers/functions.
-- Applied to production: pending.

-- Guard function: rejects direct modification of protected columns
CREATE OR REPLACE FUNCTION prevent_executor_tampering()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.reputation_score IS DISTINCT FROM OLD.reputation_score THEN
        RAISE EXCEPTION 'Cannot modify reputation_score directly — use backend functions';
    END IF;
    IF NEW.tier IS DISTINCT FROM OLD.tier THEN
        RAISE EXCEPTION 'Cannot modify tier directly — managed by update_executor_tier trigger';
    END IF;
    IF NEW.tasks_completed IS DISTINCT FROM OLD.tasks_completed THEN
        RAISE EXCEPTION 'Cannot modify tasks_completed directly — managed by task completion trigger';
    END IF;
    IF NEW.tasks_disputed IS DISTINCT FROM OLD.tasks_disputed THEN
        RAISE EXCEPTION 'Cannot modify tasks_disputed directly';
    END IF;
    IF NEW.tasks_abandoned IS DISTINCT FROM OLD.tasks_abandoned THEN
        RAISE EXCEPTION 'Cannot modify tasks_abandoned directly';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Only fires for non-service_role updates (backend/service_role bypasses this)
-- Note: current_setting('role', true) returns NULL if unset, which != 'service_role'
CREATE TRIGGER guard_executor_immutable_fields
    BEFORE UPDATE ON executors
    FOR EACH ROW
    WHEN (current_setting('role', true) IS DISTINCT FROM 'service_role')
    EXECUTE FUNCTION prevent_executor_tampering();
