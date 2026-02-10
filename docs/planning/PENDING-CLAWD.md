# 🟢 PENDING — Clawd Can Do Autonomously Tonight
> Generated: Feb 9, 2026 9 PM — from audit of 60 TODO_NOW docs + 80 commits + app state

---

## ⚡ DOING NOW (Dream Session Priority Order)

### 1. ✅ Full Doc Audit — COMPLETE
- AUDIT-GROUP1.md: 33 docs audited, 30 DONE, 3 pending
- AUDIT-GROUP2.md: 18 docs audited, 11 DONE, 4 partial, 3 pending
- APP-STATE-AUDIT.md: Full system analysis + article gap check

### 2. Fix datetime.utcnow() Deprecation Warnings (34 warnings)
**Impact:** 34 deprecation warnings in test suite
**Fix:** Replace `datetime.utcnow()` → `datetime.now(timezone.utc)` across codebase
**Risk:** Low — mechanical replacement
**Files:** Primarily in mcp_server/ Python files

### 3. NOW-015: Implement MCP Assign Task Tool
**Status:** RPC function `assign_task_to_executor` exists in Supabase
**Missing:** MCP tool wrapper in server.py
**Work:** Add `em_assign_task` tool (similar pattern to existing tools)
**Note:** Agent tools module has `em_assign_task` — need to verify it works

### 4. NOW-190: Agent Login Frontend Component
**Status:** Backend API key auth ready in `api/auth.py`
**Missing:** Frontend form for agents to enter API key
**Work:** Create AgentLogin.tsx component with:
  - API key input field
  - Validation against backend
  - Redirect to agent dashboard on success
**Risk:** Medium — UI work, needs to match existing design system

### 5. Article v46 Update
**Based on APP-STATE-AUDIT.md findings:**
- Fix "7 mainnets" claim → accurate "2 deployed + 5 configured"
- Add missing features (admin dashboard, reputation system, A2A protocol)
- Remove unverifiable user adoption numbers
- Clarify roadmap vs live features
- Highlight 726 tests, 24 tools, 63 endpoints

### 6. NOW-206: Swagger UI Documentation Polish
**Status:** Basic Swagger at /docs endpoint
**Work:** Add descriptions, examples, and response schemas to all 63 endpoints
**Risk:** Low — documentation only

### 7. Dashboard Bundle Optimization
**Issue:** Build warnings about chunks >500KB
**Work:** Code splitting, lazy loading for heavy routes
**Risk:** Low — performance improvement

### 8. Fix MCP Server Docker (NOW-071)
**Status:** Dockerfile.mcp exists but needs verification
**Work:** Test Docker build, fix any issues
**Command:** `docker build -f Dockerfile.mcp .`

---

## 🔧 CAN DO IF WALLET IS FOUND

### 9. E2E Payment Flow Tests
**Blocked by:** Need funded wallet (see PENDING-SAUL.md #1)
**Script ready:** `scripts/test-x402-full-flow.ts`
**What to test:**
  - Task creation with x402 payment header
  - Escrow deposit via facilitator
  - Worker payment (92% of bounty)
  - Fee collection (8% to treasury)
  - Refund flow
  - All stablecoins × all networks

### 10. Contract Deployment to Remaining Networks
**Blocked by:** Need gas on each chain
**Chains:** Base, Arbitrum, Polygon, Celo, Monad
**Script:** `scripts/register-and-deploy.ts`

---

## 📋 ALREADY VERIFIED AS DONE (No Action Needed)

These were flagged but confirmed complete by audits:
- ✅ Docker infrastructure (NOW-001 to NOW-003)
- ✅ Terraform/AWS (NOW-004 to NOW-007)
- ✅ Supabase setup (NOW-008, NOW-009)
- ✅ All MCP tools except assign (NOW-011 to NOW-014)
- ✅ Dashboard auth flow (NOW-188, NOW-189, NOW-191, NOW-192)
- ✅ Test suites (NOW-193, NOW-198, NOW-199, NOW-201)
- ✅ x402 SDK integration (NOW-202)
- ✅ Platform config (NOW-213)
- ✅ Admin dashboard (NOW-214)
- ✅ D14 payment gap (fixed in sdk_client.py — Step 0 settles agent auth)

---

## 🌙 Tonight's Work Plan

| Time | Task | Est. |
|------|------|------|
| 9-10 PM | ✅ Audit + PENDING docs | Done |
| 10-11 PM | Fix deprecation warnings + NOW-015 | 1hr |
| 11-12 AM | Agent Login UI (NOW-190) | 1hr |
| 12-1 AM | Article v46 update | 1hr |
| 1-2 AM | Swagger docs polish | 1hr |
| 2-3 AM | Dashboard optimization | 1hr |
| 3-5 AM | Docker testing + misc fixes | 2hr |
| 5-6 AM | Morning brief + commit everything | 1hr |

**Estimated output:** 5-7 items fixed, article updated, 0 regressions
