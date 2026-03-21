-- Migration 067: Worker Availability Pool
-- Workers broadcast availability by city/category for geographic discovery.
-- Powers /available, /unavailable, /who commands and task cross-posting.

CREATE TABLE IF NOT EXISTS worker_availability (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_address VARCHAR(42) NOT NULL,
    irc_nick VARCHAR(64),
    city VARCHAR(100),
    country VARCHAR(100),
    region VARCHAR(100),
    categories TEXT[] DEFAULT '{}',
    available_until TIMESTAMPTZ,
    last_ping TIMESTAMPTZ DEFAULT now(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(wallet_address)
);

CREATE INDEX idx_worker_availability_city ON worker_availability(city);
CREATE INDEX idx_worker_availability_until ON worker_availability(available_until)
    WHERE available_until IS NOT NULL;

-- RLS: service_role full access
ALTER TABLE worker_availability ENABLE ROW LEVEL SECURITY;

CREATE POLICY worker_availability_service_all ON worker_availability
    FOR ALL TO service_role USING (true) WITH CHECK (true);
