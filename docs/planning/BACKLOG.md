# Backlog

Items captured during conversations to avoid context drift. Review at end of session or start of next one.

| Date | Item | Context | Priority | Status |
|------|------|---------|----------|--------|
| 2026-03-20 | OIDC migration for deploy-prod.yml / deploy-staging.yml | Task 3.1 del Post-Audit plan. Credenciales AWS estaticas en GitHub Secrets — seguras pero no ideales. Requiere crear IAM OIDC provider + trust policy. No urgente. | P2 | pending |
| 2026-03-22 | Ultra Wallet (P1) — next priority | CLI MVP `uvw` with generate/import-env/status/register/sign-request. See MASTER_PLAN_UV_WALLET_REPO.md. Unblocks P3, P4, P7. | P1 | pending |
| 2026-03-22 | Balance check bug in skill.md | Advisory balanceOf() check in skill.md may show stale balance — verify fix is in place or flag for next session. | P2 | pending |
| 2026-03-26 | Human Verification Escalation | When AI can't verify evidence (score <50%), allow escalation to a human verifier. The verifier is a second independent human (not the original worker) who reviews the evidence and stakes their reputation on the verdict. Creates a trust flywheel. | P2 | pending |
| 2026-03-26 | Dogfooding: 2-human verification | For high-value tasks, hire 2 humans: one executes, one verifies. The verifier reviews photos/evidence and puts reputation on the line confirming authenticity. Could be an optional task parameter `verification_mode: "ai" | "human" | "dual"`. | P2 | pending |
| 2026-03-26 | Agent ping on evidence submission | Notify the hiring agent (via MCP callback, webhook, or Telegram) when a worker submits evidence, so they can approve faster instead of polling. Related to WS/realtime work. | P1 | pending |
| 2026-03-26 | EM as meta-verifier (recursive dogfooding) | EM could create a verification task ON EM itself — "verify this evidence is real" as a separate bounty. The original task's approval waits for the verification task's completion. Recursive trust. | P2 | pending |
| 2026-03-28 | OIDC migration for deploy.yml (Post-Audit 3.1) | Replace static IAM creds with OIDC in deploy.yml. deploy-prod.yml already uses OIDC. Needs IAM trust policy update. | P2 | pending |
| 2026-03-28 | SubmissionForm tests completion (Post-Audit 4.3) | Add AuthContext + services tests. Mock paths fixed, 4 tests still skipped (jsdom render issue). | P2 | pending |
| 2026-03-28 | Reduce `as any` casts (Post-Audit 5.4) | 12 remaining from 26. Remove react-query dep if unused. | P2 | pending |
| 2026-03-26 | H2H "Trustless Rappi" — human hires human | Formalize H2H (human-to-human) pipeline. Study Rappi's operational model (delivery logistics, real-time tracking, rating system, dispute resolution, courier assignment) and adapt for trustless execution. EM already supports H2H tasks but needs: (1) research Rappi/Uber Eats/DoorDash ops model, (2) identify gaps in EM's H2H flow, (3) design trustless equivalents for each Rappi feature (GPS tracking → on-chain proof, dispatch → open marketplace, payment → x402r escrow). **Create a separate master plan** `MASTER_PLAN_H2H_TRUSTLESS_RAPPI.md` when ready to tackle. | P1 | pending |
| 2026-03-26 | Brand shortname brainstorm: eMarket / exMarket | Shorter name for social/verbal use. Candidates: `eMarket`, `exMarket`, `EM`, `eM`. Decision pending — see conversation 2026-03-26. | P2 | pending |
| 2026-03-31 | INC-2026-03-30 remediation: rotate wallet + fund new wallet | **MOSTLY DONE** — See status below. Wallet rotated, ECS deployed, 3/8 chains funded, 5 pending. | P0 | in-progress |
| 2026-04-01 | Fund remaining 5 chains for worker wallet | Bridge USDC from Base to: Ethereum, Arbitrum, Celo, Monad, (verify Optimism arrived). deBridge programmatic bridge has allowance bug on ETH L1 — use app.debridge.finance UI instead. Scripts at `scripts/bridge/`. See handoff below. | P1 | pending |
| 2026-04-03 | WorldCoin bug fix not deployed | User reports WorldCoin-related fix not visible in production. Blocked by Terraform deploy failure. Verify which commit has the fix and ensure it deploys. | P1 | pending |
| 2026-04-03 | Terraform deploy pipeline broken | `Cannot apply incomplete plan` error in CI/CD Deploy job. Blocks ALL deploys to production. Commit `88e8cccb` (ECS task def changes) may be the trigger. Pre-existed before rating fix. Needs diagnosis. | P0 | pending |
| 2026-04-03 | Evidence visibility not deployed | Commit `65cea1ed` surfaces PHOTINT AI analysis in submission views but hasn't reached production due to Terraform failure. | P1 | pending |
| 2026-04-12 | Deploy version endpoint + sync check | Add /version endpoint to MCP API + frontend that returns git SHA + build timestamp. CI verifies all components match after deploy. Adopt Facilitator's version verification pattern. Prevents testing against stale containers. | P0 | pending |
| 2026-04-12 | S3 evidence bucket: standalone management | Evidence bucket managed by Supabase, not Terraform. Removed from TF state (was blocking every apply). Keep evidence.tf for CloudFront/Lambda presign only, not the bucket itself. | P1 | done |
| 2026-04-12 | Ring 2 providers missing in ECS | `CLAWROUTER_WALLET_KEY` and `OPENROUTER_API_KEY` not set in ECS task def. Ring 2 degrades to CHEAP (no LLM) for all tasks. Need to add these secrets to Secrets Manager + Terraform ecs.tf. | P0 | pending |
| 2026-04-12 | Forensic verification UI overhaul | Ring 1/Ring 2 need step-by-step event log in dashboard (EXIF extraction → GPS → tampering → AI analysis with provider attempts → Ring 2 tier routing → LLM verdict). Currently only shows summary badges. Needs event-driven architecture in backend + detailed checklist UI in frontend. | P1 | pending |
| 2026-04-11 | Task dedup: rate limit retry creates duplicate tasks | If ERC-8128 nonce endpoint rate-limits (429), client retries and creates a second identical task. Need idempotency key (client-generated UUID in header) so server rejects duplicate creates within a window. Also: nonce rate limit is too aggressive for E2E flows. | P1 | pending |
| 2026-04-11 | Cancel API should handle expired tasks with escrow | `POST /tasks/{id}/cancel` returns 409 for expired status. If escrow was locked and task expired without submission, agent's funds are stuck. API should either: (1) accept cancel for expired+escrow tasks and trigger refund, or (2) expose `POST /tasks/{id}/refund` endpoint. Currently agents must call `refund_via_facilitator()` directly with saved PaymentInfo. Discovered during E2E testing — documented workaround in skill.md v9.1.0. | P1 | pending |

