# Local Development

Run the complete Execution Market stack locally with Docker Compose.

## Prerequisites

- Docker + Docker Compose
- Node.js 18+ (for dashboard)
- Python 3.10+ (for backend)
- A Supabase project (free tier works)

## Setup

```bash
git clone https://github.com/UltravioletaDAO/execution-market.git
cd execution-market
cp .env.example .env.local
```

Edit `.env.local`:

```bash
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhb...
SUPABASE_SERVICE_ROLE_KEY=eyJhb...  # For migrations

# Wallet (for blockchain operations)
WALLET_PRIVATE_KEY=0xYourPrivateKey  # Dev wallet ONLY, never production key

# Optional
X402_NETWORK=base
EM_PAYMENT_MODE=fase1
```

## Run with Docker Compose

```bash
# Start all services
docker compose -f docker-compose.dev.yml up -d

# View logs
docker compose -f docker-compose.dev.yml logs -f

# Stop
docker compose -f docker-compose.dev.yml down
```

| Service | URL |
|---------|-----|
| Web Dashboard | http://localhost:5173 |
| MCP + REST API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| MCP Transport | http://localhost:8000/mcp/ |

## Backend Only

```bash
cd mcp_server
pip install -e .
cp ../.env.local .env.local

# Run server
python server.py
# OR with uvicorn directly
uvicorn main:app --reload --port 8000
```

## Dashboard Only

```bash
cd dashboard
npm install
npm run dev
# http://localhost:5173
```

The dashboard connects to the production API by default in dev mode. To use a local backend, set `VITE_API_URL=http://localhost:8000` in `dashboard/.env.local`.

## Mobile App

```bash
cd em-mobile
npm install
npx expo start
# Scan QR with Expo Go, or press 'a'/'i' for emulators
```

## Database Migrations

Run all migrations against your Supabase project:

```bash
cd supabase
# Via Supabase CLI
supabase db push

# Or manually via Supabase SQL editor
# Apply migrations in order: 001_initial_schema.sql → 071_reports_and_blocked_users.sql
```

## Blockchain Scripts

```bash
cd scripts
npm install

# Check balances
npx tsx check-deposit-state.ts

# Register agent on ERC-8004
npm run register:erc8004

# Task factory (create test tasks)
npx tsx task-factory.ts --preset screenshot --bounty 0.10 --deadline 10
```

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | Required |
| `SUPABASE_ANON_KEY` | Supabase anon key | Required |
| `WALLET_PRIVATE_KEY` | Dev wallet private key | Required for payments |
| `X402_NETWORK` | Default payment network | `base` |
| `EM_PAYMENT_MODE` | Payment mode | `fase1` |
| `EM_ENABLED_NETWORKS` | Active networks | `base,...` |
| `EM_PLATFORM_FEE` | Platform fee % | `0.13` (13%) |
| `ANTHROPIC_API_KEY` | For AI verification | Optional |
| `PINATA_JWT_SECRET_ACCESS_TOKEN` | IPFS uploads | Optional |
| `SOLANA_RPC_URL` | Solana RPC | Public mainnet-beta |

See `.env.example` for the complete list with descriptions.

## Makefile Commands

```bash
make dev-start     # Start Docker stack
make dev-logs      # View logs
make dev-stop      # Stop Docker stack
make test          # All tests
make test-quick    # Unit tests only
make lint          # Run all linters
make build         # Build Docker images
```
