# Multi-Chain x402 Payment Test Results

**Test Date:** 2026-02-10T02:19:34.506Z
**Wallet:** 0xD3868E1eD738CED6945A574a7c769433BeD5d474
**Test Count:** 5 Fibonacci tasks per network
**Networks Tested:** base, polygon, optimism, arbitrum

## Summary

| Network | Tasks | Verified | Errors | Total Bounty | Balance Change |
|---------|-------|----------|--------|--------------|-----------------|
| Base | 5 | 5/5 | 0 | $0.19 | $0.000000 |
| Polygon | 5 | 5/5 | 0 | $0.19 | $0.000000 |
| Optimism | 5 | 5/5 | 0 | $0.19 | $0.000000 |
| Arbitrum | 5 | 5/5 | 0 | $0.19 | $0.000000 |

## Detailed Results

### Base (Chain ID: 8453)

**USDC Address:** `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
**Treasury:** `0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad`

| Fib # | Bounty | Total w/Fee | Task ID | Facilitator | Error |
|-------|--------|-------------|---------|-------------|-------|
| 1 | $0.01 | $0.01 | N/A | ✅ |  |
| 2 | $0.02 | $0.02 | N/A | ✅ |  |
| 3 | $0.03 | $0.03 | N/A | ✅ |  |
| 4 | $0.05 | $0.05 | N/A | ✅ |  |
| 5 | $0.08 | $0.09 | N/A | ✅ |  |

### Polygon (Chain ID: 137)

**USDC Address:** `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
**Treasury:** `0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad`

| Fib # | Bounty | Total w/Fee | Task ID | Facilitator | Error |
|-------|--------|-------------|---------|-------------|-------|
| 1 | $0.01 | $0.01 | N/A | ✅ |  |
| 2 | $0.02 | $0.02 | N/A | ✅ |  |
| 3 | $0.03 | $0.03 | N/A | ✅ |  |
| 4 | $0.05 | $0.05 | N/A | ✅ |  |
| 5 | $0.08 | $0.09 | N/A | ✅ |  |

### Optimism (Chain ID: 10)

**USDC Address:** `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85`
**Treasury:** `0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad`

| Fib # | Bounty | Total w/Fee | Task ID | Facilitator | Error |
|-------|--------|-------------|---------|-------------|-------|
| 1 | $0.01 | $0.01 | N/A | ✅ |  |
| 2 | $0.02 | $0.02 | N/A | ✅ |  |
| 3 | $0.03 | $0.03 | N/A | ✅ |  |
| 4 | $0.05 | $0.05 | N/A | ✅ |  |
| 5 | $0.08 | $0.09 | N/A | ✅ |  |

### Arbitrum (Chain ID: 42161)

