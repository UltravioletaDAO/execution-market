-- Behavioural reproducer tests for FIX-P0-02 (identity rebind), FIX-P1-04
-- (trust-flag self-elevation), FIX-P1-08 (dispute resolver recusal), DB-004
-- (anon-writable verification tables). Security Audit 2026-06-09.
--
-- These exercise the actual exploit paths (not just grant state). Each test
-- runs the attack and asserts it is now BLOCKED, plus asserts the legitimate
-- path still works. On a database at migration <= 110 (pre-fix) the "blocked"
-- assertions FAIL (the bug is reproduced); at >= 117 they PASS.
--
-- HOW TO RUN
-- ----------
--   Apply migrations through 117, then:
--     psql "$DATABASE_URL" -f supabase/tests/test_fix_p0_02_p1_04_p1_08_behavior.sql
--   Requires the Supabase auth.uid()/auth.jwt() shims and the anon/authenticated/
--   service_role roles (present in any Supabase project).
--
-- NOTE: these tests INSERT and then clean up their own fixture rows under a
-- dedicated wallet prefix (0xfeed...) so they are safe to run against a branch DB.

\set ON_ERROR_STOP on

-- ---------------------------------------------------------------------------
-- Setup: a victim executor owned by VICTIM_UID, inserted as service_role so the
-- immutable-field guard does not interfere with fixture creation.
-- ---------------------------------------------------------------------------
SET ROLE service_role;
DELETE FROM executors WHERE wallet_address LIKE '0xfeed%';
INSERT INTO executors (id, user_id, wallet_address)
VALUES ('feed0000-0000-0000-0000-000000000001',
        'feedaaaa-0000-0000-0000-00000000000a',
        '0xfeed000000000000000000000000000000000001');
INSERT INTO executors (id, user_id, wallet_address, world_id_verified, balance_usdc)
VALUES ('feed0000-0000-0000-0000-000000000002',
        'feedbbbb-0000-0000-0000-00000000000b',
        '0xfeed000000000000000000000000000000000002', false, 0);
RESET ROLE;

-- ===========================================================================
-- FIX-P0-02: attacker session must NOT rebind a victim executor.
-- The function is service_role-only now, so we invoke it via service_role
-- (the backend path) but with an ATTACKER auth.uid() and no proving wallet
-- claim. The hardened body must leave user_id pointing at the victim.
-- ===========================================================================
DO $$
DECLARE v_owner uuid;
BEGIN
    PERFORM set_config('request.jwt.claim.sub', 'feedcccc-0000-0000-0000-00000000000c', true);  -- attacker uid
    PERFORM set_config('request.jwt.claims', '{}', true);                                        -- no wallet claim
    PERFORM get_or_create_executor('0xfeed000000000000000000000000000000000001');
    SELECT user_id INTO v_owner FROM executors WHERE wallet_address='0xfeed000000000000000000000000000000000001';
    IF v_owner <> 'feedaaaa-0000-0000-0000-00000000000a' THEN
        RAISE EXCEPTION 'FAIL P0-02: takeover succeeded — user_id became % (expected victim)', v_owner;
    END IF;
    RAISE NOTICE 'PASS P0-02: attacker rebind denied (victim ownership preserved)';
END $$;

-- Proven-owner rebind (JWT carries matching wallet claim) IS allowed.
DO $$
DECLARE v_owner uuid;
BEGIN
    PERFORM set_config('request.jwt.claim.sub', 'feeddddd-0000-0000-0000-00000000000d', true);
    PERFORM set_config('request.jwt.claims',
        '{"user_metadata":{"wallet_address":"0xfeed000000000000000000000000000000000001"}}', true);
    PERFORM get_or_create_executor('0xfeed000000000000000000000000000000000001');
    SELECT user_id INTO v_owner FROM executors WHERE wallet_address='0xfeed000000000000000000000000000000000001';
    IF v_owner <> 'feeddddd-0000-0000-0000-00000000000d' THEN
        RAISE EXCEPTION 'FAIL P0-02: proven-owner rebind did not apply (user_id=%)', v_owner;
    END IF;
    RAISE NOTICE 'PASS P0-02: proven-owner rebind allowed';
END $$;

