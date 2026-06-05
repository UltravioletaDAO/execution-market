-- Migration 110: MoonPay sign-url velocity-cap attempt log (F-05, post-audit 2026-06-05).
--
-- Context:
--   The /api/v1/moonpay/sign-url endpoint hands back a bearer-like signed
--   Widget URL — anyone holding it can initiate a buy that debits our MoonPay
--   account (threat "onramp link abuse" / R3 chargeback rings in
--   docs/runbooks/onramp-fraud.md). The fraud runbook lists server-side
--   velocity caps as a pre-launch blocker.
--
--   The moonpay_transactions table (migration 109) CANNOT serve as the
--   velocity counter: it is only written when a webhook lands AFTER a buy
--   completes (minutes later, if ever), it has no IP column, and a fraudster
--   requesting 50 signed URLs in a row generates ZERO transaction rows. The
--   risk moment is the sign-url request itself, so we log every *attempt*
--   here — across the three dimensions the runbook requires (user / wallet /
--   IP) — and count them in a rolling 24h window before issuing a URL.
--
--   This is a fraud-velocity ledger, NOT an authority over funds. Pruning old
--   rows (> 48h) is safe; the cap window is 24h.
--
-- Idempotent: uses IF NOT EXISTS everywhere. Safe to re-run.

-- ---------------------------------------------------------------------------
-- 1. moonpay_onramp_attempts — one row per /sign-url request that passed caps
-- ---------------------------------------------------------------------------
-- We record the attempt right before signing (after the caps allowed it), so
-- the row count reflects URLs actually issued. external_customer_id is
-- optional (anonymous landing-page demos omit it); wallet_address and
-- request_ip are always present so per-wallet and per-IP caps still apply to
-- anonymous callers.
CREATE TABLE IF NOT EXISTS moonpay_onramp_attempts (
    id                    UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    external_customer_id  TEXT,                                  -- = EM executor.id UUID, optional
    wallet_address        TEXT         NOT NULL,                 -- destination wallet (chain implied by currency)
    request_ip            TEXT         NOT NULL,                 -- trusted-proxy-resolved client IP
    base_amount           NUMERIC(20, 6) NOT NULL,               -- fiat amount requested (for the per-user $/24h cap)
    base_currency_code    TEXT         NOT NULL DEFAULT 'usd',
    crypto_currency_code  TEXT         NOT NULL,                 -- e.g. usdc_base, usdc_sol
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE moonpay_onramp_attempts IS
    'Fraud-velocity ledger for MoonPay sign-url. One row per issued signed Widget URL. Counted in a rolling 24h window (per user / wallet / IP) to cap onramp velocity before signing. NOT an authority over funds — prune rows > 48h freely.';
COMMENT ON COLUMN moonpay_onramp_attempts.base_amount IS
    'Fiat amount requested on this attempt. Summed per external_customer_id over 24h for the per-user USD velocity cap.';
COMMENT ON COLUMN moonpay_onramp_attempts.request_ip IS
    'Client IP resolved via utils.net.get_client_ip (trusted-proxy aware). Drives the per-IP cap that catches account farming.';

-- ---------------------------------------------------------------------------
-- 2. Indexes — the cap checks are the only read path; all are time-windowed.
-- ---------------------------------------------------------------------------
-- Per-user count + USD sum over 24h.
CREATE INDEX IF NOT EXISTS idx_moonpay_attempts_customer
    ON moonpay_onramp_attempts (external_customer_id, created_at DESC)
    WHERE external_customer_id IS NOT NULL;

-- Per-wallet count over 24h.
CREATE INDEX IF NOT EXISTS idx_moonpay_attempts_wallet
    ON moonpay_onramp_attempts (wallet_address, created_at DESC);

-- Per-IP count over 24h.
CREATE INDEX IF NOT EXISTS idx_moonpay_attempts_ip
    ON moonpay_onramp_attempts (request_ip, created_at DESC);

-- ---------------------------------------------------------------------------
-- 3. RLS — service_role only. The backend writes/reads with the service key;
--    no dashboard user should ever see another caller's onramp velocity.
-- ---------------------------------------------------------------------------
ALTER TABLE moonpay_onramp_attempts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "moonpay_attempts_service_only" ON moonpay_onramp_attempts;
CREATE POLICY "moonpay_attempts_service_only"
    ON moonpay_onramp_attempts
    FOR ALL
    TO service_role
    USING (true) WITH CHECK (true);
