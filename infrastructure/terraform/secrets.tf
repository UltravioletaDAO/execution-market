# Execution Market Infrastructure - Secrets Reference
#
# Existing secrets are managed manually in AWS Secrets Manager.
# NOTE: Secret paths kept as "chamba/*" to match existing AWS resources:
#   - chamba/supabase (url, anon_key, service_key)
#   - chamba/contracts (avalanche, etc.)
#   - chamba/commission (address)
#   - chamba/x402 (private_key)
#   - chamba/anthropic (api_key)
#
# This file only creates IAM policies for accessing these secrets.

# Data sources for existing secrets
data "aws_secretsmanager_secret" "supabase" {
  name = "chamba/supabase"
}

data "aws_secretsmanager_secret" "contracts" {
  name = "chamba/contracts"
}

data "aws_secretsmanager_secret" "commission" {
  name = "chamba/commission"
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
          "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:chamba/*"
        ]
      }
    ]
  })
}
