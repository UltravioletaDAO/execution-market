---
date: 2026-06-09
tags: [type/incident, domain/security]
status: active
severity: P0
finding_id: FIX-P0-02
---
# FIX-P0-02 — Migration 097 re-granted `get_or_create_executor` to anon, reopening DB-001 cross-account takeover (executor identity rebind)

## Summary (2-3 sentences)
Migration `097_grant_get_or_create_executor_anon.sql` re-granted `EXECUTE` on the SECURITY DEFINER RPC `get_or_create_executor(text,text,text,text,text)` to `anon` and `authenticated`, undoing the DB-001 lockdown that migration 092 had applied. Because the function unconditionally rebinds an existing executor row to the caller's `auth.uid()` (`UPDATE executors SET user_id = COALESCE(v_user_id, executors.user_id)` in `090_fix_ambiguous_column_rpc.sql:125`) and matches solely on the caller-supplied `p_wallet_address` (with `p_signature` accepted but never verified), any visitor holding the public anon JWT can take over any executor account and redirect future payouts. The fix is a NEW forward migration (111) that re-REVOKEs from `PUBLIC`/`anon`/`authenticated` and re-GRANTs only `service_role`, PLUS a hardening of the function body so it never overwrites a non-NULL `user_id` belonging to a different session (defense-in-depth that also protects the service_role backend path).

## Severity & Impact (why P0; what funds/data are at risk)
P0 — full cross-account takeover, exploitable **right now** with only the public Supabase anon key, no privileged credentials required.

The dashboard establishes a real authenticated Supabase session for **every** visitor via `supabase.auth.signInAnonymously()` (`dashboard/src/context/AuthContext.tsx:147`). Supabase anonymous sign-in returns `role=authenticated` with a non-NULL `auth.uid()`, so the migration-097 grant (`TO anon, authenticated`) applies to every browser. The entire RLS trust model derives identity from `executors.user_id = auth.uid()` via the helper functions `current_executor_id()`, `current_executor_ids()`, `current_wallet_addresses()` (`054_rls_performance_helpers.sql:12,25,37`).

After an attacker calls the RPC with a victim wallet, their session **owns** the victim's executor for all RLS checks:
- **Read** the victim's `payments` (`payments_select_own`), `submissions`/evidence (`submissions_select_own`), `escrows` (`escrows_select_executor`), `withdrawals`, `disputes` (`disputes_select_participant_real`), `moonpay_transactions`, and `world_id_verifications` rows.
- **Write/redirect funds**: PATCH the victim's executor via `executors_update_own` to overwrite `wallet_address`, redirecting future payouts and withdrawals to the attacker's wallet.
- **Detach** the victim from their own account (their `user_id` no longer matches the row).

This is simultaneously an authentication bypass (own any executor for all RLS checks) and a realistic fund-redirection vector. Migration 092's own header classified this exact path as **CRITICAL DB-001**.

## Affected code (exact file:line references, with short redacted quotes)
- `supabase/migrations/097_grant_get_or_create_executor_anon.sql:5-6` — the reopening grant:
  ```sql
  GRANT EXECUTE ON FUNCTION get_or_create_executor(text, text, text, text, text)
    TO anon, authenticated;
  ```
- `supabase/migrations/090_fix_ambiguous_column_rpc.sql:42` — `v_user_id := auth.uid();`
- `supabase/migrations/090_fix_ambiguous_column_rpc.sql:120-127` — the unconditional rebind in the existing-executor branch:
  ```sql
  ELSE
      -- Update existing executor: always bind to current session user_id
      UPDATE executors
      SET
          last_active_at = NOW(),
          user_id = COALESCE(v_user_id, executors.user_id),   -- <-- DB-001: overwrites prior owner
          email = COALESCE(executors.email, p_email)
      WHERE executors.id = v_executor_id;
  ```
