-- Migration: Add social links to executors
ALTER TABLE executors ADD COLUMN IF NOT EXISTS social_links JSONB DEFAULT '{}';
CREATE INDEX idx_executors_social_links ON executors USING GIN (social_links);
COMMENT ON COLUMN executors.social_links IS 'Social platform links. Format: {"x": {"handle": "@foo", "verified": false, "user_id": "123", "linked_at": "ISO8601"}}';
