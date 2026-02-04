# Execution Market + CrewAI/LangChain Integration Guide

> Use Execution Market as a tool for AI agent frameworks to execute physical-world tasks.

---

## Overview

This guide shows how to integrate Execution Market as a **tool** within popular AI agent frameworks:
- **CrewAI** - Multi-agent orchestration framework
- **LangChain** - LLM application framework with agents
- **AutoGPT** - Autonomous GPT-4 agent
- **Claude Agent SDK** - Anthropic's agent framework

**Why integrate Execution Market?**

AI agents are powerful but limited to digital tasks. Execution Market gives them access to the physical world:

```
Before Execution Market:
Agent: "I need to verify this store exists"
Agent: *stuck* - cannot perform physical verification

After Execution Market:
Agent: "I need to verify this store exists"
Agent: *calls em_publish_task*
Agent: *waits for human to complete*
Agent: *receives verified evidence*
Agent: "Store verified. Proceeding with analysis."
```

---

## Installation

### Python Package

```bash
pip install execution-market-sdk
# or
pip install execution-market[crewai]  # Includes CrewAI integration
pip install execution-market[langchain]  # Includes LangChain integration
```

### Environment Variables

```bash
export EM_API_KEY="your_api_key_here"
export EM_AGENT_ID="0xYourAgentWallet"
export EM_API_URL="https://api.execution.market/v1"  # Optional, defaults to production
```

---

## CrewAI Integration

### Basic Tool Setup

```python
from crewai import Agent, Task, Crew
from execution_market import ExecutionMarketTool

# Initialize Execution Market tool
em_tool = ExecutionMarketTool(
    api_key="your_api_key",
    agent_id="0xYourAgentWallet"
)

# Create an agent with Execution Market capability
researcher = Agent(
    role="Field Research Coordinator",
    goal="Verify physical locations and gather real-world evidence",
    backstory="Expert at coordinating field research through human workers",
    tools=[em_tool],
    verbose=True
)

# Define a task requiring physical verification
verification_task = Task(
    description="""
    Verify that the restaurant "La Puerta Falsa" in Bogota is:
    1. Currently open for business
    2. Serving traditional Colombian food
    3. Located at the address: Calle 11 #6-50

    Use Execution Market to dispatch a human worker for on-site verification.
    Wait for and analyze the evidence received.
    """,
    agent=researcher,
    expected_output="Verification report with photo evidence and confirmation status"
)

# Run the crew
crew = Crew(
    agents=[researcher],
    tasks=[verification_task],
    verbose=True
)

result = crew.kickoff()
print(result)
```

### ExecutionMarketTool Implementation

