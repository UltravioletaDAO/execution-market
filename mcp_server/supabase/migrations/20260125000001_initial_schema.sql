-- Execution Market MCP Server: Initial Database Schema
-- Migration: 20260125000001_initial_schema.sql
-- Description: Core tables for executors, agents, tasks, applications, submissions, and escrows

-- ============================================
-- EXTENSIONS
-- ============================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- ============================================
-- ENUMS
-- ============================================

-- Task categories (what humans can do that AI cannot)
CREATE TYPE task_category AS ENUM (
    'physical_presence',   -- Be physically somewhere
    'knowledge_access',    -- Access paywalled/restricted info
    'human_authority',     -- Sign, vote, authorize
    'simple_action',       -- Buy, deliver, verify
    'digital_physical'     -- Bridge digital and physical worlds
);

-- Task lifecycle states
CREATE TYPE task_status AS ENUM (
    'draft',               -- Not yet published
    'published',           -- Open for applications
    'accepted',            -- Executor assigned
    'in_progress',         -- Work underway
    'submitted',           -- Evidence submitted
    'verifying',           -- Under review
    'completed',           -- Approved and paid
    'disputed',            -- In dispute resolution
    'expired',             -- Deadline passed
    'cancelled'            -- Cancelled by agent
);

-- Evidence types for verification
CREATE TYPE evidence_type AS ENUM (
    'photo',               -- Standard photo
    'photo_geo',           -- Geotagged photo
    'video',               -- Video evidence
    'document',            -- PDF or document scan
    'receipt',             -- Purchase receipt
    'signature',           -- Digital signature
    'notarized',           -- Notarized document
    'timestamp_proof',     -- Cryptographic timestamp
    'text_response',       -- Written response
    'measurement',         -- Measurement data
    'screenshot'           -- Screen capture
);

-- Application status
CREATE TYPE application_status AS ENUM (
    'pending',             -- Awaiting review
    'accepted',            -- Accepted by agent
    'rejected',            -- Rejected by agent
    'withdrawn'            -- Withdrawn by executor
);

-- Submission status
CREATE TYPE submission_status AS ENUM (
    'pending',             -- Awaiting review
    'approved',            -- Approved by agent
    'rejected',            -- Rejected by agent
    'more_info',           -- More info requested
    'disputed'             -- Under dispute
);

-- Escrow status
CREATE TYPE escrow_status AS ENUM (
    'pending',             -- Awaiting deposit
    'active',              -- Funds deposited
    'partial_released',    -- Partial payment made
    'released',            -- Fully released
    'refunded',            -- Refunded to agent
    'disputed'             -- Frozen for dispute
);

-- Agent tier levels
CREATE TYPE agent_tier AS ENUM (
    'free',                -- Basic tier
    'starter',             -- Starter tier
    'professional',        -- Pro tier
    'enterprise'           -- Enterprise tier
);

-- ============================================
-- TABLES
-- ============================================

-- Executors (humans who complete tasks)
CREATE TABLE executors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Authentication
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    wallet_address VARCHAR(255) NOT NULL UNIQUE,

    -- Contact (optional)
    email VARCHAR(255),
    phone VARCHAR(50),

    -- Profile
    display_name VARCHAR(100),
    bio TEXT,
    avatar_url TEXT,
    roles TEXT[] DEFAULT '{}',

    -- Location
    default_location GEOGRAPHY(POINT, 4326),
    location_city VARCHAR(100),
    location_country VARCHAR(100),

    -- Reputation (0-100 scale)
    reputation_score INTEGER DEFAULT 50 CHECK (reputation_score >= 0 AND reputation_score <= 100),

    -- Statistics
    tasks_completed INTEGER DEFAULT 0 CHECK (tasks_completed >= 0),
    tasks_disputed INTEGER DEFAULT 0 CHECK (tasks_disputed >= 0),
    tasks_abandoned INTEGER DEFAULT 0 CHECK (tasks_abandoned >= 0),
    avg_rating DECIMAL(3, 2) CHECK (avg_rating IS NULL OR (avg_rating >= 0 AND avg_rating <= 5)),

    -- Financials
    balance_usdc DECIMAL(18, 6) DEFAULT 0 CHECK (balance_usdc >= 0),
    total_earned_usdc DECIMAL(18, 6) DEFAULT 0 CHECK (total_earned_usdc >= 0),
    total_withdrawn_usdc DECIMAL(18, 6) DEFAULT 0 CHECK (total_withdrawn_usdc >= 0),

    -- On-chain reputation (future)
    reputation_contract VARCHAR(255),
    reputation_token_id INTEGER,

    -- Verification
    kyc_verified BOOLEAN DEFAULT FALSE,
    kyc_verified_at TIMESTAMPTZ,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT valid_email CHECK (email IS NULL OR email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Agents (AI agents or organizations that create tasks)
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Identity
    wallet_address VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    logo_url TEXT,
    website_url TEXT,

    -- Authentication
    api_key_hash VARCHAR(255),

    -- Tier and limits
    tier agent_tier DEFAULT 'free',
    monthly_task_limit INTEGER DEFAULT 10,
    tasks_created_this_month INTEGER DEFAULT 0,

    -- Statistics
    total_tasks_created INTEGER DEFAULT 0 CHECK (total_tasks_created >= 0),
    total_tasks_completed INTEGER DEFAULT 0 CHECK (total_tasks_completed >= 0),
    total_spent_usdc DECIMAL(18, 6) DEFAULT 0 CHECK (total_spent_usdc >= 0),
    avg_completion_time_hours DECIMAL(10, 2),

    -- Verification
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,

    -- Contact
    contact_email VARCHAR(255),

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tasks (bounties posted by agents)
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Ownership
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,

    -- Details
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    instructions TEXT,
    category task_category NOT NULL,

    -- Payment
    bounty_usd DECIMAL(10, 2) NOT NULL CHECK (bounty_usd > 0),
    payment_token VARCHAR(255) DEFAULT 'USDC',

    -- Location (optional)
    location GEOGRAPHY(POINT, 4326),
    location_radius_km DECIMAL(5, 2) DEFAULT 5.0 CHECK (location_radius_km > 0),
    location_hint VARCHAR(255),
    location_required BOOLEAN DEFAULT FALSE,

    -- Evidence requirements
    evidence_schema JSONB NOT NULL DEFAULT '{"required": ["photo"], "optional": []}',

    -- Timing
    deadline TIMESTAMPTZ NOT NULL,
    estimated_duration_minutes INTEGER DEFAULT 60 CHECK (estimated_duration_minutes > 0),

    -- Requirements
    min_reputation INTEGER DEFAULT 0 CHECK (min_reputation >= 0 AND min_reputation <= 100),
    required_roles TEXT[] DEFAULT '{}',
    max_executors INTEGER DEFAULT 1 CHECK (max_executors >= 1),

    -- Status
    status task_status DEFAULT 'draft',

    -- Assignment
    executor_id UUID REFERENCES executors(id) ON DELETE SET NULL,
    accepted_at TIMESTAMPTZ,

    -- Completion
    completed_at TIMESTAMPTZ,
    chainwitness_proof VARCHAR(255),

    -- Escrow
    escrow_id UUID,
    escrow_tx VARCHAR(255),

    -- Metadata
    tags TEXT[] DEFAULT '{}',
    priority INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT valid_deadline CHECK (deadline > created_at)
);

