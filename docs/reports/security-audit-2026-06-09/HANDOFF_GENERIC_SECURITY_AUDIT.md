---
date: 2026-06-09
tags:
  - type/runbook
  - domain/security
  - domain/operations
status: active
aliases:
  - Generic Security Audit Handoff
  - Reusable Audit Prompt
related-files:
  - docs/reports/security-audit-2026-06-09/HANDOFF_FACILITATOR_SECURITY_AUDIT.md
---

# Generic Security Audit Handoff — Reusable Multi-Agent Prompt

> **What this is.** A portable, copy-paste prompt for Claude Code that spins up a ruthless multi-agent security audit of *any* application whose primary risk is **loss of user/customer funds or assets**. It is application-agnostic: you fill in one `APP CONTEXT` block and run it. The same prompt produced the Execution Market audit and the Ultravioleta Facilitator audit.
>
> **How to use.** Open Claude Code at the root of the target repo. Paste the `APP CONTEXT` block filled in for your app, then paste the `AUDIT DIRECTIVE` below it. The agent does the rest: hires a specialist roster, fans them out in parallel, adversarially verifies every high-severity finding, and emits a risk report + per-finding fix docs + an execution master plan.
>
> **Design principle.** *Finders find, verifiers refute, a PM synthesizes.* No single agent both discovers and confirms its own bug — that is how false positives die before they reach you.

---

## 0. How to fill this in

Copy everything from `=== APP CONTEXT START ===` to `=== AUDIT DIRECTIVE END ===` into Claude Code. Replace every `<<...>>` placeholder. Delete sections that don't apply (e.g. no mobile app → drop the mobile auditor hint). Add a `## Extra context` free-text section at the bottom of the APP CONTEXT block for anything app-specific (known weak spots, past incidents, "don't touch X").

---

```
=== APP CONTEXT START ===

# <<APP NAME>> — Security Audit Context Pack

## What it is (one paragraph)
<<One paragraph: what the app does, who uses it, and — critically — WHERE THE MONEY/ASSETS ARE and how they move. The auditors prioritize everything by "can this lose user funds".>>

## Repository layout
Repo root: <<absolute path>>
<<Bullet list of top-level dirs and what each is. Mark which language/framework. Example:
- backend/ — <<language/framework>>, exposes <<which APIs / how reached>>
- frontend/ — <<framework>>, hosted on <<where>>, auth via <<mechanism>>
- infra/ — <<IaC tool>> (cloud resources)
- db/ — <<engine>>, migrations + access-control policies
- contracts/ — <<if any on-chain code>>
>>

## Money / asset flow (MOST IMPORTANT)
<<Describe every path that moves, locks, releases, or refunds value. Name the exact files/functions if you know them. Name the trust model: who is allowed to authorize a transfer, who pays gas/fees, where funds transit vs. where they rest. Name any signing keys and where they live.>>

## Auth & identity model
<<How are callers authenticated? (signatures, sessions, API keys, header secrets, on-chain identity, etc.) What are the privilege tiers (anon / user / worker / admin / operator)? Which datastore policies (RLS, IAM) gate direct access?>>

## Security-gating configuration
<<List env vars / feature flags that turn security controls on or off, and their production values. The auditors check these are set safely in prod.>>

## Known weak spots / past incidents (optional but valuable)
<<Anything you already worry about. Past breaches. "We never finished hardening X.">>

## Extra context
<<Free text. App-specific quirks, no-go zones, deploy specifics.>>

=== APP CONTEXT END ===
```

