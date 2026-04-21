# Execution Market Infrastructure - Variables

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "execution.market"
}

# VPC
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-2a", "us-east-2b"]
}

# ECS — MCP Server
# Dashboard is served via S3+CloudFront (dashboard-cdn.tf), no ECS task needed.
variable "mcp_server_cpu" {
  # Restored from 512/1024 after 2026-04-12 spike to 1111 MB RAM (see INC-2026-04-12)
  description = "CPU units for MCP server task (1024 = 1 vCPU)."
  type        = number
  default     = 1024
}

variable "mcp_server_memory" {
  # Restored from 512/1024 after 2026-04-12 spike to 1111 MB RAM (see INC-2026-04-12)
  description = "Memory (MB) for MCP server task."
  type        = number
  default     = 2048
}

variable "mcp_desired_count" {
  description = "Initial desired task count for MCP server (auto-scaling will adjust at runtime)"
  type        = number
  default     = 1
}

variable "mcp_min_count" {
  description = "Minimum task count for MCP server auto-scaling"
  type        = number
  default     = 1
}

variable "mcp_max_count" {
  description = "Maximum task count for MCP server auto-scaling"
  type        = number
  default     = 4
}

# Container image override (leave empty to use ECR :latest)
variable "mcp_server_image" {
  description = "MCP server container image override. Leave empty to use ECR :latest."
  type        = string
  default     = ""
}

# DNS
variable "domain" {
  description = "Root domain for the application"
  type        = string
  default     = "execution.market"
}

variable "api_subdomain" {
  description = "API subdomain"
  type        = string
  default     = "api"
}

variable "app_subdomain" {
  description = "App subdomain"
  type        = string
  default     = "app"
}

# Evidence pipeline (optional): API Gateway -> Lambda -> S3 -> CloudFront
variable "enable_evidence_pipeline" {
  description = "Enable managed evidence upload and delivery stack"
  type        = bool
  default     = false
}

variable "evidence_subdomain" {
  description = "Subdomain for evidence CDN when custom domain is configured"
  type        = string
  default     = "storage"
}

variable "evidence_acm_certificate_arn" {
  description = "ACM certificate ARN for CloudFront custom domain (must be in us-east-1). Leave empty to use default *.cloudfront.net domain."
  type        = string
  default     = ""
}

variable "evidence_bucket_name" {
  description = "Optional explicit S3 bucket name for evidence. Leave empty to auto-generate."
  type        = string
  default     = ""
}

variable "evidence_allowed_origins" {
  description = "Allowed browser origins for evidence upload CORS"
  type        = list(string)
  default     = ["https://execution.market", "https://www.execution.market"]
}

variable "evidence_retention_days" {
  description = "S3 evidence retention in days. Set 0 to disable automatic expiration."
  type        = number
  default     = 365
}

variable "evidence_presign_expiry_seconds" {
  description = "Expiration time in seconds for presigned upload/download URLs"
  type        = number
  default     = 900
}

variable "evidence_max_upload_mb" {
  description = "Maximum size in MB for presigned uploads (enforced in presigned POST mode)"
  type        = number
  default     = 25
}

# WAF
variable "waf_blocked_ips" {
  description = "List of CIDR blocks to permanently block at WAF level. Added 2026-04-04 after Tor exit node 104.244.78.233 flood."
  type        = list(string)
  default     = ["104.244.78.233/32"]
}

# Build metadata (injected by CI, used in Lambda env vars for version tracking)
variable "git_sha" {
  description = "Git commit SHA of the deployed code (set by CI)"
  type        = string
  default     = "unknown"
}

variable "build_timestamp" {
  description = "ISO 8601 build timestamp (set by CI)"
  type        = string
  default     = "unknown"
}

# Monitoring
variable "alert_email" {
  description = "Email for CloudWatch alarm notifications (SNS subscription created automatically)"
  type        = string
  default     = "0xultravioleta@gmail.com"
}

# OpenTelemetry / ADOT (Phase 6.2 SAAS_PRODUCTION_HARDENING)
# Toggling this boolean:
#   - adds the AWS Distro for OpenTelemetry sidecar to the MCP task
#   - attaches AWSXRayDaemonWriteAccess to the ECS task role
#   - sets OTEL_ENABLED=true + OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
#     on the mcp-server container so outbound spans land on the sidecar
# The Python bootstrap in mcp_server/observability/tracing.py already treats
# OTEL_ENABLED as the master switch, so flipping this flag is the only knob
# needed to turn tracing on.
variable "otel_enabled" {
  description = "Enable ADOT collector sidecar + FastAPI OTel tracing (exports to X-Ray)"
  type        = bool
  default     = false
}

variable "otel_traces_sampler_arg" {
  description = "OTel head-sampling ratio (0.0–1.0). 0.1 keeps 10% of traces; increase during incident investigations."
  type        = string
  default     = "0.1"
}

variable "enable_magika_alarm" {
  # Default false so a cold alarm is never enabled before the ECS task rolls
  # out with the emitter. Flip to true (via tfvars) AFTER confirming the
  # ExecutionMarket/Verification/MagikaRejectionRate datapoints arrive from
  # `verification.cloudwatch_metrics.run_magika_metrics_loop` (see CLAUDE.md).
  description = "Enable the Magika rejection-rate CloudWatch alarm. Requires custom metric emission to be live."
  type        = bool
  default     = false
}

variable "enable_scp_management" {
  # Default false: CI deploy IAM user does NOT have organizations:* permissions
  # and the SCP itself is defense-in-depth (policy created but intentionally
  # unattached — see organizations_scp.tf limitation #2). Enable only when
  # running terraform apply from an admin machine that CAN read Organizations.
  # Reason: CI run 24749184610 failed with AccessDeniedException on
  # DescribeOrganization. See INC-2026-04-21.
  description = "Manage Organizations SCP resources (requires organizations:* perms — usually admin-only)."
  type        = bool
  default     = false
}

variable "enable_mfa_enforcement" {
  # Default false: CI deploy user does NOT have iam:CreatePolicy.
  # MFA enforcement is a human-only concern (forces console users to use MFA)
  # and the policy is managed separately from workload deploys.
  # Enable from an admin workstation with full IAM permissions.
  # Reason: CI run 24749420481 AccessDenied on iam:CreatePolicy.
  description = "Manage ForceMFA IAM policy + attachments (requires iam:* perms — admin-only)."
  type        = bool
  default     = false
}

variable "enable_vpc_flow_logs" {
  # Default false: CI deploy user does NOT have ec2:CreateFlowLogs.
  # Flow logs are a security/forensics control best provisioned from an admin
  # workstation. The S3 bucket + policy are also gated here so the Terraform
  # state stays coherent (all-or-nothing).
  # Reason: CI run 24749420481 UnauthorizedOperation on ec2:CreateFlowLogs.
  description = "Manage VPC Flow Logs (S3 bucket + flow log + policies; requires ec2:CreateFlowLogs)."
  type        = bool
  default     = false
}

variable "enable_canary_health_checks" {
  # Default false. Two reasons:
  #   (1) Route53 HealthCheckStatus metrics are only emitted in us-east-1, and
  #       the CI run fails even with `provider = aws.us_east_1` — needs
  #       investigation on the admin side.
  #   (2) Route53 health checks cost ~$3/mo; opt-in keeps cost predictable.
  # Enable once the us-east-1 provider behaviour is reproduced locally.
  # Reason: CI run 24749420481 ValidationError on AWS/Route53 alarm in us-east-2.
  description = "Manage Route53 health checks + associated CloudWatch alarms (us-east-1 only)."
  type        = bool
  default     = false
}
