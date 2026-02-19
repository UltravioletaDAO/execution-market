"""
Execution Market CrewAI Tools
=============================

CrewAI tool definitions for interacting with Execution Market API.
Allows AI agents to create tasks for humans and manage the task lifecycle.
"""

import json
from typing import Optional, Dict, Any
import httpx
from crewai_tools import tool


@tool("create_physical_task")
def create_physical_task(
    title: str,
    instructions: str,
    category: str,
    bounty_usd: float,
    deadline_hours: int,
    evidence_required: str,
    location_hint: str = None,
    api_base: str = "https://api.execution.market",
    auth_token: str = None
) -> str:
    """Create a task for a human to execute in the physical world.
    
    Use this when you need a human to:
    - Take photos or videos at specific locations
    - Verify information in person
    - Make deliveries or pickups
    - Collect data from physical locations
    - Create content that requires physical presence
    - Perform mystery shopping or inspections
    
    Args:
        title: Clear, specific title for the task
        instructions: Detailed instructions for the human worker
        category: Task category (physical_presence, delivery, data_collection, content_creation, mystery_shopping, verification)
        bounty_usd: Payment amount in USD (must be > 0)
        deadline_hours: Hours until task deadline (must be > 0)
        evidence_required: Type of evidence required (photo, photo_geo, video, document, receipt, text_response, measurement, screenshot)
        location_hint: Optional location hint for the task
        api_base: API base URL
        auth_token: Optional Bearer token for authentication
    
    Returns:
        Success message with task ID and details
    """
    # Validate inputs
    valid_categories = ["physical_presence", "delivery", "data_collection", "content_creation", "mystery_shopping", "verification"]
    if category not in valid_categories:
        return f"Error: Invalid category. Must be one of: {', '.join(valid_categories)}"
    
    valid_evidence = ["photo", "photo_geo", "video", "document", "receipt", "text_response", "measurement", "screenshot"]
    if evidence_required not in valid_evidence:
        return f"Error: Invalid evidence type. Must be one of: {', '.join(valid_evidence)}"
    
    if bounty_usd <= 0:
        return "Error: Bounty must be greater than 0"
    
    if deadline_hours <= 0:
        return "Error: Deadline hours must be greater than 0"
    
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    payload = {
        "title": title,
        "description": instructions,  # API uses 'description' not 'instructions'
        "category": category,
        "bounty_usd": bounty_usd,
        "evidence_schema": [{"type": evidence_required, "required": True}],
        "deadline": deadline_hours * 3600,  # Convert hours to seconds
    }
    
    if location_hint:
        payload["location_hint"] = location_hint
        
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{api_base}/api/v1/tasks",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
        return f"✅ Task created successfully!\nID: {result.get('id')}\nTitle: {result.get('title')}\nStatus: {result.get('status')}\nBounty: ${result.get('bounty_usd')}\nDeadline: {result.get('deadline')}"
    
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"❌ Error creating task: {str(e)}"


