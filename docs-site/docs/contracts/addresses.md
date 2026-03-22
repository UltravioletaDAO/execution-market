# Contract Addresses

All smart contracts deployed for Execution Market. Many use CREATE2 for deterministic addresses across networks.

## ERC-8004 Identity Contracts

| Contract | Network | Address |
|----------|---------|---------|
| Identity Registry | All Mainnets (CREATE2) | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| Identity Registry | All Testnets (CREATE2) | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| Reputation Registry | All Mainnets (CREATE2) | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` |

Same address on: Base, Ethereum, Polygon, Arbitrum, Avalanche, Optimism, Celo, Monad (and more) via CREATE2.

## AuthCaptureEscrow Contracts

| Network | Address |
|---------|---------|
| Base | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` |
| Ethereum | `0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0` |
| Polygon | `0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6` |
| Arbitrum | `0x320a3c35F131E5D2Fb36af56345726B298936037` |
| Avalanche | `0x320a3c35F131E5D2Fb36af56345726B298936037` |
| Celo | `0x320a3c35F131E5D2Fb36af56345726B298936037` |
| Monad | `0x320a3c35F131E5D2Fb36af56345726B298936037` |
| Optimism | `0x320a3c35F131E5D2Fb36af56345726B298936037` |

The same address on Arbitrum, Avalanche, Celo, Monad, and Optimism is due to CREATE2 deterministic deployment.

## PaymentOperator Contracts (Fase 5 — Trustless Fee Split)

| Network | Address |
|---------|---------|
| **Base** | `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` |
| Ethereum | `0x69B67962ffb7c5C7078ff348a87DF604dfA8001b` |
| Polygon | `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e` |
| Arbitrum | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |
| Avalanche | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |
| Celo | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |
| Monad | `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3` |
| Optimism | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |

## Fee Calculator

| Contract | Network | Address |
|----------|---------|---------|
| StaticFeeCalculator (1300 BPS = 13%) | Base | `0xd643DB63028Cd1852AAFe62A0E3d2A5238d7465A` |

## Facilitator EOA

| Role | Address |
|------|---------|
| Facilitator EOA (pays gas for all TXs) | `0x103040545AC5031A11E8C03dd11324C7333a13C7` |

## Agent Identity

| Property | Value |
|----------|-------|
| Execution Market Agent ID | **2106** (Base Mainnet) |
| Legacy Agent ID | 469 (Sepolia — deprecated) |

## Verify on Block Explorers

- **Base**: [basescan.org — Identity Registry](https://basescan.org/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432)
- **Base**: [basescan.org — Agent #2106](https://basescan.org/token/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432?a=2106)
- **Ethereum**: [etherscan.io — Identity Registry](https://etherscan.io/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432)
- **Polygon**: [polygonscan.com — Identity Registry](https://polygonscan.com/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432)

## Source Code

All contract source code is in `contracts/` in the repository.

x402r contracts maintained by BackTrack:
- [github.com/BackTrackCo/x402r-contracts](https://github.com/BackTrackCo/x402r-contracts)
