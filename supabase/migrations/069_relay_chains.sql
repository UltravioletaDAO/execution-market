-- Migration 069: Relay Chains (Multi-Worker Chained Execution)
-- Enables complex tasks that require handoff between workers
-- (e.g., package relay across cities, multi-leg deliveries).

CREATE TABLE IF NOT EXISTS relay_chains (
    chain_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, active, completed, failed
    total_legs INT NOT NULL,
    completed_legs INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS relay_legs (
    leg_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_id UUID NOT NULL REFERENCES relay_chains(chain_id) ON DELETE CASCADE,
    leg_number INT NOT NULL,
    worker_wallet VARCHAR(42),
    worker_nick VARCHAR(64),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- pending, assigned, in_transit, handed_off, completed, failed
    pickup_location JSONB,     -- {lat, lng, address}
    dropoff_location JSONB,    -- {lat, lng, address}
    handoff_code VARCHAR(8),   -- 8-char verification code for QR/manual
    picked_up_at TIMESTAMPTZ,
    handed_off_at TIMESTAMPTZ,
    evidence JSONB DEFAULT '{}',
    bounty_usdc NUMERIC(12,6) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(chain_id, leg_number)
);

CREATE INDEX idx_relay_chains_parent ON relay_chains(parent_task_id);
CREATE INDEX idx_relay_chains_status ON relay_chains(status)
    WHERE status IN ('pending', 'active');
CREATE INDEX idx_relay_legs_chain ON relay_legs(chain_id);
CREATE INDEX idx_relay_legs_worker ON relay_legs(worker_wallet)
    WHERE worker_wallet IS NOT NULL;

-- RLS: service_role full access
ALTER TABLE relay_chains ENABLE ROW LEVEL SECURITY;
ALTER TABLE relay_legs ENABLE ROW LEVEL SECURITY;

CREATE POLICY relay_chains_service_all ON relay_chains
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY relay_legs_service_all ON relay_legs
    FOR ALL TO service_role USING (true) WITH CHECK (true);
