# Schema Parity Audit — 2026-02-06

> Generated from live Supabase DB (`puyhpytmtkyevnxffksl`) vs local migrations (001-022).

## Summary

| Check | Status |
|-------|--------|
| All migrations applied | YES (001-022) |
| Tables match expected | YES |
| Columns match expected | YES (3 new cols from 022 confirmed) |
| RPC functions present | YES (12 custom functions) |
| Unused tables exist | YES (`escrows`, `payments`, `withdrawals`) |
| Analytics use correct source | YES (all from `tasks`/`submissions`) |

## Tables in Live DB

| Table | Columns | Used by API | Notes |
|-------|---------|-------------|-------|
| `tasks` | 28 | YES | Primary table for everything |
| `submissions` | 22 | YES | Includes 022 evidence columns |
| `executors` | 33 | YES | Includes manually added cols |
| `disputes` | 15 | YES | Arbitration flow |
| `api_keys` | 17 | YES | Agent authentication |
| `task_applications` | 8 | YES | Worker applications |
| `reputation_log` | 11 | YES | Includes 012 fix columns |
| `user_wallets` | 10 | YES | Wallet linking |
| `badges` | 17 | Partial | Schema exists, minting not wired |
| `platform_config` | 9 | YES | Admin settings |
| `config_audit_log` | 7 | YES | Config change audit trail |
| `escrows` | 17 | NO | Created by 015, not queried by API |
| `payments` | 23 | NO | Created by 015, not queried by API |

## Custom RPC Functions in Live DB

| Function | Migration | Used |
|----------|-----------|------|
| `apply_to_task` | 005 | YES — task acceptance |
| `auto_approve_submission` | 010 | YES — auto-approve trigger |
| `create_executor_profile` | 005 | YES — registration |
| `expire_tasks` | 005 | YES — scheduled |
| `get_config` | 014 | YES — platform config |
| `get_or_create_executor` | 005+012 | YES — login flow |
| `link_wallet_to_session` | 008 (x2 overloads) | YES — wallet auth |
| `platform_config_audit` | 014 | YES — trigger function |
| `release_task` | 005 | YES — task release |
| `update_executor_profile` | 011 | YES — profile updates |
| `update_executor_stats` | 005 | YES — stats trigger |
| `update_updated_at` | 001 | YES — trigger |
| `update_updated_at_column` | 001 | YES — trigger |

## Migration Application Status

| Migration | File | Applied |
|-----------|------|---------|
| 001 | `initial_schema.sql` | YES |
| 002 | `escrow_and_payments.sql` | YES |
| 003 | `add_badges.sql` | YES |
| 004 | `add_task_applications.sql` | YES |
| 005 | `rpc_functions.sql` | YES |
| 006 | `rls_policies.sql` | YES |
| 007 | `seed_data.sql` | YES |
| 008 | `fix_session_linking.sql` | YES |
| 009 | `require_wallet_signature.sql` | YES |
| 010 | `auto_approve_submissions.sql` | YES |
| 011 | `update_executor_profile.sql` | YES |
| 012 | `fix_executor_overload.sql` | YES |
| 013 | `fix_submissions_and_task_release.sql` | YES |
| 014 | `create_platform_config.sql` | YES |
| 015 | `payment_ledger_canonical.sql` | YES |
| 016 | `add_settlement_method.sql` | YES |
| 017 | `orphaned_payment_alerts.sql` | YES |
| 018 | `add_retry_count.sql` | YES |
| 019 | `add_refund_tx_to_tasks.sql` | YES |
| 020 | `tasks_erc8004_agent_id.sql` | YES |
| 021 | `add_reputation_tx_to_submissions.sql` | YES |
| 022 | `evidence_forensic_metadata.sql` | YES |

## Columns Added by Migration 022 (Verified in Live DB)

| Column | Table | Type | Status |
|--------|-------|------|--------|
| `evidence_metadata` | submissions | JSONB | CONFIRMED |
| `storage_backend` | submissions | VARCHAR(20) | CONFIRMED |
| `evidence_content_hash` | submissions | VARCHAR(66) | CONFIRMED |

## Unused Tables Assessment

### `escrows` table (17 columns)
- Created by migration 002, updated by 015
- **Not queried by any API endpoint** — all escrow data derived from `tasks.escrow_tx`/`tasks.bounty_usd`
- **Decision**: Keep in DB (harmless), do NOT add queries — current approach is simpler

### `payments` table (23 columns, includes 016 settlement_method)
- Created by migration 002, updated by 015+016
- **Not queried by any API endpoint** — payment data from `submissions.payment_tx`
- **Decision**: Keep in DB (harmless), future payment audit system could use it

## Analytics Data Sources (P1-MET-001 Verification)

All analytics endpoints confirmed to use correct data sources:

| Metric | Source | Endpoint |
|--------|--------|----------|
| Total payment volume | `SUM(tasks.bounty_usd)` | `/admin/stats`, `/admin/payments/stats` |
| Platform fees | `8% of completed tasks bounty` | `/admin/stats`, `/admin/payments/stats` |
| Active escrow | `SUM(bounty) WHERE status IN (published,accepted,in_progress,submitted)` | `/admin/stats` |
| Task counts | `COUNT(*) GROUP BY status` | `/admin/stats`, `/public/metrics` |
| Worker counts | `COUNT(executors)` | `/admin/stats`, `/public/metrics` |
| Agent counts | `COUNT(api_keys WHERE is_active)` | `/admin/stats`, `/public/metrics` |
| Orphaned payments | `submissions WHERE agent_verdict IN (accepted,approved) AND payment_tx IS NULL` | `/admin/payments/orphaned` |

## New Endpoint Added (P1-MET-003)

`GET /health/sanity` — Periodic metrics sanity check that verifies:
1. Task status distribution is queryable
2. Completed tasks have payment evidence (`payment_tx` or `escrow_tx`)
3. Active tasks have executors assigned
4. No tasks stuck in active state >24h
5. No orphaned submissions (referencing deleted tasks)
6. No active tasks with $0 bounty