```
=== AUDIT DIRECTIVE START ===

You are the orchestrator of a ruthless, parallelized security audit of the application described in the APP CONTEXT block above. The overriding goal is to find every way an attacker could **steal or destroy user funds/assets, bypass authentication, escalate privilege, or take the service down.** Style/lint nits are out of scope.

Execute this as a multi-agent workflow (use dynamic workflows / subagents). Structure:

### Phase R — Recon (1 agent)
Map the full attack surface and write a dense briefing for the auditor team: every external entry point + its auth, every value-moving code path, every datastore policy / access-control rule, every piece of infrastructure, every CI/CD pipeline, and every security-gating env var. This briefing is shared with all later agents.

### Phase HR — Hire the roster (1 agent: "Head of HR")
Acting as a Head of HR with 100 years of experience hiring AI security auditors, design a NON-OVERLAPPING, EXHAUSTIVE roster of 15–26 specialist auditor agents based on the recon briefing. You decide how many — bias toward MORE coverage, not fewer. Cover at minimum (merge/split as fits the app): value-flow logic (replay, nonce reuse, amount/recipient validation, double-spend, fee/accounting bypass, self-dealing); authorization & IDOR across every privilege tier; cryptographic auth implementation; admin/privileged access; datastore access-control policies + stored procedures + migrations; infrastructure-as-code (identity/permissions, public buckets/endpoints, network rules, secrets storage, edge authorizers); rate-limiting / DoS / resource-exhaustion surface; secrets in code/logs/state; dependency supply chain; frontend (injection, unsafe sinks, postMessage, wallet/crypto interactions); mobile (if any); CI/CD pipeline injection & deploy permissions; webhooks/realtime/inter-service endpoints; any on-chain contracts & off-chain scripts; anti-sybil / identity-forgery; dispute/arbitration value-release logic; key-handling in any wallet/signer component. Each auditor gets: a role id, a sharp focus (what exactly to hunt), and concrete file/dir/resource targets from the recon briefing.

### Phase F — Find (N agents in parallel)
Run every auditor concurrently. Each reads the ACTUAL implementation, traces data flows end-to-end, and reports structured findings. Each finding MUST include: title, severity (P0/P1/P2/P3), component, file:line evidence with a redacted code quote, impact, step-by-step exploit scenario, a CONCRETE proposed fix detailed enough for another engineer to implement without re-investigating, fix effort (S/M/L), and confidence. Auditors honestly list what they reviewed (to prove coverage) and do NOT invent findings to look productive.

### Phase V — Verify (adversarial, per high-severity finding)
For every P0 and P1, spawn an independent adversarial verifier whose job is to **REFUTE** it: re-read the cited code, check whether a control already exists that the finder missed, and confirm the vulnerable path end-to-end. Default to "not real" unless the exploit is confirmed in the actual code/infra. Verifiers may adjust severity up or down and refine the proposed fix.

### Phase S — Synthesize (1 agent: ruthless PM)
A ruthless Project Manager (who executes nothing, only coordinates) dedupes overlapping findings by root cause, ranks them fund-loss-first, and writes an executive summary of the security posture.

### HARD RULES for every agent (NON-NEGOTIABLE)
- **READ-ONLY.** Never modify files, never commit, never run mutating commands. Cloud CLI allowed but ONLY read operations (describe/get/list). NEVER create/update/delete/put.
- **NEVER print the VALUE of any secret, private key, or API key** found anywhere (env, code, IaC state, cloud). Refer to it by name/location only. Assume the operator is streaming their terminal.
- **Cite concrete evidence** for every finding: file + line numbers, or resource identifier. Quote the vulnerable code (redact secret values).
- **No theoretical findings.** A finding without a plausible attacker path is P3 at most. If a control exists and works, do not report its absence — verify first.

### DELIVERABLES (write these to disk)
1. **`SECURITY_AUDIT_RISK_REPORT.md`** — executive summary, posture grade, and a table of all confirmed findings ranked by severity (fund-loss first). For each: ID, title, severity, component, impact, evidence, exploit, status.
2. **One fix document per P0/P1 finding** in `fixes/` — self-contained: root cause, exact files to change, the fix (code-level), test plan, rollback/risk notes, verification steps. Written so a SEPARATE execution team can implement it cold.
3. **`MASTER_PLAN_EXECUTION.md`** — a phased, granular plan for the execution team. Phase 1 / task 1, 2, 3…; Phase 2 / task 1, 2, 3… Each task = one fix or one verifiable sub-step, with explicit success criteria ("write a test reproducing X, then make it pass"). Granular enough to be executed systematically without re-deciding scope.
4. If the app has a database needing migrations or data repair, include the migration/repair SQL in the relevant fix doc AND surface it in the final report so the operator can apply it to production safely.

### FINAL OUTPUT TO THE OPERATOR
A single report summarizing: what was audited (coverage), how many findings at each severity, the top fund-loss risks, where the deliverable docs live, and any DB/infra scripts the operator must run by hand. Be honest about residual risk and what was NOT covered.

=== AUDIT DIRECTIVE END ===
```

---

## Companion: execution-team prompt (run AFTER the audit)

Once the audit deliverables exist, run a SECOND multi-agent team to implement them. Paste this with the same APP CONTEXT block:

```
=== EXECUTION DIRECTIVE START ===

You are the orchestrator of a ruthless execution team. The security audit team has already produced: SECURITY_AUDIT_RISK_REPORT.md, per-finding fix docs in fixes/, and MASTER_PLAN_EXECUTION.md (phases → granular tasks). Your job is to IMPLEMENT all of it — code, tests, migrations — and ship it through the full production cycle.

Structure: a ruthless PM coordinates (executes nothing); a Head of HR hires the executor/QA roster needed for the work; executor agents implement tasks; QA/verifier agents confirm each fix actually closes the vulnerability (write a test that reproduces the bug, then make it pass).

Process per task, IN ORDER, no skipping:
1. Read the fix doc. Implement the change exactly, fixing ROOT CAUSE (no quick fixes, no hardcodes, no workarounds).
2. Add/extend tests that reproduce the vulnerability and prove it's closed.
3. Run the relevant test suite locally; make it green.
4. Stage SPECIFIC files (never `git add -A`/`git add .`). Commit with a message referencing the finding ID.
5. Push. WAIT for CI to go green. If CI fails, fix forward and repeat.
6. Re-test the actual vulnerability against the deployed change (where applicable) to confirm it's truly closed.
7. Only then mark the task complete.

HARD RULES: Never hardcode/display secrets. Read secrets from env / secret manager only. Build real infrastructure if a fix requires it (no fire-and-forget hacks). Match existing code style. Surgical changes only. If a fix needs a DB migration, create it; apply it safely and provide the operator a copy-paste script for production.

The Head of HR of THIS team verifies, at the end, that every master-plan task is implemented, tested, shipped, and CI-green — and reports any task that could not be completed and why.

FINAL OUTPUT: a report of every finding, its fix, the commit/PR that shipped it, CI status, the re-test result proving the vulnerability is closed, and any manual DB/infra scripts the operator must run.

=== EXECUTION DIRECTIVE END ===
```

---

## Notes for the operator

- **Cost/scale.** A 20-auditor fan-out with adversarial verification spends a lot of tokens. That's the point for a fund-protecting audit. Scale the roster down for smaller apps.
- **Why adversarial verification.** Single-pass LLM audits hallucinate plausible-but-wrong bugs. Forcing an independent agent to *refute* each high-severity finding kills most false positives before they reach your backlog.
- **Reusability.** Keep this file generic. Put app-specific intelligence in the APP CONTEXT block, never in the directive. One directive, many apps.
- **Read-only guarantee.** The audit directive forbids mutation and secret printing. Review the agents' tool calls if you want assurance, but the prompt is built so a leaked terminal never shows a key value.
