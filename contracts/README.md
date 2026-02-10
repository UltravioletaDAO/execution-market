# Execution Market — Contracts

## Payment System: x402 Facilitator (Production)

Execution Market uses the **x402 Facilitator** for all payment operations. This is a gasless, EIP-3009 based escrow system operated by Ultravioleta DAO.

- **SDK**: `uvd-x402-sdk` ([Python](https://pypi.org/project/uvd-x402-sdk/) / [TypeScript](https://www.npmjs.com/package/uvd-x402-sdk))
- **Facilitator**: `https://facilitator.ultravioletadao.xyz`
- **Networks**: Base, Ethereum, Polygon, Arbitrum, Celo, Monad, Avalanche (+ testnets)
- **Tokens**: USDC, EURC, USDT, PYUSD, AUSD

See `mcp_server/integrations/x402/sdk_client.py` for the full network/token registry.

## ERC-8004 Identity

| Property | Value |
|----------|-------|
| Agent ID (Base) | **2106** |
| Identity Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` (all mainnets) |
| Reputation Registry | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` (all mainnets) |

Registration is gasless via the Facilitator's `/register` endpoint.

## ChambaEscrow — DEPRECATED

> **ChambaEscrow.sol has been archived to `_archive/contracts/`.** It was a custom Solidity escrow contract used during early development. It has been fully replaced by the x402 Facilitator (gasless, EIP-3009 based).
>
> **Do not deploy, reference, or interact with ChambaEscrow.** All escrow operations go through `uvd-x402-sdk` + Facilitator.

Historical deployments (read-only, no funds at risk):
- Ethereum: `0x6c320efaC433690899725B3a7C84635430Acf722` (v1.0, pre-audit)
- Avalanche: `0xedA98AF95B76293a17399Af41A499C193A8DB51A` (v2, verified)

## Directory Structure

```
contracts/
├── contracts/          # Active Solidity sources (ERC-8004 only)
├── deployments/        # Active deployment records
│   └── erc8004-mainnet.json
├── scripts/            # Deployment scripts
├── MONAD-TESTNET.md    # Monad testnet deployment guide
└── README.md           # This file

_archive/contracts/     # Deprecated ChambaEscrow files
├── ChambaEscrow.sol
├── IChambaEscrow.sol
├── ChambaEscrow.test.ts
├── DEPLOYMENT_LOG.md
└── deployments/        # Historical deployment records
```

## Quick Start

```bash
npm install
npm run compile
npm test
```

## License

MIT
