-- Admin Actions Log
-- Tracks non-config admin operations: cancel_task, update_user_status, sweep_fees, retry_payment, update_task
-- Distinct from config_audit_log which tracks platform_config changes via trigger.

CREATE TABLE IF NOT EXISTS admin_actions_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  actor_id TEXT NOT NULL,
  action_type VARCHAR(100) NOT NULL,
  target_type VARCHAR(50),
  target_id TEXT,
  details JSONB DEFAULT '{}',
  result VARCHAR(20) DEFAULT 'success',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_admin_actions_type ON admin_actions_log(action_type);
CREATE INDEX idx_admin_actions_time ON admin_actions_log(created_at DESC);
