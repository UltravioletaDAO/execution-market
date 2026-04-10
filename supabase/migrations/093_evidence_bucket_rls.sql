-- ============================================================================
-- EXECUTION MARKET: Lock down Supabase Storage 'evidence' bucket
-- Migration: 093_evidence_bucket_rls.sql
-- Applied: 2026-04-09
--
-- Security audit 2026-04-07 — DB-008 (Phase 0 guardrail GR-0.4, database half).
--
-- PROBLEM
--   The 'evidence' bucket has three policies, all wide-open to anon/authenticated:
--     - "Anyone can upload evidence"      (INSERT — anon, authenticated)
--     - "Evidence is readable"            (SELECT — anon, authenticated)
--     - "Evidence deletable by owner"     (DELETE — authenticated, name lies:
--                                          no ownership check at all)
--   Any unauthenticated user on the internet can read, write, or delete every
--   file in the bucket. Introduced by migration 013_fix_submissions_and_task_release.
--
-- FIX
--   Replace with path-based participant checks:
--     - INSERT/UPDATE/DELETE: service_role only. The backend (MCP server) is
--       responsible for authenticating the uploader (ERC-8128 + World ID where
--       required) before accepting an upload, then writing via the service key.
--       Direct browser uploads now go through the S3 presign Lambda (protected
--       by the JWT authorizer in evidence.tf) — the Supabase storage path is
--       retained as a fallback for avatars and legacy flows.
--     - SELECT: only participants of the submission — the executor who uploaded
--       it (via executors.user_id = auth.uid()) OR the service role (the backend
--       proxies agent reads, since agents authenticate via ERC-8128 at the API
--       layer, not via Supabase sessions).
--
-- PATH CONVENTION
--   Determined by reading the frontend upload code (dashboard/src/services/
--   evidence.ts line 146 — the currently-used path format):
--     evidence uploads: '{executor_id}/{task_id}/{evidence_type}_{timestamp}'
--     avatars:          'avatars/{executor_id}/profile.{ext}'
--       (dashboard/src/components/profile/ProfileEditModal.tsx line 130)
--   NOTE: EvidenceUpload.tsx uses '{task_id}/{executor_id}/...' but per
--   CLAUDE.md "Known Bugs & TODOs" EvidenceUpload.tsx is unused — SubmissionForm
--   is the active path. submission_id is NOT in the Supabase path (only in the
--   S3 Lambda path), so the SELECT policy matches on executor_id (first segment).
--
-- DEPENDENCIES
--   - Backend helper `mint_evidence_jwt()` (Track D2) for the Lambda authorizer.
--   - Backend upload proxy for legitimate uploads that previously went direct
--     to Supabase Storage from the browser.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Permission note: storage.objects is owned by supabase_storage_admin.
-- On Supabase managed hosting, postgres cannot SET ROLE to that role.
-- Instead we transfer ownership of storage.objects to postgres temporarily,
-- apply the policy changes, then transfer ownership back.
-- If this ALSO fails, apply via the Supabase Dashboard UI (Storage → Policies).
-- ----------------------------------------------------------------------------
ALTER TABLE storage.objects OWNER TO postgres;

-- ----------------------------------------------------------------------------
-- Step 1: Drop the wide-open policies on the 'evidence' bucket.
-- These were introduced in migration 013_fix_submissions_and_task_release.
-- ----------------------------------------------------------------------------

DROP POLICY IF EXISTS "Anyone can upload evidence"      ON storage.objects;
DROP POLICY IF EXISTS "Evidence is readable"            ON storage.objects;
DROP POLICY IF EXISTS "Evidence deletable by owner"     ON storage.objects;

-- Belt and suspenders: also drop any legacy evidence policies referenced in
-- migration 013's DROP guards (the 'chamba-evidence' bucket from 001 plus
-- earlier naming iterations) so this migration leaves storage.objects with
-- exactly the four policies we create below.
DROP POLICY IF EXISTS "Authenticated users can upload evidence" ON storage.objects;
DROP POLICY IF EXISTS "Evidence viewable by task owner"         ON storage.objects;
DROP POLICY IF EXISTS "Users can view own evidence"             ON storage.objects;
DROP POLICY IF EXISTS "Users can delete own evidence"           ON storage.objects;
DROP POLICY IF EXISTS "evidence_upload_authenticated"           ON storage.objects;
DROP POLICY IF EXISTS "evidence_select_authenticated"           ON storage.objects;
DROP POLICY IF EXISTS "evidence_delete_own"                     ON storage.objects;

