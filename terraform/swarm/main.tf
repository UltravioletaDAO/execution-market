# =============================================================================
# KarmaCadabra Swarm — Terraform Main Configuration
# =============================================================================
# Deploys N OpenClaw AI agents on AWS ECS Fargate.
# Each agent has its own personality (SOUL.md), identity, and workspace.
#
# Usage:
#   terraform init
#   terraform plan -var="anthropic_api_key=sk-ant-..."
#   terraform apply -var="anthropic_api_key=sk-ant-..."
#
# Or use the deploy script:
#   ./scripts/deploy.sh --api-key sk-ant-... --agents 5
# =============================================================================

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }

  # Remote state — uses same bucket as main infra (different key).
  # Run: terraform init -backend-config="bucket=<YOUR_TERRAFORM_STATE_BUCKET>"
  backend "s3" {
    key     = "swarm/karmacadabra/terraform.tfstate"
    region  = "us-east-2"
    encrypt = true
    # bucket must be passed via -backend-config or TF_BACKEND_* env vars
    # to avoid hardcoding the bucket name in git.
  }
}

# -----------------------------------------------------------------------------
# Provider
# -----------------------------------------------------------------------------
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "karmacadabra-swarm"
      ManagedBy   = "terraform"
      Environment = var.environment
    }
  }
}

# -----------------------------------------------------------------------------
# Data Sources
# -----------------------------------------------------------------------------
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

# -----------------------------------------------------------------------------
# Networking — VPC, Subnets, NAT
# -----------------------------------------------------------------------------
resource "aws_vpc" "swarm" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "kk-swarm-vpc"
  }
}

resource "aws_internet_gateway" "swarm" {
  vpc_id = aws_vpc.swarm.id

  tags = {
    Name = "kk-swarm-igw"
  }
}

# Public subnets (for NAT Gateway + ALB)
resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.swarm.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "kk-swarm-public-${count.index + 1}"
    Type = "public"
  }
}

# Private subnets (for ECS tasks)
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.swarm.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "kk-swarm-private-${count.index + 1}"
    Type = "private"
  }
}

# NAT Gateway (single — cost optimization)
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name = "kk-swarm-nat-eip"
  }
}

resource "aws_nat_gateway" "swarm" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name = "kk-swarm-nat"
  }

  depends_on = [aws_internet_gateway.swarm]
}

# Route tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.swarm.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.swarm.id
  }

  tags = {
    Name = "kk-swarm-public-rt"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.swarm.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.swarm.id
  }

  tags = {
    Name = "kk-swarm-private-rt"
  }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# Security group for ECS tasks
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "kk-swarm-ecs-"
  vpc_id      = aws_vpc.swarm.id

  # Allow all outbound (agents need internet for LLM APIs)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "kk-swarm-ecs-sg"
  }
}

# -----------------------------------------------------------------------------
# ECS Cluster
# -----------------------------------------------------------------------------
resource "aws_ecs_cluster" "swarm" {
  name = "kk-swarm-${var.environment}"

  setting {
    name  = "containerInsights"
    value = var.enable_container_insights ? "enabled" : "disabled"
  }

  tags = {
    Name = "kk-swarm-cluster"
  }
}

# Capacity provider for Fargate Spot (70% cheaper)
resource "aws_ecs_cluster_capacity_providers" "swarm" {
  cluster_name = aws_ecs_cluster.swarm.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 1
    capacity_provider = var.use_spot ? "FARGATE_SPOT" : "FARGATE"
  }
}

# -----------------------------------------------------------------------------
# ECR Repository (shared container image for all agents)
# -----------------------------------------------------------------------------
resource "aws_ecr_repository" "openclaw_agent" {
  name                 = "kk-swarm/openclaw-agent"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "kk-swarm-openclaw-agent"
  }
}

# Lifecycle policy — keep last 10 images
resource "aws_ecr_lifecycle_policy" "openclaw_agent" {
  repository = aws_ecr_repository.openclaw_agent.name

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

# -----------------------------------------------------------------------------
# Secrets Manager
# -----------------------------------------------------------------------------
resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name                    = "kk-swarm/anthropic-api-key"
  description             = "Anthropic API key for OpenClaw agents"
  recovery_window_in_days = 0 # Immediate deletion for dev

  tags = {
    Name = "kk-swarm-anthropic-key"
  }
}

