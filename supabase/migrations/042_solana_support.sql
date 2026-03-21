-- Migration: Solana Support
-- Date: 2026-03-03
-- Description: Relax EVM-only wallet constraints to support Solana Base58 addresses.
-- Solana addresses are Base58-encoded, 32-44 characters, case-sensitive.
-- EVM addresses remain 0x-prefixed, 42 chars, case-insensitive.
--
-- Tables affected:
--   executors.wallet_address         VARCHAR(42) -> VARCHAR(50)
--   user_wallets.wallet_address      VARCHAR(42) -> VARCHAR(50)
--   withdrawals.destination_address  VARCHAR(42) -> VARCHAR(50)
--   arbitrators.wallet_address       VARCHAR(42) -> VARCHAR(50)
--   payments.from_address            VARCHAR(42) -> VARCHAR(50)
--   payments.to_address              VARCHAR(42) -> VARCHAR(50)
--   escrows.beneficiary_address      VARCHAR(42) -> VARCHAR(50)
--
-- Functions affected:
--   get_or_create_executor   — dual regex + conditional normalization
--   link_wallet_to_session   — dual regex + conditional normalization
--
-- Note: escrows.chain_id remains INTEGER. Solana uses Fase 1 (no on-chain escrow),
-- so this table is not used for Solana tasks. When Solana escrow is added,
-- migrate chain_id to nullable or add network_name column.
--
-- Note: escrows.escrow_address, escrows.token_address, payments.token_address,
-- and executors.reputation_contract remain VARCHAR(42) as they reference EVM
-- contract addresses only.

-- ============================================================================
-- 1. EXTEND COLUMN TYPES — VARCHAR(42) -> VARCHAR(50)
-- ============================================================================

-- executors
ALTER TABLE executors ALTER COLUMN wallet_address TYPE VARCHAR(50);

-- user_wallets
ALTER TABLE user_wallets ALTER COLUMN wallet_address TYPE VARCHAR(50);

-- withdrawals
ALTER TABLE withdrawals ALTER COLUMN destination_address TYPE VARCHAR(50);

-- arbitrators
ALTER TABLE arbitrators ALTER COLUMN wallet_address TYPE VARCHAR(50);

-- payments (from/to can be Solana wallets)
ALTER TABLE payments ALTER COLUMN from_address TYPE VARCHAR(50);
ALTER TABLE payments ALTER COLUMN to_address TYPE VARCHAR(50);

-- escrows (beneficiary can be a Solana wallet)
ALTER TABLE escrows ALTER COLUMN beneficiary_address TYPE VARCHAR(50);


-- ============================================================================
-- 2. UPDATE FORMAT CONSTRAINTS — accept both EVM and Solana
-- ============================================================================

-- executors: drop old EVM-only constraint, add dual-format
ALTER TABLE executors DROP CONSTRAINT IF EXISTS executors_wallet_format;
ALTER TABLE executors ADD CONSTRAINT executors_wallet_format CHECK (
    wallet_address ~* '^0x[a-f0-9]{40}$'              -- EVM (case-insensitive)
    OR wallet_address ~ '^[1-9A-HJ-NP-Za-km-z]{32,44}$'  -- Solana Base58 (case-sensitive)
);

-- user_wallets: drop old EVM-only constraint, add dual-format
ALTER TABLE user_wallets DROP CONSTRAINT IF EXISTS user_wallets_format;
ALTER TABLE user_wallets ADD CONSTRAINT user_wallets_format CHECK (
    wallet_address ~* '^0x[a-f0-9]{40}$'
    OR wallet_address ~ '^[1-9A-HJ-NP-Za-km-z]{32,44}$'
);

-- withdrawals: drop old EVM-only constraint, add dual-format
ALTER TABLE withdrawals DROP CONSTRAINT IF EXISTS withdrawals_address_format;
ALTER TABLE withdrawals ADD CONSTRAINT withdrawals_address_format CHECK (
    destination_address ~* '^0x[a-f0-9]{40}$'
    OR destination_address ~ '^[1-9A-HJ-NP-Za-km-z]{32,44}$'
);


-- ============================================================================
-- 3. UPDATE INDEXES — support both EVM (lowercase) and Solana (case-sensitive)
-- ============================================================================

-- Drop old LOWER-only indexes and recreate with expressions that preserve
-- Solana case sensitivity. For EVM addresses LOWER() is still applied via
-- the RPC functions; the index now covers the raw value so both patterns match.

-- executors: the existing idx_executors_wallet uses LOWER(), which would
-- corrupt Solana Base58. Replace with a plain btree on the raw column.
-- EVM lookups in RPC functions use LOWER() on both sides, so they still match.
DROP INDEX IF EXISTS idx_executors_wallet;
CREATE INDEX idx_executors_wallet ON executors(wallet_address);

-- user_wallets: same treatment
DROP INDEX IF EXISTS idx_user_wallets_address;
CREATE INDEX idx_user_wallets_address ON user_wallets(wallet_address);


-- ============================================================================
-- 4. UPDATE RPC FUNCTIONS — dual regex + conditional normalization
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 4a. get_or_create_executor
--     Latest version from 009_require_wallet_signature.sql, updated for Solana.
--     Changes:
--       - Normalize: LOWER for EVM, preserve case for Solana
--       - Regex: accept both EVM and Solana formats
--       - Display name fallback: first 8 chars of address (skip '0x' for EVM)
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
    -- For EVM: compare lowercased. For Solana: exact match (already normalized).
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


-- ---------------------------------------------------------------------------
-- 4b. link_wallet_to_session
--     Latest version from 009_require_wallet_signature.sql, updated for Solana.
--     Changes:
--       - Normalize: LOWER for EVM, preserve case for Solana
--       - Regex: accept both EVM and Solana formats
--       - Executor lookup: exact match (both sides already normalized)
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

    -- Normalize: lowercase for EVM, preserve case for Solana
    IF p_wallet_address LIKE '0x%' OR p_wallet_address LIKE '0X%' THEN
        v_normalized_wallet := LOWER(p_wallet_address);
    ELSE
        v_normalized_wallet := p_wallet_address;  -- Solana: case-sensitive
    END IF;

    -- Validate wallet address format (EVM or Solana Base58)
    IF v_normalized_wallet !~ '^0x[a-f0-9]{40}$' AND v_normalized_wallet !~ '^[1-9A-HJ-NP-Za-km-z]{32,44}$' THEN
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

    -- Link executor to current session
    UPDATE executors
    SET user_id = p_user_id, last_active_at = NOW()
    WHERE wallet_address = v_normalized_wallet;

    RETURN TRUE;
END;
$$;
