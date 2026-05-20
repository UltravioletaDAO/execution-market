-- Migration 109: MoonPay headless on-ramp transaction mirror (Phase 4.6).
--
-- Context:
--   Phase 4 of MASTER_PLAN_SOLANA_MPP_ROBOT_DEMO adds a just-in-time USDC
--   on-ramp so an agent (or worker) can refill its Solana wallet without
--   leaving the EM dashboard. MoonPay holds the source of truth for the
--   fiat→crypto leg; we receive lifecycle events via the
--   Moonpay-Signature-V2 webhook (Phase 4.5) and mirror them here so the
--   dashboard can poll a single Supabase Realtime channel for balance
--   updates (Phase 4.9) and so audits can reconstruct what MoonPay told us.
--
--   This table is a MIRROR, not an authority — never gate fund movement on
--   what is written here. If the webhook is lost we'll catch up via
--   MoonPay's REST API; if we disagree with MoonPay, MoonPay wins.
--
-- Idempotent: uses IF NOT EXISTS everywhere. Safe to re-run.

-- ---------------------------------------------------------------------------
-- 1. moonpay_transactions — one row per MoonPay transaction
-- ---------------------------------------------------------------------------
-- moonpay_transaction_id is MoonPay's internal id (from webhook `data.id`).
-- It's nullable because we may create a row pre-emptively when the agent
-- requests a signed URL (Phase 4.4) and only learn the MoonPay id after the
-- first webhook arrives. The UNIQUE constraint ignores NULLs so multiple
-- pre-webhook rows coexist; once the first event lands we backfill the id
-- and any subsequent row would conflict (correct: only one row per txn).
--
-- external_customer_id is the EM executor.id UUID rendered as text (MoonPay
-- requires a string). It's optional because /sign-url accepts an anonymous
-- call (no agent identity) for landing-page demos, but in production the
-- agent always supplies it so MoonPay's Customer Connection skips
-- re-onboarding for returning users.
--
-- Status values mirror MoonPay's `transaction.status` field. We do NOT add
-- a CHECK constraint — MoonPay extends this enum periodically (recent adds:
-- waitingForDeposit, processing) and we don't want a schema migration every
-- time. Comment documents the known set; raw_event preserves anything else.
CREATE TABLE IF NOT EXISTS moonpay_transactions (
    id                       UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    moonpay_transaction_id   TEXT,                                       -- MoonPay's data.id (set on first webhook)
    external_customer_id     TEXT,                                       -- = EM executor.id UUID, optional
    wallet_address           TEXT         NOT NULL,                      -- destination wallet (chain implied by currency)
    crypto_currency_code     TEXT         NOT NULL,                      -- e.g. usdc_sol, usdc_base
    base_amount              NUMERIC(20, 6),                             -- fiat amount the user paid
    quote_amount             NUMERIC(20, 6),                             -- crypto amount delivered to wallet
    fee_amount               NUMERIC(20, 6),                             -- MoonPay fee component
    status                   TEXT         NOT NULL DEFAULT 'pending',
    crypto_transaction_id    TEXT,                                       -- on-chain tx hash / Solana signature
    raw_event                JSONB        NOT NULL DEFAULT '{}'::jsonb,  -- last webhook payload (full)
    created_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_moonpay_transaction_id UNIQUE (moonpay_transaction_id)
);

COMMENT ON TABLE moonpay_transactions IS
    'Mirror of MoonPay headless on-ramp transactions. Source of truth is MoonPay; this table is updated by the Moonpay-Signature-V2 webhook receiver (Phase 4.5) and read by the useMoonPayOnramp hook (Phase 4.9). Never gate fund movement on these rows.';

COMMENT ON COLUMN moonpay_transactions.moonpay_transaction_id IS
    'MoonPay-assigned transaction id (from webhook data.id). NULL until first webhook arrives; UNIQUE ignores NULLs so pre-webhook rows can coexist.';

