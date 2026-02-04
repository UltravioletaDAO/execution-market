# Rename: Chamba → Execution Market

## Status: COMPLETED (2026-02-04)

Full rebrand from "Chamba" to "Execution Market" with domain migration from `*.chamba.ultravioletadao.xyz` to `execution.market`.

## Naming Convention Applied

| Context | Old | New |
|---------|-----|-----|
| Brand name | Chamba | Execution Market |
| MCP tool prefix | `chamba_*` | `em_*` |
| Package names | `chamba-*` / `@chamba/*` | `execution-market-*` / `@execution-market/*` |
| Docker compose services | `chamba-*` | `execution-market-*` |
| CSS theme color | `chamba` | `em` |
| Env vars | `CHAMBA_*` | `EM_*` (with `CHAMBA_*` fallback) |
| localStorage keys | `chamba-*` | `em-*` |
| API key prefixes | `chamba_<tier>_*` | `em_<tier>_*` (legacy accepted) |
| SDK classes | `ChambaClient` | `ExecutionMarketClient` |
| CLI module | `chamba_cli` | `em_cli` |
| HTTP headers | `X-Chamba-*` | `X-EM-*` |
| Prometheus metrics | `chamba_*` | `em_*` |
| Domain (dashboard) | `app.chamba.ultravioletadao.xyz` | `execution.market` |
| Domain (MCP API) | `mcp.chamba.ultravioletadao.xyz` | `mcp.execution.market` |
| Domain (API) | `api.chamba.ultravioletadao.xyz` | `api.execution.market` |

## What Was Renamed

### Dashboard
- All user-facing UI text and branding
- i18n translations (en, es, pt) — values updated, keys like `whatIsChamba` kept as internal identifiers
- Tailwind CSS theme color `chamba` → `em` (all component classes)
- localStorage/sessionStorage keys
- `package.json` name
- PWA manifest, service worker cache names
- Client info headers (`x-client-info`, `X-Client-Info`)
- CSV/report filenames
- WalletConnect metadata
- Comment headers (`// Chamba:` → `// Execution Market:`)

### MCP Server
- All 24 MCP tool names (`chamba_*` → `em_*`)
- FastAPI app title and description
- Server name in FastMCP config
- API key validation (accepts both `em_*` and legacy `chamba_*`)
- Rate limit middleware (supports both prefixes)
- Prometheus metric prefixes
- Health check service name
- Agent card metadata
- `pyproject.toml` package name

### SDK & CLI
- TypeScript SDK: `@execution-market/sdk`, `ExecutionMarket` class
- Python SDK: `em.py` module, `ExecutionMarketClient` class
- CLI: `em_cli` package directory, `em` entry point
- All backward-compat aliases maintained (`ChambaAPIClient = EMAPIClient`)

### Infrastructure
- Docker compose service/network/volume names
- Dockerfile comments
- `.env.example` and `.env.docker.example` headers and var names
- GitHub Actions workflow references (where not tied to AWS resource names)
- Terraform variable names and descriptions (where not tied to AWS resource names)

### Documentation
- All `docs/*.md` files
- All `docs-site/` source files (EN + ES)
- All `docs/planning/` and `docs/articles/` files
- Root `README.md`, `CLAUDE.md`, `SPEC.md`, `PLAN.md`
- MCP server docs (`mcp_server/docs/`)
- Contract docs (brand references only, not contract names)

### DNS & SSL
- ACM certificate: `arn:aws:acm:us-east-2:518898403364:certificate/533c7547-d225-4289-9c85-dd2d4db2e6f7`
- Route53 hosted zone: `Z050891416D4N69E74FEN`
- A records: `execution.market`, `mcp.execution.market`, `api.execution.market` → ALB
- Certificate added to ALB HTTPS listener

## Intentionally Kept As-Is

These items still contain "chamba" references and are **not bugs**:

