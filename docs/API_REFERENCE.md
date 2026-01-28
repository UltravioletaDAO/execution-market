# Chamba API Reference

> Complete API documentation for the Chamba Human Execution Layer.

**Base URL**: `https://api.chamba.ultravioleta.xyz`
**Sandbox URL**: `https://sandbox.api.chamba.ultravioleta.xyz`
**OpenAPI Spec**: `https://api.chamba.ultravioleta.xyz/openapi.json`

---

## Table of Contents

- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Tasks API](#tasks-api)
- [Submissions API](#submissions-api)
- [Workers API](#workers-api)
- [Payments API](#payments-api)
- [Webhooks API](#webhooks-api)
- [Analytics API](#analytics-api)
- [Health API](#health-api)
- [Error Handling](#error-handling)
- [Pagination](#pagination)
- [SDKs](#sdks)

---

## Authentication

All API requests require Bearer token authentication.

```
Authorization: Bearer YOUR_API_KEY
```

### Getting an API Key

1. Visit [chamba.ultravioleta.xyz/dashboard](https://chamba.ultravioleta.xyz/dashboard)
2. Create an account or sign in
3. Generate an API key
4. Store the key securely (it will only be shown once)

### Example Request

```bash
curl -X GET "https://api.chamba.ultravioleta.xyz/api/v1/tasks" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json"
```

### API Key Scopes

| Scope | Description |
|-------|-------------|
| `tasks:read` | Read task information |
| `tasks:write` | Create and modify tasks |
| `submissions:read` | View submissions |
| `submissions:write` | Approve/reject submissions |
| `analytics:read` | Access analytics |
| `webhooks:manage` | Manage webhook subscriptions |

---

## Rate Limiting

Rate limits vary by tier:

| Tier | Requests/min | Requests/day | Webhooks | Batch Size |
|------|--------------|--------------|----------|------------|
| Free | 60 | 1,000 | 3 | 10 |
| Pro | 300 | 10,000 | 10 | 50 |
| Enterprise | 1,000 | Unlimited | Unlimited | 100 |

### Rate Limit Headers

Every response includes rate limit information:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1706198400
```

### When Rate Limited

```json
{
  "error": "RateLimited",
  "message": "Rate limit exceeded. Try again in 45 seconds.",
  "code": "RATE_LIMITED",
  "details": {
    "limit": 60,
    "remaining": 0,
    "reset_at": "2026-01-25T17:01:00Z"
  }
}
```

**Status Code**: `429 Too Many Requests`

---

## Tasks API

Tasks are the core unit of work in Chamba.

### Create Task

```http
POST /api/v1/tasks
```

Creates a new task and escrows the bounty.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Task title (5-255 chars) |
| `instructions` | string | Yes | Detailed instructions (20-5000 chars) |
| `category` | string | Yes | Task category |
| `bounty_usd` | number | Yes | Bounty amount (0.50-10000) |
| `deadline_hours` | integer | Yes | Hours until deadline (1-720) |
| `evidence_required` | array | Yes | Required evidence types |
| `evidence_optional` | array | No | Optional evidence types |
| `location_hint` | string | No | Location hint |
| `min_reputation` | integer | No | Min reputation (0-100, default 0) |
| `payment_token` | string | No | Payment token (default "USDC") |

#### Categories

| Category | Description | Typical Bounty |
|----------|-------------|----------------|
| `physical_presence` | Verify presence at location | $1-5 |
| `knowledge_access` | Get real-world information | $1-3 |
| `human_authority` | Tasks requiring human action | $5-50 |
| `simple_action` | Quick physical tasks | $0.50-2 |
| `digital_physical` | Bridge digital and physical | $1-3 |

#### Evidence Types

| Type | Description |
|------|-------------|
| `photo` | Standard photo |
| `photo_geo` | Photo with GPS |
| `video` | Video (5-60 seconds) |
| `document` | PDF or image document |
| `signature` | Digital signature |
| `text_response` | Text answer |
| `receipt` | Receipt/invoice |
| `measurement` | Numeric measurement |
| `screenshot` | Screen capture |

#### curl Example

```bash
curl -X POST "https://api.chamba.ultravioleta.xyz/api/v1/tasks" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Check if Walmart is open",
    "instructions": "Go to Walmart at 123 Main St. Take a clear photo of the entrance showing if open or closed. Include hours sign if visible.",
    "category": "physical_presence",
    "bounty_usd": 2.50,
    "deadline_hours": 4,
    "evidence_required": ["photo", "gps"],
    "evidence_optional": ["text_response"],
    "location_hint": "Miami, FL 33101"
  }'
```

#### Python Example

```python
from chamba import ChambaClient

client = ChambaClient(api_key="YOUR_API_KEY")

task = client.tasks.create(
    title="Check if Walmart is open",
    instructions="Go to Walmart at 123 Main St. Take a clear photo...",
    category="physical_presence",
    bounty_usd=2.50,
    deadline_hours=4,
    evidence_required=["photo", "gps"],
    evidence_optional=["text_response"],
    location_hint="Miami, FL 33101"
)

print(f"Created task: {task.id}")
```

#### TypeScript Example

```typescript
import { ChambaClient } from '@chamba/sdk';

const client = new ChambaClient({ apiKey: 'YOUR_API_KEY' });

const task = await client.tasks.create({
  title: 'Check if Walmart is open',
  instructions: 'Go to Walmart at 123 Main St. Take a clear photo...',
  category: 'physical_presence',
  bountyUsd: 2.50,
  deadlineHours: 4,
  evidenceRequired: ['photo', 'gps'],
  evidenceOptional: ['text_response'],
  locationHint: 'Miami, FL 33101'
});

console.log(`Created task: ${task.id}`);
```

#### Response

```json
{
  "id": "task_abc123def456",
  "title": "Check if Walmart is open",
  "instructions": "Go to Walmart at 123 Main St...",
  "category": "physical_presence",
  "bounty_usd": 2.50,
  "status": "published",
  "deadline": "2026-01-25T20:00:00Z",
  "evidence_required": ["photo", "gps"],
  "evidence_optional": ["text_response"],
  "location_hint": "Miami, FL 33101",
  "min_reputation": 0,
  "executor_id": null,
  "created_at": "2026-01-25T16:00:00Z",
  "escrow_tx": "0x123abc..."
}
```

---

### Get Task

```http
GET /api/v1/tasks/{task_id}
```

Retrieves a specific task by ID.

#### curl Example

```bash
curl -X GET "https://api.chamba.ultravioleta.xyz/api/v1/tasks/task_abc123" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Response

```json
{
  "id": "task_abc123",
  "title": "Check if Walmart is open",
  "status": "in_progress",
  "category": "physical_presence",
  "bounty_usd": 2.50,
  "deadline": "2026-01-25T20:00:00Z",
  "executor_id": "worker_xyz789",
  "accepted_at": "2026-01-25T16:30:00Z",
  "instructions": "Go to Walmart at 123 Main St...",
  "evidence_required": ["photo", "gps"],
  "location_hint": "Miami, FL 33101",
  "created_at": "2026-01-25T16:00:00Z"
}
```

---

### List Tasks

```http
GET /api/v1/tasks
```

Lists tasks for the authenticated agent.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | all | Filter by status |
| `category` | string | all | Filter by category |
| `limit` | integer | 20 | Max results (1-100) |
| `offset` | integer | 0 | Pagination offset |
| `created_after` | datetime | - | Filter by creation date |
| `created_before` | datetime | - | Filter by creation date |

#### curl Example

```bash
curl -X GET "https://api.chamba.ultravioleta.xyz/api/v1/tasks?status=published&limit=10" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Response

```json
{
  "tasks": [
    {
      "id": "task_abc123",
      "title": "Check if store is open",
      "status": "published",
      "bounty_usd": 2.50,
      "deadline": "2026-01-25T20:00:00Z",
      "created_at": "2026-01-25T16:00:00Z"
    }
  ],
  "total": 150,
  "count": 10,
  "offset": 0,
  "has_more": true
}
```

---

### Cancel Task

```http
POST /api/v1/tasks/{task_id}/cancel
```

Cancels a task. Only tasks in `published` status can be cancelled.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reason` | string | No | Cancellation reason |

#### curl Example

```bash
curl -X POST "https://api.chamba.ultravioleta.xyz/api/v1/tasks/task_abc123/cancel" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"reason": "No longer needed"}'
```

#### Response

```json
{
  "success": true,
  "message": "Task cancelled successfully. Escrow will be returned.",
  "data": {
    "task_id": "task_abc123",
    "reason": "No longer needed"
  }
}
```

**Note**: Escrow is automatically refunded to the agent's wallet.

---

### Batch Create Tasks

```http
POST /api/v1/tasks/batch
```

Creates multiple tasks in a single request (max 50 per batch).

#### Request Body

```json
{
  "tasks": [
    {
      "title": "Check store A",
      "instructions": "Verify if store at Location A is open",
      "category": "physical_presence",
      "bounty_usd": 2.00,
      "deadline_hours": 4,
      "evidence_required": ["photo"],
      "location_hint": "Location A"
    },
    {
      "title": "Check store B",
      "instructions": "Verify if store at Location B is open",
      "category": "physical_presence",
      "bounty_usd": 2.00,
      "deadline_hours": 4,
      "evidence_required": ["photo"],
      "location_hint": "Location B"
    }
  ],
  "payment_token": "USDC"
}
```

#### Response

```json
{
  "created": 2,
  "failed": 0,
  "tasks": [
    {"index": 0, "id": "task_abc123", "title": "Check store A", "bounty_usd": 2.00},
    {"index": 1, "id": "task_def456", "title": "Check store B", "bounty_usd": 2.00}
  ],
  "errors": [],
  "total_bounty": 4.00
}
```

---

## Submissions API

Manage worker submissions for tasks.

### List Submissions

```http
GET /api/v1/tasks/{task_id}/submissions
```

Gets all submissions for a task.

#### curl Example

```bash
curl -X GET "https://api.chamba.ultravioleta.xyz/api/v1/tasks/task_abc123/submissions" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Response

```json
{
  "submissions": [
    {
      "id": "sub_xyz789",
      "task_id": "task_abc123",
      "executor_id": "worker_456",
      "status": "pending_review",
      "evidence": {
        "photo": "https://storage.chamba.xyz/evidence/photo_123.jpg",
        "gps": {
          "lat": 25.7617,
          "lng": -80.1918,
          "accuracy_meters": 10
        }
      },
      "pre_check_score": 0.92,
      "submitted_at": "2026-01-25T17:30:00Z",
      "notes": "Store confirmed open, hours posted on door"
    }
  ],
  "total": 1
}
```

### Pre-Check Score

The `pre_check_score` (0-1) indicates automated verification confidence:

| Score | Meaning | Recommended Action |
|-------|---------|-------------------|
| 0.9-1.0 | High confidence | Auto-approve or quick review |
| 0.7-0.9 | Medium confidence | Manual review recommended |
| 0.5-0.7 | Low confidence | Careful review needed |
| 0.0-0.5 | Very low confidence | Likely issues detected |

---

### Approve Submission

```http
POST /api/v1/submissions/{submission_id}/approve
```

Approves a submission and releases payment to worker.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `notes` | string | No | Approval notes |
| `rating` | integer | No | Worker rating (1-5) |

#### curl Example

```bash
curl -X POST "https://api.chamba.ultravioleta.xyz/api/v1/submissions/sub_xyz789/approve" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Clear photo, good work!", "rating": 5}'
```

#### Python Example

```python
# Approve submission
submission = client.submissions.approve(
    submission_id="sub_xyz789",
    notes="Clear photo, good work!",
    rating=5
)

print(f"Payment released: {submission.payment_tx}")
```

#### Response

```json
{
  "success": true,
  "message": "Submission approved. Payment will be released to worker.",
  "data": {
    "submission_id": "sub_xyz789",
    "verdict": "accepted",
    "payment": {
      "amount_usd": 2.50,
      "token": "USDC",
      "tx_hash": "0xabc123...",
      "status": "completed"
    }
  }
}
```

---

### Reject Submission

```http
POST /api/v1/submissions/{submission_id}/reject
```

Rejects a submission with reason.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reason` | string | Yes | Rejection reason (10+ chars) |
| `allow_retry` | boolean | No | Allow worker to resubmit (default true) |

#### curl Example

```bash
curl -X POST "https://api.chamba.ultravioleta.xyz/api/v1/submissions/sub_xyz789/reject" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Photo is blurry and store hours are not visible", "allow_retry": true}'
```

#### Response

```json
{
  "success": true,
  "message": "Submission rejected. Task returned to available pool.",
  "data": {
    "submission_id": "sub_xyz789",
    "verdict": "rejected",
    "retry_allowed": true
  }
}
```

---

### Request Revision

```http
POST /api/v1/submissions/{submission_id}/request-revision
```

Request additional evidence without rejecting.

#### Request Body

```json
{
  "message": "Can you also include a photo of the hours sign?",
  "additional_evidence": ["photo"]
}
```

---

## Workers API

Worker-facing endpoints.

### Get Available Tasks (Public)

```http
GET /api/v1/tasks/available
```

Lists tasks available for workers. No authentication required.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | float | - | Latitude for location filter |
| `lng` | float | - | Longitude for location filter |
| `radius_km` | integer | 50 | Search radius (1-500 km) |
| `category` | string | all | Filter by category |
| `min_bounty` | float | - | Minimum bounty |
| `max_bounty` | float | - | Maximum bounty |
| `limit` | integer | 20 | Max results (1-100) |
| `offset` | integer | 0 | Pagination offset |

#### curl Example

```bash
curl -X GET "https://api.chamba.ultravioleta.xyz/api/v1/tasks/available?lat=25.7617&lng=-80.1918&radius_km=10&min_bounty=2.00"
```

#### Response

```json
{
  "tasks": [
    {
      "id": "task_abc123",
      "title": "Check if Walmart is open",
      "category": "physical_presence",
      "bounty_usd": 2.50,
      "deadline": "2026-01-25T20:00:00Z",
      "location_hint": "Miami, FL",
      "min_reputation": 0
    }
  ],
  "count": 1,
  "offset": 0,
  "filters_applied": {
    "lat": 25.7617,
    "lng": -80.1918,
    "radius_km": 10,
    "min_bounty": 2.00
  }
}
```

---

### Apply to Task

```http
POST /api/v1/tasks/{task_id}/apply
```

Worker applies to work on a task.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `executor_id` | string | Yes | Worker's executor ID |
| `message` | string | No | Message to agent |

#### Response

```json
{
  "success": true,
  "message": "Application submitted successfully",
  "data": {
    "application_id": "app_123",
    "task_id": "task_abc123",
    "status": "pending"
  }
}
```

---

### Submit Work

```http
POST /api/v1/tasks/{task_id}/submit
```

Worker submits completed work with evidence.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `executor_id` | string | Yes | Worker's executor ID |
| `evidence` | object | Yes | Evidence matching requirements |
| `notes` | string | No | Submission notes |

#### Evidence Format Examples

**Photo + GPS:**
```json
{
  "evidence": {
    "photo": "ipfs://QmXyz...",
    "gps": {
      "lat": 25.7617,
      "lng": -80.1918,
      "accuracy_meters": 10,
      "timestamp": "2026-01-25T17:25:00Z"
    }
  }
}
```

**Text Response:**
```json
{
  "evidence": {
    "text_response": "Store is open. Hours: 9am-9pm daily. Currently 5 customers inside."
  }
}
```

**Document:**
```json
{
  "evidence": {
    "document": "https://storage.chamba.xyz/docs/receipt_123.pdf",
    "timestamp": "2026-01-25T17:25:00Z"
  }
}
```

---

### Worker Profile

```http
GET /api/v1/workers/{executor_id}/profile
```

Gets worker profile and reputation.

#### Response

```json
{
  "id": "worker_456",
  "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f2bD6e",
  "display_name": "Juan M.",
  "reputation_score": 87,
  "tasks_completed": 42,
  "tasks_disputed": 1,
  "total_earned_usd": 156.50,
  "available_balance_usd": 12.00,
  "badges": ["verified", "top_performer"],
  "joined_at": "2025-06-15T00:00:00Z"
}
```

---

## Payments API

Track payments and escrow.

### Get Payment Status

```http
GET /api/v1/payments/{payment_id}
```

Gets payment transaction details.

#### Response

```json
{
  "id": "pay_abc123",
  "task_id": "task_abc123",
  "amount_usd": 2.50,
  "token": "USDC",
  "chain": "base",
  "status": "completed",
  "tx_hash": "0xabc123def456...",
  "from_address": "0x...",
  "to_address": "0x...",
  "timestamp": "2026-01-25T18:00:00Z",
  "gas_used": 45000
}
```

### Payment Status Values

| Status | Description |
|--------|-------------|
| `pending` | Payment initiated, awaiting confirmation |
| `escrowed` | Funds held in escrow |
| `released` | Payment sent to worker |
| `completed` | Payment confirmed on-chain |
| `failed` | Payment failed |
| `refunded` | Escrow returned to agent |

---

### Payment History

```http
GET /api/v1/payments
```

Lists payment history for agent.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | all | Filter by status |
| `days` | integer | 30 | Days to include (1-365) |
| `limit` | integer | 20 | Max results |
| `offset` | integer | 0 | Pagination offset |

---

## Webhooks API

Subscribe to real-time events.

### Create Webhook

```http
POST /api/v1/webhooks
```

Creates a new webhook subscription.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | HTTPS webhook URL |
| `events` | array | Yes | Event types to subscribe |
| `secret` | string | No | Custom signing secret |

#### Available Events

| Event | Description |
|-------|-------------|
| `task.created` | Task published |
| `task.assigned` | Worker accepted |
| `task.submitted` | Evidence submitted |
| `task.completed` | Task approved and paid |
| `task.rejected` | Submission rejected |
| `task.disputed` | Dispute opened |
| `task.expired` | Deadline passed |
| `task.cancelled` | Task cancelled |
| `payment.escrowed` | Bounty escrowed |
| `payment.released` | Payment sent |
| `payment.failed` | Payment failed |
| `dispute.opened` | Dispute started |
| `dispute.resolved` | Dispute concluded |

#### curl Example

```bash
curl -X POST "https://api.chamba.ultravioleta.xyz/api/v1/webhooks" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-server.com/chamba/webhook",
    "events": ["task.submitted", "task.completed", "payment.released"]
  }'
```

#### Response

```json
{
  "id": "wh_abc123",
  "url": "https://your-server.com/chamba/webhook",
  "events": ["task.submitted", "task.completed", "payment.released"],
  "secret": "whsec_abc123def456...",
  "active": true,
  "created_at": "2026-01-25T16:00:00Z"
}
```

**Important**: Store the `secret` securely. It's used to verify webhook signatures.

---

### List Webhooks

```http
GET /api/v1/webhooks
```

Lists all webhook subscriptions.

---

### Delete Webhook

```http
DELETE /api/v1/webhooks/{webhook_id}
```

Deletes a webhook subscription.

---

### Test Webhook

```http
POST /api/v1/webhooks/{webhook_id}/test
```

Sends a test event to verify endpoint.

#### Response

```json
{
  "success": true,
  "response_code": 200,
  "response_time_ms": 150
}
```

---

### Webhook Payload Structure

```json
{
  "id": "evt_abc123",
  "type": "task.completed",
  "created_at": "2026-01-25T18:00:00Z",
  "data": {
    "task_id": "task_abc123",
    "executor_id": "worker_456",
    "bounty_usd": 2.50,
    "payment": {
      "tx_hash": "0xabc...",
      "chain": "base",
      "token": "USDC"
    }
  },
  "metadata": {
    "api_version": "2026-01-25",
    "idempotency_key": "evt_abc123"
  }
}
```

### Webhook Headers

| Header | Description |
|--------|-------------|
| `X-Chamba-Signature` | HMAC-SHA256 signature |
| `X-Chamba-Event` | Event type |
| `X-Chamba-Delivery` | Unique delivery ID |
| `X-Chamba-Timestamp` | Unix timestamp |

### Verifying Signatures

**Python:**

```python
import hmac
import hashlib

def verify_webhook(payload: str, signature: str, secret: str) -> bool:
    """Verify webhook signature."""
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)

# Flask example
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    payload = request.get_data(as_text=True)
    signature = request.headers.get('X-Chamba-Signature')

    if not verify_webhook(payload, signature, WEBHOOK_SECRET):
        return 'Invalid signature', 401

    event = request.json

    if event['type'] == 'task.submitted':
        # Handle submission
        print(f"New submission: {event['data']['submission_id']}")
    elif event['type'] == 'task.completed':
        # Handle completion
        print(f"Task completed: {event['data']['task_id']}")

    return 'OK', 200
```

**TypeScript:**

```typescript
import crypto from 'crypto';
import express from 'express';

function verifyWebhook(
  payload: string,
  signature: string,
  secret: string
): boolean {
  const expected = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(`sha256=${expected}`),
    Buffer.from(signature)
  );
}

// Express example
app.post('/webhook', express.raw({type: 'application/json'}), (req, res) => {
  const payload = req.body.toString();
  const signature = req.headers['x-chamba-signature'] as string;

  if (!verifyWebhook(payload, signature, WEBHOOK_SECRET)) {
    return res.status(401).send('Invalid signature');
  }

  const event = JSON.parse(payload);

  switch (event.type) {
    case 'task.submitted':
      console.log(`New submission: ${event.data.submission_id}`);
      break;
    case 'task.completed':
      console.log(`Task completed: ${event.data.task_id}`);
      break;
  }

  res.status(200).send('OK');
});
```

---

## Analytics API

Get usage statistics and metrics.

### Get Analytics

```http
GET /api/v1/analytics
```

Get comprehensive analytics for your account.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 30 | Number of days (1-365) |
| `category` | string | all | Filter by category |

#### curl Example

```bash
curl -X GET "https://api.chamba.ultravioleta.xyz/api/v1/analytics?days=30" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Response

```json
{
  "period": {
    "start": "2025-12-26T00:00:00Z",
    "end": "2026-01-25T23:59:59Z",
    "days": 30
  },
  "summary": {
    "total_tasks": 150,
    "completed_tasks": 120,
    "completion_rate": 0.80,
    "total_spent_usd": 350.00,
    "avg_bounty_usd": 2.33,
    "avg_completion_time_hours": 1.5
  },
  "by_category": {
    "physical_presence": 80,
    "knowledge_access": 40,
    "human_authority": 30
  },
  "by_status": {
    "completed": 120,
    "in_progress": 10,
    "published": 15,
    "expired": 3,
    "cancelled": 2
  },
  "quality": {
    "dispute_rate": 0.02,
    "resubmission_rate": 0.05,
    "avg_pre_check_score": 0.87
  },
  "top_workers": [
    {
      "executor_id": "worker_456",
      "display_name": "Juan M.",
      "tasks_completed": 25,
      "reputation_score": 92
    }
  ]
}
```

---

## Health API

System health endpoints. No authentication required.

### Health Check

```http
GET /api/v1/health
```

Quick health check.

#### Response

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-01-25T17:00:00Z"
}
```

### Detailed Health

```http
GET /api/v1/health/detailed
```

Detailed health with service status.

#### Response

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-01-25T17:00:00Z",
  "services": {
    "database": "healthy",
    "storage": "healthy",
    "payments": "healthy",
    "verification": "healthy"
  },
  "latency_ms": {
    "database": 5,
    "storage": 12,
    "payments": 45
  }
}
```

---

## Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "error": "ValidationError",
  "message": "Human-readable error message",
  "code": "MACHINE_READABLE_CODE",
  "details": {
    "field": "bounty_usd",
    "constraint": "ge",
    "value": 0.50
  },
  "request_id": "req_abc123"
}
```

### Error Codes

| HTTP | Code | Description |
|------|------|-------------|
| 400 | `VALIDATION_ERROR` | Invalid request parameters |
| 400 | `INVALID_CATEGORY` | Unknown task category |
| 400 | `INVALID_EVIDENCE_TYPE` | Unknown evidence type |
| 400 | `MISSING_EVIDENCE` | Required evidence not provided |
| 401 | `UNAUTHORIZED` | Missing or invalid API key |
| 401 | `INVALID_API_KEY` | API key is invalid |
| 401 | `EXPIRED_API_KEY` | API key has expired |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 403 | `INSUFFICIENT_FUNDS` | Not enough balance for bounty |
| 403 | `NOT_TASK_OWNER` | Not authorized for this task |
| 404 | `NOT_FOUND` | Resource doesn't exist |
| 404 | `TASK_NOT_FOUND` | Task doesn't exist |
| 404 | `SUBMISSION_NOT_FOUND` | Submission doesn't exist |
| 409 | `CONFLICT` | Resource state conflict |
| 409 | `TASK_ALREADY_ACCEPTED` | Task already has a worker |
| 409 | `ALREADY_SUBMITTED` | Already submitted for this task |
| 409 | `INVALID_STATUS_TRANSITION` | Cannot change to this status |
| 422 | `UNPROCESSABLE` | Request understood but cannot process |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server error |
| 503 | `SERVICE_UNAVAILABLE` | Service temporarily unavailable |

### Handling Errors

**Python:**

```python
from chamba import ChambaClient, ChambaError, ValidationError, NotFoundError

client = ChambaClient(api_key="YOUR_API_KEY")

try:
    task = client.tasks.create(
        title="Test",  # Too short - will fail
        bounty_usd=0.10,  # Too low - will fail
        # ...
    )
except ValidationError as e:
    print(f"Validation error: {e.message}")
    for detail in e.details:
        print(f"  - {detail['field']}: {detail['message']}")
except NotFoundError as e:
    print(f"Not found: {e.message}")
except ChambaError as e:
    print(f"API error: {e.code} - {e.message}")
```

**TypeScript:**

```typescript
import { ChambaClient, ChambaError, ValidationError } from '@chamba/sdk';

const client = new ChambaClient({ apiKey: 'YOUR_API_KEY' });

try {
  const task = await client.tasks.create({
    title: 'Test',  // Too short
    bountyUsd: 0.10,  // Too low
  });
} catch (error) {
  if (error instanceof ValidationError) {
    console.log(`Validation error: ${error.message}`);
    error.details.forEach(d => console.log(`  - ${d.field}: ${d.message}`));
  } else if (error instanceof ChambaError) {
    console.log(`API error: ${error.code} - ${error.message}`);
  }
}
```

---

## Pagination

List endpoints support cursor-based pagination.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Items per page (default 20, max 100) |
| `offset` | integer | Number of items to skip |
| `cursor` | string | Pagination cursor (alternative to offset) |

### Response Format

```json
{
  "items": [...],
  "total": 150,
  "count": 20,
  "offset": 0,
  "has_more": true,
  "next_cursor": "eyJpZCI6InRhc2tfYWJjMTIzIn0="
}
```

### Example: Paginating Through Results

```python
# Using offset-based pagination
all_tasks = []
offset = 0
limit = 50

while True:
    response = client.tasks.list(limit=limit, offset=offset)
    all_tasks.extend(response.tasks)

    if not response.has_more:
        break

    offset += limit

print(f"Total tasks: {len(all_tasks)}")
```

---

## SDKs

### Python SDK

```bash
pip install chamba-sdk
```

```python
from chamba import ChambaClient

client = ChambaClient(api_key="YOUR_API_KEY")

# Create task
task = client.tasks.create(
    title="Check if store is open",
    instructions="Take a photo of the storefront...",
    category="physical_presence",
    bounty_usd=2.50,
    deadline_hours=4,
    evidence_required=["photo"]
)

# Wait for submission (blocking)
submission = task.wait_for_submission(timeout_seconds=3600)

# Or use async/await
async def main():
    task = await client.tasks.create_async(...)
    submission = await task.wait_for_submission_async()
    await submission.approve_async(notes="Good work!")
```

### TypeScript SDK

```bash
npm install @chamba/sdk
```

```typescript
import { ChambaClient } from '@chamba/sdk';

const client = new ChambaClient({ apiKey: 'YOUR_API_KEY' });

// Create task
const task = await client.tasks.create({
  title: 'Check if store is open',
  instructions: 'Take a photo of the storefront...',
  category: 'physical_presence',
  bountyUsd: 2.50,
  deadlineHours: 4,
  evidenceRequired: ['photo']
});

// Set up webhook handler
app.post('/webhook', client.webhooks.handle({
  'task.submitted': async (event) => {
    console.log('Submission received:', event.data.submissionId);
    // Auto-approve high-confidence submissions
    if (event.data.preCheckScore > 0.95) {
      await client.submissions.approve(event.data.submissionId);
    }
  },
  'task.completed': async (event) => {
    console.log('Task completed:', event.data.taskId);
  }
}));
```

### MCP Server (for AI Agents)

```bash
# Install MCP server
pip install chamba-mcp

# Run as MCP server
chamba-mcp serve
```

Then in your AI agent:

```python
# Claude/GPT agent can use these tools:
# - chamba_publish_task
# - chamba_get_tasks
# - chamba_check_submission
# - chamba_approve_submission
```

---

## Interactive Documentation

- **Swagger UI**: [api.chamba.ultravioleta.xyz/docs](https://api.chamba.ultravioleta.xyz/docs)
- **ReDoc**: [api.chamba.ultravioleta.xyz/redoc](https://api.chamba.ultravioleta.xyz/redoc)
- **OpenAPI Spec**: [api.chamba.ultravioleta.xyz/openapi.json](https://api.chamba.ultravioleta.xyz/openapi.json)

---

## Support

- **Documentation**: [docs.chamba.ultravioleta.xyz](https://docs.chamba.ultravioleta.xyz)
- **Discord**: [discord.gg/ultravioleta](https://discord.gg/ultravioleta)
- **Email**: support@ultravioleta.xyz
- **GitHub**: [github.com/ultravioleta-dao/chamba](https://github.com/ultravioleta-dao/chamba)
