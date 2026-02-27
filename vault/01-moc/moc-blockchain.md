---
date: 2026-02-26
tags:
  - type/moc
  - domain/blockchain
status: active
aliases:
  - Blockchain MOC
  - Smart Contracts
  - On-Chain Contracts
  - Multichain
---

# Blockchain & Contracts — Map of Content

> Every on-chain contract, deployment address, stablecoin, and network configuration that powers Execution Market across 15 EVM networks.

---

## Production Networks (8 chains)

| Network | Chain ID | Escrow | Operator (Fase 5) | Stablecoins |
|---------|----------|--------|--------------------|-------------|
| **Base** | 8453 | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` | `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` | USDC, EURC |
| **Ethereum** | 1 | `0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0` | `0x69B67962ffb7c5C7078ff348a87DF604dfA8001b` | USDC, EURC, PYUSD, AUSD |
| **Polygon** | 137 | `0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6` | `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e` | USDC, AUSD |
| **Arbitrum** | 42161 | `0x320a3c35F131E5D2Fb36af56345726B298936037` | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` | USDC, USDT, AUSD |
| **Avalanche** | 43114 | `0x320a3c35F131E5D2Fb36af56345726B298936037` | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` | USDC, EURC, AUSD |
| **Monad** | 143 | `0x320a3c35F131E5D2Fb36af56345726B298936037` | `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3` | USDC, AUSD |
| **Celo** | 42220 | `0x320a3c35F131E5D2Fb36af56345726B298936037` | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` | USDC, USDT |
| **Optimism** | 10 | `0x320a3c35F131E5D2Fb36af56345726B298936037` | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` | USDC, USDT |

### Additional Networks (no escrow — identity/token registry only)

| Network | Chain ID | Stablecoins |
|---------|----------|-------------|
| HyperEVM | 999 | USDC |
| Unichain | 130 | USDC |
| Scroll | 534352 | USDC |

---

## Test Networks

| Network | Chain ID | Escrow | Stablecoins |
|---------|----------|--------|-------------|
| **Base Sepolia** | 84532 | `0x29025c0E22D4ef52e931E8B3Fb74073C32E4e5f2` | USDC |
| **Ethereum Sepolia** | 11155111 | `0x320a3c35dC6Ae4FF3ac05bB56D67C6f7f7e2b3c1` | USDC |
| Polygon Amoy | 80002 | — | USDC |
| Arbitrum Sepolia | 421614 | — | USDC |

Legacy Agent ID on Sepolia: **#469**. Production Agent ID on Base: **#2106**.

---

## Identity Contracts

### [[erc-8004]] Identity Registry

Deterministic CREATE2 deployment — same address on every supported chain:

| Variant | Address |
|---------|---------|
| **Mainnet** (all 9 mainnets) | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| **Testnet** (all 6 testnets) | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |

Execution Market is **Agent #2106** on Base mainnet. Registration, identity resolution, and metadata updates all go through the Facilitator (`POST /register`) — gasless.

### [[erc-8004-reputation]] Reputation Registry

| Variant | Address |
|---------|---------|
| **Mainnet** (all mainnets, CREATE2) | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` |

Bidirectional reputation: agent rates worker via Facilitator `/feedback`, worker rates agent via on-chain `giveFeedback()`. 15 networks supported (9 mainnets + 6 testnets).

---

## Escrow Contracts

### [[auth-capture-escrow]] (AuthCaptureEscrow)

Shared singleton per chain. Holds funds in TokenStore clones (EIP-1167 minimal proxies). This is **Layer 1** of the x402r escrow architecture.

