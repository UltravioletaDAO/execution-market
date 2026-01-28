-- ============================================================================
-- CHAMBA: Human Execution Layer for AI Agents
-- Migration: 004_disputes.sql
-- Description: Dispute resolution system with arbitration
-- Version: 2.0.0
-- Date: 2026-01-25
-- ============================================================================

-- ============================================================================
-- ENUMS
-- ============================================================================

-- Dispute status
CREATE TYPE dispute_status AS ENUM (
    'open',                 -- Just created
    'under_review',         -- Being reviewed
    'awaiting_response',    -- Waiting for other party
    'in_arbitration',       -- Escalated to arbitration
    'resolved_for_agent',   -- Agent won
    'resolved_for_executor',-- Executor won
    'settled',              -- Mutual settlement
    'closed',               -- Closed without resolution
    'expired'               -- Timed out
);

-- Dispute reason category
CREATE TYPE dispute_reason AS ENUM (
    'incomplete_work',      -- Work not fully completed
    'poor_quality',         -- Quality below expectations
    'wrong_deliverable',    -- Delivered wrong thing
    'late_delivery',        -- Missed deadline
    'fake_evidence',        -- Evidence appears fraudulent
    'no_response',          -- No response from executor
    'payment_issue',        -- Payment-related dispute
    'unfair_rejection',     -- Executor disputes rejection
    'other'                 -- Other reason
);

-- Arbitration vote
CREATE TYPE arbitration_vote AS ENUM (
    'agent',                -- Vote for agent
    'executor',             -- Vote for executor
    'split',                -- Split decision
    'abstain'               -- No vote
);

-- ============================================================================
-- TABLES
-- ============================================================================

-- ---------------------------------------------------------------------------
-- DISPUTES (Main dispute records)
-- ---------------------------------------------------------------------------
CREATE TABLE disputes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- References
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    submission_id UUID REFERENCES submissions(id) ON DELETE SET NULL,
    escrow_id UUID REFERENCES escrows(id) ON DELETE SET NULL,

    -- Parties
    agent_id VARCHAR(255) NOT NULL,
    executor_id UUID REFERENCES executors(id) ON DELETE SET NULL,

    -- Dispute details
    reason dispute_reason NOT NULL,
    reason_other TEXT,  -- If reason is 'other'
    description TEXT NOT NULL,
    disputed_amount_usdc DECIMAL(18, 6),

    -- Agent's side
    agent_evidence JSONB DEFAULT '{}',
    agent_files TEXT[] DEFAULT '{}',

    -- Executor's side
    executor_response TEXT,
    executor_evidence JSONB DEFAULT '{}',
    executor_files TEXT[] DEFAULT '{}',

    -- Status
    status dispute_status DEFAULT 'open',
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),

    -- Resolution
    resolution_type VARCHAR(50),  -- 'auto', 'manual', 'arbitration', 'settlement'
    resolution_notes TEXT,
    winner VARCHAR(50),  -- 'agent', 'executor', 'split'
    agent_refund_usdc DECIMAL(18, 6) DEFAULT 0,
    executor_payout_usdc DECIMAL(18, 6) DEFAULT 0,

    -- Arbitration
    requires_arbitration BOOLEAN DEFAULT FALSE,
    arbitration_started_at TIMESTAMPTZ,
    arbitration_deadline TIMESTAMPTZ,

    -- Handled by
    assigned_to VARCHAR(255),  -- Admin or arbitrator
    resolved_by VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    response_deadline TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,

    -- Metadata
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX idx_disputes_task ON disputes(task_id);
CREATE INDEX idx_disputes_submission ON disputes(submission_id) WHERE submission_id IS NOT NULL;
CREATE INDEX idx_disputes_agent ON disputes(agent_id);
CREATE INDEX idx_disputes_executor ON disputes(executor_id);
CREATE INDEX idx_disputes_status ON disputes(status);
CREATE INDEX idx_disputes_created ON disputes(created_at DESC);
CREATE INDEX idx_disputes_open ON disputes(status, priority DESC)
    WHERE status IN ('open', 'under_review', 'awaiting_response', 'in_arbitration');

