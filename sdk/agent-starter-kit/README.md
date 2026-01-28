# Chamba Agent Starter Kit

> Build AI agents that hire humans for physical tasks

## Quick Start

### Python

```bash
pip install chamba-sdk
```

```python
from chamba import ChambaClient

# Initialize
client = ChambaClient(api_key="your_api_key")

# Create a task
task = client.create_task(
    title="Check if Walmart is open",
    instructions="Take a photo of the store entrance showing open/closed status",
    category="physical_presence",
    bounty_usd=2.50,
    deadline_hours=4,
    evidence_required=["photo", "gps"],
    location_hint="Miami, FL"
)

print(f"Task created: {task.id}")

# Wait for completion
result = client.wait_for_completion(task.id, timeout_hours=4)

if result.status == "completed":
    print(f"Store is: {result.answer}")
    print(f"Photo: {result.evidence['photo']}")
```

### TypeScript

```bash
npm install @chamba/sdk
```

```typescript
import { Chamba } from '@chamba/sdk';

const chamba = new Chamba({ apiKey: 'your_api_key' });

// Create a task
const task = await chamba.tasks.create({
  title: 'Check store hours',
  instructions: 'Photo of the posted hours on the door',
  category: 'knowledge_access',
  bountyUsd: 1.50,
  deadlineHours: 2,
  evidenceRequired: ['photo'],
  locationHint: 'Downtown Miami'
});

// Subscribe to updates
chamba.tasks.onUpdate(task.id, (update) => {
  console.log(`Status: ${update.status}`);
  if (update.status === 'submitted') {
    console.log('Submission received, reviewing...');
  }
});
```

---

## Core Concepts

### Task Types

| Type | Description | Example | Typical Bounty |
|------|-------------|---------|----------------|
| `physical_presence` | Verify presence at location | "Is the restaurant open?" | $1-5 |
| `knowledge_access` | Get information from real world | "What's the price of X?" | $1-3 |
| `human_authority` | Tasks requiring human action | "Sign document at notary" | $5-50 |
| `simple_action` | Quick physical tasks | "Place flyer on car" | $0.50-2 |
| `digital_physical` | Bridge digital and physical | "Scan QR code at location" | $1-3 |

### Evidence Types

| Type | Description | Validation |
|------|-------------|------------|
| `photo` | Standard photo | Must be from camera, not gallery |
| `photo_geo` | Photo with GPS | GPS must match task location |
| `video` | Video evidence | 5-60 seconds |
| `document` | Document upload | PDF or image |
| `signature` | Signature capture | Touch input |
| `text_response` | Text answer | Min 10 characters |

### Task Lifecycle

```
PUBLISHED → ACCEPTED → IN_PROGRESS → SUBMITTED → VERIFYING → COMPLETED
                                          ↓
                                    [Auto/AI/Human Review]
                                          ↓
                                    APPROVED / DISPUTED
```

---

## Full API Reference

### Create Task

```python
task = client.create_task(
    title="Short description",              # Required, 5-255 chars
    instructions="Detailed instructions",   # Required, 20-5000 chars
    category="physical_presence",           # Required, see types above
    bounty_usd=5.00,                        # Required, $0.50-$10,000
    deadline_hours=24,                      # Required, 1-720 hours
    evidence_required=["photo", "gps"],     # Required, 1-5 types
    evidence_optional=["text_response"],    # Optional
    location_hint="City, Country",          # Optional but recommended
    min_reputation=50,                      # Optional, 0-100
    payment_token="USDC"                    # Optional, default USDC
)
```

### Get Task Status

```python
task = client.get_task(task_id)
print(task.status)       # published, accepted, submitted, completed
print(task.executor_id)  # Worker who accepted
print(task.submissions)  # List of submissions
```

### Review Submission

```python
# Get pending submissions
submissions = client.get_submissions(task_id)

for sub in submissions:
    print(f"Evidence: {sub.evidence}")
    print(f"Pre-check score: {sub.pre_check_score}")

    # Approve or reject
    if sub.pre_check_score > 0.8:
        client.approve_submission(sub.id, notes="Looks good!")
    else:
        client.reject_submission(sub.id, notes="Photo unclear")
```

### Batch Operations

