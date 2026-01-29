# ChambaEscrow Deployment Log

## Overview

This document tracks all ChambaEscrow smart contract deployments across supported networks.

---

## Ethereum Mainnet Deployment

**Date**: 2026-01-29
**Deployer**: `0xD577D66e9398433AB278CceD3b5987a061E132A0`

### Contract Addresses

| Contract | Address | Verified |
|----------|---------|----------|
| ChambaEscrow | `0x6c320efaC433690899725B3a7C84635430Acf722` | Pending |
| USDC | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | N/A (Circle) |

### Transaction Details

| Field | Value |
|-------|-------|
| TX Hash | `0x31e7d1f2342ca001cea3c2823f8531c18ed41cda108e989f3153b4ef464d9c10` |
| Block | 24341410 |
| Gas Used | 1,702,018 |

### Links

- Etherscan: https://etherscan.io/address/0x6c320efaC433690899725B3a7C84635430Acf722
- Transaction: https://etherscan.io/tx/0x31e7d1f2342ca001cea3c2823f8531c18ed41cda108e989f3153b4ef464d9c10

### Verification Command

```bash
forge verify-contract 0x6c320efaC433690899725B3a7C84635430Acf722 contracts/ChambaEscrow.sol:ChambaEscrow --chain-id 1 --watch
```

---

## Avalanche Mainnet Deployment (v2)

**Date**: 2026-01-28
**Deployer**: `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd`

### Contract Addresses

| Contract | Address | Verified |
|----------|---------|----------|
| ChambaEscrow | `0xedA98AF95B76293a17399Af41A499C193A8DB51A` | ✅ |
| USDC (Native) | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` | N/A (Circle) |

### Verification

| Platform | Status | URL |
|----------|--------|-----|
| Snowtrace | ✅ Verified | https://snowtrace.io/address/0xedA98AF95B76293a17399Af41A499C193A8DB51A#code |
| Sourcify | ✅ Verified | https://repo.sourcify.dev/contracts/full_match/43114/0xedA98AF95B76293a17399Af41A499C193A8DB51A/ |

### Changes from v1
- Fixed security contact email: `ultravioletadao@gmail.com`
- Previous contract: `0xae99aB957d6648BeB8ecd26F64e62919C5a6925a` (deprecated)

### Contract Details

- **Version**: 1.0.0
- **Solidity**: 0.8.24
- **Optimizer**: Enabled (200 runs)
- **viaIR**: true

### Initial State

```
Owner: 0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd
Next Escrow ID: 1
Paused: false
```

---

## AWS Secrets Manager

| Secret Name | Description | Created |
|-------------|-------------|---------|
| `chamba/commission` | Platform commission wallet (Ledger cold wallet) | 2026-01-27 |
| `chamba/contracts` | Deployed contract addresses by network | 2026-01-27 |
| `chamba/api-keys` | Block explorer API keys (Snowtrace, etc.) | 2026-01-27 |

### Commission Wallet

- **Address**: `0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad`
- **Type**: Ledger (cold wallet)
- **Purpose**: Receive platform fees from task completions

---

## Security Audit Summary

### Audited: 2026-01-27

**Findings Addressed:**

| ID | Severity | Issue | Fix |
|----|----------|-------|-----|
| M-01 | Medium | Unsafe `emergencyWithdraw` could drain escrowed funds | Added `_totalLocked` tracking, only allows withdrawal of surplus |
| M-02 | Medium | No pause mechanism for emergencies | Added `Pausable` from OpenZeppelin |
| L-01 | Low | No version tracking | Added `VERSION` constant |

### Security Features

1. **ReentrancyGuard**: Protects all state-changing functions
2. **SafeERC20**: Safe token transfers
3. **Pausable**: Emergency pause capability
4. **Ownable**: Access control for admin functions
5. **Operator System**: Authorized release managers
6. **Timeout Protection**: Configurable escrow timeouts (1h - 365d)

---

## Deployment Commands Reference

```bash
# Compile
npx hardhat compile

# Test
npx hardhat test

# Deploy to specific network
npx hardhat run scripts/deploy.ts --network <network>

# Verify on block explorer
npx hardhat verify --network <network> <contract-address>

# Available networks:
# Mainnets: ethereum, base, avalanche, polygon, optimism, arbitrum, celo, bsc, scroll
# Testnets: ethereumSepolia, baseSepolia, avalancheFuji, polygonAmoy, optimismSepolia, arbitrumSepolia, celoAlfajores, bscTestnet, scrollSepolia
```

---

## Pending Deployments

| Network | Chain ID | Status | Priority |
|---------|----------|--------|----------|
| Ethereum | 1 | ✅ Deployed | High |
| Base | 8453 | ⏳ Pending | High |
| Polygon | 137 | ⏳ Pending | Medium |
| Optimism | 10 | ⏳ Pending | Medium |
| Arbitrum | 42161 | ⏳ Pending | Medium |

---

## Changelog

### 2026-01-29
- Deployed to Ethereum mainnet
- Contract: `0x6c320efaC433690899725B3a7C84635430Acf722`
- TX: `0x31e7d1f2342ca001cea3c2823f8531c18ed41cda108e989f3153b4ef464d9c10`
- Updated platform config to use Ethereum as preferred network
- Updated scripts to use Ethereum mainnet addresses

### 2026-01-28
- Redeployed to Avalanche mainnet (v2)
- Fixed security contact email to `ultravioletadao@gmail.com`
- New address: `0xedA98AF95B76293a17399Af41A499C193A8DB51A`
- Contract verified on Snowtrace and Sourcify

### 2026-01-27
- Initial deployment to Avalanche mainnet
- Contract verified on Snowtrace and Sourcify
- AWS secrets configured for commission wallet and contract addresses
- Security audit completed with all findings addressed
