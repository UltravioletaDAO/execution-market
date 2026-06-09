---
date: 2026-06-09
tags:
  - type/runbook
  - domain/security
  - domain/payments
  - domain/blockchain
status: active
aliases:
  - Facilitator Security Audit Handoff
  - x402-rs Audit Prompt
related-files:
  - docs/reports/security-audit-2026-06-09/HANDOFF_GENERIC_SECURITY_AUDIT.md
---

# Ultravioleta Facilitator (x402-rs) — Security Audit Handoff

> **For:** the Claude Code instance running inside the **x402-rs** repo (the Ultravioleta Facilitator at `facilitator.ultravioletadao.xyz`).
>
> **What to do:** paste this entire file into Claude Code at the facilitator repo root and tell it to execute. It is a self-contained, multi-agent security-audit directive customized to the facilitator's actual architecture. It follows the same ruthless structure as the generic handoff (recon → HR roster → parallel finders → adversarial verification → PM synthesis) but with the APP CONTEXT pre-filled from inspection of the facilitator source.
>
> **Why the facilitator is the highest-stakes target in the stack.** The facilitator is the ONLY component that holds a hot signing key and pays gas to execute on-chain settlement, escrow capture/release/refund, and ERC-8004 reputation writes across ~20 networks. Every Execution Market payment, and payments from every other x402 merchant, route through it gaslessly. **If the Facilitator EOA key leaks, or if an attacker can make the facilitator settle/capture/refund an authorization it should have rejected, funds are lost directly.** This audit's #1 objective is to prove that cannot happen.

---

## APP CONTEXT (pre-filled from source inspection)

### What it is
x402-rs is a **gasless multi-chain payment facilitator** implementing HTTP 402. Clients sign payment authorizations off-chain (EIP-3009 `ReceiveWithAuthorization` / `TransferWithAuthorization` for EVM, equivalents for non-EVM); the facilitator submits them on-chain and **pays the gas from its own EOA**. It also provides **ERC-8004 on-chain reputation** (register / feedback / reputation reads) for AI agents, and an **x402r escrow** layer (AuthCaptureEscrow + PaymentOperator) used by Execution Market for hold-then-release task payments. "No custody, no trust, just payments" is the claim — **the audit must test whether that claim actually holds.**

### Stack & layout (Rust, `Cargo.toml` workspace)
- `src/` — the axum HTTP service. Key modules to scrutinize:
  - `main.rs`, `lib.rs`, `handlers.rs`, `from_env.rs` — service bootstrap, route wiring, env-driven config.
  - `facilitator.rs`, `facilitator_local.rs` — **core settlement logic** (verify → settle). The heart of fund movement.
  - `escrow.rs`, `payment_operator/` — **x402r escrow** authorize/capture/release/refund. Who is allowed to release/refund? Is the operator allowlist enforced?
  - `erc8004/` — register / feedback / reputation writes. **Can anyone forge reputation for any agent?** Is the caller's authority over the agentId verified?
  - `nonce_store.rs`, `idempotency_store.rs` — **replay & double-execution defense.** Are nonces unique-per-settle and durable across restarts? Can the same authorization be settled twice (e.g. via idempotency key collision or store reset)?
  - `blocklist.rs`, `blacklist-v1.2.1.json` — sanctioned-address / abuse blocking. Is it enforced on EVERY value path (settle AND escrow AND register)?
  - `network.rs`, `chain/`, `caip2.rs`, `provider_cache.rs`, `from_env.rs` — RPC endpoints, chain config, which networks/tokens are accepted. **Is the accepted-token/recipient set constrained, or can an attacker get the facilitator to move an arbitrary token / to an arbitrary recipient?**
  - `redact.rs`, `debug_utils.rs`, `telemetry.rs`, `sig_down.rs` — logging/observability. **Does any log/trace/error response leak the EOA private key, RPC API keys, or full signed authorizations?**
  - `json_depth.rs`, `timestamp.rs`, `types.rs`, `types_v2.rs`, `openapi.rs` — request parsing limits, timestamp/`validBefore`/`validAfter` validation, DTOs. **Is `validBefore`/`validAfter` actually enforced (expiry / not-yet-valid)? Is request body depth/size bounded against resource-exhaustion?**
  - `discovery*.rs` (`discovery`, `discovery_aggregator`, `discovery_crawler`, `discovery_store`) — agent/resource discovery + crawler. **SSRF risk in the crawler? Can `/discovery/register` poison the store?**
  - `fhe_proxy.rs` — FHE proxy path. Audit for unauthenticated proxying / SSRF.
