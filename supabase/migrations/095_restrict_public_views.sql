-- Migration 095: Phase 2 RLS — Restrict public views to hide PII & financial data
-- Security audit 2026-04-07 (specialist SC_06_DATABASE_SUPABASE)
-- Closes: DB-005, DB-006, DB-006b, DB-007, DB-015
--
-- CONTEXT
-- -------
-- Phase 0+1 (migration 092) revoked anon/authenticated EXECUTE on account-
-- takeover RPCs. This migration addresses SELECT policies that still leak PII
-- and financial data to unauthenticated or weakly-authenticated users.
--
-- PostgreSQL RLS operates at the ROW level only — there is no column-level
-- restriction in RLS policies. The standard mitigation is:
--   1. REVOKE SELECT on the base table from anon/authenticated
--   2. CREATE a VIEW that omits sensitive columns
--   3. GRANT SELECT on the view to anon/authenticated
--   4. service_role bypasses RLS automatically and retains full column access
--
-- BREAKING CHANGES
-- ----------------
-- Any frontend code that queries the base tables directly via Supabase client
-- will fail after this migration. Known affected queries:
--
--   TABLE: tasks (→ must use tasks_safe or backend API)
--   ---------------------------------------------------------------
--   dashboard/src/services/tasks.ts              — 7 .from('tasks') calls
--   dashboard/src/services/submissions.ts        — 2 .from('tasks') calls
--   dashboard/src/services/payments.ts           — 2 .from('tasks') calls
--   dashboard/src/components/TaskDetailModal.tsx  — 1 .from('tasks').select('*')
--   dashboard/src/hooks/usePublicMetrics.ts       — 1 .from('tasks')
--   dashboard/src/hooks/useActivityFeed.ts        — 1 .from('tasks')
--   dashboard/src/hooks/useAgentCard.ts           — 1 .from('tasks')
--   dashboard/src/hooks/useProfile.ts             — 1 .from('tasks')
--   dashboard/src/hooks/useTaskFeedCards.ts        — 1 .from('tasks')
--   dashboard/src/hooks/useTaskPayment.ts          — 1 .from('tasks')
--   dashboard/src/hooks/useTasks.ts                — 3 .from('tasks')
--   dashboard/src/pages/PublicProfile.tsx           — 2 .from('tasks')
--
--   TABLE: executors (→ must use executors_safe or backend API)
--   ---------------------------------------------------------------
--   dashboard/src/context/AuthContext.tsx          — 3 .from('executors')
--   dashboard/src/hooks/useProfile.ts             — 2 .from('executors')
--   dashboard/src/hooks/useProfileUpdate.ts       — 2 .from('executors')
--   dashboard/src/hooks/useAgentCard.ts           — 3 .from('executors')
--   dashboard/src/hooks/usePublicMetrics.ts       — 1 .from('executors')
--   dashboard/src/hooks/useTaskFeedCards.ts        — 2 .from('executors')
--   dashboard/src/hooks/useXProfileEnrichment.ts  — 3 .from('executors')
--   dashboard/src/i18n/index.ts                   — 1 .from('executors')
--   dashboard/src/pages/PublicProfile.tsx          — 1 .from('executors')
--   dashboard/src/services/tasks.ts               — 2 .from('executors')
--
--   TABLE: escrows (→ must use backend API)
--   ---------------------------------------------------------------
--   dashboard/src/services/payments.ts            — 1 .from('escrows')
--
--   TABLE: payments (→ must use backend API)
--   ---------------------------------------------------------------
--   dashboard/src/services/payments.ts            — 2 .from('payments')
--   dashboard/src/hooks/useTaskPayment.ts         — 1 .from('payments')
--
--   TABLE: disputes (no frontend direct queries found, but policy was open)
--
-- MIGRATION PATH: These frontend queries must be migrated to either:
--   (a) Query the _safe views (tasks_safe, executors_safe) instead of base tables, OR
--   (b) Query through the backend REST API (https://api.execution.market/api/v1/*)
--       which uses service_role and returns only the fields the endpoint chooses.
-- This is tracked as GR-1.7 in the security remediation plan.

BEGIN;

-- ============================================================================
-- 1. DB-005: tasks_select_public exposes PII columns
--    human_wallet, human_user_id, location_lat, location_lng, metadata,
--    assignment_notes, chainwitness_proof, completion_notes are all leaked.
-- ============================================================================

-- 1a. Create a safe view that omits PII/sensitive columns
CREATE OR REPLACE VIEW public.tasks_safe AS
SELECT
    -- Identity & core
    id,
    agent_id,
    agent_name,
    title,
    instructions,
    category,
    tags,

    -- Location (public hints only — no precise GPS)
    location_hint,
    location_address,
    location_radius_km,

    -- Evidence schema (describes WHAT is needed, not PII)
    evidence_schema,

    -- Payment (public info)
    bounty_usd,
    payment_token,
    chain_id,
    payment_network,

    -- Escrow (public status)
    escrow_id,
    escrow_tx,
    escrow_amount_usdc,
    escrow_created_at,

    -- Timing
    deadline,
    estimated_duration_minutes,

    -- Requirements (public info for worker matching)
    min_reputation,
    required_roles,
    required_tier,
    max_executors,
    is_public,

    -- Status & assignment
    status,
    executor_id,
    accepted_at,
    started_at,
    assigned_at,

    -- Publisher type (agent vs human)
    publisher_type,
    target_executor_type,
    verification_mode,
    required_capabilities,

    -- Arbiter
    arbiter_enabled,
    arbiter_mode,

    -- Skill version
    skill_version,

    -- Completion (non-sensitive)
    completed_at,
    refund_tx,

    -- External reference
    external_id,

    -- Timestamps
    created_at,
    updated_at,
    published_at,

    -- REDACTED columns: returned as NULL to preserve column compatibility
    -- but never expose real values to anon/authenticated
    NULL::text      AS human_wallet,
    NULL::text      AS human_user_id,
    NULL::float8    AS location_lat,
    NULL::float8    AS location_lng,
    NULL::jsonb     AS metadata,
    NULL::text      AS assignment_notes,
    NULL::varchar   AS chainwitness_proof,
    NULL::text      AS completion_notes
FROM tasks
WHERE status NOT IN ('draft', 'cancelled');

COMMENT ON VIEW public.tasks_safe IS
    'Public-safe view of tasks. Omits PII (human_wallet, human_user_id, '
    'location_lat/lng) and sensitive metadata. Use for anon/authenticated '
    'queries. service_role queries the base table directly. (Migration 095, DB-005)';

-- 1b. Drop the overly permissive policy
-- (Cannot column-restrict via RLS, so we revoke table access entirely for
-- anon/authenticated and grant only on the safe view.)
DO $$ BEGIN
    DROP POLICY IF EXISTS "tasks_select_public" ON tasks;
    RAISE NOTICE '095: dropped tasks_select_public';
EXCEPTION WHEN undefined_object THEN
    RAISE NOTICE '095: tasks_select_public did not exist (skipped)';
END $$;

-- 1c. Revoke direct SELECT from anon/authenticated on the base table.
-- NOTE: Other SELECT policies (tasks_select_own_drafts from 055 — already
-- dropped, tasks_update_executor from 062) remain because they target
-- authenticated users who own the rows. We revoke the broad grant and the
-- remaining policies for INSERT/UPDATE/service_role are unaffected.
REVOKE SELECT ON tasks FROM anon;
-- We do NOT revoke from authenticated because other policies
-- (tasks_insert_own, tasks_update_executor) use FOR INSERT/UPDATE and
-- the SELECT needed for those is provided by the view or by service_role.
-- However, the tasks_select_public policy was the ONLY permissive SELECT
-- for anon. Dropping it means anon gets zero rows from the base table.
-- Authenticated users still have no broad SELECT policy after this drop.
-- They need the safe view too.

-- 1d. Grant SELECT on the safe view to anon and authenticated
GRANT SELECT ON public.tasks_safe TO anon;
GRANT SELECT ON public.tasks_safe TO authenticated;

-- 1e. Ensure service_role still has full access on base table
-- (service_role bypasses RLS, but explicit GRANT ensures no surprises)
GRANT ALL ON tasks TO service_role;


-- ============================================================================
-- 2. DB-015: executors_select_public exposes wallet_address, email, phone
--    Also leaks: balance_usdc, total_earned_usdc, total_withdrawn_usdc,
--    bio (arguable), user_id.
-- ============================================================================

-- 2a. Create a safe view that omits PII/financial columns
CREATE OR REPLACE VIEW public.executors_safe AS
SELECT
    -- Public identity
    id,
    display_name,
    avatar_url,
    bio,

    -- Skills & matching
    roles,
    skills,
    languages,
    preferred_language,

    -- Location (city/country only — no precise coordinates)
    location_city,
    location_country,
    timezone,

    -- Status & tier
    status,
    tier,
    is_verified,

    -- Reputation (public)
    reputation_score,
    avg_rating,

    -- Task stats (public)
    tasks_completed,
    tasks_disputed,
    tasks_abandoned,

    -- On-chain identity (public)
    erc8004_agent_id,

    -- World ID (public badge)
    world_id_verified,

    -- Social links (public)
    social_links,

    -- Timestamps
    created_at,
    updated_at,
    last_active_at,

    -- REDACTED columns: returned as NULL for column compatibility
    NULL::varchar(42)   AS wallet_address,
    NULL::uuid          AS user_id,
    NULL::varchar(255)  AS email,
    NULL::varchar(50)   AS phone,
    NULL::decimal(18,6) AS balance_usdc,
    NULL::decimal(18,6) AS total_earned_usdc,
    NULL::decimal(18,6) AS total_withdrawn_usdc,
    NULL::text          AS reputation_contract,
    NULL::integer       AS reputation_token_id,
    NULL::timestamptz   AS kyc_completed_at,
    NULL::timestamptz   AS gas_dust_funded_at
FROM executors
WHERE status IN ('active', 'pending_verification');

COMMENT ON VIEW public.executors_safe IS
    'Public-safe view of executors. Omits PII (wallet_address, email, phone, '
    'user_id) and financial data (balance_usdc, earned, withdrawn). '
    'Use for anon/authenticated queries. (Migration 095, DB-015)';

-- 2b. Drop the overly permissive policy
DO $$ BEGIN
    DROP POLICY IF EXISTS "executors_select_public" ON executors;
    RAISE NOTICE '095: dropped executors_select_public';
EXCEPTION WHEN undefined_object THEN
    RAISE NOTICE '095: executors_select_public did not exist (skipped)';
END $$;

-- 2c. Revoke direct SELECT from anon on the base table.
-- authenticated keeps access via executors_update_own (needs SELECT for
-- the USING clause) and via executors_service_role.
REVOKE SELECT ON executors FROM anon;

-- 2d. Grant SELECT on the safe view
GRANT SELECT ON public.executors_safe TO anon;
GRANT SELECT ON public.executors_safe TO authenticated;

-- 2e. Ensure service_role retains full access
GRANT ALL ON executors TO service_role;


-- ============================================================================
-- 3. DB-006: escrows_select_agent uses USING(true) — full escrow data to anyone
--    Escrow data (amounts, addresses, tx hashes, metadata) should only be
--    readable by the backend. The executor-specific policy
--    (escrows_select_executor) is fine and stays.
-- ============================================================================

DO $$ BEGIN
    DROP POLICY IF EXISTS "escrows_select_agent" ON escrows;
    RAISE NOTICE '095: dropped escrows_select_agent (USING true)';
EXCEPTION WHEN undefined_object THEN
    RAISE NOTICE '095: escrows_select_agent did not exist (skipped)';
END $$;

-- Replace with service_role-only access (in addition to the existing
-- escrows_service_role FOR ALL policy, this is a belt-and-suspenders
-- SELECT-specific grant).
CREATE POLICY "escrows_select_service_role_only"
    ON escrows FOR SELECT
    TO service_role
    USING (true);

-- Revoke direct SELECT from anon. The executor-specific policy
-- (escrows_select_executor) remains for authenticated workers to see
-- their own escrows.
REVOKE SELECT ON escrows FROM anon;

-- Ensure service_role retains full access
GRANT ALL ON escrows TO service_role;


-- ============================================================================
-- 4. DB-007: disputes_select_participant has OR true — all disputes to anyone
--    Replace with actual participant checks. Executors can see disputes where
--    they are the executor_id. Agents can see disputes for tasks they own.
-- ============================================================================

DO $$ BEGIN
    DROP POLICY IF EXISTS "disputes_select_participant" ON disputes;
    RAISE NOTICE '095: dropped disputes_select_participant (OR true)';
EXCEPTION WHEN undefined_object THEN
    RAISE NOTICE '095: disputes_select_participant did not exist (skipped)';
END $$;

-- Authenticated users can only see disputes where they are a participant:
-- either as the executor or as the agent who owns the task.
CREATE POLICY "disputes_select_participant_real"
    ON disputes FOR SELECT
    TO authenticated
    USING (
        -- Executor involved in the dispute
        executor_id IN (SELECT current_executor_ids())
        -- OR agent who owns the task
        OR task_id IN (
            SELECT id FROM tasks
            WHERE agent_id IN (SELECT current_wallet_addresses())
        )
    );

-- service_role always has full access (existing disputes_service_role policy
-- from migration 004 covers this, but add an explicit one for clarity)
DO $$ BEGIN
    DROP POLICY IF EXISTS "disputes_select_service_role" ON disputes;
EXCEPTION WHEN undefined_object THEN NULL;
END $$;

CREATE POLICY "disputes_select_service_role"
    ON disputes FOR SELECT
    TO service_role
    USING (true);

-- Revoke anon SELECT — disputes are never public
REVOKE SELECT ON disputes FROM anon;


-- ============================================================================
-- 5. DB-006b: payments_select_agent uses USING(true) — all payment records to
--    anyone. Payment data (amounts, tx hashes, executor associations) should
--    only be readable by the backend or by the executor who earned the payment.
--    The executor-specific policy (payments_select_own) stays.
-- ============================================================================

DO $$ BEGIN
    DROP POLICY IF EXISTS "payments_select_agent" ON payments;
    RAISE NOTICE '095: dropped payments_select_agent (USING true)';
EXCEPTION WHEN undefined_object THEN
    RAISE NOTICE '095: payments_select_agent did not exist (skipped)';
END $$;

-- Replace with service_role-only access
CREATE POLICY "payments_select_service_role_only"
    ON payments FOR SELECT
    TO service_role
    USING (true);

-- Revoke anon SELECT — payments are never public
REVOKE SELECT ON payments FROM anon;

-- Ensure service_role retains full access
GRANT ALL ON payments TO service_role;


-- ============================================================================
-- VERIFICATION QUERY (run after applying to check state):
--
--   -- Check that the USING(true) SELECT policies are gone:
--   SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
--   FROM pg_policies
--   WHERE tablename IN ('tasks', 'executors', 'escrows', 'payments', 'disputes')
--     AND cmd = 'SELECT'
--   ORDER BY tablename, policyname;
--
--   -- Check that the safe views exist:
--   SELECT table_name FROM information_schema.views
--   WHERE table_schema = 'public'
--     AND table_name IN ('tasks_safe', 'executors_safe');
--
--   -- Check that anon can SELECT on views but NOT on base tables:
--   SELECT has_table_privilege('anon', 'public.tasks', 'SELECT');           -- expect f
--   SELECT has_table_privilege('anon', 'public.executors', 'SELECT');       -- expect f
--   SELECT has_table_privilege('anon', 'public.tasks_safe', 'SELECT');      -- expect t
--   SELECT has_table_privilege('anon', 'public.executors_safe', 'SELECT');  -- expect t
-- ============================================================================

COMMIT;
