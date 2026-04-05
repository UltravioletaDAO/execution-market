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
  description = "CPU units for MCP server task (1024 = 1 vCPU). Doubled from 512 after OOM kills when AI verification (S3 image download + Anthropic API) runs concurrently with background jobs."
  type        = number
  default     = 1024
}

variable "mcp_server_memory" {
  description = "Memory (MB) for MCP server task. Doubled from 1024 after OOM kills during concurrent AI verification + background job spikes (rev 298 incident)."
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

# Monitoring
variable "alert_email" {
  description = "Email for CloudWatch alarm notifications (SNS subscription created automatically)"
  type        = string
  default     = "0xultravioleta@gmail.com"
}
