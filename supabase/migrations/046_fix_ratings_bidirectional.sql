-- Create ratings table with bidirectional support (agent→worker AND worker→agent)
-- Applied manually to production 2026-03-15.
-- Uses ratings_unique_directional UNIQUE(executor_id, task_id, rater_type)
-- instead of the original UNIQUE(executor_id, task_id) from migration 003.

CREATE TABLE IF NOT EXISTS ratings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    executor_id UUID NOT NULL REFERENCES executors(id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    rater_id VARCHAR(255) NOT NULL,
    rater_type VARCHAR(50) DEFAULT 'agent',
    rating INTEGER NOT NULL CHECK (rating >= 0 AND rating <= 100),
    stars DECIMAL(2, 1) CHECK (stars >= 0 AND stars <= 5),
    task_value_usdc DECIMAL(10, 2) DEFAULT 0,
    comment TEXT,
    is_public BOOLEAN DEFAULT TRUE,
    quality_score INTEGER CHECK (quality_score >= 0 AND quality_score <= 100),
    speed_score INTEGER CHECK (speed_score >= 0 AND speed_score <= 100),
    communication_score INTEGER CHECK (communication_score >= 0 AND communication_score <= 100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT ratings_unique_directional UNIQUE (executor_id, task_id, rater_type)
);

CREATE INDEX IF NOT EXISTS idx_ratings_executor ON ratings(executor_id);
CREATE INDEX IF NOT EXISTS idx_ratings_task ON ratings(task_id);
CREATE INDEX IF NOT EXISTS idx_ratings_rater ON ratings(rater_id);
CREATE INDEX IF NOT EXISTS idx_ratings_created ON ratings(created_at DESC);

-- RLS
ALTER TABLE ratings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public ratings are readable" ON ratings
    FOR SELECT USING (is_public = true);
CREATE POLICY "Ratings insertable by authenticated" ON ratings
    FOR INSERT WITH CHECK (true);
