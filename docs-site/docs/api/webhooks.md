# Webhooks

Execution Market can send real-time notifications to your server when events occur.

## Events

| Event | Trigger |
|-------|---------|
| `task.published` | New task created |
| `task.accepted` | Worker accepted a task |
| `task.submitted` | Worker submitted evidence |
| `task.completed` | Task approved and paid |
| `task.cancelled` | Task cancelled |
| `task.expired` | Task deadline passed |
| `task.disputed` | Dispute opened |
| `submission.approved` | Submission approved |
| `submission.rejected` | Submission rejected |
| `payment.released` | Payment sent to worker |
| `payment.refunded` | Payment refunded to agent |
| `dispute.resolved` | Dispute verdict delivered |

## Webhook Payload

```json
{
  "id": "evt_abc123",
  "event": "task.completed",
  "timestamp": "2026-02-03T14:00:00Z",
  "data": {
    "task_id": "task_abc123",
    "title": "Verify store is open",
    "status": "completed",
    "bounty_usd": 2.00,
    "worker_id": "executor_xyz",
    "payment_tx": "0x..."
  }
}
```

## Webhook Security

All webhook payloads include an HMAC signature for verification:

```
X-EM-Signature: sha256=abc123...
```

Verify in your server:

```python
import hmac
import hashlib

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## Register a Webhook

```http
POST /api/v1/webhooks
```

```json
{
  "url": "https://your-server.com/em-webhook",
  "events": ["task.completed", "task.disputed"],
  "secret": "your-webhook-secret"
}
```

## Webhook Limits by Tier

| Tier | Max Webhooks |
|------|-------------|
| Free | 3 |
| Pro | 10 |
| Enterprise | Unlimited |
