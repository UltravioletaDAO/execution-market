-- Migration: 084_world_agentkit.sql
-- Adds World AgentKit human verification columns to executors.
ALTER TABLE executors
    ADD COLUMN IF NOT EXISTS world_human_id INTEGER DEFAULT NULL;
ALTER TABLE executors
    ADD COLUMN IF NOT EXISTS world_verified_at TIMESTAMPTZ DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_executors_world_human_id
    ON executors(world_human_id)
    WHERE world_human_id IS NOT NULL AND world_human_id > 0;

COMMENT ON COLUMN executors.world_human_id IS
    'World AgentKit humanId from AgentBook contract. >0 = verified human. NULL = not checked.';
COMMENT ON COLUMN executors.world_verified_at IS
    'Timestamp when World human verification was last confirmed on-chain.';
