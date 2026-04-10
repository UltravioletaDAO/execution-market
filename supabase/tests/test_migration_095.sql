-- Test suite for migration 095_restrict_public_views.sql
-- Phase 2 RLS — Security audit 2026-04-07
-- Closes: DB-005, DB-006, DB-006b, DB-007, DB-015
--
-- HOW TO RUN
-- ----------
--   Via Supabase SQL editor:
--     1. Run supabase/migrations/095_restrict_public_views.sql
--     2. Run this file
--     3. The final SELECT returns 'ALL TESTS PASSED' on success;
--        any test failure raises EXCEPTION and aborts
--
--   Via psql (local):
--     psql "$DATABASE_URL" -f supabase/migrations/095_restrict_public_views.sql
--     psql "$DATABASE_URL" -f supabase/tests/test_migration_095.sql
--
-- Each DO $$ BEGIN ... END $$ block is an independent assertion. We use
-- RAISE EXCEPTION on failure (aborts the session) and RAISE NOTICE on pass
-- so the output shows which tests ran.

\set ON_ERROR_STOP on

-- ============================================================================
-- Test 1: tasks_select_public policy MUST NOT exist
-- (DB-005: was exposing human_wallet, location_lat/lng, metadata to anon)
-- ============================================================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'tasks' AND policyname = 'tasks_select_public'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: tasks_select_public policy still exists (DB-005)';
    END IF;
    RAISE NOTICE 'PASS [DB-005]: tasks_select_public policy dropped';
END $$;

-- ============================================================================
-- Test 2: tasks_safe view MUST exist with expected safe columns
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_schema = 'public' AND table_name = 'tasks_safe'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: tasks_safe view does not exist (DB-005)';
    END IF;
    RAISE NOTICE 'PASS [DB-005]: tasks_safe view exists';
END $$;

-- Check that tasks_safe has the expected safe columns
DO $$
DECLARE
    v_cols text[];
BEGIN
    SELECT array_agg(column_name::text ORDER BY ordinal_position)
    INTO v_cols
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'tasks_safe';

    -- Verify key safe columns are present
    IF NOT ('id' = ANY(v_cols)) THEN
        RAISE EXCEPTION 'TEST FAILED: tasks_safe missing column "id"';
    END IF;
    IF NOT ('title' = ANY(v_cols)) THEN
        RAISE EXCEPTION 'TEST FAILED: tasks_safe missing column "title"';
    END IF;
    IF NOT ('bounty_usd' = ANY(v_cols)) THEN
        RAISE EXCEPTION 'TEST FAILED: tasks_safe missing column "bounty_usd"';
    END IF;
    IF NOT ('status' = ANY(v_cols)) THEN
        RAISE EXCEPTION 'TEST FAILED: tasks_safe missing column "status"';
    END IF;

    -- Verify PII columns exist (as NULLed stubs) for compatibility
    IF NOT ('human_wallet' = ANY(v_cols)) THEN
        RAISE EXCEPTION 'TEST FAILED: tasks_safe missing NULLed stub "human_wallet"';
    END IF;
    IF NOT ('location_lat' = ANY(v_cols)) THEN
        RAISE EXCEPTION 'TEST FAILED: tasks_safe missing NULLed stub "location_lat"';
    END IF;

    RAISE NOTICE 'PASS [DB-005]: tasks_safe has expected columns (% total)', array_length(v_cols, 1);
END $$;

-- ============================================================================
-- Test 3: anon CANNOT SELECT from tasks base table
-- ============================================================================
DO $$
BEGIN
    IF has_table_privilege('anon', 'public.tasks', 'SELECT') THEN
        RAISE EXCEPTION 'TEST FAILED: anon still has SELECT on tasks base table (DB-005)';
    END IF;
    RAISE NOTICE 'PASS [DB-005]: anon cannot SELECT from tasks base table';
END $$;

-- ============================================================================
-- Test 4: anon CAN SELECT from tasks_safe view
-- ============================================================================
DO $$
BEGIN
    IF NOT has_table_privilege('anon', 'public.tasks_safe', 'SELECT') THEN
        RAISE EXCEPTION 'TEST FAILED: anon cannot SELECT from tasks_safe view (DB-005)';
    END IF;
    RAISE NOTICE 'PASS [DB-005]: anon can SELECT from tasks_safe view';
END $$;

