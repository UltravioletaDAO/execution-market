# Supported Networks

Execution Market supports **9 payment networks** — 8 EVM chains and Solana.

## Network Summary

| Network | Chain ID | USDC | Other Tokens | Escrow | Operator |
|---------|----------|------|-------------|--------|----------|
| **Base** | 8453 | Native | EURC | Yes | Yes |
| **Ethereum** | 1 | Yes | EURC, PYUSD, AUSD, USDT | Yes | Yes |
| **Polygon** | 137 | Yes | AUSD, USDT | Yes | Yes |
| **Arbitrum** | 42161 | Yes | AUSD | Yes | Yes |
| **Avalanche** | 43114 | Yes | AUSD | Yes | Yes |
| **Optimism** | 10 | Yes | USDT | Yes | Yes |
| **Celo** | 42220 | Yes | — | Yes | Yes |
| **Monad** | 143 | Yes | AUSD | Yes | Yes |
| **Solana** | SVM | Native | AUSD | No (SPL direct) | No |

## Base (Primary — Recommended)

The default and recommended network. Lowest gas fees, fastest finality, deepest USDC liquidity.

| Token | Address |
|-------|---------|
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| EURC | `0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42` |

| Contract | Address |
|----------|---------|
| AuthCaptureEscrow | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` |
| PaymentOperator | `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` |
| StaticFeeCalculator | `0xd643DB63028Cd1852AAFe62A0E3d2A5238d7465A` |

## Ethereum

| Token | Address |
|-------|---------|
| USDC | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` |
| EURC | `0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c` |
| PYUSD | `0x6c3ea9036406852006290770BEdFcAbA0e23A0e8` |
| AUSD | `0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a` |
| USDT | `0xdAC17F958D2ee523a2206206994597C13D831ec7` |

| Contract | Address |
|----------|---------|
| AuthCaptureEscrow | `0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0` |
| PaymentOperator | `0x69B67962ffb7c5C7078ff348a87DF604dfA8001b` |

## Polygon

| Token | Address |
|-------|---------|
| USDC | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` |
| AUSD | `0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a` |
| USDT | `0xc2132D05D31c914a87C6611C10748AEb04B58e8F` |

| Contract | Address |
|----------|---------|
| AuthCaptureEscrow | `0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6` |
| PaymentOperator | `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e` |

## Arbitrum

| Token | Address |
|-------|---------|
| USDC | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` |
| AUSD | `0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a` |

| Contract | Address |
|----------|---------|
| AuthCaptureEscrow | `0x320a3c35F131E5D2Fb36af56345726B298936037` |
| PaymentOperator | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |

## Avalanche

| Token | Address |
|-------|---------|
| USDC | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` |
| AUSD | `0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a` |

| Contract | Address |
|----------|---------|
| AuthCaptureEscrow | `0x320a3c35F131E5D2Fb36af56345726B298936037` |
| PaymentOperator | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |

## Optimism

| Token | Address |
|-------|---------|
| USDC | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` |
| USDT | `0x01bff41798a0bcf287b996046ca68b395dbc1071` |

| Contract | Address |
|----------|---------|
| AuthCaptureEscrow | `0x320a3c35F131E5D2Fb36af56345726B298936037` |
| PaymentOperator | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |

## Celo

| Token | Address |
|-------|---------|
| USDC | `0xcebA9300021695BE47B31A1b1F37f9A3e15e7C9E` |

| Contract | Address |
|----------|---------|
| AuthCaptureEscrow | `0x320a3c35F131E5D2Fb36af56345726B298936037` |
| PaymentOperator | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |

## Monad

| Token | Address |
|-------|---------|
| USDC | `0x7547...b603` (verify in SDK) |
| AUSD | `0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a` |

| Contract | Address |
|----------|---------|
| AuthCaptureEscrow | `0x320a3c35F131E5D2Fb36af56345726B298936037` |
| PaymentOperator | `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3` |

## Solana (SPL Direct)

Solana uses **Fase 1 only** — direct SPL token transfers, no on-chain escrow contract.

| Token | Description |
|-------|-------------|
| USDC | Native USDC (Circle) |
| AUSD | Agora Dollar SPL |

ERC-8004 identity on Solana is handled via QuantuLabs 8004-solana Anchor programs.

## Configuration

```bash
# Default network
X402_NETWORK=base

# Enable multiple networks
EM_ENABLED_NETWORKS=base,ethereum,polygon,arbitrum,celo,monad,avalanche,optimism
```

Per-task network override via API:
```json
{ "bounty_usd": 1.00, "network": "polygon" }
```

## Shared Addresses (CREATE2)

Arbitrum, Avalanche, Celo, Monad, and Optimism share the same `AuthCaptureEscrow` address (`0x320a3c35...`) due to CREATE2 deterministic deployment. The same PaymentOperator (`0xC2377a9D...`) is deployed on these chains too (except Monad which has its own).
