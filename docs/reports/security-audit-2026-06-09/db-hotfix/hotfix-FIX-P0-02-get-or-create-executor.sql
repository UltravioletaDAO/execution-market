-- ===========================================================================
-- HOTFIX FIX-P0-02 (paste into the Supabase SQL editor) — re-close DB-001 NOW.
-- Revoke the migration-097 anon/authenticated grant on get_or_create_executor
-- AND harden the function body against cross-session identity rebind.
-- Idempotent: re-running is a safe no-op. Run as the project owner (the SQL
-- editor connects as a superuser-equivalent).
-- Mirrors supabase/migrations/111_revoke_and_harden_get_or_create_executor.sql.
-- ===========================================================================

BEGIN;

-- 1) Immediate P0 closure: re-lock the function to service_role only.
DO $$
BEGIN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION public.get_or_create_executor(text, text, text, text, text) FROM PUBLIC, anon, authenticated';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.get_or_create_executor(text, text, text, text, text) TO service_role';
    RAISE NOTICE 'HOTFIX FIX-P0-02: get_or_create_executor re-locked to service_role only';
EXCEPTION WHEN undefined_function OR undefined_object THEN
    RAISE NOTICE 'HOTFIX FIX-P0-02: function not found, nothing to revoke';
END;
$$;

