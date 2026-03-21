-- 041: Broader GIN index on required_capabilities for skill-based filtering
-- The existing idx_tasks_required_capabilities only covers agent/any tasks.
-- This index covers ALL published tasks for the /tasks/available?skills= filter.

CREATE INDEX IF NOT EXISTS idx_tasks_required_capabilities_all
ON tasks USING GIN (required_capabilities)
WHERE status = 'published' AND required_capabilities IS NOT NULL;
