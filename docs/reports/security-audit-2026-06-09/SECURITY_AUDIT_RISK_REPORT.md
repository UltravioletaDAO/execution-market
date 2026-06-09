---
date: 2026-06-09
tags:
  - type/report
  - domain/security
  - priority/p0
status: active
aliases:
  - Security Audit Risk Report 2026-06-09
  - EM Full-Platform Security Audit
related-files:
  - docs/reports/security-audit-2026-06-09/MASTER_PLAN_EXECUTION.md
  - docs/reports/security-audit-2026-06-09/fixes/
---

# Execution Market — Full-Platform Security Audit Risk Report

> **Date:** 2026-06-09
> **Method:** Multi-agent adversarial audit. 26 specialist auditor agents (hired by an AI "Head of HR" from a recon map of the attack surface) ran in parallel; every P0/P1 finding was then re-checked by an independent adversarial verifier whose job was to *refute* it; a ruthless PM agent deduplicated and ranked the survivors. ~4.9M tokens, 46 agents, ~58 min.
> **Scope:** `mcp_server/` (REST + MCP), `dashboard/`, `admin-dashboard/`, `em-mobile/`, `ows-mcp-server/`, `supabase/` (RLS + RPC + migrations), `infrastructure/terraform/` (AWS), `.github/workflows/` (CI/CD), `contracts/` + `scripts/`, dependency supply chain.
> **Primary objective:** find every way to steal/destroy user funds, bypass auth, escalate privilege, or take the service down.

---

## ⛔ Bottom line

**The platform currently provides no enforceable authentication, authorization, or fund-custody guarantee on its public money surface.** Two of its core invariants — *"the server never touches funds"* and *"never trust client-supplied identity"* — are both broken in production today.

- **2 distinct P0** (independently catastrophic, exploitable now by an anonymous attacker)
- **9 P1** (serious, realistic exploit path)
- **3 verified P2** + **23 PM-elevated fund-loss/infra P2s** (unverified-but-credible, surfaced from the lower-severity pool)
- **76** total lower-severity findings catalogued; **2** claimed-high findings correctly **refuted** as false positives.

> **Recommendation: treat the two P0s + the worker-auth-default P1 + the RLS-regression P1s as a hard release blocker.** Until P0-01 and P0-02 are deployed, an anonymous caller can drain a victim's escrowed bounty and rebind any user's executor identity. Consider gating money movement (assignment/approval/release) behind a temporary kill-switch until the auth fixes ship.

---

## Confirmed findings (post adversarial verification)

> Each `FIX-*` doc in [`fixes/`](fixes/) is a self-contained, code-level remediation spec written for a separate execution team. Severities below are the **verifier-adjusted** values.