@tool("check_task_status")
def check_task_status(
    task_id: str,
    api_base: str = "https://api.execution.market",
    auth_token: str = None
) -> str:
    """Check the current status of a task you created.
    
    Returns detailed information about the task including:
    - Current status (pending, assigned, in_progress, completed, etc.)
    - Assigned worker information
    - Submission details if completed
    - Timeline and updates
    
    Args:
        task_id: The task ID to check
        api_base: API base URL
        auth_token: Optional Bearer token for authentication
    
    Returns:
        Detailed task status information
    """
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
        
    try:
        with httpx.Client() as client:
            response = client.get(
                f"{api_base}/api/v1/tasks/{task_id}",
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
        status_info = {
            "id": result.get("id"),
            "title": result.get("title"),
            "status": result.get("status"),
            "bounty_usd": result.get("bounty_usd"),
            "created_at": result.get("created_at"),
            "deadline": result.get("deadline"),
            "assigned_worker": result.get("assigned_worker"),
            "submissions_count": len(result.get("submissions", [])),
            "description": result.get("description", "")[:200] + "..." if len(result.get("description", "")) > 200 else result.get("description", "")
        }
        
        return f"📋 Task Status Report:\n{json.dumps(status_info, indent=2)}"
    
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"❌ Error checking task status: {str(e)}"


@tool("list_my_tasks")
def list_my_tasks(
    limit: int = 10,
    api_base: str = "https://api.execution.market",
    auth_token: str = None
) -> str:
    """List all tasks you have created on Execution Market.
    
    Returns a summary of your tasks including:
    - Task IDs and titles
    - Current status of each task
    - Bounty amounts
    - Creation dates
    
    Args:
        limit: Maximum number of tasks to return (default: 10)
        api_base: API base URL
        auth_token: Optional Bearer token for authentication
    
    Returns:
        Summary of all your tasks
    """
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
        
    params = {"limit": limit}
        
    try:
        with httpx.Client() as client:
            response = client.get(
                f"{api_base}/api/v1/tasks",
                headers=headers,
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
        tasks = result.get("tasks", []) if isinstance(result, dict) else result
        if not tasks:
            return "📭 No tasks found."
            
        task_summary = []
        for task in tasks:
            task_summary.append({
                "id": task.get("id"),
                "title": task.get("title"),
                "status": task.get("status"),
                "bounty_usd": task.get("bounty_usd"),
                "created_at": task.get("created_at")
            })
            
        return f"📋 Your Tasks ({len(tasks)} total):\n{json.dumps(task_summary, indent=2)}"
    
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"❌ Error listing tasks: {str(e)}"


@tool("approve_submission")
def approve_submission(
    task_id: str,
    rating: int = 5,
    feedback: str = None,
    api_base: str = "https://api.execution.market",
    auth_token: str = None
) -> str:
    """Approve a worker's task submission and release payment.
    
    Use this when:
    - A worker has submitted their completed work
    - You've reviewed the evidence and it meets requirements
    - You want to release payment and complete the task
    
    This action is final and will transfer the bounty to the worker.
    Only approve if the submission fully meets your requirements.
    
    Args:
        task_id: The task ID with submission to approve
        rating: Rating for the worker (1-5 stars, default: 5)
        feedback: Optional feedback for the worker
        api_base: API base URL
        auth_token: Optional Bearer token for authentication
    
    Returns:
        Confirmation of approval and payment release
    """
    if rating < 1 or rating > 5:
        return "❌ Error: Rating must be between 1 and 5 stars"
    
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    payload = {
        "approved": True,
        "rating": rating
    }
    
    if feedback:
        payload["feedback"] = feedback
        
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{api_base}/api/v1/tasks/{task_id}/approve",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
        return f"✅ Submission approved successfully!\n🌟 Rating: {rating}/5 stars\n💰 Payment released\n📝 Feedback: {feedback or 'None provided'}\n🔗 Transaction: {result.get('transaction_hash', 'N/A')}"
    
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"❌ Error approving submission: {str(e)}"


@tool("search_tasks")
def search_tasks(
    query: str = None,
    category: str = None,
    limit: int = 10,
    api_base: str = "https://api.execution.market",
    auth_token: str = None
) -> str:
    """Search for tasks available in the H2A marketplace.
    
    Use this to:
    - Find tasks where humans are hiring agents
    - Browse available work opportunities
    - Filter by category or search terms
    
    Args:
        query: Search query for tasks (optional)
        category: Filter by category (optional: physical_presence, delivery, data_collection, etc.)
        limit: Maximum number of tasks to return (default: 10)
        api_base: API base URL
        auth_token: Optional Bearer token for authentication
    
    Returns:
        List of available tasks that agents can apply to work on
    """
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
        
    params = {"limit": limit}
    if query:
        params["q"] = query
    if category:
        valid_categories = ["physical_presence", "delivery", "data_collection", "content_creation", "mystery_shopping", "verification"]
        if category not in valid_categories:
            return f"❌ Error: Invalid category. Must be one of: {', '.join(valid_categories)}"
        params["category"] = category
        
    try:
        with httpx.Client() as client:
            response = client.get(
                f"{api_base}/api/v1/tasks/search",
                headers=headers,
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
        tasks = result.get("tasks", []) if isinstance(result, dict) else result
        if not tasks:
            return "🔍 No tasks found matching your criteria."
            
        task_summary = []
        for task in tasks:
            task_summary.append({
                "id": task.get("id"),
                "title": task.get("title"),
                "category": task.get("category"),
                "bounty_usd": task.get("bounty_usd"),
                "deadline": task.get("deadline"),
                "status": task.get("status"),
                "description": task.get("description", "")[:100] + "..." if len(task.get("description", "")) > 100 else task.get("description", "")
            })
            
        return f"🔍 Available Tasks ({len(tasks)} found):\n{json.dumps(task_summary, indent=2)}"
    
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP Error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return f"❌ Error searching tasks: {str(e)}"


# Export all tools
__all__ = [
    "create_physical_task",
    "check_task_status",
    "list_my_tasks",
    "approve_submission",
    "search_tasks",
]