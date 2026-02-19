"""
Multi-agent orchestration for Execution Market using OpenAI Agents SDK handoffs

Demonstrates coordination patterns between TaskManager, Worker, and QA agents
for complete task lifecycle management.
"""

from typing import Optional, Dict, Any, List
from openai import OpenAI
from openai_agents import Agent, Swarm
from .em_agent import TaskManagerAgent, WorkerAgent, QAAgent

class ExecutionMarketSwarm:
    """
    Orchestrates multiple specialized agents to handle complete task lifecycles.
    
    Workflow:
    1. TaskManager creates and monitors tasks
    2. WorkerAgent searches for and evaluates opportunities  
    3. QAAgent reviews submissions and provides quality control
    
    Handoff patterns demonstrate how agents can collaborate and transfer
    context between specialized roles.
    """
    
    def __init__(self, model: Optional[OpenAI] = None):
        self.model = model or OpenAI()
        self.swarm = Swarm(client=self.model)
        
        # Initialize specialized agents
        self.task_manager = TaskManagerAgent(model=self.model)
        self.worker_agent = WorkerAgent(model=self.model)
        self.qa_agent = QAAgent(model=self.model)
        
        # Configure handoff functions
        self._setup_handoffs()
    
    def _setup_handoffs(self):
        """Configure handoff patterns between agents"""
        
        def handoff_to_worker_agent():
            """Handoff from TaskManager to WorkerAgent for task search/evaluation"""
            return {
                "agent": self.worker_agent,
                "context": "Task created. Now searching for similar opportunities and evaluating market conditions."
            }
        
        def handoff_to_task_manager():
            """Handoff back to TaskManager from any agent"""
            return {
                "agent": self.task_manager,
                "context": "Returning to TaskManager for task creation or management."
            }
        
        def handoff_to_qa_agent():
            """Handoff to QAAgent for submission review"""
            return {
                "agent": self.qa_agent,
                "context": "Task has submissions ready for review. Proceeding with quality assessment."
            }
        
        # Add handoff functions to agents
        self.task_manager.functions.extend([
            handoff_to_worker_agent,
            handoff_to_qa_agent
        ])
        
        self.worker_agent.functions.extend([
            handoff_to_task_manager,
            handoff_to_qa_agent
        ])
        
        self.qa_agent.functions.extend([
            handoff_to_task_manager,
            handoff_to_worker_agent
        ])
    
    def create_and_manage_task(self, task_request: str) -> Dict[str, Any]:
        """
        Complete task creation workflow with agent coordination.
        
        Args:
            task_request: Natural language description of the task needed
            
        Returns:
            Dict containing task details and workflow results
        """
        
        # Start with TaskManager
        messages = [{"role": "user", "content": f"""
        I need help creating a physical verification task: {task_request}
        
        Please:
        1. Create an appropriate task with proper requirements and bounty
        2. Then handoff to the WorkerAgent to evaluate the task from a worker's perspective
        3. Monitor the task and be ready to handle any submissions
        
        Focus on creating a clear, achievable task that will attract quality workers.
        """}]
        
        try:
            response = self.swarm.run(
                agent=self.task_manager,
                messages=messages,
                max_turns=5
            )
            
            return {
                "success": True,
                "workflow": "create_and_manage_task",
                "final_agent": response.agent.name if hasattr(response.agent, 'name') else "TaskManager",
                "messages": response.messages,
                "context_transfers": getattr(response, 'context_transfers', [])
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "workflow": "create_and_manage_task"
            }
    
    def find_and_evaluate_opportunities(self, search_criteria: str) -> Dict[str, Any]:
        """
        Worker-focused workflow for finding and evaluating tasks.
        
        Args:
            search_criteria: Description of what type of tasks to look for
            
        Returns:
            Dict containing search results and evaluations
        """
        
        messages = [{"role": "user", "content": f"""
        I'm looking for task opportunities with these criteria: {search_criteria}
        
        Please:
        1. Search for relevant tasks on the platform
        2. Evaluate the best opportunities based on bounty, feasibility, and requirements
        3. If there are tasks ready for review, handoff to QA for assessment
        
        Focus on finding profitable tasks that are achievable for human workers.
        """}]
        
        try:
            response = self.swarm.run(
                agent=self.worker_agent,
                messages=messages,
                max_turns=4
            )
            
            return {
                "success": True,
                "workflow": "find_and_evaluate_opportunities", 
                "final_agent": response.agent.name if hasattr(response.agent, 'name') else "WorkerAgent",
                "messages": response.messages,
                "context_transfers": getattr(response, 'context_transfers', [])
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "workflow": "find_and_evaluate_opportunities"
            }
    
    def review_and_approve_submissions(self, task_ids: List[str]) -> Dict[str, Any]:
        """
        QA-focused workflow for reviewing task submissions.
        
        Args:
            task_ids: List of task IDs that need review
            
        Returns:
            Dict containing review results and decisions
        """
        
        task_list = ", ".join(task_ids)
        messages = [{"role": "user", "content": f"""
        I need to review submissions for these tasks: {task_list}
        
        Please:
        1. Check the status and submissions for each task
        2. Review evidence quality and requirement compliance
        3. Make approval/rejection decisions with appropriate ratings and feedback
        4. If you need to create follow-up tasks, handoff to TaskManager
        
        Focus on maintaining quality standards while being fair to workers.
        """}]
        
        try:
            response = self.swarm.run(
                agent=self.qa_agent,
                messages=messages,
                max_turns=6
            )
            
            return {
                "success": True,
                "workflow": "review_and_approve_submissions",
                "final_agent": response.agent.name if hasattr(response.agent, 'name') else "QAAgent", 
                "messages": response.messages,
                "context_transfers": getattr(response, 'context_transfers', [])
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "workflow": "review_and_approve_submissions"
            }
    
    def full_lifecycle_demo(self, initial_request: str) -> Dict[str, Any]:
        """
        Demonstrate a complete task lifecycle with all three agents.
        
        Shows handoff patterns and collaboration between:
        - TaskManager: Creates task
        - WorkerAgent: Evaluates and searches for similar tasks  
        - QAAgent: Handles quality review (simulated)
        
        Args:
            initial_request: Description of the task to create and manage
            
        Returns:
            Dict containing complete workflow results
        """
        
        messages = [{"role": "user", "content": f"""
        Let's demonstrate a complete task lifecycle: {initial_request}
        
        Workflow:
        1. TaskManager: Create the task with proper specifications
        2. WorkerAgent: Evaluate this task type and search for similar opportunities
        3. QAAgent: Review standards and provide quality guidance
        4. TaskManager: Final monitoring and management
        
        Show how agents can handoff context and collaborate effectively.
        Each agent should use their specialized knowledge and tools.
        """}]
        
        try:
            response = self.swarm.run(
                agent=self.task_manager,  # Start with task creation
                messages=messages,
                max_turns=8  # Allow for multiple handoffs
            )
            
            return {
                "success": True,
                "workflow": "full_lifecycle_demo",
                "final_agent": response.agent.name if hasattr(response.agent, 'name') else "TaskManager",
                "messages": response.messages,
                "context_transfers": getattr(response, 'context_transfers', []),
                "demo_complete": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "workflow": "full_lifecycle_demo"
            }