| Chain | Address |
|-------|---------|
| Base | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` |
| Ethereum | `0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0` |
| Polygon | `0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6` |
| Arbitrum, Avalanche, Celo, Monad, Optimism | `0x320a3c35F131E5D2Fb36af56345726B298936037` |

Operations: `authorize` (lock funds) / `release` (pay receiver) / `refund` (return to payer). All gasless via Facilitator.

---

## Payment Operators

### [[payment-operator]] (Fase 5 — Trustless Fee Split)

**Layer 2** of x402r. Per-config contract with pluggable conditions and fee calculator. Deployed by `scripts/deploy-payment-operator.ts`.

| Chain | Address |
|-------|---------|
| **Base** | `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` |
| **Ethereum** | `0x69B67962ffb7c5C7078ff348a87DF604dfA8001b` |
| **Polygon** | `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e` |
| **Arbitrum** | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |
| **Avalanche** | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |
| **Celo** | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |
| **Optimism** | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |
| **Monad** | `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3` |

Arbitrum, Avalanche, Celo, and Optimism share the same address via CREATE2 deterministic deployment.

**Fee model (credit card convention):** Agent pays gross bounty. At release, `StaticFeeCalculator` splits atomically: worker receives 87%, operator holds 13%. `distributeFees(USDC)` flushes accumulated fees to treasury.

---

## Support Contracts

### [[static-fee-calculator]]

| Chain | Address |
|-------|---------|
| Base | `0xd643DB63028Cd1852AAFe62A0E3d2A5238d7465A` |

Configured at **1300 BPS** (13%). Plugs into PaymentOperator to split payments on-chain at release time. Other chains use the `staticFeeCalculatorFactory` from x402r infrastructure to deploy per-chain instances.

### [[facilitator-eoa]]

| Address | `0x103040545AC5031A11E8C03dd11324C7333a13C7` |
|---------|----------------------------------------------|

The Facilitator EOA pays gas on all chains. It is the off-chain relay that converts signed EIP-3009 authorizations into on-chain transactions. Part of **Layer 3** of the x402r architecture.

Facilitator URL: `https://facilitator.ultravioletadao.xyz`

---

## Stablecoins

### [[usdc-stablecoins]]

**USDC is the primary payment token.** All 15 networks have USDC configured. Additional stablecoins vary by chain.

| Token | Networks | Decimals |
|-------|----------|----------|
| **USDC** | All 15 (8 prod + 3 extra + 4 test) | 6 |
| **EURC** | Base, Ethereum, Avalanche | 6 |
| **USDT** | Arbitrum, Celo, Optimism | 6 |
| **AUSD** (Agora Dollar) | Ethereum, Polygon, Arbitrum, Avalanche, Monad | 6 |
| **PYUSD** (PayPal USD) | Ethereum | 6 |

### USDC Addresses (Production)