resource "aws_secretsmanager_secret_version" "anthropic_api_key" {
  secret_id     = aws_secretsmanager_secret.anthropic_api_key.id
  secret_string = var.anthropic_api_key
}

# -----------------------------------------------------------------------------
# S3 — Agent state, memory, and workspace files
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "agent_state" {
  bucket        = "kk-swarm-agent-state-${data.aws_caller_identity.current.account_id}"
  force_destroy = true

  tags = {
    Name = "kk-swarm-agent-state"
  }
}

resource "aws_s3_bucket_versioning" "agent_state" {
  bucket = aws_s3_bucket.agent_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "agent_state" {
  bucket = aws_s3_bucket.agent_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "agent_state" {
  bucket = aws_s3_bucket.agent_state.id

  rule {
    id     = "memory-cleanup"
    status = "Enabled"

    filter {
      prefix = "agents/*/memory/"
    }

    # Move old memory files to Glacier after 90 days
    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    # Delete after 1 year
    expiration {
      days = 365
    }
  }
}

# -----------------------------------------------------------------------------
# IAM — ECS Task Execution Role & Task Role
# -----------------------------------------------------------------------------
resource "aws_iam_role" "ecs_execution" {
  name = "kk-swarm-ecs-execution"

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

# Allow ECS to pull secrets
resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "kk-swarm-secrets-access"
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
          aws_secretsmanager_secret.anthropic_api_key.arn
        ]
      }
    ]
  })
}

# Task role — what the container can do
resource "aws_iam_role" "ecs_task" {
  name = "kk-swarm-ecs-task"

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

resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "kk-swarm-s3-access"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:DeleteObject"
        ]
        Resource = [
          aws_s3_bucket.agent_state.arn,
          "${aws_s3_bucket.agent_state.arn}/*"
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Log Group (shared)
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "swarm" {
  name              = "/ecs/kk-swarm"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "kk-swarm-logs"
  }
}

# -----------------------------------------------------------------------------
# Agent Modules — Deploy each agent
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Cost Alerting (CloudWatch + SNS)
# -----------------------------------------------------------------------------
module "cost_alerts" {
  source = "./modules/cost-alerts"

  cluster_name        = aws_ecs_cluster.swarm.name
  nat_gateway_id      = aws_nat_gateway.swarm.id
  alert_email         = var.alert_email
  daily_spend_limit   = var.daily_spend_limit
  max_expected_agents = var.agent_count
}

# -----------------------------------------------------------------------------
# Agent Modules — Deploy each agent
# -----------------------------------------------------------------------------
module "agent" {
  source   = "./modules/agent"
  for_each = { for i in range(var.agent_count) : format("agent-%03d", i) => i }

  # Identity
  agent_name  = each.key
  agent_index = each.value

  # Infrastructure
  ecs_cluster_id        = aws_ecs_cluster.swarm.id
  ecs_execution_role_arn = aws_iam_role.ecs_execution.arn
  ecs_task_role_arn      = aws_iam_role.ecs_task.arn
  subnet_ids            = aws_subnet.private[*].id
  security_group_ids    = [aws_security_group.ecs_tasks.id]
  ecr_repository_url    = aws_ecr_repository.openclaw_agent.repository_url
  log_group_name        = aws_cloudwatch_log_group.swarm.name
  s3_bucket_name        = aws_s3_bucket.agent_state.id
  s3_bucket_arn         = aws_s3_bucket.agent_state.arn

  # Secrets
  anthropic_api_key_arn = aws_secretsmanager_secret.anthropic_api_key.arn

  # Configuration
  agent_model   = var.agent_model
  use_spot      = var.use_spot
  cpu           = var.agent_cpu
  memory        = var.agent_memory
  environment   = var.environment
  aws_region    = var.aws_region

  # Personality — sourced from templates
  soul_template   = var.soul_templates[each.value % length(var.soul_templates)]
  personality_seed = each.value

  depends_on = [
    aws_ecs_cluster_capacity_providers.swarm,
    aws_secretsmanager_secret_version.anthropic_api_key,
  ]
}
