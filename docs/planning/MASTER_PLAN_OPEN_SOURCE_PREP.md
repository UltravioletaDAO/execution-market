# MASTER PLAN: Open Source Preparation

> **Created**: 2026-02-18
> **Status**: READY FOR EXECUTION
> **Total Tasks**: 39 tasks across 5 phases
> **Estimated**: ~3 sessions to complete
> **Audit Source**: Secret audit + repo hygiene audit (2026-02-18)

---

## Phase 1: Secret Scrubbing (P0 — BLOCKING)

**MUST complete before going public. Any leaked secret = game over.**

### Task 1.1 — Untrack `dashboard/.env.production`
- **File**: `dashboard/.env.production` (currently tracked in HEAD)
- **Bug**: SEC-CRIT-01 — Production env file with Supabase anon key + Dynamic.xyz environment ID is tracked in git
- **Fix**: `git rm --cached dashboard/.env.production` + add to `.gitignore`
- **Validation**: `git ls-files dashboard/.env.production` returns empty

### Task 1.2 — Add comprehensive `.gitignore` entries for env files
- **File**: `.gitignore`
- **Bug**: SEC-CRIT-02 — Missing entries for `dashboard/.env.production`, `.env.cloud`, `mcp_server/.env`
- **Fix**: Add these entries to `.gitignore`:
  ```
  .env
  .env.local
  .env.cloud
  .env.production.local
  mcp_server/.env
  contracts/.env
  dashboard/.env.local
  dashboard/.env.production
  dashboard/.env.production.local
  ```
- **Validation**: `grep -c "\.env" .gitignore` returns 10+; no `.env*` files shown by `git ls-files | grep '\.env'` except `.example` files

### Task 1.3 — Remove `docs/internal/` from tracking (11 private files)
- **File**: `docs/internal/` (11 tracked files: pitches, DMs, internal questions)
- **Bug**: SEC-CRIT-03 — Private business pitches, DM drafts, and partner questions are tracked:
  - `PITCH-RENTAHUMAN-ALEX.md`, `PITCH-RENTAHUMAN-ALEX-ES.md`
  - `PITCH-RENTAHUMAN-DM-LARGO-EN.md`, `PITCH-RENTAHUMAN-DM-LARGO-ES.md`
  - `PITCH-STREAM-ESPANOL.md`
  - `MESSAGE_FOR_MARCO.md`
  - `QUESTIONS_FOR_ALI_FASE3.md`, `QUESTIONS_FOR_ALI_FOLLOWUP.md`
  - `OPENCLAW_TASK_BRAINSTORM.md`
  - `facilitator-gasless-handoff.md`, `facilitator-reputation-bug-report.md`
- **Fix**: `git rm -r --cached docs/internal/` + add `docs/internal/` to `.gitignore`
- **Validation**: `git ls-files docs/internal/` returns empty

### Task 1.4 — Scrub secrets from git history with `git-filter-repo`
- **File**: Entire git history
- **Bug**: SEC-CRIT-04 — These files contain secrets/private info in git history even after deletion:
  - `.env.cloud` — Supabase anon key JWT tokens
  - `dashboard/.env.production` — Supabase keys + Dynamic.xyz ID
  - `docs/internal/*` — Private business correspondence
- **Fix**:
  ```bash
  pip install git-filter-repo
  git filter-repo --invert-paths \
    --path .env.cloud \
    --path dashboard/.env.production \
    --path docs/internal/
  ```
  **WARNING**: Rewrites ALL git history. Force push required. All collaborators must re-clone.
- **Validation**: `git log --all --diff-filter=A --name-only --format="" | grep -E "\.env\.cloud|docs/internal/"` returns empty

### Task 1.5 — Redact `CLAUDE.md` for public release
- **File**: `CLAUDE.md` (651 lines)
- **Bug**: SEC-CRIT-05 — Contains internal infrastructure details:
  - AWS account ID `518898403364` + username `cuchorapido`
  - Supabase project ID `puyhpytmtkyevnxffksl`
  - Supabase management token prefix `sbp_c5dd...`
  - Dev wallet address `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd`
  - Platform wallet `0xD386...`, Treasury `0xae07...`
  - AWS Secrets Manager paths (`em/x402:X402_RPC_URL`)
  - Full ECR push commands with account ID
  - QuikNode RPC reference
