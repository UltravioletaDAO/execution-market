-- ============================================================================
-- EXECUTION MARKET: Delete plaintext API keys leaked in migration 006
-- Migration: 094_delete_plaintext_api_key.sql
-- Description: Phase 0 GR-0.5 — remove the two dev/test API keys that were
--              committed in plaintext in migration 006_api_keys.sql.
--              See security audit 2026-04-07 / DB-020.
-- Date: 2026-04-09
-- ============================================================================
--
-- Context:
--   Migration 006 inserted two test API keys with the full plaintext key in
--   SQL comments AND with the key prefix stored in the `key_prefix` column.
--   The key_hash columns are SHA256 of the plaintext, which is cheap to
--   verify if an attacker guesses the plaintext. Since the plaintext is
--   literally sitting in the public git history, we treat both keys as
--   fully compromised.
--
--   This migration deletes both rows from the `api_keys` table so that any
--   request presenting the leaked keys will 401/403. The runbook for
--   Phase 0 GR-0.5 describes the companion manual step to run on the
--   production database.
--
-- Rollback:
--   None. Do NOT re-insert these keys under any circumstances. If you need
--   test keys for local development, generate new random keys and put them
--   in a gitignored seed file (supabase/seeds/local-dev.sql) — NEVER commit
--   plaintext keys to migrations.
-- ============================================================================

BEGIN;

-- Delete by key_hash (primary path — covers both plaintext variants).
DELETE FROM api_keys
WHERE key_hash IN (
    -- SHA256('chamba_free_d57b51d2a852191a7dd02d5ac158ddc3')
    'c7185996d0b08c1c811f13c378a95afe226cd09438c4e6e49d1bd8455db533e6',
    -- SHA256('chamba_enterprise_a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6')
    'f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4f3e2'
);

-- Belt-and-suspenders: delete by key_prefix in case the hashes were updated
-- downstream but the prefix still matches a leaked key.
DELETE FROM api_keys
WHERE key_prefix LIKE 'chamba_%';

-- Delete any row that still references the original test agent IDs. These
-- agent IDs only exist because migration 006 created them with plaintext
-- keys; any surviving row must be a copy of a leaked key.
DELETE FROM api_keys
WHERE agent_id IN ('test_agent_001', 'test_enterprise_agent')
  AND name IN (
      'Test API Key for Development',
      'Enterprise Test API Key'
  );

-- Sanity check: fail the migration if any row still matches a known leaked
-- prefix after the DELETEs. This guarantees the rotation is complete.
DO $$
DECLARE
    remaining_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO remaining_count
    FROM api_keys
    WHERE key_prefix LIKE 'chamba_%';

    IF remaining_count > 0 THEN
        RAISE EXCEPTION
            'Migration 094 failed: % chamba_* key(s) still present in api_keys',
            remaining_count;
    END IF;
END $$;

COMMIT;
