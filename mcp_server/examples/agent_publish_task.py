#!/usr/bin/env python3
"""
Example: Agent Publishing a Task

This example demonstrates how an AI agent can use the Execution Market MCP server
to publish a task for human execution, monitor its progress, and approve
the submission.

Requirements:
    pip install mcp aiohttp

Usage:
    python agent_publish_task.py
"""

import asyncio
import json
import os

# Simulated MCP client for demonstration
# In production, use the actual MCP client library


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
        if tool_name == "em_publish_task":
            return {
                "success": True,
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": params["title"],
                "bounty_usd": params["bounty_usd"],
                "status": "published",
                "deadline": "2026-01-26T10:30:00Z",
                "escrow_id": "esc_7f3c1d2e4a",
            }
        elif tool_name == "em_get_task":
            return {
                "id": params["task_id"],
                "title": "Verify coffee shop hours",
                "status": "submitted",  # Simulating a submitted task
                "bounty_usd": 10.00,
                "deadline": "2026-01-26T10:30:00Z",
            }
        elif tool_name == "em_check_submission":
            return {
                "submissions": [
                    {
                        "id": "7f3c1d2e-4a5b-6c7d-8e9f-0a1b2c3d4e5f",
                        "status": "pending",
                        "evidence": {
                            "photo_geo": {
                                "url": "ipfs://QmXyz123...",
                                "metadata": {
                                    "lat": 37.7749,
                                    "lng": -122.4194,
                                    "timestamp": "2026-01-25T14:30:00Z",
                                },
                            },
                            "text_response": "Shop is open. Hours: 7am-8pm daily.",
                        },
                        "executor": {
                            "id": "exec_xyz789",
                            "display_name": "Maria G.",
                            "reputation_score": 92,
                        },
                        "submitted_at": "2026-01-25T14:30:00Z",
                    }
                ]
            }
        elif tool_name == "em_approve_submission":
            return {
                "success": True,
                "verdict": params["verdict"],
                "payment_released": params["verdict"] == "accepted",
                "worker_payment": 8.70 if params["verdict"] == "accepted" else 0,
                "platform_fee": 1.30 if params["verdict"] == "accepted" else 0,
            }

        return {"error": f"Unknown tool: {tool_name}"}


async def publish_task(client: MockMCPClient, agent_id: str) -> dict:
    """
    Publish a new task for human execution.

    Args:
        client: MCP client instance
        agent_id: Your agent's identifier (wallet address or ERC-8004 ID)

    Returns:
        Task creation result
    """
    result = await client.call_tool(
        "em_publish_task",
        {
            "agent_id": agent_id,
            "title": "Verify coffee shop hours",
            "instructions": """
                Visit the coffee shop at 456 Oak Street, San Francisco.

                Please complete the following:
                1. Take a clear photo of the storefront showing the posted hours
                2. Confirm if the shop is currently open or closed
                3. Note any special notices or holiday hours

                The photo must include GPS metadata to verify location.
            """,
            "category": "physical_presence",
            "bounty_usd": 10.00,
            "deadline_hours": 24,
            "evidence_required": ["photo_geo", "text_response"],
            "evidence_optional": ["timestamp_proof"],
            "location_hint": "San Francisco, CA",
            "min_reputation": 50,
        },
    )

    return result


async def check_task_status(client: MockMCPClient, task_id: str, agent_id: str) -> dict:
    """
    Check the current status of a task and any submissions.

    Args:
        client: MCP client instance
        task_id: The task ID to check
        agent_id: Your agent's identifier

    Returns:
        Task status and submissions
    """
    # Get task status
    task = await client.call_tool(
        "em_get_task",
        {"task_id": task_id, "response_format": "json"},
    )

    # If submitted, check submissions
    if task.get("status") in ["submitted", "verifying"]:
        submissions = await client.call_tool(
            "em_check_submission",
            {
                "task_id": task_id,
                "agent_id": agent_id,
                "response_format": "json",
            },
        )
        task["submissions"] = submissions.get("submissions", [])

    return task


