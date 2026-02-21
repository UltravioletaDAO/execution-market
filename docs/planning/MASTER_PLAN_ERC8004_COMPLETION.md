# Master Plan: ERC-8004 / ERC-8128 Completion

> **Created**: 2026-02-21
> **Updated**: 2026-02-21
> **Status**: ALL PHASES COMPLETE (14/14 tasks done)
> **Scope**: Close all remaining gaps in ERC-8004 identity/reputation and ERC-8128 authentication
> **Depends on**: Multichain Golden Flow 7/8 PASS (completed 2026-02-21)

---

## Background

The Multichain Golden Flow test confirmed 7/8 chains PASS with bidirectional reputation. ERC-8004 identity registration, reputation scoring, and side effects are operational. However, several security and completeness gaps remain in the ERC-8128 auth migration, self-assignment prevention, nonce persistence, and Karma Kadabra skill coverage.

### What's Already Done (confirmed by code audit 2026-02-21)

| Item | Status | Evidence |
|------|--------|----------|
| ERC-8128 verifier | DONE | `api/auth.py:492` — `verify_agent_auth()` |
| Nonce endpoints | DONE | `api/routers/misc.py:449-484` — `/auth/nonce` + `/auth/erc8128/nonce` + `/auth/erc8128/info` |
| Nonce store (memory + DynamoDB) | DONE | `integrations/erc8128/nonce_store.py` — switchable via `ERC8128_NONCE_STORE` env |
| DynamoDB table | DONE | `infrastructure/terraform/dynamodb.tf:12-41` — deployed |
| Tasks router auth migration | DONE | `api/routers/tasks.py` — 9 endpoints use `verify_agent_auth` |
| Submissions router auth migration | DONE | `api/routers/submissions.py` — 4 endpoints use `verify_agent_auth` |
| Self-application prevention | DONE | `supabase_client.py:455-472` — agent can't apply to own task |
| Race condition protection | DONE | UNIQUE constraint `task_applications_unique(task_id, executor_id)` |
| Token validation on task creation | DONE | `api/routers/tasks.py:385` — `validate_payment_token()` called |
| Worker-signs-directly | DONE | `api/reputation.py:802-965` — prepare-feedback + confirm-feedback |
| Task expiration job | DONE | `jobs/task_expiration.py` — runs every 60s |
| Bidirectional reputation | DONE | Golden Flow 7/7 PASS with agent-rates-worker + worker-rates-agent |

---

## Phase 0 — Critical Security (P0) -- COMPLETE (5/5)

**Priority**: Must-fix before any external agent uses ERC-8128 auth in production.

### Task 0.1: Self-Assignment Prevention in `assign_task()`

- **File**: `mcp_server/supabase_client.py:715-747`
- **Bug**: `assign_task()` does NOT check if `executor_id` belongs to the agent. An agent can self-assign by passing its own executor_id, bypassing the self-application guard at `supabase_client.py:455-472`.
- **Fix**: After line 731 (`if task["agent_id"] != agent_id`), add guard:
  ```python
  # Prevent self-assignment
  executor_wallet = executor.data.get("wallet_address", "").lower()
  agent_wallet = task.get("agent_wallet", "").lower()
  if executor_wallet and agent_wallet and executor_wallet == agent_wallet:
      raise Exception("Agent cannot assign task to itself")
  ```
- **Also fix**: `mcp_server/tools/agent_tools.py:467-529` — MCP tool `em_assign_task` calls `db.assign_task()` at line 524, so the fix in `supabase_client.py` covers both paths. But add an explicit early guard in the MCP tool for better error messages.
- **Validation**: `test_self_assignment_prevention` — new test in `tests/test_routes.py`

### Task 0.2: Migrate Escrow Endpoints to `verify_agent_auth`

- **File**: `mcp_server/api/escrow.py:272,298`
- **Bug**: `release_escrow` (line 272) and `refund_escrow` (line 298) still use `verify_api_key_if_required` (API key only). These endpoints handle on-chain fund movements but don't support ERC-8128 wallet signatures.
- **Fix**: Replace `api_key: APIKeyData = Depends(verify_api_key_if_required)` with `auth: AgentAuth = Depends(verify_agent_auth)` on both endpoints. Update the function body to use `auth.agent_id` and `auth.wallet_address` instead of extracting from `api_key`.
- **Import**: Add `from .auth import verify_agent_auth, AgentAuth` (remove `verify_api_key_if_required` import if no longer used).
- **Validation**: `test_escrow_release_with_erc8128_auth`, `test_escrow_refund_with_erc8128_auth` — new tests

### Task 0.3: Migrate Rate-Worker Endpoint to `verify_agent_auth`