**USDC Address:** `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
**Treasury:** `0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad`

| Fib # | Bounty | Total w/Fee | Task ID | Facilitator | Error |
|-------|--------|-------------|---------|-------------|-------|
| 1 | $0.01 | $0.01 | N/A | ✅ |  |
| 2 | $0.02 | $0.02 | N/A | ✅ |  |
| 3 | $0.03 | $0.03 | N/A | ✅ |  |
| 4 | $0.05 | $0.05 | N/A | ✅ |  |
| 5 | $0.08 | $0.09 | N/A | ✅ |  |

## Technical Details

### Network Configuration

```json
{
  "base": {
    "name": "Base",
    "chain": {
      "formatters": {
        "block": {
          "type": "block"
        },
        "transaction": {
          "type": "transaction"
        },
        "transactionReceipt": {
          "type": "transactionReceipt"
        }
      },
      "serializers": {},
      "blockTime": 2000,
      "contracts": {
        "gasPriceOracle": {
          "address": "0x420000000000000000000000000000000000000F"
        },
        "l1Block": {
          "address": "0x4200000000000000000000000000000000000015"
        },
        "l2CrossDomainMessenger": {
          "address": "0x4200000000000000000000000000000000000007"
        },
        "l2Erc721Bridge": {
          "address": "0x4200000000000000000000000000000000000014"
        },
        "l2StandardBridge": {
          "address": "0x4200000000000000000000000000000000000010"
        },
        "l2ToL1MessagePasser": {
          "address": "0x4200000000000000000000000000000000000016"
        },
        "disputeGameFactory": {
          "1": {
            "address": "0x43edB88C4B80fDD2AdFF2412A7BebF9dF42cB40e"
          }
        },
        "l2OutputOracle": {
          "1": {
            "address": "0x56315b90c40730925ec5485cf004d835058518A0"
          }
        },
        "multicall3": {
          "address": "0xca11bde05977b3631167028862be2a173976ca11",
          "blockCreated": 5022
        },
        "portal": {
          "1": {
            "address": "0x49048044D57e1C92A77f79988d21Fa8fAF74E97e",
            "blockCreated": 17482143
          }
        },
        "l1StandardBridge": {
          "1": {
            "address": "0x3154Cf16ccdb4C6d922629664174b904d80F2C35",
            "blockCreated": 17482143
          }
        }
      },
      "id": 8453,
      "name": "Base",
      "nativeCurrency": {
        "name": "Ether",
        "symbol": "ETH",
        "decimals": 18
      },
      "rpcUrls": {
        "default": {
          "http": [
            "https://mainnet.base.org"
          ]
        }
      },
      "blockExplorers": {
        "default": {
          "name": "Basescan",
          "url": "https://basescan.org",
          "apiUrl": "https://api.basescan.org/api"
        }
      },
      "sourceId": 1
    },
    "chainId": 8453,
    "usdcAddress": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "facilitatorSupported": true,
    "emTreasury": "0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad"
  },
  "polygon": {
    "name": "Polygon",
    "chain": {
      "id": 137,
      "name": "Polygon",
      "blockTime": 2000,
      "nativeCurrency": {
        "name": "POL",
        "symbol": "POL",
        "decimals": 18
      },
      "rpcUrls": {
        "default": {
          "http": [
            "https://polygon-rpc.com"
          ]
        }
      },
      "blockExplorers": {
        "default": {
          "name": "PolygonScan",
          "url": "https://polygonscan.com",
          "apiUrl": "https://api.etherscan.io/v2/api"
        }
      },
      "contracts": {
        "multicall3": {
          "address": "0xca11bde05977b3631167028862be2a173976ca11",
          "blockCreated": 25770160
        }
      }
    },
    "chainId": 137,
    "usdcAddress": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    "facilitatorSupported": true,
    "emTreasury": "0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad"
  },
  "optimism": {
    "name": "Optimism",
    "chain": {
      "formatters": {
        "block": {
          "type": "block"
        },
        "transaction": {
          "type": "transaction"
        },
        "transactionReceipt": {
          "type": "transactionReceipt"
        }
      },
      "serializers": {},
      "blockTime": 2000,
      "contracts": {
        "gasPriceOracle": {
          "address": "0x420000000000000000000000000000000000000F"
        },
        "l1Block": {
          "address": "0x4200000000000000000000000000000000000015"
        },
        "l2CrossDomainMessenger": {
          "address": "0x4200000000000000000000000000000000000007"
        },
        "l2Erc721Bridge": {
          "address": "0x4200000000000000000000000000000000000014"
        },
        "l2StandardBridge": {
          "address": "0x4200000000000000000000000000000000000010"
        },
        "l2ToL1MessagePasser": {
          "address": "0x4200000000000000000000000000000000000016"
        },
        "disputeGameFactory": {
          "1": {
            "address": "0xe5965Ab5962eDc7477C8520243A95517CD252fA9"
          }
        },
        "l2OutputOracle": {
          "1": {
            "address": "0xdfe97868233d1aa22e815a266982f2cf17685a27"
          }
        },
        "multicall3": {
          "address": "0xca11bde05977b3631167028862be2a173976ca11",
          "blockCreated": 4286263
        },
        "portal": {
          "1": {
            "address": "0xbEb5Fc579115071764c7423A4f12eDde41f106Ed"
          }
        },
        "l1StandardBridge": {
          "1": {
            "address": "0x99C9fc46f92E8a1c0deC1b1747d010903E884bE1"
          }
        }
      },
      "id": 10,
      "name": "OP Mainnet",
      "nativeCurrency": {
        "name": "Ether",
        "symbol": "ETH",
        "decimals": 18
      },
      "rpcUrls": {
        "default": {
          "http": [
            "https://mainnet.optimism.io"
          ]
        }
      },
      "blockExplorers": {
        "default": {
          "name": "Optimism Explorer",
          "url": "https://optimistic.etherscan.io",
          "apiUrl": "https://api-optimistic.etherscan.io/api"
        }
      },
      "sourceId": 1
    },
    "chainId": 10,
    "usdcAddress": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
    "facilitatorSupported": true,
    "emTreasury": "0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad"
  },
  "arbitrum": {
    "name": "Arbitrum",
    "chain": {
      "id": 42161,
      "name": "Arbitrum One",
      "nativeCurrency": {
        "name": "Ether",
        "symbol": "ETH",
        "decimals": 18
      },
      "blockTime": 250,
      "rpcUrls": {
        "default": {
          "http": [
            "https://arb1.arbitrum.io/rpc"
          ]
        }
      },
      "blockExplorers": {
        "default": {
          "name": "Arbiscan",
          "url": "https://arbiscan.io",
          "apiUrl": "https://api.arbiscan.io/api"
        }
      },
      "contracts": {
        "multicall3": {
          "address": "0xca11bde05977b3631167028862be2a173976ca11",
          "blockCreated": 7654707
        }
      }
    },
    "chainId": 42161,
    "usdcAddress": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
    "facilitatorSupported": true,
    "emTreasury": "0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad"
  }
}
```

### Test Configuration

- **Fibonacci bounties:** $0.01, $0.02, $0.03, $0.05, $0.08
- **Platform fee:** 8%
- **Tasks per network:** 5
- **Dry run mode:** Yes

### Key Findings

- **Total tests:** 20
- **Facilitator verifications:** 20/20 (100.0%)
- **Errors encountered:** 0/20 (0.0%)

### Important Notes

1. **No funds actually moved** - EIP-3009 authorizations are signed but not executed until worker completion and agent approval
2. **Base is the primary network** - Other networks may have limited MCP API support
3. **Facilitator verification** tests the payment authorization without settling
4. **This was a dry run** - No tasks were actually created
