---
date: 2026-06-09
tags:
  - type/report
  - domain/security
  - domain/operations
  - priority/p0
status: active
aliases:
  - Security Audit Final Operator Report 2026-06-09
related-files:
  - docs/reports/security-audit-2026-06-09/SECURITY_AUDIT_RISK_REPORT.md
  - docs/reports/security-audit-2026-06-09/MASTER_PLAN_EXECUTION.md
---

# Security Audit — Final Operator Report

> **What you asked for:** a ruthless multi-agent security audit of the whole platform (funds-at-risk focus), a risk document with a fix per finding, a granular master plan, a second team that *implements* the fixes through the full production cycle (commit → push → CI green → re-test), DB hotfix scripts you can run by hand, and two reusable audit handoffs (one generic, one customized for the Ultravioleta Facilitator). This report tells you exactly what was done, what shipped to production, and what still needs your hand.

---

## 1. TL;DR

- **Two teams ran as parallel multi-agent workflows.** Team 1 (audit): 26 specialist auditors + adversarial verification + a ruthless PM. Team 2 (execution): 7 file-disjoint work-streams + adversarial QA.
- **Findings: 2 P0, 9 P1, 3 P2 confirmed** (post adversarial verification), 76 lower catalogued, **2 high false-positives correctly refuted**.
- **What shipped to `main` (5 commits, pushed — CI running):** all audit docs, the DB lockdown migrations, the MCP-transport auth + worker/evidence/worldid/payment-events hardening, dispute recusal, and trusted client-IP extraction.
- **Closed on deploy (code):** evidence IDOR (P1-02), payment-events leak (P1-03), World ID bypasses (P1-06/07), dispute single-arbiter redirect (P1-08), XFF rate-limit bypass (P2-02).
- **Staged behind a flag (flip after you verify in staging):** the two highest-risk auth changes — MCP transport auth (P0-01) and worker-auth-required (P1-01). Shipped non-breaking by design.
- **Needs your hand (cannot auto-apply):** the **DB hotfix SQL** (closes P0-02 / P1-04 / P1-05 — account takeover + privilege escalation) and the **Terraform apply** (closes P2-01 IAM secret over-scope).
- **Held back (NOT shipped):** the payment fund-loss work-stream (introduced test regressions) and the frontend/mobile work-stream (broke mobile chat) — both blocked partway by a **monthly spend-limit cutoff** on the agent fleet. Details + how to finish in §6.

---

## 2. The two P0s (fix status)

| P0 | What | Shipped? | Production status |
|----|------|----------|-------------------|
| **P0-01** Unauthenticated `/mcp` transport + self-asserted `agent_id` → anonymous escrow drain | ERC-8128 ASGI auth middleware + tool identity from verified principal | **Code shipped, STAGED** | Present but **not enforcing** until `EM_MCP_AUTH_ENABLED=true`. **Action: §4.** |
| **P0-02** Migration 097 re-granted `get_or_create_executor` to `anon` → account takeover | Revoke + body-hardening migration **111** + idempotent hotfix SQL | **Code shipped; DB not yet applied** | **Still open in prod until you run the hotfix SQL — §3.** |

> Until P0-02's SQL is applied and P0-01's flag is flipped, both P0 exploit paths remain live. P0-02's SQL is safe to apply now (verified on real PG15, non-breaking). P0-01's flag flip requires the staging check in §4.

---

## 3. ⚠️ DB hotfix scripts to run by hand (do this first — closes 3 of the highest-severity findings)

Location: [`db-hotfix/`](db-hotfix/) — idempotent, safe to re-run, verified on PostgreSQL 15. **Apply in this order** in the Supabase SQL editor (service-role):

1. `hotfix-FIX-P0-02-get-or-create-executor.sql` — **P0** account takeover. Revokes anon EXECUTE + blocks cross-session identity rebind.
2. `hotfix-FIX-P1-05-lockdown-security-definer-rpcs.sql` — **P1** revokes anon/public EXECUTE on every money/state `SECURITY DEFINER` RPC (migration 092 had only done 15 of ~50).
3. `hotfix-FIX-P1-04-executor-immutable-guard.sql` — **P1** stops workers self-elevating World ID/KYC/balance/wallet.
4. `hotfix-FIX-P1-03-payment-events-revoke-anon.sql` — defense-in-depth for the payment-events leak.
5. `hotfix-FIX-P1-08-dispute-recusal-trigger.sql` — DB-level arbiter recusal guard.
6. `hotfix-DB-004-verification-tables-anon-write.sql` — closes the anon-writable verification regression.
7. `hotfix-Phase2.4-revoke-anon-orphaned-payments.sql` — locks the orphaned-payments view.

