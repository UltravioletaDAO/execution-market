-- Migration 072: Clamp reputation_score to 0-100 range
--
-- Bug: reputation_score values > 100 found in production (e.g., 120).
-- The original CHECK constraint (migration 001) may have been dropped or
-- bypassed by RPC functions that update the column directly.
--
-- Fix: Clamp existing values and re-add the constraint.

-- Step 1: Clamp any out-of-range values
UPDATE executors
SET reputation_score = LEAST(100, GREATEST(0, reputation_score))
WHERE reputation_score > 100 OR reputation_score < 0;

-- Step 2: Drop old constraint if it exists (safe to re-add)
ALTER TABLE executors
DROP CONSTRAINT IF EXISTS executors_reputation_score_check;

-- Step 3: Re-add the constraint
ALTER TABLE executors
ADD CONSTRAINT executors_reputation_score_check
CHECK (reputation_score >= 0 AND reputation_score <= 100);
