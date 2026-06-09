---
date: 2026-05-27
tags:
  - type/runbook
  - domain/security
status: active
aliases:
  - OIDC migration runbook
  - deployer key rotation
related-files:
  - infrastructure/terraform/github_oidc.tf
  - infrastructure/terraform/iam_deploy_rate_limit.tf
  - .github/workflows/deploy.yml
---

# IAM Credential Rotation — GitHub OIDC Migration + Root Hygiene

Operator runbook for audit findings **F-01b** (migrate CI off the static
`execution-market-deployer` access key to GitHub OIDC) and the two
console-only root hygiene items. Source: [[MASTER_PLAN_AWS_ALARMS_AUDIT_2026-05-21]],
forensics in `docs/reports/aws-alarms-audit-2026-05-21/`.

> **Account**: `518898403364` · **Region**: `us-east-2` · **Repo**:
> `UltravioletaDAO/execution-market`
>
> You are likely streaming. **Never print full access key IDs or any
> secret value.** Mask key IDs as `AKIA*<last4>`. To prove a key exists
> without revealing it: `echo "KEY is ${VAR:+set}"`.

## State at time of writing (verified read-only 2026-05-27)

| Item | Finding |
|------|---------|
| `execution-market-deployer` access keys | **1 active** key, `AKIA*7AGB`, created 2026-03-13 (~2.5 mo, never rotated). Still in active use (last used today, `acm`/`us-east-1`). |
| GitHub OIDC provider | **Already exists** (`token.actions.githubusercontent.com`, client ID `sts.amazonaws.com`). Owned by another project (tag `Project=AutoJob`, `ManagedBy=Terraform`) — shared account infra. `github_oidc.tf` **references** it, does not create it. |
| Deployer managed policies | `em-cicd-deploy` + `em-cicd-terraform` (both `AttachmentCount=1`). The OIDC role attaches these same two — mirrors permissions exactly. |
| `iam_deploy_rate_limit.tf` | Prepared (commit `a348e538`); deploy-storm alarm. **Not the same change** as this OIDC work — independent. |

## Recommended order of operations

```
0. Resolve the payshell WIP so `terraform apply` won't drag uncommitted infra.
1. (a) Apply github_oidc.tf with the opt-in flag → creates the OIDC role.
2. (a) Edit deploy.yml: add id-token perm + role-to-assume, remove static-key secrets.
3. (b) Push to main, watch one full green deploy run via OIDC.
4. (b) ONLY after green: delete the static access key.
5. (b) After ~1 week of green deploys: delete the now-unused secrets + optionally the deployer user.
6. (c) Rotate the root password (console).
7. (d) Pre-check the cost/inventory SaaS, then delete the legacy 2015 root key (console).
```

Steps 6 and 7 are independent of 1–5 and can be done any time.

---

## (a) Apply `github_oidc.tf` and cut the workflow over to OIDC

### Pre-req — resolve uncommitted infra WIP

`terraform apply` operates on the whole `infrastructure/terraform/` directory.
There is uncommitted WIP (`payshell.tf` and related) in the working tree. Do
**one** of:

- Commit/finish the payshell work first, **or**
- Apply from a clean checkout of `main` that contains only `github_oidc.tf`,
  **or**
- Use a targeted apply (below) so only the OIDC resources are touched.

### Apply (targeted, opt-in)

```bash
cd infrastructure/terraform
terraform init   # if not already initialized in this checkout

# Plan ONLY the new OIDC resources, with the feature flag on.
terraform plan \
  -var=enable_github_oidc_deploy_role=true \
  -target=data.aws_iam_openid_connect_provider.github \
  -target=aws_iam_role.github_actions_deploy \
  -target=aws_iam_role_policy_attachment.github_actions_deploy \
  -out=oidc.tfplan

# Review: should create 1 role + 2 policy attachments, read 1 data source. No other changes.
terraform apply oidc.tfplan
```

