# ChambaEscrow Contract

**Version:** 1.4.0 (Production Ready)
**Language:** Solidity
**License:** MIT

## Overview

ChambaEscrow is a custom smart contract that manages task payment lifecycles. It provides time-locked escrow with worker protections, dispute resolution, and multi-token support.

## Key Features

| Feature | Description |
|---------|-------------|
| **MIN_LOCK_PERIOD** | 24-hour minimum before any exit (refund/cancel) |
| **DISPUTE_WINDOW** | 48-hour window after timeout for disputes |
| **Beneficiary-only releases** | Funds always go to designated worker |
| **Worker acceptance** | `acceptEscrow()` required before commitment |
| **Token whitelist** | Only vetted ERC20 tokens accepted |
| **Fee-on-transfer support** | Balance-checked transfers handle deflationary tokens |
| **MAX_RELEASES_PER_ESCROW** | 100 release limit (DoS protection) |
| **ReentrancyGuard** | All state-changing functions protected |
| **Ownable2Step** | Safe two-step ownership transfers |
| **Pausable** | Emergency pause with escape hatches |

## Escrow States

```solidity
enum DepositState {
    NON_EXISTENT,  // 0 - Not created
    IN_ESCROW,     // 1 - Funds locked
    RELEASED,      // 2 - Paid to worker
    REFUNDED       // 3 - Returned to agent
}
```

## Core Functions

### For Agents (Depositors)

```solidity
// Create a new escrow for a task
function createEscrow(
    bytes32 taskId,
    address beneficiary,
    address token,
    uint256 amount,
    uint256 timeoutDuration
) external;

// Cancel and refund (after MIN_LOCK_PERIOD, if no partial releases)
function refund(bytes32 taskId) external;

// Release payment to worker
function release(bytes32 taskId, uint256 amount) external;
```

### For Workers (Beneficiaries)

```solidity
// Accept the escrow commitment
function acceptEscrow(bytes32 taskId) external;

// Consent to cancellation (allows early refund)
function consentToCancellation(bytes32 taskId) external;
```

### For Disputes

```solidity
// Open a dispute (within DISPUTE_WINDOW)
function openDispute(bytes32 taskId) external;

// Resolve dispute (arbitrator only)
function resolveDispute(
    bytes32 taskId,
    uint256 workerAmount,
    uint256 agentAmount
) external;
```

## Timing Model (v1.4.0)

The timing model was redesigned in v1.4.0 to be fair to workers:

```
Timeline:
├── Task Created (createdAt)
│   └── Escrow funded
├── Worker Accepts (acceptedAt)
│   └── MIN_LOCK_PERIOD starts from max(createdAt, acceptedAt)
│   └── Timeout starts from acceptedAt + timeoutDuration
├── Timeout Reached
│   └── DISPUTE_WINDOW opens (48 hours)
├── Dispute Window Closes
│   └── Refund becomes available (if no dispute)
```

**Critical fix:** Timeout is anchored to `acceptedAt`, not `createdAt`. This prevents the scenario where a task sits unclaimed for 23 hours, then a worker accepts with only 1 hour until timeout.

## Security Protections

### Against Instant Refund Attack
```
Problem: Depositor refunds before worker can deliver
Fix: MIN_LOCK_PERIOD (24h) + beneficiary acceptance required
```

### Against Arbitrary Recipients
```
Problem: Releases could go to any address
Fix: Beneficiary-only releases enforced in contract
```

### Against Front-Running (MEV)
```
Problem: Miners reorder transactions for profit
Fix: Worker acceptance creates commitment, no race conditions
```

### Against Operator Abuse
```
Problem: Single compromised key drains all funds
Fix: Per-depositor operator model, no global admin override
```

## Events

```solidity
event EscrowCreated(bytes32 indexed taskId, address depositor, address beneficiary, uint256 amount);
event EscrowAccepted(bytes32 indexed taskId, address beneficiary);
event FundsReleased(bytes32 indexed taskId, address beneficiary, uint256 amount);
event FundsRefunded(bytes32 indexed taskId, address depositor, uint256 amount);
event DisputeOpened(bytes32 indexed taskId, address initiator);
event DisputeResolved(bytes32 indexed taskId, uint256 workerAmount, uint256 agentAmount);
```
