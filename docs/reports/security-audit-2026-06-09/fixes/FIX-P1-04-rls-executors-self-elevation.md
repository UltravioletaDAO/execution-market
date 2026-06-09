---
date: 2026-06-09
tags: [type/incident, domain/security]
status: active
severity: P1
finding_id: FIX-P1-04
---
# FIX-P1-04 — RLS self-elevation: workers can self-set World ID / VeryAI / KYC flags and edit wallet_address & balance on their own executor row

## Summary
The `executors_update_own` RLS policy (migration `001`) grants any authenticated browser a column-unrestricted `UPDATE` on its own `executors` row, and the only compensating control — the `prevent_executor_tampering` trigger (migration `050`) — guards just five reputation/stats columns. A worker can therefore issue a single `PATCH /rest/v1/executors?id=eq.<self>` to self-set `world_id_verified=true, world_id_level='orb', veryai_verified=true, is_verified=true` and defeat the platform's proof-of-humanity / anti-sybil gate on the highest-value tasks (≥ $500 Orb requirement), because `worldid/enforcement.py` and `veryai/enforcement.py` read those exact user-mutable mirror columns. The same gap lets a worker overwrite `wallet_address`, `balance_usdc`, `total_earned_usdc`, `kyc_completed_at`, and `status` on its own row.

## Severity & Impact (why P1)
- **Anti-sybil / proof-of-humanity bypass (primary):** `check_world_id_enforcement` (`mcp_server/integrations/worldid/enforcement.py:89-100`) blocks high-value applications unless `executors.world_id_verified` is true **and** `executors.world_id_level == 'orb'`. Both columns are self-mutable. A single PATCH lifts the ≥ $500 Orb gate, the strongest KYC control on the platform. `check_veryai_enforcement` (`mcp_server/integrations/veryai/enforcement.py:67-77`) is bypassed identically for the ≥ $50 palm tier.
- **Integrity of KYC/verification state:** `is_verified`, `kyc_completed_at`, `veryai_*`, `clawkey_*` can be forged, corrupting trust badges surfaced in the dashboard/showcase and any downstream gating that trusts them.
- **Payout-destination & financial-mirror tampering:** `wallet_address` is the column the backend resolves to when looking up an executor by wallet; `balance_usdc`/`total_earned_usdc`/`total_withdrawn_usdc` are self-settable.
- **Why P1, not P0:** The `WITH CHECK (auth.uid() = user_id)` clause confines every edit to the **attacker's own** row — a worker cannot rewrite another user's `wallet_address` to redirect *their* payout, and the live withdrawal path does not treat `executors.balance_usdc` as an authoritative spendable balance (payouts flow from on-chain escrow release to the assigned worker; `workers.py`/`payments.py` aggregate from payment records). So this is a serious anti-sybil/KYC control bypass with a realistic single-request path, but not direct theft of a third party's funds or a full auth bypass.

## Affected code (file:line, redacted quotes)
- `supabase/migrations/001_initial_schema.sql:487-490` — the unrestricted policy:
  ```sql
  CREATE POLICY "executors_update_own" ON executors
      FOR UPDATE
      USING (auth.uid() = user_id)
      WITH CHECK (auth.uid() = user_id);   -- no column allowlist
  ```
- `supabase/migrations/050_reputation_tampering_guard.sql:9-37` — the incomplete guard (covers only `reputation_score`, `tier`, `tasks_completed`, `tasks_disputed`, `tasks_abandoned`):
  ```sql
  CREATE OR REPLACE FUNCTION prevent_executor_tampering() ...
      IF NEW.reputation_score IS DISTINCT FROM OLD.reputation_score THEN ...
      -- (only 5 columns checked; trust/financial columns NOT checked)
  CREATE TRIGGER guard_executor_immutable_fields
      BEFORE UPDATE ON executors FOR EACH ROW
      WHEN (current_setting('role', true) IS DISTINCT FROM 'service_role')
      EXECUTE FUNCTION prevent_executor_tampering();
  ```
