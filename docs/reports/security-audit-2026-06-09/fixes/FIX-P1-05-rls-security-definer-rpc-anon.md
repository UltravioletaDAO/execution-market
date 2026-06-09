---
date: 2026-06-09
tags: [type/incident, domain/security]
status: active
severity: P1
finding_id: FIX-P1-05
---
# FIX-P1-05 — Anon-Executable SECURITY DEFINER Money/State RPCs (Migration 092 Lockdown Incomplete)

## Summary

The dashboard talks to Supabase REST directly with the **public anon key**, so RPC `EXECUTE` grants are the only trust boundary between an anonymous browser and the database. PostgreSQL grants `EXECUTE` to `PUBLIC` by default on every new function, and Supabase `anon`/`authenticated` inherit from `PUBLIC`; migration `092` revoked that default grant from only **15** functions and falsely asserted (lines 83–86) that several state-mutating RPCs were "already service_role ONLY (verified)". They are not. A set of `SECURITY DEFINER` functions that mutate dispute/task/escrow/payment tables (`resolve_dispute`, `assign_task_to_executor`, `fund_escrow`, `release_partial_payment`, `release_final_payment`, `refund_escrow`, `escalate_to_arbitration`, plus reputation/badge helpers) retain their default `PUBLIC` `EXECUTE` grant and are callable by anon via `POST /rest/v1/rpc/<fn>`, running as the function owner and **bypassing RLS**. The fix is a new migration (`111`) that dynamically REVOKEs `EXECUTE` from `PUBLIC, anon, authenticated` on **every** `SECURITY DEFINER` function in `public` that is currently anon- or authenticated-executable, except a single intentionally-anon allowlist entry (`get_or_create_executor`), plus a CI regression assertion.

## Severity & Impact (why P1)

An anonymous browser holding only the intended-public Supabase anon key can bypass RLS and write to financial / dispute / task tables:

- **Forge dispute outcomes & DoS resolution** — `resolve_dispute(004:673)` has **zero** caller-authorization check. Anon can set `status`, `winner`, `executor_payout_usdc`, `agent_refund_usdc` for any dispute. The legitimate owner/arbiter can then no longer resolve through the backend (it returns 409 "already resolved"), so this is both forgery of the dispute source-of-truth and a **denial of resolution**.
- **Hijack / squat published tasks** — `assign_task_to_executor(005:485)` is gated only by `v_task.agent_id != p_agent_id`, and `agent_id` is public (exposed via the read-only `get_task_details` RPC). Anon can flip any `published` task to `accepted` bound to an attacker-controlled `executor_id` **with no escrow lock**, squatting ahead of legitimate workers.
- **Pollute the financial ledger** — `fund_escrow`/`release_partial_payment`/`release_final_payment`/`refund_escrow(002)` have no caller auth; they mark escrows funded and `INSERT` fabricated `completed`/`pending` payment rows, corrupting financial reconciliation/auditing.

**Why P1 and not P0:** there is no clean direct on-chain drain. (a) On-chain settlement runs only through the ERC-8128-authenticated backend (`mcp_server/api/routers/disputes.py:674-708` requires auth + 409s on already-resolved + ownership/arbiter check), so the anon Supabase RPC cannot trigger a Facilitator payout. (b) The withdrawal path pays out the sum of `payments` rows with `status='available'`, a status these RPCs do not produce (they hardcode `completed`/`pending`); and `payments_update_executor_balance` fires only on `AFTER UPDATE OF status`, not on `INSERT`, so a forged row never credits `balance_usdc`. The realistic, exploitable impact is an anonymous RLS/auth bypass corrupting dispute integrity, hijacking tasks, and polluting the ledger — solidly P1.

## Affected code (exact file:line references)

**Incomplete lockdown + false comments — `supabase/migrations/092_revoke_anon_rpcs.sql`:**

- `092:99-102` — correctly documents the root mechanism: *"PostgreSQL grants EXECUTE to PUBLIC by default ... `anon` and `authenticated` are members of PUBLIC ... we must also revoke from PUBLIC."*
- `092:113` — the helper REVOKEs `FROM PUBLIC, anon, authenticated` — but is applied to only the 15 functions listed at `092:124-153`.
- `092:83-86` — **FALSE assertions** (the bug):
  ```
  --   assign_task_to_executor — already service_role ONLY (verified)
  --   complete_submission    — already service_role ONLY (verified)
  --   expire_overdue_tasks   — already service_role ONLY (verified)
  --   escalate_to_arbitration — no anon/authenticated grant found (default-deny)
  ```
  An explicit `GRANT ... TO service_role` does **not** remove `PUBLIC`'s default grant, so none of these are "service_role only" or "default-deny".