-- ---------------------------------------------------------------------------
-- DISPUTE_MESSAGES (Communication thread)
-- ---------------------------------------------------------------------------
CREATE TABLE dispute_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Reference
    dispute_id UUID NOT NULL REFERENCES disputes(id) ON DELETE CASCADE,

    -- Sender
    sender_type VARCHAR(50) NOT NULL,  -- 'agent', 'executor', 'arbitrator', 'system'
    sender_id VARCHAR(255) NOT NULL,

    -- Content
    message TEXT NOT NULL,
    attachments TEXT[] DEFAULT '{}',
    is_internal BOOLEAN DEFAULT FALSE,  -- Only visible to admins/arbitrators

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    read_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_dispute_messages_dispute ON dispute_messages(dispute_id);
CREATE INDEX idx_dispute_messages_created ON dispute_messages(dispute_id, created_at);

-- ---------------------------------------------------------------------------
-- ARBITRATORS (Registered arbitrators)
-- ---------------------------------------------------------------------------
CREATE TABLE arbitrators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Identity
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    wallet_address VARCHAR(42) NOT NULL,
    display_name VARCHAR(100) NOT NULL,

    -- Qualifications
    is_active BOOLEAN DEFAULT TRUE,
    stake_usdc DECIMAL(18, 6) DEFAULT 0,  -- Staked amount
    specialties task_category[] DEFAULT '{}',

    -- Stats
    disputes_handled INTEGER DEFAULT 0,
    disputes_correct INTEGER DEFAULT 0,  -- Matched final outcome
    accuracy_rate DECIMAL(4, 2) GENERATED ALWAYS AS (
        CASE WHEN disputes_handled > 0
        THEN (disputes_correct::DECIMAL / disputes_handled) * 100
        ELSE 0 END
    ) STORED,

    -- Availability
    max_concurrent_disputes INTEGER DEFAULT 5,
    current_disputes INTEGER DEFAULT 0,
    last_assigned_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT arbitrators_wallet_unique UNIQUE (wallet_address)
);

-- Indexes
CREATE INDEX idx_arbitrators_active ON arbitrators(is_active, current_disputes)
    WHERE is_active = TRUE;
CREATE INDEX idx_arbitrators_specialties ON arbitrators USING GIN(specialties);

-- ---------------------------------------------------------------------------
-- ARBITRATION_VOTES (Individual arbitrator votes)
-- ---------------------------------------------------------------------------
CREATE TABLE arbitration_votes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Reference
    dispute_id UUID NOT NULL REFERENCES disputes(id) ON DELETE CASCADE,
    arbitrator_id UUID NOT NULL REFERENCES arbitrators(id) ON DELETE CASCADE,

    -- Vote
    vote arbitration_vote NOT NULL,
    confidence INTEGER CHECK (confidence >= 1 AND confidence <= 10),
    reasoning TEXT NOT NULL,
    suggested_split DECIMAL(4, 2),  -- Agent's percentage if split (0-100)

    -- Quality tracking
    was_majority BOOLEAN,  -- Did this match the final outcome?
    reward_earned DECIMAL(18, 6),
    penalty_applied DECIMAL(18, 6),

    -- Timestamps
    voted_at TIMESTAMPTZ DEFAULT NOW(),
    deadline TIMESTAMPTZ,

    -- One vote per arbitrator per dispute
    CONSTRAINT arbitration_votes_unique UNIQUE (dispute_id, arbitrator_id)
);

-- Indexes
CREATE INDEX idx_votes_dispute ON arbitration_votes(dispute_id);
CREATE INDEX idx_votes_arbitrator ON arbitration_votes(arbitrator_id);

