-- Migration 108: pay.sh MPP session bindings + event log (Phase 2.6).
--
-- Context:
--   Solana payments in Execution Market are routed through pay.sh
--   (solana-foundation/pay) running as a sidecar in the same ECS task as
--   the FastAPI backend. Each accepted Solana task opens a Money Payment
--   Protocol (MPP) channel — pay.sh holds the on-chain state, emits SSE
--   voucher events, and runs settleAndFinalize at close time. EM never
--   signs Solana TXs; we just orchestrate channel lifecycle and surface
--   a "taxímetro" feed to the dashboard (Phase 2.8).
--
--   To do that we need durable storage for:
--     1) task_id ↔ channel_id binding (so refunds + close work after
--        the request that opened the channel has ended)
--     2) Append-only log of every SSE event received from pay.sh per
--        channel (so the taxímetro replay works across container
--        restarts and so audits can reconstruct exactly what pay.sh
--        accepted on-chain).
--
--   Solana settlement is the source of truth (D-21 in the master plan):
--   if pay.sh says it settled, we mark the task complete. If pay.sh
--   says expired, we mark refunded. The DB rows here are a mirror, not
--   an authority — never use them to gate payouts.
--
-- Idempotent: uses IF NOT EXISTS everywhere. Safe to re-run.

-- ---------------------------------------------------------------------------
-- 1. task_channel_bindings — links a task to a pay.sh MPP channel
-- ---------------------------------------------------------------------------
-- One row per task that ever opened a Solana session. channel_id is the
-- pay.sh-assigned base58 public key. payer/payee are recorded for audit;
-- pay.sh authenticates payer via voucher signature on the wire.
--
-- A task can only have ONE active channel at a time, but if a channel
-- expires (idle close, errored) the task can re-open a new one — that
-- second row is what wins for refund/settle dispatch. We model this by
-- letting status flow open → draining → settled/expired/errored, and
-- the dispatcher's _lookup_channel_id() reads the most-recent row.
CREATE TABLE IF NOT EXISTS task_channel_bindings (
    id                  UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    task_id             UUID         NOT NULL,
    channel_id          VARCHAR(64)  NOT NULL,        -- base58 pubkey
    payer               VARCHAR(64),                  -- base58 payer pubkey
    payee               VARCHAR(64),                  -- base58 payee pubkey
    cap_usdc            NUMERIC(20, 6),               -- declared cap when channel opened
    status              VARCHAR(16)  NOT NULL DEFAULT 'open',
    accepted_uusdc      BIGINT       NOT NULL DEFAULT 0,  -- last accepted cumulative (1 USDC = 1_000_000 uusdc)
    voucher_count       INTEGER      NOT NULL DEFAULT 0,
    settlement_tx_hash  VARCHAR(128),                 -- base58 Solana TX signature
    refund_uusdc        BIGINT       NOT NULL DEFAULT 0,
    opened_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    settled_at          TIMESTAMPTZ,
    metadata            JSONB        NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT chk_tcb_status
        CHECK (status IN ('open', 'draining', 'settled', 'expired', 'errored')),
    CONSTRAINT uq_tcb_channel UNIQUE (channel_id)
);

COMMENT ON TABLE task_channel_bindings IS
    'Maps a task to its pay.sh MPP channel. Source of truth is pay.sh; this is a mirror updated by the SSE relay (Phase 2.8) and by close-now responses (Phase 2.5 dispatcher).';
COMMENT ON COLUMN task_channel_bindings.channel_id IS
    'Base58 Solana pubkey of the channel TokenStore (assigned by pay.sh on open).';
COMMENT ON COLUMN task_channel_bindings.accepted_uusdc IS
    'Most recent accepted cumulative voucher value in micro-USDC. Drives the taxímetro UI.';
COMMENT ON COLUMN task_channel_bindings.refund_uusdc IS
    'On settlement, the cap remainder that returned to payer. Non-zero whenever bounty < cap.';

CREATE INDEX IF NOT EXISTS idx_tcb_task_id
    ON task_channel_bindings (task_id, opened_at DESC);
CREATE INDEX IF NOT EXISTS idx_tcb_status
    ON task_channel_bindings (status) WHERE status IN ('open', 'draining');
CREATE INDEX IF NOT EXISTS idx_tcb_payer
    ON task_channel_bindings (payer) WHERE payer IS NOT NULL;

ALTER TABLE task_channel_bindings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "tcb_service_only" ON task_channel_bindings;
CREATE POLICY "tcb_service_only" ON task_channel_bindings
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- 2. mpp_session_events — append-only mirror of pay.sh SSE events
-- ---------------------------------------------------------------------------
-- Every event we receive from pay.sh's /_sessions/{id}/events SSE stream
-- is logged here. The taxímetro router (Phase 2.8) reads this back for
-- replay after a reconnect. Events are NEVER updated — pay.sh's behaviour
-- is the only one that can affect on-chain state, so a "fix" to this log
-- would just be drift.
--
-- event_type values map 1:1 to pay.sh SSE event names:
--   session_open          → channel opened, first cap deposit confirmed
--   voucher_accepted      → worker submitted a voucher, facilitator accepted
--   session_close         → close-now or idle-close triggered (drain phase)
--   settlement_complete   → on-chain settleAndFinalize confirmed
--   error                 → pay.sh emitted an error (e.g. invalid voucher)
CREATE TABLE IF NOT EXISTS mpp_session_events (
    id              UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    channel_id      VARCHAR(64)  NOT NULL,
    task_id         UUID,                                 -- denormalized for fast taximetro lookup
    event_type      VARCHAR(32)  NOT NULL,
    cumulative_uusdc BIGINT,                              -- present on voucher_accepted
    voucher_index   INTEGER,                              -- present on voucher_accepted
    tx_hash         VARCHAR(128),                         -- present on settlement_complete
    payload         JSONB        NOT NULL DEFAULT '{}'::jsonb,
    received_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_mpp_event_type
        CHECK (event_type IN (
            'session_open',
            'voucher_accepted',
            'session_close',
            'settlement_complete',
            'error'
        ))
);

