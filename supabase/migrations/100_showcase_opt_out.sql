-- Migration 100: Proof Wall — show_in_showcase opt-out column
-- Part of the Proof Wall carousel feature (PLAN 2026-04-17).
--
-- Adds an opt-out flag on `submissions` that governs whether an accepted
-- submission can surface in the public `/api/v1/showcase/evidence` feed
-- (the "Proof Wall" carousel on execution.market landing page).
--
-- Semantics:
--   * Default TRUE — accepted submissions are eligible for the wall unless
--     the executor explicitly opts out.
--   * Pipeline also requires `agent_verdict = 'accepted'`, `paid_at IS NOT NULL`,
--     and `array_length(evidence_files, 1) > 0` before surfacing. This column
--     is one of several gates, not the only one.
--   * NULL behaves the same as TRUE (backward-compatible for pre-existing rows).
--
-- Idempotent: uses `ADD COLUMN IF NOT EXISTS`. Safe to re-run.
-- Additive: no backfill needed; existing rows inherit the default.

ALTER TABLE submissions
    ADD COLUMN IF NOT EXISTS show_in_showcase BOOLEAN DEFAULT TRUE;

COMMENT ON COLUMN submissions.show_in_showcase IS
    'Executor opt-out flag for the public Proof Wall carousel. TRUE/NULL = eligible, FALSE = hidden. Defaults to TRUE.';

-- Partial index to speed up the showcase feed query. We only index rows that
-- can actually appear on the wall (accepted + paid + not opted-out). This keeps
-- the index small and matches the WHERE clause in routers/showcase.py.
CREATE INDEX IF NOT EXISTS idx_submissions_showcase_feed
    ON submissions (paid_at DESC, id DESC)
    WHERE agent_verdict = 'accepted'
      AND paid_at IS NOT NULL
      AND (show_in_showcase IS NULL OR show_in_showcase = TRUE);
