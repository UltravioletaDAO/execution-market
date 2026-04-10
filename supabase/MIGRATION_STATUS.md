---
date: 2026-04-09
tags:
  - type/report
  - domain/infrastructure
  - domain/operations
status: active
related-files:
  - supabase/migrations/
---

# Migration Status

Tracking production application status for all Supabase migrations.

**Legend:**
- APPLIED: Confirmed applied to production
- PENDING: Self-annotated as pending in migration header
- ASSUMED APPLIED: No annotation but part of numbered sequence; assumed applied

## Status Table

| # | File | Production Status | Notes |
|---|------|-------------------|-------|
| 001 | `001_initial_schema.sql` | APPLIED | Core schema |
| 002 | `002_escrow_and_payments.sql` | APPLIED | Escrow + payment tables |
| 003 | `003_reputation_system.sql` | APPLIED | Reputation log, ratings, badges |
| 004 | `004_disputes.sql` | APPLIED | Dispute + arbitration |
| 005 | `005_rpc_functions.sql` | APPLIED | Core RPC functions |
| 006 | `006_api_keys.sql` | APPLIED | API key table |
| 007 | `007_platform_config.sql` | APPLIED | Platform config |
| 008 | `008_fix_session_linking.sql` | APPLIED | Session linking fix |
| 009 | `009_require_wallet_signature.sql` | APPLIED | Wallet signature requirement |
| 010 | `010_auto_approve_submissions.sql` | APPLIED | Auto-approve trigger |
| 011 | `011_update_executor_profile.sql` | APPLIED | Executor profile |
| 012 | `012_fix_executor_overload.sql` | APPLIED | Executor column fixes |
| 013 | `013_fix_submissions_and_task_release.sql` | APPLIED | Submission fixes |
| 014 | `014_create_platform_config.sql` | APPLIED | Platform config v2 |
| 015 | `015_payment_ledger_canonical.sql` | APPLIED | Payment ledger |
| 016 | `016_add_settlement_method.sql` | APPLIED | Settlement method column |
| 017 | `017_orphaned_payment_alerts.sql` | APPLIED | Orphaned payment alerts |
| 018 | `018_add_retry_count.sql` | APPLIED | Retry count column |
| 019 | `019_add_refund_tx_to_tasks.sql` | APPLIED | Refund TX column |
| 020 | `020_tasks_erc8004_agent_id.sql` | APPLIED | ERC-8004 agent ID |
| 021 | `021_add_reputation_tx_to_submissions.sql` | APPLIED | Reputation TX column |
| 022 | `022_evidence_forensic_metadata.sql` | APPLIED | Evidence forensic metadata |
| 023 | `023_add_payment_network.sql` | APPLIED | Payment network column |
| 024 | `024_update_executor_profile_v2.sql` | APPLIED | Executor profile v2 |
| 025 | `025_fix_bounty_constraint.sql` | APPLIED | Bounty constraint fix |
| 026 | `026_submit_work_rpc.sql` | APPLIED | Submit work RPC |
| 027 | `027_payment_events.sql` | APPLIED | Payment events audit trail |
| 028 | `028_erc8004_side_effects.sql` | APPLIED | ERC-8004 side effects |
| 029 | `029_feedback_documents.sql` | APPLIED | Feedback documents |
| 030 | `030_update_platform_fee_fase3.sql` | APPLIED | Platform fee update |
| 031 | `031_agent_executor_support.sql` | APPLIED | Agent executor support |
| 032 | `032_gas_dust_tracking.sql` | APPLIED | Gas dust tracking |
| 033 | `033_agent_cards.sql` | APPLIED | Agent cards |
| 034 | `034_h2a_marketplace.sql` | APPLIED | H2A marketplace |
| 035 | `035_executor_profile_extended.sql` | APPLIED | Extended executor profile |
| 036 | `036_h2a_rls_policies.sql` | APPLIED | H2A RLS policies |
| 037 | `037_kk_swarm_state.sql` | APPLIED | KK swarm state |
| 038 | `038_unique_task_application.sql` | APPLIED | Unique task application constraint |
| 039 | `039_payment_token_symbol.sql` | APPLIED | Payment token symbol |
| 040 | `040_verification_phase3.sql` | APPLIED | Verification phase 3 |
| 041 | `041_skills_required_index.sql` | APPLIED | Skills required index |
| 042 | `042_solana_support.sql` | APPLIED | Solana support |
| 043 | `043_security_advisor_fixes.sql` | APPLIED | Security advisor fixes |
| 044 | `044_add_location_coordinates.sql` | APPLIED | Location coordinates |
| 045 | `045_payment_events_worker_read_policy.sql` | APPLIED | Worker read policy on payment_events |
| 046 | `046_fix_ratings_bidirectional.sql` | APPLIED | Bidirectional ratings fix |
| 047 | `047_applications_view.sql` | APPLIED | Applied 2026-03-15 per header |
| 048 | `048_performance_composite_indexes.sql` | **PENDING** | Self-annotated pending |
| 049 | `049_performance_indexes_p1.sql` | **PENDING** | Self-annotated pending |
| 050 | `050_reputation_tampering_guard.sql` | **PENDING** | Self-annotated pending. Executor field tampering guard. |
| 051 | `051_fix_task_assignment_race.sql` | **PENDING** | Self-annotated pending |
| 052 | `052_fix_reputation_volatility.sql` | **PENDING** | Self-annotated pending |
| 053 | `053_payment_events_check.sql` | **PENDING** | Self-annotated pending |
| 054 | `054_rls_performance_helpers.sql` | **PENDING** | Self-annotated pending. Helper functions for RLS. |
| 055 | `055_rls_refactor_policies.sql` | **PENDING** | Self-annotated pending. RLS refactor. |
| 056 | `056_not_null_constraints.sql` | **PENDING** | Self-annotated pending |
| 057 | `057_missing_timestamps.sql` | **PENDING** | Self-annotated pending |
| 058 | `058_escrow_expiry_validation.sql` | **PENDING** | Self-annotated pending |
| 059 | `059_evidence_schema_check.sql` | **PENDING** | Self-annotated pending |
| 060 | `060_platform_metrics_views.sql` | **PENDING** | Self-annotated pending |
| 061 | `061_balance_reconciliation.sql` | **PENDING** | Self-annotated pending |
| 062 | `062_rls_security_hardening.sql` | ASSUMED APPLIED | Auth hardening, date 2026-03-16 |
| 063 | `063_escrow_submission_trigger.sql` | ASSUMED APPLIED | Escrow validation, date 2026-03-19 |
| 064 | `064_webhooks.sql` | ASSUMED APPLIED | Webhooks, made idempotent 2026-03-28 |
| 065 | `065_irc_identities.sql` | ASSUMED APPLIED | IRC identity system |
| 066 | `066_task_chat_log.sql` | ASSUMED APPLIED | Task chat log |
| 067 | `067_worker_availability.sql` | ASSUMED APPLIED | Worker availability |
| 068 | `068_task_bids.sql` | ASSUMED APPLIED | Task bids |
| 069 | `069_relay_chains.sql` | ASSUMED APPLIED | Relay chains |
| 070 | `070_executor_language_preference.sql` | ASSUMED APPLIED | Language preference |
| 071 | `071_reports_and_blocked_users.sql` | ASSUMED APPLIED | Reports and blocked users |
| 072 | `072_clamp_reputation_score.sql` | ASSUMED APPLIED | Reputation score clamp |
| 073 | `073_backfill_escrow_payer_wallet.sql` | ASSUMED APPLIED | Backfill escrow payer |
| 074 | `074_revert_escrow_payer_wallet.sql` | ASSUMED APPLIED | Revert backfill |
| 075 | `075_security_advisor_fixes_v2.sql` | ASSUMED APPLIED | Security advisor v2, date 2026-03-25 |
| 076 | `076_admin_actions_log.sql` | ASSUMED APPLIED | Admin actions log |
| 077 | `077_performance_indexes_critical.sql` | ASSUMED APPLIED | Critical perf indexes |
| 078 | `078_verification_inferences.sql` | ASSUMED APPLIED | Verification inferences |
| 079 | `079_add_assigned_at_to_tasks.sql` | ASSUMED APPLIED | assigned_at column |
| 080 | `080_add_skill_version_to_tasks.sql` | ASSUMED APPLIED | skill_version column |
| 081 | `081_task_lifecycle_checkpoints.sql` | ASSUMED APPLIED | Lifecycle checkpoints |
| 082 | `082_social_links.sql` | ASSUMED APPLIED | Social links |
| 083 | `083_rls_admin_actions_and_spatial.sql` | ASSUMED APPLIED | Admin + spatial RLS |
| 084 | `084_world_id_verification.sql` | ASSUMED APPLIED | World ID verification table |
| 085 | `085_world_id_rls.sql` | ASSUMED APPLIED | World ID RLS |
| 086 | `086_world_agentkit.sql` | ASSUMED APPLIED | World AgentKit |
| 087 | `087_ens_integration.sql` | ASSUMED APPLIED | ENS integration |
| 088 | `088_add_missing_task_categories.sql` | ASSUMED APPLIED | Missing task categories |
| 089 | `089_escrow_add_missing_columns.sql` | ASSUMED APPLIED | Escrow missing columns |
| 090 | `090_fix_ambiguous_column_rpc.sql` | ASSUMED APPLIED | Fix ambiguous column |
| 091 | `091_arbiter_support.sql` | ASSUMED APPLIED | Arbiter support |
| 092 | `092_revoke_anon_rpcs.sql` | ASSUMED APPLIED | Security Phase 0+1: revoke anon RPCs |
| 093 | `093_evidence_bucket_rls.sql` | ASSUMED APPLIED | Evidence bucket RLS |
| 094 | `094_delete_plaintext_api_key.sql` | ASSUMED APPLIED | Delete plaintext API key |
| 095 | `095_restrict_public_views.sql` | ASSUMED APPLIED | Phase 2 RLS: restrict public views |

