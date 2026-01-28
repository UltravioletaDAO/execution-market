-- ============================================================================
-- CHAMBA: Human Execution Layer for AI Agents
-- Migration: 001_initial_schema.sql
-- Description: Core database schema - tables, enums, indexes, RLS policies
-- Version: 2.0.0
-- Date: 2026-01-25
-- ============================================================================

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";  -- For geospatial queries
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- ============================================================================
-- ENUMS
-- ============================================================================

-- Task categories (from SPEC.md)
CREATE TYPE task_category AS ENUM (
    'physical_presence',    -- Requires being at a location
    'knowledge_access',     -- Accessing non-digital knowledge
    'human_authority',      -- Legal/professional authority required
    'simple_action',        -- Basic physical tasks
    'digital_physical'      -- Bridging digital and physical
);

-- Task lifecycle states (from SPEC.md)
CREATE TYPE task_status AS ENUM (
    'draft',          -- Being created, not yet visible
    'published',      -- Visible and open for applications
    'accepted',       -- Assigned to an executor
    'in_progress',    -- Executor is working on it
    'submitted',      -- Evidence submitted, awaiting verification
    'verifying',      -- Under verification
    'completed',      -- Successfully completed and paid
    'disputed',       -- Under dispute
    'expired',        -- Deadline passed without completion
    'cancelled',      -- Cancelled by agent
    'refunded'        -- Funds returned to agent
);

-- Evidence types
CREATE TYPE evidence_type AS ENUM (
    'photo',              -- Standard photo
    'photo_geo',          -- Photo with GPS metadata
    'video',              -- Video recording
    'document',           -- PDF or scanned document
    'receipt',            -- Transaction receipt
    'signature',          -- Digital or physical signature
    'notarized',          -- Notarized document
    'timestamp_proof',    -- ChainWitness timestamp proof
    'text_response',      -- Written response
    'measurement',        -- Measurement data
    'screenshot',         -- Screen capture
    'audio'               -- Audio recording
);

-- Executor status
CREATE TYPE executor_status AS ENUM (
    'pending_verification',  -- Just signed up
    'active',                -- Can take tasks
    'suspended',             -- Temporarily blocked
    'banned'                 -- Permanently blocked
);

-- Executor tier (based on reputation + tasks completed)
CREATE TYPE executor_tier AS ENUM (
    'probation',    -- < 10 tasks
    'standard',     -- 10-49 tasks, rep >= 60
    'verified',     -- 50-99 tasks, rep >= 75
    'expert',       -- 100-199 tasks, rep >= 85
    'master'        -- 200+ tasks, rep >= 90
);

-- Application status
CREATE TYPE application_status AS ENUM (
    'pending',
    'accepted',
    'rejected',
    'withdrawn',
    'expired'
);

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- ---------------------------------------------------------------------------
-- EXECUTORS (Humans who execute tasks)
-- ---------------------------------------------------------------------------
CREATE TABLE executors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,

    -- Identity
    wallet_address VARCHAR(42) NOT NULL,
    display_name VARCHAR(100),
    bio TEXT,
    avatar_url TEXT,
    email VARCHAR(255),
    phone VARCHAR(50),

    -- Skills & Roles
    roles TEXT[] DEFAULT '{}',
    skills TEXT[] DEFAULT '{}',
    languages TEXT[] DEFAULT ARRAY['es'],

    -- Location (optional, for nearby task matching)
    default_location GEOGRAPHY(POINT, 4326),
    location_city VARCHAR(100),
    location_country VARCHAR(100),
    timezone VARCHAR(50) DEFAULT 'America/Mexico_City',

    -- Status
    status executor_status DEFAULT 'active',
    tier executor_tier DEFAULT 'probation',
    is_verified BOOLEAN DEFAULT FALSE,
    kyc_completed_at TIMESTAMPTZ,

    -- Reputation (calculated from ratings)
    reputation_score INTEGER DEFAULT 50 CHECK (reputation_score >= 0 AND reputation_score <= 100),

    -- Task statistics
    tasks_completed INTEGER DEFAULT 0,
    tasks_disputed INTEGER DEFAULT 0,
    tasks_abandoned INTEGER DEFAULT 0,

    -- Computed average rating (updated by trigger)
    avg_rating DECIMAL(3, 2) CHECK (avg_rating >= 0 AND avg_rating <= 5),

    -- Financial
    balance_usdc DECIMAL(18, 6) DEFAULT 0,
    total_earned_usdc DECIMAL(18, 6) DEFAULT 0,
    total_withdrawn_usdc DECIMAL(18, 6) DEFAULT 0,

    -- On-chain identity (future)
    erc8004_agent_id VARCHAR(255),
    reputation_contract VARCHAR(42),
    reputation_token_id INTEGER,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT executors_wallet_format CHECK (wallet_address ~* '^0x[a-f0-9]{40}$'),
    CONSTRAINT executors_wallet_unique UNIQUE (wallet_address)
);

