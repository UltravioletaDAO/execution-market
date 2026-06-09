# Execution Market Infrastructure — GitHub Actions OIDC Deploy Role
#
# PURPOSE
#   Replace the long-lived static AKIA access key that GitHub Actions
#   currently uses (`execution-market-deployer` user) with short-lived,
#   OIDC-federated credentials. GitHub mints a per-job OIDC token; AWS STS
#   exchanges it for temporary credentials scoped to this repo. No secret
#   ever lives in GitHub, so there is nothing to leak or rotate.
#
# FINDING THAT MOTIVATED THIS (audit 2026-05-21, F-01b / P1)
#   `execution-market-deployer` authenticates CI with a static access key
#   created 2026-03-13 and never rotated (~2.5 months old at audit time).
#   A static key in CI is the single largest standing credential-leak risk:
#   it is copied into GitHub repo/org secrets, survives runner compromise,
#   and only rotates when a human remembers to. OIDC removes the key class
#   entirely. After the workflow is cut over and a deploy is verified green,
#   the human operator deletes the static key (see runbook step (b)).
#   Runbook: docs/runbooks/iam-credential-rotation.md
#
# CURRENT STATE (verified read-only at prepare time)
#   - GitHub OIDC provider ALREADY EXISTS in this account:
#       arn:aws:iam::<acct>:oidc-provider/token.actions.githubusercontent.com
#     It was created by another project (tagged Project=AutoJob,
#     ManagedBy=Terraform) and is shared account infra. ClientIDList already
#     contains "sts.amazonaws.com", which is exactly what we need. We must
#     therefore REFERENCE it (data source) and NOT declare an
#     aws_iam_openid_connect_provider here — declaring one would fail with
#     EntityAlreadyExists and would also stomp the other project's resource.
#   - The deployer user has exactly TWO managed policies:
#       em-cicd-deploy     (ECR push, ECS deploy, S3 sync, CF invalidation)
#       em-cicd-terraform  (terraform plan/apply: ECS, VPC, IAM, CW, ALB, WAF…)
#     The OIDC role attaches THESE SAME TWO policies — mirroring the
#     deployer's permissions exactly, never exceeding them.
#
# SCOPING / TRUST
#   The trust policy restricts who can assume this role to:
#     - audience  : sts.amazonaws.com (the OIDC provider's configured client ID)
#     - subject   : repo:UltravioletaDAO/execution-market — only THIS repo,
#                   only the two branches that deploy (main, production) and
#                   the GitHub Environments the workflow uses (production,
#                   staging). PRs from forks cannot assume the role.
#   GitHub's `sub` claim is case-sensitive and uses the canonical org/repo
#   casing as stored on GitHub: "UltravioletaDAO/execution-market".
#
# ROLLOUT IS OPT-IN
#   Gated behind var.enable_github_oidc_deploy_role (default false) so a plain
#   `terraform apply` is a no-op until the operator deliberately enables it.
#   This matches the careful pattern in iam_mfa_enforcement.tf — IAM changes
#   that touch CI must never roll out implicitly. Flip to true (or pass
#   -var=enable_github_oidc_deploy_role=true) per the runbook.

# ── Inputs (declared inline — do NOT add to variables.tf) ─────────────────────

variable "enable_github_oidc_deploy_role" {
  description = "Create the GitHub Actions OIDC deploy role. Default false so apply is a no-op until the operator opts in (see docs/runbooks/iam-credential-rotation.md)."
  type        = bool
  default     = false
}

variable "github_oidc_repo" {
  description = "GitHub org/repo allowed to assume the deploy role, in OIDC `sub` casing (case-sensitive)."
  type        = string
  default     = "UltravioletaDAO/execution-market"
}

variable "github_oidc_deploy_branches" {
  description = "Branches whose workflow runs may assume the deploy role. Mirrors deploy.yml `on.push.branches`."
  type        = list(string)
  default     = ["main", "production"]
}

variable "github_oidc_deploy_environments" {
  description = "GitHub Environments whose jobs may assume the deploy role. Mirrors the `environment:` blocks in deploy.yml / deploy-prod.yml (both pinned to `production`)."
  type        = list(string)
  default     = ["production", "staging"]
}