-- ============================================================================
-- Test 5: authenticated CAN SELECT from tasks_safe view
-- ============================================================================
DO $$
BEGIN
    IF NOT has_table_privilege('authenticated', 'public.tasks_safe', 'SELECT') THEN
        RAISE EXCEPTION 'TEST FAILED: authenticated cannot SELECT from tasks_safe view (DB-005)';
    END IF;
    RAISE NOTICE 'PASS [DB-005]: authenticated can SELECT from tasks_safe view';
END $$;

-- ============================================================================
-- Test 6: executors_select_public policy MUST NOT exist
-- (DB-015: was exposing wallet_address, email, phone, financial data)
-- ============================================================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'executors' AND policyname = 'executors_select_public'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: executors_select_public policy still exists (DB-015)';
    END IF;
    RAISE NOTICE 'PASS [DB-015]: executors_select_public policy dropped';
END $$;

-- ============================================================================
-- Test 7: executors_safe view MUST exist
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_schema = 'public' AND table_name = 'executors_safe'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: executors_safe view does not exist (DB-015)';
    END IF;
    RAISE NOTICE 'PASS [DB-015]: executors_safe view exists';
END $$;

-- Check executors_safe has safe columns but NULLed PII stubs
DO $$
DECLARE
    v_cols text[];
BEGIN
    SELECT array_agg(column_name::text ORDER BY ordinal_position)
    INTO v_cols
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'executors_safe';

    IF NOT ('id' = ANY(v_cols)) THEN
        RAISE EXCEPTION 'TEST FAILED: executors_safe missing "id"';
    END IF;
    IF NOT ('display_name' = ANY(v_cols)) THEN
        RAISE EXCEPTION 'TEST FAILED: executors_safe missing "display_name"';
    END IF;
    IF NOT ('reputation_score' = ANY(v_cols)) THEN
        RAISE EXCEPTION 'TEST FAILED: executors_safe missing "reputation_score"';
    END IF;
    IF NOT ('wallet_address' = ANY(v_cols)) THEN
        RAISE EXCEPTION 'TEST FAILED: executors_safe missing NULLed stub "wallet_address"';
    END IF;
    IF NOT ('email' = ANY(v_cols)) THEN
        RAISE EXCEPTION 'TEST FAILED: executors_safe missing NULLed stub "email"';
    END IF;

    RAISE NOTICE 'PASS [DB-015]: executors_safe has expected columns (% total)', array_length(v_cols, 1);
END $$;

-- ============================================================================
-- Test 8: anon CANNOT SELECT from executors base table
-- ============================================================================
DO $$
BEGIN
    IF has_table_privilege('anon', 'public.executors', 'SELECT') THEN
        RAISE EXCEPTION 'TEST FAILED: anon still has SELECT on executors base table (DB-015)';
    END IF;
    RAISE NOTICE 'PASS [DB-015]: anon cannot SELECT from executors base table';
END $$;

-- ============================================================================
-- Test 9: anon CAN SELECT from executors_safe view
-- ============================================================================
DO $$
BEGIN
    IF NOT has_table_privilege('anon', 'public.executors_safe', 'SELECT') THEN
        RAISE EXCEPTION 'TEST FAILED: anon cannot SELECT from executors_safe view (DB-015)';
    END IF;
    RAISE NOTICE 'PASS [DB-015]: anon can SELECT from executors_safe view';
END $$;

-- ============================================================================
-- Test 10: escrows_select_agent policy MUST NOT exist
-- (DB-006: was USING(true) — all escrow data visible to anyone)
-- ============================================================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'escrows' AND policyname = 'escrows_select_agent'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: escrows_select_agent policy still exists (DB-006)';
    END IF;
    RAISE NOTICE 'PASS [DB-006]: escrows_select_agent policy dropped';
END $$;

-- ============================================================================
-- Test 11: escrows_select_service_role_only policy MUST exist
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'escrows' AND policyname = 'escrows_select_service_role_only'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: escrows_select_service_role_only policy not created (DB-006)';
    END IF;
    RAISE NOTICE 'PASS [DB-006]: escrows_select_service_role_only policy exists';
END $$;

-- ============================================================================
-- Test 12: anon CANNOT SELECT from escrows
-- ============================================================================
DO $$
BEGIN
    IF has_table_privilege('anon', 'public.escrows', 'SELECT') THEN
        RAISE EXCEPTION 'TEST FAILED: anon still has SELECT on escrows (DB-006)';
    END IF;
    RAISE NOTICE 'PASS [DB-006]: anon cannot SELECT from escrows';
END $$;

