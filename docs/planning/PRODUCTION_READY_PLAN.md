# Execution Market: Production Ready Plan

## Executive Summary

This plan outlines the critical path to production for the x402 payment flow and ERC-8004 reputation integration. Based on comprehensive code analysis, we have identified **3 CRITICAL payment issues** and **3 CRITICAL reputation gaps** that must be fixed.

## Current State (as of 2026-02-04)

### x402 Payment Flow
| Flow | Status | Issue |
|------|--------|-------|
| Task Creation (Verify) | ✅ WORKS | Properly uses SDK verification |
| Submission Approval (Settle) | ❌ BROKEN | Wrong parameter type - passes tx_hash instead of X-Payment header |
| Task Cancellation (Refund) | ❌ MISSING | No refund logic whatsoever - funds get stuck |

### ERC-8004 Reputation
| Feature | Status | Issue |
|---------|--------|-------|
| Facilitator Client | ✅ WORKS | All methods implemented |
| EM Identity (Agent #469) | ✅ REGISTERED | On-chain identity exists |
| Rate Worker Function | ✅ EXISTS | But never called on payment approval |
| Auto-Reputation on Approve | ❌ MISSING | No feedback submitted after payment |
| Worker ERC-8004 Registration | ❌ MISSING | Registry class exists but never called |

---

## Critical Fixes Required

### Phase 1: Fix Payment Settlement (CRITICAL)

**Problem**: `approve_submission()` in routes.py calls `sdk.settle_task_payment()` with `escrow_tx` (a transaction hash), but the SDK expects the original `X-Payment` header.

**Root Cause**: During task creation, we verify the payment and store `escrow_tx` (the facilitator's deposit reference). But we don't store the original `X-Payment` header. At approval time, we need to either:
1. Store the original X-Payment header at task creation time, OR
2. Use the facilitator's `/settle` endpoint directly with the escrow reference

**Solution**: The x402 facilitator has a specific endpoint for settling payments by escrow reference. We need to use the escrow reference stored in the task, not try to reconstruct the X-Payment header.

**Files to Modify**:
- `mcp_server/api/routes.py` - Fix `approve_submission()` lines 765-771
- `mcp_server/integrations/x402/sdk_client.py` - Add `settle_by_escrow_ref()` method

### Phase 2: Add Cancellation Refund (CRITICAL)

**Problem**: `cancel_task()` in routes.py only updates DB status - no escrow refund happens.

**Solution**: Add refund call using the stored `escrow_tx` reference.

**Files to Modify**:
- `mcp_server/api/routes.py` - Add refund logic to `cancel_task()` at lines 897-930
- `mcp_server/integrations/x402/sdk_client.py` - Add `refund_by_escrow_ref()` method

### Phase 3: Trigger Reputation on Payment (CRITICAL)

**Problem**: When payment is released, no reputation feedback is submitted to ERC-8004.

**Solution**: After successful settlement, call `rate_worker()` with the payment tx as proof.

**Files to Modify**:
- `mcp_server/api/routes.py` - Add reputation call after settlement in `approve_submission()`
- `mcp_server/server.py` - Add reputation call in MCP `em_approve_submission` tool

---

## Detailed Implementation Tasks

### Task 1: Fix Settlement Parameter Issue
- [ ] Read current `settle_task_payment()` implementation
- [ ] Understand what the facilitator expects for settlement
- [ ] Create `settle_by_escrow_ref()` method that uses escrow reference
- [ ] Update `approve_submission()` to use new method
- [ ] Test settlement with live facilitator

### Task 2: Add Cancellation Refund
- [ ] Create `refund_by_escrow_ref()` method in sdk_client.py
- [ ] Update `cancel_task()` to call refund
- [ ] Handle refund failure gracefully
- [ ] Test refund with live facilitator

### Task 3: Integrate Reputation on Approval
- [ ] Import reputation functions in routes.py
- [ ] Add `rate_worker()` call after successful settlement
- [ ] Pass payment tx hash as proof
- [ ] Handle reputation failure gracefully (don't fail payment)
- [ ] Add logging for reputation submission

### Task 4: Create E2E Test Script
- [ ] Create test script that:
  - Creates task with x402 payment
  - Worker accepts and submits
  - Agent approves (payment released)
  - Verify reputation updated on-chain
  - Create another task and cancel (refund)
  - Verify refund received

---

## Test Scenarios

### Happy Path: Task Completion
```
1. Agent creates task with $5 bounty
2. X-Payment header verified via facilitator
3. Task stored with escrow_tx reference
4. Worker accepts task
5. Worker submits evidence
6. Agent approves submission
7. Payment settled: Worker receives $4.60 (92%), Treasury receives $0.40 (8%)
8. Reputation submitted: Worker gets positive rating with proof_tx
```

### Cancellation Path: Refund
```
1. Agent creates task with $5 bounty
2. Payment verified, task created
3. No workers accept
4. Agent cancels task
5. Refund issued via facilitator
6. Agent receives $5 back (full bounty + fee since no work done)
```

### Rejection Path: Task Reopened
```
1. Agent creates task
2. Worker accepts and submits (poor quality)
3. Agent rejects submission
4. Task status returns to 'published'
5. Escrow remains locked (worker can resubmit or new worker can accept)
6. Original worker gets negative reputation (optional)
```

---

## Architecture: Correct x402 Flow

```
                        ┌─────────────────────────────────┐
                        │         FACILITATOR             │
                        │  facilitator.ultravioletadao.xyz│
                        │                                 │
                        │  POST /verify (check signature) │
                        │  POST /settle (release payment) │
                        │  POST /refund (return to agent) │
                        └──────────────┬──────────────────┘
                                       │
                                       │ (gasless - facilitator pays gas)
                                       │
  ┌──────────────────┐                 │                ┌──────────────────┐
  │      AGENT       │◄────────────────┼────────────────│      WORKER      │
  │                  │                 │                │                  │
  │  Signs EIP-3009  │                 ▼                │ Receives USDC    │
  │  Authorization   │         ┌──────────────┐         │ after approval   │
  │  (X-Payment)     │         │   BASE       │         │                  │
  └──────────────────┘         │   MAINNET    │         └──────────────────┘
                               │              │
                               │  USDC Token  │
                               │  Escrow Vault│
                               └──────────────┘
```

---

## Environment Variables Required

```bash
# x402 Payment
X402_FACILITATOR_URL=https://facilitator.ultravioletadao.xyz
X402_NETWORK=base
EM_TREASURY_ADDRESS=0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad
EM_PLATFORM_FEE=0.08

# ERC-8004 Reputation
ERC8004_NETWORK=ethereum
EM_AGENT_ID=469
```

---

## Success Criteria

- [ ] Task creation verifies payment and stores escrow reference
- [ ] Submission approval releases payment to worker (92%) and treasury (8%)
- [ ] Submission approval triggers on-chain reputation feedback
- [ ] Task cancellation refunds agent in full
- [ ] All flows work via facilitator (gasless for users)
- [ ] E2E test passes with real USDC on Base mainnet

---

## Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1: Fix Settlement | 2-3 hours | TODO |
| Phase 2: Add Refund | 1-2 hours | TODO |
| Phase 3: Reputation | 1-2 hours | TODO |
| Phase 4: E2E Testing | 2-3 hours | TODO |
| **Total** | **6-10 hours** | **In Progress** |
