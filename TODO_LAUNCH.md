# Chamba Launch TODO - 2026-01-27

> Goal: Get Chamba fully functional by morning with tasks visible in dashboard.
> **STATUS: ✅ DASHBOARD FUNCTIONAL - Tasks visible!**

## Completed ✅

### Contract Deployment
- [x] Deploy ChambaEscrow to Avalanche mainnet
- [x] Contract address: `0xae99aB957d6648BeB8ecd26F64e62919C5a6925a`
- [x] Verify on Snowtrace
- [x] Verify on Sourcify
- [x] Save commission wallet to AWS: `YOUR_TREASURY_WALLET`
- [x] Save contracts to AWS Secrets Manager
- [x] Create DEPLOYMENT_LOG.md

### Wallet Status
- Balance: 1.89 AVAX, 3.68 USDC (Avalanche)

---

## Phase 1: MCP Server Running [P0] ✅

### 1.1 Verify MCP Server Entry Point
- [x] Check main.py exists and has proper FastMCP setup
- [x] Verify all tools are registered (agent_tools, worker_tools)
- [x] Verify A2A router is mounted
- [ ] Test health endpoint responds (requires full dependencies)

### 1.2 Environment Configuration
- [x] Create/update .env with all required variables
- [x] SUPABASE_URL and keys
- [x] Contract addresses (Avalanche)
- [x] Commission wallet address

### 1.3 Database Connection
- [x] Verify Supabase connection works
- [x] Run migrations if needed (already applied)
- [x] Create test executor in database
- [x] Create test agent in database

### 1.4 Start MCP Server
- [ ] Run server locally (requires Python venv with all dependencies)
- [ ] Test `/health` endpoint
- [ ] Test `/.well-known/agent.json` (A2A)

---

## Phase 2: Create Test Data [P0] ✅

### 2.1 Seed Test Executor (Worker)
- [x] Create executor record in Supabase
- [x] Wallet: `0x1234567890abcdef1234567890abcdef12345678`
- [x] Initial reputation: 85
- [x] Status: active

### 2.2 Seed Test Agent
- [x] Create agent with wallet address
- [x] Multiple test agents exist (colmena-forager-001, council-research-agent, etc.)

### 2.3 Create Sample Tasks
- [x] 11 published tasks exist in database
- [x] Categories: Physical Presence, Knowledge Access, Human Authority, Simple Action, Digital-Physical
- [x] Bounties range from $3 to $200 USDC
- [x] All set status to "published"

---

## Phase 3: Dashboard Connectivity [P0] ✅

### 3.1 Dashboard Environment
- [x] Update dashboard .env.local with API URL
- [x] Configure Supabase connection (correct anon key)
- [x] Set correct chain IDs (43114 - Avalanche)

### 3.2 Build and Run Dashboard
- [x] Install dependencies (npm install)
- [x] Start dev server (npm run dev) - running on port 3001

### 3.3 Verify Data Display
- [x] **Tasks appear in dashboard** ✅ (Screenshot: chamba-dashboard-tasks-working.png)
- [x] Task details load correctly
- [x] Auth modal works (manual wallet entry tested)
- [x] Category filters work
- [x] Language switcher works (EN/ES/PT)

---

## Phase 4: MCP Tool Testing [P1] - Pending

### 4.1 Agent Tools (via MCP)
- [ ] Test chamba_create_task
- [ ] Test chamba_batch_create_tasks
- [ ] Test chamba_assign_task
- [ ] Test chamba_get_task_analytics

### 4.2 Worker Tools (via MCP)
- [ ] Test chamba_get_available_tasks
- [ ] Test chamba_apply_to_task
- [ ] Test chamba_submit_work
- [ ] Test chamba_get_my_tasks

### 4.3 A2A Protocol
- [ ] Test /.well-known/agent.json
- [ ] Test /api/a2a/v1/card
- [ ] Verify capabilities listed

---

## Phase 5: End-to-End Flow [P1] - Pending

### 5.1 Full Task Lifecycle
- [ ] Agent creates task via MCP
- [ ] Task appears in dashboard
- [ ] Worker applies to task
- [ ] Agent assigns worker
- [ ] Worker submits evidence
- [ ] Agent verifies and releases payment

### 5.2 Escrow Integration (Avalanche)
- [ ] Test escrow creation with contract
- [ ] Test partial release
- [ ] Test full release on completion

---

## Phase 6: Documentation [P2] - Pending

### 6.1 API Documentation
- [ ] Document all MCP tools
- [ ] Document A2A endpoints
- [ ] Create example workflows

### 6.2 Deployment Guide
- [ ] Docker deployment instructions
- [ ] AWS deployment instructions
- [ ] Environment variables reference

---

## Technical Context

### Contract Addresses (Avalanche)
```
ChambaEscrow: 0xedA98AF95B76293a17399Af41A499C193A8DB51A  # v2 (2026-01-28)
USDC: 0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E
Commission Wallet: YOUR_TREASURY_WALLET

# Deprecated (v1): 0xae99aB957d6648BeB8ecd26F64e62919C5a6925a
```

### AWS Secrets
```
chamba/commission - Commission wallet address
chamba/contracts - Deployed contract addresses
chamba/api-keys - Block explorer API keys
chamba/supabase - Supabase credentials
chamba/admin-key - Admin API key
```

### Key Files
```
mcp_server/main.py - MCP server entry point
mcp_server/tools/agent_tools.py - Agent MCP tools
mcp_server/tools/worker_tools.py - Worker MCP tools
mcp_server/a2a/__init__.py - A2A protocol
dashboard/src/App.tsx - Dashboard entry
supabase/migrations/001_initial_schema.sql - DB schema
```

### How to Run Dashboard
```bash
cd /mnt/z/ultravioleta/dao/control-plane/ideas/chamba/dashboard
npm run dev
# Opens on http://localhost:3001 (or next available port)
```

### Test Login
- Click "I'm a Worker"
- Click "Or enter your wallet manually"
- Enter: `0x1234567890abcdef1234567890abcdef12345678`
- Click "Connect"
- You'll see 11 published tasks!
