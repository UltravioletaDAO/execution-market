---
date: 2026-02-26
tags:
  - domain/infrastructure
  - aws
  - ecs
  - containers
status: active
aliases:
  - ECS
  - Fargate
  - em-production-cluster
related-files:
  - infrastructure/
  - mcp_server/Dockerfile
  - dashboard/Dockerfile
---

# ECS Fargate

Serverless container orchestration for Execution Market production services.

## Cluster

**Name**: `em-production-cluster`
**Region**: us-east-2 (via [[aws-account]])
**Launch type**: Fargate (serverless, no EC2 instances)

## Services

| Service | Image Source | Endpoint |
|---------|-------------|----------|
| `em-production-dashboard` | [[ecr-registry]] | `execution.market` |
| `em-production-mcp-server` | [[ecr-registry]] | `mcp.execution.market` / `api.execution.market` |

## Task Definitions

Current revision: **144+** (check before deploying).

Each task definition specifies:
- Container image (MUST use `:latest` per [[image-tagging-policy]])
- Environment variables (non-secret)
- Secrets (from [[aws-secrets-manager]])
- CPU/memory allocation
- Health check configuration

> When adding new features that require env vars, **ALWAYS verify they are in the ECS task definition**. Missing secrets cause **silent 500 errors**.

## Deploy Commands

```bash
# Force new deployment (pulls latest image)
MSYS_NO_PATHCONV=1 aws ecs update-service \
  --cluster em-production-cluster \
  --service em-production-dashboard \
  --force-new-deployment --region us-east-2

MSYS_NO_PATHCONV=1 aws ecs update-service \
  --cluster em-production-cluster \
  --service em-production-mcp-server \
  --force-new-deployment --region us-east-2
```

## Verify Deployment

```bash
# Check running tasks
MSYS_NO_PATHCONV=1 aws ecs list-tasks \
  --cluster em-production-cluster \
  --service-name em-production-mcp-server --region us-east-2
```

## Related

- [[ecr-registry]] -- container image storage
- [[aws-account]] -- account context
- [[image-tagging-policy]] -- tagging rules
- [[alb-dns-routing]] -- traffic routing
