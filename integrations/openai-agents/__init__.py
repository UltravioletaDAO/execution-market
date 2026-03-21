"""
Execution Market - OpenAI Agents SDK Integration

Transform physical world tasks into AI agent capabilities with specialized agents
for task creation, worker coordination, and quality assurance.

This integration provides:
- Function tools for the Execution Market API
- Pre-configured agent roles (TaskManager, Worker, QA)  
- Multi-agent coordination patterns through swarms
- Complete examples and documentation

Quick Start:
    from execution_market_agents import TaskManagerAgent
    from openai import OpenAI
    
    agent = TaskManagerAgent(model=OpenAI())
    
For full examples, see the examples/ directory.
"""

__version__ = "1.0.0"
__author__ = "Execution Market"
__email__ = "support@execution.market"
__license__ = "MIT"

# Import main classes and functions for easy access
from .em_tools import (
    create_physical_task,
    check_task_status,
    list_my_tasks,
    search_tasks,
    approve_submission,
    TaskInput,
    TaskSearchInput,
    ApprovalInput,
    EvidenceType,
    TaskStatus
)

from .em_agent import (
    TaskManagerAgent,
    WorkerAgent,
    QAAgent,
    create_task_manager,
    create_worker_agent,
    create_qa_agent,
    create_agent,
    AGENT_TYPES
)

from .em_swarm import (
    ExecutionMarketSwarm,
    create_execution_market_swarm,
    quick_task_creation,
    quick_opportunity_search,
    quick_submission_review
)

# Define what gets imported with "from execution_market_agents import *"
__all__ = [
    # Version info
    "__version__",
    "__author__", 
    "__email__",
    "__license__",
    
    # Tools
    "create_physical_task",
    "check_task_status",
    "list_my_tasks", 
    "search_tasks",
    "approve_submission",
    
    # Data models
    "TaskInput",
    "TaskSearchInput",
    "ApprovalInput",
    "EvidenceType", 
    "TaskStatus",
    
    # Agents
    "TaskManagerAgent",
    "WorkerAgent",
    "QAAgent",
    "create_task_manager",
    "create_worker_agent",
    "create_qa_agent",
    "create_agent",
    "AGENT_TYPES",
    
    # Swarm coordination
    "ExecutionMarketSwarm",
    "create_execution_market_swarm",
    "quick_task_creation",
    "quick_opportunity_search", 
    "quick_submission_review"
]

# Package metadata
PACKAGE_INFO = {
    "name": "execution-market-openai-agents",
    "version": __version__,
    "description": "OpenAI Agents SDK integration for Execution Market",
    "url": "https://execution.market",
    "api_docs": "https://api.execution.market/docs",
    "dashboard": "https://execution.market/dashboard"
}

def get_package_info():
    """Return package information dictionary"""
    return PACKAGE_INFO.copy()

def print_package_info():
    """Print package information for debugging"""
    print(f"Execution Market OpenAI Agents Integration v{__version__}")
    print(f"Author: {__author__} ({__email__})")
    print(f"License: {__license__}")
    print(f"Homepage: {PACKAGE_INFO['url']}")
    print(f"API Docs: {PACKAGE_INFO['api_docs']}")
    print(f"Dashboard: {PACKAGE_INFO['dashboard']}")

# Environment check helper
def check_environment():
    """
    Check if required environment variables are set.
    Returns dict with status and missing variables.
    """
    import os
    
    required_vars = ['EM_API_KEY', 'OPENAI_API_KEY']
    missing = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    return {
        'all_set': len(missing) == 0,
        'missing': missing,
        'required': required_vars
    }

def print_environment_status():
    """Print environment variable status"""
    status = check_environment()
    
    if status['all_set']:
        print("✅ Environment configured correctly")
    else:
        print("❌ Missing required environment variables:")
        for var in status['missing']:
            print(f"   - {var}")
        print()
        print("Set these variables:")
        if 'EM_API_KEY' in status['missing']:
            print("   export EM_API_KEY='your-key'  # Get from https://execution.market/dashboard")
        if 'OPENAI_API_KEY' in status['missing']:
            print("   export OPENAI_API_KEY='your-key'  # Get from https://platform.openai.com")

# Quick setup verification
def verify_setup():
    """
    Verify the integration is properly set up.
    Returns True if everything is working.
    """
    try:
        # Check environment
        env_status = check_environment()
        if not env_status['all_set']:
            print("❌ Environment variables not set")
            print_environment_status()
            return False
        
        # Try importing OpenAI
        try:
            from openai import OpenAI
            print("✅ OpenAI SDK available")
        except ImportError:
            print("❌ OpenAI SDK not installed (pip install openai)")
            return False
        
        # Try importing openai-agents  
        try:
            from openai_agents import Agent
            print("✅ OpenAI Agents SDK available")
        except ImportError:
            print("❌ OpenAI Agents SDK not installed (pip install openai-agents)")
            return False
        
        # Try creating a simple agent (without API calls)
        try:
            agent = TaskManagerAgent(model=None)  # Don't initialize model for test
            print("✅ Execution Market agents can be created")
        except Exception as e:
            print(f"❌ Agent creation failed: {e}")
            return False
        
        print("🎉 Integration setup verified successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Setup verification failed: {e}")
        return False