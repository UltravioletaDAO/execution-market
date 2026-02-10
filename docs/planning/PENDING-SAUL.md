# 🔴 PENDING — Decisions for Saúl
> Generated: Feb 9, 2026 9 PM — from audit of 60 TODO_NOW docs + 80 commits + app state
> Context: Sub-agents audited all docs, I verified payment architecture + D14 gap

---

## 🚨 BLOCKING (Need Your Input Tonight/Tomorrow AM)

### 1. Which Wallet Is Funded?
**Problem:** You said AWS Secrets has a wallet funded on all networks with USDC. I checked:
- `erc8004-sniper/hotwallet` (0xD577...32A0) → **EMPTY on ALL chains**
- `chamba/production` → Has **PLACEHOLDER** for X402_PRIVATE_KEY
- `chamba/admin-key` → Just an API key string
- EM Treasury (0xae07...9a6ad) → **$0.11 USDC** on Base only

**Need:** Which secret has the funded wallet? Or do we need to fund one?

### 2. Moltiverse Hackathon Submission (Deadline Feb 15)
**Form at:** forms.moltiverse.dev/submit
**Filled so far:** Team: Ultravioleta DAO, Size: 1, Track: Agent, Rules: ✅
**Still needs (all required):**
- Your email address
- Project Title + Description
- "How does your agent leverage **Monad**?" (neither terra4mice nor EM is on Monad yet)
- **2-min demo video** (doesn't exist)
- Link to deployed app
- Tweet showcasing the project (prioritized for judging)
**Decision:** Which project? And do you want to record a video or skip Moltiverse?

### 3. Article v46 — Deployment Claims
**Current claim:** "Live on 7 EVM mainnets"
**Reality:** Only 2 networks have deployed contracts (Ethereum, Avalanche)
- 5 more are **configured** but contracts not deployed (Base, Arbitrum, Polygon, Celo, Monad)
- Payment processing only active on **Base** via facilitator
**Decision:** Deploy to remaining 5 networks (I can do this if you fund gas) or update article to say "2 deployed, 5 configured"?

### 4. Auth Model: API Key vs Wallet-Bound Token
From STATUS_SUMMARY.md — still undecided:
- Currently: `VITE_REQUIRE_AGENT_API_KEY=true` + `VITE_ALLOW_DIRECT_SUPABASE_MUTATIONS=false`
- **Option A:** API key only (simple, current state)
- **Option B:** Wallet-bound JWT (more web3 native)
- **Option C:** Both (API key for MCP agents, wallet for dashboard users)
**Decision needed** for final auth architecture.

### 5. Agent Login UI
**Status:** Backend API key auth ✅ ready. Frontend form ❌ missing.
- Workers can login via Dynamic.xyz wallet
- Agents have NO frontend login flow
**Decision:** Build agent login form? Or agents only via MCP/API (no dashboard)?

---

## 🟡 DECISIONS NEEDED (Not Blocking, But Soon)

### 6. PyPI for terra4mice
Wheel built, 420 tests passing. Need `~/.pypirc` credentials to publish.
**Decision:** Set up PyPI account? Or keep it GitHub-only for now?

### 7. Escrow Contract Deployment
- ChambaEscrow deployed on Ethereum + Avalanche
- **x402r escrow** (the new one) needs deployment on remaining chains
- Gas needed on each chain
**Decision:** Which chains to prioritize? All 7 or just Base + Arbitrum?

### 8. rentahuman.ai Competitive Response
Article v46 destroys them with facts (260K spam profiles, 1 rating, etc.)
**Decision:** Publish the article? Where? (Blog, X thread, Moltbook?)

### 9. MCP Server Hosting
Currently runs locally or via Docker. For agents to use it:
- **Option A:** Deploy to AWS ECS (terraform ready, just needs `terraform apply`)
- **Option B:** Keep at mcp.execution.market (current, but unverified uptime)
**Decision:** When to deploy to production?

---

## 📊 Quick Stats from Tonight's Audit

| Metric | Value |
|--------|-------|
| Tests passing | 726 (98.7% pass rate) |
| MCP tools | 24 |
| API endpoints | 63 |
| TODO docs DONE | 41/47 (87%) |
| TODO docs PARTIAL | 4 (8.5%) |
| TODO docs PENDING | 3 (6.4%) |
| Deployed networks | 2/7 (Ethereum, Avalanche) |
| Dashboard | Builds clean ✅ |
| D14 payment gap | Fixed in code ✅ (not tested with real funds) |

---

*This file was generated from audit reports at:*
- `docs/planning/AUDIT-GROUP1.md`
- `docs/planning/AUDIT-GROUP2.md`
- `docs/planning/APP-STATE-AUDIT.md`
