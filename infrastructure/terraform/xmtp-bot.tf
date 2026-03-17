# ─── XMTP Bot Infrastructure ────────────────────────────────
# All resources for the standalone XMTP bot ECS service.
# References existing VPC, ECS cluster, and execution role from main infra.
# CRITICAL: XMTP SQLite DB MUST persist via EFS. Losing it burns 1 of 10
# installation slots — there is no recovery mechanism.

# ─── ECR Repository (XMTP-6.2) ──────────────────────────────

resource "aws_ecr_repository" "xmtp_bot" {
  name                 = "${local.name_prefix}-xmtp-bot"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name    = "${local.name_prefix}-xmtp-bot"
    Service = "xmtp-bot"
  }
}

resource "aws_ecr_lifecycle_policy" "xmtp_bot" {
  repository = aws_ecr_repository.xmtp_bot.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ─── EFS Filesystem (XMTP-6.3) ──────────────────────────────
# CRITICAL: XMTP SQLite DB MUST persist. Losing it burns 1 of 10
# installation slots — there is no recovery mechanism.

resource "aws_efs_file_system" "xmtp_bot" {
  creation_token = "${local.name_prefix}-xmtp-bot-data"
  encrypted      = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = {
    Name    = "${local.name_prefix}-xmtp-bot-data"
    Service = "xmtp-bot"
  }
}

resource "aws_efs_backup_policy" "xmtp_bot" {
  file_system_id = aws_efs_file_system.xmtp_bot.id

  backup_policy {
    status = "ENABLED"
  }
}

resource "aws_efs_access_point" "xmtp_bot" {
  file_system_id = aws_efs_file_system.xmtp_bot.id

  posix_user {
    uid = 1001
    gid = 1001
  }

  root_directory {
    path = "/xmtp"
    creation_info {
      owner_uid   = 1001
      owner_gid   = 1001
      permissions = "750"
    }
  }

  tags = {
    Name    = "${local.name_prefix}-xmtp-bot-ap"
    Service = "xmtp-bot"
  }
}

# Mount targets in private subnets
resource "aws_efs_mount_target" "xmtp_bot" {
  count           = length(aws_subnet.private)
  file_system_id  = aws_efs_file_system.xmtp_bot.id
  subnet_id       = aws_subnet.private[count.index].id
  security_groups = [aws_security_group.efs_xmtp.id]
}

# ─── Security Groups (XMTP-6.6) ─────────────────────────────

resource "aws_security_group" "xmtp_bot" {
  name_prefix = "${local.name_prefix}-xmtp-bot-"
  description = "XMTP bot ECS task - egress only (no inbound needed)"
  vpc_id      = aws_vpc.main.id

  # HTTPS egress (XMTP network + EM API)
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS (XMTP network + EM API)"
  }

  # DNS TCP
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "DNS TCP"
  }

  # DNS UDP
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "DNS UDP"
  }

  # IRC TLS to MeshRelay (irc.meshrelay.xyz:6697)
  egress {
    from_port   = 6697
    to_port     = 6697
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "IRC TLS (MeshRelay)"
  }

  tags = {
    Name    = "${local.name_prefix}-xmtp-bot"
    Service = "xmtp-bot"
  }
}

resource "aws_security_group" "efs_xmtp" {
  name_prefix = "${local.name_prefix}-xmtp-efs-"
  description = "EFS mount target for XMTP bot"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name    = "${local.name_prefix}-xmtp-efs"
    Service = "xmtp-bot"
  }
}

# Break SG cycle with standalone rules
resource "aws_security_group_rule" "xmtp_bot_to_efs" {
  type                     = "egress"
  from_port                = 2049
  to_port                  = 2049
  protocol                 = "tcp"
  security_group_id        = aws_security_group.xmtp_bot.id
  source_security_group_id = aws_security_group.efs_xmtp.id
  description              = "NFS to EFS"
}

resource "aws_security_group_rule" "efs_from_xmtp_bot" {
  type                     = "ingress"
  from_port                = 2049
  to_port                  = 2049
  protocol                 = "tcp"
  security_group_id        = aws_security_group.efs_xmtp.id
  source_security_group_id = aws_security_group.xmtp_bot.id
  description              = "NFS from XMTP bot"
}

