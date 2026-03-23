-- Migration 073: Backfill payer_wallet on open escrows
-- Context: Commit ed36874 introduced multi-wallet escrow support.
-- Escrows created BEFORE that fix were signed by the platform wallet.
-- Without this backfill, the new code defaults to agent wallet for release/refund,
-- which would fail (wrong signer).

BEGIN;

-- Set payer_wallet = 'platform' on all open escrows that predate the fix
UPDATE escrows
SET metadata = jsonb_set(
    COALESCE(metadata, '{}'),
    '{payer_wallet}',
    '"platform"'
)
WHERE status IN ('locked', 'authorized', 'pending_release', 'pending_assignment')
  AND (metadata->>'payer_wallet' IS NULL);

COMMIT;