-- Indexes for executors
CREATE INDEX idx_executors_wallet ON executors(LOWER(wallet_address));
CREATE INDEX idx_executors_user_id ON executors(user_id);
CREATE INDEX idx_executors_reputation ON executors(reputation_score DESC);
CREATE INDEX idx_executors_status ON executors(status) WHERE status = 'active';
CREATE INDEX idx_executors_tier ON executors(tier);
CREATE INDEX idx_executors_location ON executors USING GIST(default_location);
CREATE INDEX idx_executors_skills ON executors USING GIN(skills);
CREATE INDEX idx_executors_languages ON executors USING GIN(languages);
CREATE INDEX idx_executors_last_active ON executors(last_active_at DESC);
CREATE INDEX idx_executors_created ON executors(created_at DESC);

-- ---------------------------------------------------------------------------
-- TASKS (Bounties posted by agents)
-- ---------------------------------------------------------------------------
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Agent who posted
    agent_id VARCHAR(255) NOT NULL,  -- ERC-8004 agent ID or wallet address
    agent_name VARCHAR(255),

    -- Task details
    title VARCHAR(255) NOT NULL,
    instructions TEXT NOT NULL,
    category task_category NOT NULL,
    tags TEXT[] DEFAULT '{}',

    -- Location (optional)
    location GEOGRAPHY(POINT, 4326),
    location_radius_km DECIMAL(5, 2) DEFAULT 5.0,
    location_hint VARCHAR(255),
    location_address TEXT,

    -- Evidence requirements (JSON schema)
    evidence_schema JSONB NOT NULL DEFAULT '{"required": ["photo"], "optional": []}',

    -- Payment
    bounty_usd DECIMAL(10, 2) NOT NULL CHECK (bounty_usd >= 1),
    payment_token VARCHAR(42) DEFAULT '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',  -- USDC on Base
    chain_id INTEGER DEFAULT 8453,  -- Base Mainnet

    -- Escrow
    escrow_id VARCHAR(255),          -- x402 escrow identifier
    escrow_tx VARCHAR(66),           -- On-chain transaction hash
    escrow_amount_usdc DECIMAL(18, 6),
    escrow_created_at TIMESTAMPTZ,

    -- Timing
    deadline TIMESTAMPTZ NOT NULL,
    estimated_duration_minutes INTEGER,

    -- Requirements
    min_reputation INTEGER DEFAULT 0 CHECK (min_reputation >= 0 AND min_reputation <= 100),
    required_roles TEXT[] DEFAULT '{}',
    required_tier executor_tier DEFAULT 'probation',
    max_executors INTEGER DEFAULT 1,
    is_public BOOLEAN DEFAULT TRUE,

    -- Assignment
    status task_status DEFAULT 'draft',
    executor_id UUID REFERENCES executors(id) ON DELETE SET NULL,
    accepted_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    assignment_notes TEXT,

    -- Completion
    completed_at TIMESTAMPTZ,
    chainwitness_proof VARCHAR(255),  -- ChainWitness notarization CID
    completion_notes TEXT,

    -- Metadata
    external_id VARCHAR(255),  -- For agent's internal tracking
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT tasks_deadline_future CHECK (deadline > created_at),
    CONSTRAINT tasks_bounty_positive CHECK (bounty_usd > 0)
);

-- Indexes for tasks
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_category ON tasks(category);
CREATE INDEX idx_tasks_agent ON tasks(agent_id);
CREATE INDEX idx_tasks_executor ON tasks(executor_id);
CREATE INDEX idx_tasks_deadline ON tasks(deadline);
CREATE INDEX idx_tasks_bounty ON tasks(bounty_usd DESC);
CREATE INDEX idx_tasks_location ON tasks USING GIST(location);
CREATE INDEX idx_tasks_created ON tasks(created_at DESC);
CREATE INDEX idx_tasks_published ON tasks(published_at DESC) WHERE published_at IS NOT NULL;
CREATE INDEX idx_tasks_tags ON tasks USING GIN(tags);
CREATE INDEX idx_tasks_escrow ON tasks(escrow_id) WHERE escrow_id IS NOT NULL;