**Proof the anon path is via a DEFAULT grant (not explicit GRANT-TO-anon) — `supabase/migrations/097_grant_get_or_create_executor_anon.sql:1-7`:** its comment states `get_or_create_executor` *"was only granted to postgres + service_role (migration 092 revoked too broadly)"* and re-grants it to anon. But `005:960`/`042` only ever granted that function `TO authenticated` (never anon), yet `092`'s `REVOKE ... FROM PUBLIC, anon, authenticated` removed anon's access — proving anon access in this DB comes from the `PUBLIC`/Supabase default, not from explicit GRANT-TO-anon statements. Therefore every `SECURITY DEFINER` function `092` did not revoke retains its default anon `EXECUTE`.

**Vulnerable `SECURITY DEFINER` functions (granted to `service_role` only, never revoked from `PUBLIC`):**

| Function (latest signature) | Def line | Grant line | Caller auth |
|---|---|---|---|
| `resolve_dispute(uuid, varchar, text, numeric, varchar)` | `004:673` | `004:896` | **NONE** — only checks dispute exists & not already resolved |
| `escalate_to_arbitration(uuid)` | `004:446` | `004:895` | **NONE** |
| `assign_task_to_executor(uuid, uuid, text, text)` | `005:485` | `005:976` | only `v_task.agent_id` (public) |
| `complete_submission(uuid, text, text, text, integer)` | `005:680` | `005:977` | only `p_agent_id` (mitigated at runtime, see below) |
| `expire_overdue_tasks()` | `005:902` | `005:978` | NONE |
| `fund_escrow(uuid, varchar)` | `002:390` | `002:827` | NONE |
| `release_partial_payment(uuid, uuid, varchar)` | `002:411` | `002:828` | NONE |
| `release_final_payment(uuid, varchar)` | `002:481` | `002:829` | NONE |
| `refund_escrow(uuid, text, varchar)` | `002:565` | `002:830` | NONE |
| `recalculate_executor_reputation(uuid)` | `003:302` | `003:818` | NONE (mitigated, see below) |
| `award_badge(uuid, badge_type, varchar, text, task_category)` | `003:497` | `003:820` | NONE |
| `award_tier_badge(uuid, executor_tier)` | `003:537` | *(none — also default-PUBLIC)* | NONE |
| `check_milestone_badges(uuid)` | `003:577` | `003:821` | NONE (mitigated, see below) |
| `create_reputation_snapshot(date, varchar)` | `003:661` | `003:822` | NONE |

**`resolve_dispute` body (redacted) — confirms zero caller auth (`004:673-736`):**
```sql
SELECT * INTO v_dispute FROM disputes WHERE id = p_dispute_id FOR UPDATE;
IF v_dispute.id IS NULL THEN RETURN ... 'Dispute not found'; END IF;
IF v_dispute.status IN ('resolved_for_agent', ...) THEN RETURN ... 'already resolved'; END IF;
-- (no auth.uid() / agent_id / arbiter check anywhere)
UPDATE disputes SET status=..., winner=p_winner, executor_payout_usdc=..., ...
```

**`assign_task_to_executor` body (redacted) — confirms only public-agent_id gate (`005:485-544`):**
```sql
IF v_task.agent_id != p_agent_id THEN
    RETURN jsonb_build_object('success', false, 'error', 'Not authorized to assign this task');
END IF;
UPDATE tasks SET status='accepted', executor_id=p_executor_id, ... WHERE id=p_task_id;
```

## Root cause

The real defect is a **methodological** one in migration `092`: the lockdown was driven by **hand-enumerating GRANT statements** instead of querying actual privileges. Because PostgreSQL's default `PUBLIC` `EXECUTE` grant is implicit (it appears in no `GRANT` statement), enumerating GRANTs misses it entirely. The author also misread an explicit `GRANT ... TO service_role` as proof of exclusivity (`092:83-86`), when in fact that grant is *additive* on top of the still-live `PUBLIC` default. There is no `ALTER DEFAULT PRIVILEGES`, no broad `REVOKE EXECUTE ON ALL FUNCTIONS`, and no `FORCE ROW LEVEL SECURITY` anywhere in the migration set (verified via grep), so nothing else closes the gap. Net: ~14 `SECURITY DEFINER` state-mutators in `public` remain anon-executable.

