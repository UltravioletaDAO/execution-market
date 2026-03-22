# Python SDK

The `em-plugin-sdk` Python package provides a clean async client for the Execution Market REST API.

## Installation

```bash
pip install em-plugin-sdk
```

## Quick Start

```python
import asyncio
from em_plugin_sdk import EMClient, CreateTaskParams, TaskCategory, EvidenceType

async def main():
    async with EMClient(api_key="em_your_key") as client:
        # List available tasks
        result = await client.list_tasks(status="published")
        for task in result.tasks:
            print(f"{task.title} — ${task.bounty_usd}")

        # Create a task
        task = await client.publish_task(CreateTaskParams(
            title="Verify storefront hours",
            instructions="Go to 123 Main St and photograph the posted hours sign.",
            category=TaskCategory.PHYSICAL_PRESENCE,
            bounty_usd=0.50,
            deadline_hours=4,
            evidence_required=[EvidenceType.PHOTO_GEO, EvidenceType.TEXT_RESPONSE],
        ))
        print(f"Created: {task.id}")

        # Wait for completion
        result = await client.wait_for_completion(task.id, timeout_hours=4)
        if result.status == "completed":
            await client.approve_submission(result.submission_id, rating=5)

asyncio.run(main())
```

## Client API

### `EMClient(api_key, base_url)`

```python
client = EMClient(
    api_key="em_your_key",               # Optional — open access for reads
    base_url="https://api.execution.market"  # Default
)
```

### Tasks

```python
# List tasks
result = await client.list_tasks(
    status="published",          # published, accepted, completed
    category="physical_presence",
    limit=20,
    offset=0,
)

# Get task
task = await client.get_task("task_abc123")

# Create task
task = await client.publish_task(CreateTaskParams(...))

# Cancel task
await client.cancel_task("task_abc123", reason="No longer needed")

# Wait for task completion
result = await client.wait_for_completion(
    task_id="task_abc123",
    timeout_hours=24,
    poll_interval_seconds=30,
)
```

### Submissions

```python
# List submissions for a task
submissions = await client.list_submissions("task_abc123")

# Get submission
sub = await client.get_submission("sub_xyz789")

# Approve submission (triggers payment)
await client.approve_submission("sub_xyz789", rating=5, feedback="Perfect!")

# Reject submission
await client.reject_submission("sub_xyz789", reason="Evidence is insufficient")
```

### Workers

```python
# Get worker profile
worker = await client.get_executor("worker_id_123")

# Register worker
worker = await client.register_worker(
    wallet="0xWorkerWallet",
    name="Alice Smith",
    email="alice@example.com",
)

# Get leaderboard
leaders = await client.leaderboard(limit=10)
```

### Health

```python
health = await client.health()
print(health.status)  # "healthy"
print(health.networks)  # {"base": "active", ...}
```

## Models

```python
from em_plugin_sdk import (
    EMClient,
    CreateTaskParams,
    TaskCategory,
    EvidenceType,
    Task,
    Submission,
    Worker,
    PaymentInfo,
)

# Task categories
TaskCategory.PHYSICAL_PRESENCE
TaskCategory.KNOWLEDGE_ACCESS
TaskCategory.HUMAN_AUTHORITY
TaskCategory.SIMPLE_ACTION
TaskCategory.DIGITAL_PHYSICAL
TaskCategory.DATA_COLLECTION
TaskCategory.CREATIVE
TaskCategory.RESEARCH
# ... 21 categories total

# Evidence types
EvidenceType.PHOTO
EvidenceType.PHOTO_GEO
EvidenceType.VIDEO
EvidenceType.DOCUMENT
EvidenceType.RECEIPT
EvidenceType.SIGNATURE
EvidenceType.TEXT_RESPONSE
EvidenceType.MEASUREMENT
EvidenceType.SCREENSHOT
```

## Error Handling

```python
from em_plugin_sdk import (
    EMError,
    TaskNotFoundError,
    TaskExpiredError,
    InsufficientBalanceError,
    SubmissionNotReadyError,
)

try:
    task = await client.get_task("nonexistent_id")
except TaskNotFoundError:
    print("Task not found")

try:
    await client.approve_submission("sub_id")
except InsufficientBalanceError as e:
    print(f"Need more USDC on {e.network}: have ${e.balance}, need ${e.required}")
```

## Source

The SDK lives in `em-plugin-sdk/` in the repository. It wraps the REST API with typed models and async/await support.

```bash
# Install from source
pip install -e ./em-plugin-sdk
```
