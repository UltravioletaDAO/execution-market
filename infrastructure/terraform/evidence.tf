# Execution Market Infrastructure - Evidence Upload and Delivery (optional)
#
# Stack:
#   API Gateway (HTTP) -> Lambda (presigned URLs) -> S3 (private evidence) -> CloudFront CDN
#
# Notes:
# - Entire stack is behind `enable_evidence_pipeline`.
# - Custom domain (e.g. storage.execution.market) is enabled only when
#   `evidence_acm_certificate_arn` is provided (must be ACM cert in us-east-1).

locals {
  evidence_bucket_name         = var.evidence_bucket_name != "" ? var.evidence_bucket_name : lower("${local.name_prefix}-evidence-${local.account_id}")
  evidence_custom_domain_name  = "${var.evidence_subdomain}.${var.domain}"
  evidence_custom_domain_ready = var.enable_evidence_pipeline && var.evidence_acm_certificate_arn != ""
}

resource "aws_s3_bucket" "evidence" {
  count  = var.enable_evidence_pipeline ? 1 : 0
  bucket = local.evidence_bucket_name

  tags = {
    Name    = "${local.name_prefix}-evidence"
    Purpose = "evidence-storage"
  }
}

resource "aws_s3_bucket_public_access_block" "evidence" {
  count                   = var.enable_evidence_pipeline ? 1 : 0
  bucket                  = aws_s3_bucket.evidence[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "evidence" {
  count  = var.enable_evidence_pipeline ? 1 : 0
  bucket = aws_s3_bucket.evidence[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "evidence" {
  count  = var.enable_evidence_pipeline ? 1 : 0
  bucket = aws_s3_bucket.evidence[0].bucket

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_ownership_controls" "evidence" {
  count  = var.enable_evidence_pipeline ? 1 : 0
  bucket = aws_s3_bucket.evidence[0].id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_cors_configuration" "evidence" {
  count  = var.enable_evidence_pipeline ? 1 : 0
  bucket = aws_s3_bucket.evidence[0].id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD", "PUT", "POST"]
    allowed_origins = var.evidence_allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "evidence" {
  count  = var.enable_evidence_pipeline ? 1 : 0
  bucket = aws_s3_bucket.evidence[0].id

  rule {
    id     = "evidence-retention"
    status = "Enabled"

    filter {}

    dynamic "expiration" {
      for_each = var.evidence_retention_days > 0 ? [1] : []
      content {
        days = var.evidence_retention_days
      }
    }
  }
}

resource "aws_cloudfront_origin_access_control" "evidence" {
  count                             = var.enable_evidence_pipeline ? 1 : 0
  name                              = "${local.name_prefix}-evidence-oac"
  description                       = "OAC for evidence bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "evidence" {
  count   = var.enable_evidence_pipeline ? 1 : 0
  enabled = true

  aliases = local.evidence_custom_domain_ready ? [local.evidence_custom_domain_name] : []

  origin {
    domain_name              = aws_s3_bucket.evidence[0].bucket_regional_domain_name
    origin_id                = "s3-evidence-origin"
    origin_access_control_id = aws_cloudfront_origin_access_control.evidence[0].id
  }

  default_cache_behavior {
    target_origin_id         = "s3-evidence-origin"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS"]
    cached_methods           = ["GET", "HEAD", "OPTIONS"]
    compress                 = true
    cache_policy_id          = "658327ea-f89d-4fab-a63d-7e88639e58f6" # Managed-CachingOptimized
    origin_request_policy_id = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf" # Managed-CORS-S3Origin
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn            = local.evidence_custom_domain_ready ? var.evidence_acm_certificate_arn : null
    cloudfront_default_certificate = local.evidence_custom_domain_ready ? false : true
    ssl_support_method             = local.evidence_custom_domain_ready ? "sni-only" : null
    minimum_protocol_version       = local.evidence_custom_domain_ready ? "TLSv1.2_2021" : null
  }

  price_class = "PriceClass_100"

  tags = {
    Name    = "${local.name_prefix}-evidence-cdn"
    Purpose = "evidence-delivery"
  }
}

resource "aws_s3_bucket_policy" "evidence" {
  count  = var.enable_evidence_pipeline ? 1 : 0
  bucket = aws_s3_bucket.evidence[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontRead"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.evidence[0].arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = [
              aws_cloudfront_distribution.evidence[0].arn,
              aws_cloudfront_distribution.dashboard.arn,
            ]
          }
        }
      }
    ]
  })
}

