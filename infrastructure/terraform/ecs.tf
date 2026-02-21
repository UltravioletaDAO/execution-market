# Execution Market Infrastructure - ECS Configuration

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${local.name_prefix}-cluster"
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 1
  }
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_execution" {
  name = "${local.name_prefix}-ecs-execution"

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
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Secrets Manager access for task execution
resource "aws_iam_role_policy" "ecs_secrets" {
  name = "${local.name_prefix}-ecs-secrets"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
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

# ECS Task Role
resource "aws_iam_role" "ecs_task" {
  name = "${local.name_prefix}-ecs-task"

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
}

# S3 access for feedback documents and evidence uploads
resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "${local.name_prefix}-ecs-task-s3"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EvidenceBucketReadWrite"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${local.evidence_bucket_name}",
          "arn:aws:s3:::${local.evidence_bucket_name}/*"
        ]
      }
    ]
  })
}

# Security Groups
resource "aws_security_group" "ecs" {
  name        = "${local.name_prefix}-ecs-sg"
  description = "Security group for ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-ecs-sg"
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "mcp_server" {
  name              = "/ecs/${local.name_prefix}/mcp-server"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "dashboard" {
  name              = "/ecs/${local.name_prefix}/dashboard"
  retention_in_days = 30
}

# MCP Server Task Definition
resource "aws_ecs_task_definition" "mcp_server" {
  family                   = "${local.name_prefix}-mcp-server"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.mcp_server_cpu
  memory                   = var.mcp_server_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "mcp-server"
      image     = var.mcp_server_image != "" ? var.mcp_server_image : "${aws_ecr_repository.mcp_server.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "ENVIRONMENT", value = var.environment },
        { name = "PORT", value = "8000" },
        { name = "EM_BASE_URL", value = "https://api.execution.market" },
        { name = "ERC8004_NETWORK", value = "base" },
        { name = "EM_AGENT_ID", value = "2106" },
        { name = "EM_PAYMENT_MODE", value = "fase2" },
        { name = "EM_ESCROW_MODE", value = "direct_release" },
        { name = "EM_FEE_MODEL", value = "credit_card" },
        { name = "EM_PAYMENT_OPERATOR", value = "0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb" },
        { name = "EM_ENABLED_NETWORKS", value = "base,ethereum,polygon,arbitrum,celo,monad,avalanche,optimism" },
        { name = "EVIDENCE_BUCKET", value = local.evidence_bucket_name },
        { name = "EVIDENCE_PUBLIC_BASE_URL", value = var.enable_evidence_pipeline ? "https://${aws_cloudfront_distribution.evidence[0].domain_name}" : "https://${local.evidence_bucket_name}.s3.amazonaws.com" },
        { name = "EM_FEEDBACK_BASE_URL", value = "https://execution.market" },
        { name = "ERC8128_NONCE_STORE", value = "dynamodb" },
      ]

      secrets = [
        {
          name      = "SUPABASE_URL"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/supabase:SUPABASE_URL::"
        },
        {
          name      = "SUPABASE_ANON_KEY"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/supabase:SUPABASE_ANON_KEY::"
        },
        {
          name      = "SUPABASE_SERVICE_KEY"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/supabase:SUPABASE_SERVICE_ROLE_KEY::"
        },
        {
          name      = "EM_ADMIN_KEY"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/admin-key"
        },
        {
          name      = "ANTHROPIC_API_KEY"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/anthropic:ANTHROPIC_API_KEY::"
        },
        {
          name      = "WALLET_PRIVATE_KEY"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/x402:PRIVATE_KEY::"
        },
        {
          name      = "X402_NETWORK"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/x402:X402_NETWORK::"
        },
        {
          name      = "X402_RPC_URL"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/x402:X402_RPC_URL::"
        },
        {
          name      = "X402_FACILITATOR_URL"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/x402:FACILITATOR_URL::"
        },
        {
          name      = "EM_ESCROW_ADDRESS"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/x402:X402R_ESCROW::"
        },
        {
          name      = "USDC_ADDRESS"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/x402:USDC_ADDRESS::"
        },
        {
          name      = "EM_TREASURY_ADDRESS"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/commission:wallet_address::"
        },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.mcp_server.name
          awslogs-region        = local.region
          awslogs-stream-prefix = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

# Dashboard Task Definition
resource "aws_ecs_task_definition" "dashboard" {
  family                   = "${local.name_prefix}-dashboard"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.dashboard_cpu
  memory                   = var.dashboard_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "dashboard"
      image     = var.dashboard_image != "" ? var.dashboard_image : "${aws_ecr_repository.dashboard.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 80
          hostPort      = 80
          protocol      = "tcp"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.dashboard.name
          awslogs-region        = local.region
          awslogs-stream-prefix = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "wget -q --spider http://localhost:80/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }
    }
  ])
}

# MCP Server Service
resource "aws_ecs_service" "mcp_server" {
  name            = "${local.name_prefix}-mcp-server"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.mcp_server.arn
  desired_count   = var.desired_count

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 1
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.mcp_server.arn
    container_name   = "mcp-server"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.https]

  lifecycle {
    ignore_changes = [desired_count]
  }
}

# Dashboard Service
resource "aws_ecs_service" "dashboard" {
  name            = "${local.name_prefix}-dashboard"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.dashboard.arn
  desired_count   = var.desired_count

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 1
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.dashboard.arn
    container_name   = "dashboard"
    container_port   = 80
  }

  depends_on = [aws_lb_listener.https]

  lifecycle {
    ignore_changes = [desired_count]
  }
}