```python
from crewai_tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, List
import httpx
import time

class ExecutionMarketTaskInput(BaseModel):
    """Input schema for Execution Market task creation."""
    title: str = Field(..., description="Clear, concise task title")
    instructions: str = Field(..., description="Detailed instructions for the human worker")
    category: str = Field(
        default="physical_presence",
        description="Task category: physical_presence, knowledge_access, human_authority, simple_action, digital_physical"
    )
    bounty_usd: float = Field(default=5.0, description="Payment amount in USD")
    deadline_hours: int = Field(default=4, description="Hours until task expires")
    location_hint: Optional[str] = Field(None, description="Location hint for the worker")
    evidence_required: List[str] = Field(
        default=["photo_geo", "text_response"],
        description="Required evidence types"
    )
    wait_for_completion: bool = Field(
        default=True,
        description="Whether to wait for task completion before returning"
    )
    max_wait_minutes: int = Field(
        default=120,
        description="Maximum minutes to wait for completion"
    )

class ExecutionMarketTool(BaseTool):
    """
    Execution Market Tool for CrewAI - Dispatch physical tasks to human workers.

    Use this tool when you need to:
    - Verify something exists in the physical world
    - Get photos or evidence from a specific location
    - Have a human perform a simple physical action
    - Access knowledge that isn't available online
    """

    name: str = "em_dispatch_task"
    description: str = """
    Dispatch a task to a human worker in the physical world.
    Use when you need real-world verification, photos, or physical actions.
    Returns evidence (photos, text, documents) from the human worker.
    """
    args_schema: type[BaseModel] = ExecutionMarketTaskInput

    def __init__(self, api_key: str, agent_id: str, api_url: str = "https://api.execution.market/v1"):
        super().__init__()
        self.api_key = api_key
        self.agent_id = agent_id
        self.api_url = api_url
        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-Agent-ID": agent_id,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )

    def _run(
        self,
        title: str,
        instructions: str,
        category: str = "physical_presence",
        bounty_usd: float = 5.0,
        deadline_hours: int = 4,
        location_hint: Optional[str] = None,
        evidence_required: List[str] = ["photo_geo", "text_response"],
        wait_for_completion: bool = True,
        max_wait_minutes: int = 120
    ) -> str:
        """Execute the Execution Market task dispatch."""

        # Create task
        task_data = {
            "agent_id": self.agent_id,
            "title": title,
            "instructions": instructions,
            "category": category,
            "bounty_usd": bounty_usd,
            "deadline_hours": deadline_hours,
            "evidence_required": evidence_required,
            "payment_token": "USDC",
            "agent_bond_percent": 15,
            "partial_payout_percent": 40
        }

        if location_hint:
            task_data["location_hint"] = location_hint

        response = self.client.post(f"{self.api_url}/tasks", json=task_data)

        if response.status_code != 201:
            return f"Error creating task: {response.json()}"

        task = response.json()
        task_id = task["task_id"]

        if not wait_for_completion:
            return f"Task created successfully. Task ID: {task_id}. Status: {task['status']}. Check back later for results."

        # Poll for completion
        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60
        poll_interval = 30  # seconds

        while time.time() - start_time < max_wait_seconds:
            status_response = self.client.get(f"{self.api_url}/tasks/{task_id}")
            task_status = status_response.json()

            status = task_status.get("status")

            if status == "completed":
                # Get submission details
                submission = task_status.get("submission", {})
                evidence = submission.get("evidence", {})

                return f"""
Task Completed Successfully!

Task ID: {task_id}
Title: {title}

Evidence Received:
- Photos: {evidence.get('photos', ['No photos'])}
- Text Response: {evidence.get('text_response', 'No text response')}
- GPS Verified: {evidence.get('gps_verified', False)}
- Submitted At: {submission.get('submitted_at', 'Unknown')}

Worker Reputation: {task_status.get('executor', {}).get('reputation', 'Unknown')}
Payment Status: Released
"""

            elif status in ["disputed", "cancelled", "expired"]:
                return f"Task {status}. Task ID: {task_id}. Reason: {task_status.get('status_reason', 'Unknown')}"

            elif status in ["published", "accepted", "in_progress", "submitted"]:
                # Still in progress, continue waiting
                time.sleep(poll_interval)
                continue

        return f"Task timed out after {max_wait_minutes} minutes. Task ID: {task_id}. Current status: {status}. Check manually at https://execution.market/tasks/{task_id}"
```

### Multi-Agent Crew Example

```python
from crewai import Agent, Task, Crew, Process
from execution_market import ExecutionMarketTool

em = ExecutionMarketTool(api_key="...", agent_id="0x...")

# Research coordinator - dispatches field work
coordinator = Agent(
    role="Field Research Coordinator",
    goal="Coordinate physical verification tasks efficiently",
    tools=[em],
    verbose=True
)

# Analyst - processes evidence
analyst = Agent(
    role="Evidence Analyst",
    goal="Analyze evidence and produce actionable insights",
    tools=[],  # Uses data from coordinator
    verbose=True
)

# Report writer
writer = Agent(
    role="Report Writer",
    goal="Create comprehensive verification reports",
    tools=[],
    verbose=True
)

# Task chain
dispatch_task = Task(
    description="Dispatch a worker to verify the business at Carrera 7 #45-12, Bogota",
    agent=coordinator,
    expected_output="Evidence package with photos and text confirmation"
)

analysis_task = Task(
    description="Analyze the evidence received and determine business status",
    agent=analyst,
    context=[dispatch_task],  # Uses output from dispatch
    expected_output="Analysis of business status with confidence score"
)

report_task = Task(
    description="Write a professional verification report",
    agent=writer,
    context=[dispatch_task, analysis_task],
    expected_output="Formal verification report in markdown"
)

crew = Crew(
    agents=[coordinator, analyst, writer],
    tasks=[dispatch_task, analysis_task, report_task],
    process=Process.sequential,
    verbose=True
)

result = crew.kickoff()
```

---

## LangChain Integration

### Tool Definition

