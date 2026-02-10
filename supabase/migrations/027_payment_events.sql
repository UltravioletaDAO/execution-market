-- Migration 027: Payment Events audit trail
-- Tracks every payment-related action for debugging and forensics.
-- Created in response to fund loss bug where $1.404 USDC was settled
-- to treasury instead of platform wallet, with no audit trail.

CREATE TABLE IF NOT EXISTS payment_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES tasks(id),
    event_type TEXT NOT NULL,  -- verify, store_auth, settle, disburse_worker, disburse_fee, refund, cancel, error
    created_at TIMESTAMPTZ DEFAULT now(),
    tx_hash TEXT,
    from_address TEXT,
    to_address TEXT,
    amount_usdc NUMERIC(20,6),
    network TEXT,
    token TEXT DEFAULT 'USDC',
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, success, failed
    error TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Index for querying events by task (most common access pattern)
CREATE INDEX IF NOT EXISTS idx_payment_events_task ON payment_events(task_id, created_at);

-- Index for querying events by type (admin dashboard, debugging)
CREATE INDEX IF NOT EXISTS idx_payment_events_type ON payment_events(event_type, created_at);

-- Index for querying by tx_hash (on-chain forensics)
CREATE INDEX IF NOT EXISTS idx_payment_events_tx ON payment_events(tx_hash) WHERE tx_hash IS NOT NULL;

-- RLS: payment_events are server-side only (service key access)
ALTER TABLE payment_events ENABLE ROW LEVEL SECURITY;

-- Allow service role full access (MCP server uses service key)
CREATE POLICY "Service role full access on payment_events"
    ON payment_events
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

COMMENT ON TABLE payment_events IS 'Audit trail for all payment operations (verify, settle, disburse, refund, cancel)';
COMMENT ON COLUMN payment_events.event_type IS 'verify | store_auth | settle | disburse_worker | disburse_fee | refund | cancel | error';
COMMENT ON COLUMN payment_events.status IS 'pending | success | failed';
