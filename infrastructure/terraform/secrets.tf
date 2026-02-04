# Execution Market Infrastructure - Secrets Reference
#
# Existing secrets are managed manually in AWS Secrets Manager.
# Secrets are stored under the em/* prefix:
#   - em/supabase (url, anon_key, service_key)
#   - em/contracts (avalanche, etc.)
#   - em/commission (address)
#   - em/x402 (private_key)
#   - em/api-keys (api keys)
#
# This file only creates IAM policies for accessing these secrets.

# Data sources for existing secrets
data "aws_secretsmanager_secret" "supabase" {
  name = "em/supabase"
}

data "aws_secretsmanager_secret" "contracts" {
  name = "em/contracts"
}

data "aws_secretsmanager_secret" "commission" {
  name = "em/commission"
}

# IAM Policy for reading secrets
resource "aws_iam_policy" "secrets_read" {
  name        = "${local.name_prefix}-secrets-read"
  description = "Allow reading Execution Market secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/*"
        ]
      }
    ]
  })
}
