-- Execution Market MCP Server: Performance Indexes
-- Migration: 20260125000002_indexes.sql
-- Description: Indexes for efficient queries on all tables

-- ============================================
-- EXECUTORS INDEXES
-- ============================================

-- Primary lookup by wallet address
CREATE INDEX IF NOT EXISTS idx_executors_wallet
    ON executors(wallet_address);

-- Reputation leaderboard queries
CREATE INDEX IF NOT EXISTS idx_executors_reputation
    ON executors(reputation_score DESC);

-- Geographic queries for nearby workers
CREATE INDEX IF NOT EXISTS idx_executors_location
    ON executors USING GIST(default_location);

-- User authentication lookup
CREATE INDEX IF NOT EXISTS idx_executors_user_id
    ON executors(user_id)
    WHERE user_id IS NOT NULL;

-- Active workers (recently active)
CREATE INDEX IF NOT EXISTS idx_executors_last_active
    ON executors(last_active_at DESC)
    WHERE last_active_at IS NOT NULL;

-- Email lookup (for notifications)
CREATE INDEX IF NOT EXISTS idx_executors_email
    ON executors(email)
    WHERE email IS NOT NULL;

-- KYC verified workers
CREATE INDEX IF NOT EXISTS idx_executors_kyc_verified
    ON executors(kyc_verified)
    WHERE kyc_verified = TRUE;

-- ============================================
-- AGENTS INDEXES
-- ============================================

-- Primary lookup by wallet address
CREATE INDEX IF NOT EXISTS idx_agents_wallet
    ON agents(wallet_address);

-- API key lookup (for authentication)
CREATE INDEX IF NOT EXISTS idx_agents_api_key_hash
    ON agents(api_key_hash)
    WHERE api_key_hash IS NOT NULL;

-- Tier filtering
CREATE INDEX IF NOT EXISTS idx_agents_tier
    ON agents(tier);

-- Verified agents
CREATE INDEX IF NOT EXISTS idx_agents_verified
    ON agents(verified)
    WHERE verified = TRUE;

-- ============================================
-- TASKS INDEXES
-- ============================================

-- Status filtering (most common query)
CREATE INDEX IF NOT EXISTS idx_tasks_status
    ON tasks(status);

-- Geographic queries for tasks near location
CREATE INDEX IF NOT EXISTS idx_tasks_location
    ON tasks USING GIST(location)
    WHERE location IS NOT NULL;

-- Combined status + location for "find tasks near me"
CREATE INDEX IF NOT EXISTS idx_tasks_status_location
    ON tasks USING GIST(location)
    WHERE status = 'published' AND location IS NOT NULL;

-- Agent dashboard queries
CREATE INDEX IF NOT EXISTS idx_tasks_agent_id
    ON tasks(agent_id);

-- Agent + status for filtered dashboard
CREATE INDEX IF NOT EXISTS idx_tasks_agent_status
    ON tasks(agent_id, status);

-- Category filtering
CREATE INDEX IF NOT EXISTS idx_tasks_category
    ON tasks(category);

-- Deadline filtering (expiring soon)
CREATE INDEX IF NOT EXISTS idx_tasks_deadline
    ON tasks(deadline)
    WHERE status IN ('published', 'accepted', 'in_progress');

-- Bounty filtering (high value first)
CREATE INDEX IF NOT EXISTS idx_tasks_bounty
    ON tasks(bounty_usd DESC)
    WHERE status = 'published';

-- Recent tasks
CREATE INDEX IF NOT EXISTS idx_tasks_created_at
    ON tasks(created_at DESC);

-- Published tasks (for public listing)
CREATE INDEX IF NOT EXISTS idx_tasks_published_at
    ON tasks(published_at DESC)
    WHERE status = 'published';

-- Executor's assigned tasks
CREATE INDEX IF NOT EXISTS idx_tasks_executor_id
    ON tasks(executor_id)
    WHERE executor_id IS NOT NULL;

