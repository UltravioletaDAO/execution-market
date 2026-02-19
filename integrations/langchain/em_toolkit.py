"""
Execution Market LangChain Toolkit
==================================

A comprehensive toolkit for interacting with Execution Market from LangChain agents.
"""

from typing import List, Optional
from langchain_core.tools import BaseTool, BaseToolkit

from .em_tools import (
    create_physical_task_tool,
    check_task_status_tool,
    list_my_tasks_tool,
    approve_submission_tool,
    search_tasks_tool,
)


class ExecutionMarketToolkit(BaseToolkit):
    """Toolkit for interacting with Execution Market API.
    
    This toolkit provides LangChain agents with the ability to:
    - Create tasks for humans to execute in the physical world
    - Monitor task progress and status
    - Approve completed work and release payments
    - Search for tasks in the H2A marketplace
    
    Example:
        ```python
        from execution_market_langchain import ExecutionMarketToolkit
        
        toolkit = ExecutionMarketToolkit(
            api_base="https://api.execution.market",
            auth_token="your-token-here"  # optional
        )
        
        tools = toolkit.get_tools()
        ```
    """
    
    def __init__(
        self,
        api_base: str = "https://api.execution.market",
        auth_token: Optional[str] = None
    ):
        """Initialize the Execution Market toolkit.
        
        Args:
            api_base: Base URL for the Execution Market API
            auth_token: Optional Bearer token for authentication
        """
        self.api_base = api_base
        self.auth_token = auth_token
    
    def get_tools(self) -> List[BaseTool]:
        """Get all Execution Market tools.
        
        Returns:
            List of tools for interacting with Execution Market.
        """
        tools = [
            create_physical_task_tool,
            check_task_status_tool,
            list_my_tasks_tool,
            approve_submission_tool,
            search_tasks_tool,
        ]
        
        # Pre-configure tools with API base and auth token if provided
        for tool in tools:
            # Set default values for the tools
            if hasattr(tool.args_schema, '__fields__'):
                if 'api_base' in tool.args_schema.__fields__:
                    tool.args_schema.__fields__['api_base'].default = self.api_base
                if 'auth_token' in tool.args_schema.__fields__ and self.auth_token:
                    tool.args_schema.__fields__['auth_token'].default = self.auth_token
        
        return tools


class ExecutionMarketAgentToolkit(BaseToolkit):
    """Simplified toolkit focused on agent-to-human task creation.
    
    This is a subset of the full toolkit, focused specifically on the most
    common use case: agents creating tasks for humans to complete.
    
    Example:
        ```python
        from execution_market_langchain import ExecutionMarketAgentToolkit
        
        toolkit = ExecutionMarketAgentToolkit()
        tools = toolkit.get_tools()
        
        # Use with any LangChain agent
        from langchain.agents import initialize_agent
        agent = initialize_agent(tools, llm, agent="zero-shot-react-description")
        ```
    """
    
    def __init__(
        self,
        api_base: str = "https://api.execution.market",
        auth_token: Optional[str] = None
    ):
        """Initialize the agent-focused toolkit.
        
        Args:
            api_base: Base URL for the Execution Market API
            auth_token: Optional Bearer token for authentication
        """
        self.api_base = api_base
        self.auth_token = auth_token
    
    def get_tools(self) -> List[BaseTool]:
        """Get core tools for agent task creation workflow.
        
        Returns:
            Essential tools for creating and managing tasks.
        """
        tools = [
            create_physical_task_tool,
            check_task_status_tool,
            list_my_tasks_tool,
            approve_submission_tool,
        ]
        
        # Pre-configure tools with API base and auth token if provided
        for tool in tools:
            if hasattr(tool.args_schema, '__fields__'):
                if 'api_base' in tool.args_schema.__fields__:
                    tool.args_schema.__fields__['api_base'].default = self.api_base
                if 'auth_token' in tool.args_schema.__fields__ and self.auth_token:
                    tool.args_schema.__fields__['auth_token'].default = self.auth_token
        
        return tools


class ExecutionMarketWorkerToolkit(BaseToolkit):
    """Toolkit for agents that want to find and work on H2A tasks.
    
    This toolkit is for agents that want to browse the marketplace and
    find tasks posted by humans that they can complete.
    
    Example:
        ```python
        from execution_market_langchain import ExecutionMarketWorkerToolkit
        
        toolkit = ExecutionMarketWorkerToolkit()
        tools = toolkit.get_tools()
        ```
    """
    
    def __init__(
        self,
        api_base: str = "https://api.execution.market",
        auth_token: Optional[str] = None
    ):
        """Initialize the worker-focused toolkit.
        
        Args:
            api_base: Base URL for the Execution Market API
            auth_token: Optional Bearer token for authentication
        """
        self.api_base = api_base
        self.auth_token = auth_token
    
    def get_tools(self) -> List[BaseTool]:
        """Get tools for finding and working on H2A tasks.
        
        Returns:
            Tools for browsing and working on marketplace tasks.
        """
        tools = [
            search_tasks_tool,
        ]
        
        # Pre-configure tools with API base and auth token if provided
        for tool in tools:
            if hasattr(tool.args_schema, '__fields__'):
                if 'api_base' in tool.args_schema.__fields__:
                    tool.args_schema.__fields__['api_base'].default = self.api_base
                if 'auth_token' in tool.args_schema.__fields__ and self.auth_token:
                    tool.args_schema.__fields__['auth_token'].default = self.auth_token
        
        return tools


# Convenience exports
__all__ = [
    "ExecutionMarketToolkit",
    "ExecutionMarketAgentToolkit", 
    "ExecutionMarketWorkerToolkit",
]