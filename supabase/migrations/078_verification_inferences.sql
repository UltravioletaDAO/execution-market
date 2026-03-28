-- Migration 078: Verification Inferences Audit Trail
-- Part of PHOTINT Verification Overhaul (Phase 1)
--
-- Full audit trail for every AI inference during evidence verification.
-- Tracks prompt, response, model, tokens, latency, cost for evaluation and tuning.
-- Pattern follows payment_events (migration 027).

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'verification_inferences') THEN

        CREATE TABLE verification_inferences (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
            task_id UUID NOT NULL,

            -- What check was performed
            check_name TEXT NOT NULL,                -- 'ai_semantic', 'tampering', 'genai_detection', etc.
            tier TEXT NOT NULL DEFAULT 'tier_2',     -- 'tier_0', 'tier_1', 'tier_2', 'tier_3'

            -- Which model performed it
            provider TEXT NOT NULL,                  -- 'gemini', 'anthropic', 'openai', 'bedrock', 'rekognition'
            model TEXT NOT NULL,                     -- 'gemini-2.5-flash', 'claude-sonnet-4-20250514', etc.

            -- Prompt tracking
            prompt_version TEXT NOT NULL,            -- 'photint-v1.0-physical_presence'
            prompt_hash TEXT NOT NULL,               -- SHA-256 of rendered prompt (for dedup/tracking)
            prompt_text TEXT NOT NULL,               -- Full prompt sent to model

            -- Response tracking
            response_text TEXT NOT NULL,             -- Full raw response from model
            parsed_decision TEXT,                    -- 'approved', 'rejected', 'needs_human'
            parsed_confidence NUMERIC(4,3),          -- 0.000 - 1.000
            parsed_issues JSONB DEFAULT '[]'::jsonb, -- Extracted issues array

            -- Performance metrics
            input_tokens INTEGER,
            output_tokens INTEGER,
            latency_ms INTEGER,                     -- Request duration in milliseconds
            estimated_cost_usd NUMERIC(10,6),       -- Estimated cost of this inference

            -- Context
            task_category TEXT,                      -- Task category for analytics
            evidence_types TEXT[],                   -- Evidence types submitted
            photo_count INTEGER,                     -- Number of photos analyzed

            -- Auditability
            commitment_hash TEXT,                    -- keccak256 for on-chain auditability

            -- Agent feedback (populated later when agent approves/rejects)
            agent_agreed BOOLEAN,                    -- Did agent agree with AI decision?
            agent_decision TEXT,                     -- Agent's actual decision
            agent_notes TEXT,                        -- Agent's notes on the decision

            -- Extra data
            metadata JSONB DEFAULT '{}'::jsonb,      -- EXIF summary, Rekognition labels, etc.

            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Indexes for analytics and querying
        CREATE INDEX idx_vi_submission ON verification_inferences(submission_id);
        CREATE INDEX idx_vi_task ON verification_inferences(task_id);
        CREATE INDEX idx_vi_provider_model ON verification_inferences(provider, model);
        CREATE INDEX idx_vi_prompt_version ON verification_inferences(prompt_version);
        CREATE INDEX idx_vi_decision ON verification_inferences(parsed_decision);
        CREATE INDEX idx_vi_category ON verification_inferences(task_category);
        CREATE INDEX idx_vi_created ON verification_inferences(created_at DESC);
        CREATE INDEX idx_vi_tier ON verification_inferences(tier);
        CREATE INDEX idx_vi_agent_agreed ON verification_inferences(agent_agreed)
            WHERE agent_agreed IS NOT NULL;

        -- RLS: Only service_role can insert/read (server-side only)
        ALTER TABLE verification_inferences ENABLE ROW LEVEL SECURITY;

        CREATE POLICY vi_service_role_all ON verification_inferences
            FOR ALL USING (auth.role() = 'service_role');

        RAISE NOTICE '[OK] Created verification_inferences table with indexes and RLS';
    ELSE
        RAISE NOTICE '[SKIP] verification_inferences table already exists';
    END IF;
END $$;
