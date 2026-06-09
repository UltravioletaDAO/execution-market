# Phase 2.3 — pay.sh sidecar on ECS Fargate (Solana MPP demo).
#
# Architecture (per master plan §Phase 2):
#
#   ALB :443  ──host=mcp.execution.market──>  TG payshell :7081
#                                                 │
#                                                 ▼
#                                   ┌─────────────────────────────┐
#                                   │  ECS Task: em-payshell-task │
#                                   │  ┌─────────────────────┐    │
#                                   │  │ pay.sh   :7081 ◀────┼────┘  (external)
#                                   │  │   │                 │
#                                   │  │   │ upstream        │
#                                   │  │   ▼                 │
#                                   │  │ mcp-server :8000    │  (loopback only)
#                                   │  └─────────────────────┘
#                                   └─────────────────────────────┘
#
# - pay.sh OWNS the public port. Every HTTP request hits pay.sh first.
# - 402 challenges, voucher accept, SSE events, settle calls are answered by
#   pay.sh without ever touching the Python backend.
# - Once pay.sh validates a session/voucher it forwards the original request
#   to mcp-server on loopback (sidecar shares the network namespace inside
#   the same Fargate task — `network_mode = "awsvpc"` puts both containers
#   on the same ENI so `127.0.0.1` works).
#
# Why a NEW task definition instead of editing ecs.tf in place:
#   - The existing `aws_ecs_task_definition.mcp_server` is the legacy direct
#     route and stays in Terraform as the rollback target. Until pay.sh has
#     been validated end-to-end on production (Phase 2.10 dress rehearsal),
#     we keep both task defs side-by-side and route via ALB priority.
#   - Feature flag `enable_payshell` (default `false`) keeps every resource
#     in this file at `count = 0` so a `terraform apply` after merging this
#     PR is a NO-OP. Flip the flag to `true` in `terraform.tfvars` only when
#     the operator has:
#       1. Pushed a pay.sh image to `${name_prefix}-payshell` ECR
#       2. Populated `em/payshell/facilitator` secret with the keypair JSON
#       3. Verified the YAML at `infrastructure/pay/em-gateway.yml` renders
#
# INC-2026-03-30 zero-tolerance: the facilitator keypair is NEVER inlined
# anywhere in this file or in the task definition. It is fetched at runtime
# from Secrets Manager (`em/payshell/facilitator`) and the secret container
# itself is created here with an empty placeholder.

# ---------------------------------------------------------------------------
# Feature flag
# ---------------------------------------------------------------------------

variable "enable_payshell" {
  description = <<-EOT
    Manage the pay.sh sidecar stack (Phase 2 — Solana MPP demo).
    Default false: every resource in payshell.tf is count=0 so `terraform
    apply` is a no-op until the operator has built/pushed the pay.sh image
    and populated em/payshell/facilitator.
  EOT
  type        = bool
  default     = false
}

variable "payshell_image" {
  description = <<-EOT
    Container image for the pay.sh sidecar. Leave empty to default to
    `$${aws_ecr_repository.payshell[0].repository_url}:latest`. Override with
    an explicit `:<sha>` tag for production pins.
  EOT
  type        = string
  default     = ""
}

variable "payshell_solana_rpc_url" {
  description = "Public Solana RPC URL injected into pay.sh (mainnet / surfpool override)."
  type        = string
  default     = "https://api.mainnet-beta.solana.com"
}

variable "payshell_cpu" {
  description = "CPU units for the combined pay.sh + mcp-server task (1024 = 1 vCPU)."
  type        = number
  default     = 1024
}

variable "payshell_memory" {
  description = "Memory (MB) for the combined pay.sh + mcp-server task."
  type        = number
  default     = 2048
}

