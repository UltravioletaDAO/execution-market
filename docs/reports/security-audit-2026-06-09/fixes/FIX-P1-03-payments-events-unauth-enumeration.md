---
date: 2026-06-09
tags: [type/incident, domain/security]
status: active
severity: P1
finding_id: FIX-P1-03
---
# FIX-P1-03 — Unauthenticated financial enumeration on GET /payments/events (RLS bypass + PostgREST filter injection)

## Summary
`GET /api/v1/payments/events?address=<wallet>` (`get_payment_events` in `mcp_server/api/routers/workers.py`) has **no auth dependency and no ownership check**. It runs its query with the Supabase **service-role** client, which bypasses Row Level Security, so it returns the full payment-event history (tx hashes, counterparties, amounts, internal `metadata` JSONB, computed `total_earned_usdc`) for **any** wallet to **any** anonymous caller. The RLS policies added specifically to protect this table (migration 027 = service-role only; migration 045 = authenticated-worker-own-tasks only) are silently defeated. A secondary defect — the raw `address` string is interpolated into a PostgREST `.or_(...)` filter — allows filter/wildcard injection that can broaden a single-wallet lookup into a multi-wallet (potentially whole-table) dump.

## Severity & Impact (why P1)
- **Broken object-level authorization / unauthenticated information disclosure** of other users' financial data via an endpoint that the team explicitly protected with RLS. This is industry-standard **High**.
- **Data at risk** (per wallet, no credentials): `task_id` (platform↔task linkage), `event_type`, `tx_hash`, `from_address`/`to_address`, `amount_usdc`, `network`, the full raw `metadata` JSONB (internal operational fields written by the payment dispatcher — e.g. `mode`, `tier`, escrow/release context, `executor_id`, `reason`), and platform-scoped aggregates `total_earned_usdc` + `earning_count`.
- **Honest scoping note:** the raw on-chain primitives (tx hashes, counterparty wallets, amounts, networks) for USDC transfers are already **publicly visible on any block explorer** once you know a wallet. The genuinely-novel, non-public exposure here is: (a) the **platform/task linkage** (`task_id`), (b) the **internal operational `metadata` JSONB**, (c) the **platform-scoped aggregation** (`total_earned`/`earning_count`), and (d) — combined with the public leaderboard→identity chain — **attribution of earnings to named executors**. That non-public delta plus the unauthenticated RLS bypass and trivial enumeration keeps it at **P1**.
- **Amplifier:** the PostgREST filter-injection vector (see Root cause #2) can turn a one-wallet read into a bulk dump, materially increasing blast radius.
- **No compensating control:** there is no WAF rule for `/payments` or `/api/v1` (REST API is served via ALB `api.execution.market`, not the CloudFront WAF), and there is no global auth middleware on the app.

## Affected code (exact file:line references)
- `mcp_server/api/routers/workers.py:945-1046` — `get_payment_events` route.
  - **No auth Depends** in the signature (only `Query` params):
    ```python
    @router.get("/payments/events", response_model=None, ...)
    async def get_payment_events(
        address: str = Query(..., min_length=10, max_length=128),
        since: Optional[str] = Query(None),
        limit: int = Query(20, ge=1, le=100),
        event_type: Optional[str] = Query(None, alias="event_type"),
    ) -> Dict[str, Any]:
    ```
  - **Line 974-976:** `addr = address.strip().lower()` then `client = db.get_client()` (service role).
  - **Line 983 (filter injection):** `.or_(f"from_address.ilike.{addr},to_address.ilike.{addr}")` — raw, un-validated interpolation of caller-supplied `addr` into a PostgREST filter string. `min_length=10` allows commas/`*` wildcards.
  - **Line 982:** `.select("*")` — returns every column.
  - **Line 1022:** `"metadata": row.get("metadata")` — raw internal JSONB leaked to client.
  - **Lines 1028-1046:** computes and returns `total_earned_usdc` / `earning_count` for the arbitrary address.
- `mcp_server/supabase_client.py:28-60` — `_get_client()` uses `SUPABASE_SERVICE_ROLE_KEY` (service role → **bypasses RLS**).
- `supabase/migrations/027_payment_events.sql:31-40` — RLS enabled, **service-role-only** policy (no anon/authenticated read).
- `supabase/migrations/045_payment_events_worker_read_policy.sql:6-18` — authenticated workers may read **only** events for tasks where they are the assigned executor (`auth.uid()` scoped). Both policies are bypassed because the endpoint uses the service-role client.
- `mcp_server/api/auth.py:798-940` — `verify_worker_auth` returns `Optional[WorkerAuth]` and returns **`None` (not 401)** when `EM_REQUIRE_WORKER_AUTH=false` (the default). **Merely adding `Depends(verify_worker_auth)` does NOT enforce auth.**
- `mcp_server/api/auth.py:96-167` — `verify_api_key` (validates `X-API-Key` / `Bearer`), only meaningful when `EM_API_KEYS_ENABLED=true`.

### First-party callers (backward-compat surface — verified)
- `xmtp-bot/src/commands/earnings.ts:26-32` — the **only** first-party runtime caller. Calls `GET /api/v1/payments/events?address=<senderAddress>&event_type=disburse_worker&limit=50`, where `senderAddress` is always the **requesting user's own wallet**. The bot's `apiClient` (`xmtp-bot/src/services/api-client.ts:13-17`) always sends an `X-API-Key` header but **no Supabase JWT**.
- `em-plugin-sdk/em_plugin_sdk/resources/payments.py:30-41` — external SDK helper `events(wallet_address, ...)`.
- **The web dashboard does NOT call this endpoint.** Worker earnings in the dashboard come from `dashboard/src/hooks/useProfile.ts` (direct, RLS-scoped Supabase reads of `submissions`/`tasks`), and per-task payment timelines come from `dashboard/src/hooks/useTaskPayment.ts`. So the web app is unaffected by tightening this endpoint.

## Root cause
Two compounding defects:

1. **Missing authorization on a service-role read.** The handler has no auth dependency and no ownership filter, yet it queries via the service-role client (`db.get_client()`), which is exactly the client that bypasses RLS. The migration-027/045 RLS that is supposed to be the security boundary never runs for this request, so the **in-code filter is the only boundary — and there is none**. This is broken object-level authorization (BOLA/IDOR).

2. **Untrusted input interpolated into a PostgREST filter.** `addr` is placed verbatim into `.or_(f"from_address.ilike.{addr},to_address.ilike.{addr}")`. PostgREST treats `,` as a filter separator and `*` as an `ilike` wildcard. A crafted `address` (length 10–128 passes the `Query` bounds) can inject extra OR conditions / wildcards and broaden the result set well beyond one wallet — up to a whole-table dump. Strict format validation is mandatory **even after** adding the ownership check.

## Exploit scenario
1. Attacker obtains a target wallet (public leaderboard→identity chain, a block explorer, or any showcase/task data).
2. Attacker runs, with **no credentials**:
   `curl "https://api.execution.market/api/v1/payments/events?address=0xVICTIM&limit=100"`
3. Server returns every payment event touching that wallet, the raw internal `metadata`, and `total_earned_usdc`.
4. Attacker pages with `since`/`event_type` to harvest the wallet's full financial history, and repeats across every wallet enumerated from the leaderboard.
5. **Amplification:** attacker sends a crafted `address` containing PostgREST control characters (e.g. a value embedding `*` wildcards / extra `,`-separated conditions) to broaden the `.or_()` filter and dump events for many wallets in one call.

## The Fix (code-level)

### Design
Make the endpoint **deny-by-default** with a strict allowlist:
1. **Strictly validate** `address` format up front (EVM `^0x[0-9a-fA-F]{40}$` or Solana base58 32–44 chars). Reject anything else with 400. This closes the PostgREST injection vector regardless of auth.
2. **Require an authenticated, authorized caller**, via one of two paths:
   - **Worker JWT path:** `worker_auth` present (Supabase JWT → `executor_id` → `executors.wallet_address`); the requested `address` MUST equal the caller's own wallet (case-insensitive), else **403**.
   - **Internal/service path:** a **valid** `X-API-Key` (only when `EM_API_KEYS_ENABLED=true`) — this is the XMTP bot. Internal callers may query any wallet (they already act on behalf of the message sender). This preserves the only first-party integration.
   - If **neither** path authorizes the request → **401** (no anonymous access).
3. **Build the PostgREST filter from the validated address**, never the raw input.
4. **Whitelist response fields** — stop returning raw `metadata`.
5. Compute `total_earned`/`earning_count` only for the (now validated, owned-or-internal) address — already implied by the above.

This is **flag-gated for safe rollout** via a new env var `EM_ENFORCE_PAYMENT_EVENTS_AUTH` (default **`true`** — secure by default; operators can flip to `false` for an emergency rollback without redeploy). The strict address-format validation is **always on** (it has no legitimate-caller downside and is the injection fix).

### File 1 — `mcp_server/api/routers/workers.py`

**(a) Add imports/helpers near the top of the payment-events section (after line ~942).**

```python
import os
import re
from ..auth import verify_api_key  # validates X-API-Key / Bearer (internal callers)

# Strict address validators — close the PostgREST .or_() injection vector.
_EVM_ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
_SOLANA_ADDR_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")  # base58, no 0/O/I/l

def _is_valid_wallet(addr: str) -> bool:
    return bool(_EVM_ADDR_RE.match(addr) or _SOLANA_ADDR_RE.match(addr))

# Secure by default. Set to "false" ONLY as an emergency rollback (re-opens the leak).
_ENFORCE_PAYMENT_EVENTS_AUTH = (
    os.environ.get("EM_ENFORCE_PAYMENT_EVENTS_AUTH", "true").lower() == "true"
)
```

> Note: `verify_api_key` raises `HTTPException(401)` on a bad key. We do **not** want a bad key to hard-fail the worker-JWT path, so we call it defensively (see below) — mirroring the `verify_api_key_optional` pattern at `auth.py:170-185`.

**(b) Replace the handler signature (lines 955-972)** to inject `Request`, the optional worker JWT, and the raw header values so we can attempt internal-key auth without forcing it:

```python
async def get_payment_events(
    raw_request: Request,
    address: str = Query(
        ...,
        description="Wallet address to filter by (matches from_address or to_address)",
        min_length=32,
        max_length=64,
    ),
    since: Optional[str] = Query(
        None,
        description="ISO 8601 timestamp — only return events after this time",
    ),
    limit: int = Query(20, description="Max events to return", ge=1, le=100),
    event_type: Optional[str] = Query(
        None,
        description="Filter by event type (e.g. disburse_worker, settle, escrow_release)",
        alias="event_type",
    ),
    worker_auth: Optional[WorkerAuth] = Depends(verify_worker_auth),
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Dict[str, Any]:
    """Return payment events where *address* appears as sender or receiver.

    AuthZ: caller must either (a) be the worker who owns *address* (Supabase JWT),
    or (b) present a valid internal API key (X-API-Key / Bearer). Anonymous and
    cross-wallet requests are rejected. The address is strictly format-validated
    to prevent PostgREST filter injection.
    """
    addr = address.strip().lower()

    # 1) Strict format validation — ALWAYS enforced (injection fix).
    if not _is_valid_wallet(addr):
        raise HTTPException(status_code=400, detail="Invalid wallet address format")
```

> `Header` and `Request` must be imported from `fastapi` — `Header` is **not** currently imported in this module; add it to the existing `from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request` line → add `Header`. `Request` is already imported.

**(c) Insert the authorization block immediately after the format check, before `client = db.get_client()` (replacing old lines 974-976):**

```python
    # 2) AuthZ — deny by default.
    if _ENFORCE_PAYMENT_EVENTS_AUTH:
        authorized = False

        # Path A: worker JWT must own the requested wallet (case-insensitive).
        if worker_auth and worker_auth.executor_id:
            owner_wallet = (worker_auth.wallet_address or "").strip().lower()
            if not owner_wallet:
                # JWT didn't carry a wallet — resolve from executors table.
                try:
                    _row = (
                        db.get_client()
                        .table("executors")
                        .select("wallet_address")
                        .eq("id", worker_auth.executor_id)
                        .limit(1)
                        .execute()
                    )
                    owner_wallet = (
                        (_row.data[0].get("wallet_address") or "").strip().lower()
                        if _row.data
                        else ""
                    )
                except Exception:
                    owner_wallet = ""
            if owner_wallet and owner_wallet == addr:
                authorized = True
            else:
                logger.warning(
                    "SECURITY_AUDIT action=payment_events.ownership_mismatch "
                    "executor=%s requested=%s path=%s",
                    worker_auth.executor_id[:8],
                    truncate_wallet(addr),
                    raw_request.url.path,
                )
                raise HTTPException(
                    status_code=403,
                    detail="You may only view payment events for your own wallet",
                )

        # Path B: internal/service caller (e.g. XMTP bot) with a valid API key.
        if not authorized and (authorization or x_api_key):
            try:
                await verify_api_key(authorization, x_api_key)
                authorized = True
            except HTTPException:
                authorized = False  # invalid key — fall through to 401

        if not authorized:
            logger.warning(
                "SECURITY_AUDIT action=payment_events.unauthenticated "
                "requested=%s path=%s",
                truncate_wallet(addr),
                raw_request.url.path,
            )
            raise HTTPException(
                status_code=401,
                detail="Authentication required to view payment events",
                headers={"WWW-Authenticate": "Bearer"},
            )

    client = db.get_client()
```

**(d) Build the filter from the validated `addr` (already done — `addr` is now guaranteed to match `^0x[0-9a-fA-F]{40}$` or base58, so it cannot contain `,` or `*`). Keep line 983 as-is** but it is now injection-safe because of step (1). No change needed to the `.or_(...)` line itself.

**(e) Whitelist response fields — drop raw `metadata` (replace lines 1006-1024):**

```python
    events: List[Dict[str, Any]] = []
    for row in rows:
        events.append(
            {
                "id": row.get("id"),
                "task_id": row.get("task_id"),
                "event_type": row.get("event_type"),
                "status": row.get("status"),
                "tx_hash": row.get("tx_hash"),
                "from_address": row.get("from_address"),
                "to_address": row.get("to_address"),
                "amount": row.get("amount_usdc"),
                "amount_usdc": row.get("amount_usdc"),
                "network": row.get("network"),
                "payment_network": row.get("network"),
                "token": row.get("token", "USDC"),
                "created_at": row.get("created_at"),
                # NOTE: raw `metadata` JSONB intentionally NOT returned (FIX-P1-03).
            }
        )
```

The XMTP bot (`earnings.ts`) only reads `amount`, `chain`/`payment_network`, and `created_at` — all still present. No client field is broken by dropping `metadata`.

> **`min_length` change:** the old `min_length=10` is part of the injection surface. New bounds `min_length=32, max_length=64` comfortably fit both EVM (42) and Solana (32–44) and reject the tiny crafted-prefix payloads early, but the regex in step (1) is the real guard.

### File 2 — Database (defense-in-depth; RLS stays the backstop)
**No schema change is required** to fix the endpoint — the security boundary is now the in-code ownership/internal-auth check, and the strict format validation. Migrations 027 (service-role-only) and 045 (authenticated-worker-own-tasks) **remain in place** and are correct; do not weaken them.

Add a **belt-and-suspenders revoke** so no future code path can `SELECT` this table as `anon`/`authenticated` outside the migration-045 policy. This is the next free migration number (**111** — verified `111*` does not exist; current max is `110_moonpay_onramp_attempts.sql`).

`supabase/migrations/111_payment_events_revoke_anon.sql`:
```sql
-- Migration 111: Defense-in-depth for payment_events (FIX-P1-03)
-- The REST endpoint GET /api/v1/payments/events previously read this table via
-- the service-role client with no ownership check, bypassing RLS. The code fix
-- adds ownership/internal-auth enforcement; this migration ensures the table can
-- never be read by anon/authenticated roles except through the migration-045
-- own-tasks policy. RLS remains ENABLED (migration 027).

-- Ensure RLS is on (idempotent).
ALTER TABLE payment_events ENABLE ROW LEVEL SECURITY;

-- Remove any direct table grants to anon/authenticated; RLS policies (045) are
-- the only sanctioned read path for non-service roles.
REVOKE ALL ON TABLE payment_events FROM anon;
REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE payment_events FROM authenticated;

-- (Migration 045 GRANT/POLICY for authenticated SELECT on own-task rows is kept.)
-- Re-grant ONLY the SELECT needed for the migration-045 policy to function.
GRANT SELECT ON TABLE payment_events TO authenticated;

COMMENT ON TABLE payment_events IS
    'Audit trail for payment ops. Non-service reads MUST go through the '
    'migration-045 own-tasks RLS policy. REST reads are ownership-checked in '
    'api/routers/workers.py:get_payment_events (FIX-P1-03).';
```

**Standalone idempotent production hotfix** (paste into Supabase SQL editor — safe to run repeatedly):
```sql
DO $$
BEGIN
    EXECUTE 'ALTER TABLE payment_events ENABLE ROW LEVEL SECURITY';
    EXECUTE 'REVOKE ALL ON TABLE payment_events FROM anon';
    EXECUTE 'REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE payment_events FROM authenticated';
    EXECUTE 'GRANT SELECT ON TABLE payment_events TO authenticated';
END $$;
```
> This migration is **defense-in-depth only**. The real fix is the code change in File 1; do not rely on the migration alone, because the endpoint uses the service-role client, which bypasses RLS by design.

### Feature flag / env var
- **Name:** `EM_ENFORCE_PAYMENT_EVENTS_AUTH`
- **Safe default:** `true` (deny-by-default; the secure state).
- **Purpose:** emergency kill-switch to revert auth enforcement without a redeploy if an unforeseen legitimate caller breaks. The strict address-format validation (injection fix) is **always on** and is not gated.
- **ECS task-definition update:** add to the MCP service container `environment`:
  ```json
  { "name": "EM_ENFORCE_PAYMENT_EVENTS_AUTH", "value": "true" }
  ```
  (Use the `deploy-mcp` skill / `aws ecs register-task-definition` + `update-service --force-new-deployment`. No secret involved — plain env var.)

### Backward-compatibility risk & safe rollout
- **Web dashboard:** unaffected — it does not call this endpoint (earnings via `useProfile.ts` / `useTaskPayment.ts`, both RLS-scoped Supabase reads).
- **XMTP bot (`/earnings`):** preserved via **Path B** (valid `X-API-Key`). **Action required:** the bot's `X-API-Key` is only validated when `EM_API_KEYS_ENABLED=true`. Verify that flag's state in ECS:
  - If `EM_API_KEYS_ENABLED=true` already → bot continues working with no change.
  - If `EM_API_KEYS_ENABLED=false` → `verify_api_key` will reject the bot's key and `/earnings` would 401. **Mitigation options (pick one before enabling enforcement):** (i) flip `EM_API_KEYS_ENABLED=true` and ensure the bot's key is provisioned in the `api_keys` table; or (ii) have the bot pass the message-sender's Supabase JWT and use Path A; or (iii) stage the rollout with `EM_ENFORCE_PAYMENT_EVENTS_AUTH=false` until the bot's auth is confirmed, then flip to `true`.
- **em-plugin-sdk:** external callers must now present a JWT (own wallet) or a valid API key. This is the intended hardening; document it in the SDK changelog.
- **Staged rollout:** deploy with `EM_ENFORCE_PAYMENT_EVENTS_AUTH=true` to **staging** first, run the XMTP `/earnings` smoke test against staging, then promote to prod. Keep the flag handy as instant rollback. The address-format 400 is always on but only rejects malformed input, which no legitimate caller sends.

## Test plan
Add `mcp_server/tests/test_payment_events_authz.py` (markers: `security`, `payments`). Use the minimal-app + `dependency_overrides` pattern from `tests/test_escrow_refund_ownership.py:68-77`.

**Harness sketch:**
```python
import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

OWNER_WALLET = "0x" + "ab" * 20            # 42-char EVM
OTHER_WALLET = "0x" + "cd" * 20

def _app(worker_auth=None):
    from api.routers.workers import router
    from api.auth import verify_worker_auth
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[verify_worker_auth] = lambda: worker_auth
    return app

@pytest.fixture(autouse=True)
def _enforce_on(monkeypatch):
    monkeypatch.setenv("EM_ENFORCE_PAYMENT_EVENTS_AUTH", "true")
    # reload module flag if it is read at import time
    import importlib, api.routers.workers as w
    importlib.reload(w)
    yield
```

**Tests to add (each asserts a specific control):**
1. `test_anonymous_request_rejected` — **reproduces the bug.** No auth, `GET /api/v1/payments/events?address=0x...OTHER` → **401**. (Before the fix this returns 200 with data.)
2. `test_worker_cannot_query_other_wallet` — `worker_auth` owns `OWNER_WALLET`, request `address=OTHER_WALLET` → **403**.
3. `test_worker_can_query_own_wallet` — `worker_auth.wallet_address == OWNER_WALLET`, request `address=OWNER_WALLET` → **200**; patch `supabase_client.get_client` to return a fake client yielding 1 row; assert `metadata` is **absent** from each event and `events`/`total_earned_usdc` present.
4. `test_internal_api_key_allowed_cross_wallet` — no worker JWT; patch `api.routers.workers.verify_api_key` to return a valid `APIKeyData`; request any wallet → **200**.
5. `test_invalid_api_key_falls_through_to_401` — patch `verify_api_key` to raise `HTTPException(401)`; no worker JWT → **401**.
6. `test_malformed_address_rejected` — `address="0x*,from_address.ilike.*"` (injection payload, length within 32–64) → **400** (`Invalid wallet address format`). Also test `address="not-a-wallet-but-32-chars-long-xx"` → 400. **This proves the PostgREST injection vector is closed.**
7. `test_solana_address_accepted_format` — a valid base58 32–44 char address passes format validation (reaches auth, not 400).
8. `test_metadata_not_leaked` — explicit assertion that no returned event dict contains the key `"metadata"` (regression guard for field whitelist).
9. `test_enforcement_flag_off_is_legacy` (optional) — with `EM_ENFORCE_PAYMENT_EVENTS_AUTH=false`, anonymous request is allowed (documents the kill-switch) **but** malformed address still returns 400 (format check always on).

**Manual / E2E verification (staging, then prod):**
1. `curl "https://<staging>/api/v1/payments/events?address=0x<any-wallet>"` (no auth) → **401**. (Pre-fix: 200 + data.)
2. `curl "https://<staging>/api/v1/payments/events?address=0x%2A%2Cfrom_address.ilike.%2A"` (URL-encoded injection) → **400**.
3. With a worker JWT for wallet A: query A → 200; query B → 403.
4. With the XMTP bot's `X-API-Key`: query any wallet → 200 (confirms `/earnings` still works). Run the bot `/earnings` command end-to-end in staging.
5. Confirm the bot output still renders amounts/chain/date (no reliance on `metadata`).

## Rollback plan
1. **Instant (no redeploy):** set ECS env `EM_ENFORCE_PAYMENT_EVENTS_AUTH=false` and force a new deployment — reverts auth enforcement while keeping the (harmless) format validation. Use only if a legitimate caller is broken and cannot be fixed quickly. (Note: this re-opens the data leak; treat as temporary.)
2. **Code rollback:** revert the `workers.py` commit. The migration-111 grant changes are independent and safe to keep; if they must be reverted, re-grant prior privileges (migration 045 already granted `authenticated` SELECT, so functionally no loss). Migrations 027/045 are untouched by this fix.
3. The migration is additive/idempotent; re-running the standalone hotfix block is safe.

## Verification checklist
- [ ] `get_payment_events` signature now includes `Request`, `Depends(verify_worker_auth)`, and `X-API-Key`/`Authorization` headers; `Header` imported from `fastapi`.
- [ ] Strict address regex (EVM `^0x[0-9a-fA-F]{40}$` or Solana base58) enforced **before** any DB access; malformed input → 400.
- [ ] Worker-JWT path: ownership equality (case-insensitive) enforced; mismatch → 403.
- [ ] Internal-key path: valid `X-API-Key`/`Bearer` allowed; invalid/absent (with no JWT) → 401.
- [ ] `.or_(...)` filter is built only from the validated `addr` (no raw, un-validated interpolation reachable).
- [ ] Raw `metadata` JSONB removed from the response payload.
- [ ] `total_earned_usdc`/`earning_count` only computed for the authorized address.
- [ ] `EM_ENFORCE_PAYMENT_EVENTS_AUTH` added to ECS task definition with value `true`.
- [ ] `EM_API_KEYS_ENABLED` state confirmed in ECS; XMTP bot `/earnings` verified working in staging.
- [ ] Migration `111_payment_events_revoke_anon.sql` added; standalone hotfix applied to prod DB; RLS still ENABLED.
- [ ] New test file `test_payment_events_authz.py` added; tests 1–8 pass; test 1 fails on the pre-fix code (bug reproduced) and passes after.
- [ ] `pytest -m "security or payments"` green.
- [ ] Web dashboard earnings/profile pages unaffected (no call to this endpoint).
- [ ] Staged rollout to staging completed before prod; rollback flag verified working.
