-- ============================================================================
-- CHAMBA: Human Execution Layer for AI Agents
-- Migration: 003_reputation_system.sql
-- Description: Reputation scores, ratings, badges, and Bayesian calculation
-- Version: 2.0.0
-- Date: 2026-01-25
-- ============================================================================

-- ============================================================================
-- ENUMS
-- ============================================================================

-- Reputation event types
CREATE TYPE reputation_event_type AS ENUM (
    'task_completed',         -- Task successfully completed
    'task_approved',          -- Submission approved
    'task_rejected',          -- Submission rejected
    'task_abandoned',         -- Executor abandoned task
    'dispute_won',            -- Executor won dispute
    'dispute_lost',           -- Executor lost dispute
    'bonus_awarded',          -- Manual bonus from agent
    'penalty_applied',        -- Manual penalty (fraud, etc.)
    'tier_promotion',         -- Moved to higher tier
    'verification_passed',    -- Auto-verification passed
    'verification_failed',    -- Auto-verification failed
    'rating_received',        -- New rating from agent
    'initial_registration',   -- Account creation
    'decay_applied'           -- Monthly reputation decay
);

-- Badge types
CREATE TYPE badge_type AS ENUM (
    'newcomer',               -- First task completed
    'reliable',               -- 10 tasks, no abandons
    'trusted',                -- 50 tasks, >80 reputation
    'expert',                 -- 100 tasks, >90 reputation
    'master',                 -- 200+ tasks, >95 reputation
    'specialist',             -- Category-specific achievement
    'fast_responder',         -- Consistently fast completion
    'high_accuracy',          -- >95% approval rate
    'zero_disputes',          -- 100+ tasks, no disputes
    'top_earner',             -- Earnings milestone
    'verified_identity',      -- KYC completed
    'local_hero'              -- Geographic achievement
);

-- ============================================================================
-- TABLES
-- ============================================================================

-- ---------------------------------------------------------------------------
-- REPUTATION_LOG (Audit trail of all reputation changes)
-- ---------------------------------------------------------------------------
CREATE TABLE reputation_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Who changed
    executor_id UUID NOT NULL REFERENCES executors(id) ON DELETE CASCADE,

    -- What changed
    event_type reputation_event_type NOT NULL,
    delta INTEGER NOT NULL,  -- Can be positive or negative
    old_score INTEGER NOT NULL,
    new_score INTEGER NOT NULL,

    -- Context
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    submission_id UUID REFERENCES submissions(id) ON DELETE SET NULL,
    reason TEXT NOT NULL,

    -- Calculation details (for transparency)
    calculation_details JSONB DEFAULT '{}',

    -- On-chain tracking (future)
    tx_hash VARCHAR(66),
    block_number BIGINT,

    -- Metadata
    triggered_by TEXT,  -- 'system', 'agent:<id>', 'admin', etc.
    metadata JSONB DEFAULT '{}',

    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_reputation_log_executor ON reputation_log(executor_id);
CREATE INDEX idx_reputation_log_event ON reputation_log(event_type);
CREATE INDEX idx_reputation_log_task ON reputation_log(task_id) WHERE task_id IS NOT NULL;
CREATE INDEX idx_reputation_log_created ON reputation_log(created_at DESC);
CREATE INDEX idx_reputation_log_executor_time ON reputation_log(executor_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- RATINGS (Individual ratings for Bayesian calculation)
-- ---------------------------------------------------------------------------
CREATE TABLE ratings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Who was rated
    executor_id UUID NOT NULL REFERENCES executors(id) ON DELETE CASCADE,

    -- What task
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,

    -- Who rated
    rater_id VARCHAR(255) NOT NULL,  -- Agent ID or 'system'
    rater_type VARCHAR(50) DEFAULT 'agent',  -- 'agent', 'system', 'peer'

    -- Rating details
    rating INTEGER NOT NULL CHECK (rating >= 0 AND rating <= 100),
    stars DECIMAL(2, 1) CHECK (stars >= 0 AND stars <= 5),  -- 0-5 star equivalent

    -- Weighting factors
    task_value_usdc DECIMAL(10, 2) DEFAULT 0,  -- Bounty value for weighting
    category task_category,

    -- Qualitative feedback
    comment TEXT,
    is_public BOOLEAN DEFAULT TRUE,

    -- Breakdown scores (optional)
    quality_score INTEGER CHECK (quality_score >= 0 AND quality_score <= 100),
    speed_score INTEGER CHECK (speed_score >= 0 AND speed_score <= 100),
    communication_score INTEGER CHECK (communication_score >= 0 AND communication_score <= 100),

    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- One rating per task per executor
    CONSTRAINT ratings_unique UNIQUE (executor_id, task_id)
);

