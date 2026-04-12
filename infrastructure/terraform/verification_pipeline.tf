# Execution Market Infrastructure - SQS + Lambda Verification Pipeline
#
# Extracts Ring 1 (PHOTINT image forensics) and Ring 2 (Arbiter LLM evaluation)
# from asyncio.create_task() in the ECS web server into dedicated Lambda
# functions triggered by SQS queues. This prevents deploys from killing
# in-flight verification jobs and stops AI inference from saturating the
# event loop.
#
# Architecture:
#   ECS (MCP server) --SendMessage--> SQS --trigger--> Lambda (worker)
#
# Ring 1: Image forensics (EXIF, perceptual hash, GPS, AI semantic)
# Ring 2: Arbiter LLM dual-inference verdict (approve/reject/escalate)

# ── SQS Queues ──────────────────────────────────────────────────────────────

# Ring 1: PHOTINT verification queue
resource "aws_sqs_queue" "ring1_dlq" {
  name                      = "${local.name_prefix}-ring1-verification-dlq"
  message_retention_seconds = 1209600 # 14 days
  receive_wait_time_seconds = 0

  tags = {
    Name = "${local.name_prefix}-ring1-verification-dlq"
    Ring = "1"
  }
}

resource "aws_sqs_queue" "ring1" {
  name                       = "${local.name_prefix}-ring1-verification"
  visibility_timeout_seconds = 360    # 6 min — must exceed Lambda timeout (300s)
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ring1_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name = "${local.name_prefix}-ring1-verification"
    Ring = "1"
  }
}

# Ring 2: Arbiter LLM evaluation queue
resource "aws_sqs_queue" "ring2_dlq" {
  name                      = "${local.name_prefix}-ring2-arbiter-dlq"
  message_retention_seconds = 1209600 # 14 days
  receive_wait_time_seconds = 0

  tags = {
    Name = "${local.name_prefix}-ring2-arbiter-dlq"
    Ring = "2"
  }
}

resource "aws_sqs_queue" "ring2" {
  name                       = "${local.name_prefix}-ring2-arbiter"
  visibility_timeout_seconds = 240    # 4 min — must exceed Lambda timeout (180s)
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ring2_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name = "${local.name_prefix}-ring2-arbiter"
    Ring = "2"
  }
}

# ── ECR Repositories ────────────────────────────────────────────────────────

resource "aws_ecr_repository" "ring1_worker" {
  name                 = "${local.name_prefix}-ring1-worker"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "${local.name_prefix}-ring1-worker"
  }
}

resource "aws_ecr_repository" "ring2_worker" {
  name                 = "${local.name_prefix}-ring2-worker"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "${local.name_prefix}-ring2-worker"
  }
}

resource "aws_ecr_lifecycle_policy" "ring1_worker" {
  repository = aws_ecr_repository.ring1_worker.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 5 tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["latest", "v"]
          countType     = "imageCountMoreThan"
          countNumber   = 5
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Expire untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "ring2_worker" {
  repository = aws_ecr_repository.ring2_worker.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 5 tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["latest", "v"]
          countType     = "imageCountMoreThan"
          countNumber   = 5
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Expire untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ── Lambda IAM Role (shared by both Ring 1 and Ring 2) ──────────────────────

resource "aws_iam_role" "verification_lambda" {
  name = "${local.name_prefix}-verification-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-verification-lambda"
  }
}

# SQS: receive/delete from work queues, send to DLQ (handled by redrive, but
# explicit for clarity)
resource "aws_iam_role_policy" "verification_lambda_sqs" {
  name = "${local.name_prefix}-verification-lambda-sqs"
  role = aws_iam_role.verification_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SQSConsumeMessages"
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility"
        ]
        Resource = [
          aws_sqs_queue.ring1.arn,
          aws_sqs_queue.ring2.arn
        ]
      },
      {
        Sid    = "SQSSendToDLQ"
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = [
          aws_sqs_queue.ring1_dlq.arn,
          aws_sqs_queue.ring2_dlq.arn
        ]
      }
    ]
  })
}

# Secrets Manager: read em/* secrets (API keys for AI providers, Supabase, etc.)
resource "aws_iam_role_policy" "verification_lambda_secrets" {
  name = "${local.name_prefix}-verification-lambda-secrets"
  role = aws_iam_role.verification_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SecretsManagerRead"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/*"
        ]
      }
    ]
  })
}

# CloudWatch Logs: write logs
resource "aws_iam_role_policy" "verification_lambda_logs" {
  name = "${local.name_prefix}-verification-lambda-logs"
  role = aws_iam_role.verification_lambda.id

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
        Resource = [
          "${aws_cloudwatch_log_group.ring1_worker.arn}:*",
          "${aws_cloudwatch_log_group.ring2_worker.arn}:*"
        ]
      }
    ]
  })
}

# S3: read evidence images for verification
resource "aws_iam_role_policy" "verification_lambda_s3" {
  name = "${local.name_prefix}-verification-lambda-s3"
  role = aws_iam_role.verification_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EvidenceS3Read"
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "arn:aws:s3:::${local.evidence_bucket_name}/*"
        ]
      }
    ]
  })
}

