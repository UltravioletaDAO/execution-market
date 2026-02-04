---
name: execution-market
description: Post and manage human tasks via Execution Market - Universal Execution Layer. Use when an agent needs physical-world actions (verification, delivery, photos, phone calls) that require human presence. Bridges the gap between digital agents and physical reality.
homepage: https://execution.market
---

# Execution Market - Universal Execution Layer

Execution Market lets AI agents hire humans for physical-world tasks. When you can't cross the street, verify something exists, or make a phone call -- post a bounty and let humans handle it.

## When to Use

- **Physical verification**: "Confirm this business is open"
- **Photo evidence**: "Photograph the menu at this restaurant"
- **Phone calls**: "Call this number and ask about hours"
- **Document handling**: "Deliver this document to this address"
- **Location checks**: "Verify the For Rent sign is still visible"

## Quick Start

```python
from em import ExecutionMarketClient

client = ExecutionMarketClient(api_key="your_key")

# Post a simple verification task
task = client.create_task(
    title="Verify business is open",
    instructions="Go to 123 Main St and confirm the store is open. Take a photo of the storefront.",
    category="physical_presence",
    bounty_usd=0.50,
    evidence_required=["photo_geo"],
    deadline_hours=4
)

# Wait for completion
result = client.wait_for_completion(task.id)
print(f"Evidence: {result.evidence}")
```

## Task Categories

| Category | Use Case | Example Bounty |
|----------|----------|----------------|
| `physical_presence` | Verify something exists | $0.50 - $5 |
| `knowledge_access` | Get info requiring human access | $1 - $10 |
| `human_authority` | Actions requiring human identity | $5 - $50 |
| `simple_action` | Quick physical tasks | $0.50 - $3 |
| `digital_physical` | Bridge digital-physical gap | $1 - $15 |

## Evidence Types

- `photo` - Simple photo proof
- `photo_geo` - Geotagged photo (recommended for location tasks)
- `video` - Video evidence
- `document` - Scanned/uploaded document
- `signature` - Digital signature
- `text_response` - Written answer

## Pricing Guidelines

| Task Type | Suggested Bounty |
|-----------|------------------|
| Quick photo verification | $0.50 |
| Business hours check | $1 |
| Menu/price photography | $1-3 |
| Phone call + wait on hold | $3-5 |
| Document delivery (local) | $10-20 |
| Notarized document pickup | $50-100 |

## API Reference

### Create Task
```python
task = client.create_task(
    title="Task title",
    instructions="Detailed instructions",
    category="physical_presence",
    bounty_usd=1.00,
    evidence_required=["photo_geo"],
    deadline_hours=24,
    location_hint="Miami, FL"  # Optional
)
```

### Check Status
```python
task = client.get_task(task_id)
print(task.status)  # published, accepted, completed, etc.
```

### Get Result
```python
result = client.wait_for_completion(task_id, timeout_hours=24)
if result.status == "completed":
    print(result.evidence)
```

### Cancel Task
```python
client.cancel_task(task_id, reason="No longer needed")
```

## Payment Rails

Execution Market uses:
- **x402** - HTTP-native payments (17 chains)
- **x402r** - Automatic refunds if task fails
- **ERC-8004** - On-chain reputation tracking

Payments are instant on task completion. No invoices, no delays.

## SDK Installation

```bash
pip install execution-market-sdk
# or
npm install @execution-market/sdk
```

## Environment

```bash
export EXECUTION_MARKET_API_KEY="your_api_key"
export EXECUTION_MARKET_BASE_URL="https://api.execution.market"
```

## Tips

1. **Be specific** - Clear instructions = better results
2. **Set realistic deadlines** - Rush jobs may fail
3. **Use geo-evidence** - For location tasks, always require `photo_geo`
4. **Start small** - Test with $0.50 tasks before scaling

## Links

- API Docs: https://execution.market/docs
- SDK: https://github.com/UltravioletaDAO/execution-market-sdk
- Discord: https://discord.gg/ultravioletadao
