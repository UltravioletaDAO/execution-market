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

# CloudWatch custom-metric emission for verification pipeline counters.
# The ExecutionMarket/Verification namespace is used by background_runner /
# cloudwatch_metrics.py to publish MagikaRejectionRate + MagikaRejectionCount.
# put_metric_data does not support resource-level ARNs, so scoping is enforced
# via the cloudwatch:namespace condition key (same pattern AWS recommends).
resource "aws_iam_role_policy" "ecs_task_cloudwatch_metrics" {
  name = "${local.name_prefix}-ecs-task-cw-metrics"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "PutVerificationCustomMetrics"
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData"]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "ExecutionMarket/Verification"
          }
        }
      }
    ]
  })
}

# Security Groups
# Port 8000 only — MCP server. Port 80 removed (dashboard now served via S3+CloudFront).
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
  retention_in_days = 90
}

# Log group for the ADOT collector sidecar.  Separate stream from the app so
# OTel/X-Ray collector diagnostics don't interleave with the FastAPI JSON logs
# we already query via CloudWatch Insights.  Only created when tracing is on.
resource "aws_cloudwatch_log_group" "mcp_otel_collector" {
  count             = var.otel_enabled ? 1 : 0
  name              = "/ecs/${local.name_prefix}/mcp-otel-collector"
  retention_in_days = 30
}