> To make the flag permanent (so CI's own `terraform apply` keeps the role),
> set `default = true` on `enable_github_oidc_deploy_role` in
> `github_oidc.tf`, **or** add `-var=enable_github_oidc_deploy_role=true` to
> the `TF_VARS` line in `deploy.yml`'s Terraform Plan step. Do this only
> after step (b) is green, so a failed cutover can't strand the role.

### Capture the role ARN

```bash
terraform output -raw github_actions_deploy_role_arn
# -> arn:aws:iam::518898403364:role/em-production-github-actions-deploy
```

### Edit `.github/workflows/deploy.yml`

Five jobs configure AWS credentials (`build-and-push-backend`,
`build-and-push-lambdas`, `terraform-apply`, `deploy-frontend`,
`deploy-backend`). Each needs: (1) `id-token: write` permission so the runner
can mint an OIDC token, and (2) the `configure-aws-credentials` step switched
from static keys to `role-to-assume`. `aws-actions/configure-aws-credentials`
is already pinned to v6.1.0, which supports OIDC natively.

**Add a top-level `permissions` block** (after the `concurrency:` block).
`id-token: write` is required for OIDC; `contents: read` is needed by
`actions/checkout` once an explicit `permissions` block exists:

```diff
 concurrency:
   group: deploy-${{ github.ref }}
   cancel-in-progress: true

+# Required for GitHub OIDC: id-token lets each job mint the federation token.
+# Declaring permissions explicitly drops the default token to least privilege,
+# so we must re-grant contents:read for actions/checkout.
+permissions:
+  id-token: write
+  contents: read
+
 env:
   AWS_REGION: us-east-2
```

> If any job needs broader token scope (e.g. writing PR comments), set
> `permissions:` at the job level instead and keep the top-level block minimal.
> For pure deploy, the two lines above are sufficient.

**Replace every `configure-aws-credentials` step.** There are 5 identical
blocks — apply this diff to each:

```diff
       - name: Configure AWS credentials
         uses: aws-actions/configure-aws-credentials@ec61189d14ec14c8efccab744f656cffd0e33f37  # v6.1.0
         with:
-          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
-          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
+          role-to-assume: arn:aws:iam::518898403364:role/em-production-github-actions-deploy
+          role-session-name: gha-${{ github.run_id }}
           aws-region: ${{ env.AWS_REGION }}
```

> Optionally store the ARN as a repo **variable** (not secret) and reference
> `${{ vars.AWS_DEPLOY_ROLE_ARN }}` to avoid hardcoding the account ID. An
> ARN is not sensitive, so a plain `vars.` entry is fine.

No other workflow lines change — ECR login, S3 sync, CloudFront invalidation,
and Terraform all use the resolved temporary credentials transparently.

---

## (b) Verify OIDC works, THEN delete the static key

1. Commit the `deploy.yml` change and push to `main`.
2. Watch the Actions run end-to-end. Confirm:
   - "Configure AWS credentials" succeeds (no `InvalidClientTokenId`,
     no `Not authorized to perform sts:AssumeRoleWithWebIdentity`).
   - ECR push, `terraform plan`, ECS deploy, S3 sync, CloudFront
     invalidation all pass.
   - `https://api.execution.market/api/v1/version` reports the new `git_sha`.
3. Sanity-check the role is actually being used:
   ```bash
   aws iam get-role --role-name em-production-github-actions-deploy \
     --query 'Role.RoleLastUsed' --output json
   # LastUsedDate should be within the last few minutes.
   ```

**Only after a fully green OIDC deploy**, retire the static key.

> Two-phase retirement is safer than a hard delete. Phase 1: deactivate
> (instantly reversible if a hidden consumer breaks). Phase 2: delete after a
> cooling-off window.

```bash
# Discover the key ID (it will print in full — do NOT screen-share this line).
aws iam list-access-keys --user-name execution-market-deployer \
  --query 'AccessKeyMetadata[].{Id:AccessKeyId,Status:Status,Created:CreateDate}' \
  --output table

# Phase 1 — deactivate. Replace <KEYID> with the AKIA*7AGB key.
aws iam update-access-key --user-name execution-market-deployer \
  --access-key-id <KEYID> --status Inactive

# Run a deploy (or workflow_dispatch). If it still goes green, the key is dead weight.

# Phase 2 — after ~1 week of green OIDC deploys, delete it.
aws iam delete-access-key --user-name execution-market-deployer \
  --access-key-id <KEYID>
```

3. **Clean up the now-unused GitHub secrets** (`AWS_ACCESS_KEY_ID`,
   `AWS_SECRET_ACCESS_KEY`) from repo/org settings → Secrets and variables →
   Actions. Leave `AWS_ACCOUNT_ID`, `TF_STATE_KEY`, the `VITE_*`, and
   `DASHBOARD_CLOUDFRONT_ID` secrets in place — they are not credentials.
4. **Optional**: once nothing else uses `execution-market-deployer` (it had
   no console login, only this key), delete the user itself. Detach its two
   policies first; do **not** delete the policies — the OIDC role now uses them.

---

## (c) Rotate the root password (console only — no CLI)

The root user's password is unrotated 3+ years (audit). This **cannot** be
done via CLI/API; it is a console operation by the account root owner.

1. Sign in to the AWS console **as the account root user** (root email +
   current password + the hardware MFA already enrolled on root).
2. Top-right account menu → **Security credentials**.
3. Under **Password**, choose **Change password**.
4. Set a new strong unique password (use a password manager; 24+ chars).
   - Do **not** type or paste it anywhere that is being screen-shared.
5. Confirm root MFA is still **enabled** (it is, per audit — keep it).
6. Record the rotation date in [[MASTER_PLAN_AWS_ALARMS_AUDIT_2026-05-21]]
   and store the new password in the team password manager only.

> Day-to-day work must never use root. This is hygiene on a break-glass
> credential, not a return to using it.

---

## (d) Delete the legacy 2015 root access key (console only — no CLI)

A root **access key** `AKIA*6GHQ` created in 2015 still exists (now
**Inactive**). Root access keys are a top AWS anti-pattern and should be
deleted — but **only after** confirming no external tool still depends on it.

### Pre-check FIRST — do not skip

The audit observed this key being **used 2026-04-18 through 2026-04-21**, from
an EC2 instance in **`us-west-2`** (a region this project does not deploy to).
That pattern is consistent with a third-party **cost/inventory SaaS**
(Cloudability / Vantage / CloudHealth / nOps and similar) that ingests billing
and resource data via a key. Deleting the key would silently break that
integration's data feed.

```bash
# Confirm current status + last use of the legacy root key.
# (Root key metadata is only visible while signed in AS ROOT, console or
#  a root-session CLI — it does not appear under the deployer/IAM-user APIs.)
# In the root console: Security credentials → Access keys.
#   - Note the Last used date + region (expect us-west-2, ~2026-04-18..21).

# Confirm what (if anything) still calls it via CloudTrail in the management
# account, scoped to that key's principal over the last ~60 days:
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=<ROOT_KEYID> \
  --start-time 2026-03-27 --end-time 2026-05-27 \
  --query 'Events[].{Time:EventTime,Event:EventName,Src:Username}' \
  --output table
```

**Decision:**

- If a known cost/inventory SaaS still uses it → **do not delete yet.** First
  re-onboard that vendor onto a dedicated **IAM role** (cross-account
  `AssumeRole` with their external ID) or a scoped IAM **user** with a
  read-only billing policy. Cut the vendor over, confirm their dashboard keeps
  updating, **then** delete the root key.
- If nothing uses it (no events, vendor migrated, or vendor confirmed gone) →
  proceed.

### Delete (root console)

1. Sign in **as account root**.
2. **Security credentials** → **Access keys**.
3. Locate the 2015 key (`AKIA*6GHQ`, Inactive).
4. (Belt-and-suspenders, already true) ensure it is **Inactive**, observe a
   few days, then **Delete**.
5. Verify zero root access keys remain:
   - Console: the Access keys section shows none.
   - IAM credential report (`aws iam generate-credential-report` →
     `get-credential-report`) shows the `<root_account>` row with
     `access_key_1_active = false` and no key present.
6. Record completion in the master plan.

---

## Post-conditions (done when all true)

- [ ] `deploy.yml` uses `role-to-assume`, has `id-token: write`, and has **no**
      `aws-access-key-id` / `aws-secret-access-key` lines.
- [ ] A full deploy ran green via OIDC; `RoleLastUsed` on
      `em-production-github-actions-deploy` is recent.
- [ ] `execution-market-deployer` has **0** access keys.
- [ ] `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` GitHub secrets removed.
- [ ] Root password rotated; root MFA still enabled.
- [ ] Legacy 2015 root access key deleted (after SaaS pre-check); **0** root
      access keys remain.
