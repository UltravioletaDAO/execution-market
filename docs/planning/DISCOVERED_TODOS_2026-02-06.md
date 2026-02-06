# Discovered TODOs — Session 2026-02-06 (granular-tasks)

Items discovered during Batch 0-3 execution that are **not explicitly tracked** in the existing batch plan, or that add important context to existing tasks.

---

## P0 — Must Fix Before Launch

### TODO-D00: Workers Never Receive USDC — Treasury Collects Everything — FIXED
**Severity**: CRITICAL (P0)
**Status**: FIXED (commit `94c6e30`, deployed task def rev 22)
**Discovered during**: P0-PAY-006 live test with separate worker wallet

**The Problem**: ALL x402 payments go to the EM Treasury (`0xae07ceb6...`), NOT to the worker. The EIP-3009 `TransferWithAuthorization` is signed with `to: EM_TREASURY` (hardcoded in `test-x402-rapid-flow.ts:304` and in task creation flow). When the facilitator settles, it executes `agent → treasury`. The `worker_address` parameter in `sdk_client.py:settle_task_payment` is accepted but **never used for the on-chain transfer** — it's only metadata.

**On-chain proof** (tx `0xa1c8a8b0d0dd2d34e4f826e626560c49bb03dac587e625d2167338c1d7c5d2a4`):
- Transfer event: `0x857fe6...` (agent) → `0xae07ceb6...` (treasury) = 0.01 USDC
- Worker wallet `0xb8463eb3...` received ZERO
- Code records this tx as `submission.payment_tx` — dashboard shows it as "worker paid"

**Architecture gap**: The platform collects from agents but has no disbursement step (treasury → worker). Two approaches:
1. **Split payment**: Sign two EIP-3009 auths (one agent→worker, one agent→treasury for fee)
2. **Treasury disbursement**: After settle, treasury sends USDC to worker (requires treasury private key in MCP server)
3. **Escrow-based**: Use `AdvancedEscrowClient.charge()` which handles split payments

**Impact**: No worker has ever been paid through x402. All $0.03 from test tasks went to treasury.

### TODO-D01: Self-Payment Bug (Agent Wallet = Worker Wallet)
**Severity**: HIGH (but less critical than D00 since workers aren't paid anyway)
**Discovered during**: P0-PAY-001 live test

The rapid flow test used the same wallet for agent and worker (`0x857fe6...`). The payment went through successfully — USDC moved from agent to agent via the facilitator. The self-payment check in `routes.py:580-606` compares `worker_address` with `agent_id`, but `agent_id` is the API key identifier (e.g., `em_starter`), NOT the wallet address. So the check never catches wallet-to-wallet self-payment.

**Fix**: Compare `worker_address.lower()` against the agent's actual wallet address (from the task's payment authorization or the `api_keys` table).

**Payment TX that should have been blocked**: `0xe3640e0d5bc147d1621aa103a1da1f2c965c1659204eb2b1d152da8dca61b440`

### TODO-D02: `payments` Table Doesn't Exist in Live DB
**Severity**: MEDIUM
**Discovered during**: P0-PAY-003 analysis

Migration 016 adds `settlement_method` to `payments`, but the `payments` table itself may not exist in the live DB (noted in admin dashboard fixes). All payment inserts are wrapped in try/except so they fail silently. This means **no payment audit trail is being persisted**.

**Fix**: Create the `payments` table via migration if it doesn't exist. Verify with `SELECT * FROM information_schema.tables WHERE table_name = 'payments'`.

### TODO-D03: `escrows` Table Doesn't Exist in Live DB
**Severity**: MEDIUM
**Same root cause as TODO-D02.**

The `escrows` table is referenced throughout the code but may not exist. All financial stats in the admin dashboard were already reworked to derive from `tasks.bounty_usd` instead.

**Fix**: Either create the table or remove all references and document that payment tracking lives in the `tasks` table fields (`escrow_tx`, `escrow_amount_usdc`, `refund_tx`).

---

## P1 — Important But Not Blocking Launch

### TODO-D04: Agent #469 Registered on Ethereum Mainnet, NOT Base
**Severity**: MEDIUM
**Discovered during**: ecosystem deep scan (2026-02-06)

Agent #469 is registered on Ethereum Mainnet Identity Registry (`0x8004A169...`), but all payments and operations run on **Base**. The agent needs re-registration on Base (~$0.01 gas). This requires a direct contract call since the facilitator is READ-ONLY for identity.

**Relates to**: Batch 6 (ERC-8004 Integration) — should be added as a prerequisite task.
**Script exists**: `scripts/register-erc8004-base.ts` (package.json has `register:erc8004:base`)