resource "aws_route53_record" "evidence_storage" {
  count   = local.evidence_custom_domain_ready ? 1 : 0
  zone_id = data.aws_route53_zone.main.zone_id
  name    = local.evidence_custom_domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.evidence[0].domain_name
    zone_id                = aws_cloudfront_distribution.evidence[0].hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_iam_role" "evidence_lambda" {
  count = var.enable_evidence_pipeline ? 1 : 0
  name  = "${local.name_prefix}-evidence-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "evidence_lambda" {
  count = var.enable_evidence_pipeline ? 1 : 0
  name  = "${local.name_prefix}-evidence-lambda-policy"
  role  = aws_iam_role.evidence_lambda[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Sid    = "EvidenceBucketAccess"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.evidence[0].arn}/*"
      }
    ]
  })
}

data "archive_file" "evidence_lambda" {
  count       = var.enable_evidence_pipeline ? 1 : 0
  type        = "zip"
  source_file = "${path.module}/lambda/evidence_presign.py"
  output_path = "${path.module}/lambda/evidence_presign.zip"
}

resource "aws_lambda_function" "evidence_presign" {
  count = var.enable_evidence_pipeline ? 1 : 0

  function_name = "${local.name_prefix}-evidence-presign"
  role          = aws_iam_role.evidence_lambda[0].arn
  handler       = "evidence_presign.handler"
  runtime       = "python3.12"

  filename         = data.archive_file.evidence_lambda[0].output_path
  source_code_hash = data.archive_file.evidence_lambda[0].output_base64sha256
  timeout          = 15
  memory_size      = 256

  environment {
    variables = {
      EVIDENCE_BUCKET          = aws_s3_bucket.evidence[0].id
      EVIDENCE_PUBLIC_BASE_URL = local.evidence_custom_domain_ready ? "https://${local.evidence_custom_domain_name}" : "https://${aws_cloudfront_distribution.evidence[0].domain_name}"
      PRESIGN_EXPIRES_SECONDS  = tostring(var.evidence_presign_expiry_seconds)
      MAX_UPLOAD_MB            = tostring(var.evidence_max_upload_mb)
    }
  }
}

# ----------------------------------------------------------------------------
# Phase 0 GR-0.4 (CLOUD-003): JWT Lambda authorizer for the evidence API.
#
# The presign API was previously unauthenticated — anyone on the internet
# could mint S3 PUT/GET URLs. This authorizer enforces a short-lived HS256
# JWT minted by the backend MCP server after ERC-8128 verification. The JWT
# is scoped to (task_id, submission_id, actor_id, exp).
#
# DEPENDENCY: the backend MCP server must implement `mint_evidence_jwt`
# (Track D2) and expose it to clients before this authorizer is deployed,
# otherwise legitimate evidence uploads will fail with 401 / 403.
# ----------------------------------------------------------------------------

resource "aws_secretsmanager_secret" "evidence_jwt_secret" {
  count                   = var.enable_evidence_pipeline ? 1 : 0
  name                    = "em/evidence-jwt-secret"
  description             = "HS256 signing key for the evidence presign API Gateway authorizer (Phase 0 GR-0.4 CLOUD-003). Shared with the backend MCP server's mint_evidence_jwt() helper."
  recovery_window_in_days = 7

  tags = {
    Name    = "${local.name_prefix}-evidence-jwt-secret"
    Purpose = "evidence-authorizer"
  }
}

# Generate an initial random signing key so `terraform apply` is self-contained.
# Operators can rotate out-of-band with `aws secretsmanager put-secret-value`;
# the `lifecycle { ignore_changes }` block below prevents Terraform from
# overwriting rotated values on subsequent applies.
resource "random_password" "evidence_jwt_secret" {
  count            = var.enable_evidence_pipeline ? 1 : 0
  length           = 64
  special          = true
  override_special = "!@#$%^&*()-_=+[]{}"
}

resource "aws_secretsmanager_secret_version" "evidence_jwt_secret" {
  count         = var.enable_evidence_pipeline ? 1 : 0
  secret_id     = aws_secretsmanager_secret.evidence_jwt_secret[0].id
  secret_string = random_password.evidence_jwt_secret[0].result

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_iam_role" "evidence_authorizer_lambda" {
  count = var.enable_evidence_pipeline ? 1 : 0
  name  = "${local.name_prefix}-evidence-authorizer-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "evidence_authorizer_lambda" {
  count = var.enable_evidence_pipeline ? 1 : 0
  name  = "${local.name_prefix}-evidence-authorizer-lambda-policy"
  role  = aws_iam_role.evidence_authorizer_lambda[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Sid    = "ReadEvidenceJWTSecret"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.evidence_jwt_secret[0].arn
      }
    ]
  })
}

data "archive_file" "evidence_authorizer_lambda" {
  count       = var.enable_evidence_pipeline ? 1 : 0
  type        = "zip"
  source_file = "${path.module}/lambda/evidence_presign_authorizer.py"
  output_path = "${path.module}/lambda/evidence_presign_authorizer.zip"
}

resource "aws_lambda_function" "evidence_authorizer" {
  count = var.enable_evidence_pipeline ? 1 : 0

  function_name = "${local.name_prefix}-evidence-authorizer"
  role          = aws_iam_role.evidence_authorizer_lambda[0].arn
  handler       = "evidence_presign_authorizer.lambda_handler"
  runtime       = "python3.12"

  filename         = data.archive_file.evidence_authorizer_lambda[0].output_path
  source_code_hash = data.archive_file.evidence_authorizer_lambda[0].output_base64sha256
  timeout          = 5
  memory_size      = 128

  # The Lambda fetches the secret from Secrets Manager at cold start using
  # the ARN below. This keeps the plaintext secret out of Lambda env vars,
  # matches the repo convention (see CLAUDE.md "Secrets Manager" guidance),
  # and allows rotation without redeploying the Lambda.
  environment {
    variables = {
      EM_EVIDENCE_JWT_SECRET_ARN = aws_secretsmanager_secret.evidence_jwt_secret[0].arn
    }
  }

  depends_on = [aws_secretsmanager_secret_version.evidence_jwt_secret]

  tags = {
    Name    = "${local.name_prefix}-evidence-authorizer"
    Purpose = "evidence-authorizer"
  }
}

resource "aws_apigatewayv2_api" "evidence" {
  count         = var.enable_evidence_pipeline ? 1 : 0
  name          = "${local.name_prefix}-evidence-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = var.evidence_allowed_origins
    allow_methods = ["GET", "OPTIONS"]
    allow_headers = ["content-type", "authorization", "x-evidence-token"]
    max_age       = 3600
  }
}

resource "aws_apigatewayv2_integration" "evidence_lambda" {
  count                  = var.enable_evidence_pipeline ? 1 : 0
  api_id                 = aws_apigatewayv2_api.evidence[0].id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.evidence_presign[0].invoke_arn
  payload_format_version = "2.0"
}

# Phase 0 GR-0.4 (CLOUD-003): JWT authorizer wired to the evidence HTTP API.
# authorization_type = "CUSTOM" + authorizer_id on each route enforces that
# every request carries a valid, unexpired, task-bound JWT.
resource "aws_apigatewayv2_authorizer" "evidence_jwt" {
  count                             = var.enable_evidence_pipeline ? 1 : 0
  api_id                            = aws_apigatewayv2_api.evidence[0].id
  authorizer_type                   = "REQUEST"
  identity_sources                  = ["$request.header.Authorization"]
  name                              = "evidence-jwt-authorizer"
  authorizer_uri                    = aws_lambda_function.evidence_authorizer[0].invoke_arn
  authorizer_payload_format_version = "2.0"
  enable_simple_responses           = true
  authorizer_result_ttl_in_seconds  = 0 # disable caching — JWT task_id cross-check must run per-request
}

resource "aws_lambda_permission" "apigw_invoke_evidence_authorizer" {
  count         = var.enable_evidence_pipeline ? 1 : 0
  statement_id  = "AllowExecutionFromAPIGatewayEvidenceAuthorizer"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.evidence_authorizer[0].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.evidence[0].execution_arn}/authorizers/${aws_apigatewayv2_authorizer.evidence_jwt[0].id}"
}

resource "aws_apigatewayv2_route" "upload_url" {
  count              = var.enable_evidence_pipeline ? 1 : 0
  api_id             = aws_apigatewayv2_api.evidence[0].id
  route_key          = "GET /upload-url"
  target             = "integrations/${aws_apigatewayv2_integration.evidence_lambda[0].id}"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.evidence_jwt[0].id
}

resource "aws_apigatewayv2_route" "download_url" {
  count              = var.enable_evidence_pipeline ? 1 : 0
  api_id             = aws_apigatewayv2_api.evidence[0].id
  route_key          = "GET /download-url"
  target             = "integrations/${aws_apigatewayv2_integration.evidence_lambda[0].id}"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.evidence_jwt[0].id
}

resource "aws_apigatewayv2_stage" "evidence_default" {
  count       = var.enable_evidence_pipeline ? 1 : 0
  api_id      = aws_apigatewayv2_api.evidence[0].id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 50
    throttling_rate_limit  = 25
  }
}

resource "aws_lambda_permission" "apigw_invoke_evidence" {
  count         = var.enable_evidence_pipeline ? 1 : 0
  statement_id  = "AllowExecutionFromAPIGatewayEvidence"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.evidence_presign[0].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.evidence[0].execution_arn}/*/*"
}
