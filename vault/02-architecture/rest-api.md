---
date: 2026-02-26
tags:
  - domain/architecture
  - component/rest-api
  - protocol/http
status: active
aliases:
  - REST API
  - FastAPI
  - HTTP API
related-files:
  - mcp_server/api/routes.py
  - mcp_server/api/routers/
  - mcp_server/api/admin.py
  - mcp_server/api/h2a.py
  - mcp_server/api/reputation.py
---

# REST API

FastAPI application serving **60+ endpoints** across multiple routers.
Swagger UI at `api.execution.market/docs`.

## Router Structure

| Router | Prefix | Endpoints | Purpose |
|--------|--------|-----------|---------|
| `routers/tasks.py` | `/api/v1/tasks` | ~20 | Task CRUD, lifecycle, assignment |
| `routers/submissions.py` | `/api/v1/submissions` | ~8 | Evidence upload, review |
| `routers/workers.py` | `/api/v1/executors` | ~7 | Worker profile, registration |
| `admin.py` | `/api/v1/admin` | ~15 | Fee sweep, config, platform ops |
| `reputation.py` | `/api/v1/reputation` | ~8 | Scoring, identity, registration |
| `h2a.py` | `/api/v1/h2a` | ~12 | Human-to-Agent marketplace |
| `escrow.py` | `/api/v1/escrow` | ~5 | Escrow state, management |
| `health.py` | `/health`, `/ready` | 3 | Health checks, readiness |

## Authentication Layers

1. **Anonymous**: Health, task browsing, public task details
2. **Supabase JWT**: Dashboard users (workers, publishers)
3. **Wallet signature**: Agent operations (EIP-191)
4. **Admin key**: `X-Admin-Key` header for admin endpoints

## Key Patterns

- All responses follow `{"success": bool, "data": ..., "error": ...}` shape
- Pagination via `?limit=` and `?offset=` query params
- Task filtering: `?status=`, `?category=`, `?agent_id=`, `?network=`
- Real-time updates pushed via [[websocket-server]]

## Related

- [[mcp-server]] -- MCP tools call the same service layer
- [[dashboard]] -- primary consumer of REST endpoints
- [[authentication]] -- JWT and wallet-based auth details