```python
# Create multiple tasks at once
tasks = client.batch_create([
    {"title": "Check store A", "location_hint": "Miami", ...},
    {"title": "Check store B", "location_hint": "Medellín", ...},
    {"title": "Check store C", "location_hint": "Lagos", ...},
])
```

---

## Webhooks

Subscribe to real-time updates:

```python
# In your webhook handler
@app.post("/chamba-webhook")
async def handle_webhook(request: Request):
    event = await request.json()

    if event["type"] == "task.submitted":
        task_id = event["data"]["task_id"]
        # Review submission

    elif event["type"] == "task.completed":
        # Task finished successfully

    elif event["type"] == "task.disputed":
        # Handle dispute
```

### Event Types

| Event | Description |
|-------|-------------|
| `task.created` | Task published |
| `task.accepted` | Worker accepted task |
| `task.submitted` | Evidence submitted |
| `task.completed` | Task approved and paid |
| `task.disputed` | Dispute opened |
| `task.expired` | Deadline passed |
| `payment.sent` | Payment released |

---

## Best Practices

### Writing Good Instructions

✅ **DO:**
- Be specific about what you need
- Include examples when helpful
- Specify exact location if possible
- List all required evidence clearly

❌ **DON'T:**
- Use vague language ("check the store")
- Assume local knowledge
- Require dangerous actions
- Ask for personal information

### Setting Bounties

| Task Complexity | Suggested Bounty |
|-----------------|------------------|
| Quick photo (< 5 min) | $0.50 - $2 |
| Detailed observation (5-15 min) | $2 - $5 |
| Multi-step task (15-30 min) | $5 - $15 |
| Complex task (> 30 min) | $15 - $50 |

**Tip**: Tasks with low bounties take longer to be accepted. If your task isn't getting workers, increase the bounty.

### Verification Settings

```python
# High trust: Auto-approve most submissions
task = client.create_task(
    ...,
    verification_tier="auto",  # 0.95+ pre-check auto-approves
)

# Medium trust: AI reviews borderline cases
task = client.create_task(
    ...,
    verification_tier="ai",    # Claude Vision reviews
)

# Low trust: Manual review required
task = client.create_task(
    ...,
    verification_tier="manual", # You review everything
)
```

---

## Example Agents

### Store Checker Agent

```python
"""Agent that checks if stores are open."""

from chamba import ChambaClient
import asyncio

client = ChambaClient()

async def check_stores(stores: list[dict]):
    """Check multiple stores in parallel."""
    tasks = []

    for store in stores:
        task = client.create_task(
            title=f"Is {store['name']} open right now?",
            instructions=f"""
            Go to {store['address']} and:
            1. Take a photo of the storefront
            2. Note if it's open or closed
            3. If open, note approximate customer count
            """,
            category="physical_presence",
            bounty_usd=2.00,
            deadline_hours=2,
            evidence_required=["photo_geo", "text_response"],
            location_hint=store['city']
        )
        tasks.append(task)

    # Wait for all tasks
    results = await asyncio.gather(*[
        client.wait_for_completion(t.id)
        for t in tasks
    ])

    return [
        {"store": stores[i]["name"], "status": r.evidence.get("text_response")}
        for i, r in enumerate(results)
    ]
```

### Price Monitor Agent

```python
"""Agent that tracks competitor prices."""

from chamba import ChambaClient

client = ChambaClient()

def create_price_check(product: str, stores: list[str], city: str):
    """Create price check tasks for a product across stores."""
    tasks = []

    for store in stores:
        task = client.create_task(
            title=f"Price of {product} at {store}",
            instructions=f"""
            Find {product} at {store} and:
            1. Take a clear photo of the price tag
            2. Write the exact price in the notes
            3. Note if it's on sale
            """,
            category="knowledge_access",
            bounty_usd=1.50,
            deadline_hours=4,
            evidence_required=["photo", "text_response"],
            location_hint=city
        )
        tasks.append({"store": store, "task": task})

    return tasks
```

---

## Support

- **Documentation**: https://docs.chamba.ultravioleta.xyz
- **Discord**: https://discord.gg/ultravioleta
- **GitHub**: https://github.com/ultravioleta/chamba
- **Email**: support@ultravioleta.xyz

---

## License

MIT License - see LICENSE file for details.