# X-Ray write access for the task role.  The ADOT collector forwards spans to
# X-Ray using the task role's credentials, so permissions must live on
# ecs_task (the app role), not on the execution role.  Managed policy
# AWSXRayDaemonWriteAccess grants PutTraceSegments + PutTelemetryRecords +
# sampling APIs — exactly what the collector needs.
resource "aws_iam_role_policy_attachment" "ecs_task_xray" {
  count      = var.otel_enabled ? 1 : 0
  role       = aws_iam_role.ecs_task.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Container definition for the ADOT collector.  Defined as a local so we can
# append it to the container_definitions list only when tracing is enabled.
# Image tag is pinned to the AWS-published major "v0.40.x" line to avoid
# transparent upgrades pulling in breaking config changes.  Command uses the
# bundled X-Ray profile (OTLP in → X-Ray out).
locals {
  mcp_otel_sidecar = var.otel_enabled ? [
    {
      name      = "aws-otel-collector"
      image     = "public.ecr.aws/aws-observability/aws-otel-collector:v0.40.1"
      essential = false
      command   = ["--config=/etc/ecs/ecs-xray.yaml"]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.mcp_otel_collector[0].name
          awslogs-region        = local.region
          awslogs-stream-prefix = "otel"
        }
      }

      healthCheck = {
        # Built-in health extension on :13133 — returns 200 when the pipeline
        # is running.  Without this the app container can race the collector
        # and drop the first batch of spans.
        command     = ["CMD-SHELL", "wget -qO- http://localhost:13133/ || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }
    }
  ] : []

  # Single source of truth for whether to push OTel env vars into mcp-server.
  # Keeping this as a local (not a direct var reference) documents the link
  # between the sidecar presence and the env vars — flipping otel_enabled
  # must always move both together, never just one.
  mcp_otel_env = var.otel_enabled ? [
    { name = "OTEL_ENABLED", value = "true" },
    { name = "OTEL_SERVICE_NAME", value = "execution-market-mcp" },
    { name = "OTEL_EXPORTER_OTLP_ENDPOINT", value = "http://localhost:4318" },
    { name = "OTEL_TRACES_SAMPLER_ARG", value = var.otel_traces_sampler_arg },
  ] : []
}

# MCP Server Task Definition
# cpu/memory: 512 CPU (0.5 vCPU) + 1024 MB — AI verification offloaded to Lambda
# (SQS + Lambda pipeline handles Ring 1 + Ring 2 inference since Phase 3).
# ECS only runs the web server, background jobs (escrow polling, task expiry),
# and the SQS publish path.  Halved from 1024/2048 (rev 298) after Lambda offload.
# History: 256/512 → OOM kills. 512/1024 → tight. 1024/2048 → rev 298. 512/1024 → Lambda offload.
resource "aws_ecs_task_definition" "mcp_server" {
  family                   = "${local.name_prefix}-mcp-server"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.mcp_server_cpu
  memory                   = var.mcp_server_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode(concat([
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

      # ``concat`` so flipping var.otel_enabled adds OTEL_* env vars without
      # touching the handwritten block above. The Python bootstrap in
      # mcp_server/observability/tracing.py treats OTEL_ENABLED as the
      # master switch — leaving it unset keeps the code path inert.
      environment = concat([
        { name = "ENVIRONMENT", value = var.environment },
        { name = "PORT", value = "8000" },
        { name = "EM_BASE_URL", value = "https://api.execution.market" },
        { name = "ERC8004_NETWORK", value = "base" },
        { name = "EM_AGENT_ID", value = "2106" },
        { name = "EM_PAYMENT_MODE", value = "fase2" },
        { name = "EM_ESCROW_MODE", value = "direct_release" },
        { name = "EM_FEE_MODEL", value = "credit_card" },
        { name = "EM_PAYMENT_OPERATOR", value = "0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb" },
        { name = "EM_ENABLED_NETWORKS", value = "base,ethereum,polygon,arbitrum,celo,monad,avalanche,optimism,skale" },
        { name = "EVIDENCE_BUCKET", value = local.evidence_bucket_name },
        { name = "EVIDENCE_PUBLIC_BASE_URL", value = var.enable_evidence_pipeline ? "https://${aws_cloudfront_distribution.evidence[0].domain_name}" : "https://${local.evidence_bucket_name}.s3.amazonaws.com" },
        { name = "EM_FEEDBACK_BASE_URL", value = "https://execution.market" },
        { name = "ERC8128_NONCE_STORE", value = "dynamodb" },
        { name = "EM_REQUIRE_ERC8004", value = "true" },
        { name = "EM_REQUIRE_ERC8004_WORKER", value = "true" },
        # VeryAI master switch — Phase 2 ships routes-disabled. When false,
        # /api/v1/very-id/* routes are not even mounted (returns 404, not
        # 503). Flip to "true" only after Phase 6 sandbox testing AND
        # Veros provisions production credentials in em/veryai.
        { name = "EM_VERYAI_ENABLED", value = "false" },
        { name = "EM_GEO_MATCH_ENABLED", value = "true" },
        { name = "VERIFICATION_AI_ENABLED", value = "true" },
        { name = "AI_VERIFICATION_PROVIDER", value = "gemini" },
        { name = "VERIFICATION_AUTO_APPROVE", value = "true" },
        # Phase 0 GR-0.2: hard kill-switches for the Ring 2 arbiter
        # subsystem. Ring 2 LLM is currently a stub (AI-001) and
        # auto-release has no cost cap (AI-004) or prompt hardening
        # (AI-006). Both flags default false at the code level — we set
        # them here explicitly so a misconfigured override cannot enable
        # auto-release or the AaaS endpoint in production without an
        # intentional Terraform change. See
        # docs/reports/security-audit-2026-04-07/.
        { name = "EM_AAAS_ENABLED", value = "true" },                  # Re-enabled: Ring 2 wired, cost controls active, all Phase 0 guardrails in place (2026-04-10)
        { name = "EM_ARBITER_AUTO_RELEASE_ENABLED", value = "false" }, # Stays false: auto-release requires more testing before enabling
        { name = "ARBITER_DAILY_BUDGET_USD", value = "100" },
        { name = "ARBITER_PER_CALLER_BUDGET_USD", value = "10" },
        # Verification pipeline: SQS queue URLs for Ring 1/2 offload (Phase 1)
        # EM_VERIFICATION_BACKEND controls routing: "ecs" (in-process, default)
        # or "sqs" (Lambda workers). Set to "sqs" after Phase 3 migration.
        { name = "EM_VERIFICATION_BACKEND", value = "sqs" },
        { name = "RING1_QUEUE_URL", value = aws_sqs_queue.ring1.url },
        { name = "RING2_QUEUE_URL", value = aws_sqs_queue.ring2.url },
        # Build metadata for Sentry release tracking (Phase 1.5).
        { name = "GIT_SHA", value = var.git_sha },
        # Phase 2.2 SAAS_PRODUCTION_HARDENING — cap on every HTTP call to
        # the Ultravioleta Facilitator (payments + ERC-8004 reputation).
        # Split connect/read/write keeps a stalled phase from exceeding this
        # total.  Paired with @facilitator_retry (3 attempts, exp backoff) in
        # integrations/_http_retry.py so transient transport issues still
        # recover.  Previously a single facilitator call could freeze a
        # request worker for 5 minutes (timeout=300 in payment_dispatcher).
        { name = "FACILITATOR_TIMEOUT_SECONDS", value = "30" },
      ], local.mcp_otel_env)

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
          name      = "SUPABASE_JWT_SECRET"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/supabase-jwt:SUPABASE_JWT_SECRET::"
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
          name      = "OPENAI_API_KEY"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/openai:OPENAI_API_KEY::"
        },
        {
          name      = "GOOGLE_API_KEY"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/google:GOOGLE_API_KEY::"
        },
        {
          name      = "OPENROUTER_API_KEY"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/openrouter:OPENROUTER_API_KEY::"
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
        # ENS integration (subname creation)
        {
          name      = "ENS_OWNER_PRIVATE_KEY"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/ens:ENS_OWNER_PRIVATE_KEY::"
        },
        {
          name      = "ENS_PARENT_DOMAIN"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/ens:ENS_PARENT_DOMAIN::"
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
        # Per-chain private RPCs (from facilitator QuikNode endpoints)
        {
          name      = "BASE_RPC_URL"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/rpc-mainnet:base::"
        },
        {
          name      = "ETHEREUM_RPC_URL"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/rpc-mainnet:ethereum::"
        },
        {
          name      = "POLYGON_RPC_URL"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/rpc-mainnet:polygon::"
        },
        {
          name      = "ARBITRUM_RPC_URL"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/rpc-mainnet:arbitrum::"
        },
        {
          name      = "CELO_RPC_URL"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/rpc-mainnet:celo::"
        },
        {
          name      = "AVALANCHE_RPC_URL"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/rpc-mainnet:avalanche::"
        },
        {
          name      = "OPTIMISM_RPC_URL"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/rpc-mainnet:optimism::"
        },
        # EM_WORKER_PRIVATE_KEY removed (INC-2026-03-30) — only needed for E2E
        # testing, not production. Secret em/test-worker doesn't exist in SM.
        # World ID 4.0 (hackathon Track 2 — RP signing + Cloud API verify)
        {
          name      = "WORLD_ID_APP_ID"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/worldid:WORLD_ID_APP_ID::"
        },
        {
          name      = "WORLD_ID_RP_ID"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/worldid:WORLD_ID_RP_ID::"
        },
        {
          name      = "WORLD_ID_SIGNING_KEY"
          valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/worldid:WORLD_ID_SIGNING_KEY::"
        },
        # VeryAI (Veros Inc.) — palm-print biometric Tier T1 verification.
        # Phase 2 ships routes-disabled (EM_VERYAI_ENABLED=false above), so
        # the container starts cleanly even if these secret values are still
        # the placeholder empty strings. Operators populate em/veryai via
        # the AWS Console once Veros issues sandbox credentials. The
        # ignore_changes lifecycle on aws_secretsmanager_secret_version.veryai
        # prevents `terraform apply` from clobbering rotated values.
        {
          name      = "VERYAI_CLIENT_ID"
          valueFrom = "${aws_secretsmanager_secret.veryai.arn}:VERYAI_CLIENT_ID::"
        },
        {
          name      = "VERYAI_CLIENT_SECRET"
          valueFrom = "${aws_secretsmanager_secret.veryai.arn}:VERYAI_CLIENT_SECRET::"
        },
        {
          name      = "VERYAI_REDIRECT_URI"
          valueFrom = "${aws_secretsmanager_secret.veryai.arn}:VERYAI_REDIRECT_URI::"
        },
        {
          name      = "VERYAI_STATE_SECRET"
          valueFrom = "${aws_secretsmanager_secret.veryai.arn}:VERYAI_STATE_SECRET::"
        },
        # Sentry backend DSN (Phase 1.5 SAAS_PRODUCTION_HARDENING).
        # Value is provisioned manually in AWS Secrets Manager; an empty
        # string disables telemetry at runtime (see _SENTRY_DSN handling in
        # mcp_server/main.py).
        {
          name      = "SENTRY_DSN"
          valueFrom = "${aws_secretsmanager_secret.sentry_dsn.arn}:SENTRY_DSN::"
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

      # ECS sends SIGTERM, waits stopTimeout, then SIGKILL.
      # With AI verification offloaded to Lambda (SQS pipeline), the ECS
      # container only needs time to drain HTTP connections and cancel
      # background jobs.  Reduced from 120s (when Phase B ran in-process).
      stopTimeout = 60

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }

      # When tracing is enabled, wait for the collector to report HEALTHY on
      # :13133 before the app starts issuing spans. Otherwise the first
      # 10–30s of traffic bypass the pipeline because the OTLP endpoint
      # isn't listening yet. ``dependsOn`` requires the target container to
      # be declared in the same task definition — guarded with the flag so
      # an empty list doesn't reference a missing container.
      dependsOn = var.otel_enabled ? [
        {
          containerName = "aws-otel-collector"
          condition     = "HEALTHY"
        }
      ] : []
    }
  ], local.mcp_otel_sidecar))
}

# Dashboard is served via S3 + CloudFront (dashboard-cdn.tf) — no ECS needed.

# MCP Server Service
# Uses FARGATE_SPOT (base=1 on FARGATE for guaranteed min capacity, rest on SPOT for ~70% savings).
resource "aws_ecs_service" "mcp_server" {
  name            = "${local.name_prefix}-mcp-server"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.mcp_server.arn
  desired_count   = var.mcp_desired_count

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

  # Zero-downtime deploy: start new task BEFORE stopping old one.
  # With desiredCount=1: ECS briefly runs 2 tasks (200%), then drains the old (100%).
  # Eliminates the ~1 min gap where RunningTaskCount=0 during rolling updates.
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  # Grace period: don't fail health checks during startup (server needs ~30s to warm up)
  health_check_grace_period_seconds = 60

  load_balancer {
    target_group_arn = aws_lb_target_group.mcp_server.arn
    container_name   = "mcp-server"
    container_port   = 8000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [aws_lb_listener.https]

  lifecycle {
    ignore_changes = [desired_count]
  }
}

# ── Auto-scaling: MCP Server ───────────────────────────────────────────────────
resource "aws_appautoscaling_target" "mcp_server" {
  max_capacity       = var.mcp_max_count
  min_capacity       = var.mcp_min_count
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.mcp_server.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Scale out when CPU > 60% for 2 consecutive minutes
resource "aws_appautoscaling_policy" "mcp_server_cpu_up" {
  name               = "${local.name_prefix}-mcp-cpu-scale-out"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.mcp_server.resource_id
  scalable_dimension = aws_appautoscaling_target.mcp_server.scalable_dimension
  service_namespace  = aws_appautoscaling_target.mcp_server.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 60.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Scale out when memory > 70% — catches OOM risk that CPU scaling misses
# (Magika warmup, Phase B queue backlogs, viem + aiohttp buffers).
# Task 3.5 — SaaS Production Hardening.
resource "aws_appautoscaling_policy" "mcp_server_memory_up" {
  name               = "${local.name_prefix}-mcp-memory-scale-out"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.mcp_server.resource_id
  scalable_dimension = aws_appautoscaling_target.mcp_server.scalable_dimension
  service_namespace  = aws_appautoscaling_target.mcp_server.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