- **Fix**: Create public-safe version of CLAUDE.md:
  - Replace AWS account ID with `YOUR_AWS_ACCOUNT_ID`
  - Replace Supabase project ID with `your-project.supabase.co`
  - Remove `sbp_c5dd...` reference entirely
  - Keep wallet addresses that are public on-chain (contract addresses, Agent 2106) but remove dev wallet private key references
  - Replace ECR commands with generic `YOUR_ECR_REPO` placeholder
  - Remove AWS SM paths
  - Keep all architectural documentation, payment flows, etc. (that's valuable for contributors)
- **Validation**: `grep -c "518898403364\|cuchorapido\|sbp_c5dd\|857fe615" CLAUDE.md` returns 0

### Task 1.6 — Audit `.claude/` directory for public safety
- **File**: `.claude/` directory (tracked in git)
- **Bug**: SEC-CRIT-06 — `.claude/irc-config.json` exposes IRC server address, channel, master nicknames. Skills and agents are tracked.
- **Fix**:
  - Add `.claude/.irc-nick` to `.gitignore` (DONE in earlier commit)
  - Review `.claude/irc-config.json` — remove `masters` list or replace with generic
  - Review all `.claude/skills/` — these are safe (public skill code)
  - Review `.claude/agents/` — check for internal references
- **Validation**: `git grep -l "zeroxultravioleta\|UltraClawd" .claude/` returns only config files with generic values

### Task 1.7 — Verify no AWS credentials in tracked files
- **File**: All tracked files
- **Bug**: SEC-AUDIT-01 — Need to verify no AKIA keys or aws_secret_access_key leaked
- **Fix**: Run comprehensive scan:
  ```bash
  git grep -E "AKIA[A-Z0-9]{16}" .
  git grep "aws_secret_access_key" .
  git grep -E "sk_live_|sk_test_" .
  ```
  Known safe results: `docs/planning/HANDOFF_OPEN_SOURCE_PREP.md` (grep examples, not real keys)
- **Validation**: All matches are documentation examples, not real secrets

### Task 1.8 — Clean `.env.example` hardcoded values
- **File**: `.env.example` (root, line ~35)
- **Bug**: SEC-LOW-01 — `SECRET_KEY_BASE=UpNVntn3cDx...` is a full 64-char secret baked into example
- **Fix**: Replace with `SECRET_KEY_BASE=generate-a-random-64-char-secret-here`
- **Validation**: `grep "UpNVntn3" .env.example` returns empty

### Task 1.9 — Clean scattered hardcoded Supabase anon keys from source files
- **File**: Multiple files with 3+ different Supabase anon JWTs hardcoded:
  - `.claude/scripts/deploy.sh:54` — hardcoded anon key + Dynamic.xyz env ID in build args
  - `scripts/task-factory.ts:68` — hardcoded production anon key as fallback
  - `mcp_server/supabase_client.py:16` — production URL as default fallback
- **Bug**: SEC-MED-01 — Supabase anon keys scattered as hardcoded fallbacks instead of env vars. 3 different JWTs exist (different `iat` timestamps), some may be stale.
- **Fix**: Replace all hardcoded anon keys with `os.environ["SUPABASE_ANON_KEY"]` / `process.env.SUPABASE_ANON_KEY` (no fallback). Remove stale keys. Deploy script should read from env, not hardcode.
- **Validation**: `git grep "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" -- '*.py' '*.ts' '*.sh'` returns only `.env.example` and `.env.docker.example` files

### Task 1.10 — Replace AWS infrastructure identifiers in docs/scripts
- **File**: Multiple files (40+ references)
- **Bug**: SEC-LOW-02 — AWS account ID `518898403364`, ACM certificate ARNs, API Gateway URLs hardcoded in:
  - `CLAUDE.md` (covered in Task 1.5)
  - `README.md` (Infrastructure section)
  - `infrastructure/terraform/*.tf`
  - `.claude/scripts/deploy.sh`, `scripts/deploy-docs.sh`
  - `docs/planning/HANDOFF_OPEN_SOURCE_PREP.md`
  - API Gateway URL: `vhvwpq0lu0.execute-api.us-east-2.amazonaws.com`
- **Fix**:
  - In documentation: replace with `YOUR_AWS_ACCOUNT_ID`, `YOUR_ACM_ARN`, `YOUR_API_GATEWAY_URL`
  - In Terraform: use variables (`var.aws_account_id`) instead of hardcoded values
  - In deploy scripts: read from env vars
  - Exception: `README.md` infrastructure section can be removed entirely (internal detail, not useful for contributors)
- **Validation**: `git grep "518898403364" -- ':!docs/planning/MASTER_PLAN_OPEN_SOURCE_PREP.md'` returns 0 matches (excluding this plan file)

---

## Phase 2: Core Open Source Files (P0 — Required)

**Must exist before public release. Standard open source hygiene.**

### Task 2.1 — Create `SECURITY.md`
- **File**: `SECURITY.md` (NEW — root)
- **Bug**: HYGIENE-CRIT-01 — No security disclosure policy for a project handling real USDC
- **Fix**: Create file with:
  - "Reporting a Vulnerability" section — email `security@ultravioletadao.xyz` (or GitHub private vulnerability reporting)
  - Scope: smart contracts, API server, dashboard, payment flows
  - Responsible disclosure timeline (90 days)
  - Out of scope: social engineering, DoS, third-party services
  - Known audits reference: link to `docs/reports/SECURITY_AUDIT_2026-02-18.md`
  - Bug bounty mention (even if informal)
- **Validation**: File exists, contains "Reporting" and email/contact method

### Task 2.2 — Create `CONTRIBUTING.md`
- **File**: `CONTRIBUTING.md` (NEW — root)
- **Bug**: HYGIENE-HIGH-01 — No contribution guidelines for external developers
- **Fix**: Create comprehensive file with:
  - Prerequisites (Python 3.10+, Node 18+, Docker)
  - Local dev setup (Docker Compose quick start)
  - How to run tests: `pytest` (backend, 950 tests), `npm test` (dashboard), `npm run e2e` (E2E)
  - Code style: `ruff` for Python (format + check), ESLint for TypeScript
  - PR process: conventional commits, CI must pass, link related issues
  - Branch naming: `feat/`, `fix/`, `docs/`, `refactor/`
  - Where to find issues: GitHub Issues with templates
  - Architecture overview pointer → `CLAUDE.md` and `PLAN.md`
  - "Good First Issues" label guidance
- **Validation**: File exists, contains "Getting Started", "Running Tests", "Pull Request"

### Task 2.3 — Create `CODE_OF_CONDUCT.md`
- **File**: `CODE_OF_CONDUCT.md` (NEW — root)
- **Bug**: HYGIENE-MED-01 — No code of conduct
- **Fix**: Adopt Contributor Covenant v2.1 (industry standard). Contact: `conduct@ultravioletadao.xyz` or maintainer GitHub
- **Validation**: File exists, contains "Contributor Covenant" and version 2.1

### Task 2.4 — Create `README.es.md`
- **File**: `README.es.md` (NEW — root, MISSING per audit)
- **Bug**: HYGIENE-HIGH-02 — Bilingual community requirement violated (CLAUDE.md: "README.md ↔ README.es.md SIEMPRE sincronizados")
- **Fix**: Translate current `README.md` (514 lines) to Spanish. Keep all technical terms, contract addresses, URLs identical. Translate descriptions, section headers, setup instructions.
- **Validation**: File exists, line count within 10% of README.md, contains same section headers (translated)

### Task 2.5 — Create `mcp_server/.env.example`
- **File**: `mcp_server/.env.example` (NEW — MISSING per audit)
- **Bug**: HYGIENE-HIGH-03 — Main backend has no .env.example; contributors can't set up API server
- **Fix**: Create with all required vars:
  ```bash
  # Supabase
  SUPABASE_URL=https://your-project.supabase.co
  SUPABASE_SERVICE_KEY=your-service-key
  SUPABASE_ANON_KEY=your-anon-key

  # Payment Configuration
  EM_PAYMENT_MODE=fase1          # fase1 | fase2 | preauth
  EM_ESCROW_MODE=direct_release  # platform_release | direct_release
  EM_PLATFORM_FEE=13             # Platform fee percentage
  X402_NETWORK=base              # Default payment network
  EM_ENABLED_NETWORKS=base,ethereum,polygon,arbitrum,celo,monad,avalanche,optimism

  # Wallet (for payment signing)
  WALLET_PRIVATE_KEY=your-private-key

  # Optional
  EM_SETTLEMENT_ADDRESS=          # Override settlement target
  EM_PAYMENT_OPERATOR=            # Fase 5 operator address
  EM_REPUTATION_RELAY_KEY=        # For worker→agent feedback
  EM_FEE_MODEL=credit_card        # credit_card | legacy

  # Testing
  TESTING=false
  ```
- **Validation**: File exists, contains SUPABASE_URL and EM_PAYMENT_MODE

### Task 2.6 — Update root `.env.example` with missing EM_* vars
- **File**: `.env.example` (root, ~210 lines)
- **Bug**: HYGIENE-HIGH-04 — Missing critical env vars:
  - `EM_PAYMENT_MODE` (default: `fase1`)
  - `EM_ESCROW_MODE` (default: `platform_release`)
  - `EM_PLATFORM_FEE` (default: `13`)
  - `EM_PAYMENT_OPERATOR` (for Fase 5)
  - `EM_ENABLED_NETWORKS`
  - `EM_SETTLEMENT_ADDRESS`
  - `EM_REPUTATION_RELAY_KEY`
  - `EM_FEE_MODEL`
  - Agent ID still shows `469` (line ~171) — should be `2106`
- **Fix**: Add "Payment Configuration" section with all vars + update Agent ID
- **Validation**: `grep "EM_PAYMENT_MODE" .env.example` returns match; `grep "469" .env.example` returns empty

### Task 2.7 — Update `.env.docker.example` with missing EM_* vars
- **File**: `.env.docker.example` (~137 lines)
- **Bug**: HYGIENE-HIGH-05 — Same missing vars as root .env.example
- **Fix**: Mirror the Payment Configuration section from root .env.example
- **Validation**: `grep "EM_PAYMENT_MODE" .env.docker.example` returns match

---

## Phase 3: Repository Hygiene (P1)

**Required for professional open source presence.**

### Task 3.1 — Fix `.github/CODEOWNERS`
- **File**: `.github/CODEOWNERS`
- **Bug**: HYGIENE-HIGH-06 — All paths are wrong:
  - `/backend/` → should be `/mcp_server/`
  - `/frontend/` → should be `/dashboard/`
  - `/terraform/` → should be `/infrastructure/terraform/`
- **Fix**: Rewrite with correct paths:
  ```
  * @ultravioletadao/core
  /mcp_server/ @ultravioletadao/backend
  /dashboard/ @ultravioletadao/frontend
  /infrastructure/ @ultravioletadao/devops
  /contracts/ @ultravioletadao/contracts
  /supabase/ @ultravioletadao/backend
  ```
- **Validation**: Paths match actual directory structure (`ls -d mcp_server/ dashboard/ infrastructure/`)

### Task 3.2 — Fix `.github/dependabot.yml`
- **File**: `.github/dependabot.yml`
- **Bug**: HYGIENE-HIGH-07 — Directory paths wrong (`/backend`, `/frontend`), Dependabot PRs never generated
- **Fix**: Update directories:
  - pip: `/mcp_server`
  - npm: `/dashboard`, `/scripts`, `/sdk/typescript`
  - docker: `/mcp_server`, `/dashboard`
  - github-actions: `/`
- **Validation**: All `directory` values match actual dirs in repo

### Task 3.3 — Create `.github/ISSUE_TEMPLATE/bug_report.md`
- **File**: `.github/ISSUE_TEMPLATE/bug_report.md` (NEW)
- **Bug**: HYGIENE-MED-02 — No issue templates exist
- **Fix**: Create bug report template with sections:
  - Description, Steps to Reproduce, Expected vs Actual, Environment (OS, Python version, Node version), Screenshots, Component (Backend/Dashboard/Contracts/SDK)
- **Validation**: File exists with YAML front-matter `name: Bug Report`

### Task 3.4 — Create `.github/ISSUE_TEMPLATE/feature_request.md`
- **File**: `.github/ISSUE_TEMPLATE/feature_request.md` (NEW)
- **Bug**: HYGIENE-MED-03 — No feature request template
- **Fix**: Create template with: Problem/Motivation, Proposed Solution, Alternatives Considered, Additional Context, Component affected
- **Validation**: File exists with YAML front-matter `name: Feature Request`

### Task 3.5 — Create `.github/ISSUE_TEMPLATE/config.yml`
- **File**: `.github/ISSUE_TEMPLATE/config.yml` (NEW)
- **Bug**: HYGIENE-MED-04 — No issue template chooser config
- **Fix**: Create config with `blank_issues_enabled: false` and link to SECURITY.md for vulnerability reports
- **Validation**: File exists, contains `contact_links` with security reference

### Task 3.6 — Add badges to `README.md`
- **File**: `README.md` (line 1-5)
- **Bug**: HYGIENE-LOW-01 — No CI/license/test badges
- **Fix**: Add badge row after title:
  ```markdown
  [![CI](https://github.com/UltravioletaDAO/execution-market/actions/workflows/ci.yml/badge.svg)](...)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
  [![Tests](https://img.shields.io/badge/tests-950%20passing-brightgreen)]()
  [![Agent #2106](https://img.shields.io/badge/ERC--8004-Agent%20%232106-blue)]()
  ```
- **Validation**: First 5 lines of README.md contain `shields.io` or badge URLs

### Task 3.7 — Add "Contributing" section to `README.md`
- **File**: `README.md` (add section before Links)
- **Bug**: HYGIENE-LOW-02 — No pointer to CONTRIBUTING.md
- **Fix**: Add section:
  ```markdown
  ## Contributing
  We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
  For security vulnerabilities, see [SECURITY.md](SECURITY.md).
  ```
- **Validation**: `grep "CONTRIBUTING" README.md` returns match

### Task 3.8 — Create `docs/articles/README.md`
- **File**: `docs/articles/README.md` (NEW)
- **Bug**: HYGIENE-MED-05 — 58 article versions with no context; visitors will be confused
- **Fix**: Create README explaining the evolution:
  - "This directory contains 50 versions of our manifesto, written between [dates]"
  - "Each version reflects the state of our thinking at that moment"
  - "The changelog IS the proof of authenticity"
  - Link key versions: V1 (original Spanish), V12 (For Rent vignette), V36 (Agent POV), V50 (final manifesto)
  - Note: research briefs (V50_RESEARCH_*.md) document the analytical process
- **Validation**: File exists, mentions "49" or "50" versions

### Task 3.9 — Add `docs/internal/` to `.gitignore` (if not done in Phase 1)
- **File**: `.gitignore`
- **Bug**: Covered in Task 1.3 but listed here as dependency check
- **Fix**: Ensure `docs/internal/` is in `.gitignore`
- **Validation**: `grep "docs/internal" .gitignore` returns match

### Task 3.10 — Update `contracts/.env.example` with deployment context
- **File**: `contracts/.env.example` (~67 lines)
- **Bug**: HYGIENE-LOW-03 — No note explaining that all major contracts are already deployed
- **Fix**: Add header comment:
  ```bash
  # NOTE: All production contracts (ERC-8004, x402r, PaymentOperator) are already
  # deployed on mainnet. This file is only needed if deploying NEW operator instances
  # or for local development with Hardhat/Foundry.
  # See CLAUDE.md "On-Chain Contracts" table for deployed addresses.
  ```
- **Validation**: First 5 lines contain "already deployed"

---

## Phase 4: README & Documentation Polish (P1)

**Make the README compelling for open source visitors.**

### Task 4.1 — Update `README.md` contract addresses table
- **File**: `README.md` (On-Chain Contracts section)
- **Bug**: DOC-HIGH-01 — Missing Fase 5 PaymentOperator (`0x271f...`), StaticFeeCalculator, and current production info. Legacy contracts not clearly labeled.
- **Fix**: Update table to match `CLAUDE.md` On-Chain Contracts table. Bold the active production contracts. Mark legacy with "(legacy, deprecated)".
- **Validation**: `grep "271f9fa7" README.md` returns match

### Task 4.2 — Add payment architecture section to `README.md`
- **File**: `README.md` (after Architecture section)
- **Bug**: DOC-HIGH-02 — Payment section is oversimplified; doesn't explain Fase 1/2/5 or credit card model
- **Fix**: Add concise payment section with:
  - Mermaid sequence diagram for task payment flow
  - Table of payment modes (fase1, fase2, Fase 5)
  - Fee model: 13% credit card, deducted on-chain
  - Note: "All payments gasless via x402 Facilitator"
- **Validation**: `grep "Payment" README.md` returns match in section header

### Task 4.3 — Update `README.md` Quick Start for open source
- **File**: `README.md` (Quick Start / Development section)
- **Bug**: DOC-MED-01 — Quick Start references Docker Compose but doesn't explain non-Docker setup. New contributors need clearer path.
- **Fix**: Add alternative setup paths:
  1. Docker Compose (full stack, recommended)
  2. Backend only: `cd mcp_server && pip install -e . && python server.py`
  3. Dashboard only: `cd dashboard && npm install && npm run dev`
  4. Link to `CONTRIBUTING.md` for full guide
- **Validation**: README contains "Quick Start" with at least 2 setup paths

### Task 4.4 — Sync `README.es.md` with updated `README.md`
- **File**: `README.es.md` (depends on Tasks 4.1-4.3)
- **Bug**: DOC-HIGH-03 — Must stay synced after README.md updates
- **Fix**: Apply all changes from Tasks 4.1-4.3 to Spanish version
- **Validation**: Section headers in README.es.md match README.md (translated)

### Task 4.5 — Add `videos/*/node_modules/` to `.gitignore`
- **File**: `.gitignore`
- **Bug**: DOC-LOW-01 — `videos/insights-2026/node_modules/` (222 MB) could accidentally be committed
- **Fix**: Add `videos/*/node_modules/` to `.gitignore`
- **Validation**: `grep "videos.*node_modules" .gitignore` returns match

### Task 4.6 — Clean deprecated config from `dashboard/.env.example`
- **File**: `dashboard/.env.example` (~92 lines)
- **Bug**: DOC-LOW-02 — Line ~53 mentions "Crossmint Email Wallets (deprecated)"
- **Fix**: Remove Crossmint section entirely. Add `VITE_E2E_MODE` (for E2E testing escape hatch).
- **Validation**: `grep -i "crossmint" dashboard/.env.example` returns empty

### Task 4.7 — Add Facilitator ownership note to `README.md`
- **File**: `README.md` (Infrastructure section)
- **Bug**: DOC-MED-02 — Open source visitors may confuse who controls the Facilitator
- **Fix**: Add note in Infrastructure or Architecture section:
  > **Note**: The x402 Facilitator (`facilitator.ultravioletadao.xyz`) is operated by Ultravioleta DAO. BackTrack/x402r provides the protocol contracts. See `docs/planning/X402R_REFERENCE.md` for architecture details.
- **Validation**: `grep "Facilitator.*Ultravioleta" README.md` returns match

---

## Phase 5: V51 Article + Go Public (P2)

**Final polish and launch sequence.**

### Task 5.1 — Write `ARTICLE_X_COMPETITION_V51_EN.md` (open source announcement)
- **File**: `docs/articles/ARTICLE_X_COMPETITION_V51_EN.md` (NEW)
- **Bug**: LAUNCH-01 — Need open source announcement article
- **Fix**: Write V51 incorporating:
  - web4.ai citations (from `V50_RESEARCH_WEB4AI.md`)
  - "Why Open Source" thesis section
  - Conway <> Execution Market positioning ("digital + physical = Web 4.0")
  - GitHub repo link
  - 1,027 tests, Golden Flow 7/7, BaseScan-verifiable
  - "49 versions of the manifesto prove authentic evolution"
- **Validation**: File exists, contains "open source" and "github.com"

### Task 5.2 — Update `landing/vision.html` with V51 content
- **File**: `landing/vision.html` (825 lines)
- **Bug**: LAUNCH-02 — Landing page has V50 content, not V51
- **Fix**: Update with V51 content, add GitHub repo link prominently
- **Validation**: `grep "github.com" landing/vision.html` returns match

### Task 5.3 — Update `agent-card.json` with public GitHub URL
- **File**: `agent-card.json` (links.github field)
- **Bug**: LAUNCH-03 — GitHub link exists but repo is currently private
- **Fix**: Verify `links.github` points to `https://github.com/UltravioletaDAO/execution-market` (may already be correct). Add `"open_source": true` field.
- **Validation**: `grep "github.com/UltravioletaDAO" agent-card.json` returns match

### Task 5.4 — Final secret scan (re-run all Phase 1 checks)
- **File**: Entire repository
- **Bug**: LAUNCH-04 — Must verify no secrets remain before public release
- **Fix**: Re-run:
  ```bash
  git grep -E "AKIA[A-Z0-9]{16}" .
  git grep "sbp_" .
  git grep "quiknode.pro" .
  git grep -E "0x[a-fA-F0-9]{64}" -- '*.py' '*.ts'  # private keys
  git log --all --diff-filter=A --name-only --format="" | grep -iE '\.env$|\.env\.'
  ```
  Verify all results are safe (example files, test keys, public addresses)
- **Validation**: Zero real secrets found

### Task 5.5 — Create pre-public checklist issue
- **File**: N/A (GitHub Issue)
- **Bug**: LAUNCH-05 — Need tracking issue for go-public
- **Fix**: Create GitHub Issue with checklist:
  - [ ] All Phase 1-4 tasks complete
  - [ ] Final secret scan passed
  - [ ] CI passing on main
  - [ ] `git-filter-repo` executed (if needed)
  - [ ] Force push completed
  - [ ] Flip visibility: GitHub Settings → Public
  - [ ] Verify GitHub Actions still work
  - [ ] Post announcement on X/Twitter
  - [ ] Invalidate CloudFront cache for manifesto
  - [ ] Update Discord/IRC with repo link
- **Validation**: Issue created with all checklist items

---

## Dependency Graph

```
Phase 1 (Secrets) ──► Phase 2 (Core Files) ──► Phase 3 (Hygiene) ──► Phase 4 (Polish) ──► Phase 5 (Launch)
                                                                            │
Task 1.4 (git-filter-repo) ─────────────────────────────────────────────────┼──► Task 5.4 (final scan)
                                                                            │
Tasks 4.1-4.3 (README updates) ──► Task 4.4 (README.es.md sync)            │
                                                                            │
Task 2.4 (README.es.md create) ──► Task 4.4 (sync)                         │
```

## Execution Notes

### Phase 1 Special Handling

**Task 1.4 (`git-filter-repo`) is DESTRUCTIVE and requires user decision:**

Option A: **Full history scrub** — Rewrites ALL commits. Cleanest result but:
- All commit SHAs change
- Force push required
- All forks/clones invalidated
- GitHub PR history may break

Option B: **Delete from HEAD only** — `git rm` files + `.gitignore`. Faster but:
- Secrets remain in git history
- Anyone with `git log -p` can find them
- Only OK if secrets are already rotated/public

**Recommendation**: Option A for `docs/internal/` (private correspondence). Option B may be acceptable for `.env.cloud` (only Supabase anon keys, which are publishable). **User must decide.**

### CLAUDE.md Strategy

CLAUDE.md is THE most valuable file for contributors — it has complete architecture docs, payment flows, wallet roles, contract addresses. Removing it entirely would hurt contributors significantly.

**Recommended approach**: Create TWO versions:
1. `CLAUDE.md` (public) — All architecture, flows, commands, but with redacted infra details
2. `CLAUDE.internal.md` (gitignored) — Full version with AWS account IDs, wallet keys, etc.

The public CLAUDE.md should keep: payment architecture, task lifecycle, contract addresses (these are on-chain/public), MCP tools, test profiles, development commands. It should remove: AWS account IDs, ECR repos, Supabase project ID, dev wallet address, management token prefix, deployment scripts with hardcoded values.

---

## Summary

| Phase | Tasks | Priority | Depends On |
|-------|-------|----------|------------|
| Phase 1: Secret Scrubbing | 10 | P0 (BLOCKING) | Nothing |
| Phase 2: Core Files | 7 | P0 (Required) | Phase 1 |
| Phase 3: Repo Hygiene | 10 | P1 | Phase 2 |
| Phase 4: Documentation | 7 | P1 | Phase 2-3 |
| Phase 5: Launch | 5 | P2 | Phase 1-4 |
| **TOTAL** | **39** | | |

---

*Plan generated by Claude Code session, 2026-02-18. Based on parallel audit of secrets, repo hygiene, README/env files.*