- `supabase/migrations/090_fix_ambiguous_column_rpc.sql:98-107,130-140` — `p_signature` is only **stored** into `user_wallets.signature_hash`, never cryptographically validated against `p_wallet_address`.
- `supabase/migrations/092_revoke_anon_rpcs.sql:109-125` — the DB-001 lockdown that 097 undid (`_092_safe_revoke_and_grant('public.get_or_create_executor(text, text, text, text, text)')`).
- `supabase/migrations/054_rls_performance_helpers.sql:12,25,37` — RLS identity derivation (`WHERE user_id = auth.uid()`).
- `dashboard/src/context/AuthContext.tsx:147` — `supabase.auth.signInAnonymously()` gives every visitor a non-NULL `auth.uid()`.
- `dashboard/src/context/AuthContext.tsx:209-213` — the live browser call (`supabase.rpc('get_or_create_executor', {...})`), which omits `p_signature` entirely.
- `dashboard/src/hooks/useProfileUpdate.ts:52` — a second browser caller of the same RPC.
- `mcp_server/api/routers/workers.py:99-106` — the **service_role** backend caller (`db.get_client()` uses `SUPABASE_SERVICE_ROLE_KEY`, confirmed in `mcp_server/supabase_client.py:29-44`). This path is the intended GR-1.7 trust boundary and must keep working after the revoke.

## Root cause (the real underlying defect)
Two compounding defects:

1. **Grant defect (migration 097):** The RPC was re-exposed to the browser. PostgREST publishes any function granted to `anon`/`authenticated` at `/rest/v1/rpc/get_or_create_executor`, reachable by anyone with the public anon key. Migration 097's comment ("migration 092 revoked too broadly. Browser clients need this to resolve executor identity on login") shows it was a usability walk-back that reopened a documented CRITICAL hole instead of fixing the root cause.

2. **Body defect (migration 090):** `get_or_create_executor` resolves an executor **only** by the caller-supplied `p_wallet_address`, then in the existing-row branch unconditionally sets `user_id = COALESCE(v_user_id, executors.user_id)`. `COALESCE` only guards against a NULL caller; any non-NULL caller silently overwrites the prior owner. There is **no proof** that the caller controls the wallet — `p_signature` is optional and never verified (no `ecrecover`-equivalent, no comparison to a JWT wallet claim). There is no unique constraint on `executors.user_id` (only a plain index `idx_executors_user_id`), so the rebind never fails. This body defect is dangerous even for the service_role backend path if it is ever passed an attacker-influenced wallet, so it must be hardened regardless of who can call the function.

Deleting migration 097's `.sql` file is **not sufficient** — removing the file does not undo an already-applied `GRANT` in a live database. The remediation must be a NEW forward migration plus a standalone hotfix the operator can paste into the Supabase SQL editor.

## Exploit scenario (concrete attacker steps)
1. Attacker loads `https://execution.market` (or directly hits Supabase REST with the public anon key). Anonymous sign-in yields a session where `auth.uid() = ATTACKER_UID`.
2. Attacker reads the victim's wallet address from on-chain data or the UI (wallets are public), e.g. `0xVICTIM…`.
3. Attacker calls:
   ```
   POST https://<project>.supabase.co/rest/v1/rpc/get_or_create_executor
   apikey: <public anon key>
   Authorization: Bearer <attacker anon JWT>
   { "p_wallet_address": "0xVICTIM…" }
   ```
4. The function's `ELSE` branch runs `UPDATE executors SET user_id = ATTACKER_UID WHERE id = <victim executor id>`.
5. `current_executor_ids()` / `current_wallet_addresses()` now return the victim's executor for the attacker's session.
6. Attacker reads the victim's `payments`, `submissions`, `escrows`, `withdrawals`, `disputes`, `world_id_verifications`; then PATCHes `executors.wallet_address` (allowed by `executors_update_own`) to the attacker's wallet to redirect future payouts/withdrawals. The victim is detached from their account.

## The Fix (PRECISE, code-level)

The fix has **two parts that ship together**: (A) a forward migration `111` that revokes the grant AND hardens the function body; (B) a standalone idempotent hotfix block for immediate production application. No infra, Terraform, ECS, env-var, or feature-flag changes are required — this is a pure database remediation. The backend service_role path is unaffected.

