-- Migration 034: Extended Executor Profile Columns
-- Adds pricing JSONB column used by agent directory
-- bio, avatar_url, is_verified already exist from migration 001
-- Applied: 2026-02-18

-- ============================================================================
-- 1. Add pricing column (JSONB for flexible agent pricing info)
-- ============================================================================
ALTER TABLE executors
  ADD COLUMN IF NOT EXISTS pricing JSONB;

COMMENT ON COLUMN executors.pricing IS 'Agent pricing info: min_bounty_usd, max_bounty_usd, avg_response_minutes';
