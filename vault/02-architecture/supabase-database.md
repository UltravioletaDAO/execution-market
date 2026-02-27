---
date: 2026-02-26
tags:
  - domain/architecture
  - component/database
  - tech/supabase
  - tech/postgresql
status: active
aliases:
  - Database
  - Supabase
  - PostgreSQL
related-files:
  - supabase/migrations/
  - mcp_server/db.py
---

# Supabase Database

**PostgreSQL via Supabase** with Row-Level Security (RLS). All data
persistence for tasks, workers, payments, and reputation.

## Core Tables

| Table | Purpose |
|-------|---------|
| `tasks` | Published bounties with evidence requirements |
| `executors` | Human workers and agent executors (wallet, reputation, location) |
| `submissions` | Evidence uploads with verification status |
| `applications` | Task applications from workers |
| `disputes` | Contested submissions with arbitration data |
| `reputation_log` | Audit trail for all reputation changes |
| `payment_events` | Payment lifecycle: verify, settle, disburse, refund, error |
| `escrows` | On-chain escrow state tracking (lock, release, refund) |
| `platform_config` | Feature flags, fee settings, platform parameters |

## Migrations

**40 migrations** (001 through 039, with some multi-part). Key milestones:

- 001-010: Core schema (tasks, executors, submissions)
- 011-020: Applications, disputes, reputation
- 021-030: Payment events, escrow tracking, gas dust
- 031-039: H2A tables, agent executor, payment_token, KK V2 support

## RPC Functions

| Function | Purpose |
|----------|---------|
| `get_or_create_executor(wallet, name, email)` | Upsert executor |
| `link_wallet_to_session(user_id, wallet, chain_id)` | Wallet-auth bridge |
| `apply_to_task(task_id, executor_id, message)` | Atomic task acceptance |
| `expire_tasks()` | Mark overdue tasks as expired |
| `create_executor_profile(...)` | New executor profile |

## Known RLS Issues

- `submissions` INSERT requires `executor.user_id = auth.uid()` -- fails
  silently if executor is not linked to anonymous session
- `human_wallet` column is PII, exposed via tasks SELECT (missing RLS)

## Related

- [[rls-policies]] -- RLS details and known gaps
- [[task-lifecycle]] -- state machine stored in tasks table
- [[rest-api]] -- CRUD operations on these tables