-- ----------------------------------------------------------------------------
-- Step 2: Tighten the 'evidence' bucket metadata — make sure it is private.
-- ----------------------------------------------------------------------------

UPDATE storage.buckets
SET public = false
WHERE id = 'evidence';

-- ----------------------------------------------------------------------------
-- Step 3: Write policies — service role only.
--
-- Direct browser writes are no longer supported. All evidence uploads go
-- through either:
--   (a) the S3 presign Lambda behind the JWT authorizer (primary), or
--   (b) the backend MCP server using the service_role key (fallback / avatars).
-- ----------------------------------------------------------------------------

CREATE POLICY "evidence_insert_service_role_only"
    ON storage.objects
    FOR INSERT
    TO service_role
    WITH CHECK (bucket_id = 'evidence');

CREATE POLICY "evidence_update_service_role_only"
    ON storage.objects
    FOR UPDATE
    TO service_role
    USING (bucket_id = 'evidence')
    WITH CHECK (bucket_id = 'evidence');

CREATE POLICY "evidence_delete_service_role_only"
    ON storage.objects
    FOR DELETE
    TO service_role
    USING (bucket_id = 'evidence');

-- ----------------------------------------------------------------------------
-- Step 4: Read policy — participants only.
--
-- The executor who uploaded the evidence can read it back (e.g. to preview a
-- pending submission). Everyone else must go through the backend, which uses
-- the service_role key.
--
-- Path format (per dashboard/src/services/evidence.ts:146):
--   '{executor_id_uuid}/{task_id_uuid}/{evidence_type}_{timestamp}'
--
-- SPLIT_PART(name, '/', 1) = executor_id
--
-- Avatars live under 'avatars/{executor_id}/profile.{ext}' — the executor
-- owning the avatar can still read their own file.
-- ----------------------------------------------------------------------------

CREATE POLICY "evidence_select_participant"
    ON storage.objects
    FOR SELECT
    TO authenticated
    USING (
        bucket_id = 'evidence'
        AND (
            -- Evidence upload: first path segment is the executor UUID.
            EXISTS (
                SELECT 1
                FROM executors e
                WHERE e.id::text = SPLIT_PART(storage.objects.name, '/', 1)
                  AND e.user_id = auth.uid()
            )
            OR
            -- Avatars: first segment is literal 'avatars', second segment is
            -- the executor UUID.
            (
                SPLIT_PART(storage.objects.name, '/', 1) = 'avatars'
                AND EXISTS (
                    SELECT 1
                    FROM executors e
                    WHERE e.id::text = SPLIT_PART(storage.objects.name, '/', 2)
                      AND e.user_id = auth.uid()
                )
            )
        )
    );

-- service_role bypasses RLS for SELECT by default, but we make it explicit so
-- an operator reading `pg_policies` sees the full access model for this bucket.
CREATE POLICY "evidence_select_service_role"
    ON storage.objects
    FOR SELECT
    TO service_role
    USING (bucket_id = 'evidence');

-- ----------------------------------------------------------------------------
-- Audit trail
-- ----------------------------------------------------------------------------

COMMENT ON POLICY "evidence_insert_service_role_only"  ON storage.objects IS
    'Phase 0 GR-0.4 / DB-008: direct writes forbidden; backend proxies all uploads.';
COMMENT ON POLICY "evidence_update_service_role_only"  ON storage.objects IS
    'Phase 0 GR-0.4 / DB-008: only the backend may update evidence metadata.';
COMMENT ON POLICY "evidence_delete_service_role_only"  ON storage.objects IS
    'Phase 0 GR-0.4 / DB-008: only the backend may delete evidence.';
COMMENT ON POLICY "evidence_select_participant"        ON storage.objects IS
    'Phase 0 GR-0.4 / DB-008: executor who uploaded may read back (preview); agent reads go via backend service_role.';
COMMENT ON POLICY "evidence_select_service_role"       ON storage.objects IS
    'Phase 0 GR-0.4 / DB-008: explicit service_role SELECT for the backend.';

-- Restore ownership back to the storage admin role
ALTER TABLE storage.objects OWNER TO supabase_storage_admin;