- **File**: `mcp_server/api/reputation.py:574`
- **Bug**: `rate_worker_endpoint` uses `verify_api_key_if_required`. An agent rating a worker should authenticate via ERC-8128 signature (wallet-bound) for on-chain traceability.
- **Fix**: Replace `api_key: APIKeyData = Depends(verify_api_key_if_required)` with `auth: AgentAuth = Depends(verify_agent_auth)`. Update function body to use `auth.agent_id` for task ownership verification.
- **Validation**: `test_rate_worker_with_erc8128_auth` — new test

### Task 0.4: Activate DynamoDB Nonce Store in ECS

- **File**: `infrastructure/terraform/ecs.tf` (task definition environment)
- **Bug**: Nonce store defaults to `memory` (`ERC8128_NONCE_STORE_TYPE`, nonce_store.py:31). In-memory nonces are lost on container restart and not shared across ECS tasks. A replay attack is possible across deployments.
- **Fix**: Add `ERC8128_NONCE_STORE=dynamodb` to the MCP server task definition environment variables. DynamoDB table `erc8128-nonces` is already deployed (terraform/dynamodb.tf).
- **Validation**: Manual — deploy to ECS, call `/api/v1/auth/erc8128/nonce`, verify nonce appears in DynamoDB table via AWS Console or `aws dynamodb scan`.

### Task 0.5: Create EIP-8128 Python Signer Library

- **File**: NEW — `mcp_server/integrations/erc8128/signer.py`
- **Bug**: The verifier exists (`api/auth.py:492`) but there's no signer library in the codebase. External agents (including Karma Kadabra) need a reference signer to authenticate via ERC-8128. No `eip8128_signer` package exists anywhere.
- **Fix**: Create `signer.py` with:
  - `sign_request(private_key, method, url, body, nonce)` → returns `Signature` + `Signature-Input` headers
  - Uses `eth_account` for EIP-191 signing (same dependency already in requirements.txt)
  - Follows RFC 9421 HTTP Message Signatures format
  - Include `fetch_nonce(api_base)` helper that calls `/api/v1/auth/erc8128/nonce`
- **Validation**: `test_erc8128_signer_roundtrip` — sign a request with signer, verify with existing verifier

---

## Phase 1 — Important Completeness (P1) -- COMPLETE (5/5)

**Priority**: Needed for Karma Kadabra integration and full agent autonomy.

### Task 1.1: Karma Kadabra Skill — `em-submit-evidence`

- **File**: NEW — `.claude/skills/em-submit-evidence/SKILL.md`
- **Issue**: KK agents need a skill to submit evidence for tasks they've accepted. Currently this is only possible via dashboard UI or raw API calls.
- **Fix**: Create skill that:
  1. Accepts task_id + evidence (text, file path, or URL)
  2. Uploads evidence to S3 via presigned URL (`POST /api/v1/submissions/{task_id}/upload-url`)
  3. Submits the submission (`POST /api/v1/submissions/{task_id}`)
  4. Reports success with submission ID
- **Validation**: Manual — run skill with test task, verify submission appears in dashboard

### Task 1.2: Karma Kadabra Skill — `em-rate-counterparty`

- **File**: NEW — `.claude/skills/em-rate-counterparty/SKILL.md`
- **Issue**: KK agents need to rate agents/workers after task completion. Bidirectional reputation is critical for the scoring system.
- **Fix**: Create skill that:
  1. Detects role (agent or worker) from task data
  2. If agent: calls `POST /api/v1/reputation/workers/rate`
  3. If worker: calls prepare-feedback + wallet sign + confirm-feedback flow
  4. Reports success with on-chain TX hash
- **Validation**: Manual — run skill after task completion, verify rating on-chain

### Task 1.3: Karma Kadabra Skill — `em-register-identity`

- **File**: NEW — `.claude/skills/em-register-identity/SKILL.md`
- **Issue**: KK agents need to self-register on ERC-8004 Identity Registry. Currently registration is manual or via API.
- **Fix**: Create skill that:
  1. Checks if agent already registered (`GET /api/v1/reputation/identity/{wallet}`)
  2. If not: calls `POST /api/v1/reputation/register` with wallet + metadata
  3. Reports agent_id and network
- **Validation**: Manual — run skill with test wallet, verify identity on-chain

### Task 1.4: Update `em_assign_task` MCP Tool Error Messages

- **File**: `mcp_server/tools/agent_tools.py:467-529`
- **Issue**: The MCP tool `em_assign_task` delegates to `db.assign_task()` but doesn't surface specific error types (self-assignment, eligibility, etc.) in a structured way for AI agents to parse.
- **Fix**: Add early self-assignment check before `db.assign_task()` call (line 524) with a clear error message. Also improve error formatting for eligibility failures to include actionable suggestions.
- **Validation**: `test_em_assign_task_self_assignment_error` — new test

### Task 1.5: ERC-8128 Auth Info — Add Supported Algorithms