## Exploit scenario (concrete attacker steps)

1. Attacker loads `execution.market`, reads the intended-public anon key from the bundle, and reads any task via the public `get_task_details` RPC — learning the task's `agent_id` and any open `dispute_id`.
2. Forge a dispute outcome:
   ```
   POST https://<project>.supabase.co/rest/v1/rpc/resolve_dispute
   apikey: <public anon key>
   { "p_dispute_id": "<id>", "p_winner": "executor",
     "p_resolution_notes": "x", "p_agent_refund_pct": 0 }
   ```
   The `SECURITY DEFINER` function runs as owner, bypasses RLS, sets `status='resolved_for_executor'`, `winner='executor'`, `executor_payout_usdc=<full disputed amount>`.
3. The legitimate agent/arbiter can no longer resolve the dispute via the backend (it 409s "already resolved"). Dispute integrity is forged + resolution is DoS'd.
4. Hijack a published task:
   ```
   POST .../rpc/assign_task_to_executor
   { "p_task_id": "<id>", "p_executor_id": "<attacker executor>", "p_agent_id": "<public agent_id>" }
   ```
   Task flips to `accepted` bound to the attacker, no escrow lock.
5. Pollute the ledger: `POST .../rpc/fund_escrow` then `.../rpc/release_final_payment` inject fabricated `funded`/`completed` rows into `escrows`/`payments`.

## The Fix (precise, code-level)

### Design

REVOKE `EXECUTE` from `PUBLIC, anon, authenticated` on **every** `SECURITY DEFINER` function in schema `public` that is currently anon- or authenticated-executable, then re-`GRANT` to `service_role`. **Drive this from `pg_proc`, not a hand-written list** — that is exactly how `092` missed these. Keep one explicit allowlist entry for the only intentionally-anon `SECURITY DEFINER` function:

- `get_or_create_executor(text, text, text, text, text)` — deliberately re-exposed to anon by migration `097` for login (it upserts an executor row). **Note (cross-reference):** its DB-001 account-rebind concern (`COALESCE(v_user_id, executors.user_id)` overwrite) is a *separate* live issue tracked in `FIX-P0-02-migration-097-anon-get-or-create-executor.md` — out of scope here, but the allowlist comment must point at it.

**Why the allowlist is short:** the finding lists `get_nearby_tasks`, `search_tasks`, `get_task_details`, `get_platform_stats`, `get_executor_stats`, `get_executor_tasks` as "deliberately anon" — but verification shows **none of them are `SECURITY DEFINER`** (they are SECURITY INVOKER, the default). The `prosecdef` filter never selects them, so they need no allowlist entry and are untouched by this migration. The only `SECURITY DEFINER` + intentionally-anon function is `get_or_create_executor`.

**Backward-compatibility risk — LOW (verified):** `grep -rn ".rpc('<fn>')"` over `dashboard/src` and `admin-dashboard/src` shows the browser calls only `get_or_create_executor` (allowlisted), plus `link_wallet_to_session` and `update_executor_profile` — and the latter two were **already** revoked from anon by `092` (DB-002/DB-003) and intentionally route through the backend per the GR-1.7 plan in the `092` header. So none of the functions this migration locks down has a live browser caller; revoking them cannot break the dashboard. They are all invoked exclusively by the `service_role` backend, which is unaffected by these REVOKEs.

### New migration: `supabase/migrations/111_lockdown_security_definer_rpcs.sql`

(Next free number confirmed: highest existing is `110`.)

