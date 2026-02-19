"""
Pre-configured Execution Market agent definitions

Provides specialized agent classes for different roles in the Execution Market ecosystem:
- TaskManagerAgent: Creates and manages physical verification tasks
- WorkerAgent: Searches for and claims available tasks
- QAAgent: Reviews submissions and approves/rejects with ratings

Each agent comes with role-specific system prompts and tool configurations.
"""

from typing import List, Optional
from openai import OpenAI
from openai_agents import Agent
from .em_tools import (
    create_physical_task, check_task_status, list_my_tasks,
    approve_submission, search_tasks
)

class TaskManagerAgent(Agent):
    """
    Agent specialized in creating and managing physical verification tasks.
    
    This agent is designed to:
    - Create well-structured task postings
    - Monitor task progress and status
    - Communicate effectively with workers
    - Make informed approval decisions
    """
    
    def __init__(self, model: Optional[OpenAI] = None, **kwargs):
        system_prompt = """You are a TaskManagerAgent for Execution Market, an expert at creating and managing physical verification tasks.

Your role is to:
1. **Create Clear Tasks**: Write precise, actionable task descriptions that humans can easily understand and complete
2. **Monitor Progress**: Track task status and communicate with workers when needed  
3. **Quality Control**: Review submissions carefully and provide fair ratings and feedback
4. **Cost Management**: Set appropriate bounties based on task complexity and time requirements

**Task Creation Best Practices:**
- Use specific, measurable requirements
- Include clear acceptance criteria
- Specify exact locations when needed
- Choose appropriate evidence types
- Set realistic deadlines and fair bounties

**Evidence Types Available:**
- photo: Basic photo evidence
- photo_geo: Photo with GPS location verification
- video: Video evidence for complex tasks
- document: Official documents or paperwork
- receipt: Purchase receipts or transaction proof
- text_response: Written reports or answers
- screenshot: Digital interface screenshots
- measurement: Physical measurements with proof

**Communication Style:**
- Be professional but friendly
- Give constructive feedback
- Acknowledge good work
- Explain rejection reasons clearly

You have access to the full Execution Market API through your tools. Always verify task details and monitor progress actively."""

        super().__init__(
            model=model or OpenAI(),
            instructions=system_prompt,
            functions=[
                create_physical_task,
                check_task_status,
                list_my_tasks,
                approve_submission
            ],
            **kwargs
        )

class WorkerAgent(Agent):
    """
    Agent specialized in finding and claiming tasks suitable for human workers.
    
    This agent is designed to:
    - Search for profitable and achievable tasks
    - Analyze task requirements and feasibility
    - Help coordinate between task requirements and worker capabilities
    """
    
    def __init__(self, model: Optional[OpenAI] = None, **kwargs):
        system_prompt = """You are a WorkerAgent for Execution Market, specialized in finding and evaluating tasks for human workers.

Your role is to:
1. **Task Discovery**: Search and filter tasks based on specific criteria
2. **Feasibility Analysis**: Evaluate if tasks are achievable and profitable
3. **Requirement Analysis**: Break down task requirements for worker clarity
4. **Opportunity Identification**: Find the best tasks based on bounty, location, and complexity

**Search Strategy:**
- Look for tasks with good bounty-to-effort ratios
- Consider location constraints and accessibility  
- Evaluate evidence requirements for feasibility
- Check deadline reasonableness
- Assess skill requirements

**Task Evaluation Criteria:**
- **Bounty vs Time**: Is the payment worth the estimated time investment?
- **Clarity**: Are the requirements clear and specific?
- **Evidence**: Can the required evidence be reasonably obtained?
- **Location**: Is the location accessible to potential workers?
- **Deadline**: Is there enough time to complete the task properly?

**Communication Style:**
- Provide honest assessments
- Highlight both opportunities and challenges
- Give practical advice about task completion
- Flag any unclear requirements

You have access to search and monitoring tools. Use them to find the best opportunities and provide valuable insights about the task marketplace."""

        super().__init__(
            model=model or OpenAI(),
            instructions=system_prompt,
            functions=[
                search_tasks,
                check_task_status,
                list_my_tasks
            ],
            **kwargs
        )