- `supabase/migrations/095_restrict_public_views.sql:284-287` — smoking gun: revokes only `SELECT` from `anon`, comment states `authenticated keeps access via executors_update_own`. The `UPDATE` grant for `authenticated` is never revoked.
- `mcp_server/integrations/worldid/enforcement.py:89-100` — gate reads self-mutable mirror columns:
  ```python
  db_client.table("executors").select("world_id_verified, world_id_level").eq("id", executor_id)...
  if not wid_verified or wid_level != "orb":  # both columns user-settable
  ```
- `mcp_server/integrations/veryai/enforcement.py:67-77` — gate reads `veryai_verified` from the same self-mutable table.
- Trust columns live on `executors` and are user-mutable today: `world_id_verified, world_id_level` (`084:6-7`), `veryai_verified, veryai_level, veryai_sub, veryai_verified_at` (`104:7-11`), `clawkey_verified, clawkey_human_id, clawkey_device_id, clawkey_public_key, clawkey_registered_at` (`106:8-12`), and the original `is_verified, kyc_completed_at, balance_usdc, total_earned_usdc, total_withdrawn_usdc, status, erc8004_agent_id, wallet_address` (`001:117-140,150`).

## Root cause
`executors_update_own` is a **row-scoped** policy with no **column** allowlist (Postgres RLS has no native per-column `WITH CHECK`). The architecture relies entirely on a single `BEFORE UPDATE` trigger to enforce column immutability, but that trigger (`050`) was written before the World ID (`084`), VeryAI (`104`), and ClawKey (`106`) trust columns existed and was never extended to cover them — nor the pre-existing financial/identity columns. The verification source-of-truth tables (`world_id_verifications`/`veryai_verifications`) are correctly service-role-write-only (`085`/`092`/`105`), but the enforcement code trusts the **mirror columns on `executors`** instead of those protected tables, so the RLS gap is directly load-bearing for the anti-sybil decision.

## Exploit scenario (concrete attacker steps)
1. Worker opens the SPA; `AuthContext` calls `supabase.auth.signInAnonymously()`, giving the browser an `authenticated`-role JWT with `auth.uid()` set. `get_or_create_executor`/`link_wallet_to_session` bind `executors.user_id = auth.uid()` for the worker's row.
2. Worker sends, with the public anon key + their session JWT:
   ```http
   PATCH /rest/v1/executors?id=eq.<self> HTTP/1.1
   apikey: <anon_key>
   Authorization: Bearer <session_jwt>
   Prefer: return=minimal
   Content-Type: application/json

   {"world_id_verified": true, "world_id_level": "orb",
    "veryai_verified": true, "is_verified": true}
   ```
3. `executors_update_own` permits it (`auth.uid() = user_id` holds); the `050` guard fires (role is `authenticated`, not `service_role`) but ignores all four columns. The write succeeds.
4. Worker applies to a $600 task. `check_world_id_enforcement` reads `executors.world_id_verified='true', world_id_level='orb'` and returns `(True, None)` — Orb anti-sybil bypassed. `check_veryai_enforcement` is bypassed identically for ≥ $50 tasks.

## The Fix (precise, code-level)

### Primary fix — extend the immutable-field guard (surgical, matches existing pattern)
Add the trust/financial/identity columns to `prevent_executor_tampering()`. The trigger already gates on `current_setting('role', true) IS DISTINCT FROM 'service_role'`, so the FastAPI backend (which uses the **service_role** key via `mcp_server/supabase_client.py:get_client()` → `SUPABASE_SERVICE_ROLE_KEY`) keeps writing these columns; only direct browser (`anon`/`authenticated`) writes are blocked.

**Backward-compatibility — verified safe:**
- The legitimate SPA profile-edit paths write **only non-protected** columns:
  - RPC `update_executor_profile` (`024`): `display_name, bio, skills, languages, location_city, location_country, email, avatar_url, phone, last_active_at`.
  - The browser direct-table fallback in `dashboard/src/hooks/useProfileUpdate.ts:99-113`: `display_name, bio, skills, languages, location_city, location_country, email, phone, avatar_url`.
  None of these overlap the guarded set, so legitimate edits are unaffected.
