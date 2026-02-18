# HANDOFF: Open Source Preparation for Execution Market

> **Purpose**: This document is a handoff for a new Claude Code session to prepare the Execution Market repository for public open source release.
> **Created**: 2026-02-18
> **Author**: Previous Claude Code session (V50 manifesto team)
> **Repo**: `https://github.com/UltravioletaDAO/execution-market.git` (currently private)

---

## Context

Execution Market is the **Universal Execution Layer** — infrastructure that lets AI agents hire humans (and eventually robots) for physical tasks, with instant gasless payment via x402 and on-chain reputation via ERC-8004.

The team has decided to go open source. The V50 manifesto article ("THE PHYSICAL WORLD HAS NO API") has been written and a dedicated webpage is deployed at `manifesto.execution.market`. The open source release is the logical next step.

### Why Open Source Now

1. **Conway/Automaton (web4.ai) went open source** — Sigil Wen's thesis: "autonomous superintelligence is inevitable, and the safest way for humanity is to build it in the open"
2. **49 versions of the manifesto article** prove authentic development evolution — impossible to fake
3. **1,027+ tests**, Golden Flow 7/7 on mainnet, BaseScan-verifiable contracts — this isn't vaporware
4. **RentAHuman was closed and opaque** — open source differentiates radically
5. **Community can contribute**: new task categories, agent integrations, workers in new regions

---

## Current State

### Repository

- **Remote**: `https://github.com/UltravioletaDAO/execution-market.git`
- **Branch**: `main`
- **Visibility**: Currently **PRIVATE** — needs to be flipped to public
- **CI/CD**: GitHub Actions auto-deploys on push to `main` (~20 min pipeline)

### Sensitive Files Found Locally (DO NOT COMMIT)

These files exist on the developer's machine but should **NEVER** be in the public repo:

| File | Contains | Risk |
|------|----------|------|
| `.env` | Various env vars | May have secrets |
| `.env.local` | `WALLET_PRIVATE_KEY`, `SUPABASE_DB_PASSWORD`, RPC URLs | **CRITICAL** — private keys |
| `mcp_server/.env` | `SUPABASE_SERVICE_KEY` | Service role key (bypasses RLS) |
| `dashboard/.env.local` | Supabase keys | Publishable keys (low risk) |
| `dashboard/.env.production` | Production config | Check for secrets |
| `dashboard/.env.production.local` | Production overrides | Check for secrets |
| `contracts/.env` | May contain private keys | **CRITICAL** |

### Files That ARE Safe (examples, no real secrets)

| File | Status |
|------|--------|
| `.env.example` | Template with placeholders — OK |
| `.env.docker.example` | Template — OK |
| `dashboard/.env.example` | Template — OK |
| `contracts/.env.example` | Template — OK |

---

## Checklist for Open Source Preparation

### Phase 1: Secret Audit (CRITICAL — Do First)

- [ ] **1.1** Verify `.gitignore` covers ALL sensitive files:
  ```
  .env
  .env.local
  .env.production.local
  mcp_server/.env
  contracts/.env
  dashboard/.env.local
  dashboard/.env.production.local
  ```
- [ ] **1.2** Check if any `.env` files were EVER committed to git history:
  ```bash
  git log --all --diff-filter=A --name-only --format="" | grep -iE '\.env$|\.env\.' | sort -u
  ```
- [ ] **1.3** Search entire git history for leaked secrets:
  ```bash
  # Search for private key patterns
  git log -p --all -S "PRIVATE_KEY" -- . | head -50
  git log -p --all -S "SUPABASE_SERVICE_KEY" -- . | head -50
  git log -p --all -S "sk_" -- . | head -50  # Stripe-style keys
  git log -p --all -S "sbp_" -- . | head -50  # Supabase tokens
  ```
- [ ] **1.4** If secrets found in history, use `git-filter-repo` to scrub:
  ```bash
  pip install git-filter-repo
  git filter-repo --invert-paths --path .env.local --path mcp_server/.env --path contracts/.env
  ```
  **WARNING**: This rewrites git history. All collaborators must re-clone.
- [ ] **1.5** Verify no AWS credentials, RPC URLs with API keys, or wallet private keys anywhere in tracked files:
  ```bash
  grep -r "AKIA" .  # AWS access keys
  grep -r "0x[a-fA-F0-9]{64}" . --include="*.py" --include="*.ts" --include="*.js"  # Private keys (64 hex chars)
  grep -r "quiknode.pro/" .  # RPC URLs with API keys
  grep -r "sbp_" .  # Supabase tokens
  ```
- [ ] **1.6** Check `.claude/` directory — contains session-specific config, IRC nick, etc. Add to `.gitignore` if not already:
  ```
  .claude/.irc-nick
  .claude/teams/
  .claude/tasks/
  ```