-- 2) Defense-in-depth: harden the body so it never silently rebinds a non-NULL
--    user_id of a different session without proven wallet ownership.
CREATE OR REPLACE FUNCTION get_or_create_executor(
    p_wallet_address TEXT,
    p_display_name TEXT DEFAULT NULL,
    p_email TEXT DEFAULT NULL,
    p_signature TEXT DEFAULT NULL,
    p_message TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID, wallet_address TEXT, display_name TEXT, email TEXT,
    reputation_score INTEGER, tier executor_tier, tasks_completed INTEGER,
    balance_usdc DECIMAL(18, 6), created_at TIMESTAMPTZ, is_new BOOLEAN
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
#variable_conflict use_column
DECLARE
    v_executor_id UUID;
    v_is_new BOOLEAN := FALSE;
    v_user_id UUID;
    v_existing_user_id UUID;
    v_owns_wallet BOOLEAN := FALSE;
    v_jwt_wallet TEXT;
    v_normalized_wallet TEXT;
    v_default_name TEXT;
BEGIN
    v_user_id := auth.uid();

    IF p_wallet_address LIKE '0x%' OR p_wallet_address LIKE '0X%' THEN
        v_normalized_wallet := LOWER(p_wallet_address);
    ELSE
        v_normalized_wallet := p_wallet_address;
    END IF;

    IF v_normalized_wallet !~ '^0x[a-f0-9]{40}$' AND v_normalized_wallet !~ '^[1-9A-HJ-NP-Za-km-z]{32,44}$' THEN
        RAISE EXCEPTION 'Invalid wallet address format: %', p_wallet_address;
    END IF;

    BEGIN
        v_jwt_wallet := LOWER(auth.jwt() -> 'user_metadata' ->> 'wallet_address');
    EXCEPTION WHEN OTHERS THEN
        v_jwt_wallet := NULL;
    END;
    v_owns_wallet := (v_jwt_wallet IS NOT NULL AND v_jwt_wallet = LOWER(v_normalized_wallet));

    SELECT e.id, e.user_id INTO v_executor_id, v_existing_user_id
    FROM executors e WHERE e.wallet_address = v_normalized_wallet;

    IF v_executor_id IS NULL THEN
        IF v_normalized_wallet LIKE '0x%' THEN
            v_default_name := 'Worker_' || SUBSTRING(v_normalized_wallet FROM 3 FOR 8);
        ELSE
            v_default_name := 'Worker_' || SUBSTRING(v_normalized_wallet FROM 1 FOR 8);
        END IF;

        INSERT INTO executors (wallet_address, user_id, display_name, email, reputation_score, tier, status)
        VALUES (v_normalized_wallet, v_user_id, COALESCE(p_display_name, v_default_name), p_email, 50, 'probation', 'active')
        RETURNING executors.id INTO v_executor_id;

        v_is_new := TRUE;

        INSERT INTO reputation_log (executor_id, event_type, delta, old_score, new_score, reason)
        VALUES (v_executor_id, 'initial_registration', 50, 0, 50, 'Account created');

        IF v_user_id IS NOT NULL THEN
            IF p_signature IS NOT NULL THEN
                INSERT INTO user_wallets (user_id, wallet_address, is_primary, chain_id, signature_hash, verified_at)
                VALUES (v_user_id, v_normalized_wallet, TRUE, 8453, p_signature, NOW())
                ON CONFLICT (user_id, wallet_address)
                DO UPDATE SET signature_hash = EXCLUDED.signature_hash, verified_at = NOW(), is_primary = TRUE, updated_at = NOW();
            ELSE
                INSERT INTO user_wallets (user_id, wallet_address, is_primary)
                VALUES (v_user_id, v_normalized_wallet, TRUE)
                ON CONFLICT (user_id, wallet_address) DO NOTHING;
            END IF;

            UPDATE auth.users
            SET raw_user_meta_data = COALESCE(raw_user_meta_data, '{}'::jsonb) ||
                jsonb_build_object('wallet_address', v_normalized_wallet)
            WHERE id = v_user_id;
        END IF;

        INSERT INTO badges (executor_id, badge_type, name, description, progress, max_progress)
        VALUES (v_executor_id, 'newcomer', 'Newcomer', 'Complete your first task', 0, 1);

    ELSE
        UPDATE executors
        SET last_active_at = NOW(),
            user_id = CASE
                WHEN v_existing_user_id IS NULL THEN v_user_id
                WHEN v_existing_user_id = v_user_id THEN v_existing_user_id
                WHEN v_owns_wallet THEN v_user_id
                ELSE v_existing_user_id
            END,
            email = COALESCE(executors.email, p_email)
        WHERE executors.id = v_executor_id;

        IF v_user_id IS NOT NULL
           AND p_signature IS NOT NULL
           AND (v_existing_user_id IS NULL OR v_existing_user_id = v_user_id OR v_owns_wallet) THEN
            INSERT INTO user_wallets (user_id, wallet_address, is_primary, chain_id, signature_hash, verified_at)
            VALUES (v_user_id, v_normalized_wallet, TRUE, 8453, p_signature, NOW())
            ON CONFLICT (user_id, wallet_address)
            DO UPDATE SET signature_hash = EXCLUDED.signature_hash, verified_at = NOW(), is_primary = TRUE, updated_at = NOW();

            UPDATE auth.users
            SET raw_user_meta_data = COALESCE(raw_user_meta_data, '{}'::jsonb) ||
                jsonb_build_object('wallet_address', v_normalized_wallet)
            WHERE id = v_user_id;
        END IF;
    END IF;

    RETURN QUERY
    SELECT e.id, e.wallet_address::TEXT, e.display_name::TEXT, e.email::TEXT,
           e.reputation_score, e.tier, e.tasks_completed, e.balance_usdc, e.created_at, v_is_new
    FROM executors e WHERE e.id = v_executor_id;
END;
$$;

-- Re-assert grants after CREATE OR REPLACE (harmless if already correct).
DO $$
BEGIN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION public.get_or_create_executor(text, text, text, text, text) FROM PUBLIC, anon, authenticated';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.get_or_create_executor(text, text, text, text, text) TO service_role';
EXCEPTION WHEN undefined_function OR undefined_object THEN
    RAISE NOTICE 'HOTFIX FIX-P0-02: post-body re-lock skipped (function missing)';
END;
$$;

COMMIT;

-- Verify (expect f, f, t):
SELECT
    has_function_privilege('anon',         'public.get_or_create_executor(text,text,text,text,text)', 'EXECUTE') AS anon_can_execute,
    has_function_privilege('authenticated','public.get_or_create_executor(text,text,text,text,text)', 'EXECUTE') AS authed_can_execute,
    has_function_privilege('service_role', 'public.get_or_create_executor(text,text,text,text,text)', 'EXECUTE') AS service_role_can_execute;