- The backend verification writers (`worldid.py:304-307`, `veryai.py`, `clawkey.py`, `jobs/clawkey_sync.py`) all go through `db.get_client()` (service_role) and so bypass the guard.
- **SECURITY DEFINER audit:** the three `SECURITY DEFINER` RPCs that `UPDATE executors` from a non-service_role caller — `update_executor_profile` (024), `get_or_create_executor` (008: UPDATE path sets only `last_active_at, user_id, email`), `link_wallet_to_session` (008: sets only `user_id, last_active_at`) — write **no** guarded column. (SECURITY DEFINER runs as the function owner, so `current_setting('role')` is NOT `service_role` inside them; the guard *would* fire — but since none touch guarded columns, none break.)

> Caution on the "drop the policy" alternative: dropping `executors_update_own` outright would break the SPA's legitimate direct-table profile-edit fallback (`useProfileUpdate.ts:110-113`) **and** `update_executor_profile` is already revoked from `authenticated` (migration `092`), so the RPC path also 403s from the browser. That route requires migrating all profile edits to the backend service_role API first. **Do NOT drop the policy in this fix.** Ship the guard extension now (closes the hole immediately); the policy-drop hardening is tracked separately (see Backlog note below).

#### Forward migration — `supabase/migrations/111_executor_immutable_trust_columns_guard.sql`
Create this new file (next free number is **111**; latest is `110_moonpay_onramp_attempts.sql`):

