-- Migration 064: Webhooks and Webhook Deliveries
-- Enables persistent webhook registration for partners (MeshRelay, agents).
-- Fixes BUG-3: registry.py:481 calls table("webhooks") but table didn't exist.

CREATE TABLE IF NOT EXISTS webhooks (
    webhook_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    secret_hash VARCHAR(64) NOT NULL,
    events JSONB NOT NULL DEFAULT '[]',
    description TEXT DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'paused', 'disabled', 'failed')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_triggered_at TIMESTAMPTZ,
    failure_count INT NOT NULL DEFAULT 0,
    total_deliveries INT NOT NULL DEFAULT 0,
    successful_deliveries INT NOT NULL DEFAULT 0,
    UNIQUE(owner_id, url)
);

CREATE INDEX idx_webhooks_owner ON webhooks(owner_id);
CREATE INDEX idx_webhooks_status ON webhooks(status);

CREATE TABLE IF NOT EXISTS webhook_deliveries (
    delivery_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_id UUID NOT NULL REFERENCES webhooks(webhook_id) ON DELETE CASCADE,
    event_type VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'delivered', 'failed', 'dead_letter')),
    payload JSONB DEFAULT '{}',
    attempts JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_webhook_deliveries_webhook ON webhook_deliveries(webhook_id, created_at DESC);
CREATE INDEX idx_webhook_deliveries_status ON webhook_deliveries(status);

-- RLS: service_role has full access (server-side only)
ALTER TABLE webhooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_deliveries ENABLE ROW LEVEL SECURITY;

CREATE POLICY webhooks_service_all ON webhooks
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY webhook_deliveries_service_all ON webhook_deliveries
    FOR ALL TO service_role USING (true) WITH CHECK (true);
