-- Migration 081: Task Lifecycle Checkpoints
-- Tracks the boolean/timestamped state of every lifecycle checkpoint per task.
-- Used by the Audit Grid to show which steps each task has completed.

CREATE TABLE IF NOT EXISTS task_lifecycle_checkpoints (
    task_id               UUID PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,

    -- Authentication & Identity
    auth_erc8128          BOOLEAN NOT NULL DEFAULT FALSE,
    auth_erc8128_at       TIMESTAMPTZ,
    identity_erc8004      BOOLEAN NOT NULL DEFAULT FALSE,
    identity_erc8004_at   TIMESTAMPTZ,
    agent_id_resolved     VARCHAR(20),

    -- Balance & Payment Auth
    balance_sufficient    BOOLEAN NOT NULL DEFAULT FALSE,
    balance_checked_at    TIMESTAMPTZ,
    balance_amount_usdc   DECIMAL(20, 6),
    payment_auth_signed   BOOLEAN NOT NULL DEFAULT FALSE,
    payment_auth_at       TIMESTAMPTZ,

    -- Task Creation
    task_created          BOOLEAN NOT NULL DEFAULT FALSE,
    task_created_at       TIMESTAMPTZ,
    network               VARCHAR(30),
    token                 VARCHAR(10),
    bounty_usdc           DECIMAL(10, 2),
    skill_version         VARCHAR(20),

    -- Escrow
    escrow_locked         BOOLEAN NOT NULL DEFAULT FALSE,
    escrow_locked_at      TIMESTAMPTZ,
    escrow_tx             VARCHAR(66),

    -- Assignment
    worker_assigned       BOOLEAN NOT NULL DEFAULT FALSE,
    worker_assigned_at    TIMESTAMPTZ,
    worker_id             UUID,
    worker_erc8004        BOOLEAN NOT NULL DEFAULT FALSE,

    -- Evidence
    evidence_submitted    BOOLEAN NOT NULL DEFAULT FALSE,
    evidence_submitted_at TIMESTAMPTZ,
    evidence_count        INTEGER NOT NULL DEFAULT 0,

    -- Verification
    ai_verified           BOOLEAN NOT NULL DEFAULT FALSE,
    ai_verified_at        TIMESTAMPTZ,
    ai_verdict            VARCHAR(20),

    -- Approval & Payment
    approved              BOOLEAN NOT NULL DEFAULT FALSE,
    approved_at           TIMESTAMPTZ,
    payment_released      BOOLEAN NOT NULL DEFAULT FALSE,
    payment_released_at   TIMESTAMPTZ,
    payment_tx            VARCHAR(66),
    worker_amount_usdc    DECIMAL(20, 6),
    fee_amount_usdc       DECIMAL(20, 6),

    -- Reputation
    agent_rated_worker    BOOLEAN NOT NULL DEFAULT FALSE,
    agent_rated_worker_at TIMESTAMPTZ,
    worker_rated_agent    BOOLEAN NOT NULL DEFAULT FALSE,
    worker_rated_agent_at TIMESTAMPTZ,

    -- Fee Distribution
    fees_distributed      BOOLEAN NOT NULL DEFAULT FALSE,
    fees_distributed_at   TIMESTAMPTZ,
    fees_tx               VARCHAR(66),

    -- Terminal States
    cancelled             BOOLEAN NOT NULL DEFAULT FALSE,
    cancelled_at          TIMESTAMPTZ,
    refunded              BOOLEAN NOT NULL DEFAULT FALSE,
    refunded_at           TIMESTAMPTZ,
    refund_tx             VARCHAR(66),
    expired               BOOLEAN NOT NULL DEFAULT FALSE,
    expired_at            TIMESTAMPTZ,

    -- Meta
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tlc_updated ON task_lifecycle_checkpoints(updated_at DESC);
CREATE INDEX idx_tlc_skill_version ON task_lifecycle_checkpoints(skill_version) WHERE skill_version IS NOT NULL;

-- RLS: service role only (audit data is internal)
ALTER TABLE task_lifecycle_checkpoints ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "service_role_all" ON task_lifecycle_checkpoints
    FOR ALL USING (auth.role() = 'service_role');

-- Allow authenticated users to read their own tasks' checkpoints
CREATE POLICY "authenticated_read_own" ON task_lifecycle_checkpoints
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM tasks t
            WHERE t.id = task_lifecycle_checkpoints.task_id
            AND (
                t.agent_id = auth.jwt() ->> 'sub'
                OR t.executor_id::text = auth.jwt() ->> 'sub'
            )
        )
    );