```sql
-- Migration 111: Extend executor immutable-field guard to trust/financial columns
-- Source: Security Audit 2026-06-09, finding FIX-P1-04
-- Closes the gap where executors_update_own (001) + the incomplete
-- prevent_executor_tampering trigger (050) let an authenticated browser
-- self-set World ID / VeryAI / ClawKey / KYC flags and edit wallet_address,
-- balance_usdc, status, and erc8004_agent_id on its OWN executor row.
--
-- The backend (service_role key, mcp_server/supabase_client.py) bypasses this
-- guard via the trigger's WHEN (current_setting('role') <> 'service_role')
-- clause, so all legitimate server-side writes (worldid.py, veryai.py,
-- clawkey.py, payment reconciliation) continue to work. The SPA profile-edit
-- paths only touch non-guarded columns and are unaffected.
--
-- Idempotent: CREATE OR REPLACE FUNCTION; the trigger from 050 is reused.
-- Applied to production: pending.

CREATE OR REPLACE FUNCTION prevent_executor_tampering()
RETURNS TRIGGER AS $$
BEGIN
    -- ---- Reputation & task stats (original 050 set — unchanged) ----
    IF NEW.reputation_score IS DISTINCT FROM OLD.reputation_score THEN
        RAISE EXCEPTION 'Cannot modify reputation_score directly — use backend functions';
    END IF;
    IF NEW.tier IS DISTINCT FROM OLD.tier THEN
        RAISE EXCEPTION 'Cannot modify tier directly — managed by update_executor_tier trigger';
    END IF;
    IF NEW.tasks_completed IS DISTINCT FROM OLD.tasks_completed THEN
        RAISE EXCEPTION 'Cannot modify tasks_completed directly — managed by task completion trigger';
    END IF;
    IF NEW.tasks_disputed IS DISTINCT FROM OLD.tasks_disputed THEN
        RAISE EXCEPTION 'Cannot modify tasks_disputed directly';
    END IF;
    IF NEW.tasks_abandoned IS DISTINCT FROM OLD.tasks_abandoned THEN
        RAISE EXCEPTION 'Cannot modify tasks_abandoned directly';
    END IF;

    -- ---- World ID trust flags (084) — anti-sybil gate source ----
    IF NEW.world_id_verified IS DISTINCT FROM OLD.world_id_verified THEN
        RAISE EXCEPTION 'Cannot modify world_id_verified directly — set by backend after World ID Cloud API verification';
    END IF;
    IF NEW.world_id_level IS DISTINCT FROM OLD.world_id_level THEN
        RAISE EXCEPTION 'Cannot modify world_id_level directly — set by backend';
    END IF;

    -- ---- VeryAI trust flags (104) ----
    IF NEW.veryai_verified IS DISTINCT FROM OLD.veryai_verified THEN
        RAISE EXCEPTION 'Cannot modify veryai_verified directly — set by backend after VeryAI OIDC verification';
    END IF;
    IF NEW.veryai_level IS DISTINCT FROM OLD.veryai_level THEN
        RAISE EXCEPTION 'Cannot modify veryai_level directly — set by backend';
    END IF;
    IF NEW.veryai_sub IS DISTINCT FROM OLD.veryai_sub THEN
        RAISE EXCEPTION 'Cannot modify veryai_sub directly — set by backend';
    END IF;
    IF NEW.veryai_verified_at IS DISTINCT FROM OLD.veryai_verified_at THEN
        RAISE EXCEPTION 'Cannot modify veryai_verified_at directly — set by backend';
    END IF;

    -- ---- ClawKey KYA flags (106) ----
    IF NEW.clawkey_verified IS DISTINCT FROM OLD.clawkey_verified THEN
        RAISE EXCEPTION 'Cannot modify clawkey_verified directly — set by backend ClawKey sync';
    END IF;
    IF NEW.clawkey_human_id IS DISTINCT FROM OLD.clawkey_human_id THEN
        RAISE EXCEPTION 'Cannot modify clawkey_human_id directly — set by backend';
    END IF;
    IF NEW.clawkey_device_id IS DISTINCT FROM OLD.clawkey_device_id THEN
        RAISE EXCEPTION 'Cannot modify clawkey_device_id directly — set by backend';
    END IF;
    IF NEW.clawkey_public_key IS DISTINCT FROM OLD.clawkey_public_key THEN
        RAISE EXCEPTION 'Cannot modify clawkey_public_key directly — set by backend';
    END IF;
    IF NEW.clawkey_registered_at IS DISTINCT FROM OLD.clawkey_registered_at THEN
        RAISE EXCEPTION 'Cannot modify clawkey_registered_at directly — set by backend';
    END IF;

    -- ---- Generic KYC / verification (001) ----
    IF NEW.is_verified IS DISTINCT FROM OLD.is_verified THEN
        RAISE EXCEPTION 'Cannot modify is_verified directly — set by backend';
    END IF;
    IF NEW.kyc_completed_at IS DISTINCT FROM OLD.kyc_completed_at THEN
        RAISE EXCEPTION 'Cannot modify kyc_completed_at directly — set by backend';
    END IF;

    -- ---- Financial mirror columns (001) ----
    IF NEW.balance_usdc IS DISTINCT FROM OLD.balance_usdc THEN
        RAISE EXCEPTION 'Cannot modify balance_usdc directly — managed by payment reconciliation';
    END IF;
    IF NEW.total_earned_usdc IS DISTINCT FROM OLD.total_earned_usdc THEN
        RAISE EXCEPTION 'Cannot modify total_earned_usdc directly — managed by payment reconciliation';
    END IF;
    IF NEW.total_withdrawn_usdc IS DISTINCT FROM OLD.total_withdrawn_usdc THEN
        RAISE EXCEPTION 'Cannot modify total_withdrawn_usdc directly — managed by payment reconciliation';
    END IF;

    -- ---- Identity / lifecycle ----
    IF NEW.wallet_address IS DISTINCT FROM OLD.wallet_address THEN
        RAISE EXCEPTION 'Cannot modify wallet_address directly — set at registration via backend';
    END IF;
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        RAISE EXCEPTION 'Cannot modify status directly — managed by backend';
    END IF;
    IF NEW.erc8004_agent_id IS DISTINCT FROM OLD.erc8004_agent_id THEN
        RAISE EXCEPTION 'Cannot modify erc8004_agent_id directly — set by backend after on-chain registration';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- The trigger from migration 050 (guard_executor_immutable_fields) already
-- points at this function with the correct service_role bypass; no DDL change
-- to the trigger is needed. Re-assert it defensively in case 050 was never
-- applied to this database.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'guard_executor_immutable_fields'
          AND tgrelid = 'public.executors'::regclass
    ) THEN
        CREATE TRIGGER guard_executor_immutable_fields
            BEFORE UPDATE ON executors
            FOR EACH ROW
            WHEN (current_setting('role', true) IS DISTINCT FROM 'service_role')
            EXECUTE FUNCTION prevent_executor_tampering();
        RAISE NOTICE '111: created missing guard_executor_immutable_fields trigger';
    ELSE
        RAISE NOTICE '111: guard_executor_immutable_fields trigger already present (reusing)';
    END IF;
END $$;

COMMENT ON FUNCTION prevent_executor_tampering() IS
    'Blocks non-service_role UPDATEs to immutable executor columns: reputation/stats (050) '
    'plus trust flags (world_id_*, veryai_*, clawkey_*, is_verified, kyc_completed_at), '
    'financial mirrors (balance_usdc, total_earned_usdc, total_withdrawn_usdc), and '
    'identity (wallet_address, status, erc8004_agent_id). Extended by migration 111 '
    '(Security Audit 2026-06-09, FIX-P1-04).';
```

