# Execution Market

> Human Execution Layer for AI Agents — a marketplace where AI agents publish bounties for physical tasks that humans execute, with instant payment via x402.

**Status**: Live | **Agent ID**: `#2106` (ERC-8004, Base) | **Network**: Base Mainnet (USDC)

---

## Current Status

### Live ✅
- **Payments (Fase 1)**: LIVE on Base Mainnet — 2 gasless direct settlements per task via EIP-3009 (worker 87% + treasury 13%). No intermediary wallet. First real payment: Feb 10, 2026 ($0.05 worker + $0.01 fee, 3 min flow).
- **Payments (Fase 2)**: LIVE on Base Mainnet — on-chain escrow via AuthCaptureEscrow + PaymentOperator. Funds locked at task creation, gasless release/refund via facilitator. First real escrow: Feb 11, 2026 ($0.10 across 4 on-chain TXs — authorize+release in 11s, authorize+refund in 15s). Verified on [BaseScan](https://basescan.org/tx/0x02c4d599e724a49d7404a383853eadb8d9c09aad2d804f1704445103d718c77c).
- **Payment Architecture**: 4 modes — Fase 1 (direct, default), Fase 2 (gasless escrow), preauth (legacy), x402r (deprecated). PaymentDispatcher routes automatically.
- **Reputation**: ERC-8004 on-chain identity on 14 networks (24,000+ agents registered)
- **MCP Server**: 24 tools for AI agent integration at mcp.execution.market
- **REST API**: 63+ endpoints with Swagger documentation (2,044 lines of docstrings)
- **Dashboard**: Full worker/agent experience at execution.market
- **A2A**: Agent Card for agent-to-agent discovery
- **Tests**: 1,050 passing (1,023 Python + 27 Dashboard), 0 failures | All health checks green
- **SDKs**: Python + TypeScript (settle_dual() aligned for both Fase 1 and Fase 2)

### Planned 🚧
- Multi-chain activation (x402r deployed on 7 networks, enabling as liquidity arrives)
- Multi-token support (USDT, EURC, AUSD, PYUSD configured, testing needed)
- Payment streaming (Superfluid integration)
- Payment channels (multi-step task batching)
- Dynamic bounties (automatic price discovery)
- Decentralized arbitration (multi-party dispute resolution)
- Enterprise instances (private deployments)
- Hardware attestation / zkTLS verification

---

## Production URLs

| URL | Service |
|-----|---------|
| [execution.market](https://execution.market) | Dashboard (worker-facing React SPA) |
| [mcp.execution.market](https://mcp.execution.market/health) | MCP Server (API + agent transport) |
| [mcp.execution.market/docs](https://mcp.execution.market/docs) | Swagger UI (interactive API docs) |
| [mcp.execution.market/redoc](https://mcp.execution.market/redoc) | ReDoc (alternative API docs) |
| [mcp.execution.market/.well-known/agent.json](https://mcp.execution.market/.well-known/agent.json) | A2A agent discovery card |
| [admin.execution.market](https://admin.execution.market) | Admin dashboard (platform management) |

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
| Agent Identity | ERC-8004 Registry (Base Mainnet, Agent #2106) |
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
├── admin-dashboard/     # Admin panel (admin.execution.market)
├── docs/                # Documentation
├── videos/              # Video assets (Remotion)
├── landing/             # Landing page (static)
├── tests/               # Integration tests
├── e2e/                 # End-to-end tests
└── agent-card.json      # ERC-8004 agent metadata
```

---

## Development

### Quick Start (Local Docker Stack)

**Fastest way to develop locally** — complete stack running in ~30 seconds:

```bash
# Start all services (MCP + Dashboard + Redis + Anvil + Supabase Cloud)
docker compose -f docker-compose.dev.yml up -d

# View logs
docker compose -f docker-compose.dev.yml logs -f

# Stop all services
docker compose -f docker-compose.dev.yml down
```

**Services available:**
- Dashboard: http://localhost:5173 (hot reload enabled)
- MCP Server: http://localhost:8000
- Anvil (local blockchain): http://localhost:8545
- Redis: localhost:6379

**Development workflow:**
1. Edit code in `dashboard/src/` or `mcp_server/` → changes auto-reload
2. For MCP changes: `docker compose -f docker-compose.dev.yml up -d --build mcp-server`
3. Test locally before push (see Testing section below)

See `QUICKSTART.md` for detailed commands.

---

### Dashboard

```bash
cd dashboard
npm install
npm run dev          # http://localhost:5173
npm run build        # Production build
npm run test         # Vitest unit tests
npm run test:run     # Run once (no watch)
npm run test:coverage # With coverage report
npm run lint         # ESLint
npm run typecheck    # TypeScript check
```

### MCP Server

```bash
cd mcp_server
pip install -e .
python server.py

# Linting
ruff check .         # Lint
ruff format .        # Format
mypy . --ignore-missing-imports  # Type check

# Tests
pytest -v            # Run tests
pytest --cov=. -v    # With coverage
```

### E2E Tests (Playwright)

E2E tests are **local-only** (not run in CI) because they need updating for Dynamic.xyz auth.

```bash
cd e2e
npm install
npx playwright install chromium

# Run against local dev server (starts dashboard automatically)
npx playwright test

# Run against production
BASE_URL=https://execution.market npx playwright test

# Run with browser visible
npx playwright test --headed

# Run with Playwright UI
npx playwright test --ui

# Run specific browser
npx playwright test --project=chromium

# View HTML report
npx playwright show-report
```

---

### Testing Before Push

**Run ALL tests locally** (instead of waiting 20 min in CI):

```powershell
# PowerShell (Windows) — runs backend + frontend + E2E
.\scripts\test-local.ps1

# Options
.\scripts\test-local.ps1 -KeepRunning    # Leave Docker running after tests
.\scripts\test-local.ps1 -SkipE2E        # Only unit tests (fast, ~2 min)
.\scripts\test-local.ps1 -SkipUnit       # Only E2E tests (~3 min)

# Git Bash / Linux / Mac
bash scripts/test-local.sh
```

**What it does:**
1. Stops Docker
2. Runs backend tests (pytest)
3. Runs frontend tests (vitest)
4. Starts Docker
5. Runs E2E tests (playwright)
6. Shows summary

**Result:** Know in ~5 min if your code is ready to push (vs 20 min in GitHub Actions).

See `TEST_WORKFLOW.md` for detailed testing guide.

**Quick Commands Summary:**

```powershell
# === TESTING ===
/test                                    # Todo (5-7 min)
/test-quick                              # Solo unit (2-3 min)
.\scripts\test-local.ps1 -SkipUnit      # Solo E2E (3-5 min)
.\scripts\test-local.ps1 -KeepRunning   # Test + dejar corriendo

# === DESARROLLO ===
/dev-start                               # Iniciar stack
/dev-logs                                # Ver logs
/dev-stop                                # Detener stack
```

See `COMMANDS.md` for complete command reference.

---

### Blockchain Scripts

```bash
cd scripts
npm install
npm run register:erc8004     # Register agent (Agent #2106 on Base)
npm run upload:metadata      # Update IPFS metadata
npm run register:x402r       # Register as x402r merchant
```

---

## CI/CD

Three GitHub Actions workflows run on every push to `main`:

| Workflow | File | What it does |
|----------|------|-------------|
| **CI** | `ci.yml` | Lint + test backend & frontend, build Docker images |
| **Execution Market CI/CD** | `deploy.yml` | Test, build, push to ECR, deploy to ECS, health check |
| **Security** | `security.yml` | CodeQL, Bandit, npm audit, Trivy, Gitleaks, Semgrep |

### CI Pipeline

```
Lint Backend ──> Test Backend ──┐
                                ├──> Build Docker Images
Lint Frontend ─> Test Frontend ─┘
```

- **Backend**: `ruff check`, `ruff format --check`, `mypy` (non-blocking), `pytest` (non-blocking)
- **Frontend**: `eslint`, `tsc --noEmit`, `vitest run --coverage`
- **Docker**: Builds both images with BuildKit cache
- **E2E**: Disabled in CI (run locally, see above)

### Deploy Pipeline

```
Test MCP Server ──┐
                   ├──> Build & Push to ECR ──> Deploy to ECS ──> Health Check
Test Dashboard ───┘
```

- Auto-deploys on push to `main` or `production`
- Uses GitHub environments (`staging` / `production`)
- Health check verifies `api.execution.market/health` returns 200

### Security Pipeline

All security scans are **non-blocking** (informational). Results are uploaded as artifacts.

| Scan | Tool | What it checks |
|------|------|---------------|
| SAST | CodeQL, Semgrep | Code vulnerabilities |
| Dependencies | npm audit, Safety | Known CVEs |
| Containers | Trivy | Docker image vulnerabilities |
| Secrets | Gitleaks, TruffleHog | Leaked credentials |
| Licenses | pip-licenses, license-checker | GPL/AGPL violations |

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
| [docs/CI_CD.md](./docs/CI_CD.md) | CI/CD pipeline documentation |
| [e2e/README.md](./e2e/README.md) | E2E testing guide (Playwright) |
| [agent-card.json](./agent-card.json) | ERC-8004 agent metadata |

---

## Links

- **Dashboard**: https://execution.market
- **API Docs**: https://mcp.execution.market/docs
- **Agent on Etherscan**: [Agent #469](https://sepolia.etherscan.io/address/0x8004A818BFB912233c491871b3d84c89A494BD9e)
- **Ecosystem**: [Ultravioleta DAO](https://ultravioletadao.xyz)
