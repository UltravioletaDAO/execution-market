#!/usr/bin/env python3
"""
Multi-Agent CrewAI Execution Market Example
===========================================

This example demonstrates a comprehensive workflow with multiple agents:
1. Task Manager - Creates and oversees tasks
2. Quality Assurance - Reviews and approves submissions
3. Operations Coordinator - Monitors and coordinates workflow

This shows how different agents can work together to manage the complete
task lifecycle on Execution Market.

Run with: python multi_agent_crew.py
"""

import sys
from pathlib import Path

# Add the parent directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from crewai import Agent, Task, Crew
from crewai.process import Process

from em_tools import (
    create_physical_task,
    check_task_status,
    list_my_tasks,
    approve_submission,
    search_tasks
)
from em_crew import (
    TaskManagerCrew,
    QualityAssuranceCrew,
    FullServiceCrew,
    create_task_creation_task,
    create_monitoring_task,
    create_approval_task
)


def multi_agent_task_creation():
    """Example using multiple agents for comprehensive task management."""
    
    print("🤖 Multi-Agent Task Creation and Management")
    print("=" * 60)
    
    # Create specialized agents
    task_creator = Agent(
        role="Senior Task Manager",
        goal="Create high-quality, detailed tasks that ensure successful completion",
        backstory="""You are an experienced task manager who has created thousands 
        of successful tasks. You know how to write clear instructions, set appropriate 
        compensation, and anticipate potential issues before they occur.""",
        tools=[create_physical_task, list_my_tasks],
        verbose=True,
        allow_delegation=True
    )
    
    operations_manager = Agent(
        role="Operations Manager", 
        goal="Coordinate task operations and ensure smooth workflow",
        backstory="""You are responsible for operational oversight, ensuring that 
        all tasks are properly managed and any issues are identified and resolved 
        quickly. You coordinate between different aspects of task management.""",
        tools=[check_task_status, list_my_tasks],
        verbose=True,
        allow_delegation=True
    )
    
    quality_manager = Agent(
        role="Quality Assurance Manager",
        goal="Ensure all tasks meet quality standards and submissions are fairly evaluated",
        backstory="""You are a quality assurance expert who ensures that tasks are 
        well-designed and that worker submissions are evaluated fairly and thoroughly. 
        You maintain high standards while being fair to workers.""",
        tools=[check_task_status, approve_submission],
        verbose=True,
        allow_delegation=False
    )
    
    # Create comprehensive tasks
    business_research_task = Task(
        description="""Create a comprehensive business research task for local market analysis.
        
        The task should involve:
        - Visiting 3 different coffee shops in the downtown area
        - Taking photos of each storefront and menu
        - Recording operating hours and busy periods
        - Noting pricing for standard items (coffee, pastries)
        - Observing customer volume and demographics
        - Providing a brief report on each location
        
        Set appropriate compensation considering the scope (multiple locations, time required).
        Use 'data_collection' category and require both photos and a text report.
        Give reasonable deadline considering the complexity.
        """,
        expected_output="Task created with comprehensive requirements and fair compensation",
        agent=task_creator
    )
    
    operations_oversight_task = Task(
        description="""Monitor the business research task and provide operational oversight.
        
        Once the task is created:
        1. Track the task status regularly
        2. Identify any potential issues or concerns
        3. Provide recommendations for task management
        4. Generate a status report for stakeholders
        
        Focus on ensuring smooth operations and proactive issue management.""",
        expected_output="Operational status report with recommendations",
        agent=operations_manager
    )
    
    quality_review_task = Task(
        description="""Prepare quality assurance criteria for the business research task.
        
        Define clear criteria for:
        - Photo quality standards (clear, well-lit, shows required details)
        - Report completeness (all locations visited, all data points covered)
        - Professional standards (respectful interaction, accurate information)
        
        When submissions are received, apply these criteria fairly and provide 
        constructive feedback. Balance quality standards with fair evaluation.""",
        expected_output="Quality criteria defined and ready for submission review",
        agent=quality_manager
    )
    
    # Create the crew
    multi_crew = Crew(
        agents=[task_creator, operations_manager, quality_manager],
        tasks=[business_research_task, operations_oversight_task, quality_review_task],
        verbose=True,
        process=Process.sequential,
        share_crew=True
    )
    
    print("\n🎯 Executing multi-agent crew...")
    result = multi_crew.kickoff()
    
    print("\n✅ Multi-Agent Crew Results:")
    print(result)
    
    return result


def full_service_crew_example():
    """Example using the pre-built FullServiceCrew."""
    
    print("\n🏢 Full Service Crew Example")
    print("=" * 50)
    
    # Create full service crew
    full_service = FullServiceCrew()
    crew = full_service.create_crew()
    
    # Create a complex workflow task
    workflow_task = Task(
        description="""Execute a complete task management workflow:
        
        1. Create a verification task for a new restaurant opening
           - Title: "New Restaurant Verification - Bella Vista Italian"
           - Verify they are open for business
           - Take photos of exterior, menu, and dining area
           - Note hours, contact info, and accessibility features  
           - $8 bounty, 4-hour deadline
           - Require photo evidence
           - Location: Main Street business district
        
        2. Monitor the task progress
           - Check status regularly
           - Identify any issues
           - Provide updates
        
        3. Prepare for submission review
           - Define quality criteria
           - Set up approval process
           
        Coordinate all aspects to ensure smooth execution.""",
        expected_output="Complete workflow execution from task creation to approval preparation",
        agent=crew.agents[0]  # Assign to Task Manager (first agent)
    )
    
    # Add task to crew
    crew.tasks = [workflow_task]
    
    print("\n🎯 Executing full service crew...")
    result = crew.kickoff()
    
    print("\n✅ Full Service Crew Results:")
    print(result)
    
    return result


