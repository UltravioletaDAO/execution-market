---
date: 2026-02-26
tags:
  - domain/blockchain
  - reference
  - concept/contracts
status: active
aliases:
  - Contract Addresses
  - Deployed Contracts
  - On-Chain Contracts
related-files:
  - mcp_server/integrations/x402/sdk_client.py
  - scripts/deploy-payment-operator.ts
---

# Contract Addresses

Master reference of all deployed contracts across all chains.

## ERC-8004 Identity Registry (CREATE2 -- same address all chains)

| Scope | Address |
|-------|---------|
| All Mainnets | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| All Testnets | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |

## ERC-8004 Reputation Registry (CREATE2)

| Scope | Address |
|-------|---------|
| All Mainnets | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` |

## AuthCaptureEscrow (Layer 1 Singletons)

| Chain | Address |
|-------|---------|
| Base | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` |
| Ethereum | `0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0` |
| Polygon | `0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6` |
| Arbitrum, Avalanche, Celo, Monad, Optimism | `0x320a3c35F131E5D2Fb36af56345726B298936037` |

## PaymentOperator (Fase 5 -- Trustless Fee Split)

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

## Other Contracts

| Contract | Chain | Address |
|----------|-------|---------|
| StaticFeeCalculator (1300 BPS) | Base | `0xd643DB63028Cd1852AAFe62A0E3d2A5238d7465A` |
| Facilitator EOA | All | `0x103040545AC5031A11E8C03dd11324C7333a13C7` |

## Agent Identity

| Registry | Network | Agent ID |
|----------|---------|----------|
| Production | Base | **2106** |
| Legacy | Sepolia | 469 |

## Related

- [[erc-8004]] -- identity and reputation protocol
- [[payment-operator]] -- Fase 5 trustless fee split contracts
- [[auth-capture-escrow]] -- Layer 1 escrow singletons