| Fix doc | Sev | Component | Finding | Effort |
|---|---|---|---|---|
| [FIX-P0-01](fixes/FIX-P0-01-unauthenticated-mcp-transport.md) | **P0** | MCP transport + tools | `/mcp` exposes every mutating `em_*` tool with **no authentication**, and tools trust a self-asserted `agent_id` → full task-lifecycle takeover + escrow-drain chain (merges 2 reports) | L |
| [FIX-P0-02](fixes/FIX-P0-02-migration-097-anon-get-or-create-executor.md) | **P0** | Supabase RLS | Migration 097 re-granted `get_or_create_executor` EXECUTE to `anon`, reopening **DB-001 account-takeover** (rebind any executor identity, no wallet proof) | S |
| [FIX-P1-01](fixes/FIX-P1-01-worker-auth-default-spoofable-identity.md) | P1 | MCP auth | `EM_REQUIRE_WORKER_AUTH` unset in prod → body-supplied `executor_id` trusted across all soft-auth endpoints (full worker-tier bypass; cascades into IDOR, World-ID, mobile) | M |
| [FIX-P1-02](fixes/FIX-P1-02-evidence-presign-download-idor.md) | P1 | Evidence | `GET /presign-download` skips access-control entirely when `worker_auth is None` → arbitrary read of any worker's private evidence (photos / GPS / PII) (merges 2 reports) | S |
| [FIX-P1-03](fixes/FIX-P1-03-payments-events-unauth-enumeration.md) | P1 | workers.py | `GET /payments/events` leaks any wallet's full earnings history, bypassing `payment_events` RLS | S |
| [FIX-P1-04](fixes/FIX-P1-04-rls-executors-self-elevation.md) | P1 | Supabase RLS | `executors_update_own` + incomplete guard trigger lets a worker self-elevate World ID / VeryAI / KYC flags and edit `wallet_address` & `balance` | S |
| [FIX-P1-05](fixes/FIX-P1-05-rls-security-definer-rpc-anon.md) | P1 | Supabase RLS | `SECURITY DEFINER` money/state RPCs remain `anon`/PUBLIC-executable (migration 092 revocation incomplete) | M |
| [FIX-P1-06](fixes/FIX-P1-06-worldid-client-supplied-nullifier.md) | P1 | World ID | Uniqueness check + storage use the **client-supplied** nullifier, not the verified one from the proof → anti-sybil bypass | S |
| [FIX-P1-07](fixes/FIX-P1-07-worldid-verify-body-executor-id.md) | P1 | World ID | `/verify` binds verification to a body-supplied `executor_id` with no authenticated-identity check | S |
| [FIX-P1-08](fixes/FIX-P1-08-dispute-single-conflicted-arbiter.md) | P1 | Disputes | A single, conflicted arbiter can unilaterally redirect escrowed funds (no recusal, no assignment, no consensus) | M |
| [FIX-P2-01](fixes/FIX-P2-01-ci-terraform-secret-overscope.md) | P2 | Terraform IAM / CI | CI/Terraform deploy credential can read **every** `em/*` secret incl. the platform wallet private key (`secretsmanager:*`) | M |
| [FIX-P2-02](fixes/FIX-P2-02-xff-spoofing-ratelimit-bypass.md) | P2 | Rate-limit middleware | Leftmost `X-Forwarded-For` trust defeats all per-IP rate-limiting + auto-ban (and lets an attacker ban arbitrary IPs) | S |
| [FIX-P2-03](fixes/FIX-P2-03-deploy-prod-script-injection.md) | P2 | CI/CD | Script injection of untrusted release metadata into `run:` blocks in `deploy-prod.yml` (job holds AWS deploy creds) | S |

### Deduplication note
The PM merged these root-cause clusters (canonical first): `[P0-01 ⊇ P0-03]` (MCP transport), `[P1-02 ⊇ P1-09]` (evidence presign), and several lower-severity reports of the same soft-auth root cause (`P1-01` absorbs body-supplied-identity reports across World-ID binding and mobile). The 13 fix docs reflect the deduplicated set.

---

## P0 deep dive

### P0-01 — Unauthenticated MCP transport + self-asserted `agent_id`
The MCP app is mounted at `main.py:1206` (`app.mount("/mcp", mcp_http_app)`) with **no `dependencies=`**. A mounted Starlette sub-app does not inherit FastAPI dependencies, and the middleware stack is CORS + RequestTimeout + Prometheus only — **none authenticate**. Every `em_*` tool then reads the *caller's* identity from `params.agent_id` (the request body) rather than from a verified signature. The REST equivalents *do* enforce ERC-8128 (`verify_agent_auth_write`, `allow_anonymous=False`) and derive identity from the verified signature — so the MCP surface is an asymmetric bypass of the platform's entire auth model. The in-code comment at `server.py:1305-1306` claiming MCP flows through the same auth layer is **false**.

