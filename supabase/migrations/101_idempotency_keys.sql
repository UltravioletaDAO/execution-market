-- Migration 101: Idempotency-Key storage for state-mutating endpoints (Task 4.5).
--
-- Problem this solves:
--   Retry-on-5xx/429 is a normal client pattern, but without server-side
--   dedup a retried POST /submissions/{id}/approve can settle the same
--   bounty twice (or worse, double-fire fee splits and treasury top-ups).
--   We already have a narrow guard on /tasks via `tasks.idempotency_key`
--   (migration 20260412000001) — this migration generalises the pattern
--   across all money-moving endpoints.
--
-- Keying strategy:
--   The middleware runs BEFORE FastAPI dependency-injection, so it
--   cannot know `agent_id` at the moment it needs to short-circuit a
--   retry. Instead we key on `(key, auth_scope_hash)` where
--   `auth_scope_hash = SHA-256(Authorization header value)`. This has
--   the useful property that the same Idempotency-Key string submitted
--   by two different clients will never collide — each client's bearer
--   token hashes to a different scope.
--
--   `agent_id` is still stored (populated by the backend after auth
--   runs) so dashboards and analytics can correlate cache hits to an
--   agent without replaying the auth flow.
--
-- Semantics:
--   Client sends `Idempotency-Key: <uuid>` on a POST to an allowlisted
--   endpoint. The middleware inspects this table up-front:
--     1) No row                       → process normally, cache response.
--     2) Row exists, hash matches     → return cached response as-is.
--     3) Row exists, hash DIFFERS     → HTTP 409 with
--                                        "idempotency_key_conflict"
--                                        (prevents replay with a
--                                        mutated body).
--
--   Cached responses live 24 hours then get garbage-collected by the
--   helper function below. Retention is operational policy, not
--   correctness — a cron/job calls `prune_idempotency_keys()`.
--
-- Idempotent: uses IF NOT EXISTS everywhere. Safe to re-run.

CREATE TABLE IF NOT EXISTS idempotency_keys (
    key               VARCHAR(255) NOT NULL,
    auth_scope_hash   CHAR(64)     NOT NULL, -- SHA-256 hex of Authorization header
    agent_id          VARCHAR(255),          -- filled post-auth, for analytics only
    request_hash      CHAR(64)     NOT NULL, -- SHA-256 hex of (method || path || body)
    response_status   INTEGER      NOT NULL,
    response_body     JSONB        NOT NULL,
    method            VARCHAR(16)  NOT NULL,
    path              VARCHAR(512) NOT NULL,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (key, auth_scope_hash)
);

COMMENT ON TABLE idempotency_keys IS
    'Cache of responses for state-mutating endpoints, keyed by client-supplied Idempotency-Key + SHA-256 of Authorization. Middleware consults this before handling a POST to prevent double-execution on retry. See Task 4.5 in MASTER_PLAN_SAAS_PRODUCTION_HARDENING.';

COMMENT ON COLUMN idempotency_keys.request_hash IS
    'SHA-256 hex of canonicalised (method + path + body). Used to detect reuse of the same key with a different payload (returns HTTP 409).';

COMMENT ON COLUMN idempotency_keys.response_body IS
    'Serialised JSON response — used verbatim for cache hits. NULL-safe: endpoints that return no body store {} here.';

COMMENT ON COLUMN idempotency_keys.agent_id IS
    'Populated after auth runs; used for analytics / audit only. NOT part of the lookup key (see auth_scope_hash).';

-- Cleanup index: lookups by created_at for the daily GC job.
CREATE INDEX IF NOT EXISTS idx_idempotency_keys_created_at
    ON idempotency_keys (created_at);

-- Analytics index: let dashboards group by agent without a seq-scan.
CREATE INDEX IF NOT EXISTS idx_idempotency_keys_agent_id
    ON idempotency_keys (agent_id) WHERE agent_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- RLS policy — service role only
-- ---------------------------------------------------------------------------
-- This table is written from the FastAPI backend with the service role.
-- No user should ever read it directly via PostgREST.
ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "idempotency_keys_service_only" ON idempotency_keys;
CREATE POLICY "idempotency_keys_service_only" ON idempotency_keys
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- Helper: prune entries older than 24 hours
-- ---------------------------------------------------------------------------
-- Callers can `SELECT prune_idempotency_keys();` from a cron or the app
-- startup sweep. Returns the number of rows deleted so the caller can
-- emit a metric / log line.
CREATE OR REPLACE FUNCTION prune_idempotency_keys(
    retention_hours INTEGER DEFAULT 24
) RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM idempotency_keys
     WHERE created_at < NOW() - (retention_hours || ' hours')::INTERVAL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION prune_idempotency_keys(INTEGER) IS
    'Delete idempotency cache rows older than retention_hours (default 24). Returns deleted row count.';
