-- ============================================================================
-- EXECUTION MARKET: API Keys Management
-- Migration: 006_api_keys.sql
-- Description: API keys for agent authentication
-- Version: 1.0.0
-- Date: 2026-01-26
-- ============================================================================

-- ---------------------------------------------------------------------------
-- API KEYS (Agent authentication)
-- ---------------------------------------------------------------------------
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Key data (store hash, not raw key)
    key_hash VARCHAR(64) NOT NULL,  -- SHA256 hash of the API key
    key_prefix VARCHAR(32) NOT NULL, -- First 32 chars for display (em_tier_...)

    -- Agent association
    agent_id VARCHAR(255) NOT NULL,  -- ERC-8004 agent ID or identifier

    -- Tier/access level
    tier VARCHAR(20) NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'starter', 'growth', 'enterprise')),

    -- Organization (for enterprise)
    organization_id UUID,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Usage tracking
    last_used_at TIMESTAMPTZ,
    usage_count INTEGER DEFAULT 0,

    -- Limits (per tier)
    rate_limit_per_minute INTEGER DEFAULT 60,
    monthly_task_limit INTEGER,

    -- Metadata
    name VARCHAR(255),  -- Descriptive name
    description TEXT,
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,  -- Optional expiration

    -- Constraints
    CONSTRAINT api_keys_hash_unique UNIQUE (key_hash),
    CONSTRAINT api_keys_tier_valid CHECK (tier IN ('free', 'starter', 'growth', 'enterprise'))
);

-- Indexes
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_agent ON api_keys(agent_id);
CREATE INDEX idx_api_keys_active ON api_keys(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_api_keys_tier ON api_keys(tier);
CREATE INDEX idx_api_keys_org ON api_keys(organization_id) WHERE organization_id IS NOT NULL;

-- RLS Policies
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- Service role can do everything (for API server)
CREATE POLICY "Service role full access" ON api_keys
    FOR ALL
    USING (auth.role() = 'service_role');

-- Function to update updated_at (if not exists)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update updated_at
CREATE TRIGGER api_keys_updated_at
    BEFORE UPDATE ON api_keys
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ---------------------------------------------------------------------------
-- [REDACTED 2026-04-09 — Phase 0 GR-0.5 / DB-020]
--
-- This migration previously inserted two test API keys with the full
-- plaintext key embedded in SQL comments and key_prefix columns:
--   - chamba_free_*   (free-tier dev key)
--   - chamba_enterprise_*  (enterprise-tier dev key)
--
-- Both keys were leaked via the public git history. The INSERT statements
-- have been removed from this file to prevent re-seeding on future DB
-- recreates, and migration 094_delete_plaintext_api_key.sql deletes any
-- surviving rows from existing databases.
--
-- Do NOT re-introduce plaintext keys in migrations. Use a gitignored seed
-- file (supabase/seeds/local-dev.sql) for local dev data, and AWS Secrets
-- Manager for all production credentials.
--
-- Security audit: docs/reports/security-audit-2026-04-07/
-- Runbook:        docs/reports/security-audit-2026-04-07/RUNBOOK_GR_0_5_credential_rotation.md
-- ---------------------------------------------------------------------------
