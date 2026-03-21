"""
Execution Market LangChain Tools
===============================

LangChain tool definitions for interacting with Execution Market API.
Allows AI agents to create tasks for humans and manage the task lifecycle.
"""

import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone

import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, validator


class CreatePhysicalTaskInput(BaseModel):
    """Input for creating a physical task on Execution Market."""
    
    title: str = Field(description="Clear, specific title for the task")
    instructions: str = Field(description="Detailed instructions for the human worker")
    category: str = Field(
        description="Task category",
        regex="^(physical_presence|delivery|data_collection|content_creation|mystery_shopping|verification)$"
    )
    bounty_usd: float = Field(description="Payment amount in USD", gt=0)
    deadline_hours: int = Field(description="Hours until task deadline", gt=0)
    evidence_required: str = Field(
        description="Type of evidence required for completion",
        regex="^(photo|photo_geo|video|document|receipt|text_response|measurement|screenshot)$"
    )
    location_hint: Optional[str] = Field(
        default=None,
        description="Location hint for the task (optional)"
    )
    api_base: Optional[str] = Field(
        default="https://api.execution.market",
        description="API base URL"
    )
    auth_token: Optional[str] = Field(
        default=None,
        description="Bearer token for authentication (optional)"
    )


class TaskStatusInput(BaseModel):
    """Input for checking task status."""
    
    task_id: str = Field(description="The task ID to check")
    api_base: Optional[str] = Field(
        default="https://api.execution.market",
        description="API base URL"
    )
    auth_token: Optional[str] = Field(
        default=None,
        description="Bearer token for authentication (optional)"
    )


class ListTasksInput(BaseModel):
    """Input for listing tasks."""
    
    api_base: Optional[str] = Field(
        default="https://api.execution.market",
        description="API base URL"
    )
    auth_token: Optional[str] = Field(
        default=None,
        description="Bearer token for authentication (optional)"
    )
    limit: Optional[int] = Field(
        default=10,
        description="Maximum number of tasks to return"
    )


class ApproveSubmissionInput(BaseModel):
    """Input for approving a task submission."""
    
    submission_id: str = Field(description="The submission ID to approve")
    api_base: Optional[str] = Field(
        default="https://api.execution.market",
        description="API base URL"
    )
    auth_token: Optional[str] = Field(
        default=None,
        description="Bearer token for authentication (optional)"
    )


class SearchTasksInput(BaseModel):
    """Input for searching marketplace tasks."""
    
    query: Optional[str] = Field(
        default=None,
        description="Search query for tasks"
    )
    category: Optional[str] = Field(
        default=None,
        description="Filter by category",
        regex="^(physical_presence|delivery|data_collection|content_creation|mystery_shopping|verification)$"
    )
    api_base: Optional[str] = Field(
        default="https://api.execution.market",
        description="API base URL"
    )
    auth_token: Optional[str] = Field(
        default=None,
        description="Bearer token for authentication (optional)"
    )
    limit: Optional[int] = Field(
        default=10,
        description="Maximum number of tasks to return"
    )


class CreatePhysicalTaskTool(BaseTool):
    """Tool for creating physical tasks on Execution Market."""
    
    name = "create_physical_task"
    description = """Create a task for a human to execute in the physical world.
    
    Use this when you need a human to:
    - Take photos or videos at specific locations
    - Verify information in person
    - Make deliveries or pickups
    - Collect data from physical locations
    - Create content that requires physical presence
    - Perform mystery shopping or inspections
    
    Returns the created task with ID and status."""
    
    args_schema = CreatePhysicalTaskInput
    
    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        input_data = CreatePhysicalTaskInput(**kwargs)
        
        headers = {"Content-Type": "application/json"}
        if input_data.auth_token:
            headers["Authorization"] = f"Bearer {input_data.auth_token}"
        
        payload = {
            "title": input_data.title,
            "instructions": input_data.instructions,
            "category": input_data.category,
            "bounty_usd": input_data.bounty_usd,
            "deadline_hours": input_data.deadline_hours,
            "evidence_required": input_data.evidence_required,
        }
        
        if input_data.location_hint:
            payload["location_hint"] = input_data.location_hint
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{input_data.api_base}/api/v1/tasks",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
        return f"Task created successfully! ID: {result.get('id')}, Status: {result.get('status')}, Bounty: ${result.get('bounty_usd')}"


