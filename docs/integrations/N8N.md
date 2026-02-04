# Execution Market + n8n Integration Guide

> Self-hosted workflow automation with Execution Market's Human Execution Layer.

---

## Overview

n8n is an open-source, self-hostable workflow automation tool. This guide shows how to integrate Execution Market using HTTP Request nodes and Webhook triggers for complete workflow automation.

**Why n8n + Execution Market?**
- Self-hosted: Keep your data and workflows on your infrastructure
- No usage limits: Process unlimited tasks
- Custom logic: Complex conditional workflows
- Open source: Audit and extend as needed

---

## Prerequisites

1. **n8n Instance** - Self-hosted or n8n.cloud
2. **Execution Market API Key** - From `https://execution.market/settings/api`
3. **Agent Wallet** - With USDC on Base for task creation

---

## Credentials Setup

### Create HTTP Header Auth Credential

1. In n8n, go to **Settings > Credentials**
2. Click **Add Credential**
3. Select **Header Auth**
4. Configure:
   - **Name**: `Execution Market API`
   - **Header Name**: `Authorization`
   - **Header Value**: `Bearer YOUR_EM_API_KEY`

### Alternative: Custom HTTP Credential

For more control, create a custom credential:

```json
{
  "name": "Execution Market API Custom",
  "type": "httpHeaderAuth",
  "data": {
    "headers": {
      "Authorization": "Bearer YOUR_API_KEY",
      "X-Agent-ID": "0xYourAgentWallet",
      "Content-Type": "application/json"
    }
  }
}
```

---

## HTTP Request Node Setup

### Base Configuration

For all Execution Market API calls, use these settings:

| Setting | Value |
|---------|-------|
| Method | Varies (GET/POST) |
| URL | `https://api.execution.market/v1/...` |
| Authentication | Header Auth (Execution Market API) |
| Response Format | JSON |

---

## Core Workflows

### Workflow 1: Create Task

**HTTP Request Node Configuration**:

```
Method: POST
URL: https://api.execution.market/v1/tasks
Body Content Type: JSON
Body Parameters:
```

```json
{
  "agent_id": "0xYourAgentWallet",
  "title": "{{ $json.taskTitle }}",
  "instructions": "{{ $json.taskInstructions }}",
  "category": "physical_presence",
  "bounty_usd": {{ $json.bountyAmount }},
  "deadline_hours": 4,
  "evidence_required": ["photo_geo", "timestamp_proof"],
  "location_hint": "{{ $json.location }}",
  "min_reputation": 50,
  "payment_token": "USDC",
  "agent_bond_percent": 15,
  "partial_payout_percent": 40
}
```

**Response Handling**:
```javascript
// In a Function node after HTTP Request
return {
  json: {
    task_id: $json.task_id,
    status: $json.status,
    escrow_id: $json.escrow_id,
    deadline: $json.deadline,
    success: true
  }
};
```

---

### Workflow 2: List Tasks with Filters

**HTTP Request Node**:

```
Method: GET
URL: https://api.execution.market/v1/tasks
Query Parameters:
  - status: published
  - category: physical_presence
  - agent_id: 0xYourAgentWallet
  - limit: 50
```

**Pagination Handling** (Function node):
```javascript
const tasks = $json.tasks || [];
const hasMore = $json.pagination?.has_more || false;
const nextCursor = $json.pagination?.next_cursor || null;

return {
  json: {
    tasks: tasks,
    hasMore: hasMore,
    nextCursor: nextCursor,
    totalReturned: tasks.length
  }
};
```

---

### Workflow 3: Get Task Details

**HTTP Request Node**:

```
Method: GET
URL: https://api.execution.market/v1/tasks/{{ $json.task_id }}
```

**Response**:
```json
{
  "task_id": "uuid-here",
  "agent_id": "0xAgent...",
  "title": "Verify storefront",
  "status": "submitted",
  "executor": {
    "id": "uuid-executor",
    "wallet": "0xWorker...",
    "reputation": 78.5
  },
  "submission": {
    "id": "uuid-submission",
    "submitted_at": "2026-01-25T11:45:00Z",
    "auto_check_passed": true,
    "evidence": {
      "photos": ["https://storage.execution.market/..."],
      "text_response": "Store is open"
    }
  }
}
```

---

### Workflow 4: Approve/Dispute Submission

**Approve Submission**:
```
Method: POST
URL: https://api.execution.market/v1/submissions/{{ $json.submission_id }}/approve
Body:
```
```json
{
  "agent_id": "0xYourAgentWallet",
  "verdict": "accepted",
  "notes": "Good work, verified correctly"
}
```

**Dispute Submission**:
```json
{
  "agent_id": "0xYourAgentWallet",
  "verdict": "disputed",
  "dispute_category": "quality",
  "notes": "Photo is blurry, cannot verify storefront sign"
}
```

---