-- Indexes
CREATE INDEX idx_ratings_executor ON ratings(executor_id);
CREATE INDEX idx_ratings_task ON ratings(task_id);
CREATE INDEX idx_ratings_rater ON ratings(rater_id);
CREATE INDEX idx_ratings_category ON ratings(executor_id, category);
CREATE INDEX idx_ratings_created ON ratings(created_at DESC);

-- ---------------------------------------------------------------------------
-- BADGES (Achievements and milestones)
-- ---------------------------------------------------------------------------
CREATE TABLE badges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Who earned it
    executor_id UUID NOT NULL REFERENCES executors(id) ON DELETE CASCADE,

    -- Badge details
    badge_type badge_type NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon_url TEXT,

    -- Category-specific (for specialist badges)
    category task_category,

    -- Progress tracking (for progressive badges)
    progress INTEGER DEFAULT 100,  -- 0-100, 100 = fully earned
    max_progress INTEGER DEFAULT 100,

    -- Revocable?
    is_permanent BOOLEAN DEFAULT TRUE,
    revoked_at TIMESTAMPTZ,
    revoked_reason TEXT,

    -- On-chain (future - SBT)
    token_id INTEGER,
    contract_address VARCHAR(42),
    mint_tx VARCHAR(66),

    -- Timestamps
    earned_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- One badge type per executor (except specialist which can be per category)
    CONSTRAINT badges_unique UNIQUE (executor_id, badge_type, category)
);

-- Indexes
CREATE INDEX idx_badges_executor ON badges(executor_id);
CREATE INDEX idx_badges_type ON badges(badge_type);
CREATE INDEX idx_badges_earned ON badges(earned_at DESC);
CREATE INDEX idx_badges_active ON badges(executor_id, revoked_at)
    WHERE revoked_at IS NULL;

-- ---------------------------------------------------------------------------
-- REPUTATION_SNAPSHOTS (Historical reputation for analytics)
-- ---------------------------------------------------------------------------
CREATE TABLE reputation_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Who
    executor_id UUID NOT NULL REFERENCES executors(id) ON DELETE CASCADE,

    -- Snapshot data
    reputation_score INTEGER NOT NULL,
    tier executor_tier NOT NULL,
    tasks_completed INTEGER NOT NULL,
    tasks_disputed INTEGER NOT NULL,

    -- Period
    snapshot_date DATE NOT NULL,
    snapshot_type VARCHAR(20) DEFAULT 'daily',  -- 'daily', 'weekly', 'monthly'

    -- Calculation details
    ratings_count INTEGER,
    avg_rating DECIMAL(5, 2),
    weighted_avg DECIMAL(5, 2),

    -- Category breakdown
    category_scores JSONB DEFAULT '{}',

    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- One snapshot per executor per day per type
    CONSTRAINT snapshots_unique UNIQUE (executor_id, snapshot_date, snapshot_type)
);

-- Indexes
CREATE INDEX idx_snapshots_executor ON reputation_snapshots(executor_id);
CREATE INDEX idx_snapshots_date ON reputation_snapshots(snapshot_date DESC);
CREATE INDEX idx_snapshots_executor_date ON reputation_snapshots(executor_id, snapshot_date DESC);

-- ============================================================================
-- BAYESIAN REPUTATION CALCULATION
-- ============================================================================

