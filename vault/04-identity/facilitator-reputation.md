---
date: 2026-02-26
tags:
  - type/concept
  - domain/identity
status: active
aliases:
  - Facilitator Reputation
  - Bidirectional Reputation
related-files:
  - mcp_server/integrations/erc8004/facilitator_client.py
  - scripts/e2e_golden_flow.py
---

# Facilitator Reputation

Bidirectional reputation system with two distinct paths depending on the direction of feedback. Both paths record ratings in the [[erc-8004]] Reputation Registry on-chain.

## Two Reputation Paths

### Path 1: Agent rates Worker (Gasless)

```
Agent approval
  --> MCP Server calls Facilitator POST /feedback
  --> Facilitator signs TX and pays gas
  --> Reputation Registry records agent-->worker rating
```

- **Cost to agent**: Zero (Facilitator pays gas)
- **Latency**: ~2-5 seconds on Base
- **Auth**: Platform wallet signs the feedback payload

### Path 2: Worker rates Agent (On-Chain, Worker Signs)

```
Worker submits rating
  --> Server constructs giveFeedback() calldata
  --> Relay wallet signs and submits TX
  --> Reputation Registry records worker-->agent rating
```

- **Cost**: ~0.001 ETH gas (paid by [[relay-wallet]])
- **Why not gasless?**: Platform wallet owns Agent #2106 and cannot self-rate
- **Worker wallet**: `0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15` (test environment)

## Verification (Golden Flow)

Both paths are tested in the Golden Flow E2E acceptance test:

| Path | Verified TX (example) |
|------|----------------------|
| Agent --> Worker | Facilitator TX `2fd328e1` |
| Worker --> Agent | On-chain TX `0x62361d26` (gas: 133,568) |

Requires `EM_WORKER_PRIVATE_KEY` from AWS Secret `em/test-worker:private_key`.

## Feedback Data

Each feedback record includes:

- **From**: Rater's wallet address
- **To**: Target agent/executor ID
- **Score**: Numeric rating
- **Comment**: Optional text
- **TX hash**: On-chain proof

## Related

- [[reputation-scoring]] — The multi-dimensional scoring that generates ratings
- [[relay-wallet]] — The wallet that signs worker-to-agent feedback
- [[facilitator]] — The gasless relay for agent-to-worker feedback
- [[erc-8004]] — The registry where all reputation lives on-chain
