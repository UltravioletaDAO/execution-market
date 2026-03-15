-- Fix ratings table to support bidirectional ratings (agent→worker AND worker→agent)
-- The original constraint UNIQUE(executor_id, task_id) only allowed 1 rating per task.
-- We need 2: one where rater_type='agent' and one where rater_type='worker'.

-- Drop the old constraint
ALTER TABLE ratings DROP CONSTRAINT IF EXISTS ratings_unique;

-- Add new constraint that includes rater_type
ALTER TABLE ratings ADD CONSTRAINT ratings_unique_directional
    UNIQUE (executor_id, task_id, rater_type);
