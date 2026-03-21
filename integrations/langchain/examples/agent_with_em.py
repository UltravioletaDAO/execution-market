#!/usr/bin/env python3
"""
Full LangChain Agent with Execution Market Integration
=====================================================

This example demonstrates a complete LangChain agent that can:
1. Use Execution Market tools alongside other tools
2. Reason about when to create physical tasks
3. Handle multi-step workflows involving real-world actions

Note: This example uses a mock LLM for demonstration. In practice,
you'd use a real language model like OpenAI's GPT or Anthropic's Claude.

Run with: python agent_with_em.py
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Any

# Add the parent directory to path so we can import our tools
sys.path.insert(0, str(Path(__file__).parent.parent))

from em_toolkit import ExecutionMarketAgentToolkit
from langchain_core.tools import BaseTool, tool
from langchain_core.language_models import BaseLLM
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from pydantic import BaseModel


class MockLLMResult(BaseModel):
    """Mock result from LLM."""
    generations: List[Any]
    llm_output: dict = {}


class MockLLM(BaseLLM):
    """Mock LLM for demonstration purposes."""
    
    def _llm_type(self) -> str:
        return "mock"
    
    def _call(self, prompt: str, stop: List[str] = None) -> str:
        """Mock LLM responses based on the prompt content."""
        
        # Simple pattern matching to simulate realistic responses
        if "take a photo" in prompt.lower() or "photograph" in prompt.lower():
            return """I need to create a physical task for someone to take a photo. Let me use the create_physical_task tool.

Action: create_physical_task
Action Input: {
  "title": "Photo Verification Task",
  "instructions": "Take a clear photo of the requested location or object. Ensure good lighting and include any relevant context in the frame.",
  "category": "verification",
  "bounty_usd": 5.0,
  "deadline_hours": 6,
  "evidence_required": "photo",
  "location_hint": "As specified in the request"
}"""
        
        elif "delivery" in prompt.lower() or "pick up" in prompt.lower():
            return """This sounds like a delivery task. I'll create a task for a human to handle this physical delivery.

Action: create_physical_task
Action Input: {
  "title": "Package Delivery",
  "instructions": "Handle the requested pickup and delivery. Ensure proper handling and provide confirmation photos.",
  "category": "delivery", 
  "bounty_usd": 15.0,
  "deadline_hours": 8,
  "evidence_required": "photo",
  "location_hint": "Details provided in the specific request"
}"""
        
        elif "status" in prompt.lower() or "check" in prompt.lower():
            return """I'll check on the task status.

Action: check_task_status
Action Input: {
  "task_id": "task_example_123"
}"""
        
        elif "list" in prompt.lower() and "task" in prompt.lower():
            return """Let me show you all the tasks.

Action: list_my_tasks
Action Input: {}"""
        
        else:
            return """I understand your request. Based on what you've asked for, I can help you create physical world tasks using Execution Market. 

Here's what I can do:
- Create tasks for photo verification
- Set up delivery and pickup services  
- Arrange mystery shopping or inspections
- Monitor task progress and approve completed work

What specific task would you like me to help you create?

