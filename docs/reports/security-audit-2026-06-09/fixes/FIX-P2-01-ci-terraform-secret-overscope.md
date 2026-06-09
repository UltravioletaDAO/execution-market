---
date: 2026-06-09
tags: [type/incident, domain/security]
status: active
severity: P2
finding_id: FIX-P2-01
---
# FIX-P2-01 — CI/Terraform deploy credential can read every `em/*` secret (incl. platform wallet key) via `secretsmanager:*`

## Summary

The `em-cicd-terraform` IAM policy grants `secretsmanager:*` (which includes
`GetSecretValue`) on the **entire** `em/*` secret namespace, yet Terraform only
needs to *read back* the handful of secret versions it creates and only needs
*management* verbs on the rest. As a result the CI deploy identity
(`execution-market-deployer`, plus the planned OIDC role that mirrors it) can
read fund- and auth-controlling secrets it has no business reading —
`em/x402` (platform wallet `PRIVATE_KEY`), `em/supabase` (service-role / RLS
bypass), `em/admin-key`, `em/worldid` (RP signing key), `em/ens` (ENS owner
key). This fix splits that statement into narrow management verbs on `em/*`
plus `GetSecretValue` limited to the Terraform-managed version secrets, with an
explicit `Deny` on the fund/identity secrets as a wildcard backstop.

This is **defense-in-depth (P2), not a standalone exploit**: it requires first
compromising the CI credential, and on its own it does not fully close the
fund-loss path (see *Backward-compatibility / residual risk* — the same
credential can register a malicious ECS task under an execution role that
*does* legitimately hold `GetSecretValue` on `em/*`). The durable control is
completing the OIDC cutover and retiring the static key; this fix is the
blast-radius reduction that pairs with it.

## Severity & Impact (why P2; what funds/data are at risk)

- **Classified P2 (defense-in-depth gap), not P1**, for two reasons confirmed by
  the adversarial verifier:
  1. **Not exploitable in the current state.** It requires a *precondition*:
     compromising the static CI key (leaked CI log, compromised runner,
     malicious/forked PR workflow, action supply-chain compromise). It is not a
     present-state vulnerability.
  2. **Narrowing `GetSecretValue` alone does not close fund loss.** The same
     `em-cicd-terraform` policy also grants `ecs:*` (Sid `TerraformECS`),
     `lambda:*` on `em-*` (Sid `TerraformLambda`), and `iam:PassRole` /
     `iam:*RolePolicy` on `em-*` roles **and** `ecsTaskExecutionRole`
     (Sid `TerraformIAM`). Because the ECS execution role legitimately holds
     `GetSecretValue` on `em/*` (the `secrets_read` policy in
     `secrets.tf:144-164`), a compromised deployer key can register a malicious
     task definition under that role — or rewrite `em-*` Lambda code — and
     exfiltrate every `em/*` secret **indirectly**, even with `GetSecretValue`
     stripped from the deployer policy.

- **What is at risk if the CI key leaks (today, before this fix):**
  - `em/x402` → platform/settlement wallet `PRIVATE_KEY` → drain USDC/ETH from
    the settlement wallet; sign arbitrary EIP-3009 / x402r escrow operations as
    the platform. **Direct fund loss.**
  - `em/supabase` → `SUPABASE_SERVICE_ROLE_KEY` → full DB write, RLS bypass.
  - `em/admin-key` → `X-Admin-Key` → admin API.
  - `em/worldid` → `WORLD_ID_SIGNING_KEY` → forge RP signatures (anti-sybil bypass).
  - `em/ens` → `ENS_OWNER_PRIVATE_KEY`.

- **Net effect of this fix:** removes the *direct* `GetSecretValue` read path on
  fund/auth secrets from the CI deployer and adds an explicit `Deny` backstop so
  a future wildcard cannot silently re-grant it. The *indirect* path (PassRole +
  task-def registration) is closed by the paired OIDC cutover + tightening
  tracked below, which are out of scope of this single policy edit but **must**
  be completed for the fix to be meaningful.

## Affected code (exact file:line references)

> No secret VALUES are quoted anywhere below — only secret names/ARNs and IAM
> verbs.

