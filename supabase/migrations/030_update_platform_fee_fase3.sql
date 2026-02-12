-- Migration 030: Update platform fee from 8% to 13% (Fase 3)
-- Total fee to agent: 13% of bounty
-- EM treasury receives: 12% (via direct EIP-3009 settlement)
-- x402r protocol receives: ~1% (100 BPS via on-chain feeCalculator)
--
-- This migration updates the platform_config table. The Python code
-- reads EM_PLATFORM_FEE env var first, falling back to DB config.
-- Both should be updated together.

UPDATE platform_config
SET value = '0.13',
    updated_at = NOW()
WHERE key = 'fees.platform_fee_pct';

-- Also update BPS representation if it exists
UPDATE platform_config
SET value = '1300',
    updated_at = NOW()
WHERE key = 'fees.platform_fee_bps';
