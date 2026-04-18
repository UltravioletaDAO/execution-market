-- Migration 102: EIP-3009 nonce persistence + collision guard (Task 5.1).
--
-- Why:
--   Every signed pre-auth carries a `nonce` (32 random bytes). The value is
--   currently serialised into the X-Payment-Auth payload and embedded in
--   `escrows.metadata.preauth_signature`, but is NOT surfaced as a first-class
--   field — which makes "was this nonce used twice?" queries require a
--   full-table JSON scan.
--
--   Collision is astronomical with 256 bits of entropy from `secrets.token_hex`,
--   BUT the UNIQUE partial index below also guards against:
--     - a bug in nonce generation that reintroduces state across signs.
--     - an attacker replaying a captured X-Payment-Auth against a different
--       task (would still be rejected on-chain by EIP-3009, but we want the
--       server to notice BEFORE relaying to the Facilitator).
--
--   The index is scoped with `WHERE (metadata ->> 'nonce') IS NOT NULL` so
--   legacy rows that never carried a nonce (balance_check, fee_sweep, etc.)
--   don't trigger false positives.
--
-- Safe to re-run — uses CREATE INDEX IF NOT EXISTS.

-- NOTE: Supabase SQL editor wraps migrations in a transaction, so we cannot
-- use CONCURRENTLY here. The payment_events table is small (< 50k rows
-- today), so a brief lock is acceptable.

CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_events_nonce_unique
    ON payment_events ((metadata ->> 'nonce'), (metadata ->> 'token_address'))
    WHERE (metadata ->> 'nonce') IS NOT NULL;

COMMENT ON INDEX idx_payment_events_nonce_unique IS
    'Guards against EIP-3009 nonce reuse within the same stablecoin contract. Partial — only rows with metadata.nonce set are indexed. Duplicate INSERTs must be caught at the application layer and treated as a signal, not an error (see integrations.x402.payment_events.log_payment_event).';

-- Complementary lookup index (NON-unique) — lets dashboards/forensics
-- answer "find all events for nonce X" without scanning the whole table.
CREATE INDEX IF NOT EXISTS idx_payment_events_nonce_lookup
    ON payment_events ((metadata ->> 'nonce'))
    WHERE (metadata ->> 'nonce') IS NOT NULL;

COMMENT ON INDEX idx_payment_events_nonce_lookup IS
    'Forensics lookup by EIP-3009 nonce across tokens/networks. Partial, non-unique.';