# ─── IAM (XMTP-6.7) ─────────────────────────────────────────

resource "aws_iam_role" "xmtp_bot_task" {
  name = "${local.name_prefix}-xmtp-bot-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Service = "xmtp-bot"
  }
}

resource "aws_iam_role_policy" "xmtp_bot_task" {
  name = "${local.name_prefix}-xmtp-bot-task-policy"
  role = aws_iam_role.xmtp_bot_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EFSAccess"
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess"
        ]
        Resource = aws_efs_file_system.xmtp_bot.arn
      },
      {
        Sid    = "ECSExec"
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ]
        Resource = "*"
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.xmtp_bot.arn}:*"
      }
    ]
  })
}

# ─── Secrets (XMTP-6.8) ─────────────────────────────────────

resource "aws_secretsmanager_secret" "xmtp" {
  name        = "em/xmtp"
  description = "XMTP bot secrets (wallet key, DB encryption key, API key)"

  tags = {
    Service = "xmtp-bot"
  }
}

# Placeholder values — operator fills real values post-apply
resource "aws_secretsmanager_secret_version" "xmtp" {
  secret_id = aws_secretsmanager_secret.xmtp.id

  secret_string = jsonencode({
    XMTP_WALLET_KEY        = "YOUR_XMTP_WALLET_KEY_HERE"
    XMTP_DB_ENCRYPTION_KEY = "YOUR_64_HEX_CHARS_HERE"
    EM_API_KEY             = "YOUR_EM_API_KEY_HERE"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# MeshRelay IRC bridge credentials (SASL auth + Identity API)
resource "aws_secretsmanager_secret" "meshrelay" {
  name        = "em/meshrelay"
  description = "MeshRelay IRC bridge credentials (SASL auth)"

  tags = {
    Service = "xmtp-bot"
  }
}

resource "aws_secretsmanager_secret_version" "meshrelay" {
  secret_id = aws_secretsmanager_secret.meshrelay.id

  secret_string = jsonencode({
    IRC_SASL_USER = "em-bot"
    IRC_SASL_PASS = "YOUR_IRC_SASL_PASS_HERE"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# ─── CloudWatch (XMTP-6.9) ──────────────────────────────────

resource "aws_cloudwatch_log_group" "xmtp_bot" {
  name              = "/ecs/${local.name_prefix}/xmtp-bot"
  retention_in_days = 30

  tags = {
    Service = "xmtp-bot"
  }
}

resource "aws_sns_topic" "xmtp_bot_alerts" {
  name = "${local.name_prefix}-xmtp-bot-alerts"

  tags = {
    Service = "xmtp-bot"
  }
}

resource "aws_cloudwatch_metric_alarm" "xmtp_bot_not_running" {
  alarm_name          = "${local.name_prefix}-xmtp-bot-not-running"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RunningTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 300
  statistic           = "Average"
  threshold           = 1
  alarm_description   = "XMTP bot has 0 running tasks for 10 minutes"
  alarm_actions       = [aws_sns_topic.xmtp_bot_alerts.arn]

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.xmtp_bot.name
  }
}

resource "aws_cloudwatch_metric_alarm" "xmtp_bot_memory" {
  alarm_name          = "${local.name_prefix}-xmtp-bot-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "XMTP bot memory utilization > 85% for 15 minutes"
  alarm_actions       = [aws_sns_topic.xmtp_bot_alerts.arn]

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.xmtp_bot.name
  }
}

# ─── ECS Task Definition (XMTP-6.4) ─────────────────────────

resource "aws_ecs_task_definition" "xmtp_bot" {
  family                   = "${local.name_prefix}-xmtp-bot"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.xmtp_bot_cpu
  memory                   = var.xmtp_bot_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.xmtp_bot_task.arn

  # EFS volume for persistent XMTP SQLite DB
  volume {
    name = "xmtp-data"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.xmtp_bot.id
      transit_encryption = "ENABLED"

      authorization_config {
        access_point_id = aws_efs_access_point.xmtp_bot.id
        iam             = "ENABLED"
      }
    }
  }

  container_definitions = jsonencode([
    {
      name      = "xmtp-bot"
      image     = "${aws_ecr_repository.xmtp_bot.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 8090
          protocol      = "tcp"
        }
      ]

      mountPoints = [
        {
          sourceVolume  = "xmtp-data"
          containerPath = "/data/xmtp"
          readOnly      = false
        }
      ]

      environment = [
        { name = "XMTP_ENV", value = "production" },
        { name = "XMTP_DB_PATH", value = "/data/xmtp/bot.db3" },
        { name = "EM_API_URL", value = "https://api.execution.market" },
        { name = "EM_WS_URL", value = "wss://api.execution.market/ws" },
        { name = "HEALTH_PORT", value = "8090" },
        { name = "LOG_LEVEL", value = "info" },
        { name = "NODE_ENV", value = "production" },
        # MeshRelay IRC bridge
        { name = "IRC_ENABLED", value = "true" },
        { name = "IRC_HOST", value = "irc.meshrelay.xyz" },
        { name = "IRC_PORT", value = "6697" },
        { name = "IRC_TLS", value = "true" },
        { name = "IRC_NICK", value = "em-bot" },
        { name = "IRC_CHANNELS", value = "#bounties,#Agents,#execution-market" },
        { name = "MESHRELAY_API_URL", value = "https://api.meshrelay.xyz" },
      ]

      secrets = [
        {
          name      = "XMTP_WALLET_KEY"
          valueFrom = "${aws_secretsmanager_secret.xmtp.arn}:XMTP_WALLET_KEY::"
        },
        {
          name      = "XMTP_DB_ENCRYPTION_KEY"
          valueFrom = "${aws_secretsmanager_secret.xmtp.arn}:XMTP_DB_ENCRYPTION_KEY::"
        },
        {
          name      = "EM_API_KEY"
          valueFrom = "${aws_secretsmanager_secret.xmtp.arn}:EM_API_KEY::"
        },
        # MeshRelay SASL credentials (from Secrets Manager)
        {
          name      = "IRC_SASL_USER"
          valueFrom = "${aws_secretsmanager_secret.meshrelay.arn}:IRC_SASL_USER::"
        },
        {
          name      = "IRC_SASL_PASS"
          valueFrom = "${aws_secretsmanager_secret.meshrelay.arn}:IRC_SASL_PASS::"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.xmtp_bot.name
          "awslogs-region"        = local.region
          "awslogs-stream-prefix" = "xmtp-bot"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:8090/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  tags = {
    Service = "xmtp-bot"
  }
}

# ─── ECS Service (XMTP-6.5) ─────────────────────────────────
# Singleton service — stop old task before starting new (0/100 deployment).
# No load balancer needed — bot connects outbound to XMTP network.

resource "aws_ecs_service" "xmtp_bot" {
  name             = "${local.name_prefix}-xmtp-bot"
  cluster          = aws_ecs_cluster.main.id
  task_definition  = aws_ecs_task_definition.xmtp_bot.arn
  desired_count    = 1
  launch_type      = "FARGATE"
  platform_version = "1.4.0"

  # Singleton — stop old before starting new (avoids duplicate XMTP connections)
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.xmtp_bot.id]
  }

  enable_execute_command = true

  tags = {
    Service = "xmtp-bot"
  }
}

# ─── Variables ───────────────────────────────────────────────

variable "xmtp_bot_cpu" {
  description = "CPU units for XMTP bot task"
  type        = number
  default     = 256
}

variable "xmtp_bot_memory" {
  description = "Memory for XMTP bot task (MB)"
  type        = number
  default     = 512
}

# ─── Outputs ─────────────────────────────────────────────────

output "xmtp_bot_ecr_url" {
  description = "ECR repository URL for XMTP bot"
  value       = aws_ecr_repository.xmtp_bot.repository_url
}

output "xmtp_bot_efs_id" {
  description = "EFS filesystem ID for XMTP bot persistent data"
  value       = aws_efs_file_system.xmtp_bot.id
}

output "xmtp_bot_service_name" {
  description = "XMTP bot ECS service name"
  value       = aws_ecs_service.xmtp_bot.name
}

output "xmtp_bot_secret_arn" {
  description = "Secrets Manager ARN for XMTP bot secrets"
  value       = aws_secretsmanager_secret.xmtp.arn
}
