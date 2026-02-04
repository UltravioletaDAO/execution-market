# Execution Market Escrow Contracts

Smart contracts for Execution Market's escrow system - enabling secure payments for human-executed tasks with partial release support.

## Overview

The `ChambaEscrow` contract provides:

- **ERC20 Escrow**: Lock USDC or other ERC20 tokens for task payments
- **Partial Releases**: Support for milestone-based payments (e.g., 30% on submission, 70% on approval)
- **Timeout Protection**: Automatic refund eligibility after configurable timeout
- **Operator System**: Authorized addresses can manage releases (for automated systems)
- **Release History**: Full audit trail of all fund movements

## Contract Architecture

```
ChambaEscrow.sol
├── createEscrow()     - Lock funds for a task
├── releaseEscrow()    - Release funds (partial or full)
├── refundEscrow()     - Return remaining funds to depositor
├── cancelEscrow()     - Cancel before work starts (full refund)
└── Admin functions    - Operator management
```

## Quick Start

```bash
# Install dependencies
npm install

# Compile contracts
npm run compile

# Run tests
npm test

# Start local node
npm run node

# Deploy to localhost (in another terminal)
npm run deploy:localhost
```

## Deployment

### Local Development

```bash
# Terminal 1: Start Hardhat node
npm run node

# Terminal 2: Deploy
npm run deploy:localhost
```

### Base Sepolia (Testnet)

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your private key and RPC URL

npm run deploy:base-sepolia
```

### Base Mainnet

```bash
npm run deploy:base
```

## Usage Example

```solidity
// 1. Approve escrow contract to spend USDC
usdc.approve(escrowAddress, amount);

// 2. Create escrow for a task
bytes32 taskId = keccak256("task-123");
uint256 timeout = 7 days;
escrow.createEscrow(taskId, workerAddress, usdcAddress, amount, timeout);

// 3. Release on submission (30%)
escrow.releaseEscrow(escrowId, workerAddress, amount * 30 / 100, "submission");

// 4. Release on approval (70%)
escrow.releaseEscrow(escrowId, workerAddress, amount * 70 / 100, "approval");
```

## Key Features

### Partial Releases

The contract supports any release schedule:

| Milestone | Percentage | Reason |
|-----------|------------|--------|
| Submission | 30% | Worker submitted deliverable |
| Approval | 70% | Depositor approved work |

### Timeout Mechanism

- **Before any release**: Depositor can cancel/refund anytime
- **After partial release**: Must wait for timeout to refund remaining

### Operator System

Operators are authorized addresses that can release funds on behalf of depositors:

```solidity
// Owner authorizes an operator (e.g., backend service)
escrow.setOperator(operatorAddress, true);

// Operator can now release funds
escrow.releaseEscrow(escrowId, recipient, amount, "operator release");
```

## Contract Addresses

| Network | Address | Explorer |
|---------|---------|----------|
| Base Sepolia | TBD | [Basescan](https://sepolia.basescan.org) |
| Base Mainnet | TBD | [Basescan](https://basescan.org) |

## Security

- Uses OpenZeppelin's `SafeERC20` for token transfers
- `ReentrancyGuard` on all state-changing functions
- Comprehensive access control
- Timeout protection for depositors

## Testing

```bash
# Run all tests
npm test

# Run with gas reporting
REPORT_GAS=true npm test

# Run with coverage
npm run test:coverage
```

## License

MIT
