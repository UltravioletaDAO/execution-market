# Backlog

Items captured during conversations to avoid context drift. Review at end of session or start of next one.

| Date | Item | Context | Priority | Status |
|------|------|---------|----------|--------|
| 2026-03-20 | OIDC migration for all deploy workflows | Task 3.1 del Post-Audit plan. Credenciales AWS estaticas en GitHub Secrets — seguras pero no ideales. Requiere crear IAM OIDC provider + trust policy. Aplica a deploy.yml, deploy-prod.yml, deploy-staging.yml. No urgente. | P2 | pending |
| 2026-03-26 | Human Verification Escalation | Phase 1 done: `escalation.py` creates disputes when AI score <50%. Phase 5 pending: arbiter notification + assignment + reputation staking. | P2 | partial |
| 2026-03-26 | Dogfooding: 2-human verification | `VerificationMode` enum ready (MANUAL/AUTO/ORACLE) but no `dual` mode. Needs dual-human task workflow (one executes, one verifies). | P2 | pending |
| 2026-03-26 | EM as meta-verifier (recursive dogfooding) | EM creates verification task ON EM itself. Pure concept — needs task dependency model + recursive creation API. | P2 | pending |
| 2026-03-28 | SubmissionForm tests completion (Post-Audit 4.3) | AuthContext + services tests DONE. 4 jsdom rendering tests still skipped (19% blocking). | P2 | partial |
| 2026-03-26 | H2H "Trustless Rappi" — human hires human | Formalize H2H pipeline. Study Rappi/Uber Eats/DoorDash ops model. **Create master plan** `MASTER_PLAN_H2H_TRUSTLESS_RAPPI.md` when ready. | P1 | pending |
| 2026-03-26 | Brand shortname brainstorm: eMarket / exMarket | Shorter name for social/verbal use. Candidates: `eMarket`, `exMarket`, `EM`, `eM`. Decision pending. | P2 | pending |
| 2026-03-31 | INC-2026-03-30 remediation: fund remaining chains | Wallet rotated + ECS deployed (done). 3/8 chains funded (Base, Polygon, Avalanche). Remaining: Ethereum, Arbitrum, Celo, Monad, verify Optimism. Scripts at `scripts/bridge/`. | P1 | in-progress |
| 2026-04-12 | Ring 2: add CLAWROUTER_WALLET_KEY to ECS | OPENROUTER_API_KEY already set. CLAWROUTER_WALLET_KEY missing from ECS task def — Ring 2 ClawRouter provider unavailable. Add to Secrets Manager + Terraform ecs.tf. | P1 | pending |
| 2026-04-12 | Worktree: Plugin SDK | Branch `feat/plugin-sdk` (2 commits, not in main). Sync client, idempotency, logging, README. Related to MASTER_PLAN_EM_PLUGIN_SDK. | P2 | pending |
| 2026-04-12 | Test suite audit: fix 27 failing + dead code cleanup | 27 tests failing pre-existentes: (1) `_run_gps_check` async llamado sync en `TestGPSRadiusFromTask` + `TestGPSCheck`, (2) `test_roundtrip` Windows `pathlib.rename` bug, (3) `test_verify_pass_path` assumes `cheap` tier sin API keys. Además: limpiar tests de código muerto post-Phase 5 (asyncio verification removido, `phase_b_recovery` eliminado, `background_runner` reducido). Posible reducción de 14min CI. | P1 | pending |
| 2026-04-17 | WebMCP browser-tool exposure | `navigator.modelContext.provideContext()` to expose EM tools to browser-side agents (Chrome Canary flag today). Spec still draft (webmachinelearning.github.io/webmcp). Costs: client-side MCP re-implementation, in-browser wallet signing (ERC-8128), CSP widening for `worker-src` / `wasm-eval`. Value: an agent running in the user's browser could publish/approve tasks without hitting the API. Deferred until (a) spec leaves draft, (b) we have a concrete consumer asking for it, or (c) Chrome ships WebMCP stable. Source: isitagentready.com scan 2026-04-17 (AR-09). From `MASTER_PLAN_AGENT_READINESS.md` Task 3.2. | P3 | pending |
| 2026-04-17 | Per-page Markdown snapshots at build time | Today `Accept: text/markdown` falls back to `skill.md` for every SPA route. Could render dedicated `.md` per route via Vite plugin (e.g. `/about.md`, `/developers.md`, `/disputes.md`). Lower priority than scanner impact — revisit if agents start checking per-page content depth. Source: `MARKDOWN_NEGOTIATION.md` ADR "alternatives considered" §2. | P3 | pending |
| 2026-04-20 | CSP blocks `dynamic-static-assets.com/wallet-book/` | Console muestra varios `Refused to connect` a `https://dynamic-static-assets.com/wallet-book/v1/stable/wallet-book.json`. Es `connect-src` faltante en CSP (el modal de Dynamic lo necesita para listar wallets). Agregar `https://dynamic-static-assets.com` a `connect-src`. Reportado junto al fix XMTP signer. | P2 | pending |
| 2026-04-20 | RLS: `permission denied for function link_wallet_to_session` (42501) | Auth flow falla al llamar `link_wallet_to_session()` (Postgres code 42501). Falta `GRANT EXECUTE` a rol `anon`/`authenticated` o RLS policy. Ocurre post-login de Dynamic. Reportado junto al fix XMTP signer. | P1 | pending |
| 2026-04-20 | XMTP v5 conversation API migration | El fix del signer destapa la siguiente capa: `useConversations.ts` y `useMessages.ts` usan API vieja (`peerAddress`, `newConversation`, `senderAddress`, `conversations.list()` retorna DMs v2). XMTP v5 usa MLS — `peerInboxId`, `newDm(inboxId)`, `senderInboxId`. Validar y migrar cuando se pruebe Connect XMTP end-to-end. | P1 | pending |

