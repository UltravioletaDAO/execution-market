-- Migration 065: IRC Identity System
-- 4-level trust: 0=ANONYMOUS, 1=LINKED, 2=VERIFIED, 3=REGISTERED
-- Enables persistent IRC nick <-> wallet <-> ERC-8004 binding.

CREATE TABLE IF NOT EXISTS irc_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    irc_nick VARCHAR(64) NOT NULL,
    wallet_address VARCHAR(42) NOT NULL,
    trust_level INT NOT NULL DEFAULT 1
        CHECK (trust_level BETWEEN 0 AND 3),
    -- 0=ANONYMOUS, 1=LINKED, 2=VERIFIED (sig), 3=REGISTERED (ERC-8004)
    nickserv_account VARCHAR(64),
    agent_id INT,  -- ERC-8004 agent ID (level 3 only)
    challenge_nonce VARCHAR(64),
    challenge_expires_at TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ DEFAULT now(),
    preferred_channel VARCHAR(10) DEFAULT 'both'
        CHECK (preferred_channel IN ('irc', 'xmtp', 'both')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(irc_nick),
    UNIQUE(wallet_address)
);

CREATE INDEX idx_irc_identities_wallet ON irc_identities(wallet_address);
CREATE INDEX idx_irc_identities_trust ON irc_identities(trust_level);
CREATE INDEX idx_irc_identities_agent ON irc_identities(agent_id) WHERE agent_id IS NOT NULL;

-- RLS: service_role full access (server-side only)
ALTER TABLE irc_identities ENABLE ROW LEVEL SECURITY;

CREATE POLICY irc_identities_service_all ON irc_identities
    FOR ALL TO service_role USING (true) WITH CHECK (true);
