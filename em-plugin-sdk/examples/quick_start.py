"""Quick start — publish a task, wait for submission, approve it."""

import asyncio
from em_plugin_sdk import (
    EMClient,
    CreateTaskParams,
    TaskCategory,
    EvidenceType,
    ApproveParams,
)


async def main():
    async with EMClient(api_key="em_your_key_here") as client:
        # 1. Publish a task
        task = await client.tasks.create(CreateTaskParams(
            title="Verify coffee shop is open",
            instructions="Go to Blue Bottle Coffee at 123 Main St and photograph the storefront showing it is open.",
            category=TaskCategory.PHYSICAL_PRESENCE,
            bounty_usd=2.00,
            deadline_hours=4,
            evidence_required=[EvidenceType.PHOTO_GEO],
            location_hint="San Francisco, CA",
            payment_network="base",
        ))
        print(f"Published task {task.id} — ${task.bounty_usd}")

        # 2. Wait for applications
        while True:
            apps = await client.tasks.list_applications(task.id)
            if apps.count > 0:
                break
            await asyncio.sleep(10)

        # 3. Assign the first applicant
        applicant = apps.applications[0]
        await client.tasks.assign(task.id, applicant.executor_id)
        print(f"Assigned to {applicant.executor_id}")

        # 4. Wait for submission
        while True:
            subs = await client.submissions.list(task.id)
            if subs.count > 0:
                break
            await asyncio.sleep(10)

        # 5. Approve
        sub = subs.submissions[0]
        await client.submissions.approve(sub.id, ApproveParams(notes="Photo verified"))
        print(f"Approved submission {sub.id} — payment released!")


if __name__ == "__main__":
    asyncio.run(main())
