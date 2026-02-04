# Execution Market Supabase Functions

This directory contains Supabase Edge Functions and SQL RPC functions for Execution Market.

## SQL RPC Functions (NOW-009)

Located in: `migrations/009_executor_rpc_functions.sql`

### Core Functions

| Function | Description | Auth |
|----------|-------------|------|
| `get_or_create_executor` | Get existing or create new executor by wallet | authenticated |
| `link_wallet_to_session_v2` | Link wallet address to user session | authenticated |
| `get_nearby_tasks` | Find tasks within radius (Haversine) | public |
| `update_executor_reputation` | Update reputation with Bayesian average | authenticated |
| `get_executor_stats` | Get comprehensive executor statistics | public |
| `get_executor_tasks` | Get tasks assigned to executor | authenticated |
| `claim_task` | Claim an open task | authenticated |
| `abandon_task` | Abandon a claimed task (with penalty) | authenticated |

### Usage Examples

```typescript
// Get or create executor
const { data, error } = await supabase.rpc('get_or_create_executor', {
  p_wallet_address: '0x1234...abcd',
  p_email: 'user@example.com',  // optional
  p_display_name: 'CryptoWorker'  // optional
});
// Returns: { id, wallet_address, reputation_score, tier, is_new, ... }

// Link wallet to session
const { data } = await supabase.rpc('link_wallet_to_session_v2', {
  p_user_id: 'uuid-of-user',
  p_wallet_address: '0x1234...abcd'
});
// Returns: true

// Find nearby tasks
const { data } = await supabase.rpc('get_nearby_tasks', {
  p_lat: 25.7617,
  p_lng: -80.1918,
  p_radius_km: 50,
  p_limit: 20,
  p_category: 'physical_presence',  // optional
  p_min_bounty: 5.00  // optional
});
// Returns: [{ id, title, bounty_usd, distance_km, ... }]

// Update reputation
const { data } = await supabase.rpc('update_executor_reputation', {
  p_executor_id: 'executor-uuid',
  p_task_id: 'task-uuid',
  p_rating: 85,  // 1-100
  p_task_value: 25.00
});
// Returns: new Bayesian score

// Claim task
const { data } = await supabase.rpc('claim_task', {
  p_task_id: 'task-uuid',
  p_executor_id: 'executor-uuid'
});
// Returns: { success, task_id, claimed_at, ... }
```

## Edge Functions

Located in: `functions/`

### executor-management

HTTP endpoints wrapping the SQL RPC functions.

**Deploy:**
```bash
supabase functions deploy executor-management
```

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/get-or-create` | Create or fetch executor |
| POST | `/link-wallet` | Link wallet to session |
| GET | `/stats/:executorId` | Get executor statistics |
| GET/POST | `/nearby-tasks` | Search tasks by location |
| POST | `/claim-task` | Claim an open task |
| POST | `/abandon-task` | Abandon a claimed task |

**Example Requests:**

```bash
# Get or create executor
curl -X POST 'https://your-project.supabase.co/functions/v1/executor-management/get-or-create' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"wallet_address": "0x1234...abcd"}'

# Get nearby tasks
curl 'https://your-project.supabase.co/functions/v1/executor-management/nearby-tasks?lat=25.76&lng=-80.19&radius_km=50'

# Claim task
curl -X POST 'https://your-project.supabase.co/functions/v1/executor-management/claim-task' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"task_id": "uuid", "executor_id": "uuid"}'
```

## Database Tables

Created by migration 009:

### user_wallets
Links multiple wallet addresses to a single Supabase user.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to auth.users |
| wallet_address | VARCHAR(255) | Ethereum address |
| is_primary | BOOLEAN | Primary wallet flag |
| chain_id | INTEGER | Network ID (default 1) |
| label | VARCHAR(100) | User-defined label |

### ratings
Individual ratings for Bayesian reputation calculation.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| executor_id | UUID | Rated executor |
| task_id | UUID | Related task |
| rater_id | VARCHAR | Agent or user who rated |
| rating | INTEGER | Score 1-100 |
| task_value | DECIMAL | Bounty for weighting |

## Reputation System

Execution Market uses **Bayesian Average** with task-value weighting and time decay:

```
Score = (C * m + sum(ratings * weight)) / (C + sum(weights))

where:
  C = 15 (confidence constant)
  m = 50 (prior mean - neutral starting point)
  weight = log(task_value + 1) * decay^months_old
  decay = 0.9 (monthly decay factor)
```

### Tiers

| Tier | Tasks | Min Score | Features |
|------|-------|-----------|----------|
| probation | < 10 | - | Max $5 tasks, extra verification |
| standard | 10-49 | 60 | Normal access |
| verified | 50-99 | 75 | Priority matching |
| expert | 100-199 | 85 | High-value tasks |
| master | 200+ | 90 | Premium features |

## Deployment

### Apply SQL Migrations

```bash
# Using Supabase CLI
supabase db push

# Or manually via SQL editor
psql -h your-db-host -U postgres -d postgres -f migrations/009_executor_rpc_functions.sql
```

### Deploy Edge Functions

```bash
# Set environment variables
supabase secrets set SUPABASE_URL=https://your-project.supabase.co
supabase secrets set SUPABASE_ANON_KEY=your-anon-key

# Deploy
supabase functions deploy executor-management
```

## Testing

```bash
# Test RPC functions locally
supabase start
supabase db reset

# Test Edge Functions
supabase functions serve executor-management --no-verify-jwt

# In another terminal
curl -X POST 'http://localhost:54321/functions/v1/executor-management/get-or-create' \
  -H 'Content-Type: application/json' \
  -d '{"wallet_address": "0x1234567890123456789012345678901234567890"}'
```
