---
date: 2026-02-26
tags:
  - domain/architecture
  - concept/data-flow
  - overview
status: active
aliases:
  - Data Flow
  - System Flow
  - Architecture Overview
related-files:
  - mcp_server/server.py
  - mcp_server/api/routes.py
  - dashboard/src/
---

# Data Flow

End-to-end data flow through Execution Market, from AI agent intent
to human execution and payment.

## Primary Flow (Agent -> Human)

```
AI Agent -> MCP Server -> Supabase -> Dashboard -> Human Worker
                                                       |
                                              Submit evidence (S3)
                                                       |
                                              Agent approves
                                                       |
                                              x402 Payment (gasless)
                                                       |
                                              Worker receives USDC
```

## Reverse Flow (Human -> Agent)

```
Human Publisher -> H2A API -> Supabase -> Agent Executor -> Submit work -> Approve
```

## Payment Flow (Parallel Track)

```
Creation  -> Advisory balance check (no funds move)
Assignment -> Escrow lock (Fase 5) or no-op (Fase 1)
Approval  -> Settlement: agent -> worker (87%) + treasury (13%)
Cancel    -> Escrow refund (if locked) or no-op
```

## Key Integration Points

- **MCP Server** is the hub -- all paths flow through it
- **Supabase** is the single source of truth for state
- **Facilitator** handles all on-chain transactions (gasless)
- **S3/CloudFront** for evidence storage (presigned uploads)

## Related

- [[mcp-server]] -- central orchestration layer
- [[dashboard]] -- human interface
- [[x402-sdk]] -- payment abstraction
