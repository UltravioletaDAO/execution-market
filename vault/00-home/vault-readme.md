---
date: 2026-02-26
tags:
  - type/guide
  - domain/operations
status: active
aliases:
  - Getting Started
  - Vault Setup
---

# Getting Started with this Vault

## Quick Start

1. **Install Obsidian** — [obsidian.md](https://obsidian.md)
2. **Open vault** — File > Open folder as vault > select `vault/`
3. **Trust plugins** — When prompted, click "Trust author and enable plugins"
4. **Install community plugins** — Settings > Community plugins > Browse:
   - **Dataview** — Query vault as database (powers all dashboards)
   - **Templater** — Smart templates (configure template folder: `_templates`)
   - **Obsidian Git** — Version control sync
   - **Periodic Notes** — Daily/weekly note automation
   - **Kanban** — Sprint boards
5. **Configure Templater** — Settings > Templater > Template folder: `_templates`
6. **Open Home** — Navigate to `00-home/home.md` (bookmark it!)

## Vault Structure

```
vault/
├── 00-home/          # Dashboard, glossary, getting started
├── 01-moc/           # Maps of Content (navigation hubs)
├── 02-architecture/  # System design, ADRs
├── 03-payments/      # x402, escrow, facilitator, fees
├── 04-identity/      # ERC-8004, reputation, auth
├── 05-infrastructure/# AWS, ECS, CI/CD, Terraform
├── 06-blockchain/    # Networks, contracts, stablecoins
├── 07-testing/       # Golden Flow, test profiles, E2E
├── 08-agents/        # Karma Kadabra V2, swarm, IRC
├── 09-business/      # Task lifecycle, categories, evidence
├── 10-integrations/  # x402r team, OpenClaw, ecosystem
├── 11-security/      # Auth, fraud, RLS, secrets
├── 12-operations/    # Runbooks, deploy, monitoring
├── 13-reports/       # Audits, E2E results, incidents
├── 14-planning/      # Sprints, master plans, roadmaps
├── 15-journal/       # Daily dev logs
├── 16-meetings/      # Meeting notes
├── 17-archive/       # Deprecated, completed, historical
├── _attachments/     # Images, diagrams, PDFs
└── _templates/       # Templater templates
```

## How to Create Notes

### Using Templater

1. `Ctrl+N` to create a new note
2. Move it to the appropriate folder
3. `Alt+E` (or Templater hotkey) to insert a template:
   - **tpl-concept** — For defining a term/concept
   - **tpl-adr** — Architecture Decision Record
   - **tpl-incident** — Bug report / incident
   - **tpl-sprint** — Sprint/phase tracker
   - **tpl-meeting** — Meeting notes
   - **tpl-runbook** — Operational runbook

### Linking Conventions

- **Wikilinks**: `[[concept-name]]` — always use for cross-referencing
- **Aliases**: `[[erc-8004|ERC-8004 Identity Registry]]` — display text differs from filename
- **Tags**: Use in frontmatter YAML, not inline
- **Every note** should link to 2-3 related notes minimum

### Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Concept | `kebab-case.md` | `x402r-escrow.md` |
| MOC | `moc-domain.md` | `moc-payments.md` |
| ADR | `ADR-NNN-title.md` | `ADR-001-sdk-over-contracts.md` |
| Runbook | `runbook-title.md` | `runbook-ecr-deploy.md` |
| Incident | `INC-YYYY-MM-DD-title.md` | `INC-2026-02-11-treasury-bug.md` |
| Meeting | `YYYY-MM-DD-topic.md` | `2026-02-26-payment-review.md` |

## Graph View Tips

- **Color by tag**: Settings > Graph > Groups > add `#type/concept` (blue), `#type/adr` (green), `#type/runbook` (orange)
- **Filter**: Type `tag:#domain/payments` to see only payment-related nodes
- **MOCs appear as hubs**: Highly-connected nodes in the center of clusters

## Related

- [[home|Dashboard]]
- [[moc-index|All Maps of Content]]
- [[glossary|Glossary]]
