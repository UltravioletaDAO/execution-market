-- Migration 091: Arbiter Support (Ring 2 Dual-Inference)
-- Part of MASTER_PLAN_COMMERCE_SCHEME_ARBITER (Phase 1, Task 1.3)
--
-- Adds arbiter mode + verdict columns to existing tasks/submissions tables.
-- Reuses existing `disputes` table (mig 004) and `verification_inferences` table (mig 078).
-- Adds `triggered_by` to verification_inferences to distinguish PHOTINT from arbiter runs.
--
-- Context: ArbiterService runs Ring 2 (independent semantic inference) and writes its
-- verdict to submissions. Tasks opt into arbiter mode via arbiter_mode column.
-- The verdict is stored as JSONB for flexibility + scalar columns for fast querying.

-- ============================================================================
-- TASKS: arbiter mode opt-in
-- ============================================================================

DO $$ BEGIN
    ALTER TABLE tasks ADD COLUMN IF NOT EXISTS arbiter_enabled BOOLEAN DEFAULT FALSE;
EXCEPTION WHEN OTHERS THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE tasks ADD COLUMN IF NOT EXISTS arbiter_mode VARCHAR(20) DEFAULT 'manual';
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- Constraint: arbiter_mode must be one of: manual, auto, hybrid
DO $$ BEGIN
    ALTER TABLE tasks ADD CONSTRAINT tasks_arbiter_mode_check
        CHECK (arbiter_mode IN ('manual', 'auto', 'hybrid'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Index for filtering arbiter-enabled tasks
DO $$ BEGIN
    CREATE INDEX IF NOT EXISTS idx_tasks_arbiter_enabled
        ON tasks(arbiter_enabled) WHERE arbiter_enabled = TRUE;
EXCEPTION WHEN OTHERS THEN NULL; END $$;

COMMENT ON COLUMN tasks.arbiter_enabled IS 'Opt-in: if true, ArbiterService evaluates submissions for this task';
COMMENT ON COLUMN tasks.arbiter_mode IS 'manual=agent approves (default), auto=arbiter releases/refunds, hybrid=arbiter recommends + agent confirms';

-- ============================================================================
-- SUBMISSIONS: arbiter verdict columns
-- ============================================================================

-- Verdict decision: pass, fail, inconclusive, skipped, NULL (not yet evaluated)
DO $$ BEGIN
    ALTER TABLE submissions ADD COLUMN IF NOT EXISTS arbiter_verdict VARCHAR(20);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE submissions ADD CONSTRAINT submissions_arbiter_verdict_check
        CHECK (arbiter_verdict IS NULL OR arbiter_verdict IN ('pass', 'fail', 'inconclusive', 'skipped'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Tier used by arbiter: cheap, standard, max
DO $$ BEGIN
    ALTER TABLE submissions ADD COLUMN IF NOT EXISTS arbiter_tier VARCHAR(10);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE submissions ADD CONSTRAINT submissions_arbiter_tier_check
        CHECK (arbiter_tier IS NULL OR arbiter_tier IN ('cheap', 'standard', 'max'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Aggregate score (0.000 - 1.000)
DO $$ BEGIN
    ALTER TABLE submissions ADD COLUMN IF NOT EXISTS arbiter_score NUMERIC(4,3);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE submissions ADD CONSTRAINT submissions_arbiter_score_check
        CHECK (arbiter_score IS NULL OR (arbiter_score >= 0 AND arbiter_score <= 1));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Confidence in verdict (0.000 - 1.000)
DO $$ BEGIN
    ALTER TABLE submissions ADD COLUMN IF NOT EXISTS arbiter_confidence NUMERIC(4,3);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- keccak256 of canonical evidence payload (0x + 64 hex chars)
DO $$ BEGIN
    ALTER TABLE submissions ADD COLUMN IF NOT EXISTS arbiter_evidence_hash VARCHAR(66);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- keccak256 commitment over (task_id, decision, all ring scores)
DO $$ BEGIN
    ALTER TABLE submissions ADD COLUMN IF NOT EXISTS arbiter_commitment_hash VARCHAR(66);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- Full verdict payload as JSONB (ring_scores, reason, disagreement, cost, etc.)
-- Use this for flexible querying and audit trail; scalar columns above are for fast filters
DO $$ BEGIN
    ALTER TABLE submissions ADD COLUMN IF NOT EXISTS arbiter_verdict_data JSONB;
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- Total Ring 2 LLM cost in USD for this submission
DO $$ BEGIN
    ALTER TABLE submissions ADD COLUMN IF NOT EXISTS arbiter_cost_usd NUMERIC(10,6);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- Latency of arbiter evaluation in milliseconds
DO $$ BEGIN
    ALTER TABLE submissions ADD COLUMN IF NOT EXISTS arbiter_latency_ms INTEGER;
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- When the arbiter ran (NULL if not yet evaluated)
DO $$ BEGIN
    ALTER TABLE submissions ADD COLUMN IF NOT EXISTS arbiter_evaluated_at TIMESTAMPTZ;
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- Index for finding submissions awaiting arbiter evaluation
DO $$ BEGIN
    CREATE INDEX IF NOT EXISTS idx_submissions_arbiter_pending
        ON submissions(task_id) WHERE arbiter_verdict IS NULL;
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- Index for filtering by verdict (e.g., dashboard "show all rejected")
DO $$ BEGIN
    CREATE INDEX IF NOT EXISTS idx_submissions_arbiter_verdict
        ON submissions(arbiter_verdict) WHERE arbiter_verdict IS NOT NULL;
EXCEPTION WHEN OTHERS THEN NULL; END $$;

COMMENT ON COLUMN submissions.arbiter_verdict IS 'Ring 2 final verdict: pass/fail/inconclusive/skipped';
COMMENT ON COLUMN submissions.arbiter_tier IS 'Tier used: cheap (no LLM), standard (1 LLM), max (2 LLMs + consensus)';
COMMENT ON COLUMN submissions.arbiter_score IS 'Aggregate score combining Ring 1 + Ring 2 (0-1)';
COMMENT ON COLUMN submissions.arbiter_evidence_hash IS 'keccak256 of canonical evidence -- on-chain auditable';
COMMENT ON COLUMN submissions.arbiter_commitment_hash IS 'keccak256 of (task_id, decision, all ring scores)';
COMMENT ON COLUMN submissions.arbiter_verdict_data IS 'Full ArbiterVerdict.to_dict() for flexible querying';
COMMENT ON COLUMN submissions.arbiter_cost_usd IS 'Total LLM cost for Ring 2 inferences (0 for cheap tier)';

-- ============================================================================
-- VERIFICATION_INFERENCES: distinguish PHOTINT from Arbiter inferences
-- ============================================================================

-- triggered_by lets us separate PHOTINT (Ring 1) inferences from Arbiter (Ring 2)
-- inferences when querying cost/usage analytics. Default is 'photint' for backward compat.
DO $$ BEGIN
    ALTER TABLE verification_inferences
        ADD COLUMN IF NOT EXISTS triggered_by VARCHAR(20) DEFAULT 'photint';
EXCEPTION WHEN OTHERS THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE verification_inferences ADD CONSTRAINT verification_inferences_triggered_by_check
        CHECK (triggered_by IN ('photint', 'arbiter', 'manual', 'unknown'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Index for cost/usage analytics by source
DO $$ BEGIN
    CREATE INDEX IF NOT EXISTS idx_vi_triggered_by ON verification_inferences(triggered_by);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

COMMENT ON COLUMN verification_inferences.triggered_by IS 'Which system requested this inference: photint (Ring 1) or arbiter (Ring 2)';

-- ============================================================================
-- DISPUTES: arbiter integration columns (additive, doesn't break existing schema)
-- ============================================================================

-- escalation_tier: which tier escalated (1=PHOTINT only, 2=arbiter inconclusive, 3=human)
DO $$ BEGIN
    ALTER TABLE disputes ADD COLUMN IF NOT EXISTS escalation_tier INTEGER DEFAULT 2;
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- arbiter_verdict_data: snapshot of the ArbiterVerdict that triggered escalation
DO $$ BEGIN
    ALTER TABLE disputes ADD COLUMN IF NOT EXISTS arbiter_verdict_data JSONB;
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- Index for arbiter-triggered disputes
DO $$ BEGIN
    CREATE INDEX IF NOT EXISTS idx_disputes_arbiter_triggered
        ON disputes(escalation_tier) WHERE arbiter_verdict_data IS NOT NULL;
EXCEPTION WHEN OTHERS THEN NULL; END $$;

COMMENT ON COLUMN disputes.escalation_tier IS 'Source of escalation: 1=PHOTINT-only, 2=Arbiter inconclusive, 3=Manual escalation';
COMMENT ON COLUMN disputes.arbiter_verdict_data IS 'Snapshot of ArbiterVerdict that triggered this dispute (NULL if pre-arbiter)';

-- ============================================================================
-- COMPLETION NOTICE
-- ============================================================================

DO $$ BEGIN
    RAISE NOTICE '[OK] Migration 091 applied: arbiter support columns added to tasks, submissions, verification_inferences, disputes';
END $$;