/*
Reputation Formula (Bayesian Average with Time Decay):

Score = (C * m + sum(ratings * weight * decay)) / (C + sum(weight * decay))

Where:
- C = 15 (confidence parameter - higher = more weight to prior)
- m = 50 (prior mean - neutral starting point)
- weight = ln(task_value + 1) (task value weighting)
- decay = 0.9^months_old (time decay factor)

This ensures:
1. New executors start near neutral (50)
2. High-value tasks have more influence
3. Recent ratings matter more
4. Many ratings converge toward true average
*/

CREATE OR REPLACE FUNCTION calculate_bayesian_reputation(
    p_executor_id UUID
)
RETURNS DECIMAL
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    -- Bayesian parameters
    v_C DECIMAL := 15.0;        -- Confidence parameter
    v_m DECIMAL := 50.0;        -- Prior mean
    v_decay DECIMAL := 0.9;     -- Monthly decay factor

    -- Calculation variables
    v_weighted_sum DECIMAL := 0;
    v_total_weight DECIMAL := 0;
    v_record RECORD;
    v_weight DECIMAL;
    v_months_old DECIMAL;
    v_decay_factor DECIMAL;
    v_result DECIMAL;
BEGIN
    -- Calculate weighted average from ratings
    FOR v_record IN
        SELECT
            r.rating,
            r.task_value_usdc,
            r.created_at
        FROM ratings r
        WHERE r.executor_id = p_executor_id
    LOOP
        -- Weight based on task value (log scale to prevent extreme weighting)
        v_weight := LN(GREATEST(v_record.task_value_usdc, 1) + 1);

        -- Calculate months since rating
        v_months_old := EXTRACT(EPOCH FROM (NOW() - v_record.created_at)) / (30 * 24 * 60 * 60);

        -- Apply time decay
        v_decay_factor := POWER(v_decay, GREATEST(0, v_months_old));

        -- Accumulate
        v_weighted_sum := v_weighted_sum + (v_record.rating * v_weight * v_decay_factor);
        v_total_weight := v_total_weight + (v_weight * v_decay_factor);
    END LOOP;

    -- Calculate Bayesian average
    v_result := (v_C * v_m + v_weighted_sum) / (v_C + v_total_weight);

    -- Clamp to 0-100
    RETURN GREATEST(0, LEAST(100, v_result));
END;
$$;