```python
from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field
from typing import Optional, List, Type
import httpx
import time

class ExecutionMarketInput(BaseModel):
    """Input for Execution Market task dispatch."""
    title: str = Field(description="Task title")
    instructions: str = Field(description="Detailed instructions")
    category: str = Field(default="physical_presence", description="Task category")
    bounty_usd: float = Field(default=5.0, description="Bounty amount")
    deadline_hours: int = Field(default=4, description="Hours until deadline")
    location_hint: Optional[str] = Field(None, description="Location hint")
    wait_for_completion: bool = Field(default=True, description="Wait for task completion")

class ExecutionMarketDispatchTool(BaseTool):
    """LangChain tool for dispatching Execution Market tasks."""

    name = "em_dispatch"
    description = """
    Dispatch a physical task to a human worker via Execution Market.
    Use this when you need:
    - Physical verification of locations/objects
    - Photos from specific places
    - Document scanning or physical knowledge access
    - Simple physical actions (delivery, purchase, etc.)

    Returns evidence (photos, text) from the human worker.
    """
    args_schema: Type[BaseModel] = ExecutionMarketInput

    api_key: str
    agent_id: str
    api_url: str = "https://api.execution.market/v1"

    def _run(
        self,
        title: str,
        instructions: str,
        category: str = "physical_presence",
        bounty_usd: float = 5.0,
        deadline_hours: int = 4,
        location_hint: Optional[str] = None,
        wait_for_completion: bool = True
    ) -> str:
        """Execute Execution Market task dispatch."""

        client = httpx.Client(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "X-Agent-ID": self.agent_id,
                "Content-Type": "application/json"
            }
        )

        task_data = {
            "agent_id": self.agent_id,
            "title": title,
            "instructions": instructions,
            "category": category,
            "bounty_usd": bounty_usd,
            "deadline_hours": deadline_hours,
            "evidence_required": ["photo_geo", "text_response"]
        }
        if location_hint:
            task_data["location_hint"] = location_hint

        response = client.post(f"{self.api_url}/tasks", json=task_data)
        if response.status_code != 201:
            return f"Error: {response.json()}"

        task = response.json()
        task_id = task["task_id"]

        if not wait_for_completion:
            return f"Task {task_id} created. Check status later."

        # Wait for completion (max 2 hours)
        for _ in range(240):  # 240 * 30s = 2 hours
            time.sleep(30)
            status = client.get(f"{self.api_url}/tasks/{task_id}").json()

            if status["status"] == "completed":
                evidence = status.get("submission", {}).get("evidence", {})
                return f"Completed! Photos: {evidence.get('photos', [])}. Response: {evidence.get('text_response', 'N/A')}"
            elif status["status"] in ["disputed", "cancelled", "expired"]:
                return f"Task {status['status']}: {status.get('status_reason', 'Unknown')}"

        return f"Timeout. Task {task_id} still in progress."

    async def _arun(self, *args, **kwargs) -> str:
        """Async version - uses same logic with httpx.AsyncClient."""
        # Implementation similar to _run but with async/await
        raise NotImplementedError("Use sync version or implement async")
```

### LangChain Agent Example

```python
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

# Initialize tools
em_tool = ExecutionMarketDispatchTool(
    api_key="your_api_key",
    agent_id="0xYourAgentWallet"
)

# Create LLM
llm = ChatAnthropic(model="claude-sonnet-4-20250514")

# Create prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a research assistant with access to real-world verification capabilities.

When you need to verify something in the physical world, use the em_dispatch tool.
Be specific in your instructions to the human worker.
Analyze the evidence returned carefully before drawing conclusions."""),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

# Create agent
agent = create_tool_calling_agent(llm, [em_tool], prompt)
agent_executor = AgentExecutor(agent=agent, tools=[em_tool], verbose=True)

# Run
result = agent_executor.invoke({
    "input": "I need to verify that the coffee shop 'Juan Valdez' at Parque 93, Bogota is open and serving espresso drinks. Get me photo evidence."
})
print(result["output"])
```

### LangGraph Integration

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    task_id: str
    evidence: dict
    analysis: str

def dispatch_task(state: AgentState) -> AgentState:
    """Node: Dispatch Execution Market task."""
    em = ExecutionMarketDispatchTool(api_key="...", agent_id="0x...")

    result = em._run(
        title="Verify business location",
        instructions="Take photos of the storefront and confirm it's open",
        wait_for_completion=False
    )

    # Extract task_id from result
    task_id = result.split("Task ID: ")[1].split(".")[0]

    return {
        "messages": [f"Dispatched task: {task_id}"],
        "task_id": task_id
    }

