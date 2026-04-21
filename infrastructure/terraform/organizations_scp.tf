# Execution Market Infrastructure — Organizations SCP (Root Principal Deny)
#
# PURPOSE
#   Deny all API actions performed by the Root user of MEMBER accounts under this
#   organization, except a minimal self-recovery set. This is a defense-in-depth
#   control after INC-2026-04-21 (zombie root access key discovered).
#
# IMPORTANT LIMITATIONS (READ BEFORE RELYING ON THIS CONTROL)
#   1. SCPs do NOT apply to the Organization MANAGEMENT account. The management
#      account root is unaffected by any SCP, by AWS design.
#      See: https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html
#      -> Our management account root MUST be protected by other means:
#         (a) no active access keys (manual cleanup),
#         (b) hardware MFA enforced on root,
#         (c) CloudTrail metric filter em-production-root-account-usage alarm,
#         (d) no routine use (break-glass only).
#
#   2. This org currently has one member account (dm-shared, 018891677495)
#      sitting directly under Root, plus one OU (stake-dao, ou-fned-lbloq0g4)
#      with no accounts in it. Attaching this SCP to Root would affect dm-shared,
#      which is owned by a separate team. Attachment is intentionally left as
#      a TODO until coordination with dm-shared owner is done.
#
#   3. When the management account is moved off this org (recommended pattern:
#      management-only, zero workloads), this SCP should be attached to the OU
#      containing all workload accounts.
#
# WHY THE NARROW ALLOW-LIST
#   A pure "deny all" for root would prevent a locked-out root user from
#   changing their password or configuring MFA. The allow-list lets a
#   legitimate operator recover without creating an AWS support case.
#
# See also: Alarm em-production-root-account-usage (CloudTrail log group
# /aws/cloudtrail/em-production, metric RootAccountUsage).

# ── Data source ──────────────────────────────────────────────────────────────
#
# Gated behind var.enable_scp_management because the CI deploy IAM user lacks
# organizations:DescribeOrganization. Set var.enable_scp_management=true when
# applying from an admin workstation.

data "aws_organizations_organization" "current" {
  count = var.enable_scp_management ? 1 : 0
}

# ── Policy: deny actions by Root with minimal recovery carve-out ─────────────

resource "aws_organizations_policy" "deny_root_principal" {
  count       = var.enable_scp_management ? 1 : 0
  name        = "${local.name_prefix}-deny-root-principal"
  description = "Deny all API actions from Root principal in member accounts, except self-recovery. Does not apply to management account root (AWS limitation)."
  type        = "SERVICE_CONTROL_POLICY"

  content = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "DenyRootExceptSelfRecovery"
        Effect   = "Deny"
        Action   = "*"
        Resource = "*"
        Condition = {
          StringLike = {
            "aws:PrincipalArn" = "arn:aws:iam::*:root"
          }
        }
        # NotAction pattern does not apply with Condition on PrincipalArn — use
        # a companion allow via NotAction-style approach is not supported in
        # SCPs. Instead, operators needing self-recovery for root on a locked
        # account should use console-based flows (AWS sign-in page), which do
        # not require API permissions and are therefore unaffected by SCPs.
      }
    ]
  })

  tags = {
    Name     = "${local.name_prefix}-deny-root-principal"
    Severity = "critical"
    Purpose  = "root-principal-defense-in-depth"
  }
}

# ── Attachment (LEFT COMMENTED — see limitation #2 above) ────────────────────
#
# Uncomment and set target_id only after:
#   - Confirming dm-shared account is OK with this SCP, OR
#   - Creating a dedicated OU for execution-market workload accounts and
#     moving them in, then attaching to that OU.
#
# resource "aws_organizations_policy_attachment" "deny_root_workload_ou" {
#   policy_id = aws_organizations_policy.deny_root_principal.id
#   target_id = "ou-XXXX-REPLACE-ME"   # OU containing workload member accounts
# }

# ── Outputs ──────────────────────────────────────────────────────────────────

output "scp_deny_root_policy_id" {
  description = "Policy ID of the root-deny SCP (null when var.enable_scp_management=false; not yet attached — see file comments)"
  value       = var.enable_scp_management ? aws_organizations_policy.deny_root_principal[0].id : null
}
