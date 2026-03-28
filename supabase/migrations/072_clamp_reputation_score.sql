-- Made idempotent 2026-03-28: safe to re-run on partial application
-- Migration 072: Clamp reputation_score to 0-100 range
--
-- Bug: reputation_score values > 100 found in production (e.g., 120).
-- The guard_executor_immutable_fields trigger (migration 050) prevents
-- direct updates to reputation_score unless role = 'service_role'.
-- We SET ROLE service_role to bypass it during this migration.

-- Step 1: Bypass the guard trigger by assuming service_role
SET LOCAL ROLE service_role;

-- Step 2: Clamp any out-of-range values
UPDATE executors
SET reputation_score = LEAST(100, GREATEST(0, reputation_score))
WHERE reputation_score > 100 OR reputation_score < 0;

-- Step 3: Restore role
RESET ROLE;

-- Step 4: Drop old constraint if it exists (safe to re-add)
ALTER TABLE executors
DROP CONSTRAINT IF EXISTS executors_reputation_score_check;

-- Step 5: Re-add the constraint
ALTER TABLE executors
ADD CONSTRAINT executors_reputation_score_check
CHECK (reputation_score >= 0 AND reputation_score <= 100);