### Behavior change introduced by the body hardening
The hardened function applies this rule in the existing-executor branch:
- If `executors.user_id IS NULL` → adopt the current session (`v_user_id`). (First legitimate login binds the row.)
- If `executors.user_id = v_user_id` → no-op rebind (idempotent re-login by the true owner). Profile fields still update.
- If `executors.user_id IS NOT NULL AND executors.user_id <> v_user_id` AND ownership of `p_wallet_address` is **not** proven → **leave `user_id` unchanged** (do NOT steal the row). The function still returns the executor data (so a service_role backend that has already authenticated the wallet via ERC-8128 keeps working), but it never silently transfers ownership.
- Ownership is considered proven only when the JWT carries a matching verified wallet claim: `LOWER(auth.jwt() -> 'user_metadata' ->> 'wallet_address') = v_normalized_wallet`. (The function itself writes this claim on the legitimate first-bind path, `090:109-114`.) When proven, a rebind to the proving session is allowed.

This preserves the multi-wallet model (a user may own several executors) and idempotent re-login, while making a cross-session takeover impossible at the body level — belt-and-suspenders behind the revoke.

### File 1 (NEW) — `supabase/migrations/111_revoke_and_harden_get_or_create_executor.sql`

```sql
-- Migration 111: Re-close DB-001 (P0) — revoke anon/authenticated EXECUTE on
-- get_or_create_executor AND harden the function body against identity rebind.
--
-- CONTEXT
-- -------
-- Migration 092 (GR-0.3, DB-001) revoked EXECUTE on
--   get_or_create_executor(text,text,text,text,text)
-- from PUBLIC/anon/authenticated and granted only service_role, because the
-- SECURITY DEFINER body rebinds an existing executor row to the caller's
-- auth.uid() on every call (090_fix_ambiguous_column_rpc.sql:125,
-- `user_id = COALESCE(v_user_id, executors.user_id)`), matching solely on the
-- caller-supplied p_wallet_address with no ownership proof.
--
-- Migration 097 then RE-GRANTED that exact signature to anon, authenticated,
-- reopening the CRITICAL cross-account takeover. This migration:
--   (1) re-REVOKEs from PUBLIC, anon, authenticated and re-GRANTs only
--       service_role (immediate fix; mirrors 092's _safe_revoke_and_grant), and
--   (2) hardens the function body so it NEVER overwrites a non-NULL user_id
--       belonging to a different session unless ownership of p_wallet_address is
--       proven via the verified wallet claim in the JWT (durable defense-in-depth,
--       protects the service_role backend path too).
--
-- IDEMPOTENT: REVOKE of a non-granted privilege is a no-op NOTICE; CREATE OR
-- REPLACE FUNCTION is idempotent. Safe to re-run.

BEGIN;

-- ============================================================================
-- 1. REVOKE the anon/authenticated grant that migration 097 re-added.
--    Revoke from PUBLIC too — anon/authenticated inherit PUBLIC in Supabase.
-- ============================================================================
DO $$
BEGIN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION public.get_or_create_executor(text, text, text, text, text) FROM PUBLIC, anon, authenticated';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.get_or_create_executor(text, text, text, text, text) TO service_role';
    RAISE NOTICE '111: re-locked get_or_create_executor to service_role only (re-closes DB-001)';
EXCEPTION WHEN undefined_function OR undefined_object THEN
    RAISE NOTICE '111: SKIPPED revoke/grant (function does not exist in this database)';
END;
$$;

COMMENT ON FUNCTION public.get_or_create_executor(text, text, text, text, text) IS
    'REVOKED from anon/authenticated 2026-06-09 (FIX-P0-02, re-closes DB-001 after migration 097 reopened it). service_role only. Body hardened: never rebinds a non-NULL user_id of a different session without proven wallet ownership.';

-- ============================================================================
-- 2. Harden the function body: never silently rebind a non-NULL user_id that
--    belongs to a different session. Only adopt the session when the row is
--    unowned (user_id IS NULL), already owned by this session, or wallet
--    ownership is proven via the verified JWT wallet claim.
--    (Full body re-stated from 090 with the ELSE branch hardened.)
-- ============================================================================
CREATE OR REPLACE FUNCTION get_or_create_executor(
    p_wallet_address TEXT,
    p_display_name TEXT DEFAULT NULL,
    p_email TEXT DEFAULT NULL,
    p_signature TEXT DEFAULT NULL,
    p_message TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    wallet_address TEXT,
    display_name TEXT,
    email TEXT,
    reputation_score INTEGER,
    tier executor_tier,
    tasks_completed INTEGER,
    balance_usdc DECIMAL(18, 6),
    created_at TIMESTAMPTZ,
    is_new BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
#variable_conflict use_column
DECLARE
    v_executor_id UUID;
    v_is_new BOOLEAN := FALSE;
    v_user_id UUID;
    v_existing_user_id UUID;
    v_owns_wallet BOOLEAN := FALSE;
    v_jwt_wallet TEXT;
    v_normalized_wallet TEXT;
    v_default_name TEXT;
BEGIN
    -- Get current authenticated user
    v_user_id := auth.uid();

    -- Normalize: lowercase for EVM, preserve case for Solana
    IF p_wallet_address LIKE '0x%' OR p_wallet_address LIKE '0X%' THEN
        v_normalized_wallet := LOWER(p_wallet_address);
    ELSE
        v_normalized_wallet := p_wallet_address;  -- Solana: case-sensitive
    END IF;

    -- Validate wallet address format (EVM or Solana Base58)
    IF v_normalized_wallet !~ '^0x[a-f0-9]{40}$' AND v_normalized_wallet !~ '^[1-9A-HJ-NP-Za-km-z]{32,44}$' THEN
        RAISE EXCEPTION 'Invalid wallet address format: %', p_wallet_address;
    END IF;

    -- Does the JWT already prove ownership of this wallet? The legitimate
    -- first-bind path below writes this claim into auth.users metadata.
    BEGIN
        v_jwt_wallet := LOWER(auth.jwt() -> 'user_metadata' ->> 'wallet_address');
    EXCEPTION WHEN OTHERS THEN
        v_jwt_wallet := NULL;
    END;
    v_owns_wallet := (v_jwt_wallet IS NOT NULL AND v_jwt_wallet = LOWER(v_normalized_wallet));

    -- Check if executor exists by wallet address
    SELECT e.id, e.user_id INTO v_executor_id, v_existing_user_id
    FROM executors e
    WHERE e.wallet_address = v_normalized_wallet;

    IF v_executor_id IS NULL THEN
        -- Generate default display name
        IF v_normalized_wallet LIKE '0x%' THEN
            v_default_name := 'Worker_' || SUBSTRING(v_normalized_wallet FROM 3 FOR 8);
        ELSE
            v_default_name := 'Worker_' || SUBSTRING(v_normalized_wallet FROM 1 FOR 8);
        END IF;

        -- Create new executor
        INSERT INTO executors (
            wallet_address,
            user_id,
            display_name,
            email,
            reputation_score,
            tier,
            status
        )
        VALUES (
            v_normalized_wallet,
            v_user_id,
            COALESCE(p_display_name, v_default_name),
            p_email,
            50,  -- Neutral starting reputation
            'probation',
            'active'
        )
        RETURNING executors.id INTO v_executor_id;

        v_is_new := TRUE;

        -- Log initial reputation
        INSERT INTO reputation_log (executor_id, event_type, delta, old_score, new_score, reason)
        VALUES (v_executor_id, 'initial_registration', 50, 0, 50, 'Account created');

        -- Link wallet to user if authenticated
        IF v_user_id IS NOT NULL THEN
            IF p_signature IS NOT NULL THEN
                INSERT INTO user_wallets (user_id, wallet_address, is_primary, chain_id, signature_hash, verified_at)
                VALUES (v_user_id, v_normalized_wallet, TRUE, 8453, p_signature, NOW())
                ON CONFLICT (user_id, wallet_address)
                DO UPDATE SET signature_hash = EXCLUDED.signature_hash, verified_at = NOW(), is_primary = TRUE, updated_at = NOW();
            ELSE
                INSERT INTO user_wallets (user_id, wallet_address, is_primary)
                VALUES (v_user_id, v_normalized_wallet, TRUE)
                ON CONFLICT (user_id, wallet_address) DO NOTHING;
            END IF;

            -- Store wallet_address in user metadata (this is what later proves
            -- ownership for the v_owns_wallet check above on subsequent calls).
            UPDATE auth.users
            SET raw_user_meta_data = COALESCE(raw_user_meta_data, '{}'::jsonb) ||
                jsonb_build_object('wallet_address', v_normalized_wallet)
            WHERE id = v_user_id;
        END IF;

        -- Award newcomer badge (progress at 0)
        INSERT INTO badges (executor_id, badge_type, name, description, progress, max_progress)
        VALUES (v_executor_id, 'newcomer', 'Newcomer', 'Complete your first task', 0, 1);

    ELSE
        -- HARDENED (FIX-P0-02): never overwrite a non-NULL user_id belonging to
        -- a DIFFERENT session unless ownership of this wallet is proven via the
        -- verified JWT wallet claim. Adopt the session only when the row is
        -- unowned, already owned by this session, or ownership is proven.
        UPDATE executors
        SET
            last_active_at = NOW(),
            user_id = CASE
                WHEN v_existing_user_id IS NULL THEN v_user_id              -- first bind
                WHEN v_existing_user_id = v_user_id THEN v_existing_user_id -- idempotent re-login
                WHEN v_owns_wallet THEN v_user_id                          -- proven owner rebind
                ELSE v_existing_user_id                                    -- DENY silent takeover
            END,
            email = COALESCE(executors.email, p_email)
        WHERE executors.id = v_executor_id;

        -- Only persist wallet verification / JWT claim when the caller is (or
        -- has just become) the owning session AND supplied a signature. This
        -- prevents an attacker session from writing a wallet claim it does not own.
        IF v_user_id IS NOT NULL
           AND p_signature IS NOT NULL
           AND (v_existing_user_id IS NULL OR v_existing_user_id = v_user_id OR v_owns_wallet) THEN
            INSERT INTO user_wallets (user_id, wallet_address, is_primary, chain_id, signature_hash, verified_at)
            VALUES (v_user_id, v_normalized_wallet, TRUE, 8453, p_signature, NOW())
            ON CONFLICT (user_id, wallet_address)
            DO UPDATE SET signature_hash = EXCLUDED.signature_hash, verified_at = NOW(), is_primary = TRUE, updated_at = NOW();

            UPDATE auth.users
            SET raw_user_meta_data = COALESCE(raw_user_meta_data, '{}'::jsonb) ||
                jsonb_build_object('wallet_address', v_normalized_wallet)
            WHERE id = v_user_id;
        END IF;
    END IF;

    -- Return executor data
    RETURN QUERY
    SELECT
        e.id,
        e.wallet_address::TEXT,
        e.display_name::TEXT,
        e.email::TEXT,
        e.reputation_score,
        e.tier,
        e.tasks_completed,
        e.balance_usdc,
        e.created_at,
        v_is_new
    FROM executors e
    WHERE e.id = v_executor_id;
END;
$$;

COMMIT;

-- ============================================================================
-- VERIFICATION (run after COMMIT — expect f, f, t)
-- ============================================================================
-- SELECT has_function_privilege('anon',          'public.get_or_create_executor(text,text,text,text,text)', 'EXECUTE') AS anon_can_execute;          -- expect f
-- SELECT has_function_privilege('authenticated',  'public.get_or_create_executor(text,text,text,text,text)', 'EXECUTE') AS authed_can_execute;        -- expect f
-- SELECT has_function_privilege('service_role',   'public.get_or_create_executor(text,text,text,text,text)', 'EXECUTE') AS service_role_can_execute;  -- expect t

-- ============================================================================
-- ROLLBACK (manual — NOT recommended; reopens DB-001)
-- ============================================================================
-- BEGIN;
--   GRANT EXECUTE ON FUNCTION public.get_or_create_executor(text,text,text,text,text)
--       TO anon, authenticated;  -- reopens the takeover; do not do this
--   -- To revert the body hardening, re-apply migration 090's function body.
-- COMMIT;
```

