---
date: 2026-02-26
tags:
  - domain/infrastructure
  - aws
  - networking
  - dns
status: active
aliases:
  - ALB
  - DNS
  - Application Load Balancer
  - Route53
related-files:
  - infrastructure/
---

# ALB & DNS Routing

Application Load Balancer with HTTPS termination and Route53 DNS for all Execution Market services.

## DNS Records (Route53)

| Domain | Target | Service |
|--------|--------|---------|
| `execution.market` | ALB | Dashboard (React SPA) |
| `api.execution.market` | ALB | REST API (`/api/v1/*`, `/docs`) |
| `mcp.execution.market` | ALB | MCP Transport (`/mcp/`), A2A (`/.well-known/agent.json`) |
| `admin.execution.market` | [[cloudfront-s3]] | Admin Dashboard (S3 static) |

## HTTPS / TLS

- **ACM wildcard certificate**: `*.execution.market`
- ALB terminates TLS; backend containers receive HTTP
- HSTS headers enforced

## ALB Configuration

- Listener: 443 (HTTPS) with ACM cert
- Target groups route to [[ecs-fargate]] services by host header
- Health checks: `/health` endpoint on each service
- **ALB timeout**: 960s (extended for Ethereum L1 escrow operations)

## Production URLs

| URL | Purpose |
|-----|---------|
| `https://execution.market` | Public dashboard |
| `https://api.execution.market/docs` | Swagger UI |
| `https://api.execution.market/api/v1/*` | REST API |
| `https://mcp.execution.market/mcp/` | MCP Streamable HTTP |
| `https://mcp.execution.market/.well-known/agent.json` | A2A Agent discovery |
| `https://admin.execution.market` | Admin panel |

## Related

- [[ecs-fargate]] -- backend services behind ALB
- [[cloudfront-s3]] -- admin dashboard static hosting
