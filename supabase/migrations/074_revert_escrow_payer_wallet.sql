-- Migration 074: Revert migration 073 (payer_wallet backfill)
-- Context: ADR-001 (Payment Architecture v2) eliminates the concept of
-- server-side wallet selection. The payer_wallet field in escrow metadata
-- was based on the incorrect premise that EM has an "agent wallet" separate
-- from the platform wallet. EM is a marketplace — it never signs payments.
-- External agents sign their own escrow operations.

BEGIN;

-- Remove payer_wallet key from escrow metadata where it was backfilled
UPDATE escrows
SET metadata = metadata - 'payer_wallet'
WHERE metadata ? 'payer_wallet';

COMMIT;
