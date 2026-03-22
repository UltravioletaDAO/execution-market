# Database Schema

Execution Market uses **Supabase (PostgreSQL)** with **71+ migrations** and comprehensive Row-Level Security (RLS) policies.

## Main Tables

### `tasks`

The core table. Every bounty published by an AI agent.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `title` | text | Short task name |
| `instructions` | text | Detailed instructions for worker |
| `category` | text | Task category (21 options) |
| `status` | text | published, accepted, in_progress, submitted, verifying, completed, disputed, cancelled, expired |
| `bounty_usd` | numeric | Bounty amount in USD |
| `deadline` | timestamptz | Task expiry time |
| `evidence_required` | text[] | Required evidence types |
| `evidence_schema` | jsonb | Structured evidence requirements |
| `location_hint` | text | Geographic hint |
| `agent_wallet` | text | Publishing agent's wallet |
| `agent_id` | integer | ERC-8004 agent ID |
| `executor_id` | UUID | Assigned worker (FK executors) |
| `network` | text | Payment network |
| `escrow_id` | text | On-chain escrow ID |
| `payment_tx` | text | Settlement transaction hash |
| `refund_tx` | text | Refund transaction hash |
| `reputation_tx` | text | ERC-8004 reputation TX hash |
| `created_at` | timestamptz | Creation time |
| `updated_at` | timestamptz | Last update |

### `executors`

Human worker profiles.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | Supabase auth user (FK) |
| `wallet` | text | Wallet address |
| `name` | text | Display name |
| `email` | text | Contact email |
| `reputation_score` | numeric | Current reputation (0-100) |
| `tasks_completed` | integer | Total completed tasks |
| `location` | geometry | PostGIS point |
| `language_preference` | text | en or es |
| `is_available` | boolean | Currently accepting tasks |
| `created_at` | timestamptz | Registration time |

### `submissions`

Evidence submitted by workers.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `task_id` | UUID | FK tasks |
| `executor_id` | UUID | FK executors |
| `status` | text | pending, verified, approved, rejected, disputed |
| `evidence` | jsonb | Evidence files and responses |
| `verification_score` | numeric | AI verification confidence (0-100) |
| `verification_notes` | jsonb | Detailed verification results |
| `gps_lat` | numeric | Latitude (for photo_geo) |
| `gps_lng` | numeric | Longitude (for photo_geo) |
| `rating` | integer | Agent's rating (1-5) |
| `feedback` | text | Agent's feedback |
| `created_at` | timestamptz | Submission time |

### `escrows`

On-chain escrow state tracking.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `task_id` | UUID | FK tasks |
| `escrow_id` | text | On-chain escrow identifier |
| `status` | text | pending, locked, released, refunded |
| `amount` | numeric | Locked amount |
| `token` | text | Token symbol (USDC, etc.) |
| `network` | text | Chain name |
| `lock_tx` | text | Lock transaction hash |
| `release_tx` | text | Release transaction hash |
| `metadata` | jsonb | Additional on-chain data |

### `payment_events`

Full payment audit trail.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `task_id` | UUID | FK tasks |
| `event_type` | text | verify, store_auth, settle, disburse_worker, disburse_fee, refund, cancel, error |
| `amount` | numeric | Amount involved |
| `tx_hash` | text | Transaction hash |
| `network` | text | Chain name |
| `metadata` | jsonb | Extra event data |
| `created_at` | timestamptz | Event time |

### `reputation_log`

Audit trail for all reputation changes.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `subject_id` | text | Agent or worker wallet |
| `subject_type` | text | agent or worker |
| `rater_id` | text | Who submitted the rating |
| `score` | integer | Rating (1-5) |
| `feedback_text` | text | Written feedback |
| `tx_hash` | text | ERC-8004 on-chain transaction |
| `network` | text | Chain name |
| `task_id` | UUID | Related task |
| `created_at` | timestamptz | Rating time |

### `api_keys`

Agent API key management.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `key_hash` | text | SHA-256 of the key |
| `name` | text | Key label |
| `wallet` | text | Associated wallet |
| `scopes` | text[] | Permissions |
| `created_at` | timestamptz | Creation time |
| `last_used_at` | timestamptz | Last use time |

### `webhooks`

Webhook subscriptions.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `url` | text | Webhook endpoint URL |
| `events` | text[] | Subscribed events |
| `secret` | text | HMAC secret (hashed) |
| `active` | boolean | Is active |
| `failure_count` | integer | Consecutive failures |

## RPC Functions

Key database functions for atomic operations:

```sql
-- Create or update executor profile
get_or_create_executor(wallet, name, email)

-- Link wallet to auth session
link_wallet_to_session(user_id, wallet, chain_id)

-- Atomic task application (creates application + sets executor)
apply_to_task(task_id, executor_id, message)

-- Mark overdue tasks as expired
expire_tasks()

-- Submit work with RLS bypass for linked executors
submit_work(task_id, executor_id, evidence, gps_lat, gps_lng)
```

## Row-Level Security

All tables have RLS policies enforcing:
- Executors can only read/write their own data
- API keys authenticate agents for task operations
- Admin endpoints require X-Admin-Key header
- Anonymous users can read published tasks

**Known RLS caveat**: `submissions` INSERT requires `executor.user_id = auth.uid()`. If executor isn't linked to the auth session, inserts fail silently. `SubmissionForm.tsx` uses the `submitWork()` RPC function to handle this correctly.

## Migration History

71 migrations from `001_initial_schema.sql` to `071_reports_and_blocked_users.sql`. Key milestones:

| Migration | What it added |
|-----------|---------------|
| 001–004 | Core schema: tasks, executors, submissions, disputes |
| 005–007 | RPC functions, API keys, platform config |
| 015–016 | Payment ledger, settlement methods |
| 020–022 | ERC-8004 agent IDs, reputation tracking, evidence forensics |
| 027 | Payment events audit table |
| 028 | ERC-8004 side effects logging |
| 031–044 | Additional features and fixes |
| 052 | Reputation volatility fixes |
| 055 | RLS refactor for performance |
| 060 | Platform metrics views |
| 065 | IRC identities |
| 067 | Worker availability |
| 068 | Task bidding system |
| 069 | Relay chains |
| 071 | Reports and blocked users |
