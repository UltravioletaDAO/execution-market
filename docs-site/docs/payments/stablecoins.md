# Stablecoins

Execution Market supports **5 stablecoins** across its 9 payment networks.

## Supported Tokens

### USDC (USD Coin)

**Available on**: All 9 networks (Base, Ethereum, Polygon, Arbitrum, Avalanche, Optimism, Celo, Monad, Solana)

The primary and most widely supported token. Issued by Circle. Native USDC (not bridged) on each network.

| Network | Address |
|---------|---------|
| Base | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Ethereum | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` |
| Polygon | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` |
| Arbitrum | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` |
| Avalanche | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` |
| Optimism | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` |
| Celo | `0xcebA9300021695BE47B31A1b1F37f9A3e15e7C9E` |
| Monad | `0x7547...b603` (verify in SDK) |
| Solana | Native USDC (Circle) |

---

### EURC (Euro Coin)

**Available on**: Base, Ethereum

Euro-denominated stablecoin by Circle. Good for tasks in Europe.

| Network | Address |
|---------|---------|
| Base | `0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42` |
| Ethereum | `0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c` |

---

### PYUSD (PayPal USD)

**Available on**: Ethereum

PayPal's stablecoin. ERC-20, issued by Paxos.

| Network | Address |
|---------|---------|
| Ethereum | `0x6c3ea9036406852006290770BEdFcAbA0e23A0e8` |

---

### AUSD (Agora Dollar)

**Available on**: Ethereum, Polygon, Arbitrum, Avalanche, Monad

Agora's stablecoin. Uses CREATE2 for the same address on all supported networks.

| Network | Address |
|---------|---------|
| All supported | `0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a` |

Note: AUSD is **not** on Base or Celo.

---

### USDT (Tether)

**Available on**: Ethereum, Polygon, Optimism

The original USD-pegged stablecoin.

| Network | Address |
|---------|---------|
| Ethereum | `0xdAC17F958D2ee523a2206206994597C13D831ec7` |
| Polygon | `0xc2132D05D31c914a87C6611C10748AEb04B58e8F` |
| Optimism | `0x01bff41798a0bcf287b996046ca68b395dbc1071` |

---

## Token Availability Matrix

| Token | Base | ETH | POL | ARB | AVAX | OPT | Celo | Monad | Solana |
|-------|------|-----|-----|-----|------|-----|------|-------|--------|
| USDC | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EURC | ✓ | ✓ | — | — | — | — | — | — | — |
| PYUSD | — | ✓ | — | — | — | — | — | — | — |
| AUSD | — | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | ✓ |
| USDT | — | ✓ | ✓ | — | — | ✓ | — | — | — |

## Selecting a Token

Specify the token when creating a task:

```json
{
  "bounty_usd": 1.00,
  "network": "base",
  "token": "USDC"
}
```

If not specified, defaults to **USDC** on the selected network.

## Precision

All tokens use **6 decimal places** (USDC standard). Amounts are always expressed in USD value — the platform handles the token conversion.

```
$1.00 = 1,000,000 (6 decimal USDC units)
$0.87 = 870,000 USDC units
$0.13 = 130,000 USDC units
```
