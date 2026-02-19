# Multi-chain Fase 5 PaymentOperator Deployment Report

**Date**: 2026-02-18
**Deployer**: `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd`
**Facilitator**: `0x103040545AC5031A11E8C03dd11324C7333a13C7`
**Config**: Fase 5 — StaticFeeCalculator(1300 BPS = 13%), OR(Payer|Facilitator) release, Facilitator-ONLY refund

---

## Summary

Deployed Fase 5 PaymentOperators on **4 new chains** (Polygon, Arbitrum, Avalanche, Monad), bringing the total to **5 chains with active operators**. Fixed incorrect x402r sub-factory addresses across all 7 non-Base chains by auditing the [x402r-sdk source of truth](https://github.com/BackTrackCo/x402r-sdk/blob/main/packages/core/src/config/index.ts).

### Deployment Status

| Chain | Operator Address | TX Count | Status |
|-------|-----------------|----------|--------|
| **Base** | `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` | — | Active (deployed 2026-02-13) |
| **Polygon** | `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e` | 4 TXs | Deployed, pending Facilitator allowlist |
| **Arbitrum** | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` | 4 TXs | Deployed, pending Facilitator allowlist |
| **Avalanche** | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` | 4 TXs | Deployed, pending Facilitator allowlist |
| **Monad** | `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3` | 4 TXs | Deployed, pending Facilitator allowlist |
| Ethereum | — | — | Pending (L1 RPC timeout, needs retry) |
| Celo | — | — | Blocked (0 CELO on deployer) |
| Optimism | — | — | Blocked (0 ETH on deployer) |

> Note: Arbitrum and Avalanche share the same operator address due to CREATE2 deterministic deployment (same factory + same config = same address). Monad differs because it has a different `usdcTvlLimit` parameter.

---

## What Was Done

### 1. Address Audit

Audited the x402r-sdk repo (`packages/core/src/config/index.ts`) and discovered that ALL 7 non-Base chains had **wrong sub-factory addresses** in our config. The addresses shared prefixes but had different suffixes — likely from an earlier version of the SDK.

**Key finding**: Sub-factory addresses are NOT CREATE2-identical across chains. There are 3 groups:
- **Ethereum**: Unique addresses
- **Polygon**: Unique addresses
- **Arb/Celo/Monad/Avax/Op**: Shared addresses (same factories deployed by BackTrack)

### 2. Config Updates

Updated both config files with correct SDK addresses:

- **`scripts/deploy-payment-operator.ts`** (`CHAIN_CONFIGS`): All 7 non-Base chain configs corrected
- **`mcp_server/integrations/x402/sdk_client.py`** (`NETWORK_CONFIG.x402r_infra`): All 7 non-Base chains corrected

Fields updated per chain: `staticAddressConditionFactory`, `orConditionFactory`, `staticFeeCalculatorFactory`, `protocolFeeConfig`, `usdcTvlLimit`, `tokenCollector`, `payerCondition`

Also fixed: Polygon RPC URL changed from `polygon-rpc.com` (unreliable) to `polygon-bor-rpc.publicnode.com`

### 3. Factory Bytecode Pre-check

Added in previous commit: the deploy script now verifies on-chain bytecode of all 4 factory contracts before attempting any deployment. This prevents gas waste on wrong addresses.

### 4. Deployments

Each deployment creates 4 contracts:
1. `StaticFeeCalculator(1300bps)` — 13% fee split
2. `StaticAddressCondition(Facilitator)` — authorizes `0x1030...`
3. `OrCondition([PayerCondition, FacilitatorCondition])` — release condition
4. `PaymentOperator` — the operator itself

All 4 deployed chains passed 5/5 on-chain verification checks.

### 5. Per-chain Operator Resolution

Updated `sdk_client.py` with deployed operator addresses. The `PaymentDispatcher` resolves operators per-network via `NETWORK_CONFIG[network]["operator"]`.

---

## Remaining Work

### Ethereum (High Priority)
- L1 RPC (`eth.llamarpc.com`) timed out during deployment
- **Action**: Retry with QuikNode RPC or wait for L1 congestion to clear
- Gas estimate: ~0.002 ETH (~$5)

### Celo (Medium Priority)
- Deployer has 0 CELO
- **Action**: Fund `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd` with ~0.5 CELO
- Sub-factories verified present (dry-run passed)

### Optimism (Medium Priority)
- Deployer has 0 ETH on Optimism
- **Action**: Fund deployer with ~0.0005 ETH on Optimism
- Sub-factories verified present (dry-run passed)

### Facilitator Allowlist (All New Chains)
- All 4 newly deployed operators need to be registered in the Facilitator's `addresses.rs` allowlist
- Contact: IRC `#Agents` channel or direct coordination with Facilitator team
- Operators to register:
  - Polygon: `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e`
  - Arbitrum: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
  - Avalanche: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
  - Monad: `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3`

---

## Contracts Deployed (Detail)

### Polygon (Chain 137)
| Contract | Address |
|----------|---------|
| StaticFeeCalculator(1300bps) | *(deployed via factory)* |
| StaticAddressCondition(Facilitator) | *(deployed via factory)* |
| OrCondition(Payer\|Facilitator) | *(deployed via factory)* |
| **PaymentOperator** | **`0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e`** |

### Arbitrum (Chain 42161)
| Contract | Address |
|----------|---------|
| StaticFeeCalculator(1300bps) | *(deployed via factory)* |
| StaticAddressCondition(Facilitator) | *(deployed via factory)* |
| OrCondition(Payer\|Facilitator) | *(deployed via factory)* |
| **PaymentOperator** | **`0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`** |

### Avalanche (Chain 43114)
| Contract | Address |
|----------|---------|
| StaticFeeCalculator(1300bps) | *(deployed via factory)* |
| StaticAddressCondition(Facilitator) | *(deployed via factory)* |
| OrCondition(Payer\|Facilitator) | *(deployed via factory)* |
| **PaymentOperator** | **`0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`** |

### Monad (Chain 143)
| Contract | Address |
|----------|---------|
| StaticFeeCalculator(1300bps) | *(deployed via factory)* |
| StaticAddressCondition(Facilitator) | *(deployed via factory)* |
| OrCondition(Payer\|Facilitator) | *(deployed via factory)* |
| **PaymentOperator** | **`0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3`** |

---

## Deploy Skill

Created `.claude/skills/deploy-operator/SKILL.md` — reusable skill for future deployments. Reference it when needing to deploy or redeploy operators.