#### Standalone production-hotfix SQL (paste into Supabase SQL editor)
Idempotent and self-contained — identical effect to migration 111 above. Safe to run before the migration lands in the repo deploy:

```sql
-- HOTFIX FIX-P1-04 — extend executor immutable-field guard. Idempotent.
BEGIN;

CREATE OR REPLACE FUNCTION prevent_executor_tampering()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.reputation_score   IS DISTINCT FROM OLD.reputation_score   THEN RAISE EXCEPTION 'Cannot modify reputation_score directly'; END IF;
    IF NEW.tier               IS DISTINCT FROM OLD.tier               THEN RAISE EXCEPTION 'Cannot modify tier directly'; END IF;
    IF NEW.tasks_completed    IS DISTINCT FROM OLD.tasks_completed    THEN RAISE EXCEPTION 'Cannot modify tasks_completed directly'; END IF;
    IF NEW.tasks_disputed     IS DISTINCT FROM OLD.tasks_disputed     THEN RAISE EXCEPTION 'Cannot modify tasks_disputed directly'; END IF;
    IF NEW.tasks_abandoned    IS DISTINCT FROM OLD.tasks_abandoned    THEN RAISE EXCEPTION 'Cannot modify tasks_abandoned directly'; END IF;
    IF NEW.world_id_verified  IS DISTINCT FROM OLD.world_id_verified  THEN RAISE EXCEPTION 'Cannot modify world_id_verified directly'; END IF;
    IF NEW.world_id_level     IS DISTINCT FROM OLD.world_id_level     THEN RAISE EXCEPTION 'Cannot modify world_id_level directly'; END IF;
    IF NEW.veryai_verified    IS DISTINCT FROM OLD.veryai_verified    THEN RAISE EXCEPTION 'Cannot modify veryai_verified directly'; END IF;
    IF NEW.veryai_level       IS DISTINCT FROM OLD.veryai_level       THEN RAISE EXCEPTION 'Cannot modify veryai_level directly'; END IF;
    IF NEW.veryai_sub         IS DISTINCT FROM OLD.veryai_sub         THEN RAISE EXCEPTION 'Cannot modify veryai_sub directly'; END IF;
    IF NEW.veryai_verified_at IS DISTINCT FROM OLD.veryai_verified_at THEN RAISE EXCEPTION 'Cannot modify veryai_verified_at directly'; END IF;
    IF NEW.clawkey_verified   IS DISTINCT FROM OLD.clawkey_verified   THEN RAISE EXCEPTION 'Cannot modify clawkey_verified directly'; END IF;
    IF NEW.clawkey_human_id   IS DISTINCT FROM OLD.clawkey_human_id   THEN RAISE EXCEPTION 'Cannot modify clawkey_human_id directly'; END IF;
    IF NEW.clawkey_device_id  IS DISTINCT FROM OLD.clawkey_device_id  THEN RAISE EXCEPTION 'Cannot modify clawkey_device_id directly'; END IF;
    IF NEW.clawkey_public_key IS DISTINCT FROM OLD.clawkey_public_key THEN RAISE EXCEPTION 'Cannot modify clawkey_public_key directly'; END IF;
    IF NEW.clawkey_registered_at IS DISTINCT FROM OLD.clawkey_registered_at THEN RAISE EXCEPTION 'Cannot modify clawkey_registered_at directly'; END IF;
    IF NEW.is_verified        IS DISTINCT FROM OLD.is_verified        THEN RAISE EXCEPTION 'Cannot modify is_verified directly'; END IF;
    IF NEW.kyc_completed_at   IS DISTINCT FROM OLD.kyc_completed_at   THEN RAISE EXCEPTION 'Cannot modify kyc_completed_at directly'; END IF;
    IF NEW.balance_usdc       IS DISTINCT FROM OLD.balance_usdc       THEN RAISE EXCEPTION 'Cannot modify balance_usdc directly'; END IF;
    IF NEW.total_earned_usdc  IS DISTINCT FROM OLD.total_earned_usdc  THEN RAISE EXCEPTION 'Cannot modify total_earned_usdc directly'; END IF;
    IF NEW.total_withdrawn_usdc IS DISTINCT FROM OLD.total_withdrawn_usdc THEN RAISE EXCEPTION 'Cannot modify total_withdrawn_usdc directly'; END IF;
    IF NEW.wallet_address     IS DISTINCT FROM OLD.wallet_address     THEN RAISE EXCEPTION 'Cannot modify wallet_address directly'; END IF;
    IF NEW.status             IS DISTINCT FROM OLD.status             THEN RAISE EXCEPTION 'Cannot modify status directly'; END IF;
    IF NEW.erc8004_agent_id   IS DISTINCT FROM OLD.erc8004_agent_id   THEN RAISE EXCEPTION 'Cannot modify erc8004_agent_id directly'; END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Ensure the trigger exists (no-op if migration 050 already created it)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'guard_executor_immutable_fields'
          AND tgrelid = 'public.executors'::regclass
    ) THEN
        CREATE TRIGGER guard_executor_immutable_fields
            BEFORE UPDATE ON executors FOR EACH ROW
            WHEN (current_setting('role', true) IS DISTINCT FROM 'service_role')
            EXECUTE FUNCTION prevent_executor_tampering();
    END IF;
END $$;

COMMIT;
```