## Observations

### No Duplicate Migration Numbers
The previously reported duplicate 031 has been resolved. Migrations 031 (`agent_executor_support`) and 032 (`gas_dust_tracking`) are correctly numbered.

### Pending Migrations (048-061)
14 migrations from the DB Optimization audit (2026-03-15) are self-annotated as "pending". These cover:
- Performance indexes (048, 049)
- Reputation tampering guard (050)
- Race condition fixes (051)
- Reputation volatility fix (052)
- Payment events check constraints (053)
- RLS performance helpers and refactor (054, 055)
- NOT NULL constraints (056)
- Missing timestamps (057)
- Escrow expiry validation (058)
- Evidence schema check (059)
- Platform metrics views (060)
- Balance reconciliation (061)

**Action required:** Verify against live database whether any of these were applied since annotation. Run in Supabase SQL Editor:
```sql
SELECT tablename, indexname FROM pg_indexes
WHERE indexname LIKE 'idx_%composite%' OR indexname LIKE 'idx_%performance%';
```

### DB Audit Findings (Remaining)

**reputation_log append-only:** The `reputation_log` table has RLS enabled with:
- `reputation_log_select_public`: SELECT for all (public read)
- `reputation_log_service_role`: ALL for service_role

The service_role policy allows UPDATE/DELETE, but this is by design since service_role bypasses RLS anyway. Non-service-role users cannot UPDATE or DELETE because there is no permissive policy for those operations. The table is effectively append-only for non-admin roles.

**payment_events RLS:** Originally service_role only (migration 027). Migration 045 added a read policy for authenticated workers to view payment events for their own tasks. This is appropriate -- workers need TX hashes for their mobile app timeline. Write access remains service_role only.
