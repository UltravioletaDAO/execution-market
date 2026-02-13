#!/usr/bin/env python3
"""
Example: Worker Completing a Task

This example demonstrates how a human worker can use the Execution Market MCP server
to browse available tasks, apply to a task, submit evidence, and withdraw
earnings.

Requirements:
    pip install mcp aiohttp

Usage:
    python worker_complete_task.py
"""

import asyncio
import json
import os
from datetime import datetime, timezone


class MockMCPClient:
    """Mock MCP client for demonstration purposes."""

    def __init__(self, base_url: str = "https://api.execution.market"):
        self.base_url = base_url
        self.connected = False

    async def connect(self, url: str):
        """Connect to MCP server."""
        print(f"Connecting to {url}...")
        self.connected = True
        print("Connected!")

    async def call_tool(self, tool_name: str, params: dict) -> dict:
        """Call an MCP tool."""
        print(f"\nCalling tool: {tool_name}")
        print(f"Parameters: {json.dumps(params, indent=2)}")

        # Simulated responses for demonstration
        if tool_name == "em_get_tasks":
            return {
                "total": 25,
                "count": 3,
                "tasks": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "title": "Verify coffee shop hours",
                        "status": "published",
                        "category": "physical_presence",
                        "bounty_usd": 10.00,
                        "deadline": "2026-01-26T10:30:00Z",
                        "location_hint": "San Francisco, CA",
                        "min_reputation": 50,
                        "evidence_required": ["photo_geo", "text_response"],
                    },
                    {
                        "id": "661f9511-f30c-52e5-b827-557766551111",
                        "title": "Check grocery store inventory",
                        "status": "published",
                        "category": "physical_presence",
                        "bounty_usd": 15.00,
                        "deadline": "2026-01-26T18:00:00Z",
                        "location_hint": "San Francisco, CA",
                        "min_reputation": 30,
                        "evidence_required": ["photo", "text_response"],
                    },
                    {
                        "id": "772e0622-g41d-63f6-c938-668877662222",
                        "title": "Photograph local event poster",
                        "status": "published",
                        "category": "physical_presence",
                        "bounty_usd": 5.00,
                        "deadline": "2026-01-25T22:00:00Z",
                        "location_hint": "San Francisco, CA",
                        "min_reputation": 0,
                        "evidence_required": ["photo_geo"],
                    },
                ],
            }
        elif tool_name == "em_apply_to_task":
            return {
                "success": True,
                "task_id": params["task_id"],
                "executor_id": params["executor_id"],
                "status": "accepted",  # Auto-accept for this example
                "message": "Your application was automatically accepted!",
            }
        elif tool_name == "em_submit_work":
            return {
                "success": True,
                "submission_id": "7f3c1d2e-4a5b-6c7d-8e9f-0a1b2c3d4e5f",
                "task_id": params["task_id"],
                "status": "pending",
                "evidence_received": list(params["evidence"].keys()),
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            }
        elif tool_name == "em_get_my_tasks":
            return {
                "total": 5,
                "completed": 3,
                "in_progress": 1,
                "pending_payment": 1,
                "available_balance": 28.50,
                "pending_balance": 10.00,
                "tasks": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "title": "Verify coffee shop hours",
                        "status": "submitted",
                        "bounty_usd": 10.00,
                        "submission_status": "pending",
                    },
                    {
                        "id": "previous-task-1",
                        "title": "Verify restaurant hours",
                        "status": "completed",
                        "bounty_usd": 12.00,
                        "earned": 10.44,  # After 13% fee
                    },
                    {
                        "id": "previous-task-2",
                        "title": "Check gym equipment",
                        "status": "completed",
                        "bounty_usd": 8.00,
                        "earned": 7.36,
                    },
                ],
            }
        elif tool_name == "em_withdraw_earnings":
            return {
                "success": True,
                "amount_usdc": params.get("amount_usdc") or 28.50,
                "destination": params.get("destination_address") or "0x9876...",
                "tx_hash": "0xabc123def456ghi789...",
                "network": "base",
                "gas_used": 0.50,
                "net_amount": 28.00,
                "estimated_arrival": "~2 minutes",
            }

        return {"error": f"Unknown tool: {tool_name}"}


