-- Migration 092: Phase 0 GR-0.3 — Revoke anon/authenticated execute from account-takeover RPCs
-- Security audit 2026-04-07 (specialist SC_06_DATABASE_SUPABASE)
-- Closes: DB-001, DB-002, DB-003, DB-004, DB-009, DB-010, DB-011, DB-012, DB-013, DB-019, DB-022
--
-- CONTEXT
-- -------
-- The dashboard supabase-js client talks to Supabase REST directly, bypassing
-- the FastAPI backend. RLS and RPC grants are the ONLY trust boundary between
-- an anonymous browser and full database access. The 2026-04-07 security audit
-- identified 8 CRITICAL account-takeover vectors where SECURITY DEFINER RPCs
-- accept caller-supplied identity parameters (p_executor_id, p_user_id,
-- p_wallet_address, p_arbitrator_id, ...) without verifying them against
-- auth.uid(). Any browser with the public anon JWT could:
--
--   * DB-001: rebind an existing executor row to a new user_id by calling
--             get_or_create_executor with a wallet that already exists
--             (COALESCE(v_user_id, executors.user_id) overwrites on every call)
--   * DB-002: link ANY wallet to ANY user_id via link_wallet_to_session
--             (p_user_id is passed directly, never compared to auth.uid())
--   * DB-003: edit ANY executor profile by calling update_executor_profile
--             with a known p_executor_id (no ownership check at all)
--   * DB-004: insert forged World ID verifications (the existing INSERT policy
--             has WITH CHECK (true) with no role restriction)
--   * DB-009: insert submissions on behalf of ANY executor (the existing
--             INSERT policy is `executor_id IN (SELECT id FROM executors)`
--             which accepts any existing executor_id without ownership check)
--   * DB-010..013: submit ratings, claim tasks, apply to tasks, submit work,
--             abandon tasks, submit evidence, release tasks, dispute tasks,
--             and vote in arbitration — all on behalf of anyone
--   * DB-019: create escrow records for any task
--   * DB-022: run balance reconciliation (information disclosure)
--
-- This migration forces all these RPCs through the backend (service_role)
-- instead of the browser (anon/authenticated). The FastAPI backend is the
-- only trust boundary that can validate the caller's identity using
-- ERC-8128 wallet signing and session ownership.
--
-- SIDE EFFECT
-- -----------
-- Any dashboard code that calls these RPCs directly will start failing with
-- HTTP 403. This is INTENTIONAL. GR-1.7 will migrate the dashboard to use
-- the backend REST API (https://api.execution.market/api/v1/*) which
-- authenticates the caller via wallet signature and then calls the RPC as
-- service_role.
--
-- REVOKED RPCs (15 functions)
-- ---------------------------
--   get_or_create_executor(text, text, text, text, text)                       DB-001
--   link_wallet_to_session(uuid, text, integer, text, text)                    DB-002
--   update_executor_profile(uuid, text, text, text[], text[], text, text,
--                           text, text, text)                                  DB-003
--   submit_rating(uuid, uuid, varchar, integer, text, integer, integer,
--                 integer)                                                     DB-010
--   submit_work(uuid, uuid, jsonb, text)                                       DB-011
--   claim_task(uuid, uuid)                                                     DB-012
--   apply_to_task(uuid, uuid, text)                                            DB-013
--   abandon_task(uuid, uuid, text)                                             DB-013
--   submit_evidence(uuid, uuid, jsonb, text)                                   DB-011
--   release_task(uuid, uuid)                                                   DB-012
--   create_dispute(uuid, uuid, dispute_reason, text, jsonb, text)              DB-013
--   respond_to_dispute(uuid, uuid, text, jsonb)                                DB-013
--   submit_arbitration_vote(uuid, uuid, arbitration_vote, text,
--                           integer, numeric)                                  DB-013
--   create_task_escrow(uuid, varchar, numeric, numeric)                        DB-019
--   reconcile_executor_balances()                                              DB-022
--
-- DELIBERATELY LEFT GRANTED TO ANON/AUTHENTICATED (safe — audited 2026-04-09)
-- ---------------------------------------------------------------------------
--   get_nearby_tasks       — read-only, filters to status='published' only
--   search_tasks           — read-only, filters to status='published' only
--   get_task_details       — read-only, parameter is task_id (public info)
--   get_platform_stats     — read-only, aggregates public counters
--   get_executor_stats     — read-only; uses caller-supplied id BUT returns
--                            only public fields (reputation, tasks_completed,
--                            tier, badges count). Worth revisiting in GR-1.x
--                            to strip balance_usdc / total_earned_usdc if any
--                            is exposed.
--   get_executor_tasks     — read-only; returns task list filtered by id.
--                            Caller-supplied id leaks *which tasks* the
--                            executor is working on, but not credentials.
--                            Safe for now, flagged for GR-1.x to require
--                            service_role.
--   assign_task_to_executor — already service_role ONLY (verified)
--   complete_submission    — already service_role ONLY (verified)
--   expire_overdue_tasks   — already service_role ONLY (verified)
--   escalate_to_arbitration — no anon/authenticated grant found (default-deny)
--
-- NOTE ON IDEMPOTENCY
-- -------------------
-- REVOKE is idempotent in PostgreSQL: revoking a privilege that was never
-- granted is a no-op (NOTICE, not ERROR). This migration is safe to re-run.

BEGIN;

-- ============================================================================
-- 1. REVOKE EXECUTE FROM PUBLIC, anon, authenticated on account-takeover RPCs
-- ============================================================================
--
-- IMPORTANT: PostgreSQL grants EXECUTE to PUBLIC by default on newly created
-- functions. In Supabase, `anon` and `authenticated` are members of PUBLIC, so
-- revoking ONLY from `anon`/`authenticated` is not enough — we must also
-- revoke from PUBLIC, otherwise the grant survives via inheritance.
--
-- DEFENSIVE: Each REVOKE/GRANT/COMMENT is wrapped in a DO/EXCEPTION block
-- so that functions which do not exist in the target database are skipped
-- gracefully (NOTICE instead of ERROR). This handles production databases
-- where some migrations were applied out of order or functions were dropped.

-- Helper: revoke + grant in one block, skip if function does not exist
CREATE OR REPLACE FUNCTION _092_safe_revoke_and_grant(p_func_sig text)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE format('REVOKE EXECUTE ON FUNCTION %s FROM PUBLIC, anon, authenticated', p_func_sig);
    EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO service_role', p_func_sig);
    RAISE NOTICE '092: locked down %', p_func_sig;
EXCEPTION WHEN undefined_function OR undefined_object THEN
    RAISE NOTICE '092: SKIPPED % (function does not exist in this database)', p_func_sig;
END;
$$;

-- DB-002 stale overload: drop defensively before revoking
DROP FUNCTION IF EXISTS public.link_wallet_to_session(uuid, text, integer);

-- DB-001
SELECT _092_safe_revoke_and_grant('public.get_or_create_executor(text, text, text, text, text)');
-- DB-002
SELECT _092_safe_revoke_and_grant('public.link_wallet_to_session(uuid, text, integer, text, text)');
-- DB-003
SELECT _092_safe_revoke_and_grant('public.update_executor_profile(uuid, text, text, text[], text[], text, text, text, text, text)');
-- DB-010
SELECT _092_safe_revoke_and_grant('public.submit_rating(uuid, uuid, character varying, integer, text, integer, integer, integer)');
-- DB-011
SELECT _092_safe_revoke_and_grant('public.submit_work(uuid, uuid, jsonb, text)');
-- DB-012
SELECT _092_safe_revoke_and_grant('public.claim_task(uuid, uuid)');
-- DB-013
SELECT _092_safe_revoke_and_grant('public.apply_to_task(uuid, uuid, text)');
-- DB-013
SELECT _092_safe_revoke_and_grant('public.abandon_task(uuid, uuid, text)');
-- DB-011
SELECT _092_safe_revoke_and_grant('public.submit_evidence(uuid, uuid, jsonb, text)');
-- DB-012
SELECT _092_safe_revoke_and_grant('public.release_task(uuid, uuid)');
-- DB-013
SELECT _092_safe_revoke_and_grant('public.create_dispute(uuid, uuid, dispute_reason, text, jsonb, text)');
-- DB-013
SELECT _092_safe_revoke_and_grant('public.respond_to_dispute(uuid, uuid, text, jsonb)');
-- DB-013
SELECT _092_safe_revoke_and_grant('public.submit_arbitration_vote(uuid, uuid, arbitration_vote, text, integer, numeric)');
-- DB-019
SELECT _092_safe_revoke_and_grant('public.create_task_escrow(uuid, character varying, numeric, numeric)');
-- DB-022
SELECT _092_safe_revoke_and_grant('public.reconcile_executor_balances()');

-- Clean up the helper function (one-shot, not needed after migration)
DROP FUNCTION _092_safe_revoke_and_grant(text);


-- ============================================================================
-- 2. Fix world_id_verifications INSERT/UPDATE policies (DB-004)
-- ============================================================================
--
-- Migration 085 created these policies with WITH CHECK (true) but no role
-- restriction, meaning anon can insert forged Orb-level verifications and
-- defeat the anti-sybil mechanism entirely. The only trust boundary for
-- World ID verification is the backend (which calls the World ID Cloud API
-- and signs proofs server-side). Restrict both INSERT and UPDATE to
-- service_role only.

-- Drop the broken INSERT policy from migration 085
DROP POLICY IF EXISTS "world_id_verifications_service_insert" ON world_id_verifications;
-- Defensive: also drop any variant names that might exist in production
DROP POLICY IF EXISTS "world_id_verifications_insert" ON world_id_verifications;
DROP POLICY IF EXISTS "Users can insert their own verifications" ON world_id_verifications;

CREATE POLICY "world_id_verifications_insert_service_role_only"
    ON world_id_verifications
    FOR INSERT
    TO service_role
    WITH CHECK (true);

-- Drop the broken UPDATE policy from migration 085
DROP POLICY IF EXISTS "world_id_verifications_service_update" ON world_id_verifications;
-- Defensive: also drop any variant names
DROP POLICY IF EXISTS "world_id_verifications_update" ON world_id_verifications;

CREATE POLICY "world_id_verifications_update_service_role_only"
    ON world_id_verifications
    FOR UPDATE
    TO service_role
    USING (true)
    WITH CHECK (true);

-- NOTE: the SELECT policy "world_id_verifications_select_own" from migration
-- 085 is intentionally preserved. It correctly scopes reads to rows where
-- the caller owns the linked executor via auth.uid(). This is the only
-- policy workers need to read their own verification state from the browser.


-- ============================================================================
-- 3. Comments documenting the revocation (defensive — skip if function missing)
-- ============================================================================

CREATE OR REPLACE FUNCTION _092_safe_comment(p_func_sig text, p_comment text)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE format('COMMENT ON FUNCTION %s IS %L', p_func_sig, p_comment);
EXCEPTION WHEN undefined_function OR undefined_object THEN
    RAISE NOTICE '092: COMMENT skipped for % (does not exist)', p_func_sig;
END;
$$;

SELECT _092_safe_comment('public.get_or_create_executor(text, text, text, text, text)',
    'REVOKED from anon/authenticated 2026-04-09 (GR-0.3, DB-001). Service_role only.');
SELECT _092_safe_comment('public.link_wallet_to_session(uuid, text, integer, text, text)',
    'REVOKED from anon/authenticated 2026-04-09 (GR-0.3, DB-002). Service_role only.');
SELECT _092_safe_comment('public.update_executor_profile(uuid, text, text, text[], text[], text, text, text, text, text)',
    'REVOKED from anon/authenticated 2026-04-09 (GR-0.3, DB-003). Service_role only.');
SELECT _092_safe_comment('public.submit_rating(uuid, uuid, character varying, integer, text, integer, integer, integer)',
    'REVOKED from anon/authenticated 2026-04-09 (GR-0.3, DB-010). Service_role only.');
SELECT _092_safe_comment('public.submit_work(uuid, uuid, jsonb, text)',
    'REVOKED from anon/authenticated 2026-04-09 (GR-0.3, DB-011). Service_role only.');
SELECT _092_safe_comment('public.claim_task(uuid, uuid)',
    'REVOKED from anon/authenticated 2026-04-09 (GR-0.3, DB-012). Service_role only.');
SELECT _092_safe_comment('public.apply_to_task(uuid, uuid, text)',
    'REVOKED from anon/authenticated 2026-04-09 (GR-0.3, DB-013). Service_role only.');
SELECT _092_safe_comment('public.abandon_task(uuid, uuid, text)',
    'REVOKED from anon/authenticated 2026-04-09 (GR-0.3, DB-013). Service_role only.');
SELECT _092_safe_comment('public.submit_evidence(uuid, uuid, jsonb, text)',
    'REVOKED from anon/authenticated 2026-04-09 (GR-0.3, DB-011). Service_role only.');
SELECT _092_safe_comment('public.release_task(uuid, uuid)',
    'REVOKED from anon/authenticated 2026-04-09 (GR-0.3, DB-012). Service_role only.');
SELECT _092_safe_comment('public.create_dispute(uuid, uuid, dispute_reason, text, jsonb, text)',
    'REVOKED from anon/authenticated 2026-04-09 (GR-0.3, DB-013). Service_role only.');
SELECT _092_safe_comment('public.respond_to_dispute(uuid, uuid, text, jsonb)',
    'REVOKED from anon/authenticated 2026-04-09 (GR-0.3, DB-013). Service_role only.');
SELECT _092_safe_comment('public.submit_arbitration_vote(uuid, uuid, arbitration_vote, text, integer, numeric)',
    'REVOKED from anon/authenticated 2026-04-09 (GR-0.3, DB-013). Service_role only.');
SELECT _092_safe_comment('public.create_task_escrow(uuid, character varying, numeric, numeric)',
    'REVOKED from anon/authenticated 2026-04-09 (GR-0.3, DB-019). Service_role only.');
SELECT _092_safe_comment('public.reconcile_executor_balances()',
    'REVOKED from anon/authenticated 2026-04-09 (GR-0.3, DB-022). Admin tool.');

DROP FUNCTION _092_safe_comment(text, text);

COMMIT;


-- ============================================================================
-- ROLLBACK (run this block manually to undo migration 092)
-- ============================================================================
-- BEGIN;
--
-- -- Restore PUBLIC + anon + authenticated grants on all 15 RPCs
-- GRANT EXECUTE ON FUNCTION public.get_or_create_executor(text, text, text, text, text)
--     TO PUBLIC, anon, authenticated;
-- GRANT EXECUTE ON FUNCTION public.link_wallet_to_session(uuid, text, integer, text, text)
--     TO PUBLIC, anon, authenticated;
-- GRANT EXECUTE ON FUNCTION public.update_executor_profile(
--     uuid, text, text, text[], text[], text, text, text, text, text
-- ) TO PUBLIC, anon, authenticated;
-- GRANT EXECUTE ON FUNCTION public.submit_rating(
--     uuid, uuid, character varying, integer, text, integer, integer, integer
-- ) TO PUBLIC, anon, authenticated;
-- GRANT EXECUTE ON FUNCTION public.submit_work(uuid, uuid, jsonb, text)
--     TO PUBLIC, anon, authenticated;
-- GRANT EXECUTE ON FUNCTION public.claim_task(uuid, uuid)
--     TO PUBLIC, anon, authenticated;
-- GRANT EXECUTE ON FUNCTION public.apply_to_task(uuid, uuid, text)
--     TO PUBLIC, anon, authenticated;
-- GRANT EXECUTE ON FUNCTION public.abandon_task(uuid, uuid, text)
--     TO PUBLIC, anon, authenticated;
-- GRANT EXECUTE ON FUNCTION public.submit_evidence(uuid, uuid, jsonb, text)
--     TO PUBLIC, anon, authenticated;
-- GRANT EXECUTE ON FUNCTION public.release_task(uuid, uuid)
--     TO PUBLIC, anon, authenticated;
-- GRANT EXECUTE ON FUNCTION public.create_dispute(
--     uuid, uuid, dispute_reason, text, jsonb, text
-- ) TO PUBLIC, anon, authenticated;
-- GRANT EXECUTE ON FUNCTION public.respond_to_dispute(uuid, uuid, text, jsonb)
--     TO PUBLIC, anon, authenticated;
-- GRANT EXECUTE ON FUNCTION public.submit_arbitration_vote(
--     uuid, uuid, arbitration_vote, text, integer, numeric
-- ) TO PUBLIC, anon, authenticated;
-- GRANT EXECUTE ON FUNCTION public.create_task_escrow(
--     uuid, character varying, numeric, numeric
-- ) TO PUBLIC, anon, authenticated;
-- GRANT EXECUTE ON FUNCTION public.reconcile_executor_balances()
--     TO PUBLIC, anon, authenticated;
--
-- -- Restore broken world_id policies (NOT RECOMMENDED — leaves anti-sybil open)
-- DROP POLICY IF EXISTS "world_id_verifications_insert_service_role_only" ON world_id_verifications;
-- DROP POLICY IF EXISTS "world_id_verifications_update_service_role_only" ON world_id_verifications;
--
-- CREATE POLICY "world_id_verifications_service_insert"
--     ON world_id_verifications FOR INSERT WITH CHECK (true);
-- CREATE POLICY "world_id_verifications_service_update"
--     ON world_id_verifications FOR UPDATE USING (true);
--
-- -- NOTE: the (uuid, text, integer) 3-arg overload of link_wallet_to_session
-- -- was dropped by migration 092 and is NOT restored here. If you need it back,
-- -- re-run a version of migration 008.
--
-- COMMIT;
-- ============================================================================
