-- Test suite for migrations 111-117 (Security Audit 2026-06-09)
-- Covers: FIX-P0-02, FIX-P1-03, FIX-P1-04, FIX-P1-05, FIX-P1-08, DB-004 (Phase 2.3),
--         anon read-surface lockdown (Phase 2.4).
--
-- HOW TO RUN
-- ----------
--   Apply migrations 001..117 (or the minimal fixture + 111..117), then:
--     psql "$DATABASE_URL" -f supabase/tests/test_migration_111_to_117.sql
--   Each DO $$ block raises EXCEPTION on failure (aborts) and NOTICE on pass.
--   No pgTAP required — runs in the plain Supabase SQL Editor.
--
-- These tests assert the *privilege/grant* end-state. The behavioural reproducers
-- (identity rebind, trust-flag self-elevation, recusal) are exercised by the
-- backend/integration suites and the operator E2E steps in the fix docs.

\set ON_ERROR_STOP on

-- ============================================================================
-- FIX-P0-02 (migration 111): get_or_create_executor locked to service_role only
-- ============================================================================
DO $$
BEGIN
    IF has_function_privilege('anon',
        'public.get_or_create_executor(text,text,text,text,text)', 'EXECUTE') THEN
        RAISE EXCEPTION 'FAIL P0-02: get_or_create_executor still EXECUTABLE by anon';
    END IF;
    IF has_function_privilege('authenticated',
        'public.get_or_create_executor(text,text,text,text,text)', 'EXECUTE') THEN
        RAISE EXCEPTION 'FAIL P0-02: get_or_create_executor still EXECUTABLE by authenticated';
    END IF;
    IF NOT has_function_privilege('service_role',
        'public.get_or_create_executor(text,text,text,text,text)', 'EXECUTE') THEN
        RAISE EXCEPTION 'FAIL P0-02: get_or_create_executor NOT executable by service_role (backend broken)';
    END IF;
    RAISE NOTICE 'PASS P0-02: get_or_create_executor anon=f authenticated=f service_role=t';
END $$;

-- Body hardening present (CASE branch that denies silent takeover).
DO $$
BEGIN
    -- Match on the actual hardening constructs (present in both the forward
    -- migration and the standalone hotfix): the wallet-ownership flag and the
    -- CASE that preserves the existing owner when ownership is not proven.
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE proname = 'get_or_create_executor'
          AND prosrc LIKE '%v_owns_wallet%'
          AND prosrc LIKE '%v_existing_user_id = v_user_id%'
    ) THEN
        RAISE EXCEPTION 'FAIL P0-02: get_or_create_executor body not hardened (missing v_owns_wallet/recusal CASE)';
    END IF;
    RAISE NOTICE 'PASS P0-02: get_or_create_executor body hardened (ownership-proof rebind)';
END $$;

-- ============================================================================
-- FIX-P1-04 (migration 112): tampering guard covers trust/financial/identity cols
-- ============================================================================
DO $$
DECLARE
    body text;
    col text;
    cols text[] := ARRAY[
        'world_id_verified','world_id_level','veryai_verified','veryai_level',
        'veryai_sub','veryai_verified_at','clawkey_verified','clawkey_human_id',
        'clawkey_device_id','clawkey_public_key','clawkey_registered_at',
        'is_verified','kyc_completed_at','balance_usdc','total_earned_usdc',
        'total_withdrawn_usdc','wallet_address','status','erc8004_agent_id'];
BEGIN
    SELECT prosrc INTO body FROM pg_proc WHERE proname = 'prevent_executor_tampering';
    IF body IS NULL THEN
        RAISE EXCEPTION 'FAIL P1-04: prevent_executor_tampering() does not exist';
    END IF;
    FOREACH col IN ARRAY cols LOOP
        IF position(col IN body) = 0 THEN
            RAISE EXCEPTION 'FAIL P1-04: guard does not protect column %', col;
        END IF;
    END LOOP;
    RAISE NOTICE 'PASS P1-04: guard protects all 19 trust/financial/identity columns';
END $$;

-- Trigger present with the service_role bypass.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'guard_executor_immutable_fields'
          AND tgrelid = 'public.executors'::regclass) THEN
        RAISE EXCEPTION 'FAIL P1-04: guard_executor_immutable_fields trigger missing';
    END IF;
    RAISE NOTICE 'PASS P1-04: guard trigger present on executors';
END $$;

-- ============================================================================
-- FIX-P1-05 (migration 113): NO non-allowlisted SECURITY DEFINER func in public
-- is anon/authenticated-executable.
-- ============================================================================
DO $$
DECLARE
    leaked text;
BEGIN
    SELECT string_agg(p.oid::regprocedure::text, ', ')
    INTO leaked
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.prosecdef
      AND p.proname <> 'get_or_create_executor'
      AND ( has_function_privilege('anon', p.oid, 'EXECUTE')
         OR has_function_privilege('authenticated', p.oid, 'EXECUTE') );
    IF leaked IS NOT NULL THEN
        RAISE EXCEPTION 'FAIL P1-05: SECURITY DEFINER funcs still anon/authenticated-executable: %', leaked;
    END IF;
    RAISE NOTICE 'PASS P1-05: no anon-executable SECURITY DEFINER funcs remain';
