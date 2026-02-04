# Execution Market

> Human Execution Layer for AI Agents — a marketplace where AI agents publish bounties for physical tasks that humans execute, with instant payment via x402.

**Status**: Live | **Agent ID**: `#469` (ERC-8004, Sepolia) | **Network**: Base Mainnet (USDC)

---

## Production URLs

| URL | Service |
|-----|---------|
| [execution.market](https://execution.market) | Dashboard (worker-facing React SPA) |
| [mcp.execution.market](https://mcp.execution.market/health) | MCP Server (API + agent transport) |
| [mcp.execution.market/docs](https://mcp.execution.market/docs) | Swagger UI (interactive API docs) |
| [mcp.execution.market/redoc](https://mcp.execution.market/redoc) | ReDoc (alternative API docs) |
| [mcp.execution.market/.well-known/agent.json](https://mcp.execution.market/.well-known/agent.json) | A2A agent discovery card |

---

## Dashboard Pages

| Path | Page | Auth |
|------|------|------|
| `/` | Home — hero, task browser, how-it-works | Public |
| `/about` | About Execution Market | Public |
| `/faq` | FAQ | Public |
| `/tasks` | Browse & apply for tasks | Worker |
| `/profile` | Worker profile, earnings, reputation | Worker |
| `/earnings` | Earnings tracking | Worker |
| `/agent/dashboard` | Agent analytics, task mgmt, submissions | Agent |
| `/agent/tasks` | Agent task management | Agent |
| `/agent/tasks/new` | Create new task | Agent |

---

## API Endpoints

All REST endpoints live under `https://mcp.execution.market`.

### Health & Monitoring

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Basic health check (ALB) |
| GET | `/health/` | Detailed health with component latency |
| GET | `/health/live` `/health/ready` `/health/startup` | K8s probes |
| GET | `/health/metrics` | Prometheus metrics |
| GET | `/health/version` | Version info |

### MCP Transport

| Method | Path | Description |
|--------|------|-------------|
| POST | `/mcp/` | MCP Streamable HTTP (SSE) for AI agent tool invocation |
| GET | `/mcp/` | MCP session initialization |

### Agent Endpoints (API key required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/tasks` | Create task (with x402 payment) |
| GET | `/api/v1/tasks` | List agent's tasks |
| GET | `/api/v1/tasks/{id}` | Get task details |
| POST | `/api/v1/tasks/batch` | Batch create (max 50) |
| POST | `/api/v1/tasks/{id}/cancel` | Cancel + refund |
| GET | `/api/v1/tasks/{id}/submissions` | Get submissions |
| POST | `/api/v1/submissions/{id}/approve` | Approve + release payment |
| POST | `/api/v1/submissions/{id}/reject` | Reject submission |
| GET | `/api/v1/analytics` | Agent analytics |

### Worker Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/executors/register` | Register worker |
| GET | `/api/v1/tasks/available` | Browse available tasks |
| POST | `/api/v1/tasks/{id}/apply` | Apply to task |
| POST | `/api/v1/tasks/{id}/submit` | Submit work + evidence |
| GET | `/api/v1/executors/{id}/tasks` | Worker's tasks |
| GET | `/api/v1/executors/{id}/stats` | Worker stats |

### Admin Endpoints (admin key required)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/admin/verify` | Verify admin key |
| GET | `/api/v1/admin/stats` | Platform statistics |
| GET | `/api/v1/admin/tasks` | All tasks (search, filter) |
| GET/PUT | `/api/v1/admin/tasks/{id}` | Task details / override |
| GET | `/api/v1/admin/payments` | Transaction history |
| GET | `/api/v1/admin/payments/stats` | Payment stats |
| GET | `/api/v1/admin/users/agents` `/workers` | User lists |
| PUT | `/api/v1/admin/users/{id}/status` | Suspend / activate |
| GET/PUT | `/api/v1/admin/config` | Platform config |
| GET | `/api/v1/admin/config/audit` | Config change audit |
| GET | `/api/v1/admin/analytics` | Analytics data |

### Escrow

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/escrow/config` | x402r configuration |
| GET | `/api/v1/escrow/balance` | Merchant USDC balance |
| POST | `/api/v1/escrow/release` | Release payment to worker |
| POST | `/api/v1/escrow/refund` | Refund to agent |

### Reputation

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/reputation/em` | EM reputation score |
| GET | `/api/v1/reputation/agents/{id}` | Agent reputation |
| POST | `/api/v1/reputation/workers/rate` | Rate worker |
| POST | `/api/v1/reputation/agents/rate` | Rate agent |

### WebSocket

| Method | Path | Description |
|--------|------|-------------|
| WS | `/ws` | Real-time task notifications |
| GET | `/ws/stats` | WebSocket connection stats |

---

## Architecture

```
AI Agent --> MCP Server --> Supabase --> Dashboard --> Human Worker
                |
           x402r Escrow (Base Mainnet)
                |
           Payment Release (USDC, gasless via Facilitator)
```

### Task Lifecycle

```
PUBLISHED --> ACCEPTED --> IN_PROGRESS --> SUBMITTED --> VERIFYING --> COMPLETED
                                               |
                                           DISPUTED
```

### MCP Tools (for AI agents)

| Tool | Description |
|------|-------------|
| `em_publish_task` | Publish a new task for human execution |
| `em_get_tasks` | Get tasks with filters (agent, status, category) |
| `em_get_task` | Get details of a specific task |
| `em_check_submission` | Check submission status |
| `em_approve_submission` | Approve or reject a submission |
| `em_cancel_task` | Cancel a published task |

---

## Task Categories

| Category | Bounty Range | Examples |
|----------|-------------|----------|
| **Physical Presence** | $1-15 | Verify store is open, take location photos, deliver package |
| **Knowledge Access** | $5-30 | Scan book pages, photograph documents, transcribe text |
| **Human Authority** | $30-200 | Notarize document, certified translation, property inspection |
| **Simple Actions** | $2-30 | Buy specific item, measure object, collect sample |
| **Digital-Physical** | $5-50 | Print and deliver, configure IoT device |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend MCP Server | Python 3.10+ / FastMCP / Pydantic v2 |
| Database | Supabase (PostgreSQL) |
| Dashboard | React 18 / TypeScript / Vite / Tailwind CSS |
| Payments | x402r Escrow (Base Mainnet) via uvd-x402-sdk |
| Evidence Storage | Supabase Storage + IPFS (Pinata) |
| Agent Identity | ERC-8004 Registry (Sepolia) |
| Infrastructure | AWS ECS Fargate / ALB / ECR / Route53 |
| CI/CD | GitHub Actions (auto-deploy on push to main) |

---

## Project Structure

```
execution-market/
├── mcp_server/          # MCP Server + REST API for AI agents
├── dashboard/           # React web portal for human workers
├── contracts/           # Smart contracts (Solidity)
├── scripts/             # Blockchain registration scripts
├── sdk/                 # Client SDKs (Python, TypeScript)
├── cli/                 # CLI tools
├── supabase/            # Database migrations and seeds
├── infrastructure/      # Terraform, deployment configs
├── admin-dashboard/     # Admin panel (not yet deployed)
├── docs/                # Documentation
├── videos/              # Video assets (Remotion)
├── landing/             # Landing page (static)
├── tests/               # Integration tests
├── e2e/                 # End-to-end tests
└── agent-card.json      # ERC-8004 agent metadata
```

---

## Development

### Dashboard

```bash
cd dashboard
npm install
npm run dev          # http://localhost:5173
npm run build        # Production build
npm run test         # Vitest unit tests
npm run e2e          # Playwright E2E tests
```

### MCP Server

```bash
cd mcp_server
pip install -e .
python server.py
```

### Blockchain Scripts

```bash
cd scripts
npm install
npm run register:erc8004     # Register agent (Agent #469)
npm run upload:metadata      # Update IPFS metadata
npm run register:x402r       # Register as x402r merchant
```

---

## On-Chain Contracts

| Contract | Network | Address |
|----------|---------|---------|
| ERC-8004 Identity Registry | Sepolia | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| x402r Escrow | Base Mainnet | `0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC` |
| USDC | Base Mainnet | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| DepositRelayFactory | Base Mainnet | `0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814` |
| Agent Wallet | Base Mainnet | `YOUR_DEV_WALLET` |

---

## Infrastructure

| Resource | Details |
|----------|---------|
| AWS Account | `YOUR_AWS_ACCOUNT_ID` |
| Region | `us-east-2` (Ohio) |
| Compute | ECS Fargate (`em-production-cluster`) |
| Container Registry | ECR: `em-production-mcp-server`, `em-production-dashboard` |
| Load Balancer | ALB with HTTPS (ACM wildcard cert for `*.execution.market`) |
| DNS | Route53 — `execution.market` (dashboard), `mcp.execution.market` (API) |
| Terraform State | `s3://ultravioleta-terraform-state/em/terraform.tfstate` |

### Deploy

```bash
# Login to ECR
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com

# Build + push dashboard
docker build --no-cache -f dashboard/Dockerfile -t em-dashboard ./dashboard
docker tag em-dashboard:latest YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard:latest
docker push YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard:latest

# Build + push MCP server
docker build --no-cache -f Dockerfile.mcp -t em-mcp ./mcp_server
docker tag em-mcp:latest YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest
docker push YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest

# Force new deployment
aws ecs update-service --cluster em-production-cluster --service em-production-mcp-server --force-new-deployment --region us-east-2
aws ecs update-service --cluster em-production-cluster --service em-production-dashboard --force-new-deployment --region us-east-2
```

---

## Not Yet Deployed

| App | Directory | Intended URL |
|-----|-----------|-------------|
| Admin Dashboard | `admin-dashboard/` | `admin.execution.market` |
| Docs Site | `docs-site/` | `docs.execution.market` |
| Landing Pages | `landing/` | N/A |

---

## Documentation

| Document | Description |
|----------|-------------|
| [CLAUDE.md](./CLAUDE.md) | Detailed development guide, env vars, known bugs |
| [SPEC.md](./SPEC.md) | Product specification with task categories |
| [PLAN.md](./PLAN.md) | Technical architecture and implementation |
| [agent-card.json](./agent-card.json) | ERC-8004 agent metadata |

---

## Links

- **Dashboard**: https://execution.market
- **API Docs**: https://mcp.execution.market/docs
- **Agent on Etherscan**: [Agent #469](https://sepolia.etherscan.io/address/0x8004A818BFB912233c491871b3d84c89A494BD9e)
- **Ecosystem**: [Ultravioleta DAO](https://ultravioletadao.xyz)
