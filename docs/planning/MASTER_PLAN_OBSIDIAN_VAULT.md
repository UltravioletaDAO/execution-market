# Master Plan: Obsidian Vault for Execution Market

> **Created**: 2026-02-26
> **Status**: PENDING APPROVAL
> **Scope**: Set up an interconnected Obsidian vault that serves as the "thinking layer" for the Execution Market project

---

## Overview

Transform the existing 200+ markdown files and accumulated knowledge into an interconnected Obsidian vault with proper wikilinks, MOCs (Maps of Content), templates, Dataview queries, and a navigable knowledge graph.

**Approach**: PARA + MOC hybrid. Vault lives as a **separate directory** (`Z:\ultravioleta\dao\execution-market\vault\`) inside the repo but with its own `.obsidian/` config. Existing `docs/` files remain as-is (canonical source); the vault acts as the navigation and thinking layer on top.

**Key Decisions**:
- Vault INSIDE the repo (single source of truth, notes reference code directly)
- kebab-case naming for all files
- Shallow folders (max 2 levels)
- 5 essential plugins: Dataview, Templater, Obsidian Git, Periodic Notes, Kanban
- MOCs for each of the 10 knowledge domains
- Frontmatter with `status`, `tags`, `aliases`, `related-files`

---

## Phase 1: Vault Skeleton & Configuration (Foundation)

> **Priority**: P0 — Must complete first
> **Estimated tasks**: 6

### Task 1.1: Create vault directory structure

**What**: Create the folder skeleton inside `vault/`

```
vault/
├── .obsidian/              # Obsidian config (partial git tracking)
├── 00-home/                # Dashboard, master MOC
├── 01-moc/                 # Maps of Content (one per domain)
├── 02-architecture/        # System design, ADRs
├── 03-payments/            # x402, escrow, facilitator, fees
├── 04-identity/            # ERC-8004, reputation, ERC-8128
├── 05-infrastructure/      # AWS, ECS, CI/CD, Terraform
├── 06-blockchain/          # Networks, contracts, stablecoins
├── 07-testing/             # Golden Flow, test profiles, E2E
├── 08-agents/              # Karma Kadabra, swarm, IRC
├── 09-business/            # Task lifecycle, categories, evidence
├── 10-integrations/        # x402r team, OpenClaw, MeshRelay
├── 11-security/            # Auth, fraud, RLS, secrets
├── 12-operations/          # Runbooks, deploy, monitoring
├── 13-reports/             # Audits, E2E results, incidents
├── 14-planning/            # Sprints, master plans, roadmaps
├── 15-journal/             # Daily dev logs
├── 16-meetings/            # Meeting notes
├── 17-archive/             # Deprecated, completed, historical
├── _attachments/           # Images, diagrams, PDFs
└── _templates/             # All Templater templates
```

**Validation**: `ls vault/` shows all 20 directories

### Task 1.2: Create .gitignore for vault

**File**: `vault/.gitignore`
**What**: Selective tracking of Obsidian config — ignore workspace (device-specific), track plugin list and core settings

```gitignore
# Device-specific (changes every session)
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/plugins/*/data.json
.obsidian-git-data

# Track these (shared team settings)
# .obsidian/app.json
# .obsidian/appearance.json
# .obsidian/community-plugins.json
# .obsidian/core-plugins.json

# System
.trash/
.DS_Store
Thumbs.db
```

**Validation**: `.gitignore` exists and workspace.json is excluded

### Task 1.3: Create Obsidian app config

**File**: `vault/.obsidian/app.json`
**What**: Core Obsidian settings — wikilinks enabled, default new note location, attachment folder

**Key settings**:
- `useMarkdownLinks: false` (use wikilinks `[[]]`)
- `newFileLocation: "folder"` → `00-home/`
- `attachmentFolderPath: "_attachments"`
- `showLineNumber: true`
- `strictLineBreaks: true`

**Validation**: Open vault in Obsidian, verify wikilinks work

### Task 1.4: Create community plugins manifest

**File**: `vault/.obsidian/community-plugins.json`
**What**: List of 5 essential + 5 recommended plugins to install

**Essential (install first)**:
1. `dataview` — Query vault as database
2. `templater-obsidian` — JavaScript-powered templates
3. `obsidian-git` — Git sync from within Obsidian
4. `periodic-notes` — Daily/weekly note automation
5. `obsidian-kanban` — Sprint boards

**Recommended**:
6. `obsidian-tasks-plugin` — Cross-vault task tracking
7. `quickadd` — Rapid capture macros
8. `obsidian-excalidraw-plugin` — Diagrams inside vault
9. `obsidian-omnisearch` — Enhanced full-text search
10. `cm-editor-syntax-highlight-obsidian` — Code block coloring

**Validation**: Plugin list file exists (user installs manually on first open)

### Task 1.5: Create Templater templates

**Files**: `vault/_templates/` (6 templates)

1. **`_templates/tpl-adr.md`** — Architecture Decision Record (MADR format)
   - Frontmatter: date, status (proposed/accepted/deprecated), deciders, tags
   - Sections: Context, Decision Drivers, Options, Outcome, Consequences

2. **`_templates/tpl-concept.md`** — Glossary/concept entry
   - Frontmatter: date, aliases, tags (`type/concept`)
   - Sections: Definition, Context, Key Properties, Related

3. **`_templates/tpl-incident.md`** — Bug report / incident
   - Frontmatter: date, status, severity (P0-P3), affected-service
   - Sections: Summary, Timeline, Impact, Root Cause, Resolution, Action Items

4. **`_templates/tpl-sprint.md`** — Sprint/phase tracker
   - Frontmatter: date, status, phase, sprint number
   - Sections: Goals, Tasks (checklist), Decisions Made, Blockers, Retrospective

5. **`_templates/tpl-meeting.md`** — Meeting notes
   - Frontmatter: date, attendees, tags (`type/meeting`)
   - Sections: Agenda, Notes, Decisions, Action Items

6. **`_templates/tpl-runbook.md`** — Operational runbook
   - Frontmatter: date, status, tags (`type/runbook`), related-files
   - Sections: Purpose, Prerequisites, Steps, Verification, Rollback

**Validation**: Each template renders correctly with Templater `tp.date.now()` etc.

### Task 1.6: Create Home dashboard

**File**: `vault/00-home/home.md`
**What**: Master entry point with Dataview queries and navigation links

**Content**:
- Quick nav links to all 10 MOCs
- Dataview table: Recently modified notes (last 7 days)
- Dataview table: Active ADRs (status = accepted)
- Dataview table: Open incidents (status != resolved)
- Dataview list: Active sprints
- Links to: Daily note, this week's meeting notes, runbooks index

**Validation**: Dashboard renders Dataview queries when plugins installed

---

## Phase 2: Maps of Content (Navigation Layer)

> **Priority**: P0 — Core navigation structure
> **Estimated tasks**: 11 (1 master + 10 domain MOCs)

### Task 2.1: Master MOC index

**File**: `vault/01-moc/moc-index.md`
**What**: Top-level MOC linking to all domain MOCs

```markdown
# Maps of Content

## Core Domains
- [[moc-payments]] — x402, escrow, fees, settlement flows
- [[moc-identity]] — ERC-8004, reputation, ERC-8128 auth
- [[moc-architecture]] — MCP server, REST API, dashboard, A2A, WebSocket
- [[moc-blockchain]] — Networks, contracts, stablecoins, CREATE2
- [[moc-infrastructure]] — AWS, ECS, CI/CD, Terraform, secrets
- [[moc-testing]] — Golden Flow, test profiles, E2E, CI pipeline
- [[moc-agents]] — Karma Kadabra V2, swarm, IRC, fund distribution
- [[moc-business]] — Task lifecycle, categories, evidence, executors
- [[moc-integrations]] — x402r team, OpenClaw, MeshRelay, ecosystem
- [[moc-security]] — Auth, fraud detection, RLS, secrets management
```

### Task 2.2: MOC — Payments

**File**: `vault/01-moc/moc-payments.md`
**Links to**: 15+ concept notes covering x402 SDK, x402r escrow, facilitator, PaymentOperator, PaymentDispatcher, Fase 1/2/5/preauth flows, fee structure, wallet roles, treasury model, EIP-3009, platform fee, protocol fee, manual refund, fee sweep
**Source files referenced**: `sdk_client.py`, `payment_dispatcher.py`, `payment_events.py`, `_helpers.py`
**Docs referenced**: `PAYMENT_ARCHITECTURE.md`, `X402R_REFERENCE.md`, Fase evidence reports

### Task 2.3: MOC — Identity & Reputation

**File**: `vault/01-moc/moc-identity.md`
**Links to**: 12+ concept notes covering ERC-8004, Agent #2106, reputation scoring, Bayesian layer, ERC-8128 auth, facilitator reputation endpoints, agent card, feature flags, relay wallets, executor tiers
**Source files referenced**: `facilitator_client.py`, `identity.py`, `scoring.py`, `side_effects.py`, `bayesian.py`

### Task 2.4: MOC — Architecture

**File**: `vault/01-moc/moc-architecture.md`
**Links to**: 12+ concept notes covering MCP server, REST API (63+ endpoints), A2A protocol, dashboard (React), WebSocket server, H2A marketplace, agent executor mode, Supabase client, data flow diagram
**Source files referenced**: `server.py`, `routes.py`, routers/*, `a2a/`, `websocket/`, dashboard components

### Task 2.5: MOC — Blockchain

**File**: `vault/01-moc/moc-blockchain.md`
**Links to**: 10+ concept notes covering 8 production mainnets, contract addresses (all registries, escrows, operators), stablecoins registry, CREATE2 deployments, x402r upstream relationship, ProtocolFeeConfig
**Source files referenced**: `sdk_client.py` (NETWORK_CONFIG), `deploy-payment-operator.ts`

### Task 2.6: MOC — Infrastructure

**File**: `vault/01-moc/moc-infrastructure.md`
**Links to**: 12+ concept notes covering AWS account (518898403364), ECS Fargate cluster, ECR repos, ALB + HTTPS, Route53 DNS, CloudFront, S3 evidence storage, GitHub Actions CI/CD, image tagging policy, AWS Secrets Manager, Terraform, RPC policy (QuikNode)
**Source files referenced**: `infrastructure/`, Dockerfiles, `.github/workflows/deploy.yml`

### Task 2.7: MOC — Testing

**File**: `vault/01-moc/moc-testing.md`
**Links to**: 10+ concept notes covering Golden Flow (definitive E2E), multichain Golden Flow, test profiles/markers (core, payments, erc8004, security, infrastructure), task factory, CI pipeline, dashboard tests (Vitest + Playwright), test budget ($0.20 limit)
**Source files referenced**: `pytest.ini`, `tests/`, `e2e_golden_flow.py`, `task-factory.ts`

### Task 2.8: MOC — Agents (Karma Kadabra)

**File**: `vault/01-moc/moc-agents.md`
**Links to**: 12+ concept notes covering KK V2 swarm (24 agents), HD wallet management, fund distribution lifecycle, ERC-8004 NFTs (IDs), EIP-8128 signing, self-application prevention, payment token selection, IRC integration (MeshRelay), agent-to-agent tasks, KK V2 status (97% complete)
**Source files referenced**: `scripts/kk/`, migration 036-038, `agent_tools.py`

### Task 2.9: MOC — Business Logic

**File**: `vault/01-moc/moc-business.md`
**Links to**: 10+ concept notes covering task lifecycle (state machine), 5 task categories, evidence types (12), evidence verification (GPS, AI, forensic), executor status/tiers, bounty guidelines, application flow, submission flow, approval flow, dispute resolution
**Source files referenced**: `models.py`, `routers/tasks.py`, `verification/`, `agent_tools.py`

### Task 2.10: MOC — External Integrations

**File**: `vault/01-moc/moc-integrations.md`
**Links to**: 10+ concept notes covering x402r protocol team (BackTrack/Ali) ownership boundaries, OpenClaw (future), MoltCourt (future), ChainWitness, Colmena, Council, Ultratrack, MeshRelay/ERC-8004, Superfluid (planned), Turnstile (planned), ecosystem synergies matrix
**Source files referenced**: `SYNERGIES.md`, `a2a/`, `verification/attestation.py`

### Task 2.11: MOC — Security

**File**: `vault/01-moc/moc-security.md`
**Links to**: 10+ concept notes covering authentication (Supabase + ERC-8128 + OAuth), authorization (RLS + admin key), secret management (AWS SM), private key security, fraud detection, GPS antispoofing, image tampering, behavioral analysis, rate limiting, RLS gotchas (silent failures), wallet exposure (PII)
**Source files referenced**: `agent_auth.py`, `security/`, `verification/checks/`

---

## Phase 3: Concept Notes (Knowledge Atoms)

> **Priority**: P1 — The actual content that gets interlinked
> **Estimated tasks**: 8 batches (~80 concept notes total)

Each concept note follows `_templates/tpl-concept.md` with:
- YAML frontmatter: `date`, `aliases`, `tags`, `status`, `related-files`
- Wikilinks to related concepts (bidirectional)
- Brief definition + context + key properties
- Links to source code files and existing docs

### Task 3.1: Payment concepts (15 notes)

**Folder**: `vault/03-payments/`
**Notes**: `x402-sdk.md`, `x402r-escrow.md`, `facilitator.md`, `payment-operator.md`, `payment-dispatcher.md`, `fase-1-direct-settlement.md`, `fase-2-escrow.md`, `fase-5-trustless.md`, `preauth-legacy.md`, `eip-3009.md`, `fee-structure.md`, `wallet-roles.md`, `treasury.md`, `platform-fee.md`, `protocol-fee.md`

**Interlinking examples**:
- `x402-sdk.md` links to → `[[facilitator]]`, `[[eip-3009]]`, `[[payment-operator]]`
- `fase-5-trustless.md` links to → `[[payment-operator]]`, `[[fee-structure]]`, `[[x402r-escrow]]`
- `wallet-roles.md` links to → `[[treasury]]`, `[[platform-fee]]`, `[[fase-1-direct-settlement]]`

### Task 3.2: Identity & reputation concepts (10 notes)

**Folder**: `vault/04-identity/`
**Notes**: `erc-8004.md`, `agent-2106.md`, `reputation-scoring.md`, `bayesian-reputation.md`, `erc-8128-auth.md`, `agent-card.md`, `executor-tiers.md`, `relay-wallet.md`, `facilitator-reputation.md`, `feature-flags-erc8004.md`

### Task 3.3: Architecture concepts (10 notes)

**Folder**: `vault/02-architecture/`
**Notes**: `mcp-server.md`, `rest-api.md`, `a2a-protocol.md`, `dashboard.md`, `websocket-server.md`, `h2a-marketplace.md`, `agent-executor-mode.md`, `supabase-database.md`, `data-flow.md`, `mcp-tools-reference.md`

### Task 3.4: Blockchain concepts (8 notes)

**Folder**: `vault/06-blockchain/`
**Notes**: `supported-networks.md`, `contract-addresses.md`, `usdc-stablecoins.md`, `create2-deployments.md`, `auth-capture-escrow.md`, `static-fee-calculator.md`, `facilitator-eoa.md`, `protocol-fee-config.md`

### Task 3.5: Infrastructure concepts (10 notes)

**Folder**: `vault/05-infrastructure/`
**Notes**: `aws-account.md`, `ecs-fargate.md`, `ecr-registry.md`, `alb-dns-routing.md`, `github-actions-cicd.md`, `image-tagging-policy.md`, `aws-secrets-manager.md`, `terraform.md`, `rpc-policy-quiknode.md`, `cloudfront-s3.md`

### Task 3.6: Testing concepts (7 notes)

**Folder**: `vault/07-testing/`
**Notes**: `golden-flow.md`, `multichain-golden-flow.md`, `test-profiles-markers.md`, `task-factory.md`, `ci-pipeline.md`, `dashboard-tests.md`, `test-budget.md`

### Task 3.7: Agent ecosystem concepts (10 notes)

**Folder**: `vault/08-agents/`
**Notes**: `karma-kadabra-v2.md`, `kk-agent-fleet.md`, `hd-wallet-management.md`, `fund-distribution.md`, `eip-8128-signing.md`, `self-application-prevention.md`, `irc-meshrelay.md`, `agent-to-agent-tasks.md`, `payment-token-selection.md`, `kk-v2-status.md`

### Task 3.8: Business, integration, security concepts (10 notes)

**Folder**: Multiple (`vault/09-business/`, `vault/10-integrations/`, `vault/11-security/`)
**Notes**:
- Business: `task-lifecycle.md`, `task-categories.md`, `evidence-verification.md`, `bounty-guidelines.md`
- Integrations: `x402r-team-relationship.md`, `openclaw.md`, `chainwitness.md`
- Security: `authentication.md`, `rls-policies.md`, `fraud-detection.md`

---

## Phase 4: Operational Notes & Runbooks

> **Priority**: P1 — Practical operational knowledge
> **Estimated tasks**: 4

### Task 4.1: Deployment runbooks (4 notes)

**Folder**: `vault/12-operations/`
**Notes**:
- `runbook-ecr-deploy.md` — Full ECR build + push + force deploy recipe
- `runbook-manual-refund.md` — When payment_events shows stuck funds
- `runbook-fee-sweep.md` — POST /admin/fees/sweep process
- `runbook-golden-flow.md` — How to run the definitive E2E test

### Task 4.2: Incident notes (from existing reports)

**Folder**: `vault/13-reports/`
**What**: Convert key existing reports into vault notes with proper interlinking
- Link to `GOLDEN_FLOW_REPORT.md`, `TRUSTLESSNESS_AUDIT_REPORT.md`, security audits
- Create incident entries for known bugs (treasury settlement, stuck USDC)
- Each links back to related concept notes

### Task 4.3: ADR notes (from existing decisions)

**Folder**: `vault/02-architecture/adr/`
**What**: Create ADRs for major architectural decisions already made:
- `ADR-001-x402-sdk-over-direct-contracts.md` — Why SDK + Facilitator, not raw TXs
- `ADR-002-fase5-trustless-fee-split.md` — Credit card model with on-chain fee calc
- `ADR-003-erc8004-identity.md` — Why ERC-8004 over custom identity
- `ADR-004-supabase-over-custom-db.md` — Database choice
- `ADR-005-multichain-8-networks.md` — Why these 8 chains
- `ADR-006-gasless-payments.md` — EIP-3009 + Facilitator gas relay

### Task 4.4: Planning notes (link existing master plans)

**Folder**: `vault/14-planning/`
**What**: Create thin wrapper notes that link to existing `docs/planning/MASTER_PLAN_*.md` files
- Each note has frontmatter with status, phase, tags
- Links to relevant MOCs and concept notes
- Dataview can then query planning status across vault

---

## Phase 5: Dataview Dashboards & Queries

> **Priority**: P2 — Power features for navigation
> **Estimated tasks**: 3

### Task 5.1: Home dashboard with Dataview

**File**: `vault/00-home/home.md` (update from Phase 1)
**Queries**:
```dataview
TABLE status, date FROM #type/adr SORT date DESC LIMIT 10
```
```dataview
TABLE severity, status FROM #type/incident WHERE status != "resolved" SORT severity ASC
```
```dataview
LIST FROM "" WHERE file.mtime >= date(today) - dur(7 days) SORT file.mtime DESC LIMIT 20
```

### Task 5.2: Domain-specific dashboards

**What**: Add Dataview queries to each MOC:
- Payments MOC: table of all payment concepts with status
- Testing MOC: table of test profiles with test counts
- Infrastructure MOC: table of runbooks with last-verified date
- Agents MOC: KK agent status overview

### Task 5.3: Glossary with auto-index

**File**: `vault/00-home/glossary.md`
**What**: Auto-generated glossary using Dataview
```dataview
TABLE aliases, WITHOUT ID file.link AS "Term" FROM #type/concept SORT file.name ASC
```

---

## Phase 6: Migration & Polish

> **Priority**: P2 — Import existing content, polish edges
> **Estimated tasks**: 4

### Task 6.1: Migrate key existing docs as references

**What**: For high-value existing docs, create vault notes that either:
- **Embed**: `![[../docs/planning/PAYMENT_ARCHITECTURE.md]]` (Obsidian can embed files outside vault with relative paths)
- **Link**: Reference with `related-files` frontmatter pointing to source location
- **Extract**: For critical content, extract key sections into concept notes

**Priority docs to reference**:
- `SPEC.md`, `PLAN.md`, `ARCHITECTURE.md`
- `PAYMENT_ARCHITECTURE.md`, `X402R_REFERENCE.md`
- `GOLDEN_FLOW_REPORT.md` (EN + ES)
- `ERC8004_INTEGRATION_SPECS.md`
- `KK_FUND_DISTRIBUTION_REFERENCE.md`

### Task 6.2: Add repo root .gitignore entry

**File**: `.gitignore` (repo root)
**What**: Add entry for vault Obsidian workspace files:
```
vault/.obsidian/workspace.json
vault/.obsidian/workspace-mobile.json
vault/.obsidian/plugins/*/data.json
vault/.trash/
```

### Task 6.3: Create vault README

**File**: `vault/README.md`
**What**: Quick start guide for opening the vault in Obsidian:
1. Install Obsidian
2. "Open folder as vault" → select `vault/`
3. Trust and enable community plugins
4. Install listed plugins from community-plugins.json
5. Configure Templater to use `_templates/` folder
6. Open `00-home/home.md` as starting point

### Task 6.4: Update project CLAUDE.md

**What**: Add section about Obsidian vault to CLAUDE.md:
- Vault location: `vault/`
- Naming convention: kebab-case
- When creating new docs: create in vault with proper frontmatter + wikilinks
- MOC update policy: when adding a note, add it to the relevant MOC

---

## Summary

| Phase | Tasks | Priority | Description |
|-------|-------|----------|-------------|
| **Phase 1** | 6 | P0 | Vault skeleton, config, templates, home dashboard |
| **Phase 2** | 11 | P0 | Maps of Content (1 master + 10 domain MOCs) |
| **Phase 3** | 8 | P1 | ~80 concept notes across 10 domains with interlinking |
| **Phase 4** | 4 | P1 | Runbooks, incidents, ADRs, planning wrappers |
| **Phase 5** | 3 | P2 | Dataview dashboards and auto-generated indexes |
| **Phase 6** | 4 | P2 | Migration of existing docs, polish, documentation |
| **TOTAL** | **36** | | |

## Tagging Taxonomy

```
type/     → concept, adr, incident, runbook, meeting, sprint, moc
status/   → draft, active, completed, archived, deprecated
domain/   → payments, identity, infrastructure, blockchain, testing, agents, business, integrations, security, operations
chain/    → base, ethereum, polygon, arbitrum, avalanche, monad, celo, optimism
priority/ → p0, p1, p2
```

## Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Concept | `kebab-case.md` | `x402r-escrow.md` |
| MOC | `moc-domain.md` | `moc-payments.md` |
| ADR | `ADR-NNN-short-title.md` | `ADR-001-sdk-over-contracts.md` |
| Runbook | `runbook-short-title.md` | `runbook-ecr-deploy.md` |
| Incident | `INC-YYYY-MM-DD-title.md` | `INC-2026-02-11-treasury-bug.md` |
| Meeting | `YYYY-MM-DD-topic.md` | `2026-02-26-payment-review.md` |
| Daily log | `YYYY-MM-DD.md` | `2026-02-26.md` |

## Essential Plugins

| Plugin | Purpose | Install Priority |
|--------|---------|-----------------|
| Dataview | Query vault as database | Immediate |
| Templater | Smart templates with JS | Immediate |
| Obsidian Git | Version control sync | Immediate |
| Periodic Notes | Daily/weekly automation | Immediate |
| Kanban | Sprint boards | Immediate |
| Tasks | Cross-vault task tracking | Week 1 |
| QuickAdd | Rapid note capture | Week 1 |
| Excalidraw | Architecture diagrams | Week 2 |
| Omnisearch | Enhanced search | Week 2 |
| Syntax Highlight | Code blocks in notes | Week 2 |