> **Column-name caveat for the operator:** before running, confirm the live `executors` table actually has every referenced column (e.g. `veryai_verified_at`, all `clawkey_*`). If a database is behind on migrations `104`/`106`, a missing column reference in the function body raises at the first `UPDATE` (not at `CREATE FUNCTION`, because plpgsql is late-bound). If the target DB is missing 104/106, run those migrations first, or remove the corresponding `IF` blocks for columns that do not yet exist. The forward migration assumes 104 and 106 are applied (they are, per repo migration history through 110).

### Defense-in-depth (recommended, low-risk) — stop trusting the mutable mirror columns
Even with the guard, the enforcement code should cross-check the **service-role-write-only** source tables so a *future* RLS regression on `executors` cannot re-open the gate. Keep the existing read for the public badge, but make the **gate decision** depend on the protected table.

`mcp_server/integrations/worldid/enforcement.py` (around lines 89-100) — after reading the mirror columns, require a matching Orb row in `world_id_verifications` (RLS-protected, service-role write-only per `085`/`092`):
```python
wid_check = (
    db_client.table("executors")
    .select("world_id_verified, world_id_level")
    .eq("id", executor_id).limit(1).execute()
)
wid_data = wid_check.data[0] if wid_check.data else {}
mirror_ok = wid_data.get("world_id_verified") and wid_data.get("world_id_level") == "orb"

# Authoritative source: service-role-write-only verifications table.
src = (
    db_client.table("world_id_verifications")
    .select("verification_level")
    .eq("executor_id", executor_id)
    .eq("verification_level", "orb")
    .limit(1).execute()
)
source_ok = bool(src.data)

if not (mirror_ok and source_ok):
    return False, { "error": "world_id_orb_required", ... }  # existing body
return True, None
```
`mcp_server/integrations/veryai/enforcement.py` (lines 67-77) — analogously require a row in `veryai_verifications` for `executor_id` (service-role-write-only per `105`) in addition to `executors.veryai_verified`.