-- ---------------------------------------------------------------------------
-- DISPUTE_TIMELINE (Full audit trail)
-- ---------------------------------------------------------------------------
CREATE TABLE dispute_timeline (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Reference
    dispute_id UUID NOT NULL REFERENCES disputes(id) ON DELETE CASCADE,

    -- Event
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB DEFAULT '{}',
    description TEXT NOT NULL,

    -- Actor
    actor_type VARCHAR(50),  -- 'agent', 'executor', 'arbitrator', 'system', 'admin'
    actor_id VARCHAR(255),

    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_timeline_dispute ON dispute_timeline(dispute_id);
CREATE INDEX idx_timeline_created ON dispute_timeline(dispute_id, created_at);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at
CREATE TRIGGER disputes_updated_at
    BEFORE UPDATE ON disputes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER arbitrators_updated_at
    BEFORE UPDATE ON arbitrators
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Set response deadline on create
CREATE OR REPLACE FUNCTION set_dispute_deadlines()
RETURNS TRIGGER AS $$
BEGIN
    -- 48 hour response deadline
    NEW.response_deadline := NOW() + INTERVAL '48 hours';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER disputes_set_deadlines
    BEFORE INSERT ON disputes
    FOR EACH ROW EXECUTE FUNCTION set_dispute_deadlines();

-- Log status changes to timeline
CREATE OR REPLACE FUNCTION log_dispute_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO dispute_timeline (dispute_id, event_type, description, event_data, actor_type)
        VALUES (
            NEW.id,
            'status_change',
            'Status changed from ' || OLD.status || ' to ' || NEW.status,
            jsonb_build_object('old_status', OLD.status, 'new_status', NEW.status),
            'system'
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER disputes_log_status_change
    AFTER UPDATE OF status ON disputes
    FOR EACH ROW EXECUTE FUNCTION log_dispute_status_change();

-- Update task status on dispute
CREATE OR REPLACE FUNCTION update_task_on_dispute()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE tasks SET status = 'disputed', updated_at = NOW()
        WHERE id = NEW.task_id;
    ELSIF NEW.status IN ('resolved_for_agent', 'resolved_for_executor', 'settled', 'closed') THEN
        -- Determine new task status based on resolution
        IF NEW.winner = 'agent' THEN
            UPDATE tasks SET status = 'refunded', updated_at = NOW()
            WHERE id = NEW.task_id;
        ELSIF NEW.winner = 'executor' THEN
            UPDATE tasks SET status = 'completed', completed_at = NOW(), updated_at = NOW()
            WHERE id = NEW.task_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER disputes_update_task
    AFTER INSERT OR UPDATE OF status ON disputes
    FOR EACH ROW EXECUTE FUNCTION update_task_on_dispute();

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Create a new dispute
CREATE OR REPLACE FUNCTION create_dispute(
    p_task_id UUID,
    p_submission_id UUID,
    p_reason dispute_reason,
    p_description TEXT,
    p_evidence JSONB DEFAULT '{}',
    p_reason_other TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_task tasks%ROWTYPE;
    v_dispute_id UUID;
    v_escrow_id UUID;
BEGIN
    -- Get task
    SELECT * INTO v_task FROM tasks WHERE id = p_task_id;
    IF v_task.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task not found');
    END IF;

    -- Check if already disputed
    IF EXISTS (SELECT 1 FROM disputes WHERE task_id = p_task_id AND status NOT IN ('closed', 'resolved_for_agent', 'resolved_for_executor')) THEN
        RETURN jsonb_build_object('success', false, 'error', 'Active dispute already exists for this task');
    END IF;

    -- Get escrow if exists
    SELECT id INTO v_escrow_id FROM escrows WHERE task_id = p_task_id AND status != 'refunded';

    -- Create dispute
    INSERT INTO disputes (
        task_id, submission_id, escrow_id, agent_id, executor_id,
        reason, reason_other, description, agent_evidence,
        disputed_amount_usdc
    ) VALUES (
        p_task_id, p_submission_id, v_escrow_id, v_task.agent_id, v_task.executor_id,
        p_reason, p_reason_other, p_description, p_evidence,
        v_task.bounty_usd
    )
    RETURNING id INTO v_dispute_id;

    -- Create initial timeline entry
    INSERT INTO dispute_timeline (dispute_id, event_type, description, actor_type, actor_id)
    VALUES (v_dispute_id, 'dispute_created', 'Dispute opened: ' || p_reason, 'agent', v_task.agent_id);

    -- Update escrow to disputed
    IF v_escrow_id IS NOT NULL THEN
        UPDATE escrows SET status = 'disputed' WHERE id = v_escrow_id;
    END IF;

    -- Update executor disputed count
    IF v_task.executor_id IS NOT NULL THEN
        UPDATE executors SET tasks_disputed = tasks_disputed + 1 WHERE id = v_task.executor_id;
    END IF;

    RETURN jsonb_build_object(
        'success', true,
        'dispute_id', v_dispute_id,
        'task_id', p_task_id,
        'response_deadline', NOW() + INTERVAL '48 hours'
    );
END;
$$;

-- Submit executor response to dispute
CREATE OR REPLACE FUNCTION respond_to_dispute(
    p_dispute_id UUID,
    p_executor_id UUID,
    p_response TEXT,
    p_evidence JSONB DEFAULT '{}'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_dispute disputes%ROWTYPE;
BEGIN
    SELECT * INTO v_dispute FROM disputes WHERE id = p_dispute_id FOR UPDATE;

    IF v_dispute.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Dispute not found');
    END IF;

    IF v_dispute.executor_id != p_executor_id THEN
        RETURN jsonb_build_object('success', false, 'error', 'Not authorized');
    END IF;

    IF v_dispute.status NOT IN ('open', 'awaiting_response') THEN
        RETURN jsonb_build_object('success', false, 'error', 'Dispute not accepting responses');
    END IF;

    -- Update dispute
    UPDATE disputes
    SET
        executor_response = p_response,
        executor_evidence = p_evidence,
        status = 'under_review',
        updated_at = NOW()
    WHERE id = p_dispute_id;

    -- Timeline entry
    INSERT INTO dispute_timeline (dispute_id, event_type, description, actor_type, actor_id)
    VALUES (p_dispute_id, 'executor_responded', 'Executor submitted response', 'executor', p_executor_id::TEXT);

    RETURN jsonb_build_object(
        'success', true,
        'dispute_id', p_dispute_id,
        'status', 'under_review'
    );
END;
$$;

-- Escalate to arbitration
CREATE OR REPLACE FUNCTION escalate_to_arbitration(
    p_dispute_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_dispute disputes%ROWTYPE;
    v_arbitrators UUID[];
    v_arbitrator_id UUID;
    v_deadline TIMESTAMPTZ;
BEGIN
    SELECT * INTO v_dispute FROM disputes WHERE id = p_dispute_id FOR UPDATE;

    IF v_dispute.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Dispute not found');
    END IF;

    IF v_dispute.status = 'in_arbitration' THEN
        RETURN jsonb_build_object('success', false, 'error', 'Already in arbitration');
    END IF;

    -- Set deadline (72 hours from now)
    v_deadline := NOW() + INTERVAL '72 hours';

    -- Select 3 random available arbitrators
    SELECT ARRAY_AGG(id) INTO v_arbitrators
    FROM (
        SELECT id FROM arbitrators
        WHERE is_active = TRUE
          AND current_disputes < max_concurrent_disputes
        ORDER BY RANDOM()
        LIMIT 3
    ) a;

    IF array_length(v_arbitrators, 1) < 3 THEN
        RETURN jsonb_build_object('success', false, 'error', 'Not enough arbitrators available');
    END IF;

    -- Update dispute
    UPDATE disputes
    SET
        status = 'in_arbitration',
        requires_arbitration = TRUE,
        arbitration_started_at = NOW(),
        arbitration_deadline = v_deadline,
        updated_at = NOW()
    WHERE id = p_dispute_id;

    -- Assign arbitrators and update their counts
    FOREACH v_arbitrator_id IN ARRAY v_arbitrators LOOP
        INSERT INTO arbitration_votes (dispute_id, arbitrator_id, deadline, vote, reasoning)
        VALUES (p_dispute_id, v_arbitrator_id, v_deadline, 'abstain', '')
        ON CONFLICT DO NOTHING;

        UPDATE arbitrators
        SET current_disputes = current_disputes + 1, last_assigned_at = NOW()
        WHERE id = v_arbitrator_id;
    END LOOP;

    -- Timeline entry
    INSERT INTO dispute_timeline (dispute_id, event_type, description, actor_type, event_data)
    VALUES (
        p_dispute_id,
        'escalated_to_arbitration',
        'Escalated to arbitration with 3 arbitrators',
        'system',
        jsonb_build_object('arbitrators', v_arbitrators, 'deadline', v_deadline)
    );

    RETURN jsonb_build_object(
        'success', true,
        'dispute_id', p_dispute_id,
        'arbitrators_assigned', array_length(v_arbitrators, 1),
        'deadline', v_deadline
    );
END;
$$;

-- Submit arbitration vote
CREATE OR REPLACE FUNCTION submit_arbitration_vote(
    p_dispute_id UUID,
    p_arbitrator_id UUID,
    p_vote arbitration_vote,
    p_reasoning TEXT,
    p_confidence INTEGER DEFAULT 5,
    p_suggested_split DECIMAL DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_existing_vote arbitration_votes%ROWTYPE;
BEGIN
    -- Get existing vote record
    SELECT * INTO v_existing_vote
    FROM arbitration_votes
    WHERE dispute_id = p_dispute_id AND arbitrator_id = p_arbitrator_id;

    IF v_existing_vote.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Not assigned to this dispute');
    END IF;

    IF v_existing_vote.vote != 'abstain' THEN
        RETURN jsonb_build_object('success', false, 'error', 'Already voted');
    END IF;

    IF v_existing_vote.deadline < NOW() THEN
        RETURN jsonb_build_object('success', false, 'error', 'Voting deadline passed');
    END IF;

    -- Update vote
    UPDATE arbitration_votes
    SET
        vote = p_vote,
        reasoning = p_reasoning,
        confidence = p_confidence,
        suggested_split = p_suggested_split,
        voted_at = NOW()
    WHERE id = v_existing_vote.id;

    -- Check if all votes are in
    PERFORM check_arbitration_complete(p_dispute_id);

    RETURN jsonb_build_object(
        'success', true,
        'vote_id', v_existing_vote.id,
        'vote', p_vote
    );
END;
$$;

-- Check if arbitration is complete and resolve
CREATE OR REPLACE FUNCTION check_arbitration_complete(p_dispute_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_dispute disputes%ROWTYPE;
    v_votes_count INTEGER;
    v_agent_votes INTEGER;
    v_executor_votes INTEGER;
    v_winner VARCHAR(50);
    v_agent_pct DECIMAL;
BEGIN
    SELECT * INTO v_dispute FROM disputes WHERE id = p_dispute_id;

    -- Count votes
    SELECT COUNT(*),
           COUNT(*) FILTER (WHERE vote = 'agent'),
           COUNT(*) FILTER (WHERE vote = 'executor')
    INTO v_votes_count, v_agent_votes, v_executor_votes
    FROM arbitration_votes
    WHERE dispute_id = p_dispute_id AND vote != 'abstain';

    -- Need at least 2 votes
    IF v_votes_count < 2 THEN
        RETURN FALSE;
    END IF;

    -- Determine winner by majority
    IF v_agent_votes > v_executor_votes THEN
        v_winner := 'agent';
        v_agent_pct := 100;
    ELSIF v_executor_votes > v_agent_votes THEN
        v_winner := 'executor';
        v_agent_pct := 0;
    ELSE
        -- Tie - split 50/50
        v_winner := 'split';
        v_agent_pct := 50;
    END IF;

    -- Update dispute
    UPDATE disputes
    SET
        status = CASE v_winner
            WHEN 'agent' THEN 'resolved_for_agent'
            WHEN 'executor' THEN 'resolved_for_executor'
            ELSE 'settled'
        END,
        resolution_type = 'arbitration',
        winner = v_winner,
        agent_refund_usdc = v_dispute.disputed_amount_usdc * (v_agent_pct / 100),
        executor_payout_usdc = v_dispute.disputed_amount_usdc * ((100 - v_agent_pct) / 100),
        resolved_at = NOW(),
        closed_at = NOW()
    WHERE id = p_dispute_id;

    -- Mark majority votes
    UPDATE arbitration_votes
    SET was_majority = (vote::text = v_winner OR (v_winner = 'split' AND vote = 'split'))
    WHERE dispute_id = p_dispute_id;

    -- Update arbitrator stats
    UPDATE arbitrators a
    SET
        disputes_handled = disputes_handled + 1,
        disputes_correct = disputes_correct + (
            SELECT CASE WHEN av.was_majority THEN 1 ELSE 0 END
            FROM arbitration_votes av WHERE av.arbitrator_id = a.id AND av.dispute_id = p_dispute_id
        ),
        current_disputes = current_disputes - 1
    WHERE id IN (SELECT arbitrator_id FROM arbitration_votes WHERE dispute_id = p_dispute_id);

    -- Timeline entry
    INSERT INTO dispute_timeline (dispute_id, event_type, description, actor_type, event_data)
    VALUES (
        p_dispute_id,
        'arbitration_complete',
        'Arbitration complete. Winner: ' || v_winner,
        'system',
        jsonb_build_object(
            'agent_votes', v_agent_votes,
            'executor_votes', v_executor_votes,
            'winner', v_winner
        )
    );

    RETURN TRUE;
END;
$$;

-- Manually resolve dispute (admin)
CREATE OR REPLACE FUNCTION resolve_dispute(
    p_dispute_id UUID,
    p_winner VARCHAR(50),
    p_resolution_notes TEXT,
    p_agent_refund_pct DECIMAL DEFAULT NULL,
    p_resolved_by VARCHAR(255) DEFAULT 'system'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_dispute disputes%ROWTYPE;
    v_agent_pct DECIMAL;
BEGIN
    SELECT * INTO v_dispute FROM disputes WHERE id = p_dispute_id FOR UPDATE;

    IF v_dispute.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Dispute not found');
    END IF;

    IF v_dispute.status IN ('resolved_for_agent', 'resolved_for_executor', 'settled', 'closed') THEN
        RETURN jsonb_build_object('success', false, 'error', 'Dispute already resolved');
    END IF;

    -- Determine split
    CASE p_winner
        WHEN 'agent' THEN v_agent_pct := COALESCE(p_agent_refund_pct, 100);
        WHEN 'executor' THEN v_agent_pct := COALESCE(p_agent_refund_pct, 0);
        WHEN 'split' THEN v_agent_pct := COALESCE(p_agent_refund_pct, 50);
        ELSE RETURN jsonb_build_object('success', false, 'error', 'Invalid winner');
    END CASE;

    -- Update dispute
    UPDATE disputes
    SET
        status = CASE p_winner
            WHEN 'agent' THEN 'resolved_for_agent'
            WHEN 'executor' THEN 'resolved_for_executor'
            ELSE 'settled'
        END,
        resolution_type = 'manual',
        resolution_notes = p_resolution_notes,
        winner = p_winner,
        agent_refund_usdc = v_dispute.disputed_amount_usdc * (v_agent_pct / 100),
        executor_payout_usdc = v_dispute.disputed_amount_usdc * ((100 - v_agent_pct) / 100),
        resolved_by = p_resolved_by,
        resolved_at = NOW(),
        closed_at = NOW()
    WHERE id = p_dispute_id;

    -- Timeline entry
    INSERT INTO dispute_timeline (dispute_id, event_type, description, actor_type, actor_id)
    VALUES (p_dispute_id, 'resolved', 'Dispute resolved: ' || p_winner, 'admin', p_resolved_by);

    RETURN jsonb_build_object(
        'success', true,
        'dispute_id', p_dispute_id,
        'winner', p_winner,
        'agent_refund_usdc', v_dispute.disputed_amount_usdc * (v_agent_pct / 100),
        'executor_payout_usdc', v_dispute.disputed_amount_usdc * ((100 - v_agent_pct) / 100)
    );
END;
$$;

-- Get dispute details
CREATE OR REPLACE FUNCTION get_dispute_details(p_dispute_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'dispute', jsonb_build_object(
            'id', d.id,
            'status', d.status,
            'reason', d.reason,
            'description', d.description,
            'disputed_amount_usdc', d.disputed_amount_usdc,
            'created_at', d.created_at,
            'response_deadline', d.response_deadline,
            'winner', d.winner,
            'agent_refund_usdc', d.agent_refund_usdc,
            'executor_payout_usdc', d.executor_payout_usdc
        ),
        'task', jsonb_build_object(
            'id', t.id,
            'title', t.title,
            'bounty_usd', t.bounty_usd,
            'category', t.category
        ),
        'executor', jsonb_build_object(
            'id', e.id,
            'display_name', e.display_name,
            'reputation_score', e.reputation_score
        ),
        'messages_count', (SELECT COUNT(*) FROM dispute_messages WHERE dispute_id = d.id),
        'in_arbitration', d.status = 'in_arbitration',
        'votes', CASE WHEN d.status = 'in_arbitration' THEN (
            SELECT jsonb_agg(jsonb_build_object(
                'arbitrator_id', av.arbitrator_id,
                'vote', av.vote,
                'voted_at', av.voted_at
            ))
            FROM arbitration_votes av WHERE av.dispute_id = d.id
        ) ELSE NULL END
    ) INTO v_result
    FROM disputes d
    JOIN tasks t ON d.task_id = t.id
    LEFT JOIN executors e ON d.executor_id = e.id
    WHERE d.id = p_dispute_id;

    RETURN v_result;
END;
$$;

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Open disputes summary
CREATE OR REPLACE VIEW open_disputes_summary AS
SELECT
    d.id,
    d.task_id,
    t.title as task_title,
    d.agent_id,
    d.executor_id,
    e.display_name as executor_name,
    d.reason,
    d.status,
    d.priority,
    d.disputed_amount_usdc,
    d.created_at,
    d.response_deadline,
    d.response_deadline < NOW() as response_overdue,
    d.requires_arbitration
FROM disputes d
JOIN tasks t ON d.task_id = t.id
LEFT JOIN executors e ON d.executor_id = e.id
WHERE d.status IN ('open', 'under_review', 'awaiting_response', 'in_arbitration')
ORDER BY d.priority DESC, d.created_at;

-- Arbitrator stats
CREATE OR REPLACE VIEW arbitrator_stats AS
SELECT
    a.id,
    a.display_name,
    a.is_active,
    a.disputes_handled,
    a.disputes_correct,
    a.accuracy_rate,
    a.stake_usdc,
    a.current_disputes,
    a.max_concurrent_disputes,
    (SELECT COUNT(*) FROM arbitration_votes av WHERE av.arbitrator_id = a.id AND av.vote = 'abstain') as pending_votes
FROM arbitrators a;

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE disputes ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispute_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE arbitrators ENABLE ROW LEVEL SECURITY;
ALTER TABLE arbitration_votes ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispute_timeline ENABLE ROW LEVEL SECURITY;

-- Disputes: Participants can view
CREATE POLICY "disputes_select_participant" ON disputes
    FOR SELECT
    USING (
        executor_id IN (SELECT id FROM executors WHERE user_id = auth.uid())
        OR true  -- Agents validated via API
    );

CREATE POLICY "disputes_service_role" ON disputes
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Messages: Participants can view (non-internal only)
CREATE POLICY "dispute_messages_select" ON dispute_messages
    FOR SELECT
    USING (NOT is_internal);

CREATE POLICY "dispute_messages_insert" ON dispute_messages
    FOR INSERT TO authenticated
    WITH CHECK (true);  -- API validates sender

CREATE POLICY "dispute_messages_service_role" ON dispute_messages
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Arbitrators: Public read
CREATE POLICY "arbitrators_select" ON arbitrators
    FOR SELECT USING (true);

CREATE POLICY "arbitrators_service_role" ON arbitrators
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Votes: Arbitrators can see their own
CREATE POLICY "votes_select_own" ON arbitration_votes
    FOR SELECT
    USING (arbitrator_id IN (SELECT id FROM arbitrators WHERE wallet_address IN (
        SELECT wallet_address FROM executors WHERE user_id = auth.uid()
    )));

CREATE POLICY "votes_service_role" ON arbitration_votes
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Timeline: Public read
CREATE POLICY "timeline_select" ON dispute_timeline
    FOR SELECT USING (true);

CREATE POLICY "timeline_service_role" ON dispute_timeline
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT EXECUTE ON FUNCTION create_dispute TO authenticated;
GRANT EXECUTE ON FUNCTION respond_to_dispute TO authenticated;
GRANT EXECUTE ON FUNCTION escalate_to_arbitration TO service_role;
GRANT EXECUTE ON FUNCTION submit_arbitration_vote TO authenticated;
GRANT EXECUTE ON FUNCTION resolve_dispute TO service_role;
GRANT EXECUTE ON FUNCTION get_dispute_details TO authenticated;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE disputes IS 'Dispute records between agents and executors';
COMMENT ON TABLE dispute_messages IS 'Communication thread for disputes';
COMMENT ON TABLE arbitrators IS 'Registered arbitrators for dispute resolution';
COMMENT ON TABLE arbitration_votes IS 'Individual arbitrator votes on disputes';
COMMENT ON TABLE dispute_timeline IS 'Full audit trail of dispute events';

COMMENT ON FUNCTION create_dispute IS 'Create a new dispute for a task';
COMMENT ON FUNCTION respond_to_dispute IS 'Executor responds to a dispute';
COMMENT ON FUNCTION escalate_to_arbitration IS 'Escalate dispute to arbitration panel';
COMMENT ON FUNCTION submit_arbitration_vote IS 'Submit an arbitration vote';
COMMENT ON FUNCTION resolve_dispute IS 'Manually resolve a dispute (admin)';
