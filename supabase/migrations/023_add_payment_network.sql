-- Migration 023: Add payment_network field to tasks
-- Adds a human-readable network name for multi-chain payment support.
-- The existing chain_id column stays for backward compatibility.

ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS payment_network VARCHAR(30) DEFAULT 'base';

-- Update existing rows to 'base' (they all use chain_id 8453)
UPDATE tasks SET payment_network = 'base' WHERE payment_network IS NULL;

-- Add comment
COMMENT ON COLUMN tasks.payment_network IS 'Payment network name (e.g., base, ethereum, polygon). Maps to ERC-8004 + x402 supported networks.';
