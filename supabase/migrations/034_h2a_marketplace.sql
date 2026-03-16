-- Migration 034: H2A Marketplace Support
-- Adds columns for Human-to-Agent task flow
-- Applied: 2026-02-18T03:09:00Z

-- ============================================================================
-- 1. Add publisher_type to tasks (agent = default A2H, human = H2A)
-- ============================================================================
ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS publisher_type VARCHAR(10) DEFAULT 'agent';

DO $$ BEGIN
    ALTER TABLE tasks ADD CONSTRAINT chk_tasks_publisher_type 
    CHECK (publisher_type IN ('agent', 'human'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_tasks_publisher_type 
  ON tasks(publisher_type) WHERE publisher_type = 'human';

-- ============================================================================
-- 2. Add human wallet/user tracking for H2A tasks
-- ============================================================================
ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS human_wallet TEXT;

ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS human_user_id TEXT;

CREATE INDEX IF NOT EXISTS idx_tasks_human_wallet 
  ON tasks(human_wallet) WHERE human_wallet IS NOT NULL;

-- ============================================================================
-- 3. H2A feature flags in platform_config
-- ============================================================================
INSERT INTO platform_config (key, value, category, description)
VALUES 
  ('feature.h2a_enabled', 'true'::jsonb, 'features', 'H2A marketplace enabled'),
  ('feature.h2a_min_bounty', '0.5'::jsonb, 'limits', 'Minimum H2A bounty in USD'),
  ('feature.h2a_max_bounty', '500.0'::jsonb, 'limits', 'Maximum H2A bounty in USD')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