### Standalone production hotfix (paste into Supabase SQL editor)
Idempotent; safe to run immediately, before the migration is checked in. This is the **revoke half** (the immediate P0 closure). The body hardening from File 1 above can be pasted in the same editor session right after, or applied via the full migration — either works because both are idempotent.

```sql
-- ===========================================================================
-- HOTFIX FIX-P0-02 (paste in Supabase SQL editor) — re-close DB-001 NOW.
-- Revoke the migration-097 anon/authenticated grant on get_or_create_executor.
-- Idempotent: re-running is a no-op.
-- ===========================================================================
DO $$
BEGIN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION public.get_or_create_executor(text, text, text, text, text) FROM PUBLIC, anon, authenticated';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.get_or_create_executor(text, text, text, text, text) TO service_role';
    RAISE NOTICE 'HOTFIX FIX-P0-02: get_or_create_executor re-locked to service_role only';
EXCEPTION WHEN undefined_function OR undefined_object THEN
    RAISE NOTICE 'HOTFIX FIX-P0-02: function not found, nothing to revoke';
END;
$$;

-- Verify (expect f, f, t):
SELECT
    has_function_privilege('anon',         'public.get_or_create_executor(text,text,text,text,text)', 'EXECUTE') AS anon_can_execute,
    has_function_privilege('authenticated','public.get_or_create_executor(text,text,text,text,text)', 'EXECUTE') AS authed_can_execute,
    has_function_privilege('service_role', 'public.get_or_create_executor(text,text,text,text,text)', 'EXECUTE') AS service_role_can_execute;
```

