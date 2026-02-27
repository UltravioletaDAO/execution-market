---
date: 2026-02-26
tags:
  - type/moc
  - domain/infrastructure
status: active
aliases:
  - Infrastructure MOC
  - Deployment MOC
  - AWS Infrastructure
---

# Infrastructure & Deployment

> AWS infrastructure, container orchestration, CI/CD pipelines, and operational policies for the Execution Market platform.

---

## AWS Account

| Field | Value |
|-------|-------|
| Account ID | `518898403364` |
| IAM User | `cuchorapido` |
| Region | `us-east-2` (Ohio) |
| Profile | default |

> **NEVER use account `897729094021`** — it lacks proper permissions for Execution Market infrastructure and is not the deployment target.

---

## Compute

- [[ecs-fargate]] — `em-production-cluster` runs both services as Fargate tasks
  - `em-production-dashboard` — React SPA served via Nginx
  - `em-production-mcp-server` — Python FastMCP + REST API
  - Task definition revision tracking: see [[aws-ecs-task-definitions]]
  - Current MCP server task def revision: **144**
- [[ecr-registry]] — Elastic Container Registry (us-east-2)
  - `518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard`
  - `518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server`

---

## Networking

- [[alb-dns-routing]] — Application Load Balancer with HTTPS termination
  - ACM wildcard certificate for `*.execution.market`
  - ALB timeout: 960s (extended for Ethereum L1 escrow operations)
- **Route53 DNS**:
  - `execution.market` — Dashboard (React SPA)
  - `api.execution.market` — REST API + Swagger UI (`/docs`)
  - `mcp.execution.market` — MCP transport (Streamable HTTP at `/mcp/`)
  - `admin.execution.market` — Admin Dashboard (S3 + CloudFront)

---

## Storage

- [[cloudfront-s3]] — Evidence storage and static hosting
  - **Evidence uploads**: S3 with presigned URLs for executor submissions (photos, documents)
  - **CDN delivery**: CloudFront distribution for evidence retrieval
  - **Admin dashboard**: S3 static site with CloudFront, `X-Admin-Key` header auth
- [[supabase-database]] — PostgreSQL via Supabase (managed, external)

---

## Secrets

- [[aws-secrets-manager]] — All sensitive configuration stored in AWS Secrets Manager (us-east-2)

| Secret ID | Keys | Purpose |
|-----------|------|---------|
| `em/supabase-jwt` | `SUPABASE_JWT_SECRET` | H2A publisher JWT verification |
| `em/x402` | `PRIVATE_KEY`, `X402_RPC_URL` | Platform wallet key, QuikNode Base RPC |
| `em/test-worker` | `private_key`, `address` | E2E test worker wallet (`0x52E0...`) |
| `kk/swarm-seed` | mnemonic | HD wallet seed for 24 Karma Kadabra agents |

> When adding features that require new env vars, **ALWAYS verify they are in the ECS task definition**. Missing secrets cause silent 500 errors in production.

---

## CI/CD

- [[github-actions-cicd]] — Automated deployment pipeline
  - Workflow: `.github/workflows/deploy.yml`
  - Trigger: push to `main` branch
  - Duration: ~20 minutes end-to-end
  - Steps: lint (ruff) -> type check (mypy) -> test (pytest) -> build Docker -> push ECR -> deploy ECS
  - **User controls push timing** — CI triggers on push, so never auto-push

---

## Policies

- [[image-tagging-policy]] — Container image versioning rules
  - **ALWAYS use `:latest` tag** in ECS task definitions
  - CI may create `ship-*` tags but task defs must reference `:latest`
  - If a task def references a specific tag, register a new revision with `:latest`
- [[rpc-policy-quiknode]] — RPC endpoint selection
  - **ALWAYS prefer QuikNode private RPCs** from `.env.local`
  - 6 chains with QuikNode: Base, Ethereum, Polygon, Arbitrum, Avalanche, Optimism
  - Celo: `rpc.celocolombia.org` (custom). Monad: public only
  - Public RPCs = fallback ONLY when QuikNode fails
  - Exception: Ethereum L1 large TXs (>500k gas) — use LlamaRPC (QuikNode drops from mempool)
- [[git-bash-aws-policy]] — Always prefix `aws` commands with `MSYS_NO_PATHCONV=1` on Git Bash (Windows path conversion bug)

---

## Infrastructure as Code

- [[terraform]] — ALL infrastructure managed via Terraform
  - **NEVER use CloudFormation** — Terraform only, no exceptions
  - **NEVER use manual CLI commands** for infra provisioning
  - Source: `infrastructure/main.tf`, `infrastructure/variables.tf`

---

## Runbooks

- [[runbook-ecr-deploy]] — Full ECR build/push/deploy cycle
  - ECR login -> `docker build --no-cache` -> tag `:latest` -> push -> `update-service --force-new-deployment`
  - Verify: `sleep 90 && curl https://SERVICE.domain/health`
- [[runbook-golden-flow]] — Run the definitive E2E acceptance test post-deploy
  - Script: `python scripts/e2e_golden_flow.py`
  - If Golden Flow passes, the platform is healthy
- [[runbook-ecs-secrets]] — Adding new env vars to ECS task definitions
  - Check current revision -> add secret/env -> register new revision -> force deploy

---

## Source Files

| Path | Purpose |
|------|---------|
| `infrastructure/main.tf` | Terraform root module |
| `infrastructure/variables.tf` | Terraform variables |
| `dashboard/Dockerfile` | Dashboard container build |
| `mcp_server/Dockerfile` | MCP server container build |
| `docker-compose.yml` | Local development stack |
| `.github/workflows/deploy.yml` | CI/CD pipeline definition |

---

## Documentation

| Path | Purpose |
|------|---------|
| `docs/planning/DEPLOY-INSTRUCTIONS.md` | Step-by-step deploy guide |
| `.claude/projects/*/memory/aws-ecs-operations.md` | ECS operational recipes and exact commands |

---

## Cross-links

- [[moc-security]] — Secrets management, RLS policies
- [[moc-blockchain]] — RPC endpoints, on-chain contract addresses
- [[moc-architecture]] — Hosted services, data flow through infrastructure
- [[moc-testing]] — CI pipeline runs tests before deploy
