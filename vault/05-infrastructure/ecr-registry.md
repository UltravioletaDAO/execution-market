---
date: 2026-02-26
tags:
  - domain/infrastructure
  - aws
  - ecr
  - docker
status: active
aliases:
  - ECR
  - Elastic Container Registry
related-files:
  - mcp_server/Dockerfile
  - dashboard/Dockerfile
  - .github/workflows/deploy.yml
---

# ECR Registry

Container image storage for Execution Market Docker images.

## Repositories

| Repository | Content |
|------------|---------|
| `em-production-dashboard` | React dashboard (Vite build) |
| `em-production-mcp-server` | Python MCP server (FastMCP) |

**Region**: `us-east-2`
**Account**: `518898403364` (via [[aws-account]])

## Image URI Format

```
518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard:latest
518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest
```

Always use `:latest` tag per [[image-tagging-policy]].

## Push Workflow

```bash
# 1. Authenticate
aws ecr get-login-password --region us-east-2 | \
  docker login --username AWS --password-stdin \
  518898403364.dkr.ecr.us-east-2.amazonaws.com

# 2. Build (ALWAYS --no-cache for code changes)
docker build --no-cache -f dashboard/Dockerfile -t em-dashboard ./dashboard

# 3. Tag
docker tag em-dashboard:latest \
  518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard:latest

# 4. Push
docker push \
  518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard:latest
```

## CI/CD Integration

[[github-actions-cicd]] pushes images on every merge to `main`. The pipeline builds, tags as `:latest`, pushes to ECR, then triggers [[ecs-fargate]] redeployment.

## Related

- [[ecs-fargate]] -- consumes these images
- [[github-actions-cicd]] -- automated push pipeline
- [[image-tagging-policy]] -- tagging rules
