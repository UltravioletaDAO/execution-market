-- Migration 121: Atomic verification-event writes + April zombie backfill
-- Phase 5 of MASTER_PLAN_RINGS_VERIFICATION_FIXES_2026-06-11
-- Findings: C-05/C-06/C-10/C-22/C-23/C-30 (event log destroyed by
-- read-modify-write races and replace-writes), C-44 + U-35 (77 zombie
-- submissions + 10 frozen event streams from INC-2026-04-12/13/22).

-- ---------------------------------------------------------------------------
-- 1. append_verification_event — atomic JSONB append (C-06/C-10/C-23)
--    Replaces the GET+PATCH read-modify-write cycle used by 4+ concurrent
--    writers (Ring 1 Lambda, Ring 2 Lambda, ECS arbiter, background runner)
--    that randomly lost events and froze dashboard spinners.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION append_verification_event(
    p_submission_id UUID,
    p_event JSONB
) RETURNS VOID
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    UPDATE submissions
    SET auto_check_details = jsonb_set(
        COALESCE(auto_check_details, '{}'::jsonb),
        '{verification_events}',
        COALESCE(auto_check_details->'verification_events', '[]'::jsonb)
            || jsonb_build_array(p_event),
        true
    )
    WHERE id = p_submission_id;
$$;

REVOKE ALL ON FUNCTION append_verification_event(UUID, JSONB)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION append_verification_event(UUID, JSONB)
    TO service_role;

-- ---------------------------------------------------------------------------
-- 2. update_auto_check_merged — final write that PRESERVES the forensic
--    event log (C-05/C-22/C-30). The old write replaced the whole JSONB,
--    destroying verification_events twice per run. DB-side events always
--    win; the caller's copy of verification_events is only used when the
--    row has none (first write).
--    Also persists auto_check_score from details->>'score' (C-42).
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION update_auto_check_merged(
    p_submission_id UUID,
    p_passed BOOLEAN,
    p_details JSONB
) RETURNS VOID
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    UPDATE submissions
    SET auto_check_passed = p_passed,
        auto_check_score = COALESCE(
            (p_details->>'score')::numeric,
            auto_check_score
        ),
        auto_check_details = (p_details - 'verification_events')
            || jsonb_build_object(
                'verification_events',
                COALESCE(
                    auto_check_details->'verification_events',
                    p_details->'verification_events',
                    '[]'::jsonb
                )
            )
    WHERE id = p_submission_id;
$$;

REVOKE ALL ON FUNCTION update_auto_check_merged(UUID, BOOLEAN, JSONB)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION update_auto_check_merged(UUID, BOOLEAN, JSONB)
    TO service_role;

-- ---------------------------------------------------------------------------
-- 3. One-shot backfill: April zombies -> terminal state (C-44, U-35)
--    Approved by Saul 2026-06-12: terminal state = 'expired_unreviewed'.
--    Idempotent: re-running matches no rows.
-- ---------------------------------------------------------------------------

-- 3a. Non-terminal submissions from before May -> expired_unreviewed
UPDATE submissions
SET agent_verdict = 'expired_unreviewed'
WHERE (agent_verdict IS NULL OR agent_verdict = 'pending')
  AND created_at < '2026-05-01';

-- 3b. Frozen event streams (ring1_status stuck on 'running') -> close with
--     a terminal error state + closing event so dashboards stop spinning.
UPDATE submissions
SET auto_check_passed = FALSE,
    auto_check_details = jsonb_set(
        COALESCE(auto_check_details, '{}'::jsonb),
        '{verification_events}',
        COALESCE(auto_check_details->'verification_events', '[]'::jsonb)
            || jsonb_build_array(jsonb_build_object(
                'ts', EXTRACT(EPOCH FROM NOW())::bigint,
                'ring', 1,
                'step', 'backfill_close',
                'status', 'error',
                'detail', jsonb_build_object(
                    'reason',
                    'Stale run closed by 2026-06 backfill (INC-2026-04-12/13/22 zombies)'
                )
            )),
        true
    ) || jsonb_build_object(
        'ring1_status', 'error',
        'ring1_error', 'Backfilled: stale April run closed as expired_unreviewed',
        'review_required', true
    )
WHERE created_at < '2026-05-01'
  AND auto_check_details->>'ring1_status' = 'running';