async def browse_available_tasks(
    client: MockMCPClient,
    executor_id: str,
    my_reputation: int,
    my_location: str,
) -> list:
    """
    Browse tasks available in your area that match your reputation.

    Args:
        client: MCP client instance
        executor_id: Your executor ID
        my_reputation: Your current reputation score
        my_location: Your location

    Returns:
        List of available tasks
    """
    result = await client.call_tool(
        "em_get_tasks",
        {
            "status": "published",
            "category": "physical_presence",
            "limit": 20,
            "response_format": "json",
        },
    )

    # Filter tasks that match reputation
    available = [
        task for task in result["tasks"] if task["min_reputation"] <= my_reputation
    ]

    return available


async def apply_to_task(
    client: MockMCPClient,
    task_id: str,
    executor_id: str,
    message: str = "",
) -> dict:
    """
    Apply to work on a task.

    Args:
        client: MCP client instance
        task_id: The task to apply to
        executor_id: Your executor ID
        message: Optional message to the agent

    Returns:
        Application result
    """
    result = await client.call_tool(
        "em_apply_to_task",
        {
            "task_id": task_id,
            "executor_id": executor_id,
            "message": message,
        },
    )

    return result


async def submit_evidence(
    client: MockMCPClient,
    task_id: str,
    executor_id: str,
    evidence: dict,
    notes: str = "",
) -> dict:
    """
    Submit completed work with evidence.

    Args:
        client: MCP client instance
        task_id: The task ID
        executor_id: Your executor ID
        evidence: Evidence matching task requirements
        notes: Optional notes about the submission

    Returns:
        Submission result
    """
    result = await client.call_tool(
        "em_submit_work",
        {
            "task_id": task_id,
            "executor_id": executor_id,
            "evidence": evidence,
            "notes": notes,
        },
    )

    return result


async def check_my_status(client: MockMCPClient, executor_id: str) -> dict:
    """
    Check your task history and available balance.

    Args:
        client: MCP client instance
        executor_id: Your executor ID

    Returns:
        Your tasks and earnings status
    """
    result = await client.call_tool(
        "em_get_my_tasks",
        {
            "executor_id": executor_id,
            "response_format": "json",
        },
    )

    return result


async def withdraw_earnings(
    client: MockMCPClient,
    executor_id: str,
    amount: float = None,
) -> dict:
    """
    Withdraw available earnings to your wallet.

    Args:
        client: MCP client instance
        executor_id: Your executor ID
        amount: Amount to withdraw (None = all available)

    Returns:
        Withdrawal result
    """
    params = {"executor_id": executor_id}
    if amount is not None:
        params["amount_usdc"] = amount

    result = await client.call_tool("em_withdraw_earnings", params)

    return result


def upload_photo_to_ipfs(photo_path: str) -> str:
    """
    Simulate uploading a photo to IPFS.

    In a real implementation, this would:
    1. Read the photo file
    2. Extract EXIF metadata (GPS, timestamp)
    3. Upload to IPFS (e.g., via Pinata, Infura, or web3.storage)
    4. Return the IPFS CID

    Args:
        photo_path: Path to the photo file

    Returns:
        IPFS CID
    """
    print(f"  Uploading {photo_path} to IPFS...")
    # Simulated CID
    return "QmXyz123abc456def789ghi012jkl345mno678pqr901stu"


def get_current_location() -> dict:
    """
    Get current GPS coordinates.

    In a real implementation, this would use device GPS.

    Returns:
        Location dict with lat/lng
    """
    # Simulated location (San Francisco)
    return {
        "lat": 37.7749,
        "lng": -122.4194,
    }


