# Contract Addresses

## x402r Escrow System (Production)

### Base Mainnet (Chain ID: 8453)

| Contract | Address | Purpose |
|----------|---------|---------|
| **Escrow** | [`0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC`](https://basescan.org/address/0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC) | Main escrow for task payments |
| **DepositRelayFactory** | [`0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814`](https://basescan.org/address/0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814) | Deterministic proxy deployment |
| **RefundRequest** | [`0x55e0Fb85833f77A0d699346E827afa06bcf58e4e`](https://basescan.org/address/0x55e0Fb85833f77A0d699346E827afa06bcf58e4e) | Refund processing |
| **MerchantRouter** | [`0xa48E8AdcA504D2f48e5AF6be49039354e922913F`](https://basescan.org/address/0xa48E8AdcA504D2f48e5AF6be49039354e922913F) | Merchant registration & routing |
| **USDC** | [`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`](https://basescan.org/address/0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913) | Circle USDC token |

### Base Sepolia Testnet (Chain ID: 84532)

| Contract | Address |
|----------|---------|
| **Escrow** | `0xF7F2Bc463d79Bd3E5Cb693944B422c39114De058` |
| **Factory** | `0xf981D813842eE78d18ef8ac825eef8e2C8A8BaC2` |
| **USDC** | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` |

## ChambaEscrow (Custom Contract)

### Deployments

| Network | Address | TX Hash | Status |
|---------|---------|---------|--------|
| **Ethereum Mainnet** | [`0x6c320efaC433690899725B3a7C84635430Acf722`](https://etherscan.io/address/0x6c320efaC433690899725B3a7C84635430Acf722) | `0x31e7d1f2...` | Deployed (v1.0, pre-audit) |
| **Avalanche Mainnet** | [`0xedA98AF95B76293a17399Af41A499C193A8DB51A`](https://snowscan.xyz/address/0xedA98AF95B76293a17399Af41A499C193A8DB51A) | - | Deployed & Verified (v2) |

> **Note:** The Ethereum mainnet deployment (`0x6c320e...`) is the **pre-audit** version with known vulnerabilities. The production-ready contract is v1.4.0 (post 5 audit rounds). New deployments use x402r escrow contracts on Base.

## ERC-8004 Identity Registry

| Property | Value |
|----------|-------|
| **Network** | Sepolia (testnet) |
| **Registry** | [`0x8004A818BFB912233c491871b3d84c89A494BD9e`](https://sepolia.etherscan.io/address/0x8004A818BFB912233c491871b3d84c89A494BD9e) |
| **Agent ID** | **469** |
| **Registration TX** | [`0xf04d7c3c86adf948acc8358180fea05c89645058150891cde21fa946cc748608`](https://sepolia.etherscan.io/tx/0xf04d7c3c86adf948acc8358180fea05c89645058150891cde21fa946cc748608) |
| **IPFS Metadata** | [`QmZJaHCf4u9Wy9hPusKF9bpV69Jr3E6ZAVXHZCinfMrjbL`](https://gateway.pinata.cloud/ipfs/QmZJaHCf4u9Wy9hPusKF9bpV69Jr3E6ZAVXHZCinfMrjbL) |

## Token Addresses by Network

### USDC

| Network | Chain ID | Address |
|---------|----------|---------|
| Base | 8453 | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Polygon | 137 | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` |
| Optimism | 10 | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` |
| Arbitrum | 42161 | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` |
| Ethereum | 1 | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` |
| Base Sepolia | 84532 | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` |
