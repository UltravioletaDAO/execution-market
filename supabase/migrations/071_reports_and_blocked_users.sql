-- Made idempotent 2026-03-28: safe to re-run on partial application
-- Reports table for content moderation (Apple 1.2 / Google UGC policy)
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id UUID NOT NULL REFERENCES executors(id),
    target_type TEXT NOT NULL CHECK (target_type IN ('task', 'submission', 'message', 'user')),
    target_id TEXT NOT NULL,
    reason_category TEXT NOT NULL CHECK (reason_category IN ('spam', 'abuse', 'fraud', 'inappropriate', 'harassment', 'other')),
    reason_text TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'actioned', 'dismissed')),
    admin_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

DO $$ BEGIN
    CREATE INDEX idx_reports_status ON reports(status);
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;

DO $$ BEGIN
    CREATE INDEX idx_reports_target ON reports(target_type, target_id);
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;

DO $$ BEGIN
    CREATE INDEX idx_reports_reporter ON reports(reporter_id);
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;

-- Blocked users table
CREATE TABLE IF NOT EXISTS blocked_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES executors(id),
    blocked_user_id UUID NOT NULL REFERENCES executors(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, blocked_user_id)
);

DO $$ BEGIN
    CREATE INDEX idx_blocked_users_user ON blocked_users(user_id);
EXCEPTION WHEN duplicate_table THEN NULL;
END $$;

-- RLS policies
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE blocked_users ENABLE ROW LEVEL SECURITY;

-- Reports: users can create, admins can read/update
DO $$ BEGIN
    CREATE POLICY reports_insert ON reports FOR INSERT WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reports_select_own ON reports FOR SELECT USING (reporter_id = auth.uid()::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Blocked users: users manage their own blocks
DO $$ BEGIN
    CREATE POLICY blocked_users_own ON blocked_users FOR ALL USING (user_id = auth.uid()::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
