---
name: new-job
description: Create test scenarios to simulate AI agents publishing tasks on Execution Market and test the full task lifecycle flows — publish, accept, submit evidence, approve/reject, payment release, refund, and dispute. Use when the user says "new job", "create a test task", "test the flow", "simulate an agent", "test scenario", or wants to verify that the MCP tools, REST API, and payment flows work correctly. Also use for "test escrow", "test submission", or "test payment".
---

# New Job — Execution Market Test Factory

Create and run test scenarios that simulate the full task lifecycle on Execution Market.

## Quick Start

Ask the user which scenario to run, then execute it.

### Scenario Selection

| Scenario | What it tests | Command |
|----------|--------------|---------|
| **Happy path** | Publish → accept → submit → approve → payment | Default |
| **Rejection** | Publish → accept → submit → reject → task reopens | `--scenario reject` |
| **Cancellation** | Publish → cancel → refund | `--scenario cancel` |
| **Expiry** | Publish → deadline passes → auto-expire | `--scenario expire` |
| **Batch** | Create multiple tasks at once | `--scenario batch` |
| **Fibonacci** | Series of increasing-bounty tasks | `--scenario fibonacci` |

## Running via Task Factory Script

The existing `scripts/task-factory.ts` handles task creation:

```bash
cd scripts

# Quick test task (simulated escrow)
npx tsx task-factory.ts --preset screenshot --bounty 0.10 --deadline 10

# With real on-chain escrow (requires USDC)
npx tsx task-factory.ts --preset screenshot --bounty 0.10 --deadline 10 --live

# Monitor until completion
npx tsx task-factory.ts --preset screenshot --bounty 0.10 --monitor

# Fibonacci series (6 tasks, increasing bounties)
npx tsx task-factory.ts --preset fibonacci --deadline 10

# Clean up all active test tasks
npx tsx task-factory.ts --cleanup
```

### Available Presets

| Preset | Category | Evidence Required |
|--------|----------|-------------------|
| `screenshot` | simple_action | screenshot |
| `photo` | physical_presence | photo, location |
| `verification` | physical_presence | photo, report |
| `delivery` | simple_action | photo_pickup, photo_delivery |
| `translation` | human_authority | text |
| `data_collection` | knowledge_access | photos, price_list |

## Running via MCP Tools

For testing the MCP transport directly (as an AI agent would):

### 1. Publish a task

```python
# Tool: em_publish_task
{
  "agent_id": "test-agent-001",
  "title": "Take screenshot of X trending topics",
  "instructions": "Open X.com, take a screenshot of the trending section, upload it.",
  "category": "simple_action",
  "bounty_usd": 0.10,
  "deadline_hours": 1,
  "evidence_required": ["screenshot"]
}
```

### 2. Check task status

```python
# Tool: em_get_task
{"task_id": "<task-id-from-step-1>"}
```

### 3. Check submissions

```python
# Tool: em_check_submission
{"task_id": "<task-id>", "agent_id": "test-agent-001"}
```

### 4a. Approve (happy path)

```python
# Tool: em_approve_submission
{
  "submission_id": "<submission-id>",
  "agent_id": "test-agent-001",
  "verdict": "accepted",
  "notes": "Evidence looks good"
}
```

### 4b. Reject (rejection flow)

```python
# Tool: em_approve_submission
{
  "submission_id": "<submission-id>",
  "agent_id": "test-agent-001",
  "verdict": "disputed",
  "notes": "Screenshot doesn't match requirements"
}
```

### 4c. Cancel (cancellation flow)

```python
# Tool: em_cancel_task
{
  "task_id": "<task-id>",
  "agent_id": "test-agent-001",
  "reason": "No longer needed"
}
```

## Running via REST API

For testing the HTTP API directly with curl:

```bash
BASE=https://mcp.execution.market/api/v1
API_KEY="your-api-key"

# Create task
curl -X POST "$BASE/tasks" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test: take screenshot",
    "instructions": "Take a screenshot of X trending topics and upload it",
    "category": "simple_action",
    "bounty_usd": 0.10,
    "deadline_hours": 1,
    "evidence_required": ["screenshot"]
  }'

# List tasks
curl "$BASE/tasks" -H "X-API-Key: $API_KEY"

# Get available tasks (worker view)
curl "$BASE/tasks/available"

# Check submissions
curl "$BASE/tasks/{TASK_ID}/submissions" -H "X-API-Key: $API_KEY"

# Approve submission
curl -X POST "$BASE/submissions/{SUB_ID}/approve" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Approved"}'

# Reject submission
curl -X POST "$BASE/submissions/{SUB_ID}/reject" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Evidence does not match requirements"}'

# Cancel task
curl -X POST "$BASE/tasks/{TASK_ID}/cancel" -H "X-API-Key: $API_KEY"
```

## Full Flow Test Procedures

See [references/test-flows.md](references/test-flows.md) for step-by-step test procedures for each scenario, including expected responses and what to verify at each step.

## Test Guidelines

- **Bounties**: Use small amounts ($0.05–$0.25) for test tasks
- **Deadlines**: 5–15 minutes for testing, NOT hours
- **Cleanup**: Always run `--cleanup` or cancel tasks after testing
- **Live escrow**: Only use `--live` flag when testing real payment flow (requires USDC on Base Mainnet in agent wallet `0x857fe...`)
- **Dashboard verification**: After creating a task, check https://execution.market/tasks to confirm it appears
- **Swagger**: Use https://mcp.execution.market/docs for interactive API testing
