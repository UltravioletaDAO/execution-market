#!/usr/bin/env python3
"""
Simple Execution Market Task Example
===================================

This example demonstrates how to:
1. Create a physical task for a human to complete
2. Monitor the task status
3. Approve the submission when completed

Run with: python simple_task.py
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to path so we can import our tools
sys.path.insert(0, str(Path(__file__).parent.parent))

from em_tools import (
    create_physical_task_tool,
    check_task_status_tool,
    list_my_tasks_tool,
    approve_submission_tool,
)


async def create_and_monitor_task():
    """Create a simple task and monitor it until completion."""
    
    print("🚀 Creating a simple verification task...")
    
    # Step 1: Create a task
    task_result = await create_physical_task_tool._arun(
        title="Verify Coffee Shop Status",
        instructions="""Please visit the Starbucks location at 123 Main Street and:
        
        1. Take a clear photo of the storefront
        2. Verify if it's currently open or closed
        3. If open, note the current wait time/crowd level
        4. Report back with your findings
        
        This is for a business intelligence project. Please be discrete and professional.""",
        category="verification",
        bounty_usd=5.00,  # $5 for this simple task
        deadline_hours=4,  # 4 hours to complete
        evidence_required="photo",  # We need photo evidence
        location_hint="Downtown area, near the subway station",
        # Note: Using default API base and no auth (anonymous)
    )
    
    print(f"✅ Task created: {task_result}")
    
    # Extract task ID from the result (this is a simple example)
    # In a real application, you'd parse the JSON response properly
    task_id = "task_123"  # This would come from parsing the actual response
    
    print(f"\n🔍 Monitoring task {task_id}...")
    
    # Step 2: Check task status periodically
    for attempt in range(1, 4):  # Check 3 times for demo purposes
        print(f"\n--- Status Check #{attempt} ---")
        
        status_result = await check_task_status_tool._arun(
            task_id=task_id
        )
        
        print(f"Status: {status_result}")
        
        # In a real scenario, you'd parse the JSON and check if status is "completed"
        # For this demo, we'll simulate the progression
        if attempt == 3:
            print("\n🎉 Task appears to be completed! Let's check all our tasks...")
            break
            
        # Wait a bit before checking again
        await asyncio.sleep(2)
    
    # Step 3: List all our tasks to see the overview
    print("\n📋 All my tasks:")
    all_tasks = await list_my_tasks_tool._arun()
    print(all_tasks)
    
    # Step 4: Simulate approving a submission
    print("\n✅ Approving the submission...")
    
    # In reality, you'd get the submission_id from the task status
    submission_id = "sub_456"  # This would come from the task details
    
    try:
        approval_result = await approve_submission_tool._arun(
            submission_id=submission_id
        )
        print(f"Approval result: {approval_result}")
    except Exception as e:
        print(f"Note: Approval would work with a real submission ID. Error: {e}")
    
    print("\n🎯 Task workflow completed!")
    print("\nIn a real scenario:")
    print("- The task would be posted to actual human workers")
    print("- You'd receive notifications when workers apply and complete tasks")
    print("- Payment would be automatically handled via smart contracts")
    print("- You'd have full visibility into the task lifecycle")


async def demonstrate_task_types():
    """Show examples of different types of tasks you can create."""
    
    print("\n" + "="*60)
    print("📝 TASK TYPE EXAMPLES")
    print("="*60)
    
    task_examples = [
        {
            "name": "Photo Verification",
            "description": "Take a photo of a specific location or object",
            "params": {
                "title": "Photo of Central Park Lake",
                "instructions": "Take a clear photo of the lake in Central Park, Manhattan. Include some recognizable landmarks if possible.",
                "category": "verification",
                "bounty_usd": 3.00,
                "deadline_hours": 6,
                "evidence_required": "photo_geo",
                "location_hint": "Central Park, Manhattan, NY"
            }
        },
        {
            "name": "Delivery Task", 
            "description": "Pick up or deliver items between locations",
            "params": {
                "title": "Document Pickup from Law Office",
                "instructions": "Pick up sealed envelope from Johnson & Associates Law Firm (reception desk, ask for 'Smith package'). Deliver to City Hall records office.",
                "category": "delivery",
                "bounty_usd": 15.00,
                "deadline_hours": 8,
                "evidence_required": "photo",
                "location_hint": "Downtown business district"
            }
        },
        {
            "name": "Mystery Shopping",
            "description": "Visit a business and evaluate the experience",
            "params": {
                "title": "Best Buy Gaming Laptop Shopping Experience",
                "instructions": "Visit Best Buy and inquire about gaming laptops. Ask about specs, pricing, and availability. Rate the customer service quality.",
                "category": "mystery_shopping",
                "bounty_usd": 12.00,
                "deadline_hours": 12,
                "evidence_required": "text_response",
                "location_hint": "Any Best Buy location in your area"
            }
        },
        {
            "name": "Data Collection",
            "description": "Gather specific information from physical locations",
            "params": {
                "title": "Restaurant Menu and Pricing Survey",
                "instructions": "Visit 3 pizza restaurants in downtown area. Document current menu prices for large pepperoni pizza. Take photos of menu boards.",
                "category": "data_collection", 
                "bounty_usd": 20.00,
                "deadline_hours": 24,
                "evidence_required": "photo",
                "location_hint": "Downtown area, within 5 blocks of Main & 1st"
            }
        }
    ]
    
    for i, example in enumerate(task_examples, 1):
        print(f"\n{i}. {example['name']}")
        print(f"   Description: {example['description']}")
        print(f"   Bounty: ${example['params']['bounty_usd']}")
        print(f"   Category: {example['params']['category']}")
        print(f"   Evidence: {example['params']['evidence_required']}")
        
        # Show how you would create this task
        print(f"   Code:")
        print(f"   await create_physical_task_tool._arun(")
        for key, value in example['params'].items():
            if isinstance(value, str):
                print(f"       {key}=\"{value}\",")
            else:
                print(f"       {key}={value},")
        print(f"   )")


async def main():
    """Run the complete example."""
    print("🌍 Execution Market LangChain Integration - Simple Example")
    print("="*60)
    
    # Run the main task workflow
    await create_and_monitor_task()
    
    # Show examples of different task types
    await demonstrate_task_types()
    
    print("\n" + "="*60)
    print("🎉 Example completed!")
    print("\nNext steps:")
    print("- Try the full agent example: python agent_with_em.py")
    print("- Modify the task parameters above for your use case")
    print("- Add authentication for production usage")
    print("- Integrate with your existing LangChain agent workflow")


if __name__ == "__main__":
    # Run the async example
    asyncio.run(main())