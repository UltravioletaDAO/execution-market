-- ============================================================================
-- EXECUTION MARKET: Fix submissions trigger & add task release
-- Migration: 013_fix_submissions_and_task_release.sql
-- Applied: 2026-02-05
--
-- Fixes:
-- 1. Add missing auto_check_score column to submissions
-- 2. Rewrite auto_approve_submission trigger (remove payments table dependency)
-- 3. Fix storage RLS policies for evidence bucket
-- 4. Fix submissions INSERT RLS policy (remove user_id check)
-- 5. Add release_task function (worker can give up accepted task)
-- ============================================================================

-- 1. Add missing column
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS auto_check_score NUMERIC(5,2) DEFAULT 0;

-- 2. Simplify trigger: just update task status to 'submitted', don't auto-approve
-- Agent verification happens via API, not DB trigger
CREATE OR REPLACE FUNCTION auto_approve_submission()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE tasks SET status = 'submitted', updated_at = NOW()
    WHERE id = NEW.task_id AND status IN ('accepted', 'in_progress');
    RETURN NEW;
END;
$$;

-- 3. Fix storage policies
DROP POLICY IF EXISTS "Authenticated users can upload evidence" ON storage.objects;
DROP POLICY IF EXISTS "Evidence viewable by task owner" ON storage.objects;
DROP POLICY IF EXISTS "Users can view own evidence" ON storage.objects;
DROP POLICY IF EXISTS "Users can delete own evidence" ON storage.objects;
DROP POLICY IF EXISTS "Anyone can upload evidence" ON storage.objects;
DROP POLICY IF EXISTS "Evidence is readable" ON storage.objects;
DROP POLICY IF EXISTS "Evidence deletable by owner" ON storage.objects;

CREATE POLICY "Anyone can upload evidence" ON storage.objects
    FOR INSERT TO authenticated, anon WITH CHECK (bucket_id = 'evidence');
CREATE POLICY "Evidence is readable" ON storage.objects
    FOR SELECT TO authenticated, anon USING (bucket_id = 'evidence');
CREATE POLICY "Evidence deletable by owner" ON storage.objects
    FOR DELETE TO authenticated USING (bucket_id = 'evidence');

-- 4. Fix submissions INSERT policy
DROP POLICY IF EXISTS "Executors can insert submissions for accepted tasks" ON submissions;
DROP POLICY IF EXISTS "Executors can insert submissions" ON submissions;
CREATE POLICY "Executors can insert submissions" ON submissions
    FOR INSERT TO public WITH CHECK (executor_id IN (SELECT id FROM executors));

-- 5. Add release_task function
CREATE OR REPLACE FUNCTION release_task(p_task_id UUID, p_executor_id UUID)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path TO 'public' AS $$
DECLARE
    v_task_status TEXT;
    v_task_executor UUID;
BEGIN
    SELECT status, executor_id INTO v_task_status, v_task_executor
    FROM tasks WHERE id = p_task_id FOR UPDATE;

    IF v_task_status IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task not found');
    END IF;
    IF v_task_executor != p_executor_id THEN
        RETURN jsonb_build_object('success', false, 'error', 'Not assigned to you');
    END IF;
    IF v_task_status NOT IN ('accepted', 'in_progress') THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task cannot be released in current status');
    END IF;

    UPDATE tasks SET status = 'published', executor_id = NULL, accepted_at = NULL, updated_at = NOW()
    WHERE id = p_task_id;

    UPDATE task_applications SET status = 'released', updated_at = NOW()
    WHERE task_id = p_task_id AND executor_id = p_executor_id AND status = 'accepted';

    RETURN jsonb_build_object('success', true, 'message', 'Task released back to marketplace');
END;
$$;

GRANT EXECUTE ON FUNCTION release_task(UUID, UUID) TO anon;
GRANT EXECUTE ON FUNCTION release_task(UUID, UUID) TO authenticated;