-- Applications (executors applying for tasks)
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- References
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    executor_id UUID NOT NULL REFERENCES executors(id) ON DELETE CASCADE,

    -- Application details
    message TEXT,
    proposed_rate_usd DECIMAL(10, 2),
    proposed_deadline TIMESTAMPTZ,

    -- Status
    status application_status DEFAULT 'pending',
    rejection_reason TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,

    -- Unique constraint (one application per task per executor)
    UNIQUE(task_id, executor_id)
);

-- Submissions (evidence submitted by executors)
CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- References
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    executor_id UUID NOT NULL REFERENCES executors(id) ON DELETE CASCADE,

    -- Evidence
    evidence JSONB NOT NULL,
    evidence_files TEXT[] DEFAULT '{}',
    evidence_ipfs_cid VARCHAR(255),
    evidence_hash VARCHAR(255),

    -- Verification proof
    chainwitness_proof VARCHAR(255),

    -- Status
    status submission_status DEFAULT 'pending',

    -- Auto-verification
    auto_check_passed BOOLEAN,
    auto_check_details JSONB,

    -- Agent review
    agent_verdict VARCHAR(50),
    agent_notes TEXT,
    agent_rating INTEGER CHECK (agent_rating IS NULL OR (agent_rating >= 1 AND agent_rating <= 5)),

    -- Payment
    payment_tx VARCHAR(255),
    paid_at TIMESTAMPTZ,
    payment_amount DECIMAL(10, 2),

    -- Timestamps
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verified_at TIMESTAMPTZ,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Unique constraint (one submission per task per executor)
    UNIQUE(task_id, executor_id)
);

-- Escrows (payment escrow for tasks)
CREATE TABLE escrows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- References
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,

    -- Amounts
    amount_usd DECIMAL(18, 6) NOT NULL CHECK (amount_usd > 0),
    released_amount_usd DECIMAL(18, 6) DEFAULT 0 CHECK (released_amount_usd >= 0),

    -- Status
    status escrow_status DEFAULT 'pending',

    -- Transactions
    deposit_tx VARCHAR(255),
    release_tx VARCHAR(255),
    refund_tx VARCHAR(255),

    -- Timing
    timeout_hours INTEGER DEFAULT 48 CHECK (timeout_hours > 0),
    expires_at TIMESTAMPTZ,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deposited_at TIMESTAMPTZ,
    released_at TIMESTAMPTZ,
    refunded_at TIMESTAMPTZ,

    -- Unique constraint (one escrow per task)
    UNIQUE(task_id)
);

-- ============================================
-- AUTO-UPDATE TRIGGERS
-- ============================================

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to all tables with updated_at
CREATE TRIGGER executors_updated_at
    BEFORE UPDATE ON executors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON TABLE executors IS 'Human workers who complete tasks in the Execution Market network';
COMMENT ON TABLE agents IS 'AI agents or organizations that create and fund tasks';
COMMENT ON TABLE tasks IS 'Bounties posted by agents for human execution';
COMMENT ON TABLE applications IS 'Worker applications to tasks';
COMMENT ON TABLE submissions IS 'Evidence submissions for task completion';
COMMENT ON TABLE escrows IS 'Payment escrows for task bounties';

COMMENT ON COLUMN executors.reputation_score IS 'Bayesian reputation score (0-100)';
COMMENT ON COLUMN tasks.evidence_schema IS 'JSON schema defining required/optional evidence types';
COMMENT ON COLUMN tasks.chainwitness_proof IS 'ChainWitness verification proof hash';