# ---------------------------------------------------------------------------
# ECR repository for the pay.sh image.
# ---------------------------------------------------------------------------
# Image is built from `solana-foundation/pay` upstream Dockerfile plus a tiny
# wrapper entrypoint that materializes FACILITATOR_KEYPAIR_JSON to a tmpfs
# file before launching `pay serve`. The Dockerfile lives at
# `infrastructure/pay/Dockerfile` (Phase 2.3 follow-up task).

resource "aws_ecr_repository" "payshell" {
  count                = var.enable_payshell ? 1 : 0
  name                 = "${local.name_prefix}-payshell"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name      = "${local.name_prefix}-payshell"
    Component = "solana-mpp"
  }
}

resource "aws_ecr_lifecycle_policy" "payshell" {
  count      = var.enable_payshell ? 1 : 0
  repository = aws_ecr_repository.payshell[0].name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 5 tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["latest", "v", "sha-"]
          countType     = "imageCountMoreThan"
          countNumber   = 5
        }
        action = { type = "expire" }
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
        action = { type = "expire" }
      }
    ]
  })
}

# ---------------------------------------------------------------------------
# Secret — facilitator keypair (INC-2026-03-30 zero-tolerance).
# ---------------------------------------------------------------------------
# JSON shape:
#   {
#     "FACILITATOR_KEYPAIR_JSON": "[<64 bytes as int array per Solana CLI format>]",
#     "FACILITATOR_PUBKEY":       "<base58 pubkey for log/metric tagging>",
#     "WORKER_WALLET":            "<base58 worker dest>",
#     "TREASURY_WALLET":          "<base58 treasury dest>"
#   }
#
# Populate manually after running `solana-keygen new --no-bip39-passphrase`
# on an air-gapped machine, then:
#
#   aws secretsmanager put-secret-value \
#     --secret-id em/payshell/facilitator \
#     --secret-string file://./keypair-bundle.json
#
# Terraform creates the container with an empty placeholder so `terraform
# apply` is safe before the operator has provisioned the keypair. ECS task
# fails the healthcheck and stays unhealthy until the keys are real, which
# is the right failure mode (no silent fallback to a "test" key).

resource "aws_secretsmanager_secret" "payshell_facilitator" {
  count       = var.enable_payshell ? 1 : 0
  name        = "em/payshell/facilitator"
  description = "Solana facilitator keypair + treasury/worker wallets for pay.sh sidecar. Populate manually — never store keys in Terraform."

  recovery_window_in_days = 0

  tags = {
    Name      = "${local.name_prefix}-payshell-facilitator"
    Component = "solana-mpp"
    Sensitive = "secret-key-material"
  }
}

resource "aws_secretsmanager_secret_version" "payshell_facilitator" {
  count     = var.enable_payshell ? 1 : 0
  secret_id = aws_secretsmanager_secret.payshell_facilitator[0].id

  secret_string = jsonencode({
    FACILITATOR_KEYPAIR_JSON = ""
    FACILITATOR_PUBKEY       = ""
    WORKER_WALLET            = ""
    TREASURY_WALLET          = ""
  })

  lifecycle {
    # Operator-managed values — never let `terraform apply` clobber the real
    # keypair back to the empty placeholder.
    ignore_changes = [secret_string]
  }
}

# ---------------------------------------------------------------------------
# CloudWatch log groups.
# ---------------------------------------------------------------------------
# pay.sh and mcp-server go to separate streams so JSON log queries can target
# one or the other without unioning across containers.

resource "aws_cloudwatch_log_group" "payshell" {
  count             = var.enable_payshell ? 1 : 0
  name              = "/ecs/${local.name_prefix}/payshell"
  retention_in_days = 90

  tags = {
    Component = "solana-mpp"
  }
}

resource "aws_cloudwatch_log_group" "payshell_mcp" {
  count             = var.enable_payshell ? 1 : 0
  name              = "/ecs/${local.name_prefix}/payshell-mcp"
  retention_in_days = 90

  tags = {
    Component = "solana-mpp"
  }
}

