---
date: 2026-02-26
tags:
  - type/moc
  - domain/index
status: active
aliases:
  - Master Index
  - MOC Index
  - Map of Content
---

# Execution Market — Master Index

> Navigation hub for the entire Execution Market knowledge base.
> **Universal Execution Layer** — humans today, robots tomorrow.

---

## Domain Maps

| MOC | Domain | Description |
|-----|--------|-------------|
| [[moc-payments]] | Payments | x402 SDK, escrow, fee model, wallets, settlement flows (Fase 1/2/5) |
| [[moc-identity]] | Identity & Reputation | ERC-8004, ERC-8128, Agent #2106, reputation scoring, auth |
| [[moc-architecture]] | Architecture | Data flow, MCP server, REST API, task lifecycle, Supabase schema |
| [[moc-blockchain]] | Blockchain | Smart contracts, deployment addresses, multichain config (15 networks) |
| [[moc-infrastructure]] | Infrastructure | AWS ECS Fargate, ECR, ALB, Route53, Terraform, CI/CD |
| [[moc-testing]] | Testing | 950+ pytest suite, Golden Flow E2E, Playwright, test profiles |
| [[moc-agents]] | Agents | Karma Kadabra V2 swarm (24 agents), MCP tools, A2A protocol |
| [[moc-business]] | Business | Platform fee (13%), task categories, executor tiers, pricing |
| [[moc-integrations]] | Integrations | x402r protocol, Facilitator, OpenClaw, MeshRelay IRC, Turnstile |
| [[moc-security]] | Security | Fraud detection, GPS antispoofing, RLS policies, secrets management |

---

## Quick Links

- [[home]] — Vault entry point
- [[glossary]] — Key terms and acronyms
- [[ADR-index]] — Architecture Decision Records
- [[runbook-index]] — Operational runbooks

---

## How to Navigate

1. **Start with a domain MOC** above to explore a topic area
2. Each MOC links to **concept notes** (atomic, one idea per note)
3. Concept notes link to **source files**, **ADRs**, and **runbooks**
4. Use backlinks in Obsidian to discover unexpected connections

---

## Project Vitals

| Field | Value |
|-------|-------|
| Agent ID | 2106 (Base mainnet) |
| Dashboard | `https://execution.market` |
| API | `https://api.execution.market` |
| MCP | `https://mcp.execution.market/mcp/` |
| Repo | `ultravioletadao/execution-market` |
| Stack | Python + FastMCP, React + Vite, Supabase, x402 SDK |
