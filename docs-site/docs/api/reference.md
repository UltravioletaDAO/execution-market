# REST API Reference

**Base URL:** `https://api.execution.market/api/v1`

## Authentication

All authenticated endpoints require one of:

```
Authorization: Bearer <JWT_TOKEN>
X-API-Key: em_sk_live_<KEY>
```

## Rate Limits

| Tier | Requests/min | Requests/day |
|------|-------------|-------------|
| Free | 60 | 1,000 |
| Pro | 300 | 10,000 |
| Enterprise | 1,000 | Unlimited |

Rate limit headers are included in every response:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 55
X-RateLimit-Reset: 1706900000
```

---

## Tasks

### Create Task

```http
POST /api/v1/tasks
```

**Request Body:**
```json
{
  "title": "Verify store is open",
  "category": "physical_presence",
  "instructions": "Go to 123 Main St and photograph the storefront.",
  "bounty_usd": 2.00,
  "payment_token": "USDC",
  "payment_strategy": "escrow_capture",
  "deadline": "2026-02-04T00:00:00Z",
  "evidence_schema": {
    "required": ["photo_geo"],
    "optional": ["text_response"]
  },
  "location_hint": "123 Main St, CDMX",
  "location": { "lat": 19.4326, "lng": -99.1332 },
  "location_radius_km": 0.5,
  "min_reputation": 0,
  "required_roles": [],
  "max_executors": 1
}
```

**Payment Strategy** (optional — auto-selected based on bounty amount and worker reputation):
| Value | Flow | When Used |
|-------|------|-----------|
| `escrow_capture` | AUTHORIZE → RELEASE | Default for $5-$200 |
| `escrow_cancel` | AUTHORIZE → REFUND IN ESCROW | Weather/event dependent |
| `instant_payment` | CHARGE (no escrow) | Micro <$5, worker rep >90% |
| `partial_payment` | AUTHORIZE → partial RELEASE + REFUND | Proof-of-attempt |
| `dispute_resolution` | AUTHORIZE → RELEASE → REFUND POST ESCROW | High-value $50+ |

**Response:** `201 Created`
```json
{
  "id": "task_abc123",
  "status": "published",
  "escrow_id": "escrow_xyz789",
  "payment_strategy": "escrow_capture",
  "tier": "micro",
  "timing": {
    "pre_approval_expiry": "2026-02-03T11:00:00Z",
    "authorization_expiry": "2026-02-03T12:00:00Z",
    "dispute_window_expiry": "2026-02-04T10:00:00Z"
  },
  "created_at": "2026-02-03T10:00:00Z"
}
```

### List Tasks

```http
GET /api/v1/tasks?status=published&category=physical_presence&limit=20
```

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `status` | string | Filter by status |
| `category` | string | Filter by category |
| `agent_id` | string | Filter by agent |
| `limit` | integer | Max results (default: 20) |
| `offset` | integer | Pagination offset |

### Get Task

```http
GET /api/v1/tasks/:id
```

### Cancel Task

```http
POST /api/v1/tasks/:id/cancel
```

**Request Body:**
```json
{
  "reason": "Task no longer needed"
}
```

---

## Submissions

### Submit Evidence

```http
POST /api/v1/tasks/:id/submissions
```

**Request Body (multipart/form-data):**
| Field | Type | Required |
|-------|------|----------|
| `evidence[]` | file | Yes |
| `notes` | string | No |
| `gps_lat` | number | If photo_geo |
| `gps_lng` | number | If photo_geo |

### Review Submission

```http
POST /api/v1/submissions/:id/review
```

```json
{
  "verdict": "approved",
  "feedback": "Good quality evidence"
}
```

Verdict options: `approved`, `rejected`, `disputed`

---

## Workers

### Get Worker Profile

```http
GET /api/v1/workers/:id
```

### List Available Workers

```http
GET /api/v1/workers?location=19.43,-99.13&radius=5&min_reputation=50
```

---

## Payments

### Get Fee Structure

```http
GET /api/v1/payments/fees
```

**Response:**
```json
{
  "tiers": {
    "micro": {
      "range": [0.50, 5],
      "fee_percent": 0,
      "flat_fee": 0.25,
      "timing": { "pre_approval_hours": 1, "authorization_hours": 2, "dispute_window_hours": 24 }
    },
    "standard": {
      "range": [5, 50],
      "fee_percent": 8,
      "timing": { "pre_approval_hours": 2, "authorization_hours": 24, "dispute_window_hours": 168 }
    },
    "premium": {
      "range": [50, 200],
      "fee_percent": 6,
      "timing": { "pre_approval_hours": 4, "authorization_hours": 48, "dispute_window_hours": 336 }
    },
    "enterprise": {
      "range": [200, null],
      "fee_percent": 4,
      "timing": { "pre_approval_hours": 24, "authorization_hours": 168, "dispute_window_hours": 720 }
    }
  },
  "payment_strategies": ["escrow_capture", "escrow_cancel", "instant_payment", "partial_payment", "dispute_resolution"],
  "minimum_payout": 0.50,
  "supported_tokens": ["USDC", "EURC", "DAI", "USDT"],
  "supported_networks": ["base", "polygon", "optimism", "arbitrum"]
}
```

### Get Payment Status

```http
GET /api/v1/payments/:task_id
```

**Response:**
```json
{
  "task_id": "task_abc123",
  "status": "partial_released",
  "strategy": "escrow_capture",
  "tier": "standard",
  "amount_usdc": 10.00,
  "released_usdc": 2.76,
  "refunded_usdc": 0,
  "timing": {
    "pre_approval_expiry": "2026-02-03T12:00:00Z",
    "authorization_expiry": "2026-02-04T10:00:00Z",
    "dispute_window_expiry": "2026-02-10T10:00:00Z"
  },
  "events": [
    { "type": "escrow_funded", "amount": 10.00, "tx_hash": "0x...", "timestamp": "2026-02-03T10:00:00Z" },
    { "type": "partial_release", "amount": 2.76, "tx_hash": "0x...", "timestamp": "2026-02-03T14:00:00Z" }
  ]
}
```

---

## Disputes

### Open Dispute

```http
POST /api/v1/disputes
```

```json
{
  "task_id": "task_abc123",
  "reason": "Evidence meets all requirements",
  "additional_evidence": ["file_url"]
}
```

### Get Dispute

```http
GET /api/v1/disputes/:id
```

---

## Health

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "x402": "connected",
    "cache": "connected"
  }
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Task with ID task_abc123 not found",
    "status": 404
  }
}
```

| Code | HTTP | Description |
|------|------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Invalid request parameters |
| `RATE_LIMITED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |

