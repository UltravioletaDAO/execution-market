-- ============================================================================
-- Test: migration 093_evidence_bucket_rls
--
-- Run against a DB that has migration 093 applied. Intended for local /
-- staging smoke testing — NOT the main CI test suite.
--
--   psql "$SUPABASE_URL" -f supabase/tests/test_migration_093.sql
--
-- The DO block raises an exception on any assertion failure, which psql
-- surfaces as a non-zero exit.
-- ============================================================================

DO $$
DECLARE
    v_old_policy_count integer;
    v_new_policy_count integer;
    v_bucket_public boolean;
BEGIN
    -- ------------------------------------------------------------------------
    -- 1. The wide-open policies from migration 013 must be gone.
    -- ------------------------------------------------------------------------
    SELECT COUNT(*) INTO v_old_policy_count
    FROM pg_policies
    WHERE schemaname = 'storage'
      AND tablename  = 'objects'
      AND policyname IN (
          'Anyone can upload evidence',
          'Evidence is readable',
          'Evidence deletable by owner'
      );

    IF v_old_policy_count > 0 THEN
        RAISE EXCEPTION
            'Migration 093 failed: % legacy wide-open evidence policies still exist',
            v_old_policy_count;
    END IF;

    -- ------------------------------------------------------------------------
    -- 2. The five new policies must exist.
    -- ------------------------------------------------------------------------
    SELECT COUNT(*) INTO v_new_policy_count
    FROM pg_policies
    WHERE schemaname = 'storage'
      AND tablename  = 'objects'
      AND policyname IN (
          'evidence_insert_service_role_only',
          'evidence_update_service_role_only',
          'evidence_delete_service_role_only',
          'evidence_select_participant',
          'evidence_select_service_role'
      );

    IF v_new_policy_count <> 5 THEN
        RAISE EXCEPTION
            'Migration 093 failed: expected 5 new evidence policies, found %',
            v_new_policy_count;
    END IF;

    -- ------------------------------------------------------------------------
    -- 3. INSERT / UPDATE / DELETE policies must be scoped to service_role only.
    -- ------------------------------------------------------------------------
    IF EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'storage'
          AND tablename  = 'objects'
          AND policyname = 'evidence_insert_service_role_only'
          AND (
              roles IS NULL
              OR NOT (roles::text[] = ARRAY['service_role'])
          )
    ) THEN
        RAISE EXCEPTION
            'Migration 093 failed: evidence_insert_service_role_only must apply to service_role only';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'storage'
          AND tablename  = 'objects'
          AND policyname = 'evidence_delete_service_role_only'
          AND (
              roles IS NULL
              OR NOT (roles::text[] = ARRAY['service_role'])
          )
    ) THEN
        RAISE EXCEPTION
            'Migration 093 failed: evidence_delete_service_role_only must apply to service_role only';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'storage'
          AND tablename  = 'objects'
          AND policyname = 'evidence_update_service_role_only'
          AND (
              roles IS NULL
              OR NOT (roles::text[] = ARRAY['service_role'])
          )
    ) THEN
        RAISE EXCEPTION
            'Migration 093 failed: evidence_update_service_role_only must apply to service_role only';
    END IF;

    -- ------------------------------------------------------------------------
    -- 4. evidence_select_participant must join to executors.user_id = auth.uid().
    --    We inspect the USING clause text to make sure the path-based ownership
    --    check is present.
    -- ------------------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'storage'
          AND tablename  = 'objects'
          AND policyname = 'evidence_select_participant'
          AND qual LIKE '%executors%'
          AND qual LIKE '%auth.uid%'
          AND qual LIKE '%split_part%'
    ) THEN
        RAISE EXCEPTION
            'Migration 093 failed: evidence_select_participant must cross-join executors via split_part(name) and auth.uid()';
    END IF;

    -- ------------------------------------------------------------------------
    -- 5. The 'evidence' bucket must be marked private.
    -- ------------------------------------------------------------------------
    SELECT public INTO v_bucket_public
    FROM storage.buckets
    WHERE id = 'evidence';

    IF v_bucket_public IS DISTINCT FROM false THEN
        RAISE EXCEPTION
            'Migration 093 failed: evidence bucket must be private (public = false), got %',
            v_bucket_public;
    END IF;

    RAISE NOTICE 'Migration 093 passed: evidence bucket locked down, % new policies active', v_new_policy_count;
END;
$$;