-- Composite indexes for common queries
CREATE INDEX idx_tasks_open_location ON tasks(status, location)
    WHERE status = 'published' AND location IS NOT NULL;
CREATE INDEX idx_tasks_agent_status ON tasks(agent_id, status);
CREATE INDEX idx_tasks_open_category ON tasks(category, bounty_usd DESC)
    WHERE status = 'published';
CREATE INDEX idx_tasks_open_deadline ON tasks(deadline)
    WHERE status IN ('published', 'accepted', 'in_progress');

-- ---------------------------------------------------------------------------
-- TASK APPLICATIONS (Workers applying for tasks)
-- ---------------------------------------------------------------------------
CREATE TABLE task_applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    executor_id UUID NOT NULL REFERENCES executors(id) ON DELETE CASCADE,

    -- Application content
    message TEXT,
    proposed_price DECIMAL(10, 2),
    proposed_deadline TIMESTAMPTZ,

    -- Status
    status application_status DEFAULT 'pending',
    rejection_reason TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    responded_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT task_applications_unique UNIQUE(task_id, executor_id)
);

-- Indexes for applications
CREATE INDEX idx_applications_task ON task_applications(task_id);
CREATE INDEX idx_applications_executor ON task_applications(executor_id);
CREATE INDEX idx_applications_status ON task_applications(status);
CREATE INDEX idx_applications_pending ON task_applications(task_id, status)
    WHERE status = 'pending';
CREATE INDEX idx_applications_executor_pending ON task_applications(executor_id, status)
    WHERE status = 'pending';

-- ---------------------------------------------------------------------------
-- SUBMISSIONS (Evidence submissions from executors)
-- ---------------------------------------------------------------------------
CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    executor_id UUID NOT NULL REFERENCES executors(id) ON DELETE CASCADE,

    -- Evidence data
    evidence JSONB NOT NULL,           -- Structured evidence matching schema
    evidence_files TEXT[] DEFAULT '{}', -- Storage paths
    evidence_ipfs_cid VARCHAR(255),    -- IPFS CID for permanent storage
    evidence_hash VARCHAR(66),          -- SHA256 for verification
    chainwitness_proof VARCHAR(255),   -- ChainWitness proof CID

    -- Notes
    notes TEXT,                         -- Executor's notes

    -- Auto-verification
    auto_check_passed BOOLEAN,
    auto_check_score DECIMAL(3, 2),
    auto_check_details JSONB,

    -- Agent verification
    agent_verdict VARCHAR(50),          -- 'accepted', 'rejected', 'more_info_requested'
    agent_notes TEXT,

    -- Payment
    payment_amount DECIMAL(10, 2),
    payment_tx VARCHAR(66),
    paid_at TIMESTAMPTZ,

    -- Timestamps
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    verified_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT submissions_task_executor_unique UNIQUE(task_id, executor_id)
);

-- Indexes for submissions
CREATE INDEX idx_submissions_task ON submissions(task_id);
CREATE INDEX idx_submissions_executor ON submissions(executor_id);
CREATE INDEX idx_submissions_verdict ON submissions(agent_verdict);
CREATE INDEX idx_submissions_submitted ON submissions(submitted_at DESC);
CREATE INDEX idx_submissions_pending ON submissions(agent_verdict)
    WHERE agent_verdict IS NULL OR agent_verdict = 'pending';
CREATE INDEX idx_submissions_executor_recent ON submissions(executor_id, submitted_at DESC);

-- ---------------------------------------------------------------------------
-- USER_WALLETS (Multi-wallet support per user)
-- ---------------------------------------------------------------------------
CREATE TABLE user_wallets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    wallet_address VARCHAR(42) NOT NULL,

    -- Wallet info
    is_primary BOOLEAN DEFAULT FALSE,
    chain_id INTEGER DEFAULT 1,
    label VARCHAR(100),

    -- Verification
    verified_at TIMESTAMPTZ,
    signature_hash VARCHAR(66),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT user_wallets_unique UNIQUE(user_id, wallet_address),
    CONSTRAINT user_wallets_format CHECK (wallet_address ~* '^0x[a-f0-9]{40}$')
);

