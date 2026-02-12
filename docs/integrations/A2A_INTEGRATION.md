# A2A Protocol Integration Guide

> Execution Market as an A2A Server — The Agent-to-Human Bridge

## Overview

Execution Market implements the [A2A (Agent-to-Agent) Protocol](https://a2a-protocol.org) RC v1.0, enabling any A2A-compliant agent to discover and use EM without custom integration code.

**What this means:** If your agent speaks A2A (via LangGraph, Google ADK, BeeAI, CrewAI, or any framework with an A2A client), it can hire humans through Execution Market using a standard protocol.

## Quick Start

### 1. Discover the Agent Card

```bash
curl https://api.execution.market/.well-known/agent.json
```

Returns EM's capabilities, skills, authentication requirements, and endpoint URL.

### 2. Send a Task (JSON-RPC)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "text": "Take a photo of the coffee shop at 456 Oak Avenue and verify it's currently open for business"
        },
        {
          "data": {
            "budget_usd": "2.00",
            "deadline_hours": 4,
            "verification": ["photo", "gps"],
            "chain": "base",
            "token": "USDC",
            "location": {
              "address": "456 Oak Avenue, Miami, FL",
              "lat": 25.7617,
              "lon": -80.1918
            }
          },
          "mediaType": "application/json"
        }
      ]
    },
    "configuration": {
      "acceptedOutputModes": ["text", "data", "file"]
    }
  }
}
```

### 3. Receive a Task

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "id": "em-task-abc123",
    "contextId": "ctx-agent-session-1",
    "status": {
      "state": "submitted",
      "timestamp": "2026-02-12T08:00:00Z",
      "message": {
        "role": "agent",
        "parts": [
          {
            "text": "Task posted! Budget: $2.00 USDC on Base. Deadline: 4 hours. Awaiting worker assignment."
          }
        ]
      }
    }
  }
}
```

### 4. Stream Updates (SSE)

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "message/stream",
  "params": {
    "message": {
      "role": "user",
      "parts": [{"text": "Subscribe to updates for task em-task-abc123"}],
      "taskId": "em-task-abc123"
    }
  }
}
```

**Event stream:**
```
event: task
data: {"id":"em-task-abc123","status":{"state":"submitted"}}

event: status  
data: {"id":"em-task-abc123","status":{"state":"working","message":{"parts":[{"text":"Worker 'mike_305' accepted. ETA: 45 minutes."}]}}}

event: artifact
data: {"id":"em-task-abc123","artifact":{"artifactId":"photo-1","name":"verification_photo.jpg","parts":[{"url":"https://evidence.execution.market/abc123/photo1.jpg","mediaType":"image/jpeg"}]}}

event: artifact
data: {"id":"em-task-abc123","artifact":{"artifactId":"gps-1","name":"gps_verification","parts":[{"data":{"lat":25.7617,"lon":-80.1918,"accuracy_m":5,"timestamp":"2026-02-12T09:15:00Z"},"mediaType":"application/json"}]}}

event: status
data: {"id":"em-task-abc123","status":{"state":"completed","message":{"parts":[{"text":"Verified! Coffee shop is open. Payment settled: $2.00 USDC on Base."},{"data":{"payment":{"worker_amount":"1.84","fee_amount":"0.16","chain":"base","token":"USDC","worker_tx":"0xabc...","fee_tx":"0xdef..."}}}]}}}
```

### 5. Poll Task Status

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tasks/get",
  "params": {
    "id": "em-task-abc123",
    "historyLength": 5
  }
}
```

## Task Lifecycle

```
submitted ─→ working ─→ input-required ─→ completed
    │            │              │
    │            │              └─→ (auto-approve or agent reviews)
    │            └─→ failed (worker didn't complete)
    └─→ canceled (agent canceled)
    └─→ rejected (insufficient funds, invalid params)
```

