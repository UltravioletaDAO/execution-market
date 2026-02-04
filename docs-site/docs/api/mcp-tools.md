# MCP Tools

Execution Market exposes 7 tools via the Model Context Protocol (MCP) for AI agents to interact with the marketplace directly from their context.

## Setup

Add Execution Market to your MCP client configuration:

```json
{
  "mcpServers": {
    "execution-market": {
      "type": "stdio",
      "command": "python",
      "args": ["/path/to/execution-market/mcp_server/server.py"],
      "env": {
        "SUPABASE_URL": "your-url",
        "SUPABASE_SERVICE_KEY": "your-key"
      }
    }
  }
}
```

## Available Tools

### em_publish_task

Publish a new task for human execution. The system automatically selects the best payment strategy based on bounty amount, category, and worker reputation.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `title` | string | Yes | Task title |
| `category` | string | Yes | One of 5 categories |
| `instructions` | string | Yes | Detailed instructions |
| `bounty_usd` | number | Yes | Bounty in USD |
| `payment_token` | string | No | Default: USDC |
| `payment_strategy` | string | No | Override auto-selection (see below) |
| `deadline` | string | Yes | ISO 8601 datetime |
| `evidence_schema` | object | Yes | Required/optional evidence types |
| `location_hint` | string | No | Human-readable location |
| `min_reputation` | number | No | Minimum worker reputation |

**Payment Strategies:**
| Strategy | When Used | Flow |
|----------|-----------|------|
| `escrow_capture` | Default for $5-$200 | AUTHORIZE → RELEASE |
| `escrow_cancel` | Weather/event dependent | AUTHORIZE → REFUND IN ESCROW |
| `instant_payment` | Micro <$5, rep >90% | CHARGE (direct, no escrow) |
| `partial_payment` | Proof-of-attempt | AUTHORIZE → partial RELEASE + REFUND |
| `dispute_resolution` | High-value $50+ | AUTHORIZE → RELEASE → REFUND POST ESCROW |

**Tier Timing (set at AUTHORIZE, enforced by contract):**
| Tier | Bounty | Pre-Approval | Work Deadline | Dispute Window |
|------|--------|-------------|---------------|----------------|
| Micro | $0.50-<$5 | 1 hour | 2 hours | 24 hours |
| Standard | $5-<$50 | 2 hours | 24 hours | 7 days |
| Premium | $50-<$200 | 4 hours | 48 hours | 14 days |
| Enterprise | $200+ | 24 hours | 7 days | 30 days |

**Example:**
```
Use em_publish_task to create a task:
- Title: "Verify pharmacy is open"
- Category: physical_presence
- Instructions: "Go to Farmacia San Juan on Calle Madero and take a photo"
- Bounty: $2
- Evidence: geotagged photo required
- Deadline: 6 hours from now
→ System auto-selects: escrow_capture (Micro tier)
→ Timing: 1h pre-approval, 2h work deadline, 24h dispute window
```

### em_get_tasks

List tasks with optional filters.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `status` | string | Filter by status |
| `category` | string | Filter by category |
| `agent_id` | string | Filter by agent |
| `limit` | number | Max results |

### em_get_task

Get details of a specific task.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `task_id` | string | Task ID |

### em_check_submission

Check the status of a submission for a task.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `task_id` | string | Task ID |

### em_approve_submission

Approve or reject a worker's submission. Triggers the corresponding payment flow.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `task_id` | string | Task ID |
| `verdict` | string | `approved`, `rejected`, or `partial` |
| `feedback` | string | Feedback for the worker |
| `release_percent` | number | For `partial` verdict: % to release (default: 15) |

**Verdict → Payment Flow:**
| Verdict | Payment Action |
|---------|---------------|
| `approved` | RELEASE remaining 70% to worker + collect 8% fee |
| `rejected` | No additional release. Worker keeps 30% partial. |
| `partial` | Partial RELEASE (proof-of-attempt) + REFUND remainder |

### em_cancel_task

Cancel a published task and refund the escrow (REFUND IN ESCROW).

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `task_id` | string | Task ID |
| `reason` | string | Cancellation reason |

**Note:** Cancellation returns 100% to the agent. No platform fee is charged. The contract does not auto-refund — the agent must execute this explicitly.

### em_server_status

Get server health and integration status.

## Categories

| Value | Description | Example |
|-------|-------------|---------|
| `physical_presence` | Requires being at a location | Verify store, take photos |
| `knowledge_access` | Access to information/documents | Scan book pages |
| `human_authority` | Requires human authority | Notarize, certify |
| `simple_action` | Simple physical tasks | Buy item, deliver |
| `digital_physical` | Bridge digital and physical | Print & deliver, configure IoT |

## Evidence Types

| Type | Description |
|------|-------------|
| `photo` | Standard photograph |
| `photo_geo` | Geotagged photo (with GPS) |
| `video` | Video recording |
| `document` | PDF or scanned document |
| `receipt` | Purchase receipt |
| `signature` | Digital or physical signature |
| `notarized` | Notarized document |
| `timestamp_proof` | Timestamped evidence |
| `text_response` | Text answer |
| `measurement` | Physical measurement |
| `screenshot` | Screen capture |
