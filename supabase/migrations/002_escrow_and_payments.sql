-- ============================================================================
-- CHAMBA: Human Execution Layer for AI Agents
-- Migration: 002_escrow_and_payments.sql
-- Description: Escrow tracking, payment history, and x402 integration
-- Version: 2.0.0
-- Date: 2026-01-25
-- ============================================================================

-- ============================================================================
-- ENUMS
-- ============================================================================

-- Payment status
CREATE TYPE payment_status AS ENUM (
    'pending',          -- Created but not yet processed
    'processing',       -- Being processed by x402
    'completed',        -- Successfully completed
    'failed',           -- Failed to process
    'refunded',         -- Refunded to sender
    'cancelled'         -- Cancelled before processing
);

-- Payment type
CREATE TYPE payment_type AS ENUM (
    'escrow_create',      -- Initial escrow creation (lock funds)
    'partial_release',    -- 30% release on submission
    'final_release',      -- Remaining 70% on approval
    'full_release',       -- 100% release (no partial)
    'refund',             -- Full refund to agent
    'partial_refund',     -- Partial refund (after partial release)
    'platform_fee',       -- 8% platform fee
    'withdrawal',         -- Executor withdrawal to external wallet
    'deposit'             -- Deposit to platform balance
);

-- Escrow status
CREATE TYPE escrow_status AS ENUM (
    'pending',            -- Created, waiting for funding
    'funded',             -- Funds locked in escrow
    'partial_released',   -- Part released (after submission)
    'released',           -- Fully released to executor
    'refunded',           -- Refunded to agent
    'disputed',           -- Frozen due to dispute
    'expired'             -- Expired without completion
);

-- ============================================================================
-- TABLES
-- ============================================================================

-- ---------------------------------------------------------------------------
-- ESCROWS (x402 escrow tracking)
-- ---------------------------------------------------------------------------
CREATE TABLE escrows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- References
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    agent_id VARCHAR(255) NOT NULL,

    -- x402 identifiers
    escrow_id VARCHAR(255) NOT NULL,      -- x402 escrow identifier (unique)
    escrow_address VARCHAR(42),            -- On-chain escrow contract address
    funding_tx VARCHAR(66),                -- Transaction that funded escrow

    -- Status
    status escrow_status DEFAULT 'pending',

    -- Amounts (stored as DECIMAL for precision)
    total_amount_usdc DECIMAL(18, 6) NOT NULL,
    platform_fee_usdc DECIMAL(18, 6) NOT NULL,  -- 8% platform fee
    net_bounty_usdc DECIMAL(18, 6) GENERATED ALWAYS AS (total_amount_usdc - platform_fee_usdc) STORED,

    -- Release tracking
    released_amount_usdc DECIMAL(18, 6) DEFAULT 0,
    remaining_usdc DECIMAL(18, 6) GENERATED ALWAYS AS (total_amount_usdc - released_amount_usdc) STORED,

    -- Beneficiary (executor who will receive payment)
    beneficiary_id UUID REFERENCES executors(id) ON DELETE SET NULL,
    beneficiary_address VARCHAR(42),

    -- Chain info
    chain_id INTEGER DEFAULT 8453,         -- Base Mainnet
    token_address VARCHAR(42) DEFAULT '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',  -- USDC on Base

    -- Timing
    timeout_hours INTEGER DEFAULT 48,      -- Auto-refund timeout
    expires_at TIMESTAMPTZ,                -- When escrow expires

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    funded_at TIMESTAMPTZ,
    partial_released_at TIMESTAMPTZ,
    released_at TIMESTAMPTZ,
    refunded_at TIMESTAMPTZ,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Constraints
    CONSTRAINT escrows_x402_unique UNIQUE (escrow_id),
    CONSTRAINT escrows_positive_amount CHECK (total_amount_usdc > 0),
    CONSTRAINT escrows_valid_fee CHECK (platform_fee_usdc >= 0 AND platform_fee_usdc < total_amount_usdc)
);

-- Indexes for escrows
CREATE INDEX idx_escrows_task ON escrows(task_id);
CREATE INDEX idx_escrows_agent ON escrows(agent_id);
CREATE INDEX idx_escrows_status ON escrows(status);
CREATE INDEX idx_escrows_beneficiary ON escrows(beneficiary_id);
CREATE INDEX idx_escrows_expires ON escrows(expires_at) WHERE status IN ('pending', 'funded');
CREATE INDEX idx_escrows_x402_id ON escrows(escrow_id);
CREATE INDEX idx_escrows_created ON escrows(created_at DESC);