```sql
-- Migration 111: Lock down ALL anon-executable SECURITY DEFINER RPCs (FIX-P1-05).
-- Security audit 2026-06-09. Completes the partial lockdown of migration 092.
--
-- ROOT CAUSE
-- ----------
-- PostgreSQL grants EXECUTE to PUBLIC by default on every new function, and
-- Supabase anon/authenticated INHERIT from PUBLIC. Migration 092 documented
-- this (092:99-102) but only revoked 15 functions by HAND-ENUMERATING GRANT
-- statements — which can never see the implicit PUBLIC default grant. It also
-- falsely asserted (092:83-86) that assign_task_to_executor, complete_submission,
-- expire_overdue_tasks were "service_role ONLY" and escalate_to_arbitration was
-- "default-deny". An explicit GRANT TO service_role does NOT remove PUBLIC's
-- default grant, so ~14 SECURITY DEFINER money/state RPCs stayed anon-executable
-- via POST /rest/v1/rpc/<fn>, bypassing RLS (run as owner). See FIX-P1-05.
--
-- APPROACH
-- --------
-- Do NOT hand-enumerate (that is how 092 missed these). Loop over pg_proc and
-- REVOKE EXECUTE FROM PUBLIC, anon, authenticated for EVERY SECURITY DEFINER
-- function in schema public that anon OR authenticated can currently execute,
-- except an explicit allowlist of intentionally-anon SECURITY DEFINER funcs.
-- Then GRANT EXECUTE TO service_role. Idempotent and safe to re-run.

BEGIN;

DO $$
DECLARE
    r RECORD;
    -- Intentionally anon/authenticated-callable SECURITY DEFINER functions.
    -- get_or_create_executor: re-granted to anon by migration 097 for login.
    --   (Its DB-001 account-rebind concern is tracked separately in FIX-P0-02.)
    allowlist text[] := ARRAY['get_or_create_executor'];
BEGIN
    FOR r IN
        SELECT p.oid::regprocedure AS sig, p.proname AS name
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.prosecdef                                   -- SECURITY DEFINER only
          AND p.proname <> ALL(allowlist)
          AND (
                has_function_privilege('anon', p.oid, 'EXECUTE')
                OR has_function_privilege('authenticated', p.oid, 'EXECUTE')
              )
    LOOP
        EXECUTE format(
            'REVOKE EXECUTE ON FUNCTION %s FROM PUBLIC, anon, authenticated', r.sig);
        EXECUTE format(
            'GRANT EXECUTE ON FUNCTION %s TO service_role', r.sig);
        RAISE NOTICE '111: locked down %', r.sig;
    END LOOP;
END $$;

-- ---------------------------------------------------------------------------
-- Correct the false comments left by migration 092 (092:83-86).
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    r RECORD;
    msg constant text :=
        'REVOKED from PUBLIC/anon/authenticated 2026-06-09 (FIX-P1-05, migration 111). '
        'Service_role only. Migration 092 left this anon-executable via the default PUBLIC grant.';
BEGIN
    FOR r IN
        SELECT p.oid::regprocedure AS sig
        FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public' AND p.prosecdef
          AND p.proname = ANY(ARRAY[
              'resolve_dispute','escalate_to_arbitration','assign_task_to_executor',
              'complete_submission','expire_overdue_tasks','fund_escrow',
              'release_partial_payment','release_final_payment','refund_escrow',
              'recalculate_executor_reputation','award_badge','award_tier_badge',
              'check_milestone_badges','create_reputation_snapshot'])
    LOOP
        EXECUTE format('COMMENT ON FUNCTION %s IS %L', r.sig, msg);
    END LOOP;
END $$;

-- ---------------------------------------------------------------------------
-- ASSERTION: fail the migration if ANY non-allowlisted SECURITY DEFINER
-- function in public is still anon- or authenticated-executable.
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    leaked text;
    allowlist text[] := ARRAY['get_or_create_executor'];
BEGIN
    SELECT string_agg(p.oid::regprocedure::text, ', ')
    INTO leaked
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.prosecdef
      AND p.proname <> ALL(allowlist)
      AND (
            has_function_privilege('anon', p.oid, 'EXECUTE')
            OR has_function_privilege('authenticated', p.oid, 'EXECUTE')
          );

    IF leaked IS NOT NULL THEN
        RAISE EXCEPTION
            '111 ASSERTION FAILED: SECURITY DEFINER funcs still anon/authenticated-executable: %',
            leaked;
    END IF;
    RAISE NOTICE '111: assertion passed — no non-allowlisted anon-executable SECURITY DEFINER funcs remain';
END $$;

COMMIT;

-- ===========================================================================
-- ROLLBACK (manual — NOT recommended, re-opens the anon RLS bypass)
-- ===========================================================================
-- BEGIN;
-- -- Restore default PUBLIC EXECUTE on each locked-down function, e.g.:
-- -- GRANT EXECUTE ON FUNCTION public.resolve_dispute(uuid, character varying, text, numeric, character varying) TO PUBLIC;
-- -- GRANT EXECUTE ON FUNCTION public.assign_task_to_executor(uuid, uuid, text, text) TO PUBLIC;
-- -- ... (repeat per function). There is no behavioural reason to do this; the
-- -- backend uses service_role and is unaffected.
-- COMMIT;
```