- `crates/` — `x402-axum` (server middleware), `x402-compliance`, `x402-reqwest` (client). Audit `x402-axum` for auth/middleware gaps.
- `contracts/` — Foundry (Solidity): AuthCaptureEscrow, PaymentOperator, conditions, ERC-8004 registries. Has `echidna.yaml` (fuzzing). Audit capture/release/refund authorization, condition logic, and reentrancy.
- `terraform/` — AWS infra (`environments/`, `task-definitions/`, `FACILITATOR_MAINNET_MIGRATION.md`). Audit IAM, secrets storage, security groups, public exposure, ECS task-def secrets.
- `lambda/balances` — balance Lambda. Audit its IAM role + any public invoke path.
- `Caddyfile`, `docker/`, `docker-compose*.yml` — edge/proxy + container config. Audit TLS, exposed ports, and whether the admin/observability surfaces are internet-reachable.
- `scripts/`, `tools/`, `justfile` — operational scripts. Audit for hardcoded keys / unsafe ops.

### HTTP surface (observed routes — verify auth on each)
Value/identity-moving: `/settle`, `/verify` (implied), `/escrow/state`, `/register`, `/feedback`, `/feedback/response`, `/feedback/revoke`, `/identity/{network}/{agent_id}`, `/reputation/{network}/{agent_id}`, `/discovery/register`, `/discovery/resources`, `/blacklist`.
Per-network settle routes: `/base`, `/ethereum`, `/polygon`, `/arbitrum`, `/optimism`, `/celo`, `/celo-colombia`, `/monad`, `/avalanche`, `/skale`, `/scroll`, `/unichain`, `/hyperevm`, `/bsc`, `/solana`, `/near`, `/sui`, `/stellar`, `/algorand`, `/fogo`, plus token routes `/ausd`, `/eurc`, `/pyusd`.
Meta/health: `/health`, `/supported`, `/accepts`, `/paid-content`, `/docs/`, `/openapi`, `/logo`, `/favicon`.
> **For each route: which require authentication/authorization, and which are intentionally public? Flag any state-changing or fund-moving route that is reachable WITHOUT proof the caller is entitled to the action.**

### Money / asset flow (MOST IMPORTANT)
1. **Settlement (`/settle`):** caller submits a signed EIP-3009 authorization. Facilitator verifies signature, nonce, `validBefore`/`validAfter`, token, amount, recipient — then **submits on-chain paying gas from the Facilitator EOA.** Audit every validation: signature recovery correctness, nonce uniqueness + durability (replay), expiry enforcement, and whether `to`/recipient is taken from the signed payload (good) vs. a request field an attacker controls (bad).
2. **Escrow (`escrow.rs` / `payment_operator/`):** authorize (lock) → capture/release (to worker, with fee split) → refund (to payer). Audit the **operator allowlist** (only registered PaymentOperators may trigger release/refund) and the **condition contracts** (StaticAddressCondition / fee calculator) for who can authorize/release/refund. A bug here = drain of locked escrow.
3. **ERC-8004 (`erc8004/`, `/register`, `/feedback`):** on-chain identity + reputation writes, gasless. Audit whether the facilitator verifies the caller controls the agentId/wallet it is writing reputation for — **reputation forgery** is a data-integrity P1+ and could be P0 if reputation gates fund flows downstream.
4. **Gas/keys:** the **Facilitator EOA private key** is the crown jewel. Trace exactly where it is loaded from (env? secret manager? file?), whether it is ever logged/redacted-incorrectly/returned in an error, and whether the IAM role / container can be coerced into exposing it.

### Auth & trust model (verify, don't assume)
- The facilitator is designed to be **trustless toward payers** (it can only move funds the payer cryptographically authorized) — **the audit's job is to falsify that.** Find any path where the facilitator moves more, a different token, to a different recipient, or twice.
- **Caller authentication on privileged ops:** is `/settle`/escrow/register rate-limited and/or restricted to allowlisted operators, or fully open? An open `/settle` that only ever moves payer-authorized funds is acceptable; an open escrow-release is not.
- **Blocklist enforcement:** sanctioned addresses must be rejected on every value path.

### Security-gating configuration (find these in `from_env.rs` and task-definitions)
Enumerate every env var that gates behavior: which networks/RPCs are enabled, the EOA key source, operator/merchant allowlists, rate-limit settings, idempotency/nonce store backing (in-memory vs. persistent — **in-memory across restarts = replay risk**), debug/verbose logging flags (must be OFF in prod), and any "test mode" / "server signing" style flag that must never be true in prod. Confirm production values are safe.

### Known high-value concerns to probe first
- **EOA key exposure** (env/log/error/IaC state/IAM).
- **Replay / double-settle** across restarts and across the idempotency layer.
- **Escrow release/refund authorization** — operator allowlist actually enforced on-chain AND off-chain.
- **`validBefore`/`validAfter` and amount/recipient validation** taken from the SIGNED payload, not from spoofable request fields.
- **Reputation/identity forgery** via `/feedback` and `/register`.
- **SSRF** in `discovery_crawler.rs` and `fhe_proxy.rs`.
- **DoS:** unbounded JSON depth/body, expensive RPC fan-out per request, missing rate limits on gas-spending endpoints (an attacker forcing the facilitator to spend gas = economic DoS / treasury drain).
- **Contract layer:** reentrancy and authorization in capture/release/refund; run/inspect the existing echidna properties.