# ── CloudWatch Log Groups ───────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "ring1_worker" {
  name              = "/aws/lambda/${local.name_prefix}-ring1-worker"
  retention_in_days = 14

  tags = {
    Name = "${local.name_prefix}-ring1-worker-logs"
    Ring = "1"
  }
}

resource "aws_cloudwatch_log_group" "ring2_worker" {
  name              = "/aws/lambda/${local.name_prefix}-ring2-worker"
  retention_in_days = 14

  tags = {
    Name = "${local.name_prefix}-ring2-worker-logs"
    Ring = "2"
  }
}

# ── Lambda Functions ────────────────────────────────────────────────────────

resource "aws_lambda_function" "ring1_worker" {
  function_name = "${local.name_prefix}-ring1-worker"
  role          = aws_iam_role.verification_lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.ring1_worker.repository_url}:latest"

  memory_size                    = 1024
  timeout                        = 300 # 5 min — EXIF extraction + AI inference
  reserved_concurrent_executions = 5

  environment {
    variables = {
      LOG_LEVEL                = "INFO"
      AI_VERIFICATION_PROVIDER = "gemini"
      LLM_INFERENCE_TIMEOUT    = "120"
      EVIDENCE_BUCKET          = local.evidence_bucket_name
      RING                     = "1"
      GIT_SHA                  = var.git_sha
      BUILD_TIMESTAMP          = var.build_timestamp
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.ring1_worker,
    aws_iam_role_policy.verification_lambda_logs,
    aws_iam_role_policy.verification_lambda_sqs,
    aws_iam_role_policy.verification_lambda_secrets,
    aws_iam_role_policy.verification_lambda_s3,
  ]

  tags = {
    Name = "${local.name_prefix}-ring1-worker"
    Ring = "1"
  }

  # Lambda won't deploy until an image is pushed to ECR.
  # On first `terraform apply` this will fail — push the image first:
  #   docker build -t ring1-worker lambda/ring1/
  #   docker tag ring1-worker:latest <ECR_URI>:latest
  #   docker push <ECR_URI>:latest
  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_lambda_function" "ring2_worker" {
  function_name = "${local.name_prefix}-ring2-worker"
  role          = aws_iam_role.verification_lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.ring2_worker.repository_url}:latest"

  memory_size                    = 512
  timeout                        = 180 # 3 min — LLM dual-inference
  reserved_concurrent_executions = 5

  environment {
    variables = {
      LOG_LEVEL             = "INFO"
      LLM_INFERENCE_TIMEOUT = "90"
      RING                  = "2"
      GIT_SHA               = var.git_sha
      BUILD_TIMESTAMP       = var.build_timestamp
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.ring2_worker,
    aws_iam_role_policy.verification_lambda_logs,
    aws_iam_role_policy.verification_lambda_sqs,
    aws_iam_role_policy.verification_lambda_secrets,
    aws_iam_role_policy.verification_lambda_s3,
  ]

  tags = {
    Name = "${local.name_prefix}-ring2-worker"
    Ring = "2"
  }

  lifecycle {
    ignore_changes = [image_uri]
  }
}

# ── Event Source Mappings (SQS -> Lambda) ───────────────────────────────────

resource "aws_lambda_event_source_mapping" "ring1" {
  event_source_arn = aws_sqs_queue.ring1.arn
  function_name    = aws_lambda_function.ring1_worker.arn
  batch_size       = 1
  enabled          = true

  depends_on = [
    aws_iam_role_policy.verification_lambda_sqs
  ]
}

resource "aws_lambda_event_source_mapping" "ring2" {
  event_source_arn = aws_sqs_queue.ring2.arn
  function_name    = aws_lambda_function.ring2_worker.arn
  batch_size       = 1
  enabled          = true

  depends_on = [
    aws_iam_role_policy.verification_lambda_sqs
  ]
}

# ── CloudWatch Alarms (DLQ poison-pill detection) ──────────────────────────

resource "aws_cloudwatch_metric_alarm" "ring1_dlq_messages" {
  alarm_name          = "${local.name_prefix}-ring1-dlq-messages"
  alarm_description   = "Ring 1 DLQ has messages — verification failures need investigation"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.ring1_dlq.name
  }

  alarm_actions = [aws_sns_topic.mcp_alerts.arn]
  ok_actions    = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-ring1-dlq-messages"
    Severity = "warning"
    Ring     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "ring2_dlq_messages" {
  alarm_name          = "${local.name_prefix}-ring2-dlq-messages"
  alarm_description   = "Ring 2 DLQ has messages — arbiter evaluation failures need investigation"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.ring2_dlq.name
  }

  alarm_actions = [aws_sns_topic.mcp_alerts.arn]
  ok_actions    = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-ring2-dlq-messages"
    Severity = "warning"
    Ring     = "2"
  }
}

# ── ECS Task Role: SQS SendMessage permission ──────────────────────────────
# The MCP server (ECS) needs to enqueue verification jobs to SQS.

resource "aws_iam_role_policy" "ecs_task_sqs" {
  name = "${local.name_prefix}-ecs-task-sqs"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SQSSendVerificationJobs"
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueUrl",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.ring1.arn,
          aws_sqs_queue.ring2.arn
        ]
      }
    ]
  })
}
# trigger terraform apply
# force terraform 1776022422
