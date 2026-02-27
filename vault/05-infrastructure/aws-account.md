---
date: 2026-02-26
tags:
  - domain/infrastructure
  - aws
  - account
status: active
aliases:
  - AWS Account
  - "518898403364"
related-files:
  - infrastructure/
  - mcp_server/Dockerfile
  - dashboard/Dockerfile
---

# AWS Account

**Account ID**: `518898403364`
**IAM User**: `cuchorapido`
**Region**: `us-east-2` (Ohio)

## Access

Claude Code has **full AWS CLI access** via the default profile. All `aws` commands target this account unless overridden.

> **CRITICAL**: On Git Bash (Windows), always prefix aws commands with `MSYS_NO_PATHCONV=1` to avoid path conversion bugs.

## Forbidden Account

**NEVER use account `897729094021`**. It is not the deployment target and lacks proper permissions for Execution Market infrastructure.

## Core Services

| Service | Resource |
|---------|----------|
| Compute | [[ecs-fargate]] (Fargate cluster) |
| Registry | [[ecr-registry]] (container images) |
| Secrets | [[aws-secrets-manager]] |
| IaC | [[terraform]] (all infra) |
| DNS | Route53 (`execution.market` zone) |
| CDN | [[cloudfront-s3]] (evidence + admin) |
| Certs | ACM (wildcard `*.execution.market`) |
| Load Balancer | [[alb-dns-routing]] |

## Quick Verify

```bash
MSYS_NO_PATHCONV=1 aws sts get-caller-identity --query Account --output text
# Expected: 518898403364
```

## Rules

- **NEVER CloudFormation** -- [[terraform]] only
- **NEVER manual AWS CLI** for production infra changes
- All secrets via [[aws-secrets-manager]], never plaintext in task definitions