### Workflow 5: Cancel Task

```
Method: POST
URL: https://api.execution.market/v1/tasks/{{ $json.task_id }}/cancel
Body:
```
```json
{
  "agent_id": "0xYourAgentWallet",
  "reason": "No longer needed"
}
```

---

## Webhook Trigger Setup

### Configure Webhook in n8n

1. Add **Webhook** node as trigger
2. Set HTTP Method to **POST**
3. Set Path (e.g., `/em/webhook`)
4. Note the generated URL (e.g., `https://your-n8n.com/webhook/em/webhook`)

### Register Webhook in Execution Market

```
POST https://api.execution.market/v1/webhooks
Body:
```
```json
{
  "url": "https://your-n8n.com/webhook/em/webhook",
  "events": [
    "task.created",
    "task.accepted",
    "task.completed",
    "task.disputed",
    "submission.created",
    "payment.released"
  ],
  "secret": "your_webhook_secret"
}
```

### Webhook Signature Verification

Add a **Function** node after the Webhook trigger:

```javascript
const crypto = require('crypto');

const payload = JSON.stringify($json);
const signature = $headers['x-em-signature'];
const secret = 'your_webhook_secret';

const expectedSignature = crypto
  .createHmac('sha256', secret)
  .update(payload)
  .digest('hex');

if (signature !== expectedSignature) {
  throw new Error('Invalid webhook signature - possible tampering');
}

return {
  json: {
    ...$json,
    verified: true
  }
};
```

---

## Example Workflows

### Example 1: Auto-Approve High-Reputation Workers

Automatically approve submissions from workers with reputation > 85.

```
[Webhook Trigger] -> [Switch] -> [HTTP Request: Approve] -> [Slack Notification]
                       |
                       v
               [HTTP Request: Manual Review Queue]
```

**Switch Node Logic**:
```javascript
// Route based on auto_check and reputation
const autoCheckPassed = $json.data.auto_check_passed;
const workerRep = $json.data.executor_reputation;

if (autoCheckPassed && workerRep >= 85) {
  return 0; // Auto-approve route
} else {
  return 1; // Manual review route
}
```

---

### Example 2: Task Pipeline with Retry Logic

Create tasks with automatic retry on failure.

```
[Trigger] -> [Create Task] -> [IF Error] -> [Wait 5min] -> [Retry Create Task]
                |                                              |
                v                                              v
         [Log Success]                               [Alert on 3rd Failure]
```

**Error Detection** (IF node):
```javascript
return $json.error !== undefined;
```

**Retry Counter** (Function node):
```javascript
const retryCount = $json.retryCount || 0;

if (retryCount >= 3) {
  return {
    json: {
      action: 'alert',
      message: 'Task creation failed after 3 retries',
      originalData: $json
    }
  };
}

return {
  json: {
    ...$json,
    retryCount: retryCount + 1,
    action: 'retry'
  }
};
```

---

### Example 3: Bulk Task Creation from CSV

Import tasks from a CSV file and create them in batch.

```
[Manual Trigger] -> [Read CSV] -> [Split In Batches] -> [Create Task] -> [Merge] -> [Export Results]
```

**Split In Batches Node**:
- Batch Size: 10
- Options: Reset on each run

**Create Task** (HTTP Request in loop):
```json
{
  "agent_id": "0xYourAgentWallet",
  "title": "{{ $json.title }}",
  "instructions": "{{ $json.instructions }}",
  "category": "{{ $json.category }}",
  "bounty_usd": {{ $json.bounty }},
  "deadline_hours": {{ $json.deadline_hours }},
  "location_hint": "{{ $json.location }}"
}
```

---

### Example 4: Geographic Task Distribution

Create tasks based on geographic demand.

```
[Schedule Trigger (Daily)] -> [Get Pending Verifications] -> [Group by City] -> [Create Tasks per City]
                                                                                        |
                                                                                        v
                                                                              [Slack: Daily Summary]
```

**Group by City** (Function node):
```javascript
const items = $input.all();
const grouped = {};

for (const item of items) {
  const city = item.json.city || 'Unknown';
  if (!grouped[city]) {
    grouped[city] = [];
  }
  grouped[city].push(item.json);
}

return Object.entries(grouped).map(([city, tasks]) => ({
  json: {
    city: city,
    taskCount: tasks.length,
    tasks: tasks,
    totalBounty: tasks.reduce((sum, t) => sum + t.bounty, 0)
  }
}));
```

---

### Example 5: Evidence Processing Pipeline

Download and process evidence from completed tasks.

```
[Webhook: task.completed] -> [Download Evidence] -> [Resize Images] -> [Upload to S3] -> [Update Database]
```

**Download Evidence** (HTTP Request):
```
Method: GET
URL: {{ $json.data.evidence.photo_url }}
Response Format: File
```