class CheckTaskStatusTool(BaseTool):
    """Tool for checking the status of a task."""
    
    name = "check_task_status"
    description = """Check the current status of a task you created.
    
    Returns detailed information about the task including:
    - Current status (pending, assigned, in_progress, completed, etc.)
    - Assigned worker information
    - Submission details if completed
    - Timeline and updates
    
    Use this to monitor task progress."""
    
    args_schema = TaskStatusInput
    
    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        input_data = TaskStatusInput(**kwargs)
        
        headers = {}
        if input_data.auth_token:
            headers["Authorization"] = f"Bearer {input_data.auth_token}"
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{input_data.api_base}/api/v1/tasks/{input_data.task_id}",
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
        status_info = {
            "id": result.get("id"),
            "title": result.get("title"),
            "status": result.get("status"),
            "bounty": result.get("bounty_usd"),
            "created": result.get("created_at"),
            "deadline": result.get("deadline"),
            "worker": result.get("assigned_worker"),
            "submissions": len(result.get("submissions", []))
        }
        
        return f"Task Status: {json.dumps(status_info, indent=2)}"


class ListMyTasksTool(BaseTool):
    """Tool for listing tasks created by this agent."""
    
    name = "list_my_tasks"
    description = """List all tasks you have created on Execution Market.
    
    Returns a summary of your tasks including:
    - Task IDs and titles
    - Current status of each task
    - Bounty amounts
    - Creation dates
    
    Use this to get an overview of all your active and completed tasks."""
    
    args_schema = ListTasksInput
    
    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        input_data = ListTasksInput(**kwargs)
        
        headers = {}
        if input_data.auth_token:
            headers["Authorization"] = f"Bearer {input_data.auth_token}"
            
        params = {}
        if input_data.limit:
            params["limit"] = input_data.limit
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{input_data.api_base}/api/v1/tasks",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            result = response.json()
            
        tasks = result.get("tasks", [])
        if not tasks:
            return "No tasks found."
            
        task_summary = []
        for task in tasks:
            task_summary.append({
                "id": task.get("id"),
                "title": task.get("title"),
                "status": task.get("status"),
                "bounty_usd": task.get("bounty_usd"),
                "created": task.get("created_at")
            })
            
        return f"Your Tasks ({len(tasks)} total):\n{json.dumps(task_summary, indent=2)}"


class ApproveSubmissionTool(BaseTool):
    """Tool for approving a worker's task submission and releasing payment."""
    
    name = "approve_submission"
    description = """Approve a worker's submission and release payment.
    
    Use this when:
    - A worker has submitted their completed work
    - You've reviewed the evidence and it meets requirements
    - You want to release payment and complete the task
    
    This action is final and will transfer the bounty to the worker.
    Only approve if the submission fully meets your requirements."""
    
    args_schema = ApproveSubmissionInput
    
    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        input_data = ApproveSubmissionInput(**kwargs)
        
        headers = {"Content-Type": "application/json"}
        if input_data.auth_token:
            headers["Authorization"] = f"Bearer {input_data.auth_token}"
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{input_data.api_base}/api/v1/submissions/{input_data.submission_id}/approve",
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
        return f"Submission approved! Payment released. Transaction: {result.get('transaction_hash', 'N/A')}"


class SearchTasksTool(BaseTool):
    """Tool for searching available tasks in the marketplace."""
    
    name = "search_tasks"
    description = """Search for tasks available in the H2A (Human-to-Agent) marketplace.
    
    Use this to:
    - Find tasks where humans are hiring agents
    - Browse available work opportunities
    - Filter by category or search terms
    
    Returns tasks that agents can apply to work on."""
    
    args_schema = SearchTasksInput
    
    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        input_data = SearchTasksInput(**kwargs)
        
        headers = {}
        if input_data.auth_token:
            headers["Authorization"] = f"Bearer {input_data.auth_token}"
            
        params = {}
        if input_data.query:
            params["q"] = input_data.query
        if input_data.category:
            params["category"] = input_data.category
        if input_data.limit:
            params["limit"] = input_data.limit
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{input_data.api_base}/api/v1/h2a/tasks",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            result = response.json()
            
        tasks = result.get("tasks", [])
        if not tasks:
            return "No tasks found matching your criteria."
            
        task_summary = []
        for task in tasks:
            task_summary.append({
                "id": task.get("id"),
                "title": task.get("title"),
                "category": task.get("category"),
                "bounty_usd": task.get("bounty_usd"),
                "deadline": task.get("deadline"),
                "description": task.get("description", "")[:100] + "..." if task.get("description", "") else ""
            })
            
        return f"Available Tasks ({len(tasks)} found):\n{json.dumps(task_summary, indent=2)}"


# Create tool instances
create_physical_task_tool = CreatePhysicalTaskTool()
check_task_status_tool = CheckTaskStatusTool()
list_my_tasks_tool = ListMyTasksTool()
approve_submission_tool = ApproveSubmissionTool()
search_tasks_tool = SearchTasksTool()

# Export all tools
__all__ = [
    "CreatePhysicalTaskTool",
    "CheckTaskStatusTool", 
    "ListMyTasksTool",
    "ApproveSubmissionTool",
    "SearchTasksTool",
    "create_physical_task_tool",
    "check_task_status_tool",
    "list_my_tasks_tool",
    "approve_submission_tool",
    "search_tasks_tool",
]