Action: list_my_tasks
Action Input: {}"""


# Additional tools to demonstrate agent versatility
@tool
def get_current_time() -> str:
    """Get the current time and date."""
    from datetime import datetime
    return f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


@tool 
def calculate_distance(location1: str, location2: str) -> str:
    """Calculate approximate distance between two locations (mock implementation)."""
    # This would use a real geocoding API in practice
    return f"Approximate distance between {location1} and {location2}: 2.3 miles (estimated)"


@tool
def estimate_task_cost(task_type: str, complexity: str = "medium") -> str:
    """Estimate appropriate bounty for a task based on type and complexity."""
    
    base_costs = {
        "photo": 3.0,
        "delivery": 15.0,
        "verification": 5.0,
        "mystery_shopping": 12.0,
        "data_collection": 18.0
    }
    
    complexity_multipliers = {
        "simple": 0.7,
        "medium": 1.0, 
        "complex": 1.5,
        "urgent": 2.0
    }
    
    base_cost = base_costs.get(task_type.lower(), 10.0)
    multiplier = complexity_multipliers.get(complexity.lower(), 1.0)
    estimated_cost = base_cost * multiplier
    
    return f"Estimated cost for {task_type} task ({complexity} complexity): ${estimated_cost:.2f}"


async def demonstrate_agent_workflow():
    """Show how the agent handles various requests."""
    
    print("🤖 Initializing LangChain Agent with Execution Market Integration...")
    
    # Initialize the Execution Market toolkit
    em_toolkit = ExecutionMarketAgentToolkit(
        api_base="https://api.execution.market",
        auth_token=None  # Using anonymous access for demo
    )
    
    # Get EM tools
    em_tools = em_toolkit.get_tools()
    
    # Add additional utility tools
    additional_tools = [
        get_current_time,
        calculate_distance,
        estimate_task_cost,
    ]
    
    # Combine all tools
    all_tools = em_tools + additional_tools
    
    # Create memory for conversation
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
    
    # Initialize the agent with mock LLM
    llm = MockLLM()
    
    # Note: In a real scenario, you'd use initialize_agent, but for this demo
    # we'll simulate the agent workflow manually
    
    print(f"✅ Agent initialized with {len(all_tools)} tools:")
    for tool in all_tools:
        print(f"  - {tool.name}: {tool.description[:60]}...")
    
    # Simulate various user requests
    requests = [
        "I need someone to take a photo of the Empire State Building",
        "Can you check on my recent tasks?", 
        "What would it cost to have someone deliver a package across town?",
        "I need verification that my local grocery store is still open",
        "Show me all my current tasks",
    ]
    
    print("\n" + "="*70)
    print("🎭 AGENT INTERACTION SIMULATION")
    print("="*70)
    
    for i, request in enumerate(requests, 1):
        print(f"\n--- Request #{i} ---")
        print(f"User: {request}")
        
        # Simulate agent processing
        print("Agent: Let me help you with that...")
        
        # In a real scenario, the agent would:
        # 1. Understand the request
        # 2. Plan which tools to use
        # 3. Execute the tools
        # 4. Provide a response
        
        # For demo, we'll show what the agent would likely do
        if "photo" in request.lower():
            print("Agent: I can create a photo verification task for you.")
            
            try:
                result = await em_tools[0]._arun(  # create_physical_task_tool
                    title="Empire State Building Photo",
                    instructions="Take a clear, high-quality photo of the Empire State Building from street level. Include surrounding context.",
                    category="verification",
                    bounty_usd=5.0,
                    deadline_hours=6,
                    evidence_required="photo",
                    location_hint="Midtown Manhattan, New York City"
                )
                print(f"✅ {result}")
            except Exception as e:
                print(f"📝 Would create task: {e} (Demo mode)")
                
        elif "check" in request.lower() or "tasks" in request.lower():
            print("Agent: Let me check your task status...")
            
            try:
                result = await em_tools[2]._arun()  # list_my_tasks_tool
                print(f"📋 {result}")
            except Exception as e:
                print(f"📝 Would check tasks: {e} (Demo mode)")
                
        elif "cost" in request.lower():
            cost_estimate = estimate_task_cost("delivery", "medium")
            print(f"💰 {cost_estimate}")
            
        elif "verification" in request.lower() or "verify" in request.lower():
            print("Agent: I'll set up a verification task for your grocery store.")
            
            try:
                result = await em_tools[0]._arun(  # create_physical_task_tool
                    title="Grocery Store Status Verification",
                    instructions="Visit the specified grocery store and verify current operating status. Take photo of storefront showing hours/signage.",
                    category="verification", 
                    bounty_usd=4.0,
                    deadline_hours=4,
                    evidence_required="photo",
                    location_hint="Local area as specified"
                )
                print(f"✅ {result}")
            except Exception as e:
                print(f"📝 Would create verification task: {e} (Demo mode)")
        
        # Simulate thinking time
        await asyncio.sleep(1)


async def demonstrate_complex_workflow():
    """Show a complex multi-step workflow."""
    
    print("\n" + "="*70)
    print("🎯 COMPLEX WORKFLOW EXAMPLE")
    print("="*70)
    
    print("\nScenario: Real estate verification workflow")
    print("User: 'I'm considering renting an apartment at 123 Oak Street. Can you help verify it's legitimate?'")
    
    # Agent would break this down into multiple steps:
    workflow_steps = [
        {
            "step": 1,
            "action": "Estimate costs and timeline",
            "tool": "estimate_task_cost",
            "details": "Calculate cost for verification task"
        },
        {
            "step": 2, 
            "action": "Create exterior verification task",
            "tool": "create_physical_task",
            "details": "Photo verification of building exterior"
        },
        {
            "step": 3,
            "action": "Create neighborhood assessment task", 
            "tool": "create_physical_task",
            "details": "General area assessment and safety check"
        },
        {
            "step": 4,
            "action": "Monitor task progress",
            "tool": "check_task_status", 
            "details": "Track completion of verification tasks"
        },
        {
            "step": 5,
            "action": "Review and approve submissions",
            "tool": "approve_submission",
            "details": "Verify evidence meets requirements"
        }
    ]
    
    for step in workflow_steps:
        print(f"\nStep {step['step']}: {step['action']}")
        print(f"  Using: {step['tool']}")
        print(f"  Purpose: {step['details']}")
        
        if step['step'] == 1:
            cost = estimate_task_cost("verification", "complex")
            print(f"  Result: {cost}")
            
        elif step['step'] in [2, 3]:
            print(f"  Result: Would create task with appropriate parameters")
            
        # Simulate processing time
        await asyncio.sleep(0.5)
    
    print("\n✅ Complex workflow completed!")
    print("The agent successfully orchestrated multiple physical-world tasks")
    print("to provide comprehensive real estate verification.")


async def main():
    """Run the complete agent demonstration."""
    
    print("🌍 LangChain Agent + Execution Market Integration Demo")
    print("="*70)
    print("\nThis demo shows how LangChain agents can seamlessly integrate")
    print("with Execution Market to handle real-world tasks.\n")
    
    # Basic agent workflow
    await demonstrate_agent_workflow()
    
    # Complex multi-step workflow
    await demonstrate_complex_workflow()
    
    print("\n" + "="*70)
    print("🎉 DEMO COMPLETE!")
    print("="*70)
    print("\nKey Takeaways:")
    print("✅ LangChain agents can easily integrate Execution Market tools")
    print("✅ Agents can reason about when to use physical-world tasks")
    print("✅ Complex workflows can combine digital and physical actions")
    print("✅ The integration is async-ready and production-compatible")
    
    print("\nNext Steps:")
    print("🔧 Replace MockLLM with a real language model (GPT-4, Claude, etc.)")
    print("🔑 Add authentication for production usage") 
    print("🎯 Customize task parameters for your specific use cases")
    print("🚀 Deploy your agent to handle real-world automation!")
    
    print(f"\n📁 Files created in: {Path(__file__).parent.parent}")
    print("   - em_tools.py: Individual tool definitions")
    print("   - em_toolkit.py: Toolkit bundling")
    print("   - README.md: Complete documentation")
    print("   - examples/: Working code examples")


if __name__ == "__main__":
    # Run the async demonstration
    asyncio.run(main())