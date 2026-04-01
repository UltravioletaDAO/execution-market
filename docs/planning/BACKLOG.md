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
| 2026-03-31 | INC-2026-03-30 remediation: rotate wallet + fund new wallet | **HANDOFF** — See full instructions below. Wallet `0x52E0...5A15` drained via leaked key. Need: (1) generate new worker wallet, (2) update AWS SM `em/test-worker:private_key`, (3) update ECS task def `EM_WORKER_PRIVATE_KEY`, (4) fund new wallet across 8 chains using `fund-distribution` skill, (5) `git push origin main --force` to publish cleaned history. | P0 | pending |

---

## HANDOFF: INC-2026-03-30 — Wallet Rotation & Fund Distribution (P0)

**Incident**: Private key for worker wallet `0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15` leaked in `xmtp-bot/check_sub.mjs` (commit `f140f99e`, pushed to public main). Wallet drained ~$17 USDC across 8 chains by automated GitHub secret scanner bot (`0x9098...3333`).

**Already done (2026-03-31):**
- [x] Root cause identified: hardcoded key in `check_sub.mjs`
- [x] File removed from git tracking (`git rm --cached`)
- [x] `git-filter-repo --replace-text` executed — key replaced with `PRIVATE_KEY_REMOVED_INC_2026_03_30` in all history
- [x] Remote re-added (`origin` = `https://github.com/UltravioletaDAO/execution-market.git`)
- [x] Pre-commit hook added: scans staged files for `0x` + 64 hex chars, blocks commit
- [x] CLAUDE.md + global CLAUDE.md updated with zero-tolerance rules
- [x] .gitignore updated with throwaway script patterns
- [x] Memory saved: `inc-2026-03-30-key-leak.md`

**Remaining (for next session):**

### Step 1: Force push cleaned history to GitHub
```bash
cd Z:\ultravioleta\dao\execution-market
git push origin main --force
```
After this, the key will no longer be visible in GitHub commit history.

### Step 2: Generate new worker wallet
```bash
# Option A: Use cast (Foundry)
cast wallet new

# Option B: Use viem in Node
node -e "const { generatePrivateKey, privateKeyToAccount } = require('viem/accounts'); const pk = generatePrivateKey(); console.log('Address:', privateKeyToAccount(pk).address); console.log('Save key to AWS SM — do NOT display here');"
```
Save the new private key ONLY in AWS Secrets Manager. Never display it.

### Step 3: Update AWS Secrets Manager
```bash
# Update the test worker secret with new key
MSYS_NO_PATHCONV=1 aws secretsmanager update-secret \
  --secret-id em/test-worker \
  --secret-string '{"private_key":"NEW_KEY_HERE"}' \
  --region us-east-2
```

### Step 4: Update ECS task definition
Update `EM_WORKER_PRIVATE_KEY` in `infrastructure/terraform/ecs.tf` with the new AWS SM reference, then:
```bash
cd infrastructure/terraform && terraform apply
```

### Step 5: Fund new wallet across 8 chains
Use the **`fund-distribution` skill** (`/fund-distribution`). The scripts live in:

| Script | Location | Purpose |
|--------|----------|---------|
| `distribute-funds.js` | `scripts/wallet-management/` | Fan out USDC to wallets (Base + Polygon) |
| `distribute-phase0.js` | `scripts/wallet-management/` | Quick distribution to first 5 agents |
| `check-all-balances.ts` | `scripts/` | Check wallet balances across all EVM chains + Solana |
| `distribute-funds.ts` | `scripts/kk/` | Multi-token batch distribution (Disperse or sequential) |
| `distribute-gas-only.ts` | `scripts/kk/` | Gas-only distribution |
| `check-full-inventory.ts` | `scripts/kk/` | Full stablecoin + native balance inventory |

**Key pattern** (from `fund-distribution` skill — reads key from AWS SM):
```bash
node -e "
const { execSync } = require('child_process');
const raw = execSync('aws secretsmanager get-secret-value --secret-id YOUR_SECRET_PATH/x402 --query SecretString --output text --region us-east-2', {encoding:'utf8'});
const pk = JSON.parse(raw).PRIVATE_KEY;
execSync('npx tsx kk/<script>.ts <args>', {
  stdio: 'inherit',
  env: { ...process.env, WALLET_PRIVATE_KEY: pk, PRIVATE_KEY: pk }
});
"
```

**Budget**: ~$5 USDC per chain for testing. Total ~$40 across 8 EVM chains.

**Chains to fund**: Base, Ethereum, Polygon, Arbitrum, Avalanche, Celo, Monad, Optimism.

### Step 6: Revoke old wallet approvals
Visit `https://revoke.cash/address/0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15` and revoke any remaining token approvals on all chains. The wallet is burned but revoking prevents future exploit if tokens are accidentally sent there.

### Step 7: Verify
- Run Golden Flow E2E test: `python scripts/e2e_golden_flow.py`
- Verify new wallet is signing correctly on all chains
- Check that no references to old wallet remain: `grep -r "52E05C8e" --include="*.py" --include="*.ts" --include="*.js"`