def analyze_evidence(evidence: dict) -> tuple[bool, str]:
    """
    Analyze submitted evidence.

    In a real implementation, this would use AI/ML to verify:
    - Photo quality and content
    - GPS coordinates match expected location
    - Timestamp is within acceptable range
    - Text response answers the required questions

    Args:
        evidence: The submitted evidence dictionary

    Returns:
        Tuple of (is_valid, reasoning)
    """
    # This is a simplified example. Real implementation would:
    # 1. Verify GPS coordinates are near target location
    # 2. Use vision AI to verify photo content
    # 3. Check timestamp is recent and within task window
    # 4. Validate text response contains required information

    photo_geo = evidence.get("photo_geo", {})
    text_response = evidence.get("text_response", "")

    # Check GPS coordinates
    metadata = photo_geo.get("metadata", {})
    lat = metadata.get("lat")
    lng = metadata.get("lng")

    if not lat or not lng:
        return False, "Missing GPS coordinates in photo"

    # Simplified location check (real implementation would calculate distance)
    # San Francisco approximate bounds
    if not (37.7 < lat < 37.8 and -122.5 < lng < -122.3):
        return False, "GPS coordinates are outside expected area"

    # Check text response
    if len(text_response) < 20:
        return False, "Text response is too brief"

    required_keywords = ["open", "hours"]
    if not any(keyword in text_response.lower() for keyword in required_keywords):
        return False, "Text response doesn't mention shop hours or status"

    return (
        True,
        "Evidence appears valid: GPS matches location, photo provided, hours reported",
    )


async def review_submission(
    client: MockMCPClient,
    submission_id: str,
    agent_id: str,
    evidence: dict,
) -> dict:
    """
    Review and approve/reject a submission.

    Args:
        client: MCP client instance
        submission_id: The submission ID
        agent_id: Your agent's identifier
        evidence: The submitted evidence to analyze

    Returns:
        Review result
    """
    # Analyze the evidence
    is_valid, reasoning = analyze_evidence(evidence)

    if is_valid:
        result = await client.call_tool(
            "em_approve_submission",
            {
                "submission_id": submission_id,
                "agent_id": agent_id,
                "verdict": "accepted",
                "notes": reasoning,
            },
        )
    else:
        result = await client.call_tool(
            "em_approve_submission",
            {
                "submission_id": submission_id,
                "agent_id": agent_id,
                "verdict": "more_info_requested",
                "notes": reasoning,
            },
        )

    return result


async def main():
    """
    Complete workflow example:
    1. Publish a task
    2. Wait for submission (simulated)
    3. Review and approve submission
    """
    # Configuration
    agent_id = os.environ.get("AGENT_ID", "0x1234567890abcdef1234567890abcdef12345678")

    # Initialize client
    client = MockMCPClient()
    await client.connect("https://api.execution.market/mcp")

    # Step 1: Publish a task
    print("\n" + "=" * 60)
    print("STEP 1: Publishing Task")
    print("=" * 60)

    task_result = await publish_task(client, agent_id)
    task_id = task_result["task_id"]

    print("\nTask published successfully!")
    print(f"  Task ID: {task_id}")
    print(f"  Bounty: ${task_result['bounty_usd']:.2f}")
    print(f"  Status: {task_result['status']}")
    print(f"  Escrow ID: {task_result['escrow_id']}")

    # Step 2: Check for submissions (in real app, use webhooks)
    print("\n" + "=" * 60)
    print("STEP 2: Checking Task Status")
    print("=" * 60)

    task_status = await check_task_status(client, task_id, agent_id)

    print(f"\nTask status: {task_status['status']}")

    if task_status.get("submissions"):
        print(f"Found {len(task_status['submissions'])} submission(s)")

        # Step 3: Review the submission
        print("\n" + "=" * 60)
        print("STEP 3: Reviewing Submission")
        print("=" * 60)

        submission = task_status["submissions"][0]
        print(f"\nSubmission ID: {submission['id']}")
        print(f"Executor: {submission['executor']['display_name']}")
        print(f"Reputation: {submission['executor']['reputation_score']}")
        print("\nEvidence submitted:")
        print(json.dumps(submission["evidence"], indent=2))

        # Review and approve
        review_result = await review_submission(
            client,
            submission["id"],
            agent_id,
            submission["evidence"],
        )

        print("\n" + "=" * 60)
        print("STEP 4: Review Result")
        print("=" * 60)

        print(f"\nVerdict: {review_result['verdict']}")
        if review_result.get("payment_released"):
            print("Payment released!")
            print(f"  Worker payment: ${review_result['worker_payment']:.2f}")
            print(f"  Platform fee: ${review_result['platform_fee']:.2f}")
    else:
        print("No submissions yet. Waiting for a worker to complete the task...")
        print("\nIn a real implementation, you would:")
        print("  1. Set up webhooks to receive submission notifications")
        print("  2. Or poll periodically with em_get_task")

    print("\n" + "=" * 60)
    print("Workflow complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
