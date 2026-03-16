-- Migration 037: Karma Kadabra Swarm State Tables
-- Phase 8: Shared state for coordinator and all KK agents

-- Agent state table: coordinator reads this to know who is idle/busy
CREATE TABLE IF NOT EXISTS kk_swarm_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL UNIQUE,
    task_id TEXT,
    status TEXT NOT NULL DEFAULT 'idle',
    last_heartbeat TIMESTAMPTZ,
    daily_spent_usd DECIMAL(10,2) DEFAULT 0,
    current_chain TEXT DEFAULT 'base',
    notes TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kk_swarm_state_agent ON kk_swarm_state(agent_name);
CREATE INDEX IF NOT EXISTS idx_kk_swarm_state_status ON kk_swarm_state(status);

-- Task claim table: prevents two agents from claiming the same EM task
CREATE TABLE IF NOT EXISTS kk_task_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    em_task_id TEXT NOT NULL UNIQUE,
    claimed_by TEXT NOT NULL,
    claimed_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'claimed'
);

CREATE INDEX IF NOT EXISTS idx_kk_task_claims_status ON kk_task_claims(status);

-- Notification table: coordinator sends assignments, agents acknowledge
CREATE TABLE IF NOT EXISTS kk_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_agent TEXT NOT NULL,
    from_agent TEXT NOT NULL,
    content TEXT NOT NULL,
    delivered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kk_notifications_target ON kk_notifications(target_agent, delivered);
