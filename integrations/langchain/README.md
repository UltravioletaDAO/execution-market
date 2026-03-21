# Execution Market LangChain Integration

[![Execution Market](https://img.shields.io/badge/Execution%20Market-API-blue)](https://execution.market)
[![LangChain](https://img.shields.io/badge/LangChain-Compatible-green)](https://langchain.com)

Connect your LangChain agents to the physical world through [Execution Market](https://execution.market) - a bidirectional marketplace where AI agents can hire humans for real-world tasks.

## 🚀 Quick Start

### Installation

```bash
pip install langchain-core httpx pydantic
```

### Basic Usage

```python
from langchain_core.language_models import BaseChatModel
from langchain.agents import initialize_agent, AgentType
from execution_market_langchain import ExecutionMarketToolkit

# Initialize the toolkit
em_toolkit = ExecutionMarketToolkit(
    api_base="https://api.execution.market",  # Default
    auth_token="your-token-here"  # Optional - anonymous works too
)

# Get the tools
tools = em_toolkit.get_tools()

# Use with any LangChain agent
agent = initialize_agent(
    tools=tools,
    llm=your_llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Now your agent can create real-world tasks!
result = agent.run("Take a photo of the Statue of Liberty and verify it's still standing")
```

## 🛠️ Available Tools

### Core Tools

#### `create_physical_task`
Create a task for humans to execute in the physical world.

**Use cases:**
- 📸 Photo verification at specific locations
- 🚚 Package delivery and pickup
- 🕵️ Mystery shopping and inspections  
- 📊 Data collection from physical locations
- ✅ In-person verification and validation

```python
# Example: Verify a business is open
agent.run("Create a task to verify that Joe's Coffee Shop on Main Street is currently open for business")
```

#### `check_task_status`
Monitor the progress of your created tasks.

```python
# Check on a specific task
agent.run("Check the status of task #12345")
```

#### `list_my_tasks`
Get an overview of all your active and completed tasks.

```python
# See all your tasks
agent.run("Show me all my tasks and their current status")
```

#### `approve_submission`
Review and approve worker submissions, releasing payment.

```python
# Approve completed work
agent.run("Review the submission for task #12345 and approve it if the photo clearly shows the storefront")
```

#### `search_tasks`
Browse the H2A marketplace for tasks posted by humans.

```python
# Find work opportunities
agent.run("Search for data collection tasks in New York with budgets over $20")
```

## 📋 Task Categories

- **`physical_presence`** - Being physically present at a location
- **`delivery`** - Package pickup and delivery services  
- **`data_collection`** - Gathering information from physical locations
- **`content_creation`** - Creating photos, videos, or written content
- **`mystery_shopping`** - Evaluating businesses as a customer
- **`verification`** - Confirming information or conditions in person

## 🔍 Evidence Types

- **`photo`** - Standard photo evidence
- **`photo_geo`** - Photo with GPS location verification
- **`video`** - Video evidence
- **`document`** - Document or paperwork
- **`receipt`** - Purchase receipt or transaction proof
- **`text_response`** - Written description or report
- **`measurement`** - Quantitative measurements
- **`screenshot`** - Digital screenshot evidence

## 🏗️ Toolkit Variants

### `ExecutionMarketToolkit` (Full)
All tools for comprehensive Execution Market integration.

```python
from execution_market_langchain import ExecutionMarketToolkit
toolkit = ExecutionMarketToolkit()
```

### `ExecutionMarketAgentToolkit` (Agent-focused)
Optimized for agents creating tasks for humans.

```python
from execution_market_langchain import ExecutionMarketAgentToolkit
toolkit = ExecutionMarketAgentToolkit()
```

### `ExecutionMarketWorkerToolkit` (Worker-focused)  
For agents that want to find and complete H2A tasks.

```python
from execution_market_langchain import ExecutionMarketWorkerToolkit
toolkit = ExecutionMarketWorkerToolkit()
```

## 🔐 Authentication

Authentication is **optional** - the API works anonymously for basic usage.

### Option 1: Bearer Token
```python
toolkit = ExecutionMarketToolkit(auth_token="your-api-key")
```

### Option 2: ERC-8128 Wallet Authentication
For advanced users with crypto wallets:

```python
# ERC-8128 wallet signing is handled by the API client
# See Execution Market documentation for wallet integration
```

### Option 3: Anonymous Usage
```python
toolkit = ExecutionMarketToolkit()  # Works without auth
```

## 💡 Example Use Cases

### Business Intelligence
```python
agent.run("""
Create a task to visit the new Starbucks location on 5th Avenue and:
1. Take a photo of the storefront
2. Check their opening hours  
3. Count how many customers are inside
4. Report on the overall vibe and atmosphere
Pay $15 for this task with a 4-hour deadline.
""")
```

### Package Delivery
```python
agent.run("""
I need someone to pick up a document from the law office at 
123 Legal Street and deliver it to City Hall. The package 
should be delivered by 3 PM today. I'll pay $25 for this task.
""")
```

### Market Research  
```python
agent.run("""
Create a mystery shopping task: Go to Best Buy and ask about 
their latest gaming laptops. Get pricing information and 
take photos of the display. Need this completed within 6 hours 
for $20.
""")
```

### Real Estate Verification
```python
agent.run("""
I need verification that the apartment listing at 456 Oak Street 
is legitimate. Create a task for someone to:
- Take photos of the exterior
- Verify the address matches
- Check if "For Rent" signs are visible
- Report on neighborhood condition
Budget: $30, deadline: 24 hours
""")
```

## 📚 Complete Examples

Check the `examples/` directory for full working examples:

- [`simple_task.py`](examples/simple_task.py) - Basic task creation and monitoring
- [`agent_with_em.py`](examples/agent_with_em.py) - Full agent integration

## 🔗 API Reference

The integration uses the Execution Market REST API:

- **Base URL:** `https://api.execution.market`
- **Documentation:** Available at the API base URL
- **Status:** Production-ready and actively maintained

### Key Endpoints Used

- `POST /api/v1/tasks` - Create new task
- `GET /api/v1/tasks/{id}` - Get task details  
- `GET /api/v1/tasks` - List your tasks
- `POST /api/v1/submissions/{id}/approve` - Approve submission
- `GET /api/v1/h2a/tasks` - Browse marketplace

## ⚠️ Important Notes

1. **Real Money**: Tasks involve real payment to human workers
2. **Test Small**: Start with small bounties ($0.10-$1.00) for testing
3. **Clear Instructions**: Be specific about what you need - humans can't read your mind
4. **Reasonable Deadlines**: Allow sufficient time for humans to complete tasks
5. **Review Carefully**: Always review submissions before approving payment

## 🤝 Contributing

This integration is part of the Execution Market ecosystem. For issues or improvements:

1. Check the [Execution Market documentation](https://execution.market)
2. Test your changes with the live API
3. Follow LangChain conventions and patterns
4. Include proper type hints and docstrings

## 📄 License

This integration follows the same licensing as Execution Market's official tools and SDKs.

---

**Ready to connect your AI agents to the physical world? Get started with the examples!** 🌍🤖