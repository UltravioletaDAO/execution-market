#!/usr/bin/env python3
"""
Basic Execution Market task creation example

Demonstrates simple single-agent task creation using the TaskManagerAgent.
This example shows how to create a physical verification task and monitor its progress.
"""

import os
import sys
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from openai import OpenAI
from em_agent import TaskManagerAgent
from em_tools import TaskInput

def main():
    """
    Create a simple physical verification task and monitor it.
    """
    
    # Check for API key
    if not os.getenv("EM_API_KEY"):
        print("❌ Error: EM_API_KEY environment variable is required")
        print("Get your API key from: https://execution.market/dashboard")
        return
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable is required")
        return
    
    print("🤖 Creating TaskManagerAgent...")
    
    # Create the agent
    client = OpenAI()
    agent = TaskManagerAgent(model=client)
    
    # Example task request
    task_request = """
    I need someone to verify that a local coffee shop is currently open and serving customers.
    
    Task Details:
    - Location: Starbucks at 123 Main Street, Downtown
    - Required: Photo of the storefront showing it's open
    - Backup: If closed, photo of hours sign showing when they open
    - Budget: $3.00 for this simple verification
    - Deadline: Within 4 hours
    
    This is for a delivery app to update store status.
    """
    
    print("📝 Task Request:")
    print(task_request)
    print("\n" + "="*60 + "\n")
    
    # Have the agent create the task
    print("🚀 Creating task with agent...")
    
    messages = [
        {
            "role": "user", 
            "content": f"Please create this physical verification task: {task_request}"
        }
    ]
    
    try:
        # Run the agent to create the task
        response = agent.run(messages=messages)
        
        print("✅ Agent Response:")
        print(response.messages[-1]['content'])
        
        # If the agent created a task, show the details
        if hasattr(response, 'task_details'):
            print(f"\n📋 Task Created:")
            print(f"ID: {response.task_details.get('task_id', 'N/A')}")
            print(f"Status: {response.task_details.get('status', 'N/A')}")
            print(f"URL: {response.task_details.get('url', 'N/A')}")
    
    except Exception as e:
        print(f"❌ Error creating task: {e}")
        return
    
    print("\n" + "="*60)
    print("✨ Basic task creation complete!")
    print("\nNext steps:")
    print("- Check the Execution Market dashboard for your task")
    print("- Monitor for worker assignments and submissions")
    print("- Use the QA agent to review submissions when ready")

def create_task_directly():
    """
    Alternative example: Create task directly using the tools
    """
    
    print("\n🔧 Alternative: Direct tool usage")
    
    from em_tools import create_physical_task
    
    # Create task input
    task_input = TaskInput(
        title="Verify Coffee Shop Status",
        description="Visit Starbucks at 123 Main Street and take a photo showing whether they are currently open for business. If closed, photograph their hours sign.",
        bounty=Decimal("3.00"),
        deadline_hours=4,
        evidence_type="photo",
        location_required="123 Main Street, Downtown"
    )
    
    try:
        result = create_physical_task(task_input)
        
        if result['success']:
            print(f"✅ Task created successfully!")
            print(f"Task ID: {result['task_id']}")
            print(f"URL: {result['url']}")
        else:
            print(f"❌ Task creation failed: {result['error']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
    create_task_directly()