# Supported Networks

## Primary Networks

Execution Market's x402 integration supports payments across multiple EVM-compatible networks. The facilitator at `facilitator.ultravioletadao.xyz` handles cross-chain routing.

### Production Networks

| Network | Chain ID | USDC Address | Status |
|---------|----------|-------------|--------|
| **Base** | 8453 | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | **Primary** |
| **Polygon** | 137 | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | Active |
| **Optimism** | 10 | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` | Active |
| **Arbitrum** | 42161 | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | Active |

### Testnet Networks

| Network | Chain ID | USDC Address | Status |
|---------|----------|-------------|--------|
| **Base Sepolia** | 84532 | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | Testing |
| **Sepolia** | 11155111 | Test token | Testing |

### Additional Networks (via Facilitator)

The x402 facilitator supports **17+ mainnets** including:
- Ethereum, BSC, Avalanche, Fantom, Gnosis, Celo, zkSync, Linea, Scroll, Mantle, and more.

## Supported Tokens

| Token | Decimals | Networks |
|-------|----------|----------|
| **USDC** | 6 | All networks (primary) |
| **EURC** | 6 | Base, Ethereum |
| **DAI** | 18 | Base, Ethereum, Polygon |
| **USDT** | 6 | All networks |

## x402r Escrow Contracts

### Base Mainnet

| Contract | Address |
|----------|---------|
| **Escrow** | `0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC` |
| **DepositRelayFactory** | `0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814` |
| **RefundRequest** | `0x55e0Fb85833f77A0d699346E827afa06bcf58e4e` |
| **MerchantRouter** | `0xa48E8AdcA504D2f48e5AF6be49039354e922913F` |
| **USDC** | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |

### Base Sepolia (Testnet)

| Contract | Address |
|----------|---------|
| **Escrow** | `0xF7F2Bc463d79Bd3E5Cb693944B422c39114De058` |
| **Factory** | `0xf981D813842eE78d18ef8ac825eef8e2C8A8BaC2` |
| **USDC** | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` |

## ChambaEscrow Deployments

| Network | Address | Status |
|---------|---------|--------|
| **Ethereum Mainnet** | `0x6c320efaC433690899725B3a7C84635430Acf722` | Deployed |
| **Avalanche Mainnet** | `0xedA98AF95B76293a17399Af41A499C193A8DB51A` | Deployed & Verified |

## Network Selection

The recommended network for Execution Market payments is **Base** due to:
- Low gas costs (~$0.01 per transaction)
- USDC native support
- x402r escrow contract availability
- High throughput and reliability
