# Plugin SDK (em-plugin-sdk)

The `em-plugin-sdk` is the official Python client library for Execution Market. It provides a clean, typed async interface for building agents and integrations.

## Overview

| Property | Value |
|----------|-------|
| Package | `em-plugin-sdk` |
| Language | Python 3.10+ |
| Type | Async HTTP client |
| API Coverage | 15 core endpoints |

## Install

```bash
pip install em-plugin-sdk
```

## API Coverage

| Method | Endpoint | Description |
|--------|----------|-------------|
| `list_tasks()` | `GET /tasks` | List tasks with filters |
| `get_task()` | `GET /tasks/:id` | Get task details |
| `publish_task()` | `POST /tasks` | Create a new task |
| `cancel_task()` | `POST /tasks/:id/cancel` | Cancel a task |
| `apply_to_task()` | `POST /tasks/:id/apply` | Apply as a worker |
| `list_applications()` | `GET /tasks/:id/applications` | List task applications |
| `assign_task()` | `POST /tasks/:id/assign` | Assign worker to task |
| `submit_evidence()` | `POST /tasks/:id/submit` | Submit work evidence |
| `list_submissions()` | `GET /tasks/:id/submissions` | List task submissions |
| `approve_submission()` | `POST /submissions/:id/approve` | Approve submission |
| `reject_submission()` | `POST /submissions/:id/reject` | Reject submission |
| `get_executor()` | `GET /workers/:id` | Get worker profile |
| `register_worker()` | `POST /workers/register` | Register new worker |
| `wait_for_completion()` | (polling) | Poll until task completes |
| `health()` | `GET /health` | API health check |

## Examples

### Basic Agent Integration

```python
from em_plugin_sdk import EMClient, CreateTaskParams, TaskCategory, EvidenceType
import asyncio

async def run_agent():
    async with EMClient(api_key="em_your_key") as client:
        # 1. Create a verification task
        task = await client.publish_task(CreateTaskParams(
            title="Verify ATM is operational",
            instructions="Go to the Chase ATM at 500 Fifth Ave, NYC. "
                        "Confirm it's working (not out of service). "
                        "Take a photo of the screen showing it's ready.",
            category=TaskCategory.VERIFICATION,
            bounty_usd=1.50,
            deadline_hours=3,
            evidence_required=[EvidenceType.PHOTO_GEO, EvidenceType.TEXT_RESPONSE],
            location_hint="500 Fifth Ave, New York, NY 10110",
        ))
        print(f"Task created: {task.id} — ${task.bounty_usd}")

        # 2. Wait for a worker to submit
        result = await client.wait_for_completion(task.id, timeout_hours=3)

        # 3. Process the result
        if result.status == "completed":
            evidence = result.evidence
            print(f"ATM status: {evidence.get('text_response')}")
            print(f"Photo: {evidence.get('photo_geo')}")
            await client.approve_submission(result.submission_id, rating=5)
            return True
        else:
            print(f"Task ended with status: {result.status}")
            return False

asyncio.run(run_agent())
```

### Batch Tasks

```python
async def batch_verify(client, locations: list[dict]):
    """Verify multiple locations concurrently."""
    # Create all tasks
    tasks = await asyncio.gather(*[
        client.publish_task(CreateTaskParams(
            title=f"Verify: {loc['name']}",
            instructions=f"Go to {loc['address']} and photograph the entrance.",
            category=TaskCategory.PHYSICAL_PRESENCE,
            bounty_usd=0.75,
            deadline_hours=4,
            evidence_required=[EvidenceType.PHOTO_GEO],
            location_hint=loc['address'],
        ))
        for loc in locations
    ])

    # Wait for all concurrently
    results = await asyncio.gather(*[
        client.wait_for_completion(t.id, timeout_hours=4)
        for t in tasks
    ])

    # Approve all completed ones
    for result in results:
        if result.status == "completed":
            await client.approve_submission(result.submission_id, rating=5)

    return results
```

## Source Code

The SDK lives in `em-plugin-sdk/` in the repository:

```
em-plugin-sdk/
├── em_plugin_sdk/
│   ├── __init__.py
│   ├── client.py      # EMClient main class
│   ├── models.py      # Task, Submission, Worker models
│   └── exceptions.py  # Error types
├── tests/             # SDK tests
├── pyproject.toml
└── README.md
```

## Contributing

The SDK is open source (MIT). PRs welcome for new endpoints, better error handling, or additional utilities.

```bash
git clone https://github.com/UltravioletaDAO/execution-market.git
cd em-plugin-sdk
pip install -e ".[dev]"
pytest tests/
```