-- Indexes for user_wallets
CREATE INDEX idx_user_wallets_user ON user_wallets(user_id);
CREATE INDEX idx_user_wallets_address ON user_wallets(LOWER(wallet_address));
CREATE INDEX idx_user_wallets_primary ON user_wallets(user_id, is_primary)
    WHERE is_primary = TRUE;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER executors_updated_at
    BEFORE UPDATE ON executors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER task_applications_updated_at
    BEFORE UPDATE ON task_applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER user_wallets_updated_at
    BEFORE UPDATE ON user_wallets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Update executor stats on task completion
CREATE OR REPLACE FUNCTION update_executor_stats_on_task()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' AND NEW.executor_id IS NOT NULL THEN
        UPDATE executors
        SET
            tasks_completed = tasks_completed + 1,
            last_active_at = NOW()
        WHERE id = NEW.executor_id;
    END IF;

    IF NEW.status = 'disputed' AND OLD.status != 'disputed' AND NEW.executor_id IS NOT NULL THEN
        UPDATE executors
        SET tasks_disputed = tasks_disputed + 1
        WHERE id = NEW.executor_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tasks_update_executor_stats
    AFTER UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_executor_stats_on_task();

-- Auto-publish task when status changes to published
CREATE OR REPLACE FUNCTION set_published_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'published' AND OLD.status != 'published' THEN
        NEW.published_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tasks_set_published_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION set_published_at();

-- Update executor tier based on tasks completed and reputation
CREATE OR REPLACE FUNCTION update_executor_tier()
RETURNS TRIGGER AS $$
BEGIN
    NEW.tier = CASE
        WHEN NEW.tasks_completed < 10 THEN 'probation'::executor_tier
        WHEN NEW.tasks_completed < 50 AND NEW.reputation_score >= 60 THEN 'standard'::executor_tier
        WHEN NEW.tasks_completed < 100 AND NEW.reputation_score >= 75 THEN 'verified'::executor_tier
        WHEN NEW.tasks_completed < 200 AND NEW.reputation_score >= 85 THEN 'expert'::executor_tier
        WHEN NEW.tasks_completed >= 200 AND NEW.reputation_score >= 90 THEN 'master'::executor_tier
        ELSE 'standard'::executor_tier
    END;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER executors_update_tier
    BEFORE UPDATE OF tasks_completed, reputation_score ON executors
    FOR EACH ROW EXECUTE FUNCTION update_executor_tier();

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE executors ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_wallets ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- EXECUTORS RLS
-- ---------------------------------------------------------------------------

-- Anyone can view active executor profiles
CREATE POLICY "executors_select_public" ON executors
    FOR SELECT
    USING (status IN ('active', 'pending_verification'));

-- Users can update their own executor profile
CREATE POLICY "executors_update_own" ON executors
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Authenticated users can create executor profiles
CREATE POLICY "executors_insert_authenticated" ON executors
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id OR user_id IS NULL);

-- Service role has full access
CREATE POLICY "executors_service_role" ON executors
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- TASKS RLS
-- ---------------------------------------------------------------------------

-- Anyone can view non-cancelled, non-draft tasks
CREATE POLICY "tasks_select_public" ON tasks
    FOR SELECT
    USING (status NOT IN ('draft', 'cancelled'));

-- Agents can view their own draft tasks
CREATE POLICY "tasks_select_own_drafts" ON tasks
    FOR SELECT
    USING (
        status = 'draft'
        AND agent_id = (SELECT wallet_address FROM executors WHERE user_id = auth.uid())
    );

-- Agents can insert tasks (API validates agent_id)
CREATE POLICY "tasks_insert_authenticated" ON tasks
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Agents can update their own tasks
CREATE POLICY "tasks_update_own" ON tasks
    FOR UPDATE
    USING (true)  -- API validates agent_id ownership
    WITH CHECK (true);

-- Service role has full access
CREATE POLICY "tasks_service_role" ON tasks
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- TASK APPLICATIONS RLS
-- ---------------------------------------------------------------------------

-- Executors can view their own applications
CREATE POLICY "applications_select_own" ON task_applications
    FOR SELECT
    USING (executor_id IN (SELECT id FROM executors WHERE user_id = auth.uid()));

