-- Migration 056: NOT NULL Constraints on Executor Profile Fields
-- Source: DB Optimization Audit 2026-03-15 (Phase 4, Task 4.1)
-- Prevents NULL values in display_name and avg_rating, which cause
-- issues in leaderboard queries and profile display.
-- Applied to production: pending.

-- 1. display_name: prevent NULL profiles in UI
UPDATE executors SET display_name = 'Anonymous' WHERE display_name IS NULL;
ALTER TABLE executors ALTER COLUMN display_name SET NOT NULL;
ALTER TABLE executors ALTER COLUMN display_name SET DEFAULT 'Anonymous';

-- 2. avg_rating: prevent NULL in leaderboard sorting
--    DECIMAL(3,2) range is 0.00 to 9.99, CHECK constrains to 0-5
UPDATE executors SET avg_rating = 0 WHERE avg_rating IS NULL;
ALTER TABLE executors ALTER COLUMN avg_rating SET NOT NULL;
ALTER TABLE executors ALTER COLUMN avg_rating SET DEFAULT 0;