> Note: the `executors_safe` view (migration `095`) intentionally exposes `world_id_verified` as a public badge — keep that read path; only the gate decision changes to also consult the protected table.

This defense-in-depth change is **optional for closing P1** (the migration alone closes it) but strongly recommended; ship it gated behind no flag — it only tightens an existing check and adds one indexed lookup (`idx_world_id_verifications_executor`, `idx_veryai_verifications_executor` already exist).

### Infra / env / feature flag
None required. No Terraform change, no new env var, no ECS task-definition change. The backend already holds `SUPABASE_SERVICE_ROLE_KEY` (used by `get_client()`), which is what bypasses the guard.

### Backward-compatibility & rollout
- **Could this lock out legitimate agents?** No. Verified above: SPA profile edits and all server-side writers either touch no guarded column or run as `service_role`. The guard raises only on a *non-service_role* attempt to *change* a guarded column (`IS DISTINCT FROM OLD`), so a browser PATCH that includes a guarded field at its *unchanged* value is also fine.
- **Staged rollout:** apply the hotfix SQL to a staging Supabase project first; run the test plan below; then apply to production. The migration is idempotent and re-runnable.
- **Backlog (hardening, separate ticket):** migrate all SPA profile edits to the backend service_role API and then drop `executors_update_own` entirely (matches the `092`/`095` direction). Do not attempt in this fix — it requires the `useProfileUpdate.ts` direct-table fallback to be removed first or it will silently 403.

## Test plan

### DB regression tests (add `mcp_server/tests/test_rls_executor_immutable_guard.py` or a Supabase SQL test)
Run as a **non-service_role** session (anon/authenticated JWT) against a test executor row owned by the caller. Each block must reproduce the bug pre-fix (UPDATE succeeds) and pass post-fix (UPDATE raises). Suggested pytest names and assertions:

1. `test_worker_cannot_self_set_world_id_orb` — `UPDATE executors SET world_id_verified=true, world_id_level='orb' WHERE id=<self>` must raise a DB exception mentioning `world_id_verified`. (Pre-fix: succeeds — this is the reproducer.)
2. `test_worker_cannot_self_set_veryai_verified` — setting `veryai_verified=true` raises.
3. `test_worker_cannot_set_is_verified_or_kyc` — setting `is_verified=true` and `kyc_completed_at=now()` raises.
4. `test_worker_cannot_edit_wallet_address` — changing `wallet_address` raises.
5. `test_worker_cannot_inflate_balance` — setting `balance_usdc=1000000` raises.
6. `test_worker_cannot_change_status_or_agent_id` — changing `status` / `erc8004_agent_id` raises.
7. `test_worker_can_still_edit_profile` (regression-guard) — `UPDATE executors SET display_name='x', bio='y', skills=ARRAY['z'] WHERE id=<self>` **succeeds** (proves legitimate edits are not broken).
8. `test_service_role_can_set_world_id` — under a service_role session, `UPDATE executors SET world_id_verified=true, world_id_level='orb'` **succeeds** (proves backend writers unaffected).

### Backend integration test (enforcement)
9. Extend/add `mcp_server/tests/test_worldid_enforcement.py`: assert that for a `$600` bounty, when `executors.world_id_verified` is forged `true`/`orb` **but** no `world_id_verifications` Orb row exists, `check_world_id_enforcement` returns `(False, {...world_id_orb_required...})` — proves the defense-in-depth cross-check (only if the optional enforcement change is shipped).
10. Existing happy-path test: with a real `world_id_verifications` Orb row + mirror flags set by the backend, enforcement returns `(True, None)`.