-- Minimum reputation filtering
CREATE INDEX IF NOT EXISTS idx_tasks_min_reputation
    ON tasks(min_reputation)
    WHERE status = 'published';

-- Tag-based search (GIN for array containment)
CREATE INDEX IF NOT EXISTS idx_tasks_tags
    ON tasks USING GIN(tags);

-- Combined index for common task search pattern
-- Status = published, sorted by bounty, filtered by category
CREATE INDEX IF NOT EXISTS idx_tasks_search_published
    ON tasks(category, bounty_usd DESC, created_at DESC)
    WHERE status = 'published';

-- ============================================
-- APPLICATIONS INDEXES
-- ============================================

-- Worker's applications dashboard
CREATE INDEX IF NOT EXISTS idx_applications_executor_id
    ON applications(executor_id);

-- Task's applications list
CREATE INDEX IF NOT EXISTS idx_applications_task_id
    ON applications(task_id);

-- Status filtering
CREATE INDEX IF NOT EXISTS idx_applications_status
    ON applications(status);

-- Pending applications for review
CREATE INDEX IF NOT EXISTS idx_applications_pending
    ON applications(task_id, created_at ASC)
    WHERE status = 'pending';

-- Recent applications
CREATE INDEX IF NOT EXISTS idx_applications_created_at
    ON applications(created_at DESC);

-- ============================================
-- SUBMISSIONS INDEXES
-- ============================================

-- Task's submissions (for review)
CREATE INDEX IF NOT EXISTS idx_submissions_task_id
    ON submissions(task_id);

-- Worker's submissions history
CREATE INDEX IF NOT EXISTS idx_submissions_executor_id
    ON submissions(executor_id);

-- Status filtering
CREATE INDEX IF NOT EXISTS idx_submissions_status
    ON submissions(status);

-- Pending submissions for review
CREATE INDEX IF NOT EXISTS idx_submissions_pending
    ON submissions(task_id, submitted_at ASC)
    WHERE status = 'pending';

-- Recent submissions
CREATE INDEX IF NOT EXISTS idx_submissions_submitted_at
    ON submissions(submitted_at DESC);

-- Paid submissions
CREATE INDEX IF NOT EXISTS idx_submissions_paid
    ON submissions(paid_at DESC)
    WHERE paid_at IS NOT NULL;

-- ============================================
-- ESCROWS INDEXES
-- ============================================

-- Task lookup
CREATE INDEX IF NOT EXISTS idx_escrows_task_id
    ON escrows(task_id);

-- Status filtering
CREATE INDEX IF NOT EXISTS idx_escrows_status
    ON escrows(status);

-- Expiring escrows (for timeout processing)
CREATE INDEX IF NOT EXISTS idx_escrows_expires_at
    ON escrows(expires_at)
    WHERE status IN ('active', 'partial_released') AND expires_at IS NOT NULL;

-- Recent escrows
CREATE INDEX IF NOT EXISTS idx_escrows_created_at
    ON escrows(created_at DESC);

-- ============================================
-- COMPOSITE INDEXES FOR COMMON PATTERNS
-- ============================================

-- Find available tasks for a worker (published, meets reputation, near location)
-- Note: PostGIS distance queries use GIST index, combined with btree indexes above

-- Agent analytics: completed tasks in date range
CREATE INDEX IF NOT EXISTS idx_tasks_agent_completed
    ON tasks(agent_id, completed_at DESC)
    WHERE status = 'completed';

-- Worker analytics: completed tasks in date range
CREATE INDEX IF NOT EXISTS idx_tasks_executor_completed
    ON tasks(executor_id, completed_at DESC)
    WHERE status = 'completed' AND executor_id IS NOT NULL;

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON INDEX idx_tasks_status_location IS 'Optimizes "find published tasks near me" queries';
COMMENT ON INDEX idx_tasks_search_published IS 'Optimizes common task search pattern';
COMMENT ON INDEX idx_escrows_expires_at IS 'Enables efficient timeout processing job';
COMMENT ON INDEX idx_executors_location IS 'PostGIS spatial index for geographic matching';