-- ---------------------------------------------------------------------------
-- PAYMENTS (All payment transactions)
-- ---------------------------------------------------------------------------
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- References
    escrow_id UUID REFERENCES escrows(id) ON DELETE SET NULL,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    executor_id UUID REFERENCES executors(id) ON DELETE SET NULL,
    submission_id UUID REFERENCES submissions(id) ON DELETE SET NULL,

    -- Payment details
    payment_type payment_type NOT NULL,
    status payment_status DEFAULT 'pending',

    -- Amounts
    amount_usdc DECIMAL(18, 6) NOT NULL,
    fee_usdc DECIMAL(18, 6) DEFAULT 0,
    net_amount_usdc DECIMAL(18, 6) GENERATED ALWAYS AS (amount_usdc - fee_usdc) STORED,

    -- x402 protocol details
    x402_escrow_id VARCHAR(255),           -- x402 escrow identifier
    transaction_hash VARCHAR(66),          -- On-chain transaction hash
    from_address VARCHAR(42),              -- Sender wallet address
    to_address VARCHAR(42),                -- Recipient wallet address

    -- Chain info
    chain_id INTEGER DEFAULT 8453,
    token_address VARCHAR(42) DEFAULT '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    block_number BIGINT,
    gas_used BIGINT,
    gas_price_gwei DECIMAL(18, 9),

    -- Metadata
    memo TEXT,
    error_message TEXT,
    error_code VARCHAR(50),
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processing_started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,

    -- Retry tracking
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMPTZ,
    next_retry_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT payments_positive_amount CHECK (amount_usdc > 0),
    CONSTRAINT payments_valid_fee CHECK (fee_usdc >= 0 AND fee_usdc <= amount_usdc)
);

-- Indexes for payments
CREATE INDEX idx_payments_escrow ON payments(escrow_id);
CREATE INDEX idx_payments_task ON payments(task_id);
CREATE INDEX idx_payments_executor ON payments(executor_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_type ON payments(payment_type);
CREATE INDEX idx_payments_tx_hash ON payments(transaction_hash) WHERE transaction_hash IS NOT NULL;
CREATE INDEX idx_payments_created ON payments(created_at DESC);
CREATE INDEX idx_payments_pending ON payments(status, created_at)
    WHERE status = 'pending';
CREATE INDEX idx_payments_executor_completed ON payments(executor_id, completed_at DESC)
    WHERE status = 'completed';

-- ---------------------------------------------------------------------------
-- WITHDRAWALS (Executor withdrawal requests)
-- ---------------------------------------------------------------------------
CREATE TABLE withdrawals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Who is withdrawing
    executor_id UUID NOT NULL REFERENCES executors(id) ON DELETE CASCADE,

    -- Amount
    amount_usdc DECIMAL(18, 6) NOT NULL,
    fee_usdc DECIMAL(18, 6) DEFAULT 0,  -- Gas fee or withdrawal fee
    net_amount_usdc DECIMAL(18, 6) GENERATED ALWAYS AS (amount_usdc - fee_usdc) STORED,

    -- Destination
    destination_address VARCHAR(42) NOT NULL,
    destination_chain_id INTEGER DEFAULT 8453,

    -- Status
    status payment_status DEFAULT 'pending',

    -- Transaction details
    transaction_hash VARCHAR(66),
    block_number BIGINT,

    -- Error tracking
    error_message TEXT,
    error_code VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processing_started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT withdrawals_positive_amount CHECK (amount_usdc > 0),
    CONSTRAINT withdrawals_address_format CHECK (destination_address ~* '^0x[a-f0-9]{40}$')
);

