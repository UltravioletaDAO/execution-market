---
date: 2026-02-26
tags:
  - domain/architecture
  - protocol/a2a
  - component/a2a
status: active
aliases:
  - A2A
  - Agent-to-Agent
  - A2A Protocol
related-files:
  - mcp_server/a2a/agent_card.py
  - mcp_server/a2a/jsonrpc_router.py
  - mcp_server/a2a/task_manager.py
  - mcp_server/a2a/models.py
---

# A2A Protocol

**Agent-to-Agent (A2A) protocol v0.3.0** enables external AI agents to
discover and interact with Execution Market without MCP integration.

## Discovery

- Agent card served at `GET /.well-known/agent.json`
- Describes capabilities, supported methods, authentication requirements
- Source: `mcp_server/a2a/agent_card.py`

## Transport

- **JSON-RPC 2.0** over HTTP
- Endpoint: `POST /mcp/` (shared with MCP transport)
- Methods map to task lifecycle operations

## Supported Methods

| Method | Description |
|--------|-------------|
| `tasks/send` | Create or update a task |
| `tasks/get` | Retrieve task details |
| `tasks/cancel` | Cancel a published task |
| `tasks/sendSubscribe` | Subscribe to task updates (SSE) |

## Task Manager

`mcp_server/a2a/task_manager.py` bridges A2A JSON-RPC calls to the
internal service layer. Handles:

- Task creation with A2A-specific metadata
- Status mapping between A2A states and EM lifecycle states
- Artifact delivery (evidence URLs, completion data)

## Known Limitations

- A2A approve flow bypasses PaymentDispatcher (P0 bug, tracked in audit)
- A2A cancel does not trigger escrow refund (P0 bug, tracked in audit)
- No bridge between A2A identity and MCP executor registration

## Related

- [[agent-card]] -- ERC-8004 agent metadata
- [[mcp-server]] -- primary AI agent interface (preferred over A2A)
- [[h2a-marketplace]] -- reverse direction (humans publish for agents)