1. **`infrastructure/iam/em-cicd-terraform-policy.json:46-51`** — the offending
   over-broad grant (committed source of truth; this file IS Terraform-managed,
   see #4):
   ```json
   {
     "Sid": "TerraformSecrets",
     "Effect": "Allow",
     "Action": ["secretsmanager:*"],
     "Resource": ["arn:aws:secretsmanager:us-east-2:518898403364:secret:em/*"]
   }
   ```
   `secretsmanager:*` ⊇ `GetSecretValue`, so this reads every `em/*` secret.

2. **`infrastructure/terraform/secrets.tf:144-164`** — *correctly-scoped*
   read policy for the **ECS execution role** (a different principal), shown for
   contrast. This one is intentionally `GetSecretValue` on `em/*` because the
   ECS execution role legitimately resolves all `valueFrom` task-def secrets at
   container start. **Do NOT change this policy** — it belongs to a different
   principal and the new `Deny` (attached only to the deployer policy) does not
   affect it.

3. **`infrastructure/terraform/github_oidc.tf:155-163`** — the planned OIDC role
   attaches the SAME two managed policies by ARN:
   ```hcl
   resource "aws_iam_role_policy_attachment" "github_actions_deploy" {
     for_each = var.enable_github_oidc_deploy_role ? toset([
       "arn:aws:iam::${local.account_id}:policy/em-cicd-deploy",
       "arn:aws:iam::${local.account_id}:policy/em-cicd-terraform",
     ]) : toset([])
     ...
   }
   ```
   Because it references `em-cicd-terraform` **by ARN**, fixing the JSON fixes
   the OIDC role automatically. **`github_oidc.tf` needs no edit.**

4. **`infrastructure/iam/cicd-deploy.tf:123-127`** — proves the committed JSON is
   the live IaC source of truth (so editing it + `terraform apply` updates the
   live policy):
   ```hcl
   resource "aws_iam_policy" "em_cicd_terraform" {
     name   = "em-cicd-terraform"
     policy = file("${path.module}/em-cicd-terraform-policy.json")
   }
   ```

5. **`.github/workflows/deploy.yml:70-74, 117-121, 265-269, 344-348, 528-532`** —
   confirms CI authenticates with the *static* `secrets.AWS_ACCESS_KEY_ID`
   (`aws-actions/configure-aws-credentials` with `aws-access-key-id:`, no
   `role-to-assume:`). This is the credential whose blast radius the over-scope
   amplifies. Live access key: `AKIA*7AGB` (Active, created 2026-03-13, never
   rotated).

### Terraform-managed secret versions (the ONLY `em/*` secrets Terraform reads)

Confirmed by reading the `.tf` files — these are the only secrets where
Terraform owns an `aws_secretsmanager_secret_version` and therefore needs
`GetSecretValue` to read state back:

| Secret name | Terraform resource |
|-------------|--------------------|
| `em/sentry-dsn` | `secrets.tf:74` |
| `em/veryai` | `secrets.tf:126` |
| `em/evidence-jwt-secret` | `evidence.tf:305` |
| `em/payshell/facilitator` | `payshell.tf:184` |
| `em/xmtp` | `xmtp-bot.tf:264` |
| `em/meshrelay` | `xmtp-bot.tf:288` |

> Note: the `data "aws_secretsmanager_secret"` lookups for `em/supabase`,
> `em/contracts`, `em/commission` (`secrets.tf:16-26`) read only **metadata**
> (ARN/name) — `DescribeSecret`, **not** `GetSecretValue`. They do not require
> read access to the secret value. The fund/identity secrets
> (`em/x402`, `em/supabase`, `em/admin-key`, `em/worldid`, `em/ens`,
> `em/commission`, `em/rpc-mainnet`) are referenced **only** via task-def
> `valueFrom` strings (`ecs.tf:334-482`) that the **ECS execution role**
> resolves at runtime — Terraform never reads their values.

### Drift note (must re-sync)

The **live** `em-cicd-terraform` policy is **version v12** and has drifted from
the committed JSON: live adds CloudTrail/GuardDuty statements
(`TerraformCloudTrail`, `TerraformGuardDuty`, `TerraformCloudTrailList`) that are
**absent** from `em-cicd-terraform-policy.json`. A `terraform apply` of the
committed JSON would *remove* those live-only statements. Before applying this
fix, the operator must reconcile the drift (see *The Fix → Step 0*) so the apply
is intentional and does not break CloudTrail/GuardDuty Terraform-managed
resources.

## Root cause (the real underlying defect)

A convenience wildcard. When the policy was authored, `secretsmanager:*` on
`em/*` was the easy way to let Terraform create/update/delete/tag the secret
*containers and versions* it manages. But `*` also grants `GetSecretValue`, and
the `em/*` namespace co-locates Terraform-managed config secrets (sentry, veryai,
xmtp, …) with fund/auth secrets Terraform never touches (x402 wallet key,
supabase service role, worldid signing key, ens owner key). Least privilege was
never applied at the action level: management verbs and the read verb were
collapsed into `*`, and the read verb was never restricted to the specific
secrets Terraform actually reads. Compounding it, the read path is reachable by
a long-lived static CI key stored in GitHub Actions (the highest-leak credential
class), and the namespace mixes blast radii.

## Exploit scenario (concrete attacker steps)

1. Attacker obtains the static deployer key (`AKIA*7AGB`) from a leaked CI log, a
   compromised GitHub Actions runner, a malicious PR workflow, or a forked-action
   supply-chain compromise.
2. `aws secretsmanager get-secret-value --secret-id em/x402 --region us-east-2`
   returns the platform wallet `PRIVATE_KEY` (current policy permits
   `GetSecretValue` on `em/*`).
3. Attacker imports the key, transfers the settlement wallet's USDC/ETH balance,
   and/or signs EIP-3009 / x402r escrow operations to redirect settlements.
4. Lateral: same key reads `em/supabase` (RLS bypass, full DB write),
   `em/admin-key` (admin API), `em/worldid` (forge RP signatures).
5. *Even after this fix*, the same key can register a malicious ECS task def
   under `em-production-ecs-execution` (PassRole granted) whose container reads
   the secrets via `valueFrom` — which is why this fix MUST be paired with the
   OIDC cutover + static-key deletion + ECS/Lambda/PassRole tightening.

## The Fix (PRECISE, code-level)

This is a single-file IaC change to the committed policy JSON, applied via
`terraform apply`, **paired with** the already-prepared OIDC cutover.

### Step 0 — Reconcile committed JSON with live v12 (prerequisite)

Before editing, pull the live policy so the new committed JSON is a superset that
preserves the live-only CloudTrail/GuardDuty statements (read-only, masks
nothing sensitive):

```bash
# Get the default (current) version id, then the document.
VID=$(aws iam get-policy \
  --policy-arn arn:aws:iam::518898403364:policy/em-cicd-terraform \
  --query 'Policy.DefaultVersionId' --output text)
aws iam get-policy-version \
  --policy-arn arn:aws:iam::518898403364:policy/em-cicd-terraform \
  --version-id "$VID" \
  --query 'PolicyVersion.Document' --output json > /tmp/em-cicd-terraform-live.json
```

Diff `/tmp/em-cicd-terraform-live.json` against the committed JSON. **Manually
copy any live-only statements (`TerraformCloudTrail*`, `TerraformGuardDuty`) into
the committed JSON** so the apply does not delete them. Then apply the
`TerraformSecrets` change below on top of the reconciled file.

> IAM managed policies allow a max of 5 versions. If the apply fails with
> `LimitExceeded`, prune the oldest non-default version:
> `aws iam delete-policy-version --policy-arn <arn> --version-id v<N>`.

### Step 1 — Edit `infrastructure/iam/em-cicd-terraform-policy.json`

Replace the single `TerraformSecrets` statement (lines 46-51) with **three**
statements: management verbs on `em/*`, scoped `GetSecretValue` on the
Terraform-managed versions, and an explicit `Deny` backstop on the fund/identity
secrets.

**Remove** (current lines 46-51):

```json
    {
      "Sid": "TerraformSecrets",
      "Effect": "Allow",
      "Action": ["secretsmanager:*"],
      "Resource": ["arn:aws:secretsmanager:us-east-2:518898403364:secret:em/*"]
    },
```

**Add** in its place:

```json
    {
      "Sid": "TerraformSecretsManage",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:CreateSecret",
        "secretsmanager:UpdateSecret",
        "secretsmanager:PutSecretValue",
        "secretsmanager:DeleteSecret",
        "secretsmanager:RestoreSecret",
        "secretsmanager:DescribeSecret",
        "secretsmanager:ListSecretVersionIds",
        "secretsmanager:TagResource",
        "secretsmanager:UntagResource",
        "secretsmanager:GetResourcePolicy",
        "secretsmanager:PutResourcePolicy",
        "secretsmanager:DeleteResourcePolicy"
      ],
      "Resource": ["arn:aws:secretsmanager:us-east-2:518898403364:secret:em/*"]
    },
    {
      "Sid": "TerraformSecretsReadManagedVersionsOnly",
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": [
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/sentry-dsn-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/veryai-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/evidence-jwt-secret-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/payshell/facilitator-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/xmtp-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/meshrelay-*"
      ]
    },
    {
      "Sid": "DenyReadFundAndAuthSecrets",
      "Effect": "Deny",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": [
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/x402-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/ens-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/worldid-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/supabase-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/supabase-jwt-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/admin-key-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/commission-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/reputation-relay-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/rpc-mainnet-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/anthropic-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/openai-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/google-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/openrouter-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/api-keys-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/dynamic-*",
        "arn:aws:secretsmanager:us-east-2:518898403364:secret:em/test-worker-*"
      ]
    },
```

**Why the `-*` ARN suffix on every secret:** AWS Secrets Manager appends a
random 6-char suffix to every secret ARN (`em/x402-AbCd12`). An IAM `Resource`
of `secret:em/x402` matches *nothing*; you must use `secret:em/x402-*` (or
`secret:em/x402*`). The original buggy statement worked only because `em/*`
wildcards over the whole namespace. Each scoped ARN here therefore uses the
`-*` form. The `Deny` uses the same pattern.

**Defense-in-depth rationale for the explicit `Deny`:** `Deny` overrides any
`Allow` in IAM evaluation. Even if a future edit reintroduces `secretsmanager:*`
or a broad `GetSecretValue` on `em/*`, the fund/auth secrets stay unreadable by
this principal. The allow-list (`TerraformSecretsReadManagedVersionsOnly`) is the
primary control; the `Deny` is the backstop. The `Deny` is attached to the
**deployer policy only** — it does NOT touch the ECS execution role's
`secrets_read` policy (`secrets.tf:144-164`), a different principal, so the
running platform is unaffected.

### Step 2 — Apply via Terraform (preferred) or AWS CLI (manual fallback)

**Terraform (governed path):**

```bash
cd infrastructure/terraform   # the workspace that includes ../iam via cicd-deploy.tf
terraform plan -target=aws_iam_policy.em_cicd_terraform
# Expect: in-place update of aws_iam_policy.em_cicd_terraform (new policy version).
terraform apply -target=aws_iam_policy.em_cicd_terraform
```

> `aws_iam_policy.em_cicd_terraform` lives in `infrastructure/iam/cicd-deploy.tf`
> and reads `em-cicd-terraform-policy.json` via `file()`. Confirm both
> directories share state / are applied together before running; if `iam/` is a
> separate workspace, run the apply there.

**Manual AWS CLI fallback** (if Terraform state is mid-flight):

```bash
aws iam create-policy-version \
  --policy-arn arn:aws:iam::518898403364:policy/em-cicd-terraform \
  --policy-document file://infrastructure/iam/em-cicd-terraform-policy.json \
  --set-as-default
```
Then `terraform plan` again to confirm zero drift (the CLI change matches IaC).

### Step 3 — Pair with the OIDC cutover + static-key retirement (REQUIRED)

This policy edit is necessary but **not sufficient**. Per
`docs/runbooks/iam-credential-rotation.md`, complete:

1. `terraform apply -var=enable_github_oidc_deploy_role=true` → creates the OIDC
   role (`github_oidc.tf`). It picks up the **fixed** `em-cicd-terraform` policy
   by ARN automatically.
2. Edit `deploy.yml`: add `permissions: id-token: write`, set
   `role-to-assume: <github_actions_deploy_role_arn output>`, remove
   `aws-access-key-id` / `secrets.AWS_ACCESS_KEY_ID` from all 5
   `configure-aws-credentials` steps.
3. Push to `main`, watch one full green OIDC deploy.
4. **Only after green:** delete the static key
   `aws iam delete-access-key --user-name execution-market-deployer --access-key-id AKIA*7AGB`.

### Step 4 — Tighten the indirect path (follow-up, separate change)

Out of scope of this JSON edit but logged as the durable fix: narrow the
deployer/OIDC `ecs:*`, `lambda:*` on `em-*`, and `iam:PassRole` on
`ecsTaskExecutionRole`/`em-production-ecs-execution`. Until then, a compromised
CI credential can still register a malicious task def under the execution role
(which retains `GetSecretValue` on `em/*`) and read every secret indirectly.
**State this honestly in the PR description.**

### No DB migration, no feature flag, no env var

This is purely an IAM policy change. The only flag involved is the **existing**
`var.enable_github_oidc_deploy_role` (default `false`), which gates the paired
OIDC role and is part of Step 3, not this finding's core edit.

### Backward-compatibility / residual risk & safe rollout

- **Could this lock out a legitimate deploy?** Only if Terraform reads an `em/*`
  secret version not in the `TerraformSecretsReadManagedVersionsOnly` allow-list
  or matched by the `Deny`. The allow-list is derived from the **complete** set
  of `aws_secretsmanager_secret_version` resources in the repo (6, listed above).
  The `Deny` list deliberately contains **no** Terraform-managed version secret.
  Mitigation: run `terraform plan` after applying — a missing read permission
  surfaces as a plan/apply `AccessDenied` on the specific secret, which is the
  exact symptom to add to the allow-list. Roll out by applying the policy first
  and running a `terraform plan` (read-only) **before** the next real deploy.
- **Staged rollout:** (1) reconcile drift (Step 0), (2) apply policy (Step 2),
  (3) `terraform plan` to confirm no new `AccessDenied`, (4) one normal deploy
  via the existing static key to confirm CI still works, (5) only then do the
  OIDC cutover (Step 3). This isolates "did the policy break the deploy?" from
  "did OIDC break the deploy?".
- **ECS runtime unaffected:** the `Deny` is on the deployer policy, not the ECS
  execution role. Running containers keep resolving `valueFrom` secrets.

## Test plan (how the execution team proves it's fixed)

### A. IAM policy-simulator assertions (reproduce-then-pass)

Add `infrastructure/iam/tests/test_em_cicd_terraform_secret_scope.sh` (or a
pytest wrapper) that runs `aws iam simulate-custom-policy` against the committed
JSON. The test must FAIL on the current policy and PASS after the fix.

```bash
#!/usr/bin/env bash
set -euo pipefail
POLICY=infrastructure/iam/em-cicd-terraform-policy.json
ACCT=518898403364
arn() { echo "arn:aws:secretsmanager:us-east-2:${ACCT}:secret:${1}-AbCd12"; }
sim() { # $1=action $2=resource-arn -> EvalDecision
  aws iam simulate-custom-policy \
    --policy-input-list "$(cat "$POLICY")" \
    --action-names "$1" --resource-arns "$2" \
    --query 'EvaluationResults[0].EvalDecision' --output text
}

# MUST be denied (reproduces the bug on the OLD policy → expect 'allowed' there)
for s in em/x402 em/supabase em/admin-key em/worldid em/ens em/commission; do
  d=$(sim secretsmanager:GetSecretValue "$(arn "$s")")
  [ "$d" = "explicitDeny" ] || [ "$d" = "implicitDeny" ] || { echo "FAIL: $s readable ($d)"; exit 1; }
done

# MUST remain allowed (Terraform-managed versions)
for s in em/sentry-dsn em/veryai em/evidence-jwt-secret em/xmtp em/meshrelay; do
  d=$(sim secretsmanager:GetSecretValue "$(arn "$s")")
  [ "$d" = "allowed" ] || { echo "FAIL: $s not readable by TF ($d)"; exit 1; }
done

# Management verbs MUST stay allowed on the namespace
for a in CreateSecret PutSecretValue DeleteSecret TagResource DescribeSecret; do
  d=$(sim "secretsmanager:$a" "$(arn em/x402)")
  [ "$a" = "DescribeSecret" ] && want=allowed || want=allowed   # all mgmt allowed on em/*
  [ "$d" = "$want" ] || { echo "FAIL: mgmt $a => $d"; exit 1; }
done
echo "PASS"
```

- **Assertion 1 (reproduces the bug):** `GetSecretValue` on `em/x402`,
  `em/supabase`, `em/admin-key`, `em/worldid`, `em/ens`, `em/commission` →
  `explicitDeny` after fix (would be `allowed` on the current policy).
- **Assertion 2 (no regression):** `GetSecretValue` on the 6 Terraform-managed
  version secrets → `allowed`.
- **Assertion 3 (management preserved):** `CreateSecret`/`PutSecretValue`/
  `DeleteSecret`/`TagResource`/`DescribeSecret` on `em/x402-*` → `allowed`.

### B. JSON lint / structural test

Add a tiny test (`jq`/python) asserting the policy contains a statement with
`"Effect":"Deny"` and `"secretsmanager:GetSecretValue"` covering `em/x402-*`,
and that **no** statement grants `secretsmanager:*`. This guards against a future
wildcard regression.

### C. Live policy-simulator (post-apply, against the real principal)

```bash
# Should be denied for the deployer user after apply:
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::518898403364:user/execution-market-deployer \
  --action-names secretsmanager:GetSecretValue \
  --resource-arns arn:aws:secretsmanager:us-east-2:518898403364:secret:em/x402-* \
  --query 'EvaluationResults[0].EvalDecision' --output text   # expect: explicitDeny
```

### D. Manual / E2E verification

1. With the deployer key configured, attempt the read — expect `AccessDenied`:
   `aws secretsmanager get-secret-value --secret-id em/x402 --region us-east-2`
   (do **not** print the value if it ever returns; it must not).
2. Confirm a managed read still works:
   `aws secretsmanager describe-secret --secret-id em/sentry-dsn` and a
   `terraform plan` that touches `aws_secretsmanager_secret_version.sentry_dsn`
   shows **no** `AccessDenied`.
3. Run a full deploy (or `terraform plan -refresh-only`) end-to-end and confirm
   no new permission errors.

## Rollback plan

- **Terraform:** revert the commit to `em-cicd-terraform-policy.json` and
  `terraform apply -target=aws_iam_policy.em_cicd_terraform` — restores the prior
  policy version.
- **AWS CLI (immediate):** the previous policy version still exists in IAM
  (managed policies keep up to 5). Re-set it as default:
  ```bash
  aws iam list-policy-versions --policy-arn arn:aws:iam::518898403364:policy/em-cicd-terraform
  aws iam set-default-policy-version \
    --policy-arn arn:aws:iam::518898403364:policy/em-cicd-terraform \
    --version-id v<PREVIOUS>
  ```
- **Blast radius of rollback:** restores the over-broad read; safe operationally,
  re-opens the finding. Acceptable only as a temporary unblock if a legitimate
  Terraform read was wrongly denied — in which case add that secret to the
  allow-list rather than rolling back wholesale.

## Verification checklist

- [ ] Step 0 done: live v12 pulled, CloudTrail/GuardDuty statements reconciled
      into the committed JSON (no live-only statements lost).
- [ ] `em-cicd-terraform-policy.json` no longer contains `secretsmanager:*`.
- [ ] JSON contains `TerraformSecretsManage` (mgmt verbs on `em/*`),
      `TerraformSecretsReadManagedVersionsOnly` (6 managed versions), and
      `DenyReadFundAndAuthSecrets` (explicit Deny).
- [ ] Every scoped/denied `Resource` ARN uses the `-*` suffix form.
- [ ] Policy applied (Terraform `apply` succeeded OR CLI `create-policy-version
      --set-as-default`), and a follow-up `terraform plan` shows zero drift.
- [ ] Test A passes: `GetSecretValue` on em/x402, em/supabase, em/admin-key,
      em/worldid, em/ens, em/commission → denied for the deployer principal.
- [ ] Test A passes: `GetSecretValue` on em/sentry-dsn, em/veryai,
      em/evidence-jwt-secret, em/xmtp, em/meshrelay → allowed.
- [ ] Live `simulate-principal-policy` (Test C) returns `explicitDeny` for
      em/x402-* against `execution-market-deployer`.
- [ ] A full CI deploy (or `terraform plan -refresh-only`) succeeds with no new
      `AccessDenied`.
- [ ] PR description explicitly notes this is defense-in-depth and that the
      durable fix is the OIDC cutover + static-key deletion + ECS/Lambda/PassRole
      tightening (Steps 3-4), with their tracking status.
- [ ] `secrets.tf:144-164` ECS execution-role `secrets_read` policy left
      UNCHANGED (verified diff touches only the deployer policy JSON).
