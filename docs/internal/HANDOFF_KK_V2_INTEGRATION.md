# Handoff: Karma Kadabra V2 Integration

> From: Claude Code (0xultravioleta session)
> To: UltraClawd (OpenClaw)
> Date: 2026-02-20
> Branch: `main` (latest pushed: `35f382b`)

---

## TL;DR

Pull latest `main`. Read the Master Plan at `docs/planning/MASTER_PLAN_KK_V2_INTEGRATION.md`. There are **38 tasks across 6 phases** to make 24 autonomous AI agents fully operational on Execution Market across 8 EVM chains with 5 stablecoins ($200 USDC budget).

**Do NOT start any phase without 0xultravioleta's explicit approval.**

---

## What Was Built (Phases 1-14 — DONE)

Everything up to and including Phase 14 of KK V2 is complete:

| Done | What |
|------|------|
| 24 HD wallets | BIP-44 from `kk/swarm-seed` in AWS SM. 6 system + 18 community agents |
| Multi-token allocation | $200 USDC budget, 5 stablecoins (USDC, EURC, AUSD, PYUSD, USDT), 8 chains |
| 5 EM skills | `em-publish-task`, `em-apply-task`, `em-approve-work`, `em-check-status`, `em-browse-tasks` |
| Bridge script | `scripts/kk/bridge-from-source.ts` — bridges from Avalanche to all chains |
| Sweep script | `scripts/kk/sweep-funds.ts` — recovers all agent funds back to source |
| SOUL templates | Agent personality + behavior extraction system |
| IRC integration | MeshRelay config at `scripts/kk/config/irc-config.json` |
| Heartbeat system | Abracadabra + Karma Hello agents |
| Standup reports | Daily standup generator |
| Balance monitor | Cross-chain balance checker |

---

## What Needs Building (Master Plan — 38 Tasks)

### Phase 1: Missing Skills + Agent Auth (9 tasks, P0)

The agents can't complete the full lifecycle yet. Missing:

1. **`em-submit-evidence` skill** — Workers can't submit after assignment
2. **`em-rate-counterparty` skill** — No rating skill exists
3. **`em-register-identity` skill** — Workers need to register + get ERC-8004 identity
4. **EIP-8128 signing library (TS)** — `scripts/kk/lib/eip8128-signer.ts` — agents need to SIGN, server can already VERIFY (`mcp_server/integrations/erc8128/verifier.py`, 721 lines, fully working)
5. **EIP-8128 signing library (Python)** — Same for Python agents
6. **Update `em_client.py`** — Replace `X-Agent-Wallet` header with EIP-8128 signed headers
7. **Migrate API routes** — Routes still use old `verify_api_key_if_required()`. Need to switch to `verify_agent_auth()` at `auth.py:492-570`
8. **Add nonce endpoint** — `GET /api/v1/auth/erc8128/nonce` (function exists at `auth.py:578-589`, no route)
9. **Deploy DynamoDB nonce table** — Terraform for `em-production-nonce-store`

### Phase 2: Self-Protection + Race Conditions (5 tasks, P0)

Critical bugs 24 agents will hit immediately:

1. **Self-application prevention** — Agent can apply to its own task! No check at `supabase_client.py:456-465`
2. **Self-application in MCP tool** — Same bug in `server.py`
3. **Race condition on apply** — No unique constraint, no `SELECT FOR UPDATE`. 5 agents apply simultaneously = corruption
4. **`payment_token` field** — Tasks only have `payment_network`, not which stablecoin. Need to add field
5. **Token validation** — Validate token exists on target network

### Phase 3: ERC-8004 Registration + Reputation (7 tasks, P0)

All 24 agents need on-chain identity:

1. **Bulk registration script** — Register all 24 agents via Facilitator
2. **Multi-chain registration** — Register on all 8 chains
3. **Reputation in SOUL templates** — Agents need to know they must rate counterparties
4. **Relay wallets** — Each agent gets a 2nd wallet (index+100) for autonomous reputation signing
5. **Modify `rate_agent()` for direct signing** — Accept relay key, bypass `pending_signature`
6. **Update MCP tool** — `em_rate_agent` returns TX hash instead of pending
7. **Reputation leaderboard** — Query scores for all 24 agents

### Phase 4-5: Test Scenarios (12 tasks, P1)

12 novel test scenarios discovered during research:
- Cross-chain task lifecycle
- Self-application prevention
- Concurrent applications race
- Token mismatch on approval
- Rejection + resubmission
- Expiry with escrow locked
- Reputation without transaction
- Bilateral task economy
- EIP-8128 without ERC-8004
- Insufficient funds during release
- Cross-chain approval mismatch
- Token denomination mismatch

### Phase 6: Integration Harness (5 tasks, P1)

Full swarm E2E tests: integration harness, multi-chain test, chaos testing, Golden Flow multi-token, swarm coordinator.

---

## Critical Gaps Found (READ BEFORE CODING)

| Gap | Where | Impact |
|-----|-------|--------|
| Routes NOT migrated to `verify_agent_auth()` | `mcp_server/api/routers/*.py` | EIP-8128 auth exists but routes don't use it |
| `rate_agent()` returns `pending_signature` | `facilitator_client.py:866-934` | Blocks autonomous agent-to-agent reputation |
| No self-application prevention | `supabase_client.py:456-465` | Agent can execute its own task |
| No balance re-check at approval | `payment_dispatcher.py:550` | Task marked COMPLETED but payment fails |
| No chain validation on approval | `submissions.py:150-250` | Cross-chain signatures fail silently |
| No token pass-through in settlement | `payment_dispatcher.py:450-509` | All tasks default to USDC regardless of token field |
| No automatic expiry job | No cron/scheduler | Tasks stay PUBLISHED forever |
| No unique constraint on applications | `task_applications` table | Race condition on concurrent apply |

---

## Key Files to Read First

```
docs/planning/MASTER_PLAN_KK_V2_INTEGRATION.md    # THE PLAN (38 tasks, 6 phases)
scripts/kk/skills/*/SKILL.md                        # Existing 5 skills
scripts/kk/config/wallets.json                      # 24 agent wallets
scripts/kk/config/allocation.json                   # Multi-token allocation
scripts/kk/lib/chains.ts                            # Chain + token registry
scripts/kk/services/em_client.py                    # Agent EM API client
mcp_server/integrations/erc8128/verifier.py         # EIP-8128 verifier (721 lines)
mcp_server/api/auth.py                              # Unified auth (verify_agent_auth)
mcp_server/api/reputation.py                        # ERC-8004 reputation endpoints
mcp_server/integrations/x402/payment_dispatcher.py  # Payment settlement
```

---

## How to Get Started

```bash
git pull origin main
# Read the master plan
cat docs/planning/MASTER_PLAN_KK_V2_INTEGRATION.md
# Wait for 0xultravioleta to say "Empieza Phase N"
```

---

## Rules

1. **Never start a phase without 0xultravioleta's explicit approval**
2. Each task is atomic — one file, one fix, one validation
3. Always run `ruff format . && ruff check .` before committing Python
4. Test bounties ALWAYS under $0.20
5. Push only when asked
6. Reports go to `docs/reports/`, plans go to `docs/planning/`
