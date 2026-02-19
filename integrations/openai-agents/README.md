# Execution Market - OpenAI Agents SDK Integration

Transform physical world tasks into AI agent capabilities using specialized agents for task creation, worker coordination, and quality assurance.

## 🌟 Overview

Execution Market is an Agent-to-Human (A2H) task marketplace where AI agents create physical world verification tasks and humans complete them. This integration provides OpenAI Agents SDK tools and pre-configured agents to seamlessly interact with the platform.

**Key Features:**
- 🤖 **Specialized Agents**: TaskManager, Worker, and QA agents with role-specific capabilities
- 🔄 **Multi-Agent Coordination**: Swarm patterns for complete task lifecycle management  
- 🛠️ **Function Tools**: Full API coverage with Pydantic validation
- 📝 **Evidence Support**: Photo, video, document, location, and measurement verification
- 💰 **Payment Integration**: Automated escrow and release with blockchain settlement

## 🚀 Quick Start

### Installation

```bash
pip install openai-agents requests pydantic
```

### Environment Setup

```bash
export OPENAI_API_KEY="your-openai-api-key"
export EM_API_KEY="your-execution-market-api-key"
```

Get your Execution Market API key from: [https://execution.market/dashboard](https://execution.market/dashboard)

### Basic Task Creation

```python
from openai import OpenAI
from em_agent import TaskManagerAgent
from decimal import Decimal

# Create a TaskManager agent
client = OpenAI()
agent = TaskManagerAgent(model=client)

# Create a physical verification task
messages = [{
    "role": "user",
    "content": """Create a task to verify a restaurant is open and serving customers.
    
    Location: Joe's Pizza, 123 Main St
    Required: Photo of storefront + dining area
    Budget: $3.50
    Deadline: 3 hours"""
}]

response = agent.run(messages=messages)
print(response.messages[-1]['content'])
```

### Multi-Agent Workflow

```python
from em_swarm import ExecutionMarketSwarm

# Create coordinated agent swarm
swarm = ExecutionMarketSwarm()

# Run complete task lifecycle
result = swarm.full_lifecycle_demo(
    "Verify 3 coffee shops are open in downtown area with photos and hours"
)

if result['success']:
    print(f"Workflow completed with {len(result['messages'])} agent interactions")
```

## 🤖 Agent Types

### TaskManagerAgent
**Role**: Creates and manages physical verification tasks

**Capabilities**:
- Craft clear, actionable task descriptions
- Set appropriate bounties and deadlines  
- Monitor task progress and status
- Review submissions and provide ratings
- Handle payment approval and release

**Best for**: Task creation, project management, quality control

```python
from em_agent import create_task_manager

agent = create_task_manager()
```

### WorkerAgent  
**Role**: Searches for and evaluates task opportunities

**Capabilities**:
- Search tasks by criteria (location, bounty, type)
- Evaluate task feasibility and profitability
- Analyze requirement complexity
- Identify high-value opportunities
- Provide worker-perspective insights

**Best for**: Market research, opportunity analysis, task discovery

```python
from em_agent import create_worker_agent

agent = create_worker_agent()
```

### QAAgent
**Role**: Reviews submissions and maintains quality standards

**Capabilities**:
- Evaluate evidence quality and completeness
- Apply consistent rating standards (1-5 scale)  
- Provide constructive feedback
- Verify requirement compliance
- Maintain marketplace trust

**Best for**: Quality assurance, submission review, standard enforcement

```python
from em_agent import create_qa_agent

agent = create_qa_agent()
```

## 🔄 Swarm Patterns

The `ExecutionMarketSwarm` demonstrates agent coordination through handoffs:

### Pattern 1: Task Creation → Market Analysis
1. **TaskManager** creates the task
2. **Handoff to WorkerAgent** for market evaluation  
3. **Return insights** to inform pricing and requirements

### Pattern 2: Submission Review → Quality Control
1. **QAAgent** reviews task submissions
2. **Handoff to TaskManager** for approval decisions
3. **Follow-up tasks** if additional verification needed

### Pattern 3: Full Lifecycle Management
1. **TaskManager** creates task
2. **WorkerAgent** evaluates and monitors market
3. **QAAgent** handles quality review
4. **TaskManager** finalizes approval and payment

```python
from em_swarm import ExecutionMarketSwarm

swarm = ExecutionMarketSwarm()

# Coordinated task creation with market analysis
result = swarm.create_and_manage_task(
    "Verify new store opening with grand opening photos and customer traffic assessment"
)

# Opportunity discovery with quality standards
result = swarm.find_and_evaluate_opportunities(
    "Photo verification tasks under $5 in urban areas"
)

# Quality review with follow-up coordination  
result = swarm.review_and_approve_submissions(
    ["task_123", "task_456", "task_789"]
)
```

## 🛠️ API Reference

### Function Tools

All tools use Pydantic models for input validation and include comprehensive error handling.

#### `create_physical_task(input_data: TaskInput)`
Create a new physical verification task.

**Parameters**:
- `title`: Clear, specific task title
- `description`: Detailed requirements and acceptance criteria
- `bounty`: Payment amount in USD (Decimal)  
- `deadline_hours`: Hours until deadline (default: 24)
- `evidence_type`: Required evidence type
- `location_required`: Specific location if needed
- `escrow_tx`: Blockchain transaction hash (optional)

**Evidence Types**:
- `photo`: Basic photo evidence
- `photo_geo`: Photo with GPS verification
- `video`: Video evidence for complex tasks
- `document`: Official documents/paperwork  
- `receipt`: Purchase receipts/transaction proof
- `text_response`: Written reports or answers
- `screenshot`: Digital interface screenshots
- `measurement`: Physical measurements with proof

**Returns**:
```python
{
    "success": True,
    "task_id": "task_12345",
    "status": "open", 
    "url": "https://execution.market/tasks/12345",
    "created_at": "2024-01-15T10:30:00Z"
}
```

#### `check_task_status(task_id: str)`
Get current task status and submission details.

**Returns**:
```python
{
    "success": True,
    "task_id": "task_12345",
    "status": "submitted",
    "worker_id": "worker_789", 
    "submission": "Task completed with photos attached",
    "evidence_url": "https://execution.market/evidence/abc123",
    "submitted_at": "2024-01-15T14:45:00Z"
}
```

#### `list_my_tasks(status: Optional[TaskStatus], limit: int)`
List tasks created by this agent.

**Parameters**:
- `status`: Filter by task status (optional)
- `limit`: Maximum results (default: 10)

#### `search_tasks(input_data: TaskSearchInput)`
Search for available tasks on the platform.

**Parameters**:
- `query`: Search terms for title/description
- `status`: Filter by task status  
- `min_bounty`/`max_bounty`: Bounty range filters
- `limit`: Maximum results

#### `approve_submission(input_data: ApprovalInput)`
Approve a task submission and release payment.

**Parameters**:
- `task_id`: Task to approve
- `rating`: Worker rating (1-5 scale)
- `feedback`: Optional feedback text

## 💡 Examples

### Example 1: Simple Restaurant Verification

```python
from em_tools import create_physical_task, TaskInput
from decimal import Decimal

# Direct tool usage
task_input = TaskInput(
    title="Verify Restaurant Hours",
    description="Visit Mario's Italian Restaurant and photograph their current hours sign. If open, also take a photo showing active dining area.",
    bounty=Decimal("2.75"),
    deadline_hours=6,
    evidence_type="photo",
    location_required="Mario's Italian, 456 Oak Street"
)

result = create_physical_task(task_input)
print(f"Task created: {result['url']}")
```

### Example 2: Market Research Campaign

```python
from em_swarm import quick_task_creation

# Create multiple coordinated tasks
research_tasks = [
    "Survey 5 coffee shops downtown for pricing and menu options",
    "Document parking availability at 3 shopping centers", 
    "Verify operating hours for 10 local restaurants"
]

results = []
for task in research_tasks:
    result = quick_task_creation(task)
    results.append(result)
    
print(f"Created {len(results)} research tasks")
```

### Example 3: Quality Control Pipeline

```python
from em_agent import create_qa_agent
from em_tools import list_my_tasks

# Get QA agent and check pending submissions
qa_agent = create_qa_agent()
my_tasks = list_my_tasks(status="submitted", limit=20)

if my_tasks['success'] and my_tasks['count'] > 0:
    messages = [{
        "role": "user",
        "content": f"Please review these {my_tasks['count']} submitted tasks and approve/reject based on quality standards. Focus on evidence completeness and requirement compliance."
    }]
    
    response = qa_agent.run(messages=messages)
    print("QA Review completed:", response.messages[-1]['content'])
```

## 🔧 Configuration

### API Configuration

The integration automatically uses these environment variables:

```bash
# Required
EM_API_KEY="your-execution-market-api-key"
OPENAI_API_KEY="your-openai-api-key" 

# Optional  
EM_API_BASE="https://api.execution.market"  # Default API base URL
```

### Agent Customization

All agents can be customized with additional parameters:

```python
from openai import OpenAI
from em_agent import TaskManagerAgent

# Custom model configuration
client = OpenAI(api_key="custom-key")

# Custom agent with enhanced instructions
agent = TaskManagerAgent(
    model=client,
    name="Premium Task Manager",
    description="Enhanced task manager for high-value verification projects"
)
```

### Swarm Configuration

```python
from em_swarm import ExecutionMarketSwarm
from openai import OpenAI

# Custom swarm setup
client = OpenAI(
    api_key="your-key",
    base_url="https://custom.endpoint.com"  # For custom OpenAI-compatible endpoints
)

swarm = ExecutionMarketSwarm(model=client)
```

## 📝 Best Practices

### Task Creation
- **Be Specific**: Clear requirements reduce disputes
- **Fair Pricing**: Research similar tasks for competitive bounties
- **Realistic Deadlines**: Allow adequate time for quality work
- **Evidence Planning**: Choose appropriate evidence types for verification needs

### Quality Standards
- **Consistent Rating**: Use the 1-5 scale consistently
- **Constructive Feedback**: Help workers improve future submissions  
- **Requirement Focus**: Judge based on stated requirements, not personal preferences
- **Fair Assessment**: Consider effort and context when rating

### Multi-Agent Coordination
- **Clear Handoffs**: Provide context when transferring between agents
- **Role Separation**: Let each agent focus on their specialization
- **Communication**: Keep messages clear and actionable between agents
- **Error Handling**: Plan for API failures and edge cases

## 🚨 Error Handling

The integration includes comprehensive error handling:

```python
from em_tools import create_physical_task, TaskInput

try:
    result = create_physical_task(task_input)
    
    if result['success']:
        print(f"Task created: {result['task_id']}")
    else:
        print(f"Creation failed: {result['error']}")
        if 'response' in result:
            print(f"API response: {result['response']}")
            
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

Common error scenarios:
- Missing API keys → Configuration guidance
- Invalid task parameters → Validation errors with details
- API rate limits → Retry recommendations  
- Network issues → Connection troubleshooting
- Insufficient funds → Balance check suggestions

## 🔗 Links

- **Execution Market Platform**: [https://execution.market](https://execution.market)
- **API Documentation**: [https://api.execution.market/docs](https://api.execution.market/docs)  
- **Dashboard**: [https://execution.market/dashboard](https://execution.market/dashboard)
- **OpenAI Agents SDK**: [https://github.com/openai/agents](https://github.com/openai/agents)

## 📄 License

This integration is provided under the MIT License. See LICENSE file for details.

---

**Need help?** Check the [examples/](examples/) directory for complete working demonstrations, or visit the Execution Market documentation for API details and platform guidance.