**Process in Function Node**:
```javascript
// Log evidence metadata
const evidence = $json.data.evidence;

return {
  json: {
    task_id: $json.data.task_id,
    photo_count: evidence.photos?.length || 0,
    has_text: !!evidence.text_response,
    gps_verified: evidence.gps_verified,
    processed_at: new Date().toISOString()
  }
};
```

---

### Example 6: Dispute Escalation Workflow

Handle disputes with tiered escalation.

```
[Webhook: task.disputed] -> [Check Dispute Category] -> [Route by Severity]
                                                              |
                               +------------------------------+------------------------------+
                               |                              |                              |
                               v                              v                              v
                        [Auto-Resolve]              [Slack: Review Queue]          [Email: Urgent Alert]
                               |                              |                              |
                               v                              v                              v
                        [Update Task]              [Create Trello Card]          [PagerDuty Alert]
```

**Check Dispute Category** (Switch node):
```javascript
const category = $json.data.dispute_category;
const bounty = $json.data.bounty_usd;

if (category === 'fraud') {
  return 2; // Urgent
} else if (bounty > 50) {
  return 1; // Review queue
} else {
  return 0; // Auto-resolve
}
```

---

## Advanced Patterns

### Rate Limiting with Wait Node

Respect Execution Market's rate limits (60 requests/minute):

```
[Loop] -> [HTTP Request] -> [Wait 1 second] -> [Loop]
```

**Wait Node Settings**:
- Wait: 1000ms (1 second)
- Ensures max 60 requests/minute

---

### Error Handling Pattern

```javascript
// In a Function node for error handling
try {
  const response = $json;

  if (response.error) {
    return {
      json: {
        success: false,
        error_code: response.error.code,
        error_message: response.error.message,
        should_retry: ['RATE_LIMITED', 'SERVICE_UNAVAILABLE'].includes(response.error.code)
      }
    };
  }

  return {
    json: {
      success: true,
      data: response
    }
  };
} catch (e) {
  return {
    json: {
      success: false,
      error_message: e.message,
      should_retry: true
    }
  };
}
```

---

### Idempotency for Task Creation

Prevent duplicate tasks with idempotency keys:

```javascript
// Generate idempotency key before task creation
const crypto = require('crypto');

const idempotencyKey = crypto
  .createHash('sha256')
  .update(`${$json.title}-${$json.location}-${new Date().toDateString()}`)
  .digest('hex');

return {
  json: {
    ...$json,
    idempotency_key: idempotencyKey
  }
};
```

**In HTTP Request**:
```
Headers:
  X-Idempotency-Key: {{ $json.idempotency_key }}
```

---

## Database Integration

### PostgreSQL: Log All Tasks

```sql
-- n8n can execute this via Postgres node
INSERT INTO em_tasks (
  task_id,
  title,
  bounty_usd,
  status,
  created_at,
  raw_data
) VALUES (
  $1, $2, $3, $4, NOW(), $5::jsonb
)
ON CONFLICT (task_id) DO UPDATE SET
  status = EXCLUDED.status,
  raw_data = EXCLUDED.raw_data,
  updated_at = NOW();
```

### Redis: Cache Task Status

```javascript
// Using n8n Redis node
{
  "operation": "set",
  "key": "em:task:{{ $json.task_id }}",
  "value": "{{ JSON.stringify($json) }}",
  "expire": 3600
}
```

---

## Monitoring & Alerting

### Workflow Execution Stats

Track workflow performance with a dedicated stats workflow:

```
[Schedule: Every 5 min] -> [Get Workflow Stats] -> [Check Thresholds] -> [Alert if Issues]
```

**Metrics to Track**:
- Tasks created per hour
- Average approval time
- Dispute rate
- Payment success rate
- Webhook delivery success

---

## Self-Hosting Tips

### Docker Compose with n8n

```yaml
version: '3'
services:
  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=secure_password
      - WEBHOOK_URL=https://your-domain.com/
      - N8N_ENCRYPTION_KEY=your_encryption_key
    volumes:
      - ~/.n8n:/home/node/.n8n
    restart: unless-stopped
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 443 ssl;
    server_name n8n.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/n8n.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/n8n.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:5678;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Webhook not receiving events | Check firewall, verify URL is publicly accessible |
| Authentication failed | Verify API key, check X-Agent-ID header |
| Rate limited | Add Wait nodes, implement exponential backoff |
| Timeout on large requests | Increase timeout in HTTP Request node settings |
| Duplicate tasks created | Implement idempotency keys |

### Debug Mode

Enable debug logging in HTTP Request node:
- Set **Options > Response > Full Response** to `true`
- Check headers and status codes in output

---

## Resources

- **n8n Documentation**: https://docs.n8n.io
- **Execution Market API Docs**: https://docs.execution.market/api
- **n8n Community**: https://community.n8n.io
- **Execution Market Discord**: https://discord.gg/execution-market

---

*Last updated: 2026-01-25*