-- Indexes for withdrawals
CREATE INDEX idx_withdrawals_executor ON withdrawals(executor_id);
CREATE INDEX idx_withdrawals_status ON withdrawals(status);
CREATE INDEX idx_withdrawals_created ON withdrawals(created_at DESC);
CREATE INDEX idx_withdrawals_pending ON withdrawals(executor_id, status)
    WHERE status = 'pending';

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Update escrow when payment completes
CREATE OR REPLACE FUNCTION update_escrow_on_payment()
RETURNS TRIGGER AS $$
BEGIN
    -- Only process completed payments with escrow reference
    IF NEW.status = 'completed' AND NEW.escrow_id IS NOT NULL THEN
        CASE NEW.payment_type
            WHEN 'partial_release' THEN
                UPDATE escrows
                SET
                    released_amount_usdc = released_amount_usdc + NEW.amount_usdc,
                    status = 'partial_released',
                    partial_released_at = NOW()
                WHERE id = NEW.escrow_id;

            WHEN 'final_release', 'full_release' THEN
                UPDATE escrows
                SET
                    released_amount_usdc = released_amount_usdc + NEW.amount_usdc,
                    status = 'released',
                    released_at = NOW()
                WHERE id = NEW.escrow_id;

            WHEN 'refund', 'partial_refund' THEN
                UPDATE escrows
                SET
                    status = 'refunded',
                    refunded_at = NOW()
                WHERE id = NEW.escrow_id;
        END CASE;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER payments_update_escrow
    AFTER UPDATE OF status ON payments
    FOR EACH ROW
    WHEN (NEW.status = 'completed')
    EXECUTE FUNCTION update_escrow_on_payment();

-- Update executor balance on payment completion
CREATE OR REPLACE FUNCTION update_executor_balance_on_payment()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND NEW.executor_id IS NOT NULL THEN
        CASE NEW.payment_type
            WHEN 'partial_release', 'final_release', 'full_release' THEN
                -- Add to balance and total earned
                UPDATE executors
                SET
                    balance_usdc = balance_usdc + NEW.net_amount_usdc,
                    total_earned_usdc = total_earned_usdc + NEW.net_amount_usdc
                WHERE id = NEW.executor_id;

            WHEN 'withdrawal' THEN
                -- Subtract from balance, add to withdrawn
                UPDATE executors
                SET
                    balance_usdc = balance_usdc - NEW.amount_usdc,
                    total_withdrawn_usdc = total_withdrawn_usdc + NEW.amount_usdc
                WHERE id = NEW.executor_id;
        END CASE;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER payments_update_executor_balance
    AFTER UPDATE OF status ON payments
    FOR EACH ROW
    WHEN (NEW.status = 'completed')
    EXECUTE FUNCTION update_executor_balance_on_payment();

