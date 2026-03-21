# =============================================================================
# KarmaCadabra Swarm — Agent Module
# =============================================================================
# Deploys a single OpenClaw agent as an ECS Fargate task.
# Each agent gets:
#   - Unique SOUL.md personality
#   - IDENTITY.md with name/index
#   - AGENTS.md with swarm instructions
#   - USER.md with deployer context
#   - Isolated workspace in S3
#   - CloudWatch logging
# =============================================================================

locals {
  # Generate a deterministic but unique agent name from the seed
  agent_names = [
    "aurora", "blaze", "cipher", "drift", "echo",
    "flux", "glyph", "helix", "iris", "jade",
    "kite", "loom", "mirage", "nexus", "orbit",
    "prism", "quasar", "rune", "spark", "tide",
    "umbra", "vortex", "wave", "xenon", "zephyr",
    "alpha", "bravo", "coral", "delta", "ember",
    "fable", "grove", "haze", "index", "jewel",
    "karma", "lunar", "myth", "noble", "opal",
    "pulse", "quest", "relay", "shard", "trace",
    "unity", "vivid", "wisp", "xeno", "zenith",
    "aether", "beacon", "crest", "dawn", "elixir",
    "forge", "glint", "haven", "icon", "jazz",
    "knot", "light", "muse", "nerve", "onyx",
    "pixel", "quill", "ridge", "sage", "torch",
    "ultra", "vault", "wren", "xray", "yarn",
    "zen", "arc", "bolt", "chip", "dusk",
    "edge", "fern", "gust", "helm", "isle",
    "jolt", "kelp", "lens", "mint", "neon",
    "oak", "pine", "rain", "silk", "thorn",
    "umber", "vine", "wind", "axis", "yew",
    "zinc", "amber", "brook", "clay", "dove",
    "elm", "flame", "gem", "harp", "ivy",
    "jet", "koi", "lake", "maple", "nix",
    "oasis", "petal", "quartz", "reef", "storm",
    "terra", "ursa", "vigor", "willow", "xeric",
    "yucca", "zeal", "agate", "birch", "cloud",
    "dune", "echo2", "frost", "gale", "hawk",
    "ink", "jasper", "key", "lark", "moss",
    "nova", "ore", "plume", "ruby", "slate",
    "twig", "urn", "vale", "wool", "xylem",
    "yogi", "zest", "ash", "bay", "cove",
    "den", "eve", "fir", "glen", "hill",
    "ice", "jay", "kit", "log", "mist",
    "net", "owl", "pod", "rill", "sun",
    "tar", "use", "vow", "web", "xis",
  ]

  display_name = var.agent_index < length(local.agent_names) ? local.agent_names[var.agent_index] : "agent-${var.agent_index}"

  # Container environment
  container_env = [
    {
      name  = "AGENT_NAME"
      value = local.display_name
    },
    {
      name  = "AGENT_INDEX"
      value = tostring(var.agent_index)
    },
    {
      name  = "AGENT_MODEL"
      value = var.agent_model
    },
    {
      name  = "S3_BUCKET"
      value = var.s3_bucket_name
    },
    {
      name  = "S3_PREFIX"
      value = "agents/${local.display_name}"
    },
    {
      name  = "AWS_REGION"
      value = var.aws_region
    },
    {
      name  = "ENVIRONMENT"
      value = var.environment
    },
    {
      name  = "SOUL_PERSONALITY"
      value = var.soul_template.name
    },
    {
      name  = "SOUL_TRAITS"
      value = join(",", var.soul_template.traits)
    },
    {
      name  = "SOUL_COMMUNICATION"
      value = var.soul_template.communication
    },
    {
      name  = "SOUL_INTERESTS"
      value = join(",", var.soul_template.interests)
    },
    {
      name  = "SOUL_RISK_TOLERANCE"
      value = var.soul_template.risk_tolerance
    },
    {
      name  = "SOUL_LANGUAGE"
      value = var.soul_template.language
    },
    {
      name  = "PERSONALITY_SEED"
      value = tostring(var.personality_seed)
    },
  ]
}

# -----------------------------------------------------------------------------
# ECS Task Definition
# -----------------------------------------------------------------------------
resource "aws_ecs_task_definition" "agent" {
  family                   = "kk-swarm-${local.display_name}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn            = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name      = "openclaw-agent"
      image     = "${var.ecr_repository_url}:latest"
      essential = true

      environment = local.container_env

      secrets = [
        {
          name      = "ANTHROPIC_API_KEY"
          valueFrom = var.anthropic_api_key_arn
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = var.log_group_name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = local.display_name
        }
      }

      # Health check — OpenClaw Gateway responds on /health
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:18789/health || exit 1"]
        interval    = 60
        timeout     = 10
        retries     = 3
        startPeriod = 120
      }

      # Resource limits
      ulimits = [
        {
          name      = "nofile"
          softLimit = 65536
          hardLimit = 65536
        }
      ]
    }
  ])

  tags = {
    Name        = "kk-swarm-${local.display_name}"
    AgentName   = local.display_name
    AgentIndex  = var.agent_index
    Personality = var.soul_template.name
  }
}

# -----------------------------------------------------------------------------
# ECS Service
# -----------------------------------------------------------------------------
resource "aws_ecs_service" "agent" {
  name            = "kk-${local.display_name}"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.agent.arn
  desired_count   = 1
  launch_type     = var.use_spot ? null : "FARGATE"

  # Use Fargate Spot for cost savings
  dynamic "capacity_provider_strategy" {
    for_each = var.use_spot ? [1] : []
    content {
      capacity_provider = "FARGATE_SPOT"
      weight            = 1
      base              = 0
    }
  }

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = false
  }

  # Allow service to stabilize
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  # Prevent Terraform from resetting desired count on redeploy
  lifecycle {
    ignore_changes = [desired_count]
  }

  tags = {
    Name        = "kk-${local.display_name}"
    AgentName   = local.display_name
    AgentIndex  = var.agent_index
    Personality = var.soul_template.name
  }
}
