-- ============================================================================
-- EXECUTION MARKET: Add ERC-8004 Agent Identity to Tasks
-- Migration: 019_tasks_erc8004_agent_id.sql
-- Description: Adds erc8004_agent_id column to tasks for on-chain identity
--              verification during task creation.  The column is nullable
--              because not all agents have registered ERC-8004 identities.
-- Version: 1.0.0
-- Date: 2026-02-06
-- ============================================================================

-- Add the column (nullable VARCHAR, matches executors.erc8004_agent_id)
ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS erc8004_agent_id VARCHAR(255);

-- Index for filtering/querying by on-chain agent ID
CREATE INDEX IF NOT EXISTS idx_tasks_erc8004_agent_id
    ON tasks(erc8004_agent_id)
    WHERE erc8004_agent_id IS NOT NULL;

COMMENT ON COLUMN tasks.erc8004_agent_id IS
    'ERC-8004 on-chain agent token ID, populated during task creation if the '
    'agent has a registered identity on the Identity Registry.';