-- Set escrow expires_at on creation
CREATE OR REPLACE FUNCTION set_escrow_expiry()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.expires_at IS NULL THEN
        NEW.expires_at = NOW() + (NEW.timeout_hours * INTERVAL '1 hour');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER escrows_set_expiry
    BEFORE INSERT ON escrows
    FOR EACH ROW EXECUTE FUNCTION set_escrow_expiry();

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Create escrow for a task
CREATE OR REPLACE FUNCTION create_task_escrow(
    p_task_id UUID,
    p_x402_escrow_id VARCHAR(255),
    p_amount_usdc DECIMAL(18, 6),
    p_platform_fee_percent DECIMAL(4, 2) DEFAULT 8.00
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_task tasks%ROWTYPE;
    v_escrow_id UUID;
    v_platform_fee DECIMAL(18, 6);
BEGIN
    -- Get task
    SELECT * INTO v_task FROM tasks WHERE id = p_task_id;
    IF v_task.id IS NULL THEN
        RAISE EXCEPTION 'Task not found: %', p_task_id;
    END IF;

    -- Calculate platform fee
    v_platform_fee := p_amount_usdc * (p_platform_fee_percent / 100);

    -- Create escrow record
    INSERT INTO escrows (
        task_id,
        agent_id,
        escrow_id,
        total_amount_usdc,
        platform_fee_usdc,
        chain_id,
        token_address
    ) VALUES (
        p_task_id,
        v_task.agent_id,
        p_x402_escrow_id,
        p_amount_usdc,
        v_platform_fee,
        COALESCE(v_task.chain_id, 8453),
        COALESCE(v_task.payment_token, '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
    )
    RETURNING id INTO v_escrow_id;

    -- Update task with escrow info
    UPDATE tasks
    SET
        escrow_id = p_x402_escrow_id,
        escrow_amount_usdc = p_amount_usdc,
        escrow_created_at = NOW(),
        status = CASE WHEN status = 'draft' THEN 'published' ELSE status END
    WHERE id = p_task_id;

    RETURN v_escrow_id;
END;
$$;

-- Fund escrow (mark as funded after on-chain confirmation)
CREATE OR REPLACE FUNCTION fund_escrow(
    p_escrow_id UUID,
    p_funding_tx VARCHAR(66)
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    UPDATE escrows
    SET
        status = 'funded',
        funding_tx = p_funding_tx,
        funded_at = NOW()
    WHERE id = p_escrow_id AND status = 'pending';

    RETURN FOUND;
END;
$$;

-- Release partial payment (30% on submission)
CREATE OR REPLACE FUNCTION release_partial_payment(
    p_escrow_id UUID,
    p_executor_id UUID,
    p_tx_hash VARCHAR(66) DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_escrow escrows%ROWTYPE;
    v_payment_id UUID;
    v_amount DECIMAL(18, 6);
BEGIN
    SELECT * INTO v_escrow FROM escrows WHERE id = p_escrow_id FOR UPDATE;

    IF v_escrow.id IS NULL THEN
        RAISE EXCEPTION 'Escrow not found: %', p_escrow_id;
    END IF;

    IF v_escrow.status != 'funded' THEN
        RAISE EXCEPTION 'Escrow not in funded state: %', v_escrow.status;
    END IF;

    -- 30% of net bounty (after platform fee)
    v_amount := v_escrow.net_bounty_usdc * 0.30;

    -- Create payment record
    INSERT INTO payments (
        escrow_id,
        task_id,
        executor_id,
        payment_type,
        status,
        amount_usdc,
        x402_escrow_id,
        transaction_hash,
        chain_id,
        token_address
    ) VALUES (
        p_escrow_id,
        v_escrow.task_id,
        p_executor_id,
        'partial_release',
        CASE WHEN p_tx_hash IS NOT NULL THEN 'completed' ELSE 'pending' END,
        v_amount,
        v_escrow.escrow_id,
        p_tx_hash,
        v_escrow.chain_id,
        v_escrow.token_address
    )
    RETURNING id INTO v_payment_id;

    -- Update escrow
    UPDATE escrows
    SET
        beneficiary_id = p_executor_id,
        beneficiary_address = (SELECT wallet_address FROM executors WHERE id = p_executor_id)
    WHERE id = p_escrow_id;

    -- If tx_hash provided, mark as completed
    IF p_tx_hash IS NOT NULL THEN
        UPDATE payments SET completed_at = NOW() WHERE id = v_payment_id;
    END IF;

    RETURN v_payment_id;
END;
$$;

-- Release final payment (remaining 70% on approval)
CREATE OR REPLACE FUNCTION release_final_payment(
    p_escrow_id UUID,
    p_tx_hash VARCHAR(66) DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_escrow escrows%ROWTYPE;
    v_payment_id UUID;
    v_amount DECIMAL(18, 6);
BEGIN
    SELECT * INTO v_escrow FROM escrows WHERE id = p_escrow_id FOR UPDATE;

    IF v_escrow.id IS NULL THEN
        RAISE EXCEPTION 'Escrow not found: %', p_escrow_id;
    END IF;

    IF v_escrow.status NOT IN ('funded', 'partial_released') THEN
        RAISE EXCEPTION 'Escrow not in releasable state: %', v_escrow.status;
    END IF;

    -- Remaining amount
    v_amount := v_escrow.net_bounty_usdc - v_escrow.released_amount_usdc;

    IF v_amount <= 0 THEN
        RAISE EXCEPTION 'No remaining amount to release';
    END IF;

    -- Create payment record
    INSERT INTO payments (
        escrow_id,
        task_id,
        executor_id,
        payment_type,
        status,
        amount_usdc,
        x402_escrow_id,
        transaction_hash,
        chain_id,
        token_address
    ) VALUES (
        p_escrow_id,
        v_escrow.task_id,
        v_escrow.beneficiary_id,
        'final_release',
        CASE WHEN p_tx_hash IS NOT NULL THEN 'completed' ELSE 'pending' END,
        v_amount,
        v_escrow.escrow_id,
        p_tx_hash,
        v_escrow.chain_id,
        v_escrow.token_address
    )
    RETURNING id INTO v_payment_id;

    -- Also create platform fee payment
    INSERT INTO payments (
        escrow_id,
        task_id,
        payment_type,
        status,
        amount_usdc,
        x402_escrow_id,
        memo
    ) VALUES (
        p_escrow_id,
        v_escrow.task_id,
        'platform_fee',
        'completed',
        v_escrow.platform_fee_usdc,
        v_escrow.escrow_id,
        'Platform fee (8%)'
    );

    IF p_tx_hash IS NOT NULL THEN
        UPDATE payments SET completed_at = NOW() WHERE id = v_payment_id;
    END IF;

    RETURN v_payment_id;
END;
$$;

-- Refund escrow to agent
CREATE OR REPLACE FUNCTION refund_escrow(
    p_escrow_id UUID,
    p_reason TEXT DEFAULT NULL,
    p_tx_hash VARCHAR(66) DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_escrow escrows%ROWTYPE;
    v_payment_id UUID;
    v_refund_amount DECIMAL(18, 6);
BEGIN
    SELECT * INTO v_escrow FROM escrows WHERE id = p_escrow_id FOR UPDATE;

    IF v_escrow.id IS NULL THEN
        RAISE EXCEPTION 'Escrow not found: %', p_escrow_id;
    END IF;

    IF v_escrow.status IN ('released', 'refunded') THEN
        RAISE EXCEPTION 'Escrow already finalized: %', v_escrow.status;
    END IF;

    -- Calculate refund (total minus already released)
    v_refund_amount := v_escrow.total_amount_usdc - v_escrow.released_amount_usdc;

    IF v_refund_amount <= 0 THEN
        RAISE EXCEPTION 'No amount to refund';
    END IF;

    -- Create refund payment
    INSERT INTO payments (
        escrow_id,
        task_id,
        payment_type,
        status,
        amount_usdc,
        x402_escrow_id,
        transaction_hash,
        memo
    ) VALUES (
        p_escrow_id,
        v_escrow.task_id,
        CASE WHEN v_escrow.released_amount_usdc > 0 THEN 'partial_refund' ELSE 'refund' END,
        CASE WHEN p_tx_hash IS NOT NULL THEN 'completed' ELSE 'pending' END,
        v_refund_amount,
        v_escrow.escrow_id,
        p_tx_hash,
        COALESCE(p_reason, 'Escrow refund')
    )
    RETURNING id INTO v_payment_id;

    IF p_tx_hash IS NOT NULL THEN
        UPDATE payments SET completed_at = NOW() WHERE id = v_payment_id;
    END IF;

    RETURN v_payment_id;
END;
$$;

-- Get executor payment history
CREATE OR REPLACE FUNCTION get_executor_payments(
    p_executor_id UUID,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    payment_id UUID,
    payment_type payment_type,
    amount_usdc DECIMAL(18, 6),
    net_amount_usdc DECIMAL(18, 6),
    status payment_status,
    task_id UUID,
    task_title TEXT,
    transaction_hash VARCHAR(66),
    created_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.payment_type,
        p.amount_usdc,
        p.net_amount_usdc,
        p.status,
        p.task_id,
        t.title::TEXT,
        p.transaction_hash,
        p.created_at,
        p.completed_at
    FROM payments p
    LEFT JOIN tasks t ON p.task_id = t.id
    WHERE p.executor_id = p_executor_id
      AND p.payment_type IN ('partial_release', 'final_release', 'full_release', 'withdrawal')
    ORDER BY p.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$;

-- Get executor balance summary
CREATE OR REPLACE FUNCTION get_executor_balance_summary(p_executor_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'executor_id', e.id,
        'wallet_address', e.wallet_address,
        'balance_usdc', e.balance_usdc,
        'total_earned_usdc', e.total_earned_usdc,
        'total_withdrawn_usdc', e.total_withdrawn_usdc,
        'pending_payments', COALESCE(pending.amount, 0),
        'pending_withdrawals', COALESCE(pending_withdrawals.amount, 0),
        'recent_payments_count', COALESCE(recent.count, 0)
    ) INTO v_result
    FROM executors e
    LEFT JOIN LATERAL (
        SELECT COALESCE(SUM(amount_usdc), 0) as amount
        FROM payments
        WHERE executor_id = e.id AND status = 'pending'
    ) pending ON true
    LEFT JOIN LATERAL (
        SELECT COALESCE(SUM(amount_usdc), 0) as amount
        FROM withdrawals
        WHERE executor_id = e.id AND status = 'pending'
    ) pending_withdrawals ON true
    LEFT JOIN LATERAL (
        SELECT COUNT(*) as count
        FROM payments
        WHERE executor_id = e.id
          AND status = 'completed'
          AND completed_at > NOW() - INTERVAL '30 days'
    ) recent ON true
    WHERE e.id = p_executor_id;

    RETURN v_result;
END;
$$;

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE escrows ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE withdrawals ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- ESCROWS RLS
-- ---------------------------------------------------------------------------

-- Executors can view escrows for tasks they're assigned to
CREATE POLICY "escrows_select_executor" ON escrows
    FOR SELECT
    USING (beneficiary_id IN (SELECT id FROM executors WHERE user_id = auth.uid()));

-- Agents can view their own escrows
CREATE POLICY "escrows_select_agent" ON escrows
    FOR SELECT
    USING (true);  -- API validates agent_id

-- Service role full access
CREATE POLICY "escrows_service_role" ON escrows
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- PAYMENTS RLS
-- ---------------------------------------------------------------------------

-- Executors can view their own payments
CREATE POLICY "payments_select_own" ON payments
    FOR SELECT
    USING (executor_id IN (SELECT id FROM executors WHERE user_id = auth.uid()));

-- Agents can view payments for their tasks
CREATE POLICY "payments_select_agent" ON payments
    FOR SELECT
    USING (true);  -- API validates task ownership

-- Service role full access
CREATE POLICY "payments_service_role" ON payments
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- WITHDRAWALS RLS
-- ---------------------------------------------------------------------------

-- Executors can view their own withdrawals
CREATE POLICY "withdrawals_select_own" ON withdrawals
    FOR SELECT
    USING (executor_id IN (SELECT id FROM executors WHERE user_id = auth.uid()));

-- Executors can create withdrawals
CREATE POLICY "withdrawals_insert_own" ON withdrawals
    FOR INSERT
    TO authenticated
    WITH CHECK (executor_id IN (SELECT id FROM executors WHERE user_id = auth.uid()));

-- Service role full access
CREATE POLICY "withdrawals_service_role" ON withdrawals
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Active escrows summary
CREATE OR REPLACE VIEW active_escrows_summary AS
SELECT
    e.id,
    e.task_id,
    e.agent_id,
    e.status,
    e.total_amount_usdc,
    e.released_amount_usdc,
    e.remaining_usdc,
    e.expires_at,
    t.title as task_title,
    t.status as task_status,
    ex.display_name as beneficiary_name
FROM escrows e
JOIN tasks t ON e.task_id = t.id
LEFT JOIN executors ex ON e.beneficiary_id = ex.id
WHERE e.status IN ('pending', 'funded', 'partial_released');

-- Payment statistics per executor
CREATE OR REPLACE VIEW executor_payment_stats AS
SELECT
    executor_id,
    COUNT(*) as total_payments,
    COUNT(*) FILTER (WHERE status = 'completed') as completed_payments,
    SUM(amount_usdc) FILTER (WHERE status = 'completed') as total_received,
    SUM(fee_usdc) FILTER (WHERE status = 'completed') as total_fees_paid,
    AVG(amount_usdc) FILTER (WHERE status = 'completed') as avg_payment_amount,
    MAX(completed_at) as last_payment_at
FROM payments
WHERE payment_type IN ('partial_release', 'final_release', 'full_release')
GROUP BY executor_id;

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT EXECUTE ON FUNCTION create_task_escrow TO authenticated;
GRANT EXECUTE ON FUNCTION fund_escrow TO service_role;
GRANT EXECUTE ON FUNCTION release_partial_payment TO service_role;
GRANT EXECUTE ON FUNCTION release_final_payment TO service_role;
GRANT EXECUTE ON FUNCTION refund_escrow TO service_role;
GRANT EXECUTE ON FUNCTION get_executor_payments TO authenticated;
GRANT EXECUTE ON FUNCTION get_executor_balance_summary TO authenticated;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE escrows IS 'x402 escrow tracking for task bounties';
COMMENT ON TABLE payments IS 'All payment transactions (releases, refunds, withdrawals)';
COMMENT ON TABLE withdrawals IS 'Executor withdrawal requests to external wallets';

COMMENT ON COLUMN escrows.net_bounty_usdc IS 'Bounty after platform fee (auto-calculated)';
COMMENT ON COLUMN escrows.remaining_usdc IS 'Amount still in escrow (auto-calculated)';
COMMENT ON COLUMN payments.net_amount_usdc IS 'Amount after fees (auto-calculated)';

COMMENT ON FUNCTION create_task_escrow IS 'Create an escrow record for a task';
COMMENT ON FUNCTION release_partial_payment IS 'Release 30% of bounty on submission';
COMMENT ON FUNCTION release_final_payment IS 'Release remaining 70% on approval';
COMMENT ON FUNCTION refund_escrow IS 'Refund remaining escrow to agent';
