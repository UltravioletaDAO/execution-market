-- Migration 096: Ensure disputes.description column exists
--
-- The disputes table (mig 004) defines `description TEXT NOT NULL`, but the live
-- DB is missing it (PostgREST returns PGRST204 when escalation.py inserts).
-- This is a safe idempotent fix -- ADD COLUMN IF NOT EXISTS.
--
-- Also ensures all columns that escalation.py writes to are present:
--   description, status, priority, disputed_amount_usdc, response_deadline,
--   metadata, escalation_tier (mig 091), arbiter_verdict_data (mig 091).
--
-- Ref: ERROR:integrations.arbiter.escalation:Exception creating dispute:
--      Could not find the 'description' column of 'disputes' in the schema cache

-- ============================================================================
-- FIX: Add missing description column
-- ============================================================================

DO $$ BEGIN
    ALTER TABLE disputes ADD COLUMN IF NOT EXISTS description TEXT;
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- Backfill NULLs with empty string for any existing rows (column was NOT NULL in mig 004)
UPDATE disputes SET description = '' WHERE description IS NULL;

-- ============================================================================
-- SAFETY: Ensure other escalation.py columns exist (idempotent)
-- ============================================================================

-- These should already exist from mig 004, but verify:
DO $$ BEGIN
    ALTER TABLE disputes ADD COLUMN IF NOT EXISTS status dispute_status DEFAULT 'open';
EXCEPTION WHEN OTHERS THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE disputes ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 5;
EXCEPTION WHEN OTHERS THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE disputes ADD COLUMN IF NOT EXISTS disputed_amount_usdc DECIMAL(18, 6);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE disputes ADD COLUMN IF NOT EXISTS response_deadline TIMESTAMPTZ;
EXCEPTION WHEN OTHERS THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE disputes ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- These should already exist from mig 091, but verify:
DO $$ BEGIN
    ALTER TABLE disputes ADD COLUMN IF NOT EXISTS escalation_tier INTEGER DEFAULT 2;
EXCEPTION WHEN OTHERS THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE disputes ADD COLUMN IF NOT EXISTS arbiter_verdict_data JSONB;
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- ============================================================================
-- COMPLETION NOTICE
-- ============================================================================

DO $$ BEGIN
    RAISE NOTICE '[OK] Migration 096 applied: disputes.description column ensured present';
END $$;
