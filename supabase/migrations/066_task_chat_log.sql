-- Migration 066: Task Chat Log
-- Persists IRC task channel messages as evidence for disputes.
-- Only stores messages from #task-{id} channels (NOT #bounties, NOT DMs).

CREATE TABLE IF NOT EXISTS task_chat_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(64) NOT NULL,
    channel VARCHAR(100) NOT NULL,
    nick VARCHAR(64) NOT NULL,
    wallet_address VARCHAR(42),
    message TEXT NOT NULL,
    message_type VARCHAR(20) NOT NULL DEFAULT 'text'
        CHECK (message_type IN ('text', 'command', 'system', 'bot')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_task_chat_log_task ON task_chat_log(task_id);
CREATE INDEX idx_task_chat_log_task_time ON task_chat_log(task_id, created_at);

-- RLS: service_role full access, admin read
ALTER TABLE task_chat_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY task_chat_log_service_all ON task_chat_log
    FOR ALL TO service_role USING (true) WITH CHECK (true);