-- Full reputation recalculation function
CREATE OR REPLACE FUNCTION recalculate_executor_reputation(
    p_executor_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_old_score INTEGER;
    v_new_score DECIMAL;
    v_old_tier executor_tier;
    v_new_tier executor_tier;
    v_executor executors%ROWTYPE;
    v_tasks_completed INTEGER;
BEGIN
    -- Get current state
    SELECT * INTO v_executor FROM executors WHERE id = p_executor_id;
    IF v_executor.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Executor not found');
    END IF;

    v_old_score := v_executor.reputation_score;
    v_old_tier := v_executor.tier;
    v_tasks_completed := v_executor.tasks_completed;

    -- Calculate new Bayesian score
    v_new_score := calculate_bayesian_reputation(p_executor_id);

    -- Determine new tier
    v_new_tier := CASE
        WHEN v_tasks_completed < 10 THEN 'probation'::executor_tier
        WHEN v_tasks_completed < 50 AND v_new_score >= 60 THEN 'standard'::executor_tier
        WHEN v_tasks_completed < 100 AND v_new_score >= 75 THEN 'verified'::executor_tier
        WHEN v_tasks_completed < 200 AND v_new_score >= 85 THEN 'expert'::executor_tier
        WHEN v_tasks_completed >= 200 AND v_new_score >= 90 THEN 'master'::executor_tier
        ELSE 'standard'::executor_tier
    END;

    -- Update executor
    UPDATE executors
    SET
        reputation_score = ROUND(v_new_score),
        tier = v_new_tier,
        updated_at = NOW()
    WHERE id = p_executor_id;

    -- Log if tier changed
    IF v_new_tier != v_old_tier THEN
        INSERT INTO reputation_log (
            executor_id, event_type, delta, old_score, new_score, reason,
            calculation_details
        ) VALUES (
            p_executor_id,
            'tier_promotion',
            ROUND(v_new_score) - v_old_score,
            v_old_score,
            ROUND(v_new_score),
            'Tier changed from ' || v_old_tier || ' to ' || v_new_tier,
            jsonb_build_object('old_tier', v_old_tier, 'new_tier', v_new_tier)
        );

        -- Award tier badge if applicable
        PERFORM award_tier_badge(p_executor_id, v_new_tier);
    END IF;

    RETURN jsonb_build_object(
        'success', true,
        'executor_id', p_executor_id,
        'old_score', v_old_score,
        'new_score', ROUND(v_new_score),
        'old_tier', v_old_tier,
        'new_tier', v_new_tier,
        'tier_changed', v_new_tier != v_old_tier
    );
END;
$$;

-- ============================================================================
-- RATING FUNCTIONS
-- ============================================================================

-- Submit a rating for an executor
CREATE OR REPLACE FUNCTION submit_rating(
    p_executor_id UUID,
    p_task_id UUID,
    p_rater_id VARCHAR(255),
    p_rating INTEGER,
    p_comment TEXT DEFAULT NULL,
    p_quality_score INTEGER DEFAULT NULL,
    p_speed_score INTEGER DEFAULT NULL,
    p_communication_score INTEGER DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_task tasks%ROWTYPE;
    v_executor executors%ROWTYPE;
    v_rating_id UUID;
    v_old_score INTEGER;
    v_new_score DECIMAL;
    v_stars DECIMAL;
BEGIN
    -- Validate rating
    IF p_rating < 0 OR p_rating > 100 THEN
        RETURN jsonb_build_object('success', false, 'error', 'Rating must be between 0 and 100');
    END IF;

    -- Get task
    SELECT * INTO v_task FROM tasks WHERE id = p_task_id;
    IF v_task.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Task not found');
    END IF;

    -- Get executor
    SELECT * INTO v_executor FROM executors WHERE id = p_executor_id;
    IF v_executor.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Executor not found');
    END IF;

    v_old_score := v_executor.reputation_score;

    -- Convert 0-100 to 0-5 stars
    v_stars := (p_rating::DECIMAL / 100) * 5;

    -- Insert or update rating
    INSERT INTO ratings (
        executor_id, task_id, rater_id, rating, stars,
        task_value_usdc, category, comment,
        quality_score, speed_score, communication_score
    ) VALUES (
        p_executor_id, p_task_id, p_rater_id, p_rating, v_stars,
        v_task.bounty_usd, v_task.category, p_comment,
        p_quality_score, p_speed_score, p_communication_score
    )
    ON CONFLICT (executor_id, task_id) DO UPDATE SET
        rating = EXCLUDED.rating,
        stars = EXCLUDED.stars,
        comment = EXCLUDED.comment,
        quality_score = EXCLUDED.quality_score,
        speed_score = EXCLUDED.speed_score,
        communication_score = EXCLUDED.communication_score,
        created_at = NOW()
    RETURNING id INTO v_rating_id;

    -- Recalculate reputation
    v_new_score := calculate_bayesian_reputation(p_executor_id);

    -- Update executor
    UPDATE executors
    SET
        reputation_score = ROUND(v_new_score),
        avg_rating = (
            SELECT AVG(stars) FROM ratings WHERE executor_id = p_executor_id
        ),
        updated_at = NOW()
    WHERE id = p_executor_id;

    -- Log the rating event
    INSERT INTO reputation_log (
        executor_id, event_type, delta, old_score, new_score,
        task_id, reason, calculation_details
    ) VALUES (
        p_executor_id,
        'rating_received',
        ROUND(v_new_score) - v_old_score,
        v_old_score,
        ROUND(v_new_score),
        p_task_id,
        'Rating received: ' || p_rating || '/100 ($' || v_task.bounty_usd || ' task)',
        jsonb_build_object(
            'rating', p_rating,
            'stars', v_stars,
            'task_value', v_task.bounty_usd,
            'rater', p_rater_id
        )
    );

    RETURN jsonb_build_object(
        'success', true,
        'rating_id', v_rating_id,
        'old_score', v_old_score,
        'new_score', ROUND(v_new_score),
        'delta', ROUND(v_new_score) - v_old_score
    );
END;
$$;

-- ============================================================================
-- BADGE FUNCTIONS
-- ============================================================================

-- Award a badge to an executor
CREATE OR REPLACE FUNCTION award_badge(
    p_executor_id UUID,
    p_badge_type badge_type,
    p_name VARCHAR(100),
    p_description TEXT DEFAULT NULL,
    p_category task_category DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_badge_id UUID;
BEGIN
    -- Check if badge already exists
    SELECT id INTO v_badge_id
    FROM badges
    WHERE executor_id = p_executor_id
      AND badge_type = p_badge_type
      AND (category = p_category OR (category IS NULL AND p_category IS NULL))
      AND revoked_at IS NULL;

    IF v_badge_id IS NOT NULL THEN
        -- Already has badge
        RETURN v_badge_id;
    END IF;

    -- Award new badge
    INSERT INTO badges (
        executor_id, badge_type, name, description, category
    ) VALUES (
        p_executor_id, p_badge_type, p_name, p_description, p_category
    )
    RETURNING id INTO v_badge_id;

    RETURN v_badge_id;
END;
$$;

-- Award tier badge
CREATE OR REPLACE FUNCTION award_tier_badge(
    p_executor_id UUID,
    p_tier executor_tier
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_badge_type badge_type;
    v_name VARCHAR(100);
    v_description TEXT;
BEGIN
    -- Map tier to badge
    CASE p_tier
        WHEN 'standard' THEN
            v_badge_type := 'reliable';
            v_name := 'Reliable Worker';
            v_description := 'Completed 10+ tasks with no abandons';
        WHEN 'verified' THEN
            v_badge_type := 'trusted';
            v_name := 'Trusted Executor';
            v_description := 'Completed 50+ tasks with 75+ reputation';
        WHEN 'expert' THEN
            v_badge_type := 'expert';
            v_name := 'Expert';
            v_description := 'Completed 100+ tasks with 85+ reputation';
        WHEN 'master' THEN
            v_badge_type := 'master';
            v_name := 'Master Executor';
            v_description := 'Completed 200+ tasks with 90+ reputation';
        ELSE
            RETURN NULL;
    END CASE;

    RETURN award_badge(p_executor_id, v_badge_type, v_name, v_description);
END;
$$;

-- Check and award milestone badges
CREATE OR REPLACE FUNCTION check_milestone_badges(p_executor_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_executor executors%ROWTYPE;
    v_badges_awarded TEXT[] := '{}';
    v_approval_rate DECIMAL;
    v_badge_id UUID;
BEGIN
    SELECT * INTO v_executor FROM executors WHERE id = p_executor_id;
    IF v_executor.id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Executor not found');
    END IF;

    -- Newcomer badge (first task)
    IF v_executor.tasks_completed >= 1 THEN
        v_badge_id := award_badge(p_executor_id, 'newcomer', 'Newcomer', 'Completed first task');
        IF v_badge_id IS NOT NULL THEN
            v_badges_awarded := array_append(v_badges_awarded, 'newcomer');
        END IF;
    END IF;

    -- Fast responder (avg completion < 4 hours for 10+ tasks)
    IF v_executor.tasks_completed >= 10 THEN
        -- Check average completion time
        PERFORM 1 FROM tasks
        WHERE executor_id = p_executor_id
          AND status = 'completed'
          AND completed_at - accepted_at < INTERVAL '4 hours'
        HAVING COUNT(*) >= 10;

        IF FOUND THEN
            v_badge_id := award_badge(p_executor_id, 'fast_responder', 'Fast Responder',
                'Consistently completes tasks in under 4 hours');
            IF v_badge_id IS NOT NULL THEN
                v_badges_awarded := array_append(v_badges_awarded, 'fast_responder');
            END IF;
        END IF;
    END IF;

    -- High accuracy (>95% approval rate, 20+ tasks)
    IF v_executor.tasks_completed >= 20 THEN
        SELECT
            (COUNT(*) FILTER (WHERE s.agent_verdict = 'approved')::DECIMAL /
             NULLIF(COUNT(*), 0)) * 100
        INTO v_approval_rate
        FROM submissions s
        WHERE s.executor_id = p_executor_id
          AND s.agent_verdict IS NOT NULL;

        IF v_approval_rate >= 95 THEN
            v_badge_id := award_badge(p_executor_id, 'high_accuracy', 'High Accuracy',
                '95%+ approval rate on submissions');
            IF v_badge_id IS NOT NULL THEN
                v_badges_awarded := array_append(v_badges_awarded, 'high_accuracy');
            END IF;
        END IF;
    END IF;

    -- Zero disputes (100+ tasks, no disputes)
    IF v_executor.tasks_completed >= 100 AND v_executor.tasks_disputed = 0 THEN
        v_badge_id := award_badge(p_executor_id, 'zero_disputes', 'Zero Disputes',
            '100+ tasks completed with no disputes');
        IF v_badge_id IS NOT NULL THEN
            v_badges_awarded := array_append(v_badges_awarded, 'zero_disputes');
        END IF;
    END IF;

    RETURN jsonb_build_object(
        'success', true,
        'executor_id', p_executor_id,
        'badges_awarded', v_badges_awarded,
        'badges_count', array_length(v_badges_awarded, 1)
    );
END;
$$;

-- ============================================================================
-- SNAPSHOT FUNCTIONS
-- ============================================================================

-- Create daily reputation snapshot
CREATE OR REPLACE FUNCTION create_reputation_snapshot(
    p_snapshot_date DATE DEFAULT CURRENT_DATE,
    p_snapshot_type VARCHAR(20) DEFAULT 'daily'
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_count INTEGER := 0;
BEGIN
    INSERT INTO reputation_snapshots (
        executor_id, reputation_score, tier, tasks_completed, tasks_disputed,
        snapshot_date, snapshot_type, ratings_count, avg_rating, weighted_avg,
        category_scores
    )
    SELECT
        e.id,
        e.reputation_score,
        e.tier,
        e.tasks_completed,
        e.tasks_disputed,
        p_snapshot_date,
        p_snapshot_type,
        COUNT(r.id),
        AVG(r.rating),
        calculate_bayesian_reputation(e.id),
        (
            SELECT jsonb_object_agg(category, avg_rating)
            FROM (
                SELECT r2.category, AVG(r2.rating) as avg_rating
                FROM ratings r2
                WHERE r2.executor_id = e.id AND r2.category IS NOT NULL
                GROUP BY r2.category
            ) cat_scores
        )
    FROM executors e
    LEFT JOIN ratings r ON r.executor_id = e.id
    WHERE e.status = 'active'
    GROUP BY e.id
    ON CONFLICT (executor_id, snapshot_date, snapshot_type) DO UPDATE SET
        reputation_score = EXCLUDED.reputation_score,
        tier = EXCLUDED.tier,
        tasks_completed = EXCLUDED.tasks_completed,
        tasks_disputed = EXCLUDED.tasks_disputed,
        ratings_count = EXCLUDED.ratings_count,
        avg_rating = EXCLUDED.avg_rating,
        weighted_avg = EXCLUDED.weighted_avg,
        category_scores = EXCLUDED.category_scores;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$;

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Executor reputation details
CREATE OR REPLACE VIEW executor_reputation_details AS
SELECT
    e.id,
    e.display_name,
    e.wallet_address,
    e.reputation_score,
    e.tier,
    e.avg_rating,
    e.tasks_completed,
    e.tasks_disputed,
    e.tasks_abandoned,
    (SELECT COUNT(*) FROM ratings r WHERE r.executor_id = e.id) as total_ratings,
    (SELECT AVG(r.rating) FROM ratings r WHERE r.executor_id = e.id) as avg_rating_raw,
    (SELECT COUNT(*) FROM badges b WHERE b.executor_id = e.id AND b.revoked_at IS NULL) as badges_count,
    (
        SELECT jsonb_agg(jsonb_build_object('type', b.badge_type, 'name', b.name, 'earned_at', b.earned_at))
        FROM badges b WHERE b.executor_id = e.id AND b.revoked_at IS NULL
    ) as badges
FROM executors e
WHERE e.status = 'active';

-- Leaderboard
CREATE OR REPLACE VIEW reputation_leaderboard AS
SELECT
    e.id,
    e.display_name,
    e.reputation_score,
    e.tier,
    e.tasks_completed,
    e.avg_rating,
    RANK() OVER (ORDER BY e.reputation_score DESC, e.tasks_completed DESC) as rank,
    (SELECT COUNT(*) FROM badges b WHERE b.executor_id = e.id AND b.revoked_at IS NULL) as badges_count
FROM executors e
WHERE e.status = 'active' AND e.tasks_completed > 0
ORDER BY e.reputation_score DESC, e.tasks_completed DESC;

-- Category specialists
CREATE OR REPLACE VIEW category_specialists AS
SELECT
    r.executor_id,
    e.display_name,
    r.category,
    COUNT(*) as tasks_in_category,
    AVG(r.rating) as avg_category_rating,
    RANK() OVER (PARTITION BY r.category ORDER BY AVG(r.rating) DESC, COUNT(*) DESC) as category_rank
FROM ratings r
JOIN executors e ON r.executor_id = e.id
WHERE r.category IS NOT NULL AND e.status = 'active'
GROUP BY r.executor_id, e.display_name, r.category
HAVING COUNT(*) >= 5;

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE reputation_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE badges ENABLE ROW LEVEL SECURITY;
ALTER TABLE reputation_snapshots ENABLE ROW LEVEL SECURITY;

-- Reputation log is public read
CREATE POLICY "reputation_log_select_public" ON reputation_log
    FOR SELECT USING (true);

CREATE POLICY "reputation_log_service_role" ON reputation_log
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Ratings are public read
CREATE POLICY "ratings_select_public" ON ratings
    FOR SELECT USING (is_public = true);

CREATE POLICY "ratings_select_own" ON ratings
    FOR SELECT
    USING (executor_id IN (SELECT id FROM executors WHERE user_id = auth.uid()));

CREATE POLICY "ratings_service_role" ON ratings
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Badges are public read
CREATE POLICY "badges_select_public" ON badges
    FOR SELECT USING (true);

CREATE POLICY "badges_service_role" ON badges
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Snapshots are public read
CREATE POLICY "snapshots_select_public" ON reputation_snapshots
    FOR SELECT USING (true);

CREATE POLICY "snapshots_service_role" ON reputation_snapshots
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT EXECUTE ON FUNCTION calculate_bayesian_reputation TO authenticated;
GRANT EXECUTE ON FUNCTION recalculate_executor_reputation TO service_role;
GRANT EXECUTE ON FUNCTION submit_rating TO authenticated;
GRANT EXECUTE ON FUNCTION award_badge TO service_role;
GRANT EXECUTE ON FUNCTION check_milestone_badges TO service_role;
GRANT EXECUTE ON FUNCTION create_reputation_snapshot TO service_role;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE reputation_log IS 'Audit trail of all reputation score changes';
COMMENT ON TABLE ratings IS 'Individual ratings for Bayesian reputation calculation';
COMMENT ON TABLE badges IS 'Achievement badges earned by executors';
COMMENT ON TABLE reputation_snapshots IS 'Historical reputation data for analytics';

COMMENT ON FUNCTION calculate_bayesian_reputation IS
'Calculate Bayesian reputation using weighted ratings with time decay.
Formula: Score = (C * m + sum(ratings * weight * decay)) / (C + sum(weights))
where weight = ln(task_value + 1) and decay = 0.9^months_old';

COMMENT ON FUNCTION submit_rating IS 'Submit a rating for an executor and recalculate reputation';
COMMENT ON FUNCTION check_milestone_badges IS 'Check and award any earned milestone badges';
