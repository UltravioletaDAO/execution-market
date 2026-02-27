---
date: 2026-02-26
tags:
  - type/concept
  - domain/identity
status: active
aliases:
  - Agent Card
  - A2A Agent Card
related-files:
  - agent-card.json
  - mcp_server/api/routes.py
---

# Agent Card

A2A (Agent-to-Agent) protocol metadata descriptor that advertises an agent's capabilities, skills, and supported protocols. Defined in `agent-card.json` at the project root and served at the well-known discovery endpoint.

## Discovery Endpoint

```
GET https://mcp.execution.market/.well-known/agent.json
```

Any A2A-compatible agent can discover Execution Market by fetching this URL.

## Structure

The agent card contains:

| Section | Purpose |
|---------|---------|
| **name** | Human-readable agent name |
| **description** | What the agent does (Universal Execution Layer) |
| **url** | Base URL for A2A communication |
| **capabilities** | Supported protocols (MCP, A2A, REST) |
| **skills** | Available operations (publish task, check submission, etc.) |
| **authentication** | Supported auth methods ([[erc-8128-auth]], Supabase JWT) |
| **identity** | [[erc-8004]] agent ID and registry address |

## Storage

The card exists in three locations:

1. **File**: `agent-card.json` in project root (source of truth)
2. **Database**: Supabase stores a copy for API queries
3. **IPFS**: Pinned via Pinata for decentralized access

## Branding

The agent card uses the current branding: **Universal Execution Layer** (not the deprecated "Human Execution Layer"). Updated across 60+ files on 2026-02-18.

## MCP Server Integration

The MCP server at `mcp.execution.market/mcp/` exposes MCP tools (`em_publish_task`, `em_get_tasks`, etc.) that match the skills advertised in the agent card.

## Related

- [[a2a-protocol]] — The protocol standard this card implements
- [[agent-2106]] — The agent this card describes
- [[mcp-server]] — The MCP transport that serves agent tools