> Apply the body-hardening half (the `CREATE OR REPLACE FUNCTION` block from File 1, lines under section 2) right after the revoke for full defense-in-depth. The revoke alone closes the browser-reachable P0; the body hardening closes the residual risk for any service_role caller passing an attacker-influenced wallet.

### Backward-compatibility risk and safe rollout
- **No infra / Terraform / ECS / env-var / feature-flag change is required.** Pure DB remediation.
- **Backend path is unaffected.** `mcp_server/api/routers/workers.py:99` calls the RPC through `db.get_client()`, which uses `SUPABASE_SERVICE_ROLE_KEY` (`mcp_server/supabase_client.py:29-44`). service_role retains EXECUTE, so worker registration via the backend keeps working.
- **Dashboard direct browser calls WILL lose access** (HTTP 403 / PostgREST `42501`) at:
  - `dashboard/src/context/AuthContext.tsx:209`
  - `dashboard/src/hooks/useProfileUpdate.ts:52`
  This is the **same intentional consequence** migration 092 already documented (GR-1.7). `AuthContext.tsx` already has a graceful fallback path (`fetchExecutor` falls back to a direct `executors` SELECT at `:227-238`, and `linkWalletToSession` already treats `42501` as non-fatal at `:180-182`). Legitimate read of an existing executor still works via the anon SELECT path under existing SELECT RLS; only browser-side *creation*/rebind via this RPC is blocked. **Verify in staging that a brand-new wallet can still onboard** — if onboarding-by-browser must keep working before GR-1.7 lands, route the create through the backend `POST /workers/register` (already service_role) rather than re-granting the RPC. Do **not** re-grant the RPC to the browser as a shortcut.
