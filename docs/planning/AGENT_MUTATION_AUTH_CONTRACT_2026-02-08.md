# Agent Mutation Auth Contract - 2026-02-08

## Objective

Define a single, operable auth contract for dashboard agent mutations so API-first rollout can be enforced safely in production.

## Scope

Mutations covered:
- create task
- cancel task
- assign task
- approve submission
- reject submission
- request more info

Files:
- `dashboard/src/services/tasks.ts`
- `dashboard/src/services/submissions.ts`
- `mcp_server/api/routes.py`

## Current implementation state

1. API-first paths exist for all listed mutations.
2. API-first uses `X-API-Key` from `VITE_API_KEY`.
3. Transitional direct fallback still exists for environments without API key.
4. New guardrail flag added:
- `VITE_REQUIRE_AGENT_API_KEY=true`

Behavior:
- if `VITE_REQUIRE_AGENT_API_KEY=true` and `VITE_API_KEY` is missing, mutation throws (unless direct fallback is explicitly allowed via `VITE_ALLOW_DIRECT_SUPABASE_MUTATIONS=true`).

## Environment policy

Recommended production/beta policy:
- `VITE_REQUIRE_AGENT_API_KEY=true`
- `VITE_ALLOW_DIRECT_SUPABASE_MUTATIONS=false`
- `VITE_API_KEY=<agent_api_key>`

Local/dev troubleshooting policy:
- `VITE_REQUIRE_AGENT_API_KEY=false`
- `VITE_ALLOW_DIRECT_SUPABASE_MUTATIONS=true` (only when debugging)

## Remaining gap

Long-term contract should not depend on static frontend API keys.

Next hardening target:
1. Add backend support for wallet/JWT-bound agent auth on mutation endpoints.
2. Remove direct Supabase fallback from production builds.
3. Keep API key flow as compatibility mode only for server-to-server integrations.

