-- ===========================================================================
-- HOTFIX DB-004 / Phase 2.3 (paste into the Supabase SQL editor) — close the
-- anon-writable regression on veryai_verifications (mig 105) and
-- agent_kya_verifications (mig 106). Their INSERT/UPDATE/DELETE policies used
-- WITH CHECK (true) / USING (true) with no `TO` clause (apply to ALL roles), so
-- anon/authenticated could forge verification rows. This re-scopes the write
-- policies to service_role and revokes the write verbs at the grant level too.
-- The SELECT policies are intentionally preserved (own-row for veryai, public
-- trust signal for agent_kya). Idempotent.
-- Mirrors supabase/migrations/116_db004_verification_tables_anon_write_lockdown.sql.
-- ===========================================================================
BEGIN;

-- veryai_verifications
ALTER TABLE veryai_verifications ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "veryai_verifications_service_insert" ON veryai_verifications;
DROP POLICY IF EXISTS "veryai_verifications_service_update" ON veryai_verifications;
DROP POLICY IF EXISTS "veryai_verifications_insert" ON veryai_verifications;
DROP POLICY IF EXISTS "veryai_verifications_update" ON veryai_verifications;
CREATE POLICY "veryai_verifications_insert_service_role_only"
    ON veryai_verifications FOR INSERT TO service_role WITH CHECK (true);
CREATE POLICY "veryai_verifications_update_service_role_only"
    ON veryai_verifications FOR UPDATE TO service_role USING (true) WITH CHECK (true);
REVOKE INSERT, UPDATE, DELETE ON TABLE veryai_verifications FROM anon, authenticated;
REVOKE ALL ON TABLE veryai_verifications FROM anon;

-- agent_kya_verifications
ALTER TABLE agent_kya_verifications ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "agent_kya_verifications_service_insert" ON agent_kya_verifications;
DROP POLICY IF EXISTS "agent_kya_verifications_service_update" ON agent_kya_verifications;
DROP POLICY IF EXISTS "agent_kya_verifications_service_delete" ON agent_kya_verifications;
DROP POLICY IF EXISTS "agent_kya_verifications_insert" ON agent_kya_verifications;
DROP POLICY IF EXISTS "agent_kya_verifications_update" ON agent_kya_verifications;
DROP POLICY IF EXISTS "agent_kya_verifications_delete" ON agent_kya_verifications;
CREATE POLICY "agent_kya_verifications_insert_service_role_only"
    ON agent_kya_verifications FOR INSERT TO service_role WITH CHECK (true);
CREATE POLICY "agent_kya_verifications_update_service_role_only"
    ON agent_kya_verifications FOR UPDATE TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "agent_kya_verifications_delete_service_role_only"
    ON agent_kya_verifications FOR DELETE TO service_role USING (true);
REVOKE INSERT, UPDATE, DELETE ON TABLE agent_kya_verifications FROM anon, authenticated;

COMMIT;

-- Verify (expect all f):
SELECT
    has_table_privilege('anon',          'public.veryai_verifications',    'INSERT') AS veryai_anon_insert,
    has_table_privilege('authenticated', 'public.veryai_verifications',    'INSERT') AS veryai_authed_insert,
    has_table_privilege('anon',          'public.agent_kya_verifications', 'INSERT') AS kya_anon_insert,
    has_table_privilege('authenticated', 'public.agent_kya_verifications', 'INSERT') AS kya_authed_insert;
