---
date: 2026-02-26
tags:
  - domain/infrastructure
  - docker
  - policy
status: active
aliases:
  - Image Tagging
  - Docker Tag Policy
related-files:
  - .github/workflows/deploy.yml
  - mcp_server/Dockerfile
  - dashboard/Dockerfile
---

# Image Tagging Policy

Rules for Docker image tags in the Execution Market deployment pipeline.

## The Rule

**ALWAYS use the `:latest` tag.**

ECS task definitions MUST reference `:latest`. Never reference specific tags like `ship-20260206-abc123`.

## Why

- Manual deploys (`docker push :latest` + `force-new-deployment`) only work when the task definition points to `:latest`
- CI/CD may create specific tags (`ship-*`) for traceability, but the task definition must always resolve `:latest`
- Parallel deploy sessions from multiple developers must all converge on `:latest`

## Build Rules

```bash
# ALWAYS use --no-cache for code changes
docker build --no-cache -f mcp_server/Dockerfile -t em-mcp ./mcp_server

# Tag as :latest
docker tag em-mcp:latest \
  518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest

# Push :latest
docker push \
  518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest
```

## Recovery

If a task definition references a specific tag (e.g., `ship-20260206-*`):
1. Register a **new task definition revision** pointing to `:latest`
2. Update the ECS service to use the new revision
3. Force new deployment

## Related

- [[ecr-registry]] -- where images are stored
- [[ecs-fargate]] -- where images are deployed