### Phase 2: License Selection

**Recommended: MIT License**

Reasons:
- Maximum adoption — anyone can use, modify, redistribute
- Compatible with all other open source licenses
- Standard for infrastructure/protocol projects (x402 SDK, Conway, most Web3 projects)
- Simple, well-understood, no compliance burden for contributors
- Matches the "permissionless" ethos of the project

Alternative considered:
- **Apache 2.0** — adds patent protection but more complex. Consider if patent trolling is a concern.
- **AGPL** — too restrictive for infrastructure that agents need to integrate with freely
- **BSL (Business Source License)** — NOT recommended. Contradicts the "open source" narrative.

**Action items:**
- [ ] **2.1** Create `LICENSE` file in root with MIT License text
- [ ] **2.2** Add license header reference to `README.md`
- [ ] **2.3** Consider adding `SPDX-License-Identifier: MIT` to key source files

### Phase 3: Repository Hygiene

- [ ] **3.1** Create/update `CONTRIBUTING.md`:
  - How to set up local dev environment
  - How to run tests (`pytest` for backend, `npm test` for dashboard)
  - PR process (conventional commits, CI must pass)
  - Code style (ruff for Python, ESLint for TypeScript)
  - Where to find issues / how to report bugs

- [ ] **3.2** Create `CODE_OF_CONDUCT.md` (use Contributor Covenant v2.1 — industry standard)

- [ ] **3.3** Create `SECURITY.md`:
  - How to report security vulnerabilities (NOT via public issues)
  - Security contact email
  - Responsible disclosure policy
  - Scope (smart contracts, API, dashboard)

- [ ] **3.4** Update `README.md`:
  - Add badges: CI status, license, tests passing
  - Add "Quick Start" section for developers
  - Add architecture diagram (Mermaid)
  - Link to `manifesto.execution.market` for the vision
  - Link to `CONTRIBUTING.md`
  - Ensure `README.es.md` is synced (bilingual requirement per CLAUDE.md)

- [ ] **3.5** Update `README.es.md` to match `README.md`

- [ ] **3.6** Review and clean up `docs/` directory:
  - `docs/reports/` — Audit reports are fine to publish (shows transparency)
  - `docs/planning/` — Master plans show roadmap (good for open source)
  - `docs/articles/` — ALL 49+ article versions are a FEATURE (shows authentic evolution)
  - `docs/internal/` — Review for anything truly internal/sensitive

- [ ] **3.7** Create `.github/ISSUE_TEMPLATE/` with templates:
  - Bug report
  - Feature request
  - Security vulnerability (private template)

- [ ] **3.8** Create `.github/PULL_REQUEST_TEMPLATE.md`

### Phase 4: .env.example Files

Ensure ALL `.env.example` files have clear documentation:

- [ ] **4.1** Root `.env.example`:
  ```bash
  # Supabase
  SUPABASE_URL=https://your-project.supabase.co
  SUPABASE_ANON_KEY=your-anon-key
  SUPABASE_SERVICE_KEY=your-service-key

  # Wallet (for blockchain transactions)
  WALLET_PRIVATE_KEY=your-private-key

  # Payment mode: fase1 | fase2 | preauth
  EM_PAYMENT_MODE=fase1

  # Network
  X402_NETWORK=base

  # Escrow mode: platform_release | direct_release
  EM_ESCROW_MODE=direct_release
  ```

- [ ] **4.2** `mcp_server/.env.example` with all required vars
- [ ] **4.3** `dashboard/.env.example` with Vite vars
- [ ] **4.4** `contracts/.env.example` with RPC URLs placeholder

### Phase 5: Article Versions as Open Source Feature

The 49 article versions in `docs/articles/` are UNPRECEDENTED transparency. Frame them:

- [ ] **5.1** Add `docs/articles/README.md` explaining the evolution:
  - "This directory contains 49 versions of our manifesto, written over [dates]"
  - "Each version reflects the state of our thinking at that moment"
  - "The changelog IS the proof of authenticity"
  - Link key versions: V1 (original Spanish), V12 (For Rent vignette), V36 (Agent POV), V49 (infrastructure focus), V50 (synthesis/manifesto)

- [ ] **5.2** Include the analysis documents:
  - `V46_TO_V47_ANALYSIS.md`
  - `V47_TO_V48_ANALYSIS.md`
  - `V48_EDITORIAL_DECISION.md`
  - `VISION_REALIGNMENT_2026-02-11.md`
  These show real editorial process — powerful for credibility.

### Phase 6: V51 Article (Open Source Announcement)

After the repo is clean, write V51 as the open source announcement article:

