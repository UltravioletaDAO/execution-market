"""Worker agent — browse tasks, apply, submit evidence."""

import asyncio
from em_plugin_sdk import EMClient, SubmitEvidenceParams


async def main():
    async with EMClient(api_key="em_worker_key") as client:
        # Register as a worker
        worker = await client.workers.register(
            wallet_address="0x1234567890abcdef1234567890abcdef12345678",
            name="PhotoBot",
        )
        print(f"Registered: {worker.id}")

        # Browse available tasks
        available = await client.tasks.available(category="physical_presence", min_bounty=1.0)
        for t in available["tasks"]:
            print(f"  {t['title']} — ${t['bounty_usd']}")

        if not available["tasks"]:
            print("No tasks available")
            return

        # Apply to the first task
        task_id = available["tasks"][0]["id"]
        app = await client.tasks.apply(task_id, worker.id, message="I'm nearby!")
        print(f"Applied to {task_id}")

        # After being assigned and completing the work, submit evidence
        evidence_url = await client.evidence.upload(
            task_id=task_id,
            filename="storefront.jpg",
            data=b"<photo bytes>",
            content_type="image/jpeg",
        )

        sub = await client.submissions.submit(task_id, SubmitEvidenceParams(
            executor_id=worker.id,
            evidence={"photo_geo": {"url": evidence_url, "lat": 37.78, "lng": -122.41}},
            notes="Store is open, photographed at 2pm",
        ))
        print(f"Submitted: {sub.id}")


if __name__ == "__main__":
    asyncio.run(main())
