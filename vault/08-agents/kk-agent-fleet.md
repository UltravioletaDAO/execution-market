---
date: 2026-02-26
tags:
  - domain/agents
  - project/karma-kadabra
  - blockchain/erc-8004
status: active
aliases:
  - KK Fleet
  - Agent Fleet
related-files:
  - scripts/kk/generate-wallets.ts
  - mcp_server/integrations/erc8004/facilitator_client.py
---

# KK Agent Fleet

All 24 Karma Kadabra V2 agents with ERC-8004 identity NFTs on Base. Verified on-chain 2026-02-22.

## Agent NFT IDs (Base Mainnet)

| Range | Count | Type |
|-------|-------|------|
| 18775 - 18779 | 5 | System |
| 18814 - 18818 | 5 | Community |
| 18843 - 18844 | 2 | Community |
| 18849 - 18850 | 2 | Community |
| 18894 - 18898 | 5 | Community |
| 18904 - 18907 | 4 | Community |
| 18934 | 1 | System |

**Total: 24 agents, 24 NFTs**

## Funding Status

All 24 agents funded across all 8 chains:

- Base, Ethereum, Polygon, Arbitrum
- Avalanche, Monad, Celo, Optimism

Each wallet holds:
- USDC for task bounties and payments
- Native token (ETH/MATIC/AVAX/etc.) for gas on chains without gasless support

## Registration

Registration is gasless via the [[facilitator]] (`POST /register`). The Facilitator pays gas on behalf of agents. Identity registry address is deterministic (CREATE2) across all networks: `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`.

## Verification

```bash
# Check NFT ownership on Base
cast call 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432 \
  "ownerOf(uint256)" 18775 --rpc-url $BASE_RPC_URL
```

## Related

- [[karma-kadabra-v2]] -- Swarm overview and integration status
- [[erc-8004]] -- Identity registry protocol
- [[fund-distribution]] -- How agents get funded
- [[hd-wallet-management]] -- Wallet derivation from mnemonic
