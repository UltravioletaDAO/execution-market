# =============================================================================
# ERC-8128 Nonce Store — DynamoDB Table
# =============================================================================
#
# Single-use nonce storage for ERC-8128 wallet-based authentication.
# Uses conditional writes for atomic check-and-set and DynamoDB TTL
# for automatic cleanup of expired nonces.
#
# Cost estimate at 1000 agent requests/day: ~$0.04/month
# =============================================================================

resource "aws_dynamodb_table" "nonce_store" {
  name         = "${local.name_prefix}-nonce-store"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "nonce_key"

  attribute {
    name = "nonce_key"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  server_side_encryption {
    enabled = true # AWS-managed CMK (free, encrypted at rest)
  }

  point_in_time_recovery {
    enabled = false # Not needed for ephemeral nonces
  }

  tags = {
    Name        = "${local.name_prefix}-nonce-store"
    Project     = "Execution Market"
    Environment = var.environment
    Purpose     = "ERC-8128 nonce replay protection"
  }
}

# IAM policy for ECS task role to access nonce store
resource "aws_iam_role_policy" "ecs_dynamodb_nonce" {
  name = "${local.name_prefix}-ecs-dynamodb-nonce"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem"
      ]
      Resource = aws_dynamodb_table.nonce_store.arn
    }]
  })
}
