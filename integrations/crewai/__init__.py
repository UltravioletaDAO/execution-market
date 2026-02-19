"""
Execution Market CrewAI Integration
==================================

CrewAI integration for Execution Market - connect AI agent crews to the physical world.

This package provides:
- CrewAI-compatible tools for task creation and management
- Pre-built crew configurations for common workflows  
- Examples and documentation for getting started

Quick start:
    from em_tools import create_physical_task
    from em_crew import TaskManagerCrew
    
    # Create a crew
    crew_builder = TaskManagerCrew()
    crew = crew_builder.create_crew()
    
    # Execute tasks
    result = crew.kickoff()
"""

from .em_tools import (
    create_physical_task,
    check_task_status,
    list_my_tasks,
    approve_submission,
    search_tasks,
)

from .em_crew import (
    TaskManagerCrew,
    WorkerFinderCrew,
    QualityAssuranceCrew,
    FullServiceCrew,
    create_task_creation_task,
    create_monitoring_task,
    create_approval_task,
)

__version__ = "1.0.0"
__author__ = "Execution Market"
__email__ = "support@execution.market"
__description__ = "CrewAI integration for Execution Market"

__all__ = [
    # Tools
    "create_physical_task",
    "check_task_status", 
    "list_my_tasks",
    "approve_submission",
    "search_tasks",
    
    # Crew classes
    "TaskManagerCrew",
    "WorkerFinderCrew",
    "QualityAssuranceCrew", 
    "FullServiceCrew",
    
    # Task creation helpers
    "create_task_creation_task",
    "create_monitoring_task",
    "create_approval_task",
]