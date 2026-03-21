"""
Execution Market LangChain Integration
=====================================

LangChain tools and toolkits for interacting with Execution Market API.
Enables AI agents to create and manage real-world tasks performed by humans.

Quick Start:
    >>> from execution_market_langchain import ExecutionMarketToolkit
    >>> toolkit = ExecutionMarketToolkit()
    >>> tools = toolkit.get_tools()
    >>> # Use tools with any LangChain agent

Available Tools:
    - create_physical_task: Create tasks for humans
    - check_task_status: Monitor task progress  
    - list_my_tasks: View all your tasks
    - approve_submission: Approve completed work
    - search_tasks: Browse H2A marketplace

Available Toolkits:
    - ExecutionMarketToolkit: Full toolkit with all tools
    - ExecutionMarketAgentToolkit: Agent-focused (A2H tasks)
    - ExecutionMarketWorkerToolkit: Worker-focused (H2A tasks)
"""

from .em_tools import (
    CreatePhysicalTaskTool,
    CheckTaskStatusTool,
    ListMyTasksTool,
    ApproveSubmissionTool,
    SearchTasksTool,
    create_physical_task_tool,
    check_task_status_tool,
    list_my_tasks_tool,
    approve_submission_tool,
    search_tasks_tool,
)

from .em_toolkit import (
    ExecutionMarketToolkit,
    ExecutionMarketAgentToolkit,
    ExecutionMarketWorkerToolkit,
)

__version__ = "1.0.0"
__author__ = "Execution Market"
__email__ = "support@execution.market"

__all__ = [
    # Individual Tools
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
    
    # Toolkits
    "ExecutionMarketToolkit",
    "ExecutionMarketAgentToolkit",
    "ExecutionMarketWorkerToolkit",
]