---

## HANDOFF: INC-2026-03-30 — Wallet Rotation & Fund Distribution (P0)

**Incident**: Private key for worker wallet `0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15` leaked in `xmtp-bot/check_sub.mjs` (commit `f140f99e`, pushed to public main). Wallet drained ~$17 USDC across 8 chains by automated GitHub secret scanner bot (`0x9098...3333`).

**Done (2026-03-31 + 2026-04-01):**
- [x] Root cause identified: hardcoded key in `check_sub.mjs` by Clawd Bot (OpenClaw)
- [x] File removed from git tracking (`git rm --cached`)
- [x] `git-filter-repo --replace-text` executed — key replaced with `PRIVATE_KEY_REMOVED_INC_2026_03_30` in all history
- [x] `git push origin main --force` — cleaned history published to GitHub
- [x] Remote re-added + branch tracking restored (`origin/main`)
- [x] Pre-commit hook added: scans staged files for `0x` + 64 hex chars, blocks commit
- [x] CLAUDE.md + global CLAUDE.md updated with zero-tolerance rules
- [x] .gitignore updated with throwaway script patterns
- [x] Memory saved: `inc-2026-03-30-key-leak.md`
- [x] New wallet generated: `0x4aa8bE0422e042e5E8A37b0F8E956117F12740B0`
- [x] AWS SM `em/test-worker` updated with new key (verified: `0x...77b9`, 66 chars)
- [x] `.env.local` updated with new `EM_WORKER_PRIVATE_KEY`
- [x] ECS task def rev 397: `EM_WORKER_PRIVATE_KEY` added (from `em/test-worker:private_key`)
- [x] ECS force deploy done — MCP server healthy on rev 397
- [x] E2E script docstrings updated (4 files: golden_flow, multichain, rejection, refund)
- [x] `WALLET-BUG-ANALYSIS.md` updated with rotation note
- [x] Post-mortem for OpenClaw: `docs/reports/INC-2026-03-30-POSTMORTEM-OPENCLAW.md`
- [x] Bridge scripts copied from KK repo to `scripts/bridge/` (local copy, independent)
- [x] Bridge fix: 15% buffer + allowance check before approve

