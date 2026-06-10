-- Migration 118: re-grant EXECUTE on the RLS helper current_executor_ids()
--
-- WHY: Migration 113 (P1-05 lockdown) dynamically revokes anon/authenticated
-- EXECUTE on every SECURITY DEFINER function in public. That sweep is correct
-- for money/state RPCs, but it also caught current_executor_ids() — a pure
-- STABLE read helper (`SELECT id FROM executors WHERE user_id = auth.uid()`)
-- that the tasks RLS SELECT policy evaluates for EVERY caller. Revoking it
-- broke anonymous task browsing in production on 2026-06-09: PostgREST
-- returned 401 `42501 permission denied for function current_executor_ids`
-- for the dashboard's public task list query.
--
-- For anon callers auth.uid() is NULL, so the helper returns an empty set —
-- granting EXECUTE leaks nothing. It must stay executable by both API roles
-- for the RLS policies that reference it to evaluate at all.
--
-- Idempotent: GRANT is safe to re-run. Keep this migration AFTER 113 so the
-- lockdown-then-regrant order is preserved on fresh databases.

GRANT EXECUTE ON FUNCTION public.current_executor_ids() TO anon, authenticated;

-- Verification (expect: t, t)
SELECT
    has_function_privilege('anon', 'public.current_executor_ids()', 'EXECUTE') AS anon_can_execute,
    has_function_privilege('authenticated', 'public.current_executor_ids()', 'EXECUTE') AS authenticated_can_execute;