def specialized_crews_collaboration():
    """Example of multiple specialized crews working together."""
    
    print("\n🤝 Specialized Crews Collaboration")
    print("=" * 50)
    
    # Phase 1: Task Creation with TaskManagerCrew
    print("\n📝 Phase 1: Task Creation")
    task_crew = TaskManagerCrew()
    
    creation_task = create_task_creation_task(
        title="Local Art Gallery Documentation",
        instructions="""Document the current exhibition at the downtown art gallery:
        
        1. Take photos of the gallery entrance and signage
        2. Photograph 5-8 key artworks (following photography rules)
        3. Record exhibition title, dates, and featured artists
        4. Note gallery hours and admission fees
        5. Provide brief description of the exhibition theme
        
        Be respectful of gallery rules and ask permission for photography.""",
        category="content_creation",
        bounty_usd=12.00,
        deadline_hours=6,
        evidence_required="photo",
        location_hint="Downtown arts district, near the city museum"
    )
    
    task_mgmt_crew = Crew(
        agents=task_crew.create_agents(),
        tasks=[creation_task],
        verbose=True,
        process=Process.sequential
    )
    
    print("🎯 Creating task with specialized task management crew...")
    creation_result = task_mgmt_crew.kickoff()
    
    # Phase 2: Quality Assurance with QualityAssuranceCrew  
    print("\n🔍 Phase 2: Quality Assurance Setup")
    qa_crew = QualityAssuranceCrew()
    
    qa_task = create_approval_task(
        task_id="gallery-doc-task-456",  # Would be actual task ID from Phase 1
        quality_criteria="""
        Photo Quality:
        - Images are clear, well-lit, and in focus
        - All required areas are documented
        - Respectful of gallery rules and artwork
        
        Documentation Quality:
        - All required information is collected
        - Information is accurate and complete
        - Professional presentation
        
        Compliance:
        - Gallery rules were followed
        - Permission was obtained where required
        - Respectful interaction with staff
        """
    )
    
    qa_mgmt_crew = Crew(
        agents=qa_crew.create_agents(),
        tasks=[qa_task],
        verbose=True,
        process=Process.sequential
    )
    
    print("🎯 Setting up quality assurance process...")
    qa_result = qa_mgmt_crew.kickoff()
    
    print("\n✅ Collaboration Results:")
    print("Phase 1 (Task Creation):", creation_result)
    print("Phase 2 (Quality Setup):", qa_result)
    
    return {"creation": creation_result, "qa_setup": qa_result}


def marketplace_search_example():
    """Example of searching marketplace for opportunities."""
    
    print("\n🔍 Marketplace Search Example")
    print("=" * 50)
    
    # Create marketplace search agent
    market_scout = Agent(
        role="Marketplace Scout",
        goal="Find interesting task opportunities in the marketplace", 
        backstory="""You are skilled at identifying valuable opportunities in the 
        marketplace. You can quickly assess tasks for quality, fair compensation, 
        and alignment with capabilities.""",
        tools=[search_tasks, check_task_status],
        verbose=True,
        allow_delegation=False
    )
    
    search_task = Task(
        description="""Search the marketplace for interesting opportunities:
        
        1. Search for 'verification' category tasks
        2. Look for tasks with reasonable compensation (>$3)
        3. Find tasks with realistic deadlines
        4. Identify any particularly interesting or unique tasks
        5. Provide analysis of the current marketplace activity
        
        Focus on finding quality opportunities that would be worth pursuing.""",
        expected_output="Analysis of marketplace opportunities with specific recommendations",
        agent=market_scout
    )
    
    search_crew = Crew(
        agents=[market_scout],
        tasks=[search_task],
        verbose=True,
        process=Process.sequential
    )
    
    print("🎯 Searching marketplace for opportunities...")
    search_result = search_crew.kickoff()
    
    print("\n🔍 Marketplace Search Results:")
    print(search_result)
    
    return search_result


def main():
    """Run all multi-agent examples."""
    
    print("🚀 CrewAI Multi-Agent Execution Market Examples")
    print("=" * 70)
    
    try:
        # Example 1: Custom multi-agent crew
        print("\n1️⃣ Multi-Agent Task Creation Example...")
        multi_result = multi_agent_task_creation()
        
        # Example 2: Full service crew
        print("\n2️⃣ Full Service Crew Example...")
        full_service_result = full_service_crew_example()
        
        # Example 3: Specialized crews collaboration
        print("\n3️⃣ Specialized Crews Collaboration...")
        collab_result = specialized_crews_collaboration()
        
        # Example 4: Marketplace search
        print("\n4️⃣ Marketplace Search Example...")
        search_result = marketplace_search_example()
        
        print("\n🎉 All multi-agent examples completed!")
        print("\nKey Takeaways:")
        print("- Different agents can specialize in different aspects of task management")
        print("- Crews can work sequentially or hierarchically depending on needs")
        print("- Pre-built crews provide ready-to-use configurations")
        print("- Multiple crews can collaborate on complex workflows")
        print("- Marketplace search capabilities enable opportunity discovery")
        
        print("\nNext Steps:")
        print("- Customize agent roles and backstories for your specific domain")
        print("- Set up proper authentication for production use")
        print("- Implement error handling and retry logic")
        print("- Add domain-specific validation and quality checks")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("\nThis is expected if running without proper authentication.")
        print("The examples demonstrate the structure and can be adapted for real use.")


if __name__ == "__main__":
    main()