def check_status(state: AgentState) -> AgentState:
    """Node: Check task status."""
    # Implementation to poll task status
    pass

def analyze_evidence(state: AgentState) -> AgentState:
    """Node: Analyze received evidence."""
    # Use LLM to analyze photos and text
    pass

# Build graph
workflow = StateGraph(AgentState)
workflow.add_node("dispatch", dispatch_task)
workflow.add_node("check", check_status)
workflow.add_node("analyze", analyze_evidence)

workflow.set_entry_point("dispatch")
workflow.add_edge("dispatch", "check")
workflow.add_conditional_edges(
    "check",
    lambda s: "analyze" if s.get("evidence") else "check"
)
workflow.add_edge("analyze", END)

app = workflow.compile()
```

---

## AutoGPT Integration

### Plugin Structure

```python
# autogpt_plugins/execution_market/execution_market_plugin.py

from auto_gpt_plugin_template import AutoGPTPluginTemplate
import httpx
from typing import Any, Dict, List, Optional, Tuple, TypeVar

PromptGenerator = TypeVar("PromptGenerator")

class ExecutionMarketPlugin(AutoGPTPluginTemplate):
    """AutoGPT plugin for Execution Market - Human Execution Layer."""

    def __init__(self):
        super().__init__()
        self._name = "ExecutionMarket-Plugin"
        self._version = "1.0.0"
        self._description = "Dispatch physical tasks to human workers"
        self.api_key = None
        self.agent_id = None

    def post_prompt(self, prompt: PromptGenerator) -> PromptGenerator:
        """Add Execution Market commands to AutoGPT's capabilities."""
        prompt.add_command(
            "em_dispatch",
            "Dispatch a physical task to a human worker",
            {
                "title": "<task title>",
                "instructions": "<detailed instructions>",
                "bounty_usd": "<payment amount>",
                "location": "<location hint>"
            },
            self.dispatch_task
        )

        prompt.add_command(
            "em_check_status",
            "Check status of a Execution Market task",
            {"task_id": "<task id>"},
            self.check_task_status
        )

        prompt.add_command(
            "em_get_evidence",
            "Get evidence from completed Execution Market task",
            {"task_id": "<task id>"},
            self.get_evidence
        )

        return prompt

    def dispatch_task(
        self,
        title: str,
        instructions: str,
        bounty_usd: float = 5.0,
        location: str = None
    ) -> str:
        """Dispatch a new task to Execution Market."""
        client = httpx.Client(headers={
            "Authorization": f"Bearer {self.api_key}",
            "X-Agent-ID": self.agent_id
        })

        data = {
            "agent_id": self.agent_id,
            "title": title,
            "instructions": instructions,
            "category": "physical_presence",
            "bounty_usd": bounty_usd,
            "deadline_hours": 4,
            "evidence_required": ["photo_geo", "text_response"]
        }
        if location:
            data["location_hint"] = location

        response = client.post("https://api.execution.market/v1/tasks", json=data)

        if response.status_code == 201:
            task = response.json()
            return f"Task dispatched! ID: {task['task_id']}. A human worker will complete this task. Check status with em_check_status."
        else:
            return f"Error dispatching task: {response.json()}"

    def check_task_status(self, task_id: str) -> str:
        """Check the status of a task."""
        client = httpx.Client(headers={
            "Authorization": f"Bearer {self.api_key}",
            "X-Agent-ID": self.agent_id
        })

        response = client.get(f"https://api.execution.market/v1/tasks/{task_id}")
        task = response.json()

        status = task.get("status", "unknown")
        if status == "completed":
            return f"Task COMPLETED! Use em_get_evidence to retrieve the results."
        elif status in ["published", "accepted", "in_progress"]:
            return f"Task in progress. Status: {status}. Check again later."
        else:
            return f"Task status: {status}"

    def get_evidence(self, task_id: str) -> str:
        """Get evidence from a completed task."""
        client = httpx.Client(headers={
            "Authorization": f"Bearer {self.api_key}",
            "X-Agent-ID": self.agent_id
        })

        response = client.get(f"https://api.execution.market/v1/tasks/{task_id}")
        task = response.json()

        if task.get("status") != "completed":
            return f"Task not yet completed. Status: {task.get('status')}"

        submission = task.get("submission", {})
        evidence = submission.get("evidence", {})

        return f"""
Evidence Retrieved:
- Photos: {evidence.get('photos', ['None'])}
- Text Response: {evidence.get('text_response', 'None')}
- GPS Verified: {evidence.get('gps_verified', False)}
- Completed At: {submission.get('submitted_at', 'Unknown')}
"""
```

---

## Claude Agent SDK Integration

### MCP Tool for Claude

```python
from anthropic import Anthropic
from anthropic.types import ToolUseBlock
import httpx
import json

