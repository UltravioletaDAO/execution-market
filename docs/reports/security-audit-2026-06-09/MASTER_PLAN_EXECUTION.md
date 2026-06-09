---
date: 2026-06-09
tags:
  - type/plan
  - domain/security
  - priority/p0
status: active
aliases:
  - Security Remediation Master Plan 2026-06-09
related-files:
  - docs/reports/security-audit-2026-06-09/SECURITY_AUDIT_RISK_REPORT.md
  - docs/reports/security-audit-2026-06-09/fixes/
---

# Master Plan — Security Remediation Execution

> **Audience:** the second multi-agent team (ruthless PM + Head of HR + executors + QA) that implements the audit. Each task is granular and independently verifiable. Work phases in order; within a phase, tasks may parallelize unless a dependency is noted.
>
> **Source of truth per task:** the `FIX-*` doc named in the task. The doc has the exact code/SQL/Terraform change, test plan, rollback, and verification checklist. **Do not re-investigate — implement the doc.**
>
> **Definition of done (every task):** (1) root-cause fix implemented (no quick fixes/hardcodes); (2) a test that *reproduces the vulnerability* added and passing; (3) relevant suite green locally; (4) specific files committed (never `git add -A`) referencing the finding ID; (5) pushed, **CI green**; (6) the vulnerability re-tested against the change; (7) checked off here.
>
> **Engineering rules in force:** never hardcode/print secrets; build real infra if a fix needs it; surgical changes only; secure-by-default. See `CLAUDE.md`.

---

## Phase 0 — Containment (P0, ship before anything else)

> These two are live, anonymous, fund-loss exploits. Highest urgency. Consider a temporary money-movement kill-switch (env flag gating `em_assign_task` / `em_approve_submission` / release) until 0.1 deploys.

- [ ] **0.1 — Authenticate the MCP transport & derive identity from the verified principal** → `FIX-P0-01`
  - 0.1.a Add ERC-8128 verification ASGI middleware wrapping the mounted `/mcp` app (`main.py:1206`); store verified principal in a contextvar. → verify: an unsigned `/mcp` tool call is rejected 401/403.
  - 0.1.b Every state/money tool reads identity from the verified principal, not `params.agent_id`; `agent_id` removed/advisory. Cover `core_tools`, `agent_tools`, worker tools, escrow tools, reputation tools. → verify: a tool call with a forged/mismatched `agent_id` is rejected based on authenticated identity.
  - 0.1.c Backward-compat: confirm how legitimate agents call `/mcp` today; roll out fail-safe (flag-gated if needed) so real agents are not locked out. → verify: golden flow / e2e passes against the change.
  - 0.1.d Tests: add cases asserting forged-`agent_id` rejection on assign/approve/cancel/submit/withdraw. → verify: tests reproduce the escrow-drain chain pre-fix, pass post-fix.
- [ ] **0.2 — Revoke anon EXECUTE on `get_or_create_executor` + block identity rebind** → `FIX-P0-02`
  - 0.2.a New migration: `REVOKE EXECUTE ... FROM anon, public`; re-grant only to the correct role. → verify: `anon` cannot call the RPC.
  - 0.2.b Function rejects rebinding an existing executor to a new wallet without ownership proof. → verify: anon rebind attempt fails.
  - 0.2.c Provide standalone idempotent prod-hotfix SQL for the operator. → verify: applied to prod DB (operator), `\df+` shows grants corrected.

## Phase 1 — Authentication hardening (P1)

- [ ] **1.1 — Make worker auth required by default; derive identity from verified signature** → `FIX-P1-01`
  - 1.1.a Flip `EM_REQUIRE_WORKER_AUTH` to secure default (true) in code + ECS task def/Terraform. → verify: soft-auth endpoint rejects body-only `executor_id`.
  - 1.1.b Audit every soft-auth call site; derive `executor_id` from authenticated principal. → verify: enumerated list, each uses verified identity.
- [ ] **1.2 — Deny-by-default on evidence presign-download (IDOR)** → `FIX-P1-02`
  - 1.2.a Require authenticated identity; verify caller owns/has rights to the evidence before issuing presigned URL (router + Lambda authorizer). → verify: unauth/foreign-worker request → 403; owner → 200.
- [ ] **1.3 — Lock down `GET /payments/events`** → `FIX-P1-03` → verify: unauth → 401; authed caller sees only own wallet history.
- [ ] **1.4 — World ID: use only the verified nullifier from the proof** → `FIX-P1-06` → verify: replaying a different body nullifier with a valid proof does not bypass uniqueness.
- [ ] **1.5 — World ID `/verify`: bind to authenticated principal** → `FIX-P1-07` → verify: body-supplied `executor_id` mismatch → rejected.

## Phase 2 — Database / RLS hardening (P1 + DB-004 regression)

- [ ] **2.1 — Extend immutable-field guard to balance + verification flags + wallet** → `FIX-P1-04`
  - New migration extending the migration-050 guard trigger. Forward migration + standalone prod hotfix SQL. → verify: worker UPDATE that flips KYC/World-ID/balance/wallet is rejected by trigger.
- [ ] **2.2 — Revoke anon/public EXECUTE on sensitive `SECURITY DEFINER` RPCs** → `FIX-P1-05`
  - Enumerate every SECURITY DEFINER func; revoke from anon/public; re-grant to authenticated/service. Forward migration + prod hotfix SQL. → verify: `anon` cannot call any money/state RPC.