### Standalone production hotfix (paste into Supabase SQL editor)

Idempotent; same logic as the migration but self-contained. Run as the database owner/`postgres` (the Supabase SQL editor connects as a superuser-equivalent, which can REVOKE on functions it does not own).

```sql
-- HOTFIX FIX-P1-05: lock down anon-executable SECURITY DEFINER RPCs.
-- Safe to run multiple times. Skips get_or_create_executor (anon login, by design).
BEGIN;

DO $$
DECLARE
    r RECORD;
    allowlist text[] := ARRAY['get_or_create_executor'];
BEGIN
    FOR r IN
        SELECT p.oid::regprocedure AS sig
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND p.prosecdef
          AND p.proname <> ALL(allowlist)
          AND ( has_function_privilege('anon', p.oid, 'EXECUTE')
             OR has_function_privilege('authenticated', p.oid, 'EXECUTE') )
    LOOP
        EXECUTE format('REVOKE EXECUTE ON FUNCTION %s FROM PUBLIC, anon, authenticated', r.sig);
        EXECUTE format('GRANT  EXECUTE ON FUNCTION %s TO service_role', r.sig);
        RAISE NOTICE 'hotfix: locked %', r.sig;
    END LOOP;
END $$;

-- Verify: this SELECT must return ZERO rows after the fix.
SELECT p.oid::regprocedure AS still_anon_executable
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public'
  AND p.prosecdef
  AND p.proname <> 'get_or_create_executor'
  AND ( has_function_privilege('anon', p.oid, 'EXECUTE')
     OR has_function_privilege('authenticated', p.oid, 'EXECUTE') );

COMMIT;
```

For the explicit signatures the operator may want to confirm by name, the functions this REVOKEs are:

```
resolve_dispute(uuid, character varying, text, numeric, character varying)
escalate_to_arbitration(uuid)
assign_task_to_executor(uuid, uuid, text, text)
complete_submission(uuid, text, text, text, integer)
expire_overdue_tasks()
fund_escrow(uuid, character varying)
release_partial_payment(uuid, uuid, character varying)
release_final_payment(uuid, character varying)
refund_escrow(uuid, text, character varying)
recalculate_executor_reputation(uuid)
award_badge(uuid, badge_type, character varying, text, task_category)
award_tier_badge(uuid, executor_tier)
check_milestone_badges(uuid)
create_reputation_snapshot(date, character varying)
```
(plus any other `SECURITY DEFINER` function in `public` the loop discovers — e.g. `auto_approve_submission`, `check_arbitration_complete`, `reconcile_executor_balances` if its 092 revoke did not stick — which is the entire point of the dynamic approach.)

### Infra / env / feature-flag changes

**None.** This is a pure database-grant change. No Terraform, no ECS task-definition, no env var, no feature flag. The `service_role` backend (FastAPI on ECS) connects with the service-role key and is unaffected.

### Backward-compatibility & safe rollout

- **No legitimate agent is locked out.** All affected functions are server-only (verified: no browser `.rpc()` callers; the backend uses `service_role`). `get_or_create_executor` (the only browser-facing `SECURITY DEFINER` RPC) is allowlisted and keeps anon access.
- **Staged rollout:** apply to **staging first**, run the Test plan, confirm Golden Flow + dashboard login pass, then apply to production in a low-traffic window. Because the change is grant-only and idempotent, no downtime and no application redeploy is required.
- **Ordering with FIX-P0-02:** independent. FIX-P0-02 hardens `get_or_create_executor` itself (DB-001 rebind); this fix leaves that function alone. Apply in either order.

## Test plan

### Migration assertion (built-in)
The migration's final `DO` block raises and aborts the transaction if any non-allowlisted `SECURITY DEFINER` function in `public` is still anon/authenticated-executable. A clean migration run is itself the first proof.

### Regression test — `supabase/tests/test_security_definer_rpc_grants.sql` (new, pgTAP or plain assert)
Reproduces the bug pre-fix and passes post-fix. Add this and wire it into the migration-test CI job that runs against a freshly-migrated database.

