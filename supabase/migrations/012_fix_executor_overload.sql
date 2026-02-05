-- ============================================================================
-- EXECUTION MARKET: Fix get_or_create_executor function overload
-- Migration: 012_fix_executor_overload.sql
-- Applied: 2026-02-05
--
-- Problem: Multiple versions of get_or_create_executor exist due to migration layering:
--   1. (p_wallet_address, p_display_name) - 2 params
--   2. (p_wallet_address, p_display_name, p_email) - 3 params
--   3. (p_wallet_address, p_display_name, p_email, p_signature, p_message) - 5 params
--
-- Supabase can't choose between them, causing PGRST203 error.
--
-- Solution: Drop old versions, keep only the 5-parameter version, grant anon access.
-- ============================================================================

-- Drop old overloaded versions (keep only 5-param version)
DROP FUNCTION IF EXISTS get_or_create_executor(TEXT, TEXT);
DROP FUNCTION IF EXISTS get_or_create_executor(TEXT, TEXT, TEXT);

-- Grant execute to anon role (Dynamic.xyz users don't have Supabase sessions)
GRANT EXECUTE ON FUNCTION get_or_create_executor(TEXT, TEXT, TEXT, TEXT, TEXT) TO anon;
GRANT EXECUTE ON FUNCTION get_or_create_executor(TEXT, TEXT, TEXT, TEXT, TEXT) TO authenticated;

-- Also fix link_wallet_to_session grants for anon
GRANT EXECUTE ON FUNCTION link_wallet_to_session(UUID, TEXT, INTEGER, TEXT, TEXT) TO anon;
GRANT EXECUTE ON FUNCTION link_wallet_to_session(UUID, TEXT, INTEGER, TEXT, TEXT) TO authenticated;

-- Add missing columns to reputation_log that the function expects
ALTER TABLE reputation_log ADD COLUMN IF NOT EXISTS event_type TEXT DEFAULT 'manual';
ALTER TABLE reputation_log ADD COLUMN IF NOT EXISTS old_score INTEGER DEFAULT 0;
ALTER TABLE reputation_log ADD COLUMN IF NOT EXISTS submission_id UUID REFERENCES submissions(id);

-- Add comment
COMMENT ON FUNCTION get_or_create_executor(TEXT, TEXT, TEXT, TEXT, TEXT) IS
  'Get existing or create new executor by wallet address. Supports optional signature verification. Callable by anon (Dynamic.xyz) and authenticated users.';
