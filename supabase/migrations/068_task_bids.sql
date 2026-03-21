-- Migration 068: Task Bids (Reverse Auction System)
-- Workers bid on auction-mode tasks. Publisher selects best bid.
-- Powers /bid, /select-bid commands and auction lifecycle.

CREATE TABLE IF NOT EXISTS task_bids (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    wallet_address VARCHAR(42) NOT NULL,
    irc_nick VARCHAR(64),
    amount_usdc NUMERIC(12,6) NOT NULL,
    message TEXT DEFAULT '',
    eta_minutes INT,
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, selected, rejected, expired
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(task_id, wallet_address)
);

CREATE INDEX idx_task_bids_task_id ON task_bids(task_id);
CREATE INDEX idx_task_bids_status ON task_bids(status) WHERE status = 'active';

-- RLS: service_role full access
ALTER TABLE task_bids ENABLE ROW LEVEL SECURITY;

CREATE POLICY task_bids_service_all ON task_bids
    FOR ALL TO service_role USING (true) WITH CHECK (true);
