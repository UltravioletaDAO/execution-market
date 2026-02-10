# 🟢 PENDING — Clawd Can Do Autonomously Tonight
> Generated: Feb 9, 2026 9 PM — from audit of 60 TODO_NOW docs + 80 commits + app state

---

## ⚡ DOING NOW (Dream Session Priority Order)

### 1. ✅ Full Doc Audit — COMPLETE
- AUDIT-GROUP1.md: 33 docs audited, 30 DONE, 3 pending
- AUDIT-GROUP2.md: 18 docs audited, 11 DONE, 4 partial, 3 pending
- APP-STATE-AUDIT.md: Full system analysis + article gap check

### 2. ✅ Fix datetime.utcnow() Deprecation Warnings (34 warnings)
**Status:** DONE — commit `fdaac0c` (Feb 10 2AM dream session)
**Fixed:** 15 instances across 9 files, pushed to origin/main

### 3. NOW-015: Implement MCP Assign Task Tool
**Status:** RPC function `assign_task_to_executor` exists in Supabase
**Missing:** MCP tool wrapper in server.py
**Work:** Add `em_assign_task` tool (similar pattern to existing tools)
**Note:** Agent tools module has `em_assign_task` — need to verify it works

### 4. ✅ NOW-190: Agent Login Frontend Component
**Status:** DONE — `dashboard/src/components/AgentLogin.tsx` exists with full test suite (AgentLogin.test.tsx, 27+ dashboard tests)

### 5. ✅ Article v46 Update
**Status:** DONE — committed Feb 9 9PM session. Article updated with accurate claims.

### 6. NOW-206: Swagger UI Documentation Polish
**Status:** Basic Swagger at /docs endpoint
**Work:** Add descriptions, examples, and response schemas to all 63 endpoints
**Risk:** Low — documentation only

### 7. ✅ Dashboard Bundle Optimization
**Status:** DONE — commit `8e24e57` (optimized from 811KB → 176KB, -78%)

### 8. ✅ Fix MCP Server Docker (NOW-071)
**Status:** DONE — commit `9c37997` (Dockerfile.mcp updated for production readiness)

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
