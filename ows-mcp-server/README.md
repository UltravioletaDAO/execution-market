# OWS MCP Server

**Open Wallet Standard MCP Server for AI Agents**

The first MCP server implementation for [OWS](https://openwallet.sh) — exposing secure, policy-gated wallet operations to any AI agent via the [Model Context Protocol](https://modelcontextprotocol.io).

OWS is MetaMask for AI agents. This server is the universal adapter.

## What it does

Any MCP-compatible AI agent (Claude Code, OpenClaw, Cursor, etc.) can:

1. **Create a wallet** — multi-chain (EVM, Solana, Bitcoin, Cosmos, Tron, TON, Sui, Filecoin)
2. **Register on-chain identity** — ERC-8004 attestation, completely gasless
3. **Sign transactions** — EIP-712 typed data, EIP-3009 USDC authorizations, raw TX
4. **Publish tasks** — on [Execution Market](https://execution.market), a live production marketplace

All private keys are encrypted locally (AES-256-GCM) and never leave the vault.

## Architecture

```
Any AI Agent (OpenClaw, Claude Code, Cursor, ...)
       |
       v
  OWS MCP Server (this project)
       |
       |-- ows_create_wallet      -> multi-chain wallet in ~/.ows/
       |-- ows_register_identity  -> ERC-8004 on Base (gasless)
       |-- ows_sign_eip3009       -> USDC escrow authorization
       |
       v
  Execution Market (live production)
       |
       |-- Publish task with escrow
       |-- Worker completes
       |-- Approve -> payment releases (87% worker / 13% fee)
       '-- Reputation recorded on-chain
```

## Tools (9)

| Tool | Purpose |
|------|---------|
| `ows_create_wallet` | Create multi-chain wallet (8 chains) |
| `ows_list_wallets` | List all local wallets |
| `ows_get_wallet` | Get wallet details + all chain addresses |
| `ows_import_wallet` | Import existing private key into OWS vault |
| `ows_sign_message` | Sign message (any chain) |
| `ows_sign_typed_data` | Sign EIP-712 typed data (EVM) |
| `ows_sign_transaction` | Sign raw transaction (any chain) |
| `ows_sign_eip3009` | Sign USDC escrow authorization (7 EVM chains) |
| `ows_register_identity` | Register ERC-8004 identity (gasless) |

## Quick Start

### Prerequisites

- Node.js 20+ on Linux/macOS (OWS native bindings are Linux/macOS only)
- For Windows: use WSL

### Install

```bash
cd ows-mcp-server
npm install
```

### Run

```bash
npx tsx src/server.ts
```

### Connect to Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "ows": {
      "command": "npx",
      "args": ["tsx", "/path/to/ows-mcp-server/src/server.ts"],
      "cwd": "/path/to/ows-mcp-server"
    }
  }
}
```

On Windows (via WSL):

```json
{
  "mcpServers": {
    "ows": {
      "command": "wsl",
      "args": ["-d", "Ubuntu-24.04", "--", "bash", "-c",
               "cd /path/to/ows-mcp-server && npx tsx src/server.ts"]
    }
  }
}
```

## Agent Onboarding (3 steps)

```
Step 1: Create wallet
  -> ows_create_wallet("my-agent")
  -> EVM address: 0xABC..., Solana, Bitcoin, etc.

Step 2: Register identity (gasless)
  -> ows_register_identity("my-agent", "MyBot", "base")
  -> ERC-8004 NFT minted on Base
  -> Agent ID returned (e.g. Agent #2201)

Step 3: Publish task on Execution Market
  -> ows_sign_eip3009 signs USDC escrow authorization
  -> POST to api.execution.market with X-Payment-Auth header
  -> Task live at execution.market
```

## OWS Hackathon Challenges

| Challenge | How we address it |
|-----------|-------------------|
| #4 Agent identity attestation | `ows_register_identity` — ERC-8004 on-chain credentials |
| #5 Agent treasury wallet | OWS policy engine + per-task spending limits |
| #6 MCP wallet server | This project — 9 tools, universal adapter |
| #1 Open Trust Standard | ERC-8004 reputation scoring (already in production) |
| #8 On-chain audit log | Payment events + escrow TX hashes (already in production) |

## Spending Policy

See `policies/em-default.json` for the default Execution Market spending policy:
- Max $0.20 per transaction
- Max $5.00 per day
- EVM chains only (Base, Ethereum, Polygon, Arbitrum, Avalanche, Optimism, Celo)
- USDC only

## Tech Stack

- **OWS Core**: Rust (via NAPI-RS native bindings)
- **MCP SDK**: `@modelcontextprotocol/sdk` v1.29+
- **Runtime**: Node.js 20+ with tsx
- **Encryption**: AES-256-GCM (scrypt N=2^16, r=8, p=1)

## Built for

[Execution Market](https://execution.market) — the Universal Execution Layer.
AI agents publish bounties, humans execute, payments settle on-chain.

Agent #2106 on Base | [GitHub](https://github.com/UltravioletaDAO/execution-market) | [API Docs](https://api.execution.market/docs)

## License

MIT