-- Task agents can view applications for their tasks
CREATE POLICY "applications_select_task_owner" ON task_applications
    FOR SELECT
    USING (true);  -- API validates task ownership

-- Executors can create applications
CREATE POLICY "applications_insert_own" ON task_applications
    FOR INSERT
    TO authenticated
    WITH CHECK (executor_id IN (SELECT id FROM executors WHERE user_id = auth.uid()));

-- Executors can withdraw their own applications
CREATE POLICY "applications_update_own" ON task_applications
    FOR UPDATE
    USING (executor_id IN (SELECT id FROM executors WHERE user_id = auth.uid()));

-- Service role has full access
CREATE POLICY "applications_service_role" ON task_applications
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- SUBMISSIONS RLS
-- ---------------------------------------------------------------------------

-- Executors can view their own submissions
CREATE POLICY "submissions_select_own" ON submissions
    FOR SELECT
    USING (executor_id IN (SELECT id FROM executors WHERE user_id = auth.uid()));

-- Task agents can view submissions for their tasks
CREATE POLICY "submissions_select_task_owner" ON submissions
    FOR SELECT
    USING (true);  -- API validates task ownership

-- Executors can create submissions for their assigned tasks
CREATE POLICY "submissions_insert_own" ON submissions
    FOR INSERT
    TO authenticated
    WITH CHECK (executor_id IN (SELECT id FROM executors WHERE user_id = auth.uid()));

-- Executors can update their own submissions
CREATE POLICY "submissions_update_own" ON submissions
    FOR UPDATE
    USING (executor_id IN (SELECT id FROM executors WHERE user_id = auth.uid()));

-- Service role has full access
CREATE POLICY "submissions_service_role" ON submissions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- USER WALLETS RLS
-- ---------------------------------------------------------------------------

-- Users can view their own wallets
CREATE POLICY "user_wallets_select_own" ON user_wallets
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own wallets
CREATE POLICY "user_wallets_insert_own" ON user_wallets
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own wallets
CREATE POLICY "user_wallets_update_own" ON user_wallets
    FOR UPDATE
    USING (auth.uid() = user_id);

-- Users can delete their own wallets
CREATE POLICY "user_wallets_delete_own" ON user_wallets
    FOR DELETE
    USING (auth.uid() = user_id);

-- Service role has full access
CREATE POLICY "user_wallets_service_role" ON user_wallets
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ============================================================================
-- STORAGE BUCKET
-- ============================================================================

-- Create evidence bucket for file uploads
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'chamba-evidence',
    'chamba-evidence',
    false,
    52428800,  -- 50MB max
    ARRAY[
        'image/jpeg',
        'image/png',
        'image/webp',
        'image/heic',
        'video/mp4',
        'video/quicktime',
        'video/webm',
        'application/pdf',
        'application/json',
        'audio/mpeg',
        'audio/wav',
        'audio/ogg'
    ]
) ON CONFLICT (id) DO UPDATE SET
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Storage policies
CREATE POLICY "evidence_upload_authenticated" ON storage.objects
    FOR INSERT
    TO authenticated
    WITH CHECK (bucket_id = 'chamba-evidence');

CREATE POLICY "evidence_select_authenticated" ON storage.objects
    FOR SELECT
    TO authenticated
    USING (bucket_id = 'chamba-evidence');

CREATE POLICY "evidence_delete_own" ON storage.objects
    FOR DELETE
    TO authenticated
    USING (bucket_id = 'chamba-evidence');

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE executors IS 'Human workers who execute tasks for AI agents';
COMMENT ON TABLE tasks IS 'Bounties posted by AI agents for human execution';
COMMENT ON TABLE task_applications IS 'Applications from workers to execute tasks';
COMMENT ON TABLE submissions IS 'Evidence submissions for completed tasks';
COMMENT ON TABLE user_wallets IS 'Links multiple wallet addresses to user accounts';

COMMENT ON COLUMN executors.reputation_score IS 'Bayesian average reputation (0-100)';
COMMENT ON COLUMN executors.tier IS 'Calculated tier based on tasks_completed and reputation';
COMMENT ON COLUMN tasks.evidence_schema IS 'JSON schema defining required/optional evidence';
COMMENT ON COLUMN tasks.escrow_id IS 'x402 escrow identifier for payment';
COMMENT ON COLUMN submissions.chainwitness_proof IS 'ChainWitness proof CID for evidence notarization';
