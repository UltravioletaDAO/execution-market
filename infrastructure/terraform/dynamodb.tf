# ERC-8128 Nonce Store — DynamoDB Table
# Single-use nonce storage for ERC-8128 wallet-based authentication.
# Cost estimate at 1000 agent requests/day: ~$0.04/month

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
    enabled = true
  }

  point_in_time_recovery {
    enabled = false
  }

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-nonce-store"
    Purpose = "ERC-8128 nonce replay protection"
  })
}

resource "aws_iam_role_policy" "ecs_dynamodb_nonce" {
  name = "${local.name_prefix}-ecs-dynamodb-nonce"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"]
      Resource = aws_dynamodb_table.nonce_store.arn
    }]
  })
}
