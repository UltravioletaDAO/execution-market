-- Phase 3: Multimodal AI Verification columns
-- Stores perceptual hashes for duplicate detection and AI verification results.

ALTER TABLE submissions ADD COLUMN IF NOT EXISTS perceptual_hashes JSONB;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS ai_verification_result JSONB;

CREATE INDEX IF NOT EXISTS idx_submissions_perceptual_hashes
  ON submissions USING GIN (perceptual_hashes) WHERE perceptual_hashes IS NOT NULL;
