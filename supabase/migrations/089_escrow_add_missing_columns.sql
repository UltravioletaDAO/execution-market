-- ============================================================================
-- Migration: 089_escrow_add_missing_columns.sql
-- Description: Add chain_id and beneficiary_address columns to escrows table.
--              These columns were defined in 002_escrow_and_payments.sql but
--              never applied to the production Supabase database. The backend
--              code already works around this via metadata JSON, but the
--              columns should exist for data consistency and query performance.
-- Date: 2026-04-04
-- Idempotent: YES (safe to re-run)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Add missing columns (IF NOT EXISTS = safe to re-run)
-- ---------------------------------------------------------------------------

ALTER TABLE escrows ADD COLUMN IF NOT EXISTS chain_id INTEGER DEFAULT 8453;

ALTER TABLE escrows ADD COLUMN IF NOT EXISTS beneficiary_address VARCHAR(42);

-- ---------------------------------------------------------------------------
-- 2. Backfill chain_id from metadata->>'network' where the column is NULL
--
--    The backend stores network NAME in metadata (e.g. "base", "polygon"),
--    not numeric chain_id. Map known networks to chain IDs.
-- ---------------------------------------------------------------------------

UPDATE escrows
SET chain_id = CASE (metadata->>'network')
    WHEN 'base'      THEN 8453
    WHEN 'ethereum'   THEN 1
    WHEN 'polygon'    THEN 137
    WHEN 'arbitrum'   THEN 42161
    WHEN 'celo'       THEN 42220
    WHEN 'monad'      THEN 143
    WHEN 'avalanche'  THEN 43114
    WHEN 'optimism'   THEN 10
    WHEN 'skale'      THEN 1187947933
    WHEN 'base-sepolia' THEN 84532
    ELSE 8453  -- default to Base Mainnet
END
WHERE chain_id IS NULL
  AND metadata->>'network' IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 3. Backfill beneficiary_address from metadata
--
--    The code stores the address under different keys depending on the flow:
--    - "beneficiary_address" (direct insert from _helpers.py)
--    - "beneficiary" (alternative key)
--    - "agent_address" (payment_dispatcher.py stores payer as agent_address)
--
--    Prefer beneficiary_address > beneficiary > agent_address.
-- ---------------------------------------------------------------------------

UPDATE escrows
SET beneficiary_address = COALESCE(
    metadata->>'beneficiary_address',
    metadata->>'beneficiary',
    metadata->>'agent_address'
)
WHERE beneficiary_address IS NULL
  AND (
    metadata->>'beneficiary_address' IS NOT NULL
    OR metadata->>'beneficiary' IS NOT NULL
    OR metadata->>'agent_address' IS NOT NULL
  );

-- ---------------------------------------------------------------------------
-- 4. Add index on chain_id for multi-chain queries (plain CREATE INDEX,
--    NOT CONCURRENTLY — Supabase SQL Editor wraps in transaction)
-- ---------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_escrows_chain_id ON escrows(chain_id);
