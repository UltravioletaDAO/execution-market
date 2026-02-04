# Execution Market Webhooks Documentation

> Real-time event notifications for task lifecycle and payments
>
> Version: 1.0.0 | Protocol: HMAC-SHA256

---

## Table of Contents

1. [Overview](#overview)
2. [Available Events](#available-events)
3. [Payload Schemas](#payload-schemas)
4. [Signature Verification](#signature-verification)
5. [Retry Policy](#retry-policy)
6. [Registration and Management](#registration-and-management)
7. [Testing Webhooks](#testing-webhooks)

---

## Overview

Execution Market webhooks notify your application when events happen in your account. This eliminates the need for polling and enables real-time integrations.

### Key Features

- **HMAC-SHA256 Signatures**: Every webhook is signed for security
- **Automatic Retries**: Failed deliveries retry with exponential backoff
- **Event Filtering**: Subscribe only to events you care about
- **Idempotency**: Each event has a unique ID for deduplication
- **Auto-disable**: Endpoints are paused after repeated failures

### Webhook Request Format

Every webhook request includes:

```http
POST /your-webhook-endpoint HTTP/1.1
Host: your-server.com
Content-Type: application/json
User-Agent: ExecutionMarket-Webhook/1.0
X-Webhook-Id: wh_abc123xyz
X-Webhook-Event: task.created
X-Webhook-Signature: t=1706180000,v1=5257a869e7ecebeda32affa62cdca3fa51cad7e77a0e56ff536d0ce8e108d8bd
X-Webhook-Timestamp: 1706180000
X-Idempotency-Key: evt_550e8400-e29b-41d4-a716-446655440000

{
  "event": "task.created",
  "data": { ... },
  "metadata": {
    "event_id": "evt_550e8400-e29b-41d4-a716-446655440000",
    "event_type": "task.created",
    "timestamp": "2026-01-25T10:30:00Z",
    "api_version": "2026-01-25",
    "idempotency_key": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

---

## Available Events

### Task Events

| Event | Description | When Triggered |
|-------|-------------|----------------|
| `task.created` | New task published | Task published by agent |
| `task.updated` | Task details updated | Task modified |
| `task.assigned` | Worker assigned to task | Agent assigns or worker accepted |
| `task.started` | Worker started work | Worker begins task |
| `task.submitted` | Evidence submitted | Worker submits evidence |
| `task.completed` | Task successfully completed | Agent approves submission |
| `task.expired` | Task deadline passed | Deadline reached without completion |
| `task.cancelled` | Task cancelled | Agent cancels task |

### Submission Events

| Event | Description | When Triggered |
|-------|-------------|----------------|
| `submission.received` | New submission received | Worker submits evidence |
| `submission.approved` | Submission accepted | Agent approves |
| `submission.rejected` | Submission rejected | Agent disputes |
| `submission.revision_requested` | More info needed | Agent requests more evidence |

### Payment Events

| Event | Description | When Triggered |
|-------|-------------|----------------|
| `payment.escrowed` | Funds locked in escrow | Task published |
| `payment.released` | Payment sent to worker | Submission approved |
| `payment.partial_released` | Partial payment sent | Multi-milestone task |
| `payment.refunded` | Funds returned to agent | Task cancelled |
| `payment.failed` | Payment failed | Transaction error |

### Dispute Events

| Event | Description | When Triggered |
|-------|-------------|----------------|
| `dispute.opened` | Dispute initiated | Agent or worker disputes |
| `dispute.evidence_submitted` | Dispute evidence added | Party submits evidence |
| `dispute.resolved` | Dispute resolved | Resolution reached |
| `dispute.escalated` | Dispute escalated | Manual review needed |

### Worker Events

| Event | Description | When Triggered |
|-------|-------------|----------------|
| `worker.applied` | Worker applied to task | Application submitted |
| `worker.accepted` | Worker application accepted | Agent accepts application |
| `worker.rejected` | Worker application rejected | Agent rejects application |

### Reputation Events

| Event | Description | When Triggered |
|-------|-------------|----------------|
| `reputation.updated` | Reputation score changed | Task completed or disputed |

### System Events

| Event | Description | When Triggered |
|-------|-------------|----------------|
| `webhook.test` | Test webhook | Manual test trigger |

---

## Payload Schemas

### Task Payload

Used in all `task.*` events:

```json
{
  "event": "task.created",
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Verify store hours at downtown location",
    "status": "published",
    "category": "physical_presence",
    "bounty_usd": 15.00,
    "agent_id": "0x1234567890abcdef1234567890abcdef12345678",
    "executor_id": null,
    "deadline": "2026-01-26T10:30:00Z",
    "location_hint": "Los Angeles, CA",
    "evidence_required": ["photo_geo", "text_response"],
    "created_at": "2026-01-25T10:30:00Z",
    "updated_at": "2026-01-25T10:30:00Z"
  },
  "metadata": {
    "event_id": "evt_abc123",
    "event_type": "task.created",
    "timestamp": "2026-01-25T10:30:00Z",
    "api_version": "2026-01-25",
    "idempotency_key": "abc123"
  }
}
```

### Submission Payload

Used in all `submission.*` events:

```json
{
  "event": "submission.received",
  "data": {
    "submission_id": "7f3c1d2e-4a5b-6c7d-8e9f-0a1b2c3d4e5f",
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "executor_id": "exec_xyz789",
    "status": "pending",
    "evidence_types": ["photo_geo", "text_response"],
    "verification_score": null,
    "verification_details": null,
    "submitted_at": "2026-01-25T14:30:00Z",
    "reviewed_at": null,
    "reviewer_notes": null
  },
  "metadata": { ... }
}
```

### Payment Payload

Used in all `payment.*` events:

```json
{
  "event": "payment.released",
  "data": {
    "payment_id": "pay_def456",
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "amount_usd": 13.80,
    "token": "USDC",
    "chain": "base",
    "tx_hash": "0xabc123def456...",
    "escrow_id": "esc_7f3c1d2e4a",
    "from_address": "0xescrow_contract...",
    "to_address": "0xworker_wallet...",
    "status": "completed",
    "timestamp": "2026-01-25T15:00:00Z",
    "gas_used": 21000
  },
  "metadata": { ... }
}
```

### Dispute Payload

Used in all `dispute.*` events:

```json
{
  "event": "dispute.opened",
  "data": {
    "dispute_id": "dsp_ghi789",
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "submission_id": "7f3c1d2e-4a5b-6c7d-8e9f-0a1b2c3d4e5f",
    "initiator_id": "0x1234...",
    "respondent_id": "exec_xyz789",
    "reason": "Evidence does not match location requirements",
    "status": "open",
    "amount_disputed": 15.00,
    "evidence_count": 0,
    "opened_at": "2026-01-25T16:00:00Z",
    "resolved_at": null,
    "resolution": null
  },
  "metadata": { ... }
}
```

### Worker Payload

Used in all `worker.*` events:

```json
{
  "event": "worker.applied",
  "data": {
    "worker_id": "exec_xyz789",
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "wallet_address": "0x9876543210fedcba9876543210fedcba98765432",
    "reputation_score": 87,
    "completed_tasks": 42,
    "message": "I'm located near this store and can verify within 2 hours."
  },
  "metadata": { ... }
}
```

### Reputation Payload

Used in `reputation.updated` events:

```json
{
  "event": "reputation.updated",
  "data": {
    "entity_id": "exec_xyz789",
    "entity_type": "worker",
    "old_score": 85,
    "new_score": 87,
    "change_reason": "Task completed successfully",
    "task_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "metadata": { ... }
}
```

---

## Signature Verification

All webhooks are signed with HMAC-SHA256 for security. **Always verify signatures** before processing webhooks.

### Signature Format

The `X-Webhook-Signature` header contains:

```
t=<timestamp>,v1=<signature>
```

Example:
```
t=1706180000,v1=5257a869e7ecebeda32affa62cdca3fa51cad7e77a0e56ff536d0ce8e108d8bd
```

### Verification Algorithm

1. Extract timestamp (`t`) and signature (`v1`) from header
2. Create the signed payload: `{timestamp}.{request_body}`
3. Compute HMAC-SHA256 using your webhook secret
4. Compare signatures (use constant-time comparison)
5. Verify timestamp is recent (within 5 minutes)

### Python Example

```python
import hmac
import hashlib
import time

def verify_webhook_signature(
    payload: str,
    signature_header: str,
    secret: str,
    tolerance_seconds: int = 300
) -> bool:
    """
    Verify webhook signature.

    Args:
        payload: Raw request body as string
        signature_header: X-Webhook-Signature header value
        secret: Your webhook secret
        tolerance_seconds: Max age of signature (default: 5 minutes)

    Returns:
        True if signature is valid

    Raises:
        ValueError: If signature is invalid or expired
    """
    # Parse signature header
    parts = {}
    for part in signature_header.split(","):
        if "=" in part:
            key, value = part.split("=", 1)
            parts[key] = value

    if "t" not in parts or "v1" not in parts:
        raise ValueError("Invalid signature format")

    timestamp = int(parts["t"])
    signature = parts["v1"]

    # Check timestamp freshness
    current_time = int(time.time())
    if abs(current_time - timestamp) > tolerance_seconds:
        raise ValueError(f"Signature expired: {current_time - timestamp}s old")

    # Compute expected signature
    signed_payload = f"{timestamp}.{payload}"
    expected = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Signature mismatch")

    return True


# Flask example
from flask import Flask, request, jsonify

app = Flask(__name__)
WEBHOOK_SECRET = "whsec_xxxxxxxxxxxxx"

@app.route("/webhooks/execution-market", methods=["POST"])
def handle_webhook():
    payload = request.get_data(as_text=True)
    signature = request.headers.get("X-Webhook-Signature")

    try:
        verify_webhook_signature(payload, signature, WEBHOOK_SECRET)
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

    event = request.json
    event_type = event["event"]

    # Handle the event
    if event_type == "task.completed":
        handle_task_completed(event["data"])
    elif event_type == "payment.released":
        handle_payment_released(event["data"])

    return jsonify({"received": True}), 200
```

### Node.js Example

```javascript
const crypto = require('crypto');

function verifyWebhookSignature(payload, signatureHeader, secret, toleranceSeconds = 300) {
    // Parse signature header
    const parts = {};
    signatureHeader.split(',').forEach(part => {
        const [key, value] = part.split('=');
        parts[key] = value;
    });

    if (!parts.t || !parts.v1) {
        throw new Error('Invalid signature format');
    }

    const timestamp = parseInt(parts.t, 10);
    const signature = parts.v1;

    // Check timestamp freshness
    const currentTime = Math.floor(Date.now() / 1000);
    if (Math.abs(currentTime - timestamp) > toleranceSeconds) {
        throw new Error(`Signature expired: ${currentTime - timestamp}s old`);
    }

    // Compute expected signature
    const signedPayload = `${timestamp}.${payload}`;
    const expected = crypto
        .createHmac('sha256', secret)
        .update(signedPayload)
        .digest('hex');

    // Constant-time comparison
    if (!crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected))) {
        throw new Error('Signature mismatch');
    }

    return true;
}

// Express example
const express = require('express');
const app = express();

const WEBHOOK_SECRET = 'whsec_xxxxxxxxxxxxx';

app.post('/webhooks/execution-market', express.raw({ type: 'application/json' }), (req, res) => {
    const payload = req.body.toString();
    const signature = req.headers['x-webhook-signature'];

    try {
        verifyWebhookSignature(payload, signature, WEBHOOK_SECRET);
    } catch (err) {
        return res.status(401).json({ error: err.message });
    }

    const event = JSON.parse(payload);

    // Handle the event
    switch (event.event) {
        case 'task.completed':
            handleTaskCompleted(event.data);
            break;
        case 'payment.released':
            handlePaymentReleased(event.data);
            break;
    }

    res.json({ received: true });
});
```

---

## Retry Policy

Execution Market uses exponential backoff for failed webhook deliveries.

### Retry Schedule

| Attempt | Delay | Total Time |
|---------|-------|------------|
| 1 | Immediate | 0 |
| 2 | 1 second | 1s |
| 3 | 2 seconds | 3s |
| 4 | 4 seconds | 7s |
| 5 | 8 seconds | 15s |
| 6 | 16 seconds | 31s |

After 6 failed attempts, the webhook is moved to the dead letter queue.

### Success Criteria

A delivery is considered successful if:
- HTTP status code is 2xx (200, 201, 202, 204)
- Response is received within 30 seconds

### Failure Handling

Failed deliveries are retried automatically. After 10 consecutive failures, the webhook endpoint is automatically disabled (`status: "failed"`).

To re-enable a failed webhook:

```bash
curl -X POST https://api.execution.market/api/v1/webhooks/{webhook_id}/resume \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Dead Letter Queue

Events that fail all retry attempts are stored in the dead letter queue for 7 days. You can retrieve and replay them:

```bash
# List dead letter events
curl https://api.execution.market/api/v1/webhooks/{webhook_id}/dead-letter \
  -H "Authorization: Bearer YOUR_API_KEY"

# Replay a dead letter event
curl -X POST https://api.execution.market/api/v1/webhooks/dead-letter/{event_id}/replay \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Registration and Management

### Register a Webhook

```bash
curl -X POST https://api.execution.market/api/v1/webhooks \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-server.com/webhooks/execution-market",
    "events": [
      "task.created",
      "task.completed",
      "submission.received",
      "payment.released"
    ],
    "description": "Production webhook for task notifications"
  }'

# Response
{
  "webhook_id": "wh_abc123xyz",
  "url": "https://your-server.com/webhooks/execution-market",
  "events": ["task.created", "task.completed", "submission.received", "payment.released"],
  "status": "active",
  "secret": "whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "created_at": "2026-01-25T10:30:00Z"
}
```

**Important**: The `secret` is only returned at creation time. Store it securely.

### List Webhooks

```bash
curl https://api.execution.market/api/v1/webhooks \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Update Webhook

```bash
curl -X PATCH https://api.execution.market/api/v1/webhooks/{webhook_id} \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://new-server.com/webhooks/execution-market",
    "events": ["task.created", "task.completed"]
  }'
```

### Delete Webhook

```bash
curl -X DELETE https://api.execution.market/api/v1/webhooks/{webhook_id} \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Pause/Resume Webhook

```bash
# Pause
curl -X POST https://api.execution.market/api/v1/webhooks/{webhook_id}/pause \
  -H "Authorization: Bearer YOUR_API_KEY"

# Resume
curl -X POST https://api.execution.market/api/v1/webhooks/{webhook_id}/resume \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Rotate Secret

```bash
curl -X POST https://api.execution.market/api/v1/webhooks/{webhook_id}/rotate-secret \
  -H "Authorization: Bearer YOUR_API_KEY"

# Response
{
  "webhook_id": "wh_abc123xyz",
  "secret": "whsec_new_secret_xxxxxxxxxxxxx"
}
```

### Get Webhook Stats

```bash
curl https://api.execution.market/api/v1/webhooks/{webhook_id}/stats \
  -H "Authorization: Bearer YOUR_API_KEY"

# Response
{
  "webhook_id": "wh_abc123xyz",
  "status": "active",
  "total_deliveries": 1547,
  "successful_deliveries": 1523,
  "success_rate": 98.4,
  "failure_count": 0,
  "last_triggered_at": "2026-01-25T15:30:00Z",
  "average_latency_ms": 145
}
```

---

## Testing Webhooks

### Send Test Event

```bash
curl -X POST https://api.execution.market/api/v1/webhooks/{webhook_id}/test \
  -H "Authorization: Bearer YOUR_API_KEY"

# Response
{
  "success": true,
  "delivery_id": "del_xyz789",
  "status_code": 200,
  "latency_ms": 156
}
```

### Local Development

Use a tunnel service for local testing:

```bash
# Using ngrok
ngrok http 3000

# Register webhook with ngrok URL
curl -X POST https://api.execution.market/api/v1/webhooks \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "url": "https://abc123.ngrok.io/webhooks/execution-market",
    "events": ["task.created", "task.completed"]
  }'
```

### Webhook Logs

View recent webhook deliveries:

```bash
curl https://api.execution.market/api/v1/webhooks/{webhook_id}/logs \
  -H "Authorization: Bearer YOUR_API_KEY"

# Response
{
  "logs": [
    {
      "delivery_id": "del_abc123",
      "event_type": "task.created",
      "status": "delivered",
      "status_code": 200,
      "latency_ms": 145,
      "timestamp": "2026-01-25T15:30:00Z"
    },
    {
      "delivery_id": "del_def456",
      "event_type": "submission.received",
      "status": "delivered",
      "status_code": 200,
      "latency_ms": 132,
      "timestamp": "2026-01-25T15:25:00Z"
    }
  ],
  "total": 1547,
  "has_more": true
}
```

---

## Best Practices

1. **Always verify signatures** - Never process unverified webhooks
2. **Respond quickly** - Return 2xx within 30 seconds
3. **Handle idempotently** - Events may be delivered multiple times
4. **Use the event_id** - Deduplicate using the unique event ID
5. **Process asynchronously** - Queue events for background processing
6. **Monitor failures** - Set up alerts for delivery failures
7. **Rotate secrets periodically** - Rotate webhook secrets every 90 days

---

## Next Steps

- [API Reference](./API.md) - Complete API documentation
- [Integration Guide](./INTEGRATION.md) - Quick start guides
- [Examples](../examples/) - Code samples
