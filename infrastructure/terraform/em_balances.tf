# Execution Market - USDC balances Lambda for the dashboard wallet panel.
#
# Why:
#   Under ADR-001 the dashboard reads each worker's live USDC balance per chain.
#   The hook used to call public RPCs directly via viem `http()`, which was
#   rate-limited and flooded WalletSection with "RPC error" pills. This Lambda
#   holds the private QuikNode URLs (already in `facilitator-rpc-mainnet`) and
#   exposes only the result to the browser through a CORS-locked Function URL.
#
# Trust boundary:
#   - Wallet param is public information; no PII leaves the browser.
#   - Private RPC URLs never reach the client; they stay in Secrets Manager,
#     fetched on cold start and cached in-process.
#   - Function URL is `AWS_IAM = NONE` because balances of any address are
#     public on-chain data — no auth needed. CORS is the access control.

locals {
  em_balances_function_name = "${local.name_prefix}-balances"
}

resource "aws_iam_role" "em_balances_lambda" {
  count = var.enable_em_balances_lambda ? 1 : 0
  name  = "${local.name_prefix}-balances-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "em_balances_lambda" {
  count = var.enable_em_balances_lambda ? 1 : 0
  name  = "${local.name_prefix}-balances-lambda-policy"
  role  = aws_iam_role.em_balances_lambda[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Sid      = "ReadFacilitatorRpcSecret"
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:facilitator-rpc-mainnet*"
      },
    ]
  })
}

data "archive_file" "em_balances_lambda" {
  count       = var.enable_em_balances_lambda ? 1 : 0
  type        = "zip"
  source_file = "${path.module}/lambda/em_balances.py"
  output_path = "${path.module}/lambda/em_balances.zip"
}

resource "aws_cloudwatch_log_group" "em_balances_lambda" {
  count             = var.enable_em_balances_lambda ? 1 : 0
  name              = "/aws/lambda/${local.em_balances_function_name}"
  retention_in_days = 14

  tags = {
    Name    = "${local.name_prefix}-balances-logs"
    Purpose = "wallet-balances-lambda"
  }
}

resource "aws_lambda_function" "em_balances" {
  count = var.enable_em_balances_lambda ? 1 : 0

  function_name = local.em_balances_function_name
  role          = aws_iam_role.em_balances_lambda[0].arn
  handler       = "em_balances.lambda_handler"
  runtime       = "python3.12"

  filename         = data.archive_file.em_balances_lambda[0].output_path
  source_code_hash = data.archive_file.em_balances_lambda[0].output_base64sha256
  # Concurrent calls to 7 RPCs * up to 3 fallbacks each; 8s per RPC timeout.
  # 30s leaves headroom for cold start + Secrets Manager fetch.
  timeout     = 30
  memory_size = 256

  environment {
    variables = {
      # Secret name is hardcoded in the handler (`facilitator-rpc-mainnet`),
      # but we expose git_sha here so we can correlate logs with deploys.
      EM_BALANCES_GIT_SHA = var.git_sha
    }
  }

  depends_on = [aws_cloudwatch_log_group.em_balances_lambda]

  tags = {
    Name    = "${local.name_prefix}-balances"
    Purpose = "wallet-balances-lambda"
  }
}

resource "aws_lambda_function_url" "em_balances" {
  count              = var.enable_em_balances_lambda ? 1 : 0
  function_name      = aws_lambda_function.em_balances[0].function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = false
    allow_origins     = var.em_balances_allowed_origins
    allow_methods     = ["GET"]
    allow_headers     = ["content-type"]
    expose_headers    = ["cache-control"]
    max_age           = 3600
  }
}

output "em_balances_lambda_url" {
  description = "Function URL of the EM balances Lambda. Set as VITE_BALANCES_LAMBDA_URL in the dashboard build."
  value       = var.enable_em_balances_lambda ? aws_lambda_function_url.em_balances[0].function_url : null
}
