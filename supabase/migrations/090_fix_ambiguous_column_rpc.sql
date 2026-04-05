-- Migration 090: Fix ambiguous column reference in get_or_create_executor
--
-- PostgreSQL 42702 error: "column reference wallet_address is ambiguous"
-- RETURNS TABLE declares wallet_address, email, display_name as output variables,
-- which conflict with identically-named columns in the executors table.
-- Fix: #variable_conflict use_column tells PL/pgSQL to prefer column names
-- over variables when there's ambiguity. All function variables already use
-- v_ or p_ prefixes so this is safe.

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

    -- Check if executor exists by wallet address
    SELECT e.id INTO v_executor_id
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