END $$;

-- Explicit per-function assertions for the previously-false 092:83-86 claims.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
               WHERE n.nspname='public' AND p.proname='resolve_dispute'
                 AND has_function_privilege('anon', p.oid, 'EXECUTE')) THEN
        RAISE EXCEPTION 'FAIL P1-05: resolve_dispute still anon-executable';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
               WHERE n.nspname='public' AND p.proname='fund_escrow'
                 AND has_function_privilege('anon', p.oid, 'EXECUTE')) THEN
        RAISE EXCEPTION 'FAIL P1-05: fund_escrow still anon-executable';
    END IF;
    RAISE NOTICE 'PASS P1-05: resolve_dispute + fund_escrow not anon-executable';
END $$;

-- ============================================================================
-- FIX-P1-03 (migration 114): payment_events grant end-state
-- ============================================================================
DO $$
BEGIN
    IF has_table_privilege('anon', 'public.payment_events', 'SELECT')
       OR has_table_privilege('anon', 'public.payment_events', 'INSERT') THEN
        RAISE EXCEPTION 'FAIL P1-03: anon still has access to payment_events';
    END IF;
    IF has_table_privilege('authenticated', 'public.payment_events', 'INSERT')
       OR has_table_privilege('authenticated', 'public.payment_events', 'UPDATE')
       OR has_table_privilege('authenticated', 'public.payment_events', 'DELETE') THEN
        RAISE EXCEPTION 'FAIL P1-03: authenticated still has write access to payment_events';
    END IF;
    IF NOT has_table_privilege('authenticated', 'public.payment_events', 'SELECT') THEN
        RAISE EXCEPTION 'FAIL P1-03: authenticated lost SELECT (migration-045 own-tasks policy broken)';
    END IF;
    RAISE NOTICE 'PASS P1-03: payment_events anon=none, authenticated=SELECT-only';
END $$;

-- ============================================================================
-- FIX-P1-08 (migration 115): recusal trigger present
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'trg_dispute_resolver_recusal'
          AND tgrelid = 'public.disputes'::regclass) THEN
        RAISE EXCEPTION 'FAIL P1-08: trg_dispute_resolver_recusal trigger missing';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname='enforce_dispute_resolver_recusal') THEN
        RAISE EXCEPTION 'FAIL P1-08: enforce_dispute_resolver_recusal() missing';
    END IF;
    RAISE NOTICE 'PASS P1-08: dispute resolver recusal trigger installed';
END $$;

-- ============================================================================
-- DB-004 / Phase 2.3 (migration 116): veryai + agent_kya write lockdown
-- ============================================================================
DO $$
BEGIN
    IF has_table_privilege('anon', 'public.veryai_verifications', 'INSERT')
       OR has_table_privilege('authenticated', 'public.veryai_verifications', 'INSERT')
       OR has_table_privilege('anon', 'public.agent_kya_verifications', 'INSERT')
       OR has_table_privilege('authenticated', 'public.agent_kya_verifications', 'INSERT') THEN
        RAISE EXCEPTION 'FAIL DB-004: anon/authenticated can still INSERT verification rows';
    END IF;
    RAISE NOTICE 'PASS DB-004: anon/authenticated cannot write veryai/agent_kya verifications';
END $$;

-- Write policies are service_role-scoped (no unrestricted WITH CHECK(true) policy left).
DO $$
DECLARE
    bad int;
BEGIN
    SELECT count(*) INTO bad
    FROM pg_policies
    WHERE schemaname='public'
      AND tablename IN ('veryai_verifications','agent_kya_verifications')
      AND cmd IN ('INSERT','UPDATE','DELETE')
      AND (roles = '{public}' OR roles IS NULL OR 'public' = ANY(roles));
    IF bad > 0 THEN
        RAISE EXCEPTION 'FAIL DB-004: % unrestricted (public-role) write policy(ies) still present', bad;
    END IF;
    RAISE NOTICE 'PASS DB-004: all veryai/agent_kya write policies are role-restricted';
END $$;

-- ============================================================================
-- Phase 2.4 (migration 117): v_orphaned_payments anon read locked down
-- ============================================================================
DO $$
BEGIN
    IF has_table_privilege('anon', 'public.v_orphaned_payments', 'SELECT')
       OR has_table_privilege('authenticated', 'public.v_orphaned_payments', 'SELECT') THEN
        RAISE EXCEPTION 'FAIL 2.4: v_orphaned_payments still readable by anon/authenticated';
    END IF;
    IF NOT has_table_privilege('service_role', 'public.v_orphaned_payments', 'SELECT') THEN
        RAISE EXCEPTION 'FAIL 2.4: service_role lost SELECT on v_orphaned_payments (health checks broken)';
    END IF;
    IF has_function_privilege('anon', 'public.get_orphaned_payment_count()', 'EXECUTE') THEN
        RAISE EXCEPTION 'FAIL 2.4: get_orphaned_payment_count still anon-executable';
    END IF;
    RAISE NOTICE 'PASS 2.4: v_orphaned_payments + count locked to service_role';
END $$;

SELECT 'ALL TESTS PASSED (migrations 111-117)' AS result;
