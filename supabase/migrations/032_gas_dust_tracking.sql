-- 032: Gas Dust Tracking
--
-- Tracks when workers receive gas dust (tiny ETH amount) for on-chain
-- reputation transactions. Workers sign giveFeedback() directly from
-- their wallet, so they need a small amount of ETH for gas.
--
-- Anti-farming: one funding per wallet, monthly budget cap, rate limiting.

ALTER TABLE executors ADD COLUMN IF NOT EXISTS gas_dust_funded_at TIMESTAMPTZ DEFAULT NULL;

CREATE TABLE IF NOT EXISTS gas_dust_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    executor_id UUID REFERENCES executors(id),
    wallet_address TEXT NOT NULL,
    amount_eth NUMERIC(20,18) NOT NULL,
    tx_hash TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    network TEXT DEFAULT 'base',
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for budget queries (monthly aggregation)
CREATE INDEX IF NOT EXISTS idx_gas_dust_events_created_at ON gas_dust_events(created_at);
-- Index for rate limiting (per-hour count)
CREATE INDEX IF NOT EXISTS idx_gas_dust_events_status ON gas_dust_events(status, created_at);