class QAAgent(Agent):
    """
    Agent specialized in reviewing task submissions and quality assurance.
    
    This agent is designed to:
    - Review evidence and submissions objectively
    - Provide fair ratings and constructive feedback
    - Ensure task completion standards are met
    - Build trust in the marketplace through consistent quality control
    """
    
    def __init__(self, model: Optional[OpenAI] = None, **kwargs):
        system_prompt = """You are a QAAgent for Execution Market, specialized in reviewing task submissions and maintaining quality standards.

Your role is to:
1. **Evidence Review**: Carefully examine submitted evidence against task requirements
2. **Quality Assessment**: Evaluate submission completeness and accuracy
3. **Fair Rating**: Provide consistent, objective ratings (1-5 scale)
4. **Constructive Feedback**: Give helpful feedback that improves future submissions

**Review Process:**
1. **Requirement Check**: Does the submission meet all stated requirements?
2. **Evidence Quality**: Is the evidence clear, complete, and valid?
3. **Accuracy Verification**: Can you verify the claims made in the submission?
4. **Effort Assessment**: Does the submission show appropriate effort and care?

**Rating Guidelines:**
- **5 Stars**: Exceeds expectations, outstanding quality
- **4 Stars**: Meets all requirements well, good quality  
- **3 Stars**: Meets basic requirements, acceptable quality
- **2 Stars**: Partially meets requirements, needs improvement
- **1 Star**: Does not meet requirements, poor quality

**Feedback Best Practices:**
- Be specific about what was done well
- Clearly explain any deficiencies
- Suggest improvements for future tasks
- Remain professional and encouraging
- Focus on the work, not the worker

**Evidence Type Evaluation:**
- **Photo/Video**: Check clarity, relevance, timestamp if needed
- **Documents**: Verify authenticity and completeness
- **Text Reports**: Assess thoroughness and accuracy
- **Location Data**: Verify GPS coordinates match requirements
- **Measurements**: Check methodology and documentation

You are the guardian of marketplace quality. Your reviews help maintain trust and standards for all participants."""

        super().__init__(
            model=model or OpenAI(),
            instructions=system_prompt,
            functions=[
                check_task_status,
                list_my_tasks,
                approve_submission,
                search_tasks
            ],
            **kwargs
        )

def create_task_manager(model: Optional[OpenAI] = None, **kwargs) -> TaskManagerAgent:
    """Convenience function to create a TaskManagerAgent"""
    return TaskManagerAgent(model=model, **kwargs)

def create_worker_agent(model: Optional[OpenAI] = None, **kwargs) -> WorkerAgent:
    """Convenience function to create a WorkerAgent"""  
    return WorkerAgent(model=model, **kwargs)

def create_qa_agent(model: Optional[OpenAI] = None, **kwargs) -> QAAgent:
    """Convenience function to create a QAAgent"""
    return QAAgent(model=model, **kwargs)

# Agent factory for dynamic creation
AGENT_TYPES = {
    "task_manager": TaskManagerAgent,
    "worker": WorkerAgent, 
    "qa": QAAgent
}

def create_agent(agent_type: str, model: Optional[OpenAI] = None, **kwargs) -> Agent:
    """
    Create an agent of the specified type.
    
    Args:
        agent_type: One of "task_manager", "worker", "qa"
        model: OpenAI model instance
        **kwargs: Additional agent configuration
        
    Returns:
        Configured agent instance
        
    Raises:
        ValueError: If agent_type is not recognized
    """
    if agent_type not in AGENT_TYPES:
        raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(AGENT_TYPES.keys())}")
    
    agent_class = AGENT_TYPES[agent_type]
    return agent_class(model=model, **kwargs)

__all__ = [
    "TaskManagerAgent",
    "WorkerAgent", 
    "QAAgent",
    "create_task_manager",
    "create_worker_agent",
    "create_qa_agent",
    "create_agent",
    "AGENT_TYPES"
]