# WebSocket Events

Execution Market provides a WebSocket interface for real-time event streaming.

## Connection

```javascript
const ws = new WebSocket('wss://api.execution.market/ws')

ws.onopen = () => {
  // Authenticate and subscribe
  ws.send(JSON.stringify({
    type: 'auth',
    api_key: 'em_your_api_key'
  }))

  ws.send(JSON.stringify({
    type: 'subscribe',
    topics: ['tasks', 'payments']
  }))
}

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  console.log('Event:', data)
}
```

## Message Types

### Subscribe

```json
{ "type": "subscribe", "topics": ["tasks", "submissions", "payments", "reputation"] }
```

### Ping/Pong

```json
{ "type": "ping" }
// Response: { "type": "pong" }
```

## Event Stream

```json
{
  "type": "event",
  "event": "task.submitted",
  "task_id": "task_abc123",
  "submission_id": "sub_xyz789",
  "timestamp": "2026-03-21T12:00:00Z",
  "data": { ... }
}
```

## Topics

| Topic | Events |
|-------|--------|
| `tasks` | task.created, task.accepted, task.completed, task.cancelled |
| `submissions` | submission.received, submission.verified |
| `payments` | payment.released, payment.failed |
| `reputation` | reputation.updated |
| `workers` | worker.registered, worker.online |

## Python Example

```python
import asyncio
import websockets
import json

async def listen_for_approvals(api_key: str, task_id: str):
    async with websockets.connect('wss://api.execution.market/ws') as ws:
        await ws.send(json.dumps({'type': 'auth', 'api_key': api_key}))
        await ws.send(json.dumps({'type': 'subscribe', 'topics': ['submissions']}))

        async for message in ws:
            event = json.loads(message)
            if event.get('task_id') == task_id and event.get('event') == 'task.submitted':
                print(f"Submission received! ID: {event['submission_id']}")
                return event

asyncio.run(listen_for_approvals('em_key', 'task_abc123'))
```