- **No legitimate agent lockout from the body hardening:** the hardened body still adopts the session for unowned rows (`user_id IS NULL`) and is a no-op for the true owner, preserving idempotent re-login and the multi-wallet model. A user only loses the ability to *steal* a row already owned by a different `auth.uid()` — which is exactly the vulnerability.
- **Staged rollout:** (1) apply the standalone revoke hotfix in production immediately (stops active exploitation); (2) verify backend `POST /workers/register` and dashboard onboarding in staging; (3) merge migration 111 (revoke + body hardening) for the durable fix.

## Test plan (how the execution team proves it's fixed)

### A. Database / SQL regression tests (pgTAP or raw SQL asserts; add under `supabase/tests/` or the project's DB test harness)
Name: `test_fix_p0_02_get_or_create_executor_lockdown`

1. **Grant assertion (proves the revoke):**
   - `SELECT has_function_privilege('anon','public.get_or_create_executor(text,text,text,text,text)','EXECUTE')` → assert **false**.
   - Same for `authenticated` → assert **false**.
   - For `service_role` → assert **true**.

2. **Rebind-denied regression (reproduces the bug, then passes):**
   - Insert executor `E` with `wallet_address = '0xaaaa…aaaa'`, `user_id = '<VICTIM_UID>'`.
   - Simulate an attacker session: set `request.jwt.claims` so `auth.uid()` returns `<ATTACKER_UID>` and `user_metadata.wallet_address` is absent (or a different wallet).
   - Call `get_or_create_executor('0xaaaa…aaaa')`.
   - **Before fix:** `SELECT user_id FROM executors WHERE wallet_address='0xaaaa…aaaa'` returns `<ATTACKER_UID>` (takeover). **After fix:** returns `<VICTIM_UID>` (unchanged). Assert it equals `<VICTIM_UID>`.

3. **First-bind still works:**
   - Insert executor with `user_id = NULL`. Call as `<UID_X>`. Assert `user_id` becomes `<UID_X>`.