**Funding status (2026-04-01):**

| Chain | USDC | Status | deBridge Order |
|-------|------|--------|----------------|
| Base | $15.93 | Funded (+ 0.011 ETH gas) | — |
| Polygon | $2.498 | Funded | `0xa424eb10...` |
| Avalanche | $2.498 | Funded | `0x7325b0ab...` |
| Optimism | ~$2.498 | Bridge sent, verify arrival | `0x1be4ce35...` |
| Ethereum | $0 | **PENDING** | — |
| Arbitrum | $0 | **PENDING** | — |
| Celo | $0 | **PENDING** (no deBridge support) | — |
| Monad | $0 | **PENDING** (no deBridge support) | — |

**Remaining (P1):**

### Fund remaining chains

**Bridge scripts** (local copy from KK repo):
- `scripts/bridge/bridge-from-source.ts` — deBridge DLN (Base/ETH/Polygon/Arbitrum/Avalanche/Optimism)
- `scripts/bridge/lib/squid-client.ts` — Squid Router (Celo fallback)
- `scripts/bridge/lib/bridge-router.ts` — auto-selects deBridge vs Squid
- Source KK repo: `Z:\ultravioleta\dao\karmakadabra\scripts\em-integration\`

**Pattern to run** (loads key from AWS SM):
```bash
cd scripts
node -e "
const { execSync } = require('child_process');
const raw = execSync('aws secretsmanager get-secret-value --secret-id em/test-worker --query SecretString --output text --region us-east-2', {encoding:'utf8'});
const pk = JSON.parse(raw).private_key;
execSync('npx tsx bridge/bridge-from-source.ts --source base --chains ethereum,arbitrum --amount 2.50 --dry-run', {
  stdio: 'inherit',
  env: { ...process.env, WALLET_PRIVATE_KEY: pk, PRIVATE_KEY: pk }
});
"
```

**Known issues:**
- deBridge Ethereum L1: "transfer amount exceeds allowance" — the script's 15% approve buffer isn't enough for ETH L1 operating expenses. Workaround: pre-approve max USDC via separate TX, or use deBridge UI (app.debridge.finance)
- Celo/Monad: not supported by deBridge from Base. Use Squid Router (needs `SQUID_INTEGRATOR_ID` env var) or the KK scripts which have Squid integration
- Nonce stuck: if a bridge TX fails, subsequent TXs may time out. Wait ~60s and retry

**Chains still needed:**
1. **Verify Optimism** — bridge TX sent (`0x5a4277...`), should arrive in 1-5 min
2. **Ethereum** — use deBridge UI or pre-approve max + retry
3. **Arbitrum** — same approach as Ethereum
4. **Celo** — use Squid Router via `bridge-from-source.ts` (auto-selects Squid for Celo)
5. **Monad** — use Squid or deBridge with chain ID `100000030`

### Revoke old wallet approvals
Visit `https://revoke.cash/address/0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15` and revoke any remaining token approvals on all chains.

### Final verification
- Run Golden Flow: `python scripts/e2e_golden_flow.py`
- Check balances: `node scripts/check-all-balances.ts` (set `EM_WORKER_WALLET=0x4aa8bE0422e042e5E8A37b0F8E956117F12740B0`)
- Grep for old wallet refs: `grep -r "52E05C8e" --include="*.py" --include="*.ts" --include="*.js"`
