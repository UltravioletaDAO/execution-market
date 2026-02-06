-- Migration 016: Add settlement_method column to payments table
-- Tracks whether payment was processed via facilitator (gasless) or direct contract call
-- Values: 'facilitator', 'direct_contract', 'unknown'

ALTER TABLE payments ADD COLUMN IF NOT EXISTS settlement_method TEXT DEFAULT 'unknown';

COMMENT ON COLUMN payments.settlement_method IS 'Payment processing path: facilitator (gasless) or direct_contract (agent pays gas)';
