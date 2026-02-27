---
date: 2026-02-26
tags:
  - domain/architecture
  - component/websocket
  - protocol/ws
status: active
aliases:
  - WebSocket Server
  - WS Server
  - Real-time Notifications
related-files:
  - mcp_server/websocket/server.py
  - mcp_server/websocket/handlers.py
  - mcp_server/websocket/events.py
  - mcp_server/websocket/integration.py
  - mcp_server/websocket/client.py
---

# WebSocket Server

Real-time notification system for task lifecycle events, powering live
updates in the [[dashboard]].

## Endpoints

| Path | Purpose |
|------|---------|
| `/ws` | WebSocket connection for real-time events |
| `/ws/stats` | Connection statistics (HTTP GET) |

## Event Types

Events are JSON messages pushed to connected clients:

- `task.created` -- new task published
- `task.accepted` -- worker assigned to task
- `task.submitted` -- evidence submitted for review
- `task.approved` -- task completed, payment released
- `task.cancelled` -- task cancelled by publisher
- `task.expired` -- deadline passed without completion
- `worker.registered` -- new worker joined the platform

## Architecture

| File | Responsibility |
|------|---------------|
| `server.py` | WebSocket endpoint, connection lifecycle |
| `handlers.py` | Message routing, event dispatch |
| `events.py` | Event type definitions, serialization |
| `integration.py` | Hooks into task service layer |
| `client.py` | Internal client for broadcasting from backend |

## Side Effects on Approval

When a task is approved, the WebSocket integration layer automatically:

1. Broadcasts `task.approved` to all connected clients
2. Auto-registers the worker if not already registered
3. Triggers agent rating (bidirectional reputation)

## Related

- [[dashboard]] -- primary consumer of WebSocket events
- [[mcp-server]] -- task operations that generate events
- [[task-lifecycle]] -- states that trigger event broadcasts
