-- Migration 028: ERC-8004 Side Effects outbox table
-- Tracks reputation and identity side effects triggered by task lifecycle events.
-- Uses outbox pattern: enqueue on event, process asynchronously with retry.

CREATE TABLE IF NOT EXISTS erc8004_side_effects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    effect_type TEXT NOT NULL CHECK (effect_type IN (
        'register_worker_identity',
        'rate_worker_from_agent',
        'rate_agent_from_worker',
        'rate_worker_on_rejection'
    )),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'success', 'failed', 'skipped')),
    attempts INTEGER NOT NULL DEFAULT 0,
    tx_hash TEXT,
    score INTEGER CHECK (score >= 0 AND score <= 100),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (submission_id, effect_type)
);

-- Index for retry queries: pending/failed effects ordered by creation
CREATE INDEX IF NOT EXISTS idx_side_effects_retry
    ON erc8004_side_effects(status, created_at)
    WHERE status IN ('pending', 'failed');

-- Index for submission lookup
CREATE INDEX IF NOT EXISTS idx_side_effects_submission
    ON erc8004_side_effects(submission_id);

-- Trigger: auto-update updated_at on modification
CREATE OR REPLACE FUNCTION update_side_effects_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS side_effects_updated_at ON erc8004_side_effects;
CREATE TRIGGER side_effects_updated_at
    BEFORE UPDATE ON erc8004_side_effects
    FOR EACH ROW
    EXECUTE FUNCTION update_side_effects_timestamp();

-- RLS: server-side only (service key access)
ALTER TABLE erc8004_side_effects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on erc8004_side_effects"
    ON erc8004_side_effects
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Feature flags for ERC-8004 reputation integration (all default false)
INSERT INTO platform_config (key, value, description, category, is_public) VALUES
    ('feature.erc8004_auto_register_worker_enabled', 'false', 'Auto-register workers on ERC-8004 Identity Registry on first task completion', 'features', false),
    ('feature.erc8004_auto_rate_agent_enabled', 'false', 'Workers auto-rate agents on ERC-8004 after task completion', 'features', false),
    ('feature.erc8004_rejection_feedback_enabled', 'false', 'Record negative reputation feedback on task rejection', 'features', false),
    ('feature.erc8004_dynamic_scoring_enabled', 'false', 'Use dynamic scoring engine for reputation scores', 'features', false),
    ('feature.erc8004_mcp_tools_enabled', 'false', 'Expose ERC-8004 reputation MCP tools to agents', 'features', false)
ON CONFLICT (key) DO NOTHING;

COMMENT ON TABLE erc8004_side_effects IS 'Outbox for ERC-8004 reputation and identity side effects (register, rate, feedback)';
COMMENT ON COLUMN erc8004_side_effects.effect_type IS 'register_worker_identity | rate_worker_from_agent | rate_agent_from_worker | rate_worker_on_rejection';
COMMENT ON COLUMN erc8004_side_effects.status IS 'pending | success | failed | skipped';
COMMENT ON COLUMN erc8004_side_effects.score IS 'Reputation score 0-100 (used for rate_* effects)';
COMMENT ON COLUMN erc8004_side_effects.payload IS 'Effect-specific data (task_id, worker_wallet, agent_id, network, etc.)';
