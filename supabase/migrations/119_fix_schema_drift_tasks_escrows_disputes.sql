-- ============================================================================
-- Migration: 119_fix_schema_drift_tasks_escrows_disputes.sql
-- Description: Align live DB with canonical schema for tasks, escrows and
--              disputes. The production tables were created from older
--              variants of 001/002/004 and several columns those files claim
--              were never applied. The drift-tolerance retry loops in
--              supabase_client.py / _helpers.py have been silently dropping
--              writes to these columns ever since:
--
--              * tasks    — 14 columns missing vs 001. Observed in prod:
--                "Failed to store ERC-8004 identity on task <id>: no
--                compatible columns found" (metadata dropped on every task);
--                assignment_notes (assign_task) and completion_notes (admin
--                cancel) also silently dropped.
--              * escrows  — agent_id / beneficiary_address / network dropped
--                on every escrow insert (migration 089 was never applied).
--              * disputes — manual resolution endpoint (disputes.py) PATCHes
--                resolution_type / agent_refund_usdc / executor_payout_usdc /
--                resolved_by / closed_at with NO retry loop, so PostgREST
--                rejects the whole update: dispute resolution hard-fails.
--                The live dispute_status enum also lacks 'settled' (split
--                verdict) and the other 004 labels.
--
-- Date: 2026-06-10
-- Idempotent: YES (safe to re-run; no-op on fresh installs built from 001+)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. TASKS — restore the 14 columns defined in 001_initial_schema.sql
-- ---------------------------------------------------------------------------

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS agent_name VARCHAR(255);
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS location_address TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS chain_id INTEGER DEFAULT 8453;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS estimated_duration_minutes INTEGER;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS required_tier executor_tier DEFAULT 'probation';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT TRUE;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS accepted_at TIMESTAMPTZ;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS assignment_notes TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completion_notes TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS external_id VARCHAR(255);
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;

-- Indexes from 001 that depend on the restored columns
CREATE INDEX IF NOT EXISTS idx_tasks_published
    ON tasks(published_at DESC) WHERE published_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_tags ON tasks USING GIN(tags);

-- published_at trigger from 001 (verbatim)
CREATE OR REPLACE FUNCTION set_published_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'published' AND OLD.status != 'published' THEN
        NEW.published_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tasks_set_published_at ON tasks;
CREATE TRIGGER tasks_set_published_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION set_published_at();

-- ---------------------------------------------------------------------------
-- 2. ESCROWS — columns the backend writes on every insert (002/089 types)
-- ---------------------------------------------------------------------------

ALTER TABLE escrows ADD COLUMN IF NOT EXISTS agent_id VARCHAR(255);
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS beneficiary_address VARCHAR(42);
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS network TEXT DEFAULT 'base';
ALTER TABLE escrows ADD COLUMN IF NOT EXISTS chain_id INTEGER DEFAULT 8453;

CREATE INDEX IF NOT EXISTS idx_escrows_agent ON escrows(agent_id);

-- Backfill agent_id from the owning task (reliable join; new rows get it
-- directly from the insert payload once the column exists)
UPDATE escrows e
SET agent_id = t.agent_id
FROM tasks t
WHERE e.task_id = t.id AND e.agent_id IS NULL;

-- Backfill network from metadata where the dispatcher recorded it
UPDATE escrows
SET network = metadata->>'network'
WHERE NULLIF(metadata->>'network', '') IS NOT NULL
  AND network IS DISTINCT FROM metadata->>'network';

-- Backfill chain_id from network name (mapping from 089)
UPDATE escrows
SET chain_id = CASE network
    WHEN 'base'         THEN 8453
    WHEN 'ethereum'     THEN 1
    WHEN 'polygon'      THEN 137
    WHEN 'arbitrum'     THEN 42161
    WHEN 'celo'         THEN 42220
    WHEN 'monad'        THEN 143
    WHEN 'avalanche'    THEN 43114
    WHEN 'optimism'     THEN 10
    WHEN 'skale'        THEN 1187947933
    WHEN 'base-sepolia' THEN 84532
    ELSE 8453
END
WHERE chain_id IS NULL OR chain_id = 8453;

-- beneficiary_address is NOT backfilled: historical values were dropped at
-- insert time and are unrecoverable. Populated going forward.

-- ---------------------------------------------------------------------------
-- 3. DISPUTES — resolution columns from 004 used by the manual-resolution
--    endpoint (mcp_server/api/routers/disputes.py)
-- ---------------------------------------------------------------------------

ALTER TABLE disputes ADD COLUMN IF NOT EXISTS resolution_type VARCHAR(50);
ALTER TABLE disputes ADD COLUMN IF NOT EXISTS agent_refund_usdc DECIMAL(18, 6) DEFAULT 0;
ALTER TABLE disputes ADD COLUMN IF NOT EXISTS executor_payout_usdc DECIMAL(18, 6) DEFAULT 0;
ALTER TABLE disputes ADD COLUMN IF NOT EXISTS resolved_by VARCHAR(255);
ALTER TABLE disputes ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ;

-- ---------------------------------------------------------------------------
-- 4. dispute_status enum — restore the labels from 004 missing in live.
--    'settled' is required by the split verdict; cleanup_zombie_disputes.py
--    documents the missing 'closed'. ADD VALUE appends (order differs from
--    004) — nothing compares enum sort order.
-- ---------------------------------------------------------------------------

ALTER TYPE dispute_status ADD VALUE IF NOT EXISTS 'awaiting_response';
ALTER TYPE dispute_status ADD VALUE IF NOT EXISTS 'in_arbitration';
ALTER TYPE dispute_status ADD VALUE IF NOT EXISTS 'settled';
ALTER TYPE dispute_status ADD VALUE IF NOT EXISTS 'closed';
ALTER TYPE dispute_status ADD VALUE IF NOT EXISTS 'expired';

-- ---------------------------------------------------------------------------
-- 5. Refresh PostgREST schema cache so the new columns are writable
--    immediately (otherwise inserts/updates keep failing with PGRST204
--    until the next reload).
-- ---------------------------------------------------------------------------

NOTIFY pgrst, 'reload schema';
