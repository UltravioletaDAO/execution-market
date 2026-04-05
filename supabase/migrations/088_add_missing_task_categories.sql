-- Migration 088: Add missing task categories
--
-- Python models.py defines 21 task categories but the DB enum only has 11
-- (5 original + 6 from migration 031). This adds the 10 missing human-execution
-- categories to align the DB with the application code.
--
-- Context: External agents hitting POST /api/v1/tasks with category="verification"
-- get 500 errors because the enum value doesn't exist in PostgreSQL.

DO $$ BEGIN ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'location_based'; EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'verification'; EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'social_proof'; EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'data_collection'; EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'sensory'; EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'social'; EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'proxy'; EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'bureaucratic'; EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'emergency'; EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'creative'; EXCEPTION WHEN OTHERS THEN NULL; END $$;