async def main():
    """
    Complete worker workflow example:
    1. Browse available tasks
    2. Apply to a task
    3. Complete the task and submit evidence
    4. Check earnings and withdraw
    """
    # Configuration
    executor_id = os.environ.get("EXECUTOR_ID", "exec_xyz789abc")
    my_reputation = 75  # Your current reputation score
    my_location = "San Francisco, CA"

    # Initialize client
    client = MockMCPClient()
    await client.connect("wss://api.execution.market/mcp")

    # Step 1: Browse available tasks
    print("\n" + "=" * 60)
    print("STEP 1: Browsing Available Tasks")
    print("=" * 60)

    tasks = await browse_available_tasks(
        client, executor_id, my_reputation, my_location
    )

    print(f"\nFound {len(tasks)} task(s) available for you:")
    for i, task in enumerate(tasks, 1):
        print(f"\n  {i}. {task['title']}")
        print(f"     Bounty: ${task['bounty_usd']:.2f}")
        print(f"     Deadline: {task['deadline']}")
        print(f"     Location: {task['location_hint']}")
        print(f"     Min Reputation: {task['min_reputation']}")
        print(f"     Evidence needed: {', '.join(task['evidence_required'])}")

    # Step 2: Apply to a task
    print("\n" + "=" * 60)
    print("STEP 2: Applying to Task")
    print("=" * 60)

    # Select the first task
    selected_task = tasks[0]
    task_id = selected_task["id"]

    print(f"\nApplying to: {selected_task['title']}")

    apply_result = await apply_to_task(
        client,
        task_id,
        executor_id,
        message="I'm near this location and can complete within 2 hours.",
    )

    print(f"\nApplication result: {apply_result['status']}")
    if apply_result.get("message"):
        print(f"Message: {apply_result['message']}")

    # Step 3: Complete the task and submit evidence
    print("\n" + "=" * 60)
    print("STEP 3: Completing Task and Submitting Evidence")
    print("=" * 60)

    print("\nCollecting evidence...")

    # Simulate collecting evidence
    print("  1. Taking photo with GPS...")
    photo_cid = upload_photo_to_ipfs("store_front.jpg")
    location = get_current_location()

    print("  2. Recording observations...")
    text_response = (
        "The coffee shop is currently OPEN. "
        "Posted hours: Monday-Saturday 7am-8pm, Sunday 8am-6pm. "
        "No special notices posted. "
        "Approximately 5 customers inside at time of visit."
    )

    # Build evidence package
    evidence = {
        "photo_geo": {
            "url": f"ipfs://{photo_cid}",
            "metadata": {
                "lat": location["lat"],
                "lng": location["lng"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
        "text_response": text_response,
    }

    print("\nSubmitting evidence...")
    submit_result = await submit_evidence(
        client,
        task_id,
        executor_id,
        evidence,
        notes="Photo clearly shows store front with hours posted on door.",
    )

    print("\nSubmission result:")
    print(f"  Submission ID: {submit_result['submission_id']}")
    print(f"  Status: {submit_result['status']}")
    print(f"  Evidence received: {', '.join(submit_result['evidence_received'])}")
    print("\nAwaiting agent review...")

    # Step 4: Check earnings
    print("\n" + "=" * 60)
    print("STEP 4: Checking Earnings and Status")
    print("=" * 60)

    status = await check_my_status(client, executor_id)

    print("\nYour Status:")
    print(f"  Total tasks: {status['total']}")
    print(f"  Completed: {status['completed']}")
    print(f"  In progress: {status['in_progress']}")
    print(f"  Pending payment: {status['pending_payment']}")
    print(f"\n  Available balance: ${status['available_balance']:.2f}")
    print(f"  Pending balance: ${status['pending_balance']:.2f}")

    print("\nRecent tasks:")
    for task in status["tasks"][:3]:
        earned = task.get("earned", 0)
        print(f"  - {task['title']}")
        print(
            f"    Status: {task['status']}, Bounty: ${task['bounty_usd']:.2f}", end=""
        )
        if earned:
            print(f", Earned: ${earned:.2f}")
        else:
            print()

    # Step 5: Withdraw earnings (if balance is sufficient)
    if status["available_balance"] >= 5.00:  # Minimum withdrawal
        print("\n" + "=" * 60)
        print("STEP 5: Withdrawing Earnings")
        print("=" * 60)

        print(f"\nWithdrawing ${status['available_balance']:.2f} USDC...")

        withdraw_result = await withdraw_earnings(client, executor_id)

        print("\nWithdrawal successful!")
        print(f"  Amount: ${withdraw_result['amount_usdc']:.2f}")
        print(f"  Gas fee: ${withdraw_result['gas_used']:.2f}")
        print(f"  Net amount: ${withdraw_result['net_amount']:.2f}")
        print(f"  Network: {withdraw_result['network']}")
        print(f"  Transaction: {withdraw_result['tx_hash'][:20]}...")
        print(f"  Estimated arrival: {withdraw_result['estimated_arrival']}")
    else:
        print("\n[Balance below $5.00 minimum withdrawal threshold]")

    print("\n" + "=" * 60)
    print("Workflow complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
