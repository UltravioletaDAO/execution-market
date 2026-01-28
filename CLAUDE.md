# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chamba is a **Human Execution Layer for AI Agents** - a marketplace where AI agents publish bounties for physical tasks that humans execute, with instant payment via x402. Registered as **Agent #469** on Sepolia ERC-8004 Identity Registry.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend MCP Server | Python 3.10+ + FastMCP + Pydantic v2 |
| Database | Supabase (PostgreSQL) |
| Dashboard | React 18 + TypeScript + Vite + Tailwind CSS |
| Blockchain Scripts | TypeScript + viem |
| Payments | x402r Escrow (Base Mainnet) |
| Evidence Storage | Supabase Storage + IPFS (Pinata) |
| Agent Identity | ERC-8004 Registry (Sepolia) |

## Project Structure

```
chamba/
├── mcp_server/          # MCP Server for AI agents
│   ├── server.py        # FastMCP server with 6 tools
│   ├── models.py        # Pydantic validation models
│   └── supabase_client.py
├── dashboard/           # React web portal for human workers
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Route pages
│   │   ├── hooks/       # Custom React hooks
│   │   ├── services/    # API services
│   │   └── types/       # TypeScript types
│   └── e2e/             # Playwright E2E tests
├── scripts/             # Blockchain registration scripts
│   ├── register_erc8004.ts  # ERC-8004 agent registration
│   └── upload_metadata.ts   # IPFS metadata upload
└── agent-card.json      # Agent metadata for ERC-8004
```

## Common Commands

### Dashboard Development

```bash
cd dashboard
npm install
npm run dev          # Start dev server (http://localhost:5173)
npm run build        # Production build
npm run test         # Run Vitest unit tests
npm run e2e          # Run Playwright E2E tests
npm run lint         # ESLint
```

### MCP Server

```bash
cd mcp_server
pip install -e .                    # Install in dev mode
python server.py                    # Run server directly
```

Configure Claude Code (`~/.claude/settings.local.json`):
```json
{
  "mcpServers": {
    "chamba": {
      "type": "stdio",
      "command": "python",
      "args": ["Z:/ultravioleta/dao/chamba/mcp_server/server.py"],
      "env": {
        "SUPABASE_URL": "https://YOUR_PROJECT_REF.supabase.co",
        "SUPABASE_SERVICE_KEY": "your-service-key"
      }
    }
  }
}
```

### Blockchain Scripts

```bash
cd scripts
npm install
npm run register:erc8004     # Register agent (already done - Agent #469)
npm run upload:metadata      # Update IPFS metadata
npm run register:x402r       # Register as x402r merchant (pending)
```

## Architecture

### Data Flow

```
AI Agent → MCP Server → Supabase → Dashboard → Human Worker
                ↓
           x402r Escrow (Base Mainnet)
                ↓
           Payment Release
```

### MCP Tools (for AI agents)

- `chamba_publish_task` - Publish a new task for human execution
- `chamba_get_tasks` - Get tasks with filters (agent, status, category)
- `chamba_get_task` - Get details of a specific task
- `chamba_check_submission` - Check submission status
- `chamba_approve_submission` - Approve or reject a submission
- `chamba_cancel_task` - Cancel a published task

### Task Categories

| Category | Example Tasks |
|----------|---------------|
| `physical_presence` | Verify if store is open, take photos of location |
| `knowledge_access` | Scan book pages, photograph documents |
| `human_authority` | Notarize documents, certified translations |
| `simple_action` | Buy specific item, deliver package |
| `digital_physical` | Print and deliver, configure IoT device |

### Task Lifecycle

```
PUBLISHED → ACCEPTED → IN_PROGRESS → SUBMITTED → VERIFYING → COMPLETED
                                          ↓
                                      DISPUTED
```

## Database Schema

Main tables in Supabase:
- `tasks` - Published bounties with evidence requirements
- `executors` - Human workers with wallet, reputation, location
- `submissions` - Evidence uploads with verification status
- `disputes` - Contested submissions with arbitration
- `reputation_log` - Audit trail for reputation changes

## Environment Variables

Required in `.env.local` (project root):
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `WALLET_PRIVATE_KEY` - For blockchain transactions
- `SEPOLIA_RPC_URL` - Ethereum Sepolia RPC
- `PINATA_JWT_SECRET_ACCESS_TOKEN` - For IPFS uploads

Dashboard uses `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.

## On-Chain Contracts

| Contract | Network | Address |
|----------|---------|---------|
| ERC-8004 Identity Registry | Sepolia | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| x402r Escrow | Base Mainnet | `0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC` |
| Chamba Agent ID | Sepolia | `469` |

## Key Documentation

- `SPEC.md` - Product specification with task categories and edge cases
- `PLAN.md` - Technical architecture and implementation details
- `SYNERGIES.md` - Integration points with ecosystem projects
- `agent-card.json` - ERC-8004 agent metadata (editable)
