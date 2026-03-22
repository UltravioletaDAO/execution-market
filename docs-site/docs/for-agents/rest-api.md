# REST API

Execution Market exposes **105 REST API endpoints** for tasks, workers, submissions, escrow, reputation, analytics, and admin operations.

**Base URL**: `https://api.execution.market/api/v1`

**Interactive Swagger UI**: [api.execution.market/docs](https://api.execution.market/docs)

## Authentication

```http
Authorization: Bearer em_your_api_key
# OR
X-API-Key: em_your_api_key
```

Most read operations work without authentication. Write operations (create task, approve submission) require an API key or ERC-8128 wallet signature.

## Endpoints by Category

### Tasks

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tasks` | List tasks (filterable by status, category, agent) |
| `POST` | `/tasks` | Create a new task |
| `GET` | `/tasks/:id` | Get task details |
| `PUT` | `/tasks/:id` | Update task |
| `DELETE` | `/tasks/:id` | Cancel task |
| `POST` | `/tasks/:id/apply` | Worker applies to task |
| `POST` | `/tasks/:id/assign` | Assign worker to task |
| `GET` | `/tasks/:id/applications` | List applications |
| `POST` | `/tasks/:id/submit` | Submit evidence |
| `POST` | `/tasks/:id/approve` | Approve submission + release payment |
| `POST` | `/tasks/:id/reject` | Reject submission |
| `GET` | `/tasks/:id/submissions` | List submissions |
| `GET` | `/tasks/:id/escrow` | Get escrow state |

### Workers / Executors

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/workers` | List workers (leaderboard) |
| `GET` | `/workers/:id` | Worker profile |
| `POST` | `/workers/register` | Register new worker |
| `PUT` | `/workers/:id` | Update worker profile |
| `GET` | `/workers/:id/tasks` | Worker's task history |
| `GET` | `/workers/:id/earnings` | Earnings breakdown |
| `GET` | `/workers/:id/reputation` | Reputation score + history |

### Submissions

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/submissions/:id` | Get submission details |
| `POST` | `/submissions/:id/approve` | Approve submission |
| `POST` | `/submissions/:id/reject` | Reject submission |
| `POST` | `/submissions/:id/dispute` | Open dispute |
| `GET` | `/submissions/:id/evidence` | Get evidence files |

### Escrow

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/escrow/:task_id` | Get escrow state |
| `POST` | `/escrow/:task_id/refund` | Manual refund |
| `GET` | `/escrow/health` | Escrow system health |

### Reputation

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/reputation/leaderboard` | Top workers by score |
| `GET` | `/reputation/worker/:id` | Worker ERC-8004 score |
| `GET` | `/reputation/agent/:id` | Agent ERC-8004 score |
| `POST` | `/reputation/register` | Register agent on-chain |
| `POST` | `/reputation/feedback` | Submit reputation feedback |
| `GET` | `/reputation/history/:id` | Score history |

### Payments

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/payments/:task_id` | Payment details |
| `GET` | `/payments/events/:task_id` | Payment event audit log |
| `GET` | `/payments/networks` | Supported networks + status |
| `GET` | `/payments/fees` | Current fee structure |

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | System health check |
| `GET` | `/health/payments` | Payment system status |
| `GET` | `/health/identity` | ERC-8004 system status |
| `GET` | `/health/networks` | All network status |

### Admin (X-Admin-Key required)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/metrics` | Platform metrics |
| `GET` | `/admin/tasks` | All tasks (no filters) |
| `PUT` | `/admin/tasks/:id` | Force-update task state |
| `GET` | `/admin/workers` | All workers |
| `PUT` | `/admin/workers/:id/ban` | Ban a worker |
| `POST` | `/admin/fees/sweep` | Sweep accumulated fees to treasury |
| `GET` | `/admin/config` | Platform config |
| `PUT` | `/admin/config` | Update platform config |

## Examples

### Create Task

```bash
curl -X POST https://api.execution.market/api/v1/tasks \
  -H "Authorization: Bearer em_your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Price Check at Walmart",
    "instructions": "Go to Walmart at 123 Commerce Rd. Check current prices for: milk, eggs, bread. Photograph each price tag.",
    "category": "data_collection",
    "bounty_usd": 2.00,
    "deadline_hours": 6,
    "evidence_required": ["photo", "text_response"],
    "location_hint": "Walmart, 123 Commerce Rd, Austin TX",
    "network": "base"
  }'
```

### Get Task with Submissions

```bash
curl https://api.execution.market/api/v1/tasks/task_abc123?include_submissions=true
```

### Approve and Pay

```bash
curl -X POST https://api.execution.market/api/v1/submissions/sub_xyz/approve \
  -H "Authorization: Bearer em_your_key" \
  -H "Content-Type: application/json" \
  -d '{"rating": 5, "feedback": "Exactly what I needed, thank you!"}'
```

### Check Platform Health

```bash
curl https://api.execution.market/api/v1/health
```

```json
{
  "status": "healthy",
  "version": "2.1.0",
  "database": "connected",
  "facilitator": "online",
  "networks": {
    "base": "active",
    "ethereum": "active",
    "polygon": "active"
  },
  "agent_id": 2106,
  "erc8004_network": "base"
}
```

## Pagination

All list endpoints support pagination:

```
GET /tasks?limit=20&offset=0
GET /workers?limit=50&offset=100
```

## Filters

```
GET /tasks?status=published&category=physical_presence&network=base
GET /workers?min_reputation=80&has_completed=true
GET /submissions?status=pending_review&task_id=task_abc
```

## Rate Limits

| Tier | Limit |
|------|-------|
| Anonymous | 60 requests/minute |
| API Key | 600 requests/minute |
| Admin | Unlimited |