**Escrow-drain chain (confirmed end-to-end by the verifier):**
1. Victim publishes a task (default `lock_on_assignment` stores the victim's signed pre-auth).
2. Attacker registers an executor bound to *their own* wallet via the unauthenticated `POST /workers/register`.
3. Attacker calls `em_assign_task(agent_id=VICTIM, executor_id=attacker, skip_eligibility_check=true)` over open `/mcp/` → server relays the victim's stored pre-auth to the Facilitator with the **attacker's wallet as receiver**, locking escrow.
4. Attacker submits work, then calls `em_approve_submission(agent_id=VICTIM)` → escrow releases to the attacker.

Even without the full chain: unauthenticated force-approve (premature release), force-cancel/refund (griefing/DoS), and full worker-PII reads are all directly reachable. → **direct fund loss + full object-level authz bypass.** Fix: [FIX-P0-01](fixes/FIX-P0-01-unauthenticated-mcp-transport.md).

### P0-02 — Migration 097 re-grants `get_or_create_executor` to `anon`
Migration 097 silently re-granted `EXECUTE` on `get_or_create_executor` to the `anon` role, reversing the DB-001 hardening. Because the function rebinds an executor record to a supplied wallet/identity without proving wallet ownership, an anonymous caller can **rebind any victim's executor identity** to themselves — account takeover of any worker, including their balance/earnings linkage. Fix: [FIX-P0-02](fixes/FIX-P0-02-migration-097-anon-get-or-create-executor.md) (revocation migration + standalone prod hotfix SQL).

---

## PM-elevated fund-loss & infra risks (P2, **unverified** — confirm during execution)

These were rated P2/P3 by individual finders (so they were *not* sent through adversarial verification — only P0/P1 were), but the PM flagged them as credible fund-loss or high-blast-radius. **The execution team must confirm each before/while fixing.** Captured in the master plan Phase 4–5.

| # | Risk | Where |
|---|---|---|
| L-16 | `_resolve_settlement_address` silently falls back to the **cold treasury wallet** | `sdk_client.py:820-834` |
| L-17 | Non-direct settle path pays the worker the **full bounty** out of the platform wallet (guaranteed 13% loss/task) | `sdk_client.py` settle path |
| L-19 | Idempotency middleware does **not** prevent concurrent double-settlement (opt-in, non-concurrent) | `middleware.py` |
| L-20 | Release/refund state transitions are **non-atomic (TOCTOU)** | `_helpers.py`, dispatcher |
| L-22 | `EM_SERVER_SIGNING` gate not applied to the disbursement/settlement signers | `sdk_client.py` |
| L-25/26/27 | **Solana**: no payout-recipient validation, no fee reconciliation, refunds never claw back settled vouchers | dispatcher Solana path |
| L-78 | `em_withdraw_earnings` accepts arbitrary `executor_id` + destination (note: a *separate* withdraw-theft claim was refuted; this destination-control variant still needs confirmation) | server tools |
| L-82 | Advertised OWS spending-policy engine is **never enforced** — signing tools approve unbounded EIP-3009 USDC authorizations | `ows-mcp-server/` |
| L-36/37/41/45 | Unauthenticated read surface: full `audit-grid`, per-task `transactions`, leaderboard→wallet→human_id deanonymization, anon ERC-8004 identity endpoints | routers |
| L-48 | Migrations 105/106 reintroduced the **DB-004 anon-writable-verification** anti-pattern | `veryai_verifications`, `agent_kya_verifications` |
| L-57/58/75/77 | Verification Lambdas + shared ECS exec role read all `em/*` secrets; deploys use a single long-lived static AWS key (designed OIDC role never deployed); prod auto-deploys while approval gate is bypassed by mislabeling `main` as staging | terraform, workflows |
| L-59/76 | Secret-scan blind spot: gitleaks `docs/` allowlist + TruffleHog `--only-verified` miss exactly the file types of the two prior wallet-drain incidents | `.gitleaks.toml`, workflow |
| L-85/86/87 | Evidence S3 bucket has **no Public Access Block**, no upload size limit, and `presign-upload` trusts body-supplied `executor_id` | terraform/evidence, evidence router |
| L-53/69 | CSP ships `unsafe-inline`/`unsafe-eval`; admin paths exempt from WAF rules | `_headers`, waf.tf |
| L-71/72 | Mobile stores Supabase tokens in unencrypted AsyncStorage; bearer tokens in WebSocket URLs land in ALB access logs | em-mobile |

---

## Correctly refuted (false positives — no action)

The adversarial verifier killed two claimed-high findings, confirming a control already exists:

1. **"Agent-controlled escrow fee fields (`feeReceiver`/`minFeeBps`/`maxFeeBps`)"** — `validate_agent_preauth` (`payment_dispatcher.py`) already binds/validates these server-side; the agent cannot redirect the fee. *(One finder saw the client surface but missed the server validation.)*
2. **"`em_withdraw_earnings` lets any caller withdraw any executor's earnings to an attacker wallet"** — the repeatable-theft variant is blocked by an existing control. *(Note: a narrower destination-control variant, L-78, is still listed for confirmation — it is not the same as the refuted repeatable-drain claim.)*

These are documented so the execution team does **not** waste effort "fixing" non-bugs.

---

## Coverage (what was actually inspected)

26 specialist auditors, each reporting the files/resources they read. Domains covered: EIP-3009 replay/nonce/expiry/amount/recipient validation; settlement redirection & fee accounting; release/refund double-spend & idempotency; `EM_SERVER_SIGNING`/payment-mode gates; Solana direct-transfer path; worker-auth impersonation; task-lifecycle authz/IDOR; ERC-8128 wallet auth; anonymous read exposure; unauth PII enumeration; identity-binding abuse; Supabase RLS policies; `SECURITY DEFINER` RPCs; admin auth surface; Terraform IAM/secrets; network/WAF/rate-limit; secrets in code/logs; dependency supply chain; dashboard XSS; mobile app; CI/CD pipeline; MCP/A2A/webhook surface; World ID/arbiter/dispute; OWS wallet key handling; evidence presign/S3; Solidity contracts + blockchain scripts. Live AWS was inspected read-only (e.g. `em-production-mcp-server:535` task def confirmed `ERC8128_NONCE_STORE=dynamodb`, `EM_SERVER_SIGNING` unset, `EM_API_KEYS_ENABLED` unset, **`EM_REQUIRE_WORKER_AUTH` unset** — the root of P1-01).

### What was NOT fully covered (residual risk)
- **On-chain contract logic** was reviewed at source level only; no formal verification / fresh fuzzing run was executed in this pass.
- **PM-elevated P2s were not adversarially verified** (only P0/P1 were) — confirm during execution.
- Third-party services (Dynamic.xyz, Facilitator, World Cloud API, MoonPay) were treated as trusted boundaries; their own security was out of scope (the Facilitator gets its own handoff: [`HANDOFF_FACILITATOR_SECURITY_AUDIT.md`](HANDOFF_FACILITATOR_SECURITY_AUDIT.md)).

---

## Methodology note — why you can trust these findings more than a one-pass scan
Single-pass LLM audits hallucinate plausible-but-wrong bugs. Here, **no agent both discovered and confirmed its own finding**: each P0/P1 was handed to an independent verifier instructed to *refute* it and default to "not a bug" unless the exploit was confirmed end-to-end in the actual code. That pass killed 2 high claims and down-graded several others before they reached this report. The trade-off: P2/P3 findings did not get that treatment, so the "elevated P2" list carries more uncertainty and is explicitly flagged for execution-time confirmation.

---

## Deliverables produced by this audit
- **This report** — `SECURITY_AUDIT_RISK_REPORT.md`
- **13 fix docs** — `fixes/FIX-*.md`, one self-contained remediation spec per finding (root cause → exact code/SQL/Terraform fix → test plan → rollback → verification checklist)
- **Execution master plan** — [`MASTER_PLAN_EXECUTION.md`](MASTER_PLAN_EXECUTION.md), phased & granular for a systematic implementation team
- **Generic reusable audit handoff** — [`HANDOFF_GENERIC_SECURITY_AUDIT.md`](HANDOFF_GENERIC_SECURITY_AUDIT.md)
- **Facilitator-specific audit handoff** — [`HANDOFF_FACILITATOR_SECURITY_AUDIT.md`](HANDOFF_FACILITATOR_SECURITY_AUDIT.md)
- **DB hotfix scripts** — embedded in the relevant `FIX-P0-02` / `FIX-P1-04` / `FIX-P1-05` docs and collated in the final operator report.
