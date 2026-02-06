-- ============================================================================
-- MCP SERVER SUPABASE: Canonical payment ledger compatibility migration
-- Migration: 20260206000006_payment_ledger_canonical.sql
-- Date: 2026-02-06
--
-- Goal:
-- - Ensure `escrows` and `payments` tables exist in environments initialized
--   via `mcp_server/supabase/migrations`.
-- - Ensure canonical columns required by API contract exist:
--   task_id, submission_id, type, status, tx_hash, amount_usdc, network, created_at
-- - Keep compatibility with legacy aliases:
--   payment_type, transaction_hash, total_amount_usdc, chain_id
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS escrows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID UNIQUE,
    escrow_id TEXT,
    status TEXT DEFAULT 'authorized',
    amount_usdc NUMERIC(18, 6),
    total_amount_usdc NUMERIC(18, 6),
    platform_fee_usdc NUMERIC(18, 6) DEFAULT 0,
    funding_tx TEXT,
    deposit_tx TEXT,
    release_tx TEXT,
    refund_tx TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    released_at TIMESTAMPTZ,
    refunded_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ
);

ALTER TABLE escrows ADD COLUMN IF NOT EXISTS task_id UUID;
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS escrow_id TEXT;
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'authorized';
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS amount_usdc NUMERIC(18, 6);
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS total_amount_usdc NUMERIC(18, 6);
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS platform_fee_usdc NUMERIC(18, 6) DEFAULT 0;
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS funding_tx TEXT;
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS deposit_tx TEXT;
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS release_tx TEXT;
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS refund_tx TEXT;
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS released_at TIMESTAMPTZ;
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS refunded_at TIMESTAMPTZ;
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_escrows_task_id ON escrows(task_id);
CREATE INDEX IF NOT EXISTS idx_escrows_status ON escrows(status);
CREATE INDEX IF NOT EXISTS idx_escrows_created_at ON escrows(created_at DESC);

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID,
    submission_id UUID,
    executor_id UUID,
    escrow_id TEXT,
    type TEXT NOT NULL DEFAULT 'release',
    payment_type TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    tx_hash TEXT,
    transaction_hash TEXT,
    amount_usdc NUMERIC(18, 6) NOT NULL DEFAULT 0,
    fee_usdc NUMERIC(18, 6) DEFAULT 0,
    network TEXT DEFAULT 'base',
    chain_id INTEGER DEFAULT 8453,
    from_address TEXT,
    to_address TEXT,
    note TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

ALTER TABLE payments ADD COLUMN IF NOT EXISTS task_id UUID;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS submission_id UUID;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS executor_id UUID;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS escrow_id TEXT;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS type TEXT;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS payment_type TEXT;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS status TEXT;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS tx_hash TEXT;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS transaction_hash TEXT;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS amount_usdc NUMERIC(18, 6);
ALTER TABLE payments ADD COLUMN IF NOT EXISTS fee_usdc NUMERIC(18, 6) DEFAULT 0;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS network TEXT;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS chain_id INTEGER DEFAULT 8453;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS from_address TEXT;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS to_address TEXT;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS note TEXT;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE payments ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE payments ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

UPDATE payments
SET
    type = COALESCE(NULLIF(type, ''), payment_type, 'release'),
    payment_type = COALESCE(NULLIF(payment_type, ''), type, 'release'),
    tx_hash = COALESCE(NULLIF(tx_hash, ''), transaction_hash),
    transaction_hash = COALESCE(NULLIF(transaction_hash, ''), tx_hash),
    network = COALESCE(NULLIF(network, ''), CASE WHEN chain_id = 84532 THEN 'base-sepolia' ELSE 'base' END),
    status = COALESCE(NULLIF(status, ''), 'pending'),
    amount_usdc = COALESCE(amount_usdc, 0),
    created_at = COALESCE(created_at, NOW()),
    updated_at = COALESCE(updated_at, created_at, NOW())
WHERE TRUE;

ALTER TABLE payments ALTER COLUMN type SET DEFAULT 'release';
ALTER TABLE payments ALTER COLUMN status SET DEFAULT 'pending';
ALTER TABLE payments ALTER COLUMN amount_usdc SET DEFAULT 0;
ALTER TABLE payments ALTER COLUMN network SET DEFAULT 'base';
ALTER TABLE payments ALTER COLUMN created_at SET DEFAULT NOW();
ALTER TABLE payments ALTER COLUMN updated_at SET DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_payments_task_id ON payments(task_id);
CREATE INDEX IF NOT EXISTS idx_payments_submission_id ON payments(submission_id);
CREATE INDEX IF NOT EXISTS idx_payments_type ON payments(type);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_tx_hash ON payments(tx_hash);
CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at DESC);