### TODO-D05: ANTHROPIC_API_KEY Not in ECS Task Definition
**Severity**: LOW (mock mode is safe)
**Discovered during**: P0-PAY-001 live test (evidence verification returned `approved` with `confidence=0.85` — mock mode)

AI evidence verification runs in mock mode because `ANTHROPIC_API_KEY` is not in the ECS task definition secrets. AWS Secret `em/anthropic` was created but never wired to ECS.

**Fix**: Add `ANTHROPIC_API_KEY` to ECS task def from `em/anthropic` secret.
**Relates to**: Batch 10 (Deployment & Ops) — add as sub-task.

### TODO-D06: ERC8004_NETWORK and EM_AGENT_ID Not in ECS Task Def
**Severity**: LOW (hardcoded defaults work)
**Same root cause as TODO-D05.**

These env vars aren't in the ECS task definition, so the server uses hardcoded defaults. Should be configurable.

### TODO-D07: x402r_escrow.py ABI Mismatch — Deprecation Needed
**Severity**: LOW (unused in production flow)
**Discovered during**: ecosystem deep scan

`mcp_server/integrations/x402/x402r_escrow.py` has an ABI that doesn't match the actual contract (e.g., `merchantBalance` doesn't exist). The file is only used by direct-call scripts. After full migration to `EscrowClient` from the SDK, this file should be removed.

**Fix**: After Batch 6 migration to SDK escrow, delete `x402r_escrow.py`.
**Relates to**: Batch 6 or Batch 9 (cleanup).

### TODO-D08: Python SDK "base-mainnet" vs Facilitator "base" Naming
**Severity**: LOW
**Discovered during**: ecosystem deep scan

The Python SDK may use `"base-mainnet"` as the network identifier while the facilitator uses `"base"`. This could cause silent failures in reputation/identity calls. Needs verification.

**Verify**: Call `Erc8004Client.get_identity("base", 469)` vs `"base-mainnet"` and compare results.

---

## P2 — Future / Nice to Have

### TODO-D09: Funded Escrow Refund (USDC Actually Moves Back)
**Severity**: FUTURE
**Discovered during**: P0-PAY-001 refund test

The current architecture uses verify-then-settle (authorize → settle on approval). Cancellation just lets the authorization expire — no USDC moves back because it never moved forward. A **true funded escrow refund** requires the `AdvancedEscrowClient` flow: `authorize → release/refund_in_escrow`.

**Relates to**: Batch 4 P0-PAY-007, Batch 9 P2-TEST-002, Batch 11 T-003 all mention "funded refund" but none describe the architecture change needed.
**SDK class**: `AdvancedEscrowClient` (authorize, release, refund_in_escrow, charge) — Base only.

### TODO-D10: $0.10 USDC Stuck in Vault
**Severity**: LOW
**Known issue from 2026-02-04.**

$0.10 USDC from direct relay deposit (tx `0xda31cbe...`) is stuck in the vault. Needs refund via `EscrowClient.request_refund()` (gasless) or wait for contract expiry.

### TODO-D12: Modify uvd-x402-sdk to Support Custom payTo in settle_payment() — FIXED
**Severity**: MEDIUM
**Status**: FIXED (SDK v0.8.1 published to PyPI, commit `736acd7`)
**Discovered during**: TODO-D00 fix (2026-02-06)

Added `pay_to: Optional[str] = None` parameter to `verify_payment()`, `settle_payment()`, `process_payment()`, and `verify_only()`. When set, overrides `config.recipient_evm` in `_build_payment_requirements()`.

**Release**: https://github.com/UltravioletaDAO/uvd-x402-sdk-python/releases/tag/v0.8.1
**Install**: `pip install uvd-x402-sdk==0.8.1`

### TODO-D14: Agent's Original Auth Never Settled — Platform Pays From Own Wallet
**Severity**: HIGH (P0)
**Status**: OPEN
**Discovered during**: Architecture review after TODO-D00 fix (2026-02-06)

**The Problem**: When a task is approved, `settle_task_payment()` signs TWO NEW EIP-3009 auths from the **platform wallet** (`0x3403...`). The agent's original auth (stored in `task.escrow_tx`) is **never settled**. This means:
- The agent never actually pays USDC
- The platform wallet pays workers from its own balance ($29.97)
- When the platform wallet runs out, all payments stop
- The original auth just expires unused

**Correct flow** (two-step settlement):
```
1. SETTLE agent's original auth  →  Agent pays Platform (full bounty)
2. Platform signs new auth       →  Platform pays Worker (bounty - fee)
3. Fee stays in platform wallet
```

**Fix** (in `sdk_client.py:settle_task_payment()`):
```python
# Step 0: Settle agent's original auth (agent → platform wallet)
payload = self.client.extract_payload(payment_header)
settle_resp = self.client.settle_payment(payload, bounty_amount)
# Now platform wallet has the USDC from the agent

# Step 1: Disburse to worker (existing code)
# Step 2: Collect fee (existing code, or just keep it)
```