### Extra context
- This repo has NO Supabase / app database — skip RLS-style auditors; the state stores that matter are `nonce_store`/`idempotency_store` and any persistent backing they use.
- The facilitator serves MULTIPLE merchants, not just Execution Market — a vulnerability here is blast-radius across the whole x402 ecosystem. Weight severity accordingly.
- Version observed: ~1.29.x (README badge). Confirm the live version and whether any CVE-bearing dependency is in `Cargo.lock`.

---

## AUDIT DIRECTIVE (execute this)

Run a ruthless, parallelized, multi-agent security audit (dynamic workflows / subagents) of THIS facilitator repo, using the APP CONTEXT above. Overriding goal: prove an attacker **cannot** (a) extract or coerce use of the EOA key, (b) make the facilitator move funds it wasn't cryptographically authorized to move, (c) settle/capture/release/refund twice or after expiry, (d) drain escrow, (e) forge identity/reputation, or (f) economically DoS the gas treasury. Style nits are out of scope.

Phases:
- **R — Recon (1 agent):** dense attack-surface briefing — every route + its auth, every value path in `facilitator*.rs`/`escrow.rs`/`payment_operator/`/`erc8004/`, the EOA key lifecycle, nonce/idempotency backing, blocklist enforcement points, the contracts, the Terraform/Lambda infra, and every gating env var in `from_env.rs` + task-definitions. Shared with all agents.
- **HR — Hire roster (1 agent, Head of HR, 100y hiring AI auditors):** design 14–22 NON-OVERLAPPING specialist auditors from the recon briefing. Must cover at least: EIP-3009 signature/nonce/expiry/amount/recipient validation; replay & double-settle (store durability); escrow capture/release/refund authorization + operator allowlist; ERC-8004 reputation/identity forgery; EOA key handling & secret leakage in logs/errors/redaction; per-network/token config & recipient constraints; rate-limiting / DoS / gas-treasury exhaustion; JSON depth/body limits & parser DoS; SSRF in discovery crawler + FHE proxy; blocklist enforcement coverage; the `x402-axum` middleware/auth; the Solidity contracts (reentrancy + authorization + echidna properties); Terraform IAM/secrets/security-groups/public-exposure; the balances Lambda; Caddy/docker edge exposure; `Cargo.lock` dependency CVEs; operational scripts for hardcoded keys.
- **F — Find (N parallel):** each auditor reads the ACTUAL Rust/Solidity/HCL, traces flows end-to-end, reports structured findings (title, severity P0–P3, component, file:line + redacted code quote, impact, exploit steps, concrete proposed fix detailed enough to implement cold, effort S/M/L, confidence). List what was reviewed; never invent findings.
- **V — Verify (adversarial, per P0/P1):** independent verifier tries to REFUTE each high finding by re-reading the code and checking for an existing control; default "not real" unless the path is confirmed end-to-end; may adjust severity and refine the fix.
- **S — Synthesize (1 ruthless PM):** dedupe by root cause, rank fund-loss-first, write the posture summary.

### HARD RULES (every agent)
- **READ-ONLY.** No file edits, no commits, no mutating commands. AWS CLI read-only only (describe/get/list). NEVER print the VALUE of the EOA key, RPC API keys, or any secret — by name/location only; the operator streams the terminal.
- Cite file:line + redacted code for every finding. No theoretical findings — confirm a control's absence before reporting it.

### DELIVERABLES (write to disk in this repo, e.g. `docs/security-audit-<date>/`)
1. `FACILITATOR_SECURITY_AUDIT_RISK_REPORT.md` — exec summary, posture grade, ranked confirmed-findings table (fund-loss first).
2. One self-contained fix doc per P0/P1 in `fixes/` — root cause, exact files, code-level fix, test plan (extend the echidna/fuzz + Rust tests), rollback notes, verification steps.
3. `MASTER_PLAN_EXECUTION.md` — phased, granular task list (Phase N / task 1,2,3…) with explicit success criteria, ready for a separate execution team to implement systematically.
4. If any infra change is needed (IAM, secret rotation, security group), include the exact Terraform diff and a manual `aws` apply note in the relevant fix doc.

### FINAL OUTPUT TO THE OPERATOR
One report: coverage, finding counts by severity, the top fund-loss/key-exposure risks, where the deliverables live, any infra/secret-rotation steps to run by hand, and an honest statement of residual risk and what was not covered. **If the EOA key is found to be exposed or rotatable-by-attacker, that is P0 — surface it FIRST and recommend immediate key rotation.**

---

*Generated by the Execution Market security-audit orchestrator on 2026-06-09 from read-only inspection of the x402-rs source tree. Customize the APP CONTEXT further before running if the facilitator has changed since.*
