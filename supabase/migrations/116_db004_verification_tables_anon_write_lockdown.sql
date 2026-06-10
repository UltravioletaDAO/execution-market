-- Migration 116: Close the DB-004 anon-writable regression on the VeryAI and
-- ClawKey verification tables (Security Audit 2026-06-09, Phase 2.3 / L-48).
-- Applied to production: pending.
--
-- ROOT CAUSE
-- ----------
-- Migration 092 (section 2) fixed DB-004 for world_id_verifications by replacing
-- its WITH CHECK (true) INSERT/UPDATE policies — which had NO role restriction,
-- so anon/authenticated could forge Orb-level verifications — with policies
-- scoped `TO service_role`. But migrations 105 (veryai_verifications) and 106
-- (agent_kya_verifications) RE-INTRODUCED the exact same regression: their
-- INSERT/UPDATE/DELETE policies use WITH CHECK (true) / USING (true) with no
-- `TO` clause, so they apply to ALL roles. Combined with Supabase's default
-- table grants to anon/authenticated, an anonymous browser can:
--   * INSERT a forged veryai_verifications row (defeats the >=$50 palm anti-sybil
--     tier — the enforcement code trusts a matching row), and
--   * INSERT/UPDATE/DELETE agent_kya_verifications rows (forges the KYA trust
--     signal surfaced on agent profiles / showcase).
--
-- FIX
-- ---
-- Mirror migration 092's world_id_verifications fix exactly: drop the
-- unrestricted write policies and recreate them scoped `TO service_role`.
-- Backend writers use the service_role key (mcp_server/supabase_client.py) and
-- are unaffected. The SELECT policies are intentionally preserved:
--   * veryai_verifications_select_own — own-row read via auth.uid() (unchanged).
--   * agent_kya_verifications_select_public — KYA is a public trust signal by
--     design (matches ERC-8004 reputation); read stays public.
-- Belt-and-suspenders: also REVOKE the write verbs from anon/authenticated so
-- a future policy regression cannot re-open the hole through default grants.
--
-- Idempotent: DROP POLICY IF EXISTS + CREATE; REVOKE is a no-op if not granted.

BEGIN;

-- ============================================================================
-- 1. veryai_verifications (migration 105) — DB-004
-- ============================================================================
ALTER TABLE veryai_verifications ENABLE ROW LEVEL SECURITY;

-- Drop the unrestricted (no-role) write policies from migration 105.
DROP POLICY IF EXISTS "veryai_verifications_service_insert" ON veryai_verifications;
DROP POLICY IF EXISTS "veryai_verifications_service_update" ON veryai_verifications;
-- Defensive: any variant names that may exist in production.
DROP POLICY IF EXISTS "veryai_verifications_insert" ON veryai_verifications;
DROP POLICY IF EXISTS "veryai_verifications_update" ON veryai_verifications;
-- This migration's own target names — so a re-run does not collide (idempotent).
DROP POLICY IF EXISTS "veryai_verifications_insert_service_role_only" ON veryai_verifications;
DROP POLICY IF EXISTS "veryai_verifications_update_service_role_only" ON veryai_verifications;

-- Recreate scoped to service_role only.
CREATE POLICY "veryai_verifications_insert_service_role_only"
    ON veryai_verifications
    FOR INSERT
    TO service_role
    WITH CHECK (true);

CREATE POLICY "veryai_verifications_update_service_role_only"
    ON veryai_verifications
    FOR UPDATE
    TO service_role
    USING (true)
    WITH CHECK (true);

-- The select-own policy (105) is intentionally preserved. No DELETE policy by
-- design (immutable audit trail).

-- Belt-and-suspenders: anon/authenticated may not write this table at the grant
-- level. (Migration 105 has no SELECT grant to anon; the select-own policy is
-- for authenticated workers, so we keep authenticated SELECT.)
REVOKE INSERT, UPDATE, DELETE ON TABLE veryai_verifications FROM anon, authenticated;
REVOKE ALL ON TABLE veryai_verifications FROM anon;

-- ============================================================================
-- 2. agent_kya_verifications (migration 106) — DB-004
-- ============================================================================
ALTER TABLE agent_kya_verifications ENABLE ROW LEVEL SECURITY;

-- Drop the unrestricted (no-role) write policies from migration 106.
DROP POLICY IF EXISTS "agent_kya_verifications_service_insert" ON agent_kya_verifications;
DROP POLICY IF EXISTS "agent_kya_verifications_service_update" ON agent_kya_verifications;
DROP POLICY IF EXISTS "agent_kya_verifications_service_delete" ON agent_kya_verifications;
-- Defensive variants.
DROP POLICY IF EXISTS "agent_kya_verifications_insert" ON agent_kya_verifications;
DROP POLICY IF EXISTS "agent_kya_verifications_update" ON agent_kya_verifications;
DROP POLICY IF EXISTS "agent_kya_verifications_delete" ON agent_kya_verifications;
-- This migration's own target names — so a re-run does not collide (idempotent).
DROP POLICY IF EXISTS "agent_kya_verifications_insert_service_role_only" ON agent_kya_verifications;
DROP POLICY IF EXISTS "agent_kya_verifications_update_service_role_only" ON agent_kya_verifications;
DROP POLICY IF EXISTS "agent_kya_verifications_delete_service_role_only" ON agent_kya_verifications;

-- Recreate scoped to service_role only.
CREATE POLICY "agent_kya_verifications_insert_service_role_only"
    ON agent_kya_verifications
    FOR INSERT
    TO service_role
    WITH CHECK (true);

CREATE POLICY "agent_kya_verifications_update_service_role_only"
    ON agent_kya_verifications
    FOR UPDATE
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "agent_kya_verifications_delete_service_role_only"
    ON agent_kya_verifications
    FOR DELETE
    TO service_role
    USING (true);

-- The public SELECT policy (106, "agent_kya_verifications_select_public") is
-- intentionally preserved — KYA is a public trust signal by design.

-- Belt-and-suspenders: anon/authenticated may not write this table at the grant
-- level. Keep SELECT (the public-read policy needs it).
REVOKE INSERT, UPDATE, DELETE ON TABLE agent_kya_verifications FROM anon, authenticated;

COMMENT ON TABLE agent_kya_verifications IS
    'ClawKey Know Your Agent. Public read (trust signal). Writes restricted to '
    'service_role only (DB-004 fix, migration 116 / FIX Phase 2.3).';

COMMIT;

-- ===========================================================================
-- VERIFICATION (expect anon/authenticated cannot INSERT; service_role can)
-- ===========================================================================
-- SELECT has_table_privilege('anon',          'public.veryai_verifications',    'INSERT'); -- expect f
-- SELECT has_table_privilege('authenticated', 'public.veryai_verifications',    'INSERT'); -- expect f
-- SELECT has_table_privilege('anon',          'public.agent_kya_verifications', 'INSERT'); -- expect f
-- SELECT has_table_privilege('authenticated', 'public.agent_kya_verifications', 'INSERT'); -- expect f