**Prerequisites**:
- Agent's auth.to must point to the platform wallet (`0x3403...`), NOT the treasury
- Test scripts need to sign auths to platform wallet address
- SDK v0.8.1 with `pay_to` ✅ (for cases where auth.to differs from config)

**Relates to**: Batch 5 or next payment batch. ~15 lines of code change.

### TODO-D13: On-Chain Splitter Contract for Automated Fee Distribution
**Severity**: FUTURE (post-MVP)
**Discovered during**: TODO-D00 fix discussion (2026-02-06)

The current split payment uses TWO separate EIP-3009 auths signed at approval time (agent→worker + agent→treasury). This works for MVP but has limitations:
- Requires agent's private key in MCP server
- Two separate on-chain txs per payout
- Fee logic is application-level, not auditable on-chain

**Better long-term approach**: Deploy a **PaymentSplitter** contract:
1. Escrow releases USDC to splitter address
2. Splitter auto-distributes: worker gets (100% - fee), treasury gets fee
3. Fee percentage configurable via admin function
4. Single on-chain tx, fully auditable

**Alternatives considered**:
- `AdvancedEscrowClient.charge()` — SDK supports it, but agent pays gas (not gasless)
- Disbursement account pattern — intermediate wallet that the platform controls

**Current MVP approach** (dual EIP-3009 auths) is sufficient for launch. Splitter contract should be prioritized for production at scale.

### TODO-D11: SubmissionForm.tsx Bypasses Service Layer
**Severity**: MEDIUM
**Known bug from CLAUDE.md.**

`SubmissionForm.tsx` uses direct Supabase insert (bypasses `services/submissions.ts`), fails silently on RLS if executor.user_id is null. The proper `EvidenceUpload.tsx` component (with camera, GPS, EXIF) exists but is unused.

**Relates to**: Batch 7 (Evidence Pipeline) — but the service layer fix should happen sooner.

### TODO-D15: Add Mermaid Diagrams to Documentation
**Severity**: LOW (documentation quality)
**Status**: OPEN

Add Mermaid diagrams to key documentation files for visual clarity:
- **Payment flow**: Task creation → verify → approve → settle → disburse (in CLAUDE.md or dedicated doc)
- **Task lifecycle**: State machine (PUBLISHED → ACCEPTED → ... → COMPLETED/DISPUTED)
- **Auth flow**: Dynamic.xyz → wallet → executor lookup → session
- **Infrastructure**: ECS → ALB → Route53 → CloudFront
- **Escrow states**: AUTHORIZED → RELEASED / CANCELLED

**Target files**: CLAUDE.md, SPEC.md, PLAN.md, `docs/planning/` docs
**Format**: GitHub-flavored Mermaid (renders in GitHub, VS Code, and most Markdown viewers)

---

## Suggested Additions to Existing Batches

| TODO | Add To | As |
|------|--------|----|
| ~~TODO-D00 (worker not paid)~~ | ~~Batch 4.5~~ | **FIXED** — Split payment via dual EIP-3009 auths (commit `94c6e30`) |
| TODO-D01 (self-payment) | **Batch 4** | P0-PAY-008: Fix self-payment detection (compare wallets, not API key IDs) |
| TODO-D02 (payments table) | **Batch 4** | P0-PAY-009: Create `payments` table in live DB |
| TODO-D03 (escrows table) | **Batch 8** | P1-DB-002: Decide escrows table fate (create or remove refs) |
| TODO-D04 (Base registration) | **Batch 6** | P1-ERC-000: Re-register Agent #469 on Base (prerequisite) |
| TODO-D05 (ANTHROPIC_API_KEY) | **Batch 10** | P2-OPS-004: Wire remaining secrets to ECS |
| TODO-D06 (ERC env vars) | **Batch 10** | Same as D05 |
| TODO-D07 (ABI deprecation) | **Batch 9** | P2-TEST-006: Remove x402r_escrow.py after SDK migration |
| TODO-D09 (funded refund) | **Batch 6** | P1-ERC-006: Migrate to AdvancedEscrowClient for true funded escrow |
| TODO-D11 (SubmissionForm) | **Batch 7** | P1-EVID-000: Fix SubmissionForm to use service layer (prerequisite) |
| ~~TODO-D12 (SDK pay_to)~~ | ~~SDK~~ | **FIXED** — SDK v0.8.1 published to PyPI (commit `736acd7`) |
| TODO-D14 (agent auth not settled) | **Batch 5** | P0-PAY-010: Settle agent's original auth before disbursing to worker |
| TODO-D15 (mermaid diagrams) | **Batch 8** | P1-DOC-001: Add Mermaid diagrams to key docs for visual clarity |
