-- ============================================================================
-- CHAMBA: Platform Configuration System
-- Migration: 007_platform_config.sql
-- Description: Dynamic configuration with caching and audit logging
-- Version: 1.0.0
-- Date: 2026-01-27
-- ============================================================================

-- ---------------------------------------------------------------------------
-- PLATFORM CONFIGURATION TABLE
-- ---------------------------------------------------------------------------
CREATE TABLE platform_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Key-value storage
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL,

    -- Metadata
    description TEXT,
    category VARCHAR(50) NOT NULL,

    -- Access control
    is_public BOOLEAN DEFAULT FALSE,  -- If true, visible via public API

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES auth.users(id)
);

-- Indexes for fast lookup
CREATE INDEX idx_platform_config_key ON platform_config(key);
CREATE INDEX idx_platform_config_category ON platform_config(category);
CREATE INDEX idx_platform_config_public ON platform_config(is_public) WHERE is_public = TRUE;

-- ---------------------------------------------------------------------------
-- CONFIGURATION AUDIT LOG
-- ---------------------------------------------------------------------------
CREATE TABLE config_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- What changed
    config_key VARCHAR(100) NOT NULL,
    old_value JSONB,
    new_value JSONB NOT NULL,

    -- Who changed it
    changed_by UUID REFERENCES auth.users(id),
    reason TEXT,

    -- When
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_config_audit_key ON config_audit_log(config_key);
CREATE INDEX idx_config_audit_time ON config_audit_log(changed_at DESC);

-- ---------------------------------------------------------------------------
-- TRIGGER: Auto-update updated_at and create audit log
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION platform_config_audit()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert audit log entry
    INSERT INTO config_audit_log (config_key, old_value, new_value, changed_by)
    VALUES (NEW.key, OLD.value, NEW.value, NEW.updated_by);

    -- Update timestamp
    NEW.updated_at = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER platform_config_audit_trigger
    BEFORE UPDATE ON platform_config
    FOR EACH ROW
    EXECUTE FUNCTION platform_config_audit();

-- ---------------------------------------------------------------------------
-- RLS POLICIES
-- ---------------------------------------------------------------------------
ALTER TABLE platform_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE config_audit_log ENABLE ROW LEVEL SECURITY;

-- Service role has full access
CREATE POLICY "Service role full access" ON platform_config
    FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role audit access" ON config_audit_log
    FOR ALL
    USING (auth.role() = 'service_role');

-- Public config readable by anyone
CREATE POLICY "Public config readable" ON platform_config
    FOR SELECT
    USING (is_public = TRUE);

-- ---------------------------------------------------------------------------
-- DEFAULT CONFIGURATION VALUES
-- ---------------------------------------------------------------------------
INSERT INTO platform_config (key, value, description, category, is_public) VALUES

-- ==================== FEES ====================
('fees.platform_fee_pct', '0.08',
 'Platform fee as decimal (0.08 = 8%). Deducted from bounty.',
 'fees', false),

('fees.partial_release_pct', '0.30',
 'Partial release percentage on work submission (0.30 = 30%). Worker receives this immediately upon submitting work.',
 'fees', false),

('fees.min_fee_usd', '0.01',
 'Minimum platform fee in USD. Even tiny tasks pay at least this.',
 'fees', false),

('fees.protection_fund_pct', '0.005',
 'Percentage of platform fees allocated to worker protection fund (0.005 = 0.5%).',
 'fees', false),

-- ==================== BOUNTY LIMITS ====================
('bounty.min_usd', '0.25',
 'Minimum bounty in USD. Tasks below this are rejected.',
 'limits', true),

('bounty.max_usd', '10000.00',
 'Maximum bounty in USD per task.',
 'limits', true),

-- ==================== TIMEOUTS ====================
('timeout.approval_hours', '48',
 'Hours for agent to approve/reject after worker submission. After this, auto-releases to worker.',
 'timing', false),

('timeout.task_default_hours', '24',
 'Default task deadline in hours if not specified by agent.',
 'timing', false),

('timeout.auto_release_on_timeout', 'true',
 'If true, automatically release funds to worker when approval times out.',
 'timing', false),

-- ==================== LIMITS ====================
('limits.max_resubmissions', '3',
 'Maximum times a worker can resubmit after rejection.',
 'limits', false),

('limits.max_active_tasks_per_agent', '100',
 'Maximum concurrent active tasks per agent.',
 'limits', false),

('limits.max_applications_per_task', '50',
 'Maximum workers that can apply to a single task.',
 'limits', false),

('limits.max_active_tasks_per_worker', '10',
 'Maximum concurrent accepted tasks per worker.',
 'limits', false),

-- ==================== FEATURE FLAGS ====================
('feature.disputes_enabled', 'true',
 'Enable the dispute resolution system.',
 'features', false),

('feature.reputation_enabled', 'true',
 'Enable reputation scoring for workers.',
 'features', false),

('feature.auto_matching_enabled', 'false',
 'Enable automatic worker matching (experimental).',
 'features', false),

('feature.partial_release_enabled', 'true',
 'Enable partial payment release on submission.',
 'features', false),

('feature.websocket_notifications', 'true',
 'Enable real-time WebSocket notifications.',
 'features', false),

-- ==================== PAYMENT NETWORKS ====================
('x402.supported_networks', '["base", "ethereum", "polygon", "optimism", "arbitrum"]',
 'Supported blockchain networks for payments.',
 'payments', true),

('x402.supported_tokens', '["USDC", "USDT", "DAI"]',
 'Supported payment tokens.',
 'payments', true),

('x402.preferred_network', '"base"',
 'Default network for payments (lower gas fees).',
 'payments', true),

('x402.facilitator_url', '"https://facilitator.ultravioletadao.xyz"',
 'x402 facilitator URL for payment processing.',
 'payments', false),

-- ==================== TREASURY ====================
('treasury.wallet_address', '"0x0000000000000000000000000000000000000000"',
 'Treasury wallet address for platform fees. Must be set before production.',
 'treasury', false),

('treasury.protection_fund_address', '"0x0000000000000000000000000000000000000000"',
 'Worker protection fund wallet address. Must be set before production.',
 'treasury', false);

-- ---------------------------------------------------------------------------
-- HELPER FUNCTION: Get config value with default
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_config(config_key VARCHAR, default_value JSONB DEFAULT NULL)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT value INTO result FROM platform_config WHERE key = config_key;
    RETURN COALESCE(result, default_value);
END;
$$ LANGUAGE plpgsql STABLE;

-- Example usage: SELECT get_config('fees.platform_fee_pct', '0.08'::jsonb);