> **Expected non-breaking side effect (already designed for):** the dashboard's *direct browser* RPC call to `get_or_create_executor` will start returning 403. This is intended (same as migration 092's GR-1.7); `AuthContext.tsx` already treats it as non-fatal and legitimate onboarding goes through the backend `POST /workers/register` (service-role, unaffected). If you want zero dashboard 403 noise, route browser-side executor creation through the backend.

The same logic is also committed as forward migrations `supabase/migrations/111`–`117` (+ secondary-tree `20260609000001`) so a fresh `supabase db push` reaches the identical end-state. The standalone scripts are for your live DB **now**.

---

## 4. Flag cutovers (flip after a staging check) — closes the two P0/P1 auth findings

Both shipped **non-breaking** (default off) because I could not verify from here that every legitimate client authenticates correctly. To enforce:

### 4a. `EM_MCP_AUTH_ENABLED=true` (closes P0-01)
- **Before flipping:** confirm legitimate agents sign ERC-8128 on their `/mcp` calls. Check `dashboard/public/skill.md` + the client SDK. While the flag is `false`, the middleware **audit-logs** every unauthenticated `/mcp` call — review those logs to see who would break.
- **Flip in:** ECS task definition env for `em-production-mcp-server`.

### 4b. `EM_REQUIRE_WORKER_AUTH=true` (closes P1-01)
- **Before flipping:** verify the dashboard/worker clients send accepted auth on every worker endpoint (apply, submit, my-tasks, withdraw). The evidence-presign and World ID identity bindings already enforce regardless of this flag.
- **Flip in:** ECS task definition env.

> Recommended: flip both in a staging task def first, run `python scripts/e2e_golden_flow.py`, confirm green, then flip prod.

---

## 5. What shipped to production this run (commits on `main`)

| Commit | Work-stream | Closes |
|--------|-------------|--------|
| `df7e5cde` | Audit deliverables (docs) | — |
| `bcc177be` | DB RLS migrations + tests + CI guard | P0-02/P1-03/P1-04/P1-05/P1-08 (code; apply SQL per §3) |
| `5eafc1c2` | MCP transport auth + evidence/worldid/payment-events | P0-01*, P1-01*, **P1-02, P1-03, P1-06, P1-07** |
| `3172e36f` | Dispute recusal + client-IP | **P1-08, P2-02** |
| `d5d1ae08` | CI/Terraform/secret-scan/S3/WAF | P2-01†, P2-03, L-75/77/87† |

\* staged behind a flag (§4). † Terraform changes require `terraform apply` (not auto-applied by CI) — see §7.

**Enforcing on deploy (no further action):** P1-02 (evidence IDOR), P1-03 (payment-events), P1-06/07 (World ID), P1-08 (dispute app-side), P2-02 (XFF), P2-03 (CI script-injection).

---

## 6. Held back — needs the spend limit lifted to finish

The execution fleet hit a **monthly spend-limit cutoff** mid-run. Two work-streams were left in a state I judged unsafe to ship:

### 6a. WS-PAY — payment fund-loss hardening (Phase 4) — **HELD**
- Implemented in the working tree (`sdk_client.py`, `payment_dispatcher.py`, `ows-mcp-server/`) but **introduced ~8 new test failures** (Solana payshell + MPP e2e) and its adversarial QA never ran (spend cutoff). **Not committed.**
- These were *unverified* P2s (the PM elevated them; they were never adversarially confirmed). Shipping regressions to the live settlement path is unacceptable, so I held the whole stream.
- **To finish:** re-run Team-2 WS-PAY (it confirms each bug in current code first, then fixes), fix the regressions, QA, then commit. Spec is in `MASTER_PLAN_EXECUTION.md` Phase 4 + the elevated-risk table in the risk report.

### 6b. WS-FRONT — frontend/mobile hardening (Phase 6) — **HELD**
- CSP hashing + mobile secure-storage implemented, but the mobile WebSocket-auth change **breaks mobile chat**: the client moved the token to a subprotocol while the server (`mcp_server/chat/relay.py`) still reads `?token=`. QA verdict: CHANGES_REQUIRED. Plus 2 dashboard vitest failures. **Not committed.**
- **To finish:** add `Sec-WebSocket-Protocol` parsing to `relay.py` (accept `em-bearer` + `bearer.<jwt>`, echo the subprotocol back), keep `?token=` as a fallback during rollout, fix the 2 vitest failures, then commit.

> Everything needed to finish both is already written down (fix docs + master plan). A follow-up run with the spend limit raised can complete them systematically.

---

## 7. Infrastructure changes needing `terraform apply` (operator)

CI does **not** run `terraform apply`. Apply these from `infrastructure/terraform/` after review:
- **P2-01 / L-75:** `em-cicd-terraform-policy.json` (scoped secret read + explicit Deny on the wallet/auth secrets) and `github_oidc.tf` (OIDC deploy role). Then set the `AWS_DEPLOY_ROLE_ARN` repo variable to cut deploys over to OIDC and **retire the long-lived static AWS key**.
- **L-87:** `evidence.tf` — S3 Public Access Block + upload size limit.
- **L-69:** `waf.tf` — WAF rules extended to admin paths.
- **L-77:** deploy workflows now pin `environment: production`. **Add required reviewers** to that GitHub Environment to actually gate prod deploys (currently none configured — which is why the gate was a no-op).

---

## 8. The two audit handoffs (reusable)

- [`HANDOFF_GENERIC_SECURITY_AUDIT.md`](HANDOFF_GENERIC_SECURITY_AUDIT.md) — app-agnostic. Fill in one `APP CONTEXT` block and paste into any repo's Claude Code to reproduce this whole audit → fix-doc → master-plan pipeline. Includes a companion execution-team directive.
- [`HANDOFF_FACILITATOR_SECURITY_AUDIT.md`](HANDOFF_FACILITATOR_SECURITY_AUDIT.md) — **customized for the Ultravioleta Facilitator (x402-rs)** from a read-only inspection of its source: EOA hot-key lifecycle, `/settle` + escrow capture/release/refund authorization, nonce/idempotency replay defense, ERC-8004 reputation forgery, discovery-crawler/FHE-proxy SSRF, the Foundry contracts (+ echidna), its Terraform/Lambda infra, and `Cargo.lock` CVEs. Paste it into the facilitator's Claude Code and it self-audits. It has an `APP CONTEXT` block pre-filled but extendable, so you can reuse the generic shell across your other apps too.

---

## 9. Verification status & honesty notes

- **Local test runs are noisy here:** this WSL env has an `httpx`/`starlette` version skew (`TestClient(app=...)` removed), which fails ~17 security-header/exception tests **unrelated to any change** — `middleware.py` and those tests were untouched. CI has the pinned deps; **CI is the authoritative gate**, matching your "wait for actions green" requirement. The new security tests I could run pass (48/48 for the auth cluster; WS-NET 25/25; WS-DB 22/22 on real PG15; WS-DISPUTE 14/14).
- **Re-testing the vulnerabilities:** WS-DB proved its fix with a negative control (the behavioural suite *reproduces* the takeover on the pre-fix fixture, then passes post-migration). The auth/evidence/worldid fixes ship with reproducing tests. Full live re-test of P0-01 requires the flag flip (§4).
- **What was NOT covered:** on-chain contracts were source-reviewed only (no fresh fuzzing this pass); the PM-elevated P2 fund-loss items were not adversarially verified (flagged for confirmation during WS-PAY completion); third-party services (Dynamic, Facilitator, World, MoonPay) were trusted boundaries.

---

## 10. Your next actions, in order
1. **Run the 7 DB hotfix scripts** (§3) — closes P0-02, P1-04, P1-05, DB-004, +2. *(highest urgency, safe, ~5 min)*
2. **Review the `/mcp` audit logs**, then flip `EM_MCP_AUTH_ENABLED=true` (§4a) — closes P0-01.
3. **Verify worker auth in staging**, then flip `EM_REQUIRE_WORKER_AUTH=true` (§4b) — closes P1-01.
4. **`terraform apply`** the §7 changes; set `AWS_DEPLOY_ROLE_ARN`, retire the static AWS key; add prod-environment reviewers.
5. **When the spend limit is lifted:** finish WS-PAY and WS-FRONT (§6).
6. **Hand the facilitator handoff** to its Claude Code to self-audit (§8).
