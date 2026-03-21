"""
Execution Market CrewAI Crew Configurations
===========================================

Pre-built CrewAI crew configurations for common Execution Market workflows.
Each crew is designed for specific use cases and includes specialized agents.
"""

from crewai import Agent, Task, Crew
from crewai.process import Process
from typing import List, Optional, Dict, Any

from .em_tools import (
    create_physical_task,
    check_task_status, 
    list_my_tasks,
    approve_submission,
    search_tasks
)


class TaskManagerCrew:
    """
    A crew specialized in creating and managing physical tasks.
    
    This crew consists of agents that handle:
    - Task planning and creation
    - Requirements analysis
    - Task monitoring and status updates
    - Quality assurance for task specifications
    """
    
    def __init__(
        self, 
        api_base: str = "https://api.execution.market",
        auth_token: Optional[str] = None,
        llm=None
    ):
        """Initialize the Task Manager crew.
        
        Args:
            api_base: Execution Market API base URL
            auth_token: Optional authentication token
            llm: Language model to use for agents (optional)
        """
        self.api_base = api_base
        self.auth_token = auth_token
        self.llm = llm
        
        # Configure tools with API settings
        self.tools = [create_physical_task, check_task_status, list_my_tasks]
        
    def create_agents(self) -> List[Agent]:
        """Create specialized agents for task management."""
        
        task_planner = Agent(
            role="Task Planner",
            goal="Create well-structured, clear, and actionable tasks for human workers",
            backstory="""You are an expert at breaking down complex requirements into 
            clear, actionable tasks that humans can execute efficiently. You understand 
            what makes a good task: specific instructions, appropriate compensation, 
            realistic deadlines, and clear success criteria.""",
            tools=[create_physical_task],
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        task_monitor = Agent(
            role="Task Monitor", 
            goal="Track task progress and provide status updates",
            backstory="""You are responsible for monitoring active tasks and keeping 
            stakeholders informed about progress. You check task statuses, identify 
            potential issues, and provide clear status reports.""",
            tools=[check_task_status, list_my_tasks],
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        quality_controller = Agent(
            role="Quality Controller",
            goal="Ensure tasks meet quality standards before creation and during execution",
            backstory="""You are a quality assurance specialist who reviews task 
            specifications to ensure they are clear, fair, legal, and achievable. 
            You also review submissions to ensure they meet the original requirements.""",
            tools=[check_task_status, approve_submission],
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        return [task_planner, task_monitor, quality_controller]
    
    def create_crew(self) -> Crew:
        """Create the complete Task Manager crew."""
        agents = self.create_agents()
        
        return Crew(
            agents=agents,
            verbose=True,
            process=Process.sequential,
            share_crew=False
        )


class WorkerFinderCrew:
    """
    A crew specialized in finding and assigning tasks to workers.
    
    This crew handles:
    - Searching for available tasks in the marketplace
    - Analyzing task requirements and feasibility
    - Matching tasks with appropriate capabilities
    - Managing task assignments
    """
    
    def __init__(
        self,
        api_base: str = "https://api.execution.market", 
        auth_token: Optional[str] = None,
        llm=None
    ):
        """Initialize the Worker Finder crew.
        
        Args:
            api_base: Execution Market API base URL
            auth_token: Optional authentication token
            llm: Language model to use for agents (optional)
        """
        self.api_base = api_base
        self.auth_token = auth_token
        self.llm = llm
        
        self.tools = [search_tasks, check_task_status]
    
    def create_agents(self) -> List[Agent]:
        """Create specialized agents for finding and evaluating work opportunities."""
        
        task_scout = Agent(
            role="Task Scout",
            goal="Find and identify suitable task opportunities in the marketplace",
            backstory="""You are an expert at scanning the marketplace for tasks that 
            match specific criteria. You understand how to search effectively and 
            identify opportunities that align with capabilities and goals.""",
            tools=[search_tasks],
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        opportunity_analyzer = Agent(
            role="Opportunity Analyzer",
            goal="Analyze tasks for feasibility, profitability, and requirements",
            backstory="""You are skilled at evaluating task opportunities to determine 
            if they are worth pursuing. You consider factors like complexity, time 
            requirements, compensation, and success probability.""",
            tools=[search_tasks, check_task_status],
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        assignment_coordinator = Agent(
            role="Assignment Coordinator",
            goal="Coordinate task assignments and manage workflow",
            backstory="""You specialize in managing the assignment process, ensuring 
            that selected tasks are properly claimed and that workflow is optimized 
            for maximum efficiency and success.""",
            tools=[check_task_status],
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        return [task_scout, opportunity_analyzer, assignment_coordinator]
    
    def create_crew(self) -> Crew:
        """Create the complete Worker Finder crew."""
        agents = self.create_agents()
        
        return Crew(
            agents=agents,
            verbose=True,
            process=Process.sequential,
            share_crew=False
        )


class QualityAssuranceCrew:
    """
    A crew specialized in reviewing and approving task submissions.
    
    This crew handles:
    - Reviewing completed task submissions
    - Verifying evidence and compliance with requirements
    - Providing feedback to workers
    - Managing payment approvals
    """
    
    def __init__(
        self,
        api_base: str = "https://api.execution.market",
        auth_token: Optional[str] = None,
        llm=None
    ):
        """Initialize the Quality Assurance crew.
        
        Args:
            api_base: Execution Market API base URL
            auth_token: Optional authentication token
            llm: Language model to use for agents (optional)
        """
        self.api_base = api_base
        self.auth_token = auth_token
        self.llm = llm
        
        self.tools = [check_task_status, approve_submission, list_my_tasks]
    
    def create_agents(self) -> List[Agent]:
        """Create specialized agents for quality assurance and approval."""
        
        submission_reviewer = Agent(
            role="Submission Reviewer",
            goal="Thoroughly review task submissions for completeness and quality",
            backstory="""You are an expert at evaluating submitted work to ensure it 
            meets the original task requirements. You have a keen eye for detail and 
            understand what constitutes satisfactory completion of various task types.""",
            tools=[check_task_status],
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        evidence_validator = Agent(
            role="Evidence Validator", 
            goal="Validate evidence and documentation provided by workers",
            backstory="""You specialize in verifying that submitted evidence (photos, 
            documents, reports) is authentic, complete, and meets the specified 
            requirements. You understand different types of evidence and their standards.""",
            tools=[check_task_status],
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        payment_approver = Agent(
            role="Payment Approver",
            goal="Make final approval decisions and release payments to workers",
            backstory="""You are responsible for the final step in the quality 
            assurance process: deciding whether to approve submissions and release 
            payment. You balance quality standards with fairness to workers.""",
            tools=[approve_submission, check_task_status],
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
        
        return [submission_reviewer, evidence_validator, payment_approver]
    
    def create_crew(self) -> Crew:
        """Create the complete Quality Assurance crew."""
        agents = self.create_agents()
        
        return Crew(
            agents=agents,
            verbose=True,
            process=Process.sequential,
            share_crew=False
        )


class FullServiceCrew:
    """
    A comprehensive crew that combines all aspects of task management.
    
    This crew can handle the complete workflow:
    - Task creation and planning
    - Task monitoring and management
    - Finding marketplace opportunities
    - Quality assurance and approvals
    """
    
    def __init__(
        self,
        api_base: str = "https://api.execution.market",
        auth_token: Optional[str] = None,
        llm=None
    ):
        """Initialize the Full Service crew.
        
        Args:
            api_base: Execution Market API base URL
            auth_token: Optional authentication token
            llm: Language model to use for agents (optional)
        """
        self.api_base = api_base
        self.auth_token = auth_token
        self.llm = llm
        
        self.tools = [
            create_physical_task,
            check_task_status,
            list_my_tasks,
            approve_submission,
            search_tasks
        ]
    
    def create_agents(self) -> List[Agent]:
        """Create a comprehensive set of agents for full task lifecycle management."""
        
        task_manager = Agent(
            role="Task Manager",
            goal="Oversee complete task lifecycle from creation to completion",
            backstory="""You are a senior task management professional who coordinates 
            all aspects of task execution. You can create tasks, monitor progress, 
            find opportunities, and ensure quality standards are met.""",
            tools=self.tools,
            verbose=True,
            allow_delegation=True,
            llm=self.llm
        )
        
        operations_coordinator = Agent(
            role="Operations Coordinator",
            goal="Coordinate operations between task creation, monitoring, and approval",
            backstory="""You specialize in workflow coordination, ensuring smooth 
            operations across all phases of task management. You handle communication, 
            scheduling, and process optimization.""",
            tools=[check_task_status, list_my_tasks, search_tasks],
            verbose=True,
            allow_delegation=True,
            llm=self.llm
        )
        
        quality_supervisor = Agent(
            role="Quality Supervisor",
            goal="Supervise quality across all task management activities",
            backstory="""You are responsible for maintaining high quality standards 
            across all aspects of task management. You ensure tasks are well-designed, 
            properly executed, and fairly evaluated.""",
            tools=[check_task_status, approve_submission, list_my_tasks],
            verbose=True,
            allow_delegation=True,
            llm=self.llm
        )
        
        return [task_manager, operations_coordinator, quality_supervisor]
    
    def create_crew(self) -> Crew:
        """Create the complete Full Service crew."""
        agents = self.create_agents()
        
        return Crew(
            agents=agents,
            verbose=True,
            process=Process.hierarchical,
            share_crew=True,
            manager_llm=self.llm
        )


def create_task_creation_task(
    title: str,
    instructions: str,
    category: str,
    bounty_usd: float,
    deadline_hours: int,
    evidence_required: str,
    location_hint: Optional[str] = None
) -> Task:
    """Create a task for task creation workflow.
    
    Args:
        title: Task title
        instructions: Detailed instructions
        category: Task category
        bounty_usd: Bounty amount
        deadline_hours: Deadline in hours
        evidence_required: Required evidence type
        location_hint: Optional location hint
    
    Returns:
        Configured Task for CrewAI
    """
    return Task(
        description=f"""Create a physical task with the following specifications:
        
        Title: {title}
        Instructions: {instructions}
        Category: {category}
        Bounty: ${bounty_usd}
        Deadline: {deadline_hours} hours
        Evidence Required: {evidence_required}
        Location Hint: {location_hint or 'None specified'}
        
        Ensure the task is well-structured, clear, and includes all necessary details 
        for a human worker to complete successfully.""",
        expected_output="Task creation confirmation with task ID and details",
        agent=None  # Will be assigned when used with crew
    )


def create_monitoring_task(task_ids: List[str]) -> Task:
    """Create a task for monitoring existing tasks.
    
    Args:
        task_ids: List of task IDs to monitor
    
    Returns:
        Configured Task for monitoring workflow
    """
    return Task(
        description=f"""Monitor the status of the following tasks:
        
        Task IDs: {', '.join(task_ids)}
        
        Provide a comprehensive status report including:
        - Current status of each task
        - Any issues or concerns
        - Recommendations for next steps
        - Timeline updates""",
        expected_output="Detailed status report for all monitored tasks",
        agent=None  # Will be assigned when used with crew
    )


def create_approval_task(task_id: str, quality_criteria: str) -> Task:
    """Create a task for reviewing and approving submissions.
    
    Args:
        task_id: Task ID to review
        quality_criteria: Criteria for approval
    
    Returns:
        Configured Task for approval workflow
    """
    return Task(
        description=f"""Review the submission for task {task_id} and make an approval decision.
        
        Quality Criteria:
        {quality_criteria}
        
        Steps:
        1. Check the current task status and submission details
        2. Evaluate the submission against the quality criteria
        3. If approved, release payment with appropriate rating and feedback
        4. If not approved, provide constructive feedback
        
        Ensure fair and thorough evaluation.""",
        expected_output="Approval decision with rating, feedback, and reasoning",
        agent=None  # Will be assigned when used with crew
    )


# Export all classes and functions
__all__ = [
    "TaskManagerCrew",
    "WorkerFinderCrew", 
    "QualityAssuranceCrew",
    "FullServiceCrew",
    "create_task_creation_task",
    "create_monitoring_task",
    "create_approval_task",
]