COMMENT ON TABLE mpp_session_events IS
    'Append-only mirror of SSE events from pay.sh /_sessions/{id}/events. Powers the taxímetro replay (Phase 2.8). Never UPDATE — only INSERT.';
COMMENT ON COLUMN mpp_session_events.cumulative_uusdc IS
    'Cumulative voucher value in micro-USDC at time of acceptance. NULL except on voucher_accepted events.';
COMMENT ON COLUMN mpp_session_events.tx_hash IS
    'Solana base58 TX signature. NULL except on settlement_complete events.';
COMMENT ON COLUMN mpp_session_events.payload IS
    'Full SSE data payload, JSON-decoded. Kept so the taxímetro can re-render any future field without a migration.';

-- Hot-path index: taxímetro pulls "last N events for channel X" on every
-- SSE reconnect, so this needs to be fast.
CREATE INDEX IF NOT EXISTS idx_mpp_events_channel_received
    ON mpp_session_events (channel_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_mpp_events_task
    ON mpp_session_events (task_id, received_at DESC) WHERE task_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mpp_events_settlement
    ON mpp_session_events (tx_hash) WHERE event_type = 'settlement_complete';

ALTER TABLE mpp_session_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "mpp_events_service_only" ON mpp_session_events;
CREATE POLICY "mpp_events_service_only" ON mpp_session_events
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- 3. Extend payment_events.event_type CHECK constraint
-- ---------------------------------------------------------------------------
-- The Solana session dispatcher path (payment_dispatcher.py
-- _authorize_solana_session, _release_solana_session, _refund_solana_session)
-- emits new event types. Without this, the CHECK from migration 053 rejects
-- those inserts — log_payment_event swallows the error so payments still
-- work, but the audit trail goes blank for Solana flows. Add them now.
ALTER TABLE payment_events DROP CONSTRAINT IF EXISTS chk_payment_events_event_type;
ALTER TABLE payment_events ADD CONSTRAINT chk_payment_events_event_type
    CHECK (event_type IN (
        -- Core payment flow
        'verify',
        'balance_check',
        'store_auth',
        'settle',
        -- Fase 1 direct settlement
        'settle_worker_direct',
        'settle_fee_direct',
        -- Fase 2/5 escrow flow
        'escrow_authorize',
        'escrow_release',
        'escrow_refund',
        -- Platform release disbursements
        'disburse_worker',
        'disburse_fee',
        'distribute_fees',
        'fee_sweep',
        'fee_collect',
        -- H2A (human-published tasks)
        'h2a_settle_worker',
        'h2a_settle_fee',
        'h2a_settle_error',
        -- Reputation events
        'reputation_agent_rates_worker',
        'reputation_worker_rates_agent',
        -- Lifecycle
        'refund',
        'cancel',
        'error',
        -- Solana / pay.sh MPP session events (Phase 2.5 / 2.6)
        'solana_session_authorize',
        'solana_session_release',
        'solana_session_refund',
        'payshell_session_open',
        'payshell_voucher_accepted',
        'payshell_session_close',
        'payshell_settlement_complete'
    ));

-- ---------------------------------------------------------------------------
-- 4. Helper: upsert a task↔channel binding from an SSE session_open event
-- ---------------------------------------------------------------------------
-- Called from the taxímetro relay (Phase 2.8) when it sees the first
-- session_open event. The relay does not always know task_id at this
-- point — pay.sh emits channel_id first, and we backfill task_id later
-- via the X-EM-Task-Id header captured by the middleware (Phase 2.4).
-- Using a function keeps the upsert atomic.
CREATE OR REPLACE FUNCTION upsert_task_channel_binding(
    p_channel_id   VARCHAR,
    p_task_id      UUID,
    p_payer        VARCHAR,
    p_payee        VARCHAR,
    p_cap_usdc     NUMERIC,
    p_metadata     JSONB DEFAULT '{}'::jsonb
) RETURNS UUID AS $$
DECLARE
    binding_id UUID;
BEGIN
    INSERT INTO task_channel_bindings (
        channel_id, task_id, payer, payee, cap_usdc, status, metadata
    ) VALUES (
        p_channel_id, p_task_id, p_payer, p_payee, p_cap_usdc, 'open', p_metadata
    )
    ON CONFLICT (channel_id) DO UPDATE SET
        -- Backfill task_id and payer/payee only if not already set.
        task_id  = COALESCE(task_channel_bindings.task_id, EXCLUDED.task_id),
        payer    = COALESCE(task_channel_bindings.payer,   EXCLUDED.payer),
        payee    = COALESCE(task_channel_bindings.payee,   EXCLUDED.payee),
        cap_usdc = COALESCE(task_channel_bindings.cap_usdc, EXCLUDED.cap_usdc),
        metadata = task_channel_bindings.metadata || EXCLUDED.metadata
    RETURNING id INTO binding_id;
    RETURN binding_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION upsert_task_channel_binding IS
    'Idempotent insert/update of task_channel_bindings on pay.sh session_open. Backfills task_id/payer/payee if NULL, otherwise leaves them alone. Used by the taxímetro SSE relay (Phase 2.8).';