# Convenience functions for quick swarm creation

def create_execution_market_swarm(model: Optional[OpenAI] = None) -> ExecutionMarketSwarm:
    """Create a new ExecutionMarketSwarm instance"""
    return ExecutionMarketSwarm(model=model)

def quick_task_creation(task_description: str, model: Optional[OpenAI] = None) -> Dict[str, Any]:
    """
    Quick utility for creating a task with agent coordination.
    
    Args:
        task_description: What task needs to be created
        model: OpenAI model to use
        
    Returns:
        Task creation results
    """
    swarm = ExecutionMarketSwarm(model=model)
    return swarm.create_and_manage_task(task_description)

def quick_opportunity_search(search_criteria: str, model: Optional[OpenAI] = None) -> Dict[str, Any]:
    """
    Quick utility for searching task opportunities.
    
    Args:
        search_criteria: What to search for
        model: OpenAI model to use
        
    Returns:
        Search and evaluation results
    """
    swarm = ExecutionMarketSwarm(model=model)
    return swarm.find_and_evaluate_opportunities(search_criteria)

def quick_submission_review(task_ids: List[str], model: Optional[OpenAI] = None) -> Dict[str, Any]:
    """
    Quick utility for reviewing submissions.
    
    Args:
        task_ids: Tasks to review
        model: OpenAI model to use
        
    Returns:
        Review results
    """
    swarm = ExecutionMarketSwarm(model=model)
    return swarm.review_and_approve_submissions(task_ids)

__all__ = [
    "ExecutionMarketSwarm",
    "create_execution_market_swarm", 
    "quick_task_creation",
    "quick_opportunity_search",
    "quick_submission_review"
]