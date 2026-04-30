-- 106: ClawKey KYA (Know Your Agent) — bind agent keys to verified humans
-- Schema deviation from master plan: project uses `executors.agent_type='ai'`
-- instead of a separate `agents` table. ClawKey columns are added to executors.
-- See: docs/planning/MASTER_PLAN_VERYAI_INTEGRATION.md Phase 1.3

-- Add ClawKey columns to executors (applies to executors with agent_type='ai')
ALTER TABLE executors
  ADD COLUMN IF NOT EXISTS clawkey_verified boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS clawkey_human_id text DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS clawkey_device_id text DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS clawkey_public_key text DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS clawkey_registered_at timestamptz DEFAULT NULL;

-- Create agent KYA verifications table (audit trail)
CREATE TABLE IF NOT EXISTS agent_kya_verifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  executor_id uuid NOT NULL REFERENCES executors(id) ON DELETE CASCADE,
  clawkey_human_id text NOT NULL,
  clawkey_device_id text NOT NULL,
  clawkey_public_key text NOT NULL,
  registered_at timestamptz DEFAULT now(),
  last_verified_at timestamptz DEFAULT now(),
  CONSTRAINT uq_clawkey_public_key UNIQUE (clawkey_public_key),
  CONSTRAINT uq_clawkey_executor UNIQUE (executor_id)
);

-- Index for fast lookup by executor (agent)
CREATE INDEX IF NOT EXISTS idx_agent_kya_verifications_executor
  ON agent_kya_verifications(executor_id);

-- Index for cross-agent humanId lookups (find all agents bound to same human)
CREATE INDEX IF NOT EXISTS idx_agent_kya_verifications_human_id
  ON agent_kya_verifications(clawkey_human_id);

-- Index on executors for filtering ClawKey-verified agents
CREATE INDEX IF NOT EXISTS idx_executors_clawkey_verified
  ON executors(clawkey_verified)
  WHERE clawkey_verified = true;

-- Enable RLS
ALTER TABLE agent_kya_verifications ENABLE ROW LEVEL SECURITY;

-- Public read: KYA status is a public trust signal (similar to ERC-8004 reputation)
CREATE POLICY "agent_kya_verifications_select_public"
  ON agent_kya_verifications
  FOR SELECT
  USING (true);

-- Service role inserts after upstream verification at api.clawkey.ai
CREATE POLICY "agent_kya_verifications_service_insert"
  ON agent_kya_verifications
  FOR INSERT
  WITH CHECK (true);

-- Service role updates `last_verified_at` during periodic sync
CREATE POLICY "agent_kya_verifications_service_update"
  ON agent_kya_verifications
  FOR UPDATE
  USING (true);

-- Service role can delete (when ClawKey revokes the binding upstream)
CREATE POLICY "agent_kya_verifications_service_delete"
  ON agent_kya_verifications
  FOR DELETE
  USING (true);

COMMENT ON TABLE agent_kya_verifications IS
  'ClawKey Know Your Agent: binds an AI agent (executor with agent_type=ai) '
  'to a verified human via Ed25519 public key. Public read by design — '
  'KYA is a trust signal surfaced in agent profiles and showcase. '
  'Updated by background sync against api.clawkey.ai/v1.';

COMMENT ON COLUMN agent_kya_verifications.clawkey_human_id IS
  'humanId from ClawKey upstream. Multiple agents can share one human (one operator, many bots).';

COMMENT ON COLUMN agent_kya_verifications.clawkey_public_key IS
  'Agent Ed25519 public key (base58). UNIQUE — one key, one agent, one binding.';

COMMENT ON COLUMN executors.clawkey_verified IS
  'True when this agent (agent_type=ai) is registered in ClawKey and bound to a verified human. '
  'Additive trust signal — never blocks task creation or application.';
