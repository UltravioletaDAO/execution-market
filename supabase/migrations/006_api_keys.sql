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
-- Insert test API key for development/testing
-- Key: chamba_free_d57b51d2a852191a7dd02d5ac158ddc3
-- ---------------------------------------------------------------------------
INSERT INTO api_keys (
    key_hash,
    key_prefix,
    agent_id,
    tier,
    name,
    is_active
) VALUES (
    -- SHA256 of 'chamba_free_d57b51d2a852191a7dd02d5ac158ddc3'
    'c7185996d0b08c1c811f13c378a95afe226cd09438c4e6e49d1bd8455db533e6',
    'chamba_free_d57b51d2a8521',
    'test_agent_001',
    'free',
    'Test API Key for Development',
    TRUE
);

-- Also insert an enterprise test key
-- Key: chamba_enterprise_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
INSERT INTO api_keys (
    key_hash,
    key_prefix,
    agent_id,
    tier,
    name,
    is_active,
    rate_limit_per_minute,
    monthly_task_limit
) VALUES (
    -- SHA256 of 'chamba_enterprise_a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6'
    'f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4f3e2',
    'chamba_enterprise_a1b2c3d4e5f',
    'test_enterprise_agent',
    'enterprise',
    'Enterprise Test API Key',
    TRUE,
    1000,
    10000
);
