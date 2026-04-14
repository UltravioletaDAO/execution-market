-- Migration 098: Magika file type detection columns
--
-- Adds audit trail for content-based file type validation (Ring 1 Phase B).
-- Uses flat root fields for efficient B-tree indexing — nested JSONB @> operator
-- does NOT work for keys inside nested objects (returns 0 rows for deep paths).
--
-- Related: docs/planning/MASTER_PLAN_MAGIKA_INTEGRATION.md
-- Related: mcp_server/verification/magika_validator.py

-- 1. Main JSONB column for Magika analysis results.
--    Structure (flat root fields for indexing, nested details for audit):
--    {
--      "analyzed": true,
--      "max_fraud_score": 0.8,        <- flat, B-tree indexable via computed column
--      "has_critical_mismatch": true, <- flat, B-tree indexable
--      "files_analyzed": 4,
--      "files_rejected": 1,
--      "analyzed_at": "2026-04-14T...",
--      "details": {
--        "photo": {
--          "detected_mime": "image/jpeg",
--          "claimed_mime": "image/jpeg",
--          "is_mismatch": false,
--          "confidence": 0.99,
--          "fraud_score": 0.0
--        },
--        "screenshot": { ... }
--      }
--    }
ALTER TABLE submissions
  ADD COLUMN IF NOT EXISTS magika_detections JSONB DEFAULT '{}'::jsonb;

COMMENT ON COLUMN submissions.magika_detections IS
  'Magika content-based file type detection results. Root-level fields (max_fraud_score, '
  'has_critical_mismatch) are flat for efficient B-tree indexing via computed column. '
  'Per-file details are nested under "details" key keyed by evidence type.';


-- 2. Computed (generated) column: extracts max_fraud_score from JSONB.
--    B-tree indexed directly — no GIN required for fraud score range queries.
--    PostgreSQL 12+ supports GENERATED ALWAYS AS ... STORED.
ALTER TABLE submissions
  ADD COLUMN IF NOT EXISTS magika_max_fraud_score NUMERIC(4,3)
  GENERATED ALWAYS AS (
    CASE
      WHEN magika_detections ? 'max_fraud_score'
      THEN (magika_detections->>'max_fraud_score')::numeric
      ELSE NULL
    END
  ) STORED;

COMMENT ON COLUMN submissions.magika_max_fraud_score IS
  'Computed from magika_detections.max_fraud_score. '
  'Indexed for fast fraud queries. NULL means Magika has not run yet.';


-- 3. GIN index for general JSONB queries (label searches, analyzed flag, etc.)
CREATE INDEX IF NOT EXISTS idx_submissions_magika_detections
  ON submissions USING GIN (magika_detections);


-- 4. B-tree index on computed fraud score (range queries: score >= 0.8)
CREATE INDEX IF NOT EXISTS idx_submissions_magika_fraud_score
  ON submissions(magika_max_fraud_score)
  WHERE magika_max_fraud_score IS NOT NULL;


-- 5. Partial index for critical mismatches (admin dashboard query, compliance reports)
CREATE INDEX IF NOT EXISTS idx_submissions_magika_critical
  ON submissions(id, submitted_at)
  WHERE magika_max_fraud_score >= 0.8;


-- 6. Extend verification_inferences table for Magika audit trail (Tarea 2.6)
--    Optional columns — existing rows default to NULL, no data loss.
ALTER TABLE verification_inferences
  ADD COLUMN IF NOT EXISTS magika_detections JSONB DEFAULT '{}'::jsonb;

ALTER TABLE verification_inferences
  ADD COLUMN IF NOT EXISTS magika_max_fraud_score NUMERIC(4,3);

COMMENT ON COLUMN verification_inferences.magika_detections IS
  'Snapshot of Magika detections at inference time. Allows correlating file type '
  'fraud signals with specific LLM inference calls in the audit trail.';


-- 7. Feature flags in platform_config (dynamic — no ECS redeploy needed to toggle).
--    enabled:             master switch (false = skip Magika, log warning)
--    hard_block:          false = soft signal only (ring 2 penalizes score)
--                         true  = reject submission immediately at fraud_score >= threshold
--    min_fraud_score_block: score threshold for hard block (only used if hard_block=true)
INSERT INTO platform_config (key, value, description, updated_at)
VALUES (
  'feature.magika',
  '{"enabled": false, "hard_block": false, "min_fraud_score_block": 0.8}'::jsonb,
  'Magika content-based file type validation. enabled=false is safe default (fail-open). '
  'Set enabled=true to activate. hard_block=false = soft signal (recommended for rollout). '
  'Toggle without ECS redeploy.',
  NOW()
)
ON CONFLICT (key) DO NOTHING;