variable "github_oidc_deploy_tag_patterns" {
  description = <<-EOT
    Tag-ref glob patterns whose workflow runs may assume the deploy role.
    deploy-prod.yml triggers on `release: published`, so its jobs run with
    github.ref = refs/tags/<tag>. The `build-and-push` job has no environment,
    so its OIDC `sub` is `repo:<repo>:ref:refs/tags/<tag>` — it would be denied
    unless tag refs are allowed. Restricted to strict semver release tags so a
    throwaway tag cannot assume the role.
  EOT
  type        = list(string)
  default     = ["refs/tags/v*"]
}

# ── Reference the existing account-level OIDC provider ────────────────────────
# Shared infra owned by another Terraform state (Project=AutoJob). We read it,
# we do not manage it. If this account is ever rebuilt from scratch and the
# provider does NOT exist, create it once (in this file or shared infra):
#
#   resource "aws_iam_openid_connect_provider" "github" {
#     url             = "https://token.actions.githubusercontent.com"
#     client_id_list  = ["sts.amazonaws.com"]
#     thumbprint_list = ["ffffffffffffffffffffffffffffffffffffffff"] # IAM ignores it for these providers; AWS validates the cert chain via the root CA
#   }
#
# ...then swap the data source below for that resource's .arn.

data "aws_iam_openid_connect_provider" "github" {
  count = var.enable_github_oidc_deploy_role ? 1 : 0
  url   = "https://token.actions.githubusercontent.com"
}

# ── Trust policy (web-identity assume-role) ───────────────────────────────────
# StringEquals locks the audience to sts.amazonaws.com. StringLike on `sub`
# enumerates exactly the branch refs and environments the workflow uses — no
# broad `repo:org/repo:*` wildcard, so a fork PR or an unexpected ref cannot
# assume the role.

data "aws_iam_policy_document" "github_oidc_assume" {
  count = var.enable_github_oidc_deploy_role ? 1 : 0

  statement {
    sid     = "GitHubActionsOIDC"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github[0].arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = concat(
        [for b in var.github_oidc_deploy_branches : "repo:${var.github_oidc_repo}:ref:refs/heads/${b}"],
        [for e in var.github_oidc_deploy_environments : "repo:${var.github_oidc_repo}:environment:${e}"],
        # Release-tag runs (deploy-prod.yml `release: published` build-and-push
        # job has no environment, so it authenticates by tag ref). Restricted to
        # strict semver release tags via the glob in github_oidc_deploy_tag_patterns.
        [for t in var.github_oidc_deploy_tag_patterns : "repo:${var.github_oidc_repo}:ref:${t}"],
      )
    }
  }
}

# ── The deploy role ───────────────────────────────────────────────────────────

resource "aws_iam_role" "github_actions_deploy" {
  count = var.enable_github_oidc_deploy_role ? 1 : 0

  name                 = "${local.name_prefix}-github-actions-deploy"
  description          = "Assumed by GitHub Actions (UltravioletaDAO/execution-market) via OIDC. Replaces the static execution-market-deployer access key. Mirrors that user's two managed policies."
  assume_role_policy   = data.aws_iam_policy_document.github_oidc_assume[0].json
  max_session_duration = 3600 # 1h — a single deploy run fits comfortably; keep blast radius small

  tags = {
    Name    = "${local.name_prefix}-github-actions-deploy"
    Purpose = "cicd-oidc-deploy"
  }
}

# ── Permissions: mirror the deployer user EXACTLY ─────────────────────────────
# Attach the SAME two managed policies already on execution-market-deployer.
# This guarantees the OIDC role can do everything the static-key user can do
# and nothing more. If CI needs a new permission later, edit those policies
# (per .claude/agent-memory aws-infrastructure-expert/iam-deployer-policy.md
# and infrastructure/iam/em-cicd-terraform-policy.json) — NOT this file.

resource "aws_iam_role_policy_attachment" "github_actions_deploy" {
  for_each = var.enable_github_oidc_deploy_role ? toset([
    "arn:aws:iam::${local.account_id}:policy/em-cicd-deploy",
    "arn:aws:iam::${local.account_id}:policy/em-cicd-terraform",
  ]) : toset([])

  role       = aws_iam_role.github_actions_deploy[0].name
  policy_arn = each.key
}

# ── Output: the role ARN for `role-to-assume:` in deploy.yml ──────────────────

output "github_actions_deploy_role_arn" {
  description = "ARN to put in deploy.yml configure-aws-credentials `role-to-assume`. Null until var.enable_github_oidc_deploy_role=true."
  value       = var.enable_github_oidc_deploy_role ? aws_iam_role.github_actions_deploy[0].arn : null
}