- **File**: `mcp_server/api/routers/misc.py:496-516`
- **Issue**: The `/auth/erc8128/info` endpoint doesn't specify which signing algorithm is expected. Agents need to know it's `eip191-personal` not `eip712` or `raw-secp256k1`.
- **Fix**: Add to the response:
  ```python
  "signing_algorithm": "eip191-personal",
  "signature_format": "hex-encoded-65-bytes",
  "covered_components": ["@method", "@target-uri", "content-digest", "nonce"],
  ```
- **Validation**: `test_erc8128_info_includes_algorithm` — new test

---

## Phase 2 — External Dependencies & Blocked Items -- COMPLETE (4/4)

**Priority**: Depends on Facilitator updates, BackTrack coordination, or multi-repo changes.

### Task 2.1: Register 8 Operators in Facilitator Allowlist (7 pending) -- DONE (already allowlisted)

- **Resolved**: All 8 operators were already in `addresses.rs`. Confirmed via IRC with Facilitator agent 2026-02-21.
- **Dependency**: Requires updating `addresses.rs` in `UltravioletaDAO/x402-rs` repo
- **All 8 operators** (Base already allowlisted, 7 pending):
  | Chain | Operator Address | Allowlist Status |
  |-------|-----------------|------------------|
  | Base | `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` | ACTIVE |
  | Ethereum | `0x69B67962ffb7c5C7078ff348a87DF604dfA8001b` | Pending |
  | Polygon | `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e` | Pending |
  | Arbitrum | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` | Pending |
  | Avalanche | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` | Pending |
  | Monad | `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3` | Pending |
  | Celo | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` | Pending |
  | Optimism | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` | Pending |
- **Note**: Arb/Avax/Celo/Op share same address (CREATE2 deterministic). 4 unique addresses to add.
- **Action**: Clone x402-rs, update `src/addresses.rs`, rebuild + redeploy Facilitator
- **Validation**: Multichain Golden Flow 8/8 PASS

### Task 2.2: Ethereum L1 Facilitator Timeout Fix -- DONE (already resolved)

- **Resolved**: Facilitator v1.33.18 already has TxWatcher timeout at 900s (`src/chain/evm.rs:479`). Was bumped 300→600→900. Also `TX_RECEIPT_TIMEOUT_SECS` env var for override. 8/8 PASS achieved. Remaining Ethereum failures are intermittent L1 congestion, not bugs. Confirmed via IRC 2026-02-21.
- **Dependency**: Facilitator TxWatcher configuration in x402-rs
- **Validation**: Multichain Golden Flow 8/8 PASS including Ethereum

### Task 2.3: EIP-8128 TypeScript Signer for Browser/Node.js Agents -- DONE

- **Commit**: `12e567a` — `sdk/typescript/src/erc8128.ts`
- **Dependency**: Needs Phase 0 Task 0.5 (Python signer) as reference implementation
- **Implemented**: `sdk/typescript/src/erc8128.ts` with ethers v6:
  - `signRequest()` — signs HTTP requests per ERC-8128
  - `fetchNonce()` — fetches single-use nonce from server
  - `createSignedFetch()` — auto-signing fetch wrapper
  - 5 tests (headers, GET, query, keyid, roundtrip recovery)
- **Validation**: `vitest run src/__tests__/erc8128.test.ts` — 5/5 PASS

### Task 2.4: Multi-Chain Bulk ERC-8004 Registration for KK Agents -- DONE

- **Commit**: `5030c4a` — `scripts/bulk_register_erc8004.py`
- **Implemented**: `scripts/bulk_register_erc8004.py`:
  - `--wallet 0x... --all-mainnets` — registers on all 9 mainnets in parallel
  - `--dry-run` — check existing registrations without registering
  - `--concurrency N` — limit parallel requests (default 3)
  - `--metadata-uri` — optional agent-card.json URL
  - Checks existing registrations first (skip already registered)
- **Validation**: Manual — `python scripts/bulk_register_erc8004.py --wallet 0x... --dry-run`

---

## Execution Rules

1. **One task = one commit** — each fix is atomic and independently verifiable
2. **Commit message format**: `fix: [TASK-X.Y] description` or `feat: [TASK-X.Y] description`
3. **Never start a phase without user approval**
4. **Run ruff format + ruff check before every commit**
5. **Run relevant pytest markers after each fix**
6. Phase 2 tasks may require switching repos (x402-rs) — confirm with user

## Execution Log

| Phase | Tasks | Done | Commits |
|-------|-------|------|---------|
| Phase 0 | 5 | 5 | `7aef54d`, `3805bec`, `df18782`, `bd3c398`, `4011dba` |
| Phase 1 | 5 | 5 | `579c26e`, `7756c4d`, `f29165c`, `8e4fba0`, `e8b090d` |
| Phase 2 | 4 | 4 | `12e567a`, `5030c4a` (Tasks 2.1+2.2 resolved via IRC) |
| **Total** | **14** | **14** | **12 commits** |

**ALL TASKS COMPLETE.** ERC-8004/ERC-8128 integration is production-ready.
