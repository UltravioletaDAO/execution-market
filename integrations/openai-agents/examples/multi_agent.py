#!/usr/bin/env python3
"""
Multi-agent Execution Market demonstration

Shows how TaskManager, Worker, and QA agents work together through
handoffs and coordination patterns to manage complete task lifecycles.
"""

import os
import sys
import time
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from openai import OpenAI
from em_swarm import ExecutionMarketSwarm, quick_task_creation
from em_agent import create_agent

def main():
    """
    Demonstrate multi-agent coordination for task lifecycle management.
    """
    
    # Check for required API keys
    required_keys = ["EM_API_KEY", "OPENAI_API_KEY"]
    for key in required_keys:
        if not os.getenv(key):
            print(f"❌ Error: {key} environment variable is required")
            return
    
    print("🤖 Initializing Execution Market Swarm...")
    print("Agents: TaskManager → WorkerAgent → QAAgent")
    print("\n" + "="*70 + "\n")
    
    # Create the swarm
    client = OpenAI()
    swarm = ExecutionMarketSwarm(model=client)
    
    # Demonstration scenarios
    scenarios = [
        {
            "name": "Restaurant Verification",
            "description": "Verify that a new restaurant is open and serving customers, get photos of menu and dining area",
            "workflow": "create_and_manage_task"
        },
        {
            "name": "Market Research",  
            "description": "Find tasks related to retail store visits and price comparisons under $5",
            "workflow": "find_opportunities"
        },
        {
            "name": "Quality Review",
            "description": "Review recent submissions for photo quality and requirement compliance",
            "workflow": "review_submissions"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"📋 Scenario {i}: {scenario['name']}")
        print(f"Description: {scenario['description']}")
        print(f"Workflow: {scenario['workflow']}")
        print("-" * 50)
        
        try:
            if scenario['workflow'] == 'create_and_manage_task':
                result = swarm.create_and_manage_task(scenario['description'])
                
            elif scenario['workflow'] == 'find_opportunities':
                result = swarm.find_and_evaluate_opportunities(scenario['description'])
                
            elif scenario['workflow'] == 'review_submissions':
                # For demo purposes, use placeholder task IDs
                result = swarm.review_and_approve_submissions(['demo_task_1', 'demo_task_2'])
            
            # Display results
            if result['success']:
                print(f"✅ Workflow completed successfully")
                print(f"Final agent: {result.get('final_agent', 'Unknown')}")
                
                # Show conversation summary
                if 'messages' in result and result['messages']:
                    print(f"💬 Conversation summary:")
                    for msg in result['messages'][-2:]:  # Show last 2 messages
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')[:200] + "..." if len(msg.get('content', '')) > 200 else msg.get('content', '')
                        print(f"   {role.upper()}: {content}")
                
                # Show handoff information if available
                if result.get('context_transfers'):
                    print(f"🔄 Agent handoffs: {len(result['context_transfers'])}")
                        
            else:
                print(f"❌ Workflow failed: {result.get('error', 'Unknown error')}")
            
        except Exception as e:
            print(f"❌ Scenario failed: {e}")
        
        print("\n" + "="*70 + "\n")
        time.sleep(1)  # Brief pause between scenarios

def demonstrate_individual_agents():
    """
    Show how individual agents can be used independently.
    """
    print("🔧 Individual Agent Demonstrations")
    print("="*50)
    
    client = OpenAI()
    
    # TaskManager Agent
    print("\n1. 📝 TaskManager Agent - Creating a verification task")
    task_manager = create_agent("task_manager", model=client)
    
    messages = [{"role": "user", "content": """
    Create a task to verify that a local gym is open and has working equipment.
    The task should require photos of the gym floor and at least 3 pieces of working equipment.
    Set a fair bounty around $4-6 for this type of verification.
    """}]
    
    try:
        response = task_manager.run(messages=messages)
        print("📤 TaskManager Response:")
        print(response.messages[-1]['content'][:300] + "...")
    except Exception as e:
        print(f"❌ TaskManager error: {e}")
    
    # Worker Agent  
    print("\n2. 🔍 Worker Agent - Finding opportunities")
    worker_agent = create_agent("worker", model=client)
    
    messages = [{"role": "user", "content": """
    Search for tasks that involve visiting retail stores or restaurants.
    Focus on tasks under $10 with clear requirements and reasonable deadlines.
    Evaluate which ones would be best for someone with a car in an urban area.
    """}]
    
    try:
        response = worker_agent.run(messages=messages)
        print("📤 Worker Agent Response:")
        print(response.messages[-1]['content'][:300] + "...")
    except Exception as e:
        print(f"❌ Worker Agent error: {e}")
    
    # QA Agent
    print("\n3. ⭐ QA Agent - Quality assessment")
    qa_agent = create_agent("qa", model=client)
    
    messages = [{"role": "user", "content": """
    Explain your process for reviewing a photo submission for a restaurant verification task.
    What quality standards would you apply? How would you rate different scenarios?
    Give examples of 5-star vs 3-star vs 1-star submissions.
    """}]
    
    try:
        response = qa_agent.run(messages=messages)
        print("📤 QA Agent Response:")
        print(response.messages[-1]['content'][:300] + "...")
    except Exception as e:
        print(f"❌ QA Agent error: {e}")

def full_lifecycle_demo():
    """
    Demonstrate a complete task lifecycle with all agents working together.
    """
    print("\n🔄 Full Lifecycle Demonstration")
    print("="*50)
    print("Showing complete handoff chain: TaskManager → Worker → QA → TaskManager")
    
    client = OpenAI()
    swarm = ExecutionMarketSwarm(model=client)
    
    # Complex multi-step task
    complex_task = """
    I need to research a new market area for food delivery expansion.
    
    Create a task to:
    1. Visit 5 restaurants in the downtown area
    2. Document their current delivery options
    3. Photo their storefront and menu displays  
    4. Report on customer traffic during lunch hour
    5. Collect business hours information
    
    This requires coordination between task creation, worker evaluation, and quality review.
    """
    
    try:
        result = swarm.full_lifecycle_demo(complex_task)
        
        if result['success']:
            print("✅ Full lifecycle completed!")
            print(f"Final agent: {result.get('final_agent', 'Unknown')}")
            print(f"Total agent interactions: {len(result.get('messages', []))}")
            
            # Show key messages from the conversation
            print("\n💬 Key conversation highlights:")
            messages = result.get('messages', [])
            for i, msg in enumerate(messages):
                if i % 2 == 0:  # Show every other message to avoid spam
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')[:150] + "..." if len(msg.get('content', '')) > 150 else msg.get('content', '')
                    print(f"   Step {i+1} - {role.upper()}: {content}")
            
        else:
            print(f"❌ Full lifecycle failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Lifecycle demo error: {e}")

if __name__ == "__main__":
    print("🚀 Execution Market Multi-Agent Demonstration")
    print("This demo shows how specialized agents work together")
    print("to manage physical world tasks from creation to completion.\n")
    
    # Run all demonstrations
    main()
    demonstrate_individual_agents()  
    full_lifecycle_demo()
    
    print("\n" + "="*70)
    print("✨ Multi-agent demonstration complete!")
    print("\nKey takeaways:")
    print("- TaskManager specializes in creating clear, actionable tasks")
    print("- Worker Agent finds and evaluates opportunities")  
    print("- QA Agent maintains quality standards through reviews")
    print("- Swarm coordination enables complex workflows through handoffs")
    print("- Each agent brings specialized knowledge to their role")
    print("\nNext steps:")
    print("- Try creating your own agent combinations")
    print("- Experiment with different handoff patterns")
    print("- Integrate with your specific use cases")