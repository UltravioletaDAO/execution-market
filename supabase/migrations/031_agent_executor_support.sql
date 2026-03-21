-- Migration 031: Agent Executor Support
-- Enables AI agents to register as task executors (not just publishers)
-- Part of A2A + OpenClaw integration

ALTER TABLE executors
  ADD COLUMN IF NOT EXISTS executor_type VARCHAR(10) DEFAULT 'human'
  CHECK (executor_type IN ('human', 'agent'));

ALTER TABLE executors
  ADD COLUMN IF NOT EXISTS agent_card_url TEXT,
  ADD COLUMN IF NOT EXISTS mcp_endpoint_url TEXT,
  ADD COLUMN IF NOT EXISTS capabilities TEXT[],
  ADD COLUMN IF NOT EXISTS a2a_protocol_version VARCHAR(10);

ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS target_executor_type VARCHAR(10) DEFAULT 'any'
  CHECK (target_executor_type IN ('human', 'agent', 'any'));

ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS verification_mode VARCHAR(20) DEFAULT 'manual'
  CHECK (verification_mode IN ('manual', 'auto', 'oracle'));

ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS verification_criteria JSONB;

ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS required_capabilities TEXT[];

DO $$ BEGIN ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'data_processing'; EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'api_integration'; EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'content_generation'; EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'code_execution'; EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'research'; EXCEPTION WHEN OTHERS THEN NULL; END $$;
DO $$ BEGIN ALTER TYPE task_category ADD VALUE IF NOT EXISTS 'multi_step_workflow'; EXCEPTION WHEN OTHERS THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_tasks_target_executor ON tasks(target_executor_type) WHERE status = 'published';
CREATE INDEX IF NOT EXISTS idx_executors_type ON executors(executor_type);
CREATE INDEX IF NOT EXISTS idx_executors_capabilities ON executors USING GIN(capabilities) WHERE executor_type = 'agent';
CREATE INDEX IF NOT EXISTS idx_tasks_required_capabilities ON tasks USING GIN(required_capabilities) WHERE target_executor_type IN ('agent', 'any');

ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS key_type VARCHAR(20) DEFAULT 'publisher' CHECK (key_type IN ('publisher', 'executor', 'admin'));
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS executor_id UUID REFERENCES executors(id);