# ---------------------------------------------------------------------------
# Security group — port 7081 from ALB → ECS.
# ---------------------------------------------------------------------------
# We REUSE aws_security_group.ecs (defined in ecs.tf) for the new task; that
# SG already allows egress * and ingress from ALB. The only missing piece is
# ingress on 7081 from the ALB. We add it here so payshell.tf is the single
# place this concern lives.

resource "aws_security_group_rule" "ecs_payshell_ingress" {
  count = var.enable_payshell ? 1 : 0

  security_group_id        = aws_security_group.ecs.id
  type                     = "ingress"
  from_port                = 7081
  to_port                  = 7081
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
  description              = "pay.sh proxy ingress from ALB (Phase 2.3)"
}

# ---------------------------------------------------------------------------
# ALB target group — pay.sh on port 7081.
# ---------------------------------------------------------------------------
# Health check hits pay.sh's built-in `/_health` (returns 200 with a JSON
# payload describing chain head, facilitator wallet balance, voucher acceptor
# state). If pay.sh is healthy but upstream mcp-server is not, this TG still
# reports healthy — that's by design because pay.sh can serve 402 challenges
# and SSE streams without the backend.

resource "aws_lb_target_group" "payshell" {
  count = var.enable_payshell ? 1 : 0

  name        = "${local.name_prefix}-payshell-tg"
  port        = 7081
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  # pay.sh has a 30s shutdown drain (see em-gateway.yml shutdown_drain_seconds).
  # Match deregistration to give in-flight sessions time to close cleanly.
  deregistration_delay = 30

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200-299"
    path                = "/_health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 10
    unhealthy_threshold = 3
  }

  tags = {
    Name      = "${local.name_prefix}-payshell-tg"
    Component = "solana-mpp"
  }
}

# ---------------------------------------------------------------------------
# Task definition — sidecar (pay.sh + mcp-server).
# ---------------------------------------------------------------------------
# Sidecar pattern: both containers share the same Fargate ENI, so pay.sh can
# reach mcp-server at `127.0.0.1:8000` with sub-ms latency. dependsOn forces
# pay.sh to wait for mcp-server's HEALTHY signal before starting — otherwise
# the first batch of 402 challenges would proxy to a not-yet-listening Python
# server and 502.
#
# The mcp-server container definition INTENTIONALLY duplicates the env/secrets
# block from aws_ecs_task_definition.mcp_server. We could DRY this via a
# local but the duplication is deliberate — the legacy task def is the
# rollback target and any divergence between the two is a feature, not a bug
# (e.g., pay.sh task uses `EM_PAYSHELL_ENABLED=true` to mount taxímetro
# routes; legacy stays `false`).

