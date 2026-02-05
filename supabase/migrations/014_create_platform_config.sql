-- ============================================================================
-- EXECUTION MARKET: Create platform_config + config_audit_log
-- Migration: 014_create_platform_config.sql
-- Based on: 007_platform_config.sql (never applied to live DB)
-- Changes: updated_by/changed_by are TEXT (not UUID FK) for admin compatibility
-- ============================================================================

-- Platform config table
CREATE TABLE IF NOT EXISTS platform_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT  -- admin actor ID (not FK to auth.users)
);

CREATE INDEX IF NOT EXISTS idx_platform_config_key ON platform_config(key);
CREATE INDEX IF NOT EXISTS idx_platform_config_category ON platform_config(category);

-- Audit log table
CREATE TABLE IF NOT EXISTS config_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key VARCHAR(100) NOT NULL,
    old_value JSONB,
    new_value JSONB NOT NULL,
    changed_by TEXT,  -- admin actor ID
    reason TEXT,
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_config_audit_key ON config_audit_log(config_key);
CREATE INDEX IF NOT EXISTS idx_config_audit_time ON config_audit_log(changed_at DESC);

-- Trigger: auto-update timestamp + audit log + reason
CREATE OR REPLACE FUNCTION platform_config_audit()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO config_audit_log (config_key, old_value, new_value, changed_by, reason)
    VALUES (NEW.key, OLD.value, NEW.value, NEW.updated_by,
            COALESCE(current_setting('app.config_change_reason', true), NULL));
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS platform_config_audit_trigger ON platform_config;
CREATE TRIGGER platform_config_audit_trigger
    BEFORE UPDATE ON platform_config
    FOR EACH ROW
    EXECUTE FUNCTION platform_config_audit();

-- RLS
ALTER TABLE platform_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE config_audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access config" ON platform_config
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role audit access" ON config_audit_log
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Public config readable" ON platform_config
    FOR SELECT USING (is_public = TRUE);

-- Seed default values
INSERT INTO platform_config (key, value, description, category, is_public) VALUES
-- Fees
('fees.platform_fee_pct', '0.08', 'Platform fee (0.08 = 8%)', 'fees', false),
('fees.partial_release_pct', '0.30', 'Partial release on submission (30%)', 'fees', false),
('fees.min_fee_usd', '0.01', 'Minimum platform fee in USD', 'fees', false),
-- Bounty limits
('bounty.min_usd', '0.01', 'Minimum bounty in USD', 'limits', true),
('bounty.max_usd', '10000.00', 'Maximum bounty in USD', 'limits', true),
-- Timeouts
('timeout.approval_hours', '48', 'Hours for agent to approve after submission', 'timing', false),
('timeout.task_default_hours', '24', 'Default task deadline in hours', 'timing', false),
('timeout.auto_release_on_timeout', 'true', 'Auto-release funds on approval timeout', 'timing', false),
-- Limits
('limits.max_resubmissions', '3', 'Max resubmissions after rejection', 'limits', false),
('limits.max_active_tasks_per_agent', '100', 'Max concurrent tasks per agent', 'limits', false),
('limits.max_applications_per_task', '50', 'Max applications per task', 'limits', false),
('limits.max_active_tasks_per_worker', '10', 'Max concurrent tasks per worker', 'limits', false),
-- Features
('feature.disputes_enabled', 'true', 'Enable disputes', 'features', false),
('feature.reputation_enabled', 'true', 'Enable reputation scoring', 'features', false),
('feature.auto_matching_enabled', 'false', 'Enable auto worker matching', 'features', false),
('feature.partial_release_enabled', 'true', 'Enable partial release on submission', 'features', false),
-- Payments
('x402.supported_networks', '["base"]', 'Supported networks', 'payments', true),
('x402.supported_tokens', '["USDC"]', 'Supported tokens', 'payments', true),
('x402.preferred_network', '"base"', 'Default network', 'payments', true),
-- Treasury
('treasury.wallet_address', '"0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad"', 'Treasury wallet', 'treasury', false)
ON CONFLICT (key) DO NOTHING;

-- Helper function
CREATE OR REPLACE FUNCTION get_config(config_key VARCHAR, default_value JSONB DEFAULT NULL)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT value INTO result FROM platform_config WHERE key = config_key;
    RETURN COALESCE(result, default_value);
END;
$$ LANGUAGE plpgsql STABLE;
