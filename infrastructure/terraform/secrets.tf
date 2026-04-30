# Execution Market Infrastructure - Secrets Reference
#
# Existing secrets are managed manually in AWS Secrets Manager.
# Secrets are stored under the em/* prefix:
#   - em/supabase (url, anon_key, service_key)
#   - em/contracts (avalanche, etc.)
#   - em/commission (address)
#   - em/x402 (private_key)
#   - em/rpc-mainnet (per-chain private RPCs: base, ethereum, polygon, arbitrum, celo, avalanche, optimism, monad)
#   - em/api-keys (api keys)
#   - em/sentry-dsn (Phase 1.5: Sentry backend DSN — see below)
#
# This file only creates IAM policies for accessing these secrets.

# Data sources for existing secrets
data "aws_secretsmanager_secret" "supabase" {
  name = "em/supabase"
}

data "aws_secretsmanager_secret" "contracts" {
  name = "em/contracts"
}

data "aws_secretsmanager_secret" "commission" {
  name = "em/commission"
}

# ---------------------------------------------------------------------------
# Sentry backend DSN (Phase 1.5 SAAS_PRODUCTION_HARDENING)
# ---------------------------------------------------------------------------
#
# Terraform CREATES the secret container with a placeholder value. The real
# DSN must be populated manually in the AWS Console (or via
# `aws secretsmanager put-secret-value`) so that the Sentry token never
# lives in Terraform state or the git repo.
#
# Graceful degradation: if the secret value is left empty, the FastAPI
# app will start without Sentry telemetry (see _SENTRY_DSN handling in
# mcp_server/main.py). This keeps `terraform apply` safe on first run
# before an ops engineer has provisioned the actual DSN.
#
# To populate:
#   aws secretsmanager put-secret-value \
#     --secret-id em/sentry-dsn \
#     --secret-string '{"SENTRY_DSN":"https://<hash>@<org>.ingest.sentry.io/<project>"}'
# ---------------------------------------------------------------------------

variable "sentry_dsn" {
  description = <<-EOT
    Optional initial value for the Sentry backend DSN. Leave empty and
    populate em/sentry-dsn manually in AWS Secrets Manager to keep the
    token out of Terraform state. The backend runs without telemetry when
    this is empty (see mcp_server/main.py _SENTRY_DSN handling).
  EOT
  type        = string
  default     = ""
  sensitive   = true
}

resource "aws_secretsmanager_secret" "sentry_dsn" {
  name        = "em/sentry-dsn"
  description = "Sentry backend DSN (Phase 1.5). Populate manually — leave empty to disable telemetry."

  # Short recovery window so a manual rotation doesn't hit the 30-day lockout.
  recovery_window_in_days = 0

  tags = {
    Name      = "${local.name_prefix}-sentry-dsn"
    ManagedBy = "terraform"
    Component = "observability"
  }
}

resource "aws_secretsmanager_secret_version" "sentry_dsn" {
  secret_id = aws_secretsmanager_secret.sentry_dsn.id
  # JSON blob so we can reference SENTRY_DSN in ECS task-def via the
  # :SENTRY_DSN:: suffix (matches the existing em/supabase pattern).
  secret_string = jsonencode({
    SENTRY_DSN = var.sentry_dsn
  })

  lifecycle {
    # Once an operator rotates the real DSN via the AWS Console / CLI we
    # don't want `terraform apply` to clobber it back to the empty default.
    ignore_changes = [secret_string]
  }
}

# ---------------------------------------------------------------------------
# VeryAI (Veros Inc.) OAuth2/OIDC credentials — Phase 2 VERYAI_INTEGRATION
# ---------------------------------------------------------------------------
#
# Same pattern as em/sentry-dsn: Terraform creates the secret container with
# empty placeholder values so `terraform apply` is safe before Veros issues
# real sandbox credentials. ignore_changes prevents subsequent applies from
# clobbering rotated values.
#
# The container is referenced from ECS task-def (ecs.tf) via the standard
# :KEY:: suffix syntax — one task-def env var per JSON key.
#
# Phase 2 default: routes-disabled (EM_VERYAI_ENABLED=false). The secret
# values can stay empty without affecting the running container — the FastAPI
# app will not even mount the /api/v1/very-id/* routes, so missing client_id
# is never dereferenced. Operators populate ALL FOUR keys before flipping
# EM_VERYAI_ENABLED to "true":
#
#   aws secretsmanager put-secret-value \
#     --secret-id em/veryai \
#     --secret-string '{"VERYAI_CLIENT_ID":"...","VERYAI_CLIENT_SECRET":"...","VERYAI_REDIRECT_URI":"https://api.execution.market/api/v1/very-id/callback","VERYAI_STATE_SECRET":"<openssl rand -base64 48>"}'
# ---------------------------------------------------------------------------

resource "aws_secretsmanager_secret" "veryai" {
  name        = "em/veryai"
  description = "VeryAI (Veros Inc.) OAuth2 client + state-signing secret. Populate manually after sandbox provisioning."

  # Short recovery window so a manual rotation doesn't hit the 30-day lockout.
  recovery_window_in_days = 0

  tags = {
    Name      = "${local.name_prefix}-veryai"
    ManagedBy = "terraform"
    Component = "verification"
  }
}

resource "aws_secretsmanager_secret_version" "veryai" {
  secret_id = aws_secretsmanager_secret.veryai.id
  # All four keys must exist for the :KEY:: syntax in ecs.tf to resolve,
  # even when the values are empty strings. Empty values are harmless while
  # EM_VERYAI_ENABLED=false because the routes are not registered.
  secret_string = jsonencode({
    VERYAI_CLIENT_ID     = ""
    VERYAI_CLIENT_SECRET = ""
    VERYAI_REDIRECT_URI  = ""
    VERYAI_STATE_SECRET  = ""
  })

  lifecycle {
    # Operator-managed values — do not let Terraform reset rotated secrets.
    ignore_changes = [secret_string]
  }
}

# IAM Policy for reading secrets
resource "aws_iam_policy" "secrets_read" {
  name        = "${local.name_prefix}-secrets-read"
  description = "Allow reading Execution Market secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          "arn:aws:secretsmanager:${local.region}:${local.account_id}:secret:em/*"
        ]
      }
    ]
  })
}