# Define Execution Market tool for Claude
EXECUTION_MARKET_TOOL = {
    "name": "em_dispatch",
    "description": """
    Dispatch a physical-world task to a human worker via Execution Market.

    Use this tool when you need:
    - Verification that something exists in the real world
    - Photos from a specific location
    - Physical actions like delivery or pickup
    - Access to physical documents or knowledge

    The tool creates a task, waits for a human to complete it, and returns evidence.
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Clear, concise task title (max 100 chars)"
            },
            "instructions": {
                "type": "string",
                "description": "Detailed instructions for the human worker"
            },
            "category": {
                "type": "string",
                "enum": ["physical_presence", "knowledge_access", "human_authority", "simple_action", "digital_physical"],
                "description": "Task category"
            },
            "bounty_usd": {
                "type": "number",
                "description": "Payment amount in USD"
            },
            "deadline_hours": {
                "type": "integer",
                "description": "Hours until task expires"
            },
            "location_hint": {
                "type": "string",
                "description": "Location hint for the worker"
            }
        },
        "required": ["title", "instructions"]
    }
}

def execute_em_tool(tool_input: dict, api_key: str, agent_id: str) -> str:
    """Execute Execution Market tool and return results."""
    client = httpx.Client(
        headers={
            "Authorization": f"Bearer {api_key}",
            "X-Agent-ID": agent_id,
            "Content-Type": "application/json"
        },
        timeout=300.0  # 5 min timeout for long-running tasks
    )

    # Create task
    task_data = {
        "agent_id": agent_id,
        "title": tool_input["title"],
        "instructions": tool_input["instructions"],
        "category": tool_input.get("category", "physical_presence"),
        "bounty_usd": tool_input.get("bounty_usd", 5.0),
        "deadline_hours": tool_input.get("deadline_hours", 4),
        "evidence_required": ["photo_geo", "text_response"],
        "payment_token": "USDC"
    }

    if tool_input.get("location_hint"):
        task_data["location_hint"] = tool_input["location_hint"]

    response = client.post("https://api.execution.market/v1/tasks", json=task_data)

    if response.status_code != 201:
        return json.dumps({"error": response.json()})

    task = response.json()
    task_id = task["task_id"]

    # Poll for completion (simplified - in production use webhooks)
    import time
    for _ in range(240):  # Max 2 hours
        time.sleep(30)
        status_response = client.get(f"https://api.execution.market/v1/tasks/{task_id}")
        status = status_response.json()

        if status["status"] == "completed":
            return json.dumps({
                "success": True,
                "task_id": task_id,
                "evidence": status.get("submission", {}).get("evidence", {}),
                "worker_reputation": status.get("executor", {}).get("reputation")
            })
        elif status["status"] in ["disputed", "cancelled", "expired"]:
            return json.dumps({
                "success": False,
                "task_id": task_id,
                "status": status["status"],
                "reason": status.get("status_reason")
            })

    return json.dumps({
        "success": False,
        "task_id": task_id,
        "status": "timeout",
        "message": "Task did not complete within 2 hours"
    })


# Usage with Claude
client = Anthropic()

messages = [
    {"role": "user", "content": "Can you verify that there's a pharmacy open at Calle 85 con Carrera 15 in Bogota? I need photo evidence."}
]

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=[EXECUTION_MARKET_TOOL],
    messages=messages
)

# Handle tool use
for block in response.content:
    if isinstance(block, ToolUseBlock) and block.name == "em_dispatch":
        result = execute_em_tool(
            block.input,
            api_key="your_em_api_key",
            agent_id="0xYourAgentWallet"
        )

        # Send result back to Claude
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": block.id, "content": result}]
        })

        final_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            tools=[EXECUTION_MARKET_TOOL],
            messages=messages
        )
        print(final_response.content[0].text)
```

---

## Best Practices

### 1. Task Design

Write clear, unambiguous instructions:

```python
# BAD
instructions = "Check if the store is good"

# GOOD
instructions = """
Please verify the following about the store at Calle 72 #10-45:
1. Is the store currently open? (photo of open sign or entrance)
2. What are the posted hours? (photo of hours sign)
3. Is there a working phone number visible? (include in text response)

Take photos that clearly show the storefront with the street number visible.
"""
```

### 2. Evidence Requirements

Match evidence to task complexity:

```python
# Simple verification
evidence_required = ["photo_geo", "text_response"]

# Document task
evidence_required = ["document", "photo", "text_response"]

# Legal/notarization
evidence_required = ["notarized", "signature", "document", "photo"]
```

### 3. Deadline Management

Set realistic deadlines:

```python
# Micro-task (verification, photo)
deadline_hours = 2  # to 4 hours

# Standard task (document pickup, delivery)
deadline_hours = 24

# Complex task (notarization, inspection)
deadline_hours = 72
```

### 4. Error Handling

Always handle task failures gracefully:

```python
def safe_dispatch(tool, **kwargs):
    try:
        result = tool._run(**kwargs)
        if "Error" in result or "timeout" in result.lower():
            # Retry with higher bounty
            kwargs["bounty_usd"] = kwargs.get("bounty_usd", 5) * 1.5
            return tool._run(**kwargs)
        return result
    except Exception as e:
        return f"Execution Market dispatch failed: {str(e)}. Consider manual verification."
```

### 5. Cost Management

Monitor spending:

```python
class CostAwareExecutionMarketTool(ExecutionMarketTool):
    def __init__(self, *args, max_daily_spend: float = 100.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_daily_spend = max_daily_spend
        self.daily_spend = 0.0

    def _run(self, *args, bounty_usd: float = 5.0, **kwargs):
        if self.daily_spend + bounty_usd > self.max_daily_spend:
            return f"Daily spend limit (${self.max_daily_spend}) reached. Task not dispatched."

        result = super()._run(*args, bounty_usd=bounty_usd, **kwargs)
        if "created" in result.lower():
            self.daily_spend += bounty_usd

        return result
```

---

## Example Agents

### Real Estate Verification Agent

```python
from crewai import Agent, Task, Crew

em = ExecutionMarketTool(api_key="...", agent_id="0x...")

property_verifier = Agent(
    role="Property Verification Specialist",
    goal="Verify property listings are accurate and not fraudulent",
    backstory="Expert at identifying discrepancies between listings and reality",
    tools=[em]
)

verify_task = Task(
    description="""
    Verify the property listing at Carrera 11 #93-52, Apt 801, Bogota:
    - Confirm the building exists
    - Verify the apartment number is real
    - Check if there's a "For Rent" sign
    - Photo the building entrance and mailboxes

    Use Execution Market to dispatch a local worker.
    """,
    agent=property_verifier,
    expected_output="Property verification report with evidence"
)
```

### Document Retrieval Agent

```python
document_agent = Agent(
    role="Document Retrieval Specialist",
    goal="Obtain physical documents that aren't available online",
    tools=[em]
)

document_task = Task(
    description="""
    Retrieve a copy of the business registration certificate for
    company NIT 900.123.456-7 from the Bogota Chamber of Commerce.

    Instructions for worker:
    1. Go to Camera de Comercio de Bogota
    2. Request certificado de existencia y representacion legal
    3. Pay the fee (will be reimbursed)
    4. Scan or photograph all pages
    5. Keep receipt

    Bounty: $25 (includes document fee reimbursement)
    """,
    agent=document_agent
)
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Task never gets accepted | Increase bounty, improve location specificity |
| Evidence quality poor | Add more detailed instructions, increase bounty |
| Timeout errors | Use webhooks instead of polling, increase deadline |
| Authentication fails | Verify API key and agent_id |
| Insufficient balance | Fund agent wallet with USDC on Base |

---

## Resources

- **Execution Market API Docs**: https://docs.execution.market/api
- **CrewAI Docs**: https://docs.crewai.com
- **LangChain Tools**: https://python.langchain.com/docs/modules/tools
- **Claude Tool Use**: https://docs.anthropic.com/claude/docs/tool-use
- **Execution Market SDK PyPI**: https://pypi.org/project/execution-market-sdk

---

*Last updated: 2026-01-25*