-- ============================================================================
-- Test 13: disputes_select_participant (with OR true) MUST NOT exist
-- (DB-007: OR true made all disputes visible to anyone)
-- ============================================================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'disputes' AND policyname = 'disputes_select_participant'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: disputes_select_participant policy still exists (DB-007)';
    END IF;
    RAISE NOTICE 'PASS [DB-007]: disputes_select_participant (OR true) policy dropped';
END $$;

-- ============================================================================
-- Test 14: disputes_select_participant_real policy MUST exist
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'disputes' AND policyname = 'disputes_select_participant_real'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: disputes_select_participant_real not created (DB-007)';
    END IF;
    RAISE NOTICE 'PASS [DB-007]: disputes_select_participant_real policy exists';
END $$;

-- ============================================================================
-- Test 15: disputes_select_participant_real targets authenticated only
-- ============================================================================
DO $$
DECLARE
    v_roles text[];
BEGIN
    SELECT roles INTO v_roles
    FROM pg_policies
    WHERE tablename = 'disputes' AND policyname = 'disputes_select_participant_real';

    IF NOT ('{authenticated}' = v_roles::text) THEN
        RAISE EXCEPTION 'TEST FAILED: disputes_select_participant_real should target authenticated, got %', v_roles;
    END IF;
    RAISE NOTICE 'PASS [DB-007]: disputes_select_participant_real targets authenticated only';
END $$;

-- ============================================================================
-- Test 16: disputes_select_service_role policy MUST exist
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'disputes' AND policyname = 'disputes_select_service_role'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: disputes_select_service_role not created (DB-007)';
    END IF;
    RAISE NOTICE 'PASS [DB-007]: disputes_select_service_role policy exists';
END $$;

-- ============================================================================
-- Test 17: payments_select_agent policy MUST NOT exist
-- (DB-006b: was USING(true) — all payment records visible to anyone)
-- ============================================================================
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'payments' AND policyname = 'payments_select_agent'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: payments_select_agent policy still exists (DB-006b)';
    END IF;
    RAISE NOTICE 'PASS [DB-006b]: payments_select_agent policy dropped';
END $$;

-- ============================================================================
-- Test 18: payments_select_service_role_only policy MUST exist
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'payments' AND policyname = 'payments_select_service_role_only'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: payments_select_service_role_only not created (DB-006b)';
    END IF;
    RAISE NOTICE 'PASS [DB-006b]: payments_select_service_role_only policy exists';
END $$;

-- ============================================================================
-- Test 19: anon CANNOT SELECT from payments
-- ============================================================================
DO $$
BEGIN
    IF has_table_privilege('anon', 'public.payments', 'SELECT') THEN
        RAISE EXCEPTION 'TEST FAILED: anon still has SELECT on payments (DB-006b)';
    END IF;
    RAISE NOTICE 'PASS [DB-006b]: anon cannot SELECT from payments';
END $$;

-- ============================================================================
-- Test 20: No USING(true) SELECT policies remain on sensitive tables
-- (Meta-check: catches any policies we missed)
-- ============================================================================
DO $$
DECLARE
    v_count integer;
    v_details text;
BEGIN
    SELECT COUNT(*), string_agg(tablename || '.' || policyname, ', ')
    INTO v_count, v_details
    FROM pg_policies
    WHERE tablename IN ('escrows', 'payments', 'disputes')
      AND cmd = 'SELECT'
      AND qual = 'true'
      AND NOT ('service_role' = ANY(roles));

    IF v_count > 0 THEN
        RAISE EXCEPTION 'TEST FAILED: % USING(true) SELECT policies remain on sensitive tables: %',
            v_count, v_details;
    END IF;
    RAISE NOTICE 'PASS [META]: no USING(true) SELECT policies on escrows/payments/disputes for non-service roles';
END $$;

-- ============================================================================
-- Test 21: service_role retains full access on all tables
-- ============================================================================
DO $$
DECLARE
    v_table text;
BEGIN
    FOREACH v_table IN ARRAY ARRAY['tasks', 'executors', 'escrows', 'payments', 'disputes']
    LOOP
        IF NOT has_table_privilege('service_role', 'public.' || v_table, 'SELECT') THEN
            RAISE EXCEPTION 'TEST FAILED: service_role lost SELECT on %', v_table;
        END IF;
    END LOOP;
    RAISE NOTICE 'PASS [META]: service_role retains SELECT on all 5 tables';
END $$;

-- ============================================================================
-- SUMMARY
-- ============================================================================
SELECT '=== ALL 21 TESTS PASSED — Migration 095 verified ===' AS result;
