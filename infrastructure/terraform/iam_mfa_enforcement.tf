# Execution Market Infrastructure — IAM MFA Enforcement for Console Users
#
# PURPOSE
#   Standard AWS pattern: deny all actions for IAM users who have not
#   authenticated with MFA, except a minimal self-service carve-out so the
#   user can list/activate their own MFA device and change their password.
#
# WHO THIS APPLIES TO
#   Console-enabled human users only. Service/CI users MUST NOT be attached
#   here (they use programmatic credentials and do not authenticate via MFA).
#
#   Console users in this account (as of 2026-04-21, from `aws iam list-users`):
#     - kadrez  — PasswordLastUsed 2025-07-18, NO MFA device  → ATTACH
#     - lxhxr   — PasswordLastUsed 2021-07-19, MFA ALREADY set → SAFE TO ATTACH
#                 (policy is a no-op for users already using MFA)
#     - cuchorapido — PasswordLastUsed NEVER, NO MFA device, but has a login
#                 profile used for console. Attaching is safe (forces MFA on
#                 first login), but coordinate before apply.
#
#   All other users in this account (amplify-deployer, cv-deployer, datboi,
#   execution-market-deployer, github-actions-pixel-marketplace,
#   perplexity-computer, terraform-deployer, ultraclawd) are service users
#   with programmatic access only — DO NOT attach.
#
# POLICY SOURCE
#   Canonical AWS-published pattern:
#   https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_examples_aws_my-sec-creds-self-manage.html
#   (simplified for the single "force MFA before doing anything else" use case)

# ── Policy: Force MFA on console users ───────────────────────────────────────

resource "aws_iam_policy" "force_mfa" {
  name        = "ForceMFA-ExecutionMarket"
  path        = "/"
  description = "Blocks all actions until the user authenticates with MFA. Allows self-service MFA device registration and password change. Attach ONLY to console-enabled human users."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowListActionsRequiredForSignIn"
        Effect = "Allow"
        Action = [
          "iam:ListMFADevices",
          "iam:ListVirtualMFADevices",
          "iam:ListUsers",
          "iam:GetAccountPasswordPolicy",
          "iam:GetAccountSummary"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowManageOwnVirtualMFADevice"
        Effect = "Allow"
        Action = [
          "iam:CreateVirtualMFADevice",
          "iam:DeleteVirtualMFADevice"
        ]
        Resource = "arn:aws:iam::*:mfa/&{aws:username}"
      },
      {
        Sid    = "AllowManageOwnMFAEnrollment"
        Effect = "Allow"
        Action = [
          "iam:DeactivateMFADevice",
          "iam:EnableMFADevice",
          "iam:GetUser",
          "iam:GetMFADevice",
          "iam:ListMFADeviceTags",
          "iam:ResyncMFADevice"
        ]
        Resource = "arn:aws:iam::*:user/&{aws:username}"
      },
      {
        Sid    = "AllowManageOwnPasswordAndKeys"
        Effect = "Allow"
        Action = [
          "iam:ChangePassword",
          "iam:GetLoginProfile",
          "iam:CreateLoginProfile",
          "iam:UpdateLoginProfile",
          "iam:GetAccessKeyLastUsed",
          "iam:ListAccessKeys",
          "iam:UpdateAccessKey",
          "iam:CreateAccessKey",
          "iam:DeleteAccessKey"
        ]
        Resource = "arn:aws:iam::*:user/&{aws:username}"
      },
      {
        Sid    = "DenyAllExceptListedIfNoMFA"
        Effect = "Deny"
        NotAction = [
          "iam:CreateVirtualMFADevice",
          "iam:DeleteVirtualMFADevice",
          "iam:ListMFADevices",
          "iam:ListVirtualMFADevices",
          "iam:EnableMFADevice",
          "iam:ResyncMFADevice",
          "iam:ChangePassword",
          "iam:GetUser",
          "iam:GetMFADevice",
          "iam:GetAccountPasswordPolicy",
          "iam:GetAccountSummary",
          "iam:ListUsers",
          "iam:ListAccessKeys",
          "iam:GetAccessKeyLastUsed",
          "iam:GetLoginProfile",
          "sts:GetCallerIdentity"
        ]
        Resource = "*"
        Condition = {
          BoolIfExists = {
            "aws:MultiFactorAuthPresent" = "false"
          }
        }
      }
    ]
  })

  tags = {
    Name    = "ForceMFA-ExecutionMarket"
    Purpose = "console-user-mfa-enforcement"
  }
}

# ── Attachments ──────────────────────────────────────────────────────────────
#
# Start with kadrez (no MFA, confirmed console user).
# cuchorapido can be added once user is notified.
# lxhxr already has MFA, attachment is safe but not urgent.
#
# Leave this list EXPLICIT — do NOT iterate a broad filter. We never want to
# accidentally attach this to a service user and break CI/CD.

variable "mfa_enforced_users" {
  description = "IAM users who must authenticate with MFA. Attach ONLY human console users."
  type        = list(string)
  # Intentionally empty by default — operator must opt in per user.
  # Confirmed target for first enforcement: "kadrez"
  default = []
}

resource "aws_iam_user_policy_attachment" "force_mfa" {
  for_each   = toset(var.mfa_enforced_users)
  user       = each.key
  policy_arn = aws_iam_policy.force_mfa.arn
}

# ── Outputs ──────────────────────────────────────────────────────────────────

output "force_mfa_policy_arn" {
  description = "ARN of the ForceMFA policy — attach manually or via mfa_enforced_users variable."
  value       = aws_iam_policy.force_mfa.arn
}
