-- ============================================================================
-- EXECUTION MARKET: Require wallet ownership proof via signature
-- Migration: 009_require_wallet_signature.sql
--
-- Purpose: Update get_or_create_executor and link_wallet_to_session to accept
-- an optional wallet signature (p_signature, p_message). When provided, the
-- signature hash and verification timestamp are persisted in user_wallets.
--
-- Backwards compatible: new params default to NULL so existing callers
-- continue to work. The frontend will always provide the signature going
-- forward.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Update get_or_create_executor - add signature/message params
-- ---------------------------------------------------------------------------
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
DECLARE
    v_executor_id UUID;
    v_is_new BOOLEAN := FALSE;
    v_user_id UUID;
    v_normalized_wallet TEXT;
BEGIN
    -- Get current authenticated user
    v_user_id := auth.uid();

    -- Normalize wallet address to lowercase
    v_normalized_wallet := LOWER(p_wallet_address);

    -- Validate wallet address format
    IF v_normalized_wallet !~ '^0x[a-f0-9]{40}$' THEN
        RAISE EXCEPTION 'Invalid wallet address format: %', p_wallet_address;
    END IF;

    -- Check if executor exists by wallet address
    SELECT e.id INTO v_executor_id
    FROM executors e
    WHERE LOWER(e.wallet_address) = v_normalized_wallet;

    IF v_executor_id IS NULL THEN
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
            COALESCE(p_display_name, 'Worker_' || SUBSTRING(v_normalized_wallet FROM 3 FOR 8)),
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
                -- Store wallet with signature verification
                INSERT INTO user_wallets (user_id, wallet_address, is_primary, chain_id, signature_hash, verified_at)
                VALUES (v_user_id, v_normalized_wallet, TRUE, 8453, p_signature, NOW())
                ON CONFLICT (user_id, wallet_address)
                DO UPDATE SET signature_hash = EXCLUDED.signature_hash, verified_at = NOW(), is_primary = TRUE, updated_at = NOW();
            ELSE
                INSERT INTO user_wallets (user_id, wallet_address, is_primary)
                VALUES (v_user_id, v_normalized_wallet, TRUE)
                ON CONFLICT (user_id, wallet_address) DO NOTHING;
            END IF;

            -- Store wallet_address in user metadata
            UPDATE auth.users
            SET raw_user_meta_data = COALESCE(raw_user_meta_data, '{}'::jsonb) ||
                jsonb_build_object('wallet_address', v_normalized_wallet)
            WHERE id = v_user_id;
        END IF;

        -- Award newcomer badge (progress at 0)
        INSERT INTO badges (executor_id, badge_type, name, description, progress, max_progress)
        VALUES (v_executor_id, 'newcomer', 'Newcomer', 'Complete your first task', 0, 1);

    ELSE
        -- Update existing executor: always bind to current session user_id
        -- so returning users with a new anonymous session get linked correctly
        UPDATE executors
        SET
            last_active_at = NOW(),
            user_id = COALESCE(v_user_id, executors.user_id),
            email = COALESCE(executors.email, p_email)
        WHERE executors.id = v_executor_id;

        -- If signature provided, store/update verification for existing executor
        IF v_user_id IS NOT NULL AND p_signature IS NOT NULL THEN
            INSERT INTO user_wallets (user_id, wallet_address, is_primary, chain_id, signature_hash, verified_at)
            VALUES (v_user_id, v_normalized_wallet, TRUE, 8453, p_signature, NOW())
            ON CONFLICT (user_id, wallet_address)
            DO UPDATE SET signature_hash = EXCLUDED.signature_hash, verified_at = NOW(), is_primary = TRUE, updated_at = NOW();

            -- Store wallet_address in user metadata
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

-- ---------------------------------------------------------------------------
-- 2. Update link_wallet_to_session - add signature/message params
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION link_wallet_to_session(
    p_user_id UUID,
    p_wallet_address TEXT,
    p_chain_id INTEGER DEFAULT 8453,
    p_signature TEXT DEFAULT NULL,
    p_message TEXT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_normalized_wallet TEXT;
BEGIN
    IF p_user_id IS NULL THEN
        RAISE EXCEPTION 'User ID is required';
    END IF;

    v_normalized_wallet := LOWER(p_wallet_address);

    IF v_normalized_wallet !~ '^0x[a-f0-9]{40}$' THEN
        RAISE EXCEPTION 'Invalid wallet address format';
    END IF;

    -- Update user metadata
    UPDATE auth.users
    SET raw_user_meta_data = COALESCE(raw_user_meta_data, '{}'::jsonb) ||
        jsonb_build_object('wallet_address', v_normalized_wallet)
    WHERE id = p_user_id;

    -- Create or update wallet link (include signature if provided)
    IF p_signature IS NOT NULL THEN
        INSERT INTO user_wallets (user_id, wallet_address, is_primary, chain_id, signature_hash, verified_at)
        VALUES (p_user_id, v_normalized_wallet, TRUE, p_chain_id, p_signature, NOW())
        ON CONFLICT (user_id, wallet_address)
        DO UPDATE SET is_primary = TRUE, signature_hash = EXCLUDED.signature_hash, verified_at = NOW(), updated_at = NOW();
    ELSE
        INSERT INTO user_wallets (user_id, wallet_address, is_primary, chain_id)
        VALUES (p_user_id, v_normalized_wallet, TRUE, p_chain_id)
        ON CONFLICT (user_id, wallet_address)
        DO UPDATE SET is_primary = TRUE, updated_at = NOW();
    END IF;

    -- Set other wallets as non-primary
    UPDATE user_wallets
    SET is_primary = FALSE, updated_at = NOW()
    WHERE user_id = p_user_id AND wallet_address != v_normalized_wallet;

    -- Link executor to current session (always update user_id so
    -- returning users with a new anonymous session get linked correctly)
    UPDATE executors
    SET user_id = p_user_id, last_active_at = NOW()
    WHERE LOWER(wallet_address) = v_normalized_wallet;

    RETURN TRUE;
END;
$$;

-- ---------------------------------------------------------------------------
-- 3. Index for wallet_address lookups on user_wallets
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_user_wallets_wallet ON user_wallets(wallet_address);