### Manual / E2E verification
- Reproduce the exploit pre-fix on staging: with a worker session JWT, `curl -X PATCH "$SUPABASE_URL/rest/v1/executors?id=eq.<self>" -H "apikey: $ANON" -H "Authorization: Bearer $JWT" -H "Prefer: return=minimal" -H "Content-Type: application/json" -d '{"world_id_verified":true,"world_id_level":"orb"}'` → expect `204` pre-fix.
- After applying the hotfix → expect `400/500` with the `Cannot modify world_id_verified directly` message; row unchanged.
- Confirm a normal profile save in the dashboard (display name + bio) still succeeds end-to-end.
- Confirm the backend World ID verify flow (`POST /api/v1/worldid/verify`) still sets `world_id_verified`/`world_id_level` (service_role path) and the Orb badge appears.

## Rollback plan
- **Migration/hotfix rollback:** restore the original 5-column function body. Paste:
  ```sql
  -- ROLLBACK FIX-P1-04 (re-opens the hole — emergency use only)
  CREATE OR REPLACE FUNCTION prevent_executor_tampering()
  RETURNS TRIGGER AS $$
  BEGIN
      IF NEW.reputation_score IS DISTINCT FROM OLD.reputation_score THEN RAISE EXCEPTION 'Cannot modify reputation_score directly'; END IF;
      IF NEW.tier            IS DISTINCT FROM OLD.tier            THEN RAISE EXCEPTION 'Cannot modify tier directly'; END IF;
      IF NEW.tasks_completed IS DISTINCT FROM OLD.tasks_completed THEN RAISE EXCEPTION 'Cannot modify tasks_completed directly'; END IF;
      IF NEW.tasks_disputed  IS DISTINCT FROM OLD.tasks_disputed  THEN RAISE EXCEPTION 'Cannot modify tasks_disputed directly'; END IF;
      IF NEW.tasks_abandoned IS DISTINCT FROM OLD.tasks_abandoned THEN RAISE EXCEPTION 'Cannot modify tasks_abandoned directly'; END IF;
      RETURN NEW;
  END;
  $$ LANGUAGE plpgsql;
  ```
- **Enforcement code rollback (if defense-in-depth shipped):** revert `worldid/enforcement.py` and `veryai/enforcement.py` to read only the mirror columns and redeploy MCP (`deploy-mcp` skill). Note: rolling back the migration without rolling back nothing else is safe; rolling back the enforcement code while keeping the migration is also safe.
- Migration `111` itself is `CREATE OR REPLACE` + idempotent trigger creation — no data is mutated, so rollback is purely the function body swap above.

## Verification checklist
- [ ] Migration `supabase/migrations/111_executor_immutable_trust_columns_guard.sql` added with the full function body covering all listed columns.
- [ ] Standalone hotfix SQL applied to **staging**; exploit `PATCH` now returns an error (`Cannot modify world_id_verified directly`) and the row is unchanged.
- [ ] DB regression tests 1-8 added and green (each guarded-column UPDATE raises; profile-edit UPDATE and service_role UPDATE succeed).
- [ ] Confirmed legitimate SPA profile save (display_name/bio/skills/avatar/phone) still works end-to-end on staging.
- [ ] Confirmed backend World ID verify (`POST /api/v1/worldid/verify`) still sets `world_id_verified`/`world_id_level` and the Orb badge renders.
- [ ] Verified all four staging DBs / prod are at migration ≥ 106 so every referenced column exists (or guarded `IF` blocks adjusted for any DB behind on 104/106).
- [ ] (Optional, recommended) Defense-in-depth cross-check added to `worldid/enforcement.py` + `veryai/enforcement.py`; integration test 9 green; MCP redeployed.
- [ ] Hotfix SQL applied to **production**; exploit re-tested on prod and now blocked.
- [ ] Backlog ticket filed for the hardening follow-up (migrate profile edits server-side, then drop `executors_update_own`).
