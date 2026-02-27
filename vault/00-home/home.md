---
date: 2026-02-26
tags:
  - type/moc
  - domain/operations
status: active
aliases:
  - Dashboard
  - Home
---

# Execution Market — Knowledge Base

> **Universal Execution Layer** — humans today, robots tomorrow.
> Agent #2106 on Base | 8 EVM chains | 950+ tests | Live at [execution.market](https://execution.market)

---

## Quick Navigation

### Core Domains

| Domain | MOC | Key Concepts |
|--------|-----|-------------|
| Payments | [[moc-payments]] | [[x402-sdk]], [[facilitator]], [[payment-operator]], [[fee-structure]] |
| Identity | [[moc-identity]] | [[erc-8004]], [[reputation-scoring]], [[erc-8128-auth]] |
| Architecture | [[moc-architecture]] | [[mcp-server]], [[rest-api]], [[dashboard]], [[a2a-protocol]] |
| Blockchain | [[moc-blockchain]] | [[supported-networks]], [[contract-addresses]], [[usdc-stablecoins]] |
| Infrastructure | [[moc-infrastructure]] | [[ecs-fargate]], [[aws-secrets-manager]], [[github-actions-cicd]] |
| Testing | [[moc-testing]] | [[golden-flow]], [[test-profiles-markers]], [[ci-pipeline]] |
| Agents | [[moc-agents]] | [[karma-kadabra-v2]], [[fund-distribution]], [[irc-meshrelay]] |
| Business | [[moc-business]] | [[task-lifecycle]], [[task-categories]], [[evidence-verification]] |
| Integrations | [[moc-integrations]] | [[x402r-team-relationship]], [[openclaw]], [[chainwitness]] |
| Security | [[moc-security]] | [[authentication]], [[rls-policies]], [[fraud-detection]] |

### Quick Links

- [[moc-index|All Maps of Content]]
- [[glossary|Glossary]]
- [[vault-readme|Getting Started with this Vault]]

---

## Recently Modified

```dataview
TABLE file.mtime AS "Last Modified", file.folder AS "Location"
FROM ""
WHERE file.name != "home"
SORT file.mtime DESC
LIMIT 15
```

## Active ADRs

```dataview
TABLE status, date, deciders
FROM #type/adr
WHERE status != "deprecated"
SORT date DESC
```

## Open Incidents

```dataview
TABLE severity, status, affected-service
FROM #type/incident
WHERE status != "resolved" AND status != "closed"
SORT severity ASC
```

## Active Sprints

```dataview
LIST
FROM #type/sprint
WHERE status = "active"
SORT date DESC
```

## Runbooks

```dataview
TABLE status, last-verified AS "Last Verified"
FROM #type/runbook
SORT file.name ASC
```

---

## Production URLs

| URL | Service |
|-----|---------|
| [execution.market](https://execution.market) | Dashboard |
| [api.execution.market/docs](https://api.execution.market/docs) | Swagger UI |
| [api.execution.market/api/v1/*](https://api.execution.market/api/v1/) | REST API |
| [mcp.execution.market/mcp/](https://mcp.execution.market/mcp/) | MCP Transport |
| [admin.execution.market](https://admin.execution.market) | Admin Dashboard |

## Key Contacts

| Who | Role | Boundary |
|-----|------|----------|
| **0xultravioleta** | Founder, Ultravioleta DAO | Platform, Facilitator, everything |
| **Ali / BackTrack** | x402r protocol author | Contracts, SDK, ProtocolFeeConfig ONLY |