---

## Completed (2026-04-12 audit)

Items verified as implemented by codebase audit. Removed from active backlog.

| Date | Item | Resolution |
|------|------|------------|
| 2026-04-03 | Terraform deploy pipeline broken (P0) | Fixed in commit `bf9932b8` — terraform plan runs on every deploy now |
| 2026-04-03 | WorldCoin bug fix not deployed (P1) | Deployed 2026-04-10 — commit `9cd619dd` (CRY-002, CRY-007, CRY-010) |
| 2026-04-03 | Evidence visibility not deployed (P1) | Live — AIAnalysisDetails + SubmissionReviewModal + Phase B polling |
| 2026-04-12 | Deploy version endpoint (P0) | Implemented — `/health/version` returns git SHA + build timestamp |
| 2026-04-11 | Cancel API for expired tasks with escrow (P1) | Implemented — expired status handled with escrow refund logic |
| 2026-04-26 | Agent ping on evidence submission (P1) | Implemented — webhook + WebSocket + event adapters + MeshRelay |
| 2026-04-12 | Forensic verification UI overhaul (P1) | Implemented — ForensicEventLog component with Ring 1+2 step-by-step timeline |
| 2026-04-12 | S3 evidence bucket standalone (P1) | Done — evidence.tf with CDN, security, IAM |
| 2026-03-28 | Reduce `as any` casts (P2) | Done — 3 remaining (1 Leaflet, 2 test fixtures). Target was 12. |
| 2026-03-22 | Balance check bug in skill.md (P2) | Resolved — advisory no longer present in skill.md |
| 2026-03-22 | Ultra Wallet / uvw CLI (P1) | **Superseded** by OWS MCP Server (`ows-mcp-server/`) — 9 tools, multi-chain, production |
| 2026-04-11 | Task dedup: X-Idempotency header (P1) | Server (`7108339b`) + Python/TS SDKs (`2568f4f7`). Full E2E dedup on task creation. |
| 2026-04-18 | Terraform Apply IAM permissions: CloudTrail + GuardDuty (P1) | `em-cicd-terraform` v12 — tight-scoped: `TerraformCloudTrail` (ARN `arn:aws:cloudtrail:*:518898403364:trail/em-*`, enumerated CRUD+tagging actions), `TerraformGuardDuty` (Resource `*`, enumerated detector CRUD+tagging), `TerraformCloudTrailList` (`DescribeTrails`/`ListTrails`/`LookupEvents`, no resource-level auth possible). Verified: Terraform Apply green on run `24616096176`, CloudTrail `em-production-cloudtrail` logging multi-region, GuardDuty detector ENABLED. Runbook: `vault/05-infrastructure/ci-deployer-iam-policy.md`. |

---

## HANDOFF: INC-2026-03-30 — Wallet Rotation & Fund Distribution

**Incident**: Private key for worker wallet `0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15` leaked in `xmtp-bot/check_sub.mjs` (commit `f140f99e`, pushed to public main). Wallet drained ~$17 USDC across 8 chains by automated GitHub secret scanner bot (`0x9098...3333`).

**Done (2026-03-31 + 2026-04-01):**
- [x] Root cause identified: hardcoded key in `check_sub.mjs` by Clawd Bot (OpenClaw)
- [x] File removed from git tracking (`git rm --cached`)
- [x] `git-filter-repo --replace-text` executed — key replaced in all history
- [x] `git push origin main --force` — cleaned history published to GitHub
- [x] Pre-commit hook added: scans staged files for `0x` + 64 hex chars
- [x] New wallet generated: `0x4aa8bE0422e042e5E8A37b0F8E956117F12740B0`
- [x] AWS SM + `.env.local` + ECS task def updated
- [x] E2E script docstrings updated

**Funding status (2026-04-01):**

| Chain | USDC | Status |
|-------|------|--------|
| Base | $15.93 | Funded |
| Polygon | $2.498 | Funded |
| Avalanche | $2.498 | Funded |
| Optimism | ~$2.498 | Bridge sent, verify arrival |
| Ethereum | $0 | **PENDING** |
| Arbitrum | $0 | **PENDING** |
| Celo | $0 | **PENDING** (no deBridge support) |
| Monad | $0 | **PENDING** (no deBridge support) |

**Remaining:**
- Verify Optimism bridge arrived
- Fund Ethereum + Arbitrum (deBridge UI or pre-approve max)
- Fund Celo + Monad (Squid Router)
- Revoke old wallet approvals: `revoke.cash/address/0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15`
- Run Golden Flow: `python scripts/e2e_golden_flow.py`
