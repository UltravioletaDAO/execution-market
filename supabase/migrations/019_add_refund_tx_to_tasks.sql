-- Migration 019: Add refund_tx to tasks for on-chain refund tracking
-- Stores the on-chain transaction hash when a funded escrow is refunded.
-- For authorize-only (EIP-3009), this remains NULL (authorization just expires).

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS refund_tx TEXT;

COMMENT ON COLUMN tasks.refund_tx IS 'On-chain tx hash from escrow refund (NULL for authorize-only cancellations)';

-- Index for finding tasks with pending refunds
CREATE INDEX IF NOT EXISTS idx_tasks_refund_tx ON tasks(refund_tx) WHERE refund_tx IS NOT NULL;