resource "aws_ecs_task_definition" "payshell" {
  count = var.enable_payshell ? 1 : 0

  family                   = "${local.name_prefix}-payshell"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.payshell_cpu
  memory                   = var.payshell_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    # ---------- pay.sh proxy ------------------------------------------------
    {
      name      = "payshell"
      image     = var.payshell_image != "" ? var.payshell_image : "${aws_ecr_repository.payshell[0].repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 7081
          hostPort      = 7081
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "PAYSHELL_CONFIG", value = "/etc/pay/em-gateway.yml" },
        { name = "EM_UPSTREAM_URL", value = "http://127.0.0.1:8000" },
        { name = "SOLANA_RPC_URL", value = var.payshell_solana_rpc_url },
        { name = "FACILITATOR_KEYPAIR_PATH", value = "/tmp/facilitator-keypair.json" },
        # MPP program ID — blank until Tempo publishes mainnet program (D-15).
        # Surfpool dev uses upstream Anchor build; production pins SHA via
        # task-def update once Ludo announces the deploy.
        { name = "MPP_PROGRAM_ID", value = "" },
        { name = "RUST_LOG", value = "info,pay=info" },
      ]

      secrets = [
        # Wrapper entrypoint writes this JSON-encoded keypair to
        # /tmp/facilitator-keypair.json before launching `pay serve`. The
        # raw key never lives on disk outside tmpfs and never appears in
        # logs (pay.sh's `drop_fields` config strips facilitator.keypair).
        {
          name      = "FACILITATOR_KEYPAIR_JSON"
          valueFrom = "${aws_secretsmanager_secret.payshell_facilitator[0].arn}:FACILITATOR_KEYPAIR_JSON::"
        },
        {
          name      = "WORKER_WALLET"
          valueFrom = "${aws_secretsmanager_secret.payshell_facilitator[0].arn}:WORKER_WALLET::"
        },
        {
          name      = "TREASURY_WALLET"
          valueFrom = "${aws_secretsmanager_secret.payshell_facilitator[0].arn}:TREASURY_WALLET::"
        },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.payshell[0].name
          awslogs-region        = local.region
          awslogs-stream-prefix = "payshell"
        }
      }

      # Health check hits pay.sh's own /_health endpoint on loopback.
      # Used by ECS to decide if the task is healthy before adding it to TG.
      healthCheck = {
        command     = ["CMD-SHELL", "curl -fsS http://127.0.0.1:7081/_health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 30
      }

      # Sidecar coupling — wait for mcp-server to be HEALTHY before pay.sh
      # accepts traffic. Avoids the proxy 502'ing during cold-start.
      dependsOn = [
        {
          containerName = "mcp-server"
          condition     = "HEALTHY"
        }
      ]

      # Phase 2.10 graceful shutdown — ECS sends SIGTERM, pay.sh drains
      # sessions over 30s (em-gateway.yml shutdown_drain_seconds), THEN
      # mcp-server stops. Total task stopTimeout must accommodate this.
      stopTimeout = 60
    },

    # ---------- mcp-server (Python upstream) -------------------------------
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

      # NOTE: mirrors aws_ecs_task_definition.mcp_server.environment, plus
      # the payshell-specific flags (EM_PAYSHELL_ENABLED, EM_PAYSHELL_URL).
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
        { name = "EM_ENABLED_NETWORKS", value = "base,ethereum,polygon,arbitrum,celo,monad,avalanche,optimism,skale,solana" },
        { name = "EVIDENCE_BUCKET", value = local.evidence_bucket_name },
        { name = "EVIDENCE_PUBLIC_BASE_URL", value = var.enable_evidence_pipeline ? "https://${aws_cloudfront_distribution.evidence[0].domain_name}" : "https://${local.evidence_bucket_name}.s3.amazonaws.com" },
        { name = "EM_FEEDBACK_BASE_URL", value = "https://execution.market" },
        { name = "ERC8128_NONCE_STORE", value = "dynamodb" },
        { name = "EM_REQUIRE_ERC8004", value = "true" },
        { name = "EM_REQUIRE_ERC8004_WORKER", value = "true" },
        { name = "EM_VERYAI_ENABLED", value = "true" },
        { name = "EM_GEO_MATCH_ENABLED", value = "true" },
        { name = "VERIFICATION_AI_ENABLED", value = "true" },
        { name = "AI_VERIFICATION_PROVIDER", value = "gemini" },
        { name = "VERIFICATION_AUTO_APPROVE", value = "true" },
        { name = "EM_AAAS_ENABLED", value = "true" },
        { name = "EM_ARBITER_AUTO_RELEASE_ENABLED", value = "false" },
        { name = "ARBITER_DAILY_BUDGET_USD", value = "100" },
        { name = "ARBITER_PER_CALLER_BUDGET_USD", value = "10" },
        { name = "EM_VERIFICATION_BACKEND", value = "sqs" },
        { name = "RING1_QUEUE_URL", value = aws_sqs_queue.ring1.url },
        { name = "RING2_QUEUE_URL", value = aws_sqs_queue.ring2.url },
        { name = "GIT_SHA", value = var.git_sha },
        { name = "FACILITATOR_TIMEOUT_SECONDS", value = "30" },

        # ---- Phase 2.3 payshell-only flags ----
        # Mounts /api/v1/taximetro/* routes (SSE relay) and enables the
        # session-aware payment dispatcher branch (solana_session mode).
        { name = "EM_PAYSHELL_ENABLED", value = "true" },
        # Backend reaches pay.sh on loopback for control-plane ops
        # (get_session, close_session, subscribe_events). See
        # mcp_server/integrations/solana/pay_shell_client.py.
        { name = "EM_PAYSHELL_URL", value = "http://127.0.0.1:7081" },
        { name = "EM_PAYSHELL_TIMEOUT", value = "30" },
      ]

      secrets = [
        { name = "SUPABASE_URL", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/supabase:SUPABASE_URL::" },
        { name = "SUPABASE_ANON_KEY", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/supabase:SUPABASE_ANON_KEY::" },
        { name = "SUPABASE_SERVICE_KEY", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/supabase:SUPABASE_SERVICE_ROLE_KEY::" },
        { name = "SUPABASE_JWT_SECRET", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/supabase-jwt:SUPABASE_JWT_SECRET::" },
        { name = "EM_ADMIN_KEY", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/admin-key" },
        { name = "ANTHROPIC_API_KEY", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/anthropic:ANTHROPIC_API_KEY::" },
        { name = "OPENAI_API_KEY", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/openai:OPENAI_API_KEY::" },
        { name = "GOOGLE_API_KEY", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/google:GOOGLE_API_KEY::" },
        { name = "OPENROUTER_API_KEY", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/openrouter:OPENROUTER_API_KEY::" },
        { name = "WALLET_PRIVATE_KEY", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/x402:PRIVATE_KEY::" },
        { name = "X402_NETWORK", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/x402:X402_NETWORK::" },
        { name = "X402_RPC_URL", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/x402:X402_RPC_URL::" },
        { name = "X402_FACILITATOR_URL", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/x402:FACILITATOR_URL::" },
        { name = "ENS_OWNER_PRIVATE_KEY", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/ens:ENS_OWNER_PRIVATE_KEY::" },
        { name = "ENS_PARENT_DOMAIN", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/ens:ENS_PARENT_DOMAIN::" },
        { name = "EM_ESCROW_ADDRESS", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/x402:X402R_ESCROW::" },
        { name = "USDC_ADDRESS", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/x402:USDC_ADDRESS::" },
        { name = "EM_TREASURY_ADDRESS", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/commission:wallet_address::" },
        { name = "BASE_RPC_URL", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/rpc-mainnet:base::" },
        { name = "ETHEREUM_RPC_URL", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/rpc-mainnet:ethereum::" },
        { name = "POLYGON_RPC_URL", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/rpc-mainnet:polygon::" },
        { name = "ARBITRUM_RPC_URL", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/rpc-mainnet:arbitrum::" },
        { name = "CELO_RPC_URL", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/rpc-mainnet:celo::" },
        { name = "AVALANCHE_RPC_URL", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/rpc-mainnet:avalanche::" },
        { name = "OPTIMISM_RPC_URL", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/rpc-mainnet:optimism::" },
        { name = "WORLD_ID_APP_ID", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/worldid:WORLD_ID_APP_ID::" },
        { name = "WORLD_ID_RP_ID", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/worldid:WORLD_ID_RP_ID::" },
        { name = "WORLD_ID_SIGNING_KEY", valueFrom = "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/worldid:WORLD_ID_SIGNING_KEY::" },
        { name = "VERYAI_CLIENT_ID", valueFrom = "${aws_secretsmanager_secret.veryai.arn}:VERYAI_CLIENT_ID::" },
        { name = "VERYAI_CLIENT_SECRET", valueFrom = "${aws_secretsmanager_secret.veryai.arn}:VERYAI_CLIENT_SECRET::" },
        { name = "VERYAI_REDIRECT_URI", valueFrom = "${aws_secretsmanager_secret.veryai.arn}:VERYAI_REDIRECT_URI::" },
        { name = "VERYAI_STATE_SECRET", valueFrom = "${aws_secretsmanager_secret.veryai.arn}:VERYAI_STATE_SECRET::" },
        { name = "SENTRY_DSN", valueFrom = "${aws_secretsmanager_secret.sentry_dsn.arn}:SENTRY_DSN::" },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.payshell_mcp[0].name
          awslogs-region        = local.region
          awslogs-stream-prefix = "ecs"
        }
      }

      stopTimeout = 60

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    },
  ])

  tags = {
    Component = "solana-mpp"
  }
}

# ---------------------------------------------------------------------------
# ECS service.
# ---------------------------------------------------------------------------
# Lives alongside the legacy `aws_ecs_service.mcp_server`. The ALB listener
# rule below decides which one serves mcp.execution.market based on header
# (X-EM-Route: payshell), so we can canary the new path before flipping the
# default. desired_count=1 by default; bump via tfvars when stable.

resource "aws_ecs_service" "payshell" {
  count           = var.enable_payshell ? 1 : 0
  name            = "${local.name_prefix}-payshell"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.payshell[0].arn
  desired_count   = 1

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

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 90

  load_balancer {
    target_group_arn = aws_lb_target_group.payshell[0].arn
    container_name   = "payshell"
    container_port   = 7081
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [
    aws_lb_listener.https,
    aws_security_group_rule.ecs_payshell_ingress,
  ]

  lifecycle {
    ignore_changes = [desired_count]
  }

  tags = {
    Component = "solana-mpp"
  }
}

# ---------------------------------------------------------------------------
# ALB listener rule — header-based canary.
# ---------------------------------------------------------------------------
# Priority 90 (BEFORE the existing mcp rule at priority 100). When a client
# sends `X-EM-Route: payshell` we route to the new TG; everything else falls
# through to the legacy mcp_server TG. This makes Phase 2.10 dress rehearsal
# a one-header flip (no config push, no DNS swap).
#
# Once Phase 2.10 passes, the cutover is:
#   1. Bump this rule's `host_header` condition to match all of
#      mcp.execution.market traffic
#   2. Remove the X-EM-Route condition
#   3. Scale aws_ecs_service.mcp_server desired_count to 0 (keep as rollback)

resource "aws_lb_listener_rule" "payshell" {
  count        = var.enable_payshell ? 1 : 0
  listener_arn = aws_lb_listener.https.arn
  priority     = 90

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.payshell[0].arn
  }

  condition {
    host_header {
      values = ["mcp.${var.domain_name}"]
    }
  }

  condition {
    http_header {
      http_header_name = "X-EM-Route"
      values           = ["payshell"]
    }
  }

  tags = {
    Component = "solana-mpp"
  }
}

# ---------------------------------------------------------------------------
# Outputs — used by deploy scripts and the Phase 2.10 runbook.
# ---------------------------------------------------------------------------

output "payshell_ecr_repository_url" {
  description = "ECR repository URL for the pay.sh image. Empty until enable_payshell=true."
  value       = var.enable_payshell ? aws_ecr_repository.payshell[0].repository_url : ""
}

output "payshell_service_name" {
  description = "ECS service name for the pay.sh sidecar stack."
  value       = var.enable_payshell ? aws_ecs_service.payshell[0].name : ""
}

output "payshell_target_group_arn" {
  description = "ALB target group ARN for pay.sh — useful for canary scripts."
  value       = var.enable_payshell ? aws_lb_target_group.payshell[0].arn : ""
}

output "payshell_facilitator_secret_arn" {
  description = "Secrets Manager ARN for the facilitator keypair. Populate before flipping enable_payshell."
  value       = var.enable_payshell ? aws_secretsmanager_secret.payshell_facilitator[0].arn : ""
}
