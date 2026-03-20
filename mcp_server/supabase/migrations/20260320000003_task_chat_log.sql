-- ============================================================================
-- Migration 012: Task Chat Log — persistence for IRC task chat relay
-- ============================================================================
-- Stores all messages from task chat channels (IRC relay, mobile WS, XMTP
-- bridge, system events). Used by:
-- - relay.py: _load_history() on WS connect, _persist_message() on each msg
-- - event_injector.py: system messages for lifecycle events
-- ============================================================================

CREATE TABLE IF NOT EXISTS task_chat_log (
    id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    task_id     text NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    nick        text NOT NULL,
    text        text NOT NULL,
    source      text NOT NULL DEFAULT 'irc',      -- irc | mobile | xmtp | system | agent
    type        text NOT NULL DEFAULT 'message',   -- message | system | error
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- Query pattern: load recent history for a task channel
CREATE INDEX idx_task_chat_log_task_created
    ON task_chat_log (task_id, created_at DESC);

-- Query pattern: retention cleanup (delete old messages)
CREATE INDEX idx_task_chat_log_created
    ON task_chat_log (created_at);

-- RLS: participants only (executor assigned to task, or task publisher)
ALTER TABLE task_chat_log ENABLE ROW LEVEL SECURITY;

-- Workers can read chat for tasks they're assigned to
CREATE POLICY "Workers read own task chat"
ON task_chat_log FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM tasks t
        JOIN executors e ON e.id = t.executor_id
        WHERE t.id = task_chat_log.task_id
          AND e.user_id = auth.uid()
    )
);

-- Workers can insert messages for tasks they're assigned to
CREATE POLICY "Workers write own task chat"
ON task_chat_log FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM tasks t
        JOIN executors e ON e.id = t.executor_id
        WHERE t.id = task_chat_log.task_id
          AND e.user_id = auth.uid()
    )
);

-- Service role (MCP server) has full access via service_role key
-- No explicit policy needed — service_role bypasses RLS

COMMENT ON TABLE task_chat_log IS 'Chat messages from IRC task channels. Populated by the WebSocket relay and event injector.';
COMMENT ON COLUMN task_chat_log.source IS 'Origin transport: irc (desktop/CLI), mobile (WS relay), xmtp (bridge), system (lifecycle events), agent (AI agent)';
COMMENT ON COLUMN task_chat_log.type IS 'Message classification: message (user text), system (lifecycle event), error (delivery failure)';
