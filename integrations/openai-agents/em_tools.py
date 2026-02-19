"""
Execution Market tools for OpenAI Agents SDK

Provides function tools to interact with the Execution Market API:
- Create physical verification tasks
- Check task status and submissions
- List and search tasks
- Approve task submissions

Usage:
    from em_tools import create_physical_task, check_task_status
    from openai import OpenAI
    from openai_agents import Agent

    agent = Agent(
        model=OpenAI(),
        functions=[create_physical_task, check_task_status]
    )
"""

import os
import json
from typing import Optional, List, Literal
from decimal import Decimal
import requests
from pydantic import BaseModel, Field
from openai_agents import function_tool

# Evidence types supported by Execution Market
EvidenceType = Literal[
    "photo", "photo_geo", "video", "document", "receipt", 
    "text_response", "screenshot", "measurement"
]

# Task status enum
TaskStatus = Literal[
    "open", "assigned", "submitted", "approved", "rejected", "cancelled"
]

# Base API configuration
EM_API_BASE = "https://api.execution.market"
EM_API_KEY = os.getenv("EM_API_KEY")

def get_headers():
    """Get headers for Execution Market API requests"""
    if not EM_API_KEY:
        raise ValueError("EM_API_KEY environment variable is required")
    return {
        "X-API-Key": EM_API_KEY,
        "Content-Type": "application/json"
    }

class TaskInput(BaseModel):
    """Input model for creating a physical task"""
    title: str = Field(..., description="Clear, specific task title")
    description: str = Field(..., description="Detailed task description and requirements")
    bounty: Decimal = Field(..., description="Task bounty in USD (minimum $0.01)")
    deadline_hours: Optional[int] = Field(24, description="Hours until task deadline")
    evidence_type: EvidenceType = Field("photo", description="Type of evidence required")
    location_required: Optional[str] = Field(None, description="Required location (address or coordinates)")
    escrow_tx: Optional[str] = Field(None, description="Blockchain transaction hash for escrow")

class TaskSearchInput(BaseModel):
    """Input model for searching tasks"""
    query: Optional[str] = Field(None, description="Search query for task title/description")
    status: Optional[TaskStatus] = Field(None, description="Filter by task status")
    min_bounty: Optional[Decimal] = Field(None, description="Minimum bounty amount")
    max_bounty: Optional[Decimal] = Field(None, description="Maximum bounty amount")
    limit: int = Field(10, description="Maximum number of results")

class ApprovalInput(BaseModel):
    """Input model for approving task submissions"""
    task_id: str = Field(..., description="Task ID to approve")
    rating: int = Field(..., description="Rating for the worker (1-5)")
    feedback: Optional[str] = Field(None, description="Optional feedback for the worker")

@function_tool
def create_physical_task(input_data: TaskInput) -> dict:
    """
    Create a new physical verification task on Execution Market.
    
    This tool allows agents to post tasks that require human completion
    in the physical world, such as taking photos, visiting locations,
    or gathering information.
    
    Args:
        input_data: Task details including title, description, bounty, and requirements
        
    Returns:
        dict: Created task details including task_id, status, and public URL
        
    Example:
        create_physical_task(TaskInput(
            title="Verify restaurant is open",
            description="Visit McDonald's at 123 Main St and take a photo of the storefront showing current hours",
            bounty=Decimal("2.50"),
            evidence_type="photo",
            location_required="123 Main St, Anytown USA"
        ))
    """
    try:
        payload = {
            "title": input_data.title,
            "description": input_data.description,
            "bounty": str(input_data.bounty),
            "deadline_hours": input_data.deadline_hours,
            "evidence_type": input_data.evidence_type,
            "location_required": input_data.location_required,
            "escrow_tx": input_data.escrow_tx
        }
        
        response = requests.post(
            f"{EM_API_BASE}/api/v1/tasks",
            headers=get_headers(),
            json=payload
        )
        
        response.raise_for_status()
        task = response.json()
        
        return {
            "success": True,
            "task_id": task.get("id"),
            "status": task.get("status"),
            "url": f"https://execution.market/tasks/{task.get('id')}",
            "created_at": task.get("created_at"),
            "task": task
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"API request failed: {str(e)}",
            "response": getattr(e.response, 'text', None) if hasattr(e, 'response') else None
        }

