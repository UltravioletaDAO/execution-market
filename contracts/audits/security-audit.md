# ChambaEscrow Security Audit Report

**Auditor:** Smart Contract Security Specialist Agent
**Date:** 2026-01-29
**Contract:** ChambaEscrow V1
**Status:** 11 VULNERABILITIES IDENTIFIED

---

## Findings Summary

| # | Severity | Title |
|---|----------|-------|
| 1 | CRITICAL | Depositor Can Instantly Refund Before Beneficiary Claims |
| 2 | HIGH | Release to Arbitrary Recipient Allows Fund Diversion |
| 3 | HIGH | Fee-on-Transfer Tokens Break Accounting |
| 4 | HIGH | Rebasing Tokens Break Invariants |
| 5 | MEDIUM | Task ID to Escrow Mapping Not Cleared |
| 6 | MEDIUM | Missing Events for Critical State Changes |
| 7 | MEDIUM | Beneficiary Cannot Be Changed |
| 8 | MEDIUM | No Minimum Escrow Amount |
| 9 | LOW | Pause Functionality Incomplete |
| 10 | LOW | Missing Getter Functions |
| 11 | LOW | Operator Enumeration Not Possible |

---

## Detailed Findings

### 1. CRITICAL: Depositor Can Instantly Refund Before Beneficiary Claims

**Description:**
The `refundEscrow` function allows the depositor to immediately refund the full escrow amount if `escrow.released == 0`, completely bypassing the timeout mechanism.

**Vulnerable Code:**
```solidity
function refundEscrow(uint256 escrowId) external nonReentrant {
    if (escrow.released > 0) {
        require(block.timestamp >= escrow.timeout, "timeout not reached");
    }
    // If released == 0, no timeout check!
}
```

**Attack Scenario:**
1. Alice creates escrow for 1000 USDC for Bob
2. Bob completes the task and submits evidence
3. Before release confirms, Alice front-runs with `refundEscrow`
4. Alice steals 1000 USDC, Bob gets nothing

**Fix:**
```solidity
// ALWAYS require timeout for depositor-initiated refunds
require(block.timestamp >= escrow.timeout, "timeout not reached");
```

---

### 2. HIGH: Release to Arbitrary Recipient Allows Fund Diversion

**Description:**
The `releaseEscrow` function allows releasing to ANY address, not just the designated beneficiary.

**Vulnerable Code:**
```solidity
function releaseEscrow(uint256 escrowId, address recipient, ...)
{
    require(recipient != address(0), "invalid recipient");
    // No check that recipient == escrow.beneficiary!
    IERC20(escrow.token).safeTransfer(recipient, amount);
}
```

**Fix:**
```solidity
// Always pay the designated beneficiary
IERC20(escrow.token).safeTransfer(escrow.beneficiary, amount);
```

---

### 3. HIGH: Fee-on-Transfer Tokens Break Accounting

**Description:**
Contract assumes amount received equals amount specified. For fee-on-transfer tokens, `_totalLocked` will be incorrect.

**Fix:**
```solidity
uint256 balanceBefore = IERC20(token).balanceOf(address(this));
IERC20(token).safeTransferFrom(msg.sender, address(this), amount);
uint256 actualAmount = IERC20(token).balanceOf(address(this)) - balanceBefore;
escrow.amount = actualAmount;
_totalLocked[token] += actualAmount;
```

---

### 4. HIGH: Rebasing Tokens Break Invariants

**Description:**
Rebasing tokens change balance automatically. Fixed `amount` tracking becomes inconsistent.

**Fix:**
Token whitelist - only allow vetted tokens.

---

### 5. MEDIUM: Task ID to Escrow Mapping Not Cleared

**Description:**
`_taskToEscrow[taskId]` is never cleared on refund/cancel.

**Fix:**
```solidity
delete _taskToEscrow[escrow.taskId];
```

---

### 6-11. Additional Findings

See full report for details on:
- Missing events
- Immutable beneficiary
- No minimum amount
- Incomplete pause
- Missing getters
- No operator enumeration

---

## Recommendations

1. **Immediate:** Fix refund timeout and release recipient validation
2. **Short-term:** Add token whitelist and balance-checked transfers
3. **Long-term:** Add dispute mechanism and operator accountability