4. **Idempotent re-login no-op:**
   - Executor owned by `<UID_X>`. Call as `<UID_X>`. Assert `user_id` stays `<UID_X>` and `last_active_at` updated.

5. **Proven-owner rebind allowed:**
   - Executor `user_id = <UID_OLD>`. Call as `<UID_NEW>` whose JWT `user_metadata.wallet_address` equals the executor's wallet. Assert `user_id` becomes `<UID_NEW>` (legitimate device/session migration of the real owner).

### B. Backend integration test (`mcp_server/tests/`)
Name: `test_register_worker_uses_service_role_path` (extend existing worker registration tests).
- Assert `POST /workers/register` still creates/returns an executor after the revoke (because it runs as service_role). This proves the production onboarding path is not broken.

### C. Manual / E2E verification
1. With only the **public anon key**, run the exploit `POST /rest/v1/rpc/get_or_create_executor` with a wallet you do NOT own → expect HTTP 401/403 / PostgREST error code `42501` (function not executable). Confirm no `executors.user_id` row changed.
2. Run the verification query in `111` → `anon=f`, `authenticated=f`, `service_role=t`.
3. Log into the dashboard with an existing wallet → confirm profile still loads (via the `AuthContext` fallback SELECT or the backend register endpoint) and no console error escalates beyond the expected non-fatal `42501` debug log.
4. Onboard a brand-new wallet via the dashboard → confirm onboarding still completes (via backend `POST /workers/register`). If it does not, wire onboarding to the backend endpoint before closing this finding.

## Rollback plan
- The migration is self-contained and idempotent. To roll back the **revoke** (NOT recommended — reopens DB-001): run `GRANT EXECUTE ON FUNCTION public.get_or_create_executor(text,text,text,text,text) TO anon, authenticated;`.
- To roll back the **body hardening**: re-apply the function body from `090_fix_ambiguous_column_rpc.sql` (the `CREATE OR REPLACE FUNCTION get_or_create_executor(...)` block). The rollback SQL is included as a comment at the bottom of migration 111.
- No data migration occurs, so no data rollback is needed. Rows whose `user_id` was previously stolen via the live bug are NOT auto-restored by this fix — see the post-fix audit note below.

## Verification checklist (boxes the executor ticks before marking done)
- [ ] Read `092_revoke_anon_rpcs.sql`, `090_fix_ambiguous_column_rpc.sql`, `097_grant_get_or_create_executor_anon.sql`, `054_rls_performance_helpers.sql`, and `dashboard/src/context/AuthContext.tsx:141-238` to confirm the flow.
- [ ] Created `supabase/migrations/111_revoke_and_harden_get_or_create_executor.sql` exactly as specified (revoke + body hardening).
- [ ] Ran the standalone hotfix in production Supabase SQL editor; verification query returns `anon=f`, `authenticated=f`, `service_role=t`.
- [ ] `git grep -n "GRANT EXECUTE ON FUNCTION get_or_create_executor"` shows NO grant to anon/authenticated remains in `supabase/migrations/` after 097 (i.e., 111 is the last word). Also checked `mcp_server/supabase/migrations/20260125000003_rpc_functions.sql:678` — that stale grant lives in the secondary migration tree; ensure the production DB has 111 applied last, or neutralize that grant too if that tree is applied to production.
- [ ] DB regression test `test_fix_p0_02_get_or_create_executor_lockdown` added and passing: rebind-denied case fails on old code, passes on new.
- [ ] Backend `POST /workers/register` integration test passes (service_role path intact).
- [ ] Manual exploit attempt with public anon key returns 401/403/`42501`; no `executors.user_id` mutated.
- [ ] Dashboard login (existing wallet) and onboarding (new wallet) verified in staging; onboarding routed via backend if browser RPC create is needed.
- [ ] Post-fix audit: queried `executors` for rows whose `user_id` was changed in the exposure window (compare `last_active_at` / `updated_at` against the 097→111 deployment window, cross-check `user_wallets` and `auth.users.raw_user_meta_data.wallet_address`) to detect any live takeover; reverted any orphaned/hijacked `user_id` and checked for `executors.wallet_address` overwrites that could have redirected payouts.
- [ ] Confirmed no secret values are printed anywhere in this change.