COMMENT ON COLUMN moonpay_transactions.external_customer_id IS
    'EM executor.id UUID rendered as text. Required for production /sign-url calls so MoonPay Customer Connection can skip re-onboarding; NULL for landing-page demos.';

COMMENT ON COLUMN moonpay_transactions.wallet_address IS
    'Destination wallet for the crypto leg. Format depends on crypto_currency_code (base58 for usdc_sol, 0x-hex for usdc_base, etc.).';

COMMENT ON COLUMN moonpay_transactions.status IS
    'MoonPay transaction.status enum. Known values: pending, waitingPayment, waitingAuthorization, waitingForDeposit, pendingAuthorization, processing, completed, failed. No CHECK constraint — MoonPay extends this set without notice.';

COMMENT ON COLUMN moonpay_transactions.raw_event IS
    'Last webhook payload received for this transaction. Powers any future field rendering without a schema migration.';

-- ---------------------------------------------------------------------------
-- 2. Indexes (hot paths only — no speculative indexes)
-- ---------------------------------------------------------------------------
-- Webhook receiver looks up by moonpay_transaction_id on every POST → must be fast.
-- The UNIQUE constraint above already creates this index, no extra needed.

-- useMoonPayOnramp hook (Phase 4.9) polls by external_customer_id ordered by
-- created_at DESC to render the txn list for the agent.
CREATE INDEX IF NOT EXISTS idx_moonpay_txn_customer
    ON moonpay_transactions (external_customer_id, created_at DESC)
    WHERE external_customer_id IS NOT NULL;

-- Balance-gating (Phase 4.7) queries by wallet_address to detect a fresh
-- delivery before re-attempting em_publish_task / em_assign_task.
CREATE INDEX IF NOT EXISTS idx_moonpay_txn_wallet
    ON moonpay_transactions (wallet_address, created_at DESC);

-- Ops dashboards filter by status (e.g. show all 'failed' from last 24h).
CREATE INDEX IF NOT EXISTS idx_moonpay_txn_status
    ON moonpay_transactions (status)
    WHERE status NOT IN ('completed', 'failed');

-- ---------------------------------------------------------------------------
-- 3. updated_at maintenance
-- ---------------------------------------------------------------------------
-- The webhook receiver upserts and sets updated_at = NOW() explicitly. We
-- also add a trigger so any out-of-band UPDATE (admin tooling, manual fix)
-- keeps updated_at honest. Same pattern as elsewhere in the schema.
CREATE OR REPLACE FUNCTION moonpay_transactions_touch_updated_at()
    RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_moonpay_transactions_touch ON moonpay_transactions;
CREATE TRIGGER trg_moonpay_transactions_touch
    BEFORE UPDATE ON moonpay_transactions
    FOR EACH ROW EXECUTE FUNCTION moonpay_transactions_touch_updated_at();

-- ---------------------------------------------------------------------------
-- 4. RLS — service_role full access; authenticated user reads own
-- ---------------------------------------------------------------------------
-- The webhook receiver runs with the service_role key, so it needs blanket
-- ALL access (signature is verified at the application layer before any
-- write happens).
--
-- A dashboard user (auth.uid()) can SELECT rows whose external_customer_id
-- matches an executor they own. This lets useMoonPayOnramp render the
-- agent's own on-ramp history without exposing other agents' transactions.
--
-- We deliberately do NOT grant INSERT/UPDATE/DELETE to authenticated — all
-- writes go through the backend.
ALTER TABLE moonpay_transactions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "moonpay_txn_service_all" ON moonpay_transactions;
CREATE POLICY "moonpay_txn_service_all"
    ON moonpay_transactions
    FOR ALL
    TO service_role
    USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "moonpay_txn_select_own" ON moonpay_transactions;
CREATE POLICY "moonpay_txn_select_own"
    ON moonpay_transactions
    FOR SELECT
    USING (
        external_customer_id IS NOT NULL
        AND external_customer_id IN (
            SELECT id::text FROM executors WHERE user_id = auth.uid()
        )
    );