### Smart Contract Names
- `ChambaEscrow` — deployed on-chain, immutable
- `IChambaEscrow` — Solidity interface
- `ChambaReputation` — contract in `docs/SYNERGIES.md`
- Files: `contracts/` directory, `docs-site/docs/contracts/chamba-escrow.md`

### Supabase Storage Bucket
- `chamba-evidence` — renaming requires data migration and policy updates
- Referenced in: `mcp_server/api/health.py`, `mcp_server/health/checks.py`, `docs/INITIAL_MILESTONE.md`

### AWS Infrastructure Names (renaming requires service recreation)
- ECS cluster: `chamba-production-cluster`, `chamba-staging`, `chamba-cluster`
- ECS services: `chamba-production-dashboard`, `chamba-production-mcp-server`
- ECS containers: `chamba-backend`, `chamba-frontend`
- ECR repos: `chamba-dashboard`, `chamba-mcp-server`
- Referenced in: `.github/workflows/deploy*.yml`, `infrastructure/terraform/*.tf`, `infrastructure/task-def-mcp.json`

### AWS Secrets Manager Paths
- `chamba/supabase`, `chamba/contracts`, `chamba/commission`
- Renaming requires re-creating secrets and updating all ECS task definitions
- Referenced in: `infrastructure/task-def-mcp.json`, `mcp_server/.env` comments

### Backward-Compatibility Env Var Fallbacks
All `EM_*` vars accept `CHAMBA_*` as fallback for migration period:
- `EM_TREASURY_ADDRESS` / `CHAMBA_TREASURY_ADDRESS`
- `EM_ADMIN_KEY` / `CHAMBA_ADMIN_KEY`
- `EM_AGENT_ID` / `CHAMBA_AGENT_ID`
- `EM_PLATFORM_FEE` / `CHAMBA_PLATFORM_FEE`
- `EM_PLATFORM_FEE_BPS` / `CHAMBA_PLATFORM_FEE_BPS`
- `EM_PROTECTION_FUND_ADDRESS` / `CHAMBA_PROTECTION_FUND_ADDRESS`
- `EM_API_KEY` / `CHAMBA_API_KEY`
- `EM_API_URL` / `CHAMBA_API_URL`
- `EM_EXECUTOR_ID` / `CHAMBA_EXECUTOR_ID`
- `EM_ESCROW_ADDRESS` / `CHAMBA_ESCROW_ADDRESS`

### Legacy API Key Prefix Support
- `chamba_free_*`, `chamba_starter_*`, `chamba_growth_*`, `chamba_enterprise_*`
- `sk_chamba_*`
- Accepted alongside new `em_*` prefixes in `mcp_server/api/auth.py` and `mcp_server/api/middleware.py`

### CLI Backward-Compat Alias
- `ChambaAPIClient = EMAPIClient` in `cli/src/em_cli/api.py`

### i18n Key Names (Internal, Not User-Facing)
- `whatIsChamba` key in `dashboard/src/i18n/locales/*.json`
- Used in `t()` calls but display text shows "Execution Market"

### Spanish Cultural Tagline
- "Hay una chamba, alguien la hace, alguien paga" in `docs/COMPARISON.md`, `docs/PITCH.md`
- Cultural context, not brand reference

### Filesystem Path
- `/mnt/z/ultravioleta/dao/chamba/` — local directory name, not deployed
- Referenced in `CLAUDE.md` MCP config example

## Future Cleanup (Optional)

These can be done when convenient but are not blocking:

1. **Rename Supabase bucket** `chamba-evidence` → `em-evidence` (requires data migration)
2. **Rename AWS Secrets Manager paths** `chamba/*` → `em/*` (requires secret re-creation)
3. **Rename ECR repos** (just create new repos and re-tag images)
4. **Rename ECS clusters/services** (requires service recreation via Terraform)
5. **Remove legacy `CHAMBA_*` env var fallbacks** after all deployments use `EM_*`
6. **Remove legacy `chamba_*` API key prefix support** after all clients migrate
7. **Rename GitHub repo** from `chamba` to `execution-market`