```sql
-- Asserts NO non-allowlisted SECURITY DEFINER function in public is
-- anon- or authenticated-executable. FAILS on a DB at migration <= 110,
-- PASSES at >= 111. Catches future regressions (new unrevoked SECDEF fn).
DO $$
DECLARE
    leaked text;
BEGIN
    SELECT string_agg(p.oid::regprocedure::text, ', ')
    INTO leaked
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.prosecdef
      AND p.proname <> 'get_or_create_executor'
      AND ( has_function_privilege('anon', p.oid, 'EXECUTE')
         OR has_function_privilege('authenticated', p.oid, 'EXECUTE') );
    ASSERT leaked IS NULL,
        format('SECURITY DEFINER funcs anon/authenticated-executable: %s', leaked);
END $$;

-- Positive control: get_or_create_executor MUST stay anon-executable (login).
DO $$
BEGIN
    ASSERT has_function_privilege(
        'anon',
        'public.get_or_create_executor(text,text,text,text,text)'::regprocedure,
        'EXECUTE'),
      'get_or_create_executor lost anon EXECUTE — dashboard login will break';
END $$;
```

### Targeted unit assertions (name 4 explicit cases)
Add to the same test file — these document the previously-false `092:83-86` claims now being true:
1. `resolve_dispute(...)` — `has_function_privilege('anon', ..., 'EXECUTE')` is **false**.
2. `assign_task_to_executor(...)` — anon EXECUTE is **false**.
3. `fund_escrow(...)` — anon EXECUTE is **false**.
4. `escalate_to_arbitration(uuid)` — anon EXECUTE is **false** (was falsely "default-deny").

### Manual / E2E verification
1. **Staging, pre-fix (reproduce):** with the anon key, `POST /rest/v1/rpc/resolve_dispute` for a seeded open dispute → returns `{"success": true, ...}` and the `disputes` row is mutated. This is the bug.
2. **Apply migration 111** to staging.
3. **Staging, post-fix:** repeat the same anon `POST` → HTTP **403** (`permission denied for function resolve_dispute`). Repeat for `assign_task_to_executor`, `fund_escrow`, `release_final_payment` → all **403**.
4. **Dashboard login still works:** load the staging dashboard, connect a wallet → `get_or_create_executor` resolves the executor (no 403). Confirms the allowlist.
5. **Golden Flow:** run `python scripts/e2e_golden_flow.py` against staging → still PASS (the backend uses `service_role`, unaffected). Then run on production after the prod apply.

## Rollback plan

- The change is grant-only; rollback is to re-`GRANT EXECUTE ... TO PUBLIC` on the affected functions (template in the migration's ROLLBACK block). **Not recommended** — it re-opens the anon RLS bypass.
- If the production hotfix somehow blocks a legitimate path, the symptom would be a backend (`service_role`) call returning permission-denied — which cannot happen here, since the migration explicitly `GRANT ... TO service_role` on every function it touches. If observed, immediately re-run `GRANT EXECUTE ON FUNCTION <sig> TO service_role` for that function and investigate why the backend is not connecting as `service_role`.
- No data migration, so there is nothing to un-migrate.

## Verification checklist

- [ ] Read `092_revoke_anon_rpcs.sql` and confirmed only 15 functions revoked + false comments at `092:83-86`.
- [ ] Created `supabase/migrations/111_lockdown_security_definer_rpcs.sql` (next free number `111`).
- [ ] Migration loops `pg_proc` (`prosecdef`) and checks BOTH `anon` AND `authenticated` `EXECUTE` privilege.
- [ ] Allowlist contains exactly `get_or_create_executor` and nothing else.
- [ ] Migration's built-in assertion passes on a freshly-migrated DB.
- [ ] Added `supabase/tests/test_security_definer_rpc_grants.sql`; it FAILS at migration ≤ 110 and PASSES at ≥ 111; wired into migration-test CI.
- [ ] Pre-fix repro on staging: anon `POST /rest/v1/rpc/resolve_dispute` succeeds.
- [ ] Post-fix on staging: anon calls to `resolve_dispute`, `assign_task_to_executor`, `fund_escrow`, `release_final_payment` all return 403.
- [ ] Dashboard login (`get_or_create_executor`) still works post-fix (no 403).
- [ ] `scripts/e2e_golden_flow.py` PASS on staging and on production after apply.
- [ ] Standalone hotfix run on production; the verification `SELECT` returns zero rows.
- [ ] Corrected `092:83-86` false comments are superseded by the COMMENT block in 111 (or 092 comments edited).
- [ ] Confirmed no Terraform / ECS / env / flag change was needed.
- [ ] Cross-referenced FIX-P0-02 for the separate `get_or_create_executor` DB-001 rebind concern (out of scope, noted in allowlist comment).
