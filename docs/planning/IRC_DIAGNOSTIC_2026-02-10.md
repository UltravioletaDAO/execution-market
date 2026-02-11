# IRC Diagnostic Session — Application Status Review

**Date:** 2026-02-10
**Channel:** #execution-market-facilitator @ irc.meshrelay.xyz
**Participants:** claude-exec-market, claude-facilitator, claude-python-sdk, claude-ts-sdk
**Requested by:** zeroxultravioleta
**Topic:** "Todo está a medias, no funcionan los pagos, no está listo el escrow, qué vamos a hacer"

---

## Diagnosis Summary

### What WORKS

| Component | Status | Details |
|-----------|--------|---------|
| MCP Server | OK | 63 endpoints REST API + MCP transport, deployed ECS Fargate |
| Dashboard | OK | React SPA at execution.market, workers can browse/submit |
| Task Lifecycle | OK | publish/accept/submit/approve/cancel — full cycle in DB |
| ERC-8004 Identity | OK | Agent #2106 on Base, gasless registration via facilitator (15 networks) |
| AI Verification | OK | Multi-provider (Anthropic/OpenAI/Bedrock) |
| Evidence Pipeline | OK | S3 + CloudFront CDN for uploads |
| Admin Dashboard | OK | admin.execution.market with full task/payment management |
| Payment Audit Trail | OK | `payment_events` table tracking all payment operations |
| Facilitator | OK | v1.31.2, 22 mainnets, 5 stablecoins, all endpoints operational |
| ERC-8004 Endpoints | OK | /register, /feedback, /reputation — all confirmed working |

### What's BROKEN / NOT WORKING

| Issue | Severity | Details |
|-------|----------|---------|
| End-to-end payments | **CRITICAL** | Preauth mode verifies auth but settlement flow (3-step via platform wallet) not tested with real money |
| Fund loss bug | PATCHED | $1.404 USDC lost — recipient_evm pointed to treasury. Fixed with preauth default, but architectural fix needed |
| Escrow on-chain | UNUSABLE | AuthCaptureEscrow deployed on 9 networks but release()/refund() need direct on-chain TX (no gasless) |
| Platform wallet risk | HIGH | 0xD386 is hot wallet transit point; if settle succeeds but disburse fails, funds stuck |
| x402r mode | DEPRECATED | Caused fund loss by settling at creation time. Do not use. |
| Network coverage | GAP | We have 15 EVM / 8 enabled; facilitator has 22 mainnets including non-EVM |

---

## Key Findings from IRC

### 1. The Facilitator is NOT the bottleneck
- Facilitator v1.31.2 is fully operational
- POST /verify, POST /settle work correctly
- The fund loss bug was 100% on our side (wrong recipient_evm)
- ERC-8004 endpoints (/register, /feedback, /reputation) all confirmed working

### 2. POST /settle does NOT have a `pay_to` field
- **Critical correction**: The recipient is determined by the `to` field in the EIP-3009 auth itself
- The agent signs `transferWithAuthorization(from=agent, to=recipient, value, ...)`
- The facilitator just executes what the auth says
- For Fase 1: agent signs auth1(to=worker) and auth2(to=treasury) separately

### 3. /register and /feedback DO exist in the facilitator
- Initial confusion: facilitator said they didn't exist
- **Corrected**: Facilitator verified and confirmed ALL ERC-8004 endpoints are active
- Our `facilitator_client.py` integration is correct

### 4. Facilitator now supports 22+ mainnets
We're missing: HyperEVM, Unichain, Scroll, Sei, BSC (EVM), XDC, XRPL_EVM, Fogo, SKALE, Solana, NEAR, Stellar, Algorand, Sui

### 5. Nonce management for dual settlements
- Use UNIQUE nonces per settle: `keccak256(taskId + type + timestamp)`
- If a settle fails, generate a NEW nonce — never retry with the same one
- Retry with exponential backoff

---

## Agreed Action Plan

### ACCION 1: Implement Fase 1 "Auth on Approve" (EXEC-MARKET, immediate)
- **Owner:** claude-exec-market
- **What:** Refactor `payment_dispatcher.py`
  - Task creation: only POST /verify (confirm agent has funds, no settlement)
  - Task approval: agent signs 2 EIP-3009 auths → 2x POST /settle
    - Auth 1: agent → worker (92% of bounty)
    - Auth 2: agent → treasury (8% fee)
  - Eliminate platform wallet from flow entirely
- **Facilitator changes:** ZERO
- **SDK changes:** ZERO

### ACCION 2: Create E2E Automated Test (EXEC-MARKET, immediate)
- **Owner:** claude-exec-market
- **What:** Script that tests full lifecycle:
  1. Create task ($0.10)
  2. Worker accepts
  3. Worker submits evidence
  4. Agent approves
  5. Verify on-chain: worker got 92%, treasury got 8%
- **Environment:** Base testnet first, then mainnet
- **Facilitator support:** Available to verify tx hashes from their logs

### ACCION 3: settle_dual() Helper (EXEC-MARKET, short-term)
- **Owner:** claude-exec-market (SDK teams didn't confirm)
- **What:** Local wrapper that:
  - Executes 2 settlements atomically with retry logic
  - Validates auth.to == target before sending
  - Uses unique nonces per settle
  - Retry with exponential backoff, new nonce on failure

### ACCION 4: Escrow Gasless — Fase 2 (FACILITATOR + x402r, future)
- **Owner:** Facilitator team + x402r team
- **Prerequisites:**
  - `captureToAddress()` added to PaymentOperator contract
  - Redeployment on 9+ networks
  - Facilitator wallet registered as operator via `addOperator()`
- **Facilitator will implement:**
  - POST /escrow/release (gasless)
  - POST /escrow/refund (gasless)
  - HMAC-SHA256 auth
- **Timeline:** When x402r team can redeploy contracts

### ACCION 5: Update Token Registry (EXEC-MARKET, short-term)
- **Owner:** claude-exec-market
- **What:** Add new networks the facilitator supports
- **Priority order:**
  - TIER 1 (cheap gas, USDC ready): Scroll, Sei, Unichain
  - TIER 2: BSC, Fogo, SKALE
  - TIER 3: XDC, XRPL_EVM, HyperEVM
  - Non-EVM (future): Solana, NEAR, Stellar, Algorand, Sui

---

## Technical Details Confirmed

| Parameter | Value |
|-----------|-------|
| Facilitator URL | `https://facilitator.ultravioletadao.xyz` |
| Facilitator Version | v1.31.2 |
| Facilitator Mainnets | 22 (17 EVM + 5 non-EVM) |
| Facilitator Stablecoins | USDC (22 networks), EURC (3), USDT (4), AUSD (8), PYUSD (1) |
| ERC-8004 Reputation | Optimism mainnet + Sepolia |
| Settle gas (Base) | $0.001-0.003 per tx |
| Settle gas (Polygon) | $0.002-0.005 per tx |
| Settle gas (Ethereum) | $0.50-3.00 per tx |
| Escrow status | Deployed (9 networks), not gasless yet |
| Protocol versions | v1 (network string) + v2 (CAIP-2), auto-detection |

---

## Session Notes

- Server was very unstable — 6 reconnections during the session
- SDK teams (python + ts) were intermittently connected, couldn't get full confirmation
- Facilitator was the most reliable participant, provided detailed technical answers
- Key false alarm: facilitator initially said /register and /feedback don't exist, then corrected themselves after checking source code

---

*Document generated 2026-02-10 post-IRC session.*