@function_tool
def check_task_status(task_id: str) -> dict:
    """
    Check the status and details of a specific task.
    
    Retrieves current task information including status, submissions,
    worker assignments, and any evidence that has been provided.
    
    Args:
        task_id: The unique task ID to check
        
    Returns:
        dict: Task details including status, submissions, and worker info
    """
    try:
        response = requests.get(
            f"{EM_API_BASE}/api/v1/tasks/{task_id}",
            headers=get_headers()
        )
        
        response.raise_for_status()
        task = response.json()
        
        return {
            "success": True,
            "task_id": task_id,
            "status": task.get("status"),
            "title": task.get("title"),
            "bounty": task.get("bounty"),
            "worker_id": task.get("worker_id"),
            "submission": task.get("submission"),
            "evidence_url": task.get("evidence_url"),
            "submitted_at": task.get("submitted_at"),
            "task": task
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"API request failed: {str(e)}",
            "response": getattr(e.response, 'text', None) if hasattr(e, 'response') else None
        }

@function_tool
def list_my_tasks(status: Optional[TaskStatus] = None, limit: int = 10) -> dict:
    """
    List tasks created by this agent.
    
    Retrieves a list of tasks that were created using this API key,
    optionally filtered by status.
    
    Args:
        status: Optional status filter (open, assigned, submitted, approved, etc.)
        limit: Maximum number of tasks to return
        
    Returns:
        dict: List of tasks with their current status and details
    """
    try:
        params = {"limit": limit}
        if status:
            params["status"] = status
            
        response = requests.get(
            f"{EM_API_BASE}/api/v1/tasks",
            headers=get_headers(),
            params=params
        )
        
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "count": len(data.get("tasks", [])),
            "tasks": data.get("tasks", []),
            "total": data.get("total", 0)
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"API request failed: {str(e)}",
            "response": getattr(e.response, 'text', None) if hasattr(e, 'response') else None
        }

@function_tool
def search_tasks(input_data: TaskSearchInput) -> dict:
    """
    Search for available tasks on the platform.
    
    Find tasks that match specific criteria, useful for worker agents
    looking for tasks to complete or for market research.
    
    Args:
        input_data: Search criteria including query, status, and bounty filters
        
    Returns:
        dict: List of matching tasks
    """
    try:
        params = {"limit": input_data.limit}
        
        if input_data.query:
            params["q"] = input_data.query
        if input_data.status:
            params["status"] = input_data.status
        if input_data.min_bounty:
            params["min_bounty"] = str(input_data.min_bounty)
        if input_data.max_bounty:
            params["max_bounty"] = str(input_data.max_bounty)
            
        response = requests.get(
            f"{EM_API_BASE}/api/v1/tasks/search",
            headers=get_headers(),
            params=params
        )
        
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "count": len(data.get("tasks", [])),
            "tasks": data.get("tasks", []),
            "query": input_data.query,
            "filters_applied": {
                "status": input_data.status,
                "min_bounty": input_data.min_bounty,
                "max_bounty": input_data.max_bounty
            }
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"API request failed: {str(e)}",
            "response": getattr(e.response, 'text', None) if hasattr(e, 'response') else None
        }

@function_tool
def approve_submission(input_data: ApprovalInput) -> dict:
    """
    Approve a task submission and release payment to the worker.
    
    After reviewing evidence and submission quality, use this tool
    to approve the work and trigger payment release.
    
    Args:
        input_data: Approval details including task_id, rating, and feedback
        
    Returns:
        dict: Approval confirmation and payment details
    """
    try:
        payload = {
            "rating": input_data.rating,
            "feedback": input_data.feedback
        }
        
        response = requests.post(
            f"{EM_API_BASE}/api/v1/tasks/{input_data.task_id}/approve",
            headers=get_headers(),
            json=payload
        )
        
        response.raise_for_status()
        result = response.json()
        
        return {
            "success": True,
            "task_id": input_data.task_id,
            "approved": True,
            "rating_given": input_data.rating,
            "payment_status": result.get("payment_status"),
            "worker_id": result.get("worker_id"),
            "result": result
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"API request failed: {str(e)}",
            "response": getattr(e.response, 'text', None) if hasattr(e, 'response') else None
        }

# Export all tools for easy import
__all__ = [
    "create_physical_task",
    "check_task_status", 
    "list_my_tasks",
    "search_tasks",
    "approve_submission",
    "TaskInput",
    "TaskSearchInput", 
    "ApprovalInput",
    "EvidenceType",
    "TaskStatus"
]