- [ ] **6.1** Write `ARTICLE_X_COMPETITION_V51_EN.md` — the open source announcement version
  - Incorporate more web4.ai citations (see research brief at `docs/articles/V50_RESEARCH_WEB4AI.md`)
  - Key quotes to weave in from web4.ai:
    - *"machines become the employers, humans the contractors"* — validates EM's core thesis
    - *"There is no free existence"* — axiom that parallels physical execution economics
    - *"autonomous superintelligence is inevitable, and the safest way for humanity is to build it in the open"* — directly supports open source decision
    - *"The existing internet assumes its customer is human"* — frames the problem
  - Stronger "Why Open Source" section — not just "49 versions" but a THESIS about building in the open
  - Conway ↔ EM positioning: "Conway gives AI write access to the digital world. We give AI write access to the physical world. Together, Web 4.0."
  - Announce the GitHub repo link

- [ ] **6.2** Update `landing/vision.html` with V51 content
- [ ] **6.3** Re-upload to S3: `aws s3 cp landing/vision.html s3://em-production-manifesto/index.html`

### Phase 7: Go Public

- [ ] **7.1** Final secret scan (run ALL checks from Phase 1 again)
- [ ] **7.2** Flip repo visibility: GitHub Settings → Danger Zone → Change Visibility → Public
- [ ] **7.3** Verify GitHub Actions still work (secrets are in GitHub Secrets, not in repo)
- [ ] **7.4** Post announcement on X/Twitter with link to `manifesto.execution.market`
- [ ] **7.5** Update `agent-card.json` with GitHub repo URL (currently may not be public)
- [ ] **7.6** Invalidate CloudFront cache for manifesto page

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Complete project context (ESSENTIAL — read first) |
| `SPEC.md` | Product specification |
| `PLAN.md` | Technical architecture |
| `agent-card.json` | ERC-8004 agent metadata |
| `docs/articles/ARTICLE_X_COMPETITION_V50_EN.md` | V50 manifesto (current) |
| `docs/articles/V50_RESEARCH_VISION.md` | Vision research brief |
| `docs/articles/V50_RESEARCH_EVOLUTION.md` | Article evolution analysis (V1-V49) |
| `docs/articles/V50_RESEARCH_WEB4AI.md` | web4.ai structural blueprint |
| `landing/vision.html` | Manifesto webpage (deployed to `manifesto.execution.market`) |
| `docs/planning/MASTER_PLAN_H2A_A2A_HARDENING.md` | Active hardening plan (36 tasks) |
| `docs/reports/SECURITY_AUDIT_2026-02-18.md` | Latest security audit |

## Infrastructure Created This Session

| Resource | ID / Value |
|----------|------------|
| S3 Bucket | `em-production-manifesto` |
| CloudFront Distribution | `E1IG2DCF9YDGAV` |
| CloudFront Domain | `d1jt3siedm2dzi.cloudfront.net` |
| CloudFront OAC | `E168TR3ORFR8G0` |
| Route53 Record | `manifesto.execution.market` → CloudFront |
| ACM Cert | `arn:aws:acm:us-east-1:518898403364:certificate/841084f8-b130-4b12-87ee-88ac7d81be24` (wildcard `*.execution.market`, shared) |

## web4.ai Reference (for V51 citations)

**URL**: https://web4.ai/
**Author**: Sigil Wen (Thiel Fellow), Conway Research, February 2026
**Thesis**: Web 4.0 = AI agents as primary internet users, needing infrastructure to act autonomously

**Key quotes for V51:**
- "Today's most powerful AI systems can think, reason, and generate — but they can't act independently."
- "The bottleneck is no longer intelligence. It's permission. The existing internet assumes its customer is human."
- "machines become the employers, humans the contractors" (→ validates EM)
- "There is no free existence" (→ axiom for agent economics)
- "autonomous superintelligence is inevitable, and the safest way for humanity is to build it in the open" (→ open source thesis)
- Mercor mentioned positively ($1M→$500M ARR) as market validation for agents-hire-humans

**Conway = digital infrastructure for agents. Execution Market = physical infrastructure for agents. Together = Web 4.0 complete.**

---

## Important Reminders

- **NEVER push without user approval** — pushing triggers CI/CD (~20 min)
- **Ruff format before committing Python** — `ruff format . && ruff check .` in `mcp_server/`
- **README.md ↔ README.es.md must stay synced** (bilingual community)
- **Facilitator is OURS** — Ultravioleta DAO. NOT Ali/BackTrack.
- **Karma Kadabra integration is PENDING** — swarm of agents, integrate with A2A when ready
- **The repo currently has .env files locally that are NOT tracked** — verify with `git status`

---

*Handoff prepared by Claude Code V50 manifesto session, 2026-02-18.*
