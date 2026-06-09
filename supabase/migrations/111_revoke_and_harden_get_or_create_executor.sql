-- Migration 111: Re-close DB-001 (P0) — revoke anon/authenticated EXECUTE on
-- get_or_create_executor AND harden the function body against identity rebind.
-- Source: Security Audit 2026-06-09, finding FIX-P0-02.
--
-- CONTEXT
-- -------
-- Migration 092 (GR-0.3, DB-001) revoked EXECUTE on
--   get_or_create_executor(text,text,text,text,text)
-- from PUBLIC/anon/authenticated and granted only service_role, because the
-- SECURITY DEFINER body rebinds an existing executor row to the caller's
-- auth.uid() on every call (090_fix_ambiguous_column_rpc.sql:125,
-- `user_id = COALESCE(v_user_id, executors.user_id)`), matching solely on the
-- caller-supplied p_wallet_address with no ownership proof.
--
-- Migration 097 then RE-GRANTED that exact signature to anon, authenticated,
-- reopening the CRITICAL cross-account takeover. This migration:
--   (1) re-REVOKEs from PUBLIC, anon, authenticated and re-GRANTs only
--       service_role (immediate fix; mirrors 092's _safe_revoke_and_grant), and
--   (2) hardens the function body so it NEVER overwrites a non-NULL user_id
--       belonging to a different session unless ownership of p_wallet_address is
--       proven via the verified wallet claim in the JWT (durable defense-in-depth,
--       protects the service_role backend path too).
--
-- IDEMPOTENT: REVOKE of a non-granted privilege is a no-op NOTICE; CREATE OR
-- REPLACE FUNCTION is idempotent. Safe to re-run.
-- Applied to production: pending.

BEGIN;

-- ============================================================================
-- 1. REVOKE the anon/authenticated grant that migration 097 re-added.
--    Revoke from PUBLIC too — anon/authenticated inherit PUBLIC in Supabase.
-- ============================================================================
DO $$
BEGIN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION public.get_or_create_executor(text, text, text, text, text) FROM PUBLIC, anon, authenticated';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.get_or_create_executor(text, text, text, text, text) TO service_role';
    RAISE NOTICE '111: re-locked get_or_create_executor to service_role only (re-closes DB-001)';
EXCEPTION WHEN undefined_function OR undefined_object THEN
    RAISE NOTICE '111: SKIPPED revoke/grant (function does not exist in this database)';
END;
$$;

COMMENT ON FUNCTION public.get_or_create_executor(text, text, text, text, text) IS
    'REVOKED from anon/authenticated 2026-06-09 (FIX-P0-02, re-closes DB-001 after migration 097 reopened it). service_role only. Body hardened: never rebinds a non-NULL user_id of a different session without proven wallet ownership.';

-- ============================================================================
-- 2. Harden the function body: never silently rebind a non-NULL user_id that
--    belongs to a different session. Only adopt the session when the row is
--    unowned (user_id IS NULL), already owned by this session, or wallet
--    ownership is proven via the verified JWT wallet claim.
--    (Full body re-stated from 090 with the ELSE branch hardened.)
-- ============================================================================
CREATE OR REPLACE FUNCTION get_or_create_executor(
    p_wallet_address TEXT,
    p_display_name TEXT DEFAULT NULL,
    p_email TEXT DEFAULT NULL,
    p_signature TEXT DEFAULT NULL,
    p_message TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    wallet_address TEXT,
    display_name TEXT,
    email TEXT,
    reputation_score INTEGER,
    tier executor_tier,
    tasks_completed INTEGER,
    balance_usdc DECIMAL(18, 6),
    created_at TIMESTAMPTZ,
    is_new BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
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
    -- Get current authenticated user
    v_user_id := auth.uid();

    -- Normalize: lowercase for EVM, preserve case for Solana
    IF p_wallet_address LIKE '0x%' OR p_wallet_address LIKE '0X%' THEN
        v_normalized_wallet := LOWER(p_wallet_address);
    ELSE
        v_normalized_wallet := p_wallet_address;  -- Solana: case-sensitive
    END IF;

    -- Validate wallet address format (EVM or Solana Base58)
    IF v_normalized_wallet !~ '^0x[a-f0-9]{40}$' AND v_normalized_wallet !~ '^[1-9A-HJ-NP-Za-km-z]{32,44}$' THEN
        RAISE EXCEPTION 'Invalid wallet address format: %', p_wallet_address;
    END IF;

    -- Does the JWT already prove ownership of this wallet? The legitimate
    -- first-bind path below writes this claim into auth.users metadata.
    BEGIN
        v_jwt_wallet := LOWER(auth.jwt() -> 'user_metadata' ->> 'wallet_address');
    EXCEPTION WHEN OTHERS THEN
        v_jwt_wallet := NULL;
    END;
    v_owns_wallet := (v_jwt_wallet IS NOT NULL AND v_jwt_wallet = LOWER(v_normalized_wallet));

    -- Check if executor exists by wallet address
    SELECT e.id, e.user_id INTO v_executor_id, v_existing_user_id
    FROM executors e
    WHERE e.wallet_address = v_normalized_wallet;

    IF v_executor_id IS NULL THEN
        -- Generate default display name
        IF v_normalized_wallet LIKE '0x%' THEN
            v_default_name := 'Worker_' || SUBSTRING(v_normalized_wallet FROM 3 FOR 8);
        ELSE
            v_default_name := 'Worker_' || SUBSTRING(v_normalized_wallet FROM 1 FOR 8);
        END IF;

        -- Create new executor
        INSERT INTO executors (
            wallet_address,
            user_id,
            display_name,
            email,
            reputation_score,
            tier,
            status
        )
        VALUES (
            v_normalized_wallet,
            v_user_id,
            COALESCE(p_display_name, v_default_name),
            p_email,
            50,  -- Neutral starting reputation
            'probation',
            'active'
        )
        RETURNING executors.id INTO v_executor_id;

        v_is_new := TRUE;

        -- Log initial reputation
        INSERT INTO reputation_log (executor_id, event_type, delta, old_score, new_score, reason)
        VALUES (v_executor_id, 'initial_registration', 50, 0, 50, 'Account created');

        -- Link wallet to user if authenticated
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

            -- Store wallet_address in user metadata (this is what later proves
            -- ownership for the v_owns_wallet check above on subsequent calls).
            UPDATE auth.users
            SET raw_user_meta_data = COALESCE(raw_user_meta_data, '{}'::jsonb) ||
                jsonb_build_object('wallet_address', v_normalized_wallet)
            WHERE id = v_user_id;
        END IF;

        -- Award newcomer badge (progress at 0)
        INSERT INTO badges (executor_id, badge_type, name, description, progress, max_progress)
        VALUES (v_executor_id, 'newcomer', 'Newcomer', 'Complete your first task', 0, 1);

    ELSE
        -- HARDENED (FIX-P0-02): never overwrite a non-NULL user_id belonging to
        -- a DIFFERENT session unless ownership of this wallet is proven via the
        -- verified JWT wallet claim. Adopt the session only when the row is
        -- unowned, already owned by this session, or ownership is proven.
        UPDATE executors
        SET
            last_active_at = NOW(),
            user_id = CASE
                WHEN v_existing_user_id IS NULL THEN v_user_id              -- first bind
                WHEN v_existing_user_id = v_user_id THEN v_existing_user_id -- idempotent re-login
                WHEN v_owns_wallet THEN v_user_id                          -- proven owner rebind
                ELSE v_existing_user_id                                    -- DENY silent takeover
            END,
            email = COALESCE(executors.email, p_email)
        WHERE executors.id = v_executor_id;

        -- Only persist wallet verification / JWT claim when the caller is (or
        -- has just become) the owning session AND supplied a signature. This
        -- prevents an attacker session from writing a wallet claim it does not own.
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

    -- Return executor data
    RETURN QUERY
    SELECT
        e.id,
        e.wallet_address::TEXT,
        e.display_name::TEXT,
        e.email::TEXT,
        e.reputation_score,
        e.tier,
        e.tasks_completed,
        e.balance_usdc,
        e.created_at,
        v_is_new
    FROM executors e
    WHERE e.id = v_executor_id;
END;
$$;

-- Re-assert the lockdown AFTER the CREATE OR REPLACE. A bare CREATE OR REPLACE
-- FUNCTION does not reset grants, but re-running the revoke here is harmless and
-- guarantees the final privilege state even if this file is applied out of order.
DO $$
BEGIN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION public.get_or_create_executor(text, text, text, text, text) FROM PUBLIC, anon, authenticated';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.get_or_create_executor(text, text, text, text, text) TO service_role';
EXCEPTION WHEN undefined_function OR undefined_object THEN
    RAISE NOTICE '111: post-body re-lock skipped (function missing)';
END;
$$;

COMMIT;

-- ============================================================================
-- VERIFICATION (run after COMMIT — expect f, f, t)
-- ============================================================================
-- SELECT has_function_privilege('anon',          'public.get_or_create_executor(text,text,text,text,text)', 'EXECUTE') AS anon_can_execute;          -- expect f
-- SELECT has_function_privilege('authenticated',  'public.get_or_create_executor(text,text,text,text,text)', 'EXECUTE') AS authed_can_execute;        -- expect f
-- SELECT has_function_privilege('service_role',   'public.get_or_create_executor(text,text,text,text,text)', 'EXECUTE') AS service_role_can_execute;  -- expect t

-- ============================================================================
-- ROLLBACK (manual — NOT recommended; reopens DB-001)
-- ============================================================================
-- BEGIN;
--   GRANT EXECUTE ON FUNCTION public.get_or_create_executor(text,text,text,text,text)
--       TO anon, authenticated;  -- reopens the takeover; do not do this
--   -- To revert the body hardening, re-apply migration 090's function body.
-- COMMIT;