| Chain | USDC Address |
|-------|-------------|
| Base | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Ethereum | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` |
| Polygon | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` |
| Arbitrum | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` |
| Avalanche | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` |
| Monad | `0x754704Bc059F8C67012fEd69BC8A8327a5aafb603` |
| Celo | `0xcebA9300f2b948710d2653dD7B07f33A8B32118C` |
| Optimism | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` |

---

## Deployment

### [[create2-deployments]]

Deterministic deployment via CREATE2 ensures the same address across all chains for:
- ERC-8004 Identity Registry (mainnet + testnet variants)
- ERC-8004 Reputation Registry
- AuthCaptureEscrow (shared across Arbitrum, Avalanche, Celo, Monad, Optimism)
- PaymentOperator (shared across Arbitrum, Avalanche, Celo, Optimism)

This simplifies configuration: a single address can be hardcoded for multiple chains.

### [[protocol-fee-config]]

Controlled by **BackTrack** (Ali), not Ultravioleta. Per-chain contract that sets an x402r protocol-level fee.

| Parameter | Value |
|-----------|-------|
| Hard cap | 5% |
| Timelock | 7 days |
| Current state | Read dynamically from chain |

When enabled, the x402r protocol deducts its fee before our fee calculator runs. Our treasury absorbs the difference: `treasury_gets = 13% - protocol_fee%`. Worker always gets 100% of net bounty. Code reads `ProtocolFeeConfig` address from `NETWORK_CONFIG.x402r_infra.protocolFeeConfig`.

Base ProtocolFeeConfig: `0x59314674BAbb1a24Eb2704468a9cCdD50668a1C6`

---

## Network Registry

**Single source of truth:** `mcp_server/integrations/x402/sdk_client.py` — the `NETWORK_CONFIG` dictionary.

- **15 EVM networks**: 8 production (escrow + operator), 3 additional (identity/token only), 4 testnets
- **5 stablecoins**: USDC, EURC, USDT, AUSD, PYUSD
- **10 networks with x402r escrow** (8 prod + 2 test)
- **8 networks with Fase 5 operators** (all production chains)

Other Python files (`facilitator_client.py`, tests, `platform_config.py`) **auto-derive** from `NETWORK_CONFIG`. No manual updates needed when adding a network — just update `sdk_client.py`.

### Adding a New Chain

Use the **`add-network` skill** (`.claude/skills/add-network/SKILL.md`) for the complete checklist. High-level steps:

1. Add entry to `NETWORK_CONFIG` in `sdk_client.py`
2. Deploy PaymentOperator via `scripts/deploy-payment-operator.ts`
3. Register operator in Facilitator allowlist (`addresses.rs` in `x402-rs`)
4. Fund Facilitator EOA with native gas token on the new chain
5. Run Golden Flow on the chain to validate

---

## Upstream Relationship

### [[x402r-team-relationship]]

| Entity | Controls | Does NOT control |
|--------|----------|------------------|
| **Ultravioleta DAO** (us) | Facilitator, PaymentOperators, SDK integration, deployment | x402r contracts, ProtocolFeeConfig |
| **Ali / BackTrack** | x402r protocol contracts, SDK (`@x402r/sdk`), ProtocolFeeConfig | Facilitator, our operators, our fee config |

**The Facilitator is OURS.** Repo: `UltravioletaDAO/x402-rs`. We deploy, control, and maintain it. Ali/BackTrack provides the protocol-level contracts and SDK only.

Upstream repos:
- `github.com/BackTrackCo/x402r-contracts` — Foundry (Solidity)
- `github.com/BackTrackCo/x402r-sdk` — TypeScript monorepo (pnpm)
- `github.com/BackTrackCo/docs` — Mintlify (docs.x402r.org)

---

## Source Files

| File | Purpose |
|------|---------|
| `mcp_server/integrations/x402/sdk_client.py` | `NETWORK_CONFIG` dict — single source of truth (15 networks, 5 stablecoins) |
| `scripts/deploy-payment-operator.ts` | Deploy Fase 5 PaymentOperator on any chain |
| `scripts/register-agents-erc8004.ts` | Register agent NFTs on ERC-8004 registry |
| `mcp_server/integrations/erc8004/facilitator_client.py` | ERC-8004 identity + reputation via Facilitator |
| `mcp_server/integrations/x402/advanced_escrow_integration.py` | Advanced escrow flow documentation |
| `scripts/kk/` | KK V2 fund distribution across 8 chains for 24 agents |

## Documentation

| Doc | Path |
|-----|------|
| x402r full reference | `docs/planning/X402R_REFERENCE.md` |
| Contract address table | `CLAUDE.md` (On-Chain Contracts section) |
| Payment architecture | `docs/planning/PAYMENT_ARCHITECTURE.md` |
| Golden Flow multichain report | `docs/reports/GOLDEN_FLOW_REPORT.md` |

---

## Cross-Links

- [[moc-payments]] — Payment flows (Fase 1, 2, 5) that use these contracts for settlement
- [[moc-agents]] — Karma Kadabra V2 swarm (24 agents) funded on all 8 production chains
- [[moc-infrastructure]] — RPC policy: always prefer QuikNode private RPCs from `.env.local`
- [[moc-identity]] — ERC-8004 registries and ERC-8128 authentication use these on-chain contracts
- [[moc-architecture]] — Server components that orchestrate contract interactions via SDK
- [[moc-security]] — On-chain escrow provides trustless fund protection
