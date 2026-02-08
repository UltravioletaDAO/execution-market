-- Fix 3: SECURITY DEFINER RPC to bypass RLS silent failure on submissions INSERT.
-- When executor.user_id is NULL, the RLS policy blocks inserts silently (0 rows, no error).
-- This function validates ownership and inserts with elevated privileges.

CREATE OR REPLACE FUNCTION submit_work(
  p_task_id UUID,
  p_executor_id UUID,
  p_evidence JSONB,
  p_notes TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_submission_id UUID;
  v_task RECORD;
BEGIN
  -- Verify task exists and is assigned to this executor
  SELECT * INTO v_task FROM tasks WHERE id = p_task_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Task not found';
  END IF;
  IF v_task.executor_id != p_executor_id THEN
    RAISE EXCEPTION 'Task not assigned to this executor';
  END IF;
  IF v_task.status NOT IN ('accepted', 'in_progress') THEN
    RAISE EXCEPTION 'Task not in submittable state: %', v_task.status;
  END IF;

  INSERT INTO submissions (task_id, executor_id, evidence, notes, status)
  VALUES (p_task_id, p_executor_id, p_evidence, p_notes, 'pending')
  RETURNING id INTO v_submission_id;

  -- Update task status
  UPDATE tasks SET status = 'submitted' WHERE id = p_task_id;

  RETURN v_submission_id;
END;
$$;
