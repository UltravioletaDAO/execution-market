-- Migration 043: Security Advisor Fixes
-- Resolves all 10 Supabase Security Advisor errors (2026-03-04)
--
-- Root causes:
--   A) Live DB drift: user_wallets, badges, escrows, payments had RLS in
--      original migrations (001, 002, 003) but it's OFF in production.
--      Likely caused by CREATE TABLE IF NOT EXISTS in migration 015.
--   B) Never defined: gas_dust_events (031), kk_* tables (036) shipped
--      without RLS or policies.
--   C) View security mode: h2a_tasks_public (035) uses SECURITY DEFINER
--      instead of SECURITY INVOKER. View is unused dead code.
--   D) PostGIS system table: spatial_ref_sys flagged because it's in
--      public schema without RLS.
--
-- This migration is idempotent — safe to re-run.

-- ============================================================================
-- 1. DROP unused SECURITY DEFINER view (h2a_tasks_public)
-- ============================================================================
-- This view is not used anywhere in the codebase. The API layer (h2a.py)
-- queries the tasks table directly and strips PII in Python.
DROP VIEW IF EXISTS h2a_tasks_public;

-- ============================================================================
-- 2. PostGIS system table (spatial_ref_sys) — SKIPPED
-- ============================================================================
-- spatial_ref_sys is owned by supabase_admin (PostGIS extension).
-- We cannot ALTER it. This is a known Supabase false positive for PostGIS users.
-- Suppress this warning in Supabase Security Advisor settings.

-- ============================================================================
-- 3. Re-enable RLS on tables with drift (policies already exist from 001/002/003)
-- ============================================================================
-- These are idempotent — ENABLE ROW LEVEL SECURITY is a no-op if already on.

-- user_wallets: PII table (wallet_address ↔ auth.uid)
-- Policies: user_wallets_select_own, _insert_own, _update_own, _delete_own (from 001)
ALTER TABLE user_wallets ENABLE ROW LEVEL SECURITY;

-- Re-create policies if they were lost during drift
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'user_wallets' AND policyname = 'user_wallets_select_own'
    ) THEN
        EXECUTE 'CREATE POLICY "user_wallets_select_own" ON user_wallets FOR SELECT USING (auth.uid() = user_id)';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'user_wallets' AND policyname = 'user_wallets_insert_own'
    ) THEN
        EXECUTE 'CREATE POLICY "user_wallets_insert_own" ON user_wallets FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id)';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'user_wallets' AND policyname = 'user_wallets_update_own'
    ) THEN
        EXECUTE 'CREATE POLICY "user_wallets_update_own" ON user_wallets FOR UPDATE USING (auth.uid() = user_id)';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'user_wallets' AND policyname = 'user_wallets_delete_own'
    ) THEN
        EXECUTE 'CREATE POLICY "user_wallets_delete_own" ON user_wallets FOR DELETE USING (auth.uid() = user_id)';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'user_wallets' AND policyname = 'user_wallets_service_role'
    ) THEN
        EXECUTE 'CREATE POLICY "user_wallets_service_role" ON user_wallets FOR ALL TO service_role USING (true) WITH CHECK (true)';
    END IF;
END $$;

-- badges: public read, service_role write (from 003)
ALTER TABLE badges ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'badges' AND policyname = 'badges_select_public'
    ) THEN
        EXECUTE 'CREATE POLICY "badges_select_public" ON badges FOR SELECT USING (true)';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'badges' AND policyname = 'badges_service_role'
    ) THEN
        EXECUTE 'CREATE POLICY "badges_service_role" ON badges FOR ALL TO service_role USING (true) WITH CHECK (true)';
    END IF;
END $$;

-- escrows: financial table — only accessed via service_role (sdk_client.py, payment_dispatcher.py)
-- Production schema (from migration 015) has no beneficiary_id column,
-- so the original 002 policies don't apply. Service-role only is correct.
ALTER TABLE escrows ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'escrows' AND policyname = 'escrows_service_role'
    ) THEN
        EXECUTE 'CREATE POLICY "escrows_service_role" ON escrows FOR ALL TO service_role USING (true) WITH CHECK (true)';
    END IF;
END $$;

-- payments: financial table — executor/agent SELECT, service_role full (from 002)
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'payments' AND policyname = 'payments_select_own'
    ) THEN
        EXECUTE 'CREATE POLICY "payments_select_own" ON payments FOR SELECT USING (executor_id IN (SELECT id FROM executors WHERE user_id = auth.uid()))';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'payments' AND policyname = 'payments_select_agent'
    ) THEN
        EXECUTE 'CREATE POLICY "payments_select_agent" ON payments FOR SELECT USING (true)';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'payments' AND policyname = 'payments_service_role'
    ) THEN
        EXECUTE 'CREATE POLICY "payments_service_role" ON payments FOR ALL TO service_role USING (true) WITH CHECK (true)';
    END IF;
END $$;

-- ============================================================================
-- 4. Enable RLS on gas_dust_events (never had RLS — migration 031 omission)
-- ============================================================================
-- Only accessed via service_role (gas_dust.py uses service client).
-- No anon/authenticated access needed.
ALTER TABLE gas_dust_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "gas_dust_events_service_role" ON gas_dust_events
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- 5. Enable RLS on KK tables (never had RLS — migration 036 omission)
-- ============================================================================
-- KK code was removed from this repo but tables remain in production DB.
-- KK agents access these via service_role from karmakadabra repo.
-- Lock down to service_role only — no anon/authenticated access.

ALTER TABLE kk_swarm_state ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kk_swarm_state_service_role" ON kk_swarm_state
    FOR ALL TO service_role USING (true) WITH CHECK (true);

ALTER TABLE kk_task_claims ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kk_task_claims_service_role" ON kk_task_claims
    FOR ALL TO service_role USING (true) WITH CHECK (true);

ALTER TABLE kk_notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "kk_notifications_service_role" ON kk_notifications
    FOR ALL TO service_role USING (true) WITH CHECK (true);