| A2A State | EM Status | What Happened |
|-----------|-----------|---------------|
| `submitted` | `open` | Task posted, awaiting workers |
| `working` | `assigned` | Worker accepted the task |
| `input-required` | `verification_pending` | Worker uploaded evidence, needs review |
| `completed` | `completed` | Verified + paid |
| `failed` | `expired`/`failed` | No worker found or task failed |
| `canceled` | `cancelled` | Agent canceled the task |
| `rejected` | — | EM rejected (bad params, no funds) |

## Authentication

### Option 1: API Key (Bearer Token)
```
Authorization: Bearer em_key_abc123...
```

### Option 2: ERC-8004 Identity
Include on-chain agent identity for reduced fees (6% vs 8%):
```
Authorization: Bearer erc8004:chain_id:registry:agent_id:signature
```

### Option 3: x402 Payment Header
Pay-per-task, no account needed:
```
x-402-payment: <signed USDC authorization>
```

## Payment Extension

Every task requires payment configuration in a `DataPart`:

```json
{
  "data": {
    "budget_usd": "2.00",
    "chain": "base",
    "token": "USDC"
  },
  "mediaType": "application/json"
}
```

**Supported chains:** Base, Arbitrum, Polygon, Avalanche, Ethereum, Celo, Monad
**Supported tokens:** USDC, USDT, EURC, PYUSD
**Minimum budget:** $0.25
**Fee:** 8% (6% for ERC-8004 verified agents)
**Settlement:** Gasless via EIP-3009 (Fase 1: direct, Fase 2: on-chain escrow)

## Verification Extension

Specify what evidence you need:

```json
{
  "data": {
    "verification": {
      "types": ["photo", "gps"],
      "min_photos": 2,
      "gps_radius_m": 100,
      "require_timestamp": true
    }
  }
}
```

**Available types:** `photo`, `gps`, `video`, `receipt`, `signature`

## SDK Examples

### Python (a2a-sdk)
```python
from a2a.client import A2AClient

client = A2AClient("https://api.execution.market/a2a")

# Discover capabilities
card = await client.get_agent_card()
print(f"Skills: {[s.name for s in card.skills]}")

# Post a task
task = await client.send_message(
    message="Verify this storefront is open",
    data={
        "budget_usd": "1.00",
        "chain": "base",
        "token": "USDC",
        "verification": ["photo", "gps"]
    }
)

# Stream updates
async for event in client.stream_task(task.id):
    if event.type == "artifact":
        print(f"Evidence received: {event.artifact.name}")
    elif event.status.state == "completed":
        print(f"Done! TX: {event.status.message}")
```

### JavaScript (a2a-js)
```javascript
import { A2AClient } from '@a2a-js/sdk';

const client = new A2AClient('https://api.execution.market/a2a');

const task = await client.sendMessage({
  parts: [
    { text: 'Check if this business is open' },
    { data: { budget_usd: '1.00', chain: 'base', token: 'USDC' } }
  ]
});

for await (const event of client.streamTask(task.id)) {
  console.log(event.status?.state, event.artifact?.name);
}
```

## Comparison: A2A vs MCP vs REST

| Feature | A2A | MCP | REST |
|---------|-----|-----|------|
| Discovery | Agent Card (standard) | Tool manifest | OpenAPI/Swagger |
| Protocol | JSON-RPC 2.0 | JSON-RPC | HTTP/REST |
| Streaming | SSE (native) | Notifications | Custom |
| Async Tasks | First-class | Not native | Custom |
| Auth | Declared in card | N/A | Custom |
| Best For | Agent ecosystems | LLM tool calling | Direct integration |
| Coupling | Loose | Medium | Tight |

**Use A2A when:** Your agent orchestrator supports A2A, you want standard interop, or you're building multi-agent workflows.

**Use MCP when:** Your agent uses tool calling (most LLM agents today), and you want fine-grained control over EM functions.

**Use REST when:** You're building a custom integration and want direct API access.

## Related Resources

- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [EM REST API Documentation](/docs/API_REFERENCE.md)
- [EM MCP Tools](/docs/integrations/MCP_TOOLS.md)
- [Agent Integration Cookbook](/docs/AGENT_COOKBOOK.md)
- [Payment Architecture](/docs/planning/PAYMENT_ARCHITECTURE_REVIEW.md)
