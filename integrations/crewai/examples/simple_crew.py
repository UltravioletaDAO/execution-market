#!/usr/bin/env python3
"""
Simple CrewAI Execution Market Example
=====================================

This example demonstrates how to:
1. Create a simple crew with one agent
2. Create a physical task for a human to complete
3. Monitor the task status

Run with: python simple_crew.py
"""

import sys
from pathlib import Path

# Add the parent directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from crewai import Agent, Task, Crew
from crewai.process import Process

from em_tools import create_physical_task, check_task_status
from em_crew import create_task_creation_task, TaskManagerCrew


def simple_crew_example():
    """Create a simple crew that creates a task."""
    
    print("🚀 Simple CrewAI Execution Market Example")
    print("=" * 50)
    
    # Option 1: Create a custom simple crew
    print("\n📋 Creating a simple task creation agent...")
    
    # Create a simple agent
    task_creator = Agent(
        role="Task Creator",
        goal="Create clear and actionable physical tasks for human workers",
        backstory="""You are skilled at creating tasks that humans can complete 
        efficiently. You understand how to write clear instructions, set fair 
        compensation, and specify appropriate evidence requirements.""",
        tools=[create_physical_task, check_task_status],
        verbose=True,
        allow_delegation=False
    )
    
    # Create a task for the agent to execute
    creation_task = Task(
        description="""Create a task for someone to verify that a local coffee shop 
        is open and take a photo of their menu board.
        
        Requirements:
        - Task should be in the 'verification' category
        - Pay $3.00 for the task
        - Give them 2 hours to complete it
        - Require a photo as evidence
        - Location hint should mention it's for a local business survey
        
        Make sure the instructions are clear and professional.""",
        expected_output="Confirmation that the task was created successfully with task ID",
        agent=task_creator
    )
    
    # Create a simple crew
    simple_crew = Crew(
        agents=[task_creator],
        tasks=[creation_task],
        verbose=True,
        process=Process.sequential
    )
    
    # Execute the crew
    print("\n🎯 Executing simple crew...")
    result = simple_crew.kickoff()
    
    print("\n✅ Simple Crew Result:")
    print(result)
    
    return result


def pre_built_crew_example():
    """Use a pre-built crew configuration."""
    
    print("\n🏗️ Using Pre-Built Task Manager Crew")
    print("=" * 50)
    
    # Create a pre-built crew
    task_manager_crew = TaskManagerCrew()
    crew = task_manager_crew.create_crew()
    
    # Create a task for the crew to handle
    task = create_task_creation_task(
        title="Restaurant Menu Photography",
        instructions="""Please visit the restaurant 'Mama's Kitchen' on Oak Street and:
        
        1. Take a clear, well-lit photo of their current menu board
        2. Note if they have any daily specials displayed
        3. Verify their current hours of operation
        4. Take a photo of the storefront showing the restaurant name
        
        This is for a local business directory update. Please be respectful and 
        ask permission if needed.""",
        category="verification",
        bounty_usd=4.50,
        deadline_hours=3,
        evidence_required="photo",
        location_hint="Oak Street downtown area, near the city library"
    )
    
    # Add the task to crew
    crew.tasks = [task]
    task.agent = crew.agents[0]  # Assign to first agent (Task Planner)
    
    # Execute the crew
    print("\n🎯 Executing pre-built crew...")
    result = crew.kickoff()
    
    print("\n✅ Pre-Built Crew Result:")
    print(result)
    
    return result


def monitoring_example(task_id: str = "example-task-123"):
    """Example of monitoring an existing task."""
    
    print("\n📊 Task Monitoring Example")
    print("=" * 50)
    
    # Create a monitoring agent
    monitor_agent = Agent(
        role="Task Monitor",
        goal="Monitor task progress and provide status updates",
        backstory="""You are responsible for keeping track of active tasks and 
        providing clear status reports to stakeholders.""",
        tools=[check_task_status],
        verbose=True,
        allow_delegation=False
    )
    
    # Create a monitoring task
    monitoring_task = Task(
        description=f"""Check the status of task ID: {task_id}
        
        Provide a comprehensive report including:
        - Current status
        - Any progress updates
        - Time remaining until deadline
        - Worker assignment status
        - Any issues or concerns""",
        expected_output="Detailed task status report",
        agent=monitor_agent
    )
    
    # Create monitoring crew
    monitoring_crew = Crew(
        agents=[monitor_agent],
        tasks=[monitoring_task],
        verbose=True,
        process=Process.sequential
    )
    
    # Execute monitoring
    print(f"\n🔍 Monitoring task {task_id}...")
    result = monitoring_crew.kickoff()
    
    print("\n📋 Monitoring Result:")
    print(result)
    
    return result


def main():
    """Run all examples."""
    
    print("🤖 CrewAI + Execution Market Integration Examples")
    print("=" * 60)
    
    try:
        # Run simple crew example
        print("\n1️⃣ Running Simple Crew Example...")
        simple_result = simple_crew_example()
        
        # Run pre-built crew example  
        print("\n2️⃣ Running Pre-Built Crew Example...")
        prebuilt_result = pre_built_crew_example()
        
        # Run monitoring example (will likely fail since task doesn't exist)
        print("\n3️⃣ Running Monitoring Example...")
        monitoring_result = monitoring_example()
        
        print("\n🎉 All examples completed!")
        print("\nNext steps:")
        print("- Replace 'example-task-123' with a real task ID to test monitoring")
        print("- Set up authentication tokens for production use")
        print("- Customize agents and tasks for your specific use case")
        print("- Explore the other pre-built crews: WorkerFinderCrew, QualityAssuranceCrew")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("\nThis is normal if you don't have authentication set up.")
        print("The examples show the structure and can be adapted for your needs.")


if __name__ == "__main__":
    main()