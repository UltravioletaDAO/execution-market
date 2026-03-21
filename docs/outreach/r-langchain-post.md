# Give your LangChain agent hands: Physical world task execution

Your LangChain agent can analyze data, write code, and reason through problems. But what happens when it needs to verify that a restaurant is actually open? Take a photo of a damaged package? Check if a billboard matches the mockup?

Until now: "Sorry, I can't do physical tasks."

## Introducing Execution Market for LangChain

We built a bridge between your agents and humans who can execute physical-world tasks. Your agent posts a task, humans bid on it, work gets done, agent receives proof.

```python
pip install execution-market-langchain
```

## 5-line quickstart

```python
from execution_market_langchain import ExecutionMarketTool

# Add to your agent's toolkit
em_tool = ExecutionMarketTool(api_key="your_key")
tools = [em_tool, ...your_other_tools...]

# Your agent can now create tasks like:
# "Take a photo of 123 Main St storefront and confirm it's open"
# "Verify this QR code works by scanning it with a phone"
# "Deliver this package to the address and get signature confirmation"
```

## What tasks can your agent create?

- **Verification**: Is this business actually open? Does this address exist?
- **Documentation**: Photo evidence of deliveries, damage, installations
- **Research**: What's the crowd like at this location? Price check competitors
- **Delivery**: Get something from point A to point B with proof of completion
- **Testing**: Does this app work on a real device? Is this QR code scannable?

## How it works

1. Your agent calls the tool with task details and bounty amount
2. Human workers bid on the task
3. Worker completes task and submits evidence (photos, videos, receipts)
4. Your agent receives structured proof data to continue its workflow
5. Payment released automatically

## Real example from our tests

```python
# Agent needs to verify a restaurant for a food delivery route optimizer
task = {
    "title": "Verify restaurant hours and menu prices",
    "description": "Go to Tony's Pizza (123 Oak St) and confirm: 1) Actually open at 6pm on weekdays, 2) Large pizza price, 3) Photo of current menu",
    "bounty_usd": 15.00,
    "evidence_required": ["photo", "text_response"]
}

# 23 minutes later...
result = agent.get_task_result(task_id)
# Returns: photos of menu, confirmed hours, price data
```

The marketplace handles escrow, dispute resolution, and worker reputation. Your agent just focuses on getting things done.

## Why this matters

LangChain agents are incredibly powerful at reasoning and tool use, but they've been trapped in the digital realm. Physical world verification was always a manual bottleneck.

Now your supply chain agent can verify deliveries. Your restaurant research agent can check real prices. Your property management agent can get photos of maintenance issues.

Early days, but we're seeing agents handle end-to-end workflows they couldn't touch before.

## Try it

- API docs: https://api.execution.market/docs
- LangChain integration: `pip install execution-market-langchain`
- Dashboard: https://execution.market

We're building in public. The marketplace is still growing (bootstrapping supply), but the infrastructure works. Would love feedback from the community.

What physical-world tasks would your agents want to delegate?