- [ ] **2.3 — Close DB-004 anon-writable verification regression** (L-48: `veryai_verifications` mig 105, `agent_kya_verifications` mig 106) → new fix doc `FIX-P2-04` (executor authors). → verify: anon INSERT/UPDATE on those tables rejected by RLS.
- [ ] **2.4 — Lock down unauthenticated read surface** (L-36 `audit-grid`, L-37 `/tasks/{id}/transactions`, L-41 leaderboard deanonymization, L-45 anon ERC-8004 identity) → new fix doc `FIX-P2-05`. → verify: each endpoint requires auth or returns only non-sensitive fields.

## Phase 3 — Dispute / fund-release integrity (P1)

- [ ] **3.1 — Enforce arbiter recusal + assignment + consensus before fund redirection** → `FIX-P1-08`
  - Arbiter cannot be a party to the dispute; require proper assignment; require consensus/threshold before redirecting escrow. → verify: a conflicted/self-assigned arbiter cannot resolve; single-arbiter unilateral redirect blocked.

## Phase 4 — Payment fund-loss hardening (PM-elevated P2 — **confirm then fix**)

> Each task starts by confirming the bug in current code (these were not adversarially verified). If confirmed, fix; if not, document as non-issue.

- [ ] **4.1 — Settlement must never silently fall back to the treasury wallet** (L-16, `sdk_client.py:820-834`) → verify: misconfig → hard error, not treasury payout.
- [ ] **4.2 — Non-direct settle path must deduct fee, not pay full bounty from platform wallet** (L-17) → verify: worker receives bounty − 13%; platform wallet not drained.
- [ ] **4.3 — Make release/refund atomic + idempotent under concurrency** (L-19, L-20) → verify: concurrent double-approve/refund settles exactly once (test with parallel requests).
- [ ] **4.4 — Apply `EM_SERVER_SIGNING` gate to disbursement/settlement signers** (L-22) → verify: with server-signing off, no server-side signing occurs on the settle path.
- [ ] **4.5 — Solana: validate payout recipient, reconcile fee split, claw back on refund** (L-25/26/27) → verify: payout only to assigned worker; fee correct; refund reverses settled voucher.
- [ ] **4.6 — `em_withdraw_earnings`: bind to authenticated identity + validated destination** (L-78) → verify: cannot withdraw for a non-owned `executor_id` or to an unbound destination. (Note: repeatable-drain variant already refuted — scope to destination-control residual.)
- [ ] **4.7 — Enforce OWS spending-policy engine on signing tools** (L-82, `ows-mcp-server/`) → verify: an over-limit EIP-3009 authorization is rejected by policy.

## Phase 5 — Infrastructure / CI-CD hardening (P2)

- [ ] **5.1 — Scope secret read; isolate the wallet-key secret** → `FIX-P2-01` (also L-57 Lambda role, L-58 shared ECS exec role) → verify: deploy role + Lambda role cannot read the wallet-key secret.
- [ ] **5.2 — Correct client-IP extraction (rightmost trusted hop)** → `FIX-P2-02` → verify: spoofed `X-Forwarded-For` no longer bypasses rate-limit/auto-ban; cannot ban arbitrary IPs.
- [ ] **5.3 — Remove script injection in `deploy-prod.yml`** → `FIX-P2-03` → verify: untrusted release metadata passed via env, not interpolated into `run:`.
- [ ] **5.4 — Deploy the OIDC role; remove the long-lived static AWS key** (L-75) → new fix doc `FIX-P2-06`. → verify: deploys authenticate via OIDC; static key deleted/rotated.
- [ ] **5.5 — Restore the prod approval gate (stop mislabeling `main` as staging)** (L-77) → verify: prod deploy requires the approval environment.
- [ ] **5.6 — Close the secret-scan blind spot** (L-59 TruffleHog `--only-verified`, L-76 gitleaks `docs/` allowlist) → verify: a planted test secret in `docs/` and an unverified secret are both caught by CI.
- [ ] **5.7 — Evidence S3: add Public Access Block + upload size limit + presign-upload identity check** (L-85/86/87) → new fix doc `FIX-P2-07`. → verify: bucket has PAB; oversized PUT rejected; foreign `executor_id` rejected.

## Phase 6 — Frontend / mobile / defense-in-depth (P2/P3)

- [ ] **6.1 — Tighten CSP (remove `unsafe-inline`/`unsafe-eval` where feasible)** (L-53, `dashboard/public/_headers`) → verify: CSP report-only pass then enforce; app functions.
- [ ] **6.2 — Apply WAF rules to admin paths** (L-69, `waf.tf`) → verify: admin paths covered by rate/rule set.
- [ ] **6.3 — Mobile: encrypt token storage; stop putting bearer tokens in WS URLs** (L-71/72, `em-mobile/`) → verify: tokens in secure storage; WS auth via header/subprotocol, not URL.

---

## Cross-cutting QA gates (run after each phase)
- Backend: `cd mcp_server && pytest -m "core or payments or erc8004 or security"` green.
- Dashboard: `cd dashboard && npm run test && npm run lint` green.
- E2E money path: `python scripts/e2e_golden_flow.py` passes (proves auth fixes didn't break the legitimate flow).
- CI: all GitHub Actions green on the branch before merge.

## Operator hand-back (collated in the final report)
Standalone production SQL hotfix scripts the operator runs by hand (in order): `FIX-P0-02`, `FIX-P1-04`, `FIX-P1-05`, plus Phase-2.3/2.4 RLS scripts. Any AWS changes that must be applied outside Terraform CI are noted in the respective fix docs.
