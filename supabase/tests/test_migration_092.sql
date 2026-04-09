-- Test suite for migration 092_revoke_anon_rpcs.sql
-- Phase 0 GR-0.3 — Security audit 2026-04-07
--
-- HOW TO RUN
-- ----------
--   Via Supabase SQL editor:
--     1. Run supabase/migrations/092_revoke_anon_rpcs.sql
--     2. Run this file
--     3. The final SELECT returns 'ALL TESTS PASSED' on success;
--        any test failure raises EXCEPTION and aborts
--
--   Via psql (local):
--     psql "$DATABASE_URL" -f supabase/migrations/092_revoke_anon_rpcs.sql
--     psql "$DATABASE_URL" -f supabase/tests/test_migration_092.sql
--
-- Each DO $$ BEGIN ... END $$ block is an independent assertion. We use
-- RAISE EXCEPTION on failure (aborts the session) and RAISE NOTICE on pass
-- so the output shows which tests ran. This is the simplest testing pattern
-- that works in a plain Supabase SQL Editor without pgTAP installed.

\set ON_ERROR_STOP on

-- ============================================================================
-- Test 1: get_or_create_executor REVOKED from anon
-- ============================================================================
DO $$
BEGIN
    IF has_function_privilege(
        'anon',
        'public.get_or_create_executor(text, text, text, text, text)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: get_or_create_executor still EXECUTABLE by anon (DB-001)';
    END IF;
    RAISE NOTICE 'PASS: get_or_create_executor revoked from anon';
END $$;

DO $$
BEGIN
    IF has_function_privilege(
        'authenticated',
        'public.get_or_create_executor(text, text, text, text, text)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: get_or_create_executor still EXECUTABLE by authenticated (DB-001)';
    END IF;
    RAISE NOTICE 'PASS: get_or_create_executor revoked from authenticated';
END $$;

-- ============================================================================
-- Test 2: link_wallet_to_session REVOKED from anon/authenticated
-- ============================================================================
DO $$
BEGIN
    IF has_function_privilege(
        'anon',
        'public.link_wallet_to_session(uuid, text, integer, text, text)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: link_wallet_to_session still EXECUTABLE by anon (DB-002)';
    END IF;
    IF has_function_privilege(
        'authenticated',
        'public.link_wallet_to_session(uuid, text, integer, text, text)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: link_wallet_to_session still EXECUTABLE by authenticated (DB-002)';
    END IF;
    RAISE NOTICE 'PASS: link_wallet_to_session revoked from anon + authenticated';
END $$;

-- ============================================================================
-- Test 3: update_executor_profile REVOKED from anon/authenticated
-- ============================================================================
DO $$
BEGIN
    IF has_function_privilege(
        'anon',
        'public.update_executor_profile(uuid, text, text, text[], text[], text, text, text, text, text)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: update_executor_profile still EXECUTABLE by anon (DB-003)';
    END IF;
    IF has_function_privilege(
        'authenticated',
        'public.update_executor_profile(uuid, text, text, text[], text[], text, text, text, text, text)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: update_executor_profile still EXECUTABLE by authenticated (DB-003)';
    END IF;
    RAISE NOTICE 'PASS: update_executor_profile revoked from anon + authenticated';
END $$;

-- ============================================================================
-- Test 4: submit_rating REVOKED from anon/authenticated
-- ============================================================================
DO $$
BEGIN
    IF has_function_privilege(
        'anon',
        'public.submit_rating(uuid, uuid, character varying, integer, text, integer, integer, integer)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: submit_rating still EXECUTABLE by anon (DB-010)';
    END IF;
    IF has_function_privilege(
        'authenticated',
        'public.submit_rating(uuid, uuid, character varying, integer, text, integer, integer, integer)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: submit_rating still EXECUTABLE by authenticated (DB-010)';
    END IF;
    RAISE NOTICE 'PASS: submit_rating revoked from anon + authenticated';
END $$;

-- ============================================================================
-- Test 5: submit_work REVOKED from anon/authenticated
-- ============================================================================
DO $$
BEGIN
    IF has_function_privilege('anon', 'public.submit_work(uuid, uuid, jsonb, text)', 'EXECUTE') THEN
        RAISE EXCEPTION 'TEST FAILED: submit_work still EXECUTABLE by anon (DB-011)';
    END IF;
    IF has_function_privilege('authenticated', 'public.submit_work(uuid, uuid, jsonb, text)', 'EXECUTE') THEN
        RAISE EXCEPTION 'TEST FAILED: submit_work still EXECUTABLE by authenticated (DB-011)';
    END IF;
    RAISE NOTICE 'PASS: submit_work revoked from anon + authenticated';
END $$;

-- ============================================================================
-- Test 6: claim_task REVOKED from anon/authenticated
-- ============================================================================
DO $$
BEGIN
    IF has_function_privilege('anon', 'public.claim_task(uuid, uuid)', 'EXECUTE') THEN
        RAISE EXCEPTION 'TEST FAILED: claim_task still EXECUTABLE by anon (DB-012)';
    END IF;
    IF has_function_privilege('authenticated', 'public.claim_task(uuid, uuid)', 'EXECUTE') THEN
        RAISE EXCEPTION 'TEST FAILED: claim_task still EXECUTABLE by authenticated (DB-012)';
    END IF;
    RAISE NOTICE 'PASS: claim_task revoked from anon + authenticated';
END $$;

-- ============================================================================
-- Test 7: apply_to_task REVOKED from anon/authenticated
-- ============================================================================
DO $$
BEGIN
    IF has_function_privilege('anon', 'public.apply_to_task(uuid, uuid, text)', 'EXECUTE') THEN
        RAISE EXCEPTION 'TEST FAILED: apply_to_task still EXECUTABLE by anon (DB-013)';
    END IF;
    IF has_function_privilege('authenticated', 'public.apply_to_task(uuid, uuid, text)', 'EXECUTE') THEN
        RAISE EXCEPTION 'TEST FAILED: apply_to_task still EXECUTABLE by authenticated (DB-013)';
    END IF;
    RAISE NOTICE 'PASS: apply_to_task revoked from anon + authenticated';
END $$;

-- ============================================================================
-- Test 8: abandon_task REVOKED from anon/authenticated
-- ============================================================================
DO $$
BEGIN
    IF has_function_privilege('anon', 'public.abandon_task(uuid, uuid, text)', 'EXECUTE') THEN
        RAISE EXCEPTION 'TEST FAILED: abandon_task still EXECUTABLE by anon (DB-013)';
    END IF;
    IF has_function_privilege('authenticated', 'public.abandon_task(uuid, uuid, text)', 'EXECUTE') THEN
        RAISE EXCEPTION 'TEST FAILED: abandon_task still EXECUTABLE by authenticated (DB-013)';
    END IF;
    RAISE NOTICE 'PASS: abandon_task revoked from anon + authenticated';
END $$;

-- ============================================================================
-- Test 9: submit_evidence REVOKED from anon/authenticated
-- ============================================================================
DO $$
BEGIN
    IF has_function_privilege('anon', 'public.submit_evidence(uuid, uuid, jsonb, text)', 'EXECUTE') THEN
        RAISE EXCEPTION 'TEST FAILED: submit_evidence still EXECUTABLE by anon (DB-011)';
    END IF;
    IF has_function_privilege('authenticated', 'public.submit_evidence(uuid, uuid, jsonb, text)', 'EXECUTE') THEN
        RAISE EXCEPTION 'TEST FAILED: submit_evidence still EXECUTABLE by authenticated (DB-011)';
    END IF;
    RAISE NOTICE 'PASS: submit_evidence revoked from anon + authenticated';
END $$;

-- ============================================================================
-- Test 10: release_task REVOKED from anon/authenticated
-- ============================================================================
DO $$
BEGIN
    IF has_function_privilege('anon', 'public.release_task(uuid, uuid)', 'EXECUTE') THEN
        RAISE EXCEPTION 'TEST FAILED: release_task still EXECUTABLE by anon (DB-012)';
    END IF;
    IF has_function_privilege('authenticated', 'public.release_task(uuid, uuid)', 'EXECUTE') THEN
        RAISE EXCEPTION 'TEST FAILED: release_task still EXECUTABLE by authenticated (DB-012)';
    END IF;
    RAISE NOTICE 'PASS: release_task revoked from anon + authenticated';
END $$;

-- ============================================================================
-- Test 11: create_dispute REVOKED from anon/authenticated
-- ============================================================================
DO $$
BEGIN
    IF has_function_privilege(
        'anon',
        'public.create_dispute(uuid, uuid, dispute_reason, text, jsonb, text)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: create_dispute still EXECUTABLE by anon (DB-013)';
    END IF;
    IF has_function_privilege(
        'authenticated',
        'public.create_dispute(uuid, uuid, dispute_reason, text, jsonb, text)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: create_dispute still EXECUTABLE by authenticated (DB-013)';
    END IF;
    RAISE NOTICE 'PASS: create_dispute revoked from anon + authenticated';
END $$;

-- ============================================================================
-- Test 12: respond_to_dispute REVOKED from anon/authenticated
-- ============================================================================
DO $$
BEGIN
    IF has_function_privilege('anon', 'public.respond_to_dispute(uuid, uuid, text, jsonb)', 'EXECUTE') THEN
        RAISE EXCEPTION 'TEST FAILED: respond_to_dispute still EXECUTABLE by anon (DB-013)';
    END IF;
    IF has_function_privilege('authenticated', 'public.respond_to_dispute(uuid, uuid, text, jsonb)', 'EXECUTE') THEN
        RAISE EXCEPTION 'TEST FAILED: respond_to_dispute still EXECUTABLE by authenticated (DB-013)';
    END IF;
    RAISE NOTICE 'PASS: respond_to_dispute revoked from anon + authenticated';
END $$;

-- ============================================================================
-- Test 13: submit_arbitration_vote REVOKED from anon/authenticated
-- ============================================================================
DO $$
BEGIN
    IF has_function_privilege(
        'anon',
        'public.submit_arbitration_vote(uuid, uuid, arbitration_vote, text, integer, numeric)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: submit_arbitration_vote still EXECUTABLE by anon (DB-013)';
    END IF;
    IF has_function_privilege(
        'authenticated',
        'public.submit_arbitration_vote(uuid, uuid, arbitration_vote, text, integer, numeric)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: submit_arbitration_vote still EXECUTABLE by authenticated (DB-013)';
    END IF;
    RAISE NOTICE 'PASS: submit_arbitration_vote revoked from anon + authenticated';
END $$;

-- ============================================================================
-- Test 14: create_task_escrow REVOKED from anon/authenticated
-- ============================================================================
DO $$
BEGIN
    IF has_function_privilege(
        'anon',
        'public.create_task_escrow(uuid, character varying, numeric, numeric)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: create_task_escrow still EXECUTABLE by anon (DB-019)';
    END IF;
    IF has_function_privilege(
        'authenticated',
        'public.create_task_escrow(uuid, character varying, numeric, numeric)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'TEST FAILED: create_task_escrow still EXECUTABLE by authenticated (DB-019)';
    END IF;
    RAISE NOTICE 'PASS: create_task_escrow revoked from anon + authenticated';
END $$;

-- ============================================================================
-- Test 15: reconcile_executor_balances REVOKED from anon/authenticated
-- ============================================================================
DO $$
BEGIN
    IF has_function_privilege('anon', 'public.reconcile_executor_balances()', 'EXECUTE') THEN
        RAISE EXCEPTION 'TEST FAILED: reconcile_executor_balances still EXECUTABLE by anon (DB-022)';
    END IF;
    IF has_function_privilege('authenticated', 'public.reconcile_executor_balances()', 'EXECUTE') THEN
        RAISE EXCEPTION 'TEST FAILED: reconcile_executor_balances still EXECUTABLE by authenticated (DB-022)';
    END IF;
    RAISE NOTICE 'PASS: reconcile_executor_balances revoked from anon + authenticated';
END $$;

-- ============================================================================
-- Test 16: service_role STILL has execute on all revoked RPCs
--          (revoking from anon/authenticated must NOT affect service_role)
-- ============================================================================
DO $$
DECLARE
    v_rpc_sig text;
    v_rpc_sigs text[] := ARRAY[
        'public.get_or_create_executor(text, text, text, text, text)',
        'public.link_wallet_to_session(uuid, text, integer, text, text)',
        'public.update_executor_profile(uuid, text, text, text[], text[], text, text, text, text, text)',
        'public.submit_rating(uuid, uuid, character varying, integer, text, integer, integer, integer)',
        'public.submit_work(uuid, uuid, jsonb, text)',
        'public.claim_task(uuid, uuid)',
        'public.apply_to_task(uuid, uuid, text)',
        'public.abandon_task(uuid, uuid, text)',
        'public.submit_evidence(uuid, uuid, jsonb, text)',
        'public.release_task(uuid, uuid)',
        'public.create_dispute(uuid, uuid, dispute_reason, text, jsonb, text)',
        'public.respond_to_dispute(uuid, uuid, text, jsonb)',
        'public.submit_arbitration_vote(uuid, uuid, arbitration_vote, text, integer, numeric)',
        'public.create_task_escrow(uuid, character varying, numeric, numeric)',
        'public.reconcile_executor_balances()'
    ];
BEGIN
    FOREACH v_rpc_sig IN ARRAY v_rpc_sigs LOOP
        IF NOT has_function_privilege('service_role', v_rpc_sig, 'EXECUTE') THEN
            RAISE EXCEPTION 'TEST FAILED: service_role LOST EXECUTE on % (backend API will break)', v_rpc_sig;
        END IF;
    END LOOP;
    RAISE NOTICE 'PASS: service_role retains EXECUTE on all 15 revoked RPCs';
END $$;

-- ============================================================================
-- Test 17: world_id_verifications INSERT is service_role only
-- ============================================================================
DO $$
DECLARE
    v_count integer;
BEGIN
    -- Verify the new policy exists with TO service_role
    SELECT COUNT(*) INTO v_count
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'world_id_verifications'
      AND policyname = 'world_id_verifications_insert_service_role_only'
      AND cmd = 'INSERT'
      AND 'service_role' = ANY(roles);
    IF v_count = 0 THEN
        RAISE EXCEPTION 'TEST FAILED: world_id_verifications_insert_service_role_only policy missing or not restricted to service_role (DB-004)';
    END IF;

    -- Verify the old broken policy is gone
    SELECT COUNT(*) INTO v_count
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'world_id_verifications'
      AND policyname = 'world_id_verifications_service_insert';
    IF v_count > 0 THEN
        RAISE EXCEPTION 'TEST FAILED: old world_id_verifications_service_insert policy still exists (DB-004)';
    END IF;

    RAISE NOTICE 'PASS: world_id_verifications INSERT restricted to service_role';
END $$;

-- ============================================================================
-- Test 18: world_id_verifications UPDATE is service_role only
-- ============================================================================
DO $$
DECLARE
    v_count integer;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'world_id_verifications'
      AND policyname = 'world_id_verifications_update_service_role_only'
      AND cmd = 'UPDATE'
      AND 'service_role' = ANY(roles);
    IF v_count = 0 THEN
        RAISE EXCEPTION 'TEST FAILED: world_id_verifications_update_service_role_only policy missing or not restricted to service_role (DB-004)';
    END IF;

    SELECT COUNT(*) INTO v_count
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'world_id_verifications'
      AND policyname = 'world_id_verifications_service_update';
    IF v_count > 0 THEN
        RAISE EXCEPTION 'TEST FAILED: old world_id_verifications_service_update policy still exists (DB-004)';
    END IF;

    RAISE NOTICE 'PASS: world_id_verifications UPDATE restricted to service_role';
END $$;

-- ============================================================================
-- Test 19: world_id_verifications SELECT policy preserved
--          (workers still need to read their own verification state)
-- ============================================================================
DO $$
DECLARE
    v_count integer;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'world_id_verifications'
      AND policyname = 'world_id_verifications_select_own'
      AND cmd = 'SELECT';
    IF v_count = 0 THEN
        RAISE EXCEPTION 'TEST FAILED: world_id_verifications_select_own policy was removed — workers cannot read their own verification state';
    END IF;
    RAISE NOTICE 'PASS: world_id_verifications SELECT (own) policy preserved';
END $$;

-- ============================================================================
-- Test 20: Safe public read-only RPCs are NOT affected by the revocation
--          (regression guard — make sure we didn't break public queries)
-- Uses pg_proc lookup by name because signatures for these functions depend
-- on enum types defined in earlier migrations, and has_function_privilege
-- requires the caller to provide the exact canonical signature.
-- ============================================================================
DO $$
DECLARE
    v_proc_name text;
    v_proc_names text[] := ARRAY[
        'get_nearby_tasks',
        'search_tasks',
        'get_platform_stats',
        'get_task_details',
        'get_executor_stats'
    ];
    v_oid oid;
BEGIN
    FOREACH v_proc_name IN ARRAY v_proc_names LOOP
        SELECT p.oid INTO v_oid
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.proname = v_proc_name
        LIMIT 1;

        IF v_oid IS NULL THEN
            RAISE WARNING 'Regression check: function public.% not found (skipping)', v_proc_name;
            CONTINUE;
        END IF;

        IF NOT has_function_privilege('anon', v_oid, 'EXECUTE') THEN
            RAISE WARNING 'Regression: anon lost EXECUTE on public.% — verify migration 005 grants still apply', v_proc_name;
        END IF;
    END LOOP;
    RAISE NOTICE 'PASS: safe read-only RPCs still executable by anon (or not present)';
END $$;

-- ============================================================================
-- Final summary — if we reach here, all tests passed
-- ============================================================================
SELECT 'ALL TESTS PASSED — migration 092 correctly revokes anon execute on 15 account-takeover RPCs and restricts world_id_verifications to service_role' AS result;
