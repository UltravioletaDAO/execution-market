-- Migration 037: Update payment_token column to store token symbols
-- The original schema (001) stored contract addresses in payment_token.
-- The application code now uses token symbols (USDC, EURC, AUSD, PYUSD, USDT).
-- This migration:
--   1. Widens the column to TEXT to accommodate any symbol
--   2. Converts existing contract addresses to their symbol equivalents
--   3. Sets the default to 'USDC' (symbol, not address)

-- Step 1: Change column type and default
ALTER TABLE tasks
ALTER COLUMN payment_token TYPE TEXT,
ALTER COLUMN payment_token SET DEFAULT 'USDC';

-- Step 2: Convert known contract addresses to symbols
-- Base USDC
UPDATE tasks SET payment_token = 'USDC'
WHERE payment_token = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

-- Base EURC
UPDATE tasks SET payment_token = 'EURC'
WHERE payment_token = '0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42';

-- Ethereum USDC
UPDATE tasks SET payment_token = 'USDC'
WHERE payment_token = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';

-- Polygon USDC
UPDATE tasks SET payment_token = 'USDC'
WHERE payment_token = '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359';

-- Arbitrum USDC
UPDATE tasks SET payment_token = 'USDC'
WHERE payment_token = '0xaf88d065e77c8cC2239327C5EDb3A432268e5831';

-- Any remaining 0x-prefixed values default to USDC
UPDATE tasks SET payment_token = 'USDC'
WHERE payment_token LIKE '0x%';

-- Any NULL values default to USDC
UPDATE tasks SET payment_token = 'USDC'
WHERE payment_token IS NULL;

COMMENT ON COLUMN tasks.payment_token IS 'Payment token symbol (e.g., USDC, EURC, AUSD, PYUSD, USDT). Stored as human-readable symbol, not contract address.';
