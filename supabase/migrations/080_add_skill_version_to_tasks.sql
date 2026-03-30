-- Migration 080: Add skill_version to tasks table
-- Tracks which version of skill.md the agent used to create the task

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS skill_version VARCHAR(20);

CREATE INDEX idx_tasks_skill_version ON tasks(skill_version) WHERE skill_version IS NOT NULL;