-- ===========================================================================
-- FIX-P1-04: a worker (authenticated) cannot self-set trust/financial columns,
-- but legitimate profile edits succeed and service_role writes succeed.
-- ===========================================================================
DO $$
DECLARE blocked boolean := false;
BEGIN
    SET LOCAL ROLE authenticated;
    BEGIN
        UPDATE executors SET world_id_verified=true, world_id_level='orb'
        WHERE id='feed0000-0000-0000-0000-000000000002';
    EXCEPTION WHEN OTHERS THEN blocked := true; END;
    IF NOT blocked THEN
        RAISE EXCEPTION 'FAIL P1-04: worker self-set world_id_verified/orb succeeded (anti-sybil bypass)';
    END IF;
    RAISE NOTICE 'PASS P1-04: worker cannot self-set World ID orb';
END $$;

DO $$
DECLARE blocked boolean := false;
BEGIN
    SET LOCAL ROLE authenticated;
    BEGIN
        UPDATE executors SET balance_usdc=1000000 WHERE id='feed0000-0000-0000-0000-000000000002';
    EXCEPTION WHEN OTHERS THEN blocked := true; END;
    IF NOT blocked THEN RAISE EXCEPTION 'FAIL P1-04: worker inflated balance_usdc'; END IF;
    RAISE NOTICE 'PASS P1-04: worker cannot inflate balance';
END $$;

DO $$
BEGIN
    SET LOCAL ROLE authenticated;
    UPDATE executors SET display_name='legit', bio='b', skills=ARRAY['s']
    WHERE id='feed0000-0000-0000-0000-000000000002';
    RAISE NOTICE 'PASS P1-04: legitimate profile edit still works';
END $$;

DO $$
BEGIN
    SET LOCAL ROLE service_role;
    UPDATE executors SET world_id_verified=true, world_id_level='orb'
    WHERE id='feed0000-0000-0000-0000-000000000002';
    RAISE NOTICE 'PASS P1-04: service_role (backend) can set trust flags';
END $$;

-- ===========================================================================
-- FIX-P1-08: dispute parties cannot resolve their own dispute; neutral can.
-- ===========================================================================
DO $$
DECLARE blocked boolean := false;
BEGIN
    SET LOCAL ROLE service_role;
    INSERT INTO disputes (id, task_id, agent_id, executor_id, status)
    VALUES ('feed0000-0000-0000-0000-0000000000d1', gen_random_uuid(),
            '0xfeedagent0000000000000000000000000000a1',
            'feed0000-0000-0000-0000-000000000002', 'open')
    ON CONFLICT (id) DO NOTHING;
    BEGIN
        UPDATE disputes SET status='resolved_for_executor',
            resolved_by='0xfeed000000000000000000000000000000000002'  -- the executor's own wallet
        WHERE id='feed0000-0000-0000-0000-0000000000d1';
    EXCEPTION WHEN OTHERS THEN blocked := true; END;
    IF NOT blocked THEN RAISE EXCEPTION 'FAIL P1-08: executor resolved their own dispute'; END IF;
    RAISE NOTICE 'PASS P1-08: executor cannot resolve own dispute';
END $$;

DO $$
BEGIN
    SET LOCAL ROLE service_role;
    UPDATE disputes SET status='resolved_for_executor', resolved_by='admin-neutral-actor'
    WHERE id='feed0000-0000-0000-0000-0000000000d1';
    RAISE NOTICE 'PASS P1-08: neutral resolver allowed';
END $$;

-- ===========================================================================
-- DB-004: anon/authenticated cannot forge a verification row; service_role can.
-- ===========================================================================
DO $$
DECLARE blocked boolean := false;
BEGIN
    SET LOCAL ROLE authenticated;
    BEGIN
        INSERT INTO veryai_verifications (executor_id, veryai_sub, verification_level, oidc_id_token)
        VALUES ('feed0000-0000-0000-0000-000000000002','forged','palm_dual','t');
    EXCEPTION WHEN OTHERS THEN blocked := true; END;
    IF NOT blocked THEN RAISE EXCEPTION 'FAIL DB-004: authenticated forged a veryai_verifications row'; END IF;
    RAISE NOTICE 'PASS DB-004: authenticated cannot forge veryai verification';
END $$;

-- Cleanup
SET ROLE service_role;
DELETE FROM disputes WHERE id='feed0000-0000-0000-0000-0000000000d1';
DELETE FROM veryai_verifications WHERE executor_id='feed0000-0000-0000-0000-000000000002';
DELETE FROM executors WHERE wallet_address LIKE '0xfeed%';
RESET ROLE;

SELECT 'ALL BEHAVIOURAL TESTS PASSED (P0-02, P1-04, P1-08, DB-004)' AS result;
