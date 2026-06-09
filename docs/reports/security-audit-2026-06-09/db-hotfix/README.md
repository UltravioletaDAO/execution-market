---
date: 2026-06-09
tags:
  - type/runbook
  - domain/security
  - domain/database
status: active
related-files:
  - supabase/migrations/111_revoke_and_harden_get_or_create_executor.sql
  - supabase/migrations/112_executor_immutable_trust_columns_guard.sql
  - supabase/migrations/113_lockdown_security_definer_rpcs.sql
  - supabase/migrations/114_payment_events_revoke_anon.sql
  - supabase/migrations/115_dispute_resolution_recusal_guard.sql
  - supabase/migrations/116_db004_verification_tables_anon_write_lockdown.sql
  - supabase/migrations/117_revoke_anon_orphaned_payments.sql
---

# DB Hotfix Scripts — Security Audit 2026-06-09 (WS-DB)

Standalone, **idempotent** SQL the operator pastes into the **Supabase SQL
editor** to apply the database remediations immediately, before the forward
migrations (`supabase/migrations/111`–`117`) land via the normal deploy. Each
script mirrors its migration exactly and is safe to re-run.

Run as the project owner (the Supabase SQL editor connects as a
superuser-equivalent that can REVOKE on functions it does not own).

## Apply order (recommended)

| # | Script | Finding | What it does |
|---|--------|---------|--------------|
| 1 | `hotfix-FIX-P0-02-get-or-create-executor.sql` | **P0-02** | Revoke `get_or_create_executor` from anon/authenticated + harden the body against cross-session identity rebind. **Apply first — stops active exploitation.** |
| 2 | `hotfix-FIX-P1-05-lockdown-security-definer-rpcs.sql` | P1-05 | Revoke anon/authenticated EXECUTE on every SECURITY DEFINER money/state RPC (dynamic, signature-agnostic). |
| 3 | `hotfix-FIX-P1-04-executor-immutable-guard.sql` | P1-04 | Extend the immutable-field guard to World ID / VeryAI / ClawKey / KYC / balance / wallet / status / erc8004 columns. |
| 4 | `hotfix-FIX-P1-03-payment-events-revoke-anon.sql` | P1-03 | Defense-in-depth: payment_events anon=none, authenticated=SELECT-only. (Real fix is the API ownership check.) |
| 5 | `hotfix-FIX-P1-08-dispute-recusal-trigger.sql` | P1-08 | Recusal trigger: a dispute party cannot be the resolver. |
| 6 | `hotfix-DB-004-verification-tables-anon-write.sql` | DB-004 / Phase 2.3 | Close anon-writable regression on `veryai_verifications` + `agent_kya_verifications` (scope write policies to service_role). |
| 7 | `hotfix-Phase2.4-revoke-anon-orphaned-payments.sql` | Phase 2.4 | Revoke anon read of `v_orphaned_payments` + `get_orphaned_payment_count()`. |

Order matters only loosely: 1 first (P0). The rest are independent and each is
self-contained. All are idempotent.

## Secondary migration tree

The repo also carries a second migration tree at
`mcp_server/supabase/migrations/`. If **that** tree is the one applied to a given
database, also apply
`mcp_server/supabase/migrations/20260609000001_revoke_anon_security_definer_rpcs.sql`
(same dynamic lockdown). It re-locks the anon-granted SECURITY DEFINER RPCs
(`get_or_create_executor`, `assign_task`, `complete_task`, `update_reputation`)
that `20260125000003_rpc_functions.sql:678-684` re-granted.

## After applying — verify

Each script ends with a verification `SELECT`. Expected results:

- P0-02 / P1-05: `anon` and `authenticated` cannot EXECUTE the locked RPCs; the
  P1-05 verify `SELECT` returns **zero rows**.
- P1-03: `anon` no access; `authenticated` SELECT-only on `payment_events`.
- DB-004: `anon`/`authenticated` cannot INSERT into the verification tables.
- Phase 2.4: `anon`/`authenticated` cannot SELECT `v_orphaned_payments`;
  `service_role` still can.

## Post-fix audit note (P0-02)

After applying hotfix #1, audit `executors` for rows whose `user_id` may have
been hijacked during the 097→111 exposure window (compare `last_active_at` /
`updated_at` against the deployment window; cross-check `user_wallets` and
`auth.users.raw_user_meta_data.wallet_address`). Revert any orphaned/hijacked
`user_id` and check for `executors.wallet_address` overwrites that could have
redirected payouts. The hotfix stops further takeover but does not auto-restore
rows already mutated by the live bug.

## Tests

Grant-state + behavioural regression tests live at:
- `supabase/tests/test_migration_111_to_117.sql`
- `supabase/tests/test_fix_p0_02_p1_04_p1_08_behavior.sql`

Both were validated on a local PostgreSQL 15 + PostGIS engine with the Supabase
role topology (anon/authenticated/service_role + `auth.uid()`/`auth.jwt()`
shims). The behavioural suite fails on a pre-fix database (reproduces the
takeover/self-elevation) and passes at migration ≥ 117.
