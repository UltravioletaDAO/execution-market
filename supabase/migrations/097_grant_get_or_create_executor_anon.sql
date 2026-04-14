-- Migration 097: Grant EXECUTE on get_or_create_executor to anon and authenticated
-- The function was only granted to postgres + service_role (migration 092 revoked too broadly).
-- Browser clients (anon/authenticated) need this to resolve executor identity on login.

GRANT EXECUTE ON FUNCTION get_or_create_executor(text, text, text, text, text)
  TO anon, authenticated;
