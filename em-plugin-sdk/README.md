# em-plugin-sdk

Python SDK for the [Execution Market](https://execution.market) REST API.

## Install

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

        # Publish a task
        task = await client.publish_task(CreateTaskParams(
            title="Take photo of storefront",
            instructions="Go to 123 Main St and photograph the storefront during business hours",
            category=TaskCategory.PHYSICAL_PRESENCE,
            bounty_usd=0.10,
            deadline_hours=24,
            evidence_required=[EvidenceType.PHOTO_GEO],
        ))
        print(f"Created task {task.id}")

asyncio.run(main())
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
| `health()` | `GET /health` | API health check |

